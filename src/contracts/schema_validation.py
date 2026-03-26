from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "v0.1"


def _schema_store() -> dict[str, dict[str, Any]]:
    store: dict[str, dict[str, Any]] = {}
    for schema_path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        store[schema_path.name] = schema
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            store[schema_id] = schema
    return store


def _schema_registry() -> Registry:
    registry = Registry()
    for uri, schema in _schema_store().items():
        registry = registry.with_resource(uri=uri, resource=Resource.from_contents(schema))
    return registry


def load_schema(schema_filename: str) -> dict[str, Any]:
    schema_path = SCHEMA_DIR / schema_filename
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_instance(instance: dict[str, Any], schema_filename: str) -> None:
    schema = load_schema(schema_filename)
    validator = Draft202012Validator(schema=schema, registry=_schema_registry())
    validator.validate(instance)


def validate_many(instances: list[dict[str, Any]], schema_filename: str) -> None:
    for instance in instances:
        validate_instance(instance, schema_filename)

