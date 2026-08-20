# ROADMAP — Playable Architecture → Shared Buddy Primitives → DungeonMind Kernel

**Status:** ACTIVE DESIGN ROADMAP — evidence-driven; review on every implementation PR
**Date:** 2026-08-15
**Scope:** DungeonMindBuddy Playable/Play implementation, internal hoisting, and evidence-driven promotion into DungeonMind / DungeonMindDnD

## 0. North star

The canonical Playable design should now move through a deliberate graduation path:

```text
DOGFOOD / PLAY DOMAIN
prove the GM interaction with real material

        ↓ repeated invariant

DUNGEONMINDBUDDY SHARED PRIMITIVE
hoist product-neutral editor/projection/work-object behavior

        ↓ second-system pressure + governance need

DUNGEONMIND KERNEL OR PROFILE
hoist only the authority/context semantics that must be consistent across consumers
```

The central architectural rule is:

> **DungeonMind should learn about governed operator-authored context, exact identity/revision/provenance, and capability-bounded adoption. It should not learn what a Beat, Scene, Play Object Sheet, or Combat panel is.**

## 1. Ownership model

| Concern | Long-term owner | Hoist posture |
|---|---|---|
| Runbook / Scene / Beat / Consequence semantics | DungeonMindBuddy Playable domain | Keep product-owned |
| Play Object Sheet layout and table prioritization | DungeonMindBuddy Play surface | Keep surface-owned |
| Run progress: current scene/beat, resolved beats, choices, scratch notes | DungeonMindBuddy Run runtime | Keep runtime-owned |
| Combat HP/initiative/conditions | Combat | Keep Combat-owned |
| Workspace document revision/save/CAS | Markdown Canvas / workspace document authority | Shared Buddy primitive |
| Stable address of a semantic element inside a work object | Shared Buddy Canvas/work-object layer first | Kernel may consume the ref later; should not own storage |
| Proposal apply/stale/dirty arbitration | Shared Buddy Canvas/work-object layer | Hoist inside Buddy before kernel consideration |
| Typed graph/source/mechanics references | Existing shared reference/projection seams | Reuse/extend, do not duplicate in Play |
| D&D world-object kinds and exact statblock mechanics attachments | `dungeonmind_dnd` semantic profile | Already profile territory; keep out of kernel core |
| World identity, revisions, evidence, context assembly, capability policy | DungeonMind | Kernel authority |
| Saved Playable material as governed agent context | DungeonMind candidate | Strong kernel candidate, but as generic external/operator context—not Runbook ontology |
| Playable → World promotion | DungeonMind contribution review/publication + profile adapter | Reuse existing kernel write path |
| Runtime → Playable adoption | Buddy proposal/adoption flow | Product-owned |
| Asset/map annotation | Shared Buddy asset/projection layer first | Kernel only if later required for evidence/retrieval |

## 2. Promotion test

A behavior is eligible to move **out of Play** only when all of these are true:

1. A real dogfood path has proved it useful.
2. A second consumer or surface needs the same invariant, or divergence would create an authority/safety problem.
3. The contract can be named without `Play`, `Plan`, `Beat`, `Scene`, `Canvas UI`, or adventure-specific vocabulary.
4. Moving it creates one clear owner instead of a second copy.
5. Its failure semantics can be strict and testable.
6. The lower layer does not need to own presentation or product workflow to enforce it.

For **DungeonMind kernel** promotion, add two more gates:

7. The concern is about knowledge/context identity, revisioning, provenance, admission, retrieval, capability policy, or governed durable adoption.
8. A game/system-specific semantic can remain in a profile package instead of entering kernel core.

If these are not true, keep the behavior in Buddy.


## 2.1 Roadmap maintenance contract

This roadmap is a **living design authority**, not a one-time planning artifact and not a mechanical status tracker.

Every implementation PR dispatched from this roadmap must deliberately re-read it against the evidence produced by that PR before the PR can receive a final passing review.

The required final-review question is:

> **Did this PR produce evidence that changes the ownership, sequence, hoist posture, successor boundary, or assumptions in this roadmap?**

A final passing review requires exactly one disposition:

```text
ROADMAP_REVIEW — UPDATED
<what evidence changed the design and which roadmap claims were edited>
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
<why the actual implementation/evidence still supports the current roadmap>
```

Rules:

1. The coding agent and reviewer both consider the roadmap; it is not a reviewer-only ceremony.
2. If the evidence changes a roadmap claim, the same implementation PR updates this file before passing review.
3. If the design still holds, do not churn architecture prose merely to record activity. Add one concise row to the review ledger below.
4. A roadmap edit must describe evidence from the current PR, not speculative future preference.
5. Changes to ownership or hoist posture are architecture changes and must remain consistent with the canonical Playable architecture and the owning lower-layer authority.
6. A Buddy PR may identify a DungeonMind/DungeonMindDnD successor but must not silently make a cross-repository contract change.
7. The roadmap's current phase / next-slice statement is mutable state authority and must agree with merged repository truth before the next dependent dispatch.
8. The ledger names the **implementation/evidence head** — the code commit whose tests and behavior drove the disposition. It must not chase the later bookkeeping SHA created by writing this ledger. The formal review handback records the exact reviewed PR head, which may be newer than the evidence head.

### Roadmap review ledger

| PR / evidence head | Phase | Review disposition | Design consequence | Next slice after merge |
|---|---|---|---|---|
| [#590](https://github.com/Drakosfire/DungeonMindBuddy/pull/590) evidence `3fe4a403` | P1 | ROADMAP_REVIEW — UPDATED. First use of the living-roadmap exact-head rule showed that requiring the same-PR ledger to name the final reviewed head cannot converge: the ledger write creates a new SHA. Distinguish implementation/evidence head (this row) from the reviewed head recorded in the review handback. P1A identity remains Play-owned semantic Markdown plus editor projection attrs; no second consumer needed the same invariant. | Keep Scene/Beat identity Play-owned. Do not hoist `WorkObjectElementRef` yet. Living-roadmap rows name evidence heads, not the ledger-write SHA. | P1B — Playable structure index and authored Choice identity, after this PR is reviewed |
| [#592](https://github.com/Drakosfire/DungeonMindBuddy/pull/592) evidence `c6435609` | P1B | ROADMAP_REVIEW — NO DESIGN CHANGE. The structure index is a deterministic Play-domain derivation over existing P1A root heading attrs. It creates no durable authority, Markdown grammar, Save policy, or second identity syntax. One Playable consumer can now resolve Scene/Beat membership by stable IDs, but that is not yet a second independent consumer of a shared element-ref invariant. | Keep Scene/Beat identity and the derived structure index Play-owned. Do not hoist `WorkObjectElementRef` yet. P1C still owns Choice/Option identity. | P1C — Choice / Option identity and minimal authored representation |
| [#594](https://github.com/Drakosfire/DungeonMindBuddy/pull/594) evidence `9aacb9f3` | P1C | ROADMAP_REVIEW — NO DESIGN CHANGE. Choice/Option are an additive Play-owned extension of the existing v1 marker family and P1B index. Parser/serializer/Save production code did not need Choice-specific branching. That is still one Playable consumer of element identity, not a second independent consumer of a generic ref. | Keep the four-kind identity family and derived index Play-owned. Do not hoist `WorkObjectElementRef` yet. P2 remains next. | P2 — separate Run runtime |
| [#596](https://github.com/Drakosfire/DungeonMindBuddy/pull/596) evidence `b1f93191` | P2A | ROADMAP_REVIEW — NO DESIGN CHANGE. The P2A implementation binds Runtime to the existing workspace document identity + revision + content digest authority and reuses existing generic lock/atomic-JSON seams. It did not require a server Playable parser, a second element-reference consumer, or a generic work-object revision type. Focused service/route/integrity tests at this evidence head passed, including Runbook-mutation linearization. | P2A_HOIST_OBSERVATION: exact Run→work-object revision/digest binding has not become useful outside Play Runtime; `WorkObjectRevisionRef` not yet justified; `WorkObjectElementRef` not yet justified; server-owned Playable element resolution was not needed in P2A and remains the concrete P2B design question; DungeonMind relevance discovered: none. | P2B — durable element-referenced Run progress |
| [#599](https://github.com/Drakosfire/DungeonMindBuddy/pull/599) evidence `66fd7f37` | P2B1 | ROADMAP_REVIEW — NO DESIGN CHANGE. The P2B1 implementation is a second Play-owned consumer of the existing P1 marker family: a private server scanner derives only canonical IDs and membership into an immutable Runtime sidecar. It did not store Markdown/titles/prose/order, mutate P2A Run records, invent a historical Playable archive, or require a generic work-object element ref. Cycle 1 repaired fence-interior literal treatment (`~~~` and variable-length backticks) and persisted Scene/Choice membership resolution without changing that posture. | P2B1_HOIST_OBSERVATION: server-side marker/reference resolution remained cleanly Play-owned; no independent non-Play consumer required the same element-ref contract; `WorkObjectRevisionRef` not yet justified; `WorkObjectElementRef` not yet justified; a historical Playable archive was not necessary; DungeonMind relevance discovered: none. | P2B2 — durable CAS Run progress against the sealed manifest |
| [#601](https://github.com/Drakosfire/DungeonMindBuddy/pull/601) evidence `8538409e` | P2B2 | ROADMAP_REVIEW — NO DESIGN CHANGE. The P2B2 implementation mutates one full progress snapshot inside the existing Play-owned Run JSON under `run_revision` CAS and admits every durable reference from the sealed P2B1 sidecar. It did not add a progress file/token, parse current Runbook bytes, auto-seal a missing manifest, or invent a generic runtime-state primitive. Cycle 1 required persisted `resolved_beat_ids` to fail closed when duplicate or unsorted rather than silently re-canonicalizing on reload. Focused service/route/predecessor tests at this evidence head passed, including concurrent CAS, response-loss replay, persisted-reference corruption, persisted canonical-beat shape, and legacy P2A records without `progress`. | P2B2_HOIST_OBSERVATION: Run-progress CAS has not become useful outside Play Runtime; no shared Buddy runtime-state primitive was required; no independent consumer required `WorkObjectRevisionRef` or `WorkObjectElementRef`; progress integrity used the Play-owned manifest rather than a generic cross-domain reference validator; DungeonMind relevance discovered: none. | P2C — explicit Run rebase/migration to a newer Playable revision |
| [#608](https://github.com/Drakosfire/DungeonMindBuddy/pull/608) evidence `9b6918d6` | P3C | ROADMAP_REVIEW — NO DESIGN CHANGE. P3C extracted surface-neutral exact Threat mechanics hydration/rendering (`useExactThreatMechanics`, `ThreatMechanicsPanel`) and composed it into a Play-owned object sheet without Combat or a new backend contract. Plan/Build keep `ThreatSheetProjection` as the compatibility wrapper. Living-roadmap dispatch authority remains P2C; P3A/P3B product sheets are still not merged. | P3C_HOIST_OBSERVATION: reused existing Threat query/hydration API; mechanics identity remains `(statblock_id, revision_id, definition_digest)`; no new DungeonMindDnD attachment semantic; surface-neutral read/render seam extracted; no Playable/Run persistence of mechanics; no active/default binding choice; no Combat mutation; P4 Add to Combat remains independently useful; generic WorkObject/Runtime/DungeonMind relevance: none. | P2C remains current dispatch; P4 remains the first Combat mutation after P3C is product-complete |
| [#612](https://github.com/Drakosfire/DungeonMindBuddy/pull/612) evidence `0299d6a6` | P2C | ROADMAP_REVIEW — NO DESIGN CHANGE. The P2C implementation rebases one Play-owned Run UUID onto a newer committed revision of the same Runbook artifact, preserving progress only when every durable reference remains admissible in a replacement P2B1-format manifest. It introduced one forward-only rebase intent to recover the Run+manifest pair and isolated non-rebase APIs while that intent remains. Cycle 1 required authoritative P2B2 source-progress integrity before migration, preserve-only proof of tampered intents, an explicit `rebased_from_run_revision` receipt rather than inferring completed replay from the shared CAS counter, and list isolation of orphan intents. It did not add ID mapping, a historical Playable archive, a second concurrency token, a generic multi-file transaction framework, or a DungeonMind contract. Focused service/route/predecessor tests at this evidence head passed, including preserve-only success, per-field 409 blockers, injected intent/manifest/run/cleanup failures, pending-intent 503 isolation, completed-replay pair integrity, in-process half-commit concealment, source-integrity rejection, tampered-intent fail-closed recovery, progress-vs-rebase replay distinction, and orphan-intent list isolation. | P2C_HOIST_OBSERVATION: the rebase intent remained a Play-owned recovery journal for one Run+manifest pair; the rebase receipt is a Play-owned replay identity on the existing Run record, not a generic transaction primitive; no independent non-Play consumer required a shared CAS/receipt type; `WorkObjectRevisionRef` not yet justified; `WorkObjectElementRef` not yet justified; a historical Playable archive was not necessary; DungeonMind relevance discovered: none. | After merge: P3 — native Play projections; current sequence stays P2C until post-merge state-authority sync |
| [#618](https://github.com/Drakosfire/DungeonMindBuddy/pull/618) evidence `196144bb` | P3A | ROADMAP_REVIEW — NO DESIGN CHANGE. Native `/play` reconstructs one exact Run-bound Runbook table deck from the persisted P2 Run, sealed P2B1 manifest, and matching committed workspace snapshot. Scene/Beat/Choice identity and authored bodies stay Play-owned P1 derivations; Runtime overlay and `run_revision` CAS stay Play-owned P2. Cycle 1 closed four implementation-boundary gaps without changing ownership: concurrent rebase must re-admit rather than overlay a new Run on old scenes; workspace admission carries P2B1 `active`/`committed`/`file_exists` predicates; blocked Play publishes surface identity without admitted campaign/document authority; Play stays in shared product nav. Shared AppChrome is reused; no second Projection host, AgentInteractionProvider, historical Runbook archive, graph-reference open, or backend schema was required. | P3A_HOIST_OBSERVATION: Native Runbook projection remains Play-owned. P1 stable element identity remains Play-owned. P2 Runtime remains Play-owned. shared AppChrome/Projection host remains reused rather than forked. WorkObjectElementRef remains not yet justified by an independent non-Play consumer. WorkObjectRevisionRef remains not yet justified. DungeonMind relevance discovered: none. | After merge: Start Run dogfood bridge, then Runbook briefing/instructions, then live dogfood/re-anchor. P3B remains designed but deferred. P4 remains the first Combat mutation |
| [#621](https://github.com/Drakosfire/DungeonMindBuddy/pull/621) evidence `8dc1bad2` | D1 | ROADMAP_REVIEW — NO DESIGN CHANGE. Start Run is a Play-owned UI consumer of the existing P2A create/replay and P2B1 seal/replay endpoints. One explicit attempt allocates one canonical Run UUID, sends the exact committed Runbook snapshot revision/SHA, and navigates to `/play?run=<uuid>` only after both authorities confirm. Unknown create/seal outcomes reconcile by exact GET; 409 never refreshes to latest; incomplete create-without-seal is truthful and has no delete/rebase. Cycle 1 restored the owning App `/play` composition proof: Existing Runs stay openable when Start Run discovery fails, and successful start enters the existing P3A READY deck at `/play?run=<uuid>`. No backend schema, start transaction, Plan authoring workflow, or new Playable grammar was required. | D1_HOIST_OBSERVATION: Start Run remained a Play-owned workflow over existing Run+manifest APIs. No generic start-transaction primitive was required. `WorkObjectRevisionRef` not yet justified. `WorkObjectElementRef` not yet justified. DungeonMind relevance discovered: none. | After merge: Play Runbook instructions (D2), then live dogfood/re-anchor. P3B remains designed but deferred. P4 remains the first Combat mutation |
| [#622](https://github.com/Drakosfire/DungeonMindBuddy/pull/622) evidence `b923117b` | D2 | ROADMAP_REVIEW — NO DESIGN CHANGE. Native `/play` now has two Play-owned projections of one P3A-admitted Runbook: the existing Table deck and a read-only full-document Runbook view that reuses `MarkdownEditorCore` with the exact imported TipTap document. Ordinary unmarked root H1/H2 terminate preceding playable body slices so later instructions stay visible in Runbook mode without becoming Scene/Beat identity. Mode switching is local, defaults to Table, writes no Runtime, and returns to the prior focused Beat. No briefing schema, heading-name ontology, backend parser, second Markdown import, or graph-reference open was required. | D2_HOIST_OBSERVATION: Full-document Runbook viewing remained a Play-owned projection of the already-admitted TipTap document. No generic document-view primitive or briefing persistence type was required. `WorkObjectRevisionRef` not yet justified. `WorkObjectElementRef` not yet justified. DungeonMind relevance discovered: none. | After merge: D3 C2 Session 27 native Play dogfood. P3B remains designed but **NON-DISPATCHABLE** until that dogfood report and a later re-anchor name it. P4 remains the first Combat mutation |

### Current sequence

Mutable workstream state after merged PR #622 / `62f7f9e`. Implementation PRs still add a ledger row; they do not rewrite this block except as post-merge state-authority sync. This PR selects the D4 current-Beat table stage; it does not mark that slice complete.

| Field | Current truth |
|---|---|
| Integration tip | `62f7f9e856327247b8677b4c951801e4c58a826c` — [PR #622](https://github.com/Drakosfire/DungeonMindBuddy/pull/622) merge of exact admitted Runbook view |
| Merged capability | P2 complete. P3A native `/play` table deck merged. D1 Start Run merged. D2 exact Runbook view merged. P3C landed early as a partial P3 sibling. |
| P2 status | **COMPLETE** — P2A/P2B1/P2B2/P2C merged |
| P3A status | **COMPLETE** — PR #618; evidence `196144bb`; reviewed head `a907e623`; merge `03252d51`; **3 review cycles** |
| D1 status | **COMPLETE** — PR #621; evidence `8dc1bad2`; reviewed head `11f5724f`; merge `a0e03bed`; **2 review cycles** |
| D2 status | **COMPLETE** — PR #622; evidence `b923117b`; reviewed head `c549611a`; merge `62f7f9e`; **1 review cycle** |
| D3 status | **DOGFOOD DECISION COMPLETE** — C2 Session 27 native Play READY wiring accepted; shipped three-column Table UX rejected as the table instrument |
| Next slice | current Beat table stage (this PR; not merged) |
| Next handoff | `Docs/Plans/HANDOFF-PLAY-current-beat-table-stage.md` |
| Named successor after D4 | Post-current-moment-deck re-anchor. P3B remains designed but **NON-DISPATCHABLE**. This PR does not select P3B, P4, or a Plan→Runbook bridge as next. |
| Hoist posture | Runtime remains DungeonMindBuddy Play-owned. Native Runbook projection remains Play-owned. D2 is a second Play-owned projection of the same admitted TipTap document, not a briefing schema or new element kind. `WorkObjectRevisionRef`, `WorkObjectElementRef`, and a generic transaction framework remain not yet justified without an independent non-Play consumer. |

P2 is complete. P3A is complete. D1 Start Run is complete. D2 exact Runbook view is complete. C2 Session 27 dogfood accepted the exact lifecycle wiring and rejected the native three-column Table presentation. The current work is making the current Beat the native Play table stage. P3B exact graph-reference opening remains designed but deferred until that deck lands and a later re-anchor names it. P4 remains the first Combat mutation. This is a sequencing update, not a stable architecture ownership change.

---

# 3. Delivery roadmap

## PHASE P0 — Re-anchor and freeze the graduation map

**Owner:** DESIGN / DOCUMENTS

Before implementation handoffs, treat the merged Playable architecture as the product authority and the existing DungeonMind architecture as kernel authority.

Record three explicit destinations for every new contract:

```text
PLAY DOMAIN
BUDDY SHARED
DUNGEONMIND / DUNGEONMIND-DND
```

**Exit:** no implementation PR needs to decide ownership ad hoc.

---

## PHASE P1 — Durable Playable work object

**Primary CON-READY target:** CR05 / CR-U11
**Owner:** DungeonMindBuddy Canvas + Playable domain

Build the smallest real Playable Artifact on existing workspace-document / Markdown Canvas authority.

Prove:

- exact durable work-object identity;
- exact revision/digest;
- stable Scene IDs;
- stable Beat IDs;
- stable Choice / Option IDs where runtime will reference them;
- `consequences` as the canonical outcome structure;
- save/reload;
- renaming prose/title does not change semantic identity.

Do **not** introduce a new datastore.

### P1 delivery decomposition

P1 is intentionally split so stable identity is proven before richer Playable structure depends on it.

#### P1A — Durable Scene / Beat identity grammar ← merged PR #590

Deliver one versioned semantic-Markdown identity convention for Scene and Beat headings and prove it survives:

- Markdown import;
- TipTap editing;
- title/text rename;
- reorder;
- semantic Markdown serialization;
- committed reload;
- malformed/orphan/duplicate identity failure without silent retargeting.

P1A does **not** implement Run runtime, choices/options, Play projections, legacy-runbook auto-migration, or DungeonMind contracts.

#### P1B — Playable structure index ← merged PR #592

After P1A, add the smallest consumer-facing structure needed to address Scenes/Beats by stable P1A IDs and document order. P1B is a read-only derived index: no new Markdown grammar, Save policy, persistence, or editor mutation.

P1B must re-open the hoist decision instead of assuming P1A's representation belongs in the shared Canvas layer.

Handoff: [`HANDOFF-PLAY-playable-structure-index.md`](../Plans/HANDOFF-PLAY-playable-structure-index.md).

#### P1C — Choice / Option identity and minimal authored representation ← merged PR #594

After P1B, add durable Choice/Option identity to the existing `dmb-playable-element:v1` family and extend the structure index with Scene→Choice→Option membership so P2 can later persist `choiceId → optionId` without labels or position as identity.

P1C must re-open the hoist decision. P1B did not prove a second independent consumer of generic element addressing.

Handoff: [`HANDOFF-PLAY-choice-option-identity.md`](../Plans/HANDOFF-PLAY-choice-option-identity.md).

### Hoist decision after P1

If stable semantic element identity is useful to both Play and agent/document mutation, hoist a neutral Buddy ref such as:

```text
WorkObjectElementRef
  documentId
  revision / digest
  elementId
```

The Canvas/workspace layer owns how this resolves. DungeonMind may later consume the reference but does not own the editor or storage.

**Not a kernel PR.**

---

## PHASE P2 — Separate Run runtime

**Primary CON-READY target:** CR05 / CR-U17 precursor
**Owner:** DungeonMindBuddy Play runtime

Implement persistent Run state bound to one explicit Playable revision:

```text
runId
playableArtifactId
playableRevisionId
currentSceneId
currentBeatId
resolvedBeatIds
choiceId → optionId
notesByElementId
linkedRuntimeHandles
```

Prove reload/restart and fail safely when a referenced element disappears in a newer Playable revision.

The live-control server does not currently own a canonical Playable structure resolver. P2A proved that exact Run→Playable binding can be established without one. P2B now has two separate durable concerns: freezing the minimum exact reference-admission facts for the bound revision and mutating progress under CAS. Those are split below so neither trusts current/latest Playable state after the Runbook advances.

### P2 delivery decomposition

#### P2A — Durable Run identity + exact Playable revision/digest binding ← merged PR #596

Create one Play Runtime authority: an opaque Run UUID bound to one admitted committed Runbook workspace-document identity + revision + content SHA. Persist outside authored workspace storage. Idempotent create replay. No element progress, no Playable parse, no UI.

Handoff: [`HANDOFF-PLAY-durable-run-binding.md`](../Plans/HANDOFF-PLAY-durable-run-binding.md).

#### P2B1 — Immutable Run-bound Playable reference manifest ← merged PR #599

For one existing P2A Run, seal one immutable Runtime sidecar derived from the **exact still-current bound Runbook revision/SHA**. The sidecar stores only canonical Scene/Beat/Choice/Option IDs and structural membership. It stores no Markdown, titles, prose, consequences, rendering order, progress, World/Source/Mechanics data, or migration state.

The first seal fails closed if the workspace has already advanced beyond the Run's bound revision. Once sealed, replay uses the immutable sidecar and does not consult current workspace state.

Handoff: [`HANDOFF-PLAY-run-reference-manifest.md`](../Plans/HANDOFF-PLAY-run-reference-manifest.md).

#### P2B2 — Durable CAS Run progress against the sealed manifest ← merged PR #601

After P2B1, persist current Scene/Beat, resolved Beats, `choiceId → optionId` selections, and notes. Every referenced ID must validate against the P2B1 manifest, and every mutation must use P2A `run_revision` as the compare-and-swap boundary. Do not add a second concurrency token.

P2B2 must not parse current Runbook bytes as a fallback and must not silently create/rebuild a missing manifest from a newer Playable revision.

Handoff: [`HANDOFF-PLAY-run-progress-cas.md`](../Plans/HANDOFF-PLAY-run-progress-cas.md).

#### P2C — Explicit preserve-only Run rebase to a newer Playable revision ← merged PR #612

After P2B2, explicitly move one Run UUID to a newer committed revision of the same Runbook artifact, preserving current progress only when every durable reference remains admissible in the target revision. Do not invent a mapping language, historical Playable archive, or second concurrency token.

Handoff: [`HANDOFF-PLAY-run-rebase.md`](../Plans/HANDOFF-PLAY-run-rebase.md).

`linkedRuntimeHandles` stays deferred until a real Combat/other runtime consumer requires it.

### Hoist decision after P2

Default disposition: **do not hoist to DungeonMind**.

Run position is product runtime state, just as Combat HP is Combat runtime state. Only revisit if another independent product needs the same generic runtime-state contract.

---

## PHASE P3 — Native Play projections

**Primary CON-READY target:** CR-U15 / CR-U16 preparation
**Owner:** DungeonMindBuddy Play + Surface Interaction Layer

Replace #578 campaign bridges with generic projections over real authorities:

```text
World + Source + Playable + Mechanics + small Runtime status
                     ↓
              Play Object Sheet
```

Build native:

- Run / Scene / Beat projection;
- NPC/location/item Play Object Sheets;
- Threat sheet using exact mechanics;
- reference opening through the shared Projection host;
- source/Advanced detail without losing table position.

Keep table ordering and presentation in Play.

### Buddy-shared hoist candidates

Hoist only repeated mechanics such as:

- generic graph/source/reference open behavior;
- projection composition helpers;
- common object-reference action wiring;
- reusable asset annotation rendering if Plan/Build also need it.

**Do not hoist Play Object Sheet section vocabulary into DungeonMind.**

---

## PHASE P4 — Threat → exact mechanics → Combat

**Primary CON-READY target:** CR06 / CR-U13 / CR-U14
**Owner:** DungeonMindDnD mechanics identity + Buddy Play/Combat action

Use the already-established profile-side model:

```text
world object
→ exact D&D world-object mechanics binding
→ exact statblock attachment/revision
→ explicit Add to Combat
→ Combat-owned mutable state
```

The Play action may choose quantity/team/attachment explicitly. Never use first/latest/display-name selection.

### Hoist decision after P4

No new kernel-core combat schema.

DungeonMindDnD already owns D&D world-object and mechanics attachment semantics. `Add to Combat` remains a Buddy capability consuming those exact refs.

---

## PHASE P5 — Shared proposal/adoption seam in Buddy

**Primary CON-READY target:** CR-U11
**Owner:** Shared Markdown Canvas / Surface Interaction, with Play/Plan as consumers

Promote the #578 proposal experiment into a neutral work-object mutation flow:

```text
proposal
→ exact target work object
→ exact base revision/digest
→ exact semantic element target when applicable
→ preview
→ explicit operator approval
→ Canvas mutation
→ ordinary Save
```

Centralize:

- stale-base rejection;
- dirty-edit rejection;
- document mismatch rejection;
- stable element targeting;
- apply result and local dirty state.

Keep domain payloads extensible. `Read Aloud`, `GM Note`, `Consequence`, etc. may be Playable proposal kinds without becoming Canvas core vocabulary.

### Hoist decision after P5

This should be **Buddy-shared first**.

DungeonMind already has `SuggestedAction` as a surface-offered, non-side-effecting response concept. Use that as the initial cross-boundary carrier. Only introduce a stricter kernel proposal envelope if a second product/client needs shared proposal exactness that `SuggestedAction.arguments` cannot safely express.

---

## PHASE K0 — DungeonMind Playable-context contract inventory

**Owner:** DOCUMENTS, cross-repo audit
**Repositories:** DungeonMindBuddy + DungeonMind

Before adding a kernel contract, inventory what already exists.

Specifically test whether the combination below can represent a saved Playable revision without lying about its standing:

```text
SurfaceContext.selected_document_ref / active_artifact_refs
+ SourceArtifactV2
+ SourceRevision
+ source_domain = prep
+ workspace_document_ref
+ review_state / authority / lineage
+ SemanticDocument provenance
```

Then inspect the actual Mind Turn context path.

Known pressure to verify: current deterministic context assembly is graph/evidence/anchor-centric; active external artifacts are not currently a first-class context input to that assembler.

**Required disposition:**

```text
K0_REUSE_EXISTING_CONTRACTS
```

or

```text
K0_MINIMAL_KERNEL_GAP — <exact missing generic contract>
```

Do not create `PlayableArtifact`, `Runbook`, `Scene`, or `Beat` classes in the kernel.

---

## PHASE K1 — Admit exact operator-authored context into Mind Turn

**Owner:** DungeonMind kernel, only if K0 proves the gap
**Primary CON-READY target:** CR-U12

The likely kernel capability is generic:

> Given an exact admitted external/operator-authored artifact revision referenced by surface context, DungeonMind may resolve, retrieve, budget, and assemble that material for the agent while preserving its authority/standing separately from World assertions.

Preferred shape:

```text
surface sends pointer(s)
→ kernel resolves exact artifact/revision
→ admission + visibility checks
→ optional exact-artifact semantic retrieval
→ context budgeting
→ agent context labels standing/provenance
```

The kernel should not receive caller-supplied filesystem paths or unpinned document bodies as authority.

### First design choice

Try to reuse `SourceArtifactV2` / `SourceRevision` as the provenance carrier before adding a parallel external-context identity family. It already supports:

- `SourceDomain.PREP`;
- opaque producer classification;
- workspace-document linkage;
- independent review state / evidentiary authority / access policy;
- exact source revision hashes.

If those axes cannot truthfully express operator-adopted context, add only the smallest generic standing/ref contract necessary.

### Exit proof

A GM asks:

> “What did I decide about Hesta during prep?”

DungeonMind answers from the exact saved Playable revision, while the response/agent state remains distinguishable from a World Graph assertion.

---

## PHASE K2 — Exact-artifact retrieval for Playable context

**Owner:** DungeonMind kernel retrieval/context assembly
**Depends on:** K1 and real dogfood showing whole-artifact injection is too large

Use the same discipline already applied to source follow-through:

```text
explicit admitted artifact
→ bounded exact-artifact retrieval
→ no ambient filesystem/corpus authority
```

The retrieval unit may be a semantic document/chunk derived from the exact Playable revision. Results must retain artifact/revision/element provenance and authority standing.

Do not build this merely because the architecture allows it. Build it only if the real Runbook is too large for bounded active-context injection.

---

## PHASE K3 — Proposal carrier graduation, only if needed

**Owner:** DungeonMind kernel + product adapter

Start by using existing `SuggestedAction` semantics: the kernel suggests; the surface offers; there is no silent side effect.

If repeated consumers prove `kind + arguments` is too weak, graduate a generic versioned proposal envelope containing only product-neutral exactness:

```text
target authority / capability
opaque target ref
base revision/digest
proposal schema id/version
proposal payload
provenance refs
```

The payload remains product/profile-owned. DungeonMind does not learn `GM Note` or `Beat` semantics.

The owning product still performs preview, approval, apply, and Save.

---

## PHASE K4 — Playable → World promotion through existing review authority

**Primary goal:** deliberate canonization without a second graph-write path
**Owners:** Buddy authoring UI → profile adapter → DungeonMind review/publication

Implement the user action:

```text
"Make this part of the world"
```

as:

```text
exact Playable revision/element
→ evidence/provenance record
→ profile-owned candidate assertion planning
→ explicit identity/assertion review
→ confirm_commit
→ existing DungeonMind finalized-review publication
→ new World Graph revision
```

The Playable artifact remains unchanged and remains provenance for the promoted claim.

This is where the Playable architecture should most strongly **reuse** the kernel rather than extending it.

Graph assertion metadata already separates campaign, visibility, epistemic standing, canon state, evidence, session refs, and fictional time. Use that authority; do not invent a Playable-specific graph mutation path.

---

## PHASE P6 — Runtime → Playable adoption

**Owner:** DungeonMindBuddy

After play, allow the GM to choose from runtime outcomes:

```text
keep in next prep
add to recap
promote to World
discard
```

`keep in next prep` uses the same proposal/adoption + Canvas Save seam from P5.

`promote to World` uses K4.

No automatic upward promotion.

### Kernel posture

Runtime may later be exposed as bounded **current-turn context** through surface pointers, but DungeonMind should not become the runtime database.

---

## PHASE P7 — Full one-shot dogfood and demolition

**Primary CON-READY target:** CR07 / CR-U15–U17

Run a real one-shot with no campaign-specific bridge code.

Must prove:

- durable Runbook/Scene/Beat identity;
- consequences and branching;
- saved Playable context used by Hermes;
- Play Object Sheets from real authorities;
- exact Threat mechanics;
- prepared and unexpected Add-to-Combat;
- runtime progress/notes survive restart;
- agent proposals require approval;
- source/world/playable/runtime distinctions remain truthful.

Then delete or retire:

- `ofConks*` play-object dictionaries;
- `ofConks*` beats dictionaries;
- local fake graph resolution;
- threat/statblock bridge maps;
- permanent dependency on legacy injected prep HTML.

---

## PHASE H1 — Post-dogfood hoist review

After at least one full real run—and preferably a second materially different adventure—perform a deliberate hoist audit.

### Strong kernel candidates

1. Exact external/operator-authored context admission.
2. Authority/standing-aware context assembly across World, source/evidence, operator prep, and bounded runtime observations.
3. Exact-artifact semantic retrieval constrained by an admitted artifact revision.
4. A stricter generic proposal envelope, **only if** multiple consumers require it.

### Strong Buddy-shared candidates

1. Stable work-object element refs.
2. Proposal apply / stale / dirty arbitration.
3. Generic typed-reference projection actions.
4. Asset + annotation identity if multiple surfaces use it.

### Keep product-owned unless new evidence appears

1. Runbook / Scene / Beat.
2. Consequence trigger/category UX.
3. Play Object Sheet layout/section vocabulary.
4. Run progress state.
5. Combat state and Add-to-Combat presentation.
6. Map interaction/legend behavior.
7. Play navigation and table ergonomics.

---

# 4. Kernel lessons from the Playable architecture

## Lesson A — Durable knowledge is not the only durable context

Playable Material proves a durable state category that is intentionally **not** World Graph truth but must still be queryable by the agent.

The kernel implication is not “add Runbooks to the graph.” It is:

> **Context assembly needs a governed representation of durable operator-authored context with exact revision/provenance and explicit standing.**

## Lesson B — Surface context should remain pointer-first

Buddy should publish exact selected document/artifact/run/object pointers. DungeonMind should resolve, retrieve, budget, and assemble context.

This preserves the kernel rule that surfaces do not assemble prompts or graph queries.

## Lesson C — Proposal and adoption are different states

A model output is a proposal. Approval changes the product work object. Saving makes it durable. Promotion to World is a separate reviewed kernel write.

This is the same governance instinct DungeonMind already applies to graph contributions.

## Lesson D — Promotion should create evidence, not erase provenance

When Playable material becomes World knowledge, the exact Playable revision should remain the evidence behind the new assertion.

The transition is:

```text
Playable intent
→ reviewed evidence-backed assertion
```

not:

```text
Playable row magically becomes graph row
```

## Lesson E — Domain semantics belong beside the domain

DungeonMindDnD already demonstrates the pattern: D&D world-object kinds and exact statblock mechanics attachment live in the semantic profile, while the kernel stays generic.

Use the same filter for future Play pressure:

- D&D semantic meaning → profile;
- product/table interaction → Buddy;
- generic knowledge/context/governance → kernel.

---

# 5. Recommended immediate sequence

```text
P1  durable Playable artifact + stable Scene/Beat/Choice identity
↓
P2  persistent Run state bound to exact Playable revision
↓
P3  native generic Play projections
↓
P4  exact Threat → Combat handoff
↓
P5  shared Buddy proposal/adoption seam
↓
K0  cross-repo Playable-context contract inventory
↓
K1  minimal kernel external/operator-context admission, if K0 proves needed
↓
K2  exact-artifact retrieval only if real context size requires it
↓
K4  Playable → World through existing review/publication authority
↓
P6  Runtime → Playable deliberate adoption
↓
P7  full one-shot dogfood + bridge demolition
↓
H1  evidence-based final hoist review
```

K3 (a stricter generic proposal envelope) is intentionally conditional and should be inserted only if P5 exposes a real multi-consumer contract gap.

## Final rule

> **Hoist authority, not vocabulary.**
>
> Keep the table model close to the table. Hoist exact identity, revisions, provenance, admission, context assembly, capability policy, and governed promotion only when the lower-level owner must be shared.