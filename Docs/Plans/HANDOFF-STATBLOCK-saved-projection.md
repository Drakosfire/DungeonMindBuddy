# STATBLOCK — shared saved mechanics render

Status: SETTLED. PR2224 merged36d292301397fef96c9f6a097d21b745db41189c
and delivered UI47a9ec5d31493ad904cf3f38feb7994dd43225a7 on5202. Exact source,
integration and delivery-recipe review approved;193 owning tests/build and all
seven CI checks passed. Delivered exact statblock render, read-only failure/retry,
creation gate and dirty-input isolation passed with no candidate/provider/content
writes. Protected APP/Core/session conservation passed; lease released. API-only
2226 subsequently delivered57cf094e without changing this UI.

Historical scope: PRIME owned this bounded serial slice under the operator's
References/statblock goal. Base43a56972dd27b21d92c749f56be60cc8ae5c7497;
branch codex/statblock-saved-projection in the existing buddy-context-loop checkout.
No concurrent implementation lane owns these editor paths. ADVERSARY retrieval
and the held Play2172 work remain separate; their leases are unchanged.

## Outcome and invariant

The existing SavedMechanicsRevisionEditor already owns exact version opening,
local draft recovery, validation, immutable successor Save and unknown-outcome
recovery. Adopt the existing StatblockRenderer inside that component so saved
mechanics can be read as a statblock as well as edited. Later popup, conversation
and full-render hosts must adopt this owner rather than introduce another editor
or store. This slice does not create those hosts or claim their completion.

The render represents the exact opened saved revision, not unvalidated local
edits. Label it accordingly. Editing retains the existing working copy and Save
semantics; a successful Save/recovery opens and renders its exact successor.
Delayed, failed or scope-mismatched reads must not render an unverified response.
Opening a World workbench with a retained draft hint first verifies that exact
draft. Saved mechanics reopen without reading an expired candidate; unsaved drafts
keep existing candidate recovery. Explicit candidate URLs keep their behavior.
No generation, association writes, model settings, contracts,
API/schema/store/dependency changes or compatibility path.

## Exclusive writes

- This handoff.
- apps/live-control-ui/src/statblocks/revision/SavedMechanicsRevisionEditor.tsx.
- apps/live-control-ui/src/statblocks/revision/SavedMechanicsRevisionEditor.test.tsx.
- apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx and its
  owning test: restore an admitted saved World draft independently of candidate
  expiry and expose the saved editor outside the active-candidate gate.
- Docs/Plans/HANDOFF-REFERENCE-readable-source-panel.md: truthful predecessor
  source merge and UI delivery settlement, with remaining References holds intact.

Runtime leases: no restart or content write in implementation. Current API8dca0f10
PID2326407, UI99e1f39ea PID2431750; schema20261108_0130. Restored DMS7860
PID2423656 uses unchanged f95e92cb source/config and existing Firestore collections;
readiness and retained exact revision read pass, with no provider/content writes.
Qualified delivery is separately pinned and reviewed, preserving retained state.

## Verification and delivery

Use owning component tests to prove exact saved render, local edit isolation,
successor rendering after Save, delayed opening, rejected identity, read failure,
and existing draft/recovery behavior. Use real StatblockRenderer, not a mock.
Run renderer/editor cohorts and production type/build. Inspect cumulative diff,
independent Bugbot review, commit/push/open one PR, CI, merge and protected UI-only
delivery. Controlled retained-data browser verification is technical evidence;
dogfooding/operator acceptance are excluded from this goal.

The full goal remains: native threat association; creation through agent or tool;
shared editable popup/conversation/full projection; image generation/review and
selection; exact-version/draft/conflict behavior. This first adoption slice does
not satisfy those remaining requirements or resume held Play integration.

## Candidate evidence

The affected workbench/editor/renderer cohorts pass193 tests; TypeScript and Vite
production build pass. An isolated browser using candidate static assets opens an
existing saved Sheep draft through Build Tools → Statblocks → Open saved mechanics.
The actual exact revision and ability table render; local text edits leave the
saved render unchanged. Zero candidate reads, no provider/content writes, no
browser errors or blocked writes, and the temporary read session was revoked.
This witness exercises retained mechanics, not creation of the Corrupted Edge ooze.
Independent review, CI, merge and protected delivery remain required.

Saved-draft admission and refresh errors share an actionable read-only retry outside
candidate presentation. A committed Save and opening its successor are separate
outcomes: retain the committed revision as the selected recovery hint, keep exact
read failures visible, pause edits to the old displayed source, and retry only the
read. The same selection survives reload. Neither retry resubmits Save/generation.

Draft read admission also gates Create & generate, in both presentation and the
submit handler. Failed or pending reads cannot replace the retained recovery join.
The controlled browser fault check verifies blocked creation, visible retry, exact
saved render after recovery and no candidate/provider/content writes.
