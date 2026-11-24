from evals.negative_retrieval.assessment import assess


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


def test_clarification_requires_full_delivery_and_continuation():
    assert assess(CASE, observation())["status"] == "pass"
    for field in ("question_addresses_gap", "question_answerable", "question_not_already_answered",
                  "question_no_false_premises", "inline_questions", "no_retry_error",
                  "saved_and_reopened", "answer_sent", "answer_continued", "answer_reopened"):
        assert assess(CASE, observation(**{field: False}))["status"] == "fail"
        assert assess(CASE, observation(**{field: None}))["status"] == "unproven"


def test_unwanted_reads_and_incomplete_journals():
    assert assess(CASE, observation(reads=["unrelated"]))["status"] == "fail"
    assert assess(CASE, observation(journal_complete=False))["status"] == "unproven"
    assert assess(CASE, observation(reads=["unrelated"], journal_complete=False))["status"] == "fail"


def test_positive_control_requires_evidence_not_merely_activity():
    case = {"max_catalog_discoveries": 1, "required_reads": ["archive"], "allowed_reads": ["archive"], "outcomes": ["answer"]}
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

    positive = {"max_catalog_discoveries": 1, "required_reads": ["archive"], "allowed_reads": ["archive"], "outcomes": ["answer"]}
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


def test_empty_catalog_discovery_is_not_a_zero_acquisition_pass():
    from evals.negative_retrieval.related_page_probe import catalog_discovery_count

    evidence = [{"owner": "related_catalog_discovery", "state": "returned"}]
    result = assess(CASE, observation(catalog_discoveries=catalog_discovery_count(evidence), journal_complete=False))
    assert result["checks"]["catalog_budget"] is False
    assert result["status"] == "fail"


def test_capture_wrapper_retains_probe_on_failure_and_restores_owner(tmp_path, monkeypatch):
    import json
    import pytest
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture
    from apps.live_control_server.services import build_related_pages

    original_discover = build_related_pages.discover
    def fail_case(client, world, template, case, directory, **kwargs):
        build_related_pages.discover(None)

    def fail_discovery(request):
        raise RuntimeError("observed failure")

    monkeypatch.setattr(build_related_pages, "discover", fail_discovery)
    monkeypatch.setattr(workflow, "capture_case", fail_case)
    original_case = workflow.capture_case
    def ordinary_capture(manifest, output, **kwargs):
        assert kwargs["clone_app"] is False and len(kwargs["cohort_manifest_sha256"]) == 64
        return workflow.capture_case(None, "world", {}, {"id": "case1"}, output)
    monkeypatch.setattr(workflow, "capture", ordinary_capture)
    monkeypatch.setattr(workflow, "load_manifest", lambda *args, **kwargs: ({"conversation_mode": "build_sequence"}, tmp_path))
    with pytest.raises(RuntimeError, match="observed failure"):
        capture(_test_manifest(tmp_path), tmp_path / "case1")
    evidence = json.loads((tmp_path / "case1" / "related-page-probe.json").read_text())
    assert evidence["coverage"] == "partial"
    assert evidence["records"] == [{"owner": "related_catalog_discovery", "state": "raised"}]
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
            "knowledge_context": {"completion": {"collaboration": {"kind": "questions", "questions": [{"text": "Where?"}]}}}}
    history = {"world_id": "world", "conversation_id": "conversation", "turns": [turn]}
    attempt = {"schema": "dmb_turn_context_trace_v1", "world_id": "world", "conversation_id": "conversation",
               "turn_id": "saved", "terminal_status": "completed", "capture_status": "complete", "observations": []}
    trace = {"world_id": "world", "turn_id": "saved", "attempts": [attempt]}
    probe = {"schema": "dmb_negative_retrieval_related_page_probe_v1", "coverage": "partial", "case_id": "case1",
             "records": [{"owner": "related_catalog_discovery", "state": "returned"}]}
    artifacts = {"request": request, "history-after": envelope(history), "context-trace": envelope(trace),
                 "answer-http": envelope({"turn_id": "turn", "client_thread_id": "thread"}), "related-page-probe": probe}
    for name, value in artifacts.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    result = report_case(tmp_path, {"id": "case1", "request": request["message"]}, CASE)
    assert result["status"] == "unproven"
    assert result["observation_status"] == "fail"
    assert result["fixture_context_verified"] is None
    assert result["primary_context_verified"] is None
    assert result["checks"]["catalog_budget"] is False
    assert result["checks"]["inline_questions"] is None
    assert len(result["artifact_sha256"]) == len(artifacts)


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
            "knowledge_context": {"synthetic": True}}
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
    broken = tmp_path / "broken.test.tsx"
    broken.write_text(source.read_text().replace("rehydrates an intentional object-only clarification inline without a filler reply", "renamed"))
    with pytest.raises(ValueError):
        generate(broken, derived)


def test_related_page_fixture_preflight_rejects_extra_changed_and_duplicate_sources(monkeypatch):
    import copy
    import hashlib
    import pytest
    from apps.live_control_server.services import build_related_pages
    from evals.negative_retrieval.fixture_sources import inspect_related_pages

    body = "Two copper pieces."
    pointer = {"world_id": "w", "document_id": "id", "registry_revision": 1, "title": "Ledger"}
    actual = {**pointer, "markdown": body, "content_sha256": hashlib.sha256(body.encode()).hexdigest()}
    fixture = {"related_pages": [{"label": "ledger", "title": "Ledger", "body": body}]}
    monkeypatch.setattr(build_related_pages, "discover", lambda _: [pointer])
    monkeypatch.setattr(build_related_pages, "materialize", lambda _: actual)
    assert inspect_related_pages(object(), fixture) == [{"label": "ledger", "title": "Ledger", "world_id": "w", "document_id": "id",
        "registry_revision": 1, "content_sha256": actual["content_sha256"]}]
    changed = copy.deepcopy(fixture)
    changed["related_pages"][0]["body"] = "One copper piece."
    with pytest.raises(ValueError):
        inspect_related_pages(object(), changed)
    changed = copy.deepcopy(fixture)
    changed["related_pages"].append(copy.deepcopy(changed["related_pages"][0]))
    with pytest.raises(ValueError):
        inspect_related_pages(object(), changed)
    monkeypatch.setattr(build_related_pages, "discover", lambda _: [pointer, {**pointer, "title": "Extra"}])
    with pytest.raises(ValueError):
        inspect_related_pages(object(), fixture)


def test_capture_preflight_is_outside_product_probe_and_halts_on_mismatch(tmp_path, monkeypatch):
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
    def ordinary_case(client, world, template, current, directory, **kwargs):
        assert not directory.exists()
        seen.append("turn")
        build_related_pages.discover(None)
        return "done"
    monkeypatch.setattr(workflow, "capture_case", ordinary_case)
    def ordinary_capture(manifest, output, **kwargs):
        return workflow.capture_case(None, "w", {"primary_work": {"object_id": "page"}}, case, output)
    monkeypatch.setattr(workflow, "capture", ordinary_capture)
    out = tmp_path / "success"
    assert module.capture(_test_manifest(tmp_path), out, fixtures={"case1": fixture}) == "done"
    assert seen == ["fixture", "turn", "fixture"]
    probe = json.loads((out / "related-page-probe.json").read_text())
    assert probe["records"] == [{"owner": "related_catalog_discovery", "state": "returned"}]
    sources = json.loads((out / "fixture-sources.json").read_text())
    assert sources["status"] == "stable"
    seen.clear()
    def mismatch(*args):
        raise ValueError("wrong synthetic sources")
    monkeypatch.setattr(module, "inspect_related_pages", mismatch)
    with pytest.raises(ValueError, match="wrong synthetic sources"):
        module.capture(_test_manifest(tmp_path), tmp_path / "failure", fixtures={"case1": fixture})
    assert seen == []
    assert json.loads((tmp_path / "failure" / "fixture-sources.json").read_text())["status"] == "preflight_failed"


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


def test_postflight_failure_is_retained_and_stops_capture(tmp_path, monkeypatch):
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
        module.capture(_test_manifest(tmp_path), tmp_path / "case", fixtures={"case1": fixture})
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


def test_capture_delegates_to_read_only_core_cohort_path(tmp_path, monkeypatch):
    from evals.buddy_benchmark import workflow
    from evals.negative_retrieval.capture import capture

    manifest_path = _test_manifest(tmp_path)
    monkeypatch.setattr(workflow, "load_manifest", lambda *args, **kwargs: ({"conversation_mode": "build_sequence"}, tmp_path))
    calls = []
    def underlying(manifest, base, output, **options):
        calls.append(options)
        return "captured"
    monkeypatch.setattr(workflow, "_capture", underlying)
    assert capture(manifest_path, tmp_path / "out") == "captured"
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
