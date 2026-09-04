"""Read-only historical product continuity inventory (DFC-1).

Compares explicitly supplied historical roots against current product authorities
by exact durable identity only. Never migrates or writes product state.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from application_state.config import APPLICATION_STATE_DSN_ENV, load_runtime_dsn
from application_state.content.service import (
    exact_committed_revision,
    list_plans,
    list_runbooks,
    snapshot_plan,
    snapshot_runbook,
)
from application_state.content.types import sha256_utf8
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateMigrationError,
    ApplicationStateNotFoundError,
    ApplicationStateUnavailableError,
)
from application_state.ingest.import_legacy import read_legacy_extraction_runs
from application_state.ingest.service import list_extraction_runs
from application_state.play.service import list_play_run_aggregates
from apps.live_control_server.services.play_run_registry import PlayRunRecord
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryDocument,
    list_workspace_documents,
    workspace_documents_path,
)
from graph_memory.ingestion.extraction_run import ExtractionRun
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestRunManifest,
    adapt_recap_manifest_to_extraction_run,
)
from live_play.live_store import load_json

INVENTORY_SCHEMA = "dmb_product_continuity_inventory_v1"

Domain = Literal["plan", "build", "ingest", "runbook", "play_run"]
IdentityKind = Literal["document_id", "run_id"]
Classification = Literal[
    "CURRENT_EXACT",
    "CURRENT_CONTAINS_HISTORY",
    "RECOVERABLE_EXACT",
    "NEEDS_ADAPTER",
    "ORPHAN_EVIDENCE",
    "CONFLICT",
    "MALFORMED",
    "COMPARISON_UNAVAILABLE",
]
ParseStatus = Literal["ok", "malformed", "adapted", "adapt_failed"]
AuthorityStatus = Literal[
    "readable",
    "unavailable",
    "present",
    "absent",
    "contains_history",
    "conflict",
    "not_applicable",
]

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_CLASSIFICATION_ORDER = {
    "CONFLICT": 0,
    "MALFORMED": 1,
    "COMPARISON_UNAVAILABLE": 2,
    "NEEDS_ADAPTER": 3,
    "ORPHAN_EVIDENCE": 4,
    "RECOVERABLE_EXACT": 5,
    "CURRENT_CONTAINS_HISTORY": 6,
    "CURRENT_EXACT": 7,
}


class HistoricalObservation(BaseModel):
    source_kind: str
    root_label: str
    relative_locator: str
    claimed_revision: int | None = None
    content_sha256: str | None = None
    durable_fingerprint: str | None = None
    parse_status: ParseStatus
    detail: str | None = None


class CurrentAuthorityView(BaseModel):
    status: AuthorityStatus
    matching_revision: int | None = None
    matching_content_sha256: str | None = None
    head_revision: int | None = None
    product_discoverable: bool = False
    detail: str | None = None


class LedgerItem(BaseModel):
    domain: Domain
    identity_kind: IdentityKind
    identity: str
    campaign_id: str | None = None
    session_id: str | None = None
    title: str | None = None
    historical_observations: list[HistoricalObservation] = Field(default_factory=list)
    current_authority: CurrentAuthorityView
    classification: Classification
    reason: list[str] = Field(default_factory=list)


class AuthorityCoordinates(BaseModel):
    app_state_configured: bool
    app_state_readable: bool
    host: str | None = None
    port: int | None = None
    database_name: str | None = None
    schema_head_status: str | None = None
    current_repo_root: str
    current_build_registry_locator: str
    detail: str | None = None


class InventoryReport(BaseModel):
    schema_version: Literal["dmb_product_continuity_inventory_v1"] = INVENTORY_SCHEMA
    generated_at: str
    authority: AuthorityCoordinates
    historical_roots: list[dict[str, str]] = Field(default_factory=list)
    items: list[LedgerItem] = Field(default_factory=list)
    classification_counts: dict[str, int] = Field(default_factory=dict)
    domain_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    incomplete: bool = False


@dataclass
class _PendingObs:
    domain: Domain
    identity_kind: IdentityKind
    identity: str
    campaign_id: str | None = None
    session_id: str | None = None
    title: str | None = None
    content_status: str | None = None
    observation: HistoricalObservation | None = None
    # For ingest adapted runs: durable payload fingerprint of adapted ExtractionRun
    adapted_fingerprint: str | None = None
    play_binding: dict[str, Any] | None = None


@dataclass
class CurrentAuthoritySnapshot:
    readable: bool
    detail: str | None
    schema_head_status: str | None
    plans: dict[str, Any] = field(default_factory=dict)
    runbooks: dict[str, Any] = field(default_factory=dict)
    builds: dict[str, Any] = field(default_factory=dict)
    builds_readable: bool = True
    builds_detail: str | None = None
    ingest: dict[str, Any] = field(default_factory=dict)
    play_runs: dict[str, Any] = field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _is_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value.strip()))


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _file_sha256(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return sha256_utf8(text)


def _durable_run_fingerprint(run: ExtractionRun) -> str:
    payload = json.dumps(run.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _play_fingerprint(record: PlayRunRecord) -> str:
    payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sanitize_authority_coordinates(
    *,
    current_repo_root: Path,
    readable: bool,
    schema_head_status: str | None,
    detail: str | None = None,
) -> AuthorityCoordinates:
    import os

    raw = os.environ.get(APPLICATION_STATE_DSN_ENV, "").strip()
    configured = bool(raw)
    host = port = db = None
    if configured:
        parsed = urlparse(raw)
        host = parsed.hostname
        port = parsed.port
        db = (parsed.path or "").lstrip("/") or None
    registry = workspace_documents_path(current_repo_root)
    return AuthorityCoordinates(
        app_state_configured=configured,
        app_state_readable=readable,
        host=host,
        port=port,
        database_name=db,
        schema_head_status=schema_head_status,
        current_repo_root=str(current_repo_root.resolve()),
        current_build_registry_locator=_rel(current_repo_root, registry)
        if registry.is_relative_to(current_repo_root.resolve())
        else registry.as_posix(),
        detail=detail,
    )


def observe_current_authority(current_repo_root: Path) -> CurrentAuthoritySnapshot:
    """Observe current product seams. Never writes."""
    builds, builds_readable, builds_detail = _load_current_builds(current_repo_root)

    try:
        load_runtime_dsn()
    except ApplicationStateUnavailableError as exc:
        return CurrentAuthoritySnapshot(
            readable=False,
            detail=str(exc),
            schema_head_status="unavailable",
            builds=builds,
            builds_readable=builds_readable,
            builds_detail=builds_detail,
        )

    try:
        plans = {
            str(obj.work_object_id): {
                "object_revision": obj.object_revision,
                "campaign_id": obj.campaign_id,
                "title": obj.title,
                "status": obj.status,
            }
            for obj in list_plans(status=None)
        }
        runbooks = {
            str(obj.work_object_id): {
                "object_revision": obj.object_revision,
                "campaign_id": obj.campaign_id,
                "title": obj.title,
                "status": obj.status,
            }
            for obj in list_runbooks(status=None)
        }
        ingest = {
            run.run_id: {
                "fingerprint": _durable_run_fingerprint(run),
                "campaign_id": run.campaign_id,
                "session_id": run.session_id,
                "revision": run.revision,
                "source_artifact_id": run.source_artifact_id,
                "status": str(run.status),
            }
            for run in list_extraction_runs()
        }
        play_runs: dict[str, Any] = {}
        for agg in list_play_run_aggregates():
            run_id = str(agg.run.run_id)
            play_runs[run_id] = {
                "campaign_id": agg.run.campaign_id,
                "playable_artifact_id": str(agg.run.playable_work_object_id),
                "playable_revision": agg.run.playable_revision_n,
                "playable_content_sha256": agg.run.playable_content_sha256,
                "run_revision": agg.run.run_revision,
            }
        return CurrentAuthoritySnapshot(
            readable=True,
            detail=None,
            schema_head_status="at_head",
            plans=plans,
            runbooks=runbooks,
            builds=builds,
            builds_readable=builds_readable,
            builds_detail=builds_detail,
            ingest=ingest,
            play_runs=play_runs,
        )
    except ApplicationStateMigrationError as exc:
        return CurrentAuthoritySnapshot(
            readable=False,
            detail=str(exc),
            schema_head_status="behind_head",
            builds=builds,
            builds_readable=builds_readable,
            builds_detail=builds_detail,
        )
    except ApplicationStateUnavailableError as exc:
        return CurrentAuthoritySnapshot(
            readable=False,
            detail=str(exc),
            schema_head_status="unavailable",
            builds=builds,
            builds_readable=builds_readable,
            builds_detail=builds_detail,
        )
    except ApplicationStateIntegrityError as exc:
        return CurrentAuthoritySnapshot(
            readable=False,
            detail=str(exc),
            schema_head_status="integrity_error",
            builds=builds,
            builds_readable=builds_readable,
            builds_detail=builds_detail,
        )


def _load_current_builds(
    current_repo_root: Path,
) -> tuple[dict[str, Any], bool, str | None]:
    """Build worldbuilding_source remains file-registry authority.

    Returns (builds, readable, detail). A missing registry file is an
    authoritatively empty registry. A present but unreadable/malformed
    registry is not readable and must not collapse to empty.
    """
    path = workspace_documents_path(current_repo_root)
    if not path.is_file():
        return {}, True, None

    try:
        records = list_workspace_documents(
            current_repo_root, kind="worldbuilding_source", status=None
        )
    except Exception as product_exc:
        try:
            doc = WorkspaceDocumentRegistryDocument.model_validate(load_json(path))
        except Exception as parse_exc:
            return (
                {},
                False,
                (
                    "current Build workspace registry is unreadable: "
                    f"product_seam={product_exc}; parse={parse_exc}"
                ),
            )
        records = [r for r in doc.records if r.kind == "worldbuilding_source"]

    out: dict[str, Any] = {}
    for record in records:
        digest = None
        if record.target_relpath:
            target = current_repo_root / record.target_relpath
            if target.is_file():
                digest = _file_sha256(target)
        out[record.document_id] = {
            "revision": record.revision,
            "campaign_id": record.campaign_id,
            "title": record.title,
            "content_sha256": digest,
            "target_relpath": record.target_relpath,
            "content_status": record.content_status,
        }
    return out, True, None

def _scan_workspace_registry(root: Path, root_label: str) -> list[_PendingObs]:
    pending: list[_PendingObs] = []
    path = workspace_documents_path(root)
    if not path.is_file():
        return pending
    locator = _rel(root, path)
    try:
        raw = load_json(path)
        doc = WorkspaceDocumentRegistryDocument.model_validate(raw)
    except Exception as exc:
        pending.append(
            _PendingObs(
                domain="plan",
                identity_kind="document_id",
                identity=f"malformed-registry:{root_label}",
                observation=HistoricalObservation(
                    source_kind="workspace_documents_registry",
                    root_label=root_label,
                    relative_locator=locator,
                    parse_status="malformed",
                    detail=str(exc),
                ),
            )
        )
        return pending

    for record in doc.records:
        domain: Domain | None
        if record.kind == "plan":
            domain = "plan"
        elif record.kind == "runbook":
            domain = "runbook"
        elif record.kind == "worldbuilding_source":
            domain = "build"
        else:
            continue
        digest = None
        if record.target_relpath:
            target = root / record.target_relpath
            if target.is_file():
                digest = _file_sha256(target)
        pending.append(
            _PendingObs(
                domain=domain,
                identity_kind="document_id",
                identity=record.document_id,
                campaign_id=record.campaign_id,
                title=record.title,
                content_status=record.content_status,
                observation=HistoricalObservation(
                    source_kind="workspace_documents_registry",
                    root_label=root_label,
                    relative_locator=locator,
                    claimed_revision=record.revision,
                    content_sha256=digest,
                    durable_fingerprint=digest,
                    parse_status="ok",
                    detail=f"kind={record.kind}; content_status={record.content_status}",
                ),
            )
        )
    return pending


def _scan_extraction_runs_registry(root: Path, root_label: str) -> list[_PendingObs]:
    pending: list[_PendingObs] = []
    path = root / "out/registries/extraction_runs.json"
    if not path.is_file():
        return pending
    locator = _rel(root, path)
    try:
        runs = read_legacy_extraction_runs(root)
    except Exception as exc:
        pending.append(
            _PendingObs(
                domain="ingest",
                identity_kind="run_id",
                identity=f"malformed-extraction-registry:{root_label}",
                observation=HistoricalObservation(
                    source_kind="extraction_runs_registry",
                    root_label=root_label,
                    relative_locator=locator,
                    parse_status="malformed",
                    detail=str(exc),
                ),
            )
        )
        return pending
    for run in runs:
        pending.append(
            _PendingObs(
                domain="ingest",
                identity_kind="run_id",
                identity=run.run_id,
                campaign_id=run.campaign_id,
                session_id=run.session_id,
                adapted_fingerprint=_durable_run_fingerprint(run),
                observation=HistoricalObservation(
                    source_kind="extraction_runs_registry",
                    root_label=root_label,
                    relative_locator=locator,
                    claimed_revision=run.revision,
                    durable_fingerprint=_durable_run_fingerprint(run),
                    parse_status="ok",
                    detail=f"source_artifact_id={run.source_artifact_id}",
                ),
            )
        )
    return pending


def _scan_manifests(root: Path, root_label: str) -> list[_PendingObs]:
    pending: list[_PendingObs] = []
    patterns = [
        "out/graph_memory/runs/**/graph_ingest_run_manifest.json",
        "evals/graph_memory_layer/artifacts/graph_ingest_runs/**/graph_ingest_run_manifest.json",
    ]
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            locator = _rel(root, path)
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                manifest = GraphIngestRunManifest.model_validate(raw)
            except Exception as exc:
                pending.append(
                    _PendingObs(
                        domain="ingest",
                        identity_kind="run_id",
                        identity=f"malformed-manifest:{locator}",
                        observation=HistoricalObservation(
                            source_kind="graph_ingest_run_manifest",
                            root_label=root_label,
                            relative_locator=locator,
                            parse_status="malformed",
                            detail=str(exc),
                        ),
                    )
                )
                continue
            try:
                adapted = adapt_recap_manifest_to_extraction_run(manifest)
            except ValueError as exc:
                pending.append(
                    _PendingObs(
                        domain="ingest",
                        identity_kind="run_id",
                        identity=manifest.run_id or f"orphan-manifest:{locator}",
                        campaign_id=manifest.campaign_id,
                        session_id=manifest.session_id,
                        observation=HistoricalObservation(
                            source_kind="graph_ingest_run_manifest",
                            root_label=root_label,
                            relative_locator=locator,
                            parse_status="adapt_failed",
                            detail=str(exc),
                        ),
                    )
                )
                continue
            pending.append(
                _PendingObs(
                    domain="ingest",
                    identity_kind="run_id",
                    identity=adapted.run_id,
                    campaign_id=adapted.campaign_id,
                    session_id=adapted.session_id,
                    adapted_fingerprint=_durable_run_fingerprint(adapted),
                    observation=HistoricalObservation(
                        source_kind="graph_ingest_run_manifest",
                        root_label=root_label,
                        relative_locator=locator,
                        claimed_revision=adapted.revision,
                        durable_fingerprint=_durable_run_fingerprint(adapted),
                        parse_status="adapted",
                        detail=f"source_artifact_id={adapted.source_artifact_id}",
                    ),
                )
            )
    return pending


def _scan_play_runs(root: Path, root_label: str) -> list[_PendingObs]:
    pending: list[_PendingObs] = []
    runs_dir = root / "out/runtime/play/runs"
    if not runs_dir.is_dir():
        return pending
    for path in sorted(runs_dir.glob("*.json")):
        locator = _rel(root, path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record = PlayRunRecord.model_validate(raw)
        except Exception as exc:
            pending.append(
                _PendingObs(
                    domain="play_run",
                    identity_kind="run_id",
                    identity=f"malformed-play-run:{locator}",
                    observation=HistoricalObservation(
                        source_kind="legacy_play_run",
                        root_label=root_label,
                        relative_locator=locator,
                        parse_status="malformed",
                        detail=str(exc),
                    ),
                )
            )
            continue
        pending.append(
            _PendingObs(
                domain="play_run",
                identity_kind="run_id",
                identity=record.run_id,
                campaign_id=record.campaign_id,
                play_binding={
                    "playable_artifact_id": record.playable_artifact_id,
                    "playable_revision": record.playable_revision,
                    "playable_content_sha256": record.playable_content_sha256,
                    "run_revision": record.run_revision,
                },
                observation=HistoricalObservation(
                    source_kind="legacy_play_run",
                    root_label=root_label,
                    relative_locator=locator,
                    claimed_revision=record.run_revision,
                    content_sha256=record.playable_content_sha256,
                    durable_fingerprint=_play_fingerprint(record),
                    parse_status="ok",
                ),
            )
        )
    return pending


def _scan_orphan_bytes(root: Path, root_label: str) -> list[_PendingObs]:
    pending: list[_PendingObs] = []
    candidates: list[tuple[Domain, Path]] = []
    for path in (root / "out/workspace/plan").glob("*.md") if (root / "out/workspace/plan").is_dir() else []:
        candidates.append(("plan", path))
    for path in (
        (root / "out/workspace/worldbuilding").glob("*.md")
        if (root / "out/workspace/worldbuilding").is_dir()
        else []
    ):
        candidates.append(("build", path))
    for path in root.glob("corpus/*-markdown/_dungeonbuddy/sources/*/source.md"):
        candidates.append(("build", path))

    for domain, path in candidates:
        stem = path.stem if path.name != "source.md" else path.parent.name
        if not _is_uuid(stem):
            pending.append(
                _PendingObs(
                    domain=domain,
                    identity_kind="document_id",
                    identity=f"orphan-bytes:{_rel(root, path)}",
                    observation=HistoricalObservation(
                        source_kind="orphan_bytes",
                        root_label=root_label,
                        relative_locator=_rel(root, path),
                        content_sha256=_file_sha256(path),
                        parse_status="ok",
                        detail="filename lacks admitted embedded UUID",
                    ),
                )
            )
            continue
        pending.append(
            _PendingObs(
                domain=domain,
                identity_kind="document_id",
                identity=stem,
                observation=HistoricalObservation(
                    source_kind="orphan_bytes",
                    root_label=root_label,
                    relative_locator=_rel(root, path),
                    content_sha256=_file_sha256(path),
                    durable_fingerprint=_file_sha256(path),
                    parse_status="ok",
                ),
            )
        )
    return pending


def scan_historical_root(root: Path, *, root_label: str) -> list[_PendingObs]:
    if not root.is_dir():
        raise FileNotFoundError(f"historical root is not a directory: {root}")
    pending: list[_PendingObs] = []
    pending.extend(_scan_workspace_registry(root, root_label))
    pending.extend(_scan_extraction_runs_registry(root, root_label))
    pending.extend(_scan_manifests(root, root_label))
    pending.extend(_scan_play_runs(root, root_label))
    pending.extend(_scan_orphan_bytes(root, root_label))
    return pending


def _obs_digest(obs: HistoricalObservation) -> str | None:
    """Return the durable content digest used for historical equivalence."""
    return obs.content_sha256 or obs.durable_fingerprint


def _merge_group(pendings: list[_PendingObs]) -> tuple[list[HistoricalObservation], list[str], bool]:
    """Return observations, reasons, and whether same-ID historical conflict exists.

    Registry + orphan-bytes observations for the same UUID are complementary when
    their digests agree (or one side lacks a digest). Disagreement requires
    distinct non-empty digests or incompatible claimed revisions with digests.
    """
    observations = [p.observation for p in pendings if p.observation is not None]
    reasons: list[str] = []
    ok_obs = [o for o in observations if o.parse_status in {"ok", "adapted"}]
    digests = {d for o in ok_obs if (d := _obs_digest(o))}
    conflict = False
    if len(digests) > 1:
        conflict = True
        reasons.append(
            "same durable identity disagrees across historical observations "
            "(content digest mismatch)"
        )
    else:
        # Digests agree or are absent — claimed_revision alone does not conflict
        # when digests match (orphan bytes lack revision claims).
        rev_pairs = {
            (o.claimed_revision, _obs_digest(o))
            for o in ok_obs
            if o.claimed_revision is not None and _obs_digest(o)
        }
        by_rev: dict[int, set[str]] = defaultdict(set)
        for rev, digest in rev_pairs:
            if digest:
                by_rev[rev].add(digest)
        for rev, digest_set in by_rev.items():
            if len(digest_set) > 1:
                conflict = True
                reasons.append(
                    f"same claimed revision {rev} disagrees on content digest "
                    "across historical observations"
                )
                break
    return observations, reasons, conflict


def _sufficient_plan_runbook_recoverable(
    *,
    has_registry_record: bool,
    claimed_revision: int | None,
    content_sha256: str | None,
    content_status: str | None,
) -> bool:
    """True when evidence is enough to design idempotent exact Plan/Runbook adoption."""
    if not has_registry_record or claimed_revision is None:
        return False
    if content_sha256:
        return True
    # Non-committed drafts may legitimately lack target bytes.
    return bool(content_status) and content_status != "committed"


def _sufficient_build_recoverable(
    *,
    has_registry_record: bool,
    content_sha256: str | None,
) -> bool:
    """Build recovery needs registry metadata plus recoverable bytes."""
    return has_registry_record and bool(content_sha256)


def _probe_plan_runbook_head_digest(
    *, domain: Domain, identity: str
) -> tuple[str | None, str | None]:
    """Return (digest, failure_kind) where failure_kind is unavailable|missing|None."""
    try:
        snap = snapshot_plan(identity) if domain == "plan" else snapshot_runbook(identity)
        return snap.content_sha256, None
    except ApplicationStateNotFoundError:
        return None, "missing"
    except ApplicationStateIntegrityError:
        return None, "unavailable"
    except Exception:
        return None, "unavailable"


def _classify_plan_or_runbook(
    *,
    domain: Domain,
    identity: str,
    claimed_revision: int | None,
    content_sha256: str | None,
    content_status: str | None,
    has_registry_record: bool,
    current: CurrentAuthoritySnapshot,
    historical_conflict: bool,
    has_malformed_only: bool,
    adapt_failed: bool,
) -> tuple[Classification, CurrentAuthorityView, list[str]]:
    reasons: list[str] = []
    if has_malformed_only:
        return (
            "MALFORMED",
            CurrentAuthorityView(status="not_applicable", product_discoverable=False),
            ["historical artifact failed admitted schema parse"],
        )
    if adapt_failed and domain == "ingest":
        return (
            "NEEDS_ADAPTER",
            CurrentAuthorityView(status="not_applicable", product_discoverable=False),
            ["manifest adaptation failed; refusing to invent identity fields"],
        )
    if identity.startswith("orphan-bytes:") or identity.startswith("malformed-"):
        return (
            "ORPHAN_EVIDENCE" if identity.startswith("orphan-bytes:") else "MALFORMED",
            CurrentAuthorityView(status="not_applicable", product_discoverable=False),
            ["no safe exact product identity from admitted metadata"],
        )

    table = current.plans if domain == "plan" else current.runbooks
    if domain == "build":
        table = current.builds
        if not current.builds_readable:
            if historical_conflict:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(status="conflict", product_discoverable=False),
                    reasons or ["historical observations disagree"],
                )
            return (
                "COMPARISON_UNAVAILABLE",
                CurrentAuthorityView(
                    status="unavailable",
                    product_discoverable=False,
                    detail=current.builds_detail,
                ),
                [
                    "current Build workspace registry is not authoritatively readable",
                    *( [current.builds_detail] if current.builds_detail else [] ),
                ],
            )

    # Unavailable APP-STATE must win over recoverability claims. Historical
    # same-ID conflicts remain CONFLICT even when APP-STATE is down.
    if domain in {"plan", "runbook"} and not current.readable:
        if historical_conflict:
            return (
                "CONFLICT",
                CurrentAuthorityView(status="conflict", product_discoverable=False),
                reasons or ["historical observations disagree"],
            )
        return (
            "COMPARISON_UNAVAILABLE",
            CurrentAuthorityView(
                status="unavailable",
                product_discoverable=False,
                detail=current.detail,
            ),
            ["current APP-STATE authority is not authoritatively readable"],
        )

    if historical_conflict:
        return (
            "CONFLICT",
            CurrentAuthorityView(status="conflict", product_discoverable=False),
            reasons or ["historical observations disagree"],
        )

    present = table.get(identity)
    if present is None:
        if domain == "build":
            if _sufficient_build_recoverable(
                has_registry_record=has_registry_record,
                content_sha256=content_sha256,
            ):
                return (
                    "RECOVERABLE_EXACT",
                    CurrentAuthorityView(status="absent", product_discoverable=False),
                    [
                        "exact Build identity absent from current workspace registry",
                        "registry metadata plus recoverable bytes are sufficient for a later exact adoption design",
                    ],
                )
            return (
                "NEEDS_ADAPTER",
                CurrentAuthorityView(status="absent", product_discoverable=False),
                [
                    "Build identity/evidence is incomplete for exact adoption "
                    "(need registry metadata and recoverable bytes; orphan bytes alone are insufficient)"
                    if not has_registry_record
                    else "Build registry identity survives without recoverable bytes; "
                    "exact adoption path needs an adaptor/recovery slice"
                ],
            )
        if _sufficient_plan_runbook_recoverable(
            has_registry_record=has_registry_record,
            claimed_revision=claimed_revision,
            content_sha256=content_sha256,
            content_status=content_status,
        ):
            return (
                "RECOVERABLE_EXACT",
                CurrentAuthorityView(status="absent", product_discoverable=False),
                [
                    f"exact {domain} identity absent from readable APP-STATE",
                    "registry metadata plus recoverable bytes/durable fields are sufficient for existing exact importer design",
                ],
            )
        return (
            "NEEDS_ADAPTER",
            CurrentAuthorityView(status="absent", product_discoverable=False),
            [
                f"exact {domain} identity known but durable adoption evidence is incomplete "
                "(UUID-bearing orphan bytes or registry row without required bytes/metadata "
                "cannot drive the existing exact importer alone)"
            ],
        )

    head_rev = present.get("object_revision") or present.get("revision")
    head_digest = present.get("content_sha256")

    if domain in {"plan", "runbook"} and claimed_revision is not None:
        # Honor claimed revision even when historical target bytes/digest are absent.
        evidence_label = (
            "revision/content" if content_sha256 else "claimed revision (no historical digest)"
        )
        if head_rev is not None and claimed_revision > head_rev:
            return (
                "CONFLICT",
                CurrentAuthorityView(
                    status="conflict",
                    head_revision=head_rev,
                    product_discoverable=True,
                ),
                [
                    "historical claimed revision is ahead of current head; "
                    "exact revision cannot be represented by current authority"
                ],
            )
        if head_rev == claimed_revision:
            try:
                committed = exact_committed_revision(
                    identity,
                    claimed_revision,
                    kind=domain,  # type: ignore[arg-type]
                    expected_sha256=content_sha256,
                )
                return (
                    "CURRENT_EXACT",
                    CurrentAuthorityView(
                        status="present",
                        matching_revision=committed.work_revision.revision_n,
                        matching_content_sha256=(
                            content_sha256 or committed.work_revision.content_sha256
                        ),
                        head_revision=head_rev,
                        product_discoverable=True,
                    ),
                    [f"exact identity and {evidence_label} already in APP-STATE"],
                )
            except ApplicationStateNotFoundError:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(
                        status="conflict",
                        head_revision=head_rev,
                        product_discoverable=True,
                    ),
                    [
                        "current object revision matches claim but historical "
                        "revision is not retained as claimed"
                    ],
                )
            except ApplicationStateConflictError as exc:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(
                        status="conflict",
                        head_revision=head_rev,
                        product_discoverable=True,
                        detail=str(exc),
                    ),
                    [f"same claimed revision disagrees with current retained content: {exc}"],
                )
            except ApplicationStateIntegrityError as exc:
                return (
                    "COMPARISON_UNAVAILABLE",
                    CurrentAuthorityView(
                        status="unavailable",
                        head_revision=head_rev,
                        product_discoverable=True,
                        detail=str(exc),
                    ),
                    [f"APP-STATE integrity failure while verifying exact revision: {exc}"],
                )
            except Exception as exc:
                return (
                    "COMPARISON_UNAVAILABLE",
                    CurrentAuthorityView(
                        status="unavailable",
                        head_revision=head_rev,
                        product_discoverable=True,
                        detail=str(exc),
                    ),
                    [f"could not authoritatively verify exact {evidence_label}: {exc}"],
                )
        if head_rev is not None and claimed_revision < head_rev:
            try:
                committed = exact_committed_revision(
                    identity,
                    claimed_revision,
                    kind=domain,  # type: ignore[arg-type]
                    expected_sha256=content_sha256,
                )
                return (
                    "CURRENT_CONTAINS_HISTORY",
                    CurrentAuthorityView(
                        status="contains_history",
                        matching_revision=committed.work_revision.revision_n,
                        matching_content_sha256=(
                            content_sha256 or committed.work_revision.content_sha256
                        ),
                        head_revision=head_rev,
                        product_discoverable=True,
                    ),
                    [
                        "current head advanced but exact historical "
                        f"{evidence_label} is preserved in APP-STATE history"
                    ],
                )
            except ApplicationStateNotFoundError:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(
                        status="conflict",
                        head_revision=head_rev,
                        product_discoverable=True,
                    ),
                    [
                        "same identity exists but historical claimed revision "
                        "is not retained in APP-STATE history"
                    ],
                )
            except ApplicationStateConflictError as exc:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(
                        status="conflict",
                        head_revision=head_rev,
                        product_discoverable=True,
                        detail=str(exc),
                    ),
                    [
                        "historical claimed revision exists but disagrees with "
                        f"retained content digest: {exc}"
                    ],
                )
            except ApplicationStateIntegrityError as exc:
                return (
                    "COMPARISON_UNAVAILABLE",
                    CurrentAuthorityView(
                        status="unavailable",
                        head_revision=head_rev,
                        product_discoverable=True,
                        detail=str(exc),
                    ),
                    [f"APP-STATE integrity failure while verifying preserved history: {exc}"],
                )
            except Exception as exc:
                return (
                    "COMPARISON_UNAVAILABLE",
                    CurrentAuthorityView(
                        status="unavailable",
                        head_revision=head_rev,
                        product_discoverable=True,
                        detail=str(exc),
                    ),
                    [f"could not verify preserved historical revision: {exc}"],
                )

    if domain == "build":
        if content_sha256:
            if head_digest is None:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(
                        status="conflict",
                        matching_revision=head_rev,
                        product_discoverable=True,
                    ),
                    [
                        "current Build identity is present but lacks bytes for exact "
                        "content proof against historical digest"
                    ],
                )
            if head_digest != content_sha256:
                return (
                    "CONFLICT",
                    CurrentAuthorityView(
                        status="conflict",
                        matching_revision=head_rev,
                        matching_content_sha256=head_digest,
                        product_discoverable=True,
                    ),
                    ["Build registry same identity with disagreeing digest"],
                )
            return (
                "CURRENT_EXACT",
                CurrentAuthorityView(
                    status="present",
                    matching_revision=head_rev,
                    matching_content_sha256=head_digest,
                    product_discoverable=True,
                ),
                ["exact Build identity and content digest present in current registry"],
            )
        if claimed_revision is not None and head_rev == claimed_revision:
            return (
                "CURRENT_EXACT",
                CurrentAuthorityView(
                    status="present",
                    matching_revision=head_rev,
                    matching_content_sha256=head_digest,
                    product_discoverable=True,
                ),
                ["exact Build identity and claimed revision present (no historical digest to verify)"],
            )

    # Historical content evidence requires proof — never identity-only CURRENT_EXACT.
    if domain in {"plan", "runbook"} and content_sha256:
        if head_digest is None:
            probed, failure = _probe_plan_runbook_head_digest(domain=domain, identity=identity)
            if failure == "unavailable":
                return (
                    "COMPARISON_UNAVAILABLE",
                    CurrentAuthorityView(
                        status="unavailable",
                        head_revision=head_rev,
                        product_discoverable=True,
                    ),
                    [
                        "current identity present but APP-STATE could not prove "
                        "exact content against historical digest"
                    ],
                )
            head_digest = probed
        if head_digest is None:
            return (
                "CONFLICT",
                CurrentAuthorityView(
                    status="conflict",
                    head_revision=head_rev,
                    product_discoverable=True,
                ),
                [
                    "current identity present but no content digest available to "
                    "verify historical bytes"
                ],
            )
        if head_digest != content_sha256:
            return (
                "CONFLICT",
                CurrentAuthorityView(
                    status="conflict",
                    head_revision=head_rev,
                    matching_content_sha256=head_digest,
                    product_discoverable=True,
                ),
                [
                    "same identity present with disagreeing content digest "
                    "(historical content evidence does not match current)"
                ],
            )
        return (
            "CURRENT_EXACT",
            CurrentAuthorityView(
                status="present",
                matching_revision=head_rev,
                matching_content_sha256=head_digest,
                head_revision=head_rev,
                product_discoverable=True,
            ),
            ["exact identity and content digest already in current authority"],
        )

    return (
        "CURRENT_EXACT",
        CurrentAuthorityView(
            status="present",
            matching_revision=head_rev,
            matching_content_sha256=head_digest,
            head_revision=head_rev,
            product_discoverable=True,
        ),
        reasons
        or [
            "exact identity present in current authority "
            "(no additional historical revision/content evidence to verify)"
        ],
    )

def _classify_ingest(
    *,
    identity: str,
    fingerprint: str | None,
    current: CurrentAuthoritySnapshot,
    historical_conflict: bool,
    has_malformed_only: bool,
    adapt_failed: bool,
    from_registry: bool,
) -> tuple[Classification, CurrentAuthorityView, list[str]]:
    if has_malformed_only:
        return (
            "MALFORMED",
            CurrentAuthorityView(status="not_applicable"),
            ["historical ingest artifact failed admitted schema parse"],
        )
    if adapt_failed:
        return (
            "NEEDS_ADAPTER",
            CurrentAuthorityView(status="not_applicable"),
            ["manifest lacks required stable source identity; no generated IDs"],
        )
    if historical_conflict:
        return (
            "CONFLICT",
            CurrentAuthorityView(status="conflict"),
            ["same run_id disagrees across historical observations"],
        )
    if not current.readable:
        return (
            "COMPARISON_UNAVAILABLE",
            CurrentAuthorityView(status="unavailable", detail=current.detail),
            ["current APP-STATE ingest authority is not authoritatively readable"],
        )
    present = current.ingest.get(identity)
    if present is None:
        return (
            "RECOVERABLE_EXACT",
            CurrentAuthorityView(status="absent", product_discoverable=False),
            [
                "exact ExtractionRun absent from readable APP-STATE",
                (
                    "existing explicit registry importer is a candidate successor mechanism"
                    if from_registry
                    else "manifest-era adaptation produced canonical fields without writing"
                ),
            ],
        )
    if fingerprint and present.get("fingerprint") != fingerprint:
        return (
            "CONFLICT",
            CurrentAuthorityView(
                status="conflict",
                product_discoverable=True,
                matching_content_sha256=present.get("fingerprint"),
            ),
            ["same run_id disagrees with current APP-STATE durable payload"],
        )
    return (
        "CURRENT_EXACT",
        CurrentAuthorityView(
            status="present",
            matching_revision=present.get("revision"),
            matching_content_sha256=present.get("fingerprint"),
            product_discoverable=True,
        ),
        ["exact ExtractionRun already in APP-STATE ingest.run"],
    )


def _classify_play_run(
    *,
    identity: str,
    binding: dict[str, Any] | None,
    fingerprint: str | None,
    current: CurrentAuthoritySnapshot,
    historical_conflict: bool,
    has_malformed_only: bool,
) -> tuple[Classification, CurrentAuthorityView, list[str]]:
    if has_malformed_only:
        return (
            "MALFORMED",
            CurrentAuthorityView(status="not_applicable"),
            ["legacy Play Run failed admitted schema parse"],
        )
    if historical_conflict:
        return (
            "CONFLICT",
            CurrentAuthorityView(status="conflict"),
            ["same Play Run id disagrees across historical observations"],
        )
    if not current.readable:
        return (
            "COMPARISON_UNAVAILABLE",
            CurrentAuthorityView(status="unavailable", detail=current.detail),
            ["current APP-STATE Play authority is not authoritatively readable"],
        )
    present = current.play_runs.get(identity)
    if present is None:
        return (
            "NEEDS_ADAPTER",
            CurrentAuthorityView(status="absent", product_discoverable=False),
            [
                "legacy Play Run exact id absent from APP-STATE",
                "no production Play-Run file importer is mounted; inventory-only",
            ],
        )
    # Exact binding comparison when available.
    if binding:
        mismatches = []
        for key in ("playable_artifact_id", "playable_revision", "playable_content_sha256"):
            if str(present.get(key)) != str(binding.get(key)):
                mismatches.append(key)
        if mismatches:
            return (
                "CONFLICT",
                CurrentAuthorityView(status="conflict", product_discoverable=True),
                [f"Play Run binding mismatch on {', '.join(mismatches)}"],
            )
    return (
        "CURRENT_EXACT",
        CurrentAuthorityView(
            status="present",
            matching_revision=present.get("run_revision"),
            matching_content_sha256=present.get("playable_content_sha256"),
            product_discoverable=True,
        ),
        ["exact Play Run already in APP-STATE"],
    )


def reconcile(
    pendings: list[_PendingObs],
    current: CurrentAuthoritySnapshot,
) -> list[LedgerItem]:
    groups: dict[tuple[Domain, str], list[_PendingObs]] = defaultdict(list)
    for item in pendings:
        groups[(item.domain, item.identity)].append(item)

    ledger: list[LedgerItem] = []
    for (domain, identity), group in groups.items():
        observations, reasons, hist_conflict = _merge_group(group)
        parse_statuses = {o.parse_status for o in observations}
        has_malformed_only = parse_statuses == {"malformed"} or (
            all(o.parse_status == "malformed" for o in observations) and observations
        )
        adapt_failed = any(o.parse_status == "adapt_failed" for o in observations) and not any(
            o.parse_status in {"ok", "adapted"} for o in observations
        )
        title = next((g.title for g in group if g.title), None)
        campaign_id = next((g.campaign_id for g in group if g.campaign_id), None)
        session_id = next((g.session_id for g in group if g.session_id), None)

        ok = [o for o in observations if o.parse_status in {"ok", "adapted"}]
        claimed_revision = next((o.claimed_revision for o in ok if o.claimed_revision is not None), None)
        content_sha256 = next((o.content_sha256 for o in ok if o.content_sha256), None)
        fingerprint = next((o.durable_fingerprint for o in ok if o.durable_fingerprint), None)
        from_registry = any(o.source_kind == "extraction_runs_registry" for o in observations)
        has_registry_record = any(
            o.source_kind == "workspace_documents_registry" for o in ok
        )
        content_status = next((g.content_status for g in group if g.content_status), None)
        play_binding = next((g.play_binding for g in group if g.play_binding), None)

        if domain in {"plan", "runbook", "build"}:
            classification, current_view, more = _classify_plan_or_runbook(
                domain=domain,
                identity=identity,
                claimed_revision=claimed_revision,
                content_sha256=content_sha256,
                content_status=content_status,
                has_registry_record=has_registry_record,
                current=current,
                historical_conflict=hist_conflict,
                has_malformed_only=has_malformed_only,
                adapt_failed=False,
            )
        elif domain == "ingest":
            classification, current_view, more = _classify_ingest(
                identity=identity,
                fingerprint=fingerprint,
                current=current,
                historical_conflict=hist_conflict,
                has_malformed_only=has_malformed_only,
                adapt_failed=adapt_failed,
                from_registry=from_registry,
            )
        else:
            classification, current_view, more = _classify_play_run(
                identity=identity,
                binding=play_binding,
                fingerprint=fingerprint,
                current=current,
                historical_conflict=hist_conflict,
                has_malformed_only=has_malformed_only,
            )

        ledger.append(
            LedgerItem(
                domain=domain,
                identity_kind="document_id" if domain in {"plan", "build", "runbook"} else "run_id",
                identity=identity,
                campaign_id=campaign_id,
                session_id=session_id,
                title=title,
                historical_observations=sorted(
                    observations,
                    key=lambda o: (o.root_label, o.relative_locator, o.source_kind),
                ),
                current_authority=current_view,
                classification=classification,
                reason=reasons + more,
            )
        )

    # Ensure empty domains still appear via synthetic summary items? Handoff says
    # domains appear even when empty — handled in markdown/counts, not fake items.

    ledger.sort(
        key=lambda item: (
            item.domain,
            _CLASSIFICATION_ORDER.get(item.classification, 99),
            item.identity,
        )
    )
    return ledger


def _counts(items: list[LedgerItem]) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    classification_counts: dict[str, int] = defaultdict(int)
    domain_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in items:
        classification_counts[item.classification] += 1
        domain_counts[item.domain][item.classification] += 1
    return (
        dict(sorted(classification_counts.items())),
        {d: dict(sorted(c.items())) for d, c in sorted(domain_counts.items())},
    )


def render_markdown(report: InventoryReport) -> str:
    lines: list[str] = []
    lines.append("# Product continuity inventory")
    lines.append("")
    lines.append(f"- Schema: `{report.schema_version}`")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Incomplete: `{report.incomplete}`")
    lines.append("")
    lines.append("## Current authority coordinates")
    lines.append("")
    a = report.authority
    lines.append(f"- APP-STATE configured: `{a.app_state_configured}`")
    lines.append(f"- APP-STATE readable: `{a.app_state_readable}`")
    lines.append(f"- Host: `{a.host}`")
    lines.append(f"- Port: `{a.port}`")
    lines.append(f"- Database: `{a.database_name}`")
    lines.append(f"- Schema head: `{a.schema_head_status}`")
    lines.append(f"- Current repo root: `{a.current_repo_root}`")
    lines.append(f"- Build registry locator: `{a.current_build_registry_locator}`")
    if a.detail:
        lines.append(f"- Detail: {a.detail}")
    lines.append("")
    lines.append("## Historical roots")
    lines.append("")
    for root in report.historical_roots:
        lines.append(f"- `{root['label']}` → `{root['path']}`")
    if not report.historical_roots:
        lines.append("- _(none)_")
    lines.append("")
    lines.append("## Classification counts")
    lines.append("")
    for key, value in report.classification_counts.items():
        lines.append(f"- `{key}`: {value}")
    if not report.classification_counts:
        lines.append("- _(none)_")
    lines.append("")
    lines.append("## Per-domain counts")
    lines.append("")
    for domain in ("plan", "build", "ingest", "runbook", "play_run"):
        counts = report.domain_counts.get(domain, {})
        lines.append(f"### {domain}")
        lines.append("")
        if not counts:
            lines.append("- _(no historical observations)_")
        else:
            for key, value in counts.items():
                lines.append(f"- `{key}`: {value}")
        lines.append("")
    lines.append("## Ledger")
    lines.append("")
    for item in report.items:
        lines.append(f"### `{item.domain}` / `{item.identity}` → **{item.classification}**")
        lines.append("")
        if item.title:
            lines.append(f"- Title: {item.title}")
        if item.campaign_id:
            lines.append(f"- Campaign: `{item.campaign_id}`")
        if item.session_id:
            lines.append(f"- Session: `{item.session_id}`")
        lines.append(
            f"- Current authority: `{item.current_authority.status}` "
            f"(discoverable={item.current_authority.product_discoverable})"
        )
        for reason in item.reason:
            lines.append(f"- Reason: {reason}")
        for obs in item.historical_observations:
            lines.append(
                f"- Observation: `{obs.source_kind}` @ `{obs.root_label}`:"
                f"`{obs.relative_locator}` ({obs.parse_status})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_inventory(
    *,
    current_repo_root: Path,
    historical_roots: list[tuple[str, Path]],
) -> InventoryReport:
    """Execute read-only inventory. Raises FileNotFoundError for missing roots."""
    current_repo_root = current_repo_root.resolve()
    for label, root in historical_roots:
        if not root.is_dir():
            raise FileNotFoundError(f"historical root '{label}' is missing/unreadable: {root}")

    current = observe_current_authority(current_repo_root)
    detail_parts = [current.detail, current.builds_detail]
    authority = sanitize_authority_coordinates(
        current_repo_root=current_repo_root,
        readable=current.readable,
        schema_head_status=current.schema_head_status,
        detail="; ".join(part for part in detail_parts if part),
    )

    pendings: list[_PendingObs] = []
    root_meta: list[dict[str, str]] = []
    # Sort by label so root-order never affects ledger/markdown identity order.
    for label, root in sorted(historical_roots, key=lambda pair: pair[0]):
        resolved = root.resolve()
        root_meta.append({"label": label, "path": str(resolved)})
        pendings.extend(scan_historical_root(resolved, root_label=label))

    items = reconcile(pendings, current)
    classification_counts, domain_counts = _counts(items)
    incomplete = (not current.readable) or (not current.builds_readable)
    if any(item.classification == "COMPARISON_UNAVAILABLE" for item in items):
        incomplete = True

    return InventoryReport(
        generated_at=_utc_now(),
        authority=authority,
        historical_roots=root_meta,
        items=items,
        classification_counts=classification_counts,
        domain_counts=domain_counts,
        incomplete=incomplete,
    )
