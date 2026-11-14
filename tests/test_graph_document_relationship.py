"""Saved selection adapter through the real governed HTTP boundary; isolated native port."""
from tests.test_graph_document_source import case as case
from tests.page_fixtures import page_text, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document
from types import SimpleNamespace
from uuid import uuid4
import pytest
from tests.test_graph_document_source import TEXT
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from apps.live_control_server.services.graph_document_relationship import DocumentRelationshipRequest, relationship_request

GM = NativeGraphPrincipal("operator", "gm", "local_operator")


def intent(c):
    return {'world_id':'eldyrwild','document_source':c.selector.model_dump(by_alias=True),'quote':TEXT.strip(),
        'source':{'node_id':None,'label':'Brin','kind':'npc'},
        'target':{'node_id':None,'label':'Shop','kind':'location'},
        'predicate':'owns','label':'owns','context':'Brin owns this shop in the authored setting.'}


@pytest.fixture
def graph(case,monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','local')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN','synthetic-relationship-local-token-with-adequate-length')
    case.client=TestClient(case.client.app,client=('127.0.0.1',50000),headers={'Authorization':'Bearer synthetic-relationship-local-token-with-adequate-length'})
    nodes=[]
    monkeypatch.setattr('apps.live_control_server.services.graph_document_relationship.authoring_identities',lambda *a,**kw:{"identities": [{"selectable": True, **vars(node)} for node in nodes]})
    return nodes


def test_request_preview_and_explicit_confirmation_reuse_existing_writer(case,graph):
    original=page_text(case.root, case.record.document_id).encode("utf-8")
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==200,response.text
    request=response.json()
    assert case.authority.publish_calls==0
    preview=case.client.post('/api/live/graph-authoring/prepare',json=request)
    assert preview.status_code==200,preview.text
    assert case.authority.publish_calls==0
    confirmed={**request,'confirmToken':preview.json()['confirm_token']}
    for _ in range(2):
        receipt=case.client.post('/api/live/graph-authoring/commit',json=confirmed)
        assert receipt.status_code==200,receipt.text
    assert case.authority.publish_calls==1
    assert page_text(case.root, case.record.document_id).encode("utf-8")==original
    assert request['proposals'][-1]['summary']==intent(case)['context']
    assert request['proposals'][-1]['relationshipLabel']=='owns — '+intent(case)['context']
    edge=next(a for a in case.authority.published_requests[0].contribution.accepted_assertions if a.assertion_kind=='edge')
    assert edge.label==request['proposals'][-1]['relationshipLabel']


@pytest.mark.parametrize('mutation',['quote','revision','world','self','predicate'])
def test_invalid_review_refuses_without_publication(case,graph,mutation):
    request=intent(case)
    if mutation=='quote':request['quote']='Not in the source'
    elif mutation=='revision':request['document_source']['revision']+=1
    elif mutation=='world':request['world_id']='foreign'
    elif mutation=='self':request['target']=request['source']
    else:request['predicate']=' '
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=request)
    assert response.status_code==409,response.text
    assert case.authority.publish_calls==0


@pytest.mark.parametrize('alias',[False,True])
def test_new_identity_cannot_duplicate_existing_name_or_alias(case,graph,alias):
    graph.append(SimpleNamespace(node_id='npc:brin',label='Smith' if alias else 'Brin',kind='npc',aliases=['Brin'] if alias else []))
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==409,response.text
    assert 'already exists' in response.text
    assert case.authority.publish_calls==0


def test_existing_identity_requires_exact_world_label_and_kind(case,graph):
    graph.append(SimpleNamespace(node_id='npc:brin',label='Brin',kind='npc',aliases=[]))
    request=intent(case);request['source']['node_id']='npc:brin'
    built=relationship_request(case.root,DocumentRelationshipRequest.model_validate(request), GM)
    assert len(built.proposals)==2
    assert built.proposals[-1].source_object_ref['nodeId']=='npc:brin'
    request['source']['kind']='location'
    assert case.client.post('/api/live/graph-authoring/document-relationship/request',json=request).status_code==409


def test_temporal_context_and_direction_are_preserved_without_inference(case,graph):
    request=intent(case);request['target']={'node_id':None,'label':'Rowan','kind':'npc'}
    request.update(predicate='works_with',label='worked together temporarily',context='A past temporary stint; this asserts no current employment or reciprocal edge.')
    built=relationship_request(case.root,DocumentRelationshipRequest.model_validate(request), GM)
    row=built.proposals[-1]
    assert row.relationship_type=='works_with' and row.direction=='directed'
    assert row.summary==request['context'] and row.relationship_label==request['label']+' — '+request['context']
    assert len([p for p in built.proposals if p.proposal_kind=='relationship'])==1


def test_missing_source_is_an_actionable_registry_error(case,graph,monkeypatch):
    from apps.live_control_server.services.workspace_document_registry import WorkspaceDocumentRegistryError
    def missing(*args):
        raise WorkspaceDocumentRegistryError('The selected saved page is no longer available.')
    monkeypatch.setattr('apps.live_control_server.services.graph_document_relationship.get_committed_page_snapshot',missing)
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==404,response.text
    assert response.json()['detail']['code']=='relationship_source_unavailable'
    assert case.authority.publish_calls==0


@pytest.mark.parametrize('body,quote',[(TEXT+TEXT,TEXT.strip()),(TEXT+'\nAnother source block.\n',TEXT+'\nAnother source block.')])
def test_ambiguous_or_cross_block_quote_cannot_be_previewed(case,graph,body,quote):
    import hashlib
    request=intent(case)
    save_page(case.root, case.record.document_id, body)
    record=get_workspace_document(case.root, case.record.document_id)
    request['document_source'].update(revision=record.revision,contentSha256=hashlib.sha256(body.encode()).hexdigest())
    request['quote']=quote
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=request)
    assert response.status_code==409,response.text
    assert case.authority.publish_calls==0


@pytest.mark.parametrize('mode,status',[('missing',401),('wrong',401),('remote',403),('player',403)])
def test_new_adapter_denies_before_source_graph_or_freeze_io(case,graph,monkeypatch,mode,status):
    from fastapi.testclient import TestClient
    from unittest.mock import Mock
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal,NativeGraphPrincipal
    protected=Mock(side_effect=AssertionError('Denied request must not reach protected source/native IO'))
    monkeypatch.setattr('apps.live_control_server.routes.graph_authoring.relationship_request',protected)
    if mode=='player':
        case.client.app.dependency_overrides[authenticate_native_graph_principal]=lambda:NativeGraphPrincipal('player','player','local_operator')
    headers={} if mode=='missing' else {'Authorization':'Bearer wrong' if mode=='wrong' else 'Bearer synthetic-relationship-local-token-with-adequate-length'}
    client=TestClient(case.client.app,client=('203.0.113.1' if mode=='remote' else '127.0.0.1',50000))
    response=client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case),headers=headers)
    assert response.status_code==status,response.text
    protected.assert_not_called()


def test_runtime_checkout_and_retained_world_source_root_are_distinct(case,graph,monkeypatch):
    runtime=case.root/'runtime-checkout'
    runtime.mkdir()
    observed=[]
    def projection(scope, principal):
        observed.append(scope.managed_world_id)
        assert principal == GM
        return {"identities": []}
    monkeypatch.setattr('apps.live_control_server.services.graph_document_relationship.authoring_identities',projection)
    request=relationship_request(runtime,DocumentRelationshipRequest.model_validate(intent(case)), GM)
    assert observed==[intent(case)["world_id"]]
    assert request.document_source==case.selector
    assert not (case.root/'out/registries/source_content/graph_documents').exists()
    assert not (runtime/'out').exists()
    assert case.authority.publish_calls==0


def test_relationship_reader_uses_committed_snapshot_not_file_witness(request, graph, monkeypatch):
    c = request.getfixturevalue("case")
    from apps.live_control_server.services import graph_document_relationship as reader
    from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot
    from apps.live_control_server.services.graph_object_authoring_prepare import GraphObjectAuthoringError
    original = get_committed_page_snapshot(c.root, c.record.document_id)
    projection = original.model_copy(update={"file_exists": False,
        "record": original.record.model_copy(update={"target_relpath": None})})
    monkeypatch.setattr(reader, "get_committed_page_snapshot", lambda *args: projection)
    request = DocumentRelationshipRequest.model_validate(intent(c))
    # The existing real source resolver still verifies/freezes the exact source;
    # this changes only its consumer projection, not source/native authority.
    assert reader.relationship_request(c.root, request, GM).proposals
    assert c.authority.publish_calls == 0
    for changes in ({"content_status": "draft"}, {"document_id": str(uuid4())},
                    {"world_id": "foreign"}, {"revision": original.loaded_revision + 1}):
        projection.record = original.record.model_copy(update=changes)
        with pytest.raises(GraphObjectAuthoringError):
            reader.relationship_request(c.root, request, GM)
    assert c.authority.publish_calls == 0


def test_reviewed_passage_uses_utf8_byte_offsets(case, monkeypatch):
    from hashlib import sha256

    from apps.live_control_server.services import graph_document_relationship as reader

    snapshot = reader.get_committed_page_snapshot(case.root, case.record.document_id)
    request = DocumentRelationshipRequest.model_validate(intent(case))
    prefix = "Élderwyld — "
    body = prefix + request.quote
    replacement = snapshot.model_copy(update={"markdown": body})
    monkeypatch.setattr(reader, "get_committed_page_snapshot", lambda *_: replacement)

    _, character_offset, span = reader.resolve_reviewed_passage(case.root, request)
    expected = request.quote.encode("utf-8")
    assert character_offset == len(prefix)
    assert span["start_byte"] == len(prefix.encode("utf-8"))
    assert body.encode("utf-8")[span["start_byte"]:span["end_byte"]] == expected
    assert span["expected_slice_sha256"] == sha256(expected).hexdigest()


def test_native_relationship_intent_retains_reviewed_passage_and_text(case):
    from datetime import UTC, datetime

    from apps.live_control_server.services import graph_document_relationship as reader

    request = DocumentRelationshipRequest.model_validate(intent(case))
    admission = SimpleNamespace(
        state="admitted", document_id=request.document_source.document_id,
        world_id=request.world_id, space_id="space:elderwyld",
        body_sha256=request.document_source.content_sha256,
        admission_id="admission:test", source_artifact_id="artifact:test",
        source_revision_id="source-revision:test",
    )
    extension = reader.native_relationship_evidence_request(
        case.root, request, admission=admission,
        context={"space_id": admission.space_id, "revision_id": "rev:test", "source_epoch": 1},
        operation_id="publication:test", created_at=datetime.now(UTC),
    )
    span, = extension.spans
    snapshot = reader.get_committed_page_snapshot(case.root, admission.document_id)
    assert snapshot.markdown.encode()[span.start_byte:span.end_byte] == request.quote.encode()

    change = reader.native_relationship_intent(
        request, space_id=extension.space_id,
        predicate="dungeonbuddy.custom:visits", evidence_ref_id="ev:reviewed",
    )
    relationship = change.operations[-1]
    assert change.space_id == admission.space_id
    assert relationship.metadata.evidence_ref_ids == ("ev:reviewed",)
    assert dict(relationship.metadata.domain_metadata[0].payload.items) == {
        "relationship_label": request.label, "relationship_context": request.context,
    }


def test_signed_native_review_publishes_once(case, graph, monkeypatch):
    from datetime import UTC, datetime

    from dungeonmind.application.vnext import (
        initialize_empty_knowledge_space,
        publish_native_text_source_evidence,
    )
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository

    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from apps.live_control_server.integrations.dungeonmind import native_world_source_admission as source
    from apps.live_control_server.services import graph_document_relationship as reader

    repo = InMemoryNativeSourceEvidenceRepository()
    domain, profile = source._genesis_descriptors()
    from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_custom_predicate_profile
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    space = 'space:relationship'
    now = datetime.now(UTC)
    genesis = initialize_empty_knowledge_space(
        repository=repo, space_id=space, initialization_id='init:relationship',
        created_at=now, domain_contract=domain, semantic_profile=profile,
    )
    review = intent(case)
    request = DocumentRelationshipRequest.model_validate(review)
    body = reader.get_committed_page_snapshot(case.root, case.record.document_id).markdown
    root = publish_native_text_source_evidence(
        repository=repo, domain_contract=domain, semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id=space, admission_id='admission:relationship',
            expected_parent_revision_id=genesis.published_revision_id, created_at=now,
            body_text=body, expected_body_sha256=request.document_source.content_sha256,
            source_classification=source.SOURCE_CLASSIFICATION, authority='primary',
            visibility={'kind': 'public'},
            spans=[{
                'client_ref': 'opening', 'evidence_role': 'context',
                'start_byte': 0, 'end_byte': 1,
                'expected_slice_sha256': __import__('hashlib').sha256(body.encode()[:1]).hexdigest(),
            }],
        ),
    )
    monkeypatch.setattr(native, 'repository', lambda: repo)
    monkeypatch.setattr(native, 'binding', lambda _: {'native_world_id': space})
    monkeypatch.setattr(source, 'get_native_world_source_status', lambda *a, **kw: SimpleNamespace(
        state='admitted', document_id=case.record.document_id, world_id=request.world_id,
        space_id=space, body_sha256=request.document_source.content_sha256,
        admission_id=root.admission_id, source_artifact_id=root.source_artifact_id,
        source_revision_id=root.source_revision_id,
    ))
    head = repo.get_head(space)
    epoch = repo.open_native_source_view(space).epoch
    prefix = '/api/live/graph-authoring/document-relationship'
    operation = str(uuid4())
    preview = case.client.post(f'{prefix}/native-prepare', json={'review': review, 'operation_id': operation})
    assert preview.status_code == 200, preview.text
    assert repo.get_head(space) == head
    assert repo.open_native_source_view(space).epoch == epoch

    confirmed = {'review': review, **preview.json()}
    from copy import deepcopy

    tampered = deepcopy(confirmed)
    tampered['prepared']['extension']['spans'][0]['start_byte'] += 1
    rejected = case.client.post(f'{prefix}/native-confirm', json=tampered)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()['detail']['code'] == 'confirmation_invalid'
    assert repo.get_head(space) == head
    assert repo.open_native_source_view(space).epoch == epoch

    receipt = case.client.post(f'{prefix}/native-confirm', json=confirmed)
    assert receipt.status_code == 200, receipt.text
    child = repo.get_revision(space, receipt.json()['child_revision_id'])
    assert child.revision.parent_revision_id == head.head_revision_id
    assert repo.open_native_source_view(space).epoch == epoch + 1
    retry = case.client.post(f'{prefix}/native-confirm', json=confirmed)
    assert retry.status_code == 200, retry.text
    assert retry.json() == receipt.json()
    assert repo.get_head(space).head_revision_id == child.revision.revision_id
    assert repo.open_native_source_view(space).epoch == epoch + 1
