# HANDOFF — STEWARDSHIP: finish SURFACE-INTEGRATION

**Created:** 2026-09-03  
**Status:** COMPLETE — SI-6 ACCEPTED; SURFACE-INTEGRATION CLOSED; SI-7 re-sequenced to DOGFOOD-CONTINUITY DFC-1  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Starting Buddy anchor:** `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb` — merge of PR #681  
**Completed predecessor:** SI-5B / PR #681, accepted implementation head `d0e9aaa80a78f71ad6bfd2195002eb5de67f098f`, merge `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb`, three formal review cycles  
**Agent disposition:** PR #674 CLOSED/SUPERSEDED (not merged) at final head `c194c70947780d5248f938421615b28a262d7d37`  
**SI-6 report:** [`../Reports/REPORT-surface-integration-si6-clean-start.md`](../Reports/REPORT-surface-integration-si6-clean-start.md) — ACCEPTED; PR #682 merge `86296a4021816862b1ee82cbf7478b2882493963`; accepted witness head `9349cb4b64d8a4849c4f379277ddb15df1fdc81a`; two formal review cycles  
**One-line mission:** finish the already-committed SURFACE-INTEGRATION program, prove the assembled product, dispose the parked Agent lane deliberately, synchronize authority, and stop; do not use closure work as permission to expand the product.

**Completion record (2026-09-04):**

```text
PR #682               merged @ 86296a4021816862b1ee82cbf7478b2882493963
accepted witness head 9349cb4b64d8a4849c4f379277ddb15df1fdc81a
formal review cycles  2 (RC2 review 5109075232)
SI-6 judgment         ACCEPTED
SURFACE-INTEGRATION   CLOSED
SI-7                  DONE — thaw/re-sequence → DOGFOOD-CONTINUITY DFC-1
feature freeze        lifted
next sequence         DFC-1 (not claimed done here)
```

---

## §1 Finish line

This stewardship mission exists to **close** SURFACE-INTEGRATION, not to discover a new architecture program.

It ends only when all of the following are true:

```text
SI-1 through SI-5B                  DONE / merged
remaining SI-5 Play/Combat seams    explicitly disposed
PR #674 / Agent disposition         explicit and current
SI-6 clean-start assembled witness  ACCEPTED
SURFACE-INTEGRATION                 CLOSED as blocking program
feature-freeze state                synchronized truthfully
next product sequence               re-anchored from CON-READY
```

The invariant for the rest of the mission is:

> **Do the minimum work required for every surface used by the SI-6 witness to observe the authority it actually depends on truthfully, then run the witness. A nearby architectural improvement, cleanup opportunity, richer capability, or future magic moment is not part of this mission unless the SI-6 owning-boundary evidence fails without it.**

The feature freeze applied for the duration of this mission and was **lifted upon SI-6 acceptance**:

> **No DungeonBuddy feature thaw before SI-6 acceptance.** *(historical mission law — satisfied and lifted)*

Do not convert “finish SURFACE-INTEGRATION” into “adopt Surface Information everywhere.” The contract is a tool for truthful observations, not a migration quota.

---

## §2 Read these pillars before selecting any more work

The next steward should be able to continue from repository authority without reconstructing this conversation.

### Pillar 1 — repository process and evidence

1. [`AGENTS.md`](../../AGENTS.md)
2. [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)

Governing consequences:

- re-anchor before every dispatch and review;
- one independently useful capability per slice;
- the HANDOFF §4 allowlist is an exclusive write lease;
- no silent scope expansion;
- evidence must live at the owning boundary;
- a cycle ends only after merge **and** state-authority synchronization;
- stable architecture/contracts do not churn merely because a PR merged.

### Pillar 2 — product acceptance, not architecture completion

1. [`Docs/Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)
2. [`Docs/Roadmaps/ROADMAP-surface-integration.md`](../Roadmaps/ROADMAP-surface-integration.md)
3. [`Docs/Reports/REPORT-of-conks-end-to-end-dogfood.md`](../Reports/REPORT-of-conks-end-to-end-dogfood.md)

CON-READY is the GM-visible acceptance authority. SURFACE-INTEGRATION exists because Of Conks demonstrated that individually green stations can still assemble into an untrustworthy product.

Do not replace CON-READY user stories with a new architecture checklist. SI-6 is a forcing function for the product, not an excuse to perfect every subsystem.

### Pillar 3 — Surface Interaction and Surface Information are separate

1. [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)
2. [`Docs/Design/CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md)

Keep the distinction exact:

```text
Surface Interaction
  structural capabilities / commands / chrome publication

Surface Information
  changing observations from one authority
```

Changing observations do not belong in structural AppChrome publication. One information channel observes one projection from one authority. Do not create a universal information store, `mixed` authority, or second product-wide provider registry to “finish adoption.”

### Pillar 4 — authority stays where the domain owns it

1. [`Docs/Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md)
2. [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
3. [`Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md)

Current post-cutover authority model:

```text
DungeonMind
  durable World identity, revision/head, provenance/evidence,
  scoped World projection/retrieval, governed World publication

Buddy APP-STATE
  durable Buddy work/runtime state, including Plan/Runbook/Run
  and canonical ExtractionRun lifecycle

Source storage
  readable source bytes where source contracts point

Mechanics
  exact mechanics authority

Combat
  Combat-owned runtime/state

Agent
  invocation/context/trace behavior; never World or Play authority
```

A Surface should know what it is observing, which authority supplied it, whether it is current/usable, and why it is unavailable. It should not know or infer the storage topology behind that authority.

### Pillar 5 — exact identity, fail-closed behavior, and assembled-runtime proof

Carry forward the lessons already paid for in SI-1 through SI-5B:

- exact identity beats labels/paths/latest inference;
- `EMPTY`, `UNAVAILABLE`, `INTEGRITY_ERROR`, and `STALE` are materially different truths;
- refresh/retry must not authorize old observations;
- worktree file absence must not masquerade as product absence;
- runtime excision and physical deletion are different proof obligations;
- helper tests cannot prove an assembled browser/runtime workflow;
- reload/restart evidence matters whenever the product depends on durability.

Do not invent permissive fallbacks to make SI-6 pass.

---

## §3 Current truth at handoff

Re-anchor these facts before acting; repository/GitHub truth wins if they moved.

```text
Buddy main (stewardship tip after SI-5B sync)
  5e192966ae2086267569a7dbc5397852b7735550
  (contains #681 merge 9d8c8a51… + finish-only handoff/sync)

SI-1   DONE  #675
SI-2   DONE  #676
SI-3   DONE  #677
SI-4   DONE  #679
SI-5A  DONE  #680
SI-5B  DONE  #681

PR #681
  accepted head        d0e9aaa80a78f71ad6bfd2195002eb5de67f098f
  merge                9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb
  formal review cycles 3

PR #674
  CLOSED / SUPERSEDED (disposition A)
  final head           c194c70947780d5248f938421615b28a262d7d37
  closed               2026-09-04 — not merged; A8 Play Ask deferred past SI-6

remaining program truth
  SI-5 remainder  DONE (no SI-5C/D code slices)
  SI-6 witness    ACCEPTED — PR #682 merge 86296a4021816862b1ee82cbf7478b2882493963
                  accepted witness head 9349cb4b64d8a4849c4f379277ddb15df1fdc81a
                  formal review cycles 2 (RC2 review 5109075232)
  SI-7 thaw       DONE — freeze lifted; next sequence → DOGFOOD-CONTINUITY DFC-1
  SURFACE-INTEGRATION  CLOSED
```

### Phase B disposition table (2026-09-03 / tip `5e192966…`)

| path / observation | authority | delivery | truthful? | required for SI-6? | code? |
|---|---|---|---|---|---|
| Play active run / progress / pinned revision | APP-STATE `play.*` | live Play API → page state | yes | yes (#5,#8) | **no** |
| Play Agent current-moment pointers | APP-STATE + A7 resolver | Surface Interaction agentContext | yes (fail-closed) | yes (#7) | **no** |
| Play Ask (#674 A8) | would add Ask transport | absent on main; PR parked/closed | N/A | **no** (firewall) | **no** — CLOSE/SUPERSEDE |
| Combat in Play / primary SI-6 journey | — | not consumed | N/A | **no** | **no** |
| `/surface` Combat roster (disabled) | Combat session JSON | direct REST | yes when used | **no** | **no** |
| Ingest catalog (SI-5B) | APP-STATE `ingest.run` + SI channel | already on main | yes | yes (#4) | **no** |
| Plan/Build World information | DungeonMind + SI channels | already on main (SI-3/SI-5A) | yes | yes (#2,#3) | **no** |

**Phase C:** zero implementation slices. Proceed to Phase D (SI-6).

### What SI-5B specifically established

Normal `/ingest` now starts from canonical APP-STATE `ingest.run` rows, observes the catalog through Surface Information, and selects by exact `run_id`. Legacy manifest/file/Gold data cannot create product run identity. REVIEWABLE ordinary Load reaches exact review; PROMOTED remains visible terminal history but exact historical inspection requires a later neutral inspection seam.

That PROMOTED inspection seam is a **named future issue, not a SURFACE-INTEGRATION closure requirement**, unless SI-6 demonstrates that the acceptance journey actually requires it.

---

## §4 Mission phases

This is a stewardship mission across the remaining closure work. Do **not** put everything below into one PR.

### Phase A — close SI-5B state authority before new dispatch

After re-anchoring, synchronize documents that still claim SI-5B is active/current.

Minimum set to inspect:

```text
Docs/Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md
Docs/Roadmaps/ROADMAP-surface-integration.md
this stewardship handoff
```

Required completion truth:

```text
SI-5B                 DONE
PR                    #681
accepted head         d0e9aaa80a78f71ad6bfd2195002eb5de67f098f
merge                 9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb
formal review cycles  3
current mission       finish-only SI-5 remainder → SI-6
```

Do not open a ceremonial docs-only PR for routine sync. Use the direct guarded steward mechanism unless a real dependent implementation slice is already being authored and can truthfully carry the backward sync.

### Phase B — characterize the remaining SI-5 seams before designing code

Inspect the assembled current `main`, not stale roadmap shorthand.

The question is **not** “where else can Surface Information be adopted?” The question is:

> **Which changing observations used by the SI-6 browser journey are still delivered through a false authority, structural-publication reactivity, hidden reconstruction, stale fallback, or ambiguous identity?**

Characterize only these areas:

#### B.1 Play-facing observations

Trace the current Play route and Current Moment path.

Check:

- current Run / pinned Playable revision;
- current Beat / Scene;
- contextual object/mechanics pointers used by the live surface;
- reload/restart behavior;
- any dynamic observation currently being smuggled through structural Surface Interaction publication.

If current Play already consumes APP-STATE truthfully and no changing observation crosses the wrong boundary, record **NO NEW SI CHANNEL REQUIRED**. Do not manufacture an adoption PR.

#### B.2 Combat-facing observations

Trace only the Combat information actually surfaced during the planned SI-6 journey.

Combat remains Combat-owned. Determine whether Play/Surface chrome currently:

- observes Combat state through a truthful Combat-owned seam;
- reconstructs it from another domain;
- embeds changing Combat data structurally;
- or does not depend on changing Combat information at all for SI-6.

If the witness does not require a new Combat-facing observation contract, do not broaden this mission into Combat redesign or persistence work.

#### B.3 Agent / PR #674 disposition

PR #674 is historical implementation evidence, not a current implementation authority. It was designed before the Surface Information program and its base is stale.

Re-review its intended product story against current `main` and the pillars above. Choose exactly one disposition:

```text
A. CLOSE / SUPERSEDE
   The old implementation no longer matches current authority or product shape.
   Preserve useful design/evidence in a fresh narrow handoff only if still needed.

B. REBRIEF
   The user story remains required, but current architecture changes the implementation.
   Close/leave parked #674 and author one fresh SURFACE-INTEGRATION closure slice.

C. REVALIDATE EXACTLY
   Only if the cumulative diff still matches current authority and can be proven
   against current main without reviving stale assumptions.
```

Do not casually rebase #674 until it merges. Do not extend it just to empty the PR queue.

The required closure outcome is an **explicit disposition**, not necessarily merged Agent code.

### Phase C — implement only proven closure gaps

Default expectation: **zero to two** implementation slices before SI-6.

Possible shape, only if Phase B evidence requires it:

```text
SI-5C  one Play/Combat-facing truthful-observation correction
SI-5D  one current Agent/#674 disposition implementation
```

These labels are placeholders, not mandatory work.

A third implementation slice is justified only when an owning-boundary failure proves that one invariant cannot govern the existing candidate slice. “While we are here” is not evidence.

Each implementation slice must:

- have one merge-ready invariant;
- name exact current authority and predecessor;
- use a narrow §4 write lease;
- state what remains false afterward;
- preserve the SI-6 freeze;
- include exact owning-boundary evidence;
- carry backward-looking state sync for its predecessor.

### Phase D — run SI-6 as soon as the known falsehoods are disposed

Do not defer SI-6 for polish.

SI-6 is the acceptance gate:

```text
canonical assembled runtime
  → operator preflight
  → browser journey
  → exact authority-backed information
  → hard reload
  → process restart where durability is claimed
  → same usable product context without worktree reconstruction
```

Start with the canonical operator check:

```bash
uv run python scripts/preflight_surface_runtime.py
```

Use `--require-world <world_id>` when the witness world is known.

The steward should author one bounded SI-6 witness plan/report from current CON-READY stories rather than a new feature roadmap. Prefer the existing convention/Of Conks forcing material if it still exercises the product honestly.

At minimum the witness must prove the assembled product can distinguish and survive the authority conditions that triggered SURFACE-INTEGRATION:

1. World authority is found through the supported DungeonMind runtime configuration, not guessed from local files.
2. Plan graph information remains reactive without structural-publication churn.
3. Build exact graph reads use the same truthful World information contract.
4. Ingest run existence/selection comes from APP-STATE and survives a fresh checkout/hard reload without `out/` authority.
5. Play resumes the durable current moment from APP-STATE rather than reconstructing it from authored files.
6. Any Combat information relied upon by the journey remains Combat-owned and truthfully available/unavailable.
7. Agent behavior used by the journey has an explicit current disposition and does not independently reconstruct competing World/Play truth.
8. Unavailable/integrity states fail visibly; no retired Buddy graph/file fallback silently makes the demo look healthy.

If SI-6 discovers a blocker, create the **smallest witness-enabling repair slice**, merge it, and rerun SI-6. Do not turn the witness into a backlog-mining session.

### Phase E — close the blocking program and thaw deliberately

After SI-6 acceptance, synchronize all active state authorities together.

Required end state:

```text
SI-5 remainder        DONE / explicitly disposed
SI-6                  ACCEPTED
SURFACE-INTEGRATION   CLOSED
feature freeze        lifted only by this accepted state
SI-7                  state-sync/re-sequencing step, not a feature PR
CON-READY             again owns next product sequence
```

Then re-anchor the paused roadmaps and select the next product capability from CON-READY. Do not automatically resume the oldest paused branch or handoff.

---

## §5 Scope firewall — deliberately not part of finishing SURFACE-INTEGRATION

These may be valuable. They are not closure work unless SI-6 directly fails without them.

```text
PROMOTED historical exact-inspection resolver
BF3C / additional Play At-a-Glance categories
Roll interaction extraction
Encounter extraction
new Combat features or broad Combat persistence redesign
source-relative asset productization
additional Ingest UX/extraction capability
Gold/evaluation redesign
GraphIngest compatibility-packaging demolition
SourceArtifact/blob authority redesign
Source→World contextual magic moment
richer Agent Surface capability
model/token/cost/step telemetry program
Agent harness replacement or Hermes/Pi redesign
new global Surface Information registry
new universal Surface provider/store
new DungeonMind contract or schema merely for UI convenience
```

If one of these is interesting while closing the program, put it in backlog/notes or the post-SI-6 re-sequencing discussion. Do not absorb it.

---

## §6 Finish-first decision rules

Before authoring any remaining implementation handoff, answer these in order:

1. **Does SI-6 fail without this change?** If no, defer it.
2. **Is the current product lying about authority, currentness, identity, or availability?** If no, do not refactor merely for uniformity.
3. **Can an existing authority/contract already express the needed truth?** Reuse it; do not add another abstraction.
4. **Is this one independently useful/revertible correction?** If no, split.
5. **Does the change introduce a second durable/public contract?** Stop/rebrief.
6. **Would the change touch a stable authority document whose claims did not change?** Do not churn it.
7. **Would the change make the final SI-6 witness materially broader?** Default to no.

A useful closure sentence for every candidate is:

> “Without this change, SI-6 cannot truthfully prove ______ because ______.”

If that sentence cannot be completed with repository/runtime evidence, it is not current closure work.

---

## §7 Review and evidence expectations

For every remaining implementation PR:

- review the cumulative diff against one exact head;
- reconcile every changed path to the handoff lease before judging behavior;
- trace success, empty/miss, unavailable, integrity, stale/superseded, retry, and reload paths where applicable;
- check exact identity and late-response/lease safety;
- demand owning-boundary evidence rather than helper-only assertions;
- compare head/base when a required suite has existing failures;
- count formal review cycles exactly;
- do not merge without explicit user instruction.

For SI-6 itself, evidence should be assembled-product evidence. Unit tests remain supporting proof, not a substitute for the browser/runtime journey.

Expected durable output:

```text
Docs/Reports/REPORT-surface-integration-si6-clean-start.md
```

The report should record:

- exact Buddy main SHA;
- exact DungeonMind consumed/pinned contract state relevant to the witness;
- operator preflight result;
- runtime configuration categories without leaking credentials;
- browser journey steps and observations;
- reload/restart outcomes;
- authority/status failures intentionally exercised;
- any repair PRs required by the witness;
- final acceptance judgment;
- explicit remaining non-blocking product gaps.

Do not hide remaining gaps to obtain a PASS. SI-6 accepts the Surface Information/assembly contract, not the entire CON-READY roadmap.

---

## §8 Mutable authority / closure sync checklist

Inspect only documents that actually claim current state.

During this mission, likely mutable authorities are:

```text
Docs/Roadmaps/ROADMAP-surface-integration.md
Docs/Roadmaps/ROADMAP-con-ready.md
Docs/Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md
this stewardship handoff
any new SI-5C/SI-5D implementation handoffs actually created
final SI-6 report / witness handoff
PR #674 disposition record if its status changes
```

Stable architecture/contracts normally remain unchanged:

```text
Docs/Design/CONTRACT-surface-information-v1.md
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
Docs/Design/ARCHITECTURE-application-state-layer.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Design/ARCHITECTURE-playable-material-and-runtime.md
```

Only edit those if SI-6 proves one of their semantic claims is actually false.

---

## §9 Immediate next actions for the receiving steward

1. Re-anchor current Buddy `main`, open PRs, and #674 exact head/state.
2. Complete the backward SI-5B authority sync if any active document still says SI-5B is current/active.
3. Read the five pillar groups in §2; do not start by browsing random production files.
4. Trace current Play, Combat-facing, and Agent/#674 observable information paths from the SI-6 journey only.
5. Write a short disposition table:

```text
path / observation
current authority
current delivery mechanism
truthful today? yes/no
required for SI-6? yes/no
code change required? yes/no
```

6. If no code is required for one area, record that disposition instead of manufacturing a slice.
7. If code is required, author the smallest implementation handoff and carry it through review/merge/state sync.
8. Run SI-6 at the earliest truthful opportunity.
9. Repair only blockers found by the witness.
10. After SI-6 acceptance, close SURFACE-INTEGRATION and re-sequence from CON-READY.

The default bias from this point forward is **closure over completeness**.
