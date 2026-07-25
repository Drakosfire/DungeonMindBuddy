#!/usr/bin/env python3
"""Local repeat-trial cohort runner for the bounded worldbuilding profile.

Uses the redacted fixture and deterministic pass client — no live corpus or
model payloads are written into the report.

Decision scope: deterministic contract/plumbing proof only. Three fixture
replays are not independent extraction-quality trials.
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

from apps.live_control_server.services.source_artifact_registry import (  # noqa: E402
    create_source_artifact_from_workspace_document,
    load_registered_source_artifact_text,
    load_source_span_index,
)
from apps.live_control_server.services.workspace_document_registry import (  # noqa: E402
    create_workspace_document,
    mark_workspace_document_committed,
)
from graph_memory.source_span import source_span_index_to_dict  # noqa: E402
from src.graph_memory.extraction.category_candidate_graph_extractor import (  # noqa: E402
    FixtureCategoryGraphPassClient,
)
from src.graph_memory.extraction.graph_preview_runner import (  # noqa: E402
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.source_adapter import (  # noqa: E402
    NormalizedExtractionSource,
)
from src.graph_memory.extraction.worldbuilding_extraction_profile import (  # noqa: E402
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
    validate_worldbuilding_candidate_bounds,
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
    source_artifact_id: str
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


def _admit_fixture_source(repo_root: Path, fixture: dict, trial_id: str) -> tuple[
    NormalizedExtractionSource, str
]:
    record = create_workspace_document(
        repo_root,
        title=f"Shepherd's Flock fixture {trial_id}",
        campaign_id=fixture["campaign_id"],
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class=fixture["document_class"],
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        repo_root, record.document_id, expected_revision=1
    )
    target = repo_root / committed.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    content = str(fixture["source_text"]).rstrip("\n") + "\n"
    target.write_text(content, encoding="utf-8")
    artifact = create_source_artifact_from_workspace_document(
        repo_root,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    registered, text = load_registered_source_artifact_text(
        repo_root, artifact.source_artifact_id
    )
    index = load_source_span_index(repo_root, artifact.source_artifact_id)
    index_payload = source_span_index_to_dict(index)
    first_span = (index_payload.get("spans") or [None])[0]
    if not isinstance(first_span, dict):
        raise RuntimeError("registered source span index has no spans")
    span_id = str(
        first_span.get("source_span_id") or first_span.get("source_span_ref_id") or ""
    )
    if not span_id:
        raise RuntimeError("registered span missing source_span_id")
    source = NormalizedExtractionSource(
        source_artifact_id=registered.source_artifact_id,
        source_domain=str(registered.source_domain),
        source_text=text,
        source_sha256=registered.content_sha256 or "",
        source_uri=registered.uri,
        campaign_id=registered.campaign_id,
        session_id=registered.session_id,
        document_class=registered.document_class,
        source_span_index=index_payload,
    )
    return source, span_id


def run_cohort(*, trials: int, output_dir: Path) -> dict:
    fixture = _load_fixture()
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort_id = datetime.now(UTC).strftime("wb-cohort-%Y%m%dT%H%M%SZ")
    summaries: list[TrialSummary] = []

    for index in range(1, trials + 1):
        trial_id = f"{cohort_id}-trial-{index}"
        trial_dir = output_dir / trial_id
        # Isolate registry + run artifacts under one repo root so component URIs
        # remain repo-relative.
        trial_repo = trial_dir / "repo"
        trial_repo.mkdir(parents=True, exist_ok=True)
        source, span_id = _admit_fixture_source(trial_repo, fixture, trial_id)
        client = FixtureCategoryGraphPassClient(
            _pass_outputs_for_span(fixture, span_id)
        )
        result = run_production_extraction(
            ProductionExtractionRequest(
                repo_root=trial_repo,
                source=source,
                profile_id=WORLDBUILDING_PROFILE_ID,
                profile_version=WORLDBUILDING_PROFILE_VERSION,
                allow_llm=True,
                category_client=client,
                output_dir=trial_repo / "out" / "runs" / trial_id,
            )
        )
        graph = result.candidate_graph or {}
        # Bounds are enforced by the production runtime via
        # profile.post_extraction_validator. Re-check here only as a report
        # diagnostic; do not treat a post-hoc standalone pass as the proof.
        bound_errors = (
            validate_worldbuilding_candidate_bounds(graph) if graph else ["no_candidate"]
        )
        outcome = "passed"
        if result.failure_kind:
            outcome = "failed"
        elif result.run.status.value != "reviewable":
            outcome = "failed"
        elif bound_errors:
            outcome = "failed"
        summaries.append(
            TrialSummary(
                trial_id=trial_id,
                run_id=result.run.run_id,
                source_artifact_id=source.source_artifact_id,
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
    decision = (
        "go_deterministic_plumbing"
        if failed == 0 and passed >= 3
        else "no-go"
    )
    report = {
        "schema_version": "dmb_worldbuilding_profile_pilot_v1",
        "cohort_id": cohort_id,
        "profile_id": WORLDBUILDING_PROFILE_ID,
        "profile_version": WORLDBUILDING_PROFILE_VERSION,
        "fixture_source_artifact_id": fixture["source_artifact_id"],
        "source_artifact_ids": [row.source_artifact_id for row in summaries],
        "trials_requested": trials,
        "trials_completed": len(summaries),
        "passed": passed,
        "failed": failed,
        "decision": decision,
        "decision_scope": "deterministic_contract_plumbing_only",
        "auto_promotion": False,
        "extraction_quality_proven": False,
        "trials": [asdict(row) for row in summaries],
        "notes": [
            "Aggregate metrics only; no source prose or model payloads.",
            "Three fixture replays prove plumbing, not independent extraction quality.",
            "Candidates remain inspect-only (BLD-07); no worldbuilding publication path.",
            "Per-trial source_artifact_id is the registered runtime artifact, not fixture metadata.",
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
    return 0 if report["decision"] == "go_deterministic_plumbing" else 1


if __name__ == "__main__":
    raise SystemExit(main())
