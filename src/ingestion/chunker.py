from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import blake3

from src.contracts.schema_validation import validate_many
from src.ingestion.docx_converter import docx_to_markdown, markdown_passthrough


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
            )
        return

    if node.node_type == "heading":
        child_path = path + [node.text]
        if node.children:
            # Heading absorption: prefix heading text into the first child.
            first = node.children[0]
            if first.node_type == "paragraph" and first.text:
                first.text = f"{node.text} -- {first.text}"
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
                )
        else:
            now_iso = _now_utc_iso()
            evidence_id = _compute_evidence_id(
                document_id=document_id,
                section_path=child_path,
                text=node.text.strip(),
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
                    "source_class": source_class,
                    "canon_layer": canon_layer,
                    "campaign_id": campaign_id,
                    "text": node.text.strip(),
                    "section_path": child_path,
                    "paragraph_index": max(0, node.line_start),
                    "source_order_index": counter[0],
                    "line_span": None,
                    "char_span": None,
                    "inferred_session": _infer_session_from_section_path(child_path),
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
            "source_class": source_class,
            "canon_layer": canon_layer,
            "campaign_id": campaign_id,
            "text": node.text.strip(),
            "section_path": section_path,
            "paragraph_index": max(0, node.line_start),
            "source_order_index": counter[0],
            "line_span": None,
            "char_span": None,
            "inferred_session": _infer_session_from_section_path(section_path),
            "speaker_or_subject": None,
            "notes": None,
        }
    )
    counter[0] += 1


def _merge_small_units(units: list[dict[str, Any]], min_chars: int = 50) -> list[dict[str, Any]]:
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


def chunk_document(
    docx_path: Path,
    document_id: str,
    document_title: str,
    canon_layer: str,
    campaign_id: str | None,
    source_class: str,
    document_type: str = "world_reference",
) -> list[dict[str, Any]]:
    """Create evidence units from a source document using heading-based chunking."""
    markdown = _load_markdown(Path(docx_path))
    lines = markdown.splitlines()
    blocks = _segment_blocks(lines)
    root = _build_heading_tree(blocks)

    units: list[dict[str, Any]] = []
    _walk_tree(
        node=root,
        path=[],
        units=units,
        counter=[0],
        document_id=document_id,
        document_type=document_type,
        document_title=document_title,
        source_class=source_class,
        canon_layer=canon_layer,
        campaign_id=campaign_id,
    )
    units = _merge_small_units(units, min_chars=50)
    validate_many(units, "evidence_unit.schema.json")
    return units
