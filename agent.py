"""
Talent Strategist Agent
-----------------------
An autonomous candidate-role fit analysis tool.

This agent takes a role description and a candidate background,
researches both using web search, then produces a structured
scorecard with fit analysis, risk flags, and interview probe questions.

Usage:
    python agent.py                           # interactive mode
    python agent.py --role role.txt --candidate candidate.txt
"""

import anthropic
import json
import os
import sys
import time
import argparse
from datetime import datetime


# ── Configuration ──────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
REPORTS_DIR = "reports"
MAX_RETRIES = 2          # how many times to retry a failed API call
RETRY_WAIT_SECONDS = 3   # base wait between retries (grows each attempt)

# Shown in place of live research when running with --no-search.
NO_SEARCH_PLACEHOLDER = "(Web research skipped — run without --no-search for live market context.)"


class AgentError(Exception):
    """A clear, user-facing error that should stop the run with a friendly message."""
    pass


# ── Utilities ──────────────────────────────────────────────────

def print_step(step_num, total, message):
    """Print a clear status line showing progress through the pipeline."""
    print(f"\n{'─' * 60}")
    print(f"  Step {step_num}/{total}: {message}")
    print(f"{'─' * 60}\n")


def print_substep(message):
    """Print a sub-action within a step."""
    print(f"    → {message}")


def _report_basename(role_name):
    """Build a safe, timestamped filename base (no extension) for a report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in role_name)[:40].strip().replace(" ", "_")
    return f"{REPORTS_DIR}/{timestamp}_{safe_name}"


def save_report(content, role_name):
    """Save the final scorecard as a markdown file in reports/."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{_report_basename(role_name)}.md"
    with open(filename, "w") as f:
        f.write(content)
    return filename


def save_report_pdf(content, role_name):
    """
    Save the scorecard as a nicely formatted PDF in reports/.

    Built directly with ReportLab (pure-Python, no system dependencies). We
    parse our own markdown into ReportLab "flowables" — headings, paragraphs,
    bullet lists, and real Tables with explicit column widths. ReportLab's table
    engine draws proper side-by-side columns and wraps text inside each cell, so
    columns never overlap (the failure mode of HTML-to-PDF converters here).
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filename = f"{_report_basename(role_name)}.pdf"

    margin = 1.5 * cm
    content_width = letter[0] - 2 * margin  # usable width for tables

    doc = SimpleDocTemplate(
        filename, pagesize=letter,
        leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin,
        title="Candidate Scorecard",
    )
    flowables = _markdown_to_flowables(content, content_width)
    doc.build(flowables)
    return filename


# Column-width ratios by number of columns (must sum to 1.0). Common report
# shapes are hand-tuned; anything else is split evenly in the code below.
_COLUMN_RATIOS = {
    2: [0.28, 0.72],                              # summary "label | value"
    3: [0.34, 0.12, 0.54],                        # requirement | match | evidence
    7: [0.06, 0.22, 0.11, 0.12, 0.16, 0.17, 0.16],  # comparison ranking
}


def _pdf_inline(text):
    """Prepare a line of markdown text for a ReportLab Paragraph.

    Escapes XML-special characters, converts **bold** to <b>, strips emojis the
    PDF font can't render, and drops leading markdown bullet/blockquote markers.
    """
    for emoji in ("✅", "⚠️", "⚠", "❌", "🥇"):
        text = text.replace(emoji, "")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold: **x** -> <b>x</b>  (done after escaping so the tags survive)
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text.strip()


def _is_table_row(line):
    return line.strip().startswith("|") and line.strip().endswith("|")


def _is_table_separator(line):
    # e.g. |---|:--:|---|  — only dashes, colons, pipes, spaces
    cells = line.strip().strip("|").split("|")
    return all(set(c.strip()) <= set("-: ") and "-" in c for c in cells)


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _markdown_to_flowables(md, content_width):
    """Turn our markdown report into an ordered list of ReportLab flowables."""
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable

    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=14, spaceAfter=6)
    h1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=18, leading=22, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, leading=16,
                        spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#222222"))
    h3 = ParagraphStyle("h3", parent=base["Heading3"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=2)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)
    quote = ParagraphStyle("quote", parent=body, leftIndent=14, textColor=colors.HexColor("#555555"),
                           fontName="Helvetica-Oblique")
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    cell_head = ParagraphStyle("cellhead", parent=cell, fontName="Helvetica-Bold")

    flow = []
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
            flow.append(_build_table(rows, content_width, colors, Paragraph, Table, TableStyle,
                                     cell, cell_head))
            flow.append(Spacer(1, 8))
            continue

        # Headings
        if stripped.startswith("# "):
            flow.append(Paragraph(_pdf_inline(stripped[2:]), h1))
            flow.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#333333"),
                                   spaceBefore=2, spaceAfter=8))
        elif stripped.startswith("## "):
            flow.append(Paragraph(_pdf_inline(stripped[3:]), h2))
        elif stripped.startswith("### "):
            flow.append(Paragraph(_pdf_inline(stripped[4:]), h3))
        elif stripped in ("---", "***", "___"):
            flow.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"),
                                   spaceBefore=6, spaceAfter=6))
        elif stripped.startswith(("- ", "* ")):
            flow.append(Paragraph(_pdf_inline(stripped[2:]), bullet, bulletText="•"))
        elif stripped.startswith("> "):
            flow.append(Paragraph(_pdf_inline(stripped[2:]), quote))
        else:
            flow.append(Paragraph(_pdf_inline(stripped), body))
        i += 1

    return flow


def _build_table(rows, content_width, colors, Paragraph, Table, TableStyle, cell, cell_head):
    """Build a ReportLab Table with explicit column widths so columns never overlap."""
    n_cols = max(len(r) for r in rows)
    # Normalise every row to the same column count.
    rows = [r + [""] * (n_cols - len(r)) for r in rows]

    ratios = _COLUMN_RATIOS.get(n_cols, [1.0 / n_cols] * n_cols)
    col_widths = [content_width * r for r in ratios]

    # Wrap each cell's text in a Paragraph so it wraps within its column.
    data = []
    for row_idx, row in enumerate(rows):
        style = cell_head if row_idx == 0 else cell
        data.append([Paragraph(_pdf_inline(c), style) for c in row])

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


# ── Agent Core ─────────────────────────────────────────────────

def _create_message(client, **kwargs):
    """
    Wrapper around client.messages.create that retries transient failures
    (rate limits, temporary network/API blips) and turns permanent failures
    (like a bad API key) into a clear AgentError instead of a raw traceback.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 2):  # e.g. 1 initial try + MAX_RETRIES
        try:
            return client.messages.create(**kwargs)
        except anthropic.AuthenticationError:
            # No point retrying a bad/missing key — fail fast with guidance.
            raise AgentError(
                "Authentication failed. Is ANTHROPIC_API_KEY set correctly?\n"
                "    Set it with:  export ANTHROPIC_API_KEY=your_key_here"
            )
        except (anthropic.RateLimitError, anthropic.APIConnectionError,
                anthropic.InternalServerError) as e:
            # Transient — wait a bit and try again.
            last_error = e
            if attempt <= MAX_RETRIES:
                wait = RETRY_WAIT_SECONDS * attempt
                print_substep(f"API issue ({type(e).__name__}); retrying in {wait}s "
                              f"[attempt {attempt}/{MAX_RETRIES}]")
                time.sleep(wait)
            continue
        except anthropic.APIError as e:
            # Other API errors — surface cleanly.
            raise AgentError(f"API error: {e}")

    raise AgentError(f"Gave up after {MAX_RETRIES} retries. Last error: {last_error}")


def call_claude_with_search(client, prompt, purpose=""):
    """
    Call Claude with web search enabled.

    web_search_20250305 is a server-side tool: the API runs the search
    itself and inserts the results as server_tool_use / web_search_tool_result
    blocks into the response, then keeps generating until it's done.
    There's no client-side tool loop to handle — one call is enough.
    """
    if purpose:
        print_substep(f"Calling Claude: {purpose}")

    # Research steps are enrichment, not the core deliverable — if search fails
    # entirely, we note it and let the pipeline continue (per project guidelines).
    try:
        response = _create_message(
            client,
            model=MODEL,
            max_tokens=4096,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
    except AgentError as e:
        print_substep(f"⚠ Research step failed ({e}); continuing without it")
        return "(Research unavailable — this step could not be completed.)"

    for block in response.content:
        if block.type == "server_tool_use" and block.name == "web_search":
            print_substep(f"Searching: {block.input.get('query', '...')}")

    return "\n".join(block.text for block in response.content if block.type == "text")


def call_claude_simple(client, prompt, purpose=""):
    """Call Claude without tools for pure synthesis/analysis tasks."""
    if purpose:
        print_substep(f"Analyzing: {purpose}")

    response = _create_message(
        client,
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return "\n".join(block.text for block in response.content if block.type == "text")


# ── Pipeline Steps ─────────────────────────────────────────────

def step_1_research_candidate(client, candidate_text):
    """Research the candidate's company and industry context."""
    prompt = f"""You are a Talent Strategist researching a candidate's background.

Here is the candidate's background:
{candidate_text}

Your task:
1. Identify the candidate's most recent company and role
2. Search for information about that company — what they do, size, stage, recent news
3. Search for the candidate's industry context — trends, skills in demand
4. Summarize your findings in 3-4 paragraphs that would help a recruiter understand this candidate's context

Be specific and factual. Include company details, industry positioning, and any relevant context about the candidate's likely skill set based on their background."""

    return call_claude_with_search(client, prompt, "Researching candidate background")


def step_2_research_role(client, role_text):
    """Research the target role's market context."""
    prompt = f"""You are a Talent Strategist researching a role to understand its market context.

Here is the role description:
{role_text}

Your task:
1. Search for similar roles at peer companies — what do they look for, what do they pay?
2. Search for the talent market for this type of role — is it competitive? What skills are most valued?
3. Search for the hiring company's recent news and strategic priorities
4. Summarize your findings in 3-4 paragraphs covering: role market context, compensation benchmarks (if available), and what top candidates typically look like

Be specific. Name peer companies, cite actual data where possible."""

    return call_claude_with_search(client, prompt, "Researching role market context")


def step_3_extract_requirements(client, role_text):
    """Extract structured requirements from the role description."""
    prompt = f"""Extract the key requirements from this role description.

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

    # Try the extraction; if the model wraps it in prose or malforms the JSON,
    # retry once with a stricter reminder before falling back. This is what
    # previously produced useless "Unknown" reports.
    raw = call_claude_simple(client, prompt, "Extracting role requirements")
    parsed = _parse_requirements_json(raw)

    if parsed is None:
        print_substep("⚠ JSON didn't parse — retrying once with a stricter prompt")
        strict_prompt = prompt + "\n\nIMPORTANT: Respond with ONLY the raw JSON object. " \
                                  "Do not include any prose, explanation, or markdown fences."
        raw = call_claude_simple(client, strict_prompt, "Re-extracting role requirements")
        parsed = _parse_requirements_json(raw)

    if parsed is None:
        print_substep("⚠ Still could not parse requirements — continuing without a structured list")
        return {"role_title": "Unknown", "company": "Unknown", "requirements": [], "raw": raw}

    return parsed


def _parse_requirements_json(raw):
    """Pull a JSON object out of the model's reply. Returns None if it can't."""
    try:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        start = cleaned.index("{")
        end = cleaned.rindex("}") + 1
        return json.loads(cleaned[start:end])
    except (json.JSONDecodeError, ValueError):
        return None


def step_4_build_scorecard(client, candidate_text, role_text, candidate_research, role_research, requirements):
    """Synthesize everything into a final scorecard."""
    prompt = f"""You are a senior Talent Strategist building a candidate evaluation scorecard.

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
**Date:** {datetime.now().strftime("%B %d, %Y")}

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

    return call_claude_simple(client, prompt, "Building final scorecard")


# ── Structured scoring (for ranking candidates) ────────────────

def extract_fit_score(client, scorecard_md):
    """
    Read a finished scorecard and pull out a machine-readable score so we can
    rank candidates. This just re-formats what the scorecard already decided,
    so it's reliable. Returns a dict with numeric score + labels.
    """
    prompt = f"""Here is a candidate evaluation scorecard:

{scorecard_md}

Extract its key judgments as JSON (no markdown, no prose, just the object):
{{
    "fit_score": <integer 0-100 — use the scorecard's Fit score if present, else infer>,
    "overall_fit": "Strong" or "Moderate" or "Weak",
    "recommendation": "Advance" or "Hold" or "Pass",
    "top_strength": "<the single strongest point, <=12 words>",
    "top_risk": "<the single biggest concern, <=12 words>"
}}"""

    raw = call_claude_simple(client, prompt, "Scoring candidate for ranking")
    parsed = _parse_requirements_json(raw)  # same tolerant JSON extractor
    if parsed is None:
        # Non-fatal: rank this candidate last rather than crashing the compare.
        return {"fit_score": 0, "overall_fit": "Unknown", "recommendation": "Hold",
                "top_strength": "—", "top_risk": "could not score"}
    return parsed


# ── Shared building blocks ─────────────────────────────────────

def _require_api_key():
    """Fail early with a clear message if the API key isn't set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise AgentError(
            "ANTHROPIC_API_KEY is not set.\n"
            "    Set it with:  export ANTHROPIC_API_KEY=your_key_here\n"
            "    Get a key at: https://console.anthropic.com"
        )


def _save_outputs(content, role_name, make_pdf, label="report"):
    """Save markdown (always) and optionally PDF; return (md_path, pdf_path)."""
    md_path = save_report(content, role_name)
    pdf_path = None
    if make_pdf:
        print_substep(f"Generating PDF version of {label}")
        try:
            pdf_path = save_report_pdf(content, role_name)
        except Exception as e:
            print(f"    ⚠ Could not create PDF ({e}) — markdown still saved")
    return md_path, pdf_path


def _research_role_once(client, role_text, no_search=False):
    """Steps 2 & 3 — role-level work that's identical for every candidate."""
    if no_search:
        role_research = NO_SEARCH_PLACEHOLDER
        print_substep("Skipping role research (--no-search)")
    else:
        print_step("R", "role", "Researching role market context")
        role_research = step_2_research_role(client, role_text)
        print_substep("Done — role market context gathered")

    print_step("R", "role", "Extracting structured requirements")
    requirements = step_3_extract_requirements(client, role_text)
    print_substep(f"Done — extracted {len(requirements.get('requirements', []))} requirements")
    return role_research, requirements


def _scorecard_for_candidate(client, candidate_text, role_text, role_research,
                             requirements, no_search=False):
    """Steps 1 & 4 — the per-candidate work. Returns (scorecard_md, score_dict)."""
    if no_search:
        candidate_research = NO_SEARCH_PLACEHOLDER
    else:
        candidate_research = step_1_research_candidate(client, candidate_text)
    scorecard = step_4_build_scorecard(
        client, candidate_text, role_text,
        candidate_research, role_research, requirements
    )
    score = extract_fit_score(client, scorecard)
    return scorecard, score


# ── Main Pipeline (single candidate) ───────────────────────────

def run_pipeline(role_text, candidate_text, make_pdf=False, no_search=False):
    """Run the full 4-step analysis pipeline for a single candidate."""
    _require_api_key()
    client = anthropic.Anthropic()

    print("\n" + "═" * 60)
    print("  TALENT STRATEGIST AGENT")
    print("  Autonomous candidate-role fit analysis")
    if no_search:
        print("  (--no-search: skipping web research)")
    print("═" * 60)

    if no_search:
        print_substep("Skipping candidate & role research (--no-search)")
        candidate_research = NO_SEARCH_PLACEHOLDER
        role_research = NO_SEARCH_PLACEHOLDER
    else:
        print_step(1, 4, "Researching candidate background")
        candidate_research = step_1_research_candidate(client, candidate_text)
        print_substep("Done — candidate context gathered")

        print_step(2, 4, "Researching role market context")
        role_research = step_2_research_role(client, role_text)
        print_substep("Done — role market context gathered")

    print_step(3, 4, "Extracting structured requirements")
    requirements = step_3_extract_requirements(client, role_text)
    print_substep(f"Done — extracted {len(requirements.get('requirements', []))} requirements")

    print_step(4, 4, "Synthesizing final scorecard")
    scorecard = step_4_build_scorecard(
        client, candidate_text, role_text,
        candidate_research, role_research, requirements
    )

    role_name = requirements.get("role_title", "analysis")
    filepath, pdf_path = _save_outputs(scorecard, role_name, make_pdf)

    print("\n" + "═" * 60)
    print("  ✓ SCORECARD COMPLETE")
    print(f"  Saved to: {filepath}")
    if pdf_path:
        print(f"  PDF:      {pdf_path}")
    print("═" * 60 + "\n")
    print(scorecard)
    return scorecard, filepath


# ── Comparison Pipeline (one role, many candidates) ────────────

def run_comparison(role_text, candidates, make_pdf=False, no_search=False):
    """
    Evaluate several candidates against one role and rank them.

    `candidates` is a list of (name, text) tuples. The role is researched once
    and reused, then each candidate is scored, then we build a side-by-side
    comparison report ranking who's best suited.
    """
    _require_api_key()
    client = anthropic.Anthropic()

    print("\n" + "═" * 60)
    print("  TALENT STRATEGIST AGENT — Candidate Comparison")
    print(f"  Comparing {len(candidates)} candidates for one role")
    if no_search:
        print("  (--no-search: skipping web research)")
    print("═" * 60)

    # Role-level work happens once.
    role_research, requirements = _research_role_once(client, role_text, no_search=no_search)

    # Evaluate each candidate, reusing the role research.
    results = []
    for i, (name, text) in enumerate(candidates, 1):
        print_step(i, len(candidates), f"Evaluating candidate: {name}")
        scorecard, score = _scorecard_for_candidate(
            client, text, role_text, role_research, requirements, no_search=no_search
        )
        # Save each candidate's individual scorecard too.
        md_path, _ = _save_outputs(scorecard, f"{name}_scorecard", make_pdf=False)
        results.append({"name": name, "scorecard": scorecard, "score": score, "path": md_path})
        print_substep(f"Done — fit score {score.get('fit_score', '?')}/100")

    # Rank highest score first.
    results.sort(key=lambda r: r["score"].get("fit_score", 0), reverse=True)

    # Build and save the comparison report.
    print_step("★", "compare", "Building side-by-side comparison")
    report = _build_comparison_report(client, requirements, results)
    role_name = requirements.get("role_title", "role")
    filepath, pdf_path = _save_outputs(report, f"COMPARISON_{role_name}", make_pdf,
                                       label="comparison")

    print("\n" + "═" * 60)
    print("  ✓ COMPARISON COMPLETE")
    print(f"  Winner:   {results[0]['name']} ({results[0]['score'].get('fit_score', '?')}/100)")
    print(f"  Saved to: {filepath}")
    if pdf_path:
        print(f"  PDF:      {pdf_path}")
    print("═" * 60 + "\n")
    print(report)
    return report, filepath


def _build_comparison_report(client, requirements, ranked):
    """Assemble the comparison markdown: ranking table + rationale."""
    role_title = requirements.get("role_title", "the role")
    company = requirements.get("company", "")
    header_role = f"{role_title}" + (f" at {company}" if company and company != "Unknown" else "")

    # Ranking table (built deterministically from the structured scores).
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

    # A short synthesized recommendation comparing the top candidates.
    summaries = "\n\n".join(
        f"### {r['name']} (fit {r['score'].get('fit_score', '?')}/100)\n{r['scorecard']}"
        for r in ranked
    )
    rec_prompt = f"""You are a hiring manager choosing between candidates for {header_role}.

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

    recommendation = call_claude_simple(client, rec_prompt, "Writing final recommendation")

    lines += ["", recommendation, "", "---", "",
              "## Individual scorecards saved",
              ""]
    for r in ranked:
        lines.append(f"- **{r['name']}** — {r['path']}")

    return "\n".join(lines)


# ── Input Handling ─────────────────────────────────────────────

def get_input_interactive():
    """Get role and candidate text interactively."""
    print("\n" + "═" * 60)
    print("  TALENT STRATEGIST AGENT — Interactive Mode")
    print("═" * 60)

    print("\nPaste the ROLE DESCRIPTION below.")
    print("(Type 'END' on a new line when done)\n")
    role_lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        role_lines.append(line)
    role_text = "\n".join(role_lines)

    print("\nPaste the CANDIDATE BACKGROUND below.")
    print("(Type 'END' on a new line when done)\n")
    candidate_lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        candidate_lines.append(line)
    candidate_text = "\n".join(candidate_lines)

    return role_text, candidate_text


def _read_file(path, label):
    """Read a text file, raising a clear AgentError if it's missing."""
    if not os.path.isfile(path):
        raise AgentError(f"{label} file not found: {path}\n"
                         f"    Check the path, or see examples/ for template files.")
    with open(path, "r") as f:
        return f.read()


def get_input_from_files(role_path, candidate_path):
    """Read role and candidate text from files, with clear errors if missing."""
    return _read_file(role_path, "Role"), _read_file(candidate_path, "Candidate")


def _candidate_name_from_path(path):
    """Fallback: turn a file path into a readable name, e.g. jane_doe.txt -> Jane Doe."""
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = stem.replace("my_candidate", "candidate")  # avoid a generic 'My Candidate'
    return stem.replace("_", " ").replace("-", " ").strip().title() or "Candidate"


def _candidate_name_from_text(text, fallback):
    """
    Pull the candidate's actual name from the top of their résumé.

    Résumés almost always lead with the person's name, often followed by a title
    after a dash or pipe (e.g. "Jordan Kim — Operations Professional"). We take
    the first non-empty line and cut it at the first such separator. If the
    result doesn't look like a name, we use the filename-based fallback.
    """
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    for sep in ("—", "–", " - ", "|", ",", "\t"):
        if sep in first_line:
            first_line = first_line.split(sep)[0].strip()
            break
    # A real name is short and isn't a placeholder heading.
    if 0 < len(first_line) <= 40 and first_line.lower() not in ("name", "candidate"):
        return first_line
    return fallback


def get_candidates_from_files(candidate_paths):
    """Read multiple candidate files into a list of (name, text) tuples."""
    candidates = []
    seen = {}
    for path in candidate_paths:
        text = _read_file(path, "Candidate")
        # Prefer the real name from the résumé; fall back to the filename.
        name = _candidate_name_from_text(text, _candidate_name_from_path(path))
        # Disambiguate duplicate display names so the report stays readable.
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        candidates.append((name, text))
    return candidates


# ── Entry Point ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Talent Strategist Agent — autonomous candidate-role fit analysis",
        epilog="Examples:\n"
               "  Single:   python agent.py --role role.txt --candidate cand.txt\n"
               "  Compare:  python agent.py --role role.txt --candidates a.txt b.txt c.txt --pdf",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--role", help="Path to role description file")
    parser.add_argument("--candidate", help="Path to a single candidate background file")
    parser.add_argument("--candidates", nargs="+",
                        help="Paths to two or more candidate files — ranks them side by side")
    parser.add_argument("--pdf", action="store_true", help="Also save a formatted PDF")
    parser.add_argument("--no-search", action="store_true",
                        help="Skip web research for faster, cheaper, offline testing")
    args = parser.parse_args()

    try:
        # --- Comparison mode: one role, several candidates ---
        if args.candidates:
            if not args.role:
                raise AgentError("--role is required when using --candidates.")
            if args.candidate:
                raise AgentError("Use either --candidate (one) or --candidates (many), not both.")
            if len(args.candidates) < 2:
                raise AgentError("--candidates needs at least two files. "
                                 "For a single candidate, use --candidate.")
            role_text = _read_file(args.role, "Role")
            candidates = get_candidates_from_files(args.candidates)
            if not role_text.strip():
                raise AgentError("The role description file is empty.")
            run_comparison(role_text, candidates, make_pdf=args.pdf, no_search=args.no_search)
            return

        # --- Single-candidate mode ---
        if bool(args.role) != bool(args.candidate):
            raise AgentError("--role and --candidate must be used together.")

        if args.role and args.candidate:
            role_text, candidate_text = get_input_from_files(args.role, args.candidate)
        else:
            role_text, candidate_text = get_input_interactive()

        if not role_text.strip() or not candidate_text.strip():
            raise AgentError("Both role description and candidate background are required.")

        run_pipeline(role_text, candidate_text, make_pdf=args.pdf, no_search=args.no_search)

    except AgentError as e:
        # Expected, user-facing problems — show a clean message, no traceback.
        print(f"\n✗ {e}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
