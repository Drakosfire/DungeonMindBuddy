# INGEST: editable drafts per source session

Status: ACTIVE. User-authorized dogfood fix; the broader ingestion goal stays paused.
Base: 04d9d6793e197f50069b5b77ea89b3db3d26c9af.
Lane: codex/ingest-draft-navigation. Topology: parallel-independent of PR2079 backend and PR2080 native picker; no overlapping writes. No merge authority.

Outcome: switching source sessions preserves each draft while leaving the destination editable; clearing a draft cannot resurrect legacy text.
Write lease: this handoff and apps/live-control-ui/src/modules/IngestionModule.tsx, IngestionModule.test.tsx, IngestionModule.savedRuns.test.tsx.
Validation: component navigation, clearing, legacy restoration and late response tests; UI typecheck and cumulative diff review.
Failure cases: never move text implicitly across sessions, overwrite a legacy recovery record, or accept stale Process results. Existing scoped empty records override legacy content.
Resources: mocked component tests only. No live port5202 interaction, providers, publication, primary writes or database effects. Existing browser drafts remain untouched.

Re-anchor: origin/main e151ee4cae05a8eaca4a777d6df5843cd34abba5 contains merged PR2080, whose five picker files remain disjoint from this lease.
Validation: 37 module/saved-reader tests and 22 page integration tests pass; tsc -b and git diff --check pass. Existing React act warnings in async response tests remain visible in /tmp/draft-navigation-tests.log. No live browser storage was accessed.
