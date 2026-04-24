from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import blake3

from src.contracts.schema_validation import validate_many
from src.ingestion.docx_converter import docx_to_markdown, markdown_passthrough
from src.ingestion.frontmatter import DocumentMetadata, parse_document_frontmatter
from src.ingestion.source_anchor import (
    body_first_line_0based_in_file,
    build_recap_extracted_anchor,
    resolve_git_commit_sha,
)


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SESSION_RE = re.compile(r"\bsession\s+(\d+)\b", re.IGNORECASE)


@dataclass
class _ASTNode:
    node_type: str
    level: int
    text: str
    line_start: int
    line_end: int
    children: list["_ASTNode"] = field(default_factory=list)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _classify_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return "blank"
    if _HEADING_RE.match(stripped):
        return "heading"
    return "text"


def _segment_blocks(lines: list[str]) -> list[tuple[str, int, int, str]]:
    blocks: list[tuple[str, int, int, str]] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        line_kind = _classify_line(line)
        if line_kind == "blank":
            idx += 1
            continue
        if line_kind == "heading":
            blocks.append(("heading", idx, idx + 1, line.strip()))
            idx += 1
            continue

        start = idx
        paragraph_lines: list[str] = []
        while idx < len(lines):
            if _classify_line(lines[idx]) == "heading":
                break
            if lines[idx].strip():
                paragraph_lines.append(lines[idx].strip())
            elif paragraph_lines:
                break
            idx += 1
        if paragraph_lines:
            blocks.append(("paragraph", start, idx, "\n".join(paragraph_lines).strip()))
        else:
            idx += 1
    return blocks


def _build_heading_tree(blocks: list[tuple[str, int, int, str]]) -> _ASTNode:
    root = _ASTNode(node_type="root", level=0, text="", line_start=0, line_end=0)
    stack: list[tuple[int, _ASTNode]] = [(0, root)]

    for block_type, start, end, text in blocks:
        if block_type == "heading":
            match = _HEADING_RE.match(text)
            if not match:
                continue
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            node = _ASTNode(
                node_type="heading",
                level=level,
                text=heading_text,
                line_start=start,
                line_end=end,
            )
            while stack and stack[-1][0] >= level:
                stack.pop()
            if not stack:
                stack = [(0, root)]
            stack[-1][1].children.append(node)
            stack.append((level, node))
            continue

        node = _ASTNode(
            node_type="paragraph",
            level=0,
            text=text,
            line_start=start,
            line_end=end,
        )
        stack[-1][1].children.append(node)

    return root


def _compute_evidence_id(document_id: str, section_path: list[str], text: str) -> str:
    payload = f"{document_id}|{' > '.join(section_path)}|{text}"
    digest = blake3.blake3(payload.encode("utf-8")).hexdigest()[:16]
    return f"evid_{digest}"


def _line_span_and_anchors(
    *,
    body_line_start_0: int,
    body_line_end_exclusive_0: int,
    body_line_offset: int,
    full_file_lines: list[str],
    corpus_source_path: str,
    commit_sha: str,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """Map body-relative 0-based half-open span to on-disk 1-based inclusive line_span + anchor."""
    file_start_1 = body_line_offset + body_line_start_0 + 1
    file_end_1 = body_line_offset + body_line_end_exclusive_0
    line_span, anchor = build_recap_extracted_anchor(
        corpus_source_path=corpus_source_path,
        full_file_lines=full_file_lines,
        line_start_1=file_start_1,
        line_end_1=file_end_1,
        commit_sha=commit_sha,
    )
    return line_span, [anchor.to_json_dict()]


def _infer_session_from_section_path(section_path: list[str]) -> int | None:
    for section in reversed(section_path):
        match = _SESSION_RE.search(section)
        if match:
            return int(match.group(1))
    return None


def _walk_tree(
    node: _ASTNode,
    path: list[str],
    units: list[dict[str, Any]],
    counter: list[int],
    document_id: str,
    document_type: str,
    document_title: str,
    source_class: str,
    canon_layer: str,
    campaign_id: str | None,
    document_temporal_scope: str | None,
    document_session: int | None,
    document_origin_session: int | None,
    document_last_updated_session: int | None,
    *,
    full_file_lines: list[str],
    body_line_offset: int,
    corpus_source_path: str,
    commit_sha: str,
) -> None:
    if node.node_type == "root":
        for child in node.children:
            _walk_tree(
                node=child,
                path=path,
                units=units,
                counter=counter,
                document_id=document_id,
                document_type=document_type,
                document_title=document_title,
                source_class=source_class,
                canon_layer=canon_layer,
                campaign_id=campaign_id,
                document_temporal_scope=document_temporal_scope,
                document_session=document_session,
                document_origin_session=document_origin_session,
                document_last_updated_session=document_last_updated_session,
                full_file_lines=full_file_lines,
                body_line_offset=body_line_offset,
                corpus_source_path=corpus_source_path,
                commit_sha=commit_sha,
            )
        return

    if node.node_type == "heading":
        child_path = path + [node.text]
        if node.children:
            # Heading absorption: prefix heading text into the first child.
            first = node.children[0]
            if first.node_type == "paragraph" and first.text:
                first.text = f"{node.text} -- {first.text}"
                # Heading absorption: span must cover the heading line + paragraph lines so
                # SourceAnchor bytes match on-disk markdown (see DESIGN-citation-grounded-corpus).
                first.line_start = min(node.line_start, first.line_start)
                first.line_end = max(node.line_end, first.line_end)
            for child in node.children:
                _walk_tree(
                    node=child,
                    path=child_path,
                    units=units,
                    counter=counter,
                    document_id=document_id,
                    document_type=document_type,
                    document_title=document_title,
                    source_class=source_class,
                    canon_layer=canon_layer,
                    campaign_id=campaign_id,
                    document_temporal_scope=document_temporal_scope,
                    document_session=document_session,
                    document_origin_session=document_origin_session,
                    document_last_updated_session=document_last_updated_session,
                    full_file_lines=full_file_lines,
                    body_line_offset=body_line_offset,
                    corpus_source_path=corpus_source_path,
                    commit_sha=commit_sha,
                )
        else:
            now_iso = _now_utc_iso()
            evidence_id = _compute_evidence_id(
                document_id=document_id,
                section_path=child_path,
                text=node.text.strip(),
            )
            line_span, source_anchors = _line_span_and_anchors(
                body_line_start_0=node.line_start,
                body_line_end_exclusive_0=node.line_end,
                body_line_offset=body_line_offset,
                full_file_lines=full_file_lines,
                corpus_source_path=corpus_source_path,
                commit_sha=commit_sha,
            )
            units.append(
                {
                    "schema_version": "0.1.0",
                    "created_at": now_iso,
                    "updated_at": now_iso,
                    "record_status": "active",
                    "evidence_id": evidence_id,
                    "document_id": document_id,
                    "document_type": document_type,
                    "document_title": document_title,
                    "document_temporal_scope": document_temporal_scope,
                    "document_origin_session": document_origin_session,
                    "document_last_updated_session": document_last_updated_session,
                    "source_class": source_class,
                    "canon_layer": canon_layer,
                    "campaign_id": campaign_id,
                    "text": node.text.strip(),
                    "section_path": child_path,
                    "paragraph_index": max(0, node.line_start),
                    "source_order_index": counter[0],
                    "line_span": line_span,
                    "char_span": None,
                    "source_anchors": source_anchors,
                    "inferred_session": (
                        document_session
                        if document_session is not None
                        else _infer_session_from_section_path(child_path)
                    ),
                    "document_session": document_session,
                    "speaker_or_subject": None,
                    "notes": None,
                }
            )
            counter[0] += 1
        return

    if node.node_type != "paragraph" or not node.text.strip():
        return

    now_iso = _now_utc_iso()
    section_path = path[:] if path else ["Document"]
    evidence_id = _compute_evidence_id(
        document_id=document_id,
        section_path=section_path,
        text=node.text.strip(),
    )
    line_span, source_anchors = _line_span_and_anchors(
        body_line_start_0=node.line_start,
        body_line_end_exclusive_0=node.line_end,
        body_line_offset=body_line_offset,
        full_file_lines=full_file_lines,
        corpus_source_path=corpus_source_path,
        commit_sha=commit_sha,
    )
    units.append(
        {
            "schema_version": "0.1.0",
            "created_at": now_iso,
            "updated_at": now_iso,
            "record_status": "active",
            "evidence_id": evidence_id,
            "document_id": document_id,
            "document_type": document_type,
            "document_title": document_title,
            "document_temporal_scope": document_temporal_scope,
            "document_origin_session": document_origin_session,
            "document_last_updated_session": document_last_updated_session,
            "source_class": source_class,
            "canon_layer": canon_layer,
            "campaign_id": campaign_id,
            "text": node.text.strip(),
            "section_path": section_path,
            "paragraph_index": max(0, node.line_start),
            "source_order_index": counter[0],
            "line_span": line_span,
            "char_span": None,
            "source_anchors": source_anchors,
            "inferred_session": (
                document_session
                if document_session is not None
                else _infer_session_from_section_path(section_path)
            ),
            "document_session": document_session,
            "speaker_or_subject": None,
            "notes": None,
        }
    )
    counter[0] += 1


def _merge_small_units(
    units: list[dict[str, Any]],
    min_chars: int,
    *,
    full_file_lines: list[str],
    corpus_source_path: str,
    commit_sha: str,
) -> list[dict[str, Any]]:
    if not units:
        return []
    merged: list[dict[str, Any]] = []
    idx = 0
    while idx < len(units):
        unit = dict(units[idx])
        if len(unit["text"].strip()) < min_chars and idx + 1 < len(units):
            nxt = dict(units[idx + 1])
            nxt["text"] = f"{unit['text'].rstrip()}\n\n{nxt['text'].lstrip()}".strip()
            nxt["section_path"] = unit["section_path"]
            nxt["paragraph_index"] = min(
                int(unit.get("paragraph_index", 0)),
                int(nxt.get("paragraph_index", 0)),
            )
            span_u = unit.get("line_span")
            span_n = nxt.get("line_span")
            if isinstance(span_u, dict) and isinstance(span_n, dict):
                merged_start = min(int(span_u["start"]), int(span_n["start"]))
                merged_end = max(int(span_u["end"]), int(span_n["end"]))
                line_span, anchor = build_recap_extracted_anchor(
                    corpus_source_path=corpus_source_path,
                    full_file_lines=full_file_lines,
                    line_start_1=merged_start,
                    line_end_1=merged_end,
                    commit_sha=commit_sha,
                )
                nxt["line_span"] = line_span
                nxt["source_anchors"] = [anchor.to_json_dict()]
            merged.append(nxt)
            idx += 2
            continue
        merged.append(unit)
        idx += 1

    # Recompute ids and order after merge.
    for order, unit in enumerate(merged):
        unit["source_order_index"] = order
        unit["evidence_id"] = _compute_evidence_id(
            document_id=str(unit["document_id"]),
            section_path=list(unit["section_path"]),
            text=str(unit["text"]),
        )
    return merged


def _load_markdown(source_path: Path) -> str:
    if source_path.suffix.lower() == ".md":
        return markdown_passthrough(source_path)
    return docx_to_markdown(source_path)


def _coalesce_metadata(
    frontmatter: DocumentMetadata | None,
    *,
    fallback_document_id: str | None,
    fallback_document_title: str | None,
    fallback_canon_layer: str | None,
    fallback_campaign_id: str | None,
    fallback_source_class: str | None,
) -> tuple[
    str,
    str,
    str,
    str | None,
    str,
    str | None,
    int | None,
    int | None,
    int | None,
]:
    """Resolve metadata from frontmatter, else CLI fallback."""
    if frontmatter is not None:
        document_title = frontmatter.title
        document_id = (
            fallback_document_id
            if fallback_document_id is not None and fallback_document_id.strip()
            else f"doc_{_sanitize(frontmatter.title)}"
        )
        return (
            document_id,
            document_title,
            frontmatter.canon_layer,
            frontmatter.campaign_id,
            frontmatter.source_class,
            frontmatter.temporal_scope,
            frontmatter.session,
            frontmatter.origin_session,
            frontmatter.last_updated_session,
        )

    missing = []
    if not fallback_document_id:
        missing.append("document_id")
    if not fallback_document_title:
        missing.append("document_title")
    if not fallback_canon_layer:
        missing.append("canon_layer")
    if not fallback_source_class:
        missing.append("source_class")
    if missing:
        missing_csv = ", ".join(missing)
        raise ValueError(
            f"Missing metadata and no frontmatter available: {missing_csv}. "
            "Provide metadata args or add document frontmatter."
        )
    fallback_layer = str(fallback_canon_layer)
    fallback_scope = "evergreen" if fallback_layer == "world" else "campaign_stateful"
    return (
        str(fallback_document_id),
        str(fallback_document_title),
        fallback_layer,
        fallback_campaign_id,
        str(fallback_source_class),
        fallback_scope,
        None,
        None,
        None,
    )


def _sanitize(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", raw.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "document"


def chunk_document(
    docx_path: Path,
    document_id: str | None = None,
    document_title: str | None = None,
    canon_layer: str | None = None,
    campaign_id: str | None = None,
    source_class: str | None = None,
    document_type: str = "world_reference",
    min_chars: int = 50,
    corpus_source_path: str | None = None,
    commit_sha: str | None = None,
) -> list[dict[str, Any]]:
    """Create evidence units from a source document using heading-based chunking.

    Each evidence unit carries ``line_span`` (1-based inclusive file line numbers) and
    ``source_anchors`` (``SourceAnchor`` JSON dicts) for recap_extracted ingestion.
    ``corpus_source_path`` should be POSIX path relative to the corpus root when known;
    otherwise it defaults to ``docx_path.name``.
    """
    markdown = _load_markdown(Path(docx_path))
    metadata, body = parse_document_frontmatter(markdown)
    (
        resolved_document_id,
        resolved_document_title,
        resolved_canon_layer,
        resolved_campaign_id,
        resolved_source_class,
        resolved_document_temporal_scope,
        resolved_document_session,
        resolved_document_origin_session,
        resolved_document_last_updated_session,
    ) = _coalesce_metadata(
        metadata,
        fallback_document_id=document_id,
        fallback_document_title=document_title,
        fallback_canon_layer=canon_layer,
        fallback_campaign_id=campaign_id,
        fallback_source_class=source_class,
    )
    full_file_lines = markdown.splitlines()
    if metadata is not None:
        body_line_offset = body_first_line_0based_in_file(markdown, body)
        lines = body.splitlines()
        document_type = f"{metadata.document_class}_document"
    else:
        body_line_offset = 0
        lines = full_file_lines

    resolved_commit = (
        commit_sha.strip()
        if isinstance(commit_sha, str) and commit_sha.strip()
        else resolve_git_commit_sha(cwd=docx_path.parent)
    )
    anchor_path = (
        corpus_source_path.strip()
        if isinstance(corpus_source_path, str) and corpus_source_path.strip()
        else docx_path.name
    )

    blocks = _segment_blocks(lines)
    root = _build_heading_tree(blocks)

    units: list[dict[str, Any]] = []
    _walk_tree(
        node=root,
        path=[],
        units=units,
        counter=[0],
        document_id=resolved_document_id,
        document_type=document_type,
        document_title=resolved_document_title,
        source_class=resolved_source_class,
        canon_layer=resolved_canon_layer,
        campaign_id=resolved_campaign_id,
        document_temporal_scope=resolved_document_temporal_scope,
        document_session=resolved_document_session,
        document_origin_session=resolved_document_origin_session,
        document_last_updated_session=resolved_document_last_updated_session,
        full_file_lines=full_file_lines,
        body_line_offset=body_line_offset,
        corpus_source_path=anchor_path,
        commit_sha=resolved_commit,
    )
    if min_chars < 1:
        raise ValueError("min_chars must be >= 1")
    units = _merge_small_units(
        units,
        min_chars=min_chars,
        full_file_lines=full_file_lines,
        corpus_source_path=anchor_path,
        commit_sha=resolved_commit,
    )
    validate_many(units, "evidence_unit.schema.json")
    return units
