"""Corpus-agnostic defaults for the bottom layer of the precedence stack.

Anything campaign- or setting-specific is forbidden here. Such tokens belong in
the lexicon artifact (auto-derived) or a hub frontmatter alias (canon-attached).
"""

from __future__ import annotations

from src.token_resolution.contracts import GenericDefaults

_STRUCTURAL_ROUTE_STOPWORDS: frozenset[str] = frozenset(
    {
        # Generic corpus-structural folder/role words. NEVER campaign or world names.
        "and",
        "campaign",
        "campaigns",
        "cities",
        "dossiers",
        "location",
        "locations",
        "npcs",
        "parties",
        "pcs",
        "session",
        "sessions",
        "the",
        "towns",
        "town",
        "factions",
        "items",
        "events",
        "world",
        "recap",
        "recaps",
        "prep",
    }
)

_QUERY_SIGNAL_STOPWORDS: frozenset[str] = frozenset(
    {
        # English filler/question words that aren't useful retrieval signal.
        "a",
        "about",
        "after",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "before",
        "but",
        "by",
        "can",
        "did",
        "do",
        "does",
        "during",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "she",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
    }
)

_EXPANSION_TOKEN_STOPWORDS: frozenset[str] = _STRUCTURAL_ROUTE_STOPWORDS | frozenset(
    {
        # Reuse structural words and add tokens that are too generic to seed
        # route expansion (would over-match unrelated routes).
        "and",
        "the",
        "of",
    }
)


def default_generic_defaults() -> GenericDefaults:
    """Frozen, corpus-agnostic default layer.

    No setting-specific names, no campaign vocabulary. Adding world/place names
    here is an architectural regression — they belong in the lexicon artifact.
    """
    return GenericDefaults(
        structural_route_stopwords=_STRUCTURAL_ROUTE_STOPWORDS,
        expansion_token_stopwords=_EXPANSION_TOKEN_STOPWORDS,
        query_signal_stopwords=_QUERY_SIGNAL_STOPWORDS,
        base_equivalences={},
    )
