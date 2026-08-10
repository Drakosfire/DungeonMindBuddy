# HANDOFF — Finish DOGFOOD-POLISH semantic prep authoring

**Created:** 2026-08-09
**Status:** ACTIVE — finish the semantic-prep authoring capability originally carried by PR #529.
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-finish-dogfood-polish-semantic-prep-authoring.md`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `DOGFOOD-POLISH: finish semantic prep authoring`
**Target PR:** existing PR #529 may be rebuilt in place if practical.
**Repository:** `Drakosfire/DungeonMindBuddy`

**Base authority:** current `main` after merged PR #535.
**Required base anchor at dispatch:** `2fb059c3daf0644860eaac73bf05990c70dc2e8c` or a descendant containing PR #535 unchanged.
**Merged predecessor:** PR #535, `DOGFOOD-POLISH: unify Markdown structural analysis`.
**Archaeological donor only:** PR #529 head `62a24eb705f000e222b843995cde661d1f6d2b22`.

> **Critical dispatch rule:** this is a feature port onto the parser-backed boundary created by #535. It is **not** a rebase-and-resolve exercise.
>
> PR #529's Decision/Consequence nodes, UX, serializer behavior, styling, and regression cases are useful implementation donors. Its handwritten `markdownToTiptap.ts` grammar is obsolete and must not survive.
>
> If resolving the old branch would restore structural Markdown regexes, line parsers, reference-definition recognizers, indentation grammars, or any second Markdown parser beside `parseMarkdownAst` / `analyzeMarkdownBody`, stop. Rebuild the feature from current `main` instead.

---

## §0 Why this handoff exists

PR #529 was paused because repeated review failures exposed a deeper problem: semantic-prep support was being built on a handwritten Markdown recognizer whose negative-regex admission model could not reliably distinguish supported Markdown from unsupported CommonMark/GFM structures.

PR #535 was the rescue sidequest. It replaced that recognizer with:

```text
Markdown source
    ↓
mdast-util-from-markdown
    ↓
one MDAST structure
    ↓
markdownAdmission.ts
    ├─ admission decision
    └─ TipTap projection
```

That work is now merged.

PR #535 did **not** replace the product mission of #529. It deliberately left the following false:

* nested prep lists are not admitted;
* supported callouts inside list items are not admitted;
* Decision/Consequence has no current parser/admission representation;
* Decision/Consequence TipTap extensions are not mounted on `main`;
* Plan has no Decision/Consequence insertion affordance;
* Plan has no semantic Markdown paste behavior;
* production Plan styling still imports prep-theme CSS from `evals/`.

This handoff finishes that work on the correct foundation.

---

# §1 Mission and merge-ready invariant

## Mission

A GM can author Session-26-style semantic prep in Plan so that nested Decision/Consequence forks survive insertion, semantic paste, editing, Save, and reload as structured lossless Markdown.

## Merge-ready invariant

Every semantic-prep structure admitted into Plan is established by the single #535 CommonMark/GFM parser boundary and has one lossless TipTap ↔ semantic-Markdown representation; unsupported or ambiguous source never partially converts into saveable TipTap state, and #527 authoritative-source protection remains intact.

### Canonical Decision/Consequence representation

Markdown:

```md
> [!DECISION-CONSEQUENCE]
> ### Decision
> <decision body>
>
> ### Consequence
> <consequence body>
```

TipTap:

```text
decisionConsequence
├── decisionPane block+
└── consequencePane block+
```

There are always exactly two panes.

`decisionPane` is first.

`consequencePane` is second.

Malformed source is never guessed into this structure.

---

## Pre-dispatch critique

| Question                                     | Answer                                                                                                                                                                                          |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern every claimed path? | Yes. Insert, paste, edit, serialize, Save, and reload all depend on the same lossless semantic-prep representation.                                                                             |
| Most likely adversarial failure              | Paste a mostly-supported nested Decision/Consequence fork containing one unsupported construct; importer projects part of it; paste inserts partial TipTap; Save serializes a changed meaning.  |
| Will required evidence detect it?            | Yes. Paste tests must verify atomic refusal, importer tests must verify blocking diagnostics, and round-trip tests must compare the complete admitted structure.                                |
| Easiest boundary to under-test               | Nested list-item → blockquote → semantic-callout / Decision-Consequence classification inside `markdownAdmission.ts`.                                                                           |
| What forces a stop?                          | Any implementation that needs a second structural Markdown recognizer, cannot round-trip the claimed nested structure, or expands supported Markdown beyond what serializer + safety can prove. |

---

# §2 Authority, context, and boundaries

## Read in this order

1. Merged PR #535 implementation on current `main`.
2. `apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts`
3. `apps/live-control-ui/src/tiptap/markdown/parseMarkdownAst.ts`
4. `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts`
5. `apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts`
6. #527 workspace source-authority/save-gate implementation and tests.
7. PR #529 head `62a24eb...` **only as a feature/test donor**.
8. Existing Session-26 nested Decision/Consequence fixture/corpus cases.

## Predecessor contracts

### #527 — source authority

Preserve all existing behavior:

* exact leading YAML/frontmatter fidelity;
* `exported_markdown_authoritative`;
* unsupported/ambiguous source may be projected for viewing but cannot silently become durable lossy Markdown;
* Save remains fail-closed;
* explicit reimport is the transition back to editor authority.

### #535 — parser owns Markdown structure

This is non-negotiable.

`mdast-util-from-markdown` establishes Markdown structure exactly once.

DungeonBuddy may classify **application semantics on parser-established nodes**:

* canonical callout marker;
* Decision/Consequence marker;
* typed reference destination;
* graph-node reference destination;
* serializer-compatible source spelling where exact source spelling matters.

DungeonBuddy must not independently rediscover Markdown blocks with regexes.

### #529 — donor, not authority

Useful pieces include:

* `DecisionConsequenceNode.ts`
* its tests and editor interaction behavior;
* canonical serializer form;
* safety rules for exactly-two ordered panes;
* Plan insert/remove affordances;
* semantic-paste atomicity behavior;
* app-owned prep theme CSS;
* Session-26 behavioral regression fixtures.

Do **not** transplant its `markdownToTiptap.ts`.

Do **not** resurrect:

* `headingPattern`
* `bulletListPattern`
* `orderedListPattern`
* `calloutMarkerPattern`
* reference-definition regex recognition
* inline structural tokenization that duplicates MDAST
* indentation grammar
* raw line parsers that decide Markdown structure

---

# §3 Exact capability being delivered

This slice delivers **semantic prep authoring in Plan**.

That capability consists of one coherent round-trip contract across four entry paths.

| Path                             | Required behavior                                                          | Owning boundary                                       |
| -------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------- |
| Insert Decision/Consequence      | Insert exactly one valid paired semantic block                             | TipTap extension + Plan toolbar                       |
| Paste supported semantic prep    | Convert whole clipboard payload to structured TipTap exactly once          | Semantic paste + `analyzeMarkdownBody`                |
| Paste unsupported/ambiguous prep | Do not intercept; insert no partial parsed structure                       | Semantic paste                                        |
| Save/reload admitted prep        | Preserve nested lists, supported callouts, D/C panes, marks and references | admission + serializer + safety + workspace authoring |

Plain prose remains ordinary paste.

Rich ProseMirror/TipTap HTML remains owned by the normal rich-paste path.

A complete document containing leading YAML frontmatter must not be intercepted as semantic paste because dropping its metadata would be a partial conversion.

---

# §4 Supported semantic-prep grammar

Do **not** interpret this section as authorization to build another grammar. These are admission decisions over parser-established MDAST.

Existing supported language remains supported.

This slice additionally admits the minimum nested structures needed for semantic prep:

```text
list
└── listItem
    ├── paragraph
    ├── admitted nested list
    ├── admitted canonical callout
    └── admitted Decision/Consequence
```

Decision and Consequence panes may contain the existing serializer-safe block subset required by the original #529 behavior:

* paragraph
* heading
* horizontal rule
* admitted lists
* table

Do not silently add:

* arbitrary blockquotes
* raw HTML
* fenced/indented code
* task-list semantics
* arbitrary links
* nested Decision/Consequence inside Decision/Consequence
* callouts nested inside callouts unless explicitly proven and admitted
* arbitrary unlimited container nesting merely because MDAST can represent it

If the real Session-26 fixture requires another structure, establish whether it belongs to the same invariant before expanding scope.

---

# §5 Decision/Consequence admission contract

A parser-established blockquote may be classified as `decisionConsequence` only when all of the following are true:

1. Its application marker is canonically `DECISION-CONSEQUENCE`.
2. Its body parses through the same `parseMarkdownAst` boundary.
3. It contains one Decision section and one Consequence section.
4. Decision is first.
5. Consequence is second.
6. Both section labels are level-3 headings with semantic text exactly identifying the required pane.
7. No duplicate Decision heading exists.
8. No duplicate Consequence heading exists.
9. Neither pane is missing.
10. No ambiguous content exists outside the two panes.
11. Every child structure inside each pane is itself admitted in that context.

Malformed cases emit blocking diagnostics.

Examples that must **not** be guessed:

```md
> [!DECISION-CONSEQUENCE]
> ### Decision
> A
```

```md
> [!DECISION-CONSEQUENCE]
> ### Consequence
> B
>
> ### Decision
> A
```

```md
> [!DECISION-CONSEQUENCE]
> ### Decision
> A
>
> ### Decision
> B
>
> ### Consequence
> C
```

```md
> [!DECISION-CONSEQUENCE]
> ### Decision-ish
> A
>
> ### Consequence
> B
```

They may still receive a best-effort sealed viewing projection, but they cannot be cleanly admitted or Save-authoritative.

### Structural rule

The classifier operates on the parser-established `Blockquote` and its parsed body.

Regex may identify the **DungeonBuddy-owned marker text** after MDAST has established the blockquote.

Regex must not decide whether something is a blockquote, list, heading, definition, continuation, nested container, or other Markdown construct.

---

# §6 Nested list/callout contract

Current #535 intentionally emits warnings for:

* nested lists;
* callouts inside list items.

This slice may relax those restrictions only where serializer + safety can represent the result losslessly.

## Required behavior

Given:

```md
- Outer choice
  - Inner choice
    > [!GM-NOTE]
    > Something changes.
```

the parser owns the list/listItem/blockquote structure.

DungeonBuddy may then classify the nested blockquote as `GM-NOTE`.

Do not reconstruct its nesting from indentation strings.

### Ordered-list warning

Before claiming arbitrary nested ordered-list support, prove serializer indentation for multi-digit markers.

For example:

```md
10. Outer
    - Inner
```

must either round-trip correctly or remain outside the admitted subset.

Do not let `semanticMarkdownSafety` claim a structure that `calloutMarkdown.ts` serializes ambiguously.

---

# §7 TipTap extension contract

Port the useful #529 Decision/Consequence extension behavior onto current `main`.

Expected semantic nodes:

```text
DecisionConsequenceNode
DecisionPane
ConsequencePane
```

Required schema:

```text
decisionConsequence:
  content = "decisionPane consequencePane"

decisionPane:
  content = "block+"

consequencePane:
  content = "block+"
```

Required interaction behavior:

* `insertDecisionConsequence()` inserts an empty pair.
* deleting/removing the semantic block removes the pair as one unit.
* the pair cannot structurally reorder its panes.
* an empty pair may retain the existing safe Backspace behavior from #529 if its tests remain valid.
* ordinary editing inside a pane behaves like normal TipTap block editing.

The node schema may be mounted in the shared editor extension set if required so persisted D/C content can hydrate/render safely across shared document infrastructure.

**Authoring affordance remains Plan-owned.**

Build must not gain a Decision/Consequence launcher from this slice.

---

# §8 Serializer contract

Port the canonical Decision/Consequence serialization behavior into current `calloutMarkdown.ts`.

Exactly:

```md
> [!DECISION-CONSEQUENCE]
> ### Decision
> <decision body>
>
> ### Consequence
> <consequence body>
```

No alternate emitted spelling.

The serializer must preserve:

* marks already supported by semantic Markdown;
* graph references;
* typed/action references;
* nested admitted list structure;
* admitted callouts;
* tables in currently-supported form.

### Required round-trip property

For every newly admitted semantic-prep fixture:

```text
parse(source)
→ TipTap A
→ serialize(A)
→ canonical source
→ parse(canonical source)
→ TipTap B
```

`A` and `B` must be semantically equal.

Exact source spelling need not survive where current DungeonBuddy policy intentionally canonicalizes a supported spelling.

Unsupported source authority behavior from #527 must remain unchanged.

---

# §9 Outgoing semantic-safety contract

Extend `semanticMarkdownSafety.ts` only as far as the serializer is proven.

Required D/C checks:

* exactly two children;
* first child `decisionPane`;
* second child `consequencePane`;
* pane nodes cannot exist outside a D/C parent;
* unsupported pane children block Save;
* nested D/C blocks block unless this handoff explicitly proves otherwise.

Required nested-list checks:

`semanticMarkdownSafety` must agree with the actual admitted/serializable nested subset.

Do not merely copy #529's broad `LIST_ITEM_CHILD_TYPES` expansion.

For every newly allowed node/context pair there must be a corresponding round-trip test.

---

# §10 Semantic paste contract

Port the behavioral intent of #529's `SemanticMarkdownPaste`, but rebuild its Markdown detection on #535.

## Required behavior

### Plain prose

```text
Just a sentence about the wall.
```

Do not intercept.

Let the normal paste path own it.

### Rich editor HTML

If the clipboard carries TipTap/ProseMirror semantic HTML representing an editor structure, do not replace that with the plain-text Markdown parser path.

### Supported semantic Markdown

If the clipboard contains semantic Markdown that this editor recognizes and `analyzeMarkdownBody` produces zero blocking diagnostics:

* intercept once;
* insert the complete projected content once;
* do not also insert the plain clipboard text.

### Unsupported / mixed Markdown

Example:

```md
## Prep

- Hold the wall
  - > [!DECISION-CONSEQUENCE]
    > ### Decision
    > Advance
    >
    > ### Consequence
    > Reinforcements arrive

See [rules](https://example.com/rules).
```

If any part produces a blocking diagnostic:

* do not partially insert the parsed heading/list/D/C;
* return control to the ordinary paste path;
* editor state must not already contain a partial semantic conversion.

### Frontmatter

A clipboard document with leading YAML frontmatter is not a semantic-body paste payload.

Do not strip the frontmatter and paste only the body.

### Detection

Do not restore #529's Markdown structural regex heuristic.

Prefer a parser/projection-backed predicate such as:

```text
analyze clipboard body
→ zero blockers?
→ contains a semantic block worth intercepting?
```

Plain paragraph-only text should not trigger interception.

Useful semantic-block signals may include parser-established:

* heading;
* list;
* supported callout;
* Decision/Consequence;
* table.

If list interception needs a threshold to avoid changing ordinary one-line paste behavior, preserve that deliberately and test it rather than rediscovering list syntax with regex.

---

# §11 Plan UX contract

Restore the useful Plan behavior from #529.

In Plan's **Insert blocks** tools:

```text
Read aloud
GM note
Rules
Warning
Decision / Consequence
```

`Decision / Consequence` invokes the TipTap command.

Plan removal should treat a D/C pair as one semantic block rather than deleting a pane independently when the generic "Remove block" action is used.

Mount `SemanticMarkdownPaste` on Plan.

Do not add:

* Ask
* Recap
* Combat
* Threat
* statblock editing
* graph writes
* additional Build launchers
* new persistence controls

Those remain separate capabilities.

---

# §12 Product CSS ownership

Current `main` still imports prep theme styling from:

```text
evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css
```

Finish the #529 cleanup by moving the production-required theme rules into app-owned code:

```text
apps/live-control-ui/src/tiptap/prepMarkdownThemes.css
```

Plan must import the app-owned stylesheet.

`evals/` must not be a runtime production dependency.

This is a code-ownership cleanup inside the same semantic-prep capability, not authorization to visually redesign the editor.

Preserve existing dogfood styling unless a rule is specifically required for Decision/Consequence.

---

# §13 Files in scope

Expected allowlist:

| Action | Path                                                                         | Purpose                                                 |
| ------ | ---------------------------------------------------------------------------- | ------------------------------------------------------- |
| Create | `apps/live-control-ui/src/tiptap/extensions/DecisionConsequenceNode.ts`      | Semantic TipTap structure + commands                    |
| Create | `apps/live-control-ui/src/tiptap/extensions/DecisionConsequenceNode.test.ts` | Editor/schema proof                                     |
| Create | `apps/live-control-ui/src/tiptap/extensions/SemanticMarkdownPaste.ts`        | Atomic Plan semantic paste                              |
| Create | `apps/live-control-ui/src/tiptap/extensions/SemanticMarkdownPaste.test.ts`   | Paste-path proof                                        |
| Modify | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx`                     | Mount D/C schema if required                            |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts`              | Admit nested prep + classify D/C using MDAST            |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownIngressCorpus.test.ts`     | Adversarial/source corpus                               |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts`          | Import/round-trip regressions                           |
| Modify | `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts`                | Canonical D/C serialization + safe nested serialization |
| Modify | `apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts`         | Outgoing safety for exact admitted subset               |
| Modify | `apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.test.ts`    | Safety regressions                                      |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx`      | Plan insertion/removal/paste + CSS ownership            |
| Create | `apps/live-control-ui/src/tiptap/prepMarkdownThemes.css`                     | App-owned semantic-prep styling                         |
| Create | `Docs/Plans/HANDOFF-BUILD-finish-dogfood-polish-semantic-prep-authoring.md`  | Checked-in implementation authority                     |

### Bounded discovery exception

Additional existing test files under:

```text
apps/live-control-ui/src/workspaceDocument/
apps/live-control-ui/src/tiptap/
apps/live-control-ui/src/planSurface/
```

may be modified only when an existing owning-boundary regression requires adjustment for the new supported structure.

Maximum additional production paths: **2**.

If more production files are required, stop and report why the mission cannot remain within this slice.

---

# §14 Explicitly out of scope

Do not modify or claim:

* parser replacement;
* parser dependency selection;
* frontmatter representation;
* workspace local-state schema;
* graph identity;
* graph writes;
* semantic node creation in the World Graph;
* arbitrary Markdown links;
* images;
* code blocks;
* task lists;
* raw HTML;
* Ask blocks;
* Recap blocks;
* Threat blocks;
* Combat blocks;
* statblock authoring;
* Build-surface D/C launcher;
* Runbook-specific authoring UX;
* new backend endpoints;
* new durable document format;
* generalized arbitrary nested CommonMark support;
* handoff/docs cleanup unrelated to this capability.

---

# §15 Required adversarial cases

These are merge gates, not optional polish.

## Decision/Consequence

Clean canonical pair.

Missing Decision.

Missing Consequence.

Reversed panes.

Duplicate Decision.

Duplicate Consequence.

Wrong heading level.

Near-match heading text.

Content before Decision.

Ambiguous extra content between/outside pane sections.

Nested D/C.

D/C inside an admitted list item.

## Nested prep

Nested bullet list.

Nested ordered list only if serializer-safe and explicitly claimed.

Supported callout inside list item.

Plain blockquote inside list item remains blocked.

Nested callout inside callout remains blocked unless explicitly proven.

Table/list combination actually required by Session-26 fixture.

## Paste

Plain prose not intercepted.

Supported D/C paste inserted once.

Supported nested prep paste inserted once.

Rich ProseMirror/Tiptap HTML deferred.

Frontmatter payload deferred.

One unsupported ordinary link causes zero semantic insertion.

One unsupported image causes zero semantic insertion.

One unsupported code block causes zero semantic insertion.

## Existing #535 challenge set

Re-run the existing corpus cases covering:

* escaped reference definition labels;
* zero-space definitions;
* split destinations;
* indented code;
* nested blockquote/heading;
* images;
* autolinks;
* Setext headings;
* tasks;
* raw HTML.

Adding semantic prep must not reopen any of these holes.

---

# §16 Session-26 acceptance fixture

The implementation must include at least one realistic nested prep fixture shaped like actual dogfood intent, not only synthetic unit fragments.

For example:

```md
## North Gate

- If the party holds position:
  - > [!DECISION-CONSEQUENCE]
    > ### Decision
    > Hold the gate and keep the refugees behind the wall.
    >
    > ### Consequence
    > - The pressure remains concentrated at the gate.
    > - Lysandra can reposition the reserve.

- If the party abandons the gate:
  > [!GM-NOTE]
  > Advance the breach clock.
```

The exact prose may follow the existing Session-26 fixture already in the repository.

Required:

```text
source
→ parse/admit
→ structured TipTap
→ serialize
→ reparse
→ semantic equality
```

Zero blocking diagnostics.

---

# §17 Persistence and source-authority matrix

| Situation                                          | Required result                                                  |
| -------------------------------------------------- | ---------------------------------------------------------------- |
| Clean supported semantic prep loaded from Markdown | TipTap becomes editable semantic projection                      |
| User edits clean prep                              | TipTap remains editor authority under existing workspace rules   |
| Save                                               | Canonical semantic Markdown emitted                              |
| Hard reload                                        | Same semantic structure restored                                 |
| Unsupported/ambiguous source                       | Existing #527 sealed/source-authority behavior                   |
| Parser upgrade changes diagnostics                 | Persisted authority bit still prevents silent lossy regeneration |
| Semantic paste contains blocker                    | No partial semantic insertion occurs                             |
| Existing v5 local state                            | No new migration; this slice must not change local-state schema  |

No persistence migration is authorized.

---

# §18 Evidence required to merge

PR-description test claims are not evidence.

Record actual command output or CI evidence.

| Guarantee                                                  | Owning boundary          | Required evidence                        |
| ---------------------------------------------------------- | ------------------------ | ---------------------------------------- |
| D/C schema exactly two ordered panes                       | TipTap                   | `DecisionConsequenceNode.test.ts`        |
| Canonical D/C parser projection                            | admission                | focused importer tests                   |
| Malformed D/C fails closed                                 | admission                | adversarial corpus/tests                 |
| Nested Session-26 prep round-trips                         | admission + serializer   | exact fixture parse→serialize→parse      |
| Serializer never claims unsafe nested structures           | semantic safety          | focused safety tests                     |
| Supported semantic paste is atomic                         | paste plugin             | paste integration tests                  |
| Unsupported semantic paste performs zero partial insertion | paste plugin             | before/after editor JSON equality        |
| Existing #535 holes remain sealed                          | Markdown ingress         | complete existing Markdown corpus        |
| #527 authority behavior remains intact                     | workspace authoring      | workspace/source-fidelity tests          |
| Plan exposes D/C insertion                                 | Plan component           | component test or minimal manual dogfood |
| Build does not gain D/C launcher                           | surface UX               | existing component test or manual check  |
| Production no longer imports CSS from `evals/`             | bundle/source inspection | grep/diff + build                        |
| Application compiles                                       | frontend                 | typecheck                                |
| Production bundle succeeds                                 | frontend                 | build                                    |

Required commands from `apps/live-control-ui`:

```bash
npx vitest run src/tiptap/extensions/DecisionConsequenceNode.test.ts
npx vitest run src/tiptap/extensions/SemanticMarkdownPaste.test.ts
npx vitest run src/tiptap/markdown/
npx vitest run src/workspaceDocument/ src/tiptap/
npm run typecheck
npm run build
```

Also:

```bash
git diff --check
git diff --name-only <BASE>...HEAD
git diff --stat <BASE>...HEAD
```

If the full repository suite has known base failures, compare base and head and report branch-only failures separately.

Do not call an unobserved command green.

---

# §19 Minimal dogfood proof

Use the existing Plan surface.

No new testing surface.

Scenario:

1. Open a Plan document.
2. Unlock editing.
3. Insert Decision / Consequence from Plan tools.
4. Enter prose in each pane.
5. Create or paste a nested Session-26-style fork.
6. Confirm structure renders as semantic nested prep.
7. Copy/export Markdown.
8. Confirm canonical marker/headings.
9. Save.
10. Hard reload.
11. Confirm the same panes, nesting, callouts, references, and text remain structured.
12. Paste a similar document containing one unsupported ordinary Markdown link.
13. Confirm no partial semantic conversion occurs before ordinary paste handling.

Capture the smallest useful evidence available: test result, screenshot, or exact manual observation.

Do not build new dogfood instrumentation.

---

# §20 Nano-commit contract

Prefer a sequence approximately like:

### Commit 1 — semantic TipTap structure

```text
DOGFOOD-POLISH: restore decision consequence editor nodes
```

* D/C nodes
* schema
* commands
* focused tests

No Markdown parser changes yet.

### Commit 2 — AST admission

```text
DOGFOOD-POLISH: admit nested semantic prep through MDAST
```

* nested-list contexts
* nested supported callouts
* D/C classifier
* malformed blocking diagnostics
* importer/corpus tests

No old #529 grammar code.

### Commit 3 — serializer and safety

```text
DOGFOOD-POLISH: round trip semantic prep blocks
```

* canonical D/C Markdown
* safe nested serialization
* matching outgoing safety
* round-trip regressions

### Commit 4 — Plan semantic paste and tools

```text
DOGFOOD-POLISH: author semantic prep in Plan
```

* Plan launcher
* remove-block behavior
* parser-backed semantic paste
* atomic-paste tests

### Commit 5 — product-owned styling + integrated proof

```text
DOGFOOD-POLISH: own prep theme styling in app
```

* move production theme dependency out of `evals/`
* integrated Session-26 fixture/proof
* no unrelated visual redesign

If implementation reality suggests a better nano-commit decomposition, preserve the discrete proof stories rather than mechanically following these names.

---

# §21 Stop conditions

Stop rather than expanding if:

### Structural-parser regression

You believe you need a regex to decide whether source is a:

* list;
* heading;
* blockquote;
* reference definition;
* code block;
* continuation line;
* nested container.

That means #535's boundary is being bypassed.

### Serializer mismatch

Admission can represent a nested structure that `calloutMarkdown.ts` cannot serialize without ambiguity.

Either narrow admission or explicitly fix/prove serialization in this slice.

Do not simply loosen `semanticMarkdownSafety`.

### Unbounded nesting

Session-26 support unexpectedly requires generalized arbitrary CommonMark nesting.

Stop and identify the actual minimum grammar.

### New durable state

Implementation appears to require:

* local-state v6;
* new persisted provenance;
* new document schema;
* backend changes.

Stop. This mission does not own a new durable contract.

### Feature expansion

Implementation starts adding:

* Ask;
* Recap;
* Threat;
* Combat;
* statblocks;
* graph writes;
* generalized semantic blocks.

Stop and dispatch separately.

### More than two unexpected production paths

Report why the current allowlist was insufficient before changing them.

---

# §22 Required review handback

The coding agent must return:

1. exact branch / PR / head SHA;
2. base SHA;
3. mission and merge-ready invariant copied verbatim;
4. nano-commit list and purpose;
5. exact changed-path list;
6. confirmation that old #529 `markdownToTiptap.ts` grammar was **not** resurrected;
7. explanation of how D/C is classified from parser-established MDAST;
8. exact nested structures newly admitted;
9. exact structures intentionally still blocked;
10. parse→serialize→parse evidence for Session-26 fixture;
11. malformed D/C adversarial results;
12. semantic-paste atomicity results;
13. #535 corpus regression results;
14. #527 source-authority regression results;
15. typecheck/build results;
16. provenance for every result: local / CI / manual;
17. baseline failures, if any;
18. paths outside the allowlist, or `none`;
19. stop conditions encountered, or `none`;
20. confirmation that Build gained no D/C launcher;
21. confirmation production Plan no longer imports CSS from `evals/`.

---

# §23 Acceptance rubric

Merge only when all are true:

* [ ] A GM can insert a Decision/Consequence pair in Plan.
* [ ] A clean canonical D/C Markdown block imports into exactly two ordered semantic panes.
* [ ] A D/C block serializes to exactly the canonical marker + headings.
* [ ] Parse→serialize→parse preserves semantic pane content.
* [ ] Required Session-26 nested list/callout/D/C structure is admitted.
* [ ] Unsupported nested structures still emit blocking diagnostics.
* [ ] Malformed D/C is never guessed into a clean pair.
* [ ] Semantic paste is atomic.
* [ ] Plain prose is not hijacked by semantic paste.
* [ ] Rich editor HTML is not hijacked by semantic paste.
* [ ] Frontmatter documents are not partially converted.
* [ ] Outgoing safety exactly matches what serializer can preserve.
* [ ] #535 adversarial Markdown corpus remains sealed where expected.
* [ ] #527 authoritative-source behavior remains intact.
* [ ] Existing reference semantics remain intact.
* [ ] Plan owns the D/C authoring affordance.
* [ ] Build has no D/C launcher.
* [ ] Production theme CSS is app-owned rather than imported from `evals/`.
* [ ] No second structural Markdown grammar exists in the resulting diff.
* [ ] No new persistence schema was introduced.
* [ ] Exact required verification was actually observed.

---

# §24 Completion definition

This DOGFOOD-POLISH sequence is complete when the original #529 product outcome exists on top of the #535 architecture:

```text
raw/session-prep Markdown
        ↓
single CommonMark/GFM parser
        ↓
DungeonBuddy admission/classification
        ↓
semantic TipTap prep
        ↕
canonical Markdown serializer
        ↓
existing authoritative Save/reload path
```

with Plan providing intentional semantic authoring tools and unsupported source remaining fail-closed.

The old #529 branch is not the desired final diff.

Its surviving value is the feature design, editor nodes, UX behavior, canonical representation, styling, and tests.

The final implementation must make those behaviors native to the architecture now on `main`.
