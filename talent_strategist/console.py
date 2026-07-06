"""Helpers for printing pipeline progress to the console."""
from __future__ import annotations

_RULE = "─" * 60


def print_step(step: object, total: object, message: str) -> None:
    """Print a header marking a major pipeline step."""
    print(f"\n{_RULE}")
    print(f"  Step {step}/{total}: {message}")
    print(f"{_RULE}\n")


def print_substep(message: str) -> None:
    """Print a sub-action within a step."""
    print(f"    → {message}")
