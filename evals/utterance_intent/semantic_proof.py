"""Private #1769 route/resolution/writer proof. Never dispatches product operations."""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace
from uuid import UUID

from . import semantic_contract as contract
from .proof import canonical, digest, sdk_request, selection

DRAFT_ID = '10000000-0000-4000-8000-000000000001'
PAGE_ID = '10000000-0000-4000-8000-000000000002'
READ_ID = '10000000-0000-4000-8000-000000000003'
DRAFT = '''# Millford Forge
Ari owns and operates the forge. Jo worked here for one summer and now owns a nearby rope shop.
The town grows silver reeds. These are setting notes, not played events.
'''
RELATED = '''# Millford trades
| Person | Shop | Detail |
| --- | --- | --- |
| Jo | Jo's Ropes | Owns and operates the rope shop. Worked at Ari's forge for one summer. |
'''
# Freeze these expectations before inference; they never enter model input.
FRESH = (
 ('opener', 'I have a strange little experiment in mind. Ready to try it?', 'discuss'),
 ('names', 'Give me eight first-and-last names for people who harvest silver reeds.', 'write_current_page'),
 ('creative_insects', 'Propose magical insects and how their habits help cultivate the silver reeds.', 'write_current_page'),
 ('creative_economy', 'Invent other profitable livelihoods for this riverside settlement.', 'write_current_page'),
 ('discuss_first', 'Before writing anything, compare a prosperous Millford with one barely surviving. Help me choose.', 'discuss'),
 ('current_fact', 'Who owns and operates the forge, according to this page?', 'discuss'),
 ('questions', 'Ask whether I want to develop the landing or the market before you make anything.', 'clarify_request'),
 ('plan', 'Give me an editable plan for developing the forge, the rope shop and their owners. I will choose which steps to run.', 'plan'),
 ('encounter', 'Create a fight with three Gravel Hounds for four third-level characters.', 'build_encounter'),
 ('encounter_prose', 'Write a short paragraph for this page describing a possible meeting with three Gravel Hounds. Leave the outcome open.', 'write_current_page'),
 ('mechanics', 'Change the Gravel Hound hit points to 22 and save a separate mechanics version.', 'change_mechanics'),
 ('map_pin', "Place Jo's Ropes on our map at coordinates 0.6 and 0.4.", 'place_map_coordinates'),
 ('save', 'Save the current page now without generating new writing.', 'save_page'),
 ('publish', 'Publish the relationship between Ari and the forge into the World Graph.', 'publish_relationships'),
 ('other', 'Export this page as a printable PDF file.', 'other_creation'),
 ('missing_reference', 'Create the thing we were talking about in the other conversation, whose contents are not included here.', 'clarify_creation'),
 ('no_editor', 'Make a small supplies table for this page.', 'write_current_page'),
 ('revision', 'Rewrite the selected paragraph to feel welcoming. Preserve ownership, operation and past temporary work.', 'write_current_page'),
 ('connected', "Prepare a connected page review for Jo's Ropes, owned and operated by Jo. Use the saved trades chart.", 'review_connected_page'),
 ('relationship', 'Prepare a relationship review from the saved current page showing that Ari owns the forge. Do not publish it.', 'review_relationship'),
 ('image', 'Prepare an illustration of the forge beside tall silver reeds.', 'prepare_image'),
 ('question_holdout', 'Before you start describing the fair, give me two questions about its season and who attends.', 'clarify_request'),
 ('compare_holdout', "Let's compare an abandoned landing with a busy one, as possibilities. No page writing yet.", 'discuss'),
 ('pin_holdout', 'Mark the forge at x=0.15, y=0.85 on the existing map.', 'place_map_coordinates'),
 ('magic_holdout', 'Propose three tools with unmistakably supernatural properties for the forge, as a short table.', 'write_current_page'),
 ('plan_holdout', 'Offer a checklist for expanding the landing and its trades. I want to select what gets done before anything runs.', 'plan'),
 ('unsupported_holdout', 'Schedule a recurring reminder to check the silver reeds every morning.', 'other_creation'),
 ('fact_holdout', "What does this page actually say about Jo's work at the forge?", 'discuss'),
)


def capabilities(case):
    if case['cohort'] != 'synthetic':
        ops = tuple(case['control']['state']['decision']['state']['interaction']['allowed_operations'])
        return contract.Capabilities(ops)  # Historical review flags were not captured.
    return contract.Capabilities(('answer_from_sources',) if case['id'] == 'no_editor' else contract.OPERATIONS,
                                 contract.REVIEWS, case['id'] != 'no_editor', case['id'] != 'no_editor')


def synthetic_control(question):
    # Clean constructed context, not a claim that this is a runtime-captured envelope.
    return {'model': 'jev-1.14.0', 'questions': {'operation': {
        'type': 'choice', 'instructions': 'Choose an offered operation.',
        'criteria': {op: None for op in (*contract.OPERATIONS, 'cannot_select')}}},
        'state': {'decision': {'state': {'user_question': question, 'rules': '',
            'interaction': {'allowed_operations': list(contract.OPERATIONS), 'history': [],
                            'working_draft': {'draft_markdown': DRAFT}}},
            'questions': [{'name': 'operation', 'kind': 'choice', 'question': 'Choose an operation.',
                           'options': [*contract.OPERATIONS, 'cannot_select']}]}}}


def load_cases(frozen_path, adjudication_path):
    frozen = json.loads(frozen_path.read_text())
    adjudication = json.loads(adjudication_path.read_text())
    if adjudication['frozen_file_sha256'] != sha256(frozen_path.read_bytes()).hexdigest():
        raise ValueError('Operator adjudication belongs to another frozen proof')
    overrides = {row['case_id']: row for row in adjudication['overrides']}
    result = []
    branches = {'answer': 'discuss', 'brainstorm': 'discuss', 'retrieve': 'discuss', 'rules': 'discuss',
                'writing': 'write_current_page', 'placement': 'write_current_page', 'image': 'prepare_image',
                'mechanics': 'change_mechanics', 'encounter': 'build_encounter', 'clarify': 'clarify_request'}
    for original in frozen['cases']:
        case = deepcopy(original)
        expected = case['expected']
        requested = {branches[b] for b in (case.get('gold') or {}).get('branches', [])}
        if case['id'] in overrides:
            override = overrides[case['id']]
            if digest(case['question']) != override['question_sha256']:
                raise ValueError('Adjudicated question differs')
            expected = override['expected']
            requested = {'write_current_page'}
            case['prospective_expectation_authority'] = override['authority']
        elif case['id'] == 'observed-page-suggestion':
            requested = {'write_current_page'}
        case['semantic_expectation_basis'] = 'legacy_branch_projection'
        case.update(cohort='historical', legacy_expected_operation=case['original_expected'], expected_operation=expected,
                    expected_work=sorted(requested) or None)
        result.append(case)
    for name, question, expected in FRESH:
        cap = contract.Capabilities(('answer_from_sources',) if name == 'no_editor' else contract.OPERATIONS,
                                    contract.REVIEWS, name != 'no_editor', name != 'no_editor')
        control = synthetic_control(question)
        control['state']['decision']['state']['interaction']['allowed_operations'] = list(cap.operations)
        result.append({'id': name, 'cohort': 'synthetic', 'origin': 'constructed_synthetic_context',
                       'question': question, 'expected_work': [expected],
                       'expected_operation': contract.resolve(expected, cap)['operation'],
                       'semantic_expectation_basis': 'explicit_synthetic_gold_frozen_before_inference',
                       'synthetic_generation': 'new_v2_holdout' if name.endswith('_holdout') else 'retained_v1_fixture', 'control': control})
    if len({c['id'] for c in result}) != len(result) or any(not re.fullmatch(r'[a-zA-Z0-9_-]+', c['id']) for c in result):
        raise ValueError('Invalid or duplicate case file identity')
    return result


def discussion_packet(case):
    from application_state.agent_conversation.source_writer_output import GAP_POLICY, POLICY
    from application_state.agent_conversation import build_primary_context as primary
    packet = {'user_question': case['question'], 'opened_passages': [], 'exposure': {'saved_sections': []},
              'working_draft_context': {'record_id': DRAFT_ID, 'draft_markdown': DRAFT},
              'source_writer_output_policy': POLICY, 'requested_detail_gap_policy': GAP_POLICY,
              'collaboration_output_policy': 'typed_author_review_collaboration_v1',
              'connected_page_review_policy': 'typed_connected_page_review_v1',
              'relationship_review_policy': 'typed_saved_relationship_review_v1'}
    if case['id'] == 'connected':
        packet['related_authored_pages'] = {'pages': [{'read_id': READ_ID, 'markdown': RELATED,
            'page': {'world_id': 'synthetic-semantic-proof', 'document_id': PAGE_ID, 'registry_revision': 1,
                     'title': 'Millford trades', 'visibility': 'internal', 'content_sha256': sha256(RELATED.encode()).hexdigest()}}]}
    if case['id'] == 'relationship':
        packet['schema'] = primary.SCHEMA
        packet['artifact_under_edit'] = {'policy': primary.POLICY, 'role': primary.ROLE,
            'sections': [{'read_id': READ_ID, 'line_start': 1, 'line_end': 3, 'text': DRAFT}]}
    return packet


def writing_request(case, resolution):
    from generationengine import TextRequest
    from apps.live_control_server.services import build_document_proposal as owner
    from apps.live_control_server.models.build_document_proposal import BuildDocumentProposalRequest
    basis = {'world_id': 'synthetic-semantic-proof', 'document_id': PAGE_ID, 'registry_revision': 1,
             'content_sha256': sha256(DRAFT.encode()).hexdigest(), 'draft_sha256': sha256(DRAFT.encode()).hexdigest(),
             'visibility': 'internal', 'caret': 2, 'draft_generation': 0, 'selection_generation': 0}
    if case['id'] == 'revision':
        passage = DRAFT.splitlines()[1]
        basis['selection'] = {'end': 2 + len(passage), 'text': passage}
    request = BuildDocumentProposalRequest(idempotency_key=UUID(DRAFT_ID), conversation_id=UUID(READ_ID),
        expected_pointer_revision=1, basis=basis, instruction=case['question'], draft_markdown=DRAFT)
    wire = owner._writer_request(request, SimpleNamespace(record=SimpleNamespace(title='Millford Forge')),
                                 owner._model(), frozen_history=[])
    packet = json.loads(wire['input'])
    packet['response_contract'] = resolution
    return TextRequest(provider='openai', model=wire['model'], user_prompt=canonical(packet),
        system_prompt=wire['instructions'] + '\nSatisfy the requested number, format, and distinctive properties in the brief; names and thematic labels alone do not satisfy a requested property.\n', temperature=None, max_output_tokens=4096, reasoning_effort='low',
        json_schema=wire['text']['format']['schema'], schema_name='build_document_proposal',
        max_conformance_retries=0, max_transport_retries=0)


def validate_cases(cases):
    from generationengine.types import DecisionRequest
    for case in cases:
        for variant in (('captured', 'semantic') if case['cohort'] == 'historical' else ('semantic',)):
            payload = case['control'] if variant == 'captured' else contract.candidate(case['control'])
            DecisionRequest.model_validate(sdk_request(payload))
        if case['cohort'] == 'synthetic':
            expected = contract.resolve(case['expected_work'][0], capabilities(case))
            if expected['operation'] == 'answer_from_sources':
                contract.writer_request(discussion_packet(case), expected)
            elif expected['operation'] == 'propose_build_insertion':
                writing_request(case, expected)


def private_write(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as target:
        target.write(json.dumps(value, indent=2))


def summarize(rows):
    groups = []
    for cohort, variant in sorted({(r['cohort'], r['variant']) for r in rows}):
        subset = [r for r in rows if (r['cohort'], r['variant']) == (cohort, variant)]
        observations = []
        unknown = 0
        for row in subset:
            for call in row['calls']:
                observation = (call.get('response') or {}).get('observation') or call.get('failure_observation')
                if not isinstance(observation, dict) or not all(isinstance(observation.get(k), int)
                    and not isinstance(observation.get(k), bool) for k in ('input_tokens', 'output_tokens')):
                    unknown += 1
                else:
                    observations.append(observation)
        groups.append({'cohort': cohort, 'variant': variant, 'runs': len(subset),
            'operation_scored': sum(r['expected_operation'] is not None for r in subset),
            'operation_correct': sum(r.get('operation_correct') is True for r in subset),
            'semantic_scored': sum(r['expected_work'] is not None for r in subset) if variant == 'semantic' else 0,
            'semantic_correct': sum(r.get('semantic_correct') is True for r in subset),
            'errors': sum(r['error'] is not None for r in subset),
            'writer_validated': sum(r.get('writer_validation') == 'accepted_output_only' for r in subset),
            'image_admission_failures': sum(r.get('image_admission') == 'refused' for r in subset),
            'correct_operation_with_admission': sum(r.get('operation_correct') is True
                and r.get('image_admission') != 'refused' and r.get('failure_stage') != 'routing' for r in subset),
            'writer_errors': sum(r.get('failure_stage') == 'writer' for r in subset),
            'legacy_correct': sum(r.get('legacy_correct') is True for r in subset),
            'provider_call_attempts': sum(len(r['calls']) for r in subset), 'calls_with_unknown_usage': unknown,
            'known_input_tokens': sum(o['input_tokens'] for o in observations),
            'known_output_tokens': sum(o['output_tokens'] for o in observations),
            'limits': 'Output/schema scores do not prove semantic usefulness, APP admission or staging.'})
    return groups


async def run(cases, output, frozen_path, adjudication_path):
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest
    from apps.live_control_server.services import build_document_proposal as proposal
    validate_cases(cases)
    output.mkdir(mode=0o700)  # Never overwrite/restart an existing experiment.
    manifest = {'policy': contract.POLICY, 'repeats': 2, 'cases': cases,
                'contract_source': Path(contract.__file__).read_text(),
                'evaluator_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
                'prior_manifest_sha256': sha256(frozen_path.read_bytes()).hexdigest(),
                'adjudication_sha256': sha256(adjudication_path.read_bytes()).hexdigest(),
                'limits': ['No runtime importer, APP admission, execution, database writes, page staging, Save or publication.',
                          'Historical captures/substitutions are retained known cases, not unseen accuracy.',
                          'Historical unknown review flags remain uncaptured, not falsely unavailable.',
                          'Only synthetic text goes to the OpenAI writer; captured payloads go only to the authorized TypeSafe/Vercel route.',
                          'Synthetic selected range is constructed, not proof of browser selection or actual replacement.',
                          'Image route is tested; image workflow/generation is not run here.',
                          'Historical expected_work is a mechanical legacy-branch projection, not new semantic gold. Preserve mismatches pending adjudication.',
                          'Semantic usefulness requires separate inspection; output validation alone is not acceptance.']}
    private_write(output / 'frozen.json', manifest)
    client = GenerationClient.from_env()
    semaphore = asyncio.Semaphore(4)
    rows = []

    async def one(case, variant, repeat):
        row = {k: case[k] for k in ('id', 'cohort', 'origin', 'expected_work', 'expected_operation', 'semantic_expectation_basis')}
        row.update(variant=variant, repeat=repeat, calls=[], error=None, failure_stage=None, image_admission='not_applicable',
                   semantic_usefulness='unreviewed')
        async def call(kind, request):
            entry = {'kind': kind, 'request': request.model_dump(mode='json'), 'response': None,
                     'failure_observation': None}
            row['calls'].append(entry)
            # Record each exact prepared input before dispatch. No resumption/replay semantics.
            private_write(output / f"{case['id']}-{variant}-{repeat}-{kind}-prepared.json", entry['request'])
            try:
                result = await (client.decide(request) if kind == 'routing' else client.generate_text(request))
                entry['response'] = result.model_dump(mode='json')
                return entry['response']
            except Exception as exc:
                obs = getattr(exc, 'observation', None)
                entry['failure_observation'] = obs.model_dump(mode='json') if hasattr(obs, 'model_dump') else None
                raise
        async with semaphore:
            try:
                row['failure_stage'] = 'routing'
                payload = case['control'] if variant == 'captured' else contract.candidate(case['control'])
                response = await call('routing', DecisionRequest.model_validate(sdk_request(payload)))
                if variant == 'captured':
                    operation = selection(response, 'operation')
                    row['legacy_correct'] = operation == case['legacy_expected_operation']
                    image_probability = response['answers']['operation']['probabilities'].get('prepare_build_image')
                else:
                    label = contract.selected(response)
                    resolution = contract.resolve(label, capabilities(case))
                    row.update(requested_work=label, resolution=resolution,
                               semantic_correct=None if case['expected_work'] is None else label in case['expected_work'])
                    operation = resolution['operation']
                    image_probability = response['answers']['requested_work']['probabilities']['prepare_image']
                row.update(operation=operation, operation_correct=None if case['expected_operation'] is None
                           else operation == case['expected_operation'])
                if operation == 'prepare_build_image':
                    row['image_admission'] = 'passed' if image_probability >= .9 else 'refused'
                    if row['image_admission'] == 'refused':
                        raise ValueError('Actual image selection failed existing .9 admission')
                if variant == 'semantic' and case['cohort'] == 'synthetic':
                    row['failure_stage'] = 'writer'
                    if operation == 'propose_build_insertion':
                        response = await call('writer', writing_request(case, resolution))
                        row['output'] = proposal._result(response['text']).model_dump(mode='json')
                    elif operation == 'answer_from_sources':
                        request, packet = contract.writer_request(discussion_packet(case), resolution)
                        response = await call('writer', request)
                        row['output'] = contract.validate_output(response['text'], packet, resolution)
                    else:
                        row['writer_validation'] = 'not_run_image_workflow'
                    if 'output' in row:
                        row['writer_validation'] = 'accepted_output_only'
                row['failure_stage'] = None
            except Exception as exc:
                row['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        private_write(output / f"{case['id']}-{variant}-{repeat}.json", row)
        rows.append(row)
    try:
        await asyncio.gather(*(one(c, v, r) for r in range(2) for c in cases
            for v in (('captured', 'semantic') if c['cohort'] == 'historical' else ('semantic',))))
    finally:
        await client.aclose()
        report = {'manifest_sha256': digest(manifest), 'completed_rows': len(rows), 'groups': summarize(rows)}
        private_write(output / 'report.json', report)
        print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-frozen', type=Path, required=True)
    parser.add_argument('--adjudication', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    cases = load_cases(args.historical_frozen, args.adjudication)
    if args.validate_only:
        validate_cases(cases)
        print(f'Validated {len(cases)} cases; no calls.')
    elif args.output is None:
        parser.error('--output required')
    else:
        asyncio.run(run(cases, args.output, args.historical_frozen, args.adjudication))


if __name__ == '__main__':
    main()
