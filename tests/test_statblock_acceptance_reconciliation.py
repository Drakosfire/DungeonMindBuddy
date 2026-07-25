from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind_statblocks.generated import (
    CreateStatblockRequestV1,
    StatblockDefinitionV1Input,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import (
    MechanicsLocatorV1,
    PROVIDER_DUNGEONMIND,
)
from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptanceMaterializationV1,
    AcceptanceOperationV1,
    create_request_digest_for_body,
    idempotency_key_for_operation,
)
from apps.live_control_server.models.threat_draft import (
    CreateThreatDraftRequest,
    GenerationIntentV1,
    GraphContextSnapshotV1,
    RulesetRefV1,
    UpdateThreatDraftRequest,
)
from apps.live_control_server.services.statblock_acceptance_reconciliation import (
    MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT,
    AcceptanceReconciliationError,
    acceptance_root,
    claim_acceptance_operation,
    get_acceptance_operation,
    record_terminal_failure,
)
from apps.live_control_server.services.threat_draft_store import (
    create_threat_draft,
    update_threat_draft,
)

FIXTURES = Path(__file__).parent / "fixtures" / "statblocks" / "v1"


def _definition() -> StatblockDefinitionV1Input:
    payload = json.loads((FIXTURES / "candidate-response.json").read_text(encoding="utf-8"))
    return StatblockDefinitionV1Input.model_validate(payload["definition"])


def _body(operation_id: str, *, change_summary: str = "test") -> dict:
    create = CreateStatblockRequestV1(
        idempotency_key=idempotency_key_for_operation(operation_id),
        definition=_definition(),
        change_summary=change_summary,
        actor="gm",
    )
    return json.loads(create.model_dump_json())


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _locator() -> MechanicsLocatorV1:
    return MechanicsLocatorV1(
        provider=PROVIDER_DUNGEONMIND,
        statblock_id="sb_test01",
        revision_id="rev_test01",
        contract="dungeonmind.dungeonbuddy-statblocks",
        contract_version="1.0.0",
        definition_digest="sha256:" + "a" * 64,
    )


def _create_draft(tmp_path: Path):
    return create_threat_draft(
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


def _operation_kwargs(
    *,
    operation_id: str | None = None,
    draft_id: str | None = None,
    authority_state: str = "dispatched_unknown",
    **overrides,
) -> dict:
    op_id = operation_id or str(uuid.uuid4())
    body = _body(op_id)
    kwargs = {
        "operation_id": op_id,
        "idempotency_key": idempotency_key_for_operation(op_id),
        "create_request_digest": create_request_digest_for_body(body),
        "request_body": body,
        "source_draft_id": draft_id or str(uuid.uuid4()),
        "source_draft_version": 1,
        "validation_receipt_digest": "sha256:" + "c" * 64,
        "authority_state": authority_state,
        "locator": None,
        "materialization": AcceptanceMaterializationV1(draft_ref="missing"),
        "created_at": _now(),
        "updated_at": _now(),
    }
    kwargs.update(overrides)
    return kwargs


def test_schema_rejects_server_committed_with_attached_draft_ref() -> None:
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            **_operation_kwargs(
                authority_state="server_committed",
                locator=_locator(),
                materialization=AcceptanceMaterializationV1(draft_ref="attached"),
            )
        )


def test_schema_rejects_terminal_with_locator() -> None:
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            **_operation_kwargs(
                authority_state="terminal_failure",
                locator=_locator(),
                terminal_code="invalid_request",
                failure_category="downstream_invalid_request",
                http_status=422,
            )
        )


def test_schema_rejects_untyped_request_body() -> None:
    op_id = str(uuid.uuid4())
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            operation_id=op_id,
            idempotency_key=op_id,
            create_request_digest="sha256:" + "b" * 64,
            request_body={"a": 1},
            source_draft_id=str(uuid.uuid4()),
            source_draft_version=1,
            validation_receipt_digest="sha256:" + "c" * 64,
            authority_state="dispatched_unknown",
            created_at=_now(),
            updated_at=_now(),
        )


def test_schema_rejects_digest_mismatch() -> None:
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            **_operation_kwargs(
                operation_id=op_id,
                request_body=body,
                create_request_digest="sha256:" + "0" * 64,
            )
        )


def test_schema_rejects_idempotency_key_mismatch() -> None:
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    body["idempotency_key"] = "other-key"
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            operation_id=op_id,
            idempotency_key=op_id,
            create_request_digest=create_request_digest_for_body(body),
            request_body=body,
            source_draft_id=str(uuid.uuid4()),
            source_draft_version=1,
            validation_receipt_digest="sha256:" + "c" * 64,
            authority_state="dispatched_unknown",
            created_at=_now(),
            updated_at=_now(),
        )


def test_schema_rejects_candidate_provenance_mismatch() -> None:
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    body["candidate_id"] = "cand_abc123"
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            operation_id=op_id,
            idempotency_key=op_id,
            create_request_digest=create_request_digest_for_body(body),
            request_body=body,
            source_draft_id=str(uuid.uuid4()),
            source_draft_version=1,
            source_candidate_id=None,
            validation_receipt_digest="sha256:" + "c" * 64,
            authority_state="dispatched_unknown",
            created_at=_now(),
            updated_at=_now(),
        )


def test_schema_rejects_terminal_without_sbw07a_proof() -> None:
    """Code/status alone is insufficient when details proof is required."""
    with pytest.raises(ValidationError):
        AcceptanceOperationV1(
            **_operation_kwargs(
                authority_state="terminal_failure",
                terminal_code="validation_failed",
                failure_category="downstream_validation_failed",
                http_status=422,
                terminal_details=None,
            )
        )


def test_schema_accepts_persistence_ready_false_terminal() -> None:
    record = AcceptanceOperationV1(
        **_operation_kwargs(
            authority_state="terminal_failure",
            terminal_code="validation_failed",
            failure_category="downstream_validation_failed",
            http_status=422,
            terminal_details={"is_persistence_ready": False},
        )
    )
    assert record.authority_state == "terminal_failure"


def test_concurrent_claim_one_active_slot(tmp_path) -> None:
    draft = _create_draft(tmp_path)
    draft_id = draft.draft_id
    op1 = str(uuid.uuid4())
    op2 = str(uuid.uuid4())
    barrier = threading.Barrier(2)
    outcomes: list = []

    def worker(operation_id: str) -> None:
        body = _body(operation_id)
        digest = create_request_digest_for_body(body)
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


def test_history_full_refuses_33rd_claim(tmp_path) -> None:
    draft = _create_draft(tmp_path)
    for _ in range(MAX_ACCEPTANCE_OPERATION_RECORDS_PER_DRAFT):
        op_id = str(uuid.uuid4())
        body = _body(op_id)
        digest = create_request_digest_for_body(body)
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
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    digest = create_request_digest_for_body(body)
    outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "f" * 64,
        source_candidate_id=None,
    )
    assert outcome == "acceptance_history_full"
    assert op is None


def test_terminal_failure_releases_active_slot(tmp_path) -> None:
    draft = _create_draft(tmp_path)
    op1 = str(uuid.uuid4())
    body1 = _body(op1)
    digest1 = create_request_digest_for_body(body1)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op1,
        create_request_digest=digest1,
        request_body=body1,
        validation_receipt_digest="sha256:" + "c" * 64,
        source_candidate_id=None,
    )
    record_terminal_failure(
        tmp_path,
        draft_id=draft.draft_id,
        operation_id=op1,
        create_request_digest=digest1,
        terminal_code="invalid_request",
        failure_category="downstream_invalid_request",
        http_status=422,
    )
    op2 = str(uuid.uuid4())
    body2 = _body(op2)
    digest2 = create_request_digest_for_body(body2)
    outcome, _ = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op2,
        create_request_digest=digest2,
        request_body=body2,
        validation_receipt_digest="sha256:" + "d" * 64,
        source_candidate_id=None,
    )
    assert outcome == "claimed"
    assert get_acceptance_operation(tmp_path, draft_id=draft.draft_id, operation_id=op2)


def test_resume_ignores_current_draft_version_gate(tmp_path) -> None:
    draft = _create_draft(tmp_path)
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    digest = create_request_digest_for_body(body)
    claimed, record = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "c" * 64,
        source_candidate_id=None,
    )
    assert claimed == "claimed"
    assert record is not None

    updated = update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description="advanced",
            threat_kind=draft.threat_kind,
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
            focus=draft.focus,
            slug_hint=draft.slug_hint,
            intended_roles=list(draft.intended_roles),
            tags=list(draft.tags),
        ),
    )
    assert updated.version == draft.version + 1

    outcome, resumed = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,  # stale relative to current draft
        operation_id=op_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "c" * 64,
        source_candidate_id=None,
    )
    assert outcome == "resume"
    assert resumed is not None
    assert resumed.operation_id == op_id


def test_new_claim_still_requires_current_draft_version(tmp_path) -> None:
    draft = _create_draft(tmp_path)
    updated = update_threat_draft(
        tmp_path,
        draft.draft_id,
        UpdateThreatDraftRequest(
            expected_version=draft.version,
            name=draft.name,
            description="advanced",
            threat_kind=draft.threat_kind,
            generation_intent=draft.generation_intent,
            encounter_context=draft.encounter_context,
            graph_context_snapshot=draft.graph_context_snapshot,
            focus=draft.focus,
            slug_hint=draft.slug_hint,
            intended_roles=list(draft.intended_roles),
            tags=list(draft.tags),
        ),
    )
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    digest = create_request_digest_for_body(body)
    outcome, op = claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "c" * 64,
        source_candidate_id=None,
    )
    assert outcome == "version_mismatch"
    assert op is None
    assert updated.version == 2


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
            id="key",
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
                p.get("request_body", {}).__setitem__("candidate_id", None)
                if isinstance(p.get("request_body"), dict)
                else None,
            ),
            id="candidate_id",
        ),
    ],
)
def test_disk_corruption_fails_closed_on_reload(tmp_path, mutate) -> None:
    draft = _create_draft(tmp_path)
    op_id = str(uuid.uuid4())
    body = _body(op_id)
    digest = create_request_digest_for_body(body)
    claim_acceptance_operation(
        tmp_path,
        draft_id=draft.draft_id,
        expected_draft_version=draft.version,
        operation_id=op_id,
        create_request_digest=digest,
        request_body=body,
        validation_receipt_digest="sha256:" + "c" * 64,
        source_candidate_id=None,
    )
    path = acceptance_root(tmp_path) / draft.draft_id / f"{op_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AcceptanceReconciliationError):
        get_acceptance_operation(tmp_path, draft_id=draft.draft_id, operation_id=op_id)


def test_claim_versus_draft_update_process_concurrency(tmp_path) -> None:
    """Claim observes draft version under ThreatDraft store lock (nested order)."""
    draft = _create_draft(tmp_path)
    barrier = threading.Barrier(2)
    results: dict[str, object] = {}

    def updater() -> None:
        from apps.live_control_server.services import threat_draft_store as store

        with store._store_lock(tmp_path):
            barrier.wait(timeout=2.0)
            # Hold the store lock while claim attempts nested version read.
            import time

            time.sleep(0.2)
            current = store._load_draft_unlocked(tmp_path, draft.draft_id)
            updated = current.model_copy(
                update={
                    "version": current.version + 1,
                    "description": "held-lock update",
                    "updated_at": _now(),
                }
            )
            store._save_draft_unlocked(tmp_path, updated, as_draft_id=draft.draft_id)
            results["updated_version"] = updated.version

    def claimer() -> None:
        barrier.wait(timeout=2.0)
        op_id = str(uuid.uuid4())
        body = _body(op_id)
        digest = create_request_digest_for_body(body)
        outcome, _ = claim_acceptance_operation(
            tmp_path,
            draft_id=draft.draft_id,
            expected_draft_version=draft.version,
            operation_id=op_id,
            create_request_digest=digest,
            request_body=body,
            validation_receipt_digest="sha256:" + "c" * 64,
            source_candidate_id=None,
        )
        results["claim_outcome"] = outcome

    t_update = threading.Thread(target=updater)
    t_claim = threading.Thread(target=claimer)
    t_update.start()
    t_claim.start()
    t_update.join(timeout=3)
    t_claim.join(timeout=3)

    assert results.get("updated_version") == 2
    # Either claimed before update became visible under lock, or version_mismatch
    # after updater advanced version — never a torn read.
    assert results.get("claim_outcome") in {"claimed", "version_mismatch"}
