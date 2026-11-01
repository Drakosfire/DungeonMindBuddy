"""Fresh source-only Recap generation never depends on a corpus directory."""
from tests.application_state.world_catalog_fixtures import store_world
import json
import pytest
from apps.live_control_server.services import graph_preview_runner as service
from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError, create_recap_source_artifact

def seed_binding(root, managed='managed-a', native='native-a', version=1):
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRecord, NativeGraphBindingRecord,
    )
    corpus = root / f'corpus/{managed}-markdown'
    corpus.mkdir(parents=True, exist_ok=True)
    record = WorldContainerRecord(
        world_id=managed, name=managed, source_root_relpath=f'corpus/{managed}-markdown', created_at='2026-01-01T00:00:00Z',
        native_graph_binding=NativeGraphBindingRecord(native_world_id=native,status='active',binding_version=version,
            validated_at='2026-01-01T00:00:00Z',validated_head_revision_id='rev:fixture'))
    store_world(record)
    return corpus


def seed_roster(corpus, label='Canonical'):
    folder=corpus/'Longmont Campaign/Campaign 2';folder.mkdir(parents=True,exist_ok=True)
    (folder/'_party_registry.json').write_text(json.dumps({'schema':'party_registry_v1','campaign_id':'longmont-c2',
        'pc_party_names':[label+' Company'],'session_pc_rosters':{'20':['hero']},'session_companion_rosters':{'20':['guide']}}))
    (folder/'_npc_registry.json').write_text(json.dumps({'npcs':[{'slug':'guide','aliases':[label+' alias']}]}))
    for kind,slug in [('PCs','hero'),('NPCs','guide')]:
        hub=folder/kind/slug/'README.md';hub.parent.mkdir(parents=True,exist_ok=True)
        hub.write_text(f'---\ntitle: {label} {slug}\n---\n# {label} {slug}\n')
    return folder



pytestmark = pytest.mark.usefixtures("application_state_dsn")

@pytest.mark.parametrize("roster", ["absent", "present", "malformed", "symlink", "mutated"])
@pytest.mark.parametrize("profile", ["category_baseline", "category_encounter_job_preview"])
def test_actual_registered_producer_does_not_read_or_inject_roster(tmp_path, monkeypatch, roster, profile):
    from graph_memory.ingestion.native_recap_source import SourceScope
    from tests.test_graph_preview_runner import FixtureClient, _first_paragraph_span_id
    root = tmp_path / "artifacts"
    root.mkdir()
    corpus = seed_binding(root)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(root))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(root))
    if roster in {"present", "mutated"}:
        seed_roster(corpus, "Poison")
    elif roster == "malformed":
        folder = corpus / "Longmont Campaign/Campaign 2"
        folder.mkdir(parents=True)
        (folder / "_party_registry.json").write_text("{broken")
    elif roster == "symlink":
        corpus.rmdir()
        external = tmp_path / "external"
        external.mkdir()
        seed_roster(external, "Poison")
        corpus.symlink_to(external, target_is_directory=True)
    else:
        corpus.rmdir()
    # Exact DB source exists independently of import files or directory discovery.
    text = "Mira guards the gate.\n"
    artifact = create_recap_source_artifact(root, world_id="native-a", campaign_id="longmont-c2", session_id="session-21", recap_text=text)
    span = _first_paragraph_span_id(service._normalized_from_registered(root, artifact.source_artifact_id))
    calls = []
    class Client(FixtureClient):
        def run_pass(self, name, **kw):
            calls.append((name, kw["user_content"]))
            assert "Poison" not in kw["user_content"]
            if roster == "mutated":
                (corpus / "Longmont Campaign/Campaign 2/_party_registry.json").write_text("{changed")
            answer = super().run_pass(name, **kw)
            if name == "actor_pass":
                answer["parsed"] = {"observation_nodes": [{"node_id":"candidate:mira", "label":"Mira", "node_type":"character", "description":"Guards the gate.", "importance":"medium", "corpus_ref":{"type":"pc","ref_id":"invented","resolution":"resolved"}, "evidence_refs":[{"source_span_ref_id":span,"anchor_quotes":["Mira guards the gate."]}]}]}
            elif name not in {"beat_pass", "edge_pass"}:
                answer["parsed"] = {"observation_nodes":[]}
            return answer
    result = service.run_recap_production_extraction(repo_root=root, campaign_id="longmont-c2", session_id="session-21", source_artifact_id=artifact.source_artifact_id,
        ingest_context=SourceScope(managed_world_id="managed-a", native_world_id="native-a", binding_version=1, campaign_id="longmont-c2"), category_client=Client(span_ref=span), profile=profile)
    assert result.failure_kind is None, result.diagnostics
    expected_profile = "recap_category_v2@2.0" if profile == "category_baseline" else "recap_category_encounter_job_preview@2.0"
    assert result.run.profile_id == expected_profile
    expected_calls = ["actor_pass","location_pass","collective_pass","object_pass","thread_pass","beat_pass"]
    if profile == "category_encounter_job_preview":
        expected_calls.append("encounter_job_pass")
    assert [name for name, _ in calls] == expected_calls + ["edge_pass"]
    graph = result.candidate_graph
    assert [node["node_id"] for node in graph["nodes"]] == ["candidate:mira"]
    mira = graph["nodes"][0]
    assert mira["node_type"] == "character" and mira.get("corpus_ref") is None
    assert mira["evidence_refs"][0]["anchor_quotes"] == ["Mira guards the gate."]
    assert graph["edges"] == []
    assert "known_entity_mentions" not in result.run.components
    assert "registry_context_graph" not in result.run.components
    assert not list(root.rglob("identity_context.json"))

@pytest.mark.parametrize("change", ["version", "native"])
def test_binding_drift_still_refuses_before_output_or_provider(tmp_path, monkeypatch, change):
    from graph_memory.ingestion.native_recap_source import SourceScope
    seed_binding(tmp_path)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    context = SourceScope(managed_world_id="managed-a", native_world_id="native-a", binding_version=1, campaign_id="longmont-c2")
    if change == "version":
        context = context.model_copy(update={"binding_version":2})
    else:
        context = context.model_copy(update={"native_world_id":"other"})
    artifact = create_recap_source_artifact(tmp_path, world_id=context.native_world_id, campaign_id="longmont-c2", session_id="session-21", recap_text="Mira guards the gate.\n")
    monkeypatch.setattr(service, "run_production_extraction", lambda *a, **kw: pytest.fail("must refuse before dispatch"))
    with pytest.raises(SourceArtifactRegistryError, match="binding changed"):
        service.run_recap_production_extraction(repo_root=tmp_path, campaign_id="longmont-c2", session_id="session-21", source_artifact_id=artifact.source_artifact_id, ingest_context=context, output_dir=tmp_path/"new-output")
    assert not (tmp_path/"new-output").exists()


def test_retired_profile_refuses_fresh_dispatch_without_provider_or_output(tmp_path, monkeypatch):
    from graph_memory.ingestion.native_recap_source import SourceScope
    from src.graph_memory.extraction.extraction_profile import UnknownExtractionProfileError
    seed_binding(tmp_path)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    source = create_recap_source_artifact(tmp_path, world_id="native-a", campaign_id="longmont-c2", session_id="session-21", recap_text="Mira guards the gate.\n")
    monkeypatch.setattr(service, "run_production_extraction", lambda *a, **kw: pytest.fail("must not execute retired profile"))
    with pytest.raises(UnknownExtractionProfileError):
        service.run_recap_production_extraction(repo_root=tmp_path, campaign_id="longmont-c2", session_id="session-21", source_artifact_id=source.source_artifact_id, ingest_context=SourceScope(managed_world_id="managed-a",native_world_id="native-a",binding_version=1,campaign_id="longmont-c2"),profile="recap_category_v1@1.0",output_dir=tmp_path/"new-output")
    assert not (tmp_path/"new-output").exists()

def test_direct_options_cannot_execute_a_retired_profile():
    from dataclasses import replace
    from src.graph_memory.extraction.category_candidate_graph_extractor import CategoryGraphExtractionOptions, CategoryGraphExtractionError, extract_category_candidate_graph
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
    class NoCalls:
        def run_pass(self,*a,**k):
            pytest.fail("must reject retired policy before inference")
    with pytest.raises(CategoryGraphExtractionError,match="Retired Recap"):
        extract_category_candidate_graph(CategoryGraphExtractionOptions(campaign_id="synthetic",session_id="session-1",session_number=1,source_span_index={},profile=replace(RECAP_EXTRACTION_PROFILE,profile_id="recap_category_v1",profile_version="1.0")),client=NoCalls())
