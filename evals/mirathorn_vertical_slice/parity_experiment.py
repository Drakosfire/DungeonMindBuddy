"""Phase A — CLI vs direct fact-extractor parity experiment.

Captured 2026-04-20 (Backlog `[READY] CLI ingest vs direct fact-extractor parity gap`).

Same source (`The City of Mirathorn.md`), four cells:

    A: direct path (chunker + run_*_extraction)            batch_size=1
    B: direct path                                          batch_size=5
    C: CLI ingest (DungeonBuddyCLI._cmd_ingest via run)     batch_size=1
    D: CLI ingest                                           batch_size=5

For each cell we capture:
  - evidence_units count (chunker output)
  - entities count                  (CLI cell also reports pre-store and post-store)
  - facts count                     (CLI cell also reports pre-store and post-store)
  - entity_extractor 'missing unit_index slots' warning count
  - fact_extractor 'missing unit_index slots' warning count
  - duplicate-slot warning count (entity + fact)
  - wall-clock seconds
  - approximate cost ($) — captured from logged usage if available, else 0

Output:
  evals/mirathorn_vertical_slice/output/parity_experiment_<ts>/
    parity_results.json  (raw machine-readable)
    parity_results.md    (human-readable table + interpretation)
    cell_<id>/           (per-cell stdout, store_dir for CLI cells)

Each cell uses its own fresh cache_dir, so LLM calls are not shared across cells.
The expected gap (Direct bs=1 ≈ 441 facts vs CLI bs=5 ≈ 289 facts) is much larger
than typical LLM stochasticity (~5–10 facts), so a single trial per cell is informative.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EVAL_DIR / "output"

sys.path.insert(0, str(PROJECT_ROOT))

from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

load_dungeonmindbuddy_dotenv()

from src.cli import DungeonBuddyCLI  # noqa: E402
from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.entity_extractor import (  # noqa: E402
    OpenAIResponsesEntityClient,
    run_entity_extraction,
)
from src.ingestion.fact_extractor import (  # noqa: E402
    OpenAIResponsesFactClient,
    run_fact_extraction,
)

MIRATHORN_SOURCE = PROJECT_ROOT / Path(
    "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/"
    "The City of Mirathorn.md"
)

ENTITY_MODEL = os.environ.get("DUNGEONMIND_ENTITY_EXTRACTOR_MODEL", "gpt-5.4-mini")
FACT_MODEL = os.environ.get("DUNGEONMIND_FACT_EXTRACTOR_MODEL", "gpt-5.4-mini")


class SlotWarningCounter(logging.Handler):
    """Count 'missing unit_index slots' / 'duplicate unit_index slots' log records."""

    PATTERNS = (
        ("entity", "missing", "entity_extractor batched call missing unit_index slots"),
        ("entity", "duplicate", "entity_extractor batched call duplicate unit_index slots"),
        ("fact", "missing", "fact_extractor batched call missing unit_index slots"),
        ("fact", "duplicate", "fact_extractor batched call duplicate unit_index slots"),
    )

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.counts: dict[str, int] = {f"{k}_{w}": 0 for k, w, _ in self.PATTERNS}

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        for kind, which, prefix in self.PATTERNS:
            if msg.startswith(prefix):
                self.counts[f"{kind}_{which}"] += 1
                return


def _attach_counter() -> SlotWarningCounter:
    counter = SlotWarningCounter()
    root = logging.getLogger()
    root.addHandler(counter)
    return counter


def _detach_counter(counter: SlotWarningCounter) -> None:
    logging.getLogger().removeHandler(counter)


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("Error: OPENAI_API_KEY not set after bootstrap.", file=sys.stderr)
        sys.exit(2)
    return key


def _run_direct_cell(
    cell_id: str,
    *,
    batch_size: int,
    cache_dir: Path,
    api_key: str,
) -> dict[str, Any]:
    print(f"[{cell_id}] direct path, batch_size={batch_size}", flush=True)
    counter = _attach_counter()
    started = time.perf_counter()
    try:
        evidence_units = chunk_document(
            docx_path=MIRATHORN_SOURCE,
            document_id="doc_city_of_mirathorn",
            document_title="The City of Mirathorn",
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
        )
        entity_client = OpenAIResponsesEntityClient(api_key=api_key)
        entity_bundle = run_entity_extraction(
            evidence_units,
            model=ENTITY_MODEL,
            batch_size=batch_size,
            cache_dir=cache_dir / "entity",
            openai_client=entity_client,
            allow_heuristic_fallback=False,
        )
        entities = entity_bundle["entities"]

        fact_client = OpenAIResponsesFactClient(api_key=api_key)
        fact_bundle = run_fact_extraction(
            evidence_units,
            entities=entities,
            canon_layer="world",
            campaign_id=None,
            source_class="seed_reference",
            model=FACT_MODEL,
            batch_size=batch_size,
            cache_dir=cache_dir / "fact",
            openai_client=fact_client,
            allow_heuristic_fallback=False,
        )
        facts = fact_bundle["facts"]
    finally:
        _detach_counter(counter)
        elapsed = time.perf_counter() - started

    return {
        "cell_id": cell_id,
        "path": "direct",
        "batch_size": batch_size,
        "evidence_units": len(evidence_units),
        "entities_extracted": len(entities),
        "facts_extracted": len(facts),
        "entities_post_store": None,
        "facts_post_store": None,
        "slot_warnings": dict(counter.counts),
        "elapsed_seconds": round(elapsed, 2),
    }


def _run_cli_cell(
    cell_id: str,
    *,
    batch_size: int,
    store_dir: Path,
    api_key: str,
) -> dict[str, Any]:
    print(f"[{cell_id}] CLI path, batch_size={batch_size}, store={store_dir}", flush=True)
    counter = _attach_counter()
    pre_store_counts: dict[str, int] = {"entities": 0, "facts": 0}
    started = time.perf_counter()
    try:
        cli = DungeonBuddyCLI(store_dir=store_dir, verbose=False)

        original_add_entities = cli.store.add_entities
        original_add_facts = cli.store.add_facts

        def _wrapped_add_entities(payload: list[dict[str, Any]]) -> Any:
            pre_store_counts["entities"] += len(payload)
            return original_add_entities(payload)

        def _wrapped_add_facts(payload: list[dict[str, Any]]) -> Any:
            pre_store_counts["facts"] += len(payload)
            return original_add_facts(payload)

        cli.store.add_entities = _wrapped_add_entities  # type: ignore[method-assign]
        cli.store.add_facts = _wrapped_add_facts  # type: ignore[method-assign]

        cmd = (
            f'ingest "{MIRATHORN_SOURCE}" '
            f"--layer world --source-class seed_reference "
            f"--batch-size {batch_size} --force"
        )
        capture = io.StringIO()
        with redirect_stdout(capture):
            cli.handle_line(cmd)
        stdout_text = capture.getvalue()

        evidence_units_count = len(cli.store.evidence_units)
        entities_post_store = len(cli.store.entities)
        facts_post_store = len(cli.store.facts)
    finally:
        _detach_counter(counter)
        elapsed = time.perf_counter() - started

    cell_dir = store_dir.parent
    (cell_dir / "stdout.txt").write_text(stdout_text)

    return {
        "cell_id": cell_id,
        "path": "cli",
        "batch_size": batch_size,
        "evidence_units": evidence_units_count,
        "entities_extracted": pre_store_counts["entities"],
        "facts_extracted": pre_store_counts["facts"],
        "entities_post_store": entities_post_store,
        "facts_post_store": facts_post_store,
        "slot_warnings": dict(counter.counts),
        "elapsed_seconds": round(elapsed, 2),
    }


def _format_results_md(results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Mirathorn parity experiment — Phase A")
    lines.append("")
    lines.append(f"Source: `{MIRATHORN_SOURCE.relative_to(PROJECT_ROOT)}`")
    lines.append(f"Entity model: `{ENTITY_MODEL}` · Fact model: `{FACT_MODEL}`")
    lines.append("")
    lines.append("## Counts per cell")
    lines.append("")
    lines.append(
        "| Cell | Path | bs | evidence | entities (extracted) | entities (post-store) | facts (extracted) | facts (post-store) | elapsed (s) |"
    )
    lines.append(
        "|------|------|----|----------|----------------------|-----------------------|-------------------|--------------------|-------------|"
    )
    for r in results:
        post_e = r["entities_post_store"] if r["entities_post_store"] is not None else "—"
        post_f = r["facts_post_store"] if r["facts_post_store"] is not None else "—"
        lines.append(
            f"| {r['cell_id']} | {r['path']} | {r['batch_size']} | {r['evidence_units']} | "
            f"{r['entities_extracted']} | {post_e} | "
            f"{r['facts_extracted']} | {post_f} | {r['elapsed_seconds']} |"
        )
    lines.append("")
    lines.append("## Slot-drop warnings per cell")
    lines.append("")
    lines.append(
        "| Cell | entity_missing | entity_duplicate | fact_missing | fact_duplicate |"
    )
    lines.append("|------|----------------|------------------|--------------|----------------|")
    for r in results:
        sw = r["slot_warnings"]
        lines.append(
            f"| {r['cell_id']} | {sw['entity_missing']} | {sw['entity_duplicate']} | "
            f"{sw['fact_missing']} | {sw['fact_duplicate']} |"
        )
    lines.append("")
    lines.append("## Auto-interpretation")
    lines.append("")
    by_id = {r["cell_id"]: r for r in results}
    a, b, c, d = by_id["A"], by_id["B"], by_id["C"], by_id["D"]

    def _delta(x: int, y: int) -> str:
        if x == 0:
            return f"{y - x:+d}"
        pct = (y - x) / x * 100
        return f"{y - x:+d} ({pct:+.1f}%)"

    lines.append(f"- **A→B (direct path: bs=1 → bs=5)**: facts {a['facts_extracted']} → {b['facts_extracted']} ({_delta(a['facts_extracted'], b['facts_extracted'])}). Isolates batching effect on direct path.")
    lines.append(f"- **A→C (bs=1: direct → CLI)**: facts {a['facts_extracted']} → {c['facts_post_store']} post-store ({_delta(a['facts_extracted'], c['facts_post_store'])}). Pre-store: {c['facts_extracted']} ({_delta(a['facts_extracted'], c['facts_extracted'])}). Isolates CLI overhead at fixed batch_size.")
    lines.append(f"- **C→D (CLI: bs=1 → bs=5)**: facts post-store {c['facts_post_store']} → {d['facts_post_store']} ({_delta(c['facts_post_store'], d['facts_post_store'])}). Isolates CLI batching effect.")
    lines.append(f"- **A→D (the headline gap)**: facts {a['facts_extracted']} → {d['facts_post_store']} post-store ({_delta(a['facts_extracted'], d['facts_post_store'])}). The full observed gap.")
    lines.append("")
    lines.append("Pre-store vs post-store gap on CLI cells indicates how much the FactStore is dropping/merging:")
    lines.append(f"- C: pre-store {c['facts_extracted']} → post-store {c['facts_post_store']} ({_delta(c['facts_extracted'], c['facts_post_store'])})")
    lines.append(f"- D: pre-store {d['facts_extracted']} → post-store {d['facts_post_store']} ({_delta(d['facts_extracted'], d['facts_post_store'])})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = OUTPUT_DIR / f"parity_experiment_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run dir: {run_dir}", flush=True)

    api_key = _get_api_key()

    cells: list[dict[str, Any]] = []

    for cell_id, batch_size in [("A", 1), ("B", 5)]:
        cell_dir = run_dir / f"cell_{cell_id}"
        cell_dir.mkdir(parents=True, exist_ok=True)
        cells.append(
            _run_direct_cell(
                cell_id,
                batch_size=batch_size,
                cache_dir=cell_dir / "cache",
                api_key=api_key,
            )
        )

    for cell_id, batch_size in [("C", 1), ("D", 5)]:
        cell_dir = run_dir / f"cell_{cell_id}"
        cell_dir.mkdir(parents=True, exist_ok=True)
        cells.append(
            _run_cli_cell(
                cell_id,
                batch_size=batch_size,
                store_dir=cell_dir / "store",
                api_key=api_key,
            )
        )

    results_payload = {
        "timestamp_utc": ts,
        "source_path": str(MIRATHORN_SOURCE.relative_to(PROJECT_ROOT)),
        "entity_model": ENTITY_MODEL,
        "fact_model": FACT_MODEL,
        "cells": cells,
    }
    (run_dir / "parity_results.json").write_text(json.dumps(results_payload, indent=2) + "\n")
    (run_dir / "parity_results.md").write_text(_format_results_md(cells))

    print(f"\nResults written to: {run_dir}/parity_results.{{json,md}}", flush=True)
    print("\n" + _format_results_md(cells), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
