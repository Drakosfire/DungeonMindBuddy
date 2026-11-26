"""Fail-closed Build browser request binding; synthetic data only."""
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

import pytest

from evals.buddy_benchmark.browser_capture import validate_build_browser_request


def fixture():
    document, conversation, turn = str(uuid4()), str(uuid4()), str(uuid4())
    text, selection = "# Room\n\nA lantern glows.\n", "A lantern glows."
    content_hash = sha256(text.encode()).hexdigest()
    editor_hash = sha256(b"browser-editor-json").hexdigest()
    work = {"kind": "build", "object_id": document, "expected_revision": 2,
            "expected_content_sha256": content_hash}
    snapshot = {"schema": "dmb_build_draft_snapshot_v1", "world_id": "elderwyld",
        "document_id": document, "registry_revision": 2, "content_sha256": content_hash,
        "visibility": "internal", "draft_markdown": text, "draft_sha256": content_hash,
        "editor_sha256": editor_hash, "draft_generation": 0}
    basis = {k: snapshot[k] for k in ("world_id", "document_id", "registry_revision",
        "content_sha256", "visibility", "draft_sha256", "editor_sha256", "draft_generation")}
    basis.update(caret=8, selection_generation=1, selection={"end": 23, "text": selection})
    request = {"schema": "dmb_agent_turn_request_v1", "client_thread_id": str(uuid4()),
        "turn_id": turn, "surface": {"surface_id": "build", "instance_id": document},
        "owner_scope": {"kind": "world", "world_id": "elderwyld"}, "primary_work": work,
        "client_work_state": "saved_clean", "graph_request": {"mode": "world", "world_id": "elderwyld",
            "revision_pin": "rev:fixture", "campaign_id": None, "focus": {"kind": "none", "campaign_id": None, "session_id": None}},
        "graph_selection": None, "message": "Tighten the selected sentence.",
        "build_draft_context": {"snapshot": snapshot, "conversation_id": conversation,
            "expected_pointer_revision": 1},
        "build_write_capability": {"idempotency_key": str(uuid4()), "conversation_id": conversation,
            "expected_pointer_revision": 1, "basis": basis, "instruction": "", "draft_markdown": text}}
    controls = dict(world="elderwyld", work=work, question=request["message"],
                    selection_text=selection, conversation_id=conversation, pointer_revision=1)
    return request, controls


def test_actual_selection_binding_accepts_exact_fixture():
    request, controls = fixture()
    assert validate_build_browser_request(request, **controls).build_write_capability.basis.selection.text == controls["selection_text"]


@pytest.mark.parametrize("mutation", ["missing", "selection", "conversation", "pointer", "editor", "page", "question", "ambiguous"])
def test_browser_selection_binding_rejects_mismatch(mutation):
    request, controls = fixture()
    request = deepcopy(request)
    if mutation == "missing":
        request.pop("build_write_capability")
    elif mutation == "selection":
        controls["selection_text"] = "different"
    elif mutation == "conversation":
        controls["conversation_id"] = str(uuid4())
    elif mutation == "pointer":
        controls["pointer_revision"] = 2
    elif mutation == "editor":
        request["build_write_capability"]["basis"]["editor_sha256"] = "a" * 64
    elif mutation == "page":
        controls["work"] = {**controls["work"], "object_id": str(uuid4())}
    elif mutation == "question":
        controls["question"] = "Different request"
    else:
        text = request["build_draft_context"]["snapshot"]["draft_markdown"]
        text += controls["selection_text"]
        digest = sha256(text.encode()).hexdigest()
        request["build_draft_context"]["snapshot"].update(draft_markdown=text, draft_sha256=digest)
        request["build_write_capability"].update(draft_markdown=text)
        request["build_write_capability"]["basis"]["draft_sha256"] = digest
    with pytest.raises(ValueError):
        validate_build_browser_request(request, **controls)


def test_build_preflight_cli_requires_owned_clone_and_case():
    from evals.buddy_benchmark import workflow
    with pytest.raises(SystemExit):
        workflow.main(["capture", "--manifest", "fixture.json", "--output", "capture", "--build-fixture"])
    with pytest.raises(SystemExit):
        workflow.main(["capture-context", "--manifest", "fixture.json", "--output", "capture",
                       "--build-fixture", "--case", "PAGE-EDIT-1", "--clone-app"])


@pytest.mark.parametrize("live", [False, True])
def test_build_preflight_cli_selects_existing_capture_owner(monkeypatch, live):
    from evals.buddy_benchmark import workflow
    calls = []
    monkeypatch.setattr(workflow, "capture", lambda *args, **kwargs: calls.append((args, kwargs)))
    workflow.main(["capture", "--manifest", "fixture.json", "--output", "capture",
                   "--build-fixture", "--case", "PAGE-EDIT-1", "--clone-app", *(["--live-build"] if live else [])])
    assert calls == [(("fixture.json", "capture"), {"clone_app": True,
        "browser_case": "PAGE-EDIT-1", "build_fixture": True, "live_build": live})]


def test_live_build_terminal_handles_stream_delivery_and_error():
    from evals.buddy_benchmark.browser_capture import build_browser_terminal

    media = "text/event-stream; charset=utf-8"
    assert build_browser_terminal(
        b'data: {"schema":"dmb_build_turn_stream_v1","client_turn_id":"turn-1","kind":"progress"}\r\n\r\ndata: {"schema":"dmb_build_turn_stream_v1","client_turn_id":"turn-1","kind":"result","response":{"answer":"ok"}}\r\n\r\n',
        200, media, "turn-1",
    ) == ({"answer": "ok"}, 200)
    assert build_browser_terminal(
        b'data: {"schema":"dmb_build_turn_stream_v1","client_turn_id":"turn-1","kind":"error","status":409,"detail":"stale"}\n\n', 200, media, "turn-1",
    ) == ({"detail": "stale"}, 409)
    with pytest.raises(ValueError, match="no terminal"):
        build_browser_terminal(b'data: {"schema":"dmb_build_turn_stream_v1","client_turn_id":"turn-1","kind":"progress"}\n\n', 200, media, "turn-1")
    with pytest.raises(ValueError, match="another request"):
        build_browser_terminal(
            b'data: {"schema":"dmb_build_turn_stream_v1","client_turn_id":"other","kind":"error","status":409}\n\n',
            200, media, "turn-1",
        )
