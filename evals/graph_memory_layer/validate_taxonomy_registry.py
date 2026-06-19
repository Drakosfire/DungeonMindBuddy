"""Validate the Graph Memory taxonomy registry.

This validator is intentionally standard-library only and does not import
production retrieval, graph schema, or LLM extraction code.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).with_name("taxonomy_registry.json")
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
REQUIRED_TOP_LEVEL = {
    "version",
    "status",
    "workstream",
    "purpose",
    "promotion_semantics",
    "vocabularies",
}
REQUIRED_VOCAB_FIELDS = {"id", "label", "description", "terms"}
REQUIRED_TERM_FIELDS = {
    "id",
    "label",
    "description",
    "allowed_usage",
    "disallowed_usage",
    "examples",
    "allowed_graph_record_states",
    "admissibility_notes",
}
TERM_LIST_FIELDS = {
    "allowed_usage",
    "disallowed_usage",
    "examples",
    "allowed_graph_record_states",
}
ALLOWED_GRAPH_RECORD_STATES = {
    "baseline",
    "candidate",
    "validated",
    "promoted",
    "rejected",
    "deprecated",
    "archived",
}
REQUIRED_VOCABULARIES = {
    "source_kind",
    "source_layer",
    "entity_kind",
    "route_kind",
    "evidence_role",
    "authority_state",
    "visibility_state",
    "truth_state",
    "lifecycle_state",
    "relationship_predicate_family",
    "planning_lane",
    "retrieval_lane",
    "graph_candidate_state",
    "promotion_state",
    "validation_severity",
}


def _is_nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_registry(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_top = REQUIRED_TOP_LEVEL - data.keys()
    if missing_top:
        errors.append(f"missing top-level fields: {', '.join(sorted(missing_top))}")

    vocabularies = data.get("vocabularies")
    if not isinstance(vocabularies, dict) or not vocabularies:
        errors.append("vocabularies must be a non-empty object")
        return errors

    missing_vocabularies = REQUIRED_VOCABULARIES - set(vocabularies)
    if missing_vocabularies:
        errors.append(
            "missing required vocabularies: " + ", ".join(sorted(missing_vocabularies))
        )

    seen_vocab_ids: set[str] = set()
    for key, vocabulary in vocabularies.items():
        if not isinstance(vocabulary, dict):
            errors.append(f"vocabulary {key!r} must be an object")
            continue
        missing_vocab_fields = REQUIRED_VOCAB_FIELDS - vocabulary.keys()
        if missing_vocab_fields:
            errors.append(
                f"vocabulary {key!r} missing fields: "
                + ", ".join(sorted(missing_vocab_fields))
            )
        vocab_id = vocabulary.get("id")
        if not _is_nonblank(vocab_id):
            errors.append(f"vocabulary {key!r} has blank id")
        elif not SNAKE_CASE_RE.match(vocab_id):
            errors.append(f"vocabulary id {vocab_id!r} is not lowercase snake_case")
        elif vocab_id in seen_vocab_ids:
            errors.append(f"duplicate vocabulary id: {vocab_id}")
        else:
            seen_vocab_ids.add(vocab_id)
        if vocab_id != key:
            errors.append(f"vocabulary key {key!r} does not match id {vocab_id!r}")
        for field in ("label", "description"):
            if not _is_nonblank(vocabulary.get(field)):
                errors.append(f"vocabulary {key!r} has blank {field}")

        terms = vocabulary.get("terms")
        if not isinstance(terms, list) or not terms:
            errors.append(f"vocabulary {key!r} terms must be a non-empty list")
            continue
        seen_term_ids: set[str] = set()
        for index, term in enumerate(terms):
            if not isinstance(term, dict):
                errors.append(f"vocabulary {key!r} term {index} must be an object")
                continue
            missing_term_fields = REQUIRED_TERM_FIELDS - term.keys()
            if missing_term_fields:
                errors.append(
                    f"vocabulary {key!r} term {index} missing fields: "
                    + ", ".join(sorted(missing_term_fields))
                )
            term_id = term.get("id")
            if not _is_nonblank(term_id):
                errors.append(f"vocabulary {key!r} term {index} has blank id")
            elif not SNAKE_CASE_RE.match(term_id):
                errors.append(f"term id {term_id!r} in {key!r} is not lowercase snake_case")
            elif term_id in seen_term_ids:
                errors.append(f"duplicate term id in {key!r}: {term_id}")
            else:
                seen_term_ids.add(term_id)
            for field in ("label", "description", "admissibility_notes"):
                if not _is_nonblank(term.get(field)):
                    errors.append(f"term {term_id!r} in {key!r} has blank {field}")
            states = term.get("allowed_graph_record_states")
            if isinstance(states, list):
                invalid_states = [state for state in states if state not in ALLOWED_GRAPH_RECORD_STATES]
                if invalid_states:
                    errors.append(
                        f"term {term_id!r} in {key!r} has invalid allowed_graph_record_states: "
                        + ", ".join(map(str, invalid_states))
                    )
            for field in TERM_LIST_FIELDS:
                if not isinstance(term.get(field), list):
                    errors.append(f"term {term_id!r} in {key!r} field {field} must be a list")
    return errors


def main() -> int:
    print("Graph Memory taxonomy registry validation")
    if not REGISTRY_PATH.is_file():
        print("- manifest: missing")
        return 1
    print("- manifest: found")
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    vocabularies = data.get("vocabularies", {})
    vocab_count = len(vocabularies) if isinstance(vocabularies, dict) else 0
    errors = validate_registry(data)
    duplicate_vocab_errors = [e for e in errors if e.startswith("duplicate vocabulary id")]
    duplicate_term_errors = [e for e in errors if e.startswith("duplicate term id")]
    required_vocab_errors = [e for e in errors if e.startswith("missing required vocabularies")]
    field_errors = [e for e in errors if e not in duplicate_vocab_errors + duplicate_term_errors + required_vocab_errors]
    print(f"- vocabularies: {vocab_count}")
    print("- duplicate vocabulary ids: " + ("none" if not duplicate_vocab_errors else "blocked"))
    print("- duplicate term ids: " + ("none" if not duplicate_term_errors else "blocked"))
    print("- required vocabularies: " + ("ok" if not required_vocab_errors else "blocked"))
    print("- required fields: " + ("ok" if not field_errors else "blocked"))
    if errors:
        print("- taxonomy registry: blocked")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("- taxonomy registry: ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
