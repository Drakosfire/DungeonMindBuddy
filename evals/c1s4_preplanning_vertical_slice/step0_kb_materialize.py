from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any

import blake3

from src.agent.session_memory_query import load_session_memory_records_jsonl
from src.corpus.session_recap_paths import session_memory_jsonl_relpath

CORPUS_ROOT = ROOT / "corpus/eldyrwild-markdown"
DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "gold/kb_policy.json"


def check_oracle_leakage(*, records_or_items: list[dict[str, Any]], heldout_sessions: list[int], forbidden_oracle_relpaths: list[str]) -> dict[str, list[str]]:
    heldout = {int(x) for x in heldout_sessions}
    forbidden = [p.lower().strip() for p in forbidden_oracle_relpaths]
    path_hits: list[str] = []
    session_hits: list[str] = []
    for row in records_or_items:
        sn = row.get("session_number")
        if sn is not None and int(sn) in heldout:
            session_hits.append(str(row.get("unit_id") or row.get("source_recap_path") or "unknown"))
        text_blob = " ".join(str(row.get(k, "")) for k in ("source_recap_path", "unit_id", "source_id", "snippet")).lower()
        if "session 4" in text_blob or "session 04" in text_blob:
            path_hits.append(str(row.get("source_recap_path") or row.get("unit_id") or "session4-heuristic"))
        p = str(row.get("source_recap_path") or "").strip()
        pl = p.lower()
        for f in forbidden:
            if pl == f or pl.startswith(f) or f in pl:
                path_hits.append(p)
                break
    return {"forbidden_path_hits": sorted(set(path_hits)), "forbidden_session_hits": sorted(set(session_hits))}


def _resolve_included_paths(policy: dict[str, Any]) -> list[str]:
    explicit = [str(p) for p in policy.get("included_session_memory_relpaths") or [] if str(p).strip()]
    if explicit:
        return explicit
    sessions = [int(s) for s in policy["included_sessions"]]
    return [
        session_memory_jsonl_relpath(campaign_number=1, session=s, corpus_root=CORPUS_ROOT)
        for s in sessions
    ]


def load_kb_manifest(policy_path: Path = DEFAULT_POLICY_PATH) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    rel_paths = _resolve_included_paths(policy)
    all_records: list[dict[str, Any]] = []
    records_by_session = {str(s): 0 for s in policy["included_sessions"]}
    source_hashes: dict[str, str] = {}
    for rel in rel_paths:
        full = CORPUS_ROOT / rel
        rows = load_session_memory_records_jsonl(full)
        all_records.extend(rows)
        for r in rows:
            key = str(int(r.get("session_number", -1)))
            if key in records_by_session:
                records_by_session[key] += 1
        source_hashes[f"corpus/eldyrwild-markdown/{rel}"] = blake3.blake3(full.read_bytes()).hexdigest()

    leakage = check_oracle_leakage(
        records_or_items=all_records,
        heldout_sessions=policy["heldout_sessions"],
        forbidden_oracle_relpaths=policy["forbidden_oracle_relpaths"],
    )
    manifest = {
        "schema": "dmb_c1s4_preplanning_kb_manifest_v1",
        "kb_id": policy["kb_id"],
        "campaign_id": policy["campaign_id"],
        "included_sessions": policy["included_sessions"],
        "heldout_sessions": policy["heldout_sessions"],
        "source_paths": [f"corpus/eldyrwild-markdown/{r}" for r in rel_paths],
        "record_count": len(all_records),
        "records_by_session": records_by_session,
        "records_with_routes": sum(1 for r in all_records if r.get("routes")),
        "forbidden_path_hits": leakage["forbidden_path_hits"],
        "forbidden_session_hits": leakage["forbidden_session_hits"],
        "source_hashes": source_hashes,
    }
    return manifest, all_records


def main() -> int:
    manifest, _ = load_kb_manifest()
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 1 if manifest["forbidden_path_hits"] or manifest["forbidden_session_hits"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
