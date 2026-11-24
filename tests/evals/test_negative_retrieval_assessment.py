from evals.negative_retrieval.assessment import assess


def observation(**overrides):
    return dict({"reads": [], "journal_complete": True, "outcome": "clarification",
                 "completed_turn": True, "no_premature_mutation": True,
                 "semantic_quality": True, "inline_questions": True,
                 "saved_and_reopened": True, "answer_continued": True}, **overrides)


CASE = {"required_reads": [], "allowed_reads": [], "outcomes": ["clarification", "proposal"]}


def test_clarification_requires_full_delivery_and_continuation():
    assert assess(CASE, observation())["status"] == "pass"
    for field in ("inline_questions", "saved_and_reopened", "answer_continued"):
        assert assess(CASE, observation(**{field: False}))["status"] == "fail"
        assert assess(CASE, observation(**{field: None}))["status"] == "unproven"


def test_unwanted_reads_and_incomplete_journals():
    assert assess(CASE, observation(reads=["unrelated"]))["status"] == "fail"
    assert assess(CASE, observation(journal_complete=False))["status"] == "unproven"
    assert assess(CASE, observation(reads=["unrelated"], journal_complete=False))["status"] == "fail"


def test_positive_control_requires_evidence_not_merely_activity():
    case = {"required_reads": ["archive"], "allowed_reads": ["archive"], "outcomes": ["answer"]}
    assert assess(case, observation(outcome="answer"))["missing_reads"] == ["archive"]
    assert assess(case, observation(outcome="answer", reads=["archive"], required_support=True))["status"] == "pass"
    assert assess(case, observation(outcome="answer", reads=["archive"]))["status"] == "unproven"


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


def test_rates_bound_unknown_evidence_without_hiding_observed_failures():
    from evals.negative_retrieval.assessment import summarize

    positive = {"required_reads": ["archive"], "allowed_reads": ["archive"], "outcomes": ["answer"]}
    cases = {"n1": CASE, "n2": CASE, "p1": positive}
    results = {"n1": assess(CASE, observation(reads=["other"], journal_complete=False)),
               "n2": assess(CASE, observation(reads=[], journal_complete=False)),
               "p1": assess(positive, observation(outcome="answer", journal_complete=False))}
    rates = summarize(cases, results)
    assert rates["unnecessary_retrieval"] == {"cases": 2, "failures": 1, "unknown": 1,
                                                "minimum_rate": .5, "maximum_rate": 1.0}
    assert rates["missed_required_reads"]["unknown"] == 1
    assert rates["missed_required_reads"]["maximum_rate"] == 1.0


def test_unmapped_acquisition_fails_zero_budget_but_is_unknown_for_positive_control():
    from evals.negative_retrieval.trace_observation import UNKNOWN

    positive = {"required_reads": ["ledger"], "allowed_reads": ["ledger"], "outcomes": ["answer"]}
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
            "knowledge_context": {"completion": {"collaboration": {"kind": "questions", "questions": [{"text": "Which one?"}]}}}}
    history = {"world_id": "world", "conversation_id": "conversation", "turns": [turn]}
    attempt = {"schema": "dmb_turn_context_trace_v1", "world_id": "world", "conversation_id": "conversation",
               "turn_id": "saved-turn", "terminal_status": "completed", "capture_status": "complete", "observations": []}
    trace = {"world_id": "world", "turn_id": "saved-turn", "attempts": [attempt]}
    answer = {"turn_id": "client-turn", "client_thread_id": "client-thread"}
    result = observe(request, envelope(history), envelope(trace), envelope(answer))
    assert result["outcome"] == "clarification" and result["completed_turn"]
    assert result["journal_complete"] is None
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
        assess({"required_reads": [], "allowed_reads": [UNKNOWN], "outcomes": ["answer"]}, observation())
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


def test_empty_catalog_discovery_is_not_a_zero_acquisition_pass():
    from evals.negative_retrieval.related_page_probe import acquisition_labels

    evidence = [{"owner": "related_catalog_discovery", "state": "returned"}]
    result = assess(CASE, observation(reads=acquisition_labels(evidence), journal_complete=False))
    assert result["checks"]["unexpected_retrieval"] is False
    assert result["status"] == "fail"
