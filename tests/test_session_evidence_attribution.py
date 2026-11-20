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


def test_hermes_session_title_is_bound_to_exact_producing_request():
    import json
    from hashlib import sha256
    from types import SimpleNamespace
    from uuid import uuid4
    from apps.live_control_server.services.session_evidence import render_session_evidence
    from application_state.agent_conversation.session_citation_labels import producing_session_titles, PREFIX
    from application_state.agent_conversation import types as t
    run=str(uuid4())
    session={'title':'Approach to Edge — Session Prep','run_id':run,'review_revision':54,
             'sha256':'a'*64,'sources':[{'kind':'closing_reflections','text':'More combat next time.'}]}
    rendered=render_session_evidence({'sessions':[session]})
    # Hermes wraps the question; source text is embedded in a model message.
    raw=json.dumps({'model':'gpt-6-luna','input':[{'role':'user','content':rendered+'\n\nUser question: What next?'}]})
    auth=SimpleNamespace(envelope_sha256=sha256(raw.encode()).hexdigest())
    turn=SimpleNamespace(provenance=SimpleNamespace(supporting_work=[
        t.HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=run,revision='54',content_sha256='a'*64)]))
    assert producing_session_titles(turn,auth,raw)==((run,'54',session['title']),)
    # Actual Hermes history retains older user messages and tool outputs. Only
    # the current host-rendered user question supplies display labels.
    older=rendered.replace('54','53').replace(session['title'],'Earlier source')
    body=json.loads(raw)
    body['input']=[{'role':'user','content':older},
        {'role':'assistant','content':'Earlier answer'},*body['input'],
        {'type':'function_call_output','call_id':'old','output':PREFIX+'not JSON'}]
    resumed=json.dumps(body)
    resumed_auth=SimpleNamespace(envelope_sha256=sha256(resumed.encode()).hexdigest())
    assert producing_session_titles(turn,resumed_auth,resumed)==((run,'54',session['title']),)
    quoted=json.dumps({'input':[{'role':'user','content':'Please discuss '+PREFIX+'not JSON'}]})
    assert producing_session_titles(turn,SimpleNamespace(envelope_sha256=sha256(quoted.encode()).hexdigest()),quoted)==()
    assert 'review checkpoint, never a session number' in rendered
    with pytest.raises(ValueError,match='actual producing request'):
        producing_session_titles(turn,auth,raw.replace('Session Prep','New title'))
    turn.provenance.supporting_work=[t.HistoricalReference(resolution='resolved',kind='session_evidence_v1',object_id=str(uuid4()),revision='54',content_sha256='b'*64)]
    with pytest.raises(ValueError,match='frozen producing source'):
        producing_session_titles(turn,auth,raw)
