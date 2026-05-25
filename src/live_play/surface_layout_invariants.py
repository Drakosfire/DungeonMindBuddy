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
