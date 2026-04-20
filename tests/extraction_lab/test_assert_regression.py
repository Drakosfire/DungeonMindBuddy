from extraction_lab.assert_regression import evaluate_regression


_CORE_THRESHOLDS_WITH_FLOOR = {
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
        "absolute_floor": {
            "entity_anchor_recall_min": 0.5,
            "fact_anchor_recall_min": 0.5,
        },
    }
}

_CORE_THRESHOLDS_NO_FLOOR = {
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


def test_vertical_slice_warns_on_question_pass_rate_drop() -> None:
    thresholds = {
        "vertical_slice": {
            "warning": {"question_pass_rate_drop_pct": 10.0},
        }
    }
    baseline = {"question_pass_rate": 0.9}
    current = {"question_pass_rate": 0.7}  # ~22% drop, exceeds 10% threshold
    result = evaluate_regression(
        surface="vertical_slice",
        current_metrics=current,
        baseline_metrics=baseline,
        thresholds=thresholds,
    )
    assert result["pass"] is True
    assert any(item.startswith("question_pass_rate_drop_pct") for item in result["warnings"])


def test_recap_lane_warns_on_event_record_recall_drop() -> None:
    thresholds = {
        "recap_lane": {
            "warning": {"event_record_recall_drop_pct": 15.0},
        }
    }
    baseline = {"event_record_recall": 0.9}
    current = {"event_record_recall": 0.7}  # ~22% drop, exceeds 15% threshold
    result = evaluate_regression(
        surface="recap_lane",
        current_metrics=current,
        baseline_metrics=baseline,
        thresholds=thresholds,
    )
    assert result["pass"] is True
    assert any(item.startswith("event_record_recall_drop_pct") for item in result["warnings"])


def test_working_set_passes_with_no_thresholds_defined() -> None:
    thresholds = {"working_set": {}}
    result = evaluate_regression(
        surface="working_set",
        current_metrics={"some_metric": 1.0},
        baseline_metrics=None,
        thresholds=thresholds,
    )
    assert result["pass"] is True
    assert result["failures"] == []


def test_core_extraction_fails_when_recall_below_absolute_floor_with_no_baseline() -> None:
    current = {
        "entity_anchor_recall": 0.0,
        "fact_anchor_recall": 0.0,
        "unresolved_core_anchors": 23,
        "total_entity_count": 50,
        "total_fact_count": 100,
    }
    result = evaluate_regression(
        surface="core_extraction",
        current_metrics=current,
        baseline_metrics=None,
        thresholds=_CORE_THRESHOLDS_WITH_FLOOR,
    )
    assert result["pass"] is False
    assert any(item.startswith("entity_anchor_recall_below_floor") for item in result["failures"])


def test_core_extraction_fails_when_recall_below_absolute_floor_with_baseline() -> None:
    baseline = {
        "entity_anchor_recall": 0.0,
        "fact_anchor_recall": 0.0,
        "unresolved_core_anchors": 0,
        "total_entity_count": 50,
        "total_fact_count": 100,
    }
    current = {
        "entity_anchor_recall": 0.0,
        "fact_anchor_recall": 0.0,
        "unresolved_core_anchors": 23,
        "total_entity_count": 50,
        "total_fact_count": 100,
    }
    result = evaluate_regression(
        surface="core_extraction",
        current_metrics=current,
        baseline_metrics=baseline,
        thresholds=_CORE_THRESHOLDS_WITH_FLOOR,
    )
    assert result["pass"] is False
    assert any(item.startswith("entity_anchor_recall_below_floor") for item in result["failures"])


def test_core_extraction_passes_when_recall_above_floor_with_no_baseline() -> None:
    current = {
        "entity_anchor_recall": 1.0,
        "fact_anchor_recall": 1.0,
        "unresolved_core_anchors": 0,
        "total_entity_count": 100,
        "total_fact_count": 200,
    }
    result = evaluate_regression(
        surface="core_extraction",
        current_metrics=current,
        baseline_metrics=None,
        thresholds=_CORE_THRESHOLDS_WITH_FLOOR,
    )
    assert result["pass"] is True
    assert result["failures"] == []


def test_unknown_surface_passes_with_warning() -> None:
    result = evaluate_regression(
        surface="not_real",
        current_metrics={"some_metric": 1.0},
        baseline_metrics=None,
        thresholds={},
    )
    assert result["pass"] is True
    assert "unknown_surface" in result["warnings"]


def test_core_extraction_floor_check_skipped_when_threshold_absent() -> None:
    # Old threshold dict without absolute_floor key — floor check must be skipped silently.
    current = {
        "entity_anchor_recall": 0.0,
        "fact_anchor_recall": 0.0,
        "unresolved_core_anchors": 0,
        "total_entity_count": 100,
        "total_fact_count": 200,
    }
    result = evaluate_regression(
        surface="core_extraction",
        current_metrics=current,
        baseline_metrics=None,
        thresholds=_CORE_THRESHOLDS_NO_FLOOR,
    )
    assert result["pass"] is True
    assert not any("below_floor" in item for item in result["failures"])
