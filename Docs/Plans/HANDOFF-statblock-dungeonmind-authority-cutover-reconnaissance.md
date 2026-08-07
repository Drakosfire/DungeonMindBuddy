# HANDOFF — Statblock DungeonMind authority cutover reconnaissance

**Created:** 2026-08-06  
**Status:** ACTIVE — dispatch one docs-only reconnaissance capability after this handoff merges.  
**Flow:** `STATBLOCK`  
**Canonical handoff path:** `Docs/Plans/HANDOFF-statblock-dungeonmind-authority-cutover-reconnaissance.md`  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Cross-repository read authority:** `Drakosfire/DungeonMind`  
**Implementation base at dispatch design time:** `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd` (`DungeonMindBuddy/main`)  
**DungeonMind anchor at dispatch design time:** `7c311ae0d0d59d7379dee38780be509970fb3a8c` (`DungeonMind/main`, merged PR #21)  
**Suggested implementation branch:** `statblock/dungeonmind-cutover-reconnaissance`

> This is a reconnaissance/reporting PR, not a cutover implementation PR. It must not change runtime behavior, product authority, graph semantics, mechanics persistence, surface behavior, deployment, secrets, caches, or transport. Its job is to discover the exact remaining cutover seam from current code and report one bounded next step.

---

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User/operator surface changed? | Failure model changed? | Independently testable/revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Re-anchor current DungeonMind + DungeonMindBuddy mechanics path | Yes | No | No | No | Yes | Include as reconnaissance evidence |
| Trace one real published Buddy Threat through graph → binding → hydration → Plan/Build projection | Yes | No | No | No | Yes | Include; core evidence |
| Map the corresponding DungeonMind profile/resource/hydration path | Yes | No | No | No | Yes | Include; core evidence |
| Identify identity, transport, runtime, failure, deployment, and authority seams that block transparent cutover | Yes | No | No | No | Yes | Include; mission outcome |
| Recommend one smallest next PR or issue a stop report | Yes | No | No | No | Yes | Include; consequence of the same audit |
| Implement the identity/profile bridge | Yes | Yes | Possibly | Yes | Yes | **Successor — excluded** |
| Add a Buddy shadow hydration consumer | Yes | Yes | No by intent | Yes | Yes | **Successor — excluded** |
| Promote DungeonMind hydration to product authority | Yes | Yes | Potentially | Yes | Yes | **Later successor — excluded** |
| Delete Buddy duplicate authority | Yes | Yes | No by intent | Yes | Yes | **Later successor — excluded** |
| Update stale roadmaps/trackers | Yes | Yes, documentation authority | No | No | Yes | **Separate docs sync — excluded** |

**Selected capability:**

```text
Produce an evidence-backed cutover readiness report that traces one existing
published Buddy Threat across the current product and DungeonMind mechanics
spines, identifies every remaining seam preventing transparent DungeonMind
hydration, and names exactly one smallest successor capability or a precise
stop condition.
```

**Invariant:**

```text
The report describes current repository truth exactly enough that the next PR
can change one authority seam without guessing identity, transport, runtime,
failure, surface, or demolition behavior.
```

**Mission falsification test:**

```text
This is not one slice if the agent must modify production code, create a new
public/durable contract, change product behavior, add a shadow consumer, alter
cache/runtime semantics, publish graph state, or promote DungeonMind authority
in order to complete the report.
```

**Named successors intentionally still false after this PR:**

1. `STATBLOCK: adapt published Buddy Threat identity into DungeonMind D&D profile`
2. `STATBLOCK: shadow verify Buddy Threat hydration through DungeonMind`
3. bounded real campaign comparison/dogfood
4. DungeonMind mechanics-authority promotion
5. demolition or explicit retained-owner decision for replaced Buddy hydration authority

---

## §1 Mission

```text
A fresh implementation steward can see exactly what prevents one existing
Mireward Threat in Plan or Build from hydrating through DungeonMind with no
user-visible behavior change, so the next PR can attack the smallest real
cutover seam instead of inventing another parallel path.
```

### Core question

Answer this directly and concretely in the report:

```text
If we wanted one existing Mireward Latchling or Tripod Null-Calf Threat in Plan
or Build to hydrate through DungeonMind tomorrow without the GM noticing a
product change, what exact identity, profile, binding, transport, runtime,
deployment, failure-parity, and authority seams still prevent it?
```

“Without the GM noticing” means **presentation and interaction parity only**. It does not authorize a hidden authority promotion. The current Buddy path remains authoritative throughout this reconnaissance.

### Required disposition

The report must finish with exactly one of:

```text
READY_FOR_IDENTITY_PROFILE_BRIDGE
```

or

```text
NOT_READY_FOR_BRIDGE — <named blocking fact(s)>
```

If ready, name exactly one smallest successor mission. Do not implement it in this PR.

---

## §2 Context, authority, and boundaries

### 2.1 Snapshot that motivated this reconnaissance

Re-anchor all of these before work begins. These are dispatch-design anchors, not permission to ignore newer repository state.

#### DungeonMind

`main` at design time:

```text
7c311ae0d0d59d7379dee38780be509970fb3a8c
```

That merge contains PR #21:

```text
STATBLOCK: resolve exact statblock mechanics resources
```

The established DungeonMind mechanics chain is now, in broad terms:

```text
exact graph revision
+ exact D&D Threat/profile eligibility
+ exact DndMechanicsResourceRef
→ one exact authenticated provider revision GET
→ observed resource envelope
→ identity/schema/digest adjudication
→ exact Threat mechanics hydration
```

Do not reopen those semantics casually. This reconnaissance must determine how one real Buddy Threat can satisfy them.

#### DungeonMindBuddy

`main` at design time:

```text
9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd
```

This includes merged Optimization work through PR #513:

```text
#511 — OPTIMIZATION: prewarm committed World Graph revision
#513 — OPTIMIZATION: warm bounded surface projection recipes
```

At design time these adjacent product PRs remain open and must be inspected because they may own the eventual consumer seam:

```text
#510 — BUILD: insert exact World Graph reference into Canvas
  head: 9ea88533686eb257beec14591451aabe6462b294
  known live gate: E11 operator dogfood still pending

#512 — STATBLOCK: Threat parchment sheets + shared World Graph lens
  head: 08b146511359fff869bf3a30e6ba841269ad3a12
  shared Plan/Build Threat presentation and exact hydration remain in scope
```

If #510 or #512 merges, rebases, closes, splits, or materially changes before reconnaissance begins, inspect the resulting current state rather than preserving this snapshot artificially.

### 2.2 Product/kernel ownership model

Treat this as the starting hypothesis to verify against current code:

**DungeonMindBuddy owns product behavior:**

- source/authored campaign workflow;
- accepted statblock authoring and persistence;
- Threat publication orchestration and receipts;
- current World Graph product projections;
- Plan and Build surface composition;
- Threat hover/sheet presentation;
- current user-facing exact mechanics hydration behavior;
- dogfood and product recovery behavior.

**DungeonMind owns reusable mechanics/kernel semantics:**

- immutable exact graph revision semantics;
- D&D semantic profile boundaries;
- exact Threat mechanics eligibility/binding semantics;
- exact mechanics resource references;
- exact-revision mechanics hydration semantics and transport host;
- exact statblock provider resolver added by PR #21.

This PR must report where current implementation disagrees with that intended split.

### 2.3 Architecture constraints already treated as locked

Do not propose a cutover design that requires any of the following unless the report explicitly stops and asks the operator to reopen architecture:

1. copied statblock mechanics becoming World Graph truth;
2. labels or names used as cross-repository identity;
3. `latest`, current head, list, search, or first-match discovery replacing exact revision identity;
4. first-winner behavior when multiple statblock bindings exist;
5. a surface-owned mechanics binding contract;
6. an ad hoc mutable cross-repository ID dictionary;
7. graph writes hidden inside hydration;
8. silent identity repair in a shadow adapter;
9. cache/prewarm state becoming authority;
10. a new user-facing statblock feature merely to prove the migration;
11. deleting the Buddy authority path before shadow parity and bounded dogfood;
12. retaining a replaced duplicate path indefinitely without a named consumer and deletion owner.

### 2.4 Authority precedence

When sources disagree, use this order and record conflicts:

```text
1. Current merged repository code + tests
2. Current checked-in architecture / decision authority
3. Current active tracker or checked-in handoff
4. Current open-PR cumulative diff and its checked-in handoff
5. This handoff's snapshot facts
6. Attached/project source context
7. Chat summaries
```

A stale tracker must be reported as stale; do not “correct” implementation truth to fit it in this PR.

### 2.5 Required starting reads

Read current versions, not remembered copies.

#### DungeonMindBuddy

At minimum:

```text
README.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Design/ARCHITECTURE-surface-interaction-layer.md
Docs/Plans/PLAN-surface-interaction-hoist-build-first.md
Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md
Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md
```

Then inspect the current production contracts and tests for:

```text
ThreatStatblockBindingV1
uses_statblock
accepted statblock revision identity
World Graph Threat IDs
exact mechanics hydration/query
Threat projection / Threat sheet
Plan graph reference opening
Build graph reference insertion/opening
resident World Graph runtime
post-commit prewarm
projection recipe/cache prewarm
```

Inspect PR #510 and PR #512 cumulative heads or their merged equivalents.

#### DungeonMind

At minimum:

```text
Docs/Handoffs/HANDOFF-exact-statblock-resource-resolver.md
```

and current production/tests for:

```text
DndMechanicsResourceRef
DndThreatMechanicsBinding
D&D profile Threat eligibility
exact revision graph reads
Threat mechanics hydration service/host
statblock_resource_resolver
provider identity/schema/media-type constants
failure/status contracts
```

Also inspect the merged predecessor semantics from PR #17 and PR #20 as represented in current code/tests. The report must cite code, not merely PR prose.

---

## §3 Required reconnaissance traces and observable-path inventory

This is not a behavioral implementation PR, so “required behavior after this slice” means **required report coverage**.

| Trace / observable path | Current behavior to discover | Report must establish | Owning evidence boundary |
|---|---|---|---|
| Exact real Threat identity | Buddy graph node + exact graph revision | Durable ID shape and exact revision pin | World Graph models/store/projection |
| Threat → statblock binding | Current published Buddy binding | Exact binding fields, multiplicity, ownership | publication/query contracts + fixtures |
| Accepted statblock revision | Buddy immutable mechanics record | Exact statblock ID, revision ID, digest bytes | accepted-revision store/API |
| Buddy hydration | Existing exact query/hydration path | Entry point, calls, failure semantics, authority | service/route tests |
| Plan Threat projection | Existing or #512 path | How exact mechanics arrives at hover/full sheet | shared projection/component tests |
| Build Threat projection | Existing, #510/#512 path | How inserted exact graph reference reopens same Threat | Build reference + shared projection tests |
| DungeonMind profile eligibility | Current `dnd5e` profile | Required graph object/kind/relationship identity | DungeonMind D&D contract/tests |
| DungeonMind mechanics binding | Current B.3a semantics | Exact fields and required resource ref | DungeonMind domain/tests |
| DungeonMind provider resolution | PR #21 | Exact provider URL/ref/auth/bounds | integration resolver tests |
| DungeonMind hydration host | PR #20 | Exact request and failure envelope | service/route/integration tests |
| Provider miss | Both paths | 404/410/miss equivalence or mismatch | owning route/service tests |
| Dependency unavailable | Both paths | DMS/provider-down behavior parity | route/service tests |
| Integrity disagreement | Both paths | wrong ID/revision/schema/digest behavior | contract/integration tests |
| Multiple bindings | Both paths | explicit plural behavior; never first-winner | query/projection tests |
| Head advance | Both paths | exact historical revision remains exact | graph/runtime integration tests |
| Browser reload | Buddy product | reference survives and reopens exact identity | Build/Plan integration/manual evidence |
| Process restart | Buddy server + DungeonMind service | what is persisted vs recomputed/cached | runtime/store code/tests |
| Cache/prewarm cold/hot | Buddy OPT01/02/03 | latency optimization cannot change identity/result | optimization tests |

### 3.1 Choose one exact proof target

Preferred real campaign target:

```text
Mireward Latchling
```

because Build #510 already names it in its live dogfood flow and Statblock #512 names Latchling projection behavior.

Alternative:

```text
Tripod Null-Calf
```

Use the alternative only if it is the cleaner currently published exact Threat.

Do **not** identify the target by label alone. The report must record:

```text
campaign/world scope
exact graph revision
exact durable Threat object ID
exact Threat/statblock binding identity
statblock_id
statblock revision_id
exact digest representation
provider/resource schema identity
where each value came from
```

If no real campaign object can be traced reproducibly from current committed/available state, use the smallest exact committed fixture to complete the contract map and mark real campaign proof as a blocking dogfood gap. Do not invent IDs from prose.

### 3.2 Required end-to-end current Buddy trace

Produce a call/ownership trace in the report similar to:

```text
exact graph reference / current surface lens
→ exact World Graph revision/object lookup
→ Threat projection/query
→ zero/one/many mechanics binding result
→ exact accepted statblock revision lookup/hydration
→ shared Threat sheet projection
→ Plan or Build presentation
```

Every arrow must name the concrete current symbol/path that owns it.

### 3.3 Required candidate DungeonMind trace

Without implementing it, show the exact information DungeonMind currently requires:

```text
world_id
+ exact graph revision_id
+ exact object_id satisfying D&D profile eligibility
+ exact DndMechanicsResourceRef
→ DungeonMind exact hydration host
→ PR #21 exact provider revision resolution
→ mechanics payload / stable miss / stable unavailable / integrity failure
```

Then identify which values Buddy already has exactly, which require deterministic representation adaptation, which require a new governed contract, and which are deployment/runtime concerns rather than identity concerns.

---

## §4 Files in scope — implementation PR allowlist

The reconnaissance implementation PR is docs-only.

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Reports/REPORT-statblock-dungeonmind-cutover-reconnaissance.md` | Canonical evidence-backed report answering §1 |
| Modify | `Docs/Plans/HANDOFF-statblock-dungeonmind-authority-cutover-reconnaissance.md` | Append exact implementation handback/evidence only |

### Bounded discovery exception

Read-only repository discovery is intentionally broad because the mission is to locate the true existing cutover seams across two repositories.

```text
Writable directory: none beyond the two paths above
Maximum additional committed paths: 0
Allowed additional path kinds: none
Read-only discovery: current source, tests, docs, PR diffs, commit history, CI metadata in both repositories
Decision rule: inspect any path needed to prove one row of §3 or §6
Required report: every production path named as a seam must be cited in the final report
```

If a code or tracker edit seems necessary, stop and report why. Do not broaden the PR.

---

## §5 Explicitly out of scope

| Path / capability | Why excluded |
|---|---|
| Any production Python/TypeScript code | This PR discovers the cutover seam; it does not change it |
| Any API/schema/type change | Would be Successor A or another contract PR |
| Buddy statblock storage/persistence changes | Mechanics producer remains unchanged during reconnaissance |
| DungeonMind graph/profile writes | No bridge/materialization implementation yet |
| DungeonMind provider deployment | Operational design may be reported, not implemented |
| Secret provisioning | Report required topology/owner; do not create or rotate secrets |
| Plan/Build/Threat UX changes | Existing product behavior is the comparison target |
| OPT runtime/cache changes | Optimization is evidence/context only; never authority |
| Combat placement/activation | Later lane after mechanics cutover proof |
| Tracker/roadmap cleanup | Separate document synchronization operation |
| Duplicate-path deletion | Requires successful shadow proof and explicit promotion decision |

Nearby work is not authorization.

---

## §6 Required report contract

The report is the product of this PR. It must contain all sections below.

### §6A Repository and PR re-anchor ledger

Record exact current state at the start of reconnaissance:

```text
DungeonMind main SHA
DungeonMindBuddy main SHA
PR #510 state/base/head/mergeability or merged replacement
PR #512 state/base/head/mergeability or merged replacement
latest Optimization merge(s) touching resident/prewarm/projection behavior
any newer statblock/build/runtime PR that materially changes the trace
```

For each snapshot fact in this handoff classify:

```text
MATCH
ADVANCED_SAME_CONTRACT
MATERIAL_CHANGE
STALE_DOC_ONLY
CONFLICT
```

If a material change invalidates the mission, stop and report rather than forcing the old shape.

### §6B Exact identity/ownership matrix

At minimum:

| Identity / datum | Buddy current owner + representation | DungeonMind required owner + representation | Same identity already? | Adaptation required? | May be inferred? |
|---|---|---|---|---|---|
| world/campaign scope | | | | | No |
| exact graph revision | | | | | No |
| Threat graph object ID | | | | | No |
| Threat semantic kind | | | | | No |
| mechanics relationship/binding | | | | | No |
| statblock ID | | | | | No |
| statblock revision ID | | | | | No |
| definition/payload digest | | | | | No |
| provider ID | | | | | No |
| resource schema/media type | | | | | No |
| mechanics payload bytes/object | | | | | No repair |

The key unresolved historical mismatch to test, not assume, is roughly:

```text
Buddy:       threat:* + uses_statblock + ThreatStatblockBindingV1
DungeonMind: obj:* + D&D profile eligibility + DndThreatMechanicsBinding
```

Do not normalize these into apparent equality without proving the governing contract.

### §6C Predecessor-to-consumer field map

Ground the actual current Buddy binding/provider response and map it field-by-field to DungeonMind requirements.

Required shape:

| Buddy field/outcome | Exact current shape/optionality | DungeonMind destination | Transformation | Lossless? | Existing proof |
|---|---|---|---|---|---|

Explicitly answer:

- whether `sha256:<hex>` vs bare lowercase hex is only representation or changes contract meaning;
- whether the exact canonical definition bytes/object hashed by Buddy are the same payload DungeonMind verifies;
- whether statblock/revision IDs are byte-for-byte the same provider locators;
- whether provider/schema/media type values already match;
- whether any field is currently repaired, defaulted, discovered, or derived from current head;
- whether multiple bindings are plural end-to-end.

If digest bytes cannot be demonstrated equivalent, disposition must be `NOT_READY_FOR_BRIDGE`.

### §6D Current-vs-DungeonMind failure parity matrix

At minimum compare:

| Case | Buddy current observable behavior | DungeonMind behavior | Parity required for shadow? | Mismatch / owner |
|---|---|---|---|---|
| exact success | | | Yes | |
| zero binding | | | Yes | |
| multiple bindings | | | Yes | |
| provider 404 | | | Yes | |
| provider 410 | | | Yes | |
| provider unavailable/timeout | | | Yes | |
| DMS unavailable | | | Yes | |
| wrong provider identity | | | Yes | |
| wrong statblock ID/revision | | | Yes | |
| wrong schema/media type | | | Yes | |
| digest mismatch | | | Yes | |
| graph revision missing | | | Yes | |
| graph head advances after reference capture | | | Yes | |
| browser reload | | | Product parity | |
| server/process restart | | | Product parity | |

“Both fail” is not enough. Record stable status/result categories and whether either side falls back or repairs.

### §6E Runtime and transport topology

Produce one concise topology showing current processes/services and exact calls.

At minimum answer:

```text
Where is the World Graph read from today?
Which process owns resident exact revisions?
What do OPT01/OPT02/OPT03 cache or prewarm?
Where does current Buddy mechanics hydration occur?
What service currently serves accepted statblock revisions?
Where would DungeonMind PR #20/21 run in the candidate path?
Which service calls which service?
Which exact credential crosses that boundary?
Which URLs/config are repository-defined versus deployment-only unknowns?
Does a cutover require a second graph load or can an existing exact revision identity be reused?
Which caches are optional and safe to miss entirely?
```

Do not invent deployment state that is not represented in repository/config/operator evidence. Mark it `OPERATIONAL_UNKNOWN` and state whether it blocks the next code PR or only later dogfood.

### §6F Surface integration map

Inspect current merged code plus #510/#512 or their merged equivalents and answer:

```text
What single product-side seam currently asks for exact Threat mechanics?
Do Plan and Build now converge before hydration or only after hydration?
Does the shared Threat sheet consume a product-neutral projection model or Buddy-specific hydration result?
Where can a future shadow comparison be inserted without creating a second user-facing projection path?
What exact reference/revision identity survives Build save → hard reload → lens change → reopen?
Does any surface path still independently select campaign/mechanics binding?
```

Prefer one shared shadow seam. If Plan and Build would require separate shadow implementations, report that as a decomposition concern rather than silently bundling them.

### §6G Optimization interaction audit

Optimization must remain non-authoritative.

For OPT01/OPT02/OPT03 and any successor merged before reconnaissance, state:

```text
what key is cached/resident/prewarmed
whether the key contains exact graph revision identity
whether a stale head can replace a pinned revision
whether cache miss changes semantics
whether prewarm performs mechanics hydration or only graph/projection work
whether a DungeonMind shadow call would be inside or outside the cached projection builder
whether cache invalidation can change which mechanics resource is selected
```

If any optimization can change semantic identity/result rather than latency, stop and report it as an authority blocker.

### §6H Duplicate authority / demolition inventory

Name concrete Buddy production paths that would become candidates for deletion **after** DungeonMind shadow parity and promotion.

Required table:

| Buddy path/symbol | Authority/behavior owned today | Current consumers | Could DungeonMind replace it? | Earliest deletion gate | Retain reason if any |
|---|---|---|---|---|---|

Do not recommend deleting UI/presentation merely because mechanics authority moves. Separate:

```text
producer-owned statblock persistence
product-owned orchestration/presentation
kernel-owned identity/hydration semantics
transport/deployment adapter
```

### §6I Candidate cutover shapes

Evaluate, but do not implement, at least these shapes:

1. **Conformance-only / pure adapter first**  
   One exact Buddy published Threat is transformed into the exact DungeonMind profile/resource request in a deterministic testable adapter or fixture, with no live product consumer.

2. **Product shadow consumer first**  
   Existing Buddy hydration remains authoritative while a hidden DungeonMind call receives the exact same pinned identity and its result is compared/recorded.

3. **Direct authority cutover**  
   Buddy product immediately consumes DungeonMind as sole mechanics authority.

The report should strongly prefer the smallest shape that proves the unresolved authority seam. Direct authority cutover is not acceptable merely because the happy path appears technically connectable.

For each shape record:

```text
new public/durable contract required?
new write path?
new deployment dependency?
user-visible behavior change?
failure-parity risk?
rollback boundary?
duplicate path retained?
what evidence would make promotion safe?
```

### §6J Recommendation

End with one of two outcomes.

#### If bridge-ready

```text
Disposition: READY_FOR_IDENTITY_PROFILE_BRIDGE

Smallest next PR title:
<one title>

Mission:
<one independently useful capability>

Owning repository:
<DungeonMind | DungeonMindBuddy>

Exact input:
<one real/captured predecessor shape>

Exact output:
<one contract/result>

Expected changed paths:
<bounded likely path set; no unrestricted globs>

What remains false:
<shadow consumer, promotion, demolition, etc.>

Why this is smaller than a shadow consumer:
<evidence-backed explanation>
```

#### If not ready

```text
Disposition: NOT_READY_FOR_BRIDGE

Blocking fact(s):
<exact facts>

Conflicting contracts/paths:
<paths/symbols>

Smallest decision or proof required before implementation:
<one bounded next action>
```

Do not use “needs more investigation” without naming the missing fact and its owner.

---

## §7 Evidence required to merge the reconnaissance PR

Every claim must come from current code/tests/fixtures/PR state or explicit operator evidence.

| Guarantee | Owning boundary | Evidence class | Required evidence |
|---|---|---|---|
| Current repo state is re-anchored | Git/GitHub | repository metadata | exact main SHAs + active relevant PR states |
| One real Threat is traced exactly | Buddy graph/statblock/product contracts | code + fixture/data + tests, optional manual read-only check | exact IDs/revisions/digest + symbol-by-symbol trace |
| DungeonMind input requirements are exact | DungeonMind contracts/services/tests | code + tests | exact profile/resource/hydration requirements |
| Digest/resource identity compatibility is established or blocked | both mechanics contracts | canonical fixture/type comparison | byte/semantic equivalence evidence or stop |
| Failure parity is known | both owning routes/services | tests/contract inspection | matrix with stable outcomes |
| Surface seam is known | shared Plan/Build projection code | code + component/integration tests | one insertion candidate or split concern |
| Optimization remains non-authoritative | resident/prewarm/cache owners | code + tests | keys/invalidation/head behavior documented |
| Demolition candidates are concrete | current Buddy production callers | call-site inventory | symbols + consumers + deletion gate |
| Next slice is one capability | complete report | decomposition review | one mission or explicit not-ready stop |
| No production behavior changed | git diff | diff inspection | only §4 paths changed |

### 7.1 Required commands / queries

Use repository-appropriate commands. Record exact commands and results in the handback. At minimum:

```bash
# In DungeonMindBuddy
git rev-parse HEAD
git status --short
git diff --check
git diff --name-only <base>...HEAD

# In DungeonMind
git rev-parse HEAD
git status --short
```

Also run targeted search/inspection commands sufficient to enumerate symbols and callers for the selected trace. Examples may include `rg`, focused test collection, or read-only API/test execution.

The reconnaissance does not require the full application test suite merely to merge a report. If a test is run to prove a behavioral fact, record exact command/result and whether it was run on `main`, an open PR head, or both.

### 7.2 Active-PR comparison requirement

Because #510 and #512 are likely to change the eventual consumer seam, inspect them explicitly if still open.

For each:

```text
base SHA
head SHA
mergeability/state
changed paths relevant to this trace
which current-main assumptions it supersedes if merged
whether the cutover recommendation depends on it merging first
```

Do not design the next implementation PR against a branch-only symbol without saying so.

### 7.3 Minimal live/dogfood proof

Not required to merge this reconnaissance PR unless a real campaign target cannot be established from committed exact identity evidence.

If a live read-only proof is available, the smallest useful scenario is:

```text
Open existing Plan or Build.
Open one already-published Mireward Latchling/Tripod Threat.
Record the exact graph revision/object/binding/statblock revision surfaced.
Do not edit, publish, regenerate, rebind, or mutate anything.
```

Any required product mutation belongs to a later dogfood or implementation slice.

### 7.4 Baseline failure protocol

If a focused command is already failing on its inspected base/head:

- record base and head results using the same command;
- distinguish pre-existing failure from cutover evidence;
- do not call a behavioral guarantee proven by a failing test;
- do not fix the failure in this PR.

---

## §8 Stop conditions

Stop implementation and write the report around the blocking fact if any of these occur:

1. Buddy → DungeonMind identity requires label/name matching.
2. `threat:*` → DungeonMind object identity cannot be represented deterministically without a new governed identity contract.
3. Buddy accepted-definition digest and DungeonMind `payload_sha256` cannot be demonstrated to cover the same canonical mechanics object/bytes.
4. The bridge would require current-head lookup, `latest`, search, list, filename, or local-path inference.
5. Multiple Buddy bindings require choosing a first/implicit winner to satisfy DungeonMind.
6. Hydration requires publishing or mutating either graph.
7. The proposed adapter would repair provider identity/schema/digest before DungeonMind adjudication.
8. A cache/prewarm path can alter which graph revision or mechanics resource is selected.
9. Plan and Build need separate authority implementations rather than one shared product seam.
10. #510/#512 or newer merged work materially changes the surface seam during the audit; re-anchor and report the new topology.
11. Correct shadow comparison requires a new user-facing feature.
12. A real campaign proof is impossible without inventing or reconstructing IDs from prose.
13. Deployment/secret topology is unknown and is necessary to choose between candidate code boundaries; mark it explicitly rather than guessing.
14. An active repository authority sequences a conflicting prerequisite.
15. Completing the report would require any committed path outside §4.

A stop report is a successful reconnaissance outcome when it names the exact blocking contract and smallest next decision.

---

## §9 Acceptance rubric

The PR is mergeable only when all are true:

- [ ] Exactly one docs-only reconnaissance capability was delivered.
- [ ] Current DungeonMind and DungeonMindBuddy main SHAs are recorded.
- [ ] #510 and #512, or their merged/superseding state, are explicitly reconciled.
- [ ] Optimization through the current merged runtime/prewarm/cache spine is mapped and shown non-authoritative or reported as a blocker.
- [ ] One exact real Threat or smallest exact committed substitute is traced with durable graph/statblock/revision/digest identity.
- [ ] Current Buddy hydration and surface projection call chains are named with exact paths/symbols.
- [ ] Current DungeonMind profile/resource/hydration requirements are named with exact paths/symbols.
- [ ] The identity/ownership matrix is complete.
- [ ] The predecessor-to-consumer field map is complete.
- [ ] Digest semantics are demonstrated equivalent or the report stops.
- [ ] Failure parity is mapped for success, zero/multiple, miss, unavailable, integrity failure, head advance, and reload/restart.
- [ ] Runtime/transport/deployment topology distinguishes repository truth from operational unknowns.
- [ ] The likely single future shadow insertion seam is identified, or the need to split Plan/Build is reported.
- [ ] Concrete duplicate Buddy authority candidates and their current consumers are inventoried.
- [ ] The report finishes with `READY_FOR_IDENTITY_PROFILE_BRIDGE` plus one smallest successor mission, or `NOT_READY_FOR_BRIDGE` plus exact blockers.
- [ ] No product code, tests, tracker, roadmap, runtime, deployment, secret, graph, mechanics record, or UI behavior changed.
- [ ] Actual committed paths equal the §4 allowlist.

---

## §10 Required implementation handback

Append a handback to this file before requesting review. It must include:

1. reconnaissance PR URL and exact base/head SHAs;
2. exact DungeonMind and DungeonMindBuddy inspected SHAs;
3. relevant #510/#512 state and heads or merged successors;
4. report path;
5. actual changed paths and focused diff stat;
6. exact real Threat/fixture selected and why;
7. exact commands/tests/read-only scenarios run and results;
8. evidence provenance: current main, open PR head, CI, author-local, or manual operator observation;
9. every material stale-doc/implementation conflict found;
10. stop conditions encountered; `none` if none;
11. operator waivers; expected `none`;
12. final disposition string;
13. exact smallest successor title/mission if ready;
14. confirmation that no implementation/cutover/promotion/demolition capability is claimed as delivered.

A PR description is transport metadata and does not replace the report or this handback.

---

## §11 Review posture

Review this PR as a design/reconnaissance artifact, not as prose quality alone.

The reviewer should challenge:

- any identity mapping that is asserted rather than grounded;
- any digest equivalence without canonical payload evidence;
- any “same behavior” claim that collapses miss/unavailable/integrity outcomes;
- any hidden current-head or first-winner behavior;
- any surface-local path when Plan/Build now share composition;
- any optimization described as authority;
- any deployment assumption presented as repository fact;
- any demolition recommendation that does not name current consumers;
- any successor mission that combines identity adaptation, shadow consumption, authority promotion, and deletion.

A useful report should make the next PR smaller, not merely make the architecture description longer.

---

## §12 One-line pickup instruction

```text
Trace one exact published Mireward Threat from Buddy graph identity through
current Plan/Build mechanics presentation, map the exact same pinned identity
against DungeonMind PR #17/#20/#21 requirements, and report the smallest
remaining cutover seam without changing either system.
```

---

## §13 Implementation handback — reconnaissance execution

**Execution status:** COMPLETE — `NOT_READY_FOR_BRIDGE`

### Re-anchor

- Reconnaissance PR: [Drakosfire/DungeonMindBuddy#515](https://github.com/Drakosfire/DungeonMindBuddy/pull/515)
- PR base SHA: `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd`
- PR handoff head at dispatch: `3f5a328d8326c8695e7a17be72a5a8bc22a24bae`
- Implementation/report commit: `ad8d5f11909f4805c044a83f6056e719ae3f4b73`
- DungeonMind inspected `main`: `7c311ae0d0d59d7379dee38780be509970fb3a8c`
- DungeonMindBuddy inspected `main`: `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd`
- Execution branch: `docs/statblock-dungeonmind-cutover-reconnaissance`

### Adjacent PR state

- #510 — [BUILD: insert exact World Graph reference into Canvas](https://github.com/Drakosfire/DungeonMindBuddy/pull/510): OPEN, CLEAN, MERGEABLE; base `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`; head `9ea88533686eb257beec14591451aabe6462b294`.
- #512 — [STATBLOCK: Threat parchment sheets + shared World Graph lens](https://github.com/Drakosfire/DungeonMindBuddy/pull/512): OPEN, CLEAN, MERGEABLE; base `d50d0c3a45761376185d36fb39ae3a098a5b8cfc`; head `5ec7da4341bdd2697c9c0cad4a46a693aa3f01cd`.
- #508 — [STATBLOCK: publish accepted Threat from Workbench](https://github.com/Drakosfire/DungeonMindBuddy/pull/508): merged `9d4f5a3005f87d07147c03d8eee499af3bd57aa3`; source of the selected Latchling proof.
- #511 — [OPTIMIZATION: prewarm committed World Graph revision](https://github.com/Drakosfire/DungeonMindBuddy/pull/511): merged `fd05c7f20ccae22f2f43ec24642bf70290b0d9c7`.
- #513 — [OPTIMIZATION: warm bounded surface projection recipes](https://github.com/Drakosfire/DungeonMindBuddy/pull/513): merged at Buddy `main` `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd`.

The older #510/#512 snapshot heads in this handoff were stale, but the
current open heads preserve the same exact-reference/shared-projection
topology. No branch-only symbol is claimed as current merged behavior.

### Delivered report and paths

Canonical report:

```text
Docs/Reports/REPORT-statblock-dungeonmind-cutover-reconnaissance.md
```

Changed paths for this execution:

```text
Docs/Plans/HANDOFF-statblock-dungeonmind-authority-cutover-reconnaissance.md
Docs/Reports/REPORT-statblock-dungeonmind-cutover-reconnaissance.md
```

Focused cumulative diff against PR #515 base
`9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd`:

```text
2 files changed, 1666 insertions(+)
```

No production source, tests, fixture, tracker, roadmap, runtime, deployment,
secret, graph, mechanics record, or UI path changed.

### Selected exact proof target

The report uses the real published **Mireward Latchling** because it is the
target named by the open Build #510 dogfood flow and the open Statblock #512
presentation work. The exact values are:

```text
world/campaign: eldyrwild / longmont-c2
graph revision: rev:3413bf6f5044cf2680233f5e37c90dcf
Threat node: threat:authored:d16d43d376833e38caf46dd19b1dd17f
binding: threat-statblock-binding:07ab38b331085b426bb69474
statblock: sb_7727dfeeb8074214a6a9cebf257691ff
statblock revision: rev_60b7bf03dd8d4a75a0a164ad73ce83b1
definition digest: sha256:4c843b9e8672c20d94e2594a70a62b0496f009481ac69af64dee071171e2d722
publication commit: 523e293c-02c8-41db-97bc-58db9e00891b
commit state: committed_unverified
verification: failed
```

The exact target comes from the author/operator MAGIC-D3 dogfood report at
`Docs/Reports/MAGIC-MOMENT-D3-2026-08-05.md`, committed before this PR's
reconnaissance. The report does not claim that the `committed_unverified`
revision is eligible for DungeonMind binding.

### Verification performed

Provenance labels:

- current merged main code/docs: repository inspection at the SHAs above;
- open PR state: GitHub PR metadata and cumulative file lists;
- author/operator manual observation: MAGIC-D3 report;
- author-local focused tests: commands below;
- no CI or live shadow dogfood was claimed.

Buddy focused tests, run at the PR #515 worktree:

```text
uv run pytest -q tests/test_statblock_binding_graph_contract.py tests/test_threat_query_hydration.py tests/test_dungeonmind_statblocks_client.py
........................................................................ [ 62%]
...........................................                              [100%]
115 passed in 4.25s
```

DungeonMind focused tests, run at inspected `main`:

```text
uv run pytest -q tests/unit/test_dnd_threat_mechanics.py tests/unit/test_dnd_threat_mechanics_transport_service.py tests/unit/test_dnd_threat_mechanics_api.py tests/unit/test_import_boundaries.py
....................................................                     [100%]
52 passed, 1 skipped
```

The skipped module is `tests/unit/test_dnd_threat_mechanics_api.py`, skipped
because `fastapi` is not installed in the no-extra environment. The
non-optional B.3a, transport, and import-boundary tests passed. The focused
tests do not prove the missing Buddy-to-DungeonMind identity mapping or the
missing Latchling canonical payload.

Repository checks:

```text
Buddy:
  git rev-parse HEAD
  3f5a328d8326c8695e7a17be72a5a8bc22a24bae
  git status --short
  <empty>
  git diff --check
  <no output>

DungeonMind:
  git rev-parse HEAD
  7c311ae0d0d59d7379dee38780be509970fb3a8c
  git status --short
  <empty>
```

### Material conflicts and disposition

1. The handoff's #512 head was stale. GitHub reports current open head
   `5ec7da4341bdd2697c9c0cad4a46a693aa3f01cd`; the current head was
   inspected and remains branch-only.
2. The handoff's #510 head was stale. GitHub reports current open head
   `9ea88533686eb257beec14591451aabe6462b294`; the current head was
   inspected and remains branch-only.
3. The real Latchling publication is durable but `committed_unverified` with
   failed verification codes. No implementation inferred eligibility from
   that state.
4. The checked-in exact provider fixture is Ironhide Brute, not Latchling.
   Its digest proves provider vocabulary and canonical-definition shape, not
   the selected target's byte equivalence.

No scope stop condition was encountered. These are the explicit not-ready
blocking facts, not waived failures.

**Operator waivers:** none.

**Final disposition:** `NOT_READY_FOR_BRIDGE`

**Smallest successor decision/proof:** define
`STATBLOCK: define Buddy Threat → DungeonMind D&D identity/profile bridge
contract` as a fixture-backed, conformance-only slice. It must own the
`threat:*` → `obj:*` mapping, `uses_statblock` → `dnd5e:threatens` semantics,
provider/schema/media/digest representation, exact Latchling response bytes,
and `committed_unverified` eligibility decision before a shadow consumer is
implemented.

This handback claims no identity bridge, shadow consumer, authority
promotion, cutover, or demolition capability as delivered.
