"""Contract tests for OPT-BENCH01 world graph warm-path benchmark harness."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.bench_world_graph_warm_path as bench


@pytest.fixture(autouse=True)
def _isolated_bench_state() -> None:
    bench.reset_all_state(include_recipes=True)
    yield
    bench.reset_all_state(include_recipes=True)


def test_scenario_a_fully_cold_observes_miss_and_durable_reads(tmp_path: Path) -> None:
    runs, errors = bench.run_scenario_fully_cold(tmp_path, iterations=1)
    assert not errors
    run = runs[0]
    assert run.projection_cache_status == "miss"
    assert run.graph_payload_reads_this_request > 0 or run.resident_status == "miss"


def test_scenario_b_resident_hit_cache_miss_builds(tmp_path: Path) -> None:
    runs, errors = bench.run_scenario_resident_revision(tmp_path, iterations=2)
    assert not errors
    for run in runs:
        assert run.resident_status in {"hit", "coalesced"}
        assert run.projection_cache_status == "miss"
        assert run.graph_payload_reads_this_request == 0
        assert run.projection_build_ms > 0


def test_scenario_c_opt02_prewarm_resident_hit_cache_miss(tmp_path: Path) -> None:
    runs, errors = bench.run_scenario_opt02_post_publish(tmp_path, iterations=2)
    assert not errors
    for run in runs:
        assert run.resident_status in {"hit", "coalesced"}
        assert run.projection_cache_status == "miss"
        assert run.graph_payload_reads_this_request == 0
        assert run.snapshot_revision_id == run.snapshot_head_revision_id
        assert run.snapshot_is_head is True
        assert run.snapshot_revision_id == run.selected_revision_id


def test_scenario_d_opt03_surface_warm_cache_hit_zero_graph_reads(
    tmp_path: Path,
) -> None:
    runs, errors = bench.run_scenario_opt03_surface_warm(tmp_path, iterations=2)
    assert not errors
    for run in runs:
        assert run.projection_cache_status == "hit"
        assert run.graph_payload_reads_this_request == 0
        assert run.snapshot_revision_id == run.snapshot_head_revision_id
        assert run.snapshot_is_head is True
        assert run.payload_digest


def test_scenario_semantic_counts_and_digest_stable_within_scenario(
    tmp_path: Path,
) -> None:
    for runner in (
        bench.run_scenario_fully_cold,
        bench.run_scenario_resident_revision,
        bench.run_scenario_opt02_post_publish,
        bench.run_scenario_opt03_surface_warm,
    ):
        runs, errors = runner(tmp_path, iterations=2)
        assert not errors
        assert len(runs) == 2
        assert runs[0].nodes_returned == runs[1].nodes_returned
        assert runs[0].relationships_returned == runs[1].relationships_returned
        assert runs[0].attributes_returned == runs[1].attributes_returned
        assert runs[0].selected_revision_id == runs[1].selected_revision_id
        assert runs[0].snapshot_revision_id == runs[1].snapshot_revision_id
        assert runs[0].payload_digest == runs[1].payload_digest


def test_scenarios_a_and_b_share_head_shape_counts(tmp_path: Path) -> None:
    cold_runs, cold_errors = bench.run_scenario_fully_cold(tmp_path, iterations=1)
    assert not cold_errors
    bench.reset_all_state(include_recipes=True)
    resident_runs, resident_errors = bench.run_scenario_resident_revision(
        tmp_path, iterations=1
    )
    assert not resident_errors
    cold = cold_runs[0]
    resident = resident_runs[0]
    assert cold.nodes_returned == resident.nodes_returned
    assert cold.relationships_returned == resident.relationships_returned
    assert cold.attributes_returned == resident.attributes_returned
    assert cold.selected_revision_id == resident.selected_revision_id
    assert cold.payload_digest == resident.payload_digest


def test_validate_semantics_rejects_stale_snapshot_vs_observation() -> None:
    run = bench.ProjectionRun(
        e2e_ms=1.0,
        head_resolution_ms=0.0,
        resident_wait_ms=0.0,
        cold_load_ms=None,
        projection_build_ms=0.0,
        projection_cache_status="hit",
        graph_payload_reads_this_request=0,
        revision_manifest_reads_this_request=0,
        contribution_reads_this_request=0,
        source_index_reads_this_request=0,
        nodes_returned=12,
        relationships_returned=1,
        attributes_returned=1,
        selected_revision_id="rev:bbbbbbbbbbbbbbbb",
        head_revision_id="rev:bbbbbbbbbbbbbbbb",
        resident_status="hit",
        snapshot_revision_id="rev:aaaaaaaaaaaaaaaa",
        snapshot_head_revision_id="rev:aaaaaaaaaaaaaaaa",
        snapshot_is_head=True,
        payload_digest="deadbeef",
    )
    errors = bench.validate_scenario_semantics(
        [run],
        scenario="opt03_surface_warm",
        expected_revision_id="rev:bbbbbbbbbbbbbbbb",
    )
    assert any("snapshot.revision_id" in error for error in errors)
    assert any("expected published" in error for error in errors)


def test_plan_request_matches_fixture_focus() -> None:
    request = bench.build_plan_projection_request()
    assert request.world_id == bench.WORLD_ID
    assert request.campaign_id == bench.CAMPAIGN_ID
    assert request.revision_pin is None
    assert request.query_text is None
    assert request.focus.kind == "session"
    assert request.focus.session_id == bench.FOCUS_SESSION_ID
    assert request.focus.campaign_id == bench.CAMPAIGN_ID
