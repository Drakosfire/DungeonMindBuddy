"""Pinned party references must attach support without redefining canonical actors."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    WorldGraphMutationContext,
)
from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.extract_identity_gate import gate_candidate_graph_against_head

_ARTIFACT = "artifact:recap:synthetic:session-13"
_PCS = ["baergrom", "bonogo", "caelynn", "ephanna", "karsemine", "stafl"]


def _node(ref_id: str, ref_type: str = "pc") -> dict:
    return {
        "node_id": f"node:{ref_id}",
        "label": ref_id.title(),
        "node_type": "character",
        "description": "Source-specific participation, not canonical character replacement.",
        "importance": "high",
        "aliases": [],
        "proposed_action": "anchor",
        "confidence": "high",
        "warnings": [],
        "corpus_ref": {"type": ref_type, "ref_id": ref_id, "resolution": "resolved"},
        "semantic_state": {
            "canon_state": "played_canon",
            "lifecycle_state": "candidate",
            "evidence_role": "source_evidence",
            "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "evidence_refs": [
            {
                "source_ref_id": f"{_ARTIFACT}:text",
                "source_artifact_id": _ARTIFACT,
                "source_anchor_id": f"anchor:{ref_id}",
                "label": "source span",
                "evidence_role": "source_evidence",
                "can_open_source": True,
                "can_highlight_span": True,
                "source_span_ref_id": f"{_ARTIFACT}:span:{ref_id}",
                "anchor_quotes": [ref_id.title()],
            }
        ],
    }


def _context(objects: list[MutationObject]) -> WorldGraphMutationContext:
    return WorldGraphMutationContext(
        world_id="test-world",
        revision_id="rev:pinned",
        head_revision_id="rev:pinned",
        objects={obj.object_id: obj for obj in objects},
    )


def _actor(
    name: str, *, kind: str = "player_character", prefix: str = "pc"
) -> MutationObject:
    return MutationObject(
        object_id=f"{prefix}:{name}",
        label=name.title(),
        kind=kind,
        aliases=(f"Known {name.title()}",),
        canon_state="canonical",
        memory_state="active",
    )


def _gate(nodes: list[dict], context: WorldGraphMutationContext):
    preview = candidate_graph_preview_from_dict(
        {
            "schema": "dmb_candidate_graph_preview_v0",
            "version": "0.1",
            "status": "preview",
            "preview_id": "known-party-synthetic",
            "campaign_id": "test-campaign",
            "session_id": "session-13",
            "source_artifact_ids": [_ARTIFACT],
            "nodes": nodes,
            "edges": [],
            "beats": [],
            "deferred_items": [],
            "ignored_items": [],
            "proposed_writes": [],
            "diagnostics": {
                "preview_only": True,
                "extraction_performed": False,
                "llm_used": False,
                "runtime_connected": False,
                "plan_connected": False,
                "agent_interaction_connected": False,
                "corpus_scanned": False,
                "corpus_mutated": False,
                "facts_promoted": False,
                "canon_promoted": False,
                "unresolved_evidence_refs": 0,
                "missing_evidence_objects": 0,
                "warning_count": 0,
            },
        }
    )
    return gate_candidate_graph_against_head(
        preview,
        mutation_context=context,
        world_id="test-world",
        source_artifact_id=_ARTIFACT,
        source_revision_id="sha256:" + "a" * 64,
        source_uri="repo://synthetic-session-13.md",
        campaign_scope="test-campaign",
    )


def test_six_pcs_and_npc_companion_bind_exact_references_support_only() -> None:
    actors = [_actor(name) for name in _PCS] + [
        _actor("companion", kind="npc", prefix="node")
    ]
    context = _context(actors)
    before = copy.deepcopy(context)
    result = _gate(
        [_node(name) for name in _PCS] + [_node("companion", "npc")], context
    )
    assert result.node_id_map == {f"node:{name}": f"pc:{name}" for name in _PCS} | {
        "node:companion": "node:companion"
    }
    assert set(result.identity_outcome_snapshot.values()) == {"resolved_existing"}
    assert result.unresolved_mentions == result.rejected_assertions == []
    assert result.accepted_proposals
    assert all(
        assertion.assertion_kind != "node" for assertion in result.accepted_proposals
    )
    assert {
        assertion.subject_node_id for assertion in result.accepted_proposals
    } == set(context.objects)
    for assertion in result.accepted_proposals:
        if assertion.assertion_kind == "attribute":
            assert (
                assertion.value["kind"]
                == context.objects[assertion.subject_node_id].kind
            )
    assert (
        context == before
    )  # Canonical kinds, labels, aliases and state were not rewritten.


@pytest.mark.parametrize("kind", ["pc", "player_character", "dnd5e:player_character"])
def test_existing_pc_kind_representations_normalize(kind: str) -> None:
    result = _gate([_node("baergrom")], _context([_actor("baergrom", kind=kind)]))
    assert result.node_id_map == {"node:baergrom": "pc:baergrom"}
    assert all(
        assertion.assertion_kind != "node" for assertion in result.accepted_proposals
    )


@pytest.mark.parametrize(
    "case",
    [
        "missing_ref",
        "unresolved_ref",
        "missing_object",
        "wrong_kind",
        "wrong_ref_type",
        "missing_ref_id",
        "wrong_ref_id",
        "wrong_label",
        "ambiguous",
        "provisional",
        "redirected",
        "wrong_world",
        "wrong_node_type",
    ],
)
def test_invalid_known_party_references_fail_closed(case: str) -> None:
    node = _node("baergrom")
    context = _context([_actor("baergrom")])
    if case == "missing_ref":
        node["corpus_ref"] = None
    elif case == "unresolved_ref":
        node["corpus_ref"]["resolution"] = "unresolved"
    elif case == "missing_object":
        context = _context([])
    elif case == "wrong_kind":
        context = _context([_actor("baergrom", kind="npc")])
    elif case == "wrong_ref_type":
        node["corpus_ref"]["type"] = "npc"
    elif case == "missing_ref_id":
        node["corpus_ref"]["ref_id"] = ""
    elif case == "wrong_ref_id":
        node["corpus_ref"]["ref_id"] = "bonogo"
    elif case == "wrong_label":
        node["label"] = "Bonogo"
    elif case == "ambiguous":
        context = _context([_actor("baergrom"), _actor("baergrom", prefix="node")])
    elif case == "provisional":
        context = _context(
            [replace(_actor("baergrom"), canon_state="noncanonical_provisional")]
        )
    elif case == "redirected":
        context = replace(context, identity_redirects={"pc:baergrom": "pc:other"})
    elif case == "wrong_world":
        context = replace(context, world_id="other-world")
    elif case == "wrong_node_type":
        node["node_type"] = "item"
    before = copy.deepcopy(context)
    with pytest.raises(CandidateGraphMappingError, match="known party"):
        _gate([node], context)
    assert context == before


def test_normalized_ref_id_and_registered_alias_keep_exact_target() -> None:
    node = _node("stone_heart")
    node["label"] = "Known Stone Heart"
    target = MutationObject(
        object_id="pc:stone-heart",
        label="Stone Heart",
        aliases=("Known Stone Heart",),
        kind="player_character",
        canon_state="canonical",
    )
    result = _gate([node], _context([target]))
    assert result.node_id_map == {"node:stone_heart": "pc:stone-heart"}


def test_unanchored_new_character_stays_npc() -> None:
    node = _node("new_mage")
    node["corpus_ref"] = None
    node["proposed_action"] = "create"
    result = _gate([node], _context([]))
    (assertion,) = [a for a in result.accepted_proposals if a.assertion_kind == "node"]
    assert assertion.value["kind"] == "npc"


def test_legacy_unreferenced_character_match_keeps_existing_pc_identity() -> None:
    node = _node("baergrom")
    node["corpus_ref"] = None
    node["proposed_action"] = "create"
    result = _gate([node], _context([_actor("baergrom", kind="pc")]))
    assert result.node_id_map == {"node:baergrom": "pc:baergrom"}
    assert result.identity_outcome_snapshot["node:baergrom"] == "resolved_existing"
    assert all(a.assertion_kind != "node" for a in result.accepted_proposals)


def test_prior_identity_decision_cannot_retarget_a_verified_party_reference() -> None:
    from apps.live_control_server.models.world_graph_identity_models import (
        IdentityDecisionRecord,
    )

    context = _context([_actor("baergrom"), _actor("bonogo")])
    context = replace(
        context,
        identity_decisions=(
            IdentityDecisionRecord(
                decision_id="decision:synthetic",
                world_id="test-world",
                decision_kind="human_override",
                created_at="2026-10-07T00:00:00Z",
                actor="synthetic-operator",
                reason="Conflicting prior target",
                source_candidate_id="node:baergrom",
                target_node_id="pc:bonogo",
            ),
        ),
    )
    with pytest.raises(
        CandidateGraphMappingError, match="changed its verified pinned identity"
    ):
        _gate([_node("baergrom")], context)


@pytest.mark.parametrize(
    "ref_type,target_id", [("pc", "pc:shared"), ("npc", "npc:shared")]
)
def test_reference_type_disambiguates_pc_and_npc_with_the_same_slug(
    ref_type: str, target_id: str
) -> None:
    context = _context([_actor("shared"), _actor("shared", kind="npc", prefix="npc")])
    result = _gate([_node("shared", ref_type)], context)
    assert result.node_id_map == {"node:shared": target_id}
    assert all(a.assertion_kind != "node" for a in result.accepted_proposals)



def _reviewed_binding_case():
    from apps.live_control_server.models.extract_promote import ReviewedCorpusNativeBindingV1
    actor = replace(_actor("guide", kind="npc"), object_id="npc_guide")
    node = _node("guide_full", "npc")
    node["label"] = "Guide"
    binding = ReviewedCorpusNativeBindingV1(
        world_id="test-world", parent_revision_id="rev:pinned", campaign_id="test-campaign",
        candidate_sha256="a" * 64, candidate_node_id=node["node_id"],
        corpus_ref_type="npc", corpus_ref_key="guide full", target_object_id="npc_guide",
        target_sha256="b" * 64, evidence_sha256="c" * 64,
        decision_id="decision:binding", reviewer_id="reviewer:synthetic",
        sources=({"source_artifact_id":"artifact:origin", "source_revision_id":"revision:origin",
                  "artifact_sha256":"d" * 64, "revision_sha256":"e" * 64},),
    )
    context = replace(_context([actor]), reviewed_corpus_bindings=(binding,), exact_candidate_sha256="a" * 64)
    return node, context, binding


def test_reviewed_binding_attaches_support_to_bare_native_id_without_alias_invention():
    node, context, _ = _reviewed_binding_case()
    before = copy.deepcopy(context)
    result = _gate([node], context)
    assert result.node_id_map == {node["node_id"]: "npc_guide"}
    assert all(a.assertion_kind != "node" for a in result.accepted_proposals)
    assert context == before


@pytest.mark.parametrize("case", ["world", "head", "campaign", "digest", "ref", "type", "kind", "missing", "retracted", "redirect", "conflict", "unbound"])
def test_reviewed_binding_rejects_wrong_or_inactive_basis(case):
    node, context, binding = _reviewed_binding_case()
    updates = {"world":"world_id", "head":"parent_revision_id", "campaign":"campaign_id",
               "digest":"candidate_sha256", "ref":"corpus_ref_key", "type":"corpus_ref_type"}
    if case in updates:
        value = "b" * 64 if case == "digest" else "wrong"
        binding = binding.model_copy(update={updates[case]:value})
        context = replace(context, reviewed_corpus_bindings=(binding,))
    elif case == "kind":
        context = replace(context, objects={"npc_guide":replace(context.objects["npc_guide"], kind="faction")})
    elif case == "missing":
        context = replace(context, objects={})
    elif case == "retracted":
        context = replace(context, objects={"npc_guide":replace(context.objects["npc_guide"], canon_state="rejected")})
    elif case == "redirect":
        context = replace(context, identity_redirects={"npc_guide":"npc:other"})
    elif case == "conflict":
        context = replace(context, reviewed_corpus_bindings=(binding,binding))
    else:
        context = replace(context, reviewed_corpus_bindings=())
    with pytest.raises(CandidateGraphMappingError):
        _gate([node], context)
