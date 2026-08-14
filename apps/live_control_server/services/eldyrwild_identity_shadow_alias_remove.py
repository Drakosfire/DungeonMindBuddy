"""Governed exact-six Eldyrwild identity-shadow alias_remove application.

Applies public ``graph_memory.kernel.remove_identity_alias`` to six named
merge-shadow aliases on the current Eldyrwild parent, then publishes one
revision through the existing identity-decision seam.

Does not change generic Kernel semantics, does not remove Captain or Thrin
Branchborn, and does not mutate the canonical live world without an explicit
``allow_live_world`` opt-in.

PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION: preflight inspects durable assertion
and contribution copies, plus the merge-redirect map, before any
``remove_identity_alias`` call. Kernel does not export those inspectors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.config import (
    live_world_graph_root,
    world_graph_root,
)
from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contributions import semantic_assertion_value
from graph_memory.union_supergraph.redirects import active_identity_redirect_map
from graph_memory.world_supergraph.contribution_store import load_contribution_record
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
ACTOR = "gm"
EXPECTED_CANONICAL_REVISION_ID = "rev:5a7c13ae45c49a65b402920499be72ed"
EXPECTED_RELATIONSHIP_INVENTORY = {
    "semantic": 323,
    "represented": 314,
    "residual": 9,
    "uses_statblock_mechanics": 3,
}

EligibilityState = Literal[
    "eligible", "already_applied", "ineligible", "integrity_failure"
]


@dataclass(frozen=True)
class ShadowAliasTarget:
    survivor_node_id: str
    alias: str
    merged_away_node_id: str
    merge_decision_id: str
    derived_store_key: str


@dataclass(frozen=True)
class KeeperAlias:
    node_id: str
    alias: str
    assertion_id: str
    contribution_id: str
    source_sha: str


SHADOW_ALIAS_TARGETS: tuple[ShadowAliasTarget, ...] = (
    ShadowAliasTarget(
        survivor_node_id="item_foot_of_statue",
        alias="Enormous boulder",
        merged_away_node_id="item_enormous_boulder",
        merge_decision_id="identity-decision:622b690ffe07c2c6",
        derived_store_key="enormous boulder",
    ),
    ShadowAliasTarget(
        survivor_node_id="loc:chilled_warehouse",
        alias="the last warehouse",
        merged_away_node_id="loc:last_warehouse",
        merge_decision_id="identity-decision:1ff8bf27a0b1921c",
        derived_store_key="the last warehouse",
    ),
    ShadowAliasTarget(
        survivor_node_id="loc:crooked-retort",
        alias="Merchant\u2019s Crossroads apothecary",
        merged_away_node_id="organization:merchant-s-crossroads-apothecary",
        merge_decision_id="identity-decision:adab1e19800e24d7",
        derived_store_key="merchant\u2019s crossroads apothecary",
    ),
    ShadowAliasTarget(
        survivor_node_id="loc:the-council",
        alias="Council headquarters",
        merged_away_node_id="item:session11:council-headquarters",
        merge_decision_id="identity-decision:3a8965f409e85911",
        derived_store_key="council headquarters",
    ),
    ShadowAliasTarget(
        survivor_node_id="loc:underground-entrance",
        alias="A second underground entrance is discovered",
        merged_away_node_id="mystery:session9:second_underground_entrance",
        merge_decision_id="identity-decision:c7f1cab745c8a1d2",
        derived_store_key="a second underground entrance is discovered",
    ),
    ShadowAliasTarget(
        survivor_node_id="obj:session9:scroll_abyssal",
        alias="A scroll written in a strange language is found",
        merged_away_node_id="mystery:session9:scroll_in_strange_language",
        merge_decision_id="identity-decision:ac8e5efc25de3804",
        derived_store_key="a scroll written in a strange language is found",
    ),
)

KEEPER_ALIASES: tuple[KeeperAlias, ...] = (
    KeeperAlias(
        node_id="node:captain-lysandra-ironveil",
        alias="Captain",
        assertion_id="assertion:2a63c5992970e366",
        contribution_id="contribution:a4231edb9a228963",
        source_sha="2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c",
    ),
    KeeperAlias(
        node_id="node:thrin-branchborn",
        alias="Thrin Branchborn",
        assertion_id="assertion:1275811e41cbb14c",
        contribution_id="contribution:a4231edb9a228963",
        source_sha="2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c",
    ),
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EldyrwildIdentityShadowAliasRemoveStatus(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_identity_shadow_alias_remove_status_v1",
        alias="schema",
    )
    world_id: str
    campaign_id: str
    head_revision_id: str | None = None
    eligibility: EligibilityState
    reason: str | None = None
    expected_parent_revision_id: str | None = None
    target_count: int = 6
    retired_alias_count: int = 0
    keeper_aliases_present: bool | None = None
    diagnostics: list[str] = Field(default_factory=list)


class EldyrwildIdentityShadowAliasRemoveResult(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_identity_shadow_alias_remove_result_v1",
        alias="schema",
    )
    world_id: str
    expected_parent_revision_id: str
    parent_revision_id: str | None = None
    revision_id: str | None = None
    published: bool
    eligibility: EligibilityState | None = None
    decision_ids: list[str] = Field(default_factory=list)
    failure_code: str | None = None
    failure_message: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class EldyrwildIdentityShadowAliasRemoveError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def retirement_reason(target: ShadowAliasTarget) -> str:
    return (
        "CUTOVER identity-shadow alias_remove: "
        f"retire {target.alias!r} from {target.survivor_node_id} "
        f"(merge {target.merge_decision_id})"
    )


def expected_decision_id(target: ShadowAliasTarget) -> str:
    return kernel.compute_identity_decision_id(
        world_id=WORLD_ID,
        decision_kind="alias_remove",
        subject_node_id=target.survivor_node_id,
        target_node_id=None,
        alias=target.alias,
        source_candidate_id=None,
        reason=retirement_reason(target),
    )


def _resolve_root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _is_canonical_live_root(resolved: Path) -> bool:
    return resolved == live_world_graph_root().resolve()


def _alias_present(aliases: list[str], alias: str) -> bool:
    key = alias.casefold()
    return any(item.strip() and item.casefold() == key for item in aliases)


def _decisions_by_id(store: Any) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for raw in store.identity_decisions:
        payload = dict(raw)
        decision_id = str(payload.get("decision_id") or "")
        if decision_id:
            rows[decision_id] = payload
    return rows


def _matching_alias_remove(
    store: Any, target: ShadowAliasTarget
) -> dict[str, Any] | None:
    expected_id = expected_decision_id(target)
    payload = _decisions_by_id(store).get(expected_id)
    if payload is None:
        return None
    if payload.get("decision_kind") != "alias_remove":
        return None
    if payload.get("status") != "active":
        return None
    if payload.get("subject_node_id") != target.survivor_node_id:
        return None
    alias = str(payload.get("alias") or "")
    if alias.casefold() != target.alias.casefold():
        return None
    return payload


def _prior_alias_remove_exists(store: Any, target: ShadowAliasTarget) -> bool:
    for raw in store.identity_decisions:
        payload = dict(raw)
        if payload.get("decision_kind") != "alias_remove":
            continue
        if payload.get("status") != "active":
            continue
        if payload.get("subject_node_id") != target.survivor_node_id:
            continue
        alias = str(payload.get("alias") or "")
        if alias.casefold() == target.alias.casefold():
            return True
    return False


def _keeper_present(store: Any, keeper: KeeperAlias) -> bool:
    node = store.nodes.get(keeper.node_id)
    if node is None:
        return False
    return _alias_present(list(node.aliases), keeper.alias)


def _node_identity_canon_state(node: Any) -> str:
    state = dict(getattr(node, "state", None) or {})
    return str(state.get("identity_canon_state") or state.get("canon_state") or "")


def _survivor_canon_disqualifier(node: Any) -> str | None:
    """Return the Kernel alias_remove subject-eligibility disqualifier, if any."""
    state = dict(getattr(node, "state", None) or {})
    memory_state = str(state.get("memory_state") or "")
    canon = _node_identity_canon_state(node)
    if memory_state == "merged_away" or canon == "merged_away":
        return "merged_away"
    if canon in {"rejected", "noncanonical_provisional"}:
        return canon
    return None


def _iter_typed_supports(store: Any) -> list[DurableAssertionSupport]:
    supports: list[DurableAssertionSupport] = []
    for value in (store.assertion_support or {}).values():
        if isinstance(value, DurableAssertionSupport):
            supports.append(value)
        elif isinstance(value, dict):
            supports.append(DurableAssertionSupport.model_validate(value))
    return supports


def _candidate_supports_for_subject(
    store: Any, subject_node_id: str
) -> list[DurableAssertionSupport]:
    candidates: list[DurableAssertionSupport] = []
    for support in _iter_typed_supports(store):
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        kind = support.assertion_kind
        if kind not in {None, "alias", "node"}:
            continue
        if support.graph_object_id not in {None, subject_node_id}:
            continue
        candidates.append(support)
    return candidates


def _assertion_semantic_fingerprint(assertion: Any) -> tuple[Any, ...]:
    return (
        assertion.assertion_kind,
        assertion.subject_node_id,
        assertion.target_node_id,
        assertion.predicate,
        assertion.label,
        json.dumps(
            semantic_assertion_value(assertion.value),
            sort_keys=True,
            separators=(",", ":"),
        ),
        assertion.epistemic_kind,
        assertion.visibility,
        assertion.campaign_scope,
        json.dumps(assertion.temporal_scope, sort_keys=True, separators=(",", ":"))
        if assertion.temporal_scope is not None
        else None,
    )


def _assertion_graph_object_id(assertion: Any) -> str:
    return str(assertion.subject_node_id or assertion.target_node_id or "")


def _load_assertions_from_support(
    root: Path,
    support: DurableAssertionSupport,
) -> list[Any]:
    resolved: list[Any] = []
    for contribution_id in support.active_contribution_ids:
        try:
            contribution = load_contribution_record(root, WORLD_ID, contribution_id)
        except FileNotFoundError as exc:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"missing contribution {contribution_id!r}"
            ) from exc
        matched = next(
            (
                candidate
                for candidate in contribution.accepted_assertions
                if candidate.assertion_id == support.assertion_id
            ),
            None,
        )
        if matched is None:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"active contribution {contribution_id!r} does not contain the assertion"
            )
        if getattr(matched, "contribution_id", contribution_id) != contribution_id:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"assertion contribution_id {matched.contribution_id!r} does not "
                f"match active contribution {contribution_id!r}"
            )
        resolved.append(matched)
    if not resolved:
        raise ValueError(
            f"cannot resolve assertion support {support.assertion_id!r} from "
            f"active contributions {list(support.active_contribution_ids)}"
        )
    return resolved


def _assert_support_copies_consistent(
    support: DurableAssertionSupport,
    assertions: list[Any],
) -> None:
    fingerprints = {_assertion_semantic_fingerprint(item) for item in assertions}
    if len(fingerprints) > 1:
        raise ValueError(
            f"cannot resolve assertion support {support.assertion_id!r}: "
            "semantically divergent active copies"
        )
    expected_object_id = support.graph_object_id
    if expected_object_id is None:
        return
    for assertion in assertions:
        actual = _assertion_graph_object_id(assertion)
        if actual != expected_object_id:
            raise ValueError(
                f"cannot resolve assertion support {support.assertion_id!r}: "
                f"graph_object_id {expected_object_id!r} does not match "
                f"assertion object {actual!r}"
            )


def _assertion_lists_alias(assertion: Any, alias: str) -> bool:
    needle = alias.casefold()
    if assertion.assertion_kind == "alias":
        value = dict(assertion.value or {})
        claimed = str(assertion.label or value.get("alias") or "")
        return bool(claimed.strip()) and claimed.casefold() == needle
    if assertion.assertion_kind == "node":
        value = dict(assertion.value or {})
        return any(
            str(item).strip() and str(item).casefold() == needle
            for item in list(value.get("aliases") or [])
        )
    return False


def _independent_support_for_alias(
    store: Any,
    *,
    root: Path,
    subject_node_id: str,
    alias: str,
) -> tuple[bool, str | None]:
    """Return (has_independent_support, integrity_error)."""
    candidates = _candidate_supports_for_subject(store, subject_node_id)
    if not candidates:
        return False, None
    for support in candidates:
        try:
            assertions = _load_assertions_from_support(root, support)
            lists_alias = any(
                (
                    item.subject_node_id == subject_node_id
                    or support.graph_object_id == subject_node_id
                )
                and _assertion_lists_alias(item, alias)
                for item in assertions
            )
            if lists_alias:
                return True, None
            _assert_support_copies_consistent(support, assertions)
            subjects = {item.subject_node_id for item in assertions}
            if subjects != {subject_node_id} and support.graph_object_id == subject_node_id:
                return False, (
                    f"cannot resolve assertion support {support.assertion_id!r}: "
                    f"subject {sorted(subjects)!r} does not match {subject_node_id!r}"
                )
        except ValueError as exc:
            return False, str(exc)
    return False, None


def _keeper_lineage_intact(
    store: Any, keeper: KeeperAlias, *, root: Path
) -> tuple[bool, str]:
    if not _keeper_present(store, keeper):
        return False, f"keeper alias {keeper.alias!r} missing on {keeper.node_id}"
    raw = (store.assertion_support or {}).get(keeper.assertion_id)
    if raw is None:
        return False, (
            f"keeper assertion {keeper.assertion_id} missing for {keeper.alias!r}"
        )
    support = (
        raw
        if isinstance(raw, DurableAssertionSupport)
        else DurableAssertionSupport.model_validate(raw)
    )
    if support.support_state != "supported" or not support.active_contribution_ids:
        return False, (
            f"keeper assertion {keeper.assertion_id} is not actively supported"
        )
    if keeper.contribution_id not in support.active_contribution_ids:
        return False, (
            f"keeper contribution {keeper.contribution_id} is not active for "
            f"{keeper.assertion_id}"
        )
    if support.graph_object_id not in {None, keeper.node_id}:
        return False, (
            f"keeper assertion {keeper.assertion_id} graph_object_id "
            f"{support.graph_object_id!r} does not match {keeper.node_id}"
        )
    bound = (store.contribution_source_payload_sha256 or {}).get(keeper.contribution_id)
    if bound != keeper.source_sha:
        return False, (
            f"keeper source sha mismatch for {keeper.contribution_id}: "
            f"{bound!r} != {keeper.source_sha!r}"
        )
    try:
        contribution = load_contribution_record(root, WORLD_ID, keeper.contribution_id)
    except FileNotFoundError:
        return False, f"keeper contribution {keeper.contribution_id} is missing"
    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    if digest != keeper.source_sha:
        return False, (
            f"keeper contribution file digest mismatch for {keeper.contribution_id}"
        )
    try:
        assertions = _load_assertions_from_support(root, support)
        _assert_support_copies_consistent(support, assertions)
    except ValueError as exc:
        return False, str(exc)
    owns_alias = any(
        item.assertion_id == keeper.assertion_id
        and item.contribution_id == keeper.contribution_id
        and (
            item.subject_node_id == keeper.node_id
            or support.graph_object_id == keeper.node_id
        )
        and _assertion_lists_alias(item, keeper.alias)
        for item in assertions
    )
    if not owns_alias:
        return False, (
            f"locked keeper assertion {keeper.assertion_id} in "
            f"{keeper.contribution_id} does not list {keeper.alias!r}"
        )
    return True, f"keeper_lineage:{keeper.node_id}"


def _structural_preflight(
    store: Any, *, head_revision_id: str, root: Path
) -> tuple[EligibilityState, str | None, list[str], int]:
    diagnostics: list[str] = []
    present_flags: list[bool] = []
    already_flags: list[bool] = []
    redirects = active_identity_redirect_map(store.identity_redirects)
    decisions = _decisions_by_id(store)

    for target in SHADOW_ALIAS_TARGETS:
        node = store.nodes.get(target.survivor_node_id)
        if node is None:
            return (
                "ineligible",
                f"missing survivor {target.survivor_node_id}",
                [f"missing_survivor:{target.survivor_node_id}"],
                0,
            )
        disqualifier = _survivor_canon_disqualifier(node)
        if disqualifier is not None:
            return (
                "ineligible",
                (
                    f"survivor {target.survivor_node_id} is {disqualifier}; "
                    "subject is not a current canonical identity"
                ),
                [f"{disqualifier}_survivor:{target.survivor_node_id}"],
                0,
            )
        alias_present = _alias_present(list(node.aliases), target.alias)
        present_flags.append(alias_present)
        merge = decisions.get(target.merge_decision_id)
        if merge is None or merge.get("decision_kind") != "merge":
            return (
                "ineligible",
                f"missing introducing merge {target.merge_decision_id}",
                [f"missing_merge:{target.merge_decision_id}"],
                0,
            )
        redirect = redirects.get(target.merged_away_node_id)
        if redirect is None or redirect.to_node_id != target.survivor_node_id:
            return (
                "ineligible",
                (
                    f"merged-away {target.merged_away_node_id} does not redirect "
                    f"to {target.survivor_node_id}"
                ),
                [f"redirect_mismatch:{target.merged_away_node_id}"],
                0,
            )
        merged_away = store.nodes.get(target.merged_away_node_id)
        if merged_away is None:
            return (
                "ineligible",
                f"missing merged-away node {target.merged_away_node_id}",
                [f"missing_merged_away:{target.merged_away_node_id}"],
                0,
            )
        away_state = str(merged_away.state.get("memory_state") or "")
        away_canon = str(
            merged_away.state.get("identity_canon_state")
            or merged_away.state.get("canon_state")
            or ""
        )
        if away_state != "merged_away" and away_canon != "merged_away":
            return (
                "ineligible",
                f"{target.merged_away_node_id} is not merged_away",
                [f"not_merged_away:{target.merged_away_node_id}"],
                0,
            )
        matching = _matching_alias_remove(store, target)
        already_flags.append(matching is not None)
        if matching is None and _prior_alias_remove_exists(store, target):
            return (
                "ineligible",
                (
                    f"alias {target.alias!r} on {target.survivor_node_id} has a "
                    "prior active alias_remove outside this package"
                ),
                [f"foreign_alias_remove:{target.survivor_node_id}"],
                0,
            )
        if alias_present:
            has_support, integrity_error = _independent_support_for_alias(
                store,
                root=root,
                subject_node_id=target.survivor_node_id,
                alias=target.alias,
            )
            if integrity_error:
                return (
                    "integrity_failure",
                    integrity_error,
                    [f"support_integrity:{target.survivor_node_id}"],
                    0,
                )
            if has_support:
                return (
                    "ineligible",
                    (
                        f"alias {target.alias!r} on {target.survivor_node_id} has "
                        "independent active semantic support"
                    ),
                    [f"independent_support:{target.survivor_node_id}"],
                    0,
                )
            diagnostics.append(
                f"independent_support_absent:{target.survivor_node_id}"
            )
        diagnostics.append(
            f"target:{target.survivor_node_id}:present={alias_present}"
        )
        if matching is None:
            diagnostics.append(f"no_prior_alias_remove:{target.survivor_node_id}")

    for keeper in KEEPER_ALIASES:
        intact, keeper_diagnostic = _keeper_lineage_intact(
            store, keeper, root=root
        )
        if not intact:
            code = (
                f"missing_keeper:{keeper.node_id}"
                if "missing on" in keeper_diagnostic
                else f"keeper_lineage:{keeper.node_id}"
            )
            return (
                "ineligible",
                keeper_diagnostic,
                [code],
                0,
            )
        diagnostics.append(keeper_diagnostic)

    retired = sum(1 for flag in present_flags if not flag)
    if all(present_flags) and not any(already_flags):
        diagnostics.append(f"head:{head_revision_id}")
        return "eligible", None, diagnostics, 0
    if not any(present_flags) and all(already_flags):
        diagnostics.append("already_applied")
        return "already_applied", None, diagnostics, 6
    return (
        "ineligible",
        "partial or drifted identity-shadow alias_remove state",
        [
            *diagnostics,
            f"present={present_flags}",
            f"package_decisions={already_flags}",
            "preflight_drift",
        ],
        retired,
    )


def get_eldyrwild_identity_shadow_alias_remove_status(
    *,
    root: Path | None = None,
    expected_parent_revision_id: str | None = None,
) -> EldyrwildIdentityShadowAliasRemoveStatus:
    world_root = _resolve_root(root)
    try:
        head, _, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        return EldyrwildIdentityShadowAliasRemoveStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            eligibility="ineligible",
            reason=f"world missing: {exc}",
            expected_parent_revision_id=expected_parent_revision_id,
            diagnostics=["world_missing"],
        )
    head_revision_id = head.head_revision_id
    if (
        expected_parent_revision_id
        and expected_parent_revision_id.strip()
        and head_revision_id != expected_parent_revision_id.strip()
    ):
        return EldyrwildIdentityShadowAliasRemoveStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                f"expected parent {expected_parent_revision_id.strip()!r} is stale; "
                f"current head is {head_revision_id!r}"
            ),
            expected_parent_revision_id=expected_parent_revision_id.strip(),
            keeper_aliases_present=all(
                _keeper_present(store, keeper) for keeper in KEEPER_ALIASES
            ),
            diagnostics=["stale_expected_parent"],
        )
    eligibility, reason, diagnostics, retired = _structural_preflight(
        store, head_revision_id=head_revision_id, root=world_root
    )
    return EldyrwildIdentityShadowAliasRemoveStatus(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        head_revision_id=head_revision_id,
        eligibility=eligibility,
        reason=reason,
        expected_parent_revision_id=(
            expected_parent_revision_id.strip()
            if expected_parent_revision_id and expected_parent_revision_id.strip()
            else head_revision_id
        ),
        retired_alias_count=retired,
        keeper_aliases_present=all(
            _keeper_present(store, keeper) for keeper in KEEPER_ALIASES
        ),
        diagnostics=diagnostics,
    )


def _apply_targets(store: Any, *, world_root: Path) -> tuple[Any, list[str]]:
    decision_ids: list[str] = []
    updated = store
    for target in SHADOW_ALIAS_TARGETS:
        updated, decision = kernel.remove_identity_alias(
            updated,
            world_id=WORLD_ID,
            subject_node_id=target.survivor_node_id,
            alias=target.alias,
            actor=ACTOR,
            reason=retirement_reason(target),
            root=world_root,
        )
        if decision.decision_id != expected_decision_id(target):
            raise EldyrwildIdentityShadowAliasRemoveError(
                (
                    f"decision_id drift for {target.survivor_node_id}: "
                    f"{decision.decision_id} != {expected_decision_id(target)}"
                ),
                code="identity_decision_drift",
            )
        decision_ids.append(decision.decision_id)
    for keeper in KEEPER_ALIASES:
        if not _keeper_present(updated, keeper):
            raise EldyrwildIdentityShadowAliasRemoveError(
                f"keeper alias {keeper.alias!r} disappeared from {keeper.node_id}",
                code="keeper_violation",
            )
    if len(set(decision_ids)) != 6:
        raise EldyrwildIdentityShadowAliasRemoveError(
            "package did not produce six distinct alias_remove decisions",
            code="identity_decision_drift",
        )
    return updated, decision_ids


def apply_eldyrwild_identity_shadow_alias_remove(
    *,
    expected_parent_revision_id: str,
    root: Path | None = None,
    allow_live_world: bool = False,
) -> EldyrwildIdentityShadowAliasRemoveResult:
    """Apply the exact-six package to an exact Eldyrwild parent."""
    if not expected_parent_revision_id or not expected_parent_revision_id.strip():
        raise EldyrwildIdentityShadowAliasRemoveError(
            "expected_parent_revision_id is required",
            code="expected_parent_required",
        )
    expected = expected_parent_revision_id.strip()
    world_root = _resolve_root(root)
    if _is_canonical_live_root(world_root) and not allow_live_world:
        raise EldyrwildIdentityShadowAliasRemoveError(
            "canonical live world root requires allow_live_world=True",
            code="live_world_opt_in_required",
        )

    try:
        head_probe, _, _ = kernel.open_current_world_graph(world_root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        raise EldyrwildIdentityShadowAliasRemoveError(
            f"world missing: {exc}",
            code="ineligible_parent",
        ) from exc
    if head_probe.head_revision_id != expected:
        raise EldyrwildIdentityShadowAliasRemoveError(
            (
                f"expected parent {expected!r} is stale; "
                f"current head is {head_probe.head_revision_id!r}"
            ),
            code="stale_expected_parent",
        )

    status = get_eldyrwild_identity_shadow_alias_remove_status(
        root=world_root,
        expected_parent_revision_id=expected,
    )
    if status.eligibility == "already_applied":
        return EldyrwildIdentityShadowAliasRemoveResult(
            world_id=WORLD_ID,
            expected_parent_revision_id=expected,
            parent_revision_id=expected,
            revision_id=status.head_revision_id,
            published=False,
            eligibility="already_applied",
            decision_ids=[expected_decision_id(target) for target in SHADOW_ALIAS_TARGETS],
            diagnostics=[*status.diagnostics, "already_applied_noop"],
        )
    if status.eligibility != "eligible":
        raise EldyrwildIdentityShadowAliasRemoveError(
            status.reason or "parent is ineligible for identity-shadow alias_remove",
            code="ineligible_parent",
        )

    head_now, _, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    if head_now.head_revision_id != expected:
        raise EldyrwildIdentityShadowAliasRemoveError(
            (
                f"expected parent {expected!r} is stale; "
                f"current head is {head_now.head_revision_id!r}"
            ),
            code="stale_expected_parent",
        )

    try:
        updated, decision_ids = _apply_targets(store, world_root=world_root)
        publish = kernel.publish_world_revision(
            world_root,
            WORLD_ID,
            updated,
            operation_ids=decision_ids,
            expected_parent_revision_id=expected,
        )
    except EldyrwildIdentityShadowAliasRemoveError:
        raise
    except (ValueError, KeyError) as exc:
        raise EldyrwildIdentityShadowAliasRemoveError(
            str(exc),
            code="kernel_rejected",
        ) from exc

    return EldyrwildIdentityShadowAliasRemoveResult(
        world_id=WORLD_ID,
        expected_parent_revision_id=expected,
        parent_revision_id=expected,
        revision_id=publish.revision.revision_id,
        published=True,
        eligibility="eligible",
        decision_ids=decision_ids,
        diagnostics=[*status.diagnostics, "published_exact_six"],
    )
