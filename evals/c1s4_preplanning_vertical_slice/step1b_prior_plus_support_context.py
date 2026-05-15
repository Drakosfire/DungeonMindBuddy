from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, check_oracle_leakage, load_kb_manifest
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import SupportRetrievalMode, load_normalized_support_records
from src.agent.session_memory_query import query_session_memory_candidate


QUERIES = [
    {"query_id": "road_to_mirathorn", "query": "What support knowledge helps describe the road from Stone Bridge toward Mirathorn without inventing a fully canonical route?"},
    {"query_id": "hemp_merchant", "query": "What source or adaptation support exists for a hemp merchant who can point the party toward a nearby village crisis?"},
    {"query_id": "visible_tree_threat", "query": "What support knowledge helps describe a rural village with a strange visible magical tree threat?"},
    {"query_id": "false_victory", "query": "What support knowledge helps plan a false victory where a town celebrates before the deeper danger appears?"},
]


class C1S4BoundaryError(RuntimeError): ...


def run_step1b(*, mode: SupportRetrievalMode) -> dict[str, Any]:
    policy = json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    manifest, session_records = load_kb_manifest(DEFAULT_POLICY_PATH)
    if manifest["forbidden_path_hits"] or manifest["forbidden_session_hits"] or manifest.get("unexpected_session_hits"):
        raise C1S4BoundaryError("Step 0 manifest is not oracle-safe; aborting Step 1B retrieval")

    support_records = load_normalized_support_records(retrieval_mode=mode)
    ref_leak = check_oracle_leakage(records_or_items=[{"source_recap_path": str(r.get("source_reference") or "")} for r in support_records], heldout_sessions=policy["heldout_sessions"], forbidden_oracle_relpaths=policy["forbidden_oracle_relpaths"])
    if ref_leak["forbidden_path_hits"] or ref_leak["forbidden_session_hits"]:
        raise C1S4BoundaryError("Support records reference forbidden C1S4 oracle surfaces")

    combined = [*session_records, *support_records]
    records_by_unit_id = {str(r.get("unit_id")): r for r in combined if str(r.get("unit_id") or "")}
    bundles = []
    for q in QUERIES:
        result = query_session_memory_candidate(records=combined, query=q["query"], campaign_id=manifest["campaign_id"], session_min=0, session_max=3, max_hits=8)
        bundle = build_preplanning_context_bundle(
            kb_id=manifest["kb_id"],
            campaign_id=manifest["campaign_id"],
            allowed_sessions=manifest["included_sessions"],
            heldout_sessions=manifest["heldout_sessions"],
            query=q["query"],
            retrieval_result=result,
            forbidden_oracle_relpaths=policy["forbidden_oracle_relpaths"],
            records_by_unit_id=records_by_unit_id,
        )
        bundles.append({"query_id": q["query_id"], "bundle": bundle})

    layer_counts: dict[str, int] = {"source_module": 0, "adaptation_planning": 0, "world_canon": 0, "support_gap": 0, "campaign_stateful_reference": 0}
    for r in support_records:
        layer = str(r.get("source_layer") or "")
        if layer in layer_counts:
            layer_counts[layer] += 1

    bundle_path_hits: list[str] = []
    bundle_session_hits: list[str] = []
    for row in bundles:
        chk = row["bundle"]["oracle_leakage_check"]
        bundle_path_hits.extend(chk.get("forbidden_path_hits", []))
        bundle_session_hits.extend(chk.get("forbidden_session_hits", []))

    return {
        "schema": "dmb_c1s4_preplanning_step1b_prior_plus_support_summary_v1",
        "retrieval_mode": mode,
        "kb_manifest": manifest,
        "record_counts": {"session_memory": len(session_records), "support_knowledge": len(support_records), "combined": len(combined)},
        "support_records_by_source_layer": layer_counts,
        "queries": QUERIES,
        "bundles": bundles,
        "oracle_leakage_check": {"forbidden_path_hits": sorted(set(bundle_path_hits)), "forbidden_session_hits": sorted(set(bundle_session_hits))},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["content_only", "content_plus_lexical_hints"])
    args = parser.parse_args()
    try:
        out = run_step1b(mode=args.mode)
    except C1S4BoundaryError as exc:
        print(json.dumps({"schema": "dmb_c1s4_preplanning_step1b_prior_plus_support_summary_v1", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(out, indent=2))
    leaks = out["oracle_leakage_check"]["forbidden_path_hits"] or out["oracle_leakage_check"]["forbidden_session_hits"]
    return 1 if leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
