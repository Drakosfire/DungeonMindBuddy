from generationengine.types import BinaryDecisionAnswer, ChoiceDecisionAnswer

from evals.buddy_benchmark.heading_target_probe import PAGES, prepare, resolve


def test_wire_contains_only_request_titles_and_headings_and_preview_opens_exact_passage():
    request, targets = prepare("Add a signal to Mothfen's Watch.", PAGES)
    wire = request.model_dump_json()
    assert "Mothfen" in wire and "Watch" in wire
    assert "The west bell marks dusk" not in wire
    assert targets["h2"].digest not in wire
    assert len(request.questions) == 2 and request.max_transport_retries == 0
    answer = ChoiceDecisionAnswer(
        selected="h2", probabilities={"h1": 0, "h2": 0.95, "h3": 0, "h4": 0, "none": 0.05},
    )
    assert resolve(answer, targets, intent=BinaryDecisionAnswer(value=True, probability_true=0.95)) == {
        "page": "Mothfen", "heading": "Watch", "lines": [4, 5],
        "passage": "## Watch\nThe west bell marks dusk.\n",
    }


def test_unresolved_unoffered_or_malformed_choices_never_open_text():
    _, targets = prepare("Add a supplier to Trade.", PAGES)
    for answer in (
        ChoiceDecisionAnswer(selected="none", probabilities={"none": 1}),
        ChoiceDecisionAnswer(selected="h99", probabilities={"h99": 1}),
        ChoiceDecisionAnswer(selected="h1", probabilities={"h1": 1}),
        ChoiceDecisionAnswer(
            selected="h1", probabilities={"h1": 0.5, "h2": 0, "h3": 0.5, "h4": 0, "none": 0},
        ),
    ):
        assert resolve(answer, targets, intent=BinaryDecisionAnswer(value=True, probability_true=0.95)) is None

    confident = ChoiceDecisionAnswer(
        selected="h1", probabilities={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "none": 0},
    )
    assert resolve(confident, targets, intent=BinaryDecisionAnswer(value=False)) is None
    assert resolve(confident, targets, intent=None) is None
    assert resolve(confident, targets, intent=BinaryDecisionAnswer(value=True, probability_true=0.89)) is None
