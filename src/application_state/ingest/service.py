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
_RECAP_CANDIDATE_DERIVATION_V3 = "operator_recap_semantic_candidate_correction_v3"
_RECAP_CANDIDATE_DERIVATION_V4 = "operator_recap_semantic_candidate_correction_v4"
_RECAP_CANDIDATE_DERIVATION_V5 = "operator_recap_semantic_candidate_correction_v5"
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


def _assert_recap_semantic_basis(
    child: ExtractionRun,
    parent: ExtractionRun,
    basis: RecapSemanticBasisV1 | RecapSemanticBasisV2 | RecapSemanticBasisV3 | RecapSemanticBasisV4 | RecapSemanticBasisV5 | RecapSemanticBasisV6 | RecapSemanticBasisV7,
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
            _RECAP_CANDIDATE_DERIVATION_V6 if isinstance(basis, RecapSemanticBasisV7)
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
    if isinstance(basis, RecapSemanticBasisV7):
        _assert_recap_split_manifest(lineage.get("semantic_candidate_manifest"), basis)
        return
    if isinstance(basis, RecapSemanticBasisV2):
        manifest = lineage.get("semantic_candidate_manifest")
        action_manifest = isinstance(basis, RecapSemanticBasisV3)
        tuple_manifest = isinstance(basis, RecapSemanticBasisV4)
        span_manifest = isinstance(basis, (RecapSemanticBasisV5, RecapSemanticBasisV6))
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
        expected_manifest_schema = (
            basis.manifest_schema if action_manifest or tuple_manifest or span_manifest
            else "dmb_recap_semantic_candidate_manifest_v1"
        )
        if (
            not isinstance(manifest, dict)
            or set(manifest) != expected_manifest_keys
            or manifest.get("schema") != expected_manifest_schema
            or ((action_manifest or tuple_manifest or span_manifest) and lineage.get("derivation") != basis.derivation)
            or (not (tuple_manifest or span_manifest) and not isinstance(manifest.get("node_description_replacements"), list))
            or (not (tuple_manifest or span_manifest) and not isinstance(manifest.get("omitted_edge_ids"), list))
            or (action_manifest and (not isinstance(manifest.get("session_action_replacements"), list) or len(manifest["session_action_replacements"]) != 1))
            or (not (tuple_manifest or span_manifest) and len(manifest["node_description_replacements"]) > 1)
            or (not (tuple_manifest or span_manifest) and len(manifest["omitted_edge_ids"]) > 1)
            or (not (tuple_manifest or span_manifest) and not (manifest["node_description_replacements"] or manifest["omitted_edge_ids"] or (action_manifest and manifest["session_action_replacements"]) or node_omission))
            or (tuple_manifest and (not isinstance(manifest.get("edge_tuple_replacements"), list) or not 1 <= len(manifest["edge_tuple_replacements"]) <= 7))
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
        canonical = json.dumps(
            manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        if hashlib.sha256(canonical).hexdigest() != basis.manifest_sha256:
            raise ApplicationStateConflictError("recap semantic candidate manifest changed")


def record_recap_semantic_disposition(
    run_id: str,
    *,
    expected_revision: int,
    basis: RecapSemanticBasisV1 | RecapSemanticBasisV2 | RecapSemanticBasisV3 | RecapSemanticBasisV4 | RecapSemanticBasisV5 | RecapSemanticBasisV6 | RecapSemanticBasisV7,
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
