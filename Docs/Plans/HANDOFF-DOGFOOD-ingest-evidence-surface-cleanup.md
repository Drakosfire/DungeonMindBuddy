# DOGFOOD: streamline Ingest local navigation and evidence

**Status:** ACTIVE under the user-authorized Ingest-first UX iteration (2026-10-16), amended to align workflow actions with verified source proof.
**Base:** fetched origin/main@c6eacbbba94efdf8f6a0c1fad43b5a0c6bf709d1 (2026-10-16). Re-anchored from the existing PR head through a merge commit; main’s four intervening commits touch only JEV evaluator/handoff paths and are disjoint from this UI lease. The product diff remains confined to the five Ingest files.
**Branch:** `codex/ingest-evidence-surface-cleanup`.
**PR checkout:** `/tmp/dmb-ingest-pr1259-review` is an isolated content mirror of the open PR tree used for review and verification. Its local branch name/commit metadata differ from the GitHub head; compare the tree, not the local SHA. `/tmp/dmb-ingest-local-nav-refresh` is a stale, dirty precursor checkout at `6c3bf566` with overlapping uncommitted changes; do not treat it as the PR source without reconciliation.
**Topology:** serial successor to merged #1256, one follow-on PR. Open #1235 owns Graph Review/source-observation review files; open #1244 owns packaging/reference recovery; neither overlaps this UI lease. #1251 and #1258 are merged prerequisites and do not own these paths.
**Runtime/data:** UI-only. 5202 and 5204 stay read-only. A local frontend preview of this checkout may run on `127.0.0.1:5205` for rendered desktop/narrow-width acceptance; it can use existing read-only surface/artifact/status endpoints, including `inspect_status`. Do not call Prepare, Extract, Review mutations, Graph admission, publication, provider/model actions, or any endpoint that writes source, candidate, Corpus, graph, or persistence data.

## Objective

Make the sticky Ingest local navigation the clear home for recap identity,
available source loading, workflow actions, and meaningful status. In the empty
state, keep campaign/session/title identity visible while omitting disabled
source and workflow controls and the duplicate “No recap source loaded” line.
Show a welcoming canvas whenever the surface has no loaded or prepared recap,
even when a returning user has a retained session number or older processed
recaps available. Reveal source and workflow controls once they are useful.
Reduce evidence clutter below it by showing each proof fact once. File existence
and corpus impact currently repeat the same recap paths and Found/Missing
states; readiness lanes repeat the current next action already shown in the nav.

## Invariants

- Do not move or duplicate campaign/session/title, source loading, Prepare,
  Extract, Review, or concise current status out of the local navigation.
- Keep the local bar a distinct navigation landmark under the shared command
  bar. Preserve keyboard access, existing campaign/session/title editing,
  source-load behavior, and the Prepare → Extract → Review sequence.
- At narrow widths, keep the stacked source picker compact; do not retain the
  desktop source row's flex basis as a large blank vertical spacer.
- In a truly empty source state, do not show disabled source-load controls,
  disabled Prepare/Extract controls, or an empty-state status that repeats the
  editor prompt. Surface those controls as soon as a source, active operation,
  or operation feedback makes them relevant.
- Keep the empty-state “Paste recap” action in the local nav. The welcome canvas
  explains the experience briefly; it does not repeat the source choices and
  workflow as a numbered checklist or second CTA.
- When saved ingest status exists, provide a local-nav shortcut to the evidence
  disclosure while leaving recap text and detailed proof on the main surface.
- Show the designed empty welcome after hydration when no recap text, loaded
  artifact, normalized recap, or preview exists, even if prior processed recaps
  are available or the selected session is nonzero. Keep it hidden for prepared
  work, errors, active operations, and saved-source reader mode to avoid
  obscuring meaningful work or flashing while state restores.
- Keep the recap editor and saved-source projection on the main surface.
- Preserve every on-disk existence result, exact path, record count, source
  preview, graph count/status, warning/error, authority transition, canonical
  preview/diff, and spelling audit. Details may be collapsed or expanded at the
  relevant file row, but no proof may be silently discarded.
- Do not expose duplicate summary states: the navbar owns the current status and
  next action; one per-file row owns that file's existence and preview evidence.
- Do not change ingestion API contracts or backend write behavior. On the UI,
  workflow actions must require authoritative source proof; stale status tokens
  alone never grant permission to prepare or extract.

## Exclusive write set

- This handoff
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.css` (only local-nav
  selectors)
- `apps/live-control-ui/src/styles.css` (only the existing Ingest proof-row
  selectors)

## Acceptance

- Remove the redundant readiness-lane list that repeats the nav's current
  next-action/status summary.
- Combine file proof and corpus-impact presentation into one list. Each row
  shows Found/Missing once, retains its exact path and record count, and offers
  any available size/time/preview as a per-file expansion.
- Keep run diagnostics inspectable without duplicating visible nav text.
- Make the local bar a named navigation landmark. On a new/empty recap, show
  only the identity controls and any available real source choice; omit disabled
  source/load controls, inapplicable stage buttons, and “No recap source loaded”.
  Keep the “Paste recap” action in that bar; the welcome remains concise and has
  no duplicate step list or paste button. With saved status, show an Evidence
  shortcut there. Once recap text or a processed source is available, expose
  the workflow stages and a concise next action in the nav.
- Add focused regression tests for one file-status presentation and expandable
  per-file evidence, plus empty and ready nav states. Run the focused Ingest
  suites, UI typecheck/build where dependencies permit, and cumulative
  `git diff --check`.
- Treat the canonical and normalized recap proof plus normalized-lineage state
  as the authority for disk-backed actions. When proof is absent, partial,
  missing, stale, or provenance-unknown, hide workflow actions and keep the
  recovery guidance; stale `recap_reused` / `normalized_reused` tokens cannot
  authorize Prepare or Extract. User-provided raw text may authorize Prepare,
  but graph extraction waits for a prepared, current normalized source across
  the navbar and Advanced graph preview/materialization paths. Exercise the
  visible controls and handler/API-call boundary for each path in regression
  tests.
- Render the branch on isolated `127.0.0.1:5205` and verify the restored empty
  landing, loaded-source navigation, and responsive layout at desktop and
  narrow widths.
- No Prepare, Extract, Review mutation, Graph admission, persistence write, or
  publication action is used for verification; 5202 and 5204 remain untouched.

## Stop conditions

Stop if proof rows require API changes, new persistence state, or a shared
cross-surface component. Return that exact contract need for a separate bounded
slice rather than broadening this UI lease.

## Scope amendment — 2026-10-16

The user-authorized Ingest-first objective requires safe, understandable
recovery when saved source proof and status claims disagree. Fresh Bugbot review
found that `sourceInputSatisfied`, `canPrepForIngest`, and `canRunIngest` can
trust stale `recap_reused` / `normalized_reused` tokens while the same result
reports missing or unverified canonical/normalized files. This makes the UI
invite writes/extraction after it has told the user to restore or load source.
The same leased UI module and regression suite now also own a narrow action
eligibility fix: require verified canonical+normalized source proof and current
normalized lineage for disk-backed extraction; require actual raw/loaded source
for Prepare. Bugbot then identified that Advanced Build Graph Preview and
Materialize Preview Supergraph also invoke saved-recap extraction while checking
only stale reuse tokens. The same source-proof invariant therefore covers those
two UI controls and handlers; they now require confirmed current normalized
source too. The API contract and backend write behavior remain out of scope.
No other ingestion gates, pipeline behavior, or publication behavior are
authorized by this amendment. This remains the single serial implementation PR
#1259; no successor PR is opened.

## Verification

- `IngestionModule.test.tsx` and `MemoryIngestPage.test.tsx`: 77 passed
  (64 + 13), including empty-state nav focus, concise welcome, saved-status
  Evidence shortcut, and loaded-source navigation states.
- `npm run typecheck`: passed.
- `npm run build`: passed; Vite reports the existing large-chunk warning.
- `git diff --check`: passed.
- Rendered acceptance on isolated 5206 because 5205 was already occupied: at
  desktop, the empty nav keeps campaign, session, title, recap entry, and source
  choice together; the welcome is reduced to a short explanatory panel. The
  session 29 Evidence shortcut is covered by the component test. Earlier
  rendered acceptance on isolated 5205 verified that the nav keeps campaign,
  session, title, and source choice together; loading processed Session 27
  exposes Prepare / Extract / Review and the loaded normalized recap. At 390px,
  the welcome stack and toolbar remain readable; the source row's desktop flex
  basis initially caused a large blank spacer and is now reset for the stacked
  layout. The browser viewport override was reset after testing.
- A separate rendered inspection of restored Session 29 showed a graph
  candidate (59 nodes / 33 edges) while status inspection reported the
  canonical recap and normalized recap missing. The updated welcome and status
  language directs the user to restore/load verified source and treats the
  per-file evidence as authoritative; no extraction was run. A current 5204
  dogfood view also exposed that the status service still returns
  `breadcrumb_required` and CLI breadcrumb-routing steps when both recap files
  are missing. The UI now labels that state from explicit on-disk proof and
  keeps raw server recommendations in a collapsed diagnostic disclosure.
  The status-service precedence itself is outside this UI lease. Existing
  tests intentionally use `breadcrumb_required` as a retrieval-readiness state
  even immediately after Stage + Preview, before recap files exist. A follow-on
  server slice should separate retrieval readiness from the immediate next
  operation: report the earliest missing source/derivative prerequisite and
  withhold breadcrumb-routing recommendations until the normalized recap and
  reviewed seed are verified.
- `IngestionModule.test.tsx`: 64 passed after adding regression coverage for
  missing-source proof, user-facing recovery guidance, collapsed raw server
  recommendations, and persistent local-nav guidance after its transient toast
  is dismissed. Fresh inspection-only status still keeps the empty nav quiet.
  Existing React `act(...)` warnings remain.
- A fresh Bugbot review of exact head `64574602434681d7335ed25d8d06268a1f249487`
  found one P2: reuse states could outlive missing/incomplete recap-file proof,
  leaving post-dismissal guidance misleading and the prepared-source notice
  claiming the recap was on disk. The follow-up keeps file-status guidance
  visible after the toast is dismissed and only shows the prepared-source notice
  when both canonical and normalized files are explicitly confirmed. Existing
  graph-replacement guidance keeps priority when a preview graph is ready. The
  regression test covers unverified proof, toast dismissal, and the confirmed
  prepared-source case. This fix has not received another Bugbot pass.
- Latest verification: `IngestionModule.test.tsx` 68 passed;
  `MemoryIngestPage.test.tsx` 13 passed; `npm run typecheck`, `npm run build`,
  and `git diff --check` passed on the pre-review head. After the follow-up fix,
  `IngestionModule.test.tsx` passed 68/68, UI typecheck, production build, and
  `git diff --check` passed. The build retains the existing large-chunk warning
  and the IngestionModule tests retain existing React `act(...)` warnings.
- Latest nav polish keeps the empty-state next action in the local nav and
  changes the welcome card to a distinct preservation/safety message. At 390px,
  the session-title input now spans the available row instead of being squeezed
  beside its Required badge; desktop identity controls remain in one row.
  Rendered proof was captured at 390x844 and 1280x720 on isolated 5206. The
  focused Ingest suites pass 81/81; typecheck, production build, and cumulative
  `git diff --check` pass. No ingestion write action was used.
- Loading the existing Session 27 processed recap in the isolated preview
  displayed “Local Graph session was revoked. Reconnect explicitly.” I did not
  reconnect or run another graph action. The tab's temporary UI state was
  isolated to 5205; 5202 and 5204 were not changed.
- No Prepare, Extract, Review, graph publication, or persistence-write action
  was used for verification.
- Fresh Bugbot review on the pre-amendment PR tree found that stale
  `recap_reused` / `normalized_reused` states could leave Prepare and Extract
  available when recap proof was missing or incomplete. The scope amendment
  above authorizes the same leased UI module and test suite to close that gap;
  backend write/API behavior remains unchanged.
- After the amendment, `IngestionModule.test.tsx` and
  `MemoryIngestPage.test.tsx` pass 82/82; UI typecheck, production build, and
  `git diff --check` pass. The suite retains its existing React `act(...)`
  warnings and the build its existing large-chunk warning. Added cases prove
  missing/partial file proof and stale normalized lineage hide workflow actions,
  while confirmed current source remains usable.
- Rendered action-gating acceptance on isolated 5206: at 390x844 with stale
  reused-state tokens and missing file proof, Prepare/Extract/Review are absent,
  recovery guidance is visible, and the page has no horizontal overflow. At
  1280x720 with canonical+normalized files and `normalized_current`, the current
  prepared-source notice and Prepare/Extract/Review controls are visible, with
  no horizontal overflow. The captured requests were read-only `inspect_status`
  responses only; the API-call boundary was also asserted in tests.
- Re-opened the actual Session 29 surface on isolated 5206 in read-only mode;
  it reports the source missing and offers the recovery path without workflow
  write actions. No Prepare, Extract, Review mutation, Graph admission,
  persistence write, or publication action was used. 5202 and 5204 remain
  untouched. Run a fresh Bugbot review on the final re-anchored PR head before
  dogfood.
- Bugbot on re-anchored head `e262bdb3c4a556abc75f396e072a319efce59b93`
  found a remaining P2 bypass: Advanced Build Graph Preview and Materialize
  Preview Supergraph could call recap-backed extraction using stale reuse
  tokens. Both controls and handlers now require the same confirmed current
  normalized-source proof as navbar Extract. A regression forces those handlers
  after simulating enabled controls and confirms no write/API operation runs.
  The focused Ingest suites now pass 83/83; UI typecheck, production build, and
  `git diff --check` pass. Run fresh Bugbot on the updated exact PR head before
  dogfood.
- Bugbot on final PR head `acb2c470cb08f3dc59414ad2e01b423514486614` found a
  P2 session-switch gap: source proof from the previous selection could linger
  and enable actions for the newly selected session before its status was
  checked. Campaign/session changes now clear the prior result and state;
  saved-file proof and graph actions additionally require a hydrated result
  whose campaign/session match the current selection. Session changes inspect
  saved status on blur. A regression checks that verified Session 23 proof
  cannot enable graph or ingest actions for Session 24 when its files are
  unverified. The live wizard continues to use its current operation result
  while it is in progress, independent of the saved-status proof gate.
- Final focused verification after the session-switch fix: 71 IngestionModule
  tests and 13 MemoryIngestPage tests pass; UI typecheck and production build
  pass; `git diff --check` passes. The build retains its existing large-chunk
  warning. A fresh Bugbot review of the resulting PR head remains required.
- Bugbot on PR head `6eb0044f18f66dd75d169bf7f4399243c972176b` found a P2 race:
  a recap operation started for one session could finish after the operator
  switched sessions and restore the old result into the new selection. Campaign
  and session changes now synchronously invalidate the selected-target token,
  clear stale operation status, and ignore late success/error/finally updates.
  Every recap mutation also verifies that the returned campaign/session matches
  its request before adopting the result; a mismatched response produces a
  visible recovery status rather than leaving the operation in a loading state.
  All transient wizard actions require a result matching the current
  campaign/session; saved-file proof additionally requires hydrated status for
  that selection. Regressions hold Stage + Preview open, change the selected
  session, and confirm that its late response does not re-enable Apply; a
  second verifies that a mismatched server response produces an actionable
  status.
- Verification after this repair: `IngestionModule.test.tsx` 73 passed and
  `MemoryIngestPage.test.tsx` 13 passed; UI typecheck and production build
  passed (86 tests total); cumulative `git diff --check` passed. The build retains the existing
  Vite large-chunk warning and the component suite retains existing React
  `act(...)` warnings. No live ingestion or write action was used; 5202 and
  5204 remain untouched. Fresh Bugbot review of the updated exact PR head is
  required before dogfood.
- Bugbot on PR head `5d8f6251b8858274bc55bc838844cd61b8ca58e6` found a P2
  same-session draft-reset race: “New recap” leaves the campaign/session
  identity unchanged, so a late operation response could repopulate the cleared
  draft. Recap operations now capture a draft epoch; changing campaign/session,
  resetting to a new recap, or loading a prior recap invalidates that epoch.
  Stale responses and failures are ignored, and stale loading/finally handlers
  cannot clear the state of newer work. A regression holds Stage + Preview
  open, starts New recap on the same target, then resolves the old response and
  verifies that the cleared draft stays empty and Apply remains disabled.
- Verification after the same-session reset repair: `IngestionModule.test.tsx`
  74 passed and `MemoryIngestPage.test.tsx` 13 passed (87 total); `npm run
  build` passed (including TypeScript project build), with the existing Vite
  large-chunk warning; `git diff --check` passed. Existing React `act(...)`
  warnings remain in the IngestionModule suite. No live ingestion or write
  action was used; 5202 and 5204 remain untouched. A fresh Bugbot review of the
  updated exact PR head is required before dogfood.
- Fresh Bugbot found that target changes also need to clear loading indicators
  for saved-recap reads and duplicate reconciliation. Campaign/session changes
  now clear both flags alongside the previous source selection, while stale
  request cleanup remains generation-bound so it cannot reset a newer load.
  Regressions change sessions during deferred saved-source loading and
  reconciliation, then verify the source picker and repair action recover.
- Final verification after these target-change cleanup fixes:
  `IngestionModule.test.tsx` 76 passed and `MemoryIngestPage.test.tsx` 13
  passed (89 total); `npm run build` (including TypeScript project build) and
  `git diff --check` pass. The existing Vite large-chunk warning and React
  `act(...)` warnings remain. Fresh Bugbot review of the updated exact PR head
  is required before dogfood.

- Re-anchored cleanly on origin/main@3a70b3585744a42c2f5b97e68f3b7189513ab171. The current PR checkout has no Vitest installation, so the focused UI suites were not rerun after this history-only re-anchor; the existing product diff is unchanged.

- The restored empty-source canvas now keeps the identity and recovery status in
  the sticky local nav. After dismissing the transient warning, the nav still
  says saved ingest work is preserved, no graph changes were written, and how
  to load or paste a verified source. The main canvas no longer repeats the
  selected session number and missing-source warning; it stays a worldbuilding
  welcome. Added assertions to the restored-session regression. `IngestionModule.test.tsx`
  passes 76/76 and `MemoryIngestPage.test.tsx` passes 13/13. UI typecheck and
  production build pass; the typecheck used a temporary `/tmp` build-info path
  because this sandbox mounts `node_modules/.tmp` read-only. The existing Vite
  large-chunk warning and React `act(...)` warnings remain.
- Rendered acceptance of this text refinement is blocked: the authorized local
  preview port 5205 was already occupied. The strict launch returned “Port
  5205 is already in use”; I did not inspect, stop, or replace the existing
  server. 5202 and 5204 were untouched. Current main is c6eacbb, four commits
  after 3a70b358 through #1268. Its five changed paths are disjoint from this
  UI write set. This update re-anchors the UI branch to c6eacbb with a
  fast-forwardable merge commit while preserving the existing PR head.
