"""
Tests for src/backend/services/data_loader.py

Run from the src/ directory:
    pytest tests/test_data_loader.py -v
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_loader():
    """Return a freshly imported data_loader with its lru_cache cleared."""
    import backend.services.data_loader as mod
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoadDataset:
    def test_returns_dataframe(self):
        """load_dataset() returns a pandas DataFrame."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        assert isinstance(df, pd.DataFrame)

    def test_row_count(self):
        """Dataset has the expected 17,520 rows."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        assert len(df) == 17_520, f"Expected 17520 rows, got {len(df)}"

    def test_required_columns_present(self):
        """All 18 required columns are present."""
        from backend.services.data_loader import load_dataset, REQUIRED_COLUMNS
        load_dataset.cache_clear()
        df = load_dataset()
        missing = REQUIRED_COLUMNS - set(df.columns)
        assert not missing, f"Missing columns: {sorted(missing)}"

    def test_timestamp_is_datetime(self):
        """timestamp column is parsed as datetime with UTC timezone."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert df["timestamp"].dt.tz is not None, "timestamp should have timezone info"

    def test_no_null_values(self):
        """Dataset contains no null or NaN values."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        assert cols_with_nulls.empty, f"Columns with nulls: {cols_with_nulls.to_dict()}"

    def test_demand_mw_range(self):
        """demand_mw values are within the expected synthetic range."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        assert df["demand_mw"].min() >= 100.0
        assert df["demand_mw"].max() <= 400.0

    def test_frequency_nominal(self):
        """Grid frequency is close to nominal 50 Hz most of the time."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        # At least 99% of rows should be within ±0.6 Hz of 50 Hz
        near_nominal = df["frequency_hz"].between(49.4, 50.6)
        pct = near_nominal.mean()
        assert pct >= 0.99, f"Only {pct:.1%} rows have nominal frequency"

    def test_battery_soc_bounds(self):
        """Battery SOC stays within [1, 99] percent."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        assert df["battery_soc_pct"].min() >= 1.0
        assert df["battery_soc_pct"].max() <= 99.0

    def test_timestamp_continuity(self):
        """All timestamps are exactly 15 minutes apart."""
        from backend.services.data_loader import load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        deltas = df["timestamp"].diff().dropna().dt.total_seconds()
        assert (deltas == 900).all(), "Not all intervals are 15 minutes (900 seconds)"


class TestGetLatestRows:
    def test_returns_n_rows(self):
        """get_latest_rows(n) returns exactly n rows."""
        from backend.services.data_loader import get_latest_rows, load_dataset
        load_dataset.cache_clear()
        rows = get_latest_rows(48)
        assert len(rows) == 48

    def test_default_96_rows(self):
        """Default window is 96 rows."""
        from backend.services.data_loader import get_latest_rows, load_dataset
        load_dataset.cache_clear()
        rows = get_latest_rows()
        assert len(rows) == 96

    def test_returns_most_recent(self):
        """get_latest_rows returns the tail of the dataset."""
        from backend.services.data_loader import get_latest_rows, load_dataset
        load_dataset.cache_clear()
        df = load_dataset()
        recent = get_latest_rows(10)
        # Last timestamp should match last row in full dataset
        assert recent["timestamp"].iloc[-1] == df["timestamp"].iloc[-1]


class TestGetDatasetInfo:
    def test_info_keys(self):
        """get_dataset_info returns expected keys."""
        from backend.services.data_loader import get_dataset_info, load_dataset
        load_dataset.cache_clear()
        info = get_dataset_info()
        assert "rows" in info
        assert "columns" in info
        assert "start" in info
        assert "end" in info
        assert info["rows"] == 17_520


class TestMissingFile:
    def test_missing_csv_raises_file_not_found(self, tmp_path, monkeypatch):
        """load_dataset raises FileNotFoundError when CSV is missing."""
        import backend.config as cfg
        import backend.services.data_loader as loader_mod

        monkeypatch.setattr(cfg, "GRID_DATA_PATH", tmp_path / "nonexistent.csv")
        monkeypatch.setattr(loader_mod, "GRID_DATA_PATH", tmp_path / "nonexistent.csv")
        loader_mod.load_dataset.cache_clear()

        with pytest.raises(FileNotFoundError, match="Grid dataset not found"):
            loader_mod.load_dataset()
