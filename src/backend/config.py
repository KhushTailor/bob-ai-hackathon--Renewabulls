"""
GridPulse backend configuration.

All settings are read from environment variables (or .env).
Defaults are provided so the server starts without any configuration.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
import os

# Load .env from src/ directory (one level up from backend/)
_src_dir = Path(__file__).resolve().parent.parent
load_dotenv(_src_dir / ".env")

# ---------------------------------------------------------------------------
# Dataset path
# ---------------------------------------------------------------------------
# Resolved relative to src/ so the server can be started from any directory.
_default_data_path = _src_dir / "data" / "grid_data.csv"
GRID_DATA_PATH: Path = Path(os.getenv("GRID_DATA_PATH", str(_default_data_path)))

# Make it absolute if it was supplied as a relative path
if not GRID_DATA_PATH.is_absolute():
    GRID_DATA_PATH = _src_dir / GRID_DATA_PATH

# ---------------------------------------------------------------------------
# Server settings
# ---------------------------------------------------------------------------
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
APP_ENV: str = os.getenv("APP_ENV", "development")

# ---------------------------------------------------------------------------
# watsonx.ai feature toggles (not used in S3 — defined here for completeness)
# ---------------------------------------------------------------------------
WATSONX_API_KEY: str = os.getenv("WATSONX_API_KEY", "")
WATSONX_PROJECT_ID: str = os.getenv("WATSONX_PROJECT_ID", "")
WATSONX_URL: str = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_GRANITE_TTM_ENABLED: bool = os.getenv("WATSONX_GRANITE_TTM_ENABLED", "false").lower() == "true"
WATSONX_BRIEF_ENABLED: bool = os.getenv("WATSONX_BRIEF_ENABLED", "false").lower() == "true"
