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
