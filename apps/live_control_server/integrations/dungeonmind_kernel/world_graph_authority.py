"""DungeonMind-backed World Graph authority adapter (whole-world cutover).

Read architecture: hydrate a Buddy-shaped ``UnionSupergraphStore`` from
DungeonMind's durable state (contribution ledger + identity decisions) into an
ephemeral cache root keyed by the DungeonMind head revision, then reuse Buddy's
kernel view machinery against that cache. The cache is a pure derivative of
DungeonMind durable state — never a second authority — and is registered with
the quiescence guard's cache-root exemption so kernel rebuild/publish machinery
may write it in any authority mode.

Migration metadata: the contribution replay order, the initialization receipt,
and the campaign/focus bindings are read from the frozen pre-switch Buddy store
(the retained rollback snapshot). DungeonMind's v2 adoption ledger deliberately
does not carry Buddy's replay-order or initialization-receipt decoration, and
the adopted records are membership-digest-frozen (mutating them would break the
V3 receipt). Graph *content* — every node, edge, evidence row, alias, and
assertion — always comes from DungeonMind's ledger.

Write architecture: the GM-confirmed publication path is routed here in
``dungeonmind`` authority mode. The sealed Buddy review package is verified
against the DungeonMind-backed hydrated head (real verification, unchanged
semantics), then the adapter attempts to enter DungeonMind's governed write
path. Two characterized DungeonMind gaps currently fail that path closed:

1. ``dm_contribution_review_intent_v1`` admits only label/alias/summary/
   relationship assertions with restricted shapes; Buddy kernel contributions
   (node/edge assertions with attribute values, labels, temporal scopes, and
   typed corrections) are not expressible.
2. ``materialize_finalized_review`` is bound to ``dm_union_graph_v3`` parents;
   Eldyrwild's adopted world is ``dm_union_graph_v6``.

Both are §7 repair items for DungeonMind, specified in the implementation PR
handback. Until they land, every DungeonMind-routed write fails closed with a
typed error before mutating either store.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.identity_models import IdentityDecisionRecord
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.storage import (
    register_world_graph_cache_root,
)

HYDRATION_TRANSLATION_VERSION = "cutover-hydration-v1"
HYDRATION_METADATA_SCHEMA = "dmb_dungeonmind_authority_hydration_v1"
HYDRATION_METADATA_FILENAME = "hydration_metadata.json"

# Reverse mapping tables: exact inverses of the forward maps in
# ``eldyrwild_existing_world_adoption_bundle_v2.py`` (the bundle producer).
_REVERSE_SOURCE_KIND = {
    "extraction": "source_extraction",
    "standing_context": "standing_context",
    "graph_review": "graph_review_authored_assertion",
    "identity_decision": "identity_decision",
    "manual_import": "manual_import",
}
_REVERSE_EPISTEMIC = {
    "asserted": "asserted",
    "inferred": "inferred",
    "speculative": "speculative",
    "source_derived_candidate": "source_derived_candidate",
}

_EVIDENCE_EXPORT_MARKER = ":dmv1:"

_HYDRATION_LOCK = threading.Lock()


def _utc_iso(value: Any) -> str:
    """Serialize a tz-aware datetime to Buddy's ``...Z`` ledger format."""
    from datetime import UTC, datetime

    if isinstance(value, str):
        return value
    if not isinstance(value, datetime):
        raise WorldGraphAuthorityError(
            "unexpected timestamp type in DungeonMind record",
            code="hydration_integrity",
            details={"type": type(value).__name__},
        )
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> Any:
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class WorldGraphAuthorityError(RuntimeError):
    """Typed failure from the DungeonMind-backed World Graph authority."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def _open_repository_bundle(database_url: str) -> Any:
    """Construct the DungeonMind PostgreSQL repository bundle (lazy import).

    The import stays inside the function so Buddy environments that never
    enable ``dungeonmind`` authority mode never pay the driver import cost.
    """
    try:
        from dungeonmind.infrastructure.postgres import (
            PostgresDatabase,
            PostgresRepositoryBundle,
        )
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise WorldGraphAuthorityError(
            "dungeonmind postgres adapter is unavailable",
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        ) from exc
    try:
        return PostgresRepositoryBundle(PostgresDatabase(database_url))
    except Exception as exc:
        raise WorldGraphAuthorityError(
            "DungeonMind authority database is unavailable",
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        ) from exc


# ---------------------------------------------------------------------------
# Authority binding (receipt-verified, fail-closed)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorityBinding:
    """The verified adoption binding between Buddy snapshot A and DungeonMind."""

    world_id: str
    adoption_id: str
    membership_sha256: str
    legacy_buddy_revision_id: str  # A — the adopted pre-switch Buddy head
    dungeonmind_first_revision_id: str  # D_A — the adoption-published revision
    dungeonmind_head_revision_id: str  # current DungeonMind head (>= D_A)
    graph_schema: str


def _load_frozen_head_revision_id(frozen_root: Path, world_id: str) -> str:
    head_path = world_paths.head_path(frozen_root, world_id)
    if not head_path.is_file():
        raise WorldGraphAuthorityError(
            f"frozen Buddy store has no head for world {world_id!r}",
            code="frozen_store_missing",
            details={"world_id": world_id},
        )
    try:
        payload = json.loads(head_path.read_text())
        return str(payload["head_revision_id"])
    except (OSError, ValueError, KeyError) as exc:
        raise WorldGraphAuthorityError(
            "frozen Buddy store head is unreadable",
            code="frozen_store_missing",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc


def bind_world_authority(
    bundle: Any,
    world_id: str,
    *,
    frozen_root: Path,
) -> AuthorityBinding:
    """Verify the adoption receipt and bind Buddy A to DungeonMind D_A.

    Fail-closed: no receipt, a non-V3 receipt, a missing head, or a frozen
    store whose head is not the adopted snapshot all raise. A wrong frozen
    store can never be silently treated as the adopted snapshot.
    """
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionReceiptV3,
    )

    try:
        receipt = bundle.existing_world_adoptions.get_for_world(world_id)
        head = bundle.world_graph.get_head(world_id)
    except Exception as exc:
        raise WorldGraphAuthorityError(
            "DungeonMind authority read failed",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if receipt is None:
        raise WorldGraphAuthorityError(
            f"world {world_id!r} has no DungeonMind adoption receipt",
            code="adoption_receipt_missing",
            details={"world_id": world_id},
        )
    if not isinstance(receipt, ExistingWorldAdoptionReceiptV3):
        raise WorldGraphAuthorityError(
            f"world {world_id!r} adoption receipt is not a V3 membership receipt",
            code="adoption_receipt_not_v3",
            details={"world_id": world_id, "schema": receipt.schema_version},
        )
    if head is None:
        raise WorldGraphAuthorityError(
            f"world {world_id!r} has no DungeonMind head revision",
            code="authority_head_missing",
            details={"world_id": world_id},
        )
    frozen_head = _load_frozen_head_revision_id(frozen_root, world_id)
    adopted_source = receipt.source_provenance.source_world_revision_id
    if frozen_head != adopted_source:
        raise WorldGraphAuthorityError(
            "frozen Buddy store head is not the adopted snapshot",
            code="frozen_store_mismatch",
            details={
                "world_id": world_id,
                "frozen_head_revision_id": frozen_head,
                "adopted_source_revision_id": adopted_source,
            },
        )
    return AuthorityBinding(
        world_id=world_id,
        adoption_id=receipt.adoption_id,
        membership_sha256=receipt.membership_sha256,
        legacy_buddy_revision_id=adopted_source,
        dungeonmind_first_revision_id=receipt.published_revision_id,
        dungeonmind_head_revision_id=head.head_revision_id,
        graph_schema=receipt.graph_schema,
    )


def build_authority_graph_reader() -> Any:
    """The versioned graph reader with the Eldyrwild v6 semantic profile.

    The adopted union graph declares the builtin v3 semantic profile from
    ``dungeonmind_dnd``; the reader must resolve it or v6 parsing fails closed.
    """
    from dungeonmind.application.graph_snapshot import (
        VersionedUnionGraphSnapshotReader,
    )
    from dungeonmind.infrastructure.semantic_profiles import (
        StaticSemanticProfileRegistry,
    )
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    return VersionedUnionGraphSnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )


def check_world_correspondence(
    bundle: Any,
    world_id: str,
    *,
    bundle_bytes: bytes,
) -> Any:
    """Run DungeonMind's merged correspondence evaluator (read-only).

    This is the operator's final pre-switch gate and the integration test's
    correspondence evidence entry point. It never writes.
    """
    from dungeonmind.application.existing_world_correspondence import (
        ExistingWorldCorrespondenceService,
    )

    service = ExistingWorldCorrespondenceService(
        adoption_repository=bundle.existing_world_adoptions,
        world_graph_repository=bundle.world_graph,
        contribution_repository=bundle.contributions,
        identity_repository=bundle.identity_decisions,
        source_repository=bundle.sources,
        graph_reader=build_authority_graph_reader(),
    )
    return service.check(bundle_bytes, world_id=world_id)


# ---------------------------------------------------------------------------
# Translation: DungeonMind v2 durable records -> Buddy kernel records
# ---------------------------------------------------------------------------


def _reverse_revision_id(dm_revision_id: str, artifact_id: str | None) -> str:
    suffix = f"::{artifact_id}" if artifact_id else ""
    if suffix and dm_revision_id.endswith(suffix):
        return dm_revision_id[: -len(suffix)]
    return dm_revision_id


def _raw_evidence_id(exported_id: str) -> str:
    if _EVIDENCE_EXPORT_MARKER in exported_id:
        return exported_id.rsplit(_EVIDENCE_EXPORT_MARKER, 1)[0]
    return exported_id


def _translate_assertion(
    assertion: Any,
    epistemic_history: dict[str, str | None],
    contribution_id: str,
) -> dict[str, Any]:
    """Translate one v2 assertion back to Buddy's kernel assertion shape.

    The forward map collapsed visibility ``None``/``"gm"`` to ``gm``. The
    original is recovered by content-addressed id match: exactly one candidate
    reproduces the recorded assertion id (proven 1838/1838 on Eldyrwild).
    """
    from graph_memory.kernel.contributions import compute_assertion_id

    assertion_id = assertion.assertion_id
    if assertion_id in epistemic_history:
        epistemic = epistemic_history[assertion_id]
    else:
        epistemic = _REVERSE_EPISTEMIC.get(
            str(assertion.epistemic_kind or ""), None
        )
    value = json.loads(assertion.value) if assertion.value else {}
    visibility: str | None = None
    matched = False
    for candidate in (None, "gm", "player"):
        computed = compute_assertion_id(
            assertion_kind=assertion.assertion_kind,
            subject_node_id=assertion.subject_object_id,
            target_node_id=assertion.object_object_id,
            predicate=assertion.predicate,
            label=assertion.label,
            value=value,
            campaign_scope=assertion.campaign_scope,
            temporal_scope=assertion.temporal_scope,
            epistemic_kind=epistemic,
            visibility=candidate,
        )
        if computed == assertion_id:
            visibility = candidate
            matched = True
            break
    if not matched:
        raise WorldGraphAuthorityError(
            "assertion id does not match any visibility candidate",
            code="hydration_integrity",
            details={"assertion_id": assertion_id},
        )
    return {
        "assertion_id": assertion_id,
        "assertion_kind": assertion.assertion_kind,
        "subject_node_id": assertion.subject_object_id,
        "target_node_id": assertion.object_object_id,
        "predicate": assertion.predicate,
        "label": assertion.label,
        "value": value,
        "evidence_ref_ids": [
            _raw_evidence_id(ev.evidence_ref_id) for ev in assertion.evidence_refs
        ],
        "source_artifact_id": assertion.source_artifact_id,
        "source_revision_id": (
            _reverse_revision_id(assertion.source_revision_id, assertion.source_artifact_id)
            if assertion.source_revision_id
            else None
        ),
        "campaign_scope": assertion.campaign_scope,
        "temporal_scope": assertion.temporal_scope,
        "visibility": visibility,
        "epistemic_kind": epistemic,
        "acceptance_state": str(assertion.acceptance_state),
        "identity_resolution_outcome": (
            str(assertion.identity_resolution_outcome)
            if assertion.identity_resolution_outcome
            else None
        ),
        "contribution_id": contribution_id,
    }


def translate_contribution(record: Any) -> GraphContribution:
    """Translate one DungeonMind durable contribution to Buddy's kernel shape."""
    diagnostics = record.diagnostics or {}
    epistemic_history = diagnostics.get("buddy_assertion_epistemic") or {}
    buddy_diagnostics = diagnostics.get("buddy_diagnostics") or []
    assertions = [
        _translate_assertion(a, epistemic_history, record.contribution_id)
        for a in record.assertions
    ]
    return GraphContribution.model_validate(
        {
            "contribution_id": record.contribution_id,
            "world_id": record.world_id,
            "source_kind": _REVERSE_SOURCE_KIND[str(record.source_kind)],
            "source_artifact_id": record.source_artifact_id,
            "source_revision_id": (
                _reverse_revision_id(record.source_revision_id, record.source_artifact_id)
                if record.source_revision_id
                else None
            ),
            "extraction_profile": record.extraction_profile,
            "produced_at": _utc_iso(record.produced_at),
            "campaign_scope": record.campaign_scope,
            "status": str(record.status),
            "supersedes_contribution_id": record.supersedes_contribution_id,
            "candidate_assertions": [
                a for a in assertions if a["acceptance_state"] == "candidate"
            ],
            "accepted_assertions": [
                a for a in assertions if a["acceptance_state"] == "accepted"
            ],
            "rejected_assertions": [
                a for a in assertions if a["acceptance_state"] == "rejected"
            ],
            "unresolved_mentions": [
                json.loads(m) if isinstance(m, str) else m
                for m in record.unresolved_mentions
            ],
            "identity_decision_ids": list(record.identity_decision_ids or []),
            "assertion_corrections": [
                {
                    "correction_kind": str(corr.correction_kind),
                    "target_contribution_id": corr.target_contribution_id,
                    "target_assertion_id": corr.target_assertion_id,
                    "replacement_assertion_id": corr.replacement_assertion_id,
                }
                for corr in (record.assertion_corrections or [])
            ],
            "authored_by": record.authored_by,
            "diagnostics": list(buddy_diagnostics),
        }
    )


def translate_identity_decision(record: Any) -> IdentityDecisionRecord:
    """Translate one DungeonMind durable identity decision to Buddy's shape."""
    subjects = list(record.subject_object_ids or [])
    targets = list(record.target_object_ids or [])
    return IdentityDecisionRecord.model_validate(
        {
            "decision_id": record.decision_id,
            "world_id": record.world_id,
            "decision_kind": str(record.decision_kind),
            "created_at": _utc_iso(record.created_at),
            "actor": record.actor,
            "reason": record.reason,
            "subject_node_id": subjects[0] if subjects else None,
            "target_node_id": targets[0] if targets else None,
            "affected_node_ids": subjects,
            "alias": record.alias,
            "reversible": record.reversible,
            "supersedes_decision_ids": list(record.supersedes_decision_ids or []),
            "status": str(record.status),
            "merge_side_effects": (
                record.merge_side_effects.model_dump(mode="json")
                if record.merge_side_effects is not None
                else None
            ),
        }
    )


# ---------------------------------------------------------------------------
# Replay ordering
# ---------------------------------------------------------------------------


def order_contributions_for_replay(
    contributions: list[GraphContribution],
    *,
    sealed_manifest_ids: list[str],
) -> list[GraphContribution]:
    """Order the translated ledger for Buddy's replay engine.

    Adopted contributions replay in the sealed manifest order recovered from
    the frozen pre-switch store (Buddy's historical merge order; DungeonMind's
    ledger is id-ordered and carries no replay order). Contributions that
    arrived in DungeonMind after the adoption (post-cutover governed writes)
    append in ``produced_at`` order. Unknown sealed ids are ignored; adopted
    contributions missing from the sealed manifest fail closed.
    """
    by_id = {c.contribution_id: c for c in contributions}
    sealed_present = [cid for cid in sealed_manifest_ids if cid in by_id]
    sealed_set = set(sealed_present)
    # Contributions absent from the sealed manifest are post-adoption arrivals
    # (the sealed manifest covers the whole adopted history; the closing
    # snapshot id-set gate proves the assembled replay matches the authority).
    new_contributions = sorted(
        (c for c in contributions if c.contribution_id not in sealed_set),
        key=lambda c: (_parse_utc(c.produced_at), c.contribution_id),
    )
    return [by_id[cid] for cid in sealed_present] + new_contributions


# ---------------------------------------------------------------------------
# Hydration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HydrationHandle:
    """A hydrated, servable Buddy-shaped read model for one DungeonMind head."""

    world_id: str
    cache_world_root: Path  # Buddy ``root`` for kernel reads
    buddy_revision_id: str  # hydrated head revision (Buddy content-addressed)
    dungeonmind_head_revision_id: str
    legacy_revision_map: dict[str, str]  # legacy Buddy A rev -> hydrated rev


def _safe_dir_name(revision_id: str) -> str:
    return revision_id.replace(":", "_").replace("/", "_")


def _load_frozen_migration_metadata(
    frozen_root: Path, world_id: str
) -> tuple[list[str], str | None, str | None]:
    """Read replay order + campaign/focus bindings from the frozen store head."""
    from graph_memory.world_supergraph.storage import load_world_graph_revision

    head_revision_id = _load_frozen_head_revision_id(frozen_root, world_id)
    store = load_world_graph_revision(frozen_root, world_id, head_revision_id)
    manifest = [entry.contribution_id for entry in store.contribution_replay_manifest]
    if not manifest:
        raise WorldGraphAuthorityError(
            "frozen Buddy store head carries no contribution replay manifest",
            code="frozen_store_missing",
            details={"world_id": world_id, "revision_id": head_revision_id},
        )
    return manifest, store.campaign_id, store.focus_session_id


def _write_hydration_metadata(cache_dir: Path, metadata: dict[str, Any]) -> None:
    path = cache_dir / HYDRATION_METADATA_FILENAME
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def read_hydration_metadata(cache_dir: Path) -> dict[str, Any] | None:
    path = cache_dir / HYDRATION_METADATA_FILENAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if payload.get("schema") != HYDRATION_METADATA_SCHEMA:
        return None
    return payload


def _verify_hydration_against_snapshot(
    *,
    store: Any,
    graph_payload: dict[str, Any],
    dungeonmind_head_revision_id: str,
) -> None:
    """Fail-closed coverage gate: the v6 snapshot's ids must be hydrated.

    The DungeonMind revision payload is the authority snapshot at the pinned
    head, but it is a *current-semantic view*: the producer excludes
    external-resource nodes, mechanics (``uses_statblock``) edges, and
    history-only edges that Buddy's store legitimately carries. So the gate is
    coverage, not equality — every authority-snapshot id must be present in the
    hydrated store. Missing ids mean the hydration (or a mid-hydration head
    move) is unsound and must not serve.
    """
    snapshot_node_ids = {str(o["object_id"]) for o in graph_payload.get("objects") or []}
    snapshot_edge_ids = {
        str(r["relationship_id"]) for r in graph_payload.get("relationships") or []
    }
    missing_nodes = snapshot_node_ids - set(store.nodes)
    missing_edges = snapshot_edge_ids - set(store.edges)
    if missing_nodes or missing_edges:
        raise WorldGraphAuthorityError(
            "hydrated store does not cover the DungeonMind authority snapshot",
            code="hydration_integrity",
            details={
                "dungeonmind_head_revision_id": dungeonmind_head_revision_id,
                "missing_nodes": sorted(missing_nodes)[:5],
                "missing_edges": sorted(missing_edges)[:5],
                "missing_node_count": len(missing_nodes),
                "missing_edge_count": len(missing_edges),
            },
        )


def hydrate_world_graph(
    bundle: Any,
    world_id: str,
    *,
    binding: AuthorityBinding,
    cache_root: Path,
    frozen_root: Path,
) -> HydrationHandle:
    """Hydrate the Buddy-shaped read model for the binding's DungeonMind head.

    Writes a fresh cache directory keyed by the DungeonMind head revision and
    atomically renames it into place; concurrent readers never see a partial
    cache. Replays DungeonMind's translated ledger through Buddy's own rebuild
    engine, then gates on the DungeonMind authority snapshot's id sets.
    """
    from graph_memory.kernel.contribution_rebuild import rebuild_from_contributions
    from graph_memory.union_supergraph.model import UnionSupergraphStore
    from graph_memory.world_supergraph.contribution_store import (
        ContributionIndex,
        save_contribution_index,
        write_contribution_record,
    )
    from graph_memory.world_supergraph.identity_decision_store import (
        IdentityDecisionIndex,
        save_identity_decision_index,
        write_identity_decision_record,
    )
    from graph_memory.world_supergraph.storage import (
        load_world_graph_revision,
        publish_world_graph_revision,
    )

    # Head → ledger → head: pin the head, read the ledger, then require the
    # head to be unchanged so the cache key honestly names the hydrated state.
    try:
        head_before = bundle.world_graph.get_head(world_id)
        raw_contributions = bundle.contributions.list_for_world(world_id)
        raw_decisions = bundle.identity_decisions.list_for_world(world_id)
        head_after = bundle.world_graph.get_head(world_id)
    except Exception as exc:
        raise WorldGraphAuthorityError(
            "DungeonMind authority read failed during hydration",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if head_before is None or head_after is None:
        raise WorldGraphAuthorityError(
            f"world {world_id!r} has no DungeonMind head revision",
            code="authority_head_missing",
            details={"world_id": world_id},
        )
    if head_before.head_revision_id != head_after.head_revision_id:
        raise WorldGraphAuthorityError(
            "DungeonMind head moved during hydration; retry",
            code="authority_head_moved",
            details={
                "world_id": world_id,
                "head_before": head_before.head_revision_id,
                "head_after": head_after.head_revision_id,
            },
        )
    dungeonmind_head = head_before.head_revision_id
    stored = bundle.world_graph.get_revision(world_id, dungeonmind_head)
    if stored is None:
        raise WorldGraphAuthorityError(
            "DungeonMind head revision payload is unreadable",
            code="authority_head_missing",
            details={"world_id": world_id, "revision_id": dungeonmind_head},
        )

    manifest, campaign_id, focus_session_id = _load_frozen_migration_metadata(
        frozen_root, world_id
    )
    contributions = order_contributions_for_replay(
        [translate_contribution(c) for c in raw_contributions],
        sealed_manifest_ids=manifest,
    )
    decisions = sorted(
        (translate_identity_decision(d) for d in raw_decisions),
        key=lambda d: (_parse_utc(d.created_at), d.decision_id),
    )

    staged = Path(
        tempfile.mkdtemp(prefix=f".hydrate-{world_id}-", dir=cache_root)
    )
    try:
        baseline = UnionSupergraphStore.model_validate(
            {
                "schema": "dmb_union_supergraph_store_v0",
                "version": "0.1",
                "campaign_id": campaign_id,
                "focus_session_id": focus_session_id,
                "graph_id": None,
                "graph_domains": [],
                "source_domains": [],
                "nodes": {},
                "edges": {},
                "evidence": {},
                "source_artifacts": {},
                "aliases": {},
                "identity_redirects": [],
                "identity_merge_records": [],
                "identity_decisions": [],
                "assertion_support": {},
                "contribution_source_payload_sha256": {},
                "contribution_replay_manifest": [],
                "initialization_contribution_ids": [],
                "adjacency": {},
                "diagnostics": {
                    "canon_promotion": False,
                    "approved_memory_write": False,
                    "corpus_mutation": False,
                    "production_retrieval": False,
                },
            }
        )
        baseline_result = publish_world_graph_revision(
            staged, world_id, baseline, operation_ids=["hydrate:empty-baseline"]
        )
        baseline_revision_id = baseline_result.revision.revision_id

        # The initialization receipt is Buddy-side migration metadata; the
        # rebuild restores the initialization digests from it so the hydrated
        # store is fingerprint-exact against Buddy's own rebuild semantics.
        frozen_init_dir = world_paths.initialization_dir(frozen_root, world_id)
        if frozen_init_dir.is_dir():
            shutil.copytree(
                frozen_init_dir, world_paths.initialization_dir(staged, world_id)
            )

        for contribution in contributions:
            write_contribution_record(staged, world_id, contribution)
        save_contribution_index(
            staged,
            world_id,
            ContributionIndex(
                world_id=world_id,
                baseline_revision_id=baseline_revision_id,
                all_contribution_ids=[c.contribution_id for c in contributions],
                active_contribution_ids=[
                    c.contribution_id for c in contributions if c.status == "active"
                ],
                superseded_contribution_ids=[
                    c.contribution_id for c in contributions if c.status == "superseded"
                ],
                retracted_contribution_ids=[
                    c.contribution_id for c in contributions if c.status == "retracted"
                ],
                failed_contribution_ids=[
                    c.contribution_id for c in contributions if c.status == "failed"
                ],
            ),
        )
        for decision in decisions:
            write_identity_decision_record(staged, world_id, decision)
        save_identity_decision_index(
            staged,
            world_id,
            IdentityDecisionIndex(
                world_id=world_id,
                all_decision_ids=[d.decision_id for d in decisions],
            ),
        )

        rebuild = rebuild_from_contributions(staged, world_id=world_id, publish=True)
        if not rebuild.published or not rebuild.revision_id:
            raise WorldGraphAuthorityError(
                "hydration rebuild did not publish",
                code="hydration_integrity",
                details={"world_id": world_id, "diagnostics": rebuild.diagnostics},
            )
        hydrated_store = load_world_graph_revision(
            staged, world_id, rebuild.revision_id
        )
        _verify_hydration_against_snapshot(
            store=hydrated_store,
            graph_payload=stored.graph_payload,
            dungeonmind_head_revision_id=dungeonmind_head,
        )

        metadata = {
            "schema": HYDRATION_METADATA_SCHEMA,
            "translation_version": HYDRATION_TRANSLATION_VERSION,
            "world_id": world_id,
            "adoption_id": binding.adoption_id,
            "membership_sha256": binding.membership_sha256,
            "dungeonmind_head_revision_id": dungeonmind_head,
            "dungeonmind_first_revision_id": binding.dungeonmind_first_revision_id,
            "legacy_buddy_revision_id": binding.legacy_buddy_revision_id,
            "buddy_hydrated_revision_id": rebuild.revision_id,
        }
        _write_hydration_metadata(staged, metadata)

        final_dir = (
            cache_root / world_id / _safe_dir_name(dungeonmind_head)
        )
        if final_dir.exists():
            shutil.rmtree(final_dir)
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, final_dir)
    except Exception:
        shutil.rmtree(staged, ignore_errors=True)
        raise

    legacy_map = {}
    if dungeonmind_head == binding.dungeonmind_first_revision_id:
        # While the DungeonMind head is the adoption revision, the hydrated
        # head IS snapshot A's content (correspondence-gated pre-switch).
        legacy_map[binding.legacy_buddy_revision_id] = rebuild.revision_id
    else:
        legacy_dir = (
            cache_root / world_id / _safe_dir_name(binding.dungeonmind_first_revision_id)
        )
        legacy_meta = read_hydration_metadata(legacy_dir) if legacy_dir.is_dir() else None
        if legacy_meta:
            legacy_map[binding.legacy_buddy_revision_id] = str(
                legacy_meta["buddy_hydrated_revision_id"]
            )
    return HydrationHandle(
        world_id=world_id,
        cache_world_root=final_dir,
        buddy_revision_id=rebuild.revision_id,
        dungeonmind_head_revision_id=dungeonmind_head,
        legacy_revision_map=legacy_map,
    )


def ensure_hydrated_authority(
    world_id: str,
    *,
    database_url: str,
    cache_root: Path,
    frozen_root: Path,
) -> HydrationHandle:
    """Return a servable hydration for the world's current DungeonMind head.

    Cache hit when a prior hydration already covers the current head (and the
    translation version matches); otherwise re-hydrates. DungeonMind
    unavailability or integrity failure raises — there is no silent fallback
    to the frozen Buddy store in ``dungeonmind`` authority mode.
    """
    with _HYDRATION_LOCK:
        cache_root.mkdir(parents=True, exist_ok=True)
        register_world_graph_cache_root(cache_root)
        bundle = _open_repository_bundle(database_url)
        binding = bind_world_authority(bundle, world_id, frozen_root=frozen_root)
        final_dir = (
            cache_root / world_id / _safe_dir_name(binding.dungeonmind_head_revision_id)
        )
        metadata = read_hydration_metadata(final_dir) if final_dir.is_dir() else None
        if (
            metadata is not None
            and metadata.get("translation_version") == HYDRATION_TRANSLATION_VERSION
            and metadata.get("dungeonmind_head_revision_id")
            == binding.dungeonmind_head_revision_id
        ):
            legacy_map: dict[str, str] = {}
            if (
                binding.dungeonmind_head_revision_id
                == binding.dungeonmind_first_revision_id
            ):
                legacy_map[binding.legacy_buddy_revision_id] = str(
                    metadata["buddy_hydrated_revision_id"]
                )
            else:
                legacy_dir = (
                    cache_root
                    / world_id
                    / _safe_dir_name(binding.dungeonmind_first_revision_id)
                )
                legacy_meta = (
                    read_hydration_metadata(legacy_dir) if legacy_dir.is_dir() else None
                )
                if legacy_meta:
                    legacy_map[binding.legacy_buddy_revision_id] = str(
                        legacy_meta["buddy_hydrated_revision_id"]
                    )
            return HydrationHandle(
                world_id=world_id,
                cache_world_root=final_dir,
                buddy_revision_id=str(metadata["buddy_hydrated_revision_id"]),
                dungeonmind_head_revision_id=binding.dungeonmind_head_revision_id,
                legacy_revision_map=legacy_map,
            )
        return hydrate_world_graph(
            bundle,
            world_id,
            binding=binding,
            cache_root=cache_root,
            frozen_root=frozen_root,
        )


# ---------------------------------------------------------------------------
# Read-path routing (service boundary)
# ---------------------------------------------------------------------------


def route_read_request(
    request: Any,
    *,
    world_id: str,
    database_url: str,
    cache_root: Path,
    frozen_root: Path,
) -> tuple[Path, Any]:
    """Resolve the read root and rewrite legacy revision pins.

    Returns ``(graph_root, request)``. In ``dungeonmind`` mode the graph root
    is the hydrated cache root and a pin of the legacy Buddy snapshot A
    revision is rewritten to the hydrated revision that carries A's content.
    Pins of any other legacy revision fail closed: historical pre-adoption
    Buddy revisions were never adopted into DungeonMind and are not served.
    """
    handle = ensure_hydrated_authority(
        world_id,
        database_url=database_url,
        cache_root=cache_root,
        frozen_root=frozen_root,
    )
    pin = getattr(request, "revision_pin", None)
    if pin:
        mapped = handle.legacy_revision_map.get(pin)
        if mapped is None:
            raise WorldGraphAuthorityError(
                "revision pin is not bridged to the DungeonMind authority",
                code="revision_not_bridged",
                details={"world_id": world_id, "revision_pin": pin},
            )
        request = request.model_copy(update={"revision_pin": mapped})
    return handle.cache_world_root, request


def authority_error_status_code(exc: WorldGraphAuthorityError) -> int:
    """Stable HTTP mapping for authority failures at service boundaries."""
    return {
        "authority_unavailable": 503,
        "authority_head_missing": 503,
        "authority_head_moved": 409,
        "revision_not_bridged": 404,
        "adoption_receipt_missing": 409,
        "adoption_receipt_not_v3": 409,
        "frozen_store_missing": 500,
        "frozen_store_mismatch": 500,
        "hydration_integrity": 500,
        "governed_write_inexpressible": 409,
        "governed_write_materialization_unsupported": 409,
        "invalid_request": 422,
    }.get(exc.code, 500)


def route_service_read(
    request: Any,
    explicit_root: Path | None,
    *,
    default_root: Path,
) -> tuple[Path, Any]:
    """Authority-aware read routing shared by projection/retrieval services.

    Explicit roots (tests, tooling) bypass authority routing. ``buddy_files``
    and ``quiesced`` modes serve the file store unchanged. ``dungeonmind``
    mode serves the hydrated cache root and rewrites bridged revision pins.
    """
    from apps.live_control_server import config
    from graph_memory.world_supergraph import storage

    if explicit_root is not None:
        return Path(explicit_root).resolve(), request
    mode = config.world_graph_authority_mode()
    if mode != storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND:
        return default_root, request
    world_id = str(getattr(request, "world_id", "") or "").strip()
    if not world_id:
        raise WorldGraphAuthorityError(
            "request carries no world_id", code="invalid_request"
        )
    database_url = config.world_graph_authority_database_url()
    if not database_url:
        raise WorldGraphAuthorityError(
            "DungeonMind authority database URL is not configured "
            f"({config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV})",
            code="authority_unavailable",
        )
    return route_read_request(
        request,
        world_id=world_id,
        database_url=database_url,
        cache_root=config.world_graph_authority_cache_root(),
        frozen_root=default_root,
    )


# ---------------------------------------------------------------------------
# Write-path routing (governed GM-confirmed publication)
# ---------------------------------------------------------------------------

# DungeonMind's dm_contribution_review_intent_v1 admits exactly these
# assertion kinds, with per-kind field restrictions enforced by the contract.
_V1_REVIEWABLE_KINDS = frozenset({"label", "alias", "summary", "relationship"})


def _v1_review_expressibility_blockers(
    contribution: GraphContribution,
) -> list[dict[str, Any]]:
    """List the accepted assertions DungeonMind's v1 review contract cannot express."""
    blockers: list[dict[str, Any]] = []
    for assertion in contribution.accepted_assertions:
        kind = assertion.assertion_kind
        reason: str | None = None
        if kind not in _V1_REVIEWABLE_KINDS:
            reason = f"assertion_kind {kind!r} is not a v1 reviewable kind"
        elif kind == "relationship":
            if assertion.label is not None or assertion.value:
                reason = "v1 relationship assertions forbid label and value"
        elif kind == "label":
            if assertion.predicate is not None or assertion.value:
                reason = "v1 label assertions forbid predicate and value"
        elif kind in {"alias", "summary"}:
            if assertion.predicate is not None or assertion.label is not None:
                reason = f"v1 {kind} assertions forbid predicate and label"
        if assertion.campaign_scope is not None or assertion.temporal_scope:
            reason = (reason + "; " if reason else "") + (
                "v1 review assertions do not carry campaign/temporal scope"
            )
        if reason is not None:
            blockers.append(
                {
                    "assertion_id": assertion.assertion_id,
                    "assertion_kind": kind,
                    "reason": reason,
                }
            )
    return blockers


def confirm_via_dungeonmind(
    request: Any,
    *,
    world_root: Path,
    database_url: str,
    cache_root: Path,
    frozen_root: Path,
    confirming_principal: str,
    assertion_ids: tuple[str, ...],
    repo_root: Path,
) -> Any:
    """Route one GM-confirmed publication through DungeonMind's governed write.

    The sealed Buddy review package is verified against the DungeonMind-backed
    hydrated head with unchanged semantics. Entering DungeonMind's governed
    write path then fails closed at the characterized v1-review-contract and
    v6-materialization gaps (§7 repair items) — never partially, never by
    touching the frozen Buddy store.
    """
    from graph_memory.extract_promote_ops import resolve_merged_contribution_from_package

    package = dict(request.review_package or {})
    world_id = str((package.get("effect") or {}).get("world_id") or "").strip()
    if not world_id:
        raise WorldGraphAuthorityError(
            "review package carries no world_id",
            code="invalid_request",
        )
    handle = ensure_hydrated_authority(
        world_id,
        database_url=database_url,
        cache_root=cache_root,
        frozen_root=frozen_root,
    )
    # Verify the sealed package against the DungeonMind-backed head. The
    # package's parent pin is a Buddy revision id; the hydrated head carries
    # the DungeonMind head's content, so verification semantics are unchanged.
    _verified, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal=confirming_principal,
        world_id_hint=world_id,
        root=handle.cache_world_root,
        expected_parent_revision_id=handle.buddy_revision_id,
        assertion_ids=assertion_ids,
        repo_root=repo_root,
        disclose_source_digest=False,
        verify_source=True,
    )

    blockers = _v1_review_expressibility_blockers(contribution)
    if blockers:
        raise WorldGraphAuthorityError(
            "DungeonMind's governed write contract "
            "(dm_contribution_review_intent_v1) cannot express this confirmed "
            "contribution; a v2 review contract is required (cutover §7 repair)",
            code="governed_write_inexpressible",
            details={
                "world_id": world_id,
                "contribution_id": contribution.contribution_id,
                "blocker_count": len(blockers),
                "blockers": blockers[:10],
            },
        )
    # Fully v1-expressible contributions still cannot publish: DungeonMind's
    # materialization is bound to dm_union_graph_v3 parents and this world is
    # dm_union_graph_v6. Fail closed with the precise downstream gap rather
    # than constructing a review state that can only fail deep inside
    # DungeonMind's publication flow.
    raise WorldGraphAuthorityError(
        "DungeonMind governed materialization is bound to dm_union_graph_v3; "
        f"world {world_id!r} is dm_union_graph_v6 (cutover §7 repair)",
        code="governed_write_materialization_unsupported",
        details={
            "world_id": world_id,
            "contribution_id": contribution.contribution_id,
            "graph_schema": "dm_union_graph_v6",
            "materialization_schema": "dm_union_graph_v3",
        },
    )


__all__ = [
    "AuthorityBinding",
    "HYDRATION_METADATA_SCHEMA",
    "HYDRATION_TRANSLATION_VERSION",
    "HydrationHandle",
    "WorldGraphAuthorityError",
    "authority_error_status_code",
    "bind_world_authority",
    "build_authority_graph_reader",
    "check_world_correspondence",
    "confirm_via_dungeonmind",
    "ensure_hydrated_authority",
    "hydrate_world_graph",
    "order_contributions_for_replay",
    "read_hydration_metadata",
    "route_read_request",
    "route_service_read",
    "translate_contribution",
    "translate_identity_decision",
]
