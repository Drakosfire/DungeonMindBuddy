"""Projection unit checks; actual SDK/admission qualification remains separate."""
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from application_state.agent_conversation.native_build_work_view import (
    semantic_frame, selection_aliases, resolve_selectors,
)
from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA


def example():
    read, draft = str(uuid4()), str(uuid4())
    host = {'schema': NATIVE_WORK_SCHEMA, 'source_basis': {'document_id': 'host-page', 'visibility': 'internal'},
        'artifact_under_edit': {'policy': 'host-policy', 'role': 'host-role',
            'sections': [{'read_id': read, 'line_start': 1, 'line_end': 2,
                'text_ref': 'working_draft_context'}]},
        'working_draft_context': {'record_id': draft, 'snapshot_sha256': 'a'*64,
            'policy': 'host-policy', 'role': 'host-role', 'draft_markdown': 'Exact source\nquote.'}}
    return host, SimpleNamespace(policy=SimpleNamespace(action=None), events=[])


def test_local_source_and_draft_selectors_preserve_exact_single_body():
    host, execution = example()
    view = semantic_frame(host, execution)['build_work']
    assert view['current_draft']['markdown'] == host['working_draft_context']['draft_markdown']
    assert view['saved_sections'][0]['body_ref'] == 'current_draft'
    assert 'text' not in view['saved_sections'][0]
    wire = json.dumps(view)
    assert host['artifact_under_edit']['sections'][0]['read_id'] not in wire
    assert host['working_draft_context']['record_id'] not in wire
    assert 'snapshot_sha256' not in wire and 'host-policy' not in wire


def test_only_selector_slots_are_resolved_and_foreign_choices_refused():
    host, _ = example()
    identity = host['artifact_under_edit']['sections'][0]['read_id']
    alias = selection_aliases(host)[identity]
    row = {'text': alias, 'supporting_quotes': [alias], 'section_read_ids': [alias]}
    result = resolve_selectors(row, host)
    assert result == row | {'section_read_ids': [identity]}
    with pytest.raises(ValueError, match='Unknown Build'):
        resolve_selectors({'read_id': identity}, host)


def test_unknown_work_fields_require_classification():
    host, execution = example()
    with pytest.raises(ValueError, match='Unclassified'):
        semantic_frame(host | {'future_owner_field': 'unexpected'}, execution)


@pytest.mark.parametrize('digest', [None, '', 'not-a-digest'])
def test_build_authorization_requires_a_valid_complete_work_commitment(digest):
    from pydantic import ValidationError
    from application_state.agent_conversation.native_execution import NativeBuildWriterAuthorizedV2
    from tests.test_surface_native_execution import component, native_writer
    _, root = component('build')
    old = native_writer('build', root.policy, sequence=0)
    data = old.model_dump(mode='json', by_alias=True)
    data['kind'] = 'native_build_writer_authorized_v2'
    data['work_frame_sha256'] = digest
    with pytest.raises(ValidationError):
        NativeBuildWriterAuthorizedV2.model_validate_json(json.dumps(data))


def test_build_authorization_cannot_be_relabelled_as_a_plan_writer():
    from pydantic import ValidationError
    from application_state.agent_conversation.native_execution import NativeBuildWriterAuthorizedV2
    from tests.test_surface_native_execution import component, native_writer, execution
    context, root = component('plan')
    old = native_writer('plan', root.policy, sequence=0)
    data = old.model_dump(mode='json', by_alias=True) | {
        'kind': 'native_build_writer_authorized_v2', 'work_frame_sha256': 'a'*64}
    event = NativeBuildWriterAuthorizedV2.model_validate_json(json.dumps(data))
    with pytest.raises(ValidationError, match='Build work authorization cannot'):
        execution(context.context_receipt_sha256, root.policy, [event])


def _committed_related_case():
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import NativeBuildWriterAuthorizedV2
    from application_state.agent_conversation.native_writer import model_work_frame
    from tests.test_surface_native_related_pages import case
    from tests.test_surface_native_work_input import produce
    from tests.test_surface_native_completion import answer
    from tests.test_surface_native_execution import execution
    context, record, work = case()
    host = model_work_frame(context, record, **work)
    def project(value):
        view = semantic_frame(value, record)
        value.clear()
        value.update(view)
    stored, old, proof, _ = produce(context, record, work, mutate=project,
        candidate=answer([{'kind': 'discussion', 'text': 'No related claim selected.'}]))
    auth = NativeBuildWriterAuthorizedV2.model_validate_json(json.dumps(
        old.model_dump(mode='json', by_alias=True) | {
            'kind': 'native_build_writer_authorized_v2',
            'work_frame_sha256': t.canonical_sha256(host)}))
    stored = execution(context.context_receipt_sha256, stored.policy,
        [auth if e.event_id == auth.event_id else e for e in stored.events])
    return context, stored, auth, proof, work


def test_unused_related_read_mapping_is_committed_before_alias_resolution():
    from application_state.agent_conversation import build_related_pages as related
    from application_state.agent_conversation.native_writer import verify_input_records
    from tests.test_surface_native_execution import execution
    context, stored, auth, proof, work = _committed_related_case()
    verify_input_records(context, stored, auth, proof['prepared_request_json'], **work)
    read = next(e for e in stored.events if isinstance(e, related.RelatedPageRead))
    from uuid import UUID
    altered = read.model_copy(update={'read_id': UUID(int=read.read_id.int ^ 1)})
    mutated = execution(context.context_receipt_sha256, stored.policy,
        [altered if e.event_id == read.event_id else e for e in stored.events])
    with pytest.raises(ValueError, match='complete work commitment'):
        verify_input_records(context, mutated, auth, proof['prepared_request_json'], **work)


def test_semantic_build_carrier_cannot_downgrade_to_historical_authorization():
    from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1
    from application_state.agent_conversation.native_writer import verify_input_records
    from tests.test_surface_native_execution import execution
    context, stored, auth, proof, work = _committed_related_case()
    data = auth.model_dump(mode='json', by_alias=True)
    data.pop('work_frame_sha256')
    data['kind'] = 'native_writer_authorized_v1'
    old = NativeWriterAuthorizedV1.model_validate_json(json.dumps(data))
    downgraded = execution(context.context_receipt_sha256, stored.policy,
        [old if e.event_id == auth.event_id else e for e in stored.events])
    with pytest.raises(ValueError, match='complete authorization commitment'):
        verify_input_records(context, downgraded, old, proof['prepared_request_json'], **work)


@pytest.mark.parametrize('operation,schema,task', [
    ('propose_build_insertion','dmb_build_compose_input_v1','compose_current_page'),
    ('prepare_build_image','dmb_build_image_direction_input_v1','prepare_image_direction'),
])
@pytest.mark.parametrize('current_outer', [False, True])
def test_creative_carriers_refuse_mixed_work_generations(operation, schema, task, current_outer, monkeypatch):
    from application_state.agent_conversation.native_writer import _input_frames
    host, execution = example()
    from tests.test_surface_native_execution import component
    _, execution = component('build')
    monkeypatch.setattr('application_state.agent_conversation.build_intentional_response.selected_action',
        lambda _: SimpleNamespace(operation=operation))
    work = host if current_outer else semantic_frame(host, execution)
    packet = ({'task': task} if current_outer else {'schema': schema}) | {'surface_work': work}
    with pytest.raises(ValueError, match='mix historical and current'):
        _input_frames(json.dumps({'input': json.dumps(packet)}), execution, host['schema'])


def test_reopens_historical_draft_with_statblock_in_original_writer_format(monkeypatch):
    from hashlib import sha256
    from application_state.agent_conversation import build_primary_context
    from application_state.agent_conversation.native_build_work_view import VARIANT_WRITER_FORMAT

    host, execution = example()
    execution.policy.provider_roles = SimpleNamespace(writer=SimpleNamespace(model="fixture-writer"))
    host["response_contract"] = {
        "policy": "fixture", "requested_work": "draft_in_conversation", "intent_family": "discuss",
        "operation": "answer_from_sources", "purpose": "fulfill", "barrier": None,
        "barrier_detail": None, "capabilities": {}, "available_followups": [], "contract_sha256": "fixture",
    }
    definition = {"identity": {"name": "Fixture"}, "ruleset": {"name": "fixture-rules"}}
    host["saved_statblocks"] = [{"definition": definition}]
    monkeypatch.setattr(build_primary_context, "native_work_frame", lambda *_: host)

    historical = semantic_frame(host, execution)
    assert historical["build_work"]["saved_statblocks"] == [
        {"mechanics": {"identity": {"name": "Fixture"}}},
    ]
    assert "statblock_variant_guidance" not in historical["build_work"]
    current = semantic_frame(host, execution, include_variant=True)
    assert current["build_work"]["saved_statblocks"] == [
        {"mechanics": definition, "variant_source": "statblock0"},
    ]

    def body(frame, name):
        return json.dumps({
            "model": "fixture-writer",
            "input": [{"role": "user", "content": json.dumps(frame)}],
            "text": {"format": {"name": name}},
        })

    old_name = "surface_native_evidence_selectors_v2"
    from application_state.agent_conversation.native_build_work_view import VARIANT_EDITS_FORMAT

    edits = semantic_frame(host, execution, include_variant=True, variant_edits=True)
    assert "add_rules" in edits["build_work"]["statblock_variant_guidance"]
    for wire, name in [(historical, old_name), (current, VARIANT_WRITER_FORMAT), (edits, VARIANT_EDITS_FORMAT)]:
        raw = body(wire, name)
        assert build_primary_context.verify_native_work_input(
            execution, None, raw,
        ) == sha256(raw.encode()).hexdigest()
    with pytest.raises(ValueError, match="exact saved-work"):
        build_primary_context.verify_native_work_input(execution, None, body(current, old_name))


@pytest.mark.parametrize("variant_format, offered_field", [(False, True), (True, False)])
def test_variant_field_must_match_the_producing_writer_format(variant_format, offered_field):
    from application_state.agent_conversation.native_completion import normalize_candidate

    execution = SimpleNamespace(policy=SimpleNamespace(action=SimpleNamespace(surface_id="play")))
    evidence = SimpleNamespace(generic_limitations=False, variant_format=variant_format, frame={"answer_policy": "fixture"})
    candidate = {
        "schema": "fixture", "answer_segments": [], "limitations": [], "requested_detail_gaps": [],
    }
    if offered_field:
        candidate["statblock_variant"] = None
    with pytest.raises(ValueError, match="exact producing answer policy"):
        normalize_candidate(candidate, None, execution, None, evidence)


def test_statblock_rule_edits_preserve_unmentioned_mechanics():
    from application_state.agent_conversation.native_completion import _apply_statblock_rule_edits
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition().model_dump(mode="json")
    first = base["rule_elements"][0]
    addition = first | {"key": "new_rule", "costs": None}
    replacement = first | {"summary": "Explicit replacement", "costs": []}
    assembled = _apply_statblock_rule_edits(base, {
        "add_rules": [addition], "replace_rules": [replacement],
    })
    assert assembled == base | {"rule_elements": [replacement, *base["rule_elements"][1:], addition | {"costs": []}]}
    assert base == _definition().model_dump(mode="json")
    with pytest.raises(ValueError, match="key conflicts"):
        _apply_statblock_rule_edits(base, {"add_rules": [replacement], "replace_rules": []})
    with pytest.raises(ValueError, match="key conflicts"):
        _apply_statblock_rule_edits(base, {"add_rules": [], "replace_rules": [addition]})
    with pytest.raises(ValueError, match="key conflicts"):
        _apply_statblock_rule_edits(base, {"add_rules": [addition, addition], "replace_rules": []})


@pytest.mark.parametrize("usage_kind", ["manual", "once"])
def test_only_manual_single_self_reference_is_normalized_in_new_rules(usage_kind):
    from application_state.agent_conversation.native_completion import _apply_statblock_rule_edits
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition().model_dump(mode="json")
    first = base["rule_elements"][0]
    manual = first | {
        "key": "manual_truce", "automation_support": "manual",
        "usage": first["usage"] | {"kind": usage_kind, "uses": 1 if usage_kind == "once" else None},
        "mechanic": {"kind": "multiattack", "sequences": [
            {"element_key": "manual_truce", "count": 1, "choice_group": None},
        ]},
    }
    sequence = manual | {"key": "sequence", "mechanic": {
        "kind": "multiattack", "sequences": [
            {"element_key": first["key"], "count": 2, "choice_group": None},
        ],
    }}
    result = _apply_statblock_rule_edits(base, {"add_rules": [manual, sequence], "replace_rules": []})
    assert result == base | {"rule_elements": [
        *base["rule_elements"],
        manual | {"mechanic": {"kind": "human_adjudicated", "adjudication_tags": []}},
        sequence,
    ]}
    assert manual["mechanic"]["kind"] == "multiattack"


def test_variant_format_with_visible_reply_rejects_empty_segments_at_completion(monkeypatch):
    from application_state.agent_conversation.native_completion import normalize_candidate

    from application_state.agent_conversation import build_intentional_response

    monkeypatch.setattr(build_intentional_response, "native_review_enabled", lambda _: True)
    execution = SimpleNamespace(policy=SimpleNamespace(action=SimpleNamespace(surface_id="build")))
    evidence = SimpleNamespace(
        generic_limitations=False, variant_format=True, variant_visible_reply=True, frame={"answer_policy": "fixture"},
        work_frame={},
    )
    candidate = {
        "schema": "fixture", "answer_segments": [], "limitations": [],
        "requested_detail_gaps": [], "statblock_variant": None, "collaboration": {},
    }
    with pytest.raises(ValueError, match="requires a visible reply"):
        normalize_candidate(candidate, None, execution, None, evidence)


@pytest.mark.parametrize(
    ("quotes", "valid"),
    [
        (["Only after the bell."], True),
        ([], True),
        (["Only before the bell."], False),
        (["bell"], False),
    ],
)
def test_variant_witness_binds_unique_authored_clause_to_containing_rule(quotes, valid):
    from application_state.agent_conversation.native_completion import normalize_statblock_variant
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition().model_dump(mode="json")
    work = {
        "response_contract": {"requested_work": "draft_in_conversation", "operation": "answer_from_sources"},
        "saved_statblocks": [{"event_id": "4c63e929-fcec-4d8a-b787-4f908b3ce857", "definition": base}],
        "working_draft_context": {"draft_markdown": "Only after the bell. The bell falls silent."},
    }
    added = base["rule_elements"][0] | {"key": "truce"}
    proposal = {
        "source": "statblock0",
        "add_rules": [{"authored_quotes": quotes, "rule": added}],
        "replace_rules": [],
    }
    if not valid:
        with pytest.raises(ValueError, match="witness must identify exact authored text"):
            normalize_statblock_variant({"statblock_variant": proposal}, work,
                                        variant_edits=True, variant_witnesses=True)
    else:
        result = normalize_statblock_variant({"statblock_variant": proposal}, work,
                                             variant_edits=True, variant_witnesses=True)
        assert result.definition.model_dump()["rule_elements"][-1] == added


def test_carried_condition_binds_identical_text_to_playable_trigger_and_display():
    from application_state.agent_conversation.native_completion import _unwrap_witnessed_edits

    clause = "The gate opens only after the second bell."
    effect = "The guard steps aside."
    row = {
        "carried_condition": clause,
        "authored_quotes": [],
        "rule": {
            "activation": {"trigger": {"condition_text": "After a bell."}},
            "rules_text": effect,
        },
    }
    assembled, = _unwrap_witnessed_edits([row], clause, carried_condition=True)
    assert assembled["activation"]["trigger"]["condition_text"] == clause
    assert assembled["rules_text"] == f"{clause}\n\n{effect}"
    assert row["rule"]["rules_text"] == effect
    for bad_source in ("", f"{clause}\n{clause}"):
        with pytest.raises(ValueError, match="exact authored text"):
            _unwrap_witnessed_edits([row], bad_source, carried_condition=True)
    with pytest.raises(ValueError, match="requires a typed trigger"):
        _unwrap_witnessed_edits([row | {"rule": {"rules_text": effect}}], clause, carried_condition=True)


@pytest.mark.parametrize("review", [
    {"p1": "retain"},
    {"p1": "retain", "p2": "ignore"},
    {"p1": "retain", "p2": "omit", "p3": "retain"},
])
def test_variant_review_requires_every_exact_draft_handle(review):
    from application_state.agent_conversation.native_completion import normalize_statblock_variant

    work = {"working_draft_context": {"draft_markdown": "One.\r\n\r\nTwo."}}
    candidate = {"statblock_variant": {
        "passage_review": review, "source": "statblock0", "add_rules": [], "replace_rules": [],
    }}
    with pytest.raises(ValueError, match="review every offered draft passage"):
        normalize_statblock_variant(candidate, work, variant_edits=True, variant_passage_review=True)


def test_variant_passages_keep_exact_text_order_and_ignore_blank_separators():
    from application_state.agent_conversation.native_build_work_view import variant_draft_passages, variant_output_version

    work = {"working_draft_context": {"draft_markdown": "First.\r\n\t\r\n  Second.\n\nThird.\n"}}
    assert variant_draft_passages(work) == {"p1": "First.", "p2": "  Second.", "p3": "Third.\n"}
    assert variant_output_version(work) == 11
    assert variant_output_version({}) == 8


@pytest.mark.parametrize("drift", [None, "unbound", "omitted", "timing", "dependency"])
def test_retained_trigger_has_exact_binding_and_no_added_prerequisites(drift):
    from application_state.agent_conversation.native_completion import _validate_retained_trigger_bindings

    exact = "The gate opens only after the second bell."
    passages = {"p1": exact, "p2": "The guards stand aside."}
    activation = {
        "timing_text": "After a deal." if drift == "timing" else None,
        "trigger": {"source_element_key": "deal" if drift == "dependency" else None},
    }
    candidate = {
        "passage_review": {"p1": "omit" if drift == "unbound" else "retain_trigger", "p2": "retain"},
        "add_rules": [{"carried_condition": None if drift == "omitted" else exact,
                       "rule": {"activation": activation}}],
        "replace_rules": [],
    }
    if drift is None:
        _validate_retained_trigger_bindings(candidate, passages)
    else:
        with pytest.raises(ValueError, match="[Tt]rigger"):
            _validate_retained_trigger_bindings(candidate, passages)


def test_retained_v9_passage_disposition_keeps_its_completion_contract():
    from application_state.agent_conversation.native_completion import normalize_statblock_variant
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition().model_dump(mode="json")
    exact = "The gate opens only after the second bell."
    work = {
        "response_contract": {"requested_work": "draft_in_conversation", "operation": "answer_from_sources"},
        "saved_statblocks": [{"event_id": "4c63e929-fcec-4d8a-b787-4f908b3ce857", "definition": base}],
        "working_draft_context": {"draft_markdown": exact},
    }
    proposal = {
        "source": "statblock0",
        "passage_review": {"p1": "retain"},
        "add_rules": [{
            "authored_quotes": [], "carried_condition": None,
            "rule": base["rule_elements"][0] | {"key": "truce"},
        }],
        "replace_rules": [],
    }
    options = dict(variant_edits=True, variant_witnesses=True,
                   variant_carried_condition=True, variant_passage_review=True)
    normalize_statblock_variant({"statblock_variant": proposal}, work, **options)

    proposal["passage_review"]["p1"] = "retain_trigger"
    with pytest.raises(ValueError, match="review every offered draft passage"):
        normalize_statblock_variant({"statblock_variant": proposal}, work, **options)
    with pytest.raises(ValueError, match="requires a carried condition"):
        normalize_statblock_variant(
            {"statblock_variant": proposal}, work, variant_trigger_retention=True, **options,
        )

@pytest.mark.parametrize(
    ("handle", "valid"),
    [("p1", True), ("p2", False), ("p3", False), ("Only after the bell.", False)],
)
def test_variant_passage_witness_selects_exact_position_even_if_text_repeats(handle, valid):
    from application_state.agent_conversation.native_completion import normalize_statblock_variant
    from tests.test_statblock_acceptance_reconciliation import _definition

    base = _definition().model_dump(mode="json")
    work = {
        "response_contract": {"requested_work": "draft_in_conversation", "operation": "answer_from_sources"},
        "saved_statblocks": [{"event_id": "4c63e929-fcec-4d8a-b787-4f908b3ce857", "definition": base}],
        "working_draft_context": {"draft_markdown": "Only after the bell.\n\nOnly after the bell."},
    }
    added = base["rule_elements"][0] | {"key": "truce"}
    candidate = {"statblock_variant": {
        "source": "statblock0", "passage_review": {"p1": "retain", "p2": "omit"},
        "add_rules": [{"authored_passages": [handle], "carried_condition": None, "rule": added}],
        "replace_rules": [],
    }}
    flags = dict(variant_edits=True, variant_witnesses=True, variant_carried_condition=True,
                 variant_passage_review=True, variant_trigger_retention=True, variant_passage_witnesses=True)
    if not valid:
        with pytest.raises(ValueError, match="offered, non-omitted passage"):
            normalize_statblock_variant(candidate, work, **flags)
    else:
        result = normalize_statblock_variant(candidate, work, **flags)
        assert result.definition.model_dump()["rule_elements"][-1] == added
