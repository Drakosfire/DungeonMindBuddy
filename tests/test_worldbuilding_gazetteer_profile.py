import pytest
from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
    GAZETTEER_PROFILE, validate_gazetteer_candidate_bounds,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import PUBLISHABLE_WORLDBUILDING_PROFILES


def test_closed_publication_profiles_preserve_pilot_and_exact_gazetteer_version():
    assert set(PUBLISHABLE_WORLDBUILDING_PROFILES) == {
        "worldbuilding_shepherds_flock_v0@0.1", "worldbuilding_gazetteer_v1@1.0",
        "worldbuilding_gazetteer_v1@1.1", "worldbuilding_gazetteer_v1@1.2", "worldbuilding_gazetteer_v1@1.3", "worldbuilding_gazetteer_v1@1.4", "worldbuilding_gazetteer_v1@1.5"}
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
