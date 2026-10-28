"""Adapter scope and fail-closed controls; governed durable proof is separate."""

import copy

import pytest
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository
from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from apps.live_control_server.models.world_graph_object_projection import (
    WorldGraphObjectProjectionRequest,
)
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from tests._cutover_direct_dungeonmind_read_helpers import (
    CAMPAIGN_ONE,
    NOW,
    WORLD_ID,
    _FakeBundle,
    _payload,
    _receipt,
    _seed_sources,
    _meta,
)


def _services(schema="dm_union_graph_v7", mutate=None):
    graph = InMemoryWorldGraphRepository()
    parent = graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["fixture:legacy"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    payload = copy.deepcopy(_payload())
    if schema != "dm_union_graph_v6":
        payload["object_existence_support_schema"] = (
            "dm_independent_object_existence_support_v1"
        )
        hero = next(o for o in payload["objects"] if o["object_id"] == "obj:hero")
        hero["independent_existence_assertions"] = [
            {
                "label": "Hero in campaign two",
                "kind": hero["kind"],
                "assertion_metadata": _meta(
                    "asrt:hero:two", evidence=("ev:cellar",), campaign_scope="camp:two"
                ),
            }
        ]
    if mutate:
        mutate(payload)
    graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=parent.revision_id,
            expected_parent_revision_id=parent.revision_id,
            operation_ids=["fixture:child"],
            graph_schema=schema,
            graph_payload=payload,
            created_at=NOW,
        )
    )
    return direct.direct_services_from_bundle(
        _FakeBundle(graph, _seed_sources(), _receipt(WORLD_ID, parent.revision_id)),
        WORLD_ID,
    )


def _project(services, campaign, admissibility="gm", world=WORLD_ID):
    return direct.project_world_graph_direct(
        services,
        WorldGraphProjectionRequest(
            schema="dmb_world_graph_projection_request_v1",
            world_id=world,
            campaign_id=campaign,
            scope_mode="campaign",
            admissibility=admissibility,
        ),
    )


def test_independent_existence_is_visible_in_both_campaigns_without_leaking_elsewhere():
    services = _services()
    for campaign in (CAMPAIGN_ONE, "camp:two"):
        nodes = _project(services, campaign).nodes
        assert "obj:hero" in {n.node_id for n in nodes}
    assert "obj:hero" not in {n.node_id for n in _project(services, "camp:other").nodes}
    assert "obj:hero" not in {
        n.node_id for n in _project(services, "camp:two", "player").nodes
    }
    with pytest.raises(direct.DirectWorldGraphReadError):
        _project(services, CAMPAIGN_ONE, world="world:wrong")


def test_legacy_campaign_scope_and_player_visibility_remain_intact():
    services = _services("dm_union_graph_v6")
    assert "obj:hero" in {n.node_id for n in _project(services, CAMPAIGN_ONE).nodes}
    assert "obj:hero" not in {n.node_id for n in _project(services, "camp:two").nodes}
    assert {n.node_id for n in _project(services, CAMPAIGN_ONE, "player").nodes} == {
        "obj:road-sign"
    }


def test_complete_object_preserves_world_truth_and_existence_evidence():
    request = WorldGraphObjectProjectionRequest.model_validate(
        {
            "schema": "dmb_world_graph_object_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": "camp:other",
            "nodeId": "obj:hero",
            "admissibility": "gm",
        }
    )
    result = direct.get_complete_object_direct(_services(), request)
    encoded = result.model_dump_json()
    assert "asrt:hero:two" in encoded
    assert "ev:hero" in encoded
    assert "Hero in campaign two" in encoded


@pytest.mark.parametrize(
    "schema,mutate",
    [
        ("dm_union_graph_v999", None),
        ("dm_union_graph_v7", lambda p: p.pop("object_existence_support_schema")),
        (
            "dm_union_graph_v7",
            lambda p: p["objects"][-2]["independent_existence_assertions"][0][
                "assertion_metadata"
            ].update(evidence_ref_ids=["ev:forged"]),
        ),
    ],
)
def test_unknown_or_malformed_graph_fails_closed(schema, mutate):
    with pytest.raises(direct.DirectWorldGraphReadError) as error:
        _project(_services(schema, mutate), CAMPAIGN_ONE)
    assert error.value.code == "projection_integrity_error"
