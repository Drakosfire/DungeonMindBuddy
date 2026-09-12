import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from extraction_lab.campaign_memory_benchmark import REQUIRED_SOURCES
from extraction_lab.campaign_memory_temporal_intent import (
    validate_campaign_memory_temporal_intent,
)


ROOT = Path(__file__).resolve().parents[2]
CHECKED_IN = ROOT / "evals" / "campaign_memory_development"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    benchmark_root = repo / "evals" / "campaign_memory_development"
    shutil.copytree(CHECKED_IN, benchmark_root)
    corpus = repo / "corpus" / "eldyrwild-markdown"
    for locator in REQUIRED_SOURCES:
        target = corpus / locator
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "corpus" / "eldyrwild-markdown" / locator, target)
    return (
        repo,
        benchmark_root / "benchmark.json",
        benchmark_root / "temporal_expectations.json",
    )


def _validate(repo: Path, benchmark: Path, temporal: Path):
    return validate_campaign_memory_temporal_intent(
        benchmark_path=benchmark,
        temporal_intent_path=temporal,
        repo_root=repo,
    )


def _expectation(payload, expectation_id):
    return next(
        row for row in payload["expectations"] if row["expectation_id"] == expectation_id
    )


def test_checked_in_temporal_intent_validates_exact_requirements(tmp_path) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    result = _validate(repo, benchmark, temporal)
    assert result["validated"] is True
    assert result["expectation_count"] == 7
    assert result["linked_fact_expectation_count"] == 5
    assert result["requirement_only_expectation_count"] == 2
    assert result["evidence_ref_count"] == 11
    assert result["temporal_kind_counts"] == {
        "background": 1,
        "event": 1,
        "knowledge_acquisition": 1,
        "state": 4,
    }


def test_temporal_fingerprint_is_path_independent(tmp_path) -> None:
    repo_a, benchmark_a, temporal_a = _fixture(tmp_path / "a")
    repo_b, benchmark_b, temporal_b = _fixture(tmp_path / "b")
    reordered = _json(temporal_b)
    reordered["expectations"].reverse()
    for expectation in reordered["expectations"]:
        expectation["evidence"].reverse()
        expectation["identity_expectation_refs"].reverse()
    _write(temporal_b, reordered)
    assert _validate(repo_a, benchmark_a, temporal_a)[
        "temporal_intent_fingerprint"
    ] == _validate(repo_b, benchmark_b, temporal_b)["temporal_intent_fingerprint"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("benchmark_id", "wrong", "benchmark ID mismatch"),
        ("benchmark_corpus_fingerprint", "0" * 64, "corpus fingerprint mismatch"),
        ("benchmark_gold_fingerprint", "0" * 64, "gold fingerprint mismatch"),
    ],
)
def test_benchmark_pins_fail_closed(tmp_path, field, value, message) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    payload[field] = value
    _write(temporal, payload)
    with pytest.raises(ValueError, match=message):
        _validate(repo, benchmark, temporal)


def test_unknown_top_level_and_nested_fields_fail(tmp_path) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    payload["unknown"] = True
    _write(temporal, payload)
    with pytest.raises(ValidationError):
        _validate(repo, benchmark, temporal)

    repo, benchmark, temporal = _fixture(tmp_path / "nested")
    payload = _json(temporal)
    payload["expectations"][0]["truth_window"]["unknown"] = True
    _write(temporal, payload)
    with pytest.raises(ValidationError):
        _validate(repo, benchmark, temporal)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unknown_subject", "unknown subject anchor"),
        ("unknown_fact", "unknown fact anchor"),
        ("fact_subject", "fact subject mismatch"),
        ("unknown_identity", "unknown identity expectation ref"),
        ("duplicate_identity", "duplicate identity expectation ref"),
    ],
)
def test_authority_references_fail_closed(tmp_path, mutation, message) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    row = payload["expectations"][0]
    if mutation == "unknown_subject":
        row["subject_anchor"] = "missing"
    elif mutation == "unknown_fact":
        row["fact_anchor"] = "missing"
    elif mutation == "fact_subject":
        row["fact_anchor"] = "orik_mayor_role"
    elif mutation == "unknown_identity":
        row["identity_expectation_refs"] = ["missing"]
    else:
        row["identity_expectation_refs"] *= 2
    _write(temporal, payload)
    error = ValidationError if mutation == "duplicate_identity" else ValueError
    with pytest.raises(error, match=message):
        _validate(repo, benchmark, temporal)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("outside", "evidence source outside cohort"),
        ("session", "source session mismatch"),
        ("blank_marker", "must not be blank"),
        ("absent_marker", "evidence marker not found"),
        ("duplicate", "duplicate evidence row"),
    ],
)
def test_evidence_validation_fails_closed(tmp_path, mutation, message) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    evidence = payload["expectations"][0]["evidence"]
    if mutation == "outside":
        evidence[0]["source_file"] = "outside.md"
    elif mutation == "session":
        evidence[0]["source_session"] = 24
    elif mutation == "blank_marker":
        evidence[0]["source_text_marker"] = " "
    elif mutation == "absent_marker":
        evidence[0]["source_text_marker"] = "not in the pinned source"
    else:
        evidence.append(dict(evidence[0]))
    _write(temporal, payload)
    error = ValidationError if mutation == "blank_marker" else ValueError
    with pytest.raises(error, match=message):
        _validate(repo, benchmark, temporal)


def test_exact_v1_expectation_set_and_unique_ids_are_required(tmp_path) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    payload["expectations"][1] = dict(payload["expectations"][0])
    _write(temporal, payload)
    with pytest.raises(ValueError, match="duplicate temporal expectation ID"):
        _validate(repo, benchmark, temporal)

    repo, benchmark, temporal = _fixture(tmp_path / "missing")
    payload = _json(temporal)
    payload["expectations"].pop()
    _write(temporal, payload)
    with pytest.raises(ValidationError):
        _validate(repo, benchmark, temporal)

    repo, benchmark, temporal = _fixture(tmp_path / "extra")
    payload = _json(temporal)
    extra = dict(payload["expectations"][0])
    extra["expectation_id"] = "eighth"
    payload["expectations"].append(extra)
    _write(temporal, payload)
    with pytest.raises(ValidationError):
        _validate(repo, benchmark, temporal)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("end_before_start", "end before start"),
        ("bounded_without_end", "bounded persistence requires end"),
        ("ends_without_end", "ends evidence requires end session"),
        ("ends_wrong_session", "ends evidence session mismatch"),
        ("boundary_without_evidence", "start boundary lacks evidence"),
    ],
)
def test_truth_window_rules_fail_closed(tmp_path, mutation, message) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    battle = _expectation(payload, "mireward_north_gate_battle_state")
    if mutation == "end_before_start":
        battle["truth_window"] = {"start_session": 25, "end_session": 24}
    elif mutation == "bounded_without_end":
        battle["truth_window"]["end_session"] = None
        battle["evidence"][1]["role"] = "confirms"
    elif mutation == "ends_without_end":
        battle["truth_window"]["end_session"] = None
    elif mutation == "ends_wrong_session":
        battle["truth_window"]["end_session"] = 23
    else:
        battle["truth_window"]["start_session"] = 22
    _write(temporal, payload)
    with pytest.raises(ValueError, match=message):
        _validate(repo, benchmark, temporal)


def test_unknown_start_knowledge_start_and_bounded_battle_are_preserved(tmp_path) -> None:
    repo, benchmark, temporal = _fixture(tmp_path)
    payload = _json(temporal)
    mayor = _expectation(payload, "orric_mayor_state")
    knowledge = _expectation(payload, "karsemine_tripod_fire_weakness_knowledge")
    battle = _expectation(payload, "mireward_north_gate_battle_state")
    assert mayor["truth_window"] == {"start_session": None, "end_session": None}
    assert knowledge["truth_window"] == {"start_session": 23, "end_session": None}
    assert battle["truth_window"] == {"start_session": 23, "end_session": 24}
    assert _validate(repo, benchmark, temporal)["validated"] is True
