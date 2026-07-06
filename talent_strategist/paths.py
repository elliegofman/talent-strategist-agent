"""Filesystem path helpers for report output."""
from __future__ import annotations

from datetime import datetime

from .config import REPORTS_DIR


def report_basename(role_name: str) -> str:
    """Build a safe, timestamped path stem (no extension) for a report.

    e.g. "Talent Strategist" -> "reports/20260705_143000_Talent_Strategist"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in role_name)
    safe = safe[:40].strip().replace(" ", "_")
    return f"{REPORTS_DIR}/{timestamp}_{safe}"
