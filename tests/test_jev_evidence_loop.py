import asyncio
from copy import deepcopy
import hashlib
import json

import pytest

from evals.graph_memory_layer.jev_evidence_loop import run_loop, validate_snapshot
from evals.graph_memory_layer.run_jev_evidence_loop import score_gold


def fixture():
    scope = {"world_id": "synthetic", "graph_revision": "r1", "source_revision": "s1"}
    units = {}
    for uid, text in [("u1", "Aster leads the assembly."), ("u2", "The assembly governs Harbor."),
                      ("u3", "Some goats produce milk.")]:
        units[uid] = {"id": uid, "subject": uid, "text": text, "scope": scope.copy(),
                      "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "source_class": "world_reference", "provenance": [{"start_line": 1, "end_line": 1}]}
    return {"schema": "dmb_jev_loop_snapshot_v1", **scope, "source_sha256": "f" * 64,
            "model": "jev-1.14.0", "question": "How does Aster relate to Harbor government?",
            "requirements": [{"id": "leader", "text": "Who does Aster lead?"},
                             {"id": "government", "text": "What governs Harbor?"}],
            "units": units, "actions": {
                "a1": {"id": "a1", "label": "Aster observations", "kind": "graph_observations", "unit_ids": ["u1"]},
                "a2": {"id": "a2", "label": "Assembly neighborhood citation", "kind": "graph_observations", "unit_ids": ["u2"]},
                "a3": {"id": "a3", "label": "Goats", "kind": "saved_build_section", "unit_ids": ["u3"]}},
            "initial_actions": ["a1"]}


def decisions(request, *, missing=False, conflict=False, bad=False):
    ids = {e["id"] for e in request["state"]["evidence"]}
    answers = {}
    for q in request["questions"]:
        name = q["name"]
        if q["kind"] == "binary":
            answers[name] = {"kind": "binary", "value": not name.endswith("u3"),
                             "probability_true": .01 if name.endswith("u3") else .99}
        else:
            target = "u1" if name.endswith("leader") else "u2"
            supported = target in ids and not missing
            selected = ("conflict" if conflict else "sufficient" if supported else "more_evidence") if name.startswith("coverage_") else target if name.startswith("support_") and supported else "a2" if name.startswith("next_") and "a2" in q["options"] else "none"
            answers[name] = {"kind": "choice", "selected": "invented" if bad else selected}
    return {"answers": answers, "observation": {"input_tokens": 100, "output_tokens": 20, "response_model": "jev-1.14.0"}}


def test_missing_link_targets_next_action_without_repeating(tmp_path):
    calls = []
    async def evaluate(request):
        calls.append(request)
        return decisions(request)
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "provisionally_supported"
    assert len(calls) == 2
    assert [e["action_id"] for e in result["retrieval_events"]] == ["a1", "a2"]
    assert result["rounds"][0]["unresolved"] == ["government"]
    assert result["input_tokens_reported"] == 200
    assert result["luna_calls"] == 0
    assert {u["id"] for u in result["selected_evidence"]} == {"u1", "u2"}


def test_exhaustion_is_not_sufficiency_or_an_unchanged_retry(tmp_path):
    async def evaluate(request):
        return decisions(request, missing=True)
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "retrieval_exhausted"
    assert len(result["rounds"]) == 2
    assert result["unresolved_requirements"] == ["leader", "government"]


def test_conflict_is_retained_and_stops_for_qualification(tmp_path):
    async def evaluate(request):
        return decisions(request, conflict=True)
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "conflict_requires_qualification"
    assert result["selected_evidence"]


def test_malformed_action_never_executes_and_reported_usage_is_preserved(tmp_path):
    async def evaluate(request):
        return decisions(request, bad=True)
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "decision_unavailable_or_invalid"
    assert len(result["retrieval_events"]) == 2
    assert result["usage_status"] == "reported"
    assert result["input_tokens_reported"] == 100
    assert (tmp_path / "run/round-01-response.json").exists()


def test_provider_failure_preserves_start_marker_and_does_not_retry(tmp_path):
    calls = []
    async def evaluate(request):
        calls.append(request)
        raise TimeoutError()
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert len(calls) == 1
    assert result["usage_status"] == "unavailable_or_partial_not_zero"
    assert result["status"] == "decision_unavailable_or_invalid"
    assert (tmp_path / "run/round-01-started.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))


@pytest.mark.parametrize("change", ["scope", "body", "unknown_unit"])
def test_bad_snapshot_fails_before_provider(change):
    snapshot = fixture()
    if change == "scope":
        snapshot["units"]["u1"]["scope"]["world_id"] = "foreign"
    elif change == "body":
        snapshot["units"]["u1"]["text"] = "changed"
    else:
        snapshot["actions"]["a1"]["unit_ids"] = ["foreign"]
    with pytest.raises(ValueError):
        validate_snapshot(snapshot)


def test_name_matching_distractor_excluded_and_gold_separate(tmp_path):
    snapshot = fixture()
    snapshot["initial_actions"] = ["a1", "a2", "a3"]
    async def evaluate(request):
        assert "facts" not in json.dumps(request)
        return decisions(request)
    result = asyncio.run(run_loop(snapshot, evaluate, output=tmp_path / "run"))
    assert result["status"] == "provisionally_supported"
    assert "u3" not in {u["id"] for u in result["selected_evidence"]}
    score = score_gold(result, {"facts": [{"id": "governs", "evidence": [{"quote": "governs Harbor", "start_line": 1, "end_line": 1}]}]})
    assert score["recall"] == 1
    altered = deepcopy(result)
    altered["selected_evidence"] = [snapshot["units"]["u1"]]
    assert score_gold(altered, {"facts": [{"id": "governs", "evidence": [{"quote": "governs Harbor", "start_line": 1, "end_line": 1}]}]})["false_sufficient_stop"]


def test_independent_missing_requirements_retrieved_in_one_wave(tmp_path):
    snapshot = fixture()
    snapshot["initial_actions"] = ["a3"]
    async def evaluate(request):
        result = decisions(request)
        for rid, action in [("leader", "a1"), ("government", "a2")]:
            key = "next_" + rid
            q = next((q for q in request["questions"] if q["name"] == key), None)
            if q and action in q["options"]:
                result["answers"][key]["selected"] = action
        return result
    result = asyncio.run(run_loop(snapshot, evaluate, output=tmp_path / "run"))
    assert result["rounds"][0]["next_actions"] == ["a1", "a2"]
    assert len(result["rounds"]) == 2
    assert result["status"] == "provisionally_supported"


def test_sufficient_without_relevant_support_cannot_complete(tmp_path):
    async def evaluate(request):
        result = decisions(request)
        for value in result["answers"].values():
            if value["kind"] == "binary":
                value.update(value=False, probability_true=0.0)
        return result
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "retrieval_exhausted"
    assert result["unresolved_requirements"] == ["leader", "government"]


def test_discovery_hints_are_explicitly_not_support(tmp_path):
    async def evaluate(request):
        assert 'Legal action labels are discovery hints, never evidence' in request['state']['rules']
        return decisions(request)
    asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))


@pytest.mark.parametrize("returned", [None, "jev-1.13.0", "gpt-6-luna"])
def test_returned_model_mismatch_retains_usage_and_stops(tmp_path, returned):
    async def evaluate(request):
        result = decisions(request)
        result["observation"]["response_model"] = returned
        return result
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "decision_unavailable_or_invalid"
    assert len(result["observations"]) == 1
    assert result["input_tokens_reported"] == 100
    assert result["observations"][0]["response_model"] == returned
    assert (tmp_path / "run").stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("missing", ["model", "observation"])
def test_missing_model_identity_never_completes(tmp_path, missing):
    async def evaluate(request):
        result = decisions(request)
        if missing == "model":
            del result["observation"]["response_model"]
        else:
            del result["observation"]
        return result
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path / "run"))
    assert result["status"] == "decision_unavailable_or_invalid"
    assert not result["rounds"]
    assert len(result["retrieval_events"]) == 2


def heading_fixture():
    snapshot = fixture()
    for i, text in [(4, '## Outer heading'), (5, '### Empty nested heading')]:
        uid = f'u{i}'
        unit = deepcopy(snapshot['units']['u3'])
        unit.update(id=uid, text=text, content_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    provenance=[{'start_line':i, 'end_line':i}])
        snapshot['units'][uid] = unit
        snapshot['actions'][f'a{i}'] = {'id':f'a{i}', 'label':text,
            'kind':'saved_build_section', 'unit_ids':[uid], 'continuation_action_ids':[f'a{i+1}']}
    unit = deepcopy(snapshot['units']['u2'])
    unit['provenance'] = [{'start_line':6,'end_line':7}]
    snapshot['units']['u2'] = unit
    snapshot['actions']['a6'] = {'id':'a6','label':'Adjacent body context',
        'kind':'saved_build_section','unit_ids':['u2']}
    snapshot['initial_actions'] = ['a1','a4']
    return snapshot


def test_heading_navigation_reaches_body_without_extra_decision_round(tmp_path):
    calls = []
    async def evaluate(request):
        calls.append(request)
        return decisions(request)
    result = asyncio.run(run_loop(heading_fixture(), evaluate, output=tmp_path/'run'))
    assert len(calls) == 1
    assert result['status'] == 'provisionally_supported'
    assert [e['action_id'] for e in result['retrieval_events']] == ['a1','a4','a5','a6']
    assert result['retrieval_events'][-1]['reason'] == 'heading_only_adjacent_source_context'


@pytest.mark.parametrize('change', ['backward','overlap','unknown','graph'])
def test_invalid_structural_continuations_reject_before_inference(change):
    snapshot = heading_fixture()
    if change == 'backward':
        snapshot['actions']['a5']['continuation_action_ids'] = ['a4']
    elif change == 'overlap':
        snapshot['units']['u2']['provenance'][0]['start_line'] = 5
    elif change == 'unknown':
        snapshot['actions']['a4']['continuation_action_ids'] = ['foreign']
    else:
        snapshot['actions']['a5']['continuation_action_ids'] = ['a2']
    with pytest.raises(ValueError):
        validate_snapshot(snapshot)


def test_substantive_section_does_not_follow_navigation_pointer(tmp_path):
    snapshot = heading_fixture()
    snapshot['units']['u4']['text'] += '\nThis section has its own body.'
    snapshot['units']['u4']['content_sha256'] = hashlib.sha256(snapshot['units']['u4']['text'].encode()).hexdigest()
    async def evaluate(request):
        result = decisions(request)
        for key in result['answers']:
            if key.startswith('next_'):
                result['answers'][key]['selected'] = 'none'
        return result
    result = asyncio.run(run_loop(snapshot, evaluate, output=tmp_path/'run'))
    assert [e['action_id'] for e in result['retrieval_events']] == ['a1','a4']
    assert result['status'] == 'retrieval_exhausted'


def test_question_only_plans_before_reads_and_discards_manual_decomposition(tmp_path):
    snap = fixture()
    snap['initial_actions'] = ['a3']
    original = deepcopy(snap)
    calls = []
    async def evaluate(request):
        calls.append(request)
        ids = {u['id'] for u in request['state']['evidence']}
        complete = {'u1', 'u2'} <= ids
        answers = {}
        for q in request['questions']:
            if q['kind'] == 'binary':
                answers[q['name']] = {'kind': 'binary', 'probability_true': .99}
            else:
                selected = ('sufficient' if complete else 'more_evidence') if q['name'].startswith('coverage_') else ('u2' if complete else 'none') if q['name'].startswith('support_') else 'a1' if not ids else 'a2' if not complete else 'none'
                answers[q['name']] = {'kind': 'choice', 'selected': selected}
        return {'answers': answers, 'observation': {'response_model': 'jev-1.14.0'}}
    result = asyncio.run(run_loop(snap, evaluate, output=tmp_path/'run', question_only=True))
    assert snap == original
    assert calls[0]['state']['evidence'] == []
    assert calls[0]['state']['requirements'] == [{'id': 'answer', 'text': snap['question']}]
    assert [e['action_id'] for e in result['retrieval_events']] == ['a1', 'a2']
    assert result['status'] == 'provisionally_supported'
    assert len(calls) == 3


def test_question_only_unsupported_bootstrap_sufficiency_cannot_pass(tmp_path):
    async def evaluate(request):
        assert request['state']['evidence'] == []
        answers = {q['name']: {'kind': 'choice', 'selected': 'sufficient' if q['name'].startswith('coverage_') else 'none'}
                   for q in request['questions']}
        return {'answers': answers, 'observation': {'response_model': 'jev-1.14.0'}}
    result = asyncio.run(run_loop(fixture(), evaluate, output=tmp_path/'run', question_only=True))
    assert result['status'] == 'retrieval_exhausted'
    assert result['selected_evidence'] == []
    assert result['unresolved_requirements'] == ['answer']


def test_competing_action_is_opened_and_entire_evidence_reevaluated(tmp_path):
    snap = fixture()
    snap['requirements'] = [snap['requirements'][0]]
    snap['units']['u2']['text'] = 'Aster does not lead the assembly. Both claims are current and unresolved.'
    snap['units']['u2']['content_sha256'] = hashlib.sha256(snap['units']['u2']['text'].encode()).hexdigest()
    calls = []
    async def evaluate(request):
        calls.append(request)
        if request['state'].get('phase') == 'challenge_tentative_sufficiency':
            assert [u['id'] for u in request['state']['evidence']] == ['u1']
            return {'answers': {'challenge_action': {'kind': 'choice', 'selected': 'a2'}},
                    'observation': {'response_model': 'jev-1.14.0'}}
        return decisions(request, conflict=len(request['state']['evidence']) == 2)
    result = asyncio.run(run_loop(snap, evaluate, output=tmp_path/'run', challenge_before_stop=True))
    assert result['status'] == 'conflict_requires_qualification'
    assert [e['action_id'] for e in result['retrieval_events']] == ['a1', 'a2']
    assert {u['id'] for u in result['selected_evidence']} == {'u1', 'u2'}
    assert len(calls) == 3
    assert [u['id'] for u in calls[-1]['state']['evidence']] == ['u1', 'u2']
    assert (tmp_path/'run/challenge-01-started.json').exists()


@pytest.mark.parametrize('choice,status', [
    ('none', 'provisionally_supported'), ('unknown', 'coverage_unknown'),
    ('foreign', 'challenge_unavailable_or_invalid'), ('timeout', 'challenge_unavailable_or_invalid'),
])
def test_challenge_none_is_heuristic_unknown_and_failure_cannot_pass(tmp_path, choice, status):
    snap = fixture()
    snap['requirements'] = [snap['requirements'][0]]
    calls = []
    async def evaluate(request):
        calls.append(request)
        if request['state'].get('phase') == 'challenge_tentative_sufficiency':
            if choice == 'timeout':
                raise TimeoutError()
            return {'answers': {'challenge_action': {'kind': 'choice', 'selected': choice}},
                    'observation': {'response_model': 'jev-1.14.0'}}
        return decisions(request)
    result = asyncio.run(run_loop(snap, evaluate, output=tmp_path/'run', challenge_before_stop=True))
    assert result['status'] == status
    assert len(calls) == 2  # No uncertain challenge retry.
    if choice == 'none':
        assert result['rounds'][-1]['coverage_judgment'] == 'heuristic_no_plausible_unread_competitor'
    else:
        assert result['unresolved_requirements'] == result['rounds'][-1]['unresolved'] == ['leader']


def test_coverage_acquires_all_useful_actions_as_one_validated_wave(tmp_path):
    snap = fixture()
    snap['requirements'] = [snap['requirements'][0]]
    waves, evidence_seen = [], []
    async def acquire(actions):
        waves.append([a['id'] for a in actions])
        return {a['id']: [snap['units'][uid] for uid in a['unit_ids']] for a in actions}
    async def evaluate(request):
        if request['state'].get('phase') == 'unread_coverage_before_sufficiency':
            return {'answers': {q['name']: {'kind': 'choice', 'selected': 'useful'} for q in request['questions']},
                    'observation': {'response_model': 'jev-1.14.0'}}
        evidence_seen.append([u['id'] for u in request['state']['evidence']])
        return decisions(request)
    result = asyncio.run(run_loop(snap, evaluate, output=tmp_path/'run', retrieve_many=acquire,
                                  coverage_before_stop=True))
    assert waves == [['a1'], ['a2', 'a3']]
    assert evidence_seen == [['u1'], ['u1', 'u2', 'u3']]
    assert result['status'] == 'provisionally_supported'
    assert result['rounds'][0]['challenge']['selected_actions'] == ['a2', 'a3']
    assert result['rounds'][-1]['coverage_judgment'] == 'legal_catalog_exhausted_not_world_complete'


@pytest.mark.parametrize('fault,expected', [('unknown','retrieval_unavailable_or_invalid'),
    ('missing_key','challenge_unavailable_or_invalid'), ('partial_batch','retrieval_unavailable_or_invalid')])
def test_coverage_unknown_malformed_and_partial_wave_hold_success(tmp_path, fault, expected):
    snap = fixture()
    snap['requirements'] = [snap['requirements'][0]]
    decisions_count = []
    async def acquire(actions):
        loaded = {a['id']: [snap['units'][uid] for uid in a['unit_ids']] for a in actions}
        if fault == 'unknown' and len(actions) > 1:
            raise TimeoutError()
        if fault == 'partial_batch' and len(actions) > 1:
            loaded.pop('a3')
        return loaded
    async def evaluate(request):
        decisions_count.append(request)
        if request['state'].get('phase') == 'unread_coverage_before_sufficiency':
            answers = {q['name']: {'kind': 'choice', 'selected': 'unknown' if fault == 'unknown' else 'useful'}
                       for q in request['questions']}
            if fault == 'missing_key':
                answers.pop(next(iter(answers)))
            return {'answers': answers, 'observation': {'response_model': 'jev-1.14.0'}}
        return decisions(request)
    result = asyncio.run(run_loop(snap, evaluate, output=tmp_path/'run', retrieve_many=acquire,
                                  coverage_before_stop=True))
    assert result['status'] == expected
    assert len(decisions_count) == 2
    from evals.graph_memory_layer.jev_live_evidence import writer_request
    with pytest.raises(ValueError):
        writer_request(result, snap['question'])


def test_experimental_stopping_policies_are_mutually_exclusive(tmp_path):
    with pytest.raises(ValueError, match='one experimental'):
        asyncio.run(run_loop(fixture(), None, output=tmp_path/'run', challenge_before_stop=True,
                             coverage_before_stop=True))
    assert not (tmp_path/'run').exists()


@pytest.mark.parametrize('label,probability,reads,unknown', [
    ('useful', .0, ['a1'], []), ('unknown', .5, ['a1'], ['a1']),
    ('not_useful', .62, ['a1'], ['a1']), ('not_useful', .95, [], []),
    ('not_useful', None, ['a1'], ['a1']),
])
def test_coverage_only_skips_confident_negative_hints(label, probability, reads, unknown):
    from evals.graph_memory_layer.jev_evidence_loop import coverage_disposition
    answer = {'selected':label}
    if probability is not None:
        answer['probabilities'] = {'not_useful':probability}
    chosen, uncertain, skipped = coverage_disposition([{'id':'a1'}], {'use_a1':answer}, .9)
    assert chosen == reads and uncertain == unknown
    assert skipped == ([] if reads else ['a1'])


@pytest.mark.parametrize('probability', [True, float('nan'), -1, 1.2, 'high'])
def test_invalid_coverage_probability_cannot_exclude_evidence(probability):
    from evals.graph_memory_layer.jev_evidence_loop import coverage_disposition
    with pytest.raises(ValueError, match='probability'):
        coverage_disposition([{'id':'a1'}], {'use_a1': {'selected':'not_useful',
            'probabilities': {'not_useful':probability}}}, .9)
