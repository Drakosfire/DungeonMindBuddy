from __future__ import annotations

from fnmatch import fnmatch
from typing import Any

DENIED_RETRIEVAL_PATH_PARTS = (
    "evals/",
    "docs/",
    "tests/",
    "gold/",
    "canvas_templates/",
    "artifacts/",
    "docs/plans/",
    "analysis/",
)

DENIED_RETRIEVAL_BASENAME_PATTERNS = (
    "pr*_report.md",
    "pr*_analysis.md",
    "pr*_summary.json",
    "*_gold.json",
    "*.canvas.tsx",
)

NAV_ONLY_HEADINGS = (
    "retrieval keywords",
    "suggested reads",
    "cross-references",
    "npcs anchored here",
    "campaign-canon npcs anchored here",
    "npc and social anchors",
    "sub-locations and scene anchors",
)


def _canon_path(path: str) -> str:
    return str(path or "").replace("\\", "/").strip().lower()


def is_allowed_retrieval_corpus_path(path: str) -> bool:
    p = _canon_path(path)
    if not p:
        return False
    basename = p.rsplit("/", 1)[-1]
    if any(part in p for part in DENIED_RETRIEVAL_PATH_PARTS):
        return False
    if any(fnmatch(basename, pat) for pat in DENIED_RETRIEVAL_BASENAME_PATTERNS):
        return False
    return p.startswith("corpus/eldyrwild-markdown/")


def infer_context_subject_class(item: dict[str, Any]) -> str:
    sc = str(item.get("subject_class") or "").lower()
    if sc in {"location", "npc", "pc"}:
        return sc
    source_path = _canon_path(item.get("source_path") or item.get("source") or item.get("source_reference") or item.get("source_recap_path") or "")
    if "/locations/" in source_path:
        return "location"
    if "/npcs/" in source_path:
        return "npc"
    if "/pcs/" in source_path:
        return "pc"
    if "_session_memory/" in source_path or "/session recaps/" in source_path:
        return "session_memory"
    kind = str(item.get("source_kind") or "")
    if kind == "session_memory":
        return "session_memory"
    if kind == "support_knowledge_card":
        return "support"
    return "unknown"


def is_navigation_only_context(item: dict[str, Any]) -> bool:
    role = str(item.get("evidence_role") or "").lower()
    if role in {"navigation_only", "alias", "cross_reference"}:
        return True
    heading = str(item.get("section_heading") or item.get("heading") or item.get("section") or "").lower()
    text = " ".join(str(item.get(k) or "") for k in ["title", "snippet", "text", "source_reference"]).lower()
    return any(tok in heading or tok in text for tok in NAV_ONLY_HEADINGS)


def infer_planner_lane(item: dict[str, Any]) -> str:
    lane = str(item.get("presentation_lane") or "").lower()
    if lane in {"known_gap", "safety_constraint"}:
        return "known_gaps_and_safety_constraints"
    if lane in {"location_context", "worldbuilding", "location_worldbuilding"}:
        return "location_worldbuilding"
    if lane in {"pc_timeline", "party_timeline", "character_party_behavior"}:
        return "character_party_behavior"
    if lane == "support_knowledge":
        return "support_knowledge"
    if lane == "prior_campaign_memory":
        return "prior_campaign_memory"

    subject = infer_context_subject_class(item)
    doc_kind = str(item.get("subject_doc_kind") or "").lower()
    if subject == "location" or doc_kind in {"location_dossier", "world_primer"} or (doc_kind == "hub_index" and subject == "location"):
        return "location_worldbuilding"
    if subject in {"npc", "pc"} or doc_kind in {"timeline", "character_dossier"} or (doc_kind == "hub_index" and subject in {"npc", "pc"}):
        return "character_party_behavior"
    if subject == "session_memory":
        return "prior_campaign_memory"
    if str(item.get("source_kind") or "") == "support_knowledge_card":
        return "support_knowledge"
    return "unknown"


def is_context_compatible_with_required_lane(item: dict[str, Any], required_lane: str) -> bool:
    required_lane = str(required_lane or "")
    src = _canon_path(item.get("source_path") or item.get("source") or item.get("source_reference") or "")
    if not is_allowed_retrieval_corpus_path(src):
        return False
    if is_navigation_only_context(item):
        return False
    subject = infer_context_subject_class(item)
    lane = infer_planner_lane(item)

    if required_lane == "location_worldbuilding":
        return lane == "location_worldbuilding" or subject == "location" or "/locations/" in src
    if required_lane == "character_party_behavior":
        return lane == "character_party_behavior" or subject in {"npc", "pc"} or "/npcs/" in src or "/pcs/" in src
    if required_lane == "known_gap":
        return lane == "known_gaps_and_safety_constraints" or str(item.get("presentation_lane") or "") == "known_gap"
    return False
