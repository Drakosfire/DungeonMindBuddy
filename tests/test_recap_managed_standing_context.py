"""Ordinary recap standing context follows managed source authority, never cwd."""
from tests.application_state.world_catalog_fixtures import store_world

from dataclasses import replace
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


@pytest.mark.parametrize('session', [20,21])
@pytest.mark.parametrize('separate_roots', [False, True])
def test_real_service_pipeline_uses_canonical_root_for_prompt_and_consolidation(tmp_path,monkeypatch,application_state_dsn,session,separate_roots):
    from apps.live_control_server.services.recap_ingest_context import RecapContextSnapshot
    from tests.test_graph_preview_runner import FixtureClient
    from src.graph_memory.extraction import category_candidate_graph_extractor as extractor
    root=tmp_path/'artifacts';root.mkdir()
    managed_root=tmp_path/'managed' if separate_roots else root
    corpus=seed_binding(managed_root);seed_roster(corpus)
    monkeypatch.setenv('DMB_MANAGED_WORLD_DATA_ROOT',str(managed_root))
    poison=tmp_path/'code/corpus/eldyrwild-markdown';seed_roster(poison,'Poison')
    monkeypatch.chdir(tmp_path/'code');monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(root))
    source=corpus/'recap.md';source.write_text('A keeper guards a gate.\n')
    managed_before={p.relative_to(managed_root):p.read_bytes() for p in managed_root.rglob('*') if p.is_file()}
    ctx=RecapContextSnapshot(schema='dm_world_campaign_ingest_context_v1',managed_world_id='managed-a',native_world_id='native-a',binding_version=1,
        campaign_id='longmont-c2',head_revision_id='rev:fixture',graph_schema='dm_graph_v1',graph_payload_sha256='a'*64)
    rendered=[];render=extractor.render_category_pass_prompts
    def prompts(*a,**kw):
        rendered.append(kw['known_entity_registry'])
        return render(*a,**kw)
    monkeypatch.setattr(extractor,'render_category_pass_prompts',prompts)
    captured=[];actual=extractor.consolidate_category_outputs
    def consolidate(*a,**kw):
        captured.append(kw['party_context'])
        return actual(*a,**kw)
    monkeypatch.setattr(extractor,'consolidate_category_outputs',consolidate)
    class Client(FixtureClient):
        def run_pass(self,name,**kw):
            assert 'Poison' not in kw['user_content']
            return super().run_pass(name,**kw)
    # Use actual source registration/production/options/loader/validators.
    artifact=create_recap_source_artifact(root,world_id='native-a',campaign_id='longmont-c2',session_id=f'session-{session}',recap_path=source)
    from tests.test_graph_preview_runner import _first_paragraph_span_id
    span=_first_paragraph_span_id(service._normalized_from_registered(root,artifact.source_artifact_id))
    result=service.run_recap_production_extraction(repo_root=root,campaign_id='longmont-c2',session_id=f'session-{session}',
        source_artifact_id=artifact.source_artifact_id,ingest_context=ctx,profile='category_baseline',category_client=Client(span_ref=span))
    assert result.failure_kind is None,result.diagnostics
    assert captured and all(party.party_names==('Canonical Company',) for party in captured)
    assert rendered and any('Canonical alias' in entity.aliases for entity in rendered[0].entities)
    snapshot=service._recap_identity_snapshot('longmont-c2',f'session-{session}',None,corpus_root=corpus)
    registry=snapshot['known_entity_registry']
    assert len(registry['entities'])==2
    assert any('Canonical alias' in e['aliases'] for e in registry['entities'])
    assert registry['roster_carry_forward']==(session==21)
    assert 'Poison' not in json.dumps(snapshot)
    if separate_roots:
        assert not (root/'corpus').exists()
        assert {p.relative_to(managed_root):p.read_bytes() for p in managed_root.rglob('*') if p.is_file()}==managed_before


@pytest.mark.parametrize('change', ['version','native','missing','symlink'])
@pytest.mark.parametrize('separate_roots', [False, True])
def test_authority_drift_refuses_before_source_or_output_or_provider(tmp_path,monkeypatch,change,separate_roots):
    from tests.test_bounded_recap_execution import _fixture_ingest_context
    root=tmp_path/'artifacts';root.mkdir()
    managed_root=tmp_path/'managed' if separate_roots else root
    corpus=seed_binding(managed_root,'managed-fixture-world','world:synthetic')
    monkeypatch.setenv('DMB_MANAGED_WORLD_DATA_ROOT',str(managed_root))
    ctx=_fixture_ingest_context('longmont-c2')
    if change=='version':ctx=replace(ctx,binding_version=2)
    elif change=='native':ctx=replace(ctx,native_world_id='other')
    elif change=='missing':corpus.rmdir()
    else:
        corpus.rmdir();external=tmp_path/'external';external.mkdir();corpus.symlink_to(external,target_is_directory=True)
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(root))
    artifact=create_recap_source_artifact(root,world_id='world:synthetic',campaign_id='longmont-c2',session_id='session-20',recap_text='Synthetic recap.\n')
    monkeypatch.setattr(service,'run_production_extraction',lambda *a,**k:pytest.fail('must not dispatch'))
    from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
    with pytest.raises((SourceArtifactRegistryError,WorldGraphProjectionServiceError)) as failure:
        service.run_recap_production_extraction(repo_root=root,campaign_id='longmont-c2',session_id='session-20',
            source_artifact_id=artifact.source_artifact_id,ingest_context=ctx,output_dir=root/'new-output')
    assert failure.value.status_code==409
    assert not (root/'new-output').exists()


def test_changed_snapshot_refuses_before_first_provider_call(tmp_path,monkeypatch,application_state_dsn):
    # Exercise actual options/loader gate directly with a deliberately stale hash.
    from src.graph_memory.extraction.category_candidate_graph_extractor import CategoryGraphExtractionOptions,extract_category_candidate_graph,CategoryGraphExtractionError
    root=tmp_path/'root';seed_roster(root)
    class NoCalls:
        def run_pass(self,*a,**k):pytest.fail('must not call provider')
    with pytest.raises(CategoryGraphExtractionError,match='Standing identity context changed'):
        extract_category_candidate_graph(CategoryGraphExtractionOptions(campaign_id='longmont-c2',session_id='session-20',session_number=20,
            source_span_index={'spans':[]},corpus_root=root,expected_standing_context_sha256='0'*64),client=NoCalls())


def test_service_snapshot_drift_refuses_before_dispatch(tmp_path,monkeypatch,application_state_dsn):
    from tests.test_bounded_recap_execution import _fixture_ingest_context
    root=tmp_path/'data';root.mkdir();corpus=seed_binding(root,'managed-fixture-world','world:synthetic');folder=seed_roster(corpus)
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(root))
    source=corpus/'recap.md';source.write_text('The guide opened the gate.\n')
    capture=service._recap_identity_snapshot
    def changed(*a,**kw):
        snapshot=capture(*a,**kw)
        (folder/'_npc_registry.json').write_text(json.dumps({'npcs':[{'slug':'guide','aliases':['Changed after capture']}]}))
        return snapshot
    monkeypatch.setattr(service,'_recap_identity_snapshot',changed)
    class NoCalls:
        def run_pass(self,*a,**kw):pytest.fail('must not call provider after context drift')
    result=service.run_recap_production_extraction(repo_root=root,campaign_id='longmont-c2',session_id='session-20',source_artifact_id=create_recap_source_artifact(root,world_id='world:synthetic',campaign_id='longmont-c2',session_id='session-20',recap_path=source).source_artifact_id,
        ingest_context=_fixture_ingest_context('longmont-c2'),profile='category_baseline',category_client=NoCalls())
    assert result.failure_kind=='extraction'
    assert any('Standing identity context changed' in message for message in result.diagnostics)
    assert 'candidate_graph' not in result.run.components


def test_non_recap_session_cannot_load_party_registry(tmp_path,monkeypatch):
    from src.graph_memory.extraction import category_candidate_graph_extractor as extractor
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import WORLDBUILDING_PLUMBING_PROFILE
    def forbidden(*a,**kw):pytest.fail('non-recap cannot load a party registry')
    monkeypatch.setattr(extractor,'build_party_context_for_campaign',forbidden)
    monkeypatch.setattr(extractor,'build_known_entity_registry',forbidden)
    class Empty:
        def run_pass(self,*a,**kw):
            return {'parsed':{'observation_nodes':[],'observation_edges':[],'observation_beats':[]},'raw_text':'{}','usage':{},'cost_usd':0.0,'elapsed_ms':0,'response_id':'synthetic'}
    result=extractor.extract_category_candidate_graph(extractor.CategoryGraphExtractionOptions(
        campaign_id='longmont-c2',session_id='session-20',session_number=20,source_span_index={'spans':[]},
        corpus_root=tmp_path,source_artifact_id='artifact:synthetic',source_ref_id='source:synthetic',profile=WORLDBUILDING_PLUMBING_PROFILE),client=Empty())
    assert result.consolidation_diagnostics['party_anchor_identity_keys']==[]


def test_missing_and_unconfigured_registries_remain_explicit(tmp_path):
    missing=service._recap_identity_snapshot('longmont-c2','session-20',None,corpus_root=tmp_path)
    unknown=service._recap_identity_snapshot('unconfigured','session-20',None,corpus_root=tmp_path)
    assert missing['known_entity_registry']['entities']==unknown['known_entity_registry']['entities']==()
    assert any('_party_registry.json' in warning for warning in missing['party_context']['warnings'])
    assert unknown['known_entity_registry']['warnings']==('no local corpus registered for campaign',)

pytestmark = pytest.mark.usefixtures("application_state_dsn")
