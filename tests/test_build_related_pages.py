"""Related saved pages through the actual SDK/APP writer proof boundaries."""

from hashlib import sha256
from uuid import UUID, uuid4
import json
import httpx2
import httpx
import pytest
from pydantic import ValidationError
from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation.build_draft_context import (
    BuildDraftSnapshotV1,
    BuildDraftContextRequestV1,
)
from application_state.agent_conversation.build_related_pages import (
    PagePointer,
    RelatedPagesSelection,
    RelatedPageRead,
    RelatedPageInclusion,
    RelatedPageClaim,
    project,
)
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_build_world_context import WorldDecisions, world_case
from tests.test_agent_build_jev_ordinary_harness import WriterWire
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    from tests.test_agent_build_jev_ordinary_harness import build_case

    return build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class PagesDecision(WorldDecisions):
    def __init__(self, operation="answer_from_sources"):
        super().__init__()
        self.operation = operation

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body = json.loads(request.content)
        data = response.json()
        for key, answer in data["answers"].items():
            if key == 'requested_work':
                chosen = getattr(self, 'requested_work', {'answer_from_sources': 'discuss', 'propose_build_insertion': 'write_current_page', 'prepare_build_image': 'prepare_image'}[self.operation])
                answer.update(choice=chosen, probabilities={v: float(v == chosen) for v in body['questions'][key]['criteria']})
            if key.startswith("related_page_"):
                chosen = (
                    "read"
                    if not getattr(self, 'skip_pages', False) and "Quarry Households" in body["questions"][key]["instructions"]
                    else "skip"
                )
                answer.update(
                    choice=chosen,
                    probabilities={v: float(v == chosen) for v in ("read", "skip")},
                )
                if getattr(self, "tie_choice", None) and "Quarry Households" in body["questions"][key]["instructions"]:
                    answer.update(choice=self.tie_choice, probabilities={"read": .5, "skip": .5})
        return httpx2.Response(200, request=request, json=data)


class PagesWriter(WriterWire):
    collaboration = None
    connected = False
    relationship = False
    invalid_quote = False

    async def handle_async_request(self, request):
        wire = json.loads(request.content)
        if wire["text"]["format"]["name"] == "build_image_direction":
            from tests.test_build_jev_image import ImageWire

            self.calls.append(request)
            return await ImageWire(purpose="illustration").handle_async_request(request)
        response = await super().handle_async_request(request)
        if wire["text"]["format"]["name"] == "build_document_proposal":
            return response
        if wire.get('stream') is True:
            terminal=json.loads(response.content.decode().strip().split('data: ')[-1])
            response=httpx.Response(200,request=request,json=terminal['response'])
        packet = json.loads(wire["input"])
        from application_state.agent_conversation.build_draft_answer import (
            source_claim_limitations,
        )

        required = sorted(source_claim_limitations(packet))
        if required:
            assert (
                "limitations MUST include these exact codes: " + json.dumps(required)
                in wire["instructions"]
            )
        if self.connected:
            assert "one short suggestion segment without" in wire["instructions"]
        row = packet["related_authored_pages"]["pages"][0] if packet["related_authored_pages"]["pages"] else {'read_id':None}
        if self.connected:
            self.collaboration = {
                "kind": "connected_page",
                "title": "Copper Workshop",
                "read_id": row["read_id"],
                "quote": "Copper House | Repair the lantern before dusk.",
                "person_label": None,
                "relationships": [],
                "instructions": "A practical workshop; keep future encounters unplayed.",
            }
        raw = json.dumps(
            {
                "answer_context_status": "creative_proposal"
                if self.connected
                else "authored_grounded",
                "answer_segments": [
                    {
                        "kind": "suggestion",
                        "text": "Here is the connected page for your review.",
                    }
                ]
                if self.connected
                else [
                    {
                        "kind": "related_page_claim",
                        "text": "The saved Quarry table lists Copper House with a lantern repair before dusk.",
                        "read_id": row["read_id"],
                    }
                ],
                "limitations": [],
                "requested_detail_gaps": [],
                **(
                    {"collaboration": self.collaboration}
                    if "collaboration_output_policy" in packet
                    else {}
                ),
            }
        )
        if self.relationship:
            from application_state.agent_conversation.build_draft_context import resolve_body_aliases
            primary = resolve_body_aliases(packet)["artifact_under_edit"]["sections"][0]
            self.collaboration = {"kind":"relationship","read_id":primary["read_id"],"quote":primary["text"],"source":{"label":"Proposed keeper","kind":"npc"},"target":{"label":"Proposed trader","kind":"npc"},"predicate":"works_with","label":"proposed past collaboration","context":"A proposed temporary past collaboration; author must review semantic support and identities."}
            raw = json.dumps({"answer_context_status":"creative_proposal","answer_segments":[{"kind":"suggestion","text":"Review the proposed relationship."}],"limitations":[],"requested_detail_gaps":[],"collaboration":self.collaboration})
        if packet.get("source_quote_binding_policy"):
            value = json.loads(raw)
            for segment in value["answer_segments"]:
                if segment["kind"] == "related_page_claim":
                    segment["supporting_quotes"] = [
                        "Unrelated wrong-page passage"
                        if self.invalid_quote
                        else "Copper House | Repair the lantern before dusk."
                    ]
            if getattr(self,"multi_related_quotes",False):
                value["answer_segments"][0]["supporting_quotes"]=["Copper House", "Repair the lantern before dusk."]
            raw = json.dumps(value)
            assert (
                "A valid ID from a different page is not support"
                in wire["instructions"]
            )
        if getattr(self, 'object_only', False):
            value = json.loads(raw)
            value.update(answer_segments=[], answer_context_status='discussion')
            raw = json.dumps(value)
        if getattr(self, 'bad_plan_schema', False):
            value = json.loads(raw)
            value['collaboration']['steps'][0]['kind'] = 'launch'
            raw = json.dumps(value)
        self.raw_output=raw
        data = response.json()
        data["output"][0]["content"][0]["text"] = raw
        if wire.get('stream') is True:
            events=[{'type':'response.output_text.delta','sequence_number':i+1,'item_id':'msg','output_index':0,'content_index':0,'delta':raw[i:i+1]} for i in range(len(raw))]
            events.append({'type':'response.completed','sequence_number':len(events)+1,'response':data})
            return httpx.Response(200,request=request,headers={'content-type':'text/event-stream'},content=''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode())
        return httpx.Response(200, request=request, json=data)


@pytest.fixture
def completed(build_case, monkeypatch, tmp_path, request):
    mode = getattr(request, "param", "answer_from_sources")
    operation = (
        "answer_from_sources"
        if mode
        in {
            "interrupted", "tied_read", "tied_skip", "retained_retry_failure", "retained_retry_dirty_failure", "retained_controller_failure",
            "typed_plan", "typed_plan_only", "typed_plan_empty", "typed_plan_bad_schema",
            "typed_questions",
            "connected_page", "connected_page_cap", "multi_related_quotes", "multi_related_quotes_cap",
            "relationship_review", "relationship_review_cap",
            "invalid_quote",
        }
        else mode
    )
    from tests.application_state.test_agent_conversation_postgres import _new

    (source, request, bootstrap), _ = world_case(build_case, monkeypatch)
    service = AgentConversationService()
    conversation = _new(service, "elderwyld")
    pointer = service.get_world_pointer("elderwyld")
    snap = BuildDraftSnapshotV1(
        world_id="elderwyld",
        document_id=source.record.document_id,
        registry_revision=source.loaded_revision,
        content_sha256=source.content_sha256,
        visibility="internal",
        draft_markdown="Current shop under edit.",
        draft_sha256=sha256(b"Current shop under edit.").hexdigest(),
        editor_sha256="b" * 64,
        draft_generation=1,
    )
    context = BuildDraftContextRequestV1(
        snapshot=snap,
        conversation_id=conversation.conversation_id,
        expected_pointer_revision=pointer.revision,
    )
    request = AgentTurnRequest.model_validate(
        {
            **request.model_dump(mode="json", by_alias=True),
            "turn_id": str(uuid4()),
            "client_work_state": "saved_dirty" if mode == "retained_retry_dirty_failure" else "saved_clean",
            "message": {
                "answer_from_sources": "Read the Quarry Households table and tell me Copper House’s task. Do not change the page.",
                "propose_build_insertion": "Use the Quarry Households table to prepare a proposed page addition about Copper House.",
                "prepare_build_image": "Read the Quarry Households table and prepare an illustration prompt for Copper House.",
            }[operation],
            "build_draft_context": context.model_dump(mode="json", by_alias=True),
        }
    )
    from dataclasses import replace

    bootstrap = replace(bootstrap, completed_discovery_query=request.message)
    page = PagePointer(
        world_id="elderwyld",
        document_id=uuid4(),
        registry_revision=9,
        title="Quarry Households",
        visibility="internal",
    )
    other = page.model_copy(update={"document_id": uuid4(), "title": "Hill Almanac"})
    body = "# Quarry Households\n\n| Household | Task |\n| --- | --- |\n| Copper House | Repair the lantern before dusk. |\n"
    from apps.live_control_server.services import build_related_pages as owner

    monkeypatch.setattr(
        owner,
        "discover",
        lambda request: [p.model_dump(mode="json") for p in (page, other)],
    )
    reads = []

    def materialize(pointer):
        assert pointer == page
        reads.append(pointer.document_id)
        return {
            **page.model_dump(mode="json"),
            "content_sha256": sha256(body.encode()).hexdigest(),
            "markdown": body,
        }

    monkeypatch.setattr(owner, "materialize", materialize)
    if operation != "answer_from_sources" or mode in {'typed_plan', 'typed_plan_only', 'typed_plan_empty', 'typed_plan_bad_schema', 'connected_page_cap', 'multi_related_quotes_cap', 'relationship_review_cap'}:
        from apps.live_control_server.models.build_document_proposal import (
            BuildWriteCapability,
        )
        from apps.live_control_server.services import (
            build_document_proposal as proposals,
        )
        from apps.live_control_server.routes.agent import _managed_world_root

        monkeypatch.setattr(proposals, "managed_world_data_root", _managed_world_root)
        monkeypatch.setattr(proposals, "get_world_container", lambda *_: object())
        monkeypatch.setattr(proposals, "_model", lambda: "gpt-6-luna")

        cap = BuildWriteCapability(
            idempotency_key=uuid4(),
            conversation_id=conversation.conversation_id,
            expected_pointer_revision=pointer.revision,
            draft_markdown=snap.draft_markdown,
            basis={
                **snap.saved_basis(),
                "draft_sha256": snap.draft_sha256,
                "caret": 0,
                "draft_generation": snap.draft_generation,
                "selection_generation": 0,
            },
        )
        request = request.model_copy(update={"build_write_capability": cap})
    writer = PagesWriter()
    writer.multi_related_quotes = mode in {"multi_related_quotes", "multi_related_quotes_cap"}
    writer.object_only = mode in {'typed_plan_only','typed_plan_empty','typed_plan_bad_schema'}
    writer.bad_plan_schema = mode == 'typed_plan_bad_schema'
    writer.connected = mode in {"connected_page", "connected_page_cap"}
    writer.invalid_quote = mode in {"invalid_quote", "retained_retry_failure", "retained_retry_dirty_failure"}
    writer.original_case = (source, request, bootstrap)
    if mode == "retained_controller_failure":
        def reject_related_selection(*args, **kwargs):
            raise ValueError("controlled_related_selection_rejection")
        from apps.live_control_server.services import build_related_pages as producer
        original_select_pages = producer.select_pages
        monkeypatch.setattr(producer, "select_pages", reject_related_selection)
        writer.restore_selection = lambda: monkeypatch.setattr(producer, "select_pages", original_select_pages)
    if mode in {'typed_plan', 'typed_plan_only', 'typed_plan_empty', 'typed_plan_bad_schema'}:
        writer.collaboration = {
            "kind": "plan",
            "objective": "Prepare a useful, author-reviewed hook-repair description without inventing played events.",
            "steps": [
                {"text": "Discuss Copper House’s actual task.", "kind": "discuss", "selected": True},
                {
                    "text": "Prepare a short hook-repair paragraph.",
                    "kind": "prepare_insertion",
                    "selected": False,
                },
            ],
        }
    elif mode == "typed_questions":
        writer.collaboration = {
            "kind": "questions",
            "questions": [
                {
                    "text": "Should the repair become a current job or a possible encounter?"
                }
            ],
        }
    writer.relationship = mode in {"relationship_review", "relationship_review_cap"}
    decisions = PagesDecision(operation=operation)
    decisions.tie_choice = {"tied_read":"read", "tied_skip":"skip"}.get(mode)
    decisions.skip_pages = mode == 'typed_plan_empty'
    decisions.requested_work = {'typed_plan': 'plan', 'typed_plan_only': 'plan', 'typed_plan_empty':'plan', 'typed_plan_bad_schema':'plan', 'typed_questions': 'clarify_request', 'connected_page': 'review_connected_page', 'connected_page_cap':'review_connected_page', 'relationship_review': 'review_relationship', 'relationship_review_cap':'review_relationship', 'invalid_quote': 'review_relationship'}.get(mode, {'answer_from_sources': 'discuss', 'propose_build_insertion': 'write_current_page', 'prepare_build_image': 'prepare_image'}[operation])
    harness = BuildJevHarness(
        world_context=True,
        named_citations=True,
        related_pages=True,
        decision_transport=decisions,
        writer_transport=writer,
        accounting=counter(),
    )
    from apps.live_control_server.services import build_construction_stream
    writer.progress_snapshots=[]
    monkeypatch.setattr(build_construction_stream,'observe',lambda value: writer.progress_snapshots.append((value,service.list_turns('elderwyld',conversation.conversation_id)[0].status)))
    decisions.timeout = mode == "interrupted"
    if mode == "interrupted":
        from apps.live_control_server.services.agent_turn_service import (
            AgentTurnServiceError,
        )

        with pytest.raises(AgentTurnServiceError):
            execute(
                (source, request, bootstrap),
                tmp_path,
                harness,
                operator_subject="local_operator",
            )
        turn = service.list_turns("elderwyld", conversation.conversation_id)[0]
        assert turn.status == "interrupted" and not reads
        return turn, service, page, body, reads, writer, decisions
    if mode in {"invalid_quote", "typed_plan_bad_schema", "retained_retry_failure", "retained_retry_dirty_failure", "retained_controller_failure"}:
        from apps.live_control_server.services.agent_turn_service import (
            AgentTurnServiceError,
        )

        with pytest.raises(AgentTurnServiceError):
            execute(
                (source, request, bootstrap),
                tmp_path,
                harness,
                operator_subject="local_operator",
            )
        turn = service.list_turns("elderwyld", conversation.conversation_id)[0]
        assert turn.status == "interrupted"
        assert bool(reads) == (mode != "retained_controller_failure")
        assert turn.completion is None
        return turn, service, page, body, reads, writer, decisions
    response = execute(
        (source, request, bootstrap),
        tmp_path,
        harness,
        operator_subject="local_operator",
    )
    writer.staged = harness.adapter._prepared_build_writer_projection
    assert response.answer.status == "ok"
    turn = service.list_turns("elderwyld", conversation.conversation_id)[0]
    return turn, service, page, body, reads, writer, decisions


def test_selected_saved_page_reaches_writer_and_reopens_exact_table(completed):
    turn, service, page, body, reads, writer, decisions = completed
    execution = turn.graph_context_execution
    choice = next(e for e in execution.events if isinstance(e, RelatedPagesSelection))
    captured = next(e for e in execution.events if isinstance(e, RelatedPageRead))
    assert choice.document_ids == [page.document_id]
    assert reads == [
        page.document_id,
        page.document_id,
    ]  # Parent and independent APP source-owner proof.
    first = json.loads(decisions.calls[0].content)
    assert body not in json.dumps(first)
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["related_authored_pages"]["pages"][0]["markdown"] == body
    assert json.dumps(packet).count("Repair the lantern before dusk.") == 1
    assert isinstance(turn.completion.answer_segments[0], RelatedPageClaim)
    included = [e for e in execution.events if isinstance(e, RelatedPageInclusion)]
    assert len(included) == 1 and included[0].read_ids == [captured.read_id]
    from apps.live_control_server.services.build_related_pages import open_page

    reopened = open_page(service, "elderwyld", turn.turn_id, captured.read_id)
    assert reopened["markdown"] == body and reopened["page"]["title"] == page.title
    assert (
        project(execution)["role"]
        == "saved_authored_reference_not_world_or_played_truth"
    )


def test_reconstructed_turn_rejects_foreign_unselected_or_changed_page(completed):
    turn, *_ = completed
    for field, value in (
        ("markdown", "invented replacement"),
        ("read_id", str(uuid4())),
    ):
        payload = turn.model_dump(mode="json", by_alias=True)
        row = next(
            e
            for e in payload["graph_context_execution"]["events"]
            if e["kind"] == "build_related_page_read_v1"
        )
        row[field] = value
        with pytest.raises(ValidationError):
            t.Turn.model_validate(payload)
    payload = turn.model_dump(mode="json", by_alias=True)
    row = next(
        e
        for e in payload["graph_context_execution"]["events"]
        if e["kind"] == "build_related_page_read_v1"
    )
    row["page"]["world_id"] = "foreign-world"
    with pytest.raises(ValidationError):
        t.Turn.model_validate(payload)


@pytest.mark.parametrize("change", ["revision", "world", "status", "digest", "title", "draft", "identity"])
def test_source_owner_refuses_changed_or_foreign_saved_page(
    tmp_path, monkeypatch, change
):
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages as owner

    monkeypatch.setattr(owner, "root", lambda: tmp_path)
    page = PagePointer(
        world_id="one",
        document_id=uuid4(),
        registry_revision=4,
        title="Households",
        visibility="internal",
    )
    body = "| Name | Work |\n| -- | -- |\n| Copper | Lantern |\n"
    record = SimpleNamespace(
        world_id="one",
        document_id=str(page.document_id),
        kind="worldbuilding_source",
        status="active",
        content_status="committed",
        revision=4,
        title="Households",
        visibility_state="internal",
        source_domain="worldbuilding",
        document_class="location",
        authority_state="draft",
        target_relpath=None,
    )
    snap = SimpleNamespace(
        record=record,
        markdown=body,
        content_sha256=sha256(body.encode()).hexdigest(),
        loaded_revision=4,
        file_exists=False,
    )
    monkeypatch.setattr(
        owner, "get_committed_page_snapshot", lambda root, doc: snap
    )
    assert owner.materialize(page)["markdown"] == body
    if change == "revision":
        record.revision = 5
    if change == "world":
        record.world_id = "two"
    if change == "status":
        record.status = "discarded"
    if change == "digest":
        snap.content_sha256 = "a" * 64
    if change == "title":
        record.title = "Changed name"
    if change == "draft":
        record.content_status = "draft"
    if change == "identity":
        record.document_id = str(uuid4())
    with pytest.raises(ValueError, match="no newer page was substituted"):
        owner.materialize(page)


def test_discovery_is_world_scoped_metadata_only(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages as owner

    monkeypatch.setattr(owner, "root", lambda: tmp_path)
    one = uuid4()
    primary = uuid4()

    def record(identity, world="one", **updates):
        return SimpleNamespace(
            **(
                dict(
                    document_id=str(identity),
                    world_id=world,
                    revision=4,
                    title="Households",
                    kind="worldbuilding_source",
                    status="active",
                    content_status="committed",
                    source_domain="worldbuilding",
                    document_class="location",
                    authority_state="draft",
                    visibility_state="internal",
                )
                | updates
            )
        )

    rows = [
        record(one),
        record(primary),
        record(uuid4(), world="two"),
        record(uuid4(), status="discarded"),
        record(uuid4(), content_status="draft"),
    ]
    monkeypatch.setattr(owner, "list_workspace_documents", lambda *args, **kwargs: rows)
    result = owner.discover(
        SimpleNamespace(
            owner_scope=SimpleNamespace(world_id="one"),
            primary_work=SimpleNamespace(object_id=str(primary)),
        )
    )
    assert len(result) == 1 and result[0]["document_id"] == str(one)
    assert set(result[0]) == {
        "world_id",
        "document_id",
        "registry_revision",
        "title",
        "visibility",
    }


@pytest.mark.parametrize(
    "completed", ["propose_build_insertion", "prepare_build_image"], indirect=True
)
def test_selected_related_body_is_in_the_actual_proposal_and_media_writer(completed):
    turn, service, page, body, reads, writer, decisions = completed
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["related_authored_pages"]["pages"][0]["markdown"] == body
    assert len(writer.calls) == 1 and reads == [page.document_id, page.document_id]
    included = [
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, RelatedPageInclusion)
    ]
    assert len(included) == 1 and included[0].read_ids
    assert turn.completion.schema_ in {
        "dmb_build_authoring_completion_v1",
        "dmb_build_image_preparation_completion_v1",
    }


@pytest.mark.parametrize(
    "completed", ["answer_from_sources", "interrupted"], indirect=True
)
def test_downgrade_refuses_to_discard_retained_related_page_completions(
    completed, application_state_dsn
):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(
                    RuntimeError, match="retained related-page authoring authority"
                ):
                    import_module(
                        "application_state.migrations.versions.20261025_0063_build_related_authored_pages"
                    ).downgrade()
    finally:
        engine.dispose()


def test_unfrozen_policy_cannot_admit_related_authoring_events():
    from types import SimpleNamespace
    from application_state.agent_conversation.build_related_pages import validate_events

    with pytest.raises(ValueError, match="frozen capability"):
        validate_events(
            SimpleNamespace(
                policy=SimpleNamespace(),
                events=[
                    RelatedPageInclusion(
                        event_id=uuid4(),
                        sequence=0,
                        provider_attempt_id=uuid4(),
                        envelope_sha256="a" * 64,
                        read_ids=[],
                    )
                ],
            )
        )


@pytest.mark.parametrize("completed", ["typed_plan", "typed_questions"], indirect=True)
def test_typed_workflow_survives_actual_writer_and_app_admission(completed):
    turn, service, *_rest, writer, decisions = completed
    assert isinstance(turn.completion, t.BuildIntentionalResponseCompletionV1)
    request = json.loads(writer.calls[0].content)
    packet = json.loads(request["input"])
    assert (
        packet["collaboration_output_policy"] == "typed_author_review_collaboration_v1"
    )
    assert request["text"]["format"]["name"] == ("build_intentional_plan_selection_answer_v1" if "plan_output_contract" in packet else "build_intentional_response_answer_v1") + "_quotes_v3"
    assert turn.completion.collaboration.model_dump(mode="json") == writer.collaboration
    reloaded = service.list_turns(turn.world_id, turn.conversation_id)[0]
    assert reloaded.completion == turn.completion
    from application_state.agent_conversation.source_writer_output import (
        validate_writer_format,
    )

    fmt = request["text"]["format"]
    with pytest.raises(ValueError, match="format") :
        validate_writer_format({**fmt, "name": "build_working_draft_answer_v1"}, packet)
    historical = turn.completion.model_dump(mode="json", by_alias=True)
    historical["schema"] = "dmb_build_related_page_completion_v1"
    with pytest.raises(ValidationError):
        t.BuildRelatedPageCompletionV1.model_validate(historical)


@pytest.mark.parametrize("completed", ["typed_plan", "typed_questions"], indirect=True)
def test_cannot_downgrade_retained_collaboration(completed, application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="Retained typed collaboration"):
                    import_module(
                        "application_state.migrations.versions.20261025_0065_typed_collaboration"
                    ).downgrade()
    finally:
        engine.dispose()


@pytest.mark.parametrize("completed", ["connected_page"], indirect=True)
def test_connected_review_reads_exact_producing_page_without_factual_claim(completed):
    turn, service, page, body, reads, writer, decisions = completed
    assert isinstance(turn.completion, t.BuildIntentionalResponseCompletionV1)
    proposal = turn.completion.collaboration
    assert proposal.kind == "connected_page"
    assert turn.completion.answer_segments[0].kind == "connective"
    from application_state.agent_conversation.collaboration import saved_excerpt

    rows = [
        e.model_dump(mode="json")
        for e in turn.graph_context_execution.events
        if isinstance(e, RelatedPageRead)
    ]
    origin = saved_excerpt(proposal, rows)
    assert origin["line_start"] == 5 and origin["line_end"] == 5
    assert (
        origin["selected_text"] == "| Copper House | Repair the lantern before dusk. |"
    )
    from apps.live_control_server.services.build_related_pages import open_page

    assert (
        open_page(service, turn.world_id, turn.turn_id, UUID(proposal.read_id))[
            "markdown"
        ]
        == body
    )
    assert (
        service.list_turns(turn.world_id, turn.conversation_id)[0].completion
        == turn.completion
    )
    payload = turn.model_dump(mode="json", by_alias=True)
    payload["completion"]["collaboration"]["quote"] = "Unread shop invented here"
    with pytest.raises(ValidationError):
        t.Turn.model_validate(payload)
    payload = turn.model_dump(mode="json", by_alias=True)
    payload["completion"]["schema"] = "dmb_build_collaboration_completion_v1"
    with pytest.raises(ValidationError):
        t.Turn.model_validate(payload)


@pytest.mark.parametrize("completed", ["connected_page"], indirect=True)
def test_connected_review_downgrade_refuses_retained_capability(
    completed, application_state_dsn
):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    engine = create_engine(
        application_state_dsn.replace("postgresql://", "postgresql+psycopg://")
    )
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(
                    RuntimeError, match="Retained connected-page reviews"
                ):
                    import_module(
                        "application_state.migrations.versions.20261025_0066_connected_page_review"
                    ).downgrade()
    finally:
        engine.dispose()


@pytest.mark.parametrize("completed", ["invalid_quote"], indirect=True)
def test_wrong_page_quote_is_rejected_through_sdk_and_app(completed):
    turn, service, *_ = completed
    assert turn.completion is None
    assert turn.failure_code == "plan_context_delivery_failure"
    traces = service.list_context_trace_attempts(
        world_id=turn.world_id, turn_id=turn.turn_id
    )
    failures = [
        o for trace in traces for o in trace.observations if o.kind == "failure"
    ]
    assert any(
        o.stage == "completion_validation" and o.exception_type == "ValueError"
        for o in failures
    )


@pytest.mark.parametrize("completed", ["relationship_review"], indirect=True)
def test_relationship_review_survives_actual_sdk_app_history_and_refuses_tampered_source(completed):
    turn, service, _page, _body, _reads, writer, _decisions = completed
    assert isinstance(turn.completion, t.BuildIntentionalResponseCompletionV1)
    assert turn.completion.collaboration.model_dump(mode="json") == writer.collaboration
    wire=json.loads(writer.calls[0].content)
    assert wire["text"]["format"]["name"] == ("build_intentional_plan_selection_answer_v1" if "plan_output_contract" in json.loads(wire["input"]) else "build_intentional_response_answer_v1") + "_quotes_v3_rel_v2"
    assert json.loads(wire["input"])["relationship_review_policy"] == "typed_saved_relationship_review_v1"
    loaded=service.list_turns(turn.world_id,turn.conversation_id)[0]
    assert loaded.completion == turn.completion
    assert type(turn).model_validate(loaded.model_dump(mode="json",by_alias=True)).completion == turn.completion
    # The support check is exact membership, not an entailment or identity decision.
    payload=turn.model_dump(mode="json",by_alias=True)
    payload["completion"]["collaboration"]["read_id"]=str(uuid4())
    with pytest.raises(ValidationError):type(turn).model_validate(payload)
    payload=turn.model_dump(mode="json",by_alias=True)
    payload["completion"]["collaboration"]["quote"]="Unread invented supporting passage"
    with pytest.raises(ValidationError):type(turn).model_validate(payload)


@pytest.mark.parametrize("completed", ["relationship_review"], indirect=True)
def test_relationship_review_downgrade_refuses_retained_turn(completed,application_state_dsn):
    from importlib import import_module
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    engine=create_engine(application_state_dsn.replace("postgresql://","postgresql+psycopg://"))
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="Retained relationship reviews"):
                    import_module(
                        "application_state.migrations.versions.20261025_0067_relationship_review"
                    ).downgrade()
    finally:
        engine.dispose()


@pytest.mark.parametrize("completed", ["typed_plan_only"], indirect=True)
def test_object_only_plan_seeds_existing_review_owner_with_exact_empty_text_digest(
    completed,
):
    from application_state.agent_conversation import work_plan as owner

    turn, service, *_ = completed
    assert turn.assistant_text == "" and turn.completion.answer_segments == []
    assert turn.completion.collaboration.kind == "plan"
    steps = [
        owner.Step(step_id=uuid4(), text=s.text, selected=s.selected, kind=s.kind)
        for s in turn.completion.collaboration.steps
    ]
    saved = owner.save(
        turn.world_id,
        turn.conversation_id,
        turn.turn_id,
        owner.ReviewV2(expected_revision=0, steps=steps, objective=turn.completion.collaboration.objective),
    )
    assert [row["selected"] for row in saved["steps"]] == [True, False]
    assert saved["source_answer_sha256"] == sha256(b"").hexdigest()
    assert (
        owner.read(turn.world_id, turn.conversation_id, turn.turn_id)["plan"]["steps"]
        == saved["steps"]
    )
    assert (
        service.list_turns(turn.world_id, turn.conversation_id)[0].assistant_text == ""
    )


@pytest.mark.parametrize("completed", ["typed_plan", "typed_plan_empty"], indirect=True)
def test_stream_plan_rows_precede_real_app_admission_and_exact_producer_reopens(
    completed,
):
    turn, service, _page, _body, reads, writer, _decisions = completed
    request = json.loads(writer.calls[0].content)
    assert (
        request["stream"] is True and request["text"]["format"]["type"] == "json_schema"
    )
    values = writer.progress_snapshots
    assert [len(p["steps"]) for p, _ in values] == [0, 1, 2]
    assert all(p["objective"] == turn.completion.collaboration.objective for p,_ in values)
    assert all(
        status == "running" and p["status"] == "building" for p, status in values
    )
    assert (
        values[-1][0]["steps"]
        == turn.completion.collaboration.model_dump(mode="json")["steps"]
    )
    auth = [
        e
        for e in turn.graph_context_execution.events
        if e.kind == "provider_attempt_authorized_v3" and e.provider == "openai"
    ]
    assert len(auth) == 1 and all(
        p["provider_attempt_id"] == str(auth[0].provider_attempt_id) for p, _ in values
    )
    assert all(
        p["durable_turn_id"] == str(turn.turn_id) and p["turn_attempt"] == 1
        for p, _ in values
    )
    assert len(writer.calls) == 1
    assert (
        service.list_turns(turn.world_id, turn.conversation_id)[0].completion
        == turn.completion
    )
    # Empty acquired related pages still use the closed-schema plan producer.
    if not json.loads(request["input"])["related_authored_pages"]["pages"]:
        assert reads == []


@pytest.mark.parametrize("completed", ["typed_plan_bad_schema"], indirect=True)
def test_stream_invalid_schema_final_is_captured_once_without_a_plan_or_retry(
    completed,
):
    turn, service, *_, writer, _decisions = completed
    assert (
        turn.status == "interrupted"
        and turn.completion is None
        and len(writer.calls) == 1
    )
    trace = service.list_context_trace_attempts(
        world_id=turn.world_id, turn_id=turn.turn_id
    )[0]
    value = trace.model_dump(mode="json")
    raw = [
        m["text"]
        for o in value["observations"]
        if o["kind"] == "context_snapshot"
        for m in o["materials"]
        if m["item_id"].startswith("unvalidated-provider-answer:")
    ]
    assert raw == [writer.raw_output]
    assert not any(p["status"] == "ready" for p, _ in writer.progress_snapshots)


@pytest.mark.parametrize("completed", ["typed_plan_empty"], indirect=True)
def test_actual_sdk_refuses_a_stream_flag_different_from_frozen_parent(completed):
    import asyncio
    from dataclasses import replace
    from generationengine import GenerationClient, TextFailed
    from generationengine.providers.openai_text import OpenAITextProvider
    from generationengine.text_dispatch import TextDispatchGate
    from apps.live_control_server.services import build_jev_writer as writer_owner

    *_, writer, _decisions = completed
    staged = writer.staged
    wrong = replace(staged, plan_stream=False)
    calls = []

    async def authorize(prepared):
        with pytest.raises(ValueError, match="exact parent projection"):
            writer_owner.prepared_view(prepared, wrong)
        return False

    async def record(_event):
        return True

    def transport(request):
        calls.append(request)
        raise AssertionError("Denied stream must not reach provider transport")

    async def run():
        provider = OpenAITextProvider(
            api_key="synthetic-only",
            dispatch_gate=TextDispatchGate(authorize, record),
            transport=httpx.MockTransport(transport),
        )
        client = GenerationClient(text_providers={"openai": provider})
        try:
            events = [
                event
                async for event in client.stream_text(writer_owner.text_request(staged))
            ]
            assert len(events) == 1 and isinstance(events[0], TextFailed)
            # SDK counts its guarded attempt; zero HTTP sends is the owning boundary.
            assert (
                str(events[0].failure.code.value)
                == "ATTEMPT_EVIDENCE_PERSISTENCE_FAILED"
            )
        finally:
            await client.aclose()

    asyncio.run(run())
    assert calls == []


@pytest.mark.parametrize('completed',['typed_plan_only'],indirect=True)
def test_objective_contract_producer_and_installed_constraints_reject_tampering(completed,application_state_dsn):
    from copy import deepcopy
    import psycopg
    from psycopg.types.json import Jsonb
    turn,service,*_=completed
    original=turn.model_dump(mode='json',by_alias=True)
    marker=next(e for e in original['graph_context_execution']['events'] if e['kind']=='build_plan_output_contract_v2')
    assert turn.completion.schema_=='dmb_build_intentional_response_completion_v3'
    for field in ('selection_sha256','working_snapshot_sha256','destination_capability_sha256','plan_schema_sha256'):
        changed=deepcopy(original)
        next(e for e in changed['graph_context_execution']['events'] if e['kind']==marker['kind'])[field]='0'*64
        with pytest.raises(ValueError):t.Turn.model_validate(changed)
    changed=deepcopy(original)
    changed['completion']['schema']='dmb_build_intentional_response_completion_v1'
    with pytest.raises(ValueError):t.Turn.model_validate(changed)
    with psycopg.connect(application_state_dsn) as conn:
        stored=conn.execute('SELECT completion FROM agent.turn WHERE turn_id=%s',(turn.turn_id,)).fetchone()[0]
        for value in (None,'', '   '):
            changed=deepcopy(stored)
            if value is None:changed['collaboration'].pop('objective')
            else:changed['collaboration']['objective']=value
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():conn.execute('UPDATE agent.turn SET completion=%s WHERE turn_id=%s',(Jsonb(changed),turn.turn_id))
        for value in ('missing', None, 'false', 0, 1, [], {}):
            changed=deepcopy(stored)
            row=changed['collaboration']['steps'][1]
            if value == 'missing': row.pop('selected')
            else: row['selected']=value
            with pytest.raises(ValueError):
                t.Turn.model_validate({**original,'completion':changed})
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction(): conn.execute('UPDATE agent.turn SET completion=%s WHERE turn_id=%s',(Jsonb(changed),turn.turn_id))
        changed=deepcopy(stored)
        changed['collaboration']['steps'][1]['unexpected']=True
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction(): conn.execute('UPDATE agent.turn SET completion=%s WHERE turn_id=%s',(Jsonb(changed),turn.turn_id))
        changed=deepcopy(original['graph_context_execution'])
        event=next(e for e in changed['events'] if e['kind']==marker['kind'])
        event['kind']='build_plan_output_contract_v1';event['policy']='typed_plan_objective_v1'
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction(): conn.execute('UPDATE agent.turn SET graph_context_execution=%s WHERE turn_id=%s',(Jsonb(changed),turn.turn_id))
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from importlib import import_module
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    try:
        with engine.begin() as conn,Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError,match='recovery forward'):
                import_module('application_state.migrations.versions.20261026_0075_plan_proposal_selection').downgrade()
    finally:engine.dispose()


@pytest.mark.parametrize('completed',['typed_questions'],indirect=True)
def test_selection_migration_preserves_retained_rows_and_completed_readback(completed,application_state_dsn):
    import psycopg
    from sqlalchemy import create_engine
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from importlib import import_module
    turn,service,*_=completed
    before=service.list_turns(turn.world_id,turn.conversation_id)[0].model_dump_json(by_alias=True)
    def rows():
        with psycopg.connect(application_state_dsn) as conn:
            tables=conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='agent' ORDER BY tablename").fetchall()
            return {name:conn.execute('SELECT row_to_json(t)::text FROM agent.'+name+' t ORDER BY row_to_json(t)::text').fetchall() for name, in tables}
    retained=rows()
    engine=create_engine(application_state_dsn.replace('postgresql://','postgresql+psycopg://'))
    migration=import_module('application_state.migrations.versions.20261026_0075_plan_proposal_selection')
    try:
        with engine.begin() as conn,Operations.context(MigrationContext.configure(conn)): migration.downgrade()
        with engine.begin() as conn,Operations.context(MigrationContext.configure(conn)): migration.upgrade()
    finally:engine.dispose()
    assert rows()==retained
    assert service.list_turns(turn.world_id,turn.conversation_id)[0].model_dump_json(by_alias=True)==before


def test_new_preparation_refuses_retained_objective_contract_before_dispatch():
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter,AgentTurnServiceError
    from application_state.agent_conversation import plan_objective
    event=t.BuildPlanOutputContractV1(kind='build_plan_output_contract_v1',event_id=uuid4(),sequence=0,
        policy=plan_objective.POLICY,selection_event_id=uuid4(),selection_sha256='a'*64,draft_record_id=uuid4(),
        working_snapshot_sha256='b'*64,destination_capability_sha256='c'*64,plan_schema_sha256=plan_objective.schema_digest())
    adapter=SimpleNamespace(_broker_execution=lambda:SimpleNamespace(events=[event]))
    with pytest.raises(AgentTurnServiceError,match='predates explicit step selection'):
        _PolicyExecutionAdapter._with_plan_output_contract(adapter,object())


@pytest.mark.parametrize('completed',['multi_related_quotes','multi_related_quotes_cap'],indirect=True)
def test_multiple_exact_related_witnesses_complete_through_guarded_sdk_app(completed):
    turn,service,_page,_body,_reads,writer,_decisions=completed
    wire=json.loads(writer.calls[0].content);packet=json.loads(wire['input'])
    assert packet['related_page_quote_policy']=='same_read_multiple_quotes_v1'
    assert wire['text']['format']['name'].endswith('_quotes_v3')
    assert len(json.loads(writer.raw_output)['answer_segments'][0]['supporting_quotes'])==2
    claims=[segment for segment in turn.completion.answer_segments if isinstance(segment,RelatedPageClaim)]
    assert len(claims)==1
    assert str(claims[0].read_id)==json.loads(writer.raw_output)["answer_segments"][0]["read_id"]
    assert service.inspect_turn(world_id=turn.world_id,turn_id=turn.turn_id)==turn
    from application_state.agent_conversation.source_writer_output import validate_writer_format
    validate_writer_format(wire['text']['format'],packet)


@pytest.mark.parametrize("completed", ["tied_read", "tied_skip"], indirect=True)
def test_optional_related_page_tie_reaches_writer_with_exact_read(completed):
    turn, service, page, body, reads, writer, decisions = completed
    assert turn.status == "completed"
    selection = next(e for e in turn.graph_context_execution.events if isinstance(e, RelatedPagesSelection))
    assert selection.document_ids == [page.document_id]
    assert reads == [page.document_id, page.document_id]
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["related_authored_pages"]["pages"][0]["markdown"] == body
    assert isinstance(turn.completion.answer_segments[0], RelatedPageClaim)


@pytest.mark.parametrize("selected,probabilities", [
    ("read", {"read": .2, "skip": .8}),
    ("read", {"read": float("nan"), "skip": .5}),
    ("read", {"read": .9, "skip": .9}),
    ("read", {"read": .5, "other": .5}),
])
def test_optional_read_tie_rule_still_refuses_invalid_votes(selected, probabilities):
    from types import SimpleNamespace
    from application_state.agent_conversation.build_related_pages import question_text, should_read_page
    page = PagePointer(world_id="elderwyld", document_id=uuid4(), registry_revision=1, title="Edge - Location", visibility="internal")
    question = {"instructions": question_text(page), "criteria": {"read": {}, "skip": {}}}
    with pytest.raises(ValueError, match="Unresolved related page choice"):
        should_read_page(page, question, SimpleNamespace(selected=selected, probabilities=probabilities))


@pytest.mark.parametrize("completed", ["retained_retry_failure", "retained_retry_dirty_failure"], indirect=True)
@pytest.mark.parametrize("ancestor", ["root", "ordinary", "retained"])
def test_retained_discussion_retry_uses_exact_capture_and_ordinary_dispatch(completed, tmp_path, ancestor):
    from application_state.agent_conversation import retry
    from application_state.agent_conversation.build_draft_context import context_record
    turn, service, _, _, _, writer, _ = completed
    source, original, bootstrap = writer.original_case
    if ancestor != "root":
        from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
        first = retry.read_discussion_retry_input(turn.world_id, turn.conversation_id, turn.turn_id, turn.revision)
        original = AgentTurnRequest.model_validate({**original.model_dump(mode="json", by_alias=True),
            "client_thread_id": str(uuid4()), "turn_id": str(uuid4()),
            "retry_of": {"turn_id": str(turn.turn_id), "revision": turn.revision,
                **({"retained_snapshot_sha256":first["snapshot_sha256"]} if ancestor == "retained" else {})},
            "build_draft_context": {"snapshot":first["snapshot"], "conversation_id":str(turn.conversation_id), "expected_pointer_revision":first["pointer_revision"]}})
        failing_writer = PagesWriter()
        failing_writer.invalid_quote = True
        failing = BuildJevHarness(world_context=True,named_citations=True,related_pages=True,decision_transport=PagesDecision(),writer_transport=failing_writer,accounting=counter())
        with pytest.raises(AgentTurnServiceError):
            execute((source, original, bootstrap), tmp_path, failing, operator_subject="local_operator")
        turn = service.list_turns(turn.world_id, turn.conversation_id)[-1]
    captured = context_record(turn.graph_context_execution).record.snapshot
    before = service.list_turns(turn.world_id, turn.conversation_id)
    prepared = retry.read_discussion_retry_input(turn.world_id, turn.conversation_id, turn.turn_id, turn.revision)
    assert prepared == retry.read_discussion_retry_input(turn.world_id, turn.conversation_id, turn.turn_id, turn.revision)
    assert service.list_turns(turn.world_id, turn.conversation_id) == before
    assert prepared["client_work_state"] == original.client_work_state
    assert prepared["snapshot"] == captured.model_dump(mode="json", by_alias=True)
    request = AgentTurnRequest.model_validate({
        **original.model_dump(mode="json", by_alias=True),
        "client_thread_id": str(uuid4()), "turn_id": str(uuid4()),
        "retry_of": {"turn_id": str(turn.turn_id), "revision": turn.revision, "retained_snapshot_sha256": prepared["snapshot_sha256"]},
        "build_draft_context": {"snapshot": prepared["snapshot"], "conversation_id": str(turn.conversation_id), "expected_pointer_revision": prepared["pointer_revision"]},
    })
    decisions, fresh_writer = PagesDecision(), PagesWriter()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True, decision_transport=decisions, writer_transport=fresh_writer, accounting=counter())
    result = execute((source, request, bootstrap), tmp_path, harness, operator_subject="local_operator")
    assert result.answer.status == "ok"
    assert len(fresh_writer.calls) == 1
    assert retry.read_context(turn.world_id, turn.conversation_id, [turn.turn_id])["turns"][0]["context"]["reason"] == "retried"
    # Exact delivery replay uses the existing accepted turn, never another model call.
    execute((source, request, bootstrap), tmp_path, harness, operator_subject="local_operator")
    assert len(fresh_writer.calls) == 1


@pytest.mark.parametrize("completed", ["retained_retry_failure"], indirect=True)
@pytest.mark.parametrize("change", ["draft", "marker", "pointer", "question", "document", "state", "capability"])
def test_retained_discussion_retry_refuses_drift_before_provider(completed, tmp_path, change):
    from application_state.agent_conversation import retry
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    turn, service, _, _, _, writer, _ = completed
    source, original, bootstrap = writer.original_case
    prepared = retry.read_discussion_retry_input(turn.world_id, turn.conversation_id, turn.turn_id, turn.revision)
    data = {**original.model_dump(mode="json", by_alias=True),
        "client_thread_id": str(uuid4()), "turn_id": str(uuid4()),
        "retry_of": {"turn_id": str(turn.turn_id), "revision": turn.revision, "retained_snapshot_sha256": prepared["snapshot_sha256"]},
        "build_draft_context": {"snapshot": prepared["snapshot"], "conversation_id": str(turn.conversation_id), "expected_pointer_revision": prepared["pointer_revision"]}}
    if change == "draft":
        data["build_draft_context"]["snapshot"]["draft_markdown"] = "A substituted current editor"
        data["build_draft_context"]["snapshot"]["draft_sha256"] = sha256(b"A substituted current editor").hexdigest()
    elif change == "capability":
        snap = data["build_draft_context"]["snapshot"]
        data["build_write_capability"] = {"idempotency_key":str(uuid4()), "conversation_id":str(turn.conversation_id),
            "expected_pointer_revision":prepared["pointer_revision"], "draft_markdown":snap["draft_markdown"],
            "basis":{**{k:snap[k] for k in ("world_id","document_id","content_sha256","visibility","draft_sha256","editor_sha256","draft_generation")},
                "registry_revision":snap["registry_revision"], "caret":0, "selection_generation":0}}
    elif change == "state": data["client_work_state"] = "saved_dirty" if original.client_work_state == "saved_clean" else "saved_clean"
    elif change == "marker": data["retry_of"]["retained_snapshot_sha256"] = "f" * 64
    elif change == "pointer": data["build_draft_context"]["expected_pointer_revision"] += 1
    elif change == "question": data["message"] = "A different question"
    elif change == "document": data["primary_work"]["object_id"] = str(uuid4())
    decisions, fresh_writer = PagesDecision(), PagesWriter()
    harness = BuildJevHarness(world_context=True, named_citations=True, related_pages=True, decision_transport=decisions, writer_transport=fresh_writer, accounting=counter())
    with pytest.raises((AgentTurnServiceError, ValueError, retry.RetryUnavailableError)):
        request = AgentTurnRequest.model_validate(data)
        execute((source, request, bootstrap), tmp_path, harness, operator_subject="local_operator")
    assert not decisions.calls and not fresh_writer.calls
    assert len(service.list_turns(turn.world_id, turn.conversation_id)) == 1


def test_ordinary_retry_reference_serialization_keeps_immutable_fingerprint():
    reference = t.RetryTurnReference(turn_id=uuid4(), revision=4)
    assert reference.model_dump(mode="json") == {"turn_id": str(reference.turn_id), "revision": 4}
    retained = reference.model_copy(update={"retained_snapshot_sha256": "a" * 64})
    assert retained.model_dump(mode="json")["retained_snapshot_sha256"] == "a" * 64


@pytest.mark.parametrize("completed", ["interrupted"], indirect=True)
def test_retained_discussion_preparation_preserves_unknown_outcome_refusal(completed):
    from application_state.agent_conversation import retry
    turn, *_ = completed
    with pytest.raises(retry.RetryUnavailableError, match="outcome recovery"):
        retry.read_discussion_retry_input(turn.world_id, turn.conversation_id, turn.turn_id, turn.revision)


@pytest.mark.parametrize("completed", ["retained_controller_failure"], indirect=True)
def test_controller_rejection_keeps_original_draft_for_read_only_retry(completed, tmp_path):
    from application_state.agent_conversation import retry
    turn, _, _, _, _, writer, _ = completed
    events = turn.graph_context_execution.events
    capture = next(e for e in events if isinstance(e, t.BuildDraftContextCapturedV1))
    selected = next(e for e in events if isinstance(e, t.BuildRequestedWorkResolutionV1))
    assert capture.sequence < selected.sequence
    prepared = retry.read_discussion_retry_input(turn.world_id, turn.conversation_id, turn.turn_id, turn.revision)
    source, original, bootstrap = writer.original_case
    assert prepared["snapshot"] == original.build_draft_context.snapshot.model_dump(mode="json", by_alias=True)
    writer.restore_selection()
    request = AgentTurnRequest.model_validate({**original.model_dump(mode="json", by_alias=True),
        "turn_id":str(uuid4()), "client_thread_id":str(uuid4()),
        "retry_of":{"turn_id":str(turn.turn_id),"revision":turn.revision,"retained_snapshot_sha256":prepared["snapshot_sha256"]}})
    fresh = PagesWriter()
    harness = BuildJevHarness(world_context=True,named_citations=True,related_pages=True,decision_transport=PagesDecision(),writer_transport=fresh,accounting=counter())
    assert execute((source,request,bootstrap),tmp_path,harness,operator_subject="local_operator").answer.status == "ok"
    assert len(fresh.calls) == 1

@pytest.mark.parametrize("completed", ["retained_retry_failure"], indirect=True)
def test_missing_historical_capture_remains_unavailable_without_substitution(completed, monkeypatch):
    from application_state.agent_conversation import retry
    turn, *_ = completed
    historical = turn.model_copy(update={"graph_context_execution":turn.graph_context_execution.model_copy(update={
        "events":[e for e in turn.graph_context_execution.events if not isinstance(e,t.BuildDraftContextCapturedV1)]})})
    original = retry.repo.get_turn
    monkeypatch.setattr(retry.repo,"get_turn",lambda conn,world,tid:historical if tid == turn.turn_id else original(conn,world,tid))
    with pytest.raises(retry.RetryUnavailableError,match="original working draft"):
        retry.read_discussion_retry_input(turn.world_id,turn.conversation_id,turn.turn_id,turn.revision)
