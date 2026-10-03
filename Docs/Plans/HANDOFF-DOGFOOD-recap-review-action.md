# DOGFOOD — saved recap review action

Status: ACTIVE. Direct operator authorization: restore the missing review action and reduce ingest clutter.
Base: PR878 merged at 67b0df1a478f50ff324b919d13f299c276b89198. Branch: codex/dogfood-recap-review-action. Topology: serial, one successor PR.
Write lease: this handoff; apps/live-control-ui/src/api/types.ts (optional extraction_run_id field only); apps/live-control-ui/src/modules/IngestionModule.tsx; apps/live-control-ui/src/modules/IngestionModule.test.tsx.
Runtime: existing DOGFOOD UI5202 and API7866; UI patch only, no restart, provider calls or Graph writes.
Invariant: validated candidates offer a Review saved source action. Immutable run/campaign/session identity and a request epoch fence asynchronous responses, superseded requests and unmount; selection changes clear review state. Verified captured metadata is rendered with source. Validate returned run/campaign/session before rendering. Diagnostics remain accessible behind a closed disclosure. Native admission and managed exact-run World guard remain governed.
Failures: unavailable/mismatched source reports visible error; absent run ID means no action.
Verification: focused mounted saved-source review, deferred session/campaign/run change and unmount, opened-review reset, identity mismatch and unavailable source tests; cumulative diff and whitespace check.
Limit: source review only. Authoritative Longmont source/run to managed Elderwyld association is still required for governed admission.
