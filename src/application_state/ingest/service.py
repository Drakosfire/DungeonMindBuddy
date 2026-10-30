"""Ingest lifecycle over APP-STATE PostgreSQL. One mutation = one unit of work."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable, Literal, NoReturn

import psycopg
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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
from graph_memory.candidate_graph_preview import NODE_TYPES

_RECAP_CORRECTION_DERIVATION = "operator_recap_literal_evidence_correction_v1"
_RECAP_CANDIDATE_DERIVATION = "operator_recap_semantic_candidate_correction_v1"
_RECAP_CANDIDATE_DERIVATION_V2 = "operator_recap_semantic_candidate_correction_v2"
_RECAP_CANDIDATE_DERIVATION_V3 = "operator_recap_semantic_candidate_correction_v3"
_RECAP_CANDIDATE_DERIVATION_V4 = "operator_recap_semantic_candidate_correction_v4"
_RECAP_CANDIDATE_DERIVATION_V5 = "operator_recap_semantic_candidate_correction_v5"
_RECAP_CANDIDATE_DERIVATION_V8 = "operator_recap_semantic_candidate_correction_v8"
_RECAP_CANDIDATE_DERIVATION_V9 = "operator_recap_semantic_candidate_correction_v9"
_RECAP_CANDIDATE_DERIVATION_V10 = "operator_recap_semantic_candidate_correction_v10"
_RECAP_CANDIDATE_DERIVATION_V11 = "operator_recap_semantic_candidate_correction_v11"
_RECAP_SOURCE_BINDING_DERIVATION_V11 = "operator_recap_semantic_source_binding_v11"
_RECAP_CANDIDATE_DERIVATION_V7 = "operator_recap_semantic_candidate_correction_v7"
_RECAP_CANDIDATE_DERIVATION_V6 = "operator_recap_semantic_candidate_correction_v6"
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
            self.model_dump(mode="json", by_alias=True, exclude_none=True), sort_keys=True,
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


class RecapSemanticBasisV4(RecapSemanticBasisV2):
    """Bind the exact edge-tuple correction derivation and manifest version."""

    schema_: Literal["dmb_recap_semantic_basis_v4"] = Field(
        default="dmb_recap_semantic_basis_v4", alias="schema"
    )
    derivation: Literal["operator_recap_semantic_candidate_correction_v3"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v3"]


class RecapSemanticBasisV5(RecapSemanticBasisV2):
    """Bind the exact evidence-span relocation derivation and manifest version."""

    schema_: Literal["dmb_recap_semantic_basis_v5"] = Field(
        default="dmb_recap_semantic_basis_v5", alias="schema"
    )
    derivation: Literal["operator_recap_semantic_candidate_correction_v4"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v4"]


class RecapSemanticBasisV6(RecapSemanticBasisV2):
    """Bind the atomic evidence replacement batch derivation and manifest."""

    schema_: Literal["dmb_recap_semantic_basis_v6"] = Field(
        default="dmb_recap_semantic_basis_v6", alias="schema"
    )
    derivation: Literal["operator_recap_semantic_candidate_correction_v5"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v5"]


class RecapSemanticBasisV7(RecapSemanticBasisV2):
    """Bind the one-to-two evidence ref split derivation and manifest."""

    schema_: Literal["dmb_recap_semantic_basis_v7"] = Field(
        default="dmb_recap_semantic_basis_v7", alias="schema"
    )
    derivation: Literal["operator_recap_semantic_candidate_correction_v6"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v6"]


class RecapSemanticBasisV8(RecapSemanticBasisV2):
    """Bind the atomic recap batch without changing earlier bases."""

    schema_: Literal["dmb_recap_semantic_basis_v8"] = Field(
        default="dmb_recap_semantic_basis_v8", alias="schema")
    derivation: Literal["operator_recap_semantic_candidate_correction_v7"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v7"]
    inherited_pc_proof_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RecapSemanticBasisV9(RecapSemanticBasisV2):
    """Bind final remediation operations and exact parent metadata revision."""

    schema_: Literal["dmb_recap_semantic_basis_v9"] = Field(
        default="dmb_recap_semantic_basis_v9", alias="schema")
    derivation: Literal["operator_recap_semantic_candidate_correction_v8"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v8"]
    expected_parent_revision: int = Field(strict=True, ge=1)
    inherited_pc_proof_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RecapSemanticBasisV10(RecapSemanticBasisV2):
    """Bind a reference-only PC correction to roster and native World head."""

    schema_: Literal["dmb_recap_semantic_basis_v10"] = Field(
        default="dmb_recap_semantic_basis_v10", alias="schema")
    derivation: Literal["operator_recap_semantic_candidate_correction_v9"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v9"]
    expected_parent_revision: int = Field(strict=True, ge=1)
    registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    roster_key: str = Field(min_length=1)
    world_id: str = Field(min_length=1)
    expected_head_revision_id: str = Field(min_length=1)


class RecapSemanticBasisV11(RecapSemanticBasisV2):
    """Bind additive frozen evidence without reusing the V9 PC basis meaning."""

    schema_: Literal["dmb_recap_semantic_basis_v11"] = Field(
        default="dmb_recap_semantic_basis_v11", alias="schema")
    derivation: Literal["operator_recap_semantic_candidate_correction_v10"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v10"]
    expected_parent_revision: int = Field(strict=True, ge=1)
    inherited_pc_proof_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RecapSemanticBasisV13(RecapSemanticBasisV2):
    """Bind one source-supported local actor recovery and exact edge preimages."""

    schema_: Literal["dmb_recap_semantic_basis_v13"] = Field(
        default="dmb_recap_semantic_basis_v13", alias="schema")
    derivation: Literal["operator_recap_semantic_candidate_correction_v11"]
    manifest_schema: Literal["dmb_recap_semantic_candidate_manifest_v11"]
    expected_parent_revision: int = Field(strict=True, ge=1)
    inherited_pc_proof_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


RecapSemanticOperationBasis = (
    RecapSemanticBasisV2 | RecapSemanticBasisV3 | RecapSemanticBasisV4
    | RecapSemanticBasisV5 | RecapSemanticBasisV6 | RecapSemanticBasisV7
    | RecapSemanticBasisV8 | RecapSemanticBasisV9 | RecapSemanticBasisV10
    | RecapSemanticBasisV11 | RecapSemanticBasisV13
)

_RECAP_OPERATION_BASIS_BY_REQUEST = {
    1: (_RECAP_CANDIDATE_DERIVATION, "dmb_recap_semantic_candidate_manifest_v1", RecapSemanticBasisV2),
    2: (_RECAP_CANDIDATE_DERIVATION_V2, "dmb_recap_semantic_candidate_manifest_v2", RecapSemanticBasisV3),
    3: (_RECAP_CANDIDATE_DERIVATION_V3, "dmb_recap_semantic_candidate_manifest_v3", RecapSemanticBasisV4),
    4: (_RECAP_CANDIDATE_DERIVATION_V4, "dmb_recap_semantic_candidate_manifest_v4", RecapSemanticBasisV5),
    5: (_RECAP_CANDIDATE_DERIVATION_V5, "dmb_recap_semantic_candidate_manifest_v5", RecapSemanticBasisV6),
    6: (_RECAP_CANDIDATE_DERIVATION_V6, "dmb_recap_semantic_candidate_manifest_v6", RecapSemanticBasisV7),
    7: (_RECAP_CANDIDATE_DERIVATION_V7, "dmb_recap_semantic_candidate_manifest_v7", RecapSemanticBasisV8),
    8: (_RECAP_CANDIDATE_DERIVATION_V8, "dmb_recap_semantic_candidate_manifest_v8", RecapSemanticBasisV9),
    9: (_RECAP_CANDIDATE_DERIVATION_V9, "dmb_recap_semantic_candidate_manifest_v9", RecapSemanticBasisV10),
    10: (_RECAP_CANDIDATE_DERIVATION_V10, "dmb_recap_semantic_candidate_manifest_v10", RecapSemanticBasisV11),
    11: (_RECAP_CANDIDATE_DERIVATION_V11, "dmb_recap_semantic_candidate_manifest_v11", RecapSemanticBasisV13),
}


class RecapSemanticBasisV12(BaseModel):
    """Source-snapshot envelope around an unchanged semantic-operation basis."""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)
    schema_: Literal["dmb_recap_semantic_basis_v12"] = Field(
        default="dmb_recap_semantic_basis_v12", alias="schema"
    )
    request_version: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    derivation: Literal["operator_recap_semantic_source_binding_v11"]
    operation_derivation: Literal[
        "operator_recap_semantic_candidate_correction_v1",
        "operator_recap_semantic_candidate_correction_v2",
        "operator_recap_semantic_candidate_correction_v3",
        "operator_recap_semantic_candidate_correction_v4",
        "operator_recap_semantic_candidate_correction_v5",
        "operator_recap_semantic_candidate_correction_v6",
        "operator_recap_semantic_candidate_correction_v7",
        "operator_recap_semantic_candidate_correction_v8",
        "operator_recap_semantic_candidate_correction_v9",
        "operator_recap_semantic_candidate_correction_v10",
        "operator_recap_semantic_candidate_correction_v11",
    ]
    operation_manifest_schema: Literal[
        "dmb_recap_semantic_candidate_manifest_v1",
        "dmb_recap_semantic_candidate_manifest_v2",
        "dmb_recap_semantic_candidate_manifest_v3",
        "dmb_recap_semantic_candidate_manifest_v4",
        "dmb_recap_semantic_candidate_manifest_v5",
        "dmb_recap_semantic_candidate_manifest_v6",
        "dmb_recap_semantic_candidate_manifest_v7",
        "dmb_recap_semantic_candidate_manifest_v8",
        "dmb_recap_semantic_candidate_manifest_v9",
        "dmb_recap_semantic_candidate_manifest_v10",
        "dmb_recap_semantic_candidate_manifest_v11",
    ]
    operation_basis: RecapSemanticOperationBasis
    parent_source_uri: str
    child_snapshot_uri: str
    source_artifact_id: str
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    span_index_uri: str
    span_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("operation_basis", mode="before")
    @classmethod
    def _parse_exact_operation_basis(cls, value: object, info):
        request_version = info.data.get("request_version")
        expected = _RECAP_OPERATION_BASIS_BY_REQUEST.get(request_version)
        if expected is None:
            raise ValueError("source-binding basis request version is unknown")
        model = expected[2]
        if isinstance(value, model):
            return value
        if not isinstance(value, dict) or value.get("schema") != model.model_fields["schema_"].default:
            raise ValueError("source-binding basis operation schema does not match its request")
        return model.model_validate(value, strict=True)

    @field_validator(
        "parent_source_uri", "child_snapshot_uri", "source_artifact_id",
        "span_index_uri",
    )
    @classmethod
    def _nonblank_binding_identity(cls, value: str) -> str:
        return RecapSemanticBasisV1._nonblank(value)

    @model_validator(mode="after")
    def _closed_version_mapping(self):
        expected_derivation, expected_manifest, expected_model = (
            _RECAP_OPERATION_BASIS_BY_REQUEST[self.request_version]
        )
        if (
            self.operation_derivation != expected_derivation
            or self.operation_manifest_schema != expected_manifest
            or type(self.operation_basis) is not expected_model
        ):
            raise ValueError("source-binding basis version mapping is inconsistent")
        operation = self.operation_basis
        if (
            hasattr(operation, "derivation")
            and operation.derivation != expected_derivation
        ):
            raise ValueError("source-binding operation derivation is inconsistent")
        operation_manifest_schema = getattr(operation, "manifest_schema", expected_manifest)
        if operation_manifest_schema != expected_manifest:
            raise ValueError("source-binding operation manifest schema is inconsistent")
        if (
            operation.source_uri != self.parent_source_uri
            or operation.source_artifact_id != self.source_artifact_id
            or operation.source_revision_sha256 != self.source_revision_sha256
            or operation.span_index_uri != self.span_index_uri
            or operation.span_index_sha256 != self.span_index_sha256
        ):
            raise ValueError("source-binding envelope does not match its operation basis")
        return self

    def digest(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json", by_alias=True), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

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


def _assert_recap_split_manifest(manifest: object, basis: RecapSemanticBasisV7) -> None:
    """Validate the stored bounded split shape independently of the HTTP model."""
    def invalid() -> None:
        raise ApplicationStateConflictError("recap semantic evidence ref split manifest is malformed")

    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema", "source_revision_sha256", "span_index_sha256", "evidence_ref_splits"}
        or manifest.get("schema") != basis.manifest_schema
        or manifest.get("source_revision_sha256") != basis.source_revision_sha256
        or manifest.get("span_index_sha256") != basis.span_index_sha256
        or not isinstance(manifest.get("evidence_ref_splits"), list)
        or len(manifest["evidence_ref_splits"]) != 1
    ):
        invalid()
    operation = manifest["evidence_ref_splits"][0]
    if (
        not isinstance(operation, dict)
        or set(operation) != {"record_kind", "record_id", "evidence_index", "expected_evidence_ref_sha256", "parts"}
        or operation.get("record_kind") not in ("node", "edge")
        or not isinstance(operation.get("record_id"), str)
        or not operation["record_id"] or operation["record_id"] != operation["record_id"].strip()
        or len(operation["record_id"]) > 256
        or any(ch in operation["record_id"] for ch in ("\r", "\n", "\t"))
        or type(operation.get("evidence_index")) is not int or operation["evidence_index"] < 0
        or not isinstance(operation.get("expected_evidence_ref_sha256"), str)
        or not _SHA256.fullmatch(operation["expected_evidence_ref_sha256"])
        or not isinstance(operation.get("parts"), list) or len(operation["parts"]) != 2
    ):
        invalid()
    span_ids = []
    indices = []
    for part in operation["parts"]:
        if (
            not isinstance(part, dict) or set(part) != {"source_span_ref_id", "quote_indices"}
            or not isinstance(part.get("source_span_ref_id"), str)
            or not part["source_span_ref_id"] or part["source_span_ref_id"] != part["source_span_ref_id"].strip()
            or len(part["source_span_ref_id"]) > 256
            or any(ch in part["source_span_ref_id"] for ch in ("\r", "\n", "\t"))
            or not isinstance(part.get("quote_indices"), list) or not 1 <= len(part["quote_indices"]) <= 16
            or any(type(index) is not int for index in part["quote_indices"])
        ):
            invalid()
        span_ids.append(part["source_span_ref_id"])
        indices.extend(part["quote_indices"])
    if span_ids[0] == span_ids[1] or indices != list(range(len(indices))):
        invalid()
    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
        raise ApplicationStateConflictError("recap semantic candidate manifest changed")



def _assert_recap_append_manifest(manifest: object, basis: RecapSemanticBasisV11) -> None:
    def invalid():
        raise ApplicationStateConflictError("recap evidence append manifest is malformed")
    keys = {"schema", "expected_parent_revision", "source_revision_sha256", "span_index_sha256",
            "profile_id", "evidence_appends", "node_description_replacements"}
    if not isinstance(manifest, dict) or set(manifest) != keys:
        invalid()
    if (manifest["schema"] != basis.manifest_schema
        or manifest["source_revision_sha256"] != basis.source_revision_sha256
        or manifest["span_index_sha256"] != basis.span_index_sha256
        or manifest["profile_id"] != basis.profile_id
        or type(manifest["expected_parent_revision"]) is not int
        or manifest["expected_parent_revision"] != basis.expected_parent_revision):
        invalid()
    appends, descriptions = manifest["evidence_appends"], manifest["node_description_replacements"]
    if not isinstance(appends, list) or not 1 <= len(appends) <= 2 or not isinstance(descriptions, list) or len(descriptions) > 1:
        invalid()
    seen = set()
    for row in appends:
        if not isinstance(row, dict) or set(row) != {"record_kind", "record_id", "expected_evidence_refs_sha256", "source_span_ref_id", "anchor_quotes"}:
            invalid()
        if (row["record_kind"] not in {"node", "edge"}
            or any(not isinstance(row[k], str) or not row[k] or row[k] != row[k].strip() or len(row[k]) > 256 or any(c in row[k] for c in "\r\n\t") for k in ("record_id", "source_span_ref_id"))
            or not isinstance(row["expected_evidence_refs_sha256"], str)
            or not _SHA256.fullmatch(row["expected_evidence_refs_sha256"])):
            invalid()
        quotes = row["anchor_quotes"]
        if not isinstance(quotes, list) or not 1 <= len(quotes) <= 16 or any(not isinstance(q, str) or not q or q != q.strip() or len(q) > 4096 for q in quotes) or len(set(quotes)) != len(quotes):
            invalid()
        target = (row["record_kind"], row["record_id"], row["source_span_ref_id"])
        if target in seen:
            invalid()
        seen.add(target)
    for row in descriptions:
        if (not isinstance(row, dict) or set(row) != {"node_id", "original_description", "replacement_description"}
            or any(not isinstance(row[k], str) or not row[k] or len(row[k]) > 4096 for k in row)
            or row["node_id"] != row["node_id"].strip()
            or row["replacement_description"] != row["replacement_description"].strip()
            or row["original_description"] == row["replacement_description"]):
            invalid()

def _assert_recap_actor_recovery_manifest(
    manifest: object, basis: RecapSemanticBasisV13,
) -> None:
    """Close the request and host-derived actor/edge ledger for request V11."""
    def invalid():
        raise ApplicationStateConflictError("recap actor recovery manifest is malformed")

    if (not isinstance(manifest, dict)
        or set(manifest) != {"schema", "request", "actor_node", "edge_changes"}
        or manifest.get("schema") != basis.manifest_schema):
        invalid()
    request = manifest.get("request")
    request_keys = {
        "schema", "parentRunId", "expectedParentRevision", "parentCandidateSha256",
        "sourceRevisionSha256", "spanIndexSha256", "profileId", "misboundActorId",
        "actorIntroduction", "affectedEdges",
    }
    if not isinstance(request, dict) or set(request) != request_keys:
        invalid()
    if (request.get("schema") != "dmb_recap_candidate_correction_request_v11"
        or request.get("parentRunId") != basis.parent_run_id
        or request.get("parentCandidateSha256") != basis.parent_candidate_sha256
        or request.get("expectedParentRevision") != basis.expected_parent_revision
        or request.get("sourceRevisionSha256") != basis.source_revision_sha256
        or request.get("spanIndexSha256") != basis.span_index_sha256
        or request.get("profileId") != basis.profile_id
        or not isinstance(request.get("misboundActorId"), str)
        or not request["misboundActorId"] or request["misboundActorId"] != request["misboundActorId"].strip()
        or len(request["misboundActorId"]) > 256
        or any(ch in request["misboundActorId"] for ch in "\r\n\t")
        or type(request.get("expectedParentRevision")) is not int
        or any(not isinstance(request.get(key), str) or not _SHA256.fullmatch(request[key])
               for key in ("parentCandidateSha256", "sourceRevisionSha256", "spanIndexSha256"))):
        invalid()
    intro = request.get("actorIntroduction")
    if not isinstance(intro, dict) or set(intro) != {
        "literalName", "sourceSpanRefId", "nameStart", "nameEnd",
        "replacementDescription", "descriptionAnchorQuotes",
    }:
        invalid()
    name, span_id = intro.get("literalName"), intro.get("sourceSpanRefId")
    start, end = intro.get("nameStart"), intro.get("nameEnd")
    description, quotes = intro.get("replacementDescription"), intro.get("descriptionAnchorQuotes")
    if (not isinstance(name, str) or not name or name != name.strip() or len(name) > 160
        or any(ch in name for ch in "\r\n\t")
        or not isinstance(span_id, str) or not span_id or span_id != span_id.strip()
        or len(span_id) > 256 or any(ch in span_id for ch in "\r\n\t")
        or type(start) is not int or type(end) is not int or start < 0 or end <= start or end - start != len(name)
        or not isinstance(description, str) or not description or description != description.strip() or len(description) > 4096
        or not isinstance(quotes, list) or not 1 <= len(quotes) <= 4
        or any(not isinstance(q, str) or not q or q != q.strip() or len(q) > 4096 for q in quotes)
        or len(set(quotes)) != len(quotes)):
        invalid()
    actor = manifest.get("actor_node")
    if (not isinstance(actor, dict)
        or set(actor) != {"node_id", "node_type", "label", "description", "importance",
                          "semantic_state", "proposed_action", "confidence", "evidence_refs", "corpus_ref"}
        or actor.get("node_type") != "character" or actor.get("label") != name
        or actor.get("description") != description or actor.get("importance") != "medium"
        or actor.get("proposed_action") != "create" or actor.get("confidence") != "medium"):
        invalid()
    local_payload = {
        "parent_run_id": basis.parent_run_id,
        "parent_candidate_sha256": basis.parent_candidate_sha256,
        "source_revision_sha256": basis.source_revision_sha256,
        "source_span_ref_id": span_id,
        "name_start": start, "name_end": end, "literal_name": name,
    }
    local_id = "node:recovered-actor:" + hashlib.sha256(
        json.dumps(local_payload, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode("utf-8") + b"\n"
    ).hexdigest()
    evidence = actor.get("evidence_refs")
    expected_quotes = list(dict.fromkeys([name, *quotes]))
    expected_evidence_fields = {
        "source_ref_id", "source_artifact_id", "source_anchor_id", "label",
        "evidence_role", "can_open_source", "can_highlight_span",
        "source_span_ref_id", "anchor_quotes",
    }
    if (actor.get("node_id") != local_id or actor.get("corpus_ref") is not None
        or actor.get("semantic_state") != {
            "canon_state": "played_canon", "lifecycle_state": "candidate",
            "evidence_role": "source_evidence", "authority_state": "system_derived",
            "visibility_state": "gm_private",
        }
        or not isinstance(evidence, list) or len(evidence) != 1
        or not isinstance(evidence[0], dict)
        or set(evidence[0]) != expected_evidence_fields
        or evidence[0].get("source_ref_id") != f"{basis.source_artifact_id}:text"
        or evidence[0].get("source_artifact_id") != basis.source_artifact_id
        or evidence[0].get("source_span_ref_id") != span_id
        or evidence[0].get("source_anchor_id") != f"anchor:{span_id}"
        or evidence[0].get("label") != span_id
        or evidence[0].get("evidence_role") != "source_evidence"
        or evidence[0].get("can_open_source") is not True
        or evidence[0].get("can_highlight_span") is not True
        or evidence[0].get("anchor_quotes") != expected_quotes):
        invalid()
    affected, changes = request.get("affectedEdges"), manifest.get("edge_changes")
    if not isinstance(affected, list) or len(affected) > 4 or not isinstance(changes, list) or len(changes) != len(affected):
        invalid()
    affected_by_id = {}
    edge_fields = {
        "action", "edgeId", "expectedEdgeSha256", "expectedEvidenceRefsSha256",
        "originalFromId", "originalToId", "originalPredicate", "misboundEndpoint",
        "sourceSpanRefId", "actorAnchorQuotes",
    }
    for row in affected:
        if not isinstance(row, dict) or set(row) != edge_fields:
            invalid()
        edge_id = row.get("edgeId")
        edge_quotes = row.get("actorAnchorQuotes")
        original_text_fields = (
            "originalFromId", "originalToId", "originalPredicate",
        )
        if (row.get("action") not in {"retarget", "omit"}
            or not isinstance(edge_id, str) or not edge_id or edge_id != edge_id.strip()
            or len(edge_id) > 256 or any(ch in edge_id for ch in "\r\n\t")
            or any(not isinstance(row.get(key), str) or not row[key]
                   or row[key] != row[key].strip() or len(row[key]) > 256
                   or any(ch in row[key] for ch in "\r\n\t")
                   for key in original_text_fields[:2])
            or not isinstance(row.get("originalPredicate"), str)
            or not row["originalPredicate"] or row["originalPredicate"] != row["originalPredicate"].strip()
            or len(row["originalPredicate"]) > 128
            or any(not isinstance(row.get(key), str) or not _SHA256.fullmatch(row[key])
                   for key in ("expectedEdgeSha256", "expectedEvidenceRefsSha256"))
            or row.get("sourceSpanRefId") != span_id
            or row.get("misboundEndpoint") not in {"from_id", "to_id"}
            or not isinstance(edge_quotes, list) or not 1 <= len(edge_quotes) <= 4
            or any(not isinstance(q, str) or not q or q != q.strip() or len(q) > 4096 or name not in q
                   for q in edge_quotes)
            or len(set(edge_quotes)) != len(edge_quotes)
            or edge_id in affected_by_id):
            invalid()
        affected_by_id[edge_id] = row
    seen = []
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"edge_id", "action", "before", "after"}:
            invalid()
        edge_id = change.get("edge_id")
        row = affected_by_id.get(edge_id)
        before, after = change.get("before"), change.get("after")
        if (row is None or change.get("action") != row["action"]
            or not isinstance(before, dict) or before.get("edge_id") != edge_id
            or hashlib.sha256(json.dumps(before, sort_keys=True, ensure_ascii=False,
                    separators=(",", ":")).encode("utf-8") + b"\n").hexdigest()
                != row["expectedEdgeSha256"]
            or hashlib.sha256(json.dumps(before.get("evidence_refs"), sort_keys=True, ensure_ascii=False,
                    separators=(",", ":")).encode("utf-8") + b"\n").hexdigest()
                != row["expectedEvidenceRefsSha256"]
            or before.get("from_node_id") != row["originalFromId"]
            or before.get("to_node_id") != row["originalToId"]
            or before.get("relationship_type") != row["originalPredicate"]
            or (before.get("from_node_id") if row["misboundEndpoint"] == "from_id"
                else before.get("to_node_id")) != request.get("misboundActorId")
            or not isinstance(before.get("evidence_refs"), list)
            or not any(isinstance(ref, dict) and ref.get("source_span_ref_id") == span_id
                       for ref in before["evidence_refs"])
            or (row["action"] == "omit" and after is not None)
            or (row["action"] == "retarget" and (
                not isinstance(after, dict) or after.get("edge_id") != edge_id
                or (after.get("from_node_id") if row["misboundEndpoint"] == "from_id"
                    else after.get("to_node_id")) != local_id
                or {**before, ("from_node_id" if row["misboundEndpoint"] == "from_id" else "to_node_id"): local_id} != after
            ))):
            invalid()
        seen.append(edge_id)
    if seen != sorted(affected_by_id):
        invalid()
    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
        raise ApplicationStateConflictError("recap actor recovery manifest digest changed")


def _assert_recap_atomic_manifest(manifest: object, basis: RecapSemanticBasisV8 | RecapSemanticBasisV9) -> None:
    def invalid():
        raise ApplicationStateConflictError("recap atomic manifest is malformed")
    final_batch = isinstance(basis, RecapSemanticBasisV9)
    limits = {"node_description_replacements": 8, "node_label_replacements": 4,
              "edge_tuple_replacements": 2, "evidence_replacements": 2, "edge_omissions": 3}
    pins = {"schema", "source_revision_sha256", "span_index_sha256", "profile_id"}
    if final_batch:
        limits.update(node_description_replacements=10, node_label_replacements=8,
            edge_tuple_replacements=4, edge_omissions=4, node_type_replacements=6, node_omissions=1)
        pins.add("expected_parent_revision")
    if not isinstance(manifest, dict) or set(manifest) != set(limits) | pins:
        invalid()
    if manifest["schema"] != basis.manifest_schema or manifest["source_revision_sha256"] != basis.source_revision_sha256 or manifest["span_index_sha256"] != basis.span_index_sha256 or manifest["profile_id"] != basis.profile_id:
        invalid()
    if final_batch and (type(manifest["expected_parent_revision"]) is not int or manifest["expected_parent_revision"] != basis.expected_parent_revision):
        invalid()
    total = 0
    fields = {
        "node_description_replacements": {"node_id", "original_description", "replacement_description"},
        "node_label_replacements": {"node_id", "original_label", "replacement_label"},
        "edge_tuple_replacements": {"edge_id", "expected_tuple", "replacement_tuple"},
        "edge_omissions": {"edge_id", "expected_edge_sha256"},
        "evidence_replacements": {"record_kind", "record_id", "evidence_index", "expected_evidence_ref_sha256", "source_span_ref_id", "anchor_quotes"},
    }
    if final_batch:
        fields.update(node_type_replacements={"node_id", "expected_node_type", "replacement_node_type"},
                      node_omissions={"node_id", "expected_node_sha256"})
    for key, limit in limits.items():
        rows = manifest[key]
        if not isinstance(rows, list) or len(rows) > limit:
            invalid()
        total += len(rows)
        coordinates = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != fields[key]:
                invalid()
            def text(value, maximum=256):
                return isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= maximum and not any(c in value for c in ("\r", "\n", "\t"))
            if key == "evidence_replacements":
                if not text(row["record_id"]) or not text(row["source_span_ref_id"]) or not isinstance(row["expected_evidence_ref_sha256"], str) or not _SHA256.fullmatch(row["expected_evidence_ref_sha256"]) or not isinstance(row["anchor_quotes"], list) or not 1 <= len(row["anchor_quotes"]) <= 16 or any(not isinstance(q, str) or not q or q != q.strip() or len(q) > 4096 for q in row["anchor_quotes"]):
                    invalid()
            elif not text(row.get("node_id", row.get("edge_id"))):
                invalid()
            if key in {"node_description_replacements", "node_label_replacements"}:
                field = "description" if key == "node_description_replacements" else "label"
                if any(not isinstance(row[prefix + field], str) or not row[prefix + field] or len(row[prefix + field]) > 4096 for prefix in ("original_", "replacement_")) or row["original_" + field] == row["replacement_" + field]:
                    invalid()
            if key == "node_type_replacements":
                if any(not text(row[field], 64) or row[field] != row[field].lower() for field in ("expected_node_type", "replacement_node_type")) or row["expected_node_type"] == row["replacement_node_type"]:
                    invalid()
            if key == "node_omissions":
                if not isinstance(row["expected_node_sha256"], str) or not _SHA256.fullmatch(row["expected_node_sha256"]):
                    invalid()
            if key == "edge_tuple_replacements":
                for tuple_key in ("expected_tuple", "replacement_tuple"):
                    value = row[tuple_key]
                    if not isinstance(value, dict) or set(value) != {"from_node_id", "relationship_type", "to_node_id", "label"} or any(not text(v, 4096 if k == "label" else 256) for k, v in value.items()):
                        invalid()
                if row["expected_tuple"] == row["replacement_tuple"]:
                    invalid()
            if key == "evidence_replacements":
                if row["record_kind"] not in {"node", "edge"} or type(row["evidence_index"]) is not int or row["evidence_index"] < 0:
                    invalid()
                coordinate = (row["record_kind"], row["record_id"], row["evidence_index"])
            else:
                coordinate = row.get("node_id", row.get("edge_id"))
            try:
                if coordinate in coordinates:
                    invalid()
                coordinates.append(coordinate)
            except TypeError:
                invalid()
        if key == "edge_omissions":
            if any(not isinstance(x["expected_edge_sha256"], str) or not _SHA256.fullmatch(x["expected_edge_sha256"]) for x in rows):
                invalid()
    if not 1 <= total <= (35 if final_batch else 19):
        invalid()
    omitted = {x["edge_id"] for x in manifest["edge_omissions"]}
    edited = {x["edge_id"] for x in manifest["edge_tuple_replacements"]} | {x["record_id"] for x in manifest["evidence_replacements"] if x["record_kind"] == "edge"}
    if omitted & edited:
        invalid()
    if final_batch:
        omitted_nodes = {x["node_id"] for x in manifest["node_omissions"]}
        edited_nodes = {x["node_id"] for key in ("node_description_replacements", "node_label_replacements", "node_type_replacements") for x in manifest[key]} | {x["record_id"] for x in manifest["evidence_replacements"] if x["record_kind"] == "node"}
        if omitted_nodes & edited_nodes:
            invalid()
    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
    if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
        raise ApplicationStateConflictError("recap atomic manifest changed")

def _assert_recap_pc_manifest(manifest: object, basis: RecapSemanticBasisV10) -> None:
    """Independently validate the private reference manifest at metadata CAS."""
    keys = {"schema", "expected_parent_revision", "source_revision_sha256", "span_index_sha256",
            "profile_id", "registry_path", "registry_sha256", "roster_session", "roster_key",
            "world_id", "expected_head_revision_id", "reviewer_id", "review_decision_ref", "attachments"}
    if not isinstance(manifest, dict) or set(manifest) != keys:
        raise ApplicationStateConflictError("PC reference manifest is malformed")
    if (manifest["schema"] != basis.manifest_schema
        or manifest["expected_parent_revision"] != basis.expected_parent_revision
        or manifest["source_revision_sha256"] != basis.source_revision_sha256
        or manifest["span_index_sha256"] != basis.span_index_sha256
        or manifest["profile_id"] != basis.profile_id
        or manifest["registry_sha256"] != basis.registry_sha256
        or manifest["roster_key"] != basis.roster_key
        or manifest["world_id"] != basis.world_id
        or manifest["expected_head_revision_id"] != basis.expected_head_revision_id
        or type(manifest["roster_session"]) is not int or manifest["roster_session"] < 1
        or not isinstance(manifest["registry_path"], str) or not manifest["registry_path"].startswith("corpus/")
        or any(not isinstance(manifest[key], str) or not manifest[key].strip()
               for key in ("reviewer_id", "review_decision_ref"))):
        raise ApplicationStateConflictError("PC reference basis changed")
    rows = manifest["attachments"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 6:
        raise ApplicationStateConflictError("PC attachment count is invalid")
    ids, refs = set(), set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"node_id", "expected_corpus_ref", "corpus_ref",
            "source_span_ref_id", "anchor_quote", "pc_mention", "native_object_id"}
            or row["expected_corpus_ref"] is not None or not isinstance(row["corpus_ref"], dict)
            or set(row["corpus_ref"]) != {"type", "ref_id", "resolution"}
            or row["corpus_ref"].get("type") != "pc"
            or row["corpus_ref"].get("resolution") != "resolved"):
            raise ApplicationStateConflictError("PC attachment shape is invalid")
        ref = row["corpus_ref"].get("ref_id")
        if (not isinstance(ref, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,127}", ref)
            or row["native_object_id"] != f"pc:{ref}"
            or any(not isinstance(row[key], str) or not row[key].strip()
                   for key in ("node_id", "source_span_ref_id", "anchor_quote", "pc_mention"))
            or row["node_id"] in ids or ref in refs):
            raise ApplicationStateConflictError("PC attachment identity is invalid")
        ids.add(row["node_id"])
        refs.add(ref)
    canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8") + b"\n"
    if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
        raise ApplicationStateConflictError("PC reference manifest changed")


def _inherited_pc_proof_sha(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8") + b"\n"
    return hashlib.sha256(canonical).hexdigest()


def _assert_inherited_pc_basis(
    child: ExtractionRun, parent: ExtractionRun,
    basis: RecapSemanticBasisV8 | RecapSemanticBasisV9 | RecapSemanticBasisV11 | RecapSemanticBasisV13,
    get_ancestor: Callable[[str], ExtractionRun | None] | None,
) -> None:
    """Independently bind persisted proof to immutable APP-STATE ancestry."""
    corrections = {
        _RECAP_CANDIDATE_DERIVATION, _RECAP_CANDIDATE_DERIVATION_V2,
        _RECAP_CANDIDATE_DERIVATION_V3, _RECAP_CANDIDATE_DERIVATION_V4,
        _RECAP_CANDIDATE_DERIVATION_V5, _RECAP_CANDIDATE_DERIVATION_V6,
        _RECAP_CANDIDATE_DERIVATION_V7, _RECAP_CANDIDATE_DERIVATION_V8,
        _RECAP_CANDIDATE_DERIVATION_V9, _RECAP_CANDIDATE_DERIVATION_V10,
        _RECAP_CANDIDATE_DERIVATION_V11,
        _RECAP_SOURCE_BINDING_DERIVATION_V11,
    }
    seen: set[str] = set()
    links: list[dict[str, object]] = []
    introductions: list[tuple[int, ExtractionRun, dict, dict]] = []
    omitted: set[str] = set()
    current = child
    while current.lineage.get("derivation") in corrections:
        if current.run_id in seen or len(seen) >= 64:
            raise ApplicationStateConflictError("inherited PC lineage is cyclic or unbounded")
        seen.add(current.run_id)
        lineage = current.lineage
        projected_outer = lineage.get("_source_binding_outer_derivation")
        outer_binding = (
            lineage.get("derivation") == _RECAP_SOURCE_BINDING_DERIVATION_V11
            or projected_outer == _RECAP_SOURCE_BINDING_DERIVATION_V11
        )
        operation_derivation = (
            lineage.get("operation_derivation")
            if lineage.get("derivation") == _RECAP_SOURCE_BINDING_DERIVATION_V11
            else lineage.get("derivation")
        )
        identity_derivation = (
            projected_outer if projected_outer == _RECAP_SOURCE_BINDING_DERIVATION_V11
            else lineage.get("derivation")
        )
        parent_id = lineage.get("parent_run_id")
        manifest = lineage.get("semantic_candidate_manifest")
        if not isinstance(parent_id, str) or not parent_id or not isinstance(manifest, dict):
            raise ApplicationStateConflictError("inherited PC lineage manifest is missing")
        previous = parent if parent.run_id == parent_id else (
            get_ancestor(parent_id) if get_ancestor is not None else None)
        if previous is None or previous.run_id in seen:
            raise ApplicationStateConflictError("inherited PC parent is missing or cyclic")
        current_candidate = current.components.get("candidate_graph")
        previous_candidate = previous.components.get("candidate_graph")
        source = current.components.get("source_artifact")
        previous_source = previous.components.get("source_artifact")
        spans = current.components.get("source_span_index")
        previous_spans = previous.components.get("source_span_index")
        if not all((current_candidate, previous_candidate, source, previous_source, spans, previous_spans)):
            raise ApplicationStateConflictError("inherited PC components are missing")
        manifest_sha = _inherited_pc_proof_sha(manifest)
        parent_sha = _sha(previous_candidate.sha256)
        candidate_sha = _sha(current_candidate.sha256)
        if (lineage.get("manifest_sha256") != manifest_sha
            or lineage.get("parent_candidate_sha256") != parent_sha
            or not candidate_sha or not parent_sha
            or (not outer_binding and source != previous_source)
            or (outer_binding and (
                source.sha256 != previous_source.sha256
                or (projected_outer is None and source.uri == previous_source.uri)
            ))
            or spans != previous_spans
            or current.campaign_id != previous.campaign_id
            or current.session_id != previous.session_id
            or current.source_artifact_id != previous.source_artifact_id):
            raise ApplicationStateConflictError("inherited PC lineage pins changed")
        if outer_binding and projected_outer is None:
            try:
                source_basis = RecapSemanticBasisV12.model_validate(
                    lineage.get("semantic_source_binding_basis_v12"), strict=True,
                )
            except (TypeError, ValueError) as exc:
                raise ApplicationStateConflictError(
                    "inherited PC source-binding basis is malformed"
                ) from exc
            if (
                source_basis.model_dump(mode="json", by_alias=True)
                != lineage.get("semantic_source_binding_basis_v12")
                or source_basis.operation_derivation != operation_derivation
                or source_basis.operation_manifest_schema != manifest.get("schema")
                or lineage.get("operation_manifest_schema") != manifest.get("schema")
                or source_basis.operation_basis.child_run_id != current.run_id
                or source_basis.operation_basis.parent_run_id != previous.run_id
                or source_basis.child_snapshot_uri != source.uri
                or source_basis.parent_source_uri != previous_source.uri
                or source_basis.source_revision_sha256 != _sha(source.sha256)
                or source_basis.source_revision_sha256 != _sha(previous_source.sha256)
                or source_basis.span_index_uri != spans.uri
                or source_basis.span_index_sha256 != _sha(spans.sha256)
            ):
                raise ApplicationStateConflictError(
                    "inherited PC source-binding pins changed"
                )
        link = {
            "run_id": current.run_id, "parent_run_id": parent_id,
            "derivation": identity_derivation, "manifest_sha256": manifest_sha,
            "candidate_sha256": candidate_sha, "parent_candidate_sha256": parent_sha,
        }
        if outer_binding:
            link["operation_derivation"] = operation_derivation
        links.append(link)
        if operation_derivation == _RECAP_CANDIDATE_DERIVATION_V8:
            operations = manifest.get("node_omissions")
            if not isinstance(operations, list):
                raise ApplicationStateConflictError("inherited PC node omission basis changed")
            omitted.update(row["node_id"] for row in operations
                           if isinstance(row, dict) and isinstance(row.get("node_id"), str))
        if operation_derivation == _RECAP_CANDIDATE_DERIVATION_V9:
            rows = manifest.get("attachments")
            if (manifest.get("schema") != "dmb_recap_semantic_candidate_manifest_v9"
                or not isinstance(rows, list) or not 1 <= len(rows) <= 6
                or any(not isinstance(row, dict) or not isinstance(row.get("node_id"), str)
                       for row in rows)
                or len({row["node_id"] for row in rows}) != len(rows)
                or manifest.get("source_revision_sha256") != _sha(source.sha256)
                or manifest.get("span_index_sha256") != _sha(spans.sha256)):
                raise ApplicationStateConflictError("inherited PC introduction is malformed")
            for row in rows:
                if (not isinstance(row, dict)
                    or any(not isinstance(row.get(key), str) or not row[key]
                           for key in ("node_id", "native_object_id", "source_span_ref_id",
                                       "anchor_quote", "pc_mention"))
                    or not isinstance(row.get("corpus_ref"), dict)
                    or row["corpus_ref"].get("type") != "pc"
                    or row["corpus_ref"].get("resolution") != "resolved"
                    or not isinstance(manifest.get("world_id"), str)
                    or not manifest["world_id"]):
                    raise ApplicationStateConflictError("inherited PC attachment is malformed")
                if row["node_id"] not in omitted:
                    introductions.append((len(links), current, manifest, row))
        current = previous

    expected_rows: list[dict] = []
    for depth, origin, manifest, row in introductions:
        expected_rows.append({
            "node_id": row["node_id"], "corpus_ref": row["corpus_ref"],
            "native_object_id": row["native_object_id"],
            "origin_world_id": manifest["world_id"],
            "origin_run_id": origin.run_id,
            "origin_manifest_sha256": origin.lineage["manifest_sha256"],
            "source_revision_sha256": manifest["source_revision_sha256"],
            "span_index_sha256": manifest["span_index_sha256"],
            "source_span_ref_id": row["source_span_ref_id"],
            "anchor_quote": row["anchor_quote"], "pc_mention": row["pc_mention"],
            "lineage_links": links[:depth],
        })
    expected_rows.sort(key=lambda row: row["node_id"])
    digest = basis.inherited_pc_proof_sha256
    stored = child.lineage.get("inherited_pc_proof")
    if not expected_rows:
        if digest is not None or stored is not None:
            raise ApplicationStateConflictError("inherited PC proof is unexpected")
        return
    expected = {"schema": "dmb_inherited_pc_reference_proof_v1",
                "final_candidate_sha256": basis.candidate_sha256, "rows": expected_rows}
    if (not isinstance(digest, str) or not _SHA256.fullmatch(digest)
        or stored != expected or _inherited_pc_proof_sha(stored) != digest):
        raise ApplicationStateConflictError("inherited PC proof is missing or changed")


def _assert_recap_semantic_basis(
    child: ExtractionRun,
    parent: ExtractionRun,
    basis: RecapSemanticBasisV1 | RecapSemanticBasisV2 | RecapSemanticBasisV3 | RecapSemanticBasisV4 | RecapSemanticBasisV5 | RecapSemanticBasisV6 | RecapSemanticBasisV7 | RecapSemanticBasisV8 | RecapSemanticBasisV9 | RecapSemanticBasisV10 | RecapSemanticBasisV11 | RecapSemanticBasisV12 | RecapSemanticBasisV13,
    get_ancestor: Callable[[str], ExtractionRun | None] | None = None,
) -> None:
    """Prove every basis field against stored child/parent identity and refs."""
    if isinstance(basis, RecapSemanticBasisV12):
        _assert_recap_source_binding_basis(child, parent, basis, get_ancestor)
        return
    lineage = child.lineage
    if (
        child.run_id != basis.child_run_id
        or child.status != ExtractionRunStatus.REVIEWABLE
        or child.source_domain != "recap"
        or parent.source_domain != "recap"
        or parent.status not in FROZEN_COMPONENT_STATUSES
        or not parent.has_required_review_components()
        or lineage.get("derivation") != (
            _RECAP_CANDIDATE_DERIVATION_V11 if isinstance(basis, RecapSemanticBasisV13)
            else _RECAP_CANDIDATE_DERIVATION_V10 if isinstance(basis, RecapSemanticBasisV11)
            else _RECAP_CANDIDATE_DERIVATION_V9 if isinstance(basis, RecapSemanticBasisV10)
            else _RECAP_CANDIDATE_DERIVATION_V8 if isinstance(basis, RecapSemanticBasisV9)
            else _RECAP_CANDIDATE_DERIVATION_V7 if isinstance(basis, RecapSemanticBasisV8)
            else _RECAP_CANDIDATE_DERIVATION_V6 if isinstance(basis, RecapSemanticBasisV7)
            else _RECAP_CANDIDATE_DERIVATION_V5 if isinstance(basis, RecapSemanticBasisV6)
            else _RECAP_CANDIDATE_DERIVATION_V4 if isinstance(basis, RecapSemanticBasisV5)
            else _RECAP_CANDIDATE_DERIVATION_V3 if isinstance(basis, RecapSemanticBasisV4)
            else _RECAP_CANDIDATE_DERIVATION_V2 if isinstance(basis, RecapSemanticBasisV3)
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
    if isinstance(basis, RecapSemanticBasisV13):
        if parent.revision != basis.expected_parent_revision:
            raise ApplicationStateConflictError("actor recovery parent revision changed")
        _assert_recap_actor_recovery_manifest(lineage.get("semantic_candidate_manifest"), basis)
        _assert_inherited_pc_basis(child, parent, basis, get_ancestor)
        return
    if isinstance(basis, RecapSemanticBasisV11):
        if parent.revision != basis.expected_parent_revision:
            raise ApplicationStateConflictError("evidence append parent revision changed")
        _assert_recap_append_manifest(lineage.get("semantic_candidate_manifest"), basis)
        _assert_inherited_pc_basis(child, parent, basis, get_ancestor)
        return
    if isinstance(basis, RecapSemanticBasisV10):
        if parent.revision != basis.expected_parent_revision:
            raise ApplicationStateConflictError("PC reference parent revision changed")
        _assert_recap_pc_manifest(lineage.get("semantic_candidate_manifest"), basis)
        return
    if isinstance(basis, RecapSemanticBasisV9):
        if parent.revision != basis.expected_parent_revision:
            raise ApplicationStateConflictError("final batch parent revision changed")
        _assert_recap_atomic_manifest(lineage.get("semantic_candidate_manifest"), basis)
        _assert_inherited_pc_basis(child, parent, basis, get_ancestor)
        return
    if isinstance(basis, RecapSemanticBasisV8):
        _assert_recap_atomic_manifest(lineage.get("semantic_candidate_manifest"), basis)
        _assert_inherited_pc_basis(child, parent, basis, get_ancestor)
        return
    if isinstance(basis, RecapSemanticBasisV7):
        _assert_recap_split_manifest(lineage.get("semantic_candidate_manifest"), basis)
        return
    if isinstance(basis, RecapSemanticBasisV2):
        manifest = lineage.get("semantic_candidate_manifest")
        action_manifest = isinstance(basis, RecapSemanticBasisV3)
        tuple_manifest = isinstance(basis, RecapSemanticBasisV4)
        span_manifest = isinstance(basis, (RecapSemanticBasisV5, RecapSemanticBasisV6))
        label_manifest = (
            not (action_manifest or tuple_manifest or span_manifest)
            and isinstance(manifest, dict)
            and "node_label_replacements" in manifest
        )
        expected_manifest_keys = (
            {"schema", "evidence_span_replacements"}
            if span_manifest
            else
            {"schema", "edge_tuple_replacements"}
            if tuple_manifest
            else {"schema", "node_description_replacements", "omitted_edge_ids", "session_action_replacements"}
            if action_manifest
            else {"schema", "node_description_replacements", "omitted_edge_ids"}
        )
        node_omission = isinstance(manifest, dict) and "node_omissions" in manifest
        if node_omission and not (action_manifest or tuple_manifest or span_manifest):
            expected_manifest_keys.add("node_omissions")
        tuple_manifest_keys_valid = (
            isinstance(manifest, dict)
            and set(manifest) in (
                {"schema", "edge_tuple_replacements"},
                {"schema", "edge_tuple_replacements", "node_type_replacements"},
            )
        ) if tuple_manifest else True
        if label_manifest:
            expected_manifest_keys.add("node_label_replacements")
        expected_manifest_schema = (
            basis.manifest_schema if action_manifest or tuple_manifest or span_manifest
            else "dmb_recap_semantic_candidate_manifest_v1"
        )
        if (
            not isinstance(manifest, dict)
            or (not tuple_manifest and set(manifest) != expected_manifest_keys)
            or not tuple_manifest_keys_valid
            or manifest.get("schema") != expected_manifest_schema
            or ((action_manifest or tuple_manifest or span_manifest) and lineage.get("derivation") != basis.derivation)
            or (not (tuple_manifest or span_manifest) and not isinstance(manifest.get("node_description_replacements"), list))
            or (not (tuple_manifest or span_manifest) and not isinstance(manifest.get("omitted_edge_ids"), list))
            or (action_manifest and (not isinstance(manifest.get("session_action_replacements"), list) or len(manifest["session_action_replacements"]) != 1))
            or (not (tuple_manifest or span_manifest) and len(manifest["node_description_replacements"]) > 1)
            or (not (tuple_manifest or span_manifest) and len(manifest["omitted_edge_ids"]) > 1)
            or (label_manifest and (not isinstance(manifest.get("node_label_replacements"), list) or len(manifest["node_label_replacements"]) > 1))
            or (not (tuple_manifest or span_manifest) and not (manifest["node_description_replacements"] or manifest["omitted_edge_ids"] or (action_manifest and manifest["session_action_replacements"]) or (label_manifest and manifest["node_label_replacements"]) or node_omission))
            or (tuple_manifest and (not isinstance(manifest.get("edge_tuple_replacements"), list) or not 1 <= len(manifest["edge_tuple_replacements"]) <= 7))
            or (tuple_manifest and "node_type_replacements" in manifest and (
                not isinstance(manifest.get("node_type_replacements"), list)
                or len(manifest["node_type_replacements"]) != 1
            ))
            or (span_manifest and (
                not isinstance(manifest.get("evidence_span_replacements"), list)
                or not 1 <= len(manifest["evidence_span_replacements"]) <= (7 if isinstance(basis, RecapSemanticBasisV6) else 1)
            ))
        ):
            raise ApplicationStateConflictError("recap semantic candidate manifest is missing")
        if node_omission:
            operations = manifest["node_omissions"]
            if (
                not isinstance(operations, list) or len(operations) != 1
                or manifest["node_description_replacements"] or manifest["omitted_edge_ids"]
                or manifest.get("node_label_replacements")
            ):
                raise ApplicationStateConflictError("recap semantic node omission manifest is malformed")
            operation = operations[0]
            if (
                not isinstance(operation, dict)
                or set(operation) != {"node_id", "expected_node_sha256"}
                or not isinstance(operation.get("node_id"), str)
                or not operation["node_id"] or operation["node_id"] != operation["node_id"].strip()
                or len(operation["node_id"]) > 256
                or any(ch in operation["node_id"] for ch in ("\r", "\n", "\t"))
                or not isinstance(operation.get("expected_node_sha256"), str)
                or len(operation["expected_node_sha256"]) != 64
                or any(ch not in "0123456789abcdef" for ch in operation["expected_node_sha256"])
            ):
                raise ApplicationStateConflictError("recap semantic node omission manifest is malformed")
        if not (tuple_manifest or span_manifest):
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
            if label_manifest:
                for item in manifest["node_label_replacements"]:
                    if (
                        not isinstance(item, dict)
                        or set(item) != {"node_id", "original_label", "replacement_label"}
                        or not all(isinstance(item[key], str) for key in item)
                        or any(
                            not item[key].strip() or item[key] != item[key].strip() or len(item[key]) > 4096
                            for key in item
                        )
                        or item["original_label"] == item["replacement_label"]
                    ):
                        raise ApplicationStateConflictError("recap semantic node label manifest is malformed")
        if action_manifest:
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
        if span_manifest:
            seen_span_targets: set[tuple[str, str, int]] = set()
            for item in manifest["evidence_span_replacements"]:
                string_fields = (
                    "record_id", "expected_source_ref_id", "expected_source_artifact_id",
                    "expected_source_span_ref_id", "replacement_source_span_ref_id",
                )
                quote_fields = ("expected_anchor_quotes", "replacement_anchor_quotes")
                if (
                    not isinstance(item, dict)
                    or set(item) != {"record_kind", "evidence_index", *string_fields, *quote_fields}
                    or not isinstance(item.get("record_kind"), str)
                    or item.get("record_kind") not in {"node", "edge"}
                    or type(item.get("evidence_index")) is not int or item["evidence_index"] < 0
                    or item.get("expected_source_artifact_id") != basis.source_artifact_id
                    or any(
                        not isinstance(item.get(key), str) or not item[key].strip()
                        or item[key] != item[key].strip() or len(item[key]) > 256
                        for key in string_fields
                    )
                    or (
                        item["expected_source_span_ref_id"] == item["replacement_source_span_ref_id"]
                        and item["expected_anchor_quotes"] == item["replacement_anchor_quotes"]
                    )
                    or (
                        isinstance(basis, RecapSemanticBasisV5)
                        and item["expected_source_span_ref_id"] == item["replacement_source_span_ref_id"]
                    )
                    or any(
                        not isinstance(item.get(key), list) or not 1 <= len(item[key]) <= 16
                        or any(not isinstance(quote, str) or not quote or quote != quote.strip() or len(quote) > 4096 for quote in item[key])
                        for key in quote_fields
                    )
                ):
                    raise ApplicationStateConflictError("recap semantic evidence span manifest is malformed")
                target = (item["record_kind"], item["record_id"], item["evidence_index"])
                if target in seen_span_targets:
                    raise ApplicationStateConflictError("recap semantic evidence span manifest has duplicate targets")
                seen_span_targets.add(target)
        if tuple_manifest:
            edge_ids: set[str] = set()
            target_tuples: set[tuple[str, str, str, str]] = set()
            tuple_fields = {"from_node_id", "relationship_type", "to_node_id", "label"}
            for item in manifest["edge_tuple_replacements"]:
                if (
                    not isinstance(item, dict)
                    or set(item) != {"edge_id", "expected_tuple", "replacement_tuple"}
                    or not isinstance(item.get("edge_id"), str)
                    or not item["edge_id"].strip()
                    or item["edge_id"] != item["edge_id"].strip()
                    or len(item["edge_id"]) > 256
                    or any(ch in item["edge_id"] for ch in ("\r", "\n", "\t"))
                    or item["edge_id"] in edge_ids
                ):
                    raise ApplicationStateConflictError("recap semantic edge tuple manifest is malformed")
                edge_ids.add(item["edge_id"])
                tuples = []
                for key in ("expected_tuple", "replacement_tuple"):
                    value = item.get(key)
                    if (
                        not isinstance(value, dict)
                        or set(value) != tuple_fields
                        or any(
                            not isinstance(value[field], str)
                            or not value[field].strip()
                            or value[field] != value[field].strip()
                            or len(value[field]) > (4096 if field == "label" else 128 if field == "relationship_type" else 256)
                            or any(ch in value[field] for ch in ("\r", "\n", "\t"))
                            or (field == "relationship_type" and value[field] != value[field].lower())
                            for field in tuple_fields
                        )
                    ):
                        raise ApplicationStateConflictError("recap semantic edge tuple manifest is malformed")
                    tuples.append(tuple(value[field] for field in ("from_node_id", "relationship_type", "to_node_id", "label")))
                if tuples[0] == tuples[1] or tuples[1] in target_tuples:
                    raise ApplicationStateConflictError("recap semantic edge tuple targets conflict")
                target_tuples.add(tuples[1])
            if "node_type_replacements" in manifest:
                operation = manifest["node_type_replacements"][0]
                if (
                    not isinstance(operation, dict)
                    or set(operation) != {"node_id", "expected_node_type", "replacement_node_type"}
                    or not isinstance(operation.get("node_id"), str)
                    or not operation["node_id"].strip()
                    or operation["node_id"] != operation["node_id"].strip()
                    or len(operation["node_id"]) > 256
                    or any(ch in operation["node_id"] for ch in ("\r", "\n", "\t"))
                    or any(
                        not isinstance(operation.get(key), str)
                        or operation[key] not in NODE_TYPES
                        or operation[key] != operation[key].strip()
                        or operation[key] != operation[key].lower()
                        or len(operation[key]) > 64
                        or any(ch in operation[key] for ch in ("\r", "\n", "\t"))
                        for key in ("expected_node_type", "replacement_node_type")
                    )
                    or operation["expected_node_type"] == operation["replacement_node_type"]
                ):
                    raise ApplicationStateConflictError("recap semantic node type manifest is malformed")
                node_id = operation["node_id"]
                if not any(
                    node_id in {
                        tuple_operation[key][endpoint]
                        for key in ("expected_tuple", "replacement_tuple")
                        for endpoint in ("from_node_id", "to_node_id")
                    }
                    for tuple_operation in manifest["edge_tuple_replacements"]
                ):
                    raise ApplicationStateConflictError("recap semantic node type replacement is not paired with an edge tuple")
        canonical = json.dumps(
            manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
            raise ApplicationStateConflictError("recap semantic candidate manifest changed")


def _assert_recap_source_binding_basis(
    child: ExtractionRun,
    parent: ExtractionRun,
    basis: RecapSemanticBasisV12,
    get_ancestor: Callable[[str], ExtractionRun | None] | None,
) -> None:
    """Validate the outer source snapshot, then run the legacy operation proof.

    The projected child exists only in memory so the unchanged operation basis
    can still be checked against the parent's source URI. Actual source binding
    is checked against the persisted child and V12 envelope first.
    """
    lineage = child.lineage
    source = child.components.get("source_artifact")
    parent_source = parent.components.get("source_artifact")
    spans = child.components.get("source_span_index")
    parent_spans = parent.components.get("source_span_index")
    canonical_basis = basis.model_dump(mode="json", by_alias=True)
    disposition = lineage.get("semantic_disposition")
    if (
        lineage.get("derivation") != _RECAP_SOURCE_BINDING_DERIVATION_V11
        or lineage.get("operation_derivation") != basis.operation_derivation
        or lineage.get("operation_manifest_schema") != basis.operation_manifest_schema
        or lineage.get("semantic_source_binding_basis_v12") != canonical_basis
        or not isinstance(disposition, dict)
        or _sha(disposition.get("basis_sha256")) != basis.digest()
        or child.run_id != basis.operation_basis.child_run_id
        or parent.run_id != basis.operation_basis.parent_run_id
        or child.source_domain != "recap"
        or parent.source_domain != "recap"
        or child.status != ExtractionRunStatus.REVIEWABLE
        or parent.status not in FROZEN_COMPONENT_STATUSES
        or not parent.has_required_review_components()
        or child.source_artifact_id != parent.source_artifact_id
        or child.source_artifact_id != basis.source_artifact_id
        or not source or not parent_source or not spans or not parent_spans
        or source.uri != basis.child_snapshot_uri
        or parent_source.uri != basis.parent_source_uri
        or _sha(source.sha256) != basis.source_revision_sha256
        or _sha(parent_source.sha256) != basis.source_revision_sha256
        or spans.uri != basis.span_index_uri
        or spans != parent_spans
        or _sha(spans.sha256) != basis.span_index_sha256
    ):
        raise ApplicationStateConflictError("recap source-binding basis changed")

    projected_components = dict(child.components)
    projected_components["source_artifact"] = source.model_copy(
        update={"uri": parent_source.uri}
    )
    projected_lineage = dict(lineage)
    projected_lineage["derivation"] = basis.operation_derivation
    projected_lineage["_source_binding_outer_derivation"] = basis.derivation
    projected_child = child.model_copy(update={
        "components": projected_components,
        "lineage": projected_lineage,
    })
    _assert_recap_semantic_basis(
        projected_child, parent, basis.operation_basis, get_ancestor
    )


def record_recap_semantic_disposition(
    run_id: str,
    *,
    expected_revision: int,
    basis: RecapSemanticBasisV1 | RecapSemanticBasisV2 | RecapSemanticBasisV3 | RecapSemanticBasisV4 | RecapSemanticBasisV5 | RecapSemanticBasisV6 | RecapSemanticBasisV7 | RecapSemanticBasisV8 | RecapSemanticBasisV9 | RecapSemanticBasisV10 | RecapSemanticBasisV11 | RecapSemanticBasisV12 | RecapSemanticBasisV13,
    decision: RecapSemanticDispositionCommandV1,
) -> ExtractionRun:
    """Single-use metadata-only CAS for a held recap correction child.

    An exact retry with the original revision returns the persisted receipt and
    time. A conflicting or stale decision never rewrites a frozen component.
    """
    canonical = _require_run_id(run_id)
    operation_basis = basis.operation_basis if isinstance(basis, RecapSemanticBasisV12) else basis
    if decision.state == "accepted" and isinstance(operation_basis, RecapSemanticBasisV13):
        raise ApplicationStateConflictError(
            "source-supported actor recovery cannot be semantically accepted",
        )
    basis_child_run_id = (
        basis.operation_basis.child_run_id
        if isinstance(basis, RecapSemanticBasisV12)
        else basis.child_run_id
    )
    if expected_revision < 1 or canonical != basis_child_run_id:
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
        _assert_recap_semantic_basis(
            child, parent, basis, get_ancestor=lambda ancestor_id: repo.get_run(conn, ancestor_id))
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
    if (
        "native_recap_source" in run.lineage
        or run.profile_id == "fresh_recap_native_source_v1"
    ):
        from graph_memory.ingestion.native_recap_source import Record, PROFILE

        try:
            record = Record.model_validate(run.lineage.get("native_recap_source"))
            if (
                run.run_id != record.run_id
                or run.profile_id != PROFILE
                or run.components
                or run.status != ExtractionRunStatus.DRAFT
                or run.source_artifact_id != record.app_source_artifact_id
                or run.source_domain != "recap"
                or run.campaign_id != record.campaign_id
                or run.session_id != record.session_id
            ):
                raise ValueError("Invalid source-only run")
        except ValueError as exc:
            raise ApplicationStateValidationError(
                "Invalid native recap source intent"
            ) from exc
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
        if (
            "native_recap_source" in existing.lineage
            or existing.profile_id == "fresh_recap_native_source_v1"
            or (lineage is not None and "native_recap_source" in lineage)
        ):
            raise ApplicationStateConflictError(
                "Native source-only runs use their exact admission recovery, never generic extraction"
            )
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
        if (
            "native_recap_source" in existing.lineage
            or existing.profile_id == "fresh_recap_native_source_v1"
            or "native_recap_source" in successor.lineage
            or successor.profile_id == "fresh_recap_native_source_v1"
        ):
            raise ApplicationStateConflictError("Native source intents cannot be superseded by extraction")
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
            raise ApplicationStateIntegrityError(
                "supersession lineage is not reciprocal"
            )
        if successor.supersedes_run_id != predecessor.run_id:
            raise ApplicationStateIntegrityError(
                "supersession lineage is not reciprocal"
            )
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


def update_native_recap_source(
    run_id: str, *, expected_revision: int, record
) -> ExtractionRun:
    """Narrow same-lifecycle CAS. No source intent/effect authority outside this row."""
    from graph_memory.ingestion.native_recap_source import (
        Record,
        KEY,
        PROFILE,
        validate_change,
    )

    canonical = _require_run_id(run_id)
    try:
        value = Record.model_validate(record)
    except ValueError as exc:
        raise ApplicationStateConflictError(
            "Native source intent correspondence changed"
        ) from exc
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.lock_run(conn, canonical)
        if existing is None:
            raise ApplicationStateNotFoundError("Native source intent not found")
        if existing.revision != expected_revision:
            raise ApplicationStateConflictError("Native source intent revision changed")
        if (
            existing.status != ExtractionRunStatus.DRAFT
            or existing.profile_id != PROFILE
            or existing.components
        ):
            raise ApplicationStateConflictError("Not a native source-only run")
        try:
            prior = Record.model_validate(existing.lineage.get(KEY))
            validate_change(prior, value)
            if canonical != value.run_id:
                raise ValueError("Foreign source intent")
        except ValueError as exc:
            raise ApplicationStateConflictError(
                "Native source intent correspondence changed"
            ) from exc
        updated = existing.model_copy(
            update={
                "revision": existing.revision + 1,
                "updated_at": _iso_now(),
                "lineage": {**existing.lineage, KEY: value.model_dump(mode="json")},
            }
        )
        persisted = repo.cas_update_run(
            conn, updated, expected_revision=expected_revision
        )
        if persisted is None:
            raise ApplicationStateConflictError("Native source intent CAS lost")
        return persisted
