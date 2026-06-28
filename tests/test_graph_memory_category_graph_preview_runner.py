from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    compute_sha256,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import (
    GraphIngestRunStatus,
    validate_graph_ingest_run_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests/fixtures/graph_memory/category_preview_runner"
RECAP_PATH = FIXTURE_DIR / "session_24_normalized_recap.md"
CANDIDATE_PATH = FIXTURE_DIR / "candidate_graph_fixture.json"


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def _copy_recap_to_tmp(tmp_path: Path) -> Path:
    source = tmp_path / "session_24_normalized_recap.md"
    source.write_text(RECAP_PATH.read_text())
    return source


def _copy_candidate_to_tmp(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate_graph_fixture.json"
    candidate.write_text(CANDIDATE_PATH.read_text())
    return candidate


def test_runner_writes_manifest_for_arbitrary_session_without_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("evals/graph_memory_layer/runs/graph_ingest/session_24"),
        )
    )

    assert result.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    assert result.manifest_path.exists()
    assert result.candidate_graph_path is None
    assert result.source_span_bundle_dir is not None
    assert (result.output_dir / "source_span_index.json").exists()


def test_runner_manifest_uses_supplied_campaign_and_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="custom-campaign",
            session_id="session-99",
            normalized_recap_path=source,
            output_dir=Path("runs/session_99"),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert manifest["campaign_id"] == "custom-campaign"
    assert manifest["session_id"] == "session-99"
    assert (
        manifest["source"]["source_artifact_id"]
        == "artifact:recap:custom-campaign:session-99"
    )


def test_runner_manifest_records_normalized_recap_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24"),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert manifest["source"]["normalized_recap_sha256"] == compute_sha256(source)


def test_runner_manifest_ends_at_source_span_bundle_ready_without_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24"),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert manifest["status"] == "source_span_bundle_ready"
    assert manifest["diagnostics"]["candidate_extraction"] is False
    assert "preview_union_store" not in manifest["artifacts"]


def test_runner_does_not_require_gold_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/no_gold"),
        )
    )

    assert result.manifest_path.exists()


def test_runner_required_gold_mode_fails_when_gold_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    with pytest.raises(FileNotFoundError, match="required_gold"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=Path("runs/missing_gold"),
                comparison_mode="required_gold",
                gold_path=Path("missing-gold.json"),
            )
        )


def test_runner_rejects_absolute_output_dir_or_unsafe_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    with pytest.raises(ValueError, match="output_dir must be repo-relative"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=tmp_path / "absolute",
            )
        )
    with pytest.raises(ValueError, match="path traversal"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=Path("../escape"),
            )
        )


def test_runner_outputs_validate_with_graph_ingest_manifest_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/valid_manifest"),
        )
    )

    report = validate_graph_ingest_run_manifest(_load_manifest(result.manifest_path))
    assert report["valid"] is True
    assert report["errors"] == []


def test_runner_can_wrap_existing_candidate_graph_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    candidate = _copy_candidate_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_ready"),
            candidate_graph_path=candidate,
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert result.candidate_graph_path is not None
    assert result.validation_report_path is not None
    assert manifest["status"] == "candidate_validation_ready"
    assert "candidate_graph" in manifest["artifacts"]
    assert "candidate_validation_report" in manifest["artifacts"]
    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True


def test_runner_failed_candidate_validation_does_not_reach_candidate_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    invalid_candidate = tmp_path / "invalid_candidate_graph.json"
    payload = json.loads(CANDIDATE_PATH.read_text())
    payload["diagnostics"]["canon_promotion"] = True
    invalid_candidate.write_text(json.dumps(payload))

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/invalid_candidate"),
            candidate_graph_path=invalid_candidate,
        )
    )
    manifest = _load_manifest(result.manifest_path)
    assert result.validation_report_path is not None
    validation_report = json.loads(result.validation_report_path.read_text())

    assert result.status == GraphIngestRunStatus.FAILED
    assert manifest["status"] == "failed"
    assert manifest["health"]["candidate_graph_valid"] is False
    assert "forbidden lifecycle flag is true: canon_promotion" in manifest["errors"]
    assert manifest["next_actions"] == ["fix_candidate_graph"]
    assert manifest["steps"][-1]["id"] == "validate_candidate_graph"
    assert manifest["steps"][-1]["state"] == "failed"
    assert validation_report["valid"] is False
    assert (
        "forbidden lifecycle flag is true: canon_promotion"
        in validation_report["errors"]
    )
