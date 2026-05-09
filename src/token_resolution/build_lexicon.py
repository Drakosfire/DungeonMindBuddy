"""Build a deterministic lexicon artifact for a campaign.

This module is intentionally narrow: it knows how to assemble a
:class:`LexiconArtifact` from already-parsed inputs (alias specs, route token
maps, etc.). The work of extracting those inputs from the corpus or from
breadcrumb frontmatter lives in sibling modules (:mod:`extract_hub_aliases`,
:mod:`derive_stopwords`) so callers can mix-and-match input sources without
touching builder code.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Sequence

from src.token_resolution.contracts import (
    HubAliasSpec,
    LexiconArtifact,
    LexiconBuildSource,
)


def _coalesce_alias_map(*maps: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Merge multiple alias maps; later maps add aliases (no override semantics)."""
    out: dict[str, list[str]] = {}
    for source in maps:
        for canonical, aliases in source.items():
            key = str(canonical or "").strip().lower()
            if not key:
                continue
            bucket = out.setdefault(key, [])
            for alias in aliases:
                value = str(alias or "").strip()
                if value and value.lower() not in {b.lower() for b in bucket}:
                    bucket.append(value)
    return out


def assemble_lexicon(
    *,
    campaign_id: str,
    corpus_fingerprint: str = "",
    hub_aliases: Sequence[HubAliasSpec] = (),
    extra_equivalences: Mapping[str, Iterable[str]] | None = None,
    route_tokens: Mapping[str, Iterable[str]] | None = None,
    derived_route_stopwords: Iterable[str] = (),
    protected_tokens: Iterable[str] = (),
    source_refs: Mapping[str, Iterable[str]] | None = None,
    built_from: Sequence[LexiconBuildSource] = (),
) -> LexiconArtifact:
    """Compose a :class:`LexiconArtifact` from extracted inputs.

    The function performs no I/O. Callers stage extracted inputs (Packet B's
    job) and pass them in. This keeps the builder cheap to test and trivial to
    drive from CLI, eval harness, or future ingestion pipelines.
    """
    aliases_from_hubs: dict[str, list[str]] = {}
    for spec in hub_aliases:
        slug_key = str(spec.slug or "").strip().lower()
        if not slug_key:
            continue
        aliases_from_hubs.setdefault(slug_key, []).extend(spec.normalized_aliases())

    equivalences = _coalesce_alias_map(
        aliases_from_hubs,
        extra_equivalences or {},
    )

    return LexiconArtifact(
        campaign_id=str(campaign_id or "").strip(),
        corpus_fingerprint=corpus_fingerprint,
        built_from=tuple(built_from),
        equivalences=equivalences,
        route_tokens=dict(route_tokens or {}),
        derived_route_stopwords=list(derived_route_stopwords),
        protected_tokens=list(protected_tokens),
        source_refs=dict(source_refs or {}),
    )


def write_lexicon_artifact(artifact: LexiconArtifact, path: Path) -> Path:
    """Write the artifact deterministically (sorted keys, trailing newline).

    Returns the path that was written so callers can chain it into pipelines.
    """
    payload = artifact.to_json_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_lexicon_artifact(path: Path) -> LexiconArtifact:
    """Read a previously-written artifact and validate its schema/version."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return LexiconArtifact.from_json_dict(raw)
