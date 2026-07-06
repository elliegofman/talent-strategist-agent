"""Talent Strategist Agent — autonomous candidate-role fit analysis.

An agent that researches a role and candidate(s) with live web search, then
produces a structured hiring scorecard and (for multiple candidates) a ranked
comparison.
"""
from __future__ import annotations

from .errors import AgentError
from .pipeline import run_comparison, run_pipeline

__version__ = "1.0.0"
__all__ = ["run_pipeline", "run_comparison", "AgentError", "__version__"]
