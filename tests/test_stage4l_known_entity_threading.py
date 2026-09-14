from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.services import graph_preview_runner as service
from src.graph_memory.extraction.known_entity_registry import KnownEntity


def test_recap_wrapper_threads_experiment_known_entities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    known = KnownEntity(
        slug="npc:glowkindle",
        kind="npc",
        display_name="Glowkindle",
        canonical_entity_id="npc:glowkindle",
        aliases=(),
        hub_rel_path="",
        hub_resolved=False,
        corpus_ref={"type": "npc", "ref_id": "npc:glowkindle"},
        match_terms=(("Glowkindle", "canonical"),),
    )
    captured = {}
    monkeypatch.setattr(
        service,
        "create_recap_source_artifact",
        lambda *_args, **_kwargs: SimpleNamespace(source_artifact_id="artifact:a"),
    )
    monkeypatch.setattr(
        service,
        "_normalized_from_registered",
        lambda *_args: SimpleNamespace(),
    )

    def fake_run(request):
        captured["request"] = request
        return SimpleNamespace()

    monkeypatch.setattr(service, "run_production_extraction", fake_run)
    service.run_recap_production_extraction(
        repo_root=tmp_path,
        campaign_id="longmont-c1",
        session_id="session-2",
        recap_path=tmp_path / "recap.md",
        category_client=SimpleNamespace(),
        extra_known_entities=(known,),
    )
    assert captured["request"].extra_known_entities == (known,)
