from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from .model import EntityKind, VocabularyEntry
from .packet_render import ContextPacketBudgetPolicy, render_context_vocabulary_packet
from .model import ContextVocabularyPacket

SELECTION_METHOD = "dynamic_context_vocabulary_selection_v0"


@dataclass(frozen=True, slots=True)
class DynamicVocabularySelectionPolicy:
    scope: str = "campaign"
    max_entries: int = 48
    max_recent_session_distance: int | None = None
    include_context_anchors: bool = True
    include_candidate_nodes: bool = True
    include_existing_extracted_nodes: bool = True
    packet_seed: str = "dynamic-selection-v0"


@dataclass(frozen=True, slots=True)
class DynamicVocabularySelectionResult:
    packet: ContextVocabularyPacket
    diagnostics: dict[str, Any]


_NODE_TYPE_TO_ENTITY_KIND: dict[str, EntityKind] = {
    "character": "actor",
    "npc": "actor",
    "pc": "actor",
    "creature": "actor",
    "location": "place",
    "sublocation": "place",
    "region": "place",
    "route": "place",
    "hub": "place",
    "group": "collective",
    "organization": "collective",
    "faction": "collective",
    "party": "collective",
    "item": "object",
    "statblock": "object",
    "roll-table": "object",
    "roll_table": "object",
    "thread": "thread",
    "mystery": "thread",
    "clue": "thread",
    "rumor": "thread",
    "promise": "thread",
    "debt": "thread",
    "hook": "thread",
    "quest": "thread",
    "unknown_important": "thread",
    "threat": "thread",
    "event": "phenomenon",
    "warning": "phenomenon",
    "session": "phenomenon",
    "campaign": "phenomenon",
    "phenomenon": "phenomenon",
    "unresolved_phenomenon": "phenomenon",
    "combat_encounter": "combat_encounter",
    "social_encounter": "social_encounter",
    "session_beat": "session_beat",
}

_PRIORITY: dict[EntityKind, int] = {
    "combat_encounter": 0,
    "thread": 1,
    "actor": 2,
    "place": 3,
    "collective": 4,
    "object": 5,
    "phenomenon": 6,
    "social_encounter": 7,
    "session_beat": 8,
    "unknown": 9,
}


def entity_kind_from_node_type(node_type: str) -> EntityKind:
    return _NODE_TYPE_TO_ENTITY_KIND.get(str(node_type or "").strip().lower(), "unknown")


def _stable_vocab_id(node_id: str, entity_kind: EntityKind) -> str:
    safe_node_id = node_id.strip()
    if safe_node_id:
        return f"vocab:dynamic:{entity_kind}:{safe_node_id}"
    digest = hashlib.sha1(f"{entity_kind}:{node_id}".encode("utf-8")).hexdigest()[:12]
    return f"vocab:dynamic:{entity_kind}:{digest}"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _safe_source_refs(node: Mapping[str, Any]) -> list[str]:
    refs = _string_list(node.get("source_refs"))
    corpus_ref = node.get("corpus_ref")
    if isinstance(corpus_ref, str) and corpus_ref.strip():
        refs.append(corpus_ref.strip())
    elif isinstance(corpus_ref, Mapping):
        for key in ("path", "uri", "corpus_path", "artifact_id", "source_artifact_id"):
            value = corpus_ref.get(key)
            if isinstance(value, str) and value.strip():
                refs.append(value.strip())
                break
    seen: set[str] = set()
    out: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def vocabulary_entry_from_node(
    node: Mapping[str, Any],
    *,
    scope: str,
    campaign_id: str | None = None,
    world_id: str | None = None,
) -> VocabularyEntry | None:
    node_id = str(node.get("node_id") or "").strip()
    label = str(node.get("label") or "").strip()
    if not node_id or not label:
        return None
    entity_kind = entity_kind_from_node_type(str(node.get("node_type") or ""))
    entry_scope = scope.strip() or "campaign"
    entry_campaign_id = campaign_id if entry_scope == "campaign" else None
    entry_world_id = world_id if entry_scope == "world" else None
    if entry_scope == "campaign" and not entry_campaign_id:
        entry_scope = "global"
    if entry_scope == "world" and not entry_world_id:
        entry_scope = "global"
    return VocabularyEntry(
        vocab_id=_stable_vocab_id(node_id, entity_kind),
        canonical_label=label,
        entity_kind=entity_kind,
        scope=entry_scope,
        campaign_id=entry_campaign_id,
        world_id=entry_world_id,
        global_node_id=node_id,
        aliases=_string_list(node.get("aliases")),
        source_refs=_safe_source_refs(node),
        status="candidate",
        authority="derived_memory",
        notes="Dynamic vocabulary entry from supplied graph context; not reviewed canon.",
    )


def _dedupe_preference(node: Mapping[str, Any], entry: VocabularyEntry) -> tuple[int, int, str]:
    return (
        1 if bool(node.get("context_anchor")) else 0,
        1 if entry.source_refs else 0,
        entry.vocab_id,
    )


def _sort_key(item: tuple[Mapping[str, Any], VocabularyEntry]) -> tuple[int, str, str]:
    node, entry = item
    return (_PRIORITY.get(entry.entity_kind, 99), entry.canonical_label.lower(), str(node.get("node_id") or ""))


def build_dynamic_context_vocabulary_packet(
    *,
    nodes: Iterable[Mapping[str, Any]],
    campaign_id: str | None = None,
    world_id: str | None = None,
    policy: DynamicVocabularySelectionPolicy | None = None,
    budget_policy: ContextPacketBudgetPolicy | None = None,
) -> DynamicVocabularySelectionResult:
    active_policy = policy or DynamicVocabularySelectionPolicy()
    if active_policy.max_entries < 0:
        raise ValueError("max_entries must be greater than or equal to 0")

    input_nodes = [dict(node) for node in nodes]
    skipped_nodes: list[dict[str, str]] = []
    deduped: dict[tuple[EntityKind, str], tuple[Mapping[str, Any], VocabularyEntry]] = {}
    evidence_less_entries = 0

    for index, node in enumerate(input_nodes):
        node_id = str(node.get("node_id") or f"<index:{index}>")
        if bool(node.get("context_anchor")) and not active_policy.include_context_anchors:
            skipped_nodes.append({"node_id": node_id, "reason": "context_anchor_disabled"})
            continue
        if bool(node.get("existing_extracted_node")) and not active_policy.include_existing_extracted_nodes:
            skipped_nodes.append({"node_id": node_id, "reason": "existing_extracted_nodes_disabled"})
            continue
        if bool(node.get("candidate_node")) and not active_policy.include_candidate_nodes:
            skipped_nodes.append({"node_id": node_id, "reason": "candidate_nodes_disabled"})
            continue
        entry = vocabulary_entry_from_node(
            node,
            scope=active_policy.scope,
            campaign_id=campaign_id,
            world_id=world_id,
        )
        if entry is None:
            skipped_nodes.append({"node_id": node_id, "reason": "missing_node_id_or_label"})
            continue
        if not entry.source_refs and not node.get("evidence_refs"):
            evidence_less_entries += 1
        key = (entry.entity_kind, entry.canonical_label.lower())
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = (node, entry)
            continue
        if _dedupe_preference(node, entry) > _dedupe_preference(existing[0], existing[1]):
            skipped_nodes.append({"node_id": str(existing[0].get("node_id") or ""), "reason": "duplicate_label_kind"})
            deduped[key] = (node, entry)
        else:
            skipped_nodes.append({"node_id": node_id, "reason": "duplicate_label_kind"})

    ordered = sorted(deduped.values(), key=_sort_key)
    selected = ordered[: active_policy.max_entries]
    trimmed = ordered[active_policy.max_entries :]
    for node, _entry in trimmed:
        skipped_nodes.append({"node_id": str(node.get("node_id") or ""), "reason": "trimmed_by_max_entries"})

    selected_entries = [entry for _node, entry in selected]
    render_result = render_context_vocabulary_packet(
        scope=active_policy.scope,
        campaign_entries=selected_entries if active_policy.scope != "world" else (),
        world_entries=selected_entries if active_policy.scope == "world" else (),
        budget_policy=budget_policy,
        packet_seed=active_policy.packet_seed,
    )
    entity_kind_counts: dict[str, int] = {}
    for entry in selected_entries:
        entity_kind_counts[entry.entity_kind] = entity_kind_counts.get(entry.entity_kind, 0) + 1

    diagnostics = {
        "enabled": True,
        "selection_method": SELECTION_METHOD,
        "input_node_count": len(input_nodes),
        "selected_entry_count": len(selected_entries),
        "trimmed_entry_count": len(trimmed),
        "skipped_node_count": len(skipped_nodes),
        "selected_node_ids": [str(node.get("node_id") or "") for node, _entry in selected],
        "skipped_nodes": skipped_nodes,
        "entity_kind_counts": entity_kind_counts,
        "evidence_less_entry_count": evidence_less_entries,
        "packet_id": render_result.packet.packet_id,
        "packet_render_diagnostics": render_result.diagnostics,
    }
    return DynamicVocabularySelectionResult(packet=render_result.packet, diagnostics=diagnostics)
