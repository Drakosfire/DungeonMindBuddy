"""Admit an immutable Build worldbuilding source to its managed native World."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from apps.live_control_server import config
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentSnapshot,
    get_workspace_document_snapshot,
)
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRegistryError,
    get_world_container,
)
from dungeonmind.application.vnext import (
    initialize_empty_knowledge_space,
    open_admitted_native_text,
    open_native_text_source_access_context,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.common import LabelsAllVisibility
from dungeonmind.contracts.vnext.native_source import (
    MAX_NATIVE_TEXT_BYTES,
    NativeTextEvidenceSpanRequestV1,
    NativeTextSourceAdmissionV1,
    NativeTextSourceOriginV1,
)
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresNativeSourceEvidenceRepository,
)

from graph_memory.vnext.domain_runtime import (
    DUNGEONBUDDY_DOMAIN_DIGEST,
    DUNGEONBUDDY_PROFILE_DIGEST,
    GM_LABEL,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_world_domain_contract,
)

SCHEMA_VERSION = "dmb_native_world_source_admission_status_v1"
SOURCE_CLASSIFICATION = "dungeonbuddy.source:worldbuilding"
ORIGIN_NAMESPACE = "dungeonbuddy.workspace-document-registry"
WHOLE_DOCUMENT_SPAN_REF = "whole-document-v1"
MAX_ADMISSION_ATTEMPTS = 2


class NativeWorldSourceAdmissionError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class NativeWorldSourceAdmissionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_native_world_source_admission_status_v1"] = SCHEMA_VERSION
    state: Literal["pending", "admitted"]
    code: str | None = None
    message: str | None = None
    world_id: str
    document_id: str
    loaded_revision: int
    body_sha256: str
    admission_id: str
    space_id: str
    published_revision_id: str | None = None
    source_artifact_id: str | None = None
    source_revision_id: str | None = None
    evidence_ref_id: str | None = None
    span_start_byte: int | None = None
    span_end_byte: int | None = None


def _parse_timestamp(raw: str, *, field: str) -> datetime:
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise NativeWorldSourceAdmissionError(
            "source_metadata_invalid", f"{field} is not a valid timestamp"
        ) from exc
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "\0".join(parts).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()}"


def _descriptors():
    domain = dungeonbuddy_world_domain_contract()
    profile = dungeonbuddy_dnd5e_semantic_profile()
    if canonical_sha256(domain.model_dump(mode="json")) != DUNGEONBUDDY_DOMAIN_DIGEST:
        raise NativeWorldSourceAdmissionError(
            "descriptor_drift", "The accepted DungeonBuddy World descriptor has changed", status_code=503
        )
    if canonical_sha256(profile.model_dump(mode="json")) != DUNGEONBUDDY_PROFILE_DIGEST:
        raise NativeWorldSourceAdmissionError(
            "descriptor_drift", "The accepted DungeonBuddy D&D profile has changed", status_code=503
        )
    return domain, profile


def _repository():
    database_url = config.world_graph_authority_database_url()
    if not database_url:
        raise NativeWorldSourceAdmissionError(
            "authority_unavailable",
            f"DungeonMind authority database URL is not configured ({config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV})",
            status_code=503,
        )
    try:
        return PostgresNativeSourceEvidenceRepository(PostgresDatabase(database_url))
    except Exception as exc:
        raise NativeWorldSourceAdmissionError(
            "authority_unavailable", "DungeonMind authority is unavailable", status_code=503
        ) from exc


def _authority_failure(exc: Exception, *, default_code: str) -> NativeWorldSourceAdmissionError:
    name = type(exc).__name__
    unavailable = name in {
        "PersistenceUnavailableError",
        "KnowledgePublicationOutcomeUnknownError",
    }
    return NativeWorldSourceAdmissionError(
        "authority_unavailable" if unavailable else default_code,
        "DungeonMind authority is unavailable" if unavailable else "Native World source operation failed",
        status_code=503 if unavailable else 409,
    )


def _load_exact_snapshot(
    root,
    document_id: str,
    expected_revision: int | None,
) -> tuple[WorkspaceDocumentSnapshot, bytes, str, str]:
    try:
        snapshot = get_workspace_document_snapshot(root, document_id)
    except Exception as exc:
        status_code = int(getattr(exc, "status_code", 500))
        raise NativeWorldSourceAdmissionError(
            "workspace_source_unavailable", str(exc), status_code=status_code
        ) from exc
    record = snapshot.record
    if record.kind != "worldbuilding_source" or record.source_domain != "worldbuilding":
        raise NativeWorldSourceAdmissionError(
            "unsupported_source", "Only worldbuilding sources can be admitted", status_code=422
        )
    if record.status != "active" or record.content_status != "committed" or not snapshot.file_exists:
        raise NativeWorldSourceAdmissionError(
            "source_not_committed", "The worldbuilding source must be active and committed"
        )
    if record.visibility_state != "internal":
        raise NativeWorldSourceAdmissionError(
            "unsupported_visibility", "This source must remain GM-private", status_code=422
        )
    if not record.world_id or record.campaign_id != record.world_id:
        raise NativeWorldSourceAdmissionError(
            "managed_world_missing", "The source is not attached to one managed World"
        )
    if expected_revision is not None and snapshot.loaded_revision != expected_revision:
        raise NativeWorldSourceAdmissionError(
            "source_revision_changed",
            "The committed source changed; refresh or reselect it before admission",
        )
    body_bytes = snapshot.markdown.encode("utf-8", errors="strict")
    actual_digest = _digest(body_bytes)
    if len(body_bytes) > MAX_NATIVE_TEXT_BYTES:
        raise NativeWorldSourceAdmissionError(
            "source_too_large",
            f"The native text source exceeds the {MAX_NATIVE_TEXT_BYTES}-byte admission limit",
            status_code=413,
        )
    if not body_bytes or actual_digest != snapshot.content_sha256:
        raise NativeWorldSourceAdmissionError(
            "source_digest_mismatch", "The committed source snapshot failed its digest check"
        )
    try:
        get_world_container(root, record.world_id)
    except WorldContainerRegistryError as exc:
        raise NativeWorldSourceAdmissionError(
            "managed_world_missing", "The source World is not present in the managed World registry",
            status_code=exc.status_code,
        ) from exc
    admission_id = _stable_id(
        "dmb-world-source",
        record.world_id,
        record.document_id,
        str(snapshot.loaded_revision),
        actual_digest,
    )
    return snapshot, body_bytes, actual_digest, admission_id


def _origin(snapshot: WorkspaceDocumentSnapshot) -> NativeTextSourceOriginV1:
    return NativeTextSourceOriginV1(
        namespace=ORIGIN_NAMESPACE,
        object_id=snapshot.record.document_id,
        revision_id=f"registry-revision:{snapshot.loaded_revision}",
    )


def _verify_receipt_and_source(
    *,
    repository,
    snapshot: WorkspaceDocumentSnapshot,
    body_bytes: bytes,
    body_sha256: str,
    admission_id: str,
    receipt,
) -> NativeWorldSourceAdmissionStatus:
    record = snapshot.record
    world_id = record.world_id
    assert world_id is not None
    domain, _profile = _descriptors()
    expected_origin = _origin(snapshot)
    if (
        receipt.space_id != world_id
        or receipt.admission_id != admission_id
        or receipt.origin != expected_origin
        or len(receipt.bindings) != 1
        or receipt.bindings[0].client_ref != WHOLE_DOCUMENT_SPAN_REF
    ):
        raise NativeWorldSourceAdmissionError(
            "admission_receipt_mismatch", "Stored native admission does not match this source revision"
        )
    binding = receipt.bindings[0]
    try:
        context = open_native_text_source_access_context(
            repository=repository,
            space_id=world_id,
            revision_id=receipt.published_revision_id,
            domain_contract=domain,
            audience_labels=[GM_LABEL],
        )
        opened = open_admitted_native_text(context, binding.evidence_ref_id)
    except NativeWorldSourceAdmissionError:
        raise
    except Exception as exc:
        raise _authority_failure(exc, default_code="native_readback_failed") from exc
    if (
        opened.status != "available"
        or opened.body_text is None
        or opened.body_text.encode("utf-8") != body_bytes
        or opened.body_sha256 != body_sha256
        or opened.span_start_byte != 0
        or opened.span_end_byte != len(body_bytes)
        or opened.span_sha256 != body_sha256
    ):
        raise NativeWorldSourceAdmissionError(
            "admission_readback_mismatch", "DungeonMind did not return the exact admitted source bytes"
        )
    return NativeWorldSourceAdmissionStatus(
        state="admitted",
        world_id=world_id,
        space_id=world_id,
        document_id=record.document_id,
        loaded_revision=snapshot.loaded_revision,
        body_sha256=body_sha256,
        admission_id=admission_id,
        published_revision_id=receipt.published_revision_id,
        source_artifact_id=receipt.source_artifact_id,
        source_revision_id=receipt.source_revision_id,
        evidence_ref_id=binding.evidence_ref_id,
        span_start_byte=opened.span_start_byte,
        span_end_byte=opened.span_end_byte,
    )


def get_native_world_source_status(
    root, document_id: str, *, expected_revision: int | None = None
) -> NativeWorldSourceAdmissionStatus:
    snapshot, body_bytes, body_sha256, admission_id = _load_exact_snapshot(
        root, document_id, expected_revision
    )
    world_id = snapshot.record.world_id
    assert world_id is not None
    try:
        repository = _repository()
    except NativeWorldSourceAdmissionError as exc:
        if exc.code != "authority_unavailable":
            raise
        return NativeWorldSourceAdmissionStatus(
            state="pending",
            code=exc.code,
            message="Source is saved; native World admission status is temporarily unavailable",
            world_id=world_id,
            space_id=world_id,
            document_id=document_id,
            loaded_revision=snapshot.loaded_revision,
            body_sha256=body_sha256,
            admission_id=admission_id,
        )
    try:
        receipt = repository.get_native_source_admission_receipt(world_id, admission_id)
    except Exception as exc:
        mapped = _authority_failure(exc, default_code="native_status_failed")
        if mapped.code != "authority_unavailable":
            raise mapped from exc
        return NativeWorldSourceAdmissionStatus(
            state="pending",
            code=mapped.code,
            message="Source is saved; native World admission status is temporarily unavailable",
            world_id=world_id,
            space_id=world_id,
            document_id=document_id,
            loaded_revision=snapshot.loaded_revision,
            body_sha256=body_sha256,
            admission_id=admission_id,
        )
    if receipt is None:
        return NativeWorldSourceAdmissionStatus(
            state="pending",
            code="native_admission_pending",
            message="Saved source has not yet been admitted to its native World",
            world_id=world_id,
            space_id=world_id,
            document_id=document_id,
            loaded_revision=snapshot.loaded_revision,
            body_sha256=body_sha256,
            admission_id=admission_id,
        )
    try:
        return _verify_receipt_and_source(
            repository=repository,
            snapshot=snapshot,
            body_bytes=body_bytes,
            body_sha256=body_sha256,
            admission_id=admission_id,
            receipt=receipt,
        )
    except NativeWorldSourceAdmissionError as exc:
        if exc.code != "authority_unavailable":
            raise
        return NativeWorldSourceAdmissionStatus(
            state="pending",
            code=exc.code,
            message="Saved source admission exists but native readback is temporarily unavailable",
            world_id=world_id,
            space_id=world_id,
            document_id=document_id,
            loaded_revision=snapshot.loaded_revision,
            body_sha256=body_sha256,
            admission_id=admission_id,
        )


def admit_native_world_source(
    root, document_id: str, *, expected_revision: int
) -> NativeWorldSourceAdmissionStatus:
    snapshot, body_bytes, body_sha256, admission_id = _load_exact_snapshot(
        root, document_id, expected_revision
    )
    record = snapshot.record
    world_id = record.world_id
    assert world_id is not None
    domain, profile = _descriptors()
    repository = _repository()
    try:
        prior = repository.get_native_source_admission_receipt(world_id, admission_id)
    except Exception as exc:
        raise _authority_failure(exc, default_code="native_status_failed") from exc
    if prior is not None:
        return _verify_receipt_and_source(
            repository=repository,
            snapshot=snapshot,
            body_bytes=body_bytes,
            body_sha256=body_sha256,
            admission_id=admission_id,
            receipt=prior,
        )

    created_at = _parse_timestamp(
        get_world_container(root, world_id).created_at,
        field="managed World created_at",
    )
    initialization_id = _stable_id("dmb-world-genesis", world_id)
    try:
        initialize_empty_knowledge_space(
            repository=repository,
            space_id=world_id,
            initialization_id=initialization_id,
            created_at=created_at,
            domain_contract=domain,
            semantic_profile=profile,
        )
    except Exception as exc:
        raise _authority_failure(exc, default_code="native_genesis_failed") from exc

    expected_origin = _origin(snapshot)
    for attempt in range(MAX_ADMISSION_ATTEMPTS):
        try:
            head = repository.get_head(world_id)
        except Exception as exc:
            raise _authority_failure(exc, default_code="native_status_failed") from exc
        if head is None:
            raise NativeWorldSourceAdmissionError(
                "native_genesis_missing", "Native World initialization did not create a head", status_code=503
            )
        span = NativeTextEvidenceSpanRequestV1(
            client_ref=WHOLE_DOCUMENT_SPAN_REF,
            evidence_role="context",
            start_byte=0,
            end_byte=len(body_bytes),
            expected_slice_sha256=body_sha256,
        )
        request = NativeTextSourceAdmissionV1(
            space_id=world_id,
            admission_id=admission_id,
            expected_parent_revision_id=head.head_revision_id,
            created_at=_parse_timestamp(record.updated_at, field="source updated_at"),
            body_text=snapshot.markdown,
            expected_body_sha256=body_sha256,
            source_classification=SOURCE_CLASSIFICATION,
            authority="primary",
            visibility=LabelsAllVisibility(labels=[GM_LABEL]),
            origin=expected_origin,
            spans=[span],
        )
        try:
            receipt = publish_native_text_source_evidence(
                repository=repository,
                request=request,
                domain_contract=domain,
                semantic_profile=profile,
            )
            return _verify_receipt_and_source(
                repository=repository,
                snapshot=snapshot,
                body_bytes=body_bytes,
                body_sha256=body_sha256,
                admission_id=admission_id,
                receipt=receipt,
            )
        except Exception as exc:
            try:
                recovered = repository.get_native_source_admission_receipt(world_id, admission_id)
            except Exception as probe_error:
                raise NativeWorldSourceAdmissionError(
                    "authority_unavailable",
                    "Source is saved; native admission outcome cannot yet be verified",
                    status_code=503,
                ) from probe_error
            if recovered is not None:
                return _verify_receipt_and_source(
                    repository=repository,
                    snapshot=snapshot,
                    body_bytes=body_bytes,
                    body_sha256=body_sha256,
                    admission_id=admission_id,
                    receipt=recovered,
                )
            if type(exc).__name__ != "KnowledgeStaleParentRevisionError" or attempt + 1 >= MAX_ADMISSION_ATTEMPTS:
                mapped = _authority_failure(exc, default_code="native_admission_failed")
                raise NativeWorldSourceAdmissionError(
                    mapped.code,
                    "Source is saved; native World admission is pending",
                    status_code=mapped.status_code,
                ) from exc
            latest, _latest_bytes, latest_digest, _latest_admission_id = _load_exact_snapshot(
                root, document_id, expected_revision
            )
            if (
                latest.loaded_revision != snapshot.loaded_revision
                or latest_digest != body_sha256
                or latest.markdown != snapshot.markdown
            ):
                raise NativeWorldSourceAdmissionError(
                    "source_revision_changed",
                    "The source changed during admission; refresh or reselect it",
                ) from exc

    raise NativeWorldSourceAdmissionError(
        "native_admission_failed", "Source is saved; native World admission is pending", status_code=503
    )
