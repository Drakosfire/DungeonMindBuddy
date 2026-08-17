---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — post-#609 authority sync
  - Flow: DOCUMENTS
  - Direction: STEWARD → DOCUMENTS → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOCUMENTS-cutover-post-609-authority-sync.md
  - Branch: documents/cutover-post-609-authority-sync

  ## Verification pointer
  - Dispatch base / current main: `7922b6108cf9e05787f9c79cddcee9347edb0b44`
  - PR #609 head: `ef71a7eb6cb376d01144e1c01242d16a77803886`
  - Sealed bundle Git blob: `274cdd9e6d38d5a00aa43d780779e95a7919d975`
  - DungeonMind pin: `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92`

  Record the already-merged #587 / #588 / #602 / #609 chain and DungeonMind
  #31/#32/#33 atomically across the mutable CUTOVER state authorities, then
  author the dispatch-ready DungeonMind PostgreSQL adoption-proof handoff.

  This PR changes documentation/state authority only.
---

# HANDOFF — record post-#609 CUTOVER adoption-proof authority

**Created:** 2026-08-16
**Status:** ACTIVE — required post-merge state-authority synchronization
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-cutover-post-609-authority-sync.md`
**Conversation/workstream:** `CUTOVER — post-#609 authority sync`
**Flow / owner:** `DOCUMENTS`
**Direction:** STEWARD → DOCUMENTS → REVIEW
**Design base / dispatch base:** `7922b6108cf9e05787f9c79cddcee9347edb0b44`
**Suggested branch:** `documents/cutover-post-609-authority-sync`
**PR title:** `DOCUMENTS: record post-#609 CUTOVER adoption-proof authority`

> Repository law: [`AGENTS.md`](../../AGENTS.md).
> Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).
>
> This PR closes the development cycle opened by PR #609.
>
> Do not dispatch the dependent DungeonMind PostgreSQL adoption proof until this
> state sync is merged and `main` has been re-anchored to that merge.

---

## §1 Mission and merge-ready invariant

**Mission:** A fresh CUTOVER steward can read repository authority and correctly dispatch exact Eldyrwild PostgreSQL existing-world adoption proof as the next dependent capability, without reconstructing the #587/#588/#602/#609 chain from GitHub or stale post-#585 docs.

**Merge-ready invariant:** Every mutable authority touched by this PR agrees that Captain/Thrin alias packaging, dual-sense relationship packaging, DungeonMind adoption-v2 runtime, the exact Eldyrwild adoption-v2 bundle, and durable contribution evidence identity are `DONE`; the first real PostgreSQL attempt `STOPPED` on evidence identity; the next CUTOVER capability is the DungeonMind PostgreSQL adoption proof; and product-authority switch remains `BLOCKED`.

```text
#587 Captain/Thrin alias package              DONE
#588 dual-sense relationship package          DONE
DungeonMind #31/#32/#33                       DONE
#602 exact Eldyrwild adoption-v2 bundle       DONE
first PostgreSQL acceptance attempt           STOPPED on evidence identity
#609 durable contribution evidence identity   DONE / MERGED

Buddy #609 head:
  ef71a7eb6cb376d01144e1c01242d16a77803886
Buddy #609 merge / dispatch-base main:
  7922b6108cf9e05787f9c79cddcee9347edb0b44
Buddy #609 implementation stamp:
  4446b6d207921a4be121ebb756d68b6078b8eee0
new sealed bundle Git blob:
  274cdd9e6d38d5a00aa43d780779e95a7919d975
DungeonMind #33 / current main:
  f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92

canonical Eldyrwild:
  world: eldyrwild
  revision: rev:0c644e56b45bcaac709012206e3e41c2
  payload: 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
```

GitHub recorded no formal review submissions on PR #609. Do not invent a review-cycle count from this sync.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Tracker, status, roadmap, predecessor-handoff status, and successor dispatch contract are one post-#609 transition. |
| Most likely adversarial sequence | Mark #609 `DONE` in the tracker while status/roadmap still say Captain/Thrin is next and Case B is forbidden. |
| Will §7 detect that failure? | **Yes.** Positive/negative scans require the stale next-slice claims to disappear from current-state owners. |
| Easiest boundary to under-test | The newly authored DungeonMind handoff silently broadening into runtime repair or product-authority switch. |
| Fact that forces stop/split | A current canonical authority has already advanced past #609, or the successor cannot be made dispatch-complete without changing DungeonMind adoption runtime. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; stewardship handoff after PR #609 |
| Design / dispatch base | `7922b6108cf9e05787f9c79cddcee9347edb0b44` (`origin/main`; PR #609 merge) |
| Branch / isolated checkout | `documents/cutover-post-609-authority-sync` at `/tmp/dmb-cutover-post-609-authority-sync` |
| Completed predecessor | PR #609 — `CUTOVER: seal durable contribution evidence identity` |
| PR #609 final head | `ef71a7eb6cb376d01144e1c01242d16a77803886` |
| PR #609 merge | `7922b6108cf9e05787f9c79cddcee9347edb0b44` |
| PR #609 GitHub reviews | none recorded; do not invent a cycle count |
| Named successor | `dungeonmind-eldyrwild-postgres-existing-world-adoption-proof` |
| Successor handoff | `Docs/Plans/HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md` |
| What remains false | Independent DungeonMind PostgreSQL acceptance PR is not landed; Buddy reads/writes are not switched to DungeonMind; product cutover remains blocked |
| Explicit non-goals | Runtime/code/fixture/World Graph edits; DungeonMind repository files; Backlog.md; Play docs; architecture rewrite |
| Runtime/state ownership | Documentation only. No `out/`, corpus, graph head, PostgreSQL, or DungeonMind mutation |
| Parallel collision | `#605` owns `Backlog.md` and threat-statblock tracker/roadmap; `#607` owns `HANDOFF-DOCUMENTS-machine-readable-state-sync-set.md`; PLAY lanes own Play docs |
| State-authority sync set after merge | This PR **is** the sync. After merge, re-anchor to its merge SHA before dispatching the DungeonMind proof |

### Pins this sync must record

```text
Buddy #587 merge:          cc5dc6ddba0750924a46cf13843498c124937e5f
Buddy #587 head:           e3f33ddde879637d6d8bfb9b03b2c5690e235a3d
Buddy #588 merge:          3415fcf96a28a29907e248e047ea0d2e75c50071
Buddy #588 head:           b4c78161ac6a2653f9df7f285c42b8006e8c3bfa
Buddy #602 merge:          9b170c71a9d800157918186f8f17dc43fd993bcf
Buddy #602 head:           775f4aa23d9eb73ef33b4f1446ad9d7dd6f553ec
pre-fix bundle Git blob:   14cbe3394cd622fd58f321da1a6dfbcd6a3b97d3
Buddy #609 head:           ef71a7eb6cb376d01144e1c01242d16a77803886
Buddy #609 merge:          7922b6108cf9e05787f9c79cddcee9347edb0b44
#609 implementation stamp: 4446b6d207921a4be121ebb756d68b6078b8eee0
new bundle Git blob:       274cdd9e6d38d5a00aa43d780779e95a7919d975
DungeonMind #31 merge:     351af975598ee6f28d65634da150ac83d9b79808
DungeonMind #32 merge:     3d34d53b1c24862da32cf5f9f25e9b05b6ba5441
DungeonMind #33 merge / main:
                           f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92
```

---

## §3 Observable paths and adversarial sequences

| Path | Current stale claim | Required post-sync claim |
|---|---|---|
| Tracker next slice | Captain/Thrin alias package `READY` | DungeonMind PostgreSQL adoption proof `READY` |
| Status active slice | Captain/Thrin; Case B forbidden | PostgreSQL proof next; product cutover still blocked |
| Roadmap critical path | Heal/Lysandra READY/BLOCKED | Post-#609 adoption proof READY; product cutover BLOCKED |
| Alias-package handoff | `READY AFTER LIFECYCLE-PROOF STATE-SYNC MERGES` | `DONE / HISTORICAL` |
| Lifecycle-sync handoff | `ACTIVE` | `DONE / HISTORICAL` |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Worker reads tracker only | Next slice is PostgreSQL proof, not Captain/Thrin | Tracker scan |
| Worker reads status only | Same next slice; product cutover blocked | Status scan |
| Worker reads roadmap only | Same next slice; heal/Lysandra not current | Roadmap scan |
| Worker opens old alias-package handoff | Status forbids redispatch | Predecessor-handoff status |

---

## §4 Files in scope — exact write lease

This is one guarded atomic state-authority transaction.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-cutover-post-609-authority-sync.md` | Own this transition |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Record #587/#588/#602/#609 and DungeonMind #31/#32/#33; name PostgreSQL proof next |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` | Advance active CUTOVER slice and DungeonMind pin |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Repair header/critical-path claims that contradict `main` |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md` | Mark #587 slice DONE/HISTORICAL |
| Modify | `Docs/Plans/HANDOFF-DOCUMENTS-cutover-lifecycle-proof-exit-state-sync.md` | Mark the post-#585 sync DONE/HISTORICAL |
| Create | `Docs/Plans/HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md` | Dispatch-complete successor contract |

**Bounded discovery exception:** none.

If another current-state document must change to remove an actual contradiction, STOP and return the discovered path to stewardship rather than editing it silently.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `Backlog.md` | Open PR #605 write lease; sequencing belongs in the tracker |
| `Docs/Plans/HANDOFF-DOCUMENTS-machine-readable-state-sync-set.md` | Open PR #607 write lease |
| `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md` | Open PR #605 |
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Stable architecture; no invariant changed |
| `Docs/Sources/design-agent/**` | Non-authoritative export mirror |
| `apps/**`, `src/**`, `scripts/**`, `tests/**`, `graph_data/**` | Runtime/code/fixture |
| DungeonMind repository files | Successor implementation lease |

Do not:

```text
rerun or alter the sealed #609 bundle
patch DungeonMind adoption runtime
regenerate Captain/Thrin or dual-sense packages
mutate Eldyrwild
declare CUTOVER_READY
switch product authority
dispatch the DungeonMind proof from this unmerged sync
```

---

## §6 Implementation contract

Update current-state owners so they agree with GitHub `main`. Do not rewrite architecture history. Author the successor DungeonMind handoff as an acceptance/proof slice over unchanged DungeonMind #33 consuming exact post-#609 Buddy bytes.

Keep later product-authority switch `BLOCKED`. Author-reported PostgreSQL green on #609 is enough to resume the acceptance proof; it does not make Buddy a DungeonMind product-authority consumer.

---

## §7 Evidence required to merge

### Exact changed paths

```bash
git diff --name-only origin/main...HEAD
```

Require exactly the §4 write lease.

### No stale sequencing claims

Repository search over the mutable current-state authorities must not leave a current claim that:

```text
Captain/Thrin alias package is the next/active CUTOVER slice
Case B / existing-world adoption is forbidden because package-construction remains
PR #609 is unmerged/active
DungeonMind pin is still be76acc / PR #30 as current adoption runtime
eldyrwild-contribution-integrity-heal is READY
```

Historical explanation is allowed when explicitly labeled historical.

### Sequencing proof

The final docs must say:

```text
next:
  exact Eldyrwild PostgreSQL existing-world adoption proof

not yet:
  product-authority cutover
  Buddy read/write switch to DungeonMind
  correspondence/shadow-read acceptance
```

### Mechanical checks

```bash
git diff --check
git diff --name-only origin/main...HEAD
```

No runtime test suite is required for a documentation-only PR.

---

## §8 Required review handback

Record:

```text
branch
final head SHA
changed paths
confirmation that §4 was the exclusive write set
confirmation that successor handoff names unchanged DungeonMind f2e27380…
confirmation that product-authority switch remains BLOCKED
```

---

## §9 Acceptance checklist

- [ ] Tracker, status, and roadmap agree that #587/#588/#602/#609 and DungeonMind #31/#32/#33 are `DONE`
- [ ] First PostgreSQL attempt is recorded as `STOPPED` on evidence identity
- [ ] Next named CUTOVER capability is exact Eldyrwild PostgreSQL existing-world adoption proof
- [ ] Product-authority switch remains `BLOCKED`
- [ ] Predecessor Captain/Thrin and post-#585 documents handoffs are `DONE / HISTORICAL`
- [ ] Successor DungeonMind handoff is dispatch-complete and forbids runtime repair
- [ ] `Backlog.md` and architecture were not edited
- [ ] Diff is documentation-only
