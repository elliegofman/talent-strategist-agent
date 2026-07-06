"""Tests for CLI argument validation (no API calls)."""
from __future__ import annotations

import pytest

from talent_strategist.cli import build_parser, main


def test_parser_accepts_comparison_flags():
    args = build_parser().parse_args(
        ["--role", "r.txt", "--candidates", "a.txt", "b.txt", "--pdf", "--no-search"]
    )
    assert args.role == "r.txt"
    assert args.candidates == ["a.txt", "b.txt"]
    assert args.pdf and args.no_search


@pytest.mark.parametrize("argv", [
    ["--role", "r.txt"],                                   # candidate missing
    ["--candidate", "c.txt"],                              # role missing
    ["--role", "r.txt", "--candidates", "only_one.txt"],   # need >= 2
    ["--candidates", "a.txt", "b.txt"],                    # role missing
])
def test_invalid_usage_exits_cleanly(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 1
    # A friendly message, not a traceback.
    assert "✗" in capsys.readouterr().out
