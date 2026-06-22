from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "surface_vocabulary_boundary.json"

REQUIRED_SHARED_TERMS = {"source_artifact", "source_anchor", "source_unit", "provenance", "evidence_role", "lifecycle_state", "canon_state"}
REQUIRED_ONTOLOGY_TERMS = {"entity_kind", "source_kind", "evidence_role", "authority_state", "visibility_state", "lifecycle_state"}
REQUIRED_SURFACE_TERMS = {"npc_chip", "location_chip", "statblock_projection", "roll_table_projection", "reference_chip", "projection_card"}
REQUIRED_CONTESTED_TERMS = {"statblock", "summary", "route"}
REQUIRED_FORBIDDEN_COLLAPSES = {"summary_as_source_evidence", "lifecycle_as_known_fact", "ui_ref_type_as_taxonomy_owner", "surface_projection_as_corpus_truth"}
REQUIRED_PAYLOAD_FIELDS = {"adapter_key", "ref_id", "label", "source_anchor", "evidence_role", "authority_state", "visibility_state", "lifecycle_state", "canon_state", "provenance"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_manifest() -> dict[str, Any]:
    _require(MANIFEST_PATH.is_file(), "manifest missing")
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _require(isinstance(data, dict), "manifest must be a JSON object")
    return data


def _ids(items: Any) -> set[str]:
    _require(isinstance(items, list), "expected a list")
    ids: set[str] = set()
    for item in items:
        if isinstance(item, str):
            ids.add(item)
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.add(item["id"])
        else:
            raise AssertionError("list entries must be strings or objects with string id")
    return ids


def _require_contains(observed: set[str], required: set[str], label: str) -> None:
    missing = sorted(required - observed)
    _require(not missing, f"{label} missing required entries: {', '.join(missing)}")


def main() -> int:
    print("Graph Memory surface vocabulary boundary validation")
    manifest = _load_manifest()
    print("- manifest: found")

    _require(manifest.get("version") == "0.1", "version must be 0.1")
    print("- version: 0.1")
    _require(manifest.get("status") == "surface_vocabulary_boundary_v0", "status must be surface_vocabulary_boundary_v0")
    _require(manifest.get("decision") == "share_semantic_envelope_preserve_surface_vocabulary", "decision must be share_semantic_envelope_preserve_surface_vocabulary")
    print("- decision: share semantic envelope, preserve surface vocabulary")

    shared = _ids(manifest.get("shared_semantic_envelope"))
    _require(shared, "shared semantic envelope must be non-empty")
    _require_contains(shared, REQUIRED_SHARED_TERMS, "shared semantic envelope")
    print("- shared semantic envelope: ready")

    ontology = _ids(manifest.get("ontology_owned_terms"))
    _require_contains(ontology, REQUIRED_ONTOLOGY_TERMS, "ontology-owned vocabulary")
    print("- ontology-owned vocabulary: ready")

    surface = _ids(manifest.get("surface_owned_terms"))
    _require_contains(surface, REQUIRED_SURFACE_TERMS, "surface-owned vocabulary")
    print("- surface-owned vocabulary: ready")

    contested = _ids(manifest.get("contested_terms"))
    _require_contains(contested, REQUIRED_CONTESTED_TERMS, "contested terms")
    print("- contested terms: ready")

    forbidden = _ids(manifest.get("forbidden_collapses"))
    _require_contains(forbidden, REQUIRED_FORBIDDEN_COLLAPSES, "forbidden collapses")
    print("- forbidden collapses: ready")

    payload_fields = _ids(manifest.get("future_payload_required_fields"))
    _require_contains(payload_fields, REQUIRED_PAYLOAD_FIELDS, "future payload requirements")
    print("- future payload requirements: ready")

    print("- surface vocabulary boundary: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"- surface vocabulary boundary: blocked ({exc})")
        sys.exit(1)
