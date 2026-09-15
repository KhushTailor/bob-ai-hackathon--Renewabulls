"""
pytest configuration for GridPulse backend tests.

Adds src/ to sys.path so that `import backend` resolves correctly
regardless of working directory.
"""
import sys
from pathlib import Path

# src/ directory (one level up from tests/)
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
