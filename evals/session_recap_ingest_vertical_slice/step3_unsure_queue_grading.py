"""Grade planner ``unsure_queue`` JSON against ``gold/scope_b_session_20_unsure_queue.json``.

Two grading modes are supported via the ``mode`` field in the gold file:

- ``"exact"`` (default when ``mode`` is absent): existing behavior — count bounds +
  per-``expected_items`` exact ID match + question regex + default substring +
  alternatives min count.
- ``"shape"``: enforces only count bounds and per-item structural checks driven by
  an optional ``per_item_shape`` block in the gold.  ``expected_items`` is ignored
  entirely.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SLICE = Path(__file__).resolve().parent

_DEFAULT_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


def load_unsure_gold() -> dict[str, Any]:
    return json.loads(
        (_SLICE / "gold" / "scope_b_session_20_unsure_queue.json").read_text(encoding="utf-8")
    )


def _grade_exact(
    items: list[dict[str, Any]],
    gold: dict[str, Any],
    violations: list[str],
) -> None:
    """Exact-mode grading: per-item ID match, question regex, default substring, alt count."""
    by_id = {str(x.get("id", "")): x for x in items}
    for spec in gold.get("expected_items", []):
        eid = str(spec.get("id", ""))
        it = by_id.get(eid)
        if not it:
            violations.append(f"missing unsure_queue id {eid!r}")
            continue
        q = str(it.get("question", ""))
        pat = str(spec.get("question_must_match", ""))
        if pat and not re.search(pat, q):
            violations.append(f"id {eid!r}: question did not match {pat!r}")
        mention = str(spec.get("default_must_mention", "")).lower()
        dsum = str(it.get("default_summary", "")).lower()
        if mention and mention not in dsum:
            violations.append(f"id {eid!r}: default_summary missing {mention!r}")
        alts = it.get("alternative_summaries") or []
        need = int(spec.get("alternatives_min_count", 2))
        if len(alts) < need:
            violations.append(
                f"id {eid!r}: need >= {need} alternative_summaries, got {len(alts)}"
            )


def _grade_shape(
    items: list[dict[str, Any]],
    gold: dict[str, Any],
    violations: list[str],
) -> None:
    """Shape-mode grading: structural checks only, no expected_items consulted."""
    shape = gold.get("per_item_shape", {})
    id_required: bool = bool(shape.get("id_required", True))
    id_pattern: str = str(shape.get("id_pattern", _DEFAULT_ID_PATTERN))
    question_required: bool = bool(shape.get("question_required", True))
    default_summary_required: bool = bool(shape.get("default_summary_required", True))
    min_alternatives: int = int(shape.get("min_alternatives", 2))

    for idx, item in enumerate(items):
        label = f"item[{idx}]"
        raw_id = item.get("id")
        id_str = str(raw_id) if raw_id is not None else ""

        if id_required and not id_str:
            violations.append(f"{label}: id is required but missing or empty")
        elif id_str and not re.match(id_pattern, id_str):
            violations.append(
                f"{label}: id {id_str!r} does not match pattern {id_pattern!r}"
            )

        if question_required:
            q = str(item.get("question", "")).strip()
            if not q:
                violations.append(f"{label}: question is required but missing or empty")

        if default_summary_required:
            ds = str(item.get("default_summary", "")).strip()
            if not ds:
                violations.append(f"{label}: default_summary is required but missing or empty")

        alts = item.get("alternative_summaries") or []
        if len(alts) < min_alternatives:
            violations.append(
                f"{label}: need >= {min_alternatives} alternative_summaries, got {len(alts)}"
            )


def grade_unsure_queue(items: list[dict[str, Any]] | None) -> tuple[bool, list[str]]:
    """Return ``(ok, violations)`` using rules from gold.

    The gold file's ``mode`` field selects the grading strategy:

    - ``"exact"`` (or absent): existing behavior — count bounds + per-ID exact match
      + question regex + default substring + alternatives min count.
    - ``"shape"``: count bounds only + per-item structural checks from ``per_item_shape``.
      ``expected_items`` is ignored.
    """
    gold = load_unsure_gold()
    violations: list[str] = []
    if items is None:
        items = []
    max_n = int(gold.get("max_total_items", 4))
    min_n = int(gold.get("min_total_items", 0))
    if len(items) > max_n:
        violations.append(f"too many unsure_queue items: {len(items)} > {max_n}")
    if len(items) < min_n:
        violations.append(f"too few unsure_queue items: {len(items)} < {min_n}")

    mode = str(gold.get("mode", "exact"))
    if mode == "shape":
        _grade_shape(items, gold, violations)
    else:
        _grade_exact(items, gold, violations)

    return len(violations) == 0, violations
