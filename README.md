# Talent Strategist Agent

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
  match, strengths, honest risk flags, and 5 interview questions tailored to the
  specific candidate and role.
- **Candidate comparison** (multi-candidate mode) — a ranked table with fit
  scores plus a decisive recommendation on who to advance and why.
- Output is saved as clean **Markdown**, with optional **PDF** export.

---

## How it works

A four-step sequential pipeline where each step feeds the next:

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
own queries based on the inputs. Because each step's output becomes the next
step's context, the final scorecard is grounded in real research rather than
pattern-matching on the input text.

In comparison mode, the role is researched **once** and reused across all
candidates for efficiency, then each candidate is scored and ranked.

---

## Setup

Requires Python 3.9+ and an [Anthropic API key](https://console.anthropic.com).

```bash
# 1. Install dependencies (in a virtual environment)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Set your API key
export ANTHROPIC_API_KEY=your_key_here
```

---

## Usage

**Single candidate:**
```bash
python agent.py --role examples/sample_role.txt --candidate examples/sample_candidate.txt
```

**Compare several candidates (ranks them, recommends the best fit):**
```bash
python agent.py --role examples/sample_role.txt \
  --candidates examples/sample_candidate.txt examples/sample_candidate_2.txt examples/sample_candidate_3.txt
```

**Export a PDF alongside the Markdown:**
```bash
python agent.py --role examples/sample_role.txt --candidate examples/sample_candidate.txt --pdf
```

**Fast / offline mode (skips web research — faster and cheaper for testing):**
```bash
python agent.py --role examples/sample_role.txt --candidate examples/sample_candidate.txt --no-search
```

**Interactive mode (paste inputs at the prompt):**
```bash
python agent.py
```

Reports are written to `reports/`. To evaluate your own role/candidate, copy the
templates in `examples/` (`TEMPLATE_role.txt`, `TEMPLATE_candidate.txt`) and fill
them in.

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

## Project structure

```
talent-strategist-agent/
├── agent.py            # the agent (single file)
├── requirements.txt    # Python dependencies
├── examples/           # sample role + candidate files, and templates
├── reports/            # generated scorecards land here
├── README.md           # this file
├── CLAUDE.md           # project notes / architecture
└── SETUP_GUIDE.md      # detailed setup and usage walkthrough
```

---

## Notes

- Web search is a server-side tool: the Claude API runs the search and returns
  results in the response — no separate search API or client-side tool loop is
  needed.
- The agent is intentionally **candid** — it surfaces genuine gaps and risks
  rather than rubber-stamping every candidate.
- Built and iteratively extended using Claude Code.
