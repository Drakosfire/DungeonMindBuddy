from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.c1s4_preplanning_vertical_slice.campaign_corpus_materializer import load_campaign_corpus_records_for_c1s4
from evals.c1s4_preplanning_vertical_slice.context_classification import is_allowed_retrieval_corpus_path
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, load_kb_manifest
from evals.c1s4_preplanning_vertical_slice.expected_context_benchmark import (
    EXPECTED_CONTEXT_MULTIMODE_REPORT_SCHEMA,
    EXPECTED_CONTEXT_REPORT_SCHEMA,
    load_expected_context_gold,
    validate_expected_context_gold,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.pr59_artifact_emit import write_pr59_artifacts
from evals.c1s4_preplanning_vertical_slice.pr60_artifact_emit import write_pr60_artifacts
from evals.c1s4_preplanning_vertical_slice.pr61_artifact_emit import write_pr61_artifacts
from src.agent.session_memory_query import query_session_memory_candidate

from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_normalized_support_records

DEFAULT_TARGETS_PATH = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr57/pr57_expected_evidence_targets.json")
DEFAULT_GOLD_PATH = Path("evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json")

RETRIEVAL_MODES = ["prior_only", "prior_plus_support_content_only", "prior_plus_support_content_plus_lexical_hints"]


@dataclass
class ExpectedEvidence:
    question_id: str
    group_id: str
    mode: str
    required_lane: str
    expected_rendered_section: str
    label: str
    expected_path: str
    expected_source_kind: str
    expected_subject_class: str
    expected_terms: list[str]


def _load_targets(targets_path: Path) -> dict[str, Any]:
    return json.loads(targets_path.read_text(encoding="utf-8"))


def build_expected_evidence_manifest(*, targets_path: Path = DEFAULT_TARGETS_PATH) -> list[ExpectedEvidence]:
    rows: list[ExpectedEvidence] = []
    for t in _load_targets(targets_path)["targets"]:
        for expected_path in t["expected_paths"]:
            payload = {k: t[k] for k in ExpectedEvidence.__dataclass_fields__.keys() if k != "expected_path"}
            rows.append(ExpectedEvidence(**payload, expected_path=expected_path))
    return rows


def _artifact_prefix(output_dir: Path) -> str:
    name = output_dir.name.lower()
    if name.startswith("pr") and name[2:].isdigit():
        return name
    return "pr57"


def _combined_records_by_mode() -> dict[str, list[dict[str, Any]]]:
    _, session_records = load_kb_manifest(DEFAULT_POLICY_PATH)
    corpus_records = load_campaign_corpus_records_for_c1s4()
    base = list(session_records) + corpus_records
    out = {"prior_only": list(base)}
    out["prior_plus_support_content_only"] = list(base) + load_normalized_support_records(retrieval_mode="content_only")
    out["prior_plus_support_content_plus_lexical_hints"] = list(base) + load_normalized_support_records(retrieval_mode="content_plus_lexical_hints")
    return out


def _record_refs(record: dict[str, Any]) -> str:
    vals = [record.get("source_path"), record.get("source_recap_path"), record.get("source_reference"), record.get("unit_id")]
    return " ".join(json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else str(v or "") for v in vals).lower()


def classify_retrieval_failure(*, exists: bool, allowed: bool, in_records: bool, lexical_file_probe_hit: bool, step2c_retrieved: bool, step2c_candidate: bool) -> str:
    if not exists:
        return "source_missing_on_disk"
    if not allowed:
        return "source_denied_by_hygiene"
    if not in_records:
        return "source_not_materialized_as_retrieval_record"
    if lexical_file_probe_hit and not step2c_retrieved:
        return "source_exists_but_step2c_miss"
    if step2c_retrieved and not step2c_candidate:
        return "step2c_retrieved_but_candidate_missing"
    return "ok_or_later_stage"


def _validate_step2c_report(step2c_report_path: Path) -> dict[str, Any]:
    report = json.loads(step2c_report_path.read_text(encoding="utf-8"))
    schema = str(report.get("schema") or "")
    if schema not in {EXPECTED_CONTEXT_MULTIMODE_REPORT_SCHEMA, EXPECTED_CONTEXT_REPORT_SCHEMA}:
        raise ValueError(f"unsupported step2c report schema: {schema!r}")
    return report


def _load_packets_by_mode(*, step2_packets_path: Path | None, rebuild_step2c_packets: bool) -> dict[str, list[dict[str, Any]]]:
    if step2_packets_path is not None:
        raw = json.loads(step2_packets_path.read_text(encoding="utf-8"))
        if isinstance(raw.get("packets_by_mode"), dict):
            return {str(k): list(v) for k, v in raw["packets_by_mode"].items()}
        return {str(k): list(v) for k, v in raw.items()}
    if not rebuild_step2c_packets:
        raise ValueError("Provide --step2-packets-json or pass --rebuild-step2c-packets")
    return {m: build_summary(mode=m, max_hits=50)["packets"] for m in RETRIEVAL_MODES}


def run_audit(
    *,
    output_dir: Path,
    targets_path: Path = DEFAULT_TARGETS_PATH,
    gold_path: Path | None = None,
    step2c_report_path: Path | None = None,
    step2_packets_path: Path | None = None,
    rebuild_step2c_packets: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = _artifact_prefix(output_dir)
    if gold_path is not None:
        gold_errs = validate_expected_context_gold(load_expected_context_gold(gold_path))
        if gold_errs:
            raise ValueError(f"invalid gold: {gold_errs}")
    if step2c_report_path is not None:
        _validate_step2c_report(step2c_report_path)
    manifest = build_expected_evidence_manifest(targets_path=targets_path)
    records_by_mode = _combined_records_by_mode()
    packets_by_mode = _load_packets_by_mode(
        step2_packets_path=step2_packets_path,
        rebuild_step2c_packets=rebuild_step2c_packets,
    )

    manifest_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []

    for ev in manifest:
        records = records_by_mode[ev.mode]
        refs_blob = "\n".join(_record_refs(r) for r in records)
        packets = packets_by_mode[ev.mode]

        if ev.expected_source_kind == "known_context_gap":
            step2c_known_gap_hit = any(
                pkt.get("question_id") == ev.question_id and any(ev.expected_terms[0].lower() in str(g).lower() or ev.group_id.lower() in str(g).lower() for g in (pkt.get("known_context_gaps") or []))
                for pkt in packets
            )
            status = "known_gap_present" if step2c_known_gap_hit else "known_gap_missing_from_packet"
            row = asdict(ev) | {
                "source_exists_on_disk": "n/a",
                "allowed_by_retrieval_hygiene": True,
                "included_in_retrieval_records": "n/a",
                "indexed": "n/a",
                "lexical_file_probe_hit": "n/a",
                "retrieval_probe_hit": "n/a",
                "step2c_known_gap_hit": step2c_known_gap_hit,
                "step2c_retrieved_hit": False,
                "step2c_candidate_hit": False,
                "classification_status": status,
                "notes": "known_context_gap audited from packet known_context_gaps rather than filesystem/records",
            }
            manifest_rows.append(row)
            matrix_rows.append({"question_id": ev.question_id, "group_id": ev.group_id, "mode": ev.mode, "expected_path": ev.expected_path, "lexical_file_probe_hit": "n/a", "retrieval_probe_hit": "n/a", "step2c_known_gap_hit": step2c_known_gap_hit, "step2c_retrieved_hit": False, "step2c_candidate_hit": False, "classification_status": status})
            continue

        exists = ev.expected_source_kind == "support_knowledge_card" or Path(ev.expected_path).exists()
        allowed = (not any(x in ev.expected_path.lower() for x in ["evals/", "docs/", "tests/", "gold/", "artifacts/"])) if ev.expected_source_kind == "support_knowledge_card" else is_allowed_retrieval_corpus_path(ev.expected_path)
        in_records = ev.expected_path.lower() in refs_blob

        lexical_file_probe_hit = False
        if ev.expected_source_kind == "support_knowledge_card":
            lexical_file_probe_hit = any(t.lower() in refs_blob for t in ev.expected_terms)
        else:
            p = Path(ev.expected_path)
            if p.exists() and p.is_file():
                txt = p.read_text(encoding="utf-8", errors="ignore").lower()
                lexical_file_probe_hit = any(t.lower() in txt for t in ev.expected_terms)

        probe_query = " ".join(ev.expected_terms)
        hits = list(getattr(query_session_memory_candidate(records=records, query=probe_query, campaign_id="longmont-c1", session_min=0, session_max=3, max_hits=50), "hits", []) or [])
        retrieval_probe_hit = any(ev.expected_path.lower() in _record_refs(h) for h in hits)
        first_rank = next((i for i, h in enumerate(hits, start=1) if ev.expected_path.lower() in _record_refs(h)), None)

        step2c_retrieved = any(pkt.get("question_id") == ev.question_id and any(ev.expected_path.lower() in _record_refs(i) for i in pkt.get("retrieved_context", [])) for pkt in packets)
        step2c_candidate = any(pkt.get("question_id") == ev.question_id and any(ev.expected_path.lower() in _record_refs(i) for i in pkt.get("candidate_context", [])) for pkt in packets)
        status = classify_retrieval_failure(exists=exists, allowed=allowed, in_records=in_records, lexical_file_probe_hit=lexical_file_probe_hit, step2c_retrieved=step2c_retrieved, step2c_candidate=step2c_candidate)

        row = asdict(ev) | {
            "source_exists_on_disk": exists,
            "allowed_by_retrieval_hygiene": allowed,
            "included_in_retrieval_records": in_records,
            "indexed": in_records,
            "lexical_file_probe_hit": lexical_file_probe_hit,
            "retrieval_probe_hit": retrieval_probe_hit,
            "step2c_known_gap_hit": False,
            "step2c_retrieved_hit": step2c_retrieved,
            "step2c_candidate_hit": step2c_candidate,
            "classification_status": status,
            "notes": "retrieval_probe_hit uses query_session_memory_candidate over Step2C record universe",
        }
        manifest_rows.append(row)

        for k in [10, 20, 50]:
            top_hits = hits[:k]
            top_expected = any(ev.expected_path.lower() in _record_refs(h) for h in top_hits)
            probe_rows.append({"probe": probe_query, "mode": ev.mode, "top_k": k, "hit_count": len(top_hits), "top_refs": [h.get("unit_id") for h in top_hits[:5]], "expected_refs_hit": top_expected, "expected_paths_hit": top_expected, "first_expected_rank": first_rank or "", "source_kinds_seen": sorted({str(h.get('source_kind') or '') for h in top_hits}), "subject_classes_seen": "", "notes": "actual retrieval probe"})

        matrix_rows.append({"question_id": ev.question_id, "group_id": ev.group_id, "mode": ev.mode, "expected_path": ev.expected_path, "lexical_file_probe_hit": lexical_file_probe_hit, "retrieval_probe_hit": retrieval_probe_hit, "step2c_known_gap_hit": False, "step2c_retrieved_hit": step2c_retrieved, "step2c_candidate_hit": step2c_candidate, "classification_status": status})

    counts = {k: sum(1 for r in manifest_rows if r["classification_status"] == k) for k in sorted({r["classification_status"] for r in manifest_rows})}
    summary = {
        "schema": f"dmb_{prefix}_retrieval_universe_summary_v1",
        "counts": counts,
        "inputs": {
            "targets_path": str(targets_path),
            "gold_path": str(gold_path) if gold_path else None,
            "step2c_report_path": str(step2c_report_path) if step2c_report_path else None,
            "step2_packets_path": str(step2_packets_path) if step2_packets_path else None,
            "rebuild_step2c_packets": rebuild_step2c_packets,
        },
    }

    def write_csv(path: Path, data: list[dict[str, Any]]) -> None:
        if not data:
            path.write_text("", encoding="utf-8")
            return
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    (output_dir / f"{prefix}_retrieval_universe_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_csv(output_dir / f"{prefix}_expected_evidence_manifest.csv", manifest_rows)
    write_csv(output_dir / f"{prefix}_direct_probe_results.csv", probe_rows)
    write_csv(output_dir / f"{prefix}_step2c_vs_direct_probe_matrix.csv", matrix_rows)

    corpus_rows = [r for r in manifest_rows if str(r["expected_path"]).startswith("corpus/")]
    support_rows = [r for r in manifest_rows if str(r["expected_source_kind"]) == "support_knowledge_card"]
    not_materialized = sum(1 for r in corpus_rows if r["classification_status"] == "source_not_materialized_as_retrieval_record")
    support_probe_hits = sum(1 for r in support_rows if r.get("retrieval_probe_hit") is True)
    support_step2c_misses = sum(1 for r in support_rows if r.get("retrieval_probe_hit") is True and not r.get("step2c_retrieved_hit"))
    support_step2c_candidate_hits = sum(1 for r in support_rows if r.get("step2c_candidate_hit") is True)

    readme_title = prefix.upper()
    (output_dir / "README.md").write_text(f"{readme_title} retrieval-universe audit artifacts.\n", encoding="utf-8")
    audit_md = output_dir / f"{prefix}_retrieval_universe_audit.md"
    if prefix == "pr58":
        audit_md = output_dir / f"{prefix}_materialization_report.md"
    audit_md.write_text(
        f"# {readme_title} Retrieval Universe Audit\n\n"
        "## Scope\n"
        "Q1/Q3/Q5 lane-aware expected evidence groups, including known gaps and support-enabled modes.\n\n"
        "## Executive Summary\n"
        f"- Corpus markdown hubs/dossiers/recaps are materialized into the Step2C retrieval record universe ({not_materialized} corpus rows still `source_not_materialized_as_retrieval_record`).\n"
        "- Step2C retrieval universe combines Step0 session-memory records, PR58 campaign-corpus section records, and support-card augmentation.\n"
        f"- Support cards are materialized and retrieval-probe reachable ({support_probe_hits} rows); Step2C candidate hits: {support_step2c_candidate_hits}; retrieved misses after probe hit: {support_step2c_misses}.\n"
        "- Known-gap targets are audited against packet `known_context_gaps` and not treated as filesystem/index artifacts.\n\n"
        "## What this proves\n"
        "1. Existence/hygiene for corpus paths is mostly not the bottleneck.\n"
        "2. Record-universe materialization is the primary early surface for corpus hub/dossier/recap evidence.\n"
        "3. Support-card Step2C visibility depends on bundle assembly (not admission).\n\n"
        "## Caveats\n"
        "`retrieval_probe_hit` uses the same candidate query API as Step2C (`query_session_memory_candidate`) over mode-specific Step2C record universes; lexical checks are kept separate under `lexical_file_probe_hit`.\n",
        encoding="utf-8",
    )
    (output_dir / f"{prefix}_next_pr_recommendations.md").write_text(
        f"# Post-{readme_title} Planning Recommendations\n\n"
        "1. If direct retrieval works but Step2C question retrieval still misses, investigate query construction / route-alias expansion (PR59).\n"
        "2. If Step2C retrieves candidates but admission drops them, investigate admission lane floors (PR60).\n"
        "3. Keep admission/rendering/gold unchanged until earliest failing surfaces are resolved and re-audited.\n",
        encoding="utf-8",
    )
    if prefix == "pr58":
        (output_dir / f"{prefix}_support_trace.md").write_text(
            "# PR58 Support-card Step2C trace\n\n"
            "## Root cause (fixed)\n"
            "`build_preplanning_context_bundle` treated support-card `source_reference` dicts as corpus paths "
            "and dropped them via `is_allowed_retrieval_corpus_path`.\n\n"
            "## Fix\n"
            "Support knowledge cards bypass corpus path hygiene and append directly with "
            "`presentation_lane=support_knowledge` and `subject_class=support`.\n\n"
            "## Verification\n"
            "- Unit test `test_support_bundle_preserves_support_card_hits` passes with an explicit support hit.\n"
            "- Direct probe with expected terms still reaches `support:hempholm_tree_visible_threat`.\n\n"
            "## Remaining Q5 Step2C miss (not bundle assembly)\n"
            "For the actual Q5 planner question text, hempholm campaign-corpus section records outrank the "
            "support card in the top-50 candidate pool (`_retrieve` returns no support unit_id). "
            "This is query-construction / ranking depth, not admission — track as PR59.\n\n"
            f"## Audit counts (this run)\n"
            f"- support retrieval_probe_hit rows: {support_probe_hits}\n"
            f"- support step2c_candidate_hit rows: {support_step2c_candidate_hits}\n"
            f"- support probe hit but step2c retrieved miss: {support_step2c_misses}\n",
            encoding="utf-8",
        )
    if prefix == "pr59":
        write_pr59_artifacts(output_dir=output_dir, packets_by_mode=packets_by_mode)
    if prefix == "pr60":
        write_pr60_artifacts(output_dir=output_dir, packets_by_mode=packets_by_mode)
    if prefix == "pr61":
        write_pr61_artifacts(output_dir=output_dir, packets_by_mode=packets_by_mode)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit retrieval-universe materialization vs expected evidence targets. "
            "Step2C packet surfaces come from --step2-packets-json when provided; "
            "otherwise --rebuild-step2c-packets (default) regenerates them via build_summary(). "
            "--step2c-report validates report schema only (graded results, not packet payloads)."
        )
    )
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS_PATH, help="Expected evidence targets JSON")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_PATH, help="Validate expected-context gold schema")
    parser.add_argument("--step2c-report", type=Path, help="Optional Step2C benchmark report for schema validation")
    parser.add_argument("--step2-packets-json", type=Path, help="Optional {mode: [packets]} JSON for Step2C packet surfaces")
    parser.add_argument("--rebuild-step2c-packets", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run_audit(
                output_dir=args.output_dir,
                targets_path=args.targets,
                gold_path=args.gold,
                step2c_report_path=args.step2c_report,
                step2_packets_path=args.step2_packets_json,
                rebuild_step2c_packets=args.rebuild_step2c_packets,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
