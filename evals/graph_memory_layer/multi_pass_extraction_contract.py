"""Multi-pass extraction contract helpers (contract-only; no extraction)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID,
    GOLD_GRAPH_PATH,
    HIGH_RISK_EVIDENCE_AUDIT,
    load_gold_manifest,
    valid_source_anchor_ids,
    validate_gold_manifest,
)
from evals.graph_memory_layer.session_23_recap_ingest_fixture import (
    FIXTURE_ID as SOURCE_FIXTURE_ID,
    load_expected_normalized_recap,
    load_manifest,
    load_raw_recap,
    validate_manifest,
)

CONTRACT_SCHEMA = "dmb_graph_memory_multi_pass_extraction_contract_v0"
CONTRACT_VERSION = "0.1"
CONTRACT_ID = "graph-memory:multi-pass-extraction-contract:v0"
CONTRACT_DIR = "evals/graph_memory_layer/examples/multi_pass_extraction_contract"
CONTRACT_PATH = f"{CONTRACT_DIR}/multi_pass_extraction_contract.json"
SESSION_23_FIXTURE_PATH = f"{CONTRACT_DIR}/session_23_contract_fixture.json"
SESSION_23_OUTLINE_PATH = f"{CONTRACT_DIR}/session_23_expected_pass_outline.json"
SESSION_23_COMPARISON_PATH = f"{CONTRACT_DIR}/session_23_gold_comparison_contract.json"
PASS_ORDER = ["source_span_selection","session_beat_extraction","named_entity_candidate_extraction","unnamed_important_concept_extraction","relationship_edge_proposal","ignored_deferred_detection","evidence_alignment","candidate_graph_assembly","gold_comparison_report"]
ALLOWED_OUTPUT_SCHEMAS = ["dmb_extraction_source_span_selection_v0","dmb_extraction_session_beats_v0","dmb_extraction_named_entity_candidates_v0","dmb_extraction_unnamed_important_candidates_v0","dmb_extraction_relationship_edge_candidates_v0","dmb_extraction_ignored_deferred_candidates_v0","dmb_extraction_evidence_alignment_v0","dmb_candidate_graph_preview_v0","dmb_candidate_graph_gold_comparison_report_v0"]
ISSUE_CATEGORIES = "missing_required_node extra_unsupported_node missing_required_edge extra_unsupported_edge missing_required_beat beat_order_mismatch missing_evidence_ref unknown_evidence_anchor unresolved_evidence_ref unhighlightable_source_evidence unsupported_identity_binding unsupported_alias_binding unsupported_second_wave_claim unsupported_outcome_resolution promoted_lifecycle_forbidden approved_write_forbidden dangerous_diagnostic_flag source_leakage runtime_leakage".split()
HARD_FAILURE_CATEGORIES = "dangerous_diagnostic_flag promoted_lifecycle_forbidden approved_write_forbidden unknown_evidence_anchor unresolved_evidence_ref source_leakage runtime_leakage corpus_mutation llm_execution_required".split()
SOFT_MISS_CATEGORIES = "missing_optional_node missing_optional_edge low_importance_label_mismatch summary_wording_difference".split()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _load(rel: str) -> dict[str, Any]:
    return json.loads((repo_root() / rel).read_text(encoding="utf-8"))

def load_contract() -> dict[str, Any]: return _load(CONTRACT_PATH)
def load_session_23_contract_fixture() -> dict[str, Any]: return _load(SESSION_23_FIXTURE_PATH)
def load_session_23_expected_pass_outline() -> dict[str, Any]: return _load(SESSION_23_OUTLINE_PATH)
def load_session_23_gold_comparison_contract() -> dict[str, Any]: return _load(SESSION_23_COMPARISON_PATH)

def _assert(cond: bool, msg: str) -> None:
    if not cond: raise ValueError(msg)

def _check_rel(value: str) -> None:
    p = Path(value); _assert(not p.is_absolute() and ".." not in p.parts, f"unsafe path: {value}")

def _walk(obj: Any):
    if isinstance(obj, dict):
        for k,v in obj.items():
            yield str(k), v; yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj: yield from _walk(v)
    else:
        yield "", obj

def validate_contract_manifest(contract: Mapping[str, Any]) -> None:
    _assert(contract.get("schema") == CONTRACT_SCHEMA, "wrong schema")
    _assert(contract.get("version") == CONTRACT_VERSION, "wrong version")
    _assert(contract.get("contract_id") == CONTRACT_ID, "wrong contract id")
    _assert(contract.get("campaign_id") == "longmont-c2" and contract.get("target_session") == 23, "wrong target")
    _assert(contract.get("target_gold_fixture_id") == GOLD_FIXTURE_ID, "missing Session 23 gold fixture dependency")
    _assert(contract.get("source_fixture_id") == SOURCE_FIXTURE_ID, "missing Session 23 source fixture dependency")
    _assert(contract.get("execution_mode") == "contract_only", "execution mode must be contract_only")
    _assert(contract.get("pass_order") == PASS_ORDER, "pass order changed")
    _assert(len(set(contract["pass_order"])) == len(PASS_ORDER), "duplicate pass ids")
    _assert(contract.get("allowed_output_schemas") == ALLOWED_OUTPUT_SCHEMAS, "unknown output schemas")
    for k,v in contract.get("diagnostics", {}).items():
        if k == "contract_only": _assert(v is True, "contract_only diagnostic must be true")
        else: _assert(v is False, f"dangerous diagnostic flag: {k}")

def validate_pass_contracts(fixture: Mapping[str, Any]) -> None:
    _assert(fixture.get("schema") == "dmb_session_23_multi_pass_extraction_contract_fixture_v0", "wrong fixture schema")
    _assert(fixture.get("version") == CONTRACT_VERSION and fixture.get("contract_id") == CONTRACT_ID, "wrong fixture metadata")
    _assert(fixture.get("source_fixture", {}).get("fixture_id") == SOURCE_FIXTURE_ID, "wrong source fixture")
    _assert(fixture.get("gold_fixture", {}).get("fixture_id") == GOLD_FIXTURE_ID, "wrong gold fixture")
    passes = fixture.get("passes", [])
    _assert([p.get("pass_id") for p in passes] == PASS_ORDER, "wrong pass order")
    _assert(len(passes) == 9 and len({p.get("pass_id") for p in passes}) == 9, "pass count/duplicate")
    for i,p in enumerate(passes):
        _assert(p.get("schema") == ALLOWED_OUTPUT_SCHEMAS[i], f"wrong schema for {p.get('pass_id')}")
        for key in ("purpose","input_contract","output_contract","hard_gates","soft_quality_signals","forbidden_outputs","allowed_dependencies"):
            _assert(key in p and p[key] not in (None, ""), f"{p.get('pass_id')} missing {key}")

def validate_session_23_outline(outline: Mapping[str, Any]) -> None:
    _assert(outline.get("schema") == "dmb_session_23_expected_pass_outline_v0", "wrong outline schema")
    anchors = set(outline.get("required_source_anchors", []))
    _assert(anchors and anchors <= valid_source_anchor_ids(), "unknown outline source anchor")
    concepts = outline.get("required_concepts", {})
    for key in ("named_characters","groups","locations","unnamed_important","ignored","deferred"):
        _assert(concepts.get(key), f"missing concepts {key}")
    text = "\n".join(outline.get("forbidden_claims", [])).lower()
    for needle in ("questionable company", "second wave", "resolved battle outcome", "exact shadow count"):
        _assert(needle in text, f"missing forbidden claim {needle}")

def validate_gold_comparison_contract(comparison: Mapping[str, Any]) -> None:
    _assert(comparison.get("schema") == "dmb_session_23_gold_comparison_contract_v0", "wrong comparison schema")
    _assert(comparison.get("contract_id") == CONTRACT_ID and comparison.get("gold_fixture_id") == GOLD_FIXTURE_ID, "wrong comparison fixture")
    _assert(comparison.get("comparison_mode") == "contract_defined_no_execution", "comparison must be no-execution")
    _assert(set(ISSUE_CATEGORIES) <= set(comparison.get("issue_categories", [])), "missing issue category")
    _assert(set(HARD_FAILURE_CATEGORIES) <= set(comparison.get("hard_failure_categories", [])), "missing hard failure")
    _assert(set(SOFT_MISS_CATEGORIES) <= set(comparison.get("soft_miss_categories", [])), "missing soft miss")

def validate_dependencies() -> None:
    validate_manifest(load_manifest()); validate_gold_manifest(load_gold_manifest())
    for rel in (GOLD_GRAPH_PATH, "evals/graph_memory_layer/examples/session_23_recap_ingest/source_span_seed_refs.json"):
        _assert((repo_root()/rel).exists(), f"missing dependency {rel}")

def validate_safety_boundaries(*fixtures: Mapping[str, Any]) -> None:
    forbidden_keys = {"llm_response","model_response","extraction_output","extractor_output","graph_write_result","approved_write","promoted_write","runtime_payload","plan_payload","agent_interaction_payload","corpus_mutation"}
    joined = json.dumps(fixtures, sort_keys=True)
    _assert(load_expected_normalized_recap() not in joined and load_raw_recap() not in joined, "full source text leakage")
    for key,value in _walk(list(fixtures)):
        if key in forbidden_keys: raise ValueError(f"forbidden key {key}")
        if isinstance(value, str):
            _check_rel(value) if value.startswith("/") or value.startswith("evals/") or value.startswith("Docs/") else None
            low = value.lower()
            _assert(low not in {"approved", "promoted"}, "approved/promoted state leakage")


def validate_all() -> None:
    validate_dependencies()
    c=load_contract(); f=load_session_23_contract_fixture(); o=load_session_23_expected_pass_outline(); g=load_session_23_gold_comparison_contract()
    validate_contract_manifest(c); validate_pass_contracts(f); validate_session_23_outline(o); validate_gold_comparison_contract(g); validate_safety_boundaries(c,f,o,g)
