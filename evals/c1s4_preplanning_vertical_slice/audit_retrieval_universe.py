from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import argparse
import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from evals.c1s4_preplanning_vertical_slice.context_classification import (
    infer_context_subject_class,
    infer_planner_lane,
    is_allowed_retrieval_corpus_path,
)
from evals.c1s4_preplanning_vertical_slice.step2_build_question_context_packets import build_summary
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import load_normalized_support_records

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


def _load_targets() -> dict[str, Any]:
    p = Path("evals/c1s4_preplanning_vertical_slice/artifacts/pr57/pr57_expected_evidence_targets.json")
    return json.loads(p.read_text(encoding="utf-8"))


def build_expected_evidence_manifest() -> list[ExpectedEvidence]:
    out: list[ExpectedEvidence] = []
    for t in _load_targets()["targets"]:
        for path in t["expected_paths"]:
            out.append(ExpectedEvidence(**{k: t[k] for k in ExpectedEvidence.__dataclass_fields__.keys() if k != "expected_path"}, expected_path=path))
    return out


def _allowed(path: str, source_kind: str) -> bool:
    if source_kind == "support_knowledge_card":
        return not any(tok in path.lower() for tok in ["evals/", "docs/", "tests/", "gold/", "artifacts/"])
    return is_allowed_retrieval_corpus_path(path)


def classify_retrieval_failure(*, exists: bool, allowed: bool, in_records: bool, direct_hit: bool, step2c_retrieved: bool, step2c_candidate: bool) -> str:
    if not exists:
        return "source_missing_on_disk"
    if not allowed:
        return "source_denied_by_hygiene"
    if not in_records:
        return "source_not_materialized_as_retrieval_record"
    if not direct_hit:
        return "source_indexed_but_direct_probe_miss"
    if direct_hit and not step2c_retrieved:
        return "direct_probe_hit_step2c_miss"
    if step2c_retrieved and not step2c_candidate:
        return "step2c_retrieved_but_candidate_missing"
    return "ok_or_later_stage"


def run_audit(*, step2c_report: Path | None, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_expected_evidence_manifest()
    step2_by_mode = {m: build_summary(mode=m, max_hits=50)["packets"] for m in RETRIEVAL_MODES}
    support_records = load_normalized_support_records(retrieval_mode="content_plus_lexical_hints")
    support_refs = "\n".join(json.dumps(x) for x in support_records)

    rows = []
    probe_rows = []
    matrix_rows = []
    for ev in manifest:
        p = Path(ev.expected_path)
        exists = p.exists() if ev.expected_source_kind != "support_knowledge_card" else True
        allowed = _allowed(ev.expected_path, ev.expected_source_kind)
        in_records = False
        direct_hit = False
        source_text = p.read_text(encoding="utf-8", errors="ignore") if p.exists() and p.is_file() else ""
        if ev.expected_source_kind == "support_knowledge_card":
            in_records = ev.expected_path in support_refs
            direct_hit = any(term.lower() in support_refs.lower() for term in ev.expected_terms)
        else:
            in_records = exists
            direct_hit = any(term.lower() in source_text.lower() for term in ev.expected_terms)

        packets = step2_by_mode[ev.mode]
        retrieved_hit = any(pkt.get("question_id") == ev.question_id and any(ev.expected_path.lower() in json.dumps(i).lower() for i in pkt.get("retrieved_context", [])) for pkt in packets)
        candidate_hit = any(pkt.get("question_id") == ev.question_id and any(ev.expected_path.lower() in json.dumps(i).lower() for i in pkt.get("candidate_context", [])) for pkt in packets)
        status = classify_retrieval_failure(exists=exists, allowed=allowed, in_records=in_records, direct_hit=direct_hit, step2c_retrieved=retrieved_hit, step2c_candidate=candidate_hit)
        row = asdict(ev) | {
            "exists_on_disk": exists,
            "allowed_by_retrieval_hygiene": allowed,
            "included_in_retrieval_records": in_records,
            "indexed": in_records,
            "direct_probe_hit": direct_hit,
            "step2c_retrieved_hit": retrieved_hit,
            "step2c_candidate_hit": candidate_hit,
            "classification_status": status,
            "notes": "",
        }
        rows.append(row)
        for k in [10, 20, 50]:
            probe_rows.append({"probe": "|".join(ev.expected_terms), "mode": ev.mode, "top_k": k, "hit_count": 1 if direct_hit else 0, "top_refs": ev.expected_path, "expected_refs_hit": direct_hit, "expected_paths_hit": direct_hit, "first_expected_rank": 1 if direct_hit else "", "source_kinds_seen": ev.expected_source_kind, "subject_classes_seen": ev.expected_subject_class, "notes": "lexical deterministic proxy"})
        matrix_rows.append({"question_id": ev.question_id, "group_id": ev.group_id, "mode": ev.mode, "expected_path": ev.expected_path, "direct_probe_hit": direct_hit, "step2c_retrieved_hit": retrieved_hit, "step2c_candidate_hit": candidate_hit, "classification_status": status})

    summary = {"schema": "dmb_pr57_retrieval_universe_summary_v1", "counts": {k: sum(1 for r in rows if r["classification_status"] == k) for k in sorted(set(r["classification_status"] for r in rows))}}
    (output_dir / "pr57_retrieval_universe_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def _write_csv(path: Path, data: list[dict[str, Any]]):
        if not data:
            return
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader(); w.writerows(data)

    _write_csv(output_dir / "pr57_expected_evidence_manifest.csv", rows)
    _write_csv(output_dir / "pr57_direct_probe_results.csv", probe_rows)
    _write_csv(output_dir / "pr57_step2c_vs_direct_probe_matrix.csv", matrix_rows)
    (output_dir / "README.md").write_text("PR57 retrieval universe artifacts.\n", encoding="utf-8")
    (output_dir / "pr57_next_pr_recommendations.md").write_text("Prioritize earliest failing surface by taxonomy counts.\n", encoding="utf-8")
    (output_dir / "pr57_retrieval_universe_audit.md").write_text("# PR57 Retrieval Universe Audit\n\nGenerated deterministically from current retrieval pipeline.\n", encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gold", type=Path, required=False)
    p.add_argument("--step2c-report", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(run_audit(step2c_report=args.step2c_report, output_dir=args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
