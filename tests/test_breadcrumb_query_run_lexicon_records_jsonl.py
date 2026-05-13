"""Lexicon build must work when session memory comes from ``--records-jsonl`` (no ``rec_objs``)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from evals.sentence_routing_retrieval_falsification.route_equivalence_shadow import (
    ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
    build_route_equivalence_shadow_payload,
    load_route_equivalence_shadow_records,
)
from evals.sentence_routing_retrieval_falsification.token_resolver_shadow import (
    build_campaign_lexicon,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_JSONL = (
    _REPO_ROOT
    / "corpus"
    / "eldyrwild-markdown"
    / "Longmont Campaign"
    / "Campaign 1"
    / "Session Recaps"
    / "_session_memory"
    / "Session 01 - Stonebridge and Glowkindle Rats.records_meta.jsonl"
)
_NATURAL_GOLD_C1S1 = (
    _REPO_ROOT
    / "evals"
    / "sentence_routing_retrieval_falsification"
    / "gold"
    / "breadcrumb_query_natural_c1s1_v1.json"
)


def test_build_campaign_lexicon_from_jsonl_records_derives_campaign_stopwords() -> None:
    """Mirrors ``--records-jsonl`` ingest: dict rows only, no breadcrumb frontmatter."""
    assert _FIXTURE_JSONL.is_file(), f"missing fixture: {_FIXTURE_JSONL}"
    lines = _FIXTURE_JSONL.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    assert len(records) >= 4, "fixture should contain several session-memory rows"

    lex = build_campaign_lexicon(
        breadcrumb_artifact_text="",
        records=records,
        campaign_id="longmont-c1",
    )
    assert "longmont" in lex.derived_route_stopwords, (
        "route-frequency derivation should mark recurring setting token longmont; "
        "empty lexicon (records not passed) would miss this"
    )


def test_build_campaign_lexicon_from_jsonl_records_includes_cohort_equivalence_seeds() -> None:
    """Cohort benchmark seeds are merged into the lexicon layer (no frontmatter aliases)."""
    lines = _FIXTURE_JSONL.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    lex = build_campaign_lexicon(
        breadcrumb_artifact_text="",
        records=records,
        campaign_id="longmont-c1",
    )
    assert "captain" in lex.equivalences


def _route_equivalence_paths() -> list[Path]:
    return [
        _REPO_ROOT
        / "evals"
        / "sentence_routing_retrieval_falsification"
        / "artifacts"
        / "lexicon"
        / "route_equivalence_longmont_c1_v1.jsonl",
        _REPO_ROOT
        / "evals"
        / "sentence_routing_retrieval_falsification"
        / "artifacts"
        / "lexicon"
        / "route_equivalence_longmont_c2_v1.jsonl",
    ]


expected_source_paths = [
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl",
    "evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl",
]

def test_route_equivalence_shadow_payload_is_deterministic() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    first = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
        workspace_root=_REPO_ROOT,
    )
    second = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
        workspace_root=_REPO_ROOT,
    )
    assert first == second


def test_route_equivalence_shadow_payload_for_c1s1_campaign_id() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
        workspace_root=_REPO_ROOT,
    )
    assert payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
    assert payload["scenario_campaign_id"] == "longmont-c1"
    assert payload["edges_total"] == len(records)
    assert payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})
    assert payload["source_paths"] == expected_source_paths


def test_route_equivalence_shadow_payload_for_c1s2_campaign_id() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
        workspace_root=_REPO_ROOT,
    )
    assert payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
    assert payload["scenario_campaign_id"] == "longmont-c1"
    assert payload["edges_total"] == len(records)
    assert payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})
    assert payload["source_paths"] == expected_source_paths


def test_route_equivalence_shadow_payload_for_c1s3_campaign_id() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
        workspace_root=_REPO_ROOT,
    )
    assert payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
    assert payload["scenario_campaign_id"] == "longmont-c1"
    assert payload["edges_total"] == len(records)
    assert payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})
    assert payload["source_paths"] == expected_source_paths


def test_route_equivalence_shadow_payload_unknown_campaign_returns_zero_match() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c99",
        records=records,
        source_paths=source_paths,
        workspace_root=_REPO_ROOT,
    )
    assert payload["edges_for_scenario_campaign"] == 0
    assert payload["edges_total"] > 0
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})


def test_breadcrumb_query_run_help_advertises_route_equivalence_jsonl_flag() -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--route-equivalence-jsonl" in result.stdout
    assert "--use-scene-beat-expansion" in result.stdout
    assert "--scene-beat-expand-limit" in result.stdout


def _run_breadcrumb_query_run_subprocess_with_cwd(
    *, output_path: Path, extra_args: list[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "uv",
        "run",
        "--directory",
        str(_REPO_ROOT),
        "python",
        "-m",
        "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run",
        "--records-jsonl",
        str(_FIXTURE_JSONL),
        "--gold",
        str(_NATURAL_GOLD_C1S1),
        "--retrieval-only",
        "--output",
        str(output_path),
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))


def _run_breadcrumb_query_run_subprocess(*, output_path: Path, extra_args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "evals.sentence_routing_retrieval_falsification.breadcrumb_query_run",
        "--records-jsonl",
        str(_FIXTURE_JSONL),
        "--gold",
        str(_NATURAL_GOLD_C1S1),
        "--retrieval-only",
        "--output",
        str(output_path),
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_use_route_equivalence_for_ranking_flag_is_additive_only_at_harness_boundary(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_without = tmp_path / "without.json"
    out_with = tmp_path / "with.json"
    without_result = _run_breadcrumb_query_run_subprocess(output_path=out_without, extra_args=[])
    with_result = _run_breadcrumb_query_run_subprocess(
        output_path=out_with,
        extra_args=[
            "--route-equivalence-jsonl",
            str(_route_equivalence_paths()[0]),
            "--route-equivalence-jsonl",
            str(_route_equivalence_paths()[1]),
            "--use-route-equivalence-for-ranking",
        ],
    )
    assert without_result.returncode == 0, without_result.stderr
    assert with_result.returncode == 0, with_result.stderr
    rows_without = json.loads(out_without.read_text(encoding="utf-8"))["results"]
    rows_with = json.loads(out_with.read_text(encoding="utf-8"))["results"]
    assert len(rows_without) == len(rows_with)
    for base_row, flagged_row in zip(rows_without, rows_with, strict=True):
        assert "shadow_route_equivalences" not in base_row
        assert "shadow_route_equivalences" in flagged_row
        assert base_row["scenario_id"] == flagged_row["scenario_id"]
        assert flagged_row.get("ranking_augmented_by_equivalences") is True
        aliases = (flagged_row.get("query_token_aliases") or flagged_row.get("query_trace", {}).get("query_token_aliases") or flagged_row.get("full_result", {}).get("trace", {}).get("query_token_aliases") or [])
        assert aliases





def test_scene_beat_expansion_flag_emits_row_metadata(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_with = tmp_path / "with_scene_beats.json"
    with_result = _run_breadcrumb_query_run_subprocess(
        output_path=out_with,
        extra_args=["--use-scene-beat-expansion", "--scene-beat-expand-limit", "4"],
    )
    assert with_result.returncode == 0, with_result.stderr
    rows_with = json.loads(out_with.read_text(encoding="utf-8"))["results"]
    assert rows_with
    for row in rows_with:
        sb = row.get("scene_beat_expansion")
        assert isinstance(sb, dict)
        assert sb.get("enabled") is True
        assert sb.get("expand_same_beat_limit") == 4


def test_scene_beat_packet_flag_emits_row_metadata(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_with = tmp_path / "with_scene_packets.json"
    with_result = _run_breadcrumb_query_run_subprocess(
        output_path=out_with,
        extra_args=["--use-scene-beat-packets", "--scene-beat-packet-threshold", "8", "--scene-beat-packet-top-k", "2", "--scene-beat-packet-unit-limit", "5", "--scene-beat-packet-max-packets", "1"],
    )
    assert with_result.returncode == 0, with_result.stderr
    rows_with = json.loads(out_with.read_text(encoding="utf-8"))["results"]
    assert rows_with
    for row in rows_with:
        pkt = row.get("scene_beat_packets")
        assert isinstance(pkt, dict)
        assert pkt.get("enabled") is True
        assert pkt.get("threshold") == 8
        assert pkt.get("top_k") == 2
        assert pkt.get("unit_limit") == 5
        assert pkt.get("max_packets") == 1

def test_route_equivalence_source_paths_are_workspace_relative_and_cwd_invariant(
    tmp_path: Path,
) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_a = tmp_path / "from_repo_root.json"
    out_b = tmp_path / "from_subdir.json"
    extra_args = [
        "--route-equivalence-jsonl",
        str(_route_equivalence_paths()[0]),
        "--route-equivalence-jsonl",
        str(_route_equivalence_paths()[1]),
    ]
    run_a = _run_breadcrumb_query_run_subprocess_with_cwd(
        output_path=out_a,
        extra_args=extra_args,
        cwd=_REPO_ROOT,
    )
    cwd_subdir = _REPO_ROOT / "tests"
    assert cwd_subdir.is_dir()
    run_b = _run_breadcrumb_query_run_subprocess_with_cwd(
        output_path=out_b,
        extra_args=extra_args,
        cwd=cwd_subdir,
    )
    assert run_a.returncode == 0, run_a.stderr
    assert run_b.returncode == 0, run_b.stderr

    rows_a = json.loads(out_a.read_text(encoding="utf-8"))["results"]
    rows_b = json.loads(out_b.read_text(encoding="utf-8"))["results"]
    assert len(rows_a) == len(rows_b) > 0
    for row_a, row_b in zip(rows_a, rows_b, strict=True):
        payload_a = row_a["shadow_route_equivalences"]
        payload_b = row_b["shadow_route_equivalences"]
        assert payload_a == payload_b, "shadow payload must be CWD-invariant"
        assert payload_a["source_paths"] == expected_source_paths

def test_route_equivalence_load_failure_emits_error_payload_and_run_survives(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out_path = tmp_path / "error-path.json"
    missing_path = tmp_path / "does_not_exist.jsonl"
    run = _run_breadcrumb_query_run_subprocess(
        output_path=out_path,
        extra_args=["--route-equivalence-jsonl", str(missing_path)],
    )
    assert run.returncode == 0, run.stderr
    rows = json.loads(out_path.read_text(encoding="utf-8"))["results"]
    assert rows
    for row in rows:
        payload = row.get("shadow_route_equivalences")
        assert isinstance(payload, dict)
        assert payload.get("schema") == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
        error_text = str(payload.get("error") or "")
        assert error_text


def test_expected_route_substring_breakdown_is_consistent_with_violations(tmp_path: Path) -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv not available")
    out = tmp_path / "breakdown.json"
    run = _run_breadcrumb_query_run_subprocess(output_path=out, extra_args=[])
    assert run.returncode == 0, run.stderr
    rows = json.loads(out.read_text(encoding="utf-8"))["results"]
    assert rows
    for row in rows:
        breakdown = row.get("expected_route_substring_breakdown")
        assert isinstance(breakdown, list)
        any_unmatched = any(not bool(item.get("matched")) for item in breakdown)
        has_missing_violation = "missing_expected_route_hit" in row.get("violations", [])
        assert any_unmatched == has_missing_violation
