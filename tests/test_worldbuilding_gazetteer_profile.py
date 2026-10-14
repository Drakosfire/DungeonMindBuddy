import pytest
from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
    GAZETTEER_PROFILE, validate_gazetteer_candidate_bounds,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import PUBLISHABLE_WORLDBUILDING_PROFILES


def test_closed_publication_profiles_preserve_pilot_and_exact_gazetteer_version():
    assert set(PUBLISHABLE_WORLDBUILDING_PROFILES) == {
        "worldbuilding_shepherds_flock_v0@0.1", "worldbuilding_gazetteer_v1@1.0"}
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


def test_registered_gazetteer_run_retains_exact_profile_and_typed_definitions(tmp_path, application_state_dsn):
    from tests.test_graph_preview_runner import _admit_worldbuilding, FixtureClient, _first_paragraph_span_id
    from src.graph_memory.extraction.graph_preview_runner import ProductionExtractionRequest, run_production_extraction
    from apps.live_control_server.services.graph_run_registry import get_reviewable_extraction_run
    from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
    source = _admit_worldbuilding(tmp_path, "Mirathorn is a river city.\n")
    result = run_production_extraction(ProductionExtractionRequest(
        repo_root=tmp_path, source=source, profile_id=GAZETTEER_PROFILE.profile_id,
        profile_version=GAZETTEER_PROFILE.profile_version, allow_llm=True,
        category_client=FixtureClient(span_ref=_first_paragraph_span_id(source)),
        output_dir=tmp_path / "gazetteer-run"))
    assert result.failure_kind is None
    run = get_reviewable_extraction_run(tmp_path, result.run.run_id)
    assert run.profile_id == "worldbuilding_gazetteer_v1@1.0"
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
