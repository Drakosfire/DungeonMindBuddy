"""Related saved pages through the actual SDK/APP writer proof boundaries."""

from hashlib import sha256
from uuid import uuid4
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
            if key.startswith("related_page_"):
                chosen = (
                    "read"
                    if "Quarry Households" in body["questions"][key]["instructions"]
                    else "skip"
                )
                answer.update(
                    choice=chosen,
                    probabilities={v: float(v == chosen) for v in ("read", "skip")},
                )
        return httpx2.Response(200, request=request, json=data)


class PagesWriter(WriterWire):
    async def handle_async_request(self, request):
        wire = json.loads(request.content)
        if wire["text"]["format"]["name"] == "build_image_direction":
            from tests.test_build_jev_image import ImageWire

            self.calls.append(request)
            return await ImageWire(purpose="illustration").handle_async_request(request)
        response = await super().handle_async_request(request)
        if wire["text"]["format"]["name"] == "build_document_proposal":
            return response
        packet = json.loads(wire["input"])
        row = packet["related_authored_pages"]["pages"][0]
        raw = json.dumps(
            {
                "answer_context_status": "authored_grounded",
                "answer_segments": [
                    {
                        "kind": "related_page_claim",
                        "text": "The saved Quarry table lists Copper House with a lantern repair before dusk.",
                        "read_id": row["read_id"],
                    }
                ],
                "limitations": [],
                "requested_detail_gaps": [],
            }
        )
        data = response.json()
        data["output"][0]["content"][0]["text"] = raw
        return httpx.Response(200, request=request, json=data)


@pytest.fixture
def completed(build_case, monkeypatch, tmp_path, request):
    mode = getattr(request, "param", "answer_from_sources")
    operation = "answer_from_sources" if mode == "interrupted" else mode
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
    if operation != "answer_from_sources":
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
        from apps.live_control_server.services import build_image_writer

        monkeypatch.setattr(build_image_writer, "_model", lambda: "gpt-6-luna")
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
    decisions = PagesDecision(operation=operation)
    harness = BuildJevHarness(
        world_context=True,
        named_citations=True,
        related_pages=True,
        decision_transport=decisions,
        writer_transport=writer,
        accounting=counter(),
    )
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
    response = execute(
        (source, request, bootstrap),
        tmp_path,
        harness,
        operator_subject="local_operator",
    )
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


@pytest.mark.parametrize("change", ["revision", "world", "status", "digest", "title"])
def test_source_owner_refuses_changed_or_foreign_saved_page(
    tmp_path, monkeypatch, change
):
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages as owner

    monkeypatch.setattr(owner, "root", lambda: tmp_path)
    monkeypatch.setattr(owner, "artifact_data_root", lambda root: tmp_path)
    page = PagePointer(
        world_id="one",
        document_id=uuid4(),
        registry_revision=4,
        title="Households",
        visibility="internal",
    )
    body = "| Name | Work |\n| -- | -- |\n| Copper | Lantern |\n"
    (tmp_path / "source.md").write_text(body)
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
        target_relpath="source.md",
    )
    snap = SimpleNamespace(
        record=record,
        markdown=body,
        content_sha256=sha256(body.encode()).hexdigest(),
        loaded_revision=4,
        file_exists=True,
    )
    monkeypatch.setattr(
        owner, "get_workspace_document_snapshot", lambda root, doc: snap
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
