from uuid import uuid4

import pytest

from application_state.agent_conversation.plan_authoring import PlanAuthoringCaptureV1, text_digest
from evals.buddy_benchmark.browser_capture import validate_plan_browser_placement


@pytest.mark.parametrize("mismatch", [None, "missing_catalog", "wrong_revision", "wrong_pointer", "wrong_selection"])
def test_plan_browser_placement_binding(mismatch):
    world, document, conversation = "elderwyld", str(uuid4()), str(uuid4())
    markdown = "A live draft."
    editor = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"A live draft."}]}]}'
    selection = '{"type":"text","anchor":14,"head":14}'
    capture = PlanAuthoringCaptureV1.model_validate({
        "idempotency_key": str(uuid4()), "conversation_id": conversation,
        "expected_pointer_revision": 1, "world_id": world, "document_id": document,
        "base_revision": 3, "base_content_sha256": text_digest(markdown),
        "draft_markdown": markdown, "draft_sha256": text_digest(markdown),
        "editor_json": editor, "editor_sha256": text_digest(editor),
        "selection_json": selection, "selection_sha256": text_digest(selection),
        "from": 14, "to": 14, "draft_generation": 0, "selection_generation": 1,
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
    if mismatch:
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
