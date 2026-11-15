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
            events=events, before="original", after="original", fulfilled=fulfilled
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
