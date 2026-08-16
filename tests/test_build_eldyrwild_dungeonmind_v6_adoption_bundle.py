"""CLI --check/--write proofs for the Eldyrwild DungeonMind v6 adoption bundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.config import repo_root
from apps.live_control_server.integrations.dungeonmind_kernel import (
    eldyrwild_existing_world_adoption_bundle_v2 as producer,
)
from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
    BUNDLE_RELPATH,
    DUNGEONMIND_PIN,
)
from scripts.build_eldyrwild_dungeonmind_v6_adoption_bundle import main


def test_dungeonmind_pin_remains_history_replay_v2() -> None:
    text = (repo_root() / "pyproject.toml").read_text(encoding="utf-8")
    assert f"DungeonMind.git@{DUNGEONMIND_PIN}" in text


def test_check_without_artifact_fails(tmp_path: Path) -> None:
    with pytest.raises(producer.EldyrwildAdoptionBundleV2Error) as exc:
        producer.check_eldyrwild_existing_world_adoption_bundle_v2(repo=tmp_path)
    assert exc.value.code == "artifact_missing"


def test_failed_write_leaves_prior_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prior = tmp_path / BUNDLE_RELPATH
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior.write_text("prior-bytes\n", encoding="utf-8")

    def _boom(**_kwargs):
        raise producer.EldyrwildAdoptionBundleV2Error("no", code="forced")

    monkeypatch.setattr(producer, "build_eldyrwild_existing_world_adoption_bundle_v2", _boom)
    with pytest.raises(producer.EldyrwildAdoptionBundleV2Error):
        producer.write_eldyrwild_existing_world_adoption_bundle_v2(repo=tmp_path)
    assert prior.read_text(encoding="utf-8") == "prior-bytes\n"


def test_cli_requires_check_or_write() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_check_is_byte_identical_and_does_not_rewrite() -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (
        bundle_artifact_path,
        check_eldyrwild_existing_world_adoption_bundle_v2,
    )

    path = bundle_artifact_path()
    before = path.read_bytes()
    stat_before = path.stat()
    built = check_eldyrwild_existing_world_adoption_bundle_v2()
    assert path.read_bytes() == before == built.canonical_bytes
    assert path.stat().st_mtime_ns == stat_before.st_mtime_ns
    assert b'"schema_version":"dm_existing_world_adoption_bundle_v2"' in before
