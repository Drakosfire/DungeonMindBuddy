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
from application_state.unit_of_work import unit_of_work
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


@pytest.mark.parametrize("markdown", [
    "Bring a second lantern.",
    "> [!READ-ALOUD] Crossing\n> A second lantern lights up."
    "\n\n> [!GM-NOTE] Wait\n> Keep the gate closed.",
])
def test_prose_boundary_review_keeps_original_caret_and_requires_exact_offered_target(
    reservation, markdown,
):
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
        "replacement_markdown": markdown, "summary": "A proposed precaution.",
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
    assert review.get(world, action).markdown == markdown
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
    payload["identities"] += [
        {**selected, "node_id": "opaque-id", "label": "opaque-id"},
        {**selected, "node_id": "unresolved-id", "selectable": False},
    ]
    candidates = build_graph_reference.read_build_graph_reference_candidates("observatory", principal)
    assert [(item.reference.node_id, item.reference.label, item.entity_kind) for item in candidates] == [
        ("location:lurker", "Lurker", "location"), ("threat:lurker", "Lurker", "threat"),
    ]
    assert candidates[1].reference == placement.reference
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
    after_draft = "The moon shines.\n\n[Lurker](#dmb-ref:graph-node:threat:lurker)\n"
    placement.require_draft_insertion(draft, after_draft, index)
    with pytest.raises(ApplicationStateConflictError, match="authorized identity"):
        placement.require_draft_insertion(draft, after_draft.replace("threat:", "location:"), index)
    with pytest.raises(ApplicationStateConflictError, match="unrelated bytes"):
        placement.require_draft_insertion(draft, after_draft.replace("shines.", "fades."), index)
    atom["attrs"]["refId"] = "location:lurker"
    with pytest.raises(ApplicationStateConflictError, match="one typed atom"):
        placement.require_editor_insertion(editor, draft, json.dumps(after))


@pytest.mark.parametrize("href", ["dmb-node:threat:lurker", "#dmb-ref:graph-node:threat:lurker"])
def test_graph_reference_review_replays_exact_postimage_and_records_only_observed_save(
    placement_capture, application_state_dsn, href,
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
    after_draft = f"The moon shines.\n\n[Lurker]({href})\n"
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


def test_graph_reference_review_rolls_back_with_its_owner(placement_capture, application_state_dsn):
    placement, editor, draft = placement_capture
    world = placement.basis.world_id
    conversation = _new(AgentConversationService(), world)
    action_id = uuid4()
    store = BuildGraphReferenceReviewService()

    with pytest.raises(RuntimeError, match="owner completion failed"):
        with unit_of_work(application_state_dsn) as conn:
            review = store.stage_in_transaction(
                conn, action_id, conversation.conversation_id, 1, placement, editor, draft,
                admit=lambda conn, review: None,
            )
            assert review.state == "editing"
            raise RuntimeError("owner completion failed")

    with pytest.raises(ApplicationStateNotFoundError):
        store.get(world, action_id)
    assert store.stage(
        action_id, conversation.conversation_id, 1, placement, editor, draft,
        admit=lambda conn, review: None,
    ).state == "editing"


@pytest.mark.parametrize("identity_only", [False, True])
@pytest.mark.parametrize("href", ["dmb-node:threat:lurker", "#dmb-ref:graph-node:threat:lurker"])
def test_graph_reference_review_route_joins_current_graph_and_independent_content_save(
    placement_capture, application_state_dsn, monkeypatch, tmp_path, identity_only, href,
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
    after_draft = f"The moon shines.\n\n[Lurker]({href})\n"
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


def test_image_move_projection_binds_one_existing_occurrence_and_retains_order():
    from application_state.build_proposal.image_move import BuildImageMovePlacement
    from application_state.content.page_presentation import Row, Slot

    media = "dmb-media:11111111-1111-4111-8111-111111111111"
    markdown = f'## Approach\n\n![Map]({media} "dmb-image:v1 width=80 collapsed=false")\n\n![Other occurrence]({media})\n'
    raw = markdown.encode()
    text, first, second = [
        BlockBinding(id=id_, byte_start=start, byte_end=end, sha256=sha256(raw[start:end]).hexdigest())
        for id_, (start, end) in zip(("approach", "first-map", "second-map"), source_block_spans(markdown), strict=True)
    ]
    before = PagePresentation(markdown_sha256=sha256(raw).hexdigest(), items=[
        Row(id="approach-row", min_height=16, line_mode="border", slots=[
            Slot(id="left-slot", width=7, blocks=[text, first]),
            Slot(id="right-slot", width=5, blocks=[]),
        ]),
        second,
    ]).checked(markdown)
    basis = BuildProposalBasis(world_id="world", document_id="page", registry_revision=1,
        content_sha256=before.markdown_sha256, draft_sha256=before.markdown_sha256, editor_sha256="a"*64,
        visibility="internal", caret=1, draft_generation=0, selection_generation=0)
    placement = BuildImageMovePlacement(basis=basis, presentation_sha256=before.fingerprint(),
        row_id="approach-row", source_slot_id="left-slot", destination_slot_id="right-slot",
        image_block_id="first-map")
    after, asset_id = placement.project_saved_move(before, markdown)
    assert asset_id == media[10:]
    assert after.markdown_sha256 == before.markdown_sha256
    assert after.items[1] == second
    assert after.items[0].slots[0].blocks == [text]
    assert after.items[0].slots[1].blocks == [first]
    assert after.items[0].min_height == 16 and after.items[0].line_mode == "border"
    assert before.items[0].slots[0].blocks == [text, first]

    for invalid in (
        placement.model_copy(update={"image_block_id":"second-map"}),
        placement.model_copy(update={"image_block_id":"approach"}),
        placement.model_copy(update={"destination_slot_id":"foreign-slot"}),
        placement.model_copy(update={"presentation_sha256":"b"*64}),
    ):
        with pytest.raises(ApplicationStateConflictError):
            invalid.project_saved_move(before, markdown)
    with pytest.raises(ApplicationStateConflictError):
        placement.project_saved_move(after, markdown)

    node = {"type":"paragraph","attrs":{"pageBlockId":"first-map"},"content":[
        {"type":"mediaImage","attrs":{"assetId":media[10:],"alt":"Map","width":80,"collapsed":False}},
    ]}
    editor_before = {"type":"doc","content":[{
        "type":"pageRow","attrs":{"id":"approach-row","min_height":16,"line_mode":"border"},"content":[
            {"type":"pageSlot","attrs":{"id":"left-slot","width":7},"content":[
                {"type":"heading","attrs":{"pageBlockId":"approach","level":2},"content":[{"type":"text","text":"Approach"}]},
                node,
            ]},
            {"type":"pageSlot","attrs":{"id":"right-slot","width":5}},
        ],
    }, {"type":"paragraph","attrs":{"pageBlockId":"second-map"},"content":[
        {"type":"mediaImage","attrs":{"assetId":media[10:],"alt":"Other occurrence"}},
    ]}]}
    original = json.dumps(editor_before)
    placement = placement.model_copy(update={"basis":basis.model_copy(update={"editor_sha256":sha256(original.encode()).hexdigest()})})
    editor_after = json.loads(original)
    left, right = editor_after["content"][0]["content"]
    right["content"] = [left["content"].pop()]
    assert placement.project_editor_move(original, before, markdown, asset_id) == editor_after
    with pytest.raises(ApplicationStateConflictError, match="exact offered"):
        placement.project_editor_move(original, before, markdown, str(uuid4()))

    def change_sibling_text(value):
        value["content"][0]["content"][0]["content"][0]["content"][0]["text"] = "Forged prose."

    def change_unrelated_image(value):
        value["content"][1]["content"][0]["attrs"]["alt"] = "Forged caption"

    def change_moved_image_width(value):
        value["content"][0]["content"][0]["content"][1]["content"][0]["attrs"]["width"] = 85

    def change_row(value):
        value["content"][0]["attrs"]["min_height"] = 24

    from application_state.build_proposal.image_move_decision import BuildImageMoveCapture, BuildImageMoveDecision, admitted_image_move_choice

    capture = BuildImageMoveCapture(
        basis=placement.basis, editor_json=original, conversation_id=uuid4(), expected_pointer_revision=1,
    )
    choices = {"image_move_intent":"move_existing", "image_move_destination":"same_row_right", "image_move_occurrence":"image1",
               "image_move_affirmation":"author_requests_move"}
    for prompt, expected in (
        ("Move the Map to the next slot on the right.", "ready"),
        ("Move the Map to the next slot on its right.", "ready"),
        ("In the Approach row, could we nudge the image to the empty right slot within the same row?", "ready"),
        ("I'd like you to reposition the Map onto the vacant right column in its original row.", "ready"),
        ("Could the Map be moved into the empty slot on its right?", "ready"),
        ("I'd like the Map slid into the next empty slot on its right.", "ready"),
        ("The Map belongs in the empty slot on its right.", "ready"),
        ("The Map, one slot right.", "ready"),
        ("The Map in the vacant right-hand slot immediately beside its current position.", "ready"),
        ("The Map sits in the vacant right-hand slot immediately beside its current position.", "discussion"),
        ("The Map is in the right column.", "discussion"),
        ("No movement of the Map to the right column.", "discussion"),
        ("The Map was in the empty slot on its right.", "discussion"),
        ("I don't want the Map in the right column.", "discussion"),
        ("How would the Map look in the slot on its right?", "discussion"),
        ("Please slide the Map one slot to the right in the Approach row.", "ready"),
        ("Push the Map to the empty slot immediately right of its current position.", "ready"),
        ("Move the Map next to Approach into the space directly to its right.", "ready"),
        ("Move the Map right one slot within this row.", "ready"),
        ("Slide the Map right into the vacant slot.", "ready"),
        ("Transfer the Map right; preserve unrelated figures.", "ready"),
        ("Transfer the Map right; keep all existing paragraphs intact.", "ready"),
        ("Transfer the Map right; retain the existing written material.", "ready"),
        ("Transfer the Map right; remove unrelated figures.", "unsupported"),
        ("Move the Map to the empty right column; retain the surrounding notes.", "ready"),
        ("Move the Map to the empty right column; retain the surrounding notes and then remove the heading.", "unsupported"),
        ("Move the Map to the empty left column; retain the surrounding notes.", "unsupported"),
        ("Move the Map to the vacant slot on the right in the first row.", "ready"),
        ("Move an image right by one slot.", "ambiguous"),
        ("What would happen if we moved the Map to the right?", "discussion"),
        ("Please do not move the Map to the right.", "discussion"),
        ("Could the Map not be moved to the right?", "discussion"),
        ("Under Approach, could we hypothetically move the Map to the right?", "discussion"),
        ("Move the Map to the right if I approve the redesign later.", "discussion"),
        ("Move the Map to another row on the right.", "different_row"),
        ("In another row, move the Map to the right slot.", "different_row"),
        ("In the Harbor Gate row, move the Map to the right slot.", "different_row"),
        ("Move the Map below the Harbor Gate heading to the right slot.", "missing"),
        ("In the “Approach” row, move the Map to the right slot.", "ready"),
        ("Move the Map to the right slot of the Harbor Gate row.", "different_row"),
        ("Place the Map in the Harbor Gate row on the right.", "different_row"),
        ("Move the Map to the right slot in row 2.", "different_row"),
        ("Move the Map to the right slot in the Harbor Gate page.", "unsupported"),
        ("Move the Map two columns to the right.", "unsupported"),
        ("Move the Map to the right and then remove it.", "unsupported"),
        ("Move the Map one slot to the right of the lantern.", "unsupported"),
        ("Move the Map into the top-right slot.", "unsupported"),
        ("Move the Map into the empty slot right before the lantern.", "unsupported"),
        ("Move the right bank map into the empty slot.", "unsupported"),
    ):
        decision = BuildImageMoveDecision.from_saved(capture, prompt, markdown, before)
        assert decision.resolve(choices).disposition == expected, prompt
        provider_view = json.dumps(decision.semantic_state())
        assert all(value not in provider_view for value in (asset_id, "first-map", "approach-row", "left-slot"))
    selected = capture.model_copy(update={"author_selected_block_id":"first-map"})
    decision = BuildImageMoveDecision.from_saved(selected, "Could you move this image right one slot?", markdown, before)
    assert decision.selected == "image1" and decision.resolve(choices).placement == placement
    assert decision.resolve(choices | {"image_move_affirmation": "description_or_discussion"}).placement is None
    assert decision.resolve({name: value for name, value in choices.items() if name != "image_move_affirmation"}).placement == placement
    discussion = choices | {"image_move_intent": "other"}
    assert admitted_image_move_choice(discussion, "How would it look in the empty slot?") == "unresolved"
    assert admitted_image_move_choice(discussion, "Could you write a note about how to move this map to the empty slot?") == "other"

    shared_title = "Gate-in North row"
    matching_markdown = (markdown.replace("## Approach", "## North").replace("![Map]", f"![{shared_title}]")
                         .replace("![Other occurrence]", f"![{shared_title}]"))
    matching_raw = matching_markdown.encode()
    heading, first_image, second_image = [
        block.model_copy(update={"byte_start": start, "byte_end": end, "sha256": sha256(matching_raw[start:end]).hexdigest()})
        for block, (start, end) in zip((text, first, second), source_block_spans(matching_markdown), strict=True)
    ]
    row = before.items[0]
    matching_layout = before.model_copy(update={
        "markdown_sha256": sha256(matching_raw).hexdigest(),
        "items": [row.model_copy(update={"slots": [row.slots[0].model_copy(update={"blocks": [heading, first_image]}),
                                                   row.slots[1]]}), second_image],
    })
    matching_editor = json.loads(original)
    matching_editor["content"][0]["content"][0]["content"][0]["content"][0]["text"] = "North"
    matching_editor["content"][0]["content"][0]["content"][1]["content"][0]["attrs"]["alt"] = shared_title
    matching_editor["content"][1]["content"][0]["attrs"]["alt"] = shared_title
    matching_json = json.dumps(matching_editor)
    matching_capture = BuildImageMoveCapture(
        basis=basis.model_copy(update={"content_sha256": matching_layout.markdown_sha256,
                                      "draft_sha256": matching_layout.markdown_sha256,
                                      "editor_sha256": sha256(matching_json.encode()).hexdigest()}),
        editor_json=matching_json, conversation_id=uuid4(), expected_pointer_revision=1,
    )
    for prompt, expected in (
        ("Move the Gate to the right slot.", "ambiguous"),
        ("Move the image titled “Gate in North row” to the right slot.", "ambiguous"),
        ('Move the image titled "Gate in North row" to the right slot.', "ambiguous"),
        ("Move the image titled Gate in North row to the right slot.", "ambiguous"),
        ("Move the Gate image, not the one near North, to the right slot.", "ambiguous"),
        ("Move the image with the “North” caption to the right slot.", "ambiguous"),
        ("Move the image under the “North” heading to the right slot.", "ready"),
    ):
        decision = BuildImageMoveDecision.from_saved(matching_capture, prompt, matching_markdown, matching_layout)
        assert decision.resolve(choices).disposition == expected, prompt

    from dataclasses import replace
    from application_state.build_proposal.image_move_decision import CONTEXTUAL_IDENTITY

    decision = BuildImageMoveDecision.from_saved(capture, "Move the map beside the departure advice to the empty slot on its right.",
                                                markdown, before)
    first_occurrence = replace(decision.occurrences[0], row_context="Leave at dusk after the harbor bell rings three times.")
    second_occurrence = replace(
        first_occurrence, alias="image2", row_number=2,
        row_context="Ask the innkeeper to lend a dry coat for the crossing.",
    )
    decision = replace(decision, occurrences=(first_occurrence, second_occurrence), other_media=(),
                       row_media_counts={1: 1, 2: 1})
    proved = choices | {CONTEXTUAL_IDENTITY: "image1"}
    assert decision.resolve(proved).disposition == "ready"
    assert replace(
        decision, question="Move the map alongside the departure advice to the empty slot on its right.",
    ).resolve(proved).disposition == "ready"
    assert replace(
        decision, question="For the departure advice, the map belongs in the empty slot to its right.",
    ).resolve(proved).disposition == "ready"
    assert decision.resolve(choices).disposition == "ambiguous"
    assert decision.resolve(proved | {CONTEXTUAL_IDENTITY: "image2"}).disposition == "ambiguous"
    assert replace(decision, question="Move the map to the empty slot on its right.").resolve(proved).disposition == "ambiguous"
    indistinguishable = replace(second_occurrence, row_context=first_occurrence.row_context)
    assert replace(decision, occurrences=(first_occurrence, indistinguishable)).resolve(proved).disposition == "ambiguous"

    def opening(include_contextual_identity, *, modern_language=True):
        return {
            "state": {"user_question": decision.question, "interaction": {"image_move": decision.semantic_state()}},
            "questions": {
                q.name: {"type": "choice", "instructions": q.question, "criteria": dict.fromkeys(q.options)}
                for q in decision.questions(include_contextual_identity=include_contextual_identity,
                                            modern_language=modern_language)
            },
        }

    decision.require_opening_offer(opening(True))
    decision.require_opening_offer(opening(False), allow_retained=True)
    predecessor = opening(True, modern_language=False)
    decision.require_opening_offer(predecessor, allow_retained=True)
    with pytest.raises(ValueError, match="exact admitted opening"):
        decision.require_opening_offer(predecessor)
    predecessor["questions"]["image_move_destination"] = opening(True)["questions"]["image_move_destination"]
    with pytest.raises(ValueError, match="exact admitted opening"):
        decision.require_opening_offer(predecessor, allow_retained=True)
    with pytest.raises(ValueError, match="exact admitted opening"):
        decision.require_opening_offer(opening(False))

    for alter in (change_sibling_text, change_unrelated_image, change_moved_image_width, change_row):
        forged = json.loads(original)
        alter(forged)
        raw_editor = json.dumps(forged)
        forged_placement = placement.model_copy(update={
            "basis": basis.model_copy(update={"editor_sha256":sha256(raw_editor.encode()).hexdigest()}),
        })
        with pytest.raises(ApplicationStateConflictError, match="exact offered"):
            forged_placement.project_editor_move(raw_editor, before, markdown, asset_id)


def test_image_move_layout_rejects_extra_image_stack_fields():
    from application_state.build_proposal.image_move_layout import require_build_image_layout
    from application_state.content.page_presentation import ImageText

    asset = "11111111-1111-4111-8111-111111111111"
    markdown = f"![Map](dmb-media:{asset})\n\nSurvey caption.\n"
    raw = markdown.encode()
    image, caption = [
        BlockBinding(id=id_, byte_start=start, byte_end=end, sha256=sha256(raw[start:end]).hexdigest())
        for id_, (start, end) in zip(("map", "caption"), source_block_spans(markdown), strict=True)
    ]
    stack = ImageText(id="stack", image=image, text=caption)
    layout = PagePresentation(markdown_sha256=sha256(raw).hexdigest(), items=[stack]).checked(markdown)
    node = {"type":"pageImageText","attrs":{"id":"stack","anchor":stack.anchor,"inset":stack.inset,"backing":stack.backing},
        "content":[
            {"type":"paragraph","attrs":{"pageBlockId":"map"},"content":[
                {"type":"mediaImage","attrs":{"assetId":asset,"alt":"Map"}},
            ]},
            {"type":"paragraph","attrs":{"pageBlockId":"caption"},"content":[{"type":"text","text":"Survey caption."}]},
        ]}
    editor = {"type":"doc","content":[node]}
    require_build_image_layout(editor, markdown, layout)
    node["marks"] = [{"type":"bold"}]
    with pytest.raises(ValueError, match="unsupported data"):
        require_build_image_layout(editor, markdown, layout)


def test_image_move_review_consumes_once_and_confirms_only_exact_protected_save(application_state_dsn):
    from io import BytesIO
    from PIL import Image
    from application_state import media
    from application_state.build_proposal.image_move import BuildImageMovePlacement
    from application_state.build_proposal.image_move_review import BuildImageMoveReviewService
    from application_state.content.page_presentation import Row, Slot
    from application_state.world_catalog.service import create_world

    world = create_world(name="Image move test", owner_subject="subject:owner").record.world_id
    conversation = _new(AgentConversationService(), world)
    page = pages.create_page(world_id=world, title="Survey")
    document = str(page.page.work_object_id)
    png = BytesIO()
    Image.new("RGB", (8, 8), (60, 110, 180)).save(png, format="PNG")
    asset = str(media.stage_image(png.getvalue(), "local_operator", {"fixture":"image move Review"})["asset_id"])
    markdown = f"![Survey map](dmb-media:{asset})\n"
    raw = markdown.encode()
    start, end = source_block_spans(markdown)[0]
    image = BlockBinding(id="map", byte_start=start, byte_end=end, sha256=sha256(raw[start:end]).hexdigest())
    presentation = PagePresentation(markdown_sha256=sha256(raw).hexdigest(), items=[
        Row(id="row", slots=[
            Slot(id="left", width=6, blocks=[image]),
            Slot(id="right", width=6, blocks=[]),
        ]),
    ])
    pages.commit_page(document, markdown, world_id=world, expected_revision=page.page.object_revision,
        expected_working_copy_revision=None, page_presentation=presentation)
    saved = pages.committed_page(document, world_id=world)
    editor = json.dumps({"type":"doc","content":[{"type":"pageRow","attrs":{"id":"row","min_height":0,"line_mode":"guide"},"content":[
        {"type":"pageSlot","attrs":{"id":"left","width":6},"content":[{"type":"paragraph","attrs":{"pageBlockId":"map"},
            "content":[{"type":"mediaImage","attrs":{"assetId":asset,"alt":"Survey map"}}]}]},
        {"type":"pageSlot","attrs":{"id":"right","width":6}},
    ]}]})
    placement = BuildImageMovePlacement(
        basis=BuildProposalBasis(world_id=world, document_id=document, registry_revision=saved.page.object_revision,
            content_sha256=presentation.markdown_sha256, draft_sha256=presentation.markdown_sha256,
            editor_sha256=sha256(editor.encode()).hexdigest(), visibility="internal",
            caret=1, draft_generation=0, selection_generation=0),
        presentation_sha256=presentation.fingerprint(), row_id="row", source_slot_id="left",
        destination_slot_id="right", image_block_id="map",
    )
    after = json.dumps(placement.project_editor_move(editor, presentation, markdown, asset))
    store = BuildImageMoveReviewService()
    action, claim = uuid4(), uuid4()

    def admitted(_conn, review):
        assert review.placement.basis.world_id == world

    def stage():
        with unit_of_work(application_state_dsn) as conn:
            return store.stage_in_transaction(conn, action, conversation.conversation_id, 1, placement, editor, admit=admitted)

    with pytest.raises(RuntimeError, match="rollback"):
        with unit_of_work(application_state_dsn) as conn:
            store.stage_in_transaction(conn, action, conversation.conversation_id, 1, placement, editor, admit=admitted)
            raise RuntimeError("rollback")
    with pytest.raises(ApplicationStateNotFoundError):
        store.get(world, action)

    opened = stage()
    assert stage() == opened
    with pytest.raises(ApplicationStateNotFoundError):
        store.get("foreign", action)
    assert pages.committed_page(document, world_id=world) == saved
    with pytest.raises(ApplicationStateConflictError, match="postimage"):
        store.claim(world, action, opened.revision, claim, editor, editor, authorize=admitted)

    def try_claim():
        return store.claim(world, action, opened.revision, claim, editor, after, authorize=admitted)

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: try_claim(), range(2)))
    assert sorted(issued for _, issued in claims) == [False, True]
    assert claims[0][0] == claims[1][0]
    with pytest.raises(ApplicationStateConflictError, match="consumed"):
        store.claim(world, action, opened.revision, uuid4(), editor, after, authorize=admitted)
    with pytest.raises(ApplicationStateConflictError, match="not the committed Page"):
        store.confirm(world, action, claim, authorize=admitted)
    assert pages.committed_page(document, world_id=world) == saved

    projected, _ = placement.project_saved_move(presentation, markdown)
    pages.commit_page(document, markdown, world_id=world, expected_revision=saved.page.object_revision,
        expected_working_copy_revision=saved.working_copy_revision, page_presentation=projected,
        layout_writer_profile=pages.PAGE_LAYOUT_WRITER_PROFILE)
    confirmed = store.confirm(world, action, claim, authorize=admitted)
    assert confirmed.state == "saved" and confirmed.saved_revision == saved.page.object_revision + 1
    assert store.confirm(world, action, claim, authorize=admitted) == confirmed
    assert store.claim(world, action, opened.revision, claim, editor, after, authorize=admitted) == (confirmed, False)
    assert pages.committed_page(document, world_id=world).presentation == projected


def test_proposal_transaction_hooks_authorize_and_roll_back(reservation):
    seen = []
    def authorize(_conn, *, read_only):
        seen.append(('authorize', read_only))
    def reject(_conn):
        seen.append(('validate', False))
        raise ApplicationStateConflictError('guest quota exceeded')

    store = BuildProposalService(authorize_transaction=authorize, validate_transaction=reject)
    with pytest.raises(ApplicationStateConflictError, match='guest quota exceeded'):
        store.reserve(reservation)
    assert seen == [('authorize', False), ('validate', False)]
    with pytest.raises(ApplicationStateNotFoundError):
        BuildProposalService().get(reservation.basis.world_id, reservation.idempotency_key)
    with pytest.raises(ApplicationStateNotFoundError):
        store.get(reservation.basis.world_id, reservation.idempotency_key)
    assert seen[-1] == ('authorize', True)
