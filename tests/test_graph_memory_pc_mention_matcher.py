"""Deterministic PC mention matcher, IR guardrails, and projection chips."""

from __future__ import annotations

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    consolidate_category_outputs,
    render_category_pass_prompts,
)
from src.graph_memory.extraction.known_entity_mention_matcher import (
    filter_observation_nodes_dropping_known_entities,
    match_known_entities_in_spans,
    match_text_mentions,
    build_term_index,
    _ambiguous_normalized_terms,
    render_known_entity_ledger_markdown,
    validate_known_entity_ir_assertions,
)
from src.graph_memory.extraction.known_entity_mention_schema import (
    KnownEntityMention,
    KnownEntityMentionSidecar,
)
from src.graph_memory.extraction.known_entity_registry import (
    KnownEntity,
    KnownEntityRegistry,
    build_known_entity_registry,
    normalize_match_surface,
)
from graph_memory.projection.recap_projection import build_recap_graph_projection
from graph_memory.union_supergraph.model import UnionSupergraphNode, UnionSupergraphStore


def _entity(
    *,
    slug: str,
    display_name: str,
    aliases: tuple[str, ...] = (),
    kind: str = "pc",
) -> KnownEntity:
    terms: list[tuple[str, str]] = [(display_name, "canonical")]
    for alias in aliases:
        terms.append((alias, "alias"))
    return KnownEntity(
        slug=slug,
        kind=kind,
        display_name=display_name,
        canonical_entity_id=f"node:{slug.replace('_', '-')}",
        aliases=aliases,
        hub_rel_path=f"PCs/{slug}/README.md",
        hub_resolved=True,
        corpus_ref={"type": "character", "ref_id": slug, "resolution": "resolved"},
        match_terms=tuple(terms),
    )


def _registry(*entities: KnownEntity, campaign_id: str = "test-campaign") -> KnownEntityRegistry:
    return KnownEntityRegistry(
        campaign_id=campaign_id,
        session_key="1",
        roster_session_key="1",
        roster_carry_forward=False,
        registry_relpath="test/_party_registry.json",
        entities=entities,
    )


def test_exact_and_alias_mentions() -> None:
    registry = _registry(
        _entity(slug="caelynn", display_name="Caelynn", aliases=("Cae",)),
    )
    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "Caelynn and Cae meet Bonogo.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-1")
    surfaces = {(m.surface_text, m.match_method) for m in sidecar.mentions}
    assert ("Caelynn", "canonical") in surfaces
    assert ("Cae", "alias") in surfaces
    assert all(m.canonical_entity_id == "node:caelynn" for m in sidecar.mentions)


def test_case_and_punctuation_tolerant_match() -> None:
    registry = _registry(_entity(slug="baergrom", display_name="Baergrom"))
    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "Then baergrom! pressed onward.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-1")
    assert len(sidecar.mentions) == 1
    assert sidecar.mentions[0].surface_text.lower().startswith("baergrom")


def test_longest_match_wins_over_shorter_alias() -> None:
    registry = _registry(
        _entity(
            slug="captain_lysandra_ironveil",
            display_name="Captain Lysandra Ironveil",
            aliases=("Lysandra",),
        )
    )
    text = "Captain Lysandra Ironveil arrived."
    term_index = build_term_index(registry.entities)
    ambiguous = _ambiguous_normalized_terms(term_index)
    mentions, _ = match_text_mentions(
        text,
        source_span_ref_id="span:p1",
        term_index=term_index,
        ambiguous_norms=ambiguous,
    )
    assert len(mentions) == 1
    assert mentions[0].surface_text == "Captain Lysandra Ironveil"


def test_ambiguous_alias_fail_closed() -> None:
    registry = _registry(
        _entity(slug="alice_one", display_name="Alice One", aliases=("Alex",)),
        _entity(slug="alice_two", display_name="Alice Two", aliases=("Alex",)),
    )
    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "Alex waved at the gate.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-1")
    assert sidecar.mentions == ()
    assert "Alex" in sidecar.ambiguous_surfaces


def test_absent_session_mention_emits_no_chip_rows() -> None:
    registry = build_known_entity_registry("longmont-c2", 22)
    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "The fog rolled over empty streets with no party members named.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-22")
    assert sidecar.mentions == ()
    assert registry.entities  # roster present, but no occurrence


def test_filter_drops_duplicate_known_entity_nodes() -> None:
    kept, dropped = filter_observation_nodes_dropping_known_entities(
        [
            {"node_id": "node:caelynn", "label": "Caelynn"},
            {"node_id": "node:novel-npc", "label": "Novel NPC"},
        ],
        known_ids={"node:caelynn"},
        known_slugs={"caelynn"},
        known_labels_norm={normalize_match_surface("Caelynn")},
    )
    assert [n["node_id"] for n in kept] == ["node:novel-npc"]
    assert "node:caelynn" in dropped


def test_filter_keeps_pc_named_object_and_thread_nodes() -> None:
    """Substring containment must not treat PC-named objects as the PC."""
    kept, dropped = filter_observation_nodes_dropping_known_entities(
        [
            {"node_id": "node:caelynn", "label": "Caelynn"},
            {"node_id": "node:caelynn-s-whisper-bottle", "label": "Caelynn's Whisper Bottle"},
            {"node_id": "node:stafl-song", "label": "Stafl Song"},
            {"node_id": "pc:stafl", "label": "Stafl"},
        ],
        known_ids={"node:caelynn", "pc:stafl", "node:stafl"},
        known_slugs={"caelynn", "stafl"},
        known_labels_norm={
            normalize_match_surface("Caelynn"),
            normalize_match_surface("Stafl"),
        },
    )
    kept_ids = {n["node_id"] for n in kept}
    assert "node:caelynn-s-whisper-bottle" in kept_ids
    assert "node:stafl-song" in kept_ids
    assert "node:caelynn" in dropped
    assert "pc:stafl" in dropped


def test_title_prefixed_names_do_not_derive_captain_alias() -> None:
    registry = build_known_entity_registry("longmont-c2", 22)
    lysandra = registry.by_slug().get("captain_lysandra_ironveil")
    assert lysandra is not None
    surfaces = {normalize_match_surface(surface) for surface, _method in lysandra.match_terms}
    assert "captain" not in surfaces
    assert "the captain" not in surfaces
    assert "a captain" not in surfaces

    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "A captain of the city watch ordered the gate closed.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-22")
    assert sidecar.mentions == ()


def test_ir_rejects_known_node_asserts_accepts_evidenced_edges() -> None:
    report = validate_known_entity_ir_assertions(
        nodes=[
            {
                "node_id": "node:caelynn",
                "label": "Caelynn",
                "proposed_action": "create",
            },
            {
                "node_id": "node:caelynn",
                "label": "Caelynn",
                "proposed_action": "anchor",
                "context_anchor": True,
            },
        ],
        edges=[
            {
                "edge_id": "edge:1",
                "from_node_id": "node:caelynn",
                "to_node_id": "node:novel",
                "evidence_refs": [{"source_span_ref_id": "span:p1"}],
            },
            {
                "edge_id": "edge:2",
                "from_node_id": "node:caelynn",
                "to_node_id": "node:novel",
                "evidence_refs": [],
            },
        ],
        beats=[
            {
                "beat_id": "beat:1",
                "involved_node_ids": ["node:caelynn"],
                "evidence_refs": [{"source_span_ref_id": "span:p1"}],
            }
        ],
        known_ids={"node:caelynn"},
        known_slugs={"caelynn"},
        known_labels_norm={normalize_match_surface("Caelynn")},
    )
    assert "node:caelynn" in report["rejected_known_entity_node_assertions"]
    assert "edge:1" in report["accepted_known_entity_edges"]
    assert "edge:2" in report["rejected_known_entity_edges_missing_evidence"]
    assert "beat:1" in report["accepted_known_entity_beats"]
    assert report["ok"] is False


def test_consolidate_drops_duplicate_pc_nodes_keeps_novel() -> None:
    registry = build_known_entity_registry("longmont-c2", 22)
    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "Caelynn spoke with a stranger named Mireward Scout.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-22")
    parts = consolidate_category_outputs(
        {
            "actor_pass": {
                "observation_nodes": [
                    {
                        "node_id": "node:caelynn",
                        "label": "Caelynn",
                        "node_type": "character",
                        "description": "should be dropped",
                        "importance": "high",
                        "evidence_refs": [{"source_span_ref_id": "span:p1", "anchor_quotes": ["Caelynn"]}],
                    },
                    {
                        "node_id": "node:mireward-scout",
                        "label": "Mireward Scout",
                        "node_type": "character",
                        "description": "novel npc",
                        "importance": "medium",
                        "evidence_refs": [
                            {"source_span_ref_id": "span:p1", "anchor_quotes": ["Mireward Scout"]}
                        ],
                    },
                ]
            },
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {
                "observation_nodes": [],
                "ignored_items": [],
                "deferred_items": [],
            },
            "beat_pass": {"observation_beats": []},
            "edge_pass": {"observation_edges": []},
        },
        campaign_id="longmont-c2",
        session=22,
        known_entity_sidecar=sidecar,
        known_entity_registry=registry,
    )
    node_ids = {n["node_id"] for n in parts["nodes"]}
    assert "node:mireward-scout" in node_ids
    # Anchor may be present; a non-anchor create for Caelynn must not remain.
    caelynn_nodes = [n for n in parts["nodes"] if n.get("node_id") == "node:caelynn"]
    assert caelynn_nodes
    assert all(
        n.get("context_anchor") is True or n.get("proposed_action") == "anchor"
        for n in caelynn_nodes
    )
    diag = parts["consolidation_diagnostics"]["known_entity_mentions"]
    assert "node:caelynn" in diag["dropped_duplicate_node_ids"]
    assert diag["mention_count"] >= 1


def test_unsupported_known_entity_edge_removed_before_evidence_repair() -> None:
    """Empty-evidence Caelynn edges must not inherit mention citations and survive."""
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        repair_edge_evidence_refs,
        sanitize_parts,
    )

    registry = build_known_entity_registry("longmont-c2", 22)
    spans = [
        {
            "kind": "paragraph",
            "source_span_ref_id": "span:p1",
            "text": "Caelynn spoke with Mireward Scout.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-22")
    parts = consolidate_category_outputs(
        {
            "actor_pass": {
                "observation_nodes": [
                    {
                        "node_id": "node:mireward-scout",
                        "label": "Mireward Scout",
                        "node_type": "character",
                        "description": "novel npc",
                        "importance": "medium",
                        "evidence_refs": [
                            {"source_span_ref_id": "span:p1", "anchor_quotes": ["Mireward Scout"]}
                        ],
                    },
                ]
            },
            "location_pass": {"observation_nodes": []},
            "collective_pass": {"observation_nodes": []},
            "object_pass": {"observation_nodes": []},
            "thread_pass": {
                "observation_nodes": [],
                "ignored_items": [],
                "deferred_items": [],
            },
            "beat_pass": {"observation_beats": []},
            "edge_pass": {
                "observation_edges": [
                    {
                        "edge_id": "edge:caelynn-hallucinated",
                        "from_node_id": "node:caelynn",
                        "to_node_id": "node:mireward-scout",
                        "label": "commands",
                        "relationship_type": "commands",
                        "predicate_family": "authority",
                        "evidence_refs": [],
                    }
                ]
            },
        },
        campaign_id="longmont-c2",
        session=22,
        known_entity_sidecar=sidecar,
        known_entity_registry=registry,
    )
    edge_ids = {e.get("edge_id") for e in parts["edges"]}
    assert "edge:caelynn-hallucinated" not in edge_ids
    diag = parts["consolidation_diagnostics"]["known_entity_mentions"]
    assert "edge:caelynn-hallucinated" in diag["rejected_known_entity_edges_missing_evidence"]
    assert "edge:caelynn-hallucinated" in diag["removed_missing_evidence_edge_ids"]

    # Even if a caller reintroduces the edge, repair+sanitize must not resurrect it
    # from consolidate's removed set — prove consolidate already stripped it.
    repair_edge_evidence_refs(parts, {"span:p1"})
    sanitized, _ = sanitize_parts(parts, {"span:p1"})
    assert "edge:caelynn-hallucinated" not in {
        e.get("edge_id") for e in sanitized.get("edges") or []
    }


def test_prompt_wiring_includes_known_entity_ledger() -> None:
    from src.graph_memory.party_context import build_party_context_for_campaign

    registry = _registry(_entity(slug="caelynn", display_name="Caelynn"))
    sidecar = KnownEntityMentionSidecar(
        campaign_id="test-campaign",
        session_id="session-1",
        mentions=(
            KnownEntityMention(
                source_span_ref_id="span:p1",
                start_offset=0,
                end_offset=7,
                surface_text="Caelynn",
                canonical_entity_id="node:caelynn",
                entity_slug="caelynn",
                entity_kind="pc",
                match_method="canonical",
                display_name="Caelynn",
            ),
        ),
    )
    ledger = render_known_entity_ledger_markdown(sidecar, registry=registry)
    assert "do not recreate" in ledger.lower()
    assert "node:caelynn" in ledger

    party_ctx = build_party_context_for_campaign("longmont-c2", 22)
    prompts = render_category_pass_prompts(
        [
            {
                "kind": "paragraph",
                "source_span_ref_id": "span:p1",
                "source_unit_id": "span:p1",
                "text": "Caelynn walked into town.",
                "line_start": 1,
                "line_end": 1,
            }
        ],
        party_ctx=party_ctx,
        known_entity_sidecar=sidecar,
        known_entity_registry=registry,
    )
    joined = "\n".join(prompts.values())
    assert "node:caelynn" in joined
    assert "Known entity mentions" in joined


def _store_with_pc() -> UnionSupergraphStore:
    node = UnionSupergraphNode.model_validate(
        {
            "node_id": "node:caelynn",
            "label": "Caelynn",
            "kind": "character",
            "role": "character",
            "aliases": ["Caelynn"],
            "source_domains": ["recap"],
            "evidence_ref_ids": [],
            "state": {"memory_state": "graph_read_model"},
        }
    )
    return UnionSupergraphStore.model_validate(
        {
            "schema": "dmb_union_supergraph_store_v0",
            "version": "0.1",
            "campaign_id": "longmont-c2",
            "focus_session_id": "session-22",
            "nodes": {"node:caelynn": node},
            "edges": {},
            "evidence": {},
            "source_artifacts": {},
            "adjacency": {},
            "diagnostics": {},
            "identity_redirects": [],
            "aliases": {"Caelynn": "node:caelynn"},
        }
    )


def test_projection_prefers_known_mention_spans_for_chips() -> None:
    markdown = "Caelynn opened the door."
    paragraph = "Caelynn opened the door."
    sidecar = {
        "schema": "dmb_known_entity_mention_sidecar_v0",
        "mentions": [
            {
                "source_span_ref_id": "span:p1",
                "start_offset": 0,
                "end_offset": 7,
                "surface_text": "Caelynn",
                "canonical_entity_id": "node:caelynn",
                "entity_slug": "caelynn",
                "entity_kind": "pc",
                "match_method": "canonical",
                "display_name": "Caelynn",
            }
        ],
    }
    projection = build_recap_graph_projection(
        _store_with_pc(),
        session_id="session-22",
        markdown=markdown,
        paragraph_text_by_span_id={"span:p1": paragraph},
        known_entity_mentions=sidecar,
    )
    assert projection.markdown is not None
    assert "[Caelynn](dmb-node:node:caelynn)" in projection.markdown
    assert any(m.node_id == "node:caelynn" for m in projection.mentions)


def test_projection_skips_unresolved_offsets_instead_of_global_find() -> None:
    """Failed paragraph remap must not chip the first surface elsewhere in the recap."""
    markdown = (
        "Caelynn waited at the gate.\n\n"
        "Later, Caelynn opened the door."
    )
    # Wrong paragraph text so offset remap fails; surface also appears earlier.
    sidecar = {
        "schema": "dmb_known_entity_mention_sidecar_v0",
        "mentions": [
            {
                "source_span_ref_id": "span:p2",
                "start_offset": 7,
                "end_offset": 14,
                "surface_text": "Caelynn",
                "canonical_entity_id": "node:caelynn",
                "entity_slug": "caelynn",
                "entity_kind": "pc",
                "match_method": "canonical",
                "display_name": "Caelynn",
            }
        ],
    }
    projection = build_recap_graph_projection(
        _store_with_pc(),
        session_id="session-22",
        markdown=markdown,
        paragraph_text_by_span_id={
            "span:p2": "Someone else opened the door.",  # surface absent → skip
        },
        known_entity_mentions=sidecar,
    )
    assert projection.markdown is not None
    # Must not collapse onto the first "Caelynn" in the full markdown.
    assert "[Caelynn](dmb-node:node:caelynn)" not in projection.markdown
    assert all(m.node_id != "node:caelynn" for m in projection.mentions)
    assert any(
        d.code == "known_entity_mention_offset_unresolved"
        for d in projection.union_identity_diagnostics
    )


def test_projection_unique_in_paragraph_surface_still_chips() -> None:
    markdown = "Caelynn waited.\n\nLater, Caelynn opened the door."
    paragraph = "Later, Caelynn opened the door."
    sidecar = {
        "schema": "dmb_known_entity_mention_sidecar_v0",
        "mentions": [
            {
                "source_span_ref_id": "span:p2",
                # Intentionally wrong offsets; unique in-paragraph surface should recover.
                "start_offset": 0,
                "end_offset": 1,
                "surface_text": "Caelynn",
                "canonical_entity_id": "node:caelynn",
                "entity_slug": "caelynn",
                "entity_kind": "pc",
                "match_method": "canonical",
                "display_name": "Caelynn",
            }
        ],
    }
    projection = build_recap_graph_projection(
        _store_with_pc(),
        session_id="session-22",
        markdown=markdown,
        paragraph_text_by_span_id={"span:p2": paragraph},
        known_entity_mentions=sidecar,
    )
    assert projection.markdown is not None
    assert projection.markdown.count("[Caelynn](dmb-node:node:caelynn)") == 1
    # Chip must land in the second paragraph, not the first occurrence.
    first_chip = projection.markdown.index("[Caelynn](dmb-node:node:caelynn)")
    assert first_chip > markdown.index("Later")


def test_pipeline_artifact_roundtrip_feeds_live_projection() -> None:
    """Registry match → sidecar artifact → projection adapter path."""
    import json
    import shutil
    from pathlib import Path

    from apps.live_control_server.config import repo_root
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        _load_manifest_known_entity_mentions,
    )

    registry = build_known_entity_registry("longmont-c2", 22)
    spans = [
        {
            "kind": "paragraph",
            "span_id": "span:p1",
            "source_span_ref_id": "span:p1",
            "text": "Caelynn opened the door.",
        }
    ]
    sidecar = match_known_entities_in_spans(spans, registry, session_id="session-22")
    assert any(m.entity_slug == "caelynn" for m in sidecar.mentions)

    root = repo_root().resolve()
    out = root / "evals" / "graph_memory_layer" / "artifacts" / "_tmp_known_entity_repair_test"
    out.mkdir(parents=True, exist_ok=True)
    try:
        sidecar_path = out / "known_entity_mentions.json"
        sidecar_path.write_text(json.dumps(sidecar.to_dict()), encoding="utf-8")
        manifest_path = out / "graph_ingest_run_manifest.json"
        rel_uri = sidecar_path.relative_to(root).as_posix()
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": "dmb_graph_ingest_run_manifest_v0",
                    "artifacts": {
                        "known_entity_mentions": {
                            "kind": "known_entity_mentions",
                            "uri": rel_uri,
                            "exists": True,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        loaded = _load_manifest_known_entity_mentions(manifest_path)
        assert loaded is not None
        assert loaded["mentions"]

        projection = build_recap_graph_projection(
            _store_with_pc(),
            session_id="session-22",
            markdown="Caelynn opened the door.",
            paragraph_text_by_span_id={"span:p1": "Caelynn opened the door."},
            known_entity_mentions=loaded,
        )
        assert "[Caelynn](dmb-node:node:caelynn)" in (projection.markdown or "")
    finally:
        shutil.rmtree(out, ignore_errors=True)
