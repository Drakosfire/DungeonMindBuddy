---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P1A
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md
  - Branch / PR: agent/play-durable-scene-beat-identity / `PLAY: persist durable Scene and Beat identity`

  ## Verification pointer
  - Base/head: `180ffeb457106ca82f7744938c6697f88a8b7527` / <implementation head>
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and the roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — durable Playable Scene and Beat identity

**Created:** 2026-08-15  
**Status:** ACTIVE — base pinned; CODE may dispatch after steward collision review  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P1A`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `180ffeb457106ca82f7744938c6697f88a8b7527`  
Pinned `origin/main` after merged PR #589 (`Merge pull request #589 from Drakosfire/documents/canonical-playable-architecture`). Do not guess a different SHA.  
**Suggested branch:** `agent/play-durable-scene-beat-identity`  
**PR title:** `PLAY: persist durable Scene and Beat identity`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## Dispatch gate — pin current authority before code

The repository connector used while designing this handoff had stale `main` visibility even after the operator reported PR #589 merged. Do **not** guess the base SHA.

Before changing implementation code:

1. fetch current `main`;
2. verify these paths exist on that exact revision:
   - `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - `Docs/Design/DESIGN-play-surface-projection.md`
   - `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
   - `Docs/Roadmaps/ROADMAP-con-ready.md` with the Playable architecture sync;
3. replace `PIN_AT_DISPATCH` in this checked-in handoff with the exact `main` SHA;
4. run the steward preflight against the pinned handoff;
5. stop if the canonical Playable design is absent or materially changed.

The base-pin edit is handoff completion, not implementation scope expansion.

### Dispatch-gate finding — 2026-08-15 (DESIGN, pre-CODE)

First fetch of `origin/main` was `cc5dc6ddba0750924a46cf13843498c124937e5f` (`Merge pull request #587`) while PR #589 was still OPEN. Re-fetched after merge:

| Check | Result |
|---|---|
| PR #589 state | **MERGED** at 2026-08-15T21:33:36Z |
| Merge commit / current `origin/main` | `180ffeb457106ca82f7744938c6697f88a8b7527` |
| Canonical Playable architecture paths | **PRESENT** on that SHA |
| `Docs/Roadmaps/ROADMAP-con-ready.md` Playable architecture sync (§1.4) | **PRESENT** |
| `PIN_AT_DISPATCH` | **replaced** with `180ffeb457106ca82f7744938c6697f88a8b7527` |

Architecture dispatch gate: **PASS**.

Steward preflight: **block** on two write-lease overlaps with open PR #510 (`calloutMarkdown.test.ts`, `markdownToTiptap.test.ts`). Steward judgment: #510 is **not** an active competing lane — it is `CONFLICTING`/`DIRTY`, last commit 2026-08-07, and cannot merge to current `main`. P1A may dispatch; if #510 is revived it must rebase onto P1A's identity tests. Do not absorb #510's graph-reference work.

Collision pre-flight (open PRs vs §4):

| Open PR | Overlap |
|---|---|
| #510 `BUILD: insert exact World Graph reference into Canvas` | Touches `calloutMarkdown.test.ts`, `markdownToTiptap.test.ts`, `markdownToTiptap.ts`, and runbook TipTap extensions. Last updated 2026-08-07; `mergeStateStatus` UNKNOWN. Rebase or coordinate if still open when P1A lands. Steward preflight reports this as a write-lease block. |
| #578 PLAY ofConks dogfood | No TipTap markdown parser/serializer overlap observed |
| #588 CUTOVER | No overlap |

---

## §1 Mission and merge-ready invariant

**Mission:** A GM-authored `runbook` workspace document can carry exact Scene and Beat identities through edit → semantic Markdown save → reload so later Run state and proposals can address the same playable elements without using mutable titles or editor-local state.

**Merge-ready invariant:**

> **For every admitted canonical P1A identity marker, one exact stable Scene/Beat ID is bound to one exact structural heading and survives Markdown ↔ TipTap round-trip and ordinary title/reorder edits unchanged; malformed, orphaned, level-mismatched, or duplicate identities fail closed without inventing, retargeting, or silently discarding identity.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Import, editor representation, serialization, committed reload, rename/reorder, and malformed/duplicate cases all ask whether the same exact identity survives or fails closed. |
| Most likely adversarial sequence | Import valid marker → copy/reorder/rename content → serialize → reload, or import duplicate/orphan marker → editor projection tries to normalize it. |
| Will §7 actually detect that failure? | Yes. Round-trip contract tests compare exact IDs before/after serialization and adversarial fixtures assert blocking diagnostics/no semantic attachment. |
| Easiest owning boundary to under-test | The Markdown admission/serialization seam. TipTap-only tests would falsely pass while committed reload loses attrs. |
| Fact that forces stop/split | If exact identity cannot round-trip through the existing semantic-Markdown authority without a second durable sidecar/store or a broad Markdown grammar rewrite, stop and re-brief. |

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Versioned Scene/Beat identity marker grammar | Yes | Yes — semantic Markdown contract | **Include** |
| Preserve exact identity as optional TipTap heading attrs | No, inseparable from round-trip | Internal editor contract | **Include** |
| Fail closed on malformed/orphan/duplicate identity | No, invariant safety | Failure contract | **Include** |
| Generate Scene/Beat IDs from a user-facing command | Yes | Operator workflow | **Exclude — successor** |
| Automatically migrate all legacy unmarked runbooks | Yes | Migration workflow | **Exclude — successor** |
| Choice / Option identity | Yes | Additional durable element contract | **Exclude — P1B** |
| Run state | Yes | New durable runtime contract | **Exclude — P2** |
| Scene/Beat Play projection | Yes | Product workflow | **Exclude — P3** |
| Generic `WorkObjectElementRef` hoist | Yes | Shared Buddy contract | **Exclude — decide after P1A evidence** |
| DungeonMind contract | Yes | Cross-repo/kernel contract | **Explicitly prohibited** |

---

## §2 Context, authority, and lane

### Parent authority

Read current versions in this order:

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
2. `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
3. `Docs/Design/DESIGN-play-surface-projection.md`
4. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` — this PR creates the repository copy from the approved design and must review it before final PASS
5. `Docs/Roadmaps/ROADMAP-con-ready.md`
6. `Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`
7. `AGENTS.md`
8. `Docs/Process/STEWARD-CYCLE.md`

Historical runbook design documents may be read as evidence only; they do not override the authority above.

### Current implementation facts this slice must preserve

The current editor/storage chain already establishes:

```text
WorkspaceDocument
→ local TipTap JSON editing state
→ semantic Markdown serialization
→ workspace document commit/revision + content digest
→ Markdown reload/re-import
```

Important current seams:

- `apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx`
  - owns admitted document identity/revision/digest and command arbitration;
- `apps/live-control-ui/src/tiptap/state/tiptapLocalState.ts`
  - `runbook` is already a valid workspace document kind;
  - local TipTap JSON is not sufficient as durable authority because committed reload is Markdown-backed;
- `apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts`
  - one parsed AST owns admission + projection;
  - raw HTML currently warns/fails closed rather than becoming arbitrary editor structure;
- `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts`
  - current heading serialization emits only Markdown heading level/text, so arbitrary heading attrs would be lost today;
- `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx`
  - shared StarterKit-based editor used across document surfaces.

The implementation must preserve existing fail-closed Markdown safety. P1A adds one exact application-owned marker form; it does **not** broadly admit HTML.

### Lane table

| Field | Required content |
|---|---|
| Base revision | Exact dispatch-time `main` SHA `180ffeb457106ca82f7744938c6697f88a8b7527` containing merged PR #589 |
| Predecessor contract | Workspace-document Markdown round-trip + canonical Playable requirement that referenced Scene/Beat elements have stable identity |
| Exact input consumed | `runbook` semantic Markdown and TipTap JSON at one workspace-document revision/digest |
| Named successor | `P1B — Playable structure index + Choice/Option identity` |
| What remains false | No Run state; no Play Scene deck; no automatic legacy stabilization; no user-facing Scene/Beat creation command; no Choice/Option stable identity; no generic shared `WorkObjectElementRef`; no kernel context |
| Explicit non-goals | New datastore, runtime schema, graph ontology, kernel/profile changes, adventure-specific bridges, broad HTML support |
| Branch / isolated checkout | `agent/play-durable-scene-beat-identity` in an isolated worktree/equivalent |
| Parallel lanes / collision hotspots | Markdown parser/serializer/editor extension registry and active roadmap are collision hotspots. Preflight open PRs before dispatch. |
| Runtime/state ownership | Browser local storage and workspace-document test fixtures only; no shared live campaign mutation required |
| State-authority sync set after merge | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` plus this handoff status/archive handling as required by process. `ROADMAP-con-ready.md` changes only if actual product sequence changed. |

### Roadmap review is a merge gate

This PR intentionally introduces `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` as a living design authority.

Before final PASS, coding agent and reviewer must answer:

```text
Did P1A evidence change ownership, sequence, hoist posture, successor boundaries,
or assumptions in the roadmap?
```

The implementation PR must then produce one exact handback disposition:

```text
ROADMAP_REVIEW — UPDATED
<evidence + changed roadmap claims>
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
<why current roadmap still follows from the implementation evidence>
```

In either case, add/update the P1A row in the roadmap review ledger with the actual PR/head and next-slice decision. A reviewer must not issue final PASS while the roadmap still says `P1A pending` or otherwise disagrees with the reviewed implementation state.

Stable architecture docs do **not** churn unless their claims changed.

---

## §3 Observable paths and adversarial sequences

### Canonical marker grammar — P1A

P1A establishes one versioned, application-owned root-level Markdown marker form:

```md
<!-- dmb-playable-element:v1 kind=scene id=scene:<opaque-id> -->
## Scene title

<!-- dmb-playable-element:v1 kind=beat id=beat:<opaque-id> -->
### Beat title
```

Contract rules:

1. Marker is one complete single-line HTML comment parsed by the existing Markdown AST as `html`.
2. Marker must occur at document/root level.
3. It must be immediately followed by the heading it identifies; blank lines or intervening blocks make it orphaned.
4. `kind=scene` binds only to an ATX level-2 heading.
5. `kind=beat` binds only to an ATX level-3 heading.
6. `id` is an opaque canonical token matching `^(scene|beat):[a-z0-9][a-z0-9._-]{0,127}$`; `kind=scene` requires the `scene:` prefix and `kind=beat` requires the `beat:` prefix. New generated IDs should use lowercase `crypto.randomUUID()` payloads (`scene:<uuid>` / `beat:<uuid>`). Consumers compare the complete exact ID and must not derive meaning from the payload.
7. IDs must be unique across all canonical playable markers in one document, regardless of kind.
8. Unmarked headings remain ordinary headings. P1A never assigns identity merely because a heading looks scene-like.
9. Ordinary raw HTML remains unsupported exactly as before.
10. A marker that starts with `dmb-playable-element:` but is malformed is a blocking semantic-Markdown diagnostic, not ordinary text that may be normalized away.

### TipTap representation

A canonical pair projects to the existing `heading` node with optional attrs:

```ts
{
  type: "heading",
  attrs: {
    level: 2 | 3,
    playableElementKind: "scene" | "beat",
    playableElementId: string,
  },
  content: ...
}
```

These attrs are an editor projection of the Markdown marker. They are **not** a second durable authority.

A small neutral extension adds optional global heading attrs to the shared editor schema. It must not render new visible HTML semantics or make non-runbook headings into Playable elements.

For already-marked semantic headings, the extension is also the editor-time integrity guard:

- a Scene semantic heading remains level 2; a Beat semantic heading remains level 3;
- if a user transaction duplicates a marked heading, the pre-existing occurrence retains its ID and the newly duplicated occurrence is re-keyed to a fresh ID of the same kind;
- hydration/import never uses that re-key path to repair malformed source — source duplicates already fail closed in Markdown admission;
- serializer validation remains the final backstop against invalid kind/id/duplicate combinations that bypass the normal editor transaction path.

### Observable paths

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Canonical marker import | Raw HTML warning / no semantic identity | Exact marker+heading becomes one heading with exact kind/ID attrs and no blocking diagnostic | Yes | Markdown admission |
| Semantic Markdown serialization | Heading attrs would be dropped | Heading with exact playable attrs serializes canonical marker immediately before heading | Yes | Markdown serializer |
| Round-trip reload | No stable semantic heading identity | import → serialize → import retains exact kind/ID and visible heading text | Yes | admission + serializer |
| Rename heading text | Identity not modeled | text may change; exact ID/kind remain unchanged | Yes | TipTap attrs + serializer |
| Reorder Scene/Beat blocks | Identity not modeled | position/order may change; IDs remain attached to same moved headings | Yes | TipTap document model |
| Unmarked heading | ordinary heading | remains ordinary; no invented identity | Yes | admission |
| Ordinary raw HTML | warning/sealed | unchanged warning/sealed behavior | Yes | admission regression |
| Malformed DMB marker | ordinary raw HTML warning today | explicit blocking playable-marker diagnostic; no semantic ID invented | Yes | admission |
| Orphan marker | n/a | blocking diagnostic; marker is not attached to a later heading | Yes | admission |
| Level/kind mismatch | n/a | blocking diagnostic; no semantic ID attachment | Yes | admission |
| Duplicate ID in source | n/a | blocking diagnostic; second occurrence does not become another semantic element with same ID | Yes | document-level admission ledger |
| Duplicate ID introduced by user copy/paste | n/a | original retains its ID; newly duplicated marked heading is re-keyed before durable serialization | Yes | editor integrity extension |
| Invalid/duplicate semantic attrs injected outside normal editor transactions | n/a | serialization fails closed; it must never emit invalid/duplicate canonical markers | Yes | serializer backstop |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| import Scene marker → rename heading → serialize → reimport | Same exact Scene ID, new title | Round-trip rename test |
| import two scenes → reorder them → serialize → reimport | IDs follow their headings; order changes only | Reorder test |
| valid marker → blank line → heading | Orphan diagnostic; no later attachment | Orphan fixture |
| `kind=scene` → `###` heading | Level mismatch diagnostic; no attachment | Mismatch fixture |
| same ID used on Scene and Beat | Duplicate diagnostic; no two semantic elements share it | Duplicate fixture |
| raw `<div>` HTML beside valid marker | Valid marker is admitted; unrelated HTML still warns/seals | Raw HTML regression |
| duplicate marked heading created through an editor transaction | original keeps ID; duplicate gets a fresh same-kind ID before export | Editor integrity test |
| invalid/duplicate attrs manufactured directly in TipTap JSON → export | Export fails closed rather than writing invalid/duplicate IDs | Serializer integrity test |
| unmarked existing runbook opened | No automatic IDs; document content remains unchanged | Backward-compat fixture |

---

## §4 Files in scope — write lease

Expected paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md` | Checked-in slice authority; first branch commit |
| Create | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Living architecture/hoist roadmap and mandatory PR review ledger |
| Modify | `Docs/Roadmaps/README.md` | Index the hoist roadmap (and CON-READY) as active roadmap authority |
| Create | `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts` | Versioned marker parser/formatter, ID validation, document-level duplicate validation; pure helpers |
| Create | `apps/live-control-ui/src/tiptap/extensions/PlayableElementHeadingAttributes.ts` | Optional heading attrs only; no Play UI or storage authority |
| Modify | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx` | Mount neutral optional heading attrs into shared editor schema |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts` | Admit exact marker+heading pairs using existing parsed AST; preserve raw HTML fail-closed behavior |
| Modify | `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts` | Canonically serialize exact playable heading markers and reject invalid/duplicate semantic attrs |
| Modify/Create tests | `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts` | Import, malformed/orphan/duplicate/backward compatibility proof |
| Modify/Create tests | `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.test.ts` or nearest existing serializer test file | Serializer, rename/reorder, duplicate JSON proof |
| Modify/Create tests | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.test.tsx` or nearest existing editor-extension test | Optional attrs survive editor hydration/update without changing ordinary heading behavior |

**Bounded discovery exception:**

```text
Directory:
  apps/live-control-ui/src/tiptap/**
Maximum additional paths:
  4
Allowed path kinds:
  existing test fixture/helper or TipTap extension registration file required to prove the same identity invariant
Decision rule:
  path must be necessary for marker admission/serialization/editor attr preservation only;
  no new surface, route, backend, workspace-document schema, or operator command
```

If the implementation requires backend/API/store changes, a workspace-document schema migration, a runbook page rewrite, or another active roadmap/tracker path beyond the explicitly named state-sync set, stop and report.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live_control_server/**` | P1A changes no backend/store contract; Markdown remains the existing durable body authority |
| `src/graph_memory/**`, `apps/live_control_server/integrations/dungeonmind_kernel/**` | No graph/kernel semantics |
| `Drakosfire/DungeonMind/**` | Cross-repo kernel work is prohibited in this slice |
| Play surface routes/panels/object sheets | P3 owns projection/UI |
| Combat state/services | P4/P2 runtime boundaries |
| `ofConks*` bridges | Demolition waits until native consumers exist; P1A does not broaden dogfood bridge work |
| Workspace-document persistent schema/API | Existing revision/digest contract is consumed unchanged |
| Existing canonical Playable architecture docs | Stable authority; edit only under stop/re-brief if implementation evidence contradicts them |
| `Docs/Roadmaps/ROADMAP-con-ready.md` | Do not churn unless P1A evidence changes CON-READY product sequencing |
| Open PR #510 `apps/live-control-ui/src/tiptap/markdown/{calloutMarkdown.test.ts,markdownToTiptap.ts,markdownToTiptap.test.ts}` | Parallel BUILD lane edits the same Markdown admission/serializer tests P1A must change. Do not silently merge across that branch; rebase after it merges or coordinate the identity tests. |

---

## §6 Implementation contract

```text
Input:
  One semantic Markdown body admitted through the existing workspace-document / TipTap pipeline.
  Optional root-level P1A markers immediately preceding Scene/Beat ATX headings.

Output:
  TipTap heading attrs carrying exact playableElementKind + playableElementId,
  and canonical semantic Markdown that reconstructs the exact same attrs.

Invariant:
  Same as §1: exact unique identity survives round-trip and mutable presentation edits;
  invalid identity structure fails closed without silent identity invention/retargeting.

Failure behavior:
  malformed marker      → blocking import diagnostic, no semantic attachment
  orphan marker         → blocking import diagnostic, no later-heading attachment
  level mismatch        → blocking import diagnostic, no semantic attachment
  duplicate source ID   → blocking import diagnostic, later duplicate not admitted semantically
  invalid TipTap attrs  → serialization/save path fails closed; no invalid canonical marker emitted
  ordinary raw HTML     → pre-existing unsupported-HTML behavior unchanged

Replay / idempotency:
  same canonical Markdown → same TipTap identity attrs
  same TipTap JSON       → byte-stable canonical marker spelling
  changed heading text   → same identity marker, changed heading text only
  reordered headings     → same IDs in new order

Trust boundary:
  Verifies:
    exact marker grammar, structural adjacency, heading level, ID safety, document uniqueness
  Records/trusts without proving:
    semantic meaning of Scene/Beat prose, whether the GM intended a heading to become playable,
    future runtime references, graph/source truth
```

### Commit point

Not applicable — P1A introduces no new backend durable write. The existing workspace-document commit remains the durability boundary.

The important proof is that the semantic Markdown body written at that existing commit point contains enough exact identity to reconstruct the editor projection later.

### A. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Canonical Scene marker + H2 | attach exact ID/kind | none | No title-derived identity |
| Canonical Beat marker + H3 | attach exact ID/kind | none | No title-derived identity |
| Unmarked H2/H3 | ordinary heading | no inference | Yes — remain untyped/unidentified |
| Duplicate exact ID | reject duplicate semantic attachment | blocking diagnostic | No first/latest winner |
| Marker + wrong heading level | reject | blocking diagnostic | No auto-level repair |
| Marker separated from heading | reject/orphan | blocking diagnostic | No search-forward attachment |
| Rename heading | retain ID | none | No regenerated ID |
| Reorder heading | retain ID | none | No positional identity |
| Delete marker in source | heading becomes ordinary on next import | explicit loss of identity because marker was explicitly removed | No hidden sidecar resurrection |

### B. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| Import canonical marker | Markdown comment + adjacent heading | exact attrs | deterministic | additive | remove marker support only by new design; existing marked docs must not be silently corrupted |
| Editor serialize | exact canonical marker emitted from attrs | exact kind/ID preserved | same JSON → same marker bytes | unmarked docs unchanged | git revert restores prior parser/serializer; marked docs would then seal as raw HTML, which must be called out before merge |
| Workspace save/reload | existing workspace revision/digest + Markdown body | identity reconstructs from committed body | existing CAS/replay unchanged | no schema migration | existing workspace rollback behavior unchanged |

### C. Marker → editor mapping

| Markdown input | TipTap projection | Serialization |
|---|---|---|
| `<!-- dmb-playable-element:v1 kind=scene id=scene:x -->` + `## Arrival` | heading level 2 + `{playableElementKind:"scene", playableElementId:"scene:x"}` | exact marker line + `## Arrival` |
| `<!-- dmb-playable-element:v1 kind=beat id=beat:y -->` + `### Gate opens` | heading level 3 + `{playableElementKind:"beat", playableElementId:"beat:y"}` | exact marker line + `### Gate opens` |
| unmarked heading | current ordinary heading | current ordinary heading |
| malformed marker | non-admitted/sealed source with blocking diagnostic | must not normalize into valid marker |

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Canonical Scene/Beat pair admits exact attrs | Markdown admission | contract | focused Vitest | exact kind/ID/level/text | marker requires second parser or broad raw HTML admission |
| Canonical attrs serialize back exactly | serializer | contract | focused Vitest | canonical marker spelling + heading | attrs dropped or marker placement unstable |
| Import → serialize → import preserves IDs | parser+serializer | round-trip | focused Vitest | deep equality of kind/ID and no blocking diagnostics | any ID regenerated from title/order |
| Rename does not change identity | serializer/editor projection | adversarial | mutate heading text in fixture → export/reimport | same ID, new text | identity derived from display text |
| Reorder does not change identity | serializer/editor projection | adversarial | reorder fixture nodes → export/reimport | same IDs attached to same headings | position participates in identity |
| Malformed/orphan/level mismatch fails closed | Markdown admission | adversarial | fixture matrix | blocking diagnostics, no semantic attachment | parser repairs or searches forward |
| Duplicate source ID fails closed | Markdown admission | integrity | duplicate fixture | explicit duplicate diagnostic | first/latest winner or two same semantic IDs |
| Duplicate JSON attrs cannot be emitted durably | serializer/editor boundary | integrity | manufactured JSON fixture | typed/explicit failure; no duplicate marker body | duplicate body can be committed |
| Ordinary raw HTML behavior unchanged | Markdown admission | regression | existing + focused test | still unsupported/warning | P1A broadly enables HTML |
| Unmarked Markdown round-trip unchanged | parser+serializer | regression | representative Build/Plan/runbook fixture | no added markers/attrs | P1A auto-tags headings |
| Shared editor accepts optional attrs without changing normal heading render/edit | Editor extension | regression | component/unit test | ordinary headings remain normal; marked attrs survive hydration/update | extension changes surface-specific behavior |
| Roadmap reconsidered before PASS | Process/state authority | review | review handback + roadmap ledger | UPDATED or NO DESIGN CHANGE; ledger names actual PR/head | roadmap remains `P1A pending` or evidence contradicts it |

### Exact verification commands

Run from repository root unless the repo's current package-manager wrapper requires an equivalent command:

```bash
cd apps/live-control-ui
pnpm test -- markdownToTiptap.test.ts
pnpm test -- calloutMarkdown.test.ts
pnpm test -- MarkdownEditorCore.test.tsx
pnpm typecheck
pnpm build
cd ../..
git diff --check
git diff --name-only <BASE_SHA>...HEAD
uv run python scripts/steward_preflight.py --handoff Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md --pr <PR_NUMBER>
```

If the repository uses `pnpm test -- <path>` differently at implementation time, use the exact current equivalent and record it; do not omit focused tests.

### Minimal dogfood proof

```text
Existing surface:
  any existing workspace-document path capable of opening/editing a `runbook` document;
  if no current mounted runbook editor consumes the shared Canvas, use the existing
  Markdown import/export fixture harness and do not invent a new surface in P1A.

Smallest realistic scenario:
  1. create/load Markdown containing two marked Scenes and at least two marked Beats;
  2. edit one Scene title and one Beat title in TipTap;
  3. reorder one marked block if the existing editor permits it without custom UI;
  4. export semantic Markdown;
  5. re-import/reload;
  6. inspect exact IDs.

Expected observation:
  IDs survive exact; visible text/order changes are independent; no hidden title-derived repair.

Evidence captured:
  test fixture/output or manual note linked in implementation handback.
```

### Baseline failure handling

If `pnpm typecheck`, `pnpm build`, or repository-required regression tests fail on the exact base, run the same command on base and head and report both. P1A may not claim a pre-existing failure as introduced or silently waive a new one.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence + provenance;
4. nano-commit/fix story;
5. base/head and actual changed paths vs §4;
6. baseline failures/waivers;
7. paths outside §4 (`none` or stop report);
8. stop conditions and resolution;
9. named successor still false: `P1B — Playable structure index + Choice/Option identity`;
10. prior finding ledger on re-review;
11. exactly one roadmap disposition:

```text
ROADMAP_REVIEW — UPDATED
...
```

or

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
...
```

12. exact roadmap ledger row added/updated for this PR/head and the evidence-based next-slice decision;
13. hoist observation, without implementing it:

```text
P1A_HOIST_OBSERVATION
- Is stable semantic element identity now demonstrably useful outside Play? yes/no/evidence insufficient
- Candidate owner if promoted: Play domain / shared Markdown Canvas / other
- Does this PR justify a generic WorkObjectElementRef successor? yes/no/not yet
- DungeonMind relevance discovered? none / name exact future audit question only
```

The reviewer may PASS with “not yet” for every hoist question. P1A is evidence collection, not a predetermined hoist.

---

## §9 Acceptance rubric

- [ ] Exact current `main` base containing the canonical Playable architecture is pinned in the checked-in handoff before implementation.
- [ ] One versioned Scene/Beat marker grammar is implemented using the existing Markdown AST admission path.
- [ ] Exact IDs survive import → TipTap → semantic Markdown → re-import.
- [ ] Rename and reorder do not change identity.
- [ ] Unmarked headings do not receive invented identity.
- [ ] Malformed, orphaned, level-mismatched, and duplicate markers fail closed.
- [ ] Duplicate semantic IDs cannot be emitted from editor JSON into durable Markdown.
- [ ] Ordinary raw HTML remains unsupported; P1A does not widen HTML admission generally.
- [ ] Existing Build/Plan/unmarked Markdown behavior remains compatible.
- [ ] No backend/store/schema migration is introduced.
- [ ] No Choice/Option, Run state, Play projection, Combat, or DungeonMind contract is introduced.
- [ ] Actual changed paths remain inside §4 / bounded discovery.
- [ ] Focused tests + typecheck + build + diff checks pass or baseline differences are truthfully recorded.
- [ ] Roadmap review disposition is explicit and `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` is current at the reviewed head.
- [ ] Hoist observation is recorded without forcing a hoist decision.

## Stop conditions

Stop and report instead of expanding if any of these appears:

- current `main` does not contain the merged PR #589 canonical Playable authority;
- stable IDs require a new backend datastore/sidecar to survive committed reload;
- preserving IDs requires broad arbitrary HTML admission rather than one exact app-owned marker grammar;
- the existing Markdown parser cannot represent the marker safely without a second structural parser;
- duplicate-ID safety requires a new user-facing migration/editor workflow rather than a bounded serializer/admission guard;
- a second independently useful element contract (Choice/Option, Run state, proposal targeting) becomes necessary to make Scene/Beat identity work;
- a required path falls outside §4 and bounded discovery;
- another active lane owns the Markdown parser/serializer/editor registry or roadmap path;
- required owning-boundary proof cannot be produced;
- P1A evidence contradicts the canonical Playable architecture rather than merely refining the roadmap.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
Roadmap claim affected:
State-authority update needed:
```
