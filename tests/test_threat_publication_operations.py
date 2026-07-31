"""SBW09a: durable Threat publication-operation ledger — service + model tests."""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import apps.live_control_server.services.threat_publication_operations as svc
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
    RetryThreatPublicationOperationRequestV1,
    ThreatPublicationLedgerV1,
    ThreatPublicationOperationV1,
    ThreatPublicationSourceSnapshotV1,
    build_source_snapshot,
    source_digest_for_snapshot,
    validate_publication_operation_id,
)
from apps.live_control_server.services.threat_draft_store import (
    _draft_path,
    attach_accepted_mechanics_ref,
    create_threat_draft,
    get_threat_draft,
    update_threat_draft,
)

DEFAULT_DIGEST = "sha256:" + "a" * 64


class _FakeHead:
    def __init__(self, revision_id: str) -> None:
        self.head_revision_id = revision_id


def _mock_head(monkeypatch, revision_id: str) -> None:
    monkeypatch.setattr(
        svc.kernel, "open_world_graph_head", lambda root, world_id: _FakeHead(revision_id)
    )


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


def _accept_mechanics(tmp_path: Path, draft, *, locator: MechanicsLocatorV1 | None = None):
    locator = locator or _locator()
    ref = AcceptedMechanicsRefV1.from_locator(
        locator, accepted_from_draft_version=draft.version, accepted_at="2020-01-01T00:00:00Z"
    )
    return attach_accepted_mechanics_ref(
        tmp_path, draft_id=draft.draft_id, expected_version=draft.version, locator=ref
    )


def _mechanics_saved_draft(tmp_path: Path, monkeypatch, *, head: str = "rev:parent1"):
    draft = _create_draft(tmp_path)
    draft = _accept_mechanics(tmp_path, draft)
    _mock_head(monkeypatch, head)
    return draft


def _begin_request(**overrides: Any) -> BeginThreatPublicationOperationRequestV1:
    payload: dict[str, Any] = {
        "operation_id": str(uuid.uuid4()),
        "expected_draft_version": 1,
        "expected_parent_revision_id": "rev:parent1",
        "actor": "gm",
    }
    payload.update(overrides)
    return BeginThreatPublicationOperationRequestV1.model_validate(payload)


def _update_description(tmp_path: Path, draft, description: str):
    return update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description=description,
            threat_kind=draft.threat_kind,
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
        ),
    )


# ---------------------------------------------------------------------------
# Begin
# ---------------------------------------------------------------------------


def test_begin_rejects_parent_mismatch_without_record(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:actual")
    request = _begin_request(
        expected_draft_version=draft.version, expected_parent_revision_id="rev:wrong"
    )
    outcome = svc.begin_publication_operation(tmp_path, draft.draft_id, request)
    assert outcome.created is False
    assert outcome.response.result_label == "publication_parent_mismatch"
    assert outcome.response.operation is None

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert ledger.operations == []
    assert ledger.active_operation_id is None


def test_begin_rejects_non_mechanics_saved_draft_without_record(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _create_draft(tmp_path)
    assert draft.workflow_state == "drafting"
    _mock_head(monkeypatch, "rev:parent1")
    request = _begin_request(expected_draft_version=draft.version)
    outcome = svc.begin_publication_operation(tmp_path, draft.draft_id, request)
    assert outcome.created is False
    assert outcome.response.result_label == "publication_source_mismatch"

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert ledger.operations == []


def test_begin_exact_replay_does_not_resnapshot_current_state(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    request = _begin_request(expected_draft_version=draft.version)
    first = svc.begin_publication_operation(tmp_path, draft.draft_id, request)
    assert first.created is True

    # Draft and graph both drift after begin; exact replay must never re-read them.
    _update_description(tmp_path, draft, "changed after begin")
    _mock_head(monkeypatch, "rev:other")

    replay = svc.begin_publication_operation(tmp_path, draft.draft_id, request)
    assert replay.created is False
    assert replay.response.result_label == "publication_ready"
    assert replay.response.operation == first.response.operation
    assert replay.response.operation.source_snapshot.description == "A brutal enforcer."


def test_begin_same_id_changed_request_conflicts_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    op_id = str(uuid.uuid4())
    first = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(operation_id=op_id, expected_draft_version=draft.version)
    )
    assert first.created is True

    changed = svc.begin_publication_operation(
        tmp_path,
        draft.draft_id,
        _begin_request(operation_id=op_id, expected_draft_version=draft.version, actor="other-gm"),
    )
    assert changed.created is False
    assert changed.response.result_label == "publication_input_conflict"
    assert changed.response.operation is None

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert len(ledger.operations) == 1
    assert ledger.operations[0] == first.response.operation


def test_competing_begin_allows_one_active_operation(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    first = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    assert first.created is True

    second = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    assert second.created is False
    assert second.response.result_label == "publication_busy"

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert len(ledger.operations) == 1


def test_restart_reload_preserves_exact_snapshot_locator_parent_and_digests(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    request = _begin_request(expected_draft_version=draft.version)
    first = svc.begin_publication_operation(tmp_path, draft.draft_id, request)
    op_id = first.response.operation.operation_id

    reloaded = svc.read_publication_operation(tmp_path, draft.draft_id, op_id)
    assert reloaded.response.operation == first.response.operation
    assert (
        reloaded.response.operation.source_snapshot.accepted_mechanics_ref.to_mechanics_locator()
        == draft.accepted_mechanics_ref.to_mechanics_locator()
    )
    assert reloaded.response.operation.expected_parent_revision_id == "rev:parent1"
    assert reloaded.response.operation.source_digest == source_digest_for_snapshot(
        reloaded.response.operation.source_snapshot
    )


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


def test_refresh_marks_graph_parent_changed_without_rebasing(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id

    _mock_head(monkeypatch, "rev:parent2")
    refreshed = svc.refresh_publication_operation(tmp_path, draft.draft_id, op_id)
    assert refreshed.response.result_label == "publication_stale"
    assert "graph_parent_changed" in refreshed.response.operation.stale_reasons
    assert refreshed.response.operation.expected_parent_revision_id == "rev:parent1"
    assert refreshed.response.operation.source_snapshot == begin.response.operation.source_snapshot


def test_refresh_marks_source_drift_without_replacing_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id
    original_snapshot = begin.response.operation.source_snapshot

    _update_description(tmp_path, draft, "drifted description")

    refreshed = svc.refresh_publication_operation(tmp_path, draft.draft_id, op_id)
    assert refreshed.response.result_label == "publication_stale"
    reasons = set(refreshed.response.operation.stale_reasons)
    assert "draft_version_changed" in reasons
    assert "source_digest_changed" in reasons
    assert refreshed.response.operation.source_snapshot == original_snapshot
    assert refreshed.response.operation.source_digest == begin.response.operation.source_digest


def test_refresh_dependency_failure_leaves_ledger_byte_identical(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id

    ledger_path = svc._ledger_path(tmp_path, draft.draft_id)
    before_bytes = ledger_path.read_bytes()

    def _raise(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("graph store unavailable")

    monkeypatch.setattr(svc.kernel, "open_world_graph_head", _raise)

    refreshed = svc.refresh_publication_operation(tmp_path, draft.draft_id, op_id)
    assert refreshed.response.result_label == "publication_graph_unavailable"
    assert ledger_path.read_bytes() == before_bytes


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


def test_cancel_is_terminal_and_idempotent(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id

    cancel_req = CancelThreatPublicationOperationRequestV1(actor="gm", note="no longer needed")
    cancelled = svc.cancel_publication_operation(tmp_path, draft.draft_id, op_id, cancel_req)
    assert cancelled.response.result_label == "publication_cancelled"
    assert cancelled.response.operation.state == "cancelled"

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert ledger.active_operation_id is None

    replay = svc.cancel_publication_operation(tmp_path, draft.draft_id, op_id, cancel_req)
    assert replay.response.result_label == "publication_cancelled"
    assert replay.response.operation == cancelled.response.operation

    changed = svc.cancel_publication_operation(
        tmp_path, draft.draft_id, op_id, CancelThreatPublicationOperationRequestV1(actor="other-gm")
    )
    assert changed.response.result_label == "publication_input_conflict"

    # No uncancel via retry: cancelled is terminal, not stale.
    retry = svc.retry_publication_operation(
        tmp_path,
        draft.draft_id,
        op_id,
        RetryThreatPublicationOperationRequestV1(
            new_operation_id=str(uuid.uuid4()),
            expected_parent_revision_id="rev:parent1",
            actor="gm",
        ),
    )
    assert retry.response.result_label == "publication_invalid_state"


def test_cancel_of_superseded_operation_is_invalid_state(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    old_id = begin.response.operation.operation_id
    _mock_head(monkeypatch, "rev:parent2")
    svc.refresh_publication_operation(tmp_path, draft.draft_id, old_id)
    svc.retry_publication_operation(
        tmp_path,
        draft.draft_id,
        old_id,
        RetryThreatPublicationOperationRequestV1(
            new_operation_id=str(uuid.uuid4()),
            expected_parent_revision_id="rev:parent2",
            actor="gm",
        ),
    )

    result = svc.cancel_publication_operation(
        tmp_path, draft.draft_id, old_id, CancelThreatPublicationOperationRequestV1(actor="gm")
    )
    assert result.response.result_label == "publication_invalid_state"


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


def test_retry_atomically_supersedes_and_installs_one_active_operation(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    old_id = begin.response.operation.operation_id

    _mock_head(monkeypatch, "rev:parent2")
    refreshed = svc.refresh_publication_operation(tmp_path, draft.draft_id, old_id)
    assert refreshed.response.result_label == "publication_stale"

    retry_req = RetryThreatPublicationOperationRequestV1(
        new_operation_id=str(uuid.uuid4()), expected_parent_revision_id="rev:parent2", actor="gm"
    )
    retried = svc.retry_publication_operation(tmp_path, draft.draft_id, old_id, retry_req)
    assert retried.created is True
    assert retried.response.result_label == "publication_ready"
    new_id = retried.response.operation.operation_id

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert ledger.active_operation_id == new_id
    by_id = {op.operation_id: op for op in ledger.operations}
    assert by_id[old_id].state == "superseded"
    assert by_id[old_id].superseded_by_operation_id == new_id
    assert by_id[new_id].supersedes_operation_id == old_id
    assert by_id[new_id].source_digest == by_id[old_id].source_digest
    assert sum(1 for op in ledger.operations if op.state in ("ready", "stale")) == 1

    replay = svc.retry_publication_operation(tmp_path, draft.draft_id, old_id, retry_req)
    assert replay.created is False
    assert replay.response.operation.operation_id == new_id


def test_retry_source_drift_rejects_without_mutation(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    old_id = begin.response.operation.operation_id
    _mock_head(monkeypatch, "rev:parent2")
    svc.refresh_publication_operation(tmp_path, draft.draft_id, old_id)

    current = get_threat_draft(tmp_path, draft.draft_id)
    _update_description(tmp_path, current, "drifted again")

    before = svc._load_ledger_unlocked(tmp_path, draft.draft_id)

    retry_req = RetryThreatPublicationOperationRequestV1(
        new_operation_id=str(uuid.uuid4()), expected_parent_revision_id="rev:parent2", actor="gm"
    )
    result = svc.retry_publication_operation(tmp_path, draft.draft_id, old_id, retry_req)
    assert result.created is False
    assert result.response.result_label == "publication_source_mismatch"

    after = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert before == after


def test_retry_rejects_non_stale_active_operation(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id

    result = svc.retry_publication_operation(
        tmp_path,
        draft.draft_id,
        op_id,
        RetryThreatPublicationOperationRequestV1(
            new_operation_id=str(uuid.uuid4()),
            expected_parent_revision_id="rev:parent1",
            actor="gm",
        ),
    )
    assert result.response.result_label == "publication_invalid_state"


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_cancel_and_retry_have_one_coherent_winner(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id
    _mock_head(monkeypatch, "rev:parent2")
    svc.refresh_publication_operation(tmp_path, draft.draft_id, op_id)

    barrier = threading.Barrier(2)
    results: dict[str, str] = {}
    guard = threading.Lock()

    def cancel_worker() -> None:
        barrier.wait()
        outcome = svc.cancel_publication_operation(
            tmp_path, draft.draft_id, op_id, CancelThreatPublicationOperationRequestV1(actor="gm")
        )
        with guard:
            results["cancel"] = outcome.response.result_label

    def retry_worker() -> None:
        barrier.wait()
        outcome = svc.retry_publication_operation(
            tmp_path,
            draft.draft_id,
            op_id,
            RetryThreatPublicationOperationRequestV1(
                new_operation_id=str(uuid.uuid4()),
                expected_parent_revision_id="rev:parent2",
                actor="gm",
            ),
        )
        with guard:
            results["retry"] = outcome.response.result_label

    threads = [threading.Thread(target=cancel_worker), threading.Thread(target=retry_worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results["cancel"] in {"publication_cancelled", "publication_invalid_state"}
    assert results["retry"] in {"publication_ready", "publication_invalid_state"}
    # Exactly one of the two claimed the terminal transition; the loser sees a
    # coherent invalid-state conflict rather than a corrupted/duplicated record.
    assert not (
        results["cancel"] == "publication_cancelled" and results["retry"] == "publication_ready"
    )

    ledger = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    active_like = [op for op in ledger.operations if op.state in ("ready", "stale")]
    assert len(active_like) <= 1
    # Ledger remains internally coherent (re-validates without raising).
    ThreatPublicationLedgerV1.model_validate(ledger.model_dump(mode="json", by_alias=True))


# ---------------------------------------------------------------------------
# Failure / corruption
# ---------------------------------------------------------------------------


def test_atomic_write_failure_preserves_previous_ledger(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    assert begin.created is True
    op_id = begin.response.operation.operation_id

    ledger_path = svc._ledger_path(tmp_path, draft.draft_id)
    before_bytes = ledger_path.read_bytes()

    def _boom(_path: Path, _data: dict) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(svc, "write_json", _boom)

    result = svc.cancel_publication_operation(
        tmp_path, draft.draft_id, op_id, CancelThreatPublicationOperationRequestV1(actor="gm")
    )
    assert result.response.result_label == "publication_storage_unavailable"
    assert ledger_path.read_bytes() == before_bytes


def test_all_operations_leave_draft_graph_and_dungeonmind_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch, head="rev:parent1")
    draft_path = _draft_path(tmp_path, draft.draft_id)
    draft_bytes_before = draft_path.read_bytes()

    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id
    svc.read_publication_operation(tmp_path, draft.draft_id, op_id)
    _mock_head(monkeypatch, "rev:parent2")
    svc.refresh_publication_operation(tmp_path, draft.draft_id, op_id)
    retried = svc.retry_publication_operation(
        tmp_path,
        draft.draft_id,
        op_id,
        RetryThreatPublicationOperationRequestV1(
            new_operation_id=str(uuid.uuid4()),
            expected_parent_revision_id="rev:parent2",
            actor="gm",
        ),
    )
    svc.cancel_publication_operation(
        tmp_path,
        draft.draft_id,
        retried.response.operation.operation_id,
        CancelThreatPublicationOperationRequestV1(actor="gm"),
    )

    assert draft_path.read_bytes() == draft_bytes_before
    # This module performs no DungeonMind calls: it never imports a client.
    module_globals = vars(svc)
    assert not any("dungeonmind_statblocks.client" in str(value) for value in module_globals.values())
    assert "DungeonMindStatblockV1Client" not in module_globals


def test_corrupt_ledger_fails_closed_without_rewrite(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    begin = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    op_id = begin.response.operation.operation_id

    ledger_path = svc._ledger_path(tmp_path, draft.draft_id)
    ledger_path.write_text("{not valid json", encoding="utf-8")
    corrupt_bytes = ledger_path.read_bytes()

    result = svc.read_publication_operation(tmp_path, draft.draft_id, op_id)
    assert result.response.result_label == "publication_integrity_failure"

    begin_attempt = svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    assert begin_attempt.response.result_label == "publication_integrity_failure"

    assert ledger_path.read_bytes() == corrupt_bytes


def test_corrupt_ledger_bad_schema_fails_closed(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    ledger_path = svc._ledger_path(tmp_path, draft.draft_id)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps({"schema": "wrong_schema"}), encoding="utf-8")

    result = svc.read_publication_operation(tmp_path, draft.draft_id, str(uuid.uuid4()))
    assert result.response.result_label == "publication_integrity_failure"


# ---------------------------------------------------------------------------
# Bounds / model-level tamper matrix
# ---------------------------------------------------------------------------


def test_history_full_rejects_without_mutation(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    for _ in range(svc.MAX_PUBLICATION_OPERATIONS_PER_DRAFT):
        op_id = str(uuid.uuid4())
        outcome = svc.begin_publication_operation(
            tmp_path,
            draft.draft_id,
            _begin_request(operation_id=op_id, expected_draft_version=draft.version),
        )
        assert outcome.created is True
        svc.cancel_publication_operation(
            tmp_path, draft.draft_id, op_id, CancelThreatPublicationOperationRequestV1(actor="gm")
        )

    ledger_before = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert len(ledger_before.operations) == svc.MAX_PUBLICATION_OPERATIONS_PER_DRAFT

    result = svc.begin_publication_operation(
        tmp_path,
        draft.draft_id,
        _begin_request(operation_id=str(uuid.uuid4()), expected_draft_version=draft.version),
    )
    assert result.response.result_label == "publication_history_full"
    ledger_after = svc._load_ledger_unlocked(tmp_path, draft.draft_id)
    assert ledger_after == ledger_before


def test_validate_publication_operation_id_accepts_uuid_and_pubop_form() -> None:
    uid = str(uuid.uuid4())
    assert validate_publication_operation_id(uid) == uid
    assert validate_publication_operation_id("pubop_abc-123.def") == "pubop_abc-123.def"
    with pytest.raises(ValueError):
        validate_publication_operation_id("../escape")
    with pytest.raises(ValueError):
        validate_publication_operation_id("not-an-id!")


def test_source_digest_tamper_detected_on_load() -> None:
    snapshot = ThreatPublicationSourceSnapshotV1(
        draft_id=str(uuid.uuid4()),
        draft_version=1,
        world_id="world_1",
        campaign_id="campaign_1",
        name="Ironhide Brute",
        description="A brutal enforcer.",
        threat_kind="creature",
        generation_intent=GenerationIntentV1(
            ruleset=RulesetRefV1(system="dnd5e", edition="2024")
        ),
        encounter_context={},
        graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev:aaa"),
        accepted_mechanics_ref=AcceptedMechanicsRefV1.from_locator(
            _locator(), accepted_from_draft_version=1, accepted_at="2020-01-01T00:00:00Z"
        ),
    )
    payload = {
        "operation_id": str(uuid.uuid4()),
        "request_digest": DEFAULT_DIGEST,
        "source_snapshot": snapshot.model_dump(mode="json", by_alias=True),
        "source_digest": DEFAULT_DIGEST,  # deliberately wrong
        "expected_parent_revision_id": "rev:parent1",
        "state": "ready",
        "stale_reasons": [],
        "created_by": "gm",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-01T00:00:00Z",
    }
    with pytest.raises(ValidationError, match="source_digest"):
        ThreatPublicationOperationV1.model_validate(payload)


def test_ledger_rejects_unbound_extra_field(tmp_path: Path, monkeypatch) -> None:
    draft = _mechanics_saved_draft(tmp_path, monkeypatch)
    svc.begin_publication_operation(
        tmp_path, draft.draft_id, _begin_request(expected_draft_version=draft.version)
    )
    payload = svc._load_ledger_unlocked(tmp_path, draft.draft_id).model_dump(
        mode="json", by_alias=True
    )
    payload["unexpected_field"] = "nope"
    with pytest.raises(ValidationError):
        ThreatPublicationLedgerV1.model_validate(payload)


def test_build_source_snapshot_requires_accepted_mechanics_ref(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    with pytest.raises(ValueError):
        build_source_snapshot(draft)
