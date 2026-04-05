from extraction_lab.assert_regression import evaluate_regression


def test_core_extraction_fails_on_entity_recall_drop_gt_10pct() -> None:
    thresholds = {
        "core_extraction": {
            "hard_fail": {
                "entity_anchor_recall_drop_pct": 10.0,
                "fact_anchor_recall_drop_pct": 12.0,
                "unresolved_core_anchors_increase": 0,
            },
            "warning": {
                "total_entity_count_drift_pct": 15.0,
                "total_fact_count_drift_pct": 20.0,
            },
        }
    }
    baseline = {
        "entity_anchor_recall": 1.0,
        "fact_anchor_recall": 1.0,
        "unresolved_core_anchors": 0,
        "total_entity_count": 100,
        "total_fact_count": 200,
    }
    current = {
        "entity_anchor_recall": 0.89,
        "fact_anchor_recall": 1.0,
        "unresolved_core_anchors": 0,
        "total_entity_count": 100,
        "total_fact_count": 200,
    }
    result = evaluate_regression(
        surface="core_extraction",
        current_metrics=current,
        baseline_metrics=baseline,
        thresholds=thresholds,
    )
    assert result["pass"] is False
    assert any(item.startswith("entity_anchor_recall_drop_pct") for item in result["failures"])
