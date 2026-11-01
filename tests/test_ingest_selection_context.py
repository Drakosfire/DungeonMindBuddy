"""Actual authenticated route and frozen-source/record selection boundary."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from apps.live_control_server.models.ingest_selection_context import (
    IngestSelectionContextRequest,
)
from apps.live_control_server.services import ingest_selection_context as service
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
from apps.live_control_server.services.extract_promote import ExtractPromoteError
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)
from graph_memory.source_span import (
    build_source_span_index_for_text,
    source_span_index_to_dict,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def context(monkeypatch, tmp_path):
    # The repeated paragraph tests location binding, not first substring match.
    text = "Ari 🐉 visits cafe\u0301.\n\nAri 🐉 visits cafe\u0301.\n"
    artifact = "artifact:test:one"
    sha = digest(text.encode())
    index = source_span_index_to_dict(
        build_source_span_index_for_text(
            source_artifact_id=artifact, content_sha256=sha, text=text
        )
    )
    payload = {
        "campaign_id": "c1",
        "session_id": "session-29",
        "source_artifact_ids": [artifact],
        "nodes": [
            {"node_id": "ari", "label": "Ari", "node_type": "character"},
            {"node_id": "warehouse", "label": "Warehouse", "node_type": "location"},
        ],
        "edges": [
            {
                "edge_id": "e1",
                "from_node_id": "ari",
                "to_node_id": "warehouse",
                "relationship_type": "present_at",
                "label": "visits",
            }
        ],
    }
    components = {}
    outputs = {}
    for kind, filename, content in [
        ("source_artifact", "source.md", text.encode()),
        ("candidate_graph", "candidate.json", json.dumps(payload).encode()),
        ("source_span_index", "index.json", json.dumps(index).encode()),
    ]:
        (tmp_path / filename).write_bytes(content)
        outputs[kind] = content
        components[kind] = ExtractionRunComponentRef(
            kind=kind, uri=filename, sha256=digest(content), exists=True
        )
    run = ExtractionRun(
        run_id="test-run",
        source_artifact_id=artifact,
        source_domain="recap",
        campaign_id="c1",
        session_id="session-29",
        profile_id="recap_category_v1@1.0",
        status=ExtractionRunStatus.REVIEWABLE,
        revision=6,
        components=components,
        lineage={"world_campaign_ingest_context": {
            "schema": "dm_world_campaign_ingest_context_v1",
            "managed_world_id": "world-a", "native_world_id": "native-a",
            "binding_version": 2, "campaign_id": "c1",
            "head_revision_id": "rev:observed", "graph_schema": "dm_graph_v1",
            "graph_payload_sha256": "a" * 64,
        }},
    )
    source = SimpleNamespace(
        source_artifact_id=artifact,
        source_domain="recap",
        campaign_id="c1",
        session_id="session-29",
        world_id="native-a",
        content_sha256=sha,
        markdown=text,
        encoding="utf-8",
    )
    binding = SimpleNamespace(native_world_id="native-a", binding_version=2)
    monkeypatch.setattr(service, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(service, "artifact_data_root", lambda root: root)

    def get_run(root, run_id):
        if run_id != run.run_id:
            raise GraphRunRegistryError("missing run")
        return run

    def get_output(*, run_id, kind, content_sha256):
        from application_state.errors import ApplicationStateIntegrityError
        assert run_id == run.run_id
        data = outputs[str(kind)]
        if digest(data) != content_sha256:
            raise ApplicationStateIntegrityError("fixture stored output digest mismatch")
        return data

    monkeypatch.setattr(service, "get_component_bytes", get_output)
    monkeypatch.setattr(service, "get_extraction_run", get_run)
    monkeypatch.setattr(
        service.source_service, "get_source_markdown", lambda **kwargs: source
    )
    monkeypatch.setattr(service, "resolve_managed_world_binding", lambda world: binding)
    monkeypatch.setattr(service, "resolve_native_review_context", lambda **kwargs: {
        "revision_id": "native-revision-test",
        "selections": [],
        "identity_approval": False,
    })
    second_start = len(text.splitlines(keepends=True)[0]) + 1
    selection = {
        "source_span_ref_id": index["spans"][1]["source_span_id"],
        "start": second_start,
        "end": second_start + len("Ari 🐉"),
        "text": "Ari 🐉",
    }
    body = {
        "schema": "dmb_ingest_native_review_request_v2",
        "expected_run_revision": 6,
        "expected_candidate_sha256": components["candidate_graph"].sha256,
        "expected_source_sha256": sha,
        "expected_span_index_sha256": components["source_span_index"].sha256,
        "expected_world_id": "world-a",
        "node_ids": ["ari"],
        "edge_ids": [],
        "source_selection": selection,
        "annotation": "These children came from Edge.",
    }
    return SimpleNamespace(
        root=tmp_path,
        source=source,
        run=run,
        body=body,
        index=index,
        payload=payload,
        binding=binding,
        text=text,
        outputs=outputs,
    )


def resolve(context, **changes):
    body = {**context.body, **changes}
    return service.resolve_ingest_selection_context(
        context.run.run_id,
        IngestSelectionContextRequest.model_validate(body),
        operator_subject="operator:test",
    )


def rewrite_component(context, kind, filename, payload):
    data = json.dumps(payload).encode()
    (context.root / filename).write_bytes(data)
    context.outputs[kind] = data
    context.run.components[kind] = context.run.components[kind].model_copy(
        update={"sha256": digest(data)}
    )
    context.body[
        "expected_" + ({"candidate_graph": "candidate", "source_span_index": "span_index"}.get(kind, kind)) + "_sha256"
    ] = digest(data)


def test_context_is_deterministic_historical_and_does_not_write(context):
    before = {p.name: p.read_bytes() for p in context.root.iterdir()}
    first = resolve(context)
    assert first == resolve(context)
    assert first["source_domain"] == "recap"
    assert first["profile_id"] == "recap_category_v1@1.0"
    assert (
        first["source_selection"]["start"] == context.body["source_selection"]["start"]
    )
    assert first["source_selection"]["offset_unit"] == "unicode_code_points"
    assert first["source_selection"]["paragraph_start"] > 0
    assert first["annotation"] == {
        "text": context.body["annotation"],
        "provenance": "operator_annotation",
        "operator_subject": "operator:test",
    }
    assert first["scope"]["managed_world_id"] == "world-a"
    assert first["scope"]["native_world_id"] == "native-a"
    assert first["scope"]["admitted_world_facts_included"] is False
    assert {n["record"]["node_id"] for n in first["nodes"]} == {"ari", "warehouse"}
    assert all(n["identity_authority"] == "candidate_only" for n in first["nodes"])
    assert first["permissions"] == {
        "graph_write": False,
        "candidate_write": False,
        "provider_call": False,
    }
    expected = deepcopy(first)
    expected.pop("context_sha256")
    assert first["context_sha256"] == service._record_hash(expected)
    assert before == {p.name: p.read_bytes() for p in context.root.iterdir()}


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_run_revision", 5),
        ("expected_world_id", "world-b"),
        ("expected_candidate_sha256", "f" * 64),
        ("expected_source_sha256", "f" * 64),
        ("expected_span_index_sha256", "f" * 64),
    ],
)
def test_stale_or_foreign_preconditions_reject(context, field, value):
    with pytest.raises(ExtractPromoteError) as caught:
        resolve(context, **{field: value})
    assert caught.value.status_code == 409


@pytest.mark.parametrize(
    "change", ["other_paragraph", "utf16", "text", "foreign_span", "bounds"]
)
def test_source_selection_never_relocates_or_normalizes(context, change):
    selected = deepcopy(context.body["source_selection"])
    if change == "other_paragraph":
        selected["start"] = 0
        selected["end"] = len(selected["text"])
    elif change == "utf16":
        selected["end"] += 1
    elif change == "text":
        selected["text"] = (
            "Ari 🐉 visits café."  # composed differs from saved combining sequence
        )
        selected["end"] = selected["start"] + len(selected["text"])
    elif change == "foreign_span":
        selected["source_span_ref_id"] = "span:elsewhere"
    elif change == "bounds":
        selected["end"] = len(context.text) + 10
    with pytest.raises(ExtractPromoteError):
        resolve(context, source_selection=selected)


def test_combining_sequence_can_be_selected_exactly(context):
    selected = deepcopy(context.body["source_selection"])
    selected["start"] = context.text.rfind("cafe\u0301")
    selected["end"] = selected["start"] + len("cafe\u0301")
    selected["text"] = "cafe\u0301"
    assert (
        resolve(context, source_selection=selected)["source_selection"]["text"]
        == selected["text"]
    )


@pytest.mark.parametrize(
    "target",
    [
        "source_campaign",
        "source_artifact",
        "candidate_campaign",
        "index_artifact",
        "damaged_bytes",
    ],
)
def test_foreign_components_and_source_identity_reject(context, target):
    if target == "source_campaign":
        context.source.campaign_id = "other"
    elif target == "source_artifact":
        context.source.source_artifact_id = "other"
    elif target == "candidate_campaign":
        context.payload["campaign_id"] = "other"
        rewrite_component(context, "candidate_graph", "candidate.json", context.payload)
    elif target == "index_artifact":
        context.index["source_artifact_id"] = "other"
        rewrite_component(context, "source_span_index", "index.json", context.index)
    elif target == "damaged_bytes":
        context.outputs["candidate_graph"] = b"{}"
    with pytest.raises((ExtractPromoteError, GraphRunRegistryError)):
        resolve(context)


def test_world_observation_cannot_cross_binding(context):
    context.run.lineage["world_campaign_ingest_context"] = {
        "managed_world_id": "world-a",
        "native_world_id": "native-b",
        "campaign_id": "c1",
        "binding_version": 2,
    }
    with pytest.raises(ExtractPromoteError, match="binding changed"):
        resolve(context)


@pytest.mark.parametrize(
    "change", ["missing_node", "missing_edge", "dangling_edge", "duplicate_node"]
)
def test_record_identity_or_endpoint_ambiguity_rejects(context, change):
    body = {}
    if change == "missing_node":
        body["node_ids"] = ["foreign-node"]
    elif change == "missing_edge":
        body["edge_ids"] = ["foreign-edge"]
    elif change == "dangling_edge":
        context.payload["edges"][0]["to_node_id"] = "missing"
        rewrite_component(context, "candidate_graph", "candidate.json", context.payload)
    elif change == "duplicate_node":
        context.payload["nodes"].append(deepcopy(context.payload["nodes"][0]))
        rewrite_component(context, "candidate_graph", "candidate.json", context.payload)
    with pytest.raises(ExtractPromoteError):
        resolve(context, **body)


def test_neighborhood_is_bounded_sorted_and_explicitly_truncated(context):
    context.payload["edges"] = [
        {
            "edge_id": f"e{i:03}",
            "from_node_id": "ari",
            "to_node_id": "warehouse",
            "relationship_type": "present_at",
            "label": str(i),
        }
        for i in reversed(range(80))
    ]
    rewrite_component(context, "candidate_graph", "candidate.json", context.payload)
    output = resolve(context, edge_ids=["e079"])
    assert output["selected_edge_ids"] == ["e079"]
    assert output["neighborhood"] == {
        "incident_edge_count": 79,
        "returned_incident_edge_count": 64,
        "limit": 64,
        "truncated": True,
    }
    ids = [e["record"]["edge_id"] for e in output["edges"]]
    assert ids == sorted(ids) and len(ids) == 65 and "e079" in ids


def test_authenticated_route_and_schema_rejection(context):
    from apps.live_control_server.routes import extract_promote as routes
    from apps.live_control_server.services.agent_graph_auth import (
        native_graph_gm_dependency,
        NativeGraphPrincipal,
    )

    app = FastAPI()
    app.include_router(routes.router)
    principal = NativeGraphPrincipal(
        subject="operator:http", role="gm", auth_method="local_operator"
    )
    app.dependency_overrides[native_graph_gm_dependency] = lambda: principal
    url = f"/api/live/extract-promote/runs/{context.run.run_id}/selection-context"

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(url, json=context.body)
            assert response.status_code == 200, response.text
            assert response.json()["annotation"]["operator_subject"] == "operator:http"
            assert response.json()["scope"]["managed_world_id"] == "world-a"
            assert response.json()["scope"]["native_world_id"] == "native-a"
            assert (
                await client.post(url + "?world_id=other", json=context.body)
            ).status_code == 422
            assert (
                await client.post(
                    url, json={**context.body, "native_world_id": "forged"}
                )
            ).status_code == 422
            stale = await client.post(
                url, json={**context.body, "expected_run_revision": 1}
            )
            assert stale.status_code == 409
            app.dependency_overrides.clear()
            unauthenticated = await client.post(url, json=context.body)
            assert unauthenticated.status_code in (401, 503)

    asyncio.run(exercise())


def test_unbound_context_cannot_fall_back_to_worldless_review(context):
    context.source.world_id = None
    with pytest.raises(ExtractPromoteError, match="active managed World binding"):
        resolve(context, expected_world_id=None)


def test_concurrent_run_change_rejects_context(context, monkeypatch):
    count = 0

    def changed_run(root, run_id):
        nonlocal count
        count += 1
        return (
            context.run
            if count == 1
            else context.run.model_copy(update={"revision": 7})
        )

    monkeypatch.setattr(service, "get_extraction_run", changed_run)
    with pytest.raises(ExtractPromoteError, match="changed while resolving"):
        resolve(context)


def test_worldbuilding_cannot_silently_select_recap_review_scope(context):
    context.source.source_domain = "worldbuilding"
    context.source.session_id = None
    context.run.source_domain = "worldbuilding"
    context.run.session_id = None
    context.payload["session_id"] = None
    rewrite_component(context, "candidate_graph", "candidate.json", context.payload)
    with pytest.raises(ExtractPromoteError, match="recap with exact campaign and session"):
        resolve(context)


@pytest.mark.parametrize("field", ["campaign_id", "session_id"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_recap_scope_refuses_before_native_binding(context, monkeypatch, field, value):
    context.run = context.run.model_copy(update={field: value})
    setattr(context.source, field, value)
    monkeypatch.setattr(service, "get_extraction_run", lambda *_: context.run)

    def forbidden_binding(*_):
        pytest.fail("incomplete recap scope reached native binding resolution")

    monkeypatch.setattr(service, "resolve_managed_world_binding", forbidden_binding)
    with pytest.raises(ExtractPromoteError, match="recap with exact campaign and session"):
        resolve(context)


def test_observation_cannot_substitute_another_session(context):
    context.run.lineage["world_campaign_ingest_context"] = {
        "managed_world_id": "world-a",
        "native_world_id": "native-a",
        "binding_version": 2,
        "campaign_id": "c1",
        "session_id": "session-other",
    }
    with pytest.raises(ExtractPromoteError, match="another session"):
        resolve(context)


def test_selected_edge_loads_both_endpoints_without_label_resolution(context):
    output = resolve(context, node_ids=[], edge_ids=["e1"], source_selection=None)
    assert output["selected_node_ids"] == []
    assert {node["record"]["node_id"] for node in output["nodes"]} == {
        "ari",
        "warehouse",
    }
    assert output["source_selection"] is None


def test_request_does_not_accept_authority_or_excessive_records(context):
    from pydantic import ValidationError

    for change in (
        {"native_world_id": "other"},
        {"campaign_id": "other"},
        {"session_id": "other"},
        {"role": "player"},
        {"standing_selector": ["established"]},
        {"revision_id": "chosen-by-client"},
        {"candidate_path": "/etc/passwd"},
        {"node_ids": ["ari", "ari"]},
        {"node_ids": [str(i) for i in range(33)]},
        {"expected_run_revision": True},
        {"schema": "dmb_ingest_selection_context_v1"},
    ):
        with pytest.raises(ValidationError):
            IngestSelectionContextRequest.model_validate({**context.body, **change})
    untagged = {key: value for key, value in context.body.items() if key != "schema"}
    with pytest.raises(ValidationError):
        IngestSelectionContextRequest.model_validate(untagged)


def test_binding_drift_during_native_read_rejects(context, monkeypatch):
    def changed(**kwargs):
        context.binding.binding_version += 1
        return {"revision_id": "revision", "selections": [], "identity_approval": False}

    monkeypatch.setattr(service, "resolve_native_review_context", changed)
    with pytest.raises(ExtractPromoteError, match="binding changed") as caught:
        resolve(context)
    assert caught.value.status_code == 409


def test_binding_lookup_uses_selected_managed_world(context, monkeypatch):
    seen = []

    def binding(world):
        seen.append(world)
        return context.binding

    monkeypatch.setattr(service, "resolve_managed_world_binding", binding)
    output = resolve(context)
    assert seen == ["world-a", "world-a"]
    assert output["scope"]["native_world_id"] == context.source.world_id


@pytest.mark.parametrize("source_world", ["native-b", "world-a", None, ""])
def test_source_ownership_must_match_native_binding(context, monkeypatch, source_world):
    context.source.world_id = source_world
    monkeypatch.setattr(
        service, "resolve_native_review_context",
        lambda **_: pytest.fail("foreign source reached native review"),
    )
    with pytest.raises(ExtractPromoteError, match="selected native World"):
        resolve(context)


def test_frozen_binding_version_must_match_current_owner(context, monkeypatch):
    context.binding.binding_version += 1
    monkeypatch.setattr(
        service, "resolve_native_review_context",
        lambda **_: pytest.fail("stale binding reached native review"),
    )
    with pytest.raises(ExtractPromoteError, match="binding changed") as caught:
        resolve(context)
    assert caught.value.status_code == 409


def test_managed_selection_cannot_be_replaced_with_native_id(context, monkeypatch):
    monkeypatch.setattr(
        service, "resolve_managed_world_binding",
        lambda *_: pytest.fail("foreign managed selection reached binding owner"),
    )
    with pytest.raises(ExtractPromoteError, match="selection belongs to another World") as caught:
        resolve(context, expected_world_id="native-a")
    assert caught.value.status_code == 409
