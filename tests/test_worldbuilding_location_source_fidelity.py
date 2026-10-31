"""Profile experiment wiring; response fidelity still requires the fresh benchmark."""

from dataclasses import fields
from src.graph_memory.extraction.bounded_recap_execution import (
    BoundedRecapPassClient,
    RecapExecutionLimits,
    DEEPSEEK_MODEL,
)

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    FixtureCategoryGraphPassClient,
)
from src.graph_memory.extraction.extraction_profile import require_admitted_profile
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.worldbuilding_location_source_fidelity import (
    GAZETTEER_LOCATION_SOURCE_FIDELITY_PROFILE as NEW,
)
from src.graph_memory.extraction.worldbuilding_collective_source_fidelity import (
    GAZETTEER_COLLECTIVE_SOURCE_FIDELITY_PROFILE as OLD,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import (
    PUBLISHABLE_WORLDBUILDING_PROFILES,
)
from tests import test_worldbuilding_profile_pipeline as fixture


def test_exact_new_profile_admission_preserves_old_identity():
    assert (
        require_admitted_profile(
            profile_id=NEW.profile_id,
            profile_version="1.13",
            source_domain="worldbuilding",
            document_class="gazetteer",
            session_id=None,
        )
        is NEW
    )
    assert PUBLISHABLE_WORLDBUILDING_PROFILES[OLD.qualified_id] is OLD
    assert PUBLISHABLE_WORLDBUILDING_PROFILES[NEW.qualified_id] is NEW
    assert OLD.profile_version == "1.12"


def test_experiment_changes_only_location_instruction():
    allowed = {"profile_version", "node_passes"}
    for field in fields(OLD):
        if field.name not in allowed:
            assert getattr(NEW, field.name) == getattr(OLD, field.name), field.name
    old = {p.pass_id: p for p in OLD.node_passes}
    for spec in NEW.node_passes:
        if spec.pass_id == "location_pass":
            assert spec.instruction.startswith(old[spec.pass_id].instruction)
        else:
            assert spec is old[spec.pass_id]
    assert NEW.edge_pass is OLD.edge_pass
    assert NEW.edge_review_pass is OLD.edge_review_pass
    assert NEW.source_section_retainer is OLD.source_section_retainer
    assert NEW.post_extraction_validator is OLD.post_extraction_validator


def test_actual_production_pipeline_dispatches_new_profile_without_provider(
    tmp_path, application_state_dsn
):
    source, span = fixture._admit_fixture_source(tmp_path)
    data = fixture._pass_outputs_for_span(fixture._load_fixture(), span)
    data["edge_review_pass"] = {"retained_edge_ids": []}
    dispatched = {}

    class Recorder(BoundedRecapPassClient):
        supports_actor_source_handles = False

        def __init__(self):
            super().__init__(
                RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL)
            )
            self.fixture = FixtureCategoryGraphPassClient(data)

        def run_pass(self, pass_name, **kwargs):
            dispatched[pass_name] = kwargs
            return self.fixture.run_pass(pass_name, **kwargs)

    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=NEW.profile_id,
            profile_version="1.13",
            allow_llm=True,
            category_client=Recorder(),
            model_id=DEEPSEEK_MODEL,
        )
    )
    assert result.failure_kind is None
    assert result.run.profile_id == NEW.qualified_id
    assert result.candidate_graph["session_id"] is None
    assert result.candidate_graph["version"] == "0.2"
    assert NEW.post_extraction_validator(result.candidate_graph) == []
    for spec in [
        next(p for p in NEW.node_passes if p.pass_id == "location_pass"),
    ]:
        call = dispatched[spec.pass_id]
        assert call["pass_spec"].instruction == spec.instruction
        assert (
            spec.instruction in call["user_content"]
            or spec.instruction in call["instructions"]
        )
