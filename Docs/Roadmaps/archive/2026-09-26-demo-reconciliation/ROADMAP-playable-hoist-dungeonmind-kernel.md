# ROADMAP — Playable Architecture → Shared Buddy Primitives → DungeonMind Kernel

**Status:** ACTIVE DESIGN ROADMAP — evidence-driven; review on every implementation PR  
**Re-anchored:** 2026-08-26 from `main` `cc016661f80416e0816f56349217cf33c53a195f`  
**Scope:** DungeonMindBuddy Playable/Play implementation, Buddy-shared hoisting, and evidence-driven promotion into DungeonMind / DungeonMindDnD

---

## 0. North star

The graduation path remains:

```text
DOGFOOD / PLAY DOMAIN
prove the GM interaction with real material

        ↓ repeated invariant

DUNGEONBUDDY SHARED PRIMITIVE
hoist product-neutral editor/projection/work-object behavior

        ↓ second-system pressure + governance need

DUNGEONMIND KERNEL OR PROFILE
hoist only authority/context semantics that must be consistent across consumers
```

Central rule:

> **DungeonMind may learn governed operator-authored context, exact identity/revision/provenance, and capability-bounded adoption. It should not learn what a Beat, Scene, Play Object Sheet, Decision card, or Combat panel is.**

The 2026-08-26 re-anchor does not change this hoist philosophy. It changes **delivery order** now that BF1 and APP-STATE AS1–AS5 are complete and C2S27's unexpected-play lesson has been made explicit.

---

## 1. Ownership model

| Concern | Long-term owner | Hoist posture |
|---|---|---|
| Runbook / Beat / Scene / Decision / Consequence semantics | DungeonMindBuddy Playable | keep product-owned |
| Scene-centered cockpit / `At a Glance` / table prioritization | DungeonMindBuddy Play Surface | keep surface-owned |
| Run current position / resolution / selections / notes | DungeonMindBuddy Play Runtime | keep runtime-owned |
| Combat HP / initiative / conditions / encounter runtime | Combat | keep Combat-owned |
| WorkObject / WorkRevision / WorkingCopy / CAS | Buddy Application State / Canvas | shared Buddy primitive already proven |
| stable semantic element addressing | Buddy Canvas/work-object candidate | hoist only when a second consumer requires same contract |
| proposal apply / stale / dirty arbitration | Buddy Canvas/work-object | shared Buddy before kernel consideration |
| typed graph/source/mechanics refs + projection open | existing shared reference/projection seams | reuse/extend |
| D&D exact mechanics attachment semantics | `dungeonmind_dnd` profile | profile-owned |
| World identity/revisions/evidence/governed publication | DungeonMind | kernel authority |
| operator-authored context admission to Agent | DungeonMind candidate | only as generic exact external context |
| Runtime→Playable adoption | Buddy proposal/adoption | product-owned |
| Playable→World promotion | Buddy UI → profile adapter → DungeonMind review/publication | reuse kernel write path |

---

## 2. Promotion test

A behavior may move out of Play only when:

1. real dogfood proved it useful;
2. a second consumer needs the same invariant or divergence creates authority/safety risk;
3. the contract can be named without Play/Beat/Scene/adventure vocabulary;
4. moving creates one owner rather than a second copy;
5. failure semantics are strict/testable;
6. the lower layer does not need presentation/product workflow to enforce it.

For DungeonMind kernel promotion also require:

7. concern is knowledge/context identity, revision, provenance, admission, retrieval, capability policy, or governed promotion;
8. system/game semantics remain in profile/product layers.

If these are not true, keep behavior in Buddy.

---

## 3. Living-roadmap maintenance contract

Every implementation PR dispatched from this roadmap must ask:

> **Did this PR's evidence change ownership, sequence, hoist posture, successor boundary, or assumptions?**

Final review records one disposition:

```text
ROADMAP_REVIEW — UPDATED
```

or

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
```

Rules:

- current phase / next slice must agree with merged repository truth;
- evidence heads and formal reviewed heads may differ when roadmap bookkeeping creates a later SHA;
- do not create cross-repository contracts silently;
- do not hoist because abstraction feels clean; hoist because evidence proves shared ownership.

Detailed historical review-cycle/evidence rows remain available in git history prior to this re-anchor; this file now prioritizes current design authority over carrying an ever-growing implementation diary.

---

## 4. Proven foundation — do not re-sequence as unfinished work

### P1 — durable Playable identity — DONE

Merged foundation:

- P1A Scene/Beat stable identity — PR #590;
- P1B derived structure index — PR #592;
- P1C Choice/Option stable identity — PR #594.

Hoist result: identity remained Play-owned; no independent consumer yet justified a generic kernel element-ref contract.

### P2 — separate Run Runtime — DONE, later migrated to APP-STATE

Merged foundation:

- P2A exact Run→Playable binding — PR #596;
- P2B1 sealed reference manifest — PR #599;
- P2B2 CAS Runtime progress — PR #601;
- P2C preserve-only rebase — PR #612.

Original file-backed topology was later replaced by APP-STATE. Preserve the domain invariants, not the old storage implementation.

### P3A / D1 / D2 — native Play foundations — DONE

- native Runbook admission/table projection — PR #618;
- explicit Start Run — PR #621;
- exact full-document Runbook reference projection — PR #622.

The full Runbook view remains useful reference but is no longer treated as the primary target Play mode.

### P3C — exact Threat mechanics rendering seam — DONE foundation

PR #608 proved surface-neutral exact mechanics hydration/rendering. This now becomes a hot-path dependency for unexpected-play retrieval rather than a deferred nicety.

### Lane A3 / cockpit design — DONE design gate

PR #627 established Beat-first current-moment semantics.

The 2026-08-26 revision keeps its durable structure/Choice contracts but changes projection priority to Scene-centered inside Beat context.

### BF1 — Beat-first v2 grammar / index / manifest — DONE

PR #628 implemented `dmb-playable-element:v2` and `dmb_play_run_reference_manifest_v2`.

BF1 intentionally left v2 READY admission gated for BF2.

### APP-STATE AS1–AS5 — DONE Play persistence foundation

```text
AS1  Plan WorkObjects / immutable WorkRevisions
AS2  Runbook + historical Playable WorkRevisions
AS3  Run + manifest + progress CAS/rebase on PostgreSQL
AS4  active Run / resume continuity on PostgreSQL
AS5  legacy Play filesystem persistence demolished
```

Architectural consequence:

- a Run may read historical revision N after N+1 exists;
- current/latest is not required for admission;
- Play Runtime is not checkout-local;
- `out/runtime/play` is not authority;
- persistence is no longer a reason to postpone BF2/BF3.

---

## 5. Current Play product sequence

### BF2 — v2 READY Runtime + relevance — NEXT structural slice

Primary capability:

- admit sealed v2 Runs to READY;
- deterministically seed new Run `currentBeatId`;
- restore exact historical pinned WorkRevision;
- validate explicit Beat/Scene current-position CAS mutation;
- derive `activates`/`suppresses` emphasis from current selections.

Remains false after BF2: the target Scene-centered cockpit presentation.

No condition/workflow DSL. No new note schema. No Combat ownership change.

### BF3 — Scene-centered current-moment cockpit

Primary capability:

- active Scene central workspace;
- persistent/expandable Beat context;
- truthful Beat-only state;
- authored Decision/Option interaction;
- visible consequence + branch relevance;
- presence-first `At a Glance`;
- inspect versus Make Current;
- Runbook demoted to secondary reference projection;
- notes projected as pinned context using existing capability unless dogfood proves a stronger lifecycle.

BF3 acceptance must include deliberate off-script play.

### BF3.x / P3 — fast contextual + global object retrieval

This may be part of BF3 if small enough, otherwise an immediately adjacent independently useful slice.

Required proof:

```text
current Scene A1
→ inspect Scene C2 under another Beat without moving Runtime
→ find a known NPC/Threat not referenced in A1
→ open exact mechanics
→ close and still be at A1
```

The exact finder UI is not frozen. Agent Surface is not a prerequisite.

### P4 / Combat — exact Threat → Combat + expandable instrument

Required interaction:

```text
context or finder
→ Threat
→ exact StatblockRevision
→ Add to Combat
→ Combat-owned runtime
```

Combat may expand into the central Scene workspace while active. Play retains originating Beat/Scene context; collapse returns exactly there.

Durable Combat remains required before claiming CR-U17 overall.

### BF4 — Plan Beat-first authoring composition — PARALLEL-ELIGIBLE

BF1 grammar is sufficient predecessor. BF4 may proceed on a disjoint lease and must not block getting BF2/BF3 back to a real table.

Primary capability: structure-aware authoring of the exact Playable WorkObject—Beat/Scene/Decision/Option/consequence/refs—without lossy export.

### BF5 — legacy/operator posture — EVIDENCE-DRIVEN

Historical WorkRevision support removed the old premise that “new latest revision makes old Run unreadable.”

Only harden v1 migration/operator flows that real remaining users/material require. Do not manufacture migration work to fill the phase number.

---

## 6. Real-session dogfood gate

Before prioritizing broad hoist/kernel work over table functionality, run the target cockpit against real material.

Required scenario includes:

- resume exact last current Scene;
- Beat context accessible;
- authored Decision branch (`A→B`, `A→suppress C`);
- inspect suppressed/other-Beat Scene anyway;
- explicit Make Current;
- unplanned known NPC/Threat retrieval;
- exact statblock opening without table-breaking delay;
- unexpected Add to Combat;
- Combat expand/collapse with exact Scene return;
- notes;
- restart/resume.

The test is failed if the GM abandons DungeonBuddy for memory, manual source search, JSON surgery, or a separate mechanics navigation workflow.

---

## 7. Buddy-shared candidates after cockpit evidence

Candidates, not pre-authorized hoists:

1. `WorkObjectElementRef` if Play + Agent/document mutation genuinely share the same exact targeting invariant.
2. proposal apply/stale/dirty arbitration shared by Plan/Play/Agent.
3. generic typed-reference open / projection actions.
4. global/on-demand object finder primitive if multiple surfaces need the same product-neutral interaction.
5. asset/annotation identity if multiple surfaces prove the same need.

Do not move Beat/Scene/Decision semantics into shared core merely because these tools operate on them.

---

## 8. DungeonMind kernel sequence — still evidence-driven

### K0 — operator-authored context contract inventory

Before adding a kernel contract, inventory whether existing exact artifact/revision/source contracts can already represent saved Playable material with truthful standing.

Possible disposition:

```text
K0_REUSE_EXISTING_CONTRACTS
```

or

```text
K0_MINIMAL_KERNEL_GAP — <exact generic missing contract>
```

No `PlayableArtifact`, `Beat`, `Scene`, or `Decision` kernel classes.

### K1 — exact external/operator context admission — only if K0 proves a gap

Likely generic capability:

```text
surface sends exact artifact/revision pointer
→ kernel resolves/admission-checks
→ bounded retrieval/context budgeting
→ Agent sees standing/provenance
```

### K2 — exact-artifact retrieval — only if real Runbook size proves whole-artifact context too large

No ambient filesystem/corpus authority.

### K3 — stricter proposal envelope — only if multiple consumers prove `SuggestedAction` too weak

Payload remains product/profile-owned.

### K4 — Playable → World through existing review/publication authority

```text
exact Playable revision/element
→ evidence/provenance
→ profile candidate assertion planning
→ explicit review
→ DungeonMind finalized publication
```

No second graph-write path.

### P6 — Runtime → Playable adoption

Post-session operator actions:

```text
keep in next prep
add to recap
promote to World
discard
```

No automatic upward promotion.

---

## 9. Post-dogfood hoist review

After at least one full real run—and preferably a second materially different adventure—perform a deliberate hoist audit.

### Strong kernel candidates

- exact operator-authored context admission;
- authority/standing-aware context assembly;
- exact-artifact bounded retrieval;
- stricter generic proposal envelope only if repeated consumers need it.

### Strong Buddy-shared candidates

- stable work-object element refs;
- proposal apply/stale/dirty arbitration;
- generic reference projection actions;
- global finder/search primitive if cross-surface;
- asset/annotation identity if cross-surface.

### Keep product-owned absent new evidence

- Runbook / Beat / Scene / Decision / Consequence;
- Choice branch relevance vocabulary;
- Play Object Sheet layout;
- current-moment cockpit hierarchy;
- Run progress;
- notes product behavior;
- Combat state and Add-to-Combat presentation;
- table navigation ergonomics.

---

## 10. Current recommended sequence

```text
BF2  v2 READY Runtime + relevance
↓
BF3  Scene-centered cockpit
↓
BF3.x / P3  fast contextual + global object/statblock retrieval
↓
P4 / Combat  exact Threat→Combat + expandable Combat workspace
↓
REAL SESSION DOGFOOD
↓
P5 / Buddy shared proposal seams where evidence now warrants
↓
K0/K1/K2/K4 only where cross-system evidence proves kernel need
↓
P6 runtime adoption
↓
H1 post-dogfood hoist review
```

BF4 Plan Beat-first authoring may run in parallel after BF1 on a disjoint lease.

K3 remains conditional.

---

## Final rule

> **Hoist authority, not vocabulary. Keep the table model close to the table.**
>
> The immediate product priority is now proving the Scene-centered cockpit under unexpected play, not manufacturing another infrastructure prerequisite after APP-STATE already removed the persistence blocker.
