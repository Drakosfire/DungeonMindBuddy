from __future__ import annotations
from tests.page_fixtures import create_page_fixture
from apps.live_control_server.services.workspace_document_registry import get_workspace_document

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.live_control_server.routes import graph_preview


SOURCE = "The Azure Reach is a continent. Asterport is a city.\n"


@pytest.mark.parametrize("profile_version", ["1.5", "1.6", "1.7", "1.8", "1.9", "1.10"])
def test_gazetteer_launch_binds_generation_to_committed_build_source(
    profile_version: str,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_page_fixture(
        tmp_path,
        title="The City of Asterport",
        campaign_id="azure-reach",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    source_path = tmp_path / (record.target_relpath or "")
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(SOURCE, encoding="utf-8")
    committed = get_workspace_document(tmp_path, record.document_id)
    digest = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
    monkeypatch.setattr(graph_preview, "repo_root", lambda: tmp_path)

    captured: list[dict[str, Any]] = []

    class _Run:
        run_id = "run-gazetteer"

        def model_dump(self, *, mode: str) -> dict[str, Any]:
            assert mode == "json"
            return {
                "run_id": "run-gazetteer",
                "profile_id": f"worldbuilding_gazetteer_v1@{profile_version}",
                "status": "reviewable",
            }

    def _execute(**kwargs: Any) -> SimpleNamespace:
        captured.append(kwargs)
        return SimpleNamespace(
            run=_Run(), failure_kind=None, diagnostics=[]
        )

    from apps.live_control_server.services import worldbuilding_ge_execution

    monkeypatch.setattr(
        worldbuilding_ge_execution,
        "run_gazetteer_with_generation_engine",
        _execute,
    )
    payload = graph_preview.post_extraction_run(
        {
            "document_id": committed.document_id,
            "expected_revision": committed.revision,
            "expected_content_sha256": digest,
            "profile_id": "worldbuilding_gazetteer_v1",
            "profile_version": profile_version,
            "model_id": "client-selected-model-is-ignored",
            "world_id": "client-selected-world-is-ignored",
        }
    )

    assert payload["run"]["profile_id"] == f"worldbuilding_gazetteer_v1@{profile_version}"
    assert payload["document_id"] == committed.document_id
    assert payload["document_revision"] == committed.revision
    assert payload["source_content_sha256"] == digest
    assert captured == [
        {
            "repo_root": tmp_path,
            "source_artifact_id": payload["source_artifact_id"],
            "document_id": committed.document_id,
            "document_revision": committed.revision,
            "expected_content_sha256": digest,
            "profile_version": profile_version,
        }
    ]
