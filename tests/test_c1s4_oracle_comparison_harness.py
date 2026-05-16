from __future__ import annotations

from copy import deepcopy

import pytest

from evals.c1s4_preplanning_vertical_slice.oracle_comparison_harness import (
    build_oracle_comparison_report,
    load_oracle_policy,
    load_oracle_text,
    validate_oracle_comparison_report,
)
from evals.c1s4_preplanning_vertical_slice.step5_build_synthetic_prep_packet import build_summary as build_step5_summary
from evals.c1s4_preplanning_vertical_slice.synthetic_prep_packet_harness import SECTION_QUESTION_MAP
import evals.c1s4_preplanning_vertical_slice.step6_compare_synthetic_prep_to_oracle as step6


def _build_report(mode: str = "prior_only"):
    step5 = build_step5_summary(mode=mode, generator="template_stub")
    prep = step5["prep_packet"]
    policy = load_oracle_policy()
    oracle = load_oracle_text(policy)
    report = build_oracle_comparison_report(prep_packet=prep, oracle_policy=policy, oracle_text_bundle=oracle)
    return prep, policy, report


def test_oracle_policy_is_step6_only():
    policy = load_oracle_policy()
    assert policy["oracle_visibility"] == "step6_only"
    assert policy["planner_forbidden"] is True
    assert policy["heldout_session"] == 4


def test_step6_loads_oracle_but_does_not_mutate_prep_packet():
    step5 = build_step5_summary(mode="prior_only", generator="template_stub")
    prep = step5["prep_packet"]
    before = deepcopy(prep)
    policy = load_oracle_policy()
    oracle = load_oracle_text(policy)
    _ = build_oracle_comparison_report(prep_packet=prep, oracle_policy=policy, oracle_text_bundle=oracle)
    assert prep == before
    assert prep["oracle_visibility"] == "forbidden"
    assert prep["does_not_claim_observed_c1s4_match"] is True


def test_comparison_report_has_no_final_score():
    _, _, report = _build_report()
    assert report["does_not_claim_final_quality_score"] is True
    assert report["summary"]["final_score"] is None
    blob = str(report).lower()
    assert "'passed'" not in blob
    assert "'failed'" not in blob
    assert "'grade'" not in blob
    assert "'quality_score':" not in blob


def test_report_is_mode_specific():
    _, _, report_a = _build_report("prior_only")
    _, _, report_b = _build_report("prior_plus_support_content_only")
    assert report_a["retrieval_mode"] == "prior_only"
    assert report_b["retrieval_mode"] == "prior_plus_support_content_only"


def test_q35_does_not_become_planner_visible():
    prep, _, report = _build_report()
    for section in prep["sections"]:
        assert 35 not in section.get("question_numbers", [])
        for entry in section.get("prep_entries", []):
            assert entry.get("question_number") != 35
    assert "q35" not in str(report).lower()


def test_oracle_sources_loaded_are_reported():
    _, _, report = _build_report()
    loaded = report["oracle_sources_loaded"]
    assert loaded
    assert all("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps" in s["path"] for s in loaded)


def test_section_comparisons_exist():
    _, _, report = _build_report()
    got = {s["section_id"] for s in report["section_comparisons"]}
    assert set(SECTION_QUESTION_MAP) <= got


def test_no_oracle_data_written_into_prep_packet():
    prep, _, _ = _build_report()
    blob = str(prep).lower()
    assert "session 4 - the grotesque tree of hempholm" not in blob


def test_validation_rejects_final_score():
    _, _, report = _build_report()
    report["summary"]["final_score"] = 0.9
    errs = validate_oracle_comparison_report(report)
    assert any("final_score" in e for e in errs)


def test_validation_rejects_planner_visible_oracle():
    _, _, report = _build_report()
    report["planner_visibility"] = "allowed"
    errs = validate_oracle_comparison_report(report)
    assert any("planner_visibility" in e for e in errs)


def test_step6_refuses_oracle_load_when_step5_invalid(monkeypatch):
    def fake_step5_summary(*, mode: str, generator: str):
        return {
            "prep_packet_built": False,
            "counts": {
                "validation_errors": 1,
                "packets_with_oracle_leakage": 0,
                "packets_with_unsupported_forbidden_terms": 0,
            },
            "oracle_leakage_check": {"forbidden_path_hits": [], "forbidden_session_hits": []},
            "prep_packet": {"campaign_id": "longmont-c1"},
        }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("oracle should not be loaded when step5 is invalid")

    monkeypatch.setattr(step6, "build_step5_summary", fake_step5_summary)
    monkeypatch.setattr(step6, "load_oracle_policy", fail_if_called)

    with pytest.raises(ValueError, match="Step 5 summary invalid"):
        step6.build_summary(mode="prior_only", generator="template_stub")
