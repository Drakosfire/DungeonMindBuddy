# Preserve proposal placement across an exact draft save

ACTIVE serial PRIME implementation, branch codex/build-proposal-exact-save,
base 2db5a66d9908d26897f85e2569b45770572d57b0, existing buddy-context-loop checkout.
One capability and one PR. Open hosted, Combat and Ingest lanes are disjoint.

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
