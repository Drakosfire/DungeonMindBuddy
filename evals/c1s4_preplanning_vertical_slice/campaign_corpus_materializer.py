from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_classification import is_allowed_retrieval_corpus_path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "corpus/eldyrwild-markdown"
CORPUS_PREFIX = "corpus/eldyrwild-markdown/"

# Explicit allowlist — PR57 target families only; no wholesale corpus indexing.
C1S4_CAMPAIGN_CORPUS_TARGET_RELPATHS: tuple[str, ...] = (
    "Longmont Campaign/Campaign 1/NPCs/pippa/README.md",
    "Longmont Campaign/Campaign 1/NPCs/pippa/pippa_character_dossier.md",
    "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/README.md",
    "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/bubbles_the_float_goat_character_dossier.md",
    "Longmont Campaign/Campaign 1/NPCs/grishna/README.md",
    "Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md",
    "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/README.md",
    "Longmont Campaign/Campaign 1/Locations/hempholm/README.md",
    "Longmont Campaign/Campaign 1/Session Recaps/Session 3 - The Stone Bridge Flood.md",
)

LOCATION_HUB_SECTION_ROLES: dict[str, str] = {
    "authority stance": "evidence",
    "canon summary": "evidence",
    "canon location texture": "evidence",
    "sub-locations and scene anchors": "evidence",
    "scene anchors": "evidence",
    "canonical name and legacy spellings": "evidence",
    "timeline pointers": "evidence",
    "campaign-canon npcs anchored here": "navigation_only",
    "npc and social anchors": "navigation_only",
    "suggested reads": "navigation_only",
    "suggested reads (in order)": "navigation_only",
    "retrieval keywords": "alias",
    "cross-references": "cross_reference",
    "open canon questions": "known_gap",
}

NPC_HUB_SECTION_ROLES: dict[str, str] = {
    "suggested reads": "navigation_only",
    "suggested reads (in order)": "navigation_only",
    "session recaps (no pinned default)": "navigation_only",
    "mechanical sheets (priority — highest first)": "navigation_only",
    "mechanical sheets (priority - highest first)": "navigation_only",
    "package notes": "evidence",
    "retrieval keywords": "alias",
    "cross-references": "cross_reference",
}

NPC_DOSSIER_SECTION_ROLES: dict[str, str] = {
    "table role": "evidence",
    "session 3 state": "evidence",
    "statblock-generator context": "evidence",
    "summary": "evidence",
    "source pointers": "navigation_only",
}

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :].lstrip("\n")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")


def _norm_heading(heading: str) -> str:
    return re.sub(r"\s+", " ", str(heading or "").strip().lower())


def _split_markdown_sections(text: str) -> list[tuple[int, str, str]]:
    body = _strip_frontmatter(text)
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        stripped = body.strip()
        return [(1, "Document body", stripped)] if stripped else []

    sections: list[tuple[int, str, str]] = []
    if matches[0].start() > 0:
        preamble = body[: matches[0].start()].strip()
        if preamble:
            sections.append((1, "Document preamble", preamble))

    for idx, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()
        sections.append((level, heading, section_body))
    return sections


def _infer_doc_shape(relpath: str) -> tuple[str, str, str]:
    lower = relpath.lower()
    if "/session recaps/" in lower and not any(x in lower for x in ("_normalized/", "_breadcrumbed/", "_session_memory/")):
        return "session_recap", "session", "prior_campaign_memory"
    if "/locations/" in lower and lower.endswith("/readme.md"):
        slug = Path(relpath).parent.name
        return "location_hub", "location", "location_worldbuilding"
    if "/npcs/" in lower and lower.endswith("_character_dossier.md"):
        slug = Path(relpath).parent.name
        return "npc_dossier", "npc", "character_party_behavior"
    if "/npcs/" in lower and lower.endswith("/readme.md"):
        slug = Path(relpath).parent.name
        return "npc_hub", "npc", "character_party_behavior"
    raise ValueError(f"unsupported C1S4 campaign corpus target: {relpath}")


def _section_role(*, source_kind: str, heading: str) -> str:
    key = _norm_heading(heading)
    if source_kind == "location_hub":
        return LOCATION_HUB_SECTION_ROLES.get(key, "evidence")
    if source_kind == "npc_hub":
        if key in NPC_HUB_SECTION_ROLES:
            return NPC_HUB_SECTION_ROLES[key]
        return "evidence" if key not in {"suggested reads", "suggested reads (in order)"} else "navigation_only"
    if source_kind == "npc_dossier":
        return NPC_DOSSIER_SECTION_ROLES.get(key, "evidence")
    if source_kind == "session_recap":
        return "evidence"
    return "evidence"


def _presentation_lane(*, source_kind: str, subject_class: str, evidence_role: str) -> str:
    if evidence_role in {"navigation_only", "alias", "cross_reference", "known_gap"}:
        if evidence_role == "known_gap":
            return "known_gap"
        return "navigation"
    if source_kind == "session_recap":
        return "prior_campaign_memory"
    if subject_class == "location":
        return "location_context"
    if subject_class == "npc":
        return "party_timeline"
    return "unknown"


def _route_for_relpath(relpath: str, subject_class: str) -> str:
    parts = Path(relpath).parts
    if subject_class == "location" and "Locations" in parts:
        idx = parts.index("Locations")
        slug = parts[idx + 1]
        return f"Longmont Campaign/Campaign 1/Locations/{slug}/"
    if subject_class == "npc" and "NPCs" in parts:
        idx = parts.index("NPCs")
        slug = parts[idx + 1]
        return f"Longmont Campaign/Campaign 1/NPCs/{slug}/"
    if subject_class == "session":
        return "Longmont Campaign/Campaign 1/Session Recaps/"
    return ""


def _subject_route_entry(route: str, subject_class: str) -> dict[str, Any]:
    sc = "LOCATION" if subject_class == "location" else "NPC" if subject_class == "npc" else "SESSION"
    return {
        "subject_class": sc,
        "normalized_route": route,
        "proposed": False,
        "tag_kind": "hub",
    }


def _materialize_file(relpath: str) -> list[dict[str, Any]]:
    full_path = CORPUS_ROOT / relpath
    source_path = f"{CORPUS_PREFIX}{relpath}"
    if not is_allowed_retrieval_corpus_path(source_path):
        raise ValueError(f"denied retrieval corpus path: {source_path}")
    if not full_path.is_file():
        raise FileNotFoundError(source_path)

    source_kind, subject_class, planner_lane_hint = _infer_doc_shape(relpath)
    subject_id = Path(relpath).parent.name
    route = _route_for_relpath(relpath, subject_class)
    routes = [_subject_route_entry(route, subject_class)] if route else []

    if source_kind == "session_recap":
        text = full_path.read_text(encoding="utf-8")
        body = _strip_frontmatter(text).strip()
        if not body:
            return []
        unit_slug = "observed-play-prose"
        return [
            {
                "schema": "dmb_campaign_corpus_record_v1",
                "unit_id": f"corpus:session_recap:session-3:{unit_slug}",
                "source_path": source_path,
                "source_recap_path": source_path,
                "source_reference": f"{source_path}#observed-play-prose",
                "source_kind": source_kind,
                "source_layer": "campaign_corpus",
                "subject_class": subject_class,
                "subject_id": "session-3-stone-bridge-flood",
                "route": route.rstrip("/"),
                "routes": routes,
                "section_heading": "Observed play prose",
                "evidence_role": "evidence",
                "presentation_lane": _presentation_lane(
                    source_kind=source_kind, subject_class=subject_class, evidence_role="evidence"
                ),
                "planner_lane_hint": planner_lane_hint,
                "title": "Session 3 — Observed play prose",
                "snippet": body[:500],
                "lexical_plain": body,
                "campaign_id": "longmont-c1",
                "session_number": 3,
                "session_min": 0,
                "session_max": 3,
                "subject_doc_kind": "session_recap",
            }
        ]

    text = full_path.read_text(encoding="utf-8")
    sections = _split_markdown_sections(text)
    records: list[dict[str, Any]] = []
    for _level, heading, section_body in sections:
        evidence_role = _section_role(source_kind=source_kind, heading=heading)
        heading_slug = _slugify(heading) or "section"
        lexical = section_body.strip()
        if heading and evidence_role == "evidence":
            lexical = f"{heading}. {lexical}".strip(". ").strip()
        elif heading and evidence_role in {"alias", "cross_reference", "navigation_only", "known_gap"}:
            lexical = f"{heading}: {lexical}".strip(": ").strip()
        if not lexical and heading:
            lexical = heading

        unit_prefix = {
            "npc_hub": "npc",
            "npc_dossier": "npc",
            "location_hub": "location",
        }[source_kind]
        records.append(
            {
                "schema": "dmb_campaign_corpus_record_v1",
                "unit_id": f"corpus:{unit_prefix}:{subject_id}:{heading_slug}",
                "source_path": source_path,
                "source_recap_path": source_path,
                "source_reference": f"{source_path}#{heading_slug}",
                "source_kind": source_kind,
                "source_layer": "campaign_corpus",
                "subject_class": subject_class,
                "subject_id": subject_id,
                "route": route.rstrip("/"),
                "routes": routes,
                "section_heading": heading,
                "evidence_role": evidence_role,
                "presentation_lane": _presentation_lane(
                    source_kind=source_kind, subject_class=subject_class, evidence_role=evidence_role
                ),
                "planner_lane_hint": planner_lane_hint,
                "title": f"{subject_id.replace('_', ' ').title()} — {heading}",
                "snippet": lexical[:500],
                "lexical_plain": lexical,
                "campaign_id": "longmont-c1",
                "session_number": 0,
                "session_min": 0,
                "session_max": 3,
                "subject_doc_kind": "hub_index" if source_kind.endswith("_hub") else "dossier",
            }
        )
    return records


def load_campaign_corpus_records_for_c1s4() -> list[dict[str, Any]]:
    """Materialize PR57 target campaign corpus markdown into section-level retrieval records."""
    records: list[dict[str, Any]] = []
    for relpath in C1S4_CAMPAIGN_CORPUS_TARGET_RELPATHS:
        records.extend(_materialize_file(relpath))
    return records
