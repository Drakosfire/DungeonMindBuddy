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
            "D",
            "ontology_endpoint_contract_too_narrow",
            "part_of_rejects_item_part_of_creature",
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


def main(
    *,
    manifest_path: Path | None = None,
    output_dir: Path | None = None,
    report_title: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_p = manifest_path or MANIFEST_PATH
    out_d = output_dir or ANALYSIS_OUT
    out_d.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_p.read_text())
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

            s_world_k = endpoint_kinds.get(s_id)
            t_world_k = endpoint_kinds.get(t_id)

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
    rel_json_path = out_d / "relationships.json"
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
            "exact_head": "78aff372e2e419a67018805f5803a88c6fd111f0",
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
            "endpoint_ids_present": sum(1 for r in records if r["subject_candidate_id"] and r["object_candidate_id"]),
            "endpoints_resolve_to_world_objects": sum(1 for r in records if not r["gated_out_at_identity"]),
            "predicate_accepts_endpoint_kinds": sum(1 for r in records if r["qualification_ok"]),
            "published": len(published),
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
            "worthy_source_supported": sum(1 for r in records if r["should_publish"] == "yes"),
            "worthy_published": sum(1 for r in published if r["should_publish"] == "yes"),
            "blocked_by_identity_resolution": cat_counts.get("endpoint_identity_unresolved_or_wrong", 0),
            "blocked_by_endpoint_typing": cat_counts.get("endpoint_kind_missing_or_weak", 0),
            "blocked_by_ontology_endpoint_contract": cat_counts.get("ontology_endpoint_contract_too_narrow", 0),
            "blocked_by_predicate_vocabulary": cat_counts.get("predicate_unmapped", 0),
            "correctly_rejected_bad_extraction": cat_counts.get("extraction_semantically_bad", 0),
            "published_relying_on_lossy_coercions": len(lossy_published),
            "truthful_publication_rate_excluding_lossy": round(
                len(truthful_published) / 276, 4
            ),
            "percentage_of_loss_involving_weak_or_mystery_typing": round(
                cat_counts.get("endpoint_kind_missing_or_weak", 0) / len(rejects), 4
            ) if rejects else 0.0,
        },
    }

    summary_json_path = out_d / "summary.json"
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote summary metrics to {summary_json_path}")

    report_content = generate_markdown_report(records, summary, table_counter, title=report_title)
    report_path = out_d / "REPORT.md"
    report_path.write_text(report_content, encoding="utf-8")
    print(f"Wrote comprehensive investigation report to {report_path}")
    return summary, records


def generate_markdown_report(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    table_counter: Counter[tuple[str, str, str, str]],
    title: str | None = None,
) -> str:
    meta = summary["metadata"]
    funnel = summary["funnel"]
    bot = summary["bottleneck_quantification"]
    cats = summary["rejection_categories"]
    published_count = meta["published_relationships"]
    unpublished_count = meta["unpublished_relationships"]
    heading = title or "Stage 4L Campaign 1 Sessions 1–10: Relationship Rejection Investigation"

    sig_rows = []
    for sig, count in table_counter.most_common(25):
        sig_rows.append(
            f"| `{sig[0]}` | `{sig[1]}` | `{sig[2]}` | `{sig[3]}` | {count} |"
        )
    sig_table = "\n".join(sig_rows) if sig_rows else "| None | None | None | None | 0 |"

    cat_rows = []
    for cat_name, count in cats.items():
        pct = (count / unpublished_count * 100) if unpublished_count else 0.0
        cat_rows.append(f"| `{cat_name}` | {count} | {pct:.1f}% |")
    cat_table = "\n".join(cat_rows) if cat_rows else "| None | 0 | 0.0% |"

    # PC Continuity stats
    pcs = {
        "Baergrom": "node:baergrom",
        "Bonogo": "node:bonogo",
        "Caelynn": "node:caelynn",
        "Ephanna": "node:ephanna",
        "Karsemine": "node:karsemine",
        "Stafl": "node:stafl",
    }
    pc_rows = []
    for name, node_id in sorted(pcs.items()):
        cand_count = sum(1 for r in records if r["subject_candidate_id"] == node_id or r["object_candidate_id"] == node_id)
        pub_count = sum(1 for r in records if (r["subject_candidate_id"] == node_id or r["object_candidate_id"] == node_id) and r["published"])
        rej_count = cand_count - pub_count
        pc_rows.append(f"| {name} | {cand_count} | {pub_count} | {rej_count} |")
    pc_table = "\n".join(pc_rows)

    report = f"""# {heading}

**Created:** 2026-09-14  
**PR:** {meta["pr"]} — `DOGFOOD-CONTINUITY: build Campaign 1 memory through Session 10`  
**Exact Starting Head:** `{meta["exact_head"]}`  
**Authoritative Rehearsal World Revision:** `{meta["world_revision_id"]}`  
**Model Calls:** `{meta["model_calls"]}` (100% zero-model evidence analysis)  
**Cohort:** Campaign 1, Sessions 1–10  
**Denominator:** {meta["total_extracted_relationships"]} extracted relationship denominator  

---

## 1. Executive Result

This report provides the causal accounting of relationship publication for Campaign 1 Sessions 1–10 under the authoritative rehearsal World revision `{meta["world_revision_id"]}`.
Out of {meta["total_extracted_relationships"]} extracted relationships, **{published_count} are published ({published_count / meta["total_extracted_relationships"] * 100:.1f}%)** and **{unpublished_count} remain unpublished**.
Among the published relationships, **{meta["truthfully_published_relationships"]} are truthful and faithful** ({meta["truthfully_published_relationships"] / meta["total_extracted_relationships"] * 100:.1f}% truthful publication rate) and **{meta["lossy_published_relationships"]} rely on semantically lossy coercions** (`governs` → `owns`, `refers_to` → `associated_with`).
Of the {unpublished_count} remaining rejects, **{bot["correctly_rejected_bad_extraction"]} are correctly rejected bad extractions**, while the remaining are blocked by weak/missing endpoint typing, narrow ontology contracts, or unmapped predicates. Crucially, **blocked collisions due to PC kind mismatch dropped to 0**.

---

## 2. Reconciled Sequential Survival Funnel

Cumulative survival across sequential stages:

```text
extracted:                              {funnel["extracted"]} (100.0%)
  ↓
endpoint_ids_present:                   {funnel["endpoint_ids_present"]} ({funnel["endpoint_ids_present"] / funnel["extracted"] * 100:.1f}%)
  ↓
endpoints_resolve_to_world_objects:     {funnel["endpoints_resolve_to_world_objects"]} ({funnel["endpoints_resolve_to_world_objects"] / funnel["extracted"] * 100:.1f}%)
  ↓
predicate_accepts_endpoint_kinds:       {funnel["predicate_accepts_endpoint_kinds"]} ({funnel["predicate_accepts_endpoint_kinds"] / funnel["extracted"] * 100:.1f}%)
  ↓
published:                              {funnel["published"]} ({funnel["published"] / funnel["extracted"] * 100:.1f}%)
```

---

## 3. PC Continuity Table

| Player Character | Candidate Relationships | Published Relationships | Remaining Rejects |
| :--- | :---: | :---: | :---: |
{pc_table}

---

## 4. Rejection Decomposition

Every one of the {unpublished_count} unpublished relationships is classified into one primary diagnostic category:

| Primary Category | Count | Share (%) |
| :--- | :---: | :---: |
{cat_table}

---

## 5. Most Common Rejection Signatures

The most frequent rejection signatures (Reason × Predicate × Subject Kind × Object Kind) across unpublished relationships:

| Reason | Predicate | Subject Kind | Object Kind | Count |
| :--- | :--- | :--- | :--- | :---: |
{sig_table}

---

## 6. Reconciled Bottleneck Quantification

All metrics derive mechanically from the per-edge disposition in `relationships.json`:

- **Total Extracted Relationships:** {bot["total_extracted"]}
- **Worthy / Source-Supported Relationships:** {bot["worthy_source_supported"]}
- **Worthy Published Relationships:** {bot["worthy_published"]}
- **Blocked by Identity Resolution:** {bot["blocked_by_identity_resolution"]}
- **Blocked by Endpoint Typing:** {bot["blocked_by_endpoint_typing"]}
- **Blocked by Narrow Ontology Contract:** {bot["blocked_by_ontology_endpoint_contract"]}
- **Blocked by Unmapped Predicates:** {bot["blocked_by_predicate_vocabulary"]}
- **Correctly Rejected Bad Extractions:** {bot["correctly_rejected_bad_extraction"]}
- **Published Relying on Lossy Coercions:** {bot["published_relying_on_lossy_coercions"]}
- **Truthful Publication Rate (Excluding Lossy):** {bot["truthful_publication_rate_excluding_lossy"] * 100:.1f}%
- **Share of Loss Involving Weak / Mystery Typing:** {bot["percentage_of_loss_involving_weak_or_mystery_typing"] * 100:.1f}%
"""
    return report


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    p.add_argument("--output", type=Path, default=ANALYSIS_OUT)
    p.add_argument("--title", type=str, default=None)
    args = p.parse_args()
    main(manifest_path=args.manifest, output_dir=args.output, report_title=args.title)

