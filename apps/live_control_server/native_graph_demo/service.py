"""A bounded demo service whose semantic authority is DungeonMind.

The service deliberately does not import Buddy's production repository factory
or application startup.  A caller supplies one already-selected DungeonMind
native repository; this class can neither select a World nor change databases.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dungeonmind.application.vnext import (
    create_empty_space,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.common import LabelsAnyVisibility
from dungeonmind.contracts.vnext.native_source import (
    NativeTextEvidenceSpanRequestV1,
    NativeTextSourceAdmissionV1,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.domain.errors import (
    DungeonMindError,
    PersistenceIntegrityError,
    PersistenceUnavailableError,
    StaleParentRevisionError,
)
from graph_memory.vnext.domain_runtime import (
    GM_LABEL,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_world_domain_contract,
)
from worldkeeper.application.commit import (
    CommitAuthorityIntegrityFailure,
    CommittedChangeOutcomeUnknown,
    CommittedChangeVerificationIntegrityFailure,
    CommittedChangeVerificationUnavailable,
    PreparedChangeConflict,
    PreparedChangeIntegrityFailure,
    PreparedChangeStale,
)
from worldkeeper.application.contracts import (
    AssertionMetadata,
    CreateFact,
    CreateObject,
    CreateRelationship,
    DurableObjectRef,
    LiteralFactValue,
    PreparedWorldChange,
    ResultOf,
    TemporalScope,
    TermRefFactValue,
    Visibility,
    WorldChangeIntent,
)
from worldkeeper.integrations.dungeonmind.runtime import DungeonMindWorldKeeperRuntime
from apps.live_control_server.integrations.worldkeeper.registry_standing_consumer import (
    canonical as _prepared_canonical,
    decode_prepared,
    encode_prepared,
)

from .storage import NativeGraphDemoStore, canonical_json


MAX_NODES = 48
MAX_EDGES = 96
MAX_NAME_BYTES = 128
MAX_LABEL_BYTES = 128
MAX_JOURNAL_OPERATIONS = 512

_DEMO_ALLOCATION_ID = "native-graph-demo:single-space:v1"
_SEED_ADMISSION_ID = "native-graph-demo:seed-source:v1"
_SEED_OPERATION_ID = "seed:native-graph-demo-v1"
_SEED_PREPARED_ID = "prepared:native-graph-demo-seed-v1"
_SEED_LINES = (
    ("mara", "Mara is a person."),
    ("tomas", "Tomas is a person."),
    ("inn", "Lantern Inn is a gathering place."),
    ("mara_knows_tomas", "Mara knows Tomas."),
    ("tomas_knows_mara", "Tomas knows Mara."),
    ("mara_visits_inn", "Mara visits Lantern Inn."),
    ("tomas_visits_inn", "Tomas visits Lantern Inn."),
)
_ALLOWED_API_FIELDS = {
    "create_object": frozenset(
        {"operation_id", "expected_revision_id", "kind", "name", "object_kind"}
    ),
    "connect": frozenset(
        {
            "operation_id",
            "expected_revision_id",
            "kind",
            "source_id",
            "target_id",
            "predicate",
        }
    ),
}
_CUSTOM_LABEL = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


class DemoError(Exception):
    """A safe service error that the HTTP adapter can map without leaking internals."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def _now() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return _now().isoformat()


def _parse_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise DemoError("invalid_operation_id", "operation_id must be a canonical UUID")
    try:
        parsed = str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise DemoError(
            "invalid_operation_id", "operation_id must be a canonical UUID"
        ) from None
    if parsed != value:
        raise DemoError(
            "invalid_operation_id", "operation_id must be a lowercase canonical UUID"
        )
    return value


def _nonblank_text(value: object, field: str, *, max_bytes: int = 256) -> str:
    if not isinstance(value, str):
        raise DemoError("invalid_request", f"{field} must be text")
    normalized = value.strip()
    if not normalized:
        raise DemoError("invalid_request", f"{field} must not be blank")
    try:
        encoded = normalized.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise DemoError("invalid_request", f"{field} must be valid UTF-8") from None
    if len(encoded) > max_bytes:
        raise DemoError("limit_exceeded", f"{field} exceeds the {max_bytes}-byte limit")
    if any(unicodedata.category(ch) == "Cc" for ch in normalized):
        raise DemoError("invalid_request", f"{field} cannot contain control characters")
    return normalized


def _prepared_json(prepared: PreparedWorldChange) -> str:
    return _prepared_canonical(encode_prepared(prepared)).decode("utf-8")


class NativeGraphDemoService:
    """Operate one synthetic KnowledgeSpace through native DungeonMind + WorldKeeper."""

    def __init__(
        self,
        repository: object,
        state_dir: str | Path,
        storage_label: str = "postgres",
    ) -> None:
        self._repository = repository
        self._storage_label = storage_label
        self._store = NativeGraphDemoStore(
            state_dir, max_operations=MAX_JOURNAL_OPERATIONS
        )
        self._domain = dungeonbuddy_world_domain_contract()
        self._profile = dungeonbuddy_dnd5e_custom_predicate_profile()
        self._space_id: str | None = None
        self._genesis_revision_id: str | None = None
        self._initialized = False

    def graph(self) -> dict[str, Any]:
        with self._store.atomic():
            self._ensure_initialized()
            return self._read_graph()

    def close(self) -> None:
        """Release the local durable operation journal connection."""
        self._store.close()

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        with self._store.atomic():
            self._ensure_initialized()
            normalized, request_json = self._validate_prepare_request(request)
            operation_id = normalized["operation_id"]
            request_sha = hashlib.sha256(request_json.encode("utf-8")).hexdigest()
            try:
                existing = self._store.get_operation(operation_id)
            except (ValueError, json.JSONDecodeError):
                raise DemoError(
                    "journal_integrity_failure",
                    "The saved operation could not be verified. It was not changed.",
                    503,
                ) from None
            if existing is not None:
                if (
                    existing["request_sha256"] != request_sha
                    or existing["request_json"] != request_json
                ):
                    raise DemoError(
                        "operation_id_conflict",
                        "This operation_id is already bound to different input.",
                        409,
                    )
                if existing["status"] == "unknown":
                    prepared = self._record_prepared(existing)
                    state = self._recover_native_publication(prepared)
                    if state == "committed":
                        return self._confirm_record(
                            operation_id, prepared, existing, receipts_checked=True
                        )
                    return {
                        "operation_id": operation_id,
                        "status": "unknown",
                        "message": "The prior native outcome is still uncertain. Check operation status before preparing another change.",
                    }
                if existing["status"] == "committed":
                    prepared = self._record_prepared(existing)
                    self._verify_committed_record(prepared, existing)
                    return {
                        "operation_id": operation_id,
                        "status": "committed",
                        "graph": self._read_graph(),
                    }
                if existing["status"] == "rejected":
                    rejected = existing.get("rejected") or {}
                    return {
                        "operation_id": operation_id,
                        "status": "rejected",
                        "code": rejected.get("code", "operation_rejected"),
                        "error": rejected.get(
                            "error",
                            "This operation was rejected; review the graph and prepare a new operation.",
                        ),
                    }
                return self._prepared_response(operation_id, normalized, existing)

            try:
                reservation = self._store.get_reservation(operation_id)
            except (ValueError, json.JSONDecodeError):
                raise DemoError(
                    "journal_integrity_failure",
                    "The saved operation reservation could not be verified.",
                    503,
                ) from None
            if reservation is not None and (
                reservation["request_sha256"] != request_sha
                or reservation["request_json"] != request_json
            ):
                raise DemoError(
                    "operation_id_conflict",
                    "This operation_id is already reserved for different input.",
                    409,
                )

            current = self._read_graph()
            if normalized["kind"] == "create_object":
                graph = self._prepare_create(normalized, current)
            else:
                graph = self._prepare_connect(normalized, current)
            if graph is not None:
                return {
                    "status": "already_exists",
                    "message": graph["message"],
                    "graph": graph["graph"],
                }
            if reservation is None:
                operation_source = self._existing_operation_source(normalized)
                if normalized["expected_revision_id"] != current["revision_id"]:
                    # An admission may have succeeded immediately before its
                    # response was lost. Recover only the exact receipt bound
                    # to this operation and original reviewed parent.
                    if (
                        operation_source is None
                        or operation_source.publication_receipt.expected_parent_revision_id
                        != normalized["expected_revision_id"]
                        or operation_source.published_revision_id
                        != current["revision_id"]
                    ):
                        raise DemoError(
                            "stale_revision",
                            "The graph changed. Review the current graph and prepare again.",
                            409,
                        )
                if self._store.operation_count() >= self._store.max_operations:
                    raise DemoError(
                        "operation_limit_reached",
                        f"This demo keeps at most {self._store.max_operations} operations.",
                        409,
                    )
                try:
                    self._store.reserve_operation(
                        operation_id=operation_id,
                        request_json=request_json,
                        parent_revision_id=normalized["expected_revision_id"],
                        updated_at=_iso_now(),
                    )
                except OverflowError:
                    raise DemoError(
                        "operation_limit_reached",
                        f"This demo keeps at most {self._store.max_operations} operations.",
                        409,
                    ) from None
                # A reservation is durable before any native source write. If
                # the process stops after this point, it bounds retries and can
                # be reconciled through the deterministic native admission id.
                with self._store.checkpoint():
                    pass
                reservation = self._store.get_reservation(operation_id)
                assert reservation is not None
            return self._finish_reserved_prepare(
                normalized, reservation, allow_source_admission=True
            )

    def confirm(self, operation_id: str) -> dict[str, Any]:
        with self._store.atomic():
            self._ensure_initialized()
            operation_id = _parse_uuid(operation_id)
            try:
                record = self._store.get_operation(operation_id)
            except (ValueError, json.JSONDecodeError):
                raise DemoError(
                    "journal_integrity_failure",
                    "The saved operation could not be verified. It was not changed.",
                    503,
                ) from None
            if record is None:
                try:
                    reservation = self._store.get_reservation(operation_id)
                except (ValueError, json.JSONDecodeError):
                    raise DemoError(
                        "journal_integrity_failure",
                        "The saved operation reservation could not be verified.",
                        503,
                    ) from None
                if reservation is not None:
                    return {
                        "operation_id": operation_id,
                        "status": "unknown",
                        "message": "The operation is reserved while native source admission is reconciled.",
                    }
                raise DemoError(
                    "operation_not_found", "No prepared operation has this id.", 404
                )
            if record["status"] == "rejected":
                rejected = record.get("rejected") or {}
                return {
                    "operation_id": operation_id,
                    "status": "rejected",
                    "code": rejected.get("code", "operation_rejected"),
                    "error": rejected.get(
                        "error", "This operation was rejected; prepare a fresh review."
                    ),
                }
            prepared = self._record_prepared(record)
            if record["status"] == "committed":
                self._verify_committed_record(prepared, record)
                return {
                    "operation_id": operation_id,
                    "status": "committed",
                    "graph": self._read_graph(),
                }
            if record["status"] == "unknown":
                state = self._recover_native_publication(prepared)
                if state == "committed":
                    return self._confirm_record(
                        operation_id, prepared, record, receipts_checked=True
                    )
                return {
                    "operation_id": operation_id,
                    "status": "unknown",
                    "message": "The native outcome is uncertain. No new publication was attempted.",
                }
            return self._confirm_record(operation_id, prepared, record)

    def operation(self, operation_id: str) -> dict[str, Any]:
        with self._store.atomic():
            self._ensure_initialized()
            operation_id = _parse_uuid(operation_id)
            try:
                record = self._store.get_operation(operation_id)
            except (ValueError, json.JSONDecodeError):
                raise DemoError(
                    "journal_integrity_failure",
                    "The saved operation could not be verified.",
                    503,
                ) from None
            if record is None:
                try:
                    reservation = self._store.get_reservation(operation_id)
                except (ValueError, json.JSONDecodeError):
                    raise DemoError(
                        "journal_integrity_failure",
                        "The saved operation reservation could not be verified.",
                        503,
                    ) from None
                if reservation is None:
                    return {"operation_id": operation_id, "status": "not_found"}
                try:
                    normalized_reservation, reservation_json = (
                        self._validate_prepare_request(reservation["request"])
                    )
                    if (
                        normalized_reservation["operation_id"] != operation_id
                        or reservation_json != reservation["request_json"]
                    ):
                        raise DemoError(
                            "journal_integrity_failure",
                            "The reserved operation request does not match its identity.",
                            503,
                        )
                    return self._finish_reserved_prepare(
                        normalized_reservation,
                        reservation,
                        allow_source_admission=False,
                    )
                except DemoError as exc:
                    if exc.status >= 500:
                        return {
                            "operation_id": operation_id,
                            "status": "unknown",
                            "message": "The operation reservation could not be reconciled with native authority yet.",
                        }
                    raise
            if record["status"] == "rejected":
                rejected = record.get("rejected") or {}
                return {
                    "operation_id": operation_id,
                    "status": "rejected",
                    "code": rejected.get("code", "operation_rejected"),
                    "error": rejected.get(
                        "error", "This operation was rejected; prepare a fresh review."
                    ),
                }
            prepared = self._record_prepared(record)
            if record["status"] == "committed":
                self._verify_committed_record(prepared, record)
                return {
                    "operation_id": operation_id,
                    "status": "committed",
                    "graph": self._read_graph(),
                }
            recovered = self._recover_native_publication(prepared)
            if recovered == "committed":
                return self._confirm_record(
                    operation_id, prepared, record, receipts_checked=True
                )
            if recovered == "uncertain":
                return {
                    "operation_id": operation_id,
                    "status": "unknown",
                    "message": "Native publication receipts are incomplete; the outcome remains uncertain.",
                }
            if record["status"] == "unknown":
                return {
                    "operation_id": operation_id,
                    "status": "unknown",
                    "message": "No complete native receipt is available yet. The operation remains recoverable.",
                }
            return {
                "operation_id": operation_id,
                "status": "prepared",
                "parent_revision_id": record["parent_revision_id"],
                "review": {"summary": self._summary_from_record(record)},
            }

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        try:
            receipt = create_empty_space(
                repository=self._repository,
                allocation_id=_DEMO_ALLOCATION_ID,
                created_at=_now(),
                domain_contract=self._domain,
                semantic_profile=self._profile,
            )
            saved_id = self._store.get_metadata("space_id")
            if saved_id is not None and saved_id != receipt.space_id:
                raise DemoError(
                    "space_binding_mismatch",
                    "The saved demo binding does not match its native allocation receipt.",
                    503,
                )
            self._store.set_metadata("space_id", receipt.space_id)
            self._store.set_metadata(
                "genesis_revision_id", receipt.publication_receipt.published_revision_id
            )
            self._space_id = receipt.space_id
            self._genesis_revision_id = (
                receipt.publication_receipt.published_revision_id
            )
            self._ensure_seed()
            self._initialized = True
        except DemoError:
            raise
        except (PersistenceUnavailableError, OSError, sqlite3.Error) as exc:
            raise DemoError(
                "native_authority_unavailable",
                "The native DungeonMind graph authority is unavailable.",
                503,
            ) from exc
        except Exception as exc:
            mapped = self._map_native_error(
                exc, "The native demo graph could not be initialized."
            )
            raise mapped from exc

    def _ensure_seed(self) -> None:
        assert self._space_id is not None and self._genesis_revision_id is not None
        source = self._repository.get_native_source_admission_receipt(
            self._space_id, _SEED_ADMISSION_ID
        )
        if source is None:
            head = self._repository.get_head(self._space_id)
            if head is None or head.head_revision_id != self._genesis_revision_id:
                raise DemoError(
                    "seed_source_recovery_required",
                    "The synthetic source was not confirmed at the expected empty-space head.",
                    409,
                )
            source = self._admit_seed_source(head.head_revision_id)
        self._verify_seed_source(source)

        publication = self._repository.get_prospective_publication(
            self._space_id, _SEED_PREPARED_ID
        )
        publication_receipt = self._repository.get_publication_receipt(
            self._space_id, _SEED_PREPARED_ID
        )
        if publication is not None or publication_receipt is not None:
            if publication is None or publication_receipt is None:
                raise DemoError(
                    "seed_outcome_unknown",
                    "The native seed publication is incomplete and needs recovery.",
                    503,
                )
            if (
                publication.publication_receipt != publication_receipt
                or publication_receipt.expected_parent_revision_id
                != source.published_revision_id
            ):
                raise DemoError(
                    "seed_integrity_failure",
                    "The native seed receipt does not match its admitted source.",
                    503,
                )
            graph = self._read_graph()
            self._verify_seed_graph(graph, source, publication)
            self._store.set_metadata("seed_status", "committed")
            return

        record = self._store.get_operation(_SEED_OPERATION_ID)
        if record is not None:
            prepared = self._record_prepared(record)
            if record["status"] == "committed":
                self._verify_committed_record(prepared, record)
                seed_publication = self._repository.get_prospective_publication(
                    self._space_id, _SEED_PREPARED_ID
                )
                self._verify_seed_graph(self._read_graph(), source, seed_publication)
                return
            if record["status"] == "unknown":
                if self._recover_native_publication(prepared) != "committed":
                    raise DemoError(
                        "seed_outcome_unknown",
                        "The native seed outcome remains uncertain; no new publication was attempted.",
                        503,
                    )
                self._confirm_record(
                    _SEED_OPERATION_ID, prepared, record, receipts_checked=True
                )
                seed_publication = self._repository.get_prospective_publication(
                    self._space_id, _SEED_PREPARED_ID
                )
                self._verify_seed_graph(self._read_graph(), source, seed_publication)
                return
            if record["status"] == "rejected":
                raise DemoError(
                    "seed_stale_parent",
                    "The native seed was rejected against a stale parent and cannot be replayed automatically.",
                    409,
                )
        else:
            current = self._read_graph()
            if current["revision_id"] != source.published_revision_id:
                raise DemoError(
                    "seed_stale_parent",
                    "The source head changed before the synthetic seed could be published.",
                    409,
                )
            intent = self._seed_intent(source)
            prepared = self._runtime(prepared_id=_SEED_PREPARED_ID).prepare_change(
                intent
            )
            prepared_json = _prepared_json(prepared)
            request_json = canonical_json(
                {
                    "kind": "seed",
                    "seed_version": 1,
                    "source_admission_id": source.admission_id,
                    "expected_revision_id": source.published_revision_id,
                }
            )
            self._store.insert_prepared_operation(
                operation_id=_SEED_OPERATION_ID,
                request_json=request_json,
                parent_revision_id=source.published_revision_id,
                prepared_json=prepared_json,
                updated_at=_iso_now(),
            )
            record = self._store.get_operation(_SEED_OPERATION_ID)
            assert record is not None
        self._confirm_record(_SEED_OPERATION_ID, prepared, record)
        seed_publication = self._repository.get_prospective_publication(
            self._space_id, _SEED_PREPARED_ID
        )
        self._verify_seed_graph(self._read_graph(), source, seed_publication)
        self._store.set_metadata("seed_status", "committed")

    def _admit_seed_source(self, expected_parent_revision_id: str) -> Any:
        assert self._space_id is not None
        body = "\n".join(line for _, line in _SEED_LINES) + "\n"
        raw = body.encode("utf-8")
        spans: list[NativeTextEvidenceSpanRequestV1] = []
        cursor = 0
        for client_ref, line in _SEED_LINES:
            selected = (line + "\n").encode("utf-8")
            end = cursor + len(selected)
            spans.append(
                NativeTextEvidenceSpanRequestV1(
                    client_ref=client_ref,
                    evidence_role="support",
                    start_byte=cursor,
                    end_byte=end,
                    expected_slice_sha256=hashlib.sha256(selected).hexdigest(),
                )
            )
            cursor = end
        request = NativeTextSourceAdmissionV1(
            space_id=self._space_id,
            admission_id=_SEED_ADMISSION_ID,
            expected_parent_revision_id=expected_parent_revision_id,
            created_at=_now(),
            body_text=body,
            expected_body_sha256=hashlib.sha256(raw).hexdigest(),
            source_classification="dungeonbuddy.source:worldbuilding",
            authority="primary",
            visibility=LabelsAnyVisibility(labels=[GM_LABEL]),
            origin=None,
            spans=spans,
        )
        return publish_native_text_source_evidence(
            repository=self._repository,
            request=request,
            domain_contract=self._domain,
            semantic_profile=self._profile,
        )

    def _verify_seed_source(self, receipt: Any) -> None:
        assert self._space_id is not None
        expected_refs = {name for name, _ in _SEED_LINES}
        actual_refs = {item.client_ref for item in receipt.bindings}
        if (
            receipt.space_id != self._space_id
            or receipt.admission_id != _SEED_ADMISSION_ID
            or receipt.status != "published"
            or actual_refs != expected_refs
        ):
            raise DemoError(
                "seed_source_integrity_failure",
                "The synthetic source receipt failed identity verification.",
                503,
            )
        expected_body = "\n".join(line for _, line in _SEED_LINES) + "\n"
        body_bytes = expected_body.encode("utf-8")
        expected_spans: dict[str, tuple[int, int, str]] = {}
        cursor = 0
        for client_ref, line in _SEED_LINES:
            selected = (line + "\n").encode("utf-8")
            end = cursor + len(selected)
            expected_spans[client_ref] = (
                cursor,
                end,
                hashlib.sha256(selected).hexdigest(),
            )
            cursor = end
        view = self._repository.open_native_source_view(self._space_id)
        for binding in receipt.bindings:
            source = view.get_native_text_source(
                source_artifact_id=receipt.source_artifact_id,
                source_revision_id=receipt.source_revision_id,
                span_id=binding.span_id,
            )
            if source is None or source.body_bytes != body_bytes:
                raise DemoError(
                    "seed_source_integrity_failure",
                    "The admitted synthetic source could not be read back exactly.",
                    503,
                )
            expected_start, expected_end, expected_digest = expected_spans[
                binding.client_ref
            ]
            if (
                source.span_proof.evidence_ref_id != binding.evidence_ref_id
                or source.span_proof.source_revision_id != receipt.source_revision_id
                or source.span_proof.start_byte != expected_start
                or source.span_proof.end_byte != expected_end
                or source.span_proof.slice_sha256 != expected_digest
            ):
                raise DemoError(
                    "seed_source_integrity_failure",
                    "A native source evidence binding changed.",
                    503,
                )

    def _seed_intent(self, source: Any) -> WorldChangeIntent:
        evidence_by_ref = {
            item.client_ref: item.evidence_ref_id for item in source.bindings
        }

        def metadata(evidence_ref: str) -> AssertionMetadata:
            return self._metadata((evidence_ref,))

        objects = (
            CreateObject(
                client_op_id="seed-mara",
                facts=(
                    CreateFact(
                        client_op_id="seed-mara-name",
                        predicate="dnd5e:name",
                        value=LiteralFactValue.from_json("Mara"),
                        metadata=metadata(evidence_by_ref["mara"]),
                    ),
                    CreateFact(
                        client_op_id="seed-mara-classification",
                        predicate="dnd5e:classification",
                        value=TermRefFactValue("dnd5e:npc"),
                        metadata=metadata(evidence_by_ref["mara"]),
                    ),
                ),
            ),
            CreateObject(
                client_op_id="seed-tomas",
                facts=(
                    CreateFact(
                        client_op_id="seed-tomas-name",
                        predicate="dnd5e:name",
                        value=LiteralFactValue.from_json("Tomas"),
                        metadata=metadata(evidence_by_ref["tomas"]),
                    ),
                    CreateFact(
                        client_op_id="seed-tomas-classification",
                        predicate="dnd5e:classification",
                        value=TermRefFactValue("dnd5e:npc"),
                        metadata=metadata(evidence_by_ref["tomas"]),
                    ),
                ),
            ),
            CreateObject(
                client_op_id="seed-lantern-inn",
                facts=(
                    CreateFact(
                        client_op_id="seed-lantern-inn-name",
                        predicate="dnd5e:name",
                        value=LiteralFactValue.from_json("Lantern Inn"),
                        metadata=metadata(evidence_by_ref["inn"]),
                    ),
                    CreateFact(
                        client_op_id="seed-lantern-inn-classification",
                        predicate="dnd5e:classification",
                        value=TermRefFactValue("dnd5e:location"),
                        metadata=metadata(evidence_by_ref["inn"]),
                    ),
                ),
            ),
        )
        relationships = (
            CreateRelationship(
                client_op_id="seed-mara-knows-tomas",
                source=ResultOf("seed-mara"),
                predicate="dungeonbuddy.custom:knows",
                target=ResultOf("seed-tomas"),
                metadata=metadata(evidence_by_ref["mara_knows_tomas"]),
            ),
            CreateRelationship(
                client_op_id="seed-tomas-knows-mara",
                source=ResultOf("seed-tomas"),
                predicate="dungeonbuddy.custom:knows",
                target=ResultOf("seed-mara"),
                metadata=metadata(evidence_by_ref["tomas_knows_mara"]),
            ),
            CreateRelationship(
                client_op_id="seed-mara-visits-inn",
                source=ResultOf("seed-mara"),
                predicate="dungeonbuddy.custom:visits",
                target=ResultOf("seed-lantern-inn"),
                metadata=metadata(evidence_by_ref["mara_visits_inn"]),
            ),
            CreateRelationship(
                client_op_id="seed-tomas-visits-inn",
                source=ResultOf("seed-tomas"),
                predicate="dungeonbuddy.custom:visits",
                target=ResultOf("seed-lantern-inn"),
                metadata=metadata(evidence_by_ref["tomas_visits_inn"]),
            ),
        )
        return WorldChangeIntent(
            space_id=self._space_id or "",
            producer="native-graph-demo",
            operations=(*objects, *relationships),
        )

    def _verify_seed_graph(
        self, graph: dict[str, Any], source: Any, publication: Any | None
    ) -> None:
        if publication is None:
            raise DemoError(
                "seed_graph_integrity_failure",
                "The native seed result bindings are unavailable.",
                503,
            )
        assert self._space_id is not None
        result_bindings = {
            item.client_op_id: item for item in publication.prospective_result.results
        }
        expected_nodes = {
            "seed-mara": ("Mara", "person"),
            "seed-tomas": ("Tomas", "person"),
            "seed-lantern-inn": ("Lantern Inn", "location"),
        }
        if any(
            result_bindings.get(client_op_id) is None
            or result_bindings[client_op_id].result_kind != "entity"
            for client_op_id in expected_nodes
        ):
            raise DemoError(
                "seed_graph_integrity_failure",
                "The native seed result identity bindings are incomplete.",
                503,
            )
        nodes_by_id = {node["id"]: node for node in graph["nodes"]}
        ids = {
            client_op_id: result_bindings[client_op_id].durable_id
            for client_op_id in expected_nodes
        }
        if any(
            nodes_by_id.get(ids[client_op_id], {}).get("name") != name
            or nodes_by_id.get(ids[client_op_id], {}).get("kind") != kind
            for client_op_id, (name, kind) in expected_nodes.items()
        ):
            raise DemoError(
                "seed_graph_integrity_failure",
                "A native seed object failed exact identity readback.",
                503,
            )
        expected_edges = {
            "seed-mara-knows-tomas": (ids["seed-mara"], ids["seed-tomas"], "knows"),
            "seed-tomas-knows-mara": (ids["seed-tomas"], ids["seed-mara"], "knows"),
            "seed-mara-visits-inn": (
                ids["seed-mara"],
                ids["seed-lantern-inn"],
                "visits",
            ),
            "seed-tomas-visits-inn": (
                ids["seed-tomas"],
                ids["seed-lantern-inn"],
                "visits",
            ),
        }
        edges_by_id = {edge["id"]: edge for edge in graph["edges"]}
        for client_op_id, (source_id, target_id, predicate) in expected_edges.items():
            binding = result_bindings.get(client_op_id)
            edge = None if binding is None else edges_by_id.get(binding.durable_id)
            if (
                binding is None
                or binding.result_kind != "assertion"
                or edge is None
                or edge["source_id"] != source_id
                or edge["target_id"] != target_id
                or edge["predicate"] != predicate
            ):
                raise DemoError(
                    "seed_graph_integrity_failure",
                    "A native seed relationship failed exact identity readback.",
                    503,
                )
        seed_child = self._repository.get_revision(
            self._space_id, publication.prospective_result.published_revision_id
        )
        if (
            seed_child is None
            or seed_child.graph_payload_sha256
            != publication.publication_receipt.graph_payload_sha256
            or canonical_sha256(seed_child.graph_payload)
            != publication.publication_receipt.graph_payload_sha256
        ):
            raise DemoError(
                "seed_graph_integrity_failure",
                "The immutable native seed child failed readback.",
                503,
            )
        evidence_ids = {
            item.client_ref: item.evidence_ref_id for item in source.bindings
        }
        assertion_bindings = {
            "seed-mara-name": "mara",
            "seed-mara-classification": "mara",
            "seed-tomas-name": "tomas",
            "seed-tomas-classification": "tomas",
            "seed-lantern-inn-name": "inn",
            "seed-lantern-inn-classification": "inn",
            "seed-mara-knows-tomas": "mara_knows_tomas",
            "seed-tomas-knows-mara": "tomas_knows_mara",
            "seed-mara-visits-inn": "mara_visits_inn",
            "seed-tomas-visits-inn": "tomas_visits_inn",
        }
        child_assertions = {
            assertion.get("assertion_id"): assertion
            for assertion in seed_child.graph_payload.get("assertions", [])
            if isinstance(assertion, dict)
        }
        for client_op_id, source_ref in assertion_bindings.items():
            binding = result_bindings.get(client_op_id)
            assertion = (
                None if binding is None else child_assertions.get(binding.durable_id)
            )
            metadata = None if assertion is None else assertion.get("metadata")
            refs = (
                metadata.get("evidence_ref_ids") if isinstance(metadata, dict) else None
            )
            if not isinstance(refs, list) or evidence_ids.get(source_ref) not in refs:
                raise DemoError(
                    "seed_graph_integrity_failure",
                    "A native seed assertion is not bound to its exact admitted source span.",
                    503,
                )

    def _prepare_create(
        self, request: dict[str, str], graph: dict[str, Any]
    ) -> dict[str, Any] | None:
        kind = request["object_kind"]
        if kind == "event":
            raise DemoError(
                "unsupported_kind",
                "Event creation is unavailable because the current demo authoring profile has no declared event classification.",
                409,
            )
        if kind not in {"person", "location"}:
            raise DemoError(
                "unsupported_kind",
                "Only person and location objects are supported.",
                400,
            )
        if len(graph["nodes"]) >= MAX_NODES:
            raise DemoError(
                "node_limit_reached",
                f"This demo supports at most {MAX_NODES} objects.",
                409,
            )
        return None

    def _prepare_connect(
        self, request: dict[str, str], graph: dict[str, Any]
    ) -> dict[str, Any] | None:
        if len(graph["edges"]) >= MAX_EDGES:
            raise DemoError(
                "edge_limit_reached",
                f"This demo supports at most {MAX_EDGES} relationships.",
                409,
            )
        node_ids = {node["id"] for node in graph["nodes"]}
        if request["source_id"] not in node_ids or request["target_id"] not in node_ids:
            raise DemoError(
                "unknown_endpoint", "Choose two objects from this demo graph.", 400
            )
        predicate = request["predicate"]
        if not _CUSTOM_LABEL.fullmatch(predicate):
            raise DemoError(
                "invalid_predicate",
                "Relationship labels may use lowercase letters, numbers, dots, underscores, and hyphens.",
                400,
            )
        duplicate = next(
            (
                edge
                for edge in graph["edges"]
                if edge["source_id"] == request["source_id"]
                and edge["target_id"] == request["target_id"]
                and edge["predicate"] == predicate
            ),
            None,
        )
        if duplicate is not None:
            return {
                "message": "That directed relationship already exists.",
                "graph": graph,
            }
        return None

    def _finish_reserved_prepare(
        self,
        request: dict[str, str],
        reservation: dict[str, Any],
        *,
        allow_source_admission: bool,
    ) -> dict[str, Any]:
        operation_id = request["operation_id"]
        if (
            reservation.get("operation_id") != operation_id
            or reservation.get("request") != request
            or reservation.get("parent_revision_id")
            != request.get("expected_revision_id")
        ):
            raise DemoError(
                "journal_integrity_failure",
                "The saved operation reservation does not match its reviewed request.",
                503,
            )
        expected_parent_revision_id = reservation["parent_revision_id"]
        current = self._read_graph()
        source = self._existing_operation_source(request)
        if source is None:
            if not allow_source_admission:
                if current["revision_id"] == expected_parent_revision_id:
                    self._store.remove_reservation(operation_id)
                    return {"operation_id": operation_id, "status": "not_found"}
                return self._reject_reservation(
                    operation_id,
                    code="stale_revision",
                    error="The graph changed before the operation's source evidence was admitted. Review it and prepare again.",
                )
            if current["revision_id"] != expected_parent_revision_id:
                return self._reject_reservation(
                    operation_id,
                    code="stale_revision",
                    error="The graph changed before the operation's source evidence was admitted. Review it and prepare again.",
                )
            source = self._admit_operation_source(
                request,
                expected_parent_revision_id=expected_parent_revision_id,
            )
        if (
            source.publication_receipt.expected_parent_revision_id
            != expected_parent_revision_id
        ):
            return self._reject_reservation(
                operation_id,
                code="operation_source_conflict",
                error="The native source admission belongs to a different reviewed parent.",
            )
        native_head = self._repository.get_head(self._space_id)
        if (
            native_head is None
            or native_head.head_revision_id != source.published_revision_id
        ):
            return self._reject_reservation(
                operation_id,
                code="stale_revision",
                error="The graph changed after source admission. Review the current graph and prepare again.",
            )
        self._verify_operation_source(source, request)
        try:
            intent, summary = self._intent_for_request(
                request, evidence_ref_id=source.bindings[0].evidence_ref_id
            )
            prepared = self._runtime(
                prepared_id=f"prepared:{operation_id.replace('-', '')}"
            ).prepare_change(intent)
        except Exception as exc:
            mapped = self._map_native_error(
                exc, "WorldKeeper could not prepare this native change."
            )
            if mapped.status < 500:
                return self._reject_reservation(
                    operation_id, code=mapped.code, error=str(mapped)
                )
            raise mapped from exc
        if prepared.expected_parent_revision_id != native_head.head_revision_id:
            return self._reject_reservation(
                operation_id,
                code="stale_revision",
                error="The graph changed while WorldKeeper prepared the operation. Review the current graph and prepare again.",
            )
        self._store.promote_reservation(
            operation_id,
            parent_revision_id=prepared.expected_parent_revision_id,
            prepared_json=_prepared_json(prepared),
            updated_at=_iso_now(),
        )
        return {
            "operation_id": operation_id,
            "parent_revision_id": prepared.expected_parent_revision_id,
            "review": {"summary": summary},
            "status": "prepared",
        }

    def _reject_reservation(
        self, operation_id: str, *, code: str, error: str
    ) -> dict[str, Any]:
        self._store.reject_reservation(
            operation_id,
            code=code,
            error=error,
            updated_at=_iso_now(),
        )
        return {
            "operation_id": operation_id,
            "status": "rejected",
            "code": code,
            "error": error,
        }

    def _intent_for_request(
        self, request: dict[str, str], *, evidence_ref_id: str
    ) -> tuple[WorldChangeIntent, str]:
        if request["kind"] == "create_object":
            name, kind = request["name"], request["object_kind"]
            term = "dnd5e:npc" if kind == "person" else "dnd5e:location"
            metadata = self._metadata((evidence_ref_id,))
            operation = CreateObject(
                client_op_id="new-object",
                facts=(
                    CreateFact(
                        client_op_id="new-object-name",
                        predicate="dnd5e:name",
                        value=LiteralFactValue.from_json(name),
                        metadata=metadata,
                    ),
                    CreateFact(
                        client_op_id="new-object-classification",
                        predicate="dnd5e:classification",
                        value=TermRefFactValue(term),
                        metadata=metadata,
                    ),
                ),
            )
            summary = f"Create {kind} “{name}” in the demo graph."
            return (
                WorldChangeIntent(
                    space_id=self._space_id or "",
                    producer="native-graph-demo",
                    operations=(operation,),
                ),
                summary,
            )

        # A new assertion is grounded in the exact authored input admitted as
        # native text for this operation, never in caller-injected evidence IDs.
        metadata = self._metadata((evidence_ref_id,))
        operation = CreateRelationship(
            client_op_id="new-relationship",
            source=DurableObjectRef(request["source_id"]),
            predicate=f"dungeonbuddy.custom:{request['predicate']}",
            target=DurableObjectRef(request["target_id"]),
            metadata=metadata,
        )
        return (
            WorldChangeIntent(
                space_id=self._space_id or "",
                producer="native-graph-demo",
                operations=(operation,),
            ),
            f"Connect the selected objects with “{request['predicate']}”.",
        )

    def _operation_source_id(self, request: dict[str, str]) -> str:
        return f"native-graph-demo:operation-source:{request['operation_id'].replace('-', '')}"

    def _operation_source_body(self, request: dict[str, str]) -> str:
        if request["kind"] == "create_object":
            return f"Authored demo entry: {request['name']} is a {request['object_kind']}.\n"
        assert self._space_id is not None
        graph = self._read_graph()
        names = {node["id"]: node["name"] for node in graph["nodes"]}
        source = names.get(request["source_id"])
        target = names.get(request["target_id"])
        if source is None or target is None:
            raise DemoError(
                "unknown_endpoint", "Choose two objects from this demo graph.", 400
            )
        return (
            f"Authored demo relationship: {source} {request['predicate']} {target}.\n"
        )

    def _existing_operation_source(self, request: dict[str, str]) -> Any | None:
        assert self._space_id is not None
        return self._repository.get_native_source_admission_receipt(
            self._space_id, self._operation_source_id(request)
        )

    def _admit_operation_source(
        self, request: dict[str, str], *, expected_parent_revision_id: str
    ) -> Any:
        assert self._space_id is not None
        body = self._operation_source_body(request)
        raw = body.encode("utf-8")
        source_ref = request["operation_id"]
        return publish_native_text_source_evidence(
            repository=self._repository,
            request=NativeTextSourceAdmissionV1(
                space_id=self._space_id,
                admission_id=self._operation_source_id(request),
                expected_parent_revision_id=expected_parent_revision_id,
                created_at=_now(),
                body_text=body,
                expected_body_sha256=hashlib.sha256(raw).hexdigest(),
                source_classification="dungeonbuddy.source:worldbuilding",
                authority="primary",
                visibility=LabelsAnyVisibility(labels=[GM_LABEL]),
                origin=None,
                spans=[
                    NativeTextEvidenceSpanRequestV1(
                        client_ref=source_ref,
                        evidence_role="support",
                        start_byte=0,
                        end_byte=len(raw),
                        expected_slice_sha256=hashlib.sha256(raw).hexdigest(),
                    )
                ],
            ),
            domain_contract=self._domain,
            semantic_profile=self._profile,
        )

    def _verify_operation_source(self, receipt: Any, request: dict[str, str]) -> None:
        assert self._space_id is not None
        body = self._operation_source_body(request)
        if (
            receipt.space_id != self._space_id
            or receipt.admission_id != self._operation_source_id(request)
            or len(receipt.bindings) != 1
            or receipt.bindings[0].client_ref != request["operation_id"]
        ):
            raise DemoError(
                "operation_source_integrity_failure",
                "The operation's native evidence receipt failed identity verification.",
                409,
            )
        view = self._repository.open_native_source_view(self._space_id)
        source = view.get_native_text_source(
            source_artifact_id=receipt.source_artifact_id,
            source_revision_id=receipt.source_revision_id,
            span_id=receipt.bindings[0].span_id,
        )
        if (
            source is None
            or source.body_bytes != body.encode("utf-8")
            or source.span_proof.evidence_ref_id != receipt.bindings[0].evidence_ref_id
            or source.span_proof.source_revision_id != receipt.source_revision_id
            or source.span_proof.start_byte != 0
            or source.span_proof.end_byte != len(body.encode("utf-8"))
            or source.span_proof.slice_sha256
            != hashlib.sha256(body.encode("utf-8")).hexdigest()
        ):
            raise DemoError(
                "operation_source_integrity_failure",
                "The operation's exact native evidence could not be read back.",
                409,
            )

    @staticmethod
    def _metadata(evidence_ref_ids: tuple[str, ...]) -> AssertionMetadata:
        return AssertionMetadata(
            scope=(),
            visibility=Visibility(kind="public"),
            epistemic_basis="asserted",
            claim_mode="dungeonbuddy.claim:fact",
            standing="established",
            evidence_ref_ids=evidence_ref_ids,
            temporal_scope=TemporalScope(kind="timeless"),
            domain_metadata=(),
        )

    def _runtime(self, *, prepared_id: str) -> DungeonMindWorldKeeperRuntime:
        return DungeonMindWorldKeeperRuntime(
            repository=self._repository,
            domain_contract=self._domain,
            semantic_profile=self._profile,  # type: ignore[arg-type]
            clock=_now,
            prepared_id_factory=lambda: prepared_id,
        )

    def _read_graph(self) -> dict[str, Any]:
        assert self._space_id is not None
        try:
            head = self._repository.get_head(self._space_id)
            if head is None:
                raise DemoError(
                    "native_head_missing",
                    "The native demo World has no readable head.",
                    503,
                )
            stored = self._repository.get_revision(
                self._space_id, head.head_revision_id
            )
            if stored is None:
                raise DemoError(
                    "native_revision_missing",
                    "The native demo revision is unavailable.",
                    503,
                )
            payload = stored.graph_payload
            if not isinstance(payload, dict):
                raise DemoError(
                    "native_graph_integrity_failure",
                    "The native revision payload is malformed.",
                    503,
                )
            entities = payload.get("entities")
            assertions = payload.get("assertions")
            evidence = payload.get("evidence")
            aliases = payload.get("aliases")
            if (
                not isinstance(entities, list)
                or not isinstance(assertions, list)
                or not isinstance(evidence, list)
                or not isinstance(aliases, list)
                or len(entities) > MAX_NODES
                or len(assertions) > (MAX_NODES * 2 + MAX_EDGES)
                or len(evidence) > (MAX_JOURNAL_OPERATIONS + len(_SEED_LINES))
                or len(aliases) > MAX_NODES
            ):
                raise DemoError(
                    "native_graph_limit_failure",
                    "The native revision exceeds the bounded demo graph shape.",
                    503,
                )
            try:
                payload_size = len(
                    json.dumps(
                        payload, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")
                )
            except (TypeError, ValueError, UnicodeEncodeError):
                raise DemoError(
                    "native_graph_integrity_failure",
                    "The native revision payload is not canonical JSON.",
                    503,
                ) from None
            if payload_size > 512 * 1024:
                raise DemoError(
                    "native_graph_limit_failure",
                    "The native revision payload exceeds the demo read cap.",
                    503,
                )
            digest = canonical_sha256(payload)
            if (
                stored.revision.space_id != self._space_id
                or stored.revision.revision_id != head.head_revision_id
                or stored.graph_payload_sha256 != digest
                or stored.revision.graph_payload_sha256 != digest
            ):
                raise DemoError(
                    "native_revision_integrity_failure",
                    "The native graph failed exact readback verification.",
                    503,
                )
            nodes: list[dict[str, str]] = []
            names_by_id: dict[str, str] = {}
            for entity in entities:
                if not isinstance(entity, dict):
                    raise DemoError(
                        "native_graph_integrity_failure",
                        "The graph contains a malformed entity.",
                        503,
                    )
                entity_id = entity.get("entity_id")
                if not isinstance(entity_id, str):
                    raise DemoError(
                        "native_graph_integrity_failure",
                        "The graph contains an invalid entity identity.",
                        503,
                    )
                name: str | None = None
                kind = "object"
                for assertion in assertions:
                    if not isinstance(assertion, dict):
                        raise DemoError(
                            "native_graph_integrity_failure",
                            "The graph contains a malformed assertion.",
                            503,
                        )
                    if assertion.get("subject_entity_id") != entity_id:
                        continue
                    value = assertion.get("value", {})
                    if not isinstance(value, dict):
                        raise DemoError(
                            "native_graph_integrity_failure",
                            "A native assertion value is malformed.",
                            503,
                        )
                    if (
                        assertion.get("predicate") == "dnd5e:name"
                        and value.get("kind") == "literal"
                    ):
                        literal = value.get("value")
                        if isinstance(literal, str):
                            name = literal
                    elif (
                        assertion.get("predicate") == "dnd5e:classification"
                        and value.get("kind") == "term_ref"
                    ):
                        term = value.get("term")
                        if term == "dnd5e:npc":
                            kind = "person"
                        elif term == "dnd5e:location":
                            kind = "location"
                        elif isinstance(term, str):
                            kind = term
                if name is None:
                    raise DemoError(
                        "native_graph_integrity_failure",
                        "A native object has no readable name assertion.",
                        503,
                    )
                names_by_id[entity_id] = name
                nodes.append({"id": entity_id, "name": name, "kind": kind})
            if len(nodes) > MAX_NODES:
                raise DemoError(
                    "native_graph_limit_failure",
                    "The native graph exceeds the demo object cap.",
                    503,
                )
            edges: list[dict[str, str]] = []
            for assertion in assertions:
                if not isinstance(assertion, dict):
                    raise DemoError(
                        "native_graph_integrity_failure",
                        "The graph contains a malformed assertion.",
                        503,
                    )
                value = assertion.get("value", {})
                if not isinstance(value, dict):
                    raise DemoError(
                        "native_graph_integrity_failure",
                        "A native assertion value is malformed.",
                        503,
                    )
                if value.get("kind") != "entity_ref":
                    continue
                source_id = assertion.get("subject_entity_id")
                target_id = value.get("entity_id")
                predicate = assertion.get("predicate")
                if (
                    source_id not in names_by_id
                    or target_id not in names_by_id
                    or not isinstance(predicate, str)
                ):
                    raise DemoError(
                        "native_graph_integrity_failure",
                        "A native relationship has an invalid endpoint.",
                        503,
                    )
                label = predicate.removeprefix("dungeonbuddy.custom:")
                if ":" in label:
                    label = label.rsplit(":", 1)[1]
                edges.append(
                    {
                        "id": assertion["assertion_id"],
                        "source_id": source_id,
                        "target_id": target_id,
                        "predicate": label,
                    }
                )
            if len(edges) > MAX_EDGES:
                raise DemoError(
                    "native_graph_limit_failure",
                    "The native graph exceeds the demo relationship cap.",
                    503,
                )
            nodes.sort(key=lambda item: (item["name"].casefold(), item["id"]))
            edges.sort(key=lambda item: item["id"])
            return {
                "world_id": self._space_id,
                "revision_id": head.head_revision_id,
                "graph_sha256": digest,
                "nodes": nodes,
                "edges": edges,
                "storage": self._storage_label,
                "capabilities": {
                    "create": True,
                    "connect": True,
                    "rename": False,
                    "delete": False,
                    "object_kinds": ["person", "location"],
                },
                "limitations": [
                    "Event creation is unavailable because the current demo authoring profile has no declared event classification."
                ],
            }
        except DemoError:
            raise
        except (PersistenceUnavailableError, PersistenceIntegrityError) as exc:
            raise DemoError(
                "native_authority_unavailable",
                "The native DungeonMind graph could not be read.",
                503,
            ) from exc
        except Exception as exc:
            raise DemoError(
                "native_graph_integrity_failure",
                "The native DungeonMind graph could not be safely decoded.",
                503,
            ) from exc

    def _validate_prepare_request(
        self, request: dict[str, Any]
    ) -> tuple[dict[str, str], str]:
        if not isinstance(request, dict):
            raise DemoError("invalid_request", "The operation must be a JSON object.")
        kind = request.get("kind")
        if kind not in _ALLOWED_API_FIELDS:
            raise DemoError(
                "unsupported_operation",
                "Only create_object and connect operations are supported.",
            )
        if set(request) != _ALLOWED_API_FIELDS[kind]:
            raise DemoError(
                "invalid_request", "The operation contains missing or unknown fields."
            )
        normalized: dict[str, str] = {
            "operation_id": _parse_uuid(request["operation_id"]),
            "expected_revision_id": _nonblank_text(
                request["expected_revision_id"], "expected_revision_id"
            ),
            "kind": kind,
        }
        if kind == "create_object":
            normalized["name"] = _nonblank_text(
                request["name"], "name", max_bytes=MAX_NAME_BYTES
            )
            normalized["object_kind"] = _nonblank_text(
                request["object_kind"], "object_kind", max_bytes=32
            )
            if normalized["object_kind"] not in {"person", "location", "event"}:
                raise DemoError(
                    "unsupported_kind", "Use person, location, or event as object_kind."
                )
        else:
            normalized["source_id"] = _nonblank_text(request["source_id"], "source_id")
            normalized["target_id"] = _nonblank_text(request["target_id"], "target_id")
            normalized["predicate"] = _nonblank_text(
                request["predicate"], "predicate", max_bytes=MAX_LABEL_BYTES
            )
            if not _CUSTOM_LABEL.fullmatch(normalized["predicate"]):
                raise DemoError(
                    "invalid_predicate",
                    "Relationship labels may use lowercase letters, numbers, dots, underscores, and hyphens.",
                )
        # The request hash binds the normalized, exact API fields and values.
        return normalized, canonical_json(normalized)

    def _prepared_response(
        self, operation_id: str, request: dict[str, str], record: dict[str, Any]
    ) -> dict[str, Any]:
        self._record_prepared(record)
        if record["status"] == "committed":
            self._verify_committed_record(self._record_prepared(record), record)
        return {
            "operation_id": operation_id,
            "parent_revision_id": record["parent_revision_id"],
            "review": {"summary": self._summary_for_request(request)},
            "status": "prepared",
        }

    @staticmethod
    def _summary_for_request(request: dict[str, str]) -> str:
        if request["kind"] == "create_object":
            return f"Create {request['object_kind']} “{request['name']}” in the demo graph."
        return f"Connect the selected objects with “{request['predicate']}”."

    def _summary_from_record(self, record: dict[str, Any]) -> str:
        return self._summary_for_request(record["request"])

    def _record_prepared(self, record: dict[str, Any]) -> PreparedWorldChange:
        try:
            operation_id = record.get("operation_id")
            request = record.get("request")
            if not isinstance(operation_id, str) or not isinstance(request, dict):
                raise ValueError("operation identity is missing from its journal row")
            prepared = decode_prepared(record["prepared"])
            if not isinstance(prepared, PreparedWorldChange):
                raise ValueError(
                    "prepared record did not decode to a WorldKeeper change"
                )
            if request.get("kind") == "seed":
                expected_request = {
                    "kind": "seed",
                    "seed_version": 1,
                    "source_admission_id": _SEED_ADMISSION_ID,
                    "expected_revision_id": record["parent_revision_id"],
                }
                if (
                    operation_id != _SEED_OPERATION_ID
                    or request != expected_request
                    or prepared.prepared_change_id != _SEED_PREPARED_ID
                ):
                    raise ValueError("seed operation identity does not match its row")
                source = self._repository.get_native_source_admission_receipt(
                    self._space_id, _SEED_ADMISSION_ID
                )
                if (
                    source is None
                    or source.published_revision_id != record["parent_revision_id"]
                ):
                    raise ValueError("seed source receipt is unavailable")
                self._verify_seed_source(source)
                intent = self._seed_intent(source)
            else:
                normalized_request, request_json = self._validate_prepare_request(
                    request
                )
                if (
                    normalized_request != request
                    or request_json != canonical_json(request)
                    or normalized_request["operation_id"] != operation_id
                    or prepared.prepared_change_id
                    != f"prepared:{operation_id.replace('-', '')}"
                ):
                    raise ValueError(
                        "operation row, request, parent, and prepared ids do not match"
                    )
                source = self._existing_operation_source(normalized_request)
                if (
                    source is None
                    or source.publication_receipt.expected_parent_revision_id
                    != normalized_request["expected_revision_id"]
                    or source.published_revision_id != record["parent_revision_id"]
                    or source.published_revision_id
                    != prepared.expected_parent_revision_id
                ):
                    raise ValueError("operation source does not bind to its request")
                self._verify_operation_source(source, normalized_request)
                intent, _summary = self._intent_for_request(
                    normalized_request,
                    evidence_ref_id=source.bindings[0].evidence_ref_id,
                )
            if (
                prepared.space_id != self._space_id
                or prepared.producer != "native-graph-demo"
                or prepared.expected_parent_revision_id != record["parent_revision_id"]
                or prepared.prepared_change_id != prepared.dungeonmind_publication_id
                or prepared.prepared_operations != intent.operations
            ):
                raise ValueError(
                    "prepared record identity or intent does not match its journal row"
                )
            parent = self._repository.get_revision(
                self._space_id, prepared.expected_parent_revision_id
            )
            if (
                parent is None
                or parent.graph_payload_sha256 != prepared.parent_graph_payload_sha256
                or canonical_sha256(parent.graph_payload)
                != prepared.parent_graph_payload_sha256
            ):
                raise ValueError(
                    "prepared parent payload does not match native readback"
                )
            return prepared
        except Exception as exc:
            raise DemoError(
                "prepared_operation_integrity_failure",
                "The saved preparation failed integrity verification and was not committed.",
                409,
            ) from exc

    def _confirm_record(
        self,
        operation_id: str,
        prepared: PreparedWorldChange,
        record: dict[str, Any],
        *,
        receipts_checked: bool = False,
    ) -> dict[str, Any]:
        if not receipts_checked:
            state = self._recover_native_publication(prepared)
            if state == "committed":
                receipts_checked = True
            elif state == "uncertain":
                self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
                return {
                    "operation_id": operation_id,
                    "status": "unknown",
                    "message": "Native publication receipts are incomplete; the outcome remains uncertain.",
                }
        # A process can die after the native write starts but before its response
        # or local receipt update is observed. Commit the unknown state first so
        # that recovery never treats an attempted publication as merely prepared.
        self._mark_operation_unknown_before_dispatch(operation_id)
        try:
            # WorldKeeper replays through the same native publication id and
            # verifies the exact child. A lost response therefore cannot mint a
            # second semantic operation.
            result = self._runtime(
                prepared_id=prepared.prepared_change_id
            ).commit_prepared_change(prepared, confirmed_by="native-graph-demo-user")
            if not result.verification.exact_child_read_back:
                self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
                return {
                    "operation_id": operation_id,
                    "status": "unknown",
                    "message": "The native child could not be confirmed by exact readback.",
                }
            committed_json = canonical_json(
                {
                    "prepared_change_id": result.prepared_change_id,
                    "publication_id": result.dungeonmind_publication_id,
                    "parent_revision_id": result.expected_parent_revision_id,
                    "child_revision_id": result.child_revision_id,
                    "graph_sha256": result.child_graph_payload_sha256,
                    "objects": [
                        {
                            "client_op_id": item.client_op_id,
                            "id": item.durable_object_id,
                        }
                        for item in result.object_results
                    ],
                    "assertions": [
                        {
                            "client_op_id": item.client_op_id,
                            "id": item.durable_assertion_id,
                            "role": item.semantic_role,
                        }
                        for item in result.assertion_results
                    ],
                }
            )
            self._store.mark_operation_committed(
                operation_id, committed_json=committed_json, updated_at=_iso_now()
            )
            return {
                "operation_id": operation_id,
                "status": "committed",
                "graph": self._read_graph(),
            }
        except PreparedChangeStale:
            message = "The graph changed after review. Review the current graph and prepare a new operation."
            self._store.mark_operation_rejected(
                operation_id,
                code="stale_revision",
                error=message,
                updated_at=_iso_now(),
            )
            return {
                "operation_id": operation_id,
                "status": "rejected",
                "code": "stale_revision",
                "error": message,
            }
        except PreparedChangeConflict as exc:
            raise DemoError(
                "publication_conflict",
                "This operation id is bound to a different native publication.",
                409,
            ) from exc
        except (CommittedChangeOutcomeUnknown, CommittedChangeVerificationUnavailable):
            self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
            return {
                "operation_id": operation_id,
                "status": "unknown",
                "message": "Native publication could not be confirmed yet. The exact prepared operation is retained for recovery.",
            }
        except (
            PreparedChangeIntegrityFailure,
            CommitAuthorityIntegrityFailure,
            CommittedChangeVerificationIntegrityFailure,
        ) as exc:
            self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
            raise DemoError(
                "prepared_operation_integrity_failure",
                "WorldKeeper rejected the saved preparation or native exact readback.",
                409,
            ) from exc
        except (PersistenceUnavailableError, PersistenceIntegrityError):
            self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
            return {
                "operation_id": operation_id,
                "status": "unknown",
                "message": "The native authority is unavailable; the exact prepared operation is retained for recovery.",
            }
        except Exception as exc:
            mapped = self._map_native_error(
                exc, "The native change could not be confirmed."
            )
            if mapped.status >= 500:
                self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
            raise mapped from exc

    def _mark_operation_unknown_before_dispatch(self, operation_id: str) -> None:
        """Durably mark the native write attempt before calling WorldKeeper."""
        self._store.mark_operation_unknown(operation_id, updated_at=_iso_now())
        with self._store.checkpoint():
            pass

    def _recover_native_publication(self, prepared: PreparedWorldChange) -> str:
        """Check native receipts before any exact WorldKeeper replay."""
        try:
            assert self._space_id is not None
            aggregate = self._repository.get_prospective_publication(
                self._space_id, prepared.dungeonmind_publication_id
            )
            receipt = self._repository.get_publication_receipt(
                self._space_id, prepared.dungeonmind_publication_id
            )
        except Exception:
            return "uncertain"
        if aggregate is None and receipt is None:
            return "absent"
        if aggregate is None or receipt is None:
            return "uncertain"
        if (
            aggregate.publication_receipt != receipt
            or aggregate.publication_receipt.space_id != self._space_id
            or aggregate.publication_receipt.publication_id
            != prepared.dungeonmind_publication_id
            or aggregate.prospective_result.publication_id
            != prepared.dungeonmind_publication_id
            or aggregate.publication_receipt.published_revision_id
            != aggregate.prospective_result.published_revision_id
        ):
            return "uncertain"
        return "committed"

    def _verify_committed_record(
        self, prepared: PreparedWorldChange, record: dict[str, Any]
    ) -> None:
        committed = record.get("committed")
        if not isinstance(committed, dict):
            raise DemoError(
                "journal_integrity_failure",
                "A committed operation has no recovery record.",
                503,
            )
        if (
            committed.get("prepared_change_id") != prepared.prepared_change_id
            or committed.get("publication_id") != prepared.dungeonmind_publication_id
            or committed.get("parent_revision_id")
            != prepared.expected_parent_revision_id
        ):
            raise DemoError(
                "journal_integrity_failure",
                "The committed operation recovery binding changed.",
                503,
            )
        state = self._recover_native_publication(prepared)
        if state != "committed":
            raise DemoError(
                "native_receipt_missing",
                "The native publication receipt is unavailable, so the committed result cannot be revalidated.",
                503,
            )
        assert self._space_id is not None
        try:
            aggregate = self._repository.get_prospective_publication(
                self._space_id, prepared.dungeonmind_publication_id
            )
            receipt = self._repository.get_publication_receipt(
                self._space_id, prepared.dungeonmind_publication_id
            )
        except Exception as exc:
            raise DemoError(
                "native_authority_unavailable",
                "The native publication receipt could not be verified.",
                503,
            ) from exc
        if (
            aggregate is None
            or receipt is None
            or aggregate.publication_receipt != receipt
            or receipt.space_id != self._space_id
            or receipt.publication_id != prepared.dungeonmind_publication_id
            or receipt.expected_parent_revision_id
            != prepared.expected_parent_revision_id
            or receipt.published_revision_id != committed.get("child_revision_id")
            or receipt.graph_payload_sha256 != committed.get("graph_sha256")
        ):
            raise DemoError(
                "native_receipt_integrity_failure",
                "The native publication receipt does not match its committed operation record.",
                503,
            )
        native_results = {
            item.client_op_id: (item.result_kind, item.durable_id)
            for item in aggregate.prospective_result.results
        }
        journal_results: dict[str, tuple[str, str]] = {}
        for item in committed.get("objects", []):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("client_op_id"), str)
                or not isinstance(item.get("id"), str)
            ):
                raise DemoError(
                    "journal_integrity_failure",
                    "The committed object result record is malformed.",
                    503,
                )
            journal_results[item["client_op_id"]] = ("entity", item["id"])
        for item in committed.get("assertions", []):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("client_op_id"), str)
                or not isinstance(item.get("id"), str)
            ):
                raise DemoError(
                    "journal_integrity_failure",
                    "The committed assertion result record is malformed.",
                    503,
                )
            journal_results[item["client_op_id"]] = ("assertion", item["id"])
        if not native_results or journal_results != native_results:
            raise DemoError(
                "native_result_integrity_failure",
                "The committed operation result bindings do not match DungeonMind receipts.",
                503,
            )
        child_id = committed.get("child_revision_id")
        if not isinstance(child_id, str):
            raise DemoError(
                "journal_integrity_failure",
                "The committed native child identity is malformed.",
                503,
            )
        try:
            child = self._repository.get_revision(self._space_id, child_id)
        except Exception as exc:
            raise DemoError(
                "native_authority_unavailable",
                "The exact committed native child could not be read.",
                503,
            ) from exc
        if (
            child is None
            or child.revision.revision_id != child_id
            or child.graph_payload_sha256 != committed.get("graph_sha256")
            or canonical_sha256(child.graph_payload) != committed.get("graph_sha256")
        ):
            raise DemoError(
                "native_child_integrity_failure",
                "The committed native child no longer matches its exact verified result.",
                503,
            )

    def _map_native_error(self, exc: Exception, fallback: str) -> DemoError:
        if isinstance(exc, DemoError):
            return exc
        if isinstance(exc, (PersistenceUnavailableError, OSError)):
            return DemoError("native_authority_unavailable", fallback, 503)
        if isinstance(exc, StaleParentRevisionError):
            return DemoError(
                "stale_revision",
                "The native graph changed. Review it and prepare again.",
                409,
            )
        reason = getattr(exc, "reason", None)
        if isinstance(reason, str):
            return DemoError(
                "invalid_native_change",
                f"WorldKeeper rejected this operation ({reason}).",
                400,
            )
        if isinstance(exc, (ValueError, TypeError, DungeonMindError)):
            return DemoError("native_change_rejected", fallback, 400)
        return DemoError("native_authority_error", fallback, 503)
