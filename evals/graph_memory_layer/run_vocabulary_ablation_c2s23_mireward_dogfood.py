#!/usr/bin/env python3
"""Run a C2S23 Mireward vocabulary ablation dogfood comparison.

This is intentionally a report runner, not reusable extraction machinery. It
grounds extraction in the session 23 normalized recap (the canon source other
S23 fixtures use), builds a dogfood-only vocabulary packet whose known names are
partitioned into a present-set (entities that genuinely recur in S23, using the
gold label forms) and a retained absent-set (prior canon NOT in this session),
runs the four opt-in extraction variants, and emits a compact report.

The partition matters: pooled known-name pickup conflates two opposite goals.
For the present-set we want high recognition (the packet should help the model
latch onto returning entities); for the absent-set we want zero contamination
(injecting a canon name must NOT make the model hallucinate an entity that the
session text does not support). This runner reports those two lanes separately.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from evals.graph_memory_layer.session_23_recap_ingest_fixture import (
    load_expected_normalized_recap,
)
from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory import identity_resolution as ir
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    extract_category_candidate_graph,
    resolve_category_graph_model,
)
from src.graph_memory.vocabulary import (
    ContainmentHint,
    ContextVocabularyPacket,
    DoNotMergeDecision,
    ExtractedVocabularyEdge,
    ExtractedVocabularyNode,
    VocabularyAblationVariant,
    VocabularyEntry,
    compare_vocabulary_ablation_variants,
    diagnose_vocabulary_extraction_baseline,
    render_context_vocabulary_packet,
    render_vocabulary_ablation_comparison_markdown,
    vocabulary_ablation_comparison_to_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md"
)
DEFAULT_JSON_ARTIFACT_PATH = (
    REPO_ROOT
    / "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/c2s23_mireward_vocabulary_ablation.json"
)
RECAP_SOURCE_LABEL = (
    "evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md"
)

# Known names that genuinely recur in the S23 recap, using the human gold label
# forms (see candidate_graph_gold.json). The packet should help the model
# recognize these; recognition_rate over this set is the benefit signal.
EXPECTED_PRESENT: tuple[str, ...] = (
    "Mireward Reach",
    "Lysandra",
    "Lysandro",
    "Orik Tane",
    "Edge",
    "North gate",
    "First meat wave",
)

# Prior campaign canon that does NOT appear in the S23 recap. These are retained
# in the packet specifically to measure contamination: if injecting these names
# causes the extractor to emit a node for them, that is a hallucination, not a
# win. contamination_count over this set must stay at 0.
EXPECTED_ABSENT: tuple[str, ...] = (
    "Maelthor",
    "The Shepherd",
    "Shepherds",
    "Under-Hymn Brood",
    "Mireward Council",
)

VARIANT_FLAGS = {
    "baseline": (False, False),
    "edge_packet": (False, True),
    "node_packet": (True, False),
    "edge_and_node_packet": (True, True),
}


@dataclass(slots=True)
class VariantRun:
    variant: VocabularyAblationVariant
    raw_result: Any
    node_count_by_kind: dict[str, int]
    edge_count_by_predicate: dict[str, int]
    partition: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _paragraph_blocks(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    blocks: list[tuple[int, int, str]] = []
    start: int | None = None
    current: list[str] = []
    for idx, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = idx
            current.append(line)
            continue
        if start is not None and current:
            blocks.append((start, idx - 1, "\n".join(current).strip()))
        start = None
        current = []
    if start is not None and current:
        blocks.append((start, len(lines), "\n".join(current).strip()))
    return blocks


def _is_frontmatter_or_heading(block: str) -> bool:
    stripped = block.strip()
    if not stripped:
        return True
    if stripped.startswith("---") or "document_class:" in stripped:
        return True
    if all(line.lstrip().startswith("#") for line in stripped.splitlines()):
        return True
    return False


def build_source_span_index() -> tuple[dict[str, Any], list[str]]:
    """Build paragraph spans from the S23 normalized recap (canon source)."""
    text = load_expected_normalized_recap()
    spans: list[dict[str, Any]] = []
    ordinal = 0
    for line_start, line_end, block in _paragraph_blocks(text):
        if _is_frontmatter_or_heading(block):
            continue
        ordinal += 1
        spref = f"spref:c2s23-recap:{ordinal:03d}"
        spans.append(
            {
                "source_span_ref_id": spref,
                "span_id": spref,
                "source_path": RECAP_SOURCE_LABEL,
                "kind": "paragraph",
                "line_start": line_start,
                "line_end": line_end,
                "text": block.strip(),
            }
        )
    return {
        "schema": "dmb_dogfood_manual_source_span_index_v1",
        "source_artifact_id": "source-artifact:longmont-c2:session-23:mireward-recap-vocabulary-dogfood",
        "spans": spans,
    }, [RECAP_SOURCE_LABEL]


def _entry(vocab_id: str, label: str, kind: str, *, aliases: Iterable[str] = ()) -> VocabularyEntry:
    return VocabularyEntry(
        vocab_id=vocab_id,
        canonical_label=label,
        entity_kind=kind,  # type: ignore[arg-type]
        scope="campaign",
        campaign_id="longmont-c2",
        aliases=list(aliases),
        status="candidate",
        authority="manual_seed",
        notes="Dogfood-only packet entry; not canon promotion.",
    )


def build_packet() -> ContextVocabularyPacket:
    entries = [
        # Present-set: prior canon that recurs in S23, using gold label forms.
        _entry("vocab:c2s23:mireward-reach", "Mireward Reach", "place"),
        _entry("vocab:c2s23:lysandra", "Lysandra", "actor"),
        _entry("vocab:c2s23:lysandro", "Lysandro", "actor"),
        _entry("vocab:c2s23:orik-tane", "Orik Tane", "actor"),
        _entry("vocab:c2s23:edge", "Edge", "place"),
        _entry("vocab:c2s23:north-gate", "North gate", "place"),
        _entry("vocab:c2s23:first-meat-wave", "First meat wave", "combat_encounter"),
        # Absent-set: prior canon NOT in S23, retained to measure contamination.
        _entry("vocab:c2s23:maelthor", "Maelthor", "actor"),
        _entry("vocab:c2s23:the-shepherd", "The Shepherd", "actor"),
        _entry("vocab:c2s23:shepherds", "Shepherds", "collective"),
        _entry("vocab:c2s23:under-hymn-brood", "Under-Hymn Brood", "collective"),
        _entry("vocab:c2s23:mireward-council", "Mireward Council", "collective"),
    ]
    result = render_context_vocabulary_packet(
        scope="campaign",
        campaign_entries=entries,
        do_not_merge_hints=[
            DoNotMergeDecision(
                decision_id="dnm:c2s23:the-shepherd-vs-shepherds",
                left_vocab_id="vocab:c2s23:the-shepherd",
                right_vocab_id="vocab:c2s23:shepherds",
                source="dogfood_manual_packet",
                reason="Person/entity vs cult or collective ambiguity must remain visible.",
            ),
            DoNotMergeDecision(
                decision_id="dnm:c2s23:mireward-reach-vs-council",
                left_vocab_id="vocab:c2s23:mireward-reach",
                right_vocab_id="vocab:c2s23:mireward-council",
                source="dogfood_manual_packet",
                reason="Place vs polity/leadership ambiguity should not silently collapse.",
            ),
        ],
        containment_hints=[
            ContainmentHint(
                hint_id="contain:c2s23:north-gate-in-mireward",
                child_label="North gate",
                parent_label="Mireward Reach",
                child_vocab_id="vocab:c2s23:north-gate",
                parent_vocab_id="vocab:c2s23:mireward-reach",
                relationship_type="located_in",
                status="candidate",
                authority="manual_seed",
            ),
        ],
        predicate_hints={
            "Lysandra": ["leads", "commands", "present_at"],
            "Orik Tane": ["governs", "present_at"],
            "Lysandro": ["present_at", "located_in"],
            "North gate": ["located_in"],
            "Mireward Reach": ["located_in"],
            "First meat wave": ["present_at", "participates_in"],
        },
        packet_seed="c2s23-mireward-recap-dogfood-v1",
    )
    return result.packet


def _entity_kind_for_node(node: Mapping[str, Any]) -> str:
    node_type = str(node.get("node_type") or "unknown")
    type_class = ir.node_type_class(node_type)
    if type_class == "phenomenon" and node_type == "event":
        label = str(node.get("label") or "")
        if "defense" in label.lower() or "combat" in label.lower() or "gate" in label.lower():
            return "combat_encounter"
    return type_class if type_class in {"actor", "place", "collective", "object", "thread", "phenomenon"} else "unknown"


def _adapt_nodes(candidate_graph: Mapping[str, Any]) -> list[ExtractedVocabularyNode]:
    nodes = candidate_graph.get("nodes") or []
    return [
        ExtractedVocabularyNode(
            node_id=str(node.get("node_id") or f"node:{idx}"),
            label=str(node.get("label") or node.get("node_id") or f"node:{idx}"),
            entity_kind=_entity_kind_for_node(node),  # type: ignore[arg-type]
            source=str(node.get("node_type") or ""),
        )
        for idx, node in enumerate(nodes)
        if isinstance(node, Mapping)
    ]


def _node_labels(candidate_graph: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(node.get("node_id")): str(node.get("label") or node.get("node_id"))
        for node in candidate_graph.get("nodes") or []
        if isinstance(node, Mapping) and node.get("node_id")
    }


def _adapt_edges(candidate_graph: Mapping[str, Any]) -> list[ExtractedVocabularyEdge]:
    labels = _node_labels(candidate_graph)
    edges: list[ExtractedVocabularyEdge] = []
    for idx, edge in enumerate(candidate_graph.get("edges") or []):
        if not isinstance(edge, Mapping):
            continue
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        source_label = labels.get(from_id, from_id)
        target_label = labels.get(to_id, to_id)
        if not source_label or not target_label:
            continue
        edges.append(
            ExtractedVocabularyEdge(
                edge_id=str(edge.get("edge_id") or f"edge:{idx}"),
                source_label=source_label,
                predicate=str(edge.get("relationship_type") or "associated_with"),
                target_label=target_label,
                source_node_id=from_id or None,
                target_node_id=to_id or None,
            )
        )
    return edges


def _run_diagnostics(result: Any) -> dict[str, Any]:
    return {
        "consolidation_diagnostics": result.consolidation_diagnostics,
        "model_id": result.model_id,
        "total_cost_usd": result.total_cost_usd,
        "extraction_diagnostics": result.diagnostics,
    }


def _partition_metrics(diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    """Split pooled known-name pickup into recognition (present) and contamination (absent).

    Recognition rewards picking up entities the session actually contains.
    Contamination flags entities the packet supplied that the session does NOT
    contain — emitting one is a hallucination, not a pickup win.
    """
    matched = set(diagnostics.get("known_name_pickup", {}).get("matched", []))
    present_recognized = sorted(name for name in EXPECTED_PRESENT if name in matched)
    present_missed = sorted(name for name in EXPECTED_PRESENT if name not in matched)
    absent_contaminated = sorted(name for name in EXPECTED_ABSENT if name in matched)
    absent_clean = sorted(name for name in EXPECTED_ABSENT if name not in matched)
    present_count = len(EXPECTED_PRESENT)
    absent_count = len(EXPECTED_ABSENT)
    return {
        "present_count": present_count,
        "present_recognized": present_recognized,
        "present_missed": present_missed,
        "recognition_rate": round(len(present_recognized) / present_count, 3) if present_count else 0.0,
        "absent_count": absent_count,
        "absent_contaminated": absent_contaminated,
        "absent_clean": absent_clean,
        "contamination_count": len(absent_contaminated),
        "contamination_rate": round(len(absent_contaminated) / absent_count, 3) if absent_count else 0.0,
    }


def run_variant(
    name: str,
    *,
    packet: ContextVocabularyPacket,
    span_index: Mapping[str, Any],
    model_id: str | None,
) -> VariantRun:
    enable_node, enable_edge = VARIANT_FLAGS[name]
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-23",
            session_number=23,
            source_span_index=span_index,
            model_id=model_id,
            enable_node_vocabulary_packet=enable_node,
            node_vocabulary_packet=packet if enable_node else None,
            enable_edge_vocabulary_packet=enable_edge,
            edge_vocabulary_packet=packet if enable_edge else None,
        )
    )
    nodes = _adapt_nodes(result.candidate_graph)
    edges = _adapt_edges(result.candidate_graph)
    diagnostics = diagnose_vocabulary_extraction_baseline(
        packet=packet,
        extracted_nodes=nodes,
        extracted_edges=edges,
    ).diagnostics
    variant = VocabularyAblationVariant(
        variant_name=name,
        extraction_diagnostics=diagnostics,
        extracted_nodes=nodes,
        extracted_edges=edges,
        extraction_run_diagnostics=_run_diagnostics(result),
    )
    node_count_by_kind = dict(sorted(Counter(node.entity_kind for node in nodes).items()))
    edge_count_by_predicate = dict(sorted(Counter(edge.predicate for edge in edges).items()))
    return VariantRun(
        variant=variant,
        raw_result=result,
        node_count_by_kind=node_count_by_kind,
        edge_count_by_predicate=edge_count_by_predicate,
        partition=_partition_metrics(diagnostics),
    )


def _best_by(metrics: Mapping[str, Mapping[str, Any]], key: str, *, lower: bool = False) -> str:
    return min(metrics, key=lambda name: (metrics[name].get(key, 0) if lower else -metrics[name].get(key, 0), name))


def _best_names_by(metrics: Mapping[str, Mapping[str, Any]], key: str, *, lower: bool = False) -> list[str]:
    if not metrics:
        return []
    values = {name: metrics[name].get(key, 0) for name in metrics}
    best_value = min(values.values()) if lower else max(values.values())
    return sorted(name for name, value in values.items() if value == best_value)


def _format_variant_names(names: list[str], *, markdown: bool) -> str:
    formatted = [f"`{name}`" if markdown else name for name in names]
    if not formatted:
        return "none"
    if len(formatted) == 1:
        return formatted[0]
    return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"


def _partition_aware_recommendation(
    *,
    comparison_payload: Mapping[str, Any],
    variants_by_name: Mapping[str, VariantRun],
    markdown: bool,
) -> str:
    order = list(comparison_payload.get("variant_order", []))
    best = str(comparison_payload.get("best_variant") or "baseline")
    baseline = variants_by_name["baseline"].partition
    baseline_recognition = baseline["recognition_rate"]
    best_partition = variants_by_name[best].partition
    max_recognition = max(variants_by_name[name].partition["recognition_rate"] for name in order)
    clean_variants = [
        name for name in order if variants_by_name[name].partition["contamination_count"] == 0
    ]
    clean_packet_variants = [name for name in clean_variants if name != "baseline"]

    if max_recognition <= baseline_recognition and best_partition["contamination_count"] > 0:
        clean_candidate = clean_packet_variants[-1] if clean_packet_variants else "baseline"
        return (
            f"Do not promote {_format_variant_names([best], markdown=markdown)} from this run: "
            "present-set recognition tied baseline, while the heuristic winner contaminated absent-set names. "
            f"If continuing packet-assisted dogfood, use {_format_variant_names([clean_candidate], markdown=markdown)} "
            f"as the clean comparison and keep {_format_variant_names(['baseline'], markdown=markdown)} as the safety control."
        )
    if max_recognition <= baseline_recognition:
        return (
            f"Treat {_format_variant_names([best], markdown=markdown)} as an edge/predicate follow-up only: "
            "present-set recognition did not improve over baseline in this run."
        )
    if best_partition["contamination_count"] > 0:
        clean_candidates = [
            name
            for name in clean_variants
            if variants_by_name[name].partition["recognition_rate"] == max_recognition
        ]
        if clean_candidates:
            return (
                f"Prefer {_format_variant_names(clean_candidates, markdown=markdown)} for further dogfood: "
                "they matched the best recognition rate without absent-set contamination."
            )
        return (
            f"Do not promote {_format_variant_names([best], markdown=markdown)} yet: "
            "the recognition gain came with absent-set contamination."
        )
    return f"Prefer {_format_variant_names([best], markdown=markdown)} for further dogfood."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def render_report(
    *,
    packet: ContextVocabularyPacket,
    used_paths: list[str],
    variant_runs: list[VariantRun],
    comparison_payload: Mapping[str, Any],
    comparison_markdown: str,
    model_id: str,
    source_span_count: int,
    generated_at: str,
) -> str:
    metrics = comparison_payload["metrics_by_variant"]
    packet_predicates = {
        "occurred_at": "present_at",
        "involved": "participates_in",
        "defended_by": "associated_with / located_in",
        "attacked_by": "attacks",
        "protects": "serves / associated_with",
        "corrupts": "threatens / associated_with",
    }
    variants_by_name = {run.variant.variant_name: run for run in variant_runs}
    lines = [
        "# Graph Memory Vocabulary Ablation Dogfood — C2S23 Mireward",
        "",
        f"Generated: {generated_at}",
        "",
        "## 1. Scope",
        "",
        "Dogfood run grounded in the session 23 normalized recap (the canon source other S23 fixtures use), comparing `baseline`, `edge_packet`, `node_packet`, and `edge_and_node_packet` with the existing vocabulary ablation harness. This report is evidence from one dogfood slice, not a generalized benchmark claim.",
        "",
        "The packet's known names are partitioned. The present-set uses S23 gold label forms for entities that genuinely recur this session; the absent-set is prior canon NOT in this session, retained to measure contamination. Pooled pickup conflates these; recognition (present) and contamination (absent) are reported separately in section 6.",
        "",
        "## 2. Source Material Used",
        "",
        f"- Model: `{model_id}`",
        f"- Source spans: {source_span_count} recap paragraphs",
        "- Outputs: fresh LLM extraction runs, not precomputed fixtures",
        "- Authority note: the source is a post-session recap fixture; observed behavior is dogfood extraction over canon recap text, not canon memory promotion.",
        "",
        *[f"- `{path}`" for path in used_paths],
        "",
        "## 3. Packet Contents Summary",
        "",
        f"- Packet: `{packet.packet_id}`",
        f"- Known names: {len(packet.known_names)}",
        f"- Type hints: {len(packet.type_hints)}",
        f"- Predicate hint subjects: {len(packet.predicate_hints)}",
        f"- Combat encounter hints: {', '.join(packet.combat_encounter_hints) or '(none)'}",
        f"- Do-not-merge hints: {len(packet.do_not_merge_hints)}",
        f"- Containment hints: {len(packet.containment_hints)}",
        "",
        "Predicate replacements applied because the project catalog does not contain every handoff suggestion:",
        "",
        *[f"- `{bad}` -> `{replacement}`" for bad, replacement in packet_predicates.items()],
        "",
        "## 4. Variant Setup",
        "",
        "| Variant | Node packet | Edge packet | Nodes | Edges | Cost USD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in comparison_payload["variant_order"]:
        run = variants_by_name[name]
        enable_node, enable_edge = VARIANT_FLAGS[name]
        lines.append(
            f"| {name} | {_yes_no(enable_node)} | {_yes_no(enable_edge)} | "
            f"{len(run.variant.extracted_nodes or [])} | {len(run.variant.extracted_edges or [])} | "
            f"{run.raw_result.total_cost_usd:.6f} |"
        )
    partition_lines = [
        "## 6. Present vs Absent Partition (primary signal)",
        "",
        f"Present-set ({len(EXPECTED_PRESENT)} names, gold label forms): {', '.join(f'`{n}`' for n in EXPECTED_PRESENT)}.",
        "",
        f"Absent-set ({len(EXPECTED_ABSENT)} prior-canon names not in S23): {', '.join(f'`{n}`' for n in EXPECTED_ABSENT)}.",
        "",
        "| Variant | Recognition (present) | Recognized | Contamination (absent) | Contaminated |",
        "|---|---:|---|---:|---|",
    ]
    for name in comparison_payload["variant_order"]:
        part = variants_by_name[name].partition
        recognized = ", ".join(part["present_recognized"]) or "(none)"
        contaminated = ", ".join(part["absent_contaminated"]) or "(none)"
        partition_lines.append(
            f"| {name} | {part['recognition_rate']:.3f} ({len(part['present_recognized'])}/{part['present_count']}) "
            f"| {recognized} | {part['contamination_rate']:.3f} ({part['contamination_count']}/{part['absent_count']}) "
            f"| {contaminated} |"
        )
    partition_lines.extend(
        [
            "",
            "Reading: recognition should rise with the packet (the benefit); contamination must stay at 0 (any absent-set name extracted is a hallucination the injected vocabulary induced, not a pickup win).",
        ]
    )
    lines.extend(
        [
            "",
            "## 5. Comparison Table",
            "",
            comparison_markdown,
            "",
        ]
        + partition_lines
        + [
            "",
            "## 6a. Observed Improvements (pooled, exact-label)",
            "",
            f"- Best pooled known-name pickup: `{_best_by(metrics, 'known_name_pickup_rate')}` (pooled across present+absent; see section 6 for the partition).",
            f"- Best combat encounter pickup: `{_best_by(metrics, 'combat_encounter_match_count')}`.",
            f"- Best predicate hint pickup: `{_best_by(metrics, 'predicate_hint_match_count')}`.",
            "- Treat these as exact-label diagnostics over one dogfood run, not a generalized model-quality claim.",
            "",
            "Per-variant node kinds:",
            "",
        ]
    )
    for name in comparison_payload["variant_order"]:
        lines.append(f"- `{name}`: `{json.dumps(variants_by_name[name].node_count_by_kind, sort_keys=True)}`")
    lines.extend(["", "Per-variant edge predicates:", ""])
    for name in comparison_payload["variant_order"]:
        lines.append(f"- `{name}`: `{json.dumps(variants_by_name[name].edge_count_by_predicate, sort_keys=True)}`")
    lines.extend(
        [
            "",
            "## 7. Observed Regressions",
            "",
        ]
    )
    warnings = comparison_payload.get("warnings") or []
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No harness-level regression warnings were emitted.")
    best_known = _best_by(metrics, "known_name_pickup_rate")
    best_combat = _best_by(metrics, "combat_encounter_match_count")
    best_predicate = _best_by(metrics, "predicate_hint_match_count")
    recognition_metrics = {
        n: {"recognition_rate": variants_by_name[n].partition["recognition_rate"]}
        for n in comparison_payload["variant_order"]
    }
    best_recognition_names = _best_names_by(recognition_metrics, "recognition_rate")
    best_recognition_value = recognition_metrics[best_recognition_names[0]]["recognition_rate"]
    baseline_metrics = metrics.get("baseline", {})
    combined_metrics = metrics.get("edge_and_node_packet", {})
    lines.extend(
        [
            (
                f"- Combat encounter pickup is exact-label sensitive: `{best_combat}` won this lane; "
                "packet-assisted variants may emit a nearby label that does not match the gold form `First meat wave`."
            ),
            (
                f"- Combined packets changed final edge volume from {len(variants_by_name['baseline'].variant.extracted_edges or [])} "
                f"to {len(variants_by_name['edge_and_node_packet'].variant.extracted_edges or [])} edges, "
                f"with predicate validation issues changing from {baseline_metrics.get('edge_predicate_issue_count', 0)} "
                f"to {combined_metrics.get('edge_predicate_issue_count', 0)}."
            ),
            "",
            "## 7a. Pickup Answers",
            "",
            f"- Best pooled known-name pickup: `{best_known}` (read section 6 for the present/absent split).",
            (
                f"- Best present-set recognition: {_format_variant_names(best_recognition_names, markdown=True)} "
                f"at {best_recognition_value:.3f}."
            ),
            f"- Best combat encounter pickup: `{best_combat}`.",
            "- Contamination (absent-set names emitted) is reported per variant in the safety section; the target is zero.",
            "",
            "## 7b. Edge Answers",
            "",
            f"- Predicate hint pickup improved most in `{best_predicate}`.",
            "- Endpoint binding is inferred from final candidate edges and dropped-edge diagnostics; the category pipeline does not currently report a separate binding success counter.",
            "- Dropped-edge reasons come from extraction run diagnostics when present; zero reported drops means no comparison-level drop reason is available.",
            "- Obvious bad edges require raw edge review; this runner commits only compact metrics and the markdown report.",
            "",
            "## 8. Ambiguous / Inconclusive Behavior",
            "",
            "- The source is a post-session recap; combat encounters are session-novel, so a prior-canon packet would not normally carry `First meat wave` — it is included only to probe the combat lane.",
            "- Recognition is exact-label against gold forms; if the extractor emits a near-variant label, it counts as a miss unless the exact form appears.",
            "- This dogfood run scores against the packet partition, not against the full human candidate-graph gold; it does not measure overall extraction precision/recall.",
            "",
            "## 9. Safety Observations",
            "",
        ]
    )
    for name in comparison_payload["variant_order"]:
        row = metrics[name]
        part = variants_by_name[name].partition
        contaminated = ", ".join(part["absent_contaminated"]) or "(none)"
        lines.append(
            f"- `{name}`: duplicate labels={row['duplicate_label_collision_count']}, "
            f"conflicting kinds={row['conflicting_kind_collision_count']}, unsafe blocked={row['unsafe_cross_class_blocked_count']}, "
            f"do-not-merge warnings={row['do_not_merge_collision_count']}, "
            f"present recognition={part['recognition_rate']:.3f} ({len(part['present_recognized'])}/{part['present_count']}), "
            f"absent contamination={part['contamination_count']}/{part['absent_count']} [{contaminated}]."
        )
    baseline_dup = metrics.get("baseline", {}).get("duplicate_label_collision_count", 0)
    combined_dup = metrics.get("edge_and_node_packet", {}).get("duplicate_label_collision_count", 0)
    baseline_conflicts = metrics.get("baseline", {}).get("conflicting_kind_collision_count", 0)
    combined_conflicts = metrics.get("edge_and_node_packet", {}).get("conflicting_kind_collision_count", 0)
    baseline_unsafe = metrics.get("baseline", {}).get("unsafe_cross_class_blocked_count", 0)
    combined_unsafe = metrics.get("edge_and_node_packet", {}).get("unsafe_cross_class_blocked_count", 0)
    lines.extend(
        [
            (
                f"- Duplicate label collisions changed from {baseline_dup} in baseline "
                f"to {combined_dup} in `edge_and_node_packet`."
            ),
            (
                f"- Conflicting kind collisions changed from {baseline_conflicts} in baseline "
                f"to {combined_conflicts} in `edge_and_node_packet`."
            ),
            (
                f"- Unsafe cross-class blocked counts changed from {baseline_unsafe} in baseline "
                f"to {combined_unsafe} in `edge_and_node_packet`."
            ),
            "- Do-not-merge collision warnings are reported per variant above.",
            "- Absent-set contamination is the key safety lane: any absent name extracted means the injected vocabulary induced a hallucination.",
        ]
    )
    recommendation = _partition_aware_recommendation(
        comparison_payload=comparison_payload,
        variants_by_name=variants_by_name,
        markdown=True,
    )
    lines.extend(
        [
            "",
            "## 10. Recommendation",
            "",
            recommendation,
            "",
            "This recommendation is partition-aware for this dogfood run only. Treat it as a next-dogfood choice, not a production default.",
            "",
            "## 11. Follow-up Tasks",
            "",
            "- Add an alias-aware diagnostic lane so gold near-variants (e.g. `North gate` vs `north-gate crisis`) are credited without changing extractor output.",
            "- Score against the full S23 candidate-graph gold (precision/recall) so claims extend beyond packet-name recognition.",
            "- If recognition gains hold but contamination stays at zero, promote `node_packet`/`edge_and_node_packet` to a larger multi-session dogfood.",
            "- Keep the present/absent partition as the standing contract for every future vocabulary run.",
            "",
            "## Separation Of Claims",
            "",
            "Observed dogfood behavior: the metrics and notes above come from the fresh C2S23 Mireward variant runs over the recap.",
            "",
            "Synthetic harness validation: existing unit tests validate the comparison and diagnostics APIs; they do not prove model quality.",
            "",
            "Speculation / recommendations: the follow-up tasks and recommendation identify what to try next, not what is generally proven.",
            "",
        ]
    )
    return "\n".join(lines)


def build_json_artifact_payload(
    *,
    packet: ContextVocabularyPacket,
    used_paths: list[str],
    variant_runs: list[VariantRun],
    comparison_payload: dict[str, Any],
    model_id: str,
    source_span_count: int,
    generated_at: str,
    report_path: Path,
) -> dict[str, Any]:
    metrics = comparison_payload.get("metrics_by_variant", {})
    scores = comparison_payload.get("scores_by_variant", {})
    variants_by_name = {run.variant.variant_name: run for run in variant_runs}
    recommendation = _partition_aware_recommendation(
        comparison_payload=comparison_payload,
        variants_by_name=variants_by_name,
        markdown=False,
    )
    try:
        report_rel = str(report_path.relative_to(REPO_ROOT))
    except ValueError:
        report_rel = str(report_path)
    variant_setup = []
    for name in comparison_payload.get("variant_order", []):
        enable_node, enable_edge = VARIANT_FLAGS[name]
        run = variants_by_name[name]
        row_metrics = metrics.get(name, {})
        row_score = scores.get(name, {})
        variant_setup.append(
            {
                "variant_name": name,
                "enable_node_packet": enable_node,
                "enable_edge_packet": enable_edge,
                "node_count": len(run.variant.extracted_nodes or []),
                "edge_count": len(run.variant.extracted_edges or []),
                "total_cost_usd": run.raw_result.total_cost_usd,
                "score": row_score.get("score"),
                "known_name_pickup_rate": row_metrics.get("known_name_pickup_rate"),
                "combat_encounter_match_count": row_metrics.get("combat_encounter_match_count"),
                "predicate_hint_match_count": row_metrics.get("predicate_hint_match_count"),
                "unsafe_cross_class_blocked_count": row_metrics.get("unsafe_cross_class_blocked_count"),
                "recognition_rate": run.partition["recognition_rate"],
                "present_recognized": run.partition["present_recognized"],
                "present_missed": run.partition["present_missed"],
                "contamination_count": run.partition["contamination_count"],
                "contamination_rate": run.partition["contamination_rate"],
                "absent_contaminated": run.partition["absent_contaminated"],
                "node_kinds": run.node_count_by_kind,
                "edge_predicates": run.edge_count_by_predicate,
            }
        )
    return {
        "schema": "dmb_vocabulary_ablation_dogfood_v1",
        "generated_at": generated_at,
        "scope": "c2s23-mireward",
        "session_id": "session-23",
        "campaign_id": "longmont-c2",
        "model_id": model_id,
        "report_path": report_rel,
        "packet_id": packet.packet_id,
        "source_span_count": source_span_count,
        "source_files": used_paths,
        "partition": {
            "present_set": list(EXPECTED_PRESENT),
            "absent_set": list(EXPECTED_ABSENT),
        },
        "comparison": comparison_payload,
        "variant_setup": variant_setup,
        "recommendation": recommendation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run C2S23 Mireward vocabulary ablation dogfood comparison")
    parser.add_argument("--model", default=None, help="Override graph extraction model id")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-artifact-path", type=Path, default=DEFAULT_JSON_ARTIFACT_PATH)
    args = parser.parse_args()

    load_dungeonmindbuddy_dotenv()
    model_id = resolve_category_graph_model(args.model)
    span_index, used_paths = build_source_span_index()
    packet = build_packet()
    variant_runs = [
        run_variant(name, packet=packet, span_index=span_index, model_id=model_id)
        for name in VARIANT_FLAGS
    ]
    comparison = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[run.variant for run in variant_runs],
    )
    comparison_payload = vocabulary_ablation_comparison_to_payload(comparison)
    generated_at = _utc_now()
    report = render_report(
        packet=packet,
        used_paths=used_paths,
        variant_runs=variant_runs,
        comparison_payload=comparison_payload,
        comparison_markdown=render_vocabulary_ablation_comparison_markdown(comparison),
        model_id=model_id,
        source_span_count=len(span_index["spans"]),
        generated_at=generated_at,
    )
    report_path = args.report_path if args.report_path.is_absolute() else REPO_ROOT / args.report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report + "\n", encoding="utf-8")
    json_path = (
        args.json_artifact_path
        if args.json_artifact_path.is_absolute()
        else REPO_ROOT / args.json_artifact_path
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_payload = build_json_artifact_payload(
        packet=packet,
        used_paths=used_paths,
        variant_runs=variant_runs,
        comparison_payload=comparison_payload,
        model_id=model_id,
        source_span_count=len(span_index["spans"]),
        generated_at=generated_at,
        report_path=report_path,
    )
    json_path.write_text(json.dumps(json_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "json_artifact_path": str(json_path),
                "comparison": comparison_payload,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
