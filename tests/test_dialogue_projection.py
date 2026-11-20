from copy import deepcopy
from hashlib import sha256
import json

import pytest

from application_state.agent_conversation.dialogue_projection import expand_dialogue, project_dialogue


def row(identity, user="作者 asks 🌒 " * 30, assistant="A complete reply.\n" * 40):
    return {"turn_id": identity, "user": user, "assistant": assistant,
            "user_sha256": sha256(user.encode()).hexdigest(),
            "assistant_sha256": sha256(assistant.encode()).hexdigest()}


def test_nonadjacent_exact_pairs_keep_every_occurrence_and_metadata():
    original = [row("a"), row("b", assistant="Distinct answer"), row("c"),
                row("d", user="作者 asks 🌒 " * 30 + " ")]
    frozen = deepcopy(original)
    projected = project_dialogue(original)
    assert projected[2] == {k: v for k, v in original[2].items() if k not in {"user", "assistant"}} | {"same_text_as": 0}
    assert projected[1] == original[1] and projected[3] == original[3]
    assert expand_dialogue(projected) == original == frozen
    assert len(json.dumps(projected).encode()) < len(json.dumps(original).encode())
    assert project_dialogue(projected) == projected
    projected[0]["assistant"] = "tampered"
    assert original == frozen
    with pytest.raises(ValueError, match="digest"):
        expand_dialogue(projected)


def test_no_normalization_or_text_only_role_merging_and_no_costly_alias():
    pairs = [{"user": "x", "assistant": "y"}, {"user": "x", "assistant": "y"},
             {"user": "é", "assistant": "a"}, {"user": "e\u0301", "assistant": "a"},
             {"user": "a", "assistant": "é"}]
    assert project_dialogue(pairs) == pairs
    assert expand_dialogue([]) == []


@pytest.mark.parametrize("target", [-1, 1, True, 0.0, "0", None])
def test_invalid_reference_index_rejected(target):
    with pytest.raises(ValueError, match="earlier literal"):
        expand_dialogue([row("a"), {"same_text_as": target}])


@pytest.mark.parametrize("bad", [None, {}, [None], [{"user": "a"}],
    [row("a"), {"same_text_as": 0, "assistant": "injected"}],
    [row("a"), {"same_text_as": 0}, {"same_text_as": 1}],
    [row("a"), {"same_text_as": 0, "user_sha256": "wrong"}]])
def test_malformed_or_conflicting_alias_rejected(bad):
    with pytest.raises(ValueError):
        expand_dialogue(bad)
