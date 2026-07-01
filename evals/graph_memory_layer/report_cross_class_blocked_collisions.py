"""Generate the checked-in Graph Memory cross-class blocked collision report."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from src.graph_memory.diagnostics.cross_class_collision_report import (
    BlockedCollisionRecord,
    render_blocked_collision_markdown,
    summarize_blocked_collision_records,
)

ARTIFACT_ROOTS = [
    Path("evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood"),
    Path("evals/graph_memory_layer/artifacts/graph_ingest_runs"),
    Path("evals/graph_memory_layer/examples"),
    Path("out/graph_memory/runs"),
]

BED_NAMES = {
    "c1s1": "C1S1 Stonebridge / Glowkindle Rats",
    "stonebridge": "C1S1 Stonebridge / Glowkindle Rats",
    "mirathorn": "Mirathorn worldbuilding",
    "c2s23": "C2S23 Mireward Gate Battle",
    "session_23": "C2S23 Mireward Gate Battle",
    "c2s24": "C2S24 Mireward Gate Battle",
    "session_24": "C2S24 Mireward Gate Battle",
}

VARIANT_NAMES = ("edge_and_node_packet", "edge_packet", "node_packet", "baseline")


def _load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _derive_bed_id(path: Path, payload: Any | None = None) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("bed_id"), str):
        raw = payload["bed_id"]
        for token, bed in BED_NAMES.items():
            if token in raw.lower():
                return bed
        return raw
    text = str(path).lower()
    for token, bed in BED_NAMES.items():
        if token in text:
            return bed
    return "unknown"


def _derive_variant(path: Path, payload: Any | None = None) -> str:
    if isinstance(payload, dict):
        for key in ("variant", "variant_name", "name"):
            if isinstance(payload.get(key), str):
                return payload[key]
    text = str(path).lower()
    for name in VARIANT_NAMES:
        if name in text:
            return name
    return "unknown"


def _json_paths(inputs: list[Path]) -> tuple[list[Path], list[str], list[str]]:
    if inputs:
        return (sorted(dict.fromkeys(inputs)), [], [])
    found: list[Path] = []
    inspected: list[str] = []
    missing: list[str] = []
    for root in ARTIFACT_ROOTS:
        inspected.append(root.as_posix())
        if not root.exists():
            missing.append(root.as_posix())
            continue
        paths = sorted(root.rglob("*.json"))
        if not paths:
            missing.append(f"{root.as_posix()} (empty)")
        found.extend(paths)
    return (found, inspected, missing)


def _records_from_payload(path: Path, payload: Any) -> list[BlockedCollisionRecord]:
    if not isinstance(payload, dict):
        return []
    records: list[BlockedCollisionRecord] = []
    # Manual review bundles contain bed variants nested under beds[*].variants.
    beds = payload.get("beds")
    if isinstance(beds, list):
        for bed in beds:
            if not isinstance(bed, dict):
                continue
            bed_id = _derive_bed_id(path, bed)
            variants = bed.get("variants")
            if isinstance(variants, dict):
                for variant_name, variant_payload in variants.items():
                    if isinstance(variant_payload, dict):
                        records.extend(summarize_blocked_collision_records(
                            bed_id=bed_id,
                            variant=str(variant_name),
                            extraction_payload=variant_payload,
                        ))
    if records:
        return records
    return summarize_blocked_collision_records(
        bed_id=_derive_bed_id(path, payload),
        variant=_derive_variant(path, payload),
        extraction_payload=payload,
    )


def load_json_payloads_from_paths(paths: Iterable[Path]) -> list[tuple[Path, Any]]:
    payloads: list[tuple[Path, Any]] = []
    for path in paths:
        if path.is_absolute():
            raise ValueError(f"absolute input paths are not allowed: {path}")
        payload = _load_json(path)
        if payload is not None:
            payloads.append((path, payload))
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="Docs/Reports/GRAPH-MEMORY-CROSS-CLASS-BLOCKED-DIAGNOSTICS.md")
    parser.add_argument("--input", action="append", default=[], help="Repeatable relative JSON artifact path.")
    parser.add_argument("--generated-date", default=date.today().isoformat())
    args = parser.parse_args()

    inputs = [Path(value) for value in args.input]
    paths, inspected_roots, missing_roots = _json_paths(inputs)
    records: list[BlockedCollisionRecord] = []
    sources_with_records: list[str] = []
    for path, payload in load_json_payloads_from_paths(paths):
        path_records = _records_from_payload(path, payload)
        if path_records:
            sources_with_records.append(path.as_posix())
            records.extend(path_records)

    if inputs:
        inspected_roots = [p.as_posix() for p in inputs]
    source_note = (
        "Artifact roots inspected: " + (", ".join(inspected_roots) if inspected_roots else "explicit inputs only") + "; "
        "Missing or empty artifact roots: " + (", ".join(missing_roots) if missing_roots else "none") + "; "
        "JSON sources with blocked diagnostics: " + (", ".join(sources_with_records) if sources_with_records else "none") + "."
    )
    markdown = render_blocked_collision_markdown(records, source_note=source_note, generated_date=args.generated_date)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
