"""Synthetic owning-boundary proof for the SBW08 graph contract."""
from __future__ import annotations

from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
    parse_external_resource_assertion,
    parse_threat_statblock_binding_assertion,
)

WORLD_ID = "sbw08-test-world"
CAMPAIGN_ID = "longmont-c2"
THREAT_ID = "threat:sbw08-synthetic"
STATBLOCK_ID = "sb_w08"
REVISION_ID = "rev_1"
DIGEST = f"sha256:{'a' * 64}"


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:sbw08-baseline"],
    )
    return tmp_path


def _binding(
    *,
    revision_id: str = REVISION_ID,
    digest: str = DIGEST,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
) -> dict[str, str | None]:
    return {
        "schema": "dmb_threat_statblock_binding_v1",
        "binding_id": compute_binding_id(
            threat_node_id=THREAT_ID,
            provider=PROVIDER,
            statblock_id=STATBLOCK_ID,
            revision_id=revision_id,
            contract=CONTRACT,
            contract_version=CONTRACT_VERSION,
            definition_digest=digest,
            role=role,
            phase_key=phase_key,
            variant_label=variant_label,
        ),
        "provider": PROVIDER,
        "statblock_id": STATBLOCK_ID,
        "revision_id": revision_id,
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "definition_digest": digest,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }


def _resource_value() -> dict[str, object]:
    return {
        "kind": "external_resource",
        "role": "statblock",
        "external_resource": {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": STATBLOCK_ID,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        },
    }


def _binding_value(binding: dict[str, str | None]) -> dict[str, object]:
    return {
        "edge_id": edge_id_from_binding_id(str(binding["binding_id"])),
        "direction": "outbound",
        "threat_statblock_binding": binding,
    }


def _contribution(*assertions):
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:sbw08",
        source_revision_id=f"sbw08-{len(assertions)}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _request(revision_pin: str | None = None) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        revision_pin=revision_pin,
    )


def test_strict_contract_rejects_unknown_mechanics_and_endpoint_mismatch() -> None:
    value = _resource_value()
    value_with_provenance = {
        **value,
        "source_domain": "manual_seed",
        "evidence_ref_ids": ["evidence:sbw08"],
        "source_artifact_id": "graph-native:sbw08",
    }
    assert parse_external_resource_assertion(
        subject_node_id=external_statblock_node_id(STATBLOCK_ID),
        value=value_with_provenance,
    ) is not None
    with pytest.raises(ValueError, match="mechanics fields"):
        parse_external_resource_assertion(
            subject_node_id=external_statblock_node_id(STATBLOCK_ID),
            value={**value, "definition": {"forbidden": True}},
        )
    with pytest.raises(ValueError):
        parse_external_resource_assertion(
            subject_node_id=external_statblock_node_id(STATBLOCK_ID),
            value={
                **value,
                "external_resource": {
                    **value["external_resource"],
                    "schema": "dmb_external_resource_v2",
                },
            },
        )
    with pytest.raises(ValueError):
        parse_external_resource_assertion(
            subject_node_id=external_statblock_node_id(STATBLOCK_ID),
            value={
                **value,
                "external_resource": {
                    **value["external_resource"],
                    "unexpected": "rejected",
                },
            },
        )

    binding = _binding()
    with pytest.raises(ValueError, match="target"):
        parse_threat_statblock_binding_assertion(
            subject_node_id=THREAT_ID,
            target_node_id=external_statblock_node_id("sb_w09"),
            predicate="uses_statblock",
            value=_binding_value(binding),
        )
    with pytest.raises(ValueError):
        parse_threat_statblock_binding_assertion(
            subject_node_id=THREAT_ID,
            target_node_id=external_statblock_node_id(STATBLOCK_ID),
            predicate="uses_statblock",
            value={
                **_binding_value(binding),
                "definition": {"rules_elements": []},
            },
        )
    with pytest.raises(ValueError, match="phase_key"):
        parse_threat_statblock_binding_assertion(
            subject_node_id=THREAT_ID,
            target_node_id=external_statblock_node_id(STATBLOCK_ID),
            predicate="uses_statblock",
            value=_binding_value(_binding(role="phase")),
        )


def test_binding_identity_is_deterministic_and_semantic() -> None:
    original = _binding()
    assert _binding() == original
    changed_revision = _binding(revision_id="rev_2")
    changed_digest = _binding(digest=f"sha256:{'b' * 64}")
    changed_role = _binding(role="alternate")
    assert {
        original["binding_id"],
        changed_revision["binding_id"],
        changed_digest["binding_id"],
        changed_role["binding_id"],
    }.__len__() == 4

    tampered = {**original, "revision_id": "rev_2"}
    with pytest.raises(ValueError, match="binding_id"):
        parse_threat_statblock_binding_assertion(
            subject_node_id=THREAT_ID,
            target_node_id=external_statblock_node_id(STATBLOCK_ID),
            predicate="uses_statblock",
            value=_binding_value(tampered),
        )


def test_publish_reload_replay_and_pinned_projection(seeded_root: Path) -> None:
    threat = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        label="Synthetic Threat",
        campaign_scope=CAMPAIGN_ID,
        value={
            "kind": "threat",
            "role": "threat",
            "source_domains": ["manual_seed"],
        },
    )
    threat_result = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(threat)
    )
    assert threat_result.published is True

    binding = _binding()
    resource = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=external_statblock_node_id(STATBLOCK_ID),
        label="External statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_resource_value(),
    )
    edge = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        target_node_id=external_statblock_node_id(STATBLOCK_ID),
        predicate="uses_statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_binding_value(binding),
    )
    contribution = _contribution(resource, edge)
    result = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    assert result.revision_id is not None

    replay = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=contribution
    )
    assert replay.published is False
    assert replay.revision_id == result.revision_id

    _head, _revision, store = kernel.open_current_world_graph(seeded_root, WORLD_ID)
    assert store.nodes[external_statblock_node_id(STATBLOCK_ID)].external_resource is not None
    edge_id = edge_id_from_binding_id(str(binding["binding_id"]))
    assert store.edges[edge_id].threat_statblock_binding is not None

    projection = kernel.project_world_graph(
        seeded_root, _request(revision_pin=result.revision_id)
    )
    resource_view = next(
        node
        for node in projection.nodes
        if node.node_id == external_statblock_node_id(STATBLOCK_ID)
    )
    binding_view = next(item for item in projection.relationships if item.edge_id == edge_id)
    assert resource_view.external_resource is not None
    assert resource_view.external_resource.resource_id == STATBLOCK_ID
    assert binding_view.threat_statblock_binding is not None
    assert binding_view.threat_statblock_binding.revision_id == REVISION_ID


def test_two_primary_bindings_project_without_implicit_winner(seeded_root: Path) -> None:
    threat = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        label="Synthetic Threat",
        campaign_scope=CAMPAIGN_ID,
        value={"kind": "threat", "role": "threat", "source_domains": ["manual_seed"]},
    )
    assert kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(threat)
    ).published
    resource = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=external_statblock_node_id(STATBLOCK_ID),
        label="External statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_resource_value(),
    )
    first = _binding()
    second = _binding(revision_id="rev_2", digest=f"sha256:{'b' * 64}")
    edges = [
        kernel.build_assertion(
            assertion_kind="edge",
            acceptance_state="accepted",
            subject_node_id=THREAT_ID,
            target_node_id=external_statblock_node_id(STATBLOCK_ID),
            predicate="uses_statblock",
            campaign_scope=CAMPAIGN_ID,
            value=_binding_value(binding),
        )
        for binding in (first, second)
    ]
    assert kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(resource, *edges)
    ).published
    projection = kernel.project_world_graph(seeded_root, _request())
    bindings = [
        item.threat_statblock_binding
        for item in projection.relationships
        if item.predicate == "uses_statblock"
    ]
    assert len(bindings) == 2
    assert {item.revision_id for item in bindings if item is not None} == {"rev_1", "rev_2"}
