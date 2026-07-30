# Magic Moment Charter — Build as a Worldbuilding Surface

**Status:** Living product story  
**Date:** 2026-07-30  
**Purpose:** Describe the Build experience we are trying to create, in user terms, before reducing it to implementation slices.  
**Change policy:** This document is expected to change as the product is dogfooded. It is a direction and experience target, not a frozen API contract.

## The product idea

Build is the place where the GM develops the world.

It is not merely a Markdown editor. It is not a thin route into Graph Review. It is not a collection of unrelated generators arranged beside a text box.

Build is a configured DungeonBuddy Surface:

```text
shared application shell
+ Build-specific world and campaign lens
+ shared Markdown canvas
+ shared graph projection
+ configured tools
+ persistent Agent Interaction
= a worldbuilding workbench
```

The GM should be able to write prose, inspect campaign memory, follow relationships, use tools, ask Hermes questions, and make deliberate changes without losing the document they are working in.

The canvas remains the center of gravity. Everything else comes to the canvas.

---

# BUILD-R0-A — The Canvas Is Home

## The user story

The GM opens Build and selects a worldbuilding document titled:

> Mireward Reach — Siege Notes

The document opens in a spacious Markdown canvas.

It looks and behaves like an intentional writing environment rather than an exposed text field. Headings have hierarchy. Lists, quotes, callouts, tables, links, and reference chips are visually distinct. The GM can move naturally between reading and editing without switching to an entirely different screen.

The visible application is composed from the same regions used by other DungeonBuddy Surfaces:

```text
Nav Bar
Tool Bar
Edit Bar
Canvas
Agent Bar
Adaptive Projection Pane
```

The regions are shared components. Build configures them for worldbuilding.

The GM writes:

> The Mireward Latchlings crawl beneath the outer wall while the Tripod Null-Calf pins the gate.

The document becomes dirty. The Edit Bar makes that state obvious. Save writes a new revision of this exact workspace document. A successful save leaves a durable receipt and clean state.

The user never has to wonder whether the text is saved, which document is open, or whether a local draft has silently replaced the durable version.

## What should feel magical

The editor feels calm and capable enough that the GM wants to write there.

The document is not displaced when a tool or graph object opens. Build remains home throughout the workflow.

The same canvas component could later appear in Plan or another authored Surface, while each loaded document retains its own identity, local draft, revision, dirty state, and recovery state.

## State boundary

The Markdown canvas session owns:

- the exact workspace-document identity;
- the loaded durable revision;
- the current editor state;
- dirty and clean status;
- local draft recovery;
- save preparation, commit, receipt, and verification;
- stale completion suppression when the document changes.

The canvas does not own:

- the active World Graph revision;
- graph mutation;
- Agent thread identity;
- statblock candidates or saved mechanics;
- tool-specific workflow state;
- extraction candidate disposition.

## Pass experience

A GM can open a Build document, author and style useful Markdown, save it, hard reload the browser, and return to the same exact durable document without losing work or relying on route-local hidden state.

---

# BUILD-R0-B — The World Comes to the Canvas

## The user story

While writing the Mireward document, the GM wants to know whether “Tripod Null-Calf” already exists in campaign memory.

The Edit Bar includes **Find existing object**.

The GM searches:

> Tripod Null-Calf

Search runs against the World Graph using the current Build lens. The result list appears without replacing the canvas.

Each result shows useful campaign information first:

- object name and type;
- short game-facing summary;
- important relationships;
- current mechanics or external resources when available;
- visibility or authority warnings when relevant.

Internal graph scores and evidence machinery remain available through inspection, but they do not dominate the card.

The GM clicks the result.

The same shared graph-object projection used elsewhere in DungeonBuddy opens in the adaptive pane. The object is not copied into Build and Build does not invent a second representation of it.

The card shows that the Tripod Null-Calf is connected to:

- Mireward Reach;
- the north-gate encounter;
- the meat-creature threat family;
- any exact statblock binding that has been published.

The GM follows the Mireward relationship. The projected focus changes to Mireward Reach while the document and cursor remain where they were.

The GM goes back to the Tripod Null-Calf and chooses:

> Insert reference

A durable typed reference is inserted at the current cursor position. The document becomes dirty. Saving persists the reference as part of the Markdown document.

The reference does not copy the graph object body into the Markdown. It stores a durable pointer that can be resolved again later.

## The lens

Build visibly states the graph lens being used:

```text
World: Eldyrwild
Campaign: Longmont C2
Audience: GM
Revision: Current head
Focus: Campaign-wide
```

The GM can deliberately change the focus:

- campaign-wide;
- a particular session or time range;
- a location;
- a selected graph object and its neighborhood;
- an exact revision pin;
- a visibility or admissibility mode when authorized.

Changing the lens changes retrieval and projection. It does not modify the document or graph.

The UI makes pinned and current-head views distinguishable. A result from an older pinned revision cannot quietly masquerade as current memory.

## Truthful resolution

A Markdown reference has an explicit resolution state:

```text
resolved graph object
resolved compatibility fallback
ambiguous
unresolved
not visible in this lens
missing from pinned revision
```

Ambiguity never silently selects the highest-ranked object.

An unresolved reference remains visible as unresolved. The product does not conceal the gap by searching arbitrary Markdown and pretending it found canonical memory.

## What should feel magical

The GM can move through the world’s objects and relationships while remaining inside the act of writing.

The graph stops feeling like a database the GM visits. It becomes an inspectable semantic layer projected into the work.

## Pass experience

From a Build document, the GM can search for an existing object, inspect it, traverse a relationship, insert the exact reference, save, reload, and open the same object again through the reference.

No graph write occurs.

---

# BUILD-R0-C — The Whole Workshop Is Available

## The user story

The GM decides the Mireward Latchling needs mechanics.

The Tool Bar is assembled from the Build Surface configuration. It contains the tools appropriate to the current user, campaign, and document, such as:

- Statblock Workbench;
- extraction;
- exact-run inspection;
- image or token generation;
- maps;
- structured tables;
- rules lookup;
- graph search;
- document utilities.

Tools are not separate destinations with unrelated layouts. Selecting **Statblock** opens the shared Statblock Workbench in the adaptive projection pane.

The Build document remains visible.

The tool can receive explicit context from the current work:

- the selected Markdown passage;
- the current document pointer and revision;
- explicitly pinned graph objects;
- the current Build graph lens;
- the active campaign;
- an optional creative instruction from the GM.

The GM selects the paragraph describing the Mireward Latchling and chooses:

> Use selection in Statblock Workbench

The Workbench receives a pointer and captured text through a typed action. It does not scrape the DOM or guess which text matters.

The GM generates, edits, validates, and accepts the mechanics. The result receives its own exact statblock identity, immutable revision, and digest.

Returning to the document does not destroy the Workbench state. Opening another projection does not lose the canvas.

If a published Threat is already bound to those mechanics, Build can inspect that binding. If no binding exists, Build may offer a governed action:

> Propose binding to Mireward Latchling

That action begins a reviewed graph-write workflow. It does not silently add the binding merely because the statblock was generated.

## Tool configuration

The Tool Bar is shared infrastructure driven by `SurfaceConfig`.

Build does not hardcode a private Statblock button, private graph browser, or private extraction panel. It enables capabilities from the shared catalog and supplies Build-specific parameters.

A simplified conceptual config might look like:

```ts
buildSurface = {
  id: "build",
  lens: buildGraphLens,
  canvas: markdownCanvas,
  editCapabilities: [
    "edit.markdown",
    "reference.insert-existing",
    "reference.style",
  ],
  tools: [
    "graph.search",
    "build.extract",
    "extract.inspect",
    "statblock.workbench",
    "rules.lookup",
  ],
  agentCapabilities: [
    "ask",
    "use-selected-text",
    "use-pinned-context",
    "propose-tool-action",
  ],
};
```

The exact configuration can change. The product rule is that tools are composed, not rebuilt per Surface.

## What should feel magical

A tool feels like another instrument at the writing desk.

The GM can generate mechanics, inspect a graph object, ask a question, and return to writing without route churn or losing state.

## Pass experience

The GM can use selected document text and explicit graph context to generate and accept a statblock while the Build document remains open and recoverable.

The saved Markdown document, saved statblock mechanics, and graph binding remain three distinct durable things.

---

# BUILD-R0-D — Hermes Works Beside Me

## The user story

The Agent Bar is always available at the bottom of the application.

The GM asks:

> How does this version of the Mireward Latchling differ from the meat creatures we have already established?

Hermes receives:

- the active campaign and Build Surface;
- the exact current document pointer;
- the current graph lens;
- explicitly pinned graph objects;
- any selected Markdown the GM chose to include;
- the ongoing thread identity.

Hermes does not automatically receive every unsaved word in the document merely because Build is open. The GM can see and control what context is attached.

Hermes answers in campaign language.

Names supported by retrieved graph context appear as inspectable chips. Clicking one opens the same shared graph-object projection. The GM may choose **Add to question**, **Pin as context**, or **Insert reference**.

Hermes can produce a copyable or insertable Markdown artifact. The artifact appears as a distinct editable block with actions such as:

- Copy Markdown;
- Insert at cursor;
- Replace selection;
- Save as new source document;
- Continue refining.

Hermes can request tool actions:

> Generate a siege-breaker statblock from this description.

The GM sees the proposed action and the exact context it will carry before launching it.

Hermes cannot directly save the document, accept mechanics, publish graph memory, or bind a statblock without crossing the relevant explicit authority boundary.

## Thread continuity

The Agent thread belongs to the app-level interaction layer, not the canvas.

Navigating from Build to Plan may preserve the same thread and pinned graph objects while changing the active Surface context.

The Build document’s editor state remains document-scoped. The Agent thread remains interaction-scoped. The graph lens remains Surface-scoped. Tool attempts remain tool-scoped.

These states cooperate without being collapsed into one large store.

## What should feel magical

The agent understands what the GM is working on without becoming an invisible co-author.

It can investigate, explain, draft, and launch configured workflows while the GM remains in control of every durable transition.

## Pass experience

The GM can ask a grounded question about the document, inspect retrieved objects, insert a useful Markdown artifact, and launch a tool action using explicit context without hidden document or graph writes.

---

# The Surface write rule

The Build Surface is responsible for composition, context, and authorization.

It does not provide one universal `write()` operation.

```text
Markdown document change
→ MarkdownCanvasSession
→ workspace-document prepare / commit / receipt

Statblock generation or acceptance
→ Statblock Workbench capability
→ statblock candidate / immutable mechanics store

Graph memory or binding change
→ governed proposal
→ preview
→ explicit GM confirmation
→ Kernel contribution
→ immutable World Graph revision

Tool runtime state
→ owning tool workflow

Agent suggestion
→ no durable write until an authorized capability is invoked
```

This rule lets Build feel powerful without making it dangerous or architecturally ambiguous.

---

# State ownership

## Document-scoped

- document identity;
- loaded revision;
- editor content;
- formatting;
- cursor and selection;
- dirty state;
- local draft and conflict recovery;
- inserted durable references.

## Surface-scoped

- active Build lens;
- selected graph focus;
- enabled capabilities;
- active edit mode;
- layout choices that are specific to Build;
- current projected object or tool request.

## App/user-scoped

- Agent thread;
- Agent Bar and Pane state;
- global navigation;
- recent tools and notifications;
- shared projection back stack;
- user layout preferences.

## Tool-scoped

- Statblock candidate and validation state;
- extraction run state;
- map or image-generation attempts;
- rules lookup state;
- retry and recovery journals.

## Graph-scoped

- durable object identity;
- assertions and relationships;
- evidence;
- visibility;
- immutable revisions;
- exact external-resource bindings.

---

# Shared Surface chrome

Plan, Build, and Play should use the same structural application regions:

```text
Nav Bar
  Where am I going?

Tool Bar
  What workflow do I want to launch?

Edit Bar
  What can I do to the current work object?

Canvas
  What am I primarily working on?

Agent Bar
  What do I want to ask, investigate, or delegate?

Projection Pane
  What object, tool, evidence, or workflow am I inspecting?
```

The regions remain recognizable across Surfaces. Their configured capabilities, lens, terminology, and state differ.

Shared does not mean identical.

Build is document and world-authoring focused. Plan is preparation focused. Play is runtime and encounter focused. Their shells should feel like the same product without forcing their work into the same state model.

---

# Product invariants

1. The canvas remains visible and authoritative while tools and graph objects are projected.
2. Build uses the shared Markdown canvas rather than creating another editor stack.
3. Graph objects are referenced by durable identity rather than copied into documents.
4. Changing a lens never changes durable state.
5. Search ambiguity never silently selects an object.
6. The shared projection host renders both tools and graph content.
7. The Tool Bar is capability-configured rather than route-hardcoded.
8. The Edit Bar acts on the current canvas or selected document content.
9. The Agent Bar preserves interaction continuity but does not own document authority.
10. Every durable write has one named owner and an explicit transition.
11. Build does not acquire Graph Review’s correction or confirmation authority merely because it can inspect graph objects.
12. A saved statblock, a published graph binding, and a Markdown reference remain distinct.
13. No tool reconstructs document authority by scraping editor state or reading private local-storage keys.
14. Failure preserves the last known durable document, graph revision, and tool receipt.
15. The experience may evolve, but hidden writes and duplicated ownership remain unacceptable.

---

# The complete Build magic moment

The GM opens a Mireward source document in Build.

They write and style Markdown in a calm shared canvas.

They search the World Graph for Mireward Latchling, change the lens to the current campaign and exact session focus, inspect the object and its relationships, and insert a durable reference into the document.

They ask Hermes to compare the creature with established meat threats. Hermes answers in campaign language with inspectable graph chips and produces an editable Markdown block.

They insert that block into the document.

They open Statblock Workbench from the configured Tool Bar, send the selected description and explicit graph pointer into the tool, generate and accept exact mechanics, then inspect—but do not silently create—the proposed binding.

They save the document.

They reload the browser.

The document, references, selected graph identities, accepted mechanics, and any confirmed binding all resolve through their own exact durable identities.

At no point did the GM have to leave Build merely to understand the world they were writing about.

At no point did Build pretend that writing Markdown, saving mechanics, and publishing campaign truth were the same action.
