"""Diff helpers for shadow-mode integration.

Compares legacy retrieval/grading inputs against resolver-produced outputs and
emits a deterministic, JSON-serializable summary that callers can attach to per-
scenario report rows. The diff is read-only over the resolver result; nothing
here mutates state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.token_resolution.contracts import ResolvedTokens


def _normalize_str_set(values: Iterable[str]) -> set[str]:
    return {str(v or "").strip().lower() for v in values if str(v or "").strip()}


def _normalize_alias_map(mapping: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for key, vals in mapping.items():
        norm_key = str(key or "").strip().lower()
        if not norm_key:
            continue
        bucket = out.setdefault(norm_key, [])
        for v in vals:
            value = str(v or "").strip().lower()
            if value and value not in bucket:
                bucket.append(value)
    for key in list(out.keys()):
        out[key] = sorted(out[key])
    return out


def diff_token_sets(legacy: Iterable[str], resolver: Iterable[str]) -> dict[str, list[str]]:
    """Symmetric diff of two token collections (lowercase, sorted output)."""
    a = _normalize_str_set(legacy)
    b = _normalize_str_set(resolver)
    return {
        "only_in_legacy": sorted(a - b),
        "only_in_resolver": sorted(b - a),
        "in_both": sorted(a & b),
    }


def diff_alias_maps(
    legacy: Mapping[str, Iterable[str]],
    resolver: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    """Diff two canonical→aliases maps. Reports added/removed/extended canonicals."""
    a = _normalize_alias_map(legacy)
    b = _normalize_alias_map(resolver)
    only_legacy = {k: a[k] for k in sorted(a) if k not in b}
    only_resolver = {k: b[k] for k in sorted(b) if k not in a}
    extended_in_resolver: dict[str, list[str]] = {}
    extended_in_legacy: dict[str, list[str]] = {}
    for k in sorted(set(a) & set(b)):
        added = sorted(set(b[k]) - set(a[k]))
        removed = sorted(set(a[k]) - set(b[k]))
        if added:
            extended_in_resolver[k] = added
        if removed:
            extended_in_legacy[k] = removed
    return {
        "canonicals_only_in_legacy": only_legacy,
        "canonicals_only_in_resolver": only_resolver,
        "aliases_added_in_resolver": extended_in_resolver,
        "aliases_dropped_in_resolver": extended_in_legacy,
    }


def shadow_mode_diff(
    *,
    legacy_route_stopwords: Iterable[str],
    legacy_equivalences: Mapping[str, Iterable[str]],
    legacy_query_tokens: Iterable[str] | None = None,
    legacy_expanded_terms: Iterable[str] | None = None,
    resolver_result: ResolvedTokens,
) -> dict[str, Any]:
    """Build a single per-scenario shadow diff payload.

    The output is intended to be embedded under a ``shadow_token_resolution``
    key on the scenario's report row. Fields are stable: callers and downstream
    canvases can rely on the shape across runs.
    """
    diff: dict[str, Any] = {
        "schema": "dmb_token_resolver_shadow_v1",
        "campaign_id": resolver_result.campaign_id,
        "resolved_for_query": resolver_result.resolved_for_query,
        "route_stopwords_diff": diff_token_sets(
            legacy=legacy_route_stopwords,
            resolver=resolver_result.effective_route_stopwords,
        ),
        "equivalences_diff": diff_alias_maps(
            legacy=legacy_equivalences,
            resolver=resolver_result.effective_equivalences,
        ),
        "conflict_count": len(resolver_result.conflict_rows),
        "conflicts": [c.to_json_dict() for c in resolver_result.conflict_rows],
    }
    if legacy_query_tokens is not None:
        diff["query_tokens_diff"] = diff_token_sets(
            legacy=legacy_query_tokens,
            resolver=resolver_result.query_tokens,
        )
    if legacy_expanded_terms is not None:
        diff["expanded_terms_diff"] = diff_token_sets(
            legacy=legacy_expanded_terms,
            resolver=resolver_result.expanded_terms,
        )
    return diff
