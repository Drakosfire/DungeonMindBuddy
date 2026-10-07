"""Ingest lifecycle over APP-STATE PostgreSQL. One mutation = one unit of work."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Literal, NoReturn

import psycopg
from pydantic import BaseModel, ConfigDict, Field, field_validator
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateUnavailableError,
    ApplicationStateValidationError,
)
from application_state.ingest import repository as repo
from application_state.unit_of_work import unit_of_work
from graph_memory.ingestion.extraction_run import (
    FROZEN_COMPONENT_STATUSES,
    TERMINAL_EXTRACTION_RUN_STATUSES,
    ExtractionRun,
    ExtractionRunDiagnostics,
    ExtractionRunStatus,
    assert_allowed_extraction_run_transition,
    validate_extraction_run_lineage,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
)

_RECAP_CORRECTION_DERIVATION = "operator_recap_literal_evidence_correction_v1"
_RECAP_CANDIDATE_DERIVATION = "operator_recap_semantic_candidate_correction_v1"
_RECAP_CANDIDATE_DERIVATION_V2 = "operator_recap_semantic_candidate_correction_v2"
_RECAP_BASIS_SCHEMA = "dmb_recap_semantic_basis_v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class RecapSemanticBasisV1(BaseModel):
    """Exact canonical pins that SERVER re-proves before requesting CAS."""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)
    schema_: Literal["dmb_recap_semantic_basis_v1"] = Field(
        default=_RECAP_BASIS_SCHEMA, alias="schema"
    )
    parent_run_id: str
    parent_candidate_sha256: str
    correction_digest: str
    child_run_id: str
    candidate_uri: str
    candidate_sha256: str
    source_artifact_id: str
    source_uri: str
    source_revision_sha256: str
    span_index_uri: str
    span_index_sha256: str
    profile_id: str
    profile_version: Literal[RECAP_PROFILE_VERSION]
    campaign_id: str
    session_id: str

    @field_validator(
        "parent_candidate_sha256", "correction_digest", "candidate_sha256",
        "source_revision_sha256", "span_index_sha256",
    )
    @classmethod
    def _valid_sha(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("canonical SHA-256 must be 64 lowercase hex characters")
        return value

    @field_validator(
        "parent_run_id", "child_run_id", "candidate_uri", "source_artifact_id",
        "source_uri", "span_index_uri", "profile_id", "campaign_id", "session_id",
    )
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("basis identity field must be non-blank and trimmed")
        return value

    def digest(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json", by_alias=True), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class RecapSemanticBasisV2(BaseModel):
    """Distinct whole-candidate basis; V1 quote-only pins remain unchanged."""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)
    schema_: Literal["dmb_recap_semantic_basis_v2"] = Field(
        default="dmb_recap_semantic_basis_v2", alias="schema"
    )
    parent_run_id: str
    parent_candidate_sha256: str
    manifest_sha256: str
    child_run_id: str
    candidate_uri: str
    candidate_sha256: str
    source_artifact_id: str
    source_uri: str
    source_revision_sha256: str
    span_index_uri: str
    span_index_sha256: str
    profile_id: str
    profile_version: Literal[RECAP_PROFILE_VERSION]
    campaign_id: str
    session_id: str

    @field_validator(
        "parent_candidate_sha256", "manifest_sha256", "candidate_sha256",
        "source_revision_sha256", "span_index_sha256",
    )
    @classmethod
    def _valid_manifest_sha(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("basis SHA-256 must be lowercase hex")
        return value

    @field_validator(
        "parent_run_id", "child_run_id", "candidate_uri", "source_artifact_id",
        "source_uri", "span_index_uri", "profile_id", "campaign_id", "session_id",
    )
    @classmethod
    def _nonblank(cls, value: str) -> str:
        return RecapSemanticBasisV1._nonblank(value)

    def digest(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json", by_alias=True), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class RecapSemanticBasisV3(RecapSemanticBasisV2):
    """Bind V2 candidate operation identity and manifest schema explicitly."""

    schema_: Literal["dmb_recap_semantic_basis_v3"] = Field(
        default="dmb_recap_semantic_basis_v3", alias="schema"
    )
    derivation: Literal["operator_recap_semantic_candidate_correction_v2"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v2"]


class RecapSemanticDispositionCommandV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    state: Literal["accepted", "rejected"]
    review_decision_ref: str
    reviewer_id: str

    @field_validator("review_decision_ref", "reviewer_id")
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value or value != value.strip() or len(value) > 256:
            raise ValueError("decision identity must be non-blank, trimmed, and bounded")
        return value


@dataclass(frozen=True)
class CandidateRunLookup:
    kind: Literal["not_found", "unique", "ambiguous"]
    run: ExtractionRun | None = None


def _sha(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.removeprefix("sha256:").lower()
    return cleaned if _SHA256.fullmatch(cleaned) else None


@dataclass(frozen=True)
class IngestAuthoritySnapshot:
    run_count: int


def _require_run_id(run_id: str) -> str:
    cleaned = run_id.strip()
    if not cleaned:
        raise ApplicationStateValidationError("run_id is required")
    return cleaned


def _iso_now() -> str:
    return repo.iso_z(repo.now_utc()) or ""


def _connected_lineage(conn: psycopg.Connection, run: ExtractionRun) -> list[ExtractionRun]:
    connected_ids: set[str] = {run.run_id}
    changed = True
    records: dict[str, ExtractionRun] = {run.run_id: run}
    while changed:
        changed = False
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT run_id FROM ingest.run
                WHERE run_id = ANY(%s)
                   OR supersedes_run_id = ANY(%s)
                   OR superseded_by_run_id = ANY(%s)
                """,
                (list(connected_ids), list(connected_ids), list(connected_ids)),
            )
            found = {str(row[0]) for row in cur.fetchall()}
        missing = found - connected_ids
        if missing:
            for loaded in repo.get_runs_by_ids(conn, missing):
                records[loaded.run_id] = loaded
            connected_ids |= found
            changed = True
        for current in list(records.values()):
            for linked_id in (current.supersedes_run_id, current.superseded_by_run_id):
                if linked_id and linked_id not in connected_ids:
                    loaded = repo.get_run(conn, linked_id)
                    if loaded is None:
                        raise ApplicationStateIntegrityError(
                            f"ingest.run lineage pointer missing: {linked_id}"
                        )
                    records[loaded.run_id] = loaded
                    connected_ids.add(loaded.run_id)
                    changed = True
    return list(records.values())


def _validate_connected_lineage(conn: psycopg.Connection, run: ExtractionRun) -> None:
    try:
        validate_extraction_run_lineage(_connected_lineage(conn, run))
    except ValueError as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run lineage: {exc}"
        ) from exc


def _validate_catalog_lineage(conn: psycopg.Connection, records: list[ExtractionRun]) -> None:
    try:
        validate_extraction_run_lineage(records)
    except ValueError as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run lineage: {exc}"
        ) from exc


def _map_write_error(exc: BaseException, *, run_id: str) -> NoReturn:
    if isinstance(exc, UniqueViolation):
        raise ApplicationStateConflictError(
            f"extraction run already exists: {run_id}"
        ) from exc
    if isinstance(exc, ForeignKeyViolation):
        raise ApplicationStateIntegrityError(
            f"ingest.run lineage foreign key failed: {run_id}: {exc}"
        ) from exc
    raise exc


def inspect_ingest_authority() -> IngestAuthoritySnapshot:
    """Read-only catalog inspection for runtime preflight. No component-byte checks."""
    try:
        dsn = load_runtime_dsn()
    except ApplicationStateUnavailableError:
        raise
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        records = repo.list_runs(conn)
        _validate_catalog_lineage(conn, records)
        return IngestAuthoritySnapshot(run_count=len(records))


def get_extraction_run(run_id: str) -> ExtractionRun:
    canonical = _require_run_id(run_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.get_run(conn, canonical)
        if run is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        _validate_connected_lineage(conn, run)
        return run


def get_extraction_run_optional(run_id: str) -> ExtractionRun | None:
    canonical = _require_run_id(run_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.get_run(conn, canonical)
        if run is None:
            return None
        _validate_connected_lineage(conn, run)
        return run


def list_extraction_runs(
    *,
    campaign_id: str | None = None,
    session_id: str | None = None,
    source_artifact_id: str | None = None,
) -> list[ExtractionRun]:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        records = repo.list_runs(
            conn,
            campaign_id=campaign_id,
            session_id=session_id,
            source_artifact_id=source_artifact_id,
        )
        _validate_catalog_lineage(conn, records)
        return records


def lookup_extraction_run_by_candidate_component(
    *, uri: str, sha256: str
) -> CandidateRunLookup:
    """Resolve exact candidate ownership without filtering away changed runs."""
    if not isinstance(uri, str) or not uri.strip() or uri != uri.strip():
        raise ApplicationStateValidationError("candidate component URI is required")
    canonical_sha = _sha(sha256)
    if canonical_sha is None:
        raise ApplicationStateValidationError("candidate component SHA-256 is invalid")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        rows = repo.find_runs_by_candidate_component(
            conn, uri=uri, sha256=canonical_sha
        )
    if not rows:
        return CandidateRunLookup("not_found")
    if len(rows) > 1:
        return CandidateRunLookup("ambiguous")
    return CandidateRunLookup("unique", rows[0])


def _assert_recap_semantic_basis(
    child: ExtractionRun, parent: ExtractionRun, basis: RecapSemanticBasisV1 | RecapSemanticBasisV2 | RecapSemanticBasisV3
) -> None:
    """Prove every basis field against stored child/parent identity and refs."""
    lineage = child.lineage
    if (
        child.run_id != basis.child_run_id
        or child.status != ExtractionRunStatus.REVIEWABLE
        or child.source_domain != "recap"
        or parent.source_domain != "recap"
        or parent.status not in FROZEN_COMPONENT_STATUSES
        or not parent.has_required_review_components()
        or lineage.get("derivation") != (
            _RECAP_CANDIDATE_DERIVATION_V2 if isinstance(basis, RecapSemanticBasisV3)
            else _RECAP_CANDIDATE_DERIVATION if isinstance(basis, RecapSemanticBasisV2)
            else _RECAP_CORRECTION_DERIVATION
        )
        or lineage.get("parent_run_id") != parent.run_id
        or basis.parent_run_id != parent.run_id
        or parent.run_id == child.run_id
        or child.source_artifact_id != parent.source_artifact_id
        or child.source_artifact_id != basis.source_artifact_id
        or child.profile_id != parent.profile_id
        or child.profile_id != basis.profile_id
        or child.profile_id != f"{RECAP_PROFILE_ID}@{RECAP_PROFILE_VERSION}"
        or basis.profile_version != RECAP_PROFILE_VERSION
        or child.campaign_id != parent.campaign_id
        or child.campaign_id != basis.campaign_id
        or child.session_id != parent.session_id
        or child.session_id != basis.session_id
    ):
        raise ApplicationStateConflictError("recap semantic basis identity changed")
    candidate = child.components.get("candidate_graph")
    parent_candidate = parent.components.get("candidate_graph")
    source = child.components.get("source_artifact")
    parent_source = parent.components.get("source_artifact")
    spans = child.components.get("source_span_index")
    parent_spans = parent.components.get("source_span_index")
    if not all((candidate, parent_candidate, source, parent_source, spans, parent_spans)):
        raise ApplicationStateConflictError("recap semantic basis components are missing")
    if (
        candidate.uri != basis.candidate_uri
        or _sha(candidate.sha256) != basis.candidate_sha256
        or _sha(parent_candidate.sha256) != basis.parent_candidate_sha256
        or _sha(lineage.get("parent_candidate_sha256")) != basis.parent_candidate_sha256
        or (
            _sha(lineage.get("manifest_sha256")) != basis.manifest_sha256
            if isinstance(basis, RecapSemanticBasisV2)
            else _sha(lineage.get("correction_digest")) != basis.correction_digest
        )
        or source.uri != basis.source_uri
        or source.uri != parent_source.uri
        or _sha(source.sha256) != basis.source_revision_sha256
        or _sha(parent_source.sha256) != basis.source_revision_sha256
        or spans.uri != basis.span_index_uri
        or spans.uri != parent_spans.uri
        or _sha(spans.sha256) != basis.span_index_sha256
        or _sha(parent_spans.sha256) != basis.span_index_sha256
    ):
        raise ApplicationStateConflictError("recap semantic basis components changed")
    if isinstance(basis, RecapSemanticBasisV2):
        manifest = lineage.get("semantic_candidate_manifest")
        v3 = isinstance(basis, RecapSemanticBasisV3)
        if (
            not isinstance(manifest, dict)
            or set(manifest) != ({"schema", "node_description_replacements", "omitted_edge_ids", "session_action_replacements"} if v3 else {"schema", "node_description_replacements", "omitted_edge_ids"})
            or manifest.get("schema") != (basis.manifest_schema if v3 else "dmb_recap_semantic_candidate_manifest_v1")
            or (v3 and lineage.get("derivation") != basis.derivation)
            or not isinstance(manifest.get("node_description_replacements"), list)
            or not isinstance(manifest.get("omitted_edge_ids"), list)
            or (v3 and (not isinstance(manifest.get("session_action_replacements"), list) or len(manifest["session_action_replacements"]) != 1))
            or len(manifest["node_description_replacements"]) > 1
            or len(manifest["omitted_edge_ids"]) > 1
            or not (manifest["node_description_replacements"] or manifest["omitted_edge_ids"] or (v3 and manifest["session_action_replacements"]))
        ):
            raise ApplicationStateConflictError("recap semantic candidate manifest is missing")
        for item in manifest["node_description_replacements"]:
            if (
                not isinstance(item, dict)
                or set(item) != {"node_id", "original_description", "replacement_description"}
                or not all(isinstance(item[key], str) for key in item)
                or not item["node_id"].strip()
                or not item["replacement_description"].strip()
                or item["original_description"] == item["replacement_description"]
            ):
                raise ApplicationStateConflictError("recap semantic candidate manifest is malformed")
        if any(not isinstance(item, str) or not item.strip() for item in manifest["omitted_edge_ids"]):
            raise ApplicationStateConflictError("recap semantic candidate manifest is malformed")
        if v3:
            item = manifest["session_action_replacements"][0]
            if (
                not isinstance(item, dict)
                or set(item) != {"node_id", "action_index", "expected_old_text", "replacement_text"}
                or type(item.get("action_index")) is not int or item["action_index"] < 0
                or any(not isinstance(item.get(key), str) or not item[key].strip() or item[key] != item[key].strip() for key in ("node_id", "expected_old_text", "replacement_text"))
                or item["expected_old_text"] == item["replacement_text"]
                or (manifest["node_description_replacements"] and manifest["node_description_replacements"][0]["node_id"] != item["node_id"])
            ):
                raise ApplicationStateConflictError("recap semantic session action manifest is malformed")
        canonical = json.dumps(
            manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
            raise ApplicationStateConflictError("recap semantic candidate manifest changed")


def record_recap_semantic_disposition(
    run_id: str,
    *,
    expected_revision: int,
    basis: RecapSemanticBasisV1 | RecapSemanticBasisV2 | RecapSemanticBasisV3,
    decision: RecapSemanticDispositionCommandV1,
) -> ExtractionRun:
    """Single-use metadata-only CAS for a held recap correction child.

    An exact retry with the original revision returns the persisted receipt and
    time. A conflicting or stale decision never rewrites a frozen component.
    """
    canonical = _require_run_id(run_id)
    if expected_revision < 1 or canonical != basis.child_run_id:
        raise ApplicationStateValidationError("decision run/revision is invalid")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        child = repo.lock_run(conn, canonical)
        if child is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        parent_id = child.lineage.get("parent_run_id")
        parent = repo.get_run(conn, parent_id) if isinstance(parent_id, str) else None
        if parent is None:
            raise ApplicationStateConflictError("recap correction parent is missing")
        _assert_recap_semantic_basis(child, parent, basis)
        raw = child.lineage.get("semantic_disposition")
        if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw.get("version") != 1:
            raise ApplicationStateConflictError("recap semantic hold is missing or malformed")
        if _sha(raw.get("basis_sha256")) != basis.digest():
            raise ApplicationStateConflictError("recap semantic basis digest changed")
        if child.revision != expected_revision:
            if (
                child.revision == expected_revision + 1
                and raw.get("from_revision") == expected_revision
                and raw.get("state") == decision.state
                and raw.get("review_decision_ref") == decision.review_decision_ref
                and raw.get("reviewer_id") == decision.reviewer_id
                and isinstance(raw.get("decided_at"), str)
                and raw["decided_at"]
            ):
                return child
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {child.revision}"
            )
        if raw.get("state") != "held" or any(
            key in raw for key in ("review_decision_ref", "reviewer_id", "decided_at", "from_revision")
        ):
            raise ApplicationStateConflictError("recap semantic disposition is not held")
        if set(raw) - {"version", "state", "basis_sha256", "hold_code", "hold_ref"}:
            raise ApplicationStateConflictError("recap semantic hold contains unsupported fields")
        receipt = {
            **raw,
            "state": decision.state,
            "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": _iso_now(),
            "from_revision": expected_revision,
        }
        next_lineage = {**child.lineage, "semantic_disposition": receipt}
        updated = repo.cas_update_run_lineage(
            conn, run_id=canonical, expected_revision=expected_revision,
            lineage=next_lineage,
        )
        if updated is None:
            raise ApplicationStateConflictError("recap semantic disposition CAS failed")
        return updated


def create_extraction_run(run: ExtractionRun) -> ExtractionRun:
    if run.status in TERMINAL_EXTRACTION_RUN_STATUSES:
        raise ApplicationStateValidationError(
            "cannot create an extraction run directly in a terminal status"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.get_run(conn, run.run_id)
        if existing is not None:
            raise ApplicationStateConflictError(
                f"extraction run already exists: {run.run_id}"
            )
        try:
            inserted = repo.insert_run(conn, run)
        except (UniqueViolation, ForeignKeyViolation) as exc:
            _map_write_error(exc, run_id=run.run_id)
        _validate_connected_lineage(conn, inserted)
        return inserted


def update_extraction_run(
    run_id: str,
    *,
    status: ExtractionRunStatus,
    expected_revision: int,
    components: dict[str, Any] | None = None,
    diagnostics: ExtractionRunDiagnostics | None = None,
    lineage: dict[str, Any] | None = None,
) -> ExtractionRun:
    canonical = _require_run_id(run_id)
    if expected_revision < 1:
        raise ApplicationStateValidationError("expected_revision must be >= 1")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.lock_run(conn, canonical)
        if existing is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        if existing.revision != expected_revision:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        if existing.status in TERMINAL_EXTRACTION_RUN_STATUSES:
            raise ApplicationStateConflictError(
                f"extraction run status {existing.status.value} is terminal"
            )
        try:
            assert_allowed_extraction_run_transition(existing.status, status)
        except ValueError as exc:
            raise ApplicationStateValidationError(str(exc)) from exc
        if components is not None and existing.status in FROZEN_COMPONENT_STATUSES:
            raise ApplicationStateConflictError(
                "cannot replace components for a frozen extraction run"
            )
        next_components = existing.components if components is None else components
        next_diagnostics = existing.diagnostics if diagnostics is None else diagnostics
        next_lineage = existing.lineage if lineage is None else dict(lineage)
        updated = existing.model_copy(
            update={
                "status": status,
                "revision": existing.revision + 1,
                "updated_at": _iso_now(),
                "components": next_components,
                "diagnostics": next_diagnostics,
                "lineage": next_lineage,
            }
        )
        persisted = repo.cas_update_run(
            conn, updated, expected_revision=expected_revision
        )
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        _validate_connected_lineage(conn, persisted)
        return persisted


def supersede_extraction_run(
    run_id: str,
    *,
    expected_revision: int,
    successor: ExtractionRun,
) -> ExtractionRun:
    canonical = _require_run_id(run_id)
    if expected_revision < 1:
        raise ApplicationStateValidationError("expected_revision must be >= 1")
    if successor.supersedes_run_id != canonical:
        raise ApplicationStateValidationError(
            "successor.supersedes_run_id must equal the predecessor run_id"
        )
    if successor.status in TERMINAL_EXTRACTION_RUN_STATUSES:
        raise ApplicationStateValidationError(
            "cannot create an extraction run directly in a terminal status"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.lock_run(conn, canonical)
        if existing is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        if existing.revision != expected_revision:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        if existing.status == ExtractionRunStatus.SUPERSEDED:
            raise ApplicationStateConflictError("extraction run is already superseded")
        now = successor.updated_at or _iso_now()
        predecessor = existing.model_copy(
            update={
                "status": ExtractionRunStatus.SUPERSEDED,
                "revision": existing.revision + 1,
                "updated_at": now,
                "superseded_by_run_id": successor.run_id,
            }
        )
        if predecessor.superseded_by_run_id != successor.run_id:
            raise ApplicationStateIntegrityError("supersession lineage is not reciprocal")
        if successor.supersedes_run_id != predecessor.run_id:
            raise ApplicationStateIntegrityError("supersession lineage is not reciprocal")
        try:
            inserted = repo.insert_run(conn, successor)
            persisted = repo.cas_update_run(
                conn, predecessor, expected_revision=expected_revision
            )
        except (UniqueViolation, ForeignKeyViolation) as exc:
            _map_write_error(exc, run_id=successor.run_id)
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        _validate_connected_lineage(conn, inserted)
        return inserted
