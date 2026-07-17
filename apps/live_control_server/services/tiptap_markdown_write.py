from __future__ import annotations

import difflib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import blake3
from pydantic import BaseModel, Field

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    get_workspace_document,
    mark_workspace_document_committed,
)

_ALLOWED_EVAL_TIPTAP_MARKDOWN_RE = re.compile(
    r"^evals/c2_live_prep/mireward-prep/content/tiptap/[a-z0-9][a-z0-9_-]*\.md$"
)
_ALLOWED_PLAN_SESSION_PREP_RE = re.compile(
    r"^corpus/eldyrwild-markdown/Longmont Campaign/Campaign \d+/Session Prep/Session \d+ Prep\.md$"
)


def _is_allowed_tiptap_target_relpath(value: str) -> bool:
    return bool(
        _ALLOWED_EVAL_TIPTAP_MARKDOWN_RE.fullmatch(value)
        or _ALLOWED_PLAN_SESSION_PREP_RE.fullmatch(value)
    )


def _is_corpus_tiptap_target_relpath(value: str) -> bool:
    return value.startswith("corpus/eldyrwild-markdown/")


class TiptapMarkdownWriteError(ValueError):
    status_code = 422


class TiptapMarkdownWriteConflictError(TiptapMarkdownWriteError):
    status_code = 409


class TiptapMarkdownWritePrepareRequest(BaseModel):
    document_id: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    expected_revision: int | None = None


class TiptapMarkdownWritePrepareResponse(BaseModel):
    schema_version: Literal["dmb_tiptap_markdown_write_prepare_v1"] = (
        "dmb_tiptap_markdown_write_prepare_v1"
    )
    document_id: str
    title: str
    target_relpath: str
    target_display_path: str
    registry_revision: int
    file_exists: bool
    writer_ok: bool
    writer_phase: str | None = None
    writer_confirm_token: str | None = None
    writer_diff: str | None = None
    existing_size_bytes: int | None = None
    new_size_bytes: int | None = None
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class TiptapMarkdownWriteCommitRequest(BaseModel):
    document_id: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    writer_confirm_token: str = Field(min_length=1)
    expected_revision: int | None = None


class TiptapMarkdownWriteCommitResponse(BaseModel):
    schema_version: Literal["dmb_tiptap_markdown_write_commit_v1"] = (
        "dmb_tiptap_markdown_write_commit_v1"
    )
    document_id: str
    title: str
    target_relpath: str
    target_display_path: str
    registry_revision: int
    writer_ok: bool
    writer_phase: str | None = None
    bytes_written: int | None = None
    file_fingerprint: str | None = None
    backup_relpath: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


def normalize_tiptap_target_relpath(value: str) -> str:
    if value != value.strip() or "\\" in value or Path(value).is_absolute():
        raise TiptapMarkdownWriteError(
            "target_relpath must be a normalized repo-relative path"
        )
    if not _is_allowed_tiptap_target_relpath(value):
        raise TiptapMarkdownWriteError(
            "target_relpath must match an allowed Tiptap Markdown write path"
        )
    return value


def resolve_tiptap_markdown_target(root: Path, relpath: str) -> Path:
    normalized = normalize_tiptap_target_relpath(relpath)
    resolved_root = root.resolve()
    target = (resolved_root / normalized).resolve()
    if not target.is_relative_to(resolved_root):
        raise TiptapMarkdownWriteError("target_relpath escapes the repository root")
    return target


def _final_content(markdown: str) -> str:
    if not markdown.strip():
        raise TiptapMarkdownWriteError("markdown must not be empty")
    return markdown.rstrip("\n") + "\n"


def _file_state_token(target: Path) -> str:
    if not target.exists():
        return "absent"
    stat = target.stat()
    return f"present:{stat.st_mtime_ns}:{stat.st_size}"


def _confirm_token(
    document_id: str,
    registry_revision: int,
    relpath: str,
    content: str,
    file_state: str,
) -> str:
    payload = (
        f"{document_id}\0{registry_revision}\0{relpath}\0{content}\0{file_state}"
    ).encode()
    return blake3.blake3(payload).hexdigest()


def _map_registry_error(exc: WorkspaceDocumentRegistryError) -> TiptapMarkdownWriteError:
    if exc.status_code == 409:
        return TiptapMarkdownWriteConflictError(str(exc))
    error = TiptapMarkdownWriteError(str(exc))
    error.status_code = exc.status_code
    return error


def _resolve_writable_document(
    root: Path,
    document_id: str,
    *,
    expected_revision: int | None,
) -> WorkspaceDocumentRecord:
    try:
        record = get_workspace_document(root, document_id)
    except WorkspaceDocumentRegistryError as exc:
        raise _map_registry_error(exc) from exc

    if expected_revision is not None and record.revision != expected_revision:
        raise TiptapMarkdownWriteConflictError(
            f"revision mismatch: expected {expected_revision}, current {record.revision}"
        )

    if record.status == "discarded":
        raise TiptapMarkdownWriteConflictError(
            f"workspace document is discarded: {record.document_id}"
        )

    if not record.target_relpath or not record.target_relpath.strip():
        raise TiptapMarkdownWriteError(
            "workspace document has no target_relpath; cannot write Markdown"
        )

    return record


def prepare_tiptap_markdown_write(
    *, root: Path, request: TiptapMarkdownWritePrepareRequest
) -> TiptapMarkdownWritePrepareResponse:
    record = _resolve_writable_document(
        root,
        request.document_id,
        expected_revision=request.expected_revision,
    )
    relpath = normalize_tiptap_target_relpath(record.target_relpath)
    target = resolve_tiptap_markdown_target(root, relpath)
    content = _final_content(request.markdown)
    exists = target.is_file()
    existing = target.read_text(encoding="utf-8") if exists else ""
    diff = "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=relpath if exists else "/dev/null",
            tofile=relpath,
        )
    )
    return TiptapMarkdownWritePrepareResponse(
        document_id=record.document_id,
        title=record.title,
        target_relpath=relpath,
        target_display_path=relpath,
        registry_revision=record.revision,
        file_exists=exists,
        writer_ok=True,
        writer_phase="prepare",
        writer_confirm_token=_confirm_token(
            record.document_id,
            record.revision,
            relpath,
            content,
            _file_state_token(target),
        ),
        writer_diff=diff,
        existing_size_bytes=len(existing.encode()) if exists else None,
        new_size_bytes=len(content.encode()),
        warnings=["Existing file will be replaced after explicit commit."]
        if exists
        else [],
        diagnostics=_prepare_diagnostics(relpath),
    )


def _prepare_diagnostics(relpath: str) -> list[str]:
    diagnostics = [
        "dry-run only; no file was written",
        "review the Markdown diff before commit",
        "local Tiptap JSON remains browser-local",
    ]
    if not _is_corpus_tiptap_target_relpath(relpath):
        diagnostics.append("corpus was not mutated")
    return diagnostics


def commit_tiptap_markdown_write(
    *, root: Path, request: TiptapMarkdownWriteCommitRequest
) -> TiptapMarkdownWriteCommitResponse:
    record = _resolve_writable_document(
        root,
        request.document_id,
        expected_revision=request.expected_revision,
    )
    relpath = normalize_tiptap_target_relpath(record.target_relpath)
    target = resolve_tiptap_markdown_target(root, relpath)
    content = _final_content(request.markdown)
    expected = _confirm_token(
        record.document_id,
        record.revision,
        relpath,
        content,
        _file_state_token(target),
    )
    if request.writer_confirm_token != expected:
        raise TiptapMarkdownWriteConflictError(
            "stale writer confirm token; prepare file write again"
        )

    backup_relpath: str | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup = target.parent / ".backups" / f"{timestamp}__{target.name}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(target.read_bytes())
            backup_relpath = backup.relative_to(root.resolve()).as_posix()
        target.write_text(content, encoding="utf-8", newline="")
    except OSError as exc:
        error = TiptapMarkdownWriteError(f"failed to write Tiptap Markdown file: {exc}")
        error.status_code = 500
        raise error from exc

    try:
        committed_record = mark_workspace_document_committed(
            root,
            record.document_id,
            expected_revision=record.revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        raise _map_registry_error(exc) from exc

    return TiptapMarkdownWriteCommitResponse(
        document_id=committed_record.document_id,
        title=committed_record.title,
        target_relpath=relpath,
        target_display_path=relpath,
        registry_revision=committed_record.revision,
        writer_ok=True,
        writer_phase="commit",
        bytes_written=len(content.encode()),
        file_fingerprint=blake3.blake3(content.encode()).hexdigest(),
        backup_relpath=backup_relpath,
        diagnostics=_commit_diagnostics(relpath),
    )


def _commit_diagnostics(relpath: str) -> list[str]:
    diagnostics = [
        "reviewed Markdown file written",
        "local Tiptap JSON remains browser-local",
        "backend wrote Markdown only; no graph memory or ingest mutation occurred",
    ]
    if not _is_corpus_tiptap_target_relpath(relpath):
        diagnostics.append("corpus was not mutated")
    return diagnostics
