"""Grader for the Stage D NPC entity-resolution vertical slice.

Stage D consumes a frozen ``StageCOutput`` (three buckets: tracked_npcs_active[],
new_npc_candidates[], unresolved_descriptors[]) plus the same events JSON,
NPC registry, and PC roster Stage C consumed, and emits **propose-only**
auditable merge decisions. Stage D NEVER mutates the registry directly — it
writes a sidecar that the GM reviews before any registry change.

See ``Docs/Plans/AUDIT-Stage-D-Entity-Resolution-Discovery.md`` §1 (contract),
§4 (write-surface — propose-only), §5 (vertical slice ER1-ER5 sketch), §7
(TL;DR) for the design audit motivating these gates.

Stage D output (``StageDOutput``) is FOUR arrays:

* ``resolved_entities[]``    — every input new_candidate / unresolved_descriptor
  routed to a resolution: ``merge_to_registry_slug``,
  ``merge_to_canonical_new_candidate``, or ``new_net_entity``.
* ``proposed_aliases[]``     — alias additions for existing registry slugs
  (descriptor text the model resolved against the registry that may not yet
  be in the registry's ``aliases[]``).
* ``proposed_new_records[]`` — partial ``NpcRegistryRecord`` rows for truly
  net-new candidates (status MUST be ``candidate``, hub_path MUST be null,
  per ``Docs/CONVENTION-Corpus-Subject-Schemas.md`` §8).
* ``unresolvable[]``         — items legitimately ambiguous after Stage D's
  best effort (generic creature descriptions, contradictory evidence).

Five gates:

* **ER1** Schema validity: output is a JSON object with the four required
  arrays; every record's required fields are typed correctly; every
  ``canonical_slug`` and ``proposed_new_records[*].slug`` matches
  ``^[a-z0-9_]+$``; every ``source_index`` resolves to a real position in the
  Stage C input bucket named by ``source_kind``; ``resolution`` is one of the
  three allowed verbs; ``source_kind`` is one of the two allowed buckets.

* **ER2** PC safety: no ``resolved_entities[*].canonical_slug`` is in the PC
  roster; no ``proposed_new_records[*].slug`` is in the PC roster; no
  ``proposed_aliases[*].target_slug`` is in the PC roster. Mirrors the spirit
  of NC2 (``evals/stage_c_npc_candidates_vertical_slice/grader.py:273-350``)
  but moved one stage downstream.

* **ER3** No false merges (precision): every
  ``resolution=merge_to_registry_slug`` must point at a slug that exists in
  the registry; every ``resolution=merge_to_canonical_new_candidate`` must
  point at a slug that's actually in the input
  ``new_npc_candidates[*].suggested_slug``; gold may declare
  ``must_not_merge[]`` pairs (e.g. ``["cat owl", "grishna"]``) and any
  resolution that maps two declared-different items to the same canonical
  fails.

* **ER4** Recall (within scope): gold may declare
  ``must_merge_clusters[]`` — sets of input items (referenced by their
  Stage C ``suggested_slug`` for new_candidates or by a substring of the
  ``descriptor`` for unresolved_descriptors) that must resolve to one
  canonical_slug; every cluster must collapse. Gold may also declare
  ``must_resolve_unresolved[]`` — substring patterns that must NOT remain in
  ``unresolvable[]``.

* **ER5** Registry / status policy: every ``proposed_new_records[*]`` must
  validate against ``schemas/v0.1/npc_registry.schema.json`` (status MUST be
  ``candidate``, hub_path MUST be null, slug MUST match the regex, sessions
  monotonic); no ``proposed_new_records[*].slug`` may collide with an
  existing registry slug (Stage D is propose-only — never silently overwrite
  curated registry rows).

Telemetry surfaces resolution counts, unresolvable counts, false-merge slugs,
recall-cluster split slugs, and policy-violating proposed_new_records for
triage.
"""

from __future__ import annotations

import re
from typing import Any

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")

_VALID_SOURCE_KINDS = {"unresolved_descriptor", "new_candidate"}
_VALID_RESOLUTIONS = {
    "merge_to_registry_slug",
    "merge_to_canonical_new_candidate",
    "new_net_entity",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _str_or_empty(v: Any) -> str:
    return v if isinstance(v, str) else ""


def _registry_all_slugs(registry: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for rec in registry:
        slug = _str_or_empty(rec.get("slug")).strip().lower()
        if slug:
            out.add(slug)
    return out


def _stage_c_new_candidate_slugs(stage_c_output: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for rec in stage_c_output.get("new_npc_candidates") or []:
        if isinstance(rec, dict):
            slug = _str_or_empty(rec.get("suggested_slug")).strip().lower()
            if slug:
                out.add(slug)
    return out


def _stage_c_bucket_length(stage_c_output: dict[str, Any], bucket_key: str) -> int:
    bucket = stage_c_output.get(bucket_key)
    return len(bucket) if isinstance(bucket, list) else 0


def _pc_slug_set(pc_roster: list[dict[str, Any]] | None) -> set[str]:
    out: set[str] = set()
    for pc in pc_roster or []:
        if isinstance(pc, dict):
            slug = _str_or_empty(pc.get("slug")).strip().lower()
            if slug:
                out.add(slug)
    return out


def _input_descriptor_for(
    stage_c_output: dict[str, Any], source_kind: str, source_index: int
) -> str:
    """Pull the source descriptor string from the Stage C input for diagnostics."""
    if source_kind == "unresolved_descriptor":
        bucket = stage_c_output.get("unresolved_descriptors") or []
    elif source_kind == "new_candidate":
        bucket = stage_c_output.get("new_npc_candidates") or []
    else:
        return ""
    if not isinstance(bucket, list):
        return ""
    if source_index < 0 or source_index >= len(bucket):
        return ""
    rec = bucket[source_index]
    if not isinstance(rec, dict):
        return ""
    return _str_or_empty(rec.get("descriptor"))


# ---------------------------------------------------------------------------
# ER1 — schema validity
# ---------------------------------------------------------------------------


def _grade_er1(
    output: dict[str, Any],
    stage_c_output: dict[str, Any],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []

    if not isinstance(output, dict):
        return "FAIL", ["ER1: output is not a JSON object"], {"output_is_object": False}

    for key in (
        "resolved_entities",
        "proposed_aliases",
        "proposed_new_records",
        "unresolvable",
    ):
        v = output.get(key, None)
        if v is None:
            violations.append(f"ER1: missing top-level array {key!r}")
            continue
        if not isinstance(v, list):
            violations.append(
                f"ER1: top-level {key!r} is not a list (got {type(v).__name__})"
            )

    n_unresolved = _stage_c_bucket_length(stage_c_output, "unresolved_descriptors")
    n_new_cands = _stage_c_bucket_length(stage_c_output, "new_npc_candidates")

    resolved = output.get("resolved_entities") or []
    if isinstance(resolved, list):
        for i, rec in enumerate(resolved):
            if not isinstance(rec, dict):
                violations.append(f"ER1: resolved_entities[{i}] is not an object")
                continue
            sk = rec.get("source_kind")
            if sk not in _VALID_SOURCE_KINDS:
                violations.append(
                    f"ER1: resolved_entities[{i}].source_kind {sk!r} not in "
                    f"{sorted(_VALID_SOURCE_KINDS)}"
                )
            si = rec.get("source_index")
            if not isinstance(si, int) or isinstance(si, bool):
                violations.append(
                    f"ER1: resolved_entities[{i}].source_index missing or not int"
                )
            else:
                bucket_len = (
                    n_unresolved if sk == "unresolved_descriptor" else n_new_cands
                )
                if si < 0 or si >= bucket_len:
                    violations.append(
                        f"ER1: resolved_entities[{i}].source_index={si} out of range "
                        f"[0, {bucket_len}) for source_kind={sk!r} (orphan pointer)"
                    )
            res = rec.get("resolution")
            if res not in _VALID_RESOLUTIONS:
                violations.append(
                    f"ER1: resolved_entities[{i}].resolution {res!r} not in "
                    f"{sorted(_VALID_RESOLUTIONS)}"
                )
            slug = rec.get("canonical_slug")
            if not isinstance(slug, str) or not slug.strip():
                violations.append(
                    f"ER1: resolved_entities[{i}].canonical_slug missing or empty"
                )
            else:
                slug_lc = slug.strip().lower()
                if not _SLUG_RE.match(slug_lc):
                    violations.append(
                        f"ER1: resolved_entities[{i}].canonical_slug {slug!r} "
                        f"fails ^[a-z0-9_]+$"
                    )
            evi = rec.get("evidence_event_indices")
            if not isinstance(evi, list):
                violations.append(
                    f"ER1: resolved_entities[{i}].evidence_event_indices missing/not list"
                )
            rationale = rec.get("rationale")
            if not isinstance(rationale, str):
                violations.append(
                    f"ER1: resolved_entities[{i}].rationale missing/not str"
                )

    proposed_aliases = output.get("proposed_aliases") or []
    if isinstance(proposed_aliases, list):
        for i, rec in enumerate(proposed_aliases):
            if not isinstance(rec, dict):
                violations.append(f"ER1: proposed_aliases[{i}] is not an object")
                continue
            tgt = rec.get("target_slug")
            if not isinstance(tgt, str) or not tgt.strip():
                violations.append(
                    f"ER1: proposed_aliases[{i}].target_slug missing or empty"
                )
            else:
                if not _SLUG_RE.match(tgt.strip().lower()):
                    violations.append(
                        f"ER1: proposed_aliases[{i}].target_slug {tgt!r} fails "
                        f"^[a-z0-9_]+$"
                    )
            txt = rec.get("alias_text")
            if not isinstance(txt, str) or not txt.strip():
                violations.append(
                    f"ER1: proposed_aliases[{i}].alias_text missing or empty"
                )
            src_ids = rec.get("source_descriptor_ids")
            if not isinstance(src_ids, list):
                violations.append(
                    f"ER1: proposed_aliases[{i}].source_descriptor_ids missing/not list"
                )
            rationale = rec.get("rationale")
            if not isinstance(rationale, str):
                violations.append(
                    f"ER1: proposed_aliases[{i}].rationale missing/not str"
                )

    proposed_records = output.get("proposed_new_records") or []
    if isinstance(proposed_records, list):
        for i, rec in enumerate(proposed_records):
            if not isinstance(rec, dict):
                violations.append(f"ER1: proposed_new_records[{i}] is not an object")
                continue
            slug = rec.get("slug")
            if not isinstance(slug, str) or not slug.strip():
                violations.append(
                    f"ER1: proposed_new_records[{i}].slug missing or empty"
                )
            else:
                if not _SLUG_RE.match(slug.strip().lower()):
                    violations.append(
                        f"ER1: proposed_new_records[{i}].slug {slug!r} fails "
                        f"^[a-z0-9_]+$"
                    )

    unresolvable = output.get("unresolvable") or []
    if isinstance(unresolvable, list):
        for i, rec in enumerate(unresolvable):
            if not isinstance(rec, dict):
                violations.append(f"ER1: unresolvable[{i}] is not an object")
                continue
            sk = rec.get("source_kind")
            if sk not in _VALID_SOURCE_KINDS:
                violations.append(
                    f"ER1: unresolvable[{i}].source_kind {sk!r} not in "
                    f"{sorted(_VALID_SOURCE_KINDS)}"
                )
            si = rec.get("source_index")
            if not isinstance(si, int) or isinstance(si, bool):
                violations.append(
                    f"ER1: unresolvable[{i}].source_index missing or not int"
                )
            else:
                bucket_len = (
                    n_unresolved if sk == "unresolved_descriptor" else n_new_cands
                )
                if si < 0 or si >= bucket_len:
                    violations.append(
                        f"ER1: unresolvable[{i}].source_index={si} out of range "
                        f"[0, {bucket_len}) for source_kind={sk!r} (orphan pointer)"
                    )
            descriptor = rec.get("descriptor")
            if not isinstance(descriptor, str) or not descriptor.strip():
                violations.append(
                    f"ER1: unresolvable[{i}].descriptor missing or empty"
                )
            reason = rec.get("reason")
            if not isinstance(reason, str):
                violations.append(f"ER1: unresolvable[{i}].reason missing/not str")

    return ("PASS" if not violations else "FAIL"), violations, {
        "er1_violation_count": len(violations),
    }


# ---------------------------------------------------------------------------
# ER2 — PC safety
# ---------------------------------------------------------------------------


def _grade_er2(
    output: dict[str, Any],
    pc_roster: list[dict[str, Any]],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    pc_slugs = _pc_slug_set(pc_roster)
    pc_leaks: list[dict[str, str]] = []

    resolved = output.get("resolved_entities") or []
    if isinstance(resolved, list):
        for i, rec in enumerate(resolved):
            if not isinstance(rec, dict):
                continue
            slug = _str_or_empty(rec.get("canonical_slug")).strip().lower()
            if slug and slug in pc_slugs:
                violations.append(
                    f"ER2: PC slug {slug!r} appears as resolved_entities[{i}]."
                    f"canonical_slug"
                )
                pc_leaks.append({
                    "bucket": "resolved_entities",
                    "field": "canonical_slug",
                    "value": slug,
                })

    proposed_aliases = output.get("proposed_aliases") or []
    if isinstance(proposed_aliases, list):
        for i, rec in enumerate(proposed_aliases):
            if not isinstance(rec, dict):
                continue
            slug = _str_or_empty(rec.get("target_slug")).strip().lower()
            if slug and slug in pc_slugs:
                violations.append(
                    f"ER2: PC slug {slug!r} appears as proposed_aliases[{i}]."
                    f"target_slug"
                )
                pc_leaks.append({
                    "bucket": "proposed_aliases",
                    "field": "target_slug",
                    "value": slug,
                })

    proposed_records = output.get("proposed_new_records") or []
    if isinstance(proposed_records, list):
        for i, rec in enumerate(proposed_records):
            if not isinstance(rec, dict):
                continue
            slug = _str_or_empty(rec.get("slug")).strip().lower()
            if slug and slug in pc_slugs:
                violations.append(
                    f"ER2: PC slug {slug!r} appears as proposed_new_records[{i}]."
                    f"slug"
                )
                pc_leaks.append({
                    "bucket": "proposed_new_records",
                    "field": "slug",
                    "value": slug,
                })

    return ("PASS" if not violations else "FAIL"), violations, {"pc_leaks": pc_leaks}


# ---------------------------------------------------------------------------
# ER3 — no false merges (precision)
# ---------------------------------------------------------------------------


def _grade_er3(
    output: dict[str, Any],
    stage_c_output: dict[str, Any],
    registry: list[dict[str, Any]],
    must_not_merge: list[list[str]],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    registry_slugs = _registry_all_slugs(registry)
    new_cand_slugs = _stage_c_new_candidate_slugs(stage_c_output)
    bad_targets: list[dict[str, str]] = []

    resolved = output.get("resolved_entities") or []
    if not isinstance(resolved, list):
        resolved = []

    for i, rec in enumerate(resolved):
        if not isinstance(rec, dict):
            continue
        res = _str_or_empty(rec.get("resolution"))
        slug = _str_or_empty(rec.get("canonical_slug")).strip().lower()
        if res == "merge_to_registry_slug":
            if slug not in registry_slugs:
                violations.append(
                    f"ER3: resolved_entities[{i}].canonical_slug {slug!r} resolved as "
                    f"merge_to_registry_slug but is NOT in the registry"
                )
                bad_targets.append({
                    "kind": "merge_to_registry_slug",
                    "canonical_slug": slug,
                    "index": str(i),
                })
        elif res == "merge_to_canonical_new_candidate":
            if slug not in new_cand_slugs:
                violations.append(
                    f"ER3: resolved_entities[{i}].canonical_slug {slug!r} resolved as "
                    f"merge_to_canonical_new_candidate but is NOT in the input "
                    f"new_npc_candidates[*].suggested_slug pool"
                )
                bad_targets.append({
                    "kind": "merge_to_canonical_new_candidate",
                    "canonical_slug": slug,
                    "index": str(i),
                })

    forbidden_pair_violations: list[list[str]] = []
    if must_not_merge:
        descriptor_to_canonical: dict[str, str] = {}
        slug_to_canonical: dict[str, str] = {}
        for rec in resolved:
            if not isinstance(rec, dict):
                continue
            sk = _str_or_empty(rec.get("source_kind"))
            si = rec.get("source_index")
            slug = _str_or_empty(rec.get("canonical_slug")).strip().lower()
            if not slug or not isinstance(si, int) or isinstance(si, bool):
                continue
            descriptor = _input_descriptor_for(stage_c_output, sk, si)
            if descriptor:
                descriptor_to_canonical[descriptor.strip().lower()] = slug
            if sk == "new_candidate":
                bucket = stage_c_output.get("new_npc_candidates") or []
                if isinstance(bucket, list) and 0 <= si < len(bucket):
                    src_rec = bucket[si]
                    if isinstance(src_rec, dict):
                        src_slug = _str_or_empty(src_rec.get("suggested_slug")).strip().lower()
                        if src_slug:
                            slug_to_canonical[src_slug] = slug

        for pair in must_not_merge:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            a, b = pair[0], pair[1]
            if not isinstance(a, str) or not isinstance(b, str):
                continue
            a_lc = a.strip().lower()
            b_lc = b.strip().lower()

            def _resolve(term: str) -> str | None:
                if term in slug_to_canonical:
                    return slug_to_canonical[term]
                for desc_lc, can in descriptor_to_canonical.items():
                    if term in desc_lc:
                        return can
                return None

            ca = _resolve(a_lc)
            cb = _resolve(b_lc)
            if ca and cb and ca == cb:
                violations.append(
                    f"ER3: must_not_merge pair {a!r} ↔ {b!r} both resolved to "
                    f"canonical_slug {ca!r} (forbidden merge)"
                )
                forbidden_pair_violations.append([a, b])

    return ("PASS" if not violations else "FAIL"), violations, {
        "bad_resolution_targets": bad_targets,
        "forbidden_pair_violations": forbidden_pair_violations,
    }


# ---------------------------------------------------------------------------
# ER4 — recall (within scope)
# ---------------------------------------------------------------------------


def _resolved_canonical_for_input(
    output: dict[str, Any],
    stage_c_output: dict[str, Any],
    selector: str,
) -> str | None:
    """Find the canonical_slug a given input item resolved to.

    The selector matches:
      * a Stage C ``new_npc_candidates[*].suggested_slug`` (case-insensitive,
        exact match), OR
      * a substring of an ``unresolved_descriptors[*].descriptor`` /
        ``new_npc_candidates[*].descriptor`` (case-insensitive).
    Returns the canonical_slug if the matching input item appears in
    ``resolved_entities[]``; ``None`` otherwise.
    """
    sel_lc = selector.strip().lower()
    if not sel_lc:
        return None
    resolved = output.get("resolved_entities") or []
    if not isinstance(resolved, list):
        return None
    for rec in resolved:
        if not isinstance(rec, dict):
            continue
        sk = _str_or_empty(rec.get("source_kind"))
        si = rec.get("source_index")
        if not isinstance(si, int) or isinstance(si, bool):
            continue
        slug = _str_or_empty(rec.get("canonical_slug")).strip().lower()
        if not slug:
            continue
        if sk == "new_candidate":
            bucket = stage_c_output.get("new_npc_candidates") or []
            if isinstance(bucket, list) and 0 <= si < len(bucket):
                src_rec = bucket[si]
                if isinstance(src_rec, dict):
                    src_slug = _str_or_empty(src_rec.get("suggested_slug")).strip().lower()
                    if src_slug == sel_lc:
                        return slug
                    desc = _str_or_empty(src_rec.get("descriptor")).strip().lower()
                    if sel_lc in desc:
                        return slug
        elif sk == "unresolved_descriptor":
            bucket = stage_c_output.get("unresolved_descriptors") or []
            if isinstance(bucket, list) and 0 <= si < len(bucket):
                src_rec = bucket[si]
                if isinstance(src_rec, dict):
                    desc = _str_or_empty(src_rec.get("descriptor")).strip().lower()
                    if sel_lc in desc:
                        return slug
    return None


def _grade_er4(
    output: dict[str, Any],
    stage_c_output: dict[str, Any],
    must_merge_clusters: list[list[str]],
    must_resolve_unresolved: list[str],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    cluster_split: list[dict[str, Any]] = []
    still_unresolved_hits: list[str] = []

    for cluster in must_merge_clusters or []:
        if not isinstance(cluster, list) or len(cluster) < 2:
            continue
        members = [m for m in cluster if isinstance(m, str)]
        canonicals: list[str | None] = []
        per_member: list[dict[str, str]] = []
        for member in members:
            can = _resolved_canonical_for_input(output, stage_c_output, member)
            canonicals.append(can)
            per_member.append({"member": member, "canonical": can or "<unresolved>"})
        unique_resolved = {c for c in canonicals if c is not None}
        if any(c is None for c in canonicals):
            violations.append(
                f"ER4: must_merge cluster {members!r} has unresolved member(s) "
                f"(per-member: {per_member}); every cluster member must appear "
                f"in resolved_entities[]"
            )
            cluster_split.append({"cluster": members, "members": per_member})
        elif len(unique_resolved) > 1:
            violations.append(
                f"ER4: must_merge cluster {members!r} split across "
                f"{sorted(unique_resolved)} (expected one canonical_slug)"
            )
            cluster_split.append({"cluster": members, "members": per_member})

    if must_resolve_unresolved:
        unresolvable = output.get("unresolvable") or []
        unresolvable_descriptors_lc: list[str] = []
        if isinstance(unresolvable, list):
            for rec in unresolvable:
                if isinstance(rec, dict):
                    desc = _str_or_empty(rec.get("descriptor")).strip().lower()
                    if desc:
                        unresolvable_descriptors_lc.append(desc)
        for pat in must_resolve_unresolved:
            if not isinstance(pat, str):
                continue
            pat_lc = pat.strip().lower()
            if not pat_lc:
                continue
            hit = next(
                (d for d in unresolvable_descriptors_lc if pat_lc in d), None
            )
            if hit is not None:
                violations.append(
                    f"ER4: must_resolve_unresolved pattern {pat!r} still appears in "
                    f"unresolvable[] descriptor {hit!r}"
                )
                still_unresolved_hits.append(pat)

    return ("PASS" if not violations else "FAIL"), violations, {
        "must_merge_cluster_splits": cluster_split,
        "must_resolve_unresolved_still_unresolved": still_unresolved_hits,
    }


# ---------------------------------------------------------------------------
# ER5 — registry / status policy
# ---------------------------------------------------------------------------


def _grade_er5(
    output: dict[str, Any],
    registry: list[dict[str, Any]],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    registry_slugs = _registry_all_slugs(registry)
    bad_records: list[dict[str, Any]] = []

    proposed_records = output.get("proposed_new_records") or []
    if not isinstance(proposed_records, list):
        return "FAIL", ["ER5: proposed_new_records is not a list"], {"bad_records": []}

    # Lazy import so the grader works in environments without pydantic at
    # import time (the runner pulls it in regardless).
    from src.contracts.npc_registry import NpcRegistryRecord  # noqa: WPS433

    for i, rec in enumerate(proposed_records):
        if not isinstance(rec, dict):
            violations.append(f"ER5: proposed_new_records[{i}] is not an object")
            bad_records.append({"index": i, "reason": "not a dict"})
            continue

        status = rec.get("status")
        if status != "candidate":
            violations.append(
                f"ER5: proposed_new_records[{i}].status must be 'candidate' "
                f"(got {status!r})"
            )
            bad_records.append({"index": i, "reason": f"status={status!r}"})

        hub_path = rec.get("hub_path", "<missing>")
        if hub_path is not None:
            violations.append(
                f"ER5: proposed_new_records[{i}].hub_path must be null for "
                f"candidate records (got {hub_path!r})"
            )
            bad_records.append({"index": i, "reason": f"hub_path={hub_path!r}"})

        slug = _str_or_empty(rec.get("slug")).strip().lower()
        if slug and slug in registry_slugs:
            violations.append(
                f"ER5: proposed_new_records[{i}].slug {slug!r} collides with an "
                f"existing registry slug (Stage D is propose-only — never "
                f"silently overwrite)"
            )
            bad_records.append({"index": i, "reason": f"slug_collision={slug!r}"})

        try:
            NpcRegistryRecord.model_validate(rec)
        except Exception as exc:
            violations.append(
                f"ER5: proposed_new_records[{i}] fails NpcRegistryRecord schema: {exc}"
            )
            bad_records.append({"index": i, "reason": f"schema={exc!s}"})

    return ("PASS" if not violations else "FAIL"), violations, {
        "bad_records": bad_records,
    }


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def grade_stage_d(
    stage_d_output: dict[str, Any],
    gold: dict[str, Any],
    stage_c_output: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grade a Stage D output against gold + Stage C input + events + registry.

    Returns a dict with keys: ``gates_passed``, ``per_gate_verdict``,
    ``violations``, ``violation_counts``, ``telemetry``.
    """
    grading = gold.get("grading") or {}
    pc_roster = (gold.get("input") or {}).get("pc_roster") or []
    must_not_merge = list(grading.get("must_not_merge") or [])
    must_merge_clusters = list(grading.get("must_merge_clusters") or [])
    must_resolve_unresolved = list(grading.get("must_resolve_unresolved") or [])

    er1_v, er1_violations, er1_tel = _grade_er1(stage_d_output, stage_c_output)
    er2_v, er2_violations, er2_tel = _grade_er2(stage_d_output, pc_roster)
    er3_v, er3_violations, er3_tel = _grade_er3(
        stage_d_output, stage_c_output, registry, must_not_merge
    )
    er4_v, er4_violations, er4_tel = _grade_er4(
        stage_d_output, stage_c_output, must_merge_clusters, must_resolve_unresolved
    )
    er5_v, er5_violations, er5_tel = _grade_er5(stage_d_output, registry)

    per_gate_verdict = {
        "ER1": er1_v,
        "ER2": er2_v,
        "ER3": er3_v,
        "ER4": er4_v,
        "ER5": er5_v,
    }
    all_violations = (
        er1_violations + er2_violations + er3_violations + er4_violations + er5_violations
    )
    violation_counts = {
        "ER1": len(er1_violations),
        "ER2": len(er2_violations),
        "ER3": len(er3_violations),
        "ER4": len(er4_violations),
        "ER5": len(er5_violations),
    }
    gates_passed_n = sum(1 for v in per_gate_verdict.values() if v == "PASS")
    gates_passed_str = f"{gates_passed_n}/5"

    resolved = stage_d_output.get("resolved_entities") or []
    proposed_aliases = stage_d_output.get("proposed_aliases") or []
    proposed_records = stage_d_output.get("proposed_new_records") or []
    unresolvable = stage_d_output.get("unresolvable") or []

    resolution_counts = {
        "merge_to_registry_slug": 0,
        "merge_to_canonical_new_candidate": 0,
        "new_net_entity": 0,
    }
    if isinstance(resolved, list):
        for rec in resolved:
            if isinstance(rec, dict):
                res = _str_or_empty(rec.get("resolution"))
                if res in resolution_counts:
                    resolution_counts[res] += 1

    telemetry: dict[str, Any] = {
        "resolved_count": len(resolved) if isinstance(resolved, list) else 0,
        "proposed_aliases_count": (
            len(proposed_aliases) if isinstance(proposed_aliases, list) else 0
        ),
        "proposed_new_records_count": (
            len(proposed_records) if isinstance(proposed_records, list) else 0
        ),
        "unresolvable_count": (
            len(unresolvable) if isinstance(unresolvable, list) else 0
        ),
        "resolution_counts": resolution_counts,
        "pc_leaks": er2_tel.get("pc_leaks", []),
        "bad_resolution_targets": er3_tel.get("bad_resolution_targets", []),
        "forbidden_pair_violations": er3_tel.get("forbidden_pair_violations", []),
        "must_merge_cluster_splits": er4_tel.get("must_merge_cluster_splits", []),
        "must_resolve_unresolved_still_unresolved": er4_tel.get(
            "must_resolve_unresolved_still_unresolved", []
        ),
        "bad_records": er5_tel.get("bad_records", []),
    }

    return {
        "gates_passed": gates_passed_str,
        "all_gates_passed": gates_passed_n == 5,
        "per_gate_verdict": per_gate_verdict,
        "violations": all_violations,
        "violation_counts": violation_counts,
        "telemetry": telemetry,
    }


__all__ = [
    "grade_stage_d",
    "_grade_er1",
    "_grade_er2",
    "_grade_er3",
    "_grade_er4",
    "_grade_er5",
    "_resolved_canonical_for_input",
    "_input_descriptor_for",
    "_registry_all_slugs",
    "_stage_c_new_candidate_slugs",
    "_pc_slug_set",
]
