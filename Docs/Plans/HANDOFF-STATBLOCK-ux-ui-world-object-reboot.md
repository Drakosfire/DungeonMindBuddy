# Steward Handoff — Statblock UX/UI and first World Graph object

**Flow:** `STATBLOCK`
**Status:** `REBOOT — UX/UI and product dogfood focus`
**Created:** 2026-08-06
**Repository:** `Drakosfire/DungeonMindBuddy`
**Canonical handoff path:** `Docs/Plans/HANDOFF-STATBLOCK-ux-ui-world-object-reboot.md`
**Canonical integration base:** `origin/main` at `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`
**Merged predecessor:** PR [#508](https://github.com/Drakosfire/DungeonMindBuddy/pull/508), `STATBLOCK: publish accepted Threat from Workbench`
**Reboot branch at authoring:** `feat/statblock-ux-ui-world-object-reboot`

This is a fresh-context steward handoff. It deliberately does not reopen the
publication bridge as unfinished implementation. The governed publication path
is the baseline. The next line of work is to make the Statblock experience
useful, legible, and campaign-facing while dogfooding the Statblock as the
first authored World Graph object.

---

## 0. Read this first

The current product has crossed an important boundary:

```text
The Statblock can now be generated, reviewed, accepted, published as a
governed Threat + exact binding, rediscovered from Plan, and found by Hermes.

The product still does not feel like a finished GM authoring experience.
```

The next agent should not infer “more publication hardening” from the many
publication files. Those files are now durable authority and recovery
contracts. The UX/UI reboot should preserve them and work on the surfaces that
make the resulting object understandable and useful.

The immediate product question is:

> Can a GM encounter the newly authored Threat in the product and understand
> what it is, how it plays, and which exact mechanics it uses without being
> forced to read IDs, digests, graph revisions, or ledger state?

The first recommended implementation slice is a Plan-hosted, campaign-useful
Threat glance/card backed by the existing exact Threat projection. It should
improve presentation without adding a new graph write, changing identity
resolution, changing mechanics authority, or introducing a placement store.

---

## 1. Current-state authority and re-anchor

### 1.1 Canonical precedence

When documents disagree, use this order:

1. Executable code and tests on the current `origin/main`.
2. The accepted lifecycle decision:
   `Docs/Design/DECISION-grounded-authored-world-object-lifecycle.md`
3. The active domain design:
   `Docs/Design/DESIGN-authored-threat-statblock-domain-contract.md`
4. The merged publication handoff:
   `Docs/Plans/HANDOFF-magic-d3-workbench-threat-publication.md`
5. The latest real dogfood report:
   `Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md`
6. The current backlog:
   `Backlog.md`
7. Older handoffs, trackers, PR descriptions, and chat summaries.

Several older SBW handoffs and the publication tracker still describe
SBW09/SBW10 as future or blocked. That sequencing text is historical drift.
Do not use it to decide whether publication, query/hydration, or projection
exists. The merged implementation and the MAGIC-D3 report are authoritative
for the current state.

### 1.2 Re-anchor commands

Before starting a new implementation slice:

```bash
git fetch origin main
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Confirm that `main` contains the merged publication bridge. The reboot should
branch from current `main`, not from the old PR branch
`feat/statblock-magic-d3-workbench-threat-publication`.

The checked-out authoring baseline for this handoff was:

```text
origin/main: 9d4f5a3005f87d07147c03d8eee499af3bd57aa3
old PR head: f7083392675245d455699fd2aa66faf1ec6c697f
```

The two modified files under
`evals/c2_live_prep/live/session_22/` are live-session artifacts. They are
local noise, not implementation work, and must not be committed or reset as
part of this reboot.

### 1.3 Relevant backlog signal

The active project backlog entry
`MAGIC-D3: Threat glance/Hermes must be campaign-fun, not metadata` is the
direct product input for this reboot. It records:

- metadata-heavy hover/glance;
- Plan reload/navigation latency;
- Hermes silence and long agent loops;
- the need to lead with encounter usefulness;
- existing Statblock Generator and DnD-page visual grammar worth reusing.

Related READY entries cover Hermes dynamic artifacts, optimistic/live-progress
UX, graph chips, and performance telemetry. They are related follow-ons, not
permission to widen the first slice into a new Hermes or graph platform.

---

## 2. Architecture decision: what the Statblock is

The accepted architecture is
`DECISION-grounded-authored-world-object-lifecycle.md`.

The first proving domain is **Threat + Statblock**. The durable object model is:

```text
ThreatDraft
  mutable DungeonBuddy-authored concept
        |
        | generate
        v
GeneratedStatblockCandidate
  transient typed proposal from DungeonMind
        |
        | review / edit / validate / accept
        v
StatblockRevision
  immutable exact mechanics truth
        |
        | governed graph publication
        v
Threat
  durable World Graph identity and relationships
        |
        | explicit exact binding
        v
ThreatStatblockBinding
  Threat → statblock_id + revision_id + digest
        |
        | derived read projection
        v
ThreatSheet / Plan reference / Hermes context
```

These are intentionally separate:

- **ThreatDraft** is mutable authored intent. It is not graph canon.
- **GeneratedStatblockCandidate** is a transient generated proposal. It is not
  accepted mechanics and does not own the graph lifecycle.
- **StatblockRevision** is immutable mechanics truth. A later mechanical edit
  creates a new revision; it does not overwrite the old one.
- **Threat** owns campaign identity, description, relationships, authority,
  and visibility in the World Graph.
- **ThreatStatblockBinding** connects a Threat to an exact resource revision.
- **Projection** is a derived user-facing view. It must not copy mechanics into
  the graph or silently select a newer revision.
- **Placement** is a later contextual use in a document, scene, encounter, or
  map. A graph binding or projection is not automatically a placement.
- **Runtime instance** is later mutable combat state. HP, conditions, and
  initiative must not mutate graph truth or the immutable revision.

The product north star is the complete loop:

```text
grounded campaign question
→ editable Threat description
→ typed statblock candidate
→ human review/edit/validation
→ accepted immutable mechanics revision
→ governed Threat identity and binding
→ useful Plan/Build/Play projection
→ exact placement/runtime use later
```

The current reboot begins at the projection/usefulness gap. It does not
collapse these ownership boundaries to make the UI easier.

---

## 3. What is shipped on `main`

### 3.1 Statblock Workbench

Primary module:

```text
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx
```

Important symbols and regions:

- `StatblockWorkbenchModule`
- `AcceptMechanicsFlow`
- `onCreateAndGenerate`
- `onValidateWorkingCopy`
- `refreshThreatDraftSnapshot`
- `loadCandidate`
- `runGenerateFromDraft`
- the `workflow_state === "mechanics_saved"` gate

The user-visible path is:

1. Enter or receive a Threat description.
2. Create a durable `ThreatDraftV1`.
3. Generate a typed candidate through the Buddy backend adapter.
4. Load the exact candidate and review it in the Workbench.
5. Edit the supported working-copy fields.
6. Validate the exact working copy.
7. Accept/save mechanics as an immutable DungeonMind revision.
8. Reopen the exact draft/candidate/revision state.
9. Enter the publication path only after mechanics are saved.

The dedicated editor is intentionally narrow:

```text
apps/live-control-ui/src/statblocks/editor/StatblockDefinitionEditor.tsx
```

The current direct controls cover the name, ability scores, primary AC, one
HP scalar, and rule-element names/rules text. Other typed mechanics are
shown through protected or advanced representations. This is not a complete
mechanics authoring surface.

Do not describe `mechanics_saved` as published. The acceptance contract means:

```text
mechanics_saved =
  an exact accepted (statblock_id, revision_id, definition_digest)
  is persisted and recorded on the ThreatDraft.

mechanics_saved !=
  a Threat exists in the World Graph.
```

Primary API methods are in
`apps/live-control-ui/src/api/liveApi.ts`:

- `createThreatDraft`
- `generateThreatDraftCandidate`
- `getThreatDraft`
- `getStatblockCandidate`
- `reviseThreatDraftCandidate`
- `validateStatblockDefinition`

Acceptance routes are owned by the live-control server:

- `POST /api/live/threat-drafts/{draft_id}/mechanics:accept`
- `GET /api/live/threat-drafts/{draft_id}/acceptance-operations/{operation_id}`
- `POST /api/live/threat-drafts/{draft_id}/acceptance-operations/{operation_id}:reconcile`

### 3.2 Governed Threat publication

The merged publication bridge is documented in:

```text
Docs/Plans/HANDOFF-magic-d3-workbench-threat-publication.md
```

The normal Workbench path is:

```text
Publish Threat
→ prepare identity candidates
→ explicit create-new / connect-existing / refuse decision
→ review sealed proposal
→ Confirm publish
→ exact durable commit/revision result
```

The exact chain is:

```text
draft_id
→ operation_id
→ resolution_id
→ proposal_id
→ commit_id
→ committed_revision_id
```

The publication panel is:

```text
apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.tsx
```

Its durable browser recovery pointer is:

```text
apps/live-control-ui/src/statblocks/publication/threatPublicationSession.ts
```

The pointer stores IDs and stage only. It does not store graph bodies,
mechanics bodies, candidate bodies, or authority claims.

The bridge now supports:

- explicit identity judgment;
- collision rejection and deterministic candidate handling;
- proposal review before graph mutation;
- typed 409/503 lifecycle envelopes;
- active-operation/busy recovery;
- refusal cancellation recovery;
- candidate and proposal retry/reread;
- exact commit reread after lost responses;
- exact commit-ID preservation across ambiguity;
- no fresh confirmation after an admitted or uncertain commit;
- honest `committed_unverified` state when storage succeeded but verification
  could not prove the final projection.

Publication route owners are:

```text
apps/live_control_server/routes/threat_publication.py
apps/live_control_server/routes/threat_publication_identity.py
apps/live_control_server/routes/threat_publication_proposals.py
apps/live_control_server/routes/threat_publication_commits.py
```

The first UX slice should treat this path as a frozen authority boundary. A
presentation change must not turn a projection click into an implicit graph
write or bypass the proposal/confirm journey.

### 3.3 Exact query and mechanics hydration

The read boundary is:

```text
apps/live_control_server/services/threat_query_hydration.py
apps/live_control_server/routes/threat_query_hydration.py
```

The primary service function is `query_threats_with_hydration`.

The request is exact about world/campaign scope and graph revision. It supports
name/alias/query matching, focus nodes, relationship discovery, and explicit
zero/one/many Threat results. For each returned
`uses_statblock` binding, it hydrates the exact DungeonMind revision named by:

```text
threat_node_id
binding_id
statblock_id
revision_id
definition_digest
```

There is no current-head, latest-revision, label, corpus-path, or first-binding
fallback. Binding states distinguish available, unavailable, missing exact
revision, integrity failure, and not requested.

The client mirrors the request/response types in
`apps/live-control-ui/src/api/types.ts`. The route is:

```text
POST /api/live/threats/query-hydration
```

### 3.4 Threat projection

The projection implementation is:

```text
apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx
apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts
```

Important symbols:

- `ThreatSheetProjection`
- `shouldRenderThreatSheetProjection`
- `CompactCoreStats`
- `ThreatRelationshipsSection`
- `buildThreatQueryHydrationRequest`
- `selectExactThreatHit`
- `buildThreatSheetViewModel`
- `sortThreatSheetBindings`
- `isExactResolvedThreat`

Current projection behavior:

- preserves exact graph scope and exact resolved node identity;
- refuses silent first-winner behavior when bindings are ambiguous;
- renders compact core mechanics only when a trusted exact binding is
  available;
- renders complete mechanics only from a complete trusted exact revision;
- retains honest unavailable/missing/integrity states;
- exposes relationship navigation and technical binding details;
- guards stale asynchronous results and changed selections.

This is the component family to improve for the first UX slice. Do not invent a
second Threat card, a second graph resolver, or a second mechanics
canonicalization path.

### 3.5 Plan integration

Relevant files:

```text
apps/live-control-ui/src/planSurface/projection/PlanProjectionCatalogRegistration.tsx
apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx
apps/live-control-ui/src/planSurface/reference/referenceResolver.ts
apps/live-control-ui/src/planSurface/selectedObject/SelectedObjectCard.tsx
apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx
apps/live-control-ui/src/planSurface/reference/projectionRequestCache.ts
```

Plan has:

- a `statblock` tool registration;
- a neutral graph-reference projection;
- exact object/reference resolution;
- `PlanReferenceObjectCard`;
- exact Threat routing into `ThreatSheetProjection`;
- relationship navigation;
- technical details and graph-scope context;
- a cache seam in `projectionRequestCache.ts`.

The current user experience is still too close to graph metadata. A graph card
can be technically correct and still fail the GM if its default glance starts
with IDs, digests, binding IDs, or revision pins.

### 3.6 Build integration

The current Build path is not the first reboot target.

Relevant files include:

```text
apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
apps/live-control-ui/src/buildSurface/reference/BuildReferenceSearchProjection.tsx
apps/live-control-ui/src/buildSurface/reference/BuildReferenceObjectProjection.tsx
apps/live-control-ui/src/buildSurface/reference/BuildReferenceCapability.tsx
apps/live-control-ui/src/buildSurface/reference/buildBuildSurfaceInteractionPublication.ts
```

The current baseline supports Build document composition and finding/viewing
existing graph objects. The named Build graph-reference insertion work is a
separate successor and must not be smuggled into the first Plan Threat-glance
slice.

### 3.7 Hermes integration

Hermes can query published Threats through the exact hydration path:

```text
apps/live_control_server/services/hermes_graph_interaction_tools.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/hermes_graph_agent_host.py
apps/live-control-ui/src/planSurface/components/PlanAgentInteractionBar.tsx
```

Hermes successfully rediscovered the dogfood Threat, but its default answer
and wait experience remain product gaps. A dynamic Threat/statblock card and
truthful long-turn progress are follow-on slices, not prerequisites for the
first visual glance slice.

---

## 4. Real dogfood evidence

The latest report is:

```text
Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md
```

It is important to preserve the report’s distinction:

```text
Publication bridge E10: PASS
Overall MAGIC-D3 experience: PARTIAL
```

### 4.1 Mireward Latchling identity ledger

The real dogfood used:

| Artifact | Exact value |
|---|---|
| ThreatDraft | `2169f965-6098-4287-9a0b-90adfdeb1b6e` |
| Candidate | `cand_duxkq64lhy6jj32y` |
| Statblock | `sb_7727dfeeb8074214a6a9cebf257691ff` |
| Mechanics revision | `rev_60b7bf03dd8d4a75a0a164ad73ce83b1` |
| Definition digest | `sha256:4c843b9e8672c20d94e2594a70a62b0496f009481ac69af64dee071171e2d722` |
| Publication operation | `ca9fff4d-92f4-45ed-bb02-672b3b175e34` |
| Identity resolution | `c05f202f-2f94-4902-88a4-902bc9f91066` |
| Proposal | `5461a95b-11eb-40b2-b2b7-ecbdead35b2d` |
| Commit | `523e293c-02c8-41db-97bc-58db9e00891b` |
| Identity decision | `create_new` |
| Threat node | `threat:authored:d16d43d376833e38caf46dd19b1dd17f` |
| Binding | `threat-statblock-binding:07ab38b331085b426bb69474` |
| Graph revision | `rev:3413bf6f5044cf2680233f5e37c90dcf` |

Observed:

- the Workbench publication journey completed through the normal floating
  dock;
- Plan rediscovered the Threat after graph load;
- Hermes found and hydrated the exact mechanics;
- browser reload/recovery retained the exact publication chain;
- no duplicate Confirm POST was observed in the component-backed recovery
  proof;
- the durable commit was `committed_unverified`, not absent.

The recorded verification mismatch was:

```text
rebuild_unavailable
projection_threat_source_domains_mismatch
projection_external_resource_source_domain_mismatch
```

The report states that the graph store materialized the write and advanced the
head. The mismatch is audit/verification debt, not evidence that the Threat was
not published. Do not turn this into a presentation blocker for the first UX
slice unless current code proves that the mismatch leaks unsafe mechanics or
wrong identity to the user.

The publication handoff records the following cycle-seven verification results:

- Frontend publication/Workbench suite: 228 passed.
- Backend publication service suite: 200 passed.
- Publication route suite: 26 passed.
- Typecheck/build retained two pre-existing `graphScope` diagnostics in
  `BuildReferenceCapability.tsx`; this is a baseline waiver, not a reboot
  target.

### 4.2 Product friction observed by the operator

The real problems were:

1. **Hover/glance was useless metadata.** It did not answer “what is this
   Threat and how will it play?” in campaign language.
2. **Plan felt cold and slow after navigation.** Leaving Plan and returning
   appeared to restart expensive graph loading.
3. **Hermes was silent for too long.** It eventually worked, but the operator
   could not tell whether the agent was working, stalled, or lost.
4. **Verification chrome was too prominent.** Honest “verification needs
   attention” language can read as publication failure when the user mostly
   needs to know that the object is on the World Graph.
5. **The dedicated editor remains narrow.** Important typed mechanics are
   protected rather than directly editable.
6. **Revise-with-AI remains recovery-oriented rather than GM-oriented.**

These are the evidence-backed UX/UI reboot inputs. They are not reasons to
rewrite the publication ledger.

---

## 5. Reboot mission

### 5.1 Mission

Make one accepted, published Threat feel like a useful authored world object
when encountered from Plan:

```text
Find/open exact Threat
→ immediately understand campaign identity and tactical feel
→ see a small amount of trusted core mechanics
→ open deeper exact mechanics when desired
→ navigate relationships without losing exact scope
→ inspect technical proof only when needed
```

The product should lead with a GM-facing answer and retain technical proof
behind an intentional inspection path.

### 5.2 UX/UI invariant

```text
The default projection communicates campaign usefulness first, while every
mechanical value remains traceable to the exact ThreatStatblockBinding and
immutable revision that produced it.
```

A successful visual redesign must satisfy both halves. A pretty card that
shows latest or copied mechanics is a failure. A perfectly exact card that
starts with internal IDs is also a product failure.

### 5.3 Product boundary

This reboot owns:

- Statblock Workbench presentation and interaction quality;
- Plan’s first authored Threat object experience;
- exact Threat glance/full projection composition;
- truthful loading, unavailable, stale, and integrity states;
- measured navigation/loading friction;
- later Hermes presentation only through an explicitly scoped successor.

It does not own:

- a new publication protocol;
- a new graph identity resolver;
- a generic authored-object framework;
- automatic placement;
- combat activation;
- arbitrary latest-revision selection;
- a second mechanics schema.

---

## 6. Recommended first slice: Plan campaign-facing Threat glance

Start here unless new evidence falsifies the scope.

### 6.1 Existing seams to reuse

Use the existing:

```text
PlanReferenceObjectCard
ThreatSheetProjection
threatSheetViewModel
buildThreatQueryHydrationRequest
selectExactThreatHit
buildThreatSheetViewModel
sortThreatSheetBindings
projectionRequestCache
PlanProjectionCatalogRegistration
```

Do not build a parallel `ThreatCard`, `ThreatResolver`, or direct graph-fetch
path. If the existing seam cannot express the needed state, first document
which contract is missing and why a narrow extension is preferable to a
second path.

### 6.2 Default content hierarchy

The compact/glance view should aim for:

1. Threat name.
2. Kind and role, when trusted.
3. One concise campaign-facing description or “threat feel” line when an
   authoritative field exists.
4. AC, HP, CR, and speed only when one exact trusted binding hydrates.
5. A concise binding/status cue when useful.
6. A clear path to full Threat details and exact mechanics.
7. Technical IDs, digests, graph revision, evidence, source domains, and
   verification codes behind a details/inspect affordance.

Do not invent tactical prose by concatenating arbitrary mechanics fields in the
UI. If the graph has no authoritative threat-feel field yet, use an honest
description excerpt or explicitly mark the field as unavailable. Adding a new
canonical authored field is a design decision, not a styling shortcut.

### 6.3 State behavior

The card must remain useful and honest for:

- loading;
- exact Threat found with no binding;
- exact Threat with one available binding;
- exact Threat with multiple bindings;
- binding unavailable;
- exact revision missing;
- integrity/digest mismatch;
- graph scope changed;
- stale async response after selection/navigation;
- no result;
- relationship navigation.

The default state should not expose a technical error code as the primary
headline when the Threat identity is still trustworthy. Conversely, it must
not show mechanics as trusted when the exact revision is unavailable or
integrity-failed.

### 6.4 Visual direction

Reuse existing visual language rather than inventing a new design system:

- LandingPage Statblock Generator visual grammar:
  `LandingPage/src/styles/StatblockComponents.css`
  and `LandingPage/src/styles/canvas/canvas-dnd-theme.css`;
- Buddy’s DnD-page/Markdown treatment:
  `apps/live-control-ui/src/tiptap/tiptapSpike.css`;
- existing projection styles in
  `apps/live-control-ui/src/styles.css`.

The visual goal is a compact parchment/PHB-like GM card, not a dashboard of
ledger metadata. Technical details can remain dense inside an inspection
disclosure.

### 6.5 First-slice acceptance bar

The slice is ready for dogfood only when:

- Plan can open the exact authored Threat through the existing graph-reference
  path;
- the first glance is understandable without reading an ID;
- core mechanics appear only from the exact trusted revision;
- unavailable/integrity states do not render untrusted mechanics;
- multiple bindings do not silently choose the first;
- relationship navigation retains exact graph scope;
- reload/reselection does not show an older selection’s card;
- technical details remain inspectable;
- the visual card is useful in a real prep task, not just a fixture;
- the test proves no new graph write or publication mutation occurred.

---

## 7. Suggested implementation map

Start with a read-only reconnaissance and a short plan before editing.

Likely UI files:

```text
apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.tsx
apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.ts
apps/live-control-ui/src/statblocks/projection/ThreatSheetProjection.test.tsx
apps/live-control-ui/src/statblocks/projection/threatSheetViewModel.test.ts
apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.tsx
apps/live-control-ui/src/planSurface/reference/PlanReferenceObjectCard.test.tsx
apps/live-control-ui/src/planSurface/projection/PlanProjectionCatalogRegistration.tsx
apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx
apps/live-control-ui/src/planSurface/reference/projectionRequestCache.ts
apps/live-control-ui/src/styles.css
```

Before widening this list, identify the owning seam and write down why it is
needed. Do not touch publication backend files for a presentation-only slice.

Potential pure view-model work:

- separate campaign-facing identity summary from technical binding details;
- make compact/full/glance policies explicit;
- define trusted-core-stat availability;
- keep exact binding ordering deterministic;
- preserve explicit unavailable/integrity states;
- avoid deriving default copy from internal identifiers.

Potential component work:

- make `PlanReferenceObjectCard` the entry card and
  `ThreatSheetProjection` the exact mechanics/projection body;
- add a small status/details hierarchy;
- make the default display read like a GM prep card;
- retain existing relationship and technical disclosure behavior.

Potential CSS work:

- scope styles to the Threat/Statblock projection root;
- reuse existing design tokens;
- keep dense technical details visually secondary;
- do not encode business authority in CSS state.

---

## 8. Verification and dogfood

### 8.1 Baseline tests

Run the focused projection/Plan suite before and after changes:

```bash
cd apps/live-control-ui
npm test -- --run \
  src/statblocks/projection/ThreatSheetProjection.test.tsx \
  src/statblocks/projection/threatSheetViewModel.test.ts \
  src/planSurface/reference/PlanReferenceObjectCard.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/planSurface/projection/projectionCatalogRegistrations.test.tsx \
  src/planSurface/reference/projectionRequestCache.test.ts
```

If the slice changes only frontend presentation, owning backend publication
tests are regression evidence rather than the primary new gate:

```bash
uv run pytest \
  tests/test_threat_publication_identity.py \
  tests/test_threat_publication_operations.py \
  tests/test_threat_publication_proposals.py \
  tests/test_threat_publication_commits.py -q
```

Do not “fix” the known baseline TypeScript diagnostics in
`BuildReferenceCapability.tsx` as part of this slice unless a separate task
explicitly adopts that work.

### 8.2 Real dogfood

Use a real accepted/published Threat, preferably the Latchling identity ledger
in §4, or a newly created exact test object if the operator wants a clean
campaign run.

Record:

- current repository SHA;
- world/campaign and graph revision;
- exact Threat node and binding;
- exact statblock/revision/digest;
- surface and navigation path;
- cold and warm load observations;
- what appears before/after hydration;
- whether the default glance is useful without technical details;
- whether leaving and returning Plan repeats graph loading;
- any stale or unavailable behavior;
- screenshots or local evidence where available;
- whether any additional graph/publication mutation occurred.

The dogfood verdict must distinguish:

```text
projection correctness
presentation usefulness
latency/liveness
publication correctness
overall GM experience
```

Do not call a direct API or backend probe a successful product experience.

### 8.3 Falsifiers

Stop and route to the owning boundary if:

- the exact Threat cannot be opened without copied IDs or scripts;
- the card renders latest/current-head mechanics instead of the exact binding;
- a missing or mismatched revision renders as trusted;
- a multiple-binding case silently chooses one;
- stale selection data appears after navigation;
- the UX change requires a new graph write to make the read card appear;
- the operator still needs to read ledger metadata to understand the Threat;
- the latency claim is asserted without measuring cold/warm behavior;
- the change needs publication recovery or identity semantics changed.

---

## 9. Follow-on slices, in order of product evidence

These are candidates, not automatic scope for the first slice.

### 9.1 Plan navigation and projection latency

Measure and then improve:

- cold graph projection load;
- warm cache load;
- leave/return behavior;
- exact selection changes;
- relationship navigation;
- stale request cancellation/ignore behavior.

Reuse `projectionRequestCache.ts` and existing graph projection seams. Do not
hide slow work behind a spinner that provides no liveness signal.

### 9.2 Hermes live progress and Threat card output

The current Hermes host can find the Threat, but long turns feel silent.

A later slice should provide truthful:

- “Hermes is working” state;
- elapsed time;
- preserved question/thread context;
- stale/failure recovery;
- no fake provider/tool stages;
- optional structured Threat/statblock artifact/card output.

The first Hermes slice should reuse the exact Threat projection and provenance
rather than paste raw graph IDs into the transcript.

### 9.3 Workbench authoring polish

Separate from the Plan glance:

- improve the narrow editor’s direct field coverage;
- simplify revise-with-AI into a GM-facing “revise working copy” flow;
- hide recovery choreography behind advanced controls;
- expose a truthful saved/published distinction;
- compare accepted revisions without implicit rebinding.

Keep the accepted revision and publication contracts unchanged while improving
the interaction model.

### 9.4 Graph-reference insertion and placement

Opening an exact Threat is not the same as placing it in a document or scene.

Later work should explicitly distinguish:

```text
open/read exact object
insert a reference/embed
create a contextual placement
activate a runtime instance
```

Build graph-reference insertion, SBW12 exact embeds, AOW03 placement, and AOW04
shared capability routing are separate handoffs. Do not combine them with the
first visual glance.

### 9.5 Revision adoption and combat

SBW13/SBW14 and COMBAT01/SBW15 remain later:

- append immutable child revisions;
- compare revisions;
- explicitly adopt a newer revision for one binding;
- create exact `CombatantSeed`/placement lineage;
- keep mutable HP/conditions outside graph and mechanics authority.

No “use latest” convenience should be added to make the first UX slice look
complete.

---

## 10. Explicitly out of scope for the reboot’s first slice

- Rewriting or generalizing the publication ledger.
- Changing identity candidate policy or commit admission semantics.
- Adding a “list active publication” server endpoint.
- Replacing exact query/hydration authority.
- Copying full statblock JSON into graph nodes.
- Treating Markdown as canonical mechanics.
- Automatic latest-revision fallback.
- Automatic binding adoption.
- Durable object placement (`AOW03`).
- Shared placement/action routing (`AOW04`).
- Exact Plan Markdown/Tiptap embed (`SBW12`).
- Child revision/compare/adopt (`SBW13`/`SBW14`).
- Combat integration (`COMBAT01`/`SBW15`).
- Image generation or selection (`SBW16–18`).
- Generic non-Threat object publication.
- A universal authored-object framework.
- Build graph-reference insertion unless a separate Build handoff is adopted.
- Hermes dynamic artifact/card and telemetry unless a separate Hermes slice is
  scoped.
- Fixing unrelated baseline TypeScript errors.
- Cleaning or committing live session JSON artifacts.

---

## 11. Working rules for the next steward

1. Start from current `main` and record its SHA.
2. Read this handoff, the lifecycle decision, the domain design, and the latest
   MAGIC-D3 report before choosing a slice.
3. Make the smallest independently useful UX/UI change.
4. Preserve exact identity, revision, binding, and graph scope.
5. Keep campaign-facing copy primary and technical proof inspectable.
6. Use existing projection/registry seams; do not create parallel object cards
   or resolver paths.
7. Keep read projection separate from graph writes and placement mutation.
8. Test loading, stale, unavailable, integrity, multiple-binding, and reload
   states—not only the happy card.
9. Dogfood with the real product path and report both correctness and feel.
10. Commit and push verified implementation work, excluding live-session noise
    and secrets.

---

## 12. Fresh-agent first move

The next agent should do this, in order:

```text
1. Re-anchor on current origin/main.
2. Read this handoff and the three canonical sources named in §1.
3. Inspect the existing PlanReferenceObjectCard + ThreatSheetProjection path.
4. Run the focused projection/Plan baseline tests.
5. Write a short implementation plan for the campaign-facing Threat glance.
6. Confirm that the plan does not change publication or placement authority.
7. Implement the smallest visual/projection slice.
8. Rerun focused tests, then dogfood one exact published Threat.
9. Record what improved and what remains false.
```

The success condition for this reboot is not “the graph write exists.” That is
already proven. The success condition is that the first authored World Graph
object becomes something a GM can recognize, trust, and use.
