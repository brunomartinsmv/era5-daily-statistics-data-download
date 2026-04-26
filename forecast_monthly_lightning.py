#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DEFAULT = str(
    PROJECT_ROOT / "data" / "processed" / "monthly" / "cuiaba_mensal_raios_era5_corrigido_2005_2023.csv"
)
TARGET_DEFAULT = "days_with_lightning"
EXOG_DEFAULT = ["cape_mean", "cape_max", "tcwv_mean"]


@dataclass
class SplitConfig:
    train_end: str = "2021-12-31"
    test_start: str = "2022-01-01"
    test_end: str = "2022-12-31"
    val_start: str = "2023-01-01"
    val_end: str = "2023-12-31"


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def add_provenance_columns(df: pd.DataFrame, metadata: dict[str, str]) -> pd.DataFrame:
    out = df.copy()
    out["run_id"] = metadata["run_id"]
    out["run_timestamp_utc"] = metadata["run_timestamp_utc"]
    out["git_commit"] = metadata["git_commit"]
    out["input_data_sha256"] = metadata["input_data_sha256"]
    return out


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["month"] = df.index.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12.0)
    return df


def add_target_lags(df: pd.DataFrame, target: str) -> pd.DataFrame:
    df = df.copy()
    for lag in range(1, 13):
        df[f"{target}_lag_{lag}"] = df[target].shift(lag)
    for win in [3, 6, 12]:
        df[f"{target}_roll_mean_{win}"] = df[target].shift(1).rolling(win).mean()
        df[f"{target}_roll_std_{win}"] = df[target].shift(1).rolling(win).std()
    return df


def add_exog_lags(df: pd.DataFrame, exog_cols) -> pd.DataFrame:
    df = df.copy()
    for col in exog_cols:
        if col not in df.columns:
            continue
        for lag in [1, 2, 3]:
            df[f"{col}_lag_{lag}"] = df[col].shift(lag)
    return df


def build_dataset(df: pd.DataFrame, target: str, exog_cols) -> pd.DataFrame:
    df = df.copy()
    df = add_target_lags(df, target)
    df = add_exog_lags(df, exog_cols)
    df["y_next"] = df[target].shift(-1)
    df["pred_date"] = df.index + pd.offsets.MonthBegin(1)
    df = df.set_index("pred_date")
    df = add_time_features(df)
    return df


def split_data(df: pd.DataFrame, split: SplitConfig):
    train = df.loc[: split.train_end]
    test = df.loc[split.test_start : split.test_end]
    val = df.loc[split.val_start : split.val_end]
    return train, test, val


def evaluate(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = r2_score(y_true, y_pred)
    return {"mae": mae, "rmse": rmse, "r2": r2}


def seasonal_naive_forecast(y: pd.Series, horizon: int = 12) -> np.ndarray:
    # Same month last year
    if len(y) < 12:
        return np.full(horizon, np.nan)
    last_year = y.iloc[-12:].values
    if horizon <= 12:
        return last_year[:horizon]
    reps = int(np.ceil(horizon / 12))
    return np.tile(last_year, reps)[:horizon]


def build_feature_row_from_history(
    y_hist: pd.Series,
    pred_date: pd.Timestamp,
    target: str,
    exog_hist: pd.DataFrame,
    exog_cols,
    exog_climatology,
) -> pd.Series:
    row = {}
    for lag in range(1, 13):
        lag_date = pred_date - pd.DateOffset(months=lag)
        row[f"{target}_lag_{lag}"] = y_hist.get(lag_date, np.nan)
    for col in exog_cols:
        if col not in exog_hist.columns:
            continue
        for lag in [1, 2, 3]:
            lag_date = pred_date - pd.DateOffset(months=lag)
            if lag_date in exog_hist.index:
                row[f"{col}_lag_{lag}"] = exog_hist[col].get(lag_date, np.nan)
            else:
                month = lag_date.month
                row[f"{col}_lag_{lag}"] = exog_climatology.get(col, {}).get(month, np.nan)
    for win in [3, 6, 12]:
        vals = [row[f"{target}_lag_{i}"] for i in range(1, win + 1)]
        row[f"{target}_roll_mean_{win}"] = np.nanmean(vals)
        row[f"{target}_roll_std_{win}"] = np.nanstd(vals, ddof=0)
    row["month"] = pred_date.month
    row["month_sin"] = np.sin(2 * np.pi * row["month"] / 12.0)
    row["month_cos"] = np.cos(2 * np.pi * row["month"] / 12.0)
    return pd.Series(row, name=pred_date)


def recursive_forecast(
    model,
    y_history: pd.Series,
    target: str,
    steps: int,
    exog_history: pd.DataFrame,
    exog_cols,
    exog_climatology,
    feature_cols,
) -> pd.DataFrame:
    preds = []
    dates = []
    current_date = y_history.index.max()

    y_hist = y_history.copy()
    exog_hist = exog_history.copy()
    for _ in range(steps):
        next_date = (current_date + pd.offsets.MonthBegin(1)).normalize()
        feat = build_feature_row_from_history(
            y_hist, next_date, target, exog_hist, exog_cols, exog_climatology
        )
        X = feat[feature_cols]
        pred = float(model.predict(pd.DataFrame([X]))[0])
        y_hist.loc[next_date] = pred
        preds.append(pred)
        dates.append(next_date)
        current_date = next_date

    return pd.DataFrame({"date": dates, "prediction": preds})


def main():
    parser = argparse.ArgumentParser(description="Monthly lightning next-month forecast (Cuiaba).")
    parser.add_argument("--data", default=DATA_DEFAULT, help="Path to monthly merged CSV.")
    parser.add_argument("--target", default=TARGET_DEFAULT, help="Target column name.")
    parser.add_argument("--steps", type=int, default=12, help="Forecast steps beyond last month.")
    parser.add_argument(
        "--exog",
        nargs="*",
        default=EXOG_DEFAULT,
        help="Exogenous predictors to use (will be lagged by 1-3 months).",
    )
    parser.add_argument("--outdir", default="/Users/bruno/Documents/mestrado/results", help="Output directory.")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run identifier for traceability. Default: UTC timestamp.",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    if "date" not in df.columns:
        raise ValueError("Expected 'date' column in the dataset.")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    if args.target not in df.columns:
        raise ValueError(f"Target '{args.target}' not found in data columns.")

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_metadata = {
        "run_id": run_id,
        "run_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "git_commit": resolve_git_commit(),
        "input_data_sha256": compute_file_sha256(data_path),
    }

    df_model = build_dataset(df, args.target, args.exog)
    df_model = df_model.dropna()

    split = SplitConfig()
    train, test, val = split_data(df_model, split)

    base_features = {"month", "month_sin", "month_cos"}
    feature_cols = []
    for c in df_model.columns:
        if c in base_features:
            feature_cols.append(c)
        elif c.startswith(f"{args.target}_lag_") or c.startswith(f"{args.target}_roll_"):
            feature_cols.append(c)
        elif any(c.startswith(f"{ex}_lag_") for ex in args.exog):
            feature_cols.append(c)
    feature_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df_model[c])]
    X_train, y_train = train[feature_cols], train["y_next"]
    X_test, y_test = test[feature_cols], test["y_next"]
    X_val, y_val = val[feature_cols], val["y_next"]

    models = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(
            n_estimators=500, random_state=42, min_samples_leaf=2
        ),
        "GradientBoosting": GradientBoostingRegressor(random_state=42),
    }

    rows = []
    pred_frames = []

    for name, model in models.items():
        model.fit(X_train, y_train)
        pred_test = model.predict(X_test)
        pred_val = model.predict(X_val)

        metrics_test = evaluate(y_test, pred_test)
        metrics_val = evaluate(y_val, pred_val)

        rows.append(
            {
                "model": name,
                "split": "test_2022",
                **metrics_test,
            }
        )
        rows.append(
            {
                "model": name,
                "split": "val_2023",
                **metrics_val,
            }
        )

        pred_frames.append(
            pd.DataFrame(
                {
                    "date": X_test.index,
                    "split": "test_2022",
                    "model": name,
                    "y_true": y_test.values,
                    "y_pred": pred_test,
                }
            )
        )
        pred_frames.append(
            pd.DataFrame(
                {
                    "date": X_val.index,
                    "split": "val_2023",
                    "model": name,
                    "y_true": y_val.values,
                    "y_pred": pred_val,
                }
            )
        )

    metrics_df = add_provenance_columns(pd.DataFrame(rows), run_metadata)
    metrics_path = outdir / "metrics_monthly_lightning_next_month.csv"
    metrics_df.to_csv(metrics_path, index=False)

    preds_df = add_provenance_columns(pd.concat(pred_frames, ignore_index=True), run_metadata)
    preds_path = outdir / "predictions_monthly_lightning_next_month.csv"
    preds_df.to_csv(preds_path, index=False)

    # Seasonal naive baseline for 2023 validation
    naive_val = seasonal_naive_forecast(df.loc[: split.val_start][args.target], horizon=len(y_val))
    if len(naive_val) == len(y_val):
        naive_metrics = evaluate(y_val.values, naive_val)
        baseline_path = outdir / "baseline_seasonal_naive_2023.csv"
        baseline_df = add_provenance_columns(
            pd.DataFrame(
                [
                    {
                        "model": "SeasonalNaive",
                        "split": "val_2023",
                        **naive_metrics,
                    }
                ]
            ),
            run_metadata,
        )
        baseline_df.to_csv(baseline_path, index=False)

    # Train final model on train+test+val for forecasting
    # Pick best by val RMSE
    best_model_name = (
        metrics_df[metrics_df["split"] == "val_2023"]
        .sort_values("rmse")
        .iloc[0]["model"]
    )
    best_model = models[best_model_name]
    best_model.fit(df_model[feature_cols], df_model["y_next"])

    y_history = df[args.target].copy()
    exog_history = df[args.exog].copy() if len(args.exog) > 0 else pd.DataFrame(index=df.index)
    exog_climatology = {}
    if len(args.exog) > 0:
        for col in args.exog:
            if col in df.columns:
                exog_climatology[col] = (
                    df[col].groupby(df.index.month).mean().to_dict()
                )
    future_df = recursive_forecast(
        best_model,
        y_history,
        args.target,
        args.steps,
        exog_history,
        args.exog,
        exog_climatology,
        feature_cols,
    )
    future_df["model"] = best_model_name
    future_df = add_provenance_columns(future_df, run_metadata)
    future_path = outdir / "forecast_next_12_months.csv"
    future_df.to_csv(future_path, index=False)

    metadata_path = outdir / f"forecast_monthly_lightning_run_{run_id}.json"
    manifest = {
        "run": {
            **run_metadata,
            "script": str(Path(__file__).name),
        },
        "parameters": {
            "data": str(data_path),
            "target": args.target,
            "steps": args.steps,
            "exog": args.exog,
            "outdir": str(outdir),
            "split": {
                "train_end": split.train_end,
                "test_start": split.test_start,
                "test_end": split.test_end,
                "val_start": split.val_start,
                "val_end": split.val_end,
            },
        },
        "features": {
            "count": len(feature_cols),
            "columns": feature_cols,
        },
        "outputs": {
            "metrics_csv": str(metrics_path),
            "predictions_csv": str(preds_path),
            "forecast_csv": str(future_path),
        },
    }
    metadata_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Saved run metadata:", metadata_path)
    print("Saved metrics:", metrics_path)
    print("Saved predictions:", preds_path)
    print("Saved future forecast:", future_path)


if __name__ == "__main__":
    main()
