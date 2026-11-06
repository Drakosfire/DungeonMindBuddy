"""Message-role transport changes only: these tests do not prove model quality."""
from dataclasses import replace
import copy
import hashlib

import pytest

from src.graph_memory.extraction import category_candidate_graph_extractor as owner
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_EXTRACTION_PROFILE, _RECAP_SOURCE_FAITHFULNESS, recap_prompt_role_binding,
)
from src.graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict

POLICY = 'Source-faithfulness requirements: ' + _RECAP_SOURCE_FAITHFULNESS


def dispatch(profile, source, *, source_handles=False):
    class Client:
        def __init__(self): self.calls=[]
        def run_pass(self, name, *, model_id, instructions, user_content, pass_spec=None, **kwargs):
            self.calls.append((name,instructions,user_content,model_id))
            key='observation_nodes' if pass_spec.kind in ('node', 'encounter_job') else 'observation_beats' if pass_spec.kind=='beat' else 'observation_edges'
            return {'parsed':{key:[]},'cost_usd':0.0,'usage':{},'elapsed_ms':0,'response_id':'synthetic:offline'}
    client=Client()
    client.supports_node_source_handles = source_handles
    index=source_span_index_to_dict(build_source_span_index_for_text(
        source_artifact_id='synthetic:source',content_sha256=hashlib.sha256(source.encode()).hexdigest(),text=source))
    options=owner.CategoryGraphExtractionOptions(campaign_id='synthetic',session_id='session-1',
        session_number=1,source_span_index=index,source_text=source,source_artifact_id='synthetic:source',
        source_ref_id=index['source_ref_id'],profile=profile,model_id='synthetic:model',
        enable_encounter_job_pass=profile.enable_encounter_job_pass)
    owner.extract_category_candidate_graph(options,client=client)
    return client.calls


@pytest.mark.parametrize('source_handles', [False, True])
def test_seven_actual_dispatches_transfer_policy_once_and_preserve_every_other_byte(monkeypatch, source_handles):
    source='A traveler examines an old bridge. Later the traveler returns to the inn.'
    actual=dispatch(RECAP_EXTRACTION_PROFILE,source,source_handles=source_handles)
    with monkeypatch.context() as control:
        control.setattr(owner,'recap_prompt_role_binding',lambda profile:('',profile))
        previous=dispatch(RECAP_EXTRACTION_PROFILE,source,source_handles=source_handles)
    assert len(actual)==len(previous)==7
    assert {r[0] for r in actual}=={'actor_pass','location_pass','collective_pass','object_pass','thread_pass','beat_pass','edge_pass'}
    for new,old in zip(actual,previous):
        assert new[0]==old[0] and new[3]==old[3]
        assert old[2].count(POLICY)==1
        assert new[1]==old[1]+'\n\n'+POLICY
        assert new[2]==old[2].replace(POLICY,'',1)
        assert POLICY not in new[2]
        assert new[1].count(POLICY)==1


@pytest.mark.parametrize('source_handles', [False, True])
def test_source_policy_echo_is_never_removed(monkeypatch, source_handles):
    source='A copied document contains the following text:\n\n'+POLICY+'\n\nThe traveler keeps walking.'
    actual=dispatch(RECAP_EXTRACTION_PROFILE,source,source_handles=source_handles)
    with monkeypatch.context() as control:
        control.setattr(owner,'recap_prompt_role_binding',lambda profile:('',profile))
        previous=dispatch(RECAP_EXTRACTION_PROFILE,source,source_handles=source_handles)
    for new,old in zip(actual,previous):
        assert new[2]==old[2].replace(POLICY,'',1)
        # Source-handle packets split text into sentence units; the exact
        # old/new byte delta above proves every source unit survives unchanged.
        if not source_handles:
            assert POLICY in new[2]
        assert new[1].count(POLICY)==1


def test_canonical_profile_and_standalone_renderers_unchanged():
    old=copy.deepcopy(RECAP_EXTRACTION_PROFILE)
    policy,view=recap_prompt_role_binding(RECAP_EXTRACTION_PROFILE)
    assert policy==POLICY and view is not RECAP_EXTRACTION_PROFILE
    assert RECAP_EXTRACTION_PROFILE==old
    for original,task in zip(old.node_passes,view.node_passes):
        assert task.instruction==original.instruction.replace(POLICY,'',1)
        assert replace(task,instruction=original.instruction)==original
    rows=[{'source_span_ref_id':'synthetic:span','line_start':1,'line_end':1,'text':'The traveler waits.'}]
    prompts=owner.render_category_pass_prompts(rows,profile=RECAP_EXTRACTION_PROFILE)
    assert all(POLICY in prompt for prompt in prompts.values())


@pytest.mark.parametrize('profile_name',['worldbuilding','worldbuilding_plumbing','encounter_preview'])
def test_other_profiles_actual_messages_are_byte_identical(monkeypatch,profile_name):
    if profile_name=='worldbuilding':
        from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE as profile
    elif profile_name=='worldbuilding_plumbing':
        from src.graph_memory.extraction.worldbuilding_plumbing_profile import WORLDBUILDING_PLUMBING_PROFILE as profile
    else:
        from src.graph_memory.extraction.extraction_profile import get_extraction_profile
        profile=get_extraction_profile('recap_category_encounter_job_preview','2.0')
    assert recap_prompt_role_binding(profile)==('',profile)
    actual=dispatch(profile,'A traveler describes a stone bridge.')
    with monkeypatch.context() as control:
        control.setattr(owner,'recap_prompt_role_binding',lambda profile:('',profile))
        previous=dispatch(profile,'A traveler describes a stone bridge.')
    assert actual==previous
    if profile_name == 'encounter_preview':
        assert len(actual) == 8
