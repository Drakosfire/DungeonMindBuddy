# HANDOFF — MAGIC-D3 real Threat publication, discovery, hydration, and projection dogfood

**Created:** 2026-08-04
**Status:** ACTIVE OPERATOR DOGFOOD HANDOFF — execute one real end-to-end product proof; do not implement repairs during the run.
**Repository:** `Drakosfire/DungeonMindBuddy`
**Canonical handoff path:** `Docs/Plans/HANDOFF-magic-d3-threat-publication-query-projection-dogfood.md`
**Dispatch anchor:** `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e` — merge of PR `#504`, `statblock: implement exact Threat projection`
**Required report path:** `Docs/Reports/MAGIC-MOMENT-D3-<YYYY-MM-DD>.md`
**Mode:** live operator shepherd + skeptical product observer; not autonomous coding, not an implementation PR.

---

## §0 Capability decision

This handoff owns one independently useful outcome:

> Prove whether a GM can take one real accepted statblock revision through governed Threat publication, reload, semantic discovery, exact mechanics hydration, and compact/full projection while retaining trustworthy identity across failure, retry, and revision boundaries.

It does **not** own a new product capability. It owns evidence about the capability now merged across:

* `SBW09c2b` — governed commit, recovery, and verification, merged in PR `#491`;
* `SBW10a` — revision-pinned Threat query and exact mechanics hydration, merged in PR `#502`;
* `SBW10b` — exact Threat projection, merged in PR `#504`.

### Included

* current-main reanchor and reachability audit;
* one real accepted mechanics locator;
* one real publication attempt through the user-facing product path;
* explicit create-new/connect-existing/refuse identity judgment;
* durable proposal, commit, reload, and exact graph revision inspection;
* Hermes exact-name or alias discovery;
* Hermes semantic discovery without naming the Threat;
* exact binding and exact statblock hydration;
* compact and full Threat Sheet projection;
* relationship navigation from the projected Threat;
* one controlled stale or unavailable dependency case and retry;
* an exact identity ledger and a written verdict;
* routing each failure to the smallest owning-boundary repair.

### Excluded

* coding a missing product bridge during the session;
* patching publication, Hermes, hydration, projection, or graph-reference behavior;
* manual edits to hidden graph, publication, binding, or statblock storage;
* API-only substitution for a missing user-facing product action;
* placement, embedding, Build insertion, Plan mutation, combat activation, media, revision adoption, or authoring-library work;
* treating a backend contract probe as a successful product dogfood result;
* redesigning the lifecycle because one surface is missing or awkward.

### Named successors still false

* `SBW12` exact embed;
* `AOW03` durable placement;
* `AOW04` shared governed write routing;
* `COMBAT01` / `SBW15` exact live-combat activation;
* `SBW13` child revision UX;
* `SBW14` governed binding adoption;
* media and image work;
* Build reference insertion.

---

## §1 Mission and invariant

### Mission

Guide the operator through one real MAGIC-D3 session and produce enough exact evidence to decide whether the publication-to-projection path is product-ready, merely usable with friction, or blocked at a specific owning boundary.

### Invariant

```text
One accepted immutable statblock revision becomes one explicitly governed published Threat whose exact
World Graph identity and exact ThreatStatblockBinding survive reload; Hermes and graph inspection can
rediscover that Threat without identity substitution; every rendered mechanic remains attributable to
the exact bound statblock revision and digest; failure, retry, graph-head movement, and later mechanics
cannot silently replace the Threat, binding, graph revision, or mechanics revision.
```

### Falsification test

This gate fails if the operator must:

* manually edit hidden storage;
* paste node IDs or file paths into product state to make discovery work;
* use a backend route because the named product action does not exist;
* choose the first candidate or first binding without an explicit identity decision;
* accept current head or latest statblock revision in place of a pinned identity;
* ignore a duplicate Threat, mismatched digest, missing binding, integrity warning, or stale completion;
* call a successful API response the same thing as a successful GM experience.

---

## §2 Current truth and authority

### Executable anchors

| Slice      | Merged PR | Merge SHA                                  | Current claim                                                                                                     |
| ---------- | --------: | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `SBW09c2b` |    `#491` | `601326b03a5179682b630befd7ebbcaa761937ed` | Proposal-bound exact commit, durable receipt/recovery, revision-pinned verification.                              |
| `SBW10a`   |    `#502` | `b1479970aea69f47f678f35481125ebdfeabddd9` | Revision-pinned Threat query, explicit zero/one/many bindings, exact DungeonMind hydration, Hermes tool.          |
| `SBW10b`   |    `#504` | `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e` | Compact/full exact Threat projection, exact scope navigation, complete mechanics validation, stale-result guards. |

### Authority precedence

1. The checked-out executable code and tests at the recorded execution SHA.
2. Merged public contracts from PRs `#491`, `#502`, and `#504`.
3. `Docs/Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md` for gate intent and verdict vocabulary.
4. The checked-in MAGIC-D3 report produced by this run.
5. The Threat roadmap and tracker after they are reconciled to the merged state.
6. Older handoffs, attached context, and chat summaries.

The current roadmap and tracker still describe `SBW09c2b`, `SBW10a`, and `SBW10b` as future or blocked work. Their sequencing language remains useful, but their status is stale and must not override merged code.

### Main-movement rule

The dispatch anchor is `9fe0b026…`. Immediately before execution:

```bash
git fetch origin
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Record the actual SHA in the report.

If `main` differs from the dispatch anchor, inspect the complete intervening diff before continuing.

Continue only when the drift does not change the owning paths for:

* Threat publication operations, identity, proposals, commits, or routes;
* Threat query/hydration models, services, routes, or API types;
* Hermes graph interaction tools or plugin wiring;
* `AgentInteractionProvider`;
* graph-reference resolution, scope, or projection bindings;
* `ProjectionHost` or `LegacyProjectionHostAdapter`;
* Threat Sheet projection/view-model code;
* `StatblockRenderer` exact-revision input behavior.

Open Build PR `#506` changes shared graph-reference, provider, and projection-adapter seams. If it merges before this run, this handoff must be re-anchored to that merge before dogfood begins.

---

## §3 Roles and operating discipline

### Operator

The operator performs user-visible actions, makes identity judgments, and reports whether the experience is useful and trustworthy.

### Dogfood steward

The steward:

* prepares the environment and report skeleton;
* gives one operator action at a time;
* records exact observations before interpreting them;
* captures IDs, revision pins, status labels, and requests without exposing secrets;
* distinguishes product behavior from direct contract probes;
* stops at invalid authority rather than finding a workaround;
* drafts the verdict and smallest next slice.

### Cadence

Do not present the entire session as one wall of instructions during execution. Move checkpoint by checkpoint:

1. state the next operator action;
2. let the operator perform it;
3. record what actually appeared;
4. capture exact identities and evidence;
5. decide whether the next checkpoint remains valid.

Do not silently reinterpret an unexpected result as success.

---

## §4 Dispatch gate

Do not begin the primary run until all required items are true.

### Repository and services

* clean checkout at the recorded execution SHA;
* current canonical startup path used for DungeonBuddy and DungeonMindServer;
* World Graph root resolves to the intended real world;
* live-control server and UI are reachable;
* DungeonMindServer readiness is visible and honest;
* Hermes is using the intended product agent path, not a one-shot developer substitute;
* no unrelated migration or data repair is running concurrently.

### Real campaign material

Select one real nontrivial Threat concept with an accepted exact mechanics identity:

```text
(statblock_id, revision_id, definition_digest)
```

Preferred material is a Mireward siege threat because it exercises role, capability, relationship, and location discovery. Good candidates include:

* Mireward Latchling;
* Tripod Null-Calf;
* Under-Hymn Brood;
* another accepted fortification-damaging or Mireward-connected threat.

Use whichever actually exists as an accepted exact revision. Do not create a duplicate merely to match a preferred name.

### Reachable product entry points

Before changing durable state, locate the user-facing routes for:

1. starting publication from the accepted mechanics or its owning workflow;
2. reviewing create-new/connect-existing identity candidates;
3. reviewing the sealed publication proposal;
4. confirming the governed commit;
5. opening Hermes in the intended surface;
6. opening a graph result in the shared Projection Host;
7. expanding compact Threat projection to full.

If any mandatory publication action exists only as a backend endpoint or test helper, record `FAIL_PRODUCT — missing user-facing publication bridge` and stop the primary gate. A direct API probe may follow only to narrow the owning boundary; it cannot convert the verdict to PASS.

---

## §5 Evidence ledger

Create the report skeleton before the first durable action:

```text
Docs/Reports/MAGIC-MOMENT-D3-<YYYY-MM-DD>.md
```

Capture these fields as they become known. Never invent placeholders and later forget to replace them.

| Identity                                                       | Value |
| -------------------------------------------------------------- | ----- |
| Repository execution SHA                                       |       |
| World ID                                                       |       |
| Campaign ID                                                    |       |
| Starting graph head revision                                   |       |
| Accepted statblock ID                                          |       |
| Accepted statblock revision ID                                 |       |
| Accepted definition digest                                     |       |
| Threat draft / candidate identity, when relevant               |       |
| Publication operation ID                                       |       |
| Identity resolution ID and decision                            |       |
| Publication proposal ID                                        |       |
| Expected contribution ID                                       |       |
| Commit record / receipt identity                               |       |
| Committed graph revision                                       |       |
| Published Threat node ID                                       |       |
| ThreatStatblockBinding ID                                      |       |
| Bound statblock ID                                             |       |
| Bound revision ID                                              |       |
| Bound definition digest                                        |       |
| Hermes retrieval/session identity, when exposed                |       |
| Graph reference revision and scope mode                        |       |
| Later graph head used for stale test                           |       |
| Later statblock revision used for pinning test, when available |       |

For each checkpoint, record:

* operator action;
* visible result;
* exact request scope or locator when inspectable;
* screenshot or log reference;
* whether the result increased or reduced trust;
* friction that would matter during a live GM session.

Do not include credentials, internal API keys, cookies, or full sensitive headers.

---

## §6 Observable-path inventory

| Path                         | Required observation                                                                                                           | Owning boundary                         |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| Accepted mechanics reopen    | Exact accepted revision and digest reopen without reselection.                                                                 | Workbench / DungeonMind integration     |
| Publication entry            | A user-facing action starts publication from the exact accepted identity.                                                      | Product surface / publication operation |
| Candidate review             | Create-new/connect-existing/refuse remain explicit; no auto-selection.                                                         | SBW09b identity resolution              |
| Proposal review              | Threat, authored attributes, resource, binding, parent, visibility/evidence, and exact locators are inspectable before commit. | SBW09c1 proposal surface                |
| Governed confirmation        | One explicit confirmation creates or recovers one commit claim.                                                                | SBW09c2b commit route/service           |
| Reload                       | Exact committed revision, Threat, resource, and binding survive browser/server reload.                                         | Graph storage + publication receipt     |
| Exact/alias Hermes discovery | Exact or alias question finds the intended Threat without node-ID seeding.                                                     | Hermes + SBW10a                         |
| Semantic Hermes discovery    | Role/capability/relationship/location question finds it without exact name.                                                    | Graph retrieval + Hermes routing        |
| Follow-up continuity         | “What is it connected to…?” resolves the same Threat through fresh bounded traversal.                                          | Hermes session + graph tools            |
| Exact hydration              | Every binding is explicit; available mechanics match bound revision/digest.                                                    | SBW10a + DungeonMind client             |
| Compact projection           | Useful game information appears before metadata; no arbitrary winner for multiple bindings.                                    | SBW10b compact view                     |
| Full projection              | Every binding and connected graph object is represented honestly.                                                              | SBW10b full view                        |
| Relationship navigation      | Related object opens under originating exact graph scope.                                                                      | Graph-reference resolver / provider     |
| Stale or unavailable case    | Identity remains honest, no stale completion overwrites current selection, retry is understandable.                            | Owning async and dependency boundary    |
| Revision pinning             | New graph head or mechanics revision does not silently move the published object.                                              | Graph reference + exact binding         |

---

## §7 Execution protocol

### Checkpoint A — Establish the starting state

1. Record execution SHA, world, campaign, service state, and starting graph head.
2. Reopen the accepted statblock revision through the product.
3. Record exact `(statblock_id, revision_id, definition_digest)`.
4. Inspect whether the Threat concept already exists in the World Graph.
5. Record what is deliberately **not** preselected.

Stop if accepted mechanics cannot be reopened exactly. This is a prerequisite regression, not MAGIC-D3 evidence.

### Checkpoint B — Start governed publication

Use the existing product action from the accepted mechanics or its owning workflow.

Observe:

* whether the exact accepted locator is carried automatically;
* whether world and campaign are explicit and correct;
* whether expected graph parent is visible or at least inspectable;
* whether the operator must copy or retype identity;
* whether publication state is clearly distinct from saved mechanics.

Record the publication operation ID.

Stop with `FAIL_PRODUCT` if the user-facing action is missing or loses the exact accepted locator.

### Checkpoint C — Make the identity decision

Review candidates without assuming the preferred result.

The operator must explicitly choose one:

* **create new** — only when no existing Threat is the same campaign identity;
* **connect existing** — only when an exact existing Threat is the intended identity;
* **refuse** — when evidence is insufficient or candidates are misleading.

For each serious candidate, inspect:

* exact node ID;
* label and aliases;
* campaign scope;
* relevant relationships;
* evidence/source anchors when exposed;
* why it is or is not the same identity.

No first candidate, label similarity, or ranking score may become durable identity automatically.

A justified refusal is valid product behavior, but it does not complete the publish/query/project gate. Preserve it as evidence and select another real accepted Threat only after recording why this attempt stopped.

### Checkpoint D — Review and confirm the proposal

Before confirmation, inspect the proposed durable effects.

For create-new, expect the new Threat identity plus authored fields, external statblock resource, and exact binding.

For connect-existing, expect the external resource and exact binding without silently rewriting the existing Threat.

Record:

* proposal ID;
* selected target;
* expected contribution ID;
* expected parent graph revision;
* accepted assertion/effect summary;
* exact mechanics locator;
* any visible authority, evidence, and visibility fields.

Confirm through the graph-governed product action.

Observe success, retry, busy, recovery, or failure honestly. Do not restart the workflow under a new operation ID merely because the first outcome is uncertain.

### Checkpoint E — Reload durable authority

After a successful or recovered commit:

1. record the committed graph revision and current head;
2. close the relevant projection/workbench state;
3. reload the browser;
4. restart the live-control server when operationally reasonable;
5. reopen the publication/graph state through normal product entry;
6. verify the exact Threat node and exact binding still exist;
7. verify the binding still names the original statblock revision and digest.

A reload that requires manual storage reconstruction is failure.

### Checkpoint F — Hermes discovery

Ask three questions in the product Hermes path.

#### F1 — Exact name or alias

Template:

```text
What do we know about <Threat name or real alias>?
```

#### F2 — Semantic discovery without exact name

Choose a prompt grounded in the selected Threat’s actual campaign role. Examples:

```text
Which Mireward threat is built to damage fortifications?
```

```text
What insectoid siege creature is connected to the North Gate defense?
```

```text
Which threat should I prepare for if the attackers come through the ground?
```

Do not include the Threat node ID, statblock ID, exact name, or a source path.

#### F3 — Relationship follow-up

```text
What is it connected to that should affect my prep?
```

Record:

* whether the answer identifies the correct Threat;
* whether it distinguishes known facts, mechanics, and uncertainty;
* the exact graph revision or trace when exposed;
* relevant node IDs, predicates, and source anchors;
* whether unavailable mechanics are represented honestly;
* whether the follow-up stays on the same Threat without relying on ambient unsupported memory.

If F1 succeeds but F2 fails, classify a semantic retrieval/routing gap rather than a publication failure.

### Checkpoint G — Open compact and full projection

Open the exact Threat from a Hermes result or graph inspection using the existing shared projection path.

#### Compact view

Verify that it prioritizes:

* name;
* threat kind and role;
* encounter/campaign meaning;
* useful AC/HP/speed/challenge or bounded key mechanics when exactly one trusted binding is available;
* binding count/status;
* useful connected objects;
* clear expansion.

Metadata scores and evidence internals must not dominate the default card.

#### Full view

Verify that it includes:

* campaign-facing identity and summary;
* aliases/tags/role when present;
* connected objects and useful predicates;
* every enumerated mechanics binding in deterministic order;
* full mechanics only for trusted available revisions;
* honest locator/status panels for unavailable, missing, or corrupt revisions;
* inspectable graph revision, node ID, binding ID, statblock ID, revision ID, and digest.

When multiple bindings exist, no compact or full path may silently choose one as the universal winner.

### Checkpoint H — Relationship navigation and graph-scope pinning

From the projected Threat, open at least two useful related objects when available, such as:

* location;
* faction;
* event;
* encounter;
* creator/controller;
* another threat or defensive asset.

Verify:

* the related object is the exact relationship target;
* the predicate is understandable;
* navigation retains the originating world, campaign, scope mode, and graph revision;
* returning to the Threat does not change its binding or mechanics revision;
* delayed navigation cannot replace a newer selected object.

### Checkpoint I — Exercise one stale or unavailable path

At least one controlled failure/retry is required.

#### Preferred: graph-head advance while an older projection remains open

1. Keep the Threat projection open at committed graph revision `R1`.
2. In another legitimate workflow, perform one useful governed graph change that advances head to `R2`.
3. Return to the `R1` Threat projection.
4. Navigate a relationship or reopen the reference.
5. Verify that the product reloads or retains `R1` scope rather than silently substituting `R2`.
6. Then deliberately reopen from current head and verify the transition is explicit.

Do not create junk graph data solely to advance head.

#### Acceptable fallback: graph read dependency unavailable

1. Preserve the exact open reference and identity ledger.
2. Temporarily make the graph read dependency unavailable through normal service control, not storage mutation.
3. Attempt reopen/navigation.
4. Verify an honest unavailable result with no substitute identity.
5. Restore the service.
6. Retry and verify exact recovery.

A DungeonMindServer outage is useful secondary evidence for mechanics hydration but does not replace the required graph stale/unavailable case.

### Checkpoint J — Mechanics revision pinning

Prefer a selected statblock that already has at least one later immutable revision, or create a later revision only through an already-supported ordinary product path.

Verify that the published binding and Threat projection continue to use the originally bound revision and digest.

Do not use hidden APIs or manually alter binding storage to manufacture this condition.

If no safe later revision exists, record `NOT_EXERCISED — no product-valid later revision available`. The gate cannot receive an unqualified PASS with this evidence missing; the operator may choose `PASS_WITH_FRICTION` when every observable product path is otherwise correct and the owning automated evidence is accepted as coverage for this adversarial condition.

### Checkpoint K — Replay and duplicate resistance

Repeat the original confirmation or reopen the same operation/proposal through the product where supported.

Verify:

* no duplicate Threat is created;
* no duplicate binding is created;
* a known committed revision is not merged again;
* the product returns the existing durable outcome or a clear terminal state;
* the exact identity ledger remains unchanged.

Do not create a fresh operation merely to avoid understanding replay behavior.

---

## §8 Verdict matrix

Use only the established runbook verdicts.

### `PASS`

All required user-facing paths exist and complete. Exact identity survives reload. Semantic discovery works. Hydration and projection remain exact. One graph failure/stale case recovers honestly. Later mechanics do not move the binding. No serious friction would cause the GM to abandon or distrust the workflow.

### `PASS_WITH_FRICTION`

The complete capability is usable and correct, but meaningful friction exists: difficult discovery, excessive navigation, weak status language, manual cross-checking, or one explicitly accepted evidence gap such as the absence of a product-valid later mechanics revision.

Correctness failures are not friction.

### `FAIL_PRODUCT`

The architecture may exist, but the named GM experience is missing, unusable, misleading, or only reachable through scripts/API calls. Examples:

* no user-facing publication bridge;
* proposal or confirmation cannot be reached;
* Hermes result cannot open the exact projection;
* useful relationships/mechanics are technically present but not usable;
* retry state is opaque enough that the operator must restart or guess.

### `FAIL_ARCHITECTURE`

Identity or authority is incorrect. Examples:

* duplicate Threat or binding;
* silent merge of different identities;
* graph head replaces pinned revision;
* latest statblock revision replaces bound revision;
* first binding wins silently;
* copied mechanics become graph truth;
* integrity failure reaches the renderer;
* uncertain commit outcome permits another merge without recovery.

### `BLOCKED_DEPENDENCY`

A required external provider or service is unavailable before the product behavior can be meaningfully exercised. A reachable service returning bad product output is not blocked dependency.

---

## §9 Failure routing — smallest next slice

Do not respond to a failure by reopening the entire roadmap. Route it to the boundary that first made the invariant false.

| Observation                                                     | Likely owner                                 | Next-slice shape                                              |
| --------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------- |
| Accepted revision cannot reopen exactly                         | Workbench / accepted mechanics integration   | Narrow R0-A regression repair.                                |
| Publication is backend-only                                     | Product surface / shared action routing      | User-facing exact publication bridge; no lifecycle redesign.  |
| Exact locator is lost at publication entry                      | Workbench → publication handoff              | Exact accepted-locator action contract.                       |
| Candidate ranking silently selects identity                     | SBW09b surface/service                       | Explicit identity-decision repair.                            |
| Proposal omits or misstates exact effects                       | SBW09c1 proposal boundary                    | Proposal inspection/contract repair.                          |
| Retry creates duplicate or second merge                         | SBW09c2b                                     | Commit/recovery correctness repair; architecture blocker.     |
| Binding missing after reload                                    | Publication verification / graph persistence | Exact commit verification or storage repair.                  |
| Hermes exact-name query fails                                   | Hermes tool routing / SBW10a                 | Exact retrieval integration repair.                           |
| Exact name works; semantic question fails                       | Graph retrieval/ranking/context              | Narrow semantic discovery improvement with adversarial query. |
| Hermes answers but cannot open exact object                     | Graph-reference action routing               | Result-to-projection bridge.                                  |
| Mechanics hydration uses wrong or latest revision               | SBW10a / DungeonMind client                  | Exact locator and integrity repair.                           |
| Compact/full sheet hides bindings or useful game data           | SBW10b presentation                          | Threat Sheet view-model/presentation repair.                  |
| Relationship opens current head instead of originating revision | Graph-reference resolver                     | Exact-scope navigation repair.                                |
| Old async completion replaces new object                        | Provider/component stale guard               | Selection-generation/unmount repair.                          |
| Build merge regresses Plan/Threat projection                    | Shared Surface Interaction integration       | Cross-surface compatibility repair against the new base.      |

Every failure report must name:

* first incorrect observable action;
* exact expected identity;
* exact actual identity;
* owning boundary;
* whether durable state was changed;
* smallest independently useful repair;
* capabilities that remain explicitly out of scope.

---

## §10 Stop conditions

Stop the primary run and report before continuing when:

* repository drift touches an owning path and has not been reviewed;
* Build PR `#506` or another shared-surface PR merged after this handoff without reanchor;
* accepted exact mechanics do not exist or cannot reopen;
* the intended world/campaign cannot be established confidently;
* product publication requires direct backend calls;
* proceeding requires manual storage edits, copied IDs, or current-head/latest fallback;
* a publication outcome is uncertain and the product offers no honest recovery/replay path;
* duplicate Threat/resource/binding evidence appears;
* graph or mechanics integrity fails;
* the renderer receives mechanics that the backend or frontend marked untrusted;
* a test action would create junk durable campaign data;
* continuing would require code changes.

On a stop condition:

1. preserve all durable state and logs;
2. do not “clean up” evidence through hidden edits;
3. complete the report through the failure point;
4. classify the verdict;
5. draft the smallest next handoff;
6. do not implement it in the dogfood session.

---

## §11 Required report structure

```markdown
# Magic Moment Dogfood — MAGIC-D3

**Date:**
**Operator:**
**Steward:**
**Repository execution SHA:**
**Dispatch anchor:** `9fe0b0264f8f08f8fb81a3afd594a607d4f2b61e`
**World / campaign:**
**Starting graph head:**
**Ending graph head:**
**Result:** PASS | PASS_WITH_FRICTION | FAIL_PRODUCT | FAIL_ARCHITECTURE | BLOCKED_DEPENDENCY

## Intent
What real GM preparation task was attempted, and why was this Threat useful?

## Reanchor and environment
- Current main SHA
- Drift from dispatch anchor
- Services and provider state
- Product paths confirmed before mutation
- Open shared-surface work that could affect the result

## Starting exact mechanics
- Threat concept
- statblock ID
- revision ID
- definition digest
- whether a later immutable revision already existed

## Publication path
Numbered user-visible actions from publication entry through confirmation.

## Identity decision
Candidates inspected, exact IDs, create/connect/refuse decision, and rationale.

## Durable publication ledger
- operation ID
- resolution ID
- proposal ID
- expected contribution ID
- commit/receipt identity
- committed graph revision
- Threat node ID
- binding ID
- bound statblock locator and digest

## Reload proof
What survived browser reload and service restart?

## Hermes probes
### Exact or alias
Prompt, result, trace, exact node.

### Semantic
Prompt, result, trace, exact node.

### Relationship follow-up
Prompt, result, relevant predicates and objects.

## Projection proof
### Compact
Useful information, binding behavior, friction.

### Full
Every binding, connected objects, exact technical details, friction.

## Relationship navigation and exact scope
Objects opened, originating revision, later head, observed behavior.

## Failure / stale / retry proof
Injected condition, visible behavior, durable behavior, retry result.

## Mechanics revision pinning
Later revision used or NOT_EXERCISED, and whether the binding moved.

## Replay / duplicate proof
Repeated action and observed durable identity.

## What felt magical
What worked as one connected GM experience?

## Friction and distrust
Where did the operator copy data, reselect identity, leave the product, wait without useful state, or manually verify correctness?

## Invariant ledger
| Claim | PASS / FAIL / NOT_EXERCISED | Evidence |
|---|---|---|
| One explicit identity decision | | |
| No duplicate mechanics or Threat identity | | |
| Exact binding survived reload | | |
| Hermes exact/alias discovery | | |
| Hermes semantic discovery | | |
| Exact mechanics hydration | | |
| Compact projection useful | | |
| Full projection complete and honest | | |
| Relationship navigation retained exact scope | | |
| Failure/retry remained honest | | |
| Later mechanics did not move binding | | |
| Replay did not duplicate publication | | |

## Verdict
Why this is the selected result classification.

## Smallest next slice
One independently useful repair or the next roadmap gate.

## Still false
Placement, embed, Build insertion, combat, binding adoption, editing, media, and any other deferred capabilities.
```

---

## §12 Gate closeout

After the report is complete:

1. Link the report from the Threat roadmap and tracker.
2. Reconcile those documents to the merged truth:

   * `SBW09c2b` complete in PR `#491`;
   * `SBW10a` complete in PR `#502`;
   * `SBW10b` complete in PR `#504`;
   * MAGIC-D3 status set to the report verdict;
   * placement remains blocked unless MAGIC-D3 passes or the operator explicitly accepts named friction.
3. Mark the SBW10b implementation handoff as implemented history, not active dispatch authority.
4. Do not dispatch `AOW03/AOW04` merely because MAGIC-D3 was attempted.
5. On PASS or accepted PASS_WITH_FRICTION, pause for operator discussion before placement design.
6. On failure, produce a separate narrow implementation handoff and keep placement blocked.

### Expected end state

The session ends with one of two honest outcomes:

```text
MAGIC-D3 passes with exact evidence
→ publication/query/projection spine is accepted for real use
→ discuss placement from observed GM needs
```

or:

```text
MAGIC-D3 fails at one named owning boundary
→ preserve exact evidence
→ dispatch the smallest repair
→ rerun only the affected path plus the complete MAGIC-D3 gate
```

The session must not end with “the backend works, so the product probably works.”
