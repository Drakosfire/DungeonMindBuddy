"""Lossless, closed WK transport and the narrow dossier standing intent."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
import hashlib
import json
import math
import types
from typing import get_args, get_origin, get_type_hints, Union

from worldkeeper.application import contracts as wk
from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime

CODEC = "dmb_wk_prepared_standing_v1"
# Explicit types, never request-directed imports. Intent builders define allowed semantics.
_TYPES = {
    c.__name__: c
    for c in (
        wk.PreparedWorldChange,
        wk.AuthorityRef,
        wk.PreparedEvidenceWitness,
        wk.ProspectiveHandle,
        wk.CreateObject,
        wk.CreateRelationship,
        wk.DurableObjectRef,
        wk.ResultOf,
        wk.UseExisting,
        wk.CreateFact,
        wk.LiteralFactValue,
        wk.TermRefFactValue,
        wk.AssertionMetadata,
        wk.ScopeBinding,
        wk.Visibility,
        wk.TemporalScope,
        wk.DomainMetadata,
        wk.FrozenJsonArray,
        wk.FrozenJsonObject,
    )
}


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _encode(value):
    if is_dataclass(value) and type(value).__name__ in _TYPES:
        if type(value) is not _TYPES[type(value).__name__]:
            raise ValueError("unknown prepared type")
        return {
            "type": type(value).__name__,
            "fields": {f.name: _encode(getattr(value, f.name)) for f in fields(value)},
        }
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("naive prepared datetime")
        return {"type": "datetime", "value": value.isoformat()}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [_encode(v) for v in value]}
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("unsupported prepared value")


def _matches(value, annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (types.UnionType, Union):
        return any(_matches(value, arg) for arg in args)
    if origin is tuple:
        if type(value) is not tuple:
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_matches(v, args[0]) for v in value)
        return len(value) == len(args) and all(
            _matches(v, t) for v, t in zip(value, args)
        )
    if annotation in (str, int, float, bool, type(None)):
        return type(value) is annotation
    return type(value) is annotation


def _decode(value):
    if type(value) is dict:
        tag = value.get("type")
        if tag == "datetime" and set(value) == {"type", "value"}:
            result = datetime.fromisoformat(value["value"])
            if result.utcoffset() is None:
                raise ValueError("naive prepared datetime")
            return result
        if (
            tag == "tuple"
            and set(value) == {"type", "items"}
            and type(value["items"]) is list
        ):
            return tuple(_decode(v) for v in value["items"])
        if tag in _TYPES and set(value) == {"type", "fields"}:
            cls = _TYPES[tag]
            if type(value["fields"]) is not dict or set(value["fields"]) != {
                f.name for f in fields(cls)
            }:
                raise ValueError("incomplete prepared fields")
            decoded = {k: _decode(v) for k, v in value["fields"].items()}
            hints = get_type_hints(cls)
            if not all(_matches(v, hints[k]) for k, v in decoded.items()):
                raise ValueError("wrong typed prepared field")
            return cls(**decoded)
        raise ValueError("unknown prepared tag or fields")
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("unsupported encoded value")


def encode_prepared(value):
    if type(value) is not wk.PreparedWorldChange:
        raise ValueError("prepared type required")
    return {"schema": CODEC, "value": _encode(value)}


def decode_prepared(packet):
    if set(packet) != {"schema", "value"} or packet["schema"] != CODEC:
        raise ValueError("unknown prepared codec")
    result = _decode(packet["value"])
    if type(result) is not wk.PreparedWorldChange or canonical(
        encode_prepared(result)
    ) != canonical(packet):
        raise ValueError("lossy prepared encoding")
    return result


def runtime(repository, domain, profile, *, now, operation_id):
    return DungeonMindWorldKeeperRuntime(
        repository=repository,
        domain_contract=domain,
        semantic_profile=profile,
        clock=lambda: now,
        prepared_id_factory=lambda: operation_id,
    )


def standing_intent(space_id, rows, choices):
    by_slug = {c.slug: c for c in choices}
    if len(by_slug) != 6 or set(by_slug) != {r["slug"] for r in rows}:
        raise ValueError("choices must match all six subjects exactly")
    existing = [c.entity_id for c in choices if c.action == "use_existing"]
    if len(existing) != len(set(existing)):
        raise ValueError("different subjects cannot share a reviewed target")
    operations = []
    for row in rows:
        slug = row["slug"]
        metadata = wk.AssertionMetadata(
            scope=(wk.ScopeBinding("dungeonbuddy.scope:campaign", "longmont-c1"),),
            visibility=wk.Visibility("labels_any", ("dungeonbuddy.visibility:gm",)),
            epistemic_basis="asserted",
            claim_mode="dungeonbuddy.claim:fact",
            standing="established",
            evidence_ref_ids=(row["evidence_ref_id"],),
            temporal_scope=wk.TemporalScope(kind="unknown"),
        )
        facts = (
            wk.CreateFact(
                slug + ":name", "dnd5e:name", wk.LiteralFactValue(row["name"]), metadata
            ),
            wk.CreateFact(
                slug + ":pc",
                "dnd5e:classification",
                wk.TermRefFactValue("dnd5e:pc"),
                metadata,
            ),
        )
        choice = by_slug[slug]
        operations.append(
            wk.CreateObject(slug, facts)
            if choice.action == "create"
            else wk.UseExisting(choice.entity_id, facts)
        )
    return wk.WorldChangeIntent(
        space_id, "dungeonbuddy:dossier-pc-standing-v1", tuple(operations)
    )


def verify_prepared_parent(prepared, context):
    def ref(value):
        return {
            "authority_id": value.authority_id,
            "revision": value.revision,
            "descriptor_sha256": value.descriptor_sha256,
        }

    if (
        prepared.space_id != context["space_id"]
        or prepared.expected_parent_revision_id != context["revision_id"]
        or prepared.parent_graph_payload_sha256 != context["graph_sha256"]
        or ref(prepared.domain_contract_ref) != context["domain_ref"]
        or ref(prepared.semantic_profile_ref) != context["profile_ref"]
    ):
        raise ValueError("reviewed native parent changed during WK preparation")
