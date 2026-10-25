import pytest
from generationengine.types import DecisionRequest
from apps.live_control_server.services import build_action_registry as registry
from evals.utterance_intent.proof import sdk_request


OPS = ("answer_from_sources", "prepare_build_image", "propose_build_insertion")


def test_actual_sdk_preserves_the_complete_described_menu():
    wire = registry.operation_question(OPS)
    request = DecisionRequest.model_validate(
        sdk_request(
            {"model": "jev-1.14.0", "state": {}, "questions": {"operation": wire}}
        )
    )
    question = request.questions[0]
    assert tuple(question.options) == OPS
    assert dict(question.option_descriptions) == wire["criteria"]
    assert "cannot_select" not in question.options
    with pytest.raises(ValueError, match="Singleton"):
        registry.operation_question(("answer_from_sources",))


def test_no_editor_is_host_channel_selection_with_no_fake_provider_response():
    assert registry.singleton_channel(("answer_from_sources",)) == "answer_from_sources"
    assert registry.singleton_channel(OPS) is None
    projection = registry.writer_contract(
        ("answer_from_sources",), "answer_from_sources"
    )
    assert [row["operation"] for row in projection["offered_outputs"]] == [
        "answer_from_sources"
    ]
    assert projection["enabled_reviews"] == []
    assert not {"probabilities", "provider_attempt_id", "usage"} & projection.keys()
    with pytest.raises(ValueError, match="not admitted"):
        registry.writer_contract(("answer_from_sources",), "propose_build_insertion")


@pytest.mark.parametrize(
    "operations",
    [
        (),
        ("answer_from_sources", "answer_from_sources"),
        ("propose_build_insertion",),
        ("answer_from_sources", "execute_encounter"),
        ("answer_from_sources", "cannot_select"),
    ],
)
def test_foreign_empty_duplicate_or_write_only_capabilities_fail_closed(operations):
    with pytest.raises(ValueError):
        registry.offered(operations)


def test_review_availability_is_explicit_and_projection_cannot_mutate_registry():
    a = registry.writer_contract(
        OPS, "answer_from_sources", enabled_reviews=("questions", "plan")
    )
    a["offered_outputs"][0]["description"] = "changed"
    b = registry.writer_contract(OPS, "answer_from_sources")
    assert b["offered_outputs"][0]["description"] != "changed"
    assert b["enabled_reviews"] == []
    with pytest.raises(ValueError):
        registry.writer_contract(
            OPS, "answer_from_sources", enabled_reviews=("automatic_publication",)
        )
