"""Ordinary Process owns exact DB intake; providers are replaced with fixture output."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.routes import recap_ingest as route
from apps.live_control_server.services import recap_ingest_context
from apps.live_control_server.services.graph_run_registry import (
    load_reviewable_extraction_data,
)
from apps.live_control_server.services.source_artifact_registry import (
    load_registered_source_artifact_bytes,
)
from graph_memory.ingestion.native_recap_source import SourceScope
from tests.test_recap_managed_standing_context import seed_binding

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "synthetic-process-operator-token-000000"


@pytest.fixture
def client_env(application_state_dsn, tmp_path, monkeypatch):
    assert "dungeonbuddy_app_state_test_" in application_state_dsn
    for name, value in {
        "DMB_DEPLOYMENT_ENVIRONMENT": "local",
        "DMB_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": TOKEN,
        "DMB_ARTIFACT_DATA_ROOT": str(tmp_path),
        "DMB_MANAGED_WORLD_DATA_ROOT": str(tmp_path),
        "DUNGEONMIND_LIVE_SESSION_DIR": str(tmp_path),
    }.items():
        monkeypatch.setenv(name, value)
    from apps.live_control_server.config import SESSION_DIR_ENV

    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "apps.live_control_server.routes.graph_preview.repo_root", lambda: tmp_path
    )
    seed_binding(tmp_path, "elderwyld", "world:elderwyld", version=3)
    _write_synthetic_session(tmp_path)
    (tmp_path / "event_log.jsonl").write_text("")
    (tmp_path / "job_queue.jsonl").write_text("")
    # A corpus directory cannot even be opened. It is not part of Process.
    poison = tmp_path / "not-a-corpus"
    poison.write_text("not source authority")
    monkeypatch.setenv("DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT", str(poison))
    scope = SourceScope(
        managed_world_id="elderwyld",
        native_world_id="world:elderwyld",
        binding_version=3,
        campaign_id="longmont-c2",
    )

    def resolve(**kw):
        if kw != {"managed_world_id": "elderwyld", "campaign_id": "longmont-c2"}:
            raise ValueError("foreign source scope")
        return scope

    monkeypatch.setattr(recap_ingest_context, "resolve_recap_source_scope", resolve)
    _patch_fake_category_extract(monkeypatch)
    import httpx

    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda *_: pytest.fail("Provider HTTP forbidden"),
    )
    with TestClient(
        create_app(),
        client=("127.0.0.1", 50000),
        headers={"Authorization": "Bearer " + TOKEN},
    ) as client:
        yield client, tmp_path


def process_body(**changes):
    return {
        "operation": "generate_recap_memory",
        "managed_world_id": "elderwyld",
        "campaign_id": "longmont-c2",
        "session": 8,
        "raw_text": "# A recap\n\nA keeper scouts the Mireward road.",
        "include_graph_extraction": True,
        **changes,
    }


def test_recap_ingest_generate_recap_memory_with_graph_extraction_fake_client(
    client_env,
):
    client, root = client_env
    body = process_body()
    response = client.post("/api/live/recap-ingest", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["paths"] == {}
    graph = result["ingest_report"]["graph_preview"]
    assert graph["status"] == "candidate_validation_ready"
    data = load_reviewable_extraction_data(root, graph["extraction_run_id"])
    source, raw = load_registered_source_artifact_bytes(
        root, graph["source_artifact_id"]
    )
    assert raw == body["raw_text"].encode() + b"\n"
    assert source.world_id == "world:elderwyld" and source.session_id == "session-8"
    assert data.source_bytes == raw and data.candidate_bytes and data.span_bytes
    assert source.content_sha256 == hashlib.sha256(raw).hexdigest()
    assert not (root / "Longmont Campaign").exists()
    # Native source admission and Graph publication are separate commands.
    assert result["native_recap_source"] is None


def test_exact_reuse_force_and_changed_text_keep_distinct_attempts(client_env):
    client, root = client_env

    def run(**kw):
        reply = client.post("/api/live/recap-ingest", json=process_body(**kw))
        assert reply.status_code == 200, reply.text
        return reply.json()["ingest_report"]["graph_preview"]

    first = run()
    reused = run()
    assert reused["extraction_run_id"] == first["extraction_run_id"]
    fresh = run(force_graph_run=True)
    assert fresh["extraction_run_id"] != first["extraction_run_id"]
    changed = run(raw_text="A second visit to the Mireward road.")
    assert changed["source_artifact_id"] != first["source_artifact_id"]
    original, _ = load_registered_source_artifact_bytes(
        root, first["source_artifact_id"]
    )
    assert (
        original.content_sha256
        == hashlib.sha256(process_body()["raw_text"].encode() + b"\n").hexdigest()
    )
    assert load_reviewable_extraction_data(
        root, first["extraction_run_id"]
    ).candidate_bytes


def test_failed_extraction_keeps_source_and_attempt(client_env, monkeypatch):
    client, root = client_env
    import src.graph_memory.extraction.graph_preview_runner as producer

    def fail(*a, **kw):
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(producer, "extract_category_candidate_graph", fail)
    response = client.post("/api/live/recap-ingest", json=process_body())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "error"
    graph = result["ingest_report"]["graph_preview"]
    assert graph["extraction_run_status"] == "failed"
    _, raw = load_registered_source_artifact_bytes(root, graph["source_artifact_id"])
    assert raw == process_body()["raw_text"].encode() + b"\n"


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


def _live_extraction_payload(
    *,
    source_artifact_id: str,
    spref: str,
    source_text: str,
    span_index: dict,
    location_label: str = "Mireward road",
) -> dict:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        FixtureCategoryGraphPassClient,
        run_category_pipeline,
    )
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        minimal_category_pass_outputs,
    )

    # Bind the quote to its actual paragraph, never the generated frontmatter.
    lines = source_text.splitlines()
    matches = [
        span["source_span_id"]
        for span in span_index["spans"]
        if location_label in "\n".join(lines[span["start_line"] - 1 : span["end_line"]])
    ]
    assert matches, "synthetic fixture must quote a real source paragraph"
    spref = matches[0]
    # Exercise packaging with one location actually named in these source fixtures.
    # Keep the fake independent of the checkout's real standing-party registry.
    outputs = minimal_category_pass_outputs(
        spref, node_label=location_label, node_id="node:fixture-location"
    )
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
        ),
    )
    graph = result.candidate_graph
    graph["source_artifact_ids"] = [source_artifact_id]
    for collection in (
        "nodes",
        "edges",
        "beats",
        "ignored_items",
        "deferred_items",
        "proposed_writes",
    ):
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
                        "label": ref.get("label")
                        or ref.get("source_span_ref_id")
                        or spref,
                        "evidence_role": ref.get("evidence_role") or "source_evidence",
                        "can_open_source": True,
                        "can_highlight_span": True,
                        "source_span_ref_id": ref.get("source_span_ref_id") or spref,
                    }
                )
            item["evidence_refs"] = stamped
    return graph


def _patch_fake_category_extract(
    monkeypatch: pytest.MonkeyPatch, *, location_label: str = "Mireward road"
) -> None:
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
        graph = _live_extraction_payload(
            source_artifact_id=artifact,
            spref=spref,
            source_text=options.source_text,
            span_index=dict(options.source_span_index),
            location_label=location_label,
        )
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
        )

    monkeypatch.setattr(prod_runner, "extract_category_candidate_graph", fake_extract)
