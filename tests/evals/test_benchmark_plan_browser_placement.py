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



@pytest.mark.parametrize("mismatch", [None, "conversation", "message", "extra", "status", "paginated", "missing_reply"])
def test_pinned_plan_history_requires_exact_completed_prefix(mismatch):
    from evals.buddy_benchmark.workflow import require_pinned_history

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
    if mismatch == "missing_reply":
        turn["assistant_text"] = None
        pin["prior_turns"][0]["assistant_text_sha256"] = None
    if mismatch is None:
        require_pinned_history(history, pin)
    else:
        with pytest.raises(ValueError, match="pinned conversation history"):
            require_pinned_history(history, pin)


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


def test_build_capture_retains_stale_history_without_posting(tmp_path, monkeypatch):
    import httpx
    from evals.buddy_benchmark import workflow

    monkeypatch.setattr(workflow, "validate_template", lambda *args, **kwargs: None)
    requests = []
    history = {"active_conversation_id": "different", "turns": []}

    def handle(request):
        requests.append(request.method)
        return httpx.Response(200, json=history)

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError, match="pinned conversation history"):
            workflow.capture_case(
                client, "elderwyld", {}, {"id": "case"}, tmp_path / "case",
                build_thread_id="isolated-thread",
                pinned_history={"conversation_id": "expected", "prior_turns": []},
            )

    assert requests == ["GET"]
    assert (tmp_path / "case" / "history-before.json").is_file()
    assert not (tmp_path / "case" / "dispatch.json").exists()


def test_first_resumed_build_turn_retains_explicit_authored_references(tmp_path, monkeypatch):
    import json
    import httpx
    from evals.buddy_benchmark import workflow

    monkeypatch.setattr(workflow, "validate_template", lambda *args, **kwargs: None)
    turn = {"turn_id": "turn-1", "sequence": 1, "lifecycle_status": "completed",
            "user_text": "Earlier question", "assistant_text": "Earlier answer"}
    history = {"active_conversation_id": "conversation-1", "turns": [turn]}
    pin = {"conversation_id": "conversation-1", "prior_turns": [{
        "turn_id": turn["turn_id"], "sequence": 1,
        "user_text_sha256": text_digest(turn["user_text"]),
        "assistant_text_sha256": text_digest(turn["assistant_text"]),
    }]}
    references = {"fixture": "explicit first-turn reference"}
    observed = []

    def handle(request):
        if request.method == "POST":
            observed.append((request.url.path, json.loads(request.content)))
            return httpx.Response(503, json={"code": "synthetic_stop"})
        return httpx.Response(200, json=history)

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError):
            workflow.capture_case(
                client, "elderwyld", {"build_authored_references": references, "surface": {"surface_id": "build"}},
                {"id": "case", "question": "Continue"}, tmp_path / "case",
                build_thread_id="isolated-thread", pinned_history=pin,
            )

    assert len(observed) == 1
    assert observed[0][0] == "/api/live/agent/turn"
    assert observed[0][1]["build_authored_references"] == references


def test_pinned_build_history_can_preserve_exact_interrupted_turn():
    from evals.buddy_benchmark.workflow import require_pinned_history

    turn = {"turn_id": "turn-1", "sequence": 1, "lifecycle_status": "interrupted",
            "user_text": "Earlier question", "assistant_text": None}
    history = {"active_conversation_id": "conversation-1", "turns": [turn]}
    expected = {"conversation_id": "conversation-1", "prior_turns": [{
        "turn_id": turn["turn_id"], "sequence": 1, "lifecycle_status": "interrupted",
        "user_text_sha256": text_digest(turn["user_text"]), "assistant_text_sha256": None,
    }]}
    require_pinned_history(history, expected, allow_interrupted=True)
    with pytest.raises(ValueError, match="pinned conversation history"):
        require_pinned_history(history, expected)
    turn["lifecycle_status"] = "running"
    with pytest.raises(ValueError, match="pinned conversation history"):
        require_pinned_history(history, expected, allow_interrupted=True)


@pytest.mark.parametrize("failure", [None, "unsafe_rejection", "wrong_revision"])
def test_lore_confirmation_reads_back_one_saved_revision(tmp_path, monkeypatch, failure):
    import json
    from types import SimpleNamespace

    import httpx

    from application_state.agent_conversation import AgentConversationService
    from application_state.content import pages
    from evals.buddy_benchmark.workflow import capture_lore_confirmation

    world = "elderwyld"
    route = f"/api/live/agent/worlds/{world}/conversation"
    conversation, foreign, turn, document, revision = (str(uuid4()) for _ in range(5))
    original = {"document_id": str(uuid4())}
    records = [original]
    actions = []
    receipt = {"document_id": document, "revision_id": str(uuid4()) if failure == "wrong_revision" else revision}
    new_page = {"document_id": document, "world_id": world, "content_status": "committed"}
    markdown = f"[Source]({route}/turns/{turn}/native-body-excerpts/0)"
    owner_revision = SimpleNamespace(work_revision_id=revision, content_sha256=text_digest(markdown),
                                     markdown=markdown, model_dump=lambda **_: {"work_revision_id": revision})
    monkeypatch.setattr(pages, "committed_page", lambda *_, **__: SimpleNamespace(
        revision=owner_revision, page=SimpleNamespace(title="Maelthor")))
    monkeypatch.setattr(AgentConversationService, "get_conversation",
                        lambda *args: SimpleNamespace(status="archived"))
    completion = {"collaboration": {"kind": "lore_page", "destination": {"title": "Maelthor"}},
                  "native_body_citations": [{}]}
    (tmp_path / "native-citation-reopen.json").write_text(json.dumps({"citations": [{"exact_reopen": True}]}))

    def handle(request):
        path = request.url.path
        if request.method == "GET":
            if path.endswith("/snapshot"):
                assert request.url.params["view"] == "committed"
                return httpx.Response(200, json={"record": new_page, "markdown": markdown, "committed_markdown": markdown,
                    "content_sha256": text_digest(markdown)})
            return httpx.Response(200, json={"records": records})
        command = json.loads(request.content)
        actions.append(path.rsplit("/", 1)[1])
        if len(actions) == 1:
            if failure == "unsafe_rejection":
                records.append(new_page)
            return httpx.Response(409, json={})
        if command["conversation_id"] == foreign:
            return httpx.Response(404, json={})
        if len(actions) == 3:
            return httpx.Response(409, json={})
        if actions[-1] == "review":
            return httpx.Response(200, json={"review_sha256": command["review_sha256"]})
        if len(actions) == 5:
            records.append(new_page)
        return httpx.Response(200, json={**receipt, "review_sha256": command["review_sha256"]})

    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
        capture_lore_confirmation(client, tmp_path, route, world, conversation, turn, completion, foreign)

    result = json.loads((tmp_path / "lore-confirmation-result.json").read_bytes())
    if failure == "unsafe_rejection":
        assert actions == ["confirm"]
        assert result == {"status": "incomplete", "reason": "lore-wrong-digest", "protected_pages_unchanged": False}
    else:
        assert actions == ["confirm", "confirm", "confirm", "review", "confirm", "confirm"]
        assert result["status"] == ("incomplete" if failure else "observed")
        assert result["checks"]["reopened_exact_revision"] is (failure is None)
        assert all(value for key, value in result["checks"].items() if key != "reopened_exact_revision")
