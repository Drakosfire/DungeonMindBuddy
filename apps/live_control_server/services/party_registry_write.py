"""Prepare/commit writes for campaign ``_party_registry.json`` session rosters."""

from __future__ import annotations

import difflib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import blake3
from pydantic import BaseModel, Field, field_validator

from src.graph_memory.party_context import (
    PARTY_REGISTRY_BASENAME,
    PARTY_REGISTRY_SCHEMA,
    load_party_registry,
    party_registry_path,
    resolve_campaign_corpus,
)
from src.graph_memory.session_graph_context import normalize_registry_view
from src.live_play.recap_stage_paths import corpus_root

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")
_ALLOWED_REGISTRY_RE = re.compile(
    r"^Longmont Campaign/Campaign \d+/_party_registry\.json$"
)


class PartyRegistryWriteError(ValueError):
    status_code = 422


class PartyRegistryWriteConflictError(PartyRegistryWriteError):
    status_code = 409


class PartyRegistrySessionRosterWritePrepareRequest(BaseModel):
    campaign_id: str = Field(min_length=1)
    session: int = Field(ge=1)
    pc_slugs: list[str] = Field(default_factory=list)
    companion_slugs: list[str] = Field(default_factory=list)
    copy_from_session: int | None = Field(default=None, ge=1)

    @field_validator("pc_slugs", "companion_slugs", mode="before")
    @classmethod
    def _normalize_slug_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("slug lists must be arrays")
        out: list[str] = []
        for raw in value:
            slug = str(raw).strip()
            if slug and slug not in out:
                out.append(slug)
        return out


class PartyRegistrySessionRosterWritePrepareResponse(BaseModel):
    schema_version: Literal["dmb_party_registry_session_roster_write_prepare_v1"] = (
        "dmb_party_registry_session_roster_write_prepare_v1"
    )
    campaign_id: str
    session: int
    registry_relpath: str
    file_exists: bool
    writer_ok: bool
    writer_phase: str | None = None
    writer_confirm_token: str | None = None
    writer_diff: str | None = None
    existing_size_bytes: int | None = None
    new_size_bytes: int | None = None
    pc_slugs: list[str] = Field(default_factory=list)
    companion_slugs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class PartyRegistrySessionRosterWriteCommitRequest(BaseModel):
    campaign_id: str = Field(min_length=1)
    session: int = Field(ge=1)
    pc_slugs: list[str] = Field(default_factory=list)
    companion_slugs: list[str] = Field(default_factory=list)
    copy_from_session: int | None = Field(default=None, ge=1)
    writer_confirm_token: str = Field(min_length=1)

    @field_validator("pc_slugs", "companion_slugs", mode="before")
    @classmethod
    def _normalize_slug_lists(cls, value: Any) -> list[str]:
        return PartyRegistrySessionRosterWritePrepareRequest._normalize_slug_lists(value)


class PartyRegistrySessionRosterWriteCommitResponse(BaseModel):
    schema_version: Literal["dmb_party_registry_session_roster_write_commit_v1"] = (
        "dmb_party_registry_session_roster_write_commit_v1"
    )
    campaign_id: str
    session: int
    registry_relpath: str
    writer_ok: bool
    writer_phase: str | None = None
    bytes_written: int | None = None
    file_fingerprint: str | None = None
    backup_relpath: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


def _registry_relpath(campaign_id: str) -> str:
    root, rel = resolve_campaign_corpus(campaign_id, corpus_root=corpus_root())
    return f"{rel}/{PARTY_REGISTRY_BASENAME}"


def _registry_target(campaign_id: str) -> Path:
    root, rel = resolve_campaign_corpus(campaign_id, corpus_root=corpus_root())
    relpath = f"{rel}/{PARTY_REGISTRY_BASENAME}"
    if not _ALLOWED_REGISTRY_RE.fullmatch(relpath):
        raise PartyRegistryWriteError(f"registry path not writable: {relpath}")
    return party_registry_path(root, rel).resolve()


def _file_state_token(path: Path) -> str:
    if not path.is_file():
        return "missing"
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _confirm_token(relpath: str, content: str, file_state_token: str) -> str:
    payload = f"{relpath}\n{file_state_token}\n{content}"
    return blake3.blake3(payload.encode()).hexdigest()


def _validate_slugs(slugs: list[str], *, label: str) -> None:
    for slug in slugs:
        if not _SLUG_RE.fullmatch(slug):
            raise PartyRegistryWriteError(f"invalid {label} slug: {slug!r}")


def _empty_registry(campaign_id: str) -> dict[str, Any]:
    return {
        "schema": PARTY_REGISTRY_SCHEMA,
        "campaign_id": campaign_id,
        "pc_party_names": [],
        "session_pc_rosters": {},
        "session_companion_rosters": {},
    }


def _apply_session_roster_v1(
    registry: dict[str, Any],
    *,
    session_key: str,
    pc_slugs: list[str],
    companion_slugs: list[str],
    copy_from_session: int | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    updated = dict(registry)
    pc_rosters = dict(updated.get("session_pc_rosters") or {})
    companion_rosters = dict(updated.get("session_companion_rosters") or {})

    if copy_from_session is not None:
        source_key = str(copy_from_session)
        if source_key not in pc_rosters and source_key not in companion_rosters:
            raise PartyRegistryWriteError(
                f"copy_from_session {copy_from_session} has no roster in registry"
            )
        if not pc_slugs:
            pc_slugs = list(pc_rosters.get(source_key) or [])
        if not companion_slugs:
            companion_slugs = list(companion_rosters.get(source_key) or [])
        warnings.append(f"copied roster slugs from session {copy_from_session}")

    if not pc_slugs and not companion_slugs:
        raise PartyRegistryWriteError("session roster must include at least one PC or companion slug")

    _validate_slugs(pc_slugs, label="PC")
    _validate_slugs(companion_slugs, label="companion")

    pc_rosters[session_key] = pc_slugs
    updated["session_pc_rosters"] = pc_rosters
    if companion_slugs:
        companion_rosters[session_key] = companion_slugs
    elif session_key in companion_rosters:
        del companion_rosters[session_key]
    updated["session_companion_rosters"] = companion_rosters
    return updated, warnings


def _serialize_registry(registry: dict[str, Any]) -> str:
    return json.dumps(registry, indent=2, ensure_ascii=False) + "\n"


def _build_updated_registry(
    *,
    campaign_id: str,
    session: int,
    pc_slugs: list[str],
    companion_slugs: list[str],
    copy_from_session: int | None,
) -> tuple[dict[str, Any], list[str]]:
    root, rel = resolve_campaign_corpus(campaign_id, corpus_root=corpus_root())
    existing = load_party_registry(root, rel)
    registry = dict(existing) if existing else _empty_registry(campaign_id)
    if not registry.get("campaign_id"):
        registry["campaign_id"] = campaign_id
    return _apply_session_roster_v1(
        registry,
        session_key=str(session),
        pc_slugs=pc_slugs,
        companion_slugs=companion_slugs,
        copy_from_session=copy_from_session,
    )


def prepare_party_registry_session_roster_write(
    request: PartyRegistrySessionRosterWritePrepareRequest,
) -> PartyRegistrySessionRosterWritePrepareResponse:
    relpath = _registry_relpath(request.campaign_id)
    target = _registry_target(request.campaign_id)
    updated, warnings = _build_updated_registry(
        campaign_id=request.campaign_id,
        session=request.session,
        pc_slugs=list(request.pc_slugs),
        companion_slugs=list(request.companion_slugs),
        copy_from_session=request.copy_from_session,
    )
    content = _serialize_registry(updated)
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
    session_key = str(request.session)
    view = normalize_registry_view(updated)
    roster = view.get("session_rosters", {}).get(session_key, {})
    return PartyRegistrySessionRosterWritePrepareResponse(
        campaign_id=request.campaign_id,
        session=request.session,
        registry_relpath=relpath,
        file_exists=exists,
        writer_ok=True,
        writer_phase="prepare",
        writer_confirm_token=_confirm_token(relpath, content, _file_state_token(target)),
        writer_diff=diff,
        existing_size_bytes=len(existing.encode()) if exists else None,
        new_size_bytes=len(content.encode()),
        pc_slugs=list(roster.get("pcs") or []),
        companion_slugs=list(roster.get("companions") or []),
        warnings=warnings,
        diagnostics=[
            "dry-run only; _party_registry.json was not written",
            "graph ingest will pick up anchors after commit and registry reload",
        ],
    )


def commit_party_registry_session_roster_write(
    request: PartyRegistrySessionRosterWriteCommitRequest,
) -> PartyRegistrySessionRosterWriteCommitResponse:
    relpath = _registry_relpath(request.campaign_id)
    target = _registry_target(request.campaign_id)
    updated, _warnings = _build_updated_registry(
        campaign_id=request.campaign_id,
        session=request.session,
        pc_slugs=list(request.pc_slugs),
        companion_slugs=list(request.companion_slugs),
        copy_from_session=request.copy_from_session,
    )
    content = _serialize_registry(updated)
    expected = _confirm_token(relpath, content, _file_state_token(target))
    if request.writer_confirm_token != expected:
        raise PartyRegistryWriteConflictError(
            "stale writer confirm token; prepare registry write again"
        )

    backup_relpath: str | None = None
    root = corpus_root().resolve()
    target = _registry_target(request.campaign_id)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup = target.parent / ".backups" / f"{timestamp}__{PARTY_REGISTRY_BASENAME}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(target.read_bytes())
            backup_relpath = backup.resolve().relative_to(root).as_posix()
        target.write_text(content, encoding="utf-8", newline="\n")
    except OSError as exc:
        error = PartyRegistryWriteError(f"failed to write party registry: {exc}")
        error.status_code = 500
        raise error from exc

    return PartyRegistrySessionRosterWriteCommitResponse(
        campaign_id=request.campaign_id,
        session=request.session,
        registry_relpath=relpath,
        writer_ok=True,
        writer_phase="commit",
        bytes_written=len(content.encode()),
        file_fingerprint=blake3.blake3(content.encode()).hexdigest(),
        backup_relpath=backup_relpath,
        diagnostics=[
            "session roster committed to _party_registry.json",
            "reload Party Registry to refresh graph context preview",
        ],
    )
