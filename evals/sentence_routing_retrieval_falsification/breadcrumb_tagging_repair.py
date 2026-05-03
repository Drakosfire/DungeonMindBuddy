"""Deterministic candidate finder + narrow JSON repair prompt (Variant C prototype).

When a first-pass breadcrumb artifact misses a *backward-anaphora* style tag — for
example ``u-L0019-04`` ("Caelynn approaches the makeshift shelter and hears mumbling
from inside.") which is durably about Lysandra (named in the next sentence) — the
forward-only ``UNDER-TAGGED CONTINUATION CHECK`` in
``breadcrumb_prompt.PROMPT_VARIANT_CONTINUATION`` cannot help.

This module implements the deterministic step of a "candidate finder + narrow LLM
repair" pipeline:

1. ``find_repair_candidates`` walks the normalized records, computes per-paragraph
   buckets, and flags units that:
   * lack an ``NPC`` or ``PC`` (subject) route, AND
   * sit in a paragraph where one or more ``NPC`` / ``PC`` subject routes appear
     within a small window (default ±1 unit), AND
   * either carry a durable object/location signal (``Location`` or
     ``NewHubCandidate`` route) OR contain a pronoun/object cue tied to that
     subject.

2. ``build_repair_prompt`` composes a tight JSON-only adjudication prompt asking
   an LLM to add subject routes ONLY to the flagged candidates (no edits to text,
   no deletions, no new units). The prompt is deliberately minimal so the
   adjudicator can be a cheap model.

3. ``apply_repair_patches`` merges accepted patches back into the in-memory
   ``NormalizedRecord`` list, deduping by ``(subject_class, normalized_route)``.

The runtime never calls the LLM here. The purpose is a verifiable, testable
surface that future runners can plug into. Cost stays $0 unless a downstream
caller decides to send the prompt to a model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    NormalizedRecord,
    RouteAttachment,
)

SUBJECT_CLASSES = {"NPC", "PC"}

PRONOUN_CUES = (
    " she ",
    " her ",
    " he ",
    " him ",
    " they ",
    " them ",
    " their ",
)

OBJECT_CUES = (
    "the drawing",
    "the blueprint",
    "the antidote",
    "the spell",
    "the camp",
    "the storm",
    "the shelter",
    "the wagon",
    "the tea",
    "the meat",
    "her bag",
    "his bag",
    "the line",
)


@dataclass(frozen=True)
class RepairCandidate:
    unit_id: str
    line_start: int
    text: str
    current_routes: tuple[str, ...]
    nearby_subject_routes: tuple[str, ...]
    cues: tuple[str, ...]
    paragraph_index: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "line_start": self.line_start,
            "text": self.text,
            "current_routes": list(self.current_routes),
            "nearby_subject_routes": list(self.nearby_subject_routes),
            "cues": list(self.cues),
            "paragraph_index": self.paragraph_index,
        }


@dataclass(frozen=True)
class RepairPatch:
    unit_id: str
    add_routes: tuple[tuple[str, str], ...]  # (subject_class, normalized_route) pairs
    reason: str = ""


@dataclass
class RepairApplyReport:
    applied_patches: list[RepairPatch] = field(default_factory=list)
    rejected_patches: list[dict[str, Any]] = field(default_factory=list)
    routes_added: int = 0
    units_touched: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "applied_patches": [
                {
                    "unit_id": p.unit_id,
                    "add_routes": [
                        {"subject_class": sc, "normalized_route": nr}
                        for sc, nr in p.add_routes
                    ],
                    "reason": p.reason,
                }
                for p in self.applied_patches
            ],
            "rejected_patches": list(self.rejected_patches),
            "routes_added": self.routes_added,
            "units_touched": list(self.units_touched),
        }


def _has_subject_route(record: NormalizedRecord) -> bool:
    return any(att.subject_class in SUBJECT_CLASSES for att in record.routes)


def _has_durable_object_route(record: NormalizedRecord) -> bool:
    return any(att.subject_class in {"Location", "NewHubCandidate"} for att in record.routes)


def _detect_cues(text: str) -> list[str]:
    body = " " + text.lower() + " "
    cues: list[str] = []
    for cue in PRONOUN_CUES:
        if cue in body:
            cues.append(cue.strip())
    for cue in OBJECT_CUES:
        if cue in body.replace("  ", " "):
            cues.append(cue)
    return cues


def _paragraph_index(records: list[NormalizedRecord]) -> dict[str, int]:
    """Group records by ``line_start``-clustered paragraphs.

    The breadcrumb / recap pipeline puts each paragraph on its own (recap-body)
    line range, so a stable proxy for paragraph membership is to bucket by
    ``line_start``: consecutive records sharing or differing by less than 2 lines
    are treated as one paragraph. This mirrors the behavior of the manual
    baseline used in tests.
    """
    if not records:
        return {}
    out: dict[str, int] = {}
    last_line = -10
    paragraph = -1
    for rec in records:
        if rec.line_start - last_line > 1:
            paragraph += 1
        out[rec.unit_id] = paragraph
        last_line = rec.line_start
    return out


def find_repair_candidates(
    records: list[NormalizedRecord],
    *,
    window: int = 1,
) -> list[RepairCandidate]:
    """Flag units missing a *neighbor* subject route despite paragraph context.

    A candidate is emitted when ALL of:

    * within ``window`` units (forward AND backward) in the same paragraph, at
      least one record has a ``PC``/``NPC`` route THAT THIS UNIT DOES NOT
      ALREADY HAVE,
    * the unit carries a durable object/location route OR contains a pronoun /
      object cue (``the drawing``, ``the blueprint``, etc.).

    The finder intentionally does not require the unit to have *no* subject
    route — a sentence may already carry one PC (e.g. Caelynn observing) and
    still be missing the subject the scene is about (e.g. Lysandra).

    ``nearby_subject_routes`` lists ONLY routes that are missing from the
    candidate, so downstream callers know exactly which routes are eligible to
    be added.
    """
    if not records:
        return []

    paragraphs = _paragraph_index(records)
    by_index = list(records)
    candidates: list[RepairCandidate] = []
    for i, rec in enumerate(by_index):
        cues = _detect_cues(rec.lexical_plain)
        durable_object = _has_durable_object_route(rec)
        if not cues and not durable_object:
            continue

        own_routes = {att.normalized_route for att in rec.routes}
        para_id = paragraphs.get(rec.unit_id, -1)
        nearby_subjects: list[str] = []
        for offset in range(-window, window + 1):
            if offset == 0:
                continue
            j = i + offset
            if j < 0 or j >= len(by_index):
                continue
            neighbor = by_index[j]
            if paragraphs.get(neighbor.unit_id, -2) != para_id:
                continue
            for att in neighbor.routes:
                if att.subject_class in SUBJECT_CLASSES and att.normalized_route not in own_routes:
                    nearby_subjects.append(att.normalized_route)
        if not nearby_subjects:
            continue

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_subjects: list[str] = []
        for r in nearby_subjects:
            if r not in seen:
                seen.add(r)
                unique_subjects.append(r)

        candidates.append(
            RepairCandidate(
                unit_id=rec.unit_id,
                line_start=rec.line_start,
                text=rec.lexical_plain,
                current_routes=tuple(att.normalized_route for att in rec.routes),
                nearby_subject_routes=tuple(unique_subjects),
                cues=tuple(cues),
                paragraph_index=para_id,
            )
        )
    return candidates


REPAIR_PROMPT_INSTRUCTIONS = """\
You are a repair adjudicator for an inline-recap breadcrumb pipeline.

The first pass produced normalized session-memory records. Some units lack a
subject (``PC`` / ``NPC``) route even though the surrounding paragraph clearly
attaches them to a specific named PC or NPC (for example, "Caelynn approaches
the makeshift shelter and hears mumbling from inside" is durably about
Lysandra because Lysandra is who is inside).

Your job is to add **only missing subject routes** to flagged candidate units.

Hard rules:
* Do NOT delete any route.
* Do NOT modify the recap text.
* Do NOT invent new routes — every route you add MUST appear in the
  ``allowed_subject_routes`` list of the candidate.
* If a candidate is genuinely about a different subject than the nearby
  routes (for example, the pronoun "she" refers to a different PC), return an
  empty ``add_routes`` array for that unit.
* If a candidate has no clear subject, return an empty ``add_routes`` array.

Return ONLY a JSON object matching this shape:

```json
{
  "patches": [
    {
      "unit_id": "u-LNNNN-NN",
      "add_routes": [
        {"subject_class": "NPC", "normalized_route": "..."}
      ],
      "reason": "<short string>"
    }
  ]
}
```
"""


def build_repair_prompt(
    *,
    recap_body: str,
    candidates: list[RepairCandidate],
) -> tuple[str, str]:
    """Return ``(system, user)`` for a narrow JSON repair adjudication call."""
    candidates_payload = {
        "candidates": [
            {
                "unit_id": c.unit_id,
                "line_start": c.line_start,
                "text": c.text,
                "current_routes": list(c.current_routes),
                "allowed_subject_routes": list(c.nearby_subject_routes),
                "cues": list(c.cues),
            }
            for c in candidates
        ]
    }
    user = (
        "Recap body (canonical text — for reference only, do not modify):\n\n"
        "```recap\n"
        f"{recap_body.strip()}\n"
        "```\n\n"
        "Flagged candidate units (each may receive zero or more `add_routes`):\n\n"
        "```json\n"
        f"{json.dumps(candidates_payload, indent=2, ensure_ascii=False)}\n"
        "```\n\n"
        "Return ONLY the JSON object described in the instructions.\n"
    )
    return REPAIR_PROMPT_INSTRUCTIONS, user


_PATCH_RE = re.compile(r"\{[\s\S]+\}")


def parse_repair_response(text: str) -> list[RepairPatch]:
    """Parse the model's JSON repair response into ``RepairPatch`` objects.

    Tolerant of surrounding fences / prose: extracts the largest balanced JSON
    object, raises a clear error if patches are malformed.
    """
    if not text:
        return []
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`").lstrip("json").strip()
    match = _PATCH_RE.search(candidate)
    if match:
        candidate = match.group(0)
    data = json.loads(candidate)
    patches_raw = data.get("patches") or []
    out: list[RepairPatch] = []
    for entry in patches_raw:
        unit_id = str(entry.get("unit_id", "")).strip()
        if not unit_id:
            continue
        add_routes = entry.get("add_routes") or []
        pairs: list[tuple[str, str]] = []
        for r in add_routes:
            sc = str(r.get("subject_class", "")).strip()
            nr = str(r.get("normalized_route", "")).strip()
            if sc and nr:
                pairs.append((sc, nr))
        out.append(
            RepairPatch(
                unit_id=unit_id,
                add_routes=tuple(pairs),
                reason=str(entry.get("reason", "")),
            )
        )
    return out


def apply_repair_patches(
    records: list[NormalizedRecord],
    patches: Iterable[RepairPatch],
    *,
    candidate_unit_ids: set[str] | None = None,
    allowed_routes_by_unit: dict[str, set[str]] | None = None,
) -> RepairApplyReport:
    """Merge ``patches`` into ``records`` in place; return an audit report.

    Patches are rejected (recorded but not applied) when:

    * ``candidate_unit_ids`` is provided and the patch's unit is not in it
      (prevents the LLM from drifting into unflagged units),
    * the unit_id is missing from records,
    * the route is not in ``allowed_routes_by_unit[unit_id]`` when supplied
      (prevents the LLM from inventing routes outside the candidate's
      ``allowed_subject_routes``),
    * the route is already present (silent dedup, not recorded as rejected).
    """
    by_unit = {r.unit_id: r for r in records}
    report = RepairApplyReport()
    for patch in patches:
        if candidate_unit_ids is not None and patch.unit_id not in candidate_unit_ids:
            report.rejected_patches.append(
                {
                    "unit_id": patch.unit_id,
                    "reason": "unit not in candidate set",
                }
            )
            continue
        record = by_unit.get(patch.unit_id)
        if record is None:
            report.rejected_patches.append(
                {"unit_id": patch.unit_id, "reason": "unknown unit_id"}
            )
            continue
        existing = {(att.subject_class, att.normalized_route) for att in record.routes}
        added_here = 0
        applied_pairs: list[tuple[str, str]] = []
        for subject_class, normalized_route in patch.add_routes:
            if (subject_class, normalized_route) in existing:
                continue
            if (
                allowed_routes_by_unit is not None
                and normalized_route not in allowed_routes_by_unit.get(patch.unit_id, set())
            ):
                report.rejected_patches.append(
                    {
                        "unit_id": patch.unit_id,
                        "subject_class": subject_class,
                        "normalized_route": normalized_route,
                        "reason": "route not in candidate allowed list",
                    }
                )
                continue
            record.routes.append(
                RouteAttachment(
                    subject_class=subject_class,
                    normalized_route=normalized_route,
                    proposed=False,
                    tag_kind="repair",
                )
            )
            existing.add((subject_class, normalized_route))
            added_here += 1
            applied_pairs.append((subject_class, normalized_route))
        if added_here:
            report.applied_patches.append(
                RepairPatch(
                    unit_id=patch.unit_id,
                    add_routes=tuple(applied_pairs),
                    reason=patch.reason,
                )
            )
            report.routes_added += added_here
            if patch.unit_id not in report.units_touched:
                report.units_touched.append(patch.unit_id)
    return report


def candidates_to_jsonable(candidates: list[RepairCandidate]) -> list[dict[str, Any]]:
    return [c.to_json_dict() for c in candidates]


def render_candidates_markdown(
    *,
    artifact_path: str,
    candidates: list[RepairCandidate],
    paragraph_filter: str | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# Breadcrumb Tagging Repair Candidates")
    lines.append("")
    lines.append(f"- artifact: `{artifact_path}`")
    if paragraph_filter:
        lines.append(f"- paragraph filter: `{paragraph_filter}`")
    lines.append(f"- candidates: {len(candidates)}")
    lines.append("")
    lines.append("| unit_id | line | text | missing-nearby-subjects | cues |")
    lines.append("| --- | ---: | --- | --- | --- |")
    for c in candidates:
        if paragraph_filter and not c.unit_id.startswith(paragraph_filter):
            continue
        text = c.text.replace("|", "\\|")
        missing = ", ".join(f"`{r}`" for r in c.nearby_subject_routes) or "—"
        cues = ", ".join(f"`{x.strip()}`" for x in c.cues) or "—"
        lines.append(f"| `{c.unit_id}` | {c.line_start} | {text} | {missing} | {cues} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """CLI: dump candidate list (and optional repair prompt) for an artifact."""
    import argparse
    from datetime import datetime, timezone
    from pathlib import Path as _Path

    from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (  # noqa: F401
        normalize_breadcrumb_artifact,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=_Path, required=True)
    parser.add_argument("--corpus-root", type=_Path, default=_Path("corpus/eldyrwild-markdown"))
    parser.add_argument(
        "--paragraph-filter",
        type=str,
        default=None,
        help="Filter candidates to unit_id prefix (e.g. 'u-L0019-')",
    )
    parser.add_argument("--out-json", type=_Path, default=None)
    parser.add_argument("--out-md", type=_Path, default=None)
    parser.add_argument("--emit-prompt", action="store_true",
                        help="Also write the narrow JSON repair prompt to <out-md>.prompt.md")
    args = parser.parse_args()

    text = args.artifact.read_text(encoding="utf-8")
    records, _ = normalize_breadcrumb_artifact(
        artifact_text=text, corpus_root=args.corpus_root.resolve()
    )
    candidates = find_repair_candidates(records)

    out_json = args.out_json
    out_md = args.out_md
    if out_json is None or out_md is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        runs_root = (
            _Path(".")
            / "evals/sentence_routing_retrieval_falsification/artifacts/runs"
            / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        runs_root.mkdir(parents=True, exist_ok=True)
        out_json = out_json or runs_root / f"breadcrumb_tagging_repair_candidates--{stamp}.json"
        out_md = out_md or runs_root / f"breadcrumb_tagging_repair_candidates--{stamp}.md"

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            {
                "schema": "dmb_breadcrumb_tagging_repair_candidates_v1",
                "artifact_path": str(args.artifact),
                "candidates": candidates_to_jsonable(candidates),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out_md.write_text(
        render_candidates_markdown(
            artifact_path=str(args.artifact),
            candidates=candidates,
            paragraph_filter=args.paragraph_filter,
        ),
        encoding="utf-8",
    )

    if args.emit_prompt:
        from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
            parse_frontmatter_and_body,
        )
        # Recap body from artifact source path
        recap_body = ""
        for r in records:
            recap_path = args.corpus_root / r.source_recap_path
            if recap_path.is_file():
                _fm, recap_body = parse_frontmatter_and_body(
                    recap_path.read_text(encoding="utf-8")
                )
                break
        system, user = build_repair_prompt(recap_body=recap_body, candidates=candidates)
        prompt_path = out_md.with_suffix(".prompt.md")
        prompt_path.write_text(
            f"# Repair adjudication prompt\n\n## SYSTEM\n\n{system}\n\n## USER\n\n{user}\n",
            encoding="utf-8",
        )
        print(str(prompt_path))

    print(str(out_json))
    print(str(out_md))
    print(json.dumps({"candidates": len(candidates)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
