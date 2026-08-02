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
    ordered = commit_svc._require_ordered_contribution(
        contribution, list(proposal.accepted_assertion_ids)
    )
    assert ordered is not None
    return ordered


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
    assert first.response.result_label == "publication_commit_recovery_pending"
    assert first.response.commit is not None
    assert first.response.commit.state == "committing"

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
    assertion_support = {
        assertion_id: {
            "assertion_id": assertion_id,
            "active_contribution_ids": [proposal.expected_contribution_id],
            "superseded_contribution_ids": [],
            "retracted_contribution_ids": [],
            "evidence_ref_ids": [],
            "source_artifact_ids": [],
            "support_state": "supported",
            "introduced_by_contribution_id": proposal.expected_contribution_id,
            "provenance_lineage_version": 1,
            "per_contribution_evidence_ref_ids": {},
            "per_contribution_source_artifact_ids": {},
        }
        for assertion_id in proposal.accepted_assertion_ids
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
