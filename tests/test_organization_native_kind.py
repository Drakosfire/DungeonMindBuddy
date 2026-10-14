"""Future organization ingestion must not mint or bind expedition Parties."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from tests.test_candidate_graph_to_contribution import _minimal_graph
from graph_memory.candidate_graph_to_contribution import (
    load_typed_candidate_graph,
    kernel_kind_for_node_type,
)
from graph_memory.extract_identity_gate import _infer_object_kind
from graph_memory.worldbuilding_write_plan import (
    _resolve_bind_target,
    _map_node,
    WorldbuildingWritePlanError,
)
from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    _qualified_value,
    _qualified_edge_update,
    WorldGraphWriteError,
)
from dungeonmind.contracts.contribution import GraphContributionAssertionV2
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    edge_endpoint_kind_admission_reason,
)


def organization_node():
    payload = _minimal_graph(canon="worldbuilding_draft")
    payload["nodes"] = [payload["nodes"][0]]
    payload["edges"] = []
    payload["nodes"][0].update(
        node_id="org:college", label="The College", node_type="organization"
    )
    return load_typed_candidate_graph(payload).nodes[0]


def context(kind):
    obj = MutationObject(
        object_id="existing:college",
        label="The College",
        kind=kind,
        canon_state="canonical",
    )
    return WorldGraphMutationContext(
        world_id="world:test",
        revision_id="rev:one",
        head_revision_id="rev:one",
        objects={obj.object_id: obj},
    )


def test_actual_organization_contribution_and_native_qualification():
    node = organization_node()
    assertion = _map_node(
        node,
        source_revision_id="sha256:fixture",
        source_artifact_id="artifact:recap:longmont-c2:session-22",
        campaign_scope=None,
        source_uri="repo://corpus/synthetic.md",
        acceptance_state="accepted",
        identity_resolution_outcome="unresolved",
    )
    assert assertion.value["kind"] == "faction"
    native = _qualified_value(
        SimpleNamespace(
            assertion_kind=assertion.assertion_kind,
            value=json.dumps(assertion.value),
            assertion_id=assertion.assertion_id,
        )
    )
    assert json.loads(native)["dm_kind"] == "dnd5e:faction"
    assert json.loads(native)["kind"] != "party"


@pytest.mark.parametrize("existing_kind", ["party", "faction", "location"])
def test_context_cannot_retype_organization_by_same_name(existing_kind):
    assert _infer_object_kind(organization_node(), context(existing_kind)) == "faction"


def test_worldbuilding_bind_existing_rejects_same_named_party():
    with pytest.raises(WorldbuildingWritePlanError) as error:
        _resolve_bind_target(context("party"), organization_node(), "existing:college")
    assert error.value.code == "bind_target_kind_mismatch"
    assert (
        _resolve_bind_target(
            context("faction"), organization_node(), "existing:college"
        ).kind
        == "faction"
    )
    with pytest.raises(WorldbuildingWritePlanError):
        _resolve_bind_target(
            context("location"), organization_node(), "existing:college"
        )


@pytest.mark.parametrize("predicate", ["leads", "commands"])
def test_organization_relationship_uses_existing_native_endpoint_rules(predicate):
    assert (
        edge_endpoint_kind_admission_reason(
            buddy_predicate=predicate,
            from_buddy_kind="npc",
            to_buddy_kind=kernel_kind_for_node_type("organization"),
        )
        is None
    )
    assert (
        edge_endpoint_kind_admission_reason(
            buddy_predicate=predicate,
            from_buddy_kind="location",
            to_buddy_kind=kernel_kind_for_node_type("organization"),
        )
        is not None
    )
    native_edge = GraphContributionAssertionV2(
        assertion_id="edge:lead",
        assertion_kind="edge",
        subject_object_id="npc:teacher",
        object_object_id="org:college",
        predicate=predicate,
        label=predicate,
        value="{}",
    )
    qualified = _qualified_edge_update(
        native_edge,
        endpoint_kinds={
            "npc:teacher": "npc",
            "org:college": kernel_kind_for_node_type("organization"),
        },
    )
    assert json.loads(qualified["value"])["dm_predicate"] == "dnd5e:" + predicate
    with pytest.raises(WorldGraphWriteError):
        _qualified_edge_update(
            native_edge,
            endpoint_kinds={
                "npc:teacher": "location",
                "org:college": kernel_kind_for_node_type("organization"),
            },
        )


def test_explicit_party_and_group_behavior_preserved():
    assert kernel_kind_for_node_type("party") == "party"
    assert kernel_kind_for_node_type("group") == "group"
    assert kernel_kind_for_node_type("collective") == "party"
    assert (
        _resolve_bind_target(
            context("party"),
            replace(organization_node(), node_type="party"),
            "existing:college",
        ).kind
        == "party"
    )
