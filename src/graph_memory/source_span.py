from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

SOURCE_SPAN_SCHEMA = "dmb_source_span_evidence_resolver_v0"
SOURCE_SPAN_VERSION = "0.1"

DEFAULT_SNIPPET_MAX_CHARS = 240
DEFAULT_CONTEXT_LINES = 1
DEFAULT_CONTEXT_MAX_CHARS = 500


@dataclass(frozen=True)
class SourceArtifactText:
    source_artifact_id: str
    source_ref_id: str
    artifact_kind: str
    label: str
    text: str
    evidence_role: str
    visibility_state: str


@dataclass(frozen=True)
class SourceArtifactStructured:
    source_artifact_id: str
    source_ref_id: str
    artifact_kind: str
    label: str
    data: Mapping[str, Any]
    evidence_role: str
    visibility_state: str


@dataclass(frozen=True)
class SourceSpanRef:
    source_ref_id: str
    source_artifact_id: str
    source_anchor_id: str | None = None
    artifact_kind: str | None = None
    label: str | None = None
    evidence_role: str | None = None
    visibility_state: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    structured_path: str | None = None


@dataclass(frozen=True)
class ResolvedEvidence:
    source_ref_id: str
    source_artifact_id: str
    source_anchor_id: str | None
    artifact_kind: str
    label: str
    evidence_role: str
    visibility_state: str
    can_open_source: bool
    can_highlight_span: bool
    preview_snippet: str
    surrounding_context: str | None
    start_line: int | None = None
    end_line: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    structured_path: str | None = None
    structured_value_preview: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceResolutionIssue:
    severity: str
    code: str
    message: str
    source_ref_id: str | None = None
    source_artifact_id: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class EvidenceResolutionReport:
    schema: str
    version: str
    total_refs: int
    resolved_refs: int
    unresolved_refs: int
    highlightable_refs: int
    structured_refs: int
    text_span_refs: int
    issue_counts: Mapping[str, int]
    issues: tuple[EvidenceResolutionIssue, ...]


def _issue(severity: str, code: str, message: str, ref: SourceSpanRef, field: str | None = None) -> str:
    return json.dumps({"severity": severity, "code": code, "message": message, "source_ref_id": ref.source_ref_id, "source_artifact_id": ref.source_artifact_id, "field": field}, sort_keys=True)


def _parse_issue(value: str) -> EvidenceResolutionIssue:
    try:
        data = json.loads(value)
        return EvidenceResolutionIssue(**data)
    except Exception:
        return EvidenceResolutionIssue("warning", "legacy_warning", value)


def _clip(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars < 8:
        raise ValueError("snippet_max_chars must be at least 8")
    if len(text) <= max_chars:
        return text, False
    return text[: max_chars - 1].rstrip() + "…", True


def _artifact_for(ref: SourceSpanRef, text_artifacts: Mapping[str, SourceArtifactText], structured_artifacts: Mapping[str, SourceArtifactStructured]) -> SourceArtifactText | SourceArtifactStructured | None:
    if ref.source_artifact_id in text_artifacts:
        return text_artifacts[ref.source_artifact_id]
    return structured_artifacts.get(ref.source_artifact_id)


def _base(ref: SourceSpanRef, artifact: SourceArtifactText | SourceArtifactStructured | None, warnings: list[str], *, openable: bool = False, highlightable: bool = False, snippet: str = "", context: str | None = None, structured_preview: str | None = None) -> ResolvedEvidence:
    return ResolvedEvidence(
        source_ref_id=ref.source_ref_id,
        source_artifact_id=ref.source_artifact_id,
        source_anchor_id=ref.source_anchor_id,
        artifact_kind=ref.artifact_kind or (artifact.artifact_kind if artifact else "unknown"),
        label=ref.label or (artifact.label if artifact else "Unresolved source evidence"),
        evidence_role=ref.evidence_role or (artifact.evidence_role if artifact else "unknown"),
        visibility_state=ref.visibility_state or (artifact.visibility_state if artifact else "unknown"),
        can_open_source=openable,
        can_highlight_span=highlightable,
        preview_snippet=snippet,
        surrounding_context=context,
        start_line=ref.start_line,
        end_line=ref.end_line,
        start_char=ref.start_char,
        end_char=ref.end_char,
        structured_path=ref.structured_path,
        structured_value_preview=structured_preview,
        warnings=tuple(warnings),
    )


def _resolve_dot_path(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not part:
            raise KeyError(path)
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            raise KeyError(path)
    return current


def resolve_source_span_ref(ref: SourceSpanRef, *, text_artifacts: Mapping[str, SourceArtifactText] | None = None, structured_artifacts: Mapping[str, SourceArtifactStructured] | None = None, snippet_max_chars: int = DEFAULT_SNIPPET_MAX_CHARS, context_lines: int = DEFAULT_CONTEXT_LINES) -> ResolvedEvidence:
    text_artifacts = text_artifacts or {}
    structured_artifacts = structured_artifacts or {}
    warnings: list[str] = []
    artifact = _artifact_for(ref, text_artifacts, structured_artifacts)
    if artifact is None:
        warnings.append(_issue("blocker", "missing_source_artifact", "Source artifact is not registered.", ref, "source_artifact_id"))
        return _base(ref, None, warnings)
    if ref.source_ref_id != artifact.source_ref_id:
        warnings.append(_issue("blocker", "source_ref_mismatch", "Source ref does not match the registered artifact source ref.", ref, "source_ref_id"))
        return _base(ref, artifact, warnings, openable=True)
    if ref.evidence_role and ref.evidence_role != artifact.evidence_role:
        warnings.append(_issue("warning", "evidence_role_mismatch", "Evidence role differs from artifact metadata.", ref, "evidence_role"))
    if not (ref.visibility_state or artifact.visibility_state):
        warnings.append(_issue("warning", "visibility_missing", "Visibility state is missing.", ref, "visibility_state"))
    has_text = ref.start_line is not None or ref.end_line is not None or ref.start_char is not None or ref.end_char is not None
    if has_text and ref.structured_path:
        warnings.append(_issue("error", "ambiguous_source_span_ref", "Text span and structured_path cannot both be resolved in v0.", ref))
        return _base(ref, artifact, warnings, openable=True)
    if ref.structured_path:
        if not isinstance(artifact, SourceArtifactStructured):
            warnings.append(_issue("error", "structured_path_missing", "Structured path was supplied for a non-structured artifact.", ref, "structured_path"))
            return _base(ref, artifact, warnings, openable=True)
        try:
            value = _resolve_dot_path(artifact.data, ref.structured_path)
        except KeyError:
            warnings.append(_issue("error", "structured_path_missing", "Structured path is not present in the artifact.", ref, "structured_path"))
            return _base(ref, artifact, warnings, openable=True)
        preview, truncated = _clip(json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value), snippet_max_chars)
        if truncated:
            warnings.append(_issue("warning", "snippet_truncated", "Structured value preview was truncated.", ref, "structured_path"))
        return _base(ref, artifact, warnings, openable=True, highlightable=True, snippet=preview, structured_preview=preview)
    if has_text:
        if not isinstance(artifact, SourceArtifactText):
            warnings.append(_issue("error", "span_out_of_range", "Text span was supplied for a non-text artifact.", ref))
            return _base(ref, artifact, warnings, openable=True)
        lines = artifact.text.splitlines()
        start_line = ref.start_line or 1
        end_line = ref.end_line or start_line
        if start_line < 1 or end_line < start_line or end_line > len(lines):
            warnings.append(_issue("error", "span_out_of_range", "Line span is outside artifact bounds.", ref, "start_line"))
            return _base(ref, artifact, warnings, openable=True)
        selected = "\n".join(lines[start_line - 1 : end_line])
        if ref.start_char is not None or ref.end_char is not None:
            start_char = ref.start_char or 0
            end_char = ref.end_char if ref.end_char is not None else len(selected)
            if start_char < 0 or end_char < start_char or end_char > len(selected):
                warnings.append(_issue("error", "span_out_of_range", "Character span is outside selected text bounds.", ref, "start_char"))
                return _base(ref, artifact, warnings, openable=True)
            selected = selected[start_char:end_char]
        snippet, truncated = _clip(selected, snippet_max_chars)
        if truncated:
            warnings.append(_issue("warning", "snippet_truncated", "Text snippet was truncated.", ref))
        context = None
        if context_lines > 0:
            cstart = max(1, start_line - context_lines)
            cend = min(len(lines), end_line + context_lines)
            context, context_truncated = _clip("\n".join(lines[cstart - 1 : cend]), DEFAULT_CONTEXT_MAX_CHARS)
            if context_truncated:
                warnings.append(_issue("warning", "snippet_truncated", "Surrounding context was truncated.", ref, "surrounding_context"))
        return _base(ref, artifact, warnings, openable=True, highlightable=True, snippet=snippet, context=context)
    warnings.append(_issue("warning", "not_highlightable", "Ref does not include a text span or structured path.", ref))
    return _base(ref, artifact, warnings, openable=True)


def resolve_many_source_span_refs(refs: Sequence[SourceSpanRef], *, text_artifacts: Mapping[str, SourceArtifactText] | None = None, structured_artifacts: Mapping[str, SourceArtifactStructured] | None = None, snippet_max_chars: int = DEFAULT_SNIPPET_MAX_CHARS, context_lines: int = DEFAULT_CONTEXT_LINES) -> tuple[ResolvedEvidence, ...]:
    return tuple(resolve_source_span_ref(ref, text_artifacts=text_artifacts, structured_artifacts=structured_artifacts, snippet_max_chars=snippet_max_chars, context_lines=context_lines) for ref in refs)


def analyze_evidence_resolution(refs: Sequence[SourceSpanRef], resolved: Sequence[ResolvedEvidence]) -> EvidenceResolutionReport:
    issues = tuple(_parse_issue(w) for item in resolved for w in item.warnings)
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
        counts[issue.code] = counts.get(issue.code, 0) + 1
    return EvidenceResolutionReport(SOURCE_SPAN_SCHEMA, SOURCE_SPAN_VERSION, len(refs), sum(1 for r in resolved if r.can_open_source and r.preview_snippet), sum(1 for r in resolved if not (r.can_open_source and r.preview_snippet)), sum(1 for r in resolved if r.can_highlight_span), sum(1 for r in resolved if r.structured_path), sum(1 for r in resolved if r.start_line is not None), counts, issues)


def source_span_ref_from_dict(data: Mapping[str, Any]) -> SourceSpanRef:
    return SourceSpanRef(**{k: data.get(k) for k in SourceSpanRef.__dataclass_fields__})


def source_span_ref_to_dict(ref: SourceSpanRef) -> dict[str, Any]:
    return {k: v for k, v in asdict(ref).items() if v is not None}


def resolved_evidence_to_dict(evidence: ResolvedEvidence) -> dict[str, Any]:
    return {k: v for k, v in asdict(evidence).items() if v is not None and v != ()}


def evidence_resolution_report_to_dict(report: EvidenceResolutionReport) -> dict[str, Any]:
    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["issue_counts"] = dict(report.issue_counts)
    return data


def build_stable_source_span_id(
    *,
    source_artifact_id: str,
    content_sha256: str,
    start_line: int,
    end_line: int,
) -> str:
    """Stable span ID namespaced by source artifact revision digest."""
    if not source_artifact_id.strip():
        raise ValueError("source_artifact_id is required")
    if not content_sha256.strip():
        raise ValueError("content_sha256 is required")
    if start_line < 1 or end_line < start_line:
        raise ValueError("span line range is invalid")
    return (
        f"{source_artifact_id}:span:{content_sha256[:12]}:"
        f"{start_line}-{end_line}"
    )


SOURCE_SPAN_INDEX_SCHEMA = "dmb_source_span_index_v1"
SOURCE_SPAN_INDEX_VERSION = "1.0"


@dataclass(frozen=True)
class SourceSpanIndexEntry:
    source_span_id: str
    source_ref_id: str
    source_artifact_id: str
    content_sha256: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class SourceSpanIndex:
    source_artifact_id: str
    content_sha256: str
    source_ref_id: str
    spans: tuple[SourceSpanIndexEntry, ...]
    schema: str = SOURCE_SPAN_INDEX_SCHEMA
    version: str = SOURCE_SPAN_INDEX_VERSION


def document_source_ref_id(source_artifact_id: str) -> str:
    """Document-level source_ref_id shared by SourceArtifactText and span refs."""
    if not source_artifact_id.strip():
        raise ValueError("source_artifact_id is required")
    return f"{source_artifact_id}:text"


def build_source_span_index_for_text(
    *,
    source_artifact_id: str,
    content_sha256: str,
    text: str,
) -> SourceSpanIndex:
    """Build a stable paragraph-span index bound to an exact artifact digest."""
    if not content_sha256.strip():
        raise ValueError("content_sha256 is required")
    source_ref_id = document_source_ref_id(source_artifact_id)
    lines = text.splitlines()
    spans: list[SourceSpanIndexEntry] = []
    paragraph_start: int | None = None
    for index, line in enumerate(lines, start=1):
        if line.strip():
            if paragraph_start is None:
                paragraph_start = index
            continue
        if paragraph_start is not None:
            end_line = index - 1
            spans.append(
                _span_entry(
                    source_artifact_id=source_artifact_id,
                    content_sha256=content_sha256,
                    source_ref_id=source_ref_id,
                    start_line=paragraph_start,
                    end_line=end_line,
                )
            )
            paragraph_start = None
    if paragraph_start is not None:
        spans.append(
            _span_entry(
                source_artifact_id=source_artifact_id,
                content_sha256=content_sha256,
                source_ref_id=source_ref_id,
                start_line=paragraph_start,
                end_line=len(lines),
            )
        )
    if not spans and text.strip():
        spans.append(
            _span_entry(
                source_artifact_id=source_artifact_id,
                content_sha256=content_sha256,
                source_ref_id=source_ref_id,
                start_line=1,
                end_line=max(1, len(lines)),
            )
        )
    return SourceSpanIndex(
        source_artifact_id=source_artifact_id,
        content_sha256=content_sha256,
        source_ref_id=source_ref_id,
        spans=tuple(spans),
    )


def _span_entry(
    *,
    source_artifact_id: str,
    content_sha256: str,
    source_ref_id: str,
    start_line: int,
    end_line: int,
) -> SourceSpanIndexEntry:
    span_id = build_stable_source_span_id(
        source_artifact_id=source_artifact_id,
        content_sha256=content_sha256,
        start_line=start_line,
        end_line=end_line,
    )
    return SourceSpanIndexEntry(
        source_span_id=span_id,
        source_ref_id=source_ref_id,
        source_artifact_id=source_artifact_id,
        content_sha256=content_sha256,
        start_line=start_line,
        end_line=end_line,
    )


def validate_source_span_index(
    index: SourceSpanIndex,
    *,
    source_artifact_id: str,
    content_sha256: str,
) -> None:
    """Fail closed when an index is not bound to the exact artifact revision."""
    if index.source_artifact_id != source_artifact_id:
        raise ValueError("source_span_index source_artifact_id mismatch")
    if index.content_sha256 != content_sha256:
        raise ValueError("source_span_index content_sha256 mismatch")
    expected_ref = document_source_ref_id(source_artifact_id)
    if index.source_ref_id != expected_ref:
        raise ValueError("source_span_index source_ref_id mismatch")
    if not index.spans:
        raise ValueError("source_span_index must contain at least one span")
    for span in index.spans:
        if span.source_artifact_id != source_artifact_id:
            raise ValueError("span source_artifact_id mismatch")
        if span.content_sha256 != content_sha256:
            raise ValueError("span content_sha256 mismatch")
        if span.source_ref_id != expected_ref:
            raise ValueError("span source_ref_id mismatch")
        expected_id = build_stable_source_span_id(
            source_artifact_id=source_artifact_id,
            content_sha256=content_sha256,
            start_line=span.start_line,
            end_line=span.end_line,
        )
        if span.source_span_id != expected_id:
            raise ValueError("span id is not namespaced by artifact digest")


def source_span_index_to_dict(index: SourceSpanIndex) -> dict[str, Any]:
    return {
        "schema": index.schema,
        "version": index.version,
        "source_artifact_id": index.source_artifact_id,
        "content_sha256": index.content_sha256,
        "source_ref_id": index.source_ref_id,
        "spans": [asdict(span) for span in index.spans],
    }


def source_span_index_from_dict(data: Mapping[str, Any]) -> SourceSpanIndex:
    spans_raw = data.get("spans") or []
    spans = tuple(
        SourceSpanIndexEntry(
            source_span_id=str(row["source_span_id"]),
            source_ref_id=str(row["source_ref_id"]),
            source_artifact_id=str(row["source_artifact_id"]),
            content_sha256=str(row["content_sha256"]),
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
        )
        for row in spans_raw
    )
    index = SourceSpanIndex(
        schema=str(data.get("schema") or SOURCE_SPAN_INDEX_SCHEMA),
        version=str(data.get("version") or SOURCE_SPAN_INDEX_VERSION),
        source_artifact_id=str(data["source_artifact_id"]),
        content_sha256=str(data["content_sha256"]),
        source_ref_id=str(data["source_ref_id"]),
        spans=spans,
    )
    validate_source_span_index(
        index,
        source_artifact_id=index.source_artifact_id,
        content_sha256=index.content_sha256,
    )
    return index


def source_span_refs_from_index(index: SourceSpanIndex) -> tuple[SourceSpanRef, ...]:
    return tuple(
        SourceSpanRef(
            source_ref_id=span.source_ref_id,
            source_artifact_id=span.source_artifact_id,
            source_anchor_id=span.source_span_id,
            start_line=span.start_line,
            end_line=span.end_line,
            evidence_role="source",
            visibility_state="internal",
            artifact_kind="worldbuilding_markdown",
            label=span.source_span_id,
        )
        for span in index.spans
    )


def source_artifact_text_from_markdown(
    *,
    source_artifact_id: str,
    text: str,
    label: str | None = None,
    visibility_state: str = "internal",
) -> SourceArtifactText:
    return SourceArtifactText(
        source_artifact_id=source_artifact_id,
        source_ref_id=document_source_ref_id(source_artifact_id),
        artifact_kind="worldbuilding_markdown",
        label=label or source_artifact_id,
        text=text,
        evidence_role="source",
        visibility_state=visibility_state,
    )


def validate_source_span_ref_for_artifact(
    ref: SourceSpanRef,
    *,
    source_artifact_id: str,
    content_sha256: str,
) -> None:
    """Require span refs to be digest-namespaced for an exact artifact revision."""
    if ref.source_artifact_id != source_artifact_id:
        raise ValueError("source_span_ref source_artifact_id mismatch")
    if ref.source_ref_id != document_source_ref_id(source_artifact_id):
        raise ValueError("source_span_ref source_ref_id mismatch")
    if ref.start_line is None or ref.end_line is None:
        raise ValueError("source_span_ref requires start_line and end_line")
    expected = build_stable_source_span_id(
        source_artifact_id=source_artifact_id,
        content_sha256=content_sha256,
        start_line=ref.start_line,
        end_line=ref.end_line,
    )
    if ref.source_anchor_id != expected:
        raise ValueError("source_span_ref is not namespaced by artifact digest")
