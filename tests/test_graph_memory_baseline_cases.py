from evals.graph_memory_layer.validate_baseline_cases import main


def test_baseline_cases_validator_passes() -> None:
    assert main() == 0
