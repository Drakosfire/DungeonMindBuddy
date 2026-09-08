"""Broad exact C1/C2 source adoption into durable APP-STATE.

Operator/migration boundary only. Runtime historical reading continues to use
``source.revision``. Checkout files are consulted here to locate exact bytes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateValidationError,
)
from application_state.config import load_runtime_dsn
from application_state.ingest.service import list_extraction_runs
from application_state.source import repository as source_repo
from application_state.source import service as source_service
from application_state.unit_of_work import unit_of_work
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    WorldSourceInventoryRow,
    list_world_heads,
    list_world_textual_source_inventory,
)
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    _component_by_kind,
    _resolve_repo_contained_uri,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    normalize_content_digest,
)

ADOPTION_SCHEMA = "dmb_source_exact_adoption_v1"
MARKDOWN_KINDS = frozenset({"markdown", "md", "text/markdown", "text", "", "none"})
TEXTUAL_DOMAINS = frozenset(
    {
        "recap",
        "session_recap",
        "worldbuilding",
        "manual_seed",
        "manual",
        "session_memory",
        "prep",
    }
)
DOMAIN_ALIASES = {
    "session_recap": "recap",
    "manual_seed": "manual",
}
C2S25_ARTIFACT_ID = "artifact:recap:longmont-c2:session-25:fd38b5915b32"
C2S25_DIGEST = "fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d"
C2S25_REVISION_ID = UUID("8ed1e034-23c6-4295-b2ff-05d5cdd643a9")
KNOWN_HISTORICAL_REVISION_IDS: dict[tuple[str, str], UUID] = {
    (C2S25_ARTIFACT_ID, C2S25_DIGEST): C2S25_REVISION_ID,
}

Classification = Literal[
    "CURRENT_EXACT",
    "ADOPTABLE_EXACT",
    "UNAVAILABLE_BYTES",
    "AUTHORITY_METADATA_INCOMPLETE",
    "UNSUPPORTED_MEDIA",
    "DIGEST_MISMATCH",
    "SCOPE_CONFLICT",
    "REVISION_ID_CONFLICT",
    "APP_STATE_CONFLICT",
]
BLOCKING_CLASSIFICATIONS = frozenset(
    {
        "DIGEST_MISMATCH",
        "SCOPE_CONFLICT",
        "REVISION_ID_CONFLICT",
        "APP_STATE_CONFLICT",
    }
)
SKIP_CLASSIFICATIONS = frozenset(
    {
        "UNAVAILABLE_BYTES",
        "AUTHORITY_METADATA_INCOMPLETE",
        "UNSUPPORTED_MEDIA",
    }
)
AuthorityKind = Literal["ingest_run", "world_source", "app_state"]
AdoptionMode = Literal["preview", "apply"]
IdentityKind = Literal[
    "historical_uuid_recovered",
    "new_durable_source_adoption",
    "current_exact",
    "none",
]


class SourceAdoptionError(Exception):
    """Operator-facing adoption failure with no product write."""


class SourceAdoptionInputError(SourceAdoptionError):
    """Invalid selector; inventory is not run."""


class SourceClaim(BaseModel):
    source_artifact_id: str
    source_domain: str
    campaign_id: str | None = None
    session_id: str | None = None
    world_id: str | None = None
    expected_sha256: str | None = None
    locator: str | None = None
    locators: list[str] = Field(default_factory=list)
    authority_kind: AuthorityKind
    supporting_run_ids: list[str] = Field(default_factory=list)
    supporting_authority_refs: list[str] = Field(default_factory=list)
    artifact_kind: str | None = None


class DurableTarget(BaseModel):
    source_artifact_id: str
    content_sha256: str | None = None
    source_domain: str
    campaign_id: str | None = None
    session_id: str | None = None
    world_id: str | None = None
    authority_kind: AuthorityKind
    locator: str | None = None
    classification: Classification
    known_source_revision_id: str | None = None
    identity_kind: IdentityKind = "none"
    supporting_run_ids: list[str] = Field(default_factory=list)
    supporting_authority_refs: list[str] = Field(default_factory=list)
    reason: list[str] = Field(default_factory=list)
    markdown: str | None = None
    source_revision_id: str | None = None
    wrote: bool = False


class SourceAdoptionReport(BaseModel):
    schema_version: Literal["dmb_source_exact_adoption_v1"] = ADOPTION_SCHEMA
    generated_at: str
    mode: AdoptionMode
    blocked: bool
    applied: bool = False
    world_id: str
    campaign_ids: list[str]
    world_head: str | None = None
    ingest_run_count: int = 0
    claim_count: int = 0
    target_count: int = 0
    source_target_set_sha256: str
    counts: dict[str, int] = Field(default_factory=dict)
    targets: list[DurableTarget] = Field(default_factory=list)
    newly_adopted: int = 0
    noop: int = 0
    skipped: int = 0
    new_durable_identities: int = 0
    detail: str | None = None


@dataclass(frozen=True)
class _ResolvedBytes:
    digest: str
    markdown: str
    locator: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _repo_relative(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved = path.resolve()
    return resolved.relative_to(resolved_root).as_posix()


def _normalize_locator(uri: str | None) -> str | None:
    if uri is None:
        return None
    cleaned = uri.strip()
    if not cleaned:
        return None
    if cleaned.startswith("/home/") or cleaned.startswith("/Users/"):
        return None
    return cleaned


def _is_markdown_media(
    *,
    artifact_kind: str | None,
    locator: str | None,
    source_domain: str | None = None,
) -> bool:
    loc = (locator or "").lower()
    if loc.endswith((".json", ".png", ".pdf", ".jpg", ".webp")):
        return False
    kind = str(artifact_kind or "").strip().lower()
    if kind in {"image", "png", "pdf", "json", "binary"}:
        return False
    if kind in MARKDOWN_KINDS:
        return True
    if loc.endswith(".md") or loc.endswith(".markdown"):
        return True
    return (source_domain or "") in TEXTUAL_DOMAINS


def known_historical_revision_id(artifact_id: str, digest: str) -> UUID | None:
    return KNOWN_HISTORICAL_REVISION_IDS.get((artifact_id, normalize_content_digest(digest)))


def resolve_exact_source_bytes(
    root: Path,
    uri: str,
    *,
    expected_digest: str,
) -> _ResolvedBytes:
    """Hash raw bytes, then decode UTF-8 Markdown. Fail closed on mismatch."""

    expected = normalize_content_digest(expected_digest)
    source_path = _resolve_repo_contained_uri(root, uri)
    if not source_path.is_file():
        raise GraphRunRegistryError(
            "exact source is not available for explicit adoption",
            status_code=404,
        )
    raw = source_path.read_bytes()
    actual_digest = hashlib.sha256(raw).hexdigest()
    if actual_digest != expected:
        raise GraphRunRegistryError(
            "exact source digest does not match the authoritative claim",
            status_code=422,
        )
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GraphRunRegistryError(
            f"exact source is not valid UTF-8: {exc}",
            status_code=422,
        ) from exc
    return _ResolvedBytes(
        digest=actual_digest,
        markdown=markdown,
        locator=_repo_relative(root, source_path),
    )


def _try_resolve(
    root: Path,
    uri: str | None,
    expected_digest: str,
) -> tuple[_ResolvedBytes | None, str | None]:
    if not uri or not uri.strip():
        return None, "locator missing"
    try:
        return resolve_exact_source_bytes(root, uri, expected_digest=expected_digest), None
    except GraphRunRegistryError as exc:
        if exc.status_code == 404:
            return None, "bytes unavailable"
        if "digest" in str(exc):
            return None, "digest mismatch"
        if "UTF-8" in str(exc):
            return None, "not utf-8"
        return None, str(exc)


def _unique_nonempty(values: Sequence[str | None]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _collect_locators(claims: Sequence[SourceClaim]) -> list[str]:
    """Ingest locators first, then World, preserving first-seen order."""

    ordered: list[str] = []
    ranked = sorted(
        claims,
        key=lambda claim: 0 if claim.authority_kind == "ingest_run" else 1,
    )
    for claim in ranked:
        for locator in (claim.locator, *claim.locators):
            normalized = _normalize_locator(locator)
            if normalized and normalized not in ordered:
                ordered.append(normalized)
    return ordered


def _try_resolve_any(
    root: Path,
    locators: Sequence[str],
    expected_digest: str,
) -> tuple[_ResolvedBytes | None, str | None]:
    if not locators:
        return None, "locator missing"
    saw_mismatch = False
    saw_utf8 = False
    for locator in locators:
        resolved, reason = _try_resolve(root, locator, expected_digest)
        if resolved is not None:
            return resolved, None
        if reason == "digest mismatch":
            saw_mismatch = True
            continue
        if reason == "not utf-8":
            saw_utf8 = True
            continue
    if saw_mismatch:
        return None, "digest mismatch"
    if saw_utf8:
        return None, "not utf-8"
    return None, "bytes unavailable"


def _ingest_claims(
    *,
    campaign_ids: Sequence[str],
    world_id: str,
) -> list[SourceClaim]:
    wanted = {item.strip() for item in campaign_ids if item.strip()}
    claims: list[SourceClaim] = []
    for run in list_extraction_runs():
        if run.campaign_id not in wanted:
            continue
        component = _component_by_kind(
            run.components,
            ExtractionRunComponentKind.SOURCE_ARTIFACT,
        )
        locator = _normalize_locator(
            component.uri if component is not None else None
        )
        digest = normalize_content_digest(component.sha256) if component is not None else ""
        claims.append(
            SourceClaim(
                source_artifact_id=run.source_artifact_id,
                source_domain=run.source_domain,
                campaign_id=run.campaign_id,
                session_id=run.session_id,
                world_id=world_id,
                expected_sha256=digest or None,
                locator=locator,
                locators=[locator] if locator else [],
                authority_kind="ingest_run",
                supporting_run_ids=[run.run_id],
            )
        )
    return claims


def _world_claims_from_rows(
    rows: Sequence[WorldSourceInventoryRow],
    *,
    campaign_ids: Sequence[str],
    world_id: str,
) -> list[SourceClaim]:
    wanted = {item.strip() for item in campaign_ids if item.strip()}
    claims: list[SourceClaim] = []
    for row in rows:
        if row.world_id not in {world_id, ""} and row.world_id != world_id:
            continue
        if row.campaign_id and row.campaign_id not in wanted:
            continue
        locators = _unique_nonempty(
            [_normalize_locator(row.locator), _normalize_locator(row.artifact_uri)]
        )
        locator = locators[0] if locators else None
        claims.append(
            SourceClaim(
                source_artifact_id=row.source_artifact_id,
                source_domain=row.source_domain or "worldbuilding",
                campaign_id=row.campaign_id,
                session_id=row.session_id,
                world_id=row.world_id or world_id,
                expected_sha256=normalize_content_digest(row.content_sha256 or "") or None,
                locator=locator,
                locators=locators,
                authority_kind="world_source",
                supporting_authority_refs=[
                    ref
                    for ref in (
                        row.source_revision_id,
                        row.artifact_uri,
                    )
                    if ref
                ],
                artifact_kind=row.artifact_kind,
            )
        )
    return claims


def _canonical_domain(domain: str) -> str:
    cleaned = (domain or "").strip()
    return DOMAIN_ALIASES.get(cleaned, cleaned)


def _scope_tuple(claim: SourceClaim) -> tuple[str, str | None, str | None, str | None]:
    return (
        _canonical_domain(claim.source_domain),
        claim.campaign_id,
        claim.session_id,
        claim.world_id,
    )


def _target_scope(
    target: DurableTarget,
) -> tuple[str, str | None, str | None, str | None]:
    return (
        _canonical_domain(target.source_domain),
        target.campaign_id,
        target.session_id,
        target.world_id,
    )


def _scopes_conflict(
    left: tuple[str, str | None, str | None, str | None],
    right: tuple[str, str | None, str | None, str | None],
) -> bool:
    if left[0] != right[0] or left[1] != right[1] or left[2] != right[2]:
        return True
    if left[3] and right[3] and left[3] != right[3]:
        return True
    return False


def _has_conflicting_scopes(
    scopes: Sequence[tuple[str, str | None, str | None, str | None]],
) -> bool:
    for index, left in enumerate(scopes):
        for right in scopes[index + 1 :]:
            if _scopes_conflict(left, right):
                return True
    return False


def _existing_artifact_scopes(artifact_ids: Sequence[str]) -> dict[
    str, tuple[str, str | None, str | None, str | None]
]:
    found: dict[str, tuple[str, str | None, str | None, str | None]] = {}
    unique_ids = list(dict.fromkeys(artifact_ids))
    if not unique_ids:
        return found
    with unit_of_work(load_runtime_dsn()) as conn:
        for artifact_id in unique_ids:
            row = source_repo.get_source_artifact(conn, artifact_id)
            if row is None:
                continue
            found[artifact_id] = (
                _canonical_domain(str(row["source_domain"] or "")),
                row["campaign_id"],
                row["session_id"],
                row["world_id"],
            )
    return found


def _preflight_artifact_scope_conflicts(
    claims: Sequence[SourceClaim],
    targets: Sequence[DurableTarget],
) -> list[DurableTarget]:
    scopes_by_artifact: dict[
        str, list[tuple[str, str | None, str | None, str | None]]
    ] = {}
    for claim in claims:
        scopes_by_artifact.setdefault(claim.source_artifact_id, []).append(
            _scope_tuple(claim)
        )
    for target in targets:
        scopes_by_artifact.setdefault(target.source_artifact_id, []).append(
            _target_scope(target)
        )
    existing = _existing_artifact_scopes(list(scopes_by_artifact))
    for artifact_id, scope in existing.items():
        scopes_by_artifact.setdefault(artifact_id, []).append(scope)
    conflicted = {
        artifact_id
        for artifact_id, scopes in scopes_by_artifact.items()
        if _has_conflicting_scopes(scopes)
    }
    if not conflicted:
        return list(targets)
    marked: list[DurableTarget] = []
    for target in targets:
        if target.source_artifact_id not in conflicted:
            marked.append(target)
            continue
        marked.append(
            target.model_copy(
                update={
                    "classification": "SCOPE_CONFLICT",
                    "markdown": None,
                    "identity_kind": "none",
                    "reason": [
                        "source artifact identity disagrees on domain/campaign/session/world"
                    ],
                }
            )
        )
    return marked


def _merge_claims(claims: Sequence[SourceClaim]) -> list[list[SourceClaim]]:
    grouped: dict[tuple[str, str], list[SourceClaim]] = {}
    incomplete: list[SourceClaim] = []
    for claim in claims:
        digest = normalize_content_digest(claim.expected_sha256 or "")
        if not digest:
            incomplete.append(claim)
            continue
        grouped.setdefault((claim.source_artifact_id, digest), []).append(claim)
    buckets = list(grouped.values())
    for claim in incomplete:
        buckets.append([claim])
    return buckets


def classify_target(
    claims: Sequence[SourceClaim],
    *,
    repo_root: Path,
) -> DurableTarget:
    primary = sorted(
        claims,
        key=lambda claim: 0 if claim.authority_kind == "ingest_run" else 1,
    )[0]
    primary = primary.model_copy(
        update={"source_domain": _canonical_domain(primary.source_domain)}
    )
    supporting_runs = sorted(
        {run_id for claim in claims for run_id in claim.supporting_run_ids}
    )
    supporting_refs = sorted(
        {ref for claim in claims for ref in claim.supporting_authority_refs}
    )
    scopes = [_scope_tuple(claim) for claim in claims]
    locators = _collect_locators(claims)
    locator = locators[0] if locators else None
    artifact_kind = next((claim.artifact_kind for claim in claims if claim.artifact_kind), None)
    digest = normalize_content_digest(primary.expected_sha256 or "")
    base = DurableTarget(
        source_artifact_id=primary.source_artifact_id,
        content_sha256=digest or None,
        source_domain=primary.source_domain,
        campaign_id=primary.campaign_id,
        session_id=primary.session_id,
        world_id=primary.world_id,
        authority_kind=primary.authority_kind,
        locator=locator,
        classification="AUTHORITY_METADATA_INCOMPLETE",
        supporting_run_ids=supporting_runs,
        supporting_authority_refs=supporting_refs,
    )
    if _has_conflicting_scopes(scopes):
        return base.model_copy(
            update={
                "classification": "SCOPE_CONFLICT",
                "reason": ["source artifact identity disagrees on domain/campaign/session/world"],
            }
        )
    if not digest:
        return base.model_copy(
            update={"reason": ["authoritative content digest is missing"]}
        )
    if not any(
        _is_markdown_media(
            artifact_kind=artifact_kind,
            locator=candidate,
            source_domain=primary.source_domain,
        )
        for candidate in (locators or [None])
    ):
        return base.model_copy(
            update={
                "classification": "UNSUPPORTED_MEDIA",
                "reason": ["source is not UTF-8 Markdown"],
            }
        )
    resolved, resolve_reason = _try_resolve_any(repo_root, locators, digest)
    if resolve_reason == "digest mismatch":
        return base.model_copy(
            update={
                "classification": "DIGEST_MISMATCH",
                "reason": ["located bytes do not hash to the authoritative digest"],
            }
        )
    if resolve_reason == "not utf-8":
        return base.model_copy(
            update={
                "classification": "UNSUPPORTED_MEDIA",
                "reason": ["located bytes are not valid UTF-8 Markdown"],
            }
        )
    if resolved is None:
        return base.model_copy(
            update={
                "classification": "UNAVAILABLE_BYTES",
                "locator": locator,
                "reason": [resolve_reason or "exact bytes cannot be found"],
            }
        )
    known = known_historical_revision_id(primary.source_artifact_id, digest)
    known_id = str(known) if known is not None else None
    locator_reason = (
        [f"selected locator among {len(locators)} candidates"]
        if len(locators) > 1
        else []
    )
    if known is not None:
        with unit_of_work(load_runtime_dsn()) as conn:
            by_revision = source_repo.get_source_markdown_by_revision_id(conn, known)
        if by_revision is not None and (
            by_revision.source_artifact_id != primary.source_artifact_id
            or by_revision.content_sha256 != digest
        ):
            return base.model_copy(
                update={
                    "classification": "REVISION_ID_CONFLICT",
                    "known_source_revision_id": str(known),
                    "reason": ["known source_revision_id is already bound to different state"],
                }
            )
    existing = source_service.get_source_markdown(
        source_artifact_id=primary.source_artifact_id,
        content_sha256=digest,
    )
    if existing is not None:
        if existing.markdown != resolved.markdown:
            return base.model_copy(
                update={
                    "classification": "APP_STATE_CONFLICT",
                    "locator": resolved.locator,
                    "reason": ["APP-STATE artifact/digest is bound to different Markdown"],
                }
            )
        try:
            source_service.persist_source_markdown(
                source_artifact_id=primary.source_artifact_id,
                source_domain=primary.source_domain,
                campaign_id=primary.campaign_id,
                session_id=primary.session_id,
                world_id=primary.world_id,
                markdown=resolved.markdown,
                content_sha256=digest,
                source_revision_id=known or existing.source_revision_id,
                dry_run=True,
            )
        except ApplicationStateConflictError as exc:
            code = "REVISION_ID_CONFLICT" if "revision" in str(exc).lower() else "APP_STATE_CONFLICT"
            if "does not match the persisted source" in str(exc) or "different World" in str(exc):
                code = "SCOPE_CONFLICT"
            return base.model_copy(
                update={
                    "classification": code,
                    "locator": resolved.locator,
                    "reason": [str(exc)],
                }
            )
        return base.model_copy(
            update={
                "classification": "CURRENT_EXACT",
                "locator": resolved.locator,
                "markdown": resolved.markdown,
                "known_source_revision_id": known_id,
                "source_revision_id": str(existing.source_revision_id),
                "identity_kind": "current_exact",
                "reason": [
                    "exact artifact+digest already exists in APP-STATE",
                    *locator_reason,
                ],
            }
        )
    return base.model_copy(
        update={
            "classification": "ADOPTABLE_EXACT",
            "locator": resolved.locator,
            "markdown": resolved.markdown,
            "known_source_revision_id": known_id,
            "identity_kind": (
                "historical_uuid_recovered" if known else "new_durable_source_adoption"
            ),
            "reason": [
                "authoritative identity/digest + matching exact bytes",
                *locator_reason,
            ],
        }
    )


def fingerprint_targets(targets: Sequence[DurableTarget]) -> str:
    records = []
    for target in targets:
        historical = known_historical_revision_id(
            target.source_artifact_id,
            target.content_sha256 or "",
        )
        records.append(
            {
                "source_artifact_id": target.source_artifact_id,
                "content_sha256": target.content_sha256 or "",
                "source_domain": target.source_domain,
                "campaign_id": target.campaign_id or "",
                "session_id": target.session_id or "",
                "world_id": target.world_id or "",
                "authority_kind": target.authority_kind,
                "locator": target.locator or "",
                "historical_source_revision_id": str(historical) if historical else "",
            }
        )
    records.sort(key=lambda row: (row["source_artifact_id"], row["content_sha256"], row["authority_kind"]))
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _count(targets: Sequence[DurableTarget]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for target in targets:
        counts[target.classification] = counts.get(target.classification, 0) + 1
    return counts


def observe_world_head(world_id: str) -> str | None:
    for row in list_world_heads():
        if row.world_id == world_id:
            return row.head_revision_id
    return None


def build_inventory(
    *,
    repo_root: Path,
    world_id: str,
    campaign_ids: Sequence[str],
    world_rows: Sequence[WorldSourceInventoryRow] | None = None,
) -> tuple[list[SourceClaim], list[DurableTarget], int]:
    cleaned_campaigns = [item.strip() for item in campaign_ids if item.strip()]
    if not world_id.strip():
        raise SourceAdoptionInputError("world_id is required")
    if not cleaned_campaigns:
        raise SourceAdoptionInputError("at least one campaign is required")
    ingest_claims = _ingest_claims(campaign_ids=cleaned_campaigns, world_id=world_id)
    if world_rows is None:
        world_rows = list_world_textual_source_inventory(world_id=world_id)
    world_claims = _world_claims_from_rows(
        world_rows,
        campaign_ids=cleaned_campaigns,
        world_id=world_id,
    )
    claims = ingest_claims + world_claims
    targets = [
        classify_target(bucket, repo_root=repo_root)
        for bucket in _merge_claims(claims)
    ]
    targets = _preflight_artifact_scope_conflicts(claims, targets)
    targets.sort(key=lambda row: (row.source_artifact_id, row.content_sha256 or ""))
    return claims, targets, _ingest_run_count(campaign_ids)


def _ingest_run_count(campaign_ids: Sequence[str]) -> int:
    wanted = {item.strip() for item in campaign_ids if item.strip()}
    return sum(1 for run in list_extraction_runs() if run.campaign_id in wanted)


def preview_source_adoption(
    *,
    repo_root: Path,
    world_id: str,
    campaign_ids: Sequence[str],
    world_rows: Sequence[WorldSourceInventoryRow] | None = None,
    world_head: str | None = None,
) -> SourceAdoptionReport:
    claims, targets, _ = build_inventory(
        repo_root=repo_root,
        world_id=world_id,
        campaign_ids=campaign_ids,
        world_rows=world_rows,
    )
    observed_head = world_head if world_head is not None else observe_world_head(world_id)
    counts = _count(targets)
    blocked = any(target.classification in BLOCKING_CLASSIFICATIONS for target in targets)
    return SourceAdoptionReport(
        generated_at=_utc_now(),
        mode="preview",
        blocked=blocked,
        world_id=world_id,
        campaign_ids=[item.strip() for item in campaign_ids if item.strip()],
        world_head=observed_head,
        ingest_run_count=_ingest_run_count(campaign_ids),
        claim_count=len(claims),
        target_count=len(targets),
        source_target_set_sha256=fingerprint_targets(targets),
        counts=counts,
        targets=targets,
        skipped=sum(counts.get(name, 0) for name in SKIP_CLASSIFICATIONS),
        noop=counts.get("CURRENT_EXACT", 0),
    )


def apply_source_adoption(
    *,
    repo_root: Path,
    world_id: str,
    campaign_ids: Sequence[str],
    expected_set_sha256: str,
    expected_world_head: str | None = None,
    world_rows: Sequence[WorldSourceInventoryRow] | None = None,
    world_head: str | None = None,
) -> SourceAdoptionReport:
    if not expected_set_sha256 or not expected_set_sha256.strip():
        raise SourceAdoptionInputError("--expected-set-sha256 is required with --apply")
    if expected_world_head is None or not str(expected_world_head).strip():
        raise SourceAdoptionInputError("--expected-world-head is required with --apply")
    preview = preview_source_adoption(
        repo_root=repo_root,
        world_id=world_id,
        campaign_ids=campaign_ids,
        world_rows=world_rows,
        world_head=world_head,
    )
    observed_head = preview.world_head
    pinned_head = expected_world_head.strip()
    if observed_head != pinned_head:
        preview.blocked = True
        preview.applied = False
        preview.detail = "blocked: World head drifted from the preview value"
        return preview
    if preview.source_target_set_sha256 != expected_set_sha256.strip():
        preview.blocked = True
        preview.applied = False
        preview.detail = "blocked: recomputed source_target_set_sha256 does not match --expected-set-sha256"
        return preview
    if preview.blocked:
        preview.detail = preview.detail or "blocked: blocking classification present"
        return preview

    adoptable = [
        target for target in preview.targets if target.classification == "ADOPTABLE_EXACT"
    ]
    try:
        for target in adoptable:
            source_service.persist_source_markdown(
                source_artifact_id=target.source_artifact_id,
                source_domain=target.source_domain,
                campaign_id=target.campaign_id,
                session_id=target.session_id,
                world_id=target.world_id,
                markdown=target.markdown or "",
                content_sha256=target.content_sha256,
                source_revision_id=(
                    UUID(target.known_source_revision_id)
                    if target.known_source_revision_id
                    else None
                ),
                dry_run=True,
            )
    except (ApplicationStateConflictError, ApplicationStateValidationError) as exc:
        preview.blocked = True
        preview.applied = False
        preview.detail = f"blocked: persist preflight failed before any write: {exc}"
        return preview

    newly_adopted = 0
    new_identities = 0
    applied_targets: list[DurableTarget] = []
    for target in preview.targets:
        if target.classification != "ADOPTABLE_EXACT":
            applied_targets.append(target)
            continue
        known = (
            UUID(target.known_source_revision_id)
            if target.known_source_revision_id
            else None
        )
        lineage = {
            "adoption_kind": (
                "historical_uuid_recovery"
                if known is not None
                else "new_durable_source_adoption"
            ),
            "adopted_from_run_ids": target.supporting_run_ids,
            "adopted_from_authority_refs": target.supporting_authority_refs,
            "adopted_from_uri": target.locator,
            "historical_buddy_revision_id_recovered": known is not None,
        }
        record = source_service.persist_source_markdown(
            source_artifact_id=target.source_artifact_id,
            source_domain=target.source_domain,
            campaign_id=target.campaign_id,
            session_id=target.session_id,
            world_id=target.world_id,
            markdown=target.markdown or "",
            content_sha256=target.content_sha256,
            lineage=lineage,
            source_revision_id=known,
        )
        newly_adopted += 1
        if known is None:
            new_identities += 1
        applied_targets.append(
            target.model_copy(
                update={
                    "source_revision_id": str(record.source_revision_id),
                    "wrote": True,
                    "identity_kind": (
                        "historical_uuid_recovered"
                        if known is not None
                        else "new_durable_source_adoption"
                    ),
                }
            )
        )
    return SourceAdoptionReport(
        generated_at=_utc_now(),
        mode="apply",
        blocked=False,
        applied=True,
        world_id=world_id,
        campaign_ids=preview.campaign_ids,
        world_head=observed_head,
        ingest_run_count=preview.ingest_run_count,
        claim_count=preview.claim_count,
        target_count=len(applied_targets),
        source_target_set_sha256=preview.source_target_set_sha256,
        counts=_count(applied_targets),
        targets=applied_targets,
        newly_adopted=newly_adopted,
        noop=preview.noop,
        skipped=preview.skipped,
        new_durable_identities=new_identities,
    )
