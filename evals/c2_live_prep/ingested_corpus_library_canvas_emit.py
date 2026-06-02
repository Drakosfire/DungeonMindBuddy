#!/usr/bin/env python3
"""Emit ingested corpus library canvas sidecar from ingested_corpus_library.json."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_ingested_corpus_library import build_library  # noqa: E402

DEFAULT_LIBRARY = ROOT / "Docs/data/ingested-corpus-library/ingested_corpus_library.json"
TEMPLATE = ROOT / "evals/c2_live_prep/canvas_templates/ingested-corpus-library.canvas.tsx"
CANVAS_NAME = "ingested-corpus-library.canvas.tsx"


def _compact_payload(lib: dict) -> dict:
    rows = []
    for camp in lib["campaigns"]:
        for s in camp["sessions"]:
            stages = s.get("stages") or {}
            rows.append(
                {
                    "campaign": camp["campaign_id"].replace("longmont-c", "C"),
                    "session": s["session"],
                    "tier": s["pipeline_tier"],
                    "canon": "canon_recap" in stages,
                    "norm": "normalized" in stages,
                    "crumb": "breadcrumbed" in stages,
                    "memory": "session_memory_jsonl" in stages,
                    "staging": "ingest_staging" in stages,
                    "blessed": s.get("pilot_blessed", False),
                    "genericTitle": (stages.get("canon_recap") or {}).get("generic_title", False),
                }
            )
    hubs = []
    for camp in lib["campaigns"]:
        for kind, hub in (camp.get("hubs") or {}).items():
            if not hub.get("entity_count"):
                continue
            totals = hub.get("file_kind_totals") or {}
            hubs.append(
                {
                    "campaign": camp["campaign_id"].replace("longmont-c", "C"),
                    "kind": kind,
                    "entities": hub["entity_count"],
                    "readme": totals.get("readme", 0),
                    "dossier": totals.get("dossier", 0),
                    "timeline": totals.get("timeline", 0),
                    "statblock": totals.get("statblock", 0),
                    "other": totals.get("other", 0),
                }
            )
    ra = lib["retrieval_activation"]
    dogfood = ra.get("c2s23_dogfood_full_manifest") or {}
    return {
        "generatedAt": lib["generated_at"],
        "corpusRoot": lib["corpus_root"],
        "totalMdFiles": lib["summary"]["total_corpus_md_files"],
        "retrieval": {
            "manifestEntries": ra["c2s23_planning_manifest"]["entry_count"],
            "sourceSessions": ra["c2s23_planning_manifest"]["source_sessions"],
            "onDiskRoutes": ra["ingest_routes_on_disk"],
            "inManifest": ra["ingest_routes_in_c2s23_manifest"],
            "notInManifest": ra["ingest_routes_not_in_c2s23_manifest"],
            "dogfoodManifestEntries": dogfood.get("entry_count", 0),
            "dogfoodSourceSessions": dogfood.get("source_sessions") or [],
            "inDogfoodManifest": ra.get("ingest_routes_in_dogfood_full_manifest", 0),
            "notInDogfoodManifest": ra.get("ingest_routes_not_in_dogfood_full_manifest", 0),
        },
        "tierCounts": lib["summary"]["session_pipeline_tiers"],
        "sessions": rows,
        "hubs": hubs,
        "prepCounts": {
            c["campaign_id"].replace("longmont-c", "C"): len(c.get("session_prep") or []) for c in lib["campaigns"]
        },
        "looseMdCounts": {
            c["campaign_id"].replace("longmont-c", "C"): len(c.get("loose_markdown") or []) for c in lib["campaigns"]
        },
        "elderwyldMd": lib["elderwyld"].get("md_file_count", 0),
        "liveWorkspaces": [
            {
                "session": w.get("session"),
                "dir": w.get("workspace_dir"),
                "artifacts": [a["basename"] for a in w.get("artifacts") or []],
            }
            for w in lib.get("live_workspaces") or []
        ],
        "notInManifestSamples": (ra.get("sample_routes_not_in_manifest") or [])[:12],
        "gaps": [
            {
                "id": "c1",
                "label": "Campaign 1 (17 sessions)",
                "detail": (
                    "Full recap + normalized on disk; 4 sessions with breadcrumb/memory. "
                    "Entire campaign absent from C2S23 retrieval manifest."
                ),
            },
            {
                "id": "c2_early",
                "label": "C2 sessions 1–19",
                "detail": (
                    "Canon + normalized only — no breadcrumb, no session_memory jsonl. "
                    "Play text exists but not in lexical memory pipeline."
                ),
            },
            {
                "id": "c2_s20",
                "label": "C2 session 20",
                "detail": (
                    "Full breadcrumb + session memory on disk; excluded from manifest. "
                    'Canon title still generic "Session 20 - Recap.md".'
                ),
            },
            {
                "id": "hubs",
                "label": "Hub satellites",
                "detail": (
                    "Manifest activates 13 hub READMEs only. "
                    "Dossiers, timelines, and C2 PC statblocks are not retrieval routes."
                ),
            },
            {
                "id": "elderwyld",
                "label": "Elderwyld world layer",
                "detail": f"{lib['elderwyld'].get('md_file_count', 0)} markdown files — zero manifest entries.",
            },
            {
                "id": "s23",
                "label": "Session 23",
                "detail": "Live workspace recap + packet only; not yet written to corpus Session Recaps.",
            },
            {
                "id": "roll_tables",
                "label": "Roll tables",
                "detail": (
                    "Travel/encounter tables live inside prep markdown. No roll_table manifest role entries."
                ),
            },
        ],
    }


def _canvas_targets() -> list[Path]:
    home = Path.home()
    bases = [
        home / ".cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases",
        home / ".cursor/projects/home-drakosfire-Projects-DungeonOverMind/canvases",
    ]
    return [b for b in bases if b.is_dir()] or [bases[0]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--rebuild-library", action="store_true")
    args = parser.parse_args()

    if args.rebuild_library or not args.library.is_file():
        lib_full = build_library(root=ROOT)
        args.library.parent.mkdir(parents=True, exist_ok=True)
        args.library.write_text(json.dumps(lib_full, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        lib = lib_full
    else:
        lib = json.loads(args.library.read_text(encoding="utf-8"))

    payload = _compact_payload(lib)
    sidecar_body = {"ingestedCorpusPayload": payload}
    report: dict = {"targets": [], "session_count": len(payload["sessions"])}

    for canvases_dir in _canvas_targets():
        canvases_dir.mkdir(parents=True, exist_ok=True)
        canvas_tsx = canvases_dir / CANVAS_NAME
        data_json = canvases_dir / CANVAS_NAME.replace(".canvas.tsx", ".canvas.data.json")
        shell_action = "canvas_unchanged"
        if not canvas_tsx.is_file() and TEMPLATE.is_file():
            shutil.copy2(TEMPLATE, canvas_tsx)
            shell_action = "canvas_created"
        data_json.write_text(json.dumps(sidecar_body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["targets"].append(
            {
                "canvases_dir": str(canvases_dir),
                "canvas_tsx": str(canvas_tsx),
                "canvas_shell": shell_action,
                "canvas_data_json": str(data_json),
                "data_updated": True,
            }
        )

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
