from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import (
    canonicalize_definition_dict,
    source_definition_digest_from_body,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "statblocks" / "v1"


def _definition() -> dict[str, Any]:
    payload = json.loads((FIXTURE_DIR / "create-request.json").read_text())
    return payload["definition"]


def _canonical_payload(definition: dict[str, Any]) -> dict[str, Any]:
    return json.loads(canonicalize_definition_dict(definition))


def test_explains_digest_preserves_absent_vs_explicit_empty() -> None:
    absent = _definition()
    absent["rule_elements"][0].pop("explains", None)
    explicit_empty = copy.deepcopy(absent)
    explicit_empty["rule_elements"][0]["explains"] = []

    absent_canonical = _canonical_payload(absent)
    empty_canonical = _canonical_payload(explicit_empty)

    assert "explains" not in absent_canonical["rule_elements"][0]
    assert empty_canonical["rule_elements"][0]["explains"] == []
    assert source_definition_digest_from_body(absent) != source_definition_digest_from_body(
        explicit_empty
    )
    assert source_definition_digest_from_body(explicit_empty) == source_definition_digest_from_body(
        copy.deepcopy(explicit_empty)
    )


def test_explicit_null_explains_is_treated_as_absent_when_dto_accepts_it() -> None:
    absent = _definition()
    absent["rule_elements"][0].pop("explains", None)
    explicit_null = copy.deepcopy(absent)
    explicit_null["rule_elements"][0]["explains"] = None

    assert source_definition_digest_from_body(explicit_null) == source_definition_digest_from_body(
        absent
    )
    assert "explains" not in _canonical_payload(explicit_null)["rule_elements"][0]


def test_populated_explains_is_retained_in_canonical_definition() -> None:
    definition = _definition()
    definition["rule_elements"][0]["explains"] = [
        {"element_key": "greatclub", "note": "Context for the strike."}
    ]

    canonical = _canonical_payload(definition)

    assert canonical["rule_elements"][0]["explains"] == [
        {"element_key": "greatclub", "note": "Context for the strike."}
    ]


def test_other_server_default_empty_lists_keep_current_canonical_semantics() -> None:
    definition = _definition()
    definition["communication"].pop("languages", None)

    canonical = _canonical_payload(definition)

    assert canonical["communication"]["languages"] == []
