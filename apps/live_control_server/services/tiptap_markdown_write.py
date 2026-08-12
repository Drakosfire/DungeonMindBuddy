from __future__ import annotations

import contextlib
import difflib
import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import blake3
from pydantic import BaseModel, Field

from apps.live_control_server.services.registry_file_lock import (
    workspace_document_mutation_lock,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    get_workspace_document,
    mark_workspace_document_committed_unlocked,
)

_ALLOWED_EVAL_TIPTAP_MARKDOWN_RE = re.compile(
    r"^evals/c2_live_prep/mireward-prep/content/tiptap/[a-z0-9][a-z0-9_-]*\.md$"
)
_ALLOWED_PLAN_SESSION_PREP_RE = re.compile(
    r"^corpus/eldyrwild-markdown/Longmont Campaign/Campaign \d+/Session Prep/Session \d+ Prep\.md$"
)
_ALLOWED_WORLDBUILDING_WORKSPACE_RE = re.compile(
    r"^out/workspace/worldbuilding/"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\.md$"
)
_ALLOWED_WORLDBUILDING_CORPUS_SOURCE_RE = re.compile(
    r"^corpus/"
    r"(?P<world_id>[a-z][a-z0-9_-]{0,62})-markdown/"
    r"_dungeonbuddy/sources/"
    r"(?P<document_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/"
    r"source\.md$"
)
_ALLOWED_PLAN_WORKSPACE_RE = re.compile(
    r"^out/workspace/plan/"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\.md$"
)
_LOSSY_MARKDOWN_LINE_RE = re.compile(r"^\s*(?:\||<|!\[|---\s*$)")


def _is_allowed_tiptap_target_relpath(value: str) -> bool:
    return bool(
        _ALLOWED_EVAL_TIPTAP_MARKDOWN_RE.fullmatch(value)
        or _ALLOWED_PLAN_SESSION_PREP_RE.fullmatch(value)
        or _ALLOWED_WORLDBUILDING_WORKSPACE_RE.fullmatch(value)
        or _ALLOWED_WORLDBUILDING_CORPUS_SOURCE_RE.fullmatch(value)
        or _ALLOWED_PLAN_WORKSPACE_RE.fullmatch(value)
    )


def _is_corpus_tiptap_target_relpath(value: str) -> bool:
    return value.startswith("corpus/")


WriteMode = Literal["authoring", "source_import"]


def _normalize_write_mode(value: WriteMode | None) -> WriteMode:
    return value or "authoring"


def markdown_lossy_diagnostics(markdown: str) -> list[str]:
    """Return diagnostics for unsupported Markdown constructs.

    Blocking vs advisory is kind-scoped in prepare/commit (worldbuilding_source only).
    """
    diagnostics: list[str] = []
    for line_number, line in enumerate(markdown.replace("\r\n", "\n").split("\n"), start=1):
        if not line.strip():
            continue
        if _LOSSY_MARKDOWN_LINE_RE.match(line):
            diagnostics.append(
                f"line {line_number}: unsupported Markdown block would be lossy on commit"
            )
    return diagnostics


class TiptapMarkdownWriteError(ValueError):
    status_code = 422


class TiptapMarkdownWriteConflictError(TiptapMarkdownWriteError):
    status_code = 409


def require_legal_plan_target_relpath(document_id: str, relpath: str) -> str:
    """Authorize a Plan path against identity-bound workspace or Session Prep policy.

    Legal targets:
    - ``out/workspace/plan/<document_id>.md`` (own UUID workspace draft)
    - allowlisted canonical ``Session N Prep.md`` corpus path

    Foreign workspace UUID paths and arbitrary paths are rejected. Used by both
    the writer and registry create so an illegal explicit create path cannot
    persist a permanently unopenable record.
    """
    if relpath != relpath.strip():
        raise TiptapMarkdownWriteError(
            "target_relpath must be a normalized repo-relative path"
        )
    expected_workspace = f"out/workspace/plan/{document_id}.md"
    if relpath == expected_workspace:
        return normalize_tiptap_target_relpath(relpath)
    if _ALLOWED_PLAN_SESSION_PREP_RE.fullmatch(relpath):
        return normalize_tiptap_target_relpath(relpath)
    raise TiptapMarkdownWriteError(
        "plan target_relpath must match the document's workspace path "
        "or an allowed Session Prep path"
    )


def authorize_target_for_record(record: WorkspaceDocumentRecord) -> str:
    """Authorize and normalize the registry target for this document kind.

    Uses the raw registry value. Surrounding whitespace is rejected rather than
    silently normalized, matching ``normalize_tiptap_target_relpath``.
    """
    if record.target_relpath is None or record.target_relpath == "":
        raise TiptapMarkdownWriteError(
            "workspace document has no target_relpath; cannot write Markdown"
        )
    relpath = record.target_relpath
    if relpath != relpath.strip():
        raise TiptapMarkdownWriteError(
            "target_relpath must be a normalized repo-relative path"
        )

    if record.kind == "worldbuilding_source":
        if record.world_id:
            expected_target = (
                f"corpus/{record.world_id}-markdown"
                f"/_dungeonbuddy/sources/{record.document_id}/source.md"
            )
        else:
            expected_target = f"out/workspace/worldbuilding/{record.document_id}.md"
        if relpath != expected_target:
            raise TiptapMarkdownWriteError(
                "worldbuilding_source target_relpath does not match registry policy"
            )
        return normalize_tiptap_target_relpath(relpath)

    if record.kind == "plan":
        return require_legal_plan_target_relpath(record.document_id, relpath)

    if record.kind == "runbook":
        if not _ALLOWED_EVAL_TIPTAP_MARKDOWN_RE.fullmatch(relpath):
            raise TiptapMarkdownWriteError(
                "runbook target_relpath must match an allowed Tiptap runbook path"
            )
        return normalize_tiptap_target_relpath(relpath)

    raise TiptapMarkdownWriteError(f"unsupported document kind: {record.kind}")


def _commit_blocking_lossy(kind: str, markdown: str) -> list[str]:
    if kind != "worldbuilding_source":
        return []
    return markdown_lossy_diagnostics(markdown)


class TiptapMarkdownWritePrepareRequest(BaseModel):
    document_id: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    expected_revision: int | None = None
    write_mode: WriteMode | None = None


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
    write_mode: WriteMode | None = None


class TiptapMarkdownWriteCommitResponse(BaseModel):
    """Authoritative write receipt constructed under the document mutation lock.

    Clients must advance local base revision/fingerprint from this receipt. A later
    snapshot GET is verification only — never the operation that decides whether the
    durable commit succeeded.
    """

    schema_version: Literal["dmb_tiptap_markdown_write_commit_v1"] = (
        "dmb_tiptap_markdown_write_commit_v1"
    )
    document_id: str
    title: str
    target_relpath: str
    target_display_path: str
    registry_revision: int
    committed_revision: int
    committed_record: WorkspaceDocumentRecord
    normalized_content_sha256: str
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
    write_mode: WriteMode,
) -> str:
    payload = (
        f"{document_id}\0{registry_revision}\0{relpath}\0{content}\0{file_state}\0{write_mode}"
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

    if record.target_relpath is None or record.target_relpath == "":
        raise TiptapMarkdownWriteError(
            "workspace document has no target_relpath; cannot write Markdown"
        )

    return record


def _prepare_warnings(
    *,
    exists: bool,
    writer_ok: bool,
    blocking_lossy: list[str],
    advisory_lossy: list[str],
    write_mode: WriteMode,
) -> list[str]:
    if write_mode == "source_import" and blocking_lossy:
        warnings = [
            "Lossy Markdown diagnostics are informational for source_import; commit is allowed."
        ]
    elif exists and writer_ok:
        warnings = ["Existing file will be replaced after explicit commit."]
    elif blocking_lossy:
        warnings = ["Commit blocked: unsupported Markdown would be lossy."]
    else:
        warnings = []
    if advisory_lossy:
        warnings.append(
            "Unsupported Markdown constructs are advisory for this document kind; "
            "commit is allowed."
        )
    return warnings


def _assert_source_import_eligible(
    record: WorkspaceDocumentRecord,
    target: Path,
) -> None:
    if record.kind != "worldbuilding_source":
        raise TiptapMarkdownWriteError(
            "source_import is only valid for worldbuilding_source documents"
        )
    if record.status != "active":
        raise TiptapMarkdownWriteConflictError(
            f"workspace document is not active: {record.document_id}"
        )
    if record.content_status != "draft":
        raise TiptapMarkdownWriteConflictError(
            "source_import is only valid for uninitialized draft sources"
        )
    if target.is_file():
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError as exc:
            raise TiptapMarkdownWriteError(
                f"failed to read existing source target: {exc}"
            ) from exc
        if existing.strip():
            raise TiptapMarkdownWriteConflictError(
                "source_import is only valid for empty/uninitialized sources"
            )


def prepare_tiptap_markdown_write(
    *, root: Path, request: TiptapMarkdownWritePrepareRequest
) -> TiptapMarkdownWritePrepareResponse:
    write_mode = _normalize_write_mode(request.write_mode)
    record = _resolve_writable_document(
        root,
        request.document_id,
        expected_revision=request.expected_revision,
    )
    relpath = authorize_target_for_record(record)
    target = resolve_tiptap_markdown_target(root, relpath)
    if write_mode == "source_import":
        _assert_source_import_eligible(record, target)
    content = _final_content(request.markdown)
    lossy = markdown_lossy_diagnostics(request.markdown)
    blocking_lossy = (
        [] if write_mode == "source_import" else _commit_blocking_lossy(record.kind, request.markdown)
    )
    advisory_lossy = lossy if not blocking_lossy and lossy else []
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
    writer_ok = not blocking_lossy
    return TiptapMarkdownWritePrepareResponse(
        document_id=record.document_id,
        title=record.title,
        target_relpath=relpath,
        target_display_path=relpath,
        registry_revision=record.revision,
        file_exists=exists,
        writer_ok=writer_ok,
        writer_phase="prepare",
        writer_confirm_token=None
        if not writer_ok
        else _confirm_token(
            record.document_id,
            record.revision,
            relpath,
            content,
            _file_state_token(target),
            write_mode,
        ),
        writer_diff=diff,
        existing_size_bytes=len(existing.encode()) if exists else None,
        new_size_bytes=len(content.encode()),
        warnings=_prepare_warnings(
            exists=exists,
            writer_ok=writer_ok,
            blocking_lossy=blocking_lossy,
            advisory_lossy=advisory_lossy,
            write_mode=write_mode,
        ),
        diagnostics=[*_prepare_diagnostics(relpath), *lossy],
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


def _restore_prior_file_state(
    target: Path,
    *,
    prior_existed: bool,
    prior_bytes: bytes | None,
) -> None:
    if prior_existed:
        assert prior_bytes is not None
        target.write_bytes(prior_bytes)
        return
    if target.exists():
        target.unlink()


def _atomic_write_text(target: Path, content: str) -> None:
    """Write Markdown via a sibling temp file and atomic replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8", newline="")
        temp_path.replace(target)
    except OSError:
        with contextlib.suppress(OSError):
            temp_path.unlink(missing_ok=True)
        raise


def _raise_write_failure(message: str, *, cause: BaseException) -> None:
    error = TiptapMarkdownWriteError(message)
    error.status_code = 500
    raise error from cause


def _rollback_after_failure(
    target: Path,
    *,
    prior_existed: bool,
    prior_bytes: bytes | None,
    backup_path: Path | None,
    primary_exc: BaseException,
    primary_label: str,
) -> None:
    """Restore the authored target and discard a newly created backup on failure."""
    failures: list[str] = []
    cause: BaseException = primary_exc
    try:
        _restore_prior_file_state(
            target,
            prior_existed=prior_existed,
            prior_bytes=prior_bytes,
        )
    except OSError as restore_exc:
        failures.append(f"file rollback also failed: {restore_exc}")
        cause = restore_exc
    if backup_path is not None:
        try:
            backup_path.unlink(missing_ok=True)
        except OSError as backup_exc:
            failures.append(f"backup cleanup also failed: {backup_exc}")
            if cause is primary_exc:
                cause = backup_exc
    if failures:
        _raise_write_failure(
            f"{primary_label}: {primary_exc}; " + "; ".join(failures),
            cause=cause,
        )


def commit_tiptap_markdown_write(
    *, root: Path, request: TiptapMarkdownWriteCommitRequest
) -> TiptapMarkdownWriteCommitResponse:
    with workspace_document_mutation_lock(root, request.document_id):
        return _commit_tiptap_markdown_write_unlocked(root=root, request=request)


def _commit_tiptap_markdown_write_unlocked(
    *, root: Path, request: TiptapMarkdownWriteCommitRequest
) -> TiptapMarkdownWriteCommitResponse:
    write_mode = _normalize_write_mode(request.write_mode)
    record = _resolve_writable_document(
        root,
        request.document_id,
        expected_revision=request.expected_revision,
    )
    relpath = authorize_target_for_record(record)
    target = resolve_tiptap_markdown_target(root, relpath)
    content = _final_content(request.markdown)
    expected = _confirm_token(
        record.document_id,
        record.revision,
        relpath,
        content,
        _file_state_token(target),
        write_mode,
    )
    if request.writer_confirm_token != expected:
        raise TiptapMarkdownWriteConflictError(
            "stale writer confirm token; prepare file write again"
        )
    if write_mode == "source_import":
        _assert_source_import_eligible(record, target)
    blocking_lossy = (
        [] if write_mode == "source_import" else _commit_blocking_lossy(record.kind, request.markdown)
    )
    if blocking_lossy:
        raise TiptapMarkdownWriteError(
            "commit blocked: unsupported Markdown would be lossy; "
            + "; ".join(blocking_lossy[:3])
        )

    prior_existed = target.exists()
    prior_bytes = target.read_bytes() if prior_existed else None
    backup_path: Path | None = None
    backup_relpath: str | None = None
    try:
        if prior_existed:
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup_path = target.parent / ".backups" / f"{timestamp}__{target.name}"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_bytes(prior_bytes or b"")
            backup_relpath = backup_path.relative_to(root.resolve()).as_posix()
        _atomic_write_text(target, content)
    except OSError as exc:
        _rollback_after_failure(
            target,
            prior_existed=prior_existed,
            prior_bytes=prior_bytes,
            backup_path=backup_path,
            primary_exc=exc,
            primary_label="failed to write Tiptap Markdown file",
        )
        _raise_write_failure(f"failed to write Tiptap Markdown file: {exc}", cause=exc)

    try:
        committed_record = mark_workspace_document_committed_unlocked(
            root,
            record.document_id,
            expected_revision=record.revision,
        )
    except WorkspaceDocumentRegistryError as exc:
        _rollback_after_failure(
            target,
            prior_existed=prior_existed,
            prior_bytes=prior_bytes,
            backup_path=backup_path,
            primary_exc=exc,
            primary_label="file write succeeded but registry commit failed",
        )
        raise _map_registry_error(exc) from exc
    except (OSError, TypeError, ValueError) as exc:
        _rollback_after_failure(
            target,
            prior_existed=prior_existed,
            prior_bytes=prior_bytes,
            backup_path=backup_path,
            primary_exc=exc,
            primary_label="file write succeeded but registry commit failed",
        )
        _raise_write_failure(f"registry commit failed: {exc}", cause=exc)

    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return TiptapMarkdownWriteCommitResponse(
        document_id=committed_record.document_id,
        title=committed_record.title,
        target_relpath=relpath,
        target_display_path=relpath,
        registry_revision=committed_record.revision,
        committed_revision=committed_record.revision,
        committed_record=committed_record,
        normalized_content_sha256=content_sha256,
        writer_ok=True,
        writer_phase="commit",
        bytes_written=len(content.encode()),
        file_fingerprint=_file_state_token(target),
        backup_relpath=backup_relpath,
        diagnostics=_commit_diagnostics(relpath),
    )


def _commit_diagnostics(relpath: str) -> list[str]:
    diagnostics = [
        "reviewed Markdown file written",
        "local Tiptap JSON remains browser-local",
        "backend wrote Markdown only; no graph memory or ingest mutation occurred",
    ]
    if _is_corpus_tiptap_target_relpath(relpath):
        diagnostics.append("corpus target was written under managed world source path")
    else:
        diagnostics.append("corpus was not mutated")
    return diagnostics
