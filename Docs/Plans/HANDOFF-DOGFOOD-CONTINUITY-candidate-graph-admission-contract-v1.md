---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / candidate graph admission
  - Flow: DOGFOOD-CONTINUITY / candidate graph admission contract v1
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md
  - Suggested branch: dogfood-continuity/candidate-graph-admission-contract-v1

  ## Verification pointer
  - Design authority: DungeonMindBuddy main at 68a4abae9635211bc773d8480ec6ce46b10ada5e
  - Acceptance finding: frozen-42 evidence correction at 8fe3ceab467baf94b66898670a75d0270a2e2fb2
  - Frozen notebook authority: PR #715 head 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed

  Establish one production candidate-graph admission boundary between extracted
  candidate artifacts and the existing governed DungeonMind write path. The
  boundary must never repair candidate semantics silently: it either seals an
  exact, reviewable admission plan with explicit item dispositions or fails
  closed with structured integrity diagnostics.
---

# HANDOFF — DOGFOOD-CONTINUITY candidate graph admission contract v1

**Created:** 2026-09-15  
**Status:** ACTIVE — no predecessor gate; write lease is disjoint from the active V0.2 contract-proof lane  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / campaign-memory ingestion`  
**Flow / owner:** `DOGFOOD-CONTINUITY / designing steward → implementation agent`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `68a4abae9635211bc773d8480ec6ce46b10ada5e`  
**Activation gate:** `none — satisfied`  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record the exact implementation branch base at dispatch/review.  
**Suggested implementation branch:** `dogfood-continuity/candidate-graph-admission-contract-v1`  
**PR title:** `DOGFOOD-CONTINUITY: establish candidate graph admission contract`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

> This handoff is the durable design authority for one missing production seam: candidate graph → explicit admission decision/plan → existing governed confirmation. It does not authorize a new graph engine, a new source-authority system, a model rerun, or an acceptance-run rescue.

---

## §1 Mission and merge-ready invariant

**Mission:** A product or batch caller can present one exact extracted candidate graph, its exact source identity, and one pinned World parent to a single Buddy-owned production admission boundary and receive either (a) a sealed, confirmable admission plan with explicit accepted/rejected/unresolved dispositions or (b) a structured fail-closed integrity result, so that confirmation can publish through the existing governed DungeonMind path without caller-side semantic repair.

**Merge-ready invariant:** The candidate artifact is immutable input to admission. Admission may select, reject, or leave assertions unresolved, but it may never rewrite the candidate's semantic content to make publication succeed. A confirmable plan is bound to the exact candidate digest, source identity/revision, World identity, parent revision, and identity context used at prepare; confirm re-proves those bindings before the existing governed write may advance the World exactly once.

### Binding terminology

This slice uses two different meanings of “admission” and they must remain distinct:

```text
candidate graph admission
  Buddy-owned semantic/governance boundary
  candidate artifact → accepted/rejected/unresolved dispositions → sealed plan

source admission
  existing DungeonMind-backed source-authority persistence
  SourceArtifact/SourceRevision → provider source repository
```

Do not replace, duplicate, or fork `world_graph_source_admission_adapter.py`. Candidate admission must compose with the existing source-admission/write machinery.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Exact candidate content is never repaired; every transition is either explicit disposition or fail-closed integrity error. |
| Most likely adversarial sequence | Model emits conflicting duplicate IDs or an unsupported kind → batch caller tries to “make it loadable” → some assertions disappear before governed prepare → graph advances with semantics different from the frozen candidate. |
| Will §7 detect that failure? | Yes. Exact #715-derived witnesses plus owning-boundary tests require duplicate IDs to fail candidate integrity, unsupported kinds to become explicit admission rejections, and confirm to reject candidate/source/parent drift. |
| Easiest owning boundary to under-test | The seam between raw candidate integrity and typed/admissible assertion mapping; current `load_typed_candidate_graph()` collapses those concerns. |
| Fact that forces stop/split | If the only way to implement the seam is to change DungeonMind generic contracts, replace source admission, introduce a second durable graph-write command, or define model-generation policy beyond admission semantics. |

---

## §2 Context, authority, and lane

### Why this slice exists

The frozen-42 acceptance experiment exposed a missing architectural seam rather than merely a malformed-file bug.

Historically the repository evolved two strong but separately conceived paths:

```text
recap/source
  → extraction
  → candidate graph / review artifact
```

and:

```text
reviewed contribution
  → identity/source governance
  → DungeonMind governed write
  → immutable World revision
```

Interactive/operator flows could bridge these with product-specific review logic. A chronological batch replay required a general production contract between them and discovered that no such boundary was explicit enough. The acceptance runner consequently accumulated semantic knowledge that belongs in production admission: kind qualification, relationship qualification, identity outcomes, source binding, and eventually forbidden candidate repair.

Exact reviewed evidence:

```text
acceptance evidence head:
8fe3ceab467baf94b66898670a75d0270a2e2fb2

experiment verdict:
STRUCTURAL ACCEPTANCE HOLD
SEMANTIC MODEL SELECTION HOLD

OpenAI exact-frozen replay:
PASS @ f24d109d0cc0c6b1607dc82034b535c8345681df

DeepSeek exact-frozen replay:
STOP at C2 S9
  - conflicting duplicate node_id values
  - unsupported node_type = sublocation

sanitized DeepSeek Session-42 chain:
DIAGNOSTIC ONLY @ 04ff89083aabac75c4b7b135e685d1b1efefd44c
```

The forbidden sanitizer proved the missing seam: it kept first duplicate IDs, dropped later duplicates, dropped unsupported node types, then cascaded deletions into edges / beat references / proposed writes. This handoff prohibits that entire class of behavior.

| Field | Required content |
|---|---|
| Parent authority | `ARCHITECTURE-campaign-supergraph`, existing governed extract/promote path, merged governed recap genesis (#718), reviewed frozen-42 HOLD evidence `8fe3ceab…` |
| Design authority base | `68a4abae9635211bc773d8480ec6ce46b10ada5e` |
| Activation gate | none — satisfied |
| Dispatch base rule | fresh current main containing this handoff |
| Predecessor contract | current `prepare_extract_promote` / sealed promote proposal / DungeonMind governed-write integration; do not replace them wholesale |
| Exact input consumed | candidate graph payload + canonical candidate digest; exact source artifact/revision/URI; world/campaign/session scope; pinned current mutation context / parent revision |
| Named successor | fresh chronological batch acceptance using this admission seam; model-selection/evaluation design remains separate |
| What remains false | no 42-session PASS; no model winner; no automatic unattended corpus ingest loop; no UI redesign; no regeneration of #715 candidates |
| Explicit non-goals | extraction prompt changes, candidate regeneration, graph ontology redesign, vNext runtime cutover, relationship-quality optimization, retrieval benchmark design |
| Branch / isolated checkout | allocate only after dispatch from fresh current main |
| Parallel lanes / collision hotspots | active V0.2 contract-proof lane owns `pyproject.toml`, `uv.lock`, `Docs/Contracts/**`, `tests/fixtures/vnext/**`, and its focused contract test. This slice must not touch those. |
| Runtime/state ownership | focused tests use isolated temporary authority; any real PostgreSQL witness must use a disposable non-live database and explicit world ID |
| State-authority sync set after merge | steward updates this handoff disposition and current roadmap/tracker state; implementation PR does not rewrite historical acceptance handoffs |

### Binding architectural decision: candidate integrity vs admission eligibility

This PR must make the distinction explicit.

**Candidate-document integrity failures** invalidate the candidate as a coherent artifact and block preparation entirely. Examples include:

- malformed/non-object payload;
- missing required candidate identity fields;
- duplicate object/assertion identifiers where the candidate contract requires uniqueness;
- conflicting duplicate `node_id` definitions;
- candidate-internal references that violate the existing candidate document's own referential-integrity rules;
- candidate/source/run scope disagreement;
- evidence references that do not bind to the exact source authority required by the existing exact-run contract.

These return a structured candidate-integrity failure. They are never repaired by first-wins, deduplication, relabeling, or deletion.

**Admission eligibility failures** may be item-level and do not make the candidate document disappear or mutate. Examples include:

- a structurally coherent candidate node kind that current World admission cannot express (`sublocation` is the motivating witness);
- unmapped relationship predicate;
- endpoint kind not admitted;
- identity collision / unresolved identity;
- current-parent binding conflict;
- another assertion-level inexpressibility already represented by current qualification logic.

These become explicit rejected/unresolved dispositions in the admission plan. They may leave the plan confirmable if at least one assertion is truthfully admissible and no candidate-level integrity failure exists.

**Important:** do not solve `sublocation` by silently deleting it, coercing it to `location`, or adding it to the durable ontology merely to make this test pass. This slice owns the admission disposition, not a broad ontology decision. If the implementation can prove an already-established canonical mapping exists in current production authority, it may use that existing mapping. Otherwise record `unsupported_node_type` (or a comparably precise stable reason) and leave ontology expansion to a successor.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Existing exact-run Graph Review prepare | resolves run, validates evidence/scope, directly enters `prepare_extract_promote` | delegates to the single candidate-admission boundary; existing API meaning remains compatible | Yes | live-control service + candidate admission |
| Programmatic/batch prepare | caller currently has to know several production seams and failure quirks | one callable production boundary accepts exact candidate/source/parent facts and returns sealed plan or structured failure | Yes | candidate admission service |
| Candidate with conflicting duplicate ID | typed load fails or external runner may sanitize | deterministic candidate-integrity failure; zero graph/source mutation | Yes | candidate integrity validator |
| Candidate with unsupported node kind | whole typed load may fail before useful dispositions exist | exact candidate preserved; item receives explicit admission rejection; dependent assertions receive explicit reasons rather than deletion | Yes | candidate admission qualification |
| Candidate with unmapped predicate/endpoint kind | existing qualification skips/rejects in several places | same semantic decision is represented explicitly in one admission plan | Yes | admission qualification / proposal projection |
| Prepare success | existing promote package seals accepted/rejected/unresolved facts but does not make candidate identity a first-class contract | plan seals candidate digest + source + world + parent + dispositions + identity snapshot | Yes | plan sealing |
| Confirm after candidate drift | candidate bytes/content may not be part of confirm-time trust boundary | recompute candidate digest from exact input/resolved run and refuse confirm on drift | Yes | confirmation service |
| Confirm after source drift | existing source verification exists | retain/reuse exact source verification; drift refuses publication | Yes | existing source verification/write path |
| Confirm after parent drift | existing governed write fails stale parent | retain fail-closed behavior; no source/graph partial success may be reported as committed | Yes | DungeonMind governed write |
| Retry same exact plan/input | existing idempotency semantics vary by underlying write | same exact confirmed write returns same child/idempotent result per existing provider contract; no second semantic mutation | Yes | governed write |

### Required adversarial sequences

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| duplicate-ID candidate → prepare | structured candidate-invalid result; no plan marked confirmable; head/source state unchanged | candidate-admission unit + service regression |
| valid node + unsupported `sublocation` → prepare | candidate remains exact; supported item can be accepted; `sublocation` is explicitly rejected; no in-memory deletion masquerades as candidate input | admission-contract test |
| rejected node → relationship targeting it | relationship receives explicit dependency rejection such as `endpoint_not_admitted`; it is not silently dropped | admission-contract test |
| prepare valid plan → mutate candidate → confirm | digest mismatch; zero head movement | confirm adversarial test |
| prepare valid plan → mutate source → confirm | existing source mismatch; zero head movement | source/confirm adversarial test |
| prepare at parent D_N → advance head elsewhere → confirm old plan | stale-parent failure; old plan cannot publish | governed-write regression |
| valid plan → confirm → retry exact confirm | provider-defined idempotent same-child/no-second-revision result | PG owning-boundary witness |

---

## §4 Files in scope — write lease

Expected paths are intentionally narrow. The implementation should prefer factoring existing logic into the new boundary over copying it.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/candidate_graph_admission.py` | stable Buddy-owned plan/result/disposition value models if a dedicated model module is warranted |
| Create | `apps/live_control_server/services/candidate_graph_admission.py` | one production prepare/confirm orchestration boundary reusable by exact-run and batch callers |
| Modify | `apps/live_control_server/services/extract_promote.py` | delegate existing exact-run prepare/confirm behavior through the candidate-admission boundary without changing product semantics |
| Modify | `src/graph_memory/candidate_graph_to_contribution.py` | separate candidate-document integrity from admission mapping only as required; no silent repair |
| Modify | `src/graph_memory/extract_promote_ops.py` | reuse/refactor existing gate + sealed proposal mechanics behind the admission boundary |
| Modify | `src/graph_memory/extract_promote_proposal.py` | bind candidate digest / explicit disposition data into the sealed plan if current proposal schema cannot prove §1 |
| Modify | `apps/live_control_server/integrations/dungeonmind/assertion_qualification.py` | only if needed to expose existing qualification outcomes as structured admission dispositions; no new lossy semantic coercions |
| Create | `tests/test_candidate_graph_admission_contract.py` | owning-boundary success/adversarial contract tests |
| Create | `tests/fixtures/candidate_admission/**` | minimal or exact durable witnesses, including #715-derived failure evidence if chosen |

### Bounded discovery exception

```text
Directory:
  tests/
  apps/live_control_server/services/
  src/graph_memory/

Maximum additional modified existing paths:
  3

Allowed path kinds:
  focused existing regression tests;
  one existing shared value-model/helper module needed to avoid duplication;
  one exact-run service test module if present.

Decision rule:
  only when the existing owning boundary already lives there and adding a
  parallel helper/test would duplicate authority. Record every discovered path
  in handback before editing it.
```

### PR #715 evidence access exception

PR #715 is **read-only input authority**, not part of this implementation branch.

Exact frozen authority:

```text
PR: #715
head: 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
candidate freeze head recorded by its manifest:
d6e2599bbabb9719bc92601f7bc1ad8b69411e98
```

The implementation may read exact candidate artifacts from that head and may copy only the minimum durable regression evidence needed into `tests/fixtures/candidate_admission/**`.

Preferred witnesses:

```text
DeepSeek C2 S9
  duplicate candidate:miss-thistlebottoms-emporium with conflicting kinds
  duplicate candidate:sputtering-flask
  candidate:medical-wing node_type=sublocation

DeepSeek C2 S12
  duplicate candidate:crimson-chorus
```

Do not modify, rebase, regenerate, or merge #715.

### Repository-state decision authority for PR #715

The user explicitly delegates **the lifecycle decision** for PR #715 to this slice.

This supersedes the earlier acceptance handoff's narrow rule that #715 could close only after `STRUCTURAL ACCEPTANCE PASS`. That old gate governed successful retirement of the acceptance experiment. The experiment is now truthfully `STRUCTURAL ACCEPTANCE HOLD`, and this new handoff may decide that the notebook has nonetheless completed its evidentiary purpose once the failure is durably captured in the production admission contract.

The implementation handback must choose exactly one:

```text
PR715_DISPOSITION = KEEP_OPEN_AS_FROZEN_AUTHORITY
PR715_DISPOSITION = CLOSE_UNMERGED_AFTER_THIS_PR_MERGES
PR715_DISPOSITION = ARCHIVE_MINIMUM_WITNESS_THEN_CLOSE_UNMERGED
```

Decision criteria:

1. Can the exact admission failure that matters (including C2 S9 duplicate-ID conflict and unsupported `sublocation`) be reproduced from durable mergeable evidence without depending on an open #715 PR?
2. Does any named successor still need the exact 42+42 candidate corpus/manifest rather than only the preserved regression witnesses?
3. Does #715 contain any production-worthy behavior not already merged or deliberately rejected?
4. Would closing #715 remove the only practical authority needed to distinguish candidate-generation defects from admission behavior?

The implementation agent **decides and explains** the disposition. It does not merge #715. Unless the steward explicitly asks otherwise during review, actual close/comment state mutation is a post-review/post-merge steward action. Closing must not delete the branch.

---

## §5 Explicitly out of scope / collision boundary

| Path / capability | Why this slice must not touch or claim it |
|---|---|
| `pyproject.toml`, `uv.lock`, `Docs/Contracts/**`, `tests/fixtures/vnext/**`, `tests/test_v0_2_dungeonmind_vnext_contract_acceptance.py` | active V0.2 contract-proof write lease |
| `apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py` | existing source-admission authority; compose with it, do not replace/fork it in this slice |
| DungeonMind generic contracts / repository | candidate admission is Buddy domain logic; provider schema changes are a stop/rebrief |
| extraction prompts/model profiles | this slice consumes candidate artifacts; it does not change generation |
| #715 candidate files in place | frozen read-only notebook evidence |
| acceptance runner under `tools/run_frozen_42_session_acceptance.py` | historical diagnostic lane; do not rescue the experiment by adding new repair logic |
| UI component changes | existing API/UI may continue consuming compatible prepare results; UI redesign is not needed to prove the seam |
| broad relationship ontology changes | admission may reject unsupported predicates; ontology expansion is a successor |
| adding `sublocation` to durable graph ontology solely for this test | unsupported-kind disposition is sufficient for this slice |
| new unattended batch CLI | successor uses this boundary; this PR establishes the reusable production seam first |
| model winner / semantic benchmark | remains HOLD and separately designed |

---

## §6 Implementation contract

### A. Conceptual pipeline

```text
exact extraction artifact
        ↓
CandidateDocument integrity check
        ↓
coherent candidate
        ↓
Candidate Graph Admission prepare
  - exact candidate digest
  - exact source authority
  - exact World + parent
  - identity resolution
  - assertion qualification
  - explicit accepted/rejected/unresolved dispositions
        ↓
sealed CandidateAdmissionPlan
        ↓
Candidate Graph Admission confirm
  - recompute candidate digest
  - re-prove source
  - verify sealed plan
  - verify current parent / identity binding
        ↓
existing DungeonMind governed write
        ↓
exactly one child revision or no graph mutation
```

### B. Input / output

```text
Input — prepare:
  exact candidate graph payload
  canonical candidate digest computed by repository-owned code
  candidate locator/run identity when available
  source_artifact_id
  source_revision_id / exact source digest
  source URI / exact-run source authority
  world_id
  campaign/session scope carried by the source/run contract
  pinned World mutation context / parent revision
  optional standing-context contribution under existing rules
  prepared_by

Output — prepare success:
  CandidateAdmissionPlan (name may vary, semantics may not)
    schema/version
    plan_id
    plan_digest
    candidate_digest
    candidate identity/locator when available
    source artifact + revision identity
    world_id
    parent_revision_id
    accepted assertion/proposal identities
    rejected assertion/item dispositions + stable reasons
    unresolved identity dispositions
    identity snapshot / ledger binding already required by governed write
    confirmable flag
    existing sealed governed-write effect/review package or exact equivalent

Output — prepare integrity failure:
  structured error/result
    candidate_invalid / source_mismatch / scope_mismatch / evidence_invalid / ...
    stable diagnostics
    confirmable = false (if represented as a result)
  zero durable mutation

Input — confirm:
  sealed plan
  exact candidate payload resolved again from trusted run/caller input
  exact source authority resolved again
  confirming principal
  optional explicit accepted assertion selection under existing Graph Review rules

Output — confirm:
  existing governed-write receipt / child revision identity
  plus enough admission identity to prove which plan/candidate/source produced it
```

### C. Candidate digest

There must be one repository-owned deterministic digest contract for the candidate semantic document.

Preferred rule:

```text
sha256(canonical JSON serialization of the complete candidate payload)
```

with stable sorted keys / separators and no semantic filtering.

If the existing ExtractionRun manifest already owns an exact candidate digest with compatible semantics, reuse that exact contract instead of inventing a second digest. If it hashes raw file bytes, it is acceptable to bind both the existing file digest and a canonical semantic digest, but do not silently replace one with the other. The handback must state the chosen authority and why.

The digest must be computed **before** admission qualification. Qualification never changes what the digest means.

### D. Candidate-document integrity matrix

| Situation | Required outcome | Repair permitted? |
|---|---|---:|
| exact coherent candidate | continue to admission qualification | No repair needed |
| duplicate `node_id`, same or different kind | candidate invalid; fail closed with colliding IDs identified | No |
| conflicting duplicate semantic object | candidate invalid | No |
| malformed/missing required ID | candidate invalid | No |
| internal dangling reference prohibited by existing candidate contract | candidate invalid | No |
| source/run scope mismatch | candidate invalid for this admission | No |
| evidence not bound to exact source/span under exact-run rules | candidate invalid for this admission | No |
| unsupported but structurally coherent node kind | candidate remains exact; item rejected for admission | No |
| unsupported predicate | candidate remains exact; relationship rejected for admission | No |
| identity ambiguous/collision | candidate remains exact; item unresolved/rejected under current identity rules | No |

### E. Admission disposition vocabulary

Reuse existing stable reason names where they already exist. At minimum the resulting plan/evidence must distinguish these classes even if exact strings differ:

```text
candidate integrity:
  duplicate_node_id
  duplicate_edge_id / duplicate_assertion_id as applicable
  missing_required_id
  invalid_internal_reference
  run_scope_mismatch
  evidence_invalid

admission eligibility:
  unsupported_node_type
  unmapped_predicate
  endpoint_kind_not_admitted
  parent_binding_mismatch
  identity_ambiguous
  identity_blocked_collision
  source_or_assertion_inexpressible
```

Do not turn a candidate-integrity failure into a collection of silently dropped assertions merely to keep a batch moving.

### F. Confirmation trust boundary

```text
Verifies at confirm:
  sealed plan digest/signature contract already used by promote proposal
  candidate digest recomputed from exact candidate input
  source revision/content identity
  world_id
  parent revision / current head compatibility
  sealed identity ledger/snapshot contract
  selected assertion IDs belong to the sealed accepted set

Records/trusts without re-deciding:
  admission dispositions already sealed by prepare
  operator selection among already-admissible assertions
```

Confirm must not re-run a different semantic sanitizer or widen the accepted set.

### G. Commit model

```text
Prepare:
  inert — no source or graph mutation

Commit point:
  existing DungeonMind governed write transaction/path

Before commit:
  candidate/source/plan/parent mismatch → no graph mutation

After commit:
  return exact child / existing provider receipt semantics

Partial failure:
  never report structural success when no child exists;
  preserve existing provider atomicity/idempotency guarantees;
  do not introduce a second source-write + graph-write choreography outside the
  already reviewed DungeonMind path.
```

### H. Existing exact-run compatibility

`apps/live_control_server/services/extract_promote.py::prepare` remains a product entry point. After this PR it should be a thin exact-run resolver/evidence projection shell around the candidate-admission boundary rather than a second semantic implementation.

Existing user-visible behavior should remain compatible:

```text
runId resolves exact candidate/source
→ same scope/evidence rules
→ admission prepare
→ existing ExtractPromotePrepareResponse projection
```

No route/UI change is required to satisfy this handoff.

---

## §7 Evidence required to merge

Every material invariant clause needs proof at its owning boundary.

| Guarantee / invariant clause | Owning boundary | Evidence class | Expected evidence | Stop condition |
|---|---|---|---|---|
| Candidate digest covers complete pre-qualification candidate | candidate admission | contract | change any semantic field → digest changes; qualification does not alter digest input | digest derived from filtered/sanitized payload |
| Duplicate IDs fail closed | candidate integrity | adversarial | exact/minimal #715 C2 S9 witness identifies duplicates; no confirmable plan | first-wins/dedupe behavior remains |
| Unsupported `sublocation` is explicit admission disposition | admission qualification | regression | exact/minimal medical-wing witness remains in candidate digest and appears as rejected item | node silently deleted/coerced |
| Rejected-node dependent edge is explicit | admission qualification | adversarial | edge reports endpoint-not-admitted/dependency reason | edge disappears without disposition |
| Existing supported candidate remains publishable | service + governed write | regression | prepare creates confirmable plan; confirm publishes expected child | new seam blocks ordinary product path |
| Prepare is inert | service / PG authority | owning-boundary | source/head/revision counts unchanged after prepare | prepare mutates source or graph |
| Candidate drift blocks confirm | confirm boundary | adversarial | mutate candidate after prepare → stable digest mismatch; head unchanged | stale plan publishes |
| Source drift blocks confirm | existing source verification | adversarial | mutate source → mismatch; head unchanged | stale source publishes |
| Parent drift blocks confirm | governed write | adversarial | advance head, confirm old plan → stale-parent error | fork/rewind/alternate parent |
| Exact retry is idempotent | governed write / PG | regression | same exact confirmed input does not create second semantic child | duplicate revision/contribution |
| Exact-run product path uses same semantic seam | extract-promote service | regression | existing focused prepare/confirm tests pass through candidate admission | duplicate qualification logic remains |
| No caller-side sanitizer required | code/static + witness | regression | no path mutates candidate to satisfy typed load; #715 diagnostic sanitizer is not copied | repair helper appears in production/batch path |
| #715 disposition is evidence-based | review handback | lifecycle decision | one required disposition enum + criteria/evidence | vague “close later” / merge recommendation |

### Required focused tests

At minimum add and run:

```bash
uv run pytest -q tests/test_candidate_graph_admission_contract.py
```

Also run the existing focused cohorts that own:

```text
extract/promote prepare + confirm
candidate graph → contribution mapping
DungeonMind governed write / stale parent / idempotency
source admission / source mismatch
PC identity normalization
```

Discover their current exact filenames from `main` and list them in the handback; do not guess stale names if repository organization changed.

Then run:

```bash
uv run ruff check \
  apps/live_control_server/services/candidate_graph_admission.py \
  tests/test_candidate_graph_admission_contract.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

If Ruff path differs because the service was sensibly factored under an existing module rather than a new file, report the exact command used.

### Required real-PostgreSQL witness

Use a disposable non-live database and unique World ID. No model calls.

Prove this sequence:

```text
D_N exists
  ↓
prepare valid candidate A
  → inert
  → confirmable
confirm A
  → D_N+1

prepare candidate B containing:
  one supported assertion
  one structurally coherent unsupported node_type = sublocation
  → candidate digest includes both
  → supported assertion accepted
  → sublocation explicitly rejected
confirm accepted subset
  → D_N+2

prepare candidate C with conflicting duplicate node_id
  → candidate-integrity failure
  → no confirmable plan
  → head remains D_N+2
```

Capture exact parent/child IDs, candidate digests, disposition counts/reasons, source identities, and zero-model proof.

This is a seam witness, not a fresh 42-session acceptance run.

### #715 witness proof

Read exact #715 head `820fe3aa…` and prove at least:

```text
C2 S9 duplicate-ID failure is classified as candidate integrity failure
C2 S9 medical-wing sublocation can be classified independently as an explicit
admission rejection when placed in an otherwise coherent witness
C2 S12 duplicate candidate:crimson-chorus is candidate integrity failure
```

Do not run a model. Do not rewrite #715.

---

## §8 Required review handback

Return all of the following.

### Activation / branch provenance

```text
design authority base:
implementation branch base:
branch:
PR:
head:
```

### Admission contract summary

```text
candidate digest authority:
candidate-integrity validator:
admission prepare entry point:
admission confirm entry point:
sealed plan schema:
source admission reused from:
governed write reused from:
```

### Exact disposition matrix

Report observed results for:

```text
ordinary supported candidate
duplicate node ID
unsupported sublocation
unmapped predicate
endpoint rejected because node not admitted
identity collision/ambiguity
candidate drift after prepare
source drift after prepare
parent drift after prepare
exact confirm retry
```

### Changed paths

Exact list and diff stat.

Paths outside §4 / bounded discovery:

```text
none
```

or STOP report.

### Evidence

Include exact focused test commands/results, PG witness details, and whether any environment-gated test skipped.

### PR #715 disposition decision

Choose exactly one and justify it against the four criteria in §4:

```text
PR715_DISPOSITION = KEEP_OPEN_AS_FROZEN_AUTHORITY
PR715_DISPOSITION = CLOSE_UNMERGED_AFTER_THIS_PR_MERGES
PR715_DISPOSITION = ARCHIVE_MINIMUM_WITNESS_THEN_CLOSE_UNMERGED
```

If closure is chosen, name the durable replacement authority (fixture/report/test paths and exact source SHA/path provenance) that makes the open PR unnecessary.

If keep-open is chosen, name the exact future question that still requires #715 rather than generic regression fixtures.

### Named successor

State explicitly that this PR does **not** execute the next full batch experiment. Recommend one next bounded slice based on evidence, expected to be one of:

```text
fresh chronological batch admission acceptance
candidate-generation contract hardening
ontology decision for currently unsupported candidate kinds
semantic/query evaluation design
```

Do not implement it here.

---

## §9 Acceptance rubric

- [ ] Handoff was checked in by the steward before implementation dispatch and was ACTIVE at dispatch.
- [ ] One production candidate-admission boundary exists and is reusable outside the interactive UI path.
- [ ] Candidate input semantics are never silently rewritten to make admission succeed.
- [ ] Candidate-document integrity failures are distinct from item-level admission rejections/unresolved outcomes.
- [ ] Duplicate IDs fail closed with structured diagnostics.
- [ ] Unsupported `sublocation` is preserved in exact candidate identity and receives an explicit admission disposition, not deletion/coercion.
- [ ] Admission plan binds exact candidate digest, source identity, world, parent, and identity context.
- [ ] Confirm re-proves candidate/source/parent bindings before publication.
- [ ] Prepare is inert.
- [ ] Existing DungeonMind governed write remains the only graph commit path.
- [ ] Existing source-admission authority is reused, not forked.
- [ ] Existing exact-run Graph Review path delegates to the same semantic admission seam.
- [ ] Real-PG witness proves success, partial eligibility, fatal candidate integrity failure, and zero head movement on failure.
- [ ] No model calls / candidate regeneration occur.
- [ ] No V0.2 write-lease collision occurs.
- [ ] Actual changed paths remain within §4 / bounded discovery.
- [ ] PR #715 receives one explicit evidence-based lifecycle decision.
- [ ] #715 is never merged by this slice.
- [ ] Named successor remains unimplemented.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- candidate admission cannot be expressed without changing DungeonMind generic contracts;
- implementation needs a second graph-write/persistence command instead of the existing governed write;
- source admission must be duplicated/replaced rather than reused;
- `sublocation` requires an ontology/product decision larger than explicit rejection to satisfy the invariant;
- candidate generation/prompts must change to make admission work;
- full-corpus model regeneration becomes necessary;
- the only implementation is to mutate/sanitize candidates before qualification;
- current product exact-run path and batch/programmatic admission cannot share one semantic boundary;
- confirm cannot bind/re-prove candidate digest without a new durable external service outside this slice;
- required path collides with the active V0.2 lease;
- a required path falls outside §4/bounded discovery;
- exact #715 evidence differs materially from the failure described here;
- real PostgreSQL witness reveals source/graph partial commit behavior not covered by the existing governed-write contract;
- a second independently useful capability is required.

Stop report:

```text
Stop condition:
Invariant clause affected:
Exact candidate/source/parent involved:
Current behavior:
Why silent repair or local workaround is forbidden:
Required contract/architecture decision:
Affected paths/ownership layers:
PR #715 lifecycle impact:
Proposed successor/rebrief:
```

---

# Expected end state

A successful merge lets us say:

```text
Extraction may produce candidate artifacts that contain ideas the current World
cannot admit.

That is no longer a batch-runner problem.

Every exact candidate enters one production admission boundary.
The boundary proves candidate integrity, preserves the exact candidate identity,
resolves identity against one pinned World parent, explicitly classifies every
admissible/rejected/unresolved assertion, and seals that decision.

Confirmation re-proves the candidate, source, and parent and then uses the
existing governed DungeonMind write path.

No caller needs to delete, coerce, deduplicate, or otherwise repair candidate
semantics merely to get data into the graph.
```

Only after that seam exists should a successor attempt another chronological batch acceptance run.