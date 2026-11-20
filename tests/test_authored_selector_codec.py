"""Shared model presentation over exact internal authored blocks; no IO."""
from dataclasses import replace
import pytest
from application_state.agent_conversation.authored_excerpt_blocks import (
    partition,selection_catalog,project_selection_blocks,restore_selection_blocks,verify_selection_blocks,
)


def test_large_catalog_is_short_lossless_and_owner_exact():
    bodies=[('plan','# Prep 🦉\r\n'+''.join(f'\r\nParagraph {i}.\r\n' for i in range(100))),
        ('scene-note','Same thought.\n'),('reflection','Same thought.\n')]
    catalog=selection_catalog(bodies,'submission-one')
    assert len(catalog)>=102 and len({r.selection_id for r in catalog})==len(catalog)
    assert all(len(r.selection_id)<len(r.block.block_handle) for r in catalog)
    for owner,text in bodies:
        rows=project_selection_blocks(text,owner,catalog)
        assert all(set(r)=={'selection_id','text'} for r in rows)
        assert restore_selection_blocks(rows)==text
        assert verify_selection_blocks(rows,text,owner,catalog)==partition(text,owner)
        assert {r['selection_id'] for r in rows}=={r.selection_id for r in catalog if r.block.source_handle==owner}
    assert catalog[-1].selection_id!=catalog[-2].selection_id


@pytest.mark.parametrize('change',['submission','owner','body','order'])
def test_stale_or_foreign_catalog_cannot_verify_projection(change):
    sources=[('plan','# Plan\nOriginal.\n'),('note','Note.\n')]
    original=selection_catalog(sources,'submission-one')
    rows=project_selection_blocks(sources[0][1],'plan',original)
    altered=list(sources);scope='submission-one'
    if change=='submission':scope='submission-two'
    elif change=='owner':altered[1]=('foreign-note',altered[1][1])
    elif change=='body':altered[1]=('note','Changed note.\n')
    else:altered.reverse()
    current=selection_catalog(altered,scope)
    assert {r.selection_id for r in original}.isdisjoint(r.selection_id for r in current)
    with pytest.raises(ValueError):verify_selection_blocks(rows,sources[0][1],'plan',current)


@pytest.mark.parametrize('change',['unknown','internal','truncated','text','extra','duplicate'])
def test_changed_projection_is_refused(change):
    text='# Plan\nExact text.\n';catalog=selection_catalog([('plan',text)],'submission')
    rows=project_selection_blocks(text,'plan',catalog)
    if change=='unknown':rows[0]['selection_id']='a-foreign-1'
    elif change=='internal':rows[0]['selection_id']=catalog[0].block.block_handle
    elif change=='truncated':rows[0]['selection_id']=rows[0]['selection_id'][:-1]
    elif change=='text':rows[0]['text']+='changed'
    elif change=='extra':rows[0]['block_handle']=catalog[0].block.block_handle
    else:rows.append(dict(rows[0]))
    with pytest.raises(ValueError):verify_selection_blocks(rows,text,'plan',catalog)


def test_duplicate_internal_owner_and_nonblank_null_selector_are_refused():
    with pytest.raises(ValueError):selection_catalog([('same','Text.'),('same','Text.')],'submission')
    with pytest.raises(ValueError):restore_selection_blocks([{'selection_id':None,'text':'not blank'}])
    assert restore_selection_blocks([{'selection_id':None,'text':' \r\n'}])==' \r\n'


@pytest.mark.parametrize('duplicate',['selector','block'])
def test_catalog_aliases_cannot_collapse_internal_identity(duplicate):
    text='# Plan\nBody.\n';catalog=selection_catalog([('owner',text)],'submission')
    changed=list(catalog)
    changed[1]=replace(changed[1],selection_id=changed[0].selection_id) if duplicate=='selector' else replace(changed[1],block=changed[0].block)
    with pytest.raises(ValueError):project_selection_blocks(text,'owner',changed)


@pytest.mark.parametrize('mutation',[None,'truncated','internal','duplicate','text','extra','submission','legacy_frame'])
def test_current_play_carrier_uses_only_exact_scoped_selectors(mutation):
    from uuid import uuid4
    from tests.test_play_graph_authority import payload
    from application_state.agent_conversation.play_graph_authority import play_source_frame
    from application_state.agent_conversation.play_graph_input import NativePlayInputV5,pack_selector_play_frame
    from application_state.agent_conversation.surface_evidence_answer import SELECTOR_INSTRUCTIONS
    body='# North road 🦉\r\n'+''.join(f'\r\nParagraph {i}.\r\n' for i in range(100))
    frame=play_source_frame((payload(text=body),payload('scene_note',text='Saved note.\r\n')))
    submission=uuid4();packed=pack_selector_play_frame(frame,str(submission))
    blocks=packed['sources'][0]['text_blocks']
    assert len(blocks)>=100 and all(set(b)=={'selection_id','text'} for b in blocks)
    if mutation=='truncated':blocks[0]['selection_id']=blocks[0]['selection_id'][:-1]
    elif mutation=='internal':blocks[0]['selection_id']=partition(body,frame.manifest.entries[0].source_id)[0].block_handle
    elif mutation=='duplicate':blocks[1]['selection_id']=blocks[0]['selection_id']
    elif mutation=='text':blocks[0]['text']+=' forged'
    elif mutation=='extra':blocks[0]['block_handle']='b'+'e'*64
    elif mutation=='submission':submission=uuid4()
    elif mutation=='legacy_frame':packed['schema']='dmb_play_block_frame_v1'
    values=dict(submission_id=submission,message='Discuss this scene.',source_frame=packed,answer_instructions=SELECTOR_INSTRUCTIONS)
    if mutation:
        with pytest.raises(ValueError):NativePlayInputV5(**values)
    else:
        carrier=NativePlayInputV5(**values)
        assert carrier.resolved_source_frame()==frame
        assert NativePlayInputV5.model_validate_json(carrier.model_dump_json())==carrier


@pytest.mark.parametrize('version',[1,2,3,4])
def test_historical_carriers_keep_original_semantics_and_do_not_become_current(version):
    from uuid import uuid4
    from tests.test_play_graph_context import fixture
    from application_state.agent_conversation.play_graph_input import (
        NativePlayInputV1,NativePlayInputV2,NativePlayInputV3,NativePlayInputV4,NativePlayInputV5,pack_play_frame,
    )
    from application_state.agent_conversation.surface_evidence_answer import INSTRUCTIONS,NATIVE_INSTRUCTIONS
    _,_,frame=fixture();cls={1:NativePlayInputV1,2:NativePlayInputV2,3:NativePlayInputV3,4:NativePlayInputV4}[version]
    values=dict(submission_id=uuid4(),message='Historical scene.',source_frame=frame if version<3 else pack_play_frame(frame))
    if version>=3:values['answer_instructions']=INSTRUCTIONS if version==3 else NATIVE_INSTRUCTIONS
    carrier=cls(**values);raw=carrier.model_dump_json()
    decoded=cls.model_validate_json(raw)
    assert (decoded.source_frame if version<3 else decoded.resolved_source_frame())==frame
    with pytest.raises(ValueError):NativePlayInputV5.model_validate_json(raw)
