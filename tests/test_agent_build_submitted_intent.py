from hashlib import sha256
import pytest
from pydantic import ValidationError
from application_state.agent_conversation.types import SubmittedPrimaryWorkIntentV1
from apps.live_control_server.models.agent_turn import AgentTurnPrimaryWork


@pytest.mark.parametrize('model', [SubmittedPrimaryWorkIntentV1, AgentTurnPrimaryWork])
def test_build_pins_do_not_fabricate_plan_revision(model):
    payload = dict(kind='build', object_id='source', expected_revision=2, expected_content_sha256=sha256(b'source').hexdigest())
    assert model.model_validate(payload).model_dump()['expected_revision_n'] is None
    for invalid in [{**payload, 'expected_revision_n': 1}, {**payload, 'expected_content_sha256': None}]:
        with pytest.raises(ValidationError):
            model.model_validate(invalid)


@pytest.mark.parametrize('model', [SubmittedPrimaryWorkIntentV1, AgentTurnPrimaryWork])
@pytest.mark.parametrize('kind', ['plan', 'run', 'combat'])
def test_existing_pin_rules_remain(model, kind):
    bare = dict(kind=kind, object_id='work', expected_revision=1)
    assert model.model_validate(bare).kind == kind
    with pytest.raises(ValidationError):
        model.model_validate({**bare, 'expected_content_sha256': 'a' * 64})
    if kind == 'plan':
        assert model.model_validate({**bare, 'expected_content_sha256': 'a' * 64, 'expected_revision_n': 1})
