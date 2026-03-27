from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.ingestion.fact_extractor import derive_truth_state
from src.reducer.canon_projection import project_entity_state

_SCHEMA_VERSION = "0.1.0"
_NOW = datetime(2026, 3, 27, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SliceEvidenceSeed:
    evidence_id: str
    document_id: str
    document_title: str
    document_type: str
    source_class: str
    canon_layer: str
    campaign_id: str | None
    section_path: list[str]
    source_order_index: int
    inferred_session: int | None
    anchor: str
    fallback_text: str
    stage: str


_ENTITY_CATALOG: dict[str, dict[str, Any]] = {
    "ent_mirathorn": {"display_name": "Mirathorn", "entity_type": "location"},
    "ent_secure_shipment_shepherds": {
        "display_name": "Secure Shipment Shepherds",
        "entity_type": "faction",
    },
    "ent_commander_elric_vane": {
        "display_name": "Commander Elric Vane",
        "entity_type": "npc",
    },
    "ent_captain_lysandra_ironveil": {
        "display_name": "Captain Lysandra Ironveil",
        "entity_type": "npc",
    },
}

_EVIDENCE_SEEDS: list[SliceEvidenceSeed] = [
    SliceEvidenceSeed(
        evidence_id="evu_world_approach",
        document_id="doc_city_of_mirathorn",
        document_title="The City of Mirathorn",
        document_type="world_reference",
        source_class="seed_reference",
        canon_layer="world",
        campaign_id=None,
        section_path=["Mirathorn Overview", "Approach to Mirathorn"],
        source_order_index=0,
        inferred_session=None,
        anchor="approaching mirathorn",
        fallback_text="You know you are approaching Mirathorn for a few reasons. The sound can be heard from kilometers away.",
        stage="instantiation",
    ),
    SliceEvidenceSeed(
        evidence_id="evu_world_governance",
        document_id="doc_city_of_mirathorn",
        document_title="The City of Mirathorn",
        document_type="world_reference",
        source_class="seed_reference",
        canon_layer="world",
        campaign_id=None,
        section_path=["Governance"],
        source_order_index=1,
        inferred_session=None,
        anchor="democratic city-state",
        fallback_text="A democratic city-state governed by a council representing races and guilds.",
        stage="instantiation",
    ),
    SliceEvidenceSeed(
        evidence_id="evu_campaign_planning_cult",
        document_id="doc_longmont_campaign_general_notes",
        document_title="Longmont Campaign General Notes",
        document_type="campaign_notes",
        source_class="planning_document",
        canon_layer="campaign",
        campaign_id="longmont-c1",
        section_path=["Cult Activities and Beliefs"],
        source_order_index=2,
        inferred_session=6,
        anchor="twisted meat",
        fallback_text="The Shepherds distribute twisted meat through local markets while pursuing human supremacy.",
        stage="zero_tick",
    ),
    SliceEvidenceSeed(
        evidence_id="evu_campaign_planning_vane",
        document_id="doc_longmont_campaign_general_notes",
        document_title="Longmont Campaign General Notes",
        document_type="campaign_notes",
        source_class="planning_document",
        canon_layer="campaign",
        campaign_id="longmont-c1",
        section_path=["Commander Elric Vane's Role"],
        source_order_index=3,
        inferred_session=6,
        anchor="commander vane",
        fallback_text="Commander Elric Vane serves as tactical leader and high priest in the cult.",
        stage="zero_tick",
    ),
    SliceEvidenceSeed(
        evidence_id="evu_campaign_live_arrival",
        document_id="doc_longmont_campaign_general_notes",
        document_title="Longmont Campaign General Notes",
        document_type="campaign_notes",
        source_class="observed_session_recap",
        canon_layer="campaign",
        campaign_id="longmont-c1",
        section_path=["Session 6", "The Road to Miraholm"],
        source_order_index=4,
        inferred_session=6,
        anchor="go to the gate, see the beginning of the protest",
        fallback_text="The party reached Mirathorn's gate and saw the beginning of a protest.",
        stage="live",
    ),
    SliceEvidenceSeed(
        evidence_id="evu_campaign_live_guard",
        document_id="doc_longmont_campaign_general_notes",
        document_title="Longmont Campaign General Notes",
        document_type="campaign_notes",
        source_class="observed_session_recap",
        canon_layer="campaign",
        campaign_id="longmont-c1",
        section_path=["Session 6", "The Road to Miraholm"],
        source_order_index=5,
        inferred_session=6,
        anchor="talked to captain lysandra ironveil",
        fallback_text="The party talked to Captain Lysandra Ironveil at the gate.",
        stage="live",
    ),
]


def _extract_anchor_line(text: str, anchor: str, fallback: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and anchor in line.lower():
            return line
    return fallback


def _sanitize_id(raw: str, prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_.:-")
    if not cleaned:
        cleaned = prefix
    if cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return cleaned


def _event_kind_for(source_class: str) -> str:
    if source_class == "seed_reference":
        return "world_baseline_capture"
    if source_class == "planning_document":
        return "planning_signal"
    return "live_session_update"


def _event_session_for(stage: str) -> tuple[str, int | None]:
    if stage == "instantiation":
        return "instantiation", None
    if stage == "zero_tick":
        return "zero_tick_plan", None
    return "live_session_06", 6


def _value(kind: str, label: str, normalized: str) -> dict[str, Any]:
    return {"kind": kind, "label": label, "normalized": normalized}


def _state_changes_for(evidence_id: str) -> list[dict[str, Any]]:
    if evidence_id == "evu_world_approach":
        return [
            {
                "subject_entity_id": "ent_mirathorn",
                "attribute": "atmosphere",
                "proposed_value": _value(
                    "state",
                    "Approach to Mirathorn carries a city-wide thunderous sound",
                    "thunderous_city_approach",
                ),
            }
        ]
    if evidence_id == "evu_world_governance":
        return [
            {
                "subject_entity_id": "ent_mirathorn",
                "attribute": "governance",
                "proposed_value": _value(
                    "scalar",
                    "Democratic city-state council represents races and guilds",
                    "democratic_city_council",
                ),
            }
        ]
    if evidence_id == "evu_campaign_planning_cult":
        return [
            {
                "subject_entity_id": "ent_secure_shipment_shepherds",
                "attribute": "goals",
                "proposed_value": _value(
                    "interpretive",
                    "Distribute twisted meat while advancing human supremacy",
                    "twisted_meat_distribution_human_supremacy",
                ),
            }
        ]
    if evidence_id == "evu_campaign_planning_vane":
        return [
            {
                "subject_entity_id": "ent_commander_elric_vane",
                "attribute": "role",
                "proposed_value": _value(
                    "scalar",
                    "Dual role: tactical commander and high priest of the Shepherds",
                    "dual_leader_high_priest",
                ),
            }
        ]
    if evidence_id == "evu_campaign_live_arrival":
        return [
            {
                "subject_entity_id": "ent_mirathorn",
                "attribute": "atmosphere",
                "proposed_value": _value(
                    "state",
                    "Gate approach is marked by active protest pressure",
                    "gate_protest_pressure",
                ),
            }
        ]
    if evidence_id == "evu_campaign_live_guard":
        return [
            {
                "subject_entity_id": "ent_captain_lysandra_ironveil",
                "attribute": "role",
                "proposed_value": _value(
                    "scalar",
                    "Gate captain coordinating arrivals during unrest",
                    "gate_captain_arrival_coordination",
                ),
            }
        ]
    return []


def _build_evidence(
    *,
    world_text: str,
    campaign_text: str,
    campaign_id: str,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    output: list[dict[str, Any]] = []
    stage_by_evidence_id: dict[str, str] = {}
    for seed in _EVIDENCE_SEEDS:
        source_text = world_text if seed.canon_layer == "world" else campaign_text
        text = _extract_anchor_line(source_text, seed.anchor, seed.fallback_text)
        evidence_campaign_id = campaign_id if seed.canon_layer == "campaign" else None
        output.append(
            {
                "schema_version": _SCHEMA_VERSION,
                "created_at": _NOW,
                "updated_at": _NOW,
                "record_status": "active",
                "evidence_id": seed.evidence_id,
                "document_id": seed.document_id,
                "document_type": seed.document_type,
                "document_title": seed.document_title,
                "source_class": seed.source_class,
                "canon_layer": seed.canon_layer,
                "campaign_id": evidence_campaign_id,
                "text": text,
                "section_path": seed.section_path,
                "paragraph_index": seed.source_order_index,
                "source_order_index": seed.source_order_index,
                "line_span": None,
                "char_span": None,
                "inferred_session": seed.inferred_session,
                "speaker_or_subject": None,
                "notes": None,
            }
        )
        stage_by_evidence_id[seed.evidence_id] = seed.stage
    return output, stage_by_evidence_id


def _build_entities(evidence_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used_entity_ids: set[str] = set()
    for unit in evidence_units:
        lower_text = str(unit["text"]).lower()
        for entity_id, entry in _ENTITY_CATALOG.items():
            if entry["display_name"].lower() in lower_text:
                used_entity_ids.add(entity_id)
        if unit["evidence_id"] == "evu_campaign_live_arrival":
            used_entity_ids.add("ent_mirathorn")
    entities: list[dict[str, Any]] = []
    for entity_id in sorted(used_entity_ids):
        entry = _ENTITY_CATALOG[entity_id]
        entities.append(
            {
                "schema_version": _SCHEMA_VERSION,
                "created_at": _NOW,
                "updated_at": _NOW,
                "record_status": "active",
                "entity_id": entity_id,
                "entity_type": entry["entity_type"],
                "display_name": entry["display_name"],
                "canonical_name": None,
                "aliases": [entry["display_name"]],
                "entity_status": "provisional",
                "merged_into_entity_id": None,
                "source_mention_ids": [f"men_{entity_id}"],
                "review_state": "reviewed",
                "notes": None,
            }
        )
    return entities


def _build_events(
    evidence_units: list[dict[str, Any]],
    *,
    stage_by_evidence_id: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    events: list[dict[str, Any]] = []
    stage_by_event_id: dict[str, str] = {}
    for unit in sorted(evidence_units, key=lambda item: int(item["source_order_index"])):
        evidence_id = str(unit["evidence_id"])
        stage = stage_by_evidence_id[evidence_id]
        session_id, session_number = _event_session_for(stage)
        event_id = _sanitize_id(f"evt_{evidence_id}", "evt")
        state_changes = _state_changes_for(evidence_id)
        participant_ids = sorted({change["subject_entity_id"] for change in state_changes})
        participants = [
            {"entity_id": entity_id, "role": "subject", "certainty": "confirmed"}
            for entity_id in participant_ids
        ]
        events.append(
            {
                "schema_version": _SCHEMA_VERSION,
                "created_at": _NOW,
                "updated_at": _NOW,
                "record_status": "active",
                "event_id": event_id,
                "event_kind": _event_kind_for(str(unit["source_class"])),
                "label": f"{unit['document_title']} :: {evidence_id}",
                "session_id": session_id,
                "session_number": session_number,
                "sequence_index_within_session": int(unit["source_order_index"]),
                "participants": participants,
                "source_evidence_ids": [evidence_id],
                "certainty": "confirmed",
                "location_id": "ent_mirathorn"
                if any(
                    change["subject_entity_id"] == "ent_mirathorn"
                    for change in state_changes
                )
                else None,
                "subevent_ids": [],
                "outcome_summary": str(unit["text"]),
                "state_changes": state_changes,
                "related_fact_ids": [],
                "notes": None,
            }
        )
        stage_by_event_id[event_id] = stage
    return events, stage_by_event_id


def _build_facts(
    *,
    events: list[dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    stage_by_event_id: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    facts: list[dict[str, Any]] = []
    stage_by_fact_id: dict[str, str] = {}
    for event in events:
        event_id = str(event["event_id"])
        source_evidence_id = str(event["source_evidence_ids"][0])
        evidence = evidence_by_id[source_evidence_id]
        truth_state, source_authority = derive_truth_state(
            str(evidence["canon_layer"]),
            str(evidence["source_class"]),
        )
        for idx, state_change in enumerate(event.get("state_changes", [])):
            fact_id = _sanitize_id(f"fact_{event_id}_{idx}", "fact")
            facts.append(
                {
                    "schema_version": _SCHEMA_VERSION,
                    "created_at": _NOW,
                    "updated_at": _NOW,
                    "record_status": "active",
                    "fact_id": fact_id,
                    "subject_entity_id": state_change["subject_entity_id"],
                    "attribute": state_change["attribute"],
                    "value": state_change["proposed_value"],
                    "truth_state": truth_state,
                    "source_authority": source_authority,
                    "evidence_ids": [source_evidence_id],
                    "derived_from_event_ids": [event_id],
                    "related_conflict_ids": [],
                    "manually_overridden": False,
                    "notes": None,
                    "asserted_in_session": event.get("session_number"),
                    "valid_from_session": event.get("session_number"),
                    "valid_to_session": None,
                    "sequence_index_within_session": event["sequence_index_within_session"],
                    "validity_state": "active",
                }
            )
            stage_by_fact_id[fact_id] = stage_by_event_id[event_id]
    return facts, stage_by_fact_id


def _build_conflicts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fact in facts:
        key = (str(fact["subject_entity_id"]), str(fact["attribute"]))
        grouped.setdefault(key, []).append(fact)

    conflicts: list[dict[str, Any]] = []
    for (entity_id, attribute), grouped_facts in sorted(grouped.items()):
        normalized_values = {
            str(fact["value"].get("normalized") or fact["value"]["label"]).lower()
            for fact in grouped_facts
        }
        if len(normalized_values) < 2:
            continue
        fact_ids = sorted(str(fact["fact_id"]) for fact in grouped_facts)
        conflicts.append(
            {
                "schema_version": _SCHEMA_VERSION,
                "created_at": _NOW,
                "updated_at": _NOW,
                "record_status": "active",
                "conflict_id": _sanitize_id(f"conf_{entity_id}_{attribute}", "conf"),
                "conflict_type": "source_conflict",
                "entity_id": entity_id,
                "attribute": attribute,
                "fact_ids": fact_ids,
                "mention_ids": [],
                "candidate_entity_ids": [],
                "blocking": False,
                "severity": "warning",
                "resolution_decision_id": None,
                "notes": "Auto-detected attribute divergence across canon layers.",
                "conflict_status": "open",
            }
        )
    return conflicts


def _build_canon_decisions(
    *,
    conflicts: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    campaign_id: str,
) -> list[dict[str, Any]]:
    atmosphere_conflict = next(
        (
            conflict
            for conflict in conflicts
            if conflict["entity_id"] == "ent_mirathorn"
            and conflict["attribute"] == "atmosphere"
        ),
        None,
    )
    if atmosphere_conflict is None:
        return []

    selected_fact_id = ""
    for fact in facts:
        if fact["fact_id"] not in atmosphere_conflict["fact_ids"]:
            continue
        normalized = str(fact["value"].get("normalized"))
        if normalized == "gate_protest_pressure":
            selected_fact_id = str(fact["fact_id"])
            break

    if not selected_fact_id:
        return []

    decision_id = "dec_mirathorn_atmosphere_live_override"
    return [
        {
            "schema_version": _SCHEMA_VERSION,
            "created_at": _NOW,
            "updated_at": _NOW,
            "record_status": "active",
            "decision_id": decision_id,
            "decision_kind": "select_canon_fact",
            "target_type": "attribute_projection",
            "target_id": "ent_mirathorn:atmosphere",
            "entity_id": "ent_mirathorn",
            "attribute": "atmosphere",
            "campaign_id": campaign_id,
            "resolves_conflict_ids": [atmosphere_conflict["conflict_id"]],
            "rationale": "Current campaign session establishes gate protest as active atmosphere.",
            "decided_at": _NOW,
            "decided_by": "slice_hard_gate",
            "supersedes_decision_id": None,
            "effect": {
                "scope": "current_projection",
                "action_summary": "Select campaign live atmosphere fact over world baseline.",
                "selected_fact_ids": [selected_fact_id],
                "rejected_fact_ids": [],
                "retracted_fact_ids": [],
                "merged_entity_ids": [],
                "result_entity_id": None,
                "effective_from_session": 6,
                "effective_to_session": None,
            },
            "notes": None,
        }
    ]


def _stage_rank(stage: str) -> int:
    if stage == "instantiation":
        return 0
    if stage == "zero_tick":
        return 1
    return 2


def _facts_up_to_stage(
    facts: list[dict[str, Any]],
    *,
    stage_by_fact_id: dict[str, str],
    stage: str,
) -> list[dict[str, Any]]:
    max_rank = _stage_rank(stage)
    return [
        fact
        for fact in facts
        if _stage_rank(stage_by_fact_id[str(fact["fact_id"])]) <= max_rank
    ]


def _projection_delta(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    before_entities = before.get("entities", {})
    after_entities = after.get("entities", {})
    all_entities = sorted(set(before_entities) | set(after_entities))

    for entity_id in all_entities:
        before_attrs = before_entities.get(entity_id, {}).get("attributes", {})
        after_attrs = after_entities.get(entity_id, {}).get("attributes", {})
        all_attrs = sorted(set(before_attrs) | set(after_attrs))
        for attribute in all_attrs:
            before_value = before_attrs.get(attribute, {}).get("value_normalized")
            after_value = after_attrs.get(attribute, {}).get("value_normalized")
            if before_value == after_value:
                continue
            deltas.append(
                {
                    "entity_id": entity_id,
                    "attribute": attribute,
                    "before": before_value,
                    "after": after_value,
                }
            )
    return deltas


def build_mirathorn_event_slice(
    *,
    world_text: str,
    campaign_text: str,
    campaign_id: str = "longmont-c1",
) -> dict[str, Any]:
    evidence_units, stage_by_evidence_id = _build_evidence(
        world_text=world_text,
        campaign_text=campaign_text,
        campaign_id=campaign_id,
    )
    entities = _build_entities(evidence_units)
    events, stage_by_event_id = _build_events(
        evidence_units,
        stage_by_evidence_id=stage_by_evidence_id,
    )
    evidence_by_id = {entry["evidence_id"]: entry for entry in evidence_units}
    facts, stage_by_fact_id = _build_facts(
        events=events,
        evidence_by_id=evidence_by_id,
        stage_by_event_id=stage_by_event_id,
    )
    conflicts = _build_conflicts(facts)
    canon_decisions = _build_canon_decisions(
        conflicts=conflicts,
        facts=facts,
        campaign_id=campaign_id,
    )

    instantiation_facts = _facts_up_to_stage(
        facts,
        stage_by_fact_id=stage_by_fact_id,
        stage="instantiation",
    )
    zero_tick_facts = _facts_up_to_stage(
        facts,
        stage_by_fact_id=stage_by_fact_id,
        stage="zero_tick",
    )
    live_facts = _facts_up_to_stage(
        facts,
        stage_by_fact_id=stage_by_fact_id,
        stage="live",
    )

    projection_instantiation = project_entity_state(
        evidence_units=evidence_units,
        facts=instantiation_facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id=campaign_id,
    )
    projection_zero_tick = project_entity_state(
        evidence_units=evidence_units,
        facts=zero_tick_facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id=campaign_id,
    )
    projection_live_state = project_entity_state(
        evidence_units=evidence_units,
        facts=live_facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=campaign_id,
    )

    return {
        "evidence_units": evidence_units,
        "entities": entities,
        "events": events,
        "facts": facts,
        "conflicts": conflicts,
        "canon_decisions": canon_decisions,
        "projection_instantiation": projection_instantiation,
        "projection_zero_tick": projection_zero_tick,
        "projection_live_state": projection_live_state,
        "projection_deltas": {
            "instantiation_to_zero_tick": _projection_delta(
                projection_instantiation, projection_zero_tick
            ),
            "zero_tick_to_live_state": _projection_delta(
                projection_zero_tick, projection_live_state
            ),
        },
        "stage_artifacts": {
            "chunks": evidence_units,
            "entities": entities,
            "facts": facts,
            "events": events,
        },
    }
