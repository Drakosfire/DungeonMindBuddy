from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Literal

import blake3
from markdown_it import MarkdownIt
from pydantic import BaseModel, Field, field_validator, model_validator

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRecordAny,
    WorkspaceDocumentRegistryError,
)

_ALLOWED_EVAL_TIPTAP_MARKDOWN_RE = re.compile(
    r"^evals/c2_live_prep/mireward-prep/content/tiptap/[a-z0-9][a-z0-9_-]*\.md$"
)
_ALLOWED_PLAN_SESSION_PREP_RE = re.compile(
    r"^corpus/eldyrwild-markdown/Longmont Campaign/Campaign \d+/Session Prep/Session \d+ Prep\.md$"
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
        or _ALLOWED_PLAN_WORKSPACE_RE.fullmatch(value)
    )


WriteMode = Literal["authoring", "source_import"]


def _normalize_write_mode(value: WriteMode | None) -> WriteMode:
    return value or "authoring"


def _editor_table_lines(markdown: str) -> set[int]:
    """Admit the flat, unaligned pipe-table subset emitted by the rich editor."""
    lines = markdown.split("\n")
    tokens = MarkdownIt("commonmark").enable("table").parse(markdown)
    admitted: set[int] = set()

    def pipes(line: str) -> int:
        count = 0
        escaped = False
        for character in line:
            if character == "|" and not escaped:
                count += 1
            escaped = not escaped if character == "\\" else False
        return count

    for index, token in enumerate(tokens):
        if token.type != "table_open" or token.level != 0 or not token.map:
            continue
        start, end = token.map
        closing = next(
            (
                i
                for i in range(index + 1, len(tokens))
                if tokens[i].type == "table_close"
            ),
            index,
        )
        table = tokens[index:closing]
        width = sum(item.type == "th_open" for item in table)
        if (
            not width
            or start + 1 >= end
            or not re.fullmatch(r"\s*\|(?:\s*-{3,}\s*\|)+\s*", lines[start + 1])
        ):
            continue
        if any(
            not line.strip().startswith("|")
            or not line.strip().endswith("|")
            or pipes(line) != width + 1
            for line in lines[start:end]
        ):
            continue
        if any(
            child.type in {"html_inline", "image"}
            for item in table
            for child in (item.children or [])
        ):
            continue
        admitted.update(range(start + 1, end + 1))
    return admitted


_MEDIA_DESTINATION = re.compile(
    r"^dmb-media:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)


def _valid_image_presentation(title: str | None) -> bool:
    return (
        not title
        or re.fullmatch(
            r"dmb-image:v1 width=(20|[2-9][0-9]|100) collapsed=(true|false)", title
        )
        is not None
    )


def has_saved_media_references(markdown: str) -> bool:
    """Inspect decoded Markdown destinations, including character references."""
    return any(
        child.type == "image" and (child.attrGet("src") or "").startswith("dmb-media:")
        for token in MarkdownIt("commonmark").parse(markdown)
        for child in token.children or []
    )


def validate_saved_media_references(
    markdown: str, owner: str = "local_operator"
) -> None:
    """APP is the image authority; a Markdown URL never proves a saved asset."""
    from application_state import media
    from application_state.errors import ApplicationStateError

    for token in MarkdownIt("commonmark").parse(markdown):
        for child in token.children or []:
            if child.type != "image":
                continue
            destination = child.attrGet("src") or ""
            if not destination.startswith("dmb-media:"):
                continue
            match = _MEDIA_DESTINATION.fullmatch(destination)
            if (
                not match
                or not _valid_image_presentation(child.attrGet("title"))
                or not child.content.strip()
                or "\n" in child.content
                or "\r" in child.content
            ):
                raise TiptapMarkdownWriteError("Invalid saved image reference")
            try:
                record = media.get_asset(match[1], owner)
                if record["state"] == "staged":
                    # Retained originals are private durable assets. Reuse APP's
                    # byte-integrity authority at both prepare and commit.
                    media.read_staged_bytes(match[1], owner)
                    continue
            except ApplicationStateError as error:
                raise TiptapMarkdownWriteError(
                    "Saved image is not available to this operator or its original failed integrity verification"
                ) from error
            if (
                record["state"] != "ready"
                or record["receipt"]["visibility"] != "public"
            ):
                raise TiptapMarkdownWriteError(
                    "The image is not ready for placement. Reopen it in Image Studio and check its status"
                )


def _editor_image_lines(markdown: str) -> set[int]:
    result: set[int] = set()
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type == "inline" and token.map and token.children:
            images = [child for child in token.children if child.type == "image"]
            if (
                images
                and not any(child.type == "html_inline" for child in token.children)
                and all(
                    _MEDIA_DESTINATION.fullmatch(child.attrGet("src") or "")
                    and child.content.strip()
                    and _valid_image_presentation(child.attrGet("title"))
                    for child in images
                )
            ):
                result.update(range(token.map[0] + 1, token.map[1] + 1))
    return result


def markdown_lossy_diagnostics(
    markdown: str, *, allow_editor_tables: bool = False
) -> list[str]:
    """Return diagnostics for unsupported Markdown constructs.

    Blocking vs advisory is kind-scoped in prepare/commit (worldbuilding_source only).
    """
    markdown = markdown.replace("\r\n", "\n")
    table_lines = _editor_table_lines(markdown) if allow_editor_tables else set()
    image_lines = _editor_image_lines(markdown)
    diagnostics: list[str] = []
    for line_number, line in enumerate(markdown.split("\n"), start=1):
        if not line.strip():
            continue
        if (
            line_number not in table_lines
            and line_number not in image_lines
            and _LOSSY_MARKDOWN_LINE_RE.match(line)
        ):
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

    if record.kind == "plan":
        return require_legal_plan_target_relpath(record.document_id, relpath)

    if record.kind == "runbook":
        if not _ALLOWED_EVAL_TIPTAP_MARKDOWN_RE.fullmatch(relpath):
            raise TiptapMarkdownWriteError(
                "runbook target_relpath must match an allowed Tiptap runbook path"
            )
        return normalize_tiptap_target_relpath(relpath)

    raise TiptapMarkdownWriteError(f"unsupported document kind: {record.kind}")


# Same envelope recognition as the editor's splitLeadingYamlFrontmatter.
_LEADING_YAML_ENVELOPE_RE = re.compile(
    r"^---[ \t]*(?:\r\n|\n)([\s\S]*?)(?:\r\n|\n)---[ \t]*(?:(?:\r\n|\n)|$)"
)
_YAML_KEY_RE = re.compile(r"(?:^|\r?\n)[A-Za-z0-9_.-]+:\s*")


def _leading_yaml_envelope(markdown: str) -> str:
    match = _LEADING_YAML_ENVELOPE_RE.match(markdown)
    return match[0] if match and _YAML_KEY_RE.search(match[1]) else ""


def _commit_blocking_lossy(
    kind: str,
    markdown: str,
    *,
    original: str = "",
) -> list[str]:
    if kind != "worldbuilding_source":
        return []
    if original:
        envelope = _leading_yaml_envelope(original)
        if envelope:
            if _leading_yaml_envelope(markdown) != envelope:
                return [
                    "Existing leading YAML frontmatter must remain unchanged.",
                    *markdown_lossy_diagnostics(markdown),
                ]
            # Blank out only the preserved envelope, keeping body diagnostics
            # in original source coordinates. Later delimiters remain checked.
            return markdown_lossy_diagnostics(
                "\n" * envelope.count("\n") + markdown[len(envelope) :],
                allow_editor_tables=True,
            )
    return markdown_lossy_diagnostics(markdown, allow_editor_tables=True)


class TiptapMarkdownWritePrepareRequest(BaseModel):
    title: str | None = None
    document_id: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    expected_revision: int | None = None
    write_mode: WriteMode | None = None
    schema_version: Literal["dmb_tiptap_markdown_write_prepare_v2"] | None = None
    scope_mode: Literal["world"] | None = None
    world_id: str | None = None

    @field_validator("title")
    @classmethod
    def canonical_title(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("title must be a nonempty string when supplied")
        return value.strip()

    @model_validator(mode="after")
    def validate_scope_contract(self):
        if "title" in self.model_fields_set and self.schema_version is None:
            raise ValueError("title intent requires a World-owned Plan V2 write")
        if self.schema_version is None:
            if self.scope_mode is not None or self.world_id is not None:
                raise ValueError("World-scoped writes require the V2 schema")
        elif (
            self.scope_mode != "world" or not self.world_id or not self.world_id.strip()
        ):
            raise ValueError("V2 World writes require scope_mode=world and world_id")
        return self


class TiptapMarkdownWritePrepareResponse(BaseModel):
    schema_version: str = "dmb_tiptap_markdown_write_prepare_v1"
    scope_mode: Literal["world"] | None = None
    world_id: str | None = None
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
    title: str | None = None
    document_id: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    writer_confirm_token: str = Field(min_length=1)
    expected_revision: int | None = None
    write_mode: WriteMode | None = None
    schema_version: Literal["dmb_tiptap_markdown_write_commit_v2"] | None = None
    scope_mode: Literal["world"] | None = None
    world_id: str | None = None

    @field_validator("title")
    @classmethod
    def canonical_title(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("title must be a nonempty string when supplied")
        return value.strip()

    @model_validator(mode="after")
    def validate_scope_contract(self):
        if "title" in self.model_fields_set and self.schema_version is None:
            raise ValueError("title intent requires a World-owned Plan V2 write")
        if self.schema_version is None:
            if self.scope_mode is not None or self.world_id is not None:
                raise ValueError("World-scoped writes require the V2 schema")
        elif (
            self.scope_mode != "world" or not self.world_id or not self.world_id.strip()
        ):
            raise ValueError("V2 World writes require scope_mode=world and world_id")
        return self


class TiptapMarkdownWriteCommitResponse(BaseModel):
    """Authoritative write receipt constructed under the document mutation lock.

    Clients must advance local base revision/fingerprint from this receipt. A later
    snapshot GET is verification only — never the operation that decides whether the
    durable commit succeeded.
    """

    schema_version: str = "dmb_tiptap_markdown_write_commit_v1"
    scope_mode: Literal["world"] | None = None
    world_id: str | None = None
    document_id: str
    title: str
    target_relpath: str
    target_display_path: str
    registry_revision: int
    committed_revision: int
    committed_record: WorkspaceDocumentRecordAny
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


def _final_content(markdown: str) -> str:
    if not markdown.strip():
        raise TiptapMarkdownWriteError("markdown must not be empty")
    return markdown.rstrip("\n") + "\n"


def _source_import_content(markdown: str) -> str:
    if markdown == "":
        raise TiptapMarkdownWriteError("markdown must not be empty")
    return markdown


def _content_for_write_mode(markdown: str, write_mode: WriteMode) -> str:
    if write_mode == "source_import":
        return _source_import_content(markdown)
    return _final_content(markdown)


def _confirm_token(
    document_id: str,
    registry_revision: int,
    relpath: str,
    content: str,
    file_state: str,
    write_mode: WriteMode,
    world_id: str | None = None,
    title: str | None = None,
) -> str:
    payload = (
        f"{document_id}\0{world_id or ''}\0{registry_revision}\0{relpath}\0{content}\0{file_state}\0{write_mode}"
    ).encode()
    if title is not None:
        payload += ("\0plan-title:v1\0" + title).encode()
    return blake3.blake3(payload).hexdigest()


def _map_registry_error(
    exc: WorkspaceDocumentRegistryError,
) -> TiptapMarkdownWriteError:
    if exc.status_code == 409:
        return TiptapMarkdownWriteConflictError(str(exc))
    error = TiptapMarkdownWriteError(str(exc))
    error.status_code = exc.status_code
    return error


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


def _content_receipt_locator(obj) -> str:
    """Public Tiptap receipt locator. Not filesystem authority.

    Durable ``target_relpath`` is used when present. Pathless Content uses
    ``kind:uuid`` so prepare and commit agree and no fake ``out/workspace/``
    path is invented.
    """
    if obj.target_relpath:
        return obj.target_relpath
    return f"{obj.kind}:{obj.work_object_id}"


def _require_requested_world_scope(obj, world_id: str | None) -> None:
    if world_id is None:
        if obj.world_id is not None:
            raise TiptapMarkdownWriteConflictError(
                "World-owned documents require the World-scoped V2 write contract"
            )
        return
    if (
        obj.kind not in ("plan", "runbook")
        or obj.world_id != world_id
        or obj.campaign_id is not None
        or obj.target_session is not None
    ):
        raise TiptapMarkdownWriteConflictError(
            "document scope does not match the selected World"
        )


def _prepare_plan_postgres(
    *,
    root: Path,
    request: TiptapMarkdownWritePrepareRequest,
    write_mode: WriteMode,
) -> TiptapMarkdownWritePrepareResponse | None:
    from application_state.content.service import (
        autosave_plan,
        autosave_runbook,
        get_content_optional,
    )
    from application_state.errors import ApplicationStateError

    try:
        obj = get_content_optional(request.document_id)
    except ApplicationStateError as exc:
        raise _map_registry_error(
            WorkspaceDocumentRegistryError(str(exc), status_code=exc.status_code)
        ) from exc
    if request.title is not None and (
        obj is None
        or obj.kind != "plan"
        or obj.world_id is None
        or obj.campaign_id is not None
    ):
        raise TiptapMarkdownWriteError(
            "title intent is only valid for World-owned Plans"
        )
    if obj is None:
        return None
    if obj.kind not in ("plan", "runbook"):
        return None
    _require_requested_world_scope(obj, request.world_id)
    if write_mode == "source_import":
        raise TiptapMarkdownWriteError(
            "source_import is only valid for worldbuilding_source documents"
        )
    content = _content_for_write_mode(request.markdown, write_mode)
    if (
        request.expected_revision is not None
        and obj.object_revision != request.expected_revision
    ):
        raise TiptapMarkdownWriteConflictError(
            f"revision mismatch: expected {request.expected_revision}, current {obj.object_revision}"
        )
    if obj.status == "discarded":
        raise TiptapMarkdownWriteConflictError(
            f"workspace document is discarded: {request.document_id}"
        )
    if obj.target_relpath:
        from apps.live_control_server.services.workspace_document_registry import (
            _record_from_work_object,
        )

        authorize_target_for_record(_record_from_work_object(obj))
    lossy = markdown_lossy_diagnostics(request.markdown)
    autosave = autosave_plan if obj.kind == "plan" else autosave_runbook
    try:
        autosave_kwargs = {"expected_revision": request.expected_revision}
        if obj.kind == "plan":
            autosave_kwargs["expected_world_id"] = request.world_id
        obj = autosave(request.document_id, content, **autosave_kwargs)
    except ApplicationStateError as exc:
        raise _map_registry_error(
            WorkspaceDocumentRegistryError(str(exc), status_code=exc.status_code)
        ) from exc
    relpath = _content_receipt_locator(obj)
    return TiptapMarkdownWritePrepareResponse(
        document_id=str(obj.work_object_id),
        title=request.title if request.title is not None else obj.title,
        target_relpath=relpath,
        target_display_path=relpath,
        registry_revision=obj.object_revision,
        file_exists=False,
        writer_ok=True,
        writer_phase="prepare",
        writer_confirm_token=_confirm_token(
            str(obj.work_object_id),
            obj.object_revision,
            relpath,
            content,
            "postgres",
            write_mode,
            world_id=request.world_id,
            title=request.title,
        ),
        writer_diff="",
        existing_size_bytes=None,
        new_size_bytes=len(content.encode()),
        warnings=_prepare_warnings(
            exists=False,
            writer_ok=True,
            blocking_lossy=[],
            advisory_lossy=lossy,
            write_mode=write_mode,
        ),
        diagnostics=[
            "working copy persisted; Markdown file is not authority",
            "review before commit",
            *lossy,
        ],
        schema_version=(
            "dmb_tiptap_markdown_write_prepare_v2"
            if request.world_id is not None
            else "dmb_tiptap_markdown_write_prepare_v1"
        ),
        scope_mode="world" if request.world_id is not None else None,
        world_id=request.world_id,
    )


def _commit_plan_postgres(
    *,
    request: TiptapMarkdownWriteCommitRequest,
    write_mode: WriteMode,
) -> TiptapMarkdownWriteCommitResponse | None:
    from application_state.content.service import (
        commit_plan,
        commit_runbook,
        get_content_optional,
    )
    from application_state.errors import ApplicationStateError

    try:
        obj = get_content_optional(request.document_id)
    except ApplicationStateError as exc:
        raise _map_registry_error(
            WorkspaceDocumentRegistryError(str(exc), status_code=exc.status_code)
        ) from exc
    if request.title is not None and (
        obj is None
        or obj.kind != "plan"
        or obj.world_id is None
        or obj.campaign_id is not None
    ):
        raise TiptapMarkdownWriteError(
            "title intent is only valid for World-owned Plans"
        )
    if obj is None:
        return None
    if obj.kind not in ("plan", "runbook"):
        return None
    _require_requested_world_scope(obj, request.world_id)
    if write_mode == "source_import":
        raise TiptapMarkdownWriteError(
            "source_import is only valid for worldbuilding_source documents"
        )
    if obj.target_relpath:
        from apps.live_control_server.services.workspace_document_registry import (
            _record_from_work_object,
        )

        authorize_target_for_record(_record_from_work_object(obj))
    content = _content_for_write_mode(request.markdown, write_mode)
    relpath = _content_receipt_locator(obj)

    def _token_for(revision: int) -> str:
        return _confirm_token(
            str(obj.work_object_id),
            revision,
            relpath,
            content,
            "postgres",
            write_mode,
            world_id=request.world_id,
            title=request.title,
        )

    expected_revision = obj.object_revision
    if request.writer_confirm_token != _token_for(obj.object_revision):
        prior_revision = obj.object_revision - 1
        if prior_revision < 1 or request.writer_confirm_token != _token_for(
            prior_revision
        ):
            raise TiptapMarkdownWriteConflictError(
                "stale writer confirm token; prepare file write again"
            )
        expected_revision = prior_revision
    commit = commit_plan if obj.kind == "plan" else commit_runbook
    try:
        commit_kwargs = {"expected_revision": expected_revision}
        if obj.kind == "plan":
            commit_kwargs["expected_world_id"] = request.world_id
            commit_kwargs["title"] = request.title
        committed, revision = commit(request.document_id, content, **commit_kwargs)
    except ApplicationStateError as exc:
        raise _map_registry_error(
            WorkspaceDocumentRegistryError(str(exc), status_code=exc.status_code)
        ) from exc
    from apps.live_control_server.services.workspace_document_registry import (
        _record_from_work_object,
    )

    record = _record_from_work_object(committed)
    locator = _content_receipt_locator(committed)
    return TiptapMarkdownWriteCommitResponse(
        document_id=record.document_id,
        title=record.title,
        target_relpath=locator,
        target_display_path=locator,
        registry_revision=record.revision,
        committed_revision=record.revision,
        committed_record=record,
        normalized_content_sha256=revision.content_sha256,
        writer_ok=True,
        writer_phase="commit",
        bytes_written=len(content.encode()),
        file_fingerprint="postgres",
        backup_relpath=None,
        diagnostics=["WorkRevision committed in PostgreSQL"],
        schema_version=(
            "dmb_tiptap_markdown_write_commit_v2"
            if request.world_id is not None
            else "dmb_tiptap_markdown_write_commit_v1"
        ),
        scope_mode="world" if request.world_id is not None else None,
        world_id=request.world_id,
    )


def prepare_tiptap_markdown_write(
    *, root: Path, request: TiptapMarkdownWritePrepareRequest
) -> TiptapMarkdownWritePrepareResponse:
    validate_saved_media_references(request.markdown)
    write_mode = _normalize_write_mode(request.write_mode)
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    try:
        state = pages.find_page(request.document_id)
        if state is not None:
            return _prepare_page(request, write_mode, state)
    except ApplicationStateError as exc:
        raise _map_registry_error(
            WorkspaceDocumentRegistryError(str(exc), status_code=exc.status_code)
        ) from exc
    result = _prepare_plan_postgres(root=root, request=request, write_mode=write_mode)
    if result is None:
        error = TiptapMarkdownWriteError("workspace document not found")
        error.status_code = 404
        raise error
    return result


def commit_tiptap_markdown_write(
    *, root: Path, request: TiptapMarkdownWriteCommitRequest
) -> TiptapMarkdownWriteCommitResponse:
    validate_saved_media_references(request.markdown)
    write_mode = _normalize_write_mode(request.write_mode)
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    try:
        state = pages.find_page(request.document_id)
        if state is not None:
            return _commit_page(request, write_mode, state)
    except ApplicationStateError as exc:
        raise _map_registry_error(
            WorkspaceDocumentRegistryError(str(exc), status_code=exc.status_code)
        ) from exc
    result = _commit_plan_postgres(request=request, write_mode=write_mode)
    if result is None:
        error = TiptapMarkdownWriteError("workspace document not found")
        error.status_code = 404
        raise error
    return result


def _page_write_basis(request, state):
    from application_state.content import pages

    if request.title is not None or request.world_id is not None:
        raise TiptapMarkdownWriteError(
            "World-owned Plan write contract cannot write an authored Page"
        )
    saved = pages.committed_page(request.document_id, world_id=state.page.world_id)
    if saved.page.status != "active":
        raise TiptapMarkdownWriteConflictError("authored Page is discarded")
    return saved


def _page_token(saved, revision, copy_revision, content, mode):
    return _confirm_token(
        str(saved.page.work_object_id),
        revision,
        _content_receipt_locator(saved.page),
        content,
        f"page-copy:{copy_revision or 0}",
        mode,
        world_id=saved.page.world_id,
    )


def _page_import_eligible(saved):
    if saved.revision is not None or saved.working_copy_revision is not None:
        raise TiptapMarkdownWriteConflictError(
            "source_import requires an untouched, uninitialized Page"
        )


def _prepare_page(request, mode, state):
    saved = _page_write_basis(request, state)
    if (
        request.expected_revision is not None
        and request.expected_revision != saved.page.object_revision
    ):
        raise TiptapMarkdownWriteConflictError("authored Page revision changed")
    if mode == "source_import":
        _page_import_eligible(saved)
    from application_state.content.types import normalize_markdown

    content = normalize_markdown(_content_for_write_mode(request.markdown, mode))
    original = saved.revision.markdown if saved.revision else ""
    blocking = (
        []
        if mode == "source_import"
        else _commit_blocking_lossy("worldbuilding_source", content, original=original)
    )
    locator = _content_receipt_locator(saved.page)
    return TiptapMarkdownWritePrepareResponse(
        document_id=request.document_id,
        title=saved.page.title,
        target_relpath=locator,
        target_display_path=locator,
        registry_revision=saved.page.object_revision,
        file_exists=False,
        writer_ok=not blocking,
        writer_phase="prepare",
        writer_confirm_token=None
        if blocking
        else _page_token(
            saved,
            saved.page.object_revision,
            saved.working_copy_revision,
            content,
            mode,
        ),
        writer_diff="".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=locator,
                tofile=locator,
            )
        ),
        existing_size_bytes=len(original.encode()) if saved.revision else None,
        new_size_bytes=len(content.encode()),
        warnings=["Commit blocked: unsupported Markdown would be lossy."]
        if blocking
        else [],
        diagnostics=["Page prepare is read-only; review before Save", *blocking],
    )


def _commit_page(request, mode, state):
    from application_state.content import pages
    from apps.live_control_server.services.workspace_document_registry import (
        _record_from_page,
    )

    saved = _page_write_basis(request, state)
    from application_state.content.types import normalize_markdown

    content = normalize_markdown(_content_for_write_mode(request.markdown, mode))
    revision = saved.page.object_revision
    copy_revision = saved.working_copy_revision
    replay = False
    if request.writer_confirm_token != _page_token(
        saved, revision, copy_revision, content, mode
    ):
        prior_revision = revision - 1
        prior_copy = (copy_revision or 0) - 1
        if (
            prior_revision < 1
            or prior_copy < 0
            or request.writer_confirm_token
            != _page_token(saved, prior_revision, prior_copy or None, content, mode)
        ):
            raise TiptapMarkdownWriteConflictError(
                "stale writer confirm token; prepare Save again"
            )
        revision, copy_revision, replay = prior_revision, prior_copy or None, True
    if request.expected_revision is not None and request.expected_revision != revision:
        raise TiptapMarkdownWriteConflictError("authored Page revision changed")
    if mode == "source_import" and not replay:
        _page_import_eligible(saved)
    original = saved.revision.markdown if saved.revision else ""
    blocking = (
        []
        if mode == "source_import"
        else _commit_blocking_lossy("worldbuilding_source", content, original=original)
    )
    if blocking:
        raise TiptapMarkdownWriteError("commit blocked: " + "; ".join(blocking[:3]))
    committed, revision = pages.commit_page(
        request.document_id,
        content,
        world_id=saved.page.world_id,
        expected_revision=revision,
        expected_working_copy_revision=copy_revision,
    )
    record = _record_from_page(committed)
    locator = _content_receipt_locator(committed.page)
    return TiptapMarkdownWriteCommitResponse(
        document_id=record.document_id,
        title=record.title,
        target_relpath=locator,
        target_display_path=locator,
        registry_revision=record.revision,
        committed_revision=record.revision,
        committed_record=record,
        normalized_content_sha256=revision.content_sha256,
        writer_ok=True,
        writer_phase="commit",
        bytes_written=len(revision.markdown.encode()),
        file_fingerprint="postgres",
        diagnostics=["Page WorkRevision committed in PostgreSQL"],
    )
