import json
import subprocess
from dataclasses import replace
from pathlib import Path

from src.graph_memory.ontology_ir import GraphBundle, TaxonomyRef
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
VALID = ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"
INVALID = ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_invalid_bundle.json"


def load_bundle(path: Path) -> GraphBundle:
    return GraphBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))


def codes(bundle: GraphBundle) -> set[str]:
    result = validate_bundle_against_taxonomy(bundle, load_taxonomy_registry(REGISTRY))
    return {issue.code for issue in result.issues}


def test_valid_synthetic_bundle_passes_with_no_error_or_fatal_issues() -> None:
    result = validate_bundle_against_taxonomy(load_bundle(VALID), load_taxonomy_registry(REGISTRY))
    assert result.ok
    assert not [issue for issue in result.issues if issue.severity in {"error", "fatal"}]


def test_invalid_synthetic_bundle_fails() -> None:
    assert not validate_bundle_against_taxonomy(load_bundle(INVALID), load_taxonomy_registry(REGISTRY)).ok


def test_unknown_taxonomy_vocabulary_is_detected() -> None:
    bundle = load_bundle(VALID)
    node = replace(bundle.nodes[0], kind=TaxonomyRef("missing_vocab", "person"))
    assert "unknown_taxonomy_vocabulary" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_unknown_taxonomy_term_is_detected() -> None:
    bundle = load_bundle(VALID)
    node = replace(bundle.nodes[0], kind=TaxonomyRef("entity_kind", "unknown_kind"))
    assert "unknown_taxonomy_term" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_source_evidence_without_source_refs_is_detected() -> None:
    bundle = load_bundle(VALID)
    provenance = replace(bundle.nodes[0].provenance[0], source_refs=[])
    node = replace(bundle.nodes[0], provenance=[provenance])
    assert "source_evidence_without_source_ref" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_promoted_record_without_provenance_is_detected() -> None:
    bundle = load_bundle(VALID)
    node = replace(bundle.nodes[0], provenance=[])
    assert "promoted_record_without_provenance" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_promoted_record_without_source_grounding_is_detected() -> None:
    bundle = load_bundle(VALID)
    provenance = replace(bundle.nodes[0].provenance[0], evidence_role=TaxonomyRef("evidence_role", "diagnostic_only"), source_refs=[])
    node = replace(bundle.nodes[0], provenance=[provenance])
    assert "promoted_record_without_source_grounding" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_unsafe_authority_promoted_is_detected() -> None:
    bundle = load_bundle(VALID)
    provenance = replace(bundle.nodes[0].provenance[0], authority_state=TaxonomyRef("authority_state", "rumor"))
    node = replace(bundle.nodes[0], provenance=[provenance])
    assert "unsafe_authority_promoted" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_visibility_boundary_conflict_is_detected() -> None:
    bundle = load_bundle(VALID)
    provenance = replace(bundle.nodes[0].provenance[0], visibility_state=TaxonomyRef("visibility_state", "private_gm"))
    node = replace(bundle.nodes[0], provenance=[provenance])
    assert "visibility_boundary_conflict" in codes(replace(bundle, nodes=[node, *bundle.nodes[1:]]))


def test_edge_endpoint_missing_is_detected() -> None:
    bundle = load_bundle(VALID)
    edge = replace(bundle.edges[0], object_node_id="node.synthetic.absent")
    assert "edge_endpoint_missing" in codes(replace(bundle, edges=[edge]))


def test_validator_cli_exits_zero_when_expectations_hold() -> None:
    result = subprocess.run(
        ["uv", "run", "python", "-m", "evals.graph_memory_layer.validate_ontology_ir_rules"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
