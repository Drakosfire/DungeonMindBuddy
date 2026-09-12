import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

import extraction_lab.campaign_memory_benchmark as benchmark_module
from extraction_lab.anchor_resolver import resolve_fact_anchor
from extraction_lab.anchor_schema import load_fact_anchors
from extraction_lab.campaign_memory_benchmark import (
    REQUIRED_SOURCES,
    validate_campaign_memory_benchmark,
)


ROOT = Path(__file__).resolve().parents[2]
CHECKED_IN = ROOT / "evals" / "campaign_memory_development"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _copy_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    benchmark = repo / "evals" / "campaign_memory_development"
    shutil.copytree(CHECKED_IN, benchmark)
    corpus = repo / "corpus" / "eldyrwild-markdown"
    for locator in REQUIRED_SOURCES:
        destination = corpus / locator
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "corpus" / "eldyrwild-markdown" / locator, destination)
    return repo, benchmark / "benchmark.json"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_checked_in_benchmark_validates_without_model_or_store(tmp_path) -> None:
    repo, manifest = _copy_fixture(tmp_path)
    result = validate_campaign_memory_benchmark(manifest, repo_root=repo)
    assert result["validated"] is True
    assert result["source_count"] == 7
    assert result["entity_anchor_count"] == 6
    assert result["fact_anchor_count"] == 5
    assert result["identity_expectation_count"] == 2


def test_fingerprints_are_path_independent(tmp_path) -> None:
    repo_a, manifest_a = _copy_fixture(tmp_path / "a")
    repo_b, manifest_b = _copy_fixture(tmp_path / "b")
    left = validate_campaign_memory_benchmark(manifest_a, repo_root=repo_a)
    right = validate_campaign_memory_benchmark(manifest_b, repo_root=repo_b)
    assert left["corpus_fingerprint"] == right["corpus_fingerprint"]
    assert left["gold_fingerprint"] == right["gold_fingerprint"]


def test_unknown_manifest_field_fails_closed(tmp_path) -> None:
    repo, manifest = _copy_fixture(tmp_path)
    payload = _json(manifest)
    payload["unexpected"] = True
    _write(manifest, payload)
    with pytest.raises(ValidationError):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)


def test_missing_duplicate_and_sha_drift_sources_fail(tmp_path) -> None:
    repo, manifest = _copy_fixture(tmp_path)
    payload = _json(manifest)
    missing = repo / payload["corpus_root"] / payload["sources"][0]["locator"]
    missing.unlink()
    with pytest.raises(ValueError, match="source missing"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)

    repo, manifest = _copy_fixture(tmp_path / "duplicate")
    payload = _json(manifest)
    payload["sources"][1] = payload["sources"][0]
    _write(manifest, payload)
    with pytest.raises(ValueError, match="duplicate source locator"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)

    repo, manifest = _copy_fixture(tmp_path / "drift")
    payload = _json(manifest)
    source = repo / payload["corpus_root"] / payload["sources"][0]["locator"]
    source.write_text(source.read_text(encoding="utf-8") + "drift", encoding="utf-8")
    with pytest.raises(ValueError, match="source SHA mismatch"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)


def test_forbidden_derivative_and_outside_source_fail(tmp_path, monkeypatch) -> None:
    repo, manifest = _copy_fixture(tmp_path)
    payload = _json(manifest)
    old = payload["sources"][0]["locator"]
    forbidden = "_archive/copy.md"
    payload["sources"][0]["locator"] = forbidden
    source = repo / payload["corpus_root"] / forbidden
    source.parent.mkdir(parents=True)
    source.write_text("copy", encoding="utf-8")
    payload["sources"][0]["sha256"] = benchmark_module.hashlib.sha256(b"copy").hexdigest()
    monkeypatch.setattr(benchmark_module, "REQUIRED_SOURCES", REQUIRED_SOURCES - {old} | {forbidden})
    _write(manifest, payload)
    with pytest.raises(ValueError, match="forbidden derived source"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)

    payload["sources"][0]["locator"] = "../outside.md"
    monkeypatch.setattr(benchmark_module, "REQUIRED_SOURCES", REQUIRED_SOURCES - {old} | {"../outside.md"})
    _write(manifest, payload)
    with pytest.raises(ValueError, match="must resolve inside"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("surface", "surface mismatch"),
        ("outside", "source outside cohort"),
        ("missing_marker", "marker missing"),
        ("absent_marker", "marker not found"),
        ("duplicate", "duplicate entity anchor ID"),
    ],
)
def test_entity_anchor_integrity_fails_closed(tmp_path, mutation, message) -> None:
    repo, manifest = _copy_fixture(tmp_path)
    anchor_path = manifest.parent / "gold" / "entity_anchors.json"
    anchors = _json(anchor_path)
    if mutation == "surface":
        anchors[0]["surface"] = "core_extraction"
    elif mutation == "outside":
        anchors[0]["source_file"] = "not-in-cohort.md"
    elif mutation == "missing_marker":
        anchors[0].pop("source_text_marker")
    elif mutation == "absent_marker":
        anchors[0]["source_text_marker"] = "not present anywhere"
    else:
        anchors[1]["anchor_id"] = anchors[0]["anchor_id"]
    _write(anchor_path, anchors)
    with pytest.raises(ValueError, match=message):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)


def test_fact_dependency_and_identity_intent_fail_closed(tmp_path) -> None:
    repo, manifest = _copy_fixture(tmp_path)
    fact_path = manifest.parent / "gold" / "fact_anchors.json"
    facts = _json(fact_path)
    facts[0]["subject_anchor"] = "missing"
    _write(fact_path, facts)
    with pytest.raises(ValueError, match="fact subject anchor missing"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)

    repo, manifest = _copy_fixture(tmp_path / "missing-identity")
    payload = _json(manifest)
    payload["identity_expectations"][0]["anchor_ids"][1] = "missing"
    _write(manifest, payload)
    with pytest.raises(ValueError, match="identity expectation anchor missing"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)

    repo, manifest = _copy_fixture(tmp_path / "class-mismatch")
    entity_path = manifest.parent / "gold" / "entity_anchors.json"
    entities = _json(entity_path)
    entities[1]["expected_class"] = "place"
    _write(entity_path, entities)
    with pytest.raises(ValueError, match="identity expectation class mismatch"):
        validate_campaign_memory_benchmark(manifest, repo_root=repo)


def test_compound_fact_intents_reject_insufficient_partial_matches() -> None:
    anchors = {
        anchor.anchor_id: anchor
        for anchor in load_fact_anchors(CHECKED_IN / "gold" / "fact_anchors.json")
    }
    resolved = {
        "brin_holloway_session23": {"passed": True, "resolved_entity_id": "brin"},
        "karsemine_session23": {"passed": True, "resolved_entity_id": "karsemine"},
    }

    edge_without_cook = resolve_fact_anchor(
        anchors["brin_role"],
        resolved,
        [
            {
                "fact_id": "edge-only",
                "subject_entity_id": "brin",
                "attribute": "role",
                "value": {"label": "Brin came from Edge"},
            }
        ],
    )
    assert edge_without_cook["passed"] is False
    assert edge_without_cook["fail_bucket"] == "keyword_mismatch"

    group_without_leadership = resolve_fact_anchor(
        anchors["brin_refugee_leadership"],
        resolved,
        [
            {
                "fact_id": "group-only",
                "subject_entity_id": "brin",
                "attribute": "event_progression",
                "value": {"label": "Brin traveled with the group of survivors"},
            }
        ],
    )
    assert group_without_leadership["passed"] is False
    assert group_without_leadership["fail_bucket"] == "keyword_mismatch"

    poison_without_fire = resolve_fact_anchor(
        anchors["karsemine_fire_weakness_discovery"],
        resolved,
        [
            {
                "fact_id": "poison-only",
                "subject_entity_id": "karsemine",
                "attribute": "event_outcome",
                "value": {"label": "The creatures are resistant to poison"},
            }
        ],
    )
    assert poison_without_fire["passed"] is False
    assert poison_without_fire["fail_bucket"] == "keyword_mismatch"


def test_compound_fact_intents_accept_independently_sufficient_phrases() -> None:
    anchors = {
        anchor.anchor_id: anchor
        for anchor in load_fact_anchors(CHECKED_IN / "gold" / "fact_anchors.json")
    }
    resolved = {
        "brin_holloway_session23": {"passed": True, "resolved_entity_id": "brin"},
        "karsemine_session23": {"passed": True, "resolved_entity_id": "karsemine"},
    }
    cases = (
        ("brin_role", "brin", "role", "Brin is a cook from Edge"),
        (
            "brin_refugee_leadership",
            "brin",
            "event_progression",
            "Brin is the clear leader of the refugees",
        ),
        (
            "karsemine_fire_weakness_discovery",
            "karsemine",
            "event_outcome",
            "Karsemine learned the creatures are weak to fire",
        ),
    )
    for anchor_id, entity_id, attribute, label in cases:
        result = resolve_fact_anchor(
            anchors[anchor_id],
            resolved,
            [
                {
                    "fact_id": anchor_id,
                    "subject_entity_id": entity_id,
                    "attribute": attribute,
                    "value": {"label": label},
                }
            ],
        )
        assert result["passed"] is True
