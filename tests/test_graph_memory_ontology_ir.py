from evals.graph_memory_layer.validate_ontology_ir import main


def test_ontology_ir_validator_passes() -> None:
    assert main() == 0
