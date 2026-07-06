"""Orchestration: the single-candidate pipeline and the multi-candidate comparison."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import anthropic

from . import steps
from .config import NO_SEARCH_PLACEHOLDER
from .console import print_step, print_substep
from .errors import AgentError
from .llm import call_simple
from .prompts import compare_candidates
from .storage import save_outputs

_BANNER = "═" * 60


def _require_api_key() -> None:
    """Fail early with a clear message if the API key isn't set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AgentError(
            "ANTHROPIC_API_KEY is not set.\n"
            "    Set it with:  export ANTHROPIC_API_KEY=your_key_here\n"
            "    Get a key at: https://console.anthropic.com"
        )


def _research_role_once(client, role_text: str, no_search: bool = False):
    """Steps 2 & 3 — role-level work that's identical for every candidate."""
    if no_search:
        role_research = NO_SEARCH_PLACEHOLDER
        print_substep("Skipping role research (--no-search)")
    else:
        print_step("R", "role", "Researching role market context")
        role_research = steps.research_role(client, role_text)
        print_substep("Done — role market context gathered")

    print_step("R", "role", "Extracting structured requirements")
    requirements = steps.extract_requirements(client, role_text)
    print_substep(f"Done — extracted {len(requirements.get('requirements', []))} requirements")
    return role_research, requirements


def _scorecard_for_candidate(client, candidate_text, role_text, role_research,
                             requirements, no_search: bool = False):
    """Steps 1 & 4 — the per-candidate work. Returns (scorecard_md, score_dict)."""
    if no_search:
        candidate_research = NO_SEARCH_PLACEHOLDER
    else:
        candidate_research = steps.research_candidate(client, candidate_text)
    scorecard = steps.build_scorecard(
        client, candidate_text, role_text, candidate_research, role_research, requirements
    )
    score = steps.extract_fit_score(client, scorecard)
    return scorecard, score


def run_pipeline(role_text: str, candidate_text: str,
                 make_pdf: bool = False, no_search: bool = False):
    """Run the full four-step analysis pipeline for a single candidate."""
    _require_api_key()
    client = anthropic.Anthropic()

    print("\n" + _BANNER)
    print("  TALENT STRATEGIST AGENT")
    print("  Autonomous candidate-role fit analysis")
    if no_search:
        print("  (--no-search: skipping web research)")
    print(_BANNER)

    if no_search:
        print_substep("Skipping candidate & role research (--no-search)")
        candidate_research = NO_SEARCH_PLACEHOLDER
        role_research = NO_SEARCH_PLACEHOLDER
    else:
        print_step(1, 4, "Researching candidate background")
        candidate_research = steps.research_candidate(client, candidate_text)
        print_substep("Done — candidate context gathered")

        print_step(2, 4, "Researching role market context")
        role_research = steps.research_role(client, role_text)
        print_substep("Done — role market context gathered")

    print_step(3, 4, "Extracting structured requirements")
    requirements = steps.extract_requirements(client, role_text)
    print_substep(f"Done — extracted {len(requirements.get('requirements', []))} requirements")

    print_step(4, 4, "Synthesizing final scorecard")
    scorecard = steps.build_scorecard(
        client, candidate_text, role_text, candidate_research, role_research, requirements
    )

    role_name = requirements.get("role_title", "analysis")
    md_path, pdf_path = save_outputs(scorecard, role_name, make_pdf)

    print("\n" + _BANNER)
    print("  ✓ SCORECARD COMPLETE")
    print(f"  Saved to: {md_path}")
    if pdf_path:
        print(f"  PDF:      {pdf_path}")
    print(_BANNER + "\n")
    print(scorecard)
    return scorecard, md_path


def run_comparison(role_text: str, candidates: list[tuple[str, str]],
                   make_pdf: bool = False, no_search: bool = False):
    """Evaluate several candidates against one role and rank them.

    ``candidates`` is a list of (name, text) tuples. The role is researched once
    and reused, then each candidate is scored and ranked.
    """
    _require_api_key()
    client = anthropic.Anthropic()

    print("\n" + _BANNER)
    print("  TALENT STRATEGIST AGENT — Candidate Comparison")
    print(f"  Comparing {len(candidates)} candidates for one role")
    if no_search:
        print("  (--no-search: skipping web research)")
    print(_BANNER)

    role_research, requirements = _research_role_once(client, role_text, no_search=no_search)

    results: list[dict[str, Any]] = []
    for i, (name, text) in enumerate(candidates, 1):
        print_step(i, len(candidates), f"Evaluating candidate: {name}")
        scorecard, score = _scorecard_for_candidate(
            client, text, role_text, role_research, requirements, no_search=no_search
        )
        md_path, _ = save_outputs(scorecard, f"{name}_scorecard", make_pdf=False)
        results.append({"name": name, "scorecard": scorecard, "score": score, "path": md_path})
        print_substep(f"Done — fit score {score.get('fit_score', '?')}/100")

    results.sort(key=lambda r: r["score"].get("fit_score", 0), reverse=True)

    print_step("★", "compare", "Building side-by-side comparison")
    report = _build_comparison_report(client, requirements, results)
    role_name = requirements.get("role_title", "role")
    md_path, pdf_path = save_outputs(report, f"COMPARISON_{role_name}", make_pdf, label="comparison")

    print("\n" + _BANNER)
    print("  ✓ COMPARISON COMPLETE")
    print(f"  Winner:   {results[0]['name']} ({results[0]['score'].get('fit_score', '?')}/100)")
    print(f"  Saved to: {md_path}")
    if pdf_path:
        print(f"  PDF:      {pdf_path}")
    print(_BANNER + "\n")
    print(report)
    return report, md_path


def _build_comparison_report(client, requirements: dict[str, Any], ranked: list[dict]) -> str:
    """Assemble the comparison markdown: a ranking table plus a written rationale."""
    role_title = requirements.get("role_title", "the role")
    company = requirements.get("company", "")
    header_role = role_title + (f" at {company}" if company and company != "Unknown" else "")

    lines = [
        "# Candidate Comparison",
        "",
        f"**Role:** {header_role}",
        f"**Date:** {datetime.now().strftime('%B %d, %Y')}",
        f"**Candidates compared:** {len(ranked)}",
        "",
        "## Ranking",
        "",
        "| Rank | Candidate | Fit score | Overall | Recommendation | Top strength | Top risk |",
        "|---|---|---|---|---|---|---|",
    ]
    for rank, r in enumerate(ranked, 1):
        s = r["score"]
        medal = "🥇 " if rank == 1 else ""
        lines.append(
            f"| {medal}{rank} | {r['name']} | {s.get('fit_score', '?')}/100 | "
            f"{s.get('overall_fit', '?')} | {s.get('recommendation', '?')} | "
            f"{s.get('top_strength', '—')} | {s.get('top_risk', '—')} |"
        )

    summaries = "\n\n".join(
        f"### {r['name']} (fit {r['score'].get('fit_score', '?')}/100)\n{r['scorecard']}"
        for r in ranked
    )
    recommendation = call_simple(
        client, compare_candidates(header_role, summaries), "Writing final recommendation"
    )

    lines += ["", recommendation, "", "---", "", "## Individual scorecards saved", ""]
    lines += [f"- **{r['name']}** — {r['path']}" for r in ranked]
    return "\n".join(lines)
