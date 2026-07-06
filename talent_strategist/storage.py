"""Persisting reports to disk (markdown always, PDF optionally)."""
from __future__ import annotations

import os
from typing import Optional

from .config import REPORTS_DIR
from .console import print_substep
from .paths import report_basename
from .pdf import save_report_pdf


def save_report(content: str, role_name: str) -> str:
    """Save ``content`` as a markdown file in the reports directory."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{report_basename(role_name)}.md"
    with open(filename, "w") as fh:
        fh.write(content)
    return filename


def save_outputs(
    content: str, role_name: str, make_pdf: bool, label: str = "report"
) -> tuple[str, Optional[str]]:
    """Save markdown (always) and optionally a PDF. Returns (md_path, pdf_path)."""
    md_path = save_report(content, role_name)
    pdf_path: Optional[str] = None
    if make_pdf:
        print_substep(f"Generating PDF version of {label}")
        try:
            pdf_path = save_report_pdf(content, role_name)
        except Exception as exc:  # PDF is a nice-to-have; never fail the whole run
            print(f"    ⚠ Could not create PDF ({exc}) — markdown still saved")
    return md_path, pdf_path
