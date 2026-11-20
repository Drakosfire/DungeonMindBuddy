"""A source word must not become another node's high-confidence partial pill."""

import pytest
from graph_memory.projection.markdown_mentions import (
    LocatedMentionBinding,
    MentionBinding,
    project_markdown_mentions,
)
from graph_memory.projection.world_projection import WorldGraphProjectionNodeView
from graph_memory.projection.world_recap_projection import (
    project_world_markdown_mentions,
)


@pytest.mark.parametrize("located", [False, True])
@pytest.mark.parametrize(
    "word", ["team", "teapot", "teas", "tea_kit", "tea2", "teaé", "stea", "étea"]
)
def test_free_tea_binding_does_not_split_other_words(word, located):
    prefix = "Ari " if located else ""
    source = prefix + f"The {word} goes north."
    explicit = (
        [
            LocatedMentionBinding(
                surface="Ari", node_id="pc:ari", start_offset=0, end_offset=3
            )
        ]
        if located
        else []
    )
    projected, mentions, _ = project_markdown_mentions(
        source,
        [MentionBinding(surface="tea", node_id="item:tea")],
        located_bindings=explicit,
    )
    assert not any(m.node_id == "item:tea" for m in mentions)
    if not located:
        assert projected == source
    else:
        assert f"The {word} goes north." in projected


@pytest.mark.parametrize("located", [False, True])
def test_standalone_tea_still_links_without_altering_surrounding_text(located):
    prefix = "Ari " if located else ""
    source = prefix + "The team shares TEA, then tea's aroma fades."
    explicit = (
        [
            LocatedMentionBinding(
                surface="Ari", node_id="pc:ari", start_offset=0, end_offset=3
            )
        ]
        if located
        else []
    )
    projected, mentions, _ = project_markdown_mentions(
        source,
        [MentionBinding(surface="tea", node_id="item:tea")],
        located_bindings=explicit,
    )
    tea = [m for m in mentions if m.node_id == "item:tea"]
    assert [m.label for m in tea] == ["TEA", "tea"]
    assert "The team shares" in projected
    for mention in tea:
        assert projected[mention.start_offset : mention.end_offset].startswith(
            f"[{mention.label}](dmb-node:"
        )


def test_ordinary_recap_adapter_does_not_link_tea_in_team():
    source = "The team goes upstairs. Later, the team heads north."
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="item:tea", label="tea", kind="item", role="item", aliases=[]
        )
    ]
    projected, mentions, diagnostics = project_world_markdown_mentions(source, nodes)
    assert projected == source
    assert mentions == []
    assert diagnostics == []


@pytest.mark.parametrize("located", [False, True])
def test_protected_markdown_and_escape_guards_remain_intact(located):
    prefix = "Ari " if located else ""
    source = (
        prefix
        + r"`tea` [tea](https://example.test) \tea tea\ [tea] tea]"
        + "\n\n```\ntea\n```"
    )
    explicit = (
        [
            LocatedMentionBinding(
                surface="Ari", node_id="pc:ari", start_offset=0, end_offset=3
            )
        ]
        if located
        else []
    )
    projected, mentions, _ = project_markdown_mentions(
        source,
        [MentionBinding(surface="tea", node_id="item:tea")],
        located_bindings=explicit,
    )
    assert not any(m.node_id == "item:tea" for m in mentions)
    if not located:
        assert projected == source


@pytest.mark.parametrize("located", [False, True])
def test_ambiguous_tea_does_not_warn_about_team(located):
    explicit = (
        [
            LocatedMentionBinding(
                surface="Ari", node_id="pc:ari", start_offset=0, end_offset=3
            )
        ]
        if located
        else []
    )
    source = ("Ari " if located else "") + "The team goes north."
    _, mentions, diagnostics = project_markdown_mentions(
        source,
        [
            MentionBinding(surface="tea", node_id="item:tea"),
            MentionBinding(surface="TEA", node_id="item:other"),
        ],
        located_bindings=explicit,
    )
    assert not any(m.node_id.startswith("item:") for m in mentions)
    assert diagnostics == []
