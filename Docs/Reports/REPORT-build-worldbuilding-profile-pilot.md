# REPORT — Build worldbuilding profile pilot (BLD-08)

- **Date:** 2026-07-24
- **Profile:** `worldbuilding_shepherds_flock_v0@0.1`
- **Cohort mode:** fixture-backed deterministic pass client (no live corpus/model payloads in report)
- **Decision scope:** deterministic contract/plumbing proof only

## Decision

**GO for deterministic contract/plumbing proof only.**

This admits the bounded Shepherd's Flock worldbuilding profile into the
production profile registry on the strength of:

```text
profile lookup
→ source adaptation
→ pass orchestration
→ evidence materialization
→ ExtractionRun persistence
→ profile-owned post-extraction validation
→ generic reviewable transition (when bounds hold)
```

It does **not** prove extraction quality, prompt/category precision, robustness
across prose, model variability, or a small real-source cohort. Three
deterministic fixture replays are plumbing repeats, not independent
extraction-quality trials.

Candidates remain inspect-only under BLD-07 (`promotable=false`; prepare
rejected). There is no Graph Review publication path for
`worldbuilding_draft`.

## Aggregate metrics

| Metric | Value |
|---|---:|
| Trials requested | 3 |
| Trials completed | 3 |
| Passed (reviewable + runtime bounds) | 3 |
| Failed (refusal/incomplete/schema/validation) | 0 |
| Auto-promotion events | 0 |
| Live model / real-source trials | 0 |

Stable redacted identifiers from cohort `wb-cohort-20260725T045109Z`:

- Fixture source artifact id (fixture metadata): `artifact:worldbuilding:fixture:shepherds-flock:r1`
- Profile: `worldbuilding_shepherds_flock_v0@0.1`
- Trial/run IDs:
  - `wb-cohort-20260725T045109Z-trial-1` → `a9ce4262-c977-4c10-a6ee-cea722f7c673`
  - `wb-cohort-20260725T045109Z-trial-2` → `ce4a9169-19aa-4754-90bb-5226926a91f2`
  - `wb-cohort-20260725T045109Z-trial-3` → `6bc873ad-7d74-44d9-9dc1-416c1bf6aa3f`
- Local manifests under `out/evals/worldbuilding_profile_pilot/` (not promoted gold)

## Manual judgment notes

- Included categories exercised in the fixture: named NPC, faction/collective,
  named location, durable command relationship.
- Institutions/governance are represented as `faction` / `organization` /
  `group`. A distinct `institution` node type is **not** admitted — production
  IR vocabulary does not include it.
- Excluded categories (`item`, incidental flora metadata) are enforced by the
  production runtime via `post_extraction_validator` (pipeline negative tests),
  not merely by calling the standalone validator after a reviewable result.
- Session scope remained null on every successful candidate graph.
- Every positive fixture candidate retained source span evidence refs.
- Graph Review inspect-only dogfood of a BLD-08 trial: **not performed**.

## Redaction inspection

- Report contains no source prose excerpts.
- Report contains no model request/response payloads.
- Fixture text is a minimal redacted contract string, not canon/gold.

## Follow-ups

- Real Shepherd's Flock SourceArtifact / model-policy cohort if a broader pilot
  quality claim is needed.
- Inspect-only Graph Review exercise for one exact worldbuilding run.
- BLD-09 PDF/OCR lineage pilot.
- Broader ecology/resource profiles remain deferred.
- Authority elevation for `worldbuilding_draft` remains a separate architecture
  decision (not BLD-08).
