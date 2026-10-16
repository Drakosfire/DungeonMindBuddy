from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_ingest_run_registry import (
    GraphIngestRunSummary,
)
from apps.live_control_server.services.recap_graph_preview_ingest import (
    _candidate_validation_summary,
    _status_from_summary,
)


def _write_candidate_run(
    repo: Path,
    *,
    valid: bool = True,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    mismatch: str | None = None,
) -> GraphIngestRunSummary:
    run_dir = repo / "out/longmont-c2/session-29/run"
    run_dir.mkdir(parents=True)
    candidate_path = run_dir / "candidate_graph.json"
    candidate_bytes = b'{"candidate":true}'
    candidate_path.write_bytes(candidate_bytes)
    candidate_digest = hashlib.sha256(candidate_bytes).hexdigest()
    report = {
        "schema": "dmb_candidate_graph_validation_report_v0",
        "campaign_id": "longmont-c2",
        "session_id": "session-29",
        "candidate_graph_path": candidate_path.relative_to(repo).as_posix(),
        "candidate_graph_sha256": f"sha256:{candidate_digest}",
        "valid": valid,
        "errors": errors or [],
        "warnings": warnings or [],
    }
    if mismatch == "campaign":
        report["campaign_id"] = "another-campaign"
    elif mismatch == "session":
        report["session_id"] = "session-28"
    elif mismatch == "candidate_digest":
        report["candidate_graph_sha256"] = f"sha256:{'0' * 64}"
    elif mismatch == "candidate_path":
        report["candidate_graph_path"] = (
            (run_dir / "another-candidate.json").relative_to(repo).as_posix()
        )

    report_path = run_dir / "candidate_validation_report.json"
    report_bytes = json.dumps(report, sort_keys=True, indent=2).encode("utf-8")
    if mismatch == "malformed_report":
        report_bytes = b"{not-json"
    report_path.write_bytes(report_bytes)
    report_digest = hashlib.sha256(report_bytes).hexdigest()
    if mismatch == "report_hash":
        report_digest = "0" * 64

    manifest = {
        "artifacts": {
            "candidate_graph": {
                "uri": candidate_path.relative_to(repo).as_posix(),
                "sha256": f"sha256:{candidate_digest}",
            },
            "candidate_validation_report": {
                "uri": report_path.relative_to(repo).as_posix(),
                "sha256": f"sha256:{report_digest}",
            },
        },
        "diagnostics": {},
        "health": {},
        "steps": [],
    }
    if mismatch == "candidate_missing":
        manifest["artifacts"].pop("candidate_graph")
    manifest_path = run_dir / "graph_ingest_run_manifest.json"
    if mismatch != "report_missing":
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
        )
    else:
        manifest["artifacts"].pop("candidate_validation_report")
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
        )

    return GraphIngestRunSummary(
        manifest_path=manifest_path.relative_to(repo).as_posix(),
        run_dir=run_dir.relative_to(repo).as_posix(),
        campaign_id="longmont-c2",
        session_id="session-29",
        status="candidate_validation_ready",
        run_label="Session 29 candidate",
    )


def test_status_adapter_exposes_clean_candidate_validation_summary(
    tmp_path: Path,
) -> None:
    repo = tmp_path.resolve()
    summary = _write_candidate_run(repo)

    status = _status_from_summary(repo, summary, normalized_recap_path=None)

    assert status["candidate_validation"] == {
        "state": "valid",
        "error_count": 0,
        "warning_count": 0,
        "unresolved_evidence_reference_count": 0,
    }


@pytest.mark.parametrize(
    ("valid", "errors", "warnings", "expected"),
    [
        (True, [], ["review this low-confidence relation"], "warning"),
        (False, ["candidate violates a graph constraint"], [], "blocked"),
        (True, [], ["unresolved evidence ref span_id: legacy-span:29-31"], "blocked"),
    ],
)
def test_candidate_validation_summary_surfaces_warnings_and_blocks_unresolved_refs(
    tmp_path: Path,
    valid: bool,
    errors: list[str],
    warnings: list[str],
    expected: str,
) -> None:
    repo = tmp_path.resolve()
    summary = _write_candidate_run(repo, valid=valid, errors=errors, warnings=warnings)

    result = _status_from_summary(repo, summary, normalized_recap_path=None)[
        "candidate_validation"
    ]

    assert result["state"] == expected
    assert result["error_count"] == len(errors)
    assert result["warning_count"] == len(warnings)
    assert result["unresolved_evidence_reference_count"] == sum(
        item.casefold().startswith("unresolved evidence ref")
        for item in [*errors, *warnings]
    )


@pytest.mark.parametrize(
    "mismatch",
    [
        "report_hash",
        "campaign",
        "session",
        "candidate_digest",
        "candidate_path",
        "candidate_missing",
        "report_missing",
        "malformed_report",
    ],
)
def test_candidate_validation_summary_fails_closed_when_report_is_untrustworthy(
    tmp_path: Path, mismatch: str
) -> None:
    repo = tmp_path.resolve()
    summary = _write_candidate_run(repo, mismatch=mismatch)
    manifest = json.loads((repo / summary.manifest_path).read_text(encoding="utf-8"))

    assert (
        _candidate_validation_summary(repo, summary, manifest)["state"] == "unavailable"
    )


def test_candidate_validation_summary_fails_closed_if_candidate_changed_after_report(
    tmp_path: Path,
) -> None:
    repo = tmp_path.resolve()
    summary = _write_candidate_run(repo)
    candidate_path = repo / summary.run_dir / "candidate_graph.json"
    candidate_path.write_bytes(b'{"candidate":false}')
    manifest = json.loads((repo / summary.manifest_path).read_text(encoding="utf-8"))

    assert (
        _candidate_validation_summary(repo, summary, manifest)["state"] == "unavailable"
    )
