from evals.buddy_benchmark.action_assessment import assess_conversation_only


def test_dismissal_cannot_clear_unsolicited_proposal():
    result = assess_conversation_only(
        events=["proposal_created", "proposal_dismissed"],
        before={"page": "original"},
        after={"page": "original"},
        fulfilled=True,
    )
    assert result == {
        "status": "fail",
        "unwanted_effects": ["proposal_created"],
        "protected_state_changed": False,
        "fulfilled": True,
    }


def test_conversation_requires_both_fulfillment_and_observed_non_action():
    for events, fulfilled, status in [
        ([], True, "pass"),
        ([], False, "fail"),
        (None, True, "unproven"),
        ([], None, "unproven"),
    ]:
        result = assess_conversation_only(
            events=events, before="original", after="original", fulfilled=fulfilled,
            journal_complete=True
        )
        assert result["status"] == status


def test_action_report_requires_pinned_observation(tmp_path):
    from hashlib import sha256
    import json
    import pytest
    from evals.buddy_benchmark.workflow import action_report

    observation = tmp_path / "observation.json"
    observation.write_text(json.dumps({
        "events": ["proposal_created", "proposal_dismissed"],
        "before": "original",
        "after": "original",
        "fulfilled": True,
    }))
    pin = {"path": observation.name, "sha256": sha256(observation.read_bytes()).hexdigest()}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema": "dmb_aw_assessment_v1",
        "cases": [{"id": "PA01", "observation": pin}],
    }))
    result = action_report(manifest)["cases"][0]
    assert result["status"] == "fail"
    assert result["unwanted_effects"] == ["proposal_created"]
    observation.write_text("{}")
    with pytest.raises(ValueError, match="Evidence pin mismatch"):
        action_report(manifest)


def test_confirmed_action_detects_duplicate_and_preconfirmation_writes():
    from evals.buddy_benchmark.action_assessment import assess_confirmed_action

    edit = {"target": "edge/row-2", "effect": "replace"}
    evidence = dict(before_confirmation=[], mutations=[edit], expected_mutations=[edit],
                    reopened=True, protected_state_changed=False)
    assert assess_confirmed_action(**evidence)["status"] == "pass"
    assert assess_confirmed_action(**{**evidence, "mutations": [edit, edit]})["status"] == "fail"
    assert assess_confirmed_action(**{**evidence, "before_confirmation": [edit]})["status"] == "fail"


def test_blocked_action_requires_evidence_of_no_mutation_or_success():
    from evals.buddy_benchmark.action_assessment import assess_blocked_action

    evidence = dict(mutations=[], success_receipts=[], missing_prerequisite=True,
                    candidate_preserved=True)
    assert assess_blocked_action(**evidence)["status"] == "pass"
    assert assess_blocked_action(**{**evidence, "success_receipts": ["receipt"]})["status"] == "fail"
    assert assess_blocked_action(**{**evidence, "mutations": None})["status"] == "unproven"


def test_malformed_and_partial_evidence_cannot_pass():
    import pytest
    from evals.buddy_benchmark.action_assessment import assess_confirmed_action

    observation = dict(events=[], before="original", after="original", fulfilled=True)
    for invalid in (dict(events="proposal_created"), dict(fulfilled="false")):
        with pytest.raises(ValueError):
            assess_conversation_only(**(observation | invalid))
    with pytest.raises(ValueError, match="reopened"):
        assess_confirmed_action(before_confirmation=[], mutations=[], expected_mutations=[{"target": "edge", "effect": "replace"}],
                                reopened="false", protected_state_changed=False)
    assert assess_conversation_only(**observation)["status"] == "unproven"
    assert assess_conversation_only(**observation, journal_complete=False)["status"] == "unproven"
    assert assess_conversation_only(
        **(observation | {"events": ["proposal_created"]}), journal_complete=False
    )["status"] == "fail"


def test_confirmed_action_requires_an_expected_mutation():
    import pytest
    from evals.buddy_benchmark.action_assessment import assess_confirmed_action

    with pytest.raises(ValueError, match="at least one mutation"):
        assess_confirmed_action(before_confirmation=[], mutations=[], expected_mutations=[],
                                reopened=True, protected_state_changed=False)


def test_action_checkpoint_invalidates_changed_fixture_and_predecessor(tmp_path):
    from evals.buddy_benchmark.artifacts import action_checkpoint

    def run(fixture, predecessor):
        return action_checkpoint(tmp_path, stage="readback",
                                 binding={"fixture": fixture, "predecessor": predecessor},
                                 observe=lambda: {"fresh": True})

    original, reused = run("fixture-a", "previous-a")
    assert not reused
    assert run("fixture-a", "previous-a") == (original, True)
    for fixture, predecessor in (("fixture-b", "previous-a"), ("fixture-a", "previous-b")):
        fresh, reused = run(fixture, predecessor)
        assert not reused and fresh["digest"] != original["digest"]


def test_action_report_pins_trace_metrics_to_expected_turn(tmp_path):
    from hashlib import sha256
    import json

    import pytest
    from evals.buddy_benchmark.workflow import action_report

    def pin(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": name, "sha256": sha256(path.read_bytes()).hexdigest()}

    observation = pin("observation.json", {
        "events": [], "before": "same", "after": "same",
        "fulfilled": True, "journal_complete": True,
    })
    trace = {
        "schema": "dmb_agent_turn_trace_v1", "turn_id": "turn-1", "elapsed_ms": 23,
        "usage": {"total_tokens": 42, "model_call_count": 2, "status": "partial",
                  "usage_reported_call_count": 1},
        "cost": {"usd": None, "status": "unavailable"},
        "spans": [{"kind": "phase", "name": "route", "duration_ms": 3, "status": "ok"}],
    }
    case = {
        "id": "PA01", "turn_id": "turn-1", "observation": observation,
        "turn_capture": pin("capture.json", {"body": {"turn_id": "turn-1", "answer": {"trace": trace}}}),
    }
    manifest = tmp_path / "manifest.json"

    def report():
        manifest.write_text(json.dumps({"schema": "dmb_aw_assessment_v1", "cases": [case]}))
        return action_report(manifest)["cases"][0]

    result = report()
    assert result["status"] == "pass"
    assert result["turn_capture"] == case["turn_capture"]
    assert result["operation"] == {
        "elapsed_ms": 23, "model_tokens": 42, "model_calls": 2, "reported_cost_usd": None,
        "usage_status": "partial", "usage_reported_call_count": 1,
        "cost_status": "unavailable", "operator_interventions": None,
        "stages": [{"name": "route", "duration_ms": 3, "status": "ok"}],
    }
    case["turn_id"] = "different-turn"
    with pytest.raises(ValueError, match="expected turn"):
        report()
    (tmp_path / "capture.json").write_text("{}")
    with pytest.raises(ValueError, match="Evidence pin mismatch"):
        report()
