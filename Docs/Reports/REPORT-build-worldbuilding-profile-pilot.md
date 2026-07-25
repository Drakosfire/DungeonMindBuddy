# REPORT — Build worldbuilding profile pilot (BLD-08)

- **Date:** 2026-07-25
- **Profile:** `worldbuilding_shepherds_flock_v0@0.1`
- **Cohort mode:** fixture-backed deterministic pass client (no live corpus/model payloads in report)
- **Decision scope:** deterministic contract/plumbing proof only

## Decision

**GO for deterministic contract/plumbing proof only.**

This admits the bounded Shepherd's Flock worldbuilding profile into the
production profile registry on the strength of:

```text
Build launch (exact profile ID/version)
→ profile lookup
→ source adaptation
→ pass orchestration (profile-owned edge prompt; no recap session sweep)
→ evidence materialization
→ same-run consolidation gated by profile (no automatic identity merges)
→ ExtractionRun persistence
→ profile-owned post-extraction validation (fail-closed on exceptions)
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

Stable redacted identifiers from cohort `wb-cohort-20260725T152758Z`:

- Fixture metadata id (not runtime): `artifact:worldbuilding:fixture:shepherds-flock:r1`
- Profile: `worldbuilding_shepherds_flock_v0@0.1`
- Trial / run / registered SourceArtifact IDs:
  - `wb-cohort-20260725T152758Z-trial-1` → run `9edfa215-2a16-4bc1-99a2-02e5a1fcf701` → `artifact:worldbuilding:f2bdf690-180f-4f0c-a415-c69bcef55720:r2:0efeac48618e`
  - `wb-cohort-20260725T152758Z-trial-2` → run `3edc7cb5-2c04-46aa-bb73-352dad458cd2` → `artifact:worldbuilding:e150435a-fdb9-40e4-8e54-9180cc9e7cd3:r2:0efeac48618e`
  - `wb-cohort-20260725T152758Z-trial-3` → run `43366bc9-0545-476c-baf8-cd690d98c5c7` → `artifact:worldbuilding:95435088-3932-4e7f-a238-592f12d652cc:r2:0efeac48618e`
- Local manifests under `out/evals/worldbuilding_profile_pilot/` (not promoted gold)

## Manual judgment notes

- Included categories exercised in the fixture: named NPC, faction/collective,
  named location, durable command relationship (`predicate_family` required).
- Institutions/governance are represented as `faction` / `organization` /
  `group`. A distinct `institution` node type is **not** admitted — production
  IR vocabulary does not include it.
- Excluded categories (`item`, incidental flora metadata) are enforced by the
  production runtime via `post_extraction_validator` (pipeline + Build launch
  route negatives), not merely by calling the standalone validator after a
  reviewable result.
- Rendered worldbuilding edge prompt omits session-sized / refugee / siege /
  evacuation recap sweep guidance; strict edge schema still requires
  `predicate_family`.
- Same-run automatic identity consolidation is disabled for this profile;
  ambiguous cross-class label collisions remain separate candidates.
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
- Authority elevation / publication path for `worldbuilding_draft` (separate
  architecture decision; not BLD-08).
