from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.citation_source_reader import (
    CitationSourceError,
    _resolve_under_repo,
    _validate_relative_source_path,
)

MAX_FRESHNESS_BYTES = 200_000
FingerprintAlgorithm = Literal["sha256:source-lines-v1", "sha256:locator-v1"]
FreshnessStatus = Literal["current", "changed", "unknown", "unavailable"]


class CitationFreshnessRequest(BaseModel):
    path: str = Field(min_length=1)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    expected_fingerprint: str | None = None
    fingerprint_algorithm: FingerprintAlgorithm | None = None


class CitationFreshnessResponse(BaseModel):
    schema: Literal["dmb_citation_freshness_v1"] = "dmb_citation_freshness_v1"
    path: str
    status: FreshnessStatus
    current_fingerprint: str | None = None
    expected_fingerprint: str | None = None
    fingerprint_algorithm: FingerprintAlgorithm = "sha256:source-lines-v1"
    checked_at: str
    diagnostics: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _checked_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bounded_text(path: Path) -> tuple[str | None, list[str], list[str]]:
    data = path.read_bytes()
    warnings: list[str] = []
    diagnostics = ["read-only freshness lookup", "no source content returned", "no events or jobs written"]
    if len(data) > MAX_FRESHNESS_BYTES:
        warnings.append(f"source exceeds freshness read cap of {MAX_FRESHNESS_BYTES} bytes")
        return None, diagnostics, warnings
    return data.decode("utf-8", errors="replace"), diagnostics, warnings


def _selected_lines(text: str, line_start: int | None, line_end: int | None) -> tuple[str, list[str]]:
    if line_start is None and line_end is None:
        return text, []
    lines = text.splitlines()
    if not lines:
        return "", ["source has no lines to hash"]
    start = line_start or line_end or 1
    end = line_end or line_start or start
    start = max(1, min(start, len(lines)))
    end = max(start, min(end, len(lines)))
    return "\n".join(lines[start - 1 : end]), []


def check_citation_freshness(root: Path, request: CitationFreshnessRequest) -> CitationFreshnessResponse:
    rel = _validate_relative_source_path(request.path)
    try:
        source_path = _resolve_under_repo(root, rel)
    except CitationSourceError as exc:
        if exc.status_code == 404:
            return CitationFreshnessResponse(
                path=rel.as_posix(),
                status="unavailable",
                expected_fingerprint=request.expected_fingerprint,
                fingerprint_algorithm=request.fingerprint_algorithm or "sha256:source-lines-v1",
                checked_at=_checked_at(),
                diagnostics=["read-only freshness lookup", "no source content returned", "no events or jobs written"],
                warnings=["citation source could not be found"],
            )
        raise

    text, diagnostics, warnings = _bounded_text(source_path)
    algorithm: FingerprintAlgorithm = "sha256:source-lines-v1"
    if text is None:
        return CitationFreshnessResponse(
            path=rel.as_posix(),
            status="unknown",
            expected_fingerprint=request.expected_fingerprint,
            fingerprint_algorithm=algorithm,
            checked_at=_checked_at(),
            diagnostics=diagnostics,
            warnings=warnings,
        )

    selected, selection_warnings = _selected_lines(text, request.line_start, request.line_end)
    warnings.extend(selection_warnings)
    current_fingerprint = _sha256(selected)
    expected = request.expected_fingerprint or None
    if not expected:
        status: FreshnessStatus = "unknown"
        warnings.append("no expected source-lines fingerprint supplied for comparison")
    elif request.fingerprint_algorithm and request.fingerprint_algorithm != algorithm:
        status = "unknown"
        warnings.append("stored fingerprint algorithm cannot prove source-line freshness")
    else:
        status = "current" if expected == current_fingerprint else "changed"

    return CitationFreshnessResponse(
        path=rel.as_posix(),
        status=status,
        current_fingerprint=current_fingerprint,
        expected_fingerprint=expected,
        fingerprint_algorithm=algorithm,
        checked_at=_checked_at(),
        diagnostics=diagnostics,
        warnings=warnings,
    )
