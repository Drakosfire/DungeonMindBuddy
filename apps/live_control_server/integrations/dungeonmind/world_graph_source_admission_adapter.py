"""DungeonMind-backed Graph Review source admission (CUTOVER D.2C4).

Maps Buddy SourceArtifact + revision token onto SourceArtifactV2 + SourceRevision
using the already-landed mapping family and catalog-aware collision derivation,
then delegates catalog proof and atomic new-pair admission to DungeonMind.
PostgreSQL stays inside this adapter. No new DungeonMind command or UoW.

This module must be importable without ``world_graph_writes``,
``integrations/dungeonmind_kernel/**``, ``graph_memory.kernel``,
``graph_memory.world_supergraph``, or ``graph_memory.union_supergraph``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from application_state.source.identity import canonical_source_domain_key

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
    world_id: str,
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

    domain_key = canonical_source_domain_key(str(artifact.source_domain))
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
        world_id=world_id,
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


def _reverse_revision_id(dm_revision_id: str, artifact_id: str | None) -> str:
    suffix = f"::{artifact_id}" if artifact_id else ""
    if suffix and dm_revision_id.endswith(suffix):
        return dm_revision_id[: -len(suffix)]
    return dm_revision_id


def _dm_revision_id(buddy_revision_id: str, artifact_id: str) -> str:
    """New revision identity binds both immutable bytes and their owning artifact."""
    return f"{buddy_revision_id}::{artifact_id}"


def catalog_aware_source_revision_ids(
    sources: Any,
    world_id: str,
    pairs: set[tuple[str, str]],
    *,
    require_existing: bool = False,
) -> dict[tuple[str, str], str]:
    """Map (artifact_id, buddy_token) onto catalog-aware DungeonMind revision IDs.

    Persisted catalog identities are authoritative. New identities include the
    artifact even when no collision is currently visible, including across Worlds.
    """
    pair_to_dm: dict[tuple[str, str], str] = {}
    try:
        artifacts = sources.list_artifacts_for_world(world_id)
        for artifact in artifacts:
            for revision in sources.list_revisions(artifact.source_artifact_id):
                token = _reverse_revision_id(
                    revision.source_revision_id, artifact.source_artifact_id
                )
                pair = (artifact.source_artifact_id, token)
                if pair in pair_to_dm and pair_to_dm[pair] != revision.source_revision_id:
                    raise ValueError("ambiguous persisted source revision identity")
                pair_to_dm[pair] = revision.source_revision_id
    except Exception as exc:
        raise WorldGraphSourceAdmissionError(
            "DungeonMind authority read failed while resolving source identity",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc

    for artifact_id, token in sorted(pairs):
        if (artifact_id, token) not in pair_to_dm:
            if require_existing:
                raise WorldGraphSourceAdmissionError(
                    "Initialization receipt has no matching persisted source revision",
                    code="source_identity_conflict",
                    details={"world_id": world_id, "source_artifact_id": artifact_id},
                )
            pair_to_dm[(artifact_id, token)] = _dm_revision_id(token, artifact_id)
    return pair_to_dm


def _open_repository_bundle(database_url: str) -> Any:
    try:
        from dungeonmind.infrastructure.postgres import (
            PostgresDatabase,
            PostgresRepositoryBundle,
        )
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise WorldGraphSourceAdmissionError(
            "dungeonmind postgres adapter is unavailable",
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        ) from exc
    try:
        return PostgresRepositoryBundle(PostgresDatabase(database_url))
    except Exception as exc:
        raise WorldGraphSourceAdmissionError(
            "DungeonMind authority database is unavailable",
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        ) from exc


def _require_database_url(database_url: str | None) -> str:
    if database_url and database_url.strip():
        return database_url.strip()
    from apps.live_control_server import config

    configured = config.world_graph_authority_database_url()
    if not configured:
        raise WorldGraphSourceAdmissionError(
            "DungeonMind authority database URL is not configured "
            f"({config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV})",
            code="authority_unavailable",
        )
    return configured


def _map_provider_error(exc: BaseException) -> WorldGraphSourceAdmissionError:
    from dungeonmind.domain.errors import (
        HeadNotFoundError,
        IdempotencyConflictError,
        PersistenceIntegrityError,
        StaleParentRevisionError,
        PersistenceUnavailableError,
    )

    if isinstance(exc, (IdempotencyConflictError, HeadNotFoundError, StaleParentRevisionError, ValueError)):
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
    pair_to_dm = catalog_aware_source_revision_ids(
        sources,
        request.world_id,
        {(artifact_id, buddy_token)},
    )
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
    world_id = str(getattr(artifact, "world_id", None) or "").strip() or request.world_id
    dm_artifact = _store_artifact_v2(
        artifact,
        current_revision_id=dm_revision_id,
        world_id=world_id,
        uri=locator,
    )
    campaign_id = (
        str(getattr(artifact, "campaign_id", None) or "").strip()
        or request.campaign_id
    )
    dm_artifact = dm_artifact.model_copy(
        update={
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


def _catalog_identity(artifact: Any, revision: Any, buddy_token: str) -> AdmittedSourceIdentity:
    """Serialize the native-proven records using the existing review-seal format."""
    locator = str(revision.locator or "").strip()
    if not locator:
        raise WorldGraphSourceAdmissionError(
            "Native source has no external locator expressible by this review seal.",
            code="inexpressible",
        )
    material = {
        "artifact": artifact.model_dump(
            mode="json", exclude={"created_at", "updated_at"}
        ),
        "revision": revision.model_dump(mode="json", exclude={"created_at"}),
    }
    fingerprint = hashlib.sha256(json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")).hexdigest()
    identity = AdmittedSourceIdentity(
        source_artifact_id=str(artifact.source_artifact_id),
        source_revision_id=str(revision.source_revision_id),
        content_sha256=_hex_digest(str(revision.content_sha256)),
        buddy_source_revision_id=buddy_token,
        source_locator=locator,
        artifact_uri=str(artifact.uri) if artifact.uri is not None else None,
        catalog_fingerprint_sha256=fingerprint,
        campaign_id=artifact.campaign_id,
    )
    return identity


def _match_existing_pair(
    sources: Any,
    *,
    request: WorldGraphSourceAdmissionRequest,
    mapped_artifact: Any,
    mapped_revision: Any,
    buddy_token: str,
) -> AdmittedSourceIdentity | None:
    from dungeonmind.application.source_admission import match_admitted_source_revision

    try:
        pair = match_admitted_source_revision(
            artifact=mapped_artifact, revision=mapped_revision,
            verified_input_sha256=hashlib.sha256(request.source_body).hexdigest(),
            source_repository=sources,
        )
    except Exception as exc:
        raise _map_provider_error(exc) from exc
    return _catalog_identity(*pair, buddy_token) if pair is not None else None


class DungeonMindWorldGraphSourceAdmissionAdapter:
    """Production source admission. PostgreSQL stays inside this class."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        sources: Any | None = None,
        world_graph: Any | None = None,
    ) -> None:
        self._database_url = database_url
        self._sources = sources
        self._world_graph = world_graph

    def _source_repository(self) -> Any:
        if self._sources is not None:
            return self._sources
        dsn = _require_database_url(self._database_url)
        return _open_repository_bundle(dsn).sources

    def _admission_repositories(self) -> tuple[Any, Any]:
        if self._sources is not None:
            return self._sources, self._world_graph
        bundle = _open_repository_bundle(_require_database_url(self._database_url))
        return bundle.sources, bundle.world_graph

    def prove_or_admit(
        self, request: WorldGraphSourceAdmissionRequest
    ) -> AdmittedSourceIdentity:
        sources, world_graph = self._admission_repositories()
        dm_artifact, revision, buddy_token = _map_buddy_source(request, sources)
        if (
            dm_artifact.world_id != request.world_id
            or dm_artifact.campaign_id != request.campaign_id
        ):
            raise WorldGraphSourceAdmissionError(
                "Incoming source belongs to a different World or campaign.",
                code="source_identity_conflict",
            )
        identity = _match_existing_pair(
            sources, request=request, mapped_artifact=dm_artifact,
            mapped_revision=revision, buddy_token=buddy_token,
        )
        if identity is not None:
            return identity
        if world_graph is None:
            raise WorldGraphSourceAdmissionError(
                "Atomic source admission requires its World Graph repository.",
                code="authority_unavailable",
            )
        from dungeonmind.application.source_admission import (
            admit_source_revision,
            source_admission_command_sha256,
        )

        try:
            command_sha256 = source_admission_command_sha256(
                world_id=request.world_id,
                expected_head_revision_id=request.expected_head_revision_id,
                artifact=dm_artifact,
                revision=revision,
            )
            admit_source_revision(
                world_id=request.world_id,
                admission_id=f"admission:buddy:{command_sha256}",
                expected_head_revision_id=request.expected_head_revision_id,
                artifact=dm_artifact,
                revision=revision,
                source_body=request.source_body,
                admitted_at=datetime.now(UTC),
                world_graph_repository=world_graph,
                source_repository=sources,
            )
        except Exception as exc:
            raise _map_provider_error(exc) from exc
        identity = _match_existing_pair(
            sources, request=request, mapped_artifact=dm_artifact,
            mapped_revision=revision, buddy_token=buddy_token,
        )
        if identity is None:
            raise WorldGraphSourceAdmissionError(
                "Admitted source pair is not snapshot-provable.", code="source_not_admitted",
            )
        return identity

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
        from dungeonmind.application.source_admission import load_admitted_source_pair

        try:
            pair = load_admitted_source_pair(
                world_id=world_id, source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id, source_repository=sources,
            )
        except Exception as exc:
            raise _map_provider_error(exc) from exc
        if pair is None:
            raise WorldGraphSourceAdmissionError(
                "Admitted source pair is not snapshot-provable.", code="source_not_admitted",
            )
        identity = _catalog_identity(*pair, buddy_token or source_revision_id)
        if buddy_token:
            derived = catalog_aware_source_revision_ids(
                sources,
                world_id,
                {(source_artifact_id, buddy_token)},
            )
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
