"""Direct DungeonMind World Graph read adapter (CUTOVER R.3).

In ``dungeonmind`` authority mode this module is Buddy's *only* production
read path for the World Graph. The merge invariant:

    Product graph reads are pure consumers of one exact DungeonMind published
    revision. Buddy adapts request/response shape and performs clearly
    non-authoritative product presentation joins, but never reconstructs a
    graph, chooses graph truth, broadens admissibility, replays
    contributions, invokes the legacy graph read kernel, or falls back to
    Buddy files.

Concretely, on this path there is no ``UnionSupergraphStore`` construction,
no contribution replay, no ``graph_memory.kernel`` import, no Buddy
projection cache, and no frozen Buddy graph file access. Revision truth is derived from one shared ``DirectAuthorityBinding``.
Existing-world adoption preserves the historical Buddy-A → DungeonMind-D_A
bridge from ``dm_existing_world_adoption_receipt_v3``. Reviewed first-world
initialization binds to the real DungeonMind ``D_0`` with no fake Buddy
revision. Both receipts, a recognized receipt without a head, and a head
without recognized genesis fail closed as integrity. The frozen Buddy store
is never consulted.

Focus semantics (handoff §5.5, falsification verdict: presentation-only)
------------------------------------------------------------------------
Buddy's temporal focus (``kind=session``, campaign-qualified) never affects
graph admission in either implementation — the legacy kernel applies focus
only as presentation flags/ranking on top of an admitted projection, and
DungeonMind admission is focus-independent by construction. This adapter
therefore never sends focus to DungeonMind and instead recomputes the focus
presentation fields (``anchored_to_focus_session``,
``is_focus_session_evidence``, focus-first expansion ranking) from
already-admitted DungeonMind provenance — evidence ``session_id`` plus the
source artifact's ``campaign_id`` — using the legacy kernel's exact matching
rules.

Field classification (handoff §5.7)
-----------------------------------
* A (direct DungeonMind fact): node identity/label/kind/aliases/summary,
  relationship identity/endpoints/predicate, evidence refs, campaign scope,
  visibility/epistemic kind, snapshot identity, retrieval coverage.
* B (deterministic presentation from admitted facts): ``role`` (= ``kind``;
  the adopted world carries no distinct role and the hydrated legacy path
  defaults ``role`` to ``kind``), ``source_domains`` (distinct evidence
  domains), relationship ``label`` (= ``predicate.replace("_", " ")``,
  Buddy's own contribution-time default), focus flags, expansion ranking,
  anchor id prefix adaptation (``dm-source-anchor:v1:`` ↔
  ``source-anchor:v1:``).
* C (product-local join, non-authoritative): source artifact
  title/uri/excerpt and anchor content, read from Buddy product files and
  registries by admitted artifact identity and verified against the
  DungeonMind source revision's ``content_sha256`` digest.
* D (retired): ``external_resource``, ``threat_statblock_binding``,
  ``statblock_binding``, ``active_contribution_ids`` — Buddy-only
  hydration-era payloads the DungeonMind authority snapshot intentionally
  omits; the handoff forbids silently restoring them.

Admissibility parity
--------------------
The adapter maps Buddy admissibility through the closed DungeonMind
``GM`` / ``PLAYER`` vocabulary. Unknown values fail closed. PLAYER requests
rely on DungeonMind's fail-closed visibility gate to hide GM-only material;
the adapter does not reject PLAYER outright.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from dungeonmind.application.graph_snapshot import (
    GraphEvidenceRecord,
    GraphObjectView,
    GraphRelationshipView,
    VersionedUnionGraphSnapshotReader,
)
from dungeonmind.application.world_graph_projection import (
    WorldGraphProjectionResult,
    WorldGraphProjectionService,
)
from dungeonmind.application.world_graph_retrieval import (
    AdmittedAssertionValue,
    EvidenceTarget,
    GraphSearchResult,
    NeighborhoodResult,
    ObjectLookupResult,
    RetrievalBounds,
    SourceAnchorMetadata,
    SourceAnchorResolution,
    WorldGraphRetrievalService,
)
from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_v3_descriptor,
)
from dungeonmind.contracts.evidence import EvidenceRefV2
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.contracts.projection_v2 import (
    ScopeModeV2,
    WorldGraphProjectionRequestV2,
)
from dungeonmind.domain.errors import (
    DungeonMindError,
    HeadNotFoundError,
    PersistenceIntegrityError,
    PersistenceUnavailableError,
    RevisionNotFoundError,
    ScopeResolutionError,
)
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresRepositoryBundle,
)

from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionAttributeView,
    WorldGraphProjectionEvidenceBadge,
    WorldGraphProjectionEvidenceView,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionRequest,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSourceArtifactView,
    WorldGraphProjectionSuggestedExpansion,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTextHighlightSpan,
    WorldGraphProjectionTrustBoundary,
    WorldGraphQueryContext,
)
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalAttribute,
    WorldGraphRetrievalCoverage,
    WorldGraphRetrievalDiagnostic,
    WorldGraphRetrievalNode,
    WorldGraphRetrievalRelationship,
    WorldGraphRetrievalRequestContext,
    WorldGraphRetrievalResult,
    WorldGraphRetrievalSnapshot,
    WorldGraphRetrievalTrustBoundary,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchor,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
)
from graph_memory.retrieval.source_reader import (
    SourceReadError,
    parse_graph_data_uri,
    parse_heading_locator,
    parse_json_pointer_locator,
    parse_repo_uri,
    read_graph_data_json_pointer_anchor,
    read_repo_heading_anchor,
)
from graph_memory.kernel.world_retrieval import WorldGraphRetrievalError

logger = logging.getLogger(__name__)

_BUDDY_ANCHOR_PREFIX = "source-anchor:v1:"
_DND_ANCHOR_PREFIX = "dm-source-anchor:v1:"

# The v6 adoption namespaced every kind/predicate into the DND vocabulary
# (``dnd5e:located_in``). Buddy's product wire predates namespacing; the
# adapter strips the prefix so mounted consumers see the legacy vocabulary.
# Deterministic and uniform across the adopted world (verified: every kind
# and predicate in the authority payload carries exactly this prefix).
_DND_VOCAB_PREFIX = "dnd5e:"


def _wire_term(value: str | None) -> str | None:
    if value is None:
        return None
    return value[len(_DND_VOCAB_PREFIX):] if value.startswith(_DND_VOCAB_PREFIX) else value

# Trust boundary text for the direct path. The legacy text described the
# hydrated Buddy store ("immutable store bytes", "reconstructed from
# contributions"); after cutover those claims would be false, so the direct
# path states the DungeonMind-native semantics. Structure is unchanged.
_PROJECTION_TRUST_CAN = [
    "Revision pin identity matches the requested world graph revision.",
    "Selected revision is the exact immutable DungeonMind published revision.",
    "Attribute views are derived from admitted DungeonMind property assertions.",
]
_PROJECTION_TRUST_CANNOT = [
    "Evidence locators and source spans are metadata only; this projection does not verify them.",
    "Source artifact text is not read or opened by this projection.",
    (
        "Projection includes world-universal objects plus objects scoped to the "
        "requested campaign; other campaign-scoped chronology is excluded."
    ),
]
_RETRIEVAL_TRUST_CAN = [
    (
        "Every returned node, relationship, attribute, and source anchor is admitted by one "
        "explicit DungeonMind revision plus the requested world/campaign/focus/admissibility "
        "context."
    ),
    (
        "Source anchors are exact-matched and revalidated against that context before any "
        "content is returned; no anchor from another revision or context resolves."
    ),
    (
        "Anchor derivation is deterministic: the same admissible input always produces the "
        "same anchor id and the same ordering."
    ),
]
_RETRIEVAL_TRUST_CANNOT = [
    "Source content bytes are product-local presentation data verified against the "
    "DungeonMind source revision digest at read time.",
    "Result truncation is reported explicitly; truncated views are never silently complete.",
]


class DirectWorldGraphReadError(Exception):
    """Stable Buddy-envelope failure for the direct read path.

    ``code``/``status_code`` reuse the existing kernel/authority vocabulary
    so consumers see the same envelope shape the legacy path produced.

    ``cause_type`` / ``cause_message`` preserve the underlying exception
    identity when this wrapper maps an unexpected or DungeonMind failure.
    Callers that ``raise mapped from exc`` still chain ``__cause__``;
    these fields make that identity visible in ``str(exc)`` and JSON
    witnesses without requiring traceback inspection.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[dict[str, str]] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = diagnostics or []
        self.cause_type = type(cause).__name__ if cause is not None else None
        self.cause_message = str(cause) if cause is not None else None


DirectAuthorityGenesis = Literal[
    "existing_world_adoption",
    "reviewed_world_initialization",
]


@dataclass(frozen=True)
class DirectAuthorityBinding:
    """Receipt-backed authority binding — no frozen Buddy store involved.

    Exactly one genesis family is legal. Adopted worlds keep the Buddy-A →
    D_A compatibility rewrite; reviewed-init worlds have
    ``legacy_buddy_revision_id is None`` and use real DungeonMind IDs.
    """

    world_id: str
    dungeonmind_first_revision_id: str
    dungeonmind_head_revision_id: str
    legacy_buddy_revision_id: str | None
    genesis: DirectAuthorityGenesis


@dataclass(frozen=True)
class DirectWorldGraphReadServices:
    """DungeonMind native read services plus the receipt-backed binding."""

    bundle: PostgresRepositoryBundle
    projection: WorldGraphProjectionService
    retrieval: WorldGraphRetrievalService
    binding: DirectAuthorityBinding


def _verified_authority_lookup(getter: Any, world_id: str, *, what: str) -> Any:
    """Map verified DungeonMind receipt/head reads onto binder errors."""
    try:
        return getter(world_id)
    except DirectWorldGraphReadError:
        raise
    except PersistenceIntegrityError as exc:
        raise DirectWorldGraphReadError(
            f"DungeonMind {what} failed an integrity check for world '{world_id}'.",
            code="authority_integrity",
            status_code=500,
            diagnostics=[{"reason": "provider_persistence_integrity", "what": what}],
            cause=exc,
        ) from exc
    except PersistenceUnavailableError as exc:
        raise DirectWorldGraphReadError(
            "DungeonMind authority is unavailable.",
            code="authority_unavailable",
            status_code=503,
            diagnostics=[{"reason": "provider_unavailable", "what": what}],
            cause=exc,
        ) from exc


def _integrity_error(world_id: str, *, reason: str, message: str) -> DirectWorldGraphReadError:
    return DirectWorldGraphReadError(
        message,
        code="authority_integrity",
        status_code=500,
        diagnostics=[{"reason": reason, "world_id": world_id}],
    )


def _optional_revision_id(record: Any, field: str) -> str | None:
    value = str(getattr(record, field, "") or "").strip()
    return value or None


def _head_revision_id(head: Any) -> str | None:
    return _optional_revision_id(head, "head_revision_id")


def _genesis_snapshot(
    bundle: PostgresRepositoryBundle,
    world_id: str,
) -> tuple[Any, Any, Any]:
    """One non-transactional observation of adoption, reviewed-init, and head."""
    adoption = _verified_authority_lookup(
        bundle.existing_world_adoptions.get_for_world,
        world_id,
        what="existing-world adoption receipt",
    )
    init_repo = getattr(bundle, "reviewed_world_initializations", None)
    if init_repo is None:
        reviewed = None
    else:
        reviewed = _verified_authority_lookup(
            init_repo.get_for_world,
            world_id,
            what="reviewed-world initialization receipt",
        )
    head = _verified_authority_lookup(
        bundle.world_graph.get_head,
        world_id,
        what="world graph head",
    )
    return adoption, reviewed, head


def _contradictory_genesis(adoption: Any, reviewed: Any, head: Any) -> bool:
    has_adoption = adoption is not None
    has_reviewed = reviewed is not None
    has_head = bool(_head_revision_id(head))
    if has_adoption and has_reviewed:
        return True
    if (has_adoption or has_reviewed) and not has_head:
        return True
    if has_head and not has_adoption and not has_reviewed:
        return True
    return False


def _stabilize_genesis_snapshot(
    bundle: PostgresRepositoryBundle,
    world_id: str,
) -> tuple[Any, Any, Any]:
    """Reread contradictory observations before treating them as durable corruption.

    Each repository getter uses its own PostgreSQL transaction. A binder can
    straddle D.2C2's atomic receipt+head commit and see ``head_without_genesis``
    even though the database was never inconsistent. One coherent reread is
    enough to resolve that transition; a stable contradiction remains integrity.
    """
    adoption, reviewed, head = _genesis_snapshot(bundle, world_id)
    if not _contradictory_genesis(adoption, reviewed, head):
        return adoption, reviewed, head
    return _genesis_snapshot(bundle, world_id)


def _load_direct_authority_binding(
    bundle: PostgresRepositoryBundle,
    world_id: str,
) -> DirectAuthorityBinding:
    """Bind native reads/writes to exactly one recognized genesis family.

    Fail-closed: contradictory or unrecognized genesis is integrity, never a
    fallback to Buddy files. Uninitialized worlds (no head, neither receipt)
    keep the ordinary not-adopted/not-initialized miss. Contradictory
    observations are reread once before being treated as durable corruption.
    """
    adoption, reviewed, head = _stabilize_genesis_snapshot(bundle, world_id)
    has_adoption = adoption is not None
    has_reviewed = reviewed is not None
    head_revision_id = _head_revision_id(head) or ""
    has_head = bool(head_revision_id)

    if has_adoption and has_reviewed:
        raise _integrity_error(
            world_id,
            reason="both_genesis_receipts",
            message=(
                f"DungeonMind world '{world_id}' has both an existing-world "
                "adoption receipt and a reviewed-world initialization receipt."
            ),
        )
    if (has_adoption or has_reviewed) and not has_head:
        family = (
            "existing-world adoption"
            if has_adoption
            else "reviewed-world initialization"
        )
        raise _integrity_error(
            world_id,
            reason="genesis_receipt_without_head",
            message=(
                f"DungeonMind {family} receipt exists for world '{world_id}' "
                "but no published head is present."
            ),
        )
    if has_head and not has_adoption and not has_reviewed:
        raise _integrity_error(
            world_id,
            reason="head_without_genesis",
            message=(
                f"DungeonMind has a published head for world '{world_id}' "
                "without a recognized genesis receipt."
            ),
        )
    if not has_head and not has_adoption and not has_reviewed:
        raise DirectWorldGraphReadError(
            f"No DungeonMind adoption receipt exists for world '{world_id}'.",
            code="authority_receipt_missing",
            status_code=503,
        )

    if has_adoption:
        legacy = str(
            getattr(
                getattr(adoption, "source_provenance", None),
                "source_world_revision_id",
                "",
            )
            or ""
        ).strip()
        first = str(getattr(adoption, "published_revision_id", "") or "").strip()
        if not legacy or not first:
            raise _integrity_error(
                world_id,
                reason="adoption_bridge_identity_missing",
                message="DungeonMind adoption receipt is missing bridge revision identity.",
            )
        return DirectAuthorityBinding(
            world_id=world_id,
            dungeonmind_first_revision_id=first,
            dungeonmind_head_revision_id=head_revision_id,
            legacy_buddy_revision_id=legacy,
            genesis="existing_world_adoption",
        )

    first = str(getattr(reviewed, "published_revision_id", "") or "").strip()
    if not first:
        raise _integrity_error(
            world_id,
            reason="reviewed_init_revision_missing",
            message=(
                "DungeonMind reviewed-world initialization receipt is missing "
                "published revision identity."
            ),
        )
    return DirectAuthorityBinding(
        world_id=world_id,
        dungeonmind_first_revision_id=first,
        dungeonmind_head_revision_id=head_revision_id,
        legacy_buddy_revision_id=None,
        genesis="reviewed_world_initialization",
    )


def build_direct_world_graph_read_services(
    database_url: str,
    world_id: str,
) -> DirectWorldGraphReadServices:
    """Production factory: wire DungeonMind PostgreSQL repositories directly."""
    bundle = PostgresRepositoryBundle(PostgresDatabase(database_url))
    return direct_services_from_bundle(bundle, world_id)


def direct_services_from_bundle(
    bundle: PostgresRepositoryBundle,
    world_id: str,
) -> DirectWorldGraphReadServices:
    """Test seam: build services from an existing repository bundle."""
    graph_reader = VersionedUnionGraphSnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )
    projection = WorldGraphProjectionService(
        world_graph=bundle.world_graph,
        sources=bundle.sources,
        graph_reader=graph_reader,
    )
    retrieval = WorldGraphRetrievalService(
        projection=projection,
        sources=bundle.sources,
    )
    binding = _load_direct_authority_binding(bundle, world_id)
    return DirectWorldGraphReadServices(
        bundle=bundle,
        projection=projection,
        retrieval=retrieval,
        binding=binding,
    )


# ---------------------------------------------------------------------------
# Service dispatch support (R.3 cutover)
# ---------------------------------------------------------------------------
#
# The authority-mode/root check itself lives in the service modules so that
# Buddy environments which never enable ``dungeonmind`` mode never import
# this module (and therefore never pay the DungeonMind driver import cost —
# the same lazy-import discipline as the legacy authority adapter).


def direct_services_from_config(world_id: str) -> DirectWorldGraphReadServices:
    """Open the authority database from Buddy config and build read services."""
    from apps.live_control_server import config

    database_url = config.world_graph_authority_database_url()
    if not database_url:
        raise DirectWorldGraphReadError(
            "DungeonMind authority database URL is not configured "
            f"({config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV})",
            code="authority_unavailable",
            status_code=503,
        )
    try:
        bundle = PostgresRepositoryBundle(PostgresDatabase(database_url))
    except Exception as exc:
        raise DirectWorldGraphReadError(
            "DungeonMind authority database is unavailable",
            code="authority_unavailable",
            status_code=503,
        ) from exc
    try:
        return direct_services_from_bundle(bundle, world_id)
    except DirectWorldGraphReadError:
        raise
    except PersistenceUnavailableError as exc:
        # Bind-time parity with the legacy authority router: an unreachable
        # authority database is ``authority_unavailable``, not a mid-read
        # ``world_graph_unavailable``.
        raise DirectWorldGraphReadError(
            "DungeonMind authority database is unavailable",
            code="authority_unavailable",
            status_code=503,
        ) from exc
    except Exception as exc:
        raise _map_direct_error(exc) from exc


# ---------------------------------------------------------------------------
# Request mapping (Buddy wire → DungeonMind v2 contract)
# ---------------------------------------------------------------------------


def _map_admissibility(value: str) -> Admissibility:
    """Map Buddy admissibility through the closed DND GM/PLAYER vocabulary.

    Unknown values fail closed. PLAYER requests rely on DungeonMind's
    fail-closed visibility gate to hide GM-only material.
    """
    if value == "gm":
        return Admissibility.GM
    if value == "player":
        return Admissibility.PLAYER
    raise DirectWorldGraphReadError(
        f"Unsupported admissibility policy: {value!r}.",
        code="unsupported_admissibility",
        status_code=422,
    )


def _map_scope(
    *,
    scope_mode: str,
    campaign_id: str,
) -> tuple[ScopeModeV2, str | None]:
    """Map Buddy scope verbatim; never narrow or broaden.

    ``world`` maps to DungeonMind ``WORLD_CROSS_CAMPAIGN`` (which requires
    ``campaign_id=None``) — the cross-campaign GM lens over the whole world.
    """
    if scope_mode == "world":
        return ScopeModeV2.WORLD_CROSS_CAMPAIGN, None
    if scope_mode == "campaign":
        return ScopeModeV2.CAMPAIGN, campaign_id
    raise DirectWorldGraphReadError(
        f"Unsupported scope mode: {scope_mode!r}.",
        code="invalid_campaign_scope",
        status_code=422,
    )


def _resolve_revision_pin(
    revision_pin: str | None,
    binding: DirectAuthorityBinding,
) -> str | None:
    """Pin algebra: head / receipt-bridged A→D_A / DungeonMind passthrough.

    The A→D_A rewrite fires only when ``legacy_buddy_revision_id`` is present
    and the pin equals that exact Buddy identity. Reviewed-init ``D_0`` and
    later DungeonMind children pass through unchanged. Unknown pins pass
    through to DungeonMind, which fails closed with ``RevisionNotFoundError``
    (mapped to the legacy ``revision_not_bridged`` 404 envelope).
    """
    if revision_pin is None:
        return None
    legacy = binding.legacy_buddy_revision_id
    if legacy is not None and revision_pin == legacy:
        return binding.dungeonmind_first_revision_id
    return revision_pin


def _map_projection_request(
    request: WorldGraphProjectionRequest,
    binding: DirectAuthorityBinding,
) -> WorldGraphProjectionRequestV2:
    scope_mode, campaign_id = _map_scope(
        scope_mode=request.scope_mode,
        campaign_id=request.campaign_id,
    )
    return WorldGraphProjectionRequestV2(
        world_id=request.world_id,
        campaign_id=campaign_id,
        admissibility=_map_admissibility(request.admissibility),
        scope_mode=scope_mode,
        revision_pin=_resolve_revision_pin(request.revision_pin, binding),
        query_text=request.query_text,
    )


def _map_retrieval_context(
    context: WorldGraphRetrievalRequestContext,
    binding: DirectAuthorityBinding,
) -> WorldGraphProjectionRequestV2:
    scope_mode, campaign_id = _map_scope(
        scope_mode=context.scope_mode,
        campaign_id=context.campaign_id,
    )
    return WorldGraphProjectionRequestV2(
        world_id=context.world_id,
        campaign_id=campaign_id,
        admissibility=_map_admissibility(context.admissibility),
        scope_mode=scope_mode,
        revision_pin=_resolve_revision_pin(context.revision_pin, binding),
    )


# ---------------------------------------------------------------------------
# Error mapping (DungeonMind failures → existing Buddy envelope vocabulary)
# ---------------------------------------------------------------------------


def _map_direct_error(exc: Exception) -> DirectWorldGraphReadError:
    if isinstance(exc, DirectWorldGraphReadError):
        return exc
    if isinstance(exc, PersistenceUnavailableError):
        return DirectWorldGraphReadError(
            "DungeonMind authority is unavailable.",
            code="world_graph_unavailable",
            status_code=503,
            cause=exc,
        )
    if isinstance(exc, PersistenceIntegrityError):
        return DirectWorldGraphReadError(
            "DungeonMind authority state failed an integrity check.",
            code="projection_integrity_error",
            status_code=500,
            cause=exc,
        )
    if isinstance(exc, HeadNotFoundError):
        return DirectWorldGraphReadError(
            "DungeonMind has no published head for the requested world.",
            code="authority_head_missing",
            status_code=503,
            cause=exc,
        )
    if isinstance(exc, RevisionNotFoundError):
        return DirectWorldGraphReadError(
            "The requested revision pin is not bridged to DungeonMind authority.",
            code="revision_not_bridged",
            status_code=404,
            cause=exc,
        )
    if isinstance(exc, ScopeResolutionError):
        return DirectWorldGraphReadError(
            "The requested scope cannot be resolved against DungeonMind authority.",
            code="invalid_campaign_scope",
            status_code=422,
            cause=exc,
        )
    if isinstance(exc, ValueError):
        return DirectWorldGraphReadError(
            str(exc) or "Invalid world graph read request.",
            code="invalid_request",
            status_code=422,
            cause=exc,
        )
    if isinstance(exc, WorldGraphRetrievalError):
        return DirectWorldGraphReadError(
            str(exc) or "Product-local source join failed.",
            code=getattr(exc, "code", None) or "source_unavailable",
            status_code=int(getattr(exc, "status_code", 404) or 404),
            cause=exc,
        )
    if isinstance(exc, DungeonMindError):
        return DirectWorldGraphReadError(
            "DungeonMind authority rejected the read "
            f"({type(exc).__name__}: {exc}).",
            code="projection_internal_error",
            status_code=500,
            cause=exc,
        )
    return DirectWorldGraphReadError(
        "Unexpected failure in the direct DungeonMind read path "
        f"({type(exc).__name__}: {exc}).",
        code="projection_internal_error",
        status_code=500,
        cause=exc,
    )


# ---------------------------------------------------------------------------
# Focus presentation recomputation (from admitted provenance only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FocusContext:
    session_id: str | None
    campaign_id: str | None

    @property
    def active(self) -> bool:
        return bool(self.session_id)


def _focus_context(
    focus: WorldGraphProjectionFocus | Any,
    *,
    request_campaign_id: str | None,
) -> _FocusContext:
    """Legacy kernel rule: session focus qualified by explicit-or-request campaign."""
    if getattr(focus, "kind", "none") != "session" or not getattr(focus, "session_id", None):
        return _FocusContext(session_id=None, campaign_id=None)
    explicit = (getattr(focus, "campaign_id", None) or "").strip()
    campaign = explicit or (request_campaign_id or "").strip() or None
    return _FocusContext(session_id=focus.session_id, campaign_id=campaign)


def _evidence_session_id(record: GraphEvidenceRecord | EvidenceRefV2) -> str | None:
    return record.session_id if isinstance(record, EvidenceRefV2) else None


def _evidence_matches_focus(
    record: GraphEvidenceRecord | EvidenceRefV2,
    *,
    focus: _FocusContext,
    artifact_campaigns: Mapping[str, str | None],
) -> bool:
    """Kernel parity: session match, then campaign qualification when present."""
    if not focus.session_id:
        return False
    if _evidence_session_id(record) != focus.session_id:
        return False
    if not focus.campaign_id:
        return True
    # Missing artifact campaign stays non-matching under qualified focus.
    return artifact_campaigns.get(record.source_artifact_id) == focus.campaign_id


def _relationship_session_ids(relationship: GraphRelationshipView) -> list[str]:
    metadata = relationship.assertion_metadata
    if metadata is None:
        return []
    return sorted({ref for ref in metadata.session_refs if ref})


def _relationship_matches_focus(
    relationship: GraphRelationshipView,
    *,
    focus: _FocusContext,
    evidence_by_id: Mapping[str, GraphEvidenceRecord | EvidenceRefV2],
    artifact_campaigns: Mapping[str, str | None],
) -> bool:
    if not focus.session_id:
        return False
    if focus.session_id in _relationship_session_ids(relationship):
        return True
    return any(
        _evidence_matches_focus(
            evidence_by_id[ref], focus=focus, artifact_campaigns=artifact_campaigns
        )
        for ref in relationship.evidence_ref_ids
        if ref in evidence_by_id
    )


def _load_artifact_campaigns(
    services: DirectWorldGraphReadServices,
    artifact_ids: Iterable[str],
) -> dict[str, str | None]:
    """Authority-backed presentation join: artifact → campaign id."""
    campaigns: dict[str, str | None] = {}
    for artifact_id in sorted(set(artifact_ids)):
        try:
            artifact = services.bundle.sources.get_artifact(artifact_id)
        except Exception:  # noqa: BLE001 — presentation join must not break reads
            logger.warning(
                "direct-read: source artifact %s unavailable for focus annotation",
                artifact_id,
            )
            campaigns[artifact_id] = None
            continue
        campaigns[artifact_id] = artifact.campaign_id if artifact is not None else None
    return campaigns


# ---------------------------------------------------------------------------
# Product-local source content joins (never authoritative)
# ---------------------------------------------------------------------------


def _source_revision_digest(
    services: DirectWorldGraphReadServices,
    source_revision_id: str | None,
) -> str | None:
    if not source_revision_id:
        return None
    try:
        revision = services.bundle.sources.get_revision(source_revision_id)
    except Exception:  # noqa: BLE001 — presentation join must not break reads
        logger.warning(
            "direct-read: source revision %s unavailable for digest", source_revision_id
        )
        return None
    return revision.content_sha256 if revision is not None else None


def _load_span_paragraph_text(
    services: DirectWorldGraphReadServices,
    artifact_ids: Iterable[str],
    *,
    repo_root: Path,
) -> dict[str, str]:
    """Span id → paragraph text from product-local ingest run indexes.

    Mirrors the legacy kernel's ``source_span_index.json`` sidecar lookup,
    keyed by admitted artifact URIs from DungeonMind's source repository.
    """
    texts: dict[str, str] = {}
    for artifact_id in sorted(set(artifact_ids)):
        try:
            artifact = services.bundle.sources.get_artifact(artifact_id)
        except Exception:  # noqa: BLE001
            continue
        uri = getattr(artifact, "uri", None) if artifact is not None else None
        if not isinstance(uri, str) or not uri.strip():
            continue
        relative = parse_repo_uri(uri)
        if relative is None:
            continue
        index_path = (repo_root / relative).parent / "source_span_index.json"
        if not index_path.is_file():
            continue
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rows = raw.get("spans") if isinstance(raw, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            span_id = row.get("span_id") or row.get("source_span_ref_id")
            text = row.get("paragraph_text") or row.get("text")
            if isinstance(span_id, str) and isinstance(text, str):
                texts.setdefault(span_id, text)
    return texts


# ---------------------------------------------------------------------------
# Snapshot / evidence / relationship adaptation
# ---------------------------------------------------------------------------


def _scope_mode_wire(snapshot_scope: Any) -> Literal["campaign", "world"]:
    return "world" if snapshot_scope == ScopeModeV2.WORLD_CROSS_CAMPAIGN else "campaign"


def _admissibility_wire(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _snapshot_view(
    snapshot: Any,
    *,
    focus: WorldGraphProjectionFocus,
) -> WorldGraphProjectionSnapshot:
    """Snapshot identity is DungeonMind's; focus/campaign echo the request."""
    return WorldGraphProjectionSnapshot(
        world_id=snapshot.world_id,
        campaign_id=snapshot.campaign_id or "",
        revision_id=snapshot.revision_id,
        head_revision_id=snapshot.head_revision_id,
        is_head=snapshot.is_head,
        focus=focus,
        admissibility=_admissibility_wire(snapshot.admissibility),
        scope_mode=_scope_mode_wire(snapshot.scope_mode),
    )


def _retrieval_snapshot_view(
    snapshot: Any,
    *,
    focus: WorldGraphProjectionFocus,
) -> WorldGraphRetrievalSnapshot:
    return WorldGraphRetrievalSnapshot(
        world_id=snapshot.world_id,
        campaign_id=snapshot.campaign_id or "",
        revision_id=snapshot.revision_id,
        head_revision_id=snapshot.head_revision_id,
        is_head=snapshot.is_head,
        focus=focus,
        admissibility=_admissibility_wire(snapshot.admissibility),
        scope_mode=_scope_mode_wire(snapshot.scope_mode),
    )


def _evidence_badge(
    record: GraphEvidenceRecord | EvidenceRefV2,
    *,
    focus: _FocusContext,
    artifact_campaigns: Mapping[str, str | None],
) -> WorldGraphProjectionEvidenceBadge:
    return WorldGraphProjectionEvidenceBadge(
        evidence_ref_id=record.evidence_ref_id,
        source_artifact_id=record.source_artifact_id,
        source_domain=record.source_domain,
        evidence_role=getattr(record, "evidence_role", "support"),
        is_focus_session_evidence=_evidence_matches_focus(
            record, focus=focus, artifact_campaigns=artifact_campaigns
        ),
        can_open_source=record.can_open_source,
        can_highlight_span=record.can_highlight_span,
        label=None,
        session_id=_evidence_session_id(record),
        source_span_ref_id=getattr(record, "source_span_ref_id", None),
    )


def _relationship_view(
    relationship: GraphRelationshipView,
    *,
    focus: _FocusContext,
    evidence_by_id: Mapping[str, GraphEvidenceRecord | EvidenceRefV2],
    artifact_campaigns: Mapping[str, str | None],
) -> WorldGraphProjectionRelationshipView:
    metadata = relationship.assertion_metadata
    evidence_rows = [
        evidence_by_id[ref] for ref in relationship.evidence_ref_ids if ref in evidence_by_id
    ]
    return WorldGraphProjectionRelationshipView(
        edge_id=relationship.relationship_id,
        source_node_id=relationship.subject_object_id,
        target_node_id=relationship.object_object_id,
        predicate=_wire_term(relationship.predicate),
        # B: Buddy's own contribution-time default for unlabeled edges.
        label=_wire_term(relationship.predicate).replace("_", " "),
        direction="outgoing",
        session_ids=_relationship_session_ids(relationship),
        source_domains=sorted({row.source_domain for row in evidence_rows}),
        visibility=str(metadata.visibility) if metadata is not None else None,
        campaign_scope=metadata.campaign_scope if metadata is not None else None,
        epistemic_kind=str(metadata.epistemic_kind) if metadata is not None else None,
        evidence_ref_ids=list(relationship.evidence_ref_ids),
        source_artifact_ids=sorted({row.source_artifact_id for row in evidence_rows}),
        # D: Buddy contribution identity is not part of DungeonMind read views.
        active_contribution_ids=[],
        threat_statblock_binding=None,
        statblock_binding=None,
    )


def _attribute_views(
    assertions: Iterable[AdmittedAssertionValue],
    *,
    evidence_by_id: Mapping[str, GraphEvidenceRecord | EvidenceRefV2],
) -> list[WorldGraphProjectionAttributeView]:
    views: list[WorldGraphProjectionAttributeView] = []
    for assertion in assertions:
        metadata = assertion.assertion_metadata
        evidence_rows = [
            evidence_by_id[ref] for ref in assertion.evidence_ref_ids if ref in evidence_by_id
        ]
        value = assertion.property_value
        views.append(
            WorldGraphProjectionAttributeView(
                assertion_id=assertion.assertion_id,
                subject_node_id=assertion.subject_object_id,
                predicate=_wire_term(assertion.property_term),
                label=assertion.property_term,
                value=value if isinstance(value, dict) else {},
                text_value=None if isinstance(value, (dict, list)) else str(value),
                epistemic_kind=str(metadata.epistemic_kind) if metadata is not None else None,
                visibility=str(metadata.visibility) if metadata is not None else None,
                campaign_scope=metadata.campaign_scope if metadata is not None else None,
                temporal_scope=(
                    metadata.temporal_scope.model_dump(mode="json")
                    if metadata is not None and metadata.temporal_scope is not None
                    else None
                ),
                support_state=None,
                active_contribution_ids=[],
                evidence_ref_ids=list(assertion.evidence_ref_ids),
                source_artifact_ids=sorted({row.source_artifact_id for row in evidence_rows}),
            )
        )
    return views


def _expansion_views(
    adjacency: Sequence[WorldGraphProjectionAdjacencyCandidate],
    *,
    degree_by_node: Mapping[str, int],
) -> list[WorldGraphProjectionSuggestedExpansion]:
    """Kernel parity: sort by (-focus, -evidence, -degree, label); rank 1..N."""

    def sort_key(candidate: WorldGraphProjectionAdjacencyCandidate) -> tuple[int, int, int, str]:
        return (
            -1 if candidate.anchored_to_focus_session else 0,
            -len(candidate.evidence_ref_ids),
            -degree_by_node.get(candidate.node_id, 0),
            candidate.label.lower(),
        )

    expansions: list[WorldGraphProjectionSuggestedExpansion] = []
    for index, candidate in enumerate(sorted(adjacency, key=sort_key), start=1):
        degree = degree_by_node.get(candidate.node_id, 0)
        if candidate.anchored_to_focus_session:
            reason = "current session"
        elif len(candidate.evidence_ref_ids) >= 2:
            reason = "more evidence"
        elif degree >= 3:
            reason = "connected hub"
        else:
            reason = "connected thread"
        expansions.append(
            WorldGraphProjectionSuggestedExpansion(
                **candidate.model_dump(),
                rank=index,
                rank_reason=reason,
            )
        )
    return expansions


def _resolve_adjacency_excerpt(
    evidence_rows: Sequence[GraphEvidenceRecord | EvidenceRefV2],
    *,
    paragraph_text_by_span_id: Mapping[str, str],
) -> tuple[str | None, bool, list[WorldGraphProjectionTextHighlightSpan]]:
    """First available full-paragraph excerpt for the edge's admitted evidence.

    Buddy contribution-era ``label``/``anchor_quotes` evidence extras do not
    exist in the adopted DungeonMind world, so excerpts are always whole
    paragraphs (``is_full_paragraph=True``, no highlight spans).
    """
    for record in evidence_rows:
        span_id = getattr(record, "source_span_ref_id", None)
        if not span_id:
            continue
        text = paragraph_text_by_span_id.get(span_id)
        if text:
            return text, True, []
    return None, False, []


def _node_view(
    obj: GraphObjectView,
    *,
    relationships: Sequence[GraphRelationshipView],
    objects_by_id: Mapping[str, GraphObjectView],
    focus: _FocusContext,
    evidence_by_id: Mapping[str, GraphEvidenceRecord | EvidenceRefV2],
    artifact_campaigns: Mapping[str, str | None],
    paragraph_text_by_span_id: Mapping[str, str],
    degree_by_node: Mapping[str, int],
) -> WorldGraphProjectionNodeView:
    badges = [
        _evidence_badge(
            evidence_by_id[ref], focus=focus, artifact_campaigns=artifact_campaigns
        )
        for ref in obj.evidence_ref_ids
        if ref in evidence_by_id
    ]
    adjacency: list[WorldGraphProjectionAdjacencyCandidate] = []
    for rel in relationships:
        if rel.subject_object_id == obj.object_id:
            other_id, direction = rel.object_object_id, "outgoing"
        elif rel.object_object_id == obj.object_id:
            other_id, direction = rel.subject_object_id, "incoming"
        else:
            continue
        other = objects_by_id.get(other_id)
        rel_evidence = [
            evidence_by_id[ref] for ref in rel.evidence_ref_ids if ref in evidence_by_id
        ]
        excerpt, is_full, spans = _resolve_adjacency_excerpt(
            rel_evidence, paragraph_text_by_span_id=paragraph_text_by_span_id
        )
        rel_metadata = rel.assertion_metadata
        adjacency.append(
            WorldGraphProjectionAdjacencyCandidate(
                edge_id=rel.relationship_id,
                node_id=other_id,
                label=other.label if other is not None else other_id,
                kind=_wire_term(other.kind) if other is not None else "",
                predicate=_wire_term(rel.predicate),
                direction=direction,
                anchored_to_focus_session=_relationship_matches_focus(
                    rel,
                    focus=focus,
                    evidence_by_id=evidence_by_id,
                    artifact_campaigns=artifact_campaigns,
                ),
                source_domains=sorted({row.source_domain for row in rel_evidence}),
                evidence_ref_ids=list(rel.evidence_ref_ids),
                edge_label=_wire_term(rel.predicate).replace("_", " "),
                session_ids=_relationship_session_ids(rel),
                campaign_scope=(
                    rel_metadata.campaign_scope if rel_metadata is not None else None
                ),
                related_summary=other.summary if other is not None else None,
                source_excerpt=excerpt,
                source_excerpt_is_full_paragraph=is_full,
                source_excerpt_highlight_spans=spans,
            )
        )
    anchored = any(b.is_focus_session_evidence for b in badges) or any(
        a.anchored_to_focus_session for a in adjacency
    )
    return WorldGraphProjectionNodeView(
        node_id=obj.object_id,
        label=obj.label,
        kind=_wire_term(obj.kind),
        # B: the adopted world carries no distinct role; the hydrated legacy
        # path defaults role to kind, so this is parity-exact.
        role=_wire_term(obj.kind),
        aliases=list(obj.aliases),
        source_domains=sorted({b.source_domain for b in badges}),
        summary=obj.summary,
        anchored_to_focus_session=anchored,
        campaign_scope=(
            obj.existence_assertion_metadata.campaign_scope
            if obj.existence_assertion_metadata is not None
            else None
        ),
        evidence_badges=badges,
        adjacency=adjacency,
        suggested_expansions=_expansion_views(adjacency, degree_by_node=degree_by_node),
        evidence_ref_ids=list(obj.evidence_ref_ids),
        source_artifact_ids=sorted({b.source_artifact_id for b in badges}),
        # D: retired Buddy-only payload; the handoff forbids restoring it.
        external_resource=None,
    )


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def project_world_graph_direct(
    services: DirectWorldGraphReadServices,
    request: WorldGraphProjectionRequest,
    *,
    repo_root: Path | None = None,
) -> WorldGraphProjection:
    """Execute one exact DungeonMind projection and adapt to the Buddy wire."""
    try:
        dnd_request = _map_projection_request(request, services.binding)
        result = services.projection.project(dnd_request)
        projection = _adapt_projection_result(
            services, result, request=request, repo_root=repo_root
        )
        if request.query_text:
            search = services.retrieval.search(dnd_request, query_text=request.query_text)
            projection = projection.model_copy(
                update={
                    "query_context": _query_context_view(
                        projection, search, request=request
                    )
                }
            )
        return projection
    except Exception as exc:  # noqa: BLE001 — mapped to the stable envelope
        raise _map_direct_error(exc) from exc


def _adapt_projection_result(
    services: DirectWorldGraphReadServices,
    result: WorldGraphProjectionResult,
    *,
    request: WorldGraphProjectionRequest,
    repo_root: Path | None,
) -> WorldGraphProjection:
    graph = result.graph
    evidence_by_id: dict[str, GraphEvidenceRecord | EvidenceRefV2] = dict(graph.evidence)
    artifact_campaigns = _load_artifact_campaigns(
        services, (rec.source_artifact_id for rec in evidence_by_id.values())
    )
    focus = _focus_context(request.focus, request_campaign_id=request.campaign_id)
    objects_by_id = dict(graph.objects)
    relationships = list(graph.relationships.values())
    degree_by_node: dict[str, int] = {}
    for rel in relationships:
        degree_by_node[rel.subject_object_id] = degree_by_node.get(rel.subject_object_id, 0) + 1
        degree_by_node[rel.object_object_id] = degree_by_node.get(rel.object_object_id, 0) + 1
    paragraph_texts: dict[str, str] = {}
    if repo_root is not None:
        paragraph_texts = _load_span_paragraph_text(
            services,
            (rec.source_artifact_id for rec in evidence_by_id.values()),
            repo_root=repo_root,
        )
    rel_views = [
        _relationship_view(
            rel,
            focus=focus,
            evidence_by_id=evidence_by_id,
            artifact_campaigns=artifact_campaigns,
        )
        for rel in relationships
    ]
    node_views = [
        _node_view(
            obj,
            relationships=relationships,
            objects_by_id=objects_by_id,
            focus=focus,
            evidence_by_id=evidence_by_id,
            artifact_campaigns=artifact_campaigns,
            paragraph_text_by_span_id=paragraph_texts,
            degree_by_node=degree_by_node,
        )
        for obj in objects_by_id.values()
    ]
    attribute_views = _attribute_views(
        (
            assertion
            for obj in objects_by_id.values()
            for assertion in obj.admitted_property_assertions
        ),
        evidence_by_id=evidence_by_id,
    )
    evidence_views = [
        WorldGraphProjectionEvidenceView(
            evidence_ref_id=rec.evidence_ref_id,
            source_artifact_id=rec.source_artifact_id,
            source_domain=rec.source_domain,
            session_id=_evidence_session_id(rec),
            campaign_id=artifact_campaigns.get(rec.source_artifact_id),
            locator=rec.locator,
            source_span_ref_id=getattr(rec, "source_span_ref_id", None),
            locator_status="unverified",
        )
        for rec in evidence_by_id.values()
    ]
    artifact_views = _source_artifact_views(services, artifact_campaigns.keys())
    return WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=_snapshot_view(result.snapshot, focus=request.focus),
        summary=WorldGraphProjectionSummary(
            node_count=len(node_views),
            relationship_count=len(rel_views),
            attribute_count=len(attribute_views),
            evidence_count=len(evidence_views),
            source_artifact_count=len(artifact_views),
            projection_truncated=False,
        ),
        nodes=node_views,
        relationships=rel_views,
        attributes=attribute_views,
        evidence=evidence_views,
        source_artifacts=artifact_views,
        trust_boundary=WorldGraphProjectionTrustBoundary(
            can_trust=list(_PROJECTION_TRUST_CAN),
            cannot_trust=list(_PROJECTION_TRUST_CANNOT),
        ),
        diagnostics=[],
        query_context=None,
    )


def _source_artifact_views(
    services: DirectWorldGraphReadServices,
    artifact_ids: Iterable[str],
) -> list[WorldGraphProjectionSourceArtifactView]:
    views: list[WorldGraphProjectionSourceArtifactView] = []
    for artifact_id in sorted(set(artifact_ids)):
        try:
            artifact = services.bundle.sources.get_artifact(artifact_id)
        except Exception:  # noqa: BLE001 — presentation join must not break reads
            continue
        if artifact is None:
            continue
        views.append(
            WorldGraphProjectionSourceArtifactView(
                source_artifact_id=artifact.source_artifact_id,
                source_domain=artifact.source_domain_key,
                uri=artifact.uri or "",
                campaign_id=artifact.campaign_id or "",
                session_id=artifact.session_id,
            )
        )
    return views


def _query_context_view(
    projection: WorldGraphProjection,
    search: GraphSearchResult,
    *,
    request: WorldGraphProjectionRequest,
) -> WorldGraphQueryContext:
    """Query narrowing for the projection-embedded query context.

    Match selection is authority-native (DungeonMind R.2 search over the same
    admitted projection); the presented views are the already-adapted
    projection views narrowed to the matched set — the same selection shape
    the legacy kernel's pure ``search_world_graph_projection`` applied.
    """
    matched_ids = list(search.matched_object_ids)
    matched_set = set(matched_ids)
    nodes = [node for node in projection.nodes if node.node_id in matched_set]
    relationships = [
        relationship
        for relationship in projection.relationships
        if relationship.source_node_id in matched_set
        or relationship.target_node_id in matched_set
    ]
    attributes = [
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id in matched_set
    ]
    evidence_ids: set[str] = set()
    for node in nodes:
        evidence_ids.update(node.evidence_ref_ids)
    evidence_ids.update(
        evidence_id
        for attribute in attributes
        for evidence_id in attribute.evidence_ref_ids
    )
    evidence_ids.update(
        evidence_id
        for relationship in relationships
        for evidence_id in relationship.evidence_ref_ids
    )
    evidence = [
        item for item in projection.evidence if item.evidence_ref_id in evidence_ids
    ]
    artifact_ids: set[str] = set()
    for node in nodes:
        artifact_ids.update(node.source_artifact_ids)
    for attribute in attributes:
        artifact_ids.update(attribute.source_artifact_ids)
    for relationship in relationships:
        artifact_ids.update(relationship.source_artifact_ids)
    artifact_ids.update(item.source_artifact_id for item in evidence)
    source_artifacts = [
        item
        for item in projection.source_artifacts
        if item.source_artifact_id in artifact_ids
    ]
    return WorldGraphQueryContext(
        snapshot=projection.snapshot,
        revision_id=projection.snapshot.revision_id,
        query_text=request.query_text or "",
        matched_node_ids=matched_ids,
        match_reasons={k: list(v) for k, v in search.match_reasons.items()},
        nodes=nodes,
        relationships=relationships,
        attributes=attributes,
        evidence=evidence,
        source_artifacts=source_artifacts,
        diagnostics=[],
    )


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _coverage_view(coverage: Any) -> WorldGraphRetrievalCoverage:
    return WorldGraphRetrievalCoverage(
        requested_seed_node_ids=list(getattr(coverage, "requested_seed_object_ids", ()) or ()),
        missing_seed_node_ids=list(getattr(coverage, "missing_seed_object_ids", ()) or ()),
        truncated_fields=sorted(getattr(coverage, "truncated_fields", ()) or ()),
        missing_evidence_ref_ids=list(getattr(coverage, "missing_evidence_ref_ids", ()) or ()),
        unreadable_anchor_ids=list(getattr(coverage, "unreadable_anchor_ids", ()) or ()),
    )


def _determine_outcome(
    *,
    truncated: bool,
    partial: bool,
    has_content: bool,
) -> Literal["enough", "partial", "truncated", "empty"]:
    """Kernel parity for outcome selection (denied never occurs on this path)."""
    if truncated:
        return "truncated"
    if partial and has_content:
        return "partial"
    if has_content:
        return "enough"
    return "empty"


def _coverage_diagnostics(
    coverage: WorldGraphRetrievalCoverage,
) -> list[WorldGraphRetrievalDiagnostic]:
    diagnostics: list[WorldGraphRetrievalDiagnostic] = []
    if coverage.missing_seed_node_ids:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="missing_seed_node_ids",
                message=(
                    "Seed node ids not found in this revision: "
                    f"{', '.join(coverage.missing_seed_node_ids)}."
                ),
                severity="warning",
            )
        )
    if coverage.truncated_fields:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="result_truncated",
                message=f"Result truncated for: {', '.join(coverage.truncated_fields)}.",
                severity="warning",
            )
        )
    if coverage.missing_evidence_ref_ids:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="missing_evidence_ref_ids",
                message=(
                    "Selected graph data is missing admitted evidence refs: "
                    f"{', '.join(coverage.missing_evidence_ref_ids)}."
                ),
                severity="warning",
            )
        )
    if coverage.unreadable_anchor_ids:
        diagnostics.append(
            WorldGraphRetrievalDiagnostic(
                code="unreadable_source_anchors",
                message=(
                    f"{len(coverage.unreadable_anchor_ids)} source anchors could not be read."
                ),
                severity="warning",
            )
        )
    return diagnostics


def _retrieval_bounds(bounds: Any) -> RetrievalBounds:
    return RetrievalBounds(
        max_objects=getattr(bounds, "max_nodes", None) or 8,
        max_relationships=getattr(bounds, "max_relationships", None) or 16,
        max_assertions=getattr(bounds, "max_attributes", None) or 24,
        max_anchors=getattr(bounds, "max_source_anchors", None) or 24,
    )


def _retrieval_node_view(obj: GraphObjectView) -> WorldGraphRetrievalNode:
    return WorldGraphRetrievalNode(
        node_id=obj.object_id,
        label=obj.label,
        kind=_wire_term(obj.kind),
        role=_wire_term(obj.kind),
        aliases=list(obj.aliases),
        source_domains=[],
        summary=obj.summary,
        anchored_to_focus_session=False,
        evidence_ref_ids=list(obj.evidence_ref_ids),
        source_artifact_ids=[],
    )


def _retrieval_relationship_view(rel: GraphRelationshipView) -> WorldGraphRetrievalRelationship:
    metadata = rel.assertion_metadata
    return WorldGraphRetrievalRelationship(
        edge_id=rel.relationship_id,
        source_node_id=rel.subject_object_id,
        target_node_id=rel.object_object_id,
        predicate=_wire_term(rel.predicate),
        label=_wire_term(rel.predicate).replace("_", " "),
        direction="outgoing",
        direction_from_node_id=None,
        session_ids=_relationship_session_ids(rel),
        source_domains=[],
        visibility=str(metadata.visibility) if metadata is not None else None,
        campaign_scope=metadata.campaign_scope if metadata is not None else None,
        epistemic_kind=str(metadata.epistemic_kind) if metadata is not None else None,
        evidence_ref_ids=list(rel.evidence_ref_ids),
        source_artifact_ids=[],
        active_contribution_ids=[],
    )


def _retrieval_attribute_views(
    assertions: Iterable[AdmittedAssertionValue],
) -> list[WorldGraphRetrievalAttribute]:
    views: list[WorldGraphRetrievalAttribute] = []
    for assertion in assertions:
        metadata = assertion.assertion_metadata
        value = assertion.property_value
        views.append(
            WorldGraphRetrievalAttribute(
                assertion_id=assertion.assertion_id,
                subject_node_id=assertion.subject_object_id,
                predicate=_wire_term(assertion.property_term),
                label=assertion.property_term,
                value=value if isinstance(value, dict) else {},
                text_value=None if isinstance(value, (dict, list)) else str(value),
                epistemic_kind=str(metadata.epistemic_kind) if metadata is not None else None,
                visibility=str(metadata.visibility) if metadata is not None else None,
                campaign_scope=metadata.campaign_scope if metadata is not None else None,
                temporal_scope=(
                    metadata.temporal_scope.model_dump(mode="json")
                    if metadata is not None and metadata.temporal_scope is not None
                    else None
                ),
                support_state=None,
                active_contribution_ids=[],
                evidence_ref_ids=list(assertion.evidence_ref_ids),
                source_artifact_ids=[],
            )
        )
    return views


def _classify_locator_kind(anchor: SourceAnchorMetadata) -> str:
    domain = str(getattr(anchor.evidence, "source_domain", "") or "")
    span = (anchor.source_span_ref_id or "").strip()
    # Match the legacy live-control dispatch: only worldbuilding spans use
    # the registry-backed opener. Recap/other spans with a repo:// URI are
    # still source_span locators, opened via digest-pinned product files.
    if domain == "worldbuilding" and span:
        return "source_span"
    uri = getattr(anchor.artifact, "uri", None) or ""
    locator = anchor.locator_identity or ""
    if parse_repo_uri(uri) is not None and parse_heading_locator(locator) is not None:
        return "heading"
    if parse_graph_data_uri(uri) is not None and parse_json_pointer_locator(locator) is not None:
        return "json_pointer"
    if span and parse_repo_uri(uri) is not None:
        return "source_span"
    return "unsupported"


def _source_anchor_views(
    anchors: Iterable[SourceAnchorMetadata],
    *,
    revision_id: str,
) -> list[WorldGraphSourceAnchor]:
    views: list[WorldGraphSourceAnchor] = []
    for anchor in anchors:
        locator_kind = _classify_locator_kind(anchor)
        views.append(
            WorldGraphSourceAnchor(
                anchor_id=_buddy_anchor_id(anchor.anchor_id),
                revision_id=revision_id,
                evidence_ref_id=anchor.evidence_ref_id,
                source_artifact_id=anchor.source_artifact_id,
                source_domain=anchor.evidence.source_domain,
                session_id=_evidence_session_id(anchor.evidence),
                source_span_ref_id=anchor.source_span_ref_id,
                supporting_graph_object_ids=list(anchor.supporting_object_ids),
                supporting_assertion_ids=list(anchor.supporting_assertion_ids),
                readable=bool(anchor.can_open_source) and locator_kind != "unsupported",
                locator_kind=locator_kind,
                display_label=None,
            )
        )
    return views


def _buddy_anchor_id(anchor_id: str) -> str:
    if anchor_id.startswith(_DND_ANCHOR_PREFIX):
        return _BUDDY_ANCHOR_PREFIX + anchor_id[len(_DND_ANCHOR_PREFIX):]
    return anchor_id


def _dnd_anchor_id(anchor_id: str) -> str:
    if anchor_id.startswith(_BUDDY_ANCHOR_PREFIX):
        return _DND_ANCHOR_PREFIX + anchor_id[len(_BUDDY_ANCHOR_PREFIX):]
    return anchor_id


def _retrieval_trust_boundary() -> WorldGraphRetrievalTrustBoundary:
    return WorldGraphRetrievalTrustBoundary(
        can_trust=list(_RETRIEVAL_TRUST_CAN),
        cannot_trust=list(_RETRIEVAL_TRUST_CANNOT),
    )


def get_object_direct(
    services: DirectWorldGraphReadServices,
    request: WorldGraphObjectRequest,
) -> WorldGraphRetrievalResult:
    try:
        dnd_request = _map_retrieval_context(request, services.binding)
        result = services.retrieval.get_object(
            dnd_request, object_id=request.node_id, bounds=_retrieval_bounds(request.bounds)
        )
        return _object_result_view(result, request=request)
    except Exception as exc:  # noqa: BLE001
        raise _map_direct_error(exc) from exc


def _object_result_view(
    result: ObjectLookupResult,
    *,
    request: WorldGraphObjectRequest,
) -> WorldGraphRetrievalResult:
    coverage = _coverage_view(result.coverage)
    has_content = result.found and result.object is not None
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(coverage.missing_evidence_ref_ids),
        has_content=has_content,
    )
    return WorldGraphRetrievalResult(
        operation="object",
        outcome=outcome,
        snapshot=_retrieval_snapshot_view(
            result.snapshot, focus=request.focus.to_projection_focus()
        ),
        request_summary={"node_id": request.node_id},
        requested_node_id=request.node_id,
        resolved_node_id=result.object.object_id if result.object else None,
        nodes=[_retrieval_node_view(result.object)] if result.object else [],
        relationships=[_retrieval_relationship_view(rel) for rel in result.relationships],
        attributes=_retrieval_attribute_views(result.property_assertions),
        source_anchors=_source_anchor_views(
            result.anchors, revision_id=result.snapshot.revision_id
        ),
        coverage=coverage,
        trust_boundary=_retrieval_trust_boundary(),
        diagnostics=_coverage_diagnostics(coverage),
    )


def search_world_graph_direct(
    services: DirectWorldGraphReadServices,
    request: WorldGraphSearchRequest,
) -> WorldGraphRetrievalResult:
    try:
        dnd_request = _map_retrieval_context(request, services.binding)
        result = services.retrieval.search(
            dnd_request,
            query_text=request.query_text or "",
            seed_object_ids=request.seed_node_ids,
            bounds=_retrieval_bounds(request.bounds),
        )
        return _search_result_view(result, request=request)
    except Exception as exc:  # noqa: BLE001
        raise _map_direct_error(exc) from exc


def _search_result_view(
    result: GraphSearchResult,
    *,
    request: WorldGraphSearchRequest,
) -> WorldGraphRetrievalResult:
    coverage = _coverage_view(result.coverage)
    has_content = bool(result.objects)
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(coverage.missing_seed_node_ids or coverage.missing_evidence_ref_ids),
        has_content=has_content,
    )
    return WorldGraphRetrievalResult(
        operation="search",
        outcome=outcome,
        snapshot=_retrieval_snapshot_view(
            result.snapshot, focus=request.focus.to_projection_focus()
        ),
        request_summary={
            "query_text": request.query_text or "",
            "seed_node_ids": list(request.seed_node_ids),
        },
        matched_node_ids=list(result.matched_object_ids),
        match_reasons={k: list(v) for k, v in result.match_reasons.items()},
        nodes=[_retrieval_node_view(obj) for obj in result.objects],
        relationships=[_retrieval_relationship_view(rel) for rel in result.relationships],
        attributes=_retrieval_attribute_views(result.property_assertions),
        source_anchors=_source_anchor_views(
            result.anchors, revision_id=result.snapshot.revision_id
        ),
        coverage=coverage,
        trust_boundary=_retrieval_trust_boundary(),
        diagnostics=_coverage_diagnostics(coverage),
    )


def get_neighborhood_direct(
    services: DirectWorldGraphReadServices,
    request: WorldGraphNeighborhoodRequest,
) -> WorldGraphRetrievalResult:
    try:
        dnd_request = _map_retrieval_context(request, services.binding)
        result = services.retrieval.get_neighborhood(
            dnd_request,
            seed_object_ids=request.seed_node_ids,
            depth=request.max_depth,
            bounds=_retrieval_bounds(request.bounds),
        )
        return _neighborhood_result_view(result, request=request)
    except Exception as exc:  # noqa: BLE001
        raise _map_direct_error(exc) from exc


def _neighborhood_result_view(
    result: NeighborhoodResult,
    *,
    request: WorldGraphNeighborhoodRequest,
) -> WorldGraphRetrievalResult:
    coverage = _coverage_view(result.coverage)
    has_content = bool(result.objects)
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(coverage.missing_seed_node_ids or coverage.missing_evidence_ref_ids),
        has_content=has_content,
    )
    return WorldGraphRetrievalResult(
        operation="neighborhood",
        outcome=outcome,
        snapshot=_retrieval_snapshot_view(
            result.snapshot, focus=request.focus.to_projection_focus()
        ),
        request_summary={
            "seed_node_ids": list(request.seed_node_ids),
            "max_depth": request.max_depth,
        },
        nodes=[_retrieval_node_view(obj) for obj in result.objects],
        relationships=[_retrieval_relationship_view(rel) for rel in result.relationships],
        attributes=_retrieval_attribute_views(result.property_assertions),
        source_anchors=_source_anchor_views(
            result.anchors, revision_id=result.snapshot.revision_id
        ),
        coverage=coverage,
        trust_boundary=_retrieval_trust_boundary(),
        diagnostics=_coverage_diagnostics(coverage),
    )


_EVIDENCE_TARGET_KIND_MAP = {
    "node": "object",
    "relationship": "relationship",
    "attribute": "assertion",
}


def get_evidence_direct(
    services: DirectWorldGraphReadServices,
    request: WorldGraphEvidenceRequest,
) -> WorldGraphRetrievalResult:
    try:
        kind = _EVIDENCE_TARGET_KIND_MAP.get(request.target.kind)
        if kind is None:
            raise DirectWorldGraphReadError(
                f"Unsupported evidence target kind: {request.target.kind!r}.",
                code="invalid_request",
                status_code=422,
            )
        dnd_request = _map_retrieval_context(request, services.binding)
        target = EvidenceTarget(kind=kind, target_id=request.target.id)
        result = services.retrieval.get_evidence(dnd_request, target=target)
        return _evidence_result_view(result, request=request)
    except Exception as exc:  # noqa: BLE001
        raise _map_direct_error(exc) from exc


def _evidence_result_view(
    result: Any,
    *,
    request: WorldGraphEvidenceRequest,
) -> WorldGraphRetrievalResult:
    coverage = _coverage_view(result.coverage)
    has_content = result.found and bool(result.evidence)
    outcome = _determine_outcome(
        truncated=bool(coverage.truncated_fields),
        partial=bool(coverage.missing_evidence_ref_ids),
        has_content=has_content,
    )
    nodes = [_retrieval_node_view(result.object)] if result.object else []
    relationships = (
        [_retrieval_relationship_view(result.relationship)] if result.relationship else []
    )
    attributes = (
        _retrieval_attribute_views([result.assertion]) if result.assertion else []
    )
    return WorldGraphRetrievalResult(
        operation="evidence",
        outcome=outcome,
        snapshot=_retrieval_snapshot_view(
            result.snapshot, focus=request.focus.to_projection_focus()
        ),
        request_summary={"target_kind": request.target.kind, "target_id": request.target.id},
        nodes=nodes,
        relationships=relationships,
        attributes=attributes,
        source_anchors=_source_anchor_views(
            result.anchors, revision_id=result.snapshot.revision_id
        ),
        coverage=coverage,
        trust_boundary=_retrieval_trust_boundary(),
        diagnostics=_coverage_diagnostics(coverage),
    )


def read_source_anchor_direct(
    services: DirectWorldGraphReadServices,
    request: WorldGraphSourceAnchorReadRequest,
    *,
    repo_root: Path,
) -> WorldGraphSourceAnchorReadResult:
    """Opaque anchor revalidation (DungeonMind) + product-local content join."""
    try:
        dnd_request = _map_retrieval_context(request, services.binding)
        resolution = services.retrieval.resolve_source_anchor(
            dnd_request, anchor_id=_dnd_anchor_id(request.anchor_id)
        )
        return _anchor_read_view(services, resolution, request=request, repo_root=repo_root)
    except Exception as exc:  # noqa: BLE001
        raise _map_direct_error(exc) from exc


_RECAP_PARAGRAPH_SPAN = re.compile(r"(?:^|:)paragraph:(\d+)$")
_DIGEST_BOUND_LINE_SPAN = re.compile(r":span:([0-9a-f]{12}):(\d+)-(\d+)$", re.IGNORECASE)


def split_recap_body_paragraphs(text: str) -> list[str]:
    """Split a digest-pinned recap into body paragraphs after YAML frontmatter."""
    body = text
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) == 3:
            body = parts[2].lstrip("\n")
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body) if paragraph.strip()]


def extract_span_from_revision_bound_text(
    *,
    text: str,
    span_id: str,
    digest: str,
) -> tuple[str, int | None, int | None] | None:
    """Resolve a recap span from digest-pinned parent bytes only.

    Supported identities:
    - ``…:paragraph:NNN`` — Nth body paragraph after frontmatter
    - ``…:span:<12-hex-digest-prefix>:<start>-<end>`` — 1-based inclusive
      line range, only when the prefix matches the admitted parent digest

    Sidecar files and ``source_span_index.json`` are not consulted.
    """
    paragraph = _RECAP_PARAGRAPH_SPAN.search(span_id)
    if paragraph is not None:
        index = int(paragraph.group(1))
        paragraphs = split_recap_body_paragraphs(text)
        if 1 <= index <= len(paragraphs):
            return paragraphs[index - 1], None, None
        return None
    line_span = _DIGEST_BOUND_LINE_SPAN.search(span_id)
    if line_span is not None:
        prefix, start_line, end_line = (
            line_span.group(1).lower(),
            int(line_span.group(2)),
            int(line_span.group(3)),
        )
        if not digest.lower().startswith(prefix):
            return None
        if start_line < 1 or end_line < start_line:
            return None
        lines = text.splitlines()
        if end_line > len(lines):
            return None
        return "\n".join(lines[start_line - 1 : end_line]), start_line, end_line
    return None


def _unavailable_anchor_result(
    *,
    base: dict[str, Any],
    code: str,
    message: str,
) -> WorldGraphSourceAnchorReadResult:
    return WorldGraphSourceAnchorReadResult(
        outcome="unavailable",
        diagnostics=[
            WorldGraphRetrievalDiagnostic(code=code, message=message, severity="warning")
        ],
        truncated=False,
        **base,
    )


def _read_admitted_repo_span(
    services: DirectWorldGraphReadServices,
    anchor: SourceAnchorMetadata,
    *,
    request: WorldGraphSourceAnchorReadRequest,
    repo_root: Path,
    base: dict[str, Any],
) -> WorldGraphSourceAnchorReadResult:
    """Digest-pinned recap/other repo:// span join after DungeonMind revalidation.

    Span content is sliced from the parent file whose bytes match the
    DungeonMind source-revision digest. Paragraph identities and
    digest-prefixed line ranges are resolved from those bound bytes.
    Sidecar ``source_spans/`` files and ``source_span_index.json`` are
    unbound mappings and are not read.
    """
    uri = getattr(anchor.artifact, "uri", None) or ""
    relative_path = parse_repo_uri(uri)
    span_id = (anchor.source_span_ref_id or "").strip()
    digest = _source_revision_digest(services, anchor.source_revision_id)
    expected = (digest or "").removeprefix("sha256:").strip().lower()
    if relative_path is None or not span_id or not expected:
        return _unavailable_anchor_result(
            base=base,
            code="unsupported_locator",
            message="Admitted recap/repo span is missing a URI, span id, or digest.",
        )
    try:
        resolved_root = repo_root.resolve()
        parent_path = (resolved_root / relative_path).resolve()
        parent_path.relative_to(resolved_root)
        raw = parent_path.read_bytes()
    except (OSError, ValueError) as exc:
        return _unavailable_anchor_result(
            base=base,
            code="source_unavailable",
            message=f"source file unavailable: {exc}",
        )
    actual = hashlib.sha256(raw).hexdigest().lower()
    if actual != expected:
        return _unavailable_anchor_result(
            base=base,
            code="source_integrity_error",
            message="source file content does not match the DungeonMind revision digest",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _unavailable_anchor_result(
            base=base,
            code="source_integrity_error",
            message="source file is not valid UTF-8 text",
        )
    extracted = extract_span_from_revision_bound_text(
        text=text, span_id=span_id, digest=actual
    )
    if extracted is None:
        return _unavailable_anchor_result(
            base=base,
            code="source_unavailable",
            message=(
                "Admitted span could not be resolved from digest-pinned parent "
                "bytes; unbound sidecar/index mappings are not served."
            ),
        )
    content, line_start, line_end = extracted
    truncated = len(content) > request.max_chars
    return WorldGraphSourceAnchorReadResult(
        outcome="truncated" if truncated else "enough",
        diagnostics=[],
        media_type="text/markdown",
        content=content[: request.max_chars],
        content_sha256=actual,
        line_start=line_start,
        line_end=line_end,
        truncated=truncated,
        **base,
    )


def _anchor_read_view(
    services: DirectWorldGraphReadServices,
    resolution: SourceAnchorResolution,
    *,
    request: WorldGraphSourceAnchorReadRequest,
    repo_root: Path,
) -> WorldGraphSourceAnchorReadResult:
    snapshot = _retrieval_snapshot_view(
        resolution.snapshot, focus=request.focus.to_projection_focus()
    )
    if not resolution.found or resolution.anchor is None:
        return WorldGraphSourceAnchorReadResult(
            outcome="empty",
            snapshot=snapshot,
            anchor_id=request.anchor_id,
            trust_boundary=_retrieval_trust_boundary(),
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="unknown_anchor",
                    message=(
                        "No admissible source anchor matches this anchor id in the "
                        "requested context."
                    ),
                    severity="warning",
                )
            ],
            truncated=False,
        )
    anchor = resolution.anchor
    locator_kind = _classify_locator_kind(anchor)
    base: dict[str, Any] = dict(
        snapshot=snapshot,
        anchor_id=request.anchor_id,
        evidence_ref_id=anchor.evidence_ref_id,
        source_artifact_id=anchor.source_artifact_id,
        source_domain=anchor.evidence.source_domain,
        source_span_ref_id=anchor.source_span_ref_id,
        locator_kind=locator_kind,
        trust_boundary=_retrieval_trust_boundary(),
    )
    if not anchor.can_open_source or locator_kind == "unsupported":
        return WorldGraphSourceAnchorReadResult(
            outcome="partial",
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="unsupported_locator",
                    message=(
                        "This source anchor's locator/URI scheme is not supported for reading."
                    ),
                    severity="warning",
                )
            ],
            truncated=False,
            **base,
        )
    if locator_kind == "source_span":
        # Worldbuilding spans compose the registry-backed opener, matching
        # the legacy live-control dispatch. Recap/other repo:// spans are a
        # digest-pinned product-local join after DungeonMind revalidation.
        domain = str(getattr(anchor.evidence, "source_domain", "") or "")
        if domain == "worldbuilding":
            from apps.live_control_server.services.worldbuilding_source_span_read import (
                read_admitted_worldbuilding_span,
            )

            digest = _source_revision_digest(services, anchor.source_revision_id)
            try:
                return read_admitted_worldbuilding_span(
                    root=repo_root,
                    source_artifact_id=anchor.source_artifact_id,
                    source_span_ref_id=str(anchor.source_span_ref_id),
                    graph_content_sha256=digest,
                    max_chars=request.max_chars,
                    anchor_id=request.anchor_id,
                    evidence_ref_id=anchor.evidence_ref_id,
                    snapshot=snapshot,
                    graph_artifact=None,
                )
            except WorldGraphRetrievalError as exc:
                return WorldGraphSourceAnchorReadResult(
                    outcome="unavailable",
                    diagnostics=[
                        WorldGraphRetrievalDiagnostic(
                            code=getattr(exc, "code", None) or "source_unavailable",
                            message=str(exc),
                            severity="warning",
                        )
                    ],
                    truncated=False,
                    **base,
                )
        return _read_admitted_repo_span(
            services,
            anchor,
            request=request,
            repo_root=repo_root,
            base=base,
        )
    digest = _source_revision_digest(services, anchor.source_revision_id)
    if digest is None:
        raise DirectWorldGraphReadError(
            "Source artifact is missing a revision-bound content digest.",
            code="source_integrity_error",
            status_code=409,
        )
    uri = getattr(anchor.artifact, "uri", None) or ""
    try:
        if locator_kind == "heading":
            relative_path = parse_repo_uri(uri)
            heading_text = parse_heading_locator(anchor.locator_identity or "")
            if relative_path is None or heading_text is None:
                raise DirectWorldGraphReadError(
                    "Heading anchor URI/locator no longer matches the expected "
                    "repo:// + heading: shape.",
                    code="projection_integrity_error",
                    status_code=409,
                )
            outcome = read_repo_heading_anchor(
                repo_root=repo_root,
                relative_path=relative_path,
                heading_text=heading_text,
                expected_content_sha256=digest,
                max_chars=request.max_chars,
            )
        else:  # json_pointer
            relative_path = parse_graph_data_uri(uri)
            json_pointer = parse_json_pointer_locator(anchor.locator_identity or "")
            if relative_path is None or json_pointer is None:
                raise DirectWorldGraphReadError(
                    "JSON-pointer anchor locator no longer matches the expected "
                    "graph-data:// + jsonptr: shape.",
                    code="projection_integrity_error",
                    status_code=409,
                )
            payload = _read_verified_json_file(
                repo_root / relative_path, expected_content_sha256=digest
            )
            outcome = read_graph_data_json_pointer_anchor(
                contribution_payload=payload,
                json_pointer=json_pointer,
                max_chars=request.max_chars,
            )
    except SourceReadError as exc:
        return WorldGraphSourceAnchorReadResult(
            outcome="unavailable",
            diagnostics=[
                WorldGraphRetrievalDiagnostic(
                    code="source_unavailable",
                    message=str(exc),
                    severity="warning",
                )
            ],
            truncated=False,
            **base,
        )
    return WorldGraphSourceAnchorReadResult(
        outcome="enough",
        diagnostics=[],
        media_type=outcome.media_type,
        content=outcome.content,
        content_sha256=outcome.content_sha256,
        line_start=outcome.line_start,
        line_end=outcome.line_end,
        truncated=bool(outcome.truncated),
        **base,
    )


def _read_verified_json_file(
    path: Path,
    *,
    expected_content_sha256: str,
) -> dict[str, Any]:
    """Read a product-local JSON file pinned to the DungeonMind digest."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SourceReadError(f"source file unavailable: {exc}", code="source_unavailable") from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_content_sha256:
        raise SourceReadError(
            "source file content does not match the DungeonMind revision digest",
            code="source_integrity_error",
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceReadError(f"source file is not valid JSON: {exc}", code="source_integrity_error") from exc
    if not isinstance(payload, dict):
        raise SourceReadError("source file JSON payload is not an object", code="source_integrity_error")
    return payload
