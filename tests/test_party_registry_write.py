"""Tests for party registry session roster writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.services.party_registry_write import (
    PartyRegistrySessionRosterWriteCommitRequest,
    PartyRegistrySessionRosterWritePrepareRequest,
    PartyRegistryWriteConflictError,
    commit_party_registry_session_roster_write,
    prepare_party_registry_session_roster_write,
)
from src.graph_memory.party_context import PARTY_REGISTRY_BASENAME


@pytest.fixture
def isolated_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    campaign_rel = "Longmont Campaign/Campaign 2"
    campaign_dir = tmp_path / campaign_rel
    campaign_dir.mkdir(parents=True)
    registry = {
        "schema": "party_registry_v1",
        "campaign_id": "longmont-c2",
        "pc_party_names": ["Questionable Company"],
        "session_pc_rosters": {
            "22": ["stafl", "bonogo"],
        },
        "session_companion_rosters": {
            "22": ["captain_lysandra_ironveil"],
        },
    }
    (campaign_dir / PARTY_REGISTRY_BASENAME).write_text(
        json.dumps(registry, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.party_registry_write.corpus_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "src.graph_memory.party_context.CAMPAIGN_CORPUS",
        {"longmont-c2": (tmp_path, campaign_rel)},
    )
    return campaign_dir / PARTY_REGISTRY_BASENAME


def test_prepare_and_commit_copies_session_23_from_22(isolated_registry: Path) -> None:
    prepare = prepare_party_registry_session_roster_write(
        PartyRegistrySessionRosterWritePrepareRequest(
            campaign_id="longmont-c2",
            session=23,
            copy_from_session=22,
        )
    )
    assert prepare.writer_ok
    assert prepare.writer_confirm_token
    assert "23" in (prepare.writer_diff or "")
    assert prepare.pc_slugs == ["stafl", "bonogo"]
    assert prepare.companion_slugs == ["captain_lysandra_ironveil"]

    commit = commit_party_registry_session_roster_write(
        PartyRegistrySessionRosterWriteCommitRequest(
            campaign_id="longmont-c2",
            session=23,
            pc_slugs=prepare.pc_slugs,
            companion_slugs=prepare.companion_slugs,
            writer_confirm_token=prepare.writer_confirm_token or "",
        )
    )
    assert commit.writer_ok
    assert commit.backup_relpath
    assert commit.backup_relpath.endswith("__" + PARTY_REGISTRY_BASENAME)
    saved = json.loads(isolated_registry.read_text(encoding="utf-8"))
    assert saved["session_pc_rosters"]["23"] == ["stafl", "bonogo"]
    assert saved["session_companion_rosters"]["23"] == ["captain_lysandra_ironveil"]


def test_commit_rejects_stale_confirm_token(isolated_registry: Path) -> None:
    prepare = prepare_party_registry_session_roster_write(
        PartyRegistrySessionRosterWritePrepareRequest(
            campaign_id="longmont-c2",
            session=23,
            pc_slugs=["stafl"],
            companion_slugs=["captain_lysandra_ironveil"],
        )
    )
    with pytest.raises(PartyRegistryWriteConflictError):
        commit_party_registry_session_roster_write(
            PartyRegistrySessionRosterWriteCommitRequest(
                campaign_id="longmont-c2",
                session=23,
                pc_slugs=["stafl"],
                companion_slugs=["captain_lysandra_ironveil"],
                writer_confirm_token="stale-token",
            )
        )
