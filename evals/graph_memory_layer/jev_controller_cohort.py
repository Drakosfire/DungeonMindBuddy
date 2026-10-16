"""Constructed synthetic holdouts; gold is host-only, never decision state."""
from __future__ import annotations

import hashlib
from copy import deepcopy


def _case(question, texts, requirements, expected_status, support_ids, *, initial=None):
    scope = {'world_id': 'synthetic:moonwell', 'graph_revision': 'rev:cohort1',
             'source_revision': 'source:cohort1'}
    units, actions = {}, {}
    for n, (label, text) in enumerate(texts, 1):
        uid, aid = f'u{n}', f'a{n}'
        units[uid] = {'id': uid, 'subject': label, 'text': text, 'scope': scope.copy(),
                      'source_class': 'world_reference', 'provenance': [{'start_line': n, 'end_line': n}],
                      'content_sha256': hashlib.sha256(text.encode()).hexdigest()}
        actions[aid] = {'id': aid, 'label': label, 'kind': 'graph_observations', 'unit_ids': [uid]}
    snapshot = {'schema': 'dmb_jev_loop_snapshot_v1', **scope, 'source_sha256': 'f'*64,
                'model': 'jev-1.14.0', 'question': question,
                'requirements': [{'id': f'r{n}', 'text': text} for n, text in enumerate(requirements, 1)],
                'units': units, 'actions': actions, 'initial_actions': initial or ['a1']}
    return {'snapshot': snapshot, 'gold': {'expected_status': expected_status,
            'required_selected_ids': support_ids,
            'interpretation': 'Constructed scenario; explicit source statements and qualifications are gold.'}}


def cases():
    question = "What connects Nera's lantern to Moonwell?"
    facts = [('Nera lantern fuel record', "Nera's lantern burns gleam moss as fuel."),
             ('Gleam moss harvest record', 'The gleam moss used in that lantern is harvested at Moonwell.'),
             ('Moonwell festival lights', 'Moonwell hangs blue ribbons during its annual festival.')]
    out = {'two_hop_granular': _case(question, facts,
        ["Identify the lantern's fuel.", 'Identify where that fuel is harvested.'],
        'provisionally_supported', ['u1', 'u2'])}
    out['two_hop_whole_question'] = _case(question, facts, [question],
        'provisionally_supported', ['u1', 'u2'])
    out['missing_harvest_relation'] = _case(question,
        [facts[0], ('Gleam moss botanical record', 'Gleam moss glows green. This record does not identify its harvest location.'), facts[2]],
        ["Identify the lantern's fuel.", 'Identify where that fuel is harvested.'],
        'retrieval_exhausted', ['u1'])
    out['conflicting_same_time_claims'] = _case('Which fuel does the lantern use on Day 3?',
        [('Day 3 source A', 'On Day 3 the lantern uses only gleam moss as fuel.'),
         ('Day 3 source B', 'On Day 3 the same lantern uses only reed oil as fuel. Neither source has been superseded.')],
        ['Determine the fuel used on Day 3, preserving unresolved conflicting source claims.'],
        'conflict_requires_qualification', ['u1', 'u2'], initial=['a1', 'a2'])
    out['temporal_update_is_not_conflict'] = _case('Is the bridge open on Day 2?',
        [('Bridge Day 1 record', 'On Day 1 the bridge was closed.'),
         ('Bridge Day 2 record', 'On Day 2 repairs finished and the bridge reopened.')],
        ['Determine bridge access on Day 2; an earlier state is not a simultaneous contradiction.'],
        'provisionally_supported', ['u2'])
    out['belief_is_not_confirmed_cause'] = _case('Who actually caused the blue lights?',
        [('Nera testimony', 'Nera believes Voss caused the blue lights, but she has no evidence.'),
         ('Blue lights investigation', 'Investigators have not established who caused the blue lights.')],
        ['Identify the established actual cause, distinguishing belief from confirmed fact.'],
        'retrieval_exhausted', [])
    return deepcopy(out)


def score_case(result, gold):
    selected = {u['id'] for u in result['selected_evidence']}
    missing = sorted(set(gold['required_selected_ids']) - selected)
    stop_matches = result['status'] == gold['expected_status']
    return {'expected_status': gold['expected_status'], 'actual_status': result['status'],
            'stop_matches': stop_matches, 'missing_required_selected_ids': missing,
            'passed': stop_matches and not missing,
            'accuracy_scope': 'constructed stopping and required support, not generated answer accuracy',
            'semantic_review': 'required'}
