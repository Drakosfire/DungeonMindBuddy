"""Grade planner ``unsure_queue`` JSON against ``gold/scope_b_session_20_unsure_queue.json``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SLICE = Path(__file__).resolve().parent


def load_unsure_gold() -> dict[str, Any]:
    return json.loads(
        (_SLICE / "gold" / "scope_b_session_20_unsure_queue.json").read_text(encoding="utf-8")
    )


def grade_unsure_queue(items: list[dict[str, Any]] | None) -> tuple[bool, list[str]]:
    """Return ``(ok, violations)`` using regex + count rules from gold."""
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

    return len(violations) == 0, violations
