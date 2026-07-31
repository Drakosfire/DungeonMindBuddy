from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    PROVIDER_DUNGEONMIND,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptedMechanicsRefV1,
)
from apps.live_control_server.models.threat_statblock_publication import (
    PublicationArtifactRefV1,
    ThreatPublicationSourceSnapshotV1,
    ThreatStatblockPublicationOperationV1,
    claim_request_digest_for_begin,
    source_snapshot_digest_for,
)
from apps.live_control_server.models.threat_draft import (
    GraphContextSnapshotV1,
)
from apps.live_control_server.services.threat_statblock_publication_store import (
    MAX_PUBLICATION_OPERATION_RECORDS_PER_DRAFT,
    ThreatStatblockPublicationStoreError,
    atomic_claim_publication_operation,
    build_new_publication_operation,
    cas_transition_publication_cancelled,
    cas_transition_publication_stale,
    claim_publication_operation,
    get_publication_operation,
    publication_root,
)
from src.live_play.live_store import write_json


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _accepted_ref() -> AcceptedMechanicsRefV1:
    return AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_test01",
            revision_id="rev_test01",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64,
        ),
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
        accepted_from_candidate_id="cand_abc123",
    )


def _snapshot(*, draft_id: str | None = None) -> ThreatPublicationSourceSnapshotV1:
    return ThreatPublicationSourceSnapshotV1(
        source_draft_id=draft_id or str(uuid.uuid4()),
        source_draft_version=1,
        world_id="world_1",
        campaign_id="campaign_1",
        name="Test Threat",
        description="Desc",
        threat_kind="creature",
        intended_roles=["brute"],
        tags=["test"],
        graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_ctx"),
        accepted_mechanics_ref=_accepted_ref(),
    )


def _claim_digest(draft_id: str, operation_id: str) -> str:
    return claim_request_digest_for_begin(
        draft_id=draft_id,
        operation_id=operation_id,
        expected_draft_version=1,
        expected_parent_revision_id="rev:parent01",
    )


def _operation(
    *,
    draft_id: str,
    operation_id: str | None = None,
) -> ThreatStatblockPublicationOperationV1:
    op_id = operation_id or str(uuid.uuid4())
    snap = _snapshot(draft_id=draft_id)
    digest = _claim_digest(draft_id, op_id)
    return build_new_publication_operation(
        operation_id=op_id,
        claim_request_digest=digest,
        source_snapshot=snap,
        expected_parent_revision_id="rev:parent01",
        last_observed_head_revision_id="rev:parent01",
    )


def test_source_snapshot_digest_canonical() -> None:
    snap = _snapshot()
    first = source_snapshot_digest_for(snap)
    second = source_snapshot_digest_for(
        ThreatPublicationSourceSnapshotV1.model_validate(
            snap.model_dump(mode="json", by_alias=True)
        )
    )
    assert first == second
    assert first.startswith("sha256:")


def test_claim_request_digest_binds_identity() -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    first = _claim_digest(draft_id, op_id)
    second = _claim_digest(draft_id, op_id)
    changed = claim_request_digest_for_begin(
        draft_id=draft_id,
        operation_id=op_id,
        expected_draft_version=2,
        expected_parent_revision_id="rev:parent01",
    )
    assert first == second
    assert changed != first


def test_cancelled_record_rejects_commit_receipt_artifact() -> None:
    snap = _snapshot()
    digest = source_snapshot_digest_for(snap)
    receipt = PublicationArtifactRefV1(
        artifact_kind="graph_commit_receipt",
        artifact_id="receipt_1",
        artifact_schema="dmb_graph_commit_receipt_v1",
        artifact_digest="sha256:" + "b" * 64,
        storage_owner="graph_review",
    )
    with pytest.raises(ValidationError):
        ThreatStatblockPublicationOperationV1(
            operation_id=str(uuid.uuid4()),
            operation_version=1,
            claim_request_digest="sha256:" + "c" * 64,
            source_snapshot=snap,
            source_snapshot_digest=digest,
            world_id="world_1",
            campaign_id="campaign_1",
            expected_parent_revision_id="rev:parent01",
            last_observed_head_revision_id="rev:parent01",
            authority_state="cancelled",
            phase_artifacts=[receipt],
            created_at=_now(),
            updated_at=_now(),
        )


def test_store_round_trip_and_path_safety(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    outcome, written = atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        new_record=record,
    )
    assert outcome == "claimed"
    assert written is not None
    reloaded = get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id)
    assert reloaded == written
    assert reloaded.source_snapshot.accepted_mechanics_ref.statblock_id == "sb_test01"

    with pytest.raises(ThreatStatblockPublicationStoreError):
        get_publication_operation(tmp_path, draft_id="../evil", operation_id=op_id)


def test_corrupt_record_fails_closed(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        new_record=record,
    )
    path = publication_root(tmp_path) / draft_id / f"{op_id}.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id)
    assert exc.value.status_code == 500


def test_history_full_rejects_new_claim(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    for index in range(MAX_PUBLICATION_OPERATION_RECORDS_PER_DRAFT):
        op_id = f"pubop_{index:02d}"
        rec = _operation(draft_id=draft_id, operation_id=op_id)
        outcome, _ = atomic_claim_publication_operation(
            tmp_path,
            draft_id=draft_id,
            operation_id=op_id,
            claim_request_digest=rec.claim_request_digest,
            new_record=rec,
        )
        assert outcome == "claimed"
        cas_transition_publication_cancelled(
            tmp_path,
            draft_id=draft_id,
            operation_id=op_id,
            expected_operation_version=1,
        )

    overflow_id = "pubop_overflow"
    overflow = _operation(draft_id=draft_id, operation_id=overflow_id)
    outcome, written = atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=overflow_id,
        claim_request_digest=overflow.claim_request_digest,
        new_record=overflow,
    )
    assert outcome == "publication_history_full"
    assert written is None


def test_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        new_record=record,
    )
    path = publication_root(tmp_path) / draft_id / f"{op_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_snapshot_digest"] = "sha256:" + "d" * 64
    write_json(path, payload)
    with pytest.raises(ThreatStatblockPublicationStoreError):
        get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id)


def test_active_slot_blocks_second_operation(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    first_id = str(uuid.uuid4())
    first = _operation(draft_id=draft_id, operation_id=first_id)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=first_id,
        claim_request_digest=first.claim_request_digest,
        new_record=first,
    )
    second_id = str(uuid.uuid4())
    second = _operation(draft_id=draft_id, operation_id=second_id)
    outcome, _ = atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=second_id,
        claim_request_digest=second.claim_request_digest,
        new_record=second,
    )
    assert outcome == "publication_busy"


def test_cas_stale_and_cancel_idempotency(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        new_record=record,
    )
    stale = cas_transition_publication_stale(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        expected_operation_version=1,
        last_observed_head_revision_id="rev:newhead",
    )
    assert stale.authority_state == "stale"
    assert stale.expected_parent_revision_id == "rev:parent01"
    assert stale.last_observed_head_revision_id == "rev:newhead"
    again = cas_transition_publication_stale(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        expected_operation_version=stale.operation_version,
        last_observed_head_revision_id="rev:newhead",
    )
    assert again == stale

    draft2 = str(uuid.uuid4())
    op2 = str(uuid.uuid4())
    rec2 = _operation(draft_id=draft2, operation_id=op2)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft2,
        operation_id=op2,
        claim_request_digest=rec2.claim_request_digest,
        new_record=rec2,
    )
    cancelled = cas_transition_publication_cancelled(
        tmp_path,
        draft_id=draft2,
        operation_id=op2,
        expected_operation_version=1,
    )
    assert cancelled.authority_state == "cancelled"
    assert cancelled.operation_version == 2
    again_cancel = cas_transition_publication_cancelled(
        tmp_path,
        draft_id=draft2,
        operation_id=op2,
        expected_operation_version=999,
    )
    assert again_cancel.authority_state == "cancelled"


def test_operation_rejects_world_campaign_mismatch_with_snapshot() -> None:
    snap = _snapshot()
    digest = source_snapshot_digest_for(snap)
    with pytest.raises(ValidationError, match="world_id must match"):
        ThreatStatblockPublicationOperationV1(
            operation_id=str(uuid.uuid4()),
            operation_version=1,
            claim_request_digest="sha256:" + "c" * 64,
            source_snapshot=snap,
            source_snapshot_digest=digest,
            world_id="world_other",
            campaign_id=snap.campaign_id,
            expected_parent_revision_id="rev:parent01",
            last_observed_head_revision_id="rev:parent01",
            authority_state="awaiting_identity_resolution",
            created_at=_now(),
            updated_at=_now(),
        )


def test_operation_rejects_duplicate_phase_artifact_kinds() -> None:
    snap = _snapshot()
    digest = source_snapshot_digest_for(snap)
    duplicate = PublicationArtifactRefV1(
        artifact_kind="identity_resolution",
        artifact_id="id_1",
        artifact_schema="dmb_identity_resolution_v1",
        artifact_digest="sha256:" + "b" * 64,
        storage_owner="publication",
    )
    with pytest.raises(ValidationError, match="duplicate phase artifact kind"):
        ThreatStatblockPublicationOperationV1(
            operation_id=str(uuid.uuid4()),
            operation_version=1,
            claim_request_digest="sha256:" + "c" * 64,
            source_snapshot=snap,
            source_snapshot_digest=digest,
            world_id=snap.world_id,
            campaign_id=snap.campaign_id,
            expected_parent_revision_id="rev:parent01",
            last_observed_head_revision_id="rev:parent01",
            authority_state="identity_resolved",
            phase_artifacts=[duplicate, duplicate.model_copy(update={"artifact_id": "id_2"})],
            created_at=_now(),
            updated_at=_now(),
        )


def test_operation_rejects_terminal_fields_on_current_states() -> None:
    snap = _snapshot()
    digest = source_snapshot_digest_for(snap)
    with pytest.raises(ValidationError, match="forbids terminal fields"):
        ThreatStatblockPublicationOperationV1(
            operation_id=str(uuid.uuid4()),
            operation_version=1,
            claim_request_digest="sha256:" + "c" * 64,
            source_snapshot=snap,
            source_snapshot_digest=digest,
            world_id=snap.world_id,
            campaign_id=snap.campaign_id,
            expected_parent_revision_id="rev:parent01",
            last_observed_head_revision_id="rev:parent01",
            authority_state="awaiting_identity_resolution",
            terminal_code="blocked",
            created_at=_now(),
            updated_at=_now(),
        )


def test_existing_operation_skips_build_new_record(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        new_record=record,
    )
    builder_called = False

    def build_new_record() -> ThreatStatblockPublicationOperationV1:
        nonlocal builder_called
        builder_called = True
        return record

    outcome, existing = claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        build_new_record=build_new_record,
    )
    assert outcome == "resume"
    assert existing == record
    assert builder_called is False


def test_build_new_record_runs_under_publication_lock(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    claim_digest = _claim_digest(draft_id, op_id)
    callback_started = threading.Event()
    callback_release = threading.Event()
    concurrent_blocked = threading.Event()

    def build_new_record() -> ThreatStatblockPublicationOperationV1:
        callback_started.set()
        callback_release.wait(timeout=2.0)
        return _operation(draft_id=draft_id, operation_id=op_id)

    def concurrent_reader() -> None:
        assert callback_started.wait(timeout=2.0)
        start = time.monotonic()
        get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id)
        if time.monotonic() - start >= 0.02:
            concurrent_blocked.set()

    def releaser() -> None:
        assert callback_started.wait(timeout=2.0)
        time.sleep(0.05)
        callback_release.set()

    reader = threading.Thread(target=concurrent_reader)
    releaser_thread = threading.Thread(target=releaser)
    reader.start()
    releaser_thread.start()

    outcome, written = claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=claim_digest,
        build_new_record=build_new_record,
    )
    reader.join(timeout=2.0)
    releaser_thread.join(timeout=2.0)

    assert outcome == "claimed"
    assert written is not None
    assert concurrent_blocked.is_set()


def test_invalid_draft_id_rejects_with_422(tmp_path: Path) -> None:
    op_id = str(uuid.uuid4())
    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        get_publication_operation(tmp_path, draft_id="../evil", operation_id=op_id)
    assert exc.value.status_code == 422


def test_invalid_operation_id_rejects_with_422(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        get_publication_operation(tmp_path, draft_id=draft_id, operation_id="not-valid")
    assert exc.value.status_code == 422


def test_invalid_operation_filename_is_corruption(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    directory = publication_root(tmp_path) / draft_id
    directory.mkdir(parents=True)
    (directory / "bad-name.json").write_text("{}", encoding="utf-8")
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        atomic_claim_publication_operation(
            tmp_path,
            draft_id=draft_id,
            operation_id=op_id,
            claim_request_digest=record.claim_request_digest,
            new_record=record,
        )
    assert exc.value.status_code == 500
    assert "corrupt" in str(exc.value).lower()
    assert get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id) is None


def test_builder_identity_mismatch_rejects_without_write(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    claim_digest = _claim_digest(draft_id, op_id)
    wrong_op = str(uuid.uuid4())

    def build_new_record() -> ThreatStatblockPublicationOperationV1:
        return _operation(draft_id=draft_id, operation_id=wrong_op)

    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        claim_publication_operation(
            tmp_path,
            draft_id=draft_id,
            operation_id=op_id,
            claim_request_digest=claim_digest,
            build_new_record=build_new_record,
        )
    assert exc.value.status_code == 500
    assert "identity mismatch" in str(exc.value).lower()
    assert get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id) is None


def test_builder_digest_mismatch_rejects_without_write(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    claim_digest = _claim_digest(draft_id, op_id)

    def build_new_record() -> ThreatStatblockPublicationOperationV1:
        record = _operation(draft_id=draft_id, operation_id=op_id)
        return record.model_copy(update={"claim_request_digest": "sha256:" + "e" * 64})

    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        claim_publication_operation(
            tmp_path,
            draft_id=draft_id,
            operation_id=op_id,
            claim_request_digest=claim_digest,
            build_new_record=build_new_record,
        )
    assert exc.value.status_code == 500
    assert "digest mismatch" in str(exc.value).lower()
    assert get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id) is None


def test_new_claim_rejects_reserved_successor_state(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    claim_digest = _claim_digest(draft_id, op_id)

    def build_new_record() -> ThreatStatblockPublicationOperationV1:
        return _operation(draft_id=draft_id, operation_id=op_id).model_copy(
            update={"authority_state": "verified"}
        )

    with pytest.raises(ThreatStatblockPublicationStoreError) as exc:
        claim_publication_operation(
            tmp_path,
            draft_id=draft_id,
            operation_id=op_id,
            claim_request_digest=claim_digest,
            build_new_record=build_new_record,
        )
    assert exc.value.status_code == 500
    assert "must begin" in str(exc.value)
    assert get_publication_operation(tmp_path, draft_id=draft_id, operation_id=op_id) is None


def test_stale_transition_on_cancelled_is_idempotent(tmp_path: Path) -> None:
    draft_id = str(uuid.uuid4())
    op_id = str(uuid.uuid4())
    record = _operation(draft_id=draft_id, operation_id=op_id)
    atomic_claim_publication_operation(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        claim_request_digest=record.claim_request_digest,
        new_record=record,
    )
    cancelled = cas_transition_publication_cancelled(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        expected_operation_version=1,
    )
    assert cancelled.authority_state == "cancelled"
    stale_attempt = cas_transition_publication_stale(
        tmp_path,
        draft_id=draft_id,
        operation_id=op_id,
        expected_operation_version=999,
        last_observed_head_revision_id="rev:newhead",
    )
    assert stale_attempt.authority_state == "cancelled"
    assert stale_attempt == cancelled
