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
    "- placeholder_only: focal is NPC/location/object without a hub and no manifest PC/party role applies.\n\n"
    "Precedence / role preservation:\n"
    "- missing_entity_bucket is additive, not a discourse mode. If an unknown NPC/location/object is present, still fill every "
    "manifest PC role field supported by the sentence or local discourse state.\n"
    "- When named manifest PCs have concrete in-unit roles and a session NPC/non-manifest entity also appears, "
    "prefer the specific PC mode (usually explicit_pc, topic_pc, scene_owner_pc, or perceiver_pc) and represent "
    "the non-manifest entity with missing_entity_bucket (usually npc_placeholder). Do not invent a special PC+NPC mode.\n\n"
    "Per-unit routing_context (optional; benchmark harness only):\n"
    "- When a sentence_unit object includes a \"routing_context\" field, those keys apply **only** to that unit; "
    "they supplement top-level user payload routing_context (roster labels, session_pc_roster_slugs).\n"
    "- Top-level routing_context.session_npc_names, when present, is negative evidence for PC routing: "
    "those names are known session NPCs/non-PCs. Never map them to manifest PC slugs. If a session NPC "
    "is focal and no NPC hub is in hub_manifest, use missing_entity_bucket npc_placeholder; if a manifest PC "
    "is also named in the same unit, preserve that PC role additively.\n"
    "- Optional routing_context.session_npc_candidate_names / session_location_candidate_names (Stage 1 lists): "
    "when non-empty, substring-match against unit text (case-insensitive). Use only as soft anchors — they do "
    "not authorize inventing manifest PC slugs. When a focal non-manifest person matches an NPC candidate, "
    "prefer missing_entity_bucket npc_placeholder; when a focal place matches a location candidate with no "
    "manifest PC scene role, prefer missing_entity_bucket location_placeholder. Still obey narrow_pc_only and "
    "active_scene_owner_hubs when present.\n"
    "- Keys: active_scene_owner_hubs (list of manifest PC hub slugs), active_collective_actor (e.g. \"the_party\"), "
    "party_expansion_allowed (boolean), narrow_pc_only (boolean).\n"
    "- When active_scene_owner_hubs lists manifest PC slugs and the unit is narrative content rather than "
    "metadata/bookkeeping, treat that per-unit scene-owner context as authoritative for this unit: use "
    "discourse_mode scene_owner_pc and copy active_scene_owner_hubs into scene_owner_pc_slugs. Do this even "
    "when the grammatical subject is a session NPC/non-manifest character (for example Stacey/Stuart in a "
    "Bonogo scene); represent those non-manifest subjects with missing_entity_bucket npc_placeholder.\n"
    "- When active_collective_actor is \"the_party\" and party_expansion_allowed is true, prefer discourse_mode "
    "implicit_party with collective_actor \"the_party\" and party_expansion_allowed true when the unit is "
    "pronoun-led joint discovery, movement, arrival, or encounter — not pure scenery with no group/PC subject.\n"
    "- When narrow_pc_only is true on the unit, set narrow_pc_only true on the row; do not emit collective_actor "
    "\"the_party\" or roster expansion unless the unit text supports a joint-band actor.\n"
    "- Context expiry: sentence_unit.routing_context.active_scene_owner_hubs applies **only** to that exact unit. "
    "Do not carry scene-owner continuity into a later unit solely via continuation_from_unit_id — later units need "
    "their own text-bound PC antecedent, their own sentence_unit.routing_context, or a mode justified by this unit's "
    "text alone.\n\n"
    "Slug fields (manifest PC slugs only):\n"
    "- Never list a manifest PC slug unless that PC is named in the unit text, is the unambiguous antecedent of a "
    "pronoun/deictic in the unit (including continuation_from_unit_id when prior-unit binding applies), or appears "
    "in this sentence_unit's routing_context.active_scene_owner_hubs when present. Names that are not manifest PCs "
    "(NPCs, non-roster companions) are never slugs — use missing_entity_bucket npc_placeholder or another placeholder "
    "as appropriate.\n"
    "- direct_pc_slugs: sentence-local role PCs — addressed, speaking, intervening, deciding, rescuing, "
    "physically acting, or otherwise interacting in this sentence.\n"
    "- topic_pc_slugs: PCs who are the topic/object/affected target of a decision, warning, plan, "
    "accusation, threat, promise, report, or instruction **without** taking an interaction role in this "
    "sentence (for example \"how should we handle Bonogo?\" while others speak — Bonogo belongs here, not in "
    "direct_pc_slugs). Fill topic_pc_slugs even when other PCs are direct actors in the same unit, but do "
    "not add mere listeners, bystanders, or name-only mentions.\n"
    "- Topic-only separation: if the unit asks how to deal with PC Z while PCs X and/or Y converse or "
    "intervene, put Z in topic_pc_slugs only unless Z also speaks or acts in the same sentence.\n"
    "- Mixed direct + topic in one unit: when at least one manifest PC belongs in direct_pc_slugs and "
    "another manifest PC belongs only in topic_pc_slugs, keep discourse_mode explicit_pc (not topic_pc); "
    "use topic_pc discourse_mode only when no manifest PC has a sentence-local interaction role worth "
    "direct_pc_slugs.\n"
    "- scene_owner_pc_slugs: PCs whose scene/thread continues here.\n"
    "- perceiver_pc_slugs: perceiving PCs.\n"
    "- collective_actor: null or \"the_party\" when the joint band is the collective actor.\n"
    "- Party honor / collective labels (always use routing_context; never invent a campaign-specific band name):\n"
    "  When routing_context.pc_party_names is non-empty, treat each entry as an in-world label for the same "
    "adventuring band as routing_context.session_pc_roster_slugs (substring match in unit text, case-insensitive).\n"
    "  Aftermath / gratitude / congratulations / shared-credit beats: generic phrases such as \"the heroes\", "
    "\"the party\", \"the group\", \"the team\", or text matching a pc_party_names label usually refer to the "
    "full session roster as joint recipients of credit. Prefer discourse_mode explicit_party or implicit_party "
    "with collective_actor \"the_party\" and party_expansion_allowed true unless narrow_pc_only is true or the "
    "sentence explicitly narrows credit to named PCs only.\n"
    "- party_expansion_allowed: true only when roster expansion to the_party is appropriate "
    "(group beat / discovery / travel as joint actor).\n"
    "- Party flag consistency: if discourse_mode is explicit_party or implicit_party and collective_actor is "
    "\"the_party\", set party_expansion_allowed=true unless narrow_pc_only is true or the unit is pure scenery/object "
    "narration with no group or manifest PC as subject (then prefer true_empty or a placeholder mode without "
    "collective_actor \"the_party\").\n"
    "- Narrow-multi-PC (overrides explicit_party, implicit_party, and Party flag consistency; mirrors Stage B monolith): "
    "When the unit names two or more manifest PCs each in a **distinct in-unit** role in that sentence (actor+object, "
    "rescuer+target, addressee+speaker, or multiple co-actors in the same action clause like 'Ephanna, Karsemine, and "
    "Caelynn relay their findings' or 'continue to battle' with each name in that list), use discourse_mode **explicit_pc** only: fill "
    "direct_pc_slugs and topic_*/scene_owner_/perceiver_ as appropriate, set collective_actor to null, "
    "party_expansion_allowed to false, and do **not** set collective_actor to \"the_party\" or use roster expansion. "
    "If a name is not a manifest PC (companion, NPC, etc.), it is a missing-entity/placeholder, not a trigger for "
    "\"the_party\" for the manifest names in the same unit. The joint-band / party-line rules do not apply in this pattern.\n"
    "- PCs listed only in topic_pc_slugs do not count toward the Narrow-multi-PC \"two or more manifest PCs\" "
    "threshold; that threshold applies only to PCs that carry direct/scene_owner/perceiver roles in the same unit.\n"
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
