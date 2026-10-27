"""Actual completed Agent proposal, Plan review and Content transaction ownership."""
from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation.plan_authoring import text_digest
from application_state.content import repository as content
from application_state.content.service import current_committed_revision, get_plan
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from application_state.plan_action_dialogue import authoring_review as owner
from application_state.unit_of_work import unit_of_work
from tests.test_plan_jev_authoring import authoring_writer
from tests.test_plan_jev_writer import WriterWire, graph_answer

pytest_plugins = ("tests.test_plan_jev_dispatch",)


@pytest.fixture
def completed_proposal(plan_adapter):
    writer, action, capture = authoring_writer(plan_adapter)
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
    assert owner.read_review(saved.world_id, saved.action_id) == saved
    assert saved.markdown != proposal.replacement_markdown
    with pytest.raises(ApplicationStateConflictError, match="identity was reused"):
        execute(proposal, edit | {"markdown": "Changed under same identity"})
    with pytest.raises(ApplicationStateConflictError, match="review changed"):
        execute(proposal, command(proposal, initial, "discard"))
    with pytest.raises(ApplicationStateNotFoundError):
        owner.execute_review_command("foreign-world", saved.action_id, edit)
    with pytest.raises(ApplicationStateConflictError, match="generated Plan proposal changed"):
        execute(proposal, command(proposal, saved, "discard") | {"origin_sha256": "0" * 64})
    assert owner.read_review(saved.world_id, saved.action_id) == saved


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
    reloaded = owner.read_review(saved.world_id, saved.action_id)
    actual = current_committed_revision(proposal.capture.document_id, kind="plan")
    assert reloaded == saved
    assert actual.work_revision.markdown == application.after_markdown
    assert actual.work_revision.work_revision_id == saved.applications[-1].saved_work_revision_id
    assert get_plan(proposal.capture.document_id).title == application.after_title
    with unit_of_work(application_state_dsn) as conn:
        assert content.next_revision_n(conn, actual.work_object.work_object_id) == actual.work_revision.revision_n + 1
    assert reloaded.applications[-1].after_editor_json == application.after_editor_json


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
    assert owner.read_review(pending.world_id, pending.action_id) == pending
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
    stored = owner.read_review(pending.world_id, pending.action_id)
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
    assert owner.read_review(pending.world_id, pending.action_id) == pending
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
    assert owner.read_review(review.world_id, review.action_id) == review
    assert current_committed_revision(proposal.capture.document_id, kind="plan") == before
