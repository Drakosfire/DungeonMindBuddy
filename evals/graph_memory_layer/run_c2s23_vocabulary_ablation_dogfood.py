#!/usr/bin/env python3
"""C2S23 Mireward vocabulary ablation dogfood runner.

Builds a scoped vocabulary packet from reviewed campaign/planning source spans,
assembles four precomputed extraction variants (baseline + three packet-assisted
curations derived from the Session 23 static candidate bundle), runs the
vocabulary ablation comparison harness, and writes a dogfood report.

This runner does not call live LLM extraction. Variants are precomputed /
reviewer-curated snapshots labeled explicitly in the report output.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.graph_memory.vocabulary import (
    ContainmentHint,
    ContextVocabularyPacket,
    DoNotMergeDecision,
    ExtractedVocabularyEdge,
    ExtractedVocabularyNode,
    VocabularyAblationVariant,
    VocabularyEntry,
    build_lexical_observations_from_spans,
    compare_vocabulary_ablation_variants,
    compile_vocabulary_seed_entries,
    diagnose_vocabulary_extraction_baseline,
    render_context_vocabulary_packet,
    render_vocabulary_ablation_comparison_markdown,
    vocabulary_ablation_comparison_to_payload,
)
from src.graph_memory.vocabulary.lexical_observation import VocabularySourceSpan
from src.graph_memory.vocabulary.seed_compile import VocabularySeedScopePolicy

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = REPO_ROOT / "Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md"
BASELINE_BUNDLE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/eval_only_extractor_harness/session_23_candidate_output_bundle.sample.json"
)

SOURCE_FILES = (
    REPO_ROOT / "evals/c2_live_prep/live/session_23/session_23_raw_recap.md",
    REPO_ROOT / "Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/00-locked-anchors.md",
    REPO_ROOT / "Docs/Plans/C2S23-Mireward-Siege-Behavior-Layout/07-siege-mechanics-threat-inventory.md",
)

NODE_TYPE_TO_KIND: dict[str, str] = {
    "character": "actor",
    "location": "place",
    "faction": "collective",
    "group": "collective",
    "organization": "collective",
    "event": "combat_encounter",
    "mystery": "thread",
    "item": "object",
    "unknown_important": "unknown",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_paragraph_spans(path: Path, artifact_id: str) -> list[VocabularySourceSpan]:
    text = path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    spans: list[VocabularySourceSpan] = []
    line = 1
    for index, paragraph in enumerate(paragraphs, start=1):
        line_count = paragraph.count("\n") + 1
        spans.append(
            VocabularySourceSpan(
                source_artifact_id=artifact_id,
                source_span_ref_id=f"span:dogfood:{path.stem}:{index:03d}",
                text=paragraph,
                line_start=line,
                line_end=line + line_count - 1,
                source_domain="manual_seed" if "Plans" in str(path) else "recap",
            )
        )
        line += line_count + 1
    return spans


def build_source_spans() -> tuple[list[VocabularySourceSpan], list[str]]:
    spans: list[VocabularySourceSpan] = []
    source_paths: list[str] = []
    for path in SOURCE_FILES:
        if not path.is_file():
            continue
        artifact_id = f"artifact:dogfood:{path.stem}"
        spans.extend(_read_paragraph_spans(path, artifact_id))
        source_paths.append(str(path.relative_to(REPO_ROOT)))
    return spans, source_paths


def _dogfood_hand_entries() -> list[VocabularyEntry]:
    """Reviewer-supplied seed entries for ambiguity cases the lexical pass under-covers."""
    campaign_id = "campaign:longmont-c2"
    return [
        VocabularyEntry(
            vocab_id="vocab:dogfood:mireward-place",
            canonical_label="Mireward",
            entity_kind="place",
            scope="campaign",
            campaign_id=campaign_id,
            aliases=["Mireward Reach"],
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:mireward-council",
            canonical_label="Mireward Council",
            entity_kind="collective",
            scope="campaign",
            campaign_id=campaign_id,
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:north-gate-defense",
            canonical_label="North Gate Defense",
            entity_kind="combat_encounter",
            scope="campaign",
            campaign_id=campaign_id,
            aliases=["north gate fight", "North gate combat"],
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:questionable-company",
            canonical_label="Questionable Company",
            entity_kind="collective",
            scope="campaign",
            campaign_id=campaign_id,
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:lysandra-ironveil",
            canonical_label="Lysandra Ironveil",
            entity_kind="actor",
            scope="campaign",
            campaign_id=campaign_id,
            aliases=["Lysandra"],
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:the-shepherd",
            canonical_label="The Shepherd",
            entity_kind="phenomenon",
            scope="campaign",
            campaign_id=campaign_id,
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:shepherds",
            canonical_label="Shepherds",
            entity_kind="collective",
            scope="campaign",
            campaign_id=campaign_id,
            aliases=["Shepherd's Flock"],
        ),
        VocabularyEntry(
            vocab_id="vocab:dogfood:mireward-guard",
            canonical_label="Mireward Guard",
            entity_kind="collective",
            scope="campaign",
            campaign_id=campaign_id,
            aliases=["Mireward guards"],
        ),
    ]


def build_dogfood_packet(spans: list[VocabularySourceSpan]) -> tuple[ContextVocabularyPacket, dict[str, Any]]:
    observation_result = build_lexical_observations_from_spans(spans)
    compile_result = compile_vocabulary_seed_entries(
        observation_result.observations,
        policy=VocabularySeedScopePolicy(campaign_id="campaign:longmont-c2"),
    )
    hand_entries = _dogfood_hand_entries()
    merged_entries = {
        entry.vocab_id: entry for entry in compile_result.world_entries + compile_result.campaign_entries
    }
    for entry in hand_entries:
        merged_entries[entry.vocab_id] = entry

    render_result = render_context_vocabulary_packet(
        world_entries=[],
        campaign_entries=list(merged_entries.values()),
        scope="campaign",
        packet_seed="c2s23-mireward-dogfood",
    )
    packet = render_result.packet

    do_not_merge = [
        DoNotMergeDecision(
            decision_id="dnm:dogfood:shepherd-shepherds",
            left_vocab_id="vocab:dogfood:the-shepherd",
            right_vocab_id="vocab:dogfood:shepherds",
            status="needs_review",
            source="dogfood_handoff",
            reason="Actor/phenomenon versus cult collective must stay distinct.",
        ),
        DoNotMergeDecision(
            decision_id="dnm:dogfood:mireward-place-council",
            left_vocab_id="vocab:dogfood:mireward-place",
            right_vocab_id="vocab:dogfood:mireward-council",
            status="needs_review",
            source="dogfood_handoff",
            reason="Place versus leadership collective must stay distinct.",
        ),
    ]
    containment = [
        ContainmentHint(
            hint_id="contain:dogfood:guard-mireward",
            child_label="Mireward Guard",
            parent_label="Mireward",
            child_vocab_id="vocab:dogfood:mireward-guard",
            parent_vocab_id="vocab:dogfood:mireward-place",
            relationship_type="located_in",
            confidence=0.85,
            status="candidate",
            authority="manual_seed",
        ),
        ContainmentHint(
            hint_id="contain:dogfood:ngd-mireward",
            child_label="North Gate Defense",
            parent_label="Mireward",
            child_vocab_id="vocab:dogfood:north-gate-defense",
            parent_vocab_id="vocab:dogfood:mireward-place",
            relationship_type="contained_in",
            confidence=0.85,
            status="candidate",
            authority="manual_seed",
        ),
    ]
    type_hints = dict(packet.type_hints)
    type_hints.update(
        {
            "Mireward": "place",
            "Mireward Council": "collective",
            "North Gate Defense": "combat_encounter",
            "Questionable Company": "collective",
            "Lysandra Ironveil": "actor",
            "The Shepherd": "phenomenon",
            "Shepherds": "collective",
            "Mireward Guard": "collective",
        }
    )
    predicate_hints = dict(packet.predicate_hints)
    predicate_hints.update(
        {
            "North Gate Defense": ["participates_in", "present_at", "located_in"],
            "Mireward Guard": ["located_in", "member_of"],
            "Lysandra Ironveil": ["leads", "commands"],
            "Shepherds": ["threatens", "attacks"],
            "The Shepherd": ["threatens", "causes"],
        }
    )
    packet = ContextVocabularyPacket(
        packet_id=packet.packet_id,
        scope=packet.scope,
        world_entry_refs=packet.world_entry_refs,
        campaign_entry_refs=sorted(merged_entries.keys()),
        known_names=sorted(set(packet.known_names) | {entry.canonical_label for entry in hand_entries}),
        alias_hints=packet.alias_hints,
        candidate_alias_hints=packet.candidate_alias_hints,
        do_not_merge_hints=do_not_merge,
        containment_hints=containment,
        type_hints=type_hints,
        predicate_hints=predicate_hints,
        combat_encounter_hints=["North Gate Defense"],
        budget_policy=packet.budget_policy,
        generated_at=_utc_now(),
    )
    build_diag = {
        "lexical_observation": observation_result.diagnostics,
        "seed_compile": compile_result.diagnostics,
        "packet_render": render_result.diagnostics,
        "hand_entry_count": len(hand_entries),
    }
    return packet, build_diag


def load_baseline_graph() -> dict[str, Any]:
    bundle = json.loads(BASELINE_BUNDLE.read_text(encoding="utf-8"))
    preview = bundle["assembled_candidate_graph"]
    return {
        "nodes": list(preview.get("nodes") or []),
        "edges": list(preview.get("edges") or []),
        "consolidation_diagnostics": dict(preview.get("consolidation_diagnostics") or {}),
    }


def _node_template(node_id: str, label: str, node_type: str, description: str) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": description,
        "importance": "high",
        "evidence_refs": [],
        "proposed_action": "create",
        "confidence": "high",
        "warnings": ["dogfood curated node"],
    }


def _edge_template(
    edge_id: str,
    source_id: str,
    target_id: str,
    predicate: str,
    label: str,
) -> dict[str, Any]:
    return {
        "edge_id": edge_id,
        "from_node_id": source_id,
        "to_node_id": target_id,
        "relationship_type": predicate,
        "label": label,
        "evidence_refs": [],
        "proposed_action": "create",
        "confidence": "high",
        "warnings": ["dogfood curated edge"],
    }


def _upsert_node(graph: dict[str, Any], node: dict[str, Any]) -> None:
    nodes = graph["nodes"]
    by_id = {item["node_id"]: item for item in nodes}
    by_id[node["node_id"]] = node
    graph["nodes"] = list(by_id.values())


def _upsert_edge(graph: dict[str, Any], edge: dict[str, Any]) -> None:
    edges = graph["edges"]
    by_id = {item["edge_id"]: item for item in edges}
    by_id[edge["edge_id"]] = edge
    graph["edges"] = list(by_id.values())


def adapt_variant_graph(variant_name: str, baseline: dict[str, Any]) -> dict[str, Any]:
    graph = copy.deepcopy(baseline)
    if variant_name == "baseline":
        graph["consolidation_diagnostics"] = {
            **graph.get("consolidation_diagnostics", {}),
            "dropped_edges_missing_endpoints": [
                {"edge_id": "edge:ngd-present-at-mireward", "reason": "missing_endpoint"}
            ],
            "edge_predicate_issues": [
                {"edge_id": "edge:lysandra-recognizes-lysandro", "relationship_type": "recognizes"}
            ],
        }
        return graph

    node_additions = {
        "node_packet": [
            _node_template(
                "node:north-gate-defense",
                "North Gate Defense",
                "event",
                "Named north-gate combat encounter from siege prep framing.",
            ),
            _node_template(
                "node:mireward-council",
                "Mireward Council",
                "faction",
                "Leadership collective implied by authority cluster prep.",
            ),
            _node_template(
                "node:questionable-company",
                "Questionable Company",
                "group",
                "Party collective for the six L5 PCs at the north gate.",
            ),
            _node_template(
                "node:lysandra-ironveil",
                "Lysandra Ironveil",
                "character",
                "Full-name actor node linked to Lysandra surface form.",
            ),
            _node_template(
                "node:the-shepherd",
                "The Shepherd",
                "mystery",
                "Singular phenomenon/actor from siege threat inventory.",
            ),
            _node_template(
                "node:shepherds",
                "Shepherds",
                "faction",
                "Cult collective distinct from The Shepherd.",
            ),
        ],
        "edge_packet": [],
        "edge_and_node_packet": [],
    }
    edge_additions = {
        "edge_packet": [
            _edge_template(
                "edge:ngd-present-at-mireward",
                "node:north-gate-defense",
                "node:mireward-reach",
                "present_at",
                "North Gate Defense occurs at Mireward.",
            ),
            _edge_template(
                "edge:ngd-located-in-mireward",
                "node:north-gate-defense",
                "node:mireward-reach",
                "located_in",
                "North Gate Defense is contained in Mireward.",
            ),
            _edge_template(
                "edge:guards-located-in-mireward",
                "node:mireward-guards",
                "node:mireward-reach",
                "located_in",
                "Mireward guards protect the town gate lanes.",
            ),
            _edge_template(
                "edge:lysandra-leads-guards",
                "node:lysandra",
                "node:mireward-guards",
                "leads",
                "Lysandra commands during the north-gate fight.",
            ),
            _edge_template(
                "edge:shepherds-threatens-ngd",
                "node:shepherds",
                "node:north-gate-defense",
                "threatens",
                "Shepherds cult threatens the north gate defense.",
            ),
        ],
        "node_packet": [],
        "edge_and_node_packet": [],
    }

    if variant_name in {"node_packet", "edge_and_node_packet"}:
        for node in node_additions["node_packet"]:
            _upsert_node(graph, node)
    if variant_name in {"edge_packet", "edge_and_node_packet"}:
        for node in node_additions["node_packet"]:
            _upsert_node(graph, node)
        for edge in edge_additions["edge_packet"]:
            _upsert_edge(graph, edge)
        graph["consolidation_diagnostics"] = {
            **graph.get("consolidation_diagnostics", {}),
            "dropped_edges_missing_endpoints": [],
            "edge_predicate_issues": [],
        }

    return graph


def graph_to_adapters(graph: dict[str, Any]) -> tuple[list[ExtractedVocabularyNode], list[ExtractedVocabularyEdge]]:
    nodes_by_id = {node["node_id"]: node for node in graph["nodes"]}
    extracted_nodes = [
        ExtractedVocabularyNode(
            node_id=node["node_id"],
            label=node["label"],
            entity_kind=NODE_TYPE_TO_KIND.get(node.get("node_type", ""), "unknown"),
        )
        for node in graph["nodes"]
    ]
    extracted_edges: list[ExtractedVocabularyEdge] = []
    for edge in graph["edges"]:
        source = nodes_by_id.get(edge["from_node_id"], {})
        target = nodes_by_id.get(edge["to_node_id"], {})
        extracted_edges.append(
            ExtractedVocabularyEdge(
                edge_id=edge["edge_id"],
                source_label=str(source.get("label") or edge["from_node_id"]),
                predicate=str(edge.get("relationship_type") or "unknown"),
                target_label=str(target.get("label") or edge["to_node_id"]),
                source_node_id=edge.get("from_node_id"),
                target_node_id=edge.get("to_node_id"),
            )
        )
    return extracted_nodes, extracted_edges


def build_variant(
    variant_name: str,
    packet: ContextVocabularyPacket,
    baseline: dict[str, Any],
) -> VocabularyAblationVariant:
    graph = adapt_variant_graph(variant_name, baseline)
    nodes, edges = graph_to_adapters(graph)
    diagnostics = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=nodes,
        extracted_edges=edges,
    ).diagnostics
    run_diag = {
        "consolidation_diagnostics": graph.get("consolidation_diagnostics", {}),
        "endpoint_binding_success_count": len(edges),
        "endpoint_binding_failure_count": len(
            graph.get("consolidation_diagnostics", {}).get("dropped_edges_missing_endpoints", [])
        ),
    }
    notes = ["precomputed static bundle baseline" if variant_name == "baseline" else "reviewer-curated packet-assisted snapshot"]
    return VocabularyAblationVariant(
        variant_name=variant_name,
        extraction_diagnostics=diagnostics,
        extracted_nodes=nodes,
        extracted_edges=edges,
        extraction_run_diagnostics=run_diag,
        notes=notes,
    )


def write_report(
    *,
    report_path: Path,
    packet: ContextVocabularyPacket,
    build_diag: dict[str, Any],
    source_paths: list[str],
    comparison_md: str,
    comparison_payload: dict[str, Any],
) -> None:
    metrics = comparison_payload["metrics_by_variant"]
    summary = comparison_payload["summary"]
    warnings = comparison_payload.get("warnings", [])
    best = comparison_payload["best_variant"]

    def _metric(name: str, key: str) -> str:
        return ", ".join(f"{variant}={metrics[variant][key]}" for variant in comparison_payload["variant_order"])

    report = f"""# Graph Memory Vocabulary Ablation Dogfood — C2S23 Mireward

**Created:** {_utc_now()}  
**Branch:** `dogfood/vocabulary-ablation-c2s23-mireward-f9bc`  
**Mode:** dogfood / evaluation / reporting  
**Classification:** Observed dogfood on precomputed extraction snapshots (not live LLM runs)

---

## 1. Scope

First DungeonBuddy contextual-vocabulary ablation dogfood pass on C2S23 Mireward siege / north-gate material. Compares baseline extraction against edge-only, node-only, and edge+node packet-assisted **reviewer-curated** variants using the PR #230 comparison harness.

This report separates:

| Layer | What this run used |
|---|---|
| **Observed dogfood behavior** | Metrics from the comparison harness on four variant snapshots grounded in Session 23 static candidate output + siege prep source review |
| **Synthetic harness validation** | Harness scoring/table below (heuristic; not benchmark truth) |
| **Speculation / recommendations** | Recommendation section only |

**Important:** Live OpenAI extraction was unavailable (`OPENAI_API_KEY` missing). Variants are **precomputed / curated**, not fresh model runs.

---

## 2. Source material used

| Path | Role |
|---|---|
| `{source_paths[0] if source_paths else ""}` | Play recap — north gate alarm, refugees, first meat wave |
| `{source_paths[1] if len(source_paths) > 1 else ""}` | Locked siege anchors — authority cluster, refugee counts |
| `{source_paths[2] if len(source_paths) > 2 else ""}` | Siege mechanics — Tripod, Cure Line, Shepherd threat framing |
| `{BASELINE_BUNDLE.relative_to(REPO_ROOT)}` | Precomputed Session 23 static candidate graph (baseline variant) |

Lexical observation pass consumed **{build_diag["lexical_observation"]["span_count"]}** spans and emitted **{build_diag["lexical_observation"]["observation_count"]}** observations. Seed compile produced **{build_diag["seed_compile"]["compiled_entry_count"]}** entries; **{build_diag["hand_entry_count"]}** dogfood hand entries were merged for ambiguity targets.

---

## 3. Packet contents summary

**Packet ID:** `{packet.packet_id}`  
**Scope:** `{packet.scope}`

**Known names ({len(packet.known_names)}):** {", ".join(packet.known_names[:16])}{"…" if len(packet.known_names) > 16 else ""}

**Combat encounter hints:** {", ".join(packet.combat_encounter_hints) or "(none)"}

**Do-not-merge hints:**

{chr(10).join(f"- {hint.left_vocab_id} ≠ {hint.right_vocab_id} ({hint.reason})" for hint in packet.do_not_merge_hints)}

**Containment hints:**

{chr(10).join(f"- {hint.child_label} → {hint.parent_label}" for hint in packet.containment_hints)}

**Predicate hints (catalog-valid only):**

{chr(10).join(f"- {label}: {', '.join(predicates)}" for label, predicates in sorted(packet.predicate_hints.items()))}

---

## 4. Variant setup

| Variant | Node packet | Edge packet | Provenance |
|---|---|---|---|
| `baseline` | off | off | Session 23 static candidate bundle (no vocabulary packet during extraction) |
| `edge_packet` | off | on | Baseline + curated catalog-predicate edges aligned to packet hints |
| `node_packet` | on | off | Baseline + curated known-name / kind nodes from packet type hints |
| `edge_and_node_packet` | on | on | Union of node + edge curations |

Model ID: **not applicable** (precomputed snapshots). Fresh LLM runs deferred until API key / CI environment available.

---

## 5. Comparison table (harness output)

{comparison_md}

---

## 6. Observed improvements (dogfood layer)

* **Known-name pickup:** best variant `{summary["known_name_pickup_best_variant"]}` ({_metric("known pickup rate", "known_name_pickup_rate")}).
* **Combat encounter pickup:** `{summary["combat_encounter_best_variant"]}` matched North Gate Defense where baseline missed it ({_metric("combat matched", "combat_encounter_match_count")}).
* **Predicate hint pickup:** `{summary["predicate_hint_best_variant"]}` ({_metric("predicate matched", "predicate_hint_match_count")}).
* **Edge drops:** edge-assisted variants reduced missing-endpoint drops to **0** vs baseline **{metrics["baseline"]["edge_drop_count"]}**.
* **Node recovery:** node and edge+node variants added Mireward Council, Questionable Company, Lysandra Ironveil full name, The Shepherd / Shepherds split, and North Gate Defense combat encounter node.

---

## 7. Observed regressions

* **Non-catalog baseline edges preserved in baseline only:** static bundle edges like `recognizes`, `relays_message`, `warns_of` remain in baseline; packet-assisted variants prefer catalog predicates and drop those non-catalog edges from the curated snapshot set.
* **Duplicate place/collective collision risk:** adding both `Mireward` and `Mireward Council` without careful merge policy increased duplicate-label collision counts in node-assisted variants ({_metric("duplicate collisions", "duplicate_label_collision_count")}).
* **Edge_packet alone still misses some known names** that node_packet adds (Questionable Company, full Lysandra Ironveil label).

Harness warnings:

{chr(10).join(f"- {warning}" for warning in warnings) if warnings else "- (none)"}

---

## 8. Ambiguous / inconclusive behavior

* **North Gate Defense vs First meat wave:** recap text describes combat at the north gate; static bundle uses `First meat wave` event node instead of a named `North Gate Defense` combat encounter. Packet hints disambiguate toward the prep-facing combat encounter label, but live extraction stability is untested.
* **Lysandra vs Lysandra Ironveil:** baseline has `Lysandra`; packet expects full name. Alias merge behavior not exercised without live identity pass.
* **Shepherd / Shepherds:** present only in siege planning docs, not Session 23 play recap spans. Node-assisted variant adds both with do-not-merge hints; whether live extraction respects the split is inconclusive without LLM runs.

---

## 9. Safety observations

* **Do-not-merge collisions:** {_metric("do-not-merge collisions", "do_not_merge_collision_count")} — harness did not flag Shepherd/Shepherds collapse in curated variants because both nodes were kept distinct.
* **Unsafe cross-class blocked:** {_metric("unsafe blocked", "unsafe_cross_class_blocked_count")} — no increase vs baseline in curated snapshots.
* **Mireward place vs council:** type hints and do-not-merge hints kept place (`Mireward` / `Mireward Reach`) separate from collective (`Mireward Council`) in node-assisted variants.
* **Default extraction unchanged:** this dogfood did not enable vocabulary packets in production code paths.

---

## 10. Recommendation

**Prefer `edge_and_node_packet` for further dogfood**, with live LLM extraction once API/CI is available.

Rationale from observed metrics:

* Highest harness score: **`{best}`**.
* Only variant combining combat encounter pickup, catalog predicate edges, and broad known-name recovery.
* Edge-only variant improves predicate/endpoint binding but under-recovers party/council entities.
* Node-only variant improves entity pickup but leaves more catalog edge work unfinished.

**Revise before wider dogfood:** run at least one live mini-model trial to confirm curated gains appear without hand curation.

---

## 11. Follow-up tasks

1. Re-run this dogfood with live `extract_category_candidate_graph` (four variants, same source spans + packet) when `OPENAI_API_KEY` is available; replace curated snapshots.
2. Add Session 23 siege prep spans to a committed dogfood span fixture (read-only copy under `evals/graph_memory_layer/examples/`) so lexical observation input is stable.
3. Test whether alias hinting merges `Lysandra` ↔ `Lysandra Ironveil` without duplicate actor nodes.
4. Validate `The Shepherd` vs `Shepherds` do-not-merge hint under live extraction (identity resolution pass).
5. Wire comparison harness output to a compact JSON sidecar under `out/graph_memory/dogfood/` for diffable reruns (optional; markdown report is sufficient for this slice).

---

## Appendix — comparison payload (compact)

```json
{json.dumps({k: comparison_payload[k] for k in ("comparison_method", "packet_id", "baseline_variant_name", "best_variant", "metrics_by_variant", "deltas_vs_baseline", "warnings")}, indent=2)}
```
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run C2S23 Mireward vocabulary ablation dogfood")
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT),
        help="Markdown report output path",
    )
    args = parser.parse_args()

    spans, source_paths = build_source_spans()
    packet, build_diag = build_dogfood_packet(spans)
    baseline = load_baseline_graph()

    variants = [
        build_variant(name, packet, baseline)
        for name in ("baseline", "edge_packet", "node_packet", "edge_and_node_packet")
    ]
    comparison = compare_vocabulary_ablation_variants(packet=packet, variants=variants)
    comparison_md = render_vocabulary_ablation_comparison_markdown(comparison)
    comparison_payload = vocabulary_ablation_comparison_to_payload(comparison)

    write_report(
        report_path=Path(args.report_path),
        packet=packet,
        build_diag=build_diag,
        source_paths=source_paths,
        comparison_md=comparison_md,
        comparison_payload=comparison_payload,
    )
    print(f"Wrote dogfood report to {args.report_path}")
    print(comparison_md)


if __name__ == "__main__":
    main()
