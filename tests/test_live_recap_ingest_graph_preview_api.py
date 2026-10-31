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


@pytest.fixture(autouse=True)
def _declared_local_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str) -> str:
    return application_state_dsn


def _write_synthetic_session(tmp_path: Path) -> None:
    """Create minimal synthetic session state for the database-backed route test."""
    packet = {
        "schema_version": "0.1.0",
        "campaign_id": "synthetic-campaign",
        "session": 1,
        "packet_id": "packet:synthetic-session",
        "created_at": "2026-10-28T00:00:00Z",
        "source_paths": [{"path": "synthetic-recap.md", "role": "fixture"}],
        "latency_modes": [],
        "known_roll_tables": [],
        "current_state_seed": {
            "day_label": "Synthetic Day One",
            "party_position": "Synthetic Test Room",
            "route_intent": "Exercise recap routing",
            "active_weather": None,
            "next_suggested_beat": None,
        },
        "open_loops": [],
        "roll_stack": [],
        "surface_catalog": [
            {
                "module_id": "chat",
                "title": "Synthetic Chat",
                "default_slot": "main",
                "required": True,
                "enabled_by_default": True,
            },
            {
                "module_id": "record",
                "title": "Synthetic Record",
                "default_slot": "sidebar",
                "required": True,
                "enabled_by_default": True,
            },
        ],
    }
    layout = {
        "schema_version": "0.1.0",
        "layout_version": 1,
        "updated_at": "2026-10-28T00:00:00Z",
        "campaign_id": "synthetic-campaign",
        "session": 1,
        "modules": [
            {
                "module_id": "chat",
                "slot": "main",
                "order": 0,
                "enabled": True,
                "collapsed": False,
            },
            {
                "module_id": "record",
                "slot": "sidebar",
                "order": 0,
                "enabled": True,
                "collapsed": False,
            },
        ],
    }
    initial_state = {
        "schema_version": "0.1.0",
        "campaign_id": "synthetic-campaign",
        "session": 1,
        "derived": True,
        "authoritative": False,
        "derived_from": ["live_packet.json", "surface_layout.json"],
        "generated_at": "2026-10-28T00:00:00Z",
    }
    for filename, value in (
        ("live_packet.json", packet),
        ("surface_layout.json", layout),
        ("current_state.json", initial_state),
    ):
        (tmp_path / filename).write_text(
            json.dumps(value, sort_keys=True) + "\n", encoding="utf-8"
        )


@pytest.fixture
def client_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path]:
    from apps.live_control_server.services import recap_ingest_context

    # Keep every repo-relative source/run/Graph fixture under this test's
    # disposable root. Never clear or populate the checkout's own out/ tree.
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest.repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path
    )
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    graph_root = tmp_path / "out"
    graph_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(graph_root))

    class FakeContext:
        def as_lineage(self) -> dict[str, object]:
            return {
                "schema": "dm_world_campaign_ingest_context_v1",
                "managed_world_id": "elderwyld",
                "native_world_id": "world:elderwyld",
                "binding_version": 3,
                "campaign_id": "longmont-c2",
                "head_revision_id": "rev:observed-head",
                "graph_schema": "dm_graph_v1",
                "graph_payload_sha256": "a" * 64,
            }

    monkeypatch.setattr(
        recap_ingest_context,
        "read_recap_ingest_context",
        lambda **_kwargs: FakeContext(),
    )
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

    from tests.test_recap_managed_standing_context import seed_binding
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    seed_binding(tmp_path, "elderwyld", "world:elderwyld", version=3)

    try:
        yield TestClient(create_app(), client=("127.0.0.1", 50000)), corpus
    finally:
        shutil.rmtree(graph_runs, ignore_errors=True)


@pytest.fixture
def synthetic_client_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, Path]:
    from apps.live_control_server.services import recap_ingest_context

    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest.repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path
    )
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    graph_root = tmp_path / "out"
    graph_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(graph_root))

    from tests.test_recap_managed_standing_context import seed_binding
    seed_binding(tmp_path,"synthetic-world","world:synthetic-world",version=3)

    class FakeContext:
        def as_lineage(self) -> dict[str, object]:
            return {
                "schema": "dm_world_campaign_ingest_context_v1",
                "managed_world_id": "synthetic-world",
                "native_world_id": "world:synthetic-world",
                "binding_version": 3,
                "campaign_id": "synthetic-campaign",
                "head_revision_id": "rev:synthetic-head",
                "graph_schema": "dm_graph_v1",
                "graph_payload_sha256": "a" * 64,
            }

    monkeypatch.setattr(
        recap_ingest_context,
        "read_recap_ingest_context",
        lambda **_kwargs: FakeContext(),
    )
    _write_synthetic_session(tmp_path)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))

    corpus = tmp_path / "external-corpus"
    graph_runs = tmp_path / "out/graph_memory/runs/synthetic-campaign/session-1"
    source_registry = tmp_path / "out/registries"
    campaign = corpus / "Synthetic Campaign"
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(CORPUS_ENV, str(corpus))
    monkeypatch.setenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", "out/graph_memory/runs")

    try:
        yield TestClient(create_app(), client=("127.0.0.1", 50000)), corpus
    finally:
        shutil.rmtree(graph_runs, ignore_errors=True)
        shutil.rmtree(source_registry, ignore_errors=True)


def _prepare_normalized(client: TestClient) -> None:
    raw = "Session 22 Recap\n\nThe group scouts the Mireward road and regroups at dusk."
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": raw,
            "slug": "Mireward Road Dogfood",
            "include_graph_extraction": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["paths"]["normalized_recap"]


def test_recap_graph_ingest_requires_world_context_before_staging_or_source_registration(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, corpus = client_env
    from apps.live_control_server.routes import recap_ingest

    registry = ROOT / "out/registries/source_artifacts.json"
    registry_before = registry.read_bytes() if registry.exists() else None
    calls = []
    monkeypatch.setattr(recap_ingest, "run_pipeline", lambda *args, **kwargs: calls.append((args, kwargs)))
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nA new recap.",
            "slug": "New Mireward Road Recap",
            "include_graph_extraction": True,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "managed_world_context_required"
    assert calls == []
    assert not list(corpus.rglob("*.md"))
    assert (registry.read_bytes() if registry.exists() else None) == registry_before


def test_uninitialized_world_stops_before_recap_staging_or_source_registration(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, corpus = client_env
    from apps.live_control_server.routes import recap_ingest
    from apps.live_control_server.services import recap_ingest_context

    registry = ROOT / "out/registries/source_artifacts.json"
    registry_before = registry.read_bytes() if registry.exists() else None
    calls = []
    monkeypatch.setattr(recap_ingest, "run_pipeline", lambda *args, **kwargs: calls.append((args, kwargs)))

    def uninitialized(**_kwargs):
        raise recap_ingest_context.RecapIngestContextError(
            "World Graph is not initialized.",
            code="world_graph_not_initialized",
            status_code=409,
        )

    monkeypatch.setattr(recap_ingest_context, "read_recap_ingest_context", uninitialized)
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nA new recap.",
            "slug": "New Mireward Road Recap",
            "include_graph_extraction": True,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "world_graph_not_initialized"
    assert calls == []
    assert not list(corpus.rglob("*.md"))
    assert (registry.read_bytes() if registry.exists() else None) == registry_before














def _live_extraction_payload(*, source_artifact_id: str, spref: str, corpus_root: Path, source_text: str, span_index: dict, location_label: str = "Mireward road") -> dict:
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        minimal_category_pass_outputs,
    )
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        FixtureCategoryGraphPassClient,
        run_category_pipeline,
    )

    # Bind the quote to its actual paragraph, never the generated frontmatter.
    lines = source_text.splitlines()
    matches = [span["source_span_id"] for span in span_index["spans"]
        if location_label in "\n".join(lines[span["start_line"] - 1:span["end_line"]])]
    assert matches, "synthetic fixture must quote a real source paragraph"
    spref = matches[0]
    # Exercise packaging with one location actually named in these source fixtures.
    # Keep the fake independent of the checkout's real standing-party registry.
    outputs = minimal_category_pass_outputs(spref, node_label=location_label, node_id="node:fixture-location")
    node = outputs["actor_pass"]["observation_nodes"][0]
    node["node_type"] = "location"
    outputs["actor_pass"] = {"observation_nodes": []}
    outputs["location_pass"] = {"observation_nodes": [node]}
    outputs["beat_pass"] = {"observation_beats": []}
    result = run_category_pipeline(
        FixtureCategoryGraphPassClient(outputs),
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-22",
            session_number=22,
            source_span_index=span_index,
            source_text=source_text,
            source_artifact_id=source_artifact_id,
            source_ref_id=f"{source_artifact_id}:text",
            model_id="gpt-5.4-mini",
            corpus_root=corpus_root,
            enable_party_claimed_fill=False,
        ),
    )
    graph = result.candidate_graph
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


def _patch_fake_category_extract(monkeypatch: pytest.MonkeyPatch, *, location_label: str = "Mireward road") -> None:
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
        graph = _live_extraction_payload(source_artifact_id=artifact, spref=spref, corpus_root=options.corpus_root, source_text=options.source_text, span_index=dict(options.source_span_index), location_label=location_label)
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
            model_id=options.model_id or "deepseek/deepseek-v4.1-flash-1017",
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


def test_process_extracts_canonical_graph_with_fake_client(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )

    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "category_decomposed"
    assert graph["model_id"] == "deepseek/deepseek-v4.1-flash-1017"
    assert graph["candidate_node_count"] >= 1

    run_id = graph["extraction_run_id"]
    assert run_id
    run = get_extraction_run(ROOT, run_id)
    assert run.status in {ExtractionRunStatus.REVIEWABLE, ExtractionRunStatus.FAILED}
    assert run.status == ExtractionRunStatus.REVIEWABLE
    assert run.source_artifact_id == graph["source_artifact_id"]
    assert run.lineage["world_campaign_ingest_context"]["head_revision_id"] == "rev:observed-head"
    from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
    data = load_reviewable_extraction_data(ROOT, graph["extraction_run_id"])
    candidate = json.loads(data.candidate_bytes)
    assert run.source_artifact_id in (candidate.get("source_artifact_ids") or [])
    for node in candidate.get("nodes") or []:
        for ref in node.get("evidence_refs") or []:
            assert ref.get("source_artifact_id") == run.source_artifact_id


def test_recap_ingest_typed_validation_failure_blocks_candidate_and_preview_union(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A typed-validation-failed candidate must not become candidate-ready or materialize."""
    import src.graph_memory.extraction.graph_preview_runner as prod_runner
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionResult,
    )

    client, _corpus = client_env
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
        graph = _live_extraction_payload(source_artifact_id=artifact, spref=spref, corpus_root=options.corpus_root, source_text=options.source_text, span_index=dict(options.source_span_index))
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
            model_id=options.model_id or "deepseek/deepseek-v4.1-flash-1017",
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
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

            "force_graph_run": True,
            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )
    assert build.status_code == 200
    graph = build.json()["ingest_report"]["graph_preview"]
    assert graph["status"] != "candidate_validation_ready"
    assert graph["status"] != "preview_union_store_ready"
    assert graph["extraction_run_status"] == "failed"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"]
    assert graph["blocked_reason"] == "The saved extraction did not complete. Review the attempt before retrying."
    assert graph.get("preview_union_store_path") in (None, "")

    materialize = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

            "force_graph_run": True,
            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )
    assert materialize.status_code == 200
    mat_graph = materialize.json()["ingest_report"]["graph_preview"]
    assert mat_graph["status"] != "preview_union_store_ready"
    assert mat_graph["extraction_run_status"] == "failed"
    assert mat_graph.get("preview_union_store_path") in (None, "")
    assert not mat_graph.get("can_open_union_graph")


def test_recap_ingest_database_span_index_resolves_evidence_for_surface(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every candidate EvidenceRef resolves against the saved canonical span index."""
    from apps.live_control_server.services.graph_preview_surface import (
        _enrich_evidence_ref,
        _span_lookup_key,
    )
    from src.graph_memory.source_span import (
        SOURCE_SPAN_INDEX_SCHEMA,
        source_span_index_from_dict,
    )

    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )
    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
    data = load_reviewable_extraction_data(ROOT, graph["extraction_run_id"])
    candidate = json.loads(data.candidate_bytes)
    span_index = json.loads(data.span_bytes)
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

    assert graph["source_artifact_id"] in candidate["source_artifact_ids"]

    span_lookup = {
        key: sp
        for sp in span_index.get("spans") or []
        if isinstance(sp, dict)
        for key in [_span_lookup_key(sp)]
        if key is not None
    }
    recap_text = data.source_bytes.decode("utf-8")
    recap_path = ""

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


def test_recap_ingest_extracts_without_candidate_path(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

        },
    )

    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "category_decomposed"
    assert "candidate_graph_path" not in graph
    from apps.live_control_server.services.graph_run_registry import get_extraction_run

    run = get_extraction_run(ROOT, graph["extraction_run_id"])
    assert run.source_artifact_id == graph["source_artifact_id"]


def test_extraction_restarts_when_selected_world_binding_changes(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services import recap_ingest_context
    from apps.live_control_server.services.graph_run_registry import get_extraction_run

    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    build = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )
    assert build.status_code == 200, build.text
    original = build.json()["ingest_report"]["graph_preview"]["extraction_run_id"]

    class ReboundContext:
        def as_lineage(self) -> dict[str, object]:
            return {
                "schema": "dm_world_campaign_ingest_context_v1",
                "managed_world_id": "elderwyld",
                "native_world_id": "world:elderwyld-rebound",
                "binding_version": 4,
                "campaign_id": "longmont-c2",
                "head_revision_id": "rev:next-head",
                "graph_schema": "dm_graph_v1",
                "graph_payload_sha256": "b" * 64,
            }

    monkeypatch.setattr(
        recap_ingest_context,
        "read_recap_ingest_context",
        lambda **_kwargs: ReboundContext(),
    )
    from tests.test_recap_managed_standing_context import seed_binding
    seed_binding(ROOT, "elderwyld", "world:elderwyld-rebound", version=4)
    materialized = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

        },
    )
    assert materialized.status_code == 200, materialized.text
    graph = materialized.json()["ingest_report"]["graph_preview"]
    assert graph["extraction_run_id"] != original
    run = get_extraction_run(ROOT, graph["extraction_run_id"])
    assert run.lineage["world_campaign_ingest_context"]["native_world_id"] == "world:elderwyld-rebound"


def test_recap_ingest_extract_graph_missing_api_key_returns_llm_blocked(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus = client_env
    _prepare_normalized(client)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "src.graph_memory.extraction.category_candidate_graph_extractor.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,

            "force_graph_run": True,
        },
    )

    assert response.status_code == 200
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "failed"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"]
    assert not graph.get("can_open_union_graph")




def test_recap_ingest_generate_recap_memory_without_graph_extraction(
    client_env: tuple[TestClient, Path]
) -> None:
    client, _corpus = client_env

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "include_graph_extraction": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "normalized_current" in body["states"]
    assert not any("breadcrumb" in state or "session_memory" in state for state in body["states"])
    assert "graph_preview" not in body["ingest_report"]


def test_recap_ingest_generate_recap_memory_with_graph_extraction_fake_client(
    synthetic_client_env: tuple[TestClient, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from application_state.source import service as source_service
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    from apps.live_control_server.services.source_artifact_registry import get_source_artifact
    from apps.live_control_server.services import historical_recap_world_projection
    from apps.live_control_server.services import corpus_normalized_recap
    from apps.live_control_server.services.world_container_registry import (
        NativeGraphBindingRecord,
        WorldContainerRecord,
    )
    from graph_memory.projection.world_projection import (
        WorldGraphProjection,
        WorldGraphProjectionFocus,
        WorldGraphProjectionNodeView,
        WorldGraphProjectionSnapshot,
        WorldGraphProjectionSummary,
        WorldGraphProjectionTrustBoundary,
    )
    from src.corpus import session_recap_paths
    from src.live_play import planning_corpus_manifest, recap_stage_paths
    from src.live_play.recap_stage_paths import RecapStagePaths

    client, corpus = synthetic_client_env
    _patch_fake_category_extract(monkeypatch, location_label="test location")

    def synthetic_campaign_number(campaign_id: str) -> int:
        assert campaign_id == "synthetic-campaign"
        return 1

    def synthetic_session_recaps_prefix(campaign_number: int) -> str:
        assert campaign_number == 1
        return "Synthetic Campaign/Session Recaps"

    monkeypatch.setattr(
        session_recap_paths, "campaign_number_from_id", synthetic_campaign_number
    )
    monkeypatch.setattr(
        recap_stage_paths, "campaign_number_from_id", synthetic_campaign_number
    )
    monkeypatch.setattr(
        corpus_normalized_recap,
        "campaign_number_from_id",
        synthetic_campaign_number,
    )
    monkeypatch.setattr(
        planning_corpus_manifest,
        "campaign_number_from_id",
        synthetic_campaign_number,
    )
    monkeypatch.setattr(
        session_recap_paths, "session_recaps_prefix", synthetic_session_recaps_prefix
    )
    monkeypatch.setattr(
        recap_stage_paths,
        "session_recaps_prefix",
        synthetic_session_recaps_prefix,
    )
    monkeypatch.setattr(
        planning_corpus_manifest,
        "session_recaps_prefix",
        synthetic_session_recaps_prefix,
    )
    monkeypatch.setattr(recap_stage_paths, "corpus_root", lambda: corpus)
    monkeypatch.setattr(corpus_normalized_recap, "corpus_root", lambda: corpus)

    def synthetic_stage_paths(
        cls, *, campaign_id: str, session: int, slug_tail: str
    ) -> RecapStagePaths:
        base = "Synthetic Campaign"
        prefix = f"{base}/Session Recaps"
        canonical_basename = f"Session {session} - {slug_tail}"
        return cls(
            campaign_id=campaign_id,
            campaign_number=1,
            campaign_root_rel=base,
            staged_raw_notes_rel=f"{base}/_ingest_staging/session_{session}_raw_notes.md",
            canonical_recap_rel=f"{prefix}/{canonical_basename}.md",
            canonical_basename=canonical_basename,
            normalized_recap_rel=f"{prefix}/_normalized/Session {session:02d} - {slug_tail}.md",
            frontmatter_seed_rel=f"{prefix}/_breadcrumbed/{canonical_basename}.frontmatter_seed.md",
            breadcrumbed_recap_rel=f"{prefix}/_breadcrumbed/{canonical_basename}.breadcrumbed.md",
            session_memory_jsonl_rel=f"{prefix}/_session_memory/{canonical_basename}.records_meta.jsonl",
            session_memory_meta_rel=f"{prefix}/_session_memory/{canonical_basename}.records_meta.json",
        )

    monkeypatch.setattr(RecapStagePaths, "build", classmethod(synthetic_stage_paths))

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "synthetic-campaign",
            "managed_world_id": "synthetic-world",
            "session": 1,
            "raw_text": "Synthetic recap\n\nA group explores a test location.",
            "slug": "Synthetic Recap",
            "include_graph_extraction": True,
            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] != "ready_for_planning_activation"
    assert "graph_candidate_ready" in body["states"]
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    assert graph["extraction_mode"] == "category_decomposed"
    assert graph["model_id"] == "deepseek/deepseek-v4.1-flash-1017"
    assert not any("breadcrumb" in warning.lower() for warning in body["warnings"])

    # End-to-end boundary: ordinary Process creates canonical recap/source,
    # immutable graph candidate, APP-STATE source, and an exact-run
    # historical projection against that source's native World.
    run = get_extraction_run(ROOT, graph["extraction_run_id"])
    artifact = get_source_artifact(ROOT, run.source_artifact_id)
    assert artifact.source_artifact_id.startswith("artifact:recap:v2:")
    assert artifact.world_id == "world:synthetic-world"
    assert run.lineage["world_campaign_ingest_context"]["native_world_id"] == artifact.world_id
    from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
    assert load_reviewable_extraction_data(ROOT, run.run_id).candidate_bytes
    assert "manifest_path" not in graph and "candidate_graph_path" not in graph

    source = source_service.get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256 or "",
    )
    assert source is not None
    assert source.world_id == artifact.world_id
    normalized_path = Path(body["paths"]["normalized_recap"])
    if not normalized_path.is_absolute():
        normalized_path = corpus / normalized_path
    assert source.markdown == normalized_path.read_text(encoding="utf-8")

    observed: dict[str, object] = {}

    def project_fixture(request, *, root):  # noqa: ANN001
        observed["request"] = request
        return WorldGraphProjection(
            schema="dmb_world_graph_projection_v1",
            snapshot=WorldGraphProjectionSnapshot(
                world_id=request.world_id,
                campaign_id=request.campaign_id,
                revision_id="fixture-world-head",
                head_revision_id="fixture-world-head",
                is_head=True,
                focus=WorldGraphProjectionFocus(
                    kind="session",
                    campaign_id=request.campaign_id,
                    session_id="session-1",
                ),
                admissibility="gm",
                scope_mode="campaign",
            ),
            summary=WorldGraphProjectionSummary(
                node_count=1,
                relationship_count=0,
                attribute_count=0,
                evidence_count=0,
                source_artifact_count=1,
            ),
            nodes=[
                WorldGraphProjectionNodeView(
                    node_id="node:test-location",
                    label="Test Location",
                    kind="location",
                    role="place",
                    summary="A synthetic place in the fixture projection.",
                    source_artifact_ids=[artifact.source_artifact_id],
                )
            ],
            trust_boundary=WorldGraphProjectionTrustBoundary(
                can_trust=["synthetic fixture World snapshot"],
                cannot_trust=["real World graph admission"],
            ),
        )

    monkeypatch.setattr(
        historical_recap_world_projection, "project_world_graph", project_fixture
    )
    monkeypatch.setattr("apps.live_control_server.routes.graph_preview.repo_root", lambda: ROOT)
    managed_root = tmp_path / "managed-worlds"
    world_source_root = managed_root / "corpus/synthetic-world-markdown"
    world_source_root.mkdir(parents=True)
    from tests.application_state.world_catalog_fixtures import store_world
    store_world(WorldContainerRecord(
                        world_id="synthetic-world",
                        name="Synthetic World",
                        source_root_relpath="corpus/synthetic-world-markdown",
                        created_at="2026-01-01T00:00:00Z",
                        owner_subject="subject:synthetic-owner",
                        native_graph_binding=NativeGraphBindingRecord(
                            native_world_id="world:synthetic-world",
                            status="active",
                            binding_version=3,
                            validated_at="2026-01-01T00:00:00Z",
                            validated_head_revision_id="rev:observed-head",
                        ),
                    ))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(managed_root))
    projection = client.get(
        f"/api/live/graph-preview/extraction-runs/{run.run_id}/recap-projection"
        "?managed_world_id=synthetic-world"
    )
    assert projection.status_code == 200, projection.text
    projected = projection.json()
    assert projected["worldId"] == "world:synthetic-world"
    assert projected["managedWorldId"] == "synthetic-world"
    assert projected["bindingVersion"] == 3
    assert projected["sourceArtifactId"] == artifact.source_artifact_id
    assert projected["nodeViews"]["node:test-location"]["label"] == "Test Location"
    assert observed["request"].world_id == "world:synthetic-world"


def test_generate_recap_memory_reuses_preview_graph_without_force(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    payload = {
        "operation": "generate_recap_memory",
        "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld",
        "session": 22,
        "slug": "Mireward Road Dogfood",
        "include_graph_extraction": True,
        "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
    }
    first = client.post("/api/live/recap-ingest", json=payload)
    assert first.status_code == 200, first.text
    first_graph = first.json()["ingest_report"]["graph_preview"]
    assert first_graph["status"] == "candidate_validation_ready"
    first_run = first_graph["extraction_run_id"]

    second = client.post("/api/live/recap-ingest", json=payload)
    assert second.status_code == 200, second.text
    second_graph = second.json()["ingest_report"]["graph_preview"]
    assert second_graph["extraction_run_id"] == first_run


def test_generate_recap_memory_force_graph_run_starts_new_preview_run(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)

    payload = {
        "operation": "generate_recap_memory",
        "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld",
        "session": 22,
        "slug": "Mireward Road Dogfood",
        "include_graph_extraction": True,
        "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
    }
    first = client.post("/api/live/recap-ingest", json=payload)
    assert first.status_code == 200, first.text
    first_run = first.json()["ingest_report"]["graph_preview"]["extraction_run_id"]

    forced = client.post("/api/live/recap-ingest", json={**payload, "force_graph_run": True})
    assert forced.status_code == 200, forced.text
    forced_graph = forced.json()["ingest_report"]["graph_preview"]
    assert forced_graph["status"] == "candidate_validation_ready"
    assert forced_graph["extraction_run_id"] != first_run


def test_generate_recap_memory_stops_on_staged_source_conflict(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, corpus = client_env
    _patch_fake_category_extract(monkeypatch)
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
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": "Different pasted text should not replace staged notes.",
            "slug": "Mireward Road Dogfood",
            "include_graph_extraction": True,
            "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] != "ready_for_planning_activation"
    assert "staged_raw_notes_conflict" in body["states"]
    assert "graph_candidate_ready" not in body["states"]
    assert "graph_preview" not in body["ingest_report"]
    assert "Different pasted text" not in staged.read_text(encoding="utf-8")


def test_recap_ingest_generate_recap_memory_with_blocked_graph_preserves_recap_success(
    client_env: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.graph_memory.extraction.graph_preview_runner as prod_runner

    client, _corpus = client_env
    shutil.rmtree(ROOT / "out/graph_memory/runs/longmont-c2/session-22", ignore_errors=True)

    def fake_extract_blocked(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("test llm blocked")

    monkeypatch.setattr(prod_runner, "extract_category_candidate_graph", fake_extract_blocked)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": "Session 22 Recap\n\nThe group scouts the Mireward road.",
            "slug": "Mireward Road Dogfood",
            "include_graph_extraction": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] != "ready_for_planning_activation"
    graph = body["ingest_report"]["graph_preview"]
    assert graph["status"] == "failed"
    assert graph["extraction_mode"] == "llm_blocked"
    assert graph["blocked_reason"] == "The saved extraction did not complete. Review the attempt before retrying."
    assert "test llm blocked" not in graph["blocked_reason"]
    assert any("preview graph extraction blocked" in warning for warning in body["warnings"])




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
    return TestClient(create_app(), client=("127.0.0.1", 50000))


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






def test_unmocked_candidate_completion_recovers_without_provider_replay(client_env, monkeypatch):
    import src.graph_memory.extraction.graph_preview_runner as production
    client, _corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    built = client.post("/api/live/recap-ingest", json={
        "operation": "generate_recap_memory", "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld",
        "session": 22,
        "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
    })
    assert built.status_code == 200, built.text
    initial = built.json()["ingest_report"]["graph_preview"]
    assert initial["status"] == "candidate_validation_ready"
    assert initial["extraction_run_status"] == "reviewable"

    from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
    data = load_reviewable_extraction_data(ROOT, initial["extraction_run_id"])
    assert data.run.source_artifact_id == initial["source_artifact_id"]
    shutil.rmtree(ROOT / "out/graph_memory", ignore_errors=True)

    def forbidden(*args, **kwargs):
        pytest.fail("Recovery must not dispatch a provider or invoke retired materialization")

    monkeypatch.setattr(production, "extract_category_candidate_graph", forbidden)
    request = {
        "operation": "generate_recap_memory",
        "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld",
        "session": 22,
        "include_graph_extraction": True,
        "graph_model_id": "deepseek/deepseek-v4.1-flash-1017",
    }
    for _ in range(2):
        response = client.post("/api/live/recap-ingest", json=request)
        assert response.status_code == 200, response.text
        body = response.json()
        graph = body["ingest_report"]["graph_preview"]
        assert graph["status"] == "candidate_validation_ready"
        assert graph["extraction_run_id"] == initial["extraction_run_id"]
        assert graph["source_artifact_id"] == initial["source_artifact_id"]
        assert "candidate_graph_path" not in graph and "manifest_path" not in graph
        assert graph["next_actions"] == ["review_candidate"]
        assert not graph.get("can_open_union_graph")
        assert not graph.get("preview_union_store_path")
        assert not graph["blocked_reason"]
        assert body["status"] != "ready_for_planning_activation"
        assert "session_memory_materialized" not in body["states"]


@pytest.mark.parametrize("failure_kind", ["structured", "pre_provider"])
def test_failed_production_step_is_durable_safe_and_not_reexecuted(
    client_env, monkeypatch, failure_kind,
):
    import src.graph_memory.extraction.graph_preview_runner as producer
    from src.graph_memory.extraction.category_candidate_graph_extractor import CategoryGraphExtractionError

    client, _corpus = client_env
    _prepare_normalized(client)
    invocations = []
    provider_attempts = []
    secret = "PRIVATE_MODEL_OUTPUT_sk-secret_/private/host/path"

    actual_extract = producer.extract_category_candidate_graph

    class FailingClient:
        def run_pass(self, pass_name, **kwargs):
            provider_attempts.append(pass_name)
            raise CategoryGraphExtractionError("invalid JSON " + secret, pass_name=pass_name)

    def fail_once(options, **kwargs):
        invocations.append(True)
        if failure_kind == "structured":
            # Exercise the actual category controller with an injected backend;
            # this is an observed fake-client call, never a real provider call.
            return actual_extract(options, client=FailingClient())
        raise RuntimeError("configuration refused before provider " + secret)

    monkeypatch.setattr(producer, "extract_category_candidate_graph", fail_once)
    response = client.post("/api/live/recap-ingest", json={
        "operation": "generate_recap_memory", "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld", "session": 22,
        "force_graph_run": True,
    })
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert len(invocations) == 1
    assert len(provider_attempts) == (1 if failure_kind == "structured" else 0)
    assert secret not in response.text
    assert graph["status"] == "failed"
    assert graph["blocked_reason"] == "The saved extraction did not complete. Review the attempt before retrying."
    assert "candidate_graph_path" not in graph and "manifest_path" not in graph
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    before = get_extraction_run(ROOT, graph["extraction_run_id"]).model_dump(mode="json")
    inspected = client.post("/api/live/recap-ingest", json={
        "operation": "inspect_status", "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld", "session": 22,
    })
    assert inspected.status_code == 200, inspected.text
    readback = inspected.json()["ingest_report"]["graph_preview"]
    assert readback["extraction_run_id"] == graph["extraction_run_id"]
    assert readback["extraction_run_status"] == "failed"
    assert readback["status"] == "failed"
    assert readback["next_actions"] == ["force_graph_run"]
    assert "graph_steps" not in readback and secret not in inspected.text
    assert len(invocations) == 1
    assert get_extraction_run(ROOT, graph["extraction_run_id"]).model_dump(mode="json") == before
    # A synthetic legacy manifest cannot override the database attempt.
    manifest = ROOT / "out/graph_memory/fake/graph_ingest_run_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"status":"candidate_validation_ready","diagnostics":{"extraction_run_id":graph["extraction_run_id"]}}))
    fake_bytes = manifest.read_bytes()
    legacy_read = client.post("/api/live/recap-ingest", json={
        "operation": "inspect_status", "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld", "session": 22,
    })
    assert legacy_read.status_code == 200
    legacy_graph = legacy_read.json()["ingest_report"]["graph_preview"]
    assert legacy_graph == readback
    assert manifest.read_bytes() == fake_bytes


def test_process_reuses_exact_run_after_packaging_mirrors_disappear(client_env, monkeypatch):
    from apps.live_control_server.services import recap_graph_preview_ingest as service
    client, _ = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    payload = {'operation':'generate_recap_memory','campaign_id':'longmont-c2',
        'managed_world_id':'elderwyld','session':22,
        'graph_model_id':'deepseek/deepseek-v4.1-flash-1017'}
    first = client.post('/api/live/recap-ingest',json=payload)
    assert first.status_code == 200, first.text
    graph = first.json()['ingest_report']['graph_preview']
    shutil.rmtree(ROOT / 'out/graph_memory', ignore_errors=True)
    def forbidden(*args, **kwargs):
        pytest.fail('Process redispatched extraction after losing operational mirrors')
    monkeypatch.setattr(service, 'run_recap_production_extraction', forbidden)
    second = client.post('/api/live/recap-ingest',json=payload)
    assert second.status_code == 200, second.text
    reused = second.json()['ingest_report']['graph_preview']
    assert reused['extraction_run_id'] == graph['extraction_run_id']
    assert reused['status'] == 'candidate_validation_ready'
    assert 'manifest_path' not in reused and 'candidate_graph_path' not in reused


@pytest.mark.parametrize('latest', ['failed', 'corrupt', 'different_model', 'different_profile'])
def test_process_does_not_revive_an_older_success(client_env, monkeypatch, application_state_dsn, latest):
    import psycopg
    from apps.live_control_server.services import recap_graph_preview_ingest as service, recap_ingest_context
    from apps.live_control_server.services.graph_run_registry import get_extraction_run, update_extraction_run_status
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus
    client, _ = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    payload = {'operation':'generate_recap_memory','campaign_id':'longmont-c2',
        'managed_world_id':'elderwyld','session':22,
        'graph_model_id':'deepseek/deepseek-v4.1-flash-1017'}
    first = client.post('/api/live/recap-ingest',json=payload)
    assert first.status_code == 200, first.text
    first_id = first.json()['ingest_report']['graph_preview']['extraction_run_id']
    if latest in {'different_model', 'different_profile'}:
        normalized = Path(first.json()['paths']['normalized_recap'])
        if not normalized.is_absolute():
            normalized = client_env[1] / normalized
        newer = service.run_recap_production_extraction(repo_root=ROOT,campaign_id='longmont-c2',
            session_id='session-22',recap_path=normalized,
            model_id='gpt-5.4-mini' if latest == 'different_model' else payload['graph_model_id'],
            profile='category_encounter_job_preview' if latest == 'different_profile' else None,allow_llm=True,
            category_client=object(),ingest_context=recap_ingest_context.read_recap_ingest_context())
        latest_id = newer.run.run_id
        assert newer.run.status == ExtractionRunStatus.REVIEWABLE
    else:
        newer = client.post('/api/live/recap-ingest',json={**payload,'force_graph_run':True})
        assert newer.status_code == 200, newer.text
        latest_id = newer.json()['ingest_report']['graph_preview']['extraction_run_id']
        if latest == 'failed':
            update_extraction_run_status(ROOT,latest_id,status=ExtractionRunStatus.FAILED,expected_revision=get_extraction_run(ROOT,latest_id).revision)
        else:
            with psycopg.connect(application_state_dsn) as connection:
                connection.execute('UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s',
                    (b'corrupt',latest_id,'candidate_graph'))
    assert latest_id != first_id
    actual = service.run_recap_production_extraction
    calls = []
    def record(**kwargs):
        calls.append(kwargs)
        return actual(**kwargs)
    monkeypatch.setattr(service,'run_recap_production_extraction',record)
    current = client.post('/api/live/recap-ingest',json=payload)
    if latest == 'corrupt':
        assert current.status_code in {409,422,500}, current.text
        assert current.json()['detail']['code'] == 'ingest_run_catalog_integrity_error'
        assert calls == []
    else:
        assert current.status_code == 200, current.text
        graph = current.json()['ingest_report']['graph_preview']
        assert graph['status'] == 'candidate_validation_ready'
        assert graph['extraction_run_id'] not in {first_id,latest_id}
        assert len(calls) == 1
        if latest == 'failed':
            assert get_extraction_run(ROOT,latest_id).status == ExtractionRunStatus.FAILED


def test_process_and_status_select_source_before_loading_other_run_outputs(client_env, monkeypatch, application_state_dsn):
    import psycopg
    from apps.live_control_server.services import recap_graph_preview_ingest as service, recap_ingest_context
    client, corpus = client_env
    _prepare_normalized(client)
    _patch_fake_category_extract(monkeypatch)
    payload = {'operation':'generate_recap_memory','campaign_id':'longmont-c2',
        'managed_world_id':'elderwyld','session':22,
        'graph_model_id':'deepseek/deepseek-v4.1-flash-1017'}
    first = client.post('/api/live/recap-ingest',json=payload)
    assert first.status_code == 200, first.text
    first_id = first.json()['ingest_report']['graph_preview']['extraction_run_id']
    normalized = Path(first.json()['paths']['normalized_recap'])
    if not normalized.is_absolute():
        normalized = corpus / normalized
    other = ROOT / 'other-source.md'
    other.write_text(normalized.read_text()+'\n\nThe party waits for a second report.\n')
    newer = service.run_recap_production_extraction(repo_root=ROOT,campaign_id='longmont-c2',
        session_id='session-22',recap_path=other,model_id=payload['graph_model_id'],allow_llm=True,
        ingest_context=recap_ingest_context.read_recap_ingest_context())
    assert newer.run.status.value == 'reviewable'
    assert newer.run.run_id != first_id
    with psycopg.connect(application_state_dsn) as connection:
        connection.execute('UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s',
            (b'corrupt',newer.run.run_id,'candidate_graph'))
    monkeypatch.setattr(service,'run_recap_production_extraction',
        lambda **kwargs:pytest.fail('Other source output forced extraction for a valid selected source'))
    for operation in ('generate_recap_memory','inspect_status'):
        response = client.post('/api/live/recap-ingest',json={**payload,'operation':operation})
        assert response.status_code == 200, response.text
        graph = response.json()['ingest_report']['graph_preview']
        assert graph['status'] == 'candidate_validation_ready' and graph['extraction_run_id'] == first_id
