"""Exact historical Ingest run adoption (DFC-2c).

Re-observes current product authority via the accepted DFC-1 inventory, adapts
admitted manifests with the existing recap adapter, and commits only a pinned
canonical ExtractionRun snapshot through the existing registry importer.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateUnavailableError,
)
from application_state.ingest.import_legacy import (
    ExtractionRunRegistryDocument,
    import_extraction_runs_from_registry,
)
from application_state.ingest.service import get_extraction_run, list_extraction_runs
from apps.live_control_server.services.ingest_run_catalog import (
    list_canonical_extraction_runs,
)
from graph_memory.ingestion.extraction_run import ExtractionRun
from graph_memory.ingestion.graph_ingest_run import (
    GraphIngestRunManifest,
    adapt_recap_manifest_to_extraction_run,
)
from product_continuity.inventory import (
    AuthorityCoordinates,
    Classification,
    HistoricalObservation,
    InventoryReport,
    LedgerItem,
    _durable_run_fingerprint,
    run_inventory,
)

ADOPTION_SCHEMA = "dmb_ingest_exact_adoption_v1"
MANIFEST_SOURCE_KIND = "graph_ingest_run_manifest"
ADMITTED_MANIFEST_PATTERNS = (
    "out/graph_memory/runs/**/graph_ingest_run_manifest.json",
    "evals/graph_memory_layer/artifacts/graph_ingest_runs/**/graph_ingest_run_manifest.json",
)
ADOPT_CLASSIFICATIONS: frozenset[Classification] = frozenset({"RECOVERABLE_EXACT"})
NOOP_CLASSIFICATIONS: frozenset[Classification] = frozenset({"CURRENT_EXACT"})
SAFE_CLASSIFICATIONS = ADOPT_CLASSIFICATIONS | NOOP_CLASSIFICATIONS
ESCAPING_LOCATOR_REASON = (
    "manifest locator escapes the explicitly supplied historical root"
)
_URI_USERINFO_SECRET = re.compile(
    r"(?i)([a-z][a-z0-9+.-]*://[^/\s:@]+):([^@\s]+)@"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*\S+"
)

AdoptionAction = Literal["adopt", "noop", "block"]
AdoptionMode = Literal["preview", "apply"]
ProductVerification = Literal["not_run", "skipped", "passed", "failed"]
RootUnchanged = Literal["true", "false", "unknown"]


class IngestAdoptionError(Exception):
    """Operator-facing adoption failure with no product write."""


class IngestAdoptionInputError(IngestAdoptionError):
    """Invalid selector/root; inventory is not run."""


class IngestAdoptionDisposition(BaseModel):
    run_id: str
    campaign_id: str | None = None
    session_id: str | None = None
    classification: Classification | None = None
    action: AdoptionAction
    durable_fingerprint: str | None = None
    reason: list[str] = Field(default_factory=list)


class IngestAdoptionReport(BaseModel):
    schema_version: Literal["dmb_ingest_exact_adoption_v1"] = ADOPTION_SCHEMA
    generated_at: str
    mode: AdoptionMode
    blocked: bool
    applied: bool = False
    historical_roots: list[dict[str, str]] = Field(default_factory=list)
    current_repo_root: str
    authority: AuthorityCoordinates
    selected_ids: list[str] = Field(default_factory=list)
    selected_count: int = 0
    target_set_sha256: str
    dispositions: list[IngestAdoptionDisposition] = Field(default_factory=list)
    importer_imported: int = 0
    importer_noop: int = 0
    importer_conflict: int = 0
    product_verification: ProductVerification = "not_run"
    product_verification_detail: str | None = None
    historical_roots_digest_before: str | None = None
    historical_roots_digest_after: str | None = None
    historical_roots_unchanged: RootUnchanged | None = None
    unavailable_component_count: int = 0
    detail: str | None = None


@dataclass(frozen=True)
class HistoricalRoot:
    label: str
    path: Path


@dataclass(frozen=True)
class PinnedIngestEvidence:
    run: ExtractionRun
    fingerprint: str
    root_label: str
    relative_locator: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sanitize_operator_detail(text: str) -> str:
    """Redact credentials and URI userinfo from operator-visible detail."""
    try:
        redacted = _URI_USERINFO_SECRET.sub(r"\1:***@", text)
        return _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=***", redacted)
    except Exception:
        return "post-commit observation failed; exception detail omitted"


def _sanitized_post_commit_exception(prefix: str, exc: BaseException) -> str:
    return sanitize_operator_detail(f"{prefix}: {type(exc).__name__}: {exc}")


def normalize_run_id(raw: str) -> str:
    text = str(raw).strip()
    if not text:
        raise IngestAdoptionInputError("not an exact run_id: empty")
    return text


def normalize_run_ids(raw_ids: list[str]) -> list[str]:
    if not raw_ids:
        raise IngestAdoptionInputError("--run-id is required unless --all-historical-ingest")
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in raw_ids:
        run_id = normalize_run_id(raw)
        if run_id in seen:
            raise IngestAdoptionInputError(f"duplicate --run-id {run_id}")
        seen.add(run_id)
        normalized.append(run_id)
    return normalized


def normalize_historical_roots(
    pairs: list[tuple[str, Path]],
) -> list[HistoricalRoot]:
    if not pairs:
        raise IngestAdoptionInputError("--historical-root is required")
    seen: set[str] = set()
    roots: list[HistoricalRoot] = []
    for label, path in pairs:
        cleaned = str(label).strip()
        if not cleaned:
            raise IngestAdoptionInputError("historical root label is required")
        if cleaned in seen:
            raise IngestAdoptionInputError(f"duplicate historical root label {cleaned}")
        seen.add(cleaned)
        resolved = path.expanduser().resolve()
        if not resolved.is_dir():
            raise IngestAdoptionInputError(
                f"historical root '{cleaned}' is missing/unreadable"
            )
        roots.append(HistoricalRoot(label=cleaned, path=resolved))
    return roots


def confined_manifest_path(
    historical_root: Path, relative_locator: str | None
) -> tuple[Path | None, str | None]:
    if relative_locator is None or str(relative_locator).strip() == "":
        return None, "historical manifest locator is missing"
    raw = str(relative_locator)
    if Path(raw).is_absolute():
        return None, ESCAPING_LOCATOR_REASON
    root = historical_root.resolve()
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, ESCAPING_LOCATOR_REASON
    return candidate, None


def target_set_sha256(members: list[tuple[str, str]]) -> str:
    """Digest sorted (run_id, fingerprint) tuples. Independent of root order."""
    digest = hashlib.sha256()
    for run_id, fingerprint in sorted(members, key=lambda item: (item[0], item[1])):
        digest.update(run_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(fingerprint.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def historical_roots_digest(roots: list[HistoricalRoot]) -> str:
    """Digest admitted manifest evidence under the supplied roots."""
    digest = hashlib.sha256()
    for root in sorted(roots, key=lambda item: item.label):
        digest.update(root.label.encode("utf-8"))
        digest.update(b"\0")
        candidates: set[Path] = set()
        for pattern in ADMITTED_MANIFEST_PATTERNS:
            for path in root.path.glob(pattern):
                if path.is_file():
                    resolved = path.resolve()
                    try:
                        resolved.relative_to(root.path.resolve())
                    except ValueError:
                        continue
                    candidates.add(resolved)
        for path in sorted(candidates, key=lambda item: item.as_posix()):
            relative = path.relative_to(root.path.resolve()).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _root_by_label(roots: list[HistoricalRoot]) -> dict[str, HistoricalRoot]:
    return {root.label: root for root in roots}


def _ingest_items(inventory: InventoryReport) -> dict[str, LedgerItem]:
    return {
        item.identity: item
        for item in inventory.items
        if item.domain == "ingest"
    }


def _all_ingest_identities(inventory: InventoryReport) -> list[str]:
    return sorted(_ingest_items(inventory))


def _member_fingerprint(row: IngestAdoptionDisposition) -> str:
    if row.durable_fingerprint:
        return row.durable_fingerprint
    return f"!{row.classification or 'ABSENT'}:{row.action}"


def _target_members(
    dispositions: list[IngestAdoptionDisposition],
) -> list[tuple[str, str]]:
    return [(row.run_id, _member_fingerprint(row)) for row in dispositions]


def _blocked(dispositions: list[IngestAdoptionDisposition]) -> bool:
    return any(row.action == "block" for row in dispositions)


def _manifest_observations(item: LedgerItem) -> list[HistoricalObservation]:
    return [
        obs
        for obs in item.historical_observations
        if obs.source_kind == MANIFEST_SOURCE_KIND
        and obs.parse_status in {"adapted", "ok"}
        and obs.durable_fingerprint
    ]


def _observation_for_pin(item: LedgerItem) -> HistoricalObservation | None:
    ok = _manifest_observations(item)
    fingerprints = {obs.durable_fingerprint for obs in ok}
    if len(fingerprints) != 1:
        return None
    ordered = sorted(ok, key=lambda obs: (obs.root_label, obs.relative_locator))
    return ordered[0] if ordered else None


def _read_adapted_run(
    roots: list[HistoricalRoot], observation: HistoricalObservation
) -> tuple[ExtractionRun | None, str | None]:
    by_label = _root_by_label(roots)
    root = by_label.get(observation.root_label)
    if root is None:
        return None, "classified observation root label is not in the supplied roots"
    path, error = confined_manifest_path(root.path, observation.relative_locator)
    if error:
        return None, error
    assert path is not None
    if not path.is_file():
        return None, "classified manifest locator is missing"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        manifest = GraphIngestRunManifest.model_validate(raw)
        adapted = adapt_recap_manifest_to_extraction_run(manifest)
    except Exception as exc:
        return None, f"live manifest re-adapt failed: {type(exc).__name__}"
    return adapted, None


def classify_selected_ingest(
    inventory: InventoryReport,
    selected_ids: list[str],
    *,
    roots: list[HistoricalRoot],
) -> list[IngestAdoptionDisposition]:
    items = _ingest_items(inventory)
    rows: list[IngestAdoptionDisposition] = []
    for run_id in selected_ids:
        item = items.get(run_id)
        if item is None:
            rows.append(
                IngestAdoptionDisposition(
                    run_id=run_id,
                    action="block",
                    reason=["selected run_id is absent from admitted historical ingest evidence"],
                )
            )
            continue
        classification = item.classification
        fingerprint = None
        observation = _observation_for_pin(item)
        if observation is not None:
            fingerprint = observation.durable_fingerprint
        if classification in ADOPT_CLASSIFICATIONS:
            if observation is None:
                rows.append(
                    IngestAdoptionDisposition(
                        run_id=run_id,
                        campaign_id=item.campaign_id,
                        session_id=item.session_id,
                        classification=classification,
                        action="block",
                        reason=[
                            "RECOVERABLE_EXACT has no unique adapted graph_ingest_run_manifest observation"
                        ],
                    )
                )
                continue
            live, error = _read_adapted_run(roots, observation)
            if live is None or error:
                rows.append(
                    IngestAdoptionDisposition(
                        run_id=run_id,
                        campaign_id=item.campaign_id,
                        session_id=item.session_id,
                        classification=classification,
                        action="block",
                        durable_fingerprint=fingerprint,
                        reason=[error or "live manifest could not be re-adapted"],
                    )
                )
                continue
            live_fp = _durable_run_fingerprint(live)
            if live_fp != observation.durable_fingerprint:
                rows.append(
                    IngestAdoptionDisposition(
                        run_id=run_id,
                        campaign_id=item.campaign_id,
                        session_id=item.session_id,
                        classification=classification,
                        action="block",
                        durable_fingerprint=fingerprint,
                        reason=[
                            "live adapted durable fingerprint does not match the classified observation"
                        ],
                    )
                )
                continue
            rows.append(
                IngestAdoptionDisposition(
                    run_id=run_id,
                    campaign_id=item.campaign_id,
                    session_id=item.session_id,
                    classification=classification,
                    action="adopt",
                    durable_fingerprint=live_fp,
                    reason=list(item.reason) or ["RECOVERABLE_EXACT is eligible to import"],
                )
            )
            continue
        if classification in NOOP_CLASSIFICATIONS:
            rows.append(
                IngestAdoptionDisposition(
                    run_id=run_id,
                    campaign_id=item.campaign_id,
                    session_id=item.session_id,
                    classification=classification,
                    action="noop",
                    durable_fingerprint=fingerprint
                    or (item.current_authority.matching_content_sha256),
                    reason=list(item.reason) or ["exact ExtractionRun already in APP-STATE"],
                )
            )
            continue
        rows.append(
            IngestAdoptionDisposition(
                run_id=run_id,
                campaign_id=item.campaign_id,
                session_id=item.session_id,
                classification=classification,
                action="block",
                durable_fingerprint=fingerprint,
                reason=list(item.reason) or [f"unsafe classification {classification}"],
            )
        )
    rows.sort(key=lambda row: row.run_id)
    return rows


def _observe(
    *,
    current_repo_root: Path,
    roots: list[HistoricalRoot],
) -> InventoryReport:
    return run_inventory(
        current_repo_root=current_repo_root,
        historical_roots=[(root.label, root.path) for root in roots],
    )


def _pin_selected_adoptions(
    roots: list[HistoricalRoot],
    dispositions: list[IngestAdoptionDisposition],
    inventory: InventoryReport,
) -> tuple[list[PinnedIngestEvidence] | None, str | None]:
    items = _ingest_items(inventory)
    pins: list[PinnedIngestEvidence] = []
    for row in dispositions:
        if row.action != "adopt":
            continue
        item = items.get(row.run_id)
        if item is None:
            return None, f"{row.run_id}: classified LedgerItem missing at pin time"
        observation = _observation_for_pin(item)
        if observation is None:
            return None, (
                f"{row.run_id}: classified LedgerItem has no unique adapted "
                "graph_ingest_run_manifest observation"
            )
        live, error = _read_adapted_run(roots, observation)
        if live is None or error:
            return None, f"{row.run_id}: {error or 'live manifest could not be re-adapted'}"
        live_fp = _durable_run_fingerprint(live)
        if live_fp != observation.durable_fingerprint:
            return None, (
                f"{row.run_id}: live adapted durable fingerprint does not match "
                "the classified RECOVERABLE_EXACT observation"
            )
        if row.durable_fingerprint and live_fp != row.durable_fingerprint:
            return None, (
                f"{row.run_id}: live adapted durable fingerprint does not match "
                "the preview target-set member"
            )
        pins.append(
            PinnedIngestEvidence(
                run=live,
                fingerprint=live_fp,
                root_label=observation.root_label,
                relative_locator=observation.relative_locator,
            )
        )
    pins.sort(key=lambda pin: pin.run.run_id)
    return pins, None


def _revalidate_pinned_evidence(
    roots: list[HistoricalRoot], pins: list[PinnedIngestEvidence]
) -> str | None:
    for pin in pins:
        observation = HistoricalObservation(
            source_kind=MANIFEST_SOURCE_KIND,
            root_label=pin.root_label,
            relative_locator=pin.relative_locator,
            durable_fingerprint=pin.fingerprint,
            parse_status="adapted",
        )
        live, error = _read_adapted_run(roots, observation)
        if live is None or error:
            return f"{pin.run.run_id}: {error or 'live manifest missing before commit'}"
        live_fp = _durable_run_fingerprint(live)
        if live_fp != pin.fingerprint:
            return (
                f"{pin.run.run_id}: live historical evidence no longer matches the pinned "
                "canonical payload"
            )
    return None


def _materialize_pinned_importer_root(pins: list[PinnedIngestEvidence]) -> Path:
    snapshot = Path(tempfile.mkdtemp(prefix="dmb-ingest-adopt-"))
    registry = snapshot / "out/registries/extraction_runs.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    document = ExtractionRunRegistryDocument(records=[pin.run for pin in pins])
    registry.write_text(
        json.dumps(document.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return snapshot


def _count_unavailable_components(
    runs: list[ExtractionRun], *, current_repo_root: Path
) -> int:
    count = 0
    for run in runs:
        for component in run.components.values():
            uri = (component.uri or "").strip()
            if not uri:
                count += 1
                continue
            candidate = Path(uri)
            if not candidate.is_absolute():
                candidate = current_repo_root / uri
            if not candidate.is_file():
                count += 1
    return count


def _verify_product_seam(
    *,
    dispositions: list[IngestAdoptionDisposition],
    pins: list[PinnedIngestEvidence],
) -> tuple[ProductVerification, str | None]:
    pins_by_id = {pin.run.run_id: pin for pin in pins}
    try:
        catalog = list_canonical_extraction_runs()
        listed = catalog.get("runs") or []
    except Exception as exc:
        raise ApplicationStateUnavailableError(
            f"Ingest catalog unavailable: {exc}"
        ) from exc
    listed_ids = {str(row.get("run_id")) for row in listed}
    failures: list[str] = []
    for row in dispositions:
        if row.action not in {"adopt", "noop"}:
            continue
        if row.run_id not in listed_ids:
            failures.append(f"{row.run_id}: absent from APP-STATE Ingest catalog")
            continue
        loaded = get_extraction_run(row.run_id)
        actual_fp = _durable_run_fingerprint(loaded)
        expected_fp = row.durable_fingerprint
        if row.action == "adopt":
            pin = pins_by_id.get(row.run_id)
            if pin is None:
                failures.append(f"{row.run_id}: adopted identity has no pinned evidence")
                continue
            expected_fp = pin.fingerprint
        if expected_fp and actual_fp != expected_fp:
            failures.append(
                f"{row.run_id}: catalog durable fingerprint does not match expected payload"
            )
    service_ids = {run.run_id for run in list_extraction_runs()}
    for row in dispositions:
        if row.action in {"adopt", "noop"} and row.run_id not in service_ids:
            failures.append(f"{row.run_id}: absent from list_extraction_runs()")
    if failures:
        return "failed", "; ".join(failures)
    return "passed", None


def _finalize_unchanged(
    before: str, after: str | None
) -> RootUnchanged:
    if after is None:
        return "unknown"
    return "true" if before == after else "false"


def _root_meta(roots: list[HistoricalRoot]) -> list[dict[str, str]]:
    return [{"label": root.label, "path": str(root.path)} for root in roots]


def preview_ingest_adoption(
    *,
    current_repo_root: Path,
    historical_roots: list[tuple[str, Path]],
    run_ids: list[str] | None,
    all_historical: bool,
) -> IngestAdoptionReport:
    roots = normalize_historical_roots(historical_roots)
    current_repo_root = current_repo_root.resolve()
    before = historical_roots_digest(roots)
    inventory = _observe(current_repo_root=current_repo_root, roots=roots)
    if all_historical:
        selected = _all_ingest_identities(inventory)
        if not selected:
            raise IngestAdoptionInputError(
                "--all-historical-ingest selected an empty ingest identity set"
            )
    else:
        selected = normalize_run_ids(list(run_ids or []))
    dispositions = classify_selected_ingest(inventory, selected, roots=roots)
    after = historical_roots_digest(roots)
    blocked = _blocked(dispositions)
    digest = target_set_sha256(_target_members(dispositions))
    return IngestAdoptionReport(
        generated_at=_utc_now(),
        mode="preview",
        blocked=blocked,
        applied=False,
        historical_roots=_root_meta(roots),
        current_repo_root=str(current_repo_root),
        authority=inventory.authority,
        selected_ids=selected,
        selected_count=len(selected),
        target_set_sha256=digest,
        dispositions=dispositions,
        product_verification="skipped",
        historical_roots_digest_before=before,
        historical_roots_digest_after=after,
        historical_roots_unchanged=_finalize_unchanged(before, after),
        detail="preview only; no importer write",
    )


def apply_ingest_adoption(
    *,
    current_repo_root: Path,
    historical_roots: list[tuple[str, Path]],
    run_ids: list[str] | None,
    all_historical: bool,
    expected_set_sha256: str,
) -> IngestAdoptionReport:
    expected = str(expected_set_sha256).strip().lower()
    if not expected:
        raise IngestAdoptionInputError("--expected-set-sha256 is required with --apply")
    roots = normalize_historical_roots(historical_roots)
    current_repo_root = current_repo_root.resolve()
    before = historical_roots_digest(roots)
    inventory = _observe(current_repo_root=current_repo_root, roots=roots)
    if all_historical:
        selected = _all_ingest_identities(inventory)
        if not selected:
            raise IngestAdoptionInputError(
                "--all-historical-ingest selected an empty ingest identity set"
            )
    else:
        selected = normalize_run_ids(list(run_ids or []))
    dispositions = classify_selected_ingest(inventory, selected, roots=roots)
    digest = target_set_sha256(_target_members(dispositions))
    blocked = _blocked(dispositions)
    base = IngestAdoptionReport(
        generated_at=_utc_now(),
        mode="apply",
        blocked=blocked,
        applied=False,
        historical_roots=_root_meta(roots),
        current_repo_root=str(current_repo_root),
        authority=inventory.authority,
        selected_ids=selected,
        selected_count=len(selected),
        target_set_sha256=digest,
        dispositions=dispositions,
        historical_roots_digest_before=before,
    )
    if digest != expected:
        after = historical_roots_digest(roots)
        base.blocked = True
        base.historical_roots_digest_after = after
        base.historical_roots_unchanged = _finalize_unchanged(before, after)
        base.product_verification = "skipped"
        base.detail = (
            "blocked: recomputed target_set_sha256 does not match --expected-set-sha256"
        )
        return base
    if blocked:
        after = historical_roots_digest(roots)
        base.historical_roots_digest_after = after
        base.historical_roots_unchanged = _finalize_unchanged(before, after)
        base.product_verification = "skipped"
        base.detail = "blocked: entire requested set performs zero writes"
        return base

    pins, pin_error = _pin_selected_adoptions(
        roots, dispositions, inventory=inventory
    )
    if pins is None:
        after = historical_roots_digest(roots)
        base.blocked = True
        base.historical_roots_digest_after = after
        base.historical_roots_unchanged = _finalize_unchanged(before, after)
        base.product_verification = "skipped"
        base.detail = pin_error
        return base

    mismatch = _revalidate_pinned_evidence(roots, pins)
    if mismatch:
        after = historical_roots_digest(roots)
        base.blocked = True
        base.historical_roots_digest_after = after
        base.historical_roots_unchanged = _finalize_unchanged(before, after)
        base.product_verification = "skipped"
        base.detail = f"blocked: {mismatch}"
        return base

    if pins:
        snapshot_root = _materialize_pinned_importer_root(pins)
        try:
            try:
                importer_report = import_extraction_runs_from_registry(
                    snapshot_root, dry_run=False
                )
            except (
                ApplicationStateConflictError,
                ApplicationStateIntegrityError,
                ApplicationStateUnavailableError,
            ) as exc:
                after = historical_roots_digest(roots)
                base.blocked = True
                base.historical_roots_digest_after = after
                base.historical_roots_unchanged = _finalize_unchanged(before, after)
                base.product_verification = "skipped"
                base.detail = (
                    "importer fail-closed; transaction rolled back: "
                    f"{sanitize_operator_detail(type(exc).__name__)}"
                )
                return base
        finally:
            shutil.rmtree(snapshot_root, ignore_errors=True)
        base.importer_imported = importer_report.imported
        base.importer_noop = importer_report.noop
        base.importer_conflict = importer_report.conflict

    base.applied = True
    verification: ProductVerification = "failed"
    verify_detail: str | None = None
    after: str | None = None
    try:
        verification, verify_detail = _verify_product_seam(
            dispositions=dispositions,
            pins=pins,
        )
        after = historical_roots_digest(roots)
        base.unavailable_component_count = _count_unavailable_components(
            [pin.run for pin in pins] if pins else [],
            current_repo_root=current_repo_root,
        )
    except Exception as exc:
        verification = "failed"
        verify_detail = _sanitized_post_commit_exception(
            "post-commit observation failed", exc
        )
    base.product_verification = verification
    base.product_verification_detail = verify_detail
    base.historical_roots_digest_after = after
    base.historical_roots_unchanged = _finalize_unchanged(before, after)
    if verification == "failed":
        base.detail = "adoption committed; product verification failed"
    else:
        base.detail = "adoption committed through existing importer unit-of-work"
    return base


def run_ingest_adoption(
    *,
    current_repo_root: Path,
    historical_roots: list[tuple[str, Path]],
    run_ids: list[str] | None,
    all_historical: bool,
    apply: bool,
    expected_set_sha256: str | None = None,
) -> IngestAdoptionReport:
    if all_historical and run_ids:
        raise IngestAdoptionInputError(
            "--run-id and --all-historical-ingest are mutually exclusive"
        )
    if not all_historical and not run_ids:
        raise IngestAdoptionInputError(
            "select exact --run-id values or pass --all-historical-ingest"
        )
    if apply:
        return apply_ingest_adoption(
            current_repo_root=current_repo_root,
            historical_roots=historical_roots,
            run_ids=run_ids,
            all_historical=all_historical,
            expected_set_sha256=expected_set_sha256 or "",
        )
    return preview_ingest_adoption(
        current_repo_root=current_repo_root,
        historical_roots=historical_roots,
        run_ids=run_ids,
        all_historical=all_historical,
    )
