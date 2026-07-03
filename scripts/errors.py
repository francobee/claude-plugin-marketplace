#!/usr/bin/env python3
"""Error registry accessor: map registry codes (errors.json) to exit codes + terse failure output. Every script failure exits through die()."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_REGISTRY: dict | None = None


def registry() -> dict:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = {k: v for k, v in json.loads((REPO / "errors.json").read_text()).items()
                     if not k.startswith("_")}
    return _REGISTRY


def get(code: str) -> dict:
    entry = registry().get(code)
    if entry is None:
        # Unknown code is itself a bug — fail loud with a generic exit so it can't pass silently.
        print(f"✗ [ERR-UNKNOWN] no registry entry for code {code!r} — add it to errors.json", file=sys.stderr)
        sys.exit(1)
    return entry


def summary(code: str) -> str:
    """One-line summary for health checks and notifications."""
    return f"[{code}] {get(code)['meaning']}"


def die(code: str, detail: str = "") -> "None":
    """Print the registry meaning (+ optional detail) and exit with the registry exit code."""
    entry = get(code)
    line = f"✗ [{code}] {entry['meaning']}"
    if detail:
        line += f" — {detail}"
    print(line, file=sys.stderr)
    if entry.get("admin_fix"):
        print(f"  fix: {entry['admin_fix']}", file=sys.stderr)
    sys.exit(int(entry.get("exit", 1)))


if __name__ == "__main__":  # `python3 scripts/errors.py CFG-001` prints the entry (used by shell scripts/tests)
    if len(sys.argv) != 2:
        print("usage: errors.py <CODE>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps({sys.argv[1]: get(sys.argv[1])}, indent=2))
