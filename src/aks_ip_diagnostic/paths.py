"""Filesystem path helpers for generated reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_EXTENSION_BY_FORMAT = {
    "text": "txt",
    "json": "json",
    "json-pretty": "json",
    "json-compact": "json",
    "yaml": "yaml",
    "markdown": "md",
    "html": "html",
}


def get_report_path(
    cluster_name: str, output_format: str, custom_filename: str | None = None
) -> Path:
    """Return the final report path and create parent directories as needed.

    If a user provides --output, that exact path is respected.  Otherwise the
    report is timestamped under ./reports to avoid overwriting earlier scans.
    """

    if custom_filename:
        custom_path = Path(custom_filename)
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        return custom_path

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = _EXTENSION_BY_FORMAT.get(output_format, "txt")
    return reports_dir / f"{cluster_name}_diagnostic_{timestamp}.{extension}"
