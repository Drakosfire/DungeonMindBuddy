from __future__ import annotations

import copy
import json

import evals.llm_ingestion_slice.run_slice as run_slice_module

from evals.llm_ingestion_slice.run_slice import (
    MANIFEST_PATH,
    OUTPUT_DIR,
    _gate_a_source_layer_integrity,
    _gate_extraction_viability,
    _gate_d_workflow_state_progression,
    _load_json,
    _load_viability_thresholds,
    main,
    run_slice,
)


def test_llm_ingestion_slice_main_passes_and_writes_artifacts() -> None:
    exit_code = main()
    assert exit_code == 0

    assert (OUTPUT_DIR / "run_payload.json").exists()
    assert (OUTPUT_DIR / "gate_report.json").exists()
    assert (OUTPUT_DIR / "report.md").exists()
    assert (OUTPUT_DIR / "stage_chunks.json").exists()
    assert (OUTPUT_DIR / "stage_entities.json").exists()
    assert (OUTPUT_DIR / "stage_facts.json").exists()
    assert (OUTPUT_DIR / "stage_events.json").exists()
    assert (OUTPUT_DIR / "projection_deltas.json").exists()
    assert (OUTPUT_DIR / "gold_score.json").exists()

    gate_report = json.loads((OUTPUT_DIR / "gate_report.json").read_text(encoding="utf-8"))
    assert gate_report["overall_pass"] is True
    gate_t = next(g for g in gate_report["gates"] if g["name"] == "Gate T - narrative temporal tick")
    assert gate_t["pass"] is True
    gate_tc = next(g for g in gate_report["gates"] if g["name"] == "Gate TC - campaign temporal consistency")
    assert gate_tc["pass"] is True
    gate_tw = next(g for g in gate_report["gates"] if g["name"] == "Gate TW - sequence-only temporal warning")
    assert gate_tw["pass"] is True
    assert "metrics" in gate_tw
    gate_g = next(g for g in gate_report["gates"] if g["name"] == "Gate G - gold scoring")
    assert gate_g["pass"] is True
    assert "metrics" in gate_g


def test_gate_a_fails_when_source_fingerprint_changes() -> None:
    manifest = _load_json(MANIFEST_PATH)
    run_payload = run_slice()
    broken_manifest = copy.deepcopy(manifest)
    broken_manifest["sources"]["world_markdown"]["sha256"] = "deadbeef"

    gate = _gate_a_source_layer_integrity(
        manifest=broken_manifest,
        evidence_units=run_payload["evidence_units"],
    )
    assert gate["pass"] is False
    assert gate["source_errors"]


def test_gate_d_fails_when_missing_projection_stage() -> None:
    payload = run_slice()
    payload.pop("projection_zero_tick", None)
    payload["projection_deltas"]["instantiation_to_zero_tick"] = []

    gate = _gate_d_workflow_state_progression(payload)
    assert gate["pass"] is False
    assert gate["errors"]


def test_viability_gate_passes_with_current_slice_payload() -> None:
    payload = run_slice()
    thresholds = _load_viability_thresholds()

    gate = _gate_extraction_viability(
        evidence_units=payload["evidence_units"],
        entities=payload["entities"],
        facts=payload["facts"],
        conflicts=payload["conflicts"],
        thresholds=thresholds,
    )
    assert gate["pass"] is True
    assert gate["metrics"]["counts"]["facts"] > 0
    assert gate["metrics"]["counts"]["unique_entity_ids"] > 0


def test_viability_gate_fails_for_zero_entities() -> None:
    payload = run_slice()
    thresholds = _load_viability_thresholds()
    payload["entities"] = []

    gate = _gate_extraction_viability(
        evidence_units=payload["evidence_units"],
        entities=payload["entities"],
        facts=payload["facts"],
        conflicts=payload["conflicts"],
        thresholds=thresholds,
    )
    assert gate["pass"] is False
    assert any("unique entity_id count is 0" in error for error in gate["errors"])


def test_viability_gate_fails_for_zero_facts() -> None:
    payload = run_slice()
    thresholds = _load_viability_thresholds()
    payload["facts"] = []

    gate = _gate_extraction_viability(
        evidence_units=payload["evidence_units"],
        entities=payload["entities"],
        facts=payload["facts"],
        conflicts=payload["conflicts"],
        thresholds=thresholds,
    )
    assert gate["pass"] is False
    assert any("facts count is 0" in error for error in gate["errors"])


def test_viability_gate_fails_for_high_duplicate_fact_ratio() -> None:
    payload = run_slice()
    thresholds = _load_viability_thresholds()
    source_fact = payload["facts"][0]
    payload["facts"] = [copy.deepcopy(source_fact) for _ in range(4)]

    gate = _gate_extraction_viability(
        evidence_units=payload["evidence_units"],
        entities=payload["entities"],
        facts=payload["facts"],
        conflicts=payload["conflicts"],
        thresholds=thresholds,
    )
    assert gate["pass"] is False
    assert any("duplicate_fact_ratio" in error for error in gate["errors"])


def test_viability_gate_fails_for_conflict_count_outside_band() -> None:
    payload = run_slice()
    thresholds = _load_viability_thresholds()
    payload["conflicts"] = []

    gate = _gate_extraction_viability(
        evidence_units=payload["evidence_units"],
        entities=payload["entities"],
        facts=payload["facts"],
        conflicts=payload["conflicts"],
        thresholds=thresholds,
    )
    assert gate["pass"] is False
    assert any("conflict_count 0 below minimum" in error for error in gate["errors"])


def test_main_fails_fast_when_viability_fails(monkeypatch) -> None:
    payload = run_slice()
    payload["facts"] = []

    def _mock_run_slice() -> dict:
        return payload

    monkeypatch.setattr(run_slice_module, "run_slice", _mock_run_slice)
    exit_code = run_slice_module.main()
    assert exit_code == 1

    gate_report = json.loads((OUTPUT_DIR / "gate_report.json").read_text(encoding="utf-8"))
    gate_names = [gate["name"] for gate in gate_report["gates"]]
    assert "Gate A - source and layer integrity" in gate_names
    assert "Gate V - extraction viability" in gate_names
    assert "Gate T - narrative temporal tick" in gate_names
    assert "Gate TC - campaign temporal consistency" in gate_names
    assert "Gate TW - sequence-only temporal warning" in gate_names
    assert "Gate G - gold scoring" not in gate_names
    assert "Gate B - event contract integrity" not in gate_names
    assert "Gate C - hybrid correctness" not in gate_names
    assert "Gate D - workflow state progression" not in gate_names


def test_campaign_planning_facts_copy_asserted_session_from_evidence() -> None:
    payload = run_slice()
    planning_facts = [
        fact
        for fact in payload["stage_artifacts"]["facts"]
        if "evu_campaign_planning_cult" in fact.get("evidence_ids", [])
    ]
    assert planning_facts, "expected at least one fact for evu_campaign_planning_cult"
    assert all(fact["asserted_in_session"] == 6 for fact in planning_facts)


def test_all_fact_subject_entities_exist_in_stage_entities() -> None:
    payload = run_slice()
    entity_ids = {
        str(entity.get("entity_id"))
        for entity in payload["stage_artifacts"]["entities"]
        if entity.get("entity_id") is not None
    }
    subject_ids = {
        str(fact.get("subject_entity_id"))
        for fact in payload["stage_artifacts"]["facts"]
        if fact.get("subject_entity_id") is not None
    }
    missing = sorted(subject_ids - entity_ids)
    assert not missing, f"missing subject entities in stage_entities: {missing}"
