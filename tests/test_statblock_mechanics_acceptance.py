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
    reloaded = get_threat_draft(tmp_path, draft.draft_id)
    assert reloaded.workflow_state == "mechanics_saved"
    assert reloaded.accepted_mechanics_ref is not None
    op = get_acceptance_operation(
        tmp_path, draft_id=draft.draft_id, operation_id=request.operation_id
    )
    assert op is not None
    assert op.authority_state == "reconciled"
    assert op.materialization.draft_ref == "attached"


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
