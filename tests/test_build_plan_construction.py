import json
import pytest
from apps.live_control_server.services.build_plan_construction import PlanStepProgress

ROWS = [
    {"text": "Inspect the “hinge” 雪😀.", "kind": "prepare_insertion"},
    {"text": "Discuss a possible handoff.", "kind": "discuss"},
]


@pytest.mark.parametrize("size", [1, 2, 3, 7, 19, 4096])
@pytest.mark.parametrize("kind_first", [True, False])
def test_complete_prefix_rows_arbitrary_json_partitions(size, kind_first):
    obj = (
        {"kind": "plan", "steps": ROWS}
        if kind_first
        else {"steps": ROWS, "kind": "plan"}
    )
    raw = json.dumps(
        {
            "answer_segments": [{"text": "decoy collaboration.steps"}],
            "collaboration": obj,
        },
        ensure_ascii=True,
    )
    decoder = PlanStepProgress()
    seen = []
    for i in range(0, len(raw), size):
        if decoder.feed(raw[i : i + size]):
            seen.append(decoder.steps)
    assert not decoder.invalid and decoder.root_done and decoder.steps == ROWS
    assert all(value == ROWS[: len(value)] for value in seen)


def test_only_completed_direct_rows_and_plan_kind_are_observed():
    d = PlanStepProgress()
    d.feed(
        '{"nested":{"collaboration":{"kind":"plan","steps":[{"text":"wrong","kind":"discuss"}]}},"collaboration":{"steps":['
    )
    d.feed(json.dumps(ROWS[0]) + ',{"text":"unfinished')
    assert d.steps == []
    d.feed(' text","kind":"discuss"}],"kind":"plan"}')
    assert d.steps == [ROWS[0], {"text": "unfinished text", "kind": "discuss"}]
    assert not d.root_done


@pytest.mark.parametrize(
    "tail",
    [
        '{"text":"bad","kind":"launch"}',
        '{"text":"bad","kind":"discuss","extra":true}',
        '{"text":"old","text":"new","kind":"discuss"}',
        '{"text":{},"kind":"discuss"}',
        '{"text":"\\uD800","kind":"discuss"}',
        '"not a row"',
    ],
)
def test_bad_rows_never_become_a_new_prefix(tail):
    d = PlanStepProgress()
    d.feed('{"collaboration":{"kind":"plan","steps":[' + json.dumps(ROWS[0]) + ",")
    d.feed(tail + "]}}")
    assert d.invalid and d.steps == ROWS[:1]


def test_duplicate_collaboration_and_invalid_escape_retire_observation():
    d = PlanStepProgress()
    d.feed(json.dumps({"collaboration": {"kind": "plan", "steps": ROWS}})[:-1])
    assert d.steps == ROWS
    d.feed(',"collaboration":{"kind":"questions"}}')
    assert d.invalid
    d = PlanStepProgress()
    d.feed('{"collaboration":{"kind":"plan","steps":[{"text":"\\q')
    d.feed('","kind":"discuss"}]}}')
    assert d.invalid


def test_mixed_schema_selects_only_its_known_base_plan_path():
    d = PlanStepProgress(("base_output", "collaboration"))
    raw = json.dumps(
        {
            "collaboration": {
                "kind": "plan",
                "steps": [{"text": "decoy", "kind": "discuss"}],
            },
            "base_output": {"collaboration": {"kind": "plan", "steps": ROWS}},
        }
    )
    for char in raw:
        d.feed(char)
    assert not d.invalid and d.steps == ROWS


def test_json_object_plan_is_a_pre_dispatch_error_not_a_transport_fallback():
    from types import SimpleNamespace
    from apps.live_control_server.services.build_jev_writer import (
        WriterProjection,
        with_plan_stream,
    )

    staged = WriterProjection(
        json.dumps({"response_contract": {"requested_work": "plan", "barrier": None}}),
        0,
        "prior",
    )
    request = SimpleNamespace(
        build_write_capability=object(), build_draft_context=object()
    )
    with pytest.raises(ValueError, match="closed provider schema"):
        with_plan_stream(staged, request)


def test_all_supported_typed_plan_policies_use_closed_schema_owner():
    from application_state.agent_conversation import types as t

    for name in (
        "BuildCollaborationPolicyV1",
        "BuildCollaborationImagePolicyV1",
        "BuildConnectedPageReviewPolicyV1",
        "BuildConnectedPageReviewImagePolicyV1",
        "BuildSourceQuotePolicyV1",
        "BuildSourceQuoteImagePolicyV1",
        "BuildRelationshipReviewPolicyV1",
        "BuildRelationshipReviewImagePolicyV1",
        "BuildIntentionalResponsePolicyV2",
        "BuildIntentionalResponseImagePolicyV2",
        "BuildIntentionalResponseSourcePolicyV2",
        "BuildIntentionalResponseSourceImagePolicyV2",
    ):
        assert issubclass(
            getattr(t, name), t.BuildCitedSourceActionControllerWriterPolicyV1
        )


@pytest.mark.parametrize('objective_first',[True,False])
def test_objective_stream_holds_rows_until_complete_real_outcome(objective_first):
    objective='A useful “hinge” repair scene 雪😀.'
    values={'objective':objective,'steps':ROWS} if objective_first else {'steps':ROWS,'objective':objective}
    decoder=PlanStepProgress(objective_required=True)
    raw=json.dumps({'collaboration':{'kind':'plan',**values}},ensure_ascii=True)
    observed=[]
    for c in raw:
        if decoder.feed(c):
            observed.append((decoder.objective,decoder.steps))
    assert decoder.root_done and not decoder.invalid
    assert decoder.objective==objective and decoder.steps==ROWS
    assert all(not rows or outcome==objective for outcome,rows in observed)
    assert any(outcome==objective for outcome,_ in observed)


def test_blank_duplicate_and_nontext_objectives_cannot_be_observed():
    for value in ['   ',None,[],{}]:
        decoder=PlanStepProgress(objective_required=True)
        decoder.feed(json.dumps({'collaboration':{'kind':'plan','objective':value,'steps':ROWS}}))
        assert decoder.invalid and decoder.steps==[]
    decoder=PlanStepProgress(objective_required=True)
    decoder.feed('{"collaboration":{"kind":"plan","objective":"Original","objective":"Changed","steps":[]}}')
    assert decoder.invalid and decoder.objective=='Original'


@pytest.mark.parametrize('size', [1, 3, 17, 4096])
@pytest.mark.parametrize('path', [('collaboration',), ('base_output', 'collaboration')])
def test_selected_complete_rows_keep_explicit_defer_across_stream_partitions(size, path):
    rows=[{**ROWS[0], 'selected':True}, {**ROWS[1], 'selected':False}]
    plan={'kind':'plan','objective':'Review the proposed repair before any writing.','steps':rows}
    value={'collaboration':plan} if len(path)==1 else {'base_output':{'collaboration':plan}}
    decoder=PlanStepProgress(path,objective_required=True,selection_required=True)
    raw=json.dumps(value,ensure_ascii=True)
    seen=[]
    for i in range(0,len(raw),size):
        if decoder.feed(raw[i:i+size]): seen.append(decoder.steps)
    assert decoder.root_done and not decoder.invalid and decoder.steps==rows
    assert all(value==rows[:len(value)] for value in seen)


@pytest.mark.parametrize('selection', ['missing', None, 'false', 0, 1, [], {}])
def test_selected_stream_rejects_missing_or_coerced_boolean(selection):
    row={**ROWS[0], 'selected':selection}
    if selection=='missing': row.pop('selected')
    decoder=PlanStepProgress(objective_required=True,selection_required=True)
    decoder.feed(json.dumps({'collaboration':{'kind':'plan','objective':'Review a repair.','steps':[row]}}))
    assert decoder.invalid and decoder.steps==[]


def test_selected_stream_does_not_expose_incomplete_selection():
    decoder=PlanStepProgress(objective_required=True,selection_required=True)
    decoder.feed('{"collaboration":{"kind":"plan","objective":"Review a repair.","steps":[{"text":"Defer writing","kind":"prepare_insertion","selected":fal')
    assert not decoder.invalid and decoder.steps==[]
    decoder.feed('se}]}}')
    assert decoder.root_done and decoder.steps[0]['selected'] is False
