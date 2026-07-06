"""Tests for the ReportLab PDF rendering helpers."""
from __future__ import annotations

from reportlab.platypus import Table

from talent_strategist.pdf import (
    COLUMN_RATIOS,
    _inline,
    _markdown_to_flowables,
    save_report_pdf,
)


def test_inline_strips_emoji_and_bolds():
    assert _inline("**Strong** ✅") == "<b>Strong</b>"
    assert "🥇" not in _inline("🥇 1")


def test_inline_escapes_xml():
    assert _inline("a < b & c > d") == "a &lt; b &amp; c &gt; d"


def test_column_ratios_sum_to_one():
    for cols, ratios in COLUMN_RATIOS.items():
        assert len(ratios) == cols
        assert abs(sum(ratios) - 1.0) < 1e-9


def test_markdown_table_becomes_reportlab_table():
    md = "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    flowables = _markdown_to_flowables(md, content_width=400)
    assert any(isinstance(f, Table) for f in flowables)


def test_save_report_pdf_writes_a_pdf(tmp_path, monkeypatch):
    # Redirect the reports directory into a temp folder for the test.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reports").mkdir()
    path = save_report_pdf("# Scorecard\n\n| Overall fit | Moderate |\n|---|---|\n", "Test Role")
    data = (tmp_path / path).read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 500
