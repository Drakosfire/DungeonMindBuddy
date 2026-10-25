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


@pytest.mark.parametrize(
    "observation,complete,tokens",
    [({"input_tokens": 17, "output_tokens": 3}, True, 17), (None, False, 0)],
)
def test_proof_retains_failure_usage_without_inventing_image_refusal(
    observation, complete, tokens
):
    from evals.utterance_intent.response_proof import summarize

    row = {
        "variant": "candidate",
        "family": "synthetic_failure",
        "expected": "answer_from_sources",
        "question_sha256": "test",
        "correct": False,
        "error": {"type": "SDKFailure"},
        "routing_provider_calls": 1,
        "response": None,
        "failure_observation": observation,
    }
    group = next(
        g
        for g in summarize([row])
        if g["family"] == "all" and g["variant"] == "candidate"
    )
    assert group["usage_complete"] is complete
    assert group["known_input_tokens"] == tokens
    assert group["known_output_tokens"] == (3 if complete else 0)
    assert group["calls_with_unknown_usage"] == (0 if complete else 1)
    assert group["errors"] == 1 and group["image_gate_failures"] == 0


def test_proof_separates_non_image_tie_from_image_threshold_refusal():
    from evals.utterance_intent.response_proof import image_status

    row = {
        "routing_provider_calls": 1,
        "error": {"type": "ValueError"},
        "response": {
            "answers": {
                "operation": {
                    "selected": "answer_from_sources",
                    "probabilities": {
                        "answer_from_sources": 0.5,
                        "propose_build_insertion": 0.5,
                    },
                }
            }
        },
    }
    assert image_status(row) == "not_applicable"
    row["response"]["answers"]["operation"] = {
        "selected": "prepare_build_image",
        "probabilities": {"prepare_build_image": 0.8},
    }
    assert image_status(row) == "refused"


@pytest.mark.parametrize("known_usage", [True, False])
def test_actual_proof_failure_path_keeps_known_observation(
    tmp_path, monkeypatch, known_usage
):
    import asyncio
    import json
    from generationengine import GenerationClient
    from evals.utterance_intent.response_proof import run

    class Failure(Exception):
        observation = {"input_tokens": 17, "output_tokens": 3} if known_usage else None

    class FailingClient:
        async def decide(self, request):
            raise Failure("controlled provider failure; no network")

        async def aclose(self):
            pass

    monkeypatch.setattr(GenerationClient, "from_env", lambda: FailingClient())
    control = {
        "model": "jev-1.14.0",
        "questions": {"operation": registry.operation_question(OPS)},
        "state": {
            "decision": {
                "state": {"interaction": {"allowed_operations": list(OPS)}},
                "questions": [],
            }
        },
    }
    case = {
        "id": "controlled-failure",
        "family": "failure_boundary",
        "origin": "constructed",
        "question": "Clarify what I mean.",
        "expected": "answer_from_sources",
        "original_expected": None,
        "control": control,
    }
    output = tmp_path / "proof"
    asyncio.run(run([case], output))
    report = json.loads((output / "report.json").read_text())
    for group in [g for g in report["groups"] if g["family"] == "all"]:
        assert group["errors"] == 2 and group["image_gate_failures"] == 0
        assert group["usage_complete"] is known_usage
        assert group["known_input_tokens"] == (34 if known_usage else 0)
        assert group["known_output_tokens"] == (6 if known_usage else 0)
    row = json.loads((output / "controlled-failure-candidate-0.json").read_text())
    assert row["failure_observation"] == (
        {"input_tokens": 17, "output_tokens": 3} if known_usage else None
    )
