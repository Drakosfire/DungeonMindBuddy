"""Build Recap source identity through actual document/source/run owners."""
from tests.page_fixtures import create_page_fixture, save_page, page_text
from apps.live_control_server.services.workspace_document_registry import get_workspace_document
import hashlib
import json
from dataclasses import replace

import pytest

from apps.live_control_server.services import graph_preview_runner as runner
from apps.live_control_server.services.build_recap_source import register_build_recap_source, frozen_build_recap_configuration
from apps.live_control_server.services.recap_ingest_context import RecapContextSnapshot
from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError, load_registered_source_artifact_text, load_source_span_index

pytestmark = pytest.mark.usefixtures("application_state_dsn")

@pytest.fixture
def context():
    return RecapContextSnapshot(schema="dm_world_campaign_ingest_context_v1",managed_world_id="managed-a",native_world_id="native-a",binding_version=1,
        campaign_id="longmont-c2",head_revision_id="rev:1",graph_schema="dm_graph_v1",graph_payload_sha256="a"*64)

@pytest.fixture
def source(tmp_path,monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT",str(tmp_path))
    from tests.test_recap_managed_standing_context import seed_binding
    seed_binding(tmp_path)
    record=create_page_fixture(tmp_path,title="External recap",campaign_id="workspace-campaign",world_id="managed-a",kind="worldbuilding_source",
        source_domain="worldbuilding",document_class="lore",authority_state="draft",visibility_state="internal")
    text="Mirathorn’s party crossed the boardwalk.\n\nThey camped north of Mireward Reach.\n"
    record = save_page(tmp_path, record.document_id, text)
    record=get_workspace_document(tmp_path, record.document_id)
    return record,None,text,hashlib.sha256(text.encode()).hexdigest()

def register(tmp_path,source,context,**changes):
    record,_,_,digest=source
    args=dict(document_id=record.document_id,expected_revision=record.revision,expected_content_sha256=digest,session_id="session-30",ingest_context=context)
    args.update(changes)
    return register_build_recap_source(tmp_path,**args)


def test_freezes_exact_document_bytes_without_reinterpreting_document(tmp_path,source,context):
    record,target,text,digest=source;artifact=register(tmp_path,source,context)
    assert artifact.source_domain=="recap" and artifact.session_id=="session-30"
    assert artifact.campaign_id=="longmont-c2" and artifact.world_id=="native-a"
    assert artifact.workspace_document_id==record.document_id and artifact.workspace_document_revision==record.revision
    assert artifact.content_sha256==digest
    assert load_registered_source_artifact_text(tmp_path,artifact.source_artifact_id)[1]==text
    index=load_source_span_index(tmp_path,artifact.source_artifact_id)
    assert index.content_sha256==digest
    assert get_workspace_document(tmp_path,record.document_id).campaign_id=="workspace-campaign"
    assert get_workspace_document(tmp_path,record.document_id).source_domain=="worldbuilding"
    assert page_text(tmp_path, record.document_id)==text
    # Registry source remains immutable even when the editor later saves different text.
    save_page(tmp_path, record.document_id, "Newer editor text.\n")
    assert load_registered_source_artifact_text(tmp_path,artifact.source_artifact_id)[1]==text
    with pytest.raises(SourceArtifactRegistryError,match="revision changed"):
        register(tmp_path,source,context)


@pytest.mark.parametrize("change",[{"expected_revision":99},{"expected_content_sha256":"b"*64},{"session_id":"session-0"},{"session_id":"../session-30"},{"expected_revision":True},{"expected_content_sha256":"bad"}])
def test_rejects_bad_source_identity_before_registration(tmp_path,source,context,change):
    with pytest.raises(SourceArtifactRegistryError):register(tmp_path,source,context,**change)
    assert not (tmp_path/"out/registries/source_content/recap/build").exists()


def test_rejects_other_world_and_missing_verified_context(tmp_path,source,context):
    with pytest.raises(SourceArtifactRegistryError,match="another managed World"):
        register(tmp_path,source,replace(context,managed_world_id="managed-b"))
    with pytest.raises(SourceArtifactRegistryError,match="verified World/campaign"):
        register(tmp_path,source,None)
    assert not (tmp_path/"out/registries/source_content/recap/build").exists()


def test_same_document_is_idempotent_but_other_session_has_distinct_source(tmp_path,source,context):
    first=register(tmp_path,source,context)
    assert register(tmp_path,source,context).source_artifact_id==first.source_artifact_id
    second=register(tmp_path,source,context,session_id="session-31")
    assert second.source_artifact_id!=first.source_artifact_id
    assert second.content_sha256==first.content_sha256


def config(tmp_path,artifact,snapshot,**changes):
    args=dict(source_artifact_id=artifact.source_artifact_id,campaign_id="longmont-c2",session_id="session-30",context=snapshot.as_lineage(),
        profile_id="recap_category_v1",profile_version="1.0",supplemental_evidence=None)
    args.update(changes)
    return frozen_build_recap_configuration(tmp_path,**args)


def test_configuration_binds_document_source_session_profile_and_destination(tmp_path,source,context):
    artifact=register(tmp_path,source,context);frozen=config(tmp_path,artifact,context)
    canonical=json.dumps(frozen["configuration"],sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    assert frozen["configuration_sha256"]==hashlib.sha256(canonical).hexdigest()
    assert frozen["configuration"]["source"]["document_id"]==source[0].document_id
    assert config(tmp_path,artifact,context,profile_version="2.0")["configuration_sha256"]!=frozen["configuration_sha256"]
    for changes in ({"campaign_id":"other"},{"session_id":"session-31"},{"context":replace(context,native_world_id="native-b").as_lineage()},
                    {"context":replace(context,managed_world_id="managed-b").as_lineage()}):
        with pytest.raises(SourceArtifactRegistryError,match="does not match"):config(tmp_path,artifact,context,**changes)


def test_runner_uses_registered_build_source_and_retains_exact_lineage(tmp_path,source,context,monkeypatch):
    artifact=register(tmp_path,source,context)
    # Actual registered production run/validators, using the existing deterministic client.
    from tests.test_graph_preview_runner import FixtureClient, _first_paragraph_span_id
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    client=FixtureClient(span_ref=_first_paragraph_span_id(runner._normalized_from_registered(tmp_path,artifact.source_artifact_id)))
    result=runner.run_recap_production_extraction(repo_root=tmp_path,campaign_id="longmont-c2",session_id="session-30",
        source_artifact_id=artifact.source_artifact_id,allow_llm=True,category_client=client,profile="category_baseline",ingest_context=context,output_dir=tmp_path/"run")
    assert result.failure_kind is None
    assert result.run.status.value=="reviewable"
    assert get_extraction_run(tmp_path,result.run.run_id).lineage==result.run.lineage
    assert result.run.source_artifact_id==artifact.source_artifact_id
    # Build configuration belongs to Build launch, not the generic source runner.
    assert "build_document_ingest" not in result.run.lineage


def test_runner_rejects_retired_file_option_or_foreign_source_before_execution(tmp_path,source,context,monkeypatch):
    artifact=register(tmp_path,source,context)
    monkeypatch.setattr(runner,"run_production_extraction",lambda *a,**k:pytest.fail("must not execute"))
    args=dict(repo_root=tmp_path,campaign_id="longmont-c2",session_id="session-30",source_artifact_id=artifact.source_artifact_id,ingest_context=context)
    with pytest.raises(TypeError,match="recap_path"):
        runner.run_recap_production_extraction(**args,recap_path=tmp_path/"ambiguous-recap.md")
    with pytest.raises(SourceArtifactRegistryError,match="does not match"):
        runner.run_recap_production_extraction(**{**args,"session_id":"session-31"})


def test_equal_bytes_in_another_document_do_not_erase_provenance(tmp_path,source,context):
    original=register(tmp_path,source,context)
    other=create_page_fixture(tmp_path,title="Another recap",campaign_id="workspace-campaign",world_id="managed-a",kind="worldbuilding_source",
        source_domain="worldbuilding",document_class="lore",authority_state="draft",visibility_state="internal")
    pass;None;other = save_page(tmp_path, other.document_id, source[2])
    other=get_workspace_document(tmp_path, other.document_id)
    artifact=register(tmp_path,(other,None,source[2],source[3]),context)
    assert artifact.content_sha256==original.content_sha256
    assert artifact.source_artifact_id!=original.source_artifact_id
    assert artifact.workspace_document_id==other.document_id


@pytest.mark.parametrize("state",["draft","discarded"])
def test_rejects_unusable_document_before_registration(tmp_path,source,context,state):
    from apps.live_control_server.services.workspace_document_registry import discard_workspace_document
    record,target,_,_=source
    if state=="discarded":discard_workspace_document(tmp_path,record.document_id)
    else:
        draft=create_page_fixture(tmp_path,title="Draft",campaign_id="workspace-campaign",world_id="managed-a",kind="worldbuilding_source",
            source_domain="worldbuilding",document_class="lore",authority_state="draft",visibility_state="internal")
        source=(draft,target,source[2],source[3])
    with pytest.raises(SourceArtifactRegistryError):register(tmp_path,source,context)
    assert not (tmp_path/"out/registries/source_content/recap/build").exists()


def test_supplement_pins_are_frozen_separately_from_external_recap_source(tmp_path,source,context):
    artifact=register(tmp_path,source,context)
    bundle={"sha256":"b"*64,"sessions":[{"run_id":"run-1","review_revision":2,"sha256":"c"*64}]}
    first=config(tmp_path,artifact,context,supplemental_evidence=bundle)
    second=config(tmp_path,artifact,context,supplemental_evidence={"sha256":"d"*64,"sessions":[{"run_id":"run-1","review_revision":3,"sha256":"e"*64}]})
    assert first["configuration_sha256"]!=second["configuration_sha256"]
    assert first["configuration"]["source"]==second["configuration"]["source"]
    assert load_registered_source_artifact_text(tmp_path,artifact.source_artifact_id)[1]==source[2]


def test_build_sources_freeze_document_names_across_later_renames(tmp_path, source, context):
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document, get_source_artifact,
    )
    from apps.live_control_server.services.workspace_document_registry import update_workspace_document_metadata
    record, target, text, digest = source
    recap = register(tmp_path, source, context)
    worldbuilding = create_source_artifact_from_workspace_document(tmp_path,
        document_id=record.document_id, expected_revision=record.revision)
    for artifact in (recap, worldbuilding):
        assert artifact.lineage['source_name'] == record.title
    assert register(tmp_path, source, context) == recap
    renamed = update_workspace_document_metadata(tmp_path, record.document_id,
        title='The party reaches Willow Park', expected_revision=record.revision)
    for artifact in (recap, worldbuilding):
        assert get_source_artifact(tmp_path, artifact.source_artifact_id).lineage['source_name'] == record.title
    new_recap = register(tmp_path, (renamed, target, text, digest), context)
    new_worldbuilding = create_source_artifact_from_workspace_document(tmp_path,
        document_id=renamed.document_id, expected_revision=renamed.revision)
    assert new_recap.lineage['source_name'] == new_worldbuilding.lineage['source_name'] == renamed.title
    assert new_recap.source_artifact_id != recap.source_artifact_id
    assert new_worldbuilding.source_artifact_id != worldbuilding.source_artifact_id
    assert page_text(tmp_path, record.document_id) == text
