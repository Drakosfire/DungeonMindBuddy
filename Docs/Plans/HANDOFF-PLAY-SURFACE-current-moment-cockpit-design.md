---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY-SURFACE / Lane A3 current-moment cockpit contract
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit-design.md
  - Design anchor: Docs/Design/DESIGN-play-surface-gm-cockpit-target.md
  - Branch / PR: agent/play-surface-current-moment-cockpit-design / `PLAY-SURFACE: define the current-moment cockpit contract`

  ## Verification pointer
  - Assumption anchor: `f90924d1ae4961e5ecba61a7c841fb5b0bf2bfab` (approved GM cockpit design target on top of merged PR #626)
  - Predecessor: merged PR #626 / Lane A2 readability + active-Run dogfood
  - Dispatch base: re-anchor current `main` containing this handoff and record the exact SHA in the PR body before editing
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7 + design consistency audit + exact-head formal review

  This is a steward-designated design/architecture PR under AGENTS.md. It may
  change only the reviewed Play design/architecture contract and the first
  implementation handoff that follows from that contract. It must contain no
  production implementation.
---

# HANDOFF — define the current-moment GM cockpit contract

**Created:** 2026-08-20  
**Status:** ACTIVE DESIGN HANDOFF — re-anchor current `main` immediately before dispatch.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit-design.md`  
**Workstream:** `PLAY-SURFACE / Lane A3 current-moment cockpit contract`  
**Flow / owner:** `PLAY-SURFACE`  
**Direction:** DESIGN → REVIEW  
**Assumption anchor:** `f90924d1ae4961e5ecba61a7c841fb5b0bf2bfab`  
**Suggested branch:** `agent/play-surface-current-moment-cockpit-design`  
**PR title:** `PLAY-SURFACE: define the current-moment cockpit contract`

> Repository law: `AGENTS.md`.  
> Approved UX target: `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`.  
> Play architecture: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Play projection design: `Docs/Design/DESIGN-play-surface-projection.md`.  
> Playable authoring design: `Docs/Design/DESIGN-playable-authoring-and-adoption.md`.  
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.  
> Parent acceptance: `Docs/Roadmaps/ROADMAP-con-ready.md`.  
> Lane A2 evidence: `Docs/Reports/REPORT-play-readability-dogfood-2026-08.md`.

---

## 0. Re-anchor and predecessor truth

At handoff-authoring time, repository truth is:

```text
PR #626:
  title:                    PLAY-SURFACE: make Play readable and dogfood active Run
  final branch head:        f26e6449927d6a509d8cbb71d8798d8a9197015a
  merge commit:             a56cf4ab1ea231164db1f5a30fa3d177d8b328a6
  formal review cycle 1:    REQUEST-CHANGES-equivalent @ d42b9db1...
  formal review cycle 2:    REQUEST-CHANGES-equivalent @ c11b0f6b...
  formal review cycle 3:    REQUEST-CHANGES-equivalent @ 98a1fce0...
  formal review cycle 4:    PASS-equivalent @ f26e6449...
  review cycles total:      4
  readability dogfood:      PASS
  active-Run continuity:    PASS

approved design anchor:
  f90924d1ae4961e5ecba61a7c841fb5b0bf2bfab
  PLAY-SURFACE: anchor GM cockpit design target

main at assumption anchor:
  f90924d1ae4961e5ecba61a7c841fb5b0bf2bfab
```

The approved target is:

`Docs/Design/assets/play-surface-gm-cockpit-target.webp`

and its interpretation contract is:

`Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`.

There is one harmless history wart immediately after the #626 merge: an
accidental one-line `noop` commit was immediately repaired forward by the
anchor commit, which removes the stray file. The current tree is clean. Do not
rewrite published `main` history merely to hide that telemetry.

### Re-anchor before dispatch

Before creating the design branch:

1. fetch current `main`;
2. record its exact SHA in the PR body;
3. verify the approved design anchor still exists unchanged;
4. inspect active PRs/worktrees for overlapping writes to the paths in §4;
5. verify whether Lane B / Combat collision status changed;
6. amend this handoff before editing if current repository authority materially changed.

The assumption anchor is not permission to ignore a newer `main`.

### Backward-looking sync carried by this design PR

PR #626 is now completed predecessor truth and the living sequence still shows
Lane A2 as active. This design PR consumes #626 and must synchronize that truth
atomically with its reviewed design output:

- #626 MERGED at `a56cf4ab...`;
- final branch head `f26e6449...`;
- **4 formal review cycles**;
- Cycle 4 PASS-equivalent;
- readability and same-store active-Run continuity dogfood PASS;
- Lane A2 is complete;
- the approved GM cockpit target exists on `main`;
- the current structural gate is this reviewed Beat/Scene/Decision + Plan→Playable design;
- CR-U17 remains false overall;
- Combat durability remains Combat-owned and separately sequenced;
- P3B/P4 remain non-dispatchable/deferred unless a fresh re-anchor explicitly changes that.

Do not pre-mark this design PR complete or invent its review count/merge SHA.

---

## 1. Mission and merge-ready invariant

### Mission

Turn the approved GM-cockpit target into a reviewed product + architecture
contract that is precise enough to implement **without guessing the structural
meaning of Beat, Scene, Decision, consequence, current position, relevance,
Run migration, or Plan→Playable adoption**.

This is the deliberate pause before more structural Play wiring.

### Merge-ready invariant

> **The repository contains one reviewed current-moment cockpit contract that preserves the approved table-first UX target and unambiguously specifies the Playable containment model, serialization responsibilities, manifest membership/versioning, Runtime current-position semantics, Decision/consequence/relevance behavior, old-Run migration/reconciliation, rebase behavior, and Plan→Playable authoring relationship. A reviewer can use the contract to decompose implementation into isolated PR slices without making new product decisions inside implementation code. No production code changes in this PR.**

### What may be claimed after this design PR passes

```text
true:
  the approved cockpit UX hierarchy has a reviewed interaction contract
  Beat/Scene/Decision containment is unambiguous
  current Beat/current Scene Runtime semantics are unambiguous
  Decision selection and relevance semantics are unambiguous
  the new Playable wire/version boundary is specified
  existing sealed Runs/manifests have an explicit migration/reconciliation posture
  Plan→Playable no-loss authoring has an explicit composition/adoption posture
  implementation can be decomposed without deciding product semantics in code
```

### What must remain false after this design PR

```text
false:
  the Beat-first structure is implemented
  current sealed Runs have been migrated
  the cockpit UI is implemented
  the final aesthetic system is frozen
  Combat durability is solved
  Play owns Combat runtime
  graph object sheets are newly dispatchable by implication
  Add to Combat is newly dispatchable by implication
  cross-worktree persistence is solved
  a general workflow/rules engine exists
  Decision consequences automatically mutate arbitrary World/Runtime state
```

---

## 2. Approved UX target — what the design must preserve

The reviewed design may refine the target but must not silently collapse it
back into the current Scene-first three-column document navigator.

The target establishes these product requirements:

### 2.1 Current moment dominates

Default Play is a GM cockpit for **the next few minutes at the table**.

The operator should immediately see:

```text
current Beat
  objective / pressure / phase

current Scene
  concrete situation inside that Beat

current Decision, when one matters
  options
  immediate consequence framing
  selected state / changed relevance

relevant-now support
  people / threats / rules / notes / maps / tools as admitted context
```

Runbook structure remains available as an alternate full-structure projection.

### 2.2 Table loop

The design must support the repeated loop:

```text
ORIENT
→ DECIDE
→ CONSEQUENCE
→ STATE CHANGE
→ KEEP GOING
```

without forcing the GM to reconstruct navigation context.

### 2.3 Detail is contextual

Opening an NPC, Threat, Rule, Note, Map, source excerpt, or other relevant
object should normally preserve the current table moment and close back to it.

The design must continue to respect shared AppChrome / shared projection-host
ownership. Do not invent a second Play chrome.

### 2.4 Combat is continuous in experience, separate in authority

The design may show how the GM enters/exits Combat from the cockpit, but Combat
remains Combat-owned. This design must not absorb HP/initiative/conditions into
the Play Run merely to make the mockup convenient.

### 2.5 Visual treatment is not frozen

Do not turn the target image into a pixel spec.

The following remain implementation/design-system decisions:

- exact color values;
- fonts;
- icons;
- spacing;
- exact side-panel geometry;
- mobile layout details;
- exact capability-nav labels/order;
- exact `At a Glance` contents.

The PR is about information architecture, interaction, and durable semantics.

---

## 3. Design contract to resolve

The design PR must answer every subsection below explicitly. A heading that
says “TBD” is a blocker unless it is clearly marked as a separate later
capability that does not prevent the first implementation slice.

### 3.1 Canonical Playable containment

Current architecture direction is Beat-first, but current shipped P1/P2 is
Scene-first and incompatible.

Resolve the exact semantic containment model.

At minimum answer:

1. Does a Runbook own an ordered collection of Beats directly?
2. Does every Scene belong to exactly one Beat?
3. Can a Beat be current with no current Scene?
4. Does every Beat require at least one Scene?
5. What is the canonical owner of a Decision?
6. Can a Decision be associated with a specific Scene while remaining Beat-owned?
7. Can a Scene own Decisions directly, or is that only a projection association?
8. Can consequences attach to Beat, Decision Option, Scene, or more than one of these?
9. What order is durable and what order is projection-only?
10. What does `spine | optional | interrupt` mean for containment versus display?

Use one canonical model. Do not leave two equivalent representations that
implementation must reconcile heuristically.

#### Steward hypothesis to test, not blindly accept

A useful starting hypothesis is:

```text
Runbook
  → ordered Beats

Beat
  → ordered Scenes
  → Decisions
  → consequences
  → references/tools

Decision
  → stable Options
  → authored consequence/transition references

Runtime
  → currentBeatId
  → currentSceneId?   # optional, and must belong to current Beat when present
  → choice selections
```

A Decision may need an optional Scene association for “this decision is
presented in this situation” without making Scene the durable parent again.
Challenge or refine this explicitly.

### 3.2 Playable serialization / P1 replacement

Specify the Beat-first wire/serialization contract sufficiently to implement.

Cover:

- stable Beat identity;
- stable Scene identity;
- stable Decision/Choice identity;
- stable Option identity;
- hierarchy representation in Markdown/Tiptap or admitted work-object content;
- ordering;
- non-semantic headings / ordinary authored prose;
- semantic block attachment (`At the table`, `Read aloud`, `GM note`, `Rules now`, `Warning`, consequences, references);
- validation failures;
- duplicate IDs;
- illegal containment;
- literal fenced-code treatment;
- forward versioning.

Do not create a second Playable database merely because the hierarchy changes.
The admitted durable Playable work object remains the normal authoring target
unless this review demonstrates a concrete blocker.

### 3.3 Manifest membership and versioning / P2B1

The current sealed manifest encodes membership under the Scene-first grammar.
Define the replacement membership contract.

At minimum specify:

```text
manifest schema/version
beat IDs
scene IDs + parent Beat
Decision/Choice IDs + canonical parent/association
Option IDs + parent Decision
membership needed to validate Runtime references
transition/relevance references that must be sealed, if any
```

Answer:

- Is this a new manifest schema version?
- Can old and new manifests coexist?
- What is rejected fail-closed?
- Does the manifest persist display titles/order, or only identity/membership?
- Which transition/relevance relationships must be immutable for the Run-bound revision?

Preserve the existing principle: the Runtime sidecar is not a copied Runbook.

### 3.4 Runtime current-position semantics / P2B2

Define current position for a Beat-first cockpit.

At minimum answer:

- Is `currentBeatId` required once a Run is READY?
- Is `currentSceneId` optional?
- Must `currentSceneId` belong to `currentBeatId`?
- What happens when the operator changes Beat?
- Does changing Beat automatically choose a Scene?
- What happens when a Beat has no Scene or only optional Scenes?
- What is focus/navigation state versus durable current position?
- Is Runbook-view expansion local UI state only?
- What is the durable resolved-state contract?
- Can a resolved Beat remain current?
- How does explicit previous/next Beat navigation behave when relevance changes?

Do not persist cosmetic focus merely because the cockpit can display it.

### 3.5 Decision selection, consequences, and changed relevance

This is the most important new table interaction in the target.

Specify the minimum durable semantics that support:

```text
Decision
→ Option selected
→ consequence is legible
→ later Scenes/Beats may become more/less relevant
```

The design must distinguish:

1. **authored intent** — what an Option says should become possible/relevant;
2. **runtime selection** — which Option the table chose;
3. **runtime consequences actually recorded** — if these require an explicit GM action;
4. **projection relevance** — what Play should emphasize, de-emphasize, or hide.

Answer explicitly:

- Is selected `choiceId → optionId` still the only mandatory Decision mutation?
- Is relevance derived from selected Options + authored transitions, or persisted separately?
- What is the smallest transition vocabulary needed?
- Does `possible`, `relevant`, `blocked`, `resolved`, or similar state need durable representation?
- Can a GM override/reopen relevance after an unexpected table choice?
- Are consequences informational first, manually applied first, or automatically applied?
- How do we avoid creating a general rules/workflow engine?

#### Strong default

Prefer **derive what can be derived** from immutable authored transition data and
durable Decision selections. Do not persist a second copy of relevance state
unless a concrete operator action cannot be reconstructed from those inputs.

Prefer explicit GM confirmation for state changes whose meaning is not fully
encoded. “The players chose B” can be durable without pretending the product
can automatically understand every narrative consequence.

### 3.6 Existing sealed Runs and migration/reconciliation

The Beat-first grammar is structurally incompatible with existing Scene-first
sealed Runs. This PR must make that operationally explicit.

Provide a migration matrix for at least:

```text
old Playable revision + old manifest + old Run
old Playable revision reopened after new code ships
old Run rebased to a new Beat-first Playable revision
new Beat-first Playable revision + new manifest + new Run
partially/incompletely sealed Run
```

Decide whether old Runs are:

- supported under a legacy reader;
- explicitly migrated;
- rebase-only into a new version;
- intentionally non-upgradable while remaining inspectable;
- another precise posture.

No silent ID remapping.
No “pick newest/first.”
No destructive cleanup of historical Runs as migration.

### 3.7 P2C rebase behavior across the grammar boundary

Current P2C preserve-only rebase requires durable references to remain
admissible. Define what happens when containment itself changes.

At minimum answer:

- Is same-ID preserve-only rebase still sufficient after Beat-first adoption?
- If a Scene changes parent Beat, is that a semantic incompatibility?
- If a Decision changes Scene association but not Beat ownership, what is preserved?
- Is any ID mapping allowed in the first implementation?
- What exact blocker/receipt should the operator see when rebase cannot preserve Runtime truth?

Prefer a conservative fail-closed first implementation over speculative mapping.

### 3.8 Plan → Playable authoring

C2S27 already settled one rule:

> **Plan authors/adopts the exact Playable material; there is no lossy derivative export to a separate Runbook representation.**

This PR must define how the Beat-first model appears during preparation.

Answer:

- Is Plan editing the same admitted Playable work object directly?
- If a free-form planning document exists, how is material explicitly adopted?
- How does the GM create/reorder Beats?
- How does the GM create/reorder Scenes within Beats?
- How are Decisions/Options/consequences authored without turning Plan into a graph editor?
- How does the authoring view preview what Play will project?
- Which semantics must be visible during authoring so Play does not surprise the GM later?

Do not solve this by reintroducing an opaque “Export to Runbook” transform.

### 3.9 Cockpit interaction contract

Write the desktop/table interaction contract independent of exact CSS.

Specify at least these states:

1. **Resume / choose / start**
2. **READY current-moment cockpit with no active Decision**
3. **READY cockpit with active Decision and Options**
4. **Decision selected / consequence and changed relevance visible**
5. **Runbook full-structure view**
6. **context projection open (NPC/Threat/Rule/etc.)**
7. **return from projection to exact current moment**
8. **Combat launch / return context boundary** — interaction only, no Combat schema
9. **warning / incomplete state**
10. **narrow viewport degradation** — conceptual priority, not pixel styling

For each state identify:

- dominant information;
- durable mutation available;
- local-only interaction state;
- exit/return behavior;
- what must remain visible for orientation.

### 3.10 `At a Glance` / relevant-now contract

The target contains an `At a Glance` region. Do not turn that mock panel into a
fixed schema without evidence.

Define it as a projection contract:

- which authorities may contribute;
- how current Beat/Scene references seed it;
- what Runtime may contribute;
- how exact Mechanics/Combat links are represented;
- what must be curated versus exhaustive;
- what happens when there is nothing relevant.

Full graph adjacency remains Advanced / another projection, not the default
cockpit payload.

### 3.11 Accessibility and table-speed interaction

The design must retain the successful #626 readability baseline and specify
interaction expectations such as:

- current/selected state is recognizable without color alone;
- primary controls remain keyboard reachable;
- contextual panel close returns focus sensibly;
- high-frequency actions do not require tiny targets;
- dense structural metadata does not dominate authored content;
- warnings remain distinct from prose.

Do not freeze exact CSS values here.

---

## 4. Exclusive write lease

This is a **design/architecture PR**. No production code is allowed.

### 4.1 Primary design outputs

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Design/DESIGN-play-current-moment-cockpit.md` | reviewed interaction + state contract derived from approved target |
| Modify | `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md` | freeze only the architecture decisions resolved by this review: containment, Runtime boundary, migration/rebase posture |
| Modify | `Docs/Design/DESIGN-play-surface-projection.md` | align projection behavior with reviewed cockpit interaction contract |
| Modify | `Docs/Design/DESIGN-playable-authoring-and-adoption.md` | align Plan→Playable authoring/adoption with reviewed Beat-first model |

The approved target remains:

- `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`
- `Docs/Design/assets/play-surface-gm-cockpit-target.webp`

Those two paths are **read-only reference** for this PR unless the operator
explicitly requests a target revision during review.

### 4.2 Successor implementation handoff

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md` | first atomic implementation slice selected by the reviewed design |

The successor handoff must select **one independently useful capability**, not
attempt the whole cockpit in one PR.

A likely first slice is the new Playable grammar/manifest foundation, but the
design review must choose the actual first seam after resolving the contract.
Do not pre-authorize UI implementation around an unresolved wire shape.

### 4.3 Backward-looking state-authority sync

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-table-readability-dogfood.md` | mark #626 MERGED / HISTORICAL with exact merge and 4-cycle truth |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | consume #626, close Lane A2, select this design gate as current Play structural work |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | consume #626 while keeping CR-U17 false overall |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | re-anchor parent acceptance state to merged #626 + current reviewed design gate |
| Modify | `Docs/Design/INDEX-design-agent-source-set.md` | include/refresh approved cockpit design authority set only if the index claims the active set |
| Modify | `Docs/Sources/design-agent/README.md` | repository export basis only if required by the same source-set refresh |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` | byte-identical mirror when canonical index changes |

Project Sources snapshot date remains operator-managed. Do not advance it merely
because repo-resident mirrors change.

### 4.4 This handoff

This file is design authority for dispatch and is read-only to the design
worker unless a discovered contradiction requires an explicit steward handback.
Do not edit the handoff merely to make implementation easier.

### 4.5 Explicitly forbidden paths

No changes anywhere under:

```text
apps/**
packages/**
tests/**
scripts/**
out/**
```

No production TypeScript/React/Python/Ruby/SQL/CSS.
No migration files.
No generated Runtime state.
No screenshots replacing the approved anchor.

If executable code is needed to prove the design, stop and return to stewardship;
that is a separate implementation slice.

---

## 5. Explicit non-goals / critique gates

### 5.1 Do not design a generic workflow engine

The product needs authored Decisions, Options, consequences, and changed
relevance. That does not justify arbitrary condition/action programming.

If the design starts producing:

```text
if/else expression language
arbitrary event bus
universal state reducer
world-rule DSL
campaign-agnostic BPMN graph
```

stop and simplify.

### 5.2 Do not mistake the mockup for data authority

Names, numeric values, labels, cards, icons, and example NPC/Threat content in
the image are illustrative. They are not schema requirements and are not
campaign canon.

### 5.3 Do not preserve Scene-first wiring for implementation convenience

The C2S27 dogfood already falsified the current Scene-first table organization
as the target model. Do not create a visual Beat wrapper over the old containment
and call the redesign complete.

### 5.4 Do not erase useful existing primitives unnecessarily

Stable IDs, Run CAS, exact Runbook revision binding, immutable manifest proof,
explicit Start Run, active-Run continuity, and preserve-only rebase are proven
primitives. Change them only where the Beat-first contract actually requires a
new version or semantic boundary.

### 5.5 Do not freeze aesthetics

The target is excellent enough to establish hierarchy. It is not evidence that
we should spend this PR choosing final shadows, purple values, animation curves,
or icon families.

### 5.6 Combat remains parallel domain work

This PR can define the cockpit's interaction seam to Combat, but cannot decide
Combat persistence internals. If Lane B becomes dispatchable during this PR,
that remains a separate write lease and PR.

---

## 6. Required design examples

The reviewed contract must include concrete examples. Abstract diagrams alone
are insufficient.

### Example A — current moment without a Decision

Use representative real Playable material and show:

```text
Run
→ current Beat
→ current Scene
→ objective / pressure
→ relevant-now references
→ no active Decision
```

Show what is durable versus projection-only.

### Example B — Decision changes later relevance

Use a generic but concrete authored Decision:

```text
Decision D1
  Option O1
  Option O2
```

Show:

- authored transition/consequence data;
- Runtime selection;
- resulting relevance projection;
- operator override/reopen behavior if supported;
- what is *not* automatically mutated.

### Example C — C2S27-style table pressure

Use repository evidence rather than invented canon to walk a moment where the
party is under immediate pressure and the GM needs current Beat, current Scene,
threats/NPC context, notes, and a possible branch without navigating away.

The example should prove the target can represent a messy live moment, not only
a clean branching tutorial.

### Example D — old Run across the grammar boundary

Show one old Scene-first Run and one new Beat-first Playable revision.
Demonstrate exactly what migration/rebase does or refuses to do.

### Example E — Plan authors what Play will run

Show the same Beat/Scene/Decision in Plan authoring and Play projection.
Demonstrate that no lossy export/transformation drops semantic blocks or stable
identity.

---

## 7. Evidence required for review

Because this is a design PR, tests are not the acceptance boundary. Precision,
consistency, and implementation readiness are.

### 7.1 Repository hygiene

```bash
git diff --check

git diff --name-only <dispatch-base>...HEAD
```

Every changed path must be in §4.

Canonical/mirror pairs must be byte-identical where touched.

### 7.2 Design consistency audit

The PR description or a checked-in appendix must provide a table like:

| Concern | Existing truth | Reviewed decision | Authority updated |
|---|---|---|---|
| Beat/Scene containment | Beat-first direction, wire unresolved | ... | architecture/design |
| Decision ownership | stable Choice/Option primitive, exact containment unresolved | ... | architecture/design |
| Manifest | Scene-first P2B1 | ... | architecture |
| current position | Scene-first relationship constraint | ... | architecture |
| relevance | product requirement, persistence unresolved | ... | design/architecture |
| old Runs | old manifest/runtime exist | ... | architecture |
| rebase | preserve-only P2C | ... | architecture |
| Plan→Playable | no lossy export | ... | authoring design |
| cockpit UX | approved target | ... | cockpit design |
| Combat seam | Combat-owned | ... | cockpit design only |

No row may rely on “implementation will decide” for a product/architecture
question needed by the first implementation slice.

### 7.3 State-transition table

Include one explicit table for the table-running state model, covering at least:

```text
open/resume Run
select Beat
select Scene
resolve/unresolve Beat
select Decision Option
Decision changes relevance
open/close contextual projection
switch Table/Runbook
Start New / choose another Run
launch/return Combat context
```

For each action state whether it is:

- durable Runtime mutation;
- Playable authoring mutation;
- local projection/focus only;
- cross-domain explicit action.

### 7.4 Migration/rebase matrix

The matrix required by §3.6 must be explicit enough that an implementation
reviewer can tell whether a test is proving the right behavior.

### 7.5 Implementation decomposition

Before final review, propose the implementation sequence as atomic capabilities.

For each proposed slice include:

```text
capability
owning flow
one merge-ready invariant
expected production write lease
runtime/state collisions
predecessor
what remains false after merge
```

Only the **first** selected slice receives the successor implementation handoff
in this PR.

### 7.6 Roadmap review

Record one deliberate disposition:

```text
ROADMAP_REVIEW — UPDATED
```

is expected because this PR freezes previously unresolved structural design.

If the reviewer believes `NO DESIGN CHANGE` is appropriate, that itself is a
red flag: this PR exists because the current architecture explicitly says the
wire grammar is unresolved.

### 7.7 Formal review

One exact distinct design-PR head receives one formal reviewer judgment.

Same-account GitHub limitation still applies: use COMMENT with explicit
`PASS` / `REQUEST-CHANGES-equivalent` when GitHub cannot submit APPROVE or
REQUEST_CHANGES.

Any repair commit creates a new head and therefore another review cycle.

---

## 8. Reviewer contract

The reviewer must independently verify:

1. the design branch was re-anchored from current `main`;
2. #626 predecessor truth is synchronized exactly: final head `f26e6449...`, merge `a56cf4ab...`, **4 formal review cycles**, final PASS-equivalent;
3. the approved cockpit target remains an anchor rather than a pixel/schema spec;
4. no production code changed;
5. canonical Beat/Scene/Decision containment is singular and unambiguous;
6. stable identity survives ordinary title/prose edits;
7. Playable serialization is implementable and versioned where needed;
8. manifest membership/version semantics are explicit;
9. current Beat/current Scene Runtime semantics are explicit;
10. local focus state is not accidentally persisted as authority;
11. Decision selection, consequence presentation, and changed relevance have a minimal explicit contract;
12. the design does not create a general workflow/rules engine;
13. derived relevance is preferred unless persistence is demonstrably necessary;
14. operator override/unexpected play is not trapped by authored branching;
15. old Scene-first Runs/manifests have a truthful support/migration posture;
16. P2C rebase behavior across the structural boundary is explicit and fail-closed where needed;
17. Plan authors/adopts exact Playable material without lossy export;
18. Play cockpit interaction preserves exact current moment when opening/closing context;
19. Combat remains Combat-owned;
20. `At a Glance` is a contextual projection, not a universal object schema;
21. the C2S27-style messy-table example is believable under the contract;
22. the design consistency table has no implementation-deferring holes needed by the first slice;
23. the implementation decomposition is atomic rather than one giant rewrite;
24. the successor handoff authorizes exactly one first implementation capability;
25. roadmap/state mirrors are truthful and byte-identical where required.

A design that looks elegant but leaves the worker to decide containment,
migration, relevance, or Plan→Playable semantics in code is **REQUEST CHANGES**.

---

## 9. Design posture / steward defaults

These are the current preferred defaults. They are critique targets, not hidden
requirements. If the design chooses differently, it must explain the product or
architecture reason.

### 9.1 Beat is the durable session-scale container

Prefer:

```text
Runbook → Beat → Scene
```

over a cosmetic Beat grouping layered on Scene-first storage.

### 9.2 Current Scene is subordinate and may be optional

A Beat is the thing the GM is deliberately trying to run. A Scene is the
specific situation currently realizing it. This suggests `currentSceneId?`
should be optional, provided the design gives the operator a coherent Beat-only
state.

### 9.3 Decisions are first-class but not a rules engine

Prefer stable Choice/Decision + Option identity and authored transition /
consequence references. Persist the selection. Derive relevance where possible.
Require explicit GM action for narrative state changes the system cannot safely
infer.

### 9.4 Projection should hide irrelevance before deleting possibility

Unexpected table play is normal. Prefer de-emphasizing/marking authored material
as currently irrelevant over destructively erasing branches from the Runbook.
The GM should be able to inspect full structure and recover material.

### 9.5 Full Runbook remains the escape hatch

The cockpit is optimized for now; Runbook is the truthful full authored
structure. Do not make the cockpit the only way to discover prepared material.

### 9.6 Plan and Play are two projections over the same Playable truth

Plan is the workshop. Play is the table instrument. They should not drift into
two semantic copies connected by an export button.

---

## 10. Post-merge successor posture

If this design PR passes and merges, the repository should be able to state:

```text
Lane A1 active-Run continuity:
  implemented + live-validated

Lane A2 readability:
  implemented + dogfooded

GM cockpit UX target:
  approved

Beat/Scene/Decision + Plan→Playable contract:
  reviewed and implementation-ready

first implementation slice:
  selected by HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md

still unresolved / separate:
  remaining cockpit implementation slices
  durable Combat / Lane B
  cross-worktree persistence outside proven domain seams
  P3B object-sheet sequencing
  P4 Add to Combat sequencing
  final aesthetic polish
```

Do not pre-authorize the second implementation slice. Re-anchor after the first
implementation merge and let evidence choose the next seam.
