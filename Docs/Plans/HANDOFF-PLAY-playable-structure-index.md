---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: Playable Architecture Graduation / P1B
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-playable-structure-index.md
  - Branch / PR: agent/play-playable-structure-index / `PLAY: index durable Scene and Beat structure`

  ## Verification pointer
  - Base/head: `e05e850349e81163402dbd6718cd83bcc778a894` / <implementation head>
  - Predecessor: merged PR #590 / main `5221fa9bb58283955165e507710d10bdf3e00d47` at design time
  - Changed paths: must remain inside HANDOFF §4
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, independently
  rerun evidence, and roadmap review disposition are the review contract.
  This body is transport metadata.
---

# HANDOFF — read-only Playable Scene / Beat structure index

**Created:** 2026-08-15  
**Status:** ACTIVE — base pinned after PR #591 state-authority sync; CODE may dispatch  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-playable-structure-index.md`  
**Conversation/workstream:** `Playable Architecture Graduation / P1B`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design anchor:** merged PR #590 at main `5221fa9bb58283955165e507710d10bdf3e00d47`  
**Implementation base:** `e05e850349e81163402dbd6718cd83bcc778a894`  
**Suggested branch:** `agent/play-playable-structure-index`  
**PR title:** `PLAY: index durable Scene and Beat structure`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## Dispatch gate — close P1A state first

PR #590 is merged. At design time, `main` is exactly:

```text
5221fa9bb58283955165e507710d10bdf3e00d47
```

The next dependent CODE lane must not dispatch until the post-merge mutable-state sync is on `main`.

That sync must, at minimum:

1. update `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` so P1A is recorded as merged and P1B is the current next slice;
2. mark `Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md` complete/merged according to repository handoff-status convention;
3. check in this P1B handoff;
4. preserve the P1A roadmap conclusion: Scene/Beat identity remains Play-owned; no `WorkObjectElementRef` hoist yet.

After that state-sync transaction lands:

1. fetch current `main`;
2. replace `PIN_AT_DISPATCH_AFTER_STATE_SYNC` in this handoff with that exact SHA;
3. verify merged P1A production paths still exist and the roadmap still names P1B as next;
4. run `uv run python scripts/steward_preflight.py --handoff Docs/Plans/HANDOFF-PLAY-playable-structure-index.md`;
5. stop if another active lane owns any §4 path or if `main` materially changed the P1A identity contract.

The pin-at-dispatch edit is handoff completion, not capability expansion.

### Dispatch-gate finding — 2026-08-15 (DESIGN, pre-CODE)

| Check | Result |
|---|---|
| PR #590 state | **MERGED** at 2026-08-15T23:49:14Z as `5221fa9bb58283955165e507710d10bdf3e00d47` |
| Post-#590 state-authority sync | **MERGED** PR #591 at 2026-08-16T00:25:07Z |
| Current `origin/main` | `e05e850349e81163402dbd6718cd83bcc778a894` |
| P1A identity module | **PRESENT** at `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts` |
| Roadmap current next slice | **P1B — read-only Playable Scene/Beat structure index** |
| Hoist posture | Scene/Beat identity remains Play-owned; no `WorkObjectElementRef` yet |
| `PIN_AT_DISPATCH_AFTER_STATE_SYNC` | **replaced** with `e05e850349e81163402dbd6718cd83bcc778a894` |

Architecture / state-sync dispatch gate: **PASS**.

---

## §1 Mission and merge-ready invariant

**Mission:** A Playable consumer can deterministically resolve the ordered Scene/Beat structure of one admitted TipTap Runbook projection by stable P1A IDs, so later Runtime and Play projections do not scan mutable titles or invent hierarchy independently.

**Merge-ready invariant:**

> **For one exact TipTap document projection, every valid root-level P1A Scene/Beat identity produces one deterministic read-only structure index in document order; each Beat resolves to exactly one preceding marked Scene or the entire index fails closed, while unmarked content remains structurally invisible and the index creates no durable authority of its own.**

### Why this is P1B instead of Choice/Option identity

P1A required three formal review cycles before its first durable identity grammar safely handled:

- exact heading level;
- serializer losslessness;
- clipboard duplication;
- Save-path failure;
- document-root structural placement.

That is useful evidence: **new durable identity syntax is a material contract, not incidental metadata.**

P1B therefore consumes the identity contract before extending it. Choice/Option identity moves to P1C, where its representation can be designed from an actual next consumer instead of being guessed into the Markdown grammar.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path asks whether one TipTap projection yields one exact, non-ambiguous Scene/Beat structure or a blocked result. |
| Most likely adversarial sequence | Valid Scene → ordinary headings/content → Beat → move Beat across a marked Scene boundary → rebuild index. A positional/title heuristic would silently retain the wrong parent. |
| Will §7 actually detect that failure? | Yes. Tests assert exact IDs, order, parent Scene, boundary moves, unmarked-heading invisibility, and blocked orphan Beats. |
| Easiest owning boundary to under-test | The P1A→P1B seam: tests that manufacture attrs directly could miss disagreement with real Markdown admission. §7 requires one Markdown → P1A import → P1B index integration proof. |
| What fact forces stop/split? | If indexing requires a new persisted representation, Save policy, Markdown grammar, editor mutation command, backend endpoint, or a generic cross-surface ref contract, stop and re-brief. |

### Capability decomposition

| Candidate outcome | Independently useful? | Durable/public contract? | Decision |
|---|---:|---:|---|
| Derive ordered Scene/Beat index from P1A semantic attrs | Yes | Caller-facing Play-domain type, non-durable | **Include** |
| Resolve Beat → parent Scene from document order | Yes, inseparable from Runbook structure | Same index contract | **Include** |
| Detect structurally unusable marked Beat before any Scene | No, safety clause of same invariant | Failure contract | **Include** |
| Read index from real P1A Markdown import | No, integration proof | Existing parser contract only | **Include as test evidence** |
| Persist index / cache it as authority | Yes | New durable contract | **Exclude** |
| Choice / Option identity | Yes | New durable identity contract | **Exclude — P1C** |
| Current Scene/Beat Runtime state | Yes | New durable runtime contract | **Exclude — P2** |
| Scene deck / Beat strip UI | Yes | Product workflow | **Exclude — P3** |
| Generic `WorkObjectElementRef` | Yes | Shared Buddy contract | **Exclude — hoist review only** |
| DungeonMind context/ref changes | Yes | Cross-repo kernel contract | **Explicitly prohibited** |

---

## §2 Context, authority, and lane

### Parent authority — read in this order

1. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
2. `Docs/Design/DESIGN-playable-authoring-and-adoption.md`
3. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
4. `Docs/Plans/HANDOFF-PLAY-durable-scene-beat-identity.md` as merged predecessor evidence
5. merged P1A implementation under `apps/live-control-ui/src/tiptap/playable/`
6. `AGENTS.md`
7. `Docs/Process/STEWARD-CYCLE.md`

### P1A predecessor contract consumed unchanged

P1A established:

```text
Scene = root-level heading level 2
  + playableElementKind = "scene"
  + exact scene:* id

Beat = root-level heading level 3
  + playableElementKind = "beat"
  + exact beat:* id
```

P1A already owns:

- durable Markdown marker spelling;
- import/admission;
- exact kind/id/level validation;
- duplicate-ID serializer rejection;
- nested playable identity rejection;
- copy/paste duplicate re-keying;
- Save-path fail-closed behavior.

P1B **must consume those semantics rather than redefining them.**

### Lane table

| Field | Required content |
|---|---|
| Base revision | Exact dispatch-time `main` SHA `e05e850349e81163402dbd6718cd83bcc778a894` containing merged PR #591 |
| Design anchor | `5221fa9bb58283955165e507710d10bdf3e00d47`, merge of PR #590 |
| Predecessor contract | P1A stable root-level Scene/Beat identity |
| Exact input consumed | One TipTap JSON `doc` projection using P1A heading attrs |
| Output | One read-only `PlayableStructureIndexResult` derived from that projection |
| Named successor | `P1C — Choice / Option identity and minimal authored representation` |
| What remains false | No durable Choice/Option ID; no Run state; no Play surface projection; no proposal targeting contract; no generic work-object ref |
| Explicit non-goals | New Markdown syntax, Save blocking, editor commands, datastore/API, migration, caching, Play UI, kernel/profile changes |
| Runtime/state ownership | None. Pure derivation only; tests may use in-memory fixtures. |
| State-authority sync after merge | This handoff status + living Playable hoist roadmap. `ROADMAP-con-ready.md` only if actual product sequencing changes. |

### Roadmap review is a merge gate

Before final PASS, coding agent and reviewer must answer:

```text
Did P1B evidence change ownership, sequence, hoist posture, successor boundaries,
or assumptions in ROADMAP-playable-hoist-dungeonmind-kernel.md?
```

The PR must record exactly one:

```text
ROADMAP_REVIEW — UPDATED
...
```

or

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
...
```

and update the P1B ledger row using the implementation/evidence head, not the later bookkeeping SHA.

---

## §3 Observable paths and adversarial sequences

### Canonical P1B structural interpretation

P1B interprets only **marked P1A root headings**.

```text
root doc

Scene A  [scene:a]
  ordinary prose/headings/etc.
  Beat A1 [beat:a1]
  Beat A2 [beat:a2]

ordinary unmarked H2
  does not start/end a Scene

Scene B [scene:b]
  Beat B1 [beat:b1]
```

Rules:

1. A canonical marked Scene starts the current Scene.
2. A canonical marked Beat belongs to the nearest preceding canonical marked Scene in root document order.
3. A marked Beat before any marked Scene blocks the structure index; it is not assigned to a synthetic/default Scene.
4. A later marked Scene starts a new Scene boundary.
5. Unmarked headings and all other ordinary blocks do not create, terminate, or rename structural identity.
6. IDs remain the only durable addressing value. Order and parent Scene are derived properties of this exact projection/revision.
7. Moving a Beat across a marked Scene boundary intentionally changes its derived parent Scene while retaining the same Beat ID.
8. P1B never adds/repairs/re-keys IDs. P1A owns identity mutation/safety.
9. P1B produces no persisted index file, localStorage record, workspace metadata, or backend row.
10. A blocked index returns **no partial usable index**. Consumers must not “use the valid scenes anyway.”

### Proposed non-durable result shape

Exact TypeScript naming may follow nearby conventions, but the semantic contract is:

```ts
type PlayableStructureIndexResult =
  | {
      status: "ready";
      index: {
        sceneOrder: string[];
        scenes: Array<{
          sceneId: string;
          order: number;
          beatOrder: string[];
        }>;
        elements: Array<
          | { kind: "scene"; id: string; order: number }
          | { kind: "beat"; id: string; order: number; sceneId: string }
        >;
      };
    }
  | {
      status: "blocked";
      diagnostics: Array<{
        code: string;
        message: string;
        elementId?: string;
      }>;
    };
```

This is a **derived Play-domain projection**, not a serialized schema commitment. The implementation may use readonly arrays/maps internally if tests and consumers preserve the same semantics.

Do not add display titles as locators. If a heading label is exposed for convenience, it is presentation metadata only and must never participate in identity, parent resolution, or equality.

### Observable paths

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Valid one-Scene Runbook | Consumers must scan TipTap/title/order ad hoc | Exact `scene:*` and ordered `beat:*` membership | Yes | P1B structure index |
| Multiple marked Scenes | No canonical derived hierarchy consumer | Each Scene has exact ordered Beat membership | Yes | P1B structure index |
| Rename Scene/Beat heading text | P1A keeps identity but no canonical consumer exists | Index IDs/hierarchy unchanged | Yes | P1B structure index |
| Reorder Beats inside same Scene | No canonical structure consumer | Beat order changes; IDs/parent remain exact | Yes | P1B structure index |
| Move Beat across marked Scene boundary | Potential future title/position heuristic risk | Same Beat ID now resolves to new preceding marked Scene | Yes | P1B structure index |
| Unmarked H2/H3 among playable content | Could be mistaken as structure by ad hoc consumer | Structurally ignored | Yes | P1B structure index |
| Marked Beat before any marked Scene | P1A can durably represent it; no run-structure judgment yet | Entire index blocked with explicit diagnostic | Yes | P1B structure index |
| Invalid/partial/nested/duplicate playable attrs in manufactured TipTap | P1A Save would fail, but a direct consumer could still be handed bad JSON | Index blocks; never normalizes or chooses a winner | Yes | P1B structure index |
| Ordinary non-playable blocks | No index contract | Ignored by structural derivation | Yes | P1B structure index |

### Adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| P1A Markdown → TipTap import → P1B index | Exact Scene/Beat IDs and parent relation agree with source order | P1A integration test |
| Scene A → Beat X → Scene B → move Beat X after Scene B | Beat X keeps ID and resolves to Scene B in rebuilt index | boundary-move test |
| Scene A → unmarked H2 → Beat X | Beat X still resolves to Scene A | unmarked-boundary test |
| Beat X → Scene A | blocked; no synthetic/default Scene | orphan-Beat test |
| duplicate `beat:x` manufactured in TipTap | blocked; no first/last winner | duplicate test |
| valid root Scene plus nested marked Beat | blocked; no partial index | nested-identity test |
| same document indexed twice | deep-equivalent result | determinism test |

---

## §4 Files in scope — write lease

Expected implementation paths after this handoff is checked into `main`:

| Action | Path | Purpose |
|---|---|---|
| Modify | `Docs/Plans/HANDOFF-PLAY-playable-structure-index.md` | Review-cycle handback / status only |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | Mandatory P1B roadmap review ledger/disposition |
| Create | `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts` | Pure Play-domain structure derivation/result contract |
| Create | `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.test.ts` | Unit + P1A integration evidence for §1 |

**Bounded discovery exception:** Not applicable.

The existing P1A identity/admission/serializer files are **read dependencies, not write authority** for this slice. If production code changes are required outside the two new Playable files, stop and report why the P1B seam cannot remain read-only.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why P1B must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts` | P1A owns identity grammar/validation; P1B should consume exports unchanged. Needing new identity semantics is a re-brief signal. |
| `apps/live-control-ui/src/tiptap/markdown/**` | No parser/serializer/admission change is required to derive structure from admitted TipTap JSON. |
| `apps/live-control-ui/src/workspaceDocument/**` | P1B creates no Save, revision, local-draft, or workspace-authoring behavior. |
| `apps/live_control_server/**` | No backend/store/API contract. |
| Play surface routes/components | P3 owns table-facing Scene deck/Beat strip/projection. |
| Runtime persistence | P2 owns current/resolved state and revision binding. |
| Choice/Option grammar or authoring | P1C owns the next durable element contract if/when P2 selections require it. |
| Proposal targeting / Canvas mutation | P5 owns shared proposal/adoption seam. |
| Generic `WorkObjectElementRef` | Promotion test not satisfied yet; this PR gathers consumer evidence only. |
| `Drakosfire/DungeonMind/**` | No kernel/profile work in P1B. |

---

## §6 Implementation contract

```text
Input:
  One TipTap JSON document projection.
  P1A optional heading attrs are the only Playable identity source.

Output:
  ready → one deterministic read-only Scene/Beat index
  blocked → explicit structural/identity diagnostics and no usable partial index

Invariant:
  same as §1

Failure behavior:
  non-doc root               → blocked
  invalid/partial identity   → blocked
  duplicate identity         → blocked
  nested playable identity   → blocked
  marked Beat before Scene   → blocked
  ordinary unmarked content  → ignored structurally

Replay / idempotency:
  same TipTap JSON → deep-equivalent index
  rename text only → same IDs/parent/order
  reorder within Scene → same IDs/parent, changed derived order
  move Beat across Scene boundary → same Beat ID, changed derived parent

Trust boundary:
  Verifies:
    P1A identity shape as consumed, document-root placement, uniqueness,
    Scene ordering, Beat ordering, Beat parent membership
  Records/trusts without proving:
    semantic meaning of prose, whether a Scene is good prep, World/Source truth,
    durable work-object revision, Runtime selection/progress
```

### A. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact marked Scene ID | one Scene entry | duplicate/invalid blocks | No |
| Exact marked Beat ID after Scene | one Beat entry + exact parent Scene | duplicate/invalid blocks | No |
| Beat before first Scene | no parent exists | block whole index | No synthetic parent |
| Unmarked heading text resembling a Scene/Beat | ignore structurally | none | No inference |
| Rename | identity unchanged | none | No label-derived rebind |
| Beat moved across Scene boundary | parent changes by exact document order | none | No sticky old parent |
| Deleted marked element | absent from rebuilt index | consumer sees missing exact ID | No old-position fallback |

### B. State/fallback matrix

| Input state | Result |
|---|---|
| Valid P1A structure | `ready` exact index |
| No marked Scenes/Beats | `ready` empty index |
| Ordinary unmarked headings only | `ready` empty index |
| Marked Scene with no Beats | `ready`; empty `beatOrder` |
| Marked Beat without preceding Scene | `blocked` |
| Invalid/duplicate/nested playable attrs | `blocked` |
| Unsupported non-playable TipTap block | ignored unless it independently violates the document shape required to traverse; P1B does not become semantic-Markdown safety authority |

### C. Persistence / replay matrix

P1B itself has **no durable representation**.

| Operation | Durable representation | Guarantee |
|---|---|---|
| Build index | none | deterministic derivation from current input projection |
| Rebuild after edit | none | reflects current exact order/parents while preserving stable IDs |
| Restart/reload | none | caller re-imports/reloads through existing authority, then rebuilds |

If implementation wants to persist/cache the index as authority, stop: that is a new contract.

### D. Predecessor-to-consumer mapping

| P1A predecessor fact | P1B interpretation |
|---|---|
| root marked H2 `scene:*` | Scene boundary / Scene entry |
| root marked H3 `beat:*` | Beat entry under nearest preceding marked Scene |
| exact stable ID | sole durable element address |
| ordinary heading | no Playable structural meaning |
| nested identity invalid for durability | blocked if encountered in direct input |
| duplicate identity invalid | blocked, never first/last winner |

---

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected result | Stop condition |
|---|---|---|---|---|
| One Scene + Beats indexes exactly | structure index | focused Vitest | exact IDs/order/parent | title/level inference needed |
| Multiple Scenes partition Beats by marked boundaries | structure index | focused Vitest | exact per-Scene Beat order | synthetic hierarchy required |
| Real P1A Markdown import feeds same index | parser → P1B integration | focused Vitest in P1B test file | P1A markers import then index exactly | P1B must modify parser to work |
| Rename does not rebind identity | structure index | adversarial test | same IDs/parent | title participates in address |
| Reorder within Scene changes only order | structure index | adversarial test | parent stable | positional identity used |
| Move Beat across Scene changes parent intentionally | structure index | adversarial test | same Beat ID, new Scene ID | sticky old parent / hidden sidecar |
| Unmarked headings are structurally invisible | structure index | regression | no Scene/Beat created/boundary changed | heading level/title inferred |
| Beat before Scene blocks entire index | structure index | adversarial | `blocked`, no partial index | synthetic/default Scene |
| Invalid/duplicate/nested identity blocks | structure index | adversarial | `blocked` | first/last/repair behavior |
| Same document gives same index | structure index | replay | deep-equivalent output | nondeterministic ordering |
| Existing app remains type/build clean | repository | typecheck/build | exit 0 | new regression |
| Roadmap reconsidered | process/state authority | review handback + ledger | explicit disposition | roadmap stale or P1C/P2 boundaries contradicted |

### Exact verification commands

From repository root:

```bash
cd apps/live-control-ui
pnpm exec vitest run src/tiptap/playable/playableStructureIndex.test.ts
pnpm typecheck
pnpm build
cd ../..
git diff --check
git diff --name-only <BASE_SHA>...HEAD
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-playable-structure-index.md \
  --pr <PR_NUMBER>
```

Reviewer should independently rerun the focused test, typecheck, build, and diff check unless a repository-level CI result provides stronger equivalent evidence.

### Minimal dogfood proof

No new UI is authorized in P1B. The smallest realistic proof is an actual semantic-Markdown fixture using P1A markers:

```text
Scene A
  Beat A1
  Beat A2
Scene B
  Beat B1
```

Import through the existing P1A Markdown path, build the P1B index, then assert:

```text
sceneOrder = [scene:a, scene:b]
scene:a.beatOrder = [beat:a1, beat:a2]
scene:b.beatOrder = [beat:b1]
```

This is a contract dogfood, not a new surface.

---

## §8 Required review handback

Record:

1. `Review Cycle <N>` and exact PR/branch/head SHA;
2. §1 mission/invariant disposition;
3. §7 required vs produced evidence + provenance;
4. nano-commit/fix story;
5. exact base/head and actual changed paths vs §4;
6. baseline failures/waivers;
7. paths outside §4 (`none` or stop report);
8. stop conditions encountered and resolution;
9. prior finding ledger on re-review;
10. named successor remains false: `P1C — Choice / Option identity and minimal authored representation`;
11. P2 remains false: no durable Run state or revision-bound progress;
12. exactly one roadmap disposition;
13. update the P1B roadmap ledger row using the implementation/evidence head;
14. record:

```text
P1B_HOIST_OBSERVATION
- Did P1B prove stable element resolution is needed by a second independent consumer? yes/no/evidence insufficient
- Is `WorkObjectElementRef` now justified? yes/no/not yet
- If yes, name the second consumer and shared invariant; do not implement the hoist in this PR
- Should P1C Choice/Option identity remain next? yes/no + evidence
- DungeonMind relevance discovered? none / exact future audit question only
```

The reviewer may PASS with `not yet`; P1B is deliberately an evidence-producing consumer before hoisting.

---

## §9 Acceptance rubric

- [x] Post-#590 state-authority sync landed before dispatch.
- [x] Exact implementation base is pinned after that sync.
- [ ] P1B consumes P1A identity exports without changing P1A durable grammar.
- [ ] Valid marked Scenes/Beats produce one deterministic ordered index.
- [ ] Every marked Beat has exactly one preceding marked Scene or the index blocks.
- [ ] Unmarked headings/content never create Playable structure or boundaries.
- [ ] Rename does not affect identity/hierarchy.
- [ ] Reorder within a Scene changes order only.
- [ ] Moving a Beat across a marked Scene boundary changes parent while preserving Beat ID.
- [ ] Invalid, duplicate, or nested identity blocks; no winner/repair/partial index.
- [ ] Empty/unmarked documents can return a valid empty index.
- [ ] No index persistence/cache/store/API is introduced.
- [ ] No Choice/Option identity is introduced.
- [ ] No Run state, Play UI, proposal targeting, generic ref, or DungeonMind contract is introduced.
- [ ] Changed paths stay inside §4.
- [ ] Focused tests, typecheck, build, diff check, and steward preflight pass or truthful baseline differences are recorded.
- [ ] Roadmap review disposition and P1B hoist observation are explicit before final PASS.

## Stop conditions

Stop and report instead of expanding if any of these appears:

- the post-#590 state-authority sync has not landed;
- `main` no longer matches P1A identity semantics;
- deriving structure requires modifying P1A Markdown grammar/admission/serialization;
- the index needs to mutate or repair the editor document;
- a durable/cached index becomes necessary;
- exact resolution requires a new generic `WorkObjectElementRef` to make P1B useful;
- Choice/Option representation becomes necessary to index Scene/Beat structure;
- Runtime persistence becomes necessary to prove the index;
- a Play surface component is required for merge value;
- a production path outside §4 is required;
- another active lane owns a §4 path;
- P1B evidence contradicts the canonical Runbook → Scene → Beat architecture.

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
