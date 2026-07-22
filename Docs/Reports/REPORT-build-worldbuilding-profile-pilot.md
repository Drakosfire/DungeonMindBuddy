# REPORT — Build worldbuilding profile pilot (BLD-08)

- **Date:** 2026-07-22
- **Profile:** `worldbuilding_shepherds_flock_v0@0.1`
- **Cohort mode:** fixture-backed deterministic pass client (no live corpus/model payloads in report)

## Decision

**GO** for admitting the bounded Shepherd's Flock worldbuilding profile into the
production profile registry, subject to Graph Review confirmation for all
candidates (no automatic promotion).

## Aggregate metrics

| Metric | Value |
|---|---:|
| Trials requested | 3 |
| Trials completed | 3 |
| Passed (reviewable + bounds) | 3 |
| Failed (refusal/incomplete/schema/validation) | 0 |
| Auto-promotion events | 0 |

Exact trial/run IDs are local under `out/evals/worldbuilding_profile_pilot/` and
are not copied here.

## Manual judgment notes

- Included categories exercised: named NPC, faction/collective, named location,
  durable command relationship.
- Excluded categories remain omit-policy (incidental flora/items) and are
  validated by profile unit tests.
- Session scope remained null on every successful candidate graph.
- Every positive candidate retained source span evidence refs.

## Redaction inspection

- Report contains no source prose excerpts.
- Report contains no model request/response payloads.
- Fixture text is a minimal redacted contract string, not canon/gold.

## Follow-ups

- BLD-09 PDF/OCR lineage pilot.
- Broader ecology/resource profiles remain deferred.
