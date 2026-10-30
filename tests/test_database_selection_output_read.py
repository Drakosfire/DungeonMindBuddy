"""Selection route consumes actual APP outputs without file authority."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import psycopg
import pytest
from fastapi import FastAPI

from apps.live_control_server.models.ingest_selection_context import IngestSelectionContextRequest
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import ingest_selection_context as selection
from apps.live_control_server.services.extract_promote import ExtractPromoteError
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _selection(monkeypatch, root):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    run = result.run
    data = registry.load_reviewable_extraction_data(root, run.run_id)
    payload = json.loads(data.candidate_bytes)
    monkeypatch.setattr(selection, "repo_root", lambda: root)
    monkeypatch.setattr(selection, "resolve_managed_world_binding", lambda _: SimpleNamespace(native_world_id="world:elderwyld", binding_version=1))
    # Native independent context is a separate read port. This test exercises
    # actual APP output/source storage and carries no native accepted facts.
    monkeypatch.setattr(selection, "resolve_native_review_context", lambda **kwargs: {
        "revision_id": "synthetic:native-context", "selections": [], "identity_approval": False})
    request = IngestSelectionContextRequest(
        schema="dmb_ingest_native_review_request_v2",
        expected_run_revision=run.revision,
        expected_candidate_sha256=run.components["candidate_graph"].sha256,
        expected_source_sha256=run.components["source_artifact"].sha256,
        expected_span_index_sha256=run.components["source_span_index"].sha256,
        expected_world_id="world:elderwyld", node_ids=[payload["nodes"][0]["node_id"]], edge_ids=[])
    return run, request


def test_mounted_selection_route_with_all_files_removed(monkeypatch, tmp_path):
    from apps.live_control_server.routes import extract_promote as routes
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency

    run, request = _selection(monkeypatch, tmp_path)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(subject="synthetic:operator", role="gm", auth_method="local_operator")
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("selection read a component file"))
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/live/extract-promote/runs/{run.run_id}/selection-context", json=request.model_dump(mode="json", by_alias=True))
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["run_id"] == run.run_id
            assert body["selected_node_ids"] == request.node_ids
            assert body["permissions"] == {"graph_write": False, "candidate_write": False, "provider_call": False}
            assert body["scope"]["admitted_world_facts_included"] is False
    asyncio.run(exercise())
    assert registry.get_extraction_run(tmp_path, run.run_id) == run


@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_selection_rejects_bad_stored_output_despite_file_mirrors(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    run, request = _selection(monkeypatch, tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        if violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (run.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", run.run_id, kind))
    with pytest.raises(ExtractPromoteError) as error:
        selection.resolve_ingest_selection_context(run.run_id, request, operator_subject="synthetic:operator")
    assert error.value.status_code == (409 if violation == "missing" else 500)
    assert registry.get_extraction_run(tmp_path, run.run_id) == run
