"""Typed schemas for layered token resolution.

These are intentionally small, immutable, and JSON-serializable. The package is
designed to be liftable, so dataclasses here import only from the standard
library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

LEXICON_SCHEMA_V1 = "dmb_token_lexicon_v1"
LEXICON_VERSION = 1

RESOLVED_TOKENS_SCHEMA_V1 = "dmb_resolved_tokens_v1"

LAYER_SCENARIO = "scenario"
LAYER_HUB = "hub"
LAYER_LEXICON = "lexicon"
LAYER_DEFAULTS = "defaults"

LAYER_ORDER: tuple[str, ...] = (
    LAYER_SCENARIO,
    LAYER_HUB,
    LAYER_LEXICON,
    LAYER_DEFAULTS,
)

ACTION_INCLUDE = "include"
ACTION_EXCLUDE = "exclude"
ACTION_SHADOW = "shadow"


def _sorted_unique_str_list(values: Iterable[str]) -> list[str]:
    """Stable, lowercase-deduped, sorted string list (ignores empty entries).

    Lexicon and resolver outputs need byte-stable JSON across builds. Source
    iteration order should never leak into the artifact.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        token = str(raw or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    out.sort()
    return out


def _sorted_token_alias_map(mapping: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Sort canonical keys and per-key alias lists. Drops empty buckets."""
    result: dict[str, list[str]] = {}
    for key in sorted({str(k or "").strip().lower() for k in mapping.keys() if str(k or "").strip()}):
        original_values: Iterable[str] = mapping.get(key, ())
        # Lookup by exact key first, fall back to case-insensitive scan for callers
        # that may pass keys with mixed case.
        if not original_values:
            for existing_key, existing_values in mapping.items():
                if str(existing_key or "").strip().lower() == key:
                    original_values = existing_values
                    break
        aliases = _sorted_unique_str_list(original_values)
        if aliases:
            result[key] = aliases
    return result


@dataclass(frozen=True)
class GenericDefaults:
    """Corpus-agnostic defaults for the bottom layer of the precedence stack.

    These are deliberately small. Anything that smells like a campaign or world
    name MUST live in the lexicon artifact, not here.
    """

    structural_route_stopwords: frozenset[str] = field(default_factory=frozenset)
    """Generic structural path words ('npcs', 'session', 'recap', etc.)."""

    expansion_token_stopwords: frozenset[str] = field(default_factory=frozenset)
    """Tokens that should never be used as a route-expansion seed."""

    query_signal_stopwords: frozenset[str] = field(default_factory=frozenset)
    """English filler words to drop when extracting query signal tokens."""

    base_equivalences: dict[str, list[str]] = field(default_factory=dict)
    """Canonical → aliases mapping that is corpus-agnostic and shippable as default."""

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "structural_route_stopwords": sorted(self.structural_route_stopwords),
            "expansion_token_stopwords": sorted(self.expansion_token_stopwords),
            "query_signal_stopwords": sorted(self.query_signal_stopwords),
            "base_equivalences": _sorted_token_alias_map(self.base_equivalences),
        }


@dataclass(frozen=True)
class HubAliasSpec:
    """Aliases attached to a hub/frontmatter entry.

    The ``slug`` is a stable, lowercase identifier (e.g. ``magma_spider``) and
    ``aliases`` are surface-form synonyms callers should treat as equivalent
    when evaluating retrieval/grading hits.
    """

    slug: str
    subject_class: str
    aliases: list[str] = field(default_factory=list)
    source_ref: str = ""

    def normalized_aliases(self) -> list[str]:
        return _sorted_unique_str_list(self.aliases)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "subject_class": self.subject_class,
            "aliases": self.normalized_aliases(),
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True)
class LexiconBuildSource:
    """One artifact source that contributed to the lexicon (for provenance)."""

    kind: str
    """e.g. ``breadcrumb_frontmatter``, ``hub_readme``, ``corpus_route_index``."""

    path: str
    """Repo-relative path string (no absolute filesystem prefixes)."""

    fingerprint: str = ""
    """Optional content fingerprint (mtime+size or hash)."""

    def to_json_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "path": self.path, "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class LexiconArtifact:
    """Auto-generated, on-disk lexicon for a campaign/setting.

    JSON serialization is deterministic: keys are sorted lexicographically and
    every list/value is normalized via the helpers above.
    """

    campaign_id: str
    corpus_fingerprint: str = ""
    built_from: tuple[LexiconBuildSource, ...] = field(default_factory=tuple)
    equivalences: dict[str, list[str]] = field(default_factory=dict)
    route_tokens: dict[str, list[str]] = field(default_factory=dict)
    derived_route_stopwords: list[str] = field(default_factory=list)
    protected_tokens: list[str] = field(default_factory=list)
    source_refs: dict[str, list[str]] = field(default_factory=dict)
    schema: str = LEXICON_SCHEMA_V1
    version: int = LEXICON_VERSION

    def to_json_dict(self) -> dict[str, Any]:
        """Deterministic JSON-ready representation."""
        return {
            "schema": self.schema,
            "version": self.version,
            "campaign_id": self.campaign_id,
            "corpus_fingerprint": self.corpus_fingerprint,
            "built_from": [s.to_json_dict() for s in self.built_from],
            "equivalences": _sorted_token_alias_map(self.equivalences),
            "route_tokens": _sorted_token_alias_map(self.route_tokens),
            "derived_route_stopwords": _sorted_unique_str_list(self.derived_route_stopwords),
            "protected_tokens": _sorted_unique_str_list(self.protected_tokens),
            "source_refs": _sorted_token_alias_map(self.source_refs),
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "LexiconArtifact":
        if not isinstance(payload, Mapping):
            raise TypeError(f"LexiconArtifact payload must be a mapping, got {type(payload)!r}")
        schema = str(payload.get("schema") or "").strip()
        if schema and schema != LEXICON_SCHEMA_V1:
            raise ValueError(f"Unsupported lexicon schema: {schema!r}")
        version = int(payload.get("version") or LEXICON_VERSION)
        if version != LEXICON_VERSION:
            raise ValueError(f"Unsupported lexicon version: {version!r}")
        built_from_raw = payload.get("built_from") or []
        built_from = tuple(
            LexiconBuildSource(
                kind=str(item.get("kind", "")),
                path=str(item.get("path", "")),
                fingerprint=str(item.get("fingerprint", "")),
            )
            for item in built_from_raw
            if isinstance(item, Mapping)
        )
        return cls(
            campaign_id=str(payload.get("campaign_id", "")),
            corpus_fingerprint=str(payload.get("corpus_fingerprint", "")),
            built_from=built_from,
            equivalences=dict(payload.get("equivalences") or {}),
            route_tokens=dict(payload.get("route_tokens") or {}),
            derived_route_stopwords=list(payload.get("derived_route_stopwords") or []),
            protected_tokens=list(payload.get("protected_tokens") or []),
            source_refs=dict(payload.get("source_refs") or {}),
            schema=schema or LEXICON_SCHEMA_V1,
            version=version,
        )


@dataclass(frozen=True)
class ScenarioOverrides:
    """Per-scenario layer (highest precedence).

    Carries the user's per-question authority so resolver decisions stay
    falsifiable from the scenario file alone.
    """

    semantic_equivalences: dict[str, list[str]] = field(default_factory=dict)
    force_include_tokens: list[str] = field(default_factory=list)
    force_exclude_tokens: list[str] = field(default_factory=list)
    extra_route_stopwords: list[str] = field(default_factory=list)
    source_ref: str = ""

    def normalized_equivalences(self) -> dict[str, list[str]]:
        return _sorted_token_alias_map(self.semantic_equivalences)

    def normalized_force_include(self) -> list[str]:
        return _sorted_unique_str_list(self.force_include_tokens)

    def normalized_force_exclude(self) -> list[str]:
        return _sorted_unique_str_list(self.force_exclude_tokens)

    def normalized_extra_route_stopwords(self) -> list[str]:
        return _sorted_unique_str_list(self.extra_route_stopwords)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "semantic_equivalences": self.normalized_equivalences(),
            "force_include_tokens": self.normalized_force_include(),
            "force_exclude_tokens": self.normalized_force_exclude(),
            "extra_route_stopwords": self.normalized_extra_route_stopwords(),
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True)
class ProvenanceRow:
    """One token decision attributed to a single layer."""

    token: str
    layer: str
    source_ref: str
    action: str = ACTION_INCLUDE

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "layer": self.layer,
            "source_ref": self.source_ref,
            "action": self.action,
        }


@dataclass(frozen=True)
class ConflictRow:
    """Recorded when a higher layer shadows a lower layer's claim on a token."""

    token: str
    winning_layer: str
    shadowed_layer: str
    winning_source_ref: str = ""
    shadowed_source_ref: str = ""
    note: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "winning_layer": self.winning_layer,
            "shadowed_layer": self.shadowed_layer,
            "winning_source_ref": self.winning_source_ref,
            "shadowed_source_ref": self.shadowed_source_ref,
            "note": self.note,
        }


@dataclass(frozen=True)
class ResolvedTokens:
    """Output of :func:`src.token_resolution.resolver.resolve_for_query`."""

    campaign_id: str
    resolved_for_query: str
    query_tokens: list[str] = field(default_factory=list)
    expanded_terms: list[str] = field(default_factory=list)
    effective_equivalences: dict[str, list[str]] = field(default_factory=dict)
    effective_route_stopwords: list[str] = field(default_factory=list)
    provenance_rows: list[ProvenanceRow] = field(default_factory=list)
    conflict_rows: list[ConflictRow] = field(default_factory=list)
    schema: str = RESOLVED_TOKENS_SCHEMA_V1

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "campaign_id": self.campaign_id,
            "resolved_for_query": self.resolved_for_query,
            "query_tokens": _sorted_unique_str_list(self.query_tokens),
            "expanded_terms": _sorted_unique_str_list(self.expanded_terms),
            "effective_equivalences": _sorted_token_alias_map(self.effective_equivalences),
            "effective_route_stopwords": _sorted_unique_str_list(self.effective_route_stopwords),
            "provenance_rows": [row.to_json_dict() for row in self.provenance_rows],
            "conflict_rows": [row.to_json_dict() for row in self.conflict_rows],
        }
