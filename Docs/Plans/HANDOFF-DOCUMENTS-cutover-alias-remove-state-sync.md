---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — post-alias_remove state-authority sync
  - Flow: DOCUMENTS
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md
  - Branch / PR: documents/cutover-alias-remove-state-sync

  ## Verification pointer
  - Design base: 3a52d309a606608c9338147b78e0a2f708084042
  - Dispatch base: 71d11169cc56880ed09f457ddd9a6069429d0b96
  - Semantic predecessor: PR #580, merged
  - Forensic predecessor: PR #577, closed unmerged at b31bbc32b98c170c44f75de3fa1e8e252e7d0555
  - Verification: exact §7 results from implementation handback

  This PR synchronizes repository state authority after the already-merged
  Kernel capability. It does not mutate Eldyrwild and does not implement the
  exact-six application slice.
---

# HANDOFF — Advance CUTOVER to exact-six alias retirement

**Created:** 2026-08-13  
**Status:** ACTIVE — one documentation/state-authority capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md`  
**Conversation/workstream:** `CUTOVER — post-alias_remove state-authority sync`  
**Flow / owner:** `DOCUMENTS`  
**Direction:** DESIGN → CODE → REVIEW  
**Design base revision:** `3a52d309a606608c9338147b78e0a2f708084042`  
**Base revision:** `71d11169cc56880ed09f457ddd9a6069429d0b96`  
**Suggested branch:** `documents/cutover-alias-remove-state-sync`  
**PR title:** `DOCUMENTS: advance CUTOVER to exact-six alias retirement`

> Repository law: `AGENTS.md`. Steward process: `Docs/Process/STEWARD-CYCLE.md`.
>
> This is the mandatory atomic state-authority sync after PR #580. Do not dispatch the dependent CUTOVER mutation slice while this sync is partial or unmerged.
>
> `origin/main` advanced from the design base by three `Docs/Sources/design-agent/**` export-mirror commits (`d9fe852b`, `317c8159`, `71d11169`). None of this PR's §4 paths changed. Dispatch proceeds from `71d11169cc56880ed09f457ddd9a6069429d0b96`.

## §1 Mission and merge-ready invariant

**Mission:** A fresh CUTOVER steward can read repository authority and correctly dispatch the exact-six Eldyrwild identity-shadow alias retirement as the next dependent capability, without reconstructing PR #580 completion state from GitHub history or stale handoffs.

**Merge-ready invariant:** Every mutable repository authority that currently claims CUTOVER status agrees that the generic Kernel `alias_remove` primitive is `DONE` at PR #580, the exact-six Eldyrwild `alias_remove` application is the sole next dependent `READY` CUTOVER slice, the remaining two source-grounded aliases stay `BLOCKED` behind its proven live/replay exit, `EVIDENCE_PROVENANCE` remains 8 until that governed mutation actually occurs, and neither documentation nor backlog state falsely claims that any Eldyrwild alias has already been retired.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** Tracker state, continuity state, completion handoff, backlog state, and successor dispatch contract are all different representations of the same post-#580 transition. |
| Most likely adversarial sequence | Mark Kernel `DONE` in one document → leave continuity/backlog saying Kernel is next → worker dispatches or reimplements the wrong capability. |
| Will §7 detect that failure? | **Yes.** Positive and negative authority scans require the stale Kernel-next claims to disappear from current-state owners and the exact-six successor to appear consistently. |
| Easiest boundary to under-test | The newly authored exact-six handoff: a tracker can say `READY` while the handoff silently broadens into generic Kernel work, all-eight packaging, or direct graph cleanup. |
| Fact that forces stop/split | A current canonical authority has advanced the CUTOVER sequence, PR #580 is no longer the relevant predecessor, or the successor cannot be made dispatch-complete without changing generic Kernel semantics or another durable contract. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `AGENTS.md`; `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Plans/PR-TRACKER-campaign-supergraph.md`; stewardship handoff after PR #580 |
| Design base | `3a52d309a606608c9338147b78e0a2f708084042` |
| Actual dispatch base | `71d11169cc56880ed09f457ddd9a6069429d0b96` (`origin/main` at dispatch; descendant of design base; §4 paths unchanged) |
| Branch / isolated checkout | `documents/cutover-alias-remove-state-sync` at `/tmp/dmb-cutover-alias-remove-state-sync` |
| Completed predecessor | PR #580 — `KERNEL: make alias_remove identity decisions replay-safe` |
| PR #580 final head | `5d4d43f01bc99729f6d6e577ec33553d9b5249b4` |
| PR #580 merge | `3a52d309a606608c9338147b78e0a2f708084042` |
| PR #580 review cycles | `2` |
| Forensic predecessor | PR #577 — already closed unmerged at `b31bbc32b98c170c44f75de3fa1e8e252e7d0555` on 2026-08-13; preserve as forensic evidence; do not reopen, merge, or extend |
| DungeonMind semantic pin | `be76acc997c5fbcb8ceaa090969ec051afa6051d` |
| Current canonical Eldyrwild observation | `rev:5a7c13ae45c49a65b402920499be72ed`, payload `2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974`; `EVIDENCE_PROVENANCE = 8` |
| Named successor | `cutover-eldyrwild-identity-shadow-alias-remove` |
| Successor handoff | `Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md` |
| What remains false | No Eldyrwild alias has been retired; `EVIDENCE_PROVENANCE` is still 8; Captain/Thrin are not yet packaged; five relationship STOPs remain; DungeonMind existing-world adoption is still blocked |
| Runtime/state ownership | Documentation only. No `out/`, corpus, graph head, revision, contribution, identity ledger, or external DungeonMind mutation |
| Parallel collision | `Docs/Sources/design-agent/**` export-mirror work is independent and non-authoritative; do not refresh or edit it here |
| Post-merge action | Re-anchor to the sync merge SHA → confirm PR #577 remains closed unmerged → dispatch exact-six successor from that merged descendant |

### PR #580 completion evidence to record truthfully

Record:

```text
PR: #580
head: 5d4d43f01bc99729f6d6e577ec33553d9b5249b4
merge: 3a52d309a606608c9338147b78e0a2f708084042
review cycles: 2
```

Verification provenance must remain truthful:

```text
author-local focused verification:
  47 focused tests passed
  Ruff clean on repair paths
  git diff --check clean

GitHub Actions / commit-status evidence:
  none attached to reviewed head

tests/test_graph_kernel_boundaries.py:
  base: 4 failed, 4 passed
  head: 4 failed, 4 passed
  same four failures pre-existing outside #580 changed paths
```

Do **not** rewrite that as “CI green.”

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owner |
|---|---|---|---:|---|
| Campaign Supergraph tracker | Kernel `READY`; six-alias slice `BLOCKED` | Kernel `DONE`; exact-six slice `READY` | Yes | tracker |
| World Graph continuity status | Kernel described as active next CUTOVER slice | Exact-six application described as active next dependent slice | Yes | status guide |
| Kernel handoff | Still carries pre-dispatch/design-ready status | Historical/completed: PR #580 merged, 2 review cycles, do not redispatch | Yes | completed handoff |
| Active backlog | Completed Kernel capability remains `[READY]` | Kernel item removed from active backlog; exact-six is immediate Case-C action | Yes | backlog |
| Backlog archive | No #580 completion entry | Completed Kernel item preserved under `[DONE]` | Yes | archive |
| Successor dispatch | No dedicated exact-six handoff | Complete bounded CUTOVER handoff exists | Yes | successor handoff |
| `EVIDENCE_PROVENANCE` | 8 | Still 8 in this PR | Yes | all current-state docs |
| PR #577 | Closed unmerged forensic STOP | Remain closed unmerged; do not reopen or extend | Yes | GitHub post-merge confirmation |

### Adversarial sequences

| Sequence | Required safe outcome | Proof |
|---|---|---|
| Tracker changes to exact-six READY → status still says Kernel next | Merge blocked | authority scan |
| Kernel handoff marked DONE → backlog still says dispatch Kernel | Merge blocked | backlog scan |
| Successor handoff says expected 8→2 → docs accidentally state 2 already | Merge blocked | current-state scan |
| Successor handoff includes Captain/Thrin removal | Merge blocked | exact keeper proof |
| Successor handoff changes generic `merge_identity()` semantics | Merge blocked | successor contract inspection |
| Parallel source-export PR moves `main` before dispatch | Re-anchor; do not edit export copies; proceed only if canonical write lease remains compatible | base/lane inspection |
| State sync merges → PR #577 reopened or extended | Keep #577 closed unmerged; do not treat it as an implementation lane | steward post-merge re-anchor |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md` | Authority for this atomic documentation slice |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Record #580 DONE and exact-six READY |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` | Make current operational state agree with tracker |
| Modify | `Docs/Plans/HANDOFF-KERNEL-alias-remove-identity-decision.md` | Close the implemented Kernel capability truthfully |
| Modify | `Backlog.md` | Remove completed Kernel READY item; make exact-six the immediate active Case-C action |
| Modify | `Backlog-DONE.md` | Preserve the completed Kernel item as DONE |
| Create | `Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md` | Complete dispatch contract for the exact-six successor |

**Bounded discovery exception:** None.

A required eighth path is a stop condition.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Stable phase-level authority; tracker already owns exact sequencing. No ceremonial PR journaling. |
| `Docs/Design/ARCHITECTURE-campaign-supergraph.md` | Architecture did not change. |
| `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-575.md` | Already `SUPERSEDED / DO NOT DISPATCH`; historical forensic handoff, not mutable current state. |
| `Docs/Design/INDEX-design-agent-source-set.md` | Separate source-export lane owns current changes here. |
| `Docs/Sources/design-agent/**` | Non-authoritative export mirror; separate active lane. |
| `src/graph_memory/**` | PR #580 implementation is already merged. |
| `apps/live_control_server/**` | Exact-six implementation belongs to successor. |
| `scripts/apply_eldyrwild_*` | Successor only. |
| `tests/**` | Successor implementation proof only. |
| `out/**`, `corpus/**`, canonical World Graph | This PR is non-publishing documentation. |
| Captain / Thrin alias package | Blocked until exact-six live/replay exit proves 8→2. |
| Five dual-sense relationship STOPs | Separate package-construction/migration decisions. |
| DungeonMind adoption seam / Case B | Still blocked. |
| Closing PR #577 | Already closed unmerged; post-merge confirmation only, not a Git/content mutation inside this PR. |

## §6 Implementation contract

### A. Required state transition

The tracker must end with the equivalent of:

```text
kernel-alias-remove-identity-decision = DONE
  PR #580
  head 5d4d43f01bc99729f6d6e577ec33553d9b5249b4
  merge 3a52d309a606608c9338147b78e0a2f708084042
  review cycles = 2

cutover-eldyrwild-identity-shadow-alias-remove = READY
  depends on merged #580
  exactly six merge-shadow aliases
  no generic Kernel semantics
  no Captain/Thrin removal
  expected observation after governed live/replay exit:
    EVIDENCE_PROVENANCE 8 → 2

cutover-alias-assertion-package-after-shadow-alias-remove = BLOCKED
  depends on exact-six slice DONE,
  including canonical live publication + replay proof
```

The tracker dispatch order must become:

```text
this state-sync merges
→ re-anchor
→ confirm PR #577 remains closed unmerged
→ dispatch exact-six successor from current main
→ review every distinct head
→ merge
→ re-anchor live world
→ preflight
→ explicit governed live publication
→ replay/exit proof
→ atomic state-authority sync
→ remeasure expected EVIDENCE_PROVENANCE 8 → 2
→ only then dispatch Captain + Thrin package
```

### B. Continuity-status transition

The status guide must state that:

- PR #580 is completed Kernel authority.
- The active dependent CUTOVER capability is exact-six Eldyrwild alias retirement.
- No Eldyrwild mutation occurred in #580.
- `EVIDENCE_PROVENANCE` remains 8 before the successor live apply.
- The expected successor observation is 8→2, not an already-achieved count.
- Captain and Thrin Branchborn remain independently source-supported keepers.
- Five dual-sense relationship STOPs remain untouched.
- `CUTOVER_NOT_READY` remains the disposition.

### C. Kernel handoff completion

Change the Kernel handoff status to the equivalent of:

```text
DONE / HISTORICAL — implemented by PR #580.
Do not redispatch.

final head: 5d4d43f01bc99729f6d6e577ec33553d9b5249b4
merge: 3a52d309a606608c9338147b78e0a2f708084042
review cycles: 2
```

Add a concise completion record preserving the verification caveat from §2.

Do not rewrite its design history or convert it into the Eldyrwild application handoff.

### D. Backlog transition

Remove this active item from `Backlog.md`:

```text
[READY] KERNEL replay-safe alias_remove before alias-package
```

Archive it newest-first in `Backlog-DONE.md` as:

```text
[DONE] KERNEL replay-safe alias_remove before alias-package
```

Its outcome must identify PR #580, merge SHA, 2 review cycles, replay-safe public `remove_identity_alias`, and the fact that no Eldyrwild mutation occurred.

Update the active Case-C / `EVIDENCE_PROVENANCE` item so its immediate action is:

```text
dispatch exact-six governed Eldyrwild alias_remove application
→ prove live/replay EVIDENCE_PROVENANCE 8→2
→ then package Captain + Thrin Branchborn
```

### E. Successor handoff — exact authority

Create:

```text
Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md
```

Do **not** put a PR number in its filename or branch.

Suggested successor branch:

```text
cutover/eldyrwild-identity-shadow-alias-remove
```

Suggested successor PR title:

```text
CUTOVER: retire Eldyrwild identity-shadow aliases
```

The successor mission must be:

```text
Apply exactly six governed alias_remove identity decisions to the current
Eldyrwild world so that merge-shadow aliases cease to be current identity
truth while all merge history, redirects, source authority, evidence,
independently supported aliases, and replay semantics remain intact.
```

Its merge-ready invariant must require one coherent package that:

1. operates on the actual current Eldyrwild parent;
2. removes exactly six named current aliases through public `remove_identity_alias`;
3. preserves original merge decisions and merge side effects;
4. preserves redirects and merged-away identities;
5. preserves contributions, evidence, and source artifacts;
6. refuses any independently supported alias;
7. preserves `Captain` and `Thrin Branchborn`;
8. reconstructs the cleaned state through full contribution + identity replay;
9. exact-retries as already applied / no-op;
10. leaves relationship inventories unchanged;
11. does not claim DONE until the canonical live exit is proven after merge.

### F. Exact six successor targets

The successor handoff must contain this exact table:

| Survivor | Remove exact alias | Merged-away source | Introducing merge decision | Derived store key |
|---|---|---|---|---|
| `item_foot_of_statue` | `Enormous boulder` | `item_enormous_boulder` | `identity-decision:622b690ffe07c2c6` | `enormous boulder` |
| `loc:chilled_warehouse` | `the last warehouse` | `loc:last_warehouse` | `identity-decision:1ff8bf27a0b1921c` | `the last warehouse` |
| `loc:crooked-retort` | `Merchant’s Crossroads apothecary` | `organization:merchant-s-crossroads-apothecary` | `identity-decision:adab1e19800e24d7` | `merchant’s crossroads apothecary` |
| `loc:the-council` | `Council headquarters` | `item:session11:council-headquarters` | `identity-decision:3a8965f409e85911` | `council headquarters` |
| `loc:underground-entrance` | `A second underground entrance is discovered` | `mystery:session9:second_underground_entrance` | `identity-decision:c7f1cab745c8a1d2` | `a second underground entrance is discovered` |
| `obj:session9:scroll_abyssal` | `A scroll written in a strange language is found` | `mystery:session9:scroll_in_strange_language` | `identity-decision:ac8e5efc25de3804` | `a scroll written in a strange language is found` |

### G. Exact keepers

The successor handoff must explicitly protect:

```text
node:captain-lysandra-ironveil
alias: Captain
source assertion: assertion:2a63c5992970e366
source contribution: contribution:a4231edb9a228963
source SHA: 2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c

node:thrin-branchborn
alias: Thrin Branchborn
source assertion: assertion:1275811e41cbb14c
source contribution: contribution:a4231edb9a228963
source SHA: 2cf28604655f23e43846e389e5dce9920f98dfd670a0717ca3bf12e48703380c
```

Attempting to remove either is a test failure and scope violation.

### H. Successor preflight — fail closed

Before package construction or any live write, successor must prove against the **actual current world head**:

1. all six survivor IDs exist and are current canonical identities;
2. each exact alias is currently materialized on its survivor;
3. each introducing merge decision exists;
4. each merged-away source redirects as expected;
5. no active current `node` or `alias` assertion independently supports any of the six aliases;
6. Captain and Thrin Branchborn retain independent active support;
7. no prior active `alias_remove` already retired any of the six;
8. the operation's expected parent is the actual current head.

Any drift is:

```text
STOP
→ remeasure
→ return to stewardship
```

Never “repair until green.”

### I. Successor implementation/write boundary

The successor handoff should lease only the bounded application seam:

```text
Create apps/live_control_server/services/eldyrwild_identity_shadow_alias_remove.py
Create scripts/apply_eldyrwild_identity_shadow_alias_remove.py
Create tests/test_eldyrwild_identity_shadow_alias_remove.py
```

No generic Kernel file belongs in the successor lease.

If the current governed real-world publication seam proves that one additional persisted policy/artifact path is structurally required, that is a stop/re-design signal. Do not silently invent a new durable representation.

The successor implementation model is:

```text
build bounded application package
→ prove on isolated temp clone
→ review every distinct head
→ merge
→ re-anchor current live world
→ rerun complete preflight
→ explicit live apply with expected-parent CAS
→ replay from durable contribution + identity authority
→ verify exact live exit
→ retry proof
→ state-authority sync
```

### J. Successor expected live exit

Expected, but never forced:

```text
EVIDENCE_PROVENANCE: 8 → 2

remaining:
  Captain
  Thrin Branchborn
```

The live proof must additionally establish:

- six and only six aliases retired;
- their alias-index entries disappear only when no surviving legitimate surface produces them;
- original merge records remain semantically/byte-equivalent in historical fields;
- redirects remain active;
- merged-away nodes remain historical/merged-away;
- contribution/evidence/source authority unchanged;
- full replay reconstructs the cleaned head;
- exact retry is no-op/already-applied;
- relationship inventories unchanged.

## §7 Evidence required to merge this documentation PR

| Guarantee | Owner | Evidence | Expected | Stop |
|---|---|---|---|---|
| PR #580 recorded as completed | tracker + Kernel handoff | exact text inspection | DONE, correct SHAs, 2 cycles | stale READY remains |
| Exact-six successor is next | tracker + status | positive/negative scan | READY/active next | Kernel still described as next |
| No fake world transition | tracker + status | count scan | `EVIDENCE_PROVENANCE = 8` remains current | any current claim of 2 |
| Backlog lifecycle correct | backlog pair | status scan | Kernel absent from active; present DONE archive | duplicate active READY |
| Successor target set exact | successor handoff | deterministic content check | all six once; both keepers | missing/extra/keeper removal |
| Stable docs untouched | diff | path review | roadmap/architecture unchanged | ceremonial churn |
| Parallel export lane isolated | diff | path review | no `Docs/Sources/design-agent/**`, no source index | collision |
| Scope exact | Git diff | allowlist | only §4 paths | eighth path |

Run:

```bash
git merge-base --is-ancestor \
  3a52d309a606608c9338147b78e0a2f708084042 HEAD

uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md \
  --local-only

rg -n \
  'kernel-alias-remove-identity-decision.*DONE|cutover-eldyrwild-identity-shadow-alias-remove.*READY' \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md

! rg -n \
  'kernel-alias-remove-identity-decision.*READY|cutover-eldyrwild-identity-shadow-alias-remove.*BLOCKED' \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md

! rg -n \
  'Active CUTOVER slice: `kernel-alias-remove-identity-decision`|Kernel `alias_remove` primitive is the next bounded slice|start `kernel-alias-remove-identity-decision`' \
  Docs/Design/STATUS-world-graph-continuity-spine.md

! rg -n \
  '^## \[READY\] KERNEL replay-safe alias_remove before alias-package' \
  Backlog.md

rg -n \
  '^## \[DONE\] KERNEL replay-safe alias_remove before alias-package' \
  Backlog-DONE.md

python - <<'PY'
from pathlib import Path

p = Path("Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md")
text = p.read_text()

required = [
    "item_foot_of_statue",
    "Enormous boulder",
    "identity-decision:622b690ffe07c2c6",
    "loc:chilled_warehouse",
    "the last warehouse",
    "identity-decision:1ff8bf27a0b1921c",
    "loc:crooked-retort",
    "Merchant’s Crossroads apothecary",
    "identity-decision:adab1e19800e24d7",
    "loc:the-council",
    "Council headquarters",
    "identity-decision:3a8965f409e85911",
    "loc:underground-entrance",
    "A second underground entrance is discovered",
    "identity-decision:c7f1cab745c8a1d2",
    "obj:session9:scroll_abyssal",
    "A scroll written in a strange language is found",
    "identity-decision:ac8e5efc25de3804",
    "node:captain-lysandra-ironveil",
    "Captain",
    "assertion:2a63c5992970e366",
    "node:thrin-branchborn",
    "Thrin Branchborn",
    "assertion:1275811e41cbb14c",
]

missing = [value for value in required if value not in text]
assert not missing, missing
assert "EVIDENCE_PROVENANCE: 8 → 2" in text
PY

git diff --check

git diff --name-only \
  71d11169cc56880ed09f457ddd9a6069429d0b96...HEAD
```

The ancestor check remains against design base `3a52d309…`. The changed-path inventory must use the actual dispatch base `71d11169…`. Diffing against the design base would mix in the independent `Docs/Sources/design-agent/**` export-mirror commits that advanced `origin/main` after PR #580; those paths are out of this lease.

`scripts/steward_preflight.py --local-only` reports `status=block` because three historical handoffs still say `**Status:** ACTIVE` and lease `Backlog.md`, `Backlog-DONE.md`, or the campaign-supergraph tracker:

- `HANDOFF-BUILD-dogfood-polish-plan-session-affinity-workspace-drafts.md`
- `HANDOFF-c2s23-mireward-siege-clocks-threats.md`
- `HANDOFF-pr011a3-confirm-durable-reload-session25-dogfood.md`

Those are not current CUTOVER lanes. PR011A3 already merged as #366; DOGFOOD-POLISH is closed; C2S23 Mireward is campaign-prep from 2026-06. No open PR owns those leases. Do not edit those handoffs in this slice to make preflight green.

Expected changed-path set:

```text
Backlog-DONE.md
Backlog.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md
Docs/Plans/HANDOFF-DOCUMENTS-cutover-alias-remove-state-sync.md
Docs/Plans/HANDOFF-KERNEL-alias-remove-identity-decision.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
```

### Minimal live proof

Not applicable — this PR must not mutate Eldyrwild or any runtime state.

### Baseline failures

Not applicable to runtime tests. Negative stale-state scans are expected to fail on the design base because repairing those exact stale claims is this PR's purpose.

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/head SHA.
2. Exact dispatch/base SHA actually used.
3. Confirmation PR #580 is still merged at expected head/merge.
4. Confirmation PR #577 remained unmerged and was not extended.
5. Actual changed paths versus §4.
6. Exact tracker state transition.
7. Exact continuity-state transition.
8. Kernel handoff completion record and verification provenance.
9. Backlog active→archive transition.
10. Successor handoff exact-six content check.
11. Confirmation `EVIDENCE_PROVENANCE` is still 8 in current state.
12. Confirmation roadmap, architecture, source-export mirror, graph code, corpus, and live world were untouched.
13. All §7 command results and provenance.
14. Paths outside §4: `none` or STOP.
15. Named successor still unimplemented.

## §9 Acceptance rubric

- [ ] Exactly one capability is delivered: post-#580 CUTOVER state authority is coherent and dispatchable.
- [ ] PR #580 is `DONE` everywhere that currently owns its status.
- [ ] PR #580 is recorded with head, merge SHA, 2 review cycles, and truthful verification provenance.
- [ ] The exact-six Eldyrwild alias retirement is `READY`.
- [ ] The remaining two-alias package remains `BLOCKED`.
- [ ] Current `EVIDENCE_PROVENANCE` remains 8; 8→2 is explicitly only the successor expectation.
- [ ] Captain and Thrin Branchborn are protected in the successor handoff.
- [ ] The successor handoff contains exactly the six merge-shadow targets and fail-closed preflight.
- [ ] The successor uses public `remove_identity_alias`; generic Kernel semantics remain out of scope.
- [ ] Completed Kernel backlog work moved from active backlog to DONE archive.
- [ ] No roadmap/architecture ceremonial churn occurred.
- [ ] No non-authoritative source-export mirror was refreshed or edited.
- [ ] No graph/corpus/live-world mutation occurred.
- [ ] Actual changed paths equal §4.
- [ ] Every distinct review head received a counted formal review judgment before merge.

## Post-merge steward action

After this PR merges:

```text
1. fetch/re-anchor current main
2. verify this full state-sync set on the merge commit
3. confirm PR #577 remains closed unmerged; if reopened, close it again with a pointer to:
     PR #580 merged Kernel authority
     HANDOFF-CUTOVER-eldyrwild-identity-shadow-alias-remove.md
4. confirm no intervening CUTOVER authority changed
5. dispatch exact-six successor from that merged main SHA
```

PR #577 was already closed unmerged at `b31bbc32b98c170c44f75de3fa1e8e252e7d0555` on 2026-08-13. Confirming that remains closed is not optional cleanup; it prevents the forensic branch from remaining a plausible implementation lane.

Do not dispatch Captain/Thrin packaging.

## Stop conditions

Stop rather than expanding if:

- PR #580 merge/head facts differ from the recorded predecessor.
- `main` has advanced with changes to any §4 canonical authority.
- another active lane owns a §4 path.
- the roadmap or architecture actually requires semantic modification to make the transition truthful.
- exact-six dispatch requires generic Kernel changes.
- an exact target/keeper fact differs from current authority.
- successor implementation requires an unplanned durable/public representation.
- a worker proposes direct graph JSON cleanup.
- a worker proposes removing Captain or Thrin.
- a worker proposes packaging all eight aliases.
- a worker proposes reclassifying the six as `SOURCE_MIGRATION_HISTORY`.
- a worker proposes relationship cleanup or Case B adoption work.
- any file outside §4 is required.