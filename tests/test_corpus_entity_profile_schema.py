from __future__ import annotations

import json
from pathlib import Path

from src.contracts.schema_validation import validate_instance

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas" / "v0.1"
_EXAMPLE = _SCHEMA_DIR / "examples" / "corpus_entity_profile.example.json"
_BONOGO = _SCHEMA_DIR / "examples" / "corpus_entity_profile.bonogo_exemplar.json"
_ENTITY_PROFILE_DIR = (
    Path(__file__).resolve().parent.parent / "Docs" / "Plans" / "entity_profiles"
)


def test_corpus_entity_profile_example_validates() -> None:
    payload = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    validate_instance(payload, "corpus_entity_profile.schema.json")


def test_corpus_entity_profile_bonogo_exemplar_validates() -> None:
    payload = json.loads(_BONOGO.read_text(encoding="utf-8"))
    validate_instance(payload, "corpus_entity_profile.schema.json")


def test_entity_audit_profiles_in_docs_plans_validate() -> None:
    paths = sorted(_ENTITY_PROFILE_DIR.glob("corpus_entity_profile.*.json"))
    assert paths, f"expected profiles under {_ENTITY_PROFILE_DIR}"
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(payload, "corpus_entity_profile.schema.json")
