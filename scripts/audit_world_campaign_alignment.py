#!/usr/bin/env python3
"""Deterministic world/campaign alignment audit.

This script hard-fails three contract classes:
1) NPC registry authority split violations (delegated to lint_npc_registry).
2) Remote normalization manifests with non-normalized campaign IDs.
3) Breadcrumb natural-query scenarios that require hierarchy equivalences but
   omit them.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import lint_npc_registry


_CAMPAIGN_ID_RE = re.compile(r"^longmont-c[1-9][0-9]*$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_corpus_root() -> Path:
    return _repo_root() / "corpus" / "eldyrwild-markdown"


def _default_schema_path() -> Path:
    return _repo_root() / "schemas" / "v0.1" / "npc_registry.schema.json"


def _default_manifest_path() -> Path:
    return _repo_root() / "out" / "evals" / "corpus_remote" / "normalization_manifest.json"


def _default_breadcrumb_gold_glob() -> str:
    return "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural*.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_registry_authority(*, corpus_root: Path, schema_path: Path) -> list[str]:
    issues: list[str] = []
    registry_paths = sorted(corpus_root.rglob("_npc_registry.json"))
    if not registry_paths:
        return [f"registry: no registry files found under {corpus_root}"]

    for registry_path in registry_paths:
        record_count, ok_count, lines = lint_npc_registry.lint_registry(
            registry_path=registry_path,
            corpus_root=corpus_root,
            schema_path=schema_path,
        )
        if any(line.startswith("ERROR:") for line in lines):
            for line in lines:
                if line.startswith("ERROR:"):
                    issues.append(f"registry:{registry_path}: {line}")
            continue
        if record_count != ok_count:
            for line in lines:
                if line.startswith("ISSUE "):
                    issues.append(f"registry:{registry_path}: {line}")
    return issues


def audit_manifest_campaign_ids(*, manifest_paths: list[Path]) -> list[str]:
    issues: list[str] = []
    for manifest_path in manifest_paths:
        if not manifest_path.is_file():
            issues.append(f"manifest:{manifest_path}: file not found")
            continue
        payload = _load_json(manifest_path)
        docs = payload.get("documents")
        if not isinstance(docs, list):
            issues.append(f"manifest:{manifest_path}: documents must be a list")
            continue
        for idx, doc in enumerate(docs):
            if not isinstance(doc, dict):
                issues.append(f"manifest:{manifest_path}: documents[{idx}] must be an object")
                continue
            layer = str(doc.get("canon_layer") or "")
            campaign_id = doc.get("campaign_id")
            if layer != "campaign":
                continue
            if not isinstance(campaign_id, str) or not _CAMPAIGN_ID_RE.fullmatch(campaign_id):
                route = str(doc.get("remote_path") or f"<index:{idx}>")
                issues.append(
                    "manifest:"
                    f"{manifest_path}: campaign document {route!r} has non-normalized "
                    f"campaign_id={campaign_id!r}; expected longmont-cN"
                )
    return issues


def _is_parent_label_route(route: str) -> bool:
    return "/" not in route


def _scenario_requires_hierarchy_equivalences(scenario: dict[str, Any]) -> bool:
    explicit = scenario.get("requires_location_hierarchy_equivalences")
    if isinstance(explicit, bool):
        return explicit

    lane = str(scenario.get("benchmark_lane") or "").strip().lower()
    routes = [str(r).strip() for r in (scenario.get("expect_route_substrings") or []) if str(r).strip()]
    return lane == "location_context" and any(_is_parent_label_route(r) for r in routes)


def audit_location_hierarchy_contracts(*, gold_paths: list[Path]) -> list[str]:
    issues: list[str] = []
    for gold_path in gold_paths:
        if not gold_path.is_file():
            issues.append(f"hierarchy:{gold_path}: file not found")
            continue
        payload = _load_json(gold_path)
        scenarios = payload.get("scenarios")
        if not isinstance(scenarios, list):
            issues.append(f"hierarchy:{gold_path}: scenarios must be a list")
            continue

        for idx, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                issues.append(f"hierarchy:{gold_path}: scenarios[{idx}] must be an object")
                continue
            if not _scenario_requires_hierarchy_equivalences(scenario):
                continue

            sid = str(scenario.get("id") or f"<index:{idx}>")
            expected_routes = {
                str(r).strip().lower()
                for r in (scenario.get("expect_route_substrings") or [])
                if str(r).strip()
            }
            mapping = scenario.get("location_hierarchy_equivalences")
            if not isinstance(mapping, dict) or not mapping:
                issues.append(
                    "hierarchy:"
                    f"{gold_path}:{sid}: requires non-empty location_hierarchy_equivalences"
                )
                continue

            keys = {str(k).strip().lower() for k in mapping.keys() if str(k).strip()}
            if not keys.intersection(expected_routes):
                issues.append(
                    "hierarchy:"
                    f"{gold_path}:{sid}: hierarchy keys must include at least one expected route "
                    f"substring ({sorted(expected_routes)})"
                )

            for parent, children in mapping.items():
                if not isinstance(children, list) or not children:
                    issues.append(
                        "hierarchy:"
                        f"{gold_path}:{sid}: parent {parent!r} must map to a non-empty list"
                    )
                    continue
                for child in children:
                    if not isinstance(child, str) or not child.strip():
                        issues.append(
                            "hierarchy:"
                            f"{gold_path}:{sid}: parent {parent!r} has blank/non-string child value"
                        )
                        break
    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=_default_corpus_root(),
        help="Corpus root containing campaign registries.",
    )
    parser.add_argument(
        "--npc-registry-schema",
        type=Path,
        default=_default_schema_path(),
        help="Path to schemas/v0.1/npc_registry.schema.json.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        action="append",
        default=None,
        help=(
            "Path to normalization_manifest.json. Repeat for multiple manifests. "
            "Default: out/evals/corpus_remote/normalization_manifest.json"
        ),
    )
    parser.add_argument(
        "--breadcrumb-gold-glob",
        type=str,
        default=_default_breadcrumb_gold_glob(),
        help="Repo-relative glob for breadcrumb natural gold files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = _repo_root()

    manifest_paths = args.manifest if args.manifest else [_default_manifest_path()]
    gold_paths = sorted(repo_root.glob(str(args.breadcrumb_gold_glob)))
    if not gold_paths:
        print(f"ERROR: no gold files matched --breadcrumb-gold-glob={args.breadcrumb_gold_glob!r}")
        return 1

    issues: list[str] = []
    issues.extend(
        audit_registry_authority(
            corpus_root=Path(args.corpus_root),
            schema_path=Path(args.npc_registry_schema),
        )
    )
    issues.extend(audit_manifest_campaign_ids(manifest_paths=[Path(p) for p in manifest_paths]))
    issues.extend(audit_location_hierarchy_contracts(gold_paths=gold_paths))

    if issues:
        print("World/Campaign alignment audit: FAIL")
        for issue in issues:
            print(f"- {issue}")
        print(f"\nTotal issues: {len(issues)}")
        return 1

    print("World/Campaign alignment audit: PASS")
    print(
        f"Checked {len(manifest_paths)} manifest(s) and {len(gold_paths)} breadcrumb natural gold file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
