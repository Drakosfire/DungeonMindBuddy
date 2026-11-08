# SURFACE: typed local World repository seam

Status: ACTIVE — bounded Phase 2A1 preparatory implementation.
Authority: coordinating steward explicitly activated this one preparatory typed-port/in-memory slice under Alan's standing request to execute the plan. This is not broad Phase 2 product activation.
Flow: SURFACE. Topology: stacked; implementation branch `codex/phase2a1-local-world-repository` is based on Phase 1 PR #2198's exact reviewed head `64f166f4fceff56e238292886bf932eb6b30e367`. Successor PR targets `codex/blank-surface-phase1` while it remains unmerged. Integrate only after #2198 and required cross-owner contract disposition settle; rebase/retarget then. No merge or deployment authority.
Checkout: `/home/drakosfire/Projects/.codex/blank-surface-phase1-20261107/worktrees/DungeonMindBuddy`.
Pinned design input: OverMind PR #106 exact draft head `7db578897e0eb40ab3672d26826eb3bbbee6007c`, `Docs/architecture/CONTRACT-local-world-execution-adoption-phase2.md`, blob `9ceb00c005a7e1a3e22c76bed22a01f501e8cb28`, supplied verbatim in the activation message. This is a design input only; no runtime import or claim that it merged.

## Disposition and boundary

Phase 1 #2198 is an acceptable implementation baseline for this development slice only. It remains draft/unmerged; its product acceptance and the broad Phase 2 gates remain open. At re-anchor, GitHub showed #2198 OPEN/DRAFT, mergeable, at the pinned head. Existing open #2199/#2196/#2197/#2200 own PROMPTS, #2191 owns REFERENCE, and other listed open PRs are INGEST/PLAY; no changed-path overlap was identified for the exact paths below. The only known same-workstream lease is #2198's blank Surface/handoff and it is not edited here. Existing authoring/recovery paths remain read-only consumers for this slice.

The OverMind contract calls Phase 2 implementation blocked pending Phase 1 acceptance; the coordinator's explicit activation narrows that hold only for this A1 contract/reference-adapter work. This slice does not activate package lifecycle, browser storage, editor integration, adoption, or renderer work. Buddy owns a future async local repository port; WorldKeeper remains semantic-operation coordinator; DungeonMind remains durable publication authority. Local IDs/revisions are distinct from durable DungeonMind IDs/revisions. No second recovery/truth ledger, fake durable receipt, or synchronous `Storage` facade.

## Exclusive expected write paths

- `Docs/Plans/HANDOFF-SURFACE-phase2a1-local-world-repository.md`
- `apps/live-control-ui/src/localWorld/localWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/inMemoryLocalWorldRepository.ts`
- `apps/live-control-ui/src/localWorld/localWorldRepository.test.ts`

No other files may be changed under this lease. If type/build integration requires a fifth path, stop and return for a scope amendment.

## Acceptance

- Define a typed asynchronous repository contract distinguishing `missing`, operational `error`, and expected-revision `conflict`; semantic local revision is separate from optional published DungeonMind revision.
- An in-memory reference adapter implements the port with stable local IDs, expected-local-revision compare-and-swap, immutable read/write boundaries, atomic semantic snapshot plus local event/history entry, and a distinct layout write revision that cannot advance semantic revision.
- A failure-injection boundary proves failed transactions preserve the committed snapshot and history. Stale writes preserve the full losing candidate alongside the committed state as an in-memory conflict result; no automatic merge or delete/retract behavior.
- Contract fixtures exercise four distinct test-only objects (two People, Location, Event) and meaningful edges; same-name distinct identities; CAS/stale conflict; stable local identity; mutation alias isolation; commit/reload-style readback through a second repository facade over the same in-memory backing; transaction failure preservation; and layout separation.
- Tests and documentation explicitly state that in-memory readback does not establish browser durability, reload persistence, quota behavior, crash consistency, or cross-tab coordination. “Reload” here means a new adapter/facade in the same process over the same in-memory reference store; constructing a new store starts empty.
- The history classification is informational only: A1 defines no executable/replayable WorldKeeper operation payload because the owner operation schemas have not been re-anchored for an implementation consumer. Do not interpret `supported-semantic-intent` as validation or authorization to publish.
- Conflict candidates are inspectable and retained in this reference store; A1 defines no resolution, discard, or export lifecycle. A later owned slice must design those paths explicitly before use.
- The A1 semantic snapshot covers only a title, objects and relationships. It does not define source/document/asset value types; candidate preservation is complete only for this current shape. Add and preserve any source/asset values before a later adapter accepts such edits.

## Deliberately excluded

No Dexie, `idb`, SQLite, IndexedDB, browser persistence, ZIP/package/import/export, conflict UI, local editor wiring, WorldKeeper/DungeonMind calls, server API changes, source admission, account adoption, graph renderer, demo data, model/provider, migration, or deletion/retraction semantics. No broad Phase 2 activation, merge, deployment, or live data changes.

The in-memory adapter only proves behavior of its process-local test store. A second facade over the same `InMemoryLocalWorldStore` can read a committed value; a fresh store starts empty. This is not browser reload restoration or durable recovery. The adapter also does not claim candidate resolution, semantic-intent compilation, or event replay.

## Verification plan and limits

Run the owning Vitest file, relevant workspace typecheck and build, inspect `git diff --check` and the exact cumulative `64f166f4...` → head diff. Run focused existing Surface/authoring regression tests only if the touched type boundary makes them applicable; this slice does not edit those paths. Obtain independent review of the exact cumulative diff and fix in-scope findings before commit/push and opening a draft stacked PR against `codex/blank-surface-phase1`. Report inherited failures and environmental limits precisely. These checks do not prove durable browser behavior or Phase 1 product acceptance.

Completed before PR:
- `npm test -- --run src/localWorld/localWorldRepository.test.ts`: 8/8 pass.
- `npm run typecheck`: pass.
- `npm run build`: pass. Existing warnings remain: a module is both dynamically and statically imported, and the main JS chunk exceeds 500 kB. This contract is not imported by a runtime surface, and no performance claim is made.
- `git diff --cached --check`: pass on the exact four-file cumulative diff.
- Independent read-only review of the cumulative `64f166f4...` diff: no blocking findings. Review specifically checked CAS/conflict retention, atomic snapshot/history swap, cloning, layout separation and scope. Follow-ups were recorded: operation classification is informational only, candidate resolution/export/discard is deferred, and a fresh-store missing assertion was added and passed. The reviewer did not rerun the commands above; those are author-run results.

No broad app test suite was run because this slice adds an unconnected contract/reference adapter and does not alter existing Surface or authoring consumers. This is not evidence of browser durability, package round-trip, conflict UI, or Phase 1 acceptance.

## Corrective review: request snapshot boundary

At the steward's report of independent HOLD on PR #2202 head `d2421f9821a1a8fc60b127b28ce425aa5921ae27`, native-browser reproduction showed that `commitSemanticEdit` cloned the proposed payload but read `worldId` and `expectedLocalRevision` from the caller-owned request again after an async hook. A caller mutation could therefore redirect the write or convert a stale CAS into a commit. The authorized corrective edit captures the entire request boundary synchronously before any await: IDs, expected semantic/layout revisions, title/scalar inputs, and cloned payloads. It adds contract tests that mutate semantic headers and layout revision immediately after invocation, plus a create-title snapshot case. The dependent IndexedDB implementation must receive the same correction and browser regression on its own branch before either PR can be re-reviewed.

This correction is limited to the existing A1-owned paths above. It does not widen Phase 2 activation or change package, editor, storage-authority, merge, or deployment scope. Exact new commit/review evidence is recorded after the owning PR update; the earlier head's approvals, if any, do not apply to the corrected head.

The initial correction was pushed to the existing PR #2202 branch as `e8cf5b1091abd8c0b8c0ed4e33d009a03563c737`, based on the prior A1 head `d2421f9821a1a8fc60b127b28ce425aa5921ae27`. Focused repository tests pass 11/11, TypeScript passes, production build passes with the existing dynamic/static import and >500 kB chunk warnings, and the cumulative diff check passes. This is author-run evidence; exact-head independent re-review and hosted CI remain pending.

## Questions for later slices

An IndexedDB adapter evaluation must compare direct IndexedDB, Dexie and `idb` against the settled port/transaction requirements before adding dependencies. It must prove real reload restoration, quota/private-mode/error handling, crash/interrupted transaction behavior, two-tab CAS conflicts, migrations, and saved-state timing in supported browsers. Package format/limits, document/source references, history/semantic mapping, serialization/hash validation, collision/fork semantics, and adoption contracts remain decisions for their authorized later owner handoffs. Renderer evaluation remains independently gated.
