"""Question-only output for the versioned contextual Plan conversation task."""
from .plan_contextual_targets import current_resolution, clarification_question

FORMAT = 'plan_contextual_question_v1'


def output_format(execution):
    selected = current_resolution(execution)
    if selected is None or selected.requested_work != 'clarify':
        return None
    expected = clarification_question(selected)
    question = {'type': 'string', 'minLength': 1, 'maxLength': 4096,
        'description': 'The single focused question to ask the user. Do not answer, draft, or merely quote evidence.'}
    if expected is not None:
        question['enum'] = [expected]
    return dict(type='json_schema', name=FORMAT, strict=True, schema={
        'type': 'object', 'properties': {'question': question}, 'required': ['question'],
        'additionalProperties': False})


def decode_question(candidate, execution):
    selected = current_resolution(execution)
    if selected is None or selected.requested_work != 'clarify':
        raise ValueError('Question output requires its contextual clarification decision')
    if not isinstance(candidate, dict) or set(candidate) != {'question'}:
        raise ValueError('Contextual clarification requires its question-only output')
    text = candidate['question']
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise ValueError('Contextual clarification requires a nonempty question')
    expected = clarification_question(selected)
    if expected is not None and text != expected:
        raise ValueError('Target question differs from the retained compatible-location set')
    return text


def response_task(execution):
    selected = current_resolution(execution)
    if selected is None or selected.requested_work != 'clarify':
        return None
    if clarification_question(selected) is not None:
        return 'contextual_target_question'
    return 'contextual_content_question'
