"""Frozen placement membership is separate from browser-owned PM positions."""
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError
from tests.application_state.test_plan_authoring import capture_payload
from application_state.agent_conversation.plan_authoring import (
    PlanAuthoringCaptureV1, PlanAuthoringBoundaryCaptureV1, text_digest,
)
from application_state.agent_conversation.plan_placement import (
    PlanPlacementCatalogV1, PlanPlacementOptionV1,
    PlanPlacementCatalogV2, PlanPlacementOptionV2, paragraph_placement_label,
    decode_plan_placement_catalog,
)
from tests.test_plan_jev_dispatch import plan_adapter as plan_adapter
from tests.test_plan_jev_harness import unavailable_native_sources  # noqa: F401


def original_capture():
    payload = capture_payload()
    content = [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Objective"}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "Keep the alternatives open."}]},
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Beat"}]},
    ]
    editor = json.dumps({"type": "doc", "content": content}, separators=(",", ":"))
    payload.update(editor_json=editor, editor_sha256=text_digest(editor))
    return PlanAuthoringCaptureV1.model_validate(payload)


def catalog_for(original):
    captured = PlanPlacementOptionV1(selector="captured", kind="captured_target", label="Captured caret",
        root_boundary=None, position=None, target_capture_sha256=original.sha256)
    boundary = PlanPlacementOptionV1(selector="after:0", kind="after_section", label="After Objective",
        root_boundary=2, position=39, target_capture_sha256="0" * 64)
    boundary = boundary.model_copy(update={"target_capture_sha256": boundary.derived_target(original).sha256})
    return PlanPlacementCatalogV1(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, boundary))


def paragraph_catalog_for(original, kind="after_paragraph", index=1):
    content = json.loads(original.editor_json)["content"]
    captured = PlanPlacementOptionV2(selector="captured", kind="captured_target",
        label="At the captured text caret", source_root_index=None, root_boundary=None,
        position=None, target_capture_sha256=original.sha256)
    option = PlanPlacementOptionV2(selector="place1", kind=kind,
        label=paragraph_placement_label(content, index, kind), source_root_index=index,
        root_boundary=index + int(kind == "after_paragraph"), position=39,
        target_capture_sha256="0" * 64)
    option = option.model_copy(update={"target_capture_sha256": option.derived_target(original).sha256})
    return PlanPlacementCatalogV2(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, option))


def complete_paragraph_only_catalog(original):
    content = json.loads(original.editor_json)["content"]
    captured = PlanPlacementOptionV2(selector="captured", kind="captured_target",
        label="At the captured text caret", source_root_index=None, root_boundary=None,
        position=None, target_capture_sha256=original.sha256)
    offsets = [0]
    for node in content:
        text = "".join(child["text"] for child in node["content"])
        offsets.append(offsets[-1] + len(text.encode("utf-16-le")) // 2 + 2)
    options = [captured]
    for index in range(len(content)):
        for kind in ("after_paragraph", "before_paragraph"):
            boundary = index + int(kind == "after_paragraph")
            options.append(PlanPlacementOptionV2(selector=f"place{len(options)}", kind=kind,
                label=paragraph_placement_label(content, index, kind), source_root_index=index,
                root_boundary=boundary, position=offsets[boundary], target_capture_sha256="0" * 64))
    options.append(PlanPlacementOptionV2(selector=f"place{len(options)}", kind="end_page",
        label="At the end of the page", source_root_index=None, root_boundary=len(content),
        position=offsets[-1], target_capture_sha256="0" * 64))
    return PlanPlacementCatalogV2(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=tuple(option.model_copy(
            update={"target_capture_sha256": option.derived_target(original).sha256}) for option in options))


def test_explicit_catalog_decoder_retains_v1_hash_and_rejects_unknown_versions():
    from pydantic import TypeAdapter
    from application_state.agent_conversation.plan_placement import PlanPlacementCatalog
    adapter = TypeAdapter(PlanPlacementCatalog)
    original = original_capture()
    for catalog in (catalog_for(original), paragraph_catalog_for(original)):
        wire = catalog.model_dump(mode="json", by_alias=True)
        decoded = decode_plan_placement_catalog(wire)
        assert type(decoded) is type(catalog)
        assert decoded.sha256 == catalog.sha256
        assert adapter.validate_python(wire).sha256 == decoded.sha256
    legacy = catalog_for(original).model_dump(mode="json", by_alias=True)
    legacy.pop("schema")
    assert decode_plan_placement_catalog(legacy).sha256 == catalog_for(original).sha256
    assert type(adapter.validate_python(legacy)) is PlanPlacementCatalogV1
    untagged_v2 = paragraph_catalog_for(original).model_dump(mode="json", by_alias=True)
    untagged_v2.pop("schema")
    with pytest.raises(ValidationError):
        adapter.validate_python(untagged_v2)
    with pytest.raises(ValidationError):
        decode_plan_placement_catalog(legacy | {"schema": "dmb_plan_placement_catalog_v99"})


@pytest.mark.parametrize("decision", ["write:place1", "clarify", "discuss"])
def test_v2_catalog_survives_dispatch_decision_sql_and_cold_read_without_implicit_reservation(
    plan_adapter, application_state_dsn, decision,
):
    import asyncio
    import psycopg
    from application_state.agent_conversation import AgentConversationService
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.agent_turn_service import _submitted_turn_intent
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from tests.test_plan_jev_authoring import admitted_authoring, SemanticWire

    original, _ = admitted_authoring(plan_adapter, admit=False)
    catalog = complete_paragraph_only_catalog(original)
    wire = plan_adapter.request.model_dump(mode="json", by_alias=True)
    wire["plan_placement_catalog"] = catalog.model_dump(mode="json", by_alias=True)
    plan_adapter.request = AgentTurnRequest.model_validate(wire)
    untagged = json.loads(json.dumps(wire))
    untagged["plan_placement_catalog"].pop("schema")
    with pytest.raises(ValidationError):
        AgentTurnRequest.model_validate(untagged)
    plan_adapter.submitted_intent = _submitted_turn_intent(plan_adapter.request, world_id="world:one")
    selected, _ = asyncio.run(PlanJevDispatch.requested_work(plan_adapter, page_title="Preparation").run(
        transport=SemanticWire(plan_adapter, decision), api_key="synthetic-not-secret"))
    service = AgentConversationService()
    cold = service.list_turns("world:one", plan_adapter.turn.conversation_id)[0]
    choices = [event for event in cold.graph_context_execution.events
               if event.kind == "plan_requested_work_selected_v2"]
    assert len(choices) == 1
    retained = decode_plan_placement_catalog(choices[0].placement_catalog)
    assert type(retained) is PlanPlacementCatalogV2
    assert retained.sha256 == catalog.sha256
    assert retained.model_dump(mode="json", by_alias=True) == wire["plan_placement_catalog"]
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM plan_action.action").fetchone()[0] == 0
    if decision == "write:place1":
        assert selected == "write_current_page"
        target = retained.resolve(original, "place1")
        assert target.selection_json == original.selection_json
        action, fresh = service.reserve_plan_authoring_action(capture=target,
            turn_id=cold.turn_id, expected_revision=cold.revision)
        assert fresh and action.authoring_origin.capture_sha256 == target.sha256
    else:
        assert selected == decision


def test_send_rejects_a_catalog_omitting_a_duplicate_paragraph(plan_adapter):
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from tests.test_plan_jev_authoring import admitted_authoring

    original, _ = admitted_authoring(plan_adapter, admit=False)
    payload = original.model_dump(mode="json", by_alias=True)
    editor = json.loads(original.editor_json)
    editor["content"].append(editor["content"][0])
    editor_json = json.dumps(editor, separators=(",", ":"))
    draft = f"{original.draft_markdown}\n\n{original.draft_markdown}"
    payload.update(editor_json=editor_json, editor_sha256=text_digest(editor_json),
        draft_markdown=draft, draft_sha256=text_digest(draft))
    capture = PlanAuthoringCaptureV1.model_validate(payload)
    catalog = complete_paragraph_only_catalog(capture)
    wire = plan_adapter.request.model_dump(mode="json", by_alias=True)
    wire["plan_authoring_capture"] = payload
    wire["plan_placement_catalog"] = catalog.model_dump(mode="json", by_alias=True)
    AgentTurnRequest.model_validate(wire)
    wire["plan_placement_catalog"]["entries"] = [
        entry for entry in wire["plan_placement_catalog"]["entries"] if entry["source_root_index"] != 1]
    with pytest.raises(ValidationError, match="must offer every eligible captured location exactly once"):
        AgentTurnRequest.model_validate(wire)


def native_paragraph_placement_fixture(original):
    pieces = ["Unrelated opening.", "## Preparation", "The gate is locked.",
              "Check supplies.", "## Rumours", "The gate is locked."]
    content = [dict(type="heading", attrs={"level": 2}, content=[dict(type="text", text=text[3:])])
               if text.startswith("## ") else dict(type="paragraph", content=[dict(type="text", text=text)])
               for text in pieces]
    editor = json.dumps(dict(type="doc", content=content), separators=(",", ":"))
    selection = '{"type":"text","anchor":1,"head":1}'
    draft = "\n\n".join(pieces)
    payload = original.model_dump(mode="json", by_alias=True)
    payload.update(editor_json=editor, editor_sha256=text_digest(editor), draft_markdown=draft,
        draft_sha256=text_digest(draft), selection_json=selection, selection_sha256=text_digest(selection),
        **{"from": 1, "to": 1})
    capture = PlanAuthoringCaptureV1.model_validate(payload)
    captured = PlanPlacementOptionV2(selector="captured", kind="captured_target", label="At the captured text caret",
        source_root_index=None, root_boundary=None, position=None, target_capture_sha256=capture.sha256)
    # Fixture-only PM sizes for these simple heading/text nodes. The real
    # compiler/position owner is exercised separately with a mounted editor.
    position = sum(len("".join(child["text"] for child in node["content"]).encode("utf-16-le")) // 2 + 2
                   for node in content[:3])
    boundary = PlanPlacementOptionV2(selector="place1", kind="after_paragraph",
        label=paragraph_placement_label(content, 2, "after_paragraph"), source_root_index=2,
        root_boundary=3, position=position, target_capture_sha256="0" * 64)
    boundary = boundary.model_copy(update={"target_capture_sha256": boundary.derived_target(capture).sha256})
    catalog = PlanPlacementCatalogV2(original_capture_sha256=capture.sha256,
        editor_sha256=capture.editor_sha256, entries=(captured, boundary))
    return capture, catalog


@pytest.mark.parametrize("failure", ["changed_capture", "changed_page", "changed_conversation"])
def test_current_native_v2_paragraph_target_refuses_changed_authority(
    plan_adapter, tmp_path, monkeypatch, failure,
):
    from tests.test_plan_jev_authoring import _shared_plan_authoring_case
    plan_adapter.request = plan_adapter.request.model_copy(update={
        "message": "Add a warning after the Preparation paragraph about the locked gate."})
    _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, "place1", "base",
        failure=failure, placement_factory=native_paragraph_placement_fixture)


@pytest.mark.parametrize("mode", ["mixed", "rules_only"])
def test_current_v2_rules_fragment_excludes_host_status_without_losing_prose_or_citations(
    plan_adapter, tmp_path, monkeypatch, mode,
):
    from tests.test_plan_jev_authoring import _shared_plan_authoring_case

    response = _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, "place1", mode,
        placement_factory=native_paragraph_placement_fixture)
    assert response.plan_proposal.replacement_markdown.strip()
    assert "This answer uses partial retrieval" not in response.plan_proposal.replacement_markdown


@pytest.mark.parametrize("version", [1, 2])
def test_native_clarification_admission_rejects_empty_v2_even_without_sdk_conformance(
    plan_adapter, tmp_path, monkeypatch, application_state_dsn, version,
):
    import generationengine.client as generation_client
    import psycopg
    from tests.test_plan_jev_authoring import _shared_plan_authoring_case
    from tests.test_plan_jev_writer import WriterWire
    from apps.live_control_server.services import agent_turn_service
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.native_plan_assertions import POLICY
    from application_state.content.service import snapshot_content

    validate = generation_client.validate_against_schema
    transport = WriterWire.handle_async_request
    execute = agent_turn_service.execute_agent_turn
    bypassed, sources, adapters = [], [], []

    def bypass_only_writer_empty_reply(candidate, schema):
        if ((schema.get("properties", {}).get("answer_segments", {}).get("minItems") == 1
                and candidate.get("answer_segments") == [])
                or (schema.get("properties", {}).get("question", {}).get("minLength") == 1
                    and candidate.get("question") == "")):
            bypassed.append(True)
            return  # Simulate a captured provider reply lacking SDK conformance.
        return validate(candidate, schema)

    async def empty_reply(writer, request):
        adapters.append(writer.adapter)
        writer.text = json.dumps(dict(question="") if json.loads(request.content)['text']['format']['name'] == 'plan_contextual_question_v1'
            else dict(schema=POLICY, answer_segments=[], limitations=[]))
        return await transport(writer, request)

    def source_guard(request, **kwargs):
        before = snapshot_content(request.plan_authoring_capture.document_id)
        try:
            return execute(request, **kwargs)
        finally:
            after = snapshot_content(request.plan_authoring_capture.document_id)
            sources.append((before.markdown, before.work_object.object_revision)
                == (after.markdown, after.work_object.object_revision))

    monkeypatch.setattr(generation_client, "validate_against_schema", bypass_only_writer_empty_reply)
    monkeypatch.setattr(WriterWire, "handle_async_request", empty_reply)
    monkeypatch.setattr(agent_turn_service, "execute_agent_turn", source_guard)
    try:
        def run():
            return _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch,
                "place1" if version == 2 else "captured", "base", routing="clarify",
                dsn=application_state_dsn,
                placement_factory=native_paragraph_placement_fixture if version == 2 else None)
        if version == 2:
            with pytest.raises(agent_turn_service.AgentTurnServiceError):
                run()
        else:
            run()  # Retained V1 keeps its historical status-only normalization.
    finally:
        for adapter in adapters:
            if adapter.fence is not None:
                adapter.fence.renewer.stop_and_join()
    service = AgentConversationService()
    pointer = service.get_world_pointer("world:one")
    turn = service.list_turns("world:one", pointer.active_conversation_id)[-1]
    assert turn.status == ("interrupted" if version == 2 else "completed")
    assert (turn.completion is None) == (version == 2)
    assert bool(bypassed) == (version == 2)
    if version == 2:
        attempts = service.list_context_trace_attempts(world_id="world:one", turn_id=turn.turn_id)
        failure_codes = [event.code for attempt in attempts for event in attempt.observations
            if event.kind == "failure"]
        assert "plan_writer_completion_rejected" in failure_codes
        assert "plan_writer_generation_rejected" not in failure_codes
    assert sources and all(sources)
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM plan_action.action").fetchone()[0] == 0


@pytest.mark.parametrize("routing", [None, "clarify", "discuss"])
def test_current_native_caller_v2_paragraph_proposal_and_explicit_save_or_no_reservation(
    plan_adapter, tmp_path, monkeypatch, application_state_dsn, routing,
):
    import psycopg
    from uuid import uuid4
    from application_state.agent_conversation import AgentConversationService
    from application_state.content.service import current_committed_revision
    from application_state.plan_action_dialogue import authoring_review as reviews
    from tests.test_plan_jev_authoring import _shared_plan_authoring_case

    plan_adapter.request = plan_adapter.request.model_copy(update={
        "message": "Add a warning after the Preparation paragraph about the locked gate."})
    response = _shared_plan_authoring_case(plan_adapter, tmp_path, monkeypatch, "place1", "base",
        routing=routing, dsn=application_state_dsn, placement_factory=native_paragraph_placement_fixture)
    service = AgentConversationService()
    pointer = service.get_world_pointer("world:one")
    cold = service.list_turns("world:one", pointer.active_conversation_id)[0]
    assert type(cold.graph_context_execution.policy.action.placement_catalog) is PlanPlacementCatalogV2
    action_type = type(cold.graph_context_execution.policy.action)
    action_wire = cold.graph_context_execution.policy.action.model_dump(mode="json", by_alias=True)
    assert action_type.model_validate(action_wire).placement_catalog.schema_ == "dmb_plan_placement_catalog_v2"
    action_wire["placement_catalog"].pop("schema")
    with pytest.raises(ValidationError):
        action_type.model_validate(action_wire)
    if routing is not None:
        with psycopg.connect(application_state_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM plan_action.action").fetchone()[0] == 0
        return
    proposal = response.plan_proposal
    from application_state.agent_conversation.plan_authoring import authored_markdown
    footer = "This answer uses partial retrieval and does not establish corpus completeness."
    assert footer in response.answer.text
    assert footer in authored_markdown(cold)  # Historical default projection is unchanged.
    assert footer not in proposal.replacement_markdown
    assert authored_markdown(cold, execution=cold.graph_context_execution) == proposal.replacement_markdown
    # These copies exercise projection only, never proposal/Save authority.
    # Equal literal words must survive; a typed status-only fragment must refuse.
    from application_state.agent_conversation import types as t
    literal = t.PlanWorldGraphProposalSegmentV1(kind="proposal", label="invented_idea", text=footer)
    projection_only = cold.model_copy(update={"completion": cold.completion.model_copy(
        update={"answer_segments": [literal]})})
    assert authored_markdown(projection_only, execution=cold.graph_context_execution) == footer
    status = next(s for s in cold.completion.answer_segments if isinstance(s, t.SurfaceLimitationV1))
    projection_only = cold.model_copy(update={"completion": cold.completion.model_copy(
        update={"answer_segments": [status]})})
    with pytest.raises(ValueError, match="no nonempty admitted content"):
        authored_markdown(projection_only, execution=cold.graph_context_execution)
    capture = proposal.capture
    assert capture.root_boundary == 3 and capture.from_ != 1
    assert json.loads(capture.selection_json) == {"type": "text", "anchor": 1, "head": 1}
    action_id = proposal.origin.action_id

    def command(review, operation, **values):
        return reviews.execute_review_command(capture.world_id, action_id,
            dict(operation=operation, command_id=uuid4(), origin_sha256=proposal.origin.sha256,
                 expected_revision=review.revision if review else 0, **values))

    opened = command(None, "open")
    before = json.loads(capture.editor_json)["content"]
    inserted = dict(type="paragraph", content=[dict(type="text", text=opened.markdown)])
    after_nodes = before[:3] + [inserted] + before[3:]
    after_editor = json.dumps(dict(type="doc", content=after_nodes), separators=(",", ":"))
    after_markdown = "\n\n".join(("## " if node["type"] == "heading" else "")
        + "".join(child["text"] for child in node["content"]) for node in after_nodes)
    application_id = uuid4()
    prepared = command(opened, "prepare", application_id=application_id,
        after_editor_json=after_editor, after_editor_sha256=text_digest(after_editor),
        after_markdown=after_markdown, after_draft_sha256=text_digest(after_markdown), after_title="Preparation")
    confirm = dict(operation="confirm", command_id=uuid4(), origin_sha256=proposal.origin.sha256,
        expected_revision=prepared.revision, application_id=application_id)
    saved = reviews.execute_review_command(capture.world_id, action_id, confirm)
    assert reviews.execute_review_command(capture.world_id, action_id, confirm) == saved
    committed = current_committed_revision(capture.document_id, kind="plan")
    assert committed.work_revision.markdown == after_markdown
    assert saved.applications[-1].outcome == "saved"
    assert json.loads(saved.applications[-1].after_editor_json)["content"] == after_nodes


@pytest.mark.parametrize("kind,boundary", [("before_paragraph", 1), ("after_paragraph", 2)])
def test_inert_v2_paragraph_catalog_binds_semantic_source_and_real_selection(kind, boundary):
    original = original_capture()
    catalog = paragraph_catalog_for(original, kind)
    selected = catalog.resolve(original, "place1")
    assert isinstance(selected, PlanAuthoringBoundaryCaptureV1)
    assert selected.root_boundary == boundary
    assert selected.selection_json == original.selection_json
    assert selected.editor_json == original.editor_json
    assert original.from_ == original.to == 14
    assert selected.from_ == selected.to == 39
    assert catalog.model_choices() == [
        {"selector": "captured", "label": "At the captured text caret"},
        {"selector": "place1", "label": f"{'Before' if boundary == 1 else 'After'} paragraph in Objective: Keep the alternatives open."},
    ]
    # This new nested value is deliberately not admitted by any old V1 reader.
    with pytest.raises(ValidationError):
        PlanPlacementCatalogV1.model_validate(catalog.model_dump(mode="json", by_alias=True))
    legacy = catalog_for(original)
    assert PlanPlacementCatalogV1.model_validate_json(legacy.model_dump_json(by_alias=True)).sha256 == legacy.sha256


@pytest.mark.parametrize("change", [
    {"source_root_index": 0}, {"root_boundary": 1},
    {"label": "After a different paragraph"}, {"source_root_index": 99},
])
def test_v2_refuses_false_semantic_targets_even_with_a_recomputed_target_digest(change):
    original = original_capture()
    catalog = paragraph_catalog_for(original)
    option = catalog.entries[1].model_copy(update=change)
    option = option.model_copy(update={"target_capture_sha256": option.derived_target(original).sha256})
    changed = catalog.model_copy(update={"entries": (catalog.entries[0], option)})
    with pytest.raises(ValueError):
        changed.require_original(original)


def test_v2_opaque_selectors_and_closed_original_replacement_authority():
    original = original_capture()
    catalog = paragraph_catalog_for(original)
    with pytest.raises(ValueError, match="not offered"):
        catalog.resolve(original, "place999")
    payload = catalog.model_dump(mode="json", by_alias=True)
    payload["entries"][1]["selector"] = "after:1"
    with pytest.raises(ValidationError, match="opaque local selector"):
        PlanPlacementCatalogV2.model_validate(payload)
    payload = original.model_dump(mode="json", by_alias=True)
    selection = '{"type":"text","anchor":8,"head":1}'
    payload.update(selection_json=selection, selection_sha256=text_digest(selection),
        target_kind="replace_selection", selected_text="Objecti", **{"from": 1, "to": 8})
    replacement = PlanAuthoringCaptureV1.model_validate(payload)
    with pytest.raises(ValueError, match="broadened"):
        catalog.entries[1].derived_target(replacement)


@pytest.mark.parametrize("node", [
    {"type": "paragraph"}, {"type": "table"},
    {"type": "paragraph", "content": [{"type": "image", "attrs": {"src": "private"}}]},
])
def test_v2_paragraph_source_does_not_admit_empty_prose_or_unrelated_objects(node):
    with pytest.raises(ValueError, match="prose"):
        paragraph_placement_label([node], 0, "after_paragraph")


def test_v2_cannot_transfer_to_another_world_or_enroll_composed_roots():
    original = original_capture()
    catalog = paragraph_catalog_for(original)
    payload = original.model_dump(mode="json", by_alias=True)
    payload["world_id"] = "foreign"
    with pytest.raises(ValueError, match="original captured page"):
        catalog.require_original(PlanAuthoringCaptureV1.model_validate(payload))
    doc = json.loads(original.editor_json)
    doc["content"][0] = {"type": "pageRow", "content": []}
    editor = json.dumps(doc, separators=(",", ":"))
    payload = original.model_dump(mode="json", by_alias=True)
    payload.update(editor_json=editor, editor_sha256=text_digest(editor))
    composed = PlanAuthoringCaptureV1.model_validate(payload)
    current = catalog.model_copy(update={"original_capture_sha256": composed.sha256,
        "editor_sha256": composed.editor_sha256})
    with pytest.raises(ValueError, match="plain Plan"):
        current.require_original(composed)


@pytest.mark.parametrize("attrs,marks,section", [
    ({"level": 2}, [], "Preparation"),
    ({"level": 2, "pageBlockId": None}, [], "Preparation"),
    ({"level": 2}, [{"type": "bold"}], "Treasure"),
    ({"level": 2, "id": "real-heading"}, [], "Treasure"),
])
def test_v2_paragraph_context_uses_exact_named_table_caption_rules(attrs, marks, section):
    content = [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Preparation"}]},
        {"type": "heading", "attrs": attrs, "content": [{"type": "text", "text": "Treasure", "marks": marks}]},
        {"type": "table", "content": []},
        {"type": "paragraph", "content": [{"type": "text", "text": "Bring a key."}]},
    ]
    assert paragraph_placement_label(content, 3, "after_paragraph") == f"After paragraph in {section}: Bring a key."


@pytest.mark.parametrize("boundary", [1, 3])
def test_v2_after_section_requires_the_exact_end_even_with_valid_rehashed_capture(boundary):
    original = original_capture()
    captured = paragraph_catalog_for(original).entries[0]
    option = PlanPlacementOptionV2(selector="place1", kind="after_section",
        label="After the entire section Objective", source_root_index=0,
        root_boundary=boundary, position=39, target_capture_sha256="0" * 64)
    option = option.model_copy(update={"target_capture_sha256": option.derived_target(original).sha256})
    catalog = PlanPlacementCatalogV2(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, option))
    with pytest.raises(ValueError, match="exact semantic boundary"):
        catalog.require_original(original)
    fixed = option.model_copy(update={"root_boundary": 2})
    fixed = fixed.model_copy(update={"target_capture_sha256": fixed.derived_target(original).sha256})
    assert catalog.model_copy(update={"entries": (captured, fixed)}).require_original(original)


@pytest.mark.parametrize("kind,index,boundary,label", [
    ("after_section", 0, 2, "After the entire section Elsewhere"),
    ("before_heading", 0, 0, "Before Elsewhere"),
    ("end_page", None, 3, "After a paragraph"),
])
def test_v2_structural_labels_cannot_misrepresent_an_admitted_source_boundary(kind, index, boundary, label):
    original = original_capture()
    captured = paragraph_catalog_for(original).entries[0]
    option = PlanPlacementOptionV2(selector="place1", kind=kind, label=label,
        source_root_index=index, root_boundary=boundary, position=39, target_capture_sha256="0" * 64)
    option = option.model_copy(update={"target_capture_sha256": option.derived_target(original).sha256})
    catalog = PlanPlacementCatalogV2(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, option))
    with pytest.raises(ValueError):
        catalog.require_original(original)


def test_v2_captured_caret_cannot_be_labeled_as_a_different_semantic_destination():
    original = original_capture()
    catalog = paragraph_catalog_for(original)
    captured = catalog.entries[0].model_copy(update={"label": "After the Preparation paragraph"})
    changed = catalog.model_copy(update={"entries": (captured, catalog.entries[1])})
    with pytest.raises(ValueError, match="original selection authority"):
        changed.require_original(original)


@pytest.mark.parametrize('older_head', ['20261120_0170', '20261120_0171'])
def test_v2_reader_fence_refuses_older_application_and_downgrade_without_schema_mutation(
    application_state_dsn, monkeypatch, older_head,
):
    import psycopg
    from alembic import command
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError

    def version():
        with psycopg.connect(application_state_dsn) as conn:
            return conn.execute("SELECT version_num FROM application_state.schema_migrations").fetchone()[0]

    current_head = cli._alembic_head()
    assert version() == current_head
    with monkeypatch.context() as patch:
        patch.setattr(cli, "_alembic_head", lambda: older_head)
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
    assert version() == current_head
    with pytest.raises(RuntimeError, match="Retained saved-page citations require a compatible forward reader"):
        command.downgrade(cli.alembic_config(), "20261120_0171")
    assert version() == current_head
    cli.assert_at_head(dsn=application_state_dsn)


def test_frozen_catalog_resolves_host_target_without_overwriting_original_caret():
    original = original_capture()
    catalog = catalog_for(original)
    resolved = catalog.resolve(original, "after:0")
    assert isinstance(resolved, PlanAuthoringBoundaryCaptureV1)
    assert resolved.target_kind == "insert_at_boundary"
    assert resolved.root_boundary == 2
    assert resolved.from_ == resolved.to == 39
    assert original.from_ == original.to == 14
    assert resolved.selection_json == original.selection_json
    assert resolved.editor_json == original.editor_json
    assert resolved.draft_markdown == original.draft_markdown
    assert catalog.resolve(original, "captured") == original
    assert catalog.sha256 != original.sha256 != resolved.sha256
    assert catalog.model_choices() == [
        {"selector": "captured", "label": "Captured caret"},
        {"selector": "after:0", "label": "After Objective"},
    ]


@pytest.mark.parametrize("field,value", [
    ("world_id", "foreign"), ("document_id", "other"), ("base_revision", 4),
    ("conversation_id", str(uuid4())), ("draft_generation", 9),
])
def test_catalog_cannot_transfer_to_another_original_owner_or_snapshot(field, value):
    original = original_capture()
    payload = original.model_dump(mode="json", by_alias=True)
    payload[field] = value
    changed = PlanAuthoringCaptureV1.model_validate(payload)
    with pytest.raises(ValueError, match="original captured page"):
        catalog_for(original).resolve(changed, "after:0")


@pytest.mark.parametrize("change", [
    {"position": 1}, {"root_boundary": 1}, {"target_capture_sha256": "f" * 64},
])
def test_catalog_rejects_substituted_target_not_only_foreign_selector(change):
    original = original_capture()
    payload = catalog_for(original).model_dump(mode="json", by_alias=True)
    payload["entries"][1].update(change)
    with pytest.raises(ValueError, match="offered digest"):
        PlanPlacementCatalogV1.model_validate(payload).resolve(original, "after:0")


def test_unknown_selector_and_duplicate_or_missing_original_are_refused():
    original = original_capture()
    catalog = catalog_for(original)
    with pytest.raises(ValueError, match="not offered"):
        catalog.resolve(original, "after:99")
    payload = catalog.model_dump(mode="json", by_alias=True)
    payload["entries"].append(payload["entries"][0])
    with pytest.raises(ValidationError, match="unique captured target"):
        PlanPlacementCatalogV1.model_validate(payload)
    payload["entries"] = payload["entries"][1:2]
    with pytest.raises(ValidationError, match="unique captured target"):
        PlanPlacementCatalogV1.model_validate(payload)


def test_boundary_capture_has_no_replacement_or_playable_authority():
    original = original_capture()
    boundary = catalog_for(original).resolve(original, "after:0")
    for change in ({"selected_text": "Replace me"}, {"to": 40}, {"root_boundary": 4}):
        payload = boundary.model_dump(mode="json", by_alias=True)
        payload.update(change)
        with pytest.raises(ValidationError):
            PlanAuthoringBoundaryCaptureV1.model_validate(payload)
    with pytest.raises(ValueError, match="original captured page"):
        catalog_for(original).require_original(boundary)


def test_boundary_catalog_cannot_broaden_exact_reverse_selection():
    payload = original_capture().model_dump(mode="json", by_alias=True)
    selection = '{"type":"text","anchor":8,"head":1}'
    payload.update(selection_json=selection, selection_sha256=text_digest(selection),
        target_kind="replace_selection", selected_text="Objecti", **{"from": 1, "to": 8})
    replacement = PlanAuthoringCaptureV1.model_validate(payload)
    source = catalog_for(original_capture()).model_dump(mode="json", by_alias=True)
    source.update(original_capture_sha256=replacement.sha256, editor_sha256=replacement.editor_sha256)
    with pytest.raises(ValueError, match="Replacement authority"):
        PlanPlacementCatalogV1.model_validate(source).require_original(replacement)


def test_retained_v1_capture_keeps_exact_old_digest_and_text_selection_rules():
    original = original_capture()
    assert PlanAuthoringCaptureV1.model_validate_json(original.model_dump_json(by_alias=True)).sha256 == original.sha256
    payload = original.model_dump(mode="json", by_alias=True)
    payload["from"] = payload["to"] = 39
    with pytest.raises(ValidationError, match="directional selection"):
        PlanAuthoringCaptureV1.model_validate(payload)


def test_current_intent_projection_preserves_frozen_v2_wire_and_location_choices():
    from pathlib import Path
    from hashlib import sha256
    from application_state.agent_conversation.plan_authoring import (
        CURRENT_REQUEST_INTENT_POLICY, prepare_requested_work_decision,
        validate_requested_work_wire, validate_prepared_requested_work,
    )
    from application_state.agent_conversation.plan_placement import (
        PlanRequestedWorkInputV2, PlanRequestedWorkInputV3,
    )
    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    raw = frozen["wire_json"].encode()
    assert sha256(raw).hexdigest() == frozen["wire_sha256"]
    old = PlanRequestedWorkInputV2.model_validate(frozen["parent"])
    validate_requested_work_wire(old, raw, expected_model='jev-1.14.0')
    with pytest.raises(ValueError, match='wire differs'):
        validate_requested_work_wire(old, raw, expected_model='typesafe-ai/jev-1.14.0')
    current = PlanRequestedWorkInputV3.model_validate(frozen["parent"] | {"schema": "dmb_plan_requested_work_input_v3"})
    projected = prepare_requested_work_decision(current)
    wire = json.loads(raw)
    assert projected.state == wire["state"] | {"intent_policy": CURRENT_REQUEST_INTENT_POLICY}
    assert projected.questions[0].options == tuple(wire["questions"]["requested_work"]["criteria"])
    wire["state"] = projected.state
    current_raw = json.dumps(wire).encode()
    validate_requested_work_wire(current, current_raw, expected_model='jev-1.14.0')
    for parent, substituted in ((old, current_raw), (current, raw)):
        with pytest.raises(ValueError, match="wire differs"):
            validate_requested_work_wire(parent, substituted, expected_model='jev-1.14.0')
    with pytest.raises(ValueError, match="requires the V3"):
        validate_prepared_requested_work(old, None)


def under_heading_catalog(original, root_boundary=1):
    captured = catalog_for(original).entries[0]
    entry = PlanPlacementOptionV1(selector="under:0", kind="after_heading",
        label="Directly below the heading Objective, before its existing body",
        root_boundary=root_boundary, position=11, target_capture_sha256="0" * 64)
    entry = entry.model_copy(update={"target_capture_sha256": entry.derived_target(original).sha256})
    return PlanPlacementCatalogV1(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=(captured, entry))


def test_under_heading_resolves_inside_section_and_preserves_frozen_original():
    original = original_capture()
    catalog = under_heading_catalog(original)
    resolved = catalog.resolve(original, "under:0")
    assert resolved.root_boundary == 1
    assert resolved.from_ == resolved.to == 11
    assert resolved.editor_json == original.editor_json
    assert resolved.selection_json == original.selection_json
    assert original.from_ == original.to == 14
    assert catalog.resolve(original, "captured") == original
    assert PlanPlacementCatalogV1.model_validate_json(catalog.model_dump_json(by_alias=True)).sha256 == catalog.sha256


@pytest.mark.parametrize("root_boundary", [0, 2, 3])
def test_under_heading_cannot_substitute_before_or_after_whole_section_even_with_matching_digest(root_boundary):
    original = original_capture()
    with pytest.raises(ValueError, match="captured root heading"):
        under_heading_catalog(original, root_boundary).require_original(original)


@pytest.mark.parametrize("selector", ["after:0", "under:00", "under:-1", "under:1"])
def test_under_heading_rejects_wrong_selector_or_nonheading(selector):
    original = original_capture()
    payload = under_heading_catalog(original).model_dump(mode="json", by_alias=True)
    payload["entries"][1]["selector"] = selector
    with pytest.raises(ValueError):
        catalog = PlanPlacementCatalogV1.model_validate(payload)
        entry = catalog.entries[1]
        entry = entry.model_copy(update={"target_capture_sha256": entry.derived_target(original).sha256})
        catalog.model_copy(update={"entries": (catalog.entries[0], entry)}).require_original(original)


def test_under_heading_decision_exposes_exact_location_without_offsets_or_new_save_authority():
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV3, work_choice
    from pathlib import Path
    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    original = original_capture()
    catalog = under_heading_catalog(original)
    parent = frozen["parent"] | {"schema": "dmb_plan_requested_work_input_v3",
        "original_capture": original.model_dump(mode="json", by_alias=True),
        "target_capture_sha256": original.sha256,
        "placement_catalog": catalog.model_dump(mode="json", by_alias=True)}
    request = PlanRequestedWorkInputV3.model_validate(parent)
    decision = prepare_requested_work_decision(request)
    assert "write:under:0" in decision.questions[0].options
    assert "inside that section before its existing body" in decision.state["placement_policy"]
    assert "Use the offered under:<selector> location for writing under a named heading." in decision.state["placement_policy"]
    assert all(set(row) == {"selector", "label"} for row in decision.state["offered_page_locations"])
    choice = work_choice(request, "write:under:0")
    assert choice["placement_selector"] == "under:0"
    assert choice["target_capture_sha256"] == catalog.resolve(original, "under:0").sha256


def test_v2_heading_guidance_uses_actual_opaque_choice_in_prepared_wire():
    from pathlib import Path
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV3
    original = original_capture()
    legacy = under_heading_catalog(original)
    entries = []
    for index, option in enumerate(legacy.entries):
        fields = option.model_dump(mode="json")
        fields.update(selector="captured" if index == 0 else "place1",
                      source_root_index=None if index == 0 else 0)
        if index == 0:
            fields["label"] = "At the captured text caret"
        entries.append(PlanPlacementOptionV2.model_validate(fields))
    catalog = PlanPlacementCatalogV2(original_capture_sha256=original.sha256,
        editor_sha256=original.editor_sha256, entries=tuple(entries))
    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    parent = frozen["parent"] | {"schema": "dmb_plan_requested_work_input_v3",
        "original_capture": original.model_dump(mode="json", by_alias=True),
        "target_capture_sha256": original.sha256,
        "placement_catalog": catalog.model_dump(mode="json", by_alias=True)}
    decision = prepare_requested_work_decision(PlanRequestedWorkInputV3.model_validate(parent))
    untagged = json.loads(json.dumps(parent))
    untagged["placement_catalog"].pop("schema")
    with pytest.raises(ValidationError):
        PlanRequestedWorkInputV3.model_validate(untagged)
    serialized = json.dumps({"state": decision.state, "options": decision.questions[0].options})
    assert "write:place1" in serialized
    assert "under:" not in serialized
    assert "Use the opaque selector offered with the matching" in serialized
    assert "match the requested side, paragraph passage, and any named section" in serialized
    assert "choose clarify. Do not break that tie using document order" in serialized
    assert "source_root_index" not in serialized


@pytest.mark.parametrize('operation',['discuss','write_current_page'])
def test_explicit_operation_restricts_actual_sdk_choices_and_rejects_wire_substitution(operation):
    from pathlib import Path
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision, validate_requested_work_wire
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV5
    frozen=json.loads((Path(__file__).parents[1]/'fixtures/plan_requested_work_v2_wire.json').read_text())
    parent=PlanRequestedWorkInputV5.model_validate(frozen['parent'] | {
        'schema':'dmb_plan_requested_work_input_v5','plan_requested_operation':operation,'authored_references':None})
    prepared=prepare_requested_work_decision(parent)
    choices=prepared.questions[0].options
    if operation=='discuss':
        assert choices==('discuss','clarify')
    else:
        assert 'discuss' not in choices
        assert {'clarify','different_destination'} <= set(choices)
        assert any(choice.startswith('write:') for choice in choices)
    assert prepared.state['plan_requested_operation']==operation
    with pytest.raises(ValueError,match='wire differs'):
        validate_requested_work_wire(parent,frozen['wire_json'].encode())


@pytest.mark.parametrize("operation",[None,"discuss","write_current_page"])
@pytest.mark.parametrize("extent",["section","full_document"])
def test_current_plan_reference_wire_keeps_semantics_and_host_binding_separate(operation,extent):
    from pathlib import Path
    from application_state.agent_conversation.authored_graph_references import (
        AuthoredGraphReferenceV1, AuthoredSourceReferenceV1, AuthoredReferencesV2)
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV6, PlanRequestedWorkInputV5
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision, validate_requested_work_wire
    shared=dict(managed_world_id="managed-world-SENTINEL",native_world_id="native-world-SENTINEL",binding_version=42)
    graph=AuthoredGraphReferenceV1(**shared,graph_revision="graph-revision-SENTINEL",node_id="node-SENTINEL",label="The Exchange")
    source=AuthoredSourceReferenceV1(**shared,knowledge_revision="knowledge-SENTINEL",source_artifact_id="source-SENTINEL",
        source_revision_id="source-revision-SENTINEL",evidence_ref_id="evidence-SENTINEL",content_sha256="e"*64,
        selection_kind=extent,section_id="f"*64 if extent=="section" else None,label="Session 20 recap")
    references=AuthoredReferencesV2(references=(graph,graph.model_copy(update={"node_id":"another-node-SENTINEL"}),source))
    frozen=json.loads((Path(__file__).parents[1]/"fixtures/plan_requested_work_v2_wire.json").read_text())
    values=frozen["parent"] | dict(schema="dmb_plan_requested_work_input_v6",plan_requested_operation=operation,
        authored_references=references.model_dump(mode="json",by_alias=True))
    parent=PlanRequestedWorkInputV6.model_validate(values)
    prepared=prepare_requested_work_decision(parent)
    assert prepared.state["author_selected_references"]==[
        {"kind":"graph_object","label":"The Exchange"},{"kind":"graph_object","label":"The Exchange"},
        {"kind":"source","label":"Session 20 recap","selection_kind":extent}]
    raw=json.dumps(dict(model=prepared.model,state=prepared.state,questions={
        q.name:dict(type="choice",instructions=q.question,criteria=dict.fromkeys(q.options)) for q in prepared.questions})).encode()
    assert b"SENTINEL" not in raw
    assert ("e"*64).encode() not in raw and ("f"*64).encode() not in raw
    validate_requested_work_wire(parent,raw)
    retained=PlanRequestedWorkInputV6.model_validate_json(parent.model_dump_json(by_alias=True))
    assert retained.authored_references==references
    # Identity is still committed by the parent although labels/semantic wire match.
    changed=parent.model_copy(update={"authored_references":references.model_copy(update={"references":(
        graph.model_copy(update={"graph_revision":"changed-host-pin"}),references.references[1],source)})})
    assert changed.digest!=parent.digest
    assert prepare_requested_work_decision(changed).state==prepared.state
    old=PlanRequestedWorkInputV5.model_validate(values | dict(schema="dmb_plan_requested_work_input_v5",plan_requested_operation=operation or "discuss"))
    assert prepare_requested_work_decision(old).state["author_selected_references"]==references.model_dump(mode="json",by_alias=True)
    with pytest.raises(ValueError,match="wire differs"):
        validate_requested_work_wire(old,raw)


@pytest.mark.parametrize("operation", [None, "discuss", "write_current_page"])
def test_intent_first_revision_preserves_old_wire_and_writing_options(operation):
    from pathlib import Path
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV6, PlanRequestedWorkInputV7
    from application_state.agent_conversation.plan_authoring import (
        CURRENT_REQUEST_INTENT_POLICY, QUESTION_FIRST_INTENT_POLICY,
        prepare_requested_work_decision, validate_requested_work_wire)

    frozen = json.loads((Path(__file__).parents[1] / "fixtures/plan_requested_work_v2_wire.json").read_text())
    values = frozen["parent"] | dict(schema="dmb_plan_requested_work_input_v6",
        authored_references=None, plan_requested_operation=operation)
    old = PlanRequestedWorkInputV6.model_validate(values)
    new = PlanRequestedWorkInputV7.model_validate(values | dict(schema="dmb_plan_requested_work_input_v7"))
    before, after = prepare_requested_work_decision(old), prepare_requested_work_decision(new)
    assert before.state["intent_policy"] == CURRENT_REQUEST_INTENT_POLICY
    assert after.state["intent_policy"] == QUESTION_FIRST_INTENT_POLICY
    assert before.questions == after.questions
    assert {k:v for k,v in before.state.items() if k not in {"intent_policy", "placement_policy"}} == {
        k:v for k,v in after.state.items() if k not in {"intent_policy", "placement_policy"}}
    for parent, prepared in [(old,before),(new,after)]:
        raw = json.dumps(dict(model=prepared.model,state=prepared.state,questions={
            q.name:dict(type="choice",instructions=q.question,criteria=dict.fromkeys(q.options))
            for q in prepared.questions})).encode()
        validate_requested_work_wire(parent,raw)
        other = new if parent is old else old
        with pytest.raises(ValueError,match="wire differs"):
            validate_requested_work_wire(other,raw)
    assert PlanRequestedWorkInputV7.model_validate_json(new.model_dump_json(by_alias=True)) == new


@pytest.mark.parametrize('operation',[None,'discuss','write_current_page'])
def test_connected_page_choice_is_explicit_and_cannot_override_interface_operation(operation):
    from pathlib import Path
    from application_state.agent_conversation.plan_placement import PlanRequestedWorkInputV7,PlanRequestedWorkInputV8,work_choice
    from application_state.agent_conversation.plan_authoring import prepare_requested_work_decision
    frozen=json.loads((Path(__file__).parents[1]/'fixtures/plan_requested_work_v2_wire.json').read_text())
    values=frozen['parent']|dict(schema='dmb_plan_requested_work_input_v8',authored_references=None,plan_requested_operation=operation)
    current=PlanRequestedWorkInputV8.model_validate(values)
    old=PlanRequestedWorkInputV7.model_validate(values|dict(schema='dmb_plan_requested_work_input_v7'))
    before,after=prepare_requested_work_decision(old),prepare_requested_work_decision(current)
    assert 'review_connected_page' not in before.questions[0].options
    assert ('review_connected_page' in after.questions[0].options)==(operation is None)
    assert set(after.questions[0].options)-{'review_connected_page'}==set(before.questions[0].options)
    assert PlanRequestedWorkInputV8.model_validate_json(current.model_dump_json(by_alias=True))==current
    with pytest.raises(ValueError):work_choice(old,'review_connected_page')
    if operation is not None:
        with pytest.raises(ValueError):work_choice(current,'review_connected_page')
    else:
        assert work_choice(current,'review_connected_page')==dict(requested_work='review_connected_page',placement_selector=None,target_capture_sha256=None)
