from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from extraction_lab.anchor_resolver import resolve_entity_anchors, resolve_fact_anchors
from extraction_lab.anchor_schema import load_entity_anchors, load_fact_anchors
from extraction_lab.pipeline_contract import compute_pipeline_contract
from extraction_lab.report import render_report
from extraction_lab.run_manifest import build_run_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "out" / "extraction_lab"
DEFAULT_ENTITY_ANCHORS = ROOT / "evals" / "mirathorn_vertical_slice" / "gold" / "entity_anchors.json"
DEFAULT_FACT_ANCHORS = ROOT / "evals" / "mirathorn_vertical_slice" / "gold" / "fact_anchors.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _resolve_store_file(store_path: Path, filename: str, fallback: str) -> Path:
    primary = store_path / filename
    if primary.exists():
        return primary
    secondary = store_path / fallback
    if secondary.exists():
        return secondary
    raise FileNotFoundError(f"Missing store file: expected {primary} or {secondary}")


def _load_store_payloads(store_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities = _read_json(_resolve_store_file(store_path, "entities.json", "stage_entities.json"))
    facts = _read_json(_resolve_store_file(store_path, "facts.json", "stage_facts.json"))
    return entities, facts


def _compute_store_sha256(*, entities: list[dict[str, Any]], facts: list[dict[str, Any]]) -> str:
    payload = json.dumps({"entities": entities, "facts": facts}, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def _resolve_source_path(raw_path: str, corpus_source_root: Path | None) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    if corpus_source_root is not None:
        return (corpus_source_root / candidate).resolve()
    return (ROOT / candidate).resolve()


def _load_ingest_source_paths(store_path: Path, corpus_source_root: Path | None) -> list[Path]:
    ingest_index_path = store_path / "ingest_index.json"
    if not ingest_index_path.exists():
        return []
    payload = _read_json(ingest_index_path)
    if not isinstance(payload, dict):
        return []
    source_paths: set[Path] = set()
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        raw_source_path = str(value.get("source_path", "")).strip()
        if not raw_source_path:
            continue
        source_paths.add(_resolve_source_path(raw_source_path, corpus_source_root))
    return sorted(source_paths)


def _compute_corpus_source_sha256(*, source_paths: list[Path], corpus_source_root: Path | None) -> str:
    paths = list(source_paths)
    if not paths and corpus_source_root is not None:
        paths = sorted(path.resolve() for path in corpus_source_root.rglob("*.md"))
    hasher = hashlib.sha256()
    for path in paths:
        normalized_path = path.as_posix().encode("utf-8")
        hasher.update(normalized_path)
        if path.exists():
            hasher.update(path.read_bytes())
        else:
            hasher.update(b"<missing>")
    return hasher.hexdigest() if paths else ""


def _aggregate_metrics(entity_results: list[dict[str, Any]], fact_results: list[dict[str, Any]], entities: list[dict[str, Any]], facts: list[dict[str, Any]]) -> dict[str, Any]:
    entity_total = len(entity_results)
    fact_total = len(fact_results)
    entity_pass = sum(1 for row in entity_results if row.get("passed"))
    fact_pass = sum(1 for row in fact_results if row.get("passed"))
    unresolved_core = sum(
        1
        for row in [*entity_results, *fact_results]
        if row.get("surface") == "core_extraction" and not row.get("passed")
    )
    return {
        "entity_anchor_recall": float(entity_pass) / float(entity_total) if entity_total else 0.0,
        "fact_anchor_recall": float(fact_pass) / float(fact_total) if fact_total else 0.0,
        "unresolved_core_anchors": unresolved_core,
        "total_entity_count": len(entities),
        "total_fact_count": len(facts),
    }


def run_extraction_lab(
    *,
    store_path: Path,
    surface: str,
    out_dir: Path,
    run_id: str,
    entity_anchor_path: Path,
    fact_anchor_path: Path,
    entity_model: str,
    fact_model: str,
    recap_model: str | None = None,
    batch_size: int | None = None,
    filter_version: str | None = None,
    pipeline_code_sha: str | None = None,
    corpus_source_root: Path | None = None,
) -> Path:
    started_at = _utc_now_iso()
    entities, facts = _load_store_payloads(store_path)
    store_sha = _compute_store_sha256(entities=entities, facts=facts)
    source_paths = _load_ingest_source_paths(store_path, corpus_source_root)
    corpus_source_sha = _compute_corpus_source_sha256(
        source_paths=source_paths,
        corpus_source_root=corpus_source_root,
    )
    contract = compute_pipeline_contract(
        store_sha256=store_sha,
        corpus_source_sha256=corpus_source_sha,
        entity_model=entity_model,
        fact_model=fact_model,
        recap_model=recap_model,
        batch_size=batch_size,
        filter_version=filter_version,
        pipeline_code_sha=pipeline_code_sha,
    )

    entity_anchors = [a for a in load_entity_anchors(entity_anchor_path) if a.surface == surface]
    fact_anchors = [a for a in load_fact_anchors(fact_anchor_path) if a.surface == surface]
    entity_results = resolve_entity_anchors(entity_anchors, entities, facts)
    entity_results_by_id = {row["anchor_id"]: row for row in entity_results}
    fact_results = resolve_fact_anchors(fact_anchors, entity_results_by_id, facts)
    aggregate_metrics = _aggregate_metrics(entity_results, fact_results, entities, facts)
    manifest = build_run_manifest(
        run_id=run_id,
        surface=surface,
        store_path=store_path,
        contract=contract,
        entity_anchor_count=len(entity_anchors),
        fact_anchor_count=len(fact_anchors),
        entity_count=len(entities),
        fact_count=len(facts),
        started_at=started_at,
    )

    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "pipeline_contract.json", contract)
    _write_json(run_dir / "run_manifest.json", manifest)
    _write_json(run_dir / "entity_results.json", entity_results)
    _write_json(run_dir / "fact_results.json", fact_results)
    _write_json(run_dir / "aggregate_metrics.json", aggregate_metrics)
    (run_dir / "report.md").write_text(
        render_report(
            run_id=run_id,
            surface=surface,
            aggregate_metrics=aggregate_metrics,
            entity_results=entity_results,
            fact_results=fact_results,
        ),
        encoding="utf-8",
    )
    return run_dir


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Extraction Lab v1 against a prebuilt store.")
    parser.add_argument("--surface", default="core_extraction")
    parser.add_argument("--store", type=Path, required=True, help="Directory containing entities.json and facts.json")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", type=str, default="")
    parser.add_argument("--entity-anchors", type=Path, default=DEFAULT_ENTITY_ANCHORS)
    parser.add_argument("--fact-anchors", type=Path, default=DEFAULT_FACT_ANCHORS)
    parser.add_argument("--entity-model", type=str, default="gpt-5.4-nano")
    parser.add_argument("--fact-model", type=str, default="gpt-5.4-nano")
    parser.add_argument("--recap-model", type=str, default="")
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--filter-version", type=str, default="")
    parser.add_argument("--pipeline-code-sha", type=str, default="")
    parser.add_argument(
        "--corpus-source-root",
        type=Path,
        default=None,
        help="Optional directory of raw markdown corpus for corpus_source_sha256.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_extraction_lab(
        store_path=args.store,
        surface=args.surface,
        out_dir=args.out_dir,
        run_id=run_id,
        entity_anchor_path=args.entity_anchors,
        fact_anchor_path=args.fact_anchors,
        entity_model=args.entity_model,
        fact_model=args.fact_model,
        recap_model=args.recap_model or None,
        batch_size=args.batch_size or None,
        filter_version=args.filter_version or None,
        pipeline_code_sha=args.pipeline_code_sha or None,
        corpus_source_root=args.corpus_source_root,
    )
    print(f"Extraction Lab run artifacts written to {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
