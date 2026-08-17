---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P3 reference-open
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-exact-graph-reference-open.md
  - Suggested implementation branch: agent/play-exact-graph-reference-open
  - Suggested implementation PR: `PLAY: open exact World Graph reference`

  ## Verification pointer
  - Design base: `1d8ec2d24439648644dff87857a85b4bf83efda9`
  - Prior completed slice synchronized here: P3C / PR #608
  - Changed implementation paths: HANDOFF §4 only
  - Verification: HANDOFF §7

  The checked-in handoff, cumulative implementation diff, nano-commit story,
  independently rerun evidence, and review findings are the review contract.
  This body is transport metadata.
---

# HANDOFF — open an exact World Graph reference in native Play

**Created:** 2026-08-17  
**Status:** DESIGNED — implementation not started.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-exact-graph-reference-open.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P3 reference-open`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design base:** `1d8ec2d24439648644dff87857a85b4bf83efda9`  
**Suggested implementation branch:** `agent/play-exact-graph-reference-open`  
**Suggested implementation PR title:** `PLAY: open exact World Graph reference`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). Graph authority: [`ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md). Playable authority: [`ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md). Shared host authority: [`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

---

## Retrospective atomic document sync — prior completed slice only

This handoff introduces the successor-handoff maintenance pattern: **a new handoff looks backward first and atomically records the truth of the prior completed slice before it designs the next slice. It never declares its own proposed implementation complete.**

### P3C closeout

The mutable status line in `Docs/Plans/HANDOFF-PLAY-native-threat-mechanics.md` still says `CODE IN PR #608`. That is stale. This section is the current closeout authority for that completed slice and supersedes that stale mutable status; the historical design/review body remains evidence and is not rewritten here.

```text
P3C — native exact Threat mechanics
PR: #608 — PLAY: render exact Threat mechanics
merge: 53aaf9a566cfd40dd09f1a4c9723276cefa2a98a
final reviewed head: 6b0b177f08a09c2b1f8c8ff9a1eb71b450b57087
implementation/evidence repair head: 32cee38b53d4d24337bffa20560aace01b54556a
formal review cycles: 2
status: MERGED / HISTORICAL
```

P3C established the surface-neutral exact Threat mechanics seam and an early Play-owned `PlayGraphObjectSheet` / `PlayThreatMechanicsSection`. It **did not** establish graph-reference click/open, Runbook occurrence derivation, a native `/play` host, or Add-to-Combat. The Playable roadmap already records #608 as merged evidence, so this handoff does not churn that historical ledger.

**Forward rule for later handoffs:** inspect the immediately relevant completed predecessor's mutable authorities. If one is stale, close it with exact merge/review evidence in the new handoff's retrospective sync. If none is stale, write `NO DOC SYNC REQUIRED`. Do not update a roadmap merely to claim the new slice is complete or next.

---

## §1 Mission and merge-ready invariant

**Mission:** Play can open one exact World Graph object from an exact graph reference in the existing shared Projection host, rendered through the Play-owned object sheet.

**Merge-ready invariant:**

> Given one active Play graph context `(worldId, campaignId, scopeMode, revisionId)` and one durable World Graph node ID, only a `resolved_graph` result whose exact graph locator matches that node and that complete context may open in the existing shared Projection host; the host renders that exact graph object through `PlayGraphObjectSheet`, while corpus fallback, ambiguity, miss, error, incomplete graph scope, identity mismatch, or stale completion cannot open, and this flow performs no durable mutation of World Graph, Source, Playable/Run, mechanics, or Combat authority.

### Why this slice

Current repository truth is asymmetric:

```text
landed:
  shared graphReference resolver/binding/Projection-host machinery
  lease-safe AgentInteractionProvider content projection ownership
  PlayGraphObjectSheet
  PlayThreatMechanicsSection / exact Threat mechanics

still false:
  a Play-owned admission seam that opens only exact World Graph references
```

The older broad P3B design (`HANDOFF-PLAY-native-graph-object-sheet.md`) expected a future `PlaySurfacePage`, native Runbook deck, occurrence derivation, source detail, and exact reference opening in one capability. Those expected production paths are not present on this base. P3C then landed the object-sheet/mechanics composition early. This handoff therefore **narrows** the remaining work instead of pretending the old staged topology exists.

Campaign Supergraph PR009 also names Play projection migration as READY. This slice advances that migration with one read-only exact-reference capability; it does not attempt the entire Play surface migration.

### Capability decomposition

| Candidate outcome | Independently useful? | Decision |
|---|---:|---|
| Admit/open exact World Graph reference in Play | Yes | **Include** |
| Render opened object through existing Play object sheet | No; same open capability | **Include** |
| Reject corpus-index fallback in Play | No; authority clause | **Include** |
| Reject stale/mismatched graph context | No; safety clause | **Include** |
| Derive all Runbook occurrences | Yes | **Exclude — successor** |
| Build native `/play` route / Runbook deck | Yes | **Exclude** |
| Relationship drill/source-detail expansion | Yes | **Exclude unless already provided by the existing sheet without new behavior** |
| Remove corpus fallback from shared graphReference globally | Yes / cross-surface policy change | **Exclude** |
| Add exact Threat to Combat | Yes | **Exclude — P4** |
| Persist active mechanics/reference choice | Yes | **Exclude** |
| New graph resolver/API/schema | Yes | **Exclude; stop if required** |
| Generic WorkObject/reference/transaction abstraction | Yes | **Exclude** |

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes.** All changed behavior is exact-context read admission into one existing host. |
| Most dangerous sequence | Begin X@G1 resolve → active Play context changes to G2/campaign B or lease changes → X@G1 returns late → unsafe code opens X under the new table context. |
| Does §7 detect it? | **Yes.** The owning integration test delays the resolver, changes exact context/lease, then proves the stale completion cannot call/open the host. |
| Easiest boundary to under-test | Consumer-to-Projection-host admission. Testing `PlayGraphObjectSheet` alone cannot prove safe opening. |
| Stop/split fact | Exact Play admission cannot be enforced without changing global corpus-fallback semantics, adding a new backend contract, or constructing the missing native Play route/Runbook product. |

---

## §2 Context, authority, and boundaries

Read these in order at implementation dispatch:

1. `Docs/Design/ARCHITECTURE-campaign-supergraph.md`
   - World Graph owns identity;
   - surface reads are revision-pinned and admissibility-filtered;
   - product graph context never falls back to latest-ingest/preview-source/arbitrary Markdown.
2. `Docs/Plans/PR-TRACKER-campaign-supergraph.md`
   - PR009 Play projection migration is a valid independent lane.
3. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - Play projection/runtime ownership;
   - no copied World/mechanics truth.
4. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - P3 native Play projection goals;
   - P4 remains first Threat→Combat mutation.
5. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
   - Agent/Projection host is app-owned;
   - surfaces publish/bind capabilities and do not create private hosts.
6. Landed shared graph-reference seams:
   - `apps/live-control-ui/src/graphReference/types.ts`;
   - `apps/live-control-ui/src/graphReference/GraphNodeChipRuntime.tsx`;
   - `apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx`;
   - the current resolver/provider implementation actually used by the active surface;
   - `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`.
7. Landed Play composition:
   - `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx`;
   - `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.test.tsx`;
   - `apps/live-control-ui/src/playSurface/reference/PlayThreatMechanicsSection.tsx` and tests.

### Exact predecessor vocabulary

Current shared types already distinguish:

```text
GraphReferenceContext
  worldId
  campaignId
  scopeMode
  revisionId?
  focus?

ResolvedWorldGraphLocator
  source = graph
  worldId
  campaignId
  scopeMode
  revisionId
  nodeId

GraphReferenceStatus
  resolved | ambiguous | unresolved | error

GraphResolutionSource
  graph | corpus_index
```

The shared system intentionally still supports `resolved_corpus_fallback` for transitional non-Play consumers. **Do not delete or reinterpret that shared fallback.** Play applies a stricter consumer policy: exact World Graph or no open.

### What remains false after this slice

- no native `/play` route or Runbook deck is created;
- no Runbook occurrence index is derived;
- no object-attached Playable interpretation is invented;
- no source/Advanced product expansion is claimed;
- no relationship-drill expansion is claimed beyond existing host/sheet behavior;
- no mechanics selection is persisted;
- no Combat mutation exists;
- no global graphReference fallback policy changes;
- no generic Buddy/DungeonMind abstraction is justified.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| exact graph result, exact context | shared system can open graph content | Play admits and opens through existing host | Play admission adapter + host integration |
| corpus fallback resolves | shared system may open for other surfaces | Play does **not** open | Play admission adapter |
| ambiguous | no exact identity | no open | Play admission adapter |
| unresolved/miss | no exact object | no open | Play admission adapter |
| resolver error/unavailable | error state | no open; no synthetic fallback | Play admission adapter |
| graph locator lacks revision | incomplete exact authority | no open | Play admission adapter |
| world/campaign/scope/revision mismatch | wrong authority context | no open | Play admission adapter |
| returned node ID differs | wrong identity | no open | Play admission adapter |
| stale async completion after context/lease change | possible race | discard; host unchanged | Play adapter + lease integration |
| exact Threat graph object | existing Play sheet can compose mechanics | same exact object opens; mechanics remain read-only | Play sheet regression |

Required adversarial sequences:

```text
A. X@G1 resolve starts
   → context changes to G2
   → X@G1 resolves
   → NO OPEN

B. X@campaign-A resolves
   → surface lease switches / campaign-B becomes active
   → A completion arrives
   → NO OPEN

C. exact node X resolves only through corpus_index
   → shared resolver reports fallback
   → Play keeps result non-openable

D. exact graph result says node Y for requested X
   → integrity mismatch
   → NO OPEN
```

No failure path may repair itself by label lookup, alias first-win, current-head retry, corpus fallback, or a copied object body.

---

## §4 Files in scope — implementation write lease

This lease is intentionally narrower than the old P3B staged design because its expected `PlaySurfacePage`/Runbook paths are not present at this design base.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/playSurface/reference/PlayExactGraphReference.tsx` | Play-owned exact graph admission/open wrapper over existing shared resolver + Projection host; no new host |
| Create | `apps/live-control-ui/src/playSurface/reference/PlayExactGraphReference.test.tsx` | exact success, fallback rejection, mismatch, stale-context/lease, no-mutation proof |
| Modify only if composition requires it | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx` | accept/render the already-resolved exact graph object; no new authority or occurrence model |
| Modify only if above changes | `apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.test.tsx` | regression at Play rendering boundary |
| Modify only if export wiring exists/needed | `apps/live-control-ui/src/playSurface/reference/index.ts` | local Play reference exports only |
| Modify only for an existing registration seam | one current Play/shared projection registration/composition file discovered under `apps/live-control-ui/src/` | register `PlayGraphObjectSheet` for this Play capability without changing global resolution policy |
| Modify only if the registration path is changed | its existing owning test | prove one shared host and lease-safe registration |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/
Maximum additional production paths: 1
Maximum additional test paths: 1
Allowed kind: the already-existing graph-reference resolver/provider or projection-catalog composition owner required to attach the Play adapter to the existing host.
Decision rule: the path may be added only if it already owns the shared host/resolver integration and the change is a Play-scoped registration/admission seam. It may not change shared corpus-fallback semantics.
```

If implementation requires a route, backend, API type, persistence file, shared resolver semantic rewrite, new Projection host, or more paths than this lease: **stop and re-brief**.

### Design/handoff PR paths

This handoff-design PR itself owns only:

```text
Docs/Plans/HANDOFF-PLAY-exact-graph-reference-open.md
```

The retrospective P3C closeout is deliberately embedded here as the atomic look-back sync; it does not rewrite historical design prose or claim this new implementation complete.

---

## §5 Explicitly out of scope

| Capability / layer | Reason |
|---|---|
| `Docs/Process/**` and handoff templates | active process lanes own generalized policy; this PR proves the pattern locally |
| Campaign Supergraph roadmap/tracker mutation | PR009 already permits Play migration; no new sequence is required |
| Playable roadmap historical ledger churn | P3C merge evidence already exists there |
| global `graphReference` corpus fallback removal | other surfaces still rely on transitional policy |
| native `/play` route / Runbook table deck | separate independently useful surface capability |
| Runbook occurrence derivation | separate P3 capability |
| World/Source editing or graph writes | read-only slice |
| mechanics binding selection/persistence | P4 concern if needed |
| Add to Combat / HP / initiative / conditions | P4 / Combat authority |
| #578 campaign bridge data | historical dogfood evidence only |
| generic WorkObject refs / generic Runtime / transactions | not justified by this read seam |
| DungeonMind / DungeonMindDnD contract change | no evidence this slice needs one |

---

## §6 Implementation contract and matrices

### Contract

```text
Input:
  requestedNodeId: durable World Graph node ID
  activeContext:
    worldId
    campaignId
    scopeMode
    revisionId
  existing shared graph-reference resolver result
  existing shared Projection host lease

Output:
  exact admitted result → existing host opens PlayGraphObjectSheet
  every other result   → no open

Mutation:
  none

Replay:
  same exact input/context → same read/open behavior
  changed context          → old completion invalid
```

### A. State/fallback matrix

| State | Play behavior |
|---|---|
| loading | no open |
| exact `resolved_graph` + full exact locator match | open |
| exact graph ordinary miss | no open |
| `resolved_corpus_fallback` | no open |
| ambiguous | no open |
| unresolved | no open |
| dependency unavailable/error | no open; preserve truthful error state |
| incomplete graph context | no open |
| stale/superseded context | discard completion |
| retry | resolve again under the current exact context only |

### B. Identity matrix

| Situation | Rule | Fallback? |
|---|---|---|
| exact durable node ID | requested ID must equal returned graph locator node ID | No |
| display label | presentation only | No |
| alias | may be graph-owned evidence inside an already resolved object; never admission identity | No |
| normalized label/key | prohibited for open admission | No |
| world/campaign/scope/revision | all must exactly equal active Play context | No |
| rename | node ID remains authority | No label repair |
| deletion/miss | unresolved/no open | No |

### C. Persistence/replay matrix

**Not applicable — this slice creates no persisted representation, identifier, receipt, or migration.** The existing app-scoped Projection host may hold ephemeral leased UI state; this slice adds no persistence format.

### D. Predecessor-to-consumer mapping

| Existing predecessor field/outcome | Play rule | Proof |
|---|---|---|
| `GraphReferenceContext.worldId` | exact match | integration test |
| `.campaignId` | exact match | integration test |
| `.scopeMode` | exact match | integration test |
| `.revisionId` | required and exact | missing/mismatch test |
| `ResolvedWorldGraphLocator.nodeId` | equals requested durable node ID | mismatch test |
| locator `source: graph` | required | corpus-fallback rejection test |
| ambiguous/unresolved/error | non-openable | state tests |
| resolved `graphObject` | passed to existing Play sheet only after all admission checks | exact-success test |

No new wire vocabulary is allowed merely to make this mapping convenient.

---

## §7 Evidence required to merge

| Guarantee | Owning boundary | Required proof | Stop condition |
|---|---|---|---|
| exact graph result opens | Play adapter + shared host | component/integration test asserts one host open with exact graph object | cannot prove at host boundary |
| corpus fallback cannot open | Play adapter | resolved corpus fallback produces zero host-open calls | global resolver must be rewritten |
| ambiguity/miss/error cannot open | Play adapter | table-driven state tests | synthetic fallback appears |
| exact node ID required | Play adapter | X request + Y locator → no open | label/alias needed to repair |
| full world/campaign/scope/revision match required | Play adapter | mismatch each field independently; no open | current context lacks exact revision |
| stale completion cannot cross context | adapter + lease | delay resolve, update context/lease, complete old request; no open | host cannot distinguish/revoke lease |
| Play sheet renders admitted object | Play composition | exact graph object reaches `PlayGraphObjectSheet` | new object-body store required |
| P3C mechanics regression | Play sheet | exact Threat continues to render through existing P3C section | mechanics requires new binding semantics |
| no durable mutation | Play adapter/network mocks/static audit | no World/Source/Run/mechanics/Combat write API called | mutation required |
| shared fallback unchanged | shared regression/diff inspection | non-Play shared resolver tests remain unchanged/green | implementation changes global policy |
| one shared Projection host | provider/registration test | no second host/provider mounted | second host required |

Run at minimum:

```bash
cd apps/live-control-ui
npm test -- \
  src/playSurface/reference/PlayExactGraphReference.test.tsx \
  src/playSurface/reference/PlayGraphObjectSheet.test.tsx
npm run typecheck
npm run build
```

Also run the exact existing shared graph-reference / AgentInteraction provider tests touched by the registration seam. Record exact filenames and commands in the handback.

Repository/diff gates:

```bash
git diff --check
git diff --name-only <PINNED_IMPLEMENTATION_BASE>...HEAD
git diff --stat <PINNED_IMPLEMENTATION_BASE>...HEAD -- <HANDOFF-§4-PATHS>
```

Static boundary audit:

```bash
rg -n "corpus_index|resolved_corpus_fallback|fetch\(|post\(|put\(|delete\(|combat|ofConks" \
  apps/live-control-ui/src/playSurface/reference
```

Interpretation is contextual: shared fallback vocabulary may be imported to reject it explicitly; no Play path may accept it as graph authority, and no mutation/Of-Conks bridge may enter the capability.

### Minimal dogfood

If there is no current native Play entry surface capable of mounting this exact adapter at implementation base, component + existing shared-host integration evidence is sufficient for this slice. **Do not create `/play` merely to satisfy dogfood ceremony.** A later route/Runbook slice owns end-to-end table mounting.

If an existing Play entry seam is present by dispatch without expanding §4, use the smallest scenario:

```text
exact graph node reference → open → Play object sheet → close
```

Capture exact world/campaign/scope/revision/node ID; do not paste campaign prose.

---

## §8 Required review handback

The implementation handback must include:

1. exact PR, base SHA, and reviewed head SHA;
2. §1 mission and invariant verbatim;
3. exact changed paths versus §4;
4. nano-commit story;
5. §7 ledger with exact command results and provenance;
6. proof that `resolved_corpus_fallback` is rejected only by the Play consumer, not removed globally;
7. proof that each context field mismatch fails closed;
8. stale async/context/lease sequence result;
9. exact Play sheet rendering proof;
10. exact P3C Threat mechanics regression result;
11. no-mutation proof;
12. baseline failures / operator waivers (`none` when none);
13. paths outside §4 (`none` or stop report);
14. confirmation that native route/Runbook/occurrence/P4 capabilities remain false;
15. formal review-cycle count: one formal judgment against one distinct head SHA = one cycle.

---

## §9 Acceptance rubric

PASS only if every item is true:

- [ ] one capability only: exact Play World Graph reference open;
- [ ] exact durable node ID is admission identity;
- [ ] world/campaign/scope/revision are all exact and revision is present;
- [ ] only `resolved_graph` is openable in Play;
- [ ] corpus fallback remains available to other shared consumers but cannot open in Play;
- [ ] ambiguity, miss, error, incomplete context, identity mismatch, and stale completion fail closed;
- [ ] exact admitted object renders through existing `PlayGraphObjectSheet` in the one shared Projection host;
- [ ] P3C Threat mechanics still renders for admitted Threats;
- [ ] no new route, Runbook deck, occurrence model, persistence, mutation, Combat action, or campaign bridge is introduced;
- [ ] no shared resolver/API/schema semantics are rewritten;
- [ ] actual paths remain inside §4/bounded discovery;
- [ ] focused tests, shared regressions, typecheck/build, and diff gates are exact and green or truthfully report baseline failures;
- [ ] named successors remain false.

REQUEST CHANGES for repairable invariant/evidence gaps. STOP/rebrief for authority or scope mismatch.

---

## Stop conditions

Stop rather than expand if:

- the implementation base no longer has the landed shared Projection host or Play object sheet assumed here;
- current Play context cannot provide an exact revision-pinned World Graph scope;
- exact admission would require changing shared fallback semantics for Plan/Build;
- a new backend endpoint, API/schema, persistence representation, or identity policy is required;
- a native `/play` route/Runbook product must be built to make the capability exist;
- Runbook occurrence derivation becomes necessary to prove opening;
- the implementation needs a second Projection host/provider;
- any World/Source/Run/mechanics/Combat mutation becomes necessary;
- more than the §4 bounded discovery paths are required;
- an active parallel lane owns a required path and cannot be serialized cleanly.

Report the violated invariant clause, exact new requirement, missing proof, affected paths, and proposed successor/rebrief.

---

## Successors deliberately still false

This handoff does **not** select the next slice after implementation. It only names remaining capabilities for later decomposition:

```text
native Runbook/table mounting
Runbook occurrence derivation
richer Source/Advanced object detail
relationship drill expansion if not already sufficient
P4 — explicit Add to Combat
full Campaign-Supergraph PR009 Play migration
```

After this slice eventually merges, its successor handoff must perform the same retrospective check: close this completed slice with exact merge/review evidence if any mutable authority is stale, then design one new capability. It must not predeclare this slice complete now.
