"""Diff post-run corpus + tool trace against ``gold/scope_b_session_20.json`` (stub)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SLICE = Path(__file__).resolve().parent


def load_scope_b_gold() -> dict[str, Any]:
    return json.loads((_SLICE / "gold" / "scope_b_session_20.json").read_text(encoding="utf-8"))


def grade_placeholder() -> dict[str, Any]:
    """Return a gate report shape; full grading is TODO (wire tool trace + filesystem diff)."""
    return {
        "schema": "session_recap_ingest_grade_report_v1",
        "gates": {"B1": False, "note": "Grader not wired — implement in follow-up."},
    }


def main() -> None:
    _ = load_scope_b_gold()
    print(json.dumps(grade_placeholder(), indent=2))


if __name__ == "__main__":
    main()
