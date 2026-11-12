"""Campaign timeline placement at the native recap prepare/confirm boundary."""

import copy
from datetime import UTC, datetime

import pytest

from tests.test_native_recap_preparation import (
    CAMPAIGN_ID, META, SPACE_ID, PublishKnowledgeRevisionCommand,
    _source_order_candidate, choice, confirm, confirmation, lane,
)


def _declare_campaign(lane, count, *, existing_npc=False, alternate_timeline=False):
    head = lane.repo.get_head(SPACE_ID).head_revision_id
    snapshot = lane.repo.get_revision(SPACE_ID, head)
    payload = copy.deepcopy(snapshot.graph_payload)
    # Reuse existing synthetic object identities; classification is the
    # governed declaration that binds each target to this exact scope.
    identities = ("ent:location",) if existing_npc or alternate_timeline else ("ent:pippa", "ent:location")[:count]
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


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_later_review_cannot_place_same_event_again(lane):
    _declare_campaign(lane, 1)
    _select(lane)
    response = confirm(lane, confirmation(lane))
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    existing = next(item["durable_object_id"] for item in result["object_results"]
                    if item["client_op_id"] == "record:0")
    lane.body["expected_parent_revision_id"] = result["child_revision_id"]
    lane.body["selections"] = [s for s in lane.body["selections"] if s["kind"] != "edge"]
    lane.body["selections"][0].update(action="use_existing", entity_id=existing)
    response = lane.post()
    assert response.status_code == 409, response.text
    assert "event_already_placed_on_timeline" in response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == result["child_revision_id"]


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_placement_refuses_conflicting_classification_in_same_review(lane):
    _declare_campaign(lane, 1, alternate_timeline=True)
    _select(lane)
    lane.payload["nodes"][1]["node_type"] = "character"
    lane.refresh()
    lane.body["selections"] = [
        selection for selection in lane.body["selections"] if selection["kind"] != "edge"
    ]
    # Declare the timeline on a new identity, leaving the reused object unclassified.
    lane.body["selections"][0].update(action="use_existing", entity_id="ent:pippa")
    lane.body["selections"][1] = choice(
        "discussion", action="use_existing", entity_id="ent:pippa", fields=("node_type",),
    )
    before = lane.repo.get_head(SPACE_ID).head_revision_id
    response = lane.post()
    assert response.status_code == 409, response.text
    assert "placement_incompatible_occurrence_identity" in response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == before


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_generic_review_edge_cannot_publish_a_timeline_placement(lane):
    _source_order_candidate(lane)
    lane.payload["edges"][0]["relationship_type"] = "on_timeline"
    lane.refresh()
    before = lane.repo.get_head(SPACE_ID).head_revision_id
    response = lane.post()
    assert response.status_code == 409, response.text
    assert "timeline_edge_requires_reviewed_placement" in response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == before


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
@pytest.mark.parametrize("scope_mode", ["campaign", "world"])
def test_timeline_search_discovers_placed_event_relationships(lane, monkeypatch, scope_mode):
    from types import SimpleNamespace
    from uuid import uuid4

    from application_state.agent_conversation.native_plan_assertions import (
        NativePlanAssertionReadAuthorizedV1,
    )
    from apps.live_control_server.services import native_graph_reads
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal

    _declare_campaign(lane, 1)
    _select(lane)
    response = confirm(lane, confirmation(lane))
    assert response.status_code == 200, response.text
    revision = response.json()["result"]["child_revision_id"]
    child = lane.repo.get_revision(SPACE_ID, revision)
    objects = {row["client_op_id"]: row["durable_object_id"]
               for row in response.json()["result"]["object_results"]}
    arrival = objects["record:0"]
    edge, = [row for row in child.graph_payload["assertions"]
             if row["predicate"] == "dungeonbuddy.custom:precedes"
             and row["subject_entity_id"] == arrival]

    def timeline_search_only(self, context, question):
        return SimpleNamespace(
            identity=SimpleNamespace(space_id=SPACE_ID, revision_id=revision),
            result_digest="a" * 64,
            completeness=SimpleNamespace(status="complete"),
            hits=[SimpleNamespace(entity=SimpleNamespace(entity_id="ent:pippa"))],
        )

    monkeypatch.setattr(native_graph_reads.SearchReadService, "search_entities", timeline_search_only)
    principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    binding = SimpleNamespace(managed_world_id="managed", **lane.bound)
    context, query = native_graph_reads.prepare_query(
        "managed", "What happened on the timeline?", principal, repository=lane.repo,
        resolve_binding=lambda _: binding, scope_mode=scope_mode,
        campaign_id=CAMPAIGN_ID if scope_mode == "campaign" else None,
    )
    ids = {match.assertion_id for match in query.assertion_matches}
    if scope_mode == "world":
        assert edge["assertion_id"] not in ids
        return

    assert edge["assertion_id"] in ids
    grant = NativePlanAssertionReadAuthorizedV1(
        event_id=uuid4(), sequence=0, provider_attempt_id=uuid4(),
        query_sha256=query.sha256, assertion_ids=(edge["assertion_id"],),
    )
    reads, unavailable = native_graph_reads.read_selected(context, grant, principal)
    assert not unavailable
    read, = reads
    assert read.spans
