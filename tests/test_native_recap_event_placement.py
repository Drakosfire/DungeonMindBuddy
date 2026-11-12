"""Campaign timeline placement at the native recap prepare/confirm boundary."""

import copy
from datetime import UTC, datetime

import pytest

from tests.test_native_recap_preparation import (
    CAMPAIGN_ID, META, SPACE_ID, PublishKnowledgeRevisionCommand,
    _source_order_candidate, choice, confirm, confirmation, lane,
)


def _declare_campaign(lane, count, *, existing_npc=False):
    head = lane.repo.get_head(SPACE_ID).head_revision_id
    snapshot = lane.repo.get_revision(SPACE_ID, head)
    payload = copy.deepcopy(snapshot.graph_payload)
    # Reuse existing synthetic object identities; classification is the
    # governed declaration that binds each target to this exact scope.
    identities = ("ent:location",) if existing_npc else ("ent:pippa", "ent:location")[:count]
    for index, identity in enumerate(identities):
        if identity != "ent:pippa":
            payload["entities"].append({"schema_version": "dm_entity_v1", "entity_id": identity})
        payload["assertions"].append({
            "assertion_id": f"asrt:campaign-fixture-{index}",
            "subject_entity_id": identity,
            "predicate": "dnd5e:classification",
            "value": {"kind": "term_ref", "term": "dungeonbuddy:campaign"},
            "metadata": copy.deepcopy(META) | {
                "scope": [{"axis": "dungeonbuddy.scope:campaign", "value": CAMPAIGN_ID}],
            },
        })
    if existing_npc:
        payload["assertions"].append({
            **payload["assertions"][-1],
            "assertion_id": "asrt:placement-fixture-npc",
            "subject_entity_id": "ent:pippa",
            "value": {"kind": "term_ref", "term": "dnd5e:npc"},
        })
    lane.repo.publish_revision(PublishKnowledgeRevisionCommand(
        space_id=SPACE_ID, parent_revision_id=head, expected_parent_revision_id=head,
        operation_ids=["campaign-fixture-declaration"], graph_schema=snapshot.revision.graph_schema,
        graph_payload=payload, domain_contract_ref=snapshot.revision.domain_contract_ref,
        semantic_profile_ref=snapshot.revision.semantic_profile_ref, created_at=datetime.now(UTC),
    ))
    lane.body["expected_parent_revision_id"] = lane.repo.get_head(SPACE_ID).head_revision_id


def _select(lane, session=8):
    _source_order_candidate(lane)
    lane.body["selections"][0] = choice("arrival", fields=("label", "node_type", "description"))
    lane.body["selections"].append({
        "kind": "placement", "record_id": "arrival", "action": "create",
        "metadata": copy.deepcopy(META) | {
            "claim_mode": "dungeonbuddy.claim:observed_event",
            "temporal_scope": {"kind": "domain_ref", "schema_term": "dungeonbuddy.time:fictional_anchor_v1",
                               "payload": {"start": {"session": session}}},
        },
    })


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_reviewed_placement_commits_to_scoped_campaign(lane):
    _declare_campaign(lane, 1)
    _select(lane)
    packet = confirmation(lane)
    response = confirm(lane, packet)
    assert response.status_code == 200, response.text
    child = lane.repo.get_revision(SPACE_ID, response.json()["result"]["child_revision_id"])
    rows = [row for row in child.graph_payload["assertions"]
            if row["predicate"] == "dungeonbuddy.custom:on_timeline"]
    assert len(rows) == 1
    assert rows[0]["value"]["entity_id"] == "ent:pippa"
    assert rows[0]["metadata"]["temporal_scope"]["payload"] == {"start": {"session": 8}}
    assert lane.support_ids["first"] in rows[0]["metadata"]["evidence_ref_ids"]
    assert confirm(lane, packet).json()["result"] == response.json()["result"]


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
@pytest.mark.parametrize("count,session,code", [
    (0, 8, "campaign_timeline_requires_unique_identity"),
    (2, 8, "campaign_timeline_requires_unique_identity"),
    (1, 9, "event_placement_requires_source_session"),
])
def test_invalid_placement_preserves_head(lane, count, session, code):
    if count:
        _declare_campaign(lane, count)
    _select(lane, session)
    before = lane.repo.get_head(SPACE_ID).head_revision_id
    response = lane.post()
    assert response.status_code == 409, response.text
    assert code in response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == before


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_held_placement_does_not_require_campaign_declaration(lane):
    _select(lane)
    lane.body["selections"][-1].update(action="defer", metadata=None)
    response = lane.post()
    assert response.status_code == 200, response.text
    packet = {key: response.json()[key] for key in ("envelope", "prepared", "token")}
    result = confirm(lane, packet)
    assert result.status_code == 200, result.text
    child = lane.repo.get_revision(SPACE_ID, result.json()["result"]["child_revision_id"])
    assert not any(row["predicate"] == "dungeonbuddy.custom:on_timeline"
                   for row in child.graph_payload["assertions"])


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_placement_cannot_reuse_incompatible_occurrence_identity(lane):
    _declare_campaign(lane, 1, existing_npc=True)
    _select(lane)
    # Remove precedence so the placement boundary itself owns the refusal.
    lane.body["selections"] = [s for s in lane.body["selections"] if s["kind"] != "edge"]
    lane.body["selections"][0].update(action="use_existing", entity_id="ent:pippa")
    before = lane.repo.get_head(SPACE_ID).head_revision_id
    response = lane.post()
    assert response.status_code == 409, response.text
    assert "placement_incompatible_occurrence_identity" in response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == before
