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


def saved_fixture():
    from application_state.agent_conversation.types import BuildSourceContextBasisV1
    from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact, build_worldbuilding_source_artifact_id
    basis = BuildSourceContextBasisV1(world_id="world", document_id="document", registry_revision=2,
        content_sha256="a" * 64, visibility="internal")
    artifact_id = build_worldbuilding_source_artifact_id(workspace_document_id=basis.document_id,
        workspace_document_revision=basis.registry_revision, content_sha256=basis.content_sha256)
    artifact = GraphMemorySourceArtifact(source_artifact_id=artifact_id, source_domain="worldbuilding",
        world_id=basis.world_id, uri="repo://frozen/source.md", content_sha256=basis.content_sha256,
        workspace_document_id=basis.document_id, workspace_document_revision=basis.registry_revision,
        visibility_state=basis.visibility, lineage={"source_name": "The Frozen Source"})
    return basis, artifact


def test_saved_names_use_one_exact_metadata_batch_and_never_open_bodies(monkeypatch):
    from apps.live_control_server.services import agent_source_names as names, source_artifact_registry as registry
    basis, artifact = saved_fixture()
    calls = []
    def batch(root, identities):
        calls.append(identities)
        return {artifact.source_artifact_id: artifact}
    monkeypatch.setattr(registry, "get_source_artifacts", batch)
    monkeypatch.setattr(registry, "load_registered_source_artifact_text", lambda *_a, **_k: pytest.fail("Source body read"))
    labels = names._saved_source_names([basis, basis])
    assert len(calls) == 1 and calls[0] == {artifact.source_artifact_id}
    # Caller batches distinct bases; resolver never guesses between duplicate labels.
    assert names.source_name_for_saved_basis(basis, labels[:1]) == "The Frozen Source"
    assert names.source_name_for_saved_basis(basis, labels) is None


@pytest.mark.parametrize("change", [
    {"world_id": "foreign"}, {"workspace_document_id": "foreign"}, {"workspace_document_revision": 3},
    {"content_sha256": "b" * 64}, {"visibility_state": "player_safe"}, {"source_domain": "recap"},
    {"source_artifact_id": "foreign"}, {"lineage": {}}, {"lineage": {"source_name": " "}},
])
def test_saved_name_refuses_foreign_or_missing_metadata(monkeypatch, change):
    from apps.live_control_server.services import agent_source_names as names, source_artifact_registry as registry
    basis, artifact = saved_fixture()
    monkeypatch.setattr(registry, "get_source_artifacts", lambda *_: {artifact.source_artifact_id: artifact.model_copy(update=change)})
    assert names._saved_source_names([basis]) == []


def test_saved_name_metadata_failure_does_not_fall_back_to_current_document(monkeypatch):
    from apps.live_control_server.services import agent_source_names as names, source_artifact_registry as registry
    basis, _ = saved_fixture()
    def unavailable(*_):
        raise OSError("Unavailable metadata")
    monkeypatch.setattr(registry, "get_source_artifacts", unavailable)
    assert names._saved_source_names([basis]) == []
    assert names.source_name_for_saved_basis(basis, []) is None


def test_registry_batch_reads_one_snapshot_and_returns_only_requested_ids(monkeypatch):
    from apps.live_control_server.services import source_artifact_registry as registry
    from pathlib import Path
    _, artifact = saved_fixture()
    calls = []
    def snapshot(root):
        calls.append(root)
        return N(records=[artifact, artifact.model_copy(update={"source_artifact_id": "unrequested"})])
    monkeypatch.setattr(registry, "_load", snapshot)
    assert registry.get_source_artifacts(Path("unused"), {artifact.source_artifact_id}) == {artifact.source_artifact_id: artifact}
    assert len(calls) == 1
    assert registry.get_source_artifacts(Path("unused"), set()) == {}
    assert len(calls) == 1
