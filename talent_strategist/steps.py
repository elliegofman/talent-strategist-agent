"""The individual stages of the analysis pipeline.

Each step is a small function that takes the Anthropic client plus its inputs and
returns text (or structured data). They are composed by :mod:`pipeline`.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from . import prompts
from .console import print_substep
from .llm import call_simple, call_with_search


def research_candidate(client, candidate_text: str) -> str:
    """Step 1 — research the candidate's company and industry context."""
    return call_with_search(
        client, prompts.research_candidate(candidate_text),
        "Researching candidate background",
    )


def research_role(client, role_text: str) -> str:
    """Step 2 — research the target role's market context."""
    return call_with_search(
        client, prompts.research_role(role_text),
        "Researching role market context",
    )


def parse_requirements_json(raw: str) -> Optional[dict[str, Any]]:
    """Pull a JSON object out of the model's reply. Returns None if it can't."""
    try:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        return json.loads(cleaned[start:end])
    except (json.JSONDecodeError, ValueError):
        return None


def extract_requirements(client, role_text: str) -> dict[str, Any]:
    """Step 3 — extract structured requirements from the role description.

    If the model wraps its reply in prose or malforms the JSON, retry once with a
    stricter reminder before falling back to an empty structure.
    """
    prompt = prompts.extract_requirements(role_text)
    raw = call_simple(client, prompt, "Extracting role requirements")
    parsed = parse_requirements_json(raw)

    if parsed is None:
        print_substep("⚠ JSON didn't parse — retrying once with a stricter prompt")
        strict = prompt + (
            "\n\nIMPORTANT: Respond with ONLY the raw JSON object. "
            "Do not include any prose, explanation, or markdown fences."
        )
        raw = call_simple(client, strict, "Re-extracting role requirements")
        parsed = parse_requirements_json(raw)

    if parsed is None:
        print_substep("⚠ Still could not parse requirements — continuing without a structured list")
        return {"role_title": "Unknown", "company": "Unknown", "requirements": [], "raw": raw}

    return parsed


def build_scorecard(
    client,
    candidate_text: str,
    role_text: str,
    candidate_research: str,
    role_research: str,
    requirements: dict[str, Any],
) -> str:
    """Step 4 — synthesize everything into a final markdown scorecard."""
    prompt = prompts.build_scorecard(
        candidate_text, role_text, candidate_research, role_research, requirements
    )
    return call_simple(client, prompt, "Building final scorecard")


def extract_fit_score(client, scorecard_md: str) -> dict[str, Any]:
    """Read a finished scorecard and return a machine-readable score for ranking.

    This just re-formats what the scorecard already decided, so it's reliable. On
    a parse failure it returns a zero score so the candidate ranks last rather
    than crashing a comparison.
    """
    raw = call_simple(client, prompts.score_scorecard(scorecard_md), "Scoring candidate for ranking")
    parsed = parse_requirements_json(raw)
    if parsed is None:
        return {
            "fit_score": 0,
            "overall_fit": "Unknown",
            "recommendation": "Hold",
            "top_strength": "—",
            "top_risk": "could not score",
        }
    return parsed
