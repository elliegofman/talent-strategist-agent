"""Render a markdown report to a formatted PDF using ReportLab.

We parse our own (small, predictable) markdown into ReportLab "flowables" —
headings, paragraphs, bullet lists, and real Tables with explicit column widths.
ReportLab's table engine draws proper side-by-side columns and wraps text inside
each cell, so columns never overlap (the failure mode of HTML-to-PDF converters).
"""
from __future__ import annotations

import os
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .config import REPORTS_DIR
from .paths import report_basename

# Column-width ratios by number of columns (each list sums to 1.0). Common report
# shapes are hand-tuned; any other column count is split evenly.
COLUMN_RATIOS = {
    2: [0.28, 0.72],                                 # summary "label | value"
    3: [0.34, 0.12, 0.54],                           # requirement | match | evidence
    7: [0.06, 0.22, 0.11, 0.12, 0.16, 0.17, 0.16],   # comparison ranking
}

# Emojis the built-in PDF fonts can't render (they show as ■ boxes). The adjacent
# words carry the meaning, so we simply drop them.
_UNRENDERABLE = ("✅", "⚠️", "⚠", "❌", "🥇")

_BOLD = re.compile(r"\*\*(.+?)\*\*")


def save_report_pdf(content: str, role_name: str) -> str:
    """Write ``content`` (markdown) to a formatted PDF and return its path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{report_basename(role_name)}.pdf"

    margin = 1.5 * cm
    content_width = letter[0] - 2 * margin

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title="Candidate Scorecard",
    )
    doc.build(_markdown_to_flowables(content, content_width))
    return filename


def _inline(text: str) -> str:
    """Prepare a line of markdown for a ReportLab Paragraph.

    Strips unrenderable emojis, escapes XML-special characters, and converts
    ``**bold**`` to ``<b>`` markup.
    """
    for emoji in _UNRENDERABLE:
        text = text.replace(emoji, "")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _BOLD.sub(r"<b>\1</b>", text)
    return text.strip()


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def _is_table_separator(line: str) -> bool:
    cells = line.strip().strip("|").split("|")
    return all(set(c.strip()) <= set("-: ") and "-" in c for c in cells)


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=6)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    return {
        "body": body,
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=18, leading=22, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, leading=16,
                              spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#222222")),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontSize=11, leading=14,
                             spaceBefore=8, spaceAfter=2),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3),
        "quote": ParagraphStyle("quote", parent=body, leftIndent=14,
                                textColor=colors.HexColor("#555555"), fontName="Helvetica-Oblique"),
        "cell": cell,
        "cell_head": ParagraphStyle("cellhead", parent=cell, fontName="Helvetica-Bold"),
    }


def _markdown_to_flowables(md: str, content_width: float) -> list:
    """Turn a markdown report into an ordered list of ReportLab flowables."""
    st = _styles()
    flow: list = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Tables: gather consecutive pipe rows.
        if _is_table_row(line):
            rows = []
            while i < len(lines) and _is_table_row(lines[i]):
                if not _is_table_separator(lines[i]):
                    rows.append(_split_row(lines[i]))
                i += 1
            flow.append(_build_table(rows, content_width, st))
            flow.append(Spacer(1, 8))
            continue

        if stripped.startswith("# "):
            flow.append(Paragraph(_inline(stripped[2:]), st["h1"]))
            flow.append(HRFlowable(width="100%", thickness=1.2,
                                   color=colors.HexColor("#333333"), spaceBefore=2, spaceAfter=8))
        elif stripped.startswith("## "):
            flow.append(Paragraph(_inline(stripped[3:]), st["h2"]))
        elif stripped.startswith("### "):
            flow.append(Paragraph(_inline(stripped[4:]), st["h3"]))
        elif stripped in ("---", "***", "___"):
            flow.append(HRFlowable(width="100%", thickness=0.5,
                                   color=colors.HexColor("#dddddd"), spaceBefore=6, spaceAfter=6))
        elif stripped.startswith(("- ", "* ")):
            flow.append(Paragraph(_inline(stripped[2:]), st["bullet"], bulletText="•"))
        elif stripped.startswith("> "):
            flow.append(Paragraph(_inline(stripped[2:]), st["quote"]))
        else:
            flow.append(Paragraph(_inline(stripped), st["body"]))
        i += 1

    return flow


def _build_table(rows: list[list[str]], content_width: float, st: dict) -> Table:
    """Build a ReportLab Table with explicit column widths so columns never overlap."""
    n_cols = max(len(r) for r in rows)
    rows = [r + [""] * (n_cols - len(r)) for r in rows]  # normalise widths

    ratios = COLUMN_RATIOS.get(n_cols, [1.0 / n_cols] * n_cols)
    col_widths = [content_width * r for r in ratios]

    data = [
        [Paragraph(_inline(c), st["cell_head"] if row_idx == 0 else st["cell"]) for c in row]
        for row_idx, row in enumerate(rows)
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table
