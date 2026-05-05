from __future__ import annotations

import pytest

from evals.sentence_routing_retrieval_falsification.breadcrumb_prompt import (
    PROMPT_VARIANT_CONTINUATION,
    PROMPT_VARIANT_CONTROL,
    PROMPT_VARIANT_PRONOUN_RESOLUTION,
    build_breadcrumb_prompt,
    extract_breadcrumb_markdown,
)


def test_control_prompt_has_no_continuation_addendum() -> None:
    prompt = build_breadcrumb_prompt(
        variant=PROMPT_VARIANT_CONTROL,
        recap_body="Caelynn looks at the drawing.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
    )
    assert "UNDER-TAGGED CONTINUATION CHECK" not in prompt.system_text
    assert prompt.variant == PROMPT_VARIANT_CONTROL
    assert "schema: dmb_recap_breadcrumbs_v1" in prompt.user_text


def test_variant_prompt_includes_addendum_and_sentinel_example() -> None:
    prompt = build_breadcrumb_prompt(
        variant=PROMPT_VARIANT_CONTINUATION,
        recap_body="Caelynn looks at the drawing.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
    )
    assert "UNDER-TAGGED CONTINUATION CHECK" in prompt.system_text
    assert "captain_lysandra_ironveil" in prompt.system_text
    assert "Voices Tower" in prompt.system_text
    assert "MUST NOT spread named-subject tags onto unrelated sentences" in prompt.system_text
    assert "BACKWARD-ANAPHORA CHECK" in prompt.system_text
    assert "mumbling from inside" in prompt.system_text


def test_pronoun_resolution_variant_includes_pronoun_audit_contract() -> None:
    prompt = build_breadcrumb_prompt(
        variant=PROMPT_VARIANT_PRONOUN_RESOLUTION,
        recap_body="She tells Caelynn about the forest.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
    )
    assert "PRONOUN-RESOLVED BREADCRUMBS" in prompt.system_text
    assert "She tells Caelynn" in prompt.system_text
    assert "Require an unambiguous antecedent" in prompt.system_text
    assert prompt.variant == PROMPT_VARIANT_PRONOUN_RESOLUTION


def test_unknown_variant_raises() -> None:
    with pytest.raises(ValueError):
        build_breadcrumb_prompt(
            variant="nope",
            recap_body="x",
            frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
        )


def test_extract_breadcrumb_markdown_pulls_fenced_block() -> None:
    reply = (
        "Sure, here is the artifact:\n\n"
        "```breadcrumb\n"
        "---\nschema: dmb_recap_breadcrumbs_v1\n---\n"
        "# Recap\nLine.\n"
        "```\n"
    )
    extracted = extract_breadcrumb_markdown(reply)
    assert extracted.startswith("---")
    assert "schema: dmb_recap_breadcrumbs_v1" in extracted
    assert "# Recap" in extracted


def test_extract_breadcrumb_markdown_falls_back_to_raw_text() -> None:
    raw = "---\nschema: dmb_recap_breadcrumbs_v1\n---\n# Recap\n"
    out = extract_breadcrumb_markdown(raw)
    assert "schema: dmb_recap_breadcrumbs_v1" in out
