#!/usr/bin/env python3
"""Operator CLI for Eldyrwild C2 world graph materialization (PR006)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from graph_memory.materialization.acceptance_manifest import (  # noqa: E402
    AcceptanceManifestError,
    build_inventory,
    load_acceptance_manifest,
)
from graph_memory.materialization.candidate_bundle import (  # noqa: E402
    load_candidate_bundle,
    validate_candidate_bundle,
)
from graph_memory.materialization.world_materializer import (  # noqa: E402
    materialize_world_graph,
    verify_materialization,
    verify_rebuild,
    write_report_json,
)


def _cmd_inventory(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = load_acceptance_manifest(manifest_path)
    try:
        inventory = build_inventory(
            manifest,
            repo_root=Path(args.repo_root),
            manifest_path=manifest_path,
        )
    except AcceptanceManifestError as exc:
        print(json.dumps({"ok": False, "errors": exc.errors}, indent=2), file=sys.stderr)
        return 1
    # Automation contract (§7): inventory JSON has world_id / recap_count at top level.
    text = json.dumps(inventory, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


def _cmd_validate_bundle(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    bundle_path = Path(args.bundle)
    manifest = load_acceptance_manifest(manifest_path)
    bundle = load_candidate_bundle(bundle_path)
    manifest_sha = None
    inventory_paths = None
    try:
        inventory = build_inventory(
            manifest,
            repo_root=Path(args.repo_root),
            manifest_path=manifest_path,
        )
        inventory_paths = {item["path"] for item in inventory["source_items"]}
        manifest_sha = inventory.get("manifest_sha256")
    except AcceptanceManifestError:
        inventory_paths = None
    errors = validate_candidate_bundle(
        bundle,
        manifest_sha256=manifest_sha,
        inventory=inventory,
    )
    payload = {"ok": not errors, "errors": errors}
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 1


def _cmd_materialize(args: argparse.Namespace) -> int:
    try:
        report = materialize_world_graph(
            repo_root=Path(args.repo_root),
            store_root=Path(args.store_root),
            manifest_path=Path(args.manifest),
            bundle_path=Path(args.bundle),
            fresh_root=args.fresh_root,
            expected_parent_revision_id=args.expected_parent_revision,
        )
    except AcceptanceManifestError as exc:
        print(json.dumps({"ok": False, "errors": exc.errors}, indent=2), file=sys.stderr)
        return 1
    if args.report:
        write_report_json(report, Path(args.report))
    # Automation: report fields at top level (plus ok).
    print(json.dumps({"ok": True, **report}, indent=2))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    world_id = args.world_id or "eldyrwild"
    payload = verify_materialization(Path(args.store_root), world_id)
    print(json.dumps({"ok": True, **payload}, indent=2))
    return 0


def _cmd_verify_rebuild(args: argparse.Namespace) -> int:
    world_id = args.world_id or "eldyrwild"
    payload = verify_rebuild(Path(args.store_root), world_id)
    ok = payload.get("rebuild_equivalent_to_head") is True
    print(json.dumps({"ok": ok, **payload}, indent=2))
    return 0 if ok else 1

def main() -> int:
    parser = argparse.ArgumentParser(description="Eldyrwild C2 world graph materialization")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_repo_root(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--repo-root", default=str(_REPO_ROOT))

    inv = sub.add_parser("inventory")
    add_repo_root(inv)
    inv.add_argument("--manifest", required=True)
    inv.add_argument("--output")
    inv.set_defaults(func=_cmd_inventory)

    vb = sub.add_parser("validate-bundle")
    add_repo_root(vb)
    vb.add_argument("--manifest", required=True)
    vb.add_argument("--bundle", required=True)
    vb.set_defaults(func=_cmd_validate_bundle)

    mat = sub.add_parser("materialize")
    add_repo_root(mat)
    mat.add_argument("--manifest", required=True)
    mat.add_argument("--bundle", required=True)
    mat.add_argument("--store-root", required=True)
    mat.add_argument("--fresh-root", action="store_true")
    mat.add_argument("--expected-parent-revision")
    mat.add_argument("--report")
    mat.set_defaults(func=_cmd_materialize)

    ver = sub.add_parser("verify")
    ver.add_argument("--store-root", required=True)
    ver.add_argument("--world-id", default="eldyrwild")
    ver.set_defaults(func=_cmd_verify)

    vrb = sub.add_parser("verify-rebuild")
    vrb.add_argument("--store-root", required=True)
    vrb.add_argument("--world-id", default="eldyrwild")
    vrb.set_defaults(func=_cmd_verify_rebuild)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
