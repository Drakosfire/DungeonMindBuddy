"""Tests for alias extraction and derived stopwords (Packet B)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.token_resolution.derive_stopwords import (
    collect_routes_from_breadcrumb_records,
    derive_route_stopwords,
)
from src.token_resolution.extract_hub_aliases import (
    extract_campaign_id,
    extract_hub_aliases_from_frontmatter,
    extract_hub_aliases_from_paths,
)


SAMPLE_FRONTMATTER = """\
schema: dmb_recap_breadcrumbs_v1
campaign:
  campaign_id: longmont-c1
session:
  number: 1
entity_index:
  parties:
    party_merchant_guards:
      slug: party_merchant_guards
      display_name: "Merchant-guard fellowship"
      proposed_route: "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/"
      aliases_in_recap:
        - "the group"
        - "the team"
  pcs:
    - slug: karsemine
      route: "Longmont Campaign/Campaign 1/PCs/karsemine/"
    - slug: stafl
      route: "Longmont Campaign/Campaign 1/PCs/stafl/"
  npcs: []
  locations:
    - slug: stonebridge
      proposed_route: "Longmont Campaign/Campaign 1/Locations/stonebridge/"
      rationale: "Starting town."
    - slug: rivers_edge_pub
      proposed_route: "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/"
      rationale: "Grishna's tavern."
  new_hub_candidates:
    - slug: magma_spider
      subject_type: npc
      proposed_route: "Longmont Campaign/Campaign 1/NPCs/magma_spider/"
      rationale: "Resident of the shatter mages tower."
"""


def test_extract_hub_aliases_from_frontmatter_collects_party() -> None:
    extraction = extract_hub_aliases_from_frontmatter(
        SAMPLE_FRONTMATTER, source_path="recap.md"
    )
    party = next(a for a in extraction.aliases if a.subject_class == "Party")
    assert party.slug == "party_merchant_guards"
    aliases = party.normalized_aliases()
    assert "the group" in aliases
    assert "the team" in aliases
    assert "merchant-guard fellowship" in aliases
    assert party.source_ref == "recap.md"


def test_extract_hub_aliases_includes_pcs_and_locations() -> None:
    extraction = extract_hub_aliases_from_frontmatter(SAMPLE_FRONTMATTER)
    slugs = sorted({a.slug for a in extraction.aliases})
    assert "karsemine" in slugs
    assert "stonebridge" in slugs
    assert "rivers_edge_pub" in slugs
    rivers = next(a for a in extraction.aliases if a.slug == "rivers_edge_pub")
    aliases = rivers.normalized_aliases()
    assert "rivers" in aliases
    assert "edge" in aliases
    assert "rivers edge pub" in aliases


def test_extract_hub_aliases_handles_new_hub_candidates() -> None:
    extraction = extract_hub_aliases_from_frontmatter(SAMPLE_FRONTMATTER)
    spider = next(a for a in extraction.aliases if a.slug == "magma_spider")
    assert spider.subject_class.lower() == "npc"
    aliases = spider.normalized_aliases()
    assert "magma" in aliases
    assert "spider" in aliases


def test_protected_tokens_cover_named_entity_slugs() -> None:
    extraction = extract_hub_aliases_from_frontmatter(SAMPLE_FRONTMATTER)
    protected = set(extraction.protected_tokens)
    assert {"karsemine", "stafl", "magma", "spider", "stonebridge"}.issubset(protected)
    # Generic structural words must NOT be protected by the extractor; that's
    # the lexicon-defaults layer's job.
    assert "longmont" not in protected
    assert "elderwyld" not in protected


def test_extract_hub_aliases_from_paths_combines_files(tmp_path: Path) -> None:
    a = tmp_path / "a.breadcrumbed.md"
    b = tmp_path / "b.breadcrumbed.md"
    a.write_text(f"---\n{SAMPLE_FRONTMATTER}---\n\nbody\n", encoding="utf-8")
    second = SAMPLE_FRONTMATTER.replace("karsemine", "ephanna")
    b.write_text(f"---\n{second}---\n\nbody\n", encoding="utf-8")
    extraction = extract_hub_aliases_from_paths([a, b])
    slugs = sorted({a.slug for a in extraction.aliases})
    assert "karsemine" in slugs
    assert "ephanna" in slugs
    assert str(a) in extraction.source_paths
    assert str(b) in extraction.source_paths


def test_extract_campaign_id_from_paths(tmp_path: Path) -> None:
    p = tmp_path / "x.breadcrumbed.md"
    p.write_text(f"---\n{SAMPLE_FRONTMATTER}---\n\nbody\n", encoding="utf-8")
    assert extract_campaign_id([p]) == "longmont-c1"


def test_derive_route_stopwords_flags_recurring_setting_token() -> None:
    routes = [
        "Longmont Campaign/Campaign 1/PCs/karsemine/",
        "Longmont Campaign/Campaign 1/PCs/stafl/",
        "Longmont Campaign/Campaign 1/NPCs/grishna/",
        "Longmont Campaign/Campaign 1/Locations/stonebridge/",
        "Longmont Campaign/Campaign 1/Locations/rivers_edge_pub/",
        "Longmont Campaign/Campaign 1/Parties/party_merchant_guards/",
    ]
    protected = ["karsemine", "stafl", "grishna", "stonebridge", "rivers", "edge", "pub", "party", "merchant", "guards"]
    derived = derive_route_stopwords(routes, protected_tokens=protected)
    assert "longmont" in derived
    # Generic structural words like "campaign", "session" come from defaults,
    # so they must not be re-derived here (would double-count).
    assert "campaign" not in derived
    assert "pcs" not in derived


def test_derive_route_stopwords_respects_protected_tokens() -> None:
    routes = ["foo/lysandra"] * 6
    derived = derive_route_stopwords(routes, protected_tokens=["lysandra"])
    assert "lysandra" not in derived


def test_derive_route_stopwords_returns_empty_for_tiny_corpora() -> None:
    routes = ["a/b", "a/c"]
    derived = derive_route_stopwords(routes, protected_tokens=[])
    assert derived == []


def test_derive_route_stopwords_is_deterministic() -> None:
    routes_a = [
        "Elderwyld/Locations/branchbound/",
        "Elderwyld/NPCs/foo/",
        "Elderwyld/NPCs/bar/",
        "Elderwyld/PCs/baz/",
        "Elderwyld/Parties/qux/",
    ]
    routes_b = list(reversed(routes_a))
    assert derive_route_stopwords(routes_a, protected_tokens=["foo", "bar", "baz", "qux", "branchbound"]) == derive_route_stopwords(
        routes_b, protected_tokens=["foo", "bar", "baz", "qux", "branchbound"]
    )


def test_collect_routes_from_records_pulls_normalized_route_and_dedupes() -> None:
    records = [
        {"routes": [{"normalized_route": "A/B"}, {"normalized_route": "C"}]},
        {"routes": [{"normalized_route": "A/B"}]},
        {"routes": []},
        {},
    ]
    routes = collect_routes_from_breadcrumb_records(records)
    assert routes == ["A/B", "C"]
