from __future__ import annotations

import argparse, json
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_compile import enrich_records_with_beat_ids
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import RecapUnitAnnotationsV1
from src.agent.session_memory_query import load_session_memory_records_jsonl

SCENE_BEAT_MEMORY_META_SCHEMA_V1 = "dmb_scene_beat_memory_meta_v1"


def load_unit_annotations_payload(path: Path) -> RecapUnitAnnotationsV1:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") == "dmb_unit_annotations_ingest_report_v1":
        payload = payload.get("parsed") or {}
    return RecapUnitAnnotationsV1.model_validate(payload)


def build_scene_beat_records(*, records: list[dict[str, Any]], annotations: RecapUnitAnnotationsV1) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched = enrich_records_with_beat_ids(records, annotations)
    beat_ids = {str(r.get('beat_id')) for r in enriched if r.get('beat_id')}
    with_beat = sum(1 for r in enriched if r.get("beat_id"))
    return enriched, {
        "record_count": len(enriched),
        "records_with_beat_id": with_beat,
        "beat_count": len(beat_ids),
        "source_recap_path": annotations.source_recap_path,
    }


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except Exception:
        return path.as_posix()


def write_scene_beat_records(*, records_jsonl: Path, unit_annotations_json: Path, out_jsonl: Path, out_meta: Path) -> dict[str, Any]:
    records = load_session_memory_records_jsonl(records_jsonl)
    annotations = load_unit_annotations_payload(unit_annotations_json)
    enriched, summary = build_scene_beat_records(records=records, annotations=annotations)
    out_jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in enriched) + "\n", encoding="utf-8")
    meta = {
        "schema": SCENE_BEAT_MEMORY_META_SCHEMA_V1,
        "records_jsonl": _rel(records_jsonl),
        "unit_annotations_json": _rel(unit_annotations_json),
        "out_jsonl": _rel(out_jsonl),
        "out_meta": _rel(out_meta),
        **summary,
    }
    out_meta.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--records-jsonl", type=Path, required=True)
    p.add_argument("--unit-annotations-json", type=Path, required=True)
    p.add_argument("--out-jsonl", type=Path, required=True)
    p.add_argument("--out-meta", type=Path, required=True)
    a = p.parse_args()
    write_scene_beat_records(records_jsonl=a.records_jsonl, unit_annotations_json=a.unit_annotations_json, out_jsonl=a.out_jsonl, out_meta=a.out_meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
