"""Load monochrome dashboard HTML template."""

from __future__ import annotations

from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"
_INDEX_PATH = _STATIC_DIR / "index.html"


def get_dashboard_html() -> str:
    """Read and return the dashboard HTML template."""
    return _INDEX_PATH.read_text(encoding="utf-8")


DASHBOARD_HTML = get_dashboard_html()
