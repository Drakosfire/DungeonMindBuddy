"""Selection, preview, CLI, and fingerprint witnesses for DFC-2c Ingest adoption."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestArtifactKind,
    GraphIngestArtifactRef,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
    GraphIngestSource,
    adapt_recap_manifest_to_extraction_run,
)
from product_continuity.ingest_adoption import (
    IngestAdoptionInputError,
    confined_manifest_path,
    normalize_run_ids,
    preview_ingest_adoption,
    run_ingest_adoption,
    sanitize_operator_detail,
    target_set_sha256,
)
from product_continuity.inventory import _durable_run_fingerprint


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _manifest(
    *,
    run_id: str,
    campaign_id: str = "longmont-c2",
    session_id: str = "session-27",
    source_artifact_id: str | None = "artifact:recap:longmont-c2:session-27",
    graph_sha: str = "c" * 64,
) -> GraphIngestRunManifest:
    source = GraphIngestSource(
        source_artifact_id=source_artifact_id,
        source_domain="recap",
        input_path_record="corpus/recap.md",
        normalized_recap_sha256="a" * 64,
    )
    artifacts = {
        "source_span_index": GraphIngestArtifactRef(
            kind=GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
            uri="runs/spans.json",
            sha256="b" * 64,
            exists=True,
        ),
        "candidate_graph": GraphIngestArtifactRef(
            kind=GraphIngestArtifactKind.CANDIDATE_GRAPH,
            uri="runs/graph.json",
            sha256=graph_sha,
            exists=True,
        ),
    }
    return GraphIngestRunManifest(
        run_id=run_id,
        campaign_id=campaign_id,
        session_id=session_id,
        status=GraphIngestRunStatus.READY_FOR_PROJECTION,
        source=source,
        artifacts=artifacts,
    )


def _write_manifest(root: Path, manifest: GraphIngestRunManifest) -> Path:
    path = (
        root
        / "out/graph_memory/runs"
        / manifest.run_id
        / "graph_ingest_run_manifest.json"
    )
    _write_json(path, manifest.model_dump(mode="json", by_alias=True))
    return path


def test_sanitize_operator_detail_redacts_dsn_password() -> None:
    secret = "hunter2-not-for-logs"
    raw = (
        "APP-STATE unavailable using "
        f"postgresql://buddy:{secret}@127.0.0.1:54329/dungeonbuddy_application_state"
    )
    out = sanitize_operator_detail(raw)
    assert secret not in out
    assert f"postgresql://buddy:{secret}@" not in out
    assert "***" in out


def test_normalize_rejects_empty_and_duplicates() -> None:
    with pytest.raises(IngestAdoptionInputError, match="empty"):
        normalize_run_ids(["  "])
    with pytest.raises(IngestAdoptionInputError, match="duplicate"):
        normalize_run_ids(["run-a", "run-a"])
    assert normalize_run_ids(["run-a", "run-b"]) == ["run-a", "run-b"]


def test_cli_has_no_heuristic_selectors() -> None:
    import importlib.util
    from contextlib import redirect_stderr, redirect_stdout
    from io import StringIO

    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "adopt_historical_ingest_runs.py"
    )
    spec = importlib.util.spec_from_file_location("adopt_historical_ingest_cli", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    empty = module._parse_args([])
    assert empty.apply is False
    assert empty.all_historical_ingest is False
    args = module._parse_args(
        [
            "--historical-root",
            "/tmp/hist",
            "--all-historical-ingest",
        ]
    )
    assert args.apply is False
    assert args.all_historical_ingest is True
    buf = StringIO()
    with pytest.raises(SystemExit), redirect_stdout(buf), redirect_stderr(buf):
        module._parse_args(["--help"])
    text = buf.getvalue()
    flags: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            for token in stripped.replace(",", " ").split():
                if token.startswith("--"):
                    flags.append(token)
    assert "--run-id" in flags
    assert "--all-historical-ingest" in flags
    assert "--apply" in flags
    assert "--expected-set-sha256" in flags
    assert "--all" not in flags
    assert "--force" not in flags
    assert "--latest" not in flags
    assert "--campaign" not in flags
    assert "--session" not in flags


def test_selection_xor_and_apply_requires_expected_hash(tmp_path: Path) -> None:
    hist = tmp_path / "hist"
    hist.mkdir()
    current = tmp_path / "current"
    current.mkdir()
    with pytest.raises(IngestAdoptionInputError, match="mutually exclusive"):
        run_ingest_adoption(
            current_repo_root=current,
            historical_roots=[("hist", hist)],
            run_ids=["run-a"],
            all_historical=True,
            apply=False,
        )
    with pytest.raises(IngestAdoptionInputError, match="select exact"):
        run_ingest_adoption(
            current_repo_root=current,
            historical_roots=[("hist", hist)],
            run_ids=None,
            all_historical=False,
            apply=False,
        )
    with pytest.raises(IngestAdoptionInputError, match="expected-set-sha256"):
        run_ingest_adoption(
            current_repo_root=current,
            historical_roots=[("hist", hist)],
            run_ids=["run-a"],
            all_historical=False,
            apply=True,
            expected_set_sha256="",
        )


def test_confined_manifest_rejects_absolute_and_parent_escape(tmp_path: Path) -> None:
    root = tmp_path / "hist"
    root.mkdir()
    path, error = confined_manifest_path(root, "/tmp/secret.json")
    assert path is None
    assert error is not None
    path, error = confined_manifest_path(root, "../outside.json")
    assert path is None
    assert error is not None


def test_w2_adapter_is_reused_exactly(tmp_path: Path) -> None:
    manifest = _manifest(run_id="run-reuse-1")
    direct = adapt_recap_manifest_to_extraction_run(manifest)
    hist = tmp_path / "hist"
    path = _write_manifest(hist, manifest)
    raw = json.loads(path.read_text(encoding="utf-8"))
    reloaded = GraphIngestRunManifest.model_validate(raw)
    via_file = adapt_recap_manifest_to_extraction_run(reloaded)
    assert via_file.model_dump(mode="json") == direct.model_dump(mode="json")
    assert _durable_run_fingerprint(via_file) == _durable_run_fingerprint(direct)


def test_w3_target_set_digest_is_order_independent() -> None:
    first = target_set_sha256([("b", "ff2"), ("a", "ff1")])
    second = target_set_sha256([("a", "ff1"), ("b", "ff2")])
    assert first == second
    changed = target_set_sha256([("a", "ff1"), ("b", "ff3")])
    assert changed != first


def test_missing_historical_root_is_input_error(tmp_path: Path) -> None:
    current = tmp_path / "current"
    current.mkdir()
    with pytest.raises(IngestAdoptionInputError, match="missing/unreadable"):
        preview_ingest_adoption(
            current_repo_root=current,
            historical_roots=[("gone", tmp_path / "missing")],
            run_ids=["run-a"],
            all_historical=False,
        )


def test_w3_preview_digest_is_stable_across_root_order_and_duplicates(
    tmp_path: Path,
) -> None:
    first = tmp_path / "hist-a"
    second = tmp_path / "hist-b"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(first, _manifest(run_id="run-c1-1", campaign_id="longmont-c1"))
    _write_manifest(second, _manifest(run_id="run-c1-1", campaign_id="longmont-c1"))
    _write_manifest(
        first,
        _manifest(run_id="run-c2-1", campaign_id="longmont-c2", session_id="session-01"),
    )
    preview_ab = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist-a", first), ("hist-b", second)],
        run_ids=["run-c1-1", "run-c2-1"],
        all_historical=False,
    )
    preview_ba = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist-b", second), ("hist-a", first)],
        run_ids=["run-c2-1", "run-c1-1"],
        all_historical=False,
    )
    assert preview_ab.target_set_sha256 == preview_ba.target_set_sha256
    assert preview_ab.selected_count == 2
    mutated = _manifest(run_id="run-c2-1", campaign_id="longmont-c2", session_id="session-01")
    mutated.artifacts["candidate_graph"].sha256 = "d" * 64
    _write_manifest(first, mutated)
    preview_changed = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist-a", first), ("hist-b", second)],
        run_ids=["run-c1-1", "run-c2-1"],
        all_historical=False,
    )
    assert preview_changed.target_set_sha256 != preview_ab.target_set_sha256


def test_w6_malformed_adapt_failed_conflict_and_missing_block(tmp_path: Path) -> None:
    hist = tmp_path / "hist"
    other = tmp_path / "other"
    current = tmp_path / "current"
    current.mkdir()
    recoverable = _manifest(run_id="run-safe")
    _write_manifest(hist, recoverable)
    bad = hist / "out/graph_memory/runs/run-malformed/graph_ingest_run_manifest.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{not-json", encoding="utf-8")
    _write_manifest(
        hist,
        GraphIngestRunManifest(
            run_id="run-adapt-failed",
            campaign_id="longmont-c2",
            session_id="session-22",
            source=GraphIngestSource(source_domain="recap"),
        ),
    )
    _write_manifest(other, _manifest(run_id="run-conflict", graph_sha="e" * 64))
    _write_manifest(hist, _manifest(run_id="run-conflict", graph_sha="f" * 64))
    mixed = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist), ("other", other)],
        run_ids=["run-safe", "run-adapt-failed", "run-conflict", "run-missing"],
        all_historical=False,
    )
    assert mixed.blocked is True
    by_id = {row.run_id: row for row in mixed.dispositions}
    assert by_id["run-safe"].action == "block"
    assert by_id["run-safe"].classification == "COMPARISON_UNAVAILABLE"
    assert by_id["run-adapt-failed"].action == "block"
    assert by_id["run-adapt-failed"].classification == "NEEDS_ADAPTER"
    assert by_id["run-conflict"].action == "block"
    assert by_id["run-conflict"].classification == "CONFLICT"
    assert by_id["run-missing"].action == "block"
    all_hist = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist), ("other", other)],
        run_ids=None,
        all_historical=True,
    )
    assert all_hist.blocked is True
    assert any(row.classification == "MALFORMED" for row in all_hist.dispositions)


def test_w6_current_authority_unavailable_blocks(tmp_path: Path) -> None:
    hist = tmp_path / "hist"
    current = tmp_path / "current"
    current.mkdir()
    _write_manifest(hist, _manifest(run_id="run-unavail"))
    report = preview_ingest_adoption(
        current_repo_root=current,
        historical_roots=[("hist", hist)],
        run_ids=["run-unavail"],
        all_historical=False,
    )
    assert report.blocked is True
    assert report.applied is False
    assert report.dispositions[0].action == "block"
    assert report.dispositions[0].classification == "COMPARISON_UNAVAILABLE"


def test_all_historical_empty_set_is_input_error(tmp_path: Path) -> None:
    hist = tmp_path / "hist"
    hist.mkdir()
    current = tmp_path / "current"
    current.mkdir()
    with pytest.raises(IngestAdoptionInputError, match="empty ingest identity set"):
        preview_ingest_adoption(
            current_repo_root=current,
            historical_roots=[("hist", hist)],
            run_ids=None,
            all_historical=True,
        )
