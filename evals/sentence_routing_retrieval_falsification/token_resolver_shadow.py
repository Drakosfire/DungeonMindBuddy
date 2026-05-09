"""Shadow-mode bridge between the eval harness and ``src.token_resolution``.

The harness keeps using its existing legacy code paths for retrieval/grading.
This module computes a parallel resolver-driven view and emits a diff so we
can compare both before cutover. The legacy path is the source of truth in
this phase; nothing here changes scoring.

Benchmark-specific equivalence seeds and the frozen legacy route-stopword list
used only for shadow diffs live in:

``artifacts/lexicon/benchmark_lexicon_seeds_v1.json`` (committed).

Override path with env ``DMB_BENCHMARK_LEXICON_SEEDS`` when needed (absolute or
repo-relative resolved from cwd).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.token_resolution import (
    LexiconArtifact,
    LexiconBuildSource,
    ScenarioOverrides,
    default_generic_defaults,
)
from src.token_resolution.build_lexicon import assemble_lexicon
from src.token_resolution.derive_stopwords import (
    collect_routes_from_breadcrumb_records,
    derive_route_stopwords,
)
from src.token_resolution.explain import shadow_mode_diff
from src.token_resolution.extract_hub_aliases import (
    extract_hub_aliases_from_frontmatter,
)
from src.token_resolution.resolver import resolve_for_query

_BENCHMARK_LEXICON_SEEDS_SCHEMA = "dmb_benchmark_lexicon_seeds_v1"
_BENCHMARK_LEXICON_SEEDS_VERSION = 1

_benchmark_seeds_cache: "BenchmarkLexiconSeeds | None" = None


@dataclass(frozen=True)
class BenchmarkLexiconSeeds:
    """Payload from ``benchmark_lexicon_seeds_v1.json``."""

    equivalences: dict[str, list[str]]
    legacy_route_stopwords_for_shadow_diff: frozenset[str]
    source_path: str


def default_benchmark_lexicon_seeds_path() -> Path:
    """Default committed seed file next to this module."""
    override = (os.environ.get("DMB_BENCHMARK_LEXICON_SEEDS") or "").strip()
    if override:
        p = Path(override).expanduser()
        return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()
    here = Path(__file__).resolve().parent
    return (here / "artifacts" / "lexicon" / "benchmark_lexicon_seeds_v1.json").resolve()


def load_benchmark_lexicon_seeds(path: Path | None = None) -> BenchmarkLexiconSeeds:
    """Load and validate the benchmark lexicon seed JSON (no process-wide cache)."""
    resolved = (path or default_benchmark_lexicon_seeds_path()).resolve()
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"benchmark lexicon seeds must be a JSON object, got {type(raw)!r}")
    schema = str(raw.get("schema") or "")
    if schema != _BENCHMARK_LEXICON_SEEDS_SCHEMA:
        raise ValueError(f"unexpected seeds schema {schema!r} in {resolved}; expected {_BENCHMARK_LEXICON_SEEDS_SCHEMA!r}")
    version = int(raw.get("version") or 0)
    if version != _BENCHMARK_LEXICON_SEEDS_VERSION:
        raise ValueError(f"unsupported seeds version {version!r} in {resolved}")
    equiv_raw = raw.get("equivalences") or {}
    if not isinstance(equiv_raw, dict):
        raise ValueError(f"equivalences must be an object in {resolved}")
    equivalences: dict[str, list[str]] = {}
    for key, vals in equiv_raw.items():
        k = str(key or "").strip()
        if not k:
            continue
        if isinstance(vals, list):
            equivalences[k] = [str(v) for v in vals]
        else:
            equivalences[k] = [str(vals)]
    legacy_raw = raw.get("legacy_route_stopwords_for_shadow_diff") or []
    if not isinstance(legacy_raw, list):
        raise ValueError(f"legacy_route_stopwords_for_shadow_diff must be a list in {resolved}")
    legacy = frozenset(str(x).strip().lower() for x in legacy_raw if str(x).strip())
    return BenchmarkLexiconSeeds(
        equivalences=equivalences,
        legacy_route_stopwords_for_shadow_diff=legacy,
        source_path=str(resolved),
    )


def get_benchmark_lexicon_seeds() -> BenchmarkLexiconSeeds:
    """Process-wide memoized seeds (small, immutable, read once per interpreter)."""
    global _benchmark_seeds_cache
    if _benchmark_seeds_cache is None:
        _benchmark_seeds_cache = load_benchmark_lexicon_seeds()
    return _benchmark_seeds_cache


def clear_benchmark_lexicon_seeds_cache() -> None:
    """Drop the process-wide seed cache (tests only; not used by harness)."""
    global _benchmark_seeds_cache
    _benchmark_seeds_cache = None


def build_campaign_lexicon(
    *,
    breadcrumb_artifact_text: str,
    records: Sequence[Any],
    breadcrumb_md_path: Path | None = None,
    campaign_id: str = "",
    corpus_fingerprint: str = "",
    benchmark_seeds: BenchmarkLexiconSeeds | None = None,
) -> LexiconArtifact:
    """Build a campaign lexicon from already-loaded breadcrumb + records.

    The artifact is in-memory only; callers can persist via
    :func:`src.token_resolution.build_lexicon.write_lexicon_artifact` if they
    want a reusable on-disk artifact.

    ``benchmark_seeds`` defaults to :func:`get_benchmark_lexicon_seeds` so
    ``--records-jsonl`` and breadcrumb ingest paths share the same cohort seeds
    without duplicating literals in Python.
    """
    seeds = benchmark_seeds or get_benchmark_lexicon_seeds()
    frontmatter = ""
    if breadcrumb_artifact_text:
        front_chunks = breadcrumb_artifact_text.split("---", 2)
        if len(front_chunks) >= 3:
            frontmatter = front_chunks[1]
    extraction = extract_hub_aliases_from_frontmatter(
        frontmatter,
        source_path=str(breadcrumb_md_path) if breadcrumb_md_path else "",
    )
    record_dicts: list[dict[str, Any]] = []
    for r in records:
        if hasattr(r, "to_json_dict"):
            record_dicts.append(r.to_json_dict())  # type: ignore[union-attr]
        elif isinstance(r, dict):
            record_dicts.append(r)
    routes = collect_routes_from_breadcrumb_records(record_dicts)
    derived_stopwords = derive_route_stopwords(
        routes,
        protected_tokens=extraction.protected_tokens,
    )

    built_from: list[LexiconBuildSource] = [
        LexiconBuildSource(
            kind="benchmark_lexicon_seeds",
            path=seeds.source_path,
            fingerprint="",
        )
    ]
    if breadcrumb_md_path:
        built_from.append(
            LexiconBuildSource(
                kind="breadcrumb_frontmatter",
                path=str(breadcrumb_md_path),
                fingerprint="",
            )
        )

    return assemble_lexicon(
        campaign_id=campaign_id,
        corpus_fingerprint=corpus_fingerprint,
        hub_aliases=extraction.aliases,
        extra_equivalences=seeds.equivalences,
        derived_route_stopwords=derived_stopwords,
        protected_tokens=list(extraction.protected_tokens),
        built_from=tuple(built_from),
    )


def build_scenario_overrides(scenario: dict[str, Any]) -> ScenarioOverrides:
    """Translate gold scenario fields into a :class:`ScenarioOverrides`."""
    raw_equiv = scenario.get("semantic_equivalences") or {}
    equiv: dict[str, list[str]] = {}
    if isinstance(raw_equiv, dict):
        for key, values in raw_equiv.items():
            if isinstance(values, list):
                equiv[str(key)] = [str(v) for v in values]
            else:
                equiv[str(key)] = [str(values)]
    return ScenarioOverrides(
        semantic_equivalences=equiv,
        force_include_tokens=[str(t) for t in (scenario.get("force_include_tokens") or [])],
        force_exclude_tokens=[str(t) for t in (scenario.get("force_exclude_tokens") or [])],
        extra_route_stopwords=[str(t) for t in (scenario.get("extra_route_stopwords") or [])],
        source_ref=str(scenario.get("id") or ""),
    )


def compute_shadow_diff(
    *,
    scenario: dict[str, Any],
    lexicon: LexiconArtifact,
    legacy_route_stopwords: Iterable[str],
    legacy_equivalences: dict[str, Iterable[str]],
) -> dict[str, Any]:
    """Run the resolver for one scenario and produce a shadow diff payload."""
    overrides = build_scenario_overrides(scenario)
    resolved = resolve_for_query(
        str(scenario.get("question") or ""),
        scenario_overrides=overrides,
        lexicon=lexicon,
        defaults=default_generic_defaults(),
    )
    diff = shadow_mode_diff(
        legacy_route_stopwords=legacy_route_stopwords,
        legacy_equivalences=legacy_equivalences,
        resolver_result=resolved,
    )
    diff["lexicon_summary"] = {
        "campaign_id": lexicon.campaign_id,
        "alias_canonical_count": len(lexicon.equivalences),
        "derived_route_stopwords": list(lexicon.derived_route_stopwords),
        "protected_token_count": len(lexicon.protected_tokens),
    }
    diff["resolved_tokens"] = resolved.to_json_dict()
    return diff


def merged_route_token_stopwords(
    *,
    records: list[dict[str, Any]],
    breadcrumb_artifact_text: str = "",
    lexicon: LexiconArtifact | None = None,
) -> frozenset[str]:
    """Union of corpus-agnostic structural stopwords + derived campaign tokens."""
    built = lexicon or build_campaign_lexicon(
        breadcrumb_artifact_text=breadcrumb_artifact_text,
        records=records,
    )
    defaults = default_generic_defaults()
    return frozenset(built.derived_route_stopwords) | frozenset(defaults.structural_route_stopwords)


def effective_semantic_equivalences_for_question(
    *,
    question: str,
    scenario: dict[str, Any],
    lexicon: LexiconArtifact,
) -> dict[str, list[str]]:
    """Layered equivalences for grading (scenario wins; lexicon fills the rest)."""
    resolved = resolve_for_query(
        question,
        scenario_overrides=build_scenario_overrides(scenario),
        lexicon=lexicon,
        defaults=default_generic_defaults(),
    )
    return dict(resolved.effective_equivalences)
