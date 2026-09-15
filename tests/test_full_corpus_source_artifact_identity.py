from pathlib import Path

import pytest

from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact


def test_production_recap_registration_derives_digest_bound_identity(tmp_path: Path) -> None:
    recap = tmp_path / "recap.md"
    recap.write_text("# Recap\n\nObserved.\n", encoding="utf-8")
    with pytest.raises(TypeError):
        create_recap_source_artifact(
            tmp_path,
            campaign_id="longmont-c1",
            session_id="session-1",
            recap_path=recap,
            source_artifact_id="full-corpus:longmont-c1:session-1:verified",
        )
