from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.source_artifact_registry import load_source_span_index
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    mark_workspace_document_committed,
)
from graph_memory.source_span import source_span_index_to_dict
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
)


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str) -> str:
    return application_state_dsn


@pytest.fixture
def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> TestClient:
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.services.workspace_document_registry.repo_root",
        lambda: tmp_path,
        raising=False,
    )
    return TestClient(create_app())


class _FixtureCategoryClient:
    """Deterministic category-pass client for Build launch route proofs."""

    def __init__(self, *, mode: str = "ok", span_ref: str | None = None) -> None:
        self.mode = mode
        self.span_ref = span_ref

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: Any = None,
    ) -> dict[str, Any]:
        if self.mode == "refusal":
            raise CategoryGraphExtractionError(f"model refused {pass_name}: policy")
        if self.mode == "incomplete":
            raise CategoryGraphExtractionError(f"model response incomplete for {pass_name}")
        if self.mode == "provider_missing":
            raise RuntimeError("OPENAI_API_KEY missing after loading server env")
        if pass_name == "edge_pass":
            return {
                "parsed": {"observation_edges": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "edge",
            }
        if pass_name == "beat_pass":
            return {
                "parsed": {"observation_beats": []},
                "cost_usd": 0.0,
                "usage": {},
                "elapsed_ms": 1,
                "response_id": "beat",
            }
        evidence_ref = self.span_ref or "span-1"
        return {
            "parsed": {
                "observation_nodes": [
                    {
                        "node_id": f"{pass_name}-1",
                        "label": "Mirathorn",
                        "node_type": "location",
                        "description": "fixture",
                        "importance": "medium",
                        "evidence_refs": [
                            {
                                "source_span_ref_id": evidence_ref,
                                "anchor_quotes": ["Mirathorn"],
                            }
                        ],
                    }
                ]
            },
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": 1,
            "response_id": pass_name,
        }


def _first_span_ref(root: Path, source_artifact_id: str) -> str:
    index = load_source_span_index(root, source_artifact_id)
    payload = source_span_index_to_dict(index)
    for span in payload.get("spans") or []:
        ref = str(span.get("source_span_id") or span.get("source_span_ref_id") or "").strip()
        if ref:
            return ref
    raise AssertionError("expected at least one source span")


def _patch_build_extraction(
    monkeypatch: pytest.MonkeyPatch,
    *,
    mode: str = "ok",
    capture: list[dict[str, Any]] | None = None,
) -> None:
    """Force deterministic category clients and prove server sets allow_llm=True."""
    from apps.live_control_server.services import graph_preview_runner as gpr

    real = gpr.run_worldbuilding_production_extraction

    def _wrapped(**kwargs: Any):
        if capture is not None:
            capture.append(dict(kwargs))
        root = kwargs["repo_root"]
        artifact_id = kwargs["source_artifact_id"]
        span_ref = _first_span_ref(root, artifact_id)
        return real(
            **{
                **kwargs,
                "allow_llm": True,
                "category_client": _FixtureCategoryClient(mode=mode, span_ref=span_ref),
            }
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_preview_runner.run_worldbuilding_production_extraction",
        _wrapped,
    )


def _commit_source(tmp_path: Path, *, body: str = "Mirathorn is a river city.\n"):
    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    committed = mark_workspace_document_committed(tmp_path, record.document_id)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return committed, digest


def test_launch_requires_committed_source(client: TestClient, tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="Draft lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    response = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": record.document_id,
            "expected_revision": record.revision,
            "expected_content_sha256": "deadbeef",
        },
    )
    assert response.status_code == 422
    assert "committed" in response.json()["detail"]


def test_launch_requires_content_digest(client: TestClient, tmp_path: Path) -> None:
    committed, _digest = _commit_source(tmp_path)
    response = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
        },
    )
    assert response.status_code == 422
    assert "expected_content_sha256" in response.json()["detail"]


def test_launch_rejects_stale_revision(client: TestClient, tmp_path: Path) -> None:
    committed, digest = _commit_source(tmp_path)
    response = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision - 1,
            "expected_content_sha256": digest,
        },
    )
    assert response.status_code == 409


def test_launch_rejects_digest_mismatch_without_creating_run(
    client: TestClient,
    tmp_path: Path,
) -> None:
    committed, digest = _commit_source(tmp_path)
    target = tmp_path / (committed.target_relpath or "")
    target.write_text("Bytes changed under the same revision.\n", encoding="utf-8")
    response = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
        },
    )
    assert response.status_code == 409
    assert "expected_content_sha256" in response.json()["detail"]


def test_launch_returns_exact_run_and_status_reload(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_extraction(monkeypatch)
    committed, digest = _commit_source(tmp_path)

    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
        },
    )
    assert launch.status_code == 200, launch.text
    payload = launch.json()
    run_id = payload["run"]["run_id"]
    assert payload["document_id"] == committed.document_id
    assert payload["document_revision"] == committed.revision
    assert payload["source_content_sha256"] == digest
    assert payload["graph_review_handoff"]["extraction_run_id"] == run_id
    assert payload["graph_review_handoff"]["document_revision"] == committed.revision
    assert "latest" not in payload["graph_review_handoff"]["href"]

    generic = client.get(f"/api/live/graph-preview/extraction-runs/{run_id}")
    assert generic.status_code == 200
    generic_body = generic.json()
    assert generic_body["run_id"] == run_id
    assert "schema_version" not in generic_body or generic_body.get("schema_version") == "dmb_extraction_run_v1"
    assert "graph_review_handoff" not in generic_body

    status = client.get(f"/api/live/graph-preview/extraction-runs/{run_id}/build-context")
    assert status.status_code == 200
    body = status.json()
    assert body["schema_version"] == "dmb_extraction_run_status_v1"
    assert body["run"]["run_id"] == run_id
    assert body["document_id"] == committed.document_id
    assert body["document_revision"] == committed.revision
    assert body["source_content_sha256"] == digest
    assert body["graph_review_handoff"]["document_id"] == committed.document_id
    assert body["graph_review_handoff"]["document_revision"] == committed.revision
    assert "latest" not in body["graph_review_handoff"]["href"]


def test_launch_ignores_client_allow_llm_false_and_executes(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, Any]] = []
    _patch_build_extraction(monkeypatch, capture=captured)
    committed, digest = _commit_source(tmp_path)

    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
            "allow_llm": False,
        },
    )
    assert launch.status_code == 200, launch.text
    assert captured, "expected production extraction to be invoked"
    assert captured[0]["allow_llm"] is True
    payload = launch.json()
    assert payload["run"]["status"] == "reviewable"
    assert payload.get("failure_kind") in (None, "")
    href = payload["graph_review_handoff"]["href"]
    assert f"extractionRunId={payload['run']['run_id']}" in href
    assert f"sourceArtifactId={payload['source_artifact_id']}" in href
    assert f"documentId={committed.document_id}" in href
    assert f"revision={committed.revision}" in href
    assert "latest" not in href


def test_launch_reaches_reviewable_with_exact_handoff(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_extraction(monkeypatch)
    committed, digest = _commit_source(tmp_path)

    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
        },
    )
    assert launch.status_code == 200, launch.text
    payload = launch.json()
    run_id = payload["run"]["run_id"]
    assert payload["run"]["status"] == "reviewable"
    assert not payload.get("failure_kind")
    handoff = payload["graph_review_handoff"]
    assert handoff["extraction_run_id"] == run_id
    assert handoff["source_artifact_id"] == payload["source_artifact_id"]
    assert handoff["document_id"] == committed.document_id
    assert handoff["document_revision"] == committed.revision
    assert (
        handoff["href"]
        == (
            "/ingest"
            f"?extractionRunId={run_id}"
            f"&sourceArtifactId={payload['source_artifact_id']}"
            f"&documentId={committed.document_id}"
            f"&revision={committed.revision}"
        )
    )

    status = client.get(f"/api/live/graph-preview/extraction-runs/{run_id}/build-context")
    assert status.status_code == 200
    assert status.json()["run"]["status"] == "reviewable"
    assert status.json()["run"]["run_id"] == run_id


def test_launch_model_failure_returns_explicit_non_reviewable(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_extraction(monkeypatch, mode="provider_missing")
    committed, digest = _commit_source(tmp_path)

    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
        },
    )
    assert launch.status_code == 200, launch.text
    payload = launch.json()
    assert payload["run"]["status"] != "reviewable"
    # Prepared is not acceptable for unavailable execution — must be an explicit failure.
    assert payload["run"]["status"] != "prepared"
    assert payload["failure_kind"] == "model"
    assert payload["diagnostics"]
    assert any("OPENAI_API_KEY" in item for item in payload["diagnostics"])
    assert payload["graph_review_handoff"]["extraction_run_id"] == payload["run"]["run_id"]


def test_generic_exact_get_returns_recap_run(client: TestClient, tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import create_extraction_run
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
    )

    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="eldyrwild",
        session_id="session-1",
        recap_text="The party reached Mirathorn.\n",
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="recap",
        campaign_id="eldyrwild",
        session_id="session-1",
    )

    generic = client.get(f"/api/live/graph-preview/extraction-runs/{run.run_id}")
    assert generic.status_code == 200
    body = generic.json()
    assert body["run_id"] == run.run_id
    assert body["source_domain"] == "recap"
    assert body["source_artifact_id"] == artifact.source_artifact_id
    assert "latest" not in body.get("run_id", "")

    build_context = client.get(
        f"/api/live/graph-preview/extraction-runs/{run.run_id}/build-context"
    )
    assert build_context.status_code == 422
    detail = build_context.json()["detail"]
    assert "Build context" in detail or "not applicable" in detail

    # Generic reload remains intact after Build-context rejection.
    generic_again = client.get(f"/api/live/graph-preview/extraction-runs/{run.run_id}")
    assert generic_again.status_code == 200
    assert generic_again.json()["run_id"] == run.run_id


def test_neither_endpoint_substitutes_latest(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_build_extraction(monkeypatch)
    committed, digest = _commit_source(tmp_path)
    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
        },
    )
    assert launch.status_code == 200
    run_id = launch.json()["run"]["run_id"]

    generic = client.get(f"/api/live/graph-preview/extraction-runs/{run_id}")
    assert generic.status_code == 200
    assert generic.json()["run_id"] == run_id

    build_context = client.get(
        f"/api/live/graph-preview/extraction-runs/{run_id}/build-context"
    )
    assert build_context.status_code == 200
    assert build_context.json()["run"]["run_id"] == run_id
    assert "latest" not in build_context.json()["graph_review_handoff"]["href"]

    missing = client.get("/api/live/graph-preview/extraction-runs/not-a-real-run-id")
    assert missing.status_code == 404
    missing_ctx = client.get(
        "/api/live/graph-preview/extraction-runs/not-a-real-run-id/build-context"
    )
    assert missing_ctx.status_code == 404


def test_launch_bounded_profile_records_exact_profile_and_applies_validator(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build launch with BLD-08 profile records that profile and enforces its validator."""
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )

    class _ItemInjectingClient(_FixtureCategoryClient):
        def run_pass(self, pass_name: str, **kwargs: Any) -> dict[str, Any]:
            result = super().run_pass(pass_name, **kwargs)
            if pass_name == "actor_pass" and self.mode == "ok":
                nodes = result["parsed"]["observation_nodes"]
                nodes.append(
                    {
                        "node_id": "item:trail-rations",
                        "label": "trail rations",
                        "node_type": "item",
                        "description": "excluded by BLD-08",
                        "importance": "low",
                        "evidence_refs": [
                            {
                                "source_span_ref_id": self.span_ref or "span-1",
                                "anchor_quotes": ["Mirathorn"],
                            }
                        ],
                    }
                )
            return result

    from apps.live_control_server.services import graph_preview_runner as gpr

    real = gpr.run_worldbuilding_production_extraction
    captured: list[dict[str, Any]] = []

    def _wrapped(**kwargs: Any):
        captured.append(dict(kwargs))
        root = kwargs["repo_root"]
        artifact_id = kwargs["source_artifact_id"]
        span_ref = _first_span_ref(root, artifact_id)
        return real(
            **{
                **kwargs,
                "allow_llm": True,
                "category_client": _ItemInjectingClient(mode="ok", span_ref=span_ref),
            }
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_preview_runner.run_worldbuilding_production_extraction",
        _wrapped,
    )
    committed, digest = _commit_source(tmp_path)
    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
            "profile_id": WORLDBUILDING_PROFILE_ID,
            "profile_version": WORLDBUILDING_PROFILE_VERSION,
        },
    )
    assert launch.status_code == 200, launch.text
    assert captured
    assert captured[0]["profile_id"] == WORLDBUILDING_PROFILE_ID
    assert captured[0]["profile_version"] == WORLDBUILDING_PROFILE_VERSION
    payload = launch.json()
    assert payload["run"]["profile_id"] == (
        f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
    )
    assert payload["run"]["status"] != "reviewable"
    assert payload["failure_kind"] == "validation"
    assert any("excluded type" in d for d in payload["diagnostics"])


def test_launch_default_uses_bounded_shepherds_flock_profile(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )

    captured: list[dict[str, Any]] = []
    _patch_build_extraction(monkeypatch, capture=captured)
    committed, digest = _commit_source(tmp_path)
    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
        },
    )
    assert launch.status_code == 200, launch.text
    assert captured[0]["profile_id"] == WORLDBUILDING_PROFILE_ID
    assert captured[0]["profile_version"] == WORLDBUILDING_PROFILE_VERSION
    assert launch.json()["run"]["profile_id"] == (
        f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
    )
    assert launch.json()["run"]["status"] == "reviewable"


def test_launch_still_allows_explicit_plumbing_profile(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE_ID,
        WORLDBUILDING_PLUMBING_PROFILE_VERSION,
    )

    captured: list[dict[str, Any]] = []
    _patch_build_extraction(monkeypatch, capture=captured)
    committed, digest = _commit_source(tmp_path)
    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
            "profile_id": WORLDBUILDING_PLUMBING_PROFILE_ID,
            "profile_version": WORLDBUILDING_PLUMBING_PROFILE_VERSION,
        },
    )
    assert launch.status_code == 200, launch.text
    assert captured[0]["profile_id"] == WORLDBUILDING_PLUMBING_PROFILE_ID
    assert launch.json()["run"]["profile_id"] == (
        f"{WORLDBUILDING_PLUMBING_PROFILE_ID}@{WORLDBUILDING_PLUMBING_PROFILE_VERSION}"
    )


@pytest.mark.parametrize(
    "payload_extra,detail_fragment",
    [
        ({"profile_id": ["not", "a", "string"]}, "profile_id"),
        ({"profile_version": {"v": "0.1"}}, "profile_version"),
        ({"profile_id": ""}, "profile_id"),
        ({"profile_version": "   "}, "profile_version"),
    ],
)
def test_launch_rejects_malformed_profile_selectors_with_422(
    client: TestClient,
    tmp_path: Path,
    payload_extra: dict[str, Any],
    detail_fragment: str,
) -> None:
    committed, digest = _commit_source(tmp_path)
    launch = client.post(
        "/api/live/graph-preview/extraction-runs",
        json={
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
            **payload_extra,
        },
    )
    assert launch.status_code == 422, launch.text
    assert detail_fragment in launch.json()["detail"]
