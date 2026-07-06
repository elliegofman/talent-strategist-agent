# Talent Strategist Agent

[![CI](https://github.com/elliegofman/talent-strategist-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/elliegofman/talent-strategist-agent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

An autonomous candidate-evaluation agent built on the [Claude API](https://docs.anthropic.com/).
Give it a job description and one or more résumés; it independently researches both
using live web search, maps each candidate against the role's requirements, and
produces a structured hiring scorecard — fit score, strengths, risk flags, and
tailored interview questions. With multiple candidates, it ranks them and
recommends who to hire.

The key difference from a single chatbot prompt: the agent decides **what** to
research and **when**. It's goal-directed, not prompt-directed.

---

## What it produces

- **Fit scorecard** — an at-a-glance summary table, requirement-by-requirement
  match, strengths, honest risk flags, and 5 tailored interview questions.
- **Candidate comparison** (multi-candidate mode) — a ranked table with fit
  scores plus a decisive recommendation on who to advance and why.
- Output is saved as clean **Markdown**, with optional **PDF** export.

---

## How it works

A four-step pipeline where each step feeds the next:

```
Role + Candidate text
        │
   [1] Research candidate  ──►  live web search: their company, industry context
        │
   [2] Research role       ──►  live web search: comp benchmarks, peer companies
        │
   [3] Extract requirements ─►  structured JSON of must-haves / nice-to-haves
        │
   [4] Build scorecard     ──►  synthesis of everything into a Markdown report
```

Steps 1 and 2 use Claude's server-side `web_search` tool — Claude formulates its
own queries. Because each step's output becomes the next step's context, the
final scorecard is grounded in real research. In comparison mode the role is
researched **once** and reused across all candidates.

---

## Install

Requires Python 3.9+ and an [Anthropic API key](https://console.anthropic.com).

```bash
python3 -m venv .venv
.venv/bin/pip install -e .        # or: make install
export ANTHROPIC_API_KEY=your_key_here
```

---

## Usage

The agent can be run three equivalent ways: `talent-strategist` (installed
command), `python -m talent_strategist`, or `python agent.py`.

```bash
# Single candidate
talent-strategist --role examples/sample_role.txt --candidate examples/sample_candidate.txt

# Compare several candidates (ranks them, recommends the best fit)
talent-strategist --role examples/sample_role.txt \
  --candidates examples/sample_candidate.txt examples/sample_candidate_2.txt examples/sample_candidate_3.txt

# Export a PDF alongside the Markdown
talent-strategist --role examples/sample_role.txt --candidate examples/sample_candidate.txt --pdf

# Fast / offline mode (skips web research — faster and cheaper for testing)
talent-strategist --role examples/sample_role.txt --candidate examples/sample_candidate.txt --no-search
```

To evaluate your own role/candidate, copy the templates in `examples/`
(`TEMPLATE_role.txt`, `TEMPLATE_candidate.txt`) and fill them in. Reports are
written to `reports/`.

---

## CLI reference

| Flag | Description |
|---|---|
| `--role PATH` | Path to the role description file |
| `--candidate PATH` | Path to a single candidate file |
| `--candidates PATH...` | Two or more candidate files — ranks them side by side |
| `--pdf` | Also save a formatted PDF |
| `--no-search` | Skip web research for faster, cheaper, offline runs |

---

## Project layout

```
talent_strategist/          # the package
├── cli.py                  # argument parsing and dispatch
├── pipeline.py             # single-candidate and comparison orchestration
├── steps.py                # the four pipeline steps + scoring
├── prompts.py              # prompt templates (separated from logic)
├── llm.py                  # Anthropic client wrapper: retries, web search
├── pdf.py                  # ReportLab PDF rendering
├── storage.py / paths.py   # saving reports
├── candidates.py           # input handling + name extraction
├── console.py, config.py, errors.py
tests/                      # pytest suite
examples/                   # sample role + candidate files, and templates
agent.py                    # backwards-compatible entry point
pyproject.toml              # packaging + dependencies
```

---

## Development

```bash
make dev     # create venv + install with dev dependencies
make test    # run the pytest suite
make run     # run against the bundled sample files
```

Tests cover name extraction, tolerant JSON parsing, PDF rendering, and CLI
validation, and run in CI on Python 3.9 / 3.11 / 3.12.

---

## Notes

- Web search is a server-side tool: the Claude API runs the search and returns
  results in the response — no separate search API or client-side tool loop.
- The agent is intentionally **candid** — it surfaces genuine gaps and risks
  rather than rubber-stamping every candidate.
