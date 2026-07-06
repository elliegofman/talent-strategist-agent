"""Tests for candidate input handling and name extraction."""
from __future__ import annotations

import pytest

from talent_strategist.candidates import (
    candidate_name_from_path,
    candidate_name_from_text,
    read_candidates,
    read_file,
)
from talent_strategist.errors import AgentError


def test_name_from_text_cuts_at_separator():
    assert candidate_name_from_text("Jordan Kim — Operations Pro", "fb") == "Jordan Kim"
    assert candidate_name_from_text("Priya Nair | Recruiter", "fb") == "Priya Nair"
    assert candidate_name_from_text("Marcus Bell, Strategy", "fb") == "Marcus Bell"


def test_name_from_text_falls_back_when_not_a_name():
    long_line = "A very long first line that is clearly not a person's name at all"
    assert candidate_name_from_text(long_line, "Fallback") == "Fallback"
    assert candidate_name_from_text("", "Fallback") == "Fallback"
    assert candidate_name_from_text("Name", "Fallback") == "Fallback"


def test_name_from_path():
    assert candidate_name_from_path("examples/jane_doe.txt") == "Jane Doe"
    assert candidate_name_from_path("my_candidate.txt") == "Candidate"


def test_read_candidates_dedupes_names(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("Alex Smith — Engineer\nExperience...")
    b.write_text("Alex Smith — Designer\nExperience...")
    result = read_candidates([str(a), str(b)])
    names = [name for name, _ in result]
    assert names == ["Alex Smith", "Alex Smith (2)"]


def test_read_file_missing_raises_agenterror():
    with pytest.raises(AgentError):
        read_file("/no/such/file.txt", "Role")
