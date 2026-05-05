"""Unit tests for the planner discovery / router canvas payload renderer."""

from __future__ import annotations

import json
from typing import Any

from evals.sentence_routing_retrieval_falsification.planner_discovery_canvas_payload import (
    build_payload,
    render_canvas_tsx,
)


def _gold() -> dict[str, Any]:
    return {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c2",
        "scenarios": [
            {
                "id": "nat_captain_after_forest",
                "question": "What happened to the captain?",
                "expected_answer": "The captain was found.",
                "must_hit_tokens": ["captain"],
                "expect_route_substrings": ["NPCs/captain_lysandra_ironveil"],
                "min_context_support_ratio": 0.75,
            },
        ],
    }


def _discovery_report() -> dict[str, Any]:
    return {
        "harness": "breadcrumb_query_planner_discovery_v1",
        "results": [
            {
                "scenario_id": "nat_captain_after_forest",
                "question": "What happened to the captain?",
                "benchmark_retrieval_ok": True,
                "benchmark_violations": [],
                "benchmark_grade": {"llm_semantic_verdict": "pass_updated"},
                "planner_grade_vs_benchmark_retrieval": {
                    "ok": False,
                    "violations": ["llm_context_support_below_threshold"],
                    "llm_semantic_verdict": "pass_updated",
                },
                "planner_message_preview": "The captain ...",
                "benchmark_llm_answer_preview": "The captain ...",
                "planner_scenario_estimated_cost_usd": 0.04,
                "benchmark_llm_cost_usd": 0.001,
                "planner_discovery": {
                    "planner_read_paths": ["Longmont Campaign/.../README.md"],
                    "query_session_memory_call_count": 0,
                    "expected_open_paths": ["NPCs/captain_lysandra_ironveil"],
                    "expected_open_paths_coverage": {
                        "recall": 1.0,
                        "covered_count": 1,
                        "needle_count": 1,
                        "details": [],
                    },
                    "expected_open_paths_full_coverage": True,
                    "expect_route_substrings_coverage_on_reads": {
                        "recall": 1.0,
                        "covered_count": 1,
                        "needle_count": 1,
                        "details": [],
                    },
                    "benchmark_hit_route_coverage_on_reads": {
                        "recall": 0.5,
                        "covered_count": 1,
                        "needle_count": 2,
                        "details": [],
                    },
                },
            }
        ],
        "planner_discovery_aggregate": {
            "expected_open_paths_recall_mean": 1.0,
            "expected_open_paths_full_coverage_scenarios": 1,
            "query_session_memory_total_calls": 0,
            "query_session_memory_scenarios_with_calls": 0,
        },
        "planner_model": "stub-planner",
        "benchmark_llm_model": "stub-benchmark",
        "aggregate_scenario_planner_cost_usd": 0.04,
        "aggregate_benchmark_llm_cost_usd": 0.001,
    }


def _router_report() -> dict[str, Any]:
    return {
        "harness": "breadcrumb_query_planner_router_v1",
        "planner_model": "stub-planner",
        "router_synth_model": "stub-synth",
        "no_escalation": False,
        "decision_counts": {"answer_now": 1, "need_more_context": 1},
        "failure_reason_counts": {"low_top_hit_strength": 1},
        "cohort_pass_count": 1,
        "cohort_pass_count_answer_now": 1,
        "cohort_pass_count_escalated": 0,
        "cohort_total": 2,
        "aggregate_router_synth_cost_usd": 0.002,
        "aggregate_planner_cost_usd": 0.05,
        "aggregate_scenario_cost_usd": 0.052,
        "router_config": {
            "min_matched_records": 2,
            "min_hits": 3,
            "min_top_hit_score": 3,
            "min_route_anchor_recall": 1.0,
            "min_context_density": 0.5,
            "max_expansion_fill_ratio": 1.0,
        },
        "results": [
            {
                "scenario_id": "nat_captain_after_forest",
                "question": "What happened to the captain?",
                "router_decision": "answer_now",
                "router_failure_reasons": [],
                "router_confidence_features": {"top_hit_score": 9},
                "scenario_telemetry_cost": {
                    "router_decision": "answer_now",
                    "router_synth_cost_usd": 0.002,
                    "planner_estimated_cost_usd": 0.0,
                    "scenario_estimated_cost_usd": 0.002,
                    "escalated": False,
                },
                "router_evidence_summary": {
                    "matched_records": 5,
                    "returned_hits": 6,
                    "top_hit_score": 9,
                    "route_anchor_recall": 1.0,
                    "context_density": 0.9,
                    "expansion_fill_ratio": 0.0,
                    "why_matched_tokens": ["captain"],
                },
                "router_required_route_anchors": [],
                "router_synth_model": "stub-synth",
                "router_synth_cost_usd": 0.002,
                "router_synth_usage": {"input_tokens": 100, "output_tokens": 30},
                "router_synth_answer_preview": "The captain was found.",
                "router_grade": {
                    "ok": True,
                    "violations": [],
                    "llm_semantic_verdict": "pass_updated",
                    "llm_context_support_ratio": 1.0,
                },
                "escalation_run": None,
                "escalation_skipped": False,
                "scenario_estimated_cost_usd": 0.002,
            },
            {
                "scenario_id": "scenario_b",
                "question": "Where is the antenna?",
                "router_decision": "need_more_context",
                "router_failure_reasons": ["low_top_hit_strength"],
                "router_confidence_features": {"top_hit_score": 1},
                "scenario_telemetry_cost": {
                    "router_decision": "need_more_context",
                    "router_synth_cost_usd": 0.0,
                    "planner_estimated_cost_usd": 0.05,
                    "scenario_estimated_cost_usd": 0.05,
                    "escalated": True,
                },
                "router_evidence_summary": {
                    "matched_records": 1,
                    "returned_hits": 1,
                    "top_hit_score": 1,
                    "route_anchor_recall": None,
                    "context_density": 0.2,
                    "expansion_fill_ratio": 0.0,
                    "why_matched_tokens": [],
                },
                "router_required_route_anchors": [],
                "router_synth_model": None,
                "router_synth_cost_usd": None,
                "router_synth_usage": {},
                "router_synth_answer_preview": None,
                "router_grade": None,
                "router_decision_payload": {
                    "schema": "dmb_planner_retrieval_router_v1",
                    "decision": "need_more_context",
                    "escalation": {
                        "failure_reasons": ["low_top_hit_strength"],
                        "missing_signals": {},
                        "suggested_read_paths": [
                            "Longmont Campaign/Campaign 2/README.md",
                            "Longmont Campaign/Campaign 2/NPCs/example/README.md",
                        ],
                    },
                    "failure_reasons": ["low_top_hit_strength"],
                },
                "escalation_run": {
                    "planner_message_preview": "I could not find the antenna.",
                    "planner_final_text_parse_error": None,
                    "planner_read_paths": ["Longmont Campaign/.../README.md"],
                    "planner_tool_trace": [
                        {
                            "tool": "read_corpus_file",
                            "path": "Longmont Campaign/.../README.md",
                            "output_preview": "# Session prep\\nAntenna clues...",
                        },
                    ],
                    "planner_query_session_memory_unit_ids": [],
                    "query_session_memory_call_count": 0,
                    "planner_telemetry_cost": {
                        "planner_estimated_cost_usd": 0.05,
                        "statblock_tool_estimated_cost_usd": 0.0,
                        "scenario_estimated_cost_usd": 0.05,
                    },
                    "planner_grade": {
                        "ok": False,
                        "violations": ["llm_semantic_verdict:fail_no_signal"],
                        "llm_semantic_verdict": "fail_no_signal",
                    },
                    "planner_hit_tool_round_limit": False,
                },
                "escalation_skipped": False,
                "scenario_estimated_cost_usd": 0.05,
            },
        ],
    }


def test_build_payload_discovery_shape():
    gold = _gold()
    report = _discovery_report()
    report["source_report_path"] = "/tmp/discovery_report.json"
    report["source_gold_path"] = "/tmp/gold.json"
    payload = build_payload(report, gold)
    assert payload["harnessKind"] == "discovery"
    assert payload["title"] == "Planner Query Discovery Review"
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row["id"] == "nat_captain_after_forest"
    actual = row["actual"]
    assert actual["benchmarkRetrievalOk"] is True
    assert actual["plannerGrade"]["ok"] is False
    assert actual["expectedOpenPathsCoverage"]["recall"] == 1.0
    summary = payload["summary"]
    assert summary["plannerGradePassCount"] == 0
    assert summary["benchmarkRetrievalPassCount"] == 1


def test_build_payload_router_shape():
    gold = _gold()
    gold["scenarios"].append(
        {
            "id": "scenario_b",
            "question": "Where is the antenna?",
            "expected_answer": "Unknown",
            "must_hit_tokens": ["antenna"],
            "expect_route_substrings": [],
            "min_context_support_ratio": 0.75,
        }
    )
    report = _router_report()
    report["source_report_path"] = "/tmp/router_report.json"
    report["source_gold_path"] = "/tmp/gold.json"
    payload = build_payload(report, gold)
    assert payload["harnessKind"] == "router"
    assert payload["title"] == "Planner Retrieval Router Review"
    rows = payload["rows"]
    assert len(rows) == 2
    answer_now_row = next(r for r in rows if r["id"] == "nat_captain_after_forest")
    assert answer_now_row["actual"]["routerDecision"] == "answer_now"
    assert answer_now_row["actual"]["answeredNow"] is True
    assert answer_now_row["actual"]["escalated"] is False
    assert answer_now_row["actual"]["routerGrade"]["ok"] is True
    escalated_row = next(r for r in rows if r["id"] == "scenario_b")
    assert escalated_row["actual"]["routerDecision"] == "need_more_context"
    assert escalated_row["actual"]["escalated"] is True
    assert "low_top_hit_strength" in escalated_row["actual"]["routerFailureReasons"]
    summary = payload["summary"]
    assert summary["answerNowCount"] == 1
    assert summary["escalatedCount"] == 1
    assert summary["cohortPassCount"] == 1


def _discovery_report_two_rows() -> dict[str, Any]:
    base = _discovery_report()
    base["results"] = list(base["results"])
    base["results"].append(
        {
            "scenario_id": "scenario_b",
            "question": "Where is the antenna?",
            "benchmark_retrieval_ok": False,
            "benchmark_violations": ["x"],
            "benchmark_grade": {"ok": False},
            "planner_grade_vs_benchmark_retrieval": {"ok": True, "violations": []},
            "planner_message_preview": "stub",
            "benchmark_llm_answer_preview": "stub",
            "planner_scenario_estimated_cost_usd": 0.01,
            "benchmark_llm_cost_usd": 0.001,
            "planner_discovery": {
                "planner_read_paths": [],
                "query_session_memory_call_count": 0,
                "expected_open_paths": [],
                "expected_open_paths_coverage": {"recall": 0.0},
                "expected_open_paths_full_coverage": False,
                "expect_route_substrings_coverage_on_reads": {"recall": 0.0},
                "benchmark_hit_route_coverage_on_reads": {"recall": 0.0},
            },
        }
    )
    return base


def test_build_payload_discovery_merges_router_overlay_counts():
    gold = _gold()
    gold["scenarios"].append(
        {
            "id": "scenario_b",
            "question": "Where is the antenna?",
            "expected_answer": "Unknown",
            "must_hit_tokens": ["antenna"],
            "expect_route_substrings": [],
            "min_context_support_ratio": 0.75,
        }
    )
    report = _discovery_report_two_rows()
    report["source_report_path"] = "/tmp/discovery_report.json"
    report["source_gold_path"] = "/tmp/gold.json"
    router = _router_report()
    payload = build_payload(
        report,
        gold,
        router_report=router,
        router_report_path="/tmp/router_report.json",
    )
    assert payload["harnessKind"] == "discovery"
    assert payload["routerHarnessMeta"]["no_escalation"] is False
    summary = payload["summary"]
    assert summary["routerReportSource"] == "/tmp/router_report.json"
    assert summary["benchmarkRetrievalPassCount"] == 1
    assert summary["routerNeedMoreContextCount"] == 1
    assert summary["routerEscalationRanCount"] == 1
    assert summary["routerEscalationSkippedCount"] == 0

    b_row = next(r for r in payload["rows"] if r["id"] == "scenario_b")
    act = b_row["actual"]
    assert act["routerDecision"] == "need_more_context"
    assert "Longmont Campaign/Campaign 2/README.md" in act["routerSuggestedReadPaths"]
    assert act["escalationPlannerReadPaths"]
    assert len(act["escalationPlannerToolTrace"]) == 1
    assert act["escalationPlannerToolTrace"][0]["tool"] == "read_corpus_file"


def test_render_canvas_tsx_router_payload_smokes_to_string():
    gold = _gold()
    gold["scenarios"].append(
        {
            "id": "scenario_b",
            "question": "Where is the antenna?",
            "expected_answer": "Unknown",
            "must_hit_tokens": ["antenna"],
            "expect_route_substrings": [],
            "min_context_support_ratio": 0.75,
        }
    )
    report = _router_report()
    report["source_report_path"] = "/tmp/router_report.json"
    report["source_gold_path"] = "/tmp/gold.json"
    payload = build_payload(report, gold)
    text = render_canvas_tsx(payload)
    assert "from 'cursor/canvas';" in text
    assert "PlannerDiscoveryReview" in text
    assert "harnessKind" in text
    assert '"router"' in text
    # Sanity: payload is embedded as a `const canvasData = ... as const;` literal.
    assert "as const;" in text
    # Make sure JSON inside the tsx is valid stand-alone JSON (find by markers).
    start = text.find("const canvasData = ")
    end = text.find(" as const;", start)
    assert start != -1 and end != -1
    raw_json = text[start + len("const canvasData = ") : end]
    parsed = json.loads(raw_json)
    assert parsed["harnessKind"] == "router"
    assert len(parsed["rows"]) == 2


def test_render_canvas_tsx_discovery_with_router_overlay_embeds_json():
    gold = _gold()
    gold["scenarios"].append(
        {
            "id": "scenario_b",
            "question": "Where is the antenna?",
            "expected_answer": "Unknown",
            "must_hit_tokens": ["antenna"],
            "expect_route_substrings": [],
            "min_context_support_ratio": 0.75,
        }
    )
    report = _discovery_report_two_rows()
    report["source_report_path"] = "/tmp/discovery_report.json"
    report["source_gold_path"] = "/tmp/gold.json"
    payload = build_payload(
        report,
        gold,
        router_report=_router_report(),
        router_report_path="/tmp/router_report.json",
    )
    text = render_canvas_tsx(payload)
    assert "toolTraceBlock" in text
    assert "NeedMoreContextEscalations" in text
    assert "Benchmark retrieval pass" in text
    start = text.find("const canvasData = ")
    end = text.find(" as const;", start)
    raw_json = text[start + len("const canvasData = ") : end]
    parsed = json.loads(raw_json)
    assert parsed["summary"]["routerNeedMoreContextCount"] == 1
    assert parsed["summary"]["benchmarkRetrievalPassCount"] == 1
