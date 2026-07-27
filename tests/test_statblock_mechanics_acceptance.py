from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
    downstream_invalid_request,
    downstream_timeout,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    CreateStatblockResponseV1,
    StatblockDefinitionV1Input,
    ValidationReceiptV1,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    CreateStatblockResult,
    locator_from_create_response,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptThreatDraftMechanicsRequestV1,
    AcceptedMechanicsRefV1,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
)
from apps.live_control_server.services import statblock_mechanics_acceptance as acceptance
from apps.live_control_server.services.statblock_acceptance_reconciliation import (
    AcceptanceReconciliationError,
    claim_acceptance_operation,
    create_request_digest_for_body,
    get_acceptance_operation,
    record_server_committed,
)
from apps.live_control_server.services.statblock_definition_validation import (
    ValidateDefinitionBuddyResponseV1,
)
from apps.live_control_server.services.statblock_mechanics_acceptance import (
    begin_or_resume_acceptance,
    recover_acceptance_operation,
)
from apps.live_control_server.services.threat_draft_store import (
    attach_accepted_mechanics_ref,
    create_threat_draft,
    get_threat_draft,
)

FIXTURES = Path(__file__).parent / "fixtures" / "statblocks" / "v1"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _definition() -> StatblockDefinitionV1Input:
    return StatblockDefinitionV1Input.model_validate(
        _fixture("candidate-response.json")["definition"]
    )


def _receipt() -> ValidationReceiptV1:
    return ValidationReceiptV1.model_validate(_fixture("validate-response.json")["validation_receipt"])


def _digest() -> str:
    return _fixture("validate-response.json")["definition_digest"]


def _create_draft(tmp_path: Path):
    return create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Ironhide Brute",
            description="A brutal enforcer.",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_g1"),
            created_by="gm",
        ),
    )


def _accept_request(
    draft,
    *,
    operation_id: str | None = None,
) -> AcceptThreatDraftMechanicsRequestV1:
    return AcceptThreatDraftMechanicsRequestV1(
        operation_id=operation_id or str(uuid.uuid4()),
        expected_draft_version=draft.version,
        definition=_definition(),
        validation_receipt=_receipt(),
        validation_definition_digest=_digest(),
        change_summary="Accepted in test.",
        actor="gm",
    )


def _validate_ok(**_kwargs) -> ValidateDefinitionBuddyResponseV1:
    return ValidateDefinitionBuddyResponseV1(
        outcome="success",
        definition_digest=_digest(),
        validation_receipt=_receipt(),
    )


def _create_result() -> CreateStatblockResult:
    response = CreateStatblockResponseV1.model_validate(_fixture("create-response.json"))
    return CreateStatblockResult(
        locator=locator_from_create_response(response),
        server_metadata={},
    )


class FakeStatblockClient:
    def __init__(
        self,
        *,
        result=None,
        error=None,
        delay_event: threading.Event | None = None,
    ):
        self.result = result
        self.error = error
        self.delay_event = delay_event
        self.create_calls: list[dict] = []
        self.lock = threading.Lock()

    def create_statblock(self, body: dict):
        with self.lock:
            self.create_calls.append(body)
        if self.delay_event is not None:
            self.delay_event.wait(timeout=2.0)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result

    def validate_definition(self, _request):
        raise AssertionError("validation should be mocked")

    def close(self) -> None:
        return None


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_validation_gate_blocks_without_claim(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    request.validation_definition_digest = "sha256:" + "0" * 64
    client = FakeStatblockClient(result=_create_result())
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label == "acceptance_blocked"
    assert client.create_calls == []
    assert get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    ) is None


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_success_mechanics_saved(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    client = FakeStatblockClient(result=_create_result())
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label == "mechanics_saved"
    assert len(client.create_calls) == 1
    create_body = client.create_calls[0]
    # Fake client records the durable journal body (nulls retained). Real DMS
    # client strips nulls only on the outbound wire.
    assert create_body.get("accepted_through") is None
    assert "asset_bindings" in create_body or create_body.get("asset_bindings") is None
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.workflow_state == "mechanics_saved"
    assert reloaded.accepted_mechanics_ref is not None
    op = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert op is not None
    assert op.authority_state == "reconciled"
    assert op.materialization.draft_ref == "attached"


def test_build_create_body_keeps_null_optional_fields_for_journal_digest() -> None:
    """Durable journal body must keep nulls so pre-change ops still resume."""
    request = AcceptThreatDraftMechanicsRequestV1(
        operation_id=str(uuid.uuid4()),
        expected_draft_version=1,
        definition=_definition(),
        validation_receipt=_receipt(),
        validation_definition_digest=_digest(),
        change_summary="Accepted in test.",
        actor=None,
        accepted_through=None,
        source_candidate_id="cand_5enq3tnxsu3lw6fk",
    )
    body = acceptance._build_create_body(request)
    assert body.get("accepted_through") is None
    assert body.get("asset_bindings") is None
    assert body.get("actor") is None
    assert body["candidate_id"] == "cand_5enq3tnxsu3lw6fk"
    assert body["change_summary"] == "Accepted in test."


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_resume_matches_prechange_null_inclusive_journal_body(
    mock_validate, tmp_path: Path
) -> None:
    """Replay after exclude_none journal regression: null-inclusive body must resume."""
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    # Pre-change journal shape: optional fields present as null.
    body = acceptance._build_create_body(request)
    assert "accepted_through" in body
    assert body["accepted_through"] is None
    digest = create_request_digest_for_body(body)
    claim_outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    assert claim_outcome == "claimed"
    assert op is not None

    client = FakeStatblockClient(result=_create_result())
    # Same Accept body rebuilt post-fix must exact-match journal (no input_conflict).
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label != "acceptance_input_conflict"
    assert result.operation_id == request.operation_id


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_timeout_stays_dispatched_unknown(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    client = FakeStatblockClient(error=downstream_timeout())
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label == "dispatched_unknown"
    assert result.authority_state == "dispatched_unknown"
    assert len(client.create_calls) == 1


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_terminal_invalid_request(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    err = downstream_invalid_request(
        "invalid",
        status_code=422,
        error_code="invalid_request",
    )
    client = FakeStatblockClient(error=err)
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label == "terminal_failure"
    assert result.authority_state == "terminal_failure"


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_concurrent_second_operation_busy(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    release = threading.Event()
    client = FakeStatblockClient(result=_create_result(), delay_event=release)
    op_a = str(uuid.uuid4())
    op_b = str(uuid.uuid4())
    results: list = []
    barrier = threading.Barrier(2)

    def worker(operation_id: str) -> None:
        barrier.wait(timeout=2.0)
        results.append(
            begin_or_resume_acceptance(
                tmp_path,
                draft_id=draft.draft_id,
                request=_accept_request(draft, operation_id=operation_id),
                client=client,  # type: ignore[arg-type]
            )
        )

    threads = [
        threading.Thread(target=worker, args=(op_a,)),
        threading.Thread(target=worker, args=(op_b,)),
    ]
    for thread in threads:
        thread.start()
    threading.Event().wait(0.05)
    release.set()
    for thread in threads:
        thread.join(timeout=5)

    labels = {r.result_label for r in results}
    assert labels == {"mechanics_saved", "acceptance_busy"}
    assert len(client.create_calls) == 1


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_validation_failed_without_persistence_proof_stays_unknown(
    mock_validate, tmp_path: Path
) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    err = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="validation failed",
        status_code=422,
        error_code="validation_failed",
        details={},
    )
    client = FakeStatblockClient(error=err)
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label == "dispatched_unknown"
    assert result.authority_state == "dispatched_unknown"


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_persistence_not_ready_is_terminal(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    err = StatblockIntegrationError(
        category="downstream_validation_failed",
        message="persistence not ready",
        status_code=422,
        error_code="validation_failed",
        details={"is_persistence_ready": False},
    )
    client = FakeStatblockClient(error=err)
    result = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert result.result_label == "terminal_failure"
    op = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert op is not None
    assert op.terminal_details == {"is_persistence_ready": False}


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_same_operation_changed_body_preserves_original(
    mock_validate, tmp_path: Path
) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    client = FakeStatblockClient(result=_create_result())
    first = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert first.result_label == "mechanics_saved"
    original = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert original is not None
    original_dump = original.model_dump(mode="json", by_alias=True)

    draft_after = get_threat_draft(tmp_path, draft.draft_id)
    changed = request.model_copy(
        update={
            "change_summary": "Different summary.",
            "expected_draft_version": draft_after.version,
        }
    )
    second = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=changed,
        client=client,  # type: ignore[arg-type]
    )
    assert second.result_label == "acceptance_input_conflict"
    assert "different request body" in (second.message or "")
    reloaded = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert reloaded is not None
    assert reloaded.model_dump(mode="json", by_alias=True) == original_dump
    assert len(client.create_calls) == 1


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_phase2_repair_after_crash_between_phases(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    assert claim_outcome == "claimed"
    assert op is not None
    locator = _create_result().locator
    record_server_committed(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        create_request_digest=digest,
        locator=locator,
    )
    ref = AcceptedMechanicsRefV1.from_locator(
        locator,
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
        accepted_from_candidate_id=None,
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=draft.version,
        locator=ref,
    )
    op_mid = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert op_mid is not None
    assert op_mid.authority_state == "server_committed"

    repaired = recover_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        client=FakeStatblockClient(result=_create_result()),  # type: ignore[arg-type]
    )
    assert repaired.result_label == "mechanics_saved"
    op2 = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert op2 is not None
    assert op2.authority_state == "reconciled"


def test_attach_preserves_accepted_at_on_idempotent_retry(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    locator = _create_result().locator
    ref = AcceptedMechanicsRefV1.from_locator(
        locator,
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
        accepted_from_candidate_id=None,
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=1,
        locator=ref,
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=2,
        locator=AcceptedMechanicsRefV1.from_locator(
            locator,
            accepted_from_draft_version=1,
            accepted_at="2099-01-01T00:00:00Z",
            accepted_from_candidate_id=None,
        ),
    )
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.accepted_mechanics_ref is not None
    assert reloaded.accepted_mechanics_ref.accepted_at == "2020-01-01T00:00:00Z"


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_response_loss_before_locator_write_stays_unknown(mock_validate, tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    client = FakeStatblockClient(result=_create_result())

    original_record = acceptance.record_server_committed

    def fail_record(*args, **kwargs):
        raise AcceptanceReconciliationError("disk full", status_code=500)

    with patch.object(acceptance, "record_server_committed", side_effect=fail_record):
        result = begin_or_resume_acceptance(
            tmp_path,
            draft_id=draft.draft_id,
            request=request,
            client=client,  # type: ignore[arg-type]
        )
    assert result.authority_state == "dispatched_unknown"
    assert len(client.create_calls) == 1

    with patch.object(acceptance, "record_server_committed", original_record):
        retry = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=client,  # type: ignore[arg-type]
        )
    assert retry.result_label == "mechanics_saved"
    assert len(client.create_calls) == 2


@patch.object(acceptance, "validate_definition", side_effect=_validate_ok)
def test_same_operation_replay_after_draft_version_advance(mock_validate, tmp_path: Path) -> None:
    from apps.live_control_server.models.threat_draft import UpdateThreatDraftRequest

    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    client = FakeStatblockClient(result=_create_result())
    first = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert first.result_label == "mechanics_saved"
    draft_saved = get_threat_draft(tmp_path, draft.draft_id)
    update_threat_draft = __import__(
        "apps.live_control_server.services.threat_draft_store", fromlist=["update_threat_draft"]
    ).update_threat_draft
    advanced = update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft_saved.version,
            name=draft_saved.name,
            description="unrelated authoring",
            threat_kind=draft_saved.threat_kind,
            generation_intent=draft_saved.generation_intent,
            encounter_context=draft_saved.encounter_context,
            graph_context_snapshot=draft_saved.graph_context_snapshot,
            focus=draft_saved.focus,
            slug_hint=draft_saved.slug_hint,
            intended_roles=list(draft_saved.intended_roles),
            tags=list(draft_saved.tags),
        ),
    )
    assert advanced.version > draft_saved.version
    mock_validate.side_effect = AssertionError(
        "validation must not run on exact-body resume"
    )
    replay = begin_or_resume_acceptance(
        tmp_path,
        draft_id=draft.draft_id,
        request=request,
        client=client,  # type: ignore[arg-type]
    )
    assert replay.result_label == "mechanics_saved"
    assert len(client.create_calls) == 1
    assert mock_validate.call_count == 1


def test_server_committed_recovery_without_server_client(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    assert claim_outcome == "claimed"
    assert op is not None
    locator = _create_result().locator
    record_server_committed(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        create_request_digest=digest,
        locator=locator,
    )
    with patch.object(
        acceptance,
        "DungeonMindStatblockV1Client",
        side_effect=AssertionError("Server client must not be constructed"),
    ):
        repaired = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=None,
        )
    assert repaired.result_label == "mechanics_saved"
    op2 = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert op2 is not None
    assert op2.authority_state == "reconciled"


def test_reconciled_without_draft_is_not_mechanics_saved(tmp_path: Path) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    locator = _create_result().locator
    record_server_committed(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        create_request_digest=digest,
        locator=locator,
    )
    ref = AcceptedMechanicsRefV1.from_locator(
        locator,
        accepted_from_draft_version=1,
        accepted_at="2020-01-01T00:00:00Z",
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=draft.version,
        locator=ref,
    )
    repaired = recover_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        client=None,
    )
    assert repaired.result_label == "mechanics_saved"

    from apps.live_control_server.services.threat_draft_store import threat_drafts_root

    draft_path = threat_drafts_root(tmp_path) / f"{draft.draft_id}.json"
    draft_path.unlink()
    read_back = acceptance.read_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert read_back.result_label == "acceptance_draft_unavailable"
    assert read_back.operation is not None
    assert read_back.operation.authority_state == "reconciled"


@pytest.mark.parametrize("authority", ["dispatched_unknown", "server_committed", "reconciled"])
def test_changed_body_conflict_zero_downstream_calls(
    tmp_path: Path, authority: str
) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    assert claim_outcome == "claimed"
    assert op is not None

    if authority in {"server_committed", "reconciled"}:
        locator = _create_result().locator
        record_server_committed(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            create_request_digest=digest,
            locator=locator,
        )
        if authority == "reconciled":
            ref = AcceptedMechanicsRefV1.from_locator(
                locator,
                accepted_from_candidate_id=None,
                accepted_from_draft_version=draft.version,
                accepted_at="2020-01-01T00:00:00Z",
            )
            attach_accepted_mechanics_ref(
                tmp_path,
                draft_id=draft.draft_id,
                expected_version=draft.version,
                locator=ref,
            )
            recover_acceptance_operation(
                tmp_path,
                draft_id=draft.draft_id,
                operation_id=request.operation_id,
                client=None,
            )

    from apps.live_control_server.services.statblock_acceptance_reconciliation import (
        acceptance_root,
    )

    journal_path = acceptance_root(tmp_path) / draft.draft_id / f"{request.operation_id}.json"
    before_bytes = journal_path.read_bytes()

    draft_after = get_threat_draft(tmp_path, draft.draft_id)
    changed = request.model_copy(
        update={
            "change_summary": f"Conflict against {authority}",
            "expected_draft_version": draft_after.version,
        }
    )

    def _boom_validate(**_kwargs):
        raise AssertionError("validation must not run on changed-body conflict")

    client = FakeStatblockClient(
        error=StatblockIntegrationError(
            category="downstream_invalid_request",
            message="create must not run",
            status_code=400,
        )
    )
    with patch.object(acceptance, "validate_definition", side_effect=_boom_validate) as mock_v:
        with patch.object(
            acceptance,
            "DungeonMindStatblockV1Client",
            side_effect=AssertionError("Server client must not be constructed"),
        ):
            second = begin_or_resume_acceptance(
                tmp_path,
                draft_id=draft.draft_id,
                request=changed,
                client=client,  # type: ignore[arg-type]
            )
    assert second.result_label == "acceptance_input_conflict"
    assert second.authority_state == authority
    assert client.create_calls == []
    assert mock_v.call_count == 0
    assert journal_path.read_bytes() == before_bytes


def test_server_create_begins_only_after_locks_released(tmp_path: Path) -> None:
    import fcntl

    from apps.live_control_server.services.statblock_acceptance_reconciliation import (
        LOCK_NAME as ACCEPTANCE_LOCK_NAME,
        acceptance_root,
    )
    from apps.live_control_server.services.threat_draft_store import (
        LOCK_NAME as STORE_LOCK_NAME,
        threat_drafts_root,
    )

    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    lock_probe: dict[str, bool] = {}

    class LockProbingClient(FakeStatblockClient):
        def create_statblock(self, body: dict):
            acc_lock = acceptance_root(tmp_path) / draft.draft_id / ACCEPTANCE_LOCK_NAME
            store_lock = threat_drafts_root(tmp_path) / STORE_LOCK_NAME
            for label, path in (("acceptance", acc_lock), ("store", store_lock)):
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a+", encoding="utf-8") as fh:
                    try:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        lock_probe[label] = False
                        raise AssertionError(f"{label} lock still held during create")
                    else:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                        lock_probe[label] = True
            return super().create_statblock(body)

    client = LockProbingClient(result=_create_result())
    with patch.object(acceptance, "validate_definition", side_effect=_validate_ok):
        result = begin_or_resume_acceptance(
            tmp_path,
            draft_id=draft.draft_id,
            request=request,
            client=client,  # type: ignore[arg-type]
        )
    assert result.result_label == "mechanics_saved"
    assert lock_probe == {"acceptance": True, "store": True}


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p.__setitem__("request_body", {"a": 1}), id="body"),
        pytest.param(
            lambda p: p.__setitem__("create_request_digest", "sha256:" + "0" * 64),
            id="digest",
        ),
        pytest.param(
            lambda p: p.__setitem__("idempotency_key", "tampered-key"),
            id="record_key",
        ),
        pytest.param(
            lambda p: p["request_body"].__setitem__("idempotency_key", "tampered-body-key"),
            id="body_key",
        ),
        pytest.param(
            lambda p: p.__setitem__("source_draft_id", str(uuid.uuid4())),
            id="draft_id",
        ),
        pytest.param(
            lambda p: p.__setitem__("operation_id", str(uuid.uuid4())),
            id="operation_id",
        ),
        pytest.param(
            lambda p: (
                p.__setitem__("source_candidate_id", "cand_tampered"),
                p["request_body"].__setitem__("candidate_id", "cand_other"),
            ),
            id="candidate_id",
        ),
    ],
)
def test_recover_after_disk_corruption_zero_server(tmp_path: Path, mutate) -> None:
    from apps.live_control_server.services.statblock_acceptance_reconciliation import (
        acceptance_root,
    )

    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    path = acceptance_root(tmp_path) / draft.draft_id / f"{request.operation_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with patch.object(
        acceptance,
        "DungeonMindStatblockV1Client",
        side_effect=AssertionError("Server client must not be constructed"),
    ):
        result = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=None,
        )
    assert result.result_label == "acceptance_blocked"
    assert result.operation_id == request.operation_id


@pytest.mark.parametrize("authority", ["server_committed", "reconciled", "terminal_failure"])
def test_later_state_recovery_without_server_client_construction(
    tmp_path: Path, authority: str
) -> None:
    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    locator = _create_result().locator
    if authority == "terminal_failure":
        from apps.live_control_server.services.statblock_acceptance_reconciliation import (
            record_terminal_failure,
        )

        record_terminal_failure(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            create_request_digest=digest,
            terminal_code="invalid_request",
            failure_category="downstream_invalid_request",
            http_status=422,
        )
    else:
        record_server_committed(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            create_request_digest=digest,
            locator=locator,
        )
        if authority == "reconciled":
            ref = AcceptedMechanicsRefV1.from_locator(
                locator,
                accepted_from_candidate_id=None,
                accepted_from_draft_version=draft.version,
                accepted_at="2020-01-01T00:00:00Z",
            )
            attach_accepted_mechanics_ref(
                tmp_path,
                draft_id=draft.draft_id,
                expected_version=draft.version,
                locator=ref,
            )

    with patch.object(
        acceptance,
        "DungeonMindStatblockV1Client",
        side_effect=AssertionError("Server client must not be constructed"),
    ):
        result = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=None,
        )
    if authority == "terminal_failure":
        assert result.result_label == "terminal_failure"
        assert result.authority_state == "terminal_failure"
    elif authority == "reconciled":
        assert result.result_label == "mechanics_saved"
        assert result.authority_state == "reconciled"
    else:
        assert result.result_label == "mechanics_saved"
        assert result.authority_state == "reconciled"


def test_server_committed_missing_and_corrupt_draft_retain_authority(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.threat_draft_store import threat_drafts_root

    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    locator = _create_result().locator
    record_server_committed(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        create_request_digest=digest,
        locator=locator,
    )

    draft_path = threat_drafts_root(tmp_path) / f"{draft.draft_id}.json"
    draft_path.unlink()

    with patch.object(
        acceptance,
        "DungeonMindStatblockV1Client",
        side_effect=AssertionError("Server client must not be constructed"),
    ):
        missing = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=None,
        )
    assert missing.result_label == "acceptance_draft_unavailable"
    assert missing.authority_state == "server_committed"
    assert missing.locator is not None

    draft_path.write_text("{not-json", encoding="utf-8")
    with patch.object(
        acceptance,
        "DungeonMindStatblockV1Client",
        side_effect=AssertionError("Server client must not be constructed"),
    ):
        corrupt = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=None,
        )
    assert corrupt.result_label == "acceptance_draft_unavailable"
    assert corrupt.authority_state == "server_committed"
    assert corrupt.locator is not None


def test_reconciled_mismatched_draft_never_reports_mechanics_saved(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
        MechanicsLocatorV1,
        PROVIDER_DUNGEONMIND,
    )
    from apps.live_control_server.services.statblock_acceptance_reconciliation import (
        reconcile_acceptance_operation,
    )
    from apps.live_control_server.services import threat_draft_store as store

    draft = _create_draft(tmp_path)
    request = _accept_request(draft)
    body = acceptance._build_create_body(request)
    digest = create_request_digest_for_body(body)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=request.operation_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest=request.validation_definition_digest,
        source_candidate_id=None,
    )
    locator = _create_result().locator
    record_server_committed(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        create_request_digest=digest,
        locator=locator,
    )
    matching = AcceptedMechanicsRefV1.from_locator(
        locator,
        accepted_from_candidate_id=None,
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    attach_accepted_mechanics_ref(
        tmp_path,
        draft_id=draft.draft_id,
        expected_version=draft.version,
        locator=matching,
    )
    reconcile_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=request.operation_id,
        create_request_digest=digest,
    )

    other = AcceptedMechanicsRefV1.from_locator(
        MechanicsLocatorV1(
            provider=PROVIDER_DUNGEONMIND,
            statblock_id="sb_other",
            revision_id="rev_other",
            contract="dungeonmind.dungeonbuddy-statblocks",
            contract_version="1.0.0",
            definition_digest="sha256:" + "b" * 64,
        ),
        accepted_from_draft_version=draft.version,
        accepted_at="2020-01-01T00:00:00Z",
    )
    with store._store_lock(tmp_path):
        current = store._load_draft_unlocked(tmp_path, draft.draft_id)
        forced = current.model_copy(update={"accepted_mechanics_ref": other})
        store._save_draft_unlocked(tmp_path, forced, as_draft_id=draft.draft_id)

    with patch.object(
        acceptance,
        "DungeonMindStatblockV1Client",
        side_effect=AssertionError("Server client must not be constructed"),
    ):
        result = recover_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=request.operation_id,
            client=None,
        )
    assert result.result_label == "accepted_ref_conflict"
    assert result.authority_state == "reconciled"
