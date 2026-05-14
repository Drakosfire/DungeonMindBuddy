"""Enrich session-memory JSONL with ``beat_id`` from unit annotations or manual beat gold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import parse_frontmatter_and_body
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_compile import (
    enrich_records_with_beat_id_map,
    enrich_records_with_beat_ids,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_gold import (
    load_gold_beat_index,
    unit_beat_id_map_from_gold_beats,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import RecapUnitAnnotationsV1
from src.agent.session_memory_query import load_session_memory_records_jsonl

SCENE_BEAT_MEMORY_META_SCHEMA_V1 = "dmb_scene_beat_memory_meta_v1"


def load_unit_annotations_payload(path: Path) -> RecapUnitAnnotationsV1:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") == "dmb_unit_annotations_ingest_report_v1":
        payload = payload.get("parsed") or {}
    return RecapUnitAnnotationsV1.model_validate(payload)


def _source_recap_path_from_gold_md(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    frontmatter, _body = parse_frontmatter_and_body(text)
    if not frontmatter:
        return None
    data = yaml.safe_load(frontmatter)
    if not isinstance(data, dict):
        return None
    raw = data.get("source_recap_path")
    return str(raw).strip() if raw else None


def build_scene_beat_records(*, records: list[dict[str, Any]], annotations: RecapUnitAnnotationsV1) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched = enrich_records_with_beat_ids(records, annotations)
    beat_ids = {str(r.get("beat_id")) for r in enriched if r.get("beat_id")}
    with_beat = sum(1 for r in enriched if r.get("beat_id"))
    return enriched, {
        "record_count": len(enriched),
        "records_with_beat_id": with_beat,
        "beat_count": len(beat_ids),
        "source_recap_path": annotations.source_recap_path,
    }


def build_scene_beat_records_from_gold_beats(
    *,
    records: list[dict[str, Any]],
    gold_beat_md: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    beats = load_gold_beat_index(gold_beat_md)
    beat_map: dict[str, str | None] = {k: v for k, v in unit_beat_id_map_from_gold_beats(beats).items()}
    enriched = enrich_records_with_beat_id_map(records, beat_map)
    beat_ids = {str(r.get("beat_id")) for r in enriched if r.get("beat_id")}
    with_beat = sum(1 for r in enriched if r.get("beat_id"))
    recap = _source_recap_path_from_gold_md(gold_beat_md) or ""
    return enriched, {
        "record_count": len(enriched),
        "records_with_beat_id": with_beat,
        "beat_count": len(beat_ids),
        "source_recap_path": recap,
    }


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except Exception:
        return path.as_posix()


def write_scene_beat_records(
    *,
    records_jsonl: Path,
    out_jsonl: Path,
    out_meta: Path,
    unit_annotations_json: Path | None = None,
    gold_beat_md: Path | None = None,
) -> dict[str, Any]:
    if (unit_annotations_json is None) == (gold_beat_md is None):
        raise ValueError("provide exactly one of unit_annotations_json or gold_beat_md")
    records = load_session_memory_records_jsonl(records_jsonl)
    if unit_annotations_json is not None:
        annotations = load_unit_annotations_payload(unit_annotations_json)
        enriched, summary = build_scene_beat_records(records=records, annotations=annotations)
        meta_src = {"unit_annotations_json": _rel(unit_annotations_json)}
    else:
        assert gold_beat_md is not None
        enriched, summary = build_scene_beat_records_from_gold_beats(records=records, gold_beat_md=gold_beat_md)
        meta_src = {"gold_beat_md": _rel(gold_beat_md)}
    out_jsonl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in enriched) + "\n", encoding="utf-8")
    meta = {
        "schema": SCENE_BEAT_MEMORY_META_SCHEMA_V1,
        "records_jsonl": _rel(records_jsonl),
        "out_jsonl": _rel(out_jsonl),
        "out_meta": _rel(out_meta),
        **meta_src,
        **summary,
    }
    out_meta.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--records-jsonl", type=Path, required=True)
    p.add_argument("--unit-annotations-json", type=Path, default=None)
    p.add_argument(
        "--gold-beat-md",
        type=Path,
        default=None,
        help="Manual beat gold (``beat_index``); enriches records with ``beat_id`` without a live annotation JSON.",
    )
    p.add_argument("--out-jsonl", type=Path, required=True)
    p.add_argument("--out-meta", type=Path, required=True)
    a = p.parse_args()
    write_scene_beat_records(
        records_jsonl=a.records_jsonl,
        unit_annotations_json=a.unit_annotations_json,
        gold_beat_md=a.gold_beat_md,
        out_jsonl=a.out_jsonl,
        out_meta=a.out_meta,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
