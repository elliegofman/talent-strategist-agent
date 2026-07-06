"""Tests for the tolerant JSON parsing used in requirement extraction/scoring."""
from __future__ import annotations

from talent_strategist.steps import parse_requirements_json


def test_parses_plain_json():
    assert parse_requirements_json('{"role_title": "X"}') == {"role_title": "X"}


def test_parses_json_wrapped_in_prose():
    raw = 'Here you go:\n{"a": 1, "b": [1, 2]}\nHope that helps!'
    assert parse_requirements_json(raw) == {"a": 1, "b": [1, 2]}


def test_parses_json_in_code_fence():
    raw = '```json\n{"ok": true}\n```'
    assert parse_requirements_json(raw) == {"ok": True}


def test_returns_none_on_garbage():
    assert parse_requirements_json("no json here at all") is None
    assert parse_requirements_json("{not valid json}") is None
