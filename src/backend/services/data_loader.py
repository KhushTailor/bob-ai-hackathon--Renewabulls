"""
GridPulse data loader.

Loads grid_data.csv into a Pandas DataFrame and provides a simple
accessor used by all backend service modules.

The CSV path is resolved from config.py, which defaults to
src/data/grid_data.csv relative to the src/ directory — so the
server starts correctly regardless of the working directory.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import pandas as pd

from backend.config import GRID_DATA_PATH


# Expected columns — used for schema validation on load
REQUIRED_COLUMNS = {
    "timestamp",
    "demand_mw",
    "solar_actual_mw",
    "wind_actual_mw",
    "solar_capacity_mw",
    "wind_capacity_mw",
    "solar_irradiance_wm2",
    "wind_speed_ms",
    "temperature_c",
    "battery_soc_pct",
    "grid_import_mw",
    "grid_export_mw",
    "frequency_hz",
    "voltage_pu",
    "hour_of_day",
    "day_of_week",
    "month",
    "is_weekend",
}


@lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    """Load the full grid dataset from CSV.

    The result is cached after the first call so subsequent requests
    do not re-read the file from disk.

    Raises:
        FileNotFoundError: if grid_data.csv does not exist at the
            configured path.
        ValueError: if required columns are missing from the CSV.

    Returns:
        DataFrame with all grid columns, timestamp parsed as UTC datetime.
    """
    path: Path = GRID_DATA_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Grid dataset not found at '{path}'. "
            "Run 'python data/generate_dataset.py' from the src/ directory to create it."
        )

    df = pd.read_csv(
        path,
        parse_dates=["timestamp"],
    )

    # Normalise timestamp timezone to UTC
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    # Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Grid dataset is missing required columns: {sorted(missing)}"
        )

    return df


def get_latest_rows(n: int = 96) -> pd.DataFrame:
    """Return the most recent *n* rows of the dataset.

    Used by services that need a rolling window of recent grid state.
    """
    df = load_dataset()
    return df.tail(n).reset_index(drop=True)


def get_dataset_info() -> dict:
    """Return basic metadata about the loaded dataset."""
    df = load_dataset()
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "start": str(df["timestamp"].iloc[0]),
        "end": str(df["timestamp"].iloc[-1]),
        "path": str(GRID_DATA_PATH),
    }
