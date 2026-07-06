"""Central configuration constants for the Talent Strategist agent."""
from __future__ import annotations

# The Claude model used for every API call.
MODEL = "claude-sonnet-4-6"

# Token budget per response.
MAX_TOKENS = 4096

# Directory (relative to the working directory) where reports are written.
REPORTS_DIR = "reports"

# Retry behaviour for transient API failures.
MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 3  # base wait; grows linearly with each attempt

# Inserted in place of live research when running with --no-search.
NO_SEARCH_PLACEHOLDER = (
    "(Web research skipped — run without --no-search for live market context.)"
)
