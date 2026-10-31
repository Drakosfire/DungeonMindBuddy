"""Producer → APP reload → authenticated receipt-bound historical read; no inference."""
from application_state.world_catalog.service import get_world
from tests.application_state.world_catalog_fixtures import store_world

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from apps.live_control_server.routes import agent
from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from apps.live_control_server.services.agent_source_passages import (
    open_source_passage,
    SourcePassageOpenError,
)
from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult
from tests.test_agent_build_source_passage_writer import (
    build_case as _build_case,
    stage,
    answer,
    fresh,
    WriterWire,
    invoke,
)


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture(params=["graph", "intentional"])
def completed(build_case, monkeypatch, tmp_path, request):
    if request.param == "intentional":
        monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "synthetic-only")
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-only")
        import json
        from application_state.agent_conversation.types import (
            BuildIntentionalResponseCompletionV1,
        )
        from tests.test_build_layout_quote_witnesses import completed_layout

        turn, _, _, _, _, transport, _ = completed_layout.__wrapped__(
            build_case, monkeypatch, tmp_path, SimpleNamespace(param="native")
        )
        assert isinstance(turn.completion, BuildIntentionalResponseCompletionV1)
        packet = json.loads(json.loads(transport.calls[0].content)["input"])
        text = packet["opened_passages"][0]["text"]
    else:
        adapter, projection, _, text = stage(build_case, monkeypatch)
        adapter.complete_build_writer(
            invoke(adapter, projection, WriterWire(adapter, text=answer(projection)))
        )
        turn = fresh(adapter)
    receipt = turn.completion.source_citations[0].receipt
    result = WorldGraphSourceAnchorReadResult.model_validate(
        {
            "outcome": "enough",
            "snapshot": {
                "worldId": "native-build-world",
                "campaignId": "",
                "scopeMode": "world",
                "focus": {"kind": "none", "sessionId": None},
                "admissibility": "gm",
                "revisionId": "native-rev-3",
                "headRevisionId": "newer-head",
                "isHead": False,
            },
            "anchorId": receipt.anchor_id,
            "evidenceRefId": receipt.evidence_ref_id,
            "sourceArtifactId": receipt.source_artifact_id,
            "content": text,
            "contentSha256": "a" * 64,
            "lineStart": receipt.line_start,
            "lineEnd": receipt.line_end,
            "truncated": False,
        }
    )
    opened = direct.ResolvedSourceAnchorReadV2(
        result=result,
        source_revision_id=receipt.source_revision_id,
        source_revision_sha256="a" * 64,
        evidence_ref_id=receipt.evidence_ref_id,
        source_artifact_id=receipt.source_artifact_id,
        source_span_ref_id="span-one",
        locator_kind="source_span",
        locator_identity="span-one",
        graph_revision="native-rev-3",
    )
    calls = []

    def native(services, request, **kwargs):
        calls.append(request)
        return opened

    monkeypatch.setattr(direct, "read_source_anchor_direct_v2", native)
    return SimpleNamespace(
        turn=turn, text=text, opened=opened, calls=calls, native=native
    )


def test_exact_completed_source_reopens_with_frozen_native_authority(completed):
    c = completed
    result = open_source_passage(
        world_id=c.turn.world_id, turn_id=c.turn.turn_id, citation_index=0
    )
    assert result.content == c.text
    assert result.citation == c.turn.completion.source_citations[0]
    (request,) = c.calls
    assert request.revision_pin == "native-rev-3"
    assert request.world_id == "native-build-world" and request.campaign_id == ""
    assert request.max_chars == len(c.text) and request.admissibility == "gm"
    assert result.target.turn_id == c.turn.turn_id


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_revision_id", "wrong"),
        ("source_artifact_id", "wrong"),
        ("evidence_ref_id", "wrong"),
        ("graph_revision", "newer-head"),
        ("content", "replacement text"),
        ("content_sha256", "f" * 64),
        ("truncated", True),
        ("line_start", 99),
        ("line_end", 99),
        ("anchor_id", "foreign-anchor"),
        ("outcome", "missing"),
        ("snapshot.world_id", "foreign"),
        ("snapshot.revision_id", "newer-head"),
        ("snapshot.admissibility", "player"),
        ("snapshot.campaign_id", "campaign"),
        ("snapshot.scope_mode", "campaign"),
    ],
)
def test_changed_or_unavailable_authority_never_substitutes(
    completed, monkeypatch, field, value
):
    c = completed
    if field in {
        "source_revision_id",
        "source_artifact_id",
        "evidence_ref_id",
        "graph_revision",
    }:
        opened = replace(c.opened, **{field: value})
    elif field.startswith("snapshot."):
        snap = c.opened.result.snapshot.model_copy(update={field.split(".")[1]: value})
        opened = replace(
            c.opened, result=c.opened.result.model_copy(update={"snapshot": snap})
        )
    else:
        opened = replace(
            c.opened, result=c.opened.result.model_copy(update={field: value})
        )
    monkeypatch.setattr(direct, "read_source_anchor_direct_v2", lambda *a, **k: opened)
    with pytest.raises(SourcePassageOpenError, match="binding_invalid"):
        open_source_passage(
            world_id=c.turn.world_id, turn_id=c.turn.turn_id, citation_index=0
        )


def test_auth_world_turn_and_selector_boundaries(completed, monkeypatch):
    c = completed
    token = "synthetic-local-source-reader-token-" * 2
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")

    async def get(world=None, turn=None, index=0, authorized=True, query=""):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://test",
        ) as client:
            return await client.get(
                f"/api/live/agent/worlds/{world or c.turn.world_id}/conversation/turns/{turn or c.turn.turn_id}/source-passages/{index}{query}",
                headers={"Authorization": f"Bearer {token}"} if authorized else {},
            )

    assert asyncio.run(get(authorized=False)).status_code == 401
    assert c.calls == []
    assert asyncio.run(get(world="another-world")).status_code == 404
    assert asyncio.run(get(turn=uuid4())).status_code == 404
    assert asyncio.run(get(index=1)).status_code == 404
    assert asyncio.run(get(index=-1)).status_code == 422
    assert asyncio.run(get(query="?revisionPin=newer-head")).status_code == 422
    assert c.calls == []
    response = asyncio.run(get())
    assert response.status_code == 200, response.text
    assert response.json()["content"] == c.text
    assert response.json()["target"]["kind"] == "source_passage"


def test_native_error_has_no_trace_or_latest_fallback(completed, monkeypatch):
    def unavailable(*a, **k):
        raise FileNotFoundError("historical source missing")

    monkeypatch.setattr(direct, "read_source_anchor_direct_v2", unavailable)
    with pytest.raises(SourcePassageOpenError, match="source_passage_unavailable"):
        open_source_passage(
            world_id=completed.turn.world_id,
            turn_id=completed.turn.turn_id,
            citation_index=0,
        )


def test_immutable_app_source_reopens_after_actual_workspace_edit(
    build_case, tmp_path, monkeypatch
):
    """Native Graph resolution is stubbed; source/registry/APP/edit/read are real."""
    import json
    from hashlib import sha256
    from application_state.source import service as source_service
    from apps.live_control_server.services import (
        worldbuilding_source_span_read as reader,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        source_span_index_path,
    )
    from tests.test_worldbuilding_source_body_durability import (
        _registered_source,
        _save_source,
        _span_id,
    )
    from tests.test_agent_build_jev_controller_exposure import _start, _acquire
    from graph_memory.interaction import expansion_executor
    from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot

    document, artifact, markdown = _registered_source(tmp_path, monkeypatch)
    world = get_world("managed-world").record
    store_world(world.model_copy(update={"native_graph_binding": world.native_graph_binding.model_copy(update={"native_world_id": "native-build-world"})}))
    durable = source_service.persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        world_id=artifact.world_id,
        markdown=markdown,
    )
    span = _span_id(artifact, markdown)
    snapshot = WorldGraphRetrievalSnapshot.model_validate(
        {
            "worldId": "native-build-world",
            "campaignId": "",
            "scopeMode": "world",
            "focus": {"kind": "none", "sessionId": None},
            "admissibility": "gm",
            "revisionId": "native-rev-3",
            "headRevisionId": "later-head",
            "isHead": False,
        }
    )

    def read_source():
        return reader.read_admitted_worldbuilding_span(
            root=tmp_path,
            source_artifact_id=artifact.source_artifact_id,
            source_span_ref_id=span,
            graph_content_sha256=artifact.content_sha256,
            max_chars=12000,
            anchor_id="anchor-one",
            evidence_ref_id="evidence-one",
            snapshot=snapshot,
            graph_artifact=artifact,
        )

    original = read_source()
    adapter, _, old_text = _start(build_case, monkeypatch)
    graph_impl = direct.get_object_with_reviewed_sources_direct_v3
    source_impl = expansion_executor.execute_read_graph_source
    replacements = {
        "artifact-one": artifact.source_artifact_id,
        "source-rev-one": str(durable.source_revision_id),
        old_text: original.content,
        sha256(old_text.encode()).hexdigest(): original.content_sha256,
    }

    def replace_values(value):
        if isinstance(value, str):
            return replacements.get(value, value)
        if isinstance(value, list):
            return [replace_values(v) for v in value]
        if isinstance(value, dict):
            return {
                k: (
                    original.line_start
                    if k in {"lineStart", "line_start"}
                    else original.line_end
                    if k in {"lineEnd", "line_end"}
                    else replace_values(v)
                )
                for k, v in value.items()
            }
        return value

    def graph(*a, **k):
        resolved = graph_impl(*a, **k)
        return replace(
            resolved,
            result=type(resolved.result).model_validate(
                replace_values(resolved.result.model_dump(mode="json", by_alias=True))
            ),
            source_pins=tuple(
                SimpleNamespace(
                    **{
                        **vars(pin),
                        "source_artifact_id": artifact.source_artifact_id,
                        "source_revision_id": str(durable.source_revision_id),
                    }
                )
                for pin in resolved.source_pins
            ),
            reviewed_source_observations=tuple(
                type(o).model_validate(replace_values(o.model_dump(mode="json")))
                for o in resolved.reviewed_source_observations
            ),
        )

    monkeypatch.setattr(direct, "get_object_with_reviewed_sources_direct_v3", graph)
    monkeypatch.setattr(
        expansion_executor,
        "execute_read_graph_source",
        lambda *a, **k: replace_values(source_impl(*a, **k)),
    )
    graph_payload, source_payload = _acquire(adapter)
    projection = adapter.stage_build_source_writer(
        graph_payloads=(graph_payload,), source_payloads=(source_payload,)
    )
    output = json.loads(answer(projection))
    output["answer_segments"][0]["text"] = "The tower watches the river."
    adapter.complete_build_writer(
        invoke(adapter, projection, WriterWire(adapter, text=json.dumps(output)))
    )
    # Change the actual editable source and discard the old span-index file.
    _save_source(tmp_path, document, "# Lore\n\nThe tower has fallen.\n")
    source_span_index_path(tmp_path, artifact.source_artifact_id).unlink(
        missing_ok=True
    )

    def native(*a, **k):
        return direct.ResolvedSourceAnchorReadV2(
            result=read_source(),
            source_revision_id=str(durable.source_revision_id),
            source_revision_sha256=durable.content_sha256,
            evidence_ref_id="evidence-one",
            source_artifact_id=artifact.source_artifact_id,
            source_span_ref_id=span,
            locator_kind="source_span",
            locator_identity=span,
            graph_revision="native-rev-3",
        )

    monkeypatch.setattr(direct, "read_source_anchor_direct_v2", native)
    reopened = open_source_passage(
        world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id, citation_index=0
    )
    assert (
        reopened.content == original.content and "watches the river" in reopened.content
    )
    assert "fallen" not in reopened.content


def test_unfinished_turn_has_no_openable_source_completion(build_case, monkeypatch):
    adapter, _, _, _ = stage(build_case, monkeypatch)
    with pytest.raises(SourcePassageOpenError, match="completion_unavailable"):
        open_source_passage(
            world_id=adapter.turn.world_id, turn_id=adapter.turn.turn_id, citation_index=0
        )
