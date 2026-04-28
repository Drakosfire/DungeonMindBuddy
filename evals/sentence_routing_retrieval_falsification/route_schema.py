"""``route_sentence_units_to_hubs`` schema (legacy: Stage B): hub manifest + strict ``sentence_hub_routes_v1`` envelope (Pydantic).

Spec: ``Docs/Plans/DESIGN-Sentence-Routing-Stage-B-Hub-Routing.md`` §3–4.
"""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence


from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_SENTENCE_HUB_ROUTES_V1 = "sentence_hub_routes_v1"

# Expand post-parse to ``session_pc_roster_slugs`` from recap frontmatter, registry, or manifest order.
THE_PARTY_ROUTE_SENTINEL = "the_party"


def manifest_pc_slug_set(manifest_jsonable: list[dict[str, Any]] | None) -> set[str]:
    """Hub slugs declared as PCs in the manifest (for stripping duplicates when ``the_party`` is present)."""
    if not manifest_jsonable:
        return set()
    out: set[str] = set()
    for e in manifest_jsonable:
        if not isinstance(e, dict):
            continue
        if str(e.get("subject_class") or "").strip() != "pc":
            continue
        s = str(e.get("slug") or "").strip()
        if s:
            out.add(s)
    return out


def _has_pc_assignment(hubs: list[str], manifest_pc_slugs: set[str]) -> bool:
    """``the_party`` expands to PCs; otherwise only manifest PC slugs count as PC assignments."""
    return THE_PARTY_ROUTE_SENTINEL in hubs or any(h in manifest_pc_slugs for h in hubs)


def strip_pc_slugs_when_the_party_present(
    hubs: list[Any],
    manifest_pc_slugs: set[str],
) -> list[str]:
    """
    When ``the_party`` is present, drop manifest **PC** slugs only (models often mix ``the_party`` + focal PC).

    Non-PC hubs (NPC, location, …) are kept. When ``manifest_pc_slugs`` is empty, cannot classify PCs —
    falls back to sole ``the_party`` (legacy behavior for mixed wire output).
    """
    raw = [str(h).strip() for h in hubs if str(h).strip()]
    if THE_PARTY_ROUTE_SENTINEL not in raw:
        return raw
    if not manifest_pc_slugs:
        return [THE_PARTY_ROUTE_SENTINEL]
    out: list[str] = []
    seen: set[str] = set()
    out.append(THE_PARTY_ROUTE_SENTINEL)
    seen.add(THE_PARTY_ROUTE_SENTINEL)
    for h in raw:
        if h == THE_PARTY_ROUTE_SENTINEL:
            continue
        if h in manifest_pc_slugs:
            continue
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out

_SUBJECT_CLASSES = frozenset(
    {
        "npc",
        "pc",
        "location",
        "faction",
        "session",
        "campaign",
        "item",
        "event",
        "world",
    }
)
_SLUG_RE = re.compile(r"^[a-z0-9_]+$")

_CONFIDENCE = frozenset({"high", "medium", "low"})

_ROUTING_DIAGNOSTIC_VALUES = frozenset(
    {
        "npc_placeholder",
        "location_placeholder",
        "event_or_object_placeholder",
        "new_hub_candidate",
        "true_empty",
    }
)
# OpenAI JSON-schema enum list (sorted for deterministic ordering).
ROUTING_DIAGNOSTIC_ENUM: tuple[str, ...] = tuple(sorted(_ROUTING_DIAGNOSTIC_VALUES))
ROUTING_DIAGNOSTIC_VALUE_SET = _ROUTING_DIAGNOSTIC_VALUES

# Recap / GM typos vs manifest slugs (Eldyrwild long-form prose). Applied only when the target
# slug is present in the run's hub_manifest.
_RECAP_SPELLING_IN_UNIT_TEXT: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\bKaresmine\b"), "Karsemine", "karsemine"),
    (re.compile(r"\bBaergorm\b"), "Baergrom", "baergrom"),
    (re.compile(r"\bBaegrom\b"), "Baergrom", "baergrom"),
    (re.compile(r"\bBaergom\b"), "Baergrom", "baergrom"),
    (re.compile(r"\bBeargrom\b"), "Baergrom", "baergrom"),
)

# Wire / model output that is not a manifest slug but unambiguously maps to one.
_ASSIGNED_HUB_SLUG_ALIASES: dict[str, str] = {
    "karesmine": "karsemine",
    "beargrom": "baergrom",
    "baergorm": "baergrom",
    "baegrom": "baergrom",
    "baergom": "baergrom",
}


def normalize_assigned_hubs_for_manifest(
    hubs: list[str],
    manifest_slugs: set[str],
) -> list[str]:
    """
    Canonicalize known slug typos, drop empties, dedupe in first-seen order.
    Unknown hubs are left unchanged (``collect_stage_b_violations`` still emits B0b).
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw in hubs:
        h = str(raw).strip()
        if not h:
            continue
        if h in manifest_slugs:
            canon = h
        else:
            cand = _ASSIGNED_HUB_SLUG_ALIASES.get(h.lower())
            if cand and cand in manifest_slugs:
                canon = cand
            else:
                canon = h
        if canon not in seen:
            seen.add(canon)
            out.append(canon)
    return out


def normalize_sentence_units_text_for_manifest(
    units: list[dict[str, Any]],
    manifest_slugs: set[str],
) -> list[dict[str, Any]]:
    """Copy sentence_units and rewrite common PC name misspellings when the hub slug is in play."""
    out = deepcopy(units)
    for u in out:
        text = str(u.get("text") or "")
        for pattern, repl, slug in _RECAP_SPELLING_IN_UNIT_TEXT:
            if slug in manifest_slugs:
                text = pattern.sub(repl, text)
        u["text"] = text
    return out


def normalize_route_rows_for_manifest(
    routes: Sequence[RouteRow],
    manifest_slugs: set[str],
) -> list[RouteRow]:
    return [
        r.model_copy(
            update={
                "assigned_hubs": normalize_assigned_hubs_for_manifest(
                    r.assigned_hubs, manifest_slugs
                )
            }
        )
        for r in routes
    ]


def expand_the_party_sentinel(
    routes: Sequence[RouteRow],
    session_pc_roster_slugs: list[str],
) -> list[RouteRow]:
    """
    Replace ``the_party`` with the canonical session roster (GM-declared order), preserving any **non-PC**
    hubs that remained after ``strip_pc_slugs_when_the_party_present`` (e.g. NPC hubs on mixed manifests).

    Call after ``parse_routes_envelope`` and before ``normalize_route_rows_for_manifest``.
    """
    if not session_pc_roster_slugs:
        raise ValueError("session_pc_roster_slugs required to expand the_party sentinel")
    roster_set = set(session_pc_roster_slugs)
    out: list[RouteRow] = []
    for r in routes:
        hubs = list(r.assigned_hubs)
        if THE_PARTY_ROUTE_SENTINEL not in hubs:
            out.append(r)
            continue
        extras = [h for h in hubs if h != THE_PARTY_ROUTE_SENTINEL]
        merged = list(session_pc_roster_slugs)
        for h in extras:
            if h not in roster_set:
                merged.append(h)
                roster_set.add(h)
        out.append(r.model_copy(update={"assigned_hubs": merged}))
    return out


class HubManifestEntry(BaseModel):
    slug: str
    path: str
    subject_class: str
    campaign_id: str | None = None
    label: str | None = None

    @field_validator("slug")
    @classmethod
    def slug_shape(cls, v: str) -> str:
        s = str(v).strip()
        if not _SLUG_RE.match(s):
            raise ValueError(f"slug must match ^[a-z0-9_]+$: {s!r}")
        return s

    @field_validator("subject_class")
    @classmethod
    def subject_ok(cls, v: str) -> str:
        s = str(v).strip()
        if s not in _SUBJECT_CLASSES:
            raise ValueError(f"invalid subject_class {s!r}; expected one of {sorted(_SUBJECT_CLASSES)}")
        return s


class RouteRow(BaseModel):
    unit_id: str
    assigned_hubs: list[str] = Field(default_factory=list)
    confidence: str
    rationale: str
    needs_new_hub_candidate: bool
    routing_diagnostic_bucket: str | None = None

    @field_validator("assigned_hubs")
    @classmethod
    def unique_hubs(cls, hubs: list[str]) -> list[str]:
        out = [str(h).strip() for h in hubs if str(h).strip()]
        if len(out) != len(set(out)):
            raise ValueError("assigned_hubs must not contain duplicate slugs")
        return out

    @field_validator("confidence")
    @classmethod
    def confidence_ok(cls, v: str) -> str:
        s = str(v).strip().lower()
        if s not in _CONFIDENCE:
            raise ValueError(f"confidence must be one of {sorted(_CONFIDENCE)}")
        return s

    @field_validator("routing_diagnostic_bucket")
    @classmethod
    def diagnostic_bucket_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if s not in _ROUTING_DIAGNOSTIC_VALUES:
            raise ValueError(
                f"routing_diagnostic_bucket must be one of {sorted(_ROUTING_DIAGNOSTIC_VALUES)} or null; got {v!r}"
            )
        return s

    @model_validator(mode="after")
    def hub_vs_candidate(self) -> RouteRow:
        if self.needs_new_hub_candidate and self.assigned_hubs:
            raise ValueError("needs_new_hub_candidate true requires empty assigned_hubs")
        return self

    @model_validator(mode="after")
    def diagnostic_compatible_when_assigned(self) -> RouteRow:
        """
        Non-null diagnostic alongside hubs is only allowed for ``npc_placeholder``. The manifest-aware
        parser further requires at least one PC assignment (or ``the_party``) for that exception.
        """
        hubs = self.assigned_hubs
        b = self.routing_diagnostic_bucket
        if not hubs or b is None:
            return self
        if b == "npc_placeholder":
            return self
        raise ValueError(
            "routing_diagnostic_bucket must be null when assigned_hubs is non-empty "
            f"(unless npc_placeholder); got {b!r}"
        )


class RoutesEnvelope(BaseModel):
    """Wire JSON uses the key ``schema`` (alias); Python field avoids shadowing ``BaseModel.schema``."""

    model_config = ConfigDict(populate_by_name=True)

    envelope_schema: str = Field(alias="schema")
    routes: list[RouteRow]

    @field_validator("envelope_schema")
    @classmethod
    def schema_ok(cls, v: str) -> str:
        if str(v) != SCHEMA_SENTENCE_HUB_ROUTES_V1:
            raise ValueError(f"schema must be {SCHEMA_SENTENCE_HUB_ROUTES_V1!r}")
        return str(v)


def parse_routes_envelope(
    payload: dict[str, Any],
    *,
    manifest_jsonable: list[dict[str, Any]] | None = None,
) -> RoutesEnvelope:
    """
    Validate and return routes envelope; raises ``pydantic.ValidationError`` on failure.

    When ``manifest_jsonable`` is provided, ``assigned_hubs`` rows are normalized so ``the_party`` does not
    coexist with redundant **PC** slugs (non-PC hubs are kept).
    """
    payload_in = deepcopy(payload)
    pc_slugs = manifest_pc_slug_set(manifest_jsonable)
    routes_raw = payload_in.get("routes")
    if isinstance(routes_raw, list):
        for row in routes_raw:
            if not isinstance(row, dict):
                continue
            ah = row.get("assigned_hubs")
            if isinstance(ah, list):
                row["assigned_hubs"] = strip_pc_slugs_when_the_party_present(ah, pc_slugs)
    envelope = RoutesEnvelope.model_validate(payload_in)
    if manifest_jsonable is not None:
        for row in envelope.routes:
            if (
                row.assigned_hubs
                and row.routing_diagnostic_bucket == "npc_placeholder"
                and not _has_pc_assignment(row.assigned_hubs, pc_slugs)
            ):
                raise ValueError(
                    "routing_diagnostic_bucket='npc_placeholder' with assigned_hubs "
                    "requires at least one PC hub or the_party"
                )
    return envelope


def validate_hub_manifest(
    entries: list[dict[str, Any] | HubManifestEntry] | None,
    *,
    corpus_root: Path,
    validate_paths: bool,
    max_manifest_entries: int = 64,
) -> list[str]:
    """
    Pre-LLM manifest checks. Returns list of violation strings (empty if ok).
    """
    violations: list[str] = []
    if not entries:
        violations.append("M0: hub_manifest is empty or missing")
        return violations
    if len(entries) > max_manifest_entries:
        violations.append(f"M0: hub_manifest has {len(entries)} entries > max {max_manifest_entries}")

    seen: set[str] = set()
    normalized: list[HubManifestEntry] = []
    for i, raw in enumerate(entries):
        try:
            row = raw if isinstance(raw, HubManifestEntry) else HubManifestEntry.model_validate(raw)
        except Exception as exc:
            violations.append(f"M0: hub_manifest[{i}] invalid: {exc}")
            continue
        if row.slug in seen:
            violations.append(f"M0: duplicate manifest slug {row.slug!r}")
        seen.add(row.slug)
        normalized.append(row)

    if validate_paths and normalized:
        root = corpus_root.resolve()
        for row in normalized:
            p = root / row.path
            if not p.is_file():
                violations.append(f"M1: manifest path missing for slug={row.slug!r}: {row.path}")

    return violations


def manifest_slug_set(entries: list[HubManifestEntry] | list[dict[str, Any]]) -> set[str]:
    slugs: set[str] = set()
    for raw in entries:
        if isinstance(raw, HubManifestEntry):
            slugs.add(raw.slug)
        else:
            s = str((raw or {}).get("slug") or "").strip()
            if s:
                slugs.add(s)
    return slugs
