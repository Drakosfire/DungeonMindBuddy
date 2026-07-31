"""Synthetic owning-boundary proof for the SBW08 graph contract."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionRequest,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    dump_union_supergraph_store,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    ExternalResourceV1,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
    parse_external_resource_assertion,
    parse_threat_statblock_binding_assertion,
)
from graph_memory.union_supergraph.validate import (
    UnionSupergraphValidationError,
    validate_union_supergraph_store_payload,
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


def _complete_resource_payload() -> dict[str, str]:
    return {
        "schema": "dmb_external_resource_v1",
        "provider": PROVIDER,
        "resource_type": "statblock",
        "resource_id": STATBLOCK_ID,
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
    }


def _complete_binding_payload(
    *,
    revision_id: str = REVISION_ID,
    digest: str = DIGEST,
    role: str = "primary",
    phase_key: str | None = None,
    variant_label: str | None = None,
) -> dict[str, str | None]:
    return _binding(
        revision_id=revision_id,
        digest=digest,
        role=role,
        phase_key=phase_key,
        variant_label=variant_label,
    )


def _publish_statblock_contract(
    root: Path,
) -> tuple[dict[str, object], dict[str, str | None], str, kernel.GraphContribution]:
    threat = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        label="Synthetic Threat",
        campaign_scope=CAMPAIGN_ID,
        value={"kind": "threat", "role": "threat", "source_domains": ["manual_seed"]},
    )
    assert kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(threat)
    ).published

    binding = _complete_binding_payload()
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
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert result.published is True
    assert result.revision_id is not None
    return _complete_resource_payload(), binding, result.revision_id, contribution


def _valid_store_payload(root: Path) -> dict[str, object]:
    _publish_statblock_contract(root)
    _head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    return dump_union_supergraph_store(store)


def _mutate_binding_id_with_matching_edge_id(payload: dict[str, object]) -> None:
    edges = payload["edges"]
    edge_id = next(
        edge_id
        for edge_id, edge in edges.items()
        if edge.get("predicate") == "uses_statblock"
    )
    edge = edges.pop(edge_id)
    binding = edge["threat_statblock_binding"]
    binding["binding_id"] = "threat-statblock-binding:arbitrary"
    replacement_edge_id = edge_id_from_binding_id(str(binding["binding_id"]))
    edge["edge_id"] = replacement_edge_id
    edges[replacement_edge_id] = edge

    for items in payload["adjacency"].values():
        for item in items:
            if item.get("edge_id") == edge_id:
                item["edge_id"] = replacement_edge_id
    for support in payload["assertion_support"].values():
        if support.get("graph_object_id") == edge_id:
            support["graph_object_id"] = replacement_edge_id


def _mutate_external_resource_kind_without_payload(payload: dict[str, object]) -> None:
    node = payload["nodes"][external_statblock_node_id(STATBLOCK_ID)]
    node.pop("external_resource")
    node.update({"kind": "external_resource", "role": "npc"})


def _mutate_external_resource_role_without_payload(payload: dict[str, object]) -> None:
    node = payload["nodes"][external_statblock_node_id(STATBLOCK_ID)]
    node.pop("external_resource")
    node.update({"kind": "npc", "role": "statblock"})


_EXTERNAL_RESOURCE_REQUIRED_FIELDS = (
    "schema",
    "provider",
    "resource_type",
    "contract",
    "contract_version",
)
_BINDING_REQUIRED_FIELDS = (
    "schema",
    "provider",
    "contract",
    "contract_version",
)


@pytest.mark.parametrize("missing_field", _EXTERNAL_RESOURCE_REQUIRED_FIELDS)
def test_external_resource_required_wire_fields_reject_missing(missing_field: str) -> None:
    payload = _complete_resource_payload()
    payload.pop(missing_field)
    with pytest.raises(ValidationError):
        ExternalResourceV1.model_validate(payload)

    value = _resource_value()
    value["external_resource"] = payload
    with pytest.raises(ValidationError):
        parse_external_resource_assertion(
            subject_node_id=external_statblock_node_id(STATBLOCK_ID),
            value=value,
        )


@pytest.mark.parametrize("missing_field", _BINDING_REQUIRED_FIELDS)
def test_binding_required_wire_fields_reject_missing(missing_field: str) -> None:
    payload = _complete_binding_payload()
    payload.pop(missing_field)
    with pytest.raises(ValidationError):
        ThreatStatblockBindingV1.model_validate(payload)

    with pytest.raises(ValidationError):
        parse_threat_statblock_binding_assertion(
            subject_node_id=THREAT_ID,
            target_node_id=external_statblock_node_id(STATBLOCK_ID),
            predicate="uses_statblock",
            value=_binding_value(payload),
        )


def test_kernel_value_predicate_fallback_rejects_malformed_binding(
    seeded_root: Path,
) -> None:
    threat = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        label="Synthetic Threat",
        campaign_scope=CAMPAIGN_ID,
        value={"kind": "threat", "role": "threat", "source_domains": ["manual_seed"]},
    )
    resource = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=external_statblock_node_id(STATBLOCK_ID),
        label="External statblock",
        campaign_scope=CAMPAIGN_ID,
        value=_resource_value(),
    )
    assert kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=_contribution(threat, resource)
    ).published

    missing_binding = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=None,
        target_node_id=None,
        predicate=None,
        campaign_scope=CAMPAIGN_ID,
        value={
            "source_node_id": THREAT_ID,
            "target_node_id": external_statblock_node_id(STATBLOCK_ID),
            "predicate": "uses_statblock",
            "direction": "outbound",
        },
    )
    malformed_binding = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=None,
        target_node_id=None,
        predicate=None,
        campaign_scope=CAMPAIGN_ID,
        value={
            "source_node_id": THREAT_ID,
            "target_node_id": external_statblock_node_id(STATBLOCK_ID),
            "predicate": "uses_statblock",
            "direction": "outbound",
            "threat_statblock_binding": {"binding_id": "threat-statblock-binding:fake"},
        },
    )
    for assertion in (missing_binding, malformed_binding):
        result = kernel.merge_contribution_to_revision(
            seeded_root,
            world_id=WORLD_ID,
            contribution=_contribution(assertion),
        )
        assert result.published is False
        assert any("merge_failed" in item for item in result.diagnostics)
    _head, _revision, store = kernel.open_current_world_graph(seeded_root, WORLD_ID)
    assert all(edge.predicate != "uses_statblock" for edge in store.edges.values())


@pytest.mark.parametrize(
    ("mutator", "pattern"),
    [
        (
            lambda payload: payload["edges"][
                next(
                    edge_id
                    for edge_id, edge in payload["edges"].items()
                    if edge.get("predicate") == "uses_statblock"
                )
            ].pop("threat_statblock_binding"),
            "requires typed threat_statblock_binding",
        ),
        (
            _mutate_binding_id_with_matching_edge_id,
            "binding_id does not match immutable semantic identity",
        ),
        (
            lambda payload: payload["nodes"][THREAT_ID].update({"kind": "npc"}),
            "statblock binding source must be a Threat node",
        ),
        (
            lambda payload: payload["nodes"][
                external_statblock_node_id(STATBLOCK_ID)
            ].pop("external_resource"),
            "external_resource kind/role requires external_resource payload",
        ),
        (
            _mutate_external_resource_kind_without_payload,
            "external_resource kind/role requires external_resource payload",
        ),
        (
            _mutate_external_resource_role_without_payload,
            "external_resource kind/role requires external_resource payload",
        ),
        (
            lambda payload: payload["edges"][
                next(
                    edge_id
                    for edge_id, edge in payload["edges"].items()
                    if edge.get("predicate") == "uses_statblock"
                )
            ].update({"definition": {"rules_elements": []}}),
            "must not contain mechanics fields",
        ),
        (
            lambda payload: payload["nodes"][
                external_statblock_node_id(STATBLOCK_ID)
            ].update({"state": {"mechanics": {"forbidden": True}}}),
            "must not contain mechanics fields",
        ),
    ],
)
def test_persisted_store_rejects_adversarial_mutations(
    seeded_root: Path,
    mutator,
    pattern: str,
) -> None:
    payload = copy.deepcopy(_valid_store_payload(seeded_root))
    mutator(payload)
    with pytest.raises(UnionSupergraphValidationError, match=pattern):
        validate_union_supergraph_store_payload(payload)


def test_binding_fields_match_mechanics_locator_v1() -> None:
    binding = _complete_binding_payload()
    locator = MechanicsLocatorV1(
        provider=PROVIDER,
        statblock_id=STATBLOCK_ID,
        revision_id=REVISION_ID,
        contract=CONTRACT,
        contract_version=CONTRACT_VERSION,
        definition_digest=DIGEST,
    )
    assert locator.model_dump(mode="json") == {
        key: binding[key]
        for key in (
            "provider",
            "statblock_id",
            "revision_id",
            "contract",
            "contract_version",
            "definition_digest",
        )
    }


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
    resource_payload, binding, revision_id, contribution = _publish_statblock_contract(
        seeded_root
    )
    resource_assertion, binding_assertion = contribution.accepted_assertions
    assert resource_assertion.value["external_resource"] == resource_payload
    assert binding_assertion.value["threat_statblock_binding"] == binding

    replay = kernel.merge_contribution_to_revision(
        seeded_root, world_id=WORLD_ID, contribution=contribution
    )
    assert replay.published is False
    assert replay.revision_id == revision_id

    _head, _revision, store = kernel.open_current_world_graph(seeded_root, WORLD_ID)
    resource_node = store.nodes[external_statblock_node_id(STATBLOCK_ID)]
    edge_id = edge_id_from_binding_id(str(binding["binding_id"]))
    stored_edge = store.edges[edge_id]
    assert resource_node.external_resource is not None
    assert stored_edge.threat_statblock_binding is not None
    assert resource_node.external_resource.model_dump(mode="json", by_alias=True) == resource_payload
    assert (
        stored_edge.threat_statblock_binding.model_dump(mode="json", by_alias=True)
        == binding
    )

    projection = kernel.project_world_graph(
        seeded_root, _request(revision_pin=revision_id)
    )
    resource_view = next(
        node
        for node in projection.nodes
        if node.node_id == external_statblock_node_id(STATBLOCK_ID)
    )
    binding_view = next(item for item in projection.relationships if item.edge_id == edge_id)
    assert resource_view.external_resource is not None
    assert binding_view.threat_statblock_binding is not None
    assert resource_view.external_resource.model_dump(mode="json", by_alias=True) == resource_payload
    assert (
        binding_view.threat_statblock_binding.model_dump(mode="json", by_alias=True)
        == binding
    )


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


def test_untyped_node_assertion_cannot_reuse_typed_external_resource_id(
    seeded_root: Path,
) -> None:
    _resource_payload, binding, revision_id, _published_contribution = _publish_statblock_contract(
        seeded_root
    )
    resource_node_id = external_statblock_node_id(STATBLOCK_ID)

    generic_resource = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=resource_node_id,
        label="Hijack attempt",
        campaign_scope=CAMPAIGN_ID,
        value={"kind": "npc", "role": "npc", "source_domains": ["manual_seed"]},
    )
    adversarial = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:sbw08",
        source_revision_id="sbw08-adversarial-untyped-node",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=[generic_resource],
    )
    result = kernel.merge_contribution_to_revision(
        seeded_root,
        world_id=WORLD_ID,
        contribution=adversarial,
    )
    assert result.published is False
    assert result.revision_id is None
    assert any("merge_failed" in item for item in result.diagnostics)

    head, _revision, store = kernel.open_current_world_graph(seeded_root, WORLD_ID)
    assert head.head_revision_id == revision_id
    resource_node = store.nodes[resource_node_id]
    assert resource_node.external_resource is not None

    projection = kernel.project_world_graph(
        seeded_root, _request(revision_pin=revision_id)
    )
    resource_view = next(
        node for node in projection.nodes if node.node_id == resource_node_id
    )
    assert resource_view.external_resource is not None
    assert (
        resource_view.external_resource.model_dump(mode="json", by_alias=True)
        == _resource_payload
    )
    edge_id = edge_id_from_binding_id(str(binding["binding_id"]))
    binding_view = next(item for item in projection.relationships if item.edge_id == edge_id)
    assert binding_view.threat_statblock_binding is not None


def test_untyped_edge_assertion_cannot_reuse_typed_statblock_binding_id(
    seeded_root: Path,
) -> None:
    _resource_payload, binding, revision_id, _published_contribution = _publish_statblock_contract(
        seeded_root
    )
    edge_id = edge_id_from_binding_id(str(binding["binding_id"]))
    resource_node_id = external_statblock_node_id(STATBLOCK_ID)

    generic_edge = kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=THREAT_ID,
        target_node_id=resource_node_id,
        predicate="related_to",
        campaign_scope=CAMPAIGN_ID,
        value={
            "edge_id": edge_id,
            "source_node_id": THREAT_ID,
            "target_node_id": resource_node_id,
            "predicate": "related_to",
            "direction": "outbound",
        },
    )
    adversarial = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:sbw08",
        source_revision_id="sbw08-adversarial-untyped-edge",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=[generic_edge],
    )
    result = kernel.merge_contribution_to_revision(
        seeded_root,
        world_id=WORLD_ID,
        contribution=adversarial,
    )
    assert result.published is False
    assert result.revision_id is None
    assert any("merge_failed" in item for item in result.diagnostics)

    head, _revision, store = kernel.open_current_world_graph(seeded_root, WORLD_ID)
    assert head.head_revision_id == revision_id
    stored_edge = store.edges[edge_id]
    assert stored_edge.threat_statblock_binding is not None
    assert stored_edge.predicate == "uses_statblock"

    projection = kernel.project_world_graph(
        seeded_root, _request(revision_pin=revision_id)
    )
    binding_view = next(item for item in projection.relationships if item.edge_id == edge_id)
    assert binding_view.predicate == "uses_statblock"
    assert binding_view.threat_statblock_binding is not None
    assert (
        binding_view.threat_statblock_binding.model_dump(mode="json", by_alias=True)
        == binding
    )
