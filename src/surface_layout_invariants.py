from __future__ import annotations

from typing import Any

REQUIRED_SURFACE_MODULES = ("chat", "record")


def validate_surface_layout_invariants(layout: dict[str, Any]) -> None:
    """App-level invariants JSON Schema cannot express (unique module_id, required enabled modules)."""
    modules = layout.get("modules")
    if not isinstance(modules, list):
        raise ValueError("modules must be a list")

    seen: set[str] = set()
    for row in modules:
        if not isinstance(row, dict):
            raise ValueError("each module row must be an object")
        module_id = row.get("module_id")
        if not isinstance(module_id, str):
            raise ValueError("module_id must be a string")
        if module_id in seen:
            raise ValueError(f"duplicate module_id: {module_id}")
        seen.add(module_id)

    for required_id in REQUIRED_SURFACE_MODULES:
        match = next((row for row in modules if row.get("module_id") == required_id), None)
        if match is None:
            raise ValueError(f"missing required module: {required_id}")
        if not match.get("enabled"):
            raise ValueError(f"required module {required_id} must be enabled")


def validate_catalog_layout_consistency(
    packet: dict[str, Any],
    layout: dict[str, Any],
) -> None:
    """Packet catalog and runtime layout must agree on module identity."""
    catalog_rows = packet.get("surface_catalog")
    if not isinstance(catalog_rows, list):
        raise ValueError("surface_catalog must be a list")

    catalog_ids = [row["module_id"] for row in catalog_rows]
    if len(catalog_ids) != len(set(catalog_ids)):
        raise ValueError("duplicate module_id in surface_catalog")

    catalog = {row["module_id"]: row for row in catalog_rows}
    for required_id in REQUIRED_SURFACE_MODULES:
        if not catalog.get(required_id, {}).get("required"):
            raise ValueError(f"surface_catalog must mark {required_id} as required")

    layout_ids = [row["module_id"] for row in layout.get("modules", [])]
    unknown = set(layout_ids) - set(catalog_ids)
    if unknown:
        raise ValueError(f"layout references modules not in surface_catalog: {sorted(unknown)}")
