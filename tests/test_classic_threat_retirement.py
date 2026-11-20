"""Mounted classic publication retirement and immutable recorded history."""
from importlib import import_module
from uuid import uuid4

import pytest

from tests.test_threat_publication_identity_routes import (
    _authorized_client, _begin, _mechanics_saved_draft,
)
from tests.test_threat_publication_commit_models import _commit
from tests.test_threat_publication_proposal_models import _proposal
from apps.live_control_server.models.threat_publication_commit import ThreatPublicationCommitLedgerV1
from apps.live_control_server.models.threat_publication_identity import MATCHING_PROFILE_V1
from apps.live_control_server.models.threat_publication_proposal import (
    ThreatPublicationProposalLedgerV1, PrepareThreatPublicationProposalRequestV1, prepare_request_digest,
)
from apps.live_control_server.services import threat_publication_commits as commits
from apps.live_control_server.services import threat_publication_commit_store as commit_store
from apps.live_control_server.services import threat_publication_proposals as proposals
from apps.live_control_server.services import threat_publication_operations as operations

ROUTES = [import_module("apps.live_control_server.routes.threat_publication" + suffix)
          for suffix in ("", "_identity", "_proposals", "_commits")]


def _requests(draft, operation, resolution, proposal, commit):
    base = f"/api/live/threat-drafts/{draft}/publication-operations"
    op = f"{base}/{operation}"
    return [
        (base, dict(operation_id=operation, expected_draft_version=1,
                    expected_parent_revision_id="rev:parent", actor="gm")),
        (op + "/refresh", {}),
        (op + "/cancel", dict(actor="gm")),
        (op + "/retry", dict(new_operation_id=str(uuid4()),
                              expected_parent_revision_id="rev:parent", actor="gm")),
        (op + "/identity-candidates/prepare", {}),
        (op + "/identity-resolutions", dict(
            resolution_id=resolution, matching_profile=MATCHING_PROFILE_V1,
            candidate_query="test", candidate_set_digest="sha256:" + "a" * 64,
            decision="refuse", rejected_candidate_node_ids=[], actor="gm", reason="Retained refusal")),
        (op + f"/identity-resolutions/{resolution}/proposals", dict(proposal_id=proposal, actor="gm")),
        (op + f"/proposals/{proposal}/commits", dict(
            commit_id=commit, sealed_proposal_digest="sha256:" + "a" * 64,
            expected_parent_revision_id="rev:parent", actor="gm")),
    ]


def _bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _forbid(*args, **kwargs):
    pytest.fail("Retired publication accessed mutable storage or graph authority")


def _forbid_writers(monkeypatch):
    for route in ROUTES:
        monkeypatch.setattr(route, "repo_root", _forbid)
        monkeypatch.setattr(route, "statblock_data_root", _forbid)
    for module_name, names in [
        ("threat_publication_operations", ("begin_publication_operation", "refresh_publication_operation",
          "cancel_publication_operation", "retry_publication_operation")),
        ("threat_publication_identity", ("prepare_identity_candidates", "decide_identity_resolution")),
        ("threat_publication_proposals", ("prepare_threat_publication_proposal",)),
        ("threat_publication_commits", ("confirm_threat_publication",)),
    ]:
        module = import_module("apps.live_control_server.services." + module_name)
        for name in names:
            monkeypatch.setattr(module, name, _forbid)
        if hasattr(module, "get_world_graph_authority"):
            monkeypatch.setattr(module, "get_world_graph_authority", _forbid)


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize("retained_uncertainty", [False, True])
def test_every_mounted_mutation_is_gone_before_storage_or_authority(
    tmp_path, monkeypatch, index, retained_uncertainty,
):
    draft, operation, resolution, proposal, commit = [str(uuid4()) for _ in range(5)]
    if retained_uncertainty:
        record = _commit(draft_id=draft, operation_id=operation, proposal_id=proposal, commit_id=commit)
        commit_store.save_threat_publication_commit_ledger_unlocked(tmp_path,
            ThreatPublicationCommitLedgerV1(draft_id=draft, operation_id=operation, commit=record))
    before = _bytes(tmp_path)
    client = _authorized_client(monkeypatch)
    _forbid_writers(monkeypatch)
    path, body = _requests(draft, operation, resolution, proposal, commit)[index]
    response = client.post(path, json=body)
    assert response.status_code == 410, response.text
    assert response.json() == {"detail": "Classic Threat publication is retired; retained history is read-only."}
    assert _bytes(tmp_path) == before


def test_actual_registered_classic_post_set_is_fully_accounted_for(monkeypatch):
    app = _authorized_client(monkeypatch).app
    paths = {route.path for route in app.routes if "POST" in getattr(route, "methods", ())
             and "/publication-operations" in getattr(route, "path", "")}
    assert paths == {
        "/api/live/threat-drafts/{draft_id}/publication-operations",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/refresh",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/cancel",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/retry",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-resolutions/{resolution_id}/proposals",
        "/api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/proposals/{proposal_id}/commits",
    }


@pytest.mark.parametrize("state", ["committing", "uncommitted", "ambiguous", "committed_unverified", "committed_verified"])
def test_commit_get_preserves_recorded_state_and_bytes_but_never_allows_retry(tmp_path, monkeypatch, state):
    committed = state.startswith("committed_")
    record = _commit(state=state, committed_revision_id="rev:old" if committed else None,
                     verification_status="passed" if state == "committed_verified" else "not_started")
    ledger = ThreatPublicationCommitLedgerV1(draft_id=record.draft_id, operation_id=record.operation_id, commit=record)
    commit_store.save_threat_publication_commit_ledger_unlocked(tmp_path, ledger)
    path = commit_store._ledger_path(tmp_path, record.draft_id, record.operation_id)
    before = path.read_bytes()
    route = ROUTES[3]
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(commits, "get_world_graph_authority", _forbid)
    response = _authorized_client(monkeypatch).get(
        f"/api/live/threat-drafts/{record.draft_id}/publication-operations/{record.operation_id}/commits/{record.commit_id}")
    expected = {
        "committing": (503, "publication_commit_recovery_pending"),
        "uncommitted": (409, "publication_commit_uncommitted"),
        "ambiguous": (409, "publication_commit_outcome_ambiguous"),
        "committed_unverified": (200, "publication_commit_committed_unverified"),
        "committed_verified": (200, "publication_commit_verified"),
    }[state]
    assert response.status_code == expected[0], response.text
    body = response.json()
    assert body["result_label"] == expected[1]
    assert body["commit_admitted"] is True
    assert body["commit"] == record.model_dump(mode="json", by_alias=True)
    assert body["retry_allowed"] is False
    assert path.read_bytes() == before


@pytest.mark.parametrize("failure", ["missing", "corrupt", "unavailable"])
def test_commit_get_errors_never_authorize_retry_or_rewrite_history(tmp_path, monkeypatch, failure):
    record = _commit()
    path = commit_store._ledger_path(tmp_path, record.draft_id, record.operation_id)
    if failure != "missing":
        commit_store.save_threat_publication_commit_ledger_unlocked(tmp_path,
            ThreatPublicationCommitLedgerV1(draft_id=record.draft_id, operation_id=record.operation_id, commit=record))
    if failure == "corrupt":
        path.write_text("corrupt retained fixture")
    if failure == "unavailable":
        def unavailable(*args, **kwargs):
            raise commit_store.ThreatPublicationCommitStorageError("fixture outage", kind="unavailable")
        monkeypatch.setattr(commits, "load_threat_publication_commit_ledger_unlocked", unavailable)
    before = path.read_bytes() if path.exists() else None
    monkeypatch.setattr(ROUTES[3], "repo_root", lambda: tmp_path)
    response = _authorized_client(monkeypatch).get(
        f"/api/live/threat-drafts/{record.draft_id}/publication-operations/{record.operation_id}/commits/{record.commit_id}")
    assert response.status_code == {"missing": 404, "corrupt": 500, "unavailable": 503}[failure]
    assert response.json()["retry_allowed"] is False
    assert response.json()["commit"] is None
    assert response.json()["commit_admitted"] is (False if failure == "missing" else None)
    assert response.json()["result_label"] == {
        "missing": "publication_commit_not_found", "corrupt": "publication_commit_integrity_failure",
        "unavailable": "publication_commit_storage_unavailable",
    }[failure]
    assert (path.read_bytes() if path.exists() else None) == before


def test_operation_get_uses_retained_snapshot_without_current_draft_or_head(tmp_path, monkeypatch):
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    operation = _begin(tmp_path, draft)
    path = operations._ledger_path(tmp_path, draft.draft_id)
    before = path.read_bytes()
    monkeypatch.setattr(ROUTES[0], "repo_root", lambda: tmp_path)
    monkeypatch.setattr(operations, "_read_graph_head", _forbid)
    monkeypatch.setattr(operations, "get_threat_draft", _forbid)
    response = _authorized_client(monkeypatch).get(
        f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{operation}")
    assert response.status_code == 200, response.text
    assert response.json()["operation"]["source_snapshot"]["draft_id"] == draft.draft_id
    assert path.read_bytes() == before


def test_proposal_get_reads_exact_retained_ledger_without_head_or_source(tmp_path, monkeypatch):
    proposal = _proposal()
    request = PrepareThreatPublicationProposalRequestV1(proposal_id=proposal.proposal_id, actor=proposal.created_by)
    proposal = proposal.model_copy(update={"request_digest": prepare_request_digest(
        proposal.draft_id, proposal.operation_id, proposal.resolution_id, request)})
    ledger = ThreatPublicationProposalLedgerV1(draft_id=proposal.draft_id, operation_id=proposal.operation_id,
        active_proposal_id=proposal.proposal_id, proposals=[proposal])
    proposals._save_ledger_unlocked(tmp_path, ledger)
    path = proposals._ledger_path(tmp_path, proposal.draft_id, proposal.operation_id)
    before = path.read_bytes()
    monkeypatch.setattr(ROUTES[2], "repo_root", lambda: tmp_path)
    monkeypatch.setattr(proposals, "get_world_graph_authority", _forbid)
    response = _authorized_client(monkeypatch).get(
        f"/api/live/threat-drafts/{proposal.draft_id}/publication-operations/{proposal.operation_id}/proposals/{proposal.proposal_id}")
    assert response.status_code == 200, response.text
    assert response.json()["proposal"] == proposal.model_dump(mode="json", by_alias=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize("index", range(8))
def test_invalid_route_identity_remains_422_before_retirement(monkeypatch, index):
    ids = [str(uuid4()) for _ in range(5)]
    ids[0] = "invalid!"
    client = _authorized_client(monkeypatch)
    _forbid_writers(monkeypatch)
    path, body = _requests(*ids)[index]
    assert client.post(path, json=body).status_code == 422


def test_body_validation_and_mounted_actor_denial_are_preserved(monkeypatch):
    ids = [str(uuid4()) for _ in range(5)]
    client = _authorized_client(monkeypatch)
    _forbid_writers(monkeypatch)
    for index in (0, 7):
        path, _ = _requests(*ids)[index]
        assert client.post(path, json={}).status_code == 422
    client.headers.pop("authorization")
    path, body = _requests(*ids)[4]
    assert client.post(path, json=body).status_code == 401


@pytest.mark.parametrize("family", ["operation", "identity", "proposal"])
def test_malformed_recorded_history_is_refused_without_repair(tmp_path, monkeypatch, family):
    from unittest.mock import patch
    from apps.live_control_server.services import threat_publication_identity as identity
    from tests.test_threat_publication_identity_routes import _seed_historical_identity, _projection, _node

    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    operation = _begin(tmp_path, draft)
    resolution = str(uuid4())
    base = f"/api/live/threat-drafts/{draft.draft_id}/publication-operations/{operation}"
    if family == "identity":
        with patch.object(identity, "project_world_graph", return_value=_projection(_node("threat:1", label="One"))):
            candidate = _seed_historical_identity(tmp_path, base + "/identity-candidates/prepare", json={}).json()["candidate_set"]
            _seed_historical_identity(tmp_path, base + "/identity-resolutions", json=dict(
                resolution_id=resolution, matching_profile=MATCHING_PROFILE_V1,
                candidate_query=candidate["candidate_query"], candidate_set_digest=candidate["candidate_set_digest"],
                decision="refuse", rejected_candidate_node_ids=[], actor="gm", reason="historical"))
        path = identity._ledger_path(tmp_path, draft.draft_id, operation)
        url = base + f"/identity-resolutions/{resolution}"
    elif family == "proposal":
        # The persisted malformed file is owned by this synthetic fixture.
        path = proposals._ledger_path(tmp_path, draft.draft_id, operation)
        url = base + f"/proposals/{uuid4()}"
    else:
        path = operations._ledger_path(tmp_path, draft.draft_id)
        url = base
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"schema": "foreign_or_incomplete_history"}')
    before = path.read_bytes()
    for route in ROUTES:
        monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(identity, "project_world_graph", _forbid)
    monkeypatch.setattr(operations, "get_threat_draft", _forbid)
    monkeypatch.setattr(operations, "_read_graph_head", _forbid)
    response = _authorized_client(monkeypatch).get(url)
    assert response.status_code == 500, response.text
    assert path.read_bytes() == before
