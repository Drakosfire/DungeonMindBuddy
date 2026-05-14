from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.scene_beat_memory import (
    SCENE_BEAT_MEMORY_META_SCHEMA_V1,
    build_scene_beat_records,
    build_scene_beat_records_from_gold_beats,
    write_scene_beat_records,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import RecapUnitAnnotationsV1


def _annotations() -> RecapUnitAnnotationsV1:
    return RecapUnitAnnotationsV1.model_validate(
        {
            "schema": "dmb_recap_unit_annotations_v1",
            "campaign_id": "longmont-c1",
            "session_number": 13,
            "source_recap_path": "x.md",
            "unit_annotations": [
                {"unit_id": "u1", "beat_id": "beat-1", "tags": [], "location_mentions": [], "population_mentions": []},
                {"unit_id": "u2", "beat_id": None, "tags": [], "location_mentions": [], "population_mentions": []},
            ],
            "beat_index": [{"beat_id": "beat-1", "summary": "s"}],
        }
    )


def test_build_scene_beat_records_preserves_order_and_lexical_plain() -> None:
    records = [
        {"unit_id": "u1", "lexical_plain": "alpha"},
        {"unit_id": "u2", "lexical_plain": "beta"},
    ]
    out, meta = build_scene_beat_records(records=records, annotations=_annotations())
    assert [r["unit_id"] for r in out] == ["u1", "u2"]
    assert out[0]["beat_id"] == "beat-1"
    assert "beat_id" not in out[1]
    assert out[0]["lexical_plain"] == "alpha"
    assert meta["records_with_beat_id"] == 1


def test_build_scene_beat_records_from_gold_merges_morgue_scene_span() -> None:
    gold = Path(
        "evals/sentence_routing_retrieval_falsification/manual_labels/"
        "Session 13 - The Meaty and the Dead.gold.scene_span_v1.breadcrumbed.md"
    )
    fixture = Path(
        "evals/sentence_routing_retrieval_falsification/fixtures/"
        "c1s13_session13_scene_span_v1.records_meta.jsonl"
    )
    rows = []
    for line in fixture.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    out, meta = build_scene_beat_records_from_gold_beats(records=rows, gold_beat_md=gold)
    by_id = {r["unit_id"]: r.get("beat_id") for r in out}
    assert by_id["u-L0031-02"] == "c1s13-b009-morgue-ambush-fight-scene"
    assert by_id["u-L0037-02"] == "c1s13-b009-morgue-ambush-fight-scene"
    assert meta["beat_count"] == 10


def test_write_scene_beat_records_writes_schema(tmp_path: Path) -> None:
    records_jsonl = tmp_path / "in.jsonl"
    ann_json = tmp_path / "ann.json"
    out_jsonl = tmp_path / "out.jsonl"
    out_meta = tmp_path / "out.json"
    records_jsonl.write_text(json.dumps({"schema": "dmb_session_memory_record_v1", "unit_id": "u1", "lexical_plain": "a"}) + "\n", encoding="utf-8")
    ann_json.write_text(_annotations().model_dump_json(), encoding="utf-8")
    meta = write_scene_beat_records(records_jsonl=records_jsonl, unit_annotations_json=ann_json, out_jsonl=out_jsonl, out_meta=out_meta)
    assert meta["schema"] == SCENE_BEAT_MEMORY_META_SCHEMA_V1
    assert out_jsonl.exists()
