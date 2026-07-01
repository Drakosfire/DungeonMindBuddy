"""Manual dogfood runner for the `category_encounter_job_preview` extraction profile.

Runs the real runtime preview graph-ingest path (`build_recap_graph_preview_bundle`)
against a real recap with live model-backed category extraction. This is preview-only:
no corpus mutation, no canon promotion, no approved graph-memory write.

Usage:
    python -m evals.graph_memory_layer.run_encounter_job_dogfood \
        --campaign-id longmont-c1 --session 1 \
        --recap-path "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md"

Add ``--enable-vocabulary-packet`` to also enable the static, corpus/registry-derived
context vocabulary packet (the same packet built by
``run_vocabulary_ablation_expanded_beds_dogfood.py``'s ``c1s1-stonebridge`` bed) on both
the node and edge passes, for a baseline-vs-vocabulary-assisted comparison under the
encounter/job profile.
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
    parser.add_argument(
        "--enable-vocabulary-packet",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Enable the static, corpus/registry-derived context vocabulary packet "
            "(node + edge) on this run, for baseline-vs-vocabulary comparison. Only "
            "the c1s1-stonebridge packet is wired up; other campaigns/sessions raise."
        ),
    )
    args = parser.parse_args()

    context_vocabulary_packet = None
    if args.enable_vocabulary_packet:
        if args.campaign_id != "longmont-c1" or args.session != 1:
            raise SystemExit(
                "--enable-vocabulary-packet only has a packet wired up for "
                "longmont-c1 session 1 (c1s1-stonebridge); pass --campaign-id "
                "longmont-c1 --session 1 or omit the flag."
            )
        from evals.graph_memory_layer.run_vocabulary_ablation_expanded_beds_dogfood import (
            BED_CONFIGS,
        )

        bed = BED_CONFIGS["c1s1-stonebridge"]
        context_vocabulary_packet = bed.build_packet(bed)

    vocabulary_kwargs = (
        {
            "context_vocabulary_packet": context_vocabulary_packet,
            "enable_node_vocabulary_packet": True,
            "enable_edge_vocabulary_packet": True,
        }
        if context_vocabulary_packet is not None
        else {}
    )

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
            **vocabulary_kwargs,
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
            **vocabulary_kwargs,
        )
    print(json.dumps(status, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
