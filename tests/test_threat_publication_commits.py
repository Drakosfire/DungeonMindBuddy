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
from apps.live_control_server.models.threat_publication_commit import ThreatPublicationCommitV1
from apps.live_control_server.services.threat_publication_commit_store import (
    commit_root,
    load_threat_publication_commit_ledger_unlocked,
    save_threat_publication_commit_ledger_unlocked,
)
from apps.live_control_server.services.threat_publication_commit_store import (
    ThreatPublicationCommitLedgerV1,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    ExternalResourceV1,
    ThreatStatblockBindingV1,
    external_statblock_node_id,
)
from tests.test_threat_publication_proposals import (
    _locator,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptedMechanicsRefV1,
)
from apps.live_control_server.services.threat_publication_proposals import (
    _binding_payload as _proposal_binding_payload,
)
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
    assert commit_svc._unmodified_contribution_matches_expected_ids(
        contribution, list(proposal.accepted_assertion_ids)
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
    assert replay.merge_calls == 0
    assert merge_calls["count"] == 1
    assert replay.response.commit is not None
    assert first.response.commit is not None
    assert replay.response.commit.commit_id == first.response.commit.commit_id
    assert replay.response.commit.request_digest == first.response.commit.request_digest
    # Terminal verified replay must skip dependency reads; unverified may re-check SBW09b.
    if replay.response.commit.state == "committed_verified":
        read_resolution.assert_not_called()
    else:
        assert replay.response.commit.state == "committed_unverified"


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
    merge_calls = {"n": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        raise RuntimeError("simulated merge crash")

    def lookup_fn(*_args, **_kwargs):
        raise OSError("lookup unavailable")

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

    assert outcome.merge_calls == 1
    assert merge_calls["n"] == 1
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.merge_attempt_count == 1
    assert outcome.response.retry_allowed is True


def test_merge_raises_lookup_integrity_failure(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    merge_calls = {"n": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
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

    assert outcome.merge_calls == 1
    assert merge_calls["n"] == 1
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"


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

    assert outcome.merge_calls == 1
    assert outcome.response.result_label == "publication_commit_outcome_ambiguous"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "ambiguous"


def test_unique_contradictory_match_is_ambiguous(tmp_path: Path, monkeypatch) -> None:
    """Integrity-valid unique match with wrong parent → ambiguous; no merge retry."""
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    bad = _recovery_manifest(proposal, revision_id="rev:badparent")
    bad = bad.model_copy(update={"parent_revision_id": "rev:wrong_parent"})
    store = _recovery_store(proposal, world_root)
    merge_calls = {"n": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        raise RuntimeError("simulated merge crash")

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
            lookup_fn=lambda *_a, **_k: (bad,),
        )

    assert outcome.merge_calls == 1
    assert merge_calls["n"] == 1
    assert outcome.response.result_label == "publication_commit_outcome_ambiguous"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "ambiguous"
    assert outcome.response.commit.committed_revision_id is None


def test_zero_lookup_permits_one_bounded_retry(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    merge_calls = {"n": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        if merge_calls["n"] == 1:
            raise RuntimeError("first attempt uncertain")
        return _merge_success_result(proposal, revision_id="rev:retry_ok")

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

    assert outcome.merge_calls == 2
    assert merge_calls["n"] == 2
    assert outcome.response.commit is not None
    assert outcome.response.commit.merge_attempt_count == 2
    assert outcome.response.commit.committed_revision_id == "rev:retry_ok"
    assert outcome.response.result_label in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }


def test_receipt_save_failure_recovers_on_replay(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:receipt_recover"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _recovery_store(proposal, world_root)
    request = _confirm_request(proposal)
    merge_calls = {"n": 0}
    save_count = {"n": 0}
    real_save = commit_svc._save_commit

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        return _merge_success_result(proposal, revision_id=revision_id)

    def flaky_save(root, commit):
        save_count["n"] += 1
        # First save is intent (committing). Second is receipt (committed_unverified) — fail it.
        if commit.state == "committed_unverified" and save_count["n"] <= 2:
            from apps.live_control_server.services.threat_publication_commit_store import (
                ThreatPublicationCommitStorageError,
            )

            raise ThreatPublicationCommitStorageError(
                "receipt save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(commit_svc, "_save_commit", side_effect=flaky_save):
        first = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=merge_fn,
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert first.merge_calls == 1
    assert first.response.result_label == "publication_commit_storage_unavailable"
    assert first.response.commit is not None
    assert first.response.commit.state == "committing"
    assert first.response.commit.merge_attempt_count == 2
    assert first.response.retry_allowed is False

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=merge_fn,
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert replay.merge_calls == 0
    assert merge_calls["n"] == 1
    assert replay.response.commit is not None
    assert replay.response.commit.committed_revision_id == revision_id
    assert replay.response.commit.recovered_via_operation_lookup is True
    assert replay.response.result_label in {
        "publication_commit_verified",
        "publication_commit_committed_unverified",
    }


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
            diagnostics=["merge_failed:node assertion assertion:x has unresolved evidence references"],
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

    assert outcome.merge_calls == 1
    assert outcome.response.result_label == "publication_commit_uncommitted"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "uncommitted"
    assert outcome.response.retry_allowed is False
    assert outcome.response.message is not None
    assert "unresolved evidence" in outcome.response.message
    assert "Cancel this publication" in outcome.response.message


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


def test_ordered_assertion_ids_required() -> None:
    assert commit_svc._assertion_ids_match(["a", "b"], ["a", "b"]) is True
    assert commit_svc._assertion_ids_match(["a", "b"], ["b", "a"]) is False


def test_corrupt_record_contribution_id_integrity_failure(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    request = _confirm_request(proposal)
    world_root = tmp_path / "graph"

    record, early, _contribution, _proposal = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    commit_svc._save_commit(tmp_path, record)

    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    corrupt = ledger.commit.model_copy(
        update={"expected_contribution_id": "contrib:corrupt"}
    )
    save_threat_publication_commit_ledger_unlocked(
        tmp_path,
        ThreatPublicationCommitLedgerV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            commit=corrupt,
        ),
    )

    merge_calls = {"n": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        return _merge_success_result(proposal)

    replay = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert replay.merge_calls == 0
    assert merge_calls["n"] == 0
    assert replay.response.result_label == "publication_commit_integrity_failure"
    assert "contribution_id_mismatch" in (replay.response.message or "")


def _verification_store(proposal, world_root: Path, *, binding_direction: str = "outbound"):
    contribution = _contribution_from_proposal(proposal, world_root)
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    template_node = next(
        iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values())
    )
    template_edge = next(
        iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).edges.values())
    )
    statblock_id = "sb_1"
    resource_node_id = external_statblock_node_id(statblock_id)
    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(), accepted_from_draft_version=1, accepted_at="2020-01-01T00:00:00Z"
    )
    binding_value, binding_edge_id, _binding_id = _proposal_binding_payload(
        threat_node_id=proposal.threat_node_id,
        accepted_ref=ref,
    )
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
    resource_label = f"External statblock {statblock_id}"
    resource_node = template_node.model_copy(
        update={
            "node_id": resource_node_id,
            "label": resource_label,
            "kind": "external_resource",
            "role": "statblock",
            "aliases": [resource_label],
            "source_domains": ["manual_seed"],
            "evidence_ref_ids": [],
            "external_resource": resource,
        }
    )
    threat_assertion = next(
        item
        for item in contribution.accepted_assertions
        if item.assertion_kind == "node"
        and item.subject_node_id == proposal.threat_node_id
    )
    threat_value = threat_assertion.value or {}
    threat_node = template_node.model_copy(
        update={
            "node_id": proposal.threat_node_id,
            "label": threat_assertion.label,
            "kind": str(threat_value.get("kind", "Threat")),
            "role": str(threat_value.get("role", "threat")),
            "aliases": list(threat_value.get("aliases") or []),
            "source_domains": list(threat_value.get("source_domains") or ["worldbuilding"]),
            "evidence_ref_ids": [],
            "external_resource": None,
        }
    )
    binding = ThreatStatblockBindingV1.model_validate(binding_value["threat_statblock_binding"])
    binding_edge = template_edge.model_copy(
        update={
            "edge_id": binding_edge_id,
            "source_node_id": proposal.threat_node_id,
            "target_node_id": resource_node_id,
            "predicate": "uses_statblock",
            "label": "uses statblock",
            "direction": binding_direction,
            "source_domains": ["worldbuilding"],
            "session_ids": [],
            "evidence_ref_ids": [],
            "threat_statblock_binding": binding,
        }
    )
    assertion_support = {}
    for assertion in contribution.accepted_assertions:
        evidence_ids = list(assertion.evidence_ref_ids or [])
        artifact_ids = (
            [assertion.source_artifact_id] if assertion.source_artifact_id else []
        )
        assertion_support[assertion.assertion_id] = {
            "assertion_id": assertion.assertion_id,
            "active_contribution_ids": [proposal.expected_contribution_id],
            "superseded_contribution_ids": [],
            "retracted_contribution_ids": [],
            "evidence_ref_ids": evidence_ids,
            "source_artifact_ids": artifact_ids,
            "support_state": "supported",
            "introduced_by_contribution_id": proposal.expected_contribution_id,
            "provenance_lineage_version": 1,
            "per_contribution_evidence_ref_ids": {
                proposal.expected_contribution_id: evidence_ids,
            },
            "per_contribution_source_artifact_ids": {
                proposal.expected_contribution_id: artifact_ids,
            },
        }
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH).model_copy(
        update={
            "nodes": {
                proposal.threat_node_id: threat_node,
                resource_node_id: resource_node,
            },
            "edges": {binding_edge_id: binding_edge},
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
            "assertion_support": assertion_support,
        }
    )
    return store


def test_verification_save_failure_returns_prior_committed_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:verify-save-fail"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _verification_store(proposal, world_root)
    request = _confirm_request(proposal)
    real_save = commit_svc._save_commit

    def merge_fn(*_args, **_kwargs):
        return _merge_success_result(proposal, revision_id=revision_id)

    commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    prior = ledger.commit
    assert prior.state in {"committed_unverified", "committed_verified"}

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if commit.state in {"committed_verified", "committed_unverified"} and (
            commit.verification_status != prior.verification_status
            or commit.state != prior.state
        ):
            from apps.live_control_server.services.threat_publication_commit_store import (
                ThreatPublicationCommitStorageError,
            )

            raise ThreatPublicationCommitStorageError(
                "verification save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(commit_svc, "_save_commit", side_effect=flaky_save):
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=merge_fn,
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert replay.merge_calls == 0
    assert replay.response.result_label == "publication_commit_committed_unverified"
    assert replay.response.commit == prior
    assert replay.response.retry_allowed is False
    assert "verification could not persist" in (replay.response.message or "")


def test_verify_committed_fails_when_binding_direction_wrong(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:binding-direction-fail"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _verification_store(proposal, world_root, binding_direction="inbound")
    request = _confirm_request(proposal)

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: _merge_success_result(proposal, revision_id=revision_id),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.verification_status == "failed"
    assert "binding_direction_mismatch" in outcome.response.commit.verification_codes


def test_projection_audit_accepts_outgoing_direction(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    contribution = _contribution_from_proposal(proposal, world_root)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=_confirm_request(proposal),
    )
    assert early is None and record is not None
    record = commit_svc._with_updated(
        record,
        state="committed_unverified",
        committed_revision_id="rev:proj1",
    )
    binding = ThreatStatblockBindingV1.model_validate(
        (_proposal_binding_payload(
            threat_node_id=proposal.threat_node_id,
            accepted_ref=AcceptedMechanicsRefV1.from_locator(
                _locator(), accepted_from_draft_version=1, accepted_at="2020-01-01T00:00:00Z"
            ),
        )[0])["threat_statblock_binding"]
    )
    threat_assertion = commit_svc._threat_node_assertion(contribution, record.threat_node_id)
    assert threat_assertion is not None
    threat_value = threat_assertion.value or {}

    class _Node:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Rel:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Snap:
        revision_id = "rev:proj1"

    class _Projection:
        snapshot = _Snap()
        nodes = [
            _Node(
                node_id=record.threat_node_id,
                label=threat_assertion.label,
                kind=str(threat_value.get("kind", "Threat")),
                role=threat_value.get("role"),
                aliases=list(threat_value.get("aliases") or []),
                source_domains=list(threat_value.get("source_domains") or []),
                external_resource=None,
            ),
            _Node(
                node_id=record.external_resource_node_id,
                label="External statblock sb_1",
                kind="external_resource",
                role="statblock",
                aliases=["External statblock sb_1"],
                source_domains=["manual_seed"],
                external_resource=ExternalResourceV1.model_validate(
                    {
                        "schema": "dmb_external_resource_v1",
                        "provider": PROVIDER,
                        "resource_type": "statblock",
                        "resource_id": "sb_1",
                        "contract": CONTRACT,
                        "contract_version": CONTRACT_VERSION,
                    }
                ),
            ),
        ]
        relationships = [
            _Rel(
                edge_id=record.binding_edge_id,
                source_node_id=record.threat_node_id,
                target_node_id=record.external_resource_node_id,
                predicate="uses_statblock",
                direction="outgoing",
                threat_statblock_binding=binding,
            )
        ]
        attributes = [
            type(
                "Attr",
                (),
                {
                    "assertion_id": assertion.assertion_id,
                    "subject_node_id": record.threat_node_id,
                    "predicate": assertion.predicate,
                    "value": dict(assertion.value or {}),
                },
            )()
            for assertion in commit_svc._authored_field_assertions(
                contribution, record.threat_node_id
            )
        ]

    codes = commit_svc._verify_projection_audit(
        _Projection(),
        record=record,
        contribution=contribution,
        statblock_id="sb_1",
    )
    assert "projection_binding_direction_mismatch" not in codes
    assert codes == []

def test_verified_replay_skips_dependency_reads(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    request = _confirm_request(proposal)
    world_root = tmp_path / "graph"
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    verified = commit_svc._with_updated(
        record,
        state="committed_verified",
        committed_revision_id="rev:verified1",
        verification_status="passed",
    )
    commit_svc._save_commit(tmp_path, verified)

    with patch.object(
        commit_svc,
        "load_threat_publication_proposal_ledger_unlocked",
        side_effect=AssertionError("proposal ledger must not be read"),
    ), patch.object(
        commit_svc,
        "resolve_merged_contribution_from_package",
        side_effect=AssertionError("reconstruction must not run"),
    ):
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("merge")),
            lookup_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("lookup")),
        )

    assert replay.merge_calls == 0
    assert replay.response.result_label == "publication_commit_verified"
    assert replay.response.commit == verified


def test_corrupt_record_world_id_integrity_failure(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    request = _confirm_request(proposal)
    world_root = tmp_path / "graph"
    record, early, _contribution, _proposal = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    commit_svc._save_commit(tmp_path, record)

    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    corrupt = ledger.commit.model_copy(update={"world_id": "world:other"})
    save_threat_publication_commit_ledger_unlocked(
        tmp_path,
        ThreatPublicationCommitLedgerV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            commit=corrupt,
        ),
    )

    merge_calls = {"n": 0}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        return _merge_success_result(proposal)

    replay = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert merge_calls["n"] == 0
    assert replay.response.result_label == "publication_commit_integrity_failure"
    assert "world_id_mismatch" in (replay.response.message or "")


def test_c1_records_reconstruction_order_and_merge_uses_unmodified(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    _v, reconstructed = resolve_merged_contribution_from_package(
        review_package=proposal.sealed_proposal,
        confirming_principal=proposal.created_by,
        world_id_hint="world_1",
        root=world_root,
        expected_parent_revision_id=proposal.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    recon_ids = [item.assertion_id for item in reconstructed.accepted_assertions]
    assert list(proposal.accepted_assertion_ids) == recon_ids

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
        world_root=world_root,
        merge_fn=merge_fn,
        lookup_fn=lambda *_a, **_k: tuple(),
    )
    assert outcome.merge_calls == 1
    assert len(captured) == 1
    merged_ids = [item.assertion_id for item in captured[0].accepted_assertions]
    assert merged_ids == recon_ids
    assert captured[0] is not None
    assert not hasattr(commit_svc, "_contribution_ordered_to_expected_ids")
    assert not hasattr(commit_svc, "_require_ordered_contribution")


def test_uncommitted_replay_skips_dependency_reads(tmp_path: Path, monkeypatch) -> None:
    draft, op_id, _resolution_id, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    request = _confirm_request(proposal)
    world_root = tmp_path / "graph"
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    terminal = commit_svc._with_updated(record, state="uncommitted")
    commit_svc._save_commit(tmp_path, terminal)

    with patch.object(
        commit_svc,
        "load_threat_publication_proposal_ledger_unlocked",
        side_effect=AssertionError("proposal ledger must not be read"),
    ):
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert replay.merge_calls == 0
    assert replay.response.result_label == "publication_commit_uncommitted"
    assert replay.response.commit == terminal


def _pipeline_connect_existing(tmp_path: Path, monkeypatch):
    draft, parent = _mechanics_saved_draft(
        tmp_path, monkeypatch, name="Unique Threat", graph_nodes={"threat:1": _threat_store_node()}
    )
    op_id, _op = _begin_operation(tmp_path, draft, parent)
    resolution_id, resolution = _connect_resolution(tmp_path, draft, op_id, parent)
    proposal_id = str(uuid.uuid4())
    proposal, _request = _prepare_proposal(tmp_path, draft, op_id, resolution_id, proposal_id)
    return draft, op_id, resolution_id, proposal_id, proposal, parent, resolution


def _connect_verification_store(
    proposal,
    world_root: Path,
    *,
    selected_target,
    prior_binding_ids: list[str] | None = None,
):
    """Committed store for connect-existing: Threat unchanged + newly published binding."""
    contribution = _contribution_from_proposal(proposal, world_root)
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    template_node = next(
        iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).nodes.values())
    )
    template_edge = next(
        iter(load_union_supergraph_store(DEFAULT_FIXTURE_PATH).edges.values())
    )
    statblock_id = "sb_1"
    resource_node_id = external_statblock_node_id(statblock_id)
    ref = AcceptedMechanicsRefV1.from_locator(
        _locator(), accepted_from_draft_version=1, accepted_at="2020-01-01T00:00:00Z"
    )
    binding_value, binding_edge_id, binding_id = _proposal_binding_payload(
        threat_node_id=proposal.threat_node_id,
        accepted_ref=ref,
    )
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
    resource_label = f"External statblock {statblock_id}"
    resource_node = template_node.model_copy(
        update={
            "node_id": resource_node_id,
            "label": resource_label,
            "kind": "external_resource",
            "role": "statblock",
            "aliases": [resource_label],
            "source_domains": ["manual_seed"],
            "evidence_ref_ids": [],
            "external_resource": resource,
        }
    )
    target_dump = selected_target.model_dump(mode="json", by_alias=True)
    threat_node = template_node.model_copy(
        update={
            "node_id": proposal.threat_node_id,
            "label": target_dump["label"],
            "kind": target_dump["kind"],
            "role": target_dump["role"],
            "aliases": list(target_dump.get("aliases") or []),
            "campaign_scope": target_dump.get("campaign_scope"),
            "summary": target_dump.get("summary"),
            "source_domains": list(target_dump.get("source_domains") or []),
            "evidence_ref_ids": [],
            "external_resource": None,
        }
    )
    binding = ThreatStatblockBindingV1.model_validate(binding_value["threat_statblock_binding"])
    edges = {
        binding_edge_id: template_edge.model_copy(
            update={
                "edge_id": binding_edge_id,
                "source_node_id": proposal.threat_node_id,
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
    }
    for prior_id in prior_binding_ids or []:
        prior_edge_id = f"edge:{prior_id}"
        edges[prior_edge_id] = template_edge.model_copy(
            update={
                "edge_id": prior_edge_id,
                "source_node_id": proposal.threat_node_id,
                "target_node_id": resource_node_id,
                "predicate": "uses_statblock",
                "label": "uses statblock",
                "direction": "outbound",
                "source_domains": ["worldbuilding"],
                "session_ids": [],
                "evidence_ref_ids": [],
                "threat_statblock_binding": binding.model_copy(
                    update={"binding_id": prior_id}
                ),
            }
        )
    assertion_support = {}
    for assertion in contribution.accepted_assertions:
        evidence_ids = list(assertion.evidence_ref_ids or [])
        artifact_ids = (
            [assertion.source_artifact_id] if assertion.source_artifact_id else []
        )
        assertion_support[assertion.assertion_id] = {
            "assertion_id": assertion.assertion_id,
            "active_contribution_ids": [proposal.expected_contribution_id],
            "superseded_contribution_ids": [],
            "retracted_contribution_ids": [],
            "evidence_ref_ids": evidence_ids,
            "source_artifact_ids": artifact_ids,
            "support_state": "supported",
            "introduced_by_contribution_id": proposal.expected_contribution_id,
            "provenance_lineage_version": 1,
            "per_contribution_evidence_ref_ids": {
                proposal.expected_contribution_id: evidence_ids,
            },
            "per_contribution_source_artifact_ids": {
                proposal.expected_contribution_id: artifact_ids,
            },
        }
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH).model_copy(
        update={
            "nodes": {
                proposal.threat_node_id: threat_node,
                resource_node_id: resource_node,
            },
            "edges": edges,
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
            "assertion_support": assertion_support,
        }
    )
    return store, binding, binding_id


def _projection_for_verified_commit(*, record, contribution, binding, selected_target=None):
    threat_assertion = commit_svc._threat_node_assertion(contribution, record.threat_node_id)
    if threat_assertion is not None:
        threat_value = threat_assertion.value or {}
        threat_kwargs = {
            "node_id": record.threat_node_id,
            "label": threat_assertion.label,
            "kind": str(threat_value.get("kind", "Threat")),
            "role": threat_value.get("role"),
            "aliases": list(threat_value.get("aliases") or []),
            "source_domains": list(threat_value.get("source_domains") or []),
            "campaign_scope": threat_value.get("campaign_scope"),
            "summary": threat_value.get("summary"),
            "external_resource": None,
        }
    else:
        assert selected_target is not None
        dump = selected_target.model_dump(mode="json", by_alias=True)
        threat_kwargs = {
            "node_id": record.threat_node_id,
            "label": dump["label"],
            "kind": dump["kind"],
            "role": dump["role"],
            "aliases": list(dump.get("aliases") or []),
            "source_domains": list(dump.get("source_domains") or []),
            "campaign_scope": dump.get("campaign_scope"),
            "summary": dump.get("summary"),
            "external_resource": None,
        }

    class _Node:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Rel:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class _Snap:
        revision_id = record.committed_revision_id

    class _Projection:
        snapshot = _Snap()
        nodes = [
            _Node(**threat_kwargs),
            _Node(
                node_id=record.external_resource_node_id,
                label="External statblock sb_1",
                kind="external_resource",
                role="statblock",
                aliases=["External statblock sb_1"],
                source_domains=["manual_seed"],
                external_resource=ExternalResourceV1.model_validate(
                    {
                        "schema": "dmb_external_resource_v1",
                        "provider": PROVIDER,
                        "resource_type": "statblock",
                        "resource_id": "sb_1",
                        "contract": CONTRACT,
                        "contract_version": CONTRACT_VERSION,
                    }
                ),
            ),
        ]
        relationships = [
            _Rel(
                edge_id=record.binding_edge_id,
                source_node_id=record.threat_node_id,
                target_node_id=record.external_resource_node_id,
                predicate="uses_statblock",
                direction="outgoing",
                threat_statblock_binding=binding,
            )
        ]
        attributes = [
            type(
                "Attr",
                (),
                {
                    "assertion_id": assertion.assertion_id,
                    "subject_node_id": record.threat_node_id,
                    "predicate": assertion.predicate,
                    "value": dict(assertion.value or {}),
                },
            )()
            for assertion in commit_svc._authored_field_assertions(
                contribution, record.threat_node_id
            )
        ]

    return _Projection()


def test_connect_existing_binding_ids_allow_published_binding(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    prior = ["threat-statblock-binding:prior000000000000000"]
    selected = resolution.selected_target.model_copy(update={"binding_ids": prior})
    store, _binding, published_binding_id = _connect_verification_store(
        proposal, world_root, selected_target=selected, prior_binding_ids=prior
    )
    threat = store.nodes[proposal.threat_node_id]
    assert (
        commit_svc._identity_fields_match(
            selected,
            threat,
            store=store,
            published_binding_id=published_binding_id,
        )
        is True
    )
    # Pre-publication equality alone must fail once the new binding is present.
    assert (
        commit_svc._identity_fields_match(selected, threat, store=store) is False
    )

    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=_confirm_request(proposal),
    )
    assert early is None and record is not None
    # Force selected_target with prior bindings for the constraint check.
    record = commit_svc._with_updated(
        record,
        selected_target=selected.model_dump(mode="json", by_alias=True),
        binding_id=published_binding_id,
    )
    codes = commit_svc._verify_connect_existing_constraints(
        store=store, contribution=contribution, record=record
    )
    assert "connect_target_mismatch" not in codes


def test_connect_existing_verify_committed_reaches_verified(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    revision_id = "rev:connect-verified"
    store, binding, _binding_id = _connect_verification_store(
        proposal, world_root, selected_target=resolution.selected_target
    )
    request = _confirm_request(proposal)
    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    unverified = commit_svc._with_updated(
        record,
        state="committed_unverified",
        committed_revision_id=revision_id,
        verification_status="not_started",
        merge_attempt_count=1,
    )
    commit_svc._save_commit(tmp_path, unverified)
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    projection = _projection_for_verified_commit(
        record=unverified,
        contribution=contribution,
        binding=binding,
        selected_target=resolution.selected_target,
    )

    class _Rebuild:
        diagnostics = ["rebuild_equivalent_to_pinned_revision"]

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(
        commit_svc.kernel, "rebuild_from_contributions", return_value=_Rebuild()
    ), patch.object(
        commit_svc.kernel, "project_world_graph", return_value=projection
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_verified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_verified"
    assert outcome.response.commit.verification_status == "passed"


def test_committed_unverified_identity_unavailable_returns_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent, _resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    unverified = commit_svc._with_updated(
        record,
        state="committed_unverified",
        committed_revision_id="rev:identity-unavailable",
        verification_status="not_started",
    )
    commit_svc._save_commit(tmp_path, unverified)

    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_not_found",
            resolution=None,
            predecessor_usable=None,
            message="identity resolution not found",
        ),
        created=False,
    )
    with patch.object(
        commit_svc, "read_identity_resolution", return_value=unavailable
    ):
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert replay.merge_calls == 0
    assert replay.response.result_label == "publication_commit_committed_unverified"
    assert replay.response.commit == unverified
    assert replay.response.retry_allowed is False
    assert "identity dependency unavailable" in (replay.response.message or "")


def test_committed_unverified_identity_contradiction_is_integrity(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    unverified = commit_svc._with_updated(
        record,
        state="committed_unverified",
        committed_revision_id="rev:identity-contradiction",
        verification_status="not_started",
    )
    commit_svc._save_commit(tmp_path, unverified)

    contradictory_target = resolution.selected_target.model_copy(
        update={"label": "Completely Different Threat"}
    )
    identity = _stub_identity_outcome(
        resolution,
        result_label="publication_identity_connected_existing",
        selected_target=contradictory_target,
    )
    with patch.object(commit_svc, "read_identity_resolution", return_value=identity):
        replay = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert replay.merge_calls == 0
    assert replay.response.result_label == "publication_commit_integrity_failure"
    assert "selected_target mismatch" in (replay.response.message or "")


def _stub_identity_outcome(resolution, *, result_label: str, **field_overrides):
    """Boundary identity outcome; overrides bypass resolution model validators."""
    base = {
        "resolution_id": resolution.resolution_id,
        "draft_id": resolution.draft_id,
        "operation_id": resolution.operation_id,
        "source_digest": resolution.source_digest,
        "request_digest": resolution.request_digest,
        "candidate_set_digest": resolution.candidate_set_digest,
        "expected_parent_revision_id": resolution.expected_parent_revision_id,
        "decision": resolution.decision,
        "selected_target": resolution.selected_target,
        "created_node_id": resolution.created_node_id,
        "state": resolution.state,
    }
    base.update(field_overrides)
    fake_resolution = type("Resolution", (), base)()
    return type(
        "IdentityOutcome",
        (),
        {
            "response": type(
                "IdentityResponse",
                (),
                {"result_label": result_label, "resolution": fake_resolution},
            )()
        },
    )()


def _stub_publication_refresh(*, result_label: str, operation=None):
    return type(
        "RefreshOutcome",
        (),
        {
            "response": type(
                "RefreshResponse",
                (),
                {"result_label": result_label, "operation": operation},
            )()
        },
    )()


def _historical_seal_ids(proposal) -> list[str]:
    ids = commit_svc._historical_seal_order_ids(proposal.sealed_proposal)
    assert ids is not None
    return ids


def _mutate_proposal_accepted_ids(
    tmp_path: Path, draft_id: str, operation_id: str, proposal_id: str, new_ids: list[str]
):
    ledger = proposal_svc.load_threat_publication_proposal_ledger_unlocked(
        tmp_path, draft_id, operation_id
    )
    assert ledger is not None
    mutated = ledger.model_copy(
        update={
            "proposals": [
                (
                    p.model_copy(update={"accepted_assertion_ids": list(new_ids)})
                    if p.proposal_id == proposal_id
                    else p
                )
                for p in ledger.proposals
            ]
        }
    )
    proposal_svc._save_ledger_unlocked(tmp_path, mutated)
    return next(p for p in mutated.proposals if p.proposal_id == proposal_id)


def _corrupt_same_set_permutation(recon_ids: list[str], seal_ids: list[str]) -> list[str]:
    assert len(recon_ids) >= 2
    candidate = list(reversed(recon_ids))
    if candidate != recon_ids and candidate != seal_ids:
        return candidate
    candidate = recon_ids[1:] + recon_ids[:1]
    assert candidate != recon_ids and candidate != seal_ids
    return candidate


def test_legacy_seal_order_proposal_requires_supersession(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    recon_ids = list(proposal.accepted_assertion_ids)
    seal_ids = _historical_seal_ids(proposal)
    assert seal_ids != recon_ids
    assert set(seal_ids) == set(recon_ids)

    legacy_proposal = _mutate_proposal_accepted_ids(
        tmp_path, draft.draft_id, op_id, proposal_id, seal_ids
    )
    contribution = _contribution_from_proposal(
        proposal.model_copy(update={"accepted_assertion_ids": recon_ids}), world_root
    )
    assert (
        commit_svc._contribution_order_disposition(
            contribution,
            list(legacy_proposal.accepted_assertion_ids),
            sealed_proposal=legacy_proposal.sealed_proposal,
        )
        == "legacy_seal_order"
    )

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(legacy_proposal),
        world_root=world_root,
        merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
        lookup_fn=lambda *_a, **_k: tuple(),
    )
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_proposal_incompatible"
    assert "supersede" in (outcome.response.message or "").casefold()
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)


def test_corrupt_same_set_permutation_is_integrity_failure(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    recon_ids = list(proposal.accepted_assertion_ids)
    seal_ids = _historical_seal_ids(proposal)
    corrupt_ids = _corrupt_same_set_permutation(recon_ids, seal_ids)

    corrupt_proposal = _mutate_proposal_accepted_ids(
        tmp_path, draft.draft_id, op_id, proposal_id, corrupt_ids
    )
    contribution = _contribution_from_proposal(
        proposal.model_copy(update={"accepted_assertion_ids": recon_ids}), world_root
    )
    assert (
        commit_svc._contribution_order_disposition(
            contribution,
            list(corrupt_proposal.accepted_assertion_ids),
            sealed_proposal=corrupt_proposal.sealed_proposal,
        )
        == "corrupt_permutation"
    )

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        _confirm_request(corrupt_proposal),
        world_root=world_root,
        merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
        lookup_fn=lambda *_a, **_k: tuple(),
    )
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert "corrupt" in (outcome.response.message or "").casefold()
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)


def test_legacy_committing_record_recovers_via_c2a_without_merge(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    recon_ids = list(proposal.accepted_assertion_ids)
    seal_ids = _historical_seal_ids(proposal)
    assert seal_ids != recon_ids

    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    _v, contribution = resolve_merged_contribution_from_package(
        review_package=proposal.sealed_proposal,
        confirming_principal=proposal.created_by,
        world_id_hint="world_1",
        root=world_root,
        expected_parent_revision_id=proposal.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    by_id = {item.assertion_id: item for item in contribution.accepted_assertions}
    seal_ordered = contribution.model_copy(
        update={"accepted_assertions": [by_id[i] for i in seal_ids]}
    )
    seal_digest = kernel.compute_contribution_source_payload_sha256(seal_ordered)

    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None

    legacy_proposal = _mutate_proposal_accepted_ids(
        tmp_path, draft.draft_id, op_id, proposal_id, seal_ids
    )
    legacy_record = commit_svc._with_updated(
        record,
        accepted_assertion_ids=list(legacy_proposal.accepted_assertion_ids),
        expected_contribution_source_payload_sha256=seal_digest,
        proposal_request_digest=legacy_proposal.request_digest,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, legacy_record)

    revision_id = "rev:legacy-recovered"
    manifest = _recovery_manifest(legacy_proposal, revision_id=revision_id)
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH).model_copy(
        update={
            "nodes": {},
            "edges": {},
            "aliases": {},
            "adjacency": {},
            "evidence": {},
            "source_artifacts": {},
            "contribution_source_payload_sha256": {
                legacy_proposal.expected_contribution_id: seal_digest,
            },
            "contribution_replay_manifest": [
                ContributionReplayManifestEntry(
                    contribution_id=legacy_proposal.expected_contribution_id,
                    status="active",
                    source_payload_sha256=seal_digest,
                )
            ],
        }
    )

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.committed_revision_id == revision_id
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert "supersede" not in (outcome.response.message or "").casefold()


def test_committing_identity_unavailable_recovers_via_c2a(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent, _resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    revision_id = "rev:identity-gap-recovered"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _recovery_store(proposal, world_root)
    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_storage_unavailable",
            resolution=None,
            predecessor_usable=None,
            message="identity store unavailable",
        ),
        created=False,
    )

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=unavailable
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.committed_revision_id == revision_id


def test_committing_identity_unavailable_zero_match_keeps_retry_allowed(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent, _resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_busy",
            resolution=None,
            predecessor_usable=None,
            message="identity busy",
        ),
        created=False,
    )
    with patch.object(
        commit_svc, "read_identity_resolution", return_value=unavailable
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.retry_allowed is True
    assert "identity dependency unavailable" in (outcome.response.message or "")


def test_create_new_verify_committed_reaches_verified_full_projection(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:create-verified"
    store = _verification_store(proposal, world_root)
    request = _confirm_request(proposal)
    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    unverified = commit_svc._with_updated(
        record,
        state="committed_unverified",
        committed_revision_id=revision_id,
        verification_status="not_started",
        merge_attempt_count=1,
    )
    commit_svc._save_commit(tmp_path, unverified)
    binding = ThreatStatblockBindingV1.model_validate(
        (_proposal_binding_payload(
            threat_node_id=proposal.threat_node_id,
            accepted_ref=AcceptedMechanicsRefV1.from_locator(
                _locator(), accepted_from_draft_version=1, accepted_at="2020-01-01T00:00:00Z"
            ),
        )[0])["threat_statblock_binding"]
    )
    projection = _projection_for_verified_commit(
        record=unverified, contribution=contribution, binding=binding
    )
    manifest = _recovery_manifest(proposal, revision_id=revision_id)

    class _Rebuild:
        diagnostics = ["rebuild_equivalent_to_pinned_revision"]

    with patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(
        commit_svc.kernel, "rebuild_from_contributions", return_value=_Rebuild()
    ), patch.object(
        commit_svc.kernel, "project_world_graph", return_value=projection
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_verified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_verified"
    assert outcome.response.commit.verification_status == "passed"


def test_c2a_connect_existing_identity_unavailable_cannot_reach_verified(
    tmp_path: Path, monkeypatch
) -> None:
    """Unique c2a match must not verify connect_existing without live SBW09b."""
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    revision_id = "rev:connect-c2a-identity-gap"
    store, binding, _binding_id = _connect_verification_store(
        proposal, world_root, selected_target=resolution.selected_target
    )
    unverified_for_projection = commit_svc._with_updated(
        committing,
        state="committed_unverified",
        committed_revision_id=revision_id,
    )
    projection = _projection_for_verified_commit(
        record=unverified_for_projection,
        contribution=contribution,
        binding=binding,
        selected_target=resolution.selected_target,
    )
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_storage_unavailable",
            resolution=None,
            predecessor_usable=None,
            message="identity store unavailable",
        ),
        created=False,
    )

    class _Rebuild:
        diagnostics = ["rebuild_equivalent_to_pinned_revision"]

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=unavailable
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(
        commit_svc.kernel, "rebuild_from_contributions", return_value=_Rebuild()
    ), patch.object(
        commit_svc.kernel, "project_world_graph", return_value=projection
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.state != "committed_verified"
    assert outcome.response.commit.committed_revision_id == revision_id
    assert outcome.response.retry_allowed is False
    assert "identity dependency unavailable" in (outcome.response.message or "")


def test_c2a_recovery_verification_save_failure_preserves_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    revision_id = "rev:c2a-verify-save-fail"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _recovery_store(proposal, world_root)
    real_save = commit_svc._save_commit
    saved_unverified: dict[str, ThreatPublicationCommitV1 | None] = {"record": None}

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if commit.state == "committed_unverified" and commit.verification_status == "not_started":
            real_save(root, commit)
            saved_unverified["record"] = commit
            return
        if commit.state in {"committed_verified", "committed_unverified"} and (
            commit.verification_status != "not_started" or commit.state == "committed_verified"
        ):
            from apps.live_control_server.services.threat_publication_commit_store import (
                ThreatPublicationCommitStorageError,
            )

            raise ThreatPublicationCommitStorageError(
                "verification save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(
        commit_svc, "_save_commit", side_effect=flaky_save
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert saved_unverified["record"] is not None
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.committed_revision_id == revision_id
    assert outcome.response.commit.verification_status == "not_started"
    assert outcome.response.retry_allowed is False
    assert "verification could not persist" in (outcome.response.message or "")


def test_retry_merge_verification_save_failure_preserves_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:retry-verify-save-fail"
    merge_calls = {"n": 0}
    real_save = commit_svc._save_commit
    saved_unverified: dict[str, ThreatPublicationCommitV1 | None] = {"record": None}

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        if merge_calls["n"] == 1:
            raise RuntimeError("first attempt uncertain")
        return _merge_success_result(proposal, revision_id=revision_id)

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if (
            commit.state == "committed_unverified"
            and commit.verification_status == "not_started"
            and commit.merge_attempt_count == 2
        ):
            real_save(root, commit)
            saved_unverified["record"] = commit
            return
        if commit.state in {"committed_verified", "committed_unverified"} and (
            commit.verification_status != "not_started" or commit.state == "committed_verified"
        ):
            from apps.live_control_server.services.threat_publication_commit_store import (
                ThreatPublicationCommitStorageError,
            )

            raise ThreatPublicationCommitStorageError(
                "verification save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(commit_svc, "_save_commit", side_effect=flaky_save):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=world_root,
            merge_fn=merge_fn,
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert merge_calls["n"] == 2
    assert outcome.merge_calls == 2
    assert saved_unverified["record"] is not None
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.committed_revision_id == revision_id
    assert outcome.response.commit.verification_status == "not_started"
    assert outcome.response.retry_allowed is False
    assert "verification could not persist" in (outcome.response.message or "")


def test_legacy_zero_match_persists_uncommitted(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    recon_ids = list(proposal.accepted_assertion_ids)
    seal_ids = _historical_seal_ids(proposal)
    assert seal_ids != recon_ids

    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    _v, contribution = resolve_merged_contribution_from_package(
        review_package=proposal.sealed_proposal,
        confirming_principal=proposal.created_by,
        world_id_hint="world_1",
        root=world_root,
        expected_parent_revision_id=proposal.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    by_id = {item.assertion_id: item for item in contribution.accepted_assertions}
    seal_ordered = contribution.model_copy(
        update={"accepted_assertions": [by_id[i] for i in seal_ids]}
    )
    seal_digest = kernel.compute_contribution_source_payload_sha256(seal_ordered)

    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    legacy_proposal = _mutate_proposal_accepted_ids(
        tmp_path, draft.draft_id, op_id, proposal_id, seal_ids
    )
    legacy_record = commit_svc._with_updated(
        record,
        accepted_assertion_ids=list(legacy_proposal.accepted_assertion_ids),
        expected_contribution_source_payload_sha256=seal_digest,
        proposal_request_digest=legacy_proposal.request_digest,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, legacy_record)

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
        lookup_fn=lambda *_a, **_k: tuple(),
    )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_uncommitted"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "uncommitted"
    assert "new publication operation is required" in (outcome.response.message or "")
    assert "supersede" not in (outcome.response.message or "").casefold()

    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "uncommitted"


def test_zero_match_selected_target_drift_persists_uncommitted(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    drifted = resolution.selected_target.model_copy(
        update={"label": "Completely Different Threat"}
    )
    identity = _stub_identity_outcome(
        resolution,
        result_label="publication_identity_connected_existing",
        selected_target=drifted,
    )

    with patch.object(commit_svc, "read_identity_resolution", return_value=identity):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_uncommitted"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "uncommitted"
    assert "selected_target mismatch" in (outcome.response.message or "")
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "uncommitted"


def test_legacy_c2a_trust_requires_historical_source_digest(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    seal_ids = _historical_seal_ids(proposal)
    request = _confirm_request(proposal)
    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    historical_digest = commit_svc._historical_contribution_source_digest(
        contribution, proposal.sealed_proposal
    )
    assert historical_digest is not None
    assert historical_digest != record.expected_contribution_source_payload_sha256

    legacy_proposal = _mutate_proposal_accepted_ids(
        tmp_path, draft.draft_id, op_id, proposal_id, seal_ids
    )
    # Corrupt persisted digest: recognized legacy order, wrong payload digest.
    legacy_record = commit_svc._with_updated(
        record,
        accepted_assertion_ids=list(legacy_proposal.accepted_assertion_ids),
        expected_contribution_source_payload_sha256=(
            "0" * len(record.expected_contribution_source_payload_sha256)
        ),
        proposal_request_digest=legacy_proposal.request_digest,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, legacy_record)

    lookup_calls = {"n": 0}

    def lookup_fn(*_a, **_k):
        lookup_calls["n"] += 1
        return tuple()

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
        lookup_fn=lookup_fn,
    )

    assert lookup_calls["n"] == 0
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert "contribution_source_digest_mismatch" in (outcome.response.message or "")
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"


def _c2a_connect_verifiable_setup(tmp_path: Path, monkeypatch, *, revision_id: str):
    """Committing connect_existing record plus complete otherwise-verifiable graph."""
    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)
    store, binding, _binding_id = _connect_verification_store(
        proposal, world_root, selected_target=resolution.selected_target
    )
    unverified_for_projection = commit_svc._with_updated(
        committing,
        state="committed_unverified",
        committed_revision_id=revision_id,
    )
    projection = _projection_for_verified_commit(
        record=unverified_for_projection,
        contribution=contribution,
        binding=binding,
        selected_target=resolution.selected_target,
    )
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    return (
        draft,
        op_id,
        proposal_id,
        proposal,
        request,
        world_root,
        committing,
        contribution,
        resolution,
        store,
        projection,
        manifest,
    )


def test_c2a_superseded_historical_identity_can_reach_verified(
    tmp_path: Path, monkeypatch
) -> None:
    revision_id = "rev:connect-c2a-superseded"
    (
        draft,
        op_id,
        proposal_id,
        _proposal,
        request,
        world_root,
        _committing,
        _contribution,
        resolution,
        store,
        projection,
        manifest,
    ) = _c2a_connect_verifiable_setup(tmp_path, monkeypatch, revision_id=revision_id)

    identity = _stub_identity_outcome(
        resolution,
        result_label="publication_identity_superseded",
        state="superseded",
        superseded_by_resolution_id="tres_superseder_aaaaaaaaaaaaaaaa",
    )

    class _Rebuild:
        diagnostics = ["rebuild_equivalent_to_pinned_revision"]

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=identity
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(
        commit_svc.kernel, "rebuild_from_contributions", return_value=_Rebuild()
    ), patch.object(
        commit_svc.kernel, "project_world_graph", return_value=projection
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_verified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_verified"
    assert outcome.response.retry_allowed is False


def test_c2a_changed_request_digest_cannot_reach_verified(
    tmp_path: Path, monkeypatch
) -> None:
    revision_id = "rev:connect-c2a-request-digest"
    (
        draft,
        op_id,
        proposal_id,
        _proposal,
        request,
        world_root,
        _committing,
        _contribution,
        resolution,
        store,
        projection,
        manifest,
    ) = _c2a_connect_verifiable_setup(tmp_path, monkeypatch, revision_id=revision_id)

    identity = _stub_identity_outcome(
        resolution,
        result_label="publication_identity_connected_existing",
        request_digest="sha256:" + ("a" * 64),
    )

    class _Rebuild:
        diagnostics = ["rebuild_equivalent_to_pinned_revision"]

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=identity
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(
        commit_svc.kernel, "rebuild_from_contributions", return_value=_Rebuild()
    ), patch.object(
        commit_svc.kernel, "project_world_graph", return_value=projection
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert "request_digest" in (outcome.response.message or "")


def test_c2a_changed_candidate_set_digest_cannot_reach_verified(
    tmp_path: Path, monkeypatch
) -> None:
    revision_id = "rev:connect-c2a-candidate-set"
    (
        draft,
        op_id,
        proposal_id,
        _proposal,
        request,
        world_root,
        _committing,
        _contribution,
        resolution,
        store,
        projection,
        manifest,
    ) = _c2a_connect_verifiable_setup(tmp_path, monkeypatch, revision_id=revision_id)

    identity = _stub_identity_outcome(
        resolution,
        result_label="publication_identity_connected_existing",
        candidate_set_digest="sha256:" + ("b" * 64),
    )

    class _Rebuild:
        diagnostics = ["rebuild_equivalent_to_pinned_revision"]

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=identity
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ), patch.object(
        commit_svc.kernel, "rebuild_from_contributions", return_value=_Rebuild()
    ), patch.object(
        commit_svc.kernel, "project_world_graph", return_value=projection
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert "candidate_set_digest" in (outcome.response.message or "")


def test_retry_identity_storage_unavailable_keeps_committing(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_storage_unavailable",
            resolution=None,
            predecessor_usable=None,
            message="identity store unavailable",
        ),
        created=False,
    )
    with patch.object(commit_svc, "read_identity_resolution", return_value=unavailable):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.retry_allowed is True
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"


def test_retry_publication_storage_unavailable_keeps_committing(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    refresh = _stub_publication_refresh(
        result_label="publication_storage_unavailable",
        operation=None,
    )
    with patch.object(commit_svc, "refresh_publication_operation", return_value=refresh):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.retry_allowed is True
    assert "publication dependency unavailable" in (outcome.response.message or "")
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"


def test_c2a_committed_receipt_save_failure_returns_storage_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services.threat_publication_commit_store import (
        ThreatPublicationCommitStorageError,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    revision_id = "rev:c2a-receipt-save-fail"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _recovery_store(proposal, world_root)
    real_save = commit_svc._save_commit

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if (
            commit.state == "committed_unverified"
            and commit.verification_status == "not_started"
        ):
            raise ThreatPublicationCommitStorageError(
                "committed receipt save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(
        commit_svc, "_save_commit", side_effect=flaky_save
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.committed_revision_id is None
    assert outcome.response.commit.merge_attempt_count == 2
    assert outcome.response.retry_allowed is False
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 2
    assert ledger.commit.committed_revision_id is None


def test_retry_committed_receipt_save_failure_returns_storage_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services.threat_publication_commit_store import (
        ThreatPublicationCommitStorageError,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    revision_id = "rev:retry-receipt-save-fail"
    merge_calls = {"n": 0}
    real_save = commit_svc._save_commit

    def merge_fn(*_args, **_kwargs):
        merge_calls["n"] += 1
        if merge_calls["n"] == 1:
            raise RuntimeError("first attempt uncertain")
        return _merge_success_result(proposal, revision_id=revision_id)

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if (
            commit.state == "committed_unverified"
            and commit.verification_status == "not_started"
            and commit.merge_attempt_count == 2
        ):
            raise ThreatPublicationCommitStorageError(
                "committed receipt save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(commit_svc, "_save_commit", side_effect=flaky_save):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=world_root,
            merge_fn=merge_fn,
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert merge_calls["n"] == 2
    assert outcome.merge_calls == 2
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.merge_attempt_count == 2
    assert outcome.response.commit.committed_revision_id is None
    assert outcome.response.retry_allowed is False
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 2


def _legacy_committing_fixture(tmp_path: Path, monkeypatch):
    """Persist a recognized legacy-order committing claim for recovery classification tests."""
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    recon_ids = list(proposal.accepted_assertion_ids)
    seal_ids = _historical_seal_ids(proposal)
    assert seal_ids != recon_ids

    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    _v, contribution = resolve_merged_contribution_from_package(
        review_package=proposal.sealed_proposal,
        confirming_principal=proposal.created_by,
        world_id_hint="world_1",
        root=world_root,
        expected_parent_revision_id=proposal.expected_parent_revision_id,
        assertion_ids=None,
        verify_source=False,
    )
    by_id = {item.assertion_id: item for item in contribution.accepted_assertions}
    seal_ordered = contribution.model_copy(
        update={"accepted_assertions": [by_id[i] for i in seal_ids]}
    )
    seal_digest = kernel.compute_contribution_source_payload_sha256(seal_ordered)

    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    legacy_proposal = _mutate_proposal_accepted_ids(
        tmp_path, draft.draft_id, op_id, proposal_id, seal_ids
    )
    legacy_record = commit_svc._with_updated(
        record,
        accepted_assertion_ids=list(legacy_proposal.accepted_assertion_ids),
        expected_contribution_source_payload_sha256=seal_digest,
        proposal_request_digest=legacy_proposal.request_digest,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, legacy_record)
    return (
        draft,
        op_id,
        proposal_id,
        legacy_proposal,
        request,
        world_root,
        legacy_record,
        seal_digest,
    )


def test_legacy_c2a_oserror_keeps_committing(tmp_path: Path, monkeypatch) -> None:
    (
        draft,
        op_id,
        proposal_id,
        _legacy_proposal,
        request,
        world_root,
        _legacy_record,
        _seal_digest,
    ) = _legacy_committing_fixture(tmp_path, monkeypatch)

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
        lookup_fn=lambda *_a, **_k: (_ for _ in ()).throw(OSError("c2a unavailable")),
    )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.merge_attempt_count == 1
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 1


def test_legacy_c2a_integrity_keeps_committing(tmp_path: Path, monkeypatch) -> None:
    (
        draft,
        op_id,
        proposal_id,
        _legacy_proposal,
        request,
        world_root,
        _legacy_record,
        _seal_digest,
    ) = _legacy_committing_fixture(tmp_path, monkeypatch)

    outcome = commit_svc.confirm_threat_publication(
        tmp_path,
        draft.draft_id,
        op_id,
        proposal_id,
        request,
        world_root=world_root,
        merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
        lookup_fn=lambda *_a, **_k: (_ for _ in ()).throw(
            WorldGraphIntegrityError("corrupt c2a authority")
        ),
    )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"


def test_legacy_c2a_receipt_save_failure_keeps_committing(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services.threat_publication_commit_store import (
        ThreatPublicationCommitStorageError,
    )

    (
        draft,
        op_id,
        proposal_id,
        legacy_proposal,
        request,
        world_root,
        _legacy_record,
        seal_digest,
    ) = _legacy_committing_fixture(tmp_path, monkeypatch)

    revision_id = "rev:legacy-receipt-save-fail"
    manifest = _recovery_manifest(legacy_proposal, revision_id=revision_id)
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH).model_copy(
        update={
            "nodes": {},
            "edges": {},
            "aliases": {},
            "adjacency": {},
            "evidence": {},
            "source_artifacts": {},
            "contribution_source_payload_sha256": {
                legacy_proposal.expected_contribution_id: seal_digest,
            },
            "contribution_replay_manifest": [
                ContributionReplayManifestEntry(
                    contribution_id=legacy_proposal.expected_contribution_id,
                    status="active",
                    source_payload_sha256=seal_digest,
                )
            ],
        }
    )
    real_save = commit_svc._save_commit

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if (
            commit.state == "committed_unverified"
            and commit.verification_status == "not_started"
        ):
            raise ThreatPublicationCommitStorageError(
                "committed receipt save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(
        commit_svc, "_save_commit", side_effect=flaky_save
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.merge_attempt_count == 2
    assert outcome.response.retry_allowed is False
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 2


def test_retry_reconstruction_oserror_keeps_committing(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    identity = _stub_identity_outcome(
        type(
            "Resolution",
            (),
            {
                "resolution_id": proposal.resolution_id,
                "draft_id": draft.draft_id,
                "operation_id": op_id,
                "source_digest": proposal.source_digest,
                "request_digest": proposal.resolution_request_digest,
                "candidate_set_digest": proposal.candidate_set_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "decision": proposal.decision,
                "selected_target": None,
                "created_node_id": proposal.threat_node_id,
                "state": "active",
            },
        )(),
        result_label="publication_identity_created_new",
    )
    refresh = _stub_publication_refresh(
        result_label="publication_ready",
        operation=type(
            "Operation",
            (),
            {
                "source_digest": proposal.source_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
            },
        )(),
    )

    real_resolve = commit_svc.resolve_merged_contribution_from_package
    resolve_calls = {"n": 0}

    def resolve_once(*args, **kwargs):
        resolve_calls["n"] += 1
        if resolve_calls["n"] == 1:
            return real_resolve(*args, **kwargs)
        raise OSError("reconstruction unavailable")

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=identity
    ), patch.object(
        commit_svc, "refresh_publication_operation", return_value=refresh
    ), patch.object(
        commit_svc,
        "resolve_merged_contribution_from_package",
        side_effect=resolve_once,
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert resolve_calls["n"] >= 2
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.retry_allowed is True
    assert "reconstruction unavailable" in (outcome.response.message or "")
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 1


def test_retry_attempt2_intent_save_failure_returns_storage_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services.threat_publication_commit_store import (
        ThreatPublicationCommitStorageError,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, contribution, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None and contribution is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    identity = _stub_identity_outcome(
        type(
            "Resolution",
            (),
            {
                "resolution_id": proposal.resolution_id,
                "draft_id": draft.draft_id,
                "operation_id": op_id,
                "source_digest": proposal.source_digest,
                "request_digest": proposal.resolution_request_digest,
                "candidate_set_digest": proposal.candidate_set_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
                "decision": proposal.decision,
                "selected_target": None,
                "created_node_id": proposal.threat_node_id,
                "state": "active",
            },
        )(),
        result_label="publication_identity_created_new",
    )
    refresh = _stub_publication_refresh(
        result_label="publication_ready",
        operation=type(
            "Operation",
            (),
            {
                "source_digest": proposal.source_digest,
                "expected_parent_revision_id": proposal.expected_parent_revision_id,
            },
        )(),
    )
    real_save = commit_svc._save_commit

    def flaky_save(root, commit: ThreatPublicationCommitV1):
        if commit.state == "committing" and commit.merge_attempt_count == 2:
            raise ThreatPublicationCommitStorageError(
                "attempt-two intent save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(
        commit_svc, "read_identity_resolution", return_value=identity
    ), patch.object(
        commit_svc, "refresh_publication_operation", return_value=refresh
    ), patch.object(
        commit_svc, "_save_commit", side_effect=flaky_save
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.merge_attempt_count == 1
    assert "attempt-two intent save failed" in (outcome.response.message or "")
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 1


# --- SBW09c2b publication-boundary hardening F1-F5 regression tests ---


def test_admission_identity_storage_unavailable_no_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_storage_unavailable",
            resolution=None,
            predecessor_usable=None,
            message="identity store unavailable",
        ),
        created=False,
    )
    merge_calls = {"n": 0}

    def merge_fn(*_a, **_k):
        merge_calls["n"] += 1
        return _merge_success_result(proposal)

    with patch.object(commit_svc, "read_identity_resolution", return_value=unavailable):
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

    assert outcome.merge_calls == 0
    assert merge_calls["n"] == 0
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)


def test_admission_identity_integrity_failure_no_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    integrity = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_integrity_failure",
            resolution=None,
            predecessor_usable=None,
            message="identity ledger corrupt",
        ),
        created=False,
    )

    with patch.object(commit_svc, "read_identity_resolution", return_value=integrity):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=tmp_path / "graph",
            merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)


def test_admission_identity_not_found_is_conflict(tmp_path: Path, monkeypatch) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    missing = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_not_found",
            resolution=None,
            predecessor_usable=None,
            message="identity resolution not found",
        ),
        created=False,
    )

    with patch.object(commit_svc, "read_identity_resolution", return_value=missing):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=tmp_path / "graph",
            merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_resolution_not_active"
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)


def test_admission_publication_storage_unavailable_no_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    refresh = _stub_publication_refresh(
        result_label="publication_storage_unavailable",
        operation=None,
    )

    with patch.object(commit_svc, "refresh_publication_operation", return_value=refresh):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            _confirm_request(proposal),
            world_root=tmp_path / "graph",
            merge_fn=lambda *_a, **_k: _merge_success_result(proposal),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    _assert_no_commit_storage(tmp_path, draft.draft_id, op_id)


def test_zero_match_identity_not_found_persists_uncommitted(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    missing = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_not_found",
            resolution=None,
            predecessor_usable=None,
            message="identity resolution not found",
        ),
        created=False,
    )

    with patch.object(commit_svc, "read_identity_resolution", return_value=missing):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_uncommitted"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "uncommitted"
    assert outcome.response.retry_allowed is False
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "uncommitted"


def test_zero_match_operation_stale_persists_uncommitted(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    refresh = _stub_publication_refresh(result_label="publication_stale", operation=None)

    with patch.object(commit_svc, "refresh_publication_operation", return_value=refresh):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_uncommitted"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "uncommitted"
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "uncommitted"


def test_zero_match_identity_storage_unavailable_keeps_committing(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.models.threat_publication_identity import (
        ThreatPublicationIdentityResponseV1,
    )
    from apps.live_control_server.services.threat_publication_identity import (
        IdentityResolutionOutcome,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    unavailable = IdentityResolutionOutcome(
        ThreatPublicationIdentityResponseV1(
            draft_id=draft.draft_id,
            operation_id=op_id,
            result_label="publication_identity_storage_unavailable",
            resolution=None,
            predecessor_usable=None,
            message="identity store unavailable",
        ),
        created=False,
    )

    with patch.object(commit_svc, "read_identity_resolution", return_value=unavailable):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: tuple(),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_recovery_pending"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.retry_allowed is True
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"
    assert ledger.commit.merge_attempt_count == 1


def test_committing_reconstruction_oserror_still_runs_c2a(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    lookup_calls = {"n": 0}
    revision_id = "rev:oserror-c2a-recover"

    def lookup_fn(*_a, **_k):
        lookup_calls["n"] += 1
        return (_recovery_manifest(proposal, revision_id=revision_id),)

    store = _recovery_store(proposal, world_root)

    with patch.object(
        commit_svc,
        "resolve_merged_contribution_from_package",
        side_effect=OSError("reconstruction unavailable"),
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lookup_fn,
        )

    assert lookup_calls["n"] == 1
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.committed_revision_id == revision_id


def test_committing_reconstruction_integrity_still_runs_c2a(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    lookup_calls = {"n": 0}
    revision_id = "rev:recon-integrity-c2a-recover"

    def lookup_fn(*_a, **_k):
        lookup_calls["n"] += 1
        return (_recovery_manifest(proposal, revision_id=revision_id),)

    store = _recovery_store(proposal, world_root)

    with patch.object(
        commit_svc,
        "resolve_merged_contribution_from_package",
        side_effect=WorldGraphIntegrityError("corrupt contribution package"),
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lookup_fn,
        )

    assert lookup_calls["n"] == 1
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_committed_unverified"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committed_unverified"
    assert outcome.response.commit.committed_revision_id == revision_id
    assert outcome.response.retry_allowed is False
    assert "reconstruction integrity" in (outcome.response.message or "")


def test_committing_reconstruction_integrity_zero_match_blocks_retry(
    tmp_path: Path, monkeypatch
) -> None:
    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)

    lookup_calls = {"n": 0}

    def lookup_fn(*_a, **_k):
        lookup_calls["n"] += 1
        return tuple()

    with patch.object(
        commit_svc,
        "resolve_merged_contribution_from_package",
        side_effect=WorldGraphIntegrityError("corrupt contribution package"),
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lookup_fn,
        )

    assert lookup_calls["n"] == 1
    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_integrity_failure"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.retry_allowed is False
    ledger = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert ledger is not None
    assert ledger.commit.state == "committing"


def test_connect_existing_threat_node_assertion_rejected(
    tmp_path: Path, monkeypatch
) -> None:
    from graph_memory.kernel.contribution_models import GraphContributionAssertion

    draft, op_id, _rid, proposal_id, proposal, _parent, resolution = _pipeline_connect_existing(
        tmp_path, monkeypatch
    )
    assert resolution.selected_target is not None
    world_root = tmp_path / "graph"
    contribution = _contribution_from_proposal(proposal, world_root)
    adversarial = contribution.model_copy(
        update={
            "accepted_assertions": [
                *contribution.accepted_assertions,
                GraphContributionAssertion.model_validate(
                    {
                        "assertion_id": "adv:threat-node-rewrite",
                        "assertion_kind": "node",
                        "subject_node_id": proposal.threat_node_id,
                        "label": "Rewritten Threat",
                        "value": {"kind": "threat", "role": "foe"},
                        "acceptance_state": "accepted",
                        "contribution_id": proposal.expected_contribution_id,
                    }
                ),
            ]
        }
    )
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=_confirm_request(proposal),
    )
    assert early is None and record is not None
    store, _binding, _binding_id = _connect_verification_store(
        proposal, world_root, selected_target=resolution.selected_target
    )
    codes = commit_svc._verify_connect_existing_constraints(
        store=store,
        contribution=adversarial,
        record=record,
    )
    assert "connect_existing_threat_rewrite" in codes


def test_double_receipt_save_failure_returns_durable_prior(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services.threat_publication_commit_store import (
        ThreatPublicationCommitStorageError,
    )

    draft, op_id, _rid, proposal_id, proposal, _parent = _pipeline_create_new(
        tmp_path, monkeypatch
    )
    world_root = tmp_path / "graph"
    request = _confirm_request(proposal)
    record, early, _c, _p = commit_svc._admit_and_build_record(
        root=tmp_path,
        world_root=world_root,
        draft_id=draft.draft_id,
        operation_id=op_id,
        proposal_id=proposal_id,
        request=request,
    )
    assert early is None and record is not None
    committing = commit_svc._with_updated(
        record,
        state="committing",
        merge_attempt_count=1,
        committed_revision_id=None,
    )
    commit_svc._save_commit(tmp_path, committing)
    durable_before = _commit_ledger_bytes(tmp_path, draft.draft_id, op_id)

    revision_id = "rev:double-receipt-save-fail"
    manifest = _recovery_manifest(proposal, revision_id=revision_id)
    store = _recovery_store(proposal, world_root)
    real_save = commit_svc._save_commit

    def always_fail_save(root, commit: ThreatPublicationCommitV1):
        if commit.state == "committed_unverified" or (
            commit.state == "committing" and commit.merge_attempt_count == 2
        ):
            raise ThreatPublicationCommitStorageError(
                "receipt save failed", kind="unavailable"
            )
        return real_save(root, commit)

    with patch.object(
        commit_svc, "_save_commit", side_effect=always_fail_save
    ), patch.object(
        commit_svc.kernel, "load_world_graph_revision_with_integrity", return_value=store
    ):
        outcome = commit_svc.confirm_threat_publication(
            tmp_path,
            draft.draft_id,
            op_id,
            proposal_id,
            request,
            world_root=world_root,
            merge_fn=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no merge")),
            lookup_fn=lambda *_a, **_k: (manifest,),
        )

    assert outcome.merge_calls == 0
    assert outcome.response.result_label == "publication_commit_storage_unavailable"
    assert outcome.response.commit is not None
    assert outcome.response.commit.state == "committing"
    assert outcome.response.commit.merge_attempt_count == 1
    assert outcome.response.commit.committed_revision_id is None
    assert outcome.response.retry_allowed is False
    assert _commit_ledger_bytes(tmp_path, draft.draft_id, op_id) == durable_before
    reloaded = load_threat_publication_commit_ledger_unlocked(
        tmp_path, draft.draft_id, op_id
    )
    assert reloaded is not None
    assert reloaded.commit.model_dump(mode="json") == outcome.response.commit.model_dump(
        mode="json"
    )
