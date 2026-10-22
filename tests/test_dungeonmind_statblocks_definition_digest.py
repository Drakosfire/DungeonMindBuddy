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
# Produced by DMS compute_definition_digest and canonicalize_definition at
# f95e92cb0fb50949260534b12c063ab1811eaf30 from create-request.json.
SERVER_CURRENT_DIGEST = (
    "sha256:170d6a58c947d61bda8078d2c64705ca5edae5e68a8d61a6b3c2aad395a61246"
)


def _definition() -> dict[str, Any]:
    payload = json.loads((FIXTURE_DIR / "create-request.json").read_text())
    return payload["definition"]


def _canonical_payload(definition: dict[str, Any]) -> dict[str, Any]:
    return json.loads(canonicalize_definition_dict(definition))


def test_current_server_digest_distinguishes_null_from_explicit_empty() -> None:
    """Server domain default is null; an explicit empty list is a distinct value."""
    absent = _definition()
    absent["rule_elements"][0].pop("explains", None)
    explicit_empty = copy.deepcopy(absent)
    explicit_empty["rule_elements"][0]["explains"] = []

    absent_canonical = _canonical_payload(absent)
    empty_canonical = _canonical_payload(explicit_empty)

    assert absent_canonical["rule_elements"][0]["explains"] is None
    assert empty_canonical["rule_elements"][0]["explains"] == []
    assert source_definition_digest_from_body(absent) != source_definition_digest_from_body(
        explicit_empty
    )
    assert source_definition_digest_from_body(absent) == SERVER_CURRENT_DIGEST
    assert source_definition_digest_from_body(explicit_empty) != SERVER_CURRENT_DIGEST
    assert source_definition_digest_from_body(explicit_empty) == source_definition_digest_from_body(
        copy.deepcopy(explicit_empty)
    )


def test_null_explains_matches_current_server_default() -> None:
    absent = _definition()
    absent["rule_elements"][0].pop("explains", None)
    explicit_null = copy.deepcopy(absent)
    explicit_null["rule_elements"][0]["explains"] = None

    assert source_definition_digest_from_body(explicit_null) == source_definition_digest_from_body(
        absent
    )
    assert source_definition_digest_from_body(explicit_null) == SERVER_CURRENT_DIGEST
    assert _canonical_payload(explicit_null)["rule_elements"][0]["explains"] is None


def test_populated_explains_is_retained_in_canonical_definition() -> None:
    """Canonicalization preserves every explicit field; generation projects separately."""
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


def test_canonical_bytes_match_exact_current_dms_golden() -> None:
    expected = (FIXTURE_DIR / "definition-dms-v1.canonical.json").read_text().rstrip("\n")
    assert canonicalize_definition_dict(_definition()) == expected
    assert source_definition_digest_from_body(_definition()) == SERVER_CURRENT_DIGEST
