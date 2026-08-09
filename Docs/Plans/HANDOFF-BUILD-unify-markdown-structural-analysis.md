# HANDOFF — RESCUE: unify Markdown structural analysis

**Created:** 2026-08-09
**Repository:** `Drakosfire/DungeonMindBuddy`
**Mode:** RESCUE / infrastructure sidequest
**Priority:** BLOCKING `DOGFOOD-POLISH: semantic prep authoring` (#529)
**Target PR title:** `DOGFOOD-POLISH: unify Markdown structural analysis`
**Suggested branch:** `agent/dogfood-polish-markdown-ast-admission`

## §0 Mission

Replace DungeonBuddy's duplicated handwritten Markdown structural recognition with **one parser-backed structural analysis boundary**.

The result must make this statement true:

> Markdown structure is interpreted exactly once. DungeonBuddy decides which parsed structures it supports; it does not independently rediscover Markdown structure with regexes in its safety gate and again in its TipTap importer.

This is a rescue sidequest, not a feature-expansion PR.

Do **not** add Decision / Consequence authoring, nested semantic prep, new Plan UI, new persistence semantics, arbitrary Markdown support, or new graph behavior here.

The purpose of this PR is to establish a trustworthy ingress boundary underneath those features.

---

# §1 Why this rescue exists

PR #529 has now gone through seven adversarial review cycles.

The recurring failures have not been isolated implementation mistakes. They have exposed the same architectural defect repeatedly.

The current Markdown path contains two overlapping interpretations of Markdown:

1. source-safety logic asks whether raw Markdown can be imported safely;
2. the importer independently parses raw lines into TipTap.

Those two grammars drift.

Successive reviews have exposed examples including:

* root indentation interpreted inconsistently;
* tab indentation;
* indented code;
* nested blockquotes;
* nested headings;
* horizontal rules;
* `*` / `+` list markers;
* unsupported nested callouts;
* ordinary links inside containers;
* reference-style link definitions;
* zero-space reference definitions;
* multiline reference definitions;
* escaped characters inside reference labels;
* frontmatter being accidentally consumed by semantic paste;
* parser-upgrade/source-authority interactions.

The seventh review reached another legal CommonMark form:

```md
[foo\]]: /url
```

The latest handwritten reference-definition recognizer still does not understand the complete construct.

**Do not fix this by adding another regex.**

That would address the next example without addressing the class of defects.

---

# §2 Current anchors

## Merged foundation

PR #527:

`DOGFOOD-POLISH: preserve Markdown source fidelity`

is merged.

Its source-authority and save-safety behavior is permanent infrastructure and must survive this sidequest unchanged.

Important #527 behavior includes:

* leading YAML frontmatter preserved byte-for-byte;
* unsafe source can produce a best-effort editor projection but remains authoritative as raw Markdown;
* `exported_markdown_authoritative=true` seals that source;
* edits to a sealed projection must not overwrite authoritative Markdown;
* Save fails closed while the projection is sealed;
* parser upgrades do **not** automatically make an old lossy projection authoritative;
* explicit `reimportFromAuthoritativeMarkdown()` is required before authority can move back to TipTap;
* outgoing TipTap JSON is separately checked for safe Markdown serialization.

Do not weaken these invariants in order to simplify the parser integration.

## Frozen successor

PR #529:

`DOGFOOD-POLISH: semantic prep authoring`

latest reviewed head at dispatch time:

`62a24eb705f000e222b843995cde661d1f6d2b22`

Freeze this branch.

Do not continue repairing Markdown syntax recognition inside #529 while this rescue is underway.

At dispatch time #529 is also behind current `main`. Do **not** branch the rescue PR from #529.

## Rescue base

Branch from **current `main` at execution time**.

At handoff-writing time `main` had continued advancing after #529 branched. Resolve the live `main` SHA yourself before creating the branch.

The rescue must contain the merged #527 fidelity foundation and must not depend on #529.

---

# §3 Merge-ready invariant

The rescue PR is merge-ready when this invariant holds:

> Every Markdown body is parsed by one CommonMark/GFM-aware structural parser before DungeonBuddy makes support decisions. Admission diagnostics and TipTap projection derive from that parsed structure. Unsupported structures may be projected best-effort for viewing, but they always produce blocking diagnostics and can never become durable authoritative Markdown through the editor.

There is a second equally important invariant:

> The rescue does not expand DungeonBuddy's supported Markdown language. It changes how the existing language is recognized.

Using a complete Markdown parser does **not** mean DungeonBuddy suddenly supports all CommonMark or GFM.

The parser is the recognizer.

DungeonBuddy owns the admission policy.

---

# §4 Scope boundary

## In scope

* add a real Markdown structural parser to `live-control-ui`;
* parse Markdown into a structural AST;
* make Markdown import/admission diagnostics derive from that AST;
* make TipTap projection derive from that same AST;
* preserve current public importer APIs where practical;
* preserve current supported Markdown subset;
* preserve current serializer behavior;
* preserve frontmatter fidelity;
* preserve source-authority behavior;
* preserve outgoing `semanticMarkdownSafety` or equivalent TipTap→Markdown validation;
* capture all discovered parser/safety regressions as permanent tests;
* establish explicit container-aware admission policy;
* leave an obvious extension seam for #529 to add nested prep structures later.

## Explicitly out of scope

Do not:

* implement Decision / Consequence;
* mount Decision / Consequence TipTap nodes;
* add semantic paste;
* add nested prep authoring;
* expose Plan Insert affordances;
* modify Build/Plan product behavior beyond parser compatibility;
* add ordinary Markdown link support;
* add image support;
* add code-block editing;
* add arbitrary blockquote support;
* add arbitrary HTML;
* add task-list editing;
* add footnote editing;
* redesign TipTap schemas;
* change local-state schema;
* change `exported_markdown_authoritative`;
* change Save semantics;
* change graph identity/reference semantics;
* modify backend APIs;
* promote corpus content;
* rewrite the Markdown serializer merely because a new library offers one;
* turn this into “support all Markdown.”

If parser adoption accidentally makes a previously unsupported construct editable, treat that as a regression.

---

# §5 Preferred parser architecture

The preferred implementation is a parser from the unified/remark ecosystem.

Start by evaluating:

```text
unified
remark-parse
remark-gfm
@types/mdast
```

The desired conceptual boundary is:

```text
raw workspace Markdown
        │
        ├── preserve/remove leading YAML frontmatter using existing fidelity code
        │
        ▼
Markdown body
        │
        ▼
CommonMark/GFM parser
        │
        ▼
MDAST
        │
        ▼
DungeonBuddy admission + projection visitor
        │
        ├── supported structure ──→ TipTap
        │
        └── unsupported structure → blocking diagnostic
```

Do **not** use `remark-stringify` to replace the existing TipTap→Markdown serializer as part of this rescue.

Ingress is the problem being rescued.

Do not casually change egress.

---

# §6 Parser-selection compatibility gate

Before committing to `remark-gfm` wholesale, write a very small characterization test against current DungeonBuddy behavior.

A parser can recognize more syntax than DungeonBuddy currently does. That is expected.

It must not silently change what DungeonBuddy admits.

Pay particular attention to GFM extensions such as:

* bare URL/email autolinking;
* single-tilde strikethrough;
* task-list markers;
* tables;
* footnotes.

For example, ordinary source text containing:

```md
https://example.com
```

may currently behave as plain paragraph text.

If the selected parser represents that source as an autolink node, the adapter must preserve the pre-rescue DungeonBuddy behavior rather than accidentally introducing ordinary-link support.

Configure `remark-gfm` conservatively where possible—for example, do not introduce single-tilde strike if DungeonBuddy currently emits/accepts canonical `~~strike~~`.

If bundled GFM behavior makes compatibility awkward, it is acceptable to use the lower-level `mdast-util-from-markdown` plus only the syntax extensions required for DungeonBuddy's current supported subset.

The architectural requirement is **one parser-backed interpretation**, not loyalty to a specific npm package.

Document the choice in code/tests, not in a large ADR.

---

# §7 Frontmatter is deliberately outside the AST contract

Do not “simplify” YAML frontmatter by handing ownership to a Markdown plugin.

The existing frontmatter contract is stronger than semantic YAML parsing:

> leading frontmatter bytes, including newline convention, are preserved exactly.

Keep using the existing frontmatter boundary.

Conceptually:

```text
original source
    │
    ├── exact frontmatter bytes
    └── Markdown body
             │
             ▼
          parser
```

The AST operates on the body.

When diagnostics report source line numbers, account for stripped frontmatter so line references still point to the original document.

Required regression:

```text
CRLF frontmatter
+ unsafe body node
→ frontmatter unchanged
→ diagnostic line maps to original source
→ source remains sealed
```

---

# §8 One admission visitor, not another safety parser

The rescue should eliminate the architectural reason `sourceSafetyDiagnostics()` keeps growing new Markdown recognizers.

A good target shape is approximately:

```ts
type MarkdownAdmissionContext =
  | "document"
  | "listItem"
  | "callout"
  | "tableCell";

type MarkdownProjectionResult = {
  node?: JSONContent;
  diagnostics: MarkdownImportDiagnostic[];
};

function projectMdastNode(
  node: MdastNode,
  context: MarkdownAdmissionContext,
  source: string,
  options: MarkdownImportOptions,
): MarkdownProjectionResult;
```

Exact names are not prescribed.

The important property is this:

**the same traversal decides whether a node is supported and how that supported node projects into TipTap.**

Do not build:

```text
AST safety walker
+
independent AST→TipTap grammar
```

and recreate the same problem one layer higher.

Projection and admission should be coupled closely enough that:

> A node cannot be projected as supported unless the admission logic for that exact node/context has accepted it.

`hasBlockingMarkdownImportDiagnostics(markdown)` may continue to exist as a public convenience API, but it should derive its answer from the same importer/analysis result.

---

# §9 Raw-source checks are still allowed — but only for provenance

A real Markdown AST does not preserve every source spelling DungeonBuddy currently cares about.

That does **not** justify returning to handwritten structural parsing.

Use raw source slices only after the parser has already told you what structure exists.

Examples:

### Setext versus ATX heading

The AST may tell you:

```text
heading(level=2)
```

If DungeonBuddy supports only serializer-compatible ATX headings, inspect the source span of that known `heading` node to distinguish:

```md
## Heading
```

from:

```md
Heading
-------
```

That is a **source-form compatibility check** on an already parsed heading.

It is not an alternate Markdown parser.

### Bullet marker spelling

If current serializer/admission supports `-` but intentionally rejects `*` or `+`, the AST identifies a list first.

Source position can then validate the admitted spelling.

### Table alignment

Prefer AST metadata such as alignment and row structure wherever available.

Do not rediscover table grammar with pipe-splitting regexes if the parser already owns it.

Rule:

> AST determines structure. Raw source may validate canonical spellings that the serializer cannot preserve.

---

# §10 Current supported-language baseline

The rescue begins from the behavior on merged `main`, not from #529.

Before refactoring, characterize the current accepted subset with tests.

Expected supported categories include the existing #527 contract:

### Blocks

* paragraphs;
* ATX headings H1–H6;
* canonical horizontal rules already emitted by the serializer;
* currently supported flat bullet lists;
* currently supported flat ordered lists;
* canonical supported DungeonBuddy callouts;
* current safe flat GFM tables.

### Inline

* plain text;
* bold;
* italic;
* strike using the currently supported spelling;
* inline code;
* typed DungeonBuddy runbook references;
* graph-node `dmb-node:` references.

Do not infer support from this handoff when the current tests/code disagree.

**Current executable behavior wins.**

---

# §11 Explicit unsupported structures

The new parser is useful largely because it can identify unsupported structures correctly.

These should continue to produce blocking diagnostics unless existing main behavior explicitly says otherwise:

* fenced code blocks;
* indented code blocks;
* raw HTML;
* ordinary blockquotes;
* images;
* ordinary Markdown links;
* reference-style links;
* link reference definitions;
* image references/definitions;
* setext headings if still noncanonical;
* task lists;
* unsupported list marker/spelling forms;
* unsupported hard breaks;
* unsupported GFM extensions;
* malformed/unsupported callouts;
* structural nesting not supported by current `main`.

Do not flatten one of these into ordinary paragraph text and then call the import safe.

A best-effort visual projection is allowed only if the same import result contains a blocking diagnostic and the raw source remains authoritative.

---

# §12 DungeonBuddy references

Typed references and graph references are app semantics layered on ordinary Markdown link syntax.

The parser should own recognition of the Markdown link.

DungeonBuddy should then classify the parsed destination.

For example:

```text
link AST
   │
   ├── href begins #dmb-ref:...    → runbookReference
   ├── href begins #dmb-action:... → runbookReference
   ├── href begins dmb-node:...    → graphNodeReference
   └── anything else               → unsupported ordinary link diagnostic
```

Do not maintain a separate regex capable of parsing all Markdown link syntax from raw text.

This is one of the major benefits of the rescue.

Escaping inside labels should already have been resolved by the Markdown parser before DungeonBuddy sees the semantic label.

---

# §13 Callouts

Current canonical callouts remain supported.

They are Markdown blockquotes with DungeonBuddy-owned marker semantics.

The CommonMark parser should establish the blockquote container.

Then one shared DungeonBuddy classifier may determine whether that blockquote matches a supported callout structure.

Conceptually:

```text
blockquote AST
    │
    ├── canonical [!READ-ALOUD] → callout
    ├── canonical [!GM-NOTE]    → callout
    ├── canonical [!RULES]      → callout
    ├── canonical [!WARNING]    → callout
    └── otherwise               → unsupported blockquote
```

Do not let `normalizeCalloutKind()` turn an arbitrary or unknown blockquote marker into a WARNING during import.

Do not expand aliases in this rescue unless current merged tests prove they are already part of the permanent source contract.

Decision / Consequence is **not** implemented here.

The API should merely make it straightforward for #529 to add another app-owned blockquote classifier after this PR merges.

---

# §14 Tables

Tables are an important characterization case because the existing implementation already contains substantial handwritten table recognition.

Move structural recognition to the Markdown/GFM AST.

Preserve the current safe-editing constraints.

At minimum:

- escaped pipes must remain correct;
- current supported table cells round-trip;
- alignment markers remain blocked if the editor does not preserve alignment;
- uneven rows remain blocked if normalization would lose source meaning;
- tables remain flat if nested content is not part of the current contract;
- unsupported inline syntax inside cells still blocks the import.

Do not use the rescue as an excuse to expand the TipTap table model.

---

# §15 `semanticMarkdownSafety` remains conceptually distinct

There are two directions of safety:

```text
Markdown source → TipTap
TipTap → Markdown
```

This sidequest rescues the first.

The existing outgoing editor-JSON safety gate remains necessary.

Do not interpret “one Markdown parser” as permission to delete validation that prevents unsupported TipTap nodes from being serialized lossily.

The desired system is:

```text
INGRESS

source
→ real Markdown parser
→ admission/projector
→ TipTap
→ blocking diagnostics when unsupported


EGRESS

TipTap
→ semanticMarkdownSafety
→ existing serializer
→ Markdown
```

The two gates protect different boundaries.

---

# §16 Source-authority contract: non-negotiable regression suite

Run and preserve the #527 workspace-authority tests.

These are not incidental tests.

They define the correctness boundary of the rescue.

Required behavior includes:

### Unsupported source seals

```text
unsupported source
→ best-effort editor projection allowed
→ exported_markdown remains original source
→ exported_markdown_authoritative = true
→ Save disabled/fails closed
```

### Editing a sealed projection does not transfer authority

```text
sealed raw source
→ user edits TipTap projection
→ local TipTap may become dirty
→ raw exported_markdown remains untouched
→ Save remains blocked
```

### Parser upgrade does not silently bless stale TipTap

```text
source was unsupported under older parser
→ persisted local state contains sealed source + stale/lossy TipTap
→ new parser now understands source
→ reopen
→ source remains authoritative
→ Save remains blocked
→ only explicit reimportFromAuthoritativeMarkdown()
   rebuilds TipTap and clears authority
```

This last case is especially important for this rescue because the parser itself is changing.

Do not “helpfully” auto-reimport sealed documents after installing the new parser.

---

# §17 Required adversarial regression corpus

Create a clearly named test section/fixture corpus that survives after the rescue.

These cases should no longer each require bespoke structural regexes.

## Code / indentation

```md
    const gate = 'held'
```

Tab-indented equivalent.

Nested indentation shapes should be rejected according to current supported-language policy.

## Blockquote

```md
- Parent
  > plain blockquote
```

## Nested heading

```md
- Parent
  ## Nested heading
```

## Unsupported list markers

```md
* item
```

```md
+ item
```

Preserve the current product contract rather than whatever the parser happens to accept.

## Ordinary link

```md
[Rules](https://example.com/rules)
```

Also inside currently parsed containers.

## Image

```md
![Map](map.png)
```

## Reference-style link

```md
[Rules][rules]

[rules]: https://example.com/rules
```

## Zero-space definition

```md
[rules]:https://example.com/rules
```

## Split destination

```md
[rules]:
https://example.com/rules
```

## Escaped bracket in label

```md
[foo\]]: /url
```

This exact case ended review cycle 7.

The test should demonstrate that the real Markdown parser recognizes the construct and DungeonBuddy rejects the resulting definition node.

There should be no DungeonBuddy regex that needs to understand the escaped closing bracket.

## Fenced code

````md
```json
{"hp": 95}
```
````

## Setext heading

```md
Heading
-------
```

## Raw HTML

```md
<div>unsafe</div>
```

## Hard break

Include both Markdown hard-break spellings currently considered unsafe.

## Task list

```md
- [ ] Prepare encounter
```

## Frontmatter

CRLF frontmatter plus an unsupported body construct.

Confirm exact frontmatter preservation and correct diagnostic line numbers.

---

# §18 Supported round-trip corpus

Do not test only rejection.

We need proof that the rescue does not make normal authoring worse.

Retain/add fixtures for:

* ordinary prose;
* `snake_case_value`;
* intraword underscores;
* escaped `\*`, `\_`, `\~`, `\[`;
* H1–H6;
* bold;
* italic;
* strike;
* inline code with awkward backticks;
* typed references;
* graph-node references;
* horizontal rule;
* current bullet list;
* current ordered list;
* all supported callout kinds;
* safe escaped-pipe table;
* CRLF frontmatter.

For every admitted fixture, test the semantic invariant:

```text
source
→ Markdown AST
→ TipTap
→ semantic Markdown
→ Markdown AST
```

The two parsed results should be equivalent **within DungeonBuddy's admitted semantic model**.

Do not require byte-for-byte body identity where the existing contract intentionally canonicalizes Markdown.

Frontmatter remains byte-exact separately.

---

# §19 AST equivalence helper

Build a small test-only normalization helper rather than comparing raw MDAST objects.

Raw parser ASTs contain source positions and possibly parser-specific metadata.

Normalize to semantic structure.

For example:

```text
heading(level, children)
paragraph(children)
strong(children)
emphasis(children)
delete(children)
inlineCode(value)
list(ordered, start, items)
table(rows...)
blockquote(...)
link(url, children)
definition(identifier, url)
...
```

Remove source positions.

Normalize only parser metadata, not meaningful semantics.

This helper will become valuable when #529 later introduces nested lists and Decision / Consequence.

Do not turn it into production architecture unless production genuinely needs it.

---

# §20 Semantic paste is not part of this PR

#529 currently includes semantic-paste work.

Do not transplant it.

However, design the ingress API so #529 can later do:

```ts
const analysis = analyzeMarkdown(markdown);

if (analysis.hasBlockingDiagnostics) {
  // Do not partially semantic-paste.
} else {
  // Insert analysis.doc once.
}
```

That is the entire future integration seam we need.

Do not add clipboard event code in the rescue.

---

# §21 Quarry policy for #529

#529 is useful as an adversarial test quarry.

You may copy or adapt **tests/fixtures that demonstrate parser failures**.

Do not wholesale cherry-pick its production parser.

Specifically avoid carrying over the growing family of handwritten helpers whose purpose is to rediscover Markdown syntax.

The rescue exists because that approach reached its limit.

Likewise, do not bring Decision / Consequence schema/UI code into this branch.

---

# §22 Implementation sequence

Use this sequence unless the code proves a materially better ordering.

## Commit 1 — characterize current ingress

Before changing behavior:

* add focused baseline tests for every currently supported source form;
* add the seven-review adversarial cases;
* identify which cases current main already blocks and which expose the architectural problem;
* characterize bare URL/email behavior before enabling GFM parsing;
* characterize list-marker and setext behavior;
* ensure existing workspace-authority tests are green.

This commit should make the migration target explicit.

## Commit 2 — introduce parser adapter

Add the chosen parser dependencies.

Create a narrow module such as:

```text
apps/live-control-ui/src/tiptap/markdown/parseMarkdownAst.ts
```

or equivalent.

Responsibilities:

* accept body Markdown;
* return parser AST;
* preserve positions useful for diagnostics;
* contain parser configuration;
* contain no TipTap behavior.

Do not leak `unified` setup throughout the app.

## Commit 3 — AST admission/projector

Introduce the recursive AST→TipTap visitor.

Move block/inline structural recognition into it.

Emit blocking diagnostics for unsupported nodes.

Use shared helpers for app semantics:

* typed reference classification;
* graph-node reference classification;
* canonical callout classification.

At the end of this commit, `markdownToTiptapDoc()` should be a thin orchestration function rather than a line-oriented Markdown parser.

## Commit 4 — delete displaced handwritten grammar

Remove structural regex/parser code made obsolete by the AST path.

This commit matters.

A rescue that adds an AST parser but leaves the old structural recognizers active has failed architecturally.

Keep regexes only when they validate DungeonBuddy-owned syntax or canonical source spelling after the AST has established structure.

## Commit 5 — authority/integration hardening

Run/fix:

* workspace Markdown fidelity;
* parser-upgrade sealed-source behavior;
* serializer safety;
* app build/typecheck;
* full relevant test suite.

Avoid unrelated cleanup.

---

# §23 Code-review heuristic

During implementation, repeatedly ask:

> “If CommonMark invents another legal spelling of this same construct, does DungeonBuddy need a new regex?”

If the answer is yes for a standard Markdown construct, the rescue is not finished.

Examples where the answer should become **no**:

* reference definitions;
* nested blockquotes;
* code blocks;
* headings;
* links;
* images;
* emphasis;
* list structure.

Examples where a DungeonBuddy-specific recognizer is legitimate:

* whether a parsed link destination is `dmb-node:...`;
* whether a parsed link destination is `#dmb-ref:...`;
* whether a parsed blockquote begins with DungeonBuddy's canonical callout marker;
* whether source spelling matches DungeonBuddy's serializer-supported canonical subset.

---

# §24 Do not overcorrect

Seven review cycles can tempt a rewrite.

Do not rewrite the whole authoring stack.

The rescue should preserve these existing seams where possible:

```ts
markdownToTiptapDoc(...)
hasBlockingMarkdownImportDiagnostics(...)
tiptapJsonToSemanticMarkdown(...)
semanticMarkdownSafety(...)
stripLeadingYamlFrontmatter(...)
```

Their internals may change.

Their responsibilities should become clearer.

Do not make every caller understand MDAST.

The parser boundary belongs inside the Markdown adapter layer.

---

# §25 Dependency / browser considerations

`live-control-ui` is a Vite/React browser application.

Validate that the chosen parser stack bundles cleanly in this environment.

Required:

```text
npm run typecheck
npm test
npm run build
```

from the appropriate workspace/app location.

If the preferred parser stack creates a serious browser/bundle problem, investigate `mdast-util-from-markdown` directly before inventing another parser.

Do not fall back to custom regex parsing because of minor integration friction.

---

# §26 Required execution evidence

Do not rely on a PR-body checkbox claiming tests passed.

Capture actual executable evidence before handoff.

At minimum run the relevant equivalents of:

```text
Markdown importer tests
Markdown serializer/safety tests
workspace Markdown fidelity tests
typecheck
production build
```

If the repo has CI for the branch, ensure it is actually attached to the final reviewed head.

If CI does not exist, report the exact local commands and results in the final handoff to the reviewer.

No “should pass.”

No “not run but trivial.”

---

# §27 Definition of done

The rescue is complete only when all of the following are true:

* [ ] one real Markdown parser determines standard Markdown structure;
* [ ] importer diagnostics derive from parsed structure;
* [ ] TipTap projection derives from that same parsed structure;
* [ ] no parallel handwritten block grammar remains active;
* [ ] unsupported AST nodes produce blocking diagnostics;
* [ ] unsupported source cannot become durable authoritative Markdown;
* [ ] existing supported Markdown still round-trips;
* [ ] frontmatter remains byte-exact;
* [ ] typed references still work;
* [ ] graph-node references still work;
* [ ] canonical callouts still work;
* [ ] safe tables still work;
* [ ] outgoing TipTap safety remains enforced;
* [ ] sealed parser-upgrade source still requires explicit reimport;
* [ ] reference definitions are rejected structurally, including escaped-label forms;
* [ ] root/tab/indented code is rejected structurally;
* [ ] ordinary links/images/blockquotes/HTML remain unsupported;
* [ ] no Decision / Consequence feature leaked into the rescue;
* [ ] no semantic paste feature leaked into the rescue;
* [ ] no new persistence schema was introduced;
* [ ] typecheck passes with executable evidence;
* [ ] relevant tests pass with executable evidence;
* [ ] production build passes with executable evidence.

---

# §28 Handoff back to #529

After this rescue PR merges:

1. record the rescue merge SHA;
2. return to #529;
3. rebase #529 onto the new `main`;
4. resolve #529's handwritten parser changes **in favor of the new AST boundary**;
5. do not resurrect deleted structural regexes during conflict resolution;
6. reintroduce #529 capabilities incrementally:

   * nested admitted list structures;
   * canonical Decision / Consequence AST classification/projection;
   * semantic paste using blocking diagnostics from the shared analyzer;
   * Plan insertion UI;
7. replay the Session-26 semantic-prep fixtures;
8. replay every rescue regression;
9. rerun the #527 sealed-authority regressions.

The architecture after rebase should look like:

```text
                 Markdown parser
                       │
                       ▼
                structural AST
                       │
              DungeonBuddy admission
                 /            \
                /              \
       baseline grammar      Plan/#529 additions
              │                    │
              └──────────┬─────────┘
                         ▼
                       TipTap
```

#529 should extend the admission policy.

It should not extend the Markdown parser.

---

# §29 Reviewer challenge set

Before asking for review, manually reason through these without adding new structural regexes:

```md
[foo\]]: /url
```

```md
[foo]:
  /url
```

```md
    > [!GM-NOTE]
```

```md
- Parent
  > quote
```

```md
- Parent
  ## heading
```

```md
![alt](image.png)
```

```md
<https://example.com>
```

```md
Heading
=======
```

```md
- [ ] task
```

```md
<div>
raw html
</div>
```

For each one, you should be able to answer:

1. What AST node did the Markdown parser produce?
2. Is that node admitted in this container?
3. If not, where is the blocking diagnostic produced?
4. Can any editor/save path make a lossy projection authoritative?

If answering question 1 requires reasoning through one of our own regular expressions, the rescue has not accomplished its mission.

---

# §30 First actions for the fresh agent

Start here:

1. fetch current `main`;
2. confirm #527 is present;
3. create the rescue branch from current `main`;
4. inspect:

   * `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`
   * `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts`
   * `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts`
   * `apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts`
   * `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx`
   * relevant TipTap reference extensions;
5. run existing relevant tests before editing;
6. add characterization/adversarial tests;
7. evaluate the parser dependency;
8. implement the smallest AST-backed boundary that satisfies this handoff;
9. delete displaced structural parsing code;
10. produce a PR for this rescue only.

Do not begin by fixing `[foo\]]: /url`.

Begin by making it impossible for that class of bug to require another DungeonBuddy Markdown regex.
