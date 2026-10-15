"""Host-owned exact source handles for the GE recap actor wire contract.

Handles identify text, not entailed claims. Canonical consumers still receive
paragraph IDs and literal quotes; models never generate those strings here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True)
class SentenceUnit:
    unit_id: str
    span_id: str
    start: int
    end: int


@dataclass(frozen=True)
class SourceSentencePacket:
    source: str
    source_sha256: str
    packet_id: str
    units: tuple[SentenceUnit, ...]


_ABBREVIATIONS = {
    "dr",
    "mr",
    "mrs",
    "ms",
    "prof",
    "st",
    "sr",
    "jr",
    "etc",
    "e.g",
    "i.e",
}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _packet_id(source_sha: str, units: tuple[SentenceUnit, ...]) -> str:
    descriptors = [(u.unit_id, u.span_id, u.start, u.end) for u in units]
    return _digest(json.dumps([source_sha, descriptors], separators=(",", ":")))


def _boundaries(text: str):
    start = 0
    for match in re.finditer(
        r"""[.!?]+["'\)\]]*(?=\s|$)|\n(?=\s*(?:[-*+] |\d+[.)] ))""", text
    ):
        token = text[start : match.end()].rstrip("\"')]")
        last = token.rsplit(None, 1)[-1].rstrip(".") if token.split() else ""
        if match.group().startswith(".") and (
            last.lower() in _ABBREVIATIONS or (len(last) == 1 and last.isalpha())
        ):
            continue
        end = match.end()
        left, right = start, end
        while left < right and text[left].isspace():
            left += 1
        while right > left and text[right - 1].isspace():
            right -= 1
        if right > left:
            yield left, right
        start = end
    left, right = start, len(text)
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    if right > left:
        yield left, right


def compile_source_sentence_packet(
    source: str,
    rows: Sequence[Mapping[str, Any]],
) -> SourceSentencePacket:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    units: list[SentenceUnit] = []
    seen: dict[str, tuple[int, str]] = {}
    for row in rows:
        span, text, line = row["source_span_ref_id"], row["text"], row["line_start"]
        if not isinstance(span, str) or not span or not isinstance(text, str):
            raise ValueError("invalid_source_row")
        if type(line) is not int or not 1 <= line < len(offsets):
            raise ValueError("source_row_offsets_mismatch")
        start = offsets[line - 1]
        if source[start : start + len(text)] != text:
            raise ValueError("source_row_offsets_mismatch")
        if span in seen:
            if seen[span] != (start, text):
                raise ValueError("conflicting_span_identity")
            continue
        seen[span] = (start, text)
        for left, right in _boundaries(text):
            units.append(
                SentenceUnit(
                    f"Q{len(units) + 1:03d}", span, start + left, start + right
                )
            )
    frozen = tuple(units)
    sha = _digest(source)
    return SourceSentencePacket(source, sha, _packet_id(sha, frozen), frozen)


def validate_packet(packet: SourceSentencePacket, *, expected_packet_id: str) -> None:
    if (
        _digest(packet.source) != packet.source_sha256
        or _packet_id(packet.source_sha256, packet.units) != packet.packet_id
        or expected_packet_id != packet.packet_id
    ):
        raise ValueError("source_revision_mismatch")
    ids = set()
    for unit in packet.units:
        if unit.unit_id in ids or not unit.span_id:
            raise ValueError("duplicate_or_invalid_unit_identity")
        ids.add(unit.unit_id)
        if not (0 <= unit.start < unit.end <= len(packet.source)):
            raise ValueError("source_unit_offsets_mismatch")


def render_source_sentence_packet(packet: SourceSentencePacket) -> str:
    validate_packet(packet, expected_packet_id=packet.packet_id)
    return "\n\n".join(
        f"### {unit.unit_id}\n{packet.source[unit.start : unit.end]}"
        for unit in packet.units
    )


SENTENCE_EVIDENCE_RULE = (
    "Each evidence_refs item must contain only source_quote_ids: a nonempty array "
    "of Q handles from the Source Packet. Select all sentences needed for the "
    "claim, including conditions, negation and pronoun antecedents. Do not emit "
    "paragraph IDs or rewrite quotations. Handles prove text location, not truth. "
    "Do not merge similar names or infer a different entity type without support."
)


def actor_wire_schema(base_schema: dict, packet: SourceSentencePacket) -> dict:
    validate_packet(packet, expected_packet_id=packet.packet_id)
    schema = deepcopy(base_schema)
    ref = schema["properties"]["observation_nodes"]["items"]["properties"][
        "evidence_refs"
    ]["items"]
    ref.clear()
    ref.update(
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source_quote_ids": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "enum": [u.unit_id for u in packet.units],
                    },
                }
            },
            "required": ["source_quote_ids"],
        }
    )
    return schema


def materialize_actor_evidence(
    packet: SourceSentencePacket,
    parsed: dict,
    *,
    expected_packet_id: str,
) -> dict:
    validate_packet(packet, expected_packet_id=expected_packet_id)
    lookup = {u.unit_id: u for u in packet.units}
    result = deepcopy(parsed)
    for node in result["observation_nodes"]:
        refs, seen = [], set()
        for ref in node["evidence_refs"]:
            if set(ref) != {"source_quote_ids"} or not ref["source_quote_ids"]:
                raise ValueError("invalid_reference_shape")
            for unit_id in ref["source_quote_ids"]:
                if unit_id not in lookup or unit_id in seen:
                    raise ValueError("unknown_or_duplicate_unit")
                seen.add(unit_id)
                unit = lookup[unit_id]
                refs.append(
                    {
                        "source_span_ref_id": unit.span_id,
                        "anchor_quotes": [packet.source[unit.start : unit.end]],
                    }
                )
        if not refs:
            raise ValueError("empty_evidence")
        node["evidence_refs"] = refs
    return result
