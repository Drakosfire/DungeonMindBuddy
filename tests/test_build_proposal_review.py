"""Actual APP CAS and authenticated HTTP review, without source/provider writes."""

import asyncio
from uuid import uuid4
import pytest
from application_state.build_proposal.review import (
    BuildProposalReviewService,
    BuildReviewCommand,
)
from application_state.build_proposal.service import BuildProposalService
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from tests.test_build_document_proposal import request_case as _proposal_case, Wire
from apps.live_control_server.services import build_document_proposal as owner


@pytest.fixture
def request_case(tmp_path, monkeypatch, application_state_dsn):
    return _proposal_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture
def review_case(request_case):
    request, source, root = request_case
    request = request.model_copy(
        update={"basis": request.basis.model_copy(update={"editor_sha256": "e" * 64})}
    )
    wire = Wire(request)
    proposal = asyncio.run(owner.compose(request, transport=wire))
    service = BuildProposalReviewService()

    def command(operation, revision=0, **fields):
        return service.execute(
            "elderwyld",
            proposal.action_id,
            BuildReviewCommand(
                operation=operation, expected_revision=revision, **fields
            ),
        )

    return command, service, proposal, source, root, wire


def test_review_edit_cas_reload_and_original_evidence_are_distinct(review_case):
    command, service, proposal, source, root, wire = review_case
    opened = command("open")
    changed = command(
        "save",
        opened.revision,
        markdown="## Culture\n\nThe author’s revised suggestion.",
    )
    assert changed.markdown != proposal.proposal.replacement_markdown
    assert service.get("elderwyld", proposal.action_id) == changed
    assert command("open") == changed
    with pytest.raises(ApplicationStateConflictError):
        command("save", opened.revision, markdown="Stale copy")
    assert BuildProposalService().get("elderwyld", proposal.action_id) == proposal
    assert (root / source.record.target_relpath).read_text() == source.markdown
    assert len(wire.calls) == 1


def test_discard_is_durable_terminal_and_does_not_touch_source(review_case):
    command, service, proposal, source, root, wire = review_case
    opened = command("open")
    discarded = command("discard", opened.revision)
    assert discarded.state == "discarded" and command("open") == discarded
    for operation, fields in [
        ("save", {"markdown": "Changed"}),
        (
            "prepare",
            {
                "apply_id": uuid4(),
                "after_editor_sha256": "a" * 64,
                "after_draft_sha256": "b" * 64,
            },
        ),
    ]:
        with pytest.raises(ApplicationStateConflictError):
            command(operation, discarded.revision, **fields)
    assert (root / source.record.target_relpath).read_text() == source.markdown
    assert (
        not BuildProposalService()
        .get("elderwyld", proposal.action_id)
        .inserted_in_draft
    )
    assert len(wire.calls) == 1


def test_apply_reservation_and_ack_recover_without_reinterpreting_bytes(review_case):
    command, service, proposal, source, root, wire = review_case
    opened = command("open")
    identity = uuid4()
    fields = {
        "apply_id": identity,
        "after_editor_sha256": "a" * 64,
        "after_draft_sha256": "b" * 64,
    }
    pending = command("prepare", opened.revision, **fields)
    assert (
        pending.state == "applying" and pending.apply.before_editor_sha256 == "e" * 64
    )
    assert command("prepare", opened.revision, **fields) == pending
    assert command("open") == pending
    with pytest.raises(ApplicationStateConflictError):
        command(
            "prepare", opened.revision, **{**fields, "after_editor_sha256": "c" * 64}
        )
    with pytest.raises(ApplicationStateConflictError):
        command("prepare", pending.revision, **{**fields, "apply_id": uuid4()})
    with pytest.raises(ApplicationStateConflictError):
        command("confirm", pending.revision, apply_id=uuid4())
    applied = command("confirm", pending.revision, apply_id=identity)
    assert applied.state == "applied"
    assert command("confirm", pending.revision, apply_id=identity) == applied
    saved = BuildProposalService().get("elderwyld", proposal.action_id)
    assert saved.inserted_in_draft and saved.proposal == proposal.proposal
    assert saved.request_fingerprint == proposal.request_fingerprint
    assert (root / source.record.target_relpath).read_text() == source.markdown
    assert len(wire.calls) == 1


def test_foreign_world_and_conversation_drift_cannot_mutate(review_case):
    command, service, proposal, _, _, _ = review_case
    opened = command("open")
    with pytest.raises(ApplicationStateNotFoundError):
        service.get("foreign", proposal.action_id)
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import ConversationCommand

    AgentConversationService().new_conversation(
        ConversationCommand(
            world_id="elderwyld",
            command_id=uuid4(),
            expected_pointer_revision=1,
            expected_active_conversation_id=proposal.reservation.conversation_id,
        )
    )
    with pytest.raises(ApplicationStateConflictError):
        command("save", opened.revision, markdown="Foreign pointer")
    assert service.get("elderwyld", proposal.action_id) == opened


def test_review_routes_authentication_exact_scope_and_reopen(review_case, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent, build_proposal_reviews

    command, _, proposal, _, _, _ = review_case
    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv(
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
        "synthetic-only-review-token-00000000000",
    )
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")
    root = (
        f"/api/live/agent/worlds/elderwyld/build-proposals/{proposal.action_id}/review"
    )
    with TestClient(app) as client:
        assert (
            client.post(
                root, json={"operation": "open", "expected_revision": 0}
            ).status_code
            == 403
        )
        monkeypatch.setattr(
            build_proposal_reviews, "enforce_native_graph_gm", lambda _: None
        )
        opened = client.post(root, json={"operation": "open", "expected_revision": 0})
        assert opened.status_code == 200, opened.text
        assert client.get(root).json() == opened.json()
        assert client.get(root + "?revision=1").status_code == 422
        assert (
            client.post(
                root,
                json={
                    "operation": "discard",
                    "expected_revision": 1,
                    "markdown": "Extra selector",
                },
            ).status_code
            == 422
        )
        assert client.get(root.replace("/elderwyld/", "/foreign/")).status_code == 404
        discarded = client.post(
            root, json={"operation": "discard", "expected_revision": 1}
        )
        assert discarded.status_code == 200 and discarded.json()["state"] == "discarded"
        assert (
            client.post(
                root,
                json={"operation": "save", "expected_revision": 1, "markdown": "Stale"},
            ).status_code
            == 409
        )


def test_review_move_is_durable_cas_and_bound_into_apply(review_case):
    command, service, proposal, source, root, wire = review_case
    original = proposal.reservation.basis.caret
    opened = command("open")
    assert opened.placement_caret == original
    moved = command("move", opened.revision, placement_caret=original + 3)
    assert service.get("elderwyld", proposal.action_id) == moved
    assert command("open").placement_caret == original + 3
    with pytest.raises(ApplicationStateConflictError):
        command("move", opened.revision, placement_caret=original + 4)
    prepared = command(
        "prepare",
        moved.revision,
        apply_id=uuid4(),
        after_editor_sha256="a" * 64,
        after_draft_sha256="b" * 64,
    )
    assert prepared.apply.placement_caret == moved.placement_caret
    with pytest.raises(ApplicationStateConflictError):
        command("move", prepared.revision, placement_caret=original)
    assert BuildProposalService().get("elderwyld", proposal.action_id) == proposal
    assert (root / source.record.target_relpath).read_text() == source.markdown
    assert len(wire.calls) == 1


def test_move_command_rejects_invalid_or_unrelated_fields():
    from pydantic import ValidationError

    for fields in (
        {"placement_caret": -1},
        {"placement_caret": True},
        {"placement_caret": 1, "markdown": "Wrong operation"},
        {},
    ):
        with pytest.raises(ValidationError):
            BuildReviewCommand(operation="move", expected_revision=1, **fields)


@pytest.mark.parametrize("applying", [False, True])
def test_retained_review_migration_keeps_exact_original_placement(
    review_case, application_state_dsn, applying
):
    import psycopg
    from psycopg.types.json import Jsonb
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    command, service, proposal, source, root, wire = review_case
    opened = command("open")
    if applying:
        opened = command(
            "prepare",
            opened.revision,
            apply_id=uuid4(),
            after_editor_sha256="a" * 64,
            after_draft_sha256="b" * 64,
        )
    historical = opened.model_dump(mode="json")
    historical["schema"] = "dmb_build_proposal_review_v1"
    historical.pop("placement_caret")
    if historical["apply"]:
        historical["apply"].pop("placement_caret")
    # Reconstruct the previous schema only inside this disposable test database.
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "ALTER TABLE agent.build_proposal_review DROP CONSTRAINT build_review_current_placement"
        )
        conn.execute(
            "UPDATE agent.build_proposal_review SET payload=%s WHERE action_id=%s",
            (Jsonb(historical), proposal.action_id),
        )
        conn.execute(
            "ALTER TABLE agent.build_proposal_review ADD CONSTRAINT old_review_schema CHECK(payload->>'schema'='dmb_build_proposal_review_v1')"
        )
    # Exercise the exact historical migration, without falsely stamping all later tables old.
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            import_module('application_state.migrations.versions.20261023_0060_build_review_placement').upgrade()
    finally:
        engine.dispose()
    restored = service.get("elderwyld", proposal.action_id)
    assert restored == opened
    assert restored.placement_caret == proposal.reservation.basis.caret
    assert BuildProposalService().get("elderwyld", proposal.action_id) == proposal
    assert (root / source.record.target_relpath).read_text() == source.markdown


def test_selected_revision_review_stays_pinned_and_recovers_exact_apply(request_case):
    from application_state.build_proposal.types import BuildProposalSelection
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    request, source, root = request_case
    request = request.model_copy(update={"basis": request.basis.model_copy(update={
        "editor_sha256":"e"*64, "selection":BuildProposalSelection(end=12,text="A fort town")})})
    wire = Wire(request)
    record = asyncio.run(owner.compose(request, transport=wire))
    service = BuildProposalReviewService()
    def command(operation, revision=0, **kwargs):
        return service.execute("elderwyld",record.action_id,BuildReviewCommand(
            operation=operation,expected_revision=revision,**kwargs))
    opened = command("open")
    with pytest.raises(ApplicationStateConflictError,match="captured selection"):
        command("move",opened.revision,placement_caret=3)
    assert service.get("elderwyld",record.action_id) == opened
    changed = command("save",opened.revision,markdown="A revised flooded town.")
    apply_id=uuid4()
    prepared = command("prepare",changed.revision,apply_id=apply_id,
        after_editor_sha256="f"*64,after_draft_sha256="a"*64)
    assert command("prepare",changed.revision,apply_id=apply_id,
        after_editor_sha256="f"*64,after_draft_sha256="a"*64) == prepared
    kept = command("confirm",prepared.revision,apply_id=apply_id)
    assert command("confirm",prepared.revision,apply_id=apply_id) == kept
    assert get_workspace_document_snapshot(root,source.record.document_id) == source
    assert BuildProposalService().get("elderwyld",record.action_id).reservation.basis.selection == request.basis.selection
    assert len(wire.calls)==1


def test_fresh_placement_preserves_uncertain_receipt_without_regeneration(review_case, application_state_dsn):
    from application_state.build_proposal.review import PlacementCapability
    command, _, proposal, source, root, wire = review_case
    opened = command("open")
    pending = command("prepare", opened.revision, apply_id=uuid4(),
        after_editor_sha256="a"*64, after_draft_sha256="b"*64)
    from hashlib import sha256
    from apps.live_control_server.services.workspace_document_registry import mark_workspace_document_committed, get_workspace_document_snapshot
    newer_text=source.markdown+"\nNewer saved author writing.\n"
    (root/source.record.target_relpath).write_text(newer_text)
    mark_workspace_document_committed(root,source.record.document_id,expected_revision=source.record.revision)
    newer=get_workspace_document_snapshot(root,source.record.document_id)
    cap = PlacementCapability(command_id=uuid4(), conversation_id=proposal.reservation.conversation_id,
        expected_pointer_revision=proposal.reservation.expected_pointer_revision,
        basis=proposal.reservation.basis.model_copy(update={"registry_revision":newer.record.revision,
            "content_sha256":newer.content_sha256,"draft_sha256":sha256(newer.markdown.encode()).hexdigest()}),
        draft_markdown=newer.markdown)
    service = BuildProposalReviewService(validate_source=owner._source)
    request = BuildReviewCommand(operation="replace_placement", expected_revision=pending.revision, placement=cap)
    fresh = service.execute("elderwyld",proposal.action_id,request)
    assert fresh.state == "editing" and fresh.schema_version == "dmb_build_proposal_review_v3"
    assert fresh.markdown == pending.markdown and fresh.apply is None
    assert fresh.retired_placements[0].apply == pending.apply
    assert fresh.retired_placements[0].disposition == "superseded_unresolved"
    assert service.execute("elderwyld",proposal.action_id,request) == fresh
    with pytest.raises(ApplicationStateConflictError):
        command("confirm",fresh.revision,apply_id=pending.apply.apply_id)
    with pytest.raises(ApplicationStateConflictError):
        command("prepare",fresh.revision,apply_id=pending.apply.apply_id,
            after_editor_sha256="a"*64,after_draft_sha256="b"*64)
    assert BuildProposalService().get("elderwyld",proposal.action_id) == proposal
    assert (root/source.record.target_relpath).read_text() == newer.markdown
    assert len(wire.calls)==1
    # A fresh placement is durable new vocabulary; an older runtime may not erase it.
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError,match="recovery forward"):
                import_module('application_state.migrations.versions.20261025_0069_proposal_replacement_placement').downgrade()
    finally:engine.dispose()
    changed_cap=cap.model_copy(update={"basis":cap.basis.model_copy(update={"caret":cap.basis.caret+1})})
    with pytest.raises(ApplicationStateConflictError,match="different bytes"):
        service.execute("elderwyld",proposal.action_id,request.model_copy(update={"placement":changed_cap}))
    next_id=uuid4()
    prepared=service.execute("elderwyld",proposal.action_id,BuildReviewCommand(operation="prepare",
        expected_revision=fresh.revision,apply_id=next_id,after_editor_sha256="c"*64,after_draft_sha256="d"*64))
    assert prepared.apply.before_draft_sha256==cap.basis.draft_sha256
    finished=service.execute("elderwyld",proposal.action_id,BuildReviewCommand(operation="confirm",
        expected_revision=prepared.revision,apply_id=next_id))
    assert finished.state=="applied" and finished.retired_placements==fresh.retired_placements
    assert len(wire.calls)==1


@pytest.mark.parametrize("mutation",["world","page","revision","content","pointer","conversation","no_validator"])
def test_fresh_placement_rejects_changed_authority_at_app_boundary(review_case,mutation):
    from application_state.build_proposal.review import PlacementCapability
    command, service, proposal, source, root, wire = review_case
    opened = command("open")
    # This is the exact source-owner draft used by the original ordinary request.
    markdown = source.markdown
    cap = PlacementCapability(command_id=uuid4(), conversation_id=proposal.reservation.conversation_id,
        expected_pointer_revision=proposal.reservation.expected_pointer_revision,
        basis=proposal.reservation.basis, draft_markdown=markdown)
    if mutation in {"world","page","revision","content"}:
        field={"world":"world_id","page":"document_id","revision":"registry_revision","content":"content_sha256"}[mutation]
        value=cap.basis.registry_revision+1 if mutation=="revision" else "f"*64 if mutation=="content" else "foreign"
        cap=cap.model_copy(update={"basis":cap.basis.model_copy(update={field:value})})
    elif mutation=="pointer":cap=cap.model_copy(update={"expected_pointer_revision":999})
    elif mutation=="conversation":cap=cap.model_copy(update={"conversation_id":uuid4()})
    def validate(capability):
        try:owner._source(capability)
        except owner.BuildComposeError as exc:raise ApplicationStateConflictError(str(exc)) from exc
    checker=BuildProposalReviewService(validate_source=None if mutation=="no_validator" else validate)
    with pytest.raises((ApplicationStateConflictError,ApplicationStateNotFoundError)):
        checker.execute("elderwyld",proposal.action_id,BuildReviewCommand(operation="replace_placement",
            expected_revision=opened.revision,placement=cap))
    assert service.get("elderwyld",proposal.action_id)==opened
    assert len(wire.calls)==1


def test_exact_pending_snapshot_requires_reconciliation_not_fresh_insertion(review_case):
    from application_state.build_proposal.review import PlacementCapability
    command, _, proposal, source, _, _ = review_case
    opened=command("open")
    pending=command("prepare",opened.revision,apply_id=uuid4(),after_editor_sha256="a"*64,after_draft_sha256="b"*64)
    cap=PlacementCapability(command_id=uuid4(),conversation_id=proposal.reservation.conversation_id,
        expected_pointer_revision=proposal.reservation.expected_pointer_revision,basis=proposal.reservation.basis,draft_markdown=source.markdown)
    with pytest.raises(ApplicationStateConflictError,match="Reconcile the exact"):
        BuildProposalReviewService(validate_source=owner._source).execute("elderwyld",proposal.action_id,
            BuildReviewCommand(operation="replace_placement",expected_revision=pending.revision,placement=cap))


def test_whole_page_review_resolves_target_and_never_becomes_a_moved_insertion(request_case):
    import json
    from application_state.build_proposal.types import BuildPageBodyOffer
    request, source, root = request_case
    request=request.model_copy(update={'basis':request.basis.model_copy(update={'editor_sha256':'e'*64}),
        'page_body_offer':BuildPageBodyOffer(end=83)})
    wire=Wire(request,text=json.dumps(dict(destination='current_page',target='page_body',
        replacement_markdown='First.\n\nSecond.',summary='Replace whole body.',assumptions=[])))
    proposal=asyncio.run(owner.compose(request,transport=wire))
    service=BuildProposalReviewService()
    def command(op,revision=0,**fields):
        return service.execute('elderwyld',proposal.action_id,
            BuildReviewCommand(operation=op,expected_revision=revision,**fields))
    review=command('open')
    assert review.page_body_target==request.page_body_offer
    assert review.placement_caret==request.basis.caret
    with pytest.raises(ApplicationStateConflictError,match='stays at its captured body'):
        command('move',review.revision,placement_caret=2)
    # Changing placement is forbidden even before it can validate another source.
    from application_state.build_proposal.review import PlacementCapability
    cap=PlacementCapability(command_id=uuid4(),conversation_id=request.conversation_id,
        expected_pointer_revision=1,basis=request.basis,draft_markdown=request.draft_markdown)
    with pytest.raises(ApplicationStateConflictError,match='stays at its captured body'):
        command('replace_placement',review.revision,placement=cap)
    review=command('save',review.revision,markdown='Edited first.\n\nEdited second.')
    apply_id=uuid4()
    pending=command('prepare',review.revision,apply_id=apply_id,
        after_editor_sha256='a'*64,after_draft_sha256='b'*64)
    assert pending.apply.page_body_target==request.page_body_offer
    assert service.get('elderwyld',proposal.action_id)==pending
    assert command('prepare',review.revision,apply_id=apply_id,
        after_editor_sha256='a'*64,after_draft_sha256='b'*64)==pending
    applied=command('confirm',pending.revision,apply_id=apply_id)
    assert applied.state=='applied' and applied.apply.page_body_target==request.page_body_offer
    assert len(wire.calls)==1
    assert (root/source.record.target_relpath).read_text()==source.markdown
