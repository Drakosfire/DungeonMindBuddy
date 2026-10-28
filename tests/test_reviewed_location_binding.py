"""Reviewed location reuse never permits automatic category reuse."""
from dataclasses import replace

import pytest

from apps.live_control_server.models.extract_promote import ReviewedCorpusNativeBindingV2
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from tests.test_known_party_anchor_admission import _gate, _reviewed_binding_case


def case():
    node, context, previous = _reviewed_binding_case()
    node.update(node_type="location", corpus_ref=None, proposed_action="create")
    target = replace(context.objects[previous.target_object_id], kind="location")
    payload = previous.model_dump(mode="json")
    payload.update(schema_version="dmb_reviewed_corpus_native_binding_v2", corpus_ref_type="location")
    binding = ReviewedCorpusNativeBindingV2.model_validate(payload)
    context = replace(context, objects={target.object_id: target}, reviewed_corpus_bindings=(binding,))
    return node, context, binding


def test_reviewed_location_uses_existing_object_without_replacement():
    node, context, binding = case()
    result = _gate([node], context)
    assert result.node_id_map == {node["node_id"]: binding.target_object_id}
    assert all(p.assertion_kind != "node" for p in result.accepted_proposals)


@pytest.mark.parametrize("change", ["kind", "node_type", "candidate", "head", "digest", "redirect", "corpus_ref"])
def test_location_binding_refuses_invalid_basis(change):
    node, context, binding = case()
    if change == "kind":
        target = replace(context.objects[binding.target_object_id], kind="item")
        context = replace(context, objects={target.object_id: target})
    elif change == "node_type":
        node["node_type"] = "item"
    elif change in {"head", "digest"}:
        field = "parent_revision_id" if change == "head" else "candidate_sha256"
        binding = binding.model_copy(update={field: "b" * 64})
        context = replace(context, reviewed_corpus_bindings=(binding,))
    elif change == "candidate":
        binding = binding.model_copy(update={"candidate_node_id": "other-candidate"})
        context = replace(context, reviewed_corpus_bindings=(binding,))
        result = _gate([node], context)
        assert node["node_id"] not in result.node_id_map
        return
    elif change == "redirect":
        context = replace(context, identity_redirects={binding.target_object_id: "other-location"})
    else:
        node["corpus_ref"] = {"type": "npc", "ref_id": "guide", "resolution": "resolved"}
    with pytest.raises(CandidateGraphMappingError):
        _gate([node], context)
