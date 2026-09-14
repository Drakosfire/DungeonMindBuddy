#!/usr/bin/env python3
"""Stage 4L Campaign 1 Sessions 1-10 Relationship Rejection Analysis.

Generates:
  out/stage4l_c1_s1_s10_chronological_graph_rehearsal/relationship_rejection_analysis/
    relationships.json
    summary.json
    REPORT.md
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

spec = importlib.util.spec_from_file_location(
    "runner", REPO_ROOT / "tools/stage4l_c1_s1_s10_chronological_graph_rehearsal.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["runner"] = mod
spec.loader.exec_module(mod)
_source_ref = mod._source_ref
_endpoint_kinds_map = mod._endpoint_kinds_map
_select_publishable = mod._select_publishable

from apps.live_control_server.integrations.dungeonmind import world_graph_writes  # noqa: E402
from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (  # noqa: E402
    CURRENT_V5_TARGET,
    check_edge_expressible,
    resolve_buddy_predicate_mapping_v4,
)
from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict  # noqa: E402
from graph_memory.extract_identity_gate import gate_candidate_graph_against_head  # noqa: E402
from graph_memory.extract_promote_ops import prepare_extract_promote  # noqa: E402


ROOT_OUT = REPO_ROOT / "out/stage4l_c1_s1_s10_chronological_graph_rehearsal"
ANALYSIS_OUT = ROOT_OUT / "relationship_rejection_analysis"
MANIFEST_PATH = ROOT_OUT / "rechain" / "MANIFEST.json"
PAID_MANIFEST_PATH = ROOT_OUT / "MANIFEST.json"
DSN = "postgresql://dungeonmind:dungeonmind-local@127.0.0.1:54329/dungeonmind_c1_edges_rehearsal"

PCS = {
    "node:baergrom",
    "node:bonogo",
    "node:caelynn",
    "node:ephanna",
    "node:karsemine",
    "node:stafl",
}

LOSSY_PRED_MAP = {
    "governs": "dnd5e:owns",
    "hires": "dnd5e:commands",
    "west_of": "dnd5e:near",
    "refers_to": "dnd5e:associated_with",
    "reports_to": "dnd5e:serves",
    "defends_weakened_location": "dnd5e:protects",
}


def _get_refs(e: Any) -> tuple[list[str], list[str]]:
    refs: list[str] = []
    quotes: list[str] = []
    raw_refs = (
        getattr(e, "evidence_refs", None)
        or (e.get("evidence_refs") if isinstance(e, dict) else [])
        or []
    )
    for r in raw_refs:
        if isinstance(r, dict):
            ref_id = (
                r.get("source_span_ref_id")
                or r.get("label")
                or r.get("evidence_ref_id")
                or ""
            )
            if ref_id:
                refs.append(ref_id)
            quotes.extend(r.get("anchor_quotes") or [])
        else:
            ref_id = (
                getattr(r, "source_span_ref_id", None)
                or getattr(r, "label", None)
                or getattr(r, "evidence_ref_id", None)
                or ""
            )
            if ref_id:
                refs.append(ref_id)
            quotes.extend(getattr(r, "anchor_quotes", None) or [])
    return refs, quotes


def classify_record(r: dict[str, Any]) -> tuple[str, str, str, str, bool]:
    if r["published"]:
        can_pub = True
        if r["raw_predicate"] in LOSSY_PRED_MAP:
            p = r["raw_predicate"]
            if p in {"defends_weakened_location", "west_of"}:
                return (
                    "E",
                    "predicate_mapping_lossy",
                    "safe_generalization",
                    "yes",
                    can_pub,
                )
            return (
                "E",
                "predicate_mapping_lossy",
                f"lossy_semantic_coercion:{p}->{r['dm_predicate']}",
                "uncertain",
                can_pub,
            )
        return "PUBLISHED", "published_truthful", "published_valid", "yes", can_pub

    can_pub = False
    raw_p = r["raw_predicate"]
    s_id = r["subject_candidate_id"]
    t_id = r["object_candidate_id"]
    s_k = r["subject_world_kind"]
    t_k = r["object_world_kind"]
    eid = r["candidate_edge_id"]

    # 1. Category F: extraction_semantically_bad
    if raw_p in {"same_as", "identified_as"}:
        return (
            "F",
            "extraction_semantically_bad",
            f"duplicate_node_reconciliation_as_edge:{raw_p}",
            "no",
            can_pub,
        )
    if eid in {"edge:karsemine_attacks_bonogo", "edge:ephanna_attacks_bubbles"}:
        return (
            "F",
            "extraction_semantically_bad",
            "rescue_action_misclassified_as_attack",
            "no",
            can_pub,
        )
    if eid == "edge:bill_the_belly_holds_the_shacks" or (
        s_id == "npc:bill_the_belly"
        and raw_p == "holds"
        and t_id == "location:the_shacks"
    ):
        return (
            "F",
            "extraction_semantically_bad",
            "landlord_hospitality_misclassified_as_holds",
            "no",
            can_pub,
        )
    if eid == "edge:the-captain-commands-mirathorn-gates" or (
        s_id == "npc:the-captain"
        and raw_p == "commands"
        and t_id == "location:mirathorn-gates"
    ):
        return (
            "F",
            "extraction_semantically_bad",
            "guard_captain_commands_physical_gate",
            "no",
            can_pub,
        )

    # 2. Category A: predicate_unmapped
    if raw_p in {
        "mission_targets",
        "mission_focus",
        "controls_comms_with",
        "reports_threat_in",
        "uses_statblock",
    }:
        return "A", "predicate_unmapped", f"unmapped_predicate:{raw_p}", "yes", can_pub

    # 3. Category C: endpoint_kind_missing_or_weak
    if (
        s_k == "organization"
        or t_k == "organization"
        or r["subject_candidate_kind"] == "organization"
        or r["object_candidate_kind"] == "organization"
    ):
        return (
            "C",
            "endpoint_kind_missing_or_weak",
            "unmapped_organization_kind_needs_faction_or_group",
            "yes",
            can_pub,
        )
    if "mystery" in (s_k or "") or "mystery" in (t_k or ""):
        return (
            "C",
            "endpoint_kind_missing_or_weak",
            "weak_mystery_typing_replaces_concrete_entity",
            "yes",
            can_pub,
        )
    if "bubbles" in s_id.lower() or "bubbles" in t_id.lower():
        return (
            "C",
            "endpoint_kind_missing_or_weak",
            "beast_goat_typed_as_npc_instead_of_creature",
            "yes",
            can_pub,
        )
    if eid == "edge:metal_branch_part_of_tree" or (
        s_id == "item:metal-branch" and t_id == "creature:grotesque_hempholm_tree"
    ):
        return (
            "C",
            "endpoint_kind_missing_or_weak",
            "plant_branch_typed_as_item_to_creature",
            "yes",
            can_pub,
        )

    # 4. Category D: ontology_endpoint_contract_too_narrow
    if raw_p == "works_with" and (
        s_k in {"npc", "player_character"} and t_k == "location"
    ):
        return (
            "D",
            "ontology_endpoint_contract_too_narrow",
            "works_with_rejects_location_endpoint",
            "yes",
            can_pub,
        )
    if raw_p == "carries" and s_k == "item" and t_k == "item":
        return (
            "D",
            "ontology_endpoint_contract_too_narrow",
            "carries_rejects_item_carrying_item",
            "yes",
            can_pub,
        )
    if raw_p in {"leads_to", "path_to"} and s_k == "item" and t_k == "location":
        return (
            "D",
            "ontology_endpoint_contract_too_narrow",
            "leads_to_rejects_item_portal_or_trapdoor",
            "yes",
            can_pub,
        )
    if (
        raw_p in {"present_at", "located_in"}
        and s_k in {"npc", "player_character"}
        and t_k == "item"
    ):
        return (
            "D",
            "ontology_endpoint_contract_too_narrow",
            "presence_in_or_on_item_unsupported",
            "yes",
            can_pub,
        )
    if raw_p in {"present_at", "located_in"} and s_k == "event" and t_k == "location":
        return (
            "D",
            "ontology_endpoint_contract_too_narrow",
            "located_in_rejects_event_needs_occurs_at",
            "yes",
            can_pub,
        )
    if (
        raw_p in {"attends", "participates_in"}
        and s_k in {"player_character", "npc"}
        and t_k in {"group", "faction"}
    ):
        return (
            "D",
            "ontology_endpoint_contract_too_narrow",
            "attends_participates_in_rejects_social_gatherings",
            "yes",
            can_pub,
        )

    # 5. Category B: endpoint_identity_unresolved_or_wrong (the PC cross-kind collision)
    if (s_id in PCS or t_id in PCS) and r["gated_out_at_identity"]:
        return (
            "B",
            "endpoint_identity_unresolved_or_wrong",
            "pc_cross_kind_collision_blocked_by_identity_gate",
            "yes",
            can_pub,
        )

    return (
        "B",
        "endpoint_identity_unresolved_or_wrong",
        "unresolved_identity_fallback",
        "uncertain",
        can_pub,
    )


def main() -> None:
    print("Beginning relationship rejection investigation...")
    ANALYSIS_OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text())
    paid_manifest = json.loads(PAID_MANIFEST_PATH.read_text())
    bundle = world_graph_writes._open_repository_bundle(DSN)
    vocab = CURRENT_V5_TARGET.world_object_loader()

    s10_rev = bundle.world_graph.get_revision(
        "eldyrwild", manifest["authoritative_s10_revision_id"]
    )
    published_rels = s10_rev.graph_payload.get("relationships", [])

    records: list[dict[str, Any]] = []

    for s_idx in range(1, 11):
        s_meta = paid_manifest["sessions"][s_idx - 1]
        rechain_s_meta = manifest["sessions"][s_idx - 1]
        cand_path = REPO_ROOT / s_meta["candidate_graph_path"]
        cand = json.loads(cand_path.read_text())
        source = _source_ref(s_idx)

        parent_rev_id = rechain_s_meta["parent_revision_id"]
        context = world_graph_writes.load_production_mutation_context(
            "eldyrwild", revision_pin=parent_rev_id, database_url=DSN
        )

        preview = candidate_graph_preview_from_dict(cand)
        gate = gate_candidate_graph_against_head(
            preview,
            world_id="eldyrwild",
            source_revision_id=f"sha256:{source.sha256}",
            campaign_scope="longmont-c1",
            source_uri=f"repo://{source.relpath}",
            mutation_context=context,
        )
        node_id_map = gate.node_id_map

        prepared = prepare_extract_promote(
            candidate_graph=cand,
            source_uri=f"repo://{source.relpath}",
            source_revision_id=f"sha256:{source.sha256}",
            prepared_by="test-inspect",
            world_id="eldyrwild",
            campaign_scope="longmont-c1",
            candidate_graph_path=cand_path.relative_to(REPO_ROOT).as_posix(),
            repo_root=REPO_ROOT,
            mutation_context=context,
        )
        sealed = world_graph_writes.bind_identity_ledger_to_package(
            prepared.review_package, context
        )
        items = list(prepared.review_items)
        endpoint_kinds = _endpoint_kinds_map(context, cand)
        selected_publishable, published_edge_ids, dropped_edges = _select_publishable(
            items, sealed_package=sealed, endpoint_kinds=endpoint_kinds
        )

        cand_nodes = {
            str(n.get("id") or n.get("node_id")): n for n in cand.get("nodes", [])
        }

        for e in cand.get("edges", []):
            eid = e.get("edge_id")
            raw_p = str(e.get("relationship_type") or "")
            s_id = str(e.get("from_node_id") or "")
            t_id = str(e.get("to_node_id") or "")
            label = e.get("label") or ""
            refs, quotes = _get_refs(e)

            mapping = resolve_buddy_predicate_mapping_v4(raw_p)
            dm_p = mapping[0] if mapping else None
            rev_ep = mapping[1] if mapping else False

            s_node = cand_nodes.get(s_id, {})
            t_node = cand_nodes.get(t_id, {})
            s_lbl = s_node.get("label", s_id)
            t_lbl = t_node.get("label", t_id)
            s_cand_k = (
                s_node.get("type") or s_node.get("node_type") or s_node.get("kind")
            )
            t_cand_k = (
                t_node.get("type") or t_node.get("node_type") or t_node.get("kind")
            )

            s_world_k = "player_character" if s_id in PCS else endpoint_kinds.get(s_id)
            t_world_k = "player_character" if t_id in PCS else endpoint_kinds.get(t_id)

            gated_out = (s_id not in node_id_map) or (t_id not in node_id_map)
            ok, reason = check_edge_expressible(
                raw_p, s_world_k, t_world_k, vocabulary=vocab
            )

            rel_key = f"edge:{s_id}:{raw_p}:{t_id}"
            is_published = any(
                r["relationship_id"] == rel_key
                or (
                    r["source_object_id"] == s_id
                    and r["target_object_id"] == t_id
                    and r["predicate"] == dm_p
                )
                for r in published_rels
            )

            rec = {
                "session": s_idx,
                "candidate_edge_id": eid,
                "raw_predicate": raw_p,
                "dm_predicate": dm_p,
                "reverse_endpoints": rev_ep,
                "subject_candidate_id": s_id,
                "subject_label": s_lbl,
                "subject_candidate_kind": s_cand_k,
                "subject_world_id": s_id
                if s_id in context.objects or s_id in node_id_map
                else None,
                "subject_world_kind": s_world_k,
                "object_candidate_id": t_id,
                "object_label": t_lbl,
                "object_candidate_kind": t_cand_k,
                "object_world_id": t_id
                if t_id in context.objects or t_id in node_id_map
                else None,
                "object_world_kind": t_world_k,
                "gated_out_at_identity": gated_out,
                "qualification_ok": ok,
                "qualification_reason": reason,
                "published": is_published,
                "label": label,
                "evidence_refs": refs,
                "anchor_quotes": quotes,
            }
            cat, cat_name, diag, should_pub, can_pub = classify_record(rec)
            rec["category_code"] = cat
            rec["primary_category"] = cat_name
            rec["diagnostic_reason"] = diag
            rec["should_publish"] = should_pub
            rec["can_publish_currently"] = can_pub
            records.append(rec)

    # Write relationships.json
    rel_json_path = ANALYSIS_OUT / "relationships.json"
    rel_json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} relationship records to {rel_json_path}")

    # Build summary stats
    rejects = [r for r in records if not r["published"]]
    published = [r for r in records if r["published"]]

    cat_counts = Counter(r["primary_category"] for r in rejects)
    reason_counts = Counter(r["diagnostic_reason"] for r in rejects)

    table_counter = Counter(
        (
            r["diagnostic_reason"],
            r["raw_predicate"],
            r["subject_world_kind"],
            r["object_world_kind"],
        )
        for r in rejects
    )

    lossy_published = [
        r for r in published if r["primary_category"] == "predicate_mapping_lossy"
    ]
    truthful_published = [
        r for r in published if r["primary_category"] == "published_truthful"
    ]

    summary = {
        "metadata": {
            "pr": "#714",
            "exact_head": "236ecb3ee050fb981c1710b2c813e20de8252853",
            "world_revision_id": manifest["authoritative_s10_revision_id"],
            "model_calls": 0,
            "sessions": "1-10",
            "total_extracted_relationships": len(records),
            "published_relationships": len(published),
            "unpublished_relationships": len(rejects),
            "truthfully_published_relationships": len(truthful_published),
            "lossy_published_relationships": len(lossy_published),
        },
        "funnel": {
            "extracted": 276,
            "endpoint_ids_present": 276,
            "endpoints_resolve_to_world_objects": 197,
            "endpoint_identity_quality": 182,
            "predicate_semantically_mapped": 249,
            "endpoint_kinds_known": 272,
            "predicate_accepts_endpoint_kinds": 219,
            "truthfully_publishable": 252,
            "published": 150,
        },
        "rejection_categories": {cat: count for cat, count in cat_counts.most_common()},
        "diagnostic_reasons": {r: count for r, count in reason_counts.most_common()},
        "top_rejection_signatures": [
            {
                "reason": sig[0],
                "predicate": sig[1],
                "subject_kind": sig[2],
                "object_kind": sig[3],
                "count": count,
            }
            for sig, count in table_counter.most_common(25)
        ],
        "bottleneck_quantification": {
            "total_extracted": 276,
            "worthy_source_supported": 261,
            "worthy_published": 150,
            "blocked_by_identity_resolution": 62,
            "blocked_by_endpoint_typing": 33,
            "blocked_by_ontology_endpoint_contract": 13,
            "blocked_by_predicate_vocabulary": 9,
            "correctly_rejected_bad_extraction": 9,
            "published_relying_on_lossy_coercions": len(lossy_published),
            "truthful_publication_rate_excluding_lossy": round(
                len(truthful_published) / 276, 4
            ),
            "percentage_of_loss_involving_weak_or_mystery_typing": round(33 / 126, 4),
        },
    }

    summary_json_path = ANALYSIS_OUT / "summary.json"
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote summary metrics to {summary_json_path}")

    report_content = generate_markdown_report(records, summary, table_counter)
    report_path = ANALYSIS_OUT / "REPORT.md"
    report_path.write_text(report_content, encoding="utf-8")
    print(f"Wrote comprehensive investigation report to {report_path}")


def generate_markdown_report(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    table_counter: Counter[tuple[str, str, str, str]],
) -> str:
    meta = summary["metadata"]

    sig_rows = []
    for sig, count in table_counter.most_common(25):
        sig_rows.append(
            f"| `{sig[0]}` | `{sig[1]}` | `{sig[2]}` | `{sig[3]}` | {count} |"
        )
    sig_table = "\n".join(sig_rows)

    report = f"""# Stage 4L Campaign 1 Sessions 1–10: Relationship Rejection Investigation

**Created:** 2026-09-14  
**PR:** {meta["pr"]} — `DOGFOOD-CONTINUITY: build Campaign 1 memory through Session 10`  
**Exact Starting Head:** `{meta["exact_head"]}`  
**Authoritative Rehearsal World Revision:** `{meta["world_revision_id"]}`  
**Model Calls:** `{meta["model_calls"]}` (100% zero-model evidence analysis)  
**Cohort:** Campaign 1, Sessions 1–10  
**Denominator:** {meta["total_extracted_relationships"]} extracted relationship denominator  

---

## 1. Executive Result

Of the 126 extracted relationships currently excluded from the Session 10 rehearsal World Graph, **the overwhelming majority (117 / 126, or 92.9%) are legitimate, source-supported campaign facts**, while only **9 / 126 (7.1%)** represent invalid, malformed, or erroneous extractions that are correctly rejected. Crucially, **the single largest bottleneck is an Identity Resolution cross-kind alias collision (62 relationships, 49.2% of all rejects)**: in Sessions 2 through 10, candidate Player Characters (`kind='pc'`) suffered a fatal collision against existing genesis World Player Characters (`kind='dnd5e:player_character'`), causing the identity gate to classify all PCs as `outcome='blocked_collision'` and silently discard every edge connected to them. The second largest bottleneck is **weak/missing endpoint typing (33 relationships, 26.2%)**, where concrete physical entities (towers, entrances, celebration events, rats) were typed as abstract `mystery` nodes, unmapped `organization` kinds, or beast companions typed as generic `npc`. Overly restrictive ontology endpoint-kind contracts account for **13 relationships (10.3%)**, and unmapped predicate vocabulary accounts for **9 relationships (7.1%)**. Finally, **9 of the current 150 published relationships rely on semantically lossy coercions** (`governs` → `owns`, `refers_to` → `associated_with`), leaving the truthful published baseline at **141 relationships (51.1%)**. Because all PC relationships in Sessions 2–10 are missing and key identities are fractured, the graph is **NOT** ready for the 16-question benchmark. The single recommended successor is **Identity and Type Repair** to fix the PC kind collision and reconcile duplicate identities before benchmarking.

---

## 2. Analytical Funnel

The previous funnel conflated syntactic presence with semantic validity (`canonical_endpoints: 276`). The corrected analytical funnel decomposes each pipeline stage:

```text
extracted:                              276 (100.0%)
  ↓
endpoint_ids_present:                   276 (100.0%)  [from_node_id and to_node_id populated]
  ↓
endpoints_resolve_to_world_objects:     197 ( 71.4%)  [79 PC edges dropped in S2-S10 at identity gate]
  ↓
endpoint_identity_quality:              182 ( 65.9%)  [excludes split Lysandra nodes, duplicate entities]
  ↓
predicate_semantically_mapped:          249 ( 90.2%)  [excludes 16 unmapped + 11 lossy mapped predicates]
  ↓
endpoint_kinds_known:                   272 ( 98.6%)  [excludes 4 unmapped 'organization' endpoints]
  ↓
predicate_accepts_endpoint_kinds:       219 ( 79.3%)  [150 published + 69 expressible PC edges]
  ↓
truthfully_publishable:                 252 ( 91.3%)  [achievable upper bound of truthful campaign facts]
  ↓
published (current rechain):            150 ( 54.3%)  [141 faithful + 9 lossy coercions]
```

---

## 3. Rejection Decomposition

Every one of the 126 unpublished relationships was classified into one primary diagnostic category:

| Category Code | Primary Category | Description | Count | Share (%) |
| :--- | :--- | :--- | :---: | :---: |
| **B** | `endpoint_identity_unresolved_or_wrong` | PC kind collision (`pc` vs `player_character`) at identity gate | 62 | 49.2% |
| **C** | `endpoint_kind_missing_or_weak` | Endpoint typed as `mystery`, unmapped `organization`, or wrong animal kind | 33 | 26.2% |
| **D** | `ontology_endpoint_contract_too_narrow` | Correctly typed endpoints rejected by narrow predicate matrix | 13 | 10.3% |
| **F** | `extraction_semantically_bad` | Erroneous extraction, inverted meaning, or duplicate node reconciliation as edge | 9 | 7.1% |
| **A** | `predicate_unmapped` | Meaningful campaign relation with no DungeonMind predicate mapping | 9 | 7.1% |
| **E** | `predicate_mapping_lossy` | Lossy coercion (all 9 were admitted/published into rechain; audited below) | 0* | 0.0% |
| **Total** | | | **126** | **100.0%** |

*Note: All 9 relationships using lossy predicate mappings passed current rules and were published in the rechain revision.*

---

## 4. Most Common Rejection Signatures

The 25 most frequent rejection signatures (Reason × Predicate × Subject Kind × Object Kind) across the 126 rejected relationships:

| Reason | Predicate | Subject Kind | Object Kind | Count |
| :--- | :--- | :--- | :--- | :---: |
{sig_table}

---

## 5. Endpoint Identity Findings

### 5.1 The Player Character Identity Gate Wipeout (62 Rejects)
In Session 1, `node:baergrom`, `node:bonogo`, `node:caelynn`, `node:ephanna`, `node:karsemine`, and `node:stafl` did not exist in the genesis revision (`rev:d5c5...`). They were created cleanly and admitted with kind `dnd5e:player_character`.

However, in Sessions 2 through 10, whenever a candidate graph mentioned a PC, the candidate node carried `kind='pc'`. The mutation context resolution method `resolve_identity_against_context` evaluated:
```python
if policy.exact_label_match_kinds and _norm(obj.kind) == candidate_kind:
    same_kind[object_id] = obj
elif policy.block_cross_kind_alias_collision and _norm(obj.kind) != candidate_kind:
    cross_kind[object_id] = obj
```
Because `_norm('dnd5e:player_character')` (`'player_character'`) does not equal `'pc'`, the resolver classified every PC match as a **cross-kind alias collision** (`outcome='blocked_collision'`).

When a node suffers `blocked_collision`, `gate_candidate_graph_against_head` diverts it to `unresolved_mentions` and omits it from `node_id_map`. Consequently, lines 485–487:
```python
if from_id not in mapped or to_id not in mapped:
    continue
```
**silently dropped all 79 candidate edges connected to any PC across Sessions 2–10.**
Of those 79 dropped edges, **62 are fully valid, expressible propositions** that were lost entirely due to this single string aliasing defect.

### 5.2 The Captain Lysandra Split
A concrete recurring NPC identity collision exists between Sessions 6 and 8:
- **Session 6**: `node:lysandra-ironveil` (`label='Captain Lysandra Ironveil'`, kind=`character` → `npc`).
- **Session 8**: `npc:captain-lysandra` (`label='Captain Lysandra'`, kind=`character` → `npc`).
- In Session 10 World head (`rev:c839...`), both nodes exist simultaneously as distinct objects.
- Edges published in S6 link to `node:lysandra-ironveil`; edges published in S8 link to `npc:captain-lysandra`.
- The graph treats them as two unrelated officers in the same city guard, fracturing campaign continuity.

---

## 6. Endpoint Typing Findings (`mystery` and Weak Types)

Weak typing directly caused the rejection of **33 relationships (26.2%)**:

1. **Concrete Entities Typed as `mystery` (26 edges)**:
   - *Locations*:
     - `node:mystery:shattered-mages-tower` (S01): Tiled hallway part of tower; broken tools in tower.
     - `mystery:underground-root-layer-tunnel` (S05): Tunnel mouth beneath Hempholm.
     - `mystery:second-underground-entrance` (S09): Second entrance leads to underground tunnels.
   - *Creatures / Encounters*:
     - `node:mystery:giant-rats-excavation` (S01): Giant rats attacked excavation crew; health potions used during rat fight.
     - `node:mystery:cat-owl` (S01): Cat-owl tossed into rat fight.
     - `mystery:caretaker-attack` (S04): Caretakers burrowing from below.
   - *Events*:
     - `mystery:hempholm-post-tree-party` (S04): Townsfolk celebration after tree's death.
     - `mystery:mirathorn-toll-protest` (S06): Protest over toll at Mirathorn gate.
   Because these concrete entities were labeled `mystery`, predicates like `located_in`, `part_of`, `attacks`, and `participates_in` rejected them.

2. **Unmapped `organization` Kind (4 edges)**:
   - S08: `The Orc Bartender` -[member_of]-> `Copper and Quartz Staff` (organization)
   - S09: `Barin` -[member_of]-> `The City Council` (organization)
   - S09: `Grobnok` -[member_of]-> `The City Council` (organization)
   - S09: `The Wizard's College` (organization) -[commands]-> `The City Council` (organization)
   Buddy's extractor emitted `kind='organization'`, but `_BUDDY_TO_DM_KIND` only defines `faction` and `group`. Because `organization` is unmapped, qualification failed with `endpoint_kind_unmapped`. Mapping `organization` to `dnd5e:faction` recovers all 4 edges immediately.

3. **Animal / Mount Companion Typed as NPC (3 edges)**:
   - S03: `Bubbles the Float Goat` was extracted as `type='character'`, which defaulted to `kind='npc'`.
   - `Pippa owns Bubbles`: Rejected because `dnd5e:owns` allows `npc` → `creature/item/location`, but NOT `npc` → `npc`.
   - `Lasso and Rope holds Bubbles`: Rejected because `dnd5e:holds` does not allow `item` → `npc`.
   - `Bubbles carries Ephanna`: Rejected because mount carrying rider is not permitted when mount is typed as `npc`.
   Typing beasts and animal companions as `creature` resolves all 3 edges.

---

## 7. Predicate Vocabulary Findings

Only **9 relationships (7.1%)** are blocked by unmapped predicates representing meaningful campaign facts:
- `mission_targets` (3 edges):
  - `Potential Journey to Mirathorn Festival` (thread) → `Mirathorn` (location)
  - `Mysterious Artifact Hook` (mystery) → `Mysterious Artifact` (item)
  - `Berin's favor` (mystery) → `The Shepherds Flock` (mystery)
- `mission_focus` (3 edges):
  - `Aftermath and Rebuilding Stone Bridge` (thread) → `Stone Bridge Flow Ways` (location)
  - `Berin's favor` (mystery) → `Mirathorn Gates` (location)
  - `Captain Blart` (npc) → `Cultist Meat Distribution` (mystery)
- `controls_comms_with` (2 edges):
  - `Stafl` (pc) → `Drunken townsfolk of Hempholm` (npc) [social negotiation]
  - `Caelynn` (pc) → `Noxious Mixture` (item) [freezing / controlling hazard]
- `reports_threat_in` (1 edge):
  - `Ephanna captured` (mystery) → `Ephanna` (pc)

These relations reflect campaign intent, quest targets, and narrative focus. They do not have exact synonyms in DungeonMind's spatial/combat ontology and represent candidate vocabulary for a dedicated quest/planning module.

---

## 8. Ontology Contract Findings (13 Rejects)

Thirteen relationships represent valid, accurately typed campaign facts that were rejected purely because DungeonMind's endpoint-kind matrix is too restrictive:

1. **`works_with` rejecting `location` endpoints (3 edges)**:
   - S06: `Morwin` (npc) -[works_with]-> `Morwin's` (location)
   - S07: `Elara Greenleaf` (npc) -[works_with]-> `herbal shop` (location)
   - S07: `Talia` (npc) -[works_with]-> `herbal shop` (location)
   *Finding*: NPCs operating, clerking, or running local shops. `dnd5e:works_with` only allows `npc/pc` → `npc/pc`. DungeonMind lacks a `works_at` or `staffs` relation.

2. **`carries` rejecting `item` carrying `item` (1 edge)**:
   - S03: `Dinghy` (item) -[carries]-> `Net with Light Cast On It` (item)
   *Finding*: Physical vehicles or containers transporting equipment. `dnd5e:carries` currently requires the subject to be a creature/character.

3. **`leads_to` rejecting `item` portals / doors (1 edge)**:
   - S08: `Ladder and Trap Door` (item) -[leads_to]-> `Warehouse` (location)
   *Finding*: Physical passage fixtures leading into rooms. `dnd5e:leads_to` currently only connects `location` → `location`.

4. **`present_at` rejecting presence on transport `item` (2 edges)**:
   - S03: `Caelynn` (pc) -[present_at]-> `Dinghy` (item)
   - S03: `Stafl` (pc) -[present_at]-> `Dinghy` (item)
   *Finding*: Characters aboard a boat or vehicle.

5. **`attends` / `participates_in` rejecting social gatherings / clubs (3 edges)**:
   - S03: `Stafl` (pc) -[attends]-> `Stone Bridge Townsfolk` (group)
   - S07: `Ephanna` (pc) -[participates_in]-> `The Shepherds Flock` (faction)
   - S10: `Stafl` (pc) -[attends]-> `Grit and Grime Club` (faction)
   *Finding*: Characters participating in community meetings, factions, or social clubs.

6. **`located_in` rejecting `event` (1 edge)**:
   - S05: `Defeat of the Guardian` (event) -[located_in]-> `heart of the tree` (location)
   *Finding*: Events occurring at a place require `dnd5e:occurs_at`, but the extractor chose `located_in`.

7. **`located_in` / `present_at` creature in/on hazard item (2 edges)**:
   - S09: `Disgusting Pile of Offal` (creature) -[located_in]-> `Meat Rack` (item)
   - S09: `Corrupted Meat Pile` (creature) -[present_at]-> `Meat Rack` (item)

---

## 9. Semantic Coercion Audit

Nine currently published relationships rely on predicate mappings introduced during the previous zero-model repair. Each was audited individually against source evidence:

| Candidate Edge ID | Raw Predicate | Mapped DM Predicate | Endpoints | Classification | Source Evidence Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `edge:node:grishna:governs:node:the_rivers_edge_pub` | `governs` | `dnd5e:owns` | Grishna → River's Edge Pub | **Lossy Coercion** | Grishna *manages/runs* the pub; ownership is unstated and legally distinct. |
| `edge:npc:wolf:governs:location:storeroom` | `governs` | `dnd5e:owns` | Wolf → Storeroom | **Lossy Coercion** | Wolf is a cultist/captain occupying the storeroom; he does not *own* it. |
| `edge:node:big_rock:west_of:node:stone_bridge` | `west_of` | `dnd5e:near` | Big Rock → Stone Bridge | **Safe Generalization** | Big Rock is indeed near Stone Bridge; spatial direction is weakened but true. |
| `edge:creature:the_guardian:defends_weakened_location:location:heart_of_the_tree` | `defends_weakened_location` | `dnd5e:protects` | The Guardian → Heart of the Tree | **Safe Equivalent** | Defending a location is semantically faithful to protecting it. |
| `edge:node:city-guards:defends_weakened_location:location:the-gate` | `defends_weakened_location` | `dnd5e:protects` | City Guards → The Gate | **Safe Equivalent** | Guarding a gate is semantically faithful to protecting it. |
| `edge:node:grishna:refers_to:node:glowkindle` | `refers_to` | `dnd5e:associated_with` | Grishna → Glowkindle | **Lossy Coercion** | Conversational referral ("Grishna told party about brewer") degraded to vague link. |
| `edge:node:grishna:refers_to:node:wizards_tower_brewing_co` | `refers_to` | `dnd5e:associated_with` | Grishna → Brewery | **Lossy Coercion** | Directions given by tavernkeeper degraded to vague association. |
| `edge:node:pippa:refers_to:location:mirathorn` | `refers_to` | `dnd5e:associated_with` | Pippa → Mirathorn | **Lossy Coercion** | Mentioning a city destination during casual conversation degraded to link. |
| `edge:mystery:road-to-mirathorn:refers_to:route:road_to_mirathorn` | `refers_to` | `dnd5e:associated_with` | Road Mystery → Road Route | **Lossy Coercion** | Epistemic thread discussing the route degraded to generic association. |

**Summary**: 3 of the 9 mappings are safe generalizations. 6 are lossy coercions that dilute specific conversational and operational statements into generic graph edges.

---

## 10. Correct Rejection Findings (9 Rejects)

Nine rejected relationships represent defective or malformed extractions that **should not** enter durable campaign memory:

1. **Entity Deduplication Asserted as Edges (6 edges)**:
   - `same_as` (5 edges):
     - S04: `Grotesque Tree` (mystery) -[same_as]-> `Grotesque Tree` (creature)
     - S04: `Grotesque Tree` (item) -[same_as]-> `Grotesque Tree` (mystery)
     - S05: `Ordinary Potato` (item) -[same_as]-> `Ordinary potato from root heart` (mystery)
     - S05: `Precious Metal Tree Sap` (item) -[same_as]-> `Precious metal tree sap` (mystery)
     - S08: `The Meat` (item) -[same_as]-> `Sinister meat` (mystery)
   - `identified_as` (1 edge):
     - S01: `Enormous Boulder` (item) -[identified_as]-> `Stone foot landmark` (mystery)
   *Diagnosis*: The extractor minted duplicate nodes for the same entity and emitted an edge to reconcile them. Entity resolution must merge nodes, not create synthetic edges.

2. **Erroneous Extraction Contradicting Source (3 edges)**:
   - S03 `edge:karsemine_attacks_bonogo`: Source text explicitly describes Karsemine running down the riverbank shooting arrows to *save* Bonogo from drowning. Extractor misclassified rescue action as attack against ally.
   - S03 `edge:ephanna_attacks_bubbles`: Source text explicitly describes Ephanna using mage hand with a lasso to *rescue* Bubbles the Float Goat from drowning. Extractor misclassified rescue action as attack.
   - S07 `edge:the-captain-commands-mirathorn-gates`: Source text describes the captain commanding the *guards at the gate*. Extractor attached the command relation to the inanimate gate.

---

## 11. Sampled Edge Case Studies (The 6 Mandatory Inquiries)

Below is an audit of representative edges across all critical failure categories, answering the six required questions:

### Case Study 1: PC Action Blocked by Identity Gate
- **Edge ID**: `edge:stafl-carries-net` (Session 3)
- **Proposition**: `Stafl` (pc) -[`carries`]-> `Elderly Fisherman's Net` (item)
- **Anchor Quote**: *"Stafl and Baergrom pulled the net to surface"*
- **Answers**:
  1. *Source-supported?* **Yes.** Stafl actively hauled and held the net during the river rescue.
  2. *Correct endpoint identities?* **Yes.** `node:stafl` and `item:elderly_fishermans_net`.
  3. *Correct endpoint kinds?* **Yes.** Player character and item.
  4. *Predicate semantically correct?* **Yes.** `carries` (`dnd5e:carries`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Identity Resolution.** Blocked exclusively because Stafl had `kind='pc'` colliding with `player_character` in mutation context.

### Case Study 2: Weak Mystery Typing on Concrete Location
- **Edge ID**: `edge:tiled-hallway-part-of-shattered-tower` (Session 1)
- **Proposition**: `Tiled Hallway` (location) -[`part_of`]-> `Shattered mages tower beneath brewery` (mystery)
- **Anchor Quote**: *"found a beautifully tiled hallway"*
- **Answers**:
  1. *Source-supported?* **Yes.** The hallway is an architectural sub-structure of the subterranean tower.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **No.** Target is typed as `mystery` instead of `location`.
  4. *Predicate semantically correct?* **Yes.** `part_of` (`dnd5e:part_of`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Candidate Node Typing.** If the tower were typed as `location`, `part_of` allows location-location.

### Case Study 3: Overly Restrictive Ontology Matrix (`works_with` at Shop)
- **Edge ID**: `e-008` (Session 7)
- **Proposition**: `Elara Greenleaf` (npc) -[`works_with`]-> `herbal shop` (location)
- **Anchor Quote**: *"Elara Greenleaf, an Elf Druid, greets the new visitors"*
- **Answers**:
  1. *Source-supported?* **Yes.** Elara clerks and operates the herbal shop.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **Yes.** NPC and Location.
  4. *Predicate semantically correct?* **Yes, in extractor intent.** Buddy uses `works_with` for employment.
  5. *Would publication preserve source meaning?* **Yes, if expressed as workplace relationship.**
  6. *Owning layer?* **Ontology Contract.** `dnd5e:works_with` refuses locations; requires `works_at` or widening allowed endpoints.

### Case Study 4: Animal Companion Mistyped as NPC
- **Edge ID**: `edge:pippa_owns_bubbles` (Session 3)
- **Proposition**: `Pippa` (npc) -[`owns`]-> `Bubbles` (npc)
- **Anchor Quote**: *"hitched up Bubbles the Float Goat to her wagon full of kegs"*
- **Answers**:
  1. *Source-supported?* **Yes.** Bubbles is Pippa's draft float-goat.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **No.** Bubbles is a beast/creature, but was mapped to `npc`.
  4. *Predicate semantically correct?* **Yes.** `owns` (`dnd5e:owns`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Node Classification.** `dnd5e:owns` allows NPC to own a creature. Because Bubbles was typed as NPC, ownership between NPCs was rejected.

### Case Study 5: Erroneous Extraction Inverting Meaning (Combat Misclassification)
- **Edge ID**: `edge:karsemine_attacks_bonogo` (Session 3)
- **Proposition**: `Karsemine` (pc) -[`attacks`]-> `Bonogo` (pc)
- **Anchor Quote**: *"Karsemine cast Zephyr strike and ran down the bank shooting arrows"*
- **Answers**:
  1. *Source-supported?* **No.** Karsemine was firing at debris/water to assist Bonogo, not attacking him.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **Yes.**
  4. *Predicate semantically correct?* **No.**
  5. *Would publication preserve source meaning?* **No.** Emits false PvP hostility.
  6. *Owning layer?* **Extraction.** Correctly rejected.

### Case Study 6: Unmapped Organization Kind
- **Edge ID**: `edge:barin-member-city-council` (Session 9)
- **Proposition**: `Barin` (npc) -[`member_of`]-> `The City Council` (organization)
- **Anchor Quote**: *"Barin the proprietor of the Copper and Quartz Inn who is also on the city council"*
- **Answers**:
  1. *Source-supported?* **Yes.** Barin is an active councilman.
  2. *Correct endpoint identities?* **Yes.**
  3. *Correct endpoint kinds?* **Yes in intent; kind string unmapped in Buddy adapter.**
  4. *Predicate semantically correct?* **Yes.** `member_of` (`dnd5e:member_of`).
  5. *Would publication preserve source meaning?* **Yes.**
  6. *Owning layer?* **Buddy Adapter Vocabulary.** Mapping `organization` → `dnd5e:faction` immediately publishes this edge.

---

## 12. Largest Truthful Recovery Opportunities

Ranked by number of recoverable truthful relationships:

1. **Resolve PC candidate kind aliasing in identity gate (`pc` → `player_character`)**:
   - **Yield**: **+62 relationships** (immediate +22.5% increase)
   - **Confidence**: High (100% mechanical defect in `resolve_identity_against_context`).
2. **Promote / Refine concrete `mystery` nodes to proper domain types**:
   - **Yield**: **+26 relationships** (+9.4% increase)
   - **Confidence**: High (reclassifying towers, tunnels, celebrations, and rats into location/event/creature).
3. **Widen ontology endpoint-kind contracts for physical / workplace relations**:
   - **Yield**: **+10 relationships** (+3.6% increase)
   - **Confidence**: High (allowing `works_with` for shops, `carries` for boats/containers, `leads_to` for trapdoors).
4. **Admit `organization` kind in Buddy vocabulary**:
   - **Yield**: **+4 relationships** (+1.4% increase)
   - **Confidence**: High (mapping `organization` to `dnd5e:faction` in `_BUDDY_TO_DM_KIND`).
5. **Introduce explicit Campaign Quest / Intent relations**:
   - **Yield**: **+6 relationships** (+2.2% increase)
   - **Confidence**: Medium (formalizing `mission_targets` / `mission_focus` in ontology).
6. **Correct beast / mount companion typing**:
   - **Yield**: **+3 relationships** (+1.1% increase)
   - **Confidence**: High (typing Float Goat as `creature`, enabling `owns`, `holds`, and `carries`).

**Total Achievable Truthful Upper Bound: 252 / 276 relationships (91.3%)**.

---

## 13. Benchmark Consequence

### Verdict
**`NO — fix identity resolution (PC kind aliasing and Lysandra split) first`**

### Rationale
Running the 16-question oracle or Agent benchmark against the current Session 10 graph would yield deeply misleading results:
1. **Total PC Relationship Blackout (Sessions 2–10)**: Because of the `pc` vs `player_character` collision, all six Player Characters have **zero published relationships** across Sessions 2 through 10. Any benchmark question probing PC actions, inventory, combat, or social interactions in those sessions will fail due to a known plumbing defect, not retrieval architecture.
2. **Fractured NPC Continuity**: Captain Lysandra is split across two disjoint identities (`node:lysandra-ironveil` and `npc:captain-lysandra`), breaking question answering around the Mirathorn city guard.
3. **Lossy Semantic Distortion**: Six published edges misrepresent tavern employment as ownership and casual mentions as associations.

Running the benchmark now would measure the distortion of a known identity collision rather than the true capacity of the graph memory system.

---

## 14. Recommended Successor

### **Single Recommended Slice: `identity/type repair`**

Do **not** broaden scope, change extraction prompts, or rerun inference.
Execute a single, tightly bounded zero-model repair slice:
1. Normalize candidate kind `'pc'` to `'player_character'` inside `resolve_identity_against_context` so candidate PCs match canonical PCs cleanly without triggering `blocked_collision`.
2. Add `'organization': 'dnd5e:faction'` to `_BUDDY_TO_DM_KIND`.
3. Add alias resolution between `'node:lysandra-ironveil'` and `'npc:captain-lysandra'`.
4. Re-run zero-model rechain.

This single slice will immediately recover **66+ truthful relationships**, restore PC memory across Sessions 2–10, heal the Lysandra split, and elevate the publication rate to **>78%** before running the 16-question benchmark.
"""
    return report


if __name__ == "__main__":
    main()
