"""Citation-grounded provenance for corpus ingestion (SourceAnchor v0).

See Docs/Design/DESIGN-citation-grounded-corpus-architecture.md.
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import blake3

SourceType = Literal[
    "recap_extracted",
    "human_direct",
    "live_planning_collab",
    "derived_from_transcript",
    "legacy_unanchored",
]


@dataclass(frozen=True)
class SourceAnchor:
    """One machine-checkable link from derived text back to corpus bytes."""

    source_type: SourceType
    path: str
    line_start: int
    line_end: int
    content_hash: str
    commit_sha: str
    agent: str | None = None
    thread_id: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Normalize keys for JSON / store payloads
        return d

    @classmethod
    def from_json_dict(cls, raw: dict[str, Any]) -> SourceAnchor:
        return cls(
            source_type=raw["source_type"],  # type: ignore[arg-type]
            path=str(raw["path"]),
            line_start=int(raw["line_start"]),
            line_end=int(raw["line_end"]),
            content_hash=str(raw["content_hash"]),
            commit_sha=str(raw.get("commit_sha", "")),
            agent=raw.get("agent"),
            thread_id=raw.get("thread_id"),
        )


def hash_source_bytes(body: bytes) -> str:
    """Full 32-byte blake3 digest as 64-char hex (matches schema pattern)."""
    return blake3.blake3(body).hexdigest()


def slice_file_lines_to_bytes(lines: list[str], *, line_start_1: int, line_end_1: int) -> bytes:
    """Inclusive 1-based line numbers, matching evidence_unit.line_span / design doc."""
    if line_start_1 < 1 or line_end_1 < line_start_1:
        raise ValueError(
            f"Invalid line range: start={line_start_1} end={line_end_1} (expected 1-based inclusive)"
        )
    s0 = line_start_1 - 1
    e0 = line_end_1  # exclusive end index for slice → inclusive end line_end_1
    chunk = lines[s0:e0]
    return "\n".join(chunk).encode("utf-8")


def build_recap_extracted_anchor(
    *,
    corpus_source_path: str,
    full_file_lines: list[str],
    line_start_1: int,
    line_end_1: int,
    commit_sha: str,
) -> tuple[dict[str, int], SourceAnchor]:
    """Return (line_span dict, anchor) for one contiguous span in the on-disk file."""
    raw = slice_file_lines_to_bytes(full_file_lines, line_start_1=line_start_1, line_end_1=line_end_1)
    digest = hash_source_bytes(raw)
    anchor = SourceAnchor(
        source_type="recap_extracted",
        path=corpus_source_path,
        line_start=line_start_1,
        line_end=line_end_1,
        content_hash=digest,
        commit_sha=commit_sha,
        agent=None,
        thread_id=None,
    )
    return {"start": line_start_1, "end": line_end_1}, anchor


def _find_matching_line_spans(
    lines: list[str],
    *,
    expected_hash: str,
    line_count: int,
    max_matches: int = 5,
) -> list[dict[str, int]]:
    if line_count <= 0:
        return []
    total = len(lines)
    if total == 0 or line_count > total:
        return []
    matches: list[dict[str, int]] = []
    for start_1 in range(1, total - line_count + 2):
        end_1 = start_1 + line_count - 1
        raw = slice_file_lines_to_bytes(lines, line_start_1=start_1, line_end_1=end_1)
        if hash_source_bytes(raw) == expected_hash:
            matches.append({"line_start": start_1, "line_end": end_1})
            if len(matches) >= max_matches:
                break
    return matches


def lint_source_anchors(
    *,
    corpus_root: Path,
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    event_records: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
    include_legacy_unanchored: bool = False,
) -> dict[str, Any]:
    """
    Validate SourceAnchor hashes against current corpus bytes (HEAD workspace view).

    The report is JSON-serializable and intended for CLI lint/audit surfaces.
    """
    issues: list[dict[str, Any]] = []
    summary = {
        "records_checked": 0,
        "records_missing_source_anchors": 0,
        "anchors_total": 0,
        "anchors_validated": 0,
        "anchors_valid": 0,
        "anchors_skipped_legacy_unanchored": 0,
        "anchors_with_issues": 0,
    }
    rootspec = corpus_root.resolve()
    groups: list[tuple[str, list[dict[str, Any]], str]] = [
        ("evidence_units", evidence_units, "evidence_id"),
        ("facts", facts, "fact_id"),
        ("event_records", event_records or [], "event_name"),
        ("claims", claims or [], "subject"),
    ]

    for record_type, records, id_field in groups:
        for idx, record in enumerate(records):
            summary["records_checked"] += 1
            record_id = str(record.get(id_field, "")).strip() or f"{record_type}[{idx}]"
            anchors_raw = record.get("source_anchors")
            if not isinstance(anchors_raw, list) or not anchors_raw:
                summary["records_missing_source_anchors"] += 1
                continue
            for anchor_idx, raw in enumerate(anchors_raw):
                summary["anchors_total"] += 1
                if not isinstance(raw, dict):
                    issues.append(
                        {
                            "record_type": record_type,
                            "record_id": record_id,
                            "anchor_index": anchor_idx,
                            "issue": "malformed_anchor",
                            "detail": "anchor entry is not an object",
                        }
                    )
                    continue
                try:
                    anchor = SourceAnchor.from_json_dict(raw)
                except Exception as exc:
                    issues.append(
                        {
                            "record_type": record_type,
                            "record_id": record_id,
                            "anchor_index": anchor_idx,
                            "issue": "malformed_anchor",
                            "detail": str(exc),
                        }
                    )
                    continue
                if anchor.source_type == "legacy_unanchored" and not include_legacy_unanchored:
                    summary["anchors_skipped_legacy_unanchored"] += 1
                    continue

                summary["anchors_validated"] += 1
                source_path = Path(anchor.path)
                resolved = source_path if source_path.is_absolute() else (rootspec / source_path)
                if not resolved.exists():
                    issues.append(
                        {
                            "record_type": record_type,
                            "record_id": record_id,
                            "anchor_index": anchor_idx,
                            "issue": "missing_source_file",
                            "path": anchor.path,
                        }
                    )
                    continue
                try:
                    lines = resolved.read_text(encoding="utf-8").splitlines()
                except OSError as exc:
                    issues.append(
                        {
                            "record_type": record_type,
                            "record_id": record_id,
                            "anchor_index": anchor_idx,
                            "issue": "unreadable_source_file",
                            "path": anchor.path,
                            "detail": str(exc),
                        }
                    )
                    continue

                if anchor.line_start < 1 or anchor.line_end < anchor.line_start:
                    issues.append(
                        {
                            "record_type": record_type,
                            "record_id": record_id,
                            "anchor_index": anchor_idx,
                            "issue": "invalid_line_range",
                            "path": anchor.path,
                            "line_start": anchor.line_start,
                            "line_end": anchor.line_end,
                        }
                    )
                    continue
                if anchor.line_end > len(lines):
                    issues.append(
                        {
                            "record_type": record_type,
                            "record_id": record_id,
                            "anchor_index": anchor_idx,
                            "issue": "line_range_out_of_bounds",
                            "path": anchor.path,
                            "line_start": anchor.line_start,
                            "line_end": anchor.line_end,
                            "total_lines": len(lines),
                        }
                    )
                    continue

                raw_bytes = slice_file_lines_to_bytes(
                    lines,
                    line_start_1=anchor.line_start,
                    line_end_1=anchor.line_end,
                )
                actual_hash = hash_source_bytes(raw_bytes)
                if actual_hash == anchor.content_hash:
                    summary["anchors_valid"] += 1
                    continue

                line_count = anchor.line_end - anchor.line_start + 1
                candidates = _find_matching_line_spans(
                    lines,
                    expected_hash=anchor.content_hash,
                    line_count=line_count,
                    max_matches=5,
                )
                issues.append(
                    {
                        "record_type": record_type,
                        "record_id": record_id,
                        "anchor_index": anchor_idx,
                        "issue": "hash_mismatch",
                        "path": anchor.path,
                        "line_start": anchor.line_start,
                        "line_end": anchor.line_end,
                        "expected_hash": anchor.content_hash,
                        "actual_hash": actual_hash,
                        "relocation_candidates": candidates,
                    }
                )

    summary["anchors_with_issues"] = len(issues)
    return {
        "ok": len(issues) == 0,
        "corpus_root": rootspec.as_posix(),
        "summary": summary,
        "issues": issues,
    }


def anchor_bytes_verify_at_head(*, corpus_root: Path, raw: dict[str, Any]) -> str | None:
    """
    Return ``None`` iff *raw* is a ``SourceAnchor`` JSON dict whose ``content_hash`` matches
    the UTF-8 bytes of the anchored line span in the file under *corpus_root* **right now**.

    ``commit_sha`` is intentionally ignored here: this is the same HEAD-shaped audit as
    ``lint_source_anchors`` (rebind / drift is a separate policy layer).
    """
    try:
        anchor = SourceAnchor.from_json_dict(raw)
    except Exception as exc:  # noqa: BLE001 — surface malformed anchors verbatim
        return f"malformed_anchor:{exc}"
    if anchor.source_type == "legacy_unanchored":
        return "legacy_unanchored_not_verifiable"
    source_path = Path(anchor.path)
    resolved = source_path if source_path.is_absolute() else (corpus_root / source_path)
    if not resolved.exists():
        return "missing_source_file"
    try:
        lines = resolved.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return f"unreadable_source_file:{exc}"
    if anchor.line_start < 1 or anchor.line_end < anchor.line_start:
        return "invalid_line_range"
    if anchor.line_end > len(lines):
        return "line_range_out_of_bounds"
    raw_bytes = slice_file_lines_to_bytes(
        lines,
        line_start_1=anchor.line_start,
        line_end_1=anchor.line_end,
    )
    if hash_source_bytes(raw_bytes) != anchor.content_hash:
        return "hash_mismatch"
    return None


def resolve_git_commit_sha(*, cwd: Path | None = None) -> str:
    """Return `git rev-parse HEAD` at extraction time, or empty string if unavailable."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd) if cwd is not None else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if proc.returncode != 0:
            return ""
        sha = (proc.stdout or "").strip()
        return sha if len(sha) >= 7 else ""
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""


def body_first_line_0based_in_file(markdown: str, body: str) -> int:
    """0-based index of the first line of `body` within `markdown.splitlines()`."""
    if not body.strip():
        return 0
    idx = markdown.find(body)
    if idx < 0:
        return 0
    return markdown[:idx].count("\n")
