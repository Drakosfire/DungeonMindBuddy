from uuid import uuid4

import pytest

from application_state.agent_conversation.plan_authoring import PlanAuthoringCaptureV1, text_digest
from evals.buddy_benchmark.browser_capture import validate_plan_browser_placement


@pytest.mark.parametrize("mismatch", [None, "missing_catalog", "wrong_revision", "wrong_pointer", "wrong_selection", "wrong_caret", "document_start"])
def test_plan_browser_placement_binding(mismatch):
    world, document, conversation = "elderwyld", str(uuid4()), str(uuid4())
    markdown = "A live draft."
    editor = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"A live draft."}]}]}'
    caret = 1 if mismatch == "document_start" else 14
    selection = '{"type":"text","anchor":%d,"head":%d}' % (caret, caret)
    capture = PlanAuthoringCaptureV1.model_validate({
        "idempotency_key": str(uuid4()), "conversation_id": conversation,
        "expected_pointer_revision": 1, "world_id": world, "document_id": document,
        "base_revision": 3, "base_content_sha256": text_digest(markdown),
        "draft_markdown": markdown, "draft_sha256": text_digest(markdown),
        "editor_json": editor, "editor_sha256": text_digest(editor),
        "selection_json": selection, "selection_sha256": text_digest(selection),
        "from": caret, "to": caret, "draft_generation": 0, "selection_generation": 1,
        "target_kind": "insert_at_caret", "selected_text": "",
    })
    work = {"kind": "plan", "object_id": document, "expected_revision": 3, "expected_revision_n": 3,
            "expected_content_sha256": capture.base_content_sha256}
    question = "Stage a scene card here from the supplied passage."
    request = {
        "schema": "dmb_agent_turn_request_v1", "client_thread_id": str(uuid4()), "turn_id": str(uuid4()),
        "surface": {"surface_id": "plan", "instance_id": document},
        "owner_scope": {"kind": "world", "world_id": world}, "primary_work": work,
        "client_work_state": "saved_clean", "graph_request": {"mode": "none"}, "graph_selection": None, "message": question,
        "plan_context_policy": {"schema": "dmb_plan_context_policy_v2", "policy": "auto_plan_world",
                                "graph_source": "reviewed_native_graph"},
        "plan_authoring_capture": capture.model_dump(by_alias=True, mode="json"),
        "plan_placement_catalog": {
            "schema": "dmb_plan_placement_catalog_v1", "original_capture_sha256": capture.sha256,
            "editor_sha256": capture.editor_sha256, "entries": [{
                "selector": "captured", "kind": "captured_target", "label": "Selected caret",
                "root_boundary": None, "position": None, "target_capture_sha256": capture.sha256,
            }],
        },
    }
    if mismatch == "missing_catalog":
        request.pop("plan_placement_catalog")
    if mismatch == "wrong_revision":
        work = {**work, "expected_revision": 4}
    controls = dict(world=world, work=work, question=question, conversation_id=conversation,
                    pointer_revision=2 if mismatch == "wrong_pointer" else 1,
                    selection_text="A different passage." if mismatch == "wrong_selection" else None)
    controls["at_document_start"] = mismatch in {"wrong_caret", "document_start"}
    if mismatch and mismatch != "document_start":
        with pytest.raises(ValueError):
            validate_plan_browser_placement(request, **controls)
    else:
        parsed = validate_plan_browser_placement(request, **controls)
        assert parsed.plan_authoring_capture == capture



def test_live_plan_cli_requires_selected_case_and_clone():
    from evals.buddy_benchmark import workflow

    args = ["capture", "--manifest", "manifest.json", "--output", "capture", "--live-plan"]
    with pytest.raises(SystemExit):
        workflow.main(args + ["--case", "PLAN-CARDS-1"])
    with pytest.raises(SystemExit):
        workflow.main(args + ["--clone-app"])



@pytest.mark.parametrize("option", ["context_only", "writer_transport", "detailed_trace"])
def test_live_plan_rejects_replay_options_before_loading_manifest(option, tmp_path):
    from evals.buddy_benchmark import workflow

    with pytest.raises(ValueError, match="response mode"):
        workflow.capture(tmp_path / "missing.json", tmp_path / "output", live_plan=True,
                         browser_case="PLAN-CARDS-1", clone_app=True, **{option: True})



@pytest.mark.parametrize("status", ["active", "discarded"])
def test_plan_fixture_requires_active_committed_revision(status):
    from evals.buddy_benchmark.browser_capture import require_plan_fixture_basis

    work = {"object_id": "plan-fixture", "expected_revision": 3, "expected_revision_n": 2,
            "expected_content_sha256": "a" * 64}
    committed = {
        "schema_version": "dmb_workspace_committed_revision_v2", "scope_mode": "world",
        "campaign_id": None, "world_id": "elderwyld", "document_id": "plan-fixture",
        "kind": "plan", "status": status, "object_revision": 3, "revision_n": 2,
        "content_sha256": "a" * 64, "markdown": "A unique placement paragraph.",
    }
    if status == "active":
        require_plan_fixture_basis(committed, "elderwyld", work, committed["markdown"])
    else:
        with pytest.raises(ValueError, match="pinned active committed Plan"):
            require_plan_fixture_basis(committed, "elderwyld", work, committed["markdown"])



@pytest.mark.parametrize("mismatch", [None, "conversation", "message", "extra", "status", "paginated"])
def test_pinned_plan_history_requires_exact_completed_prefix(mismatch):
    from evals.buddy_benchmark.browser_capture import require_plan_history

    turn = {"turn_id": "turn-1", "sequence": 1, "lifecycle_status": "completed",
            "user_text": "Earlier question", "assistant_text": "Earlier answer"}
    history = {"active_conversation_id": "conversation-1", "turns": [turn]}
    pin = {"conversation_id": "conversation-1", "prior_turns": [{
        "turn_id": turn["turn_id"], "sequence": 1,
        "user_text_sha256": text_digest(turn["user_text"]),
        "assistant_text_sha256": text_digest(turn["assistant_text"]),
    }]}
    second = {**turn, "turn_id": "turn-2", "sequence": 2}
    history["turns"].insert(0, second)
    pin["prior_turns"].append({**pin["prior_turns"][0], "turn_id": "turn-2", "sequence": 2})
    if mismatch == "paginated":
        history["next_before_sequence"] = 1
    if mismatch == "conversation":
        history["active_conversation_id"] = "other-conversation"
    if mismatch == "message":
        turn["assistant_text"] = "Revised answer"
    if mismatch == "extra":
        history["turns"].append({**turn, "sequence": 2})
    if mismatch == "status":
        turn["lifecycle_status"] = "interrupted"
    if mismatch is None:
        require_plan_history(history, pin)
    else:
        with pytest.raises(ValueError, match="pinned Plan history"):
            require_plan_history(history, pin)
