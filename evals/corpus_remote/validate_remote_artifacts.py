from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required_document_fields() -> set[str]:
    return {
        "document_id",
        "remote_path",
        "source_class",
        "canon_layer",
        "campaign_id",
        "campaign_group",
    }


def validate_artifacts(
    inventory_path: Path, manifest_path: Path, reproducibility_path: Path
) -> list[str]:
    errors: list[str] = []
    inventory = _load_json(inventory_path)
    manifest = _load_json(manifest_path)
    reproducibility = _load_json(reproducibility_path)

    inv_snapshot = inventory.get("snapshot_id")
    man_snapshot = manifest.get("snapshot_id")
    rep_snapshot = reproducibility.get("snapshot_id")
    if not (inv_snapshot and inv_snapshot == man_snapshot == rep_snapshot):
        errors.append("snapshot_id mismatch across inventory/manifest/reproducibility")

    inventory_paths = {doc["path"] for doc in inventory.get("documents", [])}
    required = _required_document_fields()
    for idx, document in enumerate(manifest.get("documents", [])):
        missing = sorted(required.difference(document.keys()))
        if missing:
            errors.append(
                f"manifest document index={idx} missing required fields: {missing}"
            )
            continue
        if document["remote_path"] not in inventory_paths:
            errors.append(
                f"manifest remote_path not present in inventory: {document['remote_path']}"
            )
        if document["canon_layer"] == "campaign" and not document["campaign_id"]:
            errors.append(
                "manifest document has canon_layer=campaign but null/empty campaign_id: "
                f"{document['remote_path']}"
            )
        if document["canon_layer"] == "world" and document["campaign_id"] is not None:
            errors.append(
                "manifest document has canon_layer=world with non-null campaign_id: "
                f"{document['remote_path']}"
            )

    inventory_hash = _canonical_hash(inventory.get("documents", []))
    if reproducibility.get("inventory_hash") != inventory_hash:
        errors.append("reproducibility inventory_hash mismatch")

    manifest_hash = _canonical_hash(manifest.get("documents", []))
    if reproducibility.get("manifest_hash") != manifest_hash:
        errors.append("reproducibility manifest_hash mismatch")

    if reproducibility.get("document_counts_match") is not True:
        errors.append("reproducibility document_counts_match is not true")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate remote corpus artifacts")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reproducibility", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_artifacts(
        inventory_path=Path(args.inventory),
        manifest_path=Path(args.manifest),
        reproducibility_path=Path(args.reproducibility),
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Remote artifacts validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

