"""Real disposable APP persistence for inert Build authoring receipts."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.build_proposal.graph_reference_review import (
    BuildGraphReferenceApply, BuildGraphReferenceReviewService,
)
from application_state.build_proposal.prose_catalog import freeze_build_prose_catalog
from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.types import (
    BuildGeneratedProposal, BuildProposalBasis, BuildProposalReservation, BuildProviderAuthorization,
    BuildProseBoundaryProposalRecord, BuildProseBoundaryReservation, BuildProseBoundaryTarget,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.content import pages
from application_state.content.markdown_source_blocks import source_block_spans
from application_state.content.page_presentation import BlockBinding, PagePresentation
from apps.live_control_server.services import build_graph_reference
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from tests.application_state.test_agent_conversation_postgres import _new
from tests.page_fixtures import create_page_fixture, page_text, save_page


@pytest.fixture
def reservation(application_state_dsn):
    world = 'compose-' + uuid4().hex
    conversation = _new(AgentConversationService(), world)
    return BuildProposalReservation(idempotency_key=uuid4(), conversation_id=conversation.conversation_id,
        expected_pointer_revision=1, instruction='Create NPCs and jobs as a table.',
        basis=BuildProposalBasis(world_id=world, document_id='source-one', registry_revision=1,
            content_sha256='a'*64, draft_sha256='b'*64, visibility='internal', caret=1,
            draft_generation=0, selection_generation=0))


def test_reservation_is_durable_and_idempotent_with_real_workspace_basis(reservation):
    store = BuildProposalService()
    record, created = store.reserve(reservation)
    assert created and record.state == 'reserved' and record.after_turn_sequence == 0
    assert record.reservation.basis.document_id == 'source-one'
    assert record.reservation.basis.registry_revision == 1
    replay, created = BuildProposalService().reserve(reservation)
    assert not created and replay == record
    assert BuildProposalService().list(reservation.basis.world_id, reservation.conversation_id) == [record]
    changed = reservation.model_copy(update={'instruction':'Different instruction'})
    with pytest.raises(ApplicationStateConflictError):
        store.reserve(changed)


def test_concurrent_same_key_reserves_once(reservation):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:BuildProposalService().reserve(reservation), range(2)))
    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0].action_id == results[1][0].action_id


def test_foreign_world_and_changed_conversation_refuse(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    with pytest.raises(ApplicationStateNotFoundError):
        store.get('foreign-world', record.action_id)
    other = reservation.model_copy(update={'idempotency_key':uuid4(),'expected_pointer_revision':2})
    with pytest.raises(ApplicationStateConflictError):
        store.reserve(other)


def test_durable_authorization_lifecycle_result_and_draft_receipt(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    world, action = reservation.basis.world_id, record.action_id
    def advance(state, **fields):
        nonlocal record
        record = store.advance(world, action, expected_revision=record.revision, state=state, **fields)
        return record
    auth = BuildProviderAuthorization(provider_attempt_id=uuid4(), model='synthetic',payload_sha256='c'*64,payload_utf8_bytes=123)
    advance('authorized',authorization=auth)
    advance('sdk_entered')
    result = BuildGeneratedProposal(replacement_markdown='| NPC | Job |\n| --- | --- |\n| Nia | Baker |', summary='A proposed NPC table.', assumptions=['New authored lore.'], target='captured')
    advance('response_received',raw_response=json.dumps(dict(destination='current_page',**result.model_dump(mode='json'))))
    advance('proposed')
    fresh = BuildProposalService().get(world, action)
    assert fresh.proposal == result and fresh.authorization == auth
    inserted = store.report_inserted(world,action,expected_revision=fresh.revision)
    assert inserted.inserted_in_draft and inserted.state == 'proposed'
    assert store.report_inserted(world,action,expected_revision=fresh.revision) == inserted
    with pytest.raises(ApplicationStateConflictError):
        advance('sdk_entered')  # No provider replay after result.


def test_uncertain_dispatch_is_terminal_and_cannot_be_replayed(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    world = reservation.basis.world_id
    record = store.advance(world,record.action_id,expected_revision=1,state='authorized',
        authorization=BuildProviderAuthorization(provider_attempt_id=uuid4(),model='synthetic',payload_sha256='c'*64,payload_utf8_bytes=123))
    record = store.advance(world,record.action_id,expected_revision=record.revision,state='sdk_entered')
    record = store.advance(world,record.action_id,expected_revision=record.revision,state='unknown',failure_code='provider_outcome_unknown')
    replay, created = store.reserve(reservation)
    assert not created and replay.state == 'unknown'
    with pytest.raises(ApplicationStateConflictError):
        store.advance(world,record.action_id,expected_revision=record.revision,state='authorized')


def test_missing_authorization_or_stale_transition_rolls_back(reservation):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    with pytest.raises(ValidationError):
        store.advance(reservation.basis.world_id,record.action_id,expected_revision=1,state='authorized')
    assert store.get(reservation.basis.world_id,record.action_id).state == 'reserved'
    with pytest.raises(ApplicationStateConflictError):
        store.advance(reservation.basis.world_id,record.action_id,expected_revision=99,state='failed',failure_code='stale')
    with pytest.raises(ApplicationStateConflictError):
        store.report_inserted(reservation.basis.world_id,record.action_id,expected_revision=1)


@pytest.mark.parametrize('substitution', ['markdown', 'summary', 'assumptions', 'raw', 'target'])
def test_proposal_owner_rejects_results_unrelated_to_captured_final(reservation, substitution):
    store = BuildProposalService()
    record, _ = store.reserve(reservation)
    world = reservation.basis.world_id
    def advance(state, **fields):
        nonlocal record
        record = store.advance(world,record.action_id,expected_revision=record.revision,state=state,**fields)
        return record
    advance('authorized',authorization=BuildProviderAuthorization(provider_attempt_id=uuid4(),
        model='synthetic',payload_sha256='c'*64,payload_utf8_bytes=123))
    advance('sdk_entered')
    result = BuildGeneratedProposal(replacement_markdown='A proposed copper lamp.',
        summary='A proposed detail.',assumptions=['The lamp is invented.'],target='captured')
    raw=json.dumps(dict(destination='current_page',**result.model_dump(mode='json')))
    advance('response_received',raw_response=raw)
    changed = {'markdown': {'proposal':result.model_copy(update={'replacement_markdown':'A substituted silver lamp.'})},
        'summary': {'proposal':result.model_copy(update={'summary':'A changed summary.'})},
        'assumptions': {'proposal':result.model_copy(update={'assumptions':['It happened.']})},
        'target': {'proposal':result.model_copy(update={'target':None})},
        'raw': {'raw_response':raw.replace('copper','silver')}}[substitution]
    with pytest.raises(ApplicationStateConflictError):
        advance('response_received' if substitution=='raw' else 'proposed',**changed)
    assert store.get(world,record.action_id)==record
    assert record.state=='response_received' and record.proposal is None and record.raw_response==raw
    # The original final remains usable after the rejected transaction.
    assert advance('proposed').proposal==result


def test_prose_boundary_review_keeps_original_caret_and_requires_exact_offered_target(reservation):
    from application_state.build_proposal.review import BuildProposalReviewService, BuildReviewCommand

    basis = reservation.basis.model_copy(update={"editor_sha256": "e" * 64})
    target = BuildProseBoundaryTarget(
        catalog_sha256="a" * 64, alias="passage2:insert_after",
        operation="insert_after", **{"from": 43, "to": 43},
        before_text_sha256="b" * 64,
    )
    request = BuildProseBoundaryReservation.model_validate(
        reservation.model_dump() | {"basis": basis, "prose_target": target},
    )
    with pytest.raises(ApplicationStateConflictError, match="catalog owner"):
        BuildProposalService().reserve(request)
    admitted = []
    service = BuildProposalService(admit_prose_boundary=lambda conn, value: admitted.append(value))
    record, created = service.reserve(request)
    assert created and admitted == [request]
    assert service.reserve(request) == (record, False)
    world, action = basis.world_id, record.action_id

    def advance(state, **fields):
        nonlocal record
        record = service.advance(world, action, expected_revision=record.revision, state=state, **fields)

    advance("authorized", authorization=BuildProviderAuthorization(
        provider_attempt_id=uuid4(), model="synthetic", payload_sha256="c" * 64, payload_utf8_bytes=123,
    ))
    advance("sdk_entered")
    advance("response_received", raw_response=json.dumps({
        "destination": "current_page", "target": "prose_target",
        "replacement_markdown": "Bring a second lantern.", "summary": "A proposed precaution.",
        "assumptions": [],
    }))
    advance("proposed")
    assert type(BuildProposalService().get(world, action)) is BuildProseBoundaryProposalRecord
    assert record.reservation.basis.caret == 1 and record.reservation.prose_target == target
    with pytest.raises(ApplicationStateConflictError, match="exact Review receipt"):
        service.report_inserted(world, action, expected_revision=record.revision)

    review = BuildProposalReviewService()
    opened = review.execute(world, action, BuildReviewCommand(operation="open", expected_revision=0))
    assert opened.schema_version == "dmb_build_proposal_review_v5"
    assert opened.placement_caret == 1 and opened.prose_target == target
    with pytest.raises(ApplicationStateConflictError, match="offered paragraph boundary"):
        review.execute(world, action, BuildReviewCommand(
            operation="move", expected_revision=opened.revision, placement_caret=2,
        ))
    values = dict(operation="prepare", expected_revision=opened.revision, apply_id=uuid4(),
                  after_editor_sha256="f" * 64, after_draft_sha256="d" * 64)
    with pytest.raises(ApplicationStateConflictError, match="acknowledge the exact prose boundary"):
        review.execute(world, action, BuildReviewCommand(**values))
    prepare = BuildReviewCommand(**values, prose_target=target)
    prepared = review.execute(world, action, prepare)
    assert prepared.apply.prose_target == target
    assert review.execute(world, action, prepare) == prepared
    confirm = BuildReviewCommand(operation="confirm", expected_revision=prepared.revision, apply_id=prepare.apply_id)
    assert review.execute(world, action, confirm).state == "applied"
    assert BuildProposalService().get(world, action).inserted_in_draft
    with pytest.raises(ApplicationStateNotFoundError):
        review.get("foreign-world", action)


@pytest.fixture
def placement_capture():
    draft = "The moon shines.\n"
    editor = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"The moon shines."}]}]}'
    basis = BuildProposalBasis(
        world_id="observatory", document_id="page", registry_revision=1,
        content_sha256=sha256(draft.encode()).hexdigest(), visibility="internal", caret=1,
        draft_sha256=sha256(draft.encode()).hexdigest(), editor_sha256=sha256(editor.encode()).hexdigest(),
        draft_generation=0, selection_generation=0,
    )
    placement = BuildGraphReferencePlacement(
        basis=basis, boundary=freeze_build_prose_catalog(basis, editor, draft).target("passage1", "insert_after"),
        reference=AuthoredGraphReferenceV1(
            managed_world_id="observatory", native_world_id="native-observatory", binding_version=1,
            graph_revision="rev:one", node_id="threat:lurker", label="Lurker",
        ),
        entity_kind="threat",
    )
    return placement, editor, draft


def test_build_reference_is_bound_to_exact_captured_boundary(placement_capture):
    placement, editor, draft = placement_capture
    placement.require_boundary(editor, draft)
    with pytest.raises(ApplicationStateConflictError, match="boundary changed"):
        placement.require_boundary(editor.replace("shines", "fades"), draft)
    with pytest.raises(ValidationError, match="requires its World"):
        BuildGraphReferencePlacement.model_validate({
            **placement.model_dump(),
            "reference": {**placement.reference.model_dump(), "managed_world_id": "foreign"},
        })


def test_build_reference_joins_exact_id_and_classification_at_current_pin(placement_capture, monkeypatch):
    placement, _, _ = placement_capture
    principal = NativeGraphPrincipal(subject="local_operator", role="gm", auth_method="local_operator")
    scope = {
        "managed_world_id": "observatory", "native_world_id": "native-observatory",
        "binding_version": 1, "revision_id": "rev:one", "scope_mode": "world", "campaign_id": None,
    }
    selected = {"node_id": "threat:lurker", "label": "Lurker", "kind": "threat", "selectable": True}
    namesake = {**selected, "node_id": "location:lurker", "kind": "location"}
    payload = {"scope": scope, "identities": [namesake, selected]}

    def current(request_scope, request_principal):
        assert request_scope.managed_world_id == "observatory" and request_scope.scope_mode == "world"
        assert request_principal is principal
        return payload

    monkeypatch.setattr(build_graph_reference, "authoring_identities", current)
    build_graph_reference.require_current_build_graph_reference(placement, principal)
    wrong_kind = placement.model_copy(update={
        "reference": placement.reference.model_copy(update={"node_id": namesake["node_id"]}),
    })
    with pytest.raises(ApplicationStateConflictError, match="classification changed"):
        build_graph_reference.require_current_build_graph_reference(wrong_kind, principal)
    payload["identities"] = [namesake]
    with pytest.raises(ApplicationStateConflictError, match="identity or classification changed"):
        build_graph_reference.require_current_build_graph_reference(placement, principal)
    scope["revision_id"] = "rev:later"
    with pytest.raises(ApplicationStateConflictError, match="different or changed Graph"):
        build_graph_reference.require_current_build_graph_reference(placement, principal)


def test_build_reference_accepts_only_the_exact_typed_editor_and_markdown(placement_capture):
    placement, editor, draft = placement_capture
    after = json.loads(editor)
    atom = {"type": "runbookReference", "attrs": {
        "kind": "ref", "refType": "graph-node", "refId": "threat:lurker", "label": "Lurker",
    }}
    after["content"].append({"type": "paragraph", "attrs": {"pageBlockId": None}, "content": [atom]})
    index = placement.require_editor_insertion(editor, draft, json.dumps(after))
    assert index == 1
    after_draft = "The moon shines.\n\n[Lurker](dmb-node:threat:lurker)\n"
    placement.require_draft_insertion(draft, after_draft, index)
    with pytest.raises(ApplicationStateConflictError, match="authorized identity"):
        placement.require_draft_insertion(draft, after_draft.replace("threat:", "location:"), index)
    with pytest.raises(ApplicationStateConflictError, match="unrelated bytes"):
        placement.require_draft_insertion(draft, after_draft.replace("shines.", "fades."), index)
    atom["attrs"]["refId"] = "location:lurker"
    with pytest.raises(ApplicationStateConflictError, match="one typed atom"):
        placement.require_editor_insertion(editor, draft, json.dumps(after))


def test_graph_reference_review_replays_exact_postimage_and_records_only_observed_save(
    placement_capture, application_state_dsn,
):
    placement, editor, draft = placement_capture
    world = placement.basis.world_id
    conversation = _new(AgentConversationService(), world)
    action_id = uuid4()
    store = BuildGraphReferenceReviewService()
    stage_count = 0

    def admit(conn, review):
        nonlocal stage_count
        assert review.placement == placement and review.state == "editing"
        stage_count += 1

    review = store.stage(action_id, conversation.conversation_id, 1, placement, editor, draft, admit=admit)
    assert store.stage(action_id, conversation.conversation_id, 1, placement, editor, draft, admit=admit) == review
    assert stage_count == 1
    with pytest.raises(ApplicationStateNotFoundError):
        store.get("foreign", action_id)

    after = json.loads(editor)
    after["content"].append({"type": "paragraph", "content": [{
        "type": "runbookReference", "attrs": {
            "kind": "ref", "refType": "graph-node", "refId": placement.reference.node_id,
            "label": placement.reference.label,
        },
    }]})
    after_editor = json.dumps(after)
    after_draft = "The moon shines.\n\n[Lurker](dmb-node:threat:lurker)\n"
    after_digest = sha256(after_draft.encode()).hexdigest()
    apply = BuildGraphReferenceApply(
        apply_id=uuid4(), editor_sha256=sha256(after_editor.encode()).hexdigest(),
        draft_sha256=after_digest, content_sha256=after_digest, presentation_sha256=None,
    )

    def prepare(receipt, authorize):
        return store.prepare(
            world, action_id, review.revision, receipt, editor, draft, after_editor, after_draft,
            authorize_prepare=authorize,
        )

    def changed(*args):
        raise ApplicationStateConflictError("The current page does not match the review")

    with pytest.raises(ApplicationStateConflictError, match="current page"):
        prepare(apply, changed)
    assert store.get(world, action_id) == review
    prepared = prepare(apply, lambda previous, receipt: None)
    assert prepared.state == "applying" and prepared.apply == apply
    with pytest.raises(ApplicationStateConflictError, match="current page"):
        prepare(apply, changed)
    assert prepare(apply, lambda previous, receipt: None) == prepared
    with pytest.raises(ApplicationStateConflictError, match="different postimage"):
        prepare(apply.model_copy(update={"content_sha256": "b" * 64}), changed)
    with pytest.raises(ApplicationStateConflictError, match="current page"):
        store.confirm(world, action_id, apply.apply_id, observe_save=changed)
    assert store.get(world, action_id) == prepared
    confirmed = store.confirm(world, action_id, apply.apply_id, observe_save=lambda checked: 2)
    assert confirmed.state == "applied" and confirmed.saved_revision == 2
    assert store.confirm(world, action_id, apply.apply_id, observe_save=changed) == confirmed


@pytest.mark.parametrize("identity_only", [False, True])
def test_graph_reference_review_route_joins_current_graph_and_independent_content_save(
    placement_capture, application_state_dsn, monkeypatch, tmp_path, identity_only,
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent, build_proposal_reviews

    placement, editor, draft = placement_capture
    world = placement.basis.world_id
    page = create_page_fixture(
        tmp_path, title="Moon Gallery", world_id=world, campaign_id=world, kind="worldbuilding_source",
        source_domain="worldbuilding", document_class="lore", authority_state="draft", visibility_state="internal",
    )
    page = save_page(tmp_path, page.document_id, draft)
    original = json.loads(editor)

    def presentation(markdown, ids):
        encoded = markdown.encode()
        return PagePresentation(markdown_sha256=sha256(encoded).hexdigest(), items=[BlockBinding(
            id=identity, byte_start=start, byte_end=end, sha256=sha256(encoded[start:end]).hexdigest(),
        ) for identity, (start, end) in zip(ids, source_block_spans(markdown), strict=True)])

    def save_identities(source, layout):
        current = pages.snapshot_page(page.document_id, world_id=world)
        return pages.commit_page(
            page.document_id, source, world_id=world, expected_revision=current.page.object_revision,
            expected_working_copy_revision=current.working_copy_revision, page_presentation=layout,
        )

    registry_revision = page.revision
    if identity_only:
        original["content"][0]["attrs"] = {"pageBlockId": "original-paragraph"}
        editor = json.dumps(original)
        save_identities(draft, presentation(draft, ["original-paragraph"]))
        registry_revision = pages.snapshot_page(page.document_id, world_id=world).page.object_revision
    placement = placement.model_copy(update={"basis": placement.basis.model_copy(update={
        "document_id": page.document_id, "registry_revision": registry_revision,
        "editor_sha256": sha256(editor.encode()).hexdigest(),
    })})
    conversation = _new(AgentConversationService(), world)
    action_id = uuid4()
    BuildGraphReferenceReviewService().stage(
        action_id, conversation.conversation_id, 1, placement, editor, draft, admit=lambda conn, review: None,
    )
    principal = NativeGraphPrincipal(subject="local_operator", role="gm", auth_method="local_operator")
    graph_scope = {
        "managed_world_id": world, "native_world_id": "native-observatory", "scope_mode": "world",
        "campaign_id": None, "binding_version": 1, "revision_id": "rev:later",
    }
    monkeypatch.setattr(build_graph_reference, "authoring_identities", lambda scope, caller: {
        "scope": graph_scope, "identities": [{
            "node_id": "threat:lurker", "label": "Lurker", "kind": "threat", "selectable": True,
        }],
    })
    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "synthetic-only-review-token-00000000000")
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")
    path = f"/api/live/agent/worlds/{world}/build-proposals/{action_id}/review"
    after = json.loads(editor)
    after["content"].append({"type": "paragraph", "content": [{"type": "runbookReference", "attrs": {
        "kind": "ref", "refType": "graph-node", "refId": "threat:lurker", "label": "Lurker",
    }}]})
    after_draft = "The moon shines.\n\n[Lurker](dmb-node:threat:lurker)\n"
    layout = None
    if identity_only:
        block_id = f"page-graph-ref-{placement.boundary.catalog_sha256[:32]}-{placement.boundary.from_}"
        after["content"][1]["attrs"] = {"pageBlockId": block_id}
        layout = presentation(after_draft, ["original-paragraph", block_id])
    after_editor = json.dumps(after)
    draft_digest = sha256(after_draft.encode()).hexdigest()
    apply_id = str(uuid4())
    command = {"schema": "dmb_build_graph_reference_command_v1", "operation": "prepare", "expected_revision": 1,
               "editor_json": editor, "draft_markdown": draft,
               "after_editor_json": after_editor, "after_draft_markdown": after_draft,
               "apply": {"apply_id": apply_id, "editor_sha256": sha256(after_editor.encode()).hexdigest(),
                         "draft_sha256": draft_digest, "content_sha256": draft_digest,
                         "presentation_sha256": layout.fingerprint() if layout else None}}
    confirm = {"schema": command["schema"], "operation": "confirm", "apply_id": apply_id}
    with TestClient(app) as client:
        assert client.get(path).status_code == 403
        monkeypatch.setattr(build_proposal_reviews, "enforce_native_graph_gm", lambda _: principal)
        assert client.get(path).json()["state"] == "editing"
        assert client.get(path.replace(f"/{world}/", "/foreign/")).status_code == 404
        refused = client.post(path, json=command)
        assert refused.status_code == 409, refused.text
        assert client.get(path).json()["state"] == "editing"
        graph_scope["revision_id"] = "rev:one"
        prepared = client.post(path, json=command)
        assert prepared.status_code == 200, prepared.text
        assert prepared.json()["state"] == "applying"
        assert client.post(path, json=confirm).status_code == 409
        assert page_text(tmp_path, page.document_id) == draft
        authorize = {**confirm, "operation": "authorize_save"}
        graph_scope["revision_id"] = "rev:next"
        assert client.post(path, json=authorize).status_code == 409
        graph_scope["revision_id"] = "rev:one"
        assert client.post(path, json=authorize).status_code == 200
        if layout:
            save_identities(after_draft, layout)
        else:
            save_page(tmp_path, page.document_id, after_draft)
        saved_revision = pages.snapshot_page(page.document_id, world_id=world).page.object_revision
        observed = client.post(path, json=confirm)
        assert observed.status_code == 200, observed.text
        assert observed.json()["state"] == "applied" and observed.json()["saved_revision"] == saved_revision
        assert client.post(path, json=confirm).json() == observed.json()
