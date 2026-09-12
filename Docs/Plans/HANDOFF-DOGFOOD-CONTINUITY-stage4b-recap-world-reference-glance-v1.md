# HANDOFF — DOGFOOD-CONTINUITY: Stage 4B recap World-reference glance

**Created:** 2026-09-11  
**Status:** IMPLEMENTED — AWAITING REVIEW / HUMAN WOW DISPOSITION
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4b-recap-world-reference-glance-v1.md`  
**Conversation/workstream:** `C1/C2 demo-readiness / Stage 4 WOW gate`  
**Flow / owner:** `DOGFOOD-CONTINUITY` / historical recap reading + shared graph-reference presentation  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `92a50db8bd41d632e54e5bbbd265738f546e0a5b` (main after PR #702 merge)  
**Implementation branch:** `dogfood-continuity/stage4b-recap-world-reference-glance-impl`
**Implementation code head:** `79e012b7`
**PR title:** `DOGFOOD-CONTINUITY: make recap World references glanceable`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Product sequence: [`Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md). UI language: [`Docs/Design/ui-language/DESIGN-interaction-layer-language.md`](../Design/ui-language/DESIGN-interaction-layer-language.md).

## §1 Mission and merge-ready invariant

**Mission:** A GM reading a historical recap can immediately recognize a World reference as interactive, hover or focus it for one compact useful glance, and click/tap through to the already-shipped complete World object without losing reading continuity.

**Merge-ready invariant:** A recap World-reference token is a cheap, truthful progressive-disclosure control: idle state advertises interaction without dominating prose; hover/focus reveals only existing trustworthy table-useful identity/context; hover/focus alone never opens or selects the complete object; click/tap opens the same exact World object through the existing #700/#702 secondary-context path; closing returns to the same recap context.

### Stage 4 WOW-gate question

This PR does **not** complete Stage 4. It must make the following human question materially easier to answer “yes”:

> **When I read a recap, do World references feel like living campaign memory rather than implementation links?**

The witness is experiential as well as mechanical. A technically correct tooltip that still looks like debug chrome is a failure.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Idle token, pointer glance, keyboard glance, click/tap open, and dismiss all express the same progressive-disclosure contract. |
| Most likely adversarial sequence | Hover Karsemine → click while glance is open → complete object opens → close secondary context → recap remains at prior reading position and no stale glance remains. |
| Will §7 actually detect that failure? | Yes: focused component tests prove hover/focus vs select separation; exact C2S25 desktop+narrow dogfood proves composition and reading continuity. |
| Easiest owning boundary to under-test | `GraphNodeHoverToken`: it is shared and can accidentally mutate selection, linger after click, or become inaccessible on keyboard/touch. |
| Fact that forces stop/split | Ordinary glance requires a new backend/API fetch, new durable data contract, or a second authoring workflow. This slice must use the already-resolved `GraphProjectionNodeView` presentation only. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Demo-ready roadmap Stage 4; UI-language grammar `chip → glance → peek → modal`; post-#700 dogfood finding “hover neither styled nor informative.” |
| Base revision | `92a50db8bd41d632e54e5bbbd265738f546e0a5b` |
| Predecessor contract | PR #702 merged responsive secondary context: desktop `CENTER | SECONDARY`; narrow `CENTER XOR SECONDARY`; exact recap component remains mounted across secondary inspection. |
| Exact input consumed | Existing projected recap Markdown graph-node references plus existing `GraphProjectionNodeView` data adapted into `GraphNodeGlancePresentation`; exact node selection continues through `GraphProjectionReader.onInspectNode`. |
| Named successor | Stage 4 follow-ons: Threat-specific product treatment beyond the already-existing threat hover, session navigation polish, Details/Advanced cleanup, and representative historical-source adoption. |
| What remains false | Stage 4 WOW gate is not declared complete; C2S23 source/adoption failure remains; Agent contextual authoring remains queued; Tools/Author Node redesign remains false; suspected delayed full-page refresh remains only a reproduction watch unless independently confirmed. |
| Explicit non-goals | No 7A1; no Agent capability; no Author Node/Tools redesign; no new World/API fetch for ordinary glance; no graph identity/revision changes; no generic `?campaign=` lens repair; no Session 23 adoption; no performance project; no Play/Combat redesign. |
| Branch / isolated checkout | `dogfood-continuity/stage4b-recap-world-reference-glance-v1` from exact base above; implementation worker uses isolated worktree/equivalent. |
| Parallel lanes / collision hotspots | No implementation lane is authorized by this handoff until dispatch. Shared `graphReference` presentation/CSS is a collision hotspot for Plan and any concurrent graph-reference work. |
| Runtime/state ownership | Frontend presentation only. Existing World and APP-STATE authorities are read-only for dogfood. No durable mutation. |
| State-authority sync set after merge | In this implementation PR, backward-looking only: record #702/UI-03 as merged/current truth in `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`, `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`, `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md`, and `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`. Do not pre-mark this Stage 4B slice complete. |

Read the exact shared token implementation and its Plan/Ingest consumers before changing code. If the shared token cannot be changed without materially redesigning Plan behavior, stop and report rather than introducing a hidden second capability.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Historical recap idle World reference | Inline token exists but dogfood found the interaction visually weak/unclear. | Looks intentionally interactive while remaining cheaper than recap prose/current work. | Yes | `GraphNodeHoverToken` + CSS |
| Pointer hover | Existing anchored hover can expose several planning/debug-like sections. | Compact dark-room glance: object label, type/role, one table-useful summary when available, and at most one “why it matters here” line from existing focus evidence. | Yes | `GraphNodeHoverToken` / glance presentation |
| Keyboard focus | Existing focus opens hover state. | Same useful glance as pointer; no extra focus trap or second required action. | Yes | shared token component |
| Click / Enter while glance open | Selects node; glance may remain pointer-open until pointer leaves. | Glance dismisses immediately, then exact node opens through existing secondary context. | Yes | token + existing reader callback |
| Narrow/touch tap | No reliable hover affordance. | Tap opens the complete object directly; glance is never a mandatory first tap. | Yes | token + #702 responsive secondary context |
| Close complete object | #702 restores recap/reading context. | Same behavior remains; token/glance work must not remount recap or reset scroll. | Yes | existing historical recap + Peek path |
| Threat reference | Existing specialized `ThreatCampaignGlance` may fetch threat mechanics while open. | Preserve existing threat specialization; do not flatten it into the ordinary glance or broaden this PR into Threat redesign. | Yes | existing threat branch inside token |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| hover → click → open secondary → close | No stale hover card; exact object opens; recap position survives. | token regression + C2S25 desktop dogfood |
| focus token → press Enter → close secondary | Same exact object path as click; focus/reading context remains usable. | component test + keyboard manual witness |
| narrow tap token → Back/Close | Complete object replaces CENTER; return restores recap; no stacked glance requirement. | 390×844 dogfood |
| hover token with missing summary/evidence | Show only truthful available identity/type; do not invent copy or expose raw IDs as filler. | component fixture |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/graphReference/GraphNodeHoverToken.tsx` | Establish simplified ordinary glance hierarchy and hover/focus/select separation while preserving threat specialization. |
| Modify | `apps/live-control-ui/src/graphReference/GraphNodeHoverToken.test.tsx` | Owning-boundary interaction/accessibility regressions, including hover/focus not selecting and click dismiss-before-select. |
| Modify | `apps/live-control-ui/src/graphReference/graphReference.css` | Intentional cheap-token + dark-room anchored-glance visual hierarchy; responsive containment. |
| Modify if presentation content truly requires it | `apps/live-control-ui/src/graphReference/nodeGlancePresentation.ts` | Use only existing projected node fields to choose the table-useful summary/current-context line. No new data source. |
| Modify if previous row changes | `apps/live-control-ui/src/graphReference/nodeGlancePresentation.test.ts` | Prove deterministic truthful presentation and missing-field fallback. |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Historical-recap regression: reference click still opens existing exact World-object secondary path. |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | Backward-looking predecessor sync for merged #701/#702 truth. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md` | Record UI-02/UI-03 as merged and Stage 4 WOW work as current, without pre-completing this PR. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md` | Record #702 merge facts/review disposition as predecessor truth. |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | Backward-looking shell progress only; Stage 4 remains open. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4b-recap-world-reference-glance-v1.md` | Evidence/review handback only. |

**Bounded discovery exception:**

```text
Directory: apps/live-control-ui/src/graphReference/
Maximum additional paths: 2
Allowed path kinds: focused test fixture/helper only; no new production subsystem
Decision rule: only if the existing shared token test harness cannot prove keyboard/pointer/placement behavior without it
```

Any required production path outside this lease is a stop report. In particular, do not modify API/backend code merely to enrich the glance.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/agent/**` and Ask/provider code | Contextual Agent is a later Stage 7 capability. |
| `apps/live-control-ui/src/surfaceInteraction/**` | #702 secondary-context composition is predecessor infrastructure, not to be redesigned here. |
| `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNode*` | Author Node/Tools redesign is a separate selection-authoring successor. |
| backend/API graph projection routes | Ordinary glance must be resident from existing projected node data. |
| graph persistence / DungeonMind writes | Presentation-only slice. |
| Play / Combat surface code | Not this Stage 4 historical-recap witness. |
| historical source adoption fixtures | Stage 2/3 continuity lane; C2S23 remains separate. |

## §6 Implementation contract

```text
Input:
  existing graph-node reference label + exact node id
  existing GraphProjectionNodeView-derived GraphNodeGlancePresentation
  existing onSelect callback owned by GraphProjectionReader

Output:
  idle: visually intentional inline World-reference control
  hover/focus: anchored compact glance
  click/tap/Enter: existing exact complete-World-object inspection path

Invariant:
  glance is read-only progressive disclosure; selection happens only on activation

Failure behavior:
  missing projected node → truthful label/type fallback only; no invented summary
  missing summary → omit summary region
  missing focus evidence → omit “why it matters here” region
  placement pressure → existing above/below placement logic keeps glance usable

Replay / idempotency:
  repeated hover/focus → no mutation, no accumulating state
  repeated click on same node → existing inspection behavior, no duplicate durable work
  dismiss/reopen → same resident projected presentation

Trust boundary:
  Verifies: exact node id already resolved by projection/runtime; resident node-view presentation
  Records/trusts without proving: prose truth of projected summaries/evidence; this PR does not reinterpret campaign facts
```

### Ordinary glance content hierarchy

For non-Threat nodes, the glance is intentionally small:

```text
OBJECT LABEL
Type / role

One table-useful summary, if present
Why it matters here: one focus-session evidence line, if present
```

Do **not** include adjacency/thread lists, IDs, revision/fingerprint, origin/debug labels, raw evidence inventories, or Advanced details. Those belong after click. Do not add a second button inside the glance; the token itself is the activation control.

### Visual grammar

- recap prose remains the expensive/readable material;
- inline references are recognizable but quiet;
- glance uses **DARK ROOM CHROME**, not parchment;
- one concise card, strong label/type hierarchy, no dashboard sections;
- hover/focus treatment must be visible in light and dark surrounding content and meet normal focus visibility expectations;
- no viewport-fixed overlay; remain anchored to the token using existing placement logic.

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Hover/focus never selects | `GraphNodeHoverToken` | focused regression | focused token tests | `onSelect` untouched on hover/focus; glance visible | selection fires or active object changes |
| Click/Enter opens only through existing callback and removes transient glance | shared token | adversarial regression | focused token tests | one select; glance closed before/with activation | lingering card or duplicate select |
| Missing summary/evidence stays truthful | presentation/token | fixture regression | focused presentation/token test | optional regions omitted; label/type survive | invented/debug fallback copy |
| Threat behavior remains specialized | shared token | regression | existing threat token tests | `ThreatCampaignGlance` path still used | ordinary redesign breaks mechanics glance |
| Historical recap still opens exact World object | Graph Review integration | integration regression | focused workbench test | selected node id reaches existing complete-object path | new inspection path or identity drift |
| Desktop WOW witness | product workflow | manual dogfood | C2S25: read recap → hover Karsemine → click → close | reference looks intentional; glance answers what/why; full object opens right; recap remains | feels debug-like, overlap, stale glance, lost position |
| Narrow continuity | product workflow | manual dogfood | 390×844 C2S25: tap World reference → close/back | full object replaces recap, then exact recap context returns; no first-tap tooltip gate | stacked content, lost scroll, unusable tap |
| Keyboard accessibility | product workflow | manual + component | Tab to token → observe glance → Enter → close | visible focus/glance; full object opens; no focus trap | hover-only capability |

Exact verification commands should use the repository's current package scripts after re-anchor. At minimum:

```bash
# focused graphReference tests including GraphNodeHoverToken
# focused GraphReview historical-recap/workbench regression
# live-control-ui build/typecheck command used by current main
git diff --check
git diff --name-only 92a50db8bd41d632e54e5bbbd265738f546e0a5b...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface: Ingest → Graph Review historical recap
Smallest realistic scenario: C2 Session 25 on stable source tree
Expected observation:
  1. World references can be visually identified without instructions.
  2. Hover/focus on Karsemine gives a compact useful answer to “what is this / why here?”
  3. Clicking opens the exact complete object in #702 secondary context.
  4. Closing returns to the same reading position.
  5. At 390×844, tap opens secondary directly and Back/Close restores the recap.
Evidence captured: exact head SHA + desktop/narrow witness notes; screenshots optional but useful for WOW-gate review.
```

The suspected delayed Ingest → Plan full-document refresh is **not** part of this PR unless reproduced independently on a stable tree and shown to invalidate this witness. If reproduced, stop and escalate Stage 5B rather than hiding it inside this slice.

## §8 Required review handback

### Implementation handback

- The ordinary token now presents one compact dark-room glance: explicit object label, humanized type (`PC`/`NPC` where applicable), optional resident summary, and at most one truthful current-session relationship.
- Hover and focus only expose the glance. Click/tap/Enter first closes transient glance state and then calls the existing `onSelect`; the historical recap integration proves the same complete-object path still opens and no glance remains open.
- No new API or fetch was introduced. C2S25 revealed that Karsemine has no resident summary or labeled focus evidence, but does have focus-session adjacency. `nodeGlancePresentation` deterministically renders that resident fact as “Captain Lysandra Ironveil allied with Karsemine this session.”
- Exact-head browser dogfood also exposed unlabeled evidence-role filler (`support`). Fix commit `79e012b7` removes that debug-like fallback: unlabeled evidence uses a resident focus relationship or the context region is omitted.
- Threat specialization remains routed through `ThreatCampaignGlance`; the ordinary content reduction does not flatten it.
- Focused evidence from `apps/live-control-ui`: 3 files / 40 tests passed (`GraphNodeHoverToken`, `nodeGlancePresentation`, and `GraphReviewWorkbenchModule`); `npm run build` passed with the inherited large-chunk warning.
- Desktop C2S25: the quiet inline Karsemine token opened a compact anchored glance with `Karsemine / PC / Why it matters here`; hover → click removed the glance and opened the existing right-side complete object; close returned the recap with no stale card.
- `390×844` C2S25: direct tap opened the complete object without a tooltip gate; CENTER remained mounted/hidden; Back restored a deep internal recap scroll position of `2400`; no horizontal overflow or lingering glance appeared.
- Keyboard focus equivalence and Enter activation are proven at the owning component boundary. Browser automation could not advance native tab focus reliably, so the human reviewer should include the handoff's keyboard scenario in the experiential disposition.
- Backward-looking #701/#702 predecessor truth is synchronized in the four §2 authority files. Stage 4 remains NOT DONE.
- Changed paths are limited to §4. The only created test, `nodeGlancePresentation.test.ts`, is the explicitly named presentation-test path.
- Still false: 7A1, Agent capability, Author Node/Tools redesign, new World fetch, generic-lens repair, Session 23 adoption, performance work, and Play/Combat redesign.

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. Stage 4 WOW-gate witness disposition — specifically whether the reference now feels like living campaign memory rather than an implementation link;
4. §7 required vs produced evidence + provenance;
5. nano-commit/fix story;
6. base/head and actual changed paths vs §4;
7. baseline failures/waivers;
8. paths outside §4 (`none` or stop report);
9. named successors still false;
10. prior finding ledger on re-review.

## §9 Acceptance rubric

- [x] Exactly one independently useful capability is delivered: recognizable recap World reference → useful glance → existing full inspection.
- [x] Idle reference is intentionally interactive but remains visually cheaper than recap prose.
- [x] Ordinary glance answers “what is this?” and, when evidence exists, “why does it matter here?” without becoming a mini graph inspector.
- [x] Hover and keyboard focus reveal the same truthful glance and do not select/open the object.
- [x] Click/tap/Enter uses the existing exact node inspection path; no alternate identity or fetch path is introduced.
- [x] Glance is dismissed when activation opens the complete object; no stale floating card remains.
- [x] Narrow/touch does not require hover or a first-tap tooltip step.
- [x] Threat specialization remains intact and is not silently redesigned.
- [x] Desktop and 390×844 C2S25 witnesses preserve recap reading context through open/close.
- [x] #702/UI-03 predecessor truth is synchronized backward-looking in the named authority docs; Stage 4 is **not** pre-marked complete.
- [x] Actual changed paths stay inside §4 / bounded discovery.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- useful ordinary glance requires a new backend/API query or durable data contract;
- shared token changes require a material Plan workflow redesign;
- Threat redesign becomes necessary rather than merely preserving the existing specialized branch;
- a second operator workflow (authoring, Agent, Tools, navigation) is introduced;
- C2S25 cannot provide a stable exact-head witness because the suspected full-document reload reproduces independently;
- required production path falls outside §4;
- baseline/head gate requires an unapproved waiver.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
