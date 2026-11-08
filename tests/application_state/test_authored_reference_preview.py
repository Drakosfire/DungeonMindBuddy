"""Selected-input display reuses the reference type and cannot grant evidence."""
from copy import deepcopy
import pytest
from application_state.agent_conversation.authored_reference_preview import project
from application_state.errors import ApplicationStateIntegrityError


def selected(kind='object', schema='dmb_authored_references_v2'):
    ref=dict(schema='dmb_authored_graph_reference_v1',managed_world_id='world-one',native_world_id='native',binding_version=1,graph_revision='revision',node_id='node',label='Selected object')
    if kind=='source':
        ref=dict(schema='dmb_authored_source_reference_v1',managed_world_id='world-one',native_world_id='native',binding_version=1,knowledge_revision='revision',source_artifact_id='recap',source_revision_id='saved-revision',evidence_ref_id='evidence',content_sha256='a'*64,selection_kind='full_document',section_id=None,label='Selected recap')
    return dict(schema=schema,references=[ref])

@pytest.mark.parametrize('kind,schema',[('object','dmb_authored_graph_references_v1'),('object','dmb_authored_references_v2'),('source','dmb_authored_references_v2')])
def test_existing_selection_versions_roundtrip_without_execution_or_source_content(kind,schema):
    raw=[selected(kind,schema)];before=deepcopy(raw)
    assert project(raw,'world-one')==raw[0]
    assert raw==before
    assert set(project(raw,'world-one'))=={'schema','references'}

@pytest.mark.parametrize('raw',[None,[]])
def test_absent_input_stays_absent(raw):
    assert project(raw,'world-one') is None

@pytest.mark.parametrize('change',['world','ambiguous','unknown','malformed','duplicate','null_capture'])
def test_invalid_or_ambiguous_selection_never_becomes_display_or_authority(change):
    raw=[selected()]
    if change=='null_capture':raw=[None]
    elif change=='world':raw[0]['references'][0]['managed_world_id']='foreign'
    elif change=='ambiguous':raw.append(deepcopy(raw[0]))
    elif change=='unknown':raw[0]['schema']='unregistered'
    elif change=='duplicate':raw[0]['references']*=2
    else:raw[0]['references'][0]['reader_authority']='forged'
    with pytest.raises(ApplicationStateIntegrityError,match='cannot be displayed safely'):
        project(raw,'world-one')
