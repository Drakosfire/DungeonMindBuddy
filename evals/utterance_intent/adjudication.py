"""Host-only operator gold adjudication; never invokes a provider or rewrites a run."""
from collections import defaultdict
from copy import deepcopy
from .proof import digest, score


def adjudicate(manifest, report, overrides):
    if digest(manifest)!=report['manifest_sha256']:
        raise ValueError('Frozen manifest differs from report')
    cases={c['id']:c for c in manifest['cases']}
    revised=deepcopy(cases)
    for change in overrides:
        case=revised[change['case_id']]
        if digest(case['question'])!=change['question_sha256']:
            raise ValueError('Operator adjudication question differs')
        if not change.get('authority'):raise ValueError('Operator authority required')
        case['gold']=deepcopy(change['gold'])
    groups=[]
    for family,variant in sorted({(r['family'],r['variant']) for r in report['rows']}):
        rows=[r for r in report['rows'] if r['family']==family and r['variant']==variant]
        complete=coarse=0;utterances=defaultdict(list)
        for row in rows:
            case=revised[row['case_id']]
            result=score(row['actual'],case['gold'])
            complete+=result['passed'];coarse+=result['intent_outcome_correct']
            utterances[case['question']].append(result['intent_outcome_correct'])
        groups.append({'family':family,'variant':variant,'runs':len(rows),'complete':complete,
                       'intent_outcome':coarse,'unique_utterances':len(utterances),
                       'utterance_macro_intent_outcome':sum(sum(v)/len(v) for v in utterances.values())/len(utterances)})
    return {'kind':'operator_adjudication_not_new_inference','original_manifest_sha256':digest(manifest),
            'original_report_sha256':digest(report),'overrides':deepcopy(overrides),'groups':groups,
            'limits':['Original scores and raw calls remain unchanged.',
                      'Post-inference operator gold clarification; not a fresh holdout result.',
                      'Repeated input weighting and unique-utterance macro scores both reported.']}
