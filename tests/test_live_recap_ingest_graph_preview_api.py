from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
CORPUS_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"
FIXTURE_DIR = ROOT / "tests/fixtures/graph_memory/category_preview_runner"
CANDIDATE_FIXTURE = FIXTURE_DIR / "candidate_graph_fixture.json"


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str) -> str:
    return application_state_dsn


@pytest.fixture
def client_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path, Path]:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))

    corpus = tmp_path / "external-corpus"
    graph_runs = ROOT / "out/graph_memory/runs/longmont-c2/session-22"
    shutil.rmtree(graph_runs, ignore_errors=True)
    source_registry = ROOT / "out/registries"
    shutil.rmtree(source_registry, ignore_errors=True)
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(CORPUS_ENV, str(corpus))
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "out/graph_memory/runs")

    candidate = ROOT / "out/test_recap_ingest_graph_preview/candidate_graph_fixture.json"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(CANDIDATE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        yield TestClient(create_app()), corpus, candidate
    finally:
        shutil.rmtree(graph_runs, ignore_errors=True)


def _prepare_normalized(client: TestClient) -> None:
    raw = "Session 22 Recap\n\nThe group scouts the Mireward road and regroups at dusk."
    stage = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": raw,
            "slug": "Mireward Road Dogfood",
        },
    )
    assert stage.status_code == 200
    apply = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road Dogfood",
        },
    )
    assert apply.status_code == 200


def _stamp_fixture_candidate(
    client: TestClient,
    corpus: Path,
    candidate: Path,
) -> None:
    """Give a manual candidate the exact identity packaging now requires."""
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
    )
    from src.graph_memory.extraction.graph_ingest_packaging import (
        _with_candidate_graph_identity,
    )

    status = client.post(
        "/api/live/recap-ingest",
        json={"operation": "inspect_status", "campaign_id": "longmont-c2", "session": 22},
    )
    assert status.status_code == 200
    rel = status.json().get("paths", {}).get("normalized_recap")
    assert rel, status.json()
    recap = Path(str(rel))
    if not recap.is_absolute():
        recap = corpus / recap
    artifact = create_recap_source_artifact(
        ROOT,
        campaign_id="longmont-c2",
        session_id="session-22",
        recap_path=recap,
    )
    graph = _with_candidate_graph_identity(
        json.loads(candidate.read_text(encoding="utf-8")),
        campaign_id="longmont-c2",
        session_id="session-22",
        source_artifact_id=artifact.source_artifact_id,
    )
    candidate.write_text(
        json.dumps(graph, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _patch_retired_union_materialize(monkeypatch: pytest.MonkeyPatch) -> None:
    """D.3B retired UnionSupergraph materialization; keep the recap producer path."""
    import apps.live_control_server.routes.recap_ingest as recap_routes
    from apps.live_control_server.services.recap_graph_preview_ingest import (
        build_recap_graph_preview_bundle,
    )

    def _build_only(**kwargs):  # noqa: ANN003
        kwargs.pop("manifest_path", None)
        return build_recap_graph_preview_bundle(**kwargs)

    monkeypatch.setattr(
        recap_routes, "materialize_recap_preview_supergraph", _build_only
    )


def test_recap_ingest_build_graph_preview_bundle_from_normalized_recap(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_graph_preview_bundle", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    body = response.json()
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert (ROOT / graph["manifest_path"]).is_file()
    assert "graph_source_bundle_ready" in body["states"]
    assert "Candidate graph extraction has not run yet" in graph["blocked_reason"]


def test_recap_ingest_materialize_preview_supergraph_blocks_without_candidate_graph(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_graph_preview_bundle", "campaign_id": "longmont-c2", "session": 22},
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "materialize_preview_supergraph", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert "Candidate graph extraction has not run yet" in graph["blocked_reason"]
    assert graph["preview_union_store_path"] is None


def test_recap_ingest_materialize_preview_supergraph_with_candidate_graph_path(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, corpus, candidate = client_env
    _prepare_normalized(client)
    _stamp_fixture_candidate(client, corpus, candidate)
    _patch_retired_union_materialize(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": candidate.relative_to(ROOT).as_posix(),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert (ROOT / graph["manifest_path"]).is_file()
    assert "graph_candidate_ready" in body["states"]
    from apps.live_control_server.services.graph_run_registry import get_extraction_run

    run = get_extraction_run(ROOT, graph["extraction_run_id"])
    assert run.source_artifact_id == graph["source_artifact_id"]


def test_recap_ingest_rejects_unsafe_candidate_graph_path(client_env: tuple[TestClient, Path, Path]) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": "../escape.json",
        },
    )

    assert response.status_code == 422


def _live_extraction_payload(*, source_artifact_id: str, spref: str) -> dict:
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        canonical_candidate_graph_from_passes,
    )

    graph = canonical_candidate_graph_from_passes(spref=spref)
    graph["source_artifact_ids"] = [source_artifact_id]
    for collection in ("nodes", "edges", "beats", "ignored_items", "deferred_items", "proposed_writes"):
        for item in graph.get(collection) or []:
            if not isinstance(item, dict):
                continue
            refs = item.get("evidence_refs") or []
            stamped = []
            for ref in refs:
                if not isinstance(ref, dict):
                    continue
                stamped.append(
                    {
                        **ref,
                        "source_artifact_id": source_artifact_id,
                        "source_ref_id": f"{source_artifact_id}:text",
                        "source_anchor_id": ref.get("source_anchor_id")
                        or f"anchor:{ref.get('source_span_ref_id') or spref}",
                        "label": ref.get("label") or ref.get("source_span_ref_id") or spref,
                        "evidence_role": ref.get("evidence_role") or "source_evidence",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": ref.get("source_span_ref_id") or spref,
                    }
                )
            item["evidence_refs"] = stamped
    return graph


def _patch_fake_category_extract(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.graph_memory.extraction.graph_preview_runner as prod_runner
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionResult,
    )

    def fake_extract(options, *, client=None, progress_callback=None):  # noqa: ANN001
        spans = list(options.source_span_index.get("spans") or [])
        spref = "session-22:recap:paragraph:001"
        for span in spans:
            if not isinstance(span, dict):
                continue
            candidate = str(
                span.get("source_span_id")
                or span.get("source_span_ref_id")
                or span.get("span_id")
                or ""
            ).strip()
            if candidate:
                spref = candidate
                break
        artifact = str(
            options.source_artifact_id
            or options.source_span_index.get("source_artifact_id")
            or ""
        ).strip()
        graph = _live_extraction_payload(source_artifact_id=artifact, spref=spref)
        if options.campaign_id:
            graph["campaign_id"] = options.campaign_id
        if options.session_id:
            graph["session_id"] = options.session_id
        return CategoryGraphExtractionResult(
            candidate_graph=graph,
            envelope={"candidate_graph": graph},
            pass_outputs={},
            pass_telemetry={},
            consolidation_diagnostics={},
            model_id=options.model_id or "gpt-5.4-mini",
            total_cost_usd=0.0,
            diagnostics={"extraction_mode": "category_decomposed"},
            known_entity_mentions={
                "schema": "dmb_known_entity_mention_sidecar_v0",
                "version": "0.1",
                "campaign_id": options.campaign_id,
                "session_id": options.session_id,
                "mentions": [],
                "ambiguous_surfaces": [],
                "diagnostics": {"mention_count": 0, "empty_contract": True},
            },
        )

    monkeypatch.setattr(prod_runner, "extract_category_candidate_graph", fake_extract)


def test_recap_ingest_build_graph_preview_bundle_with_extract_graph_fake_client(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "graph_model_id": "gpt-5.4-mini",
        },
    )

    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "category_decomposed"
    assert graph["model_id"] == "gpt-5.4-mini"
    assert graph["candidate_node_count"] >= 1
    assert (ROOT / graph["candidate_graph_path"]).is_file()

    run_id = graph["extraction_run_id"]
    assert run_id
    run = get_extraction_run(ROOT, run_id)
    assert run.status in {ExtractionRunStatus.REVIEWABLE, ExtractionRunStatus.FAILED}
    assert run.status == ExtractionRunStatus.REVIEWABLE
    assert run.source_artifact_id == graph["source_artifact_id"]
    candidate = json.loads((ROOT / graph["candidate_graph_path"]).read_text(encoding="utf-8"))
    assert run.source_artifact_id in (candidate.get("source_artifact_ids") or [])
    for node in candidate.get("nodes") or []:
        for ref in node.get("evidence_refs") or []:
            assert ref.get("source_artifact_id") == run.source_artifact_id


def test_recap_ingest_typed_validation_failure_blocks_candidate_and_preview_union(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A typed-validation-failed candidate must not become candidate-ready or materialize."""
    import src.graph_memory.extraction.graph_preview_runner as prod_runner
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionResult,
    )

    client, _corpus, _candidate = client_env
    _prepare_normalized(client)

    def fake_invalid_extract(options, *, client=None, progress_callback=None):  # noqa: ANN001
        spans = list(options.source_span_index.get("spans") or [])
        spref = "invalid-span"
        for span in spans:
            if not isinstance(span, dict):
                continue
            candidate = str(
                span.get("source_span_id")
                or span.get("source_span_ref_id")
                or span.get("span_id")
                or ""
            ).strip()
            if candidate:
                spref = candidate
                break
        artifact = str(
            options.source_artifact_id
            or options.source_span_index.get("source_artifact_id")
            or "artifact:missing"
        ).strip()
        graph = _live_extraction_payload(source_artifact_id=artifact, spref=spref)
        for node in graph.get("nodes") or []:
            if isinstance(node, dict):
                node["semantic_state"] = {
                    "canon_state": "not_a_valid_canon_state",
                    "lifecycle_state": "candidate",
                    "evidence_role": "source_evidence",
                    "authority_state": "llm_generated",
                    "visibility_state": "unknown",
                }
        return CategoryGraphExtractionResult(
            candidate_graph=graph,
            envelope={"candidate_graph": graph},
            pass_outputs={},
            pass_telemetry={},
            consolidation_diagnostics={},
            model_id=options.model_id or "gpt-5.4-mini",
            total_cost_usd=0.0,
            diagnostics={"extraction_mode": "category_decomposed"},
            known_entity_mentions={
                "schema": "dmb_known_entity_mention_sidecar_v0",
                "version": "0.1",
                "campaign_id": options.campaign_id,
                "session_id": options.session_id,
                "mentions": [],
                "ambiguous_surfaces": [],
                "diagnostics": {"mention_count": 0, "empty_contract": True},
            },
        )

    monkeypatch.setattr(prod_runner, "extract_category_candidate_graph", fake_invalid_extract)

    build = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "force_graph_run": True,
            "graph_model_id": "gpt-5.4-mini",
        },
    )
    assert build.status_code == 200
    graph = build.json()["ingest_report"]["graph_preview"]
    assert graph["status"] != "candidate_validation_ready"
    assert graph["status"] != "preview_union_store_ready"
    assert graph["extraction_run_status"] == "failed"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"]
    assert "validation" in graph["blocked_reason"].lower() or "typed" in graph[
        "blocked_reason"
    ].lower() or "semantic" in graph["blocked_reason"].lower()
    assert graph.get("preview_union_store_path") in (None, "")

    materialize = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "force_graph_run": True,
            "materialize_after_extract": True,
            "graph_model_id": "gpt-5.4-mini",
        },
    )
    assert materialize.status_code == 200
    mat_graph = materialize.json()["ingest_report"]["graph_preview"]
    assert mat_graph["status"] != "preview_union_store_ready"
    assert mat_graph["extraction_run_status"] == "failed"
    assert mat_graph.get("preview_union_store_path") in (None, "")
    assert mat_graph["can_open_union_graph"] is False


def test_recap_ingest_packaged_span_index_resolves_evidence_for_surface(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every candidate EvidenceRef must resolve against the packaged canonical span index."""
    from apps.live_control_server.services.graph_preview_surface import (
        _enrich_evidence_ref,
        _span_lookup_key,
    )
    from src.graph_memory.source_span import (
        SOURCE_SPAN_INDEX_SCHEMA,
        source_span_index_from_dict,
    )

    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "graph_model_id": "gpt-5.4-mini",
        },
    )
    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    run_dir = ROOT / graph["run_dir"]
    candidate = json.loads((ROOT / graph["candidate_graph_path"]).read_text(encoding="utf-8"))
    span_index_path = run_dir / "source_span_index.json"
    span_index = json.loads(span_index_path.read_text(encoding="utf-8"))
    assert span_index.get("schema") == SOURCE_SPAN_INDEX_SCHEMA
    assert span_index.get("source_artifact_id") == graph["source_artifact_id"]
    # Canonical v1 loader must accept the packaged file (no invented :full_text entries).
    validated = source_span_index_from_dict(span_index)
    assert validated.source_artifact_id == graph["source_artifact_id"]
    assert validated.spans
    assert all(":span:" in span.source_span_id for span in validated.spans)
    assert not any(
        str(span.get("source_span_id") or "").endswith(":full_text")
        for span in (span_index.get("spans") or [])
        if isinstance(span, dict)
    )

    manifest = json.loads((ROOT / graph["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["source"]["source_artifact_id"] == graph["source_artifact_id"]
    assert (
        manifest["artifacts"]["source_span_index"]["schema"] == SOURCE_SPAN_INDEX_SCHEMA
    )
    provenance = json.loads((run_dir / "provenance_index.json").read_text(encoding="utf-8"))
    assert all(
        row.get("artifact_id") == graph["source_artifact_id"]
        for row in provenance.get("source_artifacts") or []
        if isinstance(row, dict)
    )
    assert graph["source_artifact_id"] in (candidate.get("source_artifact_ids") or [])
    assert (run_dir / "source_spans" / "recap_full_text.md").is_file()

    span_lookup = {
        key: sp
        for sp in span_index.get("spans") or []
        if isinstance(sp, dict)
        for key in [_span_lookup_key(sp)]
        if key is not None
    }
    recap_text = (run_dir / "source_spans" / "recap_full_text.md").read_text(encoding="utf-8")
    recap_path = graph.get("normalized_recap_path") or ""

    evidence_refs = []
    for collection in ("nodes", "edges", "beats", "ignored_items", "deferred_items"):
        for item in candidate.get(collection) or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or item.get("title") or "")
            for ref in item.get("evidence_refs") or []:
                if isinstance(ref, dict):
                    evidence_refs.append((ref, label))
    assert evidence_refs

    for ref, label in evidence_refs:
        enriched = _enrich_evidence_ref(
            ref,
            span_lookup=span_lookup,
            recap_text=recap_text,
            recap_path=recap_path,
            entity_label=label or None,
        )
        assert enriched.source_artifact_id == graph["source_artifact_id"]
        assert enriched.source_span_ref_id
        assert enriched.source_span_ref_id in span_lookup
        assert enriched.paragraph_text and enriched.paragraph_text.strip()
        assert enriched.line_start is not None and enriched.line_start >= 1
        assert enriched.line_end is not None and enriched.line_end >= enriched.line_start
        assert enriched.can_highlight_span is True or enriched.anchor_quote_matches
        assert enriched.anchor_quotes or enriched.anchor_quote_matches


def test_recap_ingest_materialize_preview_supergraph_extracts_without_candidate_path(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    _patch_retired_union_materialize(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "materialize_after_extract": True,
        },
    )

    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "category_decomposed"
    assert graph["candidate_graph_path"] is not None
    from apps.live_control_server.services.graph_run_registry import get_extraction_run

    run = get_extraction_run(ROOT, graph["extraction_run_id"])
    assert run.source_artifact_id == graph["source_artifact_id"]


def test_recap_ingest_extract_graph_missing_api_key_returns_llm_blocked(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "src.graph_memory.extraction.category_candidate_graph_extractor.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "extract_graph": True,
            "force_graph_run": True,
        },
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"]
    assert graph["can_open_union_graph"] is False


def test_recap_ingest_rejects_candidate_path_with_extract_graph(
    client_env: tuple[TestClient, Path, Path]
) -> None:
    client, _corpus, candidate = client_env
    _prepare_normalized(client)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_graph_preview_bundle",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": candidate.relative_to(ROOT).as_posix(),
            "extract_graph": True,
        },
    )

    assert response.status_code == 422
    assert "cannot be combined" in response.json()["detail"]


def test_recap_ingest_generate_recap_memory_without_graph_extraction(
    client_env: tuple[TestClient, Path, Path]
) -> None:
    client, _corpus, _candidate = client_env

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": False,
            "include_legacy_breadcrumb": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "session_memory_materialized" in body["states"]
    assert "graph_preview" not in body["ingest_report"]


def test_recap_ingest_generate_recap_memory_with_graph_extraction_fake_client(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus, _candidate = client_env
    _patch_fake_category_extract(monkeypatch)
    _patch_retired_union_materialize(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": True,
            "graph_model_id": "gpt-5.4-mini",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "graph_candidate_ready" in body["states"]
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "category_decomposed"
    assert graph["model_id"] == "gpt-5.4-mini"
    assert "legacy_breadcrumb_skipped" in " ".join(body["warnings"])


def test_generate_recap_memory_reuses_preview_graph_without_force(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    _patch_retired_union_materialize(monkeypatch)

    payload = {
        "operation": "generate_recap_memory",
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road Dogfood",
        "check": True,
        "include_graph_extraction": True,
        "graph_model_id": "gpt-5.4-mini",
    }
    first = client.post("/api/live/recap-ingest", json=payload)
    assert first.status_code == 200, first.text
    first_graph = first.json()["ingest_report"]["graph_preview"]
    assert first_graph["status"] == "candidate_validation_ready"
    first_manifest = first_graph["manifest_path"]

    second = client.post("/api/live/recap-ingest", json=payload)
    assert second.status_code == 200, second.text
    second_graph = second.json()["ingest_report"]["graph_preview"]
    assert second_graph["manifest_path"] == first_manifest


def test_generate_recap_memory_force_graph_run_starts_new_preview_run(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus, _candidate = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    _patch_retired_union_materialize(monkeypatch)

    payload = {
        "operation": "generate_recap_memory",
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road Dogfood",
        "check": True,
        "include_graph_extraction": True,
        "graph_model_id": "gpt-5.4-mini",
    }
    first = client.post("/api/live/recap-ingest", json=payload)
    assert first.status_code == 200, first.text
    first_manifest = first.json()["ingest_report"]["graph_preview"]["manifest_path"]

    forced = client.post("/api/live/recap-ingest", json={**payload, "force_graph_run": True})
    assert forced.status_code == 200, forced.text
    forced_graph = forced.json()["ingest_report"]["graph_preview"]
    assert forced_graph["status"] == "candidate_validation_ready"
    assert forced_graph["manifest_path"] != first_manifest


def test_generate_recap_memory_reuses_staged_notes_and_still_materializes_graph(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, corpus, _candidate = client_env
    _patch_fake_category_extract(monkeypatch)
    _patch_retired_union_materialize(monkeypatch)
    staged = corpus / "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md"
    staged.write_text(
        "Session 22 Recap\n\nBonogo scouts the Mireward road and regroups at dusk.",
        encoding="utf-8",
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Different pasted text should not replace staged notes.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": True,
            "graph_model_id": "gpt-5.4-mini",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "staged_raw_notes_conflict" in body["states"]
    assert "graph_candidate_ready" in body["states"]
    assert body["ingest_report"]["staged_raw_notes_reused_existing"] is True
    assert "Different pasted text" not in staged.read_text(encoding="utf-8")
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"


def test_recap_ingest_generate_recap_memory_with_blocked_graph_preserves_recap_success(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.graph_memory.extraction.graph_preview_runner as prod_runner

    client, _corpus, _candidate = client_env
    shutil.rmtree(ROOT / "out/graph_memory/runs/longmont-c2/session-22", ignore_errors=True)

    def fake_extract_blocked(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("test llm blocked")

    monkeypatch.setattr(prod_runner, "extract_category_candidate_graph", fake_extract_blocked)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "check": True,
            "include_graph_extraction": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_span_bundle_ready"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"] == "test llm blocked"
    assert any("preview graph extraction blocked" in warning for warning in body["warnings"])


def test_real_recap_manifest_adapts_to_extraction_run(
    client_env: tuple[TestClient, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: real recap preview producer manifest adapts to ExtractionRun."""
    from graph_memory.ingestion.graph_ingest_run import (
        GraphIngestRunManifest,
        adapt_recap_manifest_to_extraction_run,
    )

    client, corpus, candidate = client_env
    _prepare_normalized(client)
    _stamp_fixture_candidate(client, corpus, candidate)
    _patch_retired_union_materialize(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_preview_supergraph",
            "campaign_id": "longmont-c2",
            "session": 22,
            "candidate_graph_path": candidate.relative_to(ROOT).as_posix(),
        },
    )
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    manifest_path = ROOT / graph["manifest_path"]
    assert manifest_path.is_file()
    assert manifest_path.name == "graph_ingest_run_manifest.json"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = GraphIngestRunManifest.model_validate(payload)
    run = adapt_recap_manifest_to_extraction_run(manifest)

    assert run.run_id == manifest.run_id
    assert run.campaign_id == manifest.campaign_id == "longmont-c2"
    assert run.session_id == manifest.session_id
    assert run.source_domain == (manifest.source.source_domain or "recap")
    assert run.source_artifact_id == manifest.source.source_artifact_id
    assert run.source_artifact_id
    assert run.lineage["adapter"] == "graph_ingest_run_manifest_v0"
    assert run.lineage["legacy_status"] == manifest.status.value

    # Component mappings preserve recap artifact URIs and digests.
    assert "source_artifact" in run.components
    source_component = run.components["source_artifact"]
    assert source_component.uri in {
        manifest.source.input_path_record or "",
        manifest.source.normalized_recap_path or "",
    }
    assert source_component.sha256 == manifest.source.normalized_recap_sha256

    role_to_component = {
        "source_span_index": "source_span_index",
        "candidate_graph": "candidate_graph",
        "candidate_validation_report": "validation_report",
        "pass_outputs": "pass_outputs",
        "pass_telemetry": "pass_telemetry",
        "consolidation_diagnostics": "consolidation_diagnostics",
        "raw_model_response": "raw_model_response",
        "provenance_index": "provenance_index",
    }
    for key, artifact in manifest.artifacts.items():
        mapped_key = role_to_component.get(key)
        if mapped_key is None:
            continue
        assert mapped_key in run.components, f"missing adapted component for manifest role {key}"
        mapped = run.components[mapped_key]
        assert mapped.uri == artifact.uri
        assert mapped.sha256 == artifact.sha256


@pytest.fixture
def recap_inspection_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str
) -> TestClient:
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_run_registry.repo_root",
        lambda: tmp_path,
        raising=False,
    )
    return TestClient(create_app())


def test_recap_inspection_route_returns_validated_source(
    recap_inspection_client: TestClient, tmp_path: Path
) -> None:
    from tests.test_graph_run_registry import _validated_recap_run

    run, _artifact, _source_path = _validated_recap_run(tmp_path)
    response = recap_inspection_client.get(
        f"/api/live/graph-preview/extraction-runs/{run.run_id}/recap-inspection"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_historical_recap_inspection_v1"
    assert body["runId"] == run.run_id
    assert body["runStatus"] == "validated"
    assert body["sourceStatus"] == "available"
    assert "Session Recap" in (body.get("sourceProse") or "")


def test_recap_inspection_route_reads_durable_source_when_file_missing(
    recap_inspection_client: TestClient, tmp_path: Path
) -> None:
    from tests.test_graph_run_registry import _validated_recap_run

    run, _artifact, source_path = _validated_recap_run(tmp_path)
    source_path.unlink()
    response = recap_inspection_client.get(
        f"/api/live/graph-preview/extraction-runs/{run.run_id}/recap-inspection"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sourceStatus"] == "available"
    assert "Session Recap" in (body.get("sourceProse") or "")


def test_recap_inspection_route_unknown_run_404(recap_inspection_client: TestClient) -> None:
    response = recap_inspection_client.get(
        "/api/live/graph-preview/extraction-runs/not-a-real-run/recap-inspection"
    )
    assert response.status_code == 404


def test_recap_inspection_route_rejects_worldbuilding(
    recap_inspection_client: TestClient, tmp_path: Path
) -> None:
    from apps.live_control_server.services.graph_run_registry import create_extraction_run
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )

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
    committed = mark_workspace_document_committed(
        tmp_path, record.document_id, expected_revision=1
    )
    target = tmp_path / committed.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Lore\n\nBody.\n", encoding="utf-8")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    response = recap_inspection_client.get(
        f"/api/live/graph-preview/extraction-runs/{run.run_id}/recap-inspection"
    )
    assert response.status_code == 422
    assert "not applicable" in response.json()["detail"]
