#!/usr/bin/env python3
"""Bounded PDF/OCR lineage pilot runner (fixture-backed, redacted metrics)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from apps.live_control_server.services.graph_run_registry import (  # noqa: E402
    create_extraction_run,
    get_extraction_run,
    update_extraction_run_status,
)
from graph_memory.ingestion.extraction_run import (  # noqa: E402
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)
from src.graph_memory.extraction.pdf_lineage import PdfLineageError  # noqa: E402
from src.graph_memory.extraction.pdf_source_adapter import (  # noqa: E402
    PdfOcrSourceAdapter,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "pdf_lineage_fixture.json"
DEFAULT_OUT = REPO_ROOT / "out" / "evals" / "pdf_lineage_pilot"


@dataclass
class TrialSummary:
    trial_id: str
    run_id: str
    source_artifact_id: str
    page_span_count: int
    status: str
    outcome: str
    failure_kind: str | None = None


def run_cohort(*, trials: int, output_dir: Path) -> dict:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort_id = datetime.now(UTC).strftime("pdf-cohort-%Y%m%dT%H%M%SZ")
    summaries: list[TrialSummary] = []

    for index in range(1, trials + 1):
        trial_id = f"{cohort_id}-trial-{index}"
        trial_dir = output_dir / trial_id
        trial_dir.mkdir(parents=True, exist_ok=True)
        try:
            source = PdfOcrSourceAdapter(
                pdf_bytes=fixture["pdf_bytes_utf8"].encode("utf-8"),
                ocr_text=fixture["ocr_text"],
                page_map=fixture["page_map"],
                campaign_id="longmont-c2",
            ).normalize()
        except PdfLineageError as exc:
            summaries.append(
                TrialSummary(
                    trial_id=trial_id,
                    run_id="",
                    source_artifact_id="",
                    page_span_count=0,
                    status="failed",
                    outcome="failed",
                    failure_kind=str(exc),
                )
            )
            continue

        span_path = trial_dir / "source_span_index.json"
        span_path.write_text(
            json.dumps(source.source_span_index, indent=2) + "\n", encoding="utf-8"
        )
        candidate_path = trial_dir / "candidate_graph.json"
        candidate_path.write_text(
            json.dumps(
                {
                    "schema": "dmb_candidate_graph_preview_v0",
                    "session_id": None,
                    "campaign_id": "longmont-c2",
                    "source_artifact_ids": [source.source_artifact_id],
                    "nodes": [
                        {
                            "node_id": "creature:stonefist-brute",
                            "label": "Stonefist Brute",
                            "node_type": "creature",
                            "evidence_refs": [
                                {
                                    "source_span_ref_id": source.source_span_index["spans"][0][
                                        "source_span_ref_id"
                                    ],
                                    "anchor_quotes": ["Stonefist Brute"],
                                }
                            ],
                        }
                    ],
                    "edges": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        components = {
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri=source.source_uri,
                exists=True,
                sha256=source.source_sha256,
            ),
            "source_span_index": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
                uri=span_path.as_posix(),
                exists=True,
            ),
            "candidate_graph": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                uri=candidate_path.as_posix(),
                exists=True,
            ),
        }
        created = create_extraction_run(
            output_dir,
            source_artifact_id=source.source_artifact_id,
            source_domain=source.source_domain,
            campaign_id=source.campaign_id,
            session_id=None,
            profile_id="pdf_mechanical_pilot_v0@0.1",
            components=components,
            status=ExtractionRunStatus.DRAFT,
        )
        updated = update_extraction_run_status(
            output_dir,
            created.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            components=components,
        )
        reloaded = get_extraction_run(output_dir, updated.run_id)
        span_payload = json.loads(
            Path(reloaded.components["source_span_index"].uri).read_text(encoding="utf-8")
        )
        page_ok = all(
            span.get("kind") == "pdf_page_region" and "page" in span
            for span in span_payload.get("spans") or []
        )
        summaries.append(
            TrialSummary(
                trial_id=trial_id,
                run_id=reloaded.run_id,
                source_artifact_id=reloaded.source_artifact_id,
                page_span_count=len(span_payload.get("spans") or []),
                status=reloaded.status.value,
                outcome="passed" if page_ok and reloaded.is_reviewable() else "failed",
                failure_kind=None if page_ok else "missing_page_lineage",
            )
        )

    passed = sum(1 for row in summaries if row.outcome == "passed")
    failed = len(summaries) - passed
    # Stable identity across trials for same PDF/OCR inputs.
    identities = {row.source_artifact_id for row in summaries if row.source_artifact_id}
    decision = "go" if failed == 0 and passed >= 3 and len(identities) == 1 else "no-go"
    report = {
        "schema_version": "dmb_pdf_lineage_pilot_v1",
        "cohort_id": cohort_id,
        "trials_requested": trials,
        "trials_completed": len(summaries),
        "passed": passed,
        "failed": failed,
        "canonical_source_identities": sorted(identities),
        "decision": decision,
        "auto_promotion": False,
        "trials": [asdict(row) for row in summaries],
        "notes": [
            "Aggregate metrics only; no OCR prose or PDF bytes in the report.",
            "Graph Review remains the only publication path.",
        ],
    }
    (output_dir / f"{cohort_id}.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    report = run_cohort(trials=args.trials, output_dir=args.output_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["decision"] == "go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
