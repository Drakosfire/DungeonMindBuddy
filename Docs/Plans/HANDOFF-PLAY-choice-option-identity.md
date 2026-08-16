---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P1C
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-choice-option-identity.md
  - Branch / PR: agent/play-choice-option-identity / `PLAY: persist durable Choice and Option identity`

  ## Verification pointer
  - Base/head: `f9759b4967356afdd2858092ad64f0c03ca840c6` / <implementation head>
  - Predecessor: merged PR #592 / main `86a405ce7b8085515ef2804965ca4b3aad226c22` at design time
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — durable Playable Choice / Option identity

**Created:** 2026-08-15  
**Status:** ACTIVE — base pinned after PR #593 state-authority sync; CODE may dispatch  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-choice-option-identity.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P1C`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #592 at main `86a405ce7b8085515ef2804965ca4b3aad226c22`  
**Implementation base:** `f9759b4967356afdd2858092ad64f0c03ca840c6`  
**Suggested branch:** `agent/play-choice-option-identity`  
**PR title:** `PLAY: persist durable Choice and Option identity`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## Dispatch gate — close P1B state first

PR #592 is merged. At design time, `main` is exactly:

```text
86a405ce7b8085515ef2804965ca4b3aad226c22
```

The next dependent CODE lane must not dispatch until the post-merge mutable-state sync is on `main`.

That sync must, at minimum:

1. update `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` so:
   - integration tip names merged PR #592 / `86a405ce7b8085515ef2804965ca4b3aad226c22`;
   - P1B is recorded as merged;
   - P1C is the current next slice;
   - this handoff is the next handoff;
   - P2 remains the named successor after P1C;
   - the hoist posture remains `WorkObjectElementRef` **not yet justified**;
2. mark `Docs/Plans/HANDOFF-PLAY-playable-structure-index.md` complete/merged according to repository handoff-status convention;
3. check in this P1C handoff;
4. preserve the P1B review conclusion: the Scene/Beat structure index remains Play-owned and P1B did not prove a second independent consumer of generic element addressing.

After that state-sync transaction lands:

1. fetch current `main`;
2. replace `PIN_AT_DISPATCH_AFTER_STATE_SYNC` in this handoff with that exact SHA;
3. verify merged P1A/P1B production paths still exist and the roadmap still names P1C as next;
4. run:

   ```bash
   uv run python scripts/steward_preflight.py \
     --handoff Docs/Plans/HANDOFF-PLAY-choice-option-identity.md
   ```

5. stop if another active lane owns any §4 path or if `main` materially changed the P1A identity / P1B structure-index contracts.

The pin-at-dispatch edit is handoff completion, not capability expansion.

### Dispatch-gate finding — 2026-08-15 (DESIGN, pre-CODE)

| Check | Result |
|---|---|
| PR #592 state | **MERGED** at 2026-08-16T00:45:18Z as `86a405ce7b8085515ef2804965ca4b3aad226c22` |
| Post-#592 state-authority sync | **MERGED** PR #593 at 2026-08-16T00:54:07Z |
| Current `origin/main` | `f9759b4967356afdd2858092ad64f0c03ca840c6` |
| P1A identity module | **PRESENT** |
| P1B structure index | **PRESENT** |
| Roadmap current next slice | **P1C — Choice / Option identity and minimal authored representation** |
| Hoist posture | Scene/Beat identity and derived index remain Play-owned; no `WorkObjectElementRef` yet |
| `PIN_AT_DISPATCH_AFTER_STATE_SYNC` | **replaced** with `f9759b4967356afdd2858092ad64f0c03ca840c6` |

Architecture / state-sync dispatch gate: **PASS**.

---

## §1 Mission and merge-ready invariant

**Mission:** A Playable Runbook can carry exact durable Choice and Option identities, and a consumer can deterministically resolve `Choice → Options` and `Scene → Choice` membership, so P2 Runtime can later persist `choiceId → optionId` selections without using mutable labels, title text, or positional guesses as identity.

**Merge-ready invariant:**

> **For one exact workspace-document projection, every canonical root-level Choice/Option marker survives Markdown ↔ TipTap ↔ Markdown with the same exact ID and participates in one deterministic Playable structure index under exactly one marked Scene/Choice; invalid kind/level, duplicate, nested, or orphan Choice/Option structure fails closed, existing Scene/Beat marker bytes and structural semantics remain unchanged, and no Runtime selection state or second durable authority is created.**

### Why this is one P1C capability

P1C introduces one new durable semantic capability: **an authored branch choice can be addressed exactly later**.

That requires two inseparable properties:

1. the authored Choice and each Option have durable IDs;
2. the derived Playable structure can prove which Options belong to which Choice and which Scene owns that Choice.

A durable ID with no deterministic membership would be insufficient for P2 to validate `choiceId → optionId`. A membership index based on labels or headings without durable IDs would violate the Playable architecture. These are therefore two clauses of one capability, not two independent products.

P1C does **not** make or persist a runtime selection.

### Why Decision/Consequence is not Choice

The existing TipTap `decisionConsequence` node is a two-pane prep construct:

```text
Decision pane
Consequence pane
```

It has exactly one of each pane and serializes as `[!DECISION-CONSEQUENCE]` with `### Decision` / `### Consequence` delimiters.

Canonical Playable Choice semantics are different:

```text
Choice
  stable choiceId
  prompt / meaning
  options[]
    stable optionId
    label
```

A Choice may have multiple options and Runtime later records one exact `choiceId → optionId`. P1C must **not** overload, reinterpret, or migrate the existing Decision/Consequence node into Choice.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path asks whether authored Choice/Option identity and membership survive exactly or the whole derived structure blocks. |
| Most likely adversarial sequence | Choice with two Options → copy/paste the Choice/Options → duplicate IDs re-key in editor → move one Option after a Beat → serialize/index. The moved Option must retain its ID but become structurally orphaned, not silently remain attached to the old Choice. |
| Will §7 actually detect that failure? | Yes. §7 requires real Markdown round-trip, clipboard HTML re-key, structure-index boundary movement, and workspace Save/reload proof. |
| Easiest owning boundary to under-test | The generic P1A Markdown/editor seams. Merely extending the enum can compile while serializer, paste, nesting, or durable Save behavior is wrong for the new kinds. Focused integration tests must traverse those unchanged owners. |
| What fact forces stop/split? | If Choice/Option requires a custom non-heading TipTap node, new Save policy, new backend/store, user-facing authoring workflow, transition/consequence schema, or production special-casing in the Markdown parser/serializer beyond the existing generic playable-element mechanism, stop and re-brief. |

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Add `choice` / `option` to the existing durable playable-element identity family | Yes | Yes — additive semantic kind contract | **Include** |
| Canonical Choice/Option heading-level mapping and exact ID grammar | No, part of identity contract | Same contract | **Include** |
| Extend P1B structure index with Scene→Choice and Choice→Option membership | No, required consumer semantics for exact selection validation | Caller-facing derived type, non-durable | **Include** |
| Preserve copy/paste duplicate re-key for Choice/Option | No, integrity clause | Existing editor contract | **Include as proof** |
| Preserve workspace Markdown Save/reload | No, durability clause | Existing persistence contract | **Include as proof** |
| User-facing “Add Choice” / “Add Option” command | Yes | New operator workflow | **Exclude** |
| Transition targets / consequence refs on Options | Yes | New authored semantic contract | **Exclude** |
| Runtime `choiceId → optionId` selection persistence | Yes | New durable runtime contract | **Exclude — P2** |
| General branching/workflow graph | Yes | New product/ontology contract | **Explicitly excluded** |
| Reuse/replace Decision/Consequence as Choice | Yes | Semantically different editor contract | **Explicitly excluded** |
| Generic `WorkObjectElementRef` | Yes | Shared Buddy contract | **Exclude — hoist review only** |
| DungeonMind contract | Yes | Cross-repo kernel contract | **Explicitly prohibited** |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
   - §4.2 stable semantic identity;
   - §5 Scene/Beat ownership;
   - §6 generic Choice / Option semantics;
2. `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
   - §4.1 Scene authored choices/transitions;
   - §4.4 Choice authoring;
3. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
4. merged P1A handoff + implementation:
   - `Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md`
   - `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`
   - `apps/live-control-ui/src/tiptap/extensions/PlayableElementHeadingAttributes.ts`
5. merged P1B handoff + implementation:
   - `Docs/Plans/HANDOFF-PLAY-playable-structure-index.md`
   - `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts`
6. existing Decision/Consequence implementation as **contrast**, not substrate:
   - `apps/live-control-ui/src/tiptap/extensions/DecisionConsequenceNode.ts`
7. `AGENTS.md`
8. `Docs/Process/STEWARD-CYCLE.md`

Historical dogfood branch enums / `ofConks*` structures are evidence only and do not override these authorities.

### Predecessor contracts consumed unchanged

P1A established one application-owned root-level identity marker family:

```md
<!-- dmb-playable-element:v1 kind=scene id=scene:<opaque-id> -->
## Scene title

<!-- dmb-playable-element:v1 kind=beat id=beat:<opaque-id> -->
### Beat title
```

with:

- exact ID validation;
- root-only placement;
- heading-level integrity;
- duplicate failure;
- clipboard duplicate re-key;
- serializer fail-closed behavior;
- workspace Save/reload durability.

P1B established one read-only structure index:

```text
marked Scene starts current Scene
marked Beat belongs to nearest preceding marked Scene
unmarked headings are structurally invisible
invalid / duplicate / nested identity blocks
Beat before any Scene blocks
```

P1C extends these contracts; it does not replace or fork them.

### Lane table

| Field | Required content |
|---|---|
| Base revision | Exact dispatch-time `main` SHA `f9759b4967356afdd2858092ad64f0c03ca840c6` containing merged PR #593 |
| Design anchor | `86a405ce7b8085515ef2804965ca4b3aad226c22`, merge of PR #592 |
| Predecessor contract | P1A durable root-level playable identity + P1B deterministic Scene/Beat structure index |
| Exact input consumed | One TipTap JSON `doc` / semantic Markdown body using the existing workspace-document revision/digest boundary |
| Output | Exact durable Choice/Option identity plus extended read-only `PlayableStructureIndexResult` |
| Named successor | `P2 — separate Run runtime`, beginning with revision-bound current/resolved/selection state |
| What remains false | No runtime selection; no current Scene/Beat; no resolved Beat state; no Choice UI; no option transitions/consequences; no Play projection; no generic work-object ref |
| Explicit non-goals | New datastore/API, new workspace schema, custom branch graph, Decision/Consequence migration, legacy auto-tagging, Play UI, agent proposal changes, kernel/profile changes |
| Branch / isolated checkout | `agent/play-choice-option-identity` in isolated worktree/equivalent |
| Parallel lanes / collision hotspots | `playableElementIdentity.ts`, `playableStructureIndex.ts`, active roadmap. Stale PR #510 touches shared Markdown tests/implementation; P1C intentionally does not lease those production paths. PR #578 dogfood remains mining evidence only. |
| Runtime/state ownership | None. P1C creates no runtime state; test state is in-memory / existing workspace test fixtures only. |
| State-authority sync set after merge | This handoff status + living Playable hoist roadmap. `ROADMAP-con-ready.md` changes only if actual CON-READY sequencing changes. |

### Roadmap review is a merge gate

Before final PASS, coding agent and reviewer must answer:

```text
Did P1C evidence change ownership, sequence, hoist posture, successor boundaries,
or assumptions in ROADMAP-playable-hoist-dungeonmind-kernel.md?
```

The implementation PR must record exactly one:

```text
ROADMAP_REVIEW — UPDATED
<evidence + changed roadmap claims>
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
<why P1C evidence still supports the roadmap>
```

and update the roadmap ledger using the implementation/evidence head, not the later bookkeeping SHA.

---

## §3 Observable paths and adversarial sequences

### Canonical P1C authored representation

P1C **additively extends** the existing `dmb-playable-element:v1` kind registry. It does not create a second marker prefix or a second identity store.

Canonical example:

```md
<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->
## The Gate

<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->
### Arrival

<!-- dmb-playable-element:v1 kind=choice id=choice:route -->
### Which route do they take?

<!-- dmb-playable-element:v1 kind=option id=option:fire -->
#### Burn through the growth

<!-- dmb-playable-element:v1 kind=option id=option:wait -->
#### Wait and watch
```

The title text is presentation, not identity. `Choice:` / `Option:` prefixes are **not** required syntax.

### Exact kind / ID / heading contract

Canonical kinds after P1C:

```text
scene
beat
choice
option
```

Canonical ID grammar:

```regex
^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$
```

Heading-level mapping:

| kind | heading level | structural role |
|---|---:|---|
| `scene` | H2 | starts current Scene |
| `beat` | H3 | Scene-level Beat; closes any active Choice option run |
| `choice` | H3 | Scene-level Choice sibling of Beat |
| `option` | H4 | child of nearest active marked Choice |

All markers remain:

- one complete single-line HTML comment;
- document/root level only;
- immediately followed by the heading they identify;
- unique by exact complete ID within one document;
- exact-kind prefix matched (`choice:` for Choice, `option:` for Option).

P1C does not change existing Scene/Beat marker spelling or ID semantics.

### Why `v1` remains the marker spelling

P1C changes the **allowed kind registry**, not the marker envelope:

```text
same dmb-playable-element prefix
same version token
same root-level placement
same kind/id attributes
same opaque ID rules
same adjacency rule
same serializer/admission/failure machinery
```

Existing Scene/Beat Markdown must remain byte-stable. P1C must not rewrite P1A documents to a new marker version merely because new kinds exist.

If implementation evidence shows the current marker version cannot be additively extended without ambiguity or unsafe compatibility behavior, **stop and re-brief** rather than silently inventing a v2 migration inside this PR.

### Structural interpretation

The extended structure index uses only canonical marked identities in root document order.

State machine:

```text
currentScene = null
currentChoice = null

Scene:
  require valid Scene identity
  currentScene = sceneId
  currentChoice = null

Beat:
  require currentScene
  attach Beat to currentScene
  currentChoice = null

Choice:
  require currentScene
  attach Choice to currentScene
  currentChoice = choiceId

Option:
  require currentScene + currentChoice
  attach Option to currentChoice and currentScene
```

Consequences:

1. A Choice before any marked Scene blocks the entire index.
2. An Option before any active marked Choice blocks the entire index.
3. A new Scene closes the prior Choice option run.
4. A Beat closes the prior Choice option run.
5. A new Choice closes the prior Choice option run and starts another.
6. Unmarked headings/content do **not** start/end Scene or Choice structure.
7. A Choice with zero Options is structurally valid. The canonical architecture does not specify a minimum option count; P1C must not invent one.
8. Option prose/transition/consequence payload is not modeled in P1C. The H4 text is the current table-facing option label only.

### Extended P1B structure index

P1C extends the existing read-only index rather than creating a parallel Choice index.

Target shape:

```ts
type PlayableStructureScene = {
  sceneId: string;
  order: number;           // Scene ordinal in document
  beatOrder: string[];
  choiceOrder: string[];
};

type PlayableStructureChoice = {
  choiceId: string;
  sceneId: string;
  order: number;           // Choice ordinal in document
  optionOrder: string[];
};

type PlayableStructureElement =
  | { kind: "scene"; id: string; order: number }
  | { kind: "beat"; id: string; order: number; sceneId: string }
  | { kind: "choice"; id: string; order: number; sceneId: string }
  | { kind: "option"; id: string; order: number; sceneId: string; choiceId: string };

type PlayableStructureIndex = {
  sceneOrder: string[];
  scenes: PlayableStructureScene[];
  choices: PlayableStructureChoice[];
  elements: PlayableStructureElement[];
};
```

`elements.order` remains the global ordinal among **marked semantic elements**, exactly as P1B established for Scene/Beat. It is not a raw TipTap child index.

For existing Scene/Beat-only documents:

- Scene/Beat identity, order, and parent semantics remain unchanged;
- `choices` is empty;
- each Scene has empty `choiceOrder`;
- serialized Markdown remains byte-equivalent to P1A behavior.

### Observable paths

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Canonical Choice import | `kind=choice` is not currently a canonical playable kind | exact Choice H3 attaches `choice:*` attrs | Yes | P1A identity admission seam |
| Canonical Option import | `kind=option` is not currently canonical | exact Option H4 attaches `option:*` attrs | Yes | P1A identity admission seam |
| Serialize Choice/Option | unsupported as playable identity today | emit exact existing marker envelope + H3/H4 | Yes | P1A serializer seam |
| Save/reload | cannot preserve Choice/Option semantic identity today | exact IDs reconstruct after committed workspace reload | Yes | existing workspace Save boundary |
| Choice rename | n/a | prompt/title changes; `choiceId` unchanged | Yes | heading attrs + serializer |
| Option rename | n/a | label changes; `optionId` unchanged | Yes | heading attrs + serializer |
| Choice parent | n/a | nearest preceding marked Scene | Yes | structure index |
| Option parent | n/a | active marked Choice in same marked Scene | Yes | structure index |
| Beat after Choice | n/a | Beat remains Scene child and closes active Choice run | Yes | structure index |
| Unmarked H3/H4 | ordinary heading | remains structurally invisible; cannot create/end Choice | Yes | structure index |
| Clipboard duplication | only Scene/Beat proven | duplicated Choice/Option IDs re-key; originals retain IDs | Yes | editor integrity plugin |
| Nested Choice/Option attrs | unknown new kinds | block serializer/save; no nested marker grammar | Yes | serialization safety |
| Existing Scene/Beat-only doc | P1A/P1B behavior | same IDs/parents/Markdown; additive empty Choice fields only | Yes | regression |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| import Choice + two Options → rename all headings → serialize → reload | exact IDs unchanged; new text only | round-trip test |
| Choice A/options → reorder Options | IDs unchanged; `optionOrder` changes | structure test |
| Choice A/Option X → move Option X after Choice B | Option X retains ID; parent changes to Choice B | structure test |
| Scene A/Choice X → move Choice X after Scene B | Choice X retains ID; parent changes to Scene B | structure test |
| Choice → Option → Beat → Option | final Option blocks as orphan; it is not attached through the Beat boundary | adversarial structure test |
| Choice before any Scene | entire index blocked; no synthetic Scene | orphan Choice test |
| Option before any Choice | entire index blocked; no synthetic/default Choice | orphan Option test |
| unmarked H3/H4 between Choice and Option | unmarked headings ignored; Option remains under active marked Choice | regression test |
| duplicate Choice/Option introduced through clipboard HTML | original IDs retained; pasted headings receive fresh same-kind IDs | clipboard integration test |
| nested Choice/Option attrs in callout/pane | serialization diagnostics block; serializer throws; Save does not commit | serializer + Save test |
| existing Scene/Beat-only Markdown → import/export | marker bytes and P1B membership unchanged | P1A/P1B regression |

---

## §4 Files in scope — write lease

Expected paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-choice-option-identity.md` | Checked-in P1C slice authority |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Mandatory P1C review-ledger disposition only; current-sequence state is synchronized before dispatch |
| Modify | `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts` | Add Choice/Option kind registry, IDs, and heading-level mapping to existing identity family |
| Modify | `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts` | Extend P1B index with Choice/Option membership and orphan failure semantics |
| Modify | `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.test.ts` | Preserve P1B regressions and prove extended structure semantics |
| Create | `apps/live-control-ui/src/tiptap/playable/playableChoiceOptionIdentity.test.ts` | Real Markdown import/serialize/round-trip, compatibility, invalid/nested/duplicate proof through existing generic seams |
| Create | `apps/live-control-ui/src/tiptap/playable/playableChoiceOptionClipboard.test.tsx` | Real ProseMirror clipboard HTML duplicate/re-key proof for Choice/Option |
| Create | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.playableChoice.test.tsx` | Owning workspace Save/reload proof without changing Save production code |
| Modify only if required by type/generalization | `apps/live-control-ui/src/tiptap/extensions/PlayableElementHeadingAttributes.ts` | Existing generic integrity plugin must support new kinds; no new UI/command semantics |

### Deliberate non-lease for Markdown production paths

P1A intentionally centralized playable marker admission/serialization around generic helpers. P1C should prove that seam is real.

Therefore these production paths are **not** in the expected write lease:

```text
apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts
apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts
apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts
apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts
```

P1C tests may import/exercise them.

If new Choice/Option kinds require semantic special-casing in those production files instead of flowing through the generic P1A identity helpers, stop and report whether the P1A abstraction is insufficient. Do not silently widen the lease.

### Bounded discovery exception

```text
Directory:
  apps/live-control-ui/src/tiptap/playable/**
Maximum additional paths:
  2
Allowed path kinds:
  focused test fixture/helper only
Decision rule:
  required solely to prove the same Choice/Option identity+membership invariant;
  no new production semantic owner, UI, persistence, or operator command
```

A required production path outside the explicit lease is a stop report.

---

## §5 Explicitly out of scope / collision boundary

| Path / concern | Why this slice must not touch or claim it |
|---|---|
| `apps/live_control_server/**` | No backend/store/API change; existing workspace document remains durable authority |
| workspace-document schema/API | P1C consumes current revision/digest + Markdown body unchanged |
| `DecisionConsequenceNode.ts` semantics | Existing two-pane decision/consequence prep is not Choice branching |
| user-facing toolbar/slash/command creation | Separate operator workflow; Scene/Beat creation is not solved here either |
| transition/consequence fields on Options | Additional authored semantic contract; P1C only establishes exact selection identity/membership |
| P2 Run state | Successor owns current/resolved/selection persistence |
| P3 Play Scene/Beat/Choice UI | Projection workflow, not identity durability |
| generic `WorkObjectElementRef` | P1B did not prove second independent consumer; review posture only |
| DungeonMind / DungeonMindDnD | No kernel/profile change |
| `ofConks*` / adventure bridges | Mining evidence only, not permanent substrate |
| `apps/live-control-ui/src/tiptap/markdown/**` production files | Generic P1A seam should already carry new kinds; stale PR #510 also overlaps this neighborhood |
| `Docs/Roadmaps/ROADMAP-con-ready.md` | Stable product sequence unless P1C evidence materially changes it |

### Known parallel-lane note

Open PR #510 is stale/conflicting but touches shared Markdown parser/serializer tests and implementation. P1C deliberately avoids those production paths and uses new focused tests. If P1C discovers it truly must edit a #510-owned path, stop for steward ownership resolution rather than relying on merge conflict arbitration.

---

## §6 Implementation contract

```text
Input:
  One semantic Markdown / TipTap workspace-document projection using the existing
  P1A dmb-playable-element:v1 marker family and P1B structure-index contract.

Output:
  Canonical Choice/Option heading identities plus an extended read-only
  PlayableStructureIndexResult that can validate Scene→Choice→Option membership.

Invariant:
  Same as §1: exact durable identity + exact deterministic membership or a blocked
  result; existing Scene/Beat semantics remain unchanged; no Runtime state created.

Failure behavior:
  invalid choice/option kind/id/level → identity validation failure / blocked index
  nested choice/option identity      → serialization/index failure; no nested grammar
  duplicate exact ID                 → blocked; no first/latest winner
  Choice before Scene                → orphan_choice; whole index blocked
  Option without active Choice       → orphan_option; whole index blocked
  Option after Beat boundary         → orphan_option; never attached through Beat
  non-document root                  → existing non_doc_root blocked result

Replay / idempotency:
  same canonical Markdown → same TipTap identity attrs + same structure index
  same TipTap JSON        → same canonical marker bytes + same structure index
  rename heading text     → same IDs/membership
  reorder semantic blocks → same IDs; derived order/parent changes only where position changed

Trust boundary:
  Verifies:
    marker grammar, kind/id/level, root placement, uniqueness, Scene/Choice membership
  Records/trusts without proving:
    semantic wisdom of the choice, option completeness, transition correctness,
    whether an option should be selected, World/Source truth
```

### Commit point

P1C introduces no new durable commit mechanism.

The existing workspace-document Markdown commit remains the only durability point:

```text
TipTap projection
→ existing semantic Markdown serializer
→ existing workspace prepare/commit CAS
→ committed revision/digest
→ reload/admission
```

No P1C-derived index is persisted.

### A. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| canonical Scene H2 / `scene:*` | P1A behavior unchanged | none | No title-derived identity |
| canonical Beat H3 / `beat:*` | P1A behavior unchanged | none | No title-derived identity |
| canonical Choice H3 / `choice:*` | attach exact Choice ID | exact kind/level/prefix required | No |
| canonical Option H4 / `option:*` | attach exact Option ID | exact kind/level/prefix required | No |
| unmarked H3/H4 | ordinary heading | never inferred as Choice/Option | Yes — remain untyped |
| Choice rename | ID unchanged | none | No regeneration |
| Option rename | ID unchanged | none | No regeneration |
| duplicate exact ID | entire identity/index use blocks | explicit duplicate diagnostic | No winner |
| copy/paste duplicate | pre-existing owner retains ID; pasted occurrence re-keyed | same-kind fresh ID | Yes — re-key only editor-created duplicate, never source hydration |
| Choice moved across Scene | Choice ID unchanged; derived sceneId changes | document order is structure | No sticky old parent |
| Option moved across Choice | Option ID unchanged; derived choiceId changes | active Choice is structure | No sticky old parent |

### B. Persistence / compatibility matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback/reversion |
|---|---|---|---|---|---|
| Existing Scene/Beat import/save | existing v1 marker bytes | exact existing IDs | unchanged | byte/semantic behavior unchanged | P1A behavior |
| Choice import/save | v1 marker + H3 | exact `choice:*` restored | deterministic | additive kind registry | git revert removes support; new docs must then fail closed rather than silently normalize |
| Option import/save | v1 marker + H4 | exact `option:*` restored | deterministic | additive kind registry | same |
| Structure index | derived memory only | recomputed from exact doc | same doc → deep-equivalent index | existing Scene/Beat meaning preserved; additive Choice fields | no durable rollback needed |

### C. Predecessor → consumer mapping

**Grounding source:** merged P1A identity helpers + merged P1B structure index at the dispatch base.

| Predecessor field/outcome | Real shape | P1C consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| `PlayableElementKind` | currently `scene | beat` | add `choice | option` | additive registry | identity integration test |
| `headingLevelForPlayableKind()` | Scene=2, Beat=3 | Choice=3, Option=4 | exact mapping | wrong-level tests |
| `validatePlayableHeadingAttrs()` | exact kind/id/level validation | same validator owns all four kinds | no parallel validator | serializer/admission tests |
| `PlayableElementHeadingAttributes` | generic heading attrs + re-key plugin | same plugin handles Choice/Option | enum/level-driven | clipboard test |
| `PlayableStructureIndex.sceneOrder/scenes/elements` | Scene/Beat derived structure | add Choice collections/membership while preserving old semantics | additive derived shape | structure regression |
| workspace Save | diagnostics → serializer → CAS commit | no production change; new kinds traverse same path | reuse | workspace Save/reload test |

---

## §7 Evidence required to merge

Every material invariant clause needs proof at the owning boundary.

| Guarantee / invariant clause | Owning boundary | Evidence class | Command / scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Exact Choice/Option markers admit exact attrs | Markdown admission via P1A helpers | contract | focused Vitest using real Markdown | Choice H3 / Option H4 exact IDs, no diagnostics | production parser needs new semantic branch |
| Existing Scene/Beat markers remain byte/semantic stable | parser + serializer | regression | import/serialize existing P1A fixture | exact same Markdown / index parents | existing bytes change |
| Choice/Option serialize and re-import exactly | serializer + admission | round-trip | focused Vitest | exact IDs/kinds/levels after reload | ID regenerated/lost |
| Workspace Save/reload preserves Choice/Option | workspace authoring CAS path | persistence | focused hook/integration test | prepare/commit body contains exact markers; reload reconstructs IDs | Save production code must change |
| Choice belongs to exact marked Scene | P1B index | structure | focused Vitest | exact `sceneId`; unmarked H3 ignored | title/level heuristic used |
| Option belongs to exact active Choice | P1B index | structure | focused Vitest | exact `choiceId` and `sceneId` | implicit/default parent |
| Beat closes active Choice option run | P1B index | adversarial | Choice→Option→Beat→Option | final Option blocks `orphan_option` | Option leaks across Beat |
| Choice/Option before required parent blocks | P1B index | adversarial | Choice before Scene; Option before Choice | whole result `blocked` with exact diagnostic | synthetic parent or partial ready index |
| Rename preserves identity | identity + serializer | adversarial | mutate heading text only | IDs and membership unchanged | text participates in identity |
| Reorder changes only derived order/parent | structure | adversarial | move Choice across Scene; Option across Choice | IDs stable; only correct derived fields change | sticky old parent |
| Clipboard duplicates re-key | editor integrity plugin | interaction/integrity | real ProseMirror clipboard HTML serialize/parse/insert | originals retain IDs; pasted Choice/Option fresh same-kind IDs | JSON insertion stand-in only |
| Nested Choice/Option cannot commit | serializer diagnostics + Save | adversarial | manufactured attrs under callout/pane | typed failure / Save blocked | nested marker emitted |
| No Decision/Consequence conflation | schema regression | contract/regression | inspect/targeted tests | existing D/C node and Markdown unchanged | P1C mutates D/C semantics |
| Roadmap reconsidered before PASS | process/state authority | review | handback + ledger | exact disposition, evidence head, successor | roadmap stale/contradictory |

### Exact verification commands

Run from repository root unless the package wrapper requires the current equivalent:

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/tiptap/playable/playableStructureIndex.test.ts \
  src/tiptap/playable/playableChoiceOptionIdentity.test.ts \
  src/tiptap/playable/playableChoiceOptionClipboard.test.tsx \
  src/workspaceDocument/useWorkspaceDocumentAuthoring.playableChoice.test.tsx
pnpm typecheck
pnpm build
cd ../..
git diff --check
git diff --name-only <BASE_SHA>...HEAD
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-choice-option-identity.md \
  --pr <PR_NUMBER>
```

If a newly created focused test is consolidated into an already-leased P1C test file, record the exact final command. Do not replace real parser/serializer/clipboard/Save evidence with pure helper tests.

### Minimal dogfood proof

No new user-facing surface or creation workflow is delivered in P1C, so a manual toolbar/UI dogfood is not required.

The minimal realistic owning-boundary scenario is executable integration evidence:

```text
1. admit a runbook Markdown fixture with Scene + Beat + Choice + two Options;
2. derive the structure index;
3. edit Choice/Option labels in TipTap JSON/editor state;
4. serialize through the real semantic Markdown serializer;
5. commit through the existing workspace Save harness;
6. reload/re-admit;
7. derive the index again.

Expected:
  same exact choiceId/optionIds;
  same intended Scene/Choice parents;
  changed labels only;
  no persisted index/runtime state.
```

### Baseline failure handling

If `pnpm typecheck`, `pnpm build`, or a required focused test fails on the exact dispatch base, run the same command on base and head and record both. P1C may not waive a new failure as pre-existing without proof.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/reviewed head SHA;
2. implementation/evidence head separately if a roadmap bookkeeping commit follows;
3. §1 mission/invariant disposition;
4. §7 required vs produced evidence with provenance:
   - author-local;
   - independently rerun;
   - CI if present;
   - explicit waiver if any;
5. nano-commit/fix story;
6. base/head and actual changed paths vs §4;
7. baseline failures/waivers;
8. paths outside §4 (`none` or stop report);
9. stop conditions and resolution;
10. prior finding ledger on re-review;
11. named successor remains false:

```text
P2 — separate Run runtime
```

12. exactly one roadmap disposition:

```text
ROADMAP_REVIEW — UPDATED
...
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
...
```

13. exact roadmap ledger row using the implementation/evidence head;
14. this hoist observation:

```text
P1C_HOIST_OBSERVATION
- Did P1C prove stable element resolution is needed by a second independent consumer? yes/no/evidence insufficient
- Is WorkObjectElementRef now justified? yes/no/not yet
- Does the four-kind identity family still belong in Play, or did evidence reveal a genuinely product-neutral owner?
- Is P2 now safe to persist choiceId → optionId against one exact Playable revision? yes/no + missing contract if no
- DungeonMind relevance discovered? none / exact future audit question only
```

The reviewer may PASS with `not yet` on hoisting. P1C must not manufacture a shared-layer justification merely because more Play-owned element kinds exist.

---

## §9 Acceptance rubric

- [x] Post-#592 state-authority sync landed before dispatch.
- [x] Exact implementation base is pinned after that sync.
- [ ] Existing `dmb-playable-element:v1` marker family is extended additively with `choice` and `option`; no second marker authority is invented.
- [ ] Choice uses exact `choice:*` identity on root H3.
- [ ] Option uses exact `option:*` identity on root H4.
- [ ] Existing Scene H2 / Beat H3 marker bytes and semantics remain unchanged.
- [ ] Choice/Option survive real Markdown → TipTap → Markdown → reload with exact IDs.
- [ ] Clipboard duplication re-keys pasted Choice/Option IDs without changing originals.
- [ ] Nested/invalid/duplicate Choice/Option identity fails closed.
- [ ] P1B index extends to deterministic Scene→Choice→Option membership.
- [ ] Choice before Scene blocks.
- [ ] Option without active Choice blocks.
- [ ] Beat/Scene/new Choice closes the prior Choice option run.
- [ ] Unmarked H3/H4 remain structurally invisible.
- [ ] Choice with zero Options remains structurally valid; no unsupported minimum-option rule is invented.
- [ ] No Decision/Consequence semantics are changed or reused as Choice.
- [ ] No runtime `choiceId → optionId` state is persisted.
- [ ] No user-facing Choice creation workflow is introduced.
- [ ] No option transition/consequence schema is introduced.
- [ ] No backend/store/workspace schema or kernel contract changes.
- [ ] Actual changed paths stay inside §4 / bounded discovery.
- [ ] Focused tests + typecheck + build + diff checks pass or baseline differences are truthfully recorded.
- [ ] Roadmap review disposition and P1C hoist observation are explicit.
- [ ] P2 remains the named successor and is not silently started in this PR.

## Stop conditions

Stop and report instead of expanding if any of these appears:

- post-#592 roadmap/handoff state authorities are not synchronized before dispatch;
- current `main` materially changes P1A identity or P1B index contracts;
- additive `v1` kind extension is ambiguous/unsafe and appears to require a new marker version/migration;
- Choice/Option requires a custom non-heading TipTap node to satisfy the mission;
- generic P1A parser/serializer production code requires Choice-specific branching rather than existing helper generalization;
- workspace Save production code must change;
- a user-facing create/edit workflow becomes necessary to prove durability;
- transition/consequence/reference payload becomes necessary for exact identity/membership;
- a required production path falls outside §4;
- stale/active PR #510 or another lane owns a newly required shared Markdown path;
- P2 runtime state becomes necessary to make P1C meaningful rather than merely its named consumer;
- implementation evidence contradicts the canonical Playable architecture;
- required owning-boundary evidence cannot be produced.

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
