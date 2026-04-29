"""Stage B1 discourse classifier system prompt — separate from hub-routing (Stage B monolith)."""

from __future__ import annotations

import blake3
from typing import Any

from evals.sentence_routing_retrieval_falsification.discourse_schema import SCHEMA_SENTENCE_DISCOURSE_STATE_V1

DISCOURSE_SYSTEM_PROMPT_BASE: str = (
    "You classify each recap sentence_unit into structured discourse state for downstream hub routing.\n\n"
    "Output contract:\n"
    "- Return one JSON object matching the schema; no markdown fences.\n"
    "- Emit exactly one discourse row per sentence_unit in the user payload, same unit_id order.\n"
    "- Do NOT assign hub slugs or invent retrieval targets — classify roles and discourse mode only.\n"
    "- rationale must quote short phrases from sentence_unit.text supporting your classification.\n\n"
    "discourse_mode (choose one):\n"
    "- true_empty: bookkeeping, transitions, no durable retrieval subject.\n"
    "- explicit_pc: named manifest PCs have concrete in-unit roles (actor, object, addressee, "
    "rescuer, target, listener, locus, etc.).\n"
    "- explicit_party / implicit_party: joint band as grammatical actor (explicit) vs pronoun-led "
    "continuation with collective_actor (implicit).\n"
    "- previous_unit_pc_continuation: pronoun/deictic continuation bound to prior unit.\n"
    "- scene_owner_pc: continuing another PC's ongoing scene/thread.\n"
    "- topic_pc: PC is topic/object of decision, accusation, warning, question, plan — not necessarily actor.\n"
    "- perceiver_pc: PC finds/sees/hears/discovers focal content.\n"
    "- placeholder_only: focal is NPC/location/object without a hub.\n"
    "- pc_plus_missing_npc: PCs plus a named NPC without hub — missing_entity_bucket often npc_placeholder.\n\n"
    "Precedence / role preservation:\n"
    "- missing_entity_bucket is additive. If an unknown NPC/location/object is present, still fill every "
    "manifest PC role field supported by the sentence or local discourse state.\n"
    "- Do not let pc_plus_missing_npc erase a more specific PC role: preserve scene_owner_pc_slugs, "
    "topic_pc_slugs, direct_pc_slugs, and perceiver_pc_slugs when those roles are supported.\n"
    "- Use pc_plus_missing_npc as the discourse_mode only when the missing NPC is central and no more "
    "specific PC mode (scene_owner_pc, topic_pc, explicit_pc, perceiver_pc, party) is the better fit.\n\n"
    "Slug fields (manifest PC slugs only):\n"
    "- direct_pc_slugs: sentence-local role PCs.\n"
    "- topic_pc_slugs: PCs who are the topic/object/affected target of a decision, warning, plan, "
    "accusation, threat, promise, report, or instruction. Fill topic_pc_slugs even when other PCs are "
    "direct actors in the same unit, but do not add mere listeners, bystanders, or name-only mentions.\n"
    "- scene_owner_pc_slugs: PCs whose scene/thread continues here.\n"
    "- perceiver_pc_slugs: perceiving PCs.\n"
    "- collective_actor: null or \"the_party\" when the joint band is the collective actor.\n"
    "- party_expansion_allowed: true only when roster expansion to the_party is appropriate "
    "(group beat / discovery / travel as joint actor).\n"
    "- narrow_pc_only: true when only named in-unit PCs should route — suppress roster expansion.\n"
    "- continuation_from_unit_id: prior unit_id when previous-unit binding applies.\n"
    "- missing_entity_bucket: npc_placeholder, location_placeholder, event_or_object_placeholder, "
    "new_hub_candidate, true_empty, or null when not applicable.\n"
)

DISCOURSE_PROMPT_BASE_ID: str = blake3.blake3(DISCOURSE_SYSTEM_PROMPT_BASE.encode("utf-8")).hexdigest()[:24]


def build_discourse_system_prompt() -> tuple[str, str]:
    """Returns ``(system_text, discourse_prompt_id)``."""
    return DISCOURSE_SYSTEM_PROMPT_BASE, DISCOURSE_PROMPT_BASE_ID


def build_discourse_user_payload(
    *,
    campaign_id: Any,
    session: Any,
    recap_relative_path: Any,
    hub_manifest: list[dict[str, Any]],
    sentence_units: list[dict[str, Any]],
    routing_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """User JSON for B1 (global routing_context + sentence_units only)."""
    out: dict[str, Any] = {
        "campaign_id": campaign_id,
        "session": session,
        "recap_relative_path": recap_relative_path,
        "hub_manifest": hub_manifest,
        "sentence_units": sentence_units,
        "expected_schema": SCHEMA_SENTENCE_DISCOURSE_STATE_V1,
    }
    if routing_context:
        out["routing_context"] = routing_context
    return out
