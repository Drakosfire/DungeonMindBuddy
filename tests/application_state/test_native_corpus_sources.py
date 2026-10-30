"""Source-capable Plan owner pins cannot masquerade as classic Graph receipts."""
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_source_context import capability_bases, require_graph
from tests.test_native_corpus_source_access import lane, admit, capture  # noqa: F401


def receipt_payload(lane):
    admit(lane)
    source = capture(lane)
    value = dict(schema="dmb_plan_source_context_receipt_v1",
        receipt_serializer_version="canonical-json-utf8-v1",
        plan_context_policy={"policy": "auto_plan_world"},
        plan_basis=dict(world_id="managed", document_id="plan:test", object_revision=1,
            work_revision_id=str(uuid4()), revision_n=1, content_sha256="a" * 64),
        playable_target=None, source_authority=source.authority.model_dump(mode="json"),
        graph_capability=None,
        assembled_input=dict(assembler_version="plan_source_jev_initial_v1",
            provider_model_name="jev-1.14.0", provider_model_version="jev-1.14.0",
            tokenizer_name="utf8_json_bytes_plus_64_per_node_v1", tokenizer_version="v1",
            provider_envelope_input_tokens=120, output_token_reserve=200,
            context_window_limit=1000, included_history=[], assembled_input_sha256="b" * 64))
    return rehash(value)


def rehash(value):
    value.pop("context_receipt_sha256", None)
    # Schema defaults are serialized in the receipt's actual canonical form.
    value["plan_context_policy"].setdefault("schema", "dmb_plan_context_policy_v1")
    value["context_receipt_sha256"] = t.canonical_sha256(value)
    return value


def test_source_receipt_has_no_graph_authority_and_roundtrips_exactly(lane):
    payload = receipt_payload(lane)
    receipt = t.PlanSourceContextReceiptV1.model_validate(payload)
    assert t.PlanSourceContextReceiptV1.model_validate_json(receipt.model_dump_json()) == receipt
    bases = capability_bases(receipt)
    assert bases.graph is None and bases.source == receipt.source_authority
    assert bases.plan_basis == receipt.plan_basis
    assert not hasattr(receipt, "graph_authority")
    with pytest.raises(ValueError, match="no authorized Graph"):
        require_graph(receipt)


def test_source_revision_cannot_be_submitted_as_graph_authority(lane):
    payload = receipt_payload(lane)
    payload["graph_authority"] = {"graph_revision": payload["source_authority"]["revision_id"]}
    with pytest.raises(ValidationError):
        t.PlanSourceContextReceiptV1.model_validate(rehash(payload))


def test_foreign_source_world_refuses_even_with_recomputed_digest(lane):
    payload = receipt_payload(lane)
    payload["source_authority"]["managed_world_id"] = "another"
    with pytest.raises(ValidationError, match="actual Plan World"):
        t.PlanSourceContextReceiptV1.model_validate(rehash(payload))


def test_changed_source_pin_cannot_reuse_receipt_digest(lane):
    payload = receipt_payload(lane)
    changed = deepcopy(payload)
    changed["source_authority"]["revision_id"] = "rev:changed"
    with pytest.raises(ValidationError, match="digest differs"):
        t.PlanSourceContextReceiptV1.model_validate(changed)


def test_unavailable_source_is_explicit_and_does_not_invent_graph(lane):
    payload = receipt_payload(lane)
    payload["source_authority"] = dict(schema="dmb_native_corpus_unavailable_v1",
        managed_world_id="managed", failure_code="native_source_head_unavailable")
    receipt = t.PlanSourceContextReceiptV1.model_validate(rehash(payload))
    bases = capability_bases(receipt)
    assert bases.graph is None
    assert bases.source.failure_code == "native_source_head_unavailable"
    assert not hasattr(bases.source, "revision_id")


def test_actual_provider_allowance_cannot_be_overrun(lane):
    payload = receipt_payload(lane)
    payload["assembled_input"]["provider_envelope_input_tokens"] = 900
    with pytest.raises(ValidationError, match="provider context allowance"):
        t.PlanSourceContextReceiptV1.model_validate(rehash(payload))


def test_source_decision_never_relabels_native_revision_as_graph():
    from application_state.agent_conversation.jev_retrieval_contract import (
        PlanSourceRetrievalDecisionInputV1, RetrievalSelection, validate_source_selection,
    )
    request = PlanSourceRetrievalDecisionInputV1(request_id=uuid4(), parent_attempt_id=uuid4(),
        scope_sha256="a" * 64, question="What did the check reveal?", candidates=(
            {"handle": "source-search", "label": "Search sources", "kind": "navigation"},),
        allowed_operations=("select_candidates", "finish_retrieval"),
        source_authority_status="available", source_revision="native:R", graph_revision=None)
    choice = RetrievalSelection(operation="select_candidates", selected_handles=("source-search",))
    args = dict(expected_request_sha256=request.digest, current_scope_sha256=request.scope_sha256,
        current_source_revision="native:R", current_graph_revision=None,
        current_parent_attempt_id=request.parent_attempt_id)
    assert validate_source_selection(request, choice, **args)[0].handle == "source-search"
    with pytest.raises(ValueError, match="capability pins"):
        validate_source_selection(request, choice, **(args | {
            "current_source_revision": None, "current_graph_revision": "native:R"}))
    with pytest.raises(ValueError, match="capability pins"):
        validate_source_selection(request, choice, **(args | {"current_source_revision": "native:changed"}))
    with pytest.raises(ValueError, match="not admitted"):
        validate_source_selection(request, choice.model_copy(update={"selected_handles": ("foreign",)}), **args)


def test_unavailable_source_decision_keeps_independent_choices_without_fake_pin():
    from application_state.agent_conversation.jev_retrieval_contract import (
        PlanSourceRetrievalDecisionInputV1, prepare_decision,
    )
    request = PlanSourceRetrievalDecisionInputV1(request_id=uuid4(), parent_attempt_id=uuid4(),
        scope_sha256="a" * 64, question="Which rule applies?", candidates=(
            {"handle": "rules", "label": "Read rules", "kind": "rules"},),
        allowed_operations=("select_candidates", "finish_retrieval"),
        source_authority_status="unavailable", source_revision=None, graph_revision=None)
    assert prepare_decision(request).questions
    invalid = request.model_dump(mode="json", by_alias=True) | {"source_revision": "native:invented"}
    with pytest.raises(ValidationError, match="authority disposition"):
        PlanSourceRetrievalDecisionInputV1.model_validate(invalid)


def source_policy(authority_sha256="c" * 64):
    return t.PlanSourceExecutionPolicyV1(allowed_graph_operations=[],
        max_provider_attempts=None, max_graph_operations=None, max_results_per_operation=0,
        max_total_provider_input_tokens=None, max_total_provider_output_tokens=None,
        provider_input_accounting={"kind": "conservative_upper_bound",
            "estimator": "utf8_json_bytes_plus_64_per_node_v1"},
        source_opened=False, source_read_scope=None, max_source_read_chars=96000,
        max_chars_per_source_read=12000, source_read_accounting="settled_receipts_v1",
        provider_roles={"controller": {"provider": "typesafe", "model": "jev-1.14.0", "api_mode": "decision"},
            "writer": {"provider": "openai", "model": "gpt-6-luna", "api_mode": "responses"}},
        native_source_section_policy="exact_native_source_sections_v1",
        requested_work_policy="semantic_plan_placement_v1", placement_catalog_sha256=None,
        source_authority_sha256=authority_sha256)


def source_execution(policy=None, events=()):
    policy = policy or source_policy()
    payload = {"schema": "dmb_plan_source_execution_v1", "context_receipt_sha256": "a" * 64,
        "policy": policy.model_dump(mode="json", by_alias=True)}
    payload["execution_policy_sha256"] = t.canonical_sha256(payload)
    return t.PlanSourceExecutionV1.model_validate(payload | {
        "events": [row.model_dump(mode="json", by_alias=True) for row in events]})


def test_source_execution_has_distinct_kind_and_no_graph_scope():
    execution = source_execution()
    assert execution.schema_ == "dmb_plan_source_execution_v1"
    assert execution.policy.source_read_scope is None
    assert execution.effective_source_pins() == {}
    assert execution.policy.allowed_graph_operations == []
    assert t.PlanSourceExecutionV1.model_validate_json(execution.model_dump_json()) == execution


def test_source_policy_cannot_offer_graph_actions_without_graph_scope():
    payload = source_policy().model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError, match="actual Graph capability"):
        t.PlanSourceExecutionPolicyV1.model_validate(payload | {"allowed_graph_operations": ["object"]})


def test_historical_graph_policy_cannot_disable_graph_by_using_empty_operations():
    payload = source_policy().model_dump(mode="json", by_alias=True)
    old = {key: payload[key] for key in t.GraphExecutionPolicyV1.model_fields}
    old["policy_version"] = "world_graph_execution_uncapped_v1"
    with pytest.raises(ValidationError, match="explicit source-capable"):
        t.GraphExecutionPolicyV1.model_validate(old)


@pytest.mark.parametrize("operations", [[], ["object"]])
def test_generic_graph_policy_cannot_claim_source_only_uncapped_version(operations):
    payload = source_policy().model_dump(mode="json", by_alias=True)
    generic = {key: payload[key] for key in t.GraphExecutionPolicyV1.model_fields}
    generic["allowed_graph_operations"] = operations
    with pytest.raises(ValidationError, match="typed source policy"):
        t.GraphExecutionPolicyV1.model_validate(generic)


def native_body_ledger(lane, *, failed_read=False, full_document=False, all_sections=False):
    from hashlib import sha256
    from application_state.agent_conversation.native_corpus import (
        NativeBodySearchAuthorizedV1, NativeBodySearchObservedV1, NativeBodySectionMatchV1,
        NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeBodyProviderIncludedV1,
        build_native_body_catalog, select_native_body_excerpt, body_frame,
        native_corpus_search_handle, native_body_handle, native_full_document_handle,
        select_native_full_document,
    )
    from tests.test_native_corpus_source_access import BODY
    body = BODY + "\n## Unrelated scene\nUnrelated source context.\n"
    admit(lane, body=body)
    captured = capture(lane)
    catalog = build_native_body_catalog(captured.authority, captured.members[0], body)
    section = catalog.sections[0]
    query_sha = sha256(b"What did the party learn about the source context?").hexdigest()
    policy = source_policy(t.canonical_sha256(captured.authority.model_dump(mode="json")))
    initial = source_execution(policy)
    events = []
    def common(): return dict(event_id=uuid4(), sequence=len(events))
    def append(event):
        events.append(event)
        source_execution(policy, events)  # every durable prefix must validate
        return event
    def provider(*, semantic=False, writer=False):
        cls = t.PlanRequestedWorkAuthorizedV2 if semantic else t.PlanJevWriterAuthorizedV1 if writer else t.PlanJevProviderAuthorizedV1
        payload = dict(kind="plan_requested_work_authorized_v2" if semantic else "plan_jev_writer_authorized_v1" if writer else "plan_jev_provider_authorized_v1",
            provider_attempt_id=uuid4(), envelope_sha256="b"*64,
            serializer_version="openai-sdk-json-v1" if writer else "typesafe-sdk-json-v1",
            provider="openai" if writer else "typesafe", model="gpt-6-luna" if writer else "jev-1.14.0",
            api_mode="responses" if writer else "decision", tool_schema_sha256=t.canonical_sha256([]),
            input_accounting_kind="conservative_upper_bound", input_estimator="utf8_json_bytes_plus_64_per_node_v1",
            input_tokens=100, output_token_reserve=200, included_assertion_ids=[], included_relationship_ids=[],
            included_evidence_ref_ids=[], included_graph_event_ids=[], included_source_read_event_ids=[])
        if writer: payload["frame_sha256"] = "c"*64
        else: payload.update(decision_request_id=uuid4(), parent_request_sha256="c"*64)
        return cls(**common(), **payload)
    def outcomes(auth):
        append(t.ProviderOutcomeEventV1(kind="provider_outcome", **common(),
            provider_attempt_id=auth.provider_attempt_id, outcome="sdk_entered"))
        append(t.ProviderOutcomeEventV1(kind="provider_outcome", **common(),
            provider_attempt_id=auth.provider_attempt_id, outcome="response_received", response_sha256="d"*64))
    def choice(auth, operation, handles=()):
        return append(t.PlanJevRetrievalSelectionV1(kind="plan_jev_retrieval_selected_v1", **common(),
            context_receipt_sha256=initial.context_receipt_sha256, execution_policy_sha256=initial.execution_policy_sha256,
            decision_request_id=auth.decision_request_id, controller_attempt_id=auth.provider_attempt_id,
            controller_envelope_sha256=auth.envelope_sha256, controller_response_sha256="d"*64,
            parent_request_sha256=auth.parent_request_sha256, operation=operation, selected_handles=list(handles)))
    auth = append(provider(semantic=True)); outcomes(auth)
    append(t.PlanRequestedWorkSelectedV2(kind="plan_requested_work_selected_v2", **common(),
        context_receipt_sha256=initial.context_receipt_sha256, execution_policy_sha256=initial.execution_policy_sha256,
        decision_request_id=auth.decision_request_id, controller_attempt_id=auth.provider_attempt_id,
        controller_envelope_sha256=auth.envelope_sha256, controller_response_sha256="d"*64,
        parent_request_sha256=auth.parent_request_sha256, requested_work="discuss",
        original_capture_sha256=None, placement_catalog_sha256=None, placement_selector=None,
        original_capture=None, placement_catalog=None))
    auth = append(provider()); outcomes(auth)
    choice(auth, "select_candidates", (native_corpus_search_handle(query_sha),))
    grant = append(NativeBodySearchAuthorizedV1(**common(), provider_attempt_id=auth.provider_attempt_id,
        context_receipt_sha256=initial.context_receipt_sha256, execution_policy_sha256=initial.execution_policy_sha256,
        authority=captured.authority, query_sha256=query_sha))
    observed = append(NativeBodySearchObservedV1(**common(), authorization_event_id=grant.event_id,
        catalogs=(catalog,), matches=tuple(NativeBodySectionMatchV1(catalog_sha256=catalog.catalog_sha256,
            section_id=row.section_id, matched_terms=("party",) if index == 0 else ("context",))
            for index, row in enumerate(catalog.sections)), unavailable_source_count=0))
    reads = []
    for section in catalog.sections if all_sections else (catalog.sections[0],):
        auth = append(provider()); outcomes(auth)
        handle = native_full_document_handle(catalog.catalog_sha256) if full_document else native_body_handle(catalog.catalog_sha256, section.section_id)
        choice(auth, "select_candidates", (handle,))
        read_auth = append(NativeBodyReadAuthorizedV1(**common(), provider_attempt_id=auth.provider_attempt_id,
            search_event_id=observed.event_id, catalog_sha256=catalog.catalog_sha256,
            retrieval_kind="full_document" if full_document else "section",
            section_id=None if full_document else section.section_id))
        excerpt = select_native_full_document(catalog, body) if full_document else select_native_body_excerpt(catalog, body, section.section_id)
        read = append(NativeBodyReadObservedV1(**common(), authorization_event_id=read_auth.event_id,
            excerpt=None if failed_read else excerpt,
            failure_code="native_body_unavailable" if failed_read else None))
        reads.append(read)
    auth = append(provider()); outcomes(auth); choice(auth, "finish_retrieval")
    writer = provider(writer=True)
    included = [] if failed_read else reads
    append(NativeBodyProviderIncludedV1(**common(), provider_attempt_id=writer.provider_attempt_id,
        envelope_sha256=writer.envelope_sha256, read_event_ids=tuple(row.event_id for row in included),
        frame_sha256=t.canonical_sha256(body_frame(included))))
    writer = writer.model_copy(update={"sequence": len(events)})
    append(writer); outcomes(writer)
    return source_execution(policy, events)


def test_native_execution_acquisition_and_writer_join_roundtrip(lane):
    from application_state.agent_conversation.native_corpus import NativeBodyReadObservedV1
    execution = native_body_ledger(lane)
    assert execution.policy.source_read_scope is None
    read = next(row for row in execution.events if isinstance(row, NativeBodyReadObservedV1))
    assert read.excerpt.text
    assert t.PlanSourceExecutionV1.model_validate_json(execution.model_dump_json()) == execution


def test_failed_native_read_is_retained_without_fabricated_writer_support(lane):
    from application_state.agent_conversation.native_corpus import NativeBodyReadObservedV1, NativeBodyProviderIncludedV1
    execution = native_body_ledger(lane, failed_read=True)
    read = next(row for row in execution.events if isinstance(row, NativeBodyReadObservedV1))
    included = next(row for row in execution.events if isinstance(row, NativeBodyProviderIncludedV1))
    assert read.failure_code == "native_body_unavailable" and read.excerpt is None
    assert included.read_event_ids == ()


@pytest.mark.parametrize("change", ["unselected_read", "changed_authority", "wrong_read", "wrong_writer"])
def test_native_execution_rejects_acquisition_and_inclusion_substitutions(lane, change):
    from application_state.agent_conversation.native_corpus import (
        NativeBodyReadAuthorizedV1, NativeBodySearchAuthorizedV1, NativeBodyProviderIncludedV1,
    )
    execution = native_body_ledger(lane)
    payload = execution.model_dump(mode="json", by_alias=True)
    if change == "unselected_read":
        event = next(row for row in payload["events"] if row["kind"] == "plan_jev_retrieval_selected_v1"
            and row["selected_handles"] and row["selected_handles"][0].startswith("native-body:"))
        event["selected_handles"] = ["different:selection"]
    elif change == "changed_authority":
        event = next(row for row in payload["events"] if row["kind"] == "native_body_search_authorized_v1")
        event["authority"]["revision_id"] = "native:other"
    else:
        event = next(row for row in payload["events"] if row["kind"] == "native_body_provider_included_v1")
        event["read_event_ids" if change == "wrong_read" else "provider_attempt_id"] = [str(uuid4())] if change == "wrong_read" else str(uuid4())
    with pytest.raises(ValidationError):
        t.PlanSourceExecutionV1.model_validate(payload)


def test_source_execution_binds_exact_receipt_and_source_authority(lane):
    from application_state.agent_conversation.plan_source_context import validate_source_execution_binding
    receipt = t.PlanSourceContextReceiptV1.model_validate(receipt_payload(lane))
    policy = source_policy(t.canonical_sha256(receipt.source_authority.model_dump(mode="json", by_alias=True)))
    payload = {"schema": "dmb_plan_source_execution_v1", "context_receipt_sha256": receipt.context_receipt_sha256,
        "policy": policy.model_dump(mode="json", by_alias=True)}
    payload["execution_policy_sha256"] = t.canonical_sha256(payload)
    execution = t.PlanSourceExecutionV1.model_validate(payload | {"events": []})
    validate_source_execution_binding(receipt, execution)
    with pytest.raises(ValueError, match="frozen receipt authority"):
        validate_source_execution_binding(receipt, source_execution(policy))
    wrong_policy = source_policy("f" * 64)
    payload["policy"] = wrong_policy.model_dump(mode="json", by_alias=True)
    payload.pop("execution_policy_sha256")
    payload["execution_policy_sha256"] = t.canonical_sha256(payload)
    wrong = t.PlanSourceExecutionV1.model_validate(payload | {"events": []})
    with pytest.raises(ValueError, match="frozen receipt authority"):
        validate_source_execution_binding(receipt, wrong)


def test_explicit_full_document_choice_is_retained_in_writer_inclusion(lane):
    from application_state.agent_conversation.native_corpus import NativeBodyReadObservedV1
    execution = native_body_ledger(lane, full_document=True)
    read = next(row for row in execution.events if isinstance(row, NativeBodyReadObservedV1))
    assert read.excerpt.selector_policy == "native_full_document_v1"
    assert any(isinstance(row, t.PlanJevRetrievalSelectionV1)
        and any(handle.startswith("native-full-document:") for handle in row.selected_handles)
        for row in execution.events)


def test_accumulated_section_choices_cannot_expose_whole_document(lane):
    # Actual partial selections in distinct acknowledged controller decisions
    # cover the source only when combined for the final writer.
    with pytest.raises(ValidationError, match="Accumulated whole-document exposure"):
        native_body_ledger(lane, all_sections=True)


def source_submission(lane, *, unavailable=False):
    value = receipt_payload(lane)
    if unavailable:
        value["source_authority"] = dict(schema="dmb_native_corpus_unavailable_v1",
            managed_world_id="managed", failure_code="native_source_head_unavailable")
    receipt = t.PlanSourceContextReceiptV1.model_validate(rehash(value))
    basis = receipt.plan_basis
    policy = source_policy(t.canonical_sha256(receipt.source_authority.model_dump(mode="json", by_alias=True)))
    payload = {"schema": "dmb_plan_source_execution_v1", "context_receipt_sha256": receipt.context_receipt_sha256,
        "policy": policy.model_dump(mode="json", by_alias=True)}
    execution = t.PlanSourceExecutionV1.model_validate(payload | {
        "execution_policy_sha256": t.canonical_sha256(payload), "events": []})
    intent = t.SubmittedTurnIntentV2(world_id=basis.world_id, client_thread_id="test",
        message="What did the check reveal?", surface_id="plan", surface_instance_id="plan-instance",
        client_work_state="saved_clean", primary_work=dict(kind="plan", object_id=basis.document_id,
            expected_revision=basis.object_revision, expected_revision_n=basis.revision_n,
            expected_content_sha256=basis.content_sha256), plan_context_policy=receipt.plan_context_policy,
        graph_request=dict(mode="none", focus=None), graph_selection=None)
    provenance = t.TurnProvenance(world_id=basis.world_id, surface_resolution="resolved",
        surface_id="plan", surface_instance_id=intent.surface_instance_id,
        primary_work=dict(resolution="resolved", kind="plan", object_id=basis.document_id,
            object_revision=basis.object_revision, work_revision_id=basis.work_revision_id,
            revision_n=basis.revision_n, content_sha256=basis.content_sha256),
        selected_object=dict(resolution="absent"))
    return t.TurnSubmission(world_id=basis.world_id, conversation_id=uuid4(), idempotency_key=uuid4(),
        expected_conversation_revision=1, user_text=intent.message, provenance=provenance,
        submitted_intent_v2=intent, graph_context_receipt=receipt, graph_context_execution=execution)


def test_source_submission_uses_ordinary_plan_intent_and_closed_union(lane):
    submission = source_submission(lane)
    reopened = t.TurnSubmission.model_validate_json(submission.model_dump_json(by_alias=True))
    assert reopened == submission
    assert isinstance(reopened.graph_context_receipt, t.PlanSourceContextReceiptV1)
    assert isinstance(reopened.graph_context_execution, t.PlanSourceExecutionV1)
    assert reopened.graph_context_receipt.graph_capability is None


@pytest.mark.parametrize("field,value", [
    ("expected_revision", 2), ("expected_revision_n", 2),
    ("expected_content_sha256", "f" * 64), ("object_id", "plan:other"),
])
def test_source_submission_rejects_changed_plan_intent(lane, field, value):
    payload = source_submission(lane).model_dump(mode="json", by_alias=True)
    payload["submitted_intent_v2"]["primary_work"][field] = value
    with pytest.raises(ValidationError, match="submitted Plan basis"):
        t.TurnSubmission.model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("object_revision", 2), ("revision_n", 2),
    ("content_sha256", "f" * 64), ("work_revision_id", str(uuid4())),
])
def test_source_submission_rejects_changed_resolved_provenance(lane, field, value):
    payload = source_submission(lane).model_dump(mode="json", by_alias=True)
    payload["provenance"]["primary_work"][field] = value
    with pytest.raises(ValidationError, match="resolved provenance"):
        t.TurnSubmission.model_validate(payload)


def source_turn(submission):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return t.Turn(turn_id=uuid4(), conversation_id=submission.conversation_id, world_id=submission.world_id,
        idempotency_key=submission.idempotency_key, sequence=1, revision=1, status="running",
        user_text=submission.user_text, assistant_text=None, failure_code=None,
        provenance=submission.provenance, submitted_intent_fingerprint_v2=t.submitted_turn_intent_fingerprint_v2(submission.submitted_intent_v2),
        graph_context_receipt=submission.graph_context_receipt, graph_context_execution=submission.graph_context_execution,
        attempt=1, accepted_at=now, completed_at=None, updated_at=now)


def test_source_turn_reopens_without_manufactured_graph_authority(lane):
    turn = source_turn(source_submission(lane))
    assert t.Turn.model_validate_json(turn.model_dump_json(by_alias=True)) == turn
    payload = turn.model_dump(mode="json", by_alias=True)
    payload["status"] = "completed"
    with pytest.raises(ValidationError, match="validated completion"):
        t.Turn.model_validate(payload)
    payload["status"] = "running"
    payload["assistant_text"] = "Ungrounded answer"
    with pytest.raises(ValidationError, match="own validated answer"):
        t.Turn.model_validate(payload)


def source_decision_proof(turn, **changes):
    import json
    from hashlib import sha256
    from application_state.agent_conversation.plan_jev_decision import scope_digest
    from application_state.agent_conversation.jev_retrieval_contract import PlanSourceRetrievalDecisionInputV1, prepare_decision
    attempt_id = uuid4()
    values = dict(request_id=uuid4(), parent_attempt_id=attempt_id, scope_sha256=scope_digest(turn),
        question=turn.user_text, candidates=(), allowed_operations=("discover_more", "finish_retrieval"),
        source_authority_status="available", source_revision=turn.graph_context_receipt.source_authority.revision_id,
        graph_revision=None)
    request = PlanSourceRetrievalDecisionInputV1(**(values | changes))
    prepared = prepare_decision(request)
    raw = json.dumps({"model": prepared.model, "state": prepared.state,
        "questions": {row.name: {"type": "choice", "instructions": row.question,
            "criteria": {option: None for option in row.options}} for row in prepared.questions}})
    auth = t.PlanJevProviderAuthorizedV1(kind="plan_jev_provider_authorized_v1", event_id=uuid4(), sequence=0,
        provider_attempt_id=attempt_id, decision_request_id=request.request_id,
        parent_request_sha256=request.digest, envelope_sha256=sha256(raw.encode()).hexdigest(),
        serializer_version="typesafe-sdk-json-v1", provider="typesafe", model="jev-1.14.0", api_mode="decision",
        tool_schema_sha256=t.canonical_sha256([]), input_accounting_kind="conservative_upper_bound",
        input_estimator="utf8_json_bytes_plus_64_per_node_v1", input_tokens=100, output_token_reserve=200,
        included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
        included_graph_event_ids=[], included_source_read_event_ids=[])
    return request, auth, {"parent_request_json": request.model_dump_json(by_alias=True), "request_json": raw}


def test_source_decision_proof_binds_actual_turn_and_distinct_capability_pins(lane):
    from application_state.agent_conversation.plan_jev_decision import verify_input, scope_digest
    turn = source_turn(source_submission(lane))
    request, auth, proof = source_decision_proof(turn)
    assert verify_input(turn, auth, proof) == request
    assert "graph_revision" not in proof["request_json"]
    assert request.source_revision not in proof["request_json"]
    other = t.Turn.model_validate(turn.model_dump(mode="python", by_alias=True) | {"turn_id": uuid4()})
    assert scope_digest(other) != scope_digest(turn)
    with pytest.raises(ValueError, match="owner/authorization"):
        verify_input(other, auth, proof)


@pytest.mark.parametrize("changes", [
    {"source_revision": "rev:another"}, {"graph_revision": "rev:invented"},
    {"source_authority_status": "unavailable", "source_revision": None},
    {"question": "A different question"},
])
def test_source_decision_refuses_rebound_proof_even_with_valid_self_digests(lane, changes):
    from application_state.agent_conversation.plan_jev_decision import verify_input
    turn = source_turn(source_submission(lane))
    _, auth, proof = source_decision_proof(turn, **changes)
    with pytest.raises(ValueError, match="owner/authorization"):
        verify_input(turn, auth, proof)


def test_unavailable_source_plan_submission_preserves_ordinary_non_graph_owner(lane):
    submission = source_submission(lane, unavailable=True)
    assert submission.graph_context_receipt.source_authority.failure_code == "native_source_head_unavailable"
    assert source_turn(submission).graph_context_execution.policy.source_read_scope is None


def test_source_submission_cannot_invent_playable_target_provenance(lane):
    payload = source_submission(lane).model_dump(mode="json", by_alias=True)
    payload["provenance"]["supporting_work"] = [t.encode_plan_playable_target_reference(
        t.PlanPlayableTargetReceiptV1(schema="dmb_plan_playable_target_receipt_v1", kind="scene",
            id="scene:other", marker_grammar_version="v2")).model_dump(mode="json")]
    with pytest.raises(ValidationError, match="target differs"):
        t.TurnSubmission.model_validate(payload)


def test_stored_source_turn_cannot_move_to_another_world(lane):
    turn = source_turn(source_submission(lane))
    payload = turn.model_dump(mode="json", by_alias=True) | {"world_id": "another"}
    with pytest.raises(ValidationError, match="Source-capable Plan lifecycle"):
        t.Turn.model_validate(payload)


@pytest.mark.parametrize("unavailable", [False, True])
def test_source_turn_persists_claim_failure_and_exact_replay(application_state_dsn, lane, unavailable):
    from application_state.agent_conversation import AgentConversationService
    from tests.application_state.test_agent_conversation_postgres import _new
    service = AgentConversationService()
    conversation = _new(service, "managed")
    value = source_submission(lane, unavailable=unavailable).model_dump(mode="python", by_alias=True)
    value["conversation_id"] = conversation.conversation_id
    submission = t.TurnSubmission.model_validate(value)
    accepted = service.accept_turn(submission)
    receipt_bytes = accepted.graph_context_receipt.model_dump_json(by_alias=True)
    reopened = AgentConversationService().list_turns("managed", conversation.conversation_id)[0]
    assert reopened == accepted
    assert type(reopened.graph_context_execution) is t.PlanSourceExecutionV1
    assert service.accept_turn(submission) == accepted
    claimed = service.claim_turn("managed", conversation.conversation_id, accepted.turn_id,
        expected_revision=accepted.revision).turn
    failed = service.fail_turn(t.TurnFailure(world_id="managed", conversation_id=conversation.conversation_id,
        turn_id=claimed.turn_id, expected_revision=claimed.revision, failure_code="synthetic_source_unavailable"))
    reopened = AgentConversationService().list_turns("managed", conversation.conversation_id)[0]
    assert reopened == failed and reopened.status == "failed"
    assert reopened.graph_context_receipt.model_dump_json(by_alias=True) == receipt_bytes
    assert service.reconcile_turn("managed", submission.idempotency_key, submission.submitted_intent_v2) == reopened


@pytest.mark.parametrize("mutation", ["receipt", "execution", "unknown_event"])
def test_source_sql_pair_cannot_fall_through_historical_checks(application_state_dsn, lane, mutation):
    import psycopg
    from psycopg.errors import CheckViolation
    from application_state.agent_conversation import AgentConversationService
    from tests.application_state.test_agent_conversation_postgres import _new
    service = AgentConversationService()
    conversation = _new(service, "managed")
    value = source_submission(lane).model_dump(mode="python", by_alias=True)
    value["conversation_id"] = conversation.conversation_id
    turn = service.accept_turn(t.TurnSubmission.model_validate(value))
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(CheckViolation):
            if mutation == "receipt":
                conn.execute("UPDATE agent.turn SET graph_context_receipt=jsonb_set(graph_context_receipt, '{schema}', '\"legacy:invented\"'::jsonb) WHERE turn_id=%s", (turn.turn_id,))
            elif mutation == "execution":
                conn.execute("UPDATE agent.turn SET graph_context_execution=jsonb_set(graph_context_execution, '{schema}', '\"legacy:invented\"'::jsonb) WHERE turn_id=%s", (turn.turn_id,))
            else:
                conn.execute("UPDATE agent.turn SET graph_context_execution=jsonb_set(graph_context_execution, '{events}', '[{\"kind\":\"corpus_source_search_authorized_v1\"}]'::jsonb) WHERE turn_id=%s", (turn.turn_id,))
    assert AgentConversationService().list_turns("managed", conversation.conversation_id)[0] == turn


@pytest.mark.parametrize("changed_accounting", [False, True])
def test_actual_ge_source_plan_dispatch_is_durable_before_synthetic_wire(application_state_dsn, lane, changed_accounting):
    import asyncio
    import json
    from uuid import UUID
    import httpx2
    from generationengine import GenerationEngineError
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision, validate_prepared_requested_work
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV3
    from application_state.agent_conversation.plan_jev_decision import scope_digest
    from application_state.errors import ApplicationStateValidationError
    from apps.live_control_server.services.agent_turn_service import _json_node_count
    from apps.live_control_server.services.plan_jev_dispatch import decision_client
    from tests.application_state.test_agent_conversation_postgres import _new
    from tests.test_native_corpus_source_access import BODY
    service = AgentConversationService()
    conversation = _new(service, "managed")
    submission = source_submission(lane)
    parent = PlanRequestedWorkInputV3(request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256="a" * 64,
        question=submission.user_text, page_title="Synthetic Plan", target_available=False,
        original_capture=None, placement_catalog=None)
    state = {"turn": None, "parent": parent, "auth": None, "sent": [], "rejection": None}

    async def authorize(prepared):
        validate_prepared_requested_work(state["parent"], prepared)
        raw = prepared.body.decode()
        estimate = len(prepared.body) + 64 * (1 + _json_node_count(json.loads(raw)))
        value = submission.model_dump(mode="json", by_alias=True)
        value["conversation_id"] = str(conversation.conversation_id)
        receipt = value["graph_context_receipt"]
        receipt["assembled_input"].update(assembled_input_sha256=prepared.body_sha256,
            provider_envelope_input_tokens=estimate, context_window_limit=32000)
        value["graph_context_receipt"] = rehash(receipt)
        execution = value["graph_context_execution"]
        execution["context_receipt_sha256"] = receipt["context_receipt_sha256"]
        execution["execution_policy_sha256"] = t.canonical_sha256({key: execution[key]
            for key in ("schema", "context_receipt_sha256", "policy")})
        accepted = service.accept_turn(t.TurnSubmission.model_validate_json(json.dumps(value)))
        turn = service.claim_turn("managed", conversation.conversation_id, accepted.turn_id,
            expected_revision=accepted.revision).turn
        state["parent"] = state["parent"].model_copy(update={"parent_attempt_id": UUID(prepared.attempt_id),
            "scope_sha256": scope_digest(turn)})
        auth = t.PlanRequestedWorkAuthorizedV2(kind="plan_requested_work_authorized_v2", event_id=uuid4(), sequence=0,
            provider_attempt_id=UUID(prepared.attempt_id), decision_request_id=parent.request_id,
            parent_request_sha256=state["parent"].digest, envelope_sha256=prepared.body_sha256,
            serializer_version="typesafe-sdk-json-v1", provider="typesafe", model="jev-1.14.0", api_mode="decision",
            tool_schema_sha256=t.canonical_sha256([]), input_accounting_kind="conservative_upper_bound",
            input_estimator="utf8_json_bytes_plus_64_per_node_v1", input_tokens=estimate + int(changed_accounting),
            output_token_reserve=200, included_assertion_ids=[], included_relationship_ids=[],
            included_evidence_ref_ids=[], included_graph_event_ids=[], included_source_read_event_ids=[])
        state["turn"], state["auth"] = turn, auth
        try:
            state["turn"], _ = service.authorize_plan_jev_provider("managed", conversation.conversation_id, turn.turn_id,
                expected_revision=turn.revision, expected_attempt=turn.attempt, authorization=auth,
                producer_proof={"parent_request_json": state["parent"].model_dump_json(by_alias=True), "request_json": raw})
        except ApplicationStateValidationError as exc:
            state["rejection"] = str(exc)
            raise
        return True

    async def record(event):
        if state["rejection"] is not None:
            assert event.outcome == "known_not_sent"
            return True  # No durable provider authorization exists to settle.
        transition = {"sending": "sdk_entered", "response_received": "response_received"}[event.outcome]
        turn = state["turn"]
        state["turn"], _ = service.record_provider_outcome("managed", conversation.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events), provider_attempt_id=state["auth"].provider_attempt_id,
                outcome=transition))
        return True

    class Wire(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            state["sent"].append(request)
            raw = request.content.decode()
            assert BODY not in raw and "revision_id" not in raw and "native_world_id" not in raw
            durable = AgentConversationService().list_turns("managed", conversation.conversation_id)[0]
            assert durable.graph_context_execution.events[-1].outcome == "sdk_entered"
            body = json.loads(raw)
            options = body["questions"]["requested_work"]["criteria"]
            return httpx2.Response(200, request=request, json={"model": "jev-1.14.0",
                "usage": {"input_tokens": 42, "output_tokens": 3}, "answers": {"requested_work": {
                    "type": "choice", "choice": "discuss", "confidence": 1,
                    "probabilities": {key: float(key == "discuss") for key in options}}}})

    async def run():
        client = decision_client(authorize=authorize, record=record, transport=Wire(), api_key="synthetic-test-key")
        try:
            return await client.decide(prepare_requested_work_decision(parent))
        finally:
            await client.aclose()
    if changed_accounting:
        # GE must not send after durable authorization refuses the first envelope.
        with pytest.raises(GenerationEngineError):
            asyncio.run(run())
        assert "first provider authorization" in state["rejection"]
        assert not state["sent"]
        assert not AgentConversationService().list_turns("managed", conversation.conversation_id)[0].graph_context_execution.events
    else:
        assert asyncio.run(run()).answers["requested_work"].selected == "discuss"
        reopened = AgentConversationService().list_turns("managed", conversation.conversation_id)[0]
        assert len(state["sent"]) == 1 and reopened == state["turn"]
        assert [e.kind for e in reopened.graph_context_execution.events] == [
            "plan_requested_work_authorized_v2", "provider_outcome", "provider_outcome"]


@pytest.mark.parametrize("kind", ["corpus_source_search_authorized_v1", "native_source_section_observed_v1", "build_section_read_authorized_v1"])
def test_source_execution_rejects_obsolete_or_foreign_materializers(kind):
    payload = source_execution().model_dump(mode="json", by_alias=True)
    payload["events"] = [{"kind": kind}]
    with pytest.raises(ValidationError, match="union_tag_invalid"):
        t.PlanSourceExecutionV1.model_validate(payload)


def source_with_graph_submission(lane):
    import json
    from tests.application_state.test_agent_conversation_postgres import _graph_receipt
    submission = source_submission(lane)
    payload = submission.model_dump(mode="json", by_alias=True)
    receipt = payload["graph_context_receipt"]
    source = receipt["source_authority"]
    graph = _graph_receipt("managed", uuid4()).model_dump(mode="json", by_alias=True)
    graph["plan_basis"] = receipt["plan_basis"]
    graph["graph_authority"].update(native_world_id=source["native_world_id"], binding_version=source["binding_version"])
    graph.pop("context_receipt_sha256")
    graph["context_receipt_sha256"] = t.canonical_sha256(graph)
    receipt["graph_capability"] = graph
    payload["graph_context_receipt"] = rehash(receipt)
    execution = payload["graph_context_execution"]
    execution["context_receipt_sha256"] = receipt["context_receipt_sha256"]
    execution["policy"]["allowed_graph_operations"] = ["object"]
    execution["policy"]["source_read_scope"] = dict(retrieval_session_id="actual-classic-session",
        world_id="managed", campaign_id=None, graph_revision=graph["graph_authority"]["graph_revision"], admitted_anchors=[])
    execution["policy"] = t.PlanSourceExecutionPolicyV1.model_validate(execution["policy"]).model_dump(mode="json", by_alias=True)
    execution["execution_policy_sha256"] = t.canonical_sha256({key: execution[key]
        for key in ("schema", "context_receipt_sha256", "policy")})
    return t.TurnSubmission.model_validate_json(json.dumps(payload))


def test_source_with_genuine_graph_capability_persists_distinct_revisions(application_state_dsn, lane):
    from application_state.agent_conversation import AgentConversationService
    from tests.application_state.test_agent_conversation_postgres import _new
    service = AgentConversationService()
    conversation = _new(service, "managed")
    submission = source_with_graph_submission(lane)
    submission = t.TurnSubmission.model_validate(submission.model_dump(mode="python", by_alias=True) | {
        "conversation_id": conversation.conversation_id})
    accepted = service.accept_turn(submission)
    reopened = AgentConversationService().list_turns("managed", conversation.conversation_id)[0]
    assert reopened == accepted
    receipt = reopened.graph_context_receipt
    assert receipt.source_authority.revision_id != receipt.graph_capability.graph_authority.graph_revision
    assert require_graph(receipt) == receipt.graph_capability


@pytest.mark.parametrize("field,value", [("native_world_id", "foreign"), ("binding_version", 999)])
def test_source_and_graph_cannot_combine_different_world_bindings(lane, field, value):
    import json
    payload = source_with_graph_submission(lane).graph_context_receipt.model_dump(mode="json", by_alias=True)
    graph = payload["graph_capability"]
    graph["graph_authority"][field] = value
    graph.pop("context_receipt_sha256")
    graph["context_receipt_sha256"] = t.canonical_sha256(graph)
    with pytest.raises(ValidationError, match="managed/native World binding"):
        t.PlanSourceContextReceiptV1.model_validate_json(json.dumps(rehash(payload)))
