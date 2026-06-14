---
document_id: dmb-design-prime-canvas-generation-engine-audit
title: Prime Canvas / GenerationEngine Audit + Editable Command Board Strategy
document_class: design
status: proposed
version: 1.0
created_at: "2026-06-13T00:00:00Z"
source_handoff: Docs/Plans/HANDOFF-prime-design-canvas-generation-engine-audit.md
related:
  - Docs/Runbooks/RUNBOOK-statblock-combat-dogfood.md
  - Docs/Plans/HANDOFF-dogfood-readiness-pr114.md
  - Docs/Plans/HANDOFF-combat-roster-tracker-pr113.md
  - Docs/Plans/HANDOFF-statblock-add-to-combat-pr112.md
  - Docs/Plans/HANDOFF-statblock-view-readonly-pr111.md
  - Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md
  - Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md
external_repos:
  - Drakosfire/Canvas
  - Drakosfire/GenerationEngine
---

# Prime Canvas / GenerationEngine audit + editable Command Board strategy

## 1. Executive recommendation

**Primary recommendation: Path E — Hybrid.**

Use the existing DungeonBuddy React live-control surface as the home for operational Command Board modules, and add an editor island only for editable prep/session documents. Keep the static Mireward harness as a dogfood fixture, regression reference, and table backup. Do not migrate the static board wholesale yet. Do not treat Canvas or GenerationEngine as direct dependencies for the editable Command Board yet.

The current live-control stack has crossed the viability threshold. It already contains the operational shape that dogfood proved: Statblock Workbench, generated Statblock View, Add to Combat, and Combat Roster. Those surfaces should stay operational modules, not be forced into a document editor. The editable prep board is a neighboring authoring problem with different constraints: markdown fidelity, custom embeds, safe writes, media policy, and corpus promotion discipline.

**Fallback recommendation: React live-control + session-scoped markdown scratch editor.**

If OSS block editors cannot round-trip campaign markdown safely enough, the first editor slice should save only session-scoped scratch/prep notes and render corpus-linked embeds as read-only. Canon corpus writes should remain preview/confirm only until markdown fidelity, path allowlists, and writer integration are proven.

**Canvas verdict:** keep as an extractable concept/source package, not as the editable Command Board foundation. Canvas is real code, not a name shell. It provides a React/TypeScript layout and pagination package, component registry, measurement-driven layout, HTML export utilities, tests, and a Konva map mode. However, it is a render/layout engine, not a block editor or corpus authoring surface. It may be useful later for printable statblock/page layout, map-canvas widgets, or embedded page previews.

**GenerationEngine verdict:** keep as a possible future producer abstraction, but do not depend on it from DungeonBuddy until license and contract issues are fixed. It is a real Python package for image/text generation, structured outputs, retries, metrics, and provider orchestration. It is relevant to generation services, not to Command Board composition. Its README currently says `[Add license here]`, and no `LICENSE` file was found during this audit, so it is not ready for reuse as a direct dependency.

**Next approved implementation slice:** add an editable session-scoped Prep Notes module inside live-control. No corpus writes. No editor-to-corpus path. Optional simple markdown editor or explicitly approved OSS editor spike. Save into live session state, render corpus/statblock embeds read-only, and compare usability against the Mireward static board.

## 2. Evidence base and scope

This audit executed the handoff in `Docs/Plans/HANDOFF-prime-design-canvas-generation-engine-audit.md` as a research/design slice. No product code was intentionally changed. The only intended repo mutation is this design note.

Evidence inspected:

| Area | Files / sources inspected | Finding |
| --- | --- | --- |
| Handoff scope | `Docs/Plans/HANDOFF-prime-design-canvas-generation-engine-audit.md` | Requested design note at `Docs/Design/DESIGN-prime-canvas-generation-engine-audit.md`; explicitly not an implementation PR. |
| Current statblock lifecycle | `Docs/Design/DESIGN-statblock-lifecycle-agentic-workbench.md` | Establishes draft-to-corpus-to-retrieval-to-combat lifecycle and producer API boundary. |
| Current combat/statblock design | `Docs/Design/DESIGN-command-board-combat-statblock-generator-integration.md` | Establishes rows-first operational Command Board and preview-safe write principle. |
| Live-control server | `apps/live_control_server/routes/live.py` | Confirms endpoints for generated statblock view, combat roster mutations, Workbench commands, draft storage, corpus preview/prepare/commit, retrieval activation/verify. |
| Live-control UI | `apps/live-control-ui/src/surface/moduleRegistry.tsx` and modules under `apps/live-control-ui/src/surface/modules/` | Confirms React module registry includes `statblock_workbench`, `statblock_view`, and `combat_roster`. |
| Live-control dependencies | `apps/live-control-ui/package.json` | React 19 + Vite 6 + TypeScript 5.8; no editor dependencies currently. |
| Canvas repo | `Drakosfire/Canvas` README, package, source, tests, license | Real React/TypeScript layout/render package; MIT; extraction-in-progress; not an editor. |
| GenerationEngine repo | `Drakosfire/GenerationEngine` README, pyproject, source, tests | Real Python generation package; license gap; producer abstraction only. |
| OSS editor candidates | Official GitHub/docs sources checked on 2026-06-13 | BlockNote, TipTap, Milkdown, Plate, MDXEditor, Outline, HedgeDoc compared for license, React fit, markdown and integration risk. |

Limitations:

- I did not run local builds or tests for any repository in this pass.
- I inspected source files and docs through repository access and public project pages.
- Recent commit/branch history was not exhaustively audited beyond the evidence needed for architectural recommendation.
- Line-by-line dependency vulnerability review was out of scope.

## 3. DungeonBuddy current architecture findings

### 3.1 The live-control surface is now product-relevant

The previous Command Board strategy could treat React live-control as a speculative future direction. That is no longer accurate. Main now has a concrete module registry with imported modules for Chat, Record, Roll Stack, Now, Timeline, Ingestion, Sources, Statblock Workbench, Statblock View, and Combat Roster.

Evidence:

```text
apps/live-control-ui/src/surface/moduleRegistry.tsx
  imports:
    CombatRosterModule
    StatblockWorkbenchModule
    StatblockViewModule
  switch cases:
    "statblock_workbench" -> <StatblockWorkbenchModule />
    "statblock_view" -> <StatblockViewModule />
    "combat_roster" -> <CombatRosterModule />
```

This means any editable Command Board strategy that ignores React live-control would split product energy away from the surface that now owns the operational statblock/combat loop.

### 3.2 The backend already owns the critical lifecycle seams

`apps/live_control_server/routes/live.py` exposes the route families needed for the statblock lifecycle:

```text
GET  /api/live/statblocks/view/generated
GET  /api/live/statblocks/view/generated/{artifact_id}
GET  /api/live/combat/current
PATCH /api/live/combat/current/entities/{entity_id}
POST /api/live/combat/current/entities/{entity_id}/hp-delta
POST /api/live/combat/current/sort-initiative
POST /api/live/combat/current/active-turn
POST /api/live/combat/current/turn
POST /api/live/statblocks/view/generated/{artifact_id}/combat/add
POST /api/live/statblocks/workbench/command
POST /api/live/statblocks/workbench/drafts
GET  /api/live/statblocks/workbench/drafts
GET  /api/live/statblocks/workbench/drafts/{artifact_id}
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-preview
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/prepare
POST /api/live/statblocks/workbench/drafts/{artifact_id}/corpus-write/commit
POST /api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/activate
POST /api/live/statblocks/workbench/drafts/{artifact_id}/retrieval/verify
```

The important architecture fact is not merely that endpoints exist. It is that the server already separates draft storage, corpus preview/write, retrieval activation, and combat mutation. The editor strategy must preserve this separation rather than introduce a document surface that silently writes through it.

### 3.3 The current UI modules are operational, not authoring surfaces

`StatblockWorkbenchModule` exposes lifecycle status, combat defaults, stored draft list, corpus preview/prepare/commit, retrieval activation/verification, and diagnostics. Its own pending labels still use “mock generate/render” language, which should be verified separately before relying on it as fully live producer proof.

`StatblockViewModule` lists generated statblocks, displays combat-relevant summaries, exposes retrieval labels, and adds generated statblocks to combat. It is explicitly a read/drilldown/action surface.

`CombatRosterModule` exposes turn order, HP, temp HP, initiative, team, active actor, and mutation controls. It is rows-first, matching the static dogfood lesson.

None of these modules should become blocks inside a document editor. They should become embeddable/readable from a prep editor later, but continue to own their operational behaviors.

### 3.4 The frontend stack favors React editor islands, but with version caution

`apps/live-control-ui/package.json` currently uses:

```json
{
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "vite": "^6.3.5",
    "typescript": "^5.8.3",
    "vitest": "^3.1.2"
  }
}
```

Most editor candidates support React, but React 19 compatibility must be smoke-tested before adoption. This is another reason not to add editor dependencies during the audit.

## 4. Canvas repo audit

Repository: `Drakosfire/Canvas`

### 4.1 Current apparent purpose

Canvas is a React/TypeScript package named `dungeonmind-canvas` with package version `0.2.1`. Its README describes it as “a flexible, template-driven rendering engine for multi-column, multi-page layouts.” It claims support for:

- template-based component placement;
- automatic multi-column pagination with overflow handling;
- measurement-based layout calculation;
- component registry extensibility;
- data source abstraction.

The README also says the package is under active extraction from the DungeonMind LandingPage repository.

### 4.2 Actual code found

Canvas contains real source code under `src/`, not just README scaffolding.

Inspected files include:

```text
README.md
EXTRACTION_PLAN.md
package.json
tsconfig.json
jest.config.js
LICENSE
src/index.ts
src/types/canvas.types.ts
src/hooks/useCanvasLayout.ts
src/layout/paginate.ts
src/layout/__tests__/paginate.test.ts
src/map/index.ts
```

Key assets:

1. **Package boundary**

`package.json` declares a public package with build/test/lint/type-check scripts, `dist/index.js`, `dist/index.d.ts`, peer deps for React/React DOM/Konva/react-konva, and MIT license metadata.

2. **Core exports**

`src/index.ts` exports registry helpers, `buildPageDocument`, HTML export utilities, `CanvasPage`, `useCanvasLayout`, measurement components, layout utilities, pagination diagnostics, adapters, and map mode exports.

3. **Generic-ish canvas types**

`src/types/canvas.types.ts` defines `PageMode`, `PageDimensions`, `PageVariables`, `ComponentDataReference`, `ComponentDataSource`, `ComponentInstance`, `TemplateConfig`, `PageDocument`, and `ComponentRegistryEntry`. It explicitly says domain-specific types should be supplied by consuming apps.

4. **Measurement-driven layout hook**

`src/hooks/useCanvasLayout.ts` coordinates component instances, template config, data sources, component registry, adapters, page variables, measurement entries, and layout plans.

5. **Pagination implementation**

`src/layout/paginate.ts` contains concrete pagination/overflow logic, loop guards, region iteration limits, page limits, debug flags, and measurement integration.

6. **Tests exist**

`jest.config.js` is configured for `ts-jest`, `jsdom`, and `jest-canvas-mock`; `src/layout/__tests__/paginate.test.ts` includes tests for fitting components, routing overflow, and pagination behavior.

7. **Map mode exists**

`src/map/index.ts` exports a Konva-based map canvas layer with pannable/zoomable viewport, square/hex grid overlays, draggable labels, export compositing, mask drawing, and mask preview. This is not directly part of the editable prep board question, but it is a meaningful reusable capability for future map tooling.

8. **License exists**

`LICENSE` is MIT.

### 4.3 Missing or weak areas

1. **Not an editor**

No evidence was found that Canvas provides ProseMirror/TipTap/BlockNote-style rich editing, markdown editing, collaborative cursors, schema-aware document editing, or corpus writer integration. It is a layout/render/pagination engine.

2. **Extraction appears incomplete or stale**

`EXTRACTION_PLAN.md` marks Phase 2 core extraction, Phase 3 genericization, Phase 4 testing/validation, Phase 5 docs, Phase 6 integration, and Phase 7 publication as unchecked. Some source exists beyond the checklist, so the plan is stale relative to code, but the document still signals incomplete package maturity.

3. **React version mismatch risk**

Canvas peer deps require React >=18 and `react-konva` `^18.2.14`; live-control uses React 19. This may work, but it must be tested. The map mode makes the dependency surface heavier than a simple layout utility.

4. **Debug/noise risk**

`paginate.ts` contains browser console logging on module load and debug configuration logs. This is fine for an active extraction package, but not yet ideal as a polished dependency in a live GM surface.

5. **No corpus safety semantics**

Canvas knows about page documents, component data sources, and template slots. It does not know about DungeonBuddy corpus allowlists, preview tokens, dry-run writer prepare, confirmed corpus writes, retrieval activation, or session-vs-canon lifecycle.

### 4.4 Reuse verdict

**Recommended reuse mode: conceptual pattern + selective extraction later.**

Do not use Canvas as a direct dependency for the editable Command Board yet. It is not solving the authoring surface problem. It may be reused later for:

- printable/paginated statblock or prep-page rendering;
- statblock card layout previews;
- page export flows;
- map-canvas overlays, labels, masks, and export compositing;
- component registry patterns for visual embeds.

### 4.5 Upkeep recommendation

**Keep, but do not make it an active dependency of DungeonBuddy until a consumer proves the need.**

Canvas is worth upkeeping if the operator still wants reusable layout/map primitives across DungeonMind projects. It should not be archived. But it should also not distract the editable Command Board work. If upkeep continues, the next Canvas-specific work should be package hygiene: finish or retire `EXTRACTION_PLAN.md`, verify React 19 compatibility, run tests, remove noisy debug logs, and publish a clear usage example independent of LandingPage.

## 5. GenerationEngine repo audit

Repository: `Drakosfire/GenerationEngine`

### 5.1 Current apparent purpose

GenerationEngine is a Python package named `generationengine`, version `0.1.0`, described as “Unified generation infrastructure for DungeonMind generators.” The README says it provides:

- image generation via Fal.ai and OpenAI/DALL-E style services;
- text generation through OpenAI Responses API;
- structured outputs;
- metrics tracking;
- retry/error handling.

### 5.2 Actual code found

Inspected files include:

```text
README.md
pyproject.toml
src/generationengine/__init__.py
src/generationengine/models/requests.py
src/generationengine/services/text_service.py
src/generationengine/services/image_service.py
tests/test_text_service.py
```

Key assets:

1. **Python package boundary**

`pyproject.toml` defines a Hatchling package, Python `>=3.11`, dependencies on Pydantic, httpx, tenacity, OpenAI, and pytest, and a dev dependency group with pytest-asyncio.

2. **Top-level exports**

`src/generationengine/__init__.py` exports `ImageService`, `TextGenerationService`, request/response models, metrics, errors, retry error types, provider base classes, and schema utility helpers.

3. **Text service**

`src/generationengine/services/text_service.py` implements OpenAI Responses API calls with system prompt support, structured output schema formatting, retry wrapper integration, metrics, cost estimation, streaming, and error response modeling.

4. **Image service**

`src/generationengine/services/image_service.py` orchestrates image providers, Fal provider registration, upload service integration, retry handling, image result construction, and metrics.

5. **Request models**

`src/generationengine/models/requests.py` defines image models including `flux-2-pro`, `nano-banana-pro`, `gpt-image-1.5`, `flux-pro`, `flux-lora-i2i`, image generation request fields for image-to-image and inpainting, and text generation models/requests.

6. **Tests exist**

`tests/test_text_service.py` tests text generation success, system prompt use, parameter forwarding, rate limit handling, timeout handling, service initialization, and request validation.

### 5.3 Missing or weak areas

1. **License gap**

The README says `[Add license here]`, and `LICENSE` was not found during inspection. This blocks direct dependency use, especially for future commercial posture.

2. **Python version mismatch is probably acceptable but unverified**

Package requires Python `>=3.11`; DungeonBuddy’s handoff asks for Python 3.13 / uv compatibility. That is likely compatible, but not proven until the package is installed/tested under the DungeonBuddy runtime.

3. **Model/pricing drift risk**

`TextModel` only includes `gpt-5.1`, and `text_service.py` has a pricing table comment saying pricing is approximate/as of 2024 and estimates `gpt-5.1`. This should not be treated as production-grade cost accounting without update.

4. **Test/code mismatch risk**

`text_service.py` notes that `max_tokens` is not supported in Responses API and warns/ignores it, while the inspected test `test_text_generation_with_parameters` expects `max_tokens` to be forwarded. This is a red flag that tests may lag code or vice versa.

5. **Not a Command Board composition engine**

GenerationEngine does not provide layout, editor, corpus authoring, live session state, React modules, or write-path safety. It is a producer service abstraction.

### 5.4 Reuse verdict

**Recommended reuse mode: no direct dependency yet; consider future producer abstraction after license/test cleanup.**

GenerationEngine is relevant to DungeonBuddy only at the producer-client boundary, not the editable Command Board surface. It may become useful if DungeonBuddy wants a shared Python generation client wrapping text/image generation across tools. But the current production statblock lifecycle already talks through DungeonMindServer’s v2 producer seam; pulling GenerationEngine into DungeonBuddy now would increase coupling without solving the prep-board problem.

### 5.5 Upkeep recommendation

**Keep, but fix license before reuse.**

GenerationEngine is not an archive candidate. It has enough real code to keep as a separate infrastructure experiment. The next upkeep pass should add a license, verify tests, reconcile `max_tokens` behavior, update model/pricing assumptions, document provider requirements, and decide whether this package is meant to be imported by DungeonBuddy or only by DungeonMindServer/generator services.

## 6. Compatibility matrix

Scale: 1 = poor / incompatible, 3 = partially compatible with adaptation, 5 = directly compatible.

| Axis | Canvas | GenerationEngine | Notes |
| --- | ---: | ---: | --- |
| Python 3.13 / uv compatibility | 1 | 4 | Canvas is JS/TS only. GenerationEngine is Python `>=3.11` and uv-installable per README, but untested here. |
| FastAPI compatibility | 1 | 3 | Canvas has no backend. GenerationEngine could sit behind FastAPI but provides no API routes itself. |
| Vite/React compatibility | 3 | 1 | Canvas is React but peer deps/Konva need React 19 smoke test. GenerationEngine is backend Python only. |
| Corpus markdown compatibility | 2 | 2 | Canvas can render data-driven docs but has no markdown/corpus model. GenerationEngine can generate text but does not know corpus paths. |
| Two-phase write compatibility | 1 | 1 | Neither repo implements DungeonBuddy preview/confirm writer discipline. |
| Live session state compatibility | 2 | 2 | Canvas page documents could map to session documents later. GenerationEngine returns generation results, not live state. |
| Command Board module compatibility | 2 | 2 | Canvas can support visual/embed rendering later. GenerationEngine can support producer calls later. Neither plugs into modules today. |
| Test harness compatibility | 3 | 3 | Both have tests, but neither was run here; GenerationEngine has apparent test/code drift. |
| Deployment/local-first compatibility | 3 | 2 | Canvas is local frontend but adds deps. GenerationEngine needs API keys/provider env and possibly uploads. |
| License/commercial posture | 5 | 1 | Canvas is MIT. GenerationEngine license is missing. |

Summary table:

| Repo | Current apparent purpose | Unique assets found | Reuse verdict | Compatibility score | Migration cost | Risks | Recommended next action |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `Drakosfire/Canvas` | React layout/render/pagination engine plus map mode | Layout planner, measurement hook, component registry, HTML export, tests, Konva map utilities, MIT license | Conceptual pattern now; selective extraction later | 3/5 for visual rendering, 1/5 for editing | Medium if used for embeds; high if forced into editor | Not an editor; extraction plan stale; React 19/Konva compatibility unknown; no corpus writer safety | Keep; do not depend for editor R1; run package hygiene if future printable/map need is real |
| `Drakosfire/GenerationEngine` | Python generation service abstraction | Text/image requests, OpenAI Responses API service, structured outputs, retry/metrics, image orchestration, tests | No direct dependency yet; possible future producer abstraction | 2/5 for DungeonBuddy, 4/5 for generator services after cleanup | Medium for backend import; low if kept separate | Missing license; possible test/code drift; model/pricing drift; not Command Board UI | Keep; add license and fix tests before any reuse discussion |

## 7. OSS editor comparison

Checked on 2026-06-13.

| Candidate | License / posture | React fit | Markdown fidelity | Custom blocks / embeds | Media support | Local-first / self-host fit | Integration effort | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BlockNote | Mostly MPL-2.0; `xl-*` packages GPL-3.0/commercial | Excellent; React-first, Notion-style | Moderate; block model is not byte-exact markdown | Strong; intended for extensible block editing | Strong | Good for local app if avoiding GPL XL packages | Medium | Best Notion-like UX candidate, but license/package boundary and markdown round-trip need spike |
| TipTap | MIT | Strong; mature React integration via headless editor | Moderate; ProseMirror JSON is canonical unless carefully serialized | Very strong; custom nodes/marks are core | Strong via extensions | Good | Medium-high | Best low-level editor framework if custom behavior matters more than out-of-box UX |
| Milkdown | MIT | Moderate-good; markdown-native ProseMirror/remark approach | Stronger than most; markdown-first | Good but more framework-specific | Good | Good | Medium | Strong candidate if markdown fidelity outranks Notion-like block UX |
| Plate | MIT at repo root | Strong; React + Slate/shadcn ecosystem | Moderate; rich-text first, markdown possible with plugins | Very strong plugin/component story | Strong | Good, but heavier ecosystem | Medium-high | Good rich editor toolkit; likely too broad for R1 unless UI customization is the priority |
| MDXEditor | MIT | Strong; React component | Strong for markdown/MDX documents | Good for directives/JSX/MDX-style embeds | Good; supports images, tables, code blocks | Good | Low-medium | Best candidate for a conservative markdown-first session note editor spike |
| Outline | BSL 1.1 | App, not component | Markdown-compatible product | App-level extension, not easy embed | Strong | Self-hostable but heavy | Very high | Do not adopt; study product patterns only |
| HedgeDoc | AGPL-3.0 | App, not component | Markdown-first collaborative notes | App-level | Good | Self-hostable but copyleft/app-scale | Very high | Do not embed/adopt for DungeonBuddy; study collaboration patterns only |

Recommendation from editor survey:

1. **R1 safest:** MDXEditor or a simple textarea/preview markdown editor for session-scoped notes only.
2. **R2 if block UX matters:** BlockNote spike, but avoid GPL `xl-*` packages and prove corpus serialization before any canon write.
3. **R2/R3 if custom behavior matters:** TipTap or Milkdown. TipTap is more flexible; Milkdown is more markdown-native.
4. **Avoid app adoption:** Outline and HedgeDoc are full products, not embedded editor engines for this use case.

## 8. Command Board migration map

| Current/static concept | Current live-control equivalent | Future editable equivalent | Priority | Safe write posture |
| --- | --- | --- | ---: | --- |
| Static Mireward combat tracker | `CombatRosterModule` | Keep operational module; editor can link/embed read-only combat snapshot | High | Combat state writes only, not corpus writes |
| Static statblock drilldown | `StatblockViewModule` | Read-only statblock card embed in prep notes | High | Embed points to artifact/corpus path; no inline statblock mutation |
| Generated statblock workflow | `StatblockWorkbenchModule` | Link/embed draft artifact, launch Workbench from editor | High | Draft first; preview/prepare/commit for corpus |
| Session notes / agenda | None dedicated | Editable session-scoped Prep Notes module | High | Session state only in R1; no canon write |
| Open loops | Static board sections / markdown | Structured task/open-loop block or markdown section | Medium | Session state first; optional promotion later |
| NPC/location snippets | Corpus markdown retrieval/read panes | Corpus-linked read-only embeds; “open source file” affordance | Medium | No inline canon mutation until round-trip proven |
| Roll tables | Roll stack / artifact projection | Read-only roll table embed plus launch roll action | Medium | Use existing command/projection path |
| Images/media | Static/manual assets | Media block placeholder only | Low | No upload/storage policy until operator decides git vs object storage |
| Printable prep page | Static HTML harness | Canvas-powered print/export preview later | Low-medium | Export artifact only; no canon mutation |
| Map overlays/masks | Separate future map tooling | Canvas map mode candidate later | Low | Explicit asset storage policy required |

The migration should not be framed as “replace the static board.” It should be framed as “promote proven operational behaviors into live-control modules, then add editable prep as a sibling surface.”

## 9. Recommended architecture

### 9.1 Product surfaces

```text
DungeonBuddy live-control shell
├── Operational modules
│   ├── CombatRosterModule
│   ├── StatblockViewModule
│   ├── StatblockWorkbenchModule
│   ├── RollStackModule
│   └── Timeline / Now / Sources / Ingestion
│
├── Authoring/editor island
│   └── PrepNotesModule
│       ├── session-scoped markdown/doc state
│       ├── read-only corpus embeds
│       ├── read-only statblock cards
│       ├── roll-table embeds
│       └── explicit promote/export actions later
│
└── Static harness fixtures
    └── evals/c2_live_prep/mireward-prep/
        ├── dogfood reference
        ├── backup table surface
        └── regression fixture for interaction shape
```

### 9.2 Storage layers

```text
corpus/eldyrwild-markdown/...
  Canon-ish markdown source of truth.
  Writes require preview/confirm discipline.

<live_session_dir>/prep_notes/*.md or *.json
  Session-scoped editable notes.
  R1 target for editor saves.

<live_session_dir>/statblock_drafts/*.json
  Durable generated statblock draft artifacts.

<live_session_dir>/statblock_retrieval/generated_statblocks_manifest.json
  Retrieval activation overlay.

<live_session_dir>/combat/current_combat.json
  Current combat state.

surface_layout.json
  UI module layout/enabled state.
```

### 9.3 Embed model

For R1, embeds should be read-only render directives rather than mutable inline objects.

Possible markdown directive shape:

```md
::dmb-statblock{artifact_id="mireward-hp-sink-01" mode="compact"}
::

::dmb-corpus{path="NPCs/Lysandra Ironveil.md" heading="Tactics" mode="excerpt"}
::

::dmb-roll-table{table_id="mireward-escalation" mode="compact"}
::
```

The editor does not need to understand every directive in R1. It can preserve unknown directives as text and use a sidecar renderer for recognized embeds. This minimizes markdown corruption risk.

## 10. Write-path / corpus safety model

Canon writes must keep the same safety shape as the statblock lifecycle.

```text
Editor surface
→ session draft / non-corpus document state
→ preview + validation
→ writer dry-run / prepare
→ confirm token
→ confirmed corpus write
→ retrieval activation / verification
→ visible corpus path + reset/provenance note
```

R1 should stop at session draft:

```text
PrepNotesModule
→ save to <live_session_dir>/prep_notes/<note_id>.md or .json
→ render preview
→ show linked source/embed provenance
```

R2 can add export/promote preview:

```text
PrepNotesModule
→ choose target corpus path from allowlist
→ preview normalized markdown diff
→ prepare writer dry-run
→ receive writer confirm token
→ explicit commit
```

Do not implement:

- direct editor save to `corpus/`;
- silent mutation of NPC/location/statblock files;
- automatic canon promotion of combat notes;
- inline edits of generated statblocks before deciding draft-vs-corpus semantics;
- media uploads before storage policy exists.

## 11. Risks and falsification tests

| Risk | Why it matters | Falsification / mitigation test |
| --- | --- | --- |
| OSS editor corrupts corpus markdown | Campaign files are source-of-truth-ish and retrieval-sensitive | Run round-trip fixtures over representative corpus files; require semantic or byte-exact threshold before canon writes |
| React live-control is slower/worse than static board | The static board earned trust through table speed | Dogfood PrepNotesModule beside static Mireward board; track clicks/latency/friction |
| Editor tries to own operational state | Combat/statblock workflows need dedicated controls | Keep CombatRoster/Workbench/View as separate modules; editor embeds are read-only launch points |
| Canvas temptation causes wrong abstraction | Canvas is real but solves layout, not editing | Only use Canvas after an R2/R3 print/export/map use case is approved |
| GenerationEngine coupling bypasses DungeonMindServer producer seam | DungeonBuddy should not absorb generator internals prematurely | Keep using production producer API; only import GenerationEngine after license/test cleanup and explicit boundary decision |
| License surprise | Editor and GenerationEngine decisions may affect commercial posture | Treat GenerationEngine as blocked until license added; avoid BlockNote GPL XL packages; avoid AGPL app adoption |
| Media storage becomes accidental architecture | Images in git vs object storage affects backups, portability, and local-first story | No media upload in R1; operator decision required |
| Collaboration assumptions creep in | Real-time collab changes data model and dependencies | No collaboration in R1/R2 unless explicitly required |

Strong falsification tests:

1. If Canvas proves to contain a tested editor/layout authoring engine in paths not inspected here, reconsider Path C for a narrow extraction.
2. If MDXEditor/Milkdown/TipTap cannot preserve enough markdown fidelity, keep editable prep session-scoped only.
3. If React live-control cannot match the static board’s table speed, keep static harness primary for live sessions and add editor islands incrementally.
4. If GenerationEngine’s license cannot be clarified, do not import it anywhere in DungeonBuddy.
5. If generated statblock embeds become awkward as markdown directives, use sidecar JSON for embeds and render markdown as the human-readable projection.

## 12. Operator questions

Carry-forward questions:

1. Should canon hub files ever be inline-edited from the board, or only session-scoped docs?
2. Are images stored in git corpus, object storage, or both?
3. Is real-time collaboration a future requirement?
4. Should the editable surface replace Cursor for prep during live sessions, or complement it?
5. Is markdown round-trip required to be byte-exact or only semantically equivalent?

Additional questions sharpened by this audit:

1. Should embeds be stored as markdown directives, sidecar JSON, or both?
2. Should generated statblocks become editable before or after corpus promotion?
3. Should live combat notes ever promote to canon automatically, or only through explicit review?
4. Is the minimum useful editor a scratch note, a corpus-linked note, or a Notion-like block board?
5. Is Canvas still intended as an active cross-project package, or should it be treated as a source-code library for selective copy/extraction?
6. Is GenerationEngine intended for DungeonBuddy import, DungeonMindServer internals, or standalone generator products only?
7. What license should GenerationEngine use?

## 13. Recommended next slice

### R1: Session-scoped Prep Notes module

Goal: prove editable prep value without touching corpus writes or committing to a heavy editor dependency.

Scope:

```text
apps/live_control_server/services/prep_notes_store.py
apps/live_control_server/routes/live.py
apps/live-control-ui/src/surface/modules/PrepNotesModule.tsx
apps/live-control-ui/src/api/liveApi.ts
apps/live-control-ui/src/api/types.ts
surface module catalog / layout fixture updates if needed
Docs/Runbooks/RUNBOOK-prep-notes-dogfood.md
```

Functional requirements:

- create/read/update/list session-scoped prep notes;
- store notes under the live session directory, not corpus;
- support markdown text body;
- render markdown preview or plain preview;
- preserve unknown embed directives as text;
- provide read-only helper snippets for generated statblock embeds and corpus path embeds;
- show “session note only — no corpus write” visibly;
- add reset/runbook instructions;
- include unit tests for path safety and note persistence.

Non-goals:

- no corpus writes;
- no media uploads;
- no real-time collaboration;
- no Canvas dependency;
- no GenerationEngine dependency;
- no static harness migration;
- no statblock inline editing;
- no DB-backed document store.

Acceptance criteria:

1. GM can open a Prep Notes module in live-control.
2. GM can save and reload a session-scoped note.
3. Saved state survives server restart if live session dir persists.
4. UI clearly distinguishes session note from canon corpus.
5. Tests prove unsafe note ids/paths are rejected.
6. Runbook explains how to enable/reset the module.

### R2 candidates after R1

Pick one based on dogfood:

- **R2A: Corpus promotion preview for prep notes** — preview-only, no commit until allowlists and round-trip checks are proven.
- **R2B: Editor library spike** — compare MDXEditor vs Milkdown vs BlockNote using a small fixture set.
- **R2C: Read-only embeds** — render statblock/corpus/roll-table directives as cards while preserving markdown source.
- **R2D: Canvas print/export spike** — use Canvas only for printable prep-page export, not live editing.

## 14. Narrow next handoff

```markdown
# HANDOFF — R1 Prep Notes module for live-control

Mode: implementation slice, documentation-aware, no corpus writes.

Read first:

- `Docs/Design/DESIGN-prime-canvas-generation-engine-audit.md`
- `Docs/Plans/HANDOFF-prime-design-canvas-generation-engine-audit.md`
- `Docs/Runbooks/RUNBOOK-statblock-combat-dogfood.md`
- `apps/live_control_server/routes/live.py`
- `apps/live-control-ui/src/surface/moduleRegistry.tsx`
- `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx`
- `apps/live-control-ui/src/surface/modules/StatblockViewModule.tsx`
- `apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx`

Mission:

Add a session-scoped Prep Notes module to live-control.

Constraints:

- Do not write to `corpus/`.
- Do not add BlockNote/TipTap/Milkdown/Plate/Canvas/GenerationEngine dependencies.
- Do not migrate static Mireward pages.
- Do not implement media upload.
- Do not implement real-time collaboration.
- Do not inline-edit statblocks or corpus files.

Implementation target:

- Server note store under `<live_session_dir>/prep_notes/`.
- Safe note ids only.
- API routes for list/read/save.
- React module with edit and preview panes.
- Visible session-only warning.
- Tests for store path safety and persistence.
- Runbook for dogfood/reset.

Definition of done:

- Module appears in live-control when enabled.
- A note can be edited, saved, reloaded, and reset.
- No corpus files change.
- Tests pass.
- Runbook documents the dogfood flow.
```
