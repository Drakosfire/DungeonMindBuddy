# DOGFOOD: streamline Ingest local navigation and evidence

**Status:** ACTIVE under the user-authorized Ingest-first UX iteration (2026-10-16), amended to align workflow actions with verified source proof.
**Base:** GitHub's current `main` is `eac0861351c4965797233f5d7543d4cb537552c9` (2026-10-16), three commits after the last shell-fetched snapshot `f92a3e9e151742f80c77fbadbfa2b723712d1906`. The shell cannot resolve github.com, so use the connected GitHub API for re-anchoring. Those newer commits touch Agent/server evidence paths and handoffs, disjoint from this UI lease. Before this update, #1259 head `cc768839ee6e24fe4511201d71698fb735ac5210` shared merge base `b309616302225f2d84e08514eb39eb81f49f414d`; compare reports main 12 commits ahead and the old PR 18 commits ahead of main. Preserve the PR's five Ingest files while re-anchoring to current main. The original UI work merged by #1256 is included in the PR.
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
  but Extract waits for a prepared, current normalized source. Exercise both
  the visible controls and handler/API-call boundary in regression tests.
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
for Prepare. The API contract and backend write behavior remain out of scope.
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
