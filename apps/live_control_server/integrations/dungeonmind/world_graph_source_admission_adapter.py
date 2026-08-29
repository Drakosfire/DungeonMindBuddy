"""DungeonMind-backed Graph Review source admission (CUTOVER D.2C4).

Maps Buddy SourceArtifact + revision token onto SourceArtifactV2 + SourceRevision
using the already-landed mapping family and catalog-aware `_build_pair_to_dm`
derivation, then prove/admits through SourceRepository put/get/snapshot.
PostgreSQL stays inside this adapter. No new DungeonMind command or UoW.

Pure source-mapping helpers live here (and collision math in
``world_graph_writes``) so this mounted path does not import
``integrations/dungeonmind_kernel/**`` or the Buddy graph-engine packages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    WorldGraphWriteError,
    catalog_aware_source_revision_ids,
    _open_repository_bundle,
    _require_database_url,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    AdmittedSourceIdentity,
    WorldGraphSourceAdmissionError,
    WorldGraphSourceAdmissionRequest,
)


def _hex_digest(value: str) -> str:
    return value.removeprefix("sha256:").strip().lower()


def _digest_from_buddy_revision(buddy_revision_id: str) -> str | None:
    if buddy_revision_id.startswith("sha256:"):
        digest = buddy_revision_id.removeprefix("sha256:")
        if len(digest) == 64:
            return digest
    return None


def _parse_optional_aware(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not value or not str(value).strip():
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _map_source_domain(raw: str) -> Any:
    from dungeonmind.contracts.evidence import SourceDomain

    return {
        "recap": SourceDomain.SESSION_RECAP,
        "session_recap": SourceDomain.SESSION_RECAP,
        "worldbuilding": SourceDomain.WORLDBUILDING,
        "rulebook": SourceDomain.RULEBOOK,
        "prep": SourceDomain.PREP,
        "manual": SourceDomain.MANUAL,
    }.get(raw)


def _store_artifact_v2(
    artifact: Any,
    *,
    current_revision_id: str | None,
    uri: str | None = None,
    lineage: dict[str, Any] | None = None,
) -> Any:
    from dungeonmind.contracts.evidence import (
        SourceArtifactV2,
        SourceDomain,
        SourceReviewState,
        SourceStatus,
        WorkspaceDocumentRefV1,
    )
    from dungeonmind.contracts.vocabulary import Visibility

    domain_key = str(artifact.source_domain)
    domain = _map_source_domain(domain_key) or SourceDomain.OTHER
    workspace_ref = None
    if artifact.workspace_document_id is not None:
        workspace_ref = WorkspaceDocumentRefV1(
            document_id=artifact.workspace_document_id,
            revision=int(artifact.workspace_document_revision or 1),
        )
    review_state = None
    if artifact.authority_state in {"draft", "reviewed", "canonical"}:
        review_state = SourceReviewState(artifact.authority_state)
    merged_lineage = dict(artifact.lineage or {})
    if lineage:
        merged_lineage.update(lineage)
    return SourceArtifactV2(
        source_artifact_id=artifact.source_artifact_id,
        source_domain_key=domain_key,
        source_domain=domain,
        world_id=artifact.world_id,
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        uri=uri if uri is not None else artifact.uri,
        current_revision_id=current_revision_id,
        authority=None,
        visibility=Visibility.GM,
        artifact_kind=artifact.artifact_kind,
        document_class=artifact.document_class,
        review_state=review_state,
        source_visibility_state=artifact.visibility_state,
        workspace_document_ref=workspace_ref,
        lineage=merged_lineage,
        status=SourceStatus(artifact.status),
        created_at=_parse_optional_aware(artifact.created_at),
        updated_at=_parse_optional_aware(artifact.updated_at),
    )


def _raise_port(exc: WorldGraphWriteError) -> None:
    port_code = "authority_unavailable"
    if exc.code == "governed_write_inexpressible":
        port_code = "inexpressible"
    raise WorldGraphSourceAdmissionError(
        str(exc),
        code=port_code,  # type: ignore[arg-type]
        details=dict(exc.details or {}),
    ) from exc


def _map_provider_error(exc: BaseException) -> WorldGraphSourceAdmissionError:
    from dungeonmind.domain.errors import (
        IdempotencyConflictError,
        PersistenceIntegrityError,
        PersistenceUnavailableError,
    )

    if isinstance(exc, IdempotencyConflictError):
        return WorldGraphSourceAdmissionError(
            str(exc),
            code="source_identity_conflict",
            details={"reason": type(exc).__name__},
        )
    if isinstance(exc, PersistenceUnavailableError):
        return WorldGraphSourceAdmissionError(
            str(exc),
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        )
    if isinstance(exc, PersistenceIntegrityError):
        return WorldGraphSourceAdmissionError(
            str(exc),
            code="source_identity_conflict",
            details={"reason": type(exc).__name__},
        )
    return WorldGraphSourceAdmissionError(
        str(exc),
        code="authority_unavailable",
        details={"reason": type(exc).__name__},
    )


def _revision_created_at(artifact: Any) -> datetime:
    raw_created = getattr(artifact, "created_at", None)
    if isinstance(raw_created, datetime):
        return (
            raw_created
            if raw_created.tzinfo is not None
            else raw_created.replace(tzinfo=UTC)
        )
    created_at = _parse_optional_aware(raw_created)
    if created_at is None:
        raise WorldGraphSourceAdmissionError(
            "Graph Review source artifact is missing created_at",
            code="inexpressible",
            details={
                "source_artifact_id": str(getattr(artifact, "source_artifact_id", "")),
            },
        )
    return created_at


def _map_buddy_source(
    request: WorldGraphSourceAdmissionRequest,
    sources: Any,
) -> tuple[Any, Any, str]:
    from dungeonmind.contracts.evidence import SourceRevision

    artifact = request.source_artifact
    artifact_id = str(getattr(artifact, "source_artifact_id", "") or "").strip()
    buddy_token = str(request.source_revision_token or "").strip()
    if not artifact_id or not buddy_token:
        raise WorldGraphSourceAdmissionError(
            "Graph Review source identity is missing",
            code="source_identity_missing",
        )
    try:
        pair_to_dm = catalog_aware_source_revision_ids(
            sources,
            request.world_id,
            {(artifact_id, buddy_token)},
        )
    except WorldGraphWriteError as exc:
        _raise_port(exc)
        raise
    dm_revision_id = pair_to_dm[(artifact_id, buddy_token)]
    digest = _digest_from_buddy_revision(buddy_token)
    if digest is None:
        digest = _hex_digest(str(getattr(artifact, "content_sha256", "") or ""))
    if len(digest) != 64:
        raise WorldGraphSourceAdmissionError(
            "Graph Review source revision digest is not a sha256 hex",
            code="inexpressible",
            details={"source_revision_token": buddy_token},
        )
    locator = (request.source_uri or getattr(artifact, "uri", None) or "").strip()
    if not locator:
        locator = f"object://{dm_revision_id}"
    created_at = _revision_created_at(artifact)
    dm_artifact = _store_artifact_v2(
        artifact,
        current_revision_id=dm_revision_id,
        uri=locator,
    )
    campaign_id = (
        str(getattr(artifact, "campaign_id", None) or "").strip()
        or request.campaign_id
    )
    world_id = str(getattr(artifact, "world_id", None) or "").strip() or request.world_id
    dm_artifact = dm_artifact.model_copy(
        update={
            "world_id": world_id,
            "campaign_id": campaign_id,
        }
    )
    revision = SourceRevision(
        source_revision_id=dm_revision_id,
        source_artifact_id=artifact_id,
        content_sha256=digest,
        body_storage="object_store",
        locator=locator,
        created_at=created_at,
    )
    return dm_artifact, revision, buddy_token


def _snapshot_identity(
    sources: Any,
    *,
    source_artifact_id: str,
    source_revision_id: str,
    buddy_source_revision_id: str,
) -> AdmittedSourceIdentity:
    snapshot = sources.get_provenance_snapshot(
        artifact_ids=[source_artifact_id],
        revision_ids=[source_revision_id],
    )
    artifact = snapshot.get_artifact(source_artifact_id)
    revision = snapshot.get_revision(source_revision_id)
    if artifact is None or revision is None:
        raise WorldGraphSourceAdmissionError(
            "Admitted source pair is not snapshot-provable.",
            code="source_not_admitted",
            details={
                "source_artifact_id": source_artifact_id,
                "source_revision_id": source_revision_id,
            },
        )
    return AdmittedSourceIdentity(
        source_artifact_id=str(artifact.source_artifact_id),
        source_revision_id=str(revision.source_revision_id),
        content_sha256=str(revision.content_sha256),
        buddy_source_revision_id=buddy_source_revision_id,
    )


class DungeonMindWorldGraphSourceAdmissionAdapter:
    """Production source admission. PostgreSQL stays inside this class."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        sources: Any | None = None,
    ) -> None:
        self._database_url = database_url
        self._sources = sources

    def _source_repository(self) -> Any:
        if self._sources is not None:
            return self._sources
        try:
            dsn = _require_database_url(self._database_url)
            return _open_repository_bundle(dsn).sources
        except WorldGraphWriteError as exc:
            _raise_port(exc)
            raise

    def prove_or_admit(
        self, request: WorldGraphSourceAdmissionRequest
    ) -> AdmittedSourceIdentity:
        sources = self._source_repository()
        dm_artifact, revision, buddy_token = _map_buddy_source(request, sources)
        try:
            sources.put_artifact(dm_artifact)
            sources.put_revision(revision)
        except WorldGraphSourceAdmissionError:
            raise
        except Exception as exc:
            raise _map_provider_error(exc) from exc
        return _snapshot_identity(
            sources,
            source_artifact_id=str(dm_artifact.source_artifact_id),
            source_revision_id=str(revision.source_revision_id),
            buddy_source_revision_id=buddy_token,
        )

    def prove(
        self,
        *,
        world_id: str,
        source_artifact_id: str,
        source_revision_id: str,
        source_revision_token: str | None = None,
    ) -> AdmittedSourceIdentity:
        sources = self._source_repository()
        buddy_token = str(source_revision_token or "").strip()
        identity = _snapshot_identity(
            sources,
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            buddy_source_revision_id=buddy_token or source_revision_id,
        )
        if buddy_token:
            try:
                derived = catalog_aware_source_revision_ids(
                    sources,
                    world_id,
                    {(source_artifact_id, buddy_token)},
                )
            except WorldGraphWriteError as exc:
                _raise_port(exc)
                raise
            if derived.get((source_artifact_id, buddy_token)) != source_revision_id:
                raise WorldGraphSourceAdmissionError(
                    "Sealed DungeonMind source revision drifted from catalog-aware derivation.",
                    code="source_identity_conflict",
                    details={
                        "source_artifact_id": source_artifact_id,
                        "source_revision_id": source_revision_id,
                    },
                )
        return identity
