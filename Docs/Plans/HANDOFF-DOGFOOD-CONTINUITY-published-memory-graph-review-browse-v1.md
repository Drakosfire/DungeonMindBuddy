# HANDOFF — DOGFOOD-CONTINUITY: published-memory Graph Review browse authority v1

**Created:** 2026-09-17  
**Status:** ACTIVE — redesign/reimplementation of the successful #732 dogfood objectives; existing PR #732 is the one authorized serial PR  
**Canonical path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY / Gate C operator dogfood / Graph Review browse authority`  
**Direction:** DESIGN → CODE → REVIEW → HUMAN DOGFOOD  
**Design authority base:** `main@9e739057540e52e763ba9fc6a62d2f1ef5ac2f96` — PR #731 merged  
**Dogfood spike:** PR #732 @ `dd4db027994f326af4434d2c0dd74f18abbb2509`  
**Spike formal review:** Cycle 1 HOLD, review `5242516505`  
**Spike disposition:** behavior/objectives are accepted empirical dogfood evidence; implementation is disposable and is not authority  
**PR topology:** `serial`  
**Authorized PR:** existing PR **#732 only**  
**Authorized branch:** `dogfood/graph-review-recap-campaign-session`  
**Authorized PR title after rebase:** `DOGFOOD-CONTINUITY: make published campaign memory the Graph Review browse authority`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Sequencing authority: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Readiness doctrine: [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md).

---

## §0 Why this slice exists

The infrastructure sequence reached a point where fresh recap writes, graph identity round-trip, evidence, and digest-verified recap source reads all work. PR #731 merged the remaining source-read continuity repair.

The next obstacle was not graph correctness. It was the **ordinary human product path**.

During real dogfood, PR #732 changed Graph Review so the operator could:

1. choose a campaign and focus session directly;
2. read the published recap without first choosing an ExtractionRun/catalog row;
3. click a graph mention and see the complete durable World object with useful relationship/origin prose;
4. switch C1/C2 and sessions without a separate “Load recap” workflow;
5. avoid false World Graph campaign-mismatch warnings on legitimate cross-campaign world projections.

With those behaviors in place, the operator was able to dogfood the campaign and reported the experience as satisfactory.

That is strong product evidence.

It is **not** evidence that the current #732 implementation is the right architecture. Review found that its browse selection and Graph Review authoring/run state can diverge, and that published recap browsing still waits on the ExtractionRun catalog before mounting.

Therefore:

> **Preserve the dogfood behavior. Rebuild the authority model intentionally. Do not preserve the spike code merely because it unlocked the workflow.**

---

## §1 Product model — two authorities, never one ambiguous state

Graph Review currently carries two conceptually different jobs. This slice must make them explicit.

### 1.1 Published-memory browse authority — ordinary/default mode

Ordinary Graph Review browsing is governed by:

```text
world_id
campaign_id
focus session
revision/head policy
admissibility
```

Its source is the **published World Graph**, not an ExtractionRun.

The ordinary operator workflow is:

```text
open Graph Review
→ select Campaign
→ select Focus session
→ read published recap
→ click graph mention
→ inspect complete durable World object
→ follow relationships / provenance
→ switch campaign or session
```

This mode MUST NOT require:

- an ExtractionRun catalog row;
- a run id;
- “Load recap”;
- an exact-run review package;
- gold/eval data;
- an ingest-run checkpoint;
- a hidden persisted run selection.

### 1.2 Write/author authority — explicit mode only

Anything that can author, prepare, confirm, promote, or otherwise write graph state must have an explicit write-capable authority binding.

Examples include:

- exact-run extract/promote review;
- authored proposal/draft work that truly requires a source/run binding;
- confirmation of governed writes.

A browse selection is **not** enough authority to write.

The product must never infer:

```text
visible published recap
therefore
some stale/default ExtractionRun is safe to author against
```

If Author Node or another write-capable tool requires an ExtractionRun/source binding, it must either:

1. already have an explicit valid binding; or
2. truthfully explain that authoring requires entering/creating an authoring context.

It must not silently bind to a persisted/default catalog run.

### 1.3 Exact-run mode remains separate

An explicit exact-run handoff such as:

```text
extractionRunId + sourceArtifactId
```

remains authoritative for the extract/promote review workflow.

Exact-run mode may temporarily replace the ordinary browse presentation because the operator explicitly entered a different authority context.

Campaign/session browsing must not destroy or mutate exact-run authority implicitly.

---

## §2 Merge-ready invariants

### Invariant A — browse authority is campaign/session World memory

> **On an ordinary Graph Review visit, Campaign + Focus session select the published World Graph recap directly. No ExtractionRun selection is required to display or explore it.**

Representative URL:

```text
/ingest?campaign=longmont-c2&session=session-27
```

must be sufficient to select the published-memory browse context.

### Invariant B — browse mounts independently of the ExtractionRun catalog

> **Failure, latency, emptiness, or absence of the ExtractionRun catalog does not block a valid published recap from loading.**

Catalog state may still support diagnostics or explicit authoring workflows, but it is not the ordinary recap-reader gate.

### Invariant C — visible browse state and World Graph lens agree

Campaign/session selection must drive one coherent browse context:

```text
Recap projection
World Graph lens
complete-object reads
relationship/object inspection
URL state
```

A single-campaign Ingest selection must remain campaign-scoped.

A legitimate world-union projection may omit single-campaign identity without producing a false mismatch.

### Invariant D — mention inspection uses complete durable objects

> **Clicking a published recap graph mention opens the complete World object at the same World/campaign/revision/focus context, not merely the thin recap projection stub.**

Relationship rows may show available origin/source prose or excerpts from the complete-object result.

The object viewer must preserve the exact revision returned by the recap projection unless the user explicitly changes context.

### Invariant E — browsing cannot silently acquire write authority

> **The presence of a published recap on screen never causes Author Node or another write-capable workflow to bind to an unrelated/stale/default ExtractionRun.**

When no explicit authoring authority exists:

- browsing remains fully usable;
- write-capable controls are hidden, disabled, or transition into an explicit authoring-entry flow;
- no mutation API is invoked.

### Invariant F — exact-run review still works

Explicit exact-run deep links must continue to load the exact source/run review path, including identity checks and fail-closed behavior.

Ordinary browsing must not weaken exact-run semantics.

---

## §3 Accepted dogfood objectives from #732

These behaviors are product requirements for this slice.

### O1 — Campaign + Focus session are the ordinary recap controls

The operator should not need to understand extraction catalogs to browse campaign memory.

Campaign/session controls should be visible while loading, empty, and ready so the operator can change context without escaping the surface.

Changing them updates the URL deterministically.

For ordinary Ingest/Graph Review browsing, a bare campaign selection means that campaign, not a hidden C1+C2 union.

### O2 — no ordinary “Load recap” ceremony

The old “choose campaign → session → run → Load” interaction is not the browse model.

Do not restore it for ordinary published-memory browsing.

If run selection remains useful for exact-run review, diagnostics, or authored workflows, surface it only in that explicit context.

### O3 — mention click gives useful object detail

A mention click should feel like exploring campaign memory:

```text
mention
→ complete World object
→ relationships
→ source/origin context when available
→ continue/follow related durable objects
```

Do not regress to a thin projection card that omits available complete-object context.

### O4 — cross-campaign world projection is not a false error

When `scopeMode=world` represents a C1+C2 union, a response with no single campaign identity is valid.

Campaign identity verification must remain strict for `scopeMode=campaign`.

Do not weaken world/campaign/revision verification generally to make this pass.

### O5 — refresh/deep-link continuity

A browser refresh on:

```text
/ingest?campaign=<campaign>&session=<session>
```

returns to the same published-memory browse context without restoring an unrelated run from local/persisted state.

### O6 — successful dogfood remains simple

The target subjective workflow is intentionally boring:

```text
pick campaign/session
read recap
click names/things
explore what the graph knows
follow provenance when useful
```

Do not reintroduce infrastructure concepts into the default interaction unless the operator asks to author/promote/debug.

---

## §4 Required authority state design

Before editing production code, document the state ownership you will implement.

At minimum distinguish these concepts in code, even if the exact type names differ:

```ts
PublishedMemoryBrowseContext {
  worldId
  campaignId
  sessionId
  revisionPin/head policy
  admissibility
}

GraphReviewWriteAuthority =
  | ExactRunAuthority
  | ExplicitAuthoringAuthority
  | null
```

The critical rule is:

```text
PublishedMemoryBrowseContext != GraphReviewWriteAuthority
```

Do not use one nullable “selection” object that sometimes means browse state and sometimes means mutation authority.

### 4.1 Source of truth

For ordinary browse context:

1. explicit URL campaign/session;
2. product context/default campaign/session when URL is absent;
3. user picker changes, persisted back into the URL.

Do not use persisted ExtractionRun selection as browse truth.

### 4.2 Exact-run precedence

If an explicit exact-run handoff is present and valid, exact-run authority wins that workflow.

If it is invalid, fail closed with an exact-run error. Do not silently degrade into a similarly named campaign/session browse context while preserving write controls.

### 4.3 Authoring entry from browse

This slice does not need to invent a new graph-writing workflow.

If the existing Author Node workflow cannot operate without a run/source binding, preserve browsing and make the missing authoring authority explicit.

Acceptable outcomes include:

- hide Author Node in browse-only mode;
- show it disabled with “Authoring requires an explicit source/run context”;
- provide an existing explicit handoff into authoring if one already exists and is correctly bound.

Unacceptable outcome:

- derive/write against whichever catalog run happens to correspond to the visible session.

---

## §5 Implementation strategy

The #732 spike may be mined for ideas and tests, but it is not the implementation baseline.

Worker instructions:

1. rebase/update PR #732 onto the `main` commit containing this handoff;
2. treat `dd4db027994f326af4434d2c0dd74f18abbb2509` as disposable spike evidence;
3. preserve or rewrite individual changes only when they fit §§1–4;
4. prefer the smallest coherent architecture over retaining the 25-file diff;
5. do not delete legacy components merely because the new browse path no longer uses them; cleanup can follow separately unless deletion is necessary for correctness.

The reviewer will judge invariants, not similarity to the spike.

---

## §6 Expected write lease

This is the expected implementation surface. The worker may use a strict subset.

### Core production paths

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | separate ordinary browse authority from exact-run/write authority; remove catalog as browse gate |
| MODIFY if needed | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeader.tsx` | chrome appropriate to browse vs exact-run modes |
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx` | Campaign/Focus-session published-memory controls + URL continuity |
| MODIFY | `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx` | complete-object inspection from mention clicks at exact recap revision |
| MODIFY | `apps/live-control-ui/src/graphLens/sessionCampaignContext.ts` | Ingest campaign semantics and browse lens consistency |
| MODIFY if required | `apps/live-control-ui/src/worldGraph/verifyWorldGraphProjectionResponse.ts` | accept campaignless world-union snapshot while preserving campaign-scope strictness |
| MODIFY if required | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNodeHost.tsx` | make write-authority requirement explicit |
| MODIFY if required | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorNodePanel.tsx` | fail closed / truthful browse-only authoring state |

### Focused tests

The corresponding existing tests for those modules may be modified. Prefer focused coverage in:

```text
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx
apps/live-control-ui/src/graphLens/sessionCampaignContext.test.ts
apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.test.tsx
apps/live-control-ui/src/worldGraph/verifyWorldGraphProjectionResponse.test.ts
```

One additional directly adjacent Graph Review test file is allowed when needed to prove the browse/write authority split.

### Durable report

CREATE:

`Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`

The report must state which #732 spike ideas were kept, redesigned, or discarded and why.

### Out of scope

Do not modify:

- backend World Graph semantics;
- recap extraction/admission/write contracts;
- DungeonMind dependency/pin;
- candidate replay/evaluation runners;
- benchmark gold;
- Agent/Hermes;
- Play/Build behavior except through already-shared components;
- source/corpus bytes;
- historical/replay databases.

Do not mass-delete Graph Review catalog/run components in this slice unless a deletion is required for correctness. Unused cleanup is a successor concern.

If implementation proves one directly adjacent UI state module must change outside this lease, stop and return the exact path/reason for steward lease expansion.

---

## §7 Required regressions

At minimum prove all of the following.

### Browse path

1. Fresh ordinary `/ingest?campaign=longmont-c2&session=session-27` mounts the published recap without selecting a run.
2. Published recap still mounts when ExtractionRun catalog is slow, empty, or unavailable.
3. Campaign picker switches C1↔C2 and updates recap + World Graph lens together.
4. Focus-session picker changes the recap and URL without a Load action.
5. Refresh restores the selected campaign/session browse context.
6. A stale persisted run selection does not override visible browse campaign/session.

### Object exploration

7. Clicking a recap mention requests complete-object using the recap response's exact World/revision and selected campaign/focus.
8. Complete-object relationship/origin prose is visible when returned.
9. Clicking a related durable object does not fall back to a stale projection/run context.

### Scope verification

10. Ingest bare `?campaign=longmont-c1` resolves to campaign scope.
11. Campaign-scoped response with a different campaign still fails closed.
12. World-scope response may omit single campaign identity.
13. World-scope response claiming a contradictory nonempty campaign still fails closed unless the product contract explicitly says otherwise.

### Write-authority separation

14. Browse-only mode has no implicit `liveRun`/write authority.
15. Opening Author Node in browse-only mode cannot invoke prepare/confirm/write APIs against a stale/default run.
16. If Author Node requires explicit authority, the UI communicates that truthfully.
17. Explicit exact-run handoff still loads exact-run review and does not silently become browse authority.
18. Invalid exact-run identity still fails closed.

---

## §8 Manual dogfood acceptance

After deterministic tests are green, reproduce the behavior that made the spike useful.

Use the operator's real local campaign World.

Manual witness:

1. Open Graph Review normally.
2. Select Campaign 2 and the latest useful session.
3. Read the recap without any ExtractionRun/load ceremony.
4. Click several graph mentions, including an object with useful related/origin prose.
5. Follow at least one relationship.
6. Switch to Campaign 1 and another session.
7. Refresh.
8. Return to Campaign 2.
9. Verify no false World Graph campaign mismatch appears.
10. Confirm browsing remains useful without entering authoring/run mode.

Then, separately:

11. exercise an explicit exact-run handoff and verify its write/review authority is still intact;
12. from ordinary browse, verify write-capable authoring cannot silently attach to stale run state.

Record the operator verdict verbatim enough to distinguish:

```text
workflow usable
vs
workflow technically renders
```

---

## §9 Acceptance labels

The PR may claim:

```text
PUBLISHED-MEMORY GRAPH REVIEW BROWSE AUTHORITY = PASS
GRAPH REVIEW BROWSE/WRITE AUTHORITY SEPARATION = PASS
```

After the post-implementation human witness succeeds, steward may advance:

```text
OPERATOR DOGFOOD = PASS
```

for this campaign-memory exploration workflow.

This slice does not establish:

```text
SEMANTIC COVERAGE = PASS
AGENT ANSWERABILITY = PASS
SEMANTIC MODEL SELECTION = PASS
```

Those remain downstream.

---

## §10 PR #732 instructions

PR #732 is the only authorized implementation PR.

Before implementation:

1. update/rebase the branch onto the `main` commit that contains this handoff;
2. update the PR title to:
   `DOGFOOD-CONTINUITY: make published campaign memory the Graph Review browse authority`;
3. treat Review Cycle 1 on `dd4db027994f326af4434d2c0dd74f18abbb2509` as a HOLD against the spike implementation, not against these product objectives;
4. replace any amount of spike code necessary;
5. request a new formal review only on a distinct new head SHA.

Do not open another PR.

---

## §11 What happens after this slice

If the intentional implementation reproduces the successful dogfood experience and the authority split is sound:

1. merge;
2. steward state sync / re-anchor;
3. record Gate C operator dogfood PASS for campaign-memory exploration;
4. return to the fixed 16-question C1S1–10 semantic gauntlet against the appropriate provenance-correct historical revision;
5. repair semantic failures at the earliest A/B/C/E boundary before Agent tuning.

The point of this slice is to finish the transition from:

```text
the graph machinery works
```

to:

```text
a human can simply use the campaign memory
```

without smuggling extraction/debug authority into the ordinary product experience.
