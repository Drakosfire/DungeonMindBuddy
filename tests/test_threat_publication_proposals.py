"""SBW09c1: Threat publication proposal service tests."""
from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import apps.live_control_server.services.threat_publication_identity as identity_svc
import apps.live_control_server.services.threat_publication_operations as pub_svc
import apps.live_control_server.services.threat_publication_proposals as proposal_svc
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    PROVIDER_DUNGEONMIND,
    MechanicsLocatorV1,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptedMechanicsRefV1
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.models.threat_publication import (
    BeginThreatPublicationOperationRequestV1,
    CancelThreatPublicationOperationRequestV1,
)
from apps.live_control_server.models.threat_publication_identity import MATCHING_PROFILE_V1
from apps.live_control_server.models.threat_publication_proposal import PrepareThreatPublicationProposalRequestV1
from apps.live_control_server.services.threat_draft_store import (
    _draft_path,
    attach_accepted_mechanics_ref,
    create_threat_draft,
    update_threat_draft,
)
from apps.live_control_server.services.threat_publication_operations import (
    begin_publication_operation,
    cancel_publication_operation,
)
import graph_memory.kernel as kernel
from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package
from graph_memory.extract_promote_proposal import contribution_slices_from_effect
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH, load_union_supergraph_store
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    ExternalResourceV1,
    ThreatStatblockBindingV1,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)
from graph_memory.world_supergraph import publish_world_graph_revision

WORLD_ID = "world_1"

DEFAULT_DIGEST = "sha256:" + "a" * 64


class _FakeHead:
    def __init__(self, revision_id: str) -> None:
        self.head_revision_id = revision_id


def _empty_parent_store():
    base = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    return base.model_copy(
        update={
            "nodes": {},
            "edges": {},
            "aliases": {},
            "adjacency": {},
            "evidence": {},
            "source_artifacts": {},
        }
    )


def _threat_store_node(node_id: str = "threat:1", *, label: str = "Existing Threat"):
    template = next(iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values()))
    return template.model_copy(
        update={
            "node_id": node_id,
            "label": label,
            "kind": "Threat",
            "role": "antagonist",
            "aliases": [],
            "source_domains": ["worldbuilding"],
            "evidence_ref_ids": [],
        }
    )


def _seed_graph_parent(tmp_path: Path, *, nodes: dict | None = None) -> str:
    world_root = tmp_path / "graph"
    store = _empty_parent_store()
    if nodes:
        store = store.model_copy(update={"nodes": nodes})
    published = publish_world_graph_revision(
        world_root,
        "world_1",
        store,
        operation_ids=["op:proposal-test"],
    )
    return published.revision.revision_id


def _mock_head(monkeypatch, revision_id: str) -> None:
    monkeypatch.setattr(
        pub_svc.kernel, "open_world_graph_head", lambda root, world_id: _FakeHead(revision_id)
    )


def _locator(**overrides: Any) -> MechanicsLocatorV1:
    payload: dict[str, Any] = {
        "provider": PROVIDER_DUNGEONMIND,
        "statblock_id": "sb_1",
        "revision_id": "rev_1",
        "contract": "dungeonmind.dungeonbuddy-statblocks",
        "contract_version": "1.0.0",
        "definition_digest": DEFAULT_DIGEST,
    }
    payload.update(overrides)
    return MechanicsLocatorV1.model_validate(payload)


def _create_draft(tmp_path: Path, **overrides: Any):
    payload: dict[str, Any] = {
        "world_id": "world_1",
        "campaign_id": "campaign_1",
        "name": "Ironhide Brute",
        "description": "A brutal enforcer.",
        "threat_kind": "creature",
        "generation_intent": GenerationIntentV1(
            ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            target_cr="3",
        ),
        "graph_context_snapshot": GraphContextSnapshotV1(graph_revision_id="rev:aaa"),
        "created_by": "gm",
    }
    payload.update(overrides)
    return create_threat_draft(tmp_path, CreateThreatDraftRequest.model_validate(payload))


def _mechanics_saved_draft(
    tmp_path: Path, monkeypatch, *, name: str = "Ironhide Brute", graph_nodes: dict | None = None
):
    draft = _create_draft(tmp_path, name=name)
    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(), accepted_from_draft_version=draft.version, accepted_at="2020-01-01T00:00:00Z"
    )
    draft = attach_accepted_mechanics_ref(
        tmp_path, draft_id=draft.draft_id, expected_version=draft.version, locator=ref
    )
    parent = _seed_graph_parent(tmp_path, nodes=graph_nodes)
    _mock_head(monkeypatch, parent)
    return draft, parent


def _begin_operation(tmp_path: Path, draft, parent: str, *, operation_id: str | None = None):
    op_id = operation_id or str(uuid.uuid4())
    request = BeginThreatPublicationOperationRequestV1.model_validate(
        {
            "operation_id": op_id,
            "expected_draft_version": draft.version,
            "expected_parent_revision_id": parent,
            "actor": "gm",
        }
    )
    outcome = begin_publication_operation(tmp_path, draft.draft_id, request)
    assert outcome.response.result_label == "publication_ready"
    return op_id, outcome.response.operation


def _node(
    node_id: str,
    *,
    label: str,
    kind: str = "Threat",
    aliases: list[str] | None = None,
    role: str = "antagonist",
) -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label=label,
        kind=kind,
        role=role,
        aliases=aliases or [],
        source_domains=["worldbuilding"],
    )


def _projection_for(*nodes: WorldGraphProjectionNodeView, revision_id: str):
    return identity_svc.build_projection_fixture(revision_id=revision_id, nodes=list(nodes))


def _prepare(tmp_path: Path, draft_id: str, operation_id: str, **overrides: Any):
    body = identity_svc.PrepareThreatIdentityCandidatesRequestV1.model_validate(overrides or {})
    return identity_svc.prepare_identity_candidates(tmp_path, draft_id, operation_id, body)


def _decide(tmp_path: Path, draft_id: str, operation_id: str, **overrides: Any):
    overrides.setdefault("rejected_candidate_node_ids", [])
    body = identity_svc.CreateThreatIdentityResolutionRequestV1.model_validate(overrides)
    with patch.object(
        identity_svc,
        "_exact_revision_contains_node_id",
        side_effect=lambda _operation, node_id, *, world_root: False,
    ):
        return identity_svc.decide_identity_resolution(tmp_path, draft_id, operation_id, body)


def _reject_all_collisions(candidate_set) -> list[str]:
    return [c.node_id for c in candidate_set.candidates if c.exact_name_collision]


def _create_new_resolution(tmp_path: Path, draft, op_id: str, parent: str, *, resolution_id: str | None = None):
    projection = _projection_for(_node("threat:visible", label="Visible"), revision_id=parent)
    rid = resolution_id or str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Visible")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=rid,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="new",
        )
    assert outcome.response.result_label == "publication_identity_created_new"
    return rid, outcome.response.resolution


def _connect_resolution(
    tmp_path: Path,
    draft,
    op_id: str,
    parent: str,
    target_id: str = "threat:1",
    *,
    resolution_id: str | None = None,
):
    projection = _projection_for(_node(target_id, label="Existing Threat"), revision_id=parent)
    rid = resolution_id or str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Existing")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=rid,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="connect_existing",
            target_node_id=target_id,
            rejected_candidate_node_ids=[],
            actor="gm",
            reason="connect",
        )
    assert outcome.response.result_label == "publication_identity_connected_existing"
    return rid, outcome.response.resolution


def _refuse_resolution(tmp_path: Path, draft, op_id: str, parent: str, *, resolution_id: str | None = None):
    projection = _projection_for(_node("threat:1", label="One"), revision_id=parent)
    rid = resolution_id or str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="One")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=rid,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="refuse",
            rejected_candidate_node_ids=[],
            actor="gm",
            reason="no",
        )
    assert outcome.response.result_label == "publication_identity_refused"
    return rid


def _prepare_request(proposal_id: str | None = None, **overrides: Any):
    payload: dict[str, Any] = {
        "proposal_id": proposal_id or str(uuid.uuid4()),
        "actor": "gm",
    }
    payload.update(overrides)
    return PrepareThreatPublicationProposalRequestV1.model_validate(payload)


def _proposal_ledger_bytes(tmp_path: Path, draft_id: str, operation_id: str) -> bytes:
    path = proposal_svc._ledger_path(tmp_path, draft_id, operation_id)
    return path.read_bytes()


def _proposal_operation_directory(tmp_path: Path, draft_id: str, operation_id: str) -> Path:
    return proposal_svc._operation_directory(tmp_path, draft_id, operation_id)


def _assert_no_proposal_storage(tmp_path: Path, draft_id: str, operation_id: str) -> None:
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft_id, operation_id) is None
    operation_dir = _proposal_operation_directory(tmp_path, draft_id, operation_id)
    assert not operation_dir.exists()


def _world_tree_file_snapshot(world_root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(world_root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in world_root.rglob("*")
        if path.is_file()
    }


def _incompatible_external_resource_store_node(statblock_id: str = "sb_1"):
    template = next(iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values()))
    wrong_resource = ExternalResourceV1.model_validate(
        {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": "sb_w09",
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        }
    )
    return template.model_copy(
        update={
            "node_id": external_statblock_node_id(statblock_id),
            "label": "Foreign statblock resource",
            "kind": "external_resource",
            "role": "statblock",
            "aliases": [],
            "source_domains": ["worldbuilding"],
            "evidence_ref_ids": [],
            "external_resource": wrong_resource,
        }
    )


def _correct_payload_wrong_envelope_resource_node(statblock_id: str = "sb_1"):
    template = next(iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values()))
    resource = ExternalResourceV1.model_validate(
        {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": statblock_id,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        }
    )
    return template.model_copy(
        update={
            "node_id": external_statblock_node_id(statblock_id),
            "label": "Wrong envelope label",
            "kind": "npc",
            "role": "npc",
            "aliases": [],
            "source_domains": ["worldbuilding"],
            "evidence_ref_ids": [],
            "external_resource": resource,
        }
    )


def _correct_payload_wrong_label_aliases_resource_node(statblock_id: str = "sb_1"):
    template = next(iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values()))
    resource = ExternalResourceV1.model_validate(
        {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": statblock_id,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        }
    )
    return template.model_copy(
        update={
            "node_id": external_statblock_node_id(statblock_id),
            "label": "Mismatched label only",
            "kind": "external_resource",
            "role": "statblock",
            "aliases": ["Other alias"],
            "source_domains": ["manual_seed"],
            "evidence_ref_ids": [],
            "external_resource": resource,
        }
    )


def _incompatible_binding_edge(
    *,
    threat_node_id: str,
    resource_node_id: str,
    use_deterministic_edge_id: bool,
    accepted_statblock_id: str = "sb_1",
):
    template = next(iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).edges.values()))
    binding = ThreatStatblockBindingV1.model_validate(
        {
            "schema": "dmb_threat_statblock_binding_v1",
            "binding_id": compute_binding_id(
                threat_node_id=threat_node_id,
                provider=PROVIDER,
                statblock_id="sb_w09",
                revision_id="rev_1",
                contract=CONTRACT,
                contract_version=CONTRACT_VERSION,
                definition_digest=DEFAULT_DIGEST,
                role="primary",
                phase_key=None,
                variant_label=None,
            ),
            "provider": PROVIDER,
            "statblock_id": "sb_w09",
            "revision_id": "rev_1",
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
            "definition_digest": DEFAULT_DIGEST,
            "role": "primary",
            "phase_key": None,
            "variant_label": None,
        }
    )
    edge_id = (
        edge_id_from_binding_id(binding.binding_id)
        if use_deterministic_edge_id
        else "edge:incompatible-binding-collision"
    )
    return template.model_copy(
        update={
            "edge_id": edge_id,
            "source_node_id": threat_node_id,
            "target_node_id": resource_node_id,
            "predicate": "uses_statblock",
            "label": "uses statblock",
            "direction": "outbound",
            "source_domains": ["worldbuilding"],
            "session_ids": [],
            "evidence_ref_ids": [],
            "threat_statblock_binding": binding,
        }
    )


def _supersede_resolution(
    tmp_path: Path,
    draft,
    op_id: str,
    parent: str,
    *,
    first_resolution_id: str,
    second_resolution_id: str | None = None,
):
    projection = _projection_for(_node("threat:visible", label="Visible"), revision_id=parent)
    second_id = second_resolution_id or str(uuid.uuid4())
    with patch.object(identity_svc, "project_world_graph", return_value=projection):
        prepared = _prepare(tmp_path, draft.draft_id, op_id, query_text="Visible")
        cs = prepared.response.candidate_set
        assert cs is not None
        outcome = _decide(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id=second_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=cs.candidate_query,
            candidate_set_digest=cs.candidate_set_digest,
            decision="create_new",
            rejected_candidate_node_ids=_reject_all_collisions(cs),
            actor="gm",
            reason="supersede",
            supersedes_resolution_id=first_resolution_id,
        )
    assert outcome.response.result_label == "publication_identity_superseded"
    return second_id


def test_create_new_prepare_seals_and_reloads_exactly(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    request = _prepare_request(proposal_id)

    created = proposal_svc.prepare_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, resolution_id, request, world_root=tmp_path / "graph"
    )
    assert created.created is True
    assert created.response.result_label == "publication_proposal_ready"
    proposal = created.response.proposal
    assert proposal is not None
    assert proposal.proposal_id == proposal_id
    assert proposal.sealed_proposal_id == proposal_id
    assert proposal.decision == "create_new"
    assert proposal.effect_summary.authored_field_assertion_count >= 1

    reloaded = proposal_svc.read_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, proposal_id
    )
    assert reloaded.response.proposal == proposal


def test_connect_existing_contains_resource_and_binding_only(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(
        tmp_path, monkeypatch, name="Unique Threat", graph_nodes={"threat:1": _threat_store_node()}
    )
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _connect_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=tmp_path / "graph",
    )
    assert outcome.response.result_label == "publication_proposal_ready"
    proposal = outcome.response.proposal
    assert proposal is not None
    accepted = contribution_slices_from_effect(proposal.sealed_proposal["effect"])[0][
        "accepted_proposals"
    ]
    node_assertions = [item for item in accepted if item["assertion_kind"] == "node"]
    assert len(node_assertions) == 1
    assert node_assertions[0]["subject_node_id"].startswith("external:dungeonmind:statblock:")
    assert proposal.effect_summary.authored_field_assertion_count == 0


def test_refuse_resolution_creates_no_proposal(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id = _refuse_resolution(tmp_path, draft, op_id, parent)
    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )
    assert outcome.response.result_label == "publication_proposal_identity_refused"
    assert outcome.response.resolution_id == resolution_id
    _assert_no_proposal_storage(tmp_path, draft.draft_id, op_id)


def test_stale_operation_rejects_without_proposal(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    draft = update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description="changed",
            threat_kind=draft.threat_kind,
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
        ),
    )
    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )
    assert outcome.response.result_label == "publication_proposal_operation_not_ready"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_exact_replay_returns_existing_before_dependency_reads(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    request = _prepare_request(proposal_id)

    first = proposal_svc.prepare_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, resolution_id, request, world_root=tmp_path / "graph"
    )
    assert first.created is True

    with patch.object(proposal_svc, "read_identity_resolution") as read_resolution:
        replay = proposal_svc.prepare_threat_publication_proposal(
            tmp_path, draft.draft_id, op_id, resolution_id, request, world_root=tmp_path / "graph"
        )
    read_resolution.assert_not_called()
    assert replay.created is False
    assert replay.response.proposal == first.response.proposal


def test_changed_request_same_proposal_id_conflicts_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    request = _prepare_request(proposal_id)

    proposal_svc.prepare_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, resolution_id, request, world_root=tmp_path / "graph"
    )
    before = _proposal_ledger_bytes(tmp_path, draft.draft_id, op_id)

    changed = _prepare_request(proposal_id, operator_note="different")
    conflict = proposal_svc.prepare_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, resolution_id, changed, world_root=tmp_path / "graph"
    )
    assert conflict.response.result_label == "publication_proposal_input_conflict"
    assert _proposal_ledger_bytes(tmp_path, draft.draft_id, op_id) == before


def test_competing_first_proposals_leave_one_active(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    barrier = threading.Barrier(2)
    results: list[Any] = []
    lock = threading.Lock()

    def worker(proposal_id: str) -> None:
        barrier.wait(timeout=5)
        outcome = proposal_svc.prepare_threat_publication_proposal(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id,
            _prepare_request(proposal_id),
            world_root=tmp_path / "graph",
        )
        with lock:
            results.append(outcome)

    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())
    threads = [
        threading.Thread(target=worker, args=(first_id,)),
        threading.Thread(target=worker, args=(second_id,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    labels = {item.response.result_label for item in results}
    assert "publication_proposal_ready" in labels
    assert "publication_proposal_busy" in labels
    ledger = proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id)
    assert ledger is not None
    assert len([item for item in ledger.proposals if item.state == "active"]) == 1


def test_explicit_supersession_updates_lineage(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())

    proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(first_id),
        world_root=tmp_path / "graph",
    )
    replacement = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(second_id, supersedes_proposal_id=first_id),
        world_root=tmp_path / "graph",
    )

    assert replacement.response.result_label == "publication_proposal_ready"
    ledger = proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id)
    assert ledger is not None
    assert ledger.active_proposal_id == second_id
    old = next(item for item in ledger.proposals if item.proposal_id == first_id)
    new = next(item for item in ledger.proposals if item.proposal_id == second_id)
    assert old.state == "superseded"
    assert old.superseded_by_proposal_id == second_id
    assert new.supersedes_proposal_id == first_id


def test_create_new_collision_rejects_without_graph_mutation(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    assert resolution is not None
    assert resolution.created_node_id is not None
    store = _empty_parent_store()
    template = next(iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values()))
    occupied = template.model_copy(update={"node_id": resolution.created_node_id})
    store = store.model_copy(update={"nodes": {resolution.created_node_id: occupied}})

    with patch.object(proposal_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store):
        outcome = proposal_svc.prepare_threat_publication_proposal(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id,
            _prepare_request(),
            world_root=tmp_path / "graph",
        )
    assert outcome.response.result_label == "publication_proposal_typed_collision"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_corrupt_ledger_fails_closed(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    path = proposal_svc._ledger_path(tmp_path, draft.draft_id, op_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"schema":"broken"}', encoding="utf-8")
    outcome = proposal_svc.read_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, str(uuid.uuid4())
    )
    assert outcome.response.result_label == "publication_proposal_integrity_failure"
    assert outcome.response.resolution_id is None


def test_sealed_package_reconstructs_contribution_id(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=tmp_path / "graph",
    )
    proposal = outcome.response.proposal
    assert proposal is not None
    _verified, contribution = resolve_merged_contribution_from_package(
        review_package=proposal.sealed_proposal,
        confirming_principal="gm",
        world_id_hint="world_1",
        root=tmp_path / "graph",
        expected_parent_revision_id=proposal.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    assert contribution.contribution_id == proposal.expected_contribution_id


def test_success_leaves_predecessor_stores_unchanged(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    draft_before = _draft_path(tmp_path, draft.draft_id).read_bytes()
    pub_before = pub_svc._ledger_path(tmp_path, draft.draft_id).read_bytes()
    identity_before = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()

    proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )

    assert _draft_path(tmp_path, draft.draft_id).read_bytes() == draft_before
    assert pub_svc._ledger_path(tmp_path, draft.draft_id).read_bytes() == pub_before
    assert identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes() == identity_before


def test_missing_resolution_rejects_without_proposal(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    missing_resolution_id = str(uuid.uuid4())

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        missing_resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )

    assert outcome.response.result_label == "publication_proposal_resolution_not_active"
    assert outcome.response.resolution_id == missing_resolution_id
    _assert_no_proposal_storage(tmp_path, draft.draft_id, op_id)


def test_superseded_resolution_rejects_without_proposal(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    first_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    _supersede_resolution(tmp_path, draft, op_id, parent, first_resolution_id=first_id)

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        first_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )

    assert outcome.response.result_label == "publication_proposal_resolution_not_active"
    assert outcome.response.resolution_id == first_id
    _assert_no_proposal_storage(tmp_path, draft.draft_id, op_id)


def test_cancelled_operation_rejects_without_proposal(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    cancel_req = CancelThreatPublicationOperationRequestV1(actor="gm", note="cancelled")
    cancelled = cancel_publication_operation(tmp_path, draft.draft_id, op_id, cancel_req)
    assert cancelled.response.result_label == "publication_cancelled"

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )

    assert outcome.response.result_label == "publication_proposal_operation_not_ready"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_storage_failure_before_replace_leaves_no_partial_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    draft_before = _draft_path(tmp_path, draft.draft_id).read_bytes()
    pub_before = pub_svc._ledger_path(tmp_path, draft.draft_id).read_bytes()
    identity_before = identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes()
    ledger_path = proposal_svc._ledger_path(tmp_path, draft.draft_id, op_id)

    def _raise_on_proposal_ledger_write(path: Path, payload: dict) -> None:
        if path == ledger_path:
            raise OSError("simulated storage failure")
        proposal_svc.write_json(path, payload)

    monkeypatch.setattr(proposal_svc, "write_json", _raise_on_proposal_ledger_write)

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )

    assert outcome.response.result_label == "publication_proposal_storage_unavailable"
    assert not ledger_path.exists()
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None
    assert _draft_path(tmp_path, draft.draft_id).read_bytes() == draft_before
    assert pub_svc._ledger_path(tmp_path, draft.draft_id).read_bytes() == pub_before
    assert identity_svc._ledger_path(tmp_path, draft.draft_id, op_id).read_bytes() == identity_before


def test_incompatible_external_resource_at_exact_parent_rejects_without_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    incompatible_node = _incompatible_external_resource_store_node()
    store = _empty_parent_store().model_copy(
        update={"nodes": {incompatible_node.node_id: incompatible_node}}
    )

    with patch.object(
        proposal_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = proposal_svc.prepare_threat_publication_proposal(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id,
            _prepare_request(),
            world_root=tmp_path / "graph",
        )

    assert outcome.response.result_label == "publication_proposal_typed_collision"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_incompatible_binding_at_exact_parent_rejects_without_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    assert resolution is not None
    assert resolution.created_node_id is not None
    threat_node_id = resolution.created_node_id
    resource_node_id = external_statblock_node_id("sb_1")
    incompatible_edge = _incompatible_binding_edge(
        threat_node_id=threat_node_id,
        resource_node_id=resource_node_id,
        use_deterministic_edge_id=False,
    )
    store = _empty_parent_store().model_copy(
        update={"edges": {incompatible_edge.edge_id: incompatible_edge}}
    )

    with patch.object(
        proposal_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = proposal_svc.prepare_threat_publication_proposal(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id,
            _prepare_request(),
            world_root=tmp_path / "graph",
        )

    assert outcome.response.result_label == "publication_proposal_typed_collision"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_connect_target_missing_at_exact_parent_rejects_without_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _connect_resolution(tmp_path, draft, op_id, parent)

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=tmp_path / "graph",
    )

    assert outcome.response.result_label == "publication_proposal_typed_collision"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_success_leaves_graph_head_and_revision_bytes_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    world_root = tmp_path / "graph"
    head_before = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    tree_before = _world_tree_file_snapshot(world_root)

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(),
        world_root=world_root,
    )

    assert outcome.response.result_label == "publication_proposal_ready"
    head_after = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    tree_after = _world_tree_file_snapshot(world_root)
    assert head_after == head_before
    assert tree_after == tree_before


def test_supersedes_without_ledger_prepare_leaves_no_proposal_storage(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)

    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(supersedes_proposal_id=str(uuid.uuid4())),
        world_root=tmp_path / "graph",
    )

    assert outcome.response.result_label == "publication_proposal_input_conflict"
    assert outcome.response.resolution_id == resolution_id
    _assert_no_proposal_storage(tmp_path, draft.draft_id, op_id)


def test_get_not_found_leaves_no_proposal_storage(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)

    outcome = proposal_svc.read_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, str(uuid.uuid4())
    )

    assert outcome.response.result_label == "publication_proposal_not_found"
    assert outcome.response.resolution_id is None
    _assert_no_proposal_storage(tmp_path, draft.draft_id, op_id)


def test_get_existing_proposal_after_prepare_still_returns_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())

    prepared = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=tmp_path / "graph",
    )
    assert prepared.response.result_label == "publication_proposal_ready"

    read = proposal_svc.read_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, proposal_id
    )
    assert read.response.result_label == "publication_proposal_ready"
    assert read.response.resolution_id == resolution_id
    assert read.response.proposal == prepared.response.proposal


def test_get_not_found_with_existing_ledger_returns_null_resolution_id(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(proposal_id),
        world_root=tmp_path / "graph",
    )

    outcome = proposal_svc.read_threat_publication_proposal(
        tmp_path, draft.draft_id, op_id, str(uuid.uuid4())
    )

    assert outcome.response.result_label == "publication_proposal_not_found"
    assert outcome.response.resolution_id is None


def test_wrong_envelope_external_resource_at_exact_parent_rejects_without_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    incompatible_node = _correct_payload_wrong_envelope_resource_node()
    store = _empty_parent_store().model_copy(
        update={"nodes": {incompatible_node.node_id: incompatible_node}}
    )

    with patch.object(
        proposal_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = proposal_svc.prepare_threat_publication_proposal(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id,
            _prepare_request(),
            world_root=tmp_path / "graph",
        )

    assert outcome.response.result_label == "publication_proposal_typed_collision"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None


def test_wrong_label_aliases_external_resource_at_exact_parent_rejects_without_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    incompatible_node = _correct_payload_wrong_label_aliases_resource_node()
    store = _empty_parent_store().model_copy(
        update={"nodes": {incompatible_node.node_id: incompatible_node}}
    )

    with patch.object(
        proposal_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = proposal_svc.prepare_threat_publication_proposal(
            tmp_path,
            draft.draft_id,
            op_id,
            resolution_id,
            _prepare_request(),
            world_root=tmp_path / "graph",
        )

    assert outcome.response.result_label == "publication_proposal_typed_collision"
    assert proposal_svc._load_ledger_unlocked(tmp_path, draft.draft_id, op_id) is None
