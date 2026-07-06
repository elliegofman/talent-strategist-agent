"""Custom exception types."""
from __future__ import annotations


class AgentError(Exception):
    """A clear, user-facing error that stops the run with a friendly message.

    Raised for expected problems (missing files, bad API key, invalid CLI usage)
    so the entry point can print a clean message instead of a stack trace.
    """
