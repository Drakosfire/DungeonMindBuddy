from evals.negative_retrieval.assessment import assess
from hashlib import sha256
import struct
from uuid import UUID

from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied, _REVISION_SQL

import pytest

MANIFEST_PIN = sha256(b"{}").hexdigest()


@pytest.fixture
def verified_capture_owner(monkeypatch):
    """Simulated owner for tests that never contact a real database."""
    from evals.negative_retrieval import capture as module
    monkeypatch.setattr(module, "checked_owned_dsn", lambda: "synthetic-owned-clone")
    monkeypatch.setattr(module, "inspect_primary_page", lambda *_: {"synthetic": True})
    monkeypatch.setattr(module, "expected_primary_page", lambda *_: {"synthetic": True})


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


def test_page_probe_records_pointer_on_return_and_failure(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners

    pointer = SimpleNamespace(world_id='world', document_id='page', registry_revision=3)
    def materialize(value):
        assert records[-1]['state'] == 'entered'
        if isinstance(value, dict):
            raise ValueError('unavailable')
        return 'ok'
    monkeypatch.setattr(build_related_pages, 'materialize', materialize)
    with observe_related_page_owners() as records:
        assert build_related_pages.materialize(pointer) == 'ok'
        with pytest.raises(ValueError, match='unavailable'):
            build_related_pages.materialize({'world_id': 'other', 'document_id': 'page', 'registry_revision': 4})
    assert records == [
        {'owner': 'related_page_materialization', 'state': 'returned', 'world_id': 'world',
         'document_id': 'page', 'registry_revision': 3},
        {'owner': 'related_page_materialization', 'state': 'raised', 'world_id': 'other',
         'document_id': 'page', 'registry_revision': 4},
    ]



def test_page_probe_hashes_returned_body_without_retaining_text(monkeypatch):
    import hashlib
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners
    pointer = {"world_id": "w", "document_id": "d", "registry_revision": 1}
    body = "Synthetic private body."
    digest = hashlib.sha256(body.encode()).hexdigest()
    monkeypatch.setattr(build_related_pages, "materialize", lambda p: {**p, "markdown": body, "content_sha256": digest})
    with observe_related_page_owners() as records:
        assert build_related_pages.materialize(pointer)["markdown"] == body
    assert records[0]["returned_content_sha256"] == digest
    assert records[0]["returned_world_id"] == "w" and records[0]["returned_document_id"] == "d"
    assert records[0]["returned_registry_revision"] == 1 and body not in repr(records)
    monkeypatch.setattr(build_related_pages, "materialize", lambda p: {**p, "markdown": body, "content_sha256": "0" * 64})
    with observe_related_page_owners() as records:
        assert build_related_pages.materialize(pointer)["markdown"] == body
    assert "returned_content_sha256" not in records[0]


def test_page_probe_distinguishes_direct_metadata_from_catalog_and_body(monkeypatch):
    from types import SimpleNamespace
    from evals.negative_retrieval import related_page_probe as probe

    def lookup(value):
        assert records[-1] == {'owner': 'current_page_metadata', 'state': 'entered'}
        if value == 'bad':
            raise ValueError('unavailable')
        return []
    pending = SimpleNamespace(_lookup_current_saved_page=lookup)
    monkeypatch.setattr(probe, 'import_module', lambda name: pending)
    with probe.observe_related_page_owners() as records:
        assert pending._lookup_current_saved_page('ok') == []
        with pytest.raises(ValueError, match='unavailable'):
            pending._lookup_current_saved_page('bad')
    assert pending._lookup_current_saved_page is lookup
    assert records == [{'owner': 'current_page_metadata', 'state': 'returned'},
                       {'owner': 'current_page_metadata', 'state': 'raised'}]
    assert probe.acquisition_labels(records) == []
    assert probe.catalog_discovery_count(records) == 0


def test_page_probe_does_not_hide_missing_runtime_dependency(monkeypatch):
    from evals.negative_retrieval import related_page_probe as probe
    def broken_import(name):
        raise ModuleNotFoundError('dependency missing', name='some_dependency')
    monkeypatch.setattr(probe, 'import_module', broken_import)
    with pytest.raises(ModuleNotFoundError, match='dependency missing'):
        with probe.observe_related_page_owners():
            pass


@pytest.mark.parametrize(('world', 'revision', 'expected'), [
    ('world', 1, 'current-page'), ('other', 1, '<unmapped-acquisition>'),
    ('world', 2, '<unmapped-acquisition>'), ('world', True, '<unmapped-acquisition>'),
    (None, 1, '<unmapped-acquisition>'), ('world', None, '<unmapped-acquisition>'),
])
def test_page_attempt_label_requires_exact_pointer(world, revision, expected):
    from evals.negative_retrieval.related_page_probe import acquisition_labels
    row = {'owner': 'related_page_materialization', 'state': 'returned', 'document_id': 'page'}
    if world is not None:
        row['world_id'] = world
    if revision is not None:
        row['registry_revision'] = revision
    primary = {'world_id': 'world', 'document_id': 'page', 'registry_revision': 1}
    assert acquisition_labels([row], primary_pointer=primary) == [expected]
    assert acquisition_labels([row]) == ['<unmapped-acquisition>']


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
    assert summarize_records(records)["native_source_preparation"] is None
    assert summarize_records(records)["native_graph_binding"] is None
    assert summarize_records(records)["app_source_body_read"] is None
    for malformed in ([{"owner": "native_graph_query", "state": []}],
                      [{"owner": "native_graph_query", "state": "returned", "text": "private"}],
                      [{"owner": "unknown", "state": "returned"}]):
        with pytest.raises(ValueError, match="Malformed"):
            summarize_records(malformed)


def test_native_graph_body_aliases_observe_attempts_without_payload(monkeypatch):
    from apps.live_control_server.services import native_graph_reads
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records

    sentinel = object()
    def single(*args, **kwargs):
        return sentinel
    def batch(*args, **kwargs):
        ids = args[1] if len(args) > 1 else kwargs.get("evidence_ref_ids")
        if not ids:
            return sentinel
        raise ValueError("private failure")
    monkeypatch.setattr(native_graph_reads, "open_admitted_native_text", single)
    monkeypatch.setattr(native_graph_reads, "open_admitted_native_text_batch", batch)
    with observe_native_graph_owners() as records:
        assert native_graph_reads.open_admitted_native_text_batch("private", ()) is sentinel
        assert native_graph_reads.open_admitted_native_text_batch("private", evidence_ref_ids=[]) is sentinel
        assert records == []
        assert native_graph_reads.open_admitted_native_text("private", "source") is sentinel
        with pytest.raises(ValueError):
            native_graph_reads.open_admitted_native_text_batch("private", ("source",))
    assert records == [{"owner": "native_graph_body_open", "state": "returned"},
                       {"owner": "native_graph_body_open_batch", "state": "raised"}]
    assert summarize_records(records)["native_graph_body_open_batch"]["raised"] == 1
    assert native_graph_reads.open_admitted_native_text is single
    assert native_graph_reads.open_admitted_native_text_batch is batch
    assert summarize_records([])["native_graph_body_open"] is None
    assert summarize_records([])["native_graph_body_open_batch"] is None


def test_app_catalog_source_body_probe_records_attempts_without_payload(monkeypatch):
    from application_state.agent_conversation import native_source_catalog
    from application_state.source import repository
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records

    sentinel = object()
    def read(*args, **kwargs):
        if kwargs.get("fail"):
            raise ValueError("private failure")
        return sentinel
    monkeypatch.setattr(repository, "get_source_markdown", read)
    with observe_native_graph_owners() as records:
        assert native_source_catalog.sources.get_source_markdown("private") is sentinel
        with pytest.raises(ValueError):
            native_source_catalog.sources.get_source_markdown("private", fail=True)
    assert records == [{"owner": "app_source_body_read", "state": "returned"},
                       {"owner": "app_source_body_read", "state": "raised"}]
    assert summarize_records(records)["app_source_body_read"]["raised"] == 1
    assert repository.get_source_markdown is read


def test_pending_build_preparation_and_binding_are_separate_observed_owners(monkeypatch):
    from apps.live_control_server.services import native_graph_reads, plan_source_turn
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records

    def prepare(*args, **kwargs):
        return "prepared"
    def binding(*args, **kwargs):
        raise ValueError("synthetic failure")
    monkeypatch.setattr(plan_source_turn, "prepare", prepare)
    monkeypatch.setattr(native_graph_reads, "pending_build_query", binding)
    # A callback captured before instrumentation is an acknowledged blind spot.
    already_bound = plan_source_turn.prepare
    with observe_native_graph_owners() as records:
        assert already_bound("private") == "prepared"
        # The production Build route imports these owners while handling a turn.
        from apps.live_control_server.services.plan_source_turn import prepare as captured_during_turn
        from apps.live_control_server.services.native_graph_reads import pending_build_query
        assert captured_during_turn("private") == "prepared"
        with pytest.raises(ValueError, match="synthetic failure"):
            pending_build_query("private")
    assert records == [{"owner": "native_source_preparation", "state": "returned"},
                       {"owner": "native_graph_binding", "state": "raised"}]
    counts = summarize_records(records)
    assert counts["native_source_preparation"]["returned"] == 1
    assert counts["native_graph_binding"]["raised"] == 1
    assert counts["native_corpus_discovery"]["returned"] == 0
    assert plan_source_turn.prepare is prepare
    assert native_graph_reads.pending_build_query is binding


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
    def ordinary_capture(manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs):
        assert clone_app is False and len(cohort_manifest_sha256) == 64
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


def test_semantic_review_requires_frozen_exact_evidence_and_never_certifies_independence(tmp_path):
    import copy
    import json
    from evals.negative_retrieval.assessment import rubric_sha256
    from evals.negative_retrieval.report import read_semantic_review
    artifacts = {name: sha256(name.encode()).hexdigest() for name in (
        "request", "answer-http", "history-before", "history-after", "context-trace", "fixture-sources", "fixture-pin")}
    rubric = {"max_catalog_discoveries": 1, "required_reads": ["ledger"], "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    review = {"schema": "dmb_negative_retrieval_semantic_review_v1", "case_id": "case1", "rubric_sha256": rubric_sha256(rubric),
        "fixture_set_sha256": "f" * 64, "reviewer": "independent reviewer asserted", "artifacts": artifacts,
        "judgments": {"semantic_quality": {"value": True, "rationale": "The answer addresses the question."},
                      "required_support": {"value": False, "rationale": "The cited passage does not support the toll."}}}
    path = tmp_path / "review.json"
    def check(value, *, expected=None, hashes=artifacts):
        raw = json.dumps(value).encode()
        path.write_bytes(raw)
        return read_semantic_review(path, expected or sha256(raw).hexdigest(), case_id="case1", rubric=rubric,
                                    fixture_sha256="f" * 64, artifact_hashes=hashes)
    result = check(review)
    duplicate = json.dumps(review).replace('"case_id": "case1"', '"case_id": "case1", "case_id": "case1"')
    path.write_text(duplicate)
    with pytest.raises(ValueError, match="duplicate keys"):
        read_semantic_review(path, sha256(path.read_bytes()).hexdigest(), case_id="case1", rubric=rubric,
                             fixture_sha256="f" * 64, artifact_hashes=artifacts)
    assert result["independence"] == "unverified"
    assert result["judgments"] == {"semantic_quality": True, "required_support": False}
    with pytest.raises(ValueError, match="frozen digest"):
        check(review, expected="0" * 64)
    with pytest.raises(ValueError, match="captured artifacts"):
        check(review, hashes=artifacts | {"answer-http": "0" * 64})
    with pytest.raises(ValueError, match="captured artifacts"):
        check(review, hashes=artifacts | {"fresh-history": "1" * 64})
    for mutation in (lambda x: x.update(case_id="other"),
                     lambda x: x.update(rubric_sha256="0" * 64),
                     lambda x: x["artifacts"].pop("history-before"),
                     lambda x: x["judgments"].update(semantic_quality={"value": True, "rationale": " "}),
                     lambda x: x["judgments"].update(required_support=True),
                     lambda x: x.update(extra="unreviewed")):
        altered = copy.deepcopy(review)
        mutation(altered)
        with pytest.raises(ValueError): check(altered)
    no_required = {**rubric, "required_reads": [], "allowed_reads": []}
    invalid = copy.deepcopy(review)
    invalid["rubric_sha256"] = rubric_sha256(no_required)
    path.write_text(json.dumps(invalid))
    with pytest.raises(ValueError, match="source-required"):
        read_semantic_review(path, sha256(path.read_bytes()).hexdigest(), case_id="case1", rubric=no_required,
                             fixture_sha256="f" * 64, artifact_hashes=artifacts)


def test_offline_report_binds_semantic_review_but_keeps_partial_capture_unproven(tmp_path, monkeypatch):
    import json
    from evals.negative_retrieval import report as module, fixture_binding, fixture_sources
    from evals.negative_retrieval.assessment import rubric_sha256
    fixture = {"id": "case1", "request": "What is the toll?"}
    rubric = {"max_catalog_discoveries": 1, "required_reads": ["ledger"], "allowed_reads": ["ledger"], "outcomes": ["answer"]}
    probe = {"schema": "dmb_negative_retrieval_related_page_probe_v1", "coverage": "partial", "case_id": "case1",
             "status": "observed", "window": "turn_post_v1", "records": []}
    data = {"request": {"message": fixture["request"]}, "answer-http": {"body": {}, "http_status": 200},
            "history-before": {}, "history-after": {}, "context-trace": {"body": {}},
            "related-page-probe": probe, "fixture-sources": {"before": []}, "fixture-pin": {}}
    for name, value in data.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    monkeypatch.setattr(module, "verify_fixture_pin", lambda *a: True)
    monkeypatch.setattr(fixture_sources, "verify_related_record", lambda *a: True)
    monkeypatch.setattr(fixture_sources, "related_trace_labels", lambda *a: {})
    monkeypatch.setattr(fixture_binding, "verify_fixture", lambda *a: True)
    monkeypatch.setattr(module, "observe", lambda *a, **k: {"reads": [], "observed_acquisitions": [],
        "outcome": "answer", "completed_turn": True, "native_activity": {"counts_by_policy": {}},
        "http_status": 200, "terminal_status": "completed", "trace_capture_status": "complete", "decision_observations": {}})
    hashes = {name: sha256((tmp_path / f"{name}.json").read_bytes()).hexdigest() for name in data}
    review = {"schema": "dmb_negative_retrieval_semantic_review_v1", "case_id": "case1", "rubric_sha256": rubric_sha256(rubric),
        "fixture_set_sha256": "f" * 64, "reviewer": "reviewer", "artifacts": hashes,
        "judgments": {"semantic_quality": {"value": True, "rationale": "Answers the question."},
                      "required_support": {"value": False, "rationale": "Claim is unsupported."}}}
    path = tmp_path / "review.json"
    raw = json.dumps(review).encode(); path.write_bytes(raw)
    result = module.report_case(tmp_path, fixture, rubric, expected_fixture_sha256="f" * 64, fixture_set={"case1": fixture},
                                review_path=path, expected_review_sha256=sha256(raw).hexdigest())
    assert result["semantic_review"]["independence"] == "unverified"
    # The same bytes must be used for both hashing and parsing.
    with monkeypatch.context() as single_read:
        from pathlib import Path
        def no_text_read(*args, **kwargs): raise AssertionError("artifact read twice through text API")
        single_read.setattr(Path, "read_text", no_text_read)
        again = module.report_case(tmp_path, fixture, rubric, expected_fixture_sha256="f" * 64, fixture_set={"case1": fixture},
                                   review_path=path, expected_review_sha256=sha256(raw).hexdigest())
        assert again["semantic_review"] == result["semantic_review"]
    assert result["checks"]["semantic_quality"] is True and result["checks"]["required_support"] is False
    assert result["status"] == "unproven" and result["capture_environment_verified"] is None
    with pytest.raises(ValueError, match="path and frozen digest"):
        module.report_case(tmp_path, fixture, rubric, review_path=path)
    with monkeypatch.context() as invalid:
        def unbound(*args): raise ValueError("invalid fixture pin")
        invalid.setattr(module, "verify_fixture_pin", unbound)
        with pytest.raises(ValueError, match="verified fixture binding"):
            module.report_case(tmp_path, fixture, rubric, expected_fixture_sha256="f" * 64, fixture_set={"case1": fixture},
                               review_path=path, expected_review_sha256=sha256(raw).hexdigest())
    (tmp_path / "answer-http.json").write_text(json.dumps({"body": {"changed": True}, "http_status": 200}))
    with pytest.raises(ValueError, match="captured artifacts"):
        module.report_case(tmp_path, fixture, rubric, expected_fixture_sha256="f" * 64, fixture_set={"case1": fixture},
                           review_path=path, expected_review_sha256=sha256(raw).hexdigest())


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
        "status": "observed", "records": [{"owner": "native_graph_query", "state": "raised"},
            {"owner": "native_source_preparation", "state": "returned"},
            {"owner": "native_graph_binding", "state": "raised"}]}))
    report = report_case(tmp_path, fixture, CASE)
    assert report["case_id"] == "case1" and report["rubric_sha256"] == rubric_sha256(CASE)
    assert report["status"] == "unproven" and "answer-http" in report["missing_artifacts"]
    assert report["partial_native_graph_probe"]["counts"]["native_graph_query"]["raised"] == 1
    assert report["partial_native_graph_probe"]["counts"]["native_source_preparation"]["returned"] == 1
    assert report["partial_native_graph_probe"]["counts"]["native_graph_binding"]["raised"] == 1
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
        ("native_graph_body_open", "returned", False),
        ("native_graph_body_open_batch", "raised", False),
        ("native_pdf_source_load", "entered", False),
        ("native_pdf_source_load", "returned", False),
        ("native_pdf_source_load", "raised", False),
        ("app_source_body_read", "returned", False),
        ("app_source_body_read", "raised", False),
        ("app_source_body_read_batch", "returned", False),
        ("app_source_body_read_batch", "raised", False),
        ("app_source_body_read_revision", "returned", False),
        ("app_source_body_read_revision", "raised", False),
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
    # Empty batch calls produce no probe rows; partial absence stays unknown,
    # not a false retrieval violation or a claim of complete zero.
    native_path.write_text(json.dumps({"schema": "dmb_negative_retrieval_native_graph_probe_v1",
        "coverage": "partial", "case_id": "case1", "status": "observed", "window": "turn_post_v1", "records": []}))
    empty_batch = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    assert empty_batch["checks"]["unexpected_retrieval"] is None
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
    old_anchor = 'save_page(tmp_path, optional_page.document_id, "This unrelated lore should remain unread.")'
    current_anchor = 'save_page(tmp_path, optional_page.document_id, "The local node is proposed to want freedom." if source_answer_output else "This unrelated lore should remain unread.")'
    owner_source = source.read_text()
    assert owner_source.count(old_anchor) + owner_source.count(current_anchor) == 1
    original_anchor = old_anchor if old_anchor in owner_source else current_anchor
    alternate_anchor = current_anchor if original_anchor == old_anchor else old_anchor
    alternate_source = tmp_path / "alternate-owner.py"
    alternate_source.write_text(owner_source.replace(original_anchor, alternate_anchor, 1))
    alternate_output = tmp_path / "alternate-derived.py"
    generate(alternate_source, alternate_output, fixture, expected_fixture_sha256=digest)
    compile(alternate_output.read_text(), str(alternate_output), "exec")
    ambiguous = tmp_path / "ambiguous-owner.py"
    ambiguous.write_text(owner_source + "\n" + alternate_anchor + "\n")
    with pytest.raises(ValueError, match="anchor"):
        generate(ambiguous, tmp_path / "ambiguous-derived.py", fixture, expected_fixture_sha256=digest)
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
    changed = copy.deepcopy(fixture)
    changed["related_pages"][0]["label"] = "current-page"
    calls = []
    monkeypatch.setattr(build_related_pages, "discover", lambda _: calls.append(True) or [pointer])
    with pytest.raises(ValueError, match="nonreserved"):
        inspect_related_pages(request, changed)
    assert calls == []
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
    def ordinary_capture(manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs):
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
    assert json.loads((out / "primary-page-stability.json").read_text())["status"] == "stable"
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
        def get(self, route, *, params):
            assert route == "/api/live/agent/worlds/w/conversation" and params == {"limit": 100}
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
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs: workflow.capture_case(
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
    def changed_get(self, route, *, params):
        assert params == {"limit": 100}
        calls.append(route)
        if len(calls) == 2:
            history["turns"][0]["assistant_text"] = "Changed after preflight."
        return Response()
    monkeypatch.setattr(Client, "get", changed_get)
    with pytest.raises(ValueError, match="differs"):
        module.capture(_test_manifest(tmp_path), tmp_path / "race", fixtures=fixture_set,
                       expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=fixture_pin)
    assert len(calls) == 2 and dispatched == ["c"]


def test_long_seeded_history_uses_full_before_and_after_pages(tmp_path, monkeypatch, verified_capture_owner):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module
    history_rows = [{"turn_id": f"t{i}", "sequence": i, "lifecycle_status": "completed",
                     "user_text": f"question {i}", "assistant_text": f"answer {i}"} for i in range(1, 61)]
    dialogue = [item for row in history_rows for item in ({"role": "user", "content": row["user_text"]},
                                                        {"role": "assistant", "content": row["assistant_text"]})]
    fixture = {"request": "Continue.", "history": dialogue, "page": "# Page", "related_pages": []}
    case = {"id": "long", "question": fixture["request"]}
    history = {"world_id": "w", "conversation_id": "c", "active_conversation_id": "c",
               "next_before_sequence": None, "turns": history_rows}
    queries = []
    class Response:
        status_code = 200
        def json(self): return history
    class Client:
        def get(self, route, *, params):
            queries.append((route, dict(params)))
            return Response()
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: ({"conversation_mode": "build_sequence", "cases": [case]}, tmp_path))
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    monkeypatch.setattr(module, "inspect_related_pages", lambda *a: [])
    def ordinary_case(client, world, template, current, directory, **kwargs):
        client.get("/api/live/agent/worlds/w/conversation")
        client.get("/api/live/agent/worlds/w/conversation", params={"include_turn_correlation": "true"})
        return "done"
    monkeypatch.setattr(workflow, "capture_case", ordinary_case)
    def ordinary_capture(manifest, output, *, cohort_manifest_sha256, clone_app=False):
        return workflow.capture_case(Client(), "w", {"primary_work": {"object_id": "page"}}, case, output)
    monkeypatch.setattr(workflow, "capture", ordinary_capture)
    fixture_set = {"long": fixture}
    assert module.capture(_test_manifest(tmp_path), tmp_path / "ok", fixtures=fixture_set,
        expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=module.fixture_sha256(fixture_set)) == "done"
    assert [params for _, params in queries] == [{"limit": 100}, {"limit": 100},
        {"include_turn_correlation": "true", "limit": 100}]
    history["next_before_sequence"] = 11
    with pytest.raises(ValueError, match="incomplete"):
        module.capture(_test_manifest(tmp_path), tmp_path / "truncated", fixtures=fixture_set,
            expected_manifest_sha256=MANIFEST_PIN, expected_fixture_sha256=module.fixture_sha256(fixture_set))


def test_seeder_accepts_long_bounded_dialogue_but_rejects_oversized_before_ownership(monkeypatch):
    from evals.negative_retrieval import seed_dialogue as module
    from uuid import uuid4
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    def reached_owner(): raise RuntimeError("owner guard reached")
    monkeypatch.setattr(module, "checked_owned_dsn", reached_owner)
    def dialogue(turns):
        return [item for i in range(turns) for item in ({"role": "user", "content": f"question {i}"},
                                                       {"role": "assistant", "content": f"answer {i}"})]
    world = "negative-seed-" + uuid4().hex
    with pytest.raises(RuntimeError, match="owner guard reached"):
        module.seed_dialogue({"history": dialogue(60)}, world=world, template={}, snapshot={})
    with pytest.raises(ValueError, match="complete nonblank dialogue pairs"):
        module.seed_dialogue({"history": dialogue(99)}, world=world, template={}, snapshot={})


def test_seeder_roundtrips_sixty_exchanges_through_complete_owner(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    from application_state import agent_conversation
    from apps.live_control_server.services import workspace_document_registry
    from evals.negative_retrieval import seed_dialogue as module
    world = "negative-seed-" + uuid4().hex
    page_id = str(uuid4())
    page = "# Synthetic"
    digest = sha256(page.encode()).hexdigest()
    template = {"primary_work": {"object_id": page_id, "expected_revision": 1, "expected_content_sha256": digest}}
    saved = SimpleNamespace(record=SimpleNamespace(world_id=world, kind="worldbuilding_source", status="active", revision=1),
        loaded_revision=1, markdown=page, committed_markdown=page, content_sha256=digest, committed_content_sha256=digest)
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    monkeypatch.setattr(module, "checked_owned_dsn", lambda: "synthetic")
    monkeypatch.setattr(workspace_document_registry, "get_workspace_document_snapshot", lambda *a: saved)
    class Service:
        def __init__(self): self.rows, self.pending = [], None
        def get_world_pointer(self, world_id): return SimpleNamespace(revision=0, active_conversation_id=None)
        def new_conversation(self, command): return SimpleNamespace(conversation_id=uuid4())
        def get_conversation(self, world_id, conversation_id): return SimpleNamespace(revision=len(self.rows) + 1)
        def accept_turn(self, submission):
            self.pending = submission.user_text
            return SimpleNamespace(turn_id=uuid4(), revision=1)
        def begin_turn(self, *args, **kwargs): return SimpleNamespace(revision=2)
        def complete_turn(self, result): self.rows.append({"user": self.pending, "assistant": result.assistant_text})
        def list_pending_build_dialogue(self, *args): return self.rows
        def list_build_dialogue(self, *args): pytest.fail("legacy six-turn reader used")
    service = Service()
    monkeypatch.setattr(agent_conversation, "AgentConversationService", lambda: service)
    history = [item for i in range(60) for item in ({"role": "user", "content": f"question {i}"},
                                                   {"role": "assistant", "content": f"answer {i}"})]
    result = module.seed_dialogue({"page": page, "history": history}, world=world, template=template, snapshot={})
    assert result is not None and len(service.rows) == 60
    assert service.rows[0] == {"user": "question 0", "assistant": "answer 0"}
    assert service.rows[-1] == {"user": "question 59", "assistant": "answer 59"}


def test_seeder_chooses_complete_dialogue_owner_before_long_seed():
    from types import SimpleNamespace
    from evals.negative_retrieval.seed_dialogue import _dialogue_reader
    full = lambda *args: "complete"
    recent = lambda *args: "recent"
    current = SimpleNamespace(list_pending_build_dialogue=full, list_build_dialogue=recent)
    assert _dialogue_reader(current, turns=60) is full
    old = SimpleNamespace(list_build_dialogue=recent)
    assert _dialogue_reader(old, turns=6) is recent
    with pytest.raises(ValueError, match="Complete Build dialogue owner"):
        _dialogue_reader(old, turns=7)
    with pytest.raises(ValueError, match="Complete Build dialogue owner"):
        _dialogue_reader(SimpleNamespace(), turns=0)


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
    reserved_fixture = copy.deepcopy(fixture)
    reserved_fixture["related_pages"][0]["label"] = "current-page"
    reserved_record = copy.deepcopy(record)
    reserved_record["before"][0]["label"] = "current-page"
    reserved_record["after"][0]["label"] = "current-page"
    with pytest.raises(ValueError, match="reserved"):
        verify_related_record(request, reserved_fixture, reserved_record)
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
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, *, cohort_manifest_sha256, clone_app=False, **kw:
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
    def dispatch(manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs):
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


@pytest.mark.parametrize("signature", ["serving", "modern", "unsupported"])
def test_capture_requires_pinned_cohort_and_never_requests_a_clone(tmp_path, monkeypatch, verified_capture_owner, signature):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture
    calls = []
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: ({"conversation_mode": "build_sequence"}, tmp_path))
    def serving(manifest, output, *, cohort_manifest_sha256):
        calls.append((cohort_manifest_sha256, "serving"))
        return "ok"
    def modern(manifest, output, *, cohort_manifest_sha256, clone_app=True):
        calls.append((cohort_manifest_sha256, clone_app))
        return "ok"
    def unsupported(manifest, output, **kwargs):
        calls.append("unsafe")
    monkeypatch.setattr(workflow, "capture", {"serving": serving, "modern": modern, "unsupported": unsupported}[signature])
    if signature == "unsupported":
        with pytest.raises(ValueError, match="explicitly support the pinned cohort"):
            capture(_test_manifest(tmp_path), tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN)
        assert calls == [] and not (tmp_path / "out").exists()
    else:
        assert capture(_test_manifest(tmp_path), tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN) == "ok"
        assert calls == [(MANIFEST_PIN, "serving" if signature == "serving" else False)]


def test_serving_capture_reaches_readonly_core_guard_without_inventory(tmp_path, monkeypatch, verified_capture_owner):
    import inspect
    import psycopg
    from evals.buddy_benchmark import workflow, cohort_capture, artifacts
    from evals.negative_retrieval.capture import capture
    if "clone_app" in inspect.signature(workflow.capture).parameters:
        pytest.skip("Serving-lineage capture signature is not present")
    entries = {"app": {"host": "127.0.0.1", "port": 1234, "database": "synthetic_app", "oid": "1", "system_identifier": "2"},
               "native": {"host": "127.0.0.1", "port": 1234, "database": "synthetic_core", "oid": "3", "system_identifier": "4"}}
    spec = {"conversation_mode": "build_sequence", "pins": {"synthetic": True}, "runtime": {},
            "request_template": {}, "world": "synthetic", "isolation": entries}
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: (spec, tmp_path))
    monkeypatch.setattr(workflow, "verify_runtime", lambda *a: None)
    monkeypatch.setattr(workflow, "validate_template", lambda *a, **k: None)
    monkeypatch.delenv("DMB_AGENT_GRAPH_LOCAL_PROFILE", raising=False)
    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", "postgresql://user@127.0.0.1:1234/synthetic_app")
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://user@127.0.0.1:1234/synthetic_core")
    class FakeConnection:
        def __init__(self, values): self.values = values
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql): return self
        def fetchone(self): return self.values
    def fake_connect(dsn, **kwargs):
        assert kwargs == {"options": "-c default_transaction_read_only=on"}
        row = entries["app"] if dsn.endswith("synthetic_app") else entries["native"]
        return FakeConnection((row["database"], row["oid"], row["system_identifier"]))
    monkeypatch.setattr(psycopg, "connect", fake_connect)
    def forbidden(*args, **kwargs): pytest.fail("Full Core inventory must not run")
    monkeypatch.setattr(artifacts, "row_inventory", forbidden)
    def readonly_guard(dsn): raise RuntimeError("synthetic readonly guard reached")
    monkeypatch.setattr(cohort_capture, "require_read_only_core", readonly_guard)
    with pytest.raises(RuntimeError, match="synthetic readonly guard reached"):
        capture(_test_manifest(tmp_path), tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN)


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


@pytest.mark.parametrize(('choice', 'expected'), [
    ('current_saved_page', 'current_saved_page'),
    ('anchored', 'anchored'), ('source_lookup', 'source_lookup'), ('uncertain', 'uncertain'),
    ('private untrusted text', 'other_or_invalid'), (None, 'other_or_invalid'),
])
def test_current_source_scope_projection_never_implies_an_admitted_decision_or_read(choice, expected):
    import json
    from evals.negative_retrieval.trace_observation import controller_observations, observed_acquisitions
    response = {'answers': {'source_need': {'selected': choice}}}
    trace = {'schema': 'dmb_turn_context_trace_v1', 'observations': [{
        'sequence': 0, 'kind': 'context_snapshot', 'snapshot_kind': 'provider_response', 'stage': 'after',
        'materials': [{'item_id': 'unvalidated-controller-decision:synthetic', 'text': json.dumps(response)}]}]}
    result = controller_observations(trace)
    snapshot, = result['controller_snapshots']
    assert snapshot['validation'] == 'unvalidated'
    assert snapshot['selections']['source_need'] == expected
    assert observed_acquisitions(trace)['observed'] == []
    assert observed_acquisitions(trace)['journal_complete'] is None
    assert 'private untrusted text' not in json.dumps(result)


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


def test_shepherd_trace_question_is_a_negative_development_case():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "evals/negative_retrieval/fixtures"
    public = json.loads((root / "development.json").read_text())
    private = json.loads((root / "development-private.json").read_text())
    case = next(row for row in public["cases"] if row["id"] == "dev-shepherd-naming")
    expected = ("The Shepherd is part of the group of humans that came from Mirathorn to settle BogBlossom. "
        "I like the idea that this person was who found the collapsed swamp Wizard Tower, which suggests they worked for the Wizard Tower Salvage company, maybe even helped found it. "
        "Then disappeared as they were polluted by Maelthor. \nGive me a list of 10 name options, I'm indifferent to gender.")
    assert case["request"] == expected
    assert [row["role"] for row in case["history"]] == ["user", "assistant"]
    rubric = private["cases"][case["id"]]
    assert rubric["max_catalog_discoveries"] == rubric["max_graph_query_attempts"] == 0
    assert rubric["required_reads"] == rubric["allowed_reads"] == [] and rubric["outcomes"] == ["answer"]
    assert assess(rubric, observation(outcome="answer", graph_query_attempts=0,
                                      graph_query_journal_complete=False))["status"] == "unproven"
    assert assess(rubric, observation(outcome="answer", catalog_discoveries=1))["checks"]["catalog_budget"] is False


def test_long_context_development_case_requires_early_dialogue_without_search():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "evals/negative_retrieval/fixtures"
    public = json.loads((root / "development.json").read_text())
    private = json.loads((root / "development-private.json").read_text())
    case = next(row for row in public["cases"] if row["id"] == "dev-long-context-reuse")
    rubric = private["cases"][case["id"]]
    assert len(case["history"]) == 120
    assert all(row["role"] == ("user" if i % 2 == 0 else "assistant") for i, row in enumerate(case["history"]))
    assert "blue glass bead" in case["history"][0]["content"] and "Mara Vale" in case["history"][0]["content"]
    assert "blue glass bead" not in case["request"] and "Mara Vale" not in case["request"]
    assert all("blue glass bead" not in row["body"] and "Mara Vale" not in row["body"] for row in case["related_pages"])
    assert rubric["max_catalog_discoveries"] == rubric["max_graph_query_attempts"] == 0
    assert rubric["required_reads"] == rubric["allowed_reads"] == [] and rubric["outcomes"] == ["answer"]
    assert assess(rubric, observation(outcome="answer", graph_query_attempts=1,
                                      graph_query_journal_complete=False))["checks"]["graph_query_budget"] is False
    assert assess(rubric, observation(outcome="answer", graph_query_attempts=0,
                                      graph_query_journal_complete=False))["status"] == "unproven"


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
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs:
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
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs:
                        workflow.capture_case(None, "world", {}, {"id": "case1"}, output))
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    with pytest.raises(RuntimeError, match="history unavailable"):
        capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    for name in ("related-page-probe", "native-graph-probe"):
        evidence = json.loads((tmp_path / "case1" / (name + ".json")).read_text())
        assert evidence["status"] == "not_started" and evidence["records"] == []
    primary = json.loads((tmp_path / "case1" / "primary-resolution-probe.json").read_text())
    assert primary["status"] == "not_started" and primary["started"] == 0
    sql = json.loads((tmp_path / "case1" / "sql-window-probe.json").read_text())
    assert sql["status"] == "not_started" and sql["started"] == 0


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
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs:
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
    monkeypatch.setattr(workflow, "capture", lambda manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs:
                        workflow.capture_case(client, "world", {}, {"id": "case1"}, output))
    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k:
                        ({"conversation_mode": "build_sequence"}, tmp_path))
    with pytest.raises(TypeError, match="unsupported"):
        capture(_test_manifest(tmp_path), tmp_path / "case1", expected_manifest_sha256=MANIFEST_PIN)
    for name in ("related-page-probe", "native-graph-probe"):
        evidence = json.loads((tmp_path / "case1" / (name + ".json")).read_text())
        assert evidence["status"] == ("not_started" if kind == "async_method" else "dispatch_uncertain")
        assert evidence["records"] == []
    primary = json.loads((tmp_path / "case1" / "primary-resolution-probe.json").read_text())
    assert primary["status"] == ("unavailable" if kind == "async_method" else "uncertain")
    assert primary["started"] == 0
    sql = json.loads((tmp_path / "case1" / "sql-window-probe.json").read_text())
    assert sql["status"] == ("unavailable" if kind == "async_method" else "uncertain")
    assert sql["started"] == 0


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
    def run_capture(manifest, output, *, cohort_manifest_sha256, clone_app=False, **kwargs):
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


def test_report_does_not_credit_failed_required_page_materialization(tmp_path, monkeypatch):
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
    for state, expected in (("raised", None), ("entered", None), ("returned", None)):
        related["records"] = [{"owner": "related_page_materialization", "state": state, "document_id": "doc"}]
        (tmp_path / "related-page-probe.json").write_text(json.dumps(related))
        result = report_case(tmp_path, fixture, positive)
        assert result["related_context_verified"] is True
        assert result["checks"]["required_evidence"] is expected
        assert result["status"] == "unproven"
        negative = report_case(tmp_path, fixture, CASE)
        assert negative["checks"]["unexpected_retrieval"] is False
    # Exact fixture binding and exact returned body are both necessary. A
    # changed World, revision or digest must not credit the required source.
    from evals.negative_retrieval import report, fixture_binding
    monkeypatch.setattr(report, "verify_fixture_pin", lambda *args: True)
    monkeypatch.setattr(fixture_binding, "verify_fixture", lambda *args: True)
    (tmp_path / "fixture-pin.json").write_text("{}")
    (tmp_path / "history-before.json").write_text(json.dumps(envelope(history)))
    exact = {"owner": "related_page_materialization", "state": "returned", "world_id": "world",
             "document_id": "doc", "registry_revision": 1, "returned_world_id": "world",
             "returned_document_id": "doc", "returned_registry_revision": 1,
             "returned_content_sha256": inventory[0]["content_sha256"]}
    for change, expected in (({}, True), ({"world_id": "other"}, None),
            ({"registry_revision": 2}, None), ({"world_id": []}, None),
            ({"document_id": {}}, None), ({"returned_world_id": "other"}, None),
            ({"returned_document_id": "other"}, None), ({"returned_registry_revision": 2}, None),
            ({"returned_content_sha256": "0" * 64}, None), ({"state": "raised"}, None)):
        related["records"] = [{**exact, **change}]
        (tmp_path / "related-page-probe.json").write_text(json.dumps(related))
        assert report_case(tmp_path, fixture, positive)["checks"]["required_evidence"] is expected
    related["records"] = []
    (tmp_path / "related-page-probe.json").write_text(json.dumps(related))
    for owner in ("app_source_body_read", "app_source_body_read_batch", "app_source_body_read_revision", "native_graph_body_open", "native_graph_body_open_batch"):
        for state in ("returned", "raised"):
            native["records"] = [{"owner": owner, "state": state}]
            (tmp_path / "native-graph-probe.json").write_text(json.dumps(native))
            result = report_case(tmp_path, fixture, positive)
            assert result["checks"]["required_evidence"] is None
            assert result["status"] == "unproven"


@pytest.mark.parametrize(('state', 'document', 'world', 'revision', 'bound', 'collision', 'count', 'label'), [
    ('entered', 'primary', 'world', 1, True, False, 1, 'current-page'),
    ('returned', 'primary', 'world', 1, True, False, 1, 'current-page'),
    ('raised', 'primary', 'world', 1, True, False, 1, 'current-page'),
    ('returned', 'primary', 'other', 1, True, False, 1, '<unmapped-acquisition>'),
    ('returned', 'primary', 'world', 2, True, False, 1, '<unmapped-acquisition>'),
    ('returned', 'primary', None, None, True, False, 1, '<unmapped-acquisition>'),
    ('returned', 'foreign', 'world', 1, True, False, 0, '<unmapped-acquisition>'),
    ('returned', None, 'world', 1, True, False, 0, '<unmapped-acquisition>'),
    ('returned', 'primary', 'world', 1, False, False, None, '<unmapped-acquisition>'),
    ('returned', 'primary', 'world', 1, True, True, 1, '<unmapped-acquisition>'),
])
def test_report_primary_pointer_attempt_without_crediting_read(
        tmp_path, monkeypatch, state, document, world, revision, bound, collision, count, label):
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid5
    from evals.negative_retrieval import report, fixture_binding, fixture_sources

    def envelope(body):
        raw = json.dumps(body).encode()
        return {'http_status': 200, 'body': body, 'raw_body_hex': raw.hex(),
                'raw_body_sha256': hashlib.sha256(raw).hexdigest()}

    request = {'turn_id': 'turn', 'client_thread_id': 'thread', 'message': 'Use the current page.',
        'owner_scope': {'world_id': 'world'}, 'surface': {'surface_id': 'build', 'instance_id': 'primary'},
        'primary_work': {'object_id': 'primary', 'expected_revision': 1}}
    turn = {'turn_id': 'saved', 'idempotency_key': str(uuid5(NAMESPACE_URL, 'dmb-agent-turn:world:turn')),
        'user_text': request['message'], 'lifecycle_status': 'completed', 'provenance': {
            'world_id': 'world', 'surface_id': 'build', 'surface_instance_id': 'primary'},
        'knowledge_context': {'completion': question_completion('Where?')}}
    history = {'world_id': 'world', 'conversation_id': 'conversation', 'turns': [turn]}
    trace = {'world_id': 'world', 'turn_id': 'saved', 'attempts': [{'schema': 'dmb_turn_context_trace_v1',
        'world_id': 'world', 'conversation_id': 'conversation', 'turn_id': 'saved',
        'terminal_status': 'completed', 'capture_status': 'complete', 'observations': []}]}
    row = {'owner': 'related_page_materialization', 'state': state}
    if document is not None:
        row['document_id'] = document
    if world is not None:
        row['world_id'] = world
    if revision is not None:
        row['registry_revision'] = revision
    inventory = [{'document_id': 'other', 'label': 'current-page', 'world_id': 'world',
                  'registry_revision': 1, 'content_sha256': '0' * 64}] if collision else []
    artifacts = {'request': request, 'history-before': envelope(history), 'history-after': envelope(history),
        'context-trace': envelope(trace), 'answer-http': envelope({'turn_id': 'turn', 'client_thread_id': 'thread',
            'knowledge_context': turn['knowledge_context']}), 'fixture-sources': {'before': inventory}, 'fixture-pin': {},
        'related-page-probe': {'schema': 'dmb_negative_retrieval_related_page_probe_v1', 'coverage': 'partial',
            'case_id': 'case1', 'status': 'observed', 'window': 'turn_post_v1', 'records': [row,
                {'owner': 'current_page_metadata', 'state': 'returned'}]},
        'native-graph-probe': {'schema': 'dmb_negative_retrieval_native_graph_probe_v1', 'coverage': 'partial',
            'case_id': 'case1', 'status': 'observed', 'window': 'turn_post_v1', 'records': []}}
    for name, value in artifacts.items():
        (tmp_path / f'{name}.json').write_text(json.dumps(value))
    monkeypatch.setattr(report, 'verify_fixture_pin', lambda *a: True)
    monkeypatch.setattr(fixture_sources, 'verify_related_record', lambda *a: True)
    monkeypatch.setattr(fixture_sources, 'related_trace_labels', lambda *a: {})
    def verify(*args):
        if not bound:
            raise ValueError('fixture differs')
        return True
    monkeypatch.setattr(fixture_binding, 'verify_fixture', verify)
    actual_assess, observations = report.assess, []
    def record_assessment(rubric, observation):
        observations.append(observation)
        return actual_assess(rubric, observation)
    monkeypatch.setattr(report, 'assess', record_assessment)
    rubric = {'max_catalog_discoveries': 0, 'required_reads': ['current-page'],
              'allowed_reads': ['current-page'], 'outcomes': ['clarification']}
    result = report.report_case(tmp_path, {'id': 'case1', 'request': request['message']}, rubric)
    observation, = observations
    assert observation['reads'] == [label]
    assert result['primary_document_id_attempts_diagnostic'] == count
    assert result['current_page_metadata_attempts_diagnostic'] == 1
    assert 'current-page' not in observation['completed_reads']
    assert result['checks']['required_evidence'] is None
    assert result['status'] == 'unproven' and result['capture_environment_verified'] is None


@pytest.mark.parametrize(('state', 'input_world', 'input_id', 'input_revision', 'returned_world', 'returned_id', 'returned_revision', 'returned_hash', 'bound', 'collision', 'credited'), [
    ('returned', 'world', 'primary', 1, 'world', 'primary', 1, 'matching', True, False, True),
    ('entered', 'world', 'primary', 1, 'world', 'primary', 1, 'matching', True, False, False),
    ('raised', 'world', 'primary', 1, 'world', 'primary', 1, 'matching', True, False, False),
    ('returned', 'other', 'primary', 1, 'world', 'primary', 1, 'matching', True, False, False),
    ('returned', 'world', 'other', 1, 'world', 'primary', 1, 'matching', True, False, False),
    ('returned', 'world', 'primary', 2, 'world', 'primary', 1, 'matching', True, False, False),
    ('returned', 'world', 'primary', 1, 'other', 'primary', 1, 'matching', True, False, False),
    ('returned', 'world', 'primary', 1, 'world', 'other', 1, 'matching', True, False, False),
    ('returned', 'world', 'primary', 1, 'world', 'primary', 2, 'matching', True, False, False),
    ('returned', 'world', 'primary', 1, 'world', 'primary', 1, 'wrong', True, False, False),
    ('returned', 'world', 'primary', 1, 'world', 'primary', 1, 'matching', False, False, False),
    ('returned', 'world', 'primary', 1, 'world', 'primary', 1, 'matching', True, True, False),
    ('returned', 'world', 'other', 1, 'world', 'other', 1, 'zero', True, True, False),
])
def test_report_primary_return_requires_frozen_exact_body(
        tmp_path, monkeypatch, state, input_world, input_id, input_revision,
        returned_world, returned_id, returned_revision, returned_hash, bound, collision, credited):
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid5
    from evals.negative_retrieval import report, fixture_binding, fixture_sources

    def envelope(body):
        raw = json.dumps(body).encode()
        return {'http_status': 200, 'body': body, 'raw_body_hex': raw.hex(),
                'raw_body_sha256': hashlib.sha256(raw).hexdigest()}

    request = {'turn_id': 'turn', 'client_thread_id': 'thread', 'message': 'Use the current page.',
        'owner_scope': {'world_id': 'world'}, 'surface': {'surface_id': 'build', 'instance_id': 'primary'},
        'primary_work': {'object_id': 'primary', 'expected_revision': 1,
                         'expected_content_sha256': hashlib.sha256(b'fixture page').hexdigest()}}
    turn = {'turn_id': 'saved', 'idempotency_key': str(uuid5(NAMESPACE_URL, 'dmb-agent-turn:world:turn')),
        'user_text': request['message'], 'lifecycle_status': 'completed', 'provenance': {
            'world_id': 'world', 'surface_id': 'build', 'surface_instance_id': 'primary'},
        'knowledge_context': {'completion': question_completion('Where?')}}
    history = {'world_id': 'world', 'conversation_id': 'conversation', 'turns': [turn]}
    trace = {'world_id': 'world', 'turn_id': 'saved', 'attempts': [{'schema': 'dmb_turn_context_trace_v1',
        'world_id': 'world', 'conversation_id': 'conversation', 'turn_id': 'saved',
        'terminal_status': 'completed', 'capture_status': 'complete', 'observations': []}]}
    row = {'owner': 'related_page_materialization', 'state': state,
           'document_id': input_id, 'world_id': input_world, 'registry_revision': input_revision,
           'returned_world_id': returned_world, 'returned_document_id': returned_id,
           'returned_registry_revision': returned_revision,
           'returned_content_sha256': ('0' * 64 if returned_hash == 'zero' else
               hashlib.sha256(b'fixture page' if returned_hash == 'matching' else b'wrong').hexdigest())}
    inventory = [{'document_id': 'other', 'label': 'current-page', 'world_id': 'world',
                  'registry_revision': 1, 'content_sha256': '0' * 64}] if collision else []
    artifacts = {'request': request, 'history-before': envelope(history), 'history-after': envelope(history),
        'context-trace': envelope(trace), 'answer-http': envelope({'turn_id': 'turn', 'client_thread_id': 'thread',
            'knowledge_context': turn['knowledge_context']}), 'fixture-sources': {'before': inventory}, 'fixture-pin': {},
        'related-page-probe': {'schema': 'dmb_negative_retrieval_related_page_probe_v1', 'coverage': 'partial',
            'case_id': 'case1', 'status': 'observed', 'window': 'turn_post_v1', 'records': [row,
                {'owner': 'current_page_metadata', 'state': 'returned'}]},
        'native-graph-probe': {'schema': 'dmb_negative_retrieval_native_graph_probe_v1', 'coverage': 'partial',
            'case_id': 'case1', 'status': 'observed', 'window': 'turn_post_v1', 'records': []}}
    for name, value in artifacts.items():
        (tmp_path / f'{name}.json').write_text(json.dumps(value))
    monkeypatch.setattr(report, 'verify_fixture_pin', lambda *a: True)
    monkeypatch.setattr(fixture_sources, 'verify_related_record', lambda *a: True)
    monkeypatch.setattr(fixture_sources, 'related_trace_labels', lambda *a: {})
    def verify(*args):
        if not bound:
            raise ValueError('fixture differs')
        return True
    monkeypatch.setattr(fixture_binding, 'verify_fixture', verify)
    actual_assess, observations = report.assess, []
    def record_assessment(rubric, observation):
        observations.append(observation)
        return actual_assess(rubric, observation)
    monkeypatch.setattr(report, 'assess', record_assessment)
    rubric = {'max_catalog_discoveries': 0, 'required_reads': ['current-page'],
              'allowed_reads': ['current-page'], 'outcomes': ['clarification']}
    result = report.report_case(tmp_path, {'id': 'case1', 'request': request['message'], 'page': 'fixture page'}, rubric)
    observation, = observations
    assert ('current-page' in observation['completed_reads']) is credited
    assert result['checks']['required_evidence'] is (True if credited else None)
    assert result['status'] == 'unproven' and result['capture_environment_verified'] is None


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
    monkeypatch.setattr(workflow, "capture", lambda *a, cohort_manifest_sha256, clone_app=False, **k: calls.append("runner") or "ok")
    assert module.capture(_test_manifest(tmp_path), tmp_path / "out", expected_manifest_sha256=MANIFEST_PIN) == "ok"
    assert calls == ["owner", "runner"]


def test_owned_app_guard_rejects_a_different_working_checkout(tmp_path, monkeypatch):
    from evals.negative_retrieval.owned_db_fixture import checked_owned_dsn

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="evaluator checkout"):
        checked_owned_dsn()


def test_trace_sized_shepherd_catalog_preserves_source_free_contract():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "evals/negative_retrieval/fixtures"
    public = json.loads((root / "development.json").read_text())
    private = json.loads((root / "development-private.json").read_text())
    cases = {row["id"]: row for row in public["cases"]}
    small, large = cases["dev-shepherd-naming"], cases["dev-shepherd-catalog-20"]
    assert (large["request"], large["page"], large["history"]) == (small["request"], small["page"], small["history"])
    assert len(large["related_pages"]) == 20
    assert len({row["label"] for row in large["related_pages"]}) == 20
    assert len({row["title"] for row in large["related_pages"]}) == 20
    rubric = private["cases"][large["id"]]
    assert rubric == private["cases"][small["id"]]
    assert assess(rubric, observation(outcome="answer", catalog_discoveries=1))["checks"]["catalog_budget"] is False
    assert assess(rubric, observation(outcome="answer", catalog_discoveries=0, catalog_journal_complete=False))["checks"]["catalog_budget"] is None


def test_source_window_scopes_executor_and_flags_unrelated_calls():
    from concurrent.futures import ThreadPoolExecutor
    from evals.negative_retrieval.source_window import observe_source_window
    def source(value):
        if value == 'raise':
            raise ValueError('synthetic')
        return value
    prebound = source
    with ThreadPoolExecutor(max_workers=1) as build, ThreadPoolExecutor(max_workers=1) as unrelated:
        build.submit(lambda: None).result()
        unrelated.submit(lambda: None).result()
        original = build.submit
        with observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
            assert prebound('main') == 'main'
            assert build.submit(prebound, 'worker').result() == 'worker'
            with pytest.raises(ValueError, match='synthetic'):
                build.submit(prebound, 'raise').result()
            assert unrelated.submit(prebound, 'other').result() == 'other'
        assert build.submit == original
    assert state['status'] == 'uncertain'
    assert state['scoped']['text'] == 3 and state['unscoped']['text'] == 1
    assert state['pending_at_close'] == 0 and state['coverage'] == 'partial'


def test_source_window_retains_unfinished_work_as_uncertain():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from evals.negative_retrieval.source_window import observe_source_window
    entered, release = Event(), Event()
    def source():
        entered.set()
        assert release.wait(5)
    with ThreadPoolExecutor(max_workers=1) as build:
        try:
            with observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
                future = build.submit(source)
                assert entered.wait(5)
            assert state['status'] == 'uncertain' and state['pending_at_close'] == 1
        finally:
            release.set()
        future.result(timeout=5)
        assert state['status'] == 'uncertain' and state['pending_at_close'] == 1


def test_source_window_unavailable_slots_do_not_claim_zero(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from evals.negative_retrieval import source_window
    def source(): pass
    fake = SimpleNamespace(get_tool=lambda slot: 'occupied')
    with ThreadPoolExecutor(max_workers=1) as build:
        with monkeypatch.context() as scoped:
            scoped.setattr(source_window.sys, 'monitoring', fake)
            with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
                source()
        assert state['status'] == 'unavailable' and state['coverage'] == 'partial'
        with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build) as next_state:
            source()
        assert next_state['scoped']['text'] == 1


def test_source_window_monitors_actual_core_view_before_fake_database():
    from concurrent.futures import ThreadPoolExecutor
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from evals.negative_retrieval.source_window import observe_source_window
    class NoDatabase:
        def transaction(self): raise RuntimeError('synthetic sentinel')
    view = _PostgresNativeTextSourceView(NoDatabase(), 'synthetic', 1)
    prebound = view.get_native_text_source
    def invoke():
        with pytest.raises(RuntimeError, match='synthetic sentinel'):
            prebound(source_artifact_id='synthetic', source_revision_id='synthetic', span_id='synthetic')
    with ThreadPoolExecutor(max_workers=1) as build:
        build.submit(lambda: None).result()
        with observe_source_window(owners={prebound.__func__.__code__: 'text'}, executor=build) as state:
            invoke()
            build.submit(invoke).result()
    assert state['status'] == 'observed' and state['scoped']['text'] == 2
    assert state['coverage'] == 'partial'


def test_source_window_cancelled_task_is_conservatively_unsettled():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from evals.negative_retrieval.source_window import observe_source_window
    ready, release = Event(), Event()
    def blocker():
        ready.set()
        assert release.wait(5)
    def source(): raise AssertionError('cancelled task must not run')
    with ThreadPoolExecutor(max_workers=1) as build:
        blocker_future = build.submit(blocker)
        assert ready.wait(5)
        try:
            with observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
                future = build.submit(source)
                assert future.cancel()
            assert state['status'] == 'uncertain' and state['pending_at_close'] == 1
        finally:
            release.set()
        blocker_future.result(timeout=5)


def test_source_window_preserves_original_failure_when_cleanup_fails(monkeypatch):
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from evals.negative_retrieval import source_window
    monkeypatch.setattr(source_window, '_poisoned', False)
    real = sys.monitoring
    def source(): pass
    def set_local(slot, code, events):
        real.set_local_events(slot, code, events)
        if not events:
            raise RuntimeError('synthetic cleanup error')
    proxy = SimpleNamespace(events=real.events, get_tool=real.get_tool, use_tool_id=real.use_tool_id,
        set_local_events=set_local, register_callback=real.register_callback, free_tool_id=real.free_tool_id)
    with ThreadPoolExecutor(max_workers=1) as build, monkeypatch.context() as scoped:
        scoped.setattr(source_window.sys, 'monitoring', proxy)
        with pytest.raises(ValueError, match='original post failure') as failure:
            with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
                raise ValueError('original post failure')
        assert state['status'] == 'uncertain' and state['monitor_error'] is True
        assert any('cleanup also failed' in note for note in failure.value.__notes__)
    assert all(real.get_tool(i) != 'buddy-negative-source-window' for i in range(6))


def test_source_window_cleans_partially_armed_setup(monkeypatch):
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from evals.negative_retrieval import source_window
    real = sys.monitoring
    def source(): pass
    def set_local(slot, code, events):
        real.set_local_events(slot, code, events)
        if events:
            raise RuntimeError('synthetic setup error')
    proxy = SimpleNamespace(events=real.events, get_tool=real.get_tool, use_tool_id=real.use_tool_id,
        set_local_events=set_local, register_callback=real.register_callback, free_tool_id=real.free_tool_id)
    with ThreadPoolExecutor(max_workers=1) as build, monkeypatch.context() as scoped:
        scoped.setattr(source_window.sys, 'monitoring', proxy)
        with pytest.raises(RuntimeError, match='synthetic setup error'):
            with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build):
                pytest.fail('must not dispatch')
    assert all(real.get_tool(i) != 'buddy-negative-source-window' for i in range(6))
    with ThreadPoolExecutor(max_workers=1) as build:
        with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
            source()
    assert state['scoped']['text'] == 1


def test_capture_freezes_unfinished_source_window_artifact(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import source_window
    from evals.negative_retrieval.capture import capture
    started, release = Event(), Event()
    def source():
        started.set()
        assert release.wait(5)
    with ThreadPoolExecutor(max_workers=1) as build:
        monkeypatch.setattr(source_window, '_default_owners', lambda: ({source.__code__: 'text'}, build))
        class Client:
            def post(self, route, *args, **kwargs):
                self.future = build.submit(source)
                assert started.wait(5)
                return {'ok': True}
        client = Client()
        monkeypatch.setattr(workflow, 'capture_case', lambda client, *args, **kwargs: client.post('/api/live/agent/turn'))
        monkeypatch.setattr(workflow, 'capture', lambda manifest, output, *, cohort_manifest_sha256, clone_app=False:
                            workflow.capture_case(client, 'world', {}, {'id': 'case1'}, output))
        monkeypatch.setattr(workflow, 'load_manifest', lambda *args, **kwargs: ({'conversation_mode': 'build_sequence'}, tmp_path))
        try:
            assert capture(_test_manifest(tmp_path), tmp_path/'case1', expected_manifest_sha256=MANIFEST_PIN) == {'ok': True}
            path = tmp_path/'case1'/'source-window-probe.json'
            before = path.read_bytes()
            row = json.loads(before)
            assert row['status'] == 'uncertain' and row['pending_at_close'] == 1
            assert row['coverage'] == 'partial' and row['scoped']['text'] == 1
        finally:
            release.set()
        client.future.result(timeout=5)
        assert path.read_bytes() == before


def test_capture_records_source_window_setup_failure_before_dispatch(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from contextlib import contextmanager
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module
    @contextmanager
    def broken_monitor():
        raise RuntimeError('synthetic monitor setup failure')
        yield
    class Client:
        def post(self, *args, **kwargs): pytest.fail('must not dispatch')
    monkeypatch.setattr(module, 'observe_source_window', broken_monitor)
    monkeypatch.setattr(workflow, 'capture_case', lambda client, *args, **kwargs: client.post('/api/live/agent/turn'))
    monkeypatch.setattr(workflow, 'capture', lambda manifest, output, *, cohort_manifest_sha256, clone_app=False:
                        workflow.capture_case(Client(), 'world', {}, {'id': 'case1'}, output))
    monkeypatch.setattr(workflow, 'load_manifest', lambda *args, **kwargs: ({'conversation_mode': 'build_sequence'}, tmp_path))
    with pytest.raises(RuntimeError, match='synthetic monitor setup failure'):
        module.capture(_test_manifest(tmp_path), tmp_path/'case1', expected_manifest_sha256=MANIFEST_PIN)
    row = json.loads((tmp_path/'case1'/'source-window-probe.json').read_text())
    assert row['status'] == 'setup_failed' and row['monitor_error'] is True
    assert row['coverage'] == 'partial'


def test_source_window_submission_failure_preserves_exception():
    from evals.negative_retrieval.source_window import observe_source_window
    class BrokenExecutor:
        def submit(self, *args, **kwargs): raise LookupError('synthetic submission failure')
    def source(): pass
    build = BrokenExecutor()
    original = build.submit
    with pytest.raises(LookupError, match='synthetic submission failure'):
        with observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
            build.submit(source)
    assert build.submit == original and state['pending_at_close'] == 0


def test_source_window_cleanup_error_cannot_look_like_success(monkeypatch):
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from evals.negative_retrieval import source_window
    monkeypatch.setattr(source_window, '_poisoned', False)
    real = sys.monitoring
    def source(): pass
    def set_local(slot, code, events):
        real.set_local_events(slot, code, events)
        if not events: raise RuntimeError('synthetic cleanup error')
    proxy = SimpleNamespace(events=real.events, get_tool=real.get_tool, use_tool_id=real.use_tool_id,
        set_local_events=set_local, register_callback=real.register_callback, free_tool_id=real.free_tool_id)
    with ThreadPoolExecutor(max_workers=1) as build, monkeypatch.context() as scoped:
        scoped.setattr(source_window.sys, 'monitoring', proxy)
        with pytest.raises(source_window.SourceWindowCleanupError):
            with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
                source()
        assert state['status'] == 'uncertain' and state['monitor_error'] is True
    assert all(real.get_tool(i) != 'buddy-negative-source-window' for i in range(6))


def test_capture_source_window_observes_real_view_through_testclient_executor(tmp_path, monkeypatch, verified_capture_owner):
    import asyncio
    import json
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from apps.live_control_server.routes import agent
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView, PostgresNativeSourceEvidenceRepository
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import source_window, sql_window
    from evals.negative_retrieval.capture import capture
    class NoDatabase:
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args, **kwargs): raise RuntimeError('synthetic sentinel')
    class SqlCursor:
        def execute(self): return None
    cursor=SqlCursor()
    cursor.connection=SimpleNamespace(info=SimpleNamespace(host='127.0.0.1',port=5432,dbname='synthetic-app'))
    monkeypatch.setattr(sql_window, '_driver_owners', lambda: ({SqlCursor.execute.__code__: 'execute'},0))
    monkeypatch.setattr(sql_window, '_endpoints', lambda: {'app': ('127.0.0.1','5432','synthetic-app')})
    view = _PostgresNativeTextSourceView(NoDatabase(), 'synthetic', 1)
    pdf_repo = PostgresNativeSourceEvidenceRepository(NoDatabase())
    pdf_alias = pdf_repo.get_native_pdf_source
    pdf_list_alias = pdf_repo.list_public_native_pdf_revisions
    def acquire():
        cursor.execute()
        with pytest.raises(RuntimeError, match='synthetic sentinel'):
            pdf_list_alias('synthetic')
        with pytest.raises(RuntimeError, match='synthetic sentinel'):
            pdf_alias('synthetic', 'synthetic-revision')
        with pytest.raises(RuntimeError, match='synthetic sentinel'):
            view.get_native_text_source(source_artifact_id='synthetic', source_revision_id='synthetic', span_id='synthetic')
        assert view.get_native_text_sources([])==()
        with pytest.raises(RuntimeError, match='synthetic sentinel'):
            view.get_native_text_sources([('synthetic','synthetic','synthetic')])
    import hashlib
    page = '# synthetic primary'; digest = hashlib.sha256(page.encode()).hexdigest()
    record = SimpleNamespace(kind='worldbuilding_source', status='active', content_status='committed',
        world_id='world', document_id='page', revision=1, title='Synthetic', source_domain='worldbuilding',
        document_class='note', authority_state='draft', visibility_state='internal')
    snapshot = SimpleNamespace(record=record, markdown=page, content_sha256=digest,
                               loaded_revision=1, page_presentation=None)
    monkeypatch.setattr(agent, '_managed_world_root', lambda: 'synthetic-root')
    monkeypatch.setattr(agent, 'get_committed_page_snapshot', lambda root, page_id: snapshot)
    body = SimpleNamespace(primary_work=SimpleNamespace(kind='build',object_id='page',expected_revision=1,
                           expected_content_sha256=digest), surface=SimpleNamespace(surface_id='build'),
                           build_image_move_capture=None)
    app = FastAPI()
    with ThreadPoolExecutor(max_workers=1) as build:
        build.submit(lambda: None).result()
        @app.post('/api/live/agent/turn')
        async def turn():
            cursor.execute()
            agent._build_work_resolver(body, {'kind':'world','id':'world'})
            await asyncio.get_running_loop().run_in_executor(build, acquire)
            return {'ok': True}
        owners, _, provenance = source_window._default_owners()
        assert view.get_native_text_source.__func__.__code__ in owners and provenance is not None
        monkeypatch.setattr(source_window, '_default_owners', lambda: (owners, build, provenance))
        monkeypatch.setattr(workflow, 'capture_case', lambda client, *args, **kwargs: client.post('/api/live/agent/turn'))
        monkeypatch.setattr(workflow, 'load_manifest', lambda *args, **kwargs: ({'conversation_mode': 'build_sequence'}, tmp_path))
        with TestClient(app) as client:
            monkeypatch.setattr(workflow, 'capture', lambda manifest, output, *, cohort_manifest_sha256, clone_app=False:
                                workflow.capture_case(client, 'world', {}, {'id': 'case1'}, output))
            response = capture(_test_manifest(tmp_path), tmp_path/'case1', expected_manifest_sha256=MANIFEST_PIN)
        assert response.status_code == 200 and response.json() == {'ok': True}
    row = json.loads((tmp_path/'case1'/'source-window-probe.json').read_text())
    assert row['status'] == 'observed' and row['scoped']['text'] == 1
    assert row['pending_at_close'] == 0 and row['coverage'] == 'partial'
    assert row['schema'] == 'dmb_negative_retrieval_source_window_v7' and row['owner_provenance'] == provenance
    assert row['pdf_discovery']['scoped'] == 1
    assert row['pdf_discovery']['owner_provenance'] == source_window.KNOWN_PDF_DISCOVERY_OWNER
    assert row['pdf_source']['scoped'] == 1
    assert row['pdf_source']['owner_provenance'] == source_window.KNOWN_PDF_OWNER
    primary = json.loads((tmp_path/'case1'/'primary-resolution-probe.json').read_text())
    assert (primary['status'],primary['started'],primary['returned'],primary['raised']) == ('observed',1,1,0)
    assert page not in str(primary)
    from evals.negative_retrieval.sql_window import validate_sql_window
    sql_row = json.loads((tmp_path/'case1'/'sql-window-probe.json').read_text())
    assert validate_sql_window(sql_row,'case1')['coverage'] == 'partial'
    assert sql_row['status'] == 'observed' and sql_row['started'] == 2
    assert sql_row['schema'].endswith('_v3')
    assert sum(r['count'] for r in sql_row['calls'] if r['turn']=='scoped') == 2
    assert row['scoped']['text_batch']==2 and row['batch_read']['scoped']==1


def test_source_window_report_exposes_only_valid_partial_diagnostics(tmp_path):
    import copy
    import json
    from evals.negative_retrieval.report import report_case
    row = {'schema': 'dmb_negative_retrieval_source_window_v1', 'case_id': 'case1',
           'window': 'turn_post_v1', 'coverage': 'partial', 'status': 'observed',
           'dispatch_uncertain': False, 'scoped': {'metadata': 1, 'text': 2, 'text_batch': 0},
           'unscoped': {'metadata': 0, 'text': 0, 'text_batch': 0}, 'pending_at_close': 0,
           'late': 0, 'monitor_error': False}
    path = tmp_path/'source-window-probe.json'
    path.write_text(json.dumps(row))
    result = report_case(tmp_path, {'id': 'case1'}, CASE)
    assert result['status'] == 'unproven' and result['partial_source_window'] == row
    for mutate in (lambda x: x.update(coverage='complete'), lambda x: x.update(case_id='other'),
                   lambda x: x['scoped'].update(text=-1), lambda x: x.update(pending_at_close=1),
                   lambda x: x.update(source_text='private')):
        changed = copy.deepcopy(row)
        mutate(changed)
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match='source window'):
            report_case(tmp_path, {'id': 'case1'}, CASE)
    path.unlink()
    assert report_case(tmp_path, {'id': 'case1'}, CASE)['partial_source_window'] is None


def test_source_window_poisoned_when_cleanup_cannot_remove_hook(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from evals.negative_retrieval import source_window
    monkeypatch.setattr(source_window, '_poisoned', False)
    class FakeMonitoring:
        events = SimpleNamespace(PY_START=1)
        def __init__(self): self.owner = None; self.armed = False
        def get_tool(self, slot): return self.owner if slot == 0 else 'occupied'
        def use_tool_id(self, slot, name): self.owner = name
        def register_callback(self, slot, event, callback): pass
        def free_tool_id(self, slot): self.owner = None
        def set_local_events(self, slot, code, events):
            if not events: raise RuntimeError('hook remains active')
            self.armed = True
    fake = FakeMonitoring()
    def source(): pass
    with ThreadPoolExecutor(max_workers=1) as build, monkeypatch.context() as scoped:
        scoped.setattr(source_window.sys, 'monitoring', fake)
        with pytest.raises(source_window.SourceWindowCleanupError):
            with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build) as state:
                pass
        assert fake.armed and state['status'] == 'uncertain' and state['monitor_error']
        with pytest.raises(source_window.SourceWindowCleanupError, match='fresh process'):
            with source_window.observe_source_window(owners={source.__code__: 'text'}, executor=build):
                pytest.fail('poisoned observer must not dispatch')


def test_source_window_provenance_normalizes_only_paths_and_detects_code_changes():
    import hashlib
    import marshal
    import types
    from evals.negative_retrieval.source_window import _normalize_code
    def outer():
        return lambda: 1
    code = outer.__code__
    def relocate(c):
        return c.replace(co_filename='/another/location.py', co_consts=tuple(
            relocate(x) if isinstance(x, types.CodeType) else x for x in c.co_consts))
    def digest(c): return hashlib.sha256(marshal.dumps(_normalize_code(c))).hexdigest()
    assert digest(code) == digest(relocate(code))
    nested = next(x for x in code.co_consts if isinstance(x, types.CodeType))
    altered = nested.replace(co_consts=tuple(2 if x == 1 else x for x in nested.co_consts))
    modified = code.replace(co_consts=tuple(altered if x is nested else x for x in code.co_consts))
    assert digest(code) != digest(modified)


def test_source_window_provenance_uses_actual_expected_owner_files(tmp_path):
    import sys
    from types import SimpleNamespace
    from pathlib import Path
    from evals.negative_retrieval.source_window import _default_owners, _owner_provenance, KNOWN_TEXT_OWNERS
    owners, executor, proof = _default_owners()
    assert proof is not None and len([v for v in owners.values() if v == 'text']) == 2
    if sys.version_info[:3] == (3, 13, 12):
        assert proof == KNOWN_TEXT_OWNERS
    # The normalizer binds code as well as the file: changing code while
    # keeping the same source filename produces a different, unknown proof.
    import dungeonmind
    from dungeonmind.infrastructure.postgres import vnext_sources, vnext_operator_sources
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView as Native
    from dungeonmind.infrastructure.postgres.vnext_operator_sources import _PostgresOperatorSourceView as Operator
    original = Native.get_native_text_source.__code__
    def different(): return 'synthetic'
    changed = different.__code__.replace(co_filename=original.co_filename)
    result = _owner_provenance(vnext_sources, vnext_operator_sources, Path(dungeonmind.__file__).resolve().parent,
                               changed, Operator.get_native_text_source.__code__)
    assert result is not None and result != KNOWN_TEXT_OWNERS
    wrong = SimpleNamespace(__file__=str(tmp_path/'outside.py'), __spec__=SimpleNamespace(origin=str(tmp_path/'outside.py')))
    assert _owner_provenance(wrong, vnext_operator_sources, Path(dungeonmind.__file__).resolve().parent,
                             original, Operator.get_native_text_source.__code__) is None


def test_source_window_bound_text_attempt_affects_only_negative_budget(tmp_path, monkeypatch):
    import copy
    import hashlib
    import json
    from uuid import NAMESPACE_URL, uuid5
    from evals.negative_retrieval import report, fixture_binding, fixture_sources
    from evals.negative_retrieval.source_window import KNOWN_TEXT_OWNERS, KNOWN_APP_OWNERS
    def envelope(body, status=200):
        raw=json.dumps(body).encode()
        return {'http_status':status,'body':body,'raw_body_hex':raw.hex(),'raw_body_sha256':hashlib.sha256(raw).hexdigest()}
    request={'turn_id':'turn','client_thread_id':'thread','message':'Use that idea.',
             'owner_scope':{'world_id':'world'},'surface':{'surface_id':'build','instance_id':'page'}}
    turn={'turn_id':'saved','idempotency_key':str(uuid5(NAMESPACE_URL,'dmb-agent-turn:world:turn')),
          'user_text':request['message'],'lifecycle_status':'completed','provenance':{
              'world_id':'world','surface_id':'build','surface_instance_id':'page'},
          'knowledge_context':{'completion':question_completion('Where?')}}
    history={'world_id':'world','conversation_id':'conversation','turns':[turn]}
    trace={'world_id':'world','turn_id':'saved','attempts':[{'schema':'dmb_turn_context_trace_v1',
           'world_id':'world','conversation_id':'conversation','turn_id':'saved',
           'terminal_status':'completed','capture_status':'complete','observations':[]}]}
    artifacts={'request':request,'history-before':envelope(history),'history-after':envelope(history),
               'context-trace':envelope(trace),'terminal':{'status':'observed','error_type':None},
               'answer-http':envelope({'turn_id':'turn','client_thread_id':'thread',
               'knowledge_context':turn['knowledge_context']}),'fixture-sources':{'before':[]},'fixture-pin':{},
               'related-page-probe':{'schema':'dmb_negative_retrieval_related_page_probe_v1','coverage':'partial',
               'case_id':'case1','status':'observed','window':'turn_post_v1','records':[]},
               'native-graph-probe':{'schema':'dmb_negative_retrieval_native_graph_probe_v1','coverage':'partial',
               'case_id':'case1','status':'observed','window':'turn_post_v1','records':[]}}
    for name,value in artifacts.items():(tmp_path/(name+'.json')).write_text(json.dumps(value))
    monkeypatch.setattr(report,'verify_fixture_pin',lambda *a: True)
    monkeypatch.setattr(fixture_sources,'verify_related_record',lambda *a: True)
    monkeypatch.setattr(fixture_sources,'related_trace_labels',lambda *a: {})
    monkeypatch.setattr(fixture_binding,'verify_fixture',lambda *a: True)
    row={'schema':'dmb_negative_retrieval_source_window_v2','case_id':'case1','window':'turn_post_v1',
         'coverage':'partial','status':'observed','dispatch_uncertain':False,'scoped':{'metadata':0,'text':1,'text_batch':0},
         'unscoped':{'metadata':0,'text':0,'text_batch':0},'pending_at_close':0,'late':0,'monitor_error':False,
         'owner_provenance':copy.deepcopy(KNOWN_TEXT_OWNERS)}
    path=tmp_path/'source-window-probe.json';fixture={'id':'case1','request':request['message']}
    def assess_row(value, rubric=CASE):
        path.write_text(json.dumps(value))
        return report.report_case(tmp_path,fixture,rubric)
    got=assess_row(row)
    assert got['fixture_context_verified'] is True and got['checks']['unexpected_retrieval'] is False
    assert got['status']=='unproven' and got['capture_environment_verified'] is None
    positive={**CASE,'required_reads':['ledger'],'allowed_reads':['ledger']}
    got=assess_row(row,positive)
    assert got['checks']['required_evidence'] is None and got['checks']['unexpected_retrieval'] is None
    from evals.negative_retrieval.source_window import KNOWN_BATCH_CODE
    batch=copy.deepcopy(row);batch['schema']='dmb_negative_retrieval_source_window_v3'
    batch['scoped']['text']=0;batch['scoped']['text_batch']=1
    batch['batch_read']={'scoped':1,'unscoped':0,'code_sha256':KNOWN_BATCH_CODE}
    got=assess_row(batch)
    assert got['checks']['unexpected_retrieval'] is False and got['status']=='unproven'
    got=assess_row(batch,positive)
    assert got['checks']['required_evidence'] is None and got['checks']['unexpected_retrieval'] is None
    app=copy.deepcopy(batch);app['schema']='dmb_negative_retrieval_source_window_v4'
    app['scoped']['text_batch']=0;app['batch_read']['scoped']=0
    app['app_source']={'scoped':{'app_single':1,'app_revision':0},
                       'unscoped':{'app_single':0,'app_revision':0},
                       'owner_provenance':copy.deepcopy(KNOWN_APP_OWNERS)}
    assert assess_row(app)['checks']['unexpected_retrieval'] is False
    assert assess_row(app,positive)['checks']['required_evidence'] is None
    malformed_app=copy.deepcopy(app);malformed_app['app_source']['private_argument']='must not retain'
    with pytest.raises(ValueError, match='App source window'):
        assess_row(malformed_app)
    malformed_app=copy.deepcopy(app);malformed_app['app_source']['scoped']['app_single']=True
    with pytest.raises(ValueError, match='App source window'):
        assess_row(malformed_app)
    from evals.negative_retrieval.source_window import KNOWN_APP_BATCH_CODE
    app_batch=copy.deepcopy(app);app_batch['schema']='dmb_negative_retrieval_source_window_v5'
    app_batch['app_source']['scoped']['app_single']=0
    app_batch['app_batch_read']={'scoped':1,'unscoped':0,'scoped_starts':2,'unscoped_starts':0,
                                'code_sha256':KNOWN_APP_BATCH_CODE}
    assert assess_row(app_batch)['checks']['unexpected_retrieval'] is False
    assert assess_row(app_batch,positive)['checks']['required_evidence'] is None
    from evals.negative_retrieval.source_window import KNOWN_PDF_OWNER
    pdf=copy.deepcopy(app_batch);pdf['schema']='dmb_negative_retrieval_source_window_v6'
    pdf['app_batch_read']['scoped']=0
    pdf['pdf_source']={'scoped':1,'unscoped':0,'owner_provenance':copy.deepcopy(KNOWN_PDF_OWNER)}
    assert assess_row(pdf)['checks']['unexpected_retrieval'] is False
    assert assess_row(pdf,positive)['checks']['required_evidence'] is None
    # New records retain all prior v5 attribution paths.
    text_v6=copy.deepcopy(pdf);text_v6['pdf_source']['scoped']=0;text_v6['scoped']['text']=1
    assert assess_row(text_v6)['checks']['unexpected_retrieval'] is False
    app_v6=copy.deepcopy(pdf);app_v6['pdf_source']['scoped']=0;app_v6['app_batch_read']['scoped']=1
    assert assess_row(app_v6)['checks']['unexpected_retrieval'] is False
    pdf_unknown=copy.deepcopy(pdf);pdf_unknown['pdf_source']['owner_provenance']['code_sha256']='0'*64
    assert assess_row(pdf_unknown)['checks']['unexpected_retrieval'] is None
    pdf_inactive=copy.deepcopy(pdf);pdf_inactive['pdf_source']['scoped']=0
    assert assess_row(pdf_inactive)['checks']['unexpected_retrieval'] is None
    pdf_foreign=copy.deepcopy(pdf);pdf_foreign['pdf_source']['unscoped']=1
    with pytest.raises(ValueError,match='unresolved work'):
        assess_row(pdf_foreign)
    pdf_unstarted=copy.deepcopy(pdf);pdf_unstarted['status']='not_started'
    with pytest.raises(ValueError,match='Unstarted source window'):
        assess_row(pdf_unstarted)
    pdf_malformed=copy.deepcopy(pdf);pdf_malformed['pdf_source']['payload']='private'
    with pytest.raises(ValueError,match='PDF source window'):
        assess_row(pdf_malformed)
    from evals.negative_retrieval.source_window import KNOWN_PDF_DISCOVERY_OWNER
    discovery=copy.deepcopy(pdf);discovery['schema']='dmb_negative_retrieval_source_window_v7'
    discovery['pdf_source']['scoped']=0
    discovery['pdf_discovery']={'scoped':1,'unscoped':0,'scoped_starts':1,'unscoped_starts':0,
                                'owner_provenance':copy.deepcopy(KNOWN_PDF_DISCOVERY_OWNER)}
    got=assess_row(discovery)
    assert got['checks']['catalog_budget'] is False and got['status']=='unproven'
    assert assess_row(discovery,positive)['checks']['required_evidence'] is None
    # Native discovery can overlap the PDF listing; the lower bounds are not added.
    artifacts['native-graph-probe']['records']=[{'owner':'native_corpus_discovery','state':'returned'}]
    (tmp_path/'native-graph-probe.json').write_text(json.dumps(artifacts['native-graph-probe']))
    assert assess_row(discovery,{**CASE,'max_catalog_discoveries':1})['checks']['catalog_budget'] is None
    artifacts['native-graph-probe']['records']=[]
    (tmp_path/'native-graph-probe.json').write_text(json.dumps(artifacts['native-graph-probe']))
    unknown=copy.deepcopy(discovery);unknown['pdf_discovery']['owner_provenance']['code_sha256']='0'*64
    assert assess_row(unknown)['checks']['catalog_budget'] is None
    inactive=copy.deepcopy(discovery);inactive['pdf_discovery']['scoped']=0
    assert assess_row(inactive)['checks']['catalog_budget'] is None
    foreign=copy.deepcopy(discovery);foreign['pdf_discovery']['unscoped_starts']=1
    with pytest.raises(ValueError,match='unresolved work'): assess_row(foreign)
    unstarted=copy.deepcopy(discovery);unstarted['status']='not_started'
    with pytest.raises(ValueError,match='Unstarted source window'): assess_row(unstarted)
    malformed=copy.deepcopy(discovery);malformed['pdf_discovery']['scoped']=2
    with pytest.raises(ValueError,match='PDF discovery window'): assess_row(malformed)
    # v7 continues to recognize body attempts independently of discovery.
    body=copy.deepcopy(discovery);body['pdf_discovery']['scoped']=0;body['pdf_source']['scoped']=1
    assert assess_row(body)['checks']['unexpected_retrieval'] is False
    page = '# Synthetic'
    digest = hashlib.sha256(page.encode()).hexdigest()
    fixture['page'] = page
    request['primary_work'] = {'object_id':'page','expected_revision':1,'expected_content_sha256':digest}
    (tmp_path/'request.json').write_text(json.dumps(request))
    before = {'world_id':'world','document_id':'page','registry_revision':1,'content_sha256':digest}
    primary = {'schema':'dmb_negative_retrieval_primary_page_v1','case_id':'case1',
               'status':'stable','before':before,'after':dict(before),'error_type':None}
    primary_path = tmp_path/'primary-page-stability.json'
    def with_primary(value):
        primary_path.write_text(json.dumps(value))
        return assess_row(discovery)
    assert with_primary(primary)['checks']['no_premature_mutation'] is None
    changed_primary=copy.deepcopy(primary);changed_primary['status']='changed';changed_primary['after']['registry_revision']=2
    assert with_primary(changed_primary)['checks']['no_premature_mutation'] is False
    malformed=copy.deepcopy(changed_primary);malformed['after']['document_id']='other'
    with pytest.raises(ValueError,match='not bound'): with_primary(malformed)
    incomplete=copy.deepcopy(primary);incomplete['status']='unavailable';incomplete['after']=None;incomplete['error_type']='RuntimeError'
    assert with_primary(incomplete)['checks']['no_premature_mutation'] is None
    primary_path.unlink()
    primary_probe={'schema':'dmb_negative_retrieval_primary_resolution_v1','case_id':'case1',
        'window':'turn_post_v1','coverage':'partial','status':'observed','started':1,'returned':1,'raised':0,'pending_at_close':0}
    primary_probe_path=tmp_path/'primary-resolution-probe.json'
    primary_probe_path.write_text(json.dumps(primary_probe))
    result=assess_row(discovery)
    assert result['primary_resolution_probe']['returned']==1
    assert result['checks']['unexpected_retrieval'] is None
    assert result['checks']['catalog_budget'] is False  # PDF discovery, not the primary resolver.
    invalid=copy.deepcopy(primary_probe);invalid['returned']=2
    primary_probe_path.write_text(json.dumps(invalid))
    with pytest.raises(ValueError,match='Invalid primary-work'):assess_row(discovery)
    primary_probe_path.unlink()
    assert assess_row(discovery)['primary_resolution_probe'] is None
    sql_row={'schema':'dmb_negative_retrieval_sql_window_v1','case_id':'case1','window':'turn_post_v1',
        'coverage':'partial','status':'observed','started':1,'returned':1,'raised':0,'pending_at_close':0,
        'resumed_unknown':0,'overflow':0,'dropped_starts':0,'monitor_error':False,'unsupported_apis':0,
        'calls':[{'scope':'app','api':'execute','source_sha256':'a'*64,'code_sha256':'b'*64,'line':42,'count':1}]}
    sql_path=tmp_path/'sql-window-probe.json';sql_path.write_text(json.dumps(sql_row))
    result=assess_row(discovery)
    assert result['sql_window_probe']['started']==1 and result['checks']['unexpected_retrieval'] is None
    bad=copy.deepcopy(sql_row);bad['calls'][0]['count']=2;sql_path.write_text(json.dumps(bad))
    with pytest.raises(ValueError,match='Inconsistent SQL window'):assess_row(discovery)
    from evals.negative_retrieval.sql_source_classification import _KNOWN_RUNTIME, _PAGE_INVENTORY, _PAGES
    v2=copy.deepcopy(sql_row);v2['schema']='dmb_negative_retrieval_sql_window_v2';v2['runtime']=copy.deepcopy(_KNOWN_RUNTIME)
    v2['calls'][0].update(source_sha256=sorted(_PAGES)[0],code_sha256=_PAGE_INVENTORY,line=512)
    sql_path.write_text(json.dumps(v2)); classified=assess_row(discovery)
    assert classified['sql_source_classification']['observed_attempts']['page_inventory_attempts']==1
    assert classified['checks']['unexpected_retrieval'] is None and classified['status']=='unproven'
    # Only v3 turn-scoped inventory calls can establish a discovery lower bound.
    v3=copy.deepcopy(v2);v3['schema']='dmb_negative_retrieval_sql_window_v3'
    v3['calls'][0]['turn']='scoped';sql_path.write_text(json.dumps(v3))
    no_pdf=copy.deepcopy(discovery);no_pdf['pdf_discovery']['scoped']=0
    assert assess_row(no_pdf)['checks']['catalog_budget'] is False
    assert assess_row(no_pdf,positive)['checks']['required_evidence'] is None
    v3['calls'][0]['turn']='unscoped';sql_path.write_text(json.dumps(v3))
    assert assess_row(no_pdf)['checks']['catalog_budget'] is None
    v3['calls'][0]['turn']='scoped';v3['status']='uncertain';v3['monitor_error']=True
    sql_path.write_text(json.dumps(v3))
    assert assess_row(no_pdf)['checks']['catalog_budget'] is None
    v3['status']='observed';v3['monitor_error']=False
    v3['runtime']['version']=[3,13,13];sql_path.write_text(json.dumps(v3))
    assert assess_row(no_pdf)['checks']['catalog_budget'] is None
    v3['runtime']=copy.deepcopy(_KNOWN_RUNTIME);sql_path.write_text(json.dumps(v3))
    artifacts['native-graph-probe']['records']=[{'owner':'native_corpus_discovery','state':'returned'}]
    (tmp_path/'native-graph-probe.json').write_text(json.dumps(artifacts['native-graph-probe']))
    assert assess_row(no_pdf,{**CASE,'max_catalog_discoveries':1})['checks']['catalog_budget'] is None
    artifacts['native-graph-probe']['records']=[]
    (tmp_path/'native-graph-probe.json').write_text(json.dumps(artifacts['native-graph-probe']))
    unscoped_window=copy.deepcopy(no_pdf);unscoped_window['status']='uncertain'
    assert assess_row(unscoped_window)['checks']['catalog_budget'] is None
    def bad_pin(*args): raise ValueError('unbound')
    monkeypatch.setattr(report,'verify_fixture_pin',bad_pin)
    assert assess_row(no_pdf)['checks']['catalog_budget'] is None
    monkeypatch.setattr(report,'verify_fixture_pin',lambda *a: True)
    sql_path.unlink()
    assert assess_row(discovery)['sql_window_probe'] is None
    empty=copy.deepcopy(app_batch);empty['app_batch_read']['scoped']=0
    assert assess_row(empty)['checks']['unexpected_retrieval'] is None
    changed=copy.deepcopy(app_batch);changed['app_batch_read']['code_sha256']='0'*64
    assert assess_row(changed)['checks']['unexpected_retrieval'] is None
    bad=copy.deepcopy(app_batch);bad['app_batch_read']['scoped']=3
    with pytest.raises(ValueError,match='App batch window'):
        assess_row(bad)
    foreign=copy.deepcopy(app_batch);foreign['app_batch_read']['unscoped_starts']=1
    with pytest.raises(ValueError,match='unresolved work'):
        assess_row(foreign)
    unknown=copy.deepcopy(app);unknown['app_source']['owner_provenance']['app_single']='0'*64
    assert assess_row(unknown)['checks']['unexpected_retrieval'] is None
    inactive=copy.deepcopy(app);inactive['app_source']['scoped']['app_single']=0
    assert assess_row(inactive)['checks']['unexpected_retrieval'] is None
    uncertain=copy.deepcopy(app);uncertain['status']='uncertain'
    assert assess_row(uncertain)['checks']['unexpected_retrieval'] is None
    unscoped=copy.deepcopy(app);unscoped['app_source']['unscoped']['app_single']=1
    with pytest.raises(ValueError, match='unresolved work'):
        assess_row(unscoped)
    unstarted=copy.deepcopy(app);unstarted['status']='not_started'
    with pytest.raises(ValueError, match='Unstarted source window'):
        assess_row(unstarted)
    for field,value in (('scoped',0),('code_sha256','0'*64),('code_sha256',None)):
        value_row=copy.deepcopy(batch);value_row['batch_read'][field]=value
        if field=='code_sha256' and value is None:value_row['batch_read']['scoped']=0
        assert assess_row(value_row)['checks']['unexpected_retrieval'] is None
    malformed=copy.deepcopy(batch);malformed['batch_read']['private_argument']='must not retain'
    with pytest.raises(ValueError,match='source window'):
        assess_row(malformed)
    malformed=copy.deepcopy(batch);malformed['batch_read']['scoped']=2
    with pytest.raises(ValueError,match='source window'):
        assess_row(malformed)
    for change in ('legacy','unknown_provenance','different_code','different_source','different_python','uncertain','pending','dispatch','zero','metadata','batch'):
        value=copy.deepcopy(row)
        if change=='legacy':value['schema']='dmb_negative_retrieval_source_window_v1';value.pop('owner_provenance')
        elif change=='unknown_provenance':value['owner_provenance']=None
        elif change=='different_code':value['owner_provenance']['native']['code_sha256']='0'*64
        elif change=='different_source':value['owner_provenance']['operator']['source_sha256']='0'*64
        elif change=='different_python':value['owner_provenance']['version']=[3,13,18]
        elif change=='uncertain':value['status']='uncertain';value['unscoped']['text']=1
        elif change=='pending':value['status']='uncertain';value['pending_at_close']=1
        elif change=='dispatch':value['dispatch_uncertain']=True
        elif change=='zero':value['scoped']['text']=0
        elif change=='metadata':value['scoped']['text']=0;value['scoped']['metadata']=1
        elif change=='batch':value['scoped']['text']=0;value['scoped']['text_batch']=1
        assert assess_row(value)['checks']['unexpected_retrieval'] is None, change
    # Contradictory, missing or uncertain capture windows cannot attribute an
    # otherwise recognized event to this turn.
    for name, field, value in (('native-graph-probe','window',None),
                               ('native-graph-probe','status','dispatch_uncertain'),
                               ('related-page-probe','status','not_started'),
                               ('terminal','status','outcome_unknown'),
                               ('terminal','error_type','RuntimeError')):
        changed=copy.deepcopy(artifacts[name]);changed[field]=value
        (tmp_path/(name+'.json')).write_text(json.dumps(changed))
        assert assess_row(row)['checks']['unexpected_retrieval'] is None, (name, field, value)
        (tmp_path/(name+'.json')).write_text(json.dumps(artifacts[name]))
    for name in ('native-graph-probe','related-page-probe','terminal'):
        (tmp_path/(name+'.json')).unlink()
        result=assess_row(row)
        assert result['status']=='unproven' and ('checks' not in result or result['checks']['unexpected_retrieval'] is None), name
        (tmp_path/(name+'.json')).write_text(json.dumps(artifacts[name]))
    artifacts['answer-http']=envelope({'turn_id':'turn','client_thread_id':'thread'},status=503)
    (tmp_path/'answer-http.json').write_text(json.dumps(artifacts['answer-http']))
    assert assess_row(row)['checks']['unexpected_retrieval'] is None
    artifacts['answer-http']=envelope({'turn_id':'turn','client_thread_id':'thread','knowledge_context':turn['knowledge_context']})
    (tmp_path/'answer-http.json').write_text(json.dumps(artifacts['answer-http']))
    monkeypatch.setattr(fixture_binding,'verify_fixture',lambda *a: (_ for _ in ()).throw(ValueError('unbound')))
    assert assess_row(row)['checks']['unexpected_retrieval'] is None
    monkeypatch.setattr(fixture_binding,'verify_fixture',lambda *a: True)
    # Another owner may witness the same read; preserve one unmapped lower
    # bound, not a fabricated count of distinct reads.
    artifacts['native-graph-probe']['records']=[{'owner':'native_graph_body_open','state':'returned'}]
    (tmp_path/'native-graph-probe.json').write_text(json.dumps(artifacts['native-graph-probe']))
    original_assess=report.assess; seen=[]
    def recording_assess(case, observed):
        seen.append(list(observed['reads']))
        return original_assess(case,observed)
    monkeypatch.setattr(report,'assess',recording_assess)
    assert assess_row(row)['checks']['unexpected_retrieval'] is False
    from evals.negative_retrieval.trace_observation import UNKNOWN
    assert seen[-1].count(UNKNOWN)==1
    assert assess_row(app)['checks']['unexpected_retrieval'] is False
    assert seen[-1].count(UNKNOWN)==1
    assert assess_row(app_batch)['checks']['unexpected_retrieval'] is False
    assert seen[-1].count(UNKNOWN)==1
    artifacts['native-graph-probe']['records']=[{'owner':'native_pdf_source_load','state':'returned'}]
    (tmp_path/'native-graph-probe.json').write_text(json.dumps(artifacts['native-graph-probe']))
    assert assess_row(pdf)['checks']['unexpected_retrieval'] is False
    assert seen[-1].count(UNKNOWN)==1
    trace['attempts'][0]['turn_id']='foreign'
    (tmp_path/'context-trace.json').write_text(json.dumps(envelope(trace)))
    with pytest.raises(ValueError,match='another turn'):
        assess_row(row)


def test_source_window_provenance_detects_file_change_with_same_loaded_code(tmp_path):
    from types import SimpleNamespace
    from evals.negative_retrieval.source_window import _owner_provenance, KNOWN_TEXT_OWNERS
    root=tmp_path/'dungeonmind';directory=root/'infrastructure'/'postgres';directory.mkdir(parents=True)
    native=directory/'vnext_sources.py';operator=directory/'vnext_operator_sources.py'
    source='def source_view():\n    return 1\n'
    native.write_text(source);operator.write_text(source)
    def loaded(path):
        namespace={};exec(compile(source,str(path),'exec'),namespace);return namespace['source_view'].__code__
    native_code,operator_code=loaded(native),loaded(operator)
    def module(path):return SimpleNamespace(__file__=str(path),__spec__=SimpleNamespace(origin=str(path)))
    before=_owner_provenance(module(native),module(operator),root,native_code,operator_code)
    assert before is not None and before != KNOWN_TEXT_OWNERS
    native.write_text('def source_view():\n    return 2\n')
    after=_owner_provenance(module(native),module(operator),root,native_code,operator_code)
    assert after is not None and after['native']['source_sha256'] != before['native']['source_sha256']
    assert after['native']['code_sha256'] == before['native']['code_sha256']


def test_source_window_provenance_v2_rejects_extra_private_fields():
    import copy
    from evals.negative_retrieval.source_window import validate_artifact, KNOWN_TEXT_OWNERS
    row={'schema':'dmb_negative_retrieval_source_window_v2','case_id':'case1','window':'turn_post_v1',
         'coverage':'partial','status':'observed','dispatch_uncertain':False,
         'scoped':{'metadata':0,'text':1,'text_batch':0},'unscoped':{'metadata':0,'text':0,'text_batch':0},
         'pending_at_close':0,'late':0,'monitor_error':False,'owner_provenance':copy.deepcopy(KNOWN_TEXT_OWNERS)}
    assert validate_artifact(row,'case1') == row
    for field,value in (('source_path','private'),('code_sha256','bad')):
        changed=copy.deepcopy(row);changed['owner_provenance']['native'][field]=value
        with pytest.raises(ValueError,match='source window'):
            validate_artifact(changed,'case1')


def test_source_window_default_provenance_is_bound_to_registered_core_owner():
    import sys
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from evals.negative_retrieval.source_window import observe_source_window, KNOWN_TEXT_OWNERS
    class NoDatabase:
        def transaction(self): raise RuntimeError('synthetic sentinel')
    view=_PostgresNativeTextSourceView(NoDatabase(),'synthetic',1)
    with observe_source_window() as state:
        with pytest.raises(RuntimeError,match='synthetic sentinel'):
            view.get_native_text_source(source_artifact_id='synthetic',source_revision_id='synthetic',span_id='synthetic')
    assert state['status']=='observed' and state['scoped']['text']==1
    assert state['owner_provenance'] is not None and state['coverage']=='partial'
    if sys.version_info[:3]==(3,13,12):assert state['owner_provenance']==KNOWN_TEXT_OWNERS


def test_source_window_batch_real_owner_skips_empty_and_records_attempt():
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from evals.negative_retrieval.source_window import observe_source_window, KNOWN_BATCH_CODE, KNOWN_TEXT_OWNERS
    class NoDatabase:
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args, **kwargs): raise RuntimeError('synthetic sentinel')
    view=_PostgresNativeTextSourceView(NoDatabase(),'synthetic',1)
    with observe_source_window() as state:
        assert view.get_native_text_sources([])==()
        with pytest.raises(RuntimeError,match='synthetic sentinel'):
            view.get_native_text_sources([('synthetic','synthetic','synthetic')])
    assert state['status']=='observed' and state['owner_provenance']==KNOWN_TEXT_OWNERS
    assert state['scoped']['text_batch']==2
    assert state['batch_read']=={'scoped':1,'unscoped':0,'code_sha256':KNOWN_BATCH_CODE}


def test_source_window_batch_unknown_code_is_diagnostic(monkeypatch):
    from evals.negative_retrieval import source_window
    original=source_window._default_owners
    owners,executor,provenance=original()
    batch=next(code for code,kind in owners.items() if kind=='text_batch')
    altered=batch.replace(co_name='changed')
    modified={altered if code is batch else code:kind for code,kind in owners.items()}
    monkeypatch.setattr(source_window,'_default_owners',lambda:(modified,executor,provenance))
    with source_window.observe_source_window() as state:pass
    assert state['batch_read']=={'scoped':0,'unscoped':0,'code_sha256':None}


def test_source_window_batch_unscoped_thread_marks_window_uncertain():
    from concurrent.futures import ThreadPoolExecutor
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from evals.negative_retrieval.source_window import observe_source_window
    class NoDatabase:
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args, **kwargs): raise RuntimeError('synthetic sentinel')
    view=_PostgresNativeTextSourceView(NoDatabase(),'synthetic',1)
    def call():
        with pytest.raises(RuntimeError,match='synthetic sentinel'):
            view.get_native_text_sources([('synthetic','synthetic','synthetic')])
    with ThreadPoolExecutor(max_workers=1) as other:
        with observe_source_window() as state:
            other.submit(call).result()
    assert state['status']=='uncertain'
    assert state['unscoped']['text_batch']==1 and state['batch_read']['unscoped']==1


def test_source_window_batch_successful_transaction_counts_once():
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from evals.negative_retrieval.source_window import observe_source_window, KNOWN_BATCH_CODE
    class EmptyDatabase:
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args, **kwargs): return self
        def fetchall(self): return []
    view=_PostgresNativeTextSourceView(EmptyDatabase(),'synthetic',1)
    with observe_source_window() as state:
        assert view.get_native_text_sources([('synthetic','synthetic','synthetic')])==(None,)
    assert state['status']=='observed' and state['scoped']['text_batch']==1
    assert state['batch_read']=={'scoped':1,'unscoped':0,'code_sha256':KNOWN_BATCH_CODE}


def test_source_window_batch_failure_before_sql_stays_unknown():
    from dungeonmind.infrastructure.postgres.vnext_sources import _PostgresNativeTextSourceView
    from evals.negative_retrieval.source_window import observe_source_window
    class NoDatabase:
        def transaction(self): raise RuntimeError('before SQL')
    view=_PostgresNativeTextSourceView(NoDatabase(),'synthetic',1)
    with observe_source_window() as state:
        with pytest.raises(RuntimeError,match='before SQL'):
            view.get_native_text_sources([('synthetic','synthetic','synthetic')])
    assert state['scoped']['text_batch']==1 and state['batch_read']['scoped']==0


def test_app_source_batch_probe_records_nonempty_attempts_and_restores_owner(monkeypatch):
    from application_state.source import repository
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records
    calls = []
    def read(conn, *, bindings):
        calls.append(bindings)
        if bindings == [('raise', 'digest')]:
            raise ValueError('private detail')
        return ['private source'] if bindings else []
    monkeypatch.setattr(repository, 'get_source_markdown_batch', read)
    with observe_native_graph_owners() as records:
        assert repository.get_source_markdown_batch(None, bindings=[]) == []
        assert repository.get_source_markdown_batch(None, bindings=[('source', 'digest')]) == ['private source']
        with pytest.raises(ValueError):
            repository.get_source_markdown_batch(None, bindings=[('raise', 'digest')])
    assert records == [{'owner': 'app_source_body_read_batch', 'state': 'returned'},
                       {'owner': 'app_source_body_read_batch', 'state': 'raised'}]
    assert summarize_records(records)['app_source_body_read_batch'] == {'entered': 0, 'returned': 1, 'raised': 1}
    assert summarize_records([])['app_source_body_read_batch'] is None
    assert repository.get_source_markdown_batch is read
    assert len(calls) == 3


def test_app_source_batch_probe_wraps_real_repository_query_boundary():
    from application_state.source import repository
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners
    class Cursor:
        def __init__(self): self.executed = 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query, params): self.executed += 1
        def fetchall(self): return []
    class Connection:
        def __init__(self): self.cur = Cursor()
        def cursor(self, **kwargs): return self.cur
    conn = Connection()
    original = repository.get_source_markdown_batch
    with observe_native_graph_owners() as records:
        assert repository.get_source_markdown_batch(conn, bindings=[]) == []
        assert conn.cur.executed == 0 and records == []
        assert repository.get_source_markdown_batch(conn, bindings=[('source', 'digest')]) == []
        assert conn.cur.executed == 1
    assert records == [{'owner': 'app_source_body_read_batch', 'state': 'returned'}]
    assert repository.get_source_markdown_batch is original


def test_app_source_revision_probe_wraps_real_repository_query_boundary():
    from uuid import uuid4
    from application_state.source import repository
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records
    class Cursor:
        def __init__(self): self.executed = 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query, params): self.executed += 1
        def fetchone(self): return None
    class Connection:
        def __init__(self): self.cur = Cursor()
        def cursor(self, **kwargs): return self.cur
    conn = Connection()
    original = repository.get_source_markdown_by_revision_id
    with observe_native_graph_owners() as records:
        assert repository.get_source_markdown_by_revision_id(conn, uuid4()) is None
        assert conn.cur.executed == 1
    assert records == [{'owner': 'app_source_body_read_revision', 'state': 'returned'}]
    assert summarize_records([])['app_source_body_read_revision'] is None
    assert repository.get_source_markdown_by_revision_id is original


def test_source_window_observes_prebound_app_aliases_under_outer_probe():
    from uuid import uuid4
    from application_state.source import repository
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners
    from evals.negative_retrieval.source_window import observe_source_window, KNOWN_APP_OWNERS
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query, params): pass
        def fetchone(self): return None
    class Connection:
        def cursor(self, **kwargs): return Cursor()
    # These references are intentionally captured before the wrapper is installed.
    single = repository.get_source_markdown
    revision = repository.get_source_markdown_by_revision_id
    with observe_native_graph_owners() as records:
        with observe_source_window() as state:
            assert single(Connection(), source_artifact_id='private', content_sha256='private') is None
            assert revision(Connection(), uuid4()) is None
        assert records == []
    assert state['status'] == 'observed'
    assert state['app_source']['scoped'] == {'app_single': 1, 'app_revision': 1}
    assert state['app_source']['unscoped'] == {'app_single': 0, 'app_revision': 0}
    assert state['app_source']['owner_provenance'] == KNOWN_APP_OWNERS
    assert repository.get_source_markdown is single
    assert repository.get_source_markdown_by_revision_id is revision


def test_source_window_scopes_app_alias_in_executor_and_marks_foreign_thread_uncertain():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Thread
    from evals.negative_retrieval.source_window import observe_source_window
    def app_source(): return 'private'
    with ThreadPoolExecutor(max_workers=1) as executor:
        with observe_source_window(owners={app_source.__code__: 'app_single'}, executor=executor) as state:
            assert executor.submit(app_source).result() == 'private'
            foreign = Thread(target=app_source)
            foreign.start()
            foreign.join()
    assert state['app_source']['scoped']['app_single'] == 1
    assert state['app_source']['unscoped']['app_single'] == 1
    assert state['status'] == 'uncertain'
    assert state['app_source']['owner_provenance'] is None


def test_source_window_observes_prebound_app_batch_only_after_empty_guard():
    from application_state.source import repository
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners
    from evals.negative_retrieval.source_window import observe_source_window, KNOWN_APP_BATCH_CODE
    class Cursor:
        def __init__(self): self.executed = 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query, params): self.executed += 1
        def fetchall(self): return []
    class Connection:
        def __init__(self): self.cur = Cursor()
        def cursor(self, **kwargs): return self.cur
    class Uncheckable:
        def __bool__(self): raise ValueError('private')
    batch = repository.get_source_markdown_batch
    conn = Connection()
    with observe_native_graph_owners() as records:
        with observe_source_window() as state:
            assert batch(conn, bindings=[]) == []
            assert batch(conn, bindings=[('one', 'digest'), ('two', 'digest')]) == []
            with pytest.raises(ValueError): batch(conn, bindings=Uncheckable())
        assert records == []
    assert conn.cur.executed == 1
    assert state['app_batch_read'] == {'scoped': 1, 'unscoped': 0, 'scoped_starts': 3,
                                      'unscoped_starts': 0, 'code_sha256': KNOWN_APP_BATCH_CODE}
    assert state['status'] == 'observed'
    assert repository.get_source_markdown_batch is batch


def test_mixed_current_page_regression_flags_world_search_without_claiming_complete_capture():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / 'evals/negative_retrieval/fixtures'
    public = json.loads((root / 'development.json').read_text())
    private = json.loads((root / 'development-private.json').read_text())
    case = next(row for row in public['cases'] if row['id'] == 'dev-mixed-current-page')
    rubric = private['cases'][case['id']]
    assert 'recurring reminder' in case['request'] and 'saved current page' in case['request']
    from evals.negative_retrieval.trace_observation import UNKNOWN
    assert assess(rubric, observation(outcome='answer', reads=[UNKNOWN], journal_complete=False))['checks']['unexpected_retrieval'] is None
    assert assess(rubric, observation(outcome='answer', reads=['harbour'], journal_complete=False))['checks']['unexpected_retrieval'] is False
    assert assess(rubric, observation(outcome='answer', graph_query_attempts=1,
                                      graph_query_journal_complete=False))['checks']['graph_query_budget'] is False
    assert assess(rubric, observation(outcome='answer', graph_query_attempts=0,
                                      graph_query_journal_complete=False))['checks']['graph_query_budget'] is None


def test_current_page_partial_regression_requires_support_and_specific_gap_judgment():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / 'evals/negative_retrieval/fixtures'
    public = json.loads((root / 'development.json').read_text())
    private = json.loads((root / 'development-private.json').read_text())
    case, = (row for row in public['cases'] if row['id'] == 'dev-current-page-partial')
    rubric = private['cases'][case['id']]
    assert rubric['required_reads'] == rubric['allowed_reads'] == ['current-page']
    assert rubric['max_catalog_discoveries'] == rubric['max_graph_query_attempts'] == 0
    good = dict(outcome='answer', reads=['current-page'], required_support=True,
        graph_query_attempts=0, graph_query_journal_complete=True)
    assert assess(rubric, observation(**good))['status'] == 'pass'
    # The independent reviewer rejects the generic-only limitation seen in case 307.
    assert assess(rubric, observation(**(good | {'semantic_quality': False})))['status'] == 'fail'
    assert assess(rubric, observation(**(good | {'journal_complete': False})))['status'] == 'unproven'
    assert assess(rubric, observation(**(good | {'reads': ['current-page', 'irrelevant']})))['status'] == 'fail'


def test_pdf_probe_counts_loader_not_rejected_locator_and_restores_aliases(monkeypatch):
    import json
    from types import SimpleNamespace
    from apps.live_control_server.services import native_graph_reads, native_pdf_evidence
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners, summarize_records

    region = {'schema_version': 'dm_native_pdf_region_v1', 'source_revision_id': 'srev:test',
        'content_sha256': 'a' * 64, 'page': 1, 'left': .1, 'top': .2, 'right': .7, 'bottom': .8}
    evidence = SimpleNamespace(source_revision_id='srev:test', source_locator=json.dumps(region))
    invalid = SimpleNamespace(source_revision_id='srev:other', source_locator=json.dumps(region))
    def load(*args, **kwargs):
        return b'private PDF body'
    def open_region(region, **kwargs):
        return kwargs['load']('private source identity')
    monkeypatch.setattr(native_pdf_evidence, 'open_native_pdf_region', open_region)
    graph_original = native_graph_reads.open_admitted_pdf_evidence
    module_original = native_pdf_evidence.open_admitted_pdf_evidence
    with observe_native_graph_owners() as records:
        with pytest.raises(ValueError, match='revision differs'):
            native_graph_reads.open_admitted_pdf_evidence(invalid, space_id='private', load=load)
        assert not records
        assert native_graph_reads.open_admitted_pdf_evidence(evidence, space_id='private', load=load)[1] == b'private PDF body'
        def fail(*args, **kwargs):
            raise RuntimeError('private failure')
        with pytest.raises(RuntimeError, match='private failure'):
            native_pdf_evidence.open_admitted_pdf_evidence(evidence, space_id='private', load=fail)
    assert records == [{'owner': 'native_pdf_source_load', 'state': 'returned'},
                       {'owner': 'native_pdf_source_load', 'state': 'raised'}]
    assert summarize_records([])['native_pdf_source_load'] is None
    assert summarize_records(records)['native_pdf_source_load']['raised'] == 1
    assert 'private' not in str(records)
    assert native_graph_reads.open_admitted_pdf_evidence is graph_original
    assert native_pdf_evidence.open_admitted_pdf_evidence is module_original


def test_pdf_probe_observes_real_core_loader_on_missing_source():
    import json
    from types import SimpleNamespace
    from apps.live_control_server.services import native_graph_reads
    from evals.negative_retrieval.native_graph_probe import observe_native_graph_owners
    region = {'schema_version': 'dm_native_pdf_region_v1', 'source_revision_id': 'srev:test',
        'content_sha256': 'a' * 64, 'page': 1, 'left': .1, 'top': .2, 'right': .7, 'bottom': .8}
    evidence = SimpleNamespace(source_revision_id='srev:test', source_locator=json.dumps(region))
    with observe_native_graph_owners() as records:
        with pytest.raises(ValueError, match='Retained PDF unavailable'):
            native_graph_reads.open_admitted_pdf_evidence(evidence, space_id='synthetic', load=lambda *_: None)
    assert records == [{'owner': 'native_pdf_source_load', 'state': 'returned'}]


def test_pdf_source_window_tracks_prebound_repository_code_and_unscoped_thread():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Thread
    from dungeonmind.infrastructure.postgres.vnext_sources import PostgresNativeSourceEvidenceRepository
    from evals.negative_retrieval.source_window import _pdf_source_owner, observe_source_window, KNOWN_PDF_OWNER
    class MissingDatabase:
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args): raise RuntimeError('synthetic transaction failure')
    repo = PostgresNativeSourceEvidenceRepository(MissingDatabase())
    alias = repo.get_native_pdf_source  # Bound before any monitoring.
    owners, proof = _pdf_source_owner()
    assert proof == KNOWN_PDF_OWNER
    def attempt():
        with pytest.raises(RuntimeError, match='synthetic transaction failure'):
            alias('synthetic world', 'synthetic revision')
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(lambda: None).result()
        with observe_source_window(owners=owners, executor=pool) as state:
            pool.submit(attempt).result()
            other = Thread(target=attempt); other.start(); other.join()
    assert state['pdf_source']['scoped'] == 1
    assert state['pdf_source']['unscoped'] == 1
    assert state['status'] == 'uncertain'
    assert 'synthetic world' not in str(state) and 'synthetic revision' not in str(state)


def test_pdf_source_window_records_missing_and_returned_repository_results(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from dungeonmind.infrastructure.postgres import vnext_sources
    from evals.negative_retrieval.source_window import _pdf_source_owner, observe_source_window
    class Database:
        row = None
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args): return self
        def fetchone(self): return self.row
    db = Database()
    repo = vnext_sources.PostgresNativeSourceEvidenceRepository(db)
    alias = repo.get_native_pdf_source
    artifact = SimpleNamespace(source_artifact_id='synthetic-artifact', current_revision_id='synthetic-revision')
    revision = SimpleNamespace(source_artifact_id='synthetic-artifact', source_revision_id='synthetic-revision')
    monkeypatch.setattr(vnext_sources.SourceArtifactV3, 'model_validate', lambda _: artifact)
    monkeypatch.setattr(vnext_sources.SourceRevisionV2, 'model_validate', lambda _: revision)
    owners, _ = _pdf_source_owner()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with observe_source_window(owners=owners, executor=pool) as state:
            assert alias('synthetic', 'synthetic-revision') is None
            db.row = {'source_artifact': {}, 'source_revision': {}, 'page_count': 1, 'body_bytes': b'private pdf'}
            assert alias('synthetic', 'synthetic-revision')[-1] == b'private pdf'
    assert state['pdf_source']['scoped'] == 2 and state['status'] == 'observed'
    assert 'private pdf' not in str(state)


def test_pdf_source_owner_refuses_foreign_code_provenance(monkeypatch):
    from dungeonmind.infrastructure.postgres import vnext_sources
    from evals.negative_retrieval.source_window import _pdf_source_owner, KNOWN_PDF_OWNER
    owners, proof = _pdf_source_owner()
    assert proof == KNOWN_PDF_OWNER and len(owners) == 1
    monkeypatch.setattr(vnext_sources.PostgresNativeSourceEvidenceRepository, 'get_native_pdf_source', lambda *_: None)
    changed, proof = _pdf_source_owner()
    assert len(changed) == 1 and proof is None


def test_pdf_discovery_window_tracks_post_validation_queries_and_prebound_alias(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from dungeonmind.infrastructure.postgres.vnext_sources import PostgresNativeSourceEvidenceRepository
    from evals.negative_retrieval import source_window as sw
    class Database:
        fail_enter = False
        fail_execute = False
        def transaction(self): return self
        def __enter__(self):
            if self.fail_enter: raise RuntimeError('transaction failed')
            return self
        def __exit__(self, *args): return False
        def execute(self, *args):
            if self.fail_execute: raise RuntimeError('query failed')
            return self
        def fetchall(self): return []
    db = Database()
    alias = PostgresNativeSourceEvidenceRepository(db).list_public_native_pdf_revisions
    owners, provenance = sw._pdf_discovery_owner()
    assert provenance == sw.KNOWN_PDF_DISCOVERY_OWNER and len(owners) == 1
    original_owners, _, original_proof = sw._default_owners()
    with ThreadPoolExecutor(max_workers=1) as pool:
        monkeypatch.setattr(sw, '_default_owners', lambda: (original_owners, pool, original_proof))
        with sw.observe_source_window() as state:
            for limit in (0, 101):
                with pytest.raises(ValueError): alias('private value', limit=limit)
            db.fail_enter = True
            with pytest.raises(RuntimeError, match='transaction failed'): alias('private value')
            db.fail_enter = False
            db.fail_execute = True
            with pytest.raises(RuntimeError, match='query failed'): alias('private value')
            db.fail_execute = False
            assert pool.submit(alias, 'private value').result() == []
    assert state['status'] == 'observed'
    assert state['pdf_discovery']['scoped_starts'] == 5
    assert state['pdf_discovery']['scoped'] == 2
    assert 'private value' not in str(state)


def test_pdf_discovery_unscoped_attempt_makes_window_uncertain(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Thread
    from dungeonmind.infrastructure.postgres.vnext_sources import PostgresNativeSourceEvidenceRepository
    from evals.negative_retrieval import source_window as sw
    class Database:
        def transaction(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, *args): return self
        def fetchall(self): return []
    alias = PostgresNativeSourceEvidenceRepository(Database()).list_public_native_pdf_revisions
    owners, _, proof = sw._default_owners()
    with ThreadPoolExecutor(max_workers=1) as pool:
        monkeypatch.setattr(sw, '_default_owners', lambda: (owners, pool, proof))
        with sw.observe_source_window() as state:
            thread = Thread(target=lambda: alias('private value'))
            thread.start(); thread.join()
    assert state['status'] == 'uncertain'
    assert state['pdf_discovery']['unscoped_starts'] == 1
    assert state['pdf_discovery']['unscoped'] == 1


def test_primary_page_observation_reads_committed_owner_and_rejects_bad_snapshot(monkeypatch):
    from hashlib import sha256
    from types import SimpleNamespace
    from apps.live_control_server.services import build_related_pages, workspace_document_registry
    from evals.negative_retrieval.primary_page_stability import inspect_primary_page, expected_primary_page
    body = '# synthetic page'
    digest = sha256(body.encode()).hexdigest()
    work = {'object_id': 'page', 'expected_revision': 3, 'expected_content_sha256': digest}
    row = SimpleNamespace(world_id='world', document_id='page', revision=3)
    snapshot = SimpleNamespace(record=row, markdown=body, content_sha256=digest, loaded_revision=3)
    monkeypatch.setattr(build_related_pages, 'root', lambda: 'synthetic-root')
    monkeypatch.setattr(workspace_document_registry, 'get_committed_page_snapshot',
                        lambda root, page: snapshot if (root, page)==('synthetic-root','page') else None)
    actual = inspect_primary_page('world', work)
    assert actual == expected_primary_page({'page': body}, 'world', work)
    assert body not in str(actual)
    snapshot.content_sha256 = '0'*64
    with pytest.raises(ValueError, match='unavailable or inconsistent'): inspect_primary_page('world', work)
    snapshot.content_sha256 = digest; row.world_id = 'other'
    with pytest.raises(ValueError, match='unavailable or inconsistent'): inspect_primary_page('world', work)


def test_capture_retains_changed_and_failed_primary_postflight(tmp_path, monkeypatch, verified_capture_owner):
    import json
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module
    case = {'id':'case1','question':'Use it.'}
    fixture = {'request':'Use it.','history':[],'related_pages':[]}
    monkeypatch.setattr(workflow,'load_manifest',lambda *a,**k:({'conversation_mode':'build_sequence','cases':[case]},tmp_path))
    monkeypatch.setattr(module,'verify_preflight_snapshot',lambda *a: True)
    monkeypatch.setattr(module,'inspect_related_pages',lambda *a: [])
    class Client:
        def post(self, route): return 'completed'
    monkeypatch.setattr(workflow,'capture_case',lambda client,world,template,case,directory,**kw:client.post('/api/live/agent/turn'))
    monkeypatch.setattr(workflow,'capture',lambda manifest,output,*,cohort_manifest_sha256,clone_app=False:
                        workflow.capture_case(Client(),'world',{'primary_work':{'object_id':'page'}},case,output))
    for status, after in [('changed', {'synthetic':False}), ('unavailable', RuntimeError('postflight failed'))]:
        calls = iter([{'synthetic':True}, after])
        def inspect(*_):
            result=next(calls)
            if isinstance(result,Exception): raise result
            return result
        monkeypatch.setattr(module,'inspect_primary_page',inspect)
        directory=tmp_path/status
        assert module.capture(_test_manifest(tmp_path),directory,fixtures={'case1':fixture},
                              expected_manifest_sha256=MANIFEST_PIN,
                              expected_fixture_sha256=module.fixture_sha256({'case1':fixture})) == 'completed'
        record=json.loads((directory/'primary-page-stability.json').read_text())
        assert record['status']==status
        assert record['error_type']==('RuntimeError' if status=='unavailable' else None)
        assert record['after']==(None if status=='unavailable' else after)


def test_primary_page_record_rejects_wrong_fixture_identity_and_forged_status():
    import copy
    from hashlib import sha256
    from evals.negative_retrieval.primary_page_stability import validate_primary_page_record
    body='# synthetic';digest=sha256(body.encode()).hexdigest()
    fixture={'id':'case1','page':body}
    request={'owner_scope':{'world_id':'world'},'primary_work':{'object_id':'page',
             'expected_revision':1,'expected_content_sha256':digest}}
    before={'world_id':'world','document_id':'page','registry_revision':1,'content_sha256':digest}
    record={'schema':'dmb_negative_retrieval_primary_page_v1','case_id':'case1','status':'stable',
            'before':before,'after':dict(before),'error_type':None}
    assert validate_primary_page_record(record,fixture,request)=='stable'
    changed=copy.deepcopy(record);changed['status']='changed';changed['after']['content_sha256']='0'*64
    assert validate_primary_page_record(changed,fixture,request)=='changed'
    for bad in (dict(changed,case_id='other'),dict(changed,status='stable'),
                {**changed,'after':{**changed['after'],'world_id':'other'}},
                {**changed,'after':{**changed['after'],'content_sha256':'invalid'}},
                {**changed,'before':{**changed['before'],'registry_revision':2}}):
        with pytest.raises(ValueError): validate_primary_page_record(bad,fixture,request)


def test_primary_page_preflight_rejects_wrong_saved_page_before_dispatch(tmp_path,monkeypatch,verified_capture_owner):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module
    case={'id':'case1','question':'Use it.'};fixture={'request':'Use it.','history':[],'related_pages':[]}
    monkeypatch.setattr(workflow,'load_manifest',lambda *a,**k:({'conversation_mode':'build_sequence','cases':[case]},tmp_path))
    monkeypatch.setattr(module,'verify_preflight_snapshot',lambda *a:True)
    monkeypatch.setattr(module,'inspect_primary_page',lambda *_:{'synthetic':False})
    called=[]
    monkeypatch.setattr(workflow,'capture_case',lambda *a,**k:called.append(True))
    monkeypatch.setattr(workflow,'capture',lambda manifest,output,*,cohort_manifest_sha256,clone_app=False:
                        workflow.capture_case(None,'world',{'primary_work':{'object_id':'page'}},case,output))
    with pytest.raises(ValueError,match='Actual primary page'):
        module.capture(_test_manifest(tmp_path),tmp_path/'case',fixtures={'case1':fixture},
                       expected_manifest_sha256=MANIFEST_PIN,expected_fixture_sha256=module.fixture_sha256({'case1':fixture}))
    assert called==[]


def test_primary_resolution_probe_observes_real_resolver_and_failed_reads(monkeypatch):
    import hashlib
    from types import SimpleNamespace
    from apps.live_control_server.routes import agent
    from evals.negative_retrieval.primary_resolution_probe import observe_primary_resolution
    body_text='# private synthetic body';digest=hashlib.sha256(body_text.encode()).hexdigest()
    record=SimpleNamespace(kind='worldbuilding_source',status='active',content_status='committed',
        world_id='world',document_id='page',revision=1,title='Title',source_domain='worldbuilding',
        document_class='note',authority_state='draft',visibility_state='internal')
    snapshot=SimpleNamespace(record=record,markdown=body_text,content_sha256=digest,loaded_revision=1,page_presentation=None)
    locator=SimpleNamespace(kind='build',object_id='page',expected_revision=1,expected_content_sha256=digest)
    request=SimpleNamespace(primary_work=locator,surface=SimpleNamespace(surface_id='build'),build_image_move_capture=None)
    monkeypatch.setattr(agent,'_managed_world_root',lambda:'root')
    original=lambda *_:snapshot
    monkeypatch.setattr(agent,'get_committed_page_snapshot',original)
    with observe_primary_resolution() as result:
        agent._build_work_resolver(request,{'kind':'world','id':'world'})
        with pytest.raises(Exception):agent._build_work_resolver(request,None)
    assert result=={'status':'observed','started':1,'returned':1,'raised':0,'pending_at_close':0}
    assert agent.get_committed_page_snapshot is original
    assert body_text not in str(result) and digest not in str(result)
    def fail(*_):raise RuntimeError('synthetic failure')
    monkeypatch.setattr(agent,'get_committed_page_snapshot',fail)
    with observe_primary_resolution() as result:
        with pytest.raises(RuntimeError,match='synthetic failure'):
            agent._build_work_resolver(request,{'kind':'world','id':'world'})
    assert result['started']==1 and result['raised']==1 and result['returned']==0
    assert agent.get_committed_page_snapshot is fail


def test_primary_resolution_probe_marks_pending_work_uncertain(monkeypatch):
    from threading import Event,Thread
    from apps.live_control_server.routes import agent
    from evals.negative_retrieval.primary_resolution_probe import observe_primary_resolution,validate_primary_resolution
    entered,release=Event(),Event()
    def blocked(*_): entered.set();release.wait(timeout=5);return 'private'
    monkeypatch.setattr(agent,'get_committed_page_snapshot',blocked)
    with observe_primary_resolution() as state:
        alias=agent.get_committed_page_snapshot
        thread=Thread(target=lambda:alias('private'));thread.start();assert entered.wait(timeout=5)
    try:
        assert state=={'status':'uncertain','started':1,'returned':0,'raised':0,'pending_at_close':1}
        record={'schema':'dmb_negative_retrieval_primary_resolution_v1','case_id':'case1',
                'window':'turn_post_v1','coverage':'partial',**state}
        assert validate_primary_resolution(record,'case1')['status']=='uncertain'
    finally:
        release.set();thread.join(timeout=5)
    assert not thread.is_alive() and state['pending_at_close']==1 and state['returned']==0
    assert agent.get_committed_page_snapshot is blocked


def test_primary_resolution_validation_refuses_inconsistent_records():
    import copy
    from evals.negative_retrieval.primary_resolution_probe import validate_primary_resolution
    record={'schema':'dmb_negative_retrieval_primary_resolution_v1','case_id':'case1',
            'window':'turn_post_v1','coverage':'partial','status':'observed',
            'started':1,'returned':1,'raised':0,'pending_at_close':0}
    assert validate_primary_resolution(record,'case1')==record
    for change in (lambda x:x.update(case_id='other'),lambda x:x.update(started=True),
                   lambda x:x.update(returned=2),lambda x:x.update(status='not_started'),
                   lambda x:x.update(pending_at_close=1),lambda x:x.update(payload='private')):
        bad=copy.deepcopy(record);change(bad)
        with pytest.raises(ValueError,match='Invalid primary-work'):validate_primary_resolution(bad,'case1')
    for status in ('not_started','unavailable'):
        empty={**record,'status':status,'started':0,'returned':0}
        assert validate_primary_resolution(empty,'case1')['status']==status


def test_sql_window_observes_prebound_calls_and_exception_without_payload(tmp_path):
    from types import SimpleNamespace
    from evals.negative_retrieval.sql_window import observe_sql_window, validate_sql_window
    class Cursor:
        def execute(self, sql, arguments): return 'private result'
        def executemany(self, sql, arguments): raise RuntimeError('private failure')
    cursor=Cursor(); cursor.connection=SimpleNamespace(info=SimpleNamespace(host='127.0.0.1',port=5432,dbname='synthetic-app'))
    alias=cursor.execute
    owners={Cursor.execute.__code__:'execute',Cursor.executemany.__code__:'executemany'}
    endpoints={'app':('127.0.0.1','5432','synthetic-app')}
    root=__import__('pathlib').Path(__file__).resolve().parents[2]
    with observe_sql_window(owners=owners,roots=[root],endpoints=endpoints) as state:
        assert alias('private sql',('private argument',))=='private result'
        with pytest.raises(RuntimeError,match='private failure'):cursor.executemany('private sql',('private argument',))
    assert state['status']=='observed' and (state['started'],state['returned'],state['raised'])==(2,1,1)
    assert {r['api'] for r in state['calls']}=={'execute','executemany'}
    assert all(r['scope']=='app' and r['code_sha256'] and r['source_sha256'] for r in state['calls'])
    assert all(secret not in str(state) for secret in ('private sql','private argument','private result','private failure','synthetic-app'))
    row={'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state}
    assert validate_sql_window(row,'case1')['status']=='observed'


def test_sql_window_pending_thread_and_unknown_scope_are_not_complete():
    from threading import Event,Thread
    from pathlib import Path
    from evals.negative_retrieval.sql_window import observe_sql_window,validate_sql_window
    entered,release=Event(),Event()
    class Cursor:
        def execute(self): entered.set();release.wait(timeout=5)
    cursor=Cursor(); alias=cursor.execute
    with observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[Path(__file__).resolve().parents[2]],endpoints={}) as state:
        thread=Thread(target=alias);thread.start();assert entered.wait(timeout=5)
    try:
        assert state['status']=='uncertain' and state['started']==1 and state['pending_at_close']==1
        assert state['calls'][0]['scope']=='unknown'
        row={'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state}
        validate_sql_window(row,'case1')
    finally:
        release.set();thread.join(timeout=5)
    assert not thread.is_alive() and state['pending_at_close']==1 and state['returned']==0


def test_sql_window_detects_preexisting_async_execution():
    import asyncio
    from pathlib import Path
    from evals.negative_retrieval.sql_window import observe_sql_window,validate_sql_window
    class Cursor:
        async def execute(self):
            await asyncio.sleep(0)
            return 'private'
    cursor=Cursor(); pending=cursor.execute(); assert pending.send(None) is None
    with observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[Path(__file__).resolve().parents[2]],endpoints={}) as state:
        with pytest.raises(StopIteration):pending.send(None)
    assert state['status']=='uncertain' and state['resumed_unknown']==1 and state['started']==0
    validate_sql_window({'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state},'case1')


def test_sql_window_limits_cardinality_and_rejects_malformed(monkeypatch,tmp_path):
    import copy
    from evals.negative_retrieval import sql_window as sw
    class Cursor:
        def execute(self):return None
    monkeypatch.setattr(sw,'_MAX_CALLERS',0)
    with sw.observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[tmp_path],endpoints={}) as state:
        Cursor().execute()
    assert state['status']=='uncertain' and state['overflow']==1 and state['calls']==[]
    row={'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state}
    sw.validate_sql_window(row,'case1')
    for bad in (dict(row,status='observed'),dict(row,overflow=0),dict(row,started=True),dict(row,case_id='other'),dict(row,payload='private')):
        with pytest.raises(ValueError):sw.validate_sql_window(bad,'case1')


def test_sql_window_fails_closed_when_monitoring_cleanup_fails(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from evals.negative_retrieval import sql_window as sw
    class Cursor:
        def execute(self):return None
    real=sw.sys.monitoring
    def set_local(slot,code,events):
        real.set_local_events(slot,code,events)
        if not events:raise RuntimeError('synthetic cleanup failure')
    proxy=SimpleNamespace(events=real.events,get_tool=real.get_tool,use_tool_id=real.use_tool_id,
        set_local_events=set_local,register_callback=real.register_callback,set_events=real.set_events,free_tool_id=real.free_tool_id)
    with monkeypatch.context() as patch:
        patch.setattr(sw.sys,'monitoring',proxy)
        patch.setattr(sw,'_poisoned',False)
        with pytest.raises(sw.SqlWindowCleanupError):
            with sw.observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[tmp_path],endpoints={}) as state:
                Cursor().execute()
        assert state['status']=='uncertain' and state['monitor_error'] is True
        with pytest.raises(sw.SqlWindowCleanupError):
            with sw.observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[tmp_path],endpoints={}):pass
    assert all(real.get_tool(i)!='buddy-negative-sql-window' for i in range(6))


def test_sql_window_no_slot_is_unavailable_without_affecting_others(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from evals.negative_retrieval import sql_window as sw
    class Cursor:
        def execute(self): return None
    real=sw.sys.monitoring
    proxy=SimpleNamespace(events=real.events,get_tool=lambda _: 'other-owner')
    with monkeypatch.context() as patch:
        patch.setattr(sw.sys,'monitoring',proxy)
        with sw.observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[tmp_path],endpoints={}) as state:
            assert Cursor().execute() is None
    assert state['status']=='unavailable' and state['started']==0 and state['calls']==[]


def test_sql_window_pending_limit_marks_dropped_calls_unknown(monkeypatch,tmp_path):
    from evals.negative_retrieval import sql_window as sw
    class Cursor:
        def execute(self):return 'synthetic'
    monkeypatch.setattr(sw,'_MAX_PENDING',0)
    with sw.observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[tmp_path],endpoints={}) as state:
        assert Cursor().execute()=='synthetic'
    assert state['status']=='uncertain' and state['dropped_starts']==1 and state['started']==0
    assert state['monitor_error'] is True
    sw.validate_sql_window({'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state},'case1')


def test_sql_window_tracks_async_cursor_through_suspend_and_return():
    import asyncio
    from pathlib import Path
    from evals.negative_retrieval.sql_window import observe_sql_window,validate_sql_window
    class Cursor:
        async def execute(self):
            await asyncio.sleep(0)
            return 'private result'
    with observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[Path(__file__).resolve().parents[2]],endpoints={}) as state:
        assert asyncio.run(Cursor().execute())=='private result'
    assert (state['status'],state['started'],state['returned'],state['raised'],state['resumed_unknown'])==('observed',1,1,0,0)
    validate_sql_window({'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state},'case1')


def test_sql_window_tracks_generator_cursor_api_without_double_counting():
    from contextlib import contextmanager
    from pathlib import Path
    import inspect
    from evals.negative_retrieval.sql_window import observe_sql_window,validate_sql_window
    class Cursor:
        @contextmanager
        def copy(self):
            yield 'private result'
    code=inspect.unwrap(Cursor.copy).__code__
    with observe_sql_window(owners={code:'copy'},roots=[Path(__file__).resolve().parents[2]],endpoints={}) as state:
        with Cursor().copy() as result:assert result=='private result'
    assert (state['status'],state['started'],state['returned'],state['resumed_unknown'])==('observed',1,1,0)
    assert state['calls'][0]['api']=='copy' and 'private result' not in str(state)
    validate_sql_window({'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',**state},'case1')


def test_sql_source_classification_is_exact_partial_and_never_guesses():
    import copy
    from evals.negative_retrieval import sql_source_classification as sc
    from evals.negative_retrieval.sql_window import validate_sql_window
    old_page="29179cbe37f50b19157e6f0f157ed0cb860a42d6a7c62d3ccccfa15d42244273"
    old_repo="59803ac57cbb152e87e27665a8a626a9a1c47fcf56194f92e5efa40eabdc619d"
    new_repo="4a10c408016820ef35c1f119a2ffdd2d700f85c4336ed450cc8442039fd47819"
    def entry(source,code,line,count=1,scope='app',api='execute'):
        return {'scope':scope,'api':api,'source_sha256':source,'code_sha256':code,'line':line,'count':count}
    rows=[entry(old_page,sc._PAGE_INVENTORY,512,2),entry(old_repo,sc._REVISION,192,3),
          entry(new_repo,sc._REVISION_BY_N,209),entry(*next(x for x in sc._WORKING_COPY if x[0]==old_repo)),
          entry(new_repo,sc._REVISION,192,scope='core'),entry('0'*64,sc._REVISION,192),
          entry(new_repo,sc._REVISION,193),entry(new_repo,sc._REVISION,192,api='copy')]
    record={'schema':'dmb_negative_retrieval_sql_window_v2','case_id':'case1','window':'turn_post_v1',
        'coverage':'partial','status':'observed','started':sum(row['count'] for row in rows),
        'returned':sum(row['count'] for row in rows),'raised':0,'pending_at_close':0,
        'resumed_unknown':0,'overflow':0,'dropped_starts':0,'monitor_error':False,'unsupported_apis':0,
        'runtime':copy.deepcopy(sc._KNOWN_RUNTIME),'calls':rows}
    result=sc.classify_sql_window(record,'case1')
    assert result['coverage']=='partial' and result['observed_attempts']=={
        'page_inventory_attempts':2,'saved_revision_body_attempts':4,'working_copy_body_attempts':1}
    assert result['unclassified_started']==4
    uncertain=copy.deepcopy(record);uncertain['status']='uncertain';uncertain['resumed_unknown']=1
    assert sc.classify_sql_window(uncertain,'case1')['resumed_unknown']==1
    old=copy.deepcopy(record);old['schema']='dmb_negative_retrieval_sql_window_v1';del old['runtime']
    assert validate_sql_window(old,'case1') and sc.classify_sql_window(old,'case1') is None
    changed=copy.deepcopy(record);changed['runtime']['version']=[3,13,13]
    assert sc.classify_sql_window(changed,'case1') is None
    changed=copy.deepcopy(record);changed['runtime']['version']=[3,13,True]
    with pytest.raises(ValueError,match='runtime'):sc.classify_sql_window(changed,'case1')
    changed=copy.deepcopy(record);changed['status']='not_started';changed['started']=0;changed['returned']=0;changed['calls']=[]
    assert sc.classify_sql_window(changed,'case1') is None
    with pytest.raises(ValueError):sc.classify_sql_window(record,'other')


def test_sql_window_distinguishes_turn_executor_and_foreign_thread():
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from threading import Thread
    from types import SimpleNamespace
    from evals.negative_retrieval.source_window import observe_source_window, _scope
    from evals.negative_retrieval.sql_window import observe_sql_window, validate_sql_window
    class Cursor:
        def execute(self): return None
    cursor=Cursor();cursor.connection=SimpleNamespace(info=SimpleNamespace(host='127.0.0.1',port=5432,dbname='synthetic'))
    def owner(): return cursor.execute()
    scope_ref=[None]
    with ThreadPoolExecutor(max_workers=1) as executor:
        with observe_sql_window(owners={Cursor.execute.__code__:'execute'},roots=[Path(__file__).resolve().parents[2]],
                                endpoints={'app':('127.0.0.1','5432','synthetic')},scope_ref=scope_ref) as sql:
            cursor.execute()  # setup before source-window token
            with observe_source_window(owners={owner.__code__:'metadata'},executor=executor) as source:
                scope_ref[0]=_scope.get()
                owner()
                executor.submit(owner).result()
                foreign=Thread(target=cursor.execute);foreign.start();foreign.join()
            cursor.execute()  # after the source scope has ended
    row={'schema':'dmb_negative_retrieval_sql_window_v3','case_id':'case1','window':'turn_post_v1',**sql}
    validate_sql_window(row,'case1')
    assert sum(r['count'] for r in sql['calls'] if r['turn']=='scoped')==2, ([(r['turn'],r['count']) for r in sql['calls']],sql['status'],sql['started'],sql['monitor_error'],source['status'])
    assert sum(r['count'] for r in sql['calls'] if r['turn']=='unscoped')==3
    assert sql['status']=='observed' and source['status']=='observed'
    assert 'synthetic' not in str(sql)
    invalid=__import__('copy').deepcopy(row);invalid['calls'][0]['turn']='other'
    with pytest.raises(ValueError,match='SQL call inventory'):validate_sql_window(invalid,'case1')


from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from evals.negative_retrieval import core_connection_probe as probe
from evals.negative_retrieval.source_window import _scope

EXPECTED = {'host': '127.0.0.1', 'port': 32769}


@pytest.fixture
def owners(monkeypatch):
    from dungeonmind.infrastructure.postgres.database import PostgresDatabase, _ScopedReadTransactions

    baseline = ('core', '123', '456', 'reader', 'reader', True)
    monkeypatch.setattr(probe, '_baseline', lambda *_: baseline)

    class Connection:
        closed = False

        def __init__(self):
            self.identity = baseline
            self.events = []
            self.info = SimpleNamespace(host='127.0.0.1', port=32769)

        @contextmanager
        def transaction(self):
            self.events.append('begin')
            try:
                yield self
            except BaseException:
                self.events.append('rollback')
                raise
            else:
                self.events.append('commit')

    monkeypatch.setattr(probe, '_identity', lambda connection: connection.identity)
    connection = Connection()
    original_connect = PostgresDatabase.connect
    monkeypatch.setattr(PostgresDatabase, 'connect', lambda self: connection)
    return PostgresDatabase, _ScopedReadTransactions, connection, baseline, original_connect


def test_known_reused_transaction_is_checked_and_hooks_restored(owners):
    database, scoped, connection, baseline, _ = owners
    before = (database.connect, database.transaction, scoped.transaction)
    turn = object()
    scope_ref = [turn]
    token = _scope.set(turn)
    try:
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=scope_ref) as state:
            # A connection created before observation is still checked at admission.
            with scoped(connection).transaction() as actual:
                assert actual is connection
            assert state['transactions']['scoped'] == 1
            assert state['verified']['scoped'] == 1
            assert state['connections']['scoped'] == 0
        assert state['status'] == 'observed'
        assert state['pending_at_close'] == 0
        assert connection.events == ['begin', 'commit']
        assert (database.connect, database.transaction, scoped.transaction) == before
        assert state['coverage'] == 'partial'
    finally:
        _scope.reset(token)


@pytest.mark.parametrize('identity', [
    ('other', '123', '456', 'reader', 'reader', True),
    ('core', '999', '456', 'reader', 'reader', True),
    ('core', '123', 'different', 'reader', 'reader', True),
    ('core', '123', '456', 'other', 'reader', True),
    ('core', '123', '456', 'reader', 'reader', False),
    None,
])
def test_wrong_identity_or_writable_transaction_rolls_back(owners, identity):
    _, scoped, connection, _, _ = owners
    connection.identity = identity
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        with pytest.raises(ValueError, match='differs'):
            with scoped(connection).transaction():
                pytest.fail('Product must not receive the mismatched transaction')
    assert connection.events == ['begin', 'rollback']
    assert state['mismatches'] == 1 and state['status'] == 'uncertain'
    assert state['verified']['unscoped'] == 0


def test_check_failure_and_product_failure_preserve_original_errors(owners, monkeypatch):
    _, scoped, connection, _, _ = owners
    def failed_check(_):
        raise OSError('check failed')
    monkeypatch.setattr(probe, '_identity', failed_check)
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        with pytest.raises(OSError, match='check failed'):
            with scoped(connection).transaction():
                pass
    assert state['errors'] == 1 and state['status'] == 'uncertain'
    assert connection.events == ['begin', 'rollback']


def test_wrong_endpoint_is_rejected_even_when_database_identity_matches(owners):
    _, scoped, connection, _, _ = owners
    connection.info.port = 1111
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        with pytest.raises(ValueError, match='differs'):
            with scoped(connection).transaction():
                pytest.fail('Product must not receive a connection to the wrong endpoint')
    assert state['mismatches'] == 1
    assert connection.events == ['begin', 'rollback']


def test_open_connection_is_counted_but_never_proves_a_transaction(owners):
    database, _, connection, _, _ = owners
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        assert database('unused').connect() is connection
    assert state['connections']['unscoped'] == 1
    assert state['transactions']['unscoped'] == state['verified']['unscoped'] == 0


def test_async_owner_is_rejected_and_partially_installed_hooks_are_restored(owners, monkeypatch):
    from contextlib import asynccontextmanager
    database, _, _, _, _ = owners
    original_connect = database.connect
    @asynccontextmanager
    async def async_transaction(self):
        yield None
    monkeypatch.setattr(database, 'transaction', async_transaction)
    with pytest.raises(TypeError, match='Asynchronous'):
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]):
            pytest.fail('Unsupported owner must not dispatch')
    assert database.connect is original_connect


def test_witness_queries_are_not_counted_as_product_sql():
    from pathlib import Path
    from evals.negative_retrieval.sql_window import observe_sql_window

    class Cursor:
        def execute(self):
            return None

    cursor = Cursor()
    with observe_sql_window(owners={Cursor.execute.__code__: 'execute'},
                            roots=[Path(__file__).resolve().parents[2]], endpoints={}) as state:
        cursor.execute()
        token = probe._witness_sql.set(True)
        try:
            cursor.execute()
        finally:
            probe._witness_sql.reset(token)
        cursor.execute()
    assert state['started'] == state['returned'] == 2
    assert state['resumed_unknown'] == 0


def test_artifact_never_infers_complete_or_accepts_invalid_counts():
    row = {'schema': 'dmb_negative_retrieval_core_connection_v1', 'case_id': 'example',
           'window': 'turn_post_v1', 'coverage': 'partial', 'status': 'observed',
           'connections': {'scoped': 0, 'unscoped': 0},
           'transactions': {'scoped': 0, 'unscoped': 0},
           'verified': {'scoped': 0, 'unscoped': 0}, 'mismatches': 0, 'errors': 0,
           'pending_at_close': 0, 'owner_source_sha256': 'a' * 64}
    assert probe.validate_artifact(row, 'example')['coverage'] == 'partial'
    for change in ({'case_id': 'other'}, {'coverage': 'complete'}, {'errors': 1},
                   {'verified': {'scoped': 1, 'unscoped': 0}},
                   {'transactions': {'scoped': 1, 'unscoped': 0}}, {'extra': True}):
        with pytest.raises(ValueError):
            probe.validate_artifact(row | change, 'example')


def test_tampered_hook_poisoned_and_original_error_preserved(owners, monkeypatch):
    database, _, _, _, _ = owners
    monkeypatch.setattr(probe, '_poisoned', False)
    with pytest.raises(ValueError, match='original failure') as error:
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
            monkeypatch.setattr(database, 'connect', lambda self: None)
            raise ValueError('original failure')
    assert any('could not be restored' in note for note in error.value.__notes__)
    assert state['status'] == 'uncertain' and state['errors'] == 1
    with pytest.raises(RuntimeError, match='fresh process'):
        with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]):
            pass


def test_interrupted_hook_restoration_poisoned_and_restores_other_hooks(owners, monkeypatch):
    import builtins
    database, scoped, _, _, _ = owners
    original_connect, original_scoped = database.connect, scoped.transaction
    monkeypatch.setattr(probe, '_poisoned', False)
    def interrupted_setattr(owner, name, value):
        if owner is scoped and name == 'transaction' and value is original_scoped:
            raise KeyboardInterrupt('synthetic restoration interruption')
        return builtins.setattr(owner, name, value)
    monkeypatch.setattr(probe, 'setattr', interrupted_setattr, raising=False)
    try:
        with pytest.raises(ValueError, match='original failure') as error:
            with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
                raise ValueError('original failure')
        assert state['status'] == 'uncertain' and state['errors'] == 1
        assert database.connect is original_connect
        assert any('could not be restored' in note for note in error.value.__notes__)
        with pytest.raises(RuntimeError, match='fresh process'):
            with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]):
                pass
    finally:
        builtins.setattr(scoped, 'transaction', original_scoped)


def test_silent_hook_restoration_failure_poisoned(owners, monkeypatch):
    import builtins
    database, scoped, _, _, _ = owners
    original_connect, original_scoped = database.connect, scoped.transaction
    monkeypatch.setattr(probe, '_poisoned', False)
    def ignored_setattr(owner, name, value):
        if owner is scoped and name == 'transaction' and value is original_scoped:
            return
        return builtins.setattr(owner, name, value)
    monkeypatch.setattr(probe, 'setattr', ignored_setattr, raising=False)
    try:
        with pytest.raises(RuntimeError, match='could not be restored'):
            with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
                pass
        assert state['status'] == 'uncertain' and state['errors'] == 1
        assert database.connect is original_connect
    finally:
        builtins.setattr(scoped, 'transaction', original_scoped)


def test_retained_transaction_alias_is_inert_after_observer_closes(owners):
    from copy import deepcopy
    _, scoped, connection, _, _ = owners
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        retained = scoped(connection).transaction
    frozen = deepcopy(state)
    connection.identity = ('wrong', 'wrong', 'wrong', 'wrong', 'wrong', False)
    with retained() as actual:
        assert actual is connection
    assert state == frozen
    assert connection.events == ['begin', 'commit']


def test_inflight_transaction_at_window_close_stays_uncertain_and_frozen(owners):
    from copy import deepcopy
    from threading import Event, Thread
    _, scoped, connection, _, _ = owners
    entered, release = Event(), Event()
    def worker():
        with scoped(connection).transaction():
            entered.set()
            assert release.wait(5)
    with probe.observe_core_connections('unused', EXPECTED, scope_ref=[None]) as state:
        thread = Thread(target=worker)
        thread.start()
        assert entered.wait(5)
    frozen = deepcopy(state)
    assert frozen['status'] == 'uncertain' and frozen['pending_at_close'] == 1
    release.set()
    thread.join(5)
    assert not thread.is_alive() and state == frozen


def test_capture_retains_unavailable_witness_if_setup_fails(tmp_path, monkeypatch):
    import json
    from hashlib import sha256
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    @contextmanager
    def failed_setup(*args, **kwargs):
        raise OSError('Core connection preflight failed')
        yield

    class Client:
        def post(self, *args, **kwargs):
            pytest.fail('A failed preflight must not dispatch')

    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{}')
    out = tmp_path / 'capture'
    monkeypatch.setenv('DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL', 'unused')
    monkeypatch.setattr(module, 'checked_owned_dsn', lambda: 'unused')
    monkeypatch.setattr(module, 'observe_core_connections', failed_setup)
    monkeypatch.setattr(workflow, 'load_manifest', lambda *args, **kwargs:
                        ({'conversation_mode': 'build_sequence', 'isolation': {'native': {}}}, tmp_path))
    monkeypatch.setattr(workflow, 'capture_case', lambda client, *args, **kwargs:
                        client.post('/api/live/agent/turn'))
    monkeypatch.setattr(workflow, 'capture', lambda manifest, output, *, cohort_manifest_sha256, clone_app=False:
                        workflow.capture_case(Client(), 'world', {}, {'id': 'case1'}, output))
    with pytest.raises(OSError, match='preflight failed'):
        module.capture(manifest, out, expected_manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
                       observe_core=True)
    row = json.loads((out / 'core-connection-probe.json').read_bytes())
    assert probe.validate_artifact(row, 'case1')['status'] == 'unavailable'


def test_gateway_policy_tracks_simple_and_reused_prepared_execution():
    import struct
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy
    policy = FrontendPolicy()
    policy.frontend(b'Q', b'BEGIN\0')
    assert policy.snapshot()['pending'] == 1
    policy.backend(b'C', b'BEGIN\0')
    policy.backend(b'Z', b'T')
    policy.frontend(b'P', b's\0SELECT 1\0' + struct.pack('!H', 0))
    for name in (b'p1', b'p2'):
        policy.frontend(b'B', name + b'\0s\0' + struct.pack('!HHH', 0, 0, 0))
        policy.frontend(b'E', name + b'\0' + struct.pack('!I', 0))
    policy.frontend(b'S', b'')
    policy.backend(b'C', b'SELECT 1\0')
    policy.backend(b'C', b'SELECT 1\0')
    policy.backend(b'Z', b'T')
    policy.frontend(b'Q', b'ROLLBACK\0')
    policy.backend(b'C', b'ROLLBACK\0')
    policy.backend(b'Z', b'I')
    policy.frontend(b'X', b'')
    result = policy.snapshot()
    assert result['ended'] and result['ready'] and not result['failed'] and result['pending'] == 0
    assert [e['kind'] for e in result['events']] == ['simple', 'execute', 'execute', 'simple']
    assert all(e['outcome'] == 'completed' for e in result['events'])
    assert all(set(e) == {'sequence', 'kind', 'query_sha256', 'category', 'outcome'} for e in result['events'])


@pytest.mark.parametrize('tag,body', [
    (b'Q', b'SELECT 1; SELECT 17\0'),
    (b'Q', b'SELECT pg_read_file($$secret$$)\0'),
    (b'Q', b'SELECT 1\0trailing'),
    (b'P', b's\0SELECT $1::int\0\x00\x01\x00\x00\x00\x17'),
    (b'E', b'missing\0\x00\x00\x00\x00'),
    (b'F', b''), (b'd', b'source data'), (b'H', b''),
])
def test_gateway_policy_rejects_unknown_sql_and_protocol_before_forwarding(tag, body):
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied
    policy = FrontendPolicy()
    with pytest.raises(ProtocolDenied):
        policy.frontend(tag, body)
    assert policy.snapshot()['failed'] and not policy.snapshot()['events']


def test_gateway_policy_fails_closed_on_unknown_binding_and_backend_error():
    import struct
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied
    policy = FrontendPolicy()
    policy.frontend(b'P', b's\0SELECT 1\0' + struct.pack('!H', 0))
    with pytest.raises(ProtocolDenied):
        policy.frontend(b'B', b'p\0missing\0' + struct.pack('!HHH', 0, 0, 0))
    assert policy.snapshot()['failed']
    other = FrontendPolicy()
    other.frontend(b'Q', b'SELECT 1\0')
    other.backend(b'E', b'synthetic error contents')
    assert other.snapshot()['events'][0]['outcome'] == 'failed' and other.snapshot()['failed']
    with pytest.raises(ProtocolDenied):
        other.frontend(b'Q', b'SELECT 17\0')


def test_gateway_refuses_clean_termination_with_open_transaction():
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied
    policy = FrontendPolicy()
    policy.frontend(b'Q', b'BEGIN\0')
    policy.backend(b'C', b'BEGIN\0')
    policy.backend(b'Z', b'T')
    with pytest.raises(ProtocolDenied, match='unresolved'):
        policy.frontend(b'X', b'')
    assert policy.snapshot()['transaction_status'] == 'T' and policy.snapshot()['failed']


def test_gateway_startup_refuses_foreign_database_options_and_cancel():
    import socket
    import struct
    from evals.negative_retrieval.closed_db_gateway import _startup
    from evals.negative_retrieval.gateway_protocol import ProtocolDenied

    def frame(fields):
        body = struct.pack('!I', 196608) + b''.join(k + b'\0' + v + b'\0' for k, v in fields) + b'\0'
        return struct.pack('!I', len(body) + 4) + body

    for fields in ([(b'user', b'sandbox'), (b'database', b'other')],
                   [(b'user', b'sandbox'), (b'database', b'owned'), (b'options', b'-c role=admin')],
                   [(b'user', b'sandbox'), (b'user', b'sandbox'), (b'database', b'owned')]):
        client, server = socket.socketpair()
        try:
            client.sendall(frame(fields))
            with pytest.raises(ProtocolDenied):
                _startup(server, 'owned')
        finally:
            client.close(); server.close()
    client, server = socket.socketpair()
    try:
        client.sendall(struct.pack('!II', 16, 80877102) + b'\0' * 8)
        with pytest.raises(ProtocolDenied):
            _startup(server, 'owned')
    finally:
        client.close(); server.close()


def test_gateway_never_forwards_unknown_sql():
    import socket
    import struct
    from threading import Thread
    from evals.negative_retrieval.closed_db_gateway import _ClosedDatabaseGateway
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy
    gateway = _ClosedDatabaseGateway('/tmp', 'unused', {'database': 'owned'})
    client, incoming = socket.socketpair()
    outgoing, backend = socket.socketpair()
    backend.settimeout(.1)
    policy = FrontendPolicy()
    thread = Thread(target=gateway._relay, args=(incoming, outgoing, policy, True))
    thread.start()
    try:
        body = b'SELECT pg_read_file($$secret$$)\0'
        client.sendall(b'Q' + struct.pack('!I', len(body) + 4) + body)
        thread.join(2)
        assert not thread.is_alive() and policy.failed
        with pytest.raises(TimeoutError):
            backend.recv(1)
        assert not policy.events
    finally:
        for sock in (client, incoming, outgoing, backend):
            sock.close()


def test_gateway_finish_is_retryable_after_interruption(monkeypatch):
    import subprocess
    from evals.negative_retrieval.closed_db_gateway import _ClosedDatabaseGateway
    gateway = _ClosedDatabaseGateway('/tmp', 'unused', {'database': 'owned'})
    calls = []
    def interrupted_once():
        calls.append('close')
        if len(calls) == 1:
            raise KeyboardInterrupt('synthetic cleanup interruption')
        gateway._closed = True
    monkeypatch.setattr(gateway, '_close', interrupted_once)
    worker = subprocess.Popen(['/bin/true'])
    worker.wait(timeout=5)
    with pytest.raises(KeyboardInterrupt):
        gateway.finish(worker)
    assert not gateway._finished
    assert gateway.finish(worker)['status'] == 'unsealed'
    assert calls == ['close', 'close']


def test_owned_gateway_retries_cleanup_when_finish_is_interrupted(tmp_path, monkeypatch):
    import json
    import subprocess
    from evals.negative_retrieval import closed_db_gateway as module
    ledger = tmp_path / 'owner.json'
    ledger.write_text(json.dumps({'database': {'database': 'owned'}}))
    monkeypatch.setenv('DMB_NEGATIVE_RETRIEVAL_OWNER_LEDGER', str(ledger))
    monkeypatch.setattr(module, '_checked_owner_dsn', lambda: 'postgresql://role@/owned')
    monkeypatch.setattr(module._ClosedDatabaseGateway, 'start', lambda self: self)
    calls = []
    def interrupted_once(self):
        calls.append('close')
        if len(calls) == 1:
            raise KeyboardInterrupt('synthetic cleanup interruption')
        self._closed = True
    monkeypatch.setattr(module._ClosedDatabaseGateway, '_close', interrupted_once)
    worker = subprocess.Popen(['/bin/true'])
    worker.wait(timeout=5)
    with pytest.raises(KeyboardInterrupt):
        with module.owned_gateway(tmp_path) as gateway:
            gateway.finish(worker)
    assert calls == ['close', 'close'] and gateway._closed and not gateway._finished


def test_gateway_closes_a_backend_stalled_during_identity(monkeypatch):
    import socket
    from threading import Event, Thread
    from types import SimpleNamespace
    import psycopg
    from evals.negative_retrieval import closed_db_gateway as module
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy
    app_client, app_server = socket.socketpair()
    database, peer = socket.socketpair()
    entered = Event()
    calls = []

    class Backend:
        pgconn = SimpleNamespace(socket=database.fileno(), ssl_in_use=False)
        info = SimpleNamespace(host='127.0.0.1', port=1234)
        def __enter__(self): return self
        def __exit__(self, *args): database.close()
        def execute(self, _query):
            entered.set()
            database.recv(1)
            raise OSError('synthetic closed backend')

    def connect(*args, **kwargs):
        calls.append(kwargs)
        return Backend()
    monkeypatch.setattr(module, '_startup', lambda *_: None)
    monkeypatch.setattr(module, '_checked_owner_dsn', lambda: 'owned')
    monkeypatch.setattr(psycopg, 'connect', connect)
    identity = {'database': 'owned', 'host': '127.0.0.1', 'port': 1234, 'oid': '1', 'system_identifier': '2'}
    gateway = module._ClosedDatabaseGateway('/tmp', 'owned', identity)
    gateway._sockets.add(app_server)
    thread = Thread(target=gateway._serve, args=(app_server, FrontendPolicy()))
    gateway._threads.append(thread)
    thread.start()
    try:
        assert entered.wait(5)
        gateway._close()
        assert not thread.is_alive() and gateway._closed
        assert calls[0]['connect_timeout'] == module._CONNECT_TIMEOUT
        assert 'statement_timeout=3000' in calls[0]['options']
        assert 'forced_shutdown' in gateway._errors
    finally:
        app_client.close(); peer.close()


def test_gateway_owner_verification_timeout_fails_closed(monkeypatch):
    import subprocess
    from evals.negative_retrieval import closed_db_gateway as module
    def timeout(*args, **kwargs):
        assert kwargs['timeout'] == module._OWNER_TIMEOUT
        raise subprocess.TimeoutExpired(args[0], kwargs['timeout'])
    monkeypatch.setattr(module.subprocess, 'run', timeout)
    with pytest.raises(RuntimeError, match='verification timed out'):
        module._checked_owner_dsn()


@pytest.mark.parametrize('actual_role,hostaddr', [('other', '127.0.0.1'), ('reader', '127.0.0.2')])
def test_gateway_refuses_backend_role_or_address_mismatch_before_auth(monkeypatch, actual_role, hostaddr):
    import socket
    from types import SimpleNamespace
    import psycopg
    from evals.negative_retrieval import closed_db_gateway as module
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy
    app_client, app_server = socket.socketpair()
    database, peer = socket.socketpair()

    class Backend:
        pgconn = SimpleNamespace(socket=database.fileno(), ssl_in_use=False)
        info = SimpleNamespace(host='127.0.0.1', hostaddr=hostaddr, port=1234, user=actual_role)
        def __enter__(self): return self
        def __exit__(self, *args): database.close()
        def execute(self, _query):
            return SimpleNamespace(fetchone=lambda: ('owned', '1', '2', actual_role, actual_role))

    monkeypatch.setattr(module, '_startup', lambda *_: None)
    monkeypatch.setattr(module, '_checked_owner_dsn', lambda: 'owned')
    monkeypatch.setattr(psycopg, 'connect', lambda *args, **kwargs: Backend())
    identity = {'database': 'owned', 'host': '127.0.0.1', 'port': 1234,
                'oid': '1', 'system_identifier': '2', 'user': 'reader'}
    gateway = module._ClosedDatabaseGateway('/tmp', 'owned', identity)
    try:
        gateway._serve(app_server, FrontendPolicy())
        assert app_client.recv(1) == b''
        assert 'session_failure' in gateway._errors
    finally:
        app_client.close(); peer.close()


# Focused fail-closed protocol tests for the experimental fixture policy.
_GATEWAY_FIXTURE = UUID('12345678-1234-4234-8234-123456789abc')
_GATEWAY_OTHER = UUID('87654321-4321-4321-8321-cba987654321')


def _gateway_fixture_parse(oid=2950):
    return b's\0' + _REVISION_SQL + b'\0' + struct.pack('!HI', 1, oid)


def _gateway_fixture_bind(value, binary):
    return (b'p\0s\0' + struct.pack('!HHH', 1, int(binary), 1)
            + struct.pack('!i', len(value)) + value + struct.pack('!H', 0))


@pytest.mark.parametrize('binary', [False, True])
def test_revision_allowed_only_for_exact_fixture_and_never_journaled(binary):
    policy = FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE)
    policy.frontend(b'P', _gateway_fixture_parse())
    value = _GATEWAY_FIXTURE.bytes if binary else str(_GATEWAY_FIXTURE).encode()
    policy.frontend(b'B', _gateway_fixture_bind(value, binary))
    policy.frontend(b'E', b'p\0' + struct.pack('!I', 0))
    policy.frontend(b'S', b'')
    policy.backend(b'C', b'SELECT 1\0')
    policy.backend(b'Z', b'I')
    result = policy.snapshot()
    assert result['events'][0]['category'] == 'saved_revision_body'
    assert result['events'][0]['outcome'] == 'completed'
    assert str(_GATEWAY_FIXTURE) not in repr(result) and _GATEWAY_FIXTURE.bytes not in repr(result).encode()


@pytest.mark.parametrize('body', [
    _gateway_fixture_bind(_GATEWAY_OTHER.bytes, True), _gateway_fixture_bind(str(_GATEWAY_OTHER).encode(), False),
    _gateway_fixture_bind(_GATEWAY_FIXTURE.bytes[:-1], True), _gateway_fixture_bind(str(_GATEWAY_FIXTURE).upper().encode(), False),
    b'p\0s\0' + struct.pack('!HHHiH', 1, 1, 1, -1, 0),
    _gateway_fixture_bind(_GATEWAY_FIXTURE.bytes, True) + b'extra',
])
def test_foreign_or_malformed_revision_bind_is_denied_before_execution(body):
    policy = FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE)
    policy.frontend(b'P', _gateway_fixture_parse())
    with pytest.raises(ProtocolDenied):
        policy.frontend(b'B', body)
    assert policy.failed and not policy.events


def test_fixture_read_is_opt_in_and_parameter_type_is_fixed():
    with pytest.raises(ProtocolDenied):
        FrontendPolicy().frontend(b'P', _gateway_fixture_parse())
    with pytest.raises(ProtocolDenied):
        FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE).frontend(b'P', _gateway_fixture_parse(25))
    with pytest.raises(TypeError):
        FrontendPolicy(fixture_revision=str(_GATEWAY_FIXTURE))
    with pytest.raises(ProtocolDenied):
        FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE).frontend(b'Q', _REVISION_SQL + b'\0')


def test_prepared_revision_cannot_be_rebound_to_another_source():
    policy = FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE)
    policy.frontend(b'P', _gateway_fixture_parse())
    policy.frontend(b'B', _gateway_fixture_bind(_GATEWAY_FIXTURE.bytes, True))
    policy.frontend(b'E', b'p\0' + struct.pack('!I', 0))
    policy.frontend(b'S', b'')
    policy.backend(b'C', b'SELECT 1\0')
    policy.backend(b'Z', b'I')
    with pytest.raises(ProtocolDenied):
        policy.frontend(b'B', _gateway_fixture_bind(_GATEWAY_OTHER.bytes, True))
    assert len(policy.events) == 1 and policy.events[0]['outcome'] == 'completed'


def test_clone_profile_receipt_is_private_immutable_and_workstream_bound(tmp_path):
    from evals.negative_retrieval import clone_role_profile as profile
    owner = tmp_path / 'owner'; owner.mkdir(mode=0o700)
    run = owner / 'case-1'; run.mkdir(mode=0o700)
    path = profile._receipt_path(run / 'clone-role-profile.json', run)
    value = {'schema': profile._SCHEMA, 'synthetic': True}
    digest = profile._store(path, value)
    assert profile._load(path) == (value, digest)
    with pytest.raises(FileExistsError):
        profile._store(path, value)
    with pytest.raises(ValueError):
        profile._receipt_path(tmp_path / 'clone-role-profile.json', run)
    path.chmod(0o644)
    with pytest.raises(ValueError, match='private'):
        profile._load(path)
    path.unlink()
    import os
    os.mkfifo(path, 0o600)
    with pytest.raises(ValueError, match='private'):
        profile._load(path)


@pytest.mark.parametrize('current,expected', [
    ('baseline', 'not_applied'), ('active', 'cleaned'), ('cleaned', 'already_cleaned'),
])
def test_clone_profile_recovery_only_reconciles_exact_known_states(tmp_path, monkeypatch, current, expected):
    from evals.negative_retrieval import clone_role_profile as profile
    owner = tmp_path / 'owner'; owner.mkdir(mode=0o700)
    first = owner / 'case-1'; first.mkdir(mode=0o700)
    second = owner / 'case-2'; second.mkdir(mode=0o700)
    identity = {'database': 'synthetic-owned-clone'}
    receipt = {'schema': profile._SCHEMA, 'identity': identity,
               'policy': 'buddy_negative_scope_' + 'a' * 32,
               'revision': '12345678-1234-4234-8234-123456789abc',
               'baseline': {'state': 'baseline'}, 'active': {'state': 'active'},
               'cleaned': {'state': 'cleaned'}}
    path = first / 'clone-role-profile.json'; profile._store(path, receipt)
    state = {'value': {'state': current}, 'removed': 0}
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(profile, '_owner', lambda: ('synthetic', identity, second))
    monkeypatch.setattr(profile, '_connect', lambda *_: Conn())
    monkeypatch.setattr(profile, '_lock_and_check_idle', lambda _: None)
    monkeypatch.setattr(profile, '_snapshot', lambda _: state['value'])
    def remove(_, policy):
        assert policy == receipt['policy']
        state['removed'] += 1
        state['value'] = receipt['cleaned']
    monkeypatch.setattr(profile, '_remove', remove)
    assert profile.recover(path)['state'] == expected
    assert state['removed'] == int(current == 'active')
    assert profile.recover(path)['state'] == ('not_applied' if current == 'baseline' else 'already_cleaned')


def test_clone_profile_quarantines_drift_and_wrong_clone_without_mutation(tmp_path, monkeypatch):
    from evals.negative_retrieval import clone_role_profile as profile
    owner = tmp_path / 'owner'; owner.mkdir(mode=0o700)
    run = owner / 'case-1'; run.mkdir(mode=0o700)
    path = run / 'clone-role-profile.json'
    receipt = {'schema': profile._SCHEMA, 'identity': {'database': 'owned'},
               'policy': 'buddy_negative_scope_' + 'a' * 32,
               'revision': '12345678-1234-4234-8234-123456789abc',
               'baseline': {'state': 'baseline'}, 'active': {'state': 'active'},
               'cleaned': {'state': 'cleaned'}}
    profile._store(path, receipt)
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(profile, '_owner', lambda: ('synthetic', {'database': 'wrong'}, run))
    with pytest.raises(ValueError, match='different clone'):
        profile.recover(path)
    monkeypatch.setattr(profile, '_owner', lambda: ('synthetic', {'database': 'owned'}, run))
    monkeypatch.setattr(profile, '_connect', lambda *_: Conn())
    monkeypatch.setattr(profile, '_lock_and_check_idle', lambda _: None)
    monkeypatch.setattr(profile, '_snapshot', lambda _: {'state': 'unexpected'})
    monkeypatch.setattr(profile, '_remove', lambda *_: pytest.fail('must not mutate drifted state'))
    with pytest.raises(ValueError, match='quarantine'):
        profile.recover(path)


def test_clone_profile_does_not_invent_history_when_baseline_equals_cleaned(tmp_path, monkeypatch):
    from evals.negative_retrieval import clone_role_profile as profile
    owner = tmp_path / 'owner'; owner.mkdir(mode=0o700)
    run = owner / 'case-1'; run.mkdir(mode=0o700)
    path = run / 'clone-role-profile.json'
    receipt = {'schema': profile._SCHEMA, 'identity': {'database': 'owned'},
               'policy': 'buddy_negative_scope_' + 'a' * 32,
               'revision': '12345678-1234-4234-8234-123456789abc',
               'baseline': {'state': 'inactive'}, 'active': {'state': 'active'},
               'cleaned': {'state': 'inactive'}}
    profile._store(path, receipt)
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(profile, '_owner', lambda: ('synthetic', receipt['identity'], run))
    monkeypatch.setattr(profile, '_connect', lambda *_: Conn())
    monkeypatch.setattr(profile, '_lock_and_check_idle', lambda _: None)
    monkeypatch.setattr(profile, '_snapshot', lambda _: receipt['baseline'])
    monkeypatch.setattr(profile, '_remove', lambda *_: pytest.fail('must not mutate inactive state'))
    assert profile.recover(path)['state'] == 'inactive'


@pytest.mark.parametrize('statement', [
    b'RESET ROLE', b'SET ROLE postgres', b'SET SESSION AUTHORIZATION postgres',
    b'SELECT set_config(\'role\',\'postgres\',false)',
])
def test_profile_gateway_rejects_role_escape_before_execution(statement):
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied
    for tag, body in ((b'Q', statement + b'\0'),
                      (b'P', b's\0' + statement + b'\0' + struct.pack('!H', 0))):
        policy = FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE)
        with pytest.raises(ProtocolDenied):
            policy.frontend(tag, body)
        assert policy.failed and not policy.events


def test_profile_gateway_role_admission_checks_profile_and_effective_role(monkeypatch):
    from evals.negative_retrieval import clone_role_profile as profile
    from evals.negative_retrieval.closed_db_gateway import _enter_profile_role
    from evals.negative_retrieval.gateway_protocol import ProtocolDenied
    active = {'role': ['123']}; receipt = {'active': active}
    state = {'snapshot': active, 'role': ('pg_database_owner', 'operator', 'on', '123',
                                         False, False, False, False, False)}
    class Result:
        def fetchone(self): return state['role']
    class Backend:
        commands = []
        def execute(self, command): self.commands.append(command); return Result()
    backend = Backend()
    monkeypatch.setattr(profile, '_snapshot', lambda _: state['snapshot'])
    _enter_profile_role(backend, receipt, 'operator')
    assert backend.commands[0] == 'SET ROLE pg_database_owner'
    state['snapshot'] = {'role': ['other']}; backend.commands.clear()
    with pytest.raises(ProtocolDenied, match='profile changed'):
        _enter_profile_role(backend, receipt, 'operator')
    assert backend.commands == []
    state['snapshot'] = active
    for bad in [('postgres','operator','on','123',False,False,False,False,False),
                ('pg_database_owner','other','on','123',False,False,False,False,False),
                ('pg_database_owner','operator','off','123',False,False,False,False,False),
                ('pg_database_owner','operator','on','123',False,True,False,False,False),
                ('pg_database_owner','operator','on','different',False,False,False,False,False)]:
        state['role'] = bad
        with pytest.raises(ProtocolDenied, match='restricted role'):
            _enter_profile_role(backend, receipt, 'operator')


def test_profiled_gateway_refuses_changed_profile_before_start(monkeypatch, tmp_path):
    from evals.negative_retrieval import clone_role_profile as profile
    from evals.negative_retrieval import closed_db_gateway as gateway
    identity = {'database': 'owned'}
    receipt = {'identity': identity, 'revision': str(_GATEWAY_FIXTURE), 'active': {'valid': True}}
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(profile, '_owner', lambda: ('dsn', identity, tmp_path))
    monkeypatch.setattr(profile, '_receipt_path', lambda path, run: path)
    monkeypatch.setattr(profile, '_load', lambda _: (receipt, 'digest'))
    monkeypatch.setattr(profile, '_connect', lambda *_: Conn())
    monkeypatch.setattr(profile, '_lock_and_check_idle', lambda _: None)
    monkeypatch.setattr(profile, '_snapshot', lambda _: {'valid': False})
    monkeypatch.setattr(gateway, '_ClosedDatabaseGateway', lambda *a, **k: pytest.fail('gateway must not start'))
    with pytest.raises(ValueError, match='not active'):
        with gateway.profiled_gateway(tmp_path, tmp_path / 'receipt'):
            pytest.fail('gateway must not yield')


def test_profile_gateway_closes_backend_stalled_during_role_admission(monkeypatch):
    import socket
    from threading import Event, Thread
    from types import SimpleNamespace
    import psycopg
    from evals.negative_retrieval import closed_db_gateway as module
    from evals.negative_retrieval import clone_role_profile as profile
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy
    app_client, app_server = socket.socketpair()
    database, peer = socket.socketpair()
    entered = Event()
    class Result:
        def fetchone(self): return ('owned', '1', '2', 'operator', 'operator')
    class Backend:
        pgconn = SimpleNamespace(socket=database.fileno(), ssl_in_use=False)
        info = SimpleNamespace(host='127.0.0.1', hostaddr='127.0.0.1', port=1234, user='operator')
        def __enter__(self): return self
        def __exit__(self, *args): database.close()
        def execute(self, _query): return Result()
    def stalled(_):
        entered.set()
        database.recv(1)
        raise OSError('synthetic closed backend')
    monkeypatch.setattr(module, '_startup', lambda *_: None)
    monkeypatch.setattr(module, '_checked_owner_dsn', lambda: 'owned')
    monkeypatch.setattr(profile, '_snapshot', stalled)
    monkeypatch.setattr(psycopg, 'connect', lambda *a, **k: Backend())
    identity = {'database': 'owned', 'host': '127.0.0.1', 'port': 1234,
                'oid': '1', 'system_identifier': '2', 'user': 'operator'}
    gateway = module._ClosedDatabaseGateway('/tmp', 'owned', identity,
                                            role_profile={'active': {'role': ['123']}})
    gateway._sockets.add(app_server)
    thread = Thread(target=gateway._serve, args=(app_server, FrontendPolicy()))
    gateway._threads.append(thread); thread.start()
    try:
        assert entered.wait(5)
        gateway._close()
        assert not thread.is_alive() and gateway._closed
        assert 'forced_shutdown' in gateway._errors
    finally:
        app_client.close(); peer.close()


def test_gateway_tracks_idle_deallocation_and_denies_stale_prepared_execution():
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied
    policy = FrontendPolicy(fixture_revision=_GATEWAY_FIXTURE)
    policy.frontend(b'P', _gateway_fixture_parse())
    policy.frontend(b'B', _gateway_fixture_bind(_GATEWAY_FIXTURE.bytes, True))
    policy.frontend(b'E', b'p\0' + struct.pack('!I', 0))
    policy.frontend(b'S', b'')
    policy.backend(b'C', b'SELECT 1\0'); policy.backend(b'Z', b'I')
    policy.frontend(b'Q', b'DEALLOCATE ALL\0')
    policy.backend(b'C', b'DEALLOCATE ALL\0'); policy.backend(b'Z', b'I')
    assert not policy.statements and not policy.portals
    with pytest.raises(ProtocolDenied):
        policy.frontend(b'B', _gateway_fixture_bind(_GATEWAY_FIXTURE.bytes, True))
    assert policy.failed


def test_gateway_rejects_prepared_or_in_transaction_deallocation():
    from evals.negative_retrieval.gateway_protocol import FrontendPolicy, ProtocolDenied
    prepared = FrontendPolicy()
    with pytest.raises(ProtocolDenied, match='Prepared deallocation'):
        prepared.frontend(b'P', b's\0DEALLOCATE ALL\0' + struct.pack('!H', 0))
    active = FrontendPolicy()
    active.frontend(b'Q', b'BEGIN\0'); active.backend(b'C', b'BEGIN\0'); active.backend(b'Z', b'T')
    with pytest.raises(ProtocolDenied, match='idle session'):
        active.frontend(b'Q', b'DEALLOCATE ALL\0')


def test_different_saved_source_case_requires_correct_support_and_complete_capture():
    import json
    from pathlib import Path

    fixtures = Path(__file__).resolve().parents[2] / "evals/negative_retrieval/fixtures"
    public = json.loads((fixtures / "development.json").read_text())
    private = json.loads((fixtures / "development-private.json").read_text())
    case = next(row for row in public["cases"] if row["id"] == "dev-different-saved-source")
    rubric = private["cases"][case["id"]]
    assert {row["label"] for row in case["related_pages"]} >= {"first-record", "second-record"}
    assert rubric["required_reads"] == ["second-record"]
    good = observation(outcome="answer", reads=["second-record"], catalog_discoveries=1,
                       graph_query_attempts=0, graph_query_journal_complete=True, required_support=True)
    assert assess(rubric, good)["status"] == "pass"
    wrong = dict(good, semantic_quality=False, journal_complete=False)
    assert assess(rubric, wrong)["status"] == "fail"
    unknown = dict(good, semantic_quality=None, journal_complete=False)
    assert assess(rubric, unknown)["status"] == "unproven"
    missing = dict(good, reads=["first-record"], journal_complete=True)
    assert assess(rubric, missing)["checks"]["required_evidence"] is False


@pytest.mark.parametrize("mode", ["matching", "wrong_conversation", "stale_pin", "changed_after_preflight"])
def test_negative_capture_composes_with_ordinary_history_pin(
        tmp_path, monkeypatch, verified_capture_owner, mode):
    """Exercise the adapter and actual ordinary case through the send boundary."""
    import hashlib
    import httpx
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval import capture as module

    case = {"id": "seeded", "question": "Use that idea."}
    fixture = {"request": case["question"], "history": [
        {"role": "user", "content": "An idea?"},
        {"role": "assistant", "content": "A star."}], "related_pages": []}
    turn = {"turn_id": "t", "sequence": 1, "lifecycle_status": "completed",
            "user_text": "An idea?", "assistant_text": "A star."}
    history = {"world_id": "w", "conversation_id": "c", "active_conversation_id": "c",
               "next_before_sequence": None, "turns": [turn]}
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    pin = {"conversation_id": "other" if mode == "wrong_conversation" else "c",
           "prior_turns": [{"turn_id": "t", "sequence": 1,
               "user_text_sha256": digest("An idea?"),
               "assistant_text_sha256": digest("stale" if mode == "stale_pin" else "A star.")}]}
    requests = []
    history_reads = 0
    def handle(request):
        nonlocal history_reads
        requests.append((request.method, request.url.path))
        if request.method == "GET":
            history_reads += 1
            if mode == "changed_after_preflight" and history_reads == 2:
                turn["assistant_text"] = "Changed."
            return httpx.Response(200, json=history)
        return httpx.Response(503, json={"code": "synthetic_stop"})

    monkeypatch.setattr(workflow, "load_manifest", lambda *a, **k: (
        {"conversation_mode": "build_sequence", "cases": [case]}, tmp_path))
    monkeypatch.setattr(workflow, "validate_template", lambda *a, **k: None)
    monkeypatch.setattr(module, "verify_preflight_snapshot", lambda *a: True)
    monkeypatch.setattr(module, "inspect_related_pages", lambda *a: [])
    def run_case(manifest, output, *, cohort_manifest_sha256, clone_app=False):
        with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handle)) as client:
            return workflow.capture_case(client, "w", {"primary_work": {"object_id": "page"},
                "surface": {"surface_id": "build"}}, case, output,
                build_thread_id="test-thread", pinned_history=pin, expected_conversation_id=None)
    monkeypatch.setattr(workflow, "capture", run_case)
    fixtures = {"seeded": fixture}
    with pytest.raises(ValueError):
        module.capture(_test_manifest(tmp_path), tmp_path / "result", fixtures=fixtures,
                       expected_manifest_sha256=MANIFEST_PIN,
                       expected_fixture_sha256=module.fixture_sha256(fixtures))
    posts = [path for method, path in requests if method == "POST"]
    assert posts == (["/api/live/agent/turn"] if mode == "matching" else [])
    assert "/api/live/agent/worlds/w/conversation/new" not in posts
