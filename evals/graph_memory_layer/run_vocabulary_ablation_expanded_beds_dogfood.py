#!/usr/bin/env python3
"""Run vocabulary ablation dogfood across expanded test beds.

Compares baseline, edge_packet, node_packet, and edge_and_node_packet on two
beds: C1S1 Stonebridge recap and Mirathorn city world doc. Packets are
corpus/registry-derived (never gold-derived). Emits a compact multi-bed report
and JSON artifact with per-bed GO criteria.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from evals.graph_memory_layer.live_vs_gold_compare import compare_parts, parts_from_raw_graph
from evals.graph_memory_layer.mirathorn_city_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID as MIRATHORN_GOLD_FIXTURE_ID,
    load_gold_candidate_graph_dict as load_mirathorn_gold_candidate_graph_dict,
)
from evals.graph_memory_layer.mirathorn_city_world_doc_fixture import (
    SOURCE_DOC_REL as MIRATHORN_SOURCE_DOC_REL,
    load_source_doc,
)
from evals.graph_memory_layer.session_1_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID as C1S1_GOLD_FIXTURE_ID,
    load_gold_candidate_graph_dict as load_c1s1_gold_candidate_graph_dict,
)
from evals.graph_memory_layer.session_1_recap_ingest_fixture import load_expected_normalized_recap
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
    context_packet_to_artifact_payload,
    diagnose_vocabulary_extraction_baseline,
    render_edge_vocabulary_context,
    render_context_vocabulary_packet,
    render_node_vocabulary_context,
    render_vocabulary_ablation_comparison_markdown,
    vocabulary_ablation_comparison_to_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-EXPANDED-BEDS.md"
)
DEFAULT_JSON_ARTIFACT_PATH = (
    REPO_ROOT
    / "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/expanded_beds_vocabulary_ablation.json"
)
DEFAULT_PROMPT_REVIEW_PATH = (
    REPO_ROOT
    / "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/expanded_beds_prompt_review.json"
)
DEFAULT_PROMPT_REVIEW_REPORT_PATH = (
    REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-VOCABULARY-ABLATION-PROMPT-REVIEW.md"
)
DEFAULT_MANUAL_REVIEW_DIR = (
    REPO_ROOT / "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review"
)
MANUAL_REVIEW_VARIANTS = ("baseline", "edge_and_node_packet")
C1S1_SOURCE_LABEL = "evals/graph_memory_layer/examples/session_1_recap_ingest/expected_normalized_recap.md"

VARIANT_FLAGS = {
    "baseline": (False, False),
    "edge_packet": (False, True),
    "node_packet": (True, False),
    "edge_and_node_packet": (True, True),
}

ALL_BEDS = ("c1s1-stonebridge", "mirathorn-city")
NODE_PASS_NAMES = ("actor_pass", "location_pass", "collective_pass", "object_pass", "thread_pass")


@dataclass(frozen=True, slots=True)
class BedConfig:
    bed_id: str
    campaign_id: str
    session_id: str
    session_number: int
    source_label: str
    source_artifact_id: str
    span_ref_prefix: str
    packet_seed: str
    gold_fixture_id: str
    load_source: Callable[[], str]
    load_gold: Callable[[], dict[str, Any]]
    expected_present: tuple[str, ...]
    expected_absent: tuple[str, ...]
    build_packet: Callable[[BedConfig], ContextVocabularyPacket]


@dataclass(slots=True)
class VariantRun:
    variant: VocabularyAblationVariant
    raw_result: Any
    node_count_by_kind: dict[str, int]
    edge_count_by_predicate: dict[str, int]
    partition: dict[str, Any]
    gold_comparison: dict[str, Any]


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


def build_source_span_index(bed: BedConfig) -> tuple[dict[str, Any], list[str]]:
    text = bed.load_source()
    spans: list[dict[str, Any]] = []
    ordinal = 0
    for line_start, line_end, block in _paragraph_blocks(text):
        if _is_frontmatter_or_heading(block):
            continue
        ordinal += 1
        spref = f"{bed.span_ref_prefix}:{ordinal:03d}"
        spans.append(
            {
                "source_span_ref_id": spref,
                "span_id": spref,
                "source_path": bed.source_label,
                "kind": "paragraph",
                "line_start": line_start,
                "line_end": line_end,
                "text": block.strip(),
            }
        )
    return {
        "schema": "dmb_dogfood_manual_source_span_index_v1",
        "source_artifact_id": bed.source_artifact_id,
        "spans": spans,
    }, [bed.source_label]


def _entry(
    vocab_id: str,
    label: str,
    kind: str,
    bed: BedConfig,
    *,
    aliases: Iterable[str] = (),
) -> VocabularyEntry:
    return VocabularyEntry(
        vocab_id=vocab_id,
        canonical_label=label,
        entity_kind=kind,  # type: ignore[arg-type]
        scope="campaign",
        campaign_id=bed.campaign_id,
        aliases=list(aliases),
        status="candidate",
        authority="manual_seed",
        notes="Dogfood-only packet entry; corpus/registry-derived, not gold-derived.",
    )


def _build_c1s1_packet(bed: BedConfig) -> ContextVocabularyPacket:
    entries = [
        _entry("vocab:c1s1:stone-bridge", "Stone Bridge", "place", bed),
        _entry("vocab:c1s1:glowkindle", "Glowkindle", "actor", bed),
        _entry("vocab:c1s1:grishna", "Grishna", "actor", bed),
        _entry("vocab:c1s1:wizards-tower-brewing-co", "Wizard's Tower Brewing Co", "place", bed),
        _entry("vocab:c1s1:rivers-edge-pub", "The River's Edge Pub", "place", bed),
        _entry("vocab:c1s1:karsemine", "Karsemine", "actor", bed),
        _entry("vocab:c1s1:bonogo", "Bonogo", "actor", bed),
        _entry("vocab:c1s1:lysandra-ironveil", "Captain Lysandra Ironveil", "actor", bed),
        _entry("vocab:c1s1:mireward-reach", "Mireward Reach", "place", bed),
        _entry("vocab:c1s1:the-shepherd", "The Shepherd", "actor", bed),
        _entry("vocab:c1s1:torbin-jove", "Torbin Jove", "actor", bed),
        _entry("vocab:c1s1:wizards-tower-org", "Wizard's Tower Brewing Co", "collective", bed),
        _entry("vocab:c1s1:stone-bridge-landmark", "Stone Bridge", "place", bed, aliases=("stone bridge",)),
    ]
    result = render_context_vocabulary_packet(
        scope="campaign",
        campaign_entries=entries,
        do_not_merge_hints=[
            DoNotMergeDecision(
                decision_id="dnm:c1s1:wizards-tower-place-vs-org",
                left_vocab_id="vocab:c1s1:wizards-tower-brewing-co",
                right_vocab_id="vocab:c1s1:wizards-tower-org",
                source="dogfood_manual_packet",
                reason="Place vs organization ambiguity for Wizard's Tower Brewing Co.",
            ),
            DoNotMergeDecision(
                decision_id="dnm:c1s1:stone-bridge-town-vs-landmark",
                left_vocab_id="vocab:c1s1:stone-bridge",
                right_vocab_id="vocab:c1s1:stone-bridge-landmark",
                source="dogfood_manual_packet",
                reason="Stone Bridge town vs literal stone bridge landmark must remain visible.",
            ),
        ],
        containment_hints=[
            ContainmentHint(
                hint_id="contain:c1s1:rivers-edge-in-stone-bridge",
                child_label="The River's Edge Pub",
                parent_label="Stone Bridge",
                child_vocab_id="vocab:c1s1:rivers-edge-pub",
                parent_vocab_id="vocab:c1s1:stone-bridge",
                relationship_type="located_in",
                status="candidate",
                authority="manual_seed",
            ),
        ],
        predicate_hints={
            "Stone Bridge": ["located_in", "present_at"],
            "Glowkindle": ["present_at", "located_in"],
            "Grishna": ["present_at"],
            "Wizard's Tower Brewing Co": ["located_in", "present_at"],
            "The River's Edge Pub": ["located_in"],
            "Karsemine": ["present_at"],
            "Bonogo": ["present_at"],
        },
        packet_seed=bed.packet_seed,
    )
    return result.packet


def _build_mirathorn_packet(bed: BedConfig) -> ContextVocabularyPacket:
    entries = [
        _entry("vocab:mira:mirathorn", "Mirathorn", "place", bed),
        _entry("vocab:mira:stormspire-peaks", "Stormspire Peaks", "place", bed),
        _entry("vocab:mira:lake-mirathorn", "Lake Mirathorn", "place", bed),
        _entry("vocab:mira:lundayell-empire", "Lundayell Empire", "collective", bed),
        _entry("vocab:mira:festival-of-expansion", "Festival of Expansion", "phenomenon", bed),
        _entry("vocab:mira:shepherds-flock", "Shepherd's Flock", "collective", bed),
        _entry("vocab:mira:wizards-tower-brewing-co", "Wizard's Tower Brewing Co", "place", bed),
        _entry("vocab:mira:stone-bridge", "Stone Bridge", "place", bed),
        _entry("vocab:mira:glowkindle", "Glowkindle", "actor", bed),
        _entry("vocab:mira:mireward-reach", "Mireward Reach", "place", bed),
        _entry("vocab:mira:karsemine", "Karsemine", "actor", bed),
        _entry("vocab:mira:stormspire-academy", "Stormspire Academy", "collective", bed),
        _entry("vocab:mira:wizards-college", "Wizard's College", "collective", bed),
    ]
    result = render_context_vocabulary_packet(
        scope="campaign",
        campaign_entries=entries,
        do_not_merge_hints=[
            DoNotMergeDecision(
                decision_id="dnm:mira:stormspire-academy-vs-wizards-college",
                left_vocab_id="vocab:mira:stormspire-academy",
                right_vocab_id="vocab:mira:wizards-college",
                source="dogfood_manual_packet",
                reason="Institutional ambiguity between Stormspire Academy and Wizard's College.",
            ),
        ],
        containment_hints=[
            ContainmentHint(
                hint_id="contain:mira:lake-in-mirathorn-area",
                child_label="Lake Mirathorn",
                parent_label="Mirathorn",
                child_vocab_id="vocab:mira:lake-mirathorn",
                parent_vocab_id="vocab:mira:mirathorn",
                relationship_type="located_in",
                status="candidate",
                authority="manual_seed",
            ),
        ],
        predicate_hints={
            "Mirathorn": ["located_in", "present_at"],
            "Stormspire Peaks": ["located_in"],
            "Lake Mirathorn": ["located_in"],
            "Lundayell Empire": ["governs", "located_in"],
            "Festival of Expansion": ["occurred_at", "present_at"],
            "Shepherd's Flock": ["present_at", "located_in"],
            "Wizard's Tower Brewing Co": ["located_in"],
        },
        packet_seed=bed.packet_seed,
    )
    return result.packet


BED_CONFIGS: dict[str, BedConfig] = {
    "c1s1-stonebridge": BedConfig(
        bed_id="c1s1-stonebridge",
        campaign_id="longmont-c1",
        session_id="session-1",
        session_number=1,
        source_label=C1S1_SOURCE_LABEL,
        source_artifact_id="source-artifact:longmont-c1:session-1:stonebridge-recap-vocabulary-dogfood",
        span_ref_prefix="spref:c1s1-recap",
        packet_seed="c1s1-stonebridge-recap-dogfood-v1",
        gold_fixture_id=C1S1_GOLD_FIXTURE_ID,
        load_source=load_expected_normalized_recap,
        load_gold=load_c1s1_gold_candidate_graph_dict,
        expected_present=(
            "Stone Bridge",
            "Glowkindle",
            "Grishna",
            "Wizard's Tower Brewing Co",
            "The River's Edge Pub",
            "Karsemine",
            "Bonogo",
        ),
        expected_absent=(
            "Captain Lysandra Ironveil",
            "Mireward Reach",
            "The Shepherd",
            "Torbin Jove",
        ),
        build_packet=_build_c1s1_packet,
    ),
    "mirathorn-city": BedConfig(
        bed_id="mirathorn-city",
        campaign_id="elderwyld",
        session_id="mirathorn-city",
        session_number=0,
        source_label=MIRATHORN_SOURCE_DOC_REL,
        source_artifact_id="source-artifact:elderwyld:mirathorn-city-world-doc-vocabulary-dogfood",
        span_ref_prefix="spref:mirathorn-city",
        packet_seed="mirathorn-city-world-doc-dogfood-v1",
        gold_fixture_id=MIRATHORN_GOLD_FIXTURE_ID,
        load_source=load_source_doc,
        load_gold=load_mirathorn_gold_candidate_graph_dict,
        expected_present=(
            "Mirathorn",
            "Stormspire Peaks",
            "Lake Mirathorn",
            "Lundayell Empire",
            "Festival of Expansion",
            "Shepherd's Flock",
            "Wizard's Tower Brewing Co",
        ),
        expected_absent=(
            "Stone Bridge",
            "Glowkindle",
            "Mireward Reach",
            "Karsemine",
        ),
        build_packet=_build_mirathorn_packet,
    ),
}


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


def _partition_metrics(
    diagnostics: Mapping[str, Any],
    *,
    expected_present: tuple[str, ...],
    expected_absent: tuple[str, ...],
) -> dict[str, Any]:
    matched = set(diagnostics.get("known_name_pickup", {}).get("matched", []))
    present_recognized = sorted(name for name in expected_present if name in matched)
    present_missed = sorted(name for name in expected_present if name not in matched)
    absent_contaminated = sorted(name for name in expected_absent if name in matched)
    absent_clean = sorted(name for name in expected_absent if name not in matched)
    present_count = len(expected_present)
    absent_count = len(expected_absent)
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


def _gold_node_labels(missing_entries: Iterable[Any]) -> set[str]:
    labels: set[str] = set()
    for entry in missing_entries:
        if isinstance(entry, Mapping):
            label = str(entry.get("label") or "").strip()
            if label:
                labels.add(label)
    return labels


def run_variant(
    name: str,
    *,
    bed: BedConfig,
    packet: ContextVocabularyPacket,
    span_index: Mapping[str, Any],
    gold_parts: Mapping[str, Any],
    model_id: str | None,
) -> VariantRun:
    enable_node, enable_edge = VARIANT_FLAGS[name]
    print(f"[{bed.bed_id}] variant {name}: extraction starting...", flush=True)
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id=bed.campaign_id,
            session_id=bed.session_id,
            session_number=bed.session_number,
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
    gold_comparison = compare_parts(
        parts_from_raw_graph(result.candidate_graph),
        gold_parts,
        gold_fixture_id=bed.gold_fixture_id,
        report_id=f"graph-memory:vocabulary-ablation-dogfood:{bed.bed_id}:{name}",
    )
    node_count_by_kind = dict(sorted(Counter(node.entity_kind for node in nodes).items()))
    edge_count_by_predicate = dict(sorted(Counter(edge.predicate for edge in edges).items()))
    print(
        f"[{bed.bed_id}] variant {name}: done "
        f"({len(nodes)} nodes, {len(edges)} edges, ${result.total_cost_usd:.4f})",
        flush=True,
    )
    return VariantRun(
        variant=variant,
        raw_result=result,
        node_count_by_kind=node_count_by_kind,
        edge_count_by_predicate=edge_count_by_predicate,
        partition=_partition_metrics(
            diagnostics,
            expected_present=bed.expected_present,
            expected_absent=bed.expected_absent,
        ),
        gold_comparison=gold_comparison,
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
    clean_variants = [name for name in order if variants_by_name[name].partition["contamination_count"] == 0]
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


def _pick_best_clean_variant(
    *,
    comparison_payload: Mapping[str, Any],
    variants_by_name: Mapping[str, VariantRun],
) -> str:
    order = list(comparison_payload.get("variant_order", []))
    scores = comparison_payload.get("scores_by_variant", {})
    clean = [
        name
        for name in order
        if variants_by_name[name].partition["contamination_count"] == 0 and name != "baseline"
    ]
    if not clean:
        return "baseline"
    return max(
        clean,
        key=lambda name: (
            scores.get(name, {}).get("score", 0),
            variants_by_name[name].partition["recognition_rate"],
            name,
        ),
    )


def _compute_go_criteria(
    *,
    bed: BedConfig,
    packet: ContextVocabularyPacket,
    comparison_payload: Mapping[str, Any],
    variants_by_name: Mapping[str, VariantRun],
) -> dict[str, Any]:
    metrics = comparison_payload.get("metrics_by_variant", {})
    baseline_metrics = metrics.get("baseline", {})
    baseline_gold = variants_by_name["baseline"].gold_comparison.get("scores", {})
    best_clean = _pick_best_clean_variant(
        comparison_payload=comparison_payload,
        variants_by_name=variants_by_name,
    )
    best_metrics = metrics.get(best_clean, baseline_metrics)
    best_gold = variants_by_name[best_clean].gold_comparison.get("scores", {})
    best_partition = variants_by_name[best_clean].partition

    baseline_missing = _gold_node_labels(
        variants_by_name["baseline"].gold_comparison.get("coverage", {}).get("missing_gold_nodes", [])
    )
    best_missing = _gold_node_labels(
        variants_by_name[best_clean].gold_comparison.get("coverage", {}).get("missing_gold_nodes", [])
    )
    packet_known = set(packet.known_names)
    newly_matched_not_in_packet = sorted(
        label for label in (baseline_missing - best_missing) if label not in packet_known
    )

    go1 = (
        best_metrics.get("duplicate_label_collision_count", 0)
        < baseline_metrics.get("duplicate_label_collision_count", 0)
        or best_metrics.get("unsafe_cross_class_blocked_count", 0)
        < baseline_metrics.get("unsafe_cross_class_blocked_count", 0)
    )
    go2 = best_metrics.get("edge_drop_count", 0) < baseline_metrics.get("edge_drop_count", 0)
    go3 = (
        best_gold.get("node_recall", 0.0) >= baseline_gold.get("node_recall", 0.0)
        and best_gold.get("edge_recall", 0.0) >= baseline_gold.get("edge_recall", 0.0)
    )
    go4 = best_partition.get("contamination_count", 0) == 0
    go5 = bool(newly_matched_not_in_packet)

    return {
        "best_clean_variant": best_clean,
        "GO-1": go1,
        "GO-2": go2,
        "GO-3": go3,
        "GO-4": go4,
        "GO-5": go5,
        "newly_matched_gold_nodes_not_in_packet": newly_matched_not_in_packet,
        "baseline_duplicate_label_collision_count": baseline_metrics.get("duplicate_label_collision_count", 0),
        "best_duplicate_label_collision_count": best_metrics.get("duplicate_label_collision_count", 0),
        "baseline_unsafe_cross_class_blocked_count": baseline_metrics.get("unsafe_cross_class_blocked_count", 0),
        "best_unsafe_cross_class_blocked_count": best_metrics.get("unsafe_cross_class_blocked_count", 0),
        "baseline_edge_drop_count": baseline_metrics.get("edge_drop_count", 0),
        "best_edge_drop_count": best_metrics.get("edge_drop_count", 0),
        "baseline_node_recall": baseline_gold.get("node_recall", 0.0),
        "best_node_recall": best_gold.get("node_recall", 0.0),
        "baseline_edge_recall": baseline_gold.get("edge_recall", 0.0),
        "best_edge_recall": best_gold.get("edge_recall", 0.0),
        "best_contamination_count": best_partition.get("contamination_count", 0),
    }


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _variant_setup_rows(
    comparison_payload: Mapping[str, Any],
    variants_by_name: Mapping[str, VariantRun],
) -> list[dict[str, Any]]:
    metrics = comparison_payload.get("metrics_by_variant", {})
    scores = comparison_payload.get("scores_by_variant", {})
    rows: list[dict[str, Any]] = []
    for name in comparison_payload.get("variant_order", []):
        enable_node, enable_edge = VARIANT_FLAGS[name]
        run = variants_by_name[name]
        row_metrics = metrics.get(name, {})
        row_score = scores.get(name, {})
        rows.append(
            {
                "variant_name": name,
                "enable_node_packet": enable_node,
                "enable_edge_packet": enable_edge,
                "node_count": len(run.variant.extracted_nodes or []),
                "edge_count": len(run.variant.extracted_edges or []),
                "total_cost_usd": run.raw_result.total_cost_usd,
                "score": row_score.get("score"),
                "known_name_pickup_rate": row_metrics.get("known_name_pickup_rate"),
                "predicate_hint_match_count": row_metrics.get("predicate_hint_match_count"),
                "unsafe_cross_class_blocked_count": row_metrics.get("unsafe_cross_class_blocked_count"),
                "edge_drop_count": row_metrics.get("edge_drop_count"),
                "duplicate_label_collision_count": row_metrics.get("duplicate_label_collision_count"),
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
    return rows


def _gold_scores_by_variant(variants_by_name: Mapping[str, VariantRun]) -> dict[str, dict[str, float]]:
    return {
        name: {
            "node_recall": run.gold_comparison.get("scores", {}).get("node_recall", 0.0),
            "edge_recall": run.gold_comparison.get("scores", {}).get("edge_recall", 0.0),
        }
        for name, run in variants_by_name.items()
    }


def run_bed(bed: BedConfig, *, model_id: str) -> dict[str, Any]:
    span_index, used_paths = build_source_span_index(bed)
    packet = bed.build_packet(bed)
    gold_parts = parts_from_raw_graph(bed.load_gold())
    variant_runs = [
        run_variant(
            name,
            bed=bed,
            packet=packet,
            span_index=span_index,
            gold_parts=gold_parts,
            model_id=model_id,
        )
        for name in VARIANT_FLAGS
    ]
    comparison = compare_vocabulary_ablation_variants(
        packet=packet,
        variants=[run.variant for run in variant_runs],
    )
    comparison_payload = vocabulary_ablation_comparison_to_payload(comparison)
    variants_by_name = {run.variant.variant_name: run for run in variant_runs}
    go_criteria = _compute_go_criteria(
        bed=bed,
        packet=packet,
        comparison_payload=comparison_payload,
        variants_by_name=variants_by_name,
    )
    return {
        "bed_id": bed.bed_id,
        "campaign_id": bed.campaign_id,
        "session_id": bed.session_id,
        "session_number": bed.session_number,
        "gold_fixture_id": bed.gold_fixture_id,
        "packet_id": packet.packet_id,
        "source_span_count": len(span_index["spans"]),
        "source_files": used_paths,
        "partition": {
            "present_set": list(bed.expected_present),
            "absent_set": list(bed.expected_absent),
        },
        "variant_setup": _variant_setup_rows(comparison_payload, variants_by_name),
        "comparison": comparison_payload,
        "comparison_markdown": render_vocabulary_ablation_comparison_markdown(comparison),
        "gold_scores_by_variant": _gold_scores_by_variant(variants_by_name),
        "go_criteria": go_criteria,
        "recommendation": _partition_aware_recommendation(
            comparison_payload=comparison_payload,
            variants_by_name=variants_by_name,
            markdown=False,
        ),
        "variant_runs": variant_runs,
        "packet": packet,
    }


def _manual_review_graph_relpath(bed_id: str, variant_name: str) -> str:
    return (
        f"evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/"
        f"{bed_id}_{variant_name}_candidate_graph.json"
    )


def _gold_compare_summary(gold_comparison: Mapping[str, Any]) -> dict[str, Any]:
    if "scores" in gold_comparison and isinstance(gold_comparison.get("scores"), Mapping):
        scores = gold_comparison["scores"]
        coverage = gold_comparison.get("coverage", {}) if isinstance(gold_comparison.get("coverage"), Mapping) else {}
        missing_nodes = coverage.get("missing_gold_nodes", []) or []
        extra_nodes = coverage.get("extra_candidate_nodes", []) or []
        missing_edges = coverage.get("missing_gold_edges", []) or []
        edge_miss = (
            gold_comparison.get("diagnostics", {}).get("edge_miss_diagnostics", {})
            if isinstance(gold_comparison.get("diagnostics"), Mapping)
            else {}
        )
    else:
        return dict(gold_comparison)
    if not missing_edges and isinstance(edge_miss, Mapping):
        missing_edges = [
            {"label": detail.get("gold_edge_label") or edge_id}
            for edge_id, detail in edge_miss.items()
            if isinstance(detail, Mapping)
        ]
    return {
        "node_recall": scores.get("node_recall"),
        "edge_recall": scores.get("edge_recall"),
        "missing_gold_node_labels": [
            str(entry.get("label") or entry)
            if isinstance(entry, Mapping)
            else str(entry)
            for entry in missing_nodes
        ],
        "extra_candidate_node_labels": [
            str(entry.get("label") or entry)
            if isinstance(entry, Mapping)
            else str(entry)
            for entry in extra_nodes
        ],
        "missing_gold_edge_labels": [
            str(entry.get("label") or entry.get("detail") or entry)
            if isinstance(entry, Mapping)
            else str(entry)
            for entry in missing_edges
        ],
    }


def _normalized_gold_summary(raw: Mapping[str, Any]) -> dict[str, Any]:
    if "node_recall" in raw and "missing_gold_node_labels" in raw:
        return dict(raw)
    return _gold_compare_summary(raw)


def build_manual_review_bed_entry(
    result: Mapping[str, Any],
    *,
    prompt_review_bed: Mapping[str, Any] | None,
    out_dir: Path,
) -> dict[str, Any]:
    bed_id = str(result["bed_id"])
    variants_by_name = {run.variant.variant_name: run for run in result["variant_runs"]}
    variant_entries: dict[str, Any] = {}
    for variant_name in MANUAL_REVIEW_VARIANTS:
        run = variants_by_name[variant_name]
        graph_path = out_dir / f"{bed_id}_{variant_name}_candidate_graph.json"
        graph_path.write_text(
            json.dumps(run.raw_result.candidate_graph, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        consolidation = run.raw_result.consolidation_diagnostics or {}
        variant_entries[variant_name] = {
            "candidate_graph": run.raw_result.candidate_graph,
            "candidate_graph_path": _manual_review_graph_relpath(bed_id, variant_name),
            "cost_usd": run.raw_result.total_cost_usd,
            "diagnostics": run.variant.extraction_diagnostics,
            "run_diagnostics": run.variant.extraction_run_diagnostics,
            "gold_comparison": _gold_compare_summary(run.gold_comparison),
            "node_count": len(run.variant.extracted_nodes or []),
            "edge_count": len(run.variant.extracted_edges or []),
            "node_kinds": run.node_count_by_kind,
            "edge_predicates": run.edge_count_by_predicate,
            "partition": run.partition,
            "party_context": {
                "party_anchor_hub_paths": consolidation.get("party_anchor_hub_paths", []),
                "inserted_party_anchor_slugs": consolidation.get("inserted_party_anchor_slugs", []),
                "party_collective_inserted": consolidation.get("party_collective_inserted", False),
                "party_membership_edge_slugs": consolidation.get("party_membership_edge_slugs", []),
                "session_graph_context_warnings": consolidation.get("session_graph_context_warnings", []),
            },
        }
    entry: dict[str, Any] = {
        "bed_id": bed_id,
        "campaign_id": result["campaign_id"],
        "session_id": result["session_id"],
        "source_label": BED_CONFIGS[bed_id].source_label,
        "variants": variant_entries,
    }
    if prompt_review_bed is not None:
        entry["node_prompt_contexts"] = prompt_review_bed.get("node_prompt_contexts")
        entry["edge_prompt_context"] = prompt_review_bed.get("edge_prompt_context")
    return entry


def render_manual_review_markdown(
    *,
    bed_entries: list[Mapping[str, Any]],
    generated_at: str,
    model_id: str,
) -> str:
    lines = [
        "# Vocabulary Ablation Manual Review — Baseline vs Edge+Node",
        "",
        f"Generated: {generated_at}",
        f"Model: `{model_id}`",
        "",
    ]
    for bed in bed_entries:
        bed_id = bed["bed_id"]
        source_label = bed.get("source_label")
        if not source_label:
            source_files = bed.get("source_files")
            if isinstance(source_files, list) and source_files:
                source_label = source_files[0]
        lines.extend(
            [
                f"## {bed_id}",
                "",
                f"Source: {source_label or ''}",
                "",
            ]
        )
        variants = bed.get("variants", {}) if isinstance(bed.get("variants"), Mapping) else {}
        for variant_name in MANUAL_REVIEW_VARIANTS:
            row = variants.get(variant_name, {}) if isinstance(variants.get(variant_name), Mapping) else {}
            gold = _normalized_gold_summary(
                row.get("gold_comparison", {}) if isinstance(row.get("gold_comparison"), Mapping) else {}
            )
            partition = row.get("partition", {}) if isinstance(row.get("partition"), Mapping) else {}
            party = row.get("party_context", {}) if isinstance(row.get("party_context"), Mapping) else {}
            lines.extend(
                [
                    f"### `{variant_name}`",
                    "",
                    f"- Nodes: {row.get('node_count', 0)}; edges: {row.get('edge_count', 0)}; cost: ${float(row.get('cost_usd') or 0.0):.6f}",
                    f"- Node recall: {gold.get('node_recall')}; edge recall: {gold.get('edge_recall')}",
                    f"- Recognition: {partition.get('recognition_rate')} ({len(partition.get('present_recognized') or [])}/{partition.get('present_count')}); contamination: {partition.get('contamination_count')}/{partition.get('absent_count')}",
                    f"- Party anchors inserted: {party.get('inserted_party_anchor_slugs', [])}",
                    f"- Party collective inserted: {party.get('party_collective_inserted')}",
                    f"- Party membership edges: {party.get('party_membership_edge_slugs', [])}",
                    f"- Session context warnings: {party.get('session_graph_context_warnings', [])}",
                    f"- Node kinds: `{row.get('node_kinds')}`",
                    f"- Edge predicates: `{row.get('edge_predicates')}`",
                    f"- Missing gold nodes: {', '.join(gold.get('missing_gold_node_labels') or []) or 'none'}",
                    f"- Extra candidate nodes: {', '.join(gold.get('extra_candidate_node_labels') or []) or 'none'}",
                    f"- Missing gold edges: {', '.join(gold.get('missing_gold_edge_labels') or []) or 'none'}",
                    "",
                ]
            )
    return "\n".join(lines)


def write_manual_review_artifacts(
    *,
    bed_results: list[dict[str, Any]],
    prompt_review_payload: Mapping[str, Any],
    generated_at: str,
    model_id: str,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_beds = {
        str(bed.get("bed_id")): bed
        for bed in prompt_review_payload.get("beds", [])
        if isinstance(bed, Mapping)
    }
    new_entries = {
        result["bed_id"]: build_manual_review_bed_entry(
            result,
            prompt_review_bed=prompt_beds.get(result["bed_id"]),
            out_dir=out_dir,
        )
        for result in bed_results
    }
    bundle_path = out_dir / "baseline_vs_edge_and_node_manual_review.json"
    existing_beds: dict[str, Any] = {}
    if bundle_path.is_file():
        existing_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        for bed in existing_payload.get("beds", []) or []:
            if isinstance(bed, Mapping) and bed.get("bed_id"):
                existing_beds[str(bed["bed_id"])] = bed
    existing_beds.update(new_entries)
    merged_beds = [existing_beds[bed_id] for bed_id in ALL_BEDS if bed_id in existing_beds]
    bundle_payload = {
        "schema": "dmb_vocabulary_ablation_manual_review_v1",
        "generated_at": generated_at,
        "model_id": model_id,
        "variants": list(MANUAL_REVIEW_VARIANTS),
        "beds": merged_beds,
    }
    bundle_path.write_text(json.dumps(bundle_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_path = out_dir / "baseline_vs_edge_and_node_manual_review.md"
    summary_path.write_text(
        render_manual_review_markdown(
            bed_entries=merged_beds,
            generated_at=generated_at,
            model_id=model_id,
        )
        + "\n",
        encoding="utf-8",
    )


def render_report(*, bed_results: list[dict[str, Any]], model_id: str, generated_at: str) -> str:
    lines = [
        "# Graph Memory Vocabulary Ablation Dogfood — Expanded Test Beds",
        "",
        f"Generated: {generated_at}",
        "",
        "## 1. Scope",
        "",
        "Dogfood run comparing `baseline`, `edge_packet`, `node_packet`, and `edge_and_node_packet` on two expanded test beds: C1S1 Stonebridge recap and Mirathorn city world doc. Packets are corpus/registry-derived, never gold-derived.",
        "",
        f"- Model: `{model_id}`",
        f"- Beds: {', '.join(f'`{r['bed_id']}`' for r in bed_results)}",
        "",
    ]
    for result in bed_results:
        bed_id = result["bed_id"]
        comparison_payload = result["comparison"]
        variants_by_name = {run.variant.variant_name: run for run in result["variant_runs"]}
        metrics = comparison_payload["metrics_by_variant"]
        present = result["partition"]["present_set"]
        absent = result["partition"]["absent_set"]
        go = result["go_criteria"]
        lines.extend(
            [
                f"## Bed: `{bed_id}`",
                "",
                f"- Campaign/session: `{result['campaign_id']}` / `{result['session_id']}` (session_number={result['session_number']})",
                f"- Gold fixture: `{result['gold_fixture_id']}`",
                f"- Source spans: {result['source_span_count']}",
                f"- Packet: `{result['packet_id']}`",
                "",
                "### Variant setup",
                "",
                "| Variant | Node packet | Edge packet | Nodes | Edges | Cost USD |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for name in comparison_payload["variant_order"]:
            run = variants_by_name[name]
            enable_node, enable_edge = VARIANT_FLAGS[name]
            lines.append(
                f"| {name} | {_yes_no(enable_node)} | {_yes_no(enable_edge)} | "
                f"{len(run.variant.extracted_nodes or [])} | {len(run.variant.extracted_edges or [])} | "
                f"{run.raw_result.total_cost_usd:.6f} |"
            )
        lines.extend(
            [
                "",
                "### Comparison table",
                "",
                result["comparison_markdown"],
                "",
                "### Present vs absent partition",
                "",
                f"Present-set ({len(present)} names): {', '.join(f'`{n}`' for n in present)}.",
                "",
                f"Absent-set ({len(absent)} names): {', '.join(f'`{n}`' for n in absent)}.",
                "",
                "| Variant | Recognition (present) | Contamination (absent) |",
                "|---|---:|---:|",
            ]
        )
        for name in comparison_payload["variant_order"]:
            part = variants_by_name[name].partition
            lines.append(
                f"| {name} | {part['recognition_rate']:.3f} ({len(part['present_recognized'])}/{part['present_count']}) "
                f"| {part['contamination_count']}/{part['absent_count']} |"
            )
        lines.extend(
            [
                "",
                "### Gold recall (candidate graph gold)",
                "",
                "| Variant | Node recall | Edge recall |",
                "|---|---:|---:|",
            ]
        )
        for name in comparison_payload["variant_order"]:
            scores = result["gold_scores_by_variant"][name]
            lines.append(f"| {name} | {scores['node_recall']:.4f} | {scores['edge_recall']:.4f} |")
        lines.extend(
            [
                "",
                "### GO criteria (best clean variant vs baseline)",
                "",
                f"- Best clean variant: `{go['best_clean_variant']}`",
                f"- GO-1 (structural): {_yes_no(go['GO-1'])}",
                f"- GO-2 (edge drops): {_yes_no(go['GO-2'])}",
                f"- GO-3 (gold recall): {_yes_no(go['GO-3'])}",
                f"- GO-4 (contamination): {_yes_no(go['GO-4'])}",
                f"- GO-5 (generalization): {_yes_no(go['GO-5'])}",
            ]
        )
        if go.get("newly_matched_gold_nodes_not_in_packet"):
            lines.append(
                "- New gold nodes matched outside packet: "
                + ", ".join(f"`{label}`" for label in go["newly_matched_gold_nodes_not_in_packet"])
            )
        lines.extend(
            [
                "",
                "### Recommendation",
                "",
                result["recommendation"],
                "",
                f"- Best pooled known-name pickup: `{_best_by(metrics, 'known_name_pickup_rate')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Separation Of Claims",
            "",
            "Observed dogfood behavior: metrics above come from fresh LLM extraction runs over the two expanded beds.",
            "",
            "Synthetic harness validation: unit tests validate comparison/diagnostics APIs; they do not prove model quality.",
            "",
            "Speculation / recommendations: per-bed recommendations identify what to try next, not production defaults.",
            "",
        ]
    )
    return "\n".join(lines)


def build_prompt_review_payload(
    *,
    beds: list[BedConfig],
    generated_at: str,
    prompt_review_report_path: Path,
) -> dict[str, Any]:
    try:
        report_rel = str(prompt_review_report_path.relative_to(REPO_ROOT))
    except ValueError:
        report_rel = str(prompt_review_report_path)

    review_beds: list[dict[str, Any]] = []
    for bed in beds:
        packet = bed.build_packet(bed)
        node_contexts = {
            pass_name: {
                "context_text": (ctx := render_node_vocabulary_context(packet, pass_name=pass_name)).context_text,
                "diagnostics": ctx.diagnostics,
            }
            for pass_name in NODE_PASS_NAMES
        }
        edge_context = render_edge_vocabulary_context(packet)
        review_beds.append(
            {
                "bed_id": bed.bed_id,
                "campaign_id": bed.campaign_id,
                "session_id": bed.session_id,
                "session_number": bed.session_number,
                "source_files": [bed.source_label],
                "partition": {
                    "present_set": list(bed.expected_present),
                    "absent_set": list(bed.expected_absent),
                },
                "packet": context_packet_to_artifact_payload(packet),
                "node_prompt_contexts": node_contexts,
                "edge_prompt_context": {
                    "context_text": edge_context.context_text,
                    "diagnostics": edge_context.diagnostics,
                },
                "variant_prompt_context_map": {
                    "baseline": {"node_contexts": [], "edge_context": None},
                    "edge_packet": {"node_contexts": [], "edge_context": edge_context.context_text},
                    "node_packet": {
                        "node_contexts": {
                            pass_name: node_contexts[pass_name]["context_text"] for pass_name in NODE_PASS_NAMES
                        },
                        "edge_context": None,
                    },
                    "edge_and_node_packet": {
                        "node_contexts": {
                            pass_name: node_contexts[pass_name]["context_text"] for pass_name in NODE_PASS_NAMES
                        },
                        "edge_context": edge_context.context_text,
                    },
                },
            }
        )
    return {
        "schema": "dmb_vocabulary_ablation_prompt_review_v1",
        "generated_at": generated_at,
        "scope": "expanded-beds",
        "report_path": report_rel,
        "beds": review_beds,
    }


def render_prompt_review_report(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Graph Memory Vocabulary Ablation — Prompt Review",
        "",
        f"Generated: {payload.get('generated_at')}",
        "",
        "This report shows the corpus/registry-derived vocabulary packet and the exact compact vocabulary context rendered into node and edge extraction prompts. It is a manual-review artifact; it does not contain LLM output.",
        "",
    ]
    for bed in payload.get("beds", []):
        if not isinstance(bed, Mapping):
            continue
        packet = bed.get("packet", {}) if isinstance(bed.get("packet"), Mapping) else {}
        lines.extend(
            [
                f"## Bed: `{bed.get('bed_id')}`",
                "",
                f"- Campaign/session: `{bed.get('campaign_id')}` / `{bed.get('session_id')}`",
                f"- Packet: `{packet.get('packet_id')}`",
                f"- Known names: {len(packet.get('known_names', []) or [])}",
                f"- Type hints: {len(packet.get('type_hints', {}) or {})}",
                f"- Predicate hint subjects: {len(packet.get('predicate_hints', {}) or {})}",
                f"- Do-not-merge hints: {len(packet.get('do_not_merge_hints', []) or [])}",
                f"- Containment hints: {len(packet.get('containment_hints', []) or [])}",
                "",
                "### Known names and type hints",
                "",
            ]
        )
        type_hints = packet.get("type_hints", {}) if isinstance(packet.get("type_hints"), Mapping) else {}
        for name in packet.get("known_names", []) or []:
            lines.append(f"- `{name}` — `{type_hints.get(name, 'unknown')}`")
        lines.extend(["", "### Predicate hints", ""])
        predicate_hints = packet.get("predicate_hints", {}) if isinstance(packet.get("predicate_hints"), Mapping) else {}
        for name, predicates in predicate_hints.items():
            joined = ", ".join(f"`{predicate}`" for predicate in predicates)
            lines.append(f"- `{name}`: {joined}")
        lines.extend(["", "### Do-not-merge hints", ""])
        for hint in packet.get("do_not_merge_hints", []) or []:
            if isinstance(hint, Mapping):
                lines.append(f"- `{hint.get('left_vocab_id')}` != `{hint.get('right_vocab_id')}` — {hint.get('reason')}")
        lines.extend(["", "### Containment hints", ""])
        for hint in packet.get("containment_hints", []) or []:
            if isinstance(hint, Mapping):
                lines.append(f"- `{hint.get('child_label')}` -> `{hint.get('parent_label')}`")
        lines.extend(["", "### Node prompt contexts", ""])
        node_contexts = bed.get("node_prompt_contexts", {}) if isinstance(bed.get("node_prompt_contexts"), Mapping) else {}
        for pass_name in NODE_PASS_NAMES:
            context_row = node_contexts.get(pass_name, {}) if isinstance(node_contexts.get(pass_name), Mapping) else {}
            text = str(context_row.get("context_text") or "").strip()
            if not text:
                lines.extend([f"#### `{pass_name}`", "", "(No vocabulary context rendered for this pass.)", ""])
                continue
            lines.extend([f"#### `{pass_name}`", "", "```text", text, "```", ""])
        edge_context = bed.get("edge_prompt_context", {}) if isinstance(bed.get("edge_prompt_context"), Mapping) else {}
        lines.extend(["### Edge prompt context", "", "```text", str(edge_context.get("context_text") or "").strip(), "```", ""])
    return "\n".join(lines)


def build_json_artifact_payload(
    *,
    bed_results: list[dict[str, Any]],
    model_id: str,
    generated_at: str,
    report_path: Path,
) -> dict[str, Any]:
    try:
        report_rel = str(report_path.relative_to(REPO_ROOT))
    except ValueError:
        report_rel = str(report_path)
    beds = []
    for result in bed_results:
        beds.append(
            {
                "bed_id": result["bed_id"],
                "campaign_id": result["campaign_id"],
                "session_id": result["session_id"],
                "session_number": result["session_number"],
                "gold_fixture_id": result["gold_fixture_id"],
                "packet_id": result["packet_id"],
                "source_span_count": result["source_span_count"],
                "source_files": result["source_files"],
                "partition": result["partition"],
                "variant_setup": result["variant_setup"],
                "comparison": result["comparison"],
                "gold_scores_by_variant": result["gold_scores_by_variant"],
                "go_criteria": {
                    "best_clean_variant": result["go_criteria"]["best_clean_variant"],
                    "GO-1": result["go_criteria"]["GO-1"],
                    "GO-2": result["go_criteria"]["GO-2"],
                    "GO-3": result["go_criteria"]["GO-3"],
                    "GO-4": result["go_criteria"]["GO-4"],
                    "GO-5": result["go_criteria"]["GO-5"],
                    "newly_matched_gold_nodes_not_in_packet": result["go_criteria"][
                        "newly_matched_gold_nodes_not_in_packet"
                    ],
                },
                "recommendation": result["recommendation"],
            }
        )
    return {
        "schema": "dmb_vocabulary_ablation_dogfood_v1",
        "generated_at": generated_at,
        "scope": "expanded-beds",
        "model_id": model_id,
        "report_path": report_rel,
        "beds": beds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run expanded-bed vocabulary ablation dogfood comparison"
    )
    parser.add_argument(
        "--bed",
        choices=[*ALL_BEDS, "all"],
        default="all",
        help="Which test bed to run (default: all)",
    )
    parser.add_argument("--model", default=None, help="Override graph extraction model id")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-artifact-path", type=Path, default=DEFAULT_JSON_ARTIFACT_PATH)
    parser.add_argument("--prompt-review-path", type=Path, default=DEFAULT_PROMPT_REVIEW_PATH)
    parser.add_argument("--prompt-review-report-path", type=Path, default=DEFAULT_PROMPT_REVIEW_REPORT_PATH)
    parser.add_argument(
        "--review-only",
        action="store_true",
        help="Write packet/prompt review artifacts without running LLM extraction",
    )
    args = parser.parse_args()

    load_dungeonmindbuddy_dotenv()
    model_id = resolve_category_graph_model(args.model)
    bed_ids = list(ALL_BEDS) if args.bed == "all" else [args.bed]
    generated_at = _utc_now()
    report_path = args.report_path if args.report_path.is_absolute() else REPO_ROOT / args.report_path
    json_path = (
        args.json_artifact_path
        if args.json_artifact_path.is_absolute()
        else REPO_ROOT / args.json_artifact_path
    )
    prompt_review_path = (
        args.prompt_review_path if args.prompt_review_path.is_absolute() else REPO_ROOT / args.prompt_review_path
    )
    prompt_review_report_path = (
        args.prompt_review_report_path
        if args.prompt_review_report_path.is_absolute()
        else REPO_ROOT / args.prompt_review_report_path
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_review_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_review_report_path.parent.mkdir(parents=True, exist_ok=True)

    selected_beds = [BED_CONFIGS[bed_id] for bed_id in bed_ids]
    prompt_review_payload = build_prompt_review_payload(
        beds=selected_beds,
        generated_at=generated_at,
        prompt_review_report_path=prompt_review_report_path,
    )
    prompt_review_path.write_text(
        json.dumps(prompt_review_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    prompt_review_report_path.write_text(render_prompt_review_report(prompt_review_payload) + "\n", encoding="utf-8")
    if args.review_only:
        print(
            json.dumps(
                {
                    "prompt_review_path": str(prompt_review_path),
                    "prompt_review_report_path": str(prompt_review_report_path),
                    "beds": bed_ids,
                },
                indent=2,
            )
        )
        return

    bed_results: list[dict[str, Any]] = []
    for bed_id in bed_ids:
        print(f"=== bed {bed_id} ===", flush=True)
        bed_results.append(run_bed(BED_CONFIGS[bed_id], model_id=model_id))
        json_payload = build_json_artifact_payload(
            bed_results=bed_results,
            model_id=model_id,
            generated_at=generated_at,
            report_path=report_path,
        )
        json_path.write_text(json.dumps(json_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checkpoint_beds = [BED_CONFIGS[result["bed_id"]] for result in bed_results]
        prompt_review_payload = build_prompt_review_payload(
            beds=checkpoint_beds,
            generated_at=generated_at,
            prompt_review_report_path=prompt_review_report_path,
        )
        prompt_review_path.write_text(
            json.dumps(prompt_review_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        prompt_review_report_path.write_text(
            render_prompt_review_report(prompt_review_payload) + "\n",
            encoding="utf-8",
        )
        write_manual_review_artifacts(
            bed_results=bed_results,
            prompt_review_payload=prompt_review_payload,
            generated_at=generated_at,
            model_id=model_id,
            out_dir=DEFAULT_MANUAL_REVIEW_DIR,
        )
        print(f"checkpoint: wrote {len(bed_results)} bed(s) to {json_path}", flush=True)

    report = render_report(bed_results=bed_results, model_id=model_id, generated_at=generated_at)
    report_path.write_text(report + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "json_artifact_path": str(json_path),
                "beds": [result["bed_id"] for result in bed_results],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
