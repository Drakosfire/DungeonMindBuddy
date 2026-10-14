"""Render extraction guidance from the current native publication contract."""
from __future__ import annotations

from dataclasses import dataclass

from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET, predicate_allowed_endpoints, resolve_buddy_predicate_mapping_v4,
)
from src.graph_memory.predicate_catalog import exact_predicate_ids, predicate_family_for_type


@dataclass(frozen=True)
class NativeEdgePromptRule:
    predicate: str
    family: str
    subject_kinds: tuple[str, ...]
    object_kinds: tuple[str, ...]


def native_edge_prompt_rules() -> tuple[NativeEdgePromptRule, ...]:
    vocabulary = CURRENT_V5_TARGET.world_object_loader()
    rules = []
    for predicate in exact_predicate_ids():
        mapping = resolve_buddy_predicate_mapping_v4(predicate)
        if mapping is None or not mapping[0]:
            continue
        allowed = predicate_allowed_endpoints(mapping[0], vocabulary)
        if allowed is None:
            continue
        subjects, objects = allowed
        if mapping[1]:
            subjects, objects = objects, subjects
        source_kinds = tuple(sorted(k for k, native in CURRENT_V5_TARGET.buddy_to_dm_kind.items()
                                    if native in subjects))
        target_kinds = tuple(sorted(k for k, native in CURRENT_V5_TARGET.buddy_to_dm_kind.items()
                                    if native in objects))
        if source_kinds and target_kinds:
            rules.append(NativeEdgePromptRule(predicate, predicate_family_for_type(predicate),
                                              source_kinds, target_kinds))
    return tuple(rules)


def native_edge_prompt_markdown() -> str:
    lines = [
        "## Native relationship catalog",
        "Use only the predicates and endpoint kinds listed below. A valid tuple is not proof of a fact.",
        "Use exact IDs from the supplied node bank; do not invent a Party or any other endpoint.",
        "For character nodes, use the resolved PC/NPC reference kind when supplied; otherwise use npc.",
        "Keep a descriptive, source-backed label explaining the relationship, not merely the predicate name.",
        "Do not turn following into command, loading into ownership, or a report into independently verified truth.",
        "Do not change node kinds or invent facts to fit a tuple. Defer unsupported relationships for review.",
        "Review containment, movement, authority, threats, knowledge and participation where the source supports them.",
    ]
    for rule in native_edge_prompt_rules():
        lines.append(f"- {rule.predicate} [{rule.family}]: "
                     f"{','.join(rule.subject_kinds)} -> {','.join(rule.object_kinds)}")
    return "\n".join(lines)
