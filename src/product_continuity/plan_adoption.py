"""Exact historical Plan adoption (DFC-2a).

Re-observes current product authority via the accepted DFC-1 inventory, then
optionally drives the existing exact Plan importer. Never synthesizes identity,
never mutates the historical root, and never writes unless every selected ID is
safe.

DFC-1 classification is predecessor evidence and is not changed here. DFC-2a's
content-recovery gate is stricter: a selected ``RECOVERABLE_EXACT`` Plan is
eligible to import only when admitted historical target bytes exist under the
explicit root. Missing/empty bytes block the requested set rather than creating
blank WorkObjects.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from application_state.content.import_plans import import_plans_from_registry
from application_state.content.types import normalize_markdown, sha256_utf8
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateUnavailableError,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryDocument,
    get_workspace_document_snapshot,
    list_workspace_documents,
    workspace_documents_path,
)
from live_play.live_store import load_json
from product_continuity.inventory import (
    AuthorityCoordinates,
    Classification,
    HistoricalObservation,
    InventoryReport,
    LedgerItem,
    run_inventory,
)

ADOPTION_SCHEMA = "dmb_plan_exact_adoption_v1"
ADOPT_CLASSIFICATIONS: frozenset[Classification] = frozenset({"RECOVERABLE_EXACT"})
NOOP_CLASSIFICATIONS: frozenset[Classification] = frozenset(
    {"CURRENT_EXACT", "CURRENT_CONTAINS_HISTORY"}
)
SAFE_CLASSIFICATIONS = ADOPT_CLASSIFICATIONS | NOOP_CLASSIFICATIONS

MISSING_TARGET_BYTES_REASON = (
    "RECOVERABLE_EXACT but admitted historical target bytes are absent/empty; "
    "later archive/adapter recovery required"
)
ESCAPING_TARGET_REASON = (
    "target_relpath escapes the explicitly supplied historical root"
)

AdoptionAction = Literal["adopt", "noop", "block"]
AdoptionMode = Literal["preview", "apply"]
ProductVerification = Literal["not_run", "skipped", "passed", "failed"]


class PlanAdoptionError(Exception):
    """Operator-facing adoption failure with no product write."""


class PlanAdoptionInputError(PlanAdoptionError):
    """Invalid selector/root; inventory is not run."""


class PlanAdoptionDisposition(BaseModel):
    document_id: str
    classification: Classification | None = None
    action: AdoptionAction
    domain: str | None = None
    title: str | None = None
    reason: list[str] = Field(default_factory=list)


class PlanAdoptionReport(BaseModel):
    schema_version: Literal["dmb_plan_exact_adoption_v1"] = ADOPTION_SCHEMA
    generated_at: str
    mode: AdoptionMode
    blocked: bool
    applied: bool
    historical_root: str
    current_repo_root: str
    authority: AuthorityCoordinates
    selected_ids: list[str]
    dispositions: list[PlanAdoptionDisposition] = Field(default_factory=list)
    importer_imported: int = 0
    importer_noop: int = 0
    importer_skipped_empty: int = 0
    product_verification: ProductVerification = "not_run"
    product_verification_detail: str | None = None
    historical_root_digest_before: str | None = None
    historical_root_digest_after: str | None = None
    historical_root_unchanged: bool | None = None
    detail: str | None = None


@dataclass(frozen=True)
class PinnedPlanEvidence:
    """Exact record + target bytes classified safe immediately before commit."""

    record: WorkspaceDocumentRecord
    target_relpath: str
    markdown: str
    content_sha256: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_document_id(raw: str) -> str:
    text = str(raw).strip()
    try:
        return str(UUID(text))
    except (ValueError, TypeError) as exc:
        raise PlanAdoptionInputError(f"not an exact UUID: {raw!r}") from exc


def normalize_document_ids(raw_ids: list[str]) -> list[str]:
    if not raw_ids:
        raise PlanAdoptionInputError("--document-id is required")
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in raw_ids:
        document_id = normalize_document_id(raw)
        if document_id in seen:
            raise PlanAdoptionInputError(f"duplicate --document-id {document_id}")
        seen.add(document_id)
        normalized.append(document_id)
    return normalized


def confined_target_path(
    historical_root: Path, target_relpath: str | None
) -> tuple[Path | None, str | None]:
    """Resolve ``target_relpath`` inside ``historical_root``.

    Absolute locators and ``..`` / symlink escapes are rejected. A missing
    locator is also an error: DFC-2a will not invent a path.
    """
    if target_relpath is None or str(target_relpath).strip() == "":
        return None, "historical target_relpath is missing"
    raw = str(target_relpath)
    if Path(raw).is_absolute():
        return None, ESCAPING_TARGET_REASON
    root = historical_root.resolve()
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, ESCAPING_TARGET_REASON
    return candidate, None


def read_admitted_plan_bytes(
    historical_root: Path, record: WorkspaceDocumentRecord
) -> tuple[str | None, str | None]:
    """Return (normalized markdown, error). Empty/missing/escaping bytes fail."""
    path, error = confined_target_path(historical_root, record.target_relpath)
    if error:
        return None, error
    assert path is not None
    if not path.is_file():
        return None, MISSING_TARGET_BYTES_REASON
    markdown = normalize_markdown(path.read_text(encoding="utf-8"))
    if markdown == "":
        return None, MISSING_TARGET_BYTES_REASON
    return markdown, None


def historical_root_digest(root: Path) -> str:
    """Digest Plan evidence under the historical root (registry + Plan bytes).

    Full-tree hashing is not used: real historical checkouts contain VCS,
    dependencies, and unrelated corpus files. The importer only reads the
    workspace registry and Plan target bytes.
    """
    root = root.resolve()
    candidates: set[Path] = set()
    registry = workspace_documents_path(root)
    if registry.is_file():
        candidates.add(registry)
        try:
            document = WorkspaceDocumentRegistryDocument.model_validate(load_json(registry))
            for record in document.records:
                if not record.target_relpath:
                    continue
                target, error = confined_target_path(root, record.target_relpath)
                if error or target is None or not target.is_file():
                    continue
                candidates.add(target)
        except Exception:
            pass
    plan_dir = root / "out/workspace/plan"
    if plan_dir.is_dir():
        for path in plan_dir.rglob("*"):
            if path.is_file():
                resolved = path.resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    continue
                candidates.add(resolved)
    digest = hashlib.sha256()
    for path in sorted(candidates, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_historical_plan_record(
    historical_root: Path, document_id: str
) -> WorkspaceDocumentRecord | None:
    path = workspace_documents_path(historical_root)
    if not path.is_file():
        return None
    try:
        raw = load_json(path)
        document = WorkspaceDocumentRegistryDocument.model_validate(raw)
    except Exception:
        return None
    matches = [
        record for record in document.records if record.document_id == document_id
    ]
    if len(matches) != 1:
        return None
    record = matches[0]
    if record.kind != "plan":
        return None
    return record


def _ledger_by_identity(inventory: InventoryReport) -> dict[str, LedgerItem]:
    return {item.identity: item for item in inventory.items}


def _observation_for_historical_root(
    item: LedgerItem, historical_root: Path
) -> HistoricalObservation | None:
    """The registry observation from this root that earned classification.

    The same identity may also have an ``orphan_bytes`` observation. Only the
    workspace registry observation carries admitted record metadata + digest.
    """
    label = historical_root.name
    ok = [
        obs
        for obs in item.historical_observations
        if obs.parse_status == "ok"
        and obs.root_label == label
        and obs.source_kind == "workspace_documents_registry"
    ]
    if len(ok) == 1:
        return ok[0]
    return None


def _raw_confined_file_digest(
    historical_root: Path, record: WorkspaceDocumentRecord
) -> tuple[str | None, str | None]:
    """SHA-256 of live UTF-8 bytes, matching DFC-1 ``_file_sha256``."""
    path, error = confined_target_path(historical_root, record.target_relpath)
    if error:
        return None, error
    assert path is not None
    if not path.is_file():
        return None, MISSING_TARGET_BYTES_REASON
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None, MISSING_TARGET_BYTES_REASON
    return sha256_utf8(raw), None


def _pin_mismatches_classified_observation(
    *,
    record: WorkspaceDocumentRecord,
    raw_digest: str,
    item: LedgerItem,
    historical_root: Path,
) -> str | None:
    """Return an error if live pin evidence is not the classified observation."""
    observation = _observation_for_historical_root(item, historical_root)
    if observation is None:
        return (
            "classified LedgerItem has no unique historical observation for this root"
        )
    if not observation.content_sha256:
        return "classified observation has no admitted content digest to bind the pin"
    if raw_digest != observation.content_sha256:
        return (
            "live historical bytes digest does not match the classified "
            "RECOVERABLE_EXACT observation"
        )
    if (
        observation.claimed_revision is not None
        and record.revision != observation.claimed_revision
    ):
        return (
            "live WorkspaceDocumentRecord revision does not match classified observation"
        )
    meta = observation.durable_metadata or {}
    for key in ("campaign_id", "title", "target_session", "status", "content_status"):
        if key not in meta:
            continue
        if getattr(record, key) != meta[key]:
            return (
                f"live WorkspaceDocumentRecord {key} does not match classified observation"
            )
    return None


def classify_selected_plans(
    inventory: InventoryReport,
    document_ids: list[str],
    *,
    historical_root: Path,
) -> list[PlanAdoptionDisposition]:
    by_id = _ledger_by_identity(inventory)
    dispositions: list[PlanAdoptionDisposition] = []
    for document_id in document_ids:
        item = by_id.get(document_id)
        if item is None:
            dispositions.append(
                PlanAdoptionDisposition(
                    document_id=document_id,
                    action="block",
                    reason=["selected identity is absent from the historical ledger"],
                )
            )
            continue
        if item.domain != "plan":
            dispositions.append(
                PlanAdoptionDisposition(
                    document_id=document_id,
                    classification=item.classification,
                    action="block",
                    domain=item.domain,
                    title=item.title,
                    reason=["selected identity is not a Plan"],
                )
            )
            continue
        if item.classification in NOOP_CLASSIFICATIONS:
            dispositions.append(
                PlanAdoptionDisposition(
                    document_id=document_id,
                    classification=item.classification,
                    action="noop",
                    domain=item.domain,
                    title=item.title,
                    reason=list(item.reason)
                    or [f"{item.classification} is a truthful no-op"],
                )
            )
            continue
        if item.classification in ADOPT_CLASSIFICATIONS:
            record = load_historical_plan_record(historical_root, document_id)
            if record is None:
                dispositions.append(
                    PlanAdoptionDisposition(
                        document_id=document_id,
                        classification=item.classification,
                        action="block",
                        domain=item.domain,
                        title=item.title,
                        reason=[
                            "RECOVERABLE_EXACT but historical WorkspaceDocumentRecord "
                            "could not be resolved"
                        ],
                    )
                )
                continue
            markdown, error = read_admitted_plan_bytes(historical_root, record)
            if error or markdown is None:
                dispositions.append(
                    PlanAdoptionDisposition(
                        document_id=document_id,
                        classification=item.classification,
                        action="block",
                        domain=item.domain,
                        title=item.title,
                        reason=[error or MISSING_TARGET_BYTES_REASON],
                    )
                )
                continue
            raw_digest, digest_error = _raw_confined_file_digest(historical_root, record)
            if digest_error or raw_digest is None:
                dispositions.append(
                    PlanAdoptionDisposition(
                        document_id=document_id,
                        classification=item.classification,
                        action="block",
                        domain=item.domain,
                        title=item.title,
                        reason=[digest_error or MISSING_TARGET_BYTES_REASON],
                    )
                )
                continue
            mismatch = _pin_mismatches_classified_observation(
                record=record,
                raw_digest=raw_digest,
                item=item,
                historical_root=historical_root,
            )
            if mismatch:
                dispositions.append(
                    PlanAdoptionDisposition(
                        document_id=document_id,
                        classification=item.classification,
                        action="block",
                        domain=item.domain,
                        title=item.title,
                        reason=[mismatch],
                    )
                )
                continue
            dispositions.append(
                PlanAdoptionDisposition(
                    document_id=document_id,
                    classification=item.classification,
                    action="adopt",
                    domain=item.domain,
                    title=item.title,
                    reason=list(item.reason) or ["RECOVERABLE_EXACT is eligible to import"],
                )
            )
            continue
        dispositions.append(
            PlanAdoptionDisposition(
                document_id=document_id,
                classification=item.classification,
                action="block",
                domain=item.domain,
                title=item.title,
                reason=[
                    f"classification {item.classification} is not eligible for adoption"
                ],
            )
        )
    return dispositions


def _blocked(dispositions: list[PlanAdoptionDisposition]) -> bool:
    return any(row.action == "block" for row in dispositions)


def _observe(
    *,
    current_repo_root: Path,
    historical_root: Path,
) -> InventoryReport:
    if not historical_root.is_dir():
        raise PlanAdoptionInputError(
            f"historical root is missing/unreadable: {historical_root}"
        )
    label = historical_root.name
    return run_inventory(
        current_repo_root=current_repo_root,
        historical_roots=[(label, historical_root)],
    )


def preview_plan_adoption(
    *,
    current_repo_root: Path,
    historical_root: Path,
    document_ids: list[str],
) -> PlanAdoptionReport:
    selected = normalize_document_ids(document_ids)
    current_repo_root = current_repo_root.resolve()
    historical_root = historical_root.resolve()
    before = historical_root_digest(historical_root)
    inventory = _observe(
        current_repo_root=current_repo_root, historical_root=historical_root
    )
    dispositions = classify_selected_plans(
        inventory, selected, historical_root=historical_root
    )
    after = historical_root_digest(historical_root)
    blocked = _blocked(dispositions)
    return PlanAdoptionReport(
        generated_at=_utc_now(),
        mode="preview",
        blocked=blocked,
        applied=False,
        historical_root=str(historical_root),
        current_repo_root=str(current_repo_root),
        authority=inventory.authority,
        selected_ids=selected,
        dispositions=dispositions,
        product_verification="skipped",
        historical_root_digest_before=before,
        historical_root_digest_after=after,
        historical_root_unchanged=before == after,
        detail="preview only; no importer write",
    )


def _pin_selected_adoptions(
    historical_root: Path,
    dispositions: list[PlanAdoptionDisposition],
    inventory: InventoryReport,
) -> tuple[list[PinnedPlanEvidence] | None, str | None]:
    pins: list[PinnedPlanEvidence] = []
    by_id = _ledger_by_identity(inventory)
    for row in dispositions:
        if row.action != "adopt":
            continue
        item = by_id.get(row.document_id)
        if item is None:
            return None, (
                f"blocked: {row.document_id} disappeared from the classified ledger "
                "before pin creation"
            )
        record = load_historical_plan_record(historical_root, row.document_id)
        if record is None or record.target_relpath is None:
            return None, (
                f"blocked: {row.document_id} became unresolvable immediately before import"
            )
        markdown, error = read_admitted_plan_bytes(historical_root, record)
        if error or markdown is None:
            return None, (
                f"blocked: {row.document_id} lost admitted historical target bytes "
                "immediately before import"
            )
        raw_digest, digest_error = _raw_confined_file_digest(historical_root, record)
        if digest_error or raw_digest is None:
            return None, (
                f"blocked: {row.document_id} lost admitted historical target bytes "
                "immediately before import"
            )
        mismatch = _pin_mismatches_classified_observation(
            record=record,
            raw_digest=raw_digest,
            item=item,
            historical_root=historical_root,
        )
        if mismatch:
            return None, f"blocked: {row.document_id}: {mismatch}"
        pins.append(
            PinnedPlanEvidence(
                record=record,
                target_relpath=record.target_relpath,
                markdown=markdown,
                content_sha256=sha256_utf8(markdown),
            )
        )
    return pins, None


def _revalidate_pinned_evidence(
    historical_root: Path, pins: list[PinnedPlanEvidence]
) -> str | None:
    """Fail closed if live historical evidence no longer matches the pin.

    Tests wrap this function to mutate/delete the live target after preflight
    and prove zero product writes.
    """
    for pin in pins:
        live_record = load_historical_plan_record(
            historical_root, pin.record.document_id
        )
        if live_record is None or live_record != pin.record:
            return (
                f"{pin.record.document_id}: historical WorkspaceDocumentRecord "
                "changed after preflight"
            )
        markdown, error = read_admitted_plan_bytes(historical_root, pin.record)
        if error or markdown is None:
            return (
                f"{pin.record.document_id}: pinned evidence no longer matches live "
                f"historical bytes ({error})"
            )
        if markdown != pin.markdown or sha256_utf8(markdown) != pin.content_sha256:
            return (
                f"{pin.record.document_id}: historical target bytes changed after preflight"
            )
    return None


def _materialize_pinned_importer_root(pins: list[PinnedPlanEvidence]) -> Path:
    """Write pinned bytes under a throwaway root the existing importer can read.

    The live historical root is never this directory. The importer therefore
    cannot independently re-read bytes B after preflight classified bytes A.
    """
    snapshot = Path(tempfile.mkdtemp(prefix="dmb-dfc2a-pin-"))
    try:
        for pin in pins:
            dest, error = confined_target_path(snapshot, pin.target_relpath)
            if error or dest is None:
                raise PlanAdoptionError(
                    f"{pin.record.document_id}: pinned target_relpath is not "
                    f"confined in the importer snapshot ({error})"
                )
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(pin.markdown, encoding="utf-8")
    except Exception:
        shutil.rmtree(snapshot, ignore_errors=True)
        raise
    return snapshot


def _expected_snapshot_fields(
    record: WorkspaceDocumentRecord,
    *,
    markdown: str,
) -> dict[str, Any]:
    return {
        "document_id": record.document_id,
        "revision": record.revision,
        "campaign_id": record.campaign_id,
        "title": record.title,
        "target_session": record.target_session,
        "status": record.status,
        "content_sha256": sha256_utf8(markdown),
        "markdown": markdown,
    }


def _verify_product_seam(
    *,
    current_repo_root: Path,
    dispositions: list[PlanAdoptionDisposition],
    pins: list[PinnedPlanEvidence],
) -> tuple[ProductVerification, str | None]:
    pins_by_id = {pin.record.document_id: pin for pin in pins}
    failures: list[str] = []
    for row in dispositions:
        if row.action == "noop":
            snapshot = get_workspace_document_snapshot(current_repo_root, row.document_id)
            if snapshot.record.document_id != row.document_id:
                failures.append(f"{row.document_id}: identity mismatch after no-op")
                continue
            list_status = (
                snapshot.record.status
                if snapshot.record.status in {"active", "discarded"}
                else "active"
            )
            listed_ids = {
                record.document_id
                for record in list_workspace_documents(
                    current_repo_root, kind="plan", status=list_status
                )
            }
            if row.document_id not in listed_ids:
                failures.append(
                    f"{row.document_id}: absent from Plan product list (status={list_status})"
                )
            continue
        if row.action != "adopt":
            continue
        pin = pins_by_id.get(row.document_id)
        if pin is None:
            failures.append(f"{row.document_id}: adopted identity has no pinned evidence")
            continue
        expected = _expected_snapshot_fields(pin.record, markdown=pin.markdown)
        list_status = expected["status"] if expected["status"] in {"active", "discarded"} else "active"
        listed_for_status = {
            record.document_id: record
            for record in list_workspace_documents(
                current_repo_root, kind="plan", status=list_status
            )
        }
        if row.document_id not in listed_for_status:
            failures.append(
                f"{row.document_id}: absent from Plan product list (status={list_status})"
            )
            continue
        snapshot = get_workspace_document_snapshot(current_repo_root, row.document_id)
        checks = (
            ("document_id", snapshot.record.document_id, expected["document_id"]),
            ("revision", snapshot.record.revision, expected["revision"]),
            ("campaign_id", snapshot.record.campaign_id, expected["campaign_id"]),
            ("title", snapshot.record.title, expected["title"]),
            ("target_session", snapshot.record.target_session, expected["target_session"]),
            ("status", snapshot.record.status, expected["status"]),
            ("content_sha256", snapshot.content_sha256, expected["content_sha256"]),
            ("markdown", snapshot.markdown, expected["markdown"]),
        )
        for name, actual, wanted in checks:
            if actual != wanted:
                failures.append(
                    f"{row.document_id}: {name} mismatch after adoption"
                )
    if failures:
        return "failed", "; ".join(failures)
    return "passed", None


def apply_plan_adoption(
    *,
    current_repo_root: Path,
    historical_root: Path,
    document_ids: list[str],
) -> PlanAdoptionReport:
    selected = normalize_document_ids(document_ids)
    current_repo_root = current_repo_root.resolve()
    historical_root = historical_root.resolve()
    before = historical_root_digest(historical_root)
    inventory = _observe(
        current_repo_root=current_repo_root, historical_root=historical_root
    )
    dispositions = classify_selected_plans(
        inventory, selected, historical_root=historical_root
    )
    blocked = _blocked(dispositions)
    base = PlanAdoptionReport(
        generated_at=_utc_now(),
        mode="apply",
        blocked=blocked,
        applied=False,
        historical_root=str(historical_root),
        current_repo_root=str(current_repo_root),
        authority=inventory.authority,
        selected_ids=selected,
        dispositions=dispositions,
        historical_root_digest_before=before,
    )
    if blocked:
        after = historical_root_digest(historical_root)
        base.historical_root_digest_after = after
        base.historical_root_unchanged = before == after
        base.product_verification = "skipped"
        base.detail = "blocked: entire requested set performs zero writes"
        return base

    pins, pin_error = _pin_selected_adoptions(
        historical_root, dispositions, inventory=inventory
    )
    if pins is None:
        after = historical_root_digest(historical_root)
        base.blocked = True
        base.historical_root_digest_after = after
        base.historical_root_unchanged = before == after
        base.product_verification = "skipped"
        base.detail = pin_error
        return base

    mismatch = _revalidate_pinned_evidence(historical_root, pins)
    if mismatch:
        after = historical_root_digest(historical_root)
        base.blocked = True
        base.historical_root_digest_after = after
        base.historical_root_unchanged = before == after
        base.product_verification = "skipped"
        base.detail = f"blocked: {mismatch}"
        return base

    if pins:
        snapshot_root = _materialize_pinned_importer_root(pins)
        try:
            try:
                importer_report = import_plans_from_registry(
                    snapshot_root, [pin.record for pin in pins]
                )
            except (
                ApplicationStateConflictError,
                ApplicationStateIntegrityError,
                ApplicationStateUnavailableError,
            ) as exc:
                after = historical_root_digest(historical_root)
                base.blocked = True
                base.historical_root_digest_after = after
                base.historical_root_unchanged = before == after
                base.product_verification = "skipped"
                base.detail = f"importer fail-closed; transaction rolled back: {exc}"
                return base
        finally:
            shutil.rmtree(snapshot_root, ignore_errors=True)
        base.importer_imported = importer_report.imported
        base.importer_noop = importer_report.noop
        base.importer_skipped_empty = importer_report.skipped_empty

    base.applied = True
    try:
        if base.importer_skipped_empty:
            verification, verify_detail = (
                "failed",
                "importer skipped_empty is not successful historical-content recovery",
            )
        else:
            verification, verify_detail = _verify_product_seam(
                current_repo_root=current_repo_root,
                dispositions=dispositions,
                pins=pins,
            )
    except Exception as exc:
        verification = "failed"
        verify_detail = f"product seam raised after commit: {exc}"
    after = historical_root_digest(historical_root)
    base.product_verification = verification
    base.product_verification_detail = verify_detail
    base.historical_root_digest_after = after
    base.historical_root_unchanged = before == after
    if verification == "failed":
        base.detail = "adoption committed; product verification failed"
    else:
        base.detail = "adoption committed through existing importer unit-of-work"
    return base


def run_plan_adoption(
    *,
    current_repo_root: Path,
    historical_root: Path,
    document_ids: list[str],
    apply: bool,
) -> PlanAdoptionReport:
    if apply:
        return apply_plan_adoption(
            current_repo_root=current_repo_root,
            historical_root=historical_root,
            document_ids=document_ids,
        )
    return preview_plan_adoption(
        current_repo_root=current_repo_root,
        historical_root=historical_root,
        document_ids=document_ids,
    )
