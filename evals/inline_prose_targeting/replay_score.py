"""Offline supplied-decision scorer. Never calls models or applies edits."""
import argparse
import hashlib
import json
from pathlib import Path


def decode_json(value):
    def unique_object(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError('Duplicate JSON object key: ' + key)
            result[key] = item
        return result
    return json.loads(value, object_pairs_hook=unique_object)


def keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('Unexpected protocol fields')


def score(input_bytes, manifest, replay):
    inputs = decode_json(input_bytes)
    keys(inputs, ['schema', 'split', 'cases'])
    keys(manifest, ['schema', 'inputs_sha256', 'split', 'source_sha', 'cases'])
    keys(replay, ['schema', 'inputs_sha256', 'provenance', 'decisions'])
    digest = hashlib.sha256(input_bytes).hexdigest()
    if (inputs['schema'] != 'prose_routing_inputs_v1' or manifest['schema'] != 'prose_routing_answers_v1'
            or replay['schema'] != 'prose_routing_replay_v1' or inputs['split'] not in {'dev', 'holdout'}
            or inputs['split'] != manifest['split'] or digest != manifest['inputs_sha256']
            or digest != replay['inputs_sha256'] or replay['provenance'] not in {'scripted', 'external_unverified'}):
        raise ValueError('Mismatched frozen input or unsupported replay')
    cases, answers, decisions = {}, {}, {}
    for case in inputs['cases']:
        keys(case, ['id', 'request', 'choices'])
        if case['id'] in cases: raise ValueError('Duplicate input case')
        aliases = [choice['alias'] for choice in case['choices']]
        if len(set(aliases)) != len(aliases): raise ValueError('Duplicate offered alias')
        cases[case['id']] = case
    for answer in manifest['cases']:
        keys(answer, ['id', 'fixture_id', 'disposition', 'target_available', 'acceptable_aliases', 'snapshot_sha256', 'host_bindings'])
        identity = answer['id']
        if identity in answers or identity not in cases: raise ValueError('Unexpected answer case')
        offered = {choice['alias'] for choice in cases[identity]['choices']}
        if (answer['disposition'] not in {'target', 'clarify', 'discuss'}
                or type(answer['target_available']) is not bool
                or set(answer['host_bindings']) != offered
                or not set(answer['acceptable_aliases']) <= offered
                or answer['target_available'] != bool(answer['acceptable_aliases'])
                or answer['disposition'] != 'target' and answer['acceptable_aliases']):
            raise ValueError('Invalid evaluator answers')
        answers[identity] = answer
    if set(answers) != set(cases): raise ValueError('Missing evaluator answer')
    for row in replay['decisions']:
        keys(row, ['id', 'decision'])
        if row['id'] in decisions or row['id'] not in cases: raise ValueError('Duplicate or unknown decision case')
        decision = row['decision']
        if (not isinstance(decision, dict) or len(decision) != 1 or
                not (set(decision) == {'alias'} and isinstance(decision['alias'], str)
                     or set(decision) == {'clarify'} and decision['clarify'] is True
                     or set(decision) == {'discuss'} and decision['discuss'] is True)):
            raise ValueError('Exactly one alias, clarify, or discuss decision is required')
        decisions[row['id']] = decision
    counts = {name: 0 for name in ['correct_target', 'wrong_target_nomination', 'invalid_alias',
        'correct_clarification', 'unnecessary_clarification', 'missed_clarification',
        'correct_intentional_non_edit', 'missed_intentional_non_edit', 'capability_miss',
        'valid_miss', 'missing', 'offered_alias_accepted', 'offered_alias_rejected']}
    rows = []
    for identity, answer in answers.items():
        decision = decisions.get(identity)
        if answer['disposition'] == 'target' and not answer['target_available']: counts['capability_miss'] += 1
        if decision is None:
            counts['missing'] += 1; rows.append({'id': identity, 'outcome': 'unscored'}); continue
        if 'alias' in decision:
            if decision['alias'] not in answer['host_bindings']:
                outcome = 'invalid_alias'; counts['offered_alias_rejected'] += 1
            else:
                counts['offered_alias_accepted'] += 1
                outcome = 'correct_target' if decision['alias'] in answer['acceptable_aliases'] else 'wrong_target_nomination'
            if answer['disposition'] == 'clarify': counts['missed_clarification'] += 1
            if answer['disposition'] == 'discuss': counts['missed_intentional_non_edit'] += 1
        elif 'clarify' in decision:
            outcome = ('correct_clarification' if answer['disposition'] == 'clarify' else
                       'valid_miss' if answer['disposition'] == 'target' and not answer['target_available'] else 'unnecessary_clarification')
            if answer['disposition'] == 'discuss': counts['missed_intentional_non_edit'] += 1
        else:
            outcome = 'correct_intentional_non_edit' if answer['disposition'] == 'discuss' else 'valid_miss'
            if answer['disposition'] == 'clarify': counts['missed_clarification'] += 1
        counts[outcome] += 1; rows.append({'id': identity, 'outcome': outcome})
    hardest = counts['wrong_target_nomination'] + counts['invalid_alias']
    return {'schema': 'prose_routing_score_v1', 'source_sha': manifest['source_sha'], 'inputs_sha256': digest,
            'split': inputs['split'], 'provenance': replay['provenance'], 'counts': counts, 'cases': rows,
            'coverage': {'total': len(cases), 'supplied': len(decisions), 'missing': counts['missing']},
            'clarification': {'required': sum(a['disposition'] == 'clarify' for a in answers.values()),
                              'correct': counts['correct_clarification'], 'overuse': counts['unnecessary_clarification']},
            'intentional_non_edit': {'required': sum(a['disposition'] == 'discuss' for a in answers.values()),
                                    'correct': counts['correct_intentional_non_edit']},
            'hard_failure': bool(hardest), 'ordinary_routing_qualified': False,
            'runtime_admission': 'not exercised; only frozen offered-alias membership checked',
            'transactions': 'not run', 'save_reopen': 'not run'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['inputs', 'manifest', 'decisions', 'output']: parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Use a new output file; existing evidence is never overwritten')
    result = score(args.inputs.read_bytes(), decode_json(args.manifest.read_text()), decode_json(args.decisions.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    return 2 if result['hard_failure'] else 1 if result['coverage']['missing'] or any(result['counts'][key] for key in ['valid_miss', 'missed_clarification', 'missed_intentional_non_edit', 'unnecessary_clarification']) else 0

if __name__ == '__main__': raise SystemExit(main())
