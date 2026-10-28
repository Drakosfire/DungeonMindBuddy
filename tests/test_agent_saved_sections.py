"""Ordinary SDK→APP completion→fresh authenticated historical authored read."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as ledger
from apps.live_control_server.routes import agent
from apps.live_control_server.services.agent_saved_sections import (
    saved_section_targets,
    open_saved_section,
)
from apps.live_control_server.services.agent_source_passages import (
    SourcePassageOpenError,
)
from apps.live_control_server.services.agent_turn_service import (
    project_plan_turn_context,
)
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute
from tests.test_build_cited_writer_output import SavedThenGraphWire, OutputWire
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture(params=["saved_only", "saved", "intentional_v3"])
def completed(build_case, monkeypatch, tmp_path, request):
    if request.param == "intentional_v3":
        from tests.test_build_claim_local_citations import make_mixed_answer

        turn, *_ = make_mixed_answer(
            build_case, monkeypatch, tmp_path, mode="multi_related_quotes_cap"
        )
        assert turn.completion.schema_ == "dmb_build_intentional_response_completion_v3"
        return turn
    # These two cases exercise retained pre-primary-context completion receipts.
    # Freeze their original SDK budget explicitly rather than letting the current
    # primary-page policy silently change their writer input contract.
    current_budget = BuildJevHarness.budget

    def historical_budget(*args, **kwargs):
        budget = current_budget(*args, **kwargs)
        budget["buildJevActions"].pop("primary_work_context_policy", None)
        budget["buildJevActions"].pop("writer_status_policy", None)
        return budget

    monkeypatch.setattr(BuildJevHarness, "budget", staticmethod(historical_budget))
    case, _ = ordinary_case(build_case, monkeypatch)
    execute(
        case,
        tmp_path,
        BuildJevHarness(
            decision_transport=SavedThenGraphWire(),
            writer_transport=OutputWire(request.param),
            accounting=counter(),
        ),
    )
    service = AgentConversationService()
    pointer = service.get_world_pointer("elderwyld")
    turn = service.list_turns("elderwyld", pointer.active_conversation_id)[0]
    assert turn.status == "completed"
    return turn


def test_exact_projection_fresh_read_and_reopen_without_current_source(
    completed, monkeypatch
):
    turn = completed
    targets = saved_section_targets(turn)
    assert len(targets) == 1
    projected = project_plan_turn_context(turn, delivery_replay=True)
    assert projected.saved_source_sections == targets
    target = targets[0]
    # A current document lookup is neither needed nor allowed after edits/deletion.
    monkeypatch.setattr(
        agent,
        "_historical_work_resolver",
        lambda *_a, **_k: pytest.fail("Current document lookup"),
    )
    opened = open_saved_section(
        world_id=turn.world_id,
        turn_id=turn.turn_id,
        segment_index=target.segment_index,
        section_event_id=target.section_event_id,
    )
    assert opened.target == target
    read = next(
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, ledger.ValidatedBuildSectionReadV1)
        and e.event_id == target.section_event_id
    )
    assert opened.content == read.text
    assert target.source_class == "saved_authored_source_not_played_truth"
    fresh = AgentConversationService().inspect_turn(
        world_id=turn.world_id, turn_id=turn.turn_id
    )
    assert saved_section_targets(fresh) == targets
    assert "text" not in target.model_dump() and "content" not in target.model_dump()


@pytest.mark.parametrize("selector", ["world", "turn", "event", "segment"])
def test_foreign_selectors_never_find_another_section(completed, selector):
    target = saved_section_targets(completed)[0]
    args = dict(
        world_id=completed.world_id,
        turn_id=completed.turn_id,
        segment_index=target.segment_index,
        section_event_id=target.section_event_id,
    )
    if selector == "world":
        args["world_id"] = "foreign-world"
    elif selector == "turn":
        args["turn_id"] = uuid4()
    elif selector == "event":
        args["section_event_id"] = uuid4()
    else:
        args["segment_index"] = 127
    with pytest.raises(Exception):
        open_saved_section(**args)


@pytest.mark.parametrize(
    "mutation",
    ["text", "basis", "visibility", "binding_hash", "inclusion", "unfinished"],
)
def test_mutated_in_memory_records_are_revalidated(completed, mutation):
    turn = deepcopy(completed)
    read = next(
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, ledger.ValidatedBuildSectionReadV1)
    )
    binding = next(
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, ledger.BuildSectionAnswerBindingV1)
    )
    if mutation == "text":
        read.text = "newer replacement"
    elif mutation == "basis":
        read.source_basis.world_id = "foreign-world"
    elif mutation == "visibility":
        read.source_basis.visibility = "public"
    elif mutation == "binding_hash":
        binding.bindings[0].text_sha256 = "f" * 64
    elif mutation == "inclusion":
        inclusion = next(
            e
            for e in turn.graph_context_execution.events
            if isinstance(e, ledger.BuildSectionProviderInclusionV1)
        )
        inclusion.section_event_ids = [uuid4()]
    else:
        turn.status = "running"
    if mutation == "unfinished":
        assert saved_section_targets(turn) == []
    else:
        with pytest.raises((ValueError, KeyError)):
            saved_section_targets(turn)


def test_missing_binding_cannot_be_recovered_from_current_source(completed):
    turn = deepcopy(completed)
    turn.graph_context_execution.events = [
        e
        for e in turn.graph_context_execution.events
        if not isinstance(e, ledger.BuildSectionAnswerBindingV1)
    ]
    with pytest.raises(ValueError):
        saved_section_targets(turn)


def test_authenticated_http_selector_and_error_contract(completed, monkeypatch):
    target = saved_section_targets(completed)[0]
    monkeypatch.setattr(
        agent, "enforce_native_graph_gm", lambda _: SimpleNamespace(subject="operator")
    )
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")
    path = f"/api/live/agent/worlds/{completed.world_id}/conversation/turns/{completed.turn_id}/saved-sections/{target.segment_index}/{target.section_event_id}"
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert response.json()["target"] == target.model_dump(
            mode="json", by_alias=True
        )
        assert client.get(path + "?path=other").status_code == 422
        assert (
            client.get(
                path.replace(str(target.section_event_id), str(uuid4()))
            ).status_code
            == 404
        )
        monkeypatch.setattr(
            agent,
            "enforce_native_graph_gm",
            lambda _: (_ for _ in ()).throw(HTTPException(status_code=403)),
        )
        assert client.get(path).status_code == 403


def test_bad_selector_before_any_app_read():
    with pytest.raises(SourcePassageOpenError) as e:
        open_saved_section(
            world_id="a", turn_id=uuid4(), segment_index=True, section_event_id=uuid4()
        )
    assert e.value.status_code == 422


def test_named_projection_deduplicates_history_metadata_without_changing_targets(completed, monkeypatch):
    from apps.live_control_server.services import source_artifact_registry as registry
    from apps.live_control_server.services.agent_source_names import source_names_for_turns
    from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact, build_worldbuilding_source_artifact_id
    basis = completed.graph_context_receipt.source_basis
    identity = build_worldbuilding_source_artifact_id(workspace_document_id=basis.document_id,
        workspace_document_revision=basis.registry_revision, content_sha256=basis.content_sha256)
    artifact = GraphMemorySourceArtifact(source_artifact_id=identity, source_domain="worldbuilding",
        world_id=basis.world_id, uri="repo://frozen/source.md", content_sha256=basis.content_sha256,
        workspace_document_id=basis.document_id, workspace_document_revision=basis.registry_revision,
        visibility_state=basis.visibility, lineage={"source_name": "Original committed source name"})
    calls = []
    def batch(root, identities):
        calls.append(identities)
        return {identity: artifact}
    monkeypatch.setattr(registry, "get_source_artifacts", batch)
    targets = saved_section_targets(completed)
    names = source_names_for_turns([completed, completed])
    assert calls == [{identity}]
    assert len([label for label in names if label.get("kind") == "saved_build_source"]) == 1
    projected = project_plan_turn_context(completed, delivery_replay=True, source_names=names)
    assert projected.saved_source_name == "Original committed source name"
    assert projected.saved_source_sections == targets
    assert calls == [{identity}]
    opened = open_saved_section(world_id=completed.world_id, turn_id=completed.turn_id,
        segment_index=targets[0].segment_index, section_event_id=targets[0].section_event_id)
    assert opened.target == targets[0]
    missing = project_plan_turn_context(completed, delivery_replay=True, source_names=[])
    assert missing.saved_source_name is None and missing.saved_source_sections == targets


def test_foreign_turn_world_never_resolves_saved_name(completed, monkeypatch):
    from apps.live_control_server.services import source_artifact_registry as registry
    from apps.live_control_server.services.agent_source_names import source_names_for_turns
    monkeypatch.setattr(registry, "get_source_artifacts", lambda *_: pytest.fail("Foreign World metadata read"))
    assert source_names_for_turns([completed.model_copy(update={"world_id": "foreign"})]) == []
