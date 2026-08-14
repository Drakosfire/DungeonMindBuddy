"""Prove current Buddy alias blockers are reconstructable DungeonMind alias assertions.

Diagnostic only. Does not mutate World Graph, contributions, aliases, or evidence.
Does not traverse merged-away identity to manufacture alias provenance.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from typing import Any, Literal

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pydantic import BaseModel, ConfigDict, Field

from dungeonmind.application.graph_snapshot_v4 import AliasAssertionV4Record
from dungeonmind.contracts.knowledge_assertion import (
    CanonState,
    EpistemicKindV2,
    KnowledgeAssertionMetadataV1,
    TemporalScopeRefV1,
    Visibility,
)
from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion
from graph_memory.kernel.contributions import (
    compute_contribution_source_payload_sha256,
    explicit_assertion_evidence_ref_ids,
    explicit_assertion_source_artifact_ids,
    semantic_assertion_value,
)
from graph_memory.union_supergraph.model import UnionSupergraphNode, UnionSupergraphStore


ALIAS_ASSERTION_PACKAGE_SCHEMA = "dmb_alias_assertion_package_conformance_v1"
BUNDLED_ALIAS_ID_FAMILY = "alias"
IDENTITY_DERIVED_REASON = "identity_derived_alias_requires_identity_replay"
PROVEN_ALIAS_NOTE = (
    "validated DungeonMind-compatible alias assertion reconstructed from "
    "revision-bound Buddy source authority"
)

SourceForm = Literal["explicit_alias_assertion", "bundled_node_alias"]
ContributionLoader = Callable[[str], GraphContribution]
_ALIAS_PACKAGE_BINDING_TOKEN = object()


class AliasAssertionPackageConformanceError(RuntimeError):
    """Fail-closed alias-package proof error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(message: str, code: str) -> AliasAssertionPackageConformanceError:
    return AliasAssertionPackageConformanceError(message, code=code)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {
            key: _jsonable(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }
    return str(value)


def store_semantic_sha256(store: Any) -> str:
    """Digest the in-memory store used for alias-package attestation.

    This is not the on-disk graph payload hash. It binds a proof to the exact
    store object that was attested with a revision manifest.
    """
    encoded = _canonical_json({"store": _jsonable(store)})
    return sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AliasPackageRevisionBinding:
    """Attested world/revision/payload binding for one loaded store.

    Pins are copied from the attested revision manifest, never from free-form
    caller strings at prove time. The store digest must match the store later
    passed to ``prove_alias_assertion_package_v1``.
    """

    world_id: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    store_semantic_sha256: str
    _token: object = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _ALIAS_PACKAGE_BINDING_TOKEN:
            raise TypeError(
                "AliasPackageRevisionBinding is not a public constructor; "
                "use alias_package_binding_from_attested_revision"
            )


def alias_package_binding_from_attested_revision(
    *,
    manifest: Any,
    store: Any,
    expected_world_id: str,
    expected_revision_id: str,
    expected_graph_payload_sha256: str,
) -> AliasPackageRevisionBinding:
    """Derive alias-package pins from an attested revision manifest + store.

    Refuses when the caller-supplied expected pins do not match the manifest,
    or when any pin is blank. Does not accept free-form world/revision/payload
    labels disconnected from a manifest.
    """
    world_id = str(getattr(manifest, "world_id", "") or "")
    revision_id = str(getattr(manifest, "revision_id", "") or "")
    payload_sha = str(getattr(manifest, "graph_payload_sha256", "") or "")
    if not world_id or not revision_id or not payload_sha:
        raise _fail(
            "alias-package binding requires attested world/revision/payload pins",
            "alias_package_binding_unattested",
        )
    if not expected_world_id or not expected_revision_id or not expected_graph_payload_sha256:
        raise _fail(
            "alias-package binding expected pins must be nonblank",
            "alias_package_binding_unattested",
        )
    if (
        world_id != expected_world_id
        or revision_id != expected_revision_id
        or payload_sha != expected_graph_payload_sha256
    ):
        raise _fail(
            "alias-package expected pins do not match attested revision manifest",
            "alias_package_binding_pin_mismatch",
        )
    return AliasPackageRevisionBinding(
        world_id=world_id,
        canonical_revision_id=revision_id,
        canonical_graph_payload_sha256=payload_sha,
        store_semantic_sha256=store_semantic_sha256(store),
        _token=_ALIAS_PACKAGE_BINDING_TOKEN,
    )


def _require_alias_package_store_binding(
    binding: AliasPackageRevisionBinding,
    store: Any,
) -> None:
    if not isinstance(binding, AliasPackageRevisionBinding):
        raise _fail(
            "alias-package proof requires an attested revision binding",
            "alias_package_binding_unattested",
        )
    digest = store_semantic_sha256(store)
    if digest != binding.store_semantic_sha256:
        raise _fail(
            "alias-package proof store does not match attested revision binding",
            "alias_package_store_binding_mismatch",
        )


class AliasAssertionPackageRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocker_element_id: str
    target_node_id: str
    alias_value: str
    source_form: SourceForm
    buddy_source_assertion_id: str
    buddy_source_contribution_id: str
    buddy_source_payload_sha256: str
    source_evidence_ref_ids: list[str]
    source_artifact_ids: list[str]
    dungeonmind_assertion_id: str
    dungeonmind_alias_record: dict[str, Any]
    metadata_derivation: dict[str, str]
    reconstructable: bool
    rationale: str


class AliasPackageResidualV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocker_element_id: str
    target_node_id: str | None
    alias_value: str | None
    alias_key: str | None
    reason_code: str
    source_candidate_ids: list[str]
    diagnostics: list[str]


class AliasBlockerInventoryRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    element_family: Literal["node.aliases", "store.aliases"]
    target_node_id: str
    canonical_label: str | None
    substantive_alias_values: list[str]
    derivable_lookup_keys: list[str]


class AliasAssertionPackageConformanceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_alias_assertion_package_conformance_v1"] = Field(
        default=ALIAS_ASSERTION_PACKAGE_SCHEMA,
        alias="schema",
    )
    world_id: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    store_semantic_sha256: str
    blocker_element_ids: list[str]
    alias_inventory: list[AliasBlockerInventoryRowV1]
    package_rows: list[AliasAssertionPackageRowV1]
    covered_blocker_element_ids: list[str]
    residuals: list[AliasPackageResidualV1]
    reconstructable_count: int
    residual_count: int
    passed: bool


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def derive_bundled_alias_assertion_id(
    *,
    world_id: str,
    target_node_id: str,
    source_buddy_node_assertion_id: str,
    alias_value: str,
) -> str:
    """Deterministic child ID for an alias split from a Buddy node assertion."""
    payload = {
        "alias_value": alias_value,
        "assertion_family": BUNDLED_ALIAS_ID_FAMILY,
        "source_buddy_node_assertion_id": source_buddy_node_assertion_id,
        "target_node_id": target_node_id,
        "world_id": world_id,
    }
    digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:24]
    return f"assertion:cutover-alias:{digest}"


def _node_alias_strings(node: UnionSupergraphNode) -> list[str]:
    return [
        str(alias)
        for alias in (node.aliases or [])
        if isinstance(alias, str) and alias.strip()
    ]


def _substantive_node_aliases(node: UnionSupergraphNode) -> list[str]:
    label_key = (node.label or "").strip().casefold()
    return [
        alias
        for alias in _node_alias_strings(node)
        if alias.strip().casefold() != label_key
    ]


def _trim(value: str | None) -> str:
    return (value or "").strip()


def collect_alias_blocker_candidates(
    store: UnionSupergraphStore,
) -> list[AliasBlockerInventoryRowV1]:
    """Enumerate current EVIDENCE_PROVENANCE alias elements from store truth."""
    rows: list[AliasBlockerInventoryRowV1] = []
    for node_id, node in store.nodes.items():
        substantive = _substantive_node_aliases(node)
        if not substantive:
            continue
        label = _trim(node.label)
        derivable = []
        for key, target in store.aliases.items():
            if target != node_id:
                continue
            folded = key.casefold()
            if folded == label.casefold() or folded in {alias.casefold() for alias in _node_alias_strings(node)}:
                derivable.append(key)
        rows.append(
            AliasBlockerInventoryRowV1(
                element_id=f"node:{node_id}:field:aliases",
                element_family="node.aliases",
                target_node_id=node_id,
                canonical_label=node.label,
                substantive_alias_values=substantive,
                derivable_lookup_keys=sorted(derivable),
            )
        )
    node_alias_keys_by_target: dict[str, set[str]] = {}
    labels_by_target: dict[str, str] = {}
    for node_id, node in store.nodes.items():
        node_alias_keys_by_target[node_id] = {alias.casefold() for alias in _node_alias_strings(node)}
        labels_by_target[node_id] = (node.label or "").strip().casefold()
    for alias_label, target_node_id in store.aliases.items():
        if not alias_label.strip() or not str(target_node_id).strip():
            rows.append(
                AliasBlockerInventoryRowV1(
                    element_id=f"alias:{alias_label}",
                    element_family="store.aliases",
                    target_node_id=str(target_node_id),
                    canonical_label=None,
                    substantive_alias_values=[],
                    derivable_lookup_keys=[],
                )
            )
            continue
        node = store.nodes.get(target_node_id)
        if node is None:
            rows.append(
                AliasBlockerInventoryRowV1(
                    element_id=f"alias:{alias_label}",
                    element_family="store.aliases",
                    target_node_id=target_node_id,
                    canonical_label=None,
                    substantive_alias_values=[alias_label],
                    derivable_lookup_keys=[],
                )
            )
            continue
        key = alias_label.casefold()
        if key == labels_by_target.get(target_node_id, "") or key in node_alias_keys_by_target.get(
            target_node_id, set()
        ):
            continue
        rows.append(
            AliasBlockerInventoryRowV1(
                element_id=f"alias:{alias_label}",
                element_family="store.aliases",
                target_node_id=target_node_id,
                canonical_label=node.label,
                substantive_alias_values=[alias_label],
                derivable_lookup_keys=[],
            )
        )
    rows.sort(key=lambda row: row.element_id)
    return rows


def _replay_by_contribution(store: UnionSupergraphStore) -> dict[str, Any]:
    return {entry.contribution_id: entry for entry in store.contribution_replay_manifest}


def _parse_support(raw: Mapping[str, Any] | DurableAssertionSupport) -> DurableAssertionSupport:
    if isinstance(raw, DurableAssertionSupport):
        return raw
    return DurableAssertionSupport.model_validate(dict(raw))


def _active_redirects_to(store: UnionSupergraphStore, target_node_id: str) -> list[Any]:
    rows = []
    for redirect in store.identity_redirects:
        status = getattr(redirect, "status", None)
        if status not in {None, "active"}:
            continue
        if getattr(redirect, "to_node_id", None) == target_node_id:
            rows.append(redirect)
    return rows


def _identity_derived_sources(
    store: UnionSupergraphStore,
    *,
    target_node_id: str,
    alias_value: str,
) -> list[str]:
    """Detect merged-away labels/aliases that explain a survivor alias.

    Used only to classify a residual. Never treated as package provenance.
    """
    wanted = alias_value.strip()
    wanted_key = wanted.casefold()
    candidates: list[str] = []
    for redirect in _active_redirects_to(store, target_node_id):
        source_id = getattr(redirect, "from_node_id", None)
        if not isinstance(source_id, str) or not source_id:
            continue
        source = store.nodes.get(source_id)
        if source is None:
            continue
        merged_into = (source.state or {}).get("merged_into")
        if merged_into not in {None, target_node_id}:
            continue
        labels = [_trim(source.label), *(_node_alias_strings(source))]
        if any(item == wanted or item.casefold() == wanted_key for item in labels if item):
            candidates.append(source_id)
    for record in store.identity_merge_records:
        if getattr(record, "status", "applied") not in {"applied", None}:
            continue
        if getattr(record, "survivor_node_id", None) != target_node_id:
            continue
        unioned = list(getattr(record, "aliases_unioned", []) or [])
        if wanted in unioned or wanted_key in {str(item).casefold() for item in unioned}:
            candidates.extend(list(getattr(record, "merged_away_node_ids", []) or []))
    return sorted(set(candidates))


def _find_accepted_assertion(
    contribution: GraphContribution,
    assertion_id: str,
) -> GraphContributionAssertion | None:
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_id == assertion_id:
            return assertion
    return None


def _alias_strings_from_assertion(assertion: GraphContributionAssertion) -> tuple[list[str], str | None]:
    value = semantic_assertion_value(assertion.value)
    aliases: list[str] = []
    if assertion.assertion_kind == "alias":
        nested = value.get("alias")
        label = _trim(assertion.label)
        nested_s = _trim(nested) if isinstance(nested, str) else ""
        if nested_s and label and nested_s != label:
            return [], "alias_label_value_disagree"
        chosen = nested_s or label
        if chosen:
            aliases.append(chosen)
        return aliases, None
    raw = value.get("aliases")
    if isinstance(raw, list):
        aliases.extend(_trim(str(item)) for item in raw if str(item).strip())
    return aliases, None


def _require_revision_bound_contribution(
    store: UnionSupergraphStore,
    contribution_id: str,
    contribution: GraphContribution,
) -> tuple[str | None, str]:
    replay = _replay_by_contribution(store).get(contribution_id)
    if replay is None:
        return None, "contribution_not_in_revision_replay_manifest"
    if getattr(replay, "status", None) != "active":
        return None, "contribution_not_active_in_revision"
    if contribution.status != "active":
        return None, "contribution_ledger_not_active"
    digest = compute_contribution_source_payload_sha256(contribution)
    sealed = store.contribution_source_payload_sha256.get(contribution_id)
    replay_digest = getattr(replay, "source_payload_sha256", None)
    if sealed != digest or replay_digest != digest:
        return None, "contribution_source_digest_drift"
    return digest, "ok"


def _require_support_lineage(
    support: DurableAssertionSupport,
    *,
    contribution_id: str,
    assertion: GraphContributionAssertion,
    target_node_id: str,
) -> str | None:
    if support.support_state != "supported":
        return "support_not_supported"
    if contribution_id not in support.active_contribution_ids:
        return "contribution_not_in_active_support"
    if support.graph_object_id not in {target_node_id, None}:
        return "support_graph_object_mismatch"
    if support.graph_object_id is None and assertion.subject_node_id != target_node_id:
        return "null_support_subject_mismatch"
    expected_evidence = list(explicit_assertion_evidence_ref_ids(assertion))
    per_evidence = list(support.per_contribution_evidence_ref_ids.get(contribution_id, []))
    if expected_evidence != per_evidence:
        return "per_contribution_evidence_lineage_drift"
    expected_artifacts = list(explicit_assertion_source_artifact_ids(assertion))
    per_artifacts = list(support.per_contribution_source_artifact_ids.get(contribution_id, []))
    if expected_artifacts != per_artifacts:
        return "per_contribution_source_artifact_lineage_drift"
    if not expected_evidence:
        return "empty_evidence_refs"
    return None


def _map_visibility(raw: str | None) -> Visibility | None:
    try:
        return Visibility(raw) if raw is not None else None
    except ValueError:
        return None


def _map_epistemic(raw: str | None) -> EpistemicKindV2 | None:
    try:
        return EpistemicKindV2(raw) if raw is not None else None
    except ValueError:
        return None


def _map_canon(raw: str | None) -> CanonState | None:
    try:
        return CanonState(raw) if raw is not None else None
    except ValueError:
        return None


_REQUIRED_METADATA_DERIVATION_KEYS = (
    "campaign_scope",
    "visibility",
    "epistemic_kind",
    "canon_state",
    "evidence_ref_ids",
    "session_refs",
    "temporal_scope",
)


def _resolve_source_or_node_metadata(
    *,
    source_raw: Any,
    node_raw: Any,
    mapper: Callable[[str | None], Any],
    source_present: bool,
    source_derivation: str,
    node_derivation: str,
    unrecognized_code: str,
    conflict_code: str,
) -> tuple[Any, str | None, str | None]:
    """Prefer source metadata; fall back to current-node only when source is absent."""
    if source_present:
        mapped = mapper(source_raw if isinstance(source_raw, str) else None)
        if mapped is None:
            return None, None, unrecognized_code
        node_mapped = mapper(node_raw if isinstance(node_raw, str) else None)
        if node_mapped is not None and node_mapped != mapped:
            return None, None, conflict_code
        return mapped, source_derivation, None
    mapped = mapper(node_raw if isinstance(node_raw, str) else None)
    if mapped is None:
        return None, None, unrecognized_code
    return mapped, node_derivation, None


def _build_metadata(
    *,
    assertion: GraphContributionAssertion,
    node: UnionSupergraphNode,
    dungeonmind_assertion_id: str,
    evidence_ref_ids: list[str],
    store: UnionSupergraphStore,
) -> tuple[KnowledgeAssertionMetadataV1 | None, dict[str, str], str | None]:
    derivation: dict[str, str] = {}
    node_state = node.state or {}
    # Null campaign_scope is world-universal. Never replace it with the current campaign.
    campaign_scope = assertion.campaign_scope
    if campaign_scope is None:
        derivation["campaign_scope"] = "source_assertion_null_world_universal"
    else:
        derivation["campaign_scope"] = "source_assertion"

    visibility, vis_from, vis_error = _resolve_source_or_node_metadata(
        source_raw=assertion.visibility,
        node_raw=node_state.get("visibility"),
        mapper=_map_visibility,
        source_present=assertion.visibility is not None,
        source_derivation="source_assertion",
        node_derivation="current_node_state",
        unrecognized_code="unrecognized_visibility",
        conflict_code="source_current_visibility_conflict",
    )
    if vis_error:
        return None, derivation, vis_error
    derivation["visibility"] = vis_from or "hidden_metadata_fallback"

    epistemic, epi_from, epi_error = _resolve_source_or_node_metadata(
        source_raw=assertion.epistemic_kind,
        node_raw=node_state.get("epistemic_kind"),
        mapper=_map_epistemic,
        source_present=assertion.epistemic_kind is not None,
        source_derivation="source_assertion",
        node_derivation="current_node_state",
        unrecognized_code="unrecognized_epistemic_kind",
        conflict_code="source_current_epistemic_conflict",
    )
    if epi_error:
        return None, derivation, epi_error
    derivation["epistemic_kind"] = epi_from or "hidden_metadata_fallback"

    value = semantic_assertion_value(assertion.value)
    raw_canon = value.get("canon_state")
    canon, canon_from, canon_error = _resolve_source_or_node_metadata(
        source_raw=raw_canon,
        node_raw=node_state.get("canon_state"),
        mapper=_map_canon,
        source_present=isinstance(raw_canon, str),
        source_derivation="source_assertion_value",
        node_derivation="current_node_state",
        unrecognized_code="unrecognized_canon_state",
        conflict_code="source_current_canon_conflict",
    )
    if canon_error:
        return None, derivation, canon_error
    derivation["canon_state"] = canon_from or "hidden_metadata_fallback"

    session_refs: set[str] = set()
    for evidence_id in evidence_ref_ids:
        record = store.evidence.get(evidence_id)
        if record is None:
            return None, derivation, "dangling_evidence_ref"
        session_id = getattr(record, "session_id", None)
        if isinstance(session_id, str) and session_id.strip():
            session_refs.add(session_id.strip())
    derivation["session_refs"] = "referenced_evidence_session_ids"
    derivation["evidence_ref_ids"] = "per_source_assertion_lineage"

    raw_temporal = assertion.temporal_scope
    if raw_temporal:
        kind = raw_temporal.get("kind") if isinstance(raw_temporal, dict) else None
        if str(kind or "").strip() not in {"", "unknown"}:
            derivation["temporal_scope"] = "ungoverned_fictional_time_mapping"
            return None, derivation, "ungoverned_fictional_time_mapping"
    # Session refs are real-world provenance only. Never infer fictional time.
    derivation["temporal_scope"] = "unknown_no_fictional_time_mapping"

    missing = [
        key
        for key in _REQUIRED_METADATA_DERIVATION_KEYS
        if key not in derivation or not derivation[key]
    ]
    if missing:
        return None, derivation, "hidden_metadata_fallback"

    metadata = KnowledgeAssertionMetadataV1(
        assertion_id=dungeonmind_assertion_id,
        campaign_scope=campaign_scope,
        visibility=visibility,
        epistemic_kind=epistemic,
        canon_state=canon,
        evidence_ref_ids=evidence_ref_ids,
        session_refs=sorted(session_refs),
        temporal_scope=TemporalScopeRefV1(kind="unknown"),
    )
    return metadata, derivation, None


def _try_package_alias(
    *,
    store: UnionSupergraphStore,
    world_id: str,
    blocker_element_id: str,
    target_node_id: str,
    alias_value: str,
    contribution_loader: ContributionLoader,
) -> tuple[list[AliasAssertionPackageRowV1], list[str], list[str]]:
    """Return (rows, source_candidate_ids, failure_codes)."""
    node = store.nodes.get(target_node_id)
    if node is None:
        return [], [], ["missing_target_node"]
    rows: list[AliasAssertionPackageRowV1] = []
    candidate_ids: list[str] = []
    failures: list[str] = []
    for raw in store.assertion_support.values():
        support = _parse_support(raw)
        if support.assertion_kind not in {"alias", "node"}:
            continue
        if support.graph_object_id not in {target_node_id, None}:
            continue
        for contribution_id in support.active_contribution_ids:
            try:
                contribution = contribution_loader(contribution_id)
            except FileNotFoundError:
                failures.append("contribution_ledger_missing")
                continue
            assertion = _find_accepted_assertion(contribution, support.assertion_id)
            if assertion is None:
                failures.append("accepted_assertion_missing")
                continue
            candidate_ids.append(assertion.assertion_id)
            if assertion.acceptance_state != "accepted":
                failures.append("assertion_not_accepted")
                continue
            if assertion.subject_node_id != target_node_id:
                failures.append("assertion_subject_not_current_target")
                continue
            digest, digest_status = _require_revision_bound_contribution(
                store, contribution_id, contribution
            )
            if digest is None:
                failures.append(digest_status)
                continue
            lineage_error = _require_support_lineage(
                support,
                contribution_id=contribution_id,
                assertion=assertion,
                target_node_id=target_node_id,
            )
            if lineage_error:
                failures.append(lineage_error)
                continue
            aliases, alias_error = _alias_strings_from_assertion(assertion)
            if alias_error:
                failures.append(alias_error)
                continue
            if alias_value not in aliases:
                continue
            if assertion.assertion_kind == "alias":
                source_form: SourceForm = "explicit_alias_assertion"
                dm_id = assertion.assertion_id
            elif assertion.assertion_kind == "node":
                source_form = "bundled_node_alias"
                dm_id = derive_bundled_alias_assertion_id(
                    world_id=world_id,
                    target_node_id=target_node_id,
                    source_buddy_node_assertion_id=assertion.assertion_id,
                    alias_value=alias_value,
                )
            else:
                continue
            evidence_ids = list(explicit_assertion_evidence_ref_ids(assertion))
            artifact_ids = list(explicit_assertion_source_artifact_ids(assertion))
            if any(eid not in store.evidence for eid in evidence_ids):
                failures.append("dangling_evidence_ref")
                continue
            if any(aid not in store.source_artifacts for aid in artifact_ids):
                failures.append("dangling_source_artifact")
                continue
            metadata, derivation, meta_error = _build_metadata(
                assertion=assertion,
                node=node,
                dungeonmind_assertion_id=dm_id,
                evidence_ref_ids=evidence_ids,
                store=store,
            )
            if metadata is None or meta_error:
                failures.append(meta_error or "metadata_mapping_failed")
                continue
            try:
                record = AliasAssertionV4Record(
                    value=alias_value,
                    assertion_metadata=metadata,
                )
            except Exception:  # noqa: BLE001 — pinned DM contract is the validator
                failures.append("dungeonmind_alias_record_invalid")
                continue
            rows.append(
                AliasAssertionPackageRowV1(
                    blocker_element_id=blocker_element_id,
                    target_node_id=target_node_id,
                    alias_value=alias_value,
                    source_form=source_form,
                    buddy_source_assertion_id=assertion.assertion_id,
                    buddy_source_contribution_id=contribution_id,
                    buddy_source_payload_sha256=digest,
                    source_evidence_ref_ids=evidence_ids,
                    source_artifact_ids=artifact_ids,
                    dungeonmind_assertion_id=dm_id,
                    dungeonmind_alias_record=record.model_dump(mode="json"),
                    metadata_derivation=derivation,
                    reconstructable=True,
                    rationale=PROVEN_ALIAS_NOTE,
                )
            )
    rows.sort(key=lambda row: (row.dungeonmind_assertion_id, row.buddy_source_assertion_id))
    return rows, sorted(set(candidate_ids)), sorted(set(failures))


def prove_alias_assertion_package_v1(
    store: UnionSupergraphStore,
    *,
    binding: AliasPackageRevisionBinding,
    contribution_loader: ContributionLoader,
    expected_blocker_element_ids: list[str] | None = None,
) -> AliasAssertionPackageConformanceV1:
    _require_alias_package_store_binding(binding, store)
    world_id = binding.world_id
    canonical_revision_id = binding.canonical_revision_id
    canonical_graph_payload_sha256 = binding.canonical_graph_payload_sha256
    inventory = collect_alias_blocker_candidates(store)
    blocker_ids = [row.element_id for row in inventory]
    if expected_blocker_element_ids is not None and blocker_ids != list(expected_blocker_element_ids):
        raise _fail(
            f"alias blocker inventory drifted: observed={blocker_ids} "
            f"expected={list(expected_blocker_element_ids)}",
            "stale_alias_blocker_inventory",
        )
    if len(set(blocker_ids)) != len(blocker_ids):
        raise _fail("duplicate alias blocker element IDs", "duplicate_alias_blocker_ids")

    package_rows: list[AliasAssertionPackageRowV1] = []
    residuals: list[AliasPackageResidualV1] = []
    covered: list[str] = []
    used_dm_ids: dict[str, str] = {}

    for item in inventory:
        alias_values = list(item.substantive_alias_values)
        if item.element_family == "store.aliases" and not alias_values:
            residuals.append(
                AliasPackageResidualV1(
                    blocker_element_id=item.element_id,
                    target_node_id=item.target_node_id,
                    alias_value=None,
                    alias_key=item.element_id.removeprefix("alias:"),
                    reason_code="non_derivable_key_without_source_alias",
                    source_candidate_ids=[],
                    diagnostics=["store.aliases key has no exact source-grounded display alias"],
                )
            )
            continue
        item_rows: list[AliasAssertionPackageRowV1] = []
        uncovered: list[AliasPackageResidualV1] = []
        for alias_value in alias_values:
            rows, candidates, failures = _try_package_alias(
                store=store,
                world_id=world_id,
                blocker_element_id=item.element_id,
                target_node_id=item.target_node_id,
                alias_value=alias_value,
                contribution_loader=contribution_loader,
            )
            if rows:
                item_rows.extend(rows)
                continue
            identity_sources = _identity_derived_sources(
                store,
                target_node_id=item.target_node_id,
                alias_value=alias_value,
            )
            if identity_sources:
                uncovered.append(
                    AliasPackageResidualV1(
                        blocker_element_id=item.element_id,
                        target_node_id=item.target_node_id,
                        alias_value=alias_value,
                        alias_key=None,
                        reason_code=IDENTITY_DERIVED_REASON,
                        source_candidate_ids=identity_sources,
                        diagnostics=[
                            "alias is explained by merged-away identity, not a current-node source assertion",
                            *failures,
                        ],
                    )
                )
                continue
            uncovered.append(
                AliasPackageResidualV1(
                    blocker_element_id=item.element_id,
                    target_node_id=item.target_node_id,
                    alias_value=alias_value,
                    alias_key=item.element_id.removeprefix("alias:")
                    if item.element_family == "store.aliases"
                    else None,
                    reason_code="alias_not_source_grounded",
                    source_candidate_ids=candidates,
                    diagnostics=failures or ["no admissible current-node source assertion"],
                )
            )
        if uncovered:
            residuals.extend(uncovered)
            continue
        for row in item_rows:
            previous = used_dm_ids.get(row.dungeonmind_assertion_id)
            claim = f"{row.target_node_id}:{row.alias_value}"
            if previous is not None and previous != claim:
                raise _fail(
                    f"derived alias assertion ID collision for {row.dungeonmind_assertion_id}",
                    "alias_assertion_id_collision",
                )
            used_dm_ids[row.dungeonmind_assertion_id] = claim
        package_rows.extend(item_rows)
        covered.append(item.element_id)

    package_rows.sort(key=lambda row: (row.blocker_element_id, row.dungeonmind_assertion_id))
    residuals.sort(key=lambda row: (row.blocker_element_id, row.alias_value or "", row.reason_code))
    passed = not residuals and set(covered) == set(blocker_ids) and bool(blocker_ids)
    return AliasAssertionPackageConformanceV1(
        world_id=world_id,
        canonical_revision_id=canonical_revision_id,
        canonical_graph_payload_sha256=canonical_graph_payload_sha256,
        store_semantic_sha256=binding.store_semantic_sha256,
        blocker_element_ids=blocker_ids,
        alias_inventory=inventory,
        package_rows=package_rows,
        covered_blocker_element_ids=covered,
        residuals=residuals,
        reconstructable_count=len(package_rows),
        residual_count=len(residuals),
        passed=passed,
    )
