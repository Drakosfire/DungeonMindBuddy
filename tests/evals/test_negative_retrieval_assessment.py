from evals.negative_retrieval.assessment import assess
from hashlib import sha256

import pytest

MANIFEST_PIN = sha256(b"{}").hexdigest()


@pytest.fixture
def verified_capture_owner(monkeypatch):
    """Simulated owner for tests that never contact a real database."""
    from evals.negative_retrieval import capture as module
    monkeypatch.setattr(module, "checked_owned_dsn", lambda: "synthetic-owned-clone")


def _test_manifest(tmp_path):
    path = tmp_path / "capture-manifest-input.json"
    path.write_text("{}")
    return path


def observation(**overrides):
    return dict({"reads": [], "journal_complete": True, "catalog_discoveries": 0,
                 "catalog_journal_complete": True, "outcome": "clarification",
                 "completed_turn": True, "no_premature_mutation": True,
                 "semantic_quality": True, "question_addresses_gap": True, "question_answerable": True,
                 "question_not_already_answered": True, "question_no_false_premises": True,
                 "inline_questions": True, "no_retry_error": True, "saved_and_reopened": True,
                 "answer_sent": True, "answer_continued": True, "answer_reopened": True}, **overrides)


CASE = {"max_catalog_discoveries": 0, "required_reads": [], "allowed_reads": [], "outcomes": ["clarification", "proposal"]}


def question_completion(text="Which one?"):
    from uuid import uuid4
    from application_state.agent_conversation.native_completion import SurfaceNativeCompletionV1
    return SurfaceNativeCompletionV1(surface_id="build", context_receipt_sha256="a" * 64,
        producing_provider_attempt_id=uuid4(), answer_context_status="discussion", answer_segments=[],
        collaboration={"kind": "questions", "questions": [{"text": text}]},
        saved_source_citations=[], native_body_citations=[], native_clause_citations=[],
        native_assertion_citations=[]).model_dump(mode="json", by_alias=True)


def test_clarification_requires_full_delivery_and_continuation():
    assert assess(CASE, observation())["status"] == "pass"
    for field in ("question_addresses_gap", "question_answerable", "question_not_already_answered",
                  "question_no_false_premises", "inline_questions", "no_retry_error",
                  "saved_and_reopened", "answer_sent", "answer_continued", "answer_reopened"):
        assert assess(CASE, observation(**{field: False}))["status"] == "fail"
        assert assess(CASE, observation(**{field: None}))["status"] == "unproven"


def test_interrupted_question_records_observed_ui_failure_without_inventing_outcome():
    case = {**CASE, "outcomes": ["clarification"]}
    result = assess(case, observation(outcome=None, completed_turn=False,
                                      inline_questions=False, no_retry_error=False))
    assert result["status"] == "fail"
    assert result["checks"]["allowed_outcome"] is None
    assert result["checks"]["inline_questions"] is False
    assert result["checks"]["no_retry_error"] is False
    unknown = assess(case, observation(outcome=None, completed_turn=None,
                                       inline_questions=None, no_retry_error=None))
    assert unknown["status"] == "unproven"
    assert "inline_questions" not in unknown["checks"]
    assert "no_retry_error" not in unknown["checks"]


def test_unselected_question_does_not_penalize_a_valid_movable_proposal():
    result = assess(CASE, observation(outcome="proposal", movable_proposal=True,
                                      inline_questions=False, no_retry_error=True))
    assert result["status"] == "pass"
    assert "inline_questions" not in result["checks"]


def test_observed_retry_error_fails_even_without_a_typed_outcome():
    result = assess(CASE, observation(outcome=None, completed_turn=None, no_retry_error=False))
    assert result["status"] == "fail"
    assert result["checks"]["no_retry_error"] is False
    with pytest.raises(ValueError, match="no_retry_error"):
        assess(CASE, observation(outcome=None, no_retry_error="false"))


def test_unwanted_reads_and_incomplete_journals():
    assert assess(CASE, observation(reads=["unrelated"]))["status"] == "fail"
    assert assess(CASE, observation(journal_complete=False))["status"] == "unproven"
    assert assess(CASE, observation(reads=["unrelated"], journal_complete=False))["status"] == "fail"


def test_positive_control_requires_evidence_not_merely_activity():
    case = {"max_catalog_discoveries": 1, "required_reads": ["archive"], "allowed_reads": ["archive"], "outcomes": ["answer"]}
    assert assess(case, observation(outcome="answer"))["missing_reads"] == ["archive"]
    assert assess(case, observation(outcome="answer", reads=["archive"], required_support=True))["status"] == "pass"
    assert assess(case, observation(outcome="answer", reads=["archive"]))["status"] == "unproven"


def test_partial_journal_can_prove_required_read_but_not_its_absence():
    from evals.negative_retrieval.trace_observation import UNKNOWN

    case = {"max_catalog_discoveries": 1, "required_reads": ["ledger"],
            "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    found = assess(case, observation(outcome="answer", reads=["ledger", UNKNOWN],
                                     journal_complete=False, required_support=True))
    assert found["checks"]["required_evidence"] is True
    assert found["checks"]["unexpected_retrieval"] is None
    assert found["status"] == "unproven"
    absent = assess(case, observation(outcome="answer", reads=[], journal_complete=False,
                                      required_support=True))
    assert absent["checks"]["required_evidence"] is None
    complete_absence = assess(case, observation(outcome="answer", reads=[], journal_complete=True,
                                                required_support=True))
    assert complete_absence["checks"]["required_evidence"] is False


def test_proposal_requires_movable_and_safe_boundary():
    assert assess(CASE, observation(outcome="proposal", movable_proposal=True))["status"] == "pass"
    assert assess(CASE, observation(outcome="proposal"))["status"] == "unproven"
    assert assess(CASE, observation(outcome="proposal", movable_proposal=True, no_premature_mutation=False))["status"] == "fail"


def test_fixture_splits_have_separate_rubrics_and_valid_source_labels():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "evals/negative_retrieval/fixtures"
    identities = []
    for split in ("development", "heldout-draft"):
        inputs = json.loads((root / f"{split}.json").read_text())
        rubrics = json.loads((root / f"{split}-private.json").read_text())
        assert inputs["split"] == rubrics["split"] == split
        assert {case["id"] for case in inputs["cases"]} == set(rubrics["cases"])
        for case in inputs["cases"]:
            assert "rubric" not in case and "outcomes" not in case
            grade = rubrics["cases"][case["id"]]
            labels = {page["label"] for page in case["related_pages"]}
            assert set(grade["required_reads"]) <= set(grade["allowed_reads"]) <= labels
            assert grade["rubric"].strip()
            identities.append(case["id"])
    assert len(identities) == len(set(identities))


def test_saved_trace_projection_is_a_lower_bound_and_ignores_reuse():
    from evals.negative_retrieval.trace_observation import observed_acquisitions

    trace = {"schema": "dmb_turn_context_trace_v1", "capture_status": "complete",
             "terminal_status": "completed", "observations": [
                 {"sequence": 0, "kind": "source_passage_reuse", "source_artifact_id": "old"},
                 {"sequence": 1, "kind": "graph_tool"},
                 {"sequence": 2, "kind": "source_passage", "source_artifact_id": "ledger-id"},
                 {"sequence": 3, "kind": "context_decision", "action": "retrieved",
                  "policy_version": "selected_exact_related_authored_pages_v1", "item_ids": ["page"]}]}
    projection = observed_acquisitions(trace, related_labels={"page": "ledger"},
                                       source_labels={"ledger-id": "ledger"})
    assert [x["kind"] for x in projection["observed"]] == ["graph_operation", "source_read", "related_page_read"]
    assert projection["journal_complete"] is None
    trace["observations"][1]["sequence"] = 4
    try:
        observed_acquisitions(trace)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-order trace accepted")


def test_native_read_activity_is_an_unmapped_attempt_not_a_complete_journal():
    import pytest
    from evals.negative_retrieval.trace_observation import UNKNOWN, observed_acquisitions

    policies = ("native_statement_read_progress_v1", "native_assertion_read_progress_v1",
                "native_source_document_read_progress_v2", "native_source_section_read_progress_v2",
                "native_source_search_progress_v2")
    events = [{"sequence": index, "kind": "context_decision", "action": action,
               "policy_version": policy, "item_ids": ["opaque", "display"]}
              for index, (policy, action) in enumerate(zip(policies, ("expanded", "retained", "retrieved", "expanded", "retrieved")))]
    events.append({"sequence": len(events), "kind": "context_decision", "action": "retrieved",
                   "policy_version": "native_unknown_progress_v2", "item_ids": ["opaque"]})
    trace = {"schema": "dmb_turn_context_trace_v1", "observations": events}
    result = observed_acquisitions(trace)
    assert [row["label"] for row in result["observed"]] == [UNKNOWN] * len(policies)
    assert [row["kind"] for row in result["observed"]].count("native_search_activity") == 1
    assert result["journal_complete"] is None
    assert assess(CASE, observation(reads=[row["label"] for row in result["observed"]], journal_complete=False))["checks"]["unexpected_retrieval"] is False
    events[0]["item_ids"] = []
    with pytest.raises(ValueError, match="Native read activity"):
        observed_acquisitions(trace)


def test_rates_bound_unknown_evidence_without_hiding_observed_failures():
    from evals.negative_retrieval.assessment import REPORT_SCHEMA, rubric_sha256, summarize

    positive = {"max_catalog_discoveries": 1, "required_reads": ["archive"], "allowed_reads": ["archive"], "outcomes": ["answer"]}
    cases = {"n1": CASE, "n2": CASE, "p1": positive}
    results = {"n1": assess(CASE, observation(reads=["other"], journal_complete=False)),
               "n2": assess(CASE, observation(reads=[], journal_complete=False)),
               "p1": assess(positive, observation(outcome="answer", journal_complete=False))}
    unbound = summarize(cases, results)
    assert unbound["unnecessary_retrieval"]["failures"] == 0
    assert unbound["unnecessary_retrieval"]["unknown"] == 2
    results = {key: {**result, "schema": REPORT_SCHEMA, "case_id": key,
                     "rubric_sha256": rubric_sha256(cases[key]), "fixture_context_verified": True,
                     "capture_environment_verified": True} for key, result in results.items()}
    rates = summarize(cases, results)
    assert rates["unnecessary_retrieval"] == {"cases": 2, "failures": 1, "unknown": 1,
                                                "minimum_rate": .5, "maximum_rate": 1.0}
    assert rates["missed_required_reads"]["unknown"] == 1
    assert rates["missed_required_reads"]["maximum_rate"] == 1.0


def test_rates_do_not_count_unbound_or_unverified_capture_observations():
    from evals.negative_retrieval.assessment import REPORT_SCHEMA, rubric_sha256, summarize

    positive = {"max_catalog_discoveries": 1, "required_reads": ["ledger"],
                "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    cases = {"negative": CASE, "positive": positive, "missing": CASE}
    negative = assess(CASE, observation(reads=["unrelated"]))
    missing_read = assess(positive, observation(outcome="answer", required_support=True))
    raw_rates = summarize({"negative": CASE, "positive": positive},
                          {"negative": negative, "positive": missing_read})
    assert raw_rates["unnecessary_retrieval"]["unknown"] == 1
    assert raw_rates["missed_required_reads"]["unknown"] == 1
    assert raw_rates["missed_required_reads"]["failures"] == 0
    results = {
        "negative": {**negative, "schema": REPORT_SCHEMA, "case_id": "negative", "rubric_sha256": rubric_sha256(CASE), "fixture_context_verified": None, "capture_environment_verified": True},
        "positive": {**missing_read, "schema": REPORT_SCHEMA, "case_id": "positive", "rubric_sha256": rubric_sha256(positive), "fixture_context_verified": True, "capture_environment_verified": None},
        "missing": {"status": "unproven", "missing_artifacts": ["request"]},
    }
    rates = summarize(cases, results)
    assert rates["unnecessary_retrieval"] == {"cases": 2, "failures": 0, "unknown": 2,
                                               "minimum_rate": 0.0, "maximum_rate": 1.0}
    assert rates["missed_required_reads"] == {"cases": 1, "failures": 0, "unknown": 1,
                                               "minimum_rate": 0.0, "maximum_rate": 1.0}
    results["negative"]["fixture_context_verified"] = True
    results["positive"]["capture_environment_verified"] = True
    rates = summarize(cases, results)
    assert rates["unnecessary_retrieval"]["failures"] == 1
    assert rates["missed_required_reads"]["failures"] == 1
    results["negative"]["case_id"] = "other"
    assert summarize(cases, results)["unnecessary_retrieval"]["failures"] == 0
    results["negative"]["case_id"] = "negative"
    changed_cases = {**cases, "negative": {**CASE, "max_catalog_discoveries": CASE["max_catalog_discoveries"] + 1}}
    assert summarize(changed_cases, results)["unnecessary_retrieval"]["failures"] == 0
    del results["negative"]["capture_environment_verified"]
    assert summarize(cases, results)["unnecessary_retrieval"]["failures"] == 0
    del results["negative"]["fixture_context_verified"]
    assert summarize(cases, results)["unnecessary_retrieval"]["failures"] == 0
    del results["negative"]["schema"]
    assert summarize(cases, results)["unnecessary_retrieval"]["failures"] == 0


def test_unmapped_acquisition_fails_zero_budget_but_is_unknown_for_positive_control():
    from evals.negative_retrieval.trace_observation import UNKNOWN

    positive = {"max_catalog_discoveries": 1, "required_reads": ["ledger"], "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    negative = assess(CASE, observation(reads=[UNKNOWN]))
    unclear = assess(positive, observation(reads=[UNKNOWN], outcome="answer", required_support=True))
    assert negative["checks"]["unexpected_retrieval"] is False
    assert unclear["checks"]["unexpected_retrieval"] is None
    assert unclear["checks"]["required_evidence"] is None
    assert unclear["status"] == "unproven"


def test_ordinary_capture_requires_exact_bound_saved_question():
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid5
    from evals.negative_retrieval.capture_observation import observe

    def envelope(body, status=200):
        raw = json.dumps(body).encode()
        return {"http_status": status, "body": body, "raw_body_hex": raw.hex(),
                "raw_body_sha256": hashlib.sha256(raw).hexdigest()}

    request = {"turn_id": "client-turn", "client_thread_id": "client-thread", "message": "Which one?",
               "owner_scope": {"world_id": "world"}, "surface": {"surface_id": "build", "instance_id": "page"}}
    turn = {"turn_id": "saved-turn", "idempotency_key": str(uuid5(NAMESPACE_URL, "dmb-agent-turn:world:client-turn")),
            "user_text": request["message"], "lifecycle_status": "completed", "provenance": {
                "world_id": "world", "surface_id": "build", "surface_instance_id": "page"},
            "knowledge_context": {"completion": question_completion()}}
    history = {"world_id": "world", "conversation_id": "conversation", "turns": [turn]}
    attempt = {"schema": "dmb_turn_context_trace_v1", "world_id": "world", "conversation_id": "conversation",
               "turn_id": "saved-turn", "terminal_status": "completed", "capture_status": "complete", "observations": []}
    trace = {"world_id": "world", "turn_id": "saved-turn", "attempts": [attempt]}
    answer = {"turn_id": "client-turn", "client_thread_id": "client-thread",
              "knowledge_context": {"completion": turn["knowledge_context"]["completion"]}}
    result = observe(request, envelope(history), envelope(trace), envelope(answer))
    assert result["outcome"] == "clarification" and result["completed_turn"]
    assert result["journal_complete"] is None
    answer["knowledge_context"] = {"completion": {}}
    assert observe(request, envelope(history), envelope(trace), envelope(answer))["outcome"] is None
    invalid = {"collaboration": {"kind": "questions", "questions": [{"text": "Which one?", "extra": "invalid"}]}}
    turn["knowledge_context"]["completion"] = invalid
    answer["knowledge_context"] = {"completion": invalid}
    assert observe(request, envelope(history), envelope(trace), envelope(answer))["outcome"] is None
    invalid = {"collaboration": {"kind": "questions", "questions": [{"text": "Which one?"}]}}
    turn["knowledge_context"]["completion"] = invalid
    answer["knowledge_context"] = {"completion": invalid}
    assert observe(request, envelope(history), envelope(trace), envelope(answer))["outcome"] is None
    from application_state.agent_conversation.types import BuildAuthoringCompletionV1, BUILD_PROPOSAL_READY_TEXT
    from uuid import uuid4
    proposal = BuildAuthoringCompletionV1(context_receipt_sha256="a" * 64,
        answer_segments=[{"kind": "connective", "text": BUILD_PROPOSAL_READY_TEXT}],
        action_id=uuid4(), reservation_sha256="b" * 64, proposal_result_sha256="c" * 64,
        provider_attempt_id=uuid4(), envelope_sha256="d" * 64).model_dump(mode="json", by_alias=True)
    turn["knowledge_context"]["completion"] = proposal
    answer["knowledge_context"] = {"completion": proposal}
    result = observe(request, envelope(history), envelope(trace), envelope(answer))
    assert result["outcome"] == "proposal"
    assert assess(CASE, result)["checks"]["movable_proposal"] is None
    answer["knowledge_context"] = {"completion": {**proposal, "action_id": str(uuid4())}}
    assert observe(request, envelope(history), envelope(trace), envelope(answer))["outcome"] is None
    malformed = {**proposal, "action_id": "not-a-uuid"}
    turn["knowledge_context"]["completion"] = malformed
    answer["knowledge_context"] = {"completion": malformed}
    assert observe(request, envelope(history), envelope(trace), envelope(answer))["outcome"] is None
    from application_state.agent_conversation.native_completion import SurfaceNativeCompletionV1
    native = SurfaceNativeCompletionV1(surface_id="build", context_receipt_sha256="a" * 64,
        producing_provider_attempt_id=uuid4(), answer_context_status="discussion",
        answer_segments=[{"kind": "discussion", "text": "A response."}], collaboration=None,
        saved_source_citations=[], native_body_citations=[], native_clause_citations=[],
        native_assertion_citations=[]).model_dump(mode="json", by_alias=True)
    turn["knowledge_context"]["completion"] = native
    answer["knowledge_context"] = {"completion": native}
    observed = observe(request, envelope(history), envelope(trace), envelope(answer))
    assert observed["outcome"] == "answer"
    positive = {**CASE, "outcomes": ["answer"], "required_reads": ["ledger"], "allowed_reads": ["ledger"]}
    assert assess(positive, observed)["checks"]["required_support"] is None
    answer["knowledge_context"] = {"completion": {**native, "surface_id": "plan"}}
    assert observe(request, envelope(history), envelope(trace), envelope(answer))["outcome"] is None
    turn["lifecycle_status"] = "interrupted"
    result = observe(request, envelope(history), envelope(trace), envelope({"detail": "question"}, 409))
    assert result["outcome"] is None and result["completed_turn"] is False
    trace["turn_id"] = "different"
    try:
        observe(request, envelope(history), envelope(trace), envelope(answer))
    except ValueError:
        pass
    else:
        raise AssertionError("unrelated trace accepted")


def test_unmapped_label_cannot_be_whitelisted():
    from evals.negative_retrieval.trace_observation import UNKNOWN

    try:
        assess({"max_catalog_discoveries": 0, "required_reads": [], "allowed_reads": [UNKNOWN], "outcomes": ["answer"]}, observation())
    except ValueError:
        pass
    else:
        raise AssertionError("unmapped acquisition was whitelisted")


def test_probe_wraps_real_discovery_owner_and_restores_on_exception(monkeypatch):
    from types import SimpleNamespace
    import pytest
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners

    calls = []
    def empty_registry(*args, **kwargs):
        calls.append("queried")
        return []

    monkeypatch.setattr(build_related_pages, "list_workspace_documents", empty_registry)
    monkeypatch.setattr(build_related_pages, "root", lambda: "unused")
    request = SimpleNamespace(owner_scope=SimpleNamespace(world_id="world"),
                              primary_work=SimpleNamespace(object_id="page"))
    original = build_related_pages.discover
    with pytest.raises(RuntimeError, match="sentinel"):
        with observe_related_page_owners() as records:
            assert build_related_pages.discover(request) == []
            assert records == [{"owner": "related_catalog_discovery", "state": "returned"}]
            raise RuntimeError("sentinel")
    assert calls == ["queried"]
    assert build_related_pages.discover is original


def test_build_budget_discovers_related_catalog_before_any_decision(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners

    monkeypatch.setattr(build_related_pages, "list_workspace_documents", lambda *a, **kw: [])
    monkeypatch.setattr(build_related_pages, "root", lambda: "unused")
    harness = BuildJevHarness(related_pages=True)
    monkeypatch.setattr(harness, "budget", lambda *a, **kw: {"buildJevActions": {}})
    request = SimpleNamespace(build_draft_context=object(), reviewed_step=object(),
                              owner_scope=SimpleNamespace(world_id="world"),
                              primary_work=SimpleNamespace(object_id="page"))
    with observe_related_page_owners() as records:
        budget = harness.configured_budget(request)
    assert budget["buildJevActions"]["related_page_catalog"] == []
    assert records == [{"owner": "related_catalog_discovery", "state": "returned"}]


def test_native_graph_probe_records_direct_calls_and_restores_after_error(monkeypatch):
    import pytest
    from apps.live_control_server.services import native_graph_reads
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records

    sentinel = object()
    def query(*args, **kwargs):
        return sentinel
    def fail(*args, **kwargs):
        raise ValueError("synthetic failure")
    monkeypatch.setattr(native_graph_reads, "prepare_query", query)
    monkeypatch.setattr(native_graph_reads, "read_selected", fail)
    with observe_native_graph_owners() as records:
        assert native_graph_reads.prepare_query("private input") is sentinel
        with pytest.raises(ValueError, match="synthetic failure"):
            native_graph_reads.read_selected("private input")
        with pytest.raises(RuntimeError, match="serial process"):
            with observe_native_graph_owners():
                pass
    assert records == [{"owner": "native_graph_query", "state": "returned"},
                       {"owner": "native_graph_selected_read", "state": "raised"}]
    assert native_graph_reads.prepare_query is query
    assert native_graph_reads.read_selected is fail
    assert summarize_records(records)["native_graph_query"]["returned"] == 1
    for malformed in ([{"owner": "native_graph_query", "state": []}],
                      [{"owner": "native_graph_query", "state": "returned", "text": "private"}],
                      [{"owner": "unknown", "state": "returned"}]):
        with pytest.raises(ValueError, match="Malformed"):
            summarize_records(malformed)


def test_native_graph_probe_observes_preimported_authored_reader(monkeypatch):
    from apps.live_control_server.services import native_authored_references, native_graph_reads
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners

    def reader(*args):
        return "read"

    monkeypatch.setattr(native_graph_reads, "read_authored_reference", reader)
    monkeypatch.setattr(native_authored_references, "read_authored_reference", reader)
    monkeypatch.setattr(native_corpus_source, "read_authored_source", reader)
    monkeypatch.setattr(native_authored_references, "read_authored_source", reader)
    with observe_native_graph_owners() as records:
        assert native_authored_references.read_authored_reference("private") == "read"
        assert native_authored_references.read_authored_source("private") == "read"
    assert records == [{"owner": "native_graph_authored_reference_read", "state": "returned"},
                       {"owner": "native_corpus_authored_source_read", "state": "returned"}]
    assert native_authored_references.read_authored_reference is reader
    assert native_authored_references.read_authored_source is reader


def test_empty_catalog_discovery_is_not_a_zero_acquisition_pass():
    from evals.negative_retrieval.related_page_probe import catalog_discovery_count

    evidence = [{"owner": "related_catalog_discovery", "state": "returned"}]
    result = assess(CASE, observation(catalog_discoveries=catalog_discovery_count(evidence), journal_complete=False))
    assert result["checks"]["catalog_budget"] is False
    assert result["status"] == "fail"


def test_capture_wrapper_retains_probe_on_failure_and_restores_owner(tmp_path, monkeypatch, verified_capture_owner):
    import json
    import pytest
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture
    from apps.live_control_server.services import build_related_pages, native_graph_reads

    original_discover = build_related_pages.discover
    class Client:
        def post(self, route, *args, **kwargs):
            assert route == "/api/live/agent/turn"
            native_graph_reads.prepare_query("private question")
            return build_related_pages.discover(None)

    def fail_case(client, world, template, case, directory, **kwargs):
        return client.post("/api/live/agent/turn", json={})

    def fail_discovery(request):
        raise RuntimeError("observed failure")

    monkeypatch.setattr(build_related_pages, "discover", fail_discovery)
    monkeypatch.setattr(native_graph_reads, "prepare_query", lambda *_: None)
    monkeypatch.setattr(workflow, "capture_case", fail_case)
    original_case = workflow.capture_case
    def ordinary_capture(manifest, output, **kwargs):
        assert kwargs["clone_app"] is False and len(kwargs["cohort_manifest_sha256"]) == 64
        return workflow.capture_case(Client(), "world", {}, {"id": "case1"}, output)
    monkeypatch.setattr(workflow, "capture", ordinary_capture)
    monkeypatch.setattr(workflow, "load_manifest", lambda *args, **kwargs: ({"conversation_mode": "build_sequence"}, tmp_path))
    with pytest.raises(RuntimeError, match="observed failure"):
        capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    evidence = json.loads((tmp_path / "case1" / "related-page-probe.json").read_text())
    assert evidence["coverage"] == "partial"
    assert evidence["records"] == [{"owner": "related_catalog_discovery", "state": "raised"}]
    native = json.loads((tmp_path / "case1" / "native-graph-probe.json").read_text())
    assert native["status"] == "observed" and native["coverage"] == "partial"
    assert native["records"] == [{"owner": "native_graph_query", "state": "returned"}]
    assert workflow.capture_case is original_case
    assert build_related_pages.discover is fail_discovery
    assert original_discover is not fail_discovery


def test_offline_report_keeps_missing_and_positive_retrieval_evidence_honest(tmp_path):
    import json
    from evals.negative_retrieval.report import report_case

    fixture = {"id": "case1", "request": "Write the idea."}
    result = report_case(tmp_path, fixture, CASE)
    assert result["status"] == "unproven"
    assert "related-page-probe" in result["missing_artifacts"]
    # An unrelated or malformed probe must not be accepted as evidence.
    for name in ("request", "history-after", "context-trace", "answer-http"):
        (tmp_path / f"{name}.json").write_text(json.dumps({"message": fixture["request"]}))
    (tmp_path / "related-page-probe.json").write_text(json.dumps({"schema": "wrong"}))
    try:
        report_case(tmp_path, fixture, CASE)
    except ValueError as exc:
        assert "probe" in str(exc)
    else:
        raise AssertionError("unbound probe accepted")


def test_partial_capture_retains_probe_failure_without_claiming_a_rate(tmp_path):
    import json
    import pytest
    from evals.negative_retrieval.assessment import rubric_sha256, summarize
    from evals.negative_retrieval.report import report_case

    fixture = {"id": "case1", "request": "Use that."}
    probe = {"schema": "dmb_negative_retrieval_related_page_probe_v1", "case_id": "case1",
             "coverage": "partial", "records": [
                 {"owner": "related_catalog_discovery", "state": "returned"},
                 {"owner": "related_page_materialization", "state": "raised"}]}
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    (tmp_path / "terminal.json").write_text(json.dumps({"status": "outcome_unknown", "error_type": "RuntimeError"}))
    (tmp_path / "native-graph-probe.json").write_text(json.dumps({
        "schema": "dmb_negative_retrieval_native_graph_probe_v1", "coverage": "partial", "case_id": "case1",
        "status": "observed", "records": [{"owner": "native_graph_query", "state": "raised"}]}))
    report = report_case(tmp_path, fixture, CASE)
    assert report["case_id"] == "case1" and report["rubric_sha256"] == rubric_sha256(CASE)
    assert report["status"] == "unproven" and "answer-http" in report["missing_artifacts"]
    assert report["partial_native_graph_probe"]["counts"]["native_graph_query"]["raised"] == 1
    assert report["partial_probe"] == {"status": None, "window": None, "catalog_discoveries": 1, "materialization_attempts": 1,
                                       "raised_discoveries": 0, "raised_materializations": 1}
    assert report["capture_terminal"] == {"status": "outcome_unknown", "error_type": "RuntimeError"}
    assert summarize({"case1": CASE}, {"case1": report})["unnecessary_retrieval"]["unknown"] == 1
    probe["case_id"] = "other"
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    with pytest.raises(ValueError, match="probe"):
        report_case(tmp_path, fixture, CASE)


def test_fixture_pin_binds_case_and_caller_supplied_set_digest():
    import copy
    import pytest
    from evals.negative_retrieval.capture import fixture_sha256
    from evals.negative_retrieval.report import verify_fixture_pin

    fixture = {"id": "case1", "request": "Use that.", "page": "# Page", "history": [], "related_pages": []}
    fixtures = {"case1": fixture}
    pin = fixture_sha256(fixtures)
    record = {"schema": "dmb_negative_retrieval_fixture_pin_v1", "case_id": "case1",
              "fixture_set_sha256": pin, "case_sha256": fixture_sha256(fixtures)}
    assert verify_fixture_pin(fixture, record, pin, fixtures)
    changed = copy.deepcopy(fixture)
    changed["page"] = "# Changed"
    forged_record = {**record, "case_sha256": fixture_sha256({"case1": changed})}
    for case, proof, expected, full_set in ((changed, record, pin, fixtures), (fixture, record, None, fixtures),
            (fixture, record, "0" * 64, fixtures), (fixture, {**record, "case_id": "other"}, pin, fixtures),
            (changed, forged_record, pin, fixtures), (fixture, record, pin, None),
            (changed, forged_record, pin, {"case1": changed})):
        with pytest.raises(ValueError, match="Fixture pin"):
            verify_fixture_pin(case, proof, expected, full_set)


def test_offline_report_joins_real_wire_shapes_and_detects_empty_catalog_probe(tmp_path):
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid5
    from evals.negative_retrieval.report import report_case

    def envelope(body, status=200):
        raw = json.dumps(body).encode()
        return {"http_status": status, "body": body, "raw_body_hex": raw.hex(),
                "raw_body_sha256": hashlib.sha256(raw).hexdigest()}
    request = {"turn_id": "turn", "client_thread_id": "thread", "message": "Use that idea.",
               "owner_scope": {"world_id": "world"}, "surface": {"surface_id": "build", "instance_id": "page"}}
    turn = {"turn_id": "saved", "idempotency_key": str(uuid5(NAMESPACE_URL, "dmb-agent-turn:world:turn")),
            "user_text": request["message"], "lifecycle_status": "completed", "provenance": {
                "world_id": "world", "surface_id": "build", "surface_instance_id": "page"},
            "knowledge_context": {"completion": question_completion("Where?")}}
    history = {"world_id": "world", "conversation_id": "conversation", "turns": [turn]}
    attempt = {"schema": "dmb_turn_context_trace_v1", "world_id": "world", "conversation_id": "conversation",
               "turn_id": "saved", "terminal_status": "completed", "capture_status": "complete", "observations": []}
    trace = {"world_id": "world", "turn_id": "saved", "attempts": [attempt]}
    probe = {"schema": "dmb_negative_retrieval_related_page_probe_v1", "coverage": "partial", "case_id": "case1",
             "status": "observed", "window": "turn_post_v1", "records": [{"owner": "related_catalog_discovery", "state": "returned"}]}
    artifacts = {"request": request, "history-after": envelope(history), "context-trace": envelope(trace),
                 "answer-http": envelope({"turn_id": "turn", "client_thread_id": "thread",
                                          "knowledge_context": turn["knowledge_context"]}), "related-page-probe": probe}
    artifacts["answer-http"]["elapsed_ms"] = 1234.5
    for name, value in artifacts.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    result = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    assert result["response_latency"]["elapsed_ms"] == 1234.5
    assert "request cycle through response envelope processing" in result["response_latency"]["basis"]
    assert result["status"] == "unproven"
    assert result["observation_status"] == "unproven"  # Matching native window is absent.
    assert result["fixture_context_verified"] is None
    assert result["primary_context_verified"] is None
    assert result["checks"]["catalog_budget"] is None
    assert result["checks"]["inline_questions"] is None
    assert len(result["artifact_sha256"]) == len(artifacts)
    native_path = tmp_path / "native-graph-probe.json"
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed",
        "window": "turn_post_v1", "records": []}))
    matched = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    assert matched["checks"]["catalog_budget"] is False
    mismatched = json.loads(native_path.read_text())
    mismatched["status"] = "not_started"
    native_path.write_text(json.dumps(mismatched))
    assert report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)["checks"]["catalog_budget"] is None
    probe.pop("status")
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    mismatched["status"] = "observed"
    native_path.write_text(json.dumps(mismatched))
    assert report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)["checks"]["catalog_budget"] is None
    probe["status"] = "observed"
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    mismatched["window"] = "unrecognized"
    native_path.write_text(json.dumps(mismatched))
    with pytest.raises(ValueError, match="Native Graph probe"):
        report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    probe["window"] = "unrecognized"
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    mismatched["window"] = "turn_post_v1"
    native_path.write_text(json.dumps(mismatched))
    with pytest.raises(ValueError, match="related-page probe status"):
        report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    probe["window"] = "turn_post_v1"
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    for owner, state, expected in (
        ("native_graph_selected_read", "returned", False),
        ("native_graph_authored_reference_read", "raised", False),
        ("native_corpus_authored_source_read", "returned", False),
        ("native_corpus_member_read", "returned", False),
        ("native_corpus_body_open", "returned", False),
        ("native_corpus_direct_read", "raised", False),
        ("native_graph_selected_read", "entered", False),
        ("native_graph_query", "returned", None),
    ):
        native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
            "coverage": "partial", "case_id": "case1", "status": "observed", "window": "turn_post_v1",
            "records": [{"owner": owner, "state": state}]}))
        observed = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
        assert observed["checks"]["unexpected_retrieval"] is expected
        assert observed["status"] == "unproven"
    probe["records"] = []
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed",
        "records": [{"owner": "native_graph_query", "state": "returned"}]}))
    no_queries = {**CASE, "max_graph_query_attempts": 0}
    legacy = report_case(tmp_path, {"id": "case1", "request": request["message"]}, no_queries)
    assert legacy["checks"]["graph_query_budget"] is None  # Old probes wrapped setup too.
    probe.update(status="observed", window="turn_post_v1")
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    native = json.loads(native_path.read_text())
    native["window"] = "turn_post_v1"
    native_path.write_text(json.dumps(native))
    graph_only = report_case(tmp_path, {"id": "case1", "request": request["message"]}, no_queries)
    assert graph_only["checks"]["graph_query_budget"] is False
    assert graph_only["checks"]["unexpected_retrieval"] is None
    assert graph_only["status"] == "unproven"
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed", "window": "turn_post_v1",
        "records": [{"owner": "native_corpus_discovery", "state": "returned"}]}))
    observed = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    assert observed["checks"]["catalog_budget"] is False
    assert observed["checks"]["unexpected_retrieval"] is None
    assert observed["status"] == "unproven"
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed", "window": "turn_post_v1",
        "records": [{"owner": "native_corpus_discovery", "state": "returned"},
                    {"owner": "native_corpus_body_open", "state": "returned"}]}))
    one_catalog_no_reads = {**CASE, "max_catalog_discoveries": 1}
    observed = report_case(tmp_path, {"id": "case1", "request": request["message"]}, one_catalog_no_reads)
    assert observed["checks"]["catalog_budget"] is None  # partial cannot prove completeness
    assert observed["checks"]["unexpected_retrieval"] is False
    assert observed["status"] == "unproven"
    # A search event is discovery, not proof of a body read. Trace and owner
    # probe may witness the same search, so they form a lower bound, not a sum.
    attempt["observations"] = [
        {"sequence": 0, "kind": "context_decision", "action": "expanded",
         "policy_version": "native_source_search_progress_v2", "item_ids": ["private"]},
        {"sequence": 1, "kind": "context_decision", "action": "retrieved",
         "policy_version": "native_source_search_progress_v2", "item_ids": ["private"]},
    ]
    (tmp_path / "context-trace.json").write_text(json.dumps(envelope(trace)))
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed", "window": "turn_post_v1",
        "records": [{"owner": "native_corpus_discovery", "state": "returned"}]}))
    one_catalog_no_reads = {**CASE, "max_catalog_discoveries": 1}
    search_only = report_case(tmp_path, {"id": "case1", "request": request["message"]}, one_catalog_no_reads)
    assert search_only["checks"]["catalog_budget"] is None  # one, not two; still partial
    assert search_only["checks"]["unexpected_retrieval"] is None
    no_catalog = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    assert no_catalog["checks"]["catalog_budget"] is False
    # Mixed or repeated outcome stages are not proven distinct operations.
    attempt["observations"].append({"sequence": 2, "kind": "context_decision", "action": "retained",
        "policy_version": "native_source_search_progress_v2", "item_ids": ["private"]})
    attempt["observations"].append({"sequence": 3, "kind": "context_decision", "action": "expanded",
        "policy_version": "native_source_search_progress_v2", "item_ids": ["private"]})
    (tmp_path / "context-trace.json").write_text(json.dumps(envelope(trace)))
    mixed = report_case(tmp_path, {"id": "case1", "request": request["message"]}, one_catalog_no_reads)
    assert mixed["checks"]["catalog_budget"] is None
    assert mixed["checks"]["unexpected_retrieval"] is None
    attempt["observations"] = []
    (tmp_path / "context-trace.json").write_text(json.dumps(envelope(trace)))
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed", "window": "turn_post_v1",
        "records": [{"owner": "native_corpus_discovery", "state": "returned"},
                    {"owner": "native_corpus_body_open", "state": "returned"}]}))
    # Old probes wrapped setup and history as well as the turn. Their records
    # remain visible but cannot be attributed to this turn.
    probe.pop("window")
    probe["records"] = [{"owner": "related_catalog_discovery", "state": "returned"},
                        {"owner": "related_page_materialization", "state": "returned"}]
    (tmp_path / "related-page-probe.json").write_text(json.dumps(probe))
    legacy_native = json.loads(native_path.read_text())
    legacy_native.pop("window")
    native_path.write_text(json.dumps(legacy_native))
    legacy = report_case(tmp_path, {"id": "case1", "request": request["message"]}, no_queries)
    assert legacy["checks"]["catalog_budget"] is None
    assert legacy["checks"]["unexpected_retrieval"] is None
    assert legacy["checks"]["graph_query_budget"] is None
    assert legacy["partial_probe"]["materialization_attempts"] == 1


def test_fixture_binding_checks_owner_receipt_page_and_complete_dialogue(monkeypatch):
    import copy
    import hashlib
    import json
    import pytest
    from types import SimpleNamespace
    from uuid import NAMESPACE_URL, uuid5
    from apps.live_control_server.models.agent_turn import AgentSurfaceNativeContextResponseV1
    from application_state.agent_conversation import native_context, types
    from evals.negative_retrieval.fixture_binding import verify_fixture

    def envelope(body):
        raw = json.dumps(body).encode()
        return {"http_status": 200, "body": body, "raw_body_hex": raw.hex(),
                "raw_body_sha256": hashlib.sha256(raw).hexdigest()}
    page = "# A page\nA fact."
    digest = hashlib.sha256(page.encode()).hexdigest()
    snap = {"world_id": "world", "document_id": "page", "registry_revision": 1,
            "visibility": "internal", "content_sha256": digest, "draft_sha256": digest, "draft_markdown": page}
    request = {"turn_id": "turn", "message": "Use that.", "owner_scope": {"world_id": "world"},
               "surface": {"surface_id": "build", "instance_id": "page"},
               "primary_work": {"object_id": "page", "expected_revision": 1, "expected_content_sha256": digest},
               "build_draft_context": {"conversation_id": "chat", "expected_pointer_revision": 2, "snapshot": snap}}
    prior = {"world_id": "world", "conversation_id": "chat", "active_conversation_id": "chat",
             "pointer_revision": 2, "next_before_sequence": None,
             "turns": [{"turn_id": "old", "sequence": 1, "lifecycle_status": "completed", "user_text": "Idea?", "assistant_text": "A star."}]}
    turn = {"turn_id": "new", "sequence": 2, "idempotency_key": str(uuid5(NAMESPACE_URL, "dmb-agent-turn:world:turn")), "user_text": "Use that.",
            "provenance": {"world_id": "world", "surface_id": "build", "surface_instance_id": "page"},
            "knowledge_context": {"schema": "dmb_agent_surface_native_context_response_v1", "synthetic": True}}
    after = {"world_id": "world", "conversation_id": "chat", "active_conversation_id": "chat", "pointer_revision": 2,
             "next_before_sequence": None, "turns": [copy.deepcopy(prior["turns"][0]), turn]}
    fixture = {"request": "Use that.", "page": page,
               "history": [{"role": "user", "content": "Idea?"}, {"role": "assistant", "content": "A star."}]}
    basis = SimpleNamespace(**{k: snap[k] for k in ("world_id", "document_id", "registry_revision", "visibility", "content_sha256")})
    context = SimpleNamespace(receipt=SimpleNamespace(work_context=SimpleNamespace(surface_id="build", source_basis=basis)))
    monkeypatch.setattr(AgentSurfaceNativeContextResponseV1, "model_validate", lambda *a, **k: context)
    monkeypatch.setattr(types.TurnProvenance, "model_validate", lambda *a, **k: object())
    monkeypatch.setattr(native_context, "validate_work_context", lambda *a, **k: None)
    assert verify_fixture(fixture, request, envelope(prior), envelope(after)) is True
    for mutate in (lambda p: p.update(next_before_sequence=1),
                   lambda p: p["turns"][0].update(assistant_text="Different."),
                   lambda p: p.update(pointer_revision=3)):
        changed = copy.deepcopy(prior)
        mutate(changed)
        with pytest.raises(ValueError):
            verify_fixture(fixture, request, envelope(changed), envelope(after))
    changed_after = copy.deepcopy(after)
    changed_after["turns"][0]["assistant_text"] = "Changed after capture."
    with pytest.raises(ValueError):
        verify_fixture(fixture, request, envelope(prior), envelope(changed_after))
    changed_request = copy.deepcopy(request)
    changed_request["build_draft_context"]["snapshot"]["draft_markdown"] = "Different page"
    with pytest.raises(ValueError):
        verify_fixture(fixture, changed_request, envelope(prior), envelope(after))
    basis.content_sha256 = "0" * 64
    with pytest.raises(ValueError):
        verify_fixture(fixture, request, envelope(prior), envelope(after))


def test_ui_witness_generator_requires_exact_owner_fixture(tmp_path):
    from pathlib import Path
    import pytest
    from evals.negative_retrieval.build_inline_witness import generate

    root = Path(__file__).resolve().parents[2]
    source = root / "apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx"
    derived = tmp_path / "derived.test.tsx"
    generate(source, derived)
    content = derived.read_text()
    assert content.count("negative retrieval Build inline question answer and send witness") == 1
    assert "postWorldBuildAgentTurn" in content and "The harbour shop." in content
    assert "setupApi(savedHistory, false)" in content
    assert "const savedQuestion = await screen.findByText" in content
    assert "The harbour shop is ready for review." in content
    assert "Retry this saved request" in content
    broken = tmp_path / "broken.test.tsx"
    broken.write_text(source.read_text().replace("rehydrates an intentional object-only clarification inline without a filler reply", "renamed"))
    with pytest.raises(ValueError):
        generate(broken, derived)


def test_frozen_placement_generator_pins_input_and_owner_anchors(tmp_path):
    from pathlib import Path
    import pytest
    from evals.negative_retrieval.frozen_placement_witness import generate

    root = Path(__file__).resolve().parents[2]
    source = root / "tests/test_surface_native_build_ordinary.py"
    fixture = root / "evals/negative_retrieval/fixtures/development.json"
    digest = sha256(fixture.read_bytes()).hexdigest()
    output = tmp_path / "derived.py"
    generate(source, output, fixture, expected_fixture_sha256=digest)
    content = output.read_text()
    compile(content, str(output), "exec")
    assert "test_negative_retrieval_frozen_placement_http" in content
    assert "negative_retrieval_frozen_inventory_before: verified" in content
    assert "negative_retrieval_frozen_proposal_moved_unchanged_page: true" in content
    assert "zero discovery and materialization budget" in content
    skip_output = tmp_path / "skip.py"
    generate(source, skip_output, fixture, expected_fixture_sha256=digest, related_page_vote="skip")
    skip_content = skip_output.read_text()
    compile(skip_content, str(skip_output), "exec")
    assert 'else "skip" if read_optional_page and name.startswith("related_page_")' in skip_content
    assert 'title=frozen_fixture["related_pages"][0]["title"]' in skip_content
    with pytest.raises(ValueError, match="vote"):
        generate(source, tmp_path / "bad-vote.py", fixture, expected_fixture_sha256=digest, related_page_vote=[])
    with pytest.raises(ValueError, match="new file"):
        generate(source, output, fixture, expected_fixture_sha256=digest)
    with pytest.raises(ValueError, match="pin"):
        generate(source, tmp_path / "bad.py", fixture, expected_fixture_sha256="0" * 64)
    broken = tmp_path / "owner.py"
    broken.write_text(source.read_text().replace("    world = lane.world.world_id\n", "    world = 'changed'\n"))
    with pytest.raises(ValueError, match="anchor"):
        generate(broken, tmp_path / "bad-owner.py", fixture, expected_fixture_sha256=digest)


def test_related_page_fixture_preflight_rejects_extra_changed_and_duplicate_sources(monkeypatch):
    import copy
    import hashlib
    import pytest
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.fixture_sources import inspect_related_pages

    body = "Two copper pieces."
    pointer = {"world_id": "w", "document_id": "id", "registry_revision": 1, "title": "Ledger"}
    actual = {**pointer, "markdown": body, "content_sha256": hashlib.sha256(body.encode()).hexdigest()}
    fixture = {"related_pages": [{"label": "ledger", "title": "Ledger", "body": body}]}
    request = SimpleNamespace(owner_scope=SimpleNamespace(world_id="w"),
                              primary_work=SimpleNamespace(object_id="primary"))
    monkeypatch.setattr(build_related_pages, "discover", lambda _: [pointer])
    monkeypatch.setattr(build_related_pages, "materialize", lambda _: actual)
    assert inspect_related_pages(request, fixture) == [{"label": "ledger", "title": "Ledger", "world_id": "w", "document_id": "id",
        "registry_revision": 1, "content_sha256": actual["content_sha256"]}]
    changed = copy.deepcopy(fixture)
    changed["related_pages"][0]["body"] = "One copper piece."
    with pytest.raises(ValueError):
        inspect_related_pages(request, changed)
    changed = copy.deepcopy(fixture)
    changed["related_pages"].append(copy.deepcopy(changed["related_pages"][0]))
    with pytest.raises(ValueError):
        inspect_related_pages(request, changed)
    monkeypatch.setattr(build_related_pages, "discover", lambda _: [pointer, {**pointer, "title": "Extra"}])
    with pytest.raises(ValueError):
        inspect_related_pages(request, fixture)
    for changes in ({"world_id": "other"}, {"document_id": "primary"}, {"registry_revision": 0}):
        monkeypatch.setattr(build_related_pages, "discover", lambda _, changes=changes: [{**pointer, **changes}])
        monkeypatch.setattr(build_related_pages, "materialize", lambda _: pytest.fail("foreign page materialized"))
        with pytest.raises(ValueError, match="catalog identity"):
            inspect_related_pages(request, fixture)


def test_capture_preflight_is_outside_product_probe_and_halts_on_mismatch(tmp_path, monkeypatch, verified_capture_owner):
    import json
    import pytest
    from apps.live_control_server.services import build_related_pages
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    case = {"id": "case1", "question": "Use it."}
    fixture = {"request": "Use it.", "history": [], "related_pages": []}
    spec = {"conversation_mode": "build_sequence", "cases": [case]}
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: (spec, tmp_path))
    seen = []
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    monkeypatch.setattr(module, "inspect_related_pages", lambda *a: seen.append("fixture") or [])
    monkeypatch.setattr(build_related_pages, "discover", lambda _: [])
    class Client:
        def post(self, route):
            assert route == "/api/live/agent/turn"
            return build_related_pages.discover(None)
    def ordinary_case(client, world, template, current, directory, **kwargs):
        assert not directory.exists()
        seen.append("turn")
        client.post("/api/live/agent/turn")
        return "done"
    monkeypatch.setattr(workflow, "capture_case", ordinary_case)
    def ordinary_capture(manifest, output, **kwargs):
        return workflow.capture_case(Client(), "w", {"primary_work": {"object_id": "page"}}, case, output)
    monkeypatch.setattr(workflow, "capture", ordinary_capture)
    out = tmp_path / "success"
    fixture_set = {"case1": fixture}
    fixture_pin = module.fixture_sha256(fixture_set)
    assert module.capture(_test_manifest(tmp_path), out, fixtures=fixture_set, expected_manifest_sha256=MANIFEST_PIN,
                          expected_fixture_sha256=fixture_pin) == "done"
    assert seen == ["fixture", "turn", "fixture"]
    probe = json.loads((out / "related-page-probe.json").read_text())
    assert probe["records"] == [{"owner": "related_catalog_discovery", "state": "returned"}]
    sources = json.loads((out / "fixture-sources.json").read_text())
    assert sources["status"] == "stable"
    assert json.loads((out / "fixture-pin.json").read_text())["fixture_set_sha256"] == fixture_pin
    seen.clear()
    def mismatch(*args):
        raise ValueError("wrong synthetic sources")
    monkeypatch.setattr(module, "inspect_related_pages", mismatch)
    with pytest.raises(ValueError, match="wrong synthetic sources"):
        module.capture(_test_manifest(tmp_path), tmp_path / "failure", fixtures=fixture_set,
                       expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=fixture_pin)
    assert seen == []
    assert json.loads((tmp_path / "failure" / "fixture-sources.json").read_text())["status"] == "preflight_failed"


def test_capture_reuses_only_exact_seeded_dialogue(tmp_path, monkeypatch, verified_capture_owner):
    import pytest
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    case = {"id": "seeded", "question": "Use that idea."}
    fixture = {"request": case["question"], "history": [
        {"role": "user", "content": "An idea?"}, {"role": "assistant", "content": "A star."}],
        "related_pages": []}
    history = {"world_id": "w", "conversation_id": "c", "active_conversation_id": "c",
               "next_before_sequence": None, "turns": [{"turn_id": "t", "sequence": 1,
               "lifecycle_status": "completed", "user_text": "An idea?", "assistant_text": "A star."}]}
    class Response:
        status_code = 200
        def json(self):
            return history
    class Client:
        def get(self, route):
            assert route == "/api/live/agent/worlds/w/conversation"
            return Response()
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: (
        {"conversation_mode": "build_sequence", "cases": [case]}, tmp_path))
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    monkeypatch.setattr(module, "inspect_related_pages", lambda *a: [])
    dispatched = []
    def ordinary_case(client, world, template, current, directory, **kwargs):
        client.get("/api/live/agent/worlds/w/conversation")
        dispatched.append(kwargs["expected_conversation_id"])
        return "done"
    monkeypatch.setattr(workflow, "capture_case", ordinary_case)
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, **kwargs: workflow.capture_case(
        Client(), "w", {"primary_work": {"object_id": "page"}}, case, output,
        expected_conversation_id=None))
    fixture_set = {"seeded": fixture}
    fixture_pin = module.fixture_sha256(fixture_set)
    assert module.capture(_test_manifest(tmp_path), tmp_path / "ok", fixtures=fixture_set,
                          expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=fixture_pin) == "done"
    assert dispatched == ["c"]
    history["turns"][0]["assistant_text"] = "Different."
    with pytest.raises(ValueError, match="differs"):
        module.capture(_test_manifest(tmp_path), tmp_path / "bad", fixtures=fixture_set,
                       expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=fixture_pin)
    assert dispatched == ["c"]
    history["turns"][0]["assistant_text"] = "A star."
    calls = []
    def changed_get(self, route):
        calls.append(route)
        if len(calls) == 2:
            history["turns"][0]["assistant_text"] = "Changed after preflight."
        return Response()
    monkeypatch.setattr(Client, "get", changed_get)
    with pytest.raises(ValueError, match="differs"):
        module.capture(_test_manifest(tmp_path), tmp_path / "race", fixtures=fixture_set,
                       expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=fixture_pin)
    assert len(calls) == 2 and dispatched == ["c"]


def test_fixture_source_record_rejects_world_and_content_mismatches():
    import copy
    import hashlib
    import pytest
    from evals.negative_retrieval.fixture_sources import verify_related_record

    body = "Known ledger."
    fixture = {"id": "case1", "related_pages": [{"label": "ledger", "title": "Ledger", "body": body}]}
    request = {"owner_scope": {"world_id": "w"}, "primary_work": {"object_id": "page"}}
    row = {"label": "ledger", "title": "Ledger", "world_id": "w", "document_id": "id", "registry_revision": 1,
           "content_sha256": hashlib.sha256(body.encode()).hexdigest()}
    record = {"schema": "dmb_negative_retrieval_fixture_sources_v1", "case_id": "case1",
              "status": "stable", "before": [row], "after": [copy.deepcopy(row)]}
    assert verify_related_record(request, fixture, record)
    for change in (lambda x: x["after"][0].update(content_sha256="0" * 64),
                   lambda x: x.update(case_id="other"),
                   lambda x: x["before"][0].update(world_id="other")):
        bad = copy.deepcopy(record)
        change(bad)
        with pytest.raises(ValueError):
            verify_related_record(request, fixture, bad)


def test_postflight_failure_is_retained_and_stops_capture(tmp_path, monkeypatch, verified_capture_owner):
    import json
    import pytest
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    case = {"id": "case1", "question": "Use it."}
    fixture = {"request": "Use it.", "history": [], "related_pages": []}
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: ({"conversation_mode": "build_sequence", "cases": [case]}, tmp_path))
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    checks = iter([[], ValueError("source changed")])
    def inspect(*args):
        result = next(checks)
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(module, "inspect_related_pages", inspect)
    monkeypatch.setattr(workflow, "capture_case", lambda *a, **kw: "completed")
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, **kw:
                        workflow.capture_case(None, "w", {"primary_work": {"object_id": "page"}}, case, output))
    with pytest.raises(ValueError, match="source changed"):
        module.capture(_test_manifest(tmp_path), tmp_path / "case", fixtures={"case1": fixture},
                       expected_manifest_sha256=MANIFEST_PIN,
                       expected_fixture_sha256=module.fixture_sha256({"case1": fixture}))
    evidence = json.loads((tmp_path / "case" / "fixture-sources.json").read_text())
    assert evidence["status"] == "postflight_failed" and evidence["before"] == []


def test_preflight_requires_exact_snapshot_and_complete_prior_history():
    import hashlib
    import pytest
    from evals.negative_retrieval.fixture_binding import verify_preflight_snapshot, verify_preflight_history

    page = "# Page"
    digest = hashlib.sha256(page.encode()).hexdigest()
    fixture = {"page": page, "history": [{"role": "user", "content": "Idea?"},
                                          {"role": "assistant", "content": "A star."}]}
    template = {"primary_work": {"object_id": "page", "expected_revision": 1, "expected_content_sha256": digest}}
    snapshot = {"world_id": "w", "document_id": "page", "registry_revision": 1, "draft_markdown": page,
                "content_sha256": digest, "draft_sha256": digest}
    assert verify_preflight_snapshot(fixture, template, "w", snapshot)
    with pytest.raises(ValueError):
        verify_preflight_snapshot({**fixture, "page": "changed"}, template, "w", snapshot)
    history = {"world_id": "w", "conversation_id": "c", "active_conversation_id": "c",
               "next_before_sequence": None, "turns": [{"turn_id": "old", "sequence": 1, "lifecycle_status": "completed",
                                                         "user_text": "Idea?", "assistant_text": "A star."}]}
    assert verify_preflight_history(fixture, history, "w", "c")
    with pytest.raises(ValueError):
        verify_preflight_history(fixture, {**history, "next_before_sequence": 1}, "w", "c")
    with pytest.raises(ValueError):
        verify_preflight_history(fixture, history, "w", "other")


def test_capture_refuses_per_run_clones_before_touching_manifest(tmp_path):
    import pytest
    from evals.negative_retrieval.capture import capture

    with pytest.raises(ValueError, match="per-capture cloning"):
        capture(tmp_path / "missing", tmp_path / "output", clone_app=True)
    assert not (tmp_path / "output").exists()


def test_capture_requires_independently_pinned_manifest_before_dispatch(tmp_path, monkeypatch):
    import pytest
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    manifest = _test_manifest(tmp_path)
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: pytest.fail("unbound manifest reached runner"))
    for digest in (None, "0" * 64, "A" * 64):
        with pytest.raises(ValueError, match="manifest|Manifest"):
            capture(manifest, tmp_path / "out", expected_manifest_sha256=digest)
    assert not (tmp_path / "out").exists()


def test_capture_rejects_changed_or_unpinned_fixture_before_dispatch(tmp_path, monkeypatch):
    import pytest
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    manifest = _test_manifest(tmp_path)
    fixtures = {"case": {"request": "Use that.", "history": [], "page": "# Page", "related_pages": []}}
    pin = module.fixture_sha256(fixtures)
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: pytest.fail("fixture reached runner"))
    for supplied_pin in (None, "0" * 64):
        with pytest.raises(ValueError, match="Fixture set"):
            module.capture(manifest, tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN,
                           fixtures=fixtures, expected_fixture_sha256=supplied_pin)
    fixtures["case"]["page"] = "# Changed"
    with pytest.raises(ValueError, match="Fixture set"):
        module.capture(manifest, tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN,
                       fixtures=fixtures, expected_fixture_sha256=pin)
    assert not (tmp_path / "out").exists()


def test_capture_uses_frozen_fixture_snapshot_if_caller_mutates_input(tmp_path, monkeypatch, verified_capture_owner):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    case = {"id": "case", "question": "Use that."}
    fixtures = {"case": {"request": "Use that.", "history": [], "page": "# Original", "related_pages": []}}
    pin = module.fixture_sha256(fixtures)
    observed = []
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: (
        {"conversation_mode": "build_sequence", "cases": [case]}, tmp_path))
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda fixture, *a: observed.append(fixture["page"]))
    monkeypatch.setattr(module, "inspect_related_pages", lambda *a: [])
    monkeypatch.setattr(workflow, "capture_case", lambda *a, **k: "done")
    def dispatch(manifest, output, **kwargs):
        fixtures["case"]["page"] = "# Changed after pin"
        return workflow.capture_case(None, "w", {"primary_work": {"object_id": "page"}}, case, output)
    monkeypatch.setattr(workflow, "capture", dispatch)
    result = module.capture(_test_manifest(tmp_path), tmp_path / "out", fixtures=fixtures,
                            expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=pin)
    assert result == "done" and observed == ["# Original"]


def test_seeder_rejects_unowned_shapes_before_database_access(monkeypatch):
    import pytest
    from evals.negative_retrieval import seed_dialogue as module

    monkeypatch.setattr(module, "checked_owned_dsn", lambda: pytest.fail("database guard reached"))
    with pytest.raises(ValueError, match="synthetic World"):
        module.seed_dialogue({"history": []}, world="real-world", template={}, snapshot={})
    with pytest.raises(ValueError, match="complete nonblank"):
        module.seed_dialogue({"history": [{"role": "user", "content": "Idea"}]},
            world="negative-seed-" + "a" * 32, template={}, snapshot={})


def test_provisioner_rejects_duplicate_sources_before_database_access(tmp_path, monkeypatch):
    import pytest
    from evals.negative_retrieval import provision_fixture as module

    monkeypatch.setattr(module, "checked_owned_dsn", lambda: pytest.fail("database guard reached"))
    fixture = {"page": "# Page", "related_pages": [
        {"label": "one", "title": "Same", "body": "One."},
        {"label": "two", "title": "Same", "body": "Two."}]}
    with pytest.raises(ValueError, match="unique"):
        module.provision_fixture(fixture, root=tmp_path)


def test_seeder_refuses_forged_saved_page_before_conversation(monkeypatch):
    from hashlib import sha256
    from types import SimpleNamespace
    import pytest
    from apps.live_control_server.services import workspace_document_registry
    from application_state import agent_conversation
    from evals.negative_retrieval import seed_dialogue as module

    world = "negative-seed-" + "a" * 32
    page, digest = "# Fixture", sha256(b"# Fixture").hexdigest()
    fixture = {"page": page, "history": []}
    template = {"primary_work": {"object_id": "page", "expected_revision": 1,
                                  "expected_content_sha256": digest}}
    snapshot = {"world_id": world, "document_id": "page", "registry_revision": 1,
                "draft_markdown": page, "content_sha256": digest, "draft_sha256": digest}
    saved = SimpleNamespace(record=SimpleNamespace(world_id=world, kind="worldbuilding_source",
        status="active", revision=1), loaded_revision=1, markdown="different",
        committed_markdown="different", content_sha256=digest, committed_content_sha256=digest)
    monkeypatch.setattr(module, "checked_owned_dsn", lambda: "verified")
    monkeypatch.setattr(workspace_document_registry, "get_workspace_document_snapshot", lambda *a: saved)
    monkeypatch.setattr(agent_conversation, "AgentConversationService", lambda: pytest.fail("conversation owner reached"))
    with pytest.raises(ValueError, match="Persisted synthetic page"):
        module.seed_dialogue(fixture, world=world, template=template, snapshot=snapshot)


def test_capture_delegates_to_read_only_core_cohort_path(tmp_path, monkeypatch, verified_capture_owner):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    manifest_path = _test_manifest(tmp_path)
    monkeypatch.setattr(workflow, "load_manifest", lambda *args, **kwargs: ({"conversation_mode": "build_sequence"}, tmp_path))
    calls = []
    def underlying(manifest, base, output, **options):
        calls.append(options)
        return "captured"
    monkeypatch.setattr(workflow, "_capture", underlying)
    assert capture(manifest_path, tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN) == "captured"
    assert len(calls) == 1 and calls[0]["cohort_member"] is True
    assert calls[0]["context_only"] is False and calls[0]["writer_transport"] is False


def test_controller_votes_are_projected_as_unvalidated_not_reads():
    import json
    from evals.negative_retrieval.trace_observation import controller_observations, observed_acquisitions

    response = {"answers": {"source_need": {"selected": "anchored"},
                            "related_page_0": {"selected": "read"},
                            "related_page_1": {"selected": "skip"},
                            "requested_work": {"selected": "private untrusted text"}}}
    trace = {"schema": "dmb_turn_context_trace_v1", "observations": [
        {"sequence": 0, "kind": "provider_call", "provider": "example", "model": "model"},
        {"sequence": 1, "kind": "context_snapshot", "snapshot_kind": "provider_response", "stage": "after",
         "materials": [{"item_id": "unvalidated-controller-decision:example", "text": json.dumps(response)}]}]}
    result = controller_observations(trace)
    snapshot = result["controller_snapshots"][0]
    assert snapshot["validation"] == "unvalidated"
    assert snapshot["selections"] == {"source_need": "anchored", "requested_work": "other_or_invalid"}
    assert snapshot["related_page_votes"] == {"read": 1, "skip": 1, "other_or_invalid": 0}
    assert result["providers"] == [{"provider": "example", "model": "model"}]
    assert observed_acquisitions(trace)["observed"] == []
    assert "private untrusted text" not in json.dumps(result)


def test_catalog_budget_is_separate_from_page_reads_and_preserves_unknowns():
    case = {"max_catalog_discoveries": 1, "required_reads": ["ledger"],
            "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    good = observation(outcome="answer", reads=["ledger"], catalog_discoveries=1, required_support=True)
    assert assess(case, good)["status"] == "pass"
    assert assess(case, {**good, "catalog_discoveries": 2})["checks"]["catalog_budget"] is False
    assert assess(case, {**good, "catalog_journal_complete": None})["checks"]["catalog_budget"] is None
    assert assess(case, {**good, "catalog_discoveries": 2, "catalog_journal_complete": False})["status"] == "fail"


def test_source_mapping_uses_verified_inventory_and_exact_trace_item():
    from uuid import uuid4
    from evals.negative_retrieval.fixture_sources import related_trace_labels
    from evals.negative_retrieval.related_page_probe import acquisition_labels
    from evals.negative_retrieval.trace_observation import UNKNOWN

    item = f"Ledger · saved revision 4 · {uuid4()}"
    record = {"before": [{"title": "Ledger", "registry_revision": 4, "label": "ledger", "document_id": "doc"}]}
    trace = {"attempts": [{"observations": [{"kind": "context_decision", "action": "retrieved",
              "policy_version": "selected_exact_related_authored_pages_v1",
              "item_ids": [item, "Ledger · saved revision 4 · invalid", "Unknown"]}]}]}
    assert related_trace_labels(trace, record) == {item: "ledger"}
    records = [{"owner": "related_page_materialization", "state": "returned", "document_id": "doc"},
               {"owner": "related_page_materialization", "state": "raised", "document_id": "other"}]
    assert acquisition_labels(records, label_by_document={"doc": "ledger"}) == ["ledger", UNKNOWN]


def test_probe_records_materialization_identity_without_source_content(monkeypatch):
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners

    monkeypatch.setattr(build_related_pages, "materialize", lambda pointer: {"markdown": "private fixture body"})
    with observe_related_page_owners() as records:
        assert build_related_pages.materialize({"document_id": "doc"})["markdown"] == "private fixture body"
    assert records == [{"owner": "related_page_materialization", "state": "returned", "document_id": "doc"}]
    assert "private fixture body" not in str(records)


def test_http_witness_generator_guards_owner_fixture_and_requires_typed_questions(tmp_path):
    from pathlib import Path
    import pytest
    from evals.negative_retrieval.build_http_witness import generate

    root = Path(__file__).resolve().parents[2]
    source = root / "tests/test_surface_native_build_ordinary.py"
    output = tmp_path / "derived.py"
    generate(source, output)
    result = output.read_text()
    assert result.count("def test_negative_retrieval_ambiguous_placement_http_witness") == 1
    assert 'completion["collaboration"]["kind"] == "questions"' in result
    assert 'response.status_code == 200' in result
    safety = result.index('negative_retrieval_no_proposal_and_unchanged_page: true')
    assert safety < result.index('assert response.status_code == 200', safety)
    assert 'related_page_materialization' in result
    broken = tmp_path / "broken.py"
    broken.write_text(source.read_text().replace('if contextual in {"ambiguous", "missing", "different"}:', 'if contextual == "ambiguous":'))
    with pytest.raises(ValueError):
        generate(broken, output)
    with pytest.raises(ValueError):
        generate(source, source)


def test_owned_http_fixture_rejects_foreign_or_stale_clone_and_worker():
    import copy
    import pytest
    from evals.negative_retrieval.owned_db_fixture import validate_lease, OWNER, DERIVED_TEST

    clone = {"database": "benchmark_run_" + "a" * 32, "host": "127.0.0.1", "port": 33351,
             "oid": "42", "system_identifier": "123"}
    ledger = {"owner": OWNER, "cleanup_complete": False, "stage": "running", "source_sha": "head",
              "pid": 12, "owner_start_ticks": "42", "database": clone, "current_run": "/run/1",
              "runs": [{"process_group": 34, "workers_closed": False, "exit_code": None, "path": "/run/1"}]}
    def validate(value, **kwargs):
        return validate_lease(value, head=kwargs.get("head", "head"),
                              git_status=kwargs.get("git_status", f"?? {DERIVED_TEST}\n"),
                              pgid=kwargs.get("pgid", 34), owner_start_ticks=kwargs.get("ticks", "42"))
    assert validate(ledger) == clone
    for changes in ({"owner": "other"}, {"stage": "awaiting_review"}, {"cleanup_complete": True},
                    {"source_sha": "other"}, {"owner_start_ticks": "stale"}):
        bad = copy.deepcopy(ledger)
        bad.update(changes)
        with pytest.raises(ValueError):
            validate(bad)
    with pytest.raises(ValueError):
        validate(ledger, pgid=35)
    with pytest.raises(ValueError):
        validate(ledger, git_status=" M src/important.py\n")
    bad = copy.deepcopy(ledger)
    bad["database"]["database"] = "operator_database"
    with pytest.raises(ValueError):
        validate(bad)


def test_creative_naming_rubric_requires_proven_no_acquisition_and_quality():
    import json
    from pathlib import Path

    from evals.negative_retrieval.trace_observation import UNKNOWN

    fixtures = Path(__file__).resolve().parents[2] / 'evals/negative_retrieval/fixtures'
    public = json.loads((fixtures / 'development.json').read_text())
    private = json.loads((fixtures / 'development-private.json').read_text())
    case = next(row for row in public['cases'] if row['id'] == 'dev-creative-names')
    rubric = private['cases'][case['id']]
    assert case['history'] == [] and len(case['related_pages']) >= 3
    assert rubric['outcomes'] == ['answer'] and not rubric['allowed_reads']
    clean_graph = {"graph_query_attempts": 0, "graph_query_journal_complete": True}
    assert assess(rubric, observation(outcome='answer', **clean_graph))['status'] == 'pass'
    assert assess(rubric, observation(outcome='answer', graph_query_attempts=1,
                                      graph_query_journal_complete=False))['checks']['graph_query_budget'] is False
    assert assess(rubric, observation(outcome='answer', graph_query_attempts=0,
                                      graph_query_journal_complete=False))['status'] == 'unproven'
    assert assess(rubric, observation(outcome='answer', catalog_discoveries=1))['status'] == 'fail'
    assert assess(rubric, observation(outcome='answer', reads=[UNKNOWN], journal_complete=False))['status'] == 'fail'
    assert assess(rubric, observation(outcome='answer', journal_complete=False))['status'] == 'unproven'
    assert assess(rubric, observation(outcome='answer', semantic_quality=None))['status'] == 'unproven'
    assert assess(rubric, observation(outcome='answer', semantic_quality=False))['status'] == 'fail'
    assert assess(rubric, observation(outcome='answer', catalog_journal_complete=False))['status'] == 'unproven'
    assert assess(rubric, observation(outcome='proposal', movable_proposal=True))['status'] == 'fail'


def test_native_corpus_probe_records_discovery_and_reads_without_input_leak(monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records

    def succeeds(*args, **kwargs):
        return "private result"

    def fails(*args, **kwargs):
        raise ValueError("private failure")

    monkeypatch.setattr(native_corpus_source, "capture_native_sources", succeeds)
    monkeypatch.setattr(native_corpus_source, "read_native_corpus_member", succeeds)
    monkeypatch.setattr(native_corpus_source, "read_direct_native_source", fails)
    with observe_native_graph_owners() as records:
        assert native_corpus_source.capture_native_sources("private query") == "private result"
        assert native_corpus_source.read_native_corpus_member("private body") == "private result"
        with pytest.raises(ValueError, match="private failure"):
            native_corpus_source.read_direct_native_source("private identity")
    assert records == [
        {"owner": "native_corpus_discovery", "state": "returned"},
        {"owner": "native_corpus_member_read", "state": "returned"},
        {"owner": "native_corpus_direct_read", "state": "raised"},
    ]
    assert summarize_records(records)["native_corpus_discovery"]["returned"] == 1
    assert native_corpus_source.capture_native_sources is succeeds
    assert native_corpus_source.read_direct_native_source is fails
    assert "private" not in str(records)


def test_real_corpus_discovery_records_nested_body_open_without_source_data():
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners
    from tests import test_native_corpus_source_access as source_fixture

    lane = source_fixture.lane.__wrapped__()
    source_fixture.admit(lane)
    with observe_native_graph_owners() as records:
        captured = native_corpus_source.capture_native_sources(
            managed_world_id="managed", principal=source_fixture.GM,
            repository=lane.repo, resolve_identity=lambda _: lane.bound,
        )
    assert captured.members and captured.bodies
    assert {row["owner"] for row in records} >= {"native_corpus_discovery", "native_corpus_body_open"}
    assert all(set(row) == {"owner", "state"} for row in records)
    assert source_fixture.BODY not in str(records)


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf"), "123", 10**1000])
def test_response_latency_rejects_invalid_values(value):
    from evals.negative_retrieval.report import response_latency

    with pytest.raises(ValueError, match="Invalid response latency"):
        response_latency({"elapsed_ms": value})
    assert response_latency({}) is None


def test_capture_probe_excludes_setup_and_history_activity(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from apps.live_control_server.services import build_related_pages
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    monkeypatch.setattr(build_related_pages, "discover", lambda _: [])
    class Client:
        def get(self, route):
            build_related_pages.discover(None)
            return route

        def post(self, route, **kwargs):
            if route == "/api/live/agent/turn":
                build_related_pages.discover(None)
            return route

    def case(client, world, template, case, directory, **kwargs):
        client.get("/history-before")
        client.post("/new-conversation")
        client.post("/api/live/agent/turn", json={})
        client.get("/history-after")
        with pytest.raises(ValueError, match="only one turn"):
            client.post("/api/live/agent/turn", json={})
        return "complete"

    monkeypatch.setattr(workflow, "capture_case", case)
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, **kwargs:
                        workflow.capture_case(Client(), "world", {}, {"id": "case1"}, output))
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    result = capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    assert result == "complete"
    evidence = json.loads((tmp_path / "case1" / "related-page-probe.json").read_text())
    assert evidence["status"] == "observed" and evidence["coverage"] == "partial"
    assert evidence["records"] == [{"owner": "related_catalog_discovery", "state": "returned"}]


def test_capture_probe_marks_predispatch_failure_not_started(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    def fail_before_dispatch(*args, **kwargs):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(workflow, "capture_case", fail_before_dispatch)
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, **kwargs:
                        workflow.capture_case(None, "world", {}, {"id": "case1"}, output))
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    with pytest.raises(RuntimeError, match="history unavailable"):
        capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    for name in ("related-page-probe", "native-graph-probe"):
        evidence = json.loads((tmp_path / "case1" / (name + ".json")).read_text())
        assert evidence["status"] == "not_started" and evidence["records"] == []


def test_probe_freezes_rows_before_late_alias_and_background_completion(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from threading import Event, Thread
    from apps.live_control_server.services import build_related_pages
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    entered, release = Event(), Event()
    def discover(_):
        entered.set()
        assert release.wait(5)
        return []
    monkeypatch.setattr(build_related_pages, "discover", discover)
    threads = []
    class Client:
        def post(self, route, **kwargs):
            alias = build_related_pages.discover
            thread = Thread(target=alias, args=(None,))
            threads.append(thread)
            thread.start()
            assert entered.wait(5)
            self.alias = alias
            return "response"
        def get(self, route):
            release.set()
            threads[0].join(timeout=5)
            assert not threads[0].is_alive()
            self.alias(None)  # A retained wrapper called after the turn ended.
            return "history"
    def case(client, world, template, case, directory, **kwargs):
        client.post("/api/live/agent/turn")
        client.get("/history-after")
    monkeypatch.setattr(workflow, "capture_case", case)
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, **kwargs:
                        workflow.capture_case(Client(), "world", {}, {"id": "case1"}, output))
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    evidence = json.loads((tmp_path / "case1" / "related-page-probe.json").read_text())
    assert evidence["records"] == [{"owner": "related_catalog_discovery", "state": "entered"}]


@pytest.mark.parametrize("kind", ["async_method", "awaitable_response"])
def test_capture_rejects_async_post_without_claiming_a_completed_window(tmp_path, monkeypatch, verified_capture_owner, kind):
    import json
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    async def later():
        return "response"
    class AsyncClient:
        async def post(self, route):
            return "response"
    class AwaitableClient:
        def post(self, route):
            return later()
    client = AsyncClient() if kind == "async_method" else AwaitableClient()
    monkeypatch.setattr(workflow, "capture_case", lambda client, *a, **k: client.post("/api/live/agent/turn"))
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, **kwargs:
                        workflow.capture_case(client, "world", {}, {"id": "case1"}, output))
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    with pytest.raises(TypeError, match="unsupported"):
        capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    for name in ("related-page-probe", "native-graph-probe"):
        evidence = json.loads((tmp_path / "case1" / (name + ".json")).read_text())
        assert evidence["status"] == ("not_started" if kind == "async_method" else "dispatch_uncertain")
        assert evidence["records"] == []


def test_probe_window_wraps_real_sync_testclient_turn_post(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.services import build_related_pages
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    monkeypatch.setattr(build_related_pages, "discover", lambda _: [])
    app = FastAPI()

    @app.get("/history")
    def history():
        build_related_pages.discover(None)
        return {"history": []}

    @app.post("/api/live/agent/turn")
    def turn():
        build_related_pages.discover(None)
        return {"status": "completed"}

    def run_case(client, world, template, case, directory, **kwargs):
        assert client.get("/history").status_code == 200
        assert client.post("/api/live/agent/turn", json={}).json() == {"status": "completed"}
        assert client.get("/history").status_code == 200

    monkeypatch.setattr(workflow, "capture_case", run_case)
    def run_capture(manifest, output, **kwargs):
        with TestClient(app) as client:
            return workflow.capture_case(client, "world", {}, {"id": "case1"}, output)
    monkeypatch.setattr(workflow, "capture", run_capture)
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    evidence = json.loads((tmp_path / "case1" / "related-page-probe.json").read_text())
    assert evidence["status"] == "observed"
    assert evidence["records"] == [{"owner": "related_catalog_discovery", "state": "returned"}]


def test_native_activity_counts_separate_stages_without_dedup_or_identity_leak():
    from evals.negative_retrieval.trace_observation import native_activity_counts

    policy = "native_source_document_read_progress_v2"
    trace = {"schema": "dmb_turn_context_trace_v1", "observations": [
        {"sequence": 0, "kind": "context_decision", "policy_version": policy,
         "action": "expanded", "item_ids": ["private-source"]},
        {"sequence": 1, "kind": "context_decision", "policy_version": policy,
         "action": "retrieved", "item_ids": ["private-source"]},
        {"sequence": 2, "kind": "context_decision", "policy_version": policy,
         "action": "expanded", "item_ids": ["private-source"]},
        {"sequence": 3, "kind": "context_decision", "policy_version": policy,
         "action": "retained", "item_ids": ["other-private-source"]},
    ]}
    result = native_activity_counts(trace)
    assert result["counts_by_policy"][policy] == {"expanded": 2, "retrieved": 1, "retained": 1}
    assert result["coverage"] == "partial" and "not paired" in result["limit"]
    assert "private-source" not in str(result)
    trace["observations"][2]["sequence"] = 9
    with pytest.raises(ValueError, match="sequence"):
        native_activity_counts(trace)


@pytest.mark.parametrize("field,value", [
    ("max_graph_query_attempts", -1), ("max_graph_query_attempts", True),
    ("graph_query_attempts", -1), ("graph_query_attempts", True),
    ("graph_query_journal_complete", "yes"),
])
def test_graph_query_budget_rejects_invalid_metadata(field, value):
    rubric = {**CASE, "max_graph_query_attempts": 0}
    seen = observation(graph_query_attempts=0, graph_query_journal_complete=True)
    if field == "max_graph_query_attempts":
        rubric[field] = value
    else:
        seen[field] = value
    with pytest.raises(ValueError, match=field):
        assess(rubric, seen)


def test_negative_rate_includes_graph_query_budget_and_missing_graph_proof():
    from evals.negative_retrieval.assessment import REPORT_SCHEMA, rubric_sha256, summarize

    rubric = {**CASE, "max_graph_query_attempts": 0}
    cases = {"one": rubric}
    common = {"schema": REPORT_SCHEMA, "case_id": "one", "rubric_sha256": rubric_sha256(rubric),
              "fixture_context_verified": True, "capture_environment_verified": True}
    for graph, expected in ((False, (1, 0)), (None, (0, 1)), (True, (0, 0))):
        report = {**common, "checks": {"unexpected_retrieval": True, "catalog_budget": True,
                                       "graph_query_budget": graph}}
        result = summarize(cases, {"one": report})["unnecessary_retrieval"]
        assert (result["failures"], result["unknown"]) == expected
    del report["checks"]["graph_query_budget"]
    assert summarize(cases, {"one": report})["unnecessary_retrieval"]["unknown"] == 1


def test_report_does_not_credit_failed_required_page_materialization(tmp_path):
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid5
    from evals.negative_retrieval.report import report_case

    def envelope(body):
        raw = json.dumps(body).encode()
        return {"http_status": 200, "body": body, "raw_body_hex": raw.hex(),
                "raw_body_sha256": hashlib.sha256(raw).hexdigest()}

    request = {"turn_id": "turn", "client_thread_id": "thread", "message": "What does the ledger say?",
               "owner_scope": {"world_id": "world"}, "surface": {"surface_id": "build", "instance_id": "page"},
               "primary_work": {"object_id": "primary"}}
    turn = {"turn_id": "saved", "idempotency_key": str(uuid5(NAMESPACE_URL, "dmb-agent-turn:world:turn")),
            "user_text": request["message"], "lifecycle_status": "completed", "provenance": {
                "world_id": "world", "surface_id": "build", "surface_instance_id": "page"},
            "knowledge_context": {}}
    history = {"world_id": "world", "conversation_id": "conversation", "turns": [turn]}
    attempt = {"schema": "dmb_turn_context_trace_v1", "world_id": "world", "conversation_id": "conversation",
               "turn_id": "saved", "terminal_status": "completed", "capture_status": "complete", "observations": []}
    trace = {"world_id": "world", "turn_id": "saved", "attempts": [attempt]}
    fixture = {"id": "case1", "request": request["message"],
               "related_pages": [{"label": "ledger", "title": "Ledger", "body": "Two copper."}]}
    inventory = [{"label": "ledger", "title": "Ledger", "world_id": "world", "document_id": "doc",
                  "registry_revision": 1, "content_sha256": hashlib.sha256(b"Two copper.").hexdigest()}]
    sources = {"schema": "dmb_negative_retrieval_fixture_sources_v1", "case_id": "case1",
               "status": "stable", "before": inventory, "after": inventory}
    related = {"schema": "dmb_negative_retrieval_related_page_probe_v1", "coverage": "partial", "case_id": "case1",
               "status": "observed", "window": "turn_post_v1", "records": []}
    native = {"schema": "dmb_negative_retrieval_native_graph_probe_v1", "coverage": "partial", "case_id": "case1",
              "status": "observed", "window": "turn_post_v1", "records": []}
    artifacts = {"request": request, "history-after": envelope(history), "context-trace": envelope(trace),
                 "answer-http": envelope({"turn_id": "turn", "client_thread_id": "thread"}),
                 "related-page-probe": related, "native-graph-probe": native, "fixture-sources": sources}
    for name, value in artifacts.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    positive = {"max_catalog_discoveries": 1, "required_reads": ["ledger"],
                "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    for state, expected in (("raised", None), ("entered", None), ("returned", True)):
        related["records"] = [{"owner": "related_page_materialization", "state": state, "document_id": "doc"}]
        (tmp_path / "related-page-probe.json").write_text(json.dumps(related))
        result = report_case(tmp_path, fixture, positive)
        assert result["related_context_verified"] is True
        assert result["checks"]["required_evidence"] is expected
        assert result["status"] == "unproven"
        negative = report_case(tmp_path, fixture, CASE)
        assert negative["checks"]["unexpected_retrieval"] is False


def test_assessor_distinguishes_attempts_from_completed_required_reads():
    positive = {"max_catalog_discoveries": 1, "required_reads": ["ledger"],
                "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    partial = observation(outcome="answer", reads=["ledger"], completed_reads=[], journal_complete=False)
    assert assess(positive, partial)["checks"]["required_evidence"] is None
    assert assess(positive, {**partial, "journal_complete": True})["checks"]["required_evidence"] is False
    assert assess(positive, {**partial, "completed_reads": ["ledger"]})["checks"]["required_evidence"] is True
    with pytest.raises(ValueError, match="completed_reads"):
        assess(positive, {**partial, "completed_reads": "ledger"})


@pytest.mark.parametrize("choice", ["read", "skip"])
def test_pending_page_probe_witnesses_admitted_app_acquisition(monkeypatch, choice):
    """Pending App navigation imports the two watched owners after the hook is installed."""
    import asyncio
    from hashlib import sha256
    from importlib.util import find_spec
    import json
    if find_spec("apps.live_control_server.services.build_pending_app_pages") is None:
        pytest.skip("Pending Build is absent from this source lineage")
    from tests.test_build_source_free_protocol import pending_app_runtime_case
    from apps.live_control_server.services import build_jev_dispatch, build_related_pages
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_related_pages import RelatedPageRead
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners
    import httpx2

    # The serving test helper's synthetic policy predates the namespaced model.
    # This affects only the fake SDK transport and does not establish product routing.
    monkeypatch.setattr(build_jev_dispatch, "MODEL", "jev-1.14.0")
    monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "synthetic-only")

    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            return httpx2.Response(200, request=request, json={"model": body["model"],
                "usage": {"input_tokens": 23, "output_tokens": 4}, "answers": {
                    key: {"type": "choice", "choice": choice, "confidence": 1,
                          "probabilities": {"read": float(choice == "read"),
                                            "skip": float(choice == "skip")}}
                    for key in body["questions"]}})

    with pending_app_runtime_case(monkeypatch) as (state, adapter):
        page = state.turn.graph_context_execution.events[-1].pages[0]
        execution = state.turn.graph_context_execution
        execution = type(execution).model_validate_json(execution.model_copy(update={
            "events": execution.events[:-1]}).model_dump_json(by_alias=True))
        state.turn = t.Turn.model_validate(state.turn.model_copy(update={"graph_context_execution": execution}))
        adapter.fence.renewer.update_turn(state.turn)
        monkeypatch.setattr(build_related_pages, "discover", lambda request: [page.model_dump(mode="json")])

        def materialize(pointer):
            assert pointer == page
            text = "Synthetic saved page."
            return dict(pointer.model_dump(mode="json"), content_sha256=sha256(text.encode()).hexdigest(), markdown=text)

        monkeypatch.setattr(build_related_pages, "materialize", materialize)
        harness = BuildJevHarness(decision_transport=Transport())
        harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
        with observe_related_page_owners() as records:
            asyncio.run(acquire_pending_app_pages(adapter, harness))
        assert sum(row["owner"] == "related_catalog_discovery" for row in records) == 1
        assert sum(row["owner"] == "related_page_materialization" for row in records) == (choice == "read")
        assert len([event for event in state.turn.graph_context_execution.events
                    if type(event) is RelatedPageRead]) == (choice == "read")
        assert all(row["state"] == "returned" for row in records)


def test_pending_fixture_binding_uses_real_receipt_and_conversation_pointer():
    """Current serving's typed pending receipt must match page, World and chat."""
    from importlib.util import find_spec
    if find_spec('application_state.agent_conversation.build_source_free') is None:
        pytest.skip('Pending Build is absent from this source lineage')
    import copy
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid4, uuid5
    from apps.live_control_server.models.agent_turn import AgentBuildPendingContextResponseV1
    from application_state.agent_conversation.types import canonical_sha256
    from tests.test_build_source_free_protocol import pending_submission
    from tests.test_build_source_free_routing import seal_pending_receipt
    from tests.test_surface_native_context import provenance_for
    from evals.negative_retrieval.fixture_binding import verify_fixture

    def envelope(body):
        raw = json.dumps(body).encode()
        return {'http_status': 200, 'body': body, 'raw_body_hex': raw.hex(),
                'raw_body_sha256': hashlib.sha256(raw).hexdigest()}

    submission = pending_submission()
    original = submission.graph_context_receipt
    text = '# Synthetic page\nA fictional detail.'
    digest = hashlib.sha256(text.encode()).hexdigest()
    basis = original.work_context.source_basis.model_copy(update={'content_sha256': digest})
    work = original.work_context.model_copy(update={'source_basis': basis})
    provenance = provenance_for(work).model_copy(update={'surface_instance_id': basis.document_id})
    values = original.model_dump(mode='json', by_alias=True)
    values.pop('context_receipt_sha256')
    values['work_context'] = work.model_dump(mode='json', by_alias=True)
    values['provenance_sha256'] = canonical_sha256(provenance)
    receipt = seal_pending_receipt(values)
    context = AgentBuildPendingContextResponseV1(receipt=receipt, completion=None,
        execution=None, delivery_replay=False).model_dump(mode='json', by_alias=True)
    world, conversation = basis.world_id, str(receipt.conversation_observation.conversation_id)
    pointer = receipt.conversation_observation.pointer_revision
    snap = {'world_id': world, 'document_id': basis.document_id, 'registry_revision': basis.registry_revision,
            'visibility': basis.visibility, 'content_sha256': digest, 'draft_sha256': digest, 'draft_markdown': text}
    request = {'turn_id': str(uuid4()), 'message': 'Use the idea.', 'owner_scope': {'world_id': world},
               'surface': {'surface_id': 'build', 'instance_id': basis.document_id},
               'primary_work': {'object_id': basis.document_id, 'expected_revision': basis.registry_revision,
                                'expected_content_sha256': digest},
               'build_draft_context': {'conversation_id': conversation, 'expected_pointer_revision': pointer,
                                       'snapshot': snap}}
    fixture = {'page': text, 'history': [], 'request': request['message']}
    prior = {'world_id': world, 'conversation_id': conversation, 'active_conversation_id': conversation,
             'pointer_revision': pointer, 'next_before_sequence': None, 'turns': []}
    turn = {'turn_id': str(uuid4()), 'sequence': 1,
            'idempotency_key': str(uuid5(NAMESPACE_URL, f"dmb-agent-turn:{world}:{request['turn_id']}")),
            'user_text': request['message'], 'lifecycle_status': 'completed',
            'provenance': provenance.model_dump(mode='json', by_alias=True), 'knowledge_context': context}
    after = {**prior, 'turns': [turn]}
    assert verify_fixture(fixture, request, envelope(prior), envelope(after)) is True

    wrong = copy.deepcopy(values)
    wrong['conversation_observation']['pointer_revision'] = pointer + 1
    wrong_context = context | {'receipt': seal_pending_receipt(wrong).model_dump(mode='json', by_alias=True)}
    with pytest.raises(ValueError, match='conversation pointer'):
        verify_fixture(fixture, request, envelope(prior), envelope({**after, 'turns': [turn | {'knowledge_context': wrong_context}]}))
    wrong_chat = copy.deepcopy(values)
    wrong_chat['conversation_observation']['conversation_id'] = str(uuid4())
    wrong_chat_context = context | {'receipt': seal_pending_receipt(wrong_chat).model_dump(mode='json', by_alias=True)}
    with pytest.raises(ValueError, match='conversation pointer'):
        verify_fixture(fixture, request, envelope(prior), envelope({**after, 'turns': [turn | {'knowledge_context': wrong_chat_context}]}))
    wrong_work = work.model_copy(update={'source_basis': basis.model_copy(update={'content_sha256': '0' * 64})})
    wrong_provenance = provenance_for(wrong_work).model_copy(update={'surface_instance_id': basis.document_id})
    wrong_page = copy.deepcopy(values)
    wrong_page['work_context'] = wrong_work.model_dump(mode='json', by_alias=True)
    wrong_page['provenance_sha256'] = canonical_sha256(wrong_provenance)
    wrong_page_context = context | {'receipt': seal_pending_receipt(wrong_page).model_dump(mode='json', by_alias=True)}
    wrong_turn = turn | {'knowledge_context': wrong_page_context,
                         'provenance': wrong_provenance.model_dump(mode='json', by_alias=True)}
    with pytest.raises(ValueError, match='source receipt'):
        verify_fixture(fixture, request, envelope(prior), envelope({**after, 'turns': [wrong_turn]}))
    damaged = copy.deepcopy(context)
    damaged['receipt']['work_context']['source_basis']['content_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        verify_fixture(fixture, request, envelope(prior), envelope({**after, 'turns': [turn | {'knowledge_context': damaged}]}))
    with pytest.raises(ValueError, match='Unsupported'):
        verify_fixture(fixture, request, envelope(prior), envelope({**after, 'turns': [turn | {'knowledge_context': {'schema': 'other'}}]}))


def test_capture_rejects_unowned_app_before_runner_and_output(tmp_path, monkeypatch):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    calls = []
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    monkeypatch.setattr(workflow, "capture", lambda *a, **k: calls.append("runner"))
    def denied():
        calls.append("owner")
        raise ValueError("clone is not owned")
    monkeypatch.setattr(module, "checked_owned_dsn", denied)
    output = tmp_path / "not-created"
    with pytest.raises(ValueError, match="clone is not owned"):
        module.capture(_test_manifest(tmp_path), output, expected_manifest_sha256=MANIFEST_PIN)
    assert calls == ["owner"] and not output.exists()


def test_capture_checks_owned_app_before_delegating(tmp_path, monkeypatch):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    calls = []
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    monkeypatch.setattr(module, "checked_owned_dsn", lambda: calls.append("owner"))
    monkeypatch.setattr(workflow, "capture", lambda *a, **k: calls.append("runner") or "ok")
    assert module.capture(_test_manifest(tmp_path), tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN) == "ok"
    assert calls == ["owner", "runner"]
