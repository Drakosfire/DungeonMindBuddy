"""Server-compatible definition digest / canonicalization proofs."""
from __future__ import annotations

import copy
import json
import unicodedata
from pathlib import Path

from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import (
    canonicalize_definition_dict,
    source_definition_digest_from_body,
)

FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "statblocks"
    / "v1"
    / "server_revise_transcripts"
    / "revise-request.json"
)


def _source_definition() -> dict:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return copy.deepcopy(payload["source_definition"])


def test_omitted_server_default_lists_digest_as_empty_arrays() -> None:
    with_lists = _source_definition()
    with_lists["identity"]["subtypes"] = []
    with_lists["communication"]["languages"] = []
    with_lists["communication"]["special_modes"] = []
    with_lists["resources"] = []
    with_lists["phases"] = []

    omitted = _source_definition()
    omitted["identity"].pop("subtypes", None)
    omitted["communication"].pop("languages", None)
    omitted["communication"].pop("special_modes", None)
    omitted.pop("resources", None)
    omitted.pop("phases", None)

    assert source_definition_digest_from_body(omitted) == source_definition_digest_from_body(
        with_lists
    )
    canonical = canonicalize_definition_dict(omitted)
    assert '"subtypes":[]' in canonical
    assert '"languages":[]' in canonical
    assert '"subtypes":null' not in canonical


def test_null_server_default_lists_digest_as_empty_arrays() -> None:
    with_null = _source_definition()
    with_null["identity"]["subtypes"] = None
    with_lists = _source_definition()
    with_lists["identity"]["subtypes"] = []
    assert source_definition_digest_from_body(with_null) == source_definition_digest_from_body(
        with_lists
    )


def test_set_like_field_order_and_dedupe_normalize() -> None:
    first = _source_definition()
    first["identity"]["subtypes"] = ["orc", "brute", "orc"]
    first["communication"]["languages"] = ["Orc", "Common"]
    first["rule_elements"][0]["tags"] = ["brute", "attack", "brute"]

    second = _source_definition()
    second["identity"]["subtypes"] = ["brute", "orc"]
    second["communication"]["languages"] = ["Common", "Orc"]
    second["rule_elements"][0]["tags"] = ["attack", "brute"]

    assert source_definition_digest_from_body(first) == source_definition_digest_from_body(
        second
    )
    canonical = canonicalize_definition_dict(first)
    assert '"subtypes":["brute","orc"]' in canonical
    assert '"tags":["attack","brute"]' in canonical


def test_nfc_and_decomposed_unicode_normalize_identically() -> None:
    composed = _source_definition()
    composed["identity"]["name"] = unicodedata.normalize("NFC", "Cafe\u0301 Brute")
    decomposed = _source_definition()
    decomposed["identity"]["name"] = unicodedata.normalize("NFD", "Café Brute")
    assert source_definition_digest_from_body(composed) == source_definition_digest_from_body(
        decomposed
    )


def test_stale_openapi_explains_null_does_not_enter_canonical() -> None:
    """DMS omitted RuleElement.explains; Buddy OpenAPI may still dump null."""
    clean = _source_definition()
    for element in clean.get("rule_elements") or []:
        if isinstance(element, dict):
            element.pop("explains", None)

    with_null_explains = copy.deepcopy(clean)
    for element in with_null_explains.get("rule_elements") or []:
        if isinstance(element, dict):
            element["explains"] = None

    clean_canonical = canonicalize_definition_dict(clean)
    assert '"explains"' not in clean_canonical
    assert clean_canonical == canonicalize_definition_dict(with_null_explains)
    assert source_definition_digest_from_body(clean) == source_definition_digest_from_body(
        with_null_explains
    )

    # Legacy fixtures sealed with explicit explains:[] must keep that shape.
    with_empty_explains = copy.deepcopy(clean)
    for element in with_empty_explains.get("rule_elements") or []:
        if isinstance(element, dict):
            element["explains"] = []
    empty_canonical = canonicalize_definition_dict(with_empty_explains)
    assert '"explains":[]' in empty_canonical
    assert empty_canonical != clean_canonical
