"""Fail-closed proofs for dual-sense relationship decomposition v1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from dataclasses import replace

from apps.live_control_server.integrations.dungeonmind_kernel import (
    relationship_dual_sense_decomposition_v1 as decomp,
)
from apps.live_control_server.config import repo_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
    DecompositionRevisionBinding,
    DualSenseDecompositionPackageV1,
    EndpointAssignmentV1,
    RelationshipDualSenseDecompositionError,
    VerifiedPredecessorAuthority,
    decomposition_binding_from_attested_revision,
    evaluate_global_aspect_substitution_v1,
    evaluate_package_projection_v1,
    predecessor_authority_from_locked_bytes,
    predecessor_authority_from_sealed_repair,
    prove_relationship_dual_sense_decomposition_v1,
    store_semantic_sha256,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
)


COLLEGE = "loc:wizard_college"
NETWORK = "node:meat_distribution_network_session9"
REVELRY = "node:hempholm_folk_revelry"
LEADS = "edge:node:headmaster_tinkerbright:leads:loc:wizard_college"
TRAVELS_A = "edge:node:thalia:travels_to:loc:wizard_college"
TRAVELS_B = "edge:node:torbin:travels_to:loc:wizard_college"
LOCATED = (
    "edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of"
)
PART_OF = "edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9"
BLART = "edge:node:captain_blart:leads:node:meat_distribution_network_session9:coordinates"
LYRA = "edge:node:lyra:leads:node:meat_distribution_network_session9"
TOWNSFOLK = "edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry"
CAELYNN = "edge:pc:caelynn:participates_in:node:hempholm_folk_revelry"
WITHIN = "edge:node:hempholm_folk_revelry:within:loc:hempholm"
DEFERRED = (LOCATED, PART_OF, LEADS, TOWNSFOLK, CAELYNN)


def _node(node_id: str, kind: str) -> SimpleNamespace:
    return SimpleNamespace(node_id=node_id, kind=kind, label=node_id)


def _edge(edge_id: str, source: str, target: str, predicate: str) -> SimpleNamespace:
    return SimpleNamespace(
        edge_id=edge_id,
        source_node_id=source,
        target_node_id=target,
        predicate=predicate,
        label=predicate,
        direction="outbound",
    )


def _store() -> SimpleNamespace:
    nodes = {
        COLLEGE: _node(COLLEGE, "location"),
        "node:headmaster_tinkerbright": _node("node:headmaster_tinkerbright", "npc"),
        "node:thalia": _node("node:thalia", "npc"),
        "node:torbin": _node("node:torbin", "npc"),
        NETWORK: _node(NETWORK, "party"),
        "loc:central-office": _node("loc:central-office", "location"),
        "loc:packing-loading-area": _node("loc:packing-loading-area", "location"),
        "node:captain_blart": _node("node:captain_blart", "npc"),
        "node:lyra": _node("node:lyra", "npc"),
        REVELRY: _node(REVELRY, "group"),
        "node:hempholm_townsfolk": _node("node:hempholm_townsfolk", "npc"),
        "pc:caelynn": _node("pc:caelynn", "pc"),
        "loc:hempholm": _node("loc:hempholm", "location"),
    }
    edges = {
        LEADS: _edge(LEADS, "node:headmaster_tinkerbright", COLLEGE, "leads"),
        TRAVELS_A: _edge(TRAVELS_A, "node:thalia", COLLEGE, "travels_to"),
        TRAVELS_B: _edge(TRAVELS_B, "node:torbin", COLLEGE, "travels_to"),
        LOCATED: _edge(LOCATED, "loc:central-office", NETWORK, "located_in"),
        PART_OF: _edge(PART_OF, "loc:packing-loading-area", NETWORK, "part_of"),
        BLART: _edge(BLART, "node:captain_blart", NETWORK, "leads"),
        LYRA: _edge(LYRA, "node:lyra", NETWORK, "leads"),
        TOWNSFOLK: _edge(TOWNSFOLK, "node:hempholm_townsfolk", REVELRY, "participates_in"),
        CAELYNN: _edge(CAELYNN, "pc:caelynn", REVELRY, "participates_in"),
        WITHIN: _edge(WITHIN, REVELRY, "loc:hempholm", "within"),
    }
    return SimpleNamespace(nodes=nodes, edges=edges)


def _predecessor_payload() -> dict[str, object]:
    return {
        "schema": "dmb_eldyrwild_relationship_node_kind_source_repair_v1",
        "repair_id": "eldyrwild-relationship-node-kind-source-repair-v1",
        "world_id": "eldyrwild",
        "expected_remaining_residual_edge_ids": sorted(DEFERRED),
        "deferred_dual_sense_stops": [
            {
                "node_id": COLLEGE,
                "current_kind": "location",
                "deferred_edge_ids": [LEADS],
                "retained_effective_edge_ids": [TRAVELS_A, TRAVELS_B],
                "stop_basis": {
                    "candidate_kind": "faction",
                    "kind_only_insufficient": True,
                    "note": "faction admits leads but breaks travels_to",
                    "source_rationales": {LEADS: "organizational leadership"},
                },
            },
            {
                "node_id": REVELRY,
                "current_kind": "group",
                "deferred_edge_ids": [TOWNSFOLK, CAELYNN],
                "retained_effective_edge_ids": [WITHIN],
                "stop_basis": {
                    "candidate_kind": "event",
                    "kind_only_insufficient": True,
                    "note": "event admits participates_in but breaks within",
                    "source_rationales": {
                        TOWNSFOLK: "townsfolk join revelry",
                        CAELYNN: "Caelynn joins revelry",
                    },
                },
            },
            {
                "node_id": NETWORK,
                "current_kind": "party",
                "deferred_edge_ids": [LOCATED, PART_OF],
                "retained_effective_edge_ids": [BLART, LYRA],
                "stop_basis": {
                    "candidate_kind": "location",
                    "kind_only_insufficient": True,
                    "note": "location admits containment but breaks leads",
                    "source_rationales": {
                        LOCATED: "office is a site of the network",
                        PART_OF: "packing area belongs to the network site",
                    },
                },
            },
        ],
    }


def _predecessor_bytes() -> bytes:
    return (json.dumps(_predecessor_payload(), sort_keys=True) + "\n").encode("utf-8")


def _predecessor():
    return predecessor_authority_from_sealed_repair(repo=repo_root())


def _project(store: SimpleNamespace, package: DualSenseDecompositionPackageV1, **kwargs):
    return evaluate_package_projection_v1(
        store,
        package=package,
        binding=kwargs.pop("binding", None) or _binding(store),
        current_residual_edge_ids=kwargs.pop("current_residual_edge_ids", set(DEFERRED)),
        target=kwargs.pop("target", CURRENT_V5_TARGET),
        **kwargs,
    )


def _binding(store: SimpleNamespace):
    """In-memory reconstruction helper. This is not revision attestation."""
    return DecompositionRevisionBinding(
        world_id="eldyrwild",
        canonical_revision_id="rev:test",
        canonical_graph_payload_sha256="0" * 64,
        store_semantic_sha256=store_semantic_sha256(store),
        _token=decomp._BINDING_TOKEN,
    )


def _prove(store: SimpleNamespace | None = None, **kwargs):
    store = store or _store()
    return prove_relationship_dual_sense_decomposition_v1(
        store,
        binding=kwargs.pop("binding", None) or _binding(store),
        predecessor=kwargs.pop("predecessor", None) or _predecessor(),
        current_residual_edge_ids=kwargs.pop("current_residual_edge_ids", set(DEFERRED)),
        target=kwargs.pop("target", CURRENT_V5_TARGET),
        **kwargs,
    )


def test_public_binding_constructor_rejects_arbitrary_pins() -> None:
    with pytest.raises(TypeError):
        DecompositionRevisionBinding(
            world_id="world-B",
            canonical_revision_id="rev:B",
            canonical_graph_payload_sha256="b" * 64,
            store_semantic_sha256="c" * 64,
            _token=object(),
        )


def test_public_predecessor_constructor_rejects_caller_stop_rows() -> None:
    with pytest.raises(TypeError):
        VerifiedPredecessorAuthority(
            manifest_sha256="a" * 64,
            schema="x",
            repair_id="y",
            world_id="eldyrwild",
            remaining_residual_edge_ids=DEFERRED,
            stops=(),
            _token=object(),
        )


def test_fake_manifest_plus_own_digest_is_refused() -> None:
    raw = _predecessor_bytes()
    digest = decomp.sha256_bytes(raw)
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        predecessor_authority_from_locked_bytes(raw, expected_sha256=digest)
    assert exc.value.code == "predecessor_authority_unattested"


def test_tampered_sealed_predecessor_is_refused(tmp_path: Path) -> None:
    from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
        MANIFEST_RELPATH,
    )

    source = repo_root() / MANIFEST_RELPATH
    tampered_path = tmp_path / MANIFEST_RELPATH
    tampered_path.parent.mkdir(parents=True, exist_ok=True)
    tampered_path.write_bytes(source.read_bytes().replace(b"faction", b"factoin", 1))
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        predecessor_authority_from_sealed_repair(repo=tmp_path)
    assert exc.value.code == "predecessor_manifest_tampered"


def test_derived_package_covers_exact_three_identities_and_five_edges() -> None:
    proof = _prove()
    package = proof.package
    assert proof.passed is True
    assert [row.source_node_id for row in package.decomposition_rows] == [
        COLLEGE,
        REVELRY,
        NETWORK,
    ]
    assert [row.edge_id for row in package.endpoint_assignments] == sorted(DEFERRED)
    by_source = {row.source_node_id: row for row in package.decomposition_rows}
    assert by_source[COLLEGE].aspect_key == "organization"
    assert by_source[COLLEGE].projected_dm_kind == "dnd5e:faction"
    assert by_source[COLLEGE].stored_buddy_kind == "location"
    assert by_source[NETWORK].aspect_key == "site"
    assert by_source[NETWORK].projected_dm_kind == "dnd5e:location"
    assert by_source[REVELRY].aspect_key == "event"
    assert by_source[REVELRY].projected_dm_kind == "dnd5e:event"
    assert package.package_projection.passed is True
    assert package.package_projection.retained_regressions == []
    assert all(
        assignment.assigned_endpoint == "target"
        for assignment in package.endpoint_assignments
    )
    assert "node:aspect:" not in json.dumps(package.model_dump(mode="json"))


def test_omit_one_assignment_is_refused() -> None:
    package = _prove().package
    reduced = package.model_copy(
        update={"endpoint_assignments": package.endpoint_assignments[1:]}
    )
    projection = _project(_store(), reduced)
    assert projection.passed is False
    assert projection.uncovered_current_residual_edge_ids == [package.endpoint_assignments[0].edge_id]


def test_sixth_assignment_is_refused() -> None:
    store = _store()
    visitor = "edge:node:visitor:travels_to:loc:wizard_college"
    store.nodes["node:visitor"] = _node("node:visitor", "npc")
    store.edges[visitor] = _edge(visitor, "node:visitor", COLLEGE, "travels_to")
    package = _prove(store).package
    from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
        AspectRefV1,
    )

    college_row = next(
        row for row in package.decomposition_rows if row.source_node_id == COLLEGE
    )
    extra = EndpointAssignmentV1(
        edge_id=visitor,
        buddy_predicate="travels_to",
        source_node_id="node:visitor",
        target_node_id=COLLEGE,
        assigned_endpoint="target",
        aspect_ref=AspectRefV1(
            source_node_id=college_row.source_node_id,
            aspect_key=college_row.aspect_key,
            projected_dm_kind=college_row.projected_dm_kind,
        ),
        predecessor_stop_authority_ref="x",
        predecessor_repair_manifest_sha256="a" * 64,
        rationale="extra",
    )
    inflated = package.model_copy(
        update={"endpoint_assignments": [*package.endpoint_assignments, extra]}
    )
    projection = _project(store, inflated)
    assert projection.passed is False
    assert projection.extra_package_edge_assignments == [visitor]


def test_current_residual_sixth_id_is_refused_at_prove() -> None:
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        _prove(current_residual_edge_ids=set(DEFERRED) | {TRAVELS_A})
    assert exc.value.code == "current_residual_set_mismatch"


def test_wrong_projected_kind_fails_projection() -> None:
    store = _store()
    package = _prove(store).package
    assignment = package.endpoint_assignments[0]
    broken_aspect = assignment.aspect_ref.model_copy(update={"projected_dm_kind": "dnd5e:item"})
    broken_assignment = assignment.model_copy(update={"aspect_ref": broken_aspect})
    mutated = package.model_copy(
        update={
            "endpoint_assignments": [broken_assignment, *package.endpoint_assignments[1:]]
        }
    )
    projection = _project(store, mutated)
    assert projection.passed is False
    assert assignment.edge_id in [
        row.edge_id for row in projection.assigned_admissions if not row.admitted
    ]


def test_global_aspect_substitution_regresses_retained_senses() -> None:
    store = _store()
    package = _prove(store).package
    college = evaluate_global_aspect_substitution_v1(
        store, package=package, source_node_id=COLLEGE, target=CURRENT_V5_TARGET
    )
    network = evaluate_global_aspect_substitution_v1(
        store, package=package, source_node_id=NETWORK, target=CURRENT_V5_TARGET
    )
    revelry = evaluate_global_aspect_substitution_v1(
        store, package=package, source_node_id=REVELRY, target=CURRENT_V5_TARGET
    )
    assert college == sorted([TRAVELS_A, TRAVELS_B])
    assert network == sorted([BLART, LYRA])
    assert revelry == [WITHIN]
    assert package.package_projection.retained_regressions == []


def test_wrong_target_pin_is_refused_at_projection() -> None:
    store = _store()
    package = _prove(store).package
    fake_target = replace(CURRENT_V5_TARGET, dungeonmind_dependency_ref="ab" * 20)
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        _project(store, package, target=fake_target)
    assert exc.value.code == "decomposition_target_mismatch"


def test_wrong_vocabulary_revision_label_is_refused_at_projection() -> None:
    store = _store()
    package = _prove(store).package
    fake_target = replace(CURRENT_V5_TARGET, world_object_revision_label="world-object-v4")
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        _project(store, package, target=fake_target)
    assert exc.value.code == "decomposition_target_mismatch"


def test_package_from_store_a_projected_against_store_b_is_refused() -> None:
    store_a = _store()
    package_a = _prove(store_a).package
    store_b = copy.deepcopy(store_a)
    store_b.nodes[COLLEGE] = _node(COLLEGE, "location")
    store_b.nodes[COLLEGE].label = "other"
    binding_b = _binding(store_b)
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        evaluate_package_projection_v1(
            store_b,
            package=package_a,
            binding=binding_b,
            current_residual_edge_ids=set(DEFERRED),
            target=CURRENT_V5_TARGET,
        )
    assert exc.value.code == "decomposition_binding_pin_mismatch"
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        evaluate_package_projection_v1(
            store_b,
            package=package_a,
            binding=_binding(store_a),
            current_residual_edge_ids=set(DEFERRED),
            target=CURRENT_V5_TARGET,
        )
    assert exc.value.code == "decomposition_store_revision_mismatch"


def test_wrong_world_binding_is_refused() -> None:
    store = _store()
    binding = DecompositionRevisionBinding(
        world_id="world-B",
        canonical_revision_id="rev:test",
        canonical_graph_payload_sha256="0" * 64,
        store_semantic_sha256=store_semantic_sha256(store),
        _token=decomp._BINDING_TOKEN,
    )
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        _prove(store, binding=binding)
    assert exc.value.code == "decomposition_world_mismatch"


def test_prove_store_a_with_store_b_binding_is_refused() -> None:
    store_a = _store()
    store_b = copy.deepcopy(store_a)
    store_b.nodes[COLLEGE] = _node(COLLEGE, "location")
    store_b.nodes[COLLEGE].label = "other"
    binding_b = _binding(store_b)
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        _prove(store_a, binding=binding_b)
    assert exc.value.code == "decomposition_store_revision_mismatch"


def test_manifest_b_plus_store_a_expected_b_is_refused_at_binding_creation(
    tmp_path: Path,
) -> None:
    from graph_memory.union_supergraph.load import (
        DEFAULT_FIXTURE_PATH,
        load_union_supergraph_store,
        parse_union_supergraph_store,
    )
    from graph_memory.world_supergraph import publish_world_graph_revision
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
        _load_exact_buddy_revision,
    )

    store_a = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    published_a = publish_world_graph_revision(
        tmp_path, "world-a", store_a, operation_ids=["op:a"]
    )
    payload = copy.deepcopy(store_a.model_dump(mode="json", by_alias=True))
    first_node_id = next(iter(payload["nodes"]))
    payload["nodes"][first_node_id]["label"] = (
        str(payload["nodes"][first_node_id]["label"]) + " B"
    )
    store_b = parse_union_supergraph_store(payload)
    published_b = publish_world_graph_revision(
        tmp_path, "world-b", store_b, operation_ids=["op:b"]
    )
    _manifest_a, loaded_a = _load_exact_buddy_revision(
        root=tmp_path,
        world_id="world-a",
        revision_id=published_a.revision.revision_id,
    )
    manifest_b, loaded_b = _load_exact_buddy_revision(
        root=tmp_path,
        world_id="world-b",
        revision_id=published_b.revision.revision_id,
    )
    with pytest.raises(TypeError):
        decomposition_binding_from_attested_revision(
            manifest=manifest_b,
            store=loaded_a,
            expected_world_id=manifest_b.world_id,
            expected_revision_id=manifest_b.revision_id,
            expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
        )
    with pytest.raises(RelationshipDualSenseDecompositionError) as exc:
        decomposition_binding_from_attested_revision(
            root=tmp_path,
            world_id=manifest_b.world_id,
            revision_id=manifest_b.revision_id,
            expected_world_id=manifest_b.world_id,
            expected_revision_id=manifest_b.revision_id,
            expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
            store=loaded_a,
        )
    assert exc.value.code == "decomposition_store_revision_mismatch"
    binding_b = decomposition_binding_from_attested_revision(
        root=tmp_path,
        world_id=manifest_b.world_id,
        revision_id=manifest_b.revision_id,
        expected_world_id=manifest_b.world_id,
        expected_revision_id=manifest_b.revision_id,
        expected_graph_payload_sha256=manifest_b.graph_payload_sha256,
        store=loaded_b,
    )
    assert binding_b.canonical_revision_id == manifest_b.revision_id
    assert binding_b.store_semantic_sha256 == store_semantic_sha256(loaded_b)


def test_package_bytes_are_deterministic() -> None:
    first = decomp.package_canonical_bytes(_prove().package)
    second = decomp.package_canonical_bytes(_prove().package)
    assert first == second
    sealed = DualSenseDecompositionPackageV1.model_validate(json.loads(first))
    assert sealed.canonical_payload_sha256
    assert sealed.canonical_payload_sha256 != "0" * 64
