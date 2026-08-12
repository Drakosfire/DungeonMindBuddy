#!/usr/bin/env python3
"""Build the Eldyrwild relationship semantic closure manifest + child artifacts.

One-time governed authoring tool for the DUNGEONMIND-CUTOVER closure program.
Reads the exact Q4 canonical world (read-only), the immutable adjudication
anchors (A + S25 descendant), and both source-seal fixtures; emits the locked
closure authority artifacts consumed by the closure service:

    graph_data/approved_graph_corrections/eldyrwild/relationship-semantic-closure-v1/
        manifest.json
        source-corrections.json
        compound-decompositions.json
        identity-migrations.json
        unsupported-assertions.json

The generator fails closed if the live Q4 residual set, support cardinalities,
seals, or adjudication rows drift from the sealed 55-row inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locked constants
# ---------------------------------------------------------------------------

WORLD_ID = "eldyrwild"
CLOSURE_ID = "eldyrwild-relationship-semantic-closure-v1"
PRODUCED_AT = "2026-08-12T00:00:00Z"
AUTHORED_BY = "gm"
SOURCE_KIND = "graph_review_authored_assertion"

Q4_REVISION_ID = "rev:3759d8d6a02f09306397918234a2ded2"
Q4_PARENT_REVISION_ID = "rev:ba3abde1bfc3659795bcd77bb55eb9f7"

ARTIFACT_DIR_RELPATH = Path(
    "graph_data/approved_graph_corrections/eldyrwild/relationship-semantic-closure-v1"
)

ADJUDICATION_A_RELPATH = Path(
    "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_adjudication_v1.json"
)
ADJUDICATION_S25_RELPATH = Path(
    "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_descendant_residual_adjudication_v1.json"
)
SEAL_A_RELPATH = Path(
    "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_source_seals_v1.json"
)
SEAL_S25_RELPATH = Path(
    "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_descendant_residual_source_seals_v1.json"
)

EXPECTED_BASE_INVENTORY = {
    "semantic": 366,
    "represented": 311,
    "residual": 55,
    "uses_statblock_mechanics": 3,
    "unadjudicated": 0,
    "dungeonmind_owned": 0,
    "buddy_owned": 55,
}
# After applying the 46 mutable units (and leaving the 9 Kernel-blocked
# kind-miscoding residuals open): 366 - 46 + 3 new atomics = 323 semantic,
# 9 residual, 314 represented.
EXPECTED_FINAL_INVENTORY = {
    "semantic": 323,
    "represented": 314,
    "residual": 9,
    "uses_statblock_mechanics": 3,
}

# ---------------------------------------------------------------------------
# Per-row closure decision table (55 rows).
#
# closure_kind:
#   contradiction_only             - governed contradiction, no replacement
#   contradicts_and_replaces       - single kernel correction restoring one
#                                    source-grounded vocabulary-legal atomic
#   compound_decomposition         - contradict compound + additive contribution
#                                    carrying the source-grounded atomic(s)
#   identity_merge                 - durable identity merge + contradiction of
#                                    the identity edge
#   deferred_buddy_kind_repair     - STOP: Kernel has no governed node-kind
#                                    retype seam; residual stays open until a
#                                    Buddy source-repair successor retypes the
#                                    mistyped endpoint and re-admits the edge
# ---------------------------------------------------------------------------

IDENTITY_UNITS: dict[str, dict[str, str]] = {
    "edge:item:session11:council-headquarters:same_as:loc:the-council:same-place-as": {
        "source_node_id": "item:session11:council-headquarters",
        "target_node_id": "loc:the-council",
        "merge_reason": (
            "Council headquarters and 'the Council' place are the same site; "
            "the kind-correct location identity (broader evidence and reference "
            "authority) survives. Closure unit of eldyrwild-relationship-semantic-closure-v1."
        ),
    },
    "edge:item_enormous_boulder:same_as:item_foot_of_statue": {
        "source_node_id": "item_enormous_boulder",
        "target_node_id": "item_foot_of_statue",
        "merge_reason": (
            "The enormous boulder resolves into the foot of a once enormous "
            "statue; the resolved object identity survives. Closure unit of "
            "eldyrwild-relationship-semantic-closure-v1."
        ),
    },
    "edge:item_session2_hidden_alchemy_room:same_as:location_003": {
        "source_node_id": "item_session2_hidden_alchemy_room",
        "target_node_id": "location_003",
        "merge_reason": (
            "The hidden alchemy room item/location pair is one place; the "
            "kind-correct location identity survives. Closure unit of "
            "eldyrwild-relationship-semantic-closure-v1."
        ),
    },
    "edge:loc:last_warehouse:same_as:loc:chilled_warehouse": {
        "source_node_id": "loc:last_warehouse",
        "target_node_id": "loc:chilled_warehouse",
        "merge_reason": (
            "The last warehouse reached is the chilled warehouse; the "
            "substantive, more-referenced location identity survives. Closure "
            "unit of eldyrwild-relationship-semantic-closure-v1."
        ),
    },
    "edge:loc:underground-entrance:same_as:mystery:session9:second_underground_entrance": {
        "source_node_id": "mystery:session9:second_underground_entrance",
        "target_node_id": "loc:underground-entrance",
        "merge_reason": (
            "The second underground entrance is one durable place; the "
            "location identity survives and the mystery node is the discovery "
            "framing. Closure unit of eldyrwild-relationship-semantic-closure-v1."
        ),
    },
    "edge:obj:session9:scroll_abyssal:identified_as:mystery:session9:scroll_in_strange_language": {
        "source_node_id": "mystery:session9:scroll_in_strange_language",
        "target_node_id": "obj:session9:scroll_abyssal",
        "merge_reason": (
            "The strange-language scroll mystery and the recovered abyssal "
            "scroll item are one object; the durable item identity survives. "
            "Closure unit of eldyrwild-relationship-semantic-closure-v1."
        ),
    },
    "edge:organization:merchant-s-crossroads-apothecary:same_as:loc:crooked-retort": {
        "source_node_id": "organization:merchant-s-crossroads-apothecary",
        "target_node_id": "loc:crooked-retort",
        "merge_reason": (
            "The Session-25 recap identifies the Merchant's Crossroads "
            "apothecary as the Crooked Retort; the kind-correct place identity "
            "survives. Closure unit of eldyrwild-relationship-semantic-closure-v1."
        ),
    },
}

REPLACEMENT_UNITS: dict[str, dict[str, str]] = {
    "edge:group_session24_refugees_of_edge:part_of:loc_3": {
        "replacement_predicate": "displaced_from",
        "replacement_label": "displaced from",
        "unit_note": (
            "Refugees 'from Edge' encodes displacement origin; dnd5e:displaced_from "
            "(group->location) restores the source-grounded durable fact."
        ),
    },
    "edge:item:session17:centipede_meat_creature:leads_to:loc:ceiling": {
        "replacement_predicate": "travels_to",
        "replacement_label": "travels to",
        "unit_note": (
            "The creature climbs toward the ceiling; dnd5e:travels_to (item->location) "
            "restores the source-grounded motion without path-connectivity invention."
        ),
    },
}

DECOMPOSITION_UNITS: dict[str, dict[str, object]] = {
    "edge:node:torvak_hempdealer:reports_threat_in:mystery:session4:hempholm-moving-tree": {
        "atomics": [
            {
                "subject_node_id": "node:torvak_hempdealer",
                "target_node_id": "mystery:session4:hempholm-moving-tree",
                "predicate": "knows_about",
                "label": "knows about",
            }
        ],
        "unit_note": (
            "Torvak tells the party the story of the moving tree; the single "
            "source-grounded atomic is dnd5e:knows_about (npc->mystery). The "
            "compound reporting/threat/place bundle has no other legal atomic."
        ),
    },
}

# Nine residuals whose root defect is a mistyped endpoint kind. Kernel has no
# governed node-kind correction seam (edge-only correct/contradict; additive
# node merges refuse disagreeing fingerprints; existing-node apply ignores
# kind). These rows are inventoried and sealed but NOT mutated by this
# program — contradicting them would delete supported campaign truth while
# leaving the malformed objects in place.
DEFERRED_BUDDY_KIND_REPAIR: dict[str, dict[str, str]] = {
    "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower": {
        "mistyped_node_id": "item_shatter_mages_tower",
        "current_kind": "item",
        "required_kind": "location",
        "unit_note": (
            "STOP: Kernel cannot retype item_shatter_mages_tower item→location. "
            "located_in is source-grounded once the Buddy source-repair successor "
            "retypes the tower; do not contradict this residual."
        ),
    },
    "edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of": {
        "mistyped_node_id": "node:meat_distribution_network_session9",
        "current_kind": "party",
        "required_kind": "location",
        "unit_note": (
            "STOP: Kernel cannot retype the meat-distribution site party→location. "
            "Containment is source-grounded once Buddy retypes the logistics site."
        ),
    },
    "edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9": {
        "mistyped_node_id": "node:meat_distribution_network_session9",
        "current_kind": "party",
        "required_kind": "location",
        "unit_note": (
            "STOP: Kernel cannot retype the meat-distribution site party→location. "
            "part_of is source-grounded once Buddy retypes the logistics site."
        ),
    },
    "edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name": {
        "mistyped_node_id": "mystery_stone_bridge_river_name",
        "current_kind": "mystery",
        "required_kind": "location",
        "unit_note": (
            "STOP: Kernel cannot retype the river mystery→location. contains is "
            "source-grounded once Buddy retypes the river."
        ),
    },
    "edge:node:headmaster_tinkerbright:leads:loc:wizard_college": {
        "mistyped_node_id": "loc:wizard_college",
        "current_kind": "location",
        "required_kind": "faction",
        "unit_note": (
            "STOP: Kernel cannot retype Wizard's College location→faction/group. "
            "leads is source-grounded once Buddy retypes the organized collective."
        ),
    },
    "edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry": {
        "mistyped_node_id": "node:hempholm_folk_revelry",
        "current_kind": "group",
        "required_kind": "event",
        "unit_note": (
            "STOP: Kernel cannot retype hempholm_folk_revelry group→event. "
            "participates_in is source-grounded once Buddy retypes the revelry."
        ),
    },
    "edge:node:torrin_flamescale:serves:loc:guilds:represents": {
        "mistyped_node_id": "loc:guilds",
        "current_kind": "location",
        "required_kind": "faction",
        "unit_note": (
            "STOP: Kernel cannot retype loc:guilds location→faction. serves is "
            "source-grounded once Buddy retypes the Guilds collective."
        ),
    },
    "edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan": {
        "mistyped_node_id": "item:torvak-hemp-caravan",
        "current_kind": "item",
        "required_kind": "group",
        "unit_note": (
            "STOP: Kernel cannot retype torvak-hemp-caravan item→group. member_of "
            "is source-grounded once Buddy retypes the caravan collective."
        ),
    },
    "edge:pc:caelynn:participates_in:node:hempholm_folk_revelry": {
        "mistyped_node_id": "node:hempholm_folk_revelry",
        "current_kind": "group",
        "required_kind": "event",
        "unit_note": (
            "STOP: Kernel cannot retype hempholm_folk_revelry group→event. "
            "participates_in is source-grounded once Buddy retypes the revelry."
        ),
    },
}

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_by_edge(records: list[dict], *, fixture: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for record in records:
        edge_id = record.get("edge_id")
        if not edge_id:
            raise SystemExit(f"{fixture}: record missing edge_id")
        out[edge_id] = record
    return out


def _seal_index(payload: dict, *, fixture: str) -> dict[str, dict]:
    seals = payload.get("seals")
    if not isinstance(seals, list):
        raise SystemExit(f"{fixture}: missing seals list")
    out = {}
    for seal in seals:
        edge_id = seal.get("edge_id")
        if not edge_id:
            raise SystemExit(f"{fixture}: seal missing edge_id")
        out[edge_id] = seal
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--world-root",
        required=True,
        help="DungeomMindBuddy world graph root (read-only; must be at exact Q4 head)",
    )
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parents[1]),
        help="DungeonMind repo root (fixtures + artifact output)",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    world_root = Path(args.world_root).resolve()

    import graph_memory.kernel as kernel  # noqa: PLC0415
    from graph_memory.kernel.contributions import (  # noqa: PLC0415
        compute_contribution_source_payload_sha256,
        create_graph_contribution,
    )
    from graph_memory.kernel.contribution_models import (  # noqa: PLC0415
        GraphContributionAssertion,
        GraphContributionAssertionCorrection,
    )
    from graph_memory.kernel.identity_decisions import (  # noqa: PLC0415
        compute_identity_decision_id,
    )
    from graph_memory.world_supergraph.contribution_store import (  # noqa: PLC0415
        load_contribution_record,
    )

    # ---- 1. Load exact Q4 store (read-only) --------------------------------
    head = kernel.open_world_graph_head(world_root, WORLD_ID)
    if head.head_revision_id != Q4_REVISION_ID:
        raise SystemExit(
            f"world head {head.head_revision_id!r} != exact Q4 {Q4_REVISION_ID!r}; "
            "refusing to author against drift"
        )
    store = kernel.load_world_graph_revision(world_root, WORLD_ID, Q4_REVISION_ID)

    # ---- 2. Load anchors + seals -------------------------------------------
    adj_a = _load_json(repo / ADJUDICATION_A_RELPATH)
    adj_s25 = _load_json(repo / ADJUDICATION_S25_RELPATH)
    seals_a = _load_json(repo / SEAL_A_RELPATH)
    seals_s25 = _load_json(repo / SEAL_S25_RELPATH)

    a_records = _index_by_edge(adj_a["records"], fixture=ADJUDICATION_A_RELPATH.name)
    s25_records = _index_by_edge(adj_s25["records"], fixture=ADJUDICATION_S25_RELPATH.name)
    a_seals = _seal_index(seals_a, fixture=SEAL_A_RELPATH.name)
    s25_seals = _seal_index(seals_s25, fixture=SEAL_S25_RELPATH.name)

    decision_edges = (
        set(IDENTITY_UNITS) | set(REPLACEMENT_UNITS) | set(DECOMPOSITION_UNITS)
    )

    # Full 55-row set: every adjudicated non-admitted residual at Q4 belongs to
    # exactly one closure class in this table.
    from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (  # noqa: PLC0415
        analyze_relationship_effective_conformance_v1,
    )

    eff = analyze_relationship_effective_conformance_v1(
        root=world_root, world_id=WORLD_ID, revision_id=Q4_REVISION_ID
    )
    residual_ids = set(eff.remaining_residual_edge_ids)
    if len(residual_ids) != 55:
        raise SystemExit(f"Q4 residual count {len(residual_ids)} != 55")

    rows: list[dict] = []
    for edge_id in sorted(residual_ids):
        if edge_id in a_records:
            adj = a_records[edge_id]
            authority = "A"
            seal = a_seals.get(edge_id)
        elif edge_id in s25_records:
            adj = s25_records[edge_id]
            authority = "S25"
            seal = s25_seals.get(edge_id)
        else:
            raise SystemExit(f"residual {edge_id} lacks adjudication anchor row")
        if seal is None:
            raise SystemExit(f"residual {edge_id} lacks a source seal")

        edge = store.edges.get(edge_id)
        if edge is None:
            raise SystemExit(f"residual {edge_id} missing from Q4 store")

        support = store.assertion_support or {}

        def _field(row: object, key: str) -> object:
            if isinstance(row, dict):
                return row.get(key)
            return getattr(row, key, None)

        assertion_ids = [
            aid
            for aid, row in support.items()
            if _field(row, "graph_object_id") == edge_id
            and _field(row, "support_state") == "supported"
            and _field(row, "assertion_kind") == "edge"
        ]
        if len(assertion_ids) != 1:
            raise SystemExit(
                f"residual {edge_id} has {len(assertion_ids)} active edge assertions; "
                "closure requires exactly one"
            )
        assertion_id = assertion_ids[0]
        active_contribs = sorted(_field(support[assertion_id], "active_contribution_ids"))
        if not active_contribs:
            raise SystemExit(f"residual {edge_id} assertion has no active support")

        target_contrib = load_contribution_record(
            world_root, WORLD_ID, active_contribs[0]
        )
        target_assertion = next(
            (
                a
                for a in target_contrib.accepted_assertions
                if a.assertion_id == assertion_id
            ),
            None,
        )
        if target_assertion is None:
            raise SystemExit(
                f"residual {edge_id}: {active_contribs[0]} lacks {assertion_id}"
            )

        disposition = adj.get("disposition")
        reason_code = adj.get("reason_code")

        if edge_id in DEFERRED_BUDDY_KIND_REPAIR:
            closure_kind = "deferred_buddy_kind_repair"
        elif edge_id in IDENTITY_UNITS:
            closure_kind = "identity_merge"
        elif edge_id in REPLACEMENT_UNITS:
            closure_kind = "contradicts_and_replaces"
        elif edge_id in DECOMPOSITION_UNITS:
            closure_kind = "compound_decomposition"
        elif disposition == "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP":
            closure_kind = "contradiction_only"
        elif disposition in {"SOURCE_CORRECTION_REQUIRED", "INSUFFICIENT_EVIDENCE"}:
            closure_kind = "contradiction_only"
        else:
            raise SystemExit(
                f"residual {edge_id} has unclosable disposition {disposition!r}"
            )

        # Seal the live target contribution payload against revision-bound digest.
        target_source_payload_sha256 = {
            cid: compute_contribution_source_payload_sha256(
                load_contribution_record(world_root, WORLD_ID, cid)
            )
            for cid in active_contribs
        }

        rows.append(
            {
                "edge_id": edge_id,
                "authority": authority,
                "adjudication": adj,
                "seal": seal,
                "assertion_id": assertion_id,
                "active_contribution_ids": active_contribs,
                "target_source_payload_sha256": target_source_payload_sha256,
                "target_assertion": target_assertion.model_dump(mode="json"),
                "campaign_scope": target_assertion.campaign_scope,
                "disposition": disposition,
                "reason_code": reason_code,
                "closure_kind": closure_kind,
                "edge_shape": {
                    "source": edge.source_node_id,
                    "target": edge.target_node_id,
                    "predicate": edge.predicate,
                    "label": getattr(edge, "label", None),
                },
            }
        )

    # ---- 3. Validate decision-table coverage -------------------------------
    counts = {
        "identity_merge": 0,
        "contradicts_and_replaces": 0,
        "compound_decomposition": 0,
        "contradiction_only": 0,
        "deferred_buddy_kind_repair": 0,
    }
    for row in rows:
        counts[row["closure_kind"]] += 1
    expected_counts = {
        "identity_merge": 7,
        "contradicts_and_replaces": 2,
        "compound_decomposition": 1,
        "contradiction_only": 36,
        "deferred_buddy_kind_repair": 9,
    }
    if counts != expected_counts:
        raise SystemExit(f"closure-kind counts {counts} != {expected_counts}")
    if set(DEFERRED_BUDDY_KIND_REPAIR) - set(r["edge_id"] for r in rows):
        raise SystemExit("deferred kind-repair table references non-residual edges")
    if decision_edges - set(r["edge_id"] for r in rows):
        raise SystemExit("decision table references non-residual edges")

    # ---- 4. Order units (mutable first by disposition, deferred last) ------
    disposition_rank = {
        "IDENTITY_NOT_RELATIONSHIP": 0,
        "SOURCE_CORRECTION_REQUIRED": 1,
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": 2,
        "INSUFFICIENT_EVIDENCE": 3,
    }
    rows.sort(
        key=lambda r: (
            1 if r["closure_kind"] == "deferred_buddy_kind_repair" else 0,
            disposition_rank[r["disposition"]],
            r["edge_id"],
        )
    )

    # ---- 5. Build per-unit closure records + contribution payloads ----------
    def _correction_contribution(row: dict, unit_key: str) -> dict:
        corrections = [
            GraphContributionAssertionCorrection(
                correction_kind="contradicts",
                target_contribution_id=cid,
                target_assertion_id=row["assertion_id"],
                replacement_assertion_id=None,
            )
            for cid in row["active_contribution_ids"]
        ]
        contrib = create_graph_contribution(
            world_id=WORLD_ID,
            source_kind=SOURCE_KIND,
            source_artifact_id=f"graph-native:eldyrwild-correction:{CLOSURE_ID}:{unit_key}",
            source_revision_id=f"correction:eldyrwild:{CLOSURE_ID}:{unit_key}",
            extraction_profile=None,
            campaign_scope=row["campaign_scope"],
            assertion_corrections=corrections,
            authored_by=AUTHORED_BY,
            produced_at=PRODUCED_AT,
        )
        return contrib.model_dump(mode="json")

    def _replacement_assertion(row: dict, spec: dict[str, str]) -> GraphContributionAssertion:
        original = row["target_assertion"]
        value = dict(original["value"])
        value["predicate"] = spec["replacement_predicate"]
        value["edge_id"] = (
            f"edge:{original['subject_node_id']}:{spec['replacement_predicate']}"
            f":{original['target_node_id']}"
        )
        return GraphContributionAssertion.model_validate(
            {
                **{k: v for k, v in original.items() if k != "assertion_id"},
                "assertion_id": "assertion:pending",
                "predicate": spec["replacement_predicate"],
                "label": spec["replacement_label"],
                "value": value,
                "contribution_id": "pending",
            }
        )

    def _replacement_contribution(row: dict, unit_key: str, spec: dict[str, str]) -> dict:
        replacement = _replacement_assertion(row, spec)
        correction = GraphContributionAssertionCorrection(
            correction_kind="contradicts_and_replaces",
            target_contribution_id=row["active_contribution_ids"][0],
            target_assertion_id=row["assertion_id"],
            replacement_assertion_id=replacement.assertion_id,
        )
        contrib = create_graph_contribution(
            world_id=WORLD_ID,
            source_kind=SOURCE_KIND,
            source_artifact_id=f"graph-native:eldyrwild-correction:{CLOSURE_ID}:{unit_key}",
            source_revision_id=f"correction:eldyrwild:{CLOSURE_ID}:{unit_key}",
            extraction_profile=None,
            campaign_scope=row["campaign_scope"],
            accepted_assertions=[replacement],
            assertion_corrections=[correction],
            authored_by=AUTHORED_BY,
            produced_at=PRODUCED_AT,
        )
        return contrib.model_dump(mode="json")

    def _additive_contribution(row: dict, unit_key: str, atomics: list[dict[str, str]]) -> dict:
        original = row["target_assertion"]
        assertions = []
        for atomic in atomics:
            value = dict(original["value"])
            value["predicate"] = atomic["predicate"]
            value["edge_id"] = (
                f"edge:{atomic['subject_node_id']}:{atomic['predicate']}"
                f":{atomic['target_node_id']}"
            )
            assertions.append(
                GraphContributionAssertion.model_validate(
                    {
                        **{k: v for k, v in original.items() if k != "assertion_id"},
                        "assertion_id": "assertion:pending",
                        "subject_node_id": atomic["subject_node_id"],
                        "target_node_id": atomic["target_node_id"],
                        "predicate": atomic["predicate"],
                        "label": atomic["label"],
                        "value": value,
                        "contribution_id": "pending",
                    }
                )
            )
        contrib = create_graph_contribution(
            world_id=WORLD_ID,
            source_kind=SOURCE_KIND,
            source_artifact_id=f"graph-native:eldyrwild-correction:{CLOSURE_ID}:{unit_key}:atomics",
            source_revision_id=f"correction:eldyrwild:{CLOSURE_ID}:{unit_key}:atomics",
            extraction_profile=None,
            campaign_scope=row["campaign_scope"],
            accepted_assertions=assertions,
            authored_by=AUTHORED_BY,
            produced_at=PRODUCED_AT,
        )
        return contrib.model_dump(mode="json")

    def _with_digest(payload: dict) -> dict:
        from graph_memory.kernel.contribution_models import (  # noqa: PLC0415
            GraphContribution as GC,
        )

        model = GC.model_validate(payload)
        digest = compute_contribution_source_payload_sha256(model)
        out = model.model_dump(mode="json")
        out["source_payload_sha256"] = digest
        return out

    child_files: dict[str, list[dict]] = {
        "source-corrections": [],
        "compound-decompositions": [],
        "identity-migrations": [],
        "unsupported-assertions": [],
    }
    child_of_disposition = {
        "SOURCE_CORRECTION_REQUIRED": "source-corrections",
        "COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP": "compound-decompositions",
        "IDENTITY_NOT_RELATIONSHIP": "identity-migrations",
        "INSUFFICIENT_EVIDENCE": "unsupported-assertions",
    }

    units: list[dict] = []
    operation_plan: list[dict] = []
    global_op_ordinal = 0
    for ordinal, row in enumerate(rows, start=1):
        unit_id = f"closure-unit:{ordinal:03d}"
        unit_key = f"u{ordinal:03d}"
        edge_id = row["edge_id"]
        kind = row["closure_kind"]
        operations: list[dict] = []
        contributions: dict[str, dict] = {}
        notes: list[str] = []

        if kind == "deferred_buddy_kind_repair":
            spec = DEFERRED_BUDDY_KIND_REPAIR[edge_id]
            notes.append(spec["unit_note"])
            unit = {
                "unit_id": unit_id,
                "ordinal": ordinal,
                "edge_id": edge_id,
                "authority": row["authority"],
                "disposition": row["disposition"],
                "reason_code": row["reason_code"],
                "closure_kind": kind,
                "deferred": True,
                "mistyped_node_id": spec["mistyped_node_id"],
                "current_kind": spec["current_kind"],
                "required_kind": spec["required_kind"],
                "edge_shape": row["edge_shape"],
                "target_assertion_id": row["assertion_id"],
                "target_contribution_ids": row["active_contribution_ids"],
                "target_source_payload_sha256": row["target_source_payload_sha256"],
                "rationale": row["adjudication"].get("rationale"),
                "next_action": row["adjudication"].get("next_action"),
                "seal": row["seal"],
                "operations": [],
                "notes": notes,
            }
            units.append(unit)
            child_files[child_of_disposition[row["disposition"]]].append(
                {"unit": unit, "contributions": {}}
            )
            continue

        if kind == "contradiction_only":
            payload = _with_digest(_correction_contribution(row, unit_key))
            contributions[payload["contribution_id"]] = payload
            operations.append(
                {
                    "op": "contradict",
                    "contribution_id": payload["contribution_id"],
                    "source_payload_sha256": payload["source_payload_sha256"],
                }
            )
        elif kind == "contradicts_and_replaces":
            spec = REPLACEMENT_UNITS[edge_id]
            if len(row["active_contribution_ids"]) != 1:
                raise SystemExit(
                    f"{edge_id}: replacement requires exactly one active support"
                )
            payload = _with_digest(_replacement_contribution(row, unit_key, spec))
            contributions[payload["contribution_id"]] = payload
            operations.append(
                {
                    "op": "correct",
                    "contribution_id": payload["contribution_id"],
                    "source_payload_sha256": payload["source_payload_sha256"],
                }
            )
            notes.append(spec["unit_note"])
        elif kind == "compound_decomposition":
            spec = DECOMPOSITION_UNITS[edge_id]
            payload = _with_digest(_correction_contribution(row, unit_key))
            contributions[payload["contribution_id"]] = payload
            operations.append(
                {
                    "op": "contradict",
                    "contribution_id": payload["contribution_id"],
                    "source_payload_sha256": payload["source_payload_sha256"],
                }
            )
            additive = _with_digest(
                _additive_contribution(row, unit_key, spec["atomics"])  # type: ignore[arg-type]
            )
            contributions[additive["contribution_id"]] = additive
            operations.append(
                {
                    "op": "merge_additive",
                    "contribution_id": additive["contribution_id"],
                    "source_payload_sha256": additive["source_payload_sha256"],
                }
            )
            notes.append(str(spec["unit_note"]))
        elif kind == "identity_merge":
            spec = IDENTITY_UNITS[edge_id]
            payload = _with_digest(_correction_contribution(row, unit_key))
            contributions[payload["contribution_id"]] = payload
            operations.append(
                {
                    "op": "contradict",
                    "contribution_id": payload["contribution_id"],
                    "source_payload_sha256": payload["source_payload_sha256"],
                }
            )
            expected_decision_id = compute_identity_decision_id(
                world_id=WORLD_ID,
                decision_kind="merge",
                subject_node_id=spec["source_node_id"],
                target_node_id=spec["target_node_id"],
                alias=None,
                source_candidate_id=None,
                reason=spec["merge_reason"],
            )
            operations.append(
                {
                    "op": "identity_merge",
                    "source_node_id": spec["source_node_id"],
                    "target_node_id": spec["target_node_id"],
                    "merge_reason": spec["merge_reason"],
                    "expected_decision_id": expected_decision_id,
                }
            )
        else:  # pragma: no cover - guarded above
            raise SystemExit(f"unknown closure kind {kind}")

        for local_index, op in enumerate(operations):
            global_op_ordinal += 1
            op["op_ordinal"] = global_op_ordinal
            op["unit_id"] = unit_id
            op["unit_op_index"] = local_index
            operation_plan.append(
                {
                    "op_ordinal": global_op_ordinal,
                    "unit_id": unit_id,
                    "unit_op_index": local_index,
                    "op": op["op"],
                    "contribution_id": op.get("contribution_id"),
                    "source_payload_sha256": op.get("source_payload_sha256"),
                    "expected_decision_id": op.get("expected_decision_id"),
                }
            )

        unit = {
            "unit_id": unit_id,
            "ordinal": ordinal,
            "edge_id": edge_id,
            "authority": row["authority"],
            "disposition": row["disposition"],
            "reason_code": row["reason_code"],
            "closure_kind": kind,
            "deferred": False,
            "edge_shape": row["edge_shape"],
            "target_assertion_id": row["assertion_id"],
            "target_contribution_ids": row["active_contribution_ids"],
            "target_source_payload_sha256": row["target_source_payload_sha256"],
            "rationale": row["adjudication"].get("rationale"),
            "next_action": row["adjudication"].get("next_action"),
            "seal": row["seal"],
            "operations": operations,
            "notes": notes,
        }
        units.append(unit)
        child_files[child_of_disposition[row["disposition"]]].append(
            {"unit": unit, "contributions": contributions}
        )

    # ---- 6. Emit artifacts --------------------------------------------------
    out_dir = repo / ARTIFACT_DIR_RELPATH
    out_dir.mkdir(parents=True, exist_ok=True)

    child_index: dict[str, dict] = {}
    for name, entries in child_files.items():
        payload = {
            "schema": f"dmb_eldyrwild_relationship_semantic_closure_{name.replace('-', '_')}_v1",
            "closure_id": CLOSURE_ID,
            "produced_at": PRODUCED_AT,
            "unit_count": len(entries),
            "entries": entries,
        }
        text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
        (out_dir / f"{name}.json").write_text(text, encoding="utf-8")
        child_index[name] = {
            "path": f"{name}.json",
            "sha256": _sha256_text(text),
            "unit_count": len(entries),
        }

    deferred_edge_ids = sorted(
        u["edge_id"] for u in units if u["closure_kind"] == "deferred_buddy_kind_repair"
    )
    mutable_units = [u for u in units if not u.get("deferred")]
    manifest = {
        "schema": "dmb_eldyrwild_relationship_semantic_closure_manifest_v1",
        "closure_id": CLOSURE_ID,
        "world_id": WORLD_ID,
        "produced_at": PRODUCED_AT,
        "authored_by": AUTHORED_BY,
        "base_revision_id": Q4_REVISION_ID,
        "base_parent_revision_id": Q4_PARENT_REVISION_ID,
        "expected_base_inventory": EXPECTED_BASE_INVENTORY,
        "expected_final_inventory": EXPECTED_FINAL_INVENTORY,
        "unit_count": len(units),
        "mutable_unit_count": len(mutable_units),
        "deferred_unit_count": len(deferred_edge_ids),
        "deferred_residual_edge_ids": deferred_edge_ids,
        "operation_count": len(operation_plan),
        "operation_plan": operation_plan,
        "unit_order": [u["unit_id"] for u in units],
        "artifacts": child_index,
        "units": units,
    }
    manifest_text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    (out_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")

    print(f"units: {len(units)} (mutable={len(mutable_units)} deferred={len(deferred_edge_ids)})")
    print(f"operations: {len(operation_plan)}")
    print(f"closure kinds: {counts}")
    for name, info in child_index.items():
        print(f"  {name}.json: {info['unit_count']} units sha256={info['sha256'][:16]}…")
    print(f"manifest sha256={_sha256_text(manifest_text)}")
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
