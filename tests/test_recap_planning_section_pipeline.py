import hashlib

from graph_memory.party_context import PartyContext, PartyMember
from graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict
from src.graph_memory.extraction import category_candidate_graph_extractor as module
from src.graph_memory.extraction.worldbuilding_plumbing_profile import WORLDBUILDING_PLUMBING_PROFILE

TEXT = "## Planning Notes\n\nIria will receive the Golden Map.\n\n## Recap\n\nIria arrived in Larkhaven."


def setup(source_text=TEXT):
    index = source_span_index_to_dict(build_source_span_index_for_text(
        source_artifact_id="artifact:synthetic", content_sha256=hashlib.sha256(source_text.encode()).hexdigest(), text=source_text,
    ))
    rows = module.source_packet_rows_from_span_index(index, source_text=source_text)
    planned = next(r for r in rows if "Golden Map" in r["text"])
    played = next(r for r in rows if "arrived" in r["text"])
    return index, planned, played


class Client(module.FixtureCategoryGraphPassClient):
    def __init__(self, planned, played, fill=False):
        bad = {"node_id": "event:reward", "label": "Golden Map reward", "node_type": "event", "description": "Iria received the Golden Map.", "importance": "medium", "evidence_refs": [{"source_span_ref_id": planned["source_span_ref_id"], "anchor_quotes": ["Iria will receive the Golden Map."]}]}
        good = {"node_id": "loc:larkhaven", "label": "Larkhaven", "node_type": "location", "description": "Iria arrived here.", "importance": "medium", "evidence_refs": [{"source_span_ref_id": played["source_span_ref_id"], "anchor_quotes": ["Iria arrived in Larkhaven."]}]}
        payloads = {"thread_pass": {"observation_nodes": [bad]}, "location_pass": {"observation_nodes": [good]}}
        if fill:
            payloads["pc_claimed_fill_pass"] = {"filled_nodes": [{**bad, "node_id": "node:iria", "label": "Iria"}]}
        super().__init__(payloads)
        self.messages = []

    def run_pass(self, name, **kwargs):
        self.messages.append((name, kwargs["user_content"]))
        return super().run_pass(name, **kwargs)


def options(index, source_text=TEXT, **kwargs):
    return module.CategoryGraphExtractionOptions(
        campaign_id="longmont-c2", session_id="session-1", session_number=1,
        source_span_index=index, source_text=source_text, model_id="synthetic", **kwargs,
    )


def test_pipeline_withholds_planning_prompts_and_rejects_injected_citation():
    index, planned, played = setup()
    client = Client(planned, played)
    result = module.run_category_pipeline(client, options(index, enable_party_claimed_fill=False))
    assert all("Golden Map" not in message for _, message in client.messages)
    assert any(n["node_id"] == "loc:larkhaven" for n in result.candidate_graph["nodes"])
    assert not any(n["node_id"] == "event:reward" for n in result.candidate_graph["nodes"])
    from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph
    preview = load_typed_candidate_graph(result.candidate_graph)
    assert all(n.semantic_state.canon_state == "played_canon" for n in preview.nodes)
    assert all("Golden Map" not in n.description for n in preview.nodes)
    deferred = result.candidate_graph["deferred_items"]
    assert any("planning" in d["reason"].lower() and d["evidence_refs"] for d in deferred)
    assert result.diagnostics["recap_source_authority"]["checked"]
    assert any(d["evidence_refs"][0]["can_open_source"] for d in deferred)
    assert any(d["evidence_refs"][0]["source_span_ref_id"] == planned["source_span_ref_id"] for d in deferred)


def test_party_fill_cannot_reintroduce_withheld_planning(monkeypatch):
    index, planned, played = setup()
    member = PartyMember("iria", "pc", "Iria", "pc", "", False)
    party = PartyContext("longmont-c2", "1", ("Iria",), (member,))
    monkeypatch.setattr(module, "build_party_context_for_campaign", lambda *a, **k: party)
    client = Client(planned, played, fill=True)
    result = module.run_category_pipeline(client, options(index))
    assert all("Golden Map" not in message for _, message in client.messages)
    assert not any("Golden Map" in n["description"] for n in result.candidate_graph["nodes"])
    assert any(name == "pc_claimed_fill_pass" for name, _ in client.messages)


def test_canonical_spans_keep_literal_recap_marker_inside_planning_fence():
    text = (
        "## Planning Notes\n\n```text\n```literal\n**Recap**:\n"
        "Iria will receive the Golden Map.\n```\n\nStill planned.\n"
        "\n## Recap\n\nIria arrived in Larkhaven."
    )
    index, planned, played = setup(text)
    client = Client(planned, played)
    result = module.run_category_pipeline(client, options(index, source_text=text, enable_party_claimed_fill=False))
    assert all("Golden Map" not in message for _, message in client.messages)
    assert any(node["node_id"] == "loc:larkhaven" for node in result.candidate_graph["nodes"])
    assert not any(node["node_id"] == "event:reward" for node in result.candidate_graph["nodes"])
    assert any(
        ref["source_span_ref_id"] == planned["source_span_ref_id"]
        for item in result.candidate_graph["deferred_items"]
        for ref in item.get("evidence_refs", [])
    )


def test_canonical_spans_do_not_withhold_headings_inside_literal_code():
    text = (
        "A note introduces an example.\n\n````markdown\n## Planning Notes\n"
        "**Recap**:\nIria will receive the Golden Map.\n````\n\n"
        "## Recap\nIria arrived in Larkhaven."
    )
    index, planned, played = setup(text)
    client = Client(planned, played)
    result = module.run_category_pipeline(client, options(index, source_text=text, enable_party_claimed_fill=False))
    assert any("Golden Map" in message for _, message in client.messages)
    assert any(node["node_id"] == "event:reward" for node in result.candidate_graph["nodes"])
    assert any(node["node_id"] == "loc:larkhaven" for node in result.candidate_graph["nodes"])
    assert result.diagnostics["recap_source_authority"]["withheld_span_ids"] == []


def test_worldbuilding_profile_preserves_its_original_source_selection():
    index, planned, played = setup()
    client = Client(planned, played)
    result = module.run_category_pipeline(client, options(index, profile=WORLDBUILDING_PLUMBING_PROFILE))
    assert any("Golden Map" in message for _, message in client.messages)
    assert result.diagnostics["recap_source_authority"]["reason"] == "not_recap_profile"
