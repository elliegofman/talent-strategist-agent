# Talent Strategist Agent — Interview Cheat Sheet

A one-page reference to glance at before/during an interview.

---

## The 30-second pitch
"I built an autonomous candidate-evaluation agent on Claude's API. You give it a
job description and one or more résumés; it independently researches both with live
web search, maps each candidate against the role's requirements, and produces a
structured scorecard — fit score, strengths, risk flags, and tailored interview
questions. With multiple candidates it ranks them and recommends who to hire. The
key difference from a chatbot is that the agent decides *what* to research and
*when* — it's goal-directed, not prompt-directed."

---

## How it works (the pipeline)
1. **Research candidate** — live web search on their company & industry
2. **Research role** — live web search on comp benchmarks & peer companies
3. **Extract requirements** — structured JSON of must-haves / nice-to-haves
4. **Build scorecard** — synthesizes everything into a markdown report

Each step feeds the next, so the final scorecard is grounded in real research.

---

## Live demo commands
```bash
cd talent-strategist-agent

# A) Single candidate
.venv/bin/python agent.py --role examples/sample_role.txt \
  --candidate examples/sample_candidate.txt --pdf

# B) Rank multiple candidates (the wow moment)
.venv/bin/python agent.py --role examples/sample_role.txt \
  --candidates examples/sample_candidate.txt examples/sample_candidate_2.txt \
  examples/sample_candidate_3.txt --pdf

# Fast/offline backup (no web search — reliable if wifi is shaky)
.venv/bin/python agent.py --role examples/sample_role.txt \
  --candidate examples/sample_candidate.txt --no-search
```

---

## The three questions they'll ask

**"What makes it agentic?"**
> Tool use (it decides when/what to search) + multi-step planning (breaks the goal
> into a research-then-synthesize pipeline) + persistent context (each step feeds
> the next).

**"Walk me through a hard technical moment."** (your strongest card)
> The first version *looked* like it searched the web but was feeding the model a
> fake placeholder — the research was hallucinated. I realized `web_search` is a
> server-side tool where the API runs the search itself, rewrote the loop, and
> verified it made real searches. The skill was telling real behavior from
> apparent behavior.

**"What are its limitations?"** (shows maturity)
> Not wired into an ATS yet — in production you'd connect it via MCP to pull
> candidate records directly. Search quality varies, so I'd add a validation step
> where the agent checks its own research before synthesizing.

**"How is the code organized?"** (shows engineering judgment)
> I started as a single working script, then once the behavior was solid I
> restructured it into a proper package: `cli` (arg parsing), `pipeline`
> (orchestration), `steps` (the four stages), `prompts` (templates kept separate
> from logic), `llm` (the Anthropic wrapper with retries), and `pdf` (ReportLab
> rendering). There's a pytest suite and GitHub Actions CI running on 3 Python
> versions. Prototype first, harden second — I invested in structure once it was
> worth it, not before.

---

## Architecture at a glance (for the "walk me through the code" moment)

```
talent_strategist/
├── cli.py        → parses arguments, dispatches to a pipeline
├── pipeline.py   → orchestrates single-candidate and comparison runs
├── steps.py      → the 4 stages: research candidate, research role,
│                    extract requirements, build scorecard (+ scoring)
├── prompts.py    → all prompt text, separate from logic
├── llm.py        → Anthropic client wrapper: retries + web search
├── pdf.py        → ReportLab PDF rendering (real tables, no overlap)
├── storage.py    → saves markdown + optional PDF
└── candidates.py → reads inputs, pulls each candidate's real name
```
Plus: `pyproject.toml` (installable `talent-strategist` command), `tests/`
(pytest), `.github/workflows/ci.yml` (CI), `LICENSE`, `Makefile`.

**One-liner:** "It's a package, not a script — with tests, CI, and a real
CLI entry point."

---

## The layered-agent framing (strong for talent/ops roles)
"I directed one agent — Claude Code — to build and extend another. I added PDF
export, multi-candidate ranking, error handling, and a fast offline mode by
describing what I wanted, then reviewing and testing each change. That's what
working *with* AI tooling looks like day to day."

---

## Have open on screen
1. A generated **PDF scorecard** (the polished artifact)
2. `agent.py` at the pipeline section — steps 1→4 read like plain English
3. `CLAUDE.md` — shows you documented it like a real project

---

## Features to mention
- `--pdf` — formatted PDF export
- `--candidates a b c` — multi-candidate ranking & recommendation
- `--no-search` — fast/cheap offline mode for iterating
- Built-in summary table, API retries, and graceful error handling
