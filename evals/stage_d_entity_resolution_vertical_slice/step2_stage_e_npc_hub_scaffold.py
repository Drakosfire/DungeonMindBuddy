"""Stage E: scaffold branch-model NPC hubs from Stage D promotion sidecars.

Consumes ``branch_scaffold_proposals[]`` emitted by
``scripts/promote_stage_d_proposals.py`` and routes all writes through
``src.agent.corpus_writer.write_corpus_file``.

Default behavior is preview-only (two-phase dry run). ``--commit`` opt-in
performs the second phase immediately using each preview's confirm token.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.corpus_writer import write_corpus_file
from evals.stage_d_entity_resolution_vertical_slice.stage_e_scaffold_grader import (
    grade_stage_e_scaffold,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CORPUS_ROOT = _REPO_ROOT / "corpus" / "eldyrwild-markdown"
_DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "scaffold"


def _norm_hub_dir(path: str | None) -> str:
    p = str(path or "").strip().replace("\\", "/")
    if not p:
        return ""
    return p if p.endswith("/") else f"{p}/"


def _build_campaign_readme(
    *,
    slug: str,
    display_name: str,
    campaign_id: str,
    location_slug: str | None,
    world_parent_hub_path: str | None,
    divergence_mode: str | None,
) -> str:
    loc = str(location_slug or "").strip() or "unknown_location"
    world_parent = str(world_parent_hub_path or "").strip() or "null"
    divergence = str(divergence_mode or "").strip() or "inherit"
    return (
        "---\n"
        f"title: {display_name}\n"
        "subject_class: npc\n"
        "subject_doc_kind: hub_index\n"
        "document_class: reference\n"
        "canon_layer: campaign\n"
        f"campaign_id: {campaign_id}\n"
        "temporal_scope: campaign_stateful\n"
        f"world_hub_path: {world_parent}\n"
        f"divergence_mode: {divergence}\n"
        f"primary_location_slug: {loc}\n"
        "---\n\n"
        f"# {display_name}\n\n"
        "## Suggested reads (in order)\n\n"
        f"1. `{slug}_character_dossier.md` - Campaign-facing dossier.\n"
        "2. `timeline.md` - Session-indexed continuity row pointers.\n"
    )


def _build_campaign_timeline(*, display_name: str) -> str:
    return (
        f"# {display_name} timeline\n\n"
        "| Session | Beat (short) | Recap / prep |\n"
        "| --- | --- | --- |\n"
    )


def _build_setting_readme(
    *,
    display_name: str,
    location_slug: str | None,
) -> str:
    loc = str(location_slug or "").strip() or "unknown_location"
    return (
        "---\n"
        f"title: {display_name}\n"
        "subject_class: npc\n"
        "subject_doc_kind: hub_index\n"
        "document_class: world\n"
        "canon_layer: world\n"
        "campaign_id: null\n"
        "temporal_scope: evergreen\n"
        f"primary_location_slug: {loc}\n"
        "---\n\n"
        f"# {display_name}\n\n"
        "## Suggested reads (in order)\n\n"
        "1. `character_seed.md` - World-level seed profile.\n"
    )


def _build_setting_seed(*, display_name: str) -> str:
    return (
        f"# {display_name} - character seed\n\n"
        "- Origin: TBD\n"
        "- Core motivation: TBD\n"
        "- Signature detail: TBD\n"
    )


def _build_ops(payload: dict[str, Any]) -> list[dict[str, str]]:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    rows = payload.get("branch_scaffold_proposals") or []
    ops: list[dict[str, str]] = []
    for row in rows:
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        display_name = str(row.get("display_name") or slug).strip()
        location_slug = row.get("location_slug")
        divergence_mode = row.get("divergence_mode")
        world_hub = _norm_hub_dir(row.get("world_parent_hub_path"))
        camp_hub = _norm_hub_dir(row.get("campaign_overlay_hub_path"))
        if world_hub:
            ops.append(
                {
                    "path": f"{world_hub}README.md",
                    "mode": "create",
                    "content": _build_setting_readme(
                        display_name=display_name,
                        location_slug=location_slug,
                    ),
                }
            )
            ops.append(
                {
                    "path": f"{world_hub}character_seed.md",
                    "mode": "create",
                    "content": _build_setting_seed(display_name=display_name),
                }
            )
        if camp_hub:
            ops.append(
                {
                    "path": f"{camp_hub}README.md",
                    "mode": "create",
                    "content": _build_campaign_readme(
                        slug=slug,
                        display_name=display_name,
                        campaign_id=campaign_id,
                        location_slug=location_slug,
                        world_parent_hub_path=(f"{world_hub}README.md" if world_hub else None),
                        divergence_mode=divergence_mode,
                    ),
                }
            )
            ops.append(
                {
                    "path": f"{camp_hub}timeline.md",
                    "mode": "create",
                    "content": _build_campaign_timeline(display_name=display_name),
                }
            )
            ops.append(
                {
                    "path": f"{camp_hub}{slug}_character_dossier.md",
                    "mode": "create",
                    "content": (
                        f"# {display_name} dossier\n\n"
                        "## Summary\n\n"
                        "TBD.\n"
                    ),
                }
            )
    return ops


def run_stage_e_scaffold(
    *,
    promotion_json: Path,
    corpus_root: Path = _DEFAULT_CORPUS_ROOT,
    commit: bool = False,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    payload = json.loads(promotion_json.read_text(encoding="utf-8"))
    ops = _build_ops(payload)
    when = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    for op in ops:
        rel = str(op["path"])
        if (corpus_root / rel).exists():
            results.append({"path": rel, "mode": op["mode"], "status": "skipped_existing"})
            continue
        preview = write_corpus_file(
            corpus_root,
            path=rel,
            mode=str(op["mode"]),
            content=str(op["content"]),
            dry_run=True,
        )
        row: dict[str, Any] = {
            "path": rel,
            "mode": op["mode"],
            "status": "preview_ok" if preview.get("ok") else "preview_error",
            "preview": preview,
        }
        if commit and preview.get("ok"):
            committed = write_corpus_file(
                corpus_root,
                path=rel,
                mode=str(op["mode"]),
                content=str(op["content"]),
                dry_run=False,
                confirm_token=str(preview.get("confirm_token") or ""),
            )
            row["commit"] = committed
            row["status"] = "committed" if committed.get("ok") else "commit_error"
        results.append(row)

    report = {
        "schema": "stage_e_npc_hub_scaffold_v1",
        "generated_at": when.isoformat(),
        "campaign_id": payload.get("campaign_id"),
        "promotion_source": str(promotion_json),
        "commit": bool(commit),
        "counts": {
            "ops_total": len(ops),
            "preview_ok": sum(1 for r in results if r.get("status") == "preview_ok"),
            "preview_error": sum(1 for r in results if r.get("status") == "preview_error"),
            "committed": sum(1 for r in results if r.get("status") == "committed"),
            "commit_error": sum(1 for r in results if r.get("status") == "commit_error"),
            "skipped_existing": sum(
                1 for r in results if r.get("status") == "skipped_existing"
            ),
        },
        "ops": results,
    }
    report["grading"] = grade_stage_e_scaffold(report, corpus_root=corpus_root)

    out_root = out_dir or _DEFAULT_OUT_DIR
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = when.strftime("%Y%m%dT%H%M%S") + "Z"
    out_path = out_root / f"stage_e_hub_scaffold_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["report_path"] = str(out_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage E scaffold: build world+campaign NPC hubs from promotion sidecar."
    )
    parser.add_argument("--promotion-json", required=True, type=Path)
    parser.add_argument("--corpus-root", type=Path, default=_DEFAULT_CORPUS_ROOT)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    report = run_stage_e_scaffold(
        promotion_json=args.promotion_json,
        corpus_root=args.corpus_root,
        commit=bool(args.commit),
        out_dir=args.out_dir,
    )
    print(
        json.dumps(
            {
                "report_path": report.get("report_path"),
                "counts": report["counts"],
                "gates_passed": (report.get("grading") or {}).get("gates_passed"),
            }
        )
    )


if __name__ == "__main__":
    main()
