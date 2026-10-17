from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
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


def _fixture_source_artifact_id(
    source: Path, *, campaign_id: str, session_id: str
) -> str:
    from graph_memory.evidence.source_artifact import (
        build_world_scoped_recap_source_artifact_id,
    )

    normalized = source.read_text(encoding="utf-8").rstrip("\n") + "\n"
    return build_world_scoped_recap_source_artifact_id(
        world_id="world:fixture",
        campaign_id=campaign_id,
        session_id=session_id,
        content_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    )


def _copy_candidate_to_tmp(tmp_path: Path, *, source_artifact_id: str) -> Path:
    candidate = tmp_path / "candidate_graph_fixture.json"
    payload = json.loads(CANDIDATE_PATH.read_text())
    payload["campaign_id"] = "longmont-c2"
    payload["session_id"] = "session-24"
    payload["source_artifact_ids"] = [source_artifact_id]
    candidate.write_text(json.dumps(payload))
    return candidate


def _shortened_candidate_fixture(
    tmp_path: Path,
) -> tuple[Path, Any, dict, dict, str, str]:
    from graph_memory.evidence.source_artifact import build_recap_source_artifact_id
    from src.graph_memory.source_span import (
        build_source_span_index_for_text,
        source_span_index_to_dict,
    )

    source = tmp_path / "session_16_normalized_recap.md"
    source_text = "Session 16\n\nBonogo carried the violet astrolabe into Mireward at dawn.\n"
    source.write_text(source_text, encoding="utf-8")
    content_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    artifact = SimpleNamespace(
        source_artifact_id=build_recap_source_artifact_id(
            campaign_id="longmont-c1",
            session_id="session-16",
            content_sha256=content_sha256,
        )
    )
    span_index = source_span_index_to_dict(
        build_source_span_index_for_text(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=content_sha256,
            text=source_text,
        )
    )
    span = next(span for span in span_index["spans"] if span.get("start_line") == 3)
    canonical_span_id = span["source_span_id"]
    legacy_artifact_id = artifact.source_artifact_id.rsplit(":", 1)[0]
    legacy_span_id = f"{legacy_artifact_id}{canonical_span_id[len(artifact.source_artifact_id):]}"
    evidence_ref = {
        "id": "evidence:bonogo-recap-16",
        "span_id": legacy_span_id,
        "source_span_ref_id": legacy_span_id,
        "source_artifact_id": artifact.source_artifact_id,
        "source_ref_id": f"{artifact.source_artifact_id}:text",
        "source_anchor_id": f"anchor:{legacy_span_id}",
        "label": legacy_span_id,
        "anchor_quotes": ["Bonogo carried the violet astrolabe into Mireward at dawn."],
    }
    candidate = {
        "schema": "dmb_candidate_graph_preview_v0",
        "version": "0.1",
        "campaign_id": "longmont-c1",
        "session_id": "session-16",
        "source_artifact_ids": [artifact.source_artifact_id],
        "nodes": [
            {
                "node_id": "person:bonogo",
                "label": "Bonogo",
                "node_type": "character",
                "evidence_refs": [json.loads(json.dumps(evidence_ref))],
            }
        ],
        "edges": [],
        "beats": [],
        "evidence_refs": [evidence_ref],
        "diagnostics": {
            "preview_only": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "agent_interaction_connected": False,
            "extraction_performed": False,
            "llm_used": False,
            "unresolved_evidence_refs": 0,
            "warning_count": 0,
        },
    }
    return source, artifact, span_index, candidate, legacy_span_id, canonical_span_id


def test_runner_repairs_only_proven_legacy_candidate_span_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, artifact, span_index, candidate, legacy_span_id, canonical_span_id = (
        _shortened_candidate_fixture(tmp_path)
    )
    monkeypatch.chdir(tmp_path)
    candidate_path = tmp_path / "legacy_candidate_graph.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    original_sha256 = compute_sha256(candidate_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c1",
            session_id="session-16",
            normalized_recap_path=source,
            output_dir=Path("runs/repaired_candidate"),
            candidate_graph_path=candidate_path,
            source_span_index=span_index,
            source_artifact_id=artifact.source_artifact_id,
        )
    )

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert result.candidate_graph_path is not None
    assert result.validation_report_path is not None
    manifest = _load_manifest(result.manifest_path)
    packaged = _load_manifest(result.candidate_graph_path)
    report = _load_manifest(result.validation_report_path)
    refs = [packaged["evidence_refs"][0], packaged["nodes"][0]["evidence_refs"][0]]
    assert all(ref["span_id"] == canonical_span_id for ref in refs)
    assert all(ref["source_span_ref_id"] == canonical_span_id for ref in refs)
    assert all(ref["label"] == canonical_span_id for ref in refs)
    assert all(ref["source_anchor_id"] == f"anchor:{canonical_span_id}" for ref in refs)
    assert all(ref["span_id"] != legacy_span_id for ref in refs)
    assert len(report["evidence_reference_repairs"]) == 2
    assert report["diagnostics"]["unresolved_evidence_ref_count"] == 0
    assert packaged["diagnostics"]["unresolved_evidence_refs"] == 0
    assert packaged["diagnostics"]["evidence_reference_repair_count"] == 2
    assert manifest["status"] == "candidate_validation_ready"
    assert manifest["health"]["candidate_graph_valid"] is True
    assert compute_sha256(candidate_path) == original_sha256


def test_runner_candidate_warning_diagnostics_match_validation_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, artifact, span_index, candidate, _, _ = _shortened_candidate_fixture(
        tmp_path
    )
    monkeypatch.chdir(tmp_path)
    candidate["evidence_refs"][0].pop("id")
    candidate_path = tmp_path / "candidate_with_warning.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c1",
            session_id="session-16",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_with_warning"),
            candidate_graph_path=candidate_path,
            source_span_index=span_index,
            source_artifact_id=artifact.source_artifact_id,
        )
    )

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert result.candidate_graph_path is not None
    assert result.validation_report_path is not None
    packaged = _load_manifest(result.candidate_graph_path)
    report = _load_manifest(result.validation_report_path)
    assert report["warnings"]
    assert packaged["diagnostics"]["warning_count"] == len(report["warnings"])


def test_runner_keeps_candidate_immutable_when_source_is_in_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, artifact, span_index, candidate, _, canonical_span_id = (
        _shortened_candidate_fixture(tmp_path)
    )
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "runs" / "same_directory"
    output_dir.mkdir(parents=True)
    candidate_path = output_dir / "candidate_graph.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    original_sha256 = compute_sha256(candidate_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c1",
            session_id="session-16",
            normalized_recap_path=source,
            output_dir=Path("runs/same_directory"),
            candidate_graph_path=candidate_path,
            source_span_index=span_index,
            source_artifact_id=artifact.source_artifact_id,
        )
    )

    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    assert result.candidate_graph_path is not None
    assert result.candidate_graph_path != candidate_path
    assert result.candidate_graph_path.name == "candidate_graph_packaged.json"
    assert compute_sha256(candidate_path) == original_sha256
    packaged = _load_manifest(result.candidate_graph_path)
    assert packaged["evidence_refs"][0]["span_id"] == canonical_span_id


@pytest.mark.parametrize(
    "mutation",
    [
        "quote_mismatch",
        "missing_quotes",
        "wrong_source_ref",
        "wrong_source_artifact",
        "missing_span",
        "inconsistent_secondary_span",
        "foreign_source_anchor",
    ],
)
def test_runner_keeps_unproven_legacy_candidate_span_aliases_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    source, artifact, span_index, candidate, legacy_span_id, canonical_span_id = (
        _shortened_candidate_fixture(tmp_path)
    )
    monkeypatch.chdir(tmp_path)
    broken_candidate = json.loads(json.dumps(candidate))
    foreign_anchor_id = "anchor:artifact:other-recap:span:unrelated:9-9"
    for evidence_ref in (
        broken_candidate["evidence_refs"]
        + broken_candidate["nodes"][0]["evidence_refs"]
    ):
        if mutation == "quote_mismatch":
            evidence_ref["anchor_quotes"] = ["This sentence is not in the recap."]
        elif mutation == "missing_quotes":
            evidence_ref["anchor_quotes"] = []
        elif mutation == "wrong_source_ref":
            evidence_ref["source_ref_id"] = "artifact:other-recap:text"
        elif mutation == "wrong_source_artifact":
            evidence_ref["source_artifact_id"] = "artifact:other-recap"
        elif mutation == "inconsistent_secondary_span":
            evidence_ref["span_id"] = canonical_span_id
            evidence_ref["source_span_ref_id"] = "artifact:missing:span:unknown:3-3"
        elif mutation == "foreign_source_anchor":
            evidence_ref["source_anchor_id"] = foreign_anchor_id
        else:
            evidence_ref["span_id"] = "artifact:missing:span:unknown:3-3"
    candidate_path = tmp_path / "unproven_candidate_graph.json"
    candidate_path.write_text(json.dumps(broken_candidate), encoding="utf-8")
    original_sha256 = compute_sha256(candidate_path)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c1",
            session_id="session-16",
            normalized_recap_path=source,
            output_dir=Path(f"runs/unproven_{mutation}"),
            candidate_graph_path=candidate_path,
            source_span_index=span_index,
            source_artifact_id=artifact.source_artifact_id,
        )
    )

    assert result.status == GraphIngestRunStatus.FAILED
    assert result.candidate_graph_path is not None
    assert result.validation_report_path is not None
    manifest = _load_manifest(result.manifest_path)
    packaged = _load_manifest(result.candidate_graph_path)
    report = _load_manifest(result.validation_report_path)
    assert report["evidence_reference_repairs"] == []
    assert report["diagnostics"]["unresolved_evidence_ref_count"] == 2
    assert packaged["diagnostics"]["unresolved_evidence_refs"] == 2
    assert manifest["status"] == "failed"
    assert manifest["health"]["candidate_graph_valid"] is False
    if mutation == "inconsistent_secondary_span":
        assert (
            packaged["evidence_refs"][0]["source_span_ref_id"]
            == "artifact:missing:span:unknown:3-3"
        )
    elif mutation == "foreign_source_anchor":
        assert packaged["evidence_refs"][0]["source_anchor_id"] == foreign_anchor_id
    else:
        assert legacy_span_id in packaged["evidence_refs"][0]["source_span_ref_id"]
    assert compute_sha256(candidate_path) == original_sha256


def test_ambiguous_legacy_candidate_span_alias_is_not_repaired(tmp_path: Path) -> None:
    from src.graph_memory.extraction.graph_ingest_packaging import (
        _repair_candidate_evidence_span_aliases,
    )

    _, artifact, span_index, candidate, legacy_span_id, _ = _shortened_candidate_fixture(
        tmp_path
    )
    span = next(span for span in span_index["spans"] if span.get("start_line") == 3)
    span_index["spans"].append(json.loads(json.dumps(span)))

    repairs = _repair_candidate_evidence_span_aliases(
        candidate,
        source_span_index=span_index,
        recap_text=(tmp_path / "session_16_normalized_recap.md").read_text(
            encoding="utf-8"
        ),
    )

    assert repairs == []
    assert candidate["evidence_refs"][0]["span_id"] == legacy_span_id


def test_canonical_candidate_span_references_are_left_unchanged(tmp_path: Path) -> None:
    from src.graph_memory.extraction.graph_ingest_packaging import (
        _repair_candidate_evidence_span_aliases,
    )

    source, _, span_index, candidate, _, canonical_span_id = (
        _shortened_candidate_fixture(tmp_path)
    )
    canonical_candidate = json.loads(json.dumps(candidate))
    for evidence_ref in (
        canonical_candidate["evidence_refs"]
        + canonical_candidate["nodes"][0]["evidence_refs"]
    ):
        evidence_ref["span_id"] = canonical_span_id
        evidence_ref["source_span_ref_id"] = canonical_span_id
        evidence_ref["source_anchor_id"] = f"anchor:{canonical_span_id}"
        evidence_ref["label"] = canonical_span_id

    repairs = _repair_candidate_evidence_span_aliases(
        canonical_candidate,
        source_span_index=span_index,
        recap_text=source.read_text(encoding="utf-8"),
    )

    assert repairs == []
    assert all(
        evidence_ref["span_id"] == canonical_span_id
        and evidence_ref["source_span_ref_id"] == canonical_span_id
        and evidence_ref["source_anchor_id"] == f"anchor:{canonical_span_id}"
        and evidence_ref["label"] == canonical_span_id
        for evidence_ref in (
            canonical_candidate["evidence_refs"]
            + canonical_candidate["nodes"][0]["evidence_refs"]
        )
    )


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
    source_artifact_id = _fixture_source_artifact_id(
        source, campaign_id="longmont-c2", session_id="session-24"
    )
    candidate = _copy_candidate_to_tmp(tmp_path, source_artifact_id=source_artifact_id)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/candidate_ready"),
            candidate_graph_path=candidate,
            source_artifact_id=source_artifact_id,
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
    payload["campaign_id"] = "longmont-c2"
    payload["session_id"] = "session-24"
    source_artifact_id = _fixture_source_artifact_id(
        source, campaign_id="longmont-c2", session_id="session-24"
    )
    payload["source_artifact_ids"] = [source_artifact_id]
    payload["diagnostics"]["canon_promotion"] = True
    invalid_candidate.write_text(json.dumps(payload))

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/invalid_candidate"),
            candidate_graph_path=invalid_candidate,
            source_artifact_id=source_artifact_id,
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
    assert graph["diagnostics"]["preview_only"] is True
    assert graph["diagnostics"]["canon_promoted"] is False
    assert graph["diagnostics"]["extraction_performed"] is False
    assert "canon_promotion" not in graph["diagnostics"]
    assert "predicate_family" not in (graph.get("edges") or [{}])[0]
    assert (result.output_dir / "pass_telemetry.json").exists()


def test_runner_canonical_line_only_index_reaches_category_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        load_source_span_index,
    )
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )
    from src.graph_memory.party_context import CAMPAIGN_CORPUS
    from src.graph_memory.source_span import source_span_index_to_dict
    from tests.fixtures.graph_memory.category_extraction_helpers import (
        minimal_category_pass_outputs,
    )

    class CapturingClient(FixtureCategoryGraphPassClient):
        def __init__(self, source_span_ref_id: str) -> None:
            super().__init__(minimal_category_pass_outputs(source_span_ref_id))
            self.prompts: dict[str, str] = {}

        def run_pass(self, pass_name: str, *, model_id: str, instructions: str,
                     user_content: str, pass_spec=None) -> dict[str, Any]:
            self.prompts[pass_name] = user_content
            return super().run_pass(
                pass_name, model_id=model_id, instructions=instructions,
                user_content=user_content, pass_spec=pass_spec,
            )

    monkeypatch.setitem(
        CAMPAIGN_CORPUS,
        "longmont-c1",
        (REPO_ROOT / "corpus/eldyrwild-markdown", "Longmont Campaign/Campaign 1"),
    )
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "session_16_normalized_recap.md"
    recap_text = "Session 16\n\nBonogo carried the violet astrolabe into Mireward at dawn.\n"
    source.write_text(recap_text, encoding="utf-8")
    artifact = create_recap_source_artifact(
        tmp_path, world_id="fixture-world", campaign_id="longmont-c1", session_id="session-16", recap_path=source,
    )
    span_index = source_span_index_to_dict(
        load_source_span_index(tmp_path, artifact.source_artifact_id)
    )
    assert all("text" not in span and "text_excerpt" not in span for span in span_index["spans"])
    recap_span_ref = next(
        span["source_span_id"] for span in span_index["spans"]
        if span.get("start_line") == 3
    )
    client = CapturingClient(recap_span_ref)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c1",
            session_id="session-16",
            normalized_recap_path=source,
            output_dir=Path("runs/canonical_line_only_prompt"),
            allow_llm=True,
            category_client=client,
            source_span_index=span_index,
            source_artifact_id=artifact.source_artifact_id,
        )
    )

    actor_prompt = client.prompts["actor_pass"]
    assert "Bonogo carried the violet astrolabe into Mireward at dawn." in actor_prompt
    assert recap_span_ref in actor_prompt
    assert "Baergrom" in actor_prompt  # C1 roster context, distinct from recap text
    assert result.status == GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
    manifest = _load_manifest(result.manifest_path)
    packaged_index = _load_manifest(result.output_dir / "source_span_index.json")
    candidate = _load_manifest(result.candidate_graph_path)
    provenance = _load_manifest(result.output_dir / "provenance_index.json")
    assert packaged_index == span_index
    assert manifest["source"]["source_artifact_id"] == artifact.source_artifact_id
    assert candidate["source_artifact_ids"] == [artifact.source_artifact_id]
    assert provenance["source_artifacts"][0]["artifact_id"] == artifact.source_artifact_id


def test_runner_allow_llm_blocked_writes_calm_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenClient:
        def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str, pass_spec=None) -> dict[str, Any]:
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
        def run_pass(self, pass_name: str, *, model_id: str, instructions: str, user_content: str, pass_spec=None) -> dict[str, Any]:
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


def test_runner_encounter_job_preview_profile_threads_context_vocabulary_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )
    from src.graph_memory.vocabulary import VocabularyEntry, render_context_vocabulary_packet

    monkeypatch.chdir(tmp_path)
    source = _runner_source_with_glowkindle_recap(tmp_path)

    packet = render_context_vocabulary_packet(
        scope="campaign",
        campaign_entries=[
            VocabularyEntry(
                vocab_id="vocab:test:glowkindle",
                canonical_label="Glowkindle",
                entity_kind="actor",
                scope="campaign",
                campaign_id="longmont-c2",
                status="candidate",
                authority="manual_seed",
            ),
        ],
        packet_seed="test-runner-vocabulary-packet-v1",
    ).packet

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/encounter_job_preview_vocab"),
            allow_llm=True,
            graph_extraction_profile="category_encounter_job_preview",
            category_client=FixtureCategoryGraphPassClient(_runner_glowkindle_pass_outputs()),
            context_vocabulary_packet=packet,
            enable_node_vocabulary_packet=True,
            enable_edge_vocabulary_packet=True,
        )
    )
    manifest = _load_manifest(result.manifest_path)
    diagnostics = manifest["diagnostics"]

    assert validate_graph_ingest_run_manifest(manifest)["valid"] is True
    assert diagnostics["context_vocabulary_packet_id"] == packet.packet_id
    assert diagnostics["enable_node_vocabulary_packet"] is True
    assert diagnostics["enable_edge_vocabulary_packet"] is True


def test_runner_encounter_job_preview_profile_without_packet_leaves_vocabulary_disabled(
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
            output_dir=Path("runs/encounter_job_preview_no_vocab"),
            allow_llm=True,
            graph_extraction_profile="category_encounter_job_preview",
            category_client=FixtureCategoryGraphPassClient(_runner_glowkindle_pass_outputs()),
        )
    )
    manifest = _load_manifest(result.manifest_path)
    diagnostics = manifest["diagnostics"]

    assert diagnostics["context_vocabulary_packet_id"] is None
    assert diagnostics["enable_node_vocabulary_packet"] is False
    assert diagnostics["enable_edge_vocabulary_packet"] is False


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
    source_artifact_id = _fixture_source_artifact_id(
        source, campaign_id="longmont-c2", session_id="session-24"
    )
    candidate = _copy_candidate_to_tmp(tmp_path, source_artifact_id=source_artifact_id)

    result = run_graph_preview_extraction(
        GraphPreviewRunnerOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            normalized_recap_path=source,
            output_dir=Path("runs/profile_fixture_bypass"),
            candidate_graph_path=candidate,
            source_artifact_id=source_artifact_id,
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
