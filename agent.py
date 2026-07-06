#!/usr/bin/env python3
"""Backwards-compatible entry point.

The implementation now lives in the ``talent_strategist`` package. This shim
keeps the original ``python agent.py ...`` commands working. You can equivalently
run ``python -m talent_strategist`` or, after ``pip install -e .``, the
``talent-strategist`` command.
"""
from talent_strategist.cli import main

if __name__ == "__main__":
    main()
