"""Reading role and candidate inputs, and deriving candidate names."""
from __future__ import annotations

import os

from .errors import AgentError

# Separators that typically follow a name on a résumé's first line,
# e.g. "Jordan Kim — Operations Professional".
_NAME_SEPARATORS = ("—", "–", " - ", "|", ",", "\t")


def read_file(path: str, label: str) -> str:
    """Read a text file, raising a clear AgentError if it's missing."""
    if not os.path.isfile(path):
        raise AgentError(
            f"{label} file not found: {path}\n"
            f"    Check the path, or see examples/ for template files."
        )
    with open(path, "r") as fh:
        return fh.read()


def read_role_and_candidate(role_path: str, candidate_path: str) -> tuple[str, str]:
    """Read a role file and a single candidate file."""
    return read_file(role_path, "Role"), read_file(candidate_path, "Candidate")


def candidate_name_from_path(path: str) -> str:
    """Fallback: derive a readable name from a filename (jane_doe.txt -> Jane Doe)."""
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = stem.replace("my_candidate", "candidate")  # avoid a generic 'My Candidate'
    return stem.replace("_", " ").replace("-", " ").strip().title() or "Candidate"


def candidate_name_from_text(text: str, fallback: str) -> str:
    """Pull the candidate's actual name from the top of their résumé.

    Résumés almost always lead with the person's name, often followed by a title
    after a dash or pipe. We take the first non-empty line and cut it at the first
    such separator. If the result doesn't look like a name, use ``fallback``.
    """
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    for sep in _NAME_SEPARATORS:
        if sep in first_line:
            first_line = first_line.split(sep)[0].strip()
            break
    if 0 < len(first_line) <= 40 and first_line.lower() not in ("name", "candidate"):
        return first_line
    return fallback


def read_candidates(candidate_paths: list[str]) -> list[tuple[str, str]]:
    """Read multiple candidate files into a list of (name, text) tuples.

    Names come from the résumé text where possible, with duplicates disambiguated.
    """
    candidates: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for path in candidate_paths:
        text = read_file(path, "Candidate")
        name = candidate_name_from_text(text, candidate_name_from_path(path))
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        candidates.append((name, text))
    return candidates


def read_input_interactive() -> tuple[str, str]:
    """Prompt the user to paste the role and candidate text at the terminal."""
    print("\n" + "═" * 60)
    print("  TALENT STRATEGIST AGENT — Interactive Mode")
    print("═" * 60)

    role_text = _paste_block("ROLE DESCRIPTION")
    candidate_text = _paste_block("CANDIDATE BACKGROUND")
    return role_text, candidate_text


def _paste_block(label: str) -> str:
    print(f"\nPaste the {label} below.")
    print("(Type 'END' on a new line when done)\n")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    return "\n".join(lines)
