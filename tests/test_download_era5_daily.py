"""Tests for the ERA5 download CLI and library."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
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


def _daily_args(**overrides: object) -> era5.argparse.Namespace:
    values: dict[str, object] = {
        "output": None,
        "start_year": 2020,
        "end_year": 2020,
        "months": None,
        "statistic": "daily_mean",
        "time_zone": "utc+00:00",
        "frequency": "1_hourly",
        "variables": ["2m_temperature"],
        "area": None,
        "output_dir": "downloads",
    }
    values.update(overrides)
    return era5.argparse.Namespace(**values)


class OutputPathTests(unittest.TestCase):
    def test_hourly_year_chunk_partial_months_includes_suffix(self) -> None:
        args = era5.argparse.Namespace(
            start_year=2020,
            end_year=2021,
            start_month=11,
            end_month=2,
            variables=["2m_temperature"],
            area=None,
            format="grib",
            download_format="zip",
            chunk="year",
            output_dir="downloads",
        )
        targets = era5.build_hourly_targets(args, "single-levels", era5.DATASET_SINGLE_LEVELS)
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0].output.name, "era5_single-levels_2020_11-12.zip")
        self.assertEqual(targets[1].output.name, "era5_single-levels_2021_01-02.zip")

    def test_single_year_deterministic_name(self) -> None:
        args = _daily_args()
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        request = era5._daily_statistics_request(args)
        fingerprint = era5._request_fingerprint(request)
        self.assertEqual(
            path,
            Path(f"downloads/era5_daily_statistics_2020_2m_temperature_1_hourly_utc+00-00_{fingerprint}.nc"),
        )
        self.assertEqual(path, era5._single_output_path(args, "era5_daily_statistics", "nc"))

    def test_multi_year_deterministic_name(self) -> None:
        args = _daily_args(end_year=2023)
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertIn("2020_2023", path.name)
        self.assertEqual(path, era5._single_output_path(args, "era5_daily_statistics", "nc"))

    def test_custom_statistic_included_in_name(self) -> None:
        args = _daily_args(statistic="daily_maximum")
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertIn("daily_maximum", path.name)
        self.assertNotIn("daily_mean", path.name)

    def test_differentiates_variables_in_filename(self) -> None:
        path_temp = era5._single_output_path(_daily_args(variables=["2m_temperature"]), "era5_daily_statistics", "nc")
        path_press = era5._single_output_path(_daily_args(variables=["surface_pressure"]), "era5_daily_statistics", "nc")
        self.assertNotEqual(path_temp, path_press)
        self.assertIn("2m_temperature", path_temp.name)
        self.assertIn("surface_pressure", path_press.name)
        targets_temp = era5.build_daily_statistics_target(_daily_args(variables=["2m_temperature"]))
        targets_press = era5.build_daily_statistics_target(_daily_args(variables=["surface_pressure"]))
        self.assertNotEqual(targets_temp[0].output, targets_press[0].output)
        self.assertTrue(targets_temp[0].output.name.startswith("era5_daily_statistics_2020_2m_temperature_"))
        self.assertTrue(targets_press[0].output.name.startswith("era5_daily_statistics_2020_surface_pressure_"))

    def test_explicit_output_preserved(self) -> None:
        args = _daily_args(output="custom/path/data.nc")
        path = era5._single_output_path(args, "era5_daily_statistics", "nc")
        self.assertEqual(path, Path("custom/path/data.nc"))

    def test_equal_length_month_sets_do_not_share_a_path(self) -> None:
        january = _daily_args(months=["01", "02", "03", "04"])
        september = _daily_args(months=["09", "10", "11", "12"])
        path_january = era5._single_output_path(january, "era5_daily_statistics", "nc")
        path_september = era5._single_output_path(september, "era5_daily_statistics", "nc")
        self.assertNotEqual(path_january, path_september)
        self.assertIn("m01-02-03-04", path_january.name)
        self.assertIn("m09-10-11-12", path_september.name)
        self.assertNotIn("4months", path_january.name)

    def test_short_month_lists_keep_padding_and_separators(self) -> None:
        split_months = era5._single_output_path(_daily_args(months=["1", "2"]), "era5_daily_statistics", "nc")
        december = era5._single_output_path(_daily_args(months=["12"]), "era5_daily_statistics", "nc")
        self.assertNotEqual(split_months, december)
        self.assertIn("m01-02", split_months.name)
        self.assertIn("m12", december.name)

    def test_month_formatting_does_not_change_the_path(self) -> None:
        padded = era5._single_output_path(
            _daily_args(months=["04", "05", "06", "07"]),
            "era5_daily_statistics",
            "nc",
        )
        unpadded = era5._single_output_path(
            _daily_args(months=["4", "5", "6", "7"]),
            "era5_daily_statistics",
            "nc",
        )
        self.assertEqual(padded, unpadded)

    def test_frequency_and_time_zone_change_the_path(self) -> None:
        baseline = _daily_args()
        six_hourly = _daily_args(frequency="6_hourly")
        other_zone = _daily_args(time_zone="utc+01:00")
        path_baseline = era5._single_output_path(baseline, "era5_daily_statistics", "nc")
        path_six_hourly = era5._single_output_path(six_hourly, "era5_daily_statistics", "nc")
        path_other_zone = era5._single_output_path(other_zone, "era5_daily_statistics", "nc")
        self.assertNotEqual(path_baseline, path_six_hourly)
        self.assertNotEqual(path_baseline, path_other_zone)
        self.assertIn("6_hourly", path_six_hourly.name)
        self.assertIn("utc+01-00", path_other_zone.name)
        self.assertIn(
            era5._request_fingerprint(era5._daily_statistics_request(six_hourly)),
            path_six_hourly.name,
        )
        self.assertIn(
            era5._request_fingerprint(era5._daily_statistics_request(other_zone)),
            path_other_zone.name,
        )

    def test_built_target_uses_the_same_unique_path(self) -> None:
        args = _daily_args(months=["06", "07", "08"], frequency="3_hourly", area=[-15.0, -56.5, -16.5, -55.5])
        target = era5.build_daily_statistics_target(args)[0]
        self.assertEqual(target.output, era5._single_output_path(args, "era5_daily_statistics", "nc"))
        self.assertEqual(target.request["month"], ["06", "07", "08"])
        self.assertEqual(target.request["frequency"], "3_hourly")
        self.assertIn(era5._request_fingerprint(target.request), target.output.name)
        self.assertIn("area_-15_-56.5_-16.5_-55.5", target.output.name)


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
                self.assertIn("output.nc.", p.name)
                p.write_text("data")

            mock_client.retrieve.return_value.download.side_effect = fake_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                code = era5.retrieve_targets("dummy-dataset", [target], overwrite=True, sleep_seconds=0)

            self.assertEqual(code, 0)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.read_text(), "data")
            self.assertEqual(list(Path(tmpdir).glob("*.part")), [])
            self.assertEqual(list(Path(tmpdir).glob("*.lock")), [])

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
            self.assertEqual(list(Path(tmpdir).glob("*.part")), [])
            self.assertEqual(list(Path(tmpdir).glob("*.lock")), [])

    def test_keyboard_interrupt_removes_partial_file_and_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            target = era5.DownloadTarget(
                label="test_interrupt",
                request={"var": "2m_temperature"},
                output=dest,
            )

            mock_client = MagicMock()

            def interrupted(path_str: str) -> None:
                Path(path_str).write_text("partial")
                raise KeyboardInterrupt

            mock_client.retrieve.return_value.download.side_effect = interrupted
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                with self.assertRaises(KeyboardInterrupt):
                    era5.retrieve_targets("dummy-dataset", [target], overwrite=True, sleep_seconds=0)

            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(tmpdir).glob("*.part")), [])
            self.assertEqual(list(Path(tmpdir).glob("*.lock")), [])

            def complete(path_str: str) -> None:
                Path(path_str).write_text("ok")

            mock_client.retrieve.return_value.download.side_effect = complete
            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                code = era5.retrieve_targets("dummy-dataset", [target], overwrite=True, sleep_seconds=0)

            self.assertEqual(code, 0)
            self.assertEqual(dest.read_text(), "ok")

    def test_second_target_does_not_replace_completed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            targets = [
                era5.DownloadTarget(label="first", request={"n": 1}, output=dest),
                era5.DownloadTarget(label="second", request={"n": 2}, output=dest),
            ]
            calls: list[str] = []
            mock_client = MagicMock()

            def fake_download(path_str: str) -> None:
                calls.append(path_str)
                Path(path_str).write_text(f"payload-{len(calls)}")

            mock_client.retrieve.return_value.download.side_effect = fake_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                code = era5.retrieve_targets("dummy", targets, overwrite=False, sleep_seconds=0)

            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(dest.read_text(), "payload-1")
            self.assertEqual(list(Path(tmpdir).glob("*.lock")), [])

    def test_parallel_downloads_do_not_start_a_second_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            target = era5.DownloadTarget(label="parallel", request={"var": "t"}, output=dest)
            calls: list[str] = []
            started = threading.Barrier(2)
            both_saw_missing = threading.Event()
            seen_ids: set[int] = set()
            seen_lock = threading.Lock()
            original_exists = Path.exists

            def tracking_exists(self: Path) -> bool:
                result = original_exists(self)
                if self == dest and not result:
                    with seen_lock:
                        seen_ids.add(threading.get_ident())
                        if len(seen_ids) >= 2:
                            both_saw_missing.set()
                return result

            def fake_download(path_str: str) -> None:
                calls.append(path_str)
                self.assertTrue(both_saw_missing.wait(5))
                Path(path_str).write_text("payload")

            def worker() -> None:
                started.wait(5)
                era5.retrieve_targets("dummy", [target], overwrite=False, sleep_seconds=0)

            mock_client = MagicMock()
            mock_client.retrieve.return_value.download.side_effect = fake_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                with patch.object(Path, "exists", tracking_exists):
                    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(5)
                        self.assertFalse(thread.is_alive())

            self.assertEqual(len(calls), 1)
            self.assertEqual(dest.read_text(), "payload")
            self.assertEqual(list(Path(tmpdir).glob("*.part")), [])
            self.assertEqual(list(Path(tmpdir).glob("*.lock")), [])

    def test_output_lock_is_exclusive_across_threads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            held = threading.Event()
            release = threading.Event()
            acquired_second = threading.Event()

            def holder() -> None:
                with era5._exclusive_output_lock(dest):
                    held.set()
                    self.assertTrue(release.wait(5))

            def waiter() -> None:
                self.assertTrue(held.wait(5))
                with era5._exclusive_output_lock(dest):
                    acquired_second.set()

            first = threading.Thread(target=holder, daemon=True)
            second = threading.Thread(target=waiter, daemon=True)
            first.start()
            second.start()
            self.assertTrue(held.wait(5))
            time.sleep(0.1)
            self.assertFalse(acquired_second.is_set())
            release.set()
            first.join(5)
            second.join(5)
            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertTrue(acquired_second.is_set())
            self.assertFalse(era5._output_lock_path(dest).exists())

    def test_stale_lock_from_a_dead_process_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dead_pid = None
            for candidate in range(1_000_000, 1_002_000):
                try:
                    os.kill(candidate, 0)
                except ProcessLookupError:
                    dead_pid = candidate
                    break
                except PermissionError:
                    continue
            self.assertIsNotNone(dead_pid)
            lock_path = era5._output_lock_path(dest)
            lock_path.write_text(f"{dead_pid}-stale", encoding="ascii")
            with era5._exclusive_output_lock(dest):
                self.assertTrue(lock_path.read_text(encoding="ascii").startswith(f"{os.getpid()}-"))
            self.assertFalse(lock_path.exists())

    def test_interrupted_download_cleans_up_staging_file_and_reraises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            target = era5.DownloadTarget(
                label="test_cancel",
                request={"var": "2m_temperature"},
                output=dest,
            )

            mock_client = MagicMock()
            def interrupted_download(path_str: str) -> None:
                p = Path(path_str)
                p.write_text("interrupted partial data")
                raise KeyboardInterrupt("Simulated Ctrl-C")

            mock_client.retrieve.return_value.download.side_effect = interrupted_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                with self.assertRaises(KeyboardInterrupt):
                    era5.retrieve_targets("dummy-dataset", [target], overwrite=True, sleep_seconds=0)

            self.assertFalse(dest.exists())
            remaining_part_files = list(Path(tmpdir).glob("*.part"))
            self.assertEqual(len(remaining_part_files), 0)

    def test_concurrent_downloads_use_unique_part_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "output.nc"
            target1 = era5.DownloadTarget(label="t1", request={}, output=dest)
            target2 = era5.DownloadTarget(label="t2", request={}, output=dest)

            observed_part_paths: list[str] = []
            mock_client = MagicMock()
            def record_download(path_str: str) -> None:
                observed_part_paths.append(path_str)
                Path(path_str).write_text("dummy")

            mock_client.retrieve.return_value.download.side_effect = record_download
            mock_cdsapi = MagicMock()
            mock_cdsapi.Client.return_value = mock_client

            with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                era5.retrieve_targets("dummy", [target1, target2], overwrite=True, sleep_seconds=0)

            self.assertEqual(len(observed_part_paths), 2)
            self.assertNotEqual(observed_part_paths[0], observed_part_paths[1])


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

    def test_overwrite_failure_does_not_report_old_file_as_generated(self) -> None:
        from scripts.download_era5_temperature_regime_vars import download_kind

        with tempfile.TemporaryDirectory() as tmpdir:
            from scripts import download_era5_temperature_regime_vars as tr

            old_output = Path(tmpdir) / "era5_cuiaba_temperature_regime_single_levels_2020.zip"
            old_output.write_text("old data")

            orig_dir = tr.DATASETS["single-levels"]["output_dir"]
            try:
                tr.DATASETS["single-levels"]["output_dir"] = Path(tmpdir)
                mock_client = MagicMock()
                mock_client.retrieve.return_value.download.side_effect = RuntimeError("Failed")
                mock_cdsapi = MagicMock()
                mock_cdsapi.Client.return_value = mock_client

                with patch.dict("sys.modules", {"cdsapi": mock_cdsapi}):
                    generated, failures = download_kind(
                        kind="single-levels",
                        year_start=2020,
                        year_end=2020,
                        month_start=1,
                        month_end=12,
                        chunk_mode="year",
                        dry_run=False,
                        sleep_seconds=0,
                        overwrite=True,
                    )

                self.assertEqual(generated, [])
                self.assertEqual(len(failures), 1)
            finally:
                tr.DATASETS["single-levels"]["output_dir"] = orig_dir


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
