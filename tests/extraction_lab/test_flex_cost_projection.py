from extraction_lab.flex_cost_projection import project_flex_costs


def test_projects_same_observed_workload_across_flex_models() -> None:
    result = project_flex_costs(
        input_tokens=1_000_000,
        cached_tokens=100_000,
        output_tokens=100_000,
        measured_source_count=10,
        target_source_count=100,
    )
    assert result["models"]["gpt-5.6-sol"]["measured_workload_usd"] == 2.82
    assert result["models"]["gpt-5.6-sol"]["target_linear_projection_usd"] == 28.2
    assert result["models"]["gpt-5.6-luna"]["measured_workload_usd"] == 0.151
    assert "cache-write" in result["assumption"]
