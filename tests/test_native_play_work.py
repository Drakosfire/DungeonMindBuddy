"""Play projection is not ownership; the locked immutable owner must agree."""
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_play_work import project_work,validate_owner_locked
from application_state.agent_conversation.native_context import PlayWorkContextV1
from application_state.agent_conversation.play_graph_authority import play_source_frame
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from tests.test_surface_native_context import work,provenance_for


def supplied(*, note=None):
    original=work('play')
    basis=original.play_basis
    if note is not None:
        from hashlib import sha256
        basis=type(basis).model_validate_json(basis.model_copy(update=dict(
            scene_note=note,scene_note_sha256=sha256(note.encode()).hexdigest())).model_dump_json(by_alias=True))
    sources=[t.PlaySourcePayloadV1(source_kind='current_moment',
        locator=t.play_source_locator(basis),text='Exact saved Play moment.')]
    if note is not None:
        sources.append(t.PlaySourcePayloadV1(source_kind='scene_note',
            locator=t.play_source_locator(basis),text=note))
    frame=play_source_frame(tuple(sources))
    context=PlayWorkContextV1(play_basis=basis,play_sources=frame.manifest,
        play_source_frame_sha256=canonical_sha256(frame))
    proof=dict(source_frame=frame.model_dump(mode='json',by_alias=True),
        session_evidence=[],dialogue=[dict(role='user',content='What is here?')])
    return context,provenance_for(context),proof


def test_projection_uses_existing_selector_frame_and_keeps_scene_note_separate():
    context,provenance,proof=supplied(note='A saved possibility.')
    frame=project_work(context,provenance,uuid4(),proof)
    assert frame['schema']=='dmb_native_play_work_v1'
    assert {s['source_kind'] for s in frame['source_frame']['sources']}=={'current_moment','scene_note'}
    assert all('text_blocks' in s and 'text' not in s for s in frame['source_frame']['sources'])
    assert frame['dialogue']==proof['dialogue'] and frame['session_evidence']==[]


def test_changed_body_cannot_reuse_frozen_manifest():
    context,provenance,proof=supplied()
    proof['source_frame']['sources'][0]['text']='Another scene.'
    with pytest.raises(ValueError):project_work(context,provenance,uuid4(),proof)


def test_same_world_foreign_run_cannot_borrow_provenance():
    context,provenance,proof=supplied()
    foreign=provenance.model_copy(update={'surface_instance_id':'play:foreign',
        'primary_work':provenance.primary_work.model_copy(update={'object_id':'another-run'})})
    with pytest.raises(ValueError):project_work(context,foreign,uuid4(),proof)


def test_unadmitted_session_packet_cannot_become_work_memory():
    context,provenance,proof=supplied()
    proof['session_evidence']=[dict(schema_version='dmb_session_evidence_v1',world_id='other',run_id='other')]
    with pytest.raises(ValueError):project_work(context,provenance,uuid4(),proof)


def test_recomputed_caller_commitment_still_needs_independent_owner(monkeypatch):
    from application_state.agent_conversation import play_graph_source_owner as owner
    context,provenance,proof=supplied()
    frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
    changed=play_source_frame(tuple(s.model_copy(update={'text':'Invented scene.'}) for s in frame.sources))
    context=context.model_copy(update=dict(play_sources=changed.manifest,
        play_source_frame_sha256=canonical_sha256(changed)))
    proof['source_frame']=changed.model_dump(mode='json',by_alias=True)
    # Even structurally valid self-supplied hashes do not establish source ownership.
    project_work(context,provenance,uuid4(),proof)
    seen=[]
    monkeypatch.setattr(owner,'read_native_play_current_moment',lambda conn,basis: seen.append(basis) or 'Exact saved Play moment.')
    monkeypatch.setattr(owner,'resolve_play_work_sessions',lambda *args,**kwargs: pytest.fail('Moment mismatch must fail first'))
    with pytest.raises(ValueError,match='independent source owner'):
        validate_owner_locked(object(),context,provenance,proof)
    assert seen==[context.play_basis]


def test_locked_validation_adopts_both_existing_immutable_owners(monkeypatch):
    from application_state.agent_conversation import play_graph_source_owner as owner
    context,provenance,proof=supplied(note='Saved scene note.')
    conn=object(); seen=[]
    monkeypatch.setattr(owner,'read_native_play_current_moment',lambda c,b: seen.append(('moment',c,b)) or 'Exact saved Play moment.')
    monkeypatch.setattr(owner,'resolve_play_work_sessions',lambda c,b,refs,sessions,**kw: seen.append(('sessions',c,b,refs,sessions,kw)))
    validate_owner_locked(conn,context,provenance,proof)
    assert seen[0]==('moment',conn,context.play_basis)
    assert seen[1]==('sessions',conn,context.play_basis,provenance.supporting_work,[],{'world_id':provenance.world_id})


def test_dropping_note_cannot_redefine_current_moment():
    context,provenance,proof=supplied(note='Saved note.')
    frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
    no_note=play_source_frame(tuple(s for s in frame.sources if s.source_kind=='current_moment'))
    context=context.model_copy(update=dict(play_sources=no_note.manifest,
        play_source_frame_sha256=canonical_sha256(no_note)))
    proof['source_frame']=no_note.model_dump(mode='json',by_alias=True)
    with pytest.raises(ValueError,match='separate saved note'):
        project_work(context,provenance,uuid4(),proof)
