"""Response instructions have explicit, inspectable component ownership."""
from dataclasses import FrozenInstanceError
from hashlib import sha256

import pytest

from application_state.agent_conversation.response_prompt import compose_response_prompt


def test_response_contract_has_no_inactive_capability_instructions():
    prompt = compose_response_prompt()
    text = prompt.instructions.lower()
    for inactive in ["retrieve", "call a tool", "image_prompt", "focused_edit_target", "save the page", "publish"]:
        assert inactive not in text
    assert [c.name for c in prompt.components] == ["voice", "evidence", "citations", "response_output"]
    assert "every" in text and "material clause" in text
    assert "native structured-output schema" in text
    assert "not a completed event" in text
    assert len(prompt.instructions) < 3000


def test_component_manifest_is_host_only_and_binds_actual_instructions():
    prompt = compose_response_prompt()
    manifest = prompt.manifest()
    assert manifest["instructions_sha256"] == sha256(prompt.instructions.encode()).hexdigest()
    assert all(c["version"] == "1" for c in manifest["components"])
    assert "\n\n".join(c["text"] for c in manifest["components"]) == prompt.instructions
    assert all(c["sha256"] == sha256(c["text"].encode()).hexdigest() for c in manifest["components"])
    assert "sha256" not in prompt.instructions and "buddy_response_v1" not in prompt.instructions
    with pytest.raises(FrozenInstanceError):
        prompt.components[0].text = "changed"


def test_rules_response_guidance_is_present_only_when_active():
    base = compose_response_prompt()
    active = compose_response_prompt(rules_instructions="Use only supplied Rules supports.")
    assert len(active.components) == len(base.components) + 1
    assert active.components[-1].name == "rules_response"
    assert active.instructions.startswith(base.instructions)
    with pytest.raises(ValueError):
        compose_response_prompt(rules_instructions=" ")


def test_related_page_guidance_is_an_explicit_separate_component():
    prompt = compose_response_prompt(rules_instructions="Supplied Rules.",
                                     related_page_instructions="Quote the supplied page.")
    assert [c.name for c in prompt.components][-2:] == ['rules_response', 'related_pages_response']
    assert prompt.instructions.endswith('Quote the supplied page.')
    assert 'Quote the supplied page.' not in compose_response_prompt().instructions
    with pytest.raises(ValueError):
        compose_response_prompt(related_page_instructions=' ')


@pytest.mark.parametrize('task', ['clarify', 'scoped_discussion', 'explain_capability', 'different_destination'])
def test_conversation_task_has_a_versioned_component_without_inactive_tools(task):
    prompt = compose_response_prompt(task=task)
    assert len(prompt.components) == 5
    assert len(prompt.instructions) < 3000
    assert 'image_prompt' not in prompt.instructions
    assert 'instructions_sha256' not in prompt.instructions
    if task == 'scoped_discussion':
        assert 'only assignment' in prompt.instructions and 'siblings are context' in prompt.instructions
    with pytest.raises(ValueError):
        compose_response_prompt(task='future_unknown_task')
