"""Manual dogfood runner for the `category_encounter_job_preview` extraction profile.

Runs the real runtime preview graph-ingest path (`build_recap_graph_preview_bundle`)
against a real recap with live model-backed category extraction. This is preview-only:
no corpus mutation, no canon promotion, no approved graph-memory write.

Usage:
    python -m evals.graph_memory_layer.run_encounter_job_dogfood \
        --campaign-id longmont-c1 --session 1 \
        --recap-path "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (REPO_ROOT, REPO_ROOT / "src"):
    value = str(_path)
    if value not in sys.path:
        sys.path.insert(0, value)

from apps.live_control_server.services.recap_graph_preview_ingest import (
    build_recap_graph_preview_bundle,
    materialize_recap_preview_supergraph,
)

DEFAULT_CAMPAIGN_ID = "longmont-c1"
DEFAULT_SESSION = 1
DEFAULT_RECAP_PATH = (
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/"
    "_normalized/Session 01 - Stonebridge and Glowkindle Rats.md"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--session", type=int, default=DEFAULT_SESSION)
    parser.add_argument("--recap-path", default=DEFAULT_RECAP_PATH)
    parser.add_argument(
        "--graph-extraction-profile",
        default="category_encounter_job_preview",
    )
    parser.add_argument("--model-id", default=None)
    parser.add_argument(
        "--force-graph-run",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--materialize-preview-union",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Also materialize the preview union supergraph store, advancing the run to "
            "preview_union_store_ready so it is selectable in the Gold Review run picker."
        ),
    )
    args = parser.parse_args()

    if args.materialize_preview_union:
        status = materialize_recap_preview_supergraph(
            repo_root=REPO_ROOT,
            campaign_id=args.campaign_id,
            session=args.session,
            normalized_recap_path=args.recap_path,
            force_graph_run=args.force_graph_run,
            extract_graph=True,
            graph_model_id=args.model_id,
            graph_extraction_profile=args.graph_extraction_profile,
        )
    else:
        status = build_recap_graph_preview_bundle(
            repo_root=REPO_ROOT,
            campaign_id=args.campaign_id,
            session=args.session,
            normalized_recap_path=args.recap_path,
            force_graph_run=args.force_graph_run,
            extract_graph=True,
            graph_model_id=args.model_id,
            graph_extraction_profile=args.graph_extraction_profile,
        )
    print(json.dumps(status, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
