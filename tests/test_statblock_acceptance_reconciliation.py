from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    PROVIDER_DUNGEONMIND,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptanceMaterializationV1,
    AcceptanceOperationV1,
)
from apps.live_control_server.services.statblock_acceptance_reconciliation import (
    MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT,
    claim_acceptance_operation,
    create_request_digest_for_body,
    get_acceptance_operation,
    record_terminal_failure,
)


def _locator() -> MechanicsLocatorV1:
    return MechanicsLocatorV1(
        provider=PROVIDER_DUNGEONMIND,
        statblock_id="sb_test01",
        revision_id="rev_test01",
        contract="dungeonmind.dungeonbuddy-statblocks",
        contract_version="1.0.0",
        definition_digest="sha256:" + "a" * 64,
    )


def _body() -> dict:
    return {
        "idempotency_key": "accop_test",
        "definition": {"identity": {"name": "x"}},
        "change_summary": "test",
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def test_schema_rejects_server_committed_with_attached_draft_ref() -> None:
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            operation_id=str(uuid.uuid4()),
            idempotency_key="k",
            create_request_digest="sha256:" + "b" * 64,
            request_body={"a": 1},
            source_draft_id=str(uuid.uuid4()),
            source_draft_version=1,
            validation_receipt_digest="sha256:" + "c" * 64,
            authority_state="server_committed",
            locator=_locator(),
            materialization=AcceptanceMaterializationV1(draft_ref="attached"),
            created_at=_now(),
            updated_at=_now(),
        )


def test_schema_rejects_terminal_with_locator() -> None:
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            operation_id=str(uuid.uuid4()),
            idempotency_key="k",
            create_request_digest="sha256:" + "b" * 64,
            request_body={"a": 1},
            source_draft_id=str(uuid.uuid4()),
            source_draft_version=1,
            validation_receipt_digest="sha256:" + "c" * 64,
            authority_state="terminal_failure",
            locator=_locator(),
            materialization=AcceptanceMaterializationV1(draft_ref="missing"),
            terminal_code="invalid_request",
            failure_category="downstream_invalid_request",
            http_status=422,
            created_at=_now(),
            updated_at=_now(),
        )


def test_concurrent_claim_one_active_slot(tmp_path) -> None:
    draft_id = str(uuid.uuid4())
    body = _body()
    digest = create_request_digest_for_body(body)
    op1 = str(uuid.uuid4())
    op2 = str(uuid.uuid4())
    barrier = threading.Barrier(2)
    outcomes: list = []

    def worker(operation_id: str) -> None:
        barrier.wait(timeout=2.0)
        outcome, _ = claim_acceptance_operation(
            tmp_path,
            draft_id=draft_id,
            expected_draft_version=1,
            operation_id=operation_id,
            create_request_digest=digest,
            request_body=body,
            validation_receipt_digest="sha256:" + "d" * 64,
            source_candidate_id=None,
        )
        outcomes.append((operation_id, outcome))

    # Seed draft file + index minimally — claim reads version via _load_draft_unlocked
    from apps.live_control_server.models.threat_draft import (
        CreateThreatDraftRequest,
        GenerationIntentV1,
        GraphContextSnapshotV1,
        RulesetRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import create_threat_draft

    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Test",
            description="Desc",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_g1"),
            created_by="gm",
        ),
    )
    draft_id = draft.draft_id

    t1 = threading.Thread(target=worker, args=(op1,))
    t2 = threading.Thread(target=worker, args=(op2,))
    t1.start()
    t2.start()
    t1.join(timeout=3)
    t2.join(timeout=3)

    labels = {item[1] for item in outcomes}
    assert labels == {"claimed", "acceptance_busy"}
    claimed = [op for op, outcome in outcomes if outcome == "claimed"]
    assert len(claimed) == 1
    assert get_acceptance_operation(tmp_path, draft_id=draft_id, operation_id=claimed[0])


def test_schema_rejects_terminal_without_sbw07a_proof() -> None:
    """Code/status alone is insufficient when details proof is required."""
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            operation_id=str(uuid.uuid4()),
            idempotency_key="k",
            create_request_digest="sha256:" + "b" * 64,
            request_body={"a": 1},
            source_draft_id=str(uuid.uuid4()),
            source_draft_version=1,
            validation_receipt_digest="sha256:" + "c" * 64,
            authority_state="terminal_failure",
            locator=None,
            materialization=AcceptanceMaterializationV1(draft_ref="missing"),
            terminal_code="validation_failed",
            failure_category="downstream_validation_failed",
            http_status=422,
            terminal_details=None,
            created_at=_now(),
            updated_at=_now(),
        )


def test_schema_accepts_persistence_ready_false_terminal() -> None:
    record = AcceptanceOperationV1(
        operation_id=str(uuid.uuid4()),
        idempotency_key="k",
        create_request_digest="sha256:" + "b" * 64,
        request_body={"a": 1},
        source_draft_id=str(uuid.uuid4()),
        source_draft_version=1,
        validation_receipt_digest="sha256:" + "c" * 64,
        authority_state="terminal_failure",
        locator=None,
        materialization=AcceptanceMaterializationV1(draft_ref="missing"),
        terminal_code="validation_failed",
        failure_category="downstream_validation_failed",
        http_status=422,
        terminal_details={"is_persistence_ready": False},
        created_at=_now(),
        updated_at=_now(),
    )
    assert record.authority_state == "terminal_failure"


def test_history_full_refuses_33rd_claim(tmp_path) -> None:
    from apps.live_control_server.models.threat_draft import (
        CreateThreatDraftRequest,
        GenerationIntentV1,
        GraphContextSnapshotV1,
        RulesetRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import create_threat_draft

    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Test",
            description="Desc",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_g1"),
            created_by="gm",
        ),
    )
    body = _body()
    digest = create_request_digest_for_body(body)
    for i in range(MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT):
        op_id = str(uuid.uuid4())
        claim_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            expected_draft_version=draft.version,
            operation_id=op_id,
            create_request_digest=digest,
            request_body=body,
            validation_receipt_digest="sha256:" + "e" * 64,
            source_candidate_id=None,
        )
        record_terminal_failure(
            tmp_path,
            draft_id=draft.draft_id,
            operation_id=op_id,
            create_request_digest=digest,
            terminal_code="invalid_request",
            failure_category="downstream_invalid_request",
            http_status=422,
        )
    outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=str(uuid.uuid4()),
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "f" * 64,
        source_candidate_id=None,
    )
    assert outcome == "acceptance_history_full"
    assert op is None


def test_terminal_failure_releases_active_slot(tmp_path) -> None:
    from apps.live_control_server.models.threat_draft import (
        CreateThreatDraftRequest,
        GenerationIntentV1,
        GraphContextSnapshotV1,
        RulesetRefV1,
    )
    from apps.live_control_server.services.threat_draft_store import create_threat_draft

    draft = create_threat_draft(
        tmp_path,
        CreateThreatDraftRequest(
            world_id="world_1",
            campaign_id="campaign_1",
            name="Test",
            description="Desc",
            threat_kind="creature",
            generation_intent=GenerationIntentV1(
                ruleset=RulesetRefV1(system="dnd5e", edition="2024"),
            ),
            graph_context_snapshot=GraphContextSnapshotV1(graph_revision_id="rev_g1"),
            created_by="gm",
        ),
    )
    body = _body()
    digest = create_request_digest_for_body(body)
    op1 = str(uuid.uuid4())
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op1,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "c" * 64,
        source_candidate_id=None,
    )
    record_terminal_failure(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=op1,
        create_request_digest=digest,
        terminal_code="invalid_request",
        failure_category="downstream_invalid_request",
        http_status=422,
    )
    op2 = str(uuid.uuid4())
    outcome, _ = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op2,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "d" * 64,
        source_candidate_id=None,
    )
    assert outcome == "claimed"
    assert get_acceptance_operation(tmp_path, draft_id=draft.draft_id, operation_id=op2)
