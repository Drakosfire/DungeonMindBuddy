"""DungeonMind-backed Graph Review source admission (CUTOVER D.2C4).

Maps Buddy SourceArtifact + revision token onto SourceArtifactV2 + SourceRevision
using the already-landed mapping family and catalog-aware collision derivation,
then prove/admits through SourceRepository put/get/snapshot.
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


def _canonical_source_domain_key(raw: str) -> str:
    """Store Buddy recap producers under the DungeonMind session_recap family key.

    Graph Review and governed recap admission must put the same SourceArtifactV2
    fingerprint for the same artifact/token. The enum family was already mapped;
    the durable key must converge here too.
    """
    key = str(raw or "").strip()
    if key == "recap":
        return "session_recap"
    return key


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

    domain_key = _canonical_source_domain_key(str(artifact.source_domain))
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


def _dm_revision_id(
    buddy_revision_id: str,
    artifact_id: str,
    colliding_revision_ids: set[str],
) -> str:
    """Publisher collision suffix. Same values as the historical adoption helper."""
    if buddy_revision_id in colliding_revision_ids:
        return f"{buddy_revision_id}::{artifact_id}"
    return buddy_revision_id


def catalog_aware_source_revision_ids(
    sources: Any,
    world_id: str,
    pairs: set[tuple[str, str]],
) -> dict[tuple[str, str], str]:
    """Map (artifact_id, buddy_token) onto catalog-aware DungeonMind revision IDs.

    Shared collision algorithm for Graph Review admission and governed publish.
    Do not mint via ``_dm_revision_id(..., set())``.
    """
    pair_to_dm: dict[tuple[str, str], str] = {}
    token_artifacts: dict[str, set[str]] = {}
    try:
        artifacts = sources.list_artifacts_for_world(world_id)
        for artifact in artifacts:
            for revision in sources.list_revisions(artifact.source_artifact_id):
                token = _reverse_revision_id(
                    revision.source_revision_id, artifact.source_artifact_id
                )
                pair_to_dm[(artifact.source_artifact_id, token)] = (
                    revision.source_revision_id
                )
                token_artifacts.setdefault(token, set()).add(
                    artifact.source_artifact_id
                )
    except Exception as exc:
        raise WorldGraphSourceAdmissionError(
            "DungeonMind authority read failed while resolving source identity",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc

    for artifact_id, token in pairs:
        token_artifacts.setdefault(token, set()).add(artifact_id)
    colliding = {
        token for token, artifacts in token_artifacts.items() if len(artifacts) > 1
    }
    for artifact_id, token in sorted(pairs):
        if (artifact_id, token) not in pair_to_dm:
            pair_to_dm[(artifact_id, token)] = _dm_revision_id(
                token, artifact_id, colliding
            )
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
    if request.verified_input_sha256 is not None and (
        _hex_digest(request.verified_input_sha256) != digest
    ):
        raise WorldGraphSourceAdmissionError(
            "Verified input bytes differ from the requested source revision.",
            code="source_identity_conflict",
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


def _snapshot_pair(
    sources: Any,
    *,
    world_id: str,
    source_artifact_id: str,
    source_revision_id: str,
    buddy_source_revision_id: str,
) -> tuple[Any, Any, AdmittedSourceIdentity]:
    try:
        snapshot = sources.get_provenance_snapshot(
            artifact_ids=[source_artifact_id],
            revision_ids=[source_revision_id],
        )
    except Exception as exc:
        raise WorldGraphSourceAdmissionError(
            "DungeonMind source catalog could not be read.",
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        ) from exc
    artifact = snapshot.get_artifact(source_artifact_id)
    revision = snapshot.get_revision(source_revision_id)
    if artifact is None and revision is None:
        raise WorldGraphSourceAdmissionError(
            "Admitted source pair is not snapshot-provable.",
            code="source_not_admitted",
            details={
                "source_artifact_id": source_artifact_id,
                "source_revision_id": source_revision_id,
            },
        )
    if artifact is None or revision is None:
        raise WorldGraphSourceAdmissionError(
            "DungeonMind source catalog contains only one half of the source pair.",
            code="source_identity_conflict",
        )
    locator = str(getattr(revision, "locator", None) or "").strip()
    if (
        str(artifact.source_artifact_id) != source_artifact_id
        or str(revision.source_revision_id) != source_revision_id
        or str(revision.source_artifact_id) != source_artifact_id
        or str(artifact.current_revision_id or "") != source_revision_id
        or str(artifact.world_id) != world_id
        or not locator
        or any(ord(character) < 32 for character in locator)
    ):
        raise WorldGraphSourceAdmissionError(
            "DungeonMind source pair has changed identity, current revision, or locator.",
            code="source_identity_conflict",
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
        buddy_source_revision_id=buddy_source_revision_id,
        source_locator=locator,
        artifact_uri=str(artifact.uri) if artifact.uri is not None else None,
        catalog_fingerprint_sha256=fingerprint,
    )
    return artifact, revision, identity


def _prove_existing_pair(
    sources: Any,
    *,
    request: WorldGraphSourceAdmissionRequest,
    mapped_artifact: Any,
    mapped_revision: Any,
    buddy_token: str,
) -> AdmittedSourceIdentity:
    stored_artifact, stored_revision, identity = _snapshot_pair(
        sources,
        world_id=request.world_id,
        source_artifact_id=str(mapped_artifact.source_artifact_id),
        source_revision_id=str(mapped_revision.source_revision_id),
        buddy_source_revision_id=buddy_token,
    )
    exact_fields = (
        "source_domain_key", "source_domain", "world_id", "campaign_id",
        "session_id", "visibility", "artifact_kind", "document_class",
        "review_state", "source_visibility_state", "status",
    )
    if any(
        getattr(stored_artifact, field) != getattr(mapped_artifact, field)
        for field in exact_fields
    ) or (
        mapped_artifact.workspace_document_ref is not None
        and stored_artifact.workspace_document_ref != mapped_artifact.workspace_document_ref
    ) or any(
        stored_artifact.lineage.get(key) != value
        for key, value in mapped_artifact.lineage.items()
    ) or (
        mapped_artifact.authority is not None
        and stored_artifact.authority != mapped_artifact.authority
    ) or (
        stored_revision.body_storage != mapped_revision.body_storage
        or _hex_digest(str(stored_revision.content_sha256))
        != _hex_digest(str(mapped_revision.content_sha256))
    ):
        raise WorldGraphSourceAdmissionError(
            "Existing DungeonMind source scope, protection, or body differs from the incoming source.",
            code="source_identity_conflict",
        )
    incoming_uri = str(request.source_uri or mapped_artifact.uri or "").strip()
    known_uris = {str(stored_artifact.uri or ""), str(identity.source_locator or "")}
    if incoming_uri not in known_uris:
        verified = _hex_digest(str(request.verified_input_sha256 or ""))
        if not verified or verified != identity.content_sha256:
            raise WorldGraphSourceAdmissionError(
                "Alternate source mirror has no matching byte-verification proof.",
                code="source_identity_conflict",
            )
    elif request.verified_input_sha256 is not None and (
        _hex_digest(request.verified_input_sha256) != identity.content_sha256
    ):
        raise WorldGraphSourceAdmissionError(
            "Verified input bytes differ from the admitted source body.",
            code="source_identity_conflict",
        )
    return identity


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
        dsn = _require_database_url(self._database_url)
        return _open_repository_bundle(dsn).sources

    def prove_or_admit(
        self, request: WorldGraphSourceAdmissionRequest
    ) -> AdmittedSourceIdentity:
        sources = self._source_repository()
        dm_artifact, revision, buddy_token = _map_buddy_source(request, sources)
        if (
            dm_artifact.world_id != request.world_id
            or (request.campaign_id and dm_artifact.campaign_id != request.campaign_id)
        ):
            raise WorldGraphSourceAdmissionError(
                "Incoming source belongs to a different World or campaign.",
                code="source_identity_conflict",
            )
        try:
            existing = sources.get_provenance_snapshot(
                artifact_ids=[str(dm_artifact.source_artifact_id)],
                revision_ids=[str(revision.source_revision_id)],
            )
        except Exception as exc:
            raise WorldGraphSourceAdmissionError(
                "DungeonMind source catalog could not be read before admission.",
                code="authority_unavailable",
                details={"reason": type(exc).__name__},
            ) from exc
        if (
            existing.get_artifact(str(dm_artifact.source_artifact_id)) is not None
            or existing.get_revision(str(revision.source_revision_id)) is not None
        ):
            return _prove_existing_pair(
                sources, request=request, mapped_artifact=dm_artifact,
                mapped_revision=revision, buddy_token=buddy_token,
            )
        try:
            sources.put_artifact(dm_artifact)
            sources.put_revision(revision)
        except WorldGraphSourceAdmissionError:
            raise
        except Exception as exc:
            try:
                return _prove_existing_pair(
                    sources, request=request, mapped_artifact=dm_artifact,
                    mapped_revision=revision, buddy_token=buddy_token,
                )
            except WorldGraphSourceAdmissionError as proof_exc:
                if proof_exc.code != "source_not_admitted":
                    raise
                raise _map_provider_error(exc) from exc
        return _prove_existing_pair(
            sources, request=request, mapped_artifact=dm_artifact,
            mapped_revision=revision, buddy_token=buddy_token,
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
        _artifact, _revision, identity = _snapshot_pair(
            sources,
            world_id=world_id,
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            buddy_source_revision_id=buddy_token or source_revision_id,
        )
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
