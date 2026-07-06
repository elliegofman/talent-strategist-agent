"""Command-line interface for the Talent Strategist agent."""
from __future__ import annotations

import argparse
import sys

from .candidates import (
    read_candidates,
    read_file,
    read_input_interactive,
    read_role_and_candidate,
)
from .errors import AgentError
from .pipeline import run_comparison, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talent-strategist",
        description="Talent Strategist Agent — autonomous candidate-role fit analysis",
        epilog=(
            "Examples:\n"
            "  Single:   talent-strategist --role role.txt --candidate cand.txt\n"
            "  Compare:  talent-strategist --role role.txt --candidates a.txt b.txt c.txt --pdf"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--role", help="Path to role description file")
    parser.add_argument("--candidate", help="Path to a single candidate background file")
    parser.add_argument("--candidates", nargs="+",
                        help="Paths to two or more candidate files — ranks them side by side")
    parser.add_argument("--pdf", action="store_true", help="Also save a formatted PDF")
    parser.add_argument("--no-search", action="store_true",
                        help="Skip web research for faster, cheaper, offline testing")
    return parser


def _run(args: argparse.Namespace) -> None:
    # --- Comparison mode: one role, several candidates ---
    if args.candidates:
        if not args.role:
            raise AgentError("--role is required when using --candidates.")
        if args.candidate:
            raise AgentError("Use either --candidate (one) or --candidates (many), not both.")
        if len(args.candidates) < 2:
            raise AgentError("--candidates needs at least two files. "
                             "For a single candidate, use --candidate.")
        role_text = read_file(args.role, "Role")
        if not role_text.strip():
            raise AgentError("The role description file is empty.")
        candidates = read_candidates(args.candidates)
        run_comparison(role_text, candidates, make_pdf=args.pdf, no_search=args.no_search)
        return

    # --- Single-candidate mode ---
    if bool(args.role) != bool(args.candidate):
        raise AgentError("--role and --candidate must be used together.")

    if args.role and args.candidate:
        role_text, candidate_text = read_role_and_candidate(args.role, args.candidate)
    else:
        role_text, candidate_text = read_input_interactive()

    if not role_text.strip() or not candidate_text.strip():
        raise AgentError("Both role description and candidate background are required.")

    run_pipeline(role_text, candidate_text, make_pdf=args.pdf, no_search=args.no_search)


def main(argv: list[str] | None = None) -> None:
    """Entry point. Parses arguments and dispatches to the right pipeline."""
    args = build_parser().parse_args(argv)
    try:
        _run(args)
    except AgentError as exc:
        # Expected, user-facing problems — clean message, no traceback.
        print(f"\n✗ {exc}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
