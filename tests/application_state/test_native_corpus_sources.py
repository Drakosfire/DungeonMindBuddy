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
    policy = source_policy(t.canonical_sha256(receipt.source_authority.model_dump(mode="json")))
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
