# Preserve proposal placement across an exact draft save

SETTLED #1691, merged 7fe760d87e3f1c2297211e76e15897cd9af80eb3.
Independent Bugbot approved 90e6a22c0fbe18d9d77389fe749a6c23e5d5b223,
with60 owner tests, typecheck/build and exact-diff review. UI-only protected delivery
on5202 preserved all retained APP rows and API2db5a66d9, APP0061/native0017.
Ordinary rendered authoring acceptance remains open. No active write lease remains.

Invariant: saving an unchanged captured draft must not invalidate its proposal.
Permit a newer saved revision only when its hash equals the captured draft hash
and current editor JSON/Markdown, page/World, visibility, edit permission and target
still match. Reject other hashes, older revisions, changed text/format/selection,
async editor/scope changes. Preserve immutable reservation, original source basis,
provider admission and APP apply identity. Never rebase changed writing.

Exclusive writes: this handoff; Docs/Plans/HANDOFF-BUILD-working-draft-context.md;
Docs/Roadmaps/ROADMAP-demo.md for predecessor settlement;
apps/live-control-ui/src/buildSurface/buildComposeBridge.ts and its test;
BuildPageProposal.test.tsx and component only if a reproduced effect requires it.
No server/schema/corpus/dependency or retained-state mutation.

Reproduce with real Tiptap and mounted proposal/mock review transport. Prove Keep
and reopen after exact save, lost-prepare recovery, stale/foreign/changed refusals,
single undoable insertion and duplicate protection. Focused tests, typecheck/build,
independent exact-head Bugbot review, PRIME merge and UI-only protected delivery
on5202. Preserve API2db5a66d9, APP0061/native0017, drafts and all retained state.
Live authoring acceptance remains open; no model probes during operator dogfood.
