"""Plan Graph-need decision codec. This reader does not dispatch a provider."""
from __future__ import annotations

import json
import math
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import Field
from generationengine.types import ChoiceDecisionQuestion, DecisionRequest

from .jev_retrieval_contract import MODEL, PROVIDER, RetrievalDialogue, validated_choice_answers
from .native_statement_input import Strict
from .rules_authority_types import canonical_sha256
from .plan_authoring import strict_json

Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$', strict=True)]
OPTIONS = ('require_graph', 'no_graph', 'uncertain')
QUESTION = 'Does the current request require World Graph facts beyond the supplied conversation and current work?'
DESCRIPTIONS = {
    'require_graph': 'Graph facts are needed to satisfy the request',
    'no_graph': 'The supplied conversation and current work are sufficient without World Graph facts',
    'uncertain': 'It is unclear whether World Graph facts are needed',
}


class NativePlanGraphNeedInputV1(Strict):
    """Retained semantic inputs plus host-only pins for one exact Plan opening."""
    schema_: Literal['dmb_plan_graph_need_input_v1'] = Field(default='dmb_plan_graph_need_input_v1', alias='schema')
    pending_query_sha256: Digest
    admission_sha256: Digest
    question: str = Field(min_length=1, strict=True)
    dialogue: tuple[RetrievalDialogue, ...]
    current_work: str = Field(strict=True)

    @property
    def digest(self):
        return canonical_sha256(self.model_dump(mode='json', by_alias=True))


def validate_input_binding(parent, *, pending_sha256, admission_sha256, question, dialogue_sha256, work_sha256):
    """Join the frozen model inputs to their already-admitted host commitments."""
    from .native_plan_opening import opening_dialogue_sha256
    if (type(parent) is not NativePlanGraphNeedInputV1
            or parent.pending_query_sha256 != pending_sha256
            or parent.admission_sha256 != admission_sha256
            or parent.question != question
            or opening_dialogue_sha256(parent.dialogue) != dialogue_sha256
            or sha256(parent.current_work.encode('utf-8')).hexdigest() != work_sha256):
        raise ValueError('Plan Graph-need input differs from its committed request, dialogue or work')


def prepare_decision(parent):
    if type(parent) is not NativePlanGraphNeedInputV1:
        raise ValueError('Plan Graph-need decision requires its exact versioned input')
    return DecisionRequest(provider=PROVIDER, model=MODEL, state={
        'user_request': parent.question,
        'dialogue_reference': [row.model_dump() for row in parent.dialogue],
        'current_work': parent.current_work,
    }, questions=(ChoiceDecisionQuestion(name='graph_need', question=QUESTION,
        options=OPTIONS, option_descriptions=DESCRIPTIONS),), max_transport_retries=0)


def validate_wire(parent, raw, *, expected_model=MODEL):
    """Validate the actual prepared Jev semantics; envelope identity is checked by APP."""
    if type(raw) is not bytes:
        raise ValueError('Plan Graph-need wire must be bytes')
    decision = prepare_decision(parent)
    expected = {'state': decision.state, 'model': expected_model, 'questions': {
        q.name: {'type': 'choice', 'instructions': q.question,
                 'criteria': {option: (q.option_descriptions or {}).get(option) for option in q.options}}
        for q in decision.questions}}
    canonical = json.dumps(expected, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if strict_json(raw.decode('utf-8')) != expected or raw != canonical:
        raise ValueError('Plan Graph-need wire differs from its admitted semantic input')


def decode_decision(parent, result, *, expected_model=MODEL):
    prepare_decision(parent)
    choice = validated_choice_answers(result, {'graph_need'}, expected_model=expected_model)['graph_need']
    if choice not in OPTIONS:
        raise ValueError('Plan Graph-need decision selected an unknown option')
    distribution = result.answers['graph_need'].probabilities
    if distribution is not None:
        if (choice not in distribution or not set(distribution) <= set(OPTIONS)
                or any(not math.isfinite(value) or not 0 <= value <= 1 for value in distribution.values())):
            raise ValueError('Plan Graph-need probabilities are invalid')
        maximum = max(distribution.values())
        if distribution[choice] != maximum or sum(value == maximum for value in distribution.values()) != 1:
            raise ValueError('Plan Graph-need probability selection is tied or inconsistent')
    return choice


def decode_retained_result(parent, result_json, result_sha256, *, expected_model=MODEL):
    """Recheck a retained SDK result; its original authenticity needs the append owner."""
    from generationengine.types import DecisionResult
    if type(result_json) is not str or sha256(result_json.encode('utf-8')).hexdigest() != result_sha256:
        raise ValueError('Plan Graph-need result differs from its retained digest')
    strict_json(result_json)  # Refuse duplicate keys before Pydantic reconstruction.
    result = DecisionResult.model_validate_json(result_json)
    if result.model_dump_json() != result_json:
        raise ValueError('Plan Graph-need result differs from the exact SDK serialization')
    return decode_decision(parent, result, expected_model=expected_model)
