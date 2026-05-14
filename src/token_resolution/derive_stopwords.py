"""Derive setting-specific route stopwords from corpus signal — never literals.

A token earns "route stopword" status when:

1. It appears in a sufficient share of the route population (default 50%),
2. It is *not* in the protected-token allowlist (slugs of named entities), and
3. It is not already covered by the corpus-agnostic structural stopwords from
   :func:`src.token_resolution.defaults.default_generic_defaults`.

The output is a deduped, sorted list. The function is a pure transform: given
the same routes/protected_tokens it returns the same answer, so artifacts are
deterministic.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

from src.token_resolution.defaults import default_generic_defaults

_TOKEN_SPLIT_RE = re.compile(r"[/_\-\s]+")


def _route_tokens(route: str) -> list[str]:
    """Return lowercase tokens (length >= 3) extracted from a route path."""
    cleaned = (route or "").strip().strip("/")
    if not cleaned:
        return []
    out: list[str] = []
    for raw in _TOKEN_SPLIT_RE.split(cleaned):
        token = raw.strip().lower()
        # Drop file extensions and very short structural tokens.
        if "." in token:
            token = token.rsplit(".", 1)[0]
        if len(token) >= 3:
            out.append(token)
    return out


def derive_route_stopwords(
    routes: Iterable[str],
    *,
    protected_tokens: Iterable[str] = (),
    frequency_threshold: float = 0.5,
    min_route_count: int = 4,
    extra_excluded: Iterable[str] = (),
) -> list[str]:
    """Return tokens that recur in >= ``frequency_threshold`` of routes.

    Args:
        routes: All route strings observed in the campaign (deduped is fine).
        protected_tokens: Slug-derived tokens that must never become stopwords.
        frequency_threshold: Required share of routes the token must appear in.
        min_route_count: Need at least this many routes before deriving anything;
            otherwise we return no setting-specific stopwords (avoids dropping
            real signal in tiny corpora).
        extra_excluded: Caller-supplied additional protections (e.g. tokens that
            aren't entity slugs but still carry retrieval value).

    The corpus-agnostic structural stopwords from ``default_generic_defaults``
    are subtracted from the result so callers can union the two layers without
    double-counting.
    """
    route_list = [str(r or "").strip() for r in routes if str(r or "").strip()]
    deduped = list(dict.fromkeys(route_list))
    if len(deduped) < min_route_count:
        return []

    protected_set = {
        str(t or "").strip().lower() for t in protected_tokens if str(t or "").strip()
    }
    extra_excluded_set = {
        str(t or "").strip().lower() for t in extra_excluded if str(t or "").strip()
    }
    structural = default_generic_defaults().structural_route_stopwords

    counts: Counter[str] = Counter()
    for route in deduped:
        for token in set(_route_tokens(route)):
            counts[token] += 1

    needed = max(1, int(round(len(deduped) * frequency_threshold)))
    derived: set[str] = set()
    for token, count in counts.items():
        if count < needed:
            continue
        if token in protected_set or token in extra_excluded_set:
            continue
        if token in structural:
            # Already covered by the defaults layer — don't duplicate.
            continue
        derived.add(token)
    return sorted(derived)


def collect_routes_from_breadcrumb_records(records: Iterable[dict]) -> list[str]:
    """Helper: pull all ``routes[].normalized_route`` values from session-memory records.

    Mirrors the contract of records emitted by
    :mod:`src.session_memory.breadcrumb_normalize`,
    but keeps the dependency uni-directional so this package stays liftable.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for rec in records:
        routes = rec.get("routes") if isinstance(rec, dict) else None
        if not routes:
            continue
        for r in routes:
            if not isinstance(r, dict):
                continue
            value = str(r.get("normalized_route") or "").strip()
            if value and value not in seen_set:
                seen_set.add(value)
                seen.append(value)
    return seen
