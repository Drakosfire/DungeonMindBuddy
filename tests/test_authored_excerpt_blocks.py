"""Synthetic exact authored selections; never private story fixtures."""
from copy import deepcopy
from hashlib import sha256

import pytest
from application_state.agent_conversation.authored_excerpt_blocks import partition,project_blocks,restore_blocks,verify_blocks
from application_state.agent_conversation.surface_evidence_answer import authored_support


@pytest.mark.parametrize('text',[
    '# Heading\n\nA soft\nwrapped paragraph.\n\nA second paragraph.\n',
    '\r\n# Unicode 🐸\r\n\r\nA soft\r\nwrapped paragraph.\r\n',
    '# Repeat\n\nSame.\n\n# Repeat\n\nSame.\n',
    '- One\n  - Nested\n\n- Two\n\nAfter.\n',
    '| Name | Value |\n| --- | --- |\n| A | B |\n\nAfter.\n',
    '> One\n>\n> Two\n\nAfter.\n',
    '```text\n:::readaloud\nnot a container\n```\n\nAfter.\n',
    ':::readaloud North road\n\nA first paragraph.\n\nA second paragraph.\n:::\n\nAfter.\n',
    ':::note\n\n:::rules\nInner.\n:::\n\nOuter.\n:::\n',
    'A\u2028B\u0085C\n\nD\n',
    'No ending newline',
])
def test_exact_partition_keeps_raw_bytes_and_atomic_blocks(text):
    source=authored_support('plan','Saved Plan','plan','1','a'*64,text)
    blocks=partition(text,source.handle)
    assert ''.join(b.text for b in blocks)==text
    assert len({b.block_handle for b in blocks})==len(blocks)
    previous=0
    for b in blocks:
        assert b.byte_start==previous
        assert text.encode()[b.byte_start:b.byte_end]==b.text.encode()
        assert sha256(b.text.encode()).hexdigest()==b.block_sha256
        assert b.text.strip()
        previous=b.byte_end
    assert previous==len(text.encode())
    assert restore_blocks(project_blocks(text,source.handle))==text
    assert verify_blocks(project_blocks(text,source.handle),text,source.handle)==blocks
    # Soft wraps and compound top-level structures are never split internally.
    if text.startswith(('- ','| ','> ','```',':::')):
        assert text.split('\n\nAfter.')[0] in blocks[0].text


def test_duplicate_blocks_and_entries_have_distinct_location_bound_identity():
    text='Same.\n\nSame.\n'
    one=authored_support('session','Notes','run','2','b'*64,text,'1'*64)
    other=authored_support('session','Notes','run','2','b'*64,text,'2'*64)
    assert one.handle!=other.handle
    blocks=partition(text,one.handle)
    assert blocks[0].block_handle!=blocks[1].block_handle
    assert {b.block_handle for b in blocks}.isdisjoint(b.block_handle for b in partition(text,other.handle))
    changed=authored_support('session','Notes','run','3','b'*64,text,'1'*64)
    assert {b.block_handle for b in blocks}.isdisjoint(b.block_handle for b in partition(text,changed.handle))


@pytest.mark.parametrize('mutation',['handle','text','order','extra','drop'])
def test_projection_cannot_change_bytes_location_or_selector(mutation):
    text='One.\n\nTwo.\n';source='q'+'c'*64
    rows=project_blocks(text,source)
    changed=deepcopy(rows)
    if mutation=='handle':changed[0]['block_handle']='b'+'d'*64
    if mutation=='text':changed[0]['text']='Changed.\n\n'
    if mutation=='order':changed.reverse()
    if mutation=='extra':changed[0]['source_handle']=source
    if mutation=='drop':changed.pop()
    with pytest.raises(ValueError):verify_blocks(changed,text,source)


@pytest.mark.parametrize('mutation',[None,'text','handle','extra','legacy'])
def test_play_projection_reconstructs_only_exact_frozen_manifest(mutation):
    from uuid import uuid4
    from tests.test_play_graph_context import fixture
    from application_state.agent_conversation.play_graph_input import NativePlayInputV3,pack_play_frame
    from application_state.agent_conversation.surface_evidence_answer import INSTRUCTIONS
    import json
    _receipt,_execution,frame=fixture()
    packed=pack_play_frame(frame)
    if mutation=='text':packed['sources'][0]['text_blocks'][0]['text']+=' forged'
    if mutation=='handle':packed['sources'][0]['text_blocks'][0]['block_handle']='b'+'e'*64
    if mutation=='extra':packed['sources'][0]['text_blocks'][0]['offset']=0
    if mutation=='legacy':packed['schema']='dmb_play_source_frame_v1'
    raw=json.dumps(dict(schema='dmb_native_play_input_v3',submission_id=str(uuid4()),message='Discuss this scene.',
        source_frame=packed,answer_policy='dmb_surface_evidence_answer_v2',answer_instructions=INSTRUCTIONS))
    if mutation:
        with pytest.raises(ValueError):NativePlayInputV3.model_validate_json(raw)
    else:
        carrier=NativePlayInputV3.model_validate_json(raw)
        assert carrier.resolved_source_frame()==frame
        assert all('text' not in source and source['text_blocks'] for source in packed['sources'])
