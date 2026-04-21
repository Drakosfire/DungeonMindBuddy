"""Round-4 anti-regression: recap-write tool order in planner instructions.

The recap-write flow must not silently swap ``assemble_recap_draft`` (mandatory body
assembly) with ``build_recap_write_payload`` (optional structured payload helper).
See backlog P2 / ``_WRITE_TOOLS_ADDENDUM`` in ``corpus_session_planner.py``.
"""

from __future__ import annotations

import pytest

from src.prompts.corpus_session_planner import build_corpus_session_planner_instructions

# Exact anchors from **Session-recap creation flow:** numbered steps 3 and 5.
# If wording changes intentionally, update these strings in the same commit as the prompt.
_STEP3_MANDATORY_ASSEMBLE = "3. **Mandatory — call `assemble_recap_draft`**"
_STEP5_OPTIONAL_BUILD = (
    "5. **Optional helper after steps 3 + 4** — call **`build_recap_write_payload`**"
)


def _instructions_writes_on() -> str:
    return build_corpus_session_planner_instructions("", include_write_tools=True)


def _instructions_writes_off() -> str:
    return build_corpus_session_planner_instructions("", include_write_tools=False)


def test_planner_instructions_recap_write_mandatory_assemble_before_optional_payload() -> None:
    """``assemble_recap_draft`` (step 3) must precede ``build_recap_write_payload`` (step 5)."""
    text = _instructions_writes_on()
    assert _STEP3_MANDATORY_ASSEMBLE in text, (
        "Planner instructions must keep step 3: mandatory assemble_recap_draft "
        "(recap markdown body before preview/commit)."
    )
    assert _STEP5_OPTIONAL_BUILD in text, (
        "Planner instructions must keep step 5: optional build_recap_write_payload "
        "after steps 3–4."
    )
    a = text.index(_STEP3_MANDATORY_ASSEMBLE)
    b = text.index(_STEP5_OPTIONAL_BUILD)
    assert a < b, (
        "Round-4 regression risk: narrative order must be assemble_recap_draft (step 3) "
        f"before build_recap_write_payload (step 5); got indices {a} vs {b}."
    )


def test_planner_instructions_writes_off_omits_numbered_recap_flow() -> None:
    """Write-tools addendum (including numbered recap flow) is absent when writes are off."""
    text = _instructions_writes_off()
    assert _STEP3_MANDATORY_ASSEMBLE not in text
    assert _STEP5_OPTIONAL_BUILD not in text


@pytest.mark.parametrize("include_writes", [True, False])
def test_planner_instructions_buildable(include_writes: bool) -> None:
    """Smoke: instruction builder must not raise for minimal manifest."""
    s = build_corpus_session_planner_instructions("", include_write_tools=include_writes)
    assert len(s) > 1000
    assert "Corpus tree" in s
