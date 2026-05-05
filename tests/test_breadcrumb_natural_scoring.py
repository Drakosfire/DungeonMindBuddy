from __future__ import annotations

from evals.sentence_routing_retrieval_falsification.breadcrumb_natural_scoring import build_hit_context_text


def test_build_hit_context_text_includes_routes_by_default() -> None:
    by_unit = {
        "u1": {
            "lexical_plain": "Karsemine looks up.",
            "routes": [{"normalized_route": "Longmont Campaign/Campaign 1/PCs/karsemine/"}],
        }
    }
    hits = [{"unit_id": "u1"}]
    out = build_hit_context_text(hits, by_unit)
    assert "Karsemine looks up." in out
    assert "Longmont Campaign/Campaign 1/PCs/karsemine/" in out


def test_build_hit_context_text_can_exclude_route_lines() -> None:
    by_unit = {
        "u1": {
            "lexical_plain": "Karsemine looks up.",
            "routes": [{"normalized_route": "Longmont Campaign/Campaign 1/PCs/karsemine/"}],
        }
    }
    hits = [{"unit_id": "u1"}]
    out = build_hit_context_text(hits, by_unit, include_normalized_route_lines=False)
    assert out.strip() == "Karsemine looks up."
    assert "Longmont Campaign" not in out


def test_build_hit_context_text_excludes_path_like_lexical_units_when_requested() -> None:
    by_unit = {
        "u1": {
            "lexical_plain": "Longmont Campaign/Campaign 1/PCs/karsemine/",
            "routes": [],
        },
        "u2": {
            "lexical_plain": "Some kind of flaming magma infused spider monstrosity.",
            "routes": [],
        },
    }
    hits = [{"unit_id": "u1", "score": 5}, {"unit_id": "u2", "score": 1}]
    out = build_hit_context_text(
        hits,
        by_unit,
        include_normalized_route_lines=False,
        exclude_path_like_lexical_units=True,
    )
    assert "Longmont Campaign/Campaign 1/PCs/karsemine/" not in out
    assert "flaming magma infused spider monstrosity" in out


def test_build_hit_context_text_orders_by_lexical_signal_and_applies_caps() -> None:
    by_unit = {
        "u1": {"lexical_plain": "While doing some drinking at the pub.", "routes": []},
        "u2": {
            "lexical_plain": "Karsemine looked up and saw a flaming magma spider monstrosity.",
            "routes": [],
        },
        "u3": {"lexical_plain": "Another low-value expanded line.", "routes": []},
    }
    hits = [
        {"unit_id": "u1", "score": 4, "why_matched": ["lexical_token:while"]},
        {"unit_id": "u2", "score": 1, "why_matched": ["lexical_token:karsemine", "lexical_token:room"]},
        {"unit_id": "u3", "score": 0, "why_matched": ["expanded_adjacent:u3"]},
    ]
    out = build_hit_context_text(
        hits,
        by_unit,
        include_normalized_route_lines=False,
        query_tokens=["karsemine", "discover", "while", "searching", "room"],
        max_lexical_units=2,
        max_chars=200,
    )
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0].startswith("Karsemine looked up")
    assert all("Another low-value expanded line." not in line for line in lines)


def test_build_hit_context_text_can_emit_in_source_order() -> None:
    by_unit = {
        "u1": {"lexical_plain": "Late line.", "routes": [], "line_start": 20, "line_end": 20},
        "u2": {"lexical_plain": "Early line.", "routes": [], "line_start": 3, "line_end": 3},
    }
    hits = [
        {"unit_id": "u1", "score": 5, "why_matched": ["lexical_token:late"]},
        {"unit_id": "u2", "score": 1, "why_matched": ["lexical_token:early"]},
    ]
    out = build_hit_context_text(
        hits,
        by_unit,
        include_normalized_route_lines=False,
        order_mode="source_order",
    )
    assert out.splitlines() == ["Early line.", "Late line."]


def test_build_hit_context_text_source_order_breaks_shared_line_by_unit_suffix() -> None:
    """Three units sharing line_start must emit in recap sentence order.

    Mirrors the c1s1_karsemine_spider_reveal recap line where
    ``Finally, free to explore... -> As Karsemine searched... -> Some kind of
    flaming magma...`` all live on the same line. Retrieval rank ordered them
    [02, 01, 03] by score; we must restore the ``[01, 02, 03]`` source order
    so the magma-spider fragment sits adjacent to its referent sentence.
    """
    by_unit = {
        "u-L0017-01": {
            "lexical_plain": "Finally, free to explore.",
            "routes": [],
            "line_start": 17,
            "line_end": 17,
        },
        "u-L0017-02": {
            "lexical_plain": "As Karsemine searched the room.",
            "routes": [],
            "line_start": 17,
            "line_end": 17,
        },
        "u-L0017-03": {
            "lexical_plain": "Some kind of flaming magma infused spider monstrosity.",
            "routes": [],
            "line_start": 17,
            "line_end": 17,
        },
    }
    hits = [
        {
            "unit_id": "u-L0017-02",
            "score": 5,
            "why_matched": ["lexical_token:karsemine", "lexical_token:room"],
        },
        {
            "unit_id": "u-L0017-01",
            "score": 4,
            "why_matched": ["lexical_token:explore"],
        },
        {
            "unit_id": "u-L0017-03",
            "score": 0,
            "why_matched": ["expanded_adjacent:u-L0017-03"],
        },
    ]
    out = build_hit_context_text(
        hits,
        by_unit,
        include_normalized_route_lines=False,
        order_mode="source_order",
    )
    assert out.splitlines() == [
        "Finally, free to explore.",
        "As Karsemine searched the room.",
        "Some kind of flaming magma infused spider monstrosity.",
    ]
