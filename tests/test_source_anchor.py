from __future__ import annotations

import blake3

from src.ingestion.source_anchor import (
    SourceAnchor,
    build_recap_extracted_anchor,
    hash_source_bytes,
    lint_source_anchors,
    slice_file_lines_to_bytes,
)


def test_hash_source_bytes_matches_blake3_hex() -> None:
    b = b"hello corpus"
    assert hash_source_bytes(b) == blake3.blake3(b).hexdigest()


def test_slice_file_lines_to_bytes_inclusive_1based() -> None:
    lines = ["a", "b", "c", "d"]
    assert slice_file_lines_to_bytes(lines, line_start_1=2, line_end_1=3) == b"b\nc"


def test_build_recap_extracted_anchor_content_hash() -> None:
    lines = ["# H", "", "body line", "more"]
    span, anchor = build_recap_extracted_anchor(
        corpus_source_path="world/mirathorn.md",
        full_file_lines=lines,
        line_start_1=3,
        line_end_1=4,
        commit_sha="abc1234",
    )
    assert span == {"start": 3, "end": 4}
    assert anchor.path == "world/mirathorn.md"
    assert anchor.line_start == 3
    assert anchor.line_end == 4
    assert anchor.commit_sha == "abc1234"
    raw = slice_file_lines_to_bytes(lines, line_start_1=3, line_end_1=4)
    assert anchor.content_hash == hash_source_bytes(raw)


def test_source_anchor_json_round_trip() -> None:
    a = SourceAnchor(
        source_type="legacy_unanchored",
        path="x.md",
        line_start=1,
        line_end=2,
        content_hash="0" * 64,
        commit_sha="",
        agent=None,
        thread_id=None,
    )
    b = SourceAnchor.from_json_dict(a.to_json_dict())
    assert a == b


def test_lint_source_anchors_passes_for_valid_anchor(tmp_path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    rel = "Longmont/session.md"
    source_file = corpus_root / rel
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("line one\nline two\nline three\n", encoding="utf-8")
    lines = source_file.read_text(encoding="utf-8").splitlines()
    _, anchor = build_recap_extracted_anchor(
        corpus_source_path=rel,
        full_file_lines=lines,
        line_start_1=2,
        line_end_1=3,
        commit_sha="abc123",
    )
    report = lint_source_anchors(
        corpus_root=corpus_root,
        evidence_units=[{"evidence_id": "e1", "source_anchors": [anchor.to_json_dict()]}],
        facts=[],
    )
    assert report["ok"] is True
    assert report["summary"]["anchors_valid"] == 1
    assert report["issues"] == []


def test_lint_source_anchors_reports_hash_mismatch_and_relocation_candidates(tmp_path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    rel = "Longmont/session.md"
    source_file = corpus_root / rel
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("wrong\ntarget\nalso wrong\ntarget\n", encoding="utf-8")
    expected_hash = hash_source_bytes(b"target")
    anchor = SourceAnchor(
        source_type="recap_extracted",
        path=rel,
        line_start=1,
        line_end=1,
        content_hash=expected_hash,
        commit_sha="abc123",
    )
    report = lint_source_anchors(
        corpus_root=corpus_root,
        evidence_units=[{"evidence_id": "e1", "source_anchors": [anchor.to_json_dict()]}],
        facts=[],
    )
    assert report["ok"] is False
    assert report["summary"]["anchors_with_issues"] == 1
    issue = report["issues"][0]
    assert issue["issue"] == "hash_mismatch"
    assert {"line_start": 2, "line_end": 2} in issue["relocation_candidates"]


def test_lint_source_anchors_skips_legacy_unanchored_by_default(tmp_path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    anchor = SourceAnchor(
        source_type="legacy_unanchored",
        path="ignored.md",
        line_start=1,
        line_end=1,
        content_hash="0" * 64,
        commit_sha="",
    )
    report = lint_source_anchors(
        corpus_root=corpus_root,
        evidence_units=[{"evidence_id": "e1", "source_anchors": [anchor.to_json_dict()]}],
        facts=[],
    )
    assert report["ok"] is True
    assert report["summary"]["anchors_skipped_legacy_unanchored"] == 1
