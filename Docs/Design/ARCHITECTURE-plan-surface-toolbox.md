Plan Surface Toolbox

Product Direction

/plan becomes the first intentional configured surface, not an alias to /surface or a random session-specific static page. It should show a clear context header such as Plan · Longmont C2 · preparing Session 24 · ingesting Session 23, with the context derived from a stable Plan session descriptor rather than whatever DUNGEONMIND_LIVE_SESSION_DIR happens to point at.

The durable abstraction is Surface, not Bar. A surface expresses a work mode such as plan, build, combat, or play; each surface config composes independent regions instead of making every region pretend to be the same generic bar.

/plan does not own tool, edit, or nav internals. It supplies a SurfaceConfig to a reusable SurfaceShell:





NavBar: global/surface navigation.



ToolBar: config-projected workflow launcher and adaptive drawer/container.



EditBar: document/editing command surface when a selected context is editable.



SurfaceCanvas: the main work object for the active surface; for /plan, this is the Tiptap/Markdown planning board.

The ToolBar consumes shared knowledge and schemas, then projects configured workflow components into right-sized work surfaces:





Ingest Recap opens a wide review surface with raw text, rendered markdown, preview/status, seed/breadcrumb/session-memory actions, and terminal fallback commands.



Statblock opens a workbench surface that reuses the existing working statblock generation flow rather than rebuilding it.



The registry stays open so a new workflow is added by config, but the plan only commits what has a real backing today; speculative surfaces are not pre-built.



The drawer/container adapts to the active workflow: narrow for simple tools, wide for review surfaces, and mobile/full-screen when needed.

Reference chips on the canvas are navigation handles into corpus detail, and resolving one is the same projection primitive as opening a tool. A chip (for example a statblock mentioned inside a related reference) resolves to a glance card, then can expand into the content surface registered for whatever kind the resolver returns — rendered by the same adaptive container, sized to the content. From that projected content surface the GM can toggle edit. So "open a tool" and "follow a reference into its content surface" share one registry and one container; they differ only in what is projected and where it was triggered from. The surface does not declare a category vocabulary of its own: it resolves the kind from the existing corpus indexes and treats the chip's refId as an opaque locator.

Architecture Shape

Core primitive: A Surface is a configured work environment composed of Nav, Tool, Edit, and Canvas regions. /plan is the first concrete surface config. For /plan, the canvas is the Tiptap/Markdown working board the GM writes on. NavBar, ToolBar, and EditBar are independent projection components composed around it. Tools are not pages; they are configured workflows projected by the ToolBar into an adaptive container that can sit beside the canvas, overlay it, or fill the screen on mobile.

Second primitive: projection is shared. One projection registry maps a kind (tool or content) to a component and a preferred container size. Two things trigger a projection into the adaptive container: the ToolBar (launch a workflow) and a reference chip on the canvas (follow a corpus reference into its content surface). Both render through the same container and size modes.

Simplification thesis (the design rule that also risk-proofs against the ladder): one vocabulary, one registry, one edit capability, one resolver, one theme — and the surface never names ontology categories, it resolves them. Concretely: the content kind comes from the existing corpus-index resolver, not a surface-owned enum; edit everywhere is the single lock-model + two-phase-writer capability; one resolver module is shared by static and React; one SurfaceConfig.theme (canvas inherits). This keeps the surface structurally incapable of forking the taxonomy registry the ladder owns.

flowchart TB
  routePlan["/plan route"] --> planSurfaceConfig["SurfaceConfig id plan"]
  futureRoutes["Future routes build combat play"] --> futureSurfaceConfigs["SurfaceConfig id build combat play"]

  planSurfaceConfig --> surfaceShell["SurfaceShell composition"]
  futureSurfaceConfigs --> surfaceShell

  subgraph composition [Independent Surface Regions]
    navBar["NavBar"]
    toolBar["ToolBar"]
    editBar["EditBar"]
    surfaceCanvas["SurfaceCanvas"]
  end

  surfaceShell --> navBar
  surfaceShell --> toolBar
  surfaceShell --> editBar
  surfaceShell --> surfaceCanvas

  subgraph contextBoundary [Context boundary not a single store]
    corpusTruth["Corpus markdown on disk source of truth"]
    derivedViews["Live derived views indexes session memory via adapter"]
    ontologyLadder["Ontology taxonomy ladder external gated dependency"]
  end

  corpusTruth --> derivedViews
  corpusTruth -. "later shadow mode only" .-> ontologyLadder

  derivedViews --> navBar
  derivedViews --> toolBar
  derivedViews --> editBar
  derivedViews --> surfaceCanvas

  navConfig["Nav config"] --> navBar
  toolConfig["Tool config"] --> toolBar
  editConfig["Edit config"] --> editBar
  canvasConfig["Canvas config"] --> surfaceCanvas

  toolBar -->|"launch workflow kind tool"| projectionRegistry["One projection registry kind to component size"]
  surfaceCanvas -->|"reference chip refId opaque locator"| referenceResolver["Shared resolver resolves kind from corpus indexes"]
  referenceResolver -->|"glance then expand kind content"| projectionRegistry
  projectionRegistry --> adaptiveContainer["Adaptive container compact wide fullscreen"]

  adaptiveContainer --> ingestWorkflow["Ingestion workflow tool"]
  adaptiveContainer --> statblockWorkflow["Statblock workflow generate tool"]
  adaptiveContainer --> contentSurface["Content surface resolved kind npc location statblock roll-table"]

  adaptiveContainer -->|"toggle edit"| editCapability["One edit capability lock model plus two phase writer"]
  editCapability --> corpusTruth
  editBar -->|"same edit capability"| editCapability

  ingestWorkflow -->|"writes recap and session memory"| corpusTruth
  ingestWorkflow --> recapIngestApi["Existing recap ingest API and terminal path"]
  statblockWorkflow --> statblockApi["Existing statblock workbench API"]
  referenceResolver --> liveIndexApi["Existing live corpus index API derived from corpus"]

Interpretation:





SurfaceConfig is the top-level product abstraction. It can express plan, build, combat, or play without copying shell layout.



SurfaceCanvas is the object of work. For /plan, it is the editable Tiptap/Markdown board.



ToolBar projects configured workflow components; it does not hardcode ingestion/statblock as page-specific branches.



EditBar edits the selected canvas/document/block; it does not launch prep workflows.



A single projection registry keyed by kind (tool | content) backs both the ToolBar and reference-chip navigation. A reference chip resolves against corpus indexes (already prototyped statically in prep.js / prepReferencePopoverShell.test.ts), shows a glance card, then expands into the content surface registered for the resolved kind.



The surface resolves kind from the corpus indexes and treats refId as an opaque locator; it does not declare its own category enum and does no alias/identity/merge logic (those belong to the ladder).



Content surfaces are projected the same way tools are, sized to the content. Editing everywhere is one capability — the spike lock model plus the two-phase corpus writer; the EditBar and the projected-surface edit toggle are two triggers of that one capability, not two stacks.



One reference resolver module is shared by the static and React surfaces (both hit /api/live/*/index); there is no parallel reimplementation.



The "shared context" is not a single store. It decomposes into: corpus markdown on disk (the one source of truth), live-derived views over it (the corpus indexes the chip resolver already reads, recomputed from disk per request; plus session memory), and the ontology/taxonomy graph as an external, gated dependency. Reads/writes converge on corpus-on-disk, not on a unified mutable blob.



The surface consumes derived views through an adapter (source artifact -> source anchor -> source unit), so a later Tiptap-backed or graph-backed source is a config/adapter change, not a surface rewrite.

Boundary with the Ontology / Taxonomy ladder

Derived semantics, controlled vocabulary, and the graph model are owned by the experiment/ontology-taxonomy-ladder workstream, not by this plan (see Docs/Experiments/EXPERIMENT-Ontology-Taxonomy-Ladder.md: "The Tiptap / Markdown backend workstream owns canonical authoring... The Ontology / Taxonomy ladder owns derived semantics"). This surface plan must:





Consume existing Markdown, session-memory JSONL, manifests, routes, and corpus indexes via an adapter; treat the graph as a future shadow-mode dependency only.



Not build a unified knowledge store here, and not collapse GM prep, rumor, candidate facts, and played truth into "one state everything reads and writes" — that conflation is explicitly forbidden by the ladder's non-negotiables and is the part that needs provenance + lifecycle, not a shared blob.



Resolve, don't declare: the surface owns no category vocabulary. Entity kind is resolved from the corpus indexes; the ladder's taxonomy registry stays the canonical owner. When it lands, the adapter maps onto it — the surface enum that would have drifted never exists.



Opaque locators, no identity work: refId is a corpus locator only. The surface performs no alias resolution, identity merge, or relationship inference (all ladder non-negotiables).



Adapter speaks the ladder vocabulary (source artifact -> source anchor -> source unit) so the Rung 9 shadow-retrieval read path is a drop-in swap, not a translation layer.

Sequencing (decided)

This Surface plan and the ontology/taxonomy ladder run in parallel at full scope; the adapter boundary above is what keeps them decoupled. Neither blocks the other:





The ladder's near-term consumable target is shadow-retrieval fixtures (Rung 9) — a real, source-grounded read path the surface can later consume through the derived-views adapter.



Until that shadow read path is promoted, the surface resolves references over corpus-on-disk and its live-derived views, and degrades gracefully: shallow resolution (glance + content surface) works today; reference-depth navigation lights up when the graph shadow path lands, via an adapter swap, not a surface rewrite.



Risk to manage while parallel: full-scope surface work must not invent a stand-in "shared state" to fake reference depth before the graph exists. Keep the adapter seam honest so the depth arrives from the ladder, not from a conflated blob.

Visual Design and Theming

Anchor on the existing Tiptap spike styling rather than inventing a new look. The spike at apps/live-control-ui/src/tiptap/tiptapSpike.css and apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx already establishes the token vocabulary and theming seam to reuse:





Token set: --fg, --fg-mute, --border, --bg-card, --bg-input, --accent, --radius, --mono, each falling back to app-level tokens (--text, --text-muted, --panel). The surface should consume these same tokens so the canvas matches the spike by default.



Descriptor-driven theme: the editor applies md-theme-${themeId} / data-md-theme from a descriptor and loads prep-markdown-themes.css. This is the existing "config selects styling" mechanism to generalize, not replace.

Design intent for the projected canvas: easy and chill, ready for creative activity. Concretely:





Not busy: chrome (nav/tool/edit) stays quiet and recessive; the canvas is the visual focus. Calm spacing, soft borders (--border), generous radius (--radius), restrained accent use (--accent for state/affordance, not decoration).



Not vacant: a clear starting block, gentle block-boundary affordances (reuse the spike's block-state pills), and an inviting empty state so a blank canvas still feels like a workspace, not a void.



Calm by default, expressive on demand: ToolBar workflows expand into their adaptive container without crowding the canvas; the canvas keeps its breathing room while a tool is open.

Retain the config heart: styling is loaded through config, not hardcoded per surface, so themes can be customized and extended later.





One theme: SurfaceConfig.theme declares the token overrides and/or themeId for the surface; the canvas and projected components inherit it. No separate per-canvas theme layer until a second surface proves the need.



The shell applies theme tokens as CSS custom properties at the surface root and passes themeId down to the canvas exactly as the spike does, so a future theme is a config change, not a component rewrite.



Workflow and content components inherit the surface tokens so projected surfaces visually belong to the surface rather than carrying their own palette.

Implementation Approach





Add a real /plan route in apps/live-control-ui/src/App.tsx, separate from /surface and the static evals/.../live-play.html dogfood page.



Introduce a SurfaceConfig type with only what /plan needs now: identity, label, context, tools, canvas, and theme. Do not pre-build nav/edit config breadth or build/combat/play knobs speculatively; generalize when a second surface arrives.



Make theme carry token overrides and/or a themeId that the shell applies as CSS custom properties at the surface root, defaulting /plan to the existing Tiptap spike token set; canvas inherits.



Introduce a reusable SurfaceShell that composes independent NavBar, ToolBar, EditBar, and SurfaceCanvas regions.



Keep NavBar, ToolBar, and EditBar reusable and surface-agnostic. /plan supplies context and config; the components remain independent.



Define one projection registry keyed by kind (tool | content) mapping to a component and a preferred container size. Both ToolBar launches and resolved reference chips resolve through it.



Add an adaptive projection container that loads the selected component from the registry. Size modes: compact (glance), wide (work surface), fullscreen/mobile.



Extract one reference resolver module shared by the static prep.js surface and the React surface (both hit /api/live/*/index). It resolves the chip's kind and returns an opaque locator; the React canvas then projects the content surface for that kind.



Implement editing as one capability: the spike lock model (isEditorLocked / block-state classification) plus the two-phase corpus writer. The EditBar and the projected-surface edit toggle both call it; default read-only, unlock to edit. Do not build a second edit path.



Mount recap ingestion as a configured ToolBar workflow using the existing IngestionModule logic and /api/live/recap-ingest operations. Keep terminal commands visible as fallback.



Mount statblock generation as a configured ToolBar workflow by reusing the existing StatblockWorkbenchModule / statblock workbench API flow.



Build content surfaces only for kinds with a real resolver/index today (npc, location, statblock, roll-table). Do not pre-build item/map/creation surfaces; the registry stays open for them.



Treat the static Mireward toolbox changes as dogfood-only or transitional. The durable product direction is /plan, not burying Plan tools inside /live-play static pages.

Delivery: branch ladder and agent PR stories

This plan's output is a sequence of agent handoffs, not a single monolithic change. Build it as a second branch ladder (sibling to experiment/ontology-taxonomy-ladder) so agents work in parallel on independently defensible rungs.

Branch model





Trunk: experiment/plan-surface-ladder, with a short tracking/anchor doc on main for planning visibility (mirror the ontology ladder's anchor pattern; do not treat the trunk as a merge-back of every rung).



Rung branches: one per PR story, agent-authored (Codex-style codex/... or surface-exp/NN-<slug>), each opening a PR against the trunk.



Loop: every rung follows the four-stage external-agent PR loop — HANDOFF write -> external PR -> judgment record -> atomic doc-sync — per .cursor/skills/external-agent-pr-loop/SKILL.md and the invariants in .cursor/rules/external-agent-pr-loop.mdc. Use scripts/review_external_pr.py {fetch | verify | post | merge}; handoffs are named HANDOFF-pr<N>-<slug>.md per AGENTS.md.

The "defensible" rubric (every PR's section 9 acceptance bar)

Each rung is judged against four properties, each paired with a section 7 verification command at the boundary that owns the contract:





Testing: unit coverage plus at least one seam/integration test at the rung's owning boundary (not loader-side only). A behavioral guarantee in the rubric must name the command that exercises it.



Security: corpus writes go only through the two-phase writer + allowlist; refId is treated as an opaque locator and validated before any path use (no traversal/injection); no secrets or player PII in artifacts; respect .env/corpus-PII rules.



Simplicity: obeys the simplification thesis — no surface-owned category enum, one registry / one edit capability / one resolver / one theme. The diff stays inside the section 4 allowlist (scope creep is a reject, not an accept-and-fix).



Composability: the rung ships as an independently importable module with a typed contract, surface-agnostic where the design says so; leaf modules (resolver, adapter, edit capability) are usable without the shell; no hidden cross-rung coupling.

Rung dependency graph (parallel where safe)

flowchart TB
  r0["R0 ladder scaffold trunk doc baseline"] --> r1["R1 SurfaceConfig SurfaceShell /plan route nav"]

  r0 --> l1["L1 shared reference resolver module"]
  r0 --> l2["L2 derived-views adapter artifact anchor unit"]
  r0 --> l3["L3 edit capability lock model plus two phase writer"]

  r1 --> r2["R2 one projection registry plus adaptive container"]
  r1 --> r8["R8 single theme canvas inherits"]

  r2 --> r6["R6 ingestion tool mount"]
  r2 --> r7["R7 statblock tool mount"]

  r2 --> r5["R5 reference projection wiring"]
  l1 --> r5
  l2 --> r5
  l3 --> r5

  r5 --> r9["R9 integration verification and dogfood"]
  r6 --> r9
  r7 --> r9
  r8 --> r9

Parallel lanes after R0: the UI spine (R1 -> R2 -> {R6, R7}, plus R8) and the leaf-module lane ({L1, L2, L3}, no shell dependency) run concurrently and converge at R5; R9 integrates. Each rung is small, independently shippable, and defensible on its own — boring before powerful, mirroring the ladder operating rule.

Guardrails





Do not make /plan depend silently on DUNGEONMIND_LIVE_SESSION_DIR as its only source of truth.



Do not duplicate statblock generation logic; adapt the existing working module/API.



Do not remove terminal paths for ingestion.



Do not broaden Live Play. Live Play should consume activated prep, not host prep workflows.



Keep NavBar, ToolBar, and EditBar independent. SurfaceShell composes them; it does not fuse them into a single page-specific control.



Keep the EditBar separate from the ToolBar: the ToolBar selects workflows; the EditBar appears for document-editing contexts.



Do not make "bar" the top-level domain object. The top-level object is SurfaceConfig; bars are regions inside the surface.



Do not hardcode colors/spacing in surface or workflow components. Consume the spike token set (--fg, --bg-card, --accent, --radius, etc.) so themes stay config-driven.



Do not let the canvas feel busy or vacant. Chrome stays recessive; the canvas keeps an inviting empty state and breathing room when a tool is open.



Do not hardcode ingestion/statblock as one-off ToolBar branches; register them in the one projection registry.



Do not build a separate projection path for reference chips. Tool launches and reference-chip expansions must resolve through the same projection registry and adaptive container.



Do not let edit-in-place bypass the lock model or the two-phase corpus writer. Projected content surfaces are read-only until unlocked, and unlocked edits commit through the existing writer.



Do not build a unified knowledge/schema store in this plan, and do not collapse prep/rumor/candidate/played truth into one shared state. Derived semantics belong to the ontology/taxonomy ladder; consume corpus-on-disk and its derived views through an adapter only.



Do not declare a surface-owned category/type enum. Resolve kind from the corpus indexes; treat refId as an opaque locator; do no alias/identity/merge/relationship inference (ladder-owned).



Keep it singular: one projection registry, one edit capability, one reference resolver module, one SurfaceConfig.theme. If you find yourself adding a second of any of these, stop.



Do not pre-build speculative surfaces (item/map/NPC-creation/location-creation) or speculative nav/edit/build/combat/play config breadth before a second surface proves the need.



Do not dispatch a rung without a handoff carrying a section 4 allowlist and section 7 verification, and do not accept a green PR without rerunning section 7 yourself (external-agent PR loop invariants).



Do not let parallel rungs share files outside their allowlists. If two rungs would edit the same file, serialize them or split the seam so each owns its surface.



Do not merge a rung that fails any leg of the defensible rubric (testing, security, simplicity, composability); tighten the contract rather than loosen the rubric.

Verification





UI tests prove /plan renders the configured Surface shell with independent NavBar, ToolBar, EditBar, and SurfaceCanvas regions.



Registry tests prove one registry keyed by kind selects ingestion/statblock (tool) and content surfaces (content) and applies the right container size mode.



A theming test proves the single SurfaceConfig.theme applies token overrides / themeId at the surface root, the canvas inherits, and /plan defaults to the spike token set.



Ingestion tests prove the Plan tool calls existing recap ingest operations.



Statblock tests prove the Plan tool uses the existing statblock generation flow.



Resolver tests prove the shared resolver derives kind from the corpus indexes (no surface-owned enum) and returns an opaque locator, and that a chip expands into the content surface for the resolved kind through the shared container.



Edit-capability tests prove the EditBar and the projected-surface edit toggle invoke the same lock-model + two-phase-writer path, read-only until unlocked.



Build passes with npm run build.



Focused backend tests remain green for recap ingest and statblock workbench endpoints.

