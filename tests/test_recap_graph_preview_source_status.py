from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.live_control_server.services import recap_graph_preview_ingest


def _normalized_source_digest(source: Path) -> str:
    normalized = source.read_text(encoding="utf-8").rstrip("\n") + "\n"
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def _write_candidate_run(
    repo: Path,
    *,
    source_recap_path: str = "corpus/Session 29 normalized.md",
    source_recap_sha256: str | None = None,
) -> None:
    run_dir = repo / "out/graph_memory/runs/longmont-c2/session-29/run"
    run_dir.mkdir(parents=True)
    candidate_path = run_dir / "candidate_graph.json"
    candidate_bytes = b'{"nodes":[],"edges":[]}'
    candidate_path.write_bytes(candidate_bytes)
    candidate_digest = hashlib.sha256(candidate_bytes).hexdigest()
    report_path = run_dir / "candidate_validation_report.json"
    report = {
        "schema": "dmb_candidate_graph_validation_report_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "session_id": "session-29",
        "candidate_graph_path": candidate_path.relative_to(repo).as_posix(),
        "candidate_graph_sha256": f"sha256:{candidate_digest}",
        "valid": True,
        "errors": [],
        "warnings": [],
    }
    report_bytes = json.dumps(report, sort_keys=True, indent=2).encode("utf-8")
    report_path.write_bytes(report_bytes)
    manifest = {
        "schema": "dmb_graph_ingest_run_manifest_v0",
        "run_id": "run-session-29",
        "campaign_id": "longmont-c2",
        "session_id": "session-29",
        "status": "candidate_validation_ready",
        "source": {
            "normalized_recap_path": source_recap_path,
            **(
                {"normalized_recap_sha256": source_recap_sha256}
                if source_recap_sha256
                else {}
            ),
        },
        "next_actions": ["review_candidate"],
        "artifacts": {
            "candidate_graph": {
                "kind": "candidate_graph",
                "uri": candidate_path.relative_to(repo).as_posix(),
                "sha256": f"sha256:{candidate_digest}",
            },
            "candidate_validation_report": {
                "kind": "candidate_validation_report",
                "uri": report_path.relative_to(repo).as_posix(),
                "sha256": f"sha256:{hashlib.sha256(report_bytes).hexdigest()}",
            },
        },
        "diagnostics": {"extraction_run_id": "run-session-29"},
        "health": {"node_count": 59, "edge_count": 33, "beat_count": 4},
        "steps": [],
    }
    manifest_path = run_dir / "graph_ingest_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_path_only_candidate_is_preserved_but_not_presented_as_current(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path.resolve()
    missing_source = (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 29 - The Meat Mind of Mireward Reach.md"
    )
    _write_candidate_run(repo, source_recap_path=missing_source)
    monkeypatch.delenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", raising=False)

    status = recap_graph_preview_ingest.inspect_recap_graph_preview_status(
        repo_root=repo,
        campaign_id="longmont-c2",
        session=29,
        normalized_recap_path=missing_source,
    )

    assert status["status"] == "source_unverified"
    assert status["artifact_status"] == "candidate_validation_ready"
    assert status["source_match_mode"] == "path_only"
    assert status["artifact_next_actions"] == ["review_candidate"]
    assert status["next_actions"] == ["restore_or_load_verified_source"]
    assert status["extraction_run_id"] == "run-session-29"
    assert status["candidate_graph_path"].endswith("candidate_graph.json")
    assert status["node_count"] == 59
    assert status["edge_count"] == 33
    assert status["candidate_validation"]["state"] == "valid"
    assert "preserved" in status["blocked_reason"]
    assert "before treating this output as current" in status["blocked_reason"]


def test_session_candidate_without_source_path_is_marked_unverified(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path.resolve()
    _write_candidate_run(repo)
    monkeypatch.delenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", raising=False)

    status = recap_graph_preview_ingest.inspect_recap_graph_preview_status(
        repo_root=repo,
        campaign_id="longmont-c2",
        session=29,
        normalized_recap_path=None,
    )

    assert status["status"] == "source_unverified"
    assert status["artifact_status"] == "candidate_validation_ready"
    assert status["source_match_mode"] == "unavailable"
    assert status["next_actions"] == ["restore_or_load_verified_source"]


def test_digest_verified_candidate_keeps_its_artifact_status(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path.resolve()
    source = repo / "corpus/Session 29 normalized.md"
    source.parent.mkdir(parents=True)
    source.write_text("Session 29 normalized source.", encoding="utf-8")
    _write_candidate_run(
        repo,
        source_recap_path=source.relative_to(repo).as_posix(),
        source_recap_sha256=_normalized_source_digest(source),
    )
    monkeypatch.delenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", raising=False)

    status = recap_graph_preview_ingest.inspect_recap_graph_preview_status(
        repo_root=repo,
        campaign_id="longmont-c2",
        session=29,
        normalized_recap_path=str(source),
    )

    assert status["status"] == "candidate_validation_ready"
    assert "artifact_status" not in status
    assert status["source_match_mode"] == "content_digest"
    assert status["next_actions"] == ["review_candidate"]


def test_changed_digest_does_not_use_path_only_candidate_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path.resolve()
    source = repo / "corpus/Session 29 normalized.md"
    source.parent.mkdir(parents=True)
    source.write_text("Changed normalized source.", encoding="utf-8")
    _write_candidate_run(
        repo,
        source_recap_path=source.relative_to(repo).as_posix(),
        source_recap_sha256="sha256:" + hashlib.sha256(b"Old normalized source.\n").hexdigest(),
    )
    monkeypatch.delenv("DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT", raising=False)

    status = recap_graph_preview_ingest.inspect_recap_graph_preview_status(
        repo_root=repo,
        campaign_id="longmont-c2",
        session=29,
        normalized_recap_path=str(source),
    )

    assert status["status"] == "missing"
    assert status["source_match_mode"] == "content_digest"
    assert status["next_actions"] == ["build_graph_preview_bundle"]
