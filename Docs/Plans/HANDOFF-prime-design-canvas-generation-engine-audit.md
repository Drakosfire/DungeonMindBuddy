# HANDOFF — Prime Design next phase: Canvas / GenerationEngine audit + editable Command Board strategy

**Created:** 2026-06-13  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target base branch:** `main`  
**Suggested next branch:** `codex/prime-design-canvas-generation-engine-audit`  
**Mode:** Prime Design research + architecture recommendation. This is **not** an implementation PR.  
**Immediate operator context:** DungeonBuddy Command Board dogfood is going well. The statblock lifecycle through API-backed generation, corpus promotion, retrieval activation, Statblock View, Add to Combat, and Combat Roster is now far enough along to assess the next design layer.

---

## 0. Copyable pickup prompt

```markdown
You are the next-phase Prime Design agent for DungeonBuddy.

Read first:

- `Docs/Plans/HANDOFF-prime-design-canvas-generation-engine-audit.md`
- `Docs/Runbooks/RUNBOOK-statblock-combat-dogfood.md`
- `Docs/Plans/HANDOFF-dogfood-readiness-pr114.md`
- `Docs/Plans/HANDOFF-combat-roster-tracker-pr113.md`
- `Docs/Plans/HANDOFF-statblock-add-to-combat-pr112.md`
- `Docs/Plans/HANDOFF-statblock-view-readonly-pr111.md`
- `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md`
- `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md`
- the prior editable Command Board research handoff pasted into the chat that begins `HANDOFF — Composable editable Command Board (research + design spike)`.

You now have access to additional repositories:

- `Drakosfire/Canvas`
- `Drakosfire/GenerationEngine`

Mission:

Assess the older Canvas and GenerationEngine projects through this lens:

A. Are they at all worth upkeeping?
B. If yes, can/should DungeonBuddy leverage them?
C. If we leverage them, how compatible are they today with the current DungeonBuddy Command Board architecture?

Then produce a written recommendation for the next phase of DungeonBuddy Prime Design. The recommendation should integrate the Command Board dogfood learnings, the statblock lifecycle work, the existing live-control architecture, and the prior editable/composable Command Board research spike.

Do not implement product code. Do not add editor dependencies. Do not refactor live-control. This phase should produce an evidence-backed design note and a narrow next handoff only if the operator approves the recommended direction.
```

---

## 1. Current status: where DungeonBuddy is now

DungeonBuddy has crossed from design-theory into dogfoodable local alpha.

The Command Board stack now has the first complete generated-statblock lifecycle:

```text
DungeonMindServer statblock producer API ✅
DungeonBuddy v2 seam ✅
Lifecycle command facade ✅
Workbench draft generation/render ✅
Persistent non-corpus draft storage ✅
Corpus promotion preview ✅
Confirmed corpus write ✅
Retrieval activation/verification ✅
Read-only Statblock View ✅
Add generated statblock to current combat ✅
Combat Roster / Tracker ✅
Dogfood readiness/runbook PR ✅/pending merge verification
```

The operator reports that:

```text
Command Board is going well.
We are able to generate statblocks.
The API end in DungeonMind is working.
```

That means the next design layer should stop asking whether the Command Board concept is viable and start asking how to make it a stronger authoring/composition surface without breaking the things dogfood proved.

---

## 2. Current architecture summary

### 2.1 Live-control app

Key app paths:

```text
apps/live_control_server/
apps/live-control-ui/
src/live_play/
evals/c2_live_prep/live/session_22/
evals/c2_live_prep/mireward-prep/
corpus/eldyrwild-markdown/
```

The live-control server exposes `/api/live/*` endpoints for:

- session packet/layout/jobs/events;
- statblock Workbench operations;
- draft storage/list/read;
- corpus promotion preview;
- confirmed corpus write;
- retrieval activation/verification;
- generated Statblock View list/detail;
- Add to Combat;
- Combat Roster operations.

The live-control UI is a Vite/React module surface. Important modules now include:

```text
StatblockWorkbenchModule
StatblockViewModule
CombatRosterModule
```

These are optional/hidden modules in the live surface layout until enabled.

### 2.2 Current persistence model

The current dogfood flow uses a deliberate separation of state:

```text
corpus/eldyrwild-markdown/...
  Canon-ish markdown source of truth.
  Writes go through corpus writer preview/confirm discipline.

<live_session_dir>/statblock_drafts/*.json
  Durable non-corpus generated statblock draft records.

<live_session_dir>/statblock_retrieval/generated_statblocks_manifest.json
  Session-scoped retrieval activation overlay.

<live_session_dir>/combat/current_combat.json
  Live current combat state.

surface_layout.json
  UI module layout/enabled state.
```

The most important lesson: **not every useful GM state belongs in corpus markdown immediately.** The lifecycle now has explicit stages.

### 2.3 Corpus safety model

Do not weaken this.

The generated statblock path went through:

```text
Preview corpus promotion
→ prepare writer dry-run
→ writer confirm token
→ confirmed write
```

The confirmed writer uses the existing `src/agent/corpus_writer.py` two-phase write discipline. Future editor surfaces must use the same principle: no silent canon mutation, no direct dossier/statblock corruption, no casual writes to denied paths.

---

## 3. Key learning from PR107–PR114

### 3.1 What worked

1. **Small lifecycle slices worked better than giant surfaces.**  
   The statblock feature succeeded by adding one durable state transition at a time.

2. **Draft ≠ corpus ≠ retrieval ≠ combat.**  
   Keeping those layers explicit prevented unsafe shortcuts.

3. **The Command Board needs dedicated interfaces, not only chat.**  
   Workbench, Statblock View, and Combat Roster each proved that purpose-built UI matters.

4. **Corpus-backed does not mean markdown-only UI.**  
   The UI can expose structured controls while still preserving corpus provenance.

5. **Operator trust comes from visible state and reversible-ish staging.**  
   Preview panels, stored draft lists, corpus paths, retrieval evidence, and combat readbacks made the system understandable.

6. **Local alpha needs runbooks/reset tooling.**  
   PR114 exists because stale state and hidden modules create false bugs.

### 3.2 What remains fragile

1. **Workbench generation source must be verified.**  
   The operator says generation/API are working, but the next agent should verify whether the Workbench is actually using the live DungeonMindServer producer or still has mock/sample seams in some paths.

2. **Module enablement is still developer-ish.**  
   Some dogfood workflows require editing `surface_layout.json` unless a UI affordance exists.

3. **The editor/composable board question is unresolved.**  
   Current surfaces are operational modules, not a Notion/Confluence-like authoring surface.

4. **Static Mireward harness still matters.**  
   The static Command Board path earned trust. Do not blindly replace it just because React modules exist.

5. **Generated statblocks are corpus-backed but not yet woven into all surfaces.**  
   Combat row drilldown, editable row notes, and planning-mode task flows remain future work.

---

## 4. New repositories to audit

The operator has expanded access to:

```text
Drakosfire/Canvas
Drakosfire/GenerationEngine
```

Initial repository discovery confirms both are accessible and public under the operator account. Do not assume their names describe their true current implementation. A quick README check suggests both may currently look like DungeonMindBuddy-style pipeline/canon-reduction repos, with schema contracts, reducer, remote inventory tooling, and no API/UI layer documented. Verify by inspecting the actual tree and history.

### 4.1 Audit question A — Are they worth upkeeping?

For each repo, answer:

```text
Is it an actual separate project, a stale clone, a useful experiment, or an abandoned name shell?
Does it contain unique code not present in DungeonBuddy or DungeonMindServer?
Does it have tests, docs, and a coherent dependency story?
Does it solve a problem DungeonBuddy still has?
Would upkeep cost less than rebuilding the relevant idea inside DungeonBuddy/DungeonMindServer?
```

Possible outcomes:

```text
Keep as active source repo
Archive/read-only
Extract specific concepts then archive
Fold into DungeonBuddy/DungeonMindServer
Ignore for this phase
```

### 4.2 Audit question B — Can/should DungeonBuddy leverage them?

Evaluate leverage modes:

```text
Direct dependency
Code extraction/copy into DungeonBuddy
Conceptual pattern only
No leverage
```

Be conservative. Direct dependency is only attractive if:

- the repo has a clear package boundary;
- dependency setup works;
- tests pass;
- it does not drag an unrelated app stack;
- it has a license/commercial posture compatible with DungeonBuddy.

### 4.3 Audit question C — How compatible are they right now?

Score compatibility against current DungeonBuddy:

```text
Python 3.13 / uv compatibility
FastAPI compatibility
Vite/React compatibility
Corpus markdown compatibility
Two-phase write compatibility
Live session state compatibility
Command Board module compatibility
Test harness compatibility
Deployment/local-first compatibility
```

Produce a table with:

```text
Repo
Current apparent purpose
Unique assets found
Reuse verdict
Compatibility score 1–5
Migration cost
Risks
Recommended next action
```

---

## 5. Required repo audit method

For `Drakosfire/Canvas` and `Drakosfire/GenerationEngine`, inspect at minimum:

```text
README.md
pyproject.toml / package.json / lockfiles
src/
apps/
Docs/
tests/
schemas/
evals/
.cursor/
recent commits / branches if available
LICENSE if present
```

Search terms:

```text
canvas
layout
registry
component
block
editor
generation
template
render
export
pdf
statblock
markdown
corpus
FastAPI
React
Vite
ProseMirror
TipTap
BlockNote
```

Report explicitly if files are missing. A useful answer can say:

```text
Repo name suggested Canvas, but no canvas/editor/layout engine was found in code paths inspected.
```

Do not hand-wave.

---

## 6. Prior editable Command Board research spike to integrate

The prior handoff asked for a build-vs-adopt decision for a composable editable Command Board. It specifically asked the next design agent to:

- preserve dogfood-proven strengths: combat-first command board, fast drilldown, local persistence, corpus as source of truth;
- replace read-only accordion/modal markdown preview with an authoring surface the GM can edit at the table;
- respect corpus safety via two-phase writes and allowlists;
- inspect Canvas meanings in this repo/monorepo;
- survey OSS editors such as BlockNote, TipTap, Milkdown, Plate, Novel, AFFiNE, Outline, HedgeDoc, and simpler markdown editors;
- compare paths A–E: extend static board, new React prep module, reuse/extract Canvas engine, adopt OSS editor shell, or hybrid.

Carry that research forward, but update it with the new reality: the React live-control surface is no longer a speculative side branch. It now has proven modules for Workbench, Statblock View, and Combat Roster. That does **not** automatically mean React should replace the static board, but it raises the cost of pretending the React surface is irrelevant.

---

## 7. Current strategic question

We now have two adjacent but distinct design problems:

### Problem 1 — Operational Command Board

This is the at-table surface:

```text
combat roster
statblock view
workbench
rolls
open loops
session state
```

It needs speed, clarity, persistence, and low friction.

### Problem 2 — Editable / composable prep board

This is the authoring surface:

```text
editable session notes
inline corpus-backed snippets
block embeds
statblock cards
roll table embeds
media blocks
safe writes
```

It needs block editing, markdown fidelity, custom embeds, and corpus writer integration.

The next Prime Design recommendation should decide whether these are:

```text
one unified surface
or
separate sibling surfaces with shared chrome/state
or
static harness + React modules + editor island hybrid
```

---

## 8. Candidate path framing

Use these candidate paths, refined from the previous handoff.

### Path A — Extend static Mireward Command Board

```text
prep.js / static HTML harness
→ editable markdown embeds
→ save through writer API
```

Pros:

- preserves the dogfood harness that earned trust;
- minimal migration shock;
- easy to test against existing static pages.

Cons:

- likely hits ceiling for block composition, media, and complex custom embeds;
- risks accumulating bespoke JS;
- harder to share state with live-control modules.

### Path B — Continue React live-control as the Command Board home

```text
apps/live-control-ui
→ add editable prep/page module
→ integrate existing statblock/combat modules
```

Pros:

- already houses Workbench, Statblock View, Combat Roster;
- can adopt React editor ecosystems;
- module registry and backend API seams exist.

Cons:

- must not lose static board lessons;
- may require migration story for Mireward static pages;
- module enablement/layout is still rough.

### Path C — Reuse/extract Canvas repo/engine

```text
Canvas / GenerationEngine audit
→ find reusable layout/editor/generation primitives
→ extract only if coherent
```

Pros:

- could preserve existing operator investment;
- may contain layout/export/template logic;
- could avoid rebuilding if actually compatible.

Cons:

- current README signals may be stale/misleading;
- may have no UI/editor implementation;
- extraction can be more expensive than using current live-control.

### Path D — Adopt OSS block editor

```text
BlockNote / TipTap / Milkdown / Plate / Novel / etc.
→ custom blocks for statblocks, roll tables, corpus links
→ writer API save path
```

Pros:

- fastest path to Notion-like behavior;
- avoids greenfield editor mistakes;
- custom block ecosystem may fit embeds.

Cons:

- markdown round-trip fidelity is the hard part;
- custom corpus writer integration required;
- licensing and complexity vary.

### Path E — Hybrid

```text
React live-control operational modules
+ OSS editor island for editable prep/corpus pages
+ static harness preserved as dogfood fixture/reference
```

Pros:

- likely best product fit;
- uses right tool per pane;
- avoids forcing combat tracker into a document editor.

Cons:

- two or three surfaces can fragment unless navigation/state is designed deliberately.

---

## 9. Required deliverable

Create a design note, recommended path:

```text
Docs/Design/DESIGN-prime-canvas-generation-engine-audit.md
```

The design note must include:

1. **Executive recommendation**  
   One primary path and one fallback. One page max.

2. **Canvas repo audit**  
   `Drakosfire/Canvas`: purpose, actual code found, tests/docs, reuse verdict.

3. **GenerationEngine repo audit**  
   `Drakosfire/GenerationEngine`: purpose, actual code found, tests/docs, reuse verdict.

4. **Compatibility matrix**  
   Canvas / GenerationEngine vs DungeonBuddy current architecture.

5. **OSS editor comparison**  
   At least 5 candidates, with license, React fit, markdown fidelity, custom block support, media support, self-host/local-first fit, and integration effort.

6. **Command Board migration map**  
   Static Mireward pane / live-control module / future editable equivalent.

7. **Write-path diagram**  
   Editor surface → draft/session state → preview/validation → writer confirm token → corpus path.

8. **Risks and falsification tests**  
   What would prove the recommended path wrong?

9. **Operator questions**  
   Carry forward and refine:

   - Should canon hub files ever be inline-edited from the board, or only session-scoped docs?
   - Are images stored in git corpus, object storage, or both?
   - Is real-time collaboration a future requirement?
   - Should the editable surface replace Cursor for prep during live sessions, or complement it?
   - Is markdown round-trip byte-exact or semantically equivalent?

10. **Next handoff**  
   If the recommendation is accepted, write a narrow implementation handoff for the first R1/R2 slice only.

---

## 10. Current hypothesis before research

Treat this as a starting bias, not a conclusion.

```text
Likely recommendation: Hybrid.

Use live-control React for operational modules because that is now dogfood-proven.
Use an OSS editor or small editor island for editable prep/session pages.
Preserve the static Mireward board as dogfood fixture and migration reference, not the long-term authoring foundation.
Audit Canvas/GenerationEngine for extractable ideas, but do not assume they are reusable until code proves it.
```

Strong falsification tests:

```text
If Canvas contains a coherent editor/layout engine with working React integration and tests, reconsider Path C.
If no OSS editor can round-trip markdown safely enough for corpus writes, editor v1 should save session-scoped scratch only.
If React live-control cannot meet static board speed/usability in dogfood, keep static harness primary and add editor islands incrementally.
```

---

## 11. Evidence to preserve from current dogfood

Do not lose these product truths:

1. **Combat-first surfaces are valuable.**  
   The GM needs operational rows and one-click depth more than abstract document beauty.

2. **Dedicated interfaces beat chat-only controls.**  
   Statblock Workbench, Statblock View, and Combat Roster each justify their own shapes.

3. **Corpus path visibility builds trust.**  
   Every mutation should show where the artifact lives.

4. **Preview/confirm remains non-negotiable for canon writes.**  
   The editor must not casually mutate corpus files.

5. **Session-scoped state is legitimate.**  
   Not everything needs immediate corpus promotion.

6. **Reset/runbook tooling is part of product maturity.**  
   Statefulness is useful only when reset and provenance are understandable.

---

## 12. Suggested first tasks for the next agent

1. Verify current PR114 status and whether dogfood readiness landed.
2. Inspect `Drakosfire/Canvas` repository tree and recent commits.
3. Inspect `Drakosfire/GenerationEngine` repository tree and recent commits.
4. Search DungeonBuddy for all Canvas references:

```bash
rg -i "canvas|layout registry|component registry|block editor|cursor/canvas|generation engine"
```

5. Inspect the prior static board harness:

```text
evals/c2_live_prep/mireward-prep/
```

6. Inspect live-control modules:

```text
apps/live-control-ui/src/surface/modules/
apps/live_control_server/routes/live.py
```

7. Conduct OSS editor research with licenses. Use web search for current license/version status.
8. Write the design note in `Docs/Design/`.

---

## 13. Verification for this research phase

Research is complete when:

- `Docs/Design/DESIGN-prime-canvas-generation-engine-audit.md` exists.
- Both external repos were actually inspected and cited with file paths.
- OSS table includes at least 5 candidates and licenses.
- Recommendation chooses one primary path and one fallback.
- Recommendation includes falsification tests.
- Write-path diagram preserves preview/confirm safety.
- Next implementation handoff is included only if the recommendation is clear enough.

---

## 14. Do not do this yet

Do not:

- add TipTap/BlockNote/Milkdown/etc. dependencies;
- start migrating static pages;
- rewrite the Command Board shell;
- create a DB-backed corpus store;
- add real-time collaboration;
- implement media upload;
- wire editor saves to corpus;
- archive Canvas or GenerationEngine;
- merge repos.

First, produce the design recommendation with evidence.
