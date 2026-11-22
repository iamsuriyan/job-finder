"""Load monochrome dashboard HTML template."""

from __future__ import annotations

from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"
_INDEX_PATH = _STATIC_DIR / "index.html"
_ASSETS_DIR = _STATIC_DIR / "assets"


def get_static_dir() -> Path:
    """Return the static files directory path."""
    return _STATIC_DIR


def get_assets_dir() -> Path:
    """Return the assets directory path."""
    return _ASSETS_DIR


def get_dashboard_html() -> str:
    """Read and return the dashboard HTML template."""
    return _INDEX_PATH.read_text(encoding="utf-8")


DASHBOARD_HTML = get_dashboard_html()

