import pytest
from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
    GAZETTEER_PROFILE, GAZETTEER_LIVESTOCK_HYGIENE_PROFILE,
    compile_gazetteer_livestock_hygiene,
    validate_gazetteer_candidate_bounds,
)
from src.graph_memory.extraction.worldbuilding_gazetteer_role_citations import (
    GAZETTEER_ROLE_CITATION_PROFILE,
    compile_gazetteer_role_citations,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import PUBLISHABLE_WORLDBUILDING_PROFILES


def test_closed_publication_profiles_preserve_pilot_and_exact_gazetteer_version():
    assert set(PUBLISHABLE_WORLDBUILDING_PROFILES) == {
        "worldbuilding_shepherds_flock_v0@0.1", "worldbuilding_gazetteer_v1@1.0",
        "worldbuilding_gazetteer_v1@1.1", "worldbuilding_gazetteer_v1@1.2",
        "worldbuilding_gazetteer_v1@1.3", "worldbuilding_gazetteer_v1@1.4",
        "worldbuilding_gazetteer_v1@1.5", "worldbuilding_gazetteer_v1@1.6",
        "worldbuilding_gazetteer_v1@1.7"}
    assert "worldbuilding_gazetteer_v1@2.0" not in PUBLISHABLE_WORLDBUILDING_PROFILES
    assert "worldbuilding_plumbing_v0@0.1" not in PUBLISHABLE_WORLDBUILDING_PROFILES


def test_definition_pass_has_no_played_or_individual_invention():
    definitions = next(p for p in GAZETTEER_PROFILE.node_passes if p.pass_id == "definition_pass")
    assert definitions.allowed_node_types == ("event",)
    for phrase in ["Do not mint species", "place descriptions", "never a played episode", "defer unplayed"]:
        assert phrase in definitions.instruction
    assert GAZETTEER_PROFILE.beat_pass is None
    assert not GAZETTEER_PROFILE.enable_party_participation_attachment
    assert GAZETTEER_PROFILE.default_semantic_state["canon_state"] == "worldbuilding_draft"


def _livestock_source_rows():
    texts = [
        "#### Fantastic Livestock for the Exampleland",
        "#### 1. Float Goats",
        "Float Goats walk on water and carry goods across lakes.",
        "#### 2. Glow Sheep",
        "Glow Sheep provide luminous wool.",
        "## Cultural Significance",
        "Float Goats symbolize joy and lightness in local culture.",
        "### Festival of Expansion",
        "The Festival of Expansion commemorates the city's growth.",
        "### Unrelated City",
        "This unrelated city detail must not move to the Exampleland.",
    ]
    rows = [{"source_span_ref_id": f"span:{index}", "line_start": index + 1,
             "line_end": index + 1, "text": value}
            for index, value in enumerate(texts)]
    return texts, rows


def _source_ref(rows, index):
    return {"source_span_ref_id": rows[index]["source_span_ref_id"],
            "anchor_quotes": [rows[index]["text"]]}


def test_v16_defers_only_exact_livestock_events_and_incident_edges():
    _texts, rows = _livestock_source_rows()
    original_node = {
        "node_id": "event:goats", "label": "Float Goats Livestock Definition",
        "node_type": "event", "description": "Source-backed goat definition.",
        "evidence_refs": [_source_ref(rows, 2)],
        "qualifiers": {"scope": "owner place", "authorship": "setting guide"},
    }
    original_edge = {
        "edge_id": "edge:goats", "from_node_id": "event:goats",
        "to_node_id": "place:exampleland", "relationship_type": "located_in",
        "label": "", "qualifiers": {"certainty": "qualified", "basis": "heading"},
        "evidence_refs": [_source_ref(rows, 2)],
    }
    graph = {
        "session_id": None,
        "beats": [],
        "nodes": [
            {"node_id": "place:exampleland", "label": "The Exampleland",
             "node_type": "location", "description": "Original place context.",
             "evidence_refs": [_source_ref(rows, 0)]},
            original_node,
            {"node_id": "event:culture", "label": "Cultural Significance of Float Goats",
             "node_type": "event", "description": "Source-backed culture passage.",
             "evidence_refs": [_source_ref(rows, 6)]},
            {"node_id": "event:festival", "label": "Festival of Expansion",
             "node_type": "event", "description": "A named recurring festival.",
             "evidence_refs": [_source_ref(rows, 8)]},
            {"node_id": "event:mixed", "label": "Float Goats",
             "node_type": "event", "description": "Ambiguous cross-section evidence.",
             "evidence_refs": [_source_ref(rows, 2), _source_ref(rows, 8)]},
        ],
        "edges": [
            original_edge,
            {"edge_id": "edge:festival", "from_node_id": "event:festival",
             "to_node_id": "place:exampleland", "relationship_type": "present_at",
             "label": "festival in place", "evidence_refs": [_source_ref(rows, 8)]},
        ],
        "deferred_items": [],
    }

    transformed, diagnostics = compile_gazetteer_livestock_hygiene(graph, rows)
    node_ids = {node["node_id"] for node in transformed["nodes"]}
    edge_ids = {edge["edge_id"] for edge in transformed["edges"]}
    place = next(node for node in transformed["nodes"] if node["node_id"] == "place:exampleland")
    deferred = {item["item_id"]: item for item in transformed["deferred_items"]}

    assert "event:goats" not in node_ids and "event:culture" not in node_ids
    assert {"event:festival", "event:mixed"} <= node_ids
    assert "edge:goats" not in edge_ids and "edge:festival" in edge_ids
    assert all(edge["from_node_id"] in node_ids and edge["to_node_id"] in node_ids
               for edge in transformed["edges"])
    assert "Float Goats walk on water" in place["description"]
    assert "Float Goats symbolize joy" in place["description"]
    assert "unrelated city detail" not in place["description"]
    assert "deferred:livestock-section:node:event:goats" in deferred
    assert "deferred:livestock-section:node:event:culture" in deferred
    assert "deferred:livestock-section:edge:edge:goats" in deferred
    assert deferred["deferred:livestock-section:node:event:goats"]["evidence_refs"] == [
        _source_ref(rows, 2),
    ]
    assert diagnostics["livestock_semantic_hygiene"]["profile"] == "worldbuilding_gazetteer_v1@1.6"
    proposals = diagnostics["livestock_semantic_hygiene"]["deferred_proposals"]
    assert proposals["deferred:livestock-section:node:event:goats"] == {
        "item_id": "deferred:livestock-section:node:event:goats",
        "kind": "node",
        "proposal": original_node,
    }
    assert proposals["deferred:livestock-section:edge:edge:goats"] == {
        "item_id": "deferred:livestock-section:edge:edge:goats",
        "kind": "edge",
        "proposal": original_edge,
    }


def test_v16_real_pipeline_retains_livestock_and_keeps_recurring_festival():
    from types import SimpleNamespace
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions, FixtureCategoryGraphPassClient, run_category_pipeline,
    )
    from src.graph_memory.extraction.bounded_recap_execution import (
        BoundedRecapPassClient, DEEPSEEK_MODEL,
    )

    texts, rows = _livestock_source_rows()

    def ref(index):
        return _source_ref(rows, index)

    outputs = {
        "location_pass": {"observation_nodes": [{
            "node_id": "place:exampleland", "label": "The Exampleland",
            "node_type": "location", "description": "Original place context.",
            "importance": "medium", "evidence_refs": [ref(0)],
        }]},
        "definition_pass": {"observation_nodes": [
            {"node_id": "event:goats", "label": "Float Goats Livestock Definition",
             "node_type": "event", "description": "Source-backed goat definition.",
             "importance": "medium", "evidence_refs": [ref(2)]},
            {"node_id": "event:culture", "label": "Cultural Significance of Float Goats",
             "node_type": "event", "description": "Source-backed culture passage.",
             "importance": "medium", "evidence_refs": [ref(6)]},
            {"node_id": "event:festival", "label": "Festival of Expansion",
             "node_type": "event", "description": "A recurring festival.",
             "importance": "medium", "evidence_refs": [ref(8)]},
        ]},
        "edge_pass": {"observation_edges": [
            {"edge_id": "edge:goats", "from_node_id": "event:goats",
             "to_node_id": "place:exampleland", "relationship_type": "located_in",
             "predicate_family": "spatial", "label": "", "evidence_refs": [ref(2)]},
            {"edge_id": "edge:festival", "from_node_id": "event:festival",
             "to_node_id": "place:exampleland", "relationship_type": "present_at",
             "label": "festival in place", "evidence_refs": [ref(8)]},
        ]},
        "edge_review_pass": {"retained_edge_ids": ["edge:festival"]},
    }

    class BoundedFixtureClient(BoundedRecapPassClient):
        def __init__(self):
            self.limits = SimpleNamespace(provider="openrouter", model=DEEPSEEK_MODEL, max_calls=8)
            self.fixture = FixtureCategoryGraphPassClient(outputs)
            self.calls = []
            self.prompts = []

        def run_pass(self, pass_name, **kwargs):
            self.calls.append({"pass_name": pass_name, "observation": None})
            self.prompts.append(kwargs["user_content"])
            if pass_name == "edge_review_pass":
                return {"parsed": outputs[pass_name], "raw_text": "fixture review",
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                        "cost_usd": 0.0, "cost_info": {}, "elapsed_ms": 0,
                        "response_id": "fixture-review"}
            return self.fixture.run_pass(pass_name, **kwargs)

    result = run_category_pipeline(
        BoundedFixtureClient(),
        CategoryGraphExtractionOptions(
            campaign_id="synthetic", session_id=None, session_number=None,
            source_text="\n".join(texts), source_artifact_id="artifact:synthetic",
            source_span_index={"source_artifact_id": "artifact:synthetic",
                               "source_ref_id": "artifact:synthetic:text", "spans": rows},
            model_id=DEEPSEEK_MODEL,
            profile=GAZETTEER_LIVESTOCK_HYGIENE_PROFILE,
            enable_party_claimed_fill=False,
        ),
    )
    graph = result.candidate_graph
    node_ids = {node["node_id"] for node in graph["nodes"]}
    assert "event:goats" not in node_ids and "event:culture" not in node_ids
    assert "event:festival" in node_ids
    assert len(graph["deferred_items"]) == 3
    assert [edge["edge_id"] for edge in graph["edges"]] == ["edge:festival"]
    place = next(node for node in graph["nodes"] if node["node_id"] == "place:exampleland")
    assert "Float Goats walk on water" in place["description"]
    assert all(ref.get("source_artifact_id") == "artifact:synthetic"
               for ref in place["evidence_refs"])
    span_ids = {row["source_span_ref_id"] for row in rows}
    evidence_refs = [
        ref
        for collection in ("nodes", "edges", "deferred_items", "ignored_items")
        for item in graph.get(collection, [])
        for ref in item.get("evidence_refs", [])
    ]
    assert evidence_refs
    assert all(ref.get("source_span_ref_id") in span_ids for ref in evidence_refs)
    persisted_edge = result.consolidation_diagnostics["source_section_retention"][
        "livestock_semantic_hygiene"]["deferred_proposals"][
            "deferred:livestock-section:edge:edge:goats"]["proposal"]
    assert persisted_edge["label"] == ""
    assert persisted_edge["relationship_type"] == "located_in"
    assert persisted_edge["from_node_id"] == "event:goats"
    assert persisted_edge["to_node_id"] == "place:exampleland"
    assert persisted_edge["evidence_refs"][0]["source_artifact_id"] == "artifact:synthetic"
    assert persisted_edge["evidence_refs"][0]["source_ref_id"] == "artifact:synthetic:text"


def test_v16_profile_is_versioned_from_15_and_keeps_named_event_policy():
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
        GAZETTEER_CONSTRAINED_REVIEW_PROFILE,
    )

    v15 = GAZETTEER_CONSTRAINED_REVIEW_PROFILE
    v16 = GAZETTEER_LIVESTOCK_HYGIENE_PROFILE
    v16_definition = next(p for p in v16.node_passes if p.pass_id == "definition_pass")
    assert v15.profile_version == "1.5"
    assert v15.source_section_retainer.__name__ == "compile_role_support"
    assert v16.profile_version == "1.6"
    assert v16.source_section_retainer.__name__ == "compile_gazetteer_livestock_hygiene"
    assert "not an event" in v16_definition.instruction
    assert "recurring festivals" in v16_definition.instruction
    assert v16.edge_review_pass == v15.edge_review_pass


def test_v17_profile_preserves_v16_prompts_and_only_changes_source_retention():
    v16 = GAZETTEER_LIVESTOCK_HYGIENE_PROFILE
    v17 = GAZETTEER_ROLE_CITATION_PROFILE
    assert v16.profile_version == "1.6"
    assert v16.source_section_retainer.__name__ == "compile_gazetteer_livestock_hygiene"
    assert v17.profile_version == "1.7"
    assert v17.node_passes == v16.node_passes
    assert v17.edge_pass == v16.edge_pass
    assert v17.edge_review_pass == v16.edge_review_pass
    assert v17.source_section_retainer is compile_gazetteer_role_citations


def test_v17_adds_only_unambiguous_affirmed_exact_role_line_citations():
    rows = [
        {"source_span_ref_id": "span:role", "line_start": 1, "line_end": 1,
         "text": "**Role:** Representative of Commerce"},
        {"source_span_ref_id": "span:negated", "line_start": 2, "line_end": 2,
         "text": "Role: Representative of Arcane"},
        {"source_span_ref_id": "span:ambiguous", "line_start": 3, "line_end": 3,
         "text": "Role: Representative of the Guilds"},
    ]
    graph = {
        "session_id": None,
        "beats": [],
        "source_artifact_ids": ["artifact:synthetic"],
        "nodes": [
            {"node_id": "npc:nera", "label": "Nera", "node_type": "character",
             "description": "Nera is a Representative of Commerce.",
             "evidence_refs": [{"source_span_ref_id": "span:name"}]},
            {"node_id": "npc:aric", "label": "Aric", "node_type": "character",
             "description": "Aric is not a Representative of Arcane.",
             "evidence_refs": []},
            {"node_id": "npc:beren", "label": "Beren", "node_type": "character",
             "description": "Beren is a Representative of the Guilds.",
             "evidence_refs": []},
            {"node_id": "npc:beren-two", "label": "Beren Two", "node_type": "character",
             "description": "Also a Representative of the Guilds.",
             "evidence_refs": []},
        ],
        "edges": [],
        "deferred_items": [],
    }
    original_semantics = [
        (node["node_id"], node["label"], node["node_type"], node["description"])
        for node in graph["nodes"]
    ]

    result, diagnostics = compile_gazetteer_role_citations(graph, rows)

    nera = next(node for node in result["nodes"] if node["node_id"] == "npc:nera")
    assert nera["description"] == "Nera is a Representative of Commerce."
    assert nera["evidence_refs"] == [
        {"source_span_ref_id": "span:name"},
        {"source_span_ref_id": "span:role",
         "anchor_quotes": ["**Role:** Representative of Commerce"]},
    ]
    assert all(
        not any(ref.get("source_span_ref_id") in {"span:negated", "span:ambiguous"}
                for ref in node.get("evidence_refs", []))
        for node in result["nodes"]
    )
    assert [
        (node["node_id"], node["label"], node["node_type"], node["description"])
        for node in result["nodes"]
    ] == original_semantics
    assert diagnostics["role_line_citations"]["records"] == [
        {"source_span_ref_id": "span:role", "candidate_node_id": "npc:nera",
         "decision": "citation_added"},
        {"source_span_ref_id": "span:negated",
         "decision": "no_matching_character_claim"},
        {"source_span_ref_id": "span:ambiguous",
         "decision": "ambiguous_character_match"},
    ]


@pytest.mark.parametrize("description, expected_added", [
    ('Nera is not currently a Representative of Commerce.', False),
    ('Nera is not currently serving in the role of Representative of Commerce.', False),
    ('Nera may become a Representative of Commerce.', False),
    ('Nera might become the Representative of Commerce.', False),
    ('Nera would be the Representative of Commerce.', False),
    ('If appointed, Nera is the Representative of Commerce.', False),
    ('Nera is the Representative of Commerce if appointed.', False),
    ('Nera is the Representative of Commerce unless the council objects.', False),
    ('Nera is the Representative of Commerce, subject to council approval.', False),
    ('Nera is the Representative of Commerce and might retire next year.', True),
    ('May is the Representative of Commerce.', True),
    ('Will is the Representative of Commerce.', True),
    ('Nera might retire. Nera is the Representative of Commerce.', True),
    ('Nera is not only a Representative of Commerce but also a merchant.', True),
])
def test_v17_role_citations_respect_claim_qualifiers(description, expected_added):
    rows = [{
        "source_span_ref_id": "span:role",
        "line_start": 1,
        "line_end": 1,
        "text": "Role: Representative of Commerce",
    }]
    graph = {
        "session_id": None,
        "beats": [],
        "source_artifact_ids": ["artifact:synthetic"],
        "nodes": [{
            "node_id": "npc:nera",
            "label": "Nera",
            "node_type": "character",
            "description": description,
            "evidence_refs": [],
        }],
        "edges": [],
        "deferred_items": [],
    }

    result, diagnostics = compile_gazetteer_role_citations(graph, rows)

    refs = result["nodes"][0]["evidence_refs"]
    assert bool(refs) is expected_added
    record = diagnostics["role_line_citations"]["records"][0]
    assert record["decision"] == ("citation_added" if expected_added else "no_matching_character_claim")
    if expected_added:
        assert refs == [{"source_span_ref_id": "span:role", "anchor_quotes": [rows[0]["text"]]}]


def test_v17_role_citation_does_not_duplicate_an_existing_reference():
    rows = [{
        "source_span_ref_id": "span:role", "line_start": 1, "line_end": 1,
        "text": "Role: Representative of Commerce",
    }]
    graph = {
        "session_id": None,
        "beats": [],
        "nodes": [{"node_id": "npc:nera", "label": "Nera", "node_type": "character",
                   "description": "Representative of Commerce.",
                   "evidence_refs": [{"source_span_ref_id": "span:role",
                                      "anchor_quotes": [rows[0]["text"]]}]}],
        "edges": [],
        "deferred_items": [],
    }
    result, diagnostics = compile_gazetteer_role_citations(graph, rows)
    assert result["nodes"][0]["evidence_refs"] == graph["nodes"][0]["evidence_refs"]
    assert diagnostics["role_line_citations"]["records"] == [
        {"source_span_ref_id": "span:role", "decision": "already_cited"},
    ]


def test_v17_real_category_pipeline_adds_source_stamped_role_citations():
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        FixtureCategoryGraphPassClient,
        run_category_pipeline,
    )
    from types import SimpleNamespace
    from src.graph_memory.extraction.bounded_recap_execution import (
        BoundedRecapPassClient,
        DEEPSEEK_MODEL,
    )

    texts = [
        "**Nera** — A representative.",
        "**Role:** Representative of Commerce",
        "**Aric** — A cautious official.",
        "**Role:** Representative of Arcane",
    ]
    rows = [{
        "source_span_ref_id": f"span:{index + 1}",
        "line_start": index + 1,
        "line_end": index + 1,
        "text": text,
    } for index, text in enumerate(texts)]
    outputs = {
        "actor_pass": {"observation_nodes": [
            {"node_id": "npc:nera", "label": "Nera", "node_type": "character",
             "description": "Representative of Commerce.", "importance": "medium",
             "evidence_refs": [{"source_span_ref_id": "span:1",
                                "anchor_quotes": [texts[0]]}]},
            {"node_id": "npc:aric", "label": "Aric", "node_type": "character",
             "description": "Not a Representative of Arcane.", "importance": "medium",
             "evidence_refs": [{"source_span_ref_id": "span:3",
                                "anchor_quotes": [texts[2]]}]},
        ]},
    }
    artifact_id = "artifact:synthetic"
    class BoundedFixtureClient(BoundedRecapPassClient):
        def __init__(self):
            self.limits = SimpleNamespace(provider="openrouter", model=DEEPSEEK_MODEL, max_calls=8)
            self.fixture = FixtureCategoryGraphPassClient(outputs)
            self.calls = []

        def run_pass(self, pass_name, **kwargs):
            self.calls.append({
                "pass_name": pass_name,
                "external_outcome": "not_started",
                "observation": None,
                "attempt_evidence": [],
            })
            return self.fixture.run_pass(pass_name, **kwargs)

    def run(profile):
        return run_category_pipeline(
            BoundedFixtureClient(),
            CategoryGraphExtractionOptions(
                campaign_id="synthetic",
                session_id=None,
                session_number=None,
                source_text="\n".join(texts),
                source_artifact_id=artifact_id,
                source_span_index={
                    "source_artifact_id": artifact_id,
                    "source_ref_id": f"{artifact_id}:text",
                    "spans": rows,
                },
                model_id=DEEPSEEK_MODEL,
                profile=profile,
                enable_party_claimed_fill=False,
            ),
        )

    baseline = run(GAZETTEER_LIVESTOCK_HYGIENE_PROFILE)
    result = run(GAZETTEER_ROLE_CITATION_PROFILE)
    baseline_graph = baseline.candidate_graph
    result_graph = result.candidate_graph
    assert [
        {key: value for key, value in node.items() if key != "evidence_refs"}
        for node in result_graph["nodes"]
    ] == [
        {key: value for key, value in node.items() if key != "evidence_refs"}
        for node in baseline_graph["nodes"]
    ]
    assert result_graph["edges"] == baseline_graph["edges"]
    assert result_graph["beats"] == baseline_graph["beats"]

    nodes = {node["node_id"]: node for node in result_graph["nodes"]}
    nera = nodes["npc:nera"]
    assert nera["description"] == "Representative of Commerce."
    assert any(
        ref.get("source_span_ref_id") == "span:2"
        and ref.get("anchor_quotes") == [texts[1]]
        and ref.get("source_artifact_id") == artifact_id
        and ref.get("source_ref_id") == f"{artifact_id}:text"
        for ref in nera["evidence_refs"]
    )
    aric = nodes["npc:aric"]
    assert all(ref.get("source_span_ref_id") != "span:4" for ref in aric["evidence_refs"])
    assert result.consolidation_diagnostics["source_section_retention"]["role_line_citations"]["profile"] == "worldbuilding_gazetteer_v1@1.7"


@pytest.mark.parametrize("kind", ["creature", "event"])
def test_named_definitions_are_admitted_with_source_evidence(kind):
    assert not validate_gazetteer_candidate_bounds({"session_id": None, "nodes": [
        {"node_type": kind, "evidence_refs": [{"source_span_ref_id": "span", "anchor_quotes": ["source"]}]}]})


@pytest.mark.parametrize("graph", [
    {"session_id": "session-1"}, {"nodes": [{"node_type": "item", "evidence_refs": [{}]}]},
    {"nodes": [{"node_type": "creature", "evidence_refs": []}]}, {"beats": [{}]},
])
def test_out_of_scope_or_unsupported_candidates_reject(graph):
    assert validate_gazetteer_candidate_bounds(graph)


def test_actual_pipeline_preserves_named_definition_and_source_qualification():
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions, FixtureCategoryGraphPassClient, run_category_pipeline,
    )
    body = "Float Goats are a livestock kind used to transport goods across water. The Renewal Fair is a recurring festival; locals believe it honors a goddess. A proposed hook has not occurred."
    ref = {"source_span_ref_id": "span-1", "anchor_quotes": [body]}
    client = FixtureCategoryGraphPassClient({"location_pass": {"observation_nodes": [
        {"node_id": "location:region", "node_type": "location", "label": "Elderwyld",
         "description": "Float Goats are a livestock kind used to transport goods across water.",
         "importance": "medium", "evidence_refs": [ref]}]}, "definition_pass": {"observation_nodes": [
        {"node_id": "definition:fair", "node_type": "event", "label": "Renewal Fair",
         "description": "A recurring festival; locals believe it honors a goddess.",
         "importance": "medium", "evidence_refs": [ref]},
    ]}})
    result = run_category_pipeline(client, CategoryGraphExtractionOptions(
        campaign_id="synthetic", session_id=None, session_number=None, source_text=body,
        source_artifact_id="artifact:synthetic", source_span_index={
            "source_artifact_id": "artifact:synthetic", "source_ref_id": "artifact:synthetic:text",
            "spans": [{"source_span_ref_id": "span-1", "span_id": "span-1",
                       "line_start": 1, "line_end": 1, "text": body}]},
        profile=GAZETTEER_PROFILE, enable_party_claimed_fill=False))
    graph = result.candidate_graph
    assert len(graph["nodes"]) == 2
    assert not any(node["node_type"] == "creature" for node in graph["nodes"])
    assert any("Float Goats" in node["description"] for node in graph["nodes"])
    assert not graph["beats"]
    assert graph["session_id"] is None
    assert any("locals believe" in node["description"] for node in graph["nodes"])
    assert all(node["semantic_state"]["canon_state"] == "worldbuilding_draft" for node in graph["nodes"])
    assert not validate_gazetteer_candidate_bounds(graph)
    from tests.test_cutover_worldbuilding_authority_port import _memory_context, _plan_kwargs
    from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
    from graph_memory.worldbuilding_write_plan import build_worldbuilding_write_plan, materialize_worldbuilding_contribution
    kwargs = _plan_kwargs(_memory_context())
    kwargs.update(preview=candidate_graph_preview_from_dict(graph),
        source_artifact_id="artifact:synthetic", campaign_scope="synthetic", extraction_profile="worldbuilding_gazetteer_v1@1.0",
        dispositions=[{"assertion_id": node["node_id"], "decision": "create_new"} for node in graph["nodes"]])
    plan = build_worldbuilding_write_plan(**kwargs)
    contribution = materialize_worldbuilding_contribution(world_id=plan.world_id,
                                                         plan_digest=plan.plan_digest, effect=plan.effect)
    assert contribution.accepted_assertions
    assert "locals believe" in repr(contribution)
    assert "Float Goats" in repr(contribution)


@pytest.mark.parametrize("version", ["1.0", "1.1", "1.2", "1.3"])
def test_registered_gazetteer_run_retains_exact_profile_and_typed_definitions(tmp_path, application_state_dsn, version):
    from tests.test_graph_preview_runner import _admit_worldbuilding, FixtureClient, _first_paragraph_span_id
    from src.graph_memory.extraction.graph_preview_runner import ProductionExtractionRequest, run_production_extraction
    from apps.live_control_server.services.graph_run_registry import get_reviewable_extraction_run
    from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
    source = _admit_worldbuilding(tmp_path, "Mirathorn is a river city.\n")
    result = run_production_extraction(ProductionExtractionRequest(
        repo_root=tmp_path, source=source, profile_id=GAZETTEER_PROFILE.profile_id,
        profile_version=version, allow_llm=True,
        category_client=FixtureClient(span_ref=_first_paragraph_span_id(source)),
        output_dir=tmp_path / "gazetteer-run"))
    assert result.failure_kind is None
    assert "raw_model_response" not in result.run.components
    run = get_reviewable_extraction_run(tmp_path, result.run.run_id)
    assert run.profile_id == "worldbuilding_gazetteer_v1@" + version
    assert run.session_id is None
    preview = candidate_graph_preview_from_dict(result.candidate_graph)
    assert preview.session_id is None
    assert run.components["source_artifact"].uri.endswith("/source.md")


def test_native_write_plan_retains_gazetteer_profile_and_rejects_unknown_version():
    from tests.test_cutover_worldbuilding_authority_port import _memory_context, _plan_kwargs
    from graph_memory.worldbuilding_write_plan import build_worldbuilding_write_plan, WorldbuildingWritePlanError
    kwargs = _plan_kwargs(_memory_context())
    kwargs["extraction_profile"] = "worldbuilding_gazetteer_v1@1.0"
    plan = build_worldbuilding_write_plan(**kwargs)
    assert plan.extraction_profile == "worldbuilding_gazetteer_v1@1.0"
    assert plan.effect["contribution_meta"]["extraction_profile"] == "worldbuilding_gazetteer_v1@1.0"
    kwargs["extraction_profile"] = "worldbuilding_gazetteer_v1@2.0"
    with pytest.raises(WorldbuildingWritePlanError) as error:
        build_worldbuilding_write_plan(**kwargs)
    assert error.value.code == "unsupported_worldbuilding_profile"


def test_gazetteer_is_not_admitted_to_pilot_only_bootstrap():
    from types import SimpleNamespace
    from apps.live_control_server.services.extract_promote import (
        _load_typed_worldbuilding_preview_for_run, ExtractPromoteError,
    )
    resolved = SimpleNamespace(source_domain="worldbuilding", extraction_profile="worldbuilding_gazetteer_v1@1.0")
    with pytest.raises(ExtractPromoteError) as error:
        _load_typed_worldbuilding_preview_for_run(resolved, allow_gazetteer=False)
    assert error.value.code == "unsupported_worldbuilding_profile"


def test_gazetteer_plan_cannot_be_verified_as_pilot():
    from tests.test_cutover_worldbuilding_authority_port import _memory_context, _plan_kwargs, _wrap_built_plan
    from graph_memory.worldbuilding_write_plan import (
        build_worldbuilding_write_plan, verify_worldbuilding_write_plan,
        WorldbuildingWritePlanVerificationContext, WorldbuildingWritePlanError,
    )
    context = _memory_context()
    kwargs = _plan_kwargs(context)
    kwargs["extraction_profile"] = "worldbuilding_gazetteer_v1@1.0"
    plan = build_worldbuilding_write_plan(**kwargs)
    verification = WorldbuildingWritePlanVerificationContext(
        world_id=kwargs["world_id"], parent_revision_id=kwargs["expected_parent_revision_id"],
        run_id=kwargs["run_id"], source_artifact_id=kwargs["source_artifact_id"],
        source_revision_id=kwargs["source_revision_id"], source_uri=kwargs["source_uri"],
        extraction_profile="worldbuilding_shepherds_flock_v0@0.1", campaign_scope=kwargs["campaign_scope"])
    with pytest.raises(WorldbuildingWritePlanError):
        verify_worldbuilding_write_plan(_wrap_built_plan(plan).model_dump(mode="json", by_alias=True),
            preview=kwargs["preview"], mutation_context=context, context=verification)



def test_fidelity_profile_is_versioned_and_preserves_source_retention_contract():
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
        GAZETTEER_SOURCE_FIDELITY_PROFILE, GAZETTEER_SOURCE_RETENTION_PROFILE,
    )
    assert GAZETTEER_SOURCE_FIDELITY_PROFILE.source_section_retainer is (
        GAZETTEER_SOURCE_RETENTION_PROFILE.source_section_retainer
    )
    assert GAZETTEER_SOURCE_FIDELITY_PROFILE.edge_pass == GAZETTEER_SOURCE_RETENTION_PROFILE.edge_pass
    assert GAZETTEER_SOURCE_FIDELITY_PROFILE.default_semantic_state == GAZETTEER_PROFILE.default_semantic_state
    assert GAZETTEER_SOURCE_RETENTION_PROFILE.profile_version == "1.1"
    assert GAZETTEER_PROFILE.profile_version == "1.0"


def test_role_support_versions_differ_only_in_owned_pipeline_disposition():
    from copy import deepcopy
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
        GAZETTEER_SOURCE_FIDELITY_PROFILE,
        GAZETTEER_ROLE_SUPPORT_PROFILE,
    )
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        FixtureCategoryGraphPassClient,
        run_category_pipeline,
    )
    from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict

    texts = ["Nera — Proprietor of the Silver Inn", "Pippa — Owner of the Copper Inn"]
    refs = [
        {"source_span_ref_id": f"span-{i}", "anchor_quotes": [t]}
        for i, t in enumerate(texts)
    ]
    outputs = {
        "actor_pass": {
            "observation_nodes": [
                {
                    "node_id": "npc:nera",
                    "node_type": "character",
                    "label": "Nera",
                    "description": texts[0],
                    "evidence_refs": [refs[0]],
                },
                {
                    "node_id": "npc:pippa",
                    "node_type": "character",
                    "label": "Pippa",
                    "description": texts[1],
                    "evidence_refs": [refs[1]],
                },
            ]
        },
        "location_pass": {
            "observation_nodes": [
                {
                    "node_id": "loc:silver",
                    "node_type": "location",
                    "label": "Silver Inn",
                    "description": texts[0],
                    "evidence_refs": [refs[0]],
                },
                {
                    "node_id": "loc:copper",
                    "node_type": "location",
                    "label": "Copper Inn",
                    "description": texts[1],
                    "evidence_refs": [refs[1]],
                },
            ]
        },
        "edge_pass": {
            "observation_edges": [
                {
                    "edge_id": "edge:role",
                    "from_node_id": "npc:nera",
                    "to_node_id": "loc:silver",
                    "relationship_type": "owns",
                    "label": "Nera owns Silver Inn",
                    "evidence_refs": [refs[0]],
                },
                {
                    "edge_id": "edge:owner",
                    "from_node_id": "npc:pippa",
                    "to_node_id": "loc:copper",
                    "relationship_type": "owns",
                    "label": "Pippa owns Copper Inn",
                    "evidence_refs": [refs[1]],
                },
            ]
        },
    }
    original = deepcopy(outputs)
    results = []
    for profile in (GAZETTEER_SOURCE_FIDELITY_PROFILE, GAZETTEER_ROLE_SUPPORT_PROFILE):
        result = run_category_pipeline(
            FixtureCategoryGraphPassClient(deepcopy(outputs)),
            CategoryGraphExtractionOptions(
                campaign_id="synthetic",
                session_id=None,
                session_number=None,
                source_text="\n".join(texts),
                source_artifact_id="artifact:synthetic",
                source_span_index={
                    "source_artifact_id": "artifact:synthetic",
                    "source_ref_id": "artifact:synthetic:text",
                    "spans": [
                        {
                            "source_span_ref_id": f"span-{i}",
                            "span_id": f"span-{i}",
                            "line_start": i + 1,
                            "line_end": i + 1,
                            "text": t,
                        }
                        for i, t in enumerate(texts)
                    ],
                },
                profile=profile,
                enable_party_claimed_fill=False,
            ),
        )
        results.append(result)
    old, new = [r.candidate_graph for r in results]
    assert {e["edge_id"] for e in old["edges"]} == {"edge:role", "edge:owner"}
    assert {e["edge_id"] for e in new["edges"]} == {"edge:owner"}
    assert new["nodes"] == old["nodes"] and outputs == original
    item = candidate_graph_preview_from_dict(new).deferred_items[0]
    assert (
        item.reason == "proprietor_role_not_ownership_assertion" and item.evidence_refs
    )
    assert item.evidence_refs[0].source_artifact_id == "artifact:synthetic"
    assert item.evidence_refs[0].anchor_quotes == (texts[0],)
    assert GAZETTEER_SOURCE_FIDELITY_PROFILE.profile_version == "1.2"
    assert (
        GAZETTEER_ROLE_SUPPORT_PROFILE.node_passes
        == GAZETTEER_SOURCE_FIDELITY_PROFILE.node_passes
    )


def test_registered_role_support_run_preserves_source_and_deferred_evidence(
    tmp_path, application_state_dsn
):
    from tests.test_graph_preview_runner import (
        _admit_worldbuilding,
        _first_paragraph_span_id,
    )
    from src.graph_memory.extraction.graph_preview_runner import (
        ProductionExtractionRequest,
        run_production_extraction,
    )
    from apps.live_control_server.services.graph_run_registry import (
        get_reviewable_extraction_run,
    )
    from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict

    source = _admit_worldbuilding(tmp_path, "Nera — Proprietor of the Silver Inn\n")
    span = _first_paragraph_span_id(source)
    ref = {
        "source_span_ref_id": span,
        "anchor_quotes": ["Nera — Proprietor of the Silver Inn"],
    }

    class Client:
        def run_pass(self, pass_name, **kwargs):
            nodes = []
            edges = []
            if pass_name == "actor_pass":
                nodes = [
                    {
                        "node_id": "npc:nera",
                        "node_type": "character",
                        "label": "Nera",
                        "description": "Nera — Proprietor of the Silver Inn",
                        "evidence_refs": [ref],
                    }
                ]
            if pass_name == "location_pass":
                nodes = [
                    {
                        "node_id": "loc:silver",
                        "node_type": "location",
                        "label": "Silver Inn",
                        "description": "Nera — Proprietor of the Silver Inn",
                        "evidence_refs": [ref],
                    }
                ]
            if pass_name == "edge_pass":
                edges = [
                    {
                        "edge_id": "edge:role",
                        "from_node_id": "npc:nera",
                        "to_node_id": "loc:silver",
                        "relationship_type": "owns",
                        "label": "Nera owns Silver Inn",
                        "evidence_refs": [ref],
                    }
                ]
            return {
                "parsed": {"observation_edges": edges}
                if pass_name == "edge_pass"
                else {"observation_nodes": nodes},
                "usage": {},
                "cost_usd": 0.0,
                "elapsed_ms": 1,
                "response_id": "fixture:" + pass_name,
            }

    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id="worldbuilding_gazetteer_v1",
            profile_version="1.3",
            allow_llm=True,
            category_client=Client(),
            output_dir=tmp_path / "role-run",
        )
    )
    assert result.failure_kind is None
    run = get_reviewable_extraction_run(tmp_path, result.run.run_id)
    assert run.profile_id == "worldbuilding_gazetteer_v1@1.3"
    preview = candidate_graph_preview_from_dict(result.candidate_graph)
    assert (
        len(preview.nodes) == 2
        and not preview.edges
        and len(preview.deferred_items) == 1
    )
    assert preview.deferred_items[0].reason == "proprietor_role_not_ownership_assertion"
    assert preview.deferred_items[0].evidence_refs[0].anchor_quotes == (
        "Nera — Proprietor of the Silver Inn",
    )
    source_file = tmp_path / run.components["source_artifact"].uri.removeprefix(
        "repo://"
    )
    assert source_file.read_text() == source.source_text
