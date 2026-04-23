"""Stage D vertical slice: deterministic NPC entity resolution (v0).

Stage D consumes a frozen ``StageCOutput`` (three buckets) plus the same
events / registry / PC roster Stage C consumed, and emits four arrays:

* ``resolved_entities[]``     — every input new_candidate /
  unresolved_descriptor routed to a resolution.
* ``proposed_aliases[]``      — alias additions for existing registry slugs.
* ``proposed_new_records[]``  — partial ``NpcRegistryRecord`` rows for net-new
  candidates (status=candidate, hub_path=null).
* ``unresolvable[]``          — items legitimately ambiguous after Stage D's
  best effort.

Stage D is **propose-only**: it writes a per-run sidecar to
``artifacts/runs/YYYY-MM-DD/`` and (per-cohort) an aggregated
``proposals/<campaign>_stage_d_proposals_<ts>.json`` for GM review. It NEVER
mutates ``_npc_registry.json``. See
``Docs/Plans/AUDIT-Stage-D-Entity-Resolution-Discovery.md`` §4 + §5.

v0 runs **pure deterministic heuristics** (no LLM call):

* PC re-check (block any merge whose canonical names a PC slug).
* Registry alias / display_name / slug substring match (case-insensitive).
* Slug-variant clustering across ``new_npc_candidates[]`` with substring
  containment (length ≥ 4 of the shorter slug) OR Levenshtein distance ≤ 2;
  canonical = longest slug in the cluster (precedent: bubbles ↔
  bubbles_the_float_goat → bubbles_the_float_goat is canonical, matching the
  GM-promoted record).
* Event-pool sanity: every slug in ``participants ∪ referenced_slugs`` of
  the events should appear in some downstream bucket; gaps surface as
  telemetry only (not a gate).

Run::

    uv run python -m evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run \\
        --scenario-json evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session3_c1.json \\
        --n 5

Options::

    --n N                      Cohort size (default: 1)
    --scenario-json PATH       Gold scenario JSON
    --runs-root PATH           Override artifact runs root
    --no-writes                Skip writing artifacts to disk
    --enable-llm-coreference   No-op in v0; reserved for v1 LLM coreference pass
    -q / --quiet               Suppress progress lines
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pydantic import BaseModel, Field  # noqa: E402

from src.contracts.npc_registry import NpcRegistryRecord, load_npc_registry  # noqa: E402

from evals.stage_d_entity_resolution_vertical_slice.grader import grade_stage_d  # noqa: E402
from evals.stage_d_entity_resolution_vertical_slice.stage_d_run_report import (  # noqa: E402
    StageDRunSummary,
    write_stage_d_cohort_proposals,
    write_stage_d_multi_summary,
    write_stage_d_run_report,
)


_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "stage_d_session20.json"
_RUNNER_VERSION = "stage_d_runner_v0_deterministic"


# ---------------------------------------------------------------------------
# Pydantic structured output (mirrors the audit's StageDOutput shape)
# ---------------------------------------------------------------------------


class ResolvedEntity(BaseModel):
    source_kind: str
    source_index: int
    resolution: str
    canonical_slug: str
    evidence_event_indices: list[int] = Field(default_factory=list)
    rationale: str = ""


class ProposedAlias(BaseModel):
    target_slug: str
    alias_text: str
    source_descriptor_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class ProposedNewRecord(BaseModel):
    """Partial NpcRegistryRecord with status pinned to 'candidate'."""

    slug: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    status: str = "candidate"
    first_session: int = 0
    last_session: int = 0
    hub_path: str | None = None
    setting_hub_path: str | None = None
    notes: str = ""


class Unresolvable(BaseModel):
    source_kind: str
    source_index: int
    descriptor: str
    reason: str


class StageDOutput(BaseModel):
    resolved_entities: list[ResolvedEntity] = Field(default_factory=list)
    proposed_aliases: list[ProposedAlias] = Field(default_factory=list)
    proposed_new_records: list[ProposedNewRecord] = Field(default_factory=list)
    unresolvable: list[Unresolvable] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scenario / fixture loaders
# ---------------------------------------------------------------------------


def _resolve_relative(path_str: str | Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


def load_scenario(path: Path | None = None) -> dict[str, Any]:
    p = (path or _GOLD_SCENARIO).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing scenario JSON: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_stage_c_output(path_str: str) -> dict[str, Any]:
    """Load a frozen Stage C output fixture.

    The fixture is either (a) a raw dict with three buckets
    (tracked_npcs_active / new_npc_candidates / unresolved_descriptors), or
    (b) a Stage C run report sidecar with ``stage_c_output`` nested inside.
    """
    p = _resolve_relative(path_str)
    if not p.is_file():
        raise FileNotFoundError(f"Stage C output fixture not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "stage_c_output" in data:
        inner = data["stage_c_output"]
        if isinstance(inner, dict):
            return inner
    if isinstance(data, dict) and "tracked_npcs_active" in data:
        return data
    raise ValueError(
        f"Stage C output fixture {p} does not look like a Stage C output "
        f"(missing 'stage_c_output' or 'tracked_npcs_active' keys)"
    )


def load_events_fixture(path_str: str) -> list[dict[str, Any]]:
    p = _resolve_relative(path_str)
    if not p.is_file():
        raise FileNotFoundError(f"events fixture not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"events fixture {p} is not a top-level JSON array")
    return data


def load_registry_records(path_str: str) -> list[dict[str, Any]]:
    p = _resolve_relative(path_str)
    records = load_npc_registry(p)
    return [r.model_dump(mode="json") for r in records]


# ---------------------------------------------------------------------------
# Helpers — PC roster, registry index, slug similarity
# ---------------------------------------------------------------------------


def _pc_index(pc_roster: list[dict[str, Any]]) -> tuple[set[str], list[str]]:
    """Return (pc_slug_set, pc_substring_terms_lc)."""
    slugs: set[str] = set()
    terms: list[str] = []
    for pc in pc_roster or []:
        if not isinstance(pc, dict):
            continue
        slug = str(pc.get("slug") or "").strip().lower()
        if slug:
            slugs.add(slug)
            terms.append(slug)
        dn = str(pc.get("display_name") or "").strip().lower()
        if dn:
            terms.append(dn)
        for alias in pc.get("aliases") or []:
            if isinstance(alias, str):
                a = alias.strip().lower()
                if a:
                    terms.append(a)
    return slugs, [t for t in terms if t]


def _is_pc_match(text: str, pc_terms: list[str]) -> bool:
    t = text.strip().lower()
    if not t:
        return False
    for term in pc_terms:
        if term and term in t:
            return True
    return False


class _RegistryIndex:
    """Lightweight registry lookup helpers for the deterministic resolver."""

    def __init__(self, registry: list[dict[str, Any]]) -> None:
        self.records = registry
        self.slugs = {
            str(r.get("slug") or "").strip().lower()
            for r in registry
            if isinstance(r, dict)
        }
        self.slugs.discard("")
        self._by_slug: dict[str, dict[str, Any]] = {}
        for r in registry:
            if not isinstance(r, dict):
                continue
            slug = str(r.get("slug") or "").strip().lower()
            if slug:
                self._by_slug[slug] = r

    def get(self, slug: str) -> dict[str, Any] | None:
        return self._by_slug.get(slug.strip().lower())

    def find_by_slug(self, slug: str) -> str | None:
        slug_lc = slug.strip().lower()
        return slug_lc if slug_lc in self.slugs else None

    def find_by_text_match(self, text: str) -> tuple[str, str] | None:
        """Match descriptor text against registry display_name + aliases.

        Returns (matched_slug, matched_term_kind) or None. matched_term_kind
        is 'display_name', 'alias', or 'slug'.
        """
        text_lc = text.strip().lower()
        if not text_lc:
            return None
        for rec in self.records:
            if not isinstance(rec, dict):
                continue
            slug = str(rec.get("slug") or "").strip().lower()
            if not slug:
                continue
            if slug == text_lc:
                return slug, "slug"
            dn = str(rec.get("display_name") or "").strip().lower()
            if dn and (dn in text_lc or text_lc in dn):
                return slug, "display_name"
            for alias in rec.get("aliases") or []:
                if not isinstance(alias, str):
                    continue
                a = alias.strip().lower()
                if a and a in text_lc:
                    return slug, "alias"
        return None


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _slugs_should_cluster(a: str, b: str) -> bool:
    """Return True if two suggested_slugs likely refer to the same entity.

    Conservative precision floor:
      * Substring containment where the shorter is at least 4 chars (so
        ``bubbles`` ↔ ``bubbles_the_float_goat`` clusters; ``cat`` ↔
        ``cat_owl`` does not because shorter < 4).
      * OR Levenshtein distance ≤ 2 between equal-ish length slugs (catches
        single-character typos like ``glowkindle`` ↔ ``glowkindel``).
    """
    if a == b:
        return False
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 4 and short in long_:
        return True
    # Levenshtein only when lengths are within 2 to avoid trivial false
    # positives (e.g. short prefix sharing).
    if abs(len(a) - len(b)) <= 2 and _levenshtein(a, b) <= 2:
        return True
    return False


def _parse_session_number(session_label: str) -> int:
    if not session_label:
        return 0
    m = re.search(r"(\d+)", session_label)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Core deterministic resolver
# ---------------------------------------------------------------------------


def _normalize_descriptor_aliases(descriptor: str) -> list[str]:
    """Pull short noun-phrase aliases out of a descriptor (best-effort).

    For a descriptor like ``"Bubbles the Float Goat"`` we want aliases
    ``["Bubbles"]``. Cheap heuristic: if the descriptor contains the word
    ``"the"`` (case-insensitive), the bit BEFORE ``the`` is a useful alias.
    """
    if not descriptor:
        return []
    parts = re.split(r"\bthe\b", descriptor, flags=re.IGNORECASE, maxsplit=1)
    if len(parts) == 2 and parts[0].strip():
        head = parts[0].strip().rstrip(",").strip()
        if head and head.lower() != descriptor.strip().lower():
            return [head]
    return []


def _build_proposed_record(
    *,
    slug: str,
    descriptor: str,
    session_number: int,
    notes_extra: str = "",
) -> ProposedNewRecord:
    display_name = descriptor.strip() or slug.replace("_", " ").title()
    aliases = _normalize_descriptor_aliases(descriptor)
    return ProposedNewRecord(
        slug=slug,
        display_name=display_name,
        aliases=aliases,
        status="candidate",
        first_session=session_number,
        last_session=session_number,
        hub_path=None,
        setting_hub_path=None,
        notes=(notes_extra or "Proposed by Stage D deterministic v0 from "
               f"Stage C new_npc_candidate descriptor {descriptor!r}.").strip(),
    )


def resolve_stage_d(
    *,
    stage_c_output: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    pc_roster: list[dict[str, Any]],
    session_number: int,
) -> StageDOutput:
    """Deterministic v0 resolver. No LLM call.

    Strategy (in order):

    1. **New_candidates pass** — for each item:
       a. PC check: drop into unresolvable if descriptor or suggested_slug
          contains a PC term.
       b. Registry slug match → merge_to_registry_slug.
       c. Registry alias / display_name substring match → merge_to_registry_slug.
       d. Defer (collect for clustering pass).

    2. **Cluster deferred new_candidates** by ``_slugs_should_cluster`` —
       canonical = longest slug in cluster. Canonical → new_net_entity with
       proposed_new_record; others → merge_to_canonical_new_candidate.

    3. **Unresolved_descriptors pass** — for each item:
       a. PC check.
       b. Registry alias / display_name substring match → merge_to_registry_slug
          (and emit proposed_alias if descriptor not already in aliases /
          display_name).
       c. Else → unresolvable (Stage D v0 does NOT speculatively merge
          generic descriptions into new_candidates without name evidence).
    """
    pc_slugs, pc_terms = _pc_index(pc_roster)
    reg = _RegistryIndex(registry)

    new_candidates: list[dict[str, Any]] = list(
        stage_c_output.get("new_npc_candidates") or []
    )
    unresolved_descriptors: list[dict[str, Any]] = list(
        stage_c_output.get("unresolved_descriptors") or []
    )

    resolved: list[ResolvedEntity] = []
    proposed_aliases: list[ProposedAlias] = []
    proposed_records: list[ProposedNewRecord] = []
    unresolvable: list[Unresolvable] = []

    deferred_new_cands: list[tuple[int, dict[str, Any]]] = []

    for i, rec in enumerate(new_candidates):
        if not isinstance(rec, dict):
            continue
        descriptor = str(rec.get("descriptor") or "")
        suggested_slug = str(rec.get("suggested_slug") or "").strip().lower()
        evidence = rec.get("evidence_event_indices") or []

        if _is_pc_match(suggested_slug, pc_terms) or _is_pc_match(
            descriptor, pc_terms
        ):
            unresolvable.append(
                Unresolvable(
                    source_kind="new_candidate",
                    source_index=i,
                    descriptor=descriptor,
                    reason="matches PC roster — Stage C should have dropped this",
                )
            )
            continue

        registry_slug = reg.find_by_slug(suggested_slug) if suggested_slug else None
        if registry_slug and registry_slug not in pc_slugs:
            resolved.append(
                ResolvedEntity(
                    source_kind="new_candidate",
                    source_index=i,
                    resolution="merge_to_registry_slug",
                    canonical_slug=registry_slug,
                    evidence_event_indices=list(evidence),
                    rationale=(
                        f"suggested_slug {suggested_slug!r} matches registry slug"
                    ),
                )
            )
            continue

        text_match = reg.find_by_text_match(descriptor)
        if text_match and text_match[0] not in pc_slugs:
            registry_slug, kind = text_match
            resolved.append(
                ResolvedEntity(
                    source_kind="new_candidate",
                    source_index=i,
                    resolution="merge_to_registry_slug",
                    canonical_slug=registry_slug,
                    evidence_event_indices=list(evidence),
                    rationale=(
                        f"descriptor {descriptor!r} matches registry "
                        f"{kind} for {registry_slug!r}"
                    ),
                )
            )
            continue

        deferred_new_cands.append((i, rec))

    # Cluster the deferred new_candidates by slug similarity.
    visited: set[int] = set()
    for idx_a, rec_a in deferred_new_cands:
        if idx_a in visited:
            continue
        slug_a = str(rec_a.get("suggested_slug") or "").strip().lower()
        cluster: list[tuple[int, dict[str, Any]]] = [(idx_a, rec_a)]
        for idx_b, rec_b in deferred_new_cands:
            if idx_b == idx_a or idx_b in visited:
                continue
            slug_b = str(rec_b.get("suggested_slug") or "").strip().lower()
            if slug_a and slug_b and _slugs_should_cluster(slug_a, slug_b):
                cluster.append((idx_b, rec_b))
        for idx, _ in cluster:
            visited.add(idx)

        canonical_idx, canonical_rec = max(
            cluster,
            key=lambda pair: len(str(pair[1].get("suggested_slug") or "")),
        )
        canonical_slug = str(canonical_rec.get("suggested_slug") or "").strip().lower()
        if not canonical_slug or canonical_slug in pc_slugs:
            for idx, rec in cluster:
                unresolvable.append(
                    Unresolvable(
                        source_kind="new_candidate",
                        source_index=idx,
                        descriptor=str(rec.get("descriptor") or ""),
                        reason=(
                            "canonical slug missing or matches PC — refused "
                            "to propose new_net_entity"
                        ),
                    )
                )
            continue

        canonical_descriptor = str(canonical_rec.get("descriptor") or "")
        canonical_evidence = list(canonical_rec.get("evidence_event_indices") or [])

        # Aggregate evidence from all cluster members for the canonical record.
        merged_evidence: list[int] = []
        seen_evi: set[int] = set()
        for _, rec in cluster:
            for ev in rec.get("evidence_event_indices") or []:
                if isinstance(ev, int) and not isinstance(ev, bool):
                    if ev not in seen_evi:
                        seen_evi.add(ev)
                        merged_evidence.append(ev)

        cluster_note = ""
        cluster_slugs = sorted({
            str(r.get("suggested_slug") or "").strip().lower()
            for _, r in cluster
            if str(r.get("suggested_slug") or "").strip()
        })
        if len(cluster_slugs) > 1:
            cluster_note = (
                f"Stage D clustered slug variants {cluster_slugs} → canonical "
                f"{canonical_slug!r}."
            )

        resolved.append(
            ResolvedEntity(
                source_kind="new_candidate",
                source_index=canonical_idx,
                resolution="new_net_entity",
                canonical_slug=canonical_slug,
                evidence_event_indices=canonical_evidence,
                rationale=(
                    f"new_candidate {canonical_slug!r} not in registry; "
                    f"proposed as new candidate record."
                    + (f" {cluster_note}" if cluster_note else "")
                ).strip(),
            )
        )
        proposed_records.append(
            _build_proposed_record(
                slug=canonical_slug,
                descriptor=canonical_descriptor,
                session_number=session_number,
                notes_extra=(
                    f"Proposed by Stage D deterministic v0; descriptor "
                    f"{canonical_descriptor!r}; "
                    f"evidence event indices {merged_evidence}."
                    + (f" {cluster_note}" if cluster_note else "")
                ),
            )
        )

        for idx, rec in cluster:
            if idx == canonical_idx:
                continue
            descriptor = str(rec.get("descriptor") or "")
            evidence = list(rec.get("evidence_event_indices") or [])
            slug_b = str(rec.get("suggested_slug") or "").strip().lower()
            resolved.append(
                ResolvedEntity(
                    source_kind="new_candidate",
                    source_index=idx,
                    resolution="merge_to_canonical_new_candidate",
                    canonical_slug=canonical_slug,
                    evidence_event_indices=evidence,
                    rationale=(
                        f"slug variant {slug_b!r} clustered with canonical "
                        f"{canonical_slug!r} (substring/Levenshtein heuristic)"
                    ),
                )
            )

    # Unresolved descriptors pass.
    for i, rec in enumerate(unresolved_descriptors):
        if not isinstance(rec, dict):
            continue
        descriptor = str(rec.get("descriptor") or "")
        evidence = rec.get("evidence_event_indices") or []
        if _is_pc_match(descriptor, pc_terms):
            unresolvable.append(
                Unresolvable(
                    source_kind="unresolved_descriptor",
                    source_index=i,
                    descriptor=descriptor,
                    reason="matches PC roster — Stage C should have dropped this",
                )
            )
            continue
        text_match = reg.find_by_text_match(descriptor)
        if text_match and text_match[0] not in pc_slugs:
            registry_slug, kind = text_match
            resolved.append(
                ResolvedEntity(
                    source_kind="unresolved_descriptor",
                    source_index=i,
                    resolution="merge_to_registry_slug",
                    canonical_slug=registry_slug,
                    evidence_event_indices=list(evidence),
                    rationale=(
                        f"unresolved descriptor {descriptor!r} matches registry "
                        f"{kind} for {registry_slug!r}"
                    ),
                )
            )
            existing_record = reg.get(registry_slug)
            existing_terms_lc: set[str] = set()
            if existing_record:
                dn = str(existing_record.get("display_name") or "").strip().lower()
                if dn:
                    existing_terms_lc.add(dn)
                for alias in existing_record.get("aliases") or []:
                    if isinstance(alias, str):
                        a = alias.strip().lower()
                        if a:
                            existing_terms_lc.add(a)
            if descriptor.strip().lower() not in existing_terms_lc:
                proposed_aliases.append(
                    ProposedAlias(
                        target_slug=registry_slug,
                        alias_text=descriptor.strip(),
                        source_descriptor_ids=[
                            f"unresolved_descriptors[{i}]",
                        ],
                        rationale=(
                            f"Stage D matched unresolved descriptor against "
                            f"existing registry {kind}; proposing alias to make "
                            f"future passes match this descriptor exactly."
                        ),
                    )
                )
            continue
        unresolvable.append(
            Unresolvable(
                source_kind="unresolved_descriptor",
                source_index=i,
                descriptor=descriptor,
                reason=(
                    "generic descriptor with no name evidence; Stage D v0 "
                    "deterministic heuristics declined to merge into "
                    "registry or new_candidate without a substring match"
                ),
            )
        )

    return StageDOutput(
        resolved_entities=resolved,
        proposed_aliases=proposed_aliases,
        proposed_new_records=proposed_records,
        unresolvable=unresolvable,
    )


# ---------------------------------------------------------------------------
# Telemetry: event-pool sanity check (non-gating)
# ---------------------------------------------------------------------------


def _event_pool_coverage(
    events: list[dict[str, Any]],
    stage_c_output: dict[str, Any],
    stage_d_output: dict[str, Any],
    pc_slugs: set[str],
    registry_slugs: set[str],
) -> dict[str, Any]:
    pool: set[str] = set()
    for ev in events or []:
        for key in ("participants", "referenced_slugs"):
            for s in ev.get(key) or []:
                if isinstance(s, str):
                    pool.add(s.strip().lower())
    pool.discard("")

    # Account for slugs reachable via:
    #   - PC roster
    #   - tracked_npcs_active[] (already-resolved by Stage C)
    #   - stage_d resolved_entities[].canonical_slug (registry or net-new)
    #   - stage_d proposed_new_records[].slug
    accounted: set[str] = set(pc_slugs)
    for rec in stage_c_output.get("tracked_npcs_active") or []:
        if isinstance(rec, dict):
            slug = str(rec.get("slug") or "").strip().lower()
            if slug:
                accounted.add(slug)
    for rec in stage_d_output.get("resolved_entities") or []:
        if isinstance(rec, dict):
            slug = str(rec.get("canonical_slug") or "").strip().lower()
            if slug:
                accounted.add(slug)
    for rec in stage_d_output.get("proposed_new_records") or []:
        if isinstance(rec, dict):
            slug = str(rec.get("slug") or "").strip().lower()
            if slug:
                accounted.add(slug)

    # Drop event-pool entries that aren't real entities (e.g. anchored
    # registry-known slugs absent from this scenario's PC roster but present
    # in the registry — those are still "accounted for" via Stage C tracking).
    accounted |= registry_slugs
    pool_unaccounted = sorted(pool - accounted)
    return {
        "event_pool_size": len(pool),
        "accounted_size": len(pool & accounted),
        "unaccounted_event_slugs": pool_unaccounted,
    }


# ---------------------------------------------------------------------------
# Per-run orchestration
# ---------------------------------------------------------------------------


def run_stage_d(
    *,
    scenario: dict[str, Any],
    stage_c_output: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    enable_llm_coreference: bool = False,
) -> dict[str, Any]:
    inp = scenario.get("input") or {}
    pc_roster = list(inp.get("pc_roster") or [])
    session_label = str(inp.get("session_label") or "")
    session_number = int(
        inp.get("session_number")
        or _parse_session_number(session_label)
        or 0
    )

    # v0: --enable-llm-coreference is a documented no-op. v1 will add a
    # narrow coreference pass for hard unresolvables (Kirfan-class without
    # referenced_slugs[]).
    _ = enable_llm_coreference  # noqa: F841 — reserved for v1 LLM extension

    parsed = resolve_stage_d(
        stage_c_output=stage_c_output,
        events=events,
        registry=registry,
        pc_roster=pc_roster,
        session_number=session_number,
    )
    output_dict = parsed.model_dump()
    grade = grade_stage_d(output_dict, scenario, stage_c_output, events, registry)

    pc_slugs, _ = _pc_index(pc_roster)
    registry_slugs = {
        str(r.get("slug") or "").strip().lower()
        for r in registry
        if isinstance(r, dict)
    }
    registry_slugs.discard("")
    coverage = _event_pool_coverage(
        events, stage_c_output, output_dict, pc_slugs, registry_slugs
    )

    telemetry = dict(grade["telemetry"])
    telemetry.update(coverage)

    return {
        "stage_d_output": output_dict,
        "violations": grade["violations"],
        "violation_counts": grade["violation_counts"],
        "telemetry": telemetry,
        "per_gate_verdict": grade["per_gate_verdict"],
        "all_gates_passed": grade["all_gates_passed"],
        "gates_passed_str": grade["gates_passed"],
        "runner_version": _RUNNER_VERSION,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage D: NPC entity resolution (deterministic v0)"
    )
    parser.add_argument("--n", type=int, default=1, help="Cohort size (default: 1)")
    parser.add_argument("--scenario-json", type=Path, default=None)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true")
    parser.add_argument(
        "--enable-llm-coreference",
        action="store_true",
        help=(
            "v0 NO-OP — reserved for v1 LLM coreference pass on hard "
            "unresolvables (Kirfan-class without referenced_slugs[])."
        ),
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario_json)
    scenario_id = str(scenario.get("scenario_id") or "stage_d_unknown")

    inp = scenario.get("input") or {}
    stage_c_output_path = str(inp.get("stage_c_output_path") or "")
    events_path = str(inp.get("stage_a_events_path") or "")
    registry_path = str(inp.get("npc_registry_path") or "")
    campaign_id = str(inp.get("campaign_id") or "unknown_campaign")

    if not stage_c_output_path:
        print("scenario missing input.stage_c_output_path", file=sys.stderr)
        sys.exit(2)
    if not events_path:
        print("scenario missing input.stage_a_events_path", file=sys.stderr)
        sys.exit(2)
    if not registry_path:
        print("scenario missing input.npc_registry_path", file=sys.stderr)
        sys.exit(2)

    stage_c_output = load_stage_c_output(stage_c_output_path)
    events = load_events_fixture(events_path)
    registry = load_registry_records(registry_path)

    n = max(1, int(args.n))

    if not args.quiet:
        print(
            f"[stage-d] n={n} scenario={scenario_id} "
            f"events={len(events)} registry_records={len(registry)} "
            f"stage_c_inputs="
            f"new={len(stage_c_output.get('new_npc_candidates') or [])} "
            f"unresolved={len(stage_c_output.get('unresolved_descriptors') or [])} "
            f"tracked={len(stage_c_output.get('tracked_npcs_active') or [])} "
            f"deterministic_v0=True llm_coreference="
            f"{args.enable_llm_coreference}",
            file=sys.stderr,
        )

    summaries: list[StageDRunSummary] = []
    pass_count = 0

    for i in range(n):
        if not args.quiet:
            print(f"[stage-d] run {i + 1}/{n} starting…", file=sys.stderr)
        t0 = time.monotonic()
        result = run_stage_d(
            scenario=scenario,
            stage_c_output=stage_c_output,
            events=events,
            registry=registry,
            enable_llm_coreference=args.enable_llm_coreference,
        )
        elapsed_s = round(time.monotonic() - t0, 4)
        gates_passed = bool(result["all_gates_passed"])
        if gates_passed:
            pass_count += 1
        verdict = result["per_gate_verdict"]
        telemetry = result["telemetry"]
        verdict_str = " ".join(f"{k}={v}" for k, v in sorted(verdict.items()))
        print(
            f"[stage-d] run {i + 1}/{n} | "
            f"{'PASS' if gates_passed else 'FAIL'} | "
            f"resolved={telemetry.get('resolved_count', 0)} "
            f"new_records={telemetry.get('proposed_new_records_count', 0)} "
            f"aliases={telemetry.get('proposed_aliases_count', 0)} "
            f"unresolvable={telemetry.get('unresolvable_count', 0)} | "
            f"elapsed={elapsed_s}s | "
            f"{verdict_str}"
        )

        if not args.no_writes:
            paths, summary = write_stage_d_run_report(
                scenario_id=scenario_id,
                gates_passed=gates_passed,
                per_gate_verdict=verdict,
                violations=result["violations"],
                violation_counts=result["violation_counts"],
                grader_telemetry=telemetry,
                stage_d_output=result["stage_d_output"],
                runner_version=result["runner_version"],
                scenario=scenario,
                runs_root=args.runs_root,
                run_index=i if n > 1 else None,
                cohort_size=n if n > 1 else None,
            )
            summaries.append(summary)
            if not args.quiet:
                print(f"[stage-d] report: {paths.primary_md}", file=sys.stderr)
                print(f"[stage-d] sidecar: {paths.sidecar_json}", file=sys.stderr)
        else:
            summaries.append(
                StageDRunSummary(
                    run_index=i,
                    iso_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    gates_passed=gates_passed,
                    resolved_count=int(telemetry.get("resolved_count", 0)),
                    proposed_new_records_count=int(
                        telemetry.get("proposed_new_records_count", 0)
                    ),
                    proposed_aliases_count=int(
                        telemetry.get("proposed_aliases_count", 0)
                    ),
                    unresolvable_count=int(telemetry.get("unresolvable_count", 0)),
                    violation_counts=dict(result["violation_counts"]),
                    per_gate_verdict=dict(verdict),
                    primary_md_path="",
                    sidecar_json_path="",
                    extras={
                        "grader_telemetry": dict(telemetry),
                        "stage_d_output": dict(result["stage_d_output"]),
                    },
                )
            )

    if n > 1 and summaries and not args.no_writes:
        md_s, json_s = write_stage_d_multi_summary(
            summaries,
            scenario_id=scenario_id,
            runs_root=args.runs_root,
        )
        print(f"[stage-d] cohort summary: {md_s}", file=sys.stderr)
        print(f"[stage-d] cohort sidecar: {json_s}", file=sys.stderr)

    if summaries and not args.no_writes:
        proposals_path = write_stage_d_cohort_proposals(
            summaries,
            scenario_id=scenario_id,
            campaign_id=campaign_id,
            source_events=events,
            source_events_path=events_path,
        )
        if proposals_path is not None:
            print(f"[stage-d] proposals sidecar: {proposals_path}", file=sys.stderr)

    print(
        f"[stage-d] cohort done | scenario={scenario_id} | "
        f"pass_rate={pass_count}/{n}"
    )

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
