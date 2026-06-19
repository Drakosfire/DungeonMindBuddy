from evals.graph_memory_layer.validate_taxonomy_registry import main


def test_taxonomy_registry_validator_passes() -> None:
    assert main() == 0
