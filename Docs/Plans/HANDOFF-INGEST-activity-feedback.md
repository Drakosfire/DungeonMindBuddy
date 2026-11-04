# INGEST: request activity feedback

Status: ACTIVE, authorized by the user’s dogfood request for more than Processing.
Topology: stacked on PR2081, exact parent a4beec6db. Merge/rebase order: PR2081 then this slice. Branch codex/ingest-activity-feedback in the ingest-draft-navigation checkout. Remote main e151ee4ca re-anchored; open PR2079 backend and PR2078 design are disjoint.

Outcome: show useful, truthful waiting text and elapsed time during the ordinary ingestion request. Current API returns one completed JSON result; intermediate nodes, backend stage events and model reasoning are unavailable. Do not imply inferred progress or publication.
Write lease: this handoff; apps/live-control-ui/src/modules/IngestionActivity.tsx, IngestionActivity.css, IngestionActivity.test.tsx, IngestionModule.tsx and IngestionModule.test.tsx.
Validation: component timer cleanup and pending/error/completion lifecycle tests, existing ingestion module tests, typecheck, cumulative parent-to-head diff review.
Resources: mocked tests only; no live port5202 interaction, providers, database effects, publication, or restart. Broader ingestion/Gold goal stays paused. No merge authority.
Failure critique: timers must unmount on target change/completion/failure; elapsed time is not backend progress; no fabricated intermediate nodes, completion checks or private reasoning. Active requests and user drafts must remain untouched.

Validation result: 62 tests pass across activity, ingestion module, saved-reader and ingestion-page suites; tsc -b and diff check pass. Existing async-test act warnings retained in /tmp/ingest-activity-tests.log. Independent static review found no actionable issues; reviewer test startup hit read-only Vite cache, so tests are author-verified.
