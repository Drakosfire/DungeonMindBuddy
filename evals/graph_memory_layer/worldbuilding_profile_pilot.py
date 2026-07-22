#!/usr/bin/env python3
"""Local repeat-trial cohort runner for the bounded worldbuilding profile.

Uses the redacted fixture and deterministic pass client — no live corpus or
model payloads are written into the report.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from src.graph_memory.extraction.category_candidate_graph_extractor import (  # noqa: E402
    FixtureCategoryGraphPassClient,
)
from src.graph_memory.extraction.graph_preview_runner import (  # noqa: E402
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.worldbuilding_extraction_profile import (  # noqa: E402
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
    validate_worldbuilding_candidate_bounds,
)
from src.graph_memory.extraction.worldbuilding_source_adapter import (  # noqa: E402
    WorldbuildingSourceAdapter,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "worldbuilding_profile_fixture.json"
)
DEFAULT_OUT = REPO_ROOT / "out" / "evals" / "worldbuilding_profile_pilot"


@dataclass
class TrialSummary:
    trial_id: str
    run_id: str
    status: str
    failure_kind: str | None
    node_count: int
    edge_count: int
    bound_errors: list[str] = field(default_factory=list)
    outcome: str = "failed"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _pass_outputs_for_span(fixture: dict, span_id: str) -> dict:
    outputs = json.loads(json.dumps(fixture["pass_outputs"]))
    for pass_payload in outputs.values():
        for key in ("observation_nodes", "observation_edges"):
            for row in pass_payload.get(key) or []:
                for ref in row.get("evidence_refs") or []:
                    if ref.get("source_span_ref_id") == "PLACEHOLDER_SPAN":
                        ref["source_span_ref_id"] = span_id
    return outputs


def run_cohort(*, trials: int, output_dir: Path) -> dict:
    fixture = _load_fixture()
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort_id = datetime.now(UTC).strftime("wb-cohort-%Y%m%dT%H%M%SZ")
    summaries: list[TrialSummary] = []

    for index in range(1, trials + 1):
        trial_id = f"{cohort_id}-trial-{index}"
        trial_dir = output_dir / trial_id
        source = WorldbuildingSourceAdapter(
            source_artifact_id=fixture["source_artifact_id"],
            source_text=fixture["source_text"],
            campaign_id=fixture["campaign_id"],
            document_class=fixture["document_class"],
            source_uri=f"fixture://{trial_id}",
        ).normalize()
        paragraph = next(
            span
            for span in source.source_span_index["spans"]
            if span.get("kind") == "paragraph"
        )
        span_id = paragraph["source_span_ref_id"]
        client = FixtureCategoryGraphPassClient(
            _pass_outputs_for_span(fixture, span_id)
        )
        result = run_production_extraction(
            ProductionExtractionRequest(
                repo_root=output_dir,
                source=source,
                profile_id=WORLDBUILDING_PROFILE_ID,
                profile_version=WORLDBUILDING_PROFILE_VERSION,
                allow_llm=True,
                category_client=client,
                output_dir=trial_dir,
            )
        )
        graph = result.candidate_graph or {}
        bound_errors = (
            validate_worldbuilding_candidate_bounds(graph) if graph else ["no_candidate"]
        )
        outcome = "passed"
        if result.failure_kind:
            outcome = "failed"
        elif bound_errors:
            outcome = "failed"
        elif result.run.status.value != "reviewable":
            outcome = "failed"
        summaries.append(
            TrialSummary(
                trial_id=trial_id,
                run_id=result.run.run_id,
                status=result.run.status.value,
                failure_kind=result.failure_kind,
                node_count=len(graph.get("nodes") or []),
                edge_count=len(graph.get("edges") or []),
                bound_errors=bound_errors,
                outcome=outcome,
            )
        )

    passed = sum(1 for row in summaries if row.outcome == "passed")
    failed = len(summaries) - passed
    decision = "go" if failed == 0 and passed >= 3 else "no-go"
    report = {
        "schema_version": "dmb_worldbuilding_profile_pilot_v1",
        "cohort_id": cohort_id,
        "profile_id": WORLDBUILDING_PROFILE_ID,
        "profile_version": WORLDBUILDING_PROFILE_VERSION,
        "source_artifact_id": fixture["source_artifact_id"],
        "trials_requested": trials,
        "trials_completed": len(summaries),
        "passed": passed,
        "failed": failed,
        "decision": decision,
        "auto_promotion": False,
        "trials": [asdict(row) for row in summaries],
        "notes": [
            "Aggregate metrics only; no source prose or model payloads.",
            "Candidates remain proposed until Graph Review confirmation.",
        ],
    }
    manifest_path = output_dir / f"{cohort_id}.json"
    manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if args.trials < 1:
        print("trials must be >= 1", file=sys.stderr)
        return 2
    report = run_cohort(trials=args.trials, output_dir=args.output_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["decision"] == "go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
