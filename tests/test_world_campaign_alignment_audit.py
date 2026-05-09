from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import audit_world_campaign_alignment as audit  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_manifest_audit_rejects_non_normalized_campaign_id(tmp_path: Path) -> None:
    manifest = tmp_path / "normalization_manifest.json"
    _write_json(
        manifest,
        {
            "documents": [
                {
                    "remote_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20.md",
                    "canon_layer": "campaign",
                    "campaign_id": "campaign_2",
                }
            ]
        },
    )
    issues = audit.audit_manifest_campaign_ids(manifest_paths=[manifest])
    assert issues
    assert "expected longmont-cN" in issues[0]


def test_manifest_audit_accepts_normalized_campaign_id(tmp_path: Path) -> None:
    manifest = tmp_path / "normalization_manifest.json"
    _write_json(
        manifest,
        {
            "documents": [
                {
                    "remote_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20.md",
                    "canon_layer": "campaign",
                    "campaign_id": "longmont-c2",
                }
            ]
        },
    )
    issues = audit.audit_manifest_campaign_ids(manifest_paths=[manifest])
    assert issues == []


def test_hierarchy_audit_requires_equivalences_for_location_context_parent_labels(
    tmp_path: Path,
) -> None:
    gold = tmp_path / "breadcrumb_query_natural_test.json"
    _write_json(
        gold,
        {
            "schema": "dmb_breadcrumb_query_natural_gold_v1",
            "scenarios": [
                {
                    "id": "stormspire_parent_only",
                    "benchmark_lane": "location_context",
                    "expect_route_substrings": ["Stormspire Academy"],
                }
            ],
        },
    )
    issues = audit.audit_location_hierarchy_contracts(gold_paths=[gold])
    assert issues
    assert "requires non-empty location_hierarchy_equivalences" in issues[0]


def test_hierarchy_audit_accepts_explicit_equivalences(tmp_path: Path) -> None:
    gold = tmp_path / "breadcrumb_query_natural_test.json"
    _write_json(
        gold,
        {
            "schema": "dmb_breadcrumb_query_natural_gold_v1",
            "scenarios": [
                {
                    "id": "stormspire_parent_with_map",
                    "benchmark_lane": "location_context",
                    "expect_route_substrings": ["Stormspire Academy"],
                    "location_hierarchy_equivalences": {
                        "Stormspire Academy": ["Mossglade"]
                    },
                }
            ],
        },
    )
    issues = audit.audit_location_hierarchy_contracts(gold_paths=[gold])
    assert issues == []

