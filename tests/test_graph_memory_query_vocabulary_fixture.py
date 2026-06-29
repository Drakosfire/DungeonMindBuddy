from __future__ import annotations

import subprocess
import sys

from evals.graph_memory_layer import query_vocabulary_fixture as q


def test_manifest_validates() -> None:
    m=q.load_manifest(); q.validate_manifest(m)
    assert m["schema"] == q.QUERY_VOCABULARY_MANIFEST_SCHEMA
    assert m["fixture_id"] == q.QUERY_VOCABULARY_FIXTURE_ID
    assert m["campaign_id"] == "longmont-c2"
    assert m["target_session"] == 23
    assert m["execution_mode"] == "static_query_vocabulary_fixture"


def test_dependencies_validate() -> None:
    q.prototype.validate_all(); q.report.validate_all(); q.harness.validate_all()


def test_fixture_shape() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_query_vocabulary_shape(f)
    for key in ["query_intents","safe_queries","unsafe_queries","deferred_queries","answer_shapes","evidence_policies","agent_interaction_readiness"]:
        assert f[key]


def test_query_intents() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_query_intents(f)
    assert all(i["may_write_memory"] is False for i in f["query_intents"])
    assert all(i["may_execute_runtime_query"] is False for i in f["query_intents"])


def test_safe_queries() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_safe_queries(f)
    assert len(f["safe_queries"]) >= 12
    assert all(x["must_label_preview"] for x in f["safe_queries"])


def test_unsafe_queries() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_unsafe_queries(f)
    text=str(f["unsafe_queries"])
    for needle in ["Questionable Company","second wave","lightning bolt","Approve all","/plan","Agent Interaction","Promote this preview"]:
        assert needle in text


def test_deferred_queries() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_deferred_queries(f)
    assert len(f["deferred_queries"]) >= 6


def test_answer_shapes_and_evidence_policies() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_answer_shapes(f); q.validate_evidence_policies(f)
    assert "evidence:positive-answer-requires-refs" in {p["policy_id"] for p in f["evidence_policies"]}


def test_known_object_references_and_agent_boundary() -> None:
    f=q.load_query_vocabulary_fixture(); q.validate_known_object_references(f); q.validate_agent_interaction_boundary(f)
    ai=f["agent_interaction_readiness"]
    assert ai["status"] == "not_ready"
    assert ai["allowed_now"] == []
    for n in ["agent_action","plan_payload","agent_interaction_payload","runtime_query_result","approved_memory_claim"]:
        assert n in ai["must_not_emit"]


def test_report_deterministic() -> None:
    f=q.load_query_vocabulary_fixture(); md=q.load_query_vocabulary_report(); q.validate_report(md, f)
    for needle in ["Safe query examples: 12","Unsafe query examples: 11","Deferred query examples: 6","Agent Interaction readiness: not_ready"]:
        assert needle in md


def test_safety_boundary() -> None:
    q.validate_no_runtime_leakage(q.load_manifest(), q.load_query_vocabulary_fixture(), q.load_query_vocabulary_report())
    for obj in [q.load_manifest(), q.load_query_vocabulary_fixture()]:
        for key, value in obj["diagnostics"].items():
            assert value is (key == "static_query_vocabulary_fixture")


def test_cli_outputs() -> None:
    validator=subprocess.run([sys.executable,"-m","evals.graph_memory_layer.validate_query_vocabulary_fixture"], check=True, text=True, capture_output=True)
    assert "query vocabulary fixture: ready" in validator.stdout
    report=subprocess.run([sys.executable,"-m","evals.graph_memory_layer.report_query_vocabulary_fixture"], check=True, text=True, capture_output=True)
    assert q.QUERY_VOCABULARY_FIXTURE_PATH in report.stdout
    assert "Safe query examples: 12" in report.stdout
    assert "Unsafe query examples: 11" in report.stdout
    assert "Deferred query examples: 6" in report.stdout
    assert "Agent Interaction readiness: not_ready" in report.stdout
