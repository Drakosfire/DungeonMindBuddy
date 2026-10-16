# DOGFOOD: consolidate Ingest navigation feedback

**Status:** ACTIVE under the user-authorized Ingest-first goal (2026-10-16).
**Base:** GitHub confirms `origin/main@2efb6ea184870df0f266ff98fe2eb9938c5d0366`, the merge of #1237. This isolated checkout starts at #1237 head `cbc2312dcdace89b62bc4b8c0d9d9ab8314f103f`, which is a parent of that merge and has the same product tree. A shell fetch was unavailable because this environment cannot resolve `github.com`.
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

## Expected write set

- `Docs/Plans/HANDOFF-DOGFOOD-ingest-nav-feedback.md`
- `Docs/Plans/HANDOFF-DOGFOOD-ingest-local-source-navigation.md` (settle merged #1237)
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/modules/IngestionModule.test.tsx`
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
