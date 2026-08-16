# Backlog Dispatch Authority — 2026-08-16

**Scope:** second backlog hygiene pass after merged PR #604.  
**Verification base:** `main` at `e504310f71863604267637eea6209dcbea04f929`.  
**Goal:** make root `Backlog.md` answer “what can a free agent actually pick up?” without duplicating workstream sequencing.

## Result

The first hygiene pass reduced the active root backlog from 74 status headings to 29. The second pass changes the information model rather than merely deleting more history:

- root status-bearing entries: **29 → 13**;
- root `READY`: **25 → 7**;
- adds `BLOCKED` and `DEFERRED` as first-class states;
- requires `Kind`, `Owner`, immutable `Captured`, `Last verified @ SHA`, `Depends on`, bounded `Slice`, and `Exit proof` for every READY entry;
- makes promotion to READY a rewrite from capture prose into execution form;
- removes tracker-owned work from root status and preserves it in a non-status delegated-work ledger;
- makes entries older than 30 days stale for dispatch until re-verified;
- re-anchors the Threat/Statblock tracker and roadmap so delegated work does not land in a known-stale status owner.

## READY after the pass

Seven independently dispatchable root slices remain:

1. design the campaign-creation-inside-existing-world contract;
2. publish the existing Statblock Workbench as a Build Tool capability;
3. add Build ready-state Reload / Discard-local through shared Edit ownership;
4. design durable source archive / restore authority;
5. improve the Hermes composer with optimistic transcript + multiline input;
6. design the worldbuilding-draft elevation authority transition;
7. restore browser-local statblock working-copy persistence without restoring trusted validation receipts.

These are intentionally a mixture of CODE and DESIGN slices. A design slice is READY only when the design itself is the independently useful capability and its exit proof is a checked-in authority/implementation handoff, not “design and implement.”

## Status corrections

### `BLOCKED`

`Generation liveness via lease heartbeat` is no longer labeled READY. The Buddy change depends on a first-class pollable DungeonMind generation-operation / lease-heartbeat contract; fixed client timeout replacement cannot be safely implemented by guessing provider lifecycle semantics.

### `DEFERRED`

- `source_phrase` renderer grounding is conditional on phrase-level extraction needing that path again.
- ecology/resource extraction is deferred until fresh current dogfood reproduces material species/resource duplication pain.

Both remain useful findings without pretending they should be pulled now.

## Removed from root status because another owner exists

### Campaign Supergraph

Root no longer carries independent READY copies of:

- exact-run Graph Review presentation;
- inspectable exact-run evidence failures;
- Ingest primary-path simplification;
- E1b world-anchor insertion.

`Docs/Plans/PR-TRACKER-campaign-supergraph.md` owns their status/sequence. The root ledger preserves the E1b concrete defect so it is not lost inside generic PR380F language. CUTOVER state synchronization is separately in flight through PR #598 / #602, so this pass intentionally does not edit the Campaign tracker and collide with that active worktree domain.

### Threat / Statblock

Root no longer carries duplicate status for:

- copyable Hermes authoring artifact;
- grounded answer → Threat authoring;
- graph chips;
- Revise-with-AI UX;
- dedicated editor expansion;
- Hermes liveness;
- Hermes telemetry;
- later statblock media work.

The Threat/Statblock tracker is re-anchored in this PR because its prior snapshot still called SBW09c2b “next” even though the following are merged:

- PR #491 — SBW09c2b commit/recovery;
- PR #502 — SBW10a exact query/hydration;
- PR #504 — SBW10b exact Threat projection;
- PR #508 — normal Workbench Threat publication bridge dogfood;
- PR #509 — resident verified World Graph read optimization;
- PR #512 — Threat parchment/glance plus shared Plan/Build World Graph lens.

The re-anchored tracker now uses the same READY/BLOCKED/DEFERRED discipline, splits `HERMES-TELEMETRY` from `HERMES-LIVENESS`, and marks bundled authoring/editor work `DECOMPOSE` rather than silently dispatchable.

## Removed as already done / no current owner

- Shared Plan/Build Threat projection and campaign-useful Threat glance are treated as implemented by merged PR #512. Future failures are new defects, not predecessor backlog resurrection.
- `/surface` / `SurfaceShell` deletion is removed after current repository search found no `SurfaceShell` code owner to dispatch. If a concrete legacy consumer reappears, capture that current defect instead.

## Ownership invariant

Going forward:

> **A capability has exactly one status owner.**

Root `Backlog.md` owns independent product debt only. A sequencing tracker/roadmap owns work it has admitted. Root may preserve a pointer but not a competing READY/BLOCKED status.

This also means an owner document must be re-anchored before its work is dispatched. A stale tracker is not made authoritative merely because root points at it.

## Freshness invariant

`Captured` records when the problem entered the system and never changes. `Last verified` records when the entry was reconciled against repository truth. Rewording/splitting an old item does not reset its age.

After 30 days without verification, a READY entry is stale for dispatch until rechecked against current `main`.

## Review focus

This is documentation/process authority only. Review should challenge:

- whether any of the seven root READY slices still hides more than one independently useful capability;
- whether any delegated item actually lacks the claimed owner;
- whether a supposedly satisfied READY dependency is not truly landed;
- whether the Threat/Statblock re-anchor incorrectly claims a merged capability;
- whether any removed root item still represents a current independent capability rather than a regression or tracker-owned successor.
