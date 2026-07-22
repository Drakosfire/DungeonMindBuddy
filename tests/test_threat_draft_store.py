from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.services.threat_draft_store import (
    ThreatDraftStoreError,
    create_threat_draft,
    get_threat_draft,
    list_threat_drafts,
    update_threat_draft,
)


def _create_request(**overrides: object) -> CreateThreatDraftRequest:
    payload = {
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "name": "Ironhide Brute",
        "description": "A brutal enforcer.",
        "threat_kind": "creature",
        "generation_intent": GenerationIntentV1(
            ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            target_cr="3",
        ),
        "graph_context_snapshot": GraphContextSnapshotV1(
            graph_revision_id="rev_graph_1",
            selected_node_ids=["node_a"],
            admitted_source_anchor_ids=["anchor_1"],
        ),
        "created_by": "gm",
    }
    payload.update(overrides)
    return CreateThreatDraftRequest.model_validate(payload)


def test_create_read_list_round_trip(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.draft_id == created.draft_id
    assert loaded.version == 1
    assert loaded.description == "A brutal enforcer."
    summaries = list_threat_drafts(tmp_path, campaign_id="campaign_1")
    assert len(summaries) == 1
    assert summaries[0].draft_id == created.draft_id


def test_update_increments_version_once(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    updated = update_threat_draft(
        tmp_path,
        created.draft_id,
        UpdateThreatDraftRequest(
            expected_version=1,
            name="Ironhide Brute",
            description="Updated description.",
            threat_kind="creature",
            generation_intent=created.generation_intent,
            encounter_context=created.encounter_context,
            graph_context_snapshot=created.graph_context_snapshot,
        ),
    )
    assert updated.version == 2
    assert updated.draft_id == created.draft_id
    assert updated.description == "Updated description."


def test_stale_update_writes_nothing(tmp_path: Path) -> None:
    created = create_threat_draft(tmp_path, _create_request())
    update_threat_draft(
        tmp_path,
        created.draft_id,
        UpdateThreatDraftRequest(
            expected_version=1,
            name="Ironhide Brute",
            description="First update.",
            threat_kind="creature",
            generation_intent=created.generation_intent,
            encounter_context=created.encounter_context,
            graph_context_snapshot=created.graph_context_snapshot,
        ),
    )
    with pytest.raises(ThreatDraftStoreError) as exc_info:
        update_threat_draft(
            tmp_path,
            created.draft_id,
            UpdateThreatDraftRequest(
                expected_version=1,
                name="Ironhide Brute",
                description="Stale update.",
                threat_kind="creature",
                generation_intent=created.generation_intent,
                encounter_context=created.encounter_context,
                graph_context_snapshot=created.graph_context_snapshot,
            ),
        )
    assert exc_info.value.status_code == 409
    loaded = get_threat_draft(tmp_path, created.draft_id)
    assert loaded.version == 2
    assert loaded.description == "First update."


def test_names_do_not_resolve_identity(tmp_path: Path) -> None:
    first = create_threat_draft(tmp_path, _create_request(name="Same Name"))
    second = create_threat_draft(tmp_path, _create_request(name="Same Name"))
    assert first.draft_id != second.draft_id
