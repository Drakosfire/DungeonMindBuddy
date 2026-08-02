"""SBW09c2b: Threat publication commit service tests."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import graph_memory.kernel as kernel
from graph_memory.kernel.contribution_models import ContributionMergeResult, GraphContribution
from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH, load_union_supergraph_store
from graph_memory.union_supergraph.model import ContributionReplayManifestEntry
from graph_memory.world_supergraph.errors import WorldGraphIntegrityError
from graph_memory.world_supergraph.model import WorldGraphRevision

import apps.live_control_server.services.threat_publication_commits as commit_svc
import apps.live_control_server.services.threat_publication_proposals as proposal_svc
from apps.live_control_server.models.threat_publication_commit import ConfirmThreatPublicationRequestV1
from apps.live_control_server.services.threat_publication_commit_store import commit_root
from tests.test_threat_publication_proposals import (
    _begin_operation,
    _connect_resolution,
    _create_new_resolution,
    _mechanics_saved_draft,
    _prepare_request,
    _threat_store_node,
)


def _prepare_proposal(
    tmp_path: Path,
    draft,
    op_id: str,
    resolution_id: str,
    proposal_id: str | None = None,
    **overrides: Any,
):
    request = _prepare_request(proposal_id, **overrides)
    outcome = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        request,
        world_root=tmp_path / "graph",
    )
    assert outcome.response.result_label == "publication_proposal_ready"
    assert outcome.response.proposal is not None
    return outcome.response.proposal, request


def _confirm_request(proposal, commit_id: str | None = None, **overrides: Any):
    payload: dict[str, Any] = {
        "commit_id": commit_id or str(uuid.uuid4()),
        "sealed_proposal_digest": proposal.sealed_proposal_digest,
        "expected_parent_revision_id": proposal.expected_parent_revision_id,
        "actor": "gm",
    }
    payload.update(overrides)
    return ConfirmThreatPublicationRequestV1.model_validate(payload)


def _commit_ledger_bytes(tmp_path: Path, draft_id: str, operation_id: str) -> bytes:
    path = commit_root(tmp_path) / draft_id / operation_id / "ledger.json"
    return path.read_bytes()


def _assert_no_commit_storage(tmp_path: Path, draft_id: str, operation_id: str) -> None:
    operation_dir = commit_root(tmp_path) / draft_id / operation_id
    assert not operation_dir.exists()


def _merge_success_result(proposal, *, revision_id: str = "rev:committed1") -> ContributionMergeResult:
    return ContributionMergeResult(
        world_id="world_1",
        parent_revision_id=proposal.expected_parent_revision_id,
        revision_id=revision_id,
        contribution_ids=[proposal.expected_contribution_id],
        accepted_assertion_ids=list(proposal.accepted_assertion_ids),
        published=True,
    )


def _recovery_manifest(proposal, *, revision_id: str = "rev:recovered1") -> WorldGraphRevision:
    return WorldGraphRevision(
        world_id="world_1",
        revision_id=revision_id,
        parent_revision_id=proposal.expected_parent_revision_id,
        created_at="2020-01-01T00:00:00Z",
        operation_ids=[proposal.expected_contribution_id],
        graph_schema="union_supergraph_v1",
        graph_payload_sha256="a" * 64,
        graph_payload_path="payload.json",
        status="published",
    )


def _contribution_from_proposal(proposal, world_root: Path):
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    _verified, contribution = resolve_merged_contribution_from_package(
        review_package=proposal.sealed_proposal,
        confirming_principal=proposal.created_by,
        world_id_hint="world_1",
        root=world_root,
        expected_parent_revision_id=proposal.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    return contribution


def _recovery_store(proposal, world_root: Path):
    contribution = _contribution_from_proposal(proposal, world_root)
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH).model_copy(
        update={
            "nodes": {},
            "edges": {},
            "aliases": {},
            "adjacency": {},
            "evidence": {},
            "source_artifacts": {},
            "contribution_source_payload_sha256": {
                proposal.expected_contribution_id: digest,
            },
            "contribution_replay_manifest": [
                ContributionReplayManifestEntry(
                    contribution_id=proposal.expected_contribution_id,
                    status="active",
                    source_payload_sha256=digest,
                )
            ],
        }
    )
    return store


def _pipeline_create_new(tmp_path: Path, monkeypatch):
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _create_new_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    proposal, _request = _prepare_proposal(tmp_path, draft, op_id, resolution_id, proposal_id)
    return draft, op_id, resolution_id, proposal_id, proposal, parent


def test_create_new_confirm_intent_merge_receipt(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    commit_id = str(uuid.uuid4())
    request = _confirm_request(proposal, commit_id)

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=tmp_path / "graph",
        merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert outcome.merge_calls == 1
    assert outcome.response.commit is not None
    assert outcome.response.commit.state in {"committed_verified", "committed_unverified"}
    assert outcome.response.commit.committed_revision_id is not None
    assert outcome.response.result_label in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }


def test_connect_existing_no_threat_rewrite_in_contribution(
    tmp_path: Path, monkeypatch
) -> None:
    draft, parent = _mechanics_saved_draft(
        tmp_path, monkeypatch, name="Unique Threat", graph_nodes={"threat:1": _threat_store_node()}
    )
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, _resolution = _connect_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    proposal, _request = _prepare_proposal(tmp_path, draft, op_id, resolution_id, proposal_id)
    captured: list[GraphContribution] = []

    def merge_fn(_world_root, *, world_id, contribution, expected_parent_revision_id):
        captured.append(contribution)
        return _merge_success_result(proposal)

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal),
        world_root=tmp_path / "graph",
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert outcome.merge_calls == 1
    assert len(captured) == 1
    node_assertions = [
        item
        for item in captured[0].accepted_assertions
        if item.assertion_kind in {"node", "node_upsert"}
        and not str(item.subject_node_id).startswith("external:")
    ]
    assert node_assertions == []


def test_exact_committed_replay_merge_calls_zero(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    commit_id = str(uuid.uuid4())
    request = _confirm_request(proposal, commit_id)
    merge_calls = {"count": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["count"] += 1
        return _merge_success_result(proposal)

    first = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=tmp_path / "graph",
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )
    assert first.merge_calls == 1

    with patch.object(commit_svc, "read_identity_resolution") as read_resolution:
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=tmp_path / "graph",
            merge_fn=merge_fn,
            lookup_fn=lambda *_a, **_k: tuple(),
        )
    read_resolution.assert_not_called()
    assert replay.merge_calls == 0
    assert merge_calls["count"] == 1
    assert replay.response.commit is not None
    assert first.response.commit is not None
    assert replay.response.commit.commit_id == first.response.commit.commit_id
    assert replay.response.commit.request_digest == first.response.commit.request_digest


def test_same_commit_id_changed_request_input_conflict_ledger_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    commit_id = str(uuid.uuid4())
    request = _confirm_request(proposal, commit_id)

    commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=tmp_path / "graph",
        merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
        lookup_fn=lambda *_a, **_k: tuple(),
    )
    before = _commit_ledger_bytes(tmp_path, draft.draft_id, op_id)

    changed = _confirm_request(proposal, commit_id, operator_note="different")
    conflict = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        changed,
        world_root=tmp_path / "graph",
        merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert conflict.response.result_label == "publication_commit_input_conflict"
    assert _commit_ledger_bytes(tmp_path, draft.draft_id, op_id) == before


def test_different_commit_id_after_claim_is_busy(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    first_id = str(uuid.uuid4())
    commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal, first_id),
        world_root=tmp_path / "graph",
        merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    busy = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal, str(uuid.uuid4())),
        world_root=tmp_path / "graph",
    )
    assert busy.response.result_label == "publication_commit_busy"


def test_reconstruction_uses_proposal_created_by_not_confirm_actor(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    captured: list[GraphContribution] = []

    def merge_fn(_world_root, *, world_id, contribution, expected_parent_revision_id):
        captured.append(contribution)
        return _merge_success_result(proposal)

    commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal, actor="other_operator"),
        world_root=tmp_path / "graph",
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert len(captured) == 1
    assert captured[0].contribution_id == proposal.expected_contribution_id


def test_merge_raises_lookup_recovers_committed_unverified(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:recovered1"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _recovery_store(proposal, world_root)

    def merge_fn(*_args, **_kwargs):
        raise RuntimeError("simulated merge crash")

    def lookup_fn(_world_root, _world_id, _contribution_id):
        return (manifest,)

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=world_root,
            merge_fn=merge_fn,
            lookup_fn=lookup_fn,
        )

    assert outcome.merge_calls == 1
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.recovered_via_operation_lookup is True
    assert outcome.response.commit.committed_revision_id == revision_id


def test_merge_raises_lookup_oserror_recovery_pending(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )

    def merge_fn(*_args, **_kwargs):
        raise RuntimeError("simulated merge crash")

    def lookup_fn(*_args, **_kwargs):
        raise OSError("lookup unavailable")

    with patch.object(commit_svc, "_maybe_retry", side_effect=lambda **kwargs: (
        kwargs["record"],
        kwargs["merge_calls"],
        "publication_commit_recovery_pending",
    )):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=tmp_path / "graph",
            merge_fn=merge_fn,
            lookup_fn=lookup_fn,
        )

    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"


def test_merge_raises_lookup_integrity_failure(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )

    def merge_fn(*_args, **_kwargs):
        raise RuntimeError("simulated merge crash")

    def lookup_fn(*_args, **_kwargs):
        raise WorldGraphIntegrityError("corrupt graph")

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal),
        world_root=tmp_path / "graph",
        merge_fn=merge_fn,
        lookup_fn=lookup_fn,
    )

    assert outcome.response.result_label == "publication_commit_integrity_failure"


def test_lookup_two_matches_is_ambiguous(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    manifest = _recovery_manifest(proposal)

    def merge_fn(*_args, **_kwargs):
        raise RuntimeError("simulated merge crash")

    def lookup_fn(*_args, **_kwargs):
        return (manifest, manifest.model_copy(update={"revision_id": "rev:other"}))

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal),
        world_root=tmp_path / "graph",
        merge_fn=merge_fn,
        lookup_fn=lookup_fn,
    )

    assert outcome.response.result_label == "publication_commit_outcome_ambiguous"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "ambiguous"


def test_published_false_zero_lookup_uncommitted(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )

    def merge_fn(*_args, **_kwargs):
        return ContributionMergeResult(
            world_id="world_1",
            parent_revision_id=proposal.expected_parent_revision_id,
            revision_id=proposal.expected_parent_revision_id,
            contribution_ids=[],
            accepted_assertion_ids=[],
            published=False,
        )

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal),
        world_root=tmp_path / "graph",
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert outcome.response.result_label == "publication_commit_uncommitted"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "uncommitted"
    assert outcome.response.retry_allowed is False


def test_missing_get_creates_no_commit_dirs(tmp_path: Path, monkeypatch) -> None:
    draft, parent = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    missing_commit_id = str(uuid.uuid4())

    outcome = commit_svc.read_threat_publication_commit(
        tmp_path, draft.draft_id, op_id, missing_commit_id
    )

    assert outcome.response.result_label == "publication_commit_not_found"
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)
    proposal_lock = (
        proposal_svc._operation_directory(tmp_path, draft.draft_id, op_id) / ".proposal.lock"
    )
    assert not proposal_lock.exists()


def test_commit_claim_then_prepare_supersession_busy(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(proposal),
        world_root=tmp_path / "graph",
        merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    supersede = proposal_svc.prepare_threat_publication_proposal(
        tmp_path,
        draft.draft_id,
        op_id,
        resolution_id,
        _prepare_request(str(uuid.uuid4()), supersedes_proposal_id=proposal_id),
        world_root=tmp_path / "graph",
    )

    assert supersede.response.result_label == "publication_proposal_busy"
    assert "commit" in (supersede.response.message or "").casefold()
