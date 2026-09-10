# HANDOFF — DOGFOOD-CONTINUITY: Stage 4A opened World-object usefulness

**Created:** 2026-09-09
**Status:** DESIGN READY — dispatch only after PR #697 merges to `main`
**Flow / owner:** `DOGFOOD-CONTINUITY`
**Direction:** DESIGN → CODE → REVIEW → MERGE → HUMAN DOGFOOD
**Canonical handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-4a-opened-object-usefulness-v1.md`
**Suggested branch:** `dogfood-continuity/stage-4a-opened-object-usefulness-v1`
**Suggested PR title:** `DOGFOOD-CONTINUITY: make opened World objects useful to inspect`

> Dispatch from a clean checkout of the actual post-#697 `main`. Do not substitute the current pre-merge SHA into this handoff. Record the exact #697 accepted head and merge SHA during re-anchor.

---

## 0. Re-anchor

PR #697 established the semantic substrate this PR consumes:

```text
selected node id
  ↓
DungeonMind complete selected-object read
  ↓
complete admitted World-cross-campaign one-hop object
  +
one APP-STATE exact-source batch hydration
  ↓
same semantic fingerprint across consumers
```

The important product result is now:

> **Where an object is actually opened through the complete-object path, the World payload is present and trustworthy.**

Human dogfood exposed the next barrier as presentation/composition rather than retrieval correctness.

### Dogfood findings that motivate this slice

**Plan Expand is the positive reference.**

Search → place Karsemine → Expand produces the intended kind of object inspection. Different surface chrome is acceptable; semantic identity does not require identical layout.

**Ingest currently has dead progressive disclosure.**

Karsemine has 15 admitted relationships. The card displays eight and renders:

```text
+7 more
```

but provides no interaction for seeing the omitted seven.

Those seven relationships are already in the complete-object payload. This is not graph truncation.

**Temporal display is already conceptually sufficient for this slice.**

A fact observed in S24 while viewing S25 should continue to present as `C2 · S24`, another truthful temporal stamp, or unknown where authority is unknown. Stage 4A does not create a new timeline/reducer.

**Technical identity is over-prominent when exposed.**

Node IDs, revision IDs, semantic fingerprints, completeness internals, raw scope/debug values, and similar diagnostic material are useful for builders but do not belong in the ordinary GM reading path.

### Human STOP failures that do not belong to this PR

Do not reinterpret these as Stage 4A implementation requirements:

```text
Agent unavailable from Ingest / Build
  → Stage 7A / Agent-surface composition

Glowkindle absent from C2 generic search
  → generic retrieval/search policy

C1 object rejected by generic C2 lens
  → generic lens/retrieval contract, not complete-object-by-id

Build has no real C2 document to inhabit
  → material/template/authoring continuity

Play has no Runbook to inhabit
  → Play material/template continuity

every recap phrase is not clickable
  → intentional; recap prose is not a graph-browser dump

Threat-specific visual treatment
  → later Stage 4 capability

session-navigation polish
  → later Stage 4 capability
```

---

## 1. Candidate decomposition

The Human STOP produced several independently useful capabilities.

| Candidate                                | Disposition                            | Reason                                                                                   |
| ---------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Opened-object progressive disclosure     | **KEEP — this PR**                     | Complete payload already exists; current UI hides reachable truth behind dead `+N` copy  |
| Technical/debug identity behind Advanced | **KEEP — same presentation invariant** | Same component boundary and same goal: clean normal scan path without losing diagnostics |
| Recap mention/pill density redesign      | **NOT THIS PR**                        | Independently useful visual/editorial decision                                           |
| Threat-specific projection               | **NOT THIS PR**                        | Distinct object class and visual contract                                                |
| Agent available on current surface       | **NOT THIS PR**                        | Stage 7A                                                                                 |
| Generic World-wide search                | **NOT THIS PR**                        | Retrieval-policy successor                                                               |
| Build/Play templates/material creation   | **NOT THIS PR**                        | Separate durable-content capability                                                      |
| Timeline/current-fiction reducer         | **NOT THIS PR**                        | Separate temporal semantics capability                                                   |

### One capability

**Opened World-object progressive-disclosure presentation**

Merge invariant:

> **An opened complete World object is compact by default but never strands already-loaded relationships behind non-interactive omission text. The GM can reveal the object's full admitted relationship set without another World read, can return to the compact view, retains truthful campaign/session/provenance presentation, and sees technical identity/debug information only through an explicit Advanced disclosure.**

---

## 2. Product story

The canonical witness is Karsemine in C2 Session 25.

I click Karsemine.

The card should initially be readable rather than dumping fifteen relationship rows into the page.

I see a useful compact set.

At the bottom I see an actual affordance such as:

```text
Show all 15 relationships
```

or:

```text
Show 7 more
```

I activate it.

The same already-loaded object now shows all fifteen relationships. No second World request occurs.

S24 relationships still say things like:

```text
C2 · S24
Hunter's Mark · holds
```

S25 material remains distinguishable.

A relationship lacking durable source prose remains visible without invented prose.

I can collapse the object again.

If I need implementation/debug identity, I deliberately open:

```text
Advanced
```

Normal reading does not require looking at node IDs, revisions, fingerprints, or graph plumbing.

---

## 3. Presentation law: complete before focus, compact before dump

#697 established:

```text
complete object truth
    ↓
surface focus / presentation
```

Stage 4A adds:

```text
complete semantic payload
    ↓
deterministic presentation ordering
    ↓
compact default window
    ↓
explicit Show all
```

The compact view is a presentation choice, **not semantic truncation**.

Therefore:

* server `completeness=complete` remains complete even while eight rows are visible;
* UI omission must never be represented as graph truncation;
* `partial` complete-object responses must continue to use #697's explicit partial warning;
* Show all must use the already-loaded relationship array;
* Show all must not issue another `/complete-object`, search, neighborhood, provenance, or source request.

### Ordering

Do not invent a new relationship relevance model in this PR.

Preserve the current deterministic ordering contract unless a correctness bug requires otherwise:

1. earliest numeric session first;
2. stable label ordering;
3. stable edge-id tie break;
4. distinct edges remain distinct even when target/predicate resembles another row.

A later Stage 4 slice may reconsider relevance/ranking after dogfood.

---

## 4. Progressive-disclosure contract

Current behavior effectively performs:

```text
sorted relationships
  → first 8
  → dead "+N more"
```

Replace it with stateful progressive disclosure.

### Default state

If relationship count is `0`:

* render no empty relationship noise.

If relationship count is `1..8`:

* render all relationships;
* render no Show-all control.

If relationship count is `>8`:

* render the first eight;
* render an interactive disclosure control containing the real total or omitted count.

Acceptable product copy includes:

```text
Show all 15 relationships
```

Preferred over a bare implementation-oriented:

```text
+7 more
```

### Expanded state

When expanded:

* render every relationship from the already-loaded semantic object;
* preserve deterministic ordering;
* preserve relationship click/navigation behavior;
* preserve source/provenance rendering;
* preserve session/campaign stamps;
* render a clear collapse affordance such as `Show fewer`.

### Object-change behavior

When the selected object changes:

```text
expanded state → reset to compact
```

Do not carry Karsemine's Show-all state into Stafl, Lysandra, etc.

### Partial results

If #697 supplies `completeness=partial`:

* continue showing the explicit partial warning;
* progressive disclosure may reveal all rows actually returned;
* UI must not imply those rows are the full World object.

---

## 5. Advanced disclosure contract

Technical information is useful, but it is not primary GM content.

Add one shared explicit disclosure:

```text
Advanced
```

closed by default.

### Advanced may include existing available diagnostics such as

```text
World id
node id
exact World revision
semantic fingerprint
complete / partial status
relationship count
assertion count
source-binding count
origin surface
```

Only expose fields already available from the complete-object result or existing presentation state.

Do not create new server contracts merely to populate Advanced.

### Advanced must not

* contain generated explanations;
* dump raw model prompts;
* expose source prose solely as diagnostics;
* add Agent token/cost traces;
* add arbitrary JSON dumps;
* move ordinary provenance that a GM needs to understand a fact out of the normal product experience.

### Existing Details vs Advanced

Preserve the conceptual distinction:

**Details** may remain user-facing information such as evidence/source availability or ordinary visibility information.

**Advanced** owns implementation/identity diagnostics.

Raw node IDs should not appear in the ordinary card scan path.

---

## 6. Cross-surface rule

This remains a shared graph-object presentation capability.

The behavior must come from the shared graph-object layer, not five copies.

Expected consumers include:

```text
Ingest opened object
Plan expanded reference
Build graph-object context
Play World-object sheet
other consumers of GraphObjectCard / GraphObjectProjectionCard
```

Surface-specific chrome may remain different.

Examples:

* Plan may retain Memory tools/actions.
* Ingest may remain a recap-side panel.
* Build may retain document admission/action controls.
* Play may retain Runbook-local material around the World object.

The relationship disclosure semantics should not diverge by surface.

### Glance remains glance

Compact mention/chip/hover interactions are not required to show the whole object.

The rule is:

```text
mention / chip glance
  → may remain lightweight

explicit open / expand
  → complete-object presentation with progressive disclosure
```

Do not turn every recap mention into a persistent expanded graph card.

---

## 7. Relationship navigation

This PR does not invent a new navigation contract.

When a revealed relationship already has a valid existing relationship-open handler:

```text
Show all
  ↓
click previously omitted relationship
  ↓
existing exact target-id navigation
  ↓
target opens through existing complete-object path
```

Regression-test this because Show all is useless if newly visible rows are inert.

If a particular surface lacks a relationship-navigation binding, preserve its truthful disabled/non-interactive state rather than inventing a new surface navigation architecture here.

Do not use label/alias guessing to compensate for missing exact target identity.

---

## 8. Provenance and temporal presentation

Do not redesign temporal semantics.

Preserve existing product-facing stamps such as:

```text
C2 · S24
C2 · S25
C1 · S10
```

Unknown remains unknown.

Do not derive fictional-current state.

Do not rewrite source session to the current recap session.

### Provenance

For rows where source provenance is enabled on that surface:

* `excerpt_ready` prose remains available;
* missing durable prose remains honestly absent;
* Show all must not discard provenance attached to rows beyond the initial eight.

No additional source fetch may occur merely because the user expanded the local list.

---

## 9. Expected implementation seam

Prefer the existing shared presentation layer:

```text
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx
apps/live-control-ui/src/graphObjectCard/graphObjectDisplay.ts
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx
```

Likely supporting seam:

```text
apps/live-control-ui/src/graphObjectCard/types.ts
```

If Advanced needs complete-result metadata rather than card-model data, prefer one shared presentation component/slot at the graph-reference boundary rather than teaching each surface to rebuild technical details.

Possible bounded addition:

```text
apps/live-control-ui/src/graphReference/CompleteWorldObjectAdvancedDetails.tsx
```

and its focused test.

Surface wrappers may change only as needed to pass the shared presentation metadata through:

```text
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx
apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx
apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx
```

Use the existing graph-object styles. Do not perform a stylesheet-ownership migration as hidden cleanup unless implementation proves it unavoidable.

### Existing parked Stage 4 experiments

If a parked/staged graph-object copy experiment still exists, inspect it as design evidence only.

Do not wholesale cherry-pick it.

The handoff is authority for this PR.

---

## 10. Network and performance invariant

Show all / Show fewer is local presentation state.

Expected network delta:

```text
open object
  complete-object read       existing behavior
  APP source batch           existing behavior

Show all
  World reads                0
  APP reads                  0
  source reads               0

Show fewer
  World reads                0
  APP reads                  0
```

Advanced open/close is also local presentation state.

Do not add caching infrastructure or prefetching in this PR.

---

## 11. Automated evidence

### Shared relationship presentation

Prove:

1. `0` relationships → no disclosure control.
2. `8` relationships → all eight visible, no disclosure control.
3. `15` relationships → eight visible initially.
4. `15` relationships → interactive copy communicates the omitted/full count.
5. activating Show all renders all fifteen.
6. activating Show fewer restores eight.
7. order is identical before/after expansion for the original eight.
8. distinct edges to the same target remain distinct.
9. object identity change resets to compact.
10. no network/API callback occurs merely from Show all / Show fewer.

### Relationship semantics

Prove:

11. `C2 · S24` remains S24 under S25 focus.
12. unknown temporal/session presentation stays unknown rather than becoming S25.
13. relationship provenance on an initially omitted row survives expansion.
14. `source_not_durable` / missing prose remains honest.

### Navigation

Prove:

15. an initially omitted row becomes clickable after Show all when a handler exists.
16. its exact relationship row / target identity is passed to the existing handler.
17. no label-based identity inference is added.

### Partiality

Prove:

18. a server `partial` result still renders the #697 partial warning.
19. Show all cannot visually erase or contradict partial status.

### Advanced

Prove:

20. technical identity is not visible by default.
21. opening Advanced reveals the available exact node/revision/fingerprint/completeness diagnostics.
22. closing Advanced restores the normal scan path.
23. Advanced does not change the semantic object or issue network requests.

### Cross-surface

At minimum, focused tests must establish the shared component behavior survives through:

```text
Ingest
Plan
Build
Play
```

Do not duplicate the same behavioral logic into four surface tests when one shared test plus thin wrapper tests proves the contract.

### Production gate

Because this PR changes TypeScript production UI paths:

```bash
npm test -- --run <focused suites>
npm run build
```

must pass on the exact reviewed head.

---

## 12. Live dogfood witnesses

Use real durable C1/C2 state.

### Witness A — Karsemine from C2S25 Ingest

Open Karsemine.

Require:

```text
complete-object status            complete
actual relationships              15
initial visible relationships     8
interactive Show-all present      yes
Show all                          15 visible
Show fewer                        8 visible
S24 stamp remains S24             yes
S25 material remains distinct     yes
manual-seed edge remains honest   yes
new request on Show all           no
```

Click at least one relationship that was not in the initial eight if the surface has an active navigation binding.

### Witness B — Karsemine from Plan Expand

Require the same underlying fifteen relationship identities and same deterministic ordering.

Plan-specific chrome/actions may differ.

The objective is not pixel identity.

### Witness C — high-degree object

Use Stafl or the highest convenient admitted object.

Require:

* all relationships reachable through Show all;
* no pathological layout break;
* no additional World/source call from expansion;
* Advanced remains secondary.

### Build / Play

If no ordinary real document/Runbook exists to inhabit, do **not** fabricate one merely to claim human dogfood.

Automated wrapper tests are sufficient for this PR.

Missing real Build/Play material remains separately routed.

---

## 13. Explicitly out of scope

Do not absorb:

* new DungeonMind reads;
* changes to `get_complete_object`;
* new APP-STATE source adoption;
* generic Agent World-wide search;
* Agent availability on Ingest/Build/Play;
* Stage 7A;
* Build document templates;
* Play Runbook templates;
* historical Play fabrication;
* linking every recap mention;
* pill-density redesign;
* Threat/statblock redesign;
* recap previous/next navigation redesign;
* current-fiction-state reduction;
* timeline UI;
* relationship relevance/ranking experiments;
* graph writes;
* source regeneration;
* persistent caching/prefetch;
* global CSS architecture cleanup;
* full telemetry/log viewer.

Stage 4 remains **NOT DONE** after this PR.

---

## 14. Stop conditions

STOP and rebrief if:

* showing omitted rows requires a second World read;
* the complete semantic payload reaching the card actually contains only the first eight rows;
* different surfaces require independent relationship selection/sorting algorithms;
* fixing presentation requires changing DungeonMind truth/retrieval;
* implementation needs generic Agent search changes;
* implementation broadens Build write admission;
* an exact relationship target cannot be preserved and the proposed workaround is label/alias guessing;
* Advanced requires a new backend diagnostics contract;
* Threat-specific behavior becomes necessary to make generic object presentation work;
* implementation starts changing recap mention-link density rather than opened-object presentation.

Report using:

```text
Stop condition:
Owning boundary:
Observed behavior:
Missing presentation contract:
Why Stage 4A cannot safely compensate:
Proposed successor:
State-authority update:
```

---

## 15. Write lease

Expected production lease:

```text
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.tsx
apps/live-control-ui/src/graphObjectCard/graphObjectDisplay.ts
apps/live-control-ui/src/graphObjectCard/types.ts
apps/live-control-ui/src/graphObjectCard/GraphObjectCard.test.tsx

apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.tsx
apps/live-control-ui/src/graphReference/ResolvedGraphObjectProjection.test.tsx
```

Bounded discovery may add one shared Advanced component and thin wrapper tests/props in:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx
apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx
apps/live-control-ui/src/playSurface/reference/PlayGraphObjectSheet.tsx
apps/live-control-ui/src/planSurface/planSurface.css
```

State-authority sync:

```text
Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-4a-opened-object-usefulness-v1.md
```

Do not silently expand beyond this lease.

If a materially new production domain is required, STOP and rebrief.

---

## 16. Required predecessor sync

At dispatch, update the exact truth from `main`:

```text
PR #697
  merge SHA:
  accepted CODE head:
  review cycles:
  Human STOP:
    NOT PASSED as all-surface end-state
    successor-routed rather than #697 correctness failure
```

Record the Human STOP findings accurately:

```text
complete-object retrieval             works where object opens
Plan Expand                           positive reference
Ingest dead +N                        Stage 4A barrier
technical/debug prominence            Stage 4A barrier
Agent current-surface availability    Stage 7A
generic C2 search excluding C1        retrieval-policy successor
Build/Play empty material             template/material successors
```

Do not mark Stage 4 DONE.

Mark only:

```text
Stage 4A — opened-object usefulness
```

when this PR itself passes review and dogfood.

---

## 17. Acceptance rubric

* [ ] One capability remains: opened-object progressive-disclosure presentation.
* [ ] #697 complete-object semantics remain unchanged.
* [ ] Complete server payload is never mislabeled as UI truncation.
* [ ] Partial server payload remains explicitly partial.
* [ ] More than eight relationships produces an interactive disclosure, not dead `+N` text.
* [ ] Show all reveals every already-loaded relationship.
* [ ] Show fewer restores the compact view.
* [ ] Expansion/collapse performs zero additional World or APP reads.
* [ ] Deterministic relationship ordering is preserved.
* [ ] S24 remains visibly S24 under S25 focus.
* [ ] Missing source prose remains honest.
* [ ] Newly revealed relationships retain existing navigation behavior.
* [ ] Technical graph identity is hidden by default.
* [ ] Advanced exposes available diagnostics without adding backend contracts.
* [ ] Ingest and Plan human witnesses pass.
* [ ] Shared behavior remains valid through Build/Play wrapper tests.
* [ ] Stage 4 remains NOT DONE.
* [ ] Stage 7A remains NOT DONE.
* [ ] Generic Agent retrieval policy remains unchanged.
* [ ] Production UI build passes on exact reviewed head.
* [ ] Human STOP is performed before dispatching another Stage 4 slice.

---

## 18. Human STOP — “Can I actually inspect the whole thing?”

After merge, stop.

Do not automatically dispatch another Stage 4 PR.

Use C1/C2 naturally.

Ask:

> **When I open a person, place, item, or faction, does DungeonBuddy give me a useful compact view without hiding the rest of what it already knows?**

Specifically:

* Does the initial object feel readable rather than overwhelming?
* Is it obvious that additional relationships exist?
* Can I reveal all of them?
* Does Show all feel fast and local?
* Are campaign/session stamps understandable?
* Does source context help rather than dominate?
* Are internal IDs/debug data out of the way?
* Can I follow a relationship without losing confidence in what object I am inspecting?
* Does Ingest now feel materially closer to the useful Plan Expand experience without needing to become visually identical?

Classify failures:

```text
A — useful as-is
E — trustworthy but presentation/copy still poor
R — relationship disclosure/navigation defect
P — provenance presentation problem
T — temporal presentation problem
D — debug/technical noise still intrudes
X — failure belongs to another capability
```

If the result is mostly `A/E`, use that STOP to decide the next Stage 4 capability.

Do not pre-author it here.

