"""DungeonMind-backed zero-parent World Graph initialization (CUTOVER D.2C2).

PostgreSQL, DungeonMind models, and graph payloads stay inside this adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
    _worldbuilding_expressible,
)
from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
    WorldGraphWriteError,
    _EmptyEvidenceView,
    _build_graph_reader,
    _open_repository_bundle,
    _require_database_url,
)
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationError,
    WorldGraphInitializationReceipt,
    WorldGraphInitializationRequest,
    WorldGraphInitializationState,
)


def _raise_port(exc: WorldGraphWriteError) -> None:
    code = exc.code
    port_code = "authority_unavailable" if code == "authority_unavailable" else "initialization_failed"
    if code in {"governed_write_inexpressible"}:
        port_code = "inexpressible"
    raise WorldGraphInitializationError(
        str(exc),
        code=port_code,  # type: ignore[arg-type]
        details=dict(exc.details or {}),
    ) from exc


def _genesis_semantic_profile():
    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind.contracts.semantic_profile import SemanticProfileRef
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    descriptor = load_builtin_v3_descriptor()
    return SemanticProfileRef(
        profile_id=descriptor.profile_id,
        profile_revision=descriptor.profile_revision,
        descriptor_sha256=descriptor_sha256(descriptor),
    )


def _hex_digest(value: str) -> str:
    return value.removeprefix("sha256:").strip().lower()


def _qualify_first_world_contribution(contribution: Any) -> Any:
    """Stamp D.2B qualified kinds/predicates onto accepted first-world assertions."""
    import json

    from dungeonmind.contracts.contribution import AcceptanceState

    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _qualified_assertion_update,
    )

    endpoint_kinds: dict[str, str] = {}
    for assertion in contribution.assertions:
        if assertion.assertion_kind != "node" or not assertion.value:
            continue
        try:
            value = json.loads(assertion.value)
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        kind = value.get("kind")
        if isinstance(kind, str) and kind.strip() and assertion.subject_object_id:
            endpoint_kinds[assertion.subject_object_id] = kind
    qualified = []
    for assertion in contribution.assertions:
        if assertion.acceptance_state is AcceptanceState.ACCEPTED:
            qualified.append(
                assertion.model_copy(
                    update=_qualified_assertion_update(
                        assertion, endpoint_kinds=endpoint_kinds
                    )
                )
            )
        else:
            qualified.append(assertion)
    return contribution.model_copy(update={"assertions": qualified})


def _map_sources(request: WorldGraphInitializationRequest) -> tuple[list[Any], list[Any], dict[tuple[str, str], str]]:
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        _digest_from_buddy_revision,
        _dm_revision_id,
        _parse_optional_aware,
        _store_artifact_v2,
    )
    from dungeonmind.contracts.evidence import SourceAuthority, SourceRevision

    artifact = request.source_artifact
    artifact_id = str(artifact.source_artifact_id)
    buddy_revision = request.source_revision_token
    dm_revision_id = _dm_revision_id(buddy_revision, artifact_id, set())
    digest = _digest_from_buddy_revision(buddy_revision)
    if digest is None:
        digest = _hex_digest(getattr(artifact, "content_sha256", "") or "")
    if len(digest) != 64:
        raise WorldGraphInitializationError(
            "first-world source revision digest is not a sha256 hex",
            code="inexpressible",
            details={"source_revision_token": buddy_revision},
        )
    locator = (request.source_uri or getattr(artifact, "uri", None) or "").strip()
    if not locator:
        locator = f"object://{dm_revision_id}"
    raw_created = getattr(artifact, "created_at", None)
    if isinstance(raw_created, datetime):
        created_at = (
            raw_created
            if raw_created.tzinfo is not None
            else raw_created.replace(tzinfo=UTC)
        )
    else:
        created_at = _parse_optional_aware(raw_created)
    if created_at is None:
        raise WorldGraphInitializationError(
            "first-world source artifact is missing created_at",
            code="inexpressible",
            details={"source_artifact_id": artifact_id},
        )
    dm_artifact = _store_artifact_v2(
        artifact,
        current_revision_id=dm_revision_id,
        uri=locator,
    )
    dm_artifact = dm_artifact.model_copy(
        update={
            "world_id": request.world_id,
            "campaign_id": request.campaign_id,
            "authority": SourceAuthority.PRIMARY,
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
    pair_to_dm = {(artifact_id, buddy_revision): dm_revision_id}
    return [dm_artifact], [revision], pair_to_dm


_FIRST_WORLD_WORLDBUILDING_DOMAIN_KEY = "worldbuilding"


def _align_first_world_command_evidence_domains(
    contribution: Any,
    artifacts: list[Any],
) -> Any:
    """Copy command-owned worldbuilding domain onto first-world evidence refs.

    Historical #645 mapping derived exported evidence IDs from an OTHER
    fallback draft. DungeonMind #47 reverse-normalizes only
    ``EvidenceRef.source_domain``. This helper therefore keeps those IDs and
    changes only the domain, using the mapped SourceArtifact as authority.
    """
    from dungeonmind.contracts.evidence import SourceDomain

    artifacts_by_id: dict[str, Any] = {}
    for artifact in artifacts:
        artifact_id = str(artifact.source_artifact_id)
        prior = artifacts_by_id.get(artifact_id)
        if prior is not None and prior != artifact:
            raise WorldGraphInitializationError(
                "first-world command has conflicting source artifacts",
                code="inexpressible",
                details={
                    "source_artifact_id": artifact_id,
                    "reason": "ambiguous_source_artifact",
                },
            )
        artifacts_by_id[artifact_id] = artifact

    aligned_assertions = []
    for assertion in contribution.assertions:
        aligned_refs = []
        for ref in assertion.evidence_refs:
            artifact = artifacts_by_id.get(str(ref.source_artifact_id))
            if artifact is None:
                raise WorldGraphInitializationError(
                    "first-world evidence names a source artifact not in the command",
                    code="inexpressible",
                    details={
                        "source_artifact_id": ref.source_artifact_id,
                        "reason": "missing_source_artifact",
                    },
                )
            domain_key = str(getattr(artifact, "source_domain_key", "") or "")
            if (
                artifact.source_domain is not SourceDomain.WORLDBUILDING
                or domain_key != _FIRST_WORLD_WORLDBUILDING_DOMAIN_KEY
            ):
                raise WorldGraphInitializationError(
                    "first-world source artifact is not worldbuilding provenance",
                    code="inexpressible",
                    details={
                        "source_artifact_id": artifact.source_artifact_id,
                        "source_domain": str(artifact.source_domain),
                        "source_domain_key": domain_key,
                        "reason": "non_worldbuilding_source_artifact",
                    },
                )
            historical_id = ref.evidence_ref_id
            corrected = ref.model_copy(update={"source_domain": artifact.source_domain})
            if corrected.evidence_ref_id != historical_id:
                raise WorldGraphInitializationError(
                    "first-world evidence identity changed while correcting provenance",
                    code="integrity_failure",
                    details={
                        "historical_evidence_ref_id": historical_id,
                        "corrected_evidence_ref_id": corrected.evidence_ref_id,
                    },
                )
            aligned_refs.append(corrected)
        aligned_assertions.append(
            assertion.model_copy(update={"evidence_refs": aligned_refs})
        )
    return contribution.model_copy(update={"assertions": aligned_assertions})


def _map_contribution(request: WorldGraphInitializationRequest, pair_to_dm: dict[tuple[str, str], str]):
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
        _map_contributions,
    )

    remapped = _worldbuilding_expressible(request.reviewed_contribution)
    try:
        mapped = _map_contributions(_EmptyEvidenceView(), [remapped], pair_to_dm)
    except WorldGraphInitializationError:
        raise
    except Exception as exc:
        raise WorldGraphInitializationError(
            str(exc),
            code="inexpressible",
            details={"reason": type(exc).__name__},
        ) from exc
    if len(mapped) != 1:
        raise WorldGraphInitializationError(
            "first-world contribution mapping did not produce exactly one contribution",
            code="inexpressible",
            details={"contribution_id": getattr(request.reviewed_contribution, "contribution_id", None)},
        )
    try:
        return _qualify_first_world_contribution(mapped[0])
    except WorldGraphWriteError as exc:
        raise WorldGraphInitializationError(
            str(exc),
            code="inexpressible",
            details=dict(exc.details or {}),
        ) from exc


def _build_command(
    request: WorldGraphInitializationRequest,
    *,
    requested_initialized_at: datetime,
):
    from dungeonmind.contracts.reviewed_world_initialization import (
        ReviewedWorldInitializationCommandV1,
    )

    artifacts, revisions, pair_to_dm = _map_sources(request)
    contribution = _map_contribution(request, pair_to_dm)
    contribution = _align_first_world_command_evidence_domains(contribution, artifacts)
    return ReviewedWorldInitializationCommandV1(
        initialization_id=request.initialization_id,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        source_plan_schema=request.source_plan_schema,
        source_plan_id=request.source_plan_id,
        source_plan_sha256=_hex_digest(request.source_plan_sha256),
        semantic_profile=_genesis_semantic_profile(),
        source_artifacts=artifacts,
        source_revisions=revisions,
        reviewed_contribution=contribution,
        actor=request.actor,
        requested_initialized_at=requested_initialized_at,
    )


def _head_revision_id(head: Any) -> str | None:
    if head is None:
        return None
    return str(getattr(head, "head_revision_id", "") or "").strip() or None


def _require_receipt_head_coherent(world_id: str, receipt: Any, head: Any) -> None:
    """A verified receipt without a current head is contradictory, not initialized."""
    if receipt is None:
        return
    if _head_revision_id(head) is not None:
        return
    raise WorldGraphInitializationError(
        "reviewed-init receipt exists without a current world head",
        code="integrity_failure",
        details={
            "world_id": world_id,
            "reason": "reviewed_init_receipt_without_head",
            "initialization_id": str(receipt.initialization_id),
            "published_revision_id": str(receipt.published_revision_id),
        },
    )


def _get_verified_reviewed_init_receipt(repository: Any, world_id: str) -> Any:
    """Verified reviewed-init read. Maps DungeonMind errors onto the port."""
    try:
        return repository.get_for_world(world_id)
    except WorldGraphInitializationError:
        raise
    except Exception as exc:
        raise _map_provider_error(exc) from exc


def _receipt_from_provider(provider_receipt: Any, *, had_receipt: bool) -> WorldGraphInitializationReceipt:
    accepted = tuple(provider_receipt.accepted_assertion_ids)
    return WorldGraphInitializationReceipt(
        world_id=provider_receipt.world_id,
        initialization_id=provider_receipt.initialization_id,
        published_revision_id=provider_receipt.published_revision_id,
        reviewed_contribution_id=provider_receipt.reviewed_contribution_id,
        reviewed_contribution_sha256=provider_receipt.reviewed_contribution_sha256,
        accepted_assertion_ids=accepted,
        outcome="already_initialized" if had_receipt else "initialized",
        command_sha256=provider_receipt.command_sha256,
        baseline_revision_id=None,
        initialized_at=provider_receipt.initialized_at,
    )


def _map_provider_error(exc: BaseException) -> WorldGraphInitializationError:
    from dungeonmind.domain.errors import (
        ContributionMaterializationError,
        IdempotencyConflictError,
        PersistenceIntegrityError,
        PersistenceUnavailableError,
        ReviewedWorldInitializationOutcomeUnknownError,
    )

    if isinstance(exc, WorldGraphInitializationError):
        return exc
    if isinstance(exc, PersistenceUnavailableError):
        return WorldGraphInitializationError(
            str(exc),
            code="authority_unavailable",
            details=getattr(exc, "details", {}) or {},
        )
    if isinstance(exc, ReviewedWorldInitializationOutcomeUnknownError):
        return WorldGraphInitializationError(
            str(exc),
            code="initialization_failed",
            details=getattr(exc, "details", {}) or {},
        )
    if isinstance(exc, IdempotencyConflictError):
        return WorldGraphInitializationError(
            str(exc),
            code="idempotency_conflict",
            details=getattr(exc, "details", {}) or {},
        )
    if isinstance(exc, PersistenceIntegrityError):
        details = dict(getattr(exc, "details", {}) or {})
        reason = details.get("reason")
        if reason == "non_pristine_target":
            return WorldGraphInitializationError(
                str(exc),
                code="already_initialized",
                details=details,
            )
        if reason in {
            "accepted_identity_not_create_new",
            "accepted_edge_identity_unsupported",
            "accepted_resolved_existing",
            "unreferenced_source_artifact",
            "unreferenced_source_revision",
            "source_revision_not_in_command",
            "source_artifact_not_in_command",
        }:
            return WorldGraphInitializationError(
                str(exc),
                code="inexpressible",
                details=details,
            )
        return WorldGraphInitializationError(
            str(exc),
            code="integrity_failure",
            details=details,
        )
    if isinstance(exc, ContributionMaterializationError):
        return WorldGraphInitializationError(
            str(exc),
            code="inexpressible",
            details=getattr(exc, "details", {}) or {},
        )
    return WorldGraphInitializationError(
        str(exc),
        code="initialization_failed",
        details={"reason": type(exc).__name__},
    )


class DungeonMindWorldGraphInitializationAdapter:
    """Production first-world initialization. PostgreSQL stays inside this class."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        now: Callable[[], datetime] | None = None,
        after_uninitialized_receipt: Callable[[], None] | None = None,
    ) -> None:
        self._database_url = database_url
        self._now = now
        self._after_uninitialized_receipt = after_uninitialized_receipt

    def _bundle(self):
        try:
            dsn = _require_database_url(self._database_url)
            return _open_repository_bundle(dsn)
        except WorldGraphWriteError as exc:
            _raise_port(exc)
            raise

    def probe(self, world_id: str) -> WorldGraphInitializationState:
        try:
            bundle = self._bundle()
            head = bundle.world_graph.get_head(world_id)
            receipt = _get_verified_reviewed_init_receipt(
                bundle.reviewed_world_initializations, world_id
            )
        except WorldGraphInitializationError:
            raise
        except Exception as exc:
            raise _map_provider_error(exc) from exc
        _require_receipt_head_coherent(world_id, receipt, head)
        head_id = _head_revision_id(head)
        if receipt is not None:
            return WorldGraphInitializationState(
                world_id=world_id,
                state="initialized",
                initialization_id=str(receipt.initialization_id),
                published_revision_id=str(receipt.published_revision_id),
            )
        if head_id:
            return WorldGraphInitializationState(
                world_id=world_id,
                state="initialized",
                initialization_id=None,
                published_revision_id=head_id,
            )
        return WorldGraphInitializationState(world_id=world_id, state="uninitialized")

    def initialize(
        self,
        request: WorldGraphInitializationRequest,
    ) -> WorldGraphInitializationReceipt:
        from dungeonmind.application.reviewed_world_initialization import (
            initialize_reviewed_world,
        )
        from dungeonmind.domain.errors import IdempotencyConflictError

        bundle = self._bundle()
        repository = bundle.reviewed_world_initializations
        reader = _build_graph_reader()
        existing = _get_verified_reviewed_init_receipt(repository, request.world_id)
        if existing is not None:
            try:
                head = bundle.world_graph.get_head(request.world_id)
            except WorldGraphInitializationError:
                raise
            except Exception as exc:
                raise _map_provider_error(exc) from exc
            _require_receipt_head_coherent(request.world_id, existing, head)
            if existing.initialization_id != request.initialization_id:
                raise WorldGraphInitializationError(
                    "world already has a reviewed initialization with a different id",
                    code="already_initialized",
                    details={
                        "world_id": request.world_id,
                        "initialization_id": existing.initialization_id,
                    },
                )
        elif self._after_uninitialized_receipt is not None:
            self._after_uninitialized_receipt()
        had_matching_receipt = (
            existing is not None and existing.initialization_id == request.initialization_id
        )
        if had_matching_receipt:
            requested_at = existing.initialized_at
        else:
            clock = self._now or (lambda: datetime.now(UTC))
            requested_at = clock()
        command = _build_command(request, requested_initialized_at=requested_at)
        try:
            provider_receipt = initialize_reviewed_world(
                command,
                initialization_repository=repository,
                graph_reader=reader,
            )
            return _receipt_from_provider(
                provider_receipt, had_receipt=had_matching_receipt
            )
        except IdempotencyConflictError:
            if had_matching_receipt:
                raise _map_provider_error(
                    IdempotencyConflictError(
                        "reviewed-world initialization command digest conflict",
                        details={"initialization_id": request.initialization_id},
                    )
                ) from None
            refreshed = _get_verified_reviewed_init_receipt(
                repository, request.world_id
            )
            if refreshed is None:
                raise _map_provider_error(
                    IdempotencyConflictError(
                        "reviewed-world initialization conflict without a durable receipt",
                        details={"world_id": request.world_id},
                    )
                ) from None
            if refreshed.initialization_id != request.initialization_id:
                raise WorldGraphInitializationError(
                    "world already has a reviewed initialization with a different id",
                    code="already_initialized",
                    details={
                        "world_id": request.world_id,
                        "initialization_id": refreshed.initialization_id,
                    },
                ) from None
            try:
                refreshed_head = bundle.world_graph.get_head(request.world_id)
            except WorldGraphInitializationError:
                raise
            except Exception as exc:
                raise _map_provider_error(exc) from exc
            _require_receipt_head_coherent(request.world_id, refreshed, refreshed_head)
            replay_command = _build_command(
                request, requested_initialized_at=refreshed.initialized_at
            )
            try:
                provider_receipt = initialize_reviewed_world(
                    replay_command,
                    initialization_repository=repository,
                    graph_reader=reader,
                )
            except Exception as exc:
                raise _map_provider_error(exc) from exc
            return _receipt_from_provider(provider_receipt, had_receipt=True)
        except Exception as exc:
            raise _map_provider_error(exc) from exc
