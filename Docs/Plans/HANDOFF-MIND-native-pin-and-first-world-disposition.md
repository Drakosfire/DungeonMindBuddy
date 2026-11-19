# MIND — native Core pin and first-World disposition

**Status:** EXPLICIT SCOPE SPLIT / ADOPTABLE HANDOFF. The authorized MIND
owner may adopt Slice A after the current-state checks below; the earlier
BLOCKED disposition at commit `752516b5e69ff0793de73612c087cc9b72a480fa` is
superseded. No write to #1868 or its worktree is authorized.
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

Buddy #4029 is a later accepted precedent for a narrowly scoped current-main
native pin lane coexisting with older, different dependency proposals. Its
handoff records separate ownership of the exact Core228 pin and does not claim
to transfer every older proposal. It did **not** specifically name #1868, so
it is not by itself evidence that #1868 released its lease. On inspection the
#1868 worktree is clean at its 2026-10-28 head; that is a snapshot, not proof
that no one can resume it.

**Explicit split, authorized by the user's MIND implementation ownership and
this requested architecture disposition:** the current MIND lane may own the
current-main `4b6516e2…` → accepted `cf197b99…` native dependency adoption in
`pyproject.toml` and `uv.lock`, in its isolated checkout and serial PR. #1868
retains its separate classic-V7/Core150 proposal and every non-pin path; its
branch and worktree are untouched. This is a source- and revision-specific
allocation, not an inference that its ACTIVE handoff expired or a blanket
transfer of other paths. Before MIND writes, re-fetch both heads and inspect
active PRs, worktrees and current pin ownership; if another live editor or a
new incompatible lease has appeared, resolve that collision explicitly rather
than proceeding on this snapshot. Record this pinned disposition in the
consuming handoff. No standing PRIME or steward approval is added.

Before #1868 can integrate, its owner must re-anchor it against then-current
main, retain the accepted native pin unless a newly authorized upgrade says
otherwise, regenerate/verify the lock, resolve actual behavioral dependencies,
and obtain the current exact-head review and required verification. This
requirement neither closes nor edits #1868 and does not promise that its
classic-V7 behavior remains appropriate for the current native architecture.

## Slice A — dependency adoption after current-state checks

Re-fetch Buddy main and relevant open leases. On an isolated serial branch,
advance only Buddy's two DungeonMind dependency declarations in
`pyproject.toml` from the then-accepted main pin to the accepted Core #231 merge
`cf197b9939f7b9106c75a8afb9fcf918c8b4aa1c`, regenerate `uv.lock` with the
owning locked toolchain, and inspect all lock changes. Preserve WorldKeeper,
GenerationEngine, unrelated dependencies and accepted DungeonMind state. The
expected implementation write set is `pyproject.toml` and `uv.lock`; the
consuming handoff must pin this explicit split and name the isolated lane and
resources; use a separately authorized path for any settlement record. Do not bundle first-World runtime changes.

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
there, then re-anchor and rerun. This disposition changes no runtime and does not authorize deployment or
retirement. The user-authorized MIND owner may implement and open the bounded
Slice A PR after the stated checks; Slice B requires its own bounded handoff. Preserve the
broader objective: optimized deployment and real acceptance, V10 retirement,
and V11 completion remain subsequent work with their own evidence and gates.
Do not infer them complete from pin adoption or first-World publication.
