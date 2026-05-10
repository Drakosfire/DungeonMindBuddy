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
    / "evals"
    / "sentence_routing_retrieval_falsification"
    / "artifacts"
    / "last_session1_c1_breadcrumb_records.jsonl"
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


def test_route_equivalence_shadow_payload_is_deterministic() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    first = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
    )
    second = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
    )
    assert first == second


def test_route_equivalence_shadow_payload_for_c1s1_campaign_id() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
    )
    assert payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
    assert payload["scenario_campaign_id"] == "longmont-c1"
    assert payload["edges_total"] == len(records)
    assert payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})
    assert payload["source_paths"] == [str(p) for p in source_paths]


def test_route_equivalence_shadow_payload_for_c1s2_campaign_id() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
    )
    assert payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
    assert payload["scenario_campaign_id"] == "longmont-c1"
    assert payload["edges_total"] == len(records)
    assert payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})
    assert payload["source_paths"] == [str(p) for p in source_paths]


def test_route_equivalence_shadow_payload_for_c1s3_campaign_id() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c1",
        records=records,
        source_paths=source_paths,
    )
    assert payload["schema"] == ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1
    assert payload["scenario_campaign_id"] == "longmont-c1"
    assert payload["edges_total"] == len(records)
    assert payload["edges_for_scenario_campaign"] == sum(1 for r in records if r.campaign_id == "longmont-c1")
    assert payload["campaign_ids"] == sorted({r.campaign_id for r in records})
    assert payload["source_paths"] == [str(p) for p in source_paths]


def test_route_equivalence_shadow_payload_unknown_campaign_returns_zero_match() -> None:
    source_paths = _route_equivalence_paths()
    records = load_route_equivalence_shadow_records(source_paths)
    payload = build_route_equivalence_shadow_payload(
        scenario_campaign_id="longmont-c99",
        records=records,
        source_paths=source_paths,
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


def test_route_equivalence_flag_is_additive_only_at_harness_boundary(tmp_path: Path) -> None:
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
        flagged_without_shadow = dict(flagged_row)
        flagged_without_shadow.pop("shadow_route_equivalences", None)
        assert base_row == flagged_without_shadow


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
