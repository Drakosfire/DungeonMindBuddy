#!/usr/bin/env python3
"""Census the current canonical Eldyrwild/Longmont markdown corpus.

Walks ``corpus/eldyrwild-markdown/`` and classifies every Markdown file for
the full-corpus World Graph ingestion slice. Does not call models.

Canonical recap authority is GM-authored files at each campaign
``Session Recaps/`` root. Derivative directories are recorded but not admitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "corpus" / "eldyrwild-markdown"

EXCLUDED_DIR_NAMES = {
    "_normalized",
    "_breadcrumbed",
    "_session_memory",
    "_archive",
    "_ingest_staging",
    "_dungeonbuddy",
    ".backups",
}

C1_RECAPS = CORPUS_ROOT / "Longmont Campaign" / "Campaign 1" / "Session Recaps"
C2_RECAPS = CORPUS_ROOT / "Longmont Campaign" / "Campaign 2" / "Session Recaps"
C2_PREP = CORPUS_ROOT / "Longmont Campaign" / "Campaign 2" / "Session Prep"
ELDERWYLD = CORPUS_ROOT / "Elderwyld"

# Documented duplicate resolutions. Do not invent new corpus authority.
PREFERRED_RECAPS = {
    ("longmont-c1", 2): "Session 2 - Finishing the Job.md",
    ("longmont-c2", 23): "Session 23 - Mireward Gate Battle.md",
}
PREFERRED_RECAP_REASONS = {
    ("longmont-c1", 2): (
        "duplicate_session_recap: two Session 2 files exist at the canonical "
        "root; CORPUS-INDEX and body title agree that "
        "'Session 2 - Finishing the Job.md' is the played recap. "
        "'Session 2 - Stonebridge and Glowkindle Rats.md' is the same session "
        "with a misleading Session-1-style filename."
    ),
    ("longmont-c2", 23): (
        "duplicate_session_recap: Session Recaps/_archive/README.md names "
        "'Session 23 - Mireward Gate Battle.md' as the canonical recap. "
        "'Session 23 - Mireward Gate.md' is a leftover duplicate that should "
        "have been archived with the 2026-06-28 cleanup."
    ),
}

RECAP_MODEL_PASSES = 8  # actor, location, collective, object, thread, beat, edge, party_claimed_fill
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_PROVIDER = "openai"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    meta: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if value.lower() in {"null", "none", ""}:
            meta[key] = None
            continue
        if re.fullmatch(r"-?\d+", value):
            meta[key] = int(value)
        else:
            meta[key] = value
    return meta


def _excluded_dir_reason(path: Path) -> str | None:
    for part in path.parts:
        if part in EXCLUDED_DIR_NAMES:
            return f"derivative_directory:{part}"
    return None


def _campaign_from_path(rel: str, meta: dict[str, Any]) -> str | None:
    if meta.get("campaign_id"):
        return str(meta["campaign_id"])
    if "/Campaign 1/" in rel or rel.startswith("Longmont Campaign/Campaign 1/"):
        return "longmont-c1"
    if "/Campaign 2/" in rel or rel.startswith("Longmont Campaign/Campaign 2/"):
        return "longmont-c2"
    return None


def _session_from_path(name: str, meta: dict[str, Any]) -> int | None:
    if isinstance(meta.get("session"), int):
        return meta["session"]
    match = re.search(r"Session\s+(\d+)\b", name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _document_class_from_path(rel: str, meta: dict[str, Any]) -> str:
    if meta.get("document_class"):
        return str(meta["document_class"])
    if "/Session Recaps/" in rel:
        return "play"
    if "/Session Prep/" in rel:
        return "planning"
    if rel.startswith("Elderwyld/") or "/Elderwyld/" in rel:
        return "world"
    return "unknown"


def _source_class_from_path(rel: str, meta: dict[str, Any]) -> str | None:
    if meta.get("source_class"):
        return str(meta["source_class"])
    if "/Session Recaps/" in rel and _excluded_dir_reason(Path(rel)) is None:
        return "observed_session_recap"
    if "/Session Prep/" in rel:
        return "planning_document"
    return None


def _canon_layer(rel: str, meta: dict[str, Any]) -> str | None:
    if meta.get("canon_layer"):
        return str(meta["canon_layer"])
    if "/Session Recaps/" in rel:
        return "campaign"
    if rel.startswith("Elderwyld/"):
        return "world"
    return None


def _temporal_scope(meta: dict[str, Any], session: int | None) -> str | None:
    if meta.get("temporal_scope"):
        return str(meta["temporal_scope"])
    if session is not None:
        return "session_specific"
    return None


def _authority_class(source_class: str | None, document_class: str, rel: str) -> str:
    if source_class == "observed_session_recap" and "/Session Recaps/" in rel:
        return "played_campaign_history"
    if source_class == "planning_document" or document_class == "planning" or "/Session Prep/" in rel:
        return "gm_planning"
    if source_class in {"seed_reference", "authored_dossier", "roll_table", "character_seed"}:
        return "setting_reference"
    if document_class in {"world", "reference"}:
        return "setting_reference"
    return "unclassified"


def _bucket(rel: str, excluded: str | None) -> str:
    if excluded:
        return "derivative_or_staging"
    if rel.startswith("Longmont Campaign/Campaign 1/Session Recaps/") and rel.count("/") == 3:
        return "campaign_1_recap"
    if rel.startswith("Longmont Campaign/Campaign 2/Session Recaps/") and rel.count("/") == 3:
        return "campaign_2_recap"
    if rel.startswith("Longmont Campaign/Campaign 2/Session Prep/"):
        return "campaign_2_session_prep"
    if rel.startswith("Elderwyld/"):
        return "worldbuilding_elderwyld"
    if rel.startswith("Longmont Campaign/"):
        return "campaign_local_reference"
    return "other_markdown"


def classify_record(path: Path) -> dict[str, Any]:
    rel = path.relative_to(CORPUS_ROOT).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = _parse_frontmatter(text)
    excluded = _excluded_dir_reason(path)
    campaign = _campaign_from_path(rel, meta)
    session = _session_from_path(path.name, meta)
    document_class = _document_class_from_path(rel, meta)
    source_class = _source_class_from_path(rel, meta)
    bucket = _bucket(rel, excluded)
    authority = _authority_class(source_class, document_class, rel)

    eligible = False
    reason: str | None = None
    ambiguous = False

    if excluded:
        reason = excluded
    elif bucket == "campaign_2_session_prep":
        reason = "session_prep_is_not_played_history"
    elif bucket in {"campaign_1_recap", "campaign_2_recap"}:
        preferred = PREFERRED_RECAPS.get((campaign or "", session or -1))
        if preferred and path.name != preferred:
            eligible = False
            ambiguous = True
            reason = PREFERRED_RECAP_REASONS[(campaign or "", session or -1)]
        elif source_class and source_class != "observed_session_recap":
            reason = f"recap_root_source_class_is_{source_class}"
        elif session is None:
            reason = "recap_missing_session_number"
            ambiguous = True
        else:
            eligible = True
    elif bucket == "worldbuilding_elderwyld":
        reason = "worldbuilding_deferred_pending_authority_readiness"
    elif bucket == "campaign_local_reference":
        reason = "campaign_local_reference_not_played_recap"
    else:
        reason = "outside_admitted_recap_or_worldbuilding_roots"

    return {
        "path": rel,
        "document_class": document_class,
        "campaign": campaign,
        "session_number": session,
        "source_class": source_class,
        "canon_layer": _canon_layer(rel, meta),
        "temporal_scope": _temporal_scope(meta, session),
        "authority_epistemic_classification": authority,
        "content_sha256": _sha256_file(path),
        "byte_count": path.stat().st_size,
        "eligible_for_ingest": eligible,
        "reason_if_excluded": None if eligible else reason,
        "bucket": bucket,
        "ambiguous": ambiguous,
        "frontmatter_present": bool(meta),
        "title": meta.get("title"),
    }


def census_records() -> list[dict[str, Any]]:
    records = [
        classify_record(path)
        for path in sorted(CORPUS_ROOT.rglob("*.md"))
        if path.is_file()
    ]
    return records


def chronological_recaps(records: list[dict[str, Any]], campaign: str) -> list[dict[str, Any]]:
    admitted = [
        rec
        for rec in records
        if rec["eligible_for_ingest"] and rec["campaign"] == campaign
    ]
    admitted.sort(key=lambda rec: (rec["session_number"] or 10**9, rec["path"]))
    return admitted


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = Counter(rec["bucket"] for rec in records)
    c1 = chronological_recaps(records, "longmont-c1")
    c2 = chronological_recaps(records, "longmont-c2")
    admitted = [rec for rec in records if rec["eligible_for_ingest"]]
    skipped = [rec for rec in records if not rec["eligible_for_ingest"]]
    ambiguous = [rec for rec in records if rec["ambiguous"]]
    worldbuilding = [rec for rec in records if rec["bucket"] == "worldbuilding_elderwyld"]
    recap_discovered = [
        rec
        for rec in records
        if rec["bucket"] in {"campaign_1_recap", "campaign_2_recap"}
    ]
    total_bytes = sum(rec["byte_count"] for rec in records)
    admitted_bytes = sum(rec["byte_count"] for rec in admitted)
    estimated_requests = len(admitted) * RECAP_MODEL_PASSES
    return {
        "generated_at": _utc_now(),
        "corpus_root": "corpus/eldyrwild-markdown",
        "git_head": None,
        "extraction_contract": {
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
            "profile": "recap_category_v1@1.0",
            "estimated_model_passes_per_recap": RECAP_MODEL_PASSES,
        },
        "counts": {
            "markdown_files_discovered": len(records),
            "campaign_recap_files_discovered": len(recap_discovered),
            "campaign_recap_files_admitted": len(admitted),
            "campaign_1_recaps_discovered": buckets["campaign_1_recap"],
            "campaign_1_recaps_admitted": len(c1),
            "campaign_2_recaps_discovered": buckets["campaign_2_recap"],
            "campaign_2_recaps_admitted": len(c2),
            "worldbuilding_files_discovered": len(worldbuilding),
            "worldbuilding_files_admitted": 0,
            "session_prep_files_discovered": buckets["campaign_2_session_prep"],
            "files_skipped": len(skipped),
            "files_ambiguous": len(ambiguous),
            "total_bytes": total_bytes,
            "admitted_bytes": admitted_bytes,
            "estimated_model_requests": estimated_requests,
        },
        "chronology": {
            "campaign_1_sessions": [rec["session_number"] for rec in c1],
            "campaign_2_sessions": [rec["session_number"] for rec in c2],
            "campaign_1_paths": [rec["path"] for rec in c1],
            "campaign_2_paths": [rec["path"] for rec in c2],
        },
        "ambiguous_files": [
            {"path": rec["path"], "reason": rec["reason_if_excluded"]}
            for rec in ambiguous
        ],
        "exclusion_reasons": dict(Counter(rec["reason_if_excluded"] or "admitted" for rec in records)),
        "worldbuilding_decision": "DEFER",
        "worldbuilding_deferral_reason": (
            "Existing recap extraction stamps canon_state=played_canon and the "
            "worldbuilding write-plan owner is locked to "
            "worldbuilding_shepherds_flock_v0@0.1. Source metadata can distinguish "
            "setting/planning/play, but publication cannot yet preserve that "
            "distinction for the Elderwyld tree."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "out" / "full_corpus_world_graph_ingestion",
    )
    args = parser.parse_args()
    records = census_records()
    summary = summarize(records)
    try:
        import subprocess

        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        summary["git_head"] = head
    except Exception:
        pass

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "dmb_full_corpus_census_v1", "summary": summary, "records": records}
    (out_dir / "CENSUS.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    counts = summary["counts"]
    report = f"""# Full-corpus census

Generated: `{summary['generated_at']}`
Git head: `{summary.get('git_head')}`
Corpus root: `{summary['corpus_root']}`

## Counts

| Metric | Count |
|---|---:|
| Markdown files discovered | {counts['markdown_files_discovered']} |
| Campaign recap files discovered | {counts['campaign_recap_files_discovered']} |
| Campaign recap files admitted | {counts['campaign_recap_files_admitted']} |
| Campaign 1 recaps discovered / admitted | {counts['campaign_1_recaps_discovered']} / {counts['campaign_1_recaps_admitted']} |
| Campaign 2 recaps discovered / admitted | {counts['campaign_2_recaps_discovered']} / {counts['campaign_2_recaps_admitted']} |
| Worldbuilding files discovered | {counts['worldbuilding_files_discovered']} |
| Worldbuilding files admitted | {counts['worldbuilding_files_admitted']} |
| Session Prep files discovered (excluded) | {counts['session_prep_files_discovered']} |
| Files skipped | {counts['files_skipped']} |
| Files ambiguous | {counts['files_ambiguous']} |
| Total bytes | {counts['total_bytes']} |
| Admitted recap bytes | {counts['admitted_bytes']} |
| Estimated model requests | {counts['estimated_model_requests']} |

## Chronology

Campaign 1 sessions: {summary['chronology']['campaign_1_sessions']}

Campaign 2 sessions: {summary['chronology']['campaign_2_sessions']}

## Ambiguous recaps

{chr(10).join(f"- `{item['path']}` — {item['reason']}" for item in summary['ambiguous_files']) or '_None._'}

## Worldbuilding

Decision: **{summary['worldbuilding_decision']}**

{summary['worldbuilding_deferral_reason']}
"""
    (out_dir / "CENSUS.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary["counts"], indent=2))
    print(f"Wrote {out_dir / 'CENSUS.json'}")


if __name__ == "__main__":
    main()
