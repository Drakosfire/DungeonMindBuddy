from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from evals.c1s4_preplanning_vertical_slice.planner_affordances import derive_planner_affordances_for_support_card

SupportRetrievalMode = Literal[
    "content_only",
    "content_plus_lexical_hints",
]

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_POLICY_PATH = _THIS_DIR / "support_knowledge/support_retrieval_field_policy.json"
_DEFAULT_CARD_PATHS = [
    _THIS_DIR / "support_knowledge/retrieval_cards.hempholm_support.jsonl",
    _THIS_DIR / "support_knowledge/retrieval_cards.elderwyld_world_travel_support.jsonl",
]


def load_support_retrieval_field_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or _DEFAULT_POLICY_PATH
    return json.loads(policy_path.read_text(encoding="utf-8"))


def load_support_cards(paths: list[Path] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in (paths or _DEFAULT_CARD_PATHS):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_support_card(card: dict[str, Any], *, retrieval_mode: SupportRetrievalMode, field_policy: dict[str, Any]) -> dict[str, Any]:
    modes = field_policy.get("retrieval_modes", {})
    indexable_fields = set(modes[retrieval_mode]["indexable_fields"])
    title = str(card.get("title") or "").strip()
    summary = str(card.get("summary") or "").strip()
    retrieval_terms = [str(t).strip() for t in (card.get("retrieval_terms") or []) if str(t).strip()]
    planner_affordances = derive_planner_affordances_for_support_card(
        card,
        include_retrieval_terms="retrieval_terms" in indexable_fields,
    )

    lexical_parts = []
    if "title" in indexable_fields and title:
        lexical_parts.append(title)
    if "summary" in indexable_fields and summary:
        lexical_parts.append(summary)
    lexical_plain = ". ".join(lexical_parts)
    if "retrieval_terms" in indexable_fields and retrieval_terms:
        lexical_plain = f"{lexical_plain} Keywords: {', '.join(retrieval_terms)}" if lexical_plain else f"Keywords: {', '.join(retrieval_terms)}"
    if "planner_affordances" in indexable_fields and planner_affordances:
        labels = " ".join(str(a.get("affordance") or "").replace("_", " ") for a in planner_affordances)
        lexical_plain = f"{lexical_plain} Planner affordances: {labels}" if lexical_plain else f"Planner affordances: {labels}"

    return {
        "unit_id": f"support:{card.get('support_card_id')}",
        "campaign_id": card.get("campaign_id"),
        "session_number": 0,
        "source_kind": "support_knowledge_card",
        "source_layer": card.get("source_layer"),
        "authority_role": card.get("authority_role"),
        "canon_status": card.get("canon_status"),
        "title": title,
        "summary": summary,
        "lexical_plain": lexical_plain,
        "retrieval_terms": retrieval_terms,
        "planner_affordances": planner_affordances,
        "source_reference": card.get("source_reference") or {},
        "eval_metadata": {
            "usable_for_questions": card.get("usable_for_questions") or [],
            "must_not_claim": card.get("must_not_claim") or [],
            "must_not_include_unless_sourced": card.get("must_not_include_unless_sourced") or [],
        },
    }


def load_normalized_support_records(*, retrieval_mode: SupportRetrievalMode, paths: list[Path] | None = None, field_policy_path: Path | None = None) -> list[dict[str, Any]]:
    policy = load_support_retrieval_field_policy(field_policy_path)
    cards = load_support_cards(paths)
    return [normalize_support_card(card, retrieval_mode=retrieval_mode, field_policy=policy) for card in cards]
