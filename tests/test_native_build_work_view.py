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
    evidence = SimpleNamespace(variant_format=variant_format, frame={"answer_policy": "fixture"})
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
