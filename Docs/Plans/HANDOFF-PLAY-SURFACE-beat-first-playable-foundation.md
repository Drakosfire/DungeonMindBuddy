---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY-SURFACE / Beat-first Playable foundation (BF1)
  - Owner: PLAY-SURFACE
  - Direction: CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md
  - Design contract: Docs/Design/DESIGN-play-current-moment-cockpit.md
  - Branch / PR: agent/play-surface-beat-first-playable-foundation / `PLAY-SURFACE: beat-first Playable grammar and manifest foundation`

  ## Verification pointer
  - Steward re-anchor before dispatch handoff refresh: `2fe6a995338225a1ff3c1493a84055bebb64f7c7`
  - Dispatch base: current `main` containing this handoff; record the exact SHA before editing
  - Predecessor: merged PR #627 / current-moment cockpit design gate
  - Changed paths: HANDOFF §5 only
  - Verification: HANDOFF §6 + exact-head formal review
---

# HANDOFF — Beat-first Playable grammar and manifest foundation (BF1)

**Created:** 2026-08-21  
**Dispatch refresh:** 2026-08-22  
**Status:** READY FOR DISPATCH — predecessor PR #627 is merged; re-anchor the exact current `main` containing this handoff before creating the branch.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md`  
**Workstream:** `PLAY-SURFACE / Beat-first Playable foundation (BF1)`  
**Flow / owner:** `PLAY-SURFACE`  
**Direction:** CODE → REVIEW  
**Suggested branch:** `agent/play-surface-beat-first-playable-foundation`  
**PR title:** `PLAY-SURFACE: beat-first Playable grammar and manifest foundation`

> Operating law: `AGENTS.md`.  
> Parent acceptance: `Docs/Roadmaps/ROADMAP-con-ready.md`.  
> Steward anchor: `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`.  
> Design contract: `Docs/Design/DESIGN-play-current-moment-cockpit.md` (§1 containment, §2 serialization, §3 manifest, §3.4 rollout gate).  
> Approved UX target: `Docs/Design/DESIGN-play-surface-gm-cockpit-target.md`.  
> Architecture: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.  
> Adjacent exploration only: `Docs/Design/EXPLORATION-tick-ledger-and-temporal-adjudication.md` — not authority and not a BF1 prerequisite.

---

## 0. Re-anchor, predecessor truth, and lane allocation

### 0.1 Repository truth at steward refresh

The steward re-anchor immediately before this handoff refresh found:

```text
main before this handoff refresh:
  2fe6a995338225a1ff3c1493a84055bebb64f7c7
  PLAY-SURFACE: capture tick and temporal adjudication exploration

PR #627:
  title:               PLAY-SURFACE: define the current-moment-cockpit contract
  final branch head:   71901b60e6c90779c11b6ca3f1b8a91493b2967f
  merge commit:        0975ebcfb714b1a664dfb57362d7cd13351aa077
  review cycles:       5
  cycles 1–4:          REQUEST-CHANGES-equivalent
  cycle 5:             PASS-equivalent
  cycle 5 review id:   5000545902
  production code:     none — design/architecture gate

post-#627 exploration:
  2fe6a995338225a1ff3c1493a84055bebb64f7c7
  EXPLORATION-tick-ledger-and-temporal-adjudication.md
  status: exploration only; no BF1/BF2 sequence change
```

PR #627 froze the Beat-first product/architecture contract and selected BF1 as
its single implementation successor. The post-merge tick exploration refined
transaction-time language but explicitly did **not** change that contract or
make a ledger/temporal capability a prerequisite.

### 0.2 Re-anchor immediately before branch creation

Before editing production code:

1. fetch current `main`;
2. record the exact SHA in the PR body as the implementation base;
3. confirm PR #627 remains merged and the final reviewed contract on `main` is
   `DESIGN-play-current-moment-cockpit.md`;
4. confirm this handoff is unchanged from the dispatch copy on `main`;
5. inspect open PRs/worktrees for overlapping writes to §5;
6. if any §5 path has acquired an active owner, stop and hand back rather than
   relying on Git conflicts.

At steward refresh, no active implementation PR owns the BF1 production
paths. Long-lived PR #578 remains a mining/review vehicle and does not grant an
active write lease. Process PR #607 is a separate documentation/tooling lane.
Lane B Combat durability remains separately collision-gated and BF1 touches no
Combat authority.

### 0.3 Backward-looking state-authority sync carried by BF1

BF1 is the first implementation slice consuming merged PR #627. Per
`AGENTS.md`, it must carry the predecessor sync while leaving BF1 itself
truthfully in flight.

The BF1 PR must record, atomically with the implementation:

- PR #627 MERGED at `0975ebcfb714b1a664dfb57362d7cd13351aa077`;
- final reviewed head `71901b60e6c90779c11b6ca3f1b8a91493b2967f`;
- **5 formal review cycles**, Cycle 5 PASS-equivalent;
- Lane A3 design gate COMPLETE;
- the reviewed Beat-first cockpit contract is now active design authority;
- BF1 is the current Play structural implementation slice;
- Lane B Combat durability remains separate/collision-gated;
- P3B/P4 remain deferred unless a fresh re-anchor changes that truth;
- CR-U17 remains false overall;
- the tick/temporal exploration is retained as exploration only and does not
  authorize a Runtime ledger, global tick, temporal kernel contract, or change
  to the BF1–BF5 dependency chain.

Do **not** mark BF1 complete, invent its merge SHA/review count, or pre-authorize
BF2/BF4 as already active.

---

## 1. Product story, mission, and merge-ready invariant

### 1.1 CON-READY framing

```text
Primary CON-READY story:
  CR-U11 — the GM can develop and persist the version of the world they intend to run.

Current user-visible failure:
  The reviewed Play model is Beat-first, but executable Playable structure is
  still the shipped v1 Scene-first grammar/manifest. Continuing into cockpit
  wiring or Plan authoring would either flatten the reviewed design or force
  implementation-time structural guesses.

One independently useful outcome after this PR:
  One committed Runbook can truthfully carry the reviewed Beat-first
  Beat/Scene/Decision/Option structure through import, edit, Save, committed
  reload, structure indexing, and exact Run-bound manifest seal/replay.

What remains false afterward:
  v2 Runs are intentionally not READY-admissible; there is no v2 current-Beat
  Runtime behavior, relevance projection, cockpit UI, Plan Beat-first authoring,
  legacy migration tooling, Combat change, or Runtime tick ledger.

Real-material proof posture:
  BF1 is a wire/integrity foundation and intentionally cannot be live-table
  dogfooded because v2 admission stays blocked until BF2. Its acceptance suite
  must nevertheless include at least one representative C2S27-shaped
  Beat/Scene/Decision/Option document, not only minimal toy directives. Live
  table dogfood resumes when the BF2/BF3 path can admit and render v2 truthfully.
```

### 1.2 Mission

Deliver the Beat-first Playable wire foundation:

1. v2 grammar parse / validate / serialize;
2. a v2 read-only structure index;
3. a v2 sealed Run reference manifest and truthful v1/v2 client contract;
4. an explicit owning-boundary rollout gate that keeps v2 Runs out of READY
   until BF2 lands current-position semantics.

This slice contains **no cockpit presentation, no Runtime current-position
change, no relevance projection, no migration tooling, and no temporal ledger**.

### 1.3 Merge-ready invariant

> **A Runbook authored with `dmb-playable-element:v2` round-trips through import, TipTap edit, Save, and committed reload with stable Beat/Scene/Decision/Option identity; validation fails closed on illegal containment, duplicate IDs, bad transition edges, and mixed grammar versions; and a Run created against a v2 revision seals a `dmb_play_run_reference_manifest_v2` whose membership, parentage, and transition edges replay without consulting current workspace state. The §3.4 rollout gate holds at the owning boundary: native Runbook admission stays v1-only, so no v2 Run reaches a READY cockpit in this slice. Existing v1 documents, manifests, Runs, and Runtime `run_revision` semantics behave exactly as before.**

### 1.4 What may be true after merge

```text
true:
  v2 grammar is parseable, validatable, and serializable
  v2 structure index derives Beat/Scene/Decision/Option membership
  v2 manifest seals and replays identity + parentage + transition edges
  frontend manifest type truthfully discriminates v1 vs v2
  v1 and v2 structural material can coexist, each read by its own versioned reader
  created+sealed v2 Runs are truthfully blocked at native Play admission
```

### 1.5 What must remain false after merge

```text
false:
  any cockpit/table UI consuming v2
  Runtime current-position semantics changed
  currentBeatId seeded for v2
  any v2 Run admitted to READY
  relevance derivation exists at runtime
  Plan has Beat-first authoring controls
  any v1 document or Run was migrated
  any Runtime tick/history/ledger was added
  any global/cross-domain clock contract was added
  Combat behavior or persistence changed
  P3B/P4 dispatchability changed
```

---

## 2. Capability contract

### 2.1 v2 grammar parse / validate / serialize

Implement the reviewed contract exactly:

- `beat` on H2;
- `scene` on H3 inside the nearest preceding Beat;
- `choice` on H3 inside the nearest preceding Beat;
- Scene and Decision are Beat-owned H3 siblings; directive `kind`, never
  heading level, distinguishes them;
- `choice` may carry optional `scene=<scene-id>` association only to a Scene in
  the same Beat;
- `option` is a marked list item inside the current choice body;
- Beat supports optional `beat_kind=spine|optional|interrupt`;
- Option supports `activates` / `suppresses` transition edges targeting Beat or
  Scene IDs in the same document;
- heading level is grammar and misplaced directives fail closed;
- fenced-code interiors remain literal under the existing `~~~` and
  variable-length-backtick rules;
- ordinary unmarked headings/prose remain non-semantic;
- the D2 playable-body termination behavior for ordinary root headings remains
  preserved.

Do not invent a second Scene→Decision hierarchy, nested H4 Decision grammar,
or alternate authoring representation in code.

### 2.2 Fail-closed validation

At minimum reject:

- duplicate semantic IDs;
- Scene outside a Beat;
- Scene structurally nested beneath another Scene;
- choice outside a Beat;
- Option outside a choice;
- Scene association to an unknown Scene;
- Scene association across Beats;
- transition edge to an unknown ID;
- unsupported transition target kind;
- unknown semantic kind/version;
- mixed v1 + v2 structural directives in one document;
- any malformed directive that would otherwise be silently interpreted as a
  different ownership model.

### 2.3 v2 structure index

Extend the existing read-only Playable structure derivation with the smallest
v2 index that can address:

```text
Beat
  id
  kind
  document position/order projection

Scene
  id
  parent Beat

Decision / choice
  id
  parent Beat
  optional Scene association

Option
  id
  parent Decision
```

The index is a derivation over the admitted document. It does not become a new
durable authority, Save policy, database, or Runtime state store.

Document order authority remains the exact bound revision bytes. If the index
carries ordering for projection convenience, it is derived from those bytes and
must not create an independently mutable order authority.

### 2.4 v2 manifest seal / replay

Implement `dmb_play_run_reference_manifest_v2` per the reviewed design:

```text
run_id
playable_artifact_id
playable_revision
playable_content_sha256
sealed_at
beats:    [{ beat_id, beat_kind }]
scenes:   [{ scene_id, beat_id }]
choices:  [{ choice_id, beat_id, scene_id? }]
options:  [{ option_id, choice_id }]
edges:    [{ option_id, effect, target_kind, target_id }]
```

Rules:

- seal only from the exact still-current Run-bound revision/SHA;
- fail closed if the workspace has advanced before first seal;
- replay from the immutable sidecar without consulting current workspace state;
- arrays are membership/inspection carriers, not a second document-order
  authority;
- all transition edges are sealed for the Run revision;
- unknown manifest schema versions fail closed.

### 2.5 Frontend manifest contract

`apps/live-control-ui/src/api/types.ts` must truthfully represent the wire:

```text
PlayRunReferenceManifestV1
PlayRunReferenceManifestV2
PlayRunReferenceManifest = V1 | V2
```

with `schema_version` as the discriminator.

Frozen constraints:

- do not silently widen the existing v1 schema literal;
- do not use `as any` to cross the boundary;
- do not create one optional-everything interface;
- existing v1 consumers explicitly narrow and retain v1 semantics;
- `getPlayRunReferenceManifest()` can truthfully carry either response version
  without pretending v2 is v1.

### 2.6 Rollout gate — v2 is sealed but not READY

BF1 does **not** land v2 Runtime position semantics.

Keep the gate at the boundary that owns actual Play readiness:

- create+seal may return its existing Run-record `outcome: "ready"`;
- that is not native Play READY;
- `nativeRunbookProjection` remains v1-only for manifest admission in BF1;
- a created-and-sealed v2 Run must be refused by native Runbook admission;
- BF2 later seeds `currentBeatId` and extends native admission to v2;
- v1 create/seal/admit/project remains unchanged.

Evidence must exercise native admission directly. A helper/service test that
only proves v2 manifest creation does not prove the rollout gate.

---

## 3. Temporal/tick exploration boundary

The post-#627 exploration clarified a useful adjacent invariant but does not
change BF1 scope.

For BF1:

- Beat is a **narrative frame**, not a transaction tick;
- `run_revision` remains the existing Runtime transaction/revision identity;
- BF1 must not change when or why `run_revision` advances;
- no Run history, JSONL ledger, event stream, `last_tick`, transaction point
  reference, global tick, or kernel temporal contract is introduced;
- manifest `sealed_at` remains ordinary seal metadata and must not be promoted
  into fictional occurrence/valid time;
- no TL00 `TemporalEnvelopeV1` change is required;
- if BF1 evidence unexpectedly proves a temporal requirement, stop and hand it
  back as a separate capability rather than absorbing it.

The exploration remains useful review context because it reinforces the same
rule as v2 relevance: **do not give derivable state an independent clock.**

---

## 4. Runtime/state isolation

Source isolation is not runtime isolation.

BF1 tests create/inspect Runs, workspace snapshots, and manifests. Automated
verification must use test/temp roots and must not point at the operator's live
C2S27 `out/runtime/play` store.

Rules:

- no destructive cleanup of historical live Runs;
- no manual test that mutates the real active-Run pointer;
- no second backend instance against the same live state merely to prove BF1;
- if an interactive smoke check is useful, use an isolated temporary state root
  and separate port;
- v2 test Runs may remain intentionally non-READY, but test cleanup is confined
  to the isolated test root.

The real C2S27 store is evidence, not a disposable fixture.

---

## 5. Exclusive write lease

HANDOFF §5 is the lane's exclusive expected write set.

### 5.1 Production + focused test lease

| Area | Paths |
|---|---|
| v2 grammar parse/serialize | `apps/live-control-ui/src/tiptap/extensions/SemanticMarkdownPaste.ts`, `apps/live-control-ui/src/tiptap/extensions/SemanticMarkdownPaste.test.ts`, `apps/live-control-ui/src/tiptap/extensions/PlayableElementHeadingAttributes.ts` |
| Playable identity | `apps/live-control-ui/src/tiptap/playable/playableElementIdentity.ts`, `apps/live-control-ui/src/tiptap/playable/playableChoiceOptionIdentity.test.ts`, `apps/live-control-ui/src/tiptap/playable/playableChoiceOptionClipboard.test.tsx` |
| v2 structure index | `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.ts`, `apps/live-control-ui/src/tiptap/playable/playableStructureIndex.test.ts` |
| Runbook descriptor / admission | `apps/live-control-ui/src/tiptap/descriptors/tiptapRunbookDescriptors.ts`, `apps/live-control-ui/src/tiptap/descriptors/tiptapRunbookDescriptors.test.ts`, `apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts` |
| Choice authoring integration test | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.playableChoice.test.tsx` |
| Native admission gate | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`, `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` |
| Client manifest type contract | `apps/live-control-ui/src/api/types.ts` |
| v2 manifest service | `apps/live_control_server/services/play_run_reference_manifest.py` |
| Run creation / admission routes | `apps/live_control_server/routes/play_runs.py` |
| Run registry compatibility / gate seam | `apps/live_control_server/services/play_run_registry.py` |
| Backend tests | `tests/test_play_run_reference_manifest.py`, `tests/test_live_play_run_reference_manifest.py`, `tests/test_live_play_runs.py` |

### 5.2 Backward-looking #627 state-authority sync lease

These paths may change only to record already-completed PR #627 truth and make
BF1 the current in-flight Play structural slice:

| Authority | Canonical path | Mirror / paired path |
|---|---|---|
| completed predecessor handoff | `Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit-design.md` | none |
| Play sequence / hoist roadmap | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` |
| CON-READY product roadmap | `Docs/Roadmaps/ROADMAP-con-ready.md` | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` |
| CON-READY steward anchor | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` |
| design-agent source manifest | `Docs/Design/INDEX-design-agent-source-set.md` | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` |
| export capture basis | `Docs/Sources/design-agent/README.md` | none |

State-sync edits must preserve byte identity for every canonical/mirror pair.
Do not churn stable architecture/design prose merely because #627 merged.
`DESIGN-play-current-moment-cockpit.md`, its export mirror, the approved target,
and the tick exploration do not need content changes unless BF1 evidence
actually falsifies a design claim.

### 5.3 Living-roadmap ledger write

The BF1 implementation may append/update the required evidence disposition in:

- `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`;
- its byte-identical `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` mirror.

That row names the **implementation/evidence head**, not the later bookkeeping
SHA created by the roadmap write.

### 5.4 Bounded discovery exception

If one listed production concern is cleaner as a **new module**, the worker may
create a new sibling file inside the same directory as the listed owner.

This exception permits new sibling modules/tests; it does **not** permit editing
arbitrary existing sibling files. If BF1 needs an existing path not named
above, stop and request a lease amendment with:

```text
needed path
why the current owner cannot satisfy the contract without it
whether the seam can be split
whether another active lane owns it
```

### 5.5 Explicitly prohibited paths / domains

No changes to:

- Runtime progress/rebase services (`play_run_progress*`, `play_run_rebase*`);
- Play surface presentation/components/styles outside the two explicitly leased
  `nativeRunbookProjection` gate files;
- Plan surface UI;
- Combat code/state;
- migration/conversion tooling;
- TL00/TL01 temporal contracts or graph temporal modules;
- active-Run pointer semantics;
- global theme/AppChrome;
- lockfiles/root config/generated schemas unless separately handed back and
  leased;
- unrelated documentation authorities.

---

## 6. Verification and evidence contract

### 6.1 Focused backend evidence

Prove at minimum:

1. valid v2 manifest seal from the exact bound revision;
2. v2 immutable replay without consulting current workspace state;
3. workspace-advanced first-seal refusal;
4. duplicate/unknown/bad-parent/bad-edge validation failures;
5. unknown manifest schema failure;
6. v1 manifest behavior remains unchanged;
7. Run creation can truthfully coexist with v2 manifest sealing without
   changing Runtime progress semantics;
8. no BF1 path changes `run_revision` behavior.

### 6.2 Focused frontend evidence

Prove at minimum:

1. v2 parse → TipTap edit → serialize → committed reload round trip;
2. stable Beat/Scene/Decision/Option identity through title/prose rename;
3. Scene and Decision are H3 Beat-owned siblings and remain distinguishable;
4. optional Decision→Scene association validates only inside the same Beat;
5. `beat_kind` round trips;
6. activates/suppresses edges round trip and fail closed on invalid targets;
7. fenced-code literal behavior;
8. D2 ordinary-heading termination behavior;
9. mixed v1/v2 structural directives fail closed;
10. v1/v2 manifest client discrimination is explicit and type-safe;
11. native admission accepts the existing v1 shape and refuses a sealed v2
    manifest, proving no READY v2 cockpit is reachable in BF1.

### 6.3 Representative material proof

Include at least one representative document shaped like the approved C2S27
interaction model, with:

```text
Runbook
  Beat A (spine)
    Scene A1
    Decision A → Option activates Beat B
  Beat B (optional or spine)
    Scene B1
  Beat C (interrupt)
```

The proof should demonstrate ownership, association, edge validation, stable IDs,
and round trip together. Do not use a fixture whose only purpose is exercising
one directive at a time as the sole end-to-end evidence.

This is **structural evidence**, not a claim that Play is table-ready.

### 6.4 Build / static verification

Run the repository-standard focused frontend checks covering changed files,
plus:

- frontend typecheck;
- frontend production build;
- focused backend tests;
- `git diff --check`;
- changed-path verification against §5;
- canonical/mirror byte equality for every state-sync pair.

If a broad unrelated suite is red, report it separately with evidence that the
failure is outside BF1's changed boundary. Do not hide it and do not claim CI
that GitHub does not expose.

### 6.5 Roadmap review

Before final review, answer:

> **Did BF1 implementation/evidence change the ownership, sequence, hoist
> posture, successor boundary, or assumptions in the Playable hoist roadmap?**

Record exactly one:

```text
ROADMAP_REVIEW — UPDATED
<evidence and changed claims>
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
<why BF1 evidence still supports the reviewed sequence>
```

Explicitly reconsider—but do not assume—the tick exploration. BF1 may note
that no cross-domain temporal primitive was needed. It must not promote one
without a separate reviewed capability.

### 6.6 Final evidence ledger

The PR body/final review must name:

- implementation base SHA;
- implementation/evidence head SHA;
- exact changed paths;
- focused test commands/results;
- typecheck/build result;
- v1 regression/coexistence result;
- v2 native-admission blocked result;
- representative-material result;
- mirror-integrity result;
- roadmap disposition;
- any unrelated failures not claimed as BF1 evidence.

No screenshot requirement: BF1 intentionally ships no new presentation.

---

## 7. Review contract

One exact distinct head receives one formal reviewer judgment
(PASS / REQUEST-CHANGES-equivalent via COMMENT when GitHub blocks formal state
on the same account). Any repair commit creates a new head and another review
cycle.

The reviewer must independently verify:

- implementation base and current `main` relationship;
- all changed paths are inside §5;
- the #627 predecessor sync is backward-looking and truthful;
- the design contract was implemented without reopening frozen structure;
- no §5.5 prohibited domain shipped;
- the v2 rollout gate is proved at native admission, not inferred;
- v1 behavior remains intact;
- no Runtime tick/ledger/global temporal scope was smuggled into BF1;
- representative structural evidence is meaningful;
- roadmap disposition reflects actual BF1 evidence;
- no passing judgment is issued for a head different from the exact reviewed
  SHA.

A formal PASS on the exact final head is required before merge.

---

## 8. Post-merge successor posture

BF1 does **not** pre-authorize the next implementation.

After BF1 merges:

1. re-anchor current `main` and record BF1 completion through the next
   consuming implementation's backward-looking state sync;
2. read BF1 evidence against the reviewed cockpit design and living roadmap;
3. choose between:
   - **BF2** — Runtime current-position v2 + derived relevance; or
   - **BF4** — Plan Beat-first authoring composition, if BF1 grammar evidence
     makes it independently safe to proceed in parallel;
4. BF3 cockpit projection still requires BF2;
5. Lane B Combat durability remains separately sequenced;
6. the tick-ledger exploration remains a future evidence-gated capability,
   not an automatic BF2 adjunct.

Do not dispatch a successor merely because the design document listed an
order. Evidence from BF1 gets the next vote.
