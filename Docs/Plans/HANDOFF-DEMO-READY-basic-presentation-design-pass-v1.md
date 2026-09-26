---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DEMO-READY / UI presentation
  - Flow: PRODUCT-DESIGN
  - Direction: DESIGN → DOGFOOD → DECISION
  - Handoff: Docs/Plans/HANDOFF-DEMO-READY-basic-presentation-design-pass-v1.md
  - Branch / PR: none after merge; this file is the design authority
  - PR topology: decision STOP — no application-code PR is authorized by this handoff

  ## Verification pointer
  - Design authority / head: main@016a2351032f731aaa68eaffccad6f0c97a859f6
  - Inputs: merged UI-F0–F4 substrate + Demo-Ready Stage 4/5 human gates
  - Output: one design report + at most one successor implementation handoff

  This is a product/design handoff, not an implementation lease.
---

# HANDOFF — DEMO-READY basic presentation design pass

**Created:** 2026-09-26  
**Status:** ACTIVE AFTER MERGE — design/dogfood decision only; no application-code lease  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DEMO-READY-basic-presentation-design-pass-v1.md`  
**Conversation/workstream:** `DEMO-READY / UI presentation`  
**Flow / owner:** `PRODUCT-DESIGN`  
**Direction:** DESIGN → DOGFOOD → DECISION  
**Design authority base:** `016a2351032f731aaa68eaffccad6f0c97a859f6`  
**Activation gate:** none beyond this handoff merging to current main; UI-F0–F4 are already merged  
**Dispatch base rule:** re-anchor on fresh current `main` containing this handoff before beginning the dogfood/design pass; record that SHA in the report  
**PR topology:** `decision STOP`  
**PR authorization:** no application-code PR is authorized by this handoff. The design worker may produce one report and, after product-owner acceptance, at most one bounded successor implementation handoff.  
**Suggested decision artifact:** `Docs/Reports/REPORT-DEMO-READY-basic-presentation-design-pass-v1.md`

> Repository law: [`AGENTS.md`](../../AGENTS.md).  
> Demo authority: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md).  
> UI substrate authority: [`PLAN-ui-presentation-substrate-sidequest-v1.md`](PLAN-ui-presentation-substrate-sidequest-v1.md).  
> UI language: [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md).

## §1 Mission and decision-ready invariant

**Mission:** A product/design worker can use the merged lightweight UI substrate to inspect the current real Buddy experience, identify the first human-visible presentation defect that prevents a credible basic demo, prototype alternatives cheaply, and return exactly one bounded successor design.

**Decision-ready invariant:** The selected successor is justified by direct C1/C2 product dogfood, is materially visible in the basic demo path, can be prototyped in the backend-free UI lab before production integration, and does not require new domain authority, Canvas/spatial work, or a broad frontend redesign.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. Every activity exists to identify and validate one dominant demo-presentation defect. |
| Most likely adversarial sequence | Strong isolated component work → visually satisfying prototype → no improvement to the actual C1/C2 demo path because the wrong surface/problem was selected. |
| Will §7 detect that failure? | Yes. Real-product Stage 4/5 dogfood precedes isolated design work, and the final candidate must be rechecked in the real demo journey before a successor is authorized. |
| Easiest boundary to under-test | The gap between a good Ladle fixture and the actual production composition around it. |
| PR topology | No implementation PR. One design report; at most one successor handoff after product-owner acceptance. |
| Fact that forces stop/split | The dominant blocker is functional/durability/authority rather than presentation, or two UI capabilities are inseparable to create value. |

## §2 Context, authority, lane, and current truth

| Field | Required content |
|---|---|
| Parent authority | Demo-Ready Stage 4/5 + merged UI Presentation Substrate F0–F4 |
| Design authority base | `016a2351032f731aaa68eaffccad6f0c97a859f6` |
| Predecessor contract | UI-F0–F4 merged: Ladle/tokens/primitives, ObjectSheet showroom, ToolHost split, bounded visual contract |
| Exact input consumed | Current merged Buddy product using real C1/C2 material plus static Ladle fixtures already in repo |
| Named successor | One bounded production presentation slice selected by this STOP; no successor is preselected |
| What remains false | No Canvas F5; no spatial workspace; no theme-pack system; no broad Play redesign; no wholesale ObjectSheet rollout; no shell rewrite |
| Explicit non-goals | Fixing semantic thinness through UI; new World/DungeonMind semantics; Combat; Agent expansion; Stage 6 durability work; generic design-system completion |
| PR topology | decision STOP |
| Authorized PR action | report + optional one successor handoff only |
| Open implementation PRs at dispatch | re-check; blocked F5/F6 design PRs do not own product-code leases |
| Parallel lanes / collision hotspots | CON-READY PLAY may continue if disjoint; do not edit its authority/contracts |
| Runtime/state ownership | ordinary product authorities remain unchanged; this pass is read-only except normal user actions needed for dogfood |
| State-authority sync after decision | Demo-Ready roadmap and/or UI plan only if required to record accepted successor; no silent sequencing rewrite |

### Current merged UI substrate

Treat these as available tools, not goals to continue expanding:

```text
Ladle backend-free workshop
semantic presentation tokens
Surface / Button / Badge / Stack
ObjectSheet + typed World-object fixtures
callback-free ToolHostView presentation model
8-case explicit Chromium visual contract
```

Do not add more frontend infrastructure merely because it could be useful.

### Current deferred / blocked fun work

These remain outside this handoff:

```text
UI-F5 Canvas layout convergence        BLOCKED / not required for demo-ready presentation
UI-F6 post-substrate STOP              BLOCKED behind F5
spatial/infinite workspace             DEFERRED until basic demo-ready presentation
instant theme-pack system              DEFERRED with spatial/composable UI work
```

## §3 Required design sequence

This sequence is deliberate. Do not start by opening Ladle and redesigning the component you personally find most interesting.

### D0 — Re-anchor the actual demo path

Use current merged C1/C2 material.

Minimum real-product path:

```text
open C1/C2
→ choose a prior session
→ read recap
→ inspect at least two World references / objects
→ move Ingest → Plan → Build → Play
→ return to the original recap/session
```

If current data availability blocks a step, record the exact blocker. Do not substitute a static fixture for a missing production capability and call the path good.

### D1 — Complete the Stage 4 presentation witness

Spend time actually reading more than one representative C1/C2 recap.

Evaluate:

- prose readability;
- whether pills help without becoming visual noise;
- glance usefulness;
- opened-object usefulness;
- whether a Threat feels materially more useful than a generic object;
- whether source/provenance is available but secondary;
- whether opening/dismissing secondary content preserves reading position;
- whether accumulated campaign information feels accessible enough to create a “this remembers my game” moment.

The purpose is not to re-evaluate graph correctness. It is to determine what the human sees first.

### D2 — Complete the Stage 5 navigation witness

Navigate repeatedly among Ingest, Plan, Build, and Play while keeping one real campaign/session context.

Observe:

- page flashes/remount feel;
- context loss;
- shell density and competing chrome;
- whether current work remains visually dominant;
- back/forward behavior;
- hard reload;
- stale controls;
- whether moving surfaces feels like one application.

Stage 5B remains conditional. Do not prescribe persistent AppChrome changes unless this witness finds a concrete remount/composition failure.

### D3 — Produce a visible-defect ledger

Record the first human-visible defects, not every possible improvement.

Use this shape:

| Defect | Surface/path | Severity to basic demo | Presentation-only? | Reproducible in Ladle? | Candidate disposition |
|---|---|---:|---:|---:|---|
| ... | ... | high/med/low | yes/no | yes/no | KEEP / SPLIT / NON_UI / DROP |

A defect belongs in this design pass only when it is primarily presentation/composition and can improve the demo without changing domain authority.

### D4 — Select at most three design candidates

Candidate families may include, but are not limited to:

1. **Production World-object presentation witness**
   - integrate the proven ObjectSheet hierarchy into one canonical opened-object path;
   - likely candidate: the shared floating object Peek;
   - preserve complete-object input, actions, Advanced/provenance, exact identity.

2. **Play current-moment hierarchy**
   - make current Beat/Scene read like a table instrument;
   - distinguish existing authored semantics such as read-aloud, GM notes, rules, warnings where the current projection already exposes enough information;
   - no new Play authority or navigation semantics in a presentation-only successor.

3. **Recap / Peek composition**
   - improve reading hierarchy, spacing, pill density, secondary-context composition, or object continuity;
   - preserve exact recap/session identity and mounted CENTER behavior.

4. **Shell/chrome balance**
   - only when Stage 5 dogfood proves current chrome materially competes with current work;
   - no broad AppChrome rewrite by default.

5. **Build first-impression clarity**
   - only if the demo path reaches Build and its presentation, rather than missing product capability, is the dominant visible problem.

6. **Ingest GM-facing hierarchy**
   - only if the current historical-review experience is technically available but visually/operator-heavy;
   - do not redesign governed authoring semantics here.

Do not select a candidate merely because backlog prose already describes it well.

### D5 — Prototype candidates in the lightweight UI lab

For each retained presentation candidate:

- use static representative data;
- reuse real production view-model shapes where available;
- use existing tokens/primitives before creating new ones;
- compare desktop and narrow;
- prefer one or two materially different compositions over many cosmetic variants;
- do not add a dependency unless the candidate concretely requires it.

A prototype may be throwaway.

The point is to answer:

> Does this noticeably improve how the demo reads and feels?

### D6 — Recheck the winning prototype against the real product

Before selecting the successor, return to the real C1/C2 path and verify that the candidate solves the actual observed defect rather than only looking good in isolation.

No production code is written in this handoff. This is a design judgment step.

### D7 — Product-owner STOP

Present:

- the demo-path observations;
- the visible-defect ledger;
- up to three candidate prototypes;
- the recommended single successor;
- what remains deliberately untouched.

The product owner may:

```text
ACCEPT_ONE
  design exactly one bounded successor implementation handoff

RECONNAISSANCE
  evidence is insufficient; authorize one bounded read-only investigation

RESUME_NON_UI
  the dominant demo blocker is not presentation

HOLD
  current UI is sufficient for now; continue other demo-readiness work
```

No second implementation successor is authorized by this handoff.

## §4 Files in scope — design lease

This handoff authorizes design evidence and optional prototype-only UI-lab work after it is merged.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Reports/REPORT-DEMO-READY-basic-presentation-design-pass-v1.md` | Dogfood evidence, defect ledger, candidate comparison, product-owner outcome |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Optional pointer/status sync only if this pass changes active UI posture |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Optional Stage 4/5 STOP result sync after product-owner decision |
| Create/Modify | `apps/live-control-ui/src/ui/**/*.stories.tsx` | Prototype-only stories when an existing story cannot express a retained candidate |
| Create/Modify | `apps/live-control-ui/src/ui/**/*.css` | Prototype-only presentation styling |
| Create | `Docs/Plans/HANDOFF-DEMO-READY-<accepted-successor>.md` | Optional; exactly one successor after product-owner ACCEPT_ONE |

**Bounded discovery exception:**

```text
Directory: apps/live-control-ui/src/ui/
Maximum additional prototype paths: 4
Allowed path kinds: static fixture, story, presentation-only component, presentation-only CSS
Decision rule: only when needed to compare a retained candidate; no production route/import may consume it in this design pass
```

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why excluded |
|---|---|
| `apps/live-control-ui/src/App.tsx` | No production integration in this design pass |
| production Ingest/Plan/Build/Play components | Observe them; do not modify them here |
| `surfaceInteraction/**` controller/state contracts | Merged substrate is evidence, not current design scope |
| `markdownCanvas/**` authority | No editor/persistence redesign |
| `graphReference/**` authority/contracts | No World-reference semantic redesign |
| WorldKeeper / DungeonMind | No domain-authority work |
| Canvas F5 / `Drakosfire/Canvas` | Explicitly not prerequisite for basic demo presentation |
| spatial/infinite workspace | Deferred backlog |
| theme packs | Deferred backlog |
| Combat | Later Play capability |
| Agent expansion | Later Demo-Ready stage |
| Stage 6 durability | Separate functional demo-readiness work |

## §6 Decision contract

```text
Input:
  current merged Buddy
  real C1/C2 material
  merged F0–F4 UI substrate
  existing UI-language evidence

Output:
  REPORT-DEMO-READY-basic-presentation-design-pass-v1
  + exactly one of:
      ACCEPT_ONE + one successor handoff
      RECONNAISSANCE
      RESUME_NON_UI
      HOLD

Invariant:
  selected UI successor addresses the highest-value presentation defect actually
  observed in the basic demo path and can be prototyped without changing domain authority.

Failure behavior:
  missing real product path → record blocker; do not replace with fixture evidence
  dominant non-UI defect → RESUME_NON_UI
  candidate requires multiple capabilities → SPLIT/HOLD rather than bundle
  isolated prototype does not improve real path → DROP candidate

Replay:
  same merged product/data → observations should be reproducible enough to discuss
  changed main/data → re-anchor before implementation handoff dispatch

Trust boundary:
  Verifies: human-visible presentation/composition quality and design feasibility
  Does not prove: World correctness, durability, Agent quality, Canvas viability
```

### State / identity / persistence

No new product state, identity, persistence, or authority is introduced.

Prototype fixtures are design evidence only and must not become campaign truth or a shadow product store.

## §7 Evidence required to complete the design STOP

| Guarantee | Evidence class | Scenario | Expected evidence | Stop condition |
|---|---|---|---|---|
| Real demo path was inspected | human dogfood | D0 across real C1/C2 | exact sessions/surfaces/objects noted | fixture-only review |
| Stage 4 presentation was judged | human dogfood | D1 | readable notes on recap/pills/object/Threat/context | tests-only conclusion |
| Stage 5 coherence was judged | human dogfood | D2 | concrete navigation/chrome/context observations | broad shell assumptions without repro |
| Defects are presentation defects | design classification | D3 | each retained defect says why no authority change is needed | dominant defect is functional/domain |
| Candidate is cheap to iterate | isolated prototype | D5 | desktop+narrow prototype in Ladle or explanation why existing story suffices | requires backend to judge basic composition |
| Candidate helps real product | human comparison | D6 | before/after design judgment tied to original defect | lab-only beauty |
| Exactly one next action chosen | product-owner STOP | D7 | ACCEPT_ONE / RECONNAISSANCE / RESUME_NON_UI / HOLD | multiple implementation successors |

### Minimal live proof

```text
Existing surface:
  current merged C1/C2 Buddy product

Smallest realistic scenario:
  read one prior recap → inspect two World objects → navigate Ingest/Plan/Build/Play
  → return to original session → compare dominant presentation defect with isolated prototype

Expected observation:
  one specific presentation change clearly improves the demo, or presentation is
  not currently the dominant blocker

Evidence captured:
  report with exact main, session/material identities, screenshots/notes where useful,
  prototype story names, and product-owner outcome
```

## §8 Required handback

Return:

1. exact current main used;
2. real C1/C2 sessions/material exercised;
3. Stage 4 witness result;
4. Stage 5 witness result;
5. visible-defect ledger;
6. prototype names/paths and desktop+narrow observations;
7. candidates dropped and why;
8. recommended one successor;
9. product-owner decision;
10. either one successor handoff path or `RESUME_NON_UI / HOLD / RECONNAISSANCE`;
11. explicit statement that Canvas/spatial/theme work remained deferred.

## §9 Acceptance rubric

- [ ] Current merged main was re-anchored before dogfood.
- [ ] Real C1/C2 material, not only fixtures, was used.
- [ ] Stage 4 and Stage 5 presentation/coherence questions were explicitly answered.
- [ ] The defect ledger separates presentation from functional/domain blockers.
- [ ] Retained candidates were prototyped with the merged lightweight substrate.
- [ ] No production component was modified during the design pass.
- [ ] No new UI dependency was added without a concrete prototype need.
- [ ] No Canvas/spatial/theme work was pulled forward.
- [ ] At most one implementation successor was accepted.
- [ ] The resulting successor is bounded enough for the normal implementation handoff template.

## Stop conditions

Stop and report rather than inventing UI work when:

- real C1/C2 material required for the witness is unavailable;
- the first serious demo blocker is durability, missing data, authority, navigation correctness, or another non-presentation concern;
- a candidate requires simultaneous changes to domain semantics and presentation;
- a candidate requires more than one production capability to be independently useful;
- product-owner judgment does not support one clear successor;
- another active lane owns a required production path;
- the design pass begins drifting into Canvas, spatial layout, theme systems, Combat, or Agent expansion.

A successful outcome may be **RESUME_NON_UI**. That is not a failed design pass.
