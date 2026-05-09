"""Layered token resolution for retrieval/grading.

This package owns the precedence stack:

1. Scenario overrides (gold-authored)
2. Hub/frontmatter aliases (canon-attached)
3. Corpus-derived lexicon artifact (auto-generated)
4. Generic defaults (corpus-agnostic)

It is designed to be lifted into its own project: only ``contracts``,
``defaults``, ``build_lexicon``, ``derive_stopwords``, ``extract_hub_aliases``,
``resolver``, and ``explain`` make up the public surface. No other module in
this repo should be imported from here.
"""

from src.token_resolution.contracts import (
    LEXICON_SCHEMA_V1,
    LEXICON_VERSION,
    RESOLVED_TOKENS_SCHEMA_V1,
    ConflictRow,
    GenericDefaults,
    HubAliasSpec,
    LexiconArtifact,
    LexiconBuildSource,
    ProvenanceRow,
    ResolvedTokens,
    ScenarioOverrides,
)
from src.token_resolution.defaults import default_generic_defaults

__all__ = [
    "LEXICON_SCHEMA_V1",
    "LEXICON_VERSION",
    "RESOLVED_TOKENS_SCHEMA_V1",
    "ConflictRow",
    "GenericDefaults",
    "HubAliasSpec",
    "LexiconArtifact",
    "LexiconBuildSource",
    "ProvenanceRow",
    "ResolvedTokens",
    "ScenarioOverrides",
    "default_generic_defaults",
]
