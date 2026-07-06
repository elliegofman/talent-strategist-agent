"""Prompt templates for each stage of the pipeline.

Keeping prompt text separate from the orchestration logic makes both easier to
read and to tune independently.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def research_candidate(candidate_text: str) -> str:
    return f"""You are a Talent Strategist researching a candidate's background.

Here is the candidate's background:
{candidate_text}

Your task:
1. Identify the candidate's most recent company and role
2. Search for information about that company — what they do, size, stage, recent news
3. Search for the candidate's industry context — trends, skills in demand
4. Summarize your findings in 3-4 paragraphs that would help a recruiter understand this candidate's context

Be specific and factual. Include company details, industry positioning, and any relevant context about the candidate's likely skill set based on their background."""


def research_role(role_text: str) -> str:
    return f"""You are a Talent Strategist researching a role to understand its market context.

Here is the role description:
{role_text}

Your task:
1. Search for similar roles at peer companies — what do they look for, what do they pay?
2. Search for the talent market for this type of role — is it competitive? What skills are most valued?
3. Search for the hiring company's recent news and strategic priorities
4. Summarize your findings in 3-4 paragraphs covering: role market context, compensation benchmarks (if available), and what top candidates typically look like

Be specific. Name peer companies, cite actual data where possible."""


def extract_requirements(role_text: str) -> str:
    return f"""Extract the key requirements from this role description.

Role description:
{role_text}

Return a JSON object with this exact structure (no markdown, no explanation, just JSON):
{{
    "role_title": "the role title",
    "company": "the company name",
    "requirements": [
        {{
            "category": "technical" or "experience" or "soft_skill" or "domain",
            "requirement": "concise description, max 10 words",
            "importance": "must_have" or "nice_to_have"
        }}
    ]
}}

Extract 5-8 requirements. Be specific — "3+ years in enterprise sales" not "experience"."""


def build_scorecard(
    candidate_text: str,
    role_text: str,
    candidate_research: str,
    role_research: str,
    requirements: dict[str, Any],
) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    return f"""You are a senior Talent Strategist building a candidate evaluation scorecard.

## Inputs

### Role description
{role_text}

### Extracted requirements
{json.dumps(requirements, indent=2)}

### Candidate background
{candidate_text}

### Research on candidate's company/industry
{candidate_research}

### Research on role market context
{role_research}

## Your task

Produce a comprehensive evaluation scorecard in clean markdown format. Use this exact structure:

# Candidate Fit Scorecard: [candidate's full name]

**Candidate:** [candidate's full name, taken from their background]
**Role:** [role title] at [company]
**Date:** {today}

## Summary
[A quick at-a-glance table. Fill every cell concisely.]

| | |
|---|---|
| **Overall fit** | [Strong / Moderate / Weak] |
| **Fit score** | [0-100, your holistic score] |
| **Top strength** | [the single strongest point, ≤12 words] |
| **Top risk** | [the single biggest concern, ≤12 words] |
| **Recommendation** | [Advance / Hold / Pass] |

## Executive summary
[2-3 sentences on overall fit. Be direct — not generic praise.]

## Requirement match

| Requirement | Match | Evidence |
|---|---|---|
[One row per requirement. Match = Strong ✅ / Partial ⚠️ / Gap ❌. Evidence = specific, 1-sentence.]

## Strengths
[3-4 bullet points. Each must cite specific evidence from the candidate's background.]

## Risk flags
[2-4 bullet points. Be honest about genuine gaps or concerns. Each flag should be specific enough to investigate.]

## Interview probe questions
[5 sharp behavioral or case questions designed to test the gaps and validate the strengths you identified. Each should be specific to THIS candidate and THIS role — not generic interview questions. Include a brief note on what a strong answer would demonstrate.]

## Sourcing notes
[1-2 sentences on where to find similar candidates if this one doesn't work out, based on your market research.]

---

Be brutally honest. A scorecard that says "strong fit" on everything is useless. The hiring manager wants to know where to probe and what to worry about."""


def score_scorecard(scorecard_md: str) -> str:
    return f"""Here is a candidate evaluation scorecard:

{scorecard_md}

Extract its key judgments as JSON (no markdown, no prose, just the object):
{{
    "fit_score": <integer 0-100 — use the scorecard's Fit score if present, else infer>,
    "overall_fit": "Strong" or "Moderate" or "Weak",
    "recommendation": "Advance" or "Hold" or "Pass",
    "top_strength": "<the single strongest point, <=12 words>",
    "top_risk": "<the single biggest concern, <=12 words>"
}}"""


def compare_candidates(header_role: str, summaries: str) -> str:
    return f"""You are a hiring manager choosing between candidates for {header_role}.

Below are their scorecards, already ranked by fit score:

{summaries}

Write a concise recommendation (in markdown) with exactly these sections:

## Recommendation
[2-3 sentences: who to advance and why they beat the others. Name the top candidate explicitly.]

## Why not the others
[One bullet per remaining candidate: the specific reason they ranked lower. Be direct.]

## If you could only interview two
[Name the two you'd bring in and one sentence on what each interview should test.]

Be decisive and specific. Reference concrete evidence from the scorecards."""
