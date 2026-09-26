---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI Presentation Substrate Sidequest
  - Flow: UI
  - Direction: DESIGN → DOGFOOD → DECISION
  - Handoff: Docs/Plans/HANDOFF-UI-post-substrate-reentry.md
  - Branch / PR: docs/ui-post-substrate-reentry / #761 (BLOCKED design STOP)
  - PR topology: decision STOP — no implementation PR is authorized by this handoff

  ## Verification pointer
  - Current stacked review parent: #760 exact head ca1fef69b3ae11a090aac58ae66ea0e2d67205f6
  - Inputs: accepted UI-F1..UI-F5 handbacks + current demo/product dogfood
  - Output: one re-entry report + at most one newly designed successor handoff

  This is a product/steward STOP, not an implementation lease.
---

# HANDOFF — UI post-substrate re-entry decision

**Created:** 2026-09-25  
**Status:** BLOCKED — UI-F5 must complete with an accepted YES / NARROWER / NO convergence report; steward then re-anchors and activates this STOP  
**Canonical handoff path:** `Docs/Plans/HANDOFF-UI-post-substrate-reentry.md`  
**Conversation/workstream:** `UI Presentation Substrate Sidequest`  
**Flow / owner:** `UI`  
**Direction:** DESIGN → DOGFOOD → DECISION  
**Design authority base:** `738d7984520f21987e1dabc4151d68623e0451a4` — UI-F5 design head  
**Activation gate:** UI-F1 through UI-F5 have accepted handbacks or an explicitly accepted F5 stop/verdict; current `main` is re-anchored; product owner is available for one bounded demo-oriented pass  
**Dispatch base rule:** fresh current `main` at activation; record exact main and accepted predecessor SHAs in the report  
**PR topology:** `decision STOP` — this handoff itself authorizes no application-code PR  
**PR authorization:** none for implementation. After the STOP, Steward may design **at most one** successor handoff from the accepted outcome.  
**Suggested decision artifact:** `Docs/Reports/REPORT-UI-post-substrate-reentry-v1.md`

**Stack re-anchor, 2026-09-26:** Existing PR #761 is based on #760 exact
head `ca1fef69b3ae11a090aac58ae66ea0e2d67205f6`. UI-F5 is still
BLOCKED on Canvas's clean layout-only consumer prerequisite; #760 has not
produced a convergence verdict. Therefore this human/steward STOP is not
activated, no demo decision is being solicited, and no implementation or
successor PR is authorized here. The re-anchor keeps this one-handoff PR
reviewable without pretending the missing predecessor evidence exists.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). This is intentionally a design/product decision handoff rather than DESIGN → CODE.

## §1 Mission and merge-ready invariant

**Mission:** Decide whether DungeonBuddy is now cheap and safe enough to resume broad UI product iteration, and select exactly one next product/design capability from real substrate and demo evidence rather than from an old roadmap default.

**Decision-ready invariant:** The operator can inspect and alter representative Buddy presentation through the isolated workshop, the accepted F1–F5 evidence is summarized without rewriting predecessor truth, the current product is exercised in one demo-shaped path, and the final outcome is one of: **one bounded UI successor**, **one bounded substrate correction**, or **resume non-UI product work**. No implementation is dispatched from this handoff.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path asks whether the new substrate actually reduced the cost/risk of visual product iteration enough to justify the next UI move. |
| Most likely adversarial sequence | The sidequest finishes → roadmap momentum automatically chooses a Play redesign or Canvas integration despite dogfood pointing elsewhere. |
| Will §7 detect that failure? | Yes. The outcome worksheet requires Keep / Split / Reconnaissance / Resume-non-UI with explicit evidence and forbids more than one successor. |
| Easiest owning boundary to under-test | Real product friction versus workshop success: an excellent lab can coexist with a still-awkward production shell. |
| What PR topology is authorized, and why is it safe? | No implementation PR. One decision report; one successor handoff only after explicit product-owner acceptance. |
| Fact that forces stop/split | F1–F5 evidence is incomplete/contradictory, current product cannot be dogfooded enough to compare with the lab, or the next step actually spans multiple product capabilities. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | `PLAN-ui-presentation-substrate-sidequest-v1.md` |
| Design authority base | `738d7984520f21987e1dabc4151d68623e0451a4` |
| Activation gate | accepted F1–F5 evidence + fresh-main re-anchor |
| Dispatch base rule | fresh current main at the STOP |
| Predecessor contract | F1 fast workshop; F2 ObjectSheet showroom; F3 ToolHost split; F4 visual contract; F5 Canvas verdict |
| Exact input consumed | accepted handbacks/reports + current merged product + product-owner demo pass |
| Named successor | **none preselected** |
| What remains false | broad Play redesign, shell rewrite, full component migration, Canvas Board/freeform, Agent redesign, wholesale ObjectSheet adoption |
| Explicit non-goals | coding; broad backlog grooming; automatic migration of all components; declaring demo-ready solely from workshop evidence |
| PR topology | decision STOP |
| Authorized PR action | no application-code PR; one report/authority sync may be created by steward |
| Open implementation PRs in workstream at activation | must be none or explicitly unrelated/disjoint |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | current product main plus isolated workshop; no implementation worktree needed |
| Parallel lanes / collision hotspots | CON-READY PLAY may continue; this STOP must not reorder it without explicit product-owner decision |
| Runtime/state ownership | read-only product dogfood; normal durable authorities remain owners |
| State-authority sync set after decision | sidequest plan, campaign roadmap UI checkpoint, root backlog pointer; successor handoff only if accepted |

Read before the STOP:

1. `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md`
2. UI-F1 through UI-F5 accepted handbacks/reports
3. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`
4. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`
5. current `Backlog.md` captured UI goals
6. current app `main` and exact UI workshop state

## §3 Observable paths and adversarial sequences

### Evidence paths

| Path | Question | Same §1 invariant? | Owning evidence |
|---|---|---:|---|
| Token/primitive edit | Can a materially different tone be tried quickly without product runtime? | Yes | F1 handback |
| Object presentation | Can sparse/rich World objects be compared and changed from typed fixtures? | Yes | F2 handback |
| Mature behavior split | Did ToolHost behavior survive presentation extraction without semantic drift? | Yes | F3 handback |
| Visual safety net | Is the bounded screenshot suite useful and cheap rather than brittle/expensive? | Yes | F4 handback |
| Canvas experiment | Does Canvas deserve a future role, and if so exactly which layer? | Yes | F5 report |
| Current product demo path | Does the merged product now benefit from the substrate, or is the main blocker elsewhere? | Yes | human dogfood |

### Required adversarial questions

| Sequence / pressure | Required safe outcome |
|---|---|
| Workshop looks excellent, production still feels assembled | Do not declare UI substrate sufficient; choose a bounded integration/shell successor or resume product repair based on the dominant defect |
| Canvas F5 = YES | Do not automatically authorize Board/freeform or production Page adoption; choose only if it outranks product friction |
| Canvas F5 = NO | Record NO and move on; do not create another integration rescue slice by default |
| ObjectSheet looks excellent | Do not wholesale replace every object surface; select one product adoption witness if that is the dominant next value |
| ToolHost split was costly/brittle | Prefer substrate correction before more controller/presentation splits |
| Visual tests are slow/flaky | Shrink or correct the visual contract rather than normalizing cost |
| Demo path is already compelling | Resume PLAY/product capability work rather than polishing for its own sake |

## §4 Files in scope — decision lease

When activated, the STOP may write documentation only:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Reports/REPORT-UI-post-substrate-reentry-v1.md` | Evidence synthesis + product-owner outcome |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Mark sidequest result/exit truth |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Replace active UI sidequest checkpoint with accepted next posture |
| Modify | `Backlog.md` | Pointer/status sync only |
| Create | `Docs/Plans/HANDOFF-UI-<accepted-successor>.md` | **Optional, at most one**, only if product owner accepts one bounded UI successor |

**Bounded discovery exception:** no production-code paths. If the decision requires an architecture-authority amendment, stop and explicitly widen the design lease before editing it.

## §5 Explicitly out of scope / collision boundary

| Path/capability | Why this STOP must not touch or claim it |
|---|---|
| `apps/live-control-ui/**` production code | No implementation in F6 |
| package/lock files | No tooling changes |
| WorldKeeper/DungeonMind/APP-STATE | Not UI re-entry authority |
| multiple successor handoffs | Violates one-capability post-STOP rule |
| Play paint + ObjectSheet adoption + shell rewrite bundled | Must split; choose one |
| freeform/Board because Canvas exists | Separate future decision |
| “finish design system” umbrella | Sidequest explicitly does not require full migration |

## §6 Decision contract

### Inputs

The report must record exact accepted evidence for:

```text
F1 — workshop/tokens/primitives
F2 — World-object showroom
F3 — ToolHost behavior/presentation separation
F4 — canonical visual contract
F5 — Canvas YES / NARROWER / NO
current product/demo pass
```

### Required outcome worksheet

Every candidate receives exactly one disposition:

```text
KEEP
  bounded capability is independently useful and should become the sole successor

SPLIT
  valuable but currently bundles >1 capability; no implementation dispatch until redesigned

RECONNAISSANCE
  evidence insufficient; bounded read-only investigation needed first

RESUME_NON_UI
  UI is not the current highest-value blocker; return to PLAY/other product work

DROP
  no longer justified by current evidence
```

Candidate set must be re-derived from current evidence, but at minimum compare:

- one production ObjectSheet adoption witness;
- Play table-instrument/Scene presentation;
- shared shell/chrome presentation consolidation;
- Canvas Page production adoption if F5 supports it;
- further substrate correction if F1–F4 exposed friction;
- resume CON-READY PLAY / no UI successor.

Do not rank candidates before reading the evidence.

### Demo-shaped human pass

Use one realistic, bounded journey; preferred shape when available:

```text
open campaign/session material
→ inspect one useful World object
→ move to current Play/Plan material
→ exercise one Tool/Peek
→ compare the same concepts in the isolated UI lab
```

The question is not “is every screen finished?”

It is:

> Can we now change presentation rapidly without destabilizing mature behavior,
> and what single next product interaction would most improve a credible demo?

### A. State / fallback matrix

| Observable path | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Retry |
|---|---|---|---|---|---|
| evidence review | predecessor handback exists and is exact | missing evidence → RECONNAISSANCE/hold | affected candidate cannot be KEEP | contradictory handback → stop | re-run predecessor proof |
| product dogfood | merged path works enough to judge | blocked path recorded as dominant defect | do not infer visual conclusion | stale/wrong authority → stop | repair/retry separately |

### B. Identity matrix

| Situation | Required rule | Fallback permitted? |
|---|---|---|
| predecessor result | exact PR/head/report identity | No chat-memory substitution |
| product object/run/document | exact current product identity as normal | No label inference for authority |
| visual fixture | exact named static story | It is evidence, never product authority |

### C. Persistence / replay matrix

The F6 output is documentation authority only. Product data is read-only during the pass unless ordinary explicitly authorized product use requires otherwise.

### D. Predecessor → decision mapping

| Predecessor | Required evidence | Decision use |
|---|---|---|
| UI-F1 | target-laptop workshop ergonomics + build/test | Is isolated iteration cheap enough? |
| UI-F2 | ObjectSheet fixture findings | Is existing World-object view model sufficient for rapid presentation? |
| UI-F3 | behavioral equivalence + extraction cost | Is controller/presentation separation a repeatable pattern? |
| UI-F4 | run cost/flakiness/snapshot value | Is visual safety net worth retaining/expanding? |
| UI-F5 | exact YES/NARROWER/NO + dependency/perf evidence | What, if anything, should Canvas own? |
| current product | human journey notes | What product interaction actually blocks demo quality now? |

## §7 Evidence required to complete the STOP

| Guarantee | Evidence class | Required evidence | Stop condition |
|---|---|---|---|
| Predecessor truth is exact | provenance | exact merged PR/head/report for F1–F5 | missing/unaccepted predecessor |
| Weak-laptop goal was met | manual | F1/F4/F5 performance observations | workflow still materially cumbersome |
| Presentation is actually replaceable | structural | F2 + F3 evidence | product semantics still welded to presentation |
| Visual contract helps | regression | F4 result | baseline suite too costly/flaky |
| Canvas decision is evidence-backed | experiment | F5 report | no accepted F5 verdict |
| Current next blocker is human-observed | dogfood | one product-owner pass | no meaningful product path available |
| One successor maximum | review | outcome worksheet | >1 KEEP implementation candidate |

No code/test command is sufficient by itself for F6; this is intentionally a product decision gate.

## §8 Required review handback

Return:

1. exact current main;
2. F1–F5 merge/head/report identities;
3. compact “what we learned” per slice;
4. target-laptop ergonomics assessment;
5. current demo-path observations;
6. candidate outcome worksheet;
7. explicit accepted outcome;
8. exactly one of:
   - successor handoff path, or
   - reconnaissance handoff path, or
   - `RESUME_NON_UI`;
9. explicit list of tempting work intentionally not dispatched;
10. sidequest exit status.

## §9 Acceptance rubric

- [ ] F1–F5 evidence is accepted and exact.
- [ ] Product owner participated in the demo-oriented pass.
- [ ] Workshop evidence and production evidence are both considered.
- [ ] Canvas result is consumed exactly as YES/NARROWER/NO, not reinterpreted.
- [ ] Candidate outcomes are explicit.
- [ ] At most one successor is KEEP.
- [ ] No implementation code changed.
- [ ] Sidequest roadmap/backlog are synchronized truthfully.
- [ ] If no UI work outranks PLAY/product capability, outcome is RESUME_NON_UI without apology.

## Stop conditions

Stop and do not manufacture a successor if:

- F1–F5 are not accepted;
- workshop cannot run reliably on the target laptop;
- current product cannot be exercised enough to identify visible friction;
- two or more capabilities appear inseparable;
- the desired successor would require simultaneous UI and domain-authority redesign;
- product owner does not accept the proposed outcome.
