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
