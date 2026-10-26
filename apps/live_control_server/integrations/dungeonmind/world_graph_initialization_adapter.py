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


def _is_party_registry_profile(request: WorldGraphInitializationRequest) -> bool:
    artifact = request.source_artifact
    return (
        str(getattr(artifact, "source_domain", "") or "") == "party_registry"
        and str(getattr(request.reviewed_contribution, "source_kind", "") or "") == "standing_context"
    )


def _map_sources(
    request: WorldGraphInitializationRequest,
    *,
    requested_initialized_at: datetime,
    sources: Any = None,
    require_existing_source: bool = False,
) -> tuple[list[Any], list[Any], dict[tuple[str, str], str]]:
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        _digest_from_buddy_revision,
        _dm_revision_id,
        catalog_aware_source_revision_ids,
        WorldGraphSourceAdmissionError,
        _parse_optional_aware,
        _store_artifact_v2,
    )
    from dungeonmind.contracts.evidence import SourceAuthority, SourceRevision

    artifact = request.source_artifact
    artifact_id = str(artifact.source_artifact_id)
    buddy_revision = request.source_revision_token
    if sources is None:
        dm_revision_id = _dm_revision_id(buddy_revision, artifact_id)
    else:
        try:
            dm_revision_id = catalog_aware_source_revision_ids(
                sources, request.world_id, {(artifact_id, buddy_revision)},
                require_existing=require_existing_source,
            )[(artifact_id, buddy_revision)]
        except WorldGraphSourceAdmissionError as exc:
            raise WorldGraphInitializationError(
                str(exc), code="integrity_failure", details=exc.details,
            ) from exc
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
    # Registry bytes have no independently persisted artifact timestamp.  The
    # reviewed-init retry path reuses its receipt timestamp, keeping the command
    # exactly replayable without minting a second audit identity.
    if created_at is None and _is_party_registry_profile(request):
        created_at = requested_initialized_at
    if created_at is None:
        raise WorldGraphInitializationError(
            "first-world source artifact is missing created_at",
            code="inexpressible",
            details={"source_artifact_id": artifact_id},
        )
    dm_artifact = _store_artifact_v2(
        artifact,
        current_revision_id=dm_revision_id,
        world_id=request.world_id,
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


def _map_contribution(request: WorldGraphInitializationRequest, pair_to_dm: dict[tuple[str, str], str], artifacts: list[Any]):
    from apps.live_control_server.integrations.dungeonmind.first_world_typed_evidence import (
        map_first_world_typed_contribution,
    )

    if _is_party_registry_profile(request):
        contribution = request.reviewed_contribution
        artifact = request.source_artifact
        if (
            getattr(artifact, "session_id", None) is not None
            or getattr(contribution, "campaign_scope", None) != request.campaign_id
            or getattr(contribution, "source_artifact_id", None) != getattr(artifact, "source_artifact_id", None)
            or getattr(contribution, "source_revision_id", None) != request.source_revision_token
            or getattr(contribution, "unresolved_mentions", None)
            or getattr(contribution, "candidate_assertions", None)
            or getattr(contribution, "rejected_assertions", None)
        ):
            raise WorldGraphInitializationError(
                "party-registry first-world profile is malformed",
                code="inexpressible",
                details={"reason": "invalid_party_registry_profile"},
            )
        if not contribution.accepted_assertions or any(
            item.assertion_kind != "node" or item.acceptance_state != "accepted"
            or (item.value or {}).get("canon_state") != "canonical"
            for item in contribution.accepted_assertions
        ):
            raise WorldGraphInitializationError(
                "party-registry genesis accepts canonical node assertions only",
                code="inexpressible",
                details={"reason": "invalid_party_registry_assertions"},
            )
        remapped = contribution
    else:
        remapped = _worldbuilding_expressible(request.reviewed_contribution)
        # Product source ownership stays managed; native publication is explicitly
        # World scoped and targets only the sealed server-reserved native identity.
        remapped = remapped.model_copy(update={
            "world_id": request.world_id, "campaign_scope": request.campaign_id,
            **{field: [item.model_copy(update={"campaign_scope": request.campaign_id})
                       for item in getattr(remapped, field)]
               for field in ("accepted_assertions", "rejected_assertions", "candidate_assertions")},
        })
    try:
        mapped = [map_first_world_typed_contribution(
            remapped, artifacts=artifacts, pair_to_dm=pair_to_dm,
            party_registry=_is_party_registry_profile(request),
        )]
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
    sources: Any = None,
    require_existing_source: bool = False,
):
    from dungeonmind.contracts.reviewed_world_initialization import (
        ReviewedWorldInitializationCommandV2,
    )

    expected_plan = "dmb_recap_world_genesis_plan_v2" if _is_party_registry_profile(request) else "dmb_first_world_graph_plan_v3"
    if request.source_plan_schema != expected_plan:
        raise WorldGraphInitializationError("This review plan is out of date. Prepare and review it again.", code="inexpressible", details={"reason": "stale_review_plan"})
    artifacts, revisions, pair_to_dm = _map_sources(
        request, requested_initialized_at=requested_initialized_at,
        sources=sources, require_existing_source=require_existing_source,
    )
    contribution = _map_contribution(request, pair_to_dm, artifacts)
    command = ReviewedWorldInitializationCommandV2(
        initialization_id=request.initialization_id,
        world_id=request.world_id,
        campaign_id=request.campaign_id,
        source_plan_schema=request.source_plan_schema,
        source_plan_id=request.source_plan_id,
        source_plan_sha256=_hex_digest(request.source_plan_sha256),
        semantic_profile=_genesis_semantic_profile(),
        source_artifacts=artifacts,
        source_revisions=revisions,
        producer_profile="party_registry" if _is_party_registry_profile(request) else "worldbuilding_extraction",
        reviewed_contribution=contribution,
        actor=request.actor,
        requested_initialized_at=requested_initialized_at,
    )

    from dungeonmind.application.reviewed_world_initialization import bind_reviewed_world_initialization_command
    try:
        return bind_reviewed_world_initialization_command(command)
    except Exception as exc:
        raise _map_provider_error(exc) from exc


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

    def preflight(self, request: WorldGraphInitializationRequest) -> None:
        # Same complete command construction/qualification as initialize. No bundle,
        # receipt mutation or initialization call is allowed on this path.
        clock = self._now or (lambda: datetime.now(UTC))
        _build_command(request, requested_initialized_at=clock())

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
            if existing.schema_version != "dm_reviewed_world_initialization_receipt_v2":
                raise WorldGraphInitializationError(
                    "This World has a historical initialization. Inspect its receipt; it cannot be replayed.",
                    code="already_initialized", details={"initialization_id": existing.initialization_id},
                )
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
        command = _build_command(
            request, requested_initialized_at=requested_at,
            sources=bundle.sources, require_existing_source=had_matching_receipt,
        )
        try:
            provider_receipt = initialize_reviewed_world(
                command,
                initialization_repository=repository,
                graph_reader=reader,
            )
            return _receipt_from_provider(
                provider_receipt, had_receipt=had_matching_receipt
            )
        except IdempotencyConflictError as conflict:
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
                raise _map_provider_error(conflict) from conflict
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
                request, requested_initialized_at=refreshed.initialized_at,
                sources=bundle.sources, require_existing_source=True,
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
