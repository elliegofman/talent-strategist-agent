# Talent Strategist Agent

## What this project is

An autonomous candidate-role fit analysis tool built for a Talent Strategist workflow. Given a role description and a candidate background, the agent:

1. Researches the candidate's company/industry context (web search)
2. Researches the target role's market context — similar roles, comp benchmarks, talent pool (web search)
3. Extracts structured requirements from the role description
4. Maps candidate evidence against each requirement
5. Produces a structured scorecard: an at-a-glance summary table, fit rating, requirement matches, risk flags, and tailored interview probe questions
6. Saves the output as a clean markdown report (and optionally a PDF)

It can also compare multiple candidates against a single role, ranking them by fit score and producing a side-by-side comparison with a hiring recommendation.

## Architecture

- `agent.py` — the main agent script. Uses the Anthropic API with tool use (web search) to run the multi-step analysis autonomously.
- `reports/` — output directory for generated scorecards (markdown, plus PDF when `--pdf` is used)
- `examples/` — sample role/candidate files for testing, plus `TEMPLATE_*.txt` files to copy for your own inputs
- `requirements.txt` — Python dependencies: `anthropic`, plus `markdown` + `xhtml2pdf` for PDF export

## How to run

```bash
python agent.py --role "path/to/role.txt" --candidate "path/to/candidate.txt"
```

Add `--pdf` to also save a formatted PDF alongside the markdown scorecard:
```bash
python agent.py --role "path/to/role.txt" --candidate "path/to/candidate.txt" --pdf
```

Compare several candidates against one role (ranks them and picks the best fit):
```bash
python agent.py --role "role.txt" --candidates "a.txt" "b.txt" "c.txt" --pdf
```

Use `--no-search` to skip the web-research steps for faster, cheaper, offline testing (works in both single and comparison modes). The scorecard is then based only on the role and candidate text, without live market context:
```bash
python agent.py --role "role.txt" --candidate "cand.txt" --no-search
```

Or interactively:
```bash
python agent.py
```

## Development guidelines

- Keep the agent logic in a single file (agent.py) for simplicity
- All API calls go through the Anthropic Python SDK
- Use web_search tool for real-time research
- Output reports as clean markdown files in reports/
- Use clear step-by-step console output so the user can see the agent working through each phase
- Handle errors gracefully — if a search fails, note it and continue
- Keep the code readable and well-commented — the developer is not a professional engineer

## Key design decisions

- The agent runs a sequential pipeline, not parallel. Each step's output feeds the next.
- Web search is used for two purposes: (1) enriching candidate context (company info, industry), (2) enriching role context (market benchmarks, similar roles at peer companies)
- The final scorecard is produced by a single synthesis call that receives all prior research as context
- The agent prints status updates as it works so the user can follow along
