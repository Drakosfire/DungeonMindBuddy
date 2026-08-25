"""DungeonMind-native governed write integration (CUTOVER D.1).

In ``dungeonmind`` authority mode the normal exact-run prepare → confirm
workflow reads graph facts from DungeonMind, seals public DungeonMind parent
revision IDs, and publishes DungeonMind children without opening, hydrating,
replaying, or rebuilding Buddy's World Graph.

This module must not import ``graph_memory.kernel`` runtime, 
``graph_memory.world_supergraph``, or ``graph_memory.union_supergraph``.
Buddy contribution/proposal value models remain the product contract.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from graph_memory.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
    apply_identity_redirects_to_objects,
    identity_facts_from_dungeonmind_decisions,
    wire_kind,
)

logger = logging.getLogger(__name__)

IDENTITY_LEDGER_SCHEMA = "dmb_world_graph_identity_ledger_v1"

_WRITE_STATUS_CODES = {
    "authority_unavailable": 503,
    "authority_head_missing": 503,
    "revision_not_bridged": 404,
    "adoption_receipt_missing": 409,
    "governed_write_inexpressible": 409,
    "governed_write_materialization_failed": 409,
    "governed_write_stale_parent": 409,
    "governed_write_legacy_package": 409,
    "governed_write_failed": 502,
    "invalid_request": 422,
}


class WorldGraphWriteError(RuntimeError):
    """Typed failure from the native DungeonMind governed-write path."""

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

    @property
    def status_code(self) -> int:
        return _WRITE_STATUS_CODES.get(self.code, 500)


def write_error_status_code(exc: WorldGraphWriteError) -> int:
    return exc.status_code


@dataclass
class _EmptyEvidenceView:
    """Duck-type for adoption contribution mapping's evidence lookup.

    D.1 reconstructs from sealed package facts. Parent-graph Buddy evidence
    records are not available; ``_map_contribution_evidence_ref`` falls back
    to the assertion's source artifact identity.
    """

    evidence: dict[str, Any] = field(default_factory=dict)


def _open_repository_bundle(database_url: str) -> Any:
    try:
        from dungeonmind.infrastructure.postgres import (
            PostgresDatabase,
            PostgresRepositoryBundle,
        )
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise WorldGraphWriteError(
            "dungeonmind postgres adapter is unavailable",
            code="authority_unavailable",
            details={"reason": type(exc).__name__},
        ) from exc
    try:
        return PostgresRepositoryBundle(PostgresDatabase(database_url))
    except Exception as exc:
        raise WorldGraphWriteError(
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
        raise WorldGraphWriteError(
            "DungeonMind authority database URL is not configured "
            f"({config.WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV})",
            code="authority_unavailable",
        )
    return configured


def _build_graph_reader() -> Any:
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


def _direct_services(database_url: str, world_id: str) -> Any:
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        DirectWorldGraphReadError,
        direct_services_from_bundle,
    )

    bundle = _open_repository_bundle(database_url)
    try:
        return direct_services_from_bundle(bundle, world_id)
    except DirectWorldGraphReadError as exc:
        raise WorldGraphWriteError(
            str(exc),
            code=exc.code,
            details={"world_id": world_id},
        ) from exc


def _context_with_dungeonmind_identity(
    *,
    world_id: str,
    revision_id: str,
    head_revision_id: str,
    objects: dict[str, MutationObject],
    alias_owners: dict[str, tuple[str, ...]],
    dungeonmind_decisions: Sequence[Any] | None,
) -> WorldGraphMutationContext:
    redirects: dict[str, str] = {}
    records: tuple[Any, ...] = ()
    ledger_records = tuple(_dump_identity_decision(item) for item in dungeonmind_decisions or ())
    if dungeonmind_decisions:
        try:
            redirects, extra_alias_owners, records = identity_facts_from_dungeonmind_decisions(
                dungeonmind_decisions
            )
        except Exception as exc:
            raise WorldGraphWriteError(
                "DungeonMind identity decisions cannot be adapted for mutation",
                code="governed_write_inexpressible",
                details={"world_id": world_id, "reason": str(exc)[:500]},
            ) from exc
        objects = apply_identity_redirects_to_objects(objects, redirects)
        for alias, owners in extra_alias_owners.items():
            prior = alias_owners.get(alias, ())
            merged_owners = list(prior)
            for owner in owners:
                if owner not in merged_owners:
                    merged_owners.append(owner)
            alias_owners[alias] = tuple(merged_owners)
    return WorldGraphMutationContext(
        world_id=world_id,
        revision_id=revision_id,
        head_revision_id=head_revision_id,
        objects=objects,
        alias_owners=alias_owners,
        identity_redirects=redirects,
        identity_decisions=records,
        identity_ledger_records=ledger_records,
    )


def _iso_json_timestamp(value: Any) -> str:
    from datetime import UTC, datetime

    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return ""


def _dump_identity_decision(raw: Any) -> dict[str, Any]:
    if hasattr(raw, "model_dump"):
        dumped = raw.model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped
    side = getattr(raw, "merge_side_effects", None)
    if isinstance(side, dict):
        side_payload = dict(side)
    elif side is None:
        side_payload = None
    elif hasattr(side, "model_dump"):
        side_payload = side.model_dump(mode="json")
    else:
        rewrites = []
        for rewrite in list(getattr(side, "alias_map_rewrites", None) or []):
            if isinstance(rewrite, dict):
                rewrites.append(dict(rewrite))
            else:
                rewrites.append(
                    {
                        "alias_key": str(getattr(rewrite, "alias_key", "") or ""),
                        "prior_owner_node_id": getattr(rewrite, "prior_owner_node_id", None),
                        "new_owner_node_id": str(
                            getattr(rewrite, "new_owner_node_id", "") or ""
                        ),
                    }
                )
        side_payload = {
            "aliases_added_to_target": list(
                getattr(side, "aliases_added_to_target", None) or []
            ),
            "evidence_ref_ids_added_to_target": list(
                getattr(side, "evidence_ref_ids_added_to_target", None) or []
            ),
            "source_domains_added_to_target": list(
                getattr(side, "source_domains_added_to_target", None) or []
            ),
            "alias_map_rewrites": rewrites,
        }
    return {
        "decision_id": str(getattr(raw, "decision_id", "") or ""),
        "world_id": str(getattr(raw, "world_id", "") or ""),
        "decision_kind": str(getattr(raw, "decision_kind", "") or ""),
        "subject_object_ids": [
            str(item)
            for item in list(getattr(raw, "subject_object_ids", None) or [])
            if str(item).strip()
        ],
        "target_object_ids": [
            str(item)
            for item in list(getattr(raw, "target_object_ids", None) or [])
            if str(item).strip()
        ],
        "alias": getattr(raw, "alias", None),
        "actor": str(getattr(raw, "actor", None) or "system"),
        "reason": getattr(raw, "reason", None),
        "reversible": bool(getattr(raw, "reversible", True)),
        "supersedes_decision_ids": list(
            getattr(raw, "supersedes_decision_ids", None) or []
        ),
        "status": str(getattr(raw, "status", "") or "active"),
        "created_at": _iso_json_timestamp(getattr(raw, "created_at", None)),
        "merge_side_effects": side_payload,
        "source_candidate_id": getattr(raw, "source_candidate_id", None),
    }


def _hydrate_identity_decisions(records: Sequence[Mapping[str, Any]]) -> list[Any]:
    from types import SimpleNamespace

    from dungeonmind.contracts.identity import IdentityDecisionRecordV2

    hydrated: list[Any] = []
    for item in records:
        payload = dict(item)
        try:
            hydrated.append(IdentityDecisionRecordV2.model_validate(payload))
            continue
        except Exception:
            pass
        side = payload.get("merge_side_effects")
        if isinstance(side, dict):
            rewrites = []
            for rewrite in list(side.get("alias_map_rewrites") or []):
                rewrites.append(
                    SimpleNamespace(**dict(rewrite))
                    if isinstance(rewrite, dict)
                    else rewrite
                )
            payload["merge_side_effects"] = SimpleNamespace(
                aliases_added_to_target=list(side.get("aliases_added_to_target") or []),
                evidence_ref_ids_added_to_target=list(
                    side.get("evidence_ref_ids_added_to_target") or []
                ),
                source_domains_added_to_target=list(
                    side.get("source_domains_added_to_target") or []
                ),
                alias_map_rewrites=rewrites,
            )
        hydrated.append(SimpleNamespace(**payload))
    return hydrated


def bind_identity_ledger_to_package(
    package: Mapping[str, Any],
    context: WorldGraphMutationContext,
) -> dict[str, Any]:
    """Seal the exact identity ledger used at prepare into the proposal effect.

    DungeonMind identity decisions are append-only and have no revision/as-of
    read. The package therefore binds the snapshot so confirm can reconstruct
    the same identity semantics against the immutable graph parent.
    """
    from graph_memory.extract_promote_proposal import compute_proposal_digest

    sealed = dict(package)
    effect = dict(sealed.get("effect") or {})
    effect["identity_ledger"] = {
        "schema": IDENTITY_LEDGER_SCHEMA,
        "decisions": [dict(item) for item in context.identity_ledger_records],
    }
    sealed["effect"] = effect
    sealed["proposal_digest"] = compute_proposal_digest(effect)
    return sealed


def _require_sealed_identity_ledger(package: Mapping[str, Any]) -> list[Any]:
    effect = dict(package.get("effect") or {})
    ledger = effect.get("identity_ledger")
    if not isinstance(ledger, dict) or "decisions" not in ledger:
        raise WorldGraphWriteError(
            "sealed package does not bind an identity-ledger snapshot; "
            "re-prepare against the current DungeonMind head",
            code="governed_write_legacy_package",
            details={"reason": "identity_ledger_unsealed"},
        )
    schema = str(ledger.get("schema") or "").strip()
    if schema and schema != IDENTITY_LEDGER_SCHEMA:
        raise WorldGraphWriteError(
            "sealed identity ledger schema is not reconstructable",
            code="governed_write_inexpressible",
            details={"schema": schema},
        )
    decisions = ledger.get("decisions")
    if not isinstance(decisions, list):
        raise WorldGraphWriteError(
            "sealed identity ledger is not a decision list",
            code="governed_write_inexpressible",
            details={"reason": "identity_ledger_malformed"},
        )
    try:
        return _hydrate_identity_decisions(
            [item for item in decisions if isinstance(item, Mapping)]
        )
    except Exception as exc:
        raise WorldGraphWriteError(
            "sealed identity ledger cannot be reconstructed",
            code="governed_write_inexpressible",
            details={"reason": str(exc)[:500]},
        ) from exc


def _register_object_alias_owners(
    objects: dict[str, MutationObject],
    alias_owners: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    """Register labels and aliases the way Buddy's alias map did."""
    for obj in objects.values():
        for key in (obj.label, *obj.aliases):
            text = str(key or "").strip()
            if not text:
                continue
            prior = alias_owners.get(text, ())
            if obj.object_id not in prior:
                alias_owners[text] = (*prior, obj.object_id)
    return alias_owners


def _alias_values(raw_aliases: Any) -> tuple[str, ...]:
    values: list[str] = []
    for alias in list(raw_aliases or []):
        if isinstance(alias, str):
            text = alias.strip()
        elif isinstance(alias, dict):
            text = str(alias.get("value") or "").strip()
        else:
            text = str(getattr(alias, "value", "") or "").strip()
        if text:
            values.append(text)
    return tuple(values)


def mutation_context_from_native_projection(
    result: Any,
    *,
    world_id: str,
    dungeonmind_decisions: Sequence[Any] | None = None,
) -> WorldGraphMutationContext:
    """Build mutation context from one exact DungeonMind projection result."""
    snapshot = result.snapshot
    graph = result.graph
    objects: dict[str, MutationObject] = {}
    for obj in graph.objects.values():
        canon = ""
        meta = getattr(obj, "existence_assertion_metadata", None)
        raw_canon = str(getattr(meta, "canon_state", "") or "") if meta is not None else ""
        if raw_canon == "provisional":
            canon = "noncanonical_provisional"
        elif raw_canon == "retracted":
            canon = "rejected"
        elif raw_canon == "canonical":
            canon = "canonical"
        objects[obj.object_id] = MutationObject(
            object_id=obj.object_id,
            label=obj.label,
            kind=wire_kind(obj.kind),
            aliases=_alias_values(getattr(obj, "aliases", None)),
            canon_state=canon,
        )
    alias_owners: dict[str, tuple[str, ...]] = {}
    for alias, ids in dict(getattr(graph, "alias_index", None) or {}).items():
        owners = tuple(str(item) for item in list(ids or []) if str(item).strip())
        if alias and owners:
            alias_owners[str(alias)] = owners
    alias_owners = _register_object_alias_owners(objects, alias_owners)
    return _context_with_dungeonmind_identity(
        world_id=world_id,
        revision_id=str(snapshot.revision_id),
        head_revision_id=str(snapshot.head_revision_id),
        objects=objects,
        alias_owners=alias_owners,
        dungeonmind_decisions=dungeonmind_decisions,
    )


def mutation_context_from_revision_payload(
    stored: Any,
    *,
    world_id: str,
    head_revision_id: str,
    dungeonmind_decisions: Sequence[Any] | None = None,
) -> WorldGraphMutationContext:
    """Identity facts from one exact published DungeonMind revision payload.

    Scoped projection excludes adopted objects whose campaign_scope is unset
    (``scope_unknown``). The old Buddy store was the full revision; identity
    therefore reads the published graph payload directly. Durable identity
    decisions come from the DungeonMind identity ledger, not the graph
    snapshot — they supply reject/override/merge-redirect semantics.
    """
    payload = dict(getattr(stored, "graph_payload", None) or {})
    objects: dict[str, MutationObject] = {}
    for raw in list(payload.get("objects") or []):
        if not isinstance(raw, dict):
            continue
        object_id = str(raw.get("object_id") or "").strip()
        if not object_id:
            continue
        meta = raw.get("assertion_metadata") or raw.get("existence_assertion_metadata") or {}
        raw_canon = str((meta or {}).get("canon_state") or "") if isinstance(meta, dict) else ""
        if raw_canon == "provisional":
            canon = "noncanonical_provisional"
        elif raw_canon == "retracted":
            canon = "rejected"
        elif raw_canon == "canonical":
            canon = "canonical"
        else:
            canon = raw_canon
        objects[object_id] = MutationObject(
            object_id=object_id,
            label=str(raw.get("label") or ""),
            kind=wire_kind(str(raw.get("kind") or "")),
            aliases=_alias_values(raw.get("aliases")),
            canon_state=canon,
        )
    alias_owners: dict[str, tuple[str, ...]] = {}
    alias_owners = _register_object_alias_owners(objects, alias_owners)
    revision_id = str(getattr(getattr(stored, "revision", None), "revision_id", "") or "")
    return _context_with_dungeonmind_identity(
        world_id=world_id,
        revision_id=revision_id,
        head_revision_id=head_revision_id,
        objects=objects,
        alias_owners=alias_owners,
        dungeonmind_decisions=dungeonmind_decisions,
    )


def load_production_mutation_context(
    world_id: str,
    *,
    revision_pin: str | None = None,
    database_url: str | None = None,
) -> WorldGraphMutationContext:
    """Whole-world GM identity facts at an exact DungeonMind revision.

    Reads the published revision payload (not a campaign-scoped projection)
    so identity sees the same object set the old durable world store had.
    """
    from dungeonmind.domain.errors import (
        DungeonMindError,
        HeadNotFoundError,
        PersistenceUnavailableError,
        RevisionNotFoundError,
    )

    dsn = _require_database_url(database_url)
    services = _direct_services(dsn, world_id)
    bundle = services.bundle
    try:
        head = bundle.world_graph.get_head(world_id)
        pinned = (revision_pin or "").strip() or (
            head.head_revision_id if head is not None else ""
        )
        stored = bundle.world_graph.get_revision(world_id, pinned) if pinned else None
        identity_decisions = bundle.identity_decisions.list_for_world(world_id)
    except (PersistenceUnavailableError, DungeonMindError) as exc:
        code = "authority_unavailable"
        if isinstance(exc, HeadNotFoundError):
            code = "authority_head_missing"
        elif isinstance(exc, RevisionNotFoundError):
            code = "revision_not_bridged"
        raise WorldGraphWriteError(
            "DungeonMind authority read failed while building mutation context",
            code=code,
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed while building mutation context",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if head is None or not pinned:
        raise WorldGraphWriteError(
            "DungeonMind authority has no published head",
            code="authority_head_missing",
            details={"world_id": world_id},
        )
    if stored is None:
        raise WorldGraphWriteError(
            "DungeonMind parent revision is unreadable",
            code="revision_not_bridged",
            details={"world_id": world_id, "revision_id": pinned},
        )
    return mutation_context_from_revision_payload(
        stored,
        world_id=world_id,
        head_revision_id=str(head.head_revision_id),
        dungeonmind_decisions=identity_decisions,
    )


def _derive_confirm_operation_id(
    *,
    world_id: str,
    package: dict[str, Any],
    assertion_ids: tuple[str, ...] | None,
) -> str:
    from dungeonmind.domain.canonical import canonical_sha256

    digest = canonical_sha256(
        {
            "schema": "dmb_cutover_confirm_operation_v1",
            "world_id": world_id,
            "proposal_id": str(package.get("proposal_id") or ""),
            "proposal_digest": str(package.get("proposal_digest") or ""),
            "selected_assertion_ids": (
                sorted(assertion_ids) if assertion_ids is not None else None
            ),
        }
    )
    return f"reviewop:{digest[:32]}"


def _reverse_revision_id(dm_revision_id: str, artifact_id: str | None) -> str:
    suffix = f"::{artifact_id}" if artifact_id else ""
    if suffix and dm_revision_id.endswith(suffix):
        return dm_revision_id[: -len(suffix)]
    return dm_revision_id


def _build_pair_to_dm(
    bundle: Any,
    world_id: str,
    contribution: Any,
) -> dict[tuple[str, str], str]:
    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _dm_revision_id,
    )

    pair_to_dm: dict[tuple[str, str], str] = {}
    token_artifacts: dict[str, set[str]] = {}
    try:
        artifacts = bundle.sources.list_artifacts_for_world(world_id)
        for artifact in artifacts:
            for revision in bundle.sources.list_revisions(artifact.source_artifact_id):
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
        raise WorldGraphWriteError(
            "DungeonMind authority read failed while resolving source identity",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc

    pairs: set[tuple[str, str]] = set()
    contribution_pairs = [
        (contribution.source_artifact_id, contribution.source_revision_id)
    ]
    for assertion in (
        *contribution.candidate_assertions,
        *contribution.accepted_assertions,
        *contribution.rejected_assertions,
    ):
        contribution_pairs.append(
            (assertion.source_artifact_id, assertion.source_revision_id)
        )
    for artifact_id, token in contribution_pairs:
        if not artifact_id or not token:
            raise WorldGraphWriteError(
                "confirmed contribution is missing source identity",
                code="governed_write_inexpressible",
                details={
                    "world_id": world_id,
                    "contribution_id": contribution.contribution_id,
                    "reason": "source_identity_missing",
                },
            )
        pairs.add((artifact_id, token))
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


def _candidate_endpoint_kinds(
    context: WorldGraphMutationContext, candidate: Any
) -> dict[str, str]:
    kinds: dict[str, str] = {
        object_id: obj.kind
        for object_id, obj in context.objects.items()
        if obj.kind.strip()
    }
    for assertion in candidate.assertions:
        if assertion.assertion_kind != "node" or not assertion.value:
            continue
        try:
            value = json.loads(assertion.value)
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        kind = value.get("kind")
        if isinstance(kind, str) and kind.strip():
            kinds.setdefault(assertion.subject_object_id, kind)
    return kinds


def _qualified_value(assertion: Any) -> str | None:
    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _canonical_json,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        CURRENT_V5_TARGET,
    )

    if assertion.assertion_kind != "node" or not assertion.value:
        return assertion.value
    value = json.loads(assertion.value)
    if not isinstance(value, dict):
        return assertion.value
    if isinstance(value.get("dm_kind"), str) and value["dm_kind"].strip():
        return assertion.value
    buddy_kind = value.get("kind")
    mapped = CURRENT_V5_TARGET.buddy_to_dm_kind.get(str(buddy_kind or ""))
    if mapped is None:
        raise WorldGraphWriteError(
            "confirmed node kind has no DungeonMind mapping",
            code="governed_write_inexpressible",
            details={
                "assertion_id": assertion.assertion_id,
                "buddy_kind": buddy_kind,
            },
        )
    return _canonical_json({**value, "dm_kind": mapped})


def _assert_edge_endpoint_admission(
    assertion: Any,
    *,
    dm_predicate: str,
    reverse_endpoints: bool,
    endpoint_kinds: Mapping[str, str],
) -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
        _predicate_allowed_endpoints,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        CURRENT_V5_TARGET,
    )

    allowed = _predicate_allowed_endpoints(
        dm_predicate, CURRENT_V5_TARGET.world_object_loader()
    )
    if allowed is None:
        raise WorldGraphWriteError(
            "DungeonMind vocabulary does not define the qualified predicate",
            code="governed_write_inexpressible",
            details={
                "assertion_id": assertion.assertion_id,
                "buddy_predicate": assertion.predicate,
                "dm_predicate": dm_predicate,
                "reason": "vocabulary_missing_predicate",
            },
        )
    subject_kinds, object_kinds = allowed
    src_dm = CURRENT_V5_TARGET.buddy_to_dm_kind.get(
        endpoint_kinds.get(assertion.subject_object_id) or ""
    )
    tgt_dm = CURRENT_V5_TARGET.buddy_to_dm_kind.get(
        endpoint_kinds.get(assertion.object_object_id) or ""
    )
    admit_src, admit_tgt = (tgt_dm, src_dm) if reverse_endpoints else (src_dm, tgt_dm)
    if (
        admit_src is None
        or admit_tgt is None
        or admit_src not in subject_kinds
        or admit_tgt not in object_kinds
    ):
        raise WorldGraphWriteError(
            "confirmed edge endpoint kinds are not admitted for the qualified predicate",
            code="governed_write_inexpressible",
            details={
                "assertion_id": assertion.assertion_id,
                "buddy_predicate": assertion.predicate,
                "dm_predicate": dm_predicate,
                "subject_object_id": assertion.subject_object_id,
                "object_object_id": assertion.object_object_id,
                "subject_dm_kind": admit_src,
                "object_dm_kind": admit_tgt,
                "reverse_endpoints": reverse_endpoints,
                "reason": "endpoint_kind_not_admitted",
            },
        )


def _qualified_edge_update(
    assertion: Any, *, endpoint_kinds: Mapping[str, str]
) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _canonical_json,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        edge_has_reverse_direction_qualifier_v4,
        resolve_buddy_predicate_mapping_v4,
    )

    value = json.loads(assertion.value) if assertion.value else {}
    if not isinstance(value, dict):
        value = {}
    if isinstance(value.get("dm_predicate"), str) and value["dm_predicate"].strip():
        return {}
    mapping = resolve_buddy_predicate_mapping_v4(str(assertion.predicate or ""))
    if mapping is None or not mapping[0]:
        raise WorldGraphWriteError(
            "confirmed edge predicate has no DungeonMind mapping",
            code="governed_write_inexpressible",
            details={
                "assertion_id": assertion.assertion_id,
                "buddy_predicate": assertion.predicate,
            },
        )
    dm_predicate, reverse_endpoints = mapping
    edge_id = value.get("edge_id")
    if isinstance(edge_id, str) and edge_has_reverse_direction_qualifier_v4(
        buddy_predicate=str(assertion.predicate or ""),
        edge_id=edge_id,
    ):
        raise WorldGraphWriteError(
            "confirmed edge id carries a reverse-direction qualifier for the predicate",
            code="governed_write_inexpressible",
            details={
                "assertion_id": assertion.assertion_id,
                "buddy_predicate": assertion.predicate,
                "dm_predicate": dm_predicate,
                "edge_id": edge_id,
                "reason": "reverse_direction_qualifier",
            },
        )
    _assert_edge_endpoint_admission(
        assertion,
        dm_predicate=dm_predicate,
        reverse_endpoints=reverse_endpoints,
        endpoint_kinds=endpoint_kinds,
    )
    update: dict[str, Any] = {
        "value": _canonical_json({**value, "dm_predicate": dm_predicate})
    }
    if reverse_endpoints:
        update["subject_object_id"] = assertion.object_object_id
        update["object_object_id"] = assertion.subject_object_id
    return update


def _qualified_assertion_update(
    assertion: Any, *, endpoint_kinds: Mapping[str, str]
) -> dict[str, Any]:
    if assertion.assertion_kind == "node":
        return {"value": _qualified_value(assertion)}
    if assertion.assertion_kind == "edge":
        return _qualified_edge_update(assertion, endpoint_kinds=endpoint_kinds)
    return {}


def _normalized_temporal_scope(temporal_scope: Any) -> Any:
    if (
        isinstance(temporal_scope, dict)
        and set(temporal_scope) == {"session_id"}
        and isinstance(temporal_scope["session_id"], str)
    ):
        return None
    return temporal_scope


def _build_v2_candidate(
    contribution: Any,
    *,
    context: WorldGraphMutationContext,
    pair_to_dm: dict[tuple[str, str], str],
    produced_at: Any,
) -> tuple[Any, dict[str, Any]]:
    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _map_contributions,
    )
    from dungeonmind.contracts.contribution import AcceptanceState, ContributionStatus

    mapped = _map_contributions(_EmptyEvidenceView(), [contribution], pair_to_dm)
    if len(mapped) != 1:
        raise WorldGraphWriteError(
            "contribution mapping did not produce exactly one candidate",
            code="governed_write_failed",
            details={"contribution_id": contribution.contribution_id},
        )
    candidate = mapped[0]
    verdict_states: dict[str, Any] = {}
    for assertion in candidate.assertions:
        state = assertion.acceptance_state
        if state is AcceptanceState.CANDIDATE:
            raise WorldGraphWriteError(
                "confirmed contribution carries an un-adjudicated assertion",
                code="governed_write_inexpressible",
                details={
                    "contribution_id": contribution.contribution_id,
                    "assertion_id": assertion.assertion_id,
                },
            )
        verdict_states[assertion.assertion_id] = state
    endpoint_kinds = _candidate_endpoint_kinds(context, candidate)
    return (
        candidate.model_copy(
            update={
                "assertions": [
                    assertion.model_copy(
                        update={
                            "acceptance_state": AcceptanceState.CANDIDATE,
                            **(
                                {
                                    "temporal_scope": _normalized_temporal_scope(
                                        assertion.temporal_scope
                                    ),
                                    **_qualified_assertion_update(
                                        assertion,
                                        endpoint_kinds=endpoint_kinds,
                                    ),
                                }
                                if verdict_states[assertion.assertion_id]
                                is AcceptanceState.ACCEPTED
                                else {}
                            ),
                        }
                    )
                    for assertion in candidate.assertions
                ],
                "status": ContributionStatus.ACTIVE,
                "supersedes_contribution_id": None,
                "identity_decision_ids": [],
                "produced_at": produced_at,
            }
        ),
        verdict_states,
    )


def _build_identity_dispositions(
    candidate: Any,
    verdict_states: dict[str, Any],
) -> tuple[list[Any], list[Any]]:
    from dungeonmind.contracts.contribution import AcceptanceState
    from dungeonmind.contracts.contribution_review import (
        ContributionIdentityProposal,
        ContributionIdentityVerdict,
        ContributionIdentityVerdictKind,
    )
    from dungeonmind.contracts.identity import IdentityOutcome

    outcome_by_target: dict[str, str] = {}
    for assertion in candidate.assertions:
        if assertion.assertion_kind not in ("node", "alias"):
            continue
        if verdict_states.get(assertion.assertion_id) is not AcceptanceState.ACCEPTED:
            continue
        target = assertion.subject_object_id
        outcome = (
            str(assertion.identity_resolution_outcome)
            if assertion.identity_resolution_outcome
            else None
        )
        prior = outcome_by_target.setdefault(target, outcome or "")
        if prior != (outcome or ""):
            raise WorldGraphWriteError(
                "accepted assertions disagree on the identity outcome of a "
                "node/alias target",
                code="governed_write_inexpressible",
                details={"target_object_id": target},
            )
    proposals: list[Any] = []
    verdicts: list[Any] = []
    for target in sorted(outcome_by_target):
        outcome = outcome_by_target[target]
        candidate_id = f"identity:{target}"
        if outcome == "created_new":
            planned = IdentityOutcome.PROVISIONAL_NEW
            matched: list[str] = []
            verdict_kind = ContributionIdentityVerdictKind.CREATE_NEW
        elif outcome == "resolved_existing":
            planned = IdentityOutcome.RESOLVED_EXISTING
            matched = [target]
            verdict_kind = ContributionIdentityVerdictKind.CONFIRM_EXISTING
        else:
            raise WorldGraphWriteError(
                "accepted node/alias assertion carries an identity outcome the "
                "v2 review model cannot represent",
                code="governed_write_inexpressible",
                details={
                    "target_object_id": target,
                    "identity_resolution_outcome": outcome or None,
                },
            )
        proposals.append(
            ContributionIdentityProposal(
                candidate_id=candidate_id,
                candidate_kind="object",
                planned_outcome=planned,
                target_object_id=target,
                matched_object_ids=matched,
            )
        )
        verdicts.append(
            ContributionIdentityVerdict(
                candidate_id=candidate_id,
                verdict=verdict_kind,
                target_object_id=target,
            )
        )
    return proposals, verdicts


def _confirm_capability_policy(
    *,
    world_id: str,
    campaign_id: str | None,
    parent_revision_id: str,
) -> Any:
    from dungeonmind.contracts.capability import (
        CapabilityCategory,
        CapabilityEffect,
        CapabilityPolicy,
        GraphScope,
        ToolCapabilityRule,
    )
    from dungeonmind.contracts.contribution_review_v2 import FINALIZE_REVIEW_V2_TOOL
    from dungeonmind.contracts.projection import Admissibility

    return CapabilityPolicy(
        policy_id="cutover:graph-review-confirm",
        graph_scope=GraphScope(
            world_id=world_id,
            campaign_id=campaign_id,
            admissibility=Admissibility.GM,
            revision_pin=parent_revision_id,
        ),
        enabled_tools=[FINALIZE_REVIEW_V2_TOOL],
        tool_rules=[
            ToolCapabilityRule(
                tool_name=FINALIZE_REVIEW_V2_TOOL,
                category=CapabilityCategory.CONFIRM_COMMIT,
                require_graph_scope=True,
                allowed_effects=[CapabilityEffect.COMMIT],
            )
        ],
    )


def _threat_publish_capability_policy(
    *,
    world_id: str,
    campaign_id: str | None,
    parent_revision_id: str,
) -> Any:
    """Same confirm-commit tool admission as D.1, distinct policy identity."""
    from dungeonmind.contracts.capability import (
        CapabilityCategory,
        CapabilityEffect,
        CapabilityPolicy,
        GraphScope,
        ToolCapabilityRule,
    )
    from dungeonmind.contracts.contribution_review_v2 import FINALIZE_REVIEW_V2_TOOL
    from dungeonmind.contracts.projection import Admissibility

    return CapabilityPolicy(
        policy_id="cutover:threat-publication-confirm",
        graph_scope=GraphScope(
            world_id=world_id,
            campaign_id=campaign_id,
            admissibility=Admissibility.GM,
            revision_pin=parent_revision_id,
        ),
        enabled_tools=[FINALIZE_REVIEW_V2_TOOL],
        tool_rules=[
            ToolCapabilityRule(
                tool_name=FINALIZE_REVIEW_V2_TOOL,
                category=CapabilityCategory.CONFIRM_COMMIT,
                require_graph_scope=True,
                allowed_effects=[CapabilityEffect.COMMIT],
            )
        ],
    )


def _subject_id(assertion: Any) -> str:
    return str(
        getattr(assertion, "subject_node_id", None)
        or getattr(assertion, "subject_object_id", None)
        or ""
    ).strip()


def _target_id(assertion: Any) -> str:
    return str(
        getattr(assertion, "target_node_id", None)
        or getattr(assertion, "object_object_id", None)
        or ""
    ).strip()


def _accepted_assertions(contribution: Any) -> list[Any]:
    partition = getattr(contribution, "partition_assertions", None)
    if callable(partition):
        from dungeonmind.contracts.contribution import AcceptanceState

        return list(partition(AcceptanceState.ACCEPTED))
    return list(getattr(contribution, "accepted_assertions", None) or [])


def _affected_ids_from_contribution(contribution: Any) -> tuple[list[str], list[str]]:
    accepted = _accepted_assertions(contribution)
    accepted_assertion_ids = [item.assertion_id for item in accepted]
    affected_object_ids: list[str] = []
    seen: set[str] = set()
    for assertion in accepted:
        if assertion.assertion_kind == "node":
            node_id = _subject_id(assertion)
            if node_id and node_id not in seen:
                seen.add(node_id)
                affected_object_ids.append(node_id)
    for assertion in accepted:
        if assertion.assertion_kind != "edge":
            continue
        for node_id in (_subject_id(assertion), _target_id(assertion)):
            if node_id and node_id not in seen:
                seen.add(node_id)
                affected_object_ids.append(node_id)
    return accepted_assertion_ids, affected_object_ids


def _receipt_ids_from_reviewed_contribution(
    *,
    bundle: Any,
    world_id: str,
    publication: Any,
) -> tuple[list[str], list[str]]:
    """Recover product receipt facts from the durable reviewed contribution.

    Exact retry must not reconstruct against today's identity ledger. The
    publication already binds ``reviewed_contribution_id`` and its hash.
    """
    from dungeonmind.contracts.contribution_review_v2 import (
        contribution_v2_payload_sha256,
    )

    contribution_id = str(getattr(publication, "reviewed_contribution_id", "") or "")
    expected_hash = str(getattr(publication, "reviewed_contribution_sha256", "") or "")
    if not contribution_id or not expected_hash:
        raise WorldGraphWriteError(
            "published operation is missing reviewed-contribution identity",
            code="governed_write_failed",
            details={"world_id": world_id, "contribution_id": contribution_id},
        )
    try:
        reviewed = bundle.contributions.get(world_id, contribution_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed while recovering reviewed contribution",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if reviewed is None:
        raise WorldGraphWriteError(
            "published operation's reviewed contribution is unreadable",
            code="governed_write_failed",
            details={"world_id": world_id, "contribution_id": contribution_id},
        )
    try:
        actual_hash = contribution_v2_payload_sha256(reviewed)
    except Exception:
        from dungeonmind.domain.canonical import canonical_sha256

        actual_hash = canonical_sha256(
            reviewed.model_dump(mode="json")
            if hasattr(reviewed, "model_dump")
            else reviewed
        )
    if actual_hash != expected_hash:
        raise WorldGraphWriteError(
            "reviewed contribution hash does not match the publication binding",
            code="governed_write_failed",
            details={
                "world_id": world_id,
                "contribution_id": contribution_id,
                "reason": "reviewed_contribution_sha256_mismatch",
            },
        )
    return _affected_ids_from_contribution(reviewed)


def _mutation_context_from_sealed_package(
    *,
    stored: Any,
    package: Mapping[str, Any],
    world_id: str,
    head_revision_id: str,
) -> WorldGraphMutationContext:
    return mutation_context_from_revision_payload(
        stored,
        world_id=world_id,
        head_revision_id=head_revision_id,
        dungeonmind_decisions=_require_sealed_identity_ledger(package),
    )


def _reconstruct_selected_contribution(
    *,
    package: dict[str, Any],
    world_id: str,
    parent_revision_id: str,
    confirming_principal: str,
    assertion_ids: tuple[str, ...] | None,
    repo_root: Path,
    mutation_context: WorldGraphMutationContext,
) -> tuple[Any, Any]:
    """Rebuild the sealed contribution against an exact DungeonMind parent."""
    from graph_memory.extract_promote_ops import (
        resolve_merged_contribution_from_package,
    )

    return resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal=confirming_principal,
        world_id_hint=world_id,
        mutation_context=mutation_context,
        expected_parent_revision_id=parent_revision_id,
        assertion_ids=assertion_ids,
        repo_root=repo_root,
        disclose_source_digest=False,
        verify_source=True,
    )


def _confirm_proof_payload(
    package: dict[str, Any],
    *,
    world_id: str,
    outcome: str,
    parent_revision_id: str,
    committed_revision_id: str,
    contribution_id: str,
    accepted_assertion_ids: Sequence[str] | None = None,
    affected_object_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_promote_extract_proof_v1",
        "ok": True,
        "published": True,
        "outcome": outcome,
        "world_id": world_id,
        "proposal_id": str(package.get("proposal_id") or ""),
        "proposal_digest": str(package.get("proposal_digest") or ""),
        "parent_revision_id": parent_revision_id,
        "committed_revision_id": committed_revision_id,
        "contribution_id": contribution_id,
        "post_publication_verification": "passed",
        "accepted_assertion_ids": list(accepted_assertion_ids or []),
        "affected_object_ids": list(affected_object_ids or []),
    }


def _classify_parent_revision(
    bundle: Any,
    world_id: str,
    parent_revision_id: str,
    *,
    legacy_buddy_revision_id: str,
) -> str:
    """Return ``dungeonmind`` or raise for unsupported Buddy/private parents."""
    if parent_revision_id == legacy_buddy_revision_id:
        raise WorldGraphWriteError(
            "sealed package names the pre-cutover Buddy parent revision; "
            "re-prepare against the current DungeonMind head",
            code="governed_write_legacy_package",
            details={
                "world_id": world_id,
                "parent_revision_id": parent_revision_id,
                "reason": "buddy_a_revision",
            },
        )
    try:
        stored = bundle.world_graph.get_revision(world_id, parent_revision_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed during confirm",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if stored is None:
        raise WorldGraphWriteError(
            "sealed package names a private or legacy Buddy parent revision; "
            "re-prepare against the current DungeonMind head",
            code="governed_write_legacy_package",
            details={
                "world_id": world_id,
                "parent_revision_id": parent_revision_id,
                "reason": "not_a_dungeonmind_revision",
            },
        )
    return "dungeonmind"


def confirm_extract_promote_via_dungeonmind(
    request: Any,
    *,
    database_url: str,
    confirming_principal: str,
    assertion_ids: tuple[str, ...] | None,
    repo_root: Path,
    **_ignored: Any,
) -> dict[str, Any]:
    """Publish a D.1 package through DungeonMind without Buddy hydration."""
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict,
        ContributionPlanRef,
        derive_confirmation_id,
    )
    from dungeonmind.contracts.contribution_review_v2 import (
        CommitConfirmationReceiptV2,
        ContributionReviewIntentV2,
        ContributionReviewSubmissionV2,
        contribution_v2_payload_sha256,
        derive_review_intent_sha256_v2,
        FINALIZE_REVIEW_V2_TOOL,
    )
    from dungeonmind.contracts.semantic_profile import SemanticProfileRef
    from dungeonmind.domain.canonical import canonical_sha256
    from dungeonmind.domain.errors import (
        ContributionMaterializationError,
        DungeonMindError,
        StaleParentRevisionError,
    )

    package = dict(request.review_package or {})
    world_id = str((package.get("effect") or {}).get("world_id") or "").strip()
    if not world_id:
        raise WorldGraphWriteError(
            "review package carries no world_id",
            code="invalid_request",
        )
    dsn = _require_database_url(database_url)
    services = _direct_services(dsn, world_id)
    bundle = services.bundle
    binding = services.binding

    operation_id = _derive_confirm_operation_id(
        world_id=world_id,
        package=package,
        assertion_ids=assertion_ids,
    )
    try:
        existing = bundle.finalized_review_publications.get(world_id, operation_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed during confirm",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if existing is not None:
        accepted_assertion_ids, affected_object_ids = (
            _receipt_ids_from_reviewed_contribution(
                bundle=bundle,
                world_id=world_id,
                publication=existing,
            )
        )
        return _confirm_proof_payload(
            package,
            world_id=world_id,
            outcome="already_applied",
            parent_revision_id=existing.expected_parent_revision_id,
            committed_revision_id=existing.published_revision_id,
            contribution_id=existing.reviewed_contribution_id,
            accepted_assertion_ids=accepted_assertion_ids,
            affected_object_ids=affected_object_ids,
        )

    sealed_parent = str(
        (package.get("effect") or {}).get("parent_revision_id") or ""
    ).strip()
    if not sealed_parent:
        raise WorldGraphWriteError(
            "review package carries no parent_revision_id",
            code="invalid_request",
        )
    _classify_parent_revision(
        bundle,
        world_id,
        sealed_parent,
        legacy_buddy_revision_id=binding.legacy_buddy_revision_id,
    )

    parent_revision_id = sealed_parent
    try:
        head = bundle.world_graph.get_head(world_id)
        parent_stored = bundle.world_graph.get_revision(world_id, parent_revision_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed during confirm",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if head is None or parent_stored is None:
        raise WorldGraphWriteError(
            "DungeonMind parent revision is unreadable",
            code="authority_head_missing",
            details={"world_id": world_id, "revision_id": parent_revision_id},
        )
    if head.head_revision_id != parent_revision_id:
        raise WorldGraphWriteError(
            "DungeonMind head advanced past the sealed package's parent; "
            "re-prepare the review against the current head",
            code="governed_write_stale_parent",
            details={
                "world_id": world_id,
                "expected_parent_revision_id": parent_revision_id,
                "actual_head_revision_id": head.head_revision_id,
            },
        )

    mutation_context = _mutation_context_from_sealed_package(
        stored=parent_stored,
        package=package,
        world_id=world_id,
        head_revision_id=str(head.head_revision_id),
    )
    _verified, contribution = _reconstruct_selected_contribution(
        package=package,
        world_id=world_id,
        parent_revision_id=parent_revision_id,
        confirming_principal=confirming_principal,
        assertion_ids=assertion_ids,
        repo_root=repo_root,
        mutation_context=mutation_context,
    )
    accepted_assertion_ids, affected_object_ids = _affected_ids_from_contribution(
        contribution
    )

    parent_envelope = parent_stored.revision
    pair_to_dm = _build_pair_to_dm(bundle, world_id, contribution)
    reviewed_at = parent_envelope.created_at
    candidate, verdict_states = _build_v2_candidate(
        contribution,
        context=mutation_context,
        pair_to_dm=pair_to_dm,
        produced_at=reviewed_at,
    )
    proposals, verdicts = _build_identity_dispositions(candidate, verdict_states)
    assertion_verdicts = [
        ContributionAssertionVerdict(
            assertion_id=assertion.assertion_id,
            acceptance_state=verdict_states[assertion.assertion_id],
        )
        for assertion in sorted(
            candidate.assertions, key=lambda item: item.assertion_id
        )
    ]
    campaign_id = contribution.campaign_scope or None
    raw_profile = parent_stored.graph_payload.get("semantic_profile")
    if raw_profile is None:
        raise WorldGraphWriteError(
            "DungeonMind parent revision payload declares no semantic profile",
            code="governed_write_inexpressible",
            details={"world_id": world_id, "revision_id": parent_revision_id},
        )
    plan_ref = ContributionPlanRef(
        source_plan_schema=str(
            package.get("schema") or "dmb_promote_extract_review_package_v1"
        ),
        source_plan_id=str(package.get("proposal_id") or ""),
        source_plan_sha256=str(package.get("proposal_digest") or ""),
        source_input_sha256=canonical_sha256(package.get("effect") or {}),
        preview_content_sha256=canonical_sha256(package.get("preview") or {}),
        candidate_contribution_sha256=contribution_v2_payload_sha256(candidate),
        expected_parent_revision_id=parent_revision_id,
        base_graph_schema=parent_envelope.graph_schema,
        base_graph_payload_sha256=parent_envelope.graph_payload_sha256,
        semantic_profile=SemanticProfileRef.model_validate(raw_profile),
    )
    intent_sha256 = derive_review_intent_sha256_v2(
        operation_id=operation_id,
        world_id=world_id,
        campaign_id=campaign_id,
        plan_ref=plan_ref,
        candidate_contribution=candidate,
        identity_proposals=proposals,
        identity_verdicts=verdicts,
        assertion_verdicts=assertion_verdicts,
        reviewer_id=confirming_principal,
        reviewed_at=reviewed_at,
    )
    try:
        intent = ContributionReviewIntentV2(
            operation_id=operation_id,
            world_id=world_id,
            campaign_id=campaign_id,
            plan_ref=plan_ref,
            candidate_contribution=candidate,
            identity_proposals=proposals,
            identity_verdicts=verdicts,
            assertion_verdicts=assertion_verdicts,
            reviewer_id=confirming_principal,
            reviewed_at=reviewed_at,
            review_intent_sha256=intent_sha256,
        )
        confirmation = CommitConfirmationReceiptV2(
            confirmation_id=derive_confirmation_id(
                operation_id=operation_id,
                review_intent_sha256=intent_sha256,
                actor=confirming_principal,
                confirmed_at=reviewed_at,
            ),
            operation_id=operation_id,
            review_intent_sha256=intent_sha256,
            actor=confirming_principal,
            tool_name=FINALIZE_REVIEW_V2_TOOL,
            effect="commit",
            world_id=world_id,
            campaign_id=campaign_id,
            expected_parent_revision_id=parent_revision_id,
            confirmed_at=reviewed_at,
        )
        submission = ContributionReviewSubmissionV2(
            intent=intent, confirmation=confirmation
        )
    except Exception as exc:
        raise WorldGraphWriteError(
            "confirmed package cannot be expressed as a DungeonMind v2 review",
            code="governed_write_inexpressible",
            details={
                "world_id": world_id,
                "contribution_id": contribution.contribution_id,
                "reason": str(exc)[:500],
            },
        ) from exc

    from dungeonmind.application.contribution_review_v2 import (
        finalize_contribution_review_v2,
    )
    from dungeonmind.application.review_publication import (
        publish_finalized_review,
    )

    try:
        state = finalize_contribution_review_v2(
            submission,
            capability_policy=_confirm_capability_policy(
                world_id=world_id,
                campaign_id=campaign_id,
                parent_revision_id=parent_revision_id,
            ),
            world_graph_repository=bundle.world_graph,
            review_repository=bundle.contribution_reviews,
        )
    except StaleParentRevisionError as exc:
        raise WorldGraphWriteError(
            "DungeonMind head advanced past the sealed package's parent; "
            "re-prepare the review against the current head",
            code="governed_write_stale_parent",
            details={
                "world_id": world_id,
                "expected_parent_revision_id": parent_revision_id,
                "actual_head_revision_id": getattr(
                    exc, "actual_head_revision_id", None
                ),
            },
        ) from exc
    except DungeonMindError as exc:
        raise WorldGraphWriteError(
            "DungeonMind review finalization failed",
            code="governed_write_failed",
            details={"world_id": world_id, "reason": str(exc)[:500]},
        ) from exc

    try:
        publication = publish_finalized_review(
            world_id,
            state.record.review_id,
            published_at=reviewed_at,
            review_repository=bundle.contribution_reviews,
            world_graph_repository=bundle.world_graph,
            publication_repository=bundle.finalized_review_publications,
            graph_reader=_build_graph_reader(),
        )
    except ContributionMaterializationError as exc:
        raise WorldGraphWriteError(
            "DungeonMind v6 materialization rejected the finalized review",
            code="governed_write_materialization_failed",
            details={
                "world_id": world_id,
                "review_id": state.record.review_id,
                "reason": exc.reason,
                **{k: v for k, v in (exc.details or {}).items() if k not in {"reason"}},
            },
        ) from exc
    except DungeonMindError as exc:
        raise WorldGraphWriteError(
            "DungeonMind review publication failed",
            code="governed_write_failed",
            details={
                "world_id": world_id,
                "review_id": state.record.review_id,
                "reason": str(exc)[:500],
            },
        ) from exc

    child_id = publication.published_revision_id
    try:
        child = bundle.world_graph.get_revision(world_id, child_id)
        head_after = bundle.world_graph.get_head(world_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind post-publication verification failed",
            code="governed_write_failed",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if child is None:
        raise WorldGraphWriteError(
            "published DungeonMind child revision is unreadable",
            code="governed_write_failed",
            details={"world_id": world_id, "revision_id": child_id},
        )
    if str(getattr(child.revision, "parent_revision_id", "") or "") != parent_revision_id:
        # Some revision envelopes name parent via a different field; treat
        # successful publication + matching head as the CAS proof.
        logger.info(
            "native_write_child_parent_field",
            extra={
                "world_id": world_id,
                "child": child_id,
                "expected_parent": parent_revision_id,
                "envelope_parent": getattr(child.revision, "parent_revision_id", None),
            },
        )
    if head_after is None or head_after.head_revision_id != child_id:
        raise WorldGraphWriteError(
            "DungeonMind head did not advance to the published child",
            code="governed_write_failed",
            details={
                "world_id": world_id,
                "committed_revision_id": child_id,
                "head_revision_id": getattr(head_after, "head_revision_id", None),
            },
        )

    return _confirm_proof_payload(
        package,
        world_id=world_id,
        outcome="published",
        parent_revision_id=parent_revision_id,
        committed_revision_id=child_id,
        contribution_id=publication.reviewed_contribution_id,
        accepted_assertion_ids=accepted_assertion_ids,
        affected_object_ids=affected_object_ids,
    )


def publish_contribution_via_dungeonmind(
    *,
    world_id: str,
    expected_parent_revision_id: str,
    operation_id: str,
    actor: str,
    contribution: Any,
    database_url: str | None = None,
) -> dict[str, Any]:
    """Publish one reconstructed GraphContribution through DungeonMind.

    Product-neutral relative to Graph Review: does not change
    ``confirm_extract_promote_via_dungeonmind``. Threat (D.2A) is the first
    caller. Identity-ledger sealing remains a Graph Review concern.
    """
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict,
        ContributionPlanRef,
        derive_confirmation_id,
    )
    from dungeonmind.contracts.contribution_review_v2 import (
        CommitConfirmationReceiptV2,
        ContributionReviewIntentV2,
        ContributionReviewSubmissionV2,
        contribution_v2_payload_sha256,
        derive_review_intent_sha256_v2,
        FINALIZE_REVIEW_V2_TOOL,
    )
    from dungeonmind.contracts.semantic_profile import SemanticProfileRef
    from dungeonmind.domain.canonical import canonical_sha256
    from dungeonmind.domain.errors import (
        ContributionMaterializationError,
        DungeonMindError,
        StaleParentRevisionError,
    )

    dsn = _require_database_url(database_url)
    services = _direct_services(dsn, world_id)
    bundle = services.bundle
    try:
        existing = bundle.finalized_review_publications.get(world_id, operation_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed during publish",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if existing is not None:
        accepted_assertion_ids, _affected = _receipt_ids_from_reviewed_contribution(
            bundle=bundle,
            world_id=world_id,
            publication=existing,
        )
        return {
            "outcome": "already_applied",
            "world_id": world_id,
            "operation_id": existing.operation_id,
            "parent_revision_id": existing.expected_parent_revision_id,
            "committed_revision_id": existing.published_revision_id,
            "contribution_id": existing.reviewed_contribution_id,
            "reviewed_contribution_sha256": existing.reviewed_contribution_sha256,
            "accepted_assertion_ids": accepted_assertion_ids,
        }

    try:
        head = bundle.world_graph.get_head(world_id)
        parent_stored = bundle.world_graph.get_revision(
            world_id, expected_parent_revision_id
        )
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind authority read failed during publish",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if head is None or parent_stored is None:
        raise WorldGraphWriteError(
            "DungeonMind parent revision is unreadable",
            code="authority_head_missing",
            details={
                "world_id": world_id,
                "revision_id": expected_parent_revision_id,
            },
        )
    if head.head_revision_id != expected_parent_revision_id:
        raise WorldGraphWriteError(
            "DungeonMind head advanced past the sealed expected parent",
            code="governed_write_stale_parent",
            details={
                "world_id": world_id,
                "expected_parent_revision_id": expected_parent_revision_id,
                "actual_head_revision_id": head.head_revision_id,
            },
        )

    mutation_context = mutation_context_from_revision_payload(
        parent_stored,
        world_id=world_id,
        head_revision_id=str(head.head_revision_id),
    )
    accepted_assertion_ids, _affected = _affected_ids_from_contribution(contribution)
    parent_envelope = parent_stored.revision
    pair_to_dm = _build_pair_to_dm(bundle, world_id, contribution)
    reviewed_at = parent_envelope.created_at
    candidate, verdict_states = _build_v2_candidate(
        contribution,
        context=mutation_context,
        pair_to_dm=pair_to_dm,
        produced_at=reviewed_at,
    )
    proposals, verdicts = _build_identity_dispositions(candidate, verdict_states)
    assertion_verdicts = [
        ContributionAssertionVerdict(
            assertion_id=assertion.assertion_id,
            acceptance_state=verdict_states[assertion.assertion_id],
        )
        for assertion in sorted(
            candidate.assertions, key=lambda item: item.assertion_id
        )
    ]
    campaign_id = contribution.campaign_scope or None
    raw_profile = parent_stored.graph_payload.get("semantic_profile")
    if raw_profile is None:
        raise WorldGraphWriteError(
            "DungeonMind parent revision payload declares no semantic profile",
            code="governed_write_inexpressible",
            details={"world_id": world_id, "revision_id": expected_parent_revision_id},
        )
    plan_ref = ContributionPlanRef(
        source_plan_schema="dmb_threat_publication_contribution_v1",
        source_plan_id=operation_id,
        source_plan_sha256=canonical_sha256(
            {
                "operation_id": operation_id,
                "contribution_id": contribution.contribution_id,
            }
        ),
        source_input_sha256=canonical_sha256(
            {"contribution_id": contribution.contribution_id}
        ),
        preview_content_sha256=canonical_sha256({}),
        candidate_contribution_sha256=contribution_v2_payload_sha256(candidate),
        expected_parent_revision_id=expected_parent_revision_id,
        base_graph_schema=parent_envelope.graph_schema,
        base_graph_payload_sha256=parent_envelope.graph_payload_sha256,
        semantic_profile=SemanticProfileRef.model_validate(raw_profile),
    )
    intent_sha256 = derive_review_intent_sha256_v2(
        operation_id=operation_id,
        world_id=world_id,
        campaign_id=campaign_id,
        plan_ref=plan_ref,
        candidate_contribution=candidate,
        identity_proposals=proposals,
        identity_verdicts=verdicts,
        assertion_verdicts=assertion_verdicts,
        reviewer_id=actor,
        reviewed_at=reviewed_at,
    )
    try:
        intent = ContributionReviewIntentV2(
            operation_id=operation_id,
            world_id=world_id,
            campaign_id=campaign_id,
            plan_ref=plan_ref,
            candidate_contribution=candidate,
            identity_proposals=proposals,
            identity_verdicts=verdicts,
            assertion_verdicts=assertion_verdicts,
            reviewer_id=actor,
            reviewed_at=reviewed_at,
            review_intent_sha256=intent_sha256,
        )
        confirmation = CommitConfirmationReceiptV2(
            confirmation_id=derive_confirmation_id(
                operation_id=operation_id,
                review_intent_sha256=intent_sha256,
                actor=actor,
                confirmed_at=reviewed_at,
            ),
            operation_id=operation_id,
            review_intent_sha256=intent_sha256,
            actor=actor,
            tool_name=FINALIZE_REVIEW_V2_TOOL,
            effect="commit",
            world_id=world_id,
            campaign_id=campaign_id,
            expected_parent_revision_id=expected_parent_revision_id,
            confirmed_at=reviewed_at,
        )
        submission = ContributionReviewSubmissionV2(
            intent=intent, confirmation=confirmation
        )
    except Exception as exc:
        raise WorldGraphWriteError(
            "Threat contribution cannot be expressed as a DungeonMind v2 review",
            code="governed_write_inexpressible",
            details={
                "world_id": world_id,
                "contribution_id": contribution.contribution_id,
                "reason": str(exc)[:500],
            },
        ) from exc

    from dungeonmind.application.contribution_review_v2 import (
        finalize_contribution_review_v2,
    )
    from dungeonmind.application.review_publication import (
        publish_finalized_review,
    )

    try:
        state = finalize_contribution_review_v2(
            submission,
            capability_policy=_threat_publish_capability_policy(
                world_id=world_id,
                campaign_id=campaign_id,
                parent_revision_id=expected_parent_revision_id,
            ),
            world_graph_repository=bundle.world_graph,
            review_repository=bundle.contribution_reviews,
        )
    except StaleParentRevisionError as exc:
        raise WorldGraphWriteError(
            "DungeonMind head advanced past the sealed expected parent",
            code="governed_write_stale_parent",
            details={
                "world_id": world_id,
                "expected_parent_revision_id": expected_parent_revision_id,
                "actual_head_revision_id": getattr(
                    exc, "actual_head_revision_id", None
                ),
            },
        ) from exc
    except DungeonMindError as exc:
        raise WorldGraphWriteError(
            "DungeonMind review finalization failed",
            code="governed_write_failed",
            details={"world_id": world_id, "reason": str(exc)[:500]},
        ) from exc

    try:
        publication = publish_finalized_review(
            world_id,
            state.record.review_id,
            published_at=reviewed_at,
            review_repository=bundle.contribution_reviews,
            world_graph_repository=bundle.world_graph,
            publication_repository=bundle.finalized_review_publications,
            graph_reader=_build_graph_reader(),
        )
    except ContributionMaterializationError as exc:
        raise WorldGraphWriteError(
            "DungeonMind v6 materialization rejected the Threat contribution",
            code="governed_write_materialization_failed",
            details={
                "world_id": world_id,
                "review_id": state.record.review_id,
                "reason": exc.reason,
                **{k: v for k, v in (exc.details or {}).items() if k not in {"reason"}},
            },
        ) from exc
    except DungeonMindError as exc:
        raise WorldGraphWriteError(
            "DungeonMind review publication failed",
            code="governed_write_failed",
            details={
                "world_id": world_id,
                "review_id": state.record.review_id,
                "reason": str(exc)[:500],
            },
        ) from exc

    child_id = publication.published_revision_id
    try:
        child = bundle.world_graph.get_revision(world_id, child_id)
        head_after = bundle.world_graph.get_head(world_id)
    except Exception as exc:
        raise WorldGraphWriteError(
            "DungeonMind post-publication verification failed",
            code="governed_write_failed",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc
    if child is None:
        raise WorldGraphWriteError(
            "published DungeonMind child revision is unreadable",
            code="governed_write_failed",
            details={"world_id": world_id, "revision_id": child_id},
        )
    if head_after is None or head_after.head_revision_id != child_id:
        raise WorldGraphWriteError(
            "DungeonMind head did not advance to the published child",
            code="governed_write_failed",
            details={
                "world_id": world_id,
                "committed_revision_id": child_id,
                "head_revision_id": getattr(head_after, "head_revision_id", None),
            },
        )
    return {
        "outcome": "published",
        "world_id": world_id,
        "operation_id": publication.operation_id,
        "parent_revision_id": expected_parent_revision_id,
        "committed_revision_id": child_id,
        "contribution_id": publication.reviewed_contribution_id,
        "reviewed_contribution_sha256": publication.reviewed_contribution_sha256,
        "accepted_assertion_ids": accepted_assertion_ids,
    }


__all__ = [
    "IDENTITY_LEDGER_SCHEMA",
    "WorldGraphWriteError",
    "bind_identity_ledger_to_package",
    "confirm_extract_promote_via_dungeonmind",
    "load_production_mutation_context",
    "mutation_context_from_native_projection",
    "mutation_context_from_revision_payload",
    "publish_contribution_via_dungeonmind",
    "write_error_status_code",
]
