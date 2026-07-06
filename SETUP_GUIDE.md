# Talent Strategist Agent — Setup and Usage Guide

## What you're building

An autonomous agent that takes a role description and a candidate's background, then independently researches both using live web search, maps the candidate against the role's requirements, and produces a structured scorecard with fit analysis, risk flags, and tailored interview probe questions.

This is a real agentic workflow — Claude decides when to search, what to search for, and how to synthesize results across multiple steps — not just a single prompt getting a single answer.

## What you need

1. A computer (Mac, Windows, or Linux)
2. A Claude Pro or Max subscription ($20/month minimum) — the free plan doesn't include Claude Code
3. About 30 minutes for initial setup

## Step 1: Install Claude Code

The fastest method (no dependencies needed):

**Mac** — open Terminal and run:
```
curl -fsSL https://cli.claude.com/install.sh | sh
```

**Windows** — open PowerShell and run:
```
irm https://cli.claude.com/install.ps1 | iex
```

After it installs, verify it worked:
```
claude --version
```

You should see a version number. Then authenticate:
```
claude
```

This opens your browser — sign in with your Claude account. Once authenticated, you're ready.

## Step 2: Set up the project

Download the project folder (talent-strategist-agent) to your computer. Then open your terminal and navigate to it:

```
cd path/to/talent-strategist-agent
```

Install the Python dependency:
```
pip install -r requirements.txt
```

Set your API key (you'll need this for the agent script to call Claude directly):
```
export ANTHROPIC_API_KEY=your_key_here
```

You can get your API key at console.anthropic.com under "API Keys."

## Step 3: Run the agent

### Option A: Use Claude Code to run it for you

This is the recommended approach because Claude Code can fix issues, modify the script, and iterate — that's the agentic experience.

Start Claude Code in the project directory:
```
claude
```

Then tell it what to do:
```
Run the agent with the sample role and candidate files in examples/. Show me the output.
```

Claude Code will read the project, understand the structure (because of CLAUDE.md), run the script, and show you the results. If anything breaks, it fixes it.

### Option B: Run it directly

```
python agent.py --role examples/sample_role.txt --candidate examples/sample_candidate.txt
```

You'll see it work through each step in your terminal, then save a scorecard to the reports/ folder.

Add `--pdf` to also save a nicely formatted PDF next to the markdown — handy for sharing or screen-sharing in an interview:

```
python agent.py --role examples/sample_role.txt --candidate examples/sample_candidate.txt --pdf
```

### Option C: Interactive mode

```
python agent.py
```

Paste in a role description and candidate background when prompted.

### Option D: Compare several candidates for one role

Give one role and two or more candidate files. The agent scores each candidate, ranks them, and writes a side-by-side comparison report naming the best fit:

```
python agent.py --role examples/sample_role.txt \
  --candidates examples/sample_candidate.txt examples/sample_candidate_2.txt examples/sample_candidate_3.txt --pdf
```

The comparison report includes a ranking table (fit score, recommendation, top strength/risk per candidate), a written recommendation of who to advance and why, and links to each candidate's individual scorecard (also saved in `reports/`). Candidate names in the report are taken from the file names.

### Running it on your own role and candidate

The `examples/` folder includes two template files to make this easy. Copy them, then paste in a real job posting and résumé:

```
cp examples/TEMPLATE_role.txt      examples/my_role.txt
cp examples/TEMPLATE_candidate.txt examples/my_candidate.txt
# open each file, replace the placeholder text, and save

python agent.py --role examples/my_role.txt --candidate examples/my_candidate.txt --pdf
```

Privacy note: only use your own résumé, a public profile, or someone who has given you permission — don't feed in a stranger's private information.

## Step 4: Iterate and extend with Claude Code

This is where the real learning happens. Start Claude Code in the project:
```
claude
```

Then try these prompts to extend the agent:

**Add new features:**
- "Add a step that searches for the candidate on LinkedIn and incorporates what it finds"
- "Add a competitive analysis step — search for what similar roles pay at peer companies and include comp benchmarks in the scorecard"
- "Add a batch mode that processes multiple candidates against the same role"

**Improve the output:**
- "The scorecard interview questions are too generic. Improve the prompt so questions are highly specific to the candidate's gaps"
- "Add a section to the scorecard that recommends which interviewer panel members should meet this candidate and why"
- "Make the scorecard output cleaner — add a summary table at the top"

**Add new capabilities:**
- "Add an option to export the comparison as a shareable HTML page"
- "Let me set the fit-score threshold that counts as 'Advance'"

(PDF export, multi-candidate comparison, and a `--no-search` fast/offline mode are already built in — use `--pdf`, `--candidates`, and `--no-search`.)

Each of these is you directing the agent (Claude Code) to extend another agent (the talent strategist tool). That layered understanding is exactly what impresses in interviews.

## How to talk about this in an interview

### The 30-second version
"I built an autonomous candidate evaluation tool using Claude's API. You give it a role description and a candidate background, and it independently researches both using web search, maps the candidate against extracted requirements, and produces a structured scorecard with fit analysis, risk flags, and tailored interview questions. The key difference from just asking ChatGPT a question is that the agent decides what to search for and when — it's goal-directed, not prompt-directed."

### If they ask about the technical architecture
"It's a four-step pipeline. Step one researches the candidate's company and industry context using live web search — Claude decides what queries to run based on the candidate's background. Step two does the same for the role's market context. Step three extracts structured requirements from the role description. Step four synthesizes everything into a scorecard. Each step feeds context forward to the next, so the final output is grounded in real research, not just pattern matching on the input text."

### If they ask what makes it 'agentic'
"Three things. First, tool use — Claude autonomously decides when to search the web and what to search for, rather than me specifying every query. Second, multi-step planning — the goal is 'evaluate this candidate' but the agent breaks that into sub-tasks and sequences them. Third, persistent context — each step's output feeds the next step's prompt, so the final synthesis has the full picture. I could extend it further with MCP connections to an ATS or CRM, which would make it genuinely production-grade."

### If they ask about limitations
"The main limitation right now is that it's not connected to internal systems — in production at a company like Palantir, you'd want it integrated with your ATS via MCP so it could pull candidate records directly rather than requiring manual paste. The web search also occasionally surfaces irrelevant results, so the quality varies. I'd want to add a validation step where it checks its own research before synthesizing."

## Project structure

```
talent-strategist-agent/
├── CLAUDE.md              ← tells Claude Code what this project is
├── agent.py               ← the autonomous agent script
├── requirements.txt       ← Python dependencies
├── examples/
│   ├── sample_role.txt          ← test role description
│   ├── sample_candidate.txt     ← test candidate background
│   ├── sample_candidate_2.txt   ← more candidates, for testing --candidates compare
│   ├── sample_candidate_3.txt
│   ├── TEMPLATE_role.txt        ← copy this to make your own role file
│   └── TEMPLATE_candidate.txt   ← copy this to make your own candidate file
├── reports/               ← generated scorecards land here (.md, plus .pdf if --pdf)
└── SETUP_GUIDE.md         ← this file
```
