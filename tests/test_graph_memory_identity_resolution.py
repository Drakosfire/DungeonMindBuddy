"""Tests for src/graph_memory/identity_resolution.py.

Each test pins a specific failure mode surfaced by the S22 gpt-5.4 gap
analysis: greedy label collisions, type-only mismatches (group vs
organization), relationship-verb drift (works_with vs allied_with), and
inverse-edge duplicates (parent_of + child_of)."""

from __future__ import annotations

from src.graph_memory import identity_resolution as ir


# --------------------------------------------------------------------------- #
# Equivalence classes
# --------------------------------------------------------------------------- #

def test_node_type_classes_collapse_synonyms():
    assert ir.node_type_class("character") == ir.node_type_class("npc") == ir.node_type_class("pc") == "actor"
    assert ir.node_type_class("group") == ir.node_type_class("organization") == ir.node_type_class("faction") == "collective"
    assert ir.node_type_class("mystery") == ir.node_type_class("clue") == ir.node_type_class("thread") == "thread"
    assert ir.node_type_class("event") == ir.node_type_class("warning") == "phenomenon"
    assert ir.node_type_class("location") == ir.node_type_class("region") == ir.node_type_class("sublocation") == "place"


def test_unknown_node_type_does_not_collide():
    assert ir.node_type_class("totally_made_up") != ir.node_type_class("also_made_up")


def test_predicate_families_fold_synonyms():
    assert ir.predicate_family("works_with") == ir.predicate_family("allied_with") == "social_relation"
    assert ir.predicate_family("parent_of") == ir.predicate_family("child_of") == "kinship"
    assert ir.predicate_family("located_in") == ir.predicate_family("part_of") == "location_hierarchy"
    assert ir.predicate_family("knows_about") == ir.predicate_family("missing_contact") == "knowledge"
    assert ir.predicate_family("recruits_for") == ir.predicate_family("serves") == "membership"


def test_unknown_predicate_falls_back_to_verb():
    assert ir.predicate_family("frobnicates") == "rel:frobnicates"
    assert ir.predicate_family("frobnicates") != ir.predicate_family("wibbles")


def test_normalize_label_strips_articles_and_honorifics():
    assert ir.normalize_label("Private Hester") == "hester"
    assert ir.normalize_label("Commander Vale") == "vale"
    assert ir.normalize_label("the Reach") == "reach"
    assert ir.normalize_label("Professor Tealeaf") == "tealeaf"


# --------------------------------------------------------------------------- #
# Node matching
# --------------------------------------------------------------------------- #

def _node(nid: str, label: str, ntype: str, corpus_ref=None, anchors=(), spans=()):
    node = {"node_id": nid, "label": label, "node_type": ntype}
    if corpus_ref is not None:
        node["corpus_ref"] = corpus_ref
    refs = [{"source_anchor_id": a} for a in anchors]
    refs += [{"source_line_start": s, "source_line_end": e} for (s, e) in spans]
    if refs:
        node["evidence_refs"] = refs
    return node


def test_type_only_mismatch_still_matches():
    # gold "organization" vs candidate "group" for the same city guard.
    gold = _node("node:city-guard", "Mirathorn city guard", "organization")
    cand = _node("group_city_guard", "city guard", "group")
    assert ir.nodes_match(gold, cand)


def test_weak_label_divergence_is_not_force_matched():
    # "Converging hail storm" vs "approaching major storm" share only the common
    # token "storm"; label-only matching must NOT pair these (false-positive
    # risk). This is the honest ceiling of label matching for divergent phrasing.
    gold = _node("node:storm-hail", "Converging hail storm", "event")
    cand = _node("warning_major_storm", "approaching major storm", "warning")
    assert not ir.nodes_match(gold, cand)


def test_shared_anchor_rescues_weak_label_divergence():
    # The same divergent storm pair becomes a match once both cite the same
    # source anchor. This is the lever for the storm/song/knocking gaps: align
    # the candidate's evidence anchors with the gold's anchor ids.
    gold = _node("node:storm-hail", "Converging hail storm", "event", anchors=["anchor:s22-storm"])
    cand = _node("warning_major_storm", "approaching major storm", "warning", anchors=["anchor:s22-storm"])
    assert ir.nodes_match(gold, cand)


def test_unresolved_phenomenon_maps_to_phenomenon():
    # the autonomous extractor labels temporal/observed nodes "unresolved_phenomenon";
    # it must fold to the same class as gold's "event"/"warning" so a storm node
    # is not class-forked off into an unknown bucket.
    assert ir.node_type_class("unresolved_phenomenon") == ir.node_type_class("phenomenon") == "phenomenon"
    assert ir.node_type_class("event") == ir.node_type_class("unresolved_phenomenon")


def test_evidence_line_spans_reads_and_normalizes():
    node = _node("n", "x", "mystery", spans=[(27, 27), (35, 31)])
    assert ir.evidence_line_spans(node) == {(27, 27), (31, 35)}


def test_span_overlap_rescues_divergent_phrasing():
    # gold cites a curated anchor that resolves to line 23; the extractor cites a
    # paragraph spref that also resolves to line 23. The addressing schemes differ
    # (anchor id vs line span) but the source location is the same, and the labels
    # share >=2 content tokens -> the pair is rescued just like the anchor case.
    gold = _node("node:delayed-puddles", "Delayed puddle reflections", "mystery", spans=[(23, 23)])
    cand = _node("clue_puddles", "Roadside puddles show delayed reflections", "clue", spans=[(23, 23)])
    assert ir.label_similarity(gold["label"], cand["label"]) < 0.6  # label alone is insufficient
    assert ir.nodes_match(gold, cand)


def test_span_overlap_requires_label_support():
    # Two DISTINCT "...Reach" places named in the same paragraph (overlapping span)
    # share only the generic token "reach"; span overlap must NOT force-match them.
    gold = _node("node:mireward-reach", "Mireward Reach / Golden Fields", "location", spans=[(5, 5)])
    cand = _node("loc_elderwild", "Elderwild Reach", "location", spans=[(5, 5)])
    assert not ir.nodes_match(gold, cand)


def test_span_overlap_folds_plurals_for_label_support():
    # "storm" vs "storms" and "reflection" vs "reflections" must count as shared
    # content tokens so plural drift does not starve the span rescue.
    gold = _node("node:storm", "Converging hail storm", "event", spans=[(31, 31)])
    cand = _node("phen_storm", "Converging storms create severe weather", "unresolved_phenomenon", spans=[(31, 31)])
    assert ir.nodes_match(gold, cand)


def test_span_overlap_without_overlap_does_not_match():
    # Same divergent labels but non-overlapping spans -> no rescue.
    gold = _node("node:delayed-puddles", "Delayed puddle reflections", "mystery", spans=[(23, 23)])
    cand = _node("clue_puddles", "Roadside puddles show delayed reflections", "clue", spans=[(40, 40)])
    assert not ir.nodes_match(gold, cand)


def test_unrelated_kinds_do_not_match_on_shared_token():
    gold = _node("node:frank", "Frank", "character")
    cand = _node("item_frank_bottle", "Frank's bottle", "item")
    assert not ir.nodes_match(gold, cand)


def test_resolved_corpus_ref_is_decisive():
    cr = {"type": "npc", "ref_id": "captain_lysandra_ironveil", "resolution": "resolved",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md"}
    gold = _node("node:captain-lysandra", "Lysandra", "character", corpus_ref=cr)
    cand = _node("character_lysandra", "Lieutenant L.", "character", corpus_ref=dict(cr))
    # labels disagree, but identical resolved hub_path forces a match.
    assert ir.nodes_match(gold, cand)


def test_corpus_ref_splits_distinct_subentities_sharing_a_hub():
    # A location/collection hub (Mireward) documents many distinct sub-entities,
    # each with its own ref_id but the SAME hub_path. Keying on hub_path alone
    # collapses them into one node (silent cross-session corruption); pairing
    # hub_path with ref_id keeps them distinct.
    hub = "Elderwyld/Cities and Towns/Mireward/README.md"
    city = _node("n_mireward", "Mireward", "location",
                 corpus_ref={"type": "location", "ref_id": "mireward", "hub_path": hub})
    gate = _node("n_north_gate", "North gate", "location",
                 corpus_ref={"type": "location", "ref_id": "north_gate", "hub_path": hub})
    assert ir.canonical_node_key(city) != ir.canonical_node_key(gate)
    assert not ir.nodes_match(city, gate)
    result = ir.dedup_nodes([city, gate])
    assert len(result["kept"]) == 2


def test_corpus_ref_merges_same_entity_across_sessions():
    # The same NPC hub (one entity = one ref_id) must still merge across sessions:
    # identical hub_path AND ref_id -> identical canonical key -> decisive match.
    cr = {"type": "npc", "ref_id": "captain_lysandra_ironveil",
          "hub_path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md"}
    s22 = _node("node:captain-lysandra", "Lysandra", "character", corpus_ref=dict(cr))
    s23 = _node("character_lysandra", "Lieutenant Lysandra", "character", corpus_ref=dict(cr))
    assert ir.canonical_node_key(s22) == ir.canonical_node_key(s23)
    assert ir.node_match_score(s22, s23) == 1.0


def test_best_match_assignment_resolves_mireward_collision():
    gold = [
        _node("node:mireward-reach", "Mireward Reach / Golden Fields", "location"),
        _node("node:mireward", "Mireward", "location"),
    ]
    cand = [
        _node("location_mireward", "Mireward", "location"),
        _node("location_reach", "the Reach", "location"),
    ]
    pairs = ir.best_match_assignment(gold, cand, ir.node_match_score)
    matched_gold = {gold[gi]["node_id"] for gi, _ci, _s in pairs}
    # the narrow "Mireward" gold node must win the candidate "Mireward",
    # not be starved by the broad "Mireward Reach" label.
    assert "node:mireward" in matched_gold
    # each candidate used at most once
    used_cand = [ci for _gi, ci, _s in pairs]
    assert len(used_cand) == len(set(used_cand))


# --------------------------------------------------------------------------- #
# Edge matching & dedup
# --------------------------------------------------------------------------- #

def _edge(eid, frm, to, rel):
    return {"edge_id": eid, "from_node_id": frm, "to_node_id": to, "relationship_type": rel}


def test_edge_matches_across_relationship_drift():
    g_nodes = [_node("g_grob", "Grobnok", "character"), _node("g_sara", "Sara", "character")]
    c_nodes = [_node("c_grob", "Grobnok", "character"), _node("c_sara", "Sara", "character")]
    gi = ir.node_index(g_nodes)
    ci = ir.node_index(c_nodes)
    gold = _edge("e_g", "g_grob", "g_sara", "missing_contact")
    cand = _edge("e_c", "c_grob", "c_sara", "knows_about")
    # both fold to the "knowledge" family with matching endpoints.
    assert ir.edge_match_score(gold, cand, gi, ci) >= 0.6


def test_symmetric_family_matches_swapped_endpoints():
    g_nodes = [_node("g_dw", "Dustwalker", "character"), _node("g_song", "shared song", "mystery")]
    c_nodes = [_node("c_song", "mysterious shared song", "clue"), _node("c_dw", "the Dustwalker", "character")]
    gi, ci = ir.node_index(g_nodes), ir.node_index(c_nodes)
    gold = _edge("e_g", "g_dw", "g_song", "associated_with")
    cand = _edge("e_c", "c_song", "c_dw", "associated_with")  # endpoints swapped
    assert ir.edge_match_score(gold, cand, gi, ci) >= 0.6


def test_inverse_edges_dedup_to_one():
    nodes = [_node("n_lo", "Lysandro", "character"), _node("n_la", "Lysandra", "character")]
    edges = [
        _edge("e1", "n_lo", "n_la", "parent_of"),
        _edge("e2", "n_la", "n_lo", "child_of"),
    ]
    result = ir.dedup_edges(edges, nodes)
    assert len(result["kept"]) == 1
    assert len(result["merged"]) == 1


def test_parent_of_vs_recognizes_classified_as_family_mismatch():
    g_nodes = [_node("g_grob", "Grobnok", "character"), _node("g_sara", "Sara", "character")]
    c_nodes = [_node("c_grob", "Grobnok", "character"), _node("c_sara", "Sara", "character")]
    gi, ci = ir.node_index(g_nodes), ir.node_index(c_nodes)
    gold = _edge("e_g", "g_grob", "g_sara", "parent_of")
    cand = _edge("e_c", "c_grob", "c_sara", "recognizes")
    diagnosis = ir.classify_edge_alignment(gold, cand, gi, ci)
    assert diagnosis["reason"] == "family_mismatch"
    assert diagnosis["gold_predicate_family"] == "kinship"
    assert diagnosis["live_predicate_family"] == "rel:recognizes"
    assert diagnosis["best_score"] == ir.edge_match_score(gold, cand, gi, ci)


def test_dedup_nodes_collapses_same_canonical_key():
    nodes = [
        _node("a", "Mirathorn", "location"),
        _node("b", "Mirathorn", "location"),
        _node("c", "the swamp", "location"),
    ]
    result = ir.dedup_nodes(nodes)
    assert len(result["kept"]) == 2
    assert len(result["merged"]) == 1
