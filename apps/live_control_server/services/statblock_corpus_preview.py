from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.statblock_draft_store import (
    StoredStatblockDraftRecord,
    read_statblock_draft,
)
from apps.live_control_server.services.statblock_workbench import StatblockWorkbenchAction
from src.agent.corpus_writer import is_writable_corpus_path
from src.statblocks.lifecycle_artifact import StatblockBreadcrumb
from src.statblocks.v2_contract import CombatDefaults, SourceRef

SCHEMA_VERSION_PREVIEW = "dmb_statblock_corpus_promotion_preview_v1"
CORPUS_ROOT_DISPLAY = "corpus/eldyrwild-markdown"
_SAFE_RELPATH_PART = re.compile(r"^[^\\/]+$")
_LONGMONT_CAMPAIGN_RE = re.compile(r"^longmont-c(\d+)$", re.IGNORECASE)


class StatblockPromotionWarning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class StatblockCorpusPromotionPreviewRequest(BaseModel):
    include_writer_allowlist_check: bool = True


class StatblockCorpusPromotionPreviewValidation(BaseModel):
    ok: bool
    proposed_path_safe: bool
    writer_allowed_now: bool | None = None
    writer_reason: str | None = None


class StatblockCorpusPromotionPreviewResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_promotion_preview_v1"] = (
        SCHEMA_VERSION_PREVIEW
    )
    preview_id: str
    artifact_id: str
    draft_id: str
    title: str
    campaign_id: str
    session: int
    source_record_path: str
    corpus_root_display: str = CORPUS_ROOT_DISPLAY
    proposed_corpus_relpath: str
    proposed_corpus_display_path: str
    frontmatter: dict[str, Any]
    frontmatter_text: str
    markdown_body: str
    full_markdown: str
    breadcrumbs: list[StatblockBreadcrumb]
    source_refs: list[SourceRef]
    combat_defaults: CombatDefaults
    warnings: list[StatblockPromotionWarning] = Field(default_factory=list)
    validation: StatblockCorpusPromotionPreviewValidation
    preview_token: str
    diagnostics: list[str] = Field(default_factory=list)
    available_actions: list[StatblockWorkbenchAction] = Field(default_factory=list)


def slugify_statblock_title(title: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", normalized.lower()).strip("_")
    if not slug:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", fallback.lower()).strip("_")
    return slug or "statblock_draft"


def campaign_corpus_prefix(
    campaign_id: str,
) -> tuple[str, int | None, list[StatblockPromotionWarning]]:
    match = _LONGMONT_CAMPAIGN_RE.fullmatch(campaign_id.strip())
    if match:
        campaign_number = int(match.group(1))
        return (
            f"Longmont Campaign/Campaign {campaign_number}",
            campaign_number,
            [],
        )
    safe_campaign = slugify_statblock_title(campaign_id, "unknown_campaign")
    return (
        f"Generated Statblocks/{safe_campaign}",
        None,
        [
            StatblockPromotionWarning(
                code="unknown_campaign_mapping",
                message=(
                    "No corpus campaign mapping is configured for this campaign_id; "
                    "preview uses a conservative generated-statblock fallback path."
                ),
                severity="warning",
            )
        ],
    )


def _path_is_safe(relpath: str) -> bool:
    if not relpath or relpath.startswith(("/", "~")) or "://" in relpath:
        return False
    parts = Path(relpath).parts
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return all(_SAFE_RELPATH_PART.match(part) for part in parts)


def proposed_statblock_corpus_relpath(
    campaign_id: str, title: str, artifact_id: str
) -> tuple[str, int | None, list[StatblockPromotionWarning]]:
    prefix, campaign_number, warnings = campaign_corpus_prefix(campaign_id)
    slug = slugify_statblock_title(title, artifact_id)
    if prefix.startswith("Generated Statblocks/"):
        return f"{prefix}/{slug}.md", campaign_number, warnings
    return f"{prefix}/Statblocks/generated/{slug}.md", campaign_number, warnings


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", text) and text not in {"true", "false", "null"}:
        return text
    return json.dumps(text, ensure_ascii=False)


def _render_yaml_value(key: str, value: Any) -> list[str]:
    if isinstance(value, list):
        lines = [f"{key}:"]
        if not value:
            return [f"{key}: []"]
        for item in value:
            if isinstance(item, dict):
                compact = json.dumps(item, ensure_ascii=False, sort_keys=True)
                lines.append(f"  - {_yaml_scalar(compact)}")
            else:
                lines.append(f"  - {_yaml_scalar(item)}")
        return lines
    if isinstance(value, dict):
        compact = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return [f"{key}: {_yaml_scalar(compact)}"]
    return [f"{key}: {_yaml_scalar(value)}"]


def render_frontmatter_text(frontmatter: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.extend(_render_yaml_value(key, value))
    lines.append("---")
    return "\n".join(lines)


def _breadcrumb_frontmatter_values(breadcrumbs: list[StatblockBreadcrumb]) -> list[str]:
    return [breadcrumb.label for breadcrumb in breadcrumbs]


def render_statblock_frontmatter(
    record: StoredStatblockDraftRecord,
    *,
    campaign_id: str,
    session: int,
    campaign_number: int | None,
) -> tuple[dict[str, Any], str]:
    artifact = record.artifact
    statblock = artifact.structured_statblock
    frontmatter: dict[str, Any] = {
        "schema_version": "dmb_corpus_statblock_v1",
        "document_class": "statblock",
        "source_type": "generated_statblock_draft",
        "title": artifact.title,
        "campaign_id": campaign_id,
        "session": session,
        "artifact_id": artifact.artifact_id,
        "draft_id": artifact.draft_id,
        "review_status": artifact.review_status,
        "lifecycle_state": artifact.lifecycle_state,
        "storage_status": artifact.storage_status,
        "corpus_status": "promotion_previewed",
        "created_by": artifact.created_by,
        "created_at": artifact.created_at,
        "updated_at": record.updated_at,
        "generated_by": "dungeonbuddy_statblock_workbench",
        "statblock_generator": artifact.provenance.generator,
        "challenge_rating": statblock.get("challenge_rating"),
        "creature_type": statblock.get("type"),
        "source_record_path": record.storage_path,
        "breadcrumbs": _breadcrumb_frontmatter_values(artifact.breadcrumbs),
        "source_refs": [
            ref.id or ref.label or ref.path or ref.uri
            for ref in artifact.source_refs
            if ref.id or ref.label or ref.path or ref.uri
        ],
    }
    if campaign_number is not None:
        frontmatter = {
            **dict(list(frontmatter.items())[:5]),
            "campaign_number": campaign_number,
            **dict(list(frontmatter.items())[5:]),
        }
    return frontmatter, render_frontmatter_text(frontmatter)


def _combat_line(label: str, value: Any) -> str | None:
    if value in (None, "", []):
        return None
    if isinstance(value, list):
        if not value:
            return None
        return f"- {label}: {', '.join(str(item) for item in value)}"
    return f"- {label}: {value}"


def _render_breadcrumbs(breadcrumbs: list[StatblockBreadcrumb]) -> str:
    if not breadcrumbs:
        return "- _No breadcrumbs recorded._"
    lines = []
    for breadcrumb in breadcrumbs:
        source = f" — {breadcrumb.source}" if breadcrumb.source else ""
        target = f" ({breadcrumb.target})" if breadcrumb.target else ""
        lines.append(f"- `{breadcrumb.label}`{source}{target}")
    return "\n".join(lines)


def _render_review_warnings(record: StoredStatblockDraftRecord) -> str:
    if not record.artifact.warnings:
        return "- No draft review warnings were recorded."
    lines = []
    for warning in record.artifact.warnings:
        code = warning.code or "review_warning"
        lines.append(f"- {warning.severity.upper()} `{code}`: {warning.message}")
    return "\n".join(lines)


def render_statblock_markdown_body(
    record: StoredStatblockDraftRecord,
    preview_warnings: list[StatblockPromotionWarning],
) -> str:
    artifact = record.artifact
    defaults = artifact.combat_defaults
    combat_lines = [
        _combat_line("AC", defaults.armor_class),
        _combat_line("HP", defaults.hit_points),
        _combat_line("Initiative", f"{defaults.initiative_bonus:+d}" if defaults.initiative_bonus is not None else None),
        _combat_line("Passive Perception", defaults.passive_perception),
        _combat_line("Speed", defaults.effective_speed_summary),
        _combat_line("Primary actions", defaults.primary_actions),
    ]
    rendered_combat = "\n".join(line for line in combat_lines if line) or "- No combat defaults recorded."
    preview_warning_lines = (
        "\n".join(
            f"- {warning.severity.upper()} `{warning.code}`: {warning.message}"
            for warning in preview_warnings
        )
        if preview_warnings
        else "- No promotion preview warnings."
    )
    provenance = json.dumps(artifact.provenance.model_dump(mode="json"), indent=2, sort_keys=True)
    return (
        f"# {artifact.title}\n\n"
        "> Generated statblock draft promoted from DungeonBuddy Workbench preview. Review before corpus write.\n\n"
        "## Status\n\n"
        f"- Review status: {artifact.review_status}\n"
        f"- Source artifact: `{artifact.artifact_id}`\n"
        f"- Draft id: `{artifact.draft_id}`\n"
        "- Corpus status: promotion_previewed\n\n"
        "## Combat Defaults\n\n"
        f"{rendered_combat}\n\n"
        "## Statblock\n\n"
        f"{artifact.markdown.strip()}\n\n"
        "## Review Warnings\n\n"
        f"{_render_review_warnings(record)}\n\n"
        "## Promotion Preview Warnings\n\n"
        f"{preview_warning_lines}\n\n"
        "## Corpus Breadcrumbs\n\n"
        f"{_render_breadcrumbs(artifact.breadcrumbs)}\n\n"
        "## Provenance\n\n"
        "```json\n"
        f"{provenance}\n"
        "```\n"
    )


def build_preview_token(
    record: StoredStatblockDraftRecord, relpath: str, full_markdown: str
) -> str:
    full_markdown_hash = hashlib.sha256(full_markdown.encode("utf-8")).hexdigest()
    payload = "\n".join(
        [
            record.artifact_id,
            record.artifact.draft_id,
            record.updated_at,
            relpath,
            full_markdown_hash,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _future_preview_actions() -> list[StatblockWorkbenchAction]:
    return [
        StatblockWorkbenchAction(
            action_id="confirm_corpus_write",
            label="Confirm corpus write",
            disabled_reason="Future PR will require an explicit confirmation token.",
        ),
        StatblockWorkbenchAction(
            action_id="ingest_to_semantic_layer",
            label="Ingest to Semantic Knowledge Layer",
            disabled_reason="Disabled until corpus write exists.",
        ),
        StatblockWorkbenchAction(
            action_id="add_to_combat",
            label="Add to combat",
            disabled_reason="Disabled until corpus-backed Statblock View/combat integration exists.",
        ),
    ]


def build_statblock_corpus_promotion_preview(
    *,
    base: Path,
    packet: dict[str, Any],
    artifact_id: str,
    include_writer_allowlist_check: bool = True,
) -> StatblockCorpusPromotionPreviewResponse:
    campaign_id = str(packet["campaign_id"])
    session = int(packet["session"])
    record = read_statblock_draft(base=base, artifact_id=artifact_id)
    relpath, campaign_number, warnings = proposed_statblock_corpus_relpath(
        campaign_id, record.artifact.title, record.artifact_id
    )
    proposed_path_safe = _path_is_safe(relpath)
    if not proposed_path_safe:
        warnings.append(
            StatblockPromotionWarning(
                code="unsafe_proposed_path",
                message="The proposed corpus-relative path failed preview safety validation.",
                severity="error",
            )
        )
    if not record.artifact.breadcrumbs:
        warnings.append(
            StatblockPromotionWarning(
                code="missing_breadcrumbs",
                message="Stored draft has no breadcrumbs; review provenance before corpus write.",
                severity="warning",
            )
        )

    writer_allowed_now: bool | None = None
    writer_reason: str | None = None
    if include_writer_allowlist_check:
        writer_allowed_now, writer_reason = is_writable_corpus_path(relpath, "create")
        if not writer_allowed_now:
            warnings.append(
                StatblockPromotionWarning(
                    code="writer_allowlist_pending",
                    message=(
                        "Current corpus writer allowlist does not yet permit this "
                        "generated statblock path; PR109 must add/confirm the write "
                        "allowlist before commit."
                    ),
                    severity="info",
                )
            )

    frontmatter, frontmatter_text = render_statblock_frontmatter(
        record,
        campaign_id=campaign_id,
        session=session,
        campaign_number=campaign_number,
    )
    markdown_body = render_statblock_markdown_body(record, warnings)
    full_markdown = f"{frontmatter_text}\n\n{markdown_body}"
    preview_token = build_preview_token(record, relpath, full_markdown)
    validation = StatblockCorpusPromotionPreviewValidation(
        ok=proposed_path_safe and not any(warning.severity == "error" for warning in warnings),
        proposed_path_safe=proposed_path_safe,
        writer_allowed_now=writer_allowed_now,
        writer_reason=writer_reason or None,
    )
    return StatblockCorpusPromotionPreviewResponse(
        preview_id=f"preview-{preview_token}",
        artifact_id=record.artifact_id,
        draft_id=record.artifact.draft_id,
        title=record.artifact.title,
        campaign_id=campaign_id,
        session=session,
        source_record_path=record.storage_path,
        proposed_corpus_relpath=relpath,
        proposed_corpus_display_path=f"{CORPUS_ROOT_DISPLAY}/{relpath}",
        frontmatter=frontmatter,
        frontmatter_text=frontmatter_text,
        markdown_body=markdown_body,
        full_markdown=full_markdown,
        breadcrumbs=record.artifact.breadcrumbs,
        source_refs=record.artifact.source_refs,
        combat_defaults=record.artifact.combat_defaults,
        warnings=warnings,
        validation=validation,
        preview_token=preview_token,
        diagnostics=[
            "preview only; no corpus write occurred",
            "no Semantic Knowledge Layer ingestion occurred",
            "no stored draft mutation, event append, job queue append, or combat mutation occurred",
        ],
        available_actions=_future_preview_actions(),
    )
