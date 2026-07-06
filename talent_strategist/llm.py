"""A thin wrapper around the Anthropic client: retries, web search, plain calls."""
from __future__ import annotations

import time

import anthropic

from .config import MAX_RETRIES, MAX_TOKENS, MODEL, RETRY_WAIT_SECONDS
from .console import print_substep
from .errors import AgentError

# Server-side web search tool. The API runs the search itself and inserts the
# results into the response — there is no client-side tool loop to manage.
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

RESEARCH_UNAVAILABLE = "(Research unavailable — this step could not be completed.)"


def create_message(client: anthropic.Anthropic, **kwargs):
    """Call ``messages.create``, retrying transient failures.

    Permanent failures (e.g. a bad API key) are turned into a clean
    :class:`AgentError` rather than a raw traceback.
    """
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 2):  # one initial try + MAX_RETRIES
        try:
            return client.messages.create(**kwargs)
        except anthropic.AuthenticationError:
            raise AgentError(
                "Authentication failed. Is ANTHROPIC_API_KEY set correctly?\n"
                "    Set it with:  export ANTHROPIC_API_KEY=your_key_here"
            )
        except (
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
        ) as exc:
            last_error = exc
            if attempt <= MAX_RETRIES:
                wait = RETRY_WAIT_SECONDS * attempt
                print_substep(
                    f"API issue ({type(exc).__name__}); retrying in {wait}s "
                    f"[attempt {attempt}/{MAX_RETRIES}]"
                )
                time.sleep(wait)
            continue
        except anthropic.APIError as exc:
            raise AgentError(f"API error: {exc}")

    raise AgentError(f"Gave up after {MAX_RETRIES} retries. Last error: {last_error}")


def _text_of(response) -> str:
    """Join the text blocks of a response into a single string."""
    return "\n".join(block.text for block in response.content if block.type == "text")


def call_with_search(client: anthropic.Anthropic, prompt: str, purpose: str = "") -> str:
    """Call Claude with web search enabled.

    Research is enrichment, not the core deliverable — if the call fails, we log
    it and return a placeholder so the pipeline can continue.
    """
    if purpose:
        print_substep(f"Calling Claude: {purpose}")

    try:
        response = create_message(
            client,
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
    except AgentError as exc:
        print_substep(f"⚠ Research step failed ({exc}); continuing without it")
        return RESEARCH_UNAVAILABLE

    for block in response.content:
        if block.type == "server_tool_use" and block.name == "web_search":
            print_substep(f"Searching: {block.input.get('query', '...')}")

    return _text_of(response)


def call_simple(client: anthropic.Anthropic, prompt: str, purpose: str = "") -> str:
    """Call Claude without tools, for synthesis and analysis tasks."""
    if purpose:
        print_substep(f"Analyzing: {purpose}")

    response = create_message(
        client,
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return _text_of(response)
