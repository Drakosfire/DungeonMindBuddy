from tests.test_hosted_native_graph_access import hosted, recap_lane  # noqa: F401
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


def test_review_request_preserves_source_but_classic_preparation_is_retired(case,graph):
    original=page_text(case.root, case.record.document_id).encode("utf-8")
    response=case.client.post('/api/live/graph-authoring/document-relationship/request',json=intent(case))
    assert response.status_code==200,response.text
    request=response.json()
    assert request['worldId']==intent(case)['world_id']
    assert request['campaignId']==intent(case)['world_id']
    assert request['documentSource']==case.selector.model_dump(by_alias=True)
    assert request['proposals'][-1]['summary']==intent(case)['context']
    assert request['proposals'][-1]['relationshipLabel']=='owns — '+intent(case)['context']
    assert case.authority.publish_calls==0
    preview=case.client.post('/api/live/graph-authoring/prepare',json=request)
    assert preview.status_code==410,preview.text
    assert preview.json()['detail']['code']=='classic_manual_prepare_retired'
    assert 'confirm_token' not in preview.json()
    assert case.authority.publish_calls==0
    assert case.authority.published_requests==[]
    assert page_text(case.root, case.record.document_id).encode("utf-8")==original


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
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    protected=Mock(side_effect=AssertionError('Denied request must not reach protected source/native IO'))
    monkeypatch.setattr('apps.live_control_server.routes.graph_authoring.relationship_request',protected)
    if mode=='player':
        monkeypatch.setattr(
            'apps.live_control_server.services.agent_graph_auth.authenticate_native_graph_principal',
            lambda request: NativeGraphPrincipal('player', 'player', 'local_operator'),
        )
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


@pytest.mark.parametrize("hosted_mode", [False, True], ids=["local", "hosted"])
def test_signed_native_review_publishes_once(case, graph, monkeypatch, hosted_mode, request):
    post = case.client.post
    if hosted_mode:
        import json

        from tests.test_hosted_native_graph_access import HOSTED_WORLD_ACCESS_ENV, OWNER, _record

        hosted = request.getfixturevalue("hosted")
        world = case.record.world_id
        hosted.records[world] = _record(world, OWNER, case.binding.native_world_id)
        monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({world: [OWNER]}))
        post = lambda path, **kwargs: hosted.client.request("POST", path, **kwargs)
        kinds = hosted.client.request("GET", f"/api/live/graph-authoring/object-kinds?world_id={world}")
        assert kinds.status_code == 200, kinds.text
        assert kinds.json()["objectKinds"]
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
    def refuse_classic_capture(*args, **kwargs):
        pytest.fail('Native preparation attempted classic source capture')

    monkeypatch.setattr(reader, 'resolve_graph_document_source', refuse_classic_capture)
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
    if hosted_mode:
        forbidden = hosted.client.request(
            "POST", f"{prefix}/native-prepare", json={"review": review, "operation_id": operation}, origin=None,
        )
        assert forbidden.status_code == 403
    preview = post(f'{prefix}/native-prepare', json={'review': review, 'operation_id': operation})
    assert preview.status_code == 200, preview.text
    assert repo.get_head(space) == head
    assert repo.open_native_source_view(space).epoch == epoch

    confirmed = {'review': review, **preview.json()}
    from copy import deepcopy

    tampered = deepcopy(confirmed)
    tampered['prepared']['extension']['spans'][0]['start_byte'] += 1
    rejected = post(f'{prefix}/native-confirm', json=tampered)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()['detail']['code'] == 'confirmation_invalid'
    assert repo.get_head(space) == head
    assert repo.open_native_source_view(space).epoch == epoch

    if hosted_mode:
        from tests.test_hosted_native_graph_access import OTHER_OWNER

        original_owner = hosted.records[world]
        read_passage = reader.resolve_reviewed_passage

        def transfer_after_passage_read(*args, **kwargs):
            result = read_passage(*args, **kwargs)
            hosted.records[world] = original_owner.model_copy(update={"owner_subject": OTHER_OWNER})
            return result

        with monkeypatch.context() as patch:
            patch.setattr(reader, "resolve_reviewed_passage", transfer_after_passage_read)
            denied = post(f"{prefix}/native-confirm", json=confirmed)
        assert hosted.records[world].owner_subject == OTHER_OWNER
        assert denied.status_code == 403, denied.text
        assert repo.get_head(space) == head
        assert repo.open_native_source_view(space).epoch == epoch
        hosted.records[world] = original_owner

        read_binding = native.binding
        binding_reads = 0

        def transfer_on_final_binding(world_id):
            nonlocal binding_reads
            binding_reads += 1
            result = read_binding(world_id)
            if binding_reads == 2:
                hosted.records[world] = original_owner.model_copy(update={"owner_subject": OTHER_OWNER})
            return result

        with monkeypatch.context() as patch:
            patch.setattr(native, "binding", transfer_on_final_binding)
            denied = post(f"{prefix}/native-confirm", json=confirmed)
        assert binding_reads == 2
        assert hosted.records[world].owner_subject == OTHER_OWNER
        assert denied.status_code == 403, denied.text
        assert repo.get_head(space) == head
        assert repo.open_native_source_view(space).epoch == epoch
        hosted.records[world] = original_owner

    receipt = post(f'{prefix}/native-confirm', json=confirmed)
    assert receipt.status_code == 200, receipt.text
    child = repo.get_revision(space, receipt.json()['child_revision_id'])
    assert child.revision.parent_revision_id == head.head_revision_id
    assert repo.open_native_source_view(space).epoch == epoch + 1
    retry = post(f'{prefix}/native-confirm', json=confirmed)
    assert retry.status_code == 200, retry.text
    assert retry.json() == receipt.json()
    assert repo.get_head(space).head_revision_id == child.revision.revision_id
    assert repo.open_native_source_view(space).epoch == epoch + 1



def test_installed_core_governed_extension_metadata_recovery(case):
    """Installed public Core/WK compatibility; not HTTP recovery implementation."""
    from copy import deepcopy
    from datetime import UTC, datetime
    from hashlib import sha256

    from dungeonmind.application.vnext import (
        initialize_empty_knowledge_space, open_admitted_native_text,
        open_native_text_source_access_context, preview_native_source_evidence_extension,
        publish_native_source_evidence_extension, publish_native_text_source_evidence,
        recover_native_source_evidence_extension,
    )
    from dungeonmind.application.vnext.errors import (
        KnowledgePublicationIdempotencyConflictError, NativeTextSourceAdmissionIntegrityError,
    )
    from dungeonmind.application.vnext.materialization import decode_native_graph_payload
    from dungeonmind.contracts.vnext.native_source import (
        GovernedNativeSourceEvidenceExtensionV1, NativeSourceEvidenceExtensionV1,
        NativeTextSourceAdmissionV1,
    )
    from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
    from worldkeeper.integrations.dungeonmind import compile_prepared_change_to_dungeonmind
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from apps.live_control_server.services import graph_document_relationship as reader
    from graph_memory.vnext.domain_runtime import (
        dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile,
    )

    body = reader.get_committed_page_snapshot(case.root, case.record.document_id).markdown
    raw = body.encode("utf-8")
    domain, profile = dungeonbuddy_world_domain_contract(), dungeonbuddy_dnd5e_custom_predicate_profile()
    repo = InMemoryNativeSourceEvidenceRepository()
    space, now = "space:installed-recovery", datetime.now(UTC)
    genesis = initialize_empty_knowledge_space(repository=repo, space_id=space,
        initialization_id="init:installed-recovery", created_at=now,
        domain_contract=domain, semantic_profile=profile)
    root = publish_native_text_source_evidence(repository=repo, domain_contract=domain,
        semantic_profile=profile, request=NativeTextSourceAdmissionV1(
            space_id=space, admission_id="admission:installed-recovery",
            expected_parent_revision_id=genesis.published_revision_id, created_at=now,
            body_text=body, expected_body_sha256=sha256(raw).hexdigest(),
            source_classification="dungeonbuddy.source:worldbuilding", authority="primary",
            visibility={"kind": "public"}, spans=[dict(client_ref="opening", evidence_role="context",
                start_byte=0, end_byte=1, expected_slice_sha256=sha256(raw[:1]).hexdigest())]))
    extension = NativeSourceEvidenceExtensionV1(space_id=space,
        extension_id="extension:installed-recovery", original_admission_id=root.admission_id,
        source_artifact_id=root.source_artifact_id, source_revision_id=root.source_revision_id,
        expected_body_sha256=sha256(raw).hexdigest(), created_at=now,
        expected_parent_revision_id=repo.get_head(space).head_revision_id,
        expected_source_authority_epoch=repo.open_native_source_view(space).epoch,
        spans=[dict(client_ref="reviewed", evidence_role="support", start_byte=0,
                    end_byte=len(raw), expected_slice_sha256=sha256(raw).hexdigest())])
    evidence, = preview_native_source_evidence_extension(repository=repo, request=extension,
        domain_contract=domain, semantic_profile=profile, audience_labels=())
    context, _ = native.access_context(repo, space)
    prepared = reader.prepare_native_relationship(DocumentRelationshipRequest.model_validate(intent(case)),
        repository=repo, context=context, operation_id=extension.extension_id,
        predicate="dungeonbuddy.custom:owns", evidence_ref_id=evidence.evidence_ref_id,
        prepared_at=now, preview_evidence=evidence)
    compiled = compile_prepared_change_to_dungeonmind(prepared)
    request = GovernedNativeSourceEvidenceExtensionV1.model_validate({
        **extension.model_dump(mode="json"), "contribution": compiled.prospective_contribution,
        "dispositions": list(compiled.dispositions),
    })

    class MetadataOnly:
        def __getattr__(self, name):
            assert name in {"get_revision", "get_publication_receipt",
                            "get_native_source_admission_receipt",
                            "get_native_source_evidence_extension_receipt"}, name
            return getattr(repo, name)

    metadata = MetadataOnly()

    def recover(value=request):
        return recover_native_source_evidence_extension(repository=metadata, request=value,
            domain_contract=domain, semantic_profile=profile)

    def snapshot():
        return deepcopy({key: value for key, value in vars(repo).items() if key != "_lock"})

    before = snapshot()
    assert recover() is None
    assert snapshot() == before
    receipt = publish_native_source_evidence_extension(repository=repo, request=request,
        domain_contract=domain, semantic_profile=profile, audience_labels=())
    before = snapshot()
    assert recover() == receipt
    assert snapshot() == before
    child = repo.get_revision(space, receipt.publication_receipt.published_revision_id)
    content = decode_native_graph_payload(child.graph_payload)
    actual_entities = {e.entity_id for e in content.entities}
    actual_assertions = {a.assertion_id for a in content.assertions}
    assert {b.durable_id for b in receipt.result_bindings if b.result_kind == "entity"} <= actual_entities
    assert {b.durable_id for b in receipt.result_bindings if b.result_kind == "assertion"} <= actual_assertions
    assert len([b for b in receipt.result_bindings if b.result_kind == "entity"]) == 2
    assert len([b for b in receipt.result_bindings if b.result_kind == "assertion"]) >= 1

    later = extension.model_copy(update={
        "extension_id": "extension:installed-recovery-later",
        "expected_parent_revision_id": child.revision.revision_id,
        "expected_source_authority_epoch": repo.open_native_source_view(space).epoch,
        "spans": [extension.spans[0].model_copy(update={
            "client_ref": "later", "end_byte": 4, "expected_slice_sha256": sha256(raw[:4]).hexdigest(),
        })],
    })
    publish_native_source_evidence_extension(repository=repo, request=later,
        domain_contract=domain, semantic_profile=profile, audience_labels=())
    assert repo.get_head(space).head_revision_id != child.revision.revision_id
    before = snapshot()
    assert recover() == receipt
    assert snapshot() == before
    repo.withdraw_native_source(space_id=space, source_artifact_id=root.source_artifact_id,
                                source_revision_id=root.source_revision_id)
    before = snapshot()
    recovered = recover()
    assert recovered == receipt
    assert not hasattr(recovered, "body_text") and not hasattr(recovered, "body_bytes")
    assert snapshot() == before
    with pytest.raises(KnowledgePublicationIdempotencyConflictError):
        recover(request.model_copy(update={"created_at": now.replace(microsecond=(now.microsecond + 1) % 1000000)}))
    assert snapshot() == before
    with pytest.raises(NativeTextSourceAdmissionIntegrityError):
        publish_native_source_evidence_extension(repository=repo, request=request,
            domain_contract=domain, semantic_profile=profile, audience_labels=())
    assert snapshot() == before
    access = open_native_text_source_access_context(repository=repo, space_id=space,
        revision_id=repo.get_head(space).head_revision_id, domain_contract=domain, audience_labels=())
    assert open_admitted_native_text(access, receipt.bindings[0].evidence_ref_id).status == "unavailable"
