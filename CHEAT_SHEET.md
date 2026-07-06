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
