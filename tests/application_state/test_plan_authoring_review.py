"""Actual completed Agent proposal, Plan review and Content transaction ownership."""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation.plan_authoring import (
    PlanActionAuthoringResultV1,
    PlanAuthoringSlotBoundaryCaptureV1,
    text_digest,
)
from application_state.content import repository as content
from application_state.content.markdown_source_blocks import source_block_spans
from application_state.content.page_presentation import PagePresentation
from application_state.content.service import commit_plan, current_committed_revision, get_plan, snapshot_content
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.plan_action_dialogue import repository as actions
from application_state.plan_action_dialogue import authoring_review as owner
from application_state.unit_of_work import unit_of_work
from tests.test_hosted_native_graph_access import hosted, recap_lane  # noqa: F401
from tests.test_plan_jev_authoring import authoring_writer
from tests.test_plan_jev_writer import WriterWire, graph_answer

pytest_plugins = ("tests.test_plan_jev_dispatch",)


@pytest.fixture
def completed_proposal(plan_adapter, request):
    writer, action, capture = authoring_writer(plan_adapter, placement=getattr(request,"param","captured"))
    answer = graph_answer()
    answer["answer_segments"].append({
        "kind": "proposal", "label": "invented_idea",
        "text": "## Possible approach\n\nAsk about the pond.",
    })
    asyncio.run(writer.run(
        transport=WriterWire(plan_adapter, json.dumps(answer)), api_key="synthetic-not-secret",
    ))
    return plan_adapter.service.get_plan_authoring_proposal(capture.world_id, action.action_id)


def command(proposal, review, operation, **values):
    return dict(operation=operation, command_id=uuid4(),
        origin_sha256=proposal.origin.sha256,
        expected_revision=review.revision if review else 0, **values)


def execute(proposal, payload):
    return owner.execute_review_command(proposal.capture.world_id, proposal.origin.action_id, payload)


def opened(proposal):
    return execute(proposal, command(proposal, None, "open"))


def prepare(proposal, review, **overrides):
    after = review.capture.draft_markdown + "\n\n" + review.markdown
    editor = json.dumps({"type": "doc", "content": [{"type": "paragraph", "content": [
        {"type": "text", "text": after}]}]})
    values = dict(application_id=uuid4(), after_editor_json=editor,
        after_editor_sha256=text_digest(editor), after_markdown=after,
        after_draft_sha256=text_digest(after), after_title="Edited preparation")
    values.update(overrides)
    return execute(proposal, command(proposal, review, "prepare", **values))


def test_review_edit_replay_conflicts_and_world_owner(completed_proposal):
    proposal = completed_proposal
    initial = opened(proposal)
    edit = command(proposal, initial, "save", markdown="## Author's version\n")
    saved = execute(proposal, edit)
    assert execute(proposal, edit) == saved
    assert owner.read_review(saved.world_id, saved.action_id).review == saved
    assert saved.markdown != proposal.replacement_markdown
    with pytest.raises(ApplicationStateConflictError, match="identity was reused"):
        execute(proposal, edit | {"markdown": "Changed under same identity"})
    with pytest.raises(ApplicationStateConflictError, match="review changed"):
        execute(proposal, command(proposal, initial, "discard"))
    with pytest.raises(ApplicationStateNotFoundError):
        owner.execute_review_command("foreign-world", saved.action_id, edit)
    with pytest.raises(ApplicationStateConflictError, match="generated Plan proposal changed"):
        execute(proposal, command(proposal, saved, "discard") | {"origin_sha256": "0" * 64})
    assert owner.read_review(saved.world_id, saved.action_id).review == saved


def test_application_save_and_receipt_replay_exactly_once(completed_proposal, application_state_dsn):
    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    application = pending.applications[-1]
    before = current_committed_revision(proposal.capture.document_id, kind="plan")
    assert before.work_revision.markdown != application.after_markdown
    confirm = command(proposal, pending, "confirm", application_id=application.application_id)
    saved = execute(proposal, confirm)
    assert saved.state == "applied"
    assert execute(proposal, confirm) == saved
    reloaded = owner.read_review(saved.world_id, saved.action_id).review
    actual = current_committed_revision(proposal.capture.document_id, kind="plan")
    assert reloaded == saved
    assert actual.work_revision.markdown == application.after_markdown
    assert actual.work_revision.work_revision_id == saved.applications[-1].saved_work_revision_id
    assert get_plan(proposal.capture.document_id).title == application.after_title
    with unit_of_work(application_state_dsn) as conn:
        assert content.next_revision_n(conn, actual.work_object.work_object_id) == actual.work_revision.revision_n + 1
    assert reloaded.applications[-1].after_editor_json == application.after_editor_json
    with pytest.raises(ApplicationStateConflictError, match="not pending"):
        execute(proposal, command(proposal, saved, "recover_placement",
            application_id=application.application_id, capture=inspected_capture(proposal)))


def test_receipt_failure_rolls_back_content_and_same_application_can_retry(
    completed_proposal, monkeypatch,
):
    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    before = current_committed_revision(proposal.capture.document_id, kind="plan")
    before_object = get_plan(proposal.capture.document_id)
    confirm = command(proposal, pending, "confirm", application_id=pending.applications[-1].application_id)
    original = owner._persist_review
    with monkeypatch.context() as failure:
        def reject_receipt(conn, action, review, **kwargs):
            assert review.state == "applied"
            raise RuntimeError("receipt failed after Content update")
        failure.setattr(owner, "_persist_review", reject_receipt)
        with pytest.raises(RuntimeError, match="receipt failed"):
            execute(proposal, confirm)
    assert current_committed_revision(proposal.capture.document_id, kind="plan") == before
    assert get_plan(proposal.capture.document_id) == before_object
    assert owner.read_review(pending.world_id, pending.action_id).review == pending
    assert owner._persist_review is original
    assert execute(proposal, confirm).state == "applied"


def test_cancelled_application_fences_late_save_and_retains_edited_work(completed_proposal):
    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    application = pending.applications[-1]
    before = current_committed_revision(proposal.capture.document_id, kind="plan")
    with pytest.raises(ApplicationStateConflictError, match="Resolve the existing"):
        execute(proposal, command(proposal, pending, "discard"))
    cancelled = execute(proposal, command(proposal, pending, "resolve_before",
        application_id=application.application_id, capture=pending.capture))
    assert cancelled.state == "editing"
    assert cancelled.markdown == pending.markdown
    assert cancelled.applications[-1].outcome == "not_applied"
    with pytest.raises(ApplicationStateConflictError, match="not pending"):
        execute(proposal, command(proposal, cancelled, "confirm", application_id=application.application_id))
    with pytest.raises(ApplicationStateConflictError, match="identity was already used"):
        prepare(proposal, cancelled, application_id=application.application_id)
    assert current_committed_revision(proposal.capture.document_id, kind="plan") == before
    next_attempt = prepare(proposal, cancelled)
    assert len(next_attempt.applications) == 2
    assert next_attempt.applications[0] == cancelled.applications[0]


def test_save_and_cancel_race_serialize_at_the_action_owner(completed_proposal):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    application = pending.applications[-1]
    before = current_committed_revision(proposal.capture.document_id, kind="plan")
    gate = Barrier(2)
    save = command(proposal, pending, "confirm", application_id=application.application_id)
    cancel = command(proposal, pending, "resolve_before",
        application_id=application.application_id, capture=pending.capture)

    def race(payload):
        gate.wait(timeout=10)
        try:
            return execute(proposal, payload)
        except ApplicationStateConflictError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        one, two = pool.submit(race, save), pool.submit(race, cancel)
        results = [one.result(timeout=15), two.result(timeout=15)]
    assert sum(isinstance(value, ApplicationStateConflictError) for value in results) == 1
    stored = owner.read_review(pending.world_id, pending.action_id).review
    actual = current_committed_revision(proposal.capture.document_id, kind="plan")
    if stored.state == "applied":
        assert actual.work_revision.markdown == application.after_markdown
        assert stored.applications[-1].outcome == "saved"
    else:
        assert stored.state == "editing"
        assert actual == before
        assert stored.applications[-1].outcome == "not_applied"


def test_newer_saved_plan_blocks_pending_application_without_losing_review(completed_proposal):
    from application_state.content.service import commit_plan

    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    newer, revision = commit_plan(proposal.capture.document_id, "# Newer author work\n",
        expected_revision=pending.capture.base_revision,
        expected_world_id=pending.world_id)
    with pytest.raises(ApplicationStateConflictError, match="saved Plan changed"):
        execute(proposal, command(proposal, pending, "confirm",
            application_id=pending.applications[-1].application_id))
    assert owner.read_review(pending.world_id, pending.action_id).review == pending
    assert get_plan(proposal.capture.document_id) == newer
    assert current_committed_revision(proposal.capture.document_id, kind="plan").work_revision == revision


@pytest.mark.parametrize("changes", [
    {"after_editor_sha256": "0" * 64},
    {"after_draft_sha256": "0" * 64},
    {"after_title": "  "},
    {"after_markdown": "Unnormalized\r\n"},
])
def test_invalid_sealed_copy_never_changes_review_or_content(completed_proposal, changes):
    from pydantic import ValidationError
    from application_state.errors import ApplicationStateValidationError

    proposal = completed_proposal
    review = opened(proposal)
    before = current_committed_revision(proposal.capture.document_id, kind="plan")
    with pytest.raises((ValidationError, ApplicationStateValidationError)):
        prepare(proposal, review, **changes)
    assert owner.read_review(review.world_id, review.action_id).review == review
    assert current_committed_revision(proposal.capture.document_id, kind="plan") == before


def test_http_review_requires_auth_before_world_and_app_reads(completed_proposal, monkeypatch):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as routes

    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    proposal = completed_proposal
    touched = []
    def deny(request):
        touched.append("auth")
        raise HTTPException(401, detail="Authentication required")
    def no_world_read(world):
        pytest.fail("World lookup occurred before authentication")
    monkeypatch.setattr(routes, "enforce_native_graph_gm", deny)
    monkeypatch.setattr(routes, "_verified_world_id", no_world_read)
    path = f"/api/live/agent/worlds/{proposal.capture.world_id}/plan-proposals/{proposal.origin.action_id}/review"
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        assert client.get(path).status_code == 401
        payload = command(proposal, None, "open")
        assert client.post(path, json=json.loads(json.dumps(payload, default=str))).status_code == 401
    assert touched == ["auth", "auth"]


@pytest.mark.parametrize("hosted_mode", [False, True], ids=["local", "hosted"])
def test_http_review_snapshot_and_commands_use_actual_plan_owner(completed_proposal, monkeypatch, hosted_mode, request):
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as routes

    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    proposal = completed_proposal
    monkeypatch.setattr(routes, "enforce_native_graph_gm", lambda request: None)
    monkeypatch.setattr(routes, "_verified_world_id", lambda world: world)
    path = f"/api/live/agent/worlds/{proposal.capture.world_id}/plan-proposals/{proposal.origin.action_id}/review"
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        get, post = client.get, client.post
        if hosted_mode:
            from tests.test_hosted_native_graph_access import HOSTED_WORLD_ACCESS_ENV, OWNER, _record

            hosted = request.getfixturevalue("hosted")
            world = proposal.capture.world_id
            hosted.records[world] = _record(world, OWNER, "native-plan-fixture")
            # The older Plan fixture uses a colon-delimited World ID. Substitute
            # its catalog record at the registry seam while keeping owner checks.
            monkeypatch.setattr(
                "apps.live_control_server.services.hosted_native_graph_access.get_world_container",
                hosted.records.__getitem__,
            )
            monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({world: [OWNER]}))
            get = lambda path, **kwargs: hosted.client.request("GET", path, **kwargs)
            post = lambda path, **kwargs: hosted.client.request("POST", path, **kwargs)
            assert get(path, session="other-session").status_code == 403
        snapshot = get(path)
        assert snapshot.status_code == 200, snapshot.text
        assert snapshot.json() == {
            "schema": "dmb_plan_authoring_review_snapshot_v1",
            "world_id": proposal.capture.world_id,
            "action_id": str(proposal.origin.action_id),
            "origin_sha256": proposal.origin.sha256,
            "review": None,
        }
        payload = command(proposal, None, "open")
        opened_response = post(path, json=json.loads(json.dumps(payload, default=str)))
        assert opened_response.status_code == 200, opened_response.text
        body = opened_response.json()
        assert body["state"] == "editing" and body["revision"] == 1
        assert get(path).json()["review"] == body
        if hosted_mode:
            edit = {
                "operation": "save", "command_id": str(uuid4()), "origin_sha256": proposal.origin.sha256,
                "expected_revision": 1, "markdown": "## Revised approach\n\nAsk about the pond first.",
            }
            assert post(path, json=edit, origin=None).status_code == 403
            from application_state.plan_action_dialogue import authoring_review
            from tests.test_hosted_native_graph_access import OTHER_OWNER

            owner_record = hosted.records[world]
            read_owner = authoring_review._owner

            def transfer_after_lookup(*args, **kwargs):
                result = read_owner(*args, **kwargs)
                hosted.records[world] = owner_record.model_copy(update={"owner_subject": OTHER_OWNER})
                return result

            with monkeypatch.context() as patch:
                patch.setattr(authoring_review, "_owner", transfer_after_lookup)
                denied = get(path)
                assert denied.status_code == 403, denied.text
            hosted.records[world] = owner_record
            with monkeypatch.context() as patch:
                patch.setattr(authoring_review, "_owner", transfer_after_lookup)
                denied = post(path, json=edit)
                assert denied.status_code == 403, denied.text
            hosted.records[world] = owner_record
            assert get(path).json()["review"] == body
            saved = post(path, json=edit)
            assert saved.status_code == 200, saved.text
            assert saved.json()["revision"] == 2
            assert post(path, json=edit).json() == saved.json()
            assert get(path).json()["review"] == saved.json()

        stale = command(proposal, None, "discard")
        assert post(path, json=json.loads(json.dumps(stale, default=str))).status_code == 409
        foreign = path.replace(proposal.capture.world_id, "foreign-world")
        assert get(foreign).status_code == (403 if hosted_mode else 404)
        assert owner.read_review(proposal.capture.world_id, proposal.origin.action_id).review.revision == (2 if hosted_mode else 1)


def inspected_capture(proposal, *, obj=None, revision=None, pointer=None):
    from application_state.agent_conversation.plan_authoring import PlanAuthoringCaptureV1

    body = "A newer unsaved author copy. Inspect before placing again."
    editor = json.dumps({"type": "doc", "content": [{"type": "paragraph", "content": [
        {"type": "text", "text": body}]}]})
    payload = proposal.capture.model_dump(mode="json", by_alias=True)
    payload.update(draft_markdown=body, draft_sha256=text_digest(body),
        editor_json=editor, editor_sha256=text_digest(editor),
        draft_generation=proposal.capture.draft_generation + 1)
    if obj is not None:
        payload.update(base_revision=obj.object_revision,
            base_content_sha256=revision.content_sha256)
    if pointer is not None:
        payload.update(conversation_id=str(pointer.active_conversation_id),
            expected_pointer_revision=pointer.revision)
    return PlanAuthoringCaptureV1.model_validate(payload)


def test_explicit_current_placement_recovery_preserves_newer_page_and_original_copies(
    completed_proposal,
):
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import ConversationCommand
    from application_state.content.service import commit_plan

    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    application = pending.applications[-1]
    obj, revision = commit_plan(proposal.capture.document_id, "# A newer saved author page\n",
        expected_revision=pending.capture.base_revision, expected_world_id=pending.world_id)
    agent = AgentConversationService()
    pointer = agent.get_world_pointer(pending.world_id)
    agent.new_conversation(ConversationCommand(world_id=pending.world_id,
        command_id=uuid4(), expected_pointer_revision=pointer.revision,
        expected_active_conversation_id=pointer.active_conversation_id))
    fresh = inspected_capture(proposal, obj=obj, revision=revision,
        pointer=agent.get_world_pointer(pending.world_id))
    recovery = command(proposal, pending, "recover_placement",
        application_id=application.application_id, capture=fresh)
    recovered = execute(proposal, recovery)
    assert execute(proposal, recovery) == recovered
    assert recovered.state == "editing" and recovered.capture == fresh
    assert recovered.markdown == pending.markdown
    retired = recovered.applications[-1]
    assert retired.outcome == "superseded"
    assert retired.saved_work_revision_id is None
    assert retired.capture == application.capture
    assert retired.after_editor_json == application.after_editor_json
    assert retired.after_markdown == application.after_markdown
    assert retired.markdown == application.markdown
    assert get_plan(proposal.capture.document_id) == obj
    assert current_committed_revision(proposal.capture.document_id, kind="plan").work_revision == revision
    with pytest.raises(ApplicationStateConflictError, match="not pending"):
        execute(proposal, command(proposal, recovered, "confirm", application_id=application.application_id))
    next_application = prepare(proposal, recovered)
    assert next_application.applications[0] == retired
    assert next_application.applications[-1].application_id != application.application_id
    # Prepare does not save or insert the new proposal.
    assert get_plan(proposal.capture.document_id) == obj


def test_current_placement_recovery_rejects_stale_or_foreign_capture(completed_proposal):
    from application_state.content.service import commit_plan

    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    application_id = pending.applications[-1].application_id
    stale = inspected_capture(proposal)
    obj, _revision = commit_plan(proposal.capture.document_id, "# Another saved version\n",
        expected_revision=pending.capture.base_revision, expected_world_id=pending.world_id)
    with pytest.raises(ApplicationStateConflictError, match="saved Plan changed"):
        execute(proposal, command(proposal, pending, "recover_placement",
            application_id=application_id, capture=stale))
    foreign = stale.model_copy(update={"document_id": str(uuid4())})
    with pytest.raises(ApplicationStateConflictError, match="another page"):
        execute(proposal, command(proposal, pending, "recover_placement",
            application_id=application_id, capture=foreign))
    assert owner.read_review(pending.world_id, pending.action_id).review == pending
    assert get_plan(proposal.capture.document_id) == obj


def test_current_placement_recovery_and_confirm_race_have_only_one_winner(completed_proposal):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    proposal = completed_proposal
    pending = prepare(proposal, opened(proposal))
    application = pending.applications[-1]
    fresh = inspected_capture(proposal)
    before = current_committed_revision(proposal.capture.document_id, kind="plan")
    gate = Barrier(2)
    save = command(proposal, pending, "confirm", application_id=application.application_id)
    recover = command(proposal, pending, "recover_placement",
        application_id=application.application_id, capture=fresh)
    def race(payload):
        gate.wait(timeout=10)
        try:
            return execute(proposal, payload)
        except ApplicationStateConflictError as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        one, two = pool.submit(race, save), pool.submit(race, recover)
        results = [one.result(timeout=15), two.result(timeout=15)]
    assert sum(isinstance(value, ApplicationStateConflictError) for value in results) == 1
    stored = owner.read_review(pending.world_id, pending.action_id).review
    if stored.state == "applied":
        assert stored.applications[-1].outcome == "saved"
        assert current_committed_revision(proposal.capture.document_id, kind="plan").work_revision.markdown == application.after_markdown
    else:
        assert stored.state == "editing" and stored.capture == fresh
        assert stored.applications[-1].outcome == "superseded"
        assert current_committed_revision(proposal.capture.document_id, kind="plan") == before


@pytest.mark.parametrize("completed_proposal", ["end"], indirect=True)
def test_structural_capture_survives_review_edit_save_and_exact_confirmation_replay(completed_proposal):
    proposal=completed_proposal
    assert proposal.capture.target_kind=="insert_at_boundary"
    assert proposal.capture.root_boundary==1
    generated=proposal.model_dump(mode="json",by_alias=True)
    review=opened(proposal)
    assert review.capture==proposal.capture
    review=execute(proposal,command(proposal,review,"save",markdown="Author-edited conditional briefing.\n"))
    pending=prepare(proposal,review)
    application=pending.applications[-1]
    assert application.capture==proposal.capture
    confirm=command(proposal,pending,"confirm",application_id=application.application_id)
    saved=execute(proposal,confirm)
    assert saved.state=="applied"
    assert saved.capture==proposal.capture
    assert execute(proposal,confirm)==saved
    assert owner.read_review(saved.world_id,saved.action_id).review==saved
    committed=current_committed_revision(proposal.capture.document_id,kind="plan")
    assert committed.work_revision.content_sha256==application.after_draft_sha256
    assert committed.work_revision.markdown==application.after_markdown
    assert proposal.model_dump(mode="json",by_alias=True)==generated


def composed_plan(left, right, ending):
    blocks = [*left, *right, ending]
    markdown = "\n\n".join(text for _, text in blocks) + "\n"
    raw = markdown.encode("utf-8")
    bindings = {
        identity: dict(kind="block", id=identity, byte_start=start, byte_end=end,
            sha256=text_digest(raw[start:end].decode("utf-8")))
        for (identity, _), (start, end) in zip(blocks, source_block_spans(markdown), strict=True)
    }
    layout = PagePresentation.model_validate({
        "markdown_sha256": text_digest(markdown),
        "items": [
            {"kind": "row", "id": "row", "min_height": 160, "line_mode": "border", "slots": [
                {"id": "left", "width": 7, "blocks": [bindings[identity] for identity, _ in left]},
                {"id": "right", "width": 5, "blocks": [bindings[identity] for identity, _ in right]},
            ]},
            bindings[ending[0]],
        ],
    }).checked(markdown)

    def paragraph(pair):
        identity, text = pair
        if text.startswith("## "):
            return {"type": "heading", "attrs": {"pageBlockId": identity, "level": 2},
                "content": [{"type": "text", "text": text[3:]}]}
        return {"type": "paragraph", "attrs": {"pageBlockId": identity},
            "content": [{"type": "text", "text": text}]}

    editor = {"type": "doc", "content": [
        {"type": "pageRow", "attrs": {"id": "row", "min_height": 160, "line_mode": "border"}, "content": [
            {"type": "pageSlot", "attrs": {"id": "left", "width": 7}, "content": list(map(paragraph, left))},
            {"type": "pageSlot", "attrs": {"id": "right", "width": 5}, "content": list(map(paragraph, right))},
        ]},
        paragraph(ending),
    ]}
    return markdown, layout, json.dumps(editor, separators=(",", ":"))


LEFT = ("left-block", "The gate is locked.")
RIGHT = ("right-block", "The gate is locked.")
ENDING = ("ending", "## Retain the unrelated closing heading")
INSERTION = ("new-warning", "Keep a lantern ready.")


@pytest.fixture
def composed_proposal(completed_proposal, application_state_dsn, request):
    """Seed the successor's terminal payload. Runtime Send is intentionally inactive."""
    from psycopg.types.json import Jsonb

    proposal = completed_proposal
    old = proposal.capture
    markdown, layout, editor = composed_plan([LEFT], [RIGHT], ENDING)
    obj, revision = commit_plan(old.document_id, markdown,
        expected_revision=old.base_revision, expected_world_id=old.world_id, page_presentation=layout)
    basis = proposal.origin.basis.model_copy(update={
        "object_revision": obj.object_revision,
        "work_revision_id": revision.work_revision_id,
        "revision_n": revision.revision_n,
        "content_sha256": revision.content_sha256,
    })
    capture = PlanAuthoringSlotBoundaryCaptureV1.model_validate(old.model_dump(mode="python", by_alias=True) | {
        "schema": "dmb_plan_authoring_slot_boundary_capture_v1",
        "target_kind": "insert_at_slot_boundary",
        "base_revision": obj.object_revision,
        "base_content_sha256": revision.content_sha256,
        "draft_markdown": markdown, "draft_sha256": text_digest(markdown),
        "editor_json": editor, "editor_sha256": text_digest(editor),
        "slot_address": {"row_index": 0, "row_id": "row", "slot_index": 1, "slot_id": "right",
            "child_index": 0, "block_id": "right-block", "relation": getattr(request, "param", "after")},
        "base_page_presentation_sha256": layout.fingerprint(),
        "draft_page_presentation": layout, "draft_page_presentation_sha256": layout.fingerprint(),
    })
    with unit_of_work(application_state_dsn) as conn:
        old_action = actions._get_by_id(conn, proposal.origin.action_id, lock=True)
        stored = PlanActionAuthoringResultV1.model_validate(old_action.authoring_origin.model_dump(mode="python", by_alias=True) | {
            "basis": basis, "capture": capture, "capture_sha256": capture.sha256,
        })
        conn.execute("""
            UPDATE plan_action.action
            SET object_revision=%s, work_revision_id=%s, revision_n=%s, content_sha256=%s,
                draft_sha256=%s, target_kind='insert_at_slot_boundary', authoring_origin=%s
            WHERE action_id=%s
        """, (basis.object_revision, basis.work_revision_id, basis.revision_n, basis.content_sha256,
            capture.draft_sha256, Jsonb(stored.model_dump(mode="json", by_alias=True)), proposal.origin.action_id))
    return stored.proposal


def edit_slot_review(proposal):
    return execute(proposal, command(proposal, opened(proposal), "save", markdown=INSERTION[1]))


def slot_prepare_command(proposal, review, *, left=None, right=None, ending=ENDING, **overrides):
    default_right = [RIGHT, INSERTION] if proposal.capture.slot_address.relation == "after" else [INSERTION, RIGHT]
    markdown, layout, editor = composed_plan(
        [LEFT] if left is None else left, default_right if right is None else right, ending,
    )
    return command(proposal, review, "prepare_slot", **({
        "application_id": uuid4(), "after_editor_json": editor, "after_editor_sha256": text_digest(editor),
        "after_markdown": markdown, "after_draft_sha256": text_digest(markdown), "after_title": "Reviewed slot",
        "after_page_presentation": layout, "after_page_presentation_sha256": layout.fingerprint(),
    } | overrides))


@pytest.mark.parametrize("composed_proposal", ["before", "after"], indirect=True)
def test_composed_slot_review_http_commits_only_the_addressed_slot(composed_proposal, monkeypatch):
    from fastapi.testclient import TestClient
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import agent as routes

    proposal = composed_proposal
    review = edit_slot_review(proposal)
    payload = slot_prepare_command(proposal, review)
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setattr(routes, "enforce_native_graph_gm", lambda request: None)
    monkeypatch.setattr(routes, "_verified_world_id", lambda world: world)
    path = f"/api/live/agent/worlds/{proposal.capture.world_id}/plan-proposals/{proposal.origin.action_id}/review"
    with TestClient(create_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)) as client:
        prepare_body = owner.command_adapter.validate_python(payload).model_dump(mode="json", by_alias=True)
        prepared = client.post(path, json=prepare_body)
        assert prepared.status_code == 200, prepared.text
        assert client.post(path, json=prepare_body).json() == prepared.json()
        assert client.post(path, json=prepare_body | {"after_title": "Different retry"}).status_code == 409
        pending = owner.PlanAuthoringReviewV1.model_validate(prepared.json())
        assert client.get(path).json()["review"]["applications"] == prepared.json()["applications"]
        app = pending.applications[-1]
        assert isinstance(app, owner.PlanSlotReviewApplicationV1)
        assert app.after_page_presentation == payload["after_page_presentation"]
        confirm = command(proposal, pending, "confirm", application_id=app.application_id)
        body = owner.command_adapter.validate_python(confirm).model_dump(mode="json", by_alias=True)
        saved = client.post(path, json=body)
        assert saved.status_code == 200, saved.text
        assert client.post(path, json=body).json() == saved.json()
        assert client.get(path).json()["review"] == saved.json()
    snapshot = snapshot_content(proposal.capture.document_id)
    assert snapshot.markdown == payload["after_markdown"]
    assert snapshot.page_presentation == payload["after_page_presentation"]
    assert str(snapshot.work_object.current_revision_id) == saved.json()["applications"][-1]["saved_work_revision_id"]
    with pytest.raises(ApplicationStateNotFoundError):
        owner.read_review("unrelated-world", proposal.origin.action_id)
    row, ending = snapshot.page_presentation.items
    newer_layout = snapshot.page_presentation.model_copy(update={"items": [
        row.model_copy(update={"min_height": 168}), ending,
    ]})
    commit_plan(proposal.capture.document_id, snapshot.markdown,
        expected_revision=snapshot.loaded_revision, expected_world_id=proposal.capture.world_id,
        page_presentation=newer_layout)
    assert execute(proposal, confirm).model_dump(mode="json", by_alias=True) == saved.json()
    assert snapshot_content(proposal.capture.document_id).page_presentation == newer_layout


def test_composed_slot_rejects_other_slot_source_and_unbound_layout(composed_proposal):
    proposal = composed_proposal
    review = edit_slot_review(proposal)
    before = snapshot_content(proposal.capture.document_id)
    original = proposal.capture.model_dump(mode="python", by_alias=True)
    counterfeit = json.loads(original["editor_json"])
    counterfeit["content"][0]["content"][0]["content"][0]["content"][0]["text"] = "False neighboring text."
    counterfeit_source = json.dumps(counterfeit)
    with pytest.raises(ValueError, match="exact Markdown"):
        PlanAuthoringSlotBoundaryCaptureV1.model_validate(original | {
            "editor_json": counterfeit_source, "editor_sha256": text_digest(counterfeit_source),
        })
    with pytest.raises(ValueError, match="selection witness"):
        PlanAuthoringSlotBoundaryCaptureV1.model_validate(original | {"from": 99, "to": 99})
    invalid = [
        slot_prepare_command(proposal, review, left=[LEFT, INSERTION], right=[RIGHT]),
        slot_prepare_command(proposal, review, ending=(ENDING[0], "Changed unrelated source.")),
        slot_prepare_command(proposal, review, after_page_presentation_sha256="1" * 64),
    ]
    forged = slot_prepare_command(proposal, review)
    editor = json.loads(forged["after_editor_json"])
    editor["content"][0]["content"][1]["content"][1]["content"][0]["text"] = "Unreviewed local wording."
    forged_editor = json.dumps(editor)
    invalid.append(forged | {"after_editor_json": forged_editor, "after_editor_sha256": text_digest(forged_editor)})
    for payload in invalid:
        with pytest.raises(ValueError):
            execute(proposal, payload)
    old_payload = slot_prepare_command(proposal, review)
    old_payload.update(operation="prepare")
    del old_payload["after_page_presentation"], old_payload["after_page_presentation_sha256"]
    with pytest.raises(ApplicationStateValidationError, match="captured layout type"):
        execute(proposal, old_payload)
    assert snapshot_content(proposal.capture.document_id) == before
    assert owner.read_review(review.world_id, review.action_id).review == review


def test_composed_slot_rejects_stale_layout_and_rolls_back_receipt_failure(composed_proposal, monkeypatch):
    proposal = composed_proposal
    capture = proposal.capture
    review = edit_slot_review(proposal)
    stale_capture = capture.model_copy(update={"base_page_presentation_sha256": "1" * 64})
    with pytest.raises(ApplicationStateConflictError, match="saved Plan layout changed"):
        execute(proposal, command(proposal, review, "move", capture=stale_capture))
    pending = execute(proposal, slot_prepare_command(proposal, review))
    confirm = command(proposal, pending, "confirm", application_id=pending.applications[-1].application_id)
    before = snapshot_content(capture.document_id)
    with monkeypatch.context() as failure:
        def reject_slot_receipt(conn, action, next_review, **kwargs):
            assert next_review.state == "applied"
            raise RuntimeError("receipt failed after composed Content update")

        failure.setattr(owner, "_persist_review", reject_slot_receipt)
        with pytest.raises(RuntimeError, match="receipt failed"):
            execute(proposal, confirm)
    assert snapshot_content(capture.document_id) == before
    assert owner.read_review(review.world_id, review.action_id).review == pending
    row, ending = before.page_presentation.items
    changed_row = row.model_copy(update={"min_height": 168})
    concurrent = before.page_presentation.model_copy(update={"items": [changed_row, ending]})
    commit_plan(capture.document_id, before.markdown, expected_revision=capture.base_revision,
        expected_world_id=capture.world_id, page_presentation=concurrent)
    with pytest.raises(ApplicationStateConflictError, match="saved Plan changed"):
        execute(proposal, confirm)
    latest = snapshot_content(capture.document_id)
    assert latest.markdown == before.markdown
    assert latest.page_presentation == concurrent
    assert owner.read_review(review.world_id, review.action_id).review == pending
