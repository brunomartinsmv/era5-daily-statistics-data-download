"""Tests for the ERA5 download CLI and library."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import download_era5_daily as era5  # noqa: E402


class BuildRequestTests(unittest.TestCase):
    def test_hourly_request_omits_area_when_unset(self) -> None:
        args = era5.argparse.Namespace(
            area=None,
            format="grib",
            download_format="zip",
            pressure_levels=["850"],
        )
        request = era5._build_hourly_request(
            args,
            era5.DATASET_SINGLE_LEVELS,
            ["2m_temperature"],
            "2020",
            ["01"],
        )
        self.assertNotIn("area", request)
        self.assertEqual(request["product_type"], "reanalysis")

    def test_hourly_request_includes_area_when_set(self) -> None:
        area = [-15.0, -56.5, -16.5, -55.5]
        args = era5.argparse.Namespace(
            area=area,
            format="grib",
            download_format="zip",
            pressure_levels=["850"],
        )
        request = era5._build_hourly_request(
            args,
            era5.DATASET_SINGLE_LEVELS,
            ["2m_temperature"],
            "2020",
            ["01"],
        )
        self.assertEqual(request["area"], area)

    def test_daily_statistics_request_omits_area_when_unset(self) -> None:
        args = era5.argparse.Namespace(
            variables=["2m_temperature"],
            start_year=2020,
            end_year=2020,
            months=None,
            statistic="daily_mean",
            time_zone="utc+00:00",
            frequency="1_hourly",
            output=None,
            output_dir="downloads",
            area=None,
        )
        targets = era5.build_daily_statistics_target(args)
        self.assertNotIn("area", targets[0].request)


class OutputPathTests(unittest.TestCase):
    def test_single_year_deterministic_name(self) -> None:
        args = era5.argparse.Namespace(
            output=None,
            start_year=2020,
            end_year=2020,
            statistic="daily_mean",
            output_dir="downloads",
        )
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertEqual(path, Path("downloads/era5_daily_statistics_2020.nc"))

    def test_multi_year_deterministic_name(self) -> None:
        args = era5.argparse.Namespace(
            output=None,
            start_year=2020,
            end_year=2023,
            statistic="daily_mean",
            output_dir="downloads",
        )
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertEqual(path, Path("downloads/era5_daily_statistics_2020_2023.nc"))

    def test_custom_statistic_included_in_name(self) -> None:
        args = era5.argparse.Namespace(
            output=None,
            start_year=2020,
            end_year=2020,
            statistic="daily_maximum",
            output_dir="downloads",
        )
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertEqual(path, Path("downloads/era5_daily_statistics_2020_daily_maximum.nc"))

    def test_explicit_output_preserved(self) -> None:
        args = era5.argparse.Namespace(
            output="custom/path/data.nc",
            start_year=2020,
            end_year=2020,
            statistic="daily_mean",
            output_dir="downloads",
        )
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertEqual(path, Path("custom/path/data.nc"))


class MonthValidationTests(unittest.TestCase):
    def test_valid_month_range_same_year(self) -> None:
        era5._validate_months(1, 12, 2020, 2020)
        era5._validate_months(6, 8, 2020, 2020)

    def test_invalid_month_out_of_range(self) -> None:
        with self.assertRaises(SystemExit):
            era5._validate_months(0, 12, 2020, 2020)
        with self.assertRaises(SystemExit):
            era5._validate_months(1, 13, 2020, 2020)

    def test_inverted_months_same_year_fails(self) -> None:
        with self.assertRaises(SystemExit):
            era5._validate_months(11, 2, 2020, 2020)

    def test_inverted_months_multi_year_allowed(self) -> None:
        era5._validate_months(11, 2, 2020, 2021)


class AtomicDownloadTests(unittest.TestCase):
    def test_successful_atomic_download_renames_part_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            target = era5.DownloadTarget(
                label="test_ok",
                request={"var": "2m_temperature"},
                output=dest,
            )

            mock_client = MagicMock()
            def fake_download(path_str: str) -> None:
                p = Path(path_str)
                self.assertTrue(p.name.endswith(".part"))
                p.write_text("data")

            mock_client.retrieve.return_value.download.side_effect = fake_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                code = era5.retrieve_targets("dummy-dataset", [target], overwrite=True, sleep_seconds=0)

            self.assertEqual(code, 0)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.read_text(), "data")
            self.assertFalse(dest.with_name("output.nc.part").exists())

    def test_failed_download_cleans_up_part_file_without_corrupting_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            target = era5.DownloadTarget(
                label="test_fail",
                request={"var": "2m_temperature"},
                output=dest,
            )

            mock_client = MagicMock()
            def failing_download(path_str: str) -> None:
                p = Path(path_str)
                p.write_text("partial corrupt data")
                raise RuntimeError("CDS network error")

            mock_client.retrieve.return_value.download.side_effect = failing_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                code = era5.retrieve_targets("dummy-dataset", [target], overwrite=True, sleep_seconds=0)

            self.assertEqual(code, 1)
            self.assertFalse(dest.exists())
            self.assertFalse(dest.with_name("output.nc.part").exists())


class ModelLevelTargetTests(unittest.TestCase):
    def test_custom_output_prefix(self) -> None:
        args = era5.argparse.Namespace(
            start_year=2020,
            end_year=2020,
            start_month=1,
            end_month=1,
            variables=["t", "q"],
            area=era5.DEFAULT_AREA_CUIABA,
            output_dir="downloads/model_levels",
            output_prefix="custom_prefix",
            chunk="month",
            levelist=era5.DEFAULT_MODEL_LEVELS,
            grid=era5.DEFAULT_GRID,
            format="grib",
        )
        targets = era5.build_model_level_targets(args)
        self.assertEqual(len(targets), 1)
        self.assertTrue(targets[0].output.name.startswith("custom_prefix_2020_01"))

    def test_model_level_request_uses_mars_area_string(self) -> None:
        args = era5.argparse.Namespace(
            levelist=era5.DEFAULT_MODEL_LEVELS,
            area=era5.DEFAULT_AREA_CUIABA,
            grid=era5.DEFAULT_GRID,
            format="grib",
        )
        request = era5._build_model_level_request(args, ["t"], "2020-01-01/to/2020-01-31")
        self.assertEqual(request["area"], "-15/-56.5/-16.5/-55.5")
        self.assertEqual(request["param"], "130")


class TemperatureRegimeScriptTests(unittest.TestCase):
    def test_year_chunk_respects_month_bounds(self) -> None:
        from scripts.download_era5_temperature_regime_vars import build_targets

        targets = build_targets("single-levels", 2020, 2020, 6, 8, "year")
        self.assertEqual(len(targets), 1)
        year, months, _path = targets[0]
        self.assertEqual(year, 2020)
        self.assertEqual(months, ["06", "07", "08"])


class CliDryRunTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "download_era5_daily.py"), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_all_presets_exit_zero_on_dry_run(self) -> None:
        commands = [
            ("daily-statistics", "--variables", "2m_temperature", "--start-year", "2020", "--end-year", "2020"),
            ("single-levels", "--start-year", "2020", "--end-year", "2020", "--start-month", "6", "--end-month", "8"),
            ("land", "--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "2"),
            ("pressure-levels", "--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "1"),
            ("model-levels", "--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "1"),
        ]
        for preset_args in commands:
            with self.subTest(preset=preset_args[0]):
                result = self._run(*preset_args, "--dry-run")
                self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

    def test_auxiliary_scripts_exit_zero_on_dry_run(self) -> None:
        scripts = [
            (
                ROOT / "scripts" / "download_era5_model_levels.py",
                ["--start-year", "2020", "--end-year", "2020", "--start-month", "1", "--end-month", "1"],
            ),
            (
                ROOT / "scripts" / "download_era5_temperature_regime_vars.py",
                ["--start-year", "2020", "--end-year", "2020", "--start-month", "6", "--end-month", "8", "--preset", "single-levels"],
            ),
        ]
        for script, args in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, str(script), *args, "--dry-run"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)


class PrintDryRunTests(unittest.TestCase):
    def test_print_dry_run_includes_first_request_json(self) -> None:
        target = era5.DownloadTarget(
            label="2020",
            request={"variable": ["2m_temperature"], "year": "2020"},
            output=Path("downloads/example.nc"),
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            era5.print_dry_run(era5.DATASET_DAILY, [target], overwrite=False)
        output = buffer.getvalue()
        self.assertIn("First request:", output)
        payload = output.split("First request:\n", 1)[1].strip()
        self.assertEqual(json.loads(payload)["year"], "2020")


if __name__ == "__main__":
    unittest.main()
