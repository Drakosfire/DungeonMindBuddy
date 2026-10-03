from pathlib import Path

import pytest

from apps.live_control_server.services import source_artifact_registry as registry


def test_configured_content_root_preserves_bytes_digest_uri_and_idempotency(tmp_path, monkeypatch):
    outside = tmp_path / "shared-output"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "out").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv(registry.RECAP_SOURCE_CONTENT_ROOT_ENV, ".dogfood/recap-source-content")
    source = repo / "original.md"
    original = "Session 29 recap\n\nRain intensifies.\n"
    source.write_text(original)
    artifact = registry.create_recap_source_artifact(repo, campaign_id="longmont-c2", session_id="session-29", recap_path=source)
    assert artifact.uri.startswith("repo://.dogfood/recap-source-content/longmont-c2/session-29/")
    artifact_again = registry.create_recap_source_artifact(repo, campaign_id="longmont-c2", session_id="session-29", recap_path=source)
    assert artifact_again.source_artifact_id == artifact.source_artifact_id
    assert artifact_again.uri == artifact.uri
    loaded, text = registry.load_registered_source_artifact_text(repo, artifact.source_artifact_id)
    assert text == original
    assert loaded.content_sha256 == artifact.content_sha256
    assert source.read_text() == original
    assert not (outside / "registries/source_content").exists()


@pytest.mark.parametrize("value", ["../escape", r"..\escape", "file:escape", "/absolute", "out/escape"])
def test_content_root_rejects_traversal_uri_absolute_and_symlink_escape(tmp_path, monkeypatch, value):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "out").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv(registry.RECAP_SOURCE_CONTENT_ROOT_ENV, value)
    with pytest.raises(registry.SourceArtifactRegistryError):
        registry.create_recap_source_artifact(repo, campaign_id="longmont-c2", session_id="session-29", recap_text="Recap\n")
    assert not list(outside.iterdir())


def test_default_content_root_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv(registry.RECAP_SOURCE_CONTENT_ROOT_ENV, raising=False)
    artifact = registry.create_recap_source_artifact(tmp_path, campaign_id="longmont-c2", session_id="session-29", recap_text="Recap\n")
    assert artifact.uri.startswith("repo://out/registries/source_content/recap/longmont-c2/session-29/")


def test_existing_locator_survives_configuration_change(tmp_path, monkeypatch):
    monkeypatch.delenv(registry.RECAP_SOURCE_CONTENT_ROOT_ENV, raising=False)
    original = registry.create_recap_source_artifact(tmp_path, campaign_id="longmont-c2", session_id="session-29", recap_text="Recap\n")
    monkeypatch.setenv(registry.RECAP_SOURCE_CONTENT_ROOT_ENV, ".dogfood/recap-content")
    repeated = registry.create_recap_source_artifact(tmp_path, campaign_id="longmont-c2", session_id="session-29", recap_text="Recap\n")
    assert repeated.uri == original.uri
    assert registry.load_registered_source_artifact_text(tmp_path, original.source_artifact_id)[1] == "Recap\n"


def test_configured_snapshot_collision_and_read_digest_mismatch_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv(registry.RECAP_SOURCE_CONTENT_ROOT_ENV, ".dogfood/recap-content")
    artifact = registry.create_recap_source_artifact(tmp_path, campaign_id="longmont-c2", session_id="session-29", recap_text="Recap\n")
    target = tmp_path / artifact.uri.removeprefix("repo://")
    target.write_text("Changed bytes\n")
    with pytest.raises(registry.SourceArtifactRegistryError, match="different bytes"):
        registry.create_recap_source_artifact(tmp_path, campaign_id="longmont-c2", session_id="session-29", recap_text="Recap\n")
    with pytest.raises(registry.SourceArtifactRegistryError, match="digest mismatch"):
        registry.load_registered_source_artifact_text(tmp_path, artifact.source_artifact_id)
    assert target.read_text() == "Changed bytes\n"
