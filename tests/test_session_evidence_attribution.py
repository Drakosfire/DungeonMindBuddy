from urllib.parse import urlencode
from uuid import uuid4
import pytest
from application_state.agent_conversation.types import Turn,SessionEvidenceClaimV1,plan_answer_basis
from tests.test_agent_turn_service import _policy_turn


def test_session_claim_is_a_distinct_provenance_bound_source_not_a_plan_or_graph_fact():
    turn=_policy_turn();run_id=str(uuid4())
    url='/play?'+urlencode({'world':turn.world_id,'run':run_id,'evidence_revision':54})
    segment=SessionEvidenceClaimV1(kind='session_evidence_claim',text=f'Your closing reflections say players want combat. [Closing reflections]({url})',run_id=run_id,review_revision=54,evidence_sha256='a'*64)
    payload=turn.model_dump(mode='json',by_alias=True)
    payload['provenance']['supporting_work'].append({'resolution':'resolved','kind':'session_evidence_v1','object_id':run_id,'revision':'54','content_sha256':'a'*64})
    payload['completion']['answer_segments'].append(segment.model_dump())
    payload['completion']['answer_basis']=plan_answer_basis([*turn.completion.answer_segments,segment])
    payload['assistant_text']+='\n'+segment.text
    saved=Turn.model_validate(payload)
    assert saved.completion.answer_basis=='committed_plan_plus_session_evidence'
    assert saved.completion.answer_segments[-1].run_id==run_id
    payload['completion']['answer_segments'][-1]['evidence_sha256']='b'*64
    with pytest.raises(ValueError,match='frozen turn provenance'):Turn.model_validate(payload)


def test_session_claim_cannot_cite_mutable_current_review():
    turn=_policy_turn();run_id=str(uuid4());payload=turn.model_dump(mode='json',by_alias=True)
    payload['provenance']['supporting_work'].append({'resolution':'resolved','kind':'session_evidence_v1','object_id':run_id,'revision':'54','content_sha256':'a'*64})
    payload['completion']['answer_segments']=[{'kind':'session_evidence_claim','text':'[Notes](/play?run='+run_id+'&review=1)','run_id':run_id,'review_revision':54,'evidence_sha256':'a'*64}]
    payload['completion']['answer_basis']='committed_plan_plus_session_evidence'
    with pytest.raises(ValueError,match='exact pinned citation'):Turn.model_validate(payload)
