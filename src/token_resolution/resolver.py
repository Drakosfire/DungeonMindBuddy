"""Layered token resolver.

Implements the precedence stack described in the package docstring:

    scenario  >  hub  >  lexicon  >  defaults

Equivalences from lower layers contribute additional aliases (union) so the
resolver does not silently drop hub knowledge when a scenario adds a new word.
``force_exclude_tokens`` from the scenario layer is the explicit kill switch
that *shadows* a lower-layer claim and emits a :class:`ConflictRow`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from src.token_resolution.contracts import (
    ACTION_EXCLUDE,
    ACTION_INCLUDE,
    ACTION_SHADOW,
    LAYER_DEFAULTS,
    LAYER_HUB,
    LAYER_LEXICON,
    LAYER_SCENARIO,
    ConflictRow,
    GenericDefaults,
    HubAliasSpec,
    LexiconArtifact,
    ProvenanceRow,
    ResolvedTokens,
    ScenarioOverrides,
)


_QUERY_TOKEN_RE = re.compile(r"[A-Za-z0-9'_-]+")


def _tokenize_query(query: str, *, signal_stopwords: Iterable[str]) -> list[str]:
    stopwords = {str(s).strip().lower() for s in signal_stopwords if str(s).strip()}
    raw_tokens = _QUERY_TOKEN_RE.findall(query.lower())
    seen: set[str] = set()
    tokens: list[str] = []
    for raw in raw_tokens:
        token = raw.strip("_-'")
        if not token or token in stopwords or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _layered_equivalences(
    *,
    scenario: ScenarioOverrides,
    hub_aliases: Sequence[HubAliasSpec],
    lexicon: LexiconArtifact,
    defaults: GenericDefaults,
) -> tuple[dict[str, list[str]], list[ProvenanceRow], list[ConflictRow]]:
    """Merge equivalences across layers; track provenance and conflicts.

    Returns a tuple of (effective_equivalences, provenance_rows, conflict_rows).
    """
    layers: list[tuple[str, str, dict[str, list[str]]]] = []  # (layer, source_ref, mapping)

    layers.append(
        (
            LAYER_SCENARIO,
            scenario.source_ref or "scenario",
            {
                k: [str(v).strip().lower() for v in vs if str(v).strip()]
                for k, vs in scenario.normalized_equivalences().items()
            },
        )
    )
    hub_map: dict[str, list[str]] = {}
    hub_source_refs: dict[str, str] = {}
    for spec in hub_aliases:
        slug = (spec.slug or "").strip().lower()
        if not slug:
            continue
        hub_map.setdefault(slug, []).extend(spec.normalized_aliases())
        if slug not in hub_source_refs and spec.source_ref:
            hub_source_refs[slug] = spec.source_ref
    layers.append((LAYER_HUB, "hub", hub_map))

    layers.append((LAYER_LEXICON, "lexicon", {k: list(vs) for k, vs in lexicon.equivalences.items()}))
    layers.append((LAYER_DEFAULTS, "defaults", {k: list(vs) for k, vs in defaults.base_equivalences.items()}))

    merged: dict[str, list[str]] = {}
    canonical_first_layer: dict[str, str] = {}
    canonical_first_source: dict[str, str] = {}
    provenance: list[ProvenanceRow] = []
    conflicts: list[ConflictRow] = []
    seen_alias_origin: dict[tuple[str, str], tuple[str, str]] = {}

    force_excluded = {t.lower() for t in scenario.normalized_force_exclude()}

    for layer_name, layer_source_ref, mapping in layers:
        for canonical, aliases in mapping.items():
            key = canonical.strip().lower()
            if not key:
                continue
            if key in force_excluded:
                # Scenario override explicitly bans this canonical.
                provenance.append(
                    ProvenanceRow(
                        token=key,
                        layer=LAYER_SCENARIO,
                        source_ref=scenario.source_ref or "scenario",
                        action=ACTION_EXCLUDE,
                    )
                )
                if layer_name != LAYER_SCENARIO:
                    conflicts.append(
                        ConflictRow(
                            token=key,
                            winning_layer=LAYER_SCENARIO,
                            shadowed_layer=layer_name,
                            winning_source_ref=scenario.source_ref or "scenario",
                            shadowed_source_ref=_layer_source(layer_name, layer_source_ref, hub_source_refs, key),
                            note="force_exclude_tokens",
                        )
                    )
                continue

            if key not in merged:
                merged[key] = []
                canonical_first_layer[key] = layer_name
                canonical_first_source[key] = _layer_source(layer_name, layer_source_ref, hub_source_refs, key)
            else:
                if layer_name != canonical_first_layer[key]:
                    conflicts.append(
                        ConflictRow(
                            token=key,
                            winning_layer=canonical_first_layer[key],
                            shadowed_layer=layer_name,
                            winning_source_ref=canonical_first_source[key],
                            shadowed_source_ref=_layer_source(layer_name, layer_source_ref, hub_source_refs, key),
                            note="lower-layer aliases unioned into higher-layer key",
                        )
                    )
            for alias in aliases:
                alias_key = alias.strip().lower()
                if not alias_key:
                    continue
                if alias_key in {a.lower() for a in merged[key]}:
                    continue
                merged[key].append(alias_key)
                seen_alias_origin[(key, alias_key)] = (
                    layer_name,
                    _layer_source(layer_name, layer_source_ref, hub_source_refs, key),
                )

    for canonical, aliases in sorted(merged.items()):
        provenance.append(
            ProvenanceRow(
                token=canonical,
                layer=canonical_first_layer.get(canonical, LAYER_DEFAULTS),
                source_ref=canonical_first_source.get(canonical, "defaults"),
                action=ACTION_INCLUDE,
            )
        )
        for alias in sorted(aliases):
            origin = seen_alias_origin.get((canonical, alias))
            if origin is None:
                continue
            provenance.append(
                ProvenanceRow(
                    token=f"{canonical}->{alias}",
                    layer=origin[0],
                    source_ref=origin[1],
                    action=ACTION_INCLUDE,
                )
            )

    if conflicts:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[ConflictRow] = []
        for row in conflicts:
            key = (row.token, row.winning_layer, row.shadowed_layer)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        conflicts = deduped

    return merged, provenance, conflicts


def _layer_source(
    layer_name: str,
    fallback_ref: str,
    hub_source_refs: Mapping[str, str],
    canonical: str,
) -> str:
    if layer_name == LAYER_HUB and canonical in hub_source_refs:
        return hub_source_refs[canonical]
    return fallback_ref


def _effective_route_stopwords(
    *,
    scenario: ScenarioOverrides,
    lexicon: LexiconArtifact,
    defaults: GenericDefaults,
) -> tuple[list[str], list[ProvenanceRow]]:
    """Union route stopwords across layers; subtract scenario force-include.

    Provenance attributes each stopword to the earliest layer that contributed it.
    """
    rows: list[ProvenanceRow] = []
    bag: dict[str, tuple[str, str]] = {}

    for token in defaults.structural_route_stopwords:
        bag.setdefault(token.lower(), (LAYER_DEFAULTS, "defaults"))
    for token in lexicon.derived_route_stopwords:
        clean = (token or "").strip().lower()
        if not clean:
            continue
        bag.setdefault(clean, (LAYER_LEXICON, "lexicon"))
    for token in scenario.normalized_extra_route_stopwords():
        clean = (token or "").strip().lower()
        if not clean:
            continue
        bag.setdefault(clean, (LAYER_SCENARIO, scenario.source_ref or "scenario"))

    force_include = {t.lower() for t in scenario.normalized_force_include()}
    for token in sorted(bag):
        layer, source = bag[token]
        if token in force_include:
            rows.append(
                ProvenanceRow(
                    token=token,
                    layer=LAYER_SCENARIO,
                    source_ref=scenario.source_ref or "scenario",
                    action=ACTION_SHADOW,
                )
            )
            continue
        rows.append(ProvenanceRow(token=token, layer=layer, source_ref=source, action=ACTION_EXCLUDE))

    return [t for t in sorted(bag) if t not in force_include], rows


def _expansion_terms(
    *,
    query_tokens: Sequence[str],
    effective_equivalences: Mapping[str, Sequence[str]],
    expansion_token_stopwords: Iterable[str],
) -> list[str]:
    """Derive expansion terms from canonical equivalences seeded by query tokens.

    Layering means an expansion term wins inclusion when:
      * The canonical is a token literally in the query, OR
      * Any alias of the canonical appears in the query.
    """
    stopwords = {str(s).strip().lower() for s in expansion_token_stopwords if str(s).strip()}
    qset = {t.lower() for t in query_tokens if t}
    expanded: list[str] = []
    for canonical in sorted(effective_equivalences):
        aliases = list(effective_equivalences[canonical])
        if not (canonical in qset or any(a.lower() in qset for a in aliases)):
            continue
        for alias in [canonical] + list(aliases):
            value = alias.lower().strip()
            if not value or value in stopwords or value in qset or value in expanded:
                continue
            expanded.append(value)
    return expanded


def resolve_for_query(
    query: str,
    *,
    scenario_overrides: ScenarioOverrides | None = None,
    hub_aliases: Sequence[HubAliasSpec] = (),
    lexicon: LexiconArtifact,
    defaults: GenericDefaults,
) -> ResolvedTokens:
    """Resolve token-related decisions for one query through the layered stack."""
    scenario = scenario_overrides or ScenarioOverrides()
    query_tokens = _tokenize_query(query, signal_stopwords=defaults.query_signal_stopwords)
    effective_eq, eq_provenance, conflicts = _layered_equivalences(
        scenario=scenario,
        hub_aliases=hub_aliases,
        lexicon=lexicon,
        defaults=defaults,
    )
    effective_stopwords, stopword_provenance = _effective_route_stopwords(
        scenario=scenario,
        lexicon=lexicon,
        defaults=defaults,
    )
    expanded_terms = _expansion_terms(
        query_tokens=query_tokens,
        effective_equivalences=effective_eq,
        expansion_token_stopwords=defaults.expansion_token_stopwords,
    )

    return ResolvedTokens(
        campaign_id=lexicon.campaign_id,
        resolved_for_query=query,
        query_tokens=query_tokens,
        expanded_terms=expanded_terms,
        effective_equivalences=effective_eq,
        effective_route_stopwords=effective_stopwords,
        provenance_rows=eq_provenance + stopword_provenance,
        conflict_rows=conflicts,
    )
