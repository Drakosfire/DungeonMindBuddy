import json

from extraction_lab.run_extraction_lab import run_extraction_lab


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_run_extraction_lab_emits_required_artifacts(tmp_path) -> None:
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    _write_json(
        store_dir / "entities.json",
        [
            {
                "entity_id": "ent_mirathorn",
                "display_name": "Mirathorn",
                "entity_class": "place",
                "aliases": ["City of Mirathorn"],
            }
        ],
    )
    _write_json(
        store_dir / "facts.json",
        [
            {
                "fact_id": "fact_1",
                "subject_entity_id": "ent_mirathorn",
                "attribute": "geography",
                "value": {"label": "Stormspire Peaks nearby"},
            }
        ],
    )
    _write_json(
        store_dir / "evidence_units.json",
        [{"evidence_id": "ev_1", "text": "Mirathorn near Stormspire Peaks"}],
    )

    entity_anchor_path = tmp_path / "entity_anchors.json"
    _write_json(
        entity_anchor_path,
        [
            {
                "anchor_id": "mirathorn_city",
                "intent": "Mirathorn place extraction",
                "expected_class": "place",
                "expected_names": ["Mirathorn", "City of Mirathorn"],
                "surface": "core_extraction",
            }
        ],
    )
    fact_anchor_path = tmp_path / "fact_anchors.json"
    _write_json(
        fact_anchor_path,
        [
            {
                "anchor_id": "mirathorn_geography",
                "intent": "Mirathorn geography extraction",
                "subject_anchor": "mirathorn_city",
                "expected_attribute": "geography",
                "match_keywords": ["stormspire"],
                "alternative_attributes": [],
                "surface": "core_extraction",
            }
        ],
    )
    out_dir = tmp_path / "out"
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "doc_a.md").write_text("# A\n", encoding="utf-8")
    (corpus_root / "doc_b.md").write_text("# B\n", encoding="utf-8")

    run_dir = run_extraction_lab(
        store_path=store_dir,
        surface="core_extraction",
        out_dir=out_dir,
        run_id="fixture_run",
        entity_anchor_path=entity_anchor_path,
        fact_anchor_path=fact_anchor_path,
        entity_model="gpt-5.4-nano",
        fact_model="gpt-5.4-nano",
        corpus_source_root=corpus_root,
    )
    assert (run_dir / "pipeline_contract.json").exists()
    assert (run_dir / "run_manifest.json").exists()
    assert (run_dir / "entity_results.json").exists()
    assert (run_dir / "fact_results.json").exists()
    assert (run_dir / "aggregate_metrics.json").exists()
    assert (run_dir / "report.md").exists()
    contract = json.loads((run_dir / "pipeline_contract.json").read_text(encoding="utf-8"))
    assert contract["store_sha256"]
    assert contract["corpus_source_sha256"]
