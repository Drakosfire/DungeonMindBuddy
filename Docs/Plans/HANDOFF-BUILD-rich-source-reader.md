---
pr_body_template: |
  ## Handoff pointer
  - Conversation: CON-READY
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: `Docs/Plans/HANDOFF-BUILD-rich-source-reader.md`
  - Branch: `agent/con-ready-rich-source-reader`

  ## Verification pointer
  - Base: `0479d50d048a88b92b9d200dbf3cbbc93d295ba2`
  - Merged predecessor: PR #564 (`BUILD: create a new world from Build`)
  - Verification: see §7 and the latest numbered review handback

  The checked-in handoff, cumulative code diff, nano commits, numbered review
  handback, and independently rerun verification are the review contract. The PR
  description is transport metadata only.
---

# HANDOFF — BUILD: Rich Source Reader

**Created:** 2026-08-12.  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Conversation / workstream:** `CON-READY`  
**Flow / agent:** `BUILD`  
**Handoff direction:** `DESIGN → CODE`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-BUILD-rich-source-reader.md`  
**Implementation branch:** `agent/con-ready-rich-source-reader`  
**PR title:** `BUILD: read imported sources as rich documents`  
**Base:** `main` at `0479d50d048a88b92b9d200dbf3cbbc93d295ba2`  
**Merged predecessor:** PR #564 — `BUILD: create a new world from Build`  
**Roadmap slice:** `CR01C` — rich source reading  
**Primary user story:** `CR-U2 — Read the original source as a real document`  
**Named immediate successor:** `CR02 — Source-Backed World Ingestion`  

> **Dispatch rule:** This checked-in handoff is authoritative once present on the implementation branch. It does not need to merge to `main` before BUILD starts.
>
> **PR-body rule:** The PR description is transport metadata only. It is never merge authority and cannot substitute for the handoff, cumulative diff, nano-commit story, review handback, or verification.
>
> **Review-count rule:** The first formal review on this PR is `Review Cycle 1`; every later formal review increments exactly once regardless of PASS or CHANGES REQUESTED. Fix commits, handbacks, comments, or reruns do not increment the count until a formal review occurs.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Original source** | The exact saved Markdown bytes/text represented by `WorkspaceDocumentSnapshot.markdown`; this is richer than the editable TipTap projection and may contain constructs the editor intentionally cannot round-trip. |
| **Reader** | A read-only presentation of the exact saved source Markdown. It may support more display constructs than the editor because it never writes source. |
| **Edit projection** | The existing Markdown → TipTap authoring projection governed by source-fidelity/admission rules. It may be intentionally lossy and sealed. |
| **Saved source** | The server snapshot currently admitted by the workspace-document session. It does not include unsaved local editor changes. |
| **Explicit read/edit mode** | Ephemeral Build UI state choosing rich reading versus existing authoring; it is not persisted and does not change document identity, revision, or authority. |
| **Unresolved media** | An image/media reference that cannot be safely resolved by the current reader. It must remain visible as source information rather than silently disappearing or creating arbitrary filesystem authority. |
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved. |
| **Invariant** | The single property every changed layer and observable path establishes or protects. |
| **Stop condition** | A discovered fact that invalidates the slice boundary or required proof and must be reported before implementation expands. |

---

# §0 Pickup and operating rules

Before implementation:

1. Read `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`.
2. Read `Docs/Roadmaps/ROADMAP-con-ready.md`.
3. Read merged predecessor handoffs:
   - `Docs/Plans/HANDOFF-CON-READY-build-lossless-markdown-import.md`
   - `Docs/Plans/HANDOFF-BUILD-create-new-world-from-build.md`
4. Read the current source-fidelity/parser authorities:
   - `Docs/Plans/HANDOFF-BUILD-unify-markdown-structural-analysis.md`
   - `apps/live-control-ui/src/tiptap/markdown/parseMarkdownAst.ts`
   - `apps/live-control-ui/src/tiptap/markdown/stripLeadingYamlFrontmatter.ts`
   - `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts`
   - `apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx`
5. Read the current Build presentation seam:
   - `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx`
   - `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx`
   - `apps/live-control-ui/src/markdownCanvas/MarkdownCanvas.tsx`
6. Reconcile against current `main` and open PRs before coding. If another active branch already owns a rich source reader for Build, stop rather than creating a parallel reader authority.

The governing product question is:

> **If I ignored every architecture name and only watched a GM use Build, can they now comfortably read the imported source they brought in?**

For this PR the answer must become:

> **Yes. The source opens as a named, comfortably formatted document, and the GM can deliberately switch to the existing editor when they want to edit it.**

Do not turn this into source-file upload, asset management, provenance navigation, graph ingestion, or a new document platform.

---

# §1 Mission and merge-ready invariant

## Primary CON-READY user story

`CR-U2 — Read the original source as a real document`

Roadmap target:

> **As a GM, I can open the material I imported and read it comfortably inside DungeonBuddy.**

Minimum useful rendering:

- headings;
- paragraphs;
- emphasis;
- lists;
- tables;
- links;
- useful spacing and typography.

## Current user-visible failure

PR #562 preserves imported Markdown exactly, and PR #564 lets the GM establish a new world before importing it. The remaining CR01 failure is presentation: Build still shows the TipTap edit projection as the document itself.

That is insufficient for source reading because the edit projection is intentionally conservative and may omit or degrade source constructs such as ordinary links, images, raw HTML, or other unsupported authoring structures. The source-fidelity system is correct to protect those constructs from lossy writes; the reader must stop asking the editor projection to double as the source document.

## Mission

> **As a GM, I can open a saved Build worldbuilding source and read its exact Markdown as a comfortable rich document, while retaining an intentional path back to the existing editor.**

## One independently useful outcome after this PR

A source imported through CR01A/CR01B opens in Build with a normal document-reading experience that is derived from the exact saved source Markdown rather than the lossy TipTap projection.

The GM can:

- read the named source comfortably;
- see common Markdown structure rendered semantically;
- follow safe links;
- see image/media references truthfully where the current product can resolve them;
- switch to `Edit` without changing the document identity or source bytes;
- switch back to `Read` without triggering a save/reimport/rewrite.

## Merge-ready invariant

> **For one accepted Build workspace-document snapshot, Read mode renders only the exact saved `snapshot.markdown` through the canonical parser-backed Markdown structure without using the TipTap edit projection as source authority; Edit mode preserves the existing MarkdownCanvas authoring/CAS/fidelity contract unchanged; switching modes never mutates document identity, revision, bytes, graph state, or source authority, and unsaved local edits are never silently presented as though they were the saved source.**

## What remains deliberately false afterward

- `.md` file upload/loading is still a separate ingress enhancement; paste import remains the proven CR-U1 path.
- Relative/local asset ingestion and managed asset serving are still not implemented merely by adding a reader.
- Object → source passage navigation (`CR-U5`) is still false.
- Source-backed extraction/review/publication (`CR02`) is still false for a newly imported one-shot source until that slice lands.
- Hermes source follow-through (`CR03`) is still false.
- Reader mode does not create or alter World Graph state.

## Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path is either exact saved-source presentation or preservation of the existing edit authority; no new persistence contract is required. |
| What adversarial sequence is most likely to falsify it? | Import source containing a table + ordinary link + image + raw HTML → TipTap projection is lossy/sealed → Build reader accidentally renders the projection instead of `snapshot.markdown`, or silently drops unsupported nodes. |
| Would §7 evidence detect that failure? | **Yes.** A Hesta/Glass-Orchard-style reader fixture must render structures the editor intentionally cannot round-trip, and shell tests must prove reader input is exact snapshot Markdown. |
| Which owning boundary is easiest to under-test? | The AST-to-React renderer: especially reference links, unsafe URL schemes, raw HTML, unresolved images, and unknown-node fallback. |
| What fact would force this slice to stop or split? | If comfortable source reading requires a new backend asset-serving/filesystem authority, a persisted read-state contract, or mutation of the source-fidelity parser/admission language. Those are separate capabilities. |

---

# §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` + `Docs/Roadmaps/ROADMAP-con-ready.md` |
| Base revision | `0479d50d048a88b92b9d200dbf3cbbc93d295ba2` |
| Predecessor contract | PR #562 exact source import + PR #564 managed new-world source placement |
| Exact input consumed | `MarkdownCanvasSessionValue.snapshot` / `WorkspaceDocumentSnapshot.markdown`, `record.title`, existing authoring status/dirty state |
| Existing parser authority | `parseMarkdownAst()` is the one CommonMark/GFM structural parser boundary; reader does not add a second Markdown grammar |
| Existing authoring authority | `MarkdownCanvasSession` + `useWorkspaceDocumentAuthoring` + existing TipTap serializer/write CAS/fidelity rules |
| Named successor | `CR02 — Source-Backed World Ingestion`; local source assets remain a bounded CR01 follow-up if dogfood proves them blocking |
| What remains false | graph extraction/review, object→source navigation, local asset ingestion/serving, Hermes source follow-through |

## 2.1 Source authority

The reader consumes the already-admitted workspace snapshot:

```text
WorkspaceDocumentSnapshot
  record.document_id
  record.title
  record.world_id / campaign_id
  loaded_revision
  content_sha256
  markdown  ← exact saved source used by reader
```

The reader must **not** reconstruct source Markdown from:

- TipTap JSON;
- `Editor.getJSON()`;
- serializer output;
- graph projection Markdown;
- source-artifact excerpts;
- a separate filesystem fetch;
- title/path inference.

`session.snapshot.markdown` is sufficient for this slice.

## 2.2 Parser authority

`apps/live-control-ui/src/tiptap/markdown/parseMarkdownAst.ts` remains the single structural parser configuration.

The reader may have a different **presentation policy** than the editor admission policy. This distinction is intentional:

```text
exact source Markdown
        ↓
canonical MDAST parser
        ├── authoring admission/projection → conservative writable TipTap subset
        └── rich reader presentation       → broader read-only semantic rendering
```

Do not modify authoring admission merely because Read mode can display a construct safely.

Examples:

- ordinary Markdown links may render in Read mode while remaining unsupported for lossless authoring;
- raw HTML may be shown as escaped literal source rather than admitted as executable DOM or writable TipTap HTML;
- image nodes may be displayed when their URL is safely resolvable, without claiming local asset upload exists.

## 2.3 Frontmatter

Leading YAML frontmatter remains source authority and must stay byte-for-byte in `snapshot.markdown`, but it should not dominate the normal reading experience.

Use the existing frontmatter split/strip boundary for presentation. The rich document body may omit leading YAML frontmatter from normal prose rendering.

Do not rewrite or delete frontmatter. Read mode is presentation only.

## 2.4 No new backend

This slice should require **no backend route or persistence change**.

The existing snapshot already provides exact source Markdown. If implementation concludes a backend route is necessary merely to render headings/tables/links, stop: the frontend is reading from the wrong authority.

## 2.5 No new local-asset authority

A relative image reference such as:

```md
![Hesta](assets/hesta.webp)
```

must not cause the reader to invent a filesystem URL, traverse from `target_relpath`, expose arbitrary `corpus/`, or add a general file-serving route.

For this slice:

- safely render image URLs the browser can already consume under the reader URL policy;
- for unresolved relative/local media, show a useful visible placeholder containing alt text/reference rather than silently dropping it;
- leave an implementation seam for a later exact document-asset resolver.

If actual local-source asset serving is needed for the dogfood acceptance material, stop and propose a bounded asset-ingress/serving successor instead of widening this PR silently.

---

# §3 Observable paths and adversarial sequences

## 3.1 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Open committed imported source | TipTap edit projection is the main document view | Rich Read mode presents exact saved Markdown as named document | Yes | Build shell + reader |
| Open source whose edit projection is sealed/lossy | Projection may omit links/images/raw HTML; Save protected | Read mode still shows source constructs from exact snapshot; Edit remains sealed/protected | Yes | Reader + existing authoring |
| Open blank newly-created draft | Empty editor is useful; reader would add no value | Default to Edit for effectively empty source | Yes | Build shell mode selection |
| Open non-empty source | Editor currently appears immediately | Default to Read unless recovered unsaved local work makes Edit the truthful initial mode | Yes | Build shell mode selection |
| Switch Read → Edit | n/a | Existing MarkdownCanvas mounts with existing authoring state; no source mutation | Yes | Build shell |
| Switch Edit → Read while clean | n/a | Exact saved snapshot appears; no mutation | Yes | Build shell |
| Switch Edit → Read while dirty | n/a | Reader clearly states it is showing the last saved source and unsaved edits are not represented | Yes | Build shell + reader banner |
| Save supported edit then Read | n/a | After normal save verification updates snapshot, Read shows new saved Markdown | Yes | Existing authoring + reader |
| Load error / wrong document kind | Existing Build admission error | Existing error UI remains authoritative; reader must not bypass admission | Yes | MarkdownCanvas session/shell |
| Conflict/reconciliation | Existing conflict UI | Existing conflict/reload/discard path remains; reader must not hide conflict | Yes | MarkdownCanvas session/shell |
| External safe link | Edit projection may not retain it | Render as a normal link with safe browser behavior | Yes | Markdown reader |
| Unsafe link scheme | Could become browser-executable if naïve renderer | Degrade to non-clickable text; never render `javascript:`/unsafe executable target | Yes | Markdown reader URL policy |
| Reference-style link | May be unsupported in editor | Resolve through parsed definition/reference nodes and render safely | Yes | Markdown reader |
| Raw HTML | Edit projection intentionally rejects/seals | Show escaped literal source; never `dangerouslySetInnerHTML` | Yes | Markdown reader |
| Image with safe already-resolvable URL | Projection may omit it | Render image with alt text and safe loading behavior | Yes | Markdown reader URL policy |
| Relative/local image with no resolver | Broken/missing | Visible unresolved-media fallback; no arbitrary filesystem authority | Yes | Markdown reader |
| Hard reload | Source reopens in editor projection | Same source reopens and rich reader reconstructs from snapshot | Yes | Existing snapshot load + shell |
| Switch Build document | Same shell/provider remounts by exact document ID | Read/edit mode resolves independently for the new exact document; no prior-document bleed | Yes | BuildSurfacePage/provider key + shell |

## 3.2 Required initial-mode rule

The mode is ephemeral UI state, not persistence.

On the first accepted snapshot for one mounted `documentId`:

```text
if recovered/local session is dirty:
    initial mode = Edit
else if saved source Markdown is empty/whitespace-only:
    initial mode = Edit
else:
    initial mode = Read
```

Do not keep re-applying the default after the GM explicitly switches modes. The provider is keyed by `documentId`, so a new source gets a fresh mode decision.

## 3.3 Read/Edit control

The GM-facing control should be simple and local to the source work object:

```text
[ Read ] [ Edit ]
```

Requirements:

- labels are exactly human-facing; do not expose “projection,” “MDAST,” “authoritative Markdown,” or CAS jargon;
- selected state is accessible (`aria-pressed`, tabs, or equivalent);
- mode choice itself does not mutate or save;
- Edit returns to the existing MarkdownCanvas, not a new editor;
- mode switch is available only after a source has been admitted; load/conflict/error UI comes first.

## 3.4 Reader document structure

Normal Read mode should present:

```text
<article>
  <header>
    <h1>record.title</h1>
    optional unobtrusive saved-source status / dirty warning
  </header>
  <rich Markdown body>
</article>
```

The normal source document is the title + rendered source, not hashes, path IDs, digests, evidence spans, or graph internals.

## 3.5 Dirty-state truthfulness

Read mode always means **saved source** for this slice.

If local editor state is dirty:

- do not serialize the live editor and pretend it is source authority;
- do not silently show stale saved content with no warning;
- show concise copy such as:

> `Reading the last saved source. Unsaved edits are not shown.`

The existing status in Surface Context may remain, but the reader itself must make the saved-vs-unsaved distinction visible because the content body is otherwise plausibly mistaken for the current edit.

## 3.6 Markdown presentation policy

The reader should use semantic React elements from the canonical parsed MDAST rather than converting back through TipTap.

At minimum own explicit rendering for:

- root;
- text;
- paragraph;
- heading 1–6;
- emphasis;
- strong;
- delete/strikethrough;
- ordered/unordered list;
- list item;
- blockquote;
- thematic break;
- hard break;
- inline code;
- fenced/indented code;
- table;
- table row;
- table cell/header semantics;
- inline link;
- reference link + definition resolution;
- inline image;
- reference image + definition resolution;
- raw HTML safe literal fallback.

Task-list state may render read-only if it is already represented by the parser. Rendering it does not make task lists authorable.

### Unknown-node rule

The reader must never silently discard a parsed node it does not explicitly understand.

Preferred fallback:

1. if node positions provide valid offsets into the parsed Markdown body, render that exact source slice as escaped literal text/code;
2. otherwise render a visible neutral fallback naming the unsupported presentation construct.

This is a reader safety rule, not an editor admission rule.

## 3.7 URL policy

Centralize URL classification in the reader; do not scatter ad-hoc `startsWith` checks across node renderers.

Required behavior:

### Links

Allowed clickable targets:

- `https:`
- `http:`
- `mailto:`
- same-document `#fragment`

Relative links may remain visibly represented but should not navigate into arbitrary app routes until an exact source-relative navigation contract exists.

Unsafe/unknown schemes (`javascript:`, `data:` for anchors, `vbscript:`, malformed URLs) render as non-clickable content.

External links should use safe rel behavior (`noopener noreferrer` where applicable).

### Images

Allowed renderable targets for this slice:

- safe browser-resolvable `https:` / `http:` image URLs;
- same-origin URLs only if they are already explicit URLs in the source and do not require filesystem inference.

Do not enable `javascript:` or arbitrary executable/data targets.

Relative/local paths with no exact resolver render an unresolved-media fallback.

## 3.8 Frontmatter presentation

Use `stripLeadingYamlFrontmatter()` (or the exact shared predecessor helper) before parsing the reader body.

Do not add a second frontmatter regex.

Frontmatter omission from the normal read view is a presentation choice only; exact `snapshot.markdown` remains source authority.

## 3.9 Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Import Hesta Markdown with table + link + image + raw HTML → open source | Reader uses exact snapshot; table/link visible, image truthfully rendered/fallback, raw HTML escaped; no TipTap-roundtrip loss | reader fixture + shell test |
| Open sealed/lossy source → Read → Edit → Read | Read remains rich exact source; Edit remains existing sealed projection; no source write/mutation occurs from mode switches | shell integration |
| Clean source C1 → edit locally → dirty → switch Read | Last saved source shown with explicit unsaved-edits warning | shell integration |
| Dirty source → Save succeeds + snapshot verification → Read | Reader reflects newly saved snapshot, warning clears when clean | shell integration / existing authoring test seam |
| Source contains `[x](javascript:alert(1))` | Label remains visible but no executable anchor is emitted | renderer test |
| Source contains reference link definition | Link resolves correctly without a handwritten raw-Markdown link parser | renderer test |
| Source contains `<script>alert(1)</script>` | Literal escaped source visible; script never executes/enters DOM as executable element | renderer test |
| Source contains `![Hesta](assets/hesta.webp)` without asset resolver | Visible unresolved image representation; no request to inferred filesystem/corpus URL | renderer test |
| Build opens plan UUID or conflicted source | Existing rejection/conflict UI appears; rich reader does not mount and cannot bypass admission | BuildSurfaceShell regression |
| Switch document A → B | B gets its own initial Read/Edit decision and exact B snapshot; no A mode/content bleed | shell/page test |

---

# §4 Files in scope — strict allowlist

Every production-path change must be listed here or added under the bounded discovery exception before review acceptance.

## Reader presentation

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.tsx` | Parse exact Markdown through canonical MDAST boundary and render semantic read-only React output with centralized URL/media/fallback policy. |
| Create | `apps/live-control-ui/src/markdownReader/MarkdownDocumentReader.test.tsx` | Own headings/prose/emphasis/lists/tables/links/reference links/images/raw HTML/unknown fallback/unsafe URL proofs. |

## Build composition

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/buildSurface/BuildSourceReader.tsx` | Bind exact Build session snapshot/title/dirty truth to the generic Markdown reader. |
| Create | `apps/live-control-ui/src/buildSurface/BuildSourceReader.test.tsx` | Prove snapshot authority, title presentation, dirty warning, frontmatter behavior. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx` | Add ephemeral Read/Edit composition while preserving graph/Agent Interaction publication and existing MarkdownCanvas error/conflict behavior. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx` | Own initial-mode, mode switching, sealed-source, dirty-warning, admission/error/conflict, exact-document regressions. |
| Modify | `apps/live-control-ui/src/buildSurface/buildSurface.css` | Source-reader typography, table overflow, code/blockquote/media fallback, Read/Edit control styling. |

## Handoff

| Action | Path | Purpose |
|---|---|---|
| Current handoff | `Docs/Plans/HANDOFF-BUILD-rich-source-reader.md` | Implementation/review authority. |

## Expected unchanged authorities

These should normally remain unchanged:

- `apps/live-control-ui/src/tiptap/markdown/parseMarkdownAst.ts`
- `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`
- `apps/live-control-ui/src/tiptap/markdown/stripLeadingYamlFrontmatter.ts`
- `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts`
- `apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx`
- `apps/live-control-ui/src/markdownCanvas/MarkdownCanvas.tsx`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/types.ts`
- all backend routes/services
- graph ingestion/projection/publication code

Changing one of these production authorities requires an explicit handoff reconciliation naming the invariant clause that cannot be satisfied otherwise.

## Bounded discovery exception

```text
Directory: apps/live-control-ui/src/buildSurface/ and apps/live-control-ui/src/markdownReader/
Maximum additional paths: 2
Allowed path kinds: adjacent owning test helper or tiny pure reader helper/type module only
Decision rule: the path must establish/prove the same §1 reader invariant and may not create a second product capability, backend contract, parser configuration, persistence format, or asset authority.
```

Unrelated cleanup is not a bounded exception.

---

# §5 Explicitly out of scope

Do not implement or claim any of the following in this PR:

- `.md` file picker/upload/import;
- PDF ingestion;
- local asset upload/copy/catalog;
- generic filesystem/corpus asset-serving endpoint;
- arbitrary source-relative path traversal;
- image OCR or multimodal interpretation;
- editable ordinary-link support;
- editable image support;
- widening TipTap admission merely because the reader can display more Markdown;
- changing source-import exact-byte semantics;
- changing `exported_markdown_authoritative` / sealed-source semantics;
- changing save/CAS/revision behavior;
- a persistent per-document Read/Edit preference;
- a new workspace-document schema field for presentation mode;
- source search;
- source anchors / source-span navigation;
- graph extraction/review/publication;
- new World Graph bootstrap;
- object → source navigation;
- Hermes source follow-through;
- Playable Layer behavior;
- statblock mechanics import;
- Combat integration;
- world/campaign creation changes;
- redesign of GraphProjectionReader;
- replacement of the canonical Markdown parser stack;
- raw HTML execution/sanitized HTML feature support.

If one of these becomes necessary to satisfy basic headings/prose/lists/tables/links reading, stop and return evidence rather than widening silently.

---

# §6 Implementation contract and matrices

## 6.1 Core contract

```text
Input:
  accepted MarkdownCanvasSession for one exact Build documentId
  session.record
  session.snapshot.markdown
  session.snapshot.loaded_revision/content_sha256
  session.dirty
  session.exportedMarkdownAuthoritative

Output:
  rich read-only document presentation OR existing MarkdownCanvas edit presentation

Invariant:
  Read renders exact saved source; Edit retains existing authoring authority; mode switch never writes.

Failure behavior:
  missing/unaccepted snapshot → existing Build/MarkdownCanvas loading/error/conflict UI
  malformed/unknown parsed presentation node → escaped visible fallback, never silent drop
  unsafe URL → non-clickable visible content
  unresolved media → visible unresolved-media fallback
  dirty local editor + Read → saved source + explicit unsaved-edits warning

Replay / idempotency:
  Read ↔ Edit repeatedly → no revision/byte/identity mutation
  hard reload same document → reader reconstructs from snapshot
  switch document → new provider/document gets independent ephemeral mode decision

Trust boundary:
  Verifies/presents: parsed exact saved Markdown structure and safe URL/media policy
  Trusts without changing: existing workspace-document admission, revision, digest, authoring fidelity, save semantics
```

## 6.2 State/fallback matrix

| Build/session state | Read behavior | Edit behavior | Allowed transition | Truth requirement |
|---|---|---|---|---|
| `unloaded` / `loading` | no reader | existing loading UI | none until admitted | no stale prior source |
| `load_error` | no reader | existing rejection UI | existing retry/navigation only | reader cannot bypass admission |
| `conflict` | no reader | existing reconciliation UI | reload/discard existing flow | do not present contested snapshot as normal source |
| clean + non-empty saved source | default Read | available explicitly | Read ↔ Edit | Read = exact saved snapshot |
| clean + empty source | available but not default | default Edit | Read ↔ Edit | no fake content |
| dirty local editor | Read shows saved snapshot + warning | current local editor | Read ↔ Edit | saved source never mislabeled as local edits |
| `preparing` / `committing` / verification pending | reader may remain on last accepted saved snapshot if already selected; controls may be conservatively disabled | existing authoring status | no new writer | do not predict commit result |
| `save_error` with dirty state | saved source + warning | existing error/dirty editor | Read ↔ Edit | no data loss/misrepresentation |
| sealed/lossy source | rich source from snapshot | existing sealed projection + reimport/save rules | Read ↔ Edit | reader support does not weaken edit guard |

## 6.3 Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Document identity | exact mounted `documentId` / accepted `session.record.document_id` | mismatch handled by existing admission | No title/path fallback |
| Source content | exact `session.snapshot.markdown` | if snapshot absent, no reader | No TipTap serialization fallback |
| Source title | exact accepted record title | no title-based lookup | display only |
| World/campaign | inherited accepted record scope | reader does not resolve identity from label | No |
| Read/Edit mode | local component state for current mounted document | reset only by new document mount/initial decision | No persistence |

## 6.4 Persistence/replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay behavior | Migration | Rollback |
|---|---|---|---|---|---|
| Enter Read mode | none | n/a | repeat is presentation-only | none | switch Edit |
| Enter Edit mode | existing local authoring state only | existing contract | repeat is presentation-only | unchanged | switch Read |
| Hard reload | existing workspace registry/source file/local authoring state | same document/snapshot contract | reader rebuilt from loaded snapshot | none | n/a |
| Save edit | existing #562/authoring write contract | existing CAS/fidelity behavior | unchanged | unchanged | existing behavior |
| Render unresolved image | none | source reference remains in exact Markdown | repeated render stable | future resolver may improve presentation | n/a |

No new persisted reader format, mode field, cache, or durable identifier may be introduced.

## 6.5 Predecessor-to-consumer mapping

**Grounding source:** `WorkspaceDocumentSnapshot` in `apps/live-control-ui/src/api/types.ts` + `MarkdownCanvasSessionValue`.

| Predecessor field/outcome | Real shape | Reader consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `snapshot.markdown` | exact string, may include unsupported authoring Markdown | rich document body | strip leading frontmatter for presentation → `parseMarkdownAst` → semantic React | BuildSourceReader/renderer tests |
| `record.title` | human title | document `<h1>` | none | BuildSourceReader test |
| `snapshot.loaded_revision` | integer | optional unobtrusive debugging/test identity only; not normal reader chrome | no user-facing revision requirement | shell regression |
| `snapshot.content_sha256` | digest | remains authority underneath; not normal reader chrome | none | diff review |
| `session.dirty` | boolean | shows saved-source warning in Read mode | boolean → human copy | shell/reader test |
| `exportedMarkdownAuthoritative` | boolean | no special reader degradation; Read still uses exact snapshot | presentation only | sealed-source test |
| `session.phase` | existing authoring lifecycle | admission/loading/conflict behavior preserved | shell branching only | shell tests |

## 6.6 Rich renderer implementation guidance

Behavior is authoritative; exact component names may vary within §4.

Recommended architecture:

```text
BuildSurfaceShell
  ├── existing context/graph/Agent Interaction publication
  ├── Read/Edit ephemeral mode
  ├── Read → BuildSourceReader
  │          └── MarkdownDocumentReader
  │                 └── stripLeadingYamlFrontmatter
  │                 └── parseMarkdownAst
  │                 └── safe React node renderer
  └── Edit → existing MarkdownCanvas
```

Do **not** implement Read by:

```text
snapshot.markdown
→ markdownToTiptapDoc
→ read-only TipTap
```

That would reproduce the exact lossiness CR-U2 is intended to escape.

## 6.7 Accessibility and document ergonomics

Required minimum:

- semantic heading levels from Markdown;
- semantic ordered/unordered lists;
- semantic `<table>` with horizontal overflow container rather than viewport breakage;
- link text remains understandable;
- images include `alt` text;
- unresolved media preserves alt/reference text;
- code blocks remain readable without horizontal page breakage;
- long source text uses a comfortable readable line length;
- reader does not depend on hover for essential content;
- Read/Edit controls expose selected state to assistive technology.

Do not over-design a new visual system. Use existing Build variables and dark-mode tokens.

---

# §7 Evidence required to merge

Every material invariant clause is merge-blocking unless explicitly waived by the operator.

## 7.1 Evidence ledger

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Reader uses exact saved Markdown, not TipTap projection | BuildSourceReader/shell | contract + adversarial | focused reader/shell tests with link/image/raw HTML fixture | constructs absent from writable projection remain visible in Read | reader derives from editor JSON/serializer |
| Headings/paragraphs/emphasis/lists/tables render semantically | MarkdownDocumentReader | component | reader test | expected DOM semantics/content | stripped/plain debug text |
| Inline links render safely | MarkdownDocumentReader | security/component | reader test | https/http/mailto/# anchors clickable; unsafe schemes not anchors | executable unsafe URL |
| Reference-style links resolve from parser definitions | MarkdownDocumentReader | parser-consumer regression | reader test | reference link target works without raw regex parser | unresolved/silent drop |
| Raw HTML never executes | MarkdownDocumentReader | security | reader test with `<script>` / `<section>` | literal escaped source visible; no executable element | HTML execution / dangerouslySetInnerHTML |
| Safe image URLs render with alt text | MarkdownDocumentReader | component | reader test | `<img>` only for allowed target | unsafe image target |
| Relative/local unresolved image fails truthfully | MarkdownDocumentReader | negative capability | reader test | visible alt/reference fallback; no inferred filesystem URL | arbitrary corpus/file request |
| Unknown parsed node cannot disappear silently | MarkdownDocumentReader | adversarial | owning fallback test | exact source slice or visible unsupported fallback | silent omission |
| Leading YAML frontmatter does not pollute normal document view | BuildSourceReader/reader | regression | reader test | frontmatter preserved in input but omitted from rendered prose | second regex/rewrite/source mutation |
| Non-empty clean source defaults to Read | BuildSurfaceShell | workflow/component | shell test | reader visible, editor absent initially | editor remains only normal view |
| Blank source defaults to Edit | BuildSurfaceShell | regression | shell test | existing editor visible | blank reader blocks authoring |
| Recovered dirty source defaults to Edit | BuildSurfaceShell | state regression | shell test/local-state harness | unsaved work opens in editor | dirty work hidden behind stale read view |
| Explicit Read ↔ Edit never writes | BuildSurfaceShell | adversarial | shell test mocks prepare/commit | zero write API calls from mode switching | mode switch triggers save/reimport |
| Dirty Edit → Read is truthful | BuildSourceReader/shell | state/adversarial | shell test | saved snapshot + visible unsaved-edits warning | stale source presented as current edits |
| Sealed/lossy source reader does not weaken Save guard | shell + existing fidelity boundary | regression | include existing markdown-fidelity tests + shell sealed-source test | exact rich Read + existing sealed Edit semantics | authoring admission widened/save allowed incorrectly |
| Load error/wrong kind/conflict remain existing UI | BuildSurfaceShell | regression | existing + focused shell tests | reader does not mount/bypass | rejected source displayed as normal reader |
| Document switch has no mode/content bleed | BuildSurfaceShell/Page | navigation regression | shell/page test | B uses B snapshot + fresh initial-mode rule | A reader state/content leaks |
| Agent Interaction/source envelope remains exact accepted document | BuildSurfaceShell | regression | existing shell tests | documentId/path/hash publication unchanged | reader mode changes agent authority |
| Graph-context behavior remains unchanged | BuildSurfaceShell | regression | existing shell tests | graph pointer still gated by accepted document scope | reader bypasses or breaks graph context |
| Frontend type/build integration | UI package | compile/build | `pnpm exec tsc -b && pnpm build` | success | build/type failure |
| Scope hygiene | git | scope | `git diff --name-only 0479d50d...HEAD` | only §4/bounded exception | unrelated production path |
| Diff hygiene | git | hygiene | `git diff --check` | clean | whitespace/merge debris |

## 7.2 Required focused frontend run

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/markdownReader/MarkdownDocumentReader.test.tsx \
  src/buildSurface/BuildSourceReader.test.tsx \
  src/buildSurface/BuildSurfaceShell.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx \
  src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx \
  src/tiptap/markdown/markdownToTiptap.test.ts \
  src/tiptap/markdown/parseMarkdownAst.test.ts
pnpm exec tsc -b
pnpm build
```

If exact current repository test filenames differ, reconcile the handoff before review rather than silently dropping the owning proof.

## 7.3 No backend suite required by default

This PR is intended to be frontend-only and consume an unchanged snapshot API.

If no backend production path changes, a backend suite is not a merge gate for this slice beyond any repository-wide automation that happens to run.

If implementation changes a backend path, stop and reconcile scope/evidence first.

## 7.4 Minimal live / dogfood proof

**Existing surface:** Build.  
**Material:** use a real imported source already created through #562/#564, preferably the Hesta sample or Glass Orchard material, not a renderer-specific toy document.

The source should contain at least:

- multiple headings;
- paragraphs with emphasis;
- a list;
- a table;
- an ordinary Markdown link;
- an image reference (resolvable or intentionally unresolved);
- at least one construct known to be unsupported by the writable TipTap projection, such as raw HTML.

Expected operator journey:

1. Open Build and select/import the real source.
2. Confirm the source opens in **Read** mode when clean/non-empty.
3. Confirm the document title is prominent and the source reads like a document rather than an editor/debug panel.
4. Confirm headings, prose, emphasis, list, table, and ordinary link are readable.
5. Confirm any safely resolvable image is shown; if the source uses an unresolved relative image, confirm the fallback is useful and does not break the page.
6. Confirm raw HTML/source oddities do not execute and do not silently vanish.
7. Switch to **Edit** and confirm the existing editor appears with the same exact document identity.
8. If the source is sealed/lossy, confirm the existing Save/reimport guard is still truthful.
9. For a supported editable source, make a small local edit without saving, switch to **Read**, and confirm the saved-source warning appears and the reader does not pretend the unsaved change is saved.
10. Return to Edit, save normally, then Read; confirm the newly saved content appears after existing verification completes.
11. Hard reload; confirm the same source reopens and Read mode is reconstructed from the saved snapshot.
12. Confirm no graph extraction/publication, world mutation, new source identity, or asset-serving side effect occurred merely by reading.

Capture:

- document ID/title/world scope;
- concise before/after screenshots if practical (old edit projection vs rich reader is especially useful);
- confirmation Read used same exact source document;
- link/table/image/raw-HTML observations;
- dirty warning observation;
- hard-reload observation;
- any friction as backlog notes rather than silent scope expansion.

## 7.5 Baseline failure protocol

For any required command already failing on base `0479d50d048a88b92b9d200dbf3cbbc93d295ba2`:

1. run/cite the same command or exact failing subset on base and HEAD;
2. state whether HEAD adds/removes/preserves failures;
3. do not call a non-green gate green;
4. request an explicit fresh operator waiver if the failing row remains an acceptance gate;
5. waivers from PR #562/#564 do not automatically transfer.

## 7.6 Changed-path proof

Before handback:

```bash
git diff --check
git diff --name-only 0479d50d048a88b92b9d200dbf3cbbc93d295ba2...HEAD
git diff --stat 0479d50d048a88b92b9d200dbf3cbbc93d295ba2...HEAD -- \
  apps/live-control-ui/src/markdownReader/ \
  apps/live-control-ui/src/buildSurface/BuildSourceReader.tsx \
  apps/live-control-ui/src/buildSurface/BuildSourceReader.test.tsx \
  apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx \
  apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx \
  apps/live-control-ui/src/buildSurface/buildSurface.css \
  Docs/Plans/HANDOFF-BUILD-rich-source-reader.md
```

---

# §8 Required review handback

Every formal review begins with exactly one:

```text
Review Cycle N — PASS
```

or

```text
Review Cycle N — CHANGES REQUESTED
```

The handback must include:

1. Exact PR URL, branch, and head SHA.
2. Base `0479d50d048a88b92b9d200dbf3cbbc93d295ba2` or a deliberately reconciled replacement base.
3. §1 Mission and merge-ready invariant copied exactly.
4. Finding ledger from all prior cycles with open/closed status.
5. §7 evidence ledger with produced result and provenance.
6. Nano-commit list and the discrete implementation/proof story for each commit.
7. Actual changed paths + focused diff stat.
8. Every required test/build/manual scenario and exact result.
9. Provenance of each result: author-local, independently rerun local, CI, or manual/dogfood.
10. Baseline failures and base/head comparison.
11. Operator waivers; `none` when none exist.
12. Paths outside §4; `none` or explicit bounded-exception reconciliation/stop report.
13. Stop conditions encountered and resolution; `none` when none exist.
14. Confirmation that Read mode consumes exact `snapshot.markdown`, not TipTap/serializer output.
15. Confirmation existing source-import exact-byte authority was not weakened.
16. Confirmation existing sealed-source/Save/CAS/revision authority was not weakened.
17. Confirmation reader support did not silently become authoring support.
18. Confirmation no backend/asset/filesystem/graph authority was added.
19. Successors still false: local asset ingress/serving, CR02 extraction/review/object→source, CR03 Hermes source follow-through.

A generic PR description is neither required nor sufficient.

---

# §9 Acceptance rubric

The reviewer accepts only when every applicable bullet is true and each behavioral claim names its §7 proof.

- [ ] Exactly one independently useful capability was delivered: imported Build source can be read as a rich document.
- [ ] Read mode renders exact `WorkspaceDocumentSnapshot.markdown` rather than TipTap projection/serialization.
- [ ] Non-empty clean imported source defaults to Read.
- [ ] Blank source defaults to Edit.
- [ ] Recovered dirty source defaults to Edit so unsaved work is not hidden.
- [ ] GM can intentionally switch Read ↔ Edit without mutation.
- [ ] Dirty Edit → Read clearly says saved source is being shown and unsaved edits are absent.
- [ ] Headings, paragraphs, emphasis, lists, tables, and links render usefully.
- [ ] Reference-style links resolve through parser structure, not a second handwritten Markdown parser.
- [ ] Unsafe URL schemes cannot become executable links.
- [ ] Raw HTML cannot execute and is not silently discarded.
- [ ] Safe resolvable images show alt-aware media; unresolved local media remains visible without arbitrary filesystem access.
- [ ] Unknown parsed constructs cannot vanish silently.
- [ ] Leading YAML frontmatter remains exact source authority while staying out of normal prose presentation.
- [ ] Existing TipTap authoring language is not widened merely because the reader supports more display constructs.
- [ ] Existing sealed/lossy source behavior remains intact.
- [ ] Existing Save/CAS/revision/verification semantics remain intact.
- [ ] Existing load-error/wrong-kind/conflict behavior remains intact.
- [ ] Existing Agent Interaction publication remains bound to the exact admitted document.
- [ ] Existing Build graph-context gating remains intact.
- [ ] No backend route/schema was added.
- [ ] No local asset-ingress/serving authority was smuggled in.
- [ ] No graph extraction/publication occurs from reading.
- [ ] Hard reload reconstructs the reader from the same durable source.
- [ ] Every required proof has a produced result/provenance or explicit operator waiver.
- [ ] No production path outside §4/bounded exception changed.
- [ ] Named successors remain unimplemented and unclaimed.

---

# Stop conditions

Stop and report rather than expanding if implementation discovers any of the following.

## Source-authority stops

- The reader cannot obtain exact saved Markdown from the admitted `WorkspaceDocumentSnapshot` and would need a parallel file fetch.
- Correct reading requires serializing the TipTap editor back to Markdown and treating that as the source.
- Existing snapshot Markdown is normalized/lossy in a way that contradicts #562's source-import contract.
- The reader would need to weaken `exported_markdown_authoritative`, admission, or Save guards to display source constructs.

## Parser/presentation stops

- `parseMarkdownAst()` cannot represent a CR-U2 minimum construct already present in real imported Markdown without changing parser configuration in a way that would alter authoring admission behavior.
- Rendering reference links/images correctly requires a second raw-Markdown recognizer rather than consuming parsed definitions/references.
- A parsed construct cannot be rendered or visibly fallen back without silently dropping source information.

## Asset/security stops

- Real dogfood requires local relative images to load and there is no existing exact document-asset resolver.
- Supporting local images would require serving arbitrary `corpus/`/filesystem paths or trusting client-supplied paths.
- A proposed renderer requires executable raw HTML or unsafe URL schemes.

## Scope stops

- Correctness requires a new backend route/schema.
- Correctness requires a persisted Read/Edit mode field.
- Correctness requires `.md` upload, extraction, provenance anchors, source search, Hermes, graph publication, or campaign/world changes.
- A production path outside §4 is necessary and is not clearly the same CR-U2 invariant.

## Evidence stops

- Reader correctness cannot be proved with actual source Markdown containing constructs the editor projection loses.
- Dogfood only works with a toy Markdown fixture specifically written for the renderer.
- The reader hides unsaved edits without a truthful warning.
- Existing Build authority/Agent Interaction/graph-context tests regress.
- A required base/head failure needs operator disposition.

Use this stop-report shape:

```text
CON-READY / BUILD stop report
Head SHA:
Observed repository fact:
Assumption contradicted:
Primary CR-U story affected:
Why the current slice cannot proceed safely:
Smallest decision needed from operator/steward:
Paths/evidence inspected:
What remains untouched:
```

---

# Successor notes

After this PR merges, re-anchor rather than blindly dispatching.

The canonical next capability is likely:

## CR02 — Source-Backed World Ingestion (`CR-U3`–`CR-U5`)

GM-visible target:

> **Run bounded extraction on the imported one-shot source, get a useful semantic index of important people/threats/places/organizations/relationships, cheaply correct meaningful mistakes, and navigate a world object back into this rich source reader.**

The rich reader should become the eventual destination for `Read source`; this PR does **not** implement the provenance route or source-span landing behavior itself.

A separate CR01 follow-up may be justified before CR02 only if real material shows one of these is blocking:

- `.md` file loading;
- exact local image/asset ingestion + bounded serving.

Do not preemptively build either without dogfood signal.

---

# Handoff footer

```text
CON-READY Steward Re-anchor
Current main SHA: 0479d50d048a88b92b9d200dbf3cbbc93d295ba2
Merged source-ingress predecessors: PR #562 + PR #564
Intervening main merge: PR #563 (relationship semantic closure; unrelated to CR01 reader authority)
Selected CR-U story: CR-U2
GM-visible capability targeted: Open imported Build source and read exact saved Markdown as a rich real document
What is already true: exact pasted Markdown source persistence; existing/new world placement; reopen/reload; conservative editable TipTap projection; sealed-source safety
What remains false: local asset ingress/serving, CR02 extraction/review/object→source, CR03 Hermes source follow-through
Authority boundary: workspace snapshot owns saved source; canonical MDAST parser owns structure; reader owns presentation; MarkdownCanvas/TipTap retains authoring authority
Implementation branch: agent/con-ready-rich-source-reader
```
