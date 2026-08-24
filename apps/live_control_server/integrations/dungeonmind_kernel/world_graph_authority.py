"""DungeonMind-backed World Graph authority adapter (CUTOVER remnants).

Production ``dungeonmind`` reads use
``integrations.dungeonmind.world_graph_reads``. Production exact-run
prepare/confirm uses ``integrations.dungeonmind.world_graph_writes``. This
module retains:

- ``buddy_files`` / ``quiesced`` / explicit-root read passthrough;
- adoption receipt binding and correspondence checks;
- DND→Buddy translation helpers used by historical tests;
- a thin ``confirm_via_dungeonmind`` wrapper over the native writer.

Buddy graph hydration/replay is retired. Hydration entry points fail closed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.identity_models import IdentityDecisionRecord
from graph_memory.world_supergraph import paths as world_paths

# v2: published-ancestry-bound post-adoption selection (CAS-losing finalized
# reviews are excluded) + exact adopted-membership verification at hydration.
# v1 caches predate those semantics and are never served.
HYDRATION_TRANSLATION_VERSION = "cutover-hydration-v2"
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
    """The verified adoption binding between Buddy snapshot A and DungeonMind.

    ``membership_sha256`` is the *served* adopted-membership checkpoint:
    V3 ``membership_sha256`` (M0) or V4 ``effective_membership_sha256`` (M1).
    ``membership_manifest`` is the exact V4 adopted-member selector; it is
    ``None`` for V3, which keeps frozen-store membership selection.
    """

    world_id: str
    adoption_id: str
    membership_sha256: str
    legacy_buddy_revision_id: str  # A — the adopted pre-switch Buddy head
    dungeonmind_first_revision_id: str  # D_A — the adoption-published revision
    dungeonmind_head_revision_id: str  # current DungeonMind head (>= D_A)
    graph_schema: str
    source_artifact_count: int
    source_revision_count: int
    contribution_count: int
    identity_decision_count: int
    membership_manifest: Any | None = None


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

    Fail-closed: no receipt, an unsupported receipt schema, a missing head, or
    a frozen store whose head is not the adopted snapshot all raise. V3 and V4
    are the only accepted typed contracts; attribute presence is not a
    discriminator. A wrong frozen store can never be silently treated as the
    adopted snapshot.
    """
    from dungeonmind.contracts.existing_world_adoption import (
        ExistingWorldAdoptionReceiptV3,
        ExistingWorldAdoptionReceiptV4,
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
    # V4 subclasses V3; check the repaired contract first so M1/manifest bind.
    if isinstance(receipt, ExistingWorldAdoptionReceiptV4):
        served_checkpoint = receipt.effective_membership_sha256
        membership_manifest = receipt.membership_manifest
    elif isinstance(receipt, ExistingWorldAdoptionReceiptV3):
        served_checkpoint = receipt.membership_sha256
        membership_manifest = None
    else:
        raise WorldGraphAuthorityError(
            f"world {world_id!r} adoption receipt is not a V3 or V4 "
            "membership receipt",
            code="adoption_receipt_not_v3",
            details={
                "world_id": world_id,
                "schema": getattr(receipt, "schema_version", type(receipt).__name__),
            },
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
        membership_sha256=served_checkpoint,
        legacy_buddy_revision_id=adopted_source,
        dungeonmind_first_revision_id=receipt.published_revision_id,
        dungeonmind_head_revision_id=head.head_revision_id,
        graph_schema=receipt.graph_schema,
        source_artifact_count=receipt.source_artifact_count,
        source_revision_count=receipt.source_revision_count,
        contribution_count=receipt.contribution_count,
        identity_decision_count=receipt.identity_decision_count,
        membership_manifest=membership_manifest,
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
# Adopted-membership integrity (V3/V4 receipt enforcement at serve time)
# ---------------------------------------------------------------------------


def _adopted_source_identity(
    adopted_contributions: list[Any],
) -> tuple[set[str], set[str]]:
    """Reconstruct the adopted source artifact/revision id sets.

    The adoption minted exactly one source artifact/revision pair per
    (artifact, revision) identity referenced by the adopted contributions and
    their assertions/evidence (the bundle producer's ref collection). The DND
    records already carry the minted DungeonMind revision ids, so the adopted
    set is read back directly — no Buddy-side collision replay is needed.
    """
    artifact_ids: set[str] = set()
    revision_ids: set[str] = set()
    for contribution in adopted_contributions:
        if contribution.source_artifact_id:
            artifact_ids.add(contribution.source_artifact_id)
        if contribution.source_revision_id:
            revision_ids.add(contribution.source_revision_id)
        for assertion in contribution.assertions:
            if assertion.source_artifact_id:
                artifact_ids.add(assertion.source_artifact_id)
            if assertion.source_revision_id:
                revision_ids.add(assertion.source_revision_id)
            for evidence in assertion.evidence_refs or []:
                if evidence.source_artifact_id:
                    artifact_ids.add(evidence.source_artifact_id)
                if evidence.source_revision_id:
                    revision_ids.add(evidence.source_revision_id)
    return artifact_ids, revision_ids


def _verify_adopted_membership(
    bundle: Any,
    world_id: str,
    *,
    binding: AuthorityBinding,
    frozen_root: Path,
) -> None:
    """Recompute the exact adopted membership and fail closed on any drift.

    V3 keeps frozen-store adopted-id selection and compares the digest to the
    V3 ``membership_sha256``. V4 selects exactly the receipt manifest IDs and
    compares the digest to the served ``effective_membership_sha256`` (M1).
    Post-adoption descendants are not members: V3 ignores them because they
    are absent from the frozen store; V4 ignores them because they are absent
    from the manifest. Frozen Buddy data never overrides a V4 manifest.
    """
    from dungeonmind.domain.existing_world_membership import (
        existing_world_adoption_membership_sha256,
    )
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
    )
    from graph_memory.world_supergraph.identity_decision_store import (
        load_identity_decision_index,
    )

    manifest = binding.membership_manifest
    if manifest is not None:
        adopted_contribution_ids = set(manifest.contribution_ids)
        adopted_decision_ids = set(manifest.identity_decision_ids)
        adopted_artifact_ids = set(manifest.source_artifact_ids)
        adopted_revision_ids = set(manifest.source_revision_ids)
    else:
        adopted_contribution_ids = set(
            load_contribution_index(frozen_root, world_id).all_contribution_ids
        )
        adopted_decision_ids = set(
            load_identity_decision_index(frozen_root, world_id).all_decision_ids
        )
        adopted_artifact_ids = set()
        adopted_revision_ids = set()

    try:
        all_contributions = bundle.contributions.list_for_world(world_id)
        all_decisions = bundle.identity_decisions.list_for_world(world_id)
        all_artifacts = bundle.sources.list_artifacts_for_world(world_id)
    except Exception as exc:
        raise WorldGraphAuthorityError(
            "DungeonMind authority read failed during membership verification",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc

    contributions = [
        c for c in all_contributions if c.contribution_id in adopted_contribution_ids
    ]
    decisions = [d for d in all_decisions if d.decision_id in adopted_decision_ids]
    if manifest is None:
        adopted_artifact_ids, adopted_revision_ids = _adopted_source_identity(
            contributions
        )
    artifacts = [
        a for a in all_artifacts if a.source_artifact_id in adopted_artifact_ids
    ]
    revisions: list[Any] = []
    try:
        for artifact_id in sorted(adopted_artifact_ids):
            revisions.extend(
                revision
                for revision in bundle.sources.list_revisions(artifact_id)
                if revision.source_revision_id in adopted_revision_ids
            )
    except Exception as exc:
        raise WorldGraphAuthorityError(
            "DungeonMind authority read failed during membership verification",
            code="authority_unavailable",
            details={"world_id": world_id, "reason": type(exc).__name__},
        ) from exc

    if manifest is not None:
        observed_ids = {
            "source_artifacts": {a.source_artifact_id for a in artifacts},
            "source_revisions": {r.source_revision_id for r in revisions},
            "contributions": {c.contribution_id for c in contributions},
            "identity_decisions": {d.decision_id for d in decisions},
        }
        expected_ids = {
            "source_artifacts": adopted_artifact_ids,
            "source_revisions": adopted_revision_ids,
            "contributions": adopted_contribution_ids,
            "identity_decisions": adopted_decision_ids,
        }
        if observed_ids != expected_ids:
            raise WorldGraphAuthorityError(
                "adopted DungeonMind membership is incomplete",
                code="adopted_membership_incomplete",
                details={
                    "world_id": world_id,
                    "adoption_id": binding.adoption_id,
                    "expected_counts": {
                        family: len(ids) for family, ids in expected_ids.items()
                    },
                    "observed_counts": {
                        family: len(ids) for family, ids in observed_ids.items()
                    },
                },
            )

    observed_counts = {
        "source_artifacts": len(artifacts),
        "source_revisions": len(revisions),
        "contributions": len(contributions),
        "identity_decisions": len(decisions),
    }
    expected_counts = {
        "source_artifacts": binding.source_artifact_count,
        "source_revisions": binding.source_revision_count,
        "contributions": binding.contribution_count,
        "identity_decisions": binding.identity_decision_count,
    }
    if observed_counts != expected_counts:
        raise WorldGraphAuthorityError(
            "adopted DungeonMind membership is incomplete",
            code="adopted_membership_incomplete",
            details={
                "world_id": world_id,
                "adoption_id": binding.adoption_id,
                "expected_counts": expected_counts,
                "observed_counts": observed_counts,
            },
        )

    digest = existing_world_adoption_membership_sha256(
        source_artifacts=artifacts,
        source_revisions=revisions,
        contributions=contributions,
        identity_decisions=decisions,
    )
    if digest != binding.membership_sha256:
        checkpoint_label = (
            "V4 effective membership checkpoint"
            if manifest is not None
            else "V3 receipt"
        )
        raise WorldGraphAuthorityError(
            f"adopted DungeonMind membership does not match the {checkpoint_label}",
            code="adopted_membership_mismatch",
            details={
                "world_id": world_id,
                "adoption_id": binding.adoption_id,
                "expected_membership_sha256": binding.membership_sha256,
                "observed_membership_sha256": digest,
            },
        )


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


def _strip_derived_dm_kind(value: dict[str, Any]) -> dict[str, Any]:
    """Remove a ``dm_kind`` key that is derivable from the Buddy ``kind``.

    The Buddy→v2 confirm-path mapping injects ``dm_kind`` (the v6
    materializer requires the qualified kind for new objects). The key is a
    pure function of the Buddy ``kind``; stripping it recovers the original
    Buddy value so the content-addressed assertion id recomputes exactly —
    the same recovery pattern as the forward map's visibility collapse. A
    ``dm_kind`` that is NOT the derived value is preserved (and the id match
    fails closed if no candidate reproduces it).
    """
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        CURRENT_V5_TARGET,
    )

    dm_kind = value.get("dm_kind")
    if not isinstance(dm_kind, str):
        return value
    mapped = CURRENT_V5_TARGET.buddy_to_dm_kind.get(str(value.get("kind") or ""))
    if mapped is None or mapped != dm_kind:
        return value
    return {key: item for key, item in value.items() if key != "dm_kind"}


def _strip_derived_dm_predicate(
    assertion: Any, value: dict[str, Any]
) -> tuple[dict[str, Any], str | None, str | None]:
    """Recover the Buddy edge value and endpoints from a qualified assertion.

    The confirm-path forward mapping injects ``dm_predicate`` (the v6
    materializer requires the qualified predicate) and swaps the endpoints of
    reverse-mapped predicates (``belongs_to`` → ``dnd5e:owns``). Both are
    pure functions of the Buddy ``predicate``; reversing them recovers the
    original Buddy value and orientation so the content-addressed assertion
    id recomputes exactly — the same recovery pattern as ``dm_kind``. A
    ``dm_predicate`` that is NOT the derived value is preserved (and the id
    match fails closed if no candidate reproduces it).
    """
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        resolve_buddy_predicate_mapping_v4,
    )

    subject = assertion.subject_object_id
    target = assertion.object_object_id
    if assertion.assertion_kind != "edge":
        return value, subject, target
    dm_predicate = value.get("dm_predicate")
    if not isinstance(dm_predicate, str) or not dm_predicate.strip():
        return value, subject, target
    mapping = resolve_buddy_predicate_mapping_v4(str(assertion.predicate or ""))
    if mapping is None or mapping[0] != dm_predicate:
        return value, subject, target
    stripped = {key: item for key, item in value.items() if key != "dm_predicate"}
    if mapping[1]:
        return stripped, target, subject
    return stripped, subject, target


def _temporal_scope_candidates(temporal_scope: Any, value: dict[str, Any]) -> list[Any]:
    """Content-address candidates for the Buddy temporal scope.

    The confirm-path forward mapping normalizes Buddy's real-world-session
    hint (``{"session_id": ...}``) to ``None`` — DungeonMind carries that
    provenance as session refs, never as temporal scope. When the stored
    scope is ``None`` and the value carries exactly one ``session_ids``
    entry, the hint is reconstructed so the content-addressed assertion id
    recomputes exactly. Buddy's producer only ever pairs a single
    ``session_ids`` entry with the hint, so the reconstruction is
    unambiguous; anything else fails closed on the id match.
    """
    candidates = [temporal_scope]
    if temporal_scope is None:
        session_ids = value.get("session_ids")
        if (
            isinstance(session_ids, list)
            and len(session_ids) == 1
            and isinstance(session_ids[0], str)
            and session_ids[0].strip()
        ):
            candidates.append({"session_id": session_ids[0]})
    return candidates


def _translate_assertion(
    assertion: Any,
    epistemic_history: dict[str, str | None],
    contribution_id: str,
) -> dict[str, Any]:
    """Translate one v2 assertion back to Buddy's kernel assertion shape.

    The forward map collapsed visibility ``None``/``"gm"`` to ``gm`` and
    normalized Buddy's real-world-session temporal hint to ``None``. The
    originals are recovered by content-addressed id match: exactly one
    candidate reproduces the recorded assertion id (proven 1838/1838 on
    Eldyrwild).
    """
    from graph_memory.kernel.contributions import compute_assertion_id

    assertion_id = assertion.assertion_id
    if assertion_id in epistemic_history:
        epistemic = epistemic_history[assertion_id]
    else:
        epistemic = _REVERSE_EPISTEMIC.get(str(assertion.epistemic_kind or ""), None)
    value, subject_id, target_id = _strip_derived_dm_predicate(
        assertion,
        _strip_derived_dm_kind(json.loads(assertion.value) if assertion.value else {}),
    )
    visibility: str | None = None
    temporal_scope: Any = None
    matched = False
    for temporal_candidate in _temporal_scope_candidates(
        assertion.temporal_scope, value
    ):
        for candidate in (None, "gm", "player"):
            computed = compute_assertion_id(
                assertion_kind=assertion.assertion_kind,
                subject_node_id=subject_id,
                target_node_id=target_id,
                predicate=assertion.predicate,
                label=assertion.label,
                value=value,
                campaign_scope=assertion.campaign_scope,
                temporal_scope=temporal_candidate,
                epistemic_kind=epistemic,
                visibility=candidate,
            )
            if computed == assertion_id:
                temporal_scope = temporal_candidate
                visibility = candidate
                matched = True
                break
        if matched:
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
        "subject_node_id": subject_id,
        "target_node_id": target_id,
        "predicate": assertion.predicate,
        "label": assertion.label,
        "value": value,
        "evidence_ref_ids": [
            _raw_evidence_id(ev.evidence_ref_id) for ev in assertion.evidence_refs
        ],
        "source_artifact_id": assertion.source_artifact_id,
        "source_revision_id": (
            _reverse_revision_id(
                assertion.source_revision_id, assertion.source_artifact_id
            )
            if assertion.source_revision_id
            else None
        ),
        "campaign_scope": assertion.campaign_scope,
        "temporal_scope": temporal_scope,
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


def _buddy_contribution_id(dm_contribution_id: str) -> str:
    """Map a DungeonMind contribution id to Buddy's path-safe vocabulary.

    Adopted contributions carry Buddy's own ``contribution:<16 hex>`` ids and
    pass through unchanged. Post-adoption reviewed contributions are named by
    DungeonMind's finalize service as ``contrib:<32 hex>`` (derived from the
    review id); the cache ledger is Buddy path-safety checked, so the id is
    re-vocabularied to ``contribution:<same 32 hex>`` — deterministic, and
    length-disjoint from the adopted 16-hex ids. Anything else fails closed.
    """
    if dm_contribution_id.startswith("contrib:"):
        hexpart = dm_contribution_id.removeprefix("contrib:")
        if len(hexpart) == 32 and all(c in "0123456789abcdef" for c in hexpart):
            return f"contribution:{hexpart}"
    if dm_contribution_id.startswith("contribution:"):
        return dm_contribution_id
    raise WorldGraphAuthorityError(
        "DungeonMind contribution id cannot be represented in the Buddy cache",
        code="hydration_integrity",
        details={"contribution_id": dm_contribution_id},
    )


def translate_contribution(record: Any) -> GraphContribution:
    """Translate one DungeonMind durable contribution to Buddy's kernel shape."""
    diagnostics = record.diagnostics or {}
    epistemic_history = diagnostics.get("buddy_assertion_epistemic") or {}
    buddy_diagnostics = diagnostics.get("buddy_diagnostics") or []
    contribution_id = _buddy_contribution_id(record.contribution_id)
    assertions = [
        _translate_assertion(a, epistemic_history, contribution_id)
        for a in record.assertions
    ]
    return GraphContribution.model_validate(
        {
            "contribution_id": contribution_id,
            "world_id": record.world_id,
            "source_kind": _REVERSE_SOURCE_KIND[str(record.source_kind)],
            "source_artifact_id": record.source_artifact_id,
            "source_revision_id": (
                _reverse_revision_id(
                    record.source_revision_id, record.source_artifact_id
                )
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
    lineage_contribution_ids: list[str] | tuple[str, ...] = (),
) -> list[GraphContribution]:
    """Order the translated ledger for Buddy's replay engine.

    Adopted contributions replay in the sealed manifest order recovered from
    the frozen pre-switch store (Buddy's historical merge order; DungeonMind's
    ledger is id-ordered and carries no replay order). Post-adoption
    contributions replay in the exact published-ancestry order supplied as
    ``lineage_contribution_ids`` (the CAS-winning review chain from D_A to the
    selected DungeonMind revision). Remaining rows — adopted contributions
    whose status excludes them from the active replay manifest — append in
    deterministic order; they are written to the cache ledger for status truth
    but never replayed. Unknown lineage ids fail closed.
    """
    by_id = {c.contribution_id: c for c in contributions}
    sealed_present = [cid for cid in sealed_manifest_ids if cid in by_id]
    ordered_ids = set(sealed_present) | set(lineage_contribution_ids)
    lineage: list[GraphContribution] = []
    for cid in lineage_contribution_ids:
        if cid not in by_id:
            raise WorldGraphAuthorityError(
                "published lineage contribution is missing from the translated set",
                code="hydration_integrity",
                details={"contribution_id": cid},
            )
        lineage.append(by_id[cid])
    remainder = sorted(
        (c for c in contributions if c.contribution_id not in ordered_ids),
        key=lambda c: (_parse_utc(c.produced_at), c.contribution_id),
    )
    return [by_id[cid] for cid in sealed_present] + lineage + remainder


# ---------------------------------------------------------------------------
# Hydration (retired — CUTOVER D.1)
# ---------------------------------------------------------------------------
# Production dungeonmind prepare/confirm and production reads no longer
# reconstruct DungeonMind into a Buddy UnionSupergraphStore. The functions
# below fail closed so leftover callers and explosion monkeypatches keep a
# stable import surface. Replay/cache implementation is gone.

HYDRATION_RETIRED_MESSAGE = (
    "Buddy graph hydration is retired (CUTOVER D.1); dungeonmind production "
    "reads and governed writes use DungeonMind-native services"
)


@dataclass(frozen=True)
class HydrationHandle:
    """Retired handle. Construction is not a supported production API."""

    world_id: str
    cache_world_root: Path
    buddy_revision_id: str
    selected_revision_id: str
    head_revision_id: str


def read_hydration_metadata(cache_dir: Path) -> dict[str, Any] | None:
    return None


def hydrate_world_graph(*_args: Any, **_kwargs: Any) -> HydrationHandle:
    raise WorldGraphAuthorityError(
        HYDRATION_RETIRED_MESSAGE, code="authority_unavailable"
    )


def _ensure_hydrated_revision(*_args: Any, **_kwargs: Any) -> HydrationHandle:
    raise WorldGraphAuthorityError(
        HYDRATION_RETIRED_MESSAGE, code="authority_unavailable"
    )


def ensure_hydrated_authority(*_args: Any, **_kwargs: Any) -> HydrationHandle:
    raise WorldGraphAuthorityError(
        HYDRATION_RETIRED_MESSAGE, code="authority_unavailable"
    )


# ---------------------------------------------------------------------------
# Read-path routing (service boundary)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorityReadRoute:
    """The routed read: private graph root plus public DungeonMind identity.

    ``public_revision_id`` / ``public_head_revision_id`` are ``None`` whenever
    the read was not DungeonMind-routed (buddy_files/quiesced modes, explicit
    non-production roots); services then serve the kernel response unchanged.
    """

    graph_root: Path
    request: Any
    public_revision_id: str | None
    public_head_revision_id: str | None


def route_read_request(
    request: Any,
    *,
    world_id: str,
    database_url: str,
    cache_root: Path,
    frozen_root: Path,
) -> AuthorityReadRoute:
    """Retired hydration router.

    Production ``dungeonmind`` reads use the native DungeonMind adapter.
    Calling this function fails closed; it never opens Buddy's World Graph.
    """
    raise WorldGraphAuthorityError(
        HYDRATION_RETIRED_MESSAGE,
        code="authority_unavailable",
        details={"world_id": world_id},
    )


def authority_error_status_code(exc: WorldGraphAuthorityError) -> int:
    """Stable HTTP mapping for authority failures at service boundaries."""
    return {
        "authority_unavailable": 503,
        "authority_head_missing": 503,
        "authority_head_moved": 409,
        "revision_not_bridged": 404,
        "adoption_receipt_missing": 409,
        "adoption_receipt_not_v3": 409,
        "adopted_membership_incomplete": 409,
        "adopted_membership_mismatch": 409,
        "frozen_store_missing": 500,
        "frozen_store_mismatch": 500,
        "hydration_integrity": 500,
        "governed_write_inexpressible": 409,
        "governed_write_materialization_failed": 409,
        "governed_write_stale_parent": 409,
        "governed_write_legacy_package": 409,
        "governed_write_failed": 502,
        "invalid_request": 422,
    }.get(exc.code, 500)


def route_service_read(
    request: Any,
    explicit_root: Path | None,
    *,
    default_root: Path,
) -> AuthorityReadRoute:
    """Authority-aware read routing shared by projection/retrieval services.

    Explicit roots that are genuinely different from the configured production
    World Graph root (tests, tooling) bypass authority routing. In
    ``dungeonmind`` mode the configured production root is **not** an
    authority override: a mounted caller that passes ``world_graph_root()``
    explicitly is routed to DungeonMind exactly like a rootless call.
    ``buddy_files`` and ``quiesced`` modes serve the file store unchanged.
    """
    from apps.live_control_server import config
    from graph_memory.world_supergraph import storage

    mode = config.world_graph_authority_mode()
    if explicit_root is not None:
        resolved = Path(explicit_root).resolve()
        if (
            mode == storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
            and resolved == Path(config.world_graph_root()).resolve()
        ):
            # Mounted production callers hand the configured root down
            # explicitly; that is not a test/tool override.
            pass
        else:
            return AuthorityReadRoute(
                graph_root=resolved,
                request=request,
                public_revision_id=None,
                public_head_revision_id=None,
            )
    if mode != storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND:
        return AuthorityReadRoute(
            graph_root=default_root,
            request=request,
            public_revision_id=None,
            public_head_revision_id=None,
        )
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
    raise WorldGraphAuthorityError(
        HYDRATION_RETIRED_MESSAGE,
        code="authority_unavailable",
        details={"world_id": world_id},
    )


# ---------------------------------------------------------------------------
# Write-path routing (governed GM-confirmed publication)
# ---------------------------------------------------------------------------


def _derive_confirm_operation_id(
    *,
    world_id: str,
    package: dict[str, Any],
    assertion_ids: tuple[str, ...] | None,
) -> str:
    """Deterministic operation identity for one logical Buddy confirmation.

    Same sealed package + same assertion selection ⇒ same operation id ⇒ an
    exact retry finds the durable publication and returns it without
    re-verifying against a head that has legitimately advanced. The sealed
    package pins the Buddy parent revision, which determines the intended
    DungeonMind parent, so the package digest alone commits the operation to
    its parent. ``None`` selection names the full sealed set.
    """
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


def _build_pair_to_dm(
    bundle: Any,
    world_id: str,
    contribution: GraphContribution,
) -> dict[tuple[str, str], str]:
    """Map the contribution's (artifact, Buddy revision) pairs to DND ids.

    Adopted pairs resolve to the exact DungeonMind source revision ids minted
    at adoption. New pairs are minted with the producer's collision rule
    (``_dm_revision_id``: bare Buddy token unless the token is bound to a
    different artifact, then ``token::artifact``), computed over existing
    DungeonMind usage ∪ this contribution's pairs so the mapping matches the
    sealed adoption producer's vocabulary exactly.
    """
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
        raise WorldGraphAuthorityError(
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
            raise WorldGraphAuthorityError(
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


def _build_v2_candidate(
    contribution: GraphContribution,
    *,
    store: Any,
    pair_to_dm: dict[tuple[str, str], str],
    produced_at: Any,
) -> tuple[Any, dict[str, Any]]:
    """Translate the merged Buddy contribution to a reviewable v2 candidate.

    Reuses the sealed adoption producer's per-assertion forward mapping (the
    grounding vocabulary), then normalizes to the review model: every
    assertion becomes a CANDIDATE (the review verdicts carry the accept
    decisions), status ACTIVE, no supersession, no identity decision ids, and
    each accepted assertion's Buddy real-world-session temporal hint is
    normalized away (DungeonMind carries that provenance as session refs,
    never as temporal scope). The produced_at is the deterministic
    parent-revision timestamp so the same logical confirmation derives the
    same candidate digest.

    Returns the candidate plus the GM's adjudication partition: a mapping of
    assertion id to the acceptance state Buddy's identity gate and selection
    already decided (accepted vs rejected). The caller turns those states
    into the review's assertion verdicts, so DungeonMind's durable review
    history never claims approval for an assertion Buddy rejected. An
    un-adjudicated (CANDIDATE) mapped assertion cannot be honestly reviewed
    here and fails closed.

    DungeonMind qualification (``dm_kind``/``dm_predicate`` injection, the
    reverse-direction audit, and the world-object-v5 endpoint admission
    check) applies only to assertions the GM accepted: the v6 materializer
    skips every non-accepted assertion, so a rejected assertion is preserved
    in the durable review record exactly as adjudicated and must not be
    required to be materializable — a rejected assertion with an unmapped
    kind/predicate or inadmitted endpoints cannot veto the publication of the
    accepted assertions alongside it. The session-hint normalization is
    accept-only for the same reason: only accepted assertions materialize,
    so only they need the DungeonMind-shaped temporal scope; a rejected
    assertion keeps its Buddy temporal hint verbatim in the review record.
    """
    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _map_contributions,
    )
    from dungeonmind.contracts.contribution import AcceptanceState, ContributionStatus

    mapped = _map_contributions(store, [contribution], pair_to_dm)
    if len(mapped) != 1:
        raise WorldGraphAuthorityError(
            "contribution mapping did not produce exactly one candidate",
            code="governed_write_failed",
            details={"contribution_id": contribution.contribution_id},
        )
    candidate = mapped[0]
    verdict_states: dict[str, Any] = {}
    for assertion in candidate.assertions:
        state = assertion.acceptance_state
        if state is AcceptanceState.CANDIDATE:
            raise WorldGraphAuthorityError(
                "confirmed contribution carries an un-adjudicated assertion",
                code="governed_write_inexpressible",
                details={
                    "contribution_id": contribution.contribution_id,
                    "assertion_id": assertion.assertion_id,
                },
            )
        verdict_states[assertion.assertion_id] = state
    endpoint_kinds = _candidate_endpoint_kinds(store, candidate)
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


def _candidate_endpoint_kinds(store: Any, candidate: Any) -> dict[str, str]:
    """Buddy kind per node id visible to the confirmation.

    Endpoint admission for accepted edges is checked against the graph state
    the publication produces: pre-existing nodes come from the hydrated head
    store (the durable kind is authoritative), and the candidate's own node
    assertions contribute the kinds of nodes first materializing alongside
    the edges that reference them.
    """
    kinds: dict[str, str] = {}
    for node_id, node in getattr(store, "nodes", {}).items():
        kind = getattr(node, "kind", None)
        if isinstance(kind, str) and kind.strip():
            kinds[node_id] = kind
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


def _qualified_assertion_update(
    assertion: Any, *, endpoint_kinds: Mapping[str, str]
) -> dict[str, Any]:
    """Per-kind DungeonMind qualification for one mapped candidate assertion."""
    if assertion.assertion_kind == "node":
        return {"value": _qualified_value(assertion)}
    if assertion.assertion_kind == "edge":
        return _qualified_edge_update(assertion, endpoint_kinds=endpoint_kinds)
    return {}


def _qualified_edge_update(
    assertion: Any, *, endpoint_kinds: Mapping[str, str]
) -> dict[str, Any]:
    """Inject the qualified ``dm_predicate`` into an edge assertion's value.

    Buddy edges carry the raw Buddy ``predicate``; the v6 materializer
    requires the DungeonMind-qualified predicate in the value. The mapping
    is the conformance contract's explicit table, which deliberately refuses
    invented mappings — an unmappable predicate fails closed rather than
    publishing a fabricated term. Reverse-endpoint predicates (``belongs_to``
    → ``dnd5e:owns``) swap the assertion endpoints so the materialized
    relationship direction matches the adopted graph's convention; the
    value's ``edge_id`` keeps the original Buddy orientation, so the
    relationship id and the Buddy content-addressed assertion id are
    unchanged (the inverse translation un-swaps deterministically).

    The name mapping alone is not sufficient for publication: the concrete
    endpoint kinds must also be admitted for the qualified predicate by the
    world-object-v5 vocabulary (``dnd5e:leads_to`` is Location→Location).
    DungeonMind's materializer requires the qualified predicate and existing
    endpoints but does not re-check predicate-specific endpoint kinds, so
    this writer is the last governed gate — an inadmitted endpoint pair fails
    closed here rather than becoming authoritative.

    The writer also applies the conformance contract's full-edge direction
    audit (``edge_has_reverse_direction_qualifier_v4``) before automatic
    translation: an edge id carrying a reverse-qualifier pattern for its
    Buddy predicate (``is-threatened-by`` on a ``threatens`` edge) marks a
    relationship authored in the reverse direction, and name mapping plus
    admission-valid endpoints would otherwise publish inverted semantics.
    """
    import json as _json

    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _canonical_json,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        edge_has_reverse_direction_qualifier_v4,
        resolve_buddy_predicate_mapping_v4,
    )

    value = _json.loads(assertion.value) if assertion.value else {}
    if not isinstance(value, dict):
        value = {}
    if isinstance(value.get("dm_predicate"), str) and value["dm_predicate"].strip():
        return {}
    mapping = resolve_buddy_predicate_mapping_v4(str(assertion.predicate or ""))
    if mapping is None or not mapping[0]:
        raise WorldGraphAuthorityError(
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
        raise WorldGraphAuthorityError(
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


def _assert_edge_endpoint_admission(
    assertion: Any,
    *,
    dm_predicate: str,
    reverse_endpoints: bool,
    endpoint_kinds: Mapping[str, str],
) -> None:
    """Fail closed unless the edge's concrete endpoint kinds are admitted for
    the qualified predicate by the world-object-v5 vocabulary.

    This mirrors the conformance contract's endpoint-admission rule
    (``_admit_mapped_edge_v4``): endpoint Buddy kinds resolve through the
    same ``CURRENT_V5_TARGET.buddy_to_dm_kind`` table used for node
    qualification, reverse-mapped predicates admit the swapped orientation,
    and an endpoint that is missing, unmapped, or outside the predicate's
    admitted subject/object kinds makes the edge inexpressible — the writer
    never publishes a relationship the vocabulary does not admit.
    """
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
        raise WorldGraphAuthorityError(
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
        raise WorldGraphAuthorityError(
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


def _qualified_value(assertion: Any) -> str | None:
    """Inject the qualified ``dm_kind`` into a node assertion's value.

    The v6 materializer creates new objects from the assertion value and
    requires the DungeonMind-qualified kind. Buddy node values carry the
    Buddy ``kind`` vocabulary; qualify it through the same
    ``CURRENT_V5_TARGET.buddy_to_dm_kind`` mapping the sealed adoption
    producer used for the adopted graph payload. An unmapped kind fails
    closed — the confirmed node cannot be represented in the v6 graph.
    """
    import json as _json

    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        _canonical_json,
    )
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
        CURRENT_V5_TARGET,
    )

    if assertion.assertion_kind != "node" or not assertion.value:
        return assertion.value
    value = _json.loads(assertion.value)
    if not isinstance(value, dict):
        return assertion.value
    if isinstance(value.get("dm_kind"), str) and value["dm_kind"].strip():
        return assertion.value
    buddy_kind = value.get("kind")
    mapped = CURRENT_V5_TARGET.buddy_to_dm_kind.get(str(buddy_kind or ""))
    if mapped is None:
        raise WorldGraphAuthorityError(
            "confirmed node kind has no DungeonMind mapping",
            code="governed_write_inexpressible",
            details={
                "assertion_id": assertion.assertion_id,
                "buddy_kind": buddy_kind,
            },
        )
    return _canonical_json({**value, "dm_kind": mapped})


def _normalized_temporal_scope(temporal_scope: Any) -> Any:
    """Normalize Buddy's real-world-session temporal hint for DungeonMind.

    Buddy's edge producer encodes "surfaced in this real-world session" as
    ``temporal_scope={"session_id": ...}``. DungeonMind's contract separates
    real-world sessions (``session_refs`` — already carried in the edge
    value's ``session_ids``) from fictional-time knowledge state, and the v6
    materializer only accepts a typed ``TemporalScopeRefV1``. The hint is
    therefore normalized to ``None`` (temporal scope unknown); the hydration
    inverse reconstructs it from the value's ``session_ids`` so the
    content-addressed assertion id recomputes exactly. Any other shape passes
    through to the materializer's fail-closed validation.
    """
    if (
        isinstance(temporal_scope, dict)
        and set(temporal_scope) == {"session_id"}
        and isinstance(temporal_scope["session_id"], str)
    ):
        return None
    return temporal_scope


def _build_identity_dispositions(
    candidate: Any,
    verdict_states: dict[str, Any],
) -> tuple[list[Any], list[Any]]:
    """Build v2 identity proposals/verdicts from reviewed Buddy outcomes.

    Buddy's identity gate already resolved every accepted node/alias target:
    ``created_new`` maps to a PROVISIONAL_NEW proposal + CREATE_NEW verdict;
    ``resolved_existing`` maps to a RESOLVED_EXISTING proposal (matched to the
    target) + CONFIRM_EXISTING verdict. Any other outcome on an accepted
    node/alias target cannot be honestly represented in the v2 review model
    and fails closed.

    Only targets whose assertion verdict is ACCEPTED are covered: the v2
    contract requires proposals to cover exactly the accepted node/alias
    subject targets, and a rejected assertion keeps its candidate identity
    outcome untouched.
    """
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
            raise WorldGraphAuthorityError(
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
            raise WorldGraphAuthorityError(
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
    """The server-side confirm_commit policy bound to the exact review scope."""
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


def _confirm_proof_payload(
    package: dict[str, Any],
    *,
    world_id: str,
    outcome: str,
    parent_revision_id: str,
    committed_revision_id: str,
    contribution_id: str,
    projection_world_root: Path | None = None,
) -> dict[str, Any]:
    """The existing Buddy confirm proof shape, with DungeonMind identity.

    ``projection_world_root`` points the service's receipt decoration at the
    hydrated cache (which can resolve the DungeonMind-sealed parent); the
    frozen store cannot.
    """
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
        "projection_world_root": (
            str(projection_world_root) if projection_world_root is not None else None
        ),
    }


def confirm_via_dungeonmind(
    request: Any,
    *,
    world_root: Path,
    database_url: str,
    cache_root: Path,
    frozen_root: Path,
    confirming_principal: str,
    assertion_ids: tuple[str, ...] | None,
    repo_root: Path,
) -> Any:
    """Delegate governed exact-run confirm to the native DungeonMind writer.

    Hydration kwargs (``world_root``, ``cache_root``, ``frozen_root``) are
    accepted for call-site compatibility and ignored. New packages must seal
    a public DungeonMind parent revision.
    """
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_writes,
    )

    try:
        return world_graph_writes.confirm_extract_promote_via_dungeonmind(
            request,
            database_url=database_url,
            confirming_principal=confirming_principal,
            assertion_ids=assertion_ids,
            repo_root=repo_root,
        )
    except world_graph_writes.WorldGraphWriteError as exc:
        raise WorldGraphAuthorityError(
            str(exc),
            code=exc.code,
            details=exc.details,
        ) from exc



__all__ = [
    "AuthorityBinding",
    "AuthorityReadRoute",
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
