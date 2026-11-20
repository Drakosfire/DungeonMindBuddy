---
document_id: dmb-design-blank-surface-to-world-graph-canvas
title: Blank Surface to Local World to World Graph Canvas
document_class: design_plan
status: proposed
created_at: "2026-11-07"
updated_at: "2026-11-07"
evidence_base: f91c6475e9ec72bd3bd7fe6cb6cdb11c8fa8270e
---

# Blank Surface → Local World → World Graph Canvas

## Purpose and authority

Build more of Buddy, not a standalone diagram toy. This project should teach us how to construct a Surface, reveal unnecessary coupling, and exercise the editing, persistence, recovery and history already owned by the product.

The operator's sequence is explicit:

1. Turn the landing page into a basic, blank, **fully wired Surface**. Learn what a blank Surface requires; investigate configuration-driven construction, demolition and optimization.
2. Once that is implemented and understood, investigate and implement the appropriate **local World persistence and WorldKeeper packaging/restoration boundary**, evaluating Dexie rather than assuming it.
3. Finally build the **World Graph Canvas** as a real Surface over those capabilities.

This document records the requested design on `main`. It is **not an ACTIVE implementation handoff**, does not allocate a write/runtime lease, and does not authorize deployments, provider calls, migrations, cross-repository edits or merges of other work. Publishing this plan does not establish completion of any phase. Activate bounded implementation slices through current repository policy after re-anchoring and inspecting live leases. Default implementation topology is serial; each phase can contain independently useful bounded slices rather than one oversized PR.

Buddy owns this product plan. Cross-repository contract changes and sequencing must be reconciled in DungeonOverMind, with the actual semantic/persistence changes implemented by WorldKeeper and DungeonMind owners. This document proposes those interfaces; it does not override their authorities.

## Settled product direction

- The eventual front door is immediately playable, not a signup wall, marketing-only graph, or empty dashboard.
- **The World is the canvas**, not a required extra node connecting everything. Its editable title has a prominent edit symbol. “A World in the Making” is an illustrative title, not a settled name.
- The initial scene has **two People, a Location and an Event**. The People have a relationship with one another; both People and the Location have meaningful edges to the Event. Example names and relationship labels are replaceable content, not schema.
- The graph is another projection of the same World. Do not create a parallel toy ontology or authoritative diagram store.
- Changes save client-side while the visitor plays. Earlier “no state until sign-in” language is superseded: browser-local persistence and account persistence are distinct.
- Save options and persistence explanations live behind the **Save** button. Local export and later account adoption must state their actual guarantees; do not interrupt entry with a storage tutorial.
- A user can eventually edit entities and relationships, create new ones, and use shared content editing. Expose only operations whose semantics are implemented; missing domain capabilities are work to build, not reasons to fake successful changes.
- The reference image's **palette and mood are right**, but it is too busy and colors blend together. Preserve warm parchment, muted gold and dark framing; simplify ornament and improve separation/contrast. The decorative map is not required and must not imply factual geography.

### Visual reference

The operator-approved aesthetic reference is retained in ChatGPT Library:

`libfile_a963d557b4108191b0d6ff95f4a165ec`

It is a concept image, not a shipped UI or final specification. This opaque Library identifier is a retrieval reference for authorized tools, not a public image URL. Before visual implementation, materialize and inspect the actual image through the supported Library flow; if unavailable, report that limit rather than inventing a screenshot. Mobbin references appear below.

## Existing authority and evidence

Source research is pinned to Buddy `f91c6475e9ec72bd3bd7fe6cb6cdb11c8fa8270e`, DungeonMind `430c1a6db631d097dfa0a273f8933067f708bc56`, and WorldKeeper `ef9c50f2d6aa89a35e9408f83fc4d0ba47825ca2`. It was read-only source inspection, not a prototype or device benchmark. Reverify against current main before implementation.

| Concern | Existing owner / evidence | Consequence |
| --- | --- | --- |
| Shared chrome | [Surface architecture](ARCHITECTURE-surface-interaction-layer.md), [publication types](../../apps/live-control-ui/src/surfaceInteraction/types.ts) | Surfaces publish capabilities; AppChrome owns shared hosts. SurfaceShell is layout, not a second bar owner. |
| Current landing | [App.tsx](../../apps/live-control-ui/src/App.tsx): MirewardIndex, IndexSurfacePublisher, compatibility publications | Landing is still hard-coded composition. A neutral publication contract exists, but “new Surface is just config” is a hypothesis, not a proven facility. |
| Changing observations | [Surface Information contract](CONTRACT-surface-information-v1.md) | Data updates must not remount the editor or rebuild structural chrome. Empty, stale, unavailable and integrity-error states remain distinct. |
| Editing and save recovery | [MarkdownCanvasSession](../../apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx), [authoring hook](../../apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts), [draft coordinator](../../apps/live-control-ui/src/workspaceDocument/workspaceDraftCoordinator.ts) | Reuse session, exact identity, conflict handling, recovery and locks. Existing document admission names build/plan/runbook; generalization requires intent, not a false Build identity. |
| Autosave | [useBuildAutosave](../../apps/live-control-ui/src/buildSurface/useBuildAutosave.ts) | Existing debounced durable Page save is not graph publication. Preserve that distinction. |
| Create/connect | [connected-page orchestration](../../apps/live_control_server/services/connected_page_authoring.py), [native graph adapter](../../apps/live_control_server/services/connected_page_native_graph.py) | Reuse authority and recoverable operations, but add truthful canvas-originated intents. Existing flow starts with a source selection and has narrow relationship inputs. |
| World inspection | [NativeGraphInspection](../../apps/live-control-ui/src/graphLens/NativeGraphInspection.tsx), [catalog service](../../apps/live_control_server/services/native_graph_inspection.py) | Existing inspector is not a node-link editor. Current catalog serializes all admitted assertions, so visible-node limits alone do not bound backend work. |
| Auth | [hosted auth](../../apps/live_control_server/services/hosted_auth.py) | Hosted writers require authentication; local-operator mode is loopback-only, not public anonymous access. |

The native graph has entities and assertions. A relationship is an assertion referencing another entity. World/KnowledgeSpace is the container and revision boundary, not a mandatory entity. Positions and viewport are presentation state, not World facts.

At the inspected WorldKeeper revision, the semantic operation union is `CreateObject`, `UseExisting` and `CreateRelationship`. Rename/replace, retract/delete, merge and reversal of a published change are not automatically supplied by that union. A second name assertion is not inherently a rename. A renderer's Delete key is not authority to delete a fact.

The connected-page `/prepare` orchestration can create/save a Page and admit its source before graph confirmation. It is a journaled multi-step operation, not an all-or-nothing Page-plus-graph transaction. WorldKeeper's semantic prepare is separately mutation-free. Preserve partial recovery rather than assuming rollback.

## Phase 1: a blank but fully wired landing Surface

### Outcome

Replace the current landing presentation with a minimal real Surface using the existing shared composition. The canvas may be blank; its wiring must not be a mock. Preserve access to the existing product routes through the shared navigation. Do not require graph rendering, Dexie, WorldKeeper packaging or anonymous write support to finish this stage.

“Fully wired” means:

- A real route and stable Surface identity participate in the existing lifecycle and publication mechanism.
- AppChrome continues to own navigation, Edit, Tools, Agent and projection hosts. The new Surface publishes empty or disabled capabilities with truthful reasons when no work/World is selected.
- World/no-World context, selection and active work ownership are explicit. Do not allocate fake documents, campaign IDs, graph entities or synthetic Worlds merely to satisfy a type.
- A genuine local draft with explicit local identity is allowed where the chosen canvas is an authoring canvas; do not confuse that with a fabricated durable document. Preserve create/open/recovery entry points without requiring a previously saved document.
- Navigation, Back/Forward, repeated entry, unmount and late async completion have correct lease cleanup. Prior Surface tools and projections cannot leak into the blank Surface, or vice versa.
- Existing shared capabilities can be exercised where valid; merely rendering every toolbar icon is not proof of integration. No automatic model call, durable write or network-heavy graph load occurs simply because the blank page opens.
- Existing hosted authentication remains intact. Public guest persistence is a later boundary to design, not a reason to weaken current auth in Phase 1.

### Configuration hypothesis

The operator expects standing up a blank Surface to be largely configuration. Test that expectation. Inventory actual registration points, route dispatch, providers, canvas slot, context publication, capability policy and cleanup. Distinguish declarative configuration from domain-specific behavior.

Prefer a small typed descriptor/composition seam over copied route scaffolding where evidence supports it. Do not invent a universal Surface framework, schema language or configuration engine merely to make the assertion true. Existing architecture explicitly does not require one universal runtime manifest type.

Prove the resulting construction recipe through a test-only second inert descriptor/fixture or equivalent reusable contract test, not a second production feature. Record every remaining special case and why it exists. “Fairly trivial” is an outcome to measure, not an estimate this plan promises.

Reuse the lesson from the completed [Plan blank-authoring shell](../Plans/HANDOFF-PLAN-SURFACE-blank-authoring-shell.md) (PR #661): a usable blank state must not lose its recovery/creation controls because document resolution is empty or failed. That historical handoff is evidence, not a new active lease; current AppChrome ownership supersedes older wording suggesting surface-owned chrome. Phase 1 is about a neutral reusable Surface seam, not reimplementing Plan's blank draft.

### Demolition and optimization

Characterize before deleting. Map current landing markup, compatibility glue, duplicate registration, eager provider work and subscriptions. Candidates include obsolete launcher-only UI, redundant lifecycle paths and loading work not needed for a blank canvas.

For each proposed cut, record its current owner, live callers, replacement or reason none is needed, affected tests and before/after evidence. Do not remove shared hosts, recovery behavior, retained-state readers or access checks because the blank Surface does not visibly use them. Shared routing/providers are collision hotspots; recheck active leases before each change.

Measure cold-load requests and transferred bytes, bundle/chunk impact, idle CPU, memory, rerenders and background subscriptions. Report observed improvements or regressions; no unsupported performance target or “optimization” claim. Stop hidden/inactive work and prevent stale responses from reviving old World state. Avoid broad unrelated cleanup.

### Exit evidence

1. Ordinary landing route opens as the blank real Surface; other routes remain reachable and function.
2. Focused route/publication tests cover rapid switching, repeated mounting, null World/work, disabled commands, stale async responses and correct host ownership.
3. Auth and denied/missing/unavailable states remain truthful; no unintended write, inference or graph retrieval is emitted by blank entry.
4. A reusable “construct a blank Surface” recipe names the minimal config, necessary behavior and remaining coupling. Test it rather than merely documenting it.
5. Record demolition diff and baseline/comparison measurements. Verify the relevant aggregate UI/type checks and required owning tests; distinguish inherited failures from new failures.
6. Review the learning before activating Phase 2. Do not let the visual graph consume this stage's scope.

## Phase 2: local World storage and WorldKeeper packaging

### Outcome

Use the Phase 1 seam to establish a browser-local World lifecycle without introducing a second semantic authority. This phase begins with an explicit execution-boundary decision: current Python/PostgreSQL services do not become browser-executable by installing a JavaScript database.

Compare reuse of shared contracts plus a local adapter, necessary portable semantic logic, and any deliberately scoped server assistance. Preserve the operator's browser-local guest goal; server assistance cannot be silently described as browser-only. Account access, authority and data transmission remain explicit.

### Decisions to earn

- Evaluate **Dexie/IndexedDB** first for transactional storage, schema migration and observation. Compare the thinner `idb` wrapper if Buddy already supplies coordination. Dexie is a candidate, not an approved dependency or domain/history engine.
- Define local World identity, entity/assertion identity and operation identity. On account adoption, preserve IDs where supported or return an explicit mapping; do not predict DungeonMind-allocated IDs.
- Define versioned World packages: manifest/name, entities/assertions, authored documents, assets/references, layout, and a deliberate history inclusion policy. Treat import as untrusted input; validate limits, schema, references and identity collisions. Do not adopt a canvas library's JSON or a raw database dump as the World contract.
- Keep semantic state and presentation state separate. Dragging a node should not publish graph facts or create a stream of semantic revisions.
- Specify what “saved locally,” “Page saved,” “World published” and “adopted into account” mean. Display success only after the relevant operation succeeds.
- Keep the original local World until verified account-adoption receipt. Stable operation identity must make retry after a lost response safe rather than create duplicate Worlds/pages/entities.
- Decide history semantics explicitly: editor undo, layout undo, saved Page revision and reversal of a published semantic change are different operations. Do not reset a World head to implement ordinary undo.

Do not introduce CRDTs, SQLite-WASM or a sync platform merely to obtain persistence/history. Evaluate them only against an earned requirement such as concurrent offline multi-writer collaboration or local SQL workloads. They do not replace provenance, permission or semantic validation.

### Exit evidence

Save → reload retains exact World identity and relationships; export → import restores the defined package; schema upgrades and malformed imports fail safely; two tabs have defined conflict behavior; quota/private-mode/storage failures do not show false success; interrupted operations and retries do not duplicate state. Test the same intended command meaning against local and hosted adapters where supported. Record which semantics remain unavailable before Phase 3 exposes them.

Browser-origin storage is not a backup. The Save menu must explain device/browser scope, export and account options accurately. No public guest API should inherit loopback-operator authority.

## Phase 3: World Graph Canvas

### Outcome and interaction

Replace the blank canvas content with the small editable World projection, using the already-proved Surface and local lifecycle. The World title is directly editable with a prominent pencil. Seed two People, a Location and an Event with labeled relationships; do not add an artificial root entity or invent “belongs to World” edges to make the layout work.

Select a node to inspect or edit through existing shared editors; select a relationship to inspect its meaning; create and connect through real intents. Layout movement is immediate presentation work. Rename, remove, retract and undo must use actual domain capabilities, with implementation of missing semantics at their owner rather than optimistic fake success. Distinguish removing a node from this view from deleting/retracting World content.

### Renderer recommendation, not an irreversible commitment

Use **React Flow in controlled mode** as the leading implementation candidate. Borrow MIT-licensed official examples for connection gestures, editable labels, touch and floating edges. Buddy supplies projections and interprets commands; React Flow is not the World store, save owner or semantic undo authority.

Cytoscape remains a credible alternative, especially for larger analytical exploration; earlier repository research preferred it for that broader job. X6 offers substantial editor features but adds another imperative diagram model. Reactodia is an informative semantic-editor reference, with RDF-oriented concepts and LGPL obligations. Wireflow is an MIT interaction reference, not the foundation for a second persistence/history stack. Reconfirm exact package/example licenses when adopting code; React Flow Pro content is separate from the free MIT examples.

Preserve cycles and multiple assertions between the same endpoints. React Flow's convenience `addEdge()` deduplicates identical endpoints/handles, so do not use it blindly as domain logic. Preserve stable assertion identity and design parallel-edge presentation. Never impose a mind-map's single-root/tree constraints on the World.

### Cheap-client performance and accessibility

Start with a deliberate fixed four-node layout, retain user positions, and make automatic arrangement explicit if later added. No continuous force simulation or obligatory 3D. Keep node cards compact; open full content on selection rather than mounting an editor in every node.

Use focused neighborhoods and incremental expansion. Bound backend query/serialization work as well as rendered nodes. Preserve World/revision/scope/ownership pins and truthful completeness/staleness. A client-side filter after a full catalog download is not bounded retrieval.

Measure 4, 50, 200 and 500 visible entities with different edge densities as test fixtures, not promised capacities. Test drag/pan, memory, idle CPU, input responsiveness and saving with the real editor open on a weak client. Provide keyboard and touch creation/connection, focus/selection announcements, reduced motion and accessible editing outside pointer-only gestures.

## Reuse and validation map

| Responsibility | Keep / extend owner | Do not substitute |
| --- | --- | --- |
| Shared hosts and lifecycle | AppChrome / Surface Interaction | Route-local duplicate bars or false Build identity |
| Page authoring | Shared Markdown session and Content | Diagram-note textarea with independent saves |
| World identity, facts, revisions and admission | DungeonMind through governed Buddy ports | Renderer arrays as authoritative facts |
| Semantic preparation and verified publication | WorldKeeper / existing authority adapters | Canvas callback directly bypassing intent validation |
| Browser storage mechanics | Phase 2 chosen local adapter | A storage library as a new domain model |
| Positions, viewport, view membership | Presentation/workspace state | Invented semantic assertions |

End-to-end tests should include create → connect → edit → save → reload → inspect history, lost-response retries, source edits after preparation, navigation during save, two tabs and account adoption. Opening/closing graph panels must preserve editor identity, cursor and undo. No crossing line is a graph node. No stale response can write into a newly selected World.

## Learning deliverables and execution gates

After each phase, retain a short evidence-backed report in the owning implementation handoff: what reused unchanged, what had to be generalized, what was demolished, what got faster/slower, failed assumptions, remaining gaps and the next bounded slice. Update stable architecture only where its claims actually change. Do not accumulate a competing framework or duplicate current authority in a status document.

Before activation: re-anchor current main; inspect relevant PRs and leases; declare branch/base, expected paths, runtime/data resources, topology, tests and review gates. Documentation-only publication of this plan changes one new file. The inspected concurrent work includes the PROMPTS stack #2194–#2196, paused citation #2191 and active INGEST work; none is absorbed, released or reprioritized by this plan.

The first implementation handoff must be **Phase 1 only**. Phase 2 waits for the blank Surface learning; Phase 3 waits for its local lifecycle and required semantic capabilities. Avoid locking in later storage/rendering choices by adding their dependencies during Phase 1.

## Research references

- [Existing graph visualization research](RESEARCH-graph-visualization-exploration.md)
- [React Flow controlled interaction](https://reactflow.dev/learn/concepts/adding-interactivity), [free examples](https://reactflow.dev/examples), [performance](https://reactflow.dev/learn/advanced-use/performance), [accessibility](https://reactflow.dev/learn/advanced-use/accessibility), [addEdge behavior](https://reactflow.dev/api-reference/utils/add-edge)
- [MIT Vite starter](https://github.com/xyflow/vite-react-flow-template), [Cytoscape](https://js.cytoscape.org/), [X6](https://github.com/antvis/X6), [Reactodia authoring](https://reactodia.github.io/docs/examples/graph-authoring/), [Wireflow](https://github.com/vanila-io/wireflow)
- [Dexie React](https://dexie.org/docs/Tutorial/React), [transactions](https://dexie.org/docs/Dexie/Dexie.transaction%28%29), [idb](https://github.com/jakearchibald/idb), [browser storage limits](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)
- Mobbin interaction references: [Relevance AI: explicit connection type](https://mobbin.com/screens/1a0f842f-4954-4be2-8477-cc438997ee05), [n8n: compact nodes](https://mobbin.com/screens/817531c3-11e0-4638-bdc2-831ab9adb3a4), [Runway: compact add menu](https://mobbin.com/screens/7453b57a-8270-47bd-8fbd-2c69c60396da), [Railway: quiet dark canvas](https://mobbin.com/screens/d88f4604-19ef-4ac7-81bc-76181f0a2e1d). These are design references, not permission to copy proprietary code or assets.
