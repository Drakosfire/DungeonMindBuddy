# DOGFOOD: streamline Ingest local navigation and evidence

**Status:** ACTIVE under the user-authorized Ingest-first UX iteration (2026-10-16).
**Base:** Re-anchored to current `main@b309616302225f2d84e08514eb39eb81f49f414d` after merged #1260 changed Agent source-read accounting. The UI branch rebased cleanly; #1260 owns disjoint server/Agent files. The original UI work merged by #1256 is included in this base.
**Branch:** `codex/ingest-evidence-surface-cleanup`.
**Checkout:** `/tmp/dmb-ingest-local-nav-refresh`.
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
- Do not change ingestion gates, API contracts, or write behavior.

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
- Render the branch on isolated `127.0.0.1:5205` and verify the restored empty
  landing, loaded-source navigation, and responsive layout at desktop and
  narrow widths.
- No Prepare, Extract, Review mutation, Graph admission, persistence write, or
  publication action is used for verification; 5202 and 5204 remain untouched.

## Stop conditions

Stop if proof rows require API changes, new persistence state, or a shared
cross-surface component. Return that exact contract need for a separate bounded
slice rather than broadening this UI lease.

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
  language now directs the user to restore/load verified source and treats the
  per-file evidence as authoritative; no extraction was run.
- Loading the existing Session 27 processed recap in the isolated preview
  displayed “Local Graph session was revoked. Reconnect explicitly.” I did not
  reconnect or run another graph action. The tab's temporary UI state was
  isolated to 5205; 5202 and 5204 were not changed.
- No Prepare, Extract, Review, graph publication, or persistence-write action
  was used for verification.
