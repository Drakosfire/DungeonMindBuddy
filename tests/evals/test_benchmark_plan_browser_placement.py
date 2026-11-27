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



@pytest.mark.parametrize("status", ["active", "discarded", "divergent"])
def test_plan_fixture_requires_active_committed_revision(status):
    from evals.buddy_benchmark.browser_capture import require_plan_fixture_basis

    work = {"object_id": "plan-fixture", "expected_revision": 3, "expected_revision_n": 2,
            "expected_content_sha256": "a" * 64}
    committed = {
        "schema_version": "dmb_workspace_committed_revision_v2", "scope_mode": "world",
        "campaign_id": None, "world_id": "elderwyld", "document_id": "plan-fixture",
        "kind": "plan", "status": "active" if status == "divergent" else status,
        "has_divergent_working_copy": status == "divergent", "object_revision": 3, "revision_n": 2,
        "content_sha256": "a" * 64, "markdown": "A unique placement paragraph.",
    }
    if status == "active":
        require_plan_fixture_basis(committed, "elderwyld", work, committed["markdown"])
    elif status == "divergent":
        with pytest.raises(ValueError, match="clean committed Plan"):
            require_plan_fixture_basis(committed, "elderwyld", work, None, require_clean=True)
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


def test_saved_image_library_uses_owner_cursor_and_excludes_staged():
    import httpx
    from evals.buddy_benchmark.browser_capture import saved_image_library

    staged = {"state": "staged", "created_at": "2026-11-26T12:00:00Z", "asset_id": "staged"}
    ready = {"state": "ready", "created_at": "2026-11-26T11:00:00Z", "asset_id": "saved"}
    pages = iter(([staged], [ready], []))
    cursors = []

    def handle(request):
        cursors.append(dict(request.url.params))
        return httpx.Response(200, json={"items": next(pages)})

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
        assert saved_image_library(client, "elderwyld") == [ready]
    assert cursors == [
        {"world_id": "elderwyld"},
        {"world_id": "elderwyld", "before_time": staged["created_at"], "before_id": staged["asset_id"]},
        {"world_id": "elderwyld", "before_time": ready["created_at"], "before_id": ready["asset_id"]},
    ]


def test_image_preview_report_distinguishes_missing_and_incomplete_capture(tmp_path):
    import json
    from evals.buddy_benchmark.workflow import report_case

    case = {"id": "IMAGE-GENERATION-1", "capture_dir": ".", "capture_boundary": "image_preview"}
    assert report_case(case, tmp_path)["delivery"]["status"] == "unknown"
    result = tmp_path / "fixture-result.json"
    result.write_text(json.dumps({"status": "incomplete", "checks": {"single_generation": False}}))
    assert report_case(case, tmp_path)["delivery"]["status"] == "fail"
    result.write_text(json.dumps({"status": "observed", "checks": {"single_generation": True}}))
    assert report_case(case, tmp_path)["delivery"]["status"] == "pass"


def test_image_parent_readback_requires_original_byte_digest():
    from hashlib import sha256
    import httpx
    from evals.buddy_benchmark.browser_capture import read_image_parent

    asset_id = "05e64f01-adc1-4ebb-859f-3cfabcc54839"
    original = b"pinned image bytes"
    metadata = {"asset_id": asset_id, "state": "ready", "content_sha256": sha256(original).hexdigest()}

    def handle(request):
        assert request.url.path.startswith(f"/api/live/media/images/{asset_id}/")
        if request.url.path.endswith("/metadata"):
            return httpx.Response(200, json=metadata)
        assert request.url.path.endswith("/original")
        return httpx.Response(200, content=original)

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
        matching = read_image_parent(client, metadata)
        assert matching["matches_pin"] and matching["metadata"]["body"] == metadata
        changed = read_image_parent(client, {**metadata, "content_sha256": "0" * 64})
        assert changed["matches_pin"] is False
        assert changed["original_sha256"] == sha256(original).hexdigest()
    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(
            lambda request: httpx.Response(404, json={"detail": "Image missing"}))) as client:
        missing = read_image_parent(client, metadata)
        assert not missing["matches_pin"]
        assert missing["original_http_status"] == missing["metadata"]["http_status"] == 404
