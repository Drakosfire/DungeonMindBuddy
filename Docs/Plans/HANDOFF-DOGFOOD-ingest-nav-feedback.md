# DOGFOOD: consolidate Ingest navigation feedback

**Status:** ACTIVE under the user-authorized Ingest-first goal (2026-10-16).
**Base:** Re-anchored on fetched `origin/main@182738395801989b6169f5b3b354da9d2688dbf2` after #1257 merged. The main-only commits since this branch's original base change publication-coverage server/API files and do not overlap this UI lease. The branch was rebased onto this current main before updating the PR.
**Branch:** `codex/ingest-nav-feedback`.
**Checkout:** `/tmp/dmb-ingest-local-nav-refresh`.
**Topology:** serial successor to merged and deployed #1237; one PR. Checked open #1235 (`codex/ingest-source-observation-review` at `46ecdd5019f7fc70519b0e7b50b1a1ebe6955994`) for Graph Review/source-observation prepare UI, #1244 (`codex/ingest-candidate-evidence-ref-recovery` at `e6bea55259fec6efd3950e0d68aa9250dfa0bf15`) for server graph packaging, and #1251 (`codex/ingest-evidence-readiness` at `8e1ebf64b1ed677808b6b435f8d2d23e32f576ac`) for server readiness and `ingestReadiness` modules. Their active write sets do not overlap this UI-only lane.
**Runtime/data:** UI-only. 5202 was inspected read-only to dogfood the deployed toolbar; no source, API, Corpus, candidate, Graph, or persistence action was taken.

## Objective

Make the local Ingest navigation the single, calm home for recap identity,
source loading, workflow actions, and current workflow feedback. The recap
editor stays the main work surface. Keep the visible toolbar status concise and
put detailed feedback behind an in-toolbar disclosure, instead of a separate
large card that repeats next-action and prepared-source guidance. Keep the
prepared-recap state on the canvas concise and action-neutral because Review
and Load already live in the toolbar.

Also replace the hard-coded Session 22 prose in the empty raw-recap textarea
placeholder. On a Session 29 route, that unrelated example reads like stale
recap content; the empty editor should invite writing without implying another
session's text is loaded.

## Invariant

The toolbar status summarizes the current workflow once. Success, warning, and
error details remain inspectable and dismissible; collapsing them never hides
the concise current status or changes readiness/actions. Prepared-source copy
does not repeat toolbar instructions. The blank placeholder is instructional,
context-neutral, and never editor value or persistence input. Source selection,
review behavior, and ingestion gates remain unchanged.

When a saved browser draft is resumed, a fresh `inspect_status` response is the
authority for disk-derived recap status, paths, warnings, next actions, and
spelling audit. A stale draft must not restore claims such as `normalized_reused`
or an old readiness status when the current inspection reports the files
missing. If that inspect response does not include graph-preview information,
the last graph-preview result may remain visible as a separate graph lane; an
explicit current graph-preview result (including `missing`) replaces it.

## Expected write set

- `Docs/Plans/HANDOFF-DOGFOOD-ingest-nav-feedback.md`
- `Docs/Plans/HANDOFF-DOGFOOD-ingest-local-source-navigation.md` (settle merged #1237)
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
- `apps/live-control-ui/src/modules/ingestResultMerge.ts`
- `apps/live-control-ui/src/modules/ingestResultMerge.test.ts`
- `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.css`

Do not change API contracts, extraction or validation behavior, corpus files,
shared app navigation, saved drafts, or runtime services.

## Acceptance

- The navbar shows one concise, current status. Expandable details retain the
  exact feedback and next steps for success, warnings, and errors.
- The tall standalone toast/status card is gone; prepared-source state no
  longer repeats Review/Load instructions already available in the toolbar.
- A blank raw-recap field has an empty value and a neutral prompt such as
  “Paste or write the session recap here…”. It contains no Session 22 sample
  text for a selected session or a fresh entry.
- Resuming a saved browser draft cannot make fresh disk inspection appear to
  have reused files or be more ready than it is. Graph-preview evidence remains
  available only when the fresh inspection does not provide a newer graph
  result; an explicit missing result clears stale graph-ready claims.
- Source selection, review, and ingestion gating stay unchanged.
- Focused Ingest UI tests, UI typecheck/build, cumulative diff check, and
  rendered desktop/narrow preview are attempted and recorded. A preview may
  remain blocked by the host sandbox; record this explicitly if so.
- No prepare, extract, graph admission, or persistence action is taken during
  verification.

## Stop conditions

Stop if the fix needs a shared component, route contract, extraction change, or runtime/data change. Return that specific requirement for a new bounded handoff.

## Verification — 2026-10-16

- `IngestionModule.test.tsx`: 60/60 passed, including collapsed/expanded
  feedback, preserved error detail, prepared-source copy, and the blank recap
  prompt for both selected-session and new-entry states.
- `MemoryIngestPage.test.tsx`: 13/13 passed.
- `npm run build -- --outDir /tmp/dmb-ingest-nav-preview` passed (TypeScript
  and production Vite build); the existing large-chunk warning remains.
- `git diff --check` passed.
- Rendered verification is blocked in this host: Vite preview could not bind to
  loopback or all interfaces (`EPERM`), and browser policy blocks `file:` pages.
  The open 5202 page was observed read-only; no production service was changed.
- No prepare, extract, graph admission, publication, provider, or persistence
  action was taken.

### Saved-draft status reconciliation follow-up

- Root cause: hydration merges the fresh read-only `inspect_status` result with
  `latestResult` saved in localStorage. The prior merge let the old draft win
  status rank and restored old paths, warnings, next actions, and spelling
  findings. This could show `normalized_reused` beside fresh corpus proof that
  the normalized recap is missing.
- Updated the merge contract so fresh inspection owns recap/disk state. When
  inspection does not report a graph preview, the prior graph-preview result
  remains in its separate graph lane; an explicit graph result, including
  `missing`, takes precedence and clears stale candidate-ready states.
- Verification: `ingestResultMerge.test.ts` and `IngestionModule.test.tsx`
  passed (63 tests); `MemoryIngestPage.test.tsx` passed (13 tests); UI
  typecheck, production build, and `git diff --check` passed. The build retains
  the existing large-chunk warning.
- Rendered check remains blocked: only the user’s 5202 tabs were available in
  the browser, and the 5204 preview had refused connections on the earlier
  attempt. No navigation or write action was taken in 5202. No ingestion,
  publication, API, database, or corpus action was taken.

### Local-nav hydration feedback follow-up — 2026-10-16

- While saved status is being checked, the navbar now says it is checking; it
  does not briefly surface stale `reused`/`breadcrumb_required` claims from
  localStorage. Fresh disk inspection remains authoritative for recap status.
- If status inspection fails, the navbar keeps a dismissible warning and the
  saved disk-derived result is not promoted. The normal action guidance remains
  available, without saying the new draft has no saved files.
- Reset the status-toast key when selection changes so an identical result for
  another session can still be announced in the navbar.
- Regression coverage now exercises delayed and failed inspection with stale
  local drafts. The focused Ingest UI suites pass (78 tests); typecheck and
  production build pass. The production build still reports its existing
  large-chunk warning.
- Rendered local preview remains blocked by host networking (`listen EPERM` on
  127.0.0.1:5205); the attempted 5204 preview still refused connections.
  User-owned 5202 was observed read-only and left unchanged.

### Rendered preview and real-run inspection — 2026-10-16

- Started the PR UI on 127.0.0.1:5204 after the sandboxed bind failed. The
  desktop toolbar and empty recap prompt rendered. At 390×844, the toolbar,
  controls, and editor remain stacked without horizontal document overflow
  (`documentElement.scrollWidth === 390`).
- Opened the known Session 29 review route for run
  `f43e48e6-c775-4960-824f-fb398fe50bb9` read-only. The PR preview displayed the
  saved recap source, but its World Graph status was “Needs attention” and its
  detail said the local Graph session was revoked; Prepare and Extract were
  disabled. I did not reconnect the session or trigger any write action.
- The same review route on 5202 (current main, read-only) showed World Graph
  Ready and the existing recap source. Its status details expose a real
  contradiction for run `20261015T204654Z`: the manifest says
  `candidate_validation_ready`, `extraction_performed: false`,
  `llm_used: false`, and preview-only; the candidate has 59 nodes, 33 edges,
  and 154 evidence references, of which 144 resolve. Its validation report
  says `valid: true` while listing 10 unresolved evidence-reference warnings.
  The page also reports the canonical and normalized recap files missing while
  retaining `recap_reused` and `normalized_reused` in the inspected states.
- These are owning API/pipeline readiness and evidence-reference gaps, outside
  this UI-only lease. Open #1244 addresses provable legacy reference recovery;
  open #1251 makes unresolved candidate validation block readiness. No new
  pipeline implementation is claimed here.
- A read-only scan of available candidates found no `team`→`tea` node in the
  Session 29 candidate. The `tea` nodes found are in Session 25 and have direct
  source quotes about Hesta brewing tea, so that observation does not reproduce
  the reported misparse; its originating run still needs to be identified.
- No Prepare, Extract, Graph admission, publication, provider, persistence, or
  corpus write was triggered. 5202 was only read; the isolated preview was not
  used to reconnect or mutate its local Graph session.

### Local-nav redundancy and narrow layout refinement — 2026-10-16

- Kept the Ingest workflow in the sticky local nav: campaign/session/title,
  New recap, processed-source loading, Prepare/Extract/Review, and one current
  status. The idle status now says only “No recap source loaded”; the textarea
  keeps the actionable paste/write prompt, so the nav no longer repeats it.
- On narrow screens, New recap shares the session-title row instead of taking
  a separate full-width row. This trims vertical weight while leaving the
  session identity and source/workflow actions visible.
- Rendered the 390px Ingest preview and confirmed the title/New recap row,
  source loader, Prepare/Extract, and concise status remain visible without
  horizontal overflow. This was read-only; no ingestion, Graph reconnect, or
  persistence action was taken.
- Verification after the refinement: the three focused UI suites pass 78/78,
  `npm run typecheck`, `npm run build`, and `git diff --check` pass. The build
  retains the existing large-chunk warning.

### Superseded hydration and 320px breakpoint follow-up — 2026-10-16

- A resumed raw draft can enable Prepare while its initial disk inspection is
  pending. If that inspection later rejects, the old catch used to clear the
  newer Prepare result and replace its status with a stale verification
  warning. Hydration rejection and finalization now check the same generation
  fence as the successful response; starting a newer operation also releases
  the hydration gate so its result can be saved.
- Added a regression test that starts Prepare from a resumed raw draft, lets it
  complete successfully, then rejects the older inspect request. The prepared
  result and Run ingest availability remain intact.
- At 320px, the 40rem title/New recap placement used column 2 even though the
  22.5rem breakpoint has one explicit column. Both controls now use that single
  column. The rendered preview shows campaign/session/title/source controls
  stacked cleanly; document width is 305px in a 320px viewport.
- Verification: the three focused UI suites pass 79/79, `npm run typecheck`,
  `npm run build`, and `git diff --check origin/main...HEAD` pass. Build retains
  the existing large-chunk warning. Rendered checks were read-only; no live
  Prepare, Extract, Graph admission, or persistence action was taken.
