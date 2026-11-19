"""Closed effect inventory only: no publication, admission, allocation or I/O.

Every accepted graph effect remains unsupported until the native identity,
source and semantic prerequisites are actually closed. Neither output is an
executable plan or a claim about current source/parent/profile authority.
"""

from __future__ import annotations

import hashlib
import json
import math

from apps.live_control_server.models.native_first_world_effects import (
    AliasEffectAccounting,
    EffectBlocker,
    EffectFieldAccounting,
    FirstWorldEffectInventory,
    FirstWorldEffectResult,
    NonPublishingDecisionPacket,
    SummaryEffectAccounting,
    UnsupportedFirstWorldEffects,
)
from graph_memory.worldbuilding_write_plan import (
    WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,
    WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,
    WORLDBUILDING_EXTRACTION_PROFILE,
    WorldbuildingWritePlanError,
    _canonical_effect,
)

MAX_EFFECT_BYTES = 2 * 1024 * 1024
MAX_EFFECT_VALUES = 50_000
MAX_EFFECT_DEPTH = 32


class FirstWorldEffectInputError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _json(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _bounded_json(value) -> str:
    stack, count, string_bytes = [(value, 0)], 0, 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > MAX_EFFECT_VALUES or depth > MAX_EFFECT_DEPTH:
            raise FirstWorldEffectInputError("effect_limits_exceeded")
        if type(item) in (dict, list) and len(item) > MAX_EFFECT_VALUES:
            raise FirstWorldEffectInputError("effect_limits_exceeded")
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise FirstWorldEffectInputError("invalid_json_key")
            stack.extend((child, depth + 1) for pair in item.items() for child in pair)
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if len(item) > MAX_EFFECT_BYTES:
                raise FirstWorldEffectInputError("effect_limits_exceeded")
            try:
                string_bytes += len(item.encode("utf-8"))
            except UnicodeError as exc:
                raise FirstWorldEffectInputError("invalid_json_text") from exc
            if string_bytes > MAX_EFFECT_BYTES:
                raise FirstWorldEffectInputError("effect_limits_exceeded")
        elif type(item) is float:
            if not math.isfinite(item):
                raise FirstWorldEffectInputError("nonfinite_json_value")
        elif type(item) is int:
            if item.bit_length() > 4096:
                raise FirstWorldEffectInputError("effect_limits_exceeded")
        elif item is not None and type(item) is not bool:
            raise FirstWorldEffectInputError("invalid_json_value")
    encoded = _json(value)
    if len(encoded.encode("utf-8")) > MAX_EFFECT_BYTES:
        raise FirstWorldEffectInputError("effect_limits_exceeded")
    return encoded


def _segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _leaves(value, path=""):
    if type(value) is dict and value:
        for key in sorted(value):
            yield from _leaves(value[key], path + "/" + _segment(key))
    elif type(value) is list and value:
        for index, child in enumerate(value):
            yield from _leaves(child, path + "/" + str(index))
    else:
        yield path or "/", value


_NODE_VALUES = frozenset(
    {
        "kind",
        "role",
        "aliases",
        "summary",
        "label",
        "dm_kind",
        "source_domains",
        "evidence",
        "source_artifacts",
        "canon_state",
        "approval_state",
    }
)
_EDGE_VALUES = frozenset(
    {
        "edge_id",
        "predicate",
        "direction",
        "extract_edge_id",
        "dm_predicate",
        "source_domains",
        "evidence",
        "source_artifacts",
        "canon_state",
        "approval_state",
    }
)
_SOURCE_EVIDENCE = frozenset(
    {
        "evidence_ref_id",
        "source_artifact_id",
        "source_revision_id",
        "source_domain",
        "source_span_ref_id",
        "source_ref_id",
        "locator",
        "session_id",
        "campaign_id",
        "uri",
        "evidence_role",
        "can_open_source",
        "can_highlight_span",
        "source_content_sha256",
        "span_content_sha256",
        "span_index_sha256",
    }
)
_SOURCE_ARTIFACT = frozenset(
    {
        "source_artifact_id",
        "source_domain",
        "content_sha256",
        "uri",
        "campaign_id",
        "session_id",
    }
)


def _validate_links(effect):
    accepted = effect["accepted_proposals"]
    rejected = effect["rejected_assertions"]
    by_id = {}
    for rows, state in ((accepted, "accepted"), (rejected, "rejected")):
        for row in rows:
            key = row["assertion_id"]
            if not key.strip() or key in by_id or row["acceptance_state"] != state:
                raise FirstWorldEffectInputError("inconsistent_assertion_inventory")
            by_id[key] = state
    decisions = {row["assertion_id"]: row for row in effect["decision_snapshot"]}
    if set(decisions) != set(effect["candidate_effect_map"]):
        raise FirstWorldEffectInputError("inconsistent_decision_inventory")
    covered = set()
    for candidate, ids in effect["candidate_effect_map"].items():
        decision = decisions[candidate]["decision"]
        if decision in {"create_new", "accept"} and not ids:
            raise FirstWorldEffectInputError("accepted_decision_has_no_effect")
        for identifier in ids:
            if identifier not in by_id or (decision == "reject") != (
                by_id[identifier] == "rejected"
            ):
                raise FirstWorldEffectInputError("inconsistent_decision_inventory")
            if decision == "defer":
                raise FirstWorldEffectInputError("deferred_decision_has_graph_effect")
            if identifier in covered:
                raise FirstWorldEffectInputError("shared_assertion_inventory")
            covered.add(identifier)
    if covered != set(by_id):
        raise FirstWorldEffectInputError("unaccounted_assertion")
    expected_nodes, expected_outcomes, deferred, deferred_nodes = {}, {}, set(), set()
    outcomes = {
        "create_new": "created_new",
        "bind_existing": "human_override",
        "reject": "rejected_by_operator",
        "defer": "deferred_by_operator",
        "accept": "accepted_by_operator",
    }
    for candidate, decision in decisions.items():
        choice, kind = decision["decision"], decision["candidate_kind"]
        if kind != "source_observation":
            expected_outcomes[candidate] = outcomes[choice]
        if kind == "node" and choice in {"create_new", "bind_existing"}:
            expected_nodes[candidate] = (
                candidate if choice == "create_new" else decision["target_node_id"]
            )
        if choice == "defer":
            deferred.add(candidate)
            if kind == "node":
                deferred_nodes.add(candidate)
    if (
        effect["node_id_map"] != expected_nodes
        or effect["identity_outcome_snapshot"] != expected_outcomes
        or set(effect["deferred_candidate_ids"]) != deferred
    ):
        raise FirstWorldEffectInputError("inconsistent_identity_inventory")
    mentions = effect["unresolved_mentions"]
    if {mention["mention_id"] for mention in mentions} != deferred_nodes or any(
        mention["identity_resolution_outcome"] != "deferred_by_operator"
        for mention in mentions
    ):
        raise FirstWorldEffectInputError("inconsistent_deferred_inventory")


def inventory_first_world_native_effects(effect: dict) -> FirstWorldEffectResult:
    sealed = _bounded_json(effect)
    try:
        canonical = _canonical_effect(effect)
    except WorldbuildingWritePlanError as exc:
        raise FirstWorldEffectInputError("invalid_product_effect") from exc
    # A canonical producer packet is required; do not normalize missing/defaulted
    # fields, numeric kinds, aliases or alternate wire spellings behind its digest.
    if _json(canonical) != sealed:
        raise FirstWorldEffectInputError("noncanonical_product_effect")
    meta = canonical["contribution_meta"]
    if (meta["source_kind"], meta["authored_by"], meta["extraction_profile"]) != (
        WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,
        WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,
        WORLDBUILDING_EXTRACTION_PROFILE,
    ):
        raise FirstWorldEffectInputError("unsupported_effect_producer")
    _validate_links(canonical)
    fields, aliases, summaries, blockers = [], [], [], []
    owners = {}
    for candidate, identifiers in canonical["candidate_effect_map"].items():
        for identifier in identifiers:
            owners.setdefault(identifier, []).append(candidate)
    row_context = {}
    for collection in ("accepted_proposals", "rejected_assertions"):
        for index, row in enumerate(canonical[collection]):
            prefix = f"/{collection}/{index}"
            row_context[prefix] = (
                row["assertion_id"],
                tuple(sorted(owners[row["assertion_id"]])),
            )
    roles = {}

    def block(code, path, row_id=None, candidates=()):
        blockers.append(EffectBlocker(code, path, row_id, candidates))

    for index, row in enumerate(canonical["accepted_proposals"]):
        prefix = f"/accepted_proposals/{index}"
        identifier, candidates = row_context[prefix]
        value, kind = row["value"], row["assertion_kind"]
        allowed = (
            _NODE_VALUES
            if kind == "node"
            else _EDGE_VALUES
            if kind == "edge"
            else frozenset()
        )
        if kind not in {"node", "edge"}:
            block(
                "unsupported_graph_effect",
                prefix + "/assertion_kind",
                identifier,
                candidates,
            )
        for key in value:
            if key not in allowed:
                path = prefix + "/value/" + _segment(key)
                block("unsupported_effect_field", path, identifier, candidates)
                roles[path] = "unsupported_field"
        for key in ("evidence", "source_artifacts"):
            rows = value.get(key, [])
            if type(rows) is not list:
                block(
                    "unsupported_effect_field",
                    prefix + "/value/" + key,
                    identifier,
                    candidates,
                )
                continue
            allowed_source = _SOURCE_EVIDENCE if key == "evidence" else _SOURCE_ARTIFACT
            for source_index, source in enumerate(rows):
                path = prefix + f"/value/{key}/{source_index}"
                if type(source) is not dict:
                    block("unsupported_effect_field", path, identifier, candidates)
                else:
                    for field in source:
                        if field not in allowed_source:
                            block(
                                "unsupported_effect_field",
                                path + "/" + _segment(field),
                                identifier,
                                candidates,
                            )
        # Input carries product source operands, not verified native evidence IDs.
        block(
            "native_evidence_binding_required",
            prefix + "/evidence_ref_ids",
            identifier,
            candidates,
        )
        for key in ("visibility", "epistemic_kind", "temporal_scope", "campaign_scope"):
            block(
                "metadata_translation_required",
                prefix + "/" + key,
                identifier,
                candidates,
            )
        if kind == "node":
            label = row["label"] or value.get("label") or row["subject_node_id"]
            raw = value.get("aliases")
            effective = raw if type(raw) is list and raw else [label]
            preserved, seen = [], set()
            if any(type(alias) is not str for alias in effective):
                block(
                    "unsupported_effect_field",
                    prefix + "/value/aliases",
                    identifier,
                    candidates,
                )
            else:
                # Exact classic producer rule: skip blank/casefold duplicates,
                # preserving the first surviving string, not normalized spelling.
                for alias in effective:
                    if alias.strip() and alias.casefold() not in seen:
                        seen.add(alias.casefold())
                        preserved.append(alias)
            aliases.append(
                AliasEffectAccounting(
                    identifier,
                    candidates,
                    row["subject_node_id"] or "",
                    _json(raw),
                    tuple(preserved),
                    tuple(row["evidence_ref_ids"]),
                )
            )
            block(
                "prospective_alias_target_unsupported",
                prefix + "/value/aliases",
                identifier,
                candidates,
            )
            if "summary" in value:
                summaries.append(
                    SummaryEffectAccounting(identifier, _json(value["summary"]))
                )
                block(
                    "summary_disposition_required",
                    prefix + "/value/summary",
                    identifier,
                    candidates,
                )
        elif kind == "edge":
            block(
                "predicate_mapping_required",
                prefix + "/predicate",
                identifier,
                candidates,
            )
    for index, decision in enumerate(canonical["decision_snapshot"]):
        if decision["decision"] == "bind_existing":
            block(
                "existing_identity_unsupported",
                f"/decision_snapshot/{index}",
                candidates=(decision["assertion_id"],),
            )
    identity = canonical.get("identity_authority")
    if identity and any(
        identity[key] for key in ("decisions", "identity_redirects", "alias_owners")
    ):
        block("identity_effect_unsupported", "/identity_authority")
    for path, value in _leaves(canonical):
        context = row_context.get("/".join(path.split("/")[:3]), (None, ()))
        role = "decision_audit"
        if path.startswith("/accepted_proposals/"):
            if "/value/aliases" in path:
                role = "alias_record"
            elif "/value/summary" in path:
                role = "summary_decision"
            elif any(part in path for part in ("/evidence", "/source_")):
                role = "unverified_source_operand"
            elif "/value/kind" in path or "/value/role" in path:
                role = "classification"
            elif path.endswith("/label"):
                role = "name_or_edge_label"
            else:
                role = "requires_native_mapping"
            for blocked_path, blocked_role in roles.items():
                if path == blocked_path or path.startswith(blocked_path + "/"):
                    role = blocked_role
        fields.append(EffectFieldAccounting(path, _json(value), role, *context))
    inventory = FirstWorldEffectInventory(
        sealed,
        hashlib.sha256(sealed.encode("utf-8")).hexdigest(),
        tuple(fields),
        tuple(aliases),
        tuple(summaries),
        len(canonical["accepted_proposals"]),
    )
    if blockers:
        return UnsupportedFirstWorldEffects(
            inventory, tuple(sorted(blockers, key=lambda b: (b.field_path, b.code)))
        )
    return NonPublishingDecisionPacket(inventory)
