"""Canvas callout block proposals for Hermes (propose only — no durable write)."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any, Literal

CANVAS_BLOCK_PROPOSAL_SCHEMA = "dmb_canvas_block_proposal_v1"
CANVAS_BLOCK_PROPOSAL_ERROR_SCHEMA = "dmb_canvas_block_proposal_error_v1"
PROPOSE_CANVAS_BLOCK_TOOL_NAME = "propose_canvas_block"

CalloutKind = Literal["read-aloud", "gm-note", "rules", "warning"]
CanvasBlockOp = Literal["insert_callout", "replace_callout"]

CALLOUT_KINDS: frozenset[str] = frozenset(
    {"read-aloud", "gm-note", "rules", "warning"}
)
CANVAS_BLOCK_OPS: frozenset[str] = frozenset({"insert_callout", "replace_callout"})

_KIND_TO_MARKER: dict[str, str] = {
    "read-aloud": "READ-ALOUD",
    "gm-note": "GM-NOTE",
    "rules": "RULES",
    "warning": "WARNING",
}

MAX_BODY_CHARS = 8000
MAX_LOCATOR_CHARS = 500
MAX_PROVENANCE_REFS = 16


def callout_kind_to_markdown_marker(kind: str) -> str:
    return _KIND_TO_MARKER.get(kind, "WARNING")


def build_preview_markdown(*, kind: str, body: str) -> str:
    marker = callout_kind_to_markdown_marker(kind)
    lines = [f"> [!{marker}]"]
    for line in body.splitlines() or [""]:
        lines.append(f"> {line}" if line else ">")
    return "\n".join(lines)


def normalize_callout_kind(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "readaloud": "read-aloud",
        "read": "read-aloud",
        "gmnote": "gm-note",
        "gm": "gm-note",
        "dm": "gm-note",
        "dm-note": "gm-note",
        "rule": "rules",
        "rules-note": "rules",
        "warn": "warning",
        "danger": "warning",
        "caution": "warning",
    }
    kind = aliases.get(key, key)
    return kind if kind in CALLOUT_KINDS else None


def _error(*, code: str, message: str, diagnostics: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": CANVAS_BLOCK_PROPOSAL_ERROR_SCHEMA,
        "code": code,
        "message": message,
        "diagnostics": list(diagnostics or []),
    }


def _normalize_locator(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, Mapping):
        return None
    after = raw.get("afterHeading", raw.get("after_heading"))
    old = raw.get("oldText", raw.get("old_text"))
    out: dict[str, str] = {}
    if isinstance(after, str) and after.strip():
        text = after.strip()
        if len(text) > MAX_LOCATOR_CHARS:
            return None
        out["afterHeading"] = text
    if isinstance(old, str) and old.strip():
        text = old.strip()
        if len(text) > MAX_LOCATOR_CHARS:
            return None
        out["oldText"] = text
    return out or None


def execute_propose_canvas_block(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Build a typed canvas block proposal. Never writes files."""
    document_id = str(
        arguments.get("documentId") or arguments.get("document_id") or ""
    ).strip()
    surface_id = str(
        arguments.get("surfaceId") or arguments.get("surface_id") or ""
    ).strip()
    expected_sha = str(
        arguments.get("expectedContentSha256")
        or arguments.get("expected_content_sha256")
        or ""
    ).strip()

    if not document_id:
        return _error(
            code="canvas_work_object_missing",
            message="No Canvas work object on this surface; open a Plan document first.",
            diagnostics=["missing_document_id"],
        )

    op_raw = str(arguments.get("op") or "").strip()
    if op_raw not in CANVAS_BLOCK_OPS:
        return _error(
            code="invalid_op",
            message="op must be insert_callout or replace_callout.",
            diagnostics=["invalid_op"],
        )

    kind = normalize_callout_kind(arguments.get("kind"))
    if kind is None:
        return _error(
            code="invalid_kind",
            message="kind must be read-aloud, gm-note, rules, or warning.",
            diagnostics=["invalid_kind"],
        )

    body = str(arguments.get("body") or "").strip()
    if not body:
        return _error(
            code="empty_body",
            message="body is required.",
            diagnostics=["empty_body"],
        )
    if len(body) > MAX_BODY_CHARS:
        return _error(
            code="body_too_long",
            message=f"body exceeds {MAX_BODY_CHARS} characters.",
            diagnostics=["body_too_long"],
        )

    # Strip accidental callout wrappers — kind is authoritative.
    body = re.sub(r"^>\s*\[![^\]]+\]\s*\n?", "", body, count=1).strip()
    body = "\n".join(
        re.sub(r"^>\s?", "", line) for line in body.splitlines()
    ).strip()
    if not body:
        return _error(
            code="empty_body",
            message="body is empty after stripping callout markers.",
            diagnostics=["empty_body_after_strip"],
        )

    locator = _normalize_locator(arguments.get("locator"))
    if locator is None:
        return _error(
            code="invalid_locator",
            message="locator must include afterHeading and/or oldText.",
            diagnostics=["invalid_locator"],
        )
    if op_raw == "replace_callout" and "oldText" not in locator:
        return _error(
            code="invalid_locator",
            message="replace_callout requires locator.oldText.",
            diagnostics=["replace_requires_old_text"],
        )
    if op_raw == "insert_callout" and "afterHeading" not in locator and "oldText" not in locator:
        return _error(
            code="invalid_locator",
            message="insert_callout requires locator.afterHeading (preferred) or oldText.",
            diagnostics=["insert_requires_anchor"],
        )

    provenance_raw = arguments.get("provenanceRefs") or arguments.get("provenance_refs") or []
    provenance_refs: list[str] = []
    if isinstance(provenance_raw, list):
        for item in provenance_raw[:MAX_PROVENANCE_REFS]:
            if isinstance(item, str) and item.strip():
                provenance_refs.append(item.strip()[:200])

    proposal = {
        "schema": CANVAS_BLOCK_PROPOSAL_SCHEMA,
        "documentId": document_id,
        "surfaceId": surface_id or "plan",
        "op": op_raw,
        "kind": kind,
        "body": body,
        "locator": locator,
        "previewMarkdown": build_preview_markdown(kind=kind, body=body),
        "expectedContentSha256": expected_sha or None,
        "provenanceRefs": provenance_refs,
    }
    return proposal


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
