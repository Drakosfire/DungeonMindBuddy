"""Prove current Buddy alias blockers are reconstructable DungeonMind alias assertions.

Diagnostic only. Does not mutate World Graph, contributions, aliases, or evidence.
Does not traverse merged-away identity to manufacture alias provenance.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from typing import Any, Literal

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


class AliasAssertionPackageConformanceError(RuntimeError):
    """Fail-closed alias-package proof error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(message: str, code: str) -> AliasAssertionPackageConformanceError:
    return AliasAssertionPackageConformanceError(message, code=code)


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


def _build_metadata(
    *,
    assertion: GraphContributionAssertion,
    node: UnionSupergraphNode,
    dungeonmind_assertion_id: str,
    evidence_ref_ids: list[str],
    store: UnionSupergraphStore,
) -> tuple[KnowledgeAssertionMetadataV1 | None, dict[str, str], str | None]:
    derivation: dict[str, str] = {}
    campaign_scope = assertion.campaign_scope
    derivation["campaign_scope"] = "source_assertion"

    visibility = _map_visibility(assertion.visibility)
    if visibility is not None:
        derivation["visibility"] = "source_assertion"
    else:
        visibility = _map_visibility((node.state or {}).get("visibility"))
        if visibility is None:
            return None, derivation, "unrecognized_visibility"
        derivation["visibility"] = "current_node_state"

    epistemic = _map_epistemic(assertion.epistemic_kind)
    if epistemic is not None:
        derivation["epistemic_kind"] = "source_assertion"
    else:
        epistemic = _map_epistemic((node.state or {}).get("epistemic_kind"))
        if epistemic is None:
            return None, derivation, "unrecognized_epistemic_kind"
        derivation["epistemic_kind"] = "current_node_state"

    value = semantic_assertion_value(assertion.value)
    canon = _map_canon(value.get("canon_state") if isinstance(value.get("canon_state"), str) else None)
    if canon is not None:
        derivation["canon_state"] = "source_assertion_value"
    else:
        canon = _map_canon((node.state or {}).get("canon_state"))
        if canon is None:
            return None, derivation, "unrecognized_canon_state"
        derivation["canon_state"] = "current_node_state"

    session_refs: set[str] = set()
    for evidence_id in evidence_ref_ids:
        record = store.evidence.get(evidence_id)
        if record is None:
            return None, derivation, "dangling_evidence_ref"
        session_id = getattr(record, "session_id", None)
        if isinstance(session_id, str) and session_id.strip():
            session_refs.add(session_id.strip())
    derivation["session_refs"] = "referenced_evidence_session_ids"
    derivation["temporal_scope"] = "unknown_no_fictional_time_mapping"
    derivation["evidence_ref_ids"] = "per_source_assertion_lineage"

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
    world_id: str,
    canonical_revision_id: str,
    canonical_graph_payload_sha256: str,
    contribution_loader: ContributionLoader,
    expected_blocker_element_ids: list[str] | None = None,
) -> AliasAssertionPackageConformanceV1:
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
        blocker_element_ids=blocker_ids,
        alias_inventory=inventory,
        package_rows=package_rows,
        covered_blocker_element_ids=covered,
        residuals=residuals,
        reconstructable_count=len(package_rows),
        residual_count=len(residuals),
        passed=passed,
    )
