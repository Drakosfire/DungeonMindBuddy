from types import SimpleNamespace as N
from uuid import uuid4

import pytest

from apps.live_control_server.services.agent_source_names import source_name_for_read, source_names_for_turns


def fixture():
    event_id = uuid4()
    read = N(source_read_id='read', anchor_id='anchor', evidence_ref_id='evidence', source_artifact_id='artifact',
             source_revision_id='source-rev', content_sha256='a' * 64)
    turn = N(turn_id=uuid4(), world_id='world', conversation_id=uuid4(),
             graph_context_receipt=N(graph_authority=N(graph_revision='graph-rev')),
             graph_context_execution=N(events=[N(kind='validated_source_read_v2')]),
             completion=N(citation_map=N(entries=[N(source_read_ids=['read'])])))
    label = {'turn_id':str(turn.turn_id), 'source_read_event_id':str(event_id),
             **vars(read), 'graph_revision':'graph-rev', 'source_name':'Session 24 recap'}
    return turn, event_id, read, label


def test_title_requires_exact_current_producing_receipt():
    turn, event, read, label = fixture()
    assert source_name_for_read(turn, event, read, [label]) == 'Session 24 recap'
    assert source_name_for_read(turn, event, read, [label, label]) is None


@pytest.mark.parametrize('field', ['turn_id','source_read_event_id','source_read_id','anchor_id','evidence_ref_id',
    'source_artifact_id','source_revision_id','content_sha256','graph_revision'])
def test_changed_identity_does_not_supply_a_label(field):
    turn, event, read, label = fixture()
    assert source_name_for_read(turn, event, read, [{**label,field:'foreign'}]) is None


@pytest.mark.parametrize('name', [None, '', '  ', 42, {'name':'fake'}])
def test_missing_or_malformed_name_is_unavailable(name):
    turn, event, read, label = fixture()
    assert source_name_for_read(turn, event, read, [{**label,'source_name':name}]) is None


def test_one_batch_for_all_cited_turns_in_a_history_page():
    turn, _, _, label = fixture()
    second = N(**{**vars(turn),'turn_id':uuid4()})
    calls = []
    class Owner:
        def source_name_labels(self, world, conversation, identities):
            calls.append((world,conversation,identities))
            return [label]
    assert source_names_for_turns([turn,second,turn],service=Owner()) == [label]
    assert calls == [('world',turn.conversation_id,[turn.turn_id,second.turn_id])]


def test_no_read_for_uncited_turn_or_metadata_failure():
    turn, _, _, _ = fixture()
    calls=[]
    class Owner:
        def source_name_labels(self,*args):
            calls.append(args)
            raise ConnectionError('display metadata unavailable')
    uncited=N(**{**vars(turn),'completion':N(citation_map=None)})
    assert source_names_for_turns([uncited],service=Owner()) == []
    assert calls == []
    assert source_names_for_turns([turn],service=Owner()) == []
    assert len(calls)==1
