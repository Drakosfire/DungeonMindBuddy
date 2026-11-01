"""A fresh HTTP reader recovers exact Process bytes and candidate evidence from APP."""

import hashlib
import json
import shutil

from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_run_registry import (
    load_reviewable_extraction_data,
)
from tests.test_live_recap_ingest_graph_preview_api import (
    TOKEN,
    process_body,
)
from tests.test_live_recap_ingest_graph_preview_api import (
    client_env as client_env,
)


def test_ordinary_process_candidate_evidence_survives_fresh_exact_run_review_client(
    client_env,
):
    client, root = client_env
    request = process_body(session=29)
    response = client.post("/api/live/recap-ingest", json=request)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    run_id = graph["extraction_run_id"]
    data = load_reviewable_extraction_data(root, run_id)
    candidate = json.loads(data.candidate_bytes)
    spans = json.loads(data.span_bytes)
    ids = {r["source_span_id"] for r in spans["spans"]}
    refs = [
        ref
        for k in ["nodes", "edges", "beats"]
        for item in candidate[k]
        for ref in item.get("evidence_refs", [])
    ]
    assert refs and all(
        r["source_artifact_id"] == graph["source_artifact_id"]
        and r["source_span_ref_id"] in ids
        for r in refs
    )
    original = data.source_bytes
    assert original == request["raw_text"].encode() + b"\n"
    shutil.rmtree(root / "out/graph_memory", ignore_errors=True)
    # Neither a current file nor a previous client is needed to open the exact run.
    with TestClient(
        create_app(),
        client=("127.0.0.1", 50000),
        headers={"Authorization": "Bearer " + TOKEN},
    ) as fresh:
        catalog = fresh.get(
            "/api/live/graph-preview/extraction-runs",
            params={"managed_world_id": "elderwyld", "campaign_id": "longmont-c2"},
        )
        assert catalog.status_code == 200, catalog.text
        row = next(r for r in catalog.json()["runs"] if r["runId"] == run_id)
        reply = fresh.get(
            f"/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection",
            params={
                "managed_world_id": "elderwyld",
                "expected_run_revision": row["runRevision"],
                "source_revision_id": row["sourceRevisionId"],
            },
        )
        assert reply.status_code == 200, reply.text
        assert reply.json()["run"] == row
        assert reply.json()["sourceProse"].encode() == original
        assert hashlib.sha256(original).hexdigest() == row["sourceSha256"]
        recovered = load_reviewable_extraction_data(root, run_id)
        assert (
            recovered.candidate_bytes == data.candidate_bytes
            and recovered.span_bytes == data.span_bytes
        )
