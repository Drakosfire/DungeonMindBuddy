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
    from application_state.cli import upgrade_to_head

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
        conn.execute(
            "UPDATE application_state.schema_migrations SET version_num='20261023_0059'"
        )
    upgrade_to_head(dsn=application_state_dsn)
    restored = service.get("elderwyld", proposal.action_id)
    assert restored == opened
    assert restored.placement_caret == proposal.reservation.basis.caret
    assert BuildProposalService().get("elderwyld", proposal.action_id) == proposal
    assert (root / source.record.target_relpath).read_text() == source.markdown
