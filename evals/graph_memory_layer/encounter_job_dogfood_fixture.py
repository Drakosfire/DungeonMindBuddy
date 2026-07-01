from __future__ import annotations

from typing import Any

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    CategoryGraphExtractionResult,
    FixtureCategoryGraphPassClient,
    run_category_pipeline,
)

SCHEMA = "dmb_encounter_job_dogfood_projection_v0"
GENERATED_BY = "evals.graph_memory_layer.encounter_job_dogfood_fixture"
FIXTURE_ID = "synthetic-glowkindle-rat-job-v0"


def glowkindle_source_span_index() -> dict[str, Any]:
    return {
        "spans": [
            {
                "kind": "paragraph",
                "span_id": "spref:glowkindle:001",
                "source_span_ref_id": "spref:glowkindle:001",
                "line_start": 1,
                "line_end": 1,
                "text": "Glowkindle asks the party to clear rats from the cellar beneath the brewery.",
            },
            {
                "kind": "paragraph",
                "span_id": "spref:glowkindle:002",
                "source_span_ref_id": "spref:glowkindle:002",
                "line_start": 3,
                "line_end": 3,
                "text": "The cellar is beneath Glowkindle's brewery and contains damaged stores.",
            },
            {
                "kind": "paragraph",
                "span_id": "spref:glowkindle:003",
                "source_span_ref_id": "spref:glowkindle:003",
                "line_start": 5,
                "line_end": 5,
                "text": "In the cellar, the party fights a swarm of rats and drives them back.",
            },
            {
                "kind": "paragraph",
                "span_id": "spref:glowkindle:004",
                "source_span_ref_id": "spref:glowkindle:004",
                "line_start": 7,
                "line_end": 7,
                "text": "After the fight, the stores are safe enough for Glowkindle to reopen the cellar.",
            },
        ]
    }


def glowkindle_dynamic_vocabulary_nodes() -> tuple[dict[str, Any], ...]:
    return (
        {"node_id": "npc_glowkindle_vocab", "label": "Glowkindle", "node_type": "character"},
        {"node_id": "loc_glowkindle_brewery_vocab", "label": "Glowkindle brewery", "node_type": "location"},
        {"node_id": "loc_glowkindle_cellar_vocab", "label": "Glowkindle cellar", "node_type": "location"},
        {
            "node_id": "quest_clear_glowkindle_rats_vocab",
            "label": "Clear rats from Glowkindle's cellar",
            "node_type": "quest",
        },
        {
            "node_id": "enc_glowkindle_cellar_rats_vocab",
            "label": "Glowkindle cellar rat fight",
            "node_type": "combat_encounter",
        },
        {"node_id": "creature_rat_swarm_vocab", "label": "Rat swarm", "node_type": "character"},
    )


def _evidence(spref: str, quote: str) -> list[dict[str, Any]]:
    return [{"source_span_ref_id": spref, "anchor_quotes": [quote]}]


def _node(node_id: str, label: str, node_type: str, description: str, spref: str, quote: str) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": description,
        "importance": "medium",
        "evidence_refs": _evidence(spref, quote),
    }


def _edge(edge_id: str, from_node_id: str, to_node_id: str, relationship_type: str, predicate_family: str, label: str, spref: str, quote: str) -> dict[str, Any]:
    return {
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "label": label,
        "relationship_type": relationship_type,
        "predicate_family": predicate_family,
        "evidence_refs": _evidence(spref, quote),
        "confidence": "high",
    }


def glowkindle_fixture_pass_outputs() -> dict[str, dict[str, Any]]:
    return {
        "actor_pass": {
            "observation_nodes": [
                _node("npc_glowkindle", "Glowkindle", "character", "Glowkindle asks the party to clear rats from the cellar.", "spref:glowkindle:001", "Glowkindle asks the party"),
                _node("creature_rat_swarm", "Rat swarm", "character", "A swarm of rats fights the party in the cellar.", "spref:glowkindle:003", "a swarm of rats"),
            ]
        },
        "location_pass": {
            "observation_nodes": [
                _node("loc_glowkindle_brewery", "Glowkindle's brewery", "location", "Glowkindle's brewery stands above the cellar.", "spref:glowkindle:002", "Glowkindle's brewery"),
                _node("loc_glowkindle_cellar", "Glowkindle's cellar", "location", "The cellar beneath the brewery contains damaged stores.", "spref:glowkindle:002", "The cellar is beneath"),
            ]
        },
        "collective_pass": {"observation_nodes": [{"node_id": "node:heroes-party", "label": "Heroes / party", "node_type": "character", "description": "Deterministic party-collective anchor for the synthetic fixture.", "importance": "high", "evidence_refs": _evidence("spref:glowkindle:001", "the party"), "warnings": ["context_anchor_no_session_evidence", "party_name_binding_deferred"], "context_anchor": True}]},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {
            "observation_beats": [
                {"beat_id": "beat_001_job_offered", "order": 1, "title": "Job offered", "summary": "Glowkindle asks the party to clear rats from the cellar.", "involved_node_ids": ["npc_glowkindle", "loc_glowkindle_cellar"], "evidence_refs": _evidence("spref:glowkindle:001", "clear rats from the cellar")},
                {"beat_id": "beat_002_cellar_context", "order": 2, "title": "Cellar context", "summary": "The cellar is beneath Glowkindle's brewery and contains damaged stores.", "involved_node_ids": ["loc_glowkindle_cellar", "loc_glowkindle_brewery"], "evidence_refs": _evidence("spref:glowkindle:002", "beneath Glowkindle's brewery")},
                {"beat_id": "beat_003_rat_fight", "order": 3, "title": "Rat fight", "summary": "The party fights a swarm of rats in the cellar.", "involved_node_ids": ["creature_rat_swarm", "loc_glowkindle_cellar"], "evidence_refs": _evidence("spref:glowkindle:003", "fights a swarm of rats")},
                {"beat_id": "beat_004_cellar_safe", "order": 4, "title": "Cellar safe", "summary": "The stores are safe enough for Glowkindle to reopen the cellar.", "involved_node_ids": ["npc_glowkindle", "loc_glowkindle_cellar"], "evidence_refs": _evidence("spref:glowkindle:004", "safe enough for Glowkindle")},
            ]
        },
        "encounter_job_pass": {
            "observation_nodes": [
                _node("quest_clear_glowkindle_rats", "Clear rats from Glowkindle's cellar", "quest", "Glowkindle asks the party to clear rats from the cellar beneath the brewery.", "spref:glowkindle:001", "clear rats from the cellar"),
                _node("enc_glowkindle_cellar_rats", "Glowkindle cellar rat fight", "combat_encounter", "The party fights and drives back a swarm of rats in the cellar.", "spref:glowkindle:003", "fights a swarm of rats"),
            ]
        },
        "edge_pass": {
            "observation_edges": [
                _edge("edge:cellar-located-in-brewery", "loc_glowkindle_cellar", "loc_glowkindle_brewery", "located_in", "location_hierarchy", "Cellar located in brewery", "spref:glowkindle:002", "beneath Glowkindle's brewery"),
                _edge("edge:encounter-located-in-cellar", "enc_glowkindle_cellar_rats", "loc_glowkindle_cellar", "located_in", "location_hierarchy", "Encounter located in cellar", "spref:glowkindle:003", "In the cellar"),
                _edge("edge:rat-swarm-participates-in-encounter", "creature_rat_swarm", "enc_glowkindle_cellar_rats", "participates_in", "participation", "Rat swarm participates in encounter", "spref:glowkindle:003", "swarm of rats"),
                _edge("edge:quest-targets-rat-swarm", "quest_clear_glowkindle_rats", "creature_rat_swarm", "mission_targets", "hook_relation", "Quest targets rat swarm", "spref:glowkindle:001", "clear rats"),
                _edge("edge:quest-focuses-cellar", "quest_clear_glowkindle_rats", "loc_glowkindle_cellar", "mission_focus", "hook_relation", "Quest focuses on cellar", "spref:glowkindle:001", "from the cellar"),
            ]
        },
    }


def run_glowkindle_encounter_job_dogfood() -> CategoryGraphExtractionResult:
    return run_category_pipeline(
        FixtureCategoryGraphPassClient(glowkindle_fixture_pass_outputs()),
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="synthetic-glowkindle-c1s1",
            session_number=1,
            source_span_index=glowkindle_source_span_index(),
            model_id="fixture-no-llm",
            enable_encounter_job_pass=True,
            enable_party_participation_attachment=True,
            enable_encounter_job_edge_guidance=True,
            enable_dynamic_node_vocabulary_packet=True,
            dynamic_node_vocabulary_nodes=glowkindle_dynamic_vocabulary_nodes(),
        ),
    )


def _has_edge(edges: list[dict[str, Any]], source: str, target: str, rel: str) -> bool:
    return any(e.get("from_node_id") == source and e.get("to_node_id") == target and e.get("relationship_type") == rel for e in edges)


def dogfood_checks(candidate_graph: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, bool]:
    nodes = candidate_graph.get("nodes", [])
    edges = candidate_graph.get("edges", [])
    node_ids = {n.get("node_id") for n in nodes}
    pc_nodes = [n for n in nodes if str(n.get("node_id", "")).startswith("node:pc-")]
    return {
        "has_quest": "quest_clear_glowkindle_rats" in node_ids,
        "has_combat_encounter": "enc_glowkindle_cellar_rats" in node_ids,
        "has_party_pursues_quest": _has_edge(edges, "node:heroes-party", "quest_clear_glowkindle_rats", "pursues"),
        "has_party_participates_in_encounter": _has_edge(edges, "node:heroes-party", "enc_glowkindle_cellar_rats", "participates_in"),
        "has_encounter_location_edge": _has_edge(edges, "enc_glowkindle_cellar_rats", "loc_glowkindle_cellar", "located_in"),
        "has_rat_participation_edge": _has_edge(edges, "creature_rat_swarm", "enc_glowkindle_cellar_rats", "participates_in"),
        "has_quest_target_edge": _has_edge(edges, "quest_clear_glowkindle_rats", "creature_rat_swarm", "mission_targets"),
        "has_quest_focus_edge": _has_edge(edges, "quest_clear_glowkindle_rats", "loc_glowkindle_cellar", "mission_focus"),
        "has_duplicate_pc_nodes": len(pc_nodes) != len({n.get("node_id") for n in pc_nodes}),
        "has_invalid_predicate_issues": bool(diagnostics.get("consolidation_diagnostics", {}).get("edge_predicate_issues")),
        "has_dropped_edges": bool(diagnostics.get("consolidation_diagnostics", {}).get("dropped_edges_missing_endpoints")),
    }


def dogfood_result_to_payload(result: CategoryGraphExtractionResult) -> dict[str, Any]:
    diagnostics = {"result_diagnostics": result.diagnostics, "consolidation_diagnostics": result.consolidation_diagnostics}
    return {
        "schema": SCHEMA,
        "generated_by": GENERATED_BY,
        "llm_used": False,
        "fixture_only": True,
        "runtime_connected": False,
        "corpus_scanned": False,
        "corpus_mutated": False,
        "canon_promoted": False,
        "source_fixture": {"fixture_id": FIXTURE_ID, "description": "Synthetic fixture for encounter/job extraction dogfood; not campaign canon."},
        "extraction_options": {
            "enable_encounter_job_pass": True,
            "enable_party_participation_attachment": True,
            "enable_encounter_job_edge_guidance": True,
            "enable_dynamic_node_vocabulary_packet": True,
        },
        "candidate_graph": result.candidate_graph,
        "diagnostics": diagnostics,
        "checks": dogfood_checks(result.candidate_graph, diagnostics),
    }
