# MIND — native Core pin and first-World disposition

**Status:** BLOCKED design; no implementation write lease is allocated.
**Anchor:** Buddy `main@ef2a3e5e50ab2dd4077230589767b2629e9d46ec`; Core #231
merged at `cf197b9939f7b9106c75a8afb9fcf918c8b4aa1c`; Buddy #4087 merged at
`5574068634341c57235800b77f7278bf0c6c08ad`.
**Topology:** serial. Pin adoption precedes a separately bounded native
first-World consumer slice; neither authorizes a parallel dependency write.

## Decision on the overlapping pin

Open Buddy [#1868](https://github.com/Drakosfire/DungeonMindBuddy/pull/1868),
head `72b162688b613cd958a7b9dc57739160e714ac16`, carries the ACTIVE
`HANDOFF-INGEST-v7-read-receipt.md` on branch `codex/buddy-v7-read-receipt`.
It explicitly leases `pyproject.toml` and `uv.lock` for its Core150 pin and
contains edits to both files. The handoff is not on current main, but the
repository policy permits pinned branch handoffs; location, age, a later
mainline pin, and Git mergeability do not release or transfer the lease.
Current Buddy main pins Core `4b6516e2c0dfd81acaa4410b9b9bb9da18894c90`
in both direct and uv-source entries.

**Gate:** Before editing either shared dependency file, obtain a recorded,
explicit transfer or release of those two paths from #1868's named lane owner,
or another explicit authority that actually supersedes that lease. Record the
source, exact scope and effective ref in the consuming handoff. An owner may
retain #1868 as a separately rebased historical proposal after an explicit
release; that retention alone is not a transfer. Do not close, edit, rebase or
repurpose #1868 without authority for that action. If release is not available,
continue read-only design and verification that does not write the leased paths.

## Slice A — dependency adoption, after the gate

Re-fetch Buddy main and relevant open leases. On an isolated serial branch,
advance only Buddy's two DungeonMind dependency declarations in
`pyproject.toml` from the then-accepted main pin to the accepted Core #231 merge
`cf197b9939f7b9106c75a8afb9fcf918c8b4aa1c`, regenerate `uv.lock` with the
owning locked toolchain, and inspect all lock changes. Preserve WorldKeeper,
GenerationEngine, unrelated dependencies and accepted DungeonMind state. The
expected implementation write set is `pyproject.toml` and `uv.lock`; the
activation/transfer record must be in a separately pinned handoff or another
explicitly leased path. Do not bundle first-World runtime changes.

Acceptance requires reproducible locked installation and lock consistency,
verification that both direct and resolved sources use the exact Core SHA,
inspection of the complete dependency/lock diff, and the current owning Buddy
regression contracts for affected existing native reads, admission, publication,
authorization, scope and recovery. Run the repository's exact-source local
verification standard and independent review. Report inherited failures and
missing evidence; a successful pin is not a first-World or deployment proof.
No live World, operator database, serving process or provider call is authorized
by this design.

## Slice B — native first-World consumer, after Slice A settles

Re-anchor the actual merged Buddy and Core revisions, re-census active work and
write a new bounded implementation handoff with exact paths, resources and
verification before dispatch. Starting from Buddy #4087's immutable reviewed
effect inventory, define how the consumer compiles the reviewed first-World
effects to Core's accepted prospective, evidence-bearing operations; prepare,
confirm and recover the exact governed native change through the existing
owners. Prove scope/authorization, evidence and alias identity, atomicity,
stale or failed preparation, retry/idempotency and recovery at the owning
boundaries with disposable state. Do not silently publish a different effect
set or replace a failed native write with the classic writer. The native source
admission and classic writer currently advance different authorities; a native
source admission alone does not prove the World was written natively.

A failed consumer proof stays in its owning Buddy/Core boundary: fix and merge
there, then re-anchor and rerun. This disposition changes no runtime and does
not authorize deployment, retirement or an implementation PR. Preserve the
broader objective: optimized deployment and real acceptance, V10 retirement,
and V11 completion remain subsequent work with their own evidence and gates.
Do not infer them complete from pin adoption or first-World publication.
