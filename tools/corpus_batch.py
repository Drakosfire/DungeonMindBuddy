"""Corpus-wide OpenAI Batch API pipeline: submit / poll / complete.

Three-phase workflow that aggregates all corpus files into two batch jobs
(one entity, one fact) instead of per-file submissions.

Usage:
    uv run python tools/corpus_batch.py --submit [options]
    uv run python tools/corpus_batch.py --poll <manifest-path> [--poll-interval 300]
    uv run python tools/corpus_batch.py --complete <manifest-path>
    uv run python tools/corpus_batch.py --status <manifest-path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snake_case(value: str) -> str:
    lowered = value.lower()
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in lowered)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "document"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rss_mb() -> float:
    """Best-effort resident memory snapshot in MiB."""
    statm = Path("/proc/self/statm")
    if statm.exists():
        try:
            rss_pages = int(statm.read_text(encoding="utf-8").split()[1])
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            return (rss_pages * page_size) / (1024 * 1024)
        except Exception:
            pass
    try:
        import resource

        rss_kb = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return rss_kb / 1024.0
    except Exception:
        return 0.0


def _path_size_bytes(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _entity_merge_key(entity: dict[str, Any]) -> str:
    """Best-effort stable key for merging deduped entity records across chunks."""
    entity_id = str(entity.get("entity_id", "") or "").strip()
    if entity_id:
        return f"id::{entity_id}"
    name = str(entity.get("display_name", "") or "").strip().lower()
    entity_class = str(entity.get("entity_class", "") or "").strip().lower()
    return f"name::{name}::class::{entity_class}"


def _merge_entities(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge entities while preserving first-seen order and favoring newer fields."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in existing:
        key = _entity_merge_key(record)
        if key not in merged:
            order.append(key)
            merged[key] = dict(record)
        else:
            merged[key].update(record)
    for record in incoming:
        key = _entity_merge_key(record)
        if key not in merged:
            order.append(key)
            merged[key] = dict(record)
        else:
            merged[key].update(record)
    return [merged[key] for key in order]


def _build_units_from_manifest(
    manifest: dict[str, Any],
    *,
    file_limit: int = 0,
    unit_limit: int = 0,
) -> list[dict[str, Any]]:
    from src.ingestion.chunker import chunk_document
    from src.ingestion.source_anchor import resolve_git_commit_sha

    corpus_root = Path(str(manifest.get("corpus_root", ".")))
    commit_sha = resolve_git_commit_sha(cwd=corpus_root)

    files = manifest["files"]
    total_files = len(files)
    selected_files = files[: file_limit] if file_limit > 0 else files

    all_units: list[dict[str, Any]] = []
    started = time.perf_counter()
    for idx, fr in enumerate(selected_files, 1):
        source_path = Path(fr["source_path"])
        rel = str(fr.get("relative_path") or source_path.name)
        corpus_source_path = Path(rel).as_posix()
        units = chunk_document(
            docx_path=source_path,
            document_id=fr["document_id"],
            document_title=fr["title"],
            canon_layer=fr["canon_layer"],
            campaign_id=fr["campaign_id"],
            source_class=fr["source_class"],
            corpus_source_path=corpus_source_path,
            commit_sha=commit_sha,
        )
        all_units.extend(units)
        if idx % 10 == 0 or idx == len(selected_files):
            print(
                f"  Chunked {idx}/{len(selected_files)} selected files "
                f"({len(all_units)} units, source total files={total_files})",
                flush=True,
            )
        if unit_limit > 0 and len(all_units) >= unit_limit:
            all_units = all_units[:unit_limit]
            print(f"  Unit limit reached at {unit_limit} units", flush=True)
            break
    elapsed = time.perf_counter() - started
    print(f"  Chunk build done: {len(all_units)} units in {elapsed:.2f}s", flush=True)
    return all_units


def _extract_entities_for_units(
    *,
    units: list[dict[str, Any]],
    cache_dir: Path,
    work_dir: Path,
    model: str,
    batch_size: int,
    schema_repair_batch: bool,
    schema_repair_model: str,
    schema_repair_poll_interval: float,
    transition_unit_chunk_size: int,
    transition_chunk_pause_ms: int,
) -> list[dict[str, Any]]:
    from src.ingestion.entity_extractor import run_entity_extraction

    if not units:
        return []

    chunk_units: list[dict[str, Any]] = []
    merged_entities: list[dict[str, Any]] = []
    processed_units = 0
    started = time.perf_counter()

    for unit in units:
        chunk_units.append(unit)
        if len(chunk_units) >= max(1, transition_unit_chunk_size):
            chunk_started = time.perf_counter()
            print(
                f"  Entity transition chunk: {processed_units + 1}-{processed_units + len(chunk_units)} "
                f"of {len(units)} units",
                flush=True,
            )
            entity_result = run_entity_extraction(
                chunk_units,
                known_entities=merged_entities,
                model=model,
                batch_size=batch_size,
                cache_dir=cache_dir,
                openai_client=None,
                allow_heuristic_fallback=False,
                recap_artifacts=None,
                schema_repair_batch=schema_repair_batch,
                schema_repair_model=schema_repair_model,
                schema_repair_poll_interval=schema_repair_poll_interval,
                schema_repair_work_dir=work_dir / "schema_repair",
            )
            merged_entities = _merge_entities(merged_entities, entity_result["entities"])
            processed_units += len(chunk_units)
            print(
                f"  Entity transition progress: {processed_units}/{len(units)} units, "
                f"{len(merged_entities)} merged entities, "
                f"chunk_elapsed={time.perf_counter() - chunk_started:.2f}s",
                flush=True,
            )
            if transition_chunk_pause_ms > 0:
                time.sleep(transition_chunk_pause_ms / 1000.0)
            chunk_units = []

    if chunk_units:
        chunk_started = time.perf_counter()
        print(
            f"  Entity transition chunk: {processed_units + 1}-{processed_units + len(chunk_units)} "
            f"of {len(units)} units",
            flush=True,
        )
        entity_result = run_entity_extraction(
            chunk_units,
            known_entities=merged_entities,
            model=model,
            batch_size=batch_size,
            cache_dir=cache_dir,
            openai_client=None,
            allow_heuristic_fallback=False,
            recap_artifacts=None,
            schema_repair_batch=schema_repair_batch,
            schema_repair_model=schema_repair_model,
            schema_repair_poll_interval=schema_repair_poll_interval,
            schema_repair_work_dir=work_dir / "schema_repair",
        )
        merged_entities = _merge_entities(merged_entities, entity_result["entities"])
        processed_units += len(chunk_units)
        print(
            f"  Entity transition progress: {processed_units}/{len(units)} units, "
            f"{len(merged_entities)} merged entities, "
            f"chunk_elapsed={time.perf_counter() - chunk_started:.2f}s",
            flush=True,
        )
        if transition_chunk_pause_ms > 0:
            time.sleep(transition_chunk_pause_ms / 1000.0)

    print(
        f"  Entity extraction complete: {len(merged_entities)} entities "
        f"in {time.perf_counter() - started:.2f}s",
        flush=True,
    )
    return merged_entities


def _prepare_fact_requests_streaming(
    *,
    all_units: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    fact_model: str,
    batch_size: int,
    cache_dir: Path,
    work_dir: Path,
    fact_prep_unit_chunk_size: int,
) -> tuple[int, dict[str, Any]]:
    from src.ingestion.fact_extractor import prepare_fact_batch_requests_chunked
    from src.ingestion.openai_batch_pipeline import append_jsonl

    jsonl_path = work_dir / "fact_requests.jsonl"
    manifest_path = work_dir / "fact_extraction_manifest.json"
    jsonl_path.unlink(missing_ok=True)

    fact_manifest: dict[str, Any] = {}
    total_lines = 0
    total_units = len(all_units)
    processed_units = 0
    batch_index = 0
    started = time.perf_counter()
    chunk_size = max(1, fact_prep_unit_chunk_size)

    print(
        f"\nPreparing fact batch requests in streaming chunks "
        f"(units={total_units}, chunk_size={chunk_size})",
        flush=True,
    )

    for chunk_start in range(0, total_units, chunk_size):
        chunk_end = min(total_units, chunk_start + chunk_size)
        chunk_units = all_units[chunk_start:chunk_end]
        chunk_started = time.perf_counter()
        chunk_lines, chunk_manifest, batch_index = prepare_fact_batch_requests_chunked(
            chunk_units,
            entities=entities,
            model=fact_model,
            batch_size=batch_size,
            cache_dir=cache_dir,
            custom_id_prefix="fact_batch",
            batch_index_start=batch_index,
        )
        append_jsonl(jsonl_path, chunk_lines)
        fact_manifest.update(chunk_manifest)
        _write_json(manifest_path, fact_manifest)

        processed_units += len(chunk_units)
        total_lines += len(chunk_lines)
        chunk_misses = sum(len(spec.get("entries", [])) for spec in chunk_manifest.values())
        elapsed_chunk = time.perf_counter() - chunk_started
        elapsed_total = time.perf_counter() - started
        print(
            "  Fact prep chunk "
            f"{chunk_start + 1}-{chunk_end}/{total_units}: "
            f"misses={chunk_misses}, "
            f"lines_emitted={len(chunk_lines)}, "
            f"lines_total={total_lines}, "
            f"elapsed_chunk={elapsed_chunk:.2f}s, "
            f"elapsed_total={elapsed_total:.2f}s, "
            f"rss_mb={_rss_mb():.1f}, "
            f"jsonl_bytes={_path_size_bytes(jsonl_path)}, "
            f"manifest_bytes={_path_size_bytes(manifest_path)}",
            flush=True,
        )

    print(
        f"  Fact prep complete: units={processed_units}/{total_units}, "
        f"lines={total_lines}, manifest_entries={len(fact_manifest)}, "
        f"elapsed={time.perf_counter() - started:.2f}s, rss_mb={_rss_mb():.1f}",
        flush=True,
    )
    return total_lines, fact_manifest


def _load_model_id(role: str = "structured_generation", fallback: str = "fast_smart") -> str:
    policy_path = Path(__file__).resolve().parents[1] / "MODEL_POLICY.json"
    if not policy_path.exists():
        return fallback
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    actions = payload.get("actions", {})
    models = payload.get("models", {})
    r = actions.get(role, fallback)
    return models.get(r, r)


def _notify(title: str, message: str, *, skip: bool = False) -> None:
    if skip:
        return
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", title, message],
                timeout=5,
                check=False,
            )
        except Exception:
            pass
    print(f"[notify] {title}: {message}", flush=True)


def _resolve_paths(
    corpus_root: Path,
    paths_file: Path | None,
    limit: int,
) -> list[Path]:
    if paths_file:
        raw_lines = paths_file.read_text(encoding="utf-8").splitlines()
        rels: list[str] = []
        for line in raw_lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            rels.append(s)
        paths: list[Path] = []
        for rel in rels:
            p = Path(rel)
            path = p.resolve() if p.is_absolute() else (corpus_root / rel).resolve()
            if not path.is_file():
                print(f"Error: path from --paths-file not found: {path}", file=sys.stderr)
                sys.exit(1)
            paths.append(path)
    else:
        paths = sorted(corpus_root.rglob("*.md"))

    if limit > 0:
        paths = paths[:limit]
    return paths


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

STAGES = [
    "entity_submitted",
    "entity_complete",
    "fact_submitted",
    "fact_complete",
    "ready",
]


def _save_manifest(manifest: dict[str, Any], path: Path) -> None:
    manifest["updated_at"] = _utc_now_iso()
    _write_json(path, manifest)


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"Error: manifest not found: {path}", file=sys.stderr)
        sys.exit(1)
    return _read_json(path)


# ---------------------------------------------------------------------------
# Phase 1: --submit
# ---------------------------------------------------------------------------

def cmd_submit(args: argparse.Namespace) -> int:
    from openai import OpenAI

    from src.ingestion.chunker import chunk_document
    from src.ingestion.entity_extractor import (
        _load_fast_smart_model_id,
        prepare_entity_batch_requests,
    )
    from src.ingestion.fact_extractor import (
        _load_model_id as _load_fact_model_id,
    )
    from src.ingestion.frontmatter import load_document_frontmatter
    from src.ingestion.openai_batch_pipeline import write_jsonl

    corpus_root = args.corpus_root.resolve()
    if not corpus_root.is_dir():
        print(f"Error: corpus root not found: {corpus_root}", file=sys.stderr)
        return 1

    store_dir = args.store.resolve()
    store_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = store_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    work_dir = store_dir / "logs" / "corpus_batch"
    work_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = work_dir / "corpus_batch_manifest.json"
    if manifest_path.exists() and not args.force:
        existing = _read_json(manifest_path)
        stage = existing.get("stage", "")
        if stage not in ("ready", ""):
            print(
                f"Error: manifest already exists at stage '{stage}'. "
                f"Use --force to overwrite or --poll / --complete to continue.",
                file=sys.stderr,
            )
            return 1

    entity_model = _load_fast_smart_model_id()
    fact_model = _load_fact_model_id()
    paths = _resolve_paths(corpus_root, args.paths_file, args.limit)

    if not paths:
        print("Error: no markdown files found.", file=sys.stderr)
        return 1

    print(f"Corpus-wide batch submit: {len(paths)} files from {corpus_root}")

    from src.ingestion.source_anchor import resolve_git_commit_sha

    commit_sha = resolve_git_commit_sha(cwd=corpus_root)

    all_units: list[dict[str, Any]] = []
    file_records: list[dict[str, Any]] = []

    for i, source_path in enumerate(paths, 1):
        try:
            metadata, _body = load_document_frontmatter(source_path)
        except Exception as exc:
            print(f"  [{i}/{len(paths)}] SKIP {source_path.name}: frontmatter error: {exc}")
            continue

        if metadata is not None:
            md = metadata.to_dict()
            canon_layer = str(md["canon_layer"])
            campaign_id = str(md["campaign_id"]) if md.get("campaign_id") is not None else None
            source_class = str(md["source_class"])
            title = str(md["title"])
        else:
            canon_layer = "world"
            campaign_id = None
            source_class = "seed_reference"
            title = source_path.stem.replace("_", " ").replace("-", " ").title()

        document_id = f"doc_{_snake_case(source_path.stem)}"
        source_fingerprint = _file_sha256(source_path)

        rel = (
            str(source_path.relative_to(corpus_root).as_posix())
            if source_path.is_relative_to(corpus_root)
            else source_path.as_posix()
        )
        try:
            units = chunk_document(
                docx_path=source_path,
                document_id=document_id,
                document_title=title,
                canon_layer=canon_layer,
                campaign_id=campaign_id,
                source_class=source_class,
                corpus_source_path=rel,
                commit_sha=commit_sha,
            )
        except Exception as exc:
            print(f"  [{i}/{len(paths)}] SKIP {source_path.name}: chunking error: {exc}")
            continue

        print(f"  [{i}/{len(paths)}] {source_path.name}: {len(units)} units")
        all_units.extend(units)

        file_records.append({
            "source_path": str(source_path),
            "relative_path": rel,
            "document_id": document_id,
            "canon_layer": canon_layer,
            "campaign_id": campaign_id,
            "source_class": source_class,
            "title": title,
            "source_fingerprint": source_fingerprint,
            "evidence_unit_count": len(units),
        })

    if not all_units:
        print("Error: no evidence units produced from any file.", file=sys.stderr)
        return 1

    print(f"\nTotal: {len(all_units)} evidence units from {len(file_records)} files")

    lines, entity_manifest = prepare_entity_batch_requests(
        all_units,
        known_entities=[],
        model=entity_model,
        batch_size=args.batch_size,
        cache_dir=cache_dir,
    )

    _write_json(work_dir / "entity_extraction_manifest.json", entity_manifest)

    manifest: dict[str, Any] = {
        "version": 1,
        "created_at": _utc_now_iso(),
        "store_dir": str(store_dir),
        "corpus_root": str(corpus_root),
        "entity_model": entity_model,
        "fact_model": fact_model,
        "batch_size": args.batch_size,
        "files": file_records,
        "cache_dir": str(cache_dir),
        "work_dir": str(work_dir),
        "entity_batch": None,
        "fact_batch": None,
    }

    if not lines:
        print("All entity requests are cache hits — skipping submission.")
        manifest["stage"] = "entity_complete"
        _save_manifest(manifest, manifest_path)
        print(f"Manifest: {manifest_path}")
        print("Run --poll to prepare and submit fact batch.")
        return 0

    jsonl_path = work_dir / "entity_requests.jsonl"
    write_jsonl(jsonl_path, lines)

    api_key = _get_api_key()
    client = OpenAI(api_key=api_key)

    with jsonl_path.open("rb") as fh:
        batch_file = client.files.create(file=fh, purpose="batch")

    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
    )

    manifest["entity_batch"] = {
        "batch_id": batch.id,
        "input_file_id": batch_file.id,
        "request_count": len(lines),
        "submitted_at": _utc_now_iso(),
        "status": batch.status,
        "output_file": None,
    }
    manifest["stage"] = "entity_submitted"
    _save_manifest(manifest, manifest_path)

    print(f"\nEntity batch submitted: {batch.id} ({len(lines)} requests)")
    print(f"Manifest: {manifest_path}")
    return 0


def _get_api_key() -> str:
    import os

    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[1]
    for candidate in [project_root / ".env", project_root.parent / ".env"]:
        if candidate.exists():
            load_dotenv(candidate)
            break

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
        sys.exit(1)
    return key


# ---------------------------------------------------------------------------
# Phase 2: --poll
# ---------------------------------------------------------------------------

def cmd_poll(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    no_notify = getattr(args, "no_notify", False)
    poll_interval = getattr(args, "poll_interval", 300)

    while True:
        stage = manifest.get("stage", "")

        if stage == "entity_submitted":
            rc = _poll_batch(
                manifest,
                manifest_path,
                batch_key="entity_batch",
                next_stage="entity_complete",
                label="Entity",
                poll_interval=poll_interval,
                no_notify=no_notify,
            )
            if rc != 0:
                return rc
            manifest = _load_manifest(manifest_path)
            continue

        if stage == "entity_complete":
            rc = _transition_entity_to_fact(
                manifest,
                manifest_path,
                schema_repair_batch=not getattr(args, "no_schema_repair_batch", False),
                schema_repair_model=getattr(args, "schema_repair_model", "gpt-5.4"),
                schema_repair_poll_interval=float(getattr(args, "schema_repair_poll_interval", 30.0)),
                transition_unit_chunk_size=int(getattr(args, "transition_unit_chunk_size", 300)),
                transition_chunk_pause_ms=int(getattr(args, "transition_chunk_pause_ms", 0)),
            )
            if rc != 0:
                return rc
            manifest = _load_manifest(manifest_path)
            continue

        if stage == "fact_submitted":
            rc = _poll_batch(
                manifest,
                manifest_path,
                batch_key="fact_batch",
                next_stage="ready",
                label="Fact",
                poll_interval=poll_interval,
                no_notify=no_notify,
            )
            if rc != 0:
                return rc
            manifest = _load_manifest(manifest_path)
            if manifest.get("stage") == "ready":
                _notify(
                    "DungeonMindBuddy",
                    "Fact batch complete — run --complete",
                    skip=no_notify,
                )
                print("\nAll batches complete. Run --complete to finalize into store.")
                return 0
            continue

        if stage == "fact_complete" or stage == "ready":
            print("All batches complete. Run --complete to finalize into store.")
            return 0

        print(f"Error: unknown stage '{stage}'", file=sys.stderr)
        return 1


def _poll_batch(
    manifest: dict[str, Any],
    manifest_path: Path,
    *,
    batch_key: str,
    next_stage: str,
    label: str,
    poll_interval: float,
    no_notify: bool,
) -> int:
    from openai import OpenAI

    from src.ingestion.openai_batch_pipeline import read_jsonl_bytes

    batch_info = manifest.get(batch_key)
    if not batch_info:
        print(f"Error: no {batch_key} in manifest.", file=sys.stderr)
        return 1

    batch_id = batch_info["batch_id"]
    api_key = _get_api_key()
    client = OpenAI(api_key=api_key)

    terminal = {"completed", "failed", "expired", "cancelled"}

    while True:
        b = client.batches.retrieve(batch_id)
        status = b.status

        if b.request_counts is not None:
            rc = b.request_counts
            print(
                f"  {label} batch {batch_id}: status={status} "
                f"completed={rc.completed} failed={rc.failed} total={rc.total}",
                flush=True,
            )
        else:
            print(f"  {label} batch {batch_id}: status={status}", flush=True)

        if status in terminal:
            break

        time.sleep(poll_interval)

    if status != "completed":
        print(f"Error: {label} batch {status}: {batch_id}", file=sys.stderr)
        work_dir = Path(manifest["work_dir"])
        _write_json(work_dir / f"{batch_key}_error.json", {
            "batch_id": batch_id,
            "status": status,
            "timestamp": _utc_now_iso(),
        })
        return 1

    work_dir = Path(manifest["work_dir"])
    cache_dir = Path(manifest["cache_dir"])

    output_file = None
    if b.output_file_id:
        content = client.files.content(b.output_file_id)
        raw = content.read()
        output_path = work_dir / f"{batch_key}_output.jsonl"
        output_path.write_bytes(raw)
        output_rows = read_jsonl_bytes(raw)
        output_file = str(output_path)
    else:
        output_rows = []

    if b.error_file_id:
        err_content = client.files.content(b.error_file_id)
        err_raw = err_content.read()
        (work_dir / f"{batch_key}_errors.jsonl").write_bytes(err_raw)

    if batch_key == "entity_batch":
        from src.ingestion.entity_extractor import apply_entity_batch_outputs_to_cache

        entity_manifest_data = _read_json(work_dir / "entity_extraction_manifest.json")
        fails, usage = apply_entity_batch_outputs_to_cache(
            output_rows,
            entity_manifest_data,
            model_id=manifest["entity_model"],
            cache_dir=cache_dir,
        )
        if fails:
            print(f"  Warning: {len(fails)} entity batch row(s) failed: {fails[:5]}")
        print(f"  Entity cache updated. Usage: {usage}")

    elif batch_key == "fact_batch":
        from src.ingestion.fact_extractor import apply_fact_batch_outputs_to_cache

        fact_manifest_data = _read_json(work_dir / "fact_extraction_manifest.json")
        fails, usage = apply_fact_batch_outputs_to_cache(
            output_rows,
            fact_manifest_data,
            model_id=manifest["fact_model"],
            cache_dir=cache_dir,
        )
        if fails:
            print(f"  Warning: {len(fails)} fact batch row(s) failed: {fails[:5]}")
        print(f"  Fact cache updated. Usage: {usage}")

    batch_info["status"] = status
    batch_info["output_file"] = output_file
    manifest["stage"] = next_stage
    _save_manifest(manifest, manifest_path)

    _notify("DungeonMindBuddy", f"{label} batch complete", skip=no_notify)
    return 0


def _transition_entity_to_fact(
    manifest: dict[str, Any],
    manifest_path: Path,
    *,
    schema_repair_batch: bool = True,
    schema_repair_model: str = "gpt-5.4",
    schema_repair_poll_interval: float = 30.0,
    transition_unit_chunk_size: int = 300,
    transition_chunk_pause_ms: int = 0,
) -> int:
    """Run entity extraction from cache, then prepare+submit fact batch."""
    from openai import OpenAI

    cache_dir = Path(manifest["cache_dir"])
    work_dir = Path(manifest["work_dir"])
    entity_model = manifest["entity_model"]
    fact_model = manifest["fact_model"]
    batch_size = manifest["batch_size"]

    print("\nRunning entity extraction from cache...")

    all_units = _build_units_from_manifest(manifest)
    entities = _extract_entities_for_units(
        units=all_units,
        cache_dir=cache_dir,
        work_dir=work_dir,
        model=entity_model,
        batch_size=batch_size,
        schema_repair_batch=schema_repair_batch,
        schema_repair_model=schema_repair_model,
        schema_repair_poll_interval=schema_repair_poll_interval,
        transition_unit_chunk_size=transition_unit_chunk_size,
        transition_chunk_pause_ms=transition_chunk_pause_ms,
    )

    line_count, _ = _prepare_fact_requests_streaming(
        all_units=all_units,
        entities=entities,
        fact_model=fact_model,
        batch_size=batch_size,
        cache_dir=cache_dir,
        work_dir=work_dir,
        fact_prep_unit_chunk_size=transition_unit_chunk_size,
    )

    if line_count == 0:
        print("All fact requests are cache hits — skipping submission.")
        manifest["stage"] = "ready"
        _save_manifest(manifest, manifest_path)
        return 0

    jsonl_path = work_dir / "fact_requests.jsonl"

    api_key = _get_api_key()
    client = OpenAI(api_key=api_key)

    with jsonl_path.open("rb") as fh:
        batch_file = client.files.create(file=fh, purpose="batch")

    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
    )

    manifest["fact_batch"] = {
        "batch_id": batch.id,
        "input_file_id": batch_file.id,
        "request_count": line_count,
        "submitted_at": _utc_now_iso(),
        "status": batch.status,
        "output_file": None,
    }
    manifest["stage"] = "fact_submitted"
    _save_manifest(manifest, manifest_path)

    print(f"\nFact batch submitted: {batch.id} ({line_count} requests)")
    return 0


def cmd_transition_debug(args: argparse.Namespace) -> int:
    """Run local transition steps in isolation to diagnose lockups."""
    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    stage = manifest.get("stage", "")

    cache_dir = Path(manifest["cache_dir"])
    work_dir = Path(manifest["work_dir"])
    entity_model = manifest["entity_model"]
    fact_model = manifest["fact_model"]
    batch_size = manifest["batch_size"]

    print(f"Transition debug manifest: {manifest_path}")
    print(f"Manifest stage: {stage}")
    print(f"Debug step: {args.debug_step}")
    print(
        f"Limits: files={args.debug_file_limit or 'all'}, "
        f"units={args.debug_unit_limit or 'all'}, "
        f"transition_chunk={args.transition_unit_chunk_size}"
    )

    all_units = _build_units_from_manifest(
        manifest,
        file_limit=max(0, int(args.debug_file_limit)),
        unit_limit=max(0, int(args.debug_unit_limit)),
    )
    if args.debug_step == "chunk":
        print("Debug step complete: chunk")
        return 0

    entities = _extract_entities_for_units(
        units=all_units,
        cache_dir=cache_dir,
        work_dir=work_dir,
        model=entity_model,
        batch_size=batch_size,
        schema_repair_batch=not args.no_schema_repair_batch,
        schema_repair_model=args.schema_repair_model,
        schema_repair_poll_interval=args.schema_repair_poll_interval,
        transition_unit_chunk_size=args.transition_unit_chunk_size,
        transition_chunk_pause_ms=args.transition_chunk_pause_ms,
    )
    if args.debug_step == "entity":
        print("Debug step complete: entity")
        return 0

    started = time.perf_counter()
    line_count, fact_manifest_data = _prepare_fact_requests_streaming(
        all_units=all_units,
        entities=entities,
        fact_model=fact_model,
        batch_size=batch_size,
        cache_dir=cache_dir,
        work_dir=work_dir,
        fact_prep_unit_chunk_size=args.transition_unit_chunk_size,
    )
    elapsed = time.perf_counter() - started
    print(
        f"Fact prep complete: lines={line_count} "
        f"manifest_entries={len(fact_manifest_data)} "
        f"elapsed={elapsed:.2f}s"
    )
    print("Debug step complete: fact")
    return 0


# ---------------------------------------------------------------------------
# Phase 3: --complete
# ---------------------------------------------------------------------------

def cmd_complete(args: argparse.Namespace) -> int:
    from src.ingestion.chunker import chunk_document
    from src.ingestion.entity_extractor import run_entity_extraction
    from src.ingestion.fact_extractor import run_fact_extraction
    from src.ingestion.source_anchor import resolve_git_commit_sha
    from src.store import FactStore

    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    stage = manifest.get("stage", "")

    if stage != "ready":
        print(
            f"Error: manifest stage is '{stage}', expected 'ready'. Run --poll first.",
            file=sys.stderr,
        )
        return 1

    store_dir = Path(manifest["store_dir"])
    cache_dir = Path(manifest["cache_dir"])
    entity_model = manifest["entity_model"]
    fact_model = manifest["fact_model"]
    batch_size = manifest["batch_size"]

    store = FactStore(store_dir)
    if store._path("entities").exists():
        store.load()

    corpus_root = Path(str(manifest.get("corpus_root", ".")))
    commit_sha = resolve_git_commit_sha(cwd=corpus_root)

    totals = {
        "files": 0,
        "evidence_units": 0,
        "entities": 0,
        "facts": 0,
        "event_records": 0,
        "claims": 0,
    }

    print(f"\nFinalizing {len(manifest['files'])} files into store at {store_dir}")

    for i, fr in enumerate(manifest["files"], 1):
        source_path = Path(fr["source_path"])
        print(f"  [{i}/{len(manifest['files'])}] {fr['relative_path']}...", end="", flush=True)

        corpus_source_path = Path(str(fr.get("relative_path", source_path.name))).as_posix()
        units = chunk_document(
            docx_path=source_path,
            document_id=fr["document_id"],
            document_title=fr["title"],
            canon_layer=fr["canon_layer"],
            campaign_id=fr["campaign_id"],
            source_class=fr["source_class"],
            corpus_source_path=corpus_source_path,
            commit_sha=commit_sha,
        )

        recap_artifacts: dict[str, list[dict[str, Any]]] = {
            "event_records": [],
            "claims": [],
        }
        entity_result = run_entity_extraction(
            units,
            known_entities=store.list_entities(),
            model=entity_model,
            batch_size=batch_size,
            cache_dir=cache_dir,
            openai_client=None,
            allow_heuristic_fallback=False,
            recap_artifacts=recap_artifacts,
            schema_repair_batch=not args.no_schema_repair_batch,
            schema_repair_model=args.schema_repair_model,
            schema_repair_poll_interval=args.schema_repair_poll_interval,
            schema_repair_work_dir=Path(manifest["work_dir"]) / "schema_repair",
        )
        entities = entity_result["entities"]

        fact_result = run_fact_extraction(
            units,
            entities=entities,
            canon_layer=fr["canon_layer"],
            campaign_id=fr["campaign_id"],
            source_class=fr["source_class"],
            model=fact_model,
            batch_size=batch_size,
            cache_dir=cache_dir,
            openai_client=None,
            allow_heuristic_fallback=False,
        )
        facts = fact_result["facts"]

        store.add_evidence_units(units)
        store.add_entities(entities)
        store.add_facts(facts)
        if recap_artifacts["event_records"]:
            store.add_event_records(recap_artifacts["event_records"])
        if recap_artifacts["claims"]:
            store.add_claims(recap_artifacts["claims"])

        ingest_key = (
            f"{fr['source_fingerprint']}|layer={fr['canon_layer']}"
            f"|campaign={fr['campaign_id']}|source_class={fr['source_class']}"
        )
        store.record_ingest_fingerprint(
            ingest_key,
            {
                "source_path": fr["source_path"],
                "layer": fr["canon_layer"],
                "campaign_id": fr["campaign_id"],
                "source_class": fr["source_class"],
                "document_id": fr["document_id"],
                "recorded_at": _utc_now_iso(),
                "source_fingerprint": fr["source_fingerprint"],
            },
        )

        totals["files"] += 1
        totals["evidence_units"] += len(units)
        totals["entities"] += len(entities)
        totals["facts"] += len(facts)
        totals["event_records"] += len(recap_artifacts["event_records"])
        totals["claims"] += len(recap_artifacts["claims"])

        print(f" {len(entities)} entities, {len(facts)} facts")

    store.save()

    manifest["stage"] = "finalized"
    _save_manifest(manifest, manifest_path)

    print("\n" + "=" * 60)
    print("Corpus batch complete!")
    print(f"  Files:           {totals['files']}")
    print(f"  Evidence units:  {totals['evidence_units']}")
    print(f"  Entities:        {totals['entities']} (deduplicated in store: {len(store.entities)})")
    print(f"  Facts:           {totals['facts']}")
    print(f"  Event records:   {totals['event_records']}")
    print(f"  Claims:          {totals['claims']}")
    print(f"  Store:           {store_dir}")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# --status (one-shot check)
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    stage = manifest.get("stage", "unknown")

    print(f"Manifest: {manifest_path}")
    print(f"Stage:    {stage}")
    print(f"Files:    {len(manifest.get('files', []))}")
    print(f"Store:    {manifest.get('store_dir', 'N/A')}")

    if stage in ("entity_submitted", "entity_complete") and manifest.get("entity_batch"):
        eb = manifest["entity_batch"]
        print("\nEntity batch:")
        print(f"  batch_id:      {eb.get('batch_id', 'N/A')}")
        print(f"  request_count: {eb.get('request_count', 'N/A')}")
        print(f"  submitted_at:  {eb.get('submitted_at', 'N/A')}")

        if stage == "entity_submitted":
            _print_live_batch_status(eb.get("batch_id"))

    if stage in ("fact_submitted", "fact_complete", "ready") and manifest.get("fact_batch"):
        fb = manifest["fact_batch"]
        print("\nFact batch:")
        print(f"  batch_id:      {fb.get('batch_id', 'N/A')}")
        print(f"  request_count: {fb.get('request_count', 'N/A')}")
        print(f"  submitted_at:  {fb.get('submitted_at', 'N/A')}")

        if stage == "fact_submitted":
            _print_live_batch_status(fb.get("batch_id"))

    if stage == "ready":
        print("\nReady for --complete.")
    elif stage == "finalized":
        print("\nAlready finalized.")

    return 0


def _print_live_batch_status(batch_id: str | None) -> None:
    if not batch_id:
        return
    try:
        from openai import OpenAI

        api_key = _get_api_key()
        client = OpenAI(api_key=api_key)
        b = client.batches.retrieve(batch_id)
        status = b.status
        if b.request_counts is not None:
            rc = b.request_counts
            print(
                f"  [live] status={status} completed={rc.completed} "
                f"failed={rc.failed} total={rc.total}"
            )
        else:
            print(f"  [live] status={status}")
    except Exception as exc:
        print(f"  [live] could not retrieve: {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corpus-wide OpenAI Batch API pipeline (submit / poll / complete)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--submit", action="store_true", help="Submit entity batch for corpus")
    group.add_argument("--poll", metavar="MANIFEST", help="Poll batch status and advance stages")
    group.add_argument("--complete", metavar="MANIFEST", help="Finalize cached results into store")
    group.add_argument("--status", metavar="MANIFEST", help="One-shot status check")
    group.add_argument(
        "--transition-debug",
        metavar="MANIFEST",
        help="Run local transition diagnostics (chunk/entity/fact) without manifest mutation",
    )

    parser.add_argument(
        "--store",
        type=Path,
        default=Path("out/stores/batch_api_full_corpus"),
        help="Fact store directory (default: out/stores/batch_api_full_corpus)",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path("corpus/eldyrwild-markdown"),
        help="Root directory to scan for *.md",
    )
    parser.add_argument(
        "--paths-file",
        type=Path,
        default=None,
        help="Text file with one markdown path per line (relative to --corpus-root or absolute)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max files (0 = all)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Evidence units per LLM request (default: 5)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing manifest / ignore cache",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        help="Seconds between status checks during --poll (default: 300)",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Skip desktop notifications",
    )
    parser.add_argument(
        "--no-schema-repair-batch",
        action="store_true",
        help="Do not run gpt-5.4 Batch repair when entity records fail JSON Schema validation",
    )
    parser.add_argument(
        "--schema-repair-model",
        default="gpt-5.4",
        help="Model for entity schema repair batch (default: gpt-5.4)",
    )
    parser.add_argument(
        "--schema-repair-poll-interval",
        type=float,
        default=30.0,
        help="Seconds between repair batch status polls (default: 30)",
    )
    parser.add_argument(
        "--transition-unit-chunk-size",
        type=int,
        default=300,
        help="Units per chunk during entity->fact transition in --poll (default: 300)",
    )
    parser.add_argument(
        "--transition-chunk-pause-ms",
        type=int,
        default=0,
        help="Sleep between transition chunks to reduce UI lock risk (default: 0)",
    )
    parser.add_argument(
        "--debug-step",
        choices=["chunk", "entity", "fact"],
        default="fact",
        help="Step to run with --transition-debug (default: fact)",
    )
    parser.add_argument(
        "--debug-file-limit",
        type=int,
        default=0,
        help="Limit files loaded from manifest during --transition-debug (0 = all)",
    )
    parser.add_argument(
        "--debug-unit-limit",
        type=int,
        default=0,
        help="Limit units after chunking during --transition-debug (0 = all)",
    )

    args = parser.parse_args()

    if args.submit:
        return cmd_submit(args)
    elif args.poll:
        args.manifest = args.poll
        return cmd_poll(args)
    elif args.transition_debug:
        args.manifest = args.transition_debug
        return cmd_transition_debug(args)
    elif args.complete:
        args.manifest = args.complete
        return cmd_complete(args)
    elif args.status:
        args.manifest = args.status
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
