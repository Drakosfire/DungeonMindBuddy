# PLAN: reuse the fidelity-validated import

Status: DELIVERED. Historical contract follows. PRIME authorizes one serial measured optimization under the existing authoring-to-play goal. Base1d853915c869f5b18afb68fa7e3457cdbd980928; branch codex/plan-validated-import-reuse; reuse buddy-context-loop checkout. PRIME owns implementation/integration/5202; independent exact-head review required. No other open PR in the current inventory leases these Plan paths. No new checkout, environment, provider call or campaign content write.

## Evidence and invariant critique

The operator-supplied frontend report's assessment identifies repeated full Markdown import on accepted Plan typing: onUpdate imports next for fidelity, then render's useMemo imports the identical next again. Current source confirms it. Historical 983/4903/14703-word browser fixtures report typing latency and one profile attributes65% non-idle time to Markdown parsing; those historical timings are diagnostic, not current baseline or promised gain.

Reuse only the exact fidelity-validated source/import pair. Store source and optional validated import atomically in immutable React state, scoped to current World/document-or-local-draft/editor generation. Render is pure and never consumes a mutable ref cache; StrictMode double render must remain repeatable. Ordinary source replacement/load/recovery clears the optional import and uses the existing importer. Existing selection epoch/current editor fences must reject retired callbacks before accepting a pair. Source and parse cannot be updated independently. Fidelity rejection leaves source/recovery untouched and remounts the safe projection. No grammar, serializer, editor-core, persistence, CAS, agent or media contract changes.

## Exclusive write lease and settlement

Only apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx and PlanSurfacePage.test.tsx; this handoff; Docs/Plans/HANDOFF-DEMO-world-plan-save-fidelity-guard.md and HANDOFF-world-plan-playable-adoption.md for explicit release of overlapping old Plan page/test leases; Docs/Plans/HANDOFF-PLAY-session-edit-proposals.md for truthful delivered1440/1441 acceptance settlement. PRIME transfers only those old overlapping paths here based on confirmed merged904(fb1c48d622c9d8d404b1dddb5d5f618e03cc7ef0) and931(27337116bbbbe039fac1387f1a9135edac22ddf9). Historical contracts remain reference; do not claim unrelated work complete.

## Verification and delivery

Use mounted real editor in StrictMode with983/4903/14703-word fixtures and20 consecutive edits after warmup. Count imports for each exact exported source before/after; require removal of the redundant render import while preserving validation. Timing from synthetic DOM is only diagnostic, not browser event latency or sixfold CPU reproduction. Verify fidelity rejection/rollback, document/World switch, stale callbacks, recovery, source-mode replacement and latest autosaved revision at owning mounted boundary; compare inherited failures by exact test names. Inspect cumulative diff, typecheck/build, independent review, commit/push/PR/merge and guarded normal5202 adoption. Browser proof edits only a disposable Plan, verifies source/reopen and originating Play remains pinned/unchanged. No paid provider test required. Keep source/recovery fidelity ahead of performance.


## Pre-review evidence

Mounted StrictMode before/after count:60 ->20 full imports for20 accepted edits in each983/4903/14703 body-word fixture (one warmup edit excluded). Eleven focused checks pass, including new fidelity rejection/rollback and retired callback/identity tests plus existing source-mode recovery, World/document fences and autosave. Broader Plan/reviewed-edit baseline35 passed/67 failed (three new intentional count failures); optimized38 passed/64 failed with no newly failing names. The64 inherited tests are not claimed green. Production TypeScript/Vite build passes, existing bundle warning only. Private evidence plan-parse-reuse-measurement.json and owning/focused logs in established JEV location. Browser latency gain not measured. Independent review/merge and normal5202 acceptance remain pending.


## Delivered settlement — 2026-10-19

PR1442 merged8032438596e0c1bc669aca47292b0b3f3b6383e8 after independent exact-head PASS. Normal5202 visual typing/autosave/reopen and Document/Markdown media+callout/marker continuity passed; disposable Plan restored exact Markdown at revision19; both Play sessions, Edge, notes/progress unchanged. Private plan-parse-reuse-acceptance.json and ui-rollout evidence recorded. Parse-count measurement60->20/20 edits under StrictMode remains the measured claim; browser latency gain not measured. Exclusive Plan page/test lease released to serial HANDOFF-MEDIA-plan-play-authoring.md.
