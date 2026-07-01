from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.graph_memory_layer.graph_preview_runner import (
    GraphPreviewRunnerOptions,
    compute_sha256,
    run_graph_preview_extraction,
)
from graph_memory.ingestion import (
    GraphIngestRunStatus,
    validate_graph_ingest_run_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests/fixtures/graph_memory/category_preview_runner"
RECAP_PATH = FIXTURE_DIR / "session_24_normalized_recap.md"
CANDIDATE_PATH = FIXTURE_DIR / "candidate_graph_fixture.json"


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text())


def _copy_recap_to_tmp(tmp_path: Path) -> Path:
    source = tmp_path / "session_24_normalized_recap.md"
    source.write_text(RECAP_PATH.read_text())
    return source


def _copy_candidate_to_tmp(tmp_path: Path) -> Path:
    candidate = tmp_path / "candidate_graph_fixture.json"
    candidate.write_text(CANDIDATE_PATH.read_text())
    return candidate


def test_runner_writes_manifest_for_arbitrary_session_without_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("evals/graph_memory_layer/runs/graph_ingest/session_24"),
        )
    )

    assert result.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    assert result.manifest_path.exists()
    assert result.candidate_graph_path is None
    assert result.source_span_bundle_dir is not None
    assert (result.output_dir / "source_span_index.json").exists()


def test_runner_manifest_uses_supplied_campaign_and_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="custom-campaign",
            session_id="session-99",
            normalized_recap_path=source,
            output_dir=Path("runs/session_99"),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert manifest["campaign_id"] == "custom-campaign"
    assert manifest["session_id"] == "session-99"
    assert (
        manifest["source"]["source_artifact_id"]
        == "artifact:recap:custom-campaign:session-99"
    )


def test_runner_manifest_records_normalized_recap_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24"),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert manifest["source"]["normalized_recap_sha256"] == compute_sha256(source)


def test_runner_manifest_ends_at_source_span_bundle_ready_without_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24"),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert manifest["status"] == "source_span_bundle_ready"
    assert manifest["diagnostics"]["candidate_extraction"] is False
    assert "preview_union_store" not in manifest["artifacts"]


def test_runner_does_not_require_gold_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/no_gold"),
        )
    )

    assert result.manifest_path.exists()


def test_runner_required_gold_mode_fails_when_gold_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    with pytest.raises(FileNotFoundError, match="required_gold"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=Path("runs/missing_gold"),
                comparison_mode="required_gold",
                gold_path=Path("missing-gold.json"),
            )
        )


def test_runner_rejects_absolute_output_dir_or_unsafe_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    with pytest.raises(ValueError, match="output_dir must be repo-relative"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=tmp_path / "absolute",
            )
        )
    with pytest.raises(ValueError, match="path traversal"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=Path("../escape"),
            )
        )


def test_runner_outputs_validate_with_graph_ingest_manifest_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/valid_manifest"),
        )
    )

    report = validate_graph_ingest_run_manifest(_load_manifest(result.manifest_path))
    assert report["valid"] is True
    assert report["errors"] == []


def test_runner_can_wrap_existing_candidate_graph_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    candidate = _copy_candidate_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_ready"),
            candidate_graph_path=candidate,
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert result.candidate_graph_path is not None
    assert result.validation_report_path is not None
    assert manifest["status"] == "candidate_validation_ready"
    assert "candidate_graph" in manifest["artifacts"]
    assert "candidate_validation_report" in manifest["artifacts"]
    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True


def test_runner_failed_candidate_validation_does_not_reach_candidate_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    invalid_candidate = tmp_path / "invalid_candidate_graph.json"
    payload = json.loads(CANDIDATE_PATH.read_text())
    payload["diagnostics"]["canon_promotion"] = True
    invalid_candidate.write_text(json.dumps(payload))

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/invalid_candidate"),
            candidate_graph_path=invalid_candidate,
        )
    )
    manifest = _load_manifest(result.manifest_path)
    assert result.validation_report_path is not None
    validation_report = json.loads(result.validation_report_path.read_text())

    assert result.status == GraphIngestRunStatus.FAILED
    assert manifest["status"] == "failed"
    assert manifest["health"]["candidate_graph_valid"] is False
    assert "forbidden lifecycle flag is true: canon_promotion" in manifest["errors"]
    assert manifest["next_actions"] == ["fix_candidate_graph"]
    assert manifest["steps"][-1]["id"] == "validate_candidate_graph"
    assert manifest["steps"][-1]["state"] == "failed"
    assert validation_report["valid"] is False
    assert (
        "forbidden lifecycle flag is true: canon_promotion"
        in validation_report["errors"]
    )


def test_runner_allow_llm_with_fake_client_writes_candidate_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        minimal_category_pass_outputs,
    )

    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    source.write_text(
        "Session recap\n\nBonogo scouts the Mireward road and regroups at dusk.\n",
        encoding="utf-8",
    )

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24_llm"),
            allow_llm=True,
            category_client=FixtureCategoryGraphPassClient(
                minimal_category_pass_outputs("session-24:recap:paragraph:001")
            ),
        )
    )

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert result.candidate_graph_path is not None and result.candidate_graph_path.exists()
    assert result.validation_report_path is not None and result.validation_report_path.exists()
    manifest = _load_manifest(result.manifest_path)
    assert manifest["health"]["model_id"] == "gpt-5.4-mini"
    assert manifest["diagnostics"]["candidate_extraction"] is True
    assert manifest["diagnostics"]["extraction_mode"] == "category_decomposed"
    graph = json.loads(result.candidate_graph_path.read_text())
    assert graph["diagnostics"]["canon_promotion"] is False
    assert (result.output_dir / "pass_telemetry.json").exists()


def test_runner_allow_llm_blocked_writes_calm_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenClient:
        def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str) -> dict[str, Any]:
            raise RuntimeError("model unavailable")

    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24_blocked"),
            allow_llm=True,
            category_client=BrokenClient(),
        )
    )

    assert result.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    assert result.candidate_graph_path is None
    manifest = _load_manifest(result.manifest_path)
    assert manifest["errors"] == ["model unavailable"]
    assert manifest["next_actions"] == ["configure model", "supply candidate_graph_path"]


def test_runner_invalid_llm_json_preserves_raw_response_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionError,
    )

    class InvalidJsonClient:
        def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str) -> dict[str, Any]:
            raise CategoryGraphExtractionError(
                "actor_pass returned invalid JSON: Expecting value",
                pass_name=pass_name,
                raw_model_response='{"observation_nodes": [',
            )

    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/session_24_invalid_json"),
            allow_llm=True,
            category_client=InvalidJsonClient(),
        )
    )

    assert result.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    assert result.candidate_graph_path is None
    manifest = _load_manifest(result.manifest_path)
    assert manifest["diagnostics"]["extraction_mode"] == "llm_blocked"
    assert "actor_pass returned invalid JSON" in manifest["errors"][0]
    raw_artifact = manifest["artifacts"]["raw_model_response"]
    raw_path = tmp_path / raw_artifact["uri"]
    assert raw_path.read_text() == '{"observation_nodes": ['
    extract_step = next(step for step in manifest["steps"] if step["id"] == "extract_candidate_graph")
    assert extract_step["artifact_refs"][0]["uri"] == raw_artifact["uri"]


def test_runner_writes_deterministic_paragraph_source_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "recap.md"
    source.write_text("Opening title\n\nThe group scouts the Mireward road.\n\nThey regroup at dusk.\n")

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-22",
            normalized_recap_path=source,
            output_dir=Path("runs/session_22"),
        )
    )

    index = _load_manifest(result.output_dir / "source_span_index.json")
    span_ids = [span["span_id"] for span in index["spans"]]
    # Regression guard for the trailing-newline segmentation bug: the source
    # file ends with a single "\n" (the normal case for saved Markdown), and
    # the final paragraph ("They regroup at dusk.") must still be split out.
    assert span_ids == [
        "session-22:recap:full_text",
        "session-22:recap:paragraph:001",
        "session-22:recap:paragraph:002",
        "session-22:recap:paragraph:003",
    ]
    assert index["paragraph_span_count"] == 3
    assert index["spans"][-1]["text_excerpt"] == "They regroup at dusk."


def _profile_options(manifest: dict[str, Any]) -> dict[str, bool]:
    return manifest["diagnostics"]["graph_extraction_profile_options"]


def _assert_profile_options_disabled(options: dict[str, bool]) -> None:
    assert options == {
        "enable_encounter_job_pass": False,
        "enable_party_participation_attachment": False,
        "enable_encounter_job_edge_guidance": False,
        "enable_dynamic_node_vocabulary_packet": False,
    }


def _runner_source_with_glowkindle_recap(tmp_path: Path) -> Path:
    source = tmp_path / "session_24_normalized_recap.md"
    source.write_text(
        "Glowkindle asks the party to clear rats from the cellar beneath the brewery.\n\n"
        "The cellar is beneath Glowkindle's brewery and contains damaged stores.\n\n"
        "In the cellar, the party fights a swarm of rats and drives them back.\n\n"
        "After the fight, the stores are safe enough for Glowkindle to reopen the cellar.\n",
        encoding="utf-8",
    )
    return source


def _runner_glowkindle_pass_outputs() -> dict[str, dict[str, Any]]:
    from evals.graph_memory_layer.encounter_job_dogfood_fixture import (
        glowkindle_fixture_pass_outputs,
    )

    replacements = {
        "spref:glowkindle:001": "session-24:recap:paragraph:001",
        "spref:glowkindle:002": "session-24:recap:paragraph:002",
        "spref:glowkindle:003": "session-24:recap:paragraph:003",
        "spref:glowkindle:004": "session-24:recap:paragraph:004",
    }

    def replace(value: Any) -> Any:
        if isinstance(value, str):
            return replacements.get(value, value)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value

    return replace(glowkindle_fixture_pass_outputs())


def _has_edge(edges: list[dict[str, Any]], source: str, target: str, rel: str) -> bool:
    return any(
        edge.get("from_node_id") == source
        and edge.get("to_node_id") == target
        and edge.get("relationship_type") == rel
        for edge in edges
    )


def test_runner_default_profile_preserves_category_baseline_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        minimal_category_pass_outputs,
    )

    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    source.write_text(
        "Session recap\n\nBonogo scouts the Mireward road and regroups at dusk.\n",
        encoding="utf-8",
    )

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/default_profile"),
            allow_llm=True,
            category_client=FixtureCategoryGraphPassClient(
                minimal_category_pass_outputs("session-24:recap:paragraph:001")
            ),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True
    assert manifest["diagnostics"]["candidate_extraction"] is True
    assert manifest["diagnostics"]["extraction_mode"] == "category_decomposed"
    assert manifest["diagnostics"]["graph_extraction_profile"] == "current_default"
    _assert_profile_options_disabled(_profile_options(manifest))
    graph = json.loads(result.candidate_graph_path.read_text())
    assert "quest_clear_glowkindle_rats" not in {node.get("node_id") for node in graph["nodes"]}


def test_runner_category_baseline_profile_is_explicit_default_equivalent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        minimal_category_pass_outputs,
    )

    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    source.write_text("Bonogo scouts the road.\n", encoding="utf-8")

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/category_baseline"),
            allow_llm=True,
            graph_extraction_profile="category_baseline",
            category_client=FixtureCategoryGraphPassClient(
                minimal_category_pass_outputs("session-24:recap:paragraph:001")
            ),
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True
    assert manifest["diagnostics"]["graph_extraction_profile"] == "category_baseline"
    _assert_profile_options_disabled(_profile_options(manifest))


def test_runner_encounter_job_preview_profile_maps_flags_and_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )

    monkeypatch.chdir(tmp_path)
    source = _runner_source_with_glowkindle_recap(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/encounter_job_preview"),
            allow_llm=True,
            graph_extraction_profile="category_encounter_job_preview",
            category_client=FixtureCategoryGraphPassClient(_runner_glowkindle_pass_outputs()),
        )
    )
    manifest = _load_manifest(result.manifest_path)
    options = _profile_options(manifest)

    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True
    assert manifest["diagnostics"]["graph_extraction_profile"] == "category_encounter_job_preview"
    assert options["enable_encounter_job_pass"] is True
    assert options["enable_party_participation_attachment"] is True
    assert options["enable_encounter_job_edge_guidance"] is True
    assert options["enable_dynamic_node_vocabulary_packet"] is False
    assert (result.output_dir / "pass_outputs.json").exists()
    assert (result.output_dir / "pass_telemetry.json").exists()
    assert (result.output_dir / "consolidation_diagnostics.json").exists()
    graph = json.loads(result.candidate_graph_path.read_text())
    node_ids = {node.get("node_id") for node in graph["nodes"]}
    assert "quest_clear_glowkindle_rats" in node_ids
    assert "enc_glowkindle_cellar_rats" in node_ids
    assert _has_edge(graph["edges"], "node:heroes-party", "quest_clear_glowkindle_rats", "pursues")
    assert _has_edge(graph["edges"], "node:heroes-party", "enc_glowkindle_cellar_rats", "participates_in")
    extraction_diagnostics = json.loads((result.output_dir / "consolidation_diagnostics.json").read_text())
    assert extraction_diagnostics.get("dynamic_node_vocabulary_packet", {}).get("enabled") in {None, False}


def test_runner_unknown_graph_extraction_profile_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    with pytest.raises(ValueError, match="unsupported graph_extraction_profile: surprise_me"):
        run_graph_preview_extraction(
            GraphPreviewRunnerOptions(
                campaign_id="longmont-c2",
                session_id="session-24",
                normalized_recap_path=source,
                output_dir=Path("runs/unknown_profile"),
                allow_llm=True,
                graph_extraction_profile="surprise_me",
            )
        )

    assert not (tmp_path / "runs/unknown_profile/candidate_graph.json").exists()


def test_runner_profile_does_not_trigger_extraction_without_allow_llm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/profile_without_llm"),
            allow_llm=False,
            graph_extraction_profile="category_encounter_job_preview",
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert result.status == GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    assert result.candidate_graph_path is None
    assert manifest["diagnostics"]["candidate_extraction"] is False
    assert manifest["diagnostics"]["graph_extraction_profile"] == "category_encounter_job_preview"
    assert not (result.output_dir / "pass_outputs.json").exists()


def test_runner_candidate_graph_path_bypasses_profile_extractor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = _copy_recap_to_tmp(tmp_path)
    candidate = _copy_candidate_to_tmp(tmp_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/profile_fixture_bypass"),
            candidate_graph_path=candidate,
            allow_llm=True,
            graph_extraction_profile="category_encounter_job_preview",
        )
    )
    manifest = _load_manifest(result.manifest_path)

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert manifest["diagnostics"]["extraction_mode"] == "fixture"
    assert manifest["diagnostics"]["graph_extraction_profile"] == "category_encounter_job_preview"
    assert not (result.output_dir / "pass_outputs.json").exists()
    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True
