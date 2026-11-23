"""Reference-aware Plan uses its real authenticated/native/writer boundaries."""
import pytest
from tests.test_native_plan_assertions import lane as lane, _ordinary_native_case
from tests.application_state.test_native_plan_statements import native_read_admission_probes as native_read_admission_probes


@pytest.mark.parametrize('authoring',[False,True])
def test_plan_human_object_is_required_without_model_selection(lane,tmp_path,monkeypatch,native_read_admission_probes,authoring):
    _ordinary_native_case(lane,tmp_path,monkeypatch,True,False,None,None,False,
        native_read_admission_probes,authoring=authoring,authored=True)


@pytest.mark.parametrize('selection',['section','full_document','source_only'])
def test_plan_human_source_reaches_writer_and_exact_citation_without_object_dependency(lane,tmp_path,monkeypatch,native_read_admission_probes,selection):
    _ordinary_native_case(lane,tmp_path,monkeypatch,True,False,None,None,False,
        native_read_admission_probes,authored=True,authored_source=selection)


@pytest.mark.parametrize('field',['content_sha256','section_id','source_revision_id'])
def test_plan_exact_source_refusal_retains_input_and_never_reaches_writer(lane,tmp_path,monkeypatch,native_read_admission_probes,field):
    _ordinary_native_case(lane,tmp_path,monkeypatch,True,False,None,'selected_source_'+field,False,
        native_read_admission_probes,authored=True,authored_source='section')


@pytest.mark.parametrize('mutation',['foreign_world','play_surface','empty','without_native_policy'])
def test_plan_reference_input_requires_its_actual_surface_world_and_policy(mutation):
    from pydantic import ValidationError
    from tests.test_agent_turn_service import _pinned_plan_request
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    original=_pinned_plan_request().model_dump(mode='json',by_alias=True)
    world=original['owner_scope']['world_id']
    original['plan_context_policy']={'schema':'dmb_plan_context_policy_v2','policy':'auto_plan_world','graph_source':'reviewed_native_graph'}
    original['graph_request']={'mode':'none'}
    original['authored_references']={'schema':'dmb_authored_references_v2','references':[{
        'schema':'dmb_authored_graph_reference_v1','managed_world_id':world,'native_world_id':'native',
        'binding_version':1,'graph_revision':'revision','node_id':'node','label':'Selection'}]}
    AgentTurnRequest.model_validate(original)
    if mutation=='foreign_world':original['authored_references']['references'][0]['managed_world_id']='foreign'
    elif mutation=='play_surface':original['surface']['surface_id']='play'
    elif mutation=='empty':original['authored_references']['references']=[]
    else:original['plan_context_policy']=None
    with pytest.raises(ValidationError):AgentTurnRequest.model_validate(original)


def test_plan_human_object_keeps_unavailable_support_partial(lane,tmp_path,monkeypatch,native_read_admission_probes):
    _ordinary_native_case(lane,tmp_path,monkeypatch,True,True,None,None,False,
        native_read_admission_probes,authored=True)


@pytest.mark.parametrize('authoring',[False,True])
@pytest.mark.parametrize('with_references',[False,True])
def test_explicit_plan_operation_uses_native_sdk_writer_and_retained_history(
        lane,tmp_path,monkeypatch,native_read_admission_probes,authoring,with_references):
    _ordinary_native_case(lane,tmp_path,monkeypatch,True,False,None,None,False,
        native_read_admission_probes,authoring=authoring,authored=with_references,
        plan_operation='write_current_page' if authoring else 'discuss')


@pytest.mark.parametrize('mutation',['play_surface','without_native_policy','invalid_operation'])
def test_explicit_plan_operation_rejects_wrong_scope_or_contract(mutation):
    from pydantic import ValidationError
    from tests.test_agent_turn_service import _pinned_plan_request
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    original=_pinned_plan_request().model_dump(mode='json',by_alias=True)
    original.update(plan_requested_operation='discuss',graph_request={'mode':'none'},
        plan_context_policy={'schema':'dmb_plan_context_policy_v2','policy':'auto_plan_world','graph_source':'reviewed_native_graph'})
    AgentTurnRequest.model_validate(original)
    if mutation=='play_surface':
        original['surface']['surface_id']='play'
    elif mutation=='without_native_policy':
        original['plan_context_policy']=None
    else:
        original['plan_requested_operation']='save'
    with pytest.raises(ValidationError):
        AgentTurnRequest.model_validate(original)


def test_explicit_operation_changes_frozen_intent_fingerprint():
    from tests.test_agent_turn_service import _pinned_plan_request
    from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
    from application_state.agent_conversation.types import submitted_turn_intent_fingerprint_v2
    request=_pinned_plan_request()
    raw=request.model_dump(mode='json',by_alias=True)
    raw.update(graph_request={'mode':'none'},plan_context_policy={
        'schema':'dmb_plan_context_policy_v2','policy':'auto_plan_world','graph_source':'reviewed_native_graph'})
    intents=[_submitted_turn_intent(type(request).model_validate(raw | {'plan_requested_operation':operation}),
        world_id=raw['owner_scope']['world_id']) for operation in ('discuss','write_current_page')]
    assert len({submitted_turn_intent_fingerprint_v2(intent) for intent in intents})==2


def test_ordinary_plan_reads_saved_worldbuilding_and_reopens_exact_capture(
        lane,tmp_path,monkeypatch,native_read_admission_probes):
    _ordinary_native_case(lane,tmp_path,monkeypatch,False,False,None,None,False,
        native_read_admission_probes,related_page=True)


@pytest.mark.parametrize('mixed',[False,True])
def test_plan_new_page_uses_saved_worldbuilding_origin_and_existing_reviewed_publication(
        lane,tmp_path,monkeypatch,native_read_admission_probes,mixed):
    result=_ordinary_native_case(lane,tmp_path,monkeypatch,False,False,None,None,mixed,
        native_read_admission_probes,connected_review=True)
    assert result['confirmed']['phase']=='complete'


@pytest.mark.parametrize('mutation',['alias','quote','kind'])
def test_plan_new_page_rejects_unincluded_origin_or_other_collaboration(
        lane,tmp_path,monkeypatch,native_read_admission_probes,mutation):
    _ordinary_native_case(lane,tmp_path,monkeypatch,False,False,None,None,False,
        native_read_admission_probes,connected_review=True,connected_mutation=mutation)


@pytest.mark.parametrize('mutation', ['formatted_prose', 'metadata_rich', 'foreign', 'world_alias', 'quote_field'])
def test_plan_supplied_page_references_keep_formatting_free_and_reject_unbound_output(
        lane, tmp_path, monkeypatch, native_read_admission_probes, mutation):
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, None, False,
        native_read_admission_probes, related_page=True, related_output_mutation=mutation)


def test_fresh_plan_refuses_retired_page_quote_contract_before_writer_io(
        lane, tmp_path, monkeypatch, native_read_admission_probes):
    from application_state.agent_conversation import native_plan_work_view
    historical_view = native_plan_work_view.semantic_frame

    def retired_view(host, execution, **kwargs):
        return historical_view(host, execution, supplied_source_references=False)

    monkeypatch.setattr(native_plan_work_view, 'semantic_frame', retired_view)
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, 'retired_page_quotes', False,
        native_read_admission_probes, related_page=True)


@pytest.mark.parametrize('mutation', ['old_format', 'missing_prose_policy', 'forged_json_policy'])
def test_plan_recomputed_sdk_packet_cannot_forge_source_reference_contract(
        lane, tmp_path, monkeypatch, native_read_admission_probes, mutation):
    import json
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    original_init = PlanJevWriter.__init__

    def forged_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if mutation == 'old_format':
            self.output_format = self.output_format | {'name': 'surface_native_evidence_selectors_v2'}
        elif mutation == 'missing_prose_policy':
            self.messages[-1]['content'] = self.messages[-1]['content'].replace(
                '## Saved-page citations\nSelect the supplied local page reference. Do not regenerate supporting quotes.\n\n', '')
        else:
            for message in self.messages:
                frame = json.loads(message['content'])
                if 'citation_policy' in frame:
                    frame['citation_policy'] = 'forged_source_policy'
                    message['content'] = json.dumps(frame)
                    break
            else:
                raise AssertionError('Test requires an actual Plan policy frame')

    monkeypatch.setattr(PlanJevWriter, '__init__', forged_init)
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, 'forged_page_packet', False,
        native_read_admission_probes, related_page=True, authoring=mutation == 'forged_json_policy')


@pytest.mark.parametrize('output', ['page_gap', 'proposal_gap', 'gap_only', 'retired_field', 'foreign_page', 'unknown_code'])
@pytest.mark.parametrize('mixed', [False, True])
def test_current_plan_reply_uses_codes_without_question_phrase_witnesses(
        lane, tmp_path, monkeypatch, native_read_admission_probes, output, mixed):
    case = _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, None, mixed,
        native_read_admission_probes, related_page=True, generic_reply_output=output)
    if output in {'retired_field', 'foreign_page', 'unknown_code'}:
        assert case.response.status_code == 503
        assert case.turn.completion is None
        return
    assert case.response.status_code == 200, case.response.text
    import json
    body = json.loads(case.wire.calls[0].content)
    schema = body['text']['format']['schema']
    base = schema['$defs']['Base'] if mixed else schema
    assert 'requested_detail_gaps' not in base['properties']
    base_turn = case.turn.base_projection.turn if mixed else case.turn
    completion = base_turn.completion
    limits = [row for row in completion.answer_segments if row.kind == 'limitation']
    assert limits and all(row.question_phrase is None for row in limits)
    if output == 'page_gap':
        claim, = [row for row in completion.answer_segments if row.kind == 'related_page_claim']
        opened = case.client.get(f'/api/live/agent/worlds/{case.world}/conversation/turns/{base_turn.turn_id}/related-pages/{claim.read_id}')
        assert opened.status_code == 200
        assert 'old bath house' in opened.json()['markdown']
    if output == 'gap_only':
        assert all(row.kind == 'limitation' for row in completion.answer_segments)


def test_fresh_plan_refuses_whole_pre_generic_reply_contract_before_io(
        lane, tmp_path, monkeypatch, native_read_admission_probes):
    from application_state.agent_conversation import plan_writer_output_schema
    original = plan_writer_output_schema.native_output_format
    def historical(*args, **kwargs):
        return original(*args, **(kwargs | {'generic_reply_limits': False}))
    monkeypatch.setattr(plan_writer_output_schema, 'native_output_format', historical)
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, 'retired_reply_limits', False,
        native_read_admission_probes, related_page=True)


@pytest.mark.parametrize('mutation', ['changed_prose', 'historical_schema', 'malformed_schema', 'ambiguous_wrapper'])
def test_current_plan_generic_schema_is_bound_to_compact_input_and_exact_format(
        lane, tmp_path, monkeypatch, native_read_admission_probes, mutation):
    from copy import deepcopy
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    original = PlanJevWriter.__init__
    def forge(self, *args, **kwargs):
        original(self, *args, **kwargs)
        if mutation == 'changed_prose':
            self.messages[-1]['content'] = self.messages[-1]['content'].replace(
                '# Plan evidence\n\n', '# Plan evidence\n\nUnsupported contract annotation.\n\n', 1)
            return
        self.output_format = deepcopy(self.output_format)
        schema = self.output_format['schema']
        base = schema.get('$defs', {}).get('Base', schema)
        if mutation == 'historical_schema':
            base['properties']['requested_detail_gaps'] = {'type': 'array', 'items': {'type': 'object',
                'properties': {'question_phrase': {'type': 'string'}}, 'required': ['question_phrase'], 'additionalProperties': False}}
            base['required'].append('requested_detail_gaps')
        elif mutation == 'malformed_schema':
            base['required'].append('requested_detail_gaps')
        else:
            schema.setdefault('$defs', {})['Base'] = deepcopy(base)
    monkeypatch.setattr(PlanJevWriter, '__init__', forge)
    _ordinary_native_case(lane, tmp_path, monkeypatch, False, False, None, 'forged_page_packet', False,
        native_read_admission_probes, related_page=True)
