---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CON-READY / DOGFOOD-CONTINUITY campaign memory
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`
  - Branch / PR: `dogfood-continuity/candidate-generation-integrity-alignment-v1` / create after steward landing

  ## Verification pointer
  - Design authority / head: `main@55d0fbac467975d1e65ffc895f32619dac00e0a0`
  - Changed paths: handoff §4 only
  - Verification: handoff §7

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DOGFOOD-CONTINUITY candidate-generation integrity alignment v1

**Created:** 2026-09-15  
**Status:** ACTIVE — align production candidate generation with the merged Candidate Graph Admission integrity/eligibility split  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `main@55d0fbac467975d1e65ffc895f32619dac00e0a0`  
**Activation gate:** `none — PR #720 is merged/accepted, PR #715 is closed unmerged, and no open implementation PR existed at design re-anchor`  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record the exact implementation branch base at dispatch/review.  
**Candidate branch:** `dogfood-continuity/candidate-generation-integrity-alignment-v1`  
**PR title:** `DOGFOOD-CONTINUITY: align candidate generation integrity boundary`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

> The implementation worker consumes this already-checked-in ACTIVE handoff. It does not create, replace, or materially redesign its own authority document.

## §1 Mission and merge-ready invariant

**Mission:** Make production recap candidate generation hand coherent-but-currently-unsupported candidate concepts to Candidate Graph Admission unchanged, while still failing malformed candidate documents before review/admission, so the next chronological campaign-memory acceptance run measures the intended production seams rather than a disagreement between producer and consumer validation.

**Merge-ready invariant:**

> A production-generated candidate becomes `REVIEWABLE` if and only if its fully assembled document is coherent under the same candidate-document integrity definition consumed by Candidate Graph Admission; admission-eligibility issues do not mutate, delete, or suppress the exact candidate and remain for #720 admission to disposition, while any true document-integrity failure still fails closed before admission.

### Why this prerequisite is required

Current `main` already performs full typed candidate validation in `src/graph_memory/extraction/graph_preview_runner.py`, but it currently treats every typed preview error as generation failure. Candidate Graph Admission intentionally separates `invalid node_type` from document integrity and treats an otherwise coherent unsupported node kind such as `sublocation` as admission eligibility.

Therefore the current production sequence can classify the same candidate condition differently:

```text
production extraction:
  invalid node_type → FAILED / not reviewable

Candidate Graph Admission (#720):
  coherent unsupported node_type → exact candidate retained
  → unsupported_node_type disposition
```

That mismatch must be removed before the fresh chronological acceptance slice. This is not permission to make `sublocation` supported.

### Design-time corpus census

Re-census on the design base found current normalized observed-recap lineage for:

```text
Campaign 1: Sessions 1–17
Campaign 2: Sessions 1–27
Total logical recap sessions: 44
```

Historical duplicate raw recap choices remain resolved by existing normalized provenance, including C1 S2 → `Session 2 - Finishing the Job.md` and C2 S23 → `Session 23 - Mireward Gate Battle.md`. C2 S26 and S27 now exist with normalized observed-recap lineage.

This count is **not acceptance evidence** and is not hard-coded by this slice. The named successor must independently freeze its own current-corpus manifest at dispatch.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every changed path classifies the final candidate as document-integrity failure versus admission eligibility without changing candidate semantics. |
| Most likely adversarial sequence | Candidate contains one unsupported but coherent node kind → production runner marks it invalid → admission never gets the exact candidate → later batch STOP is misreported as malformed generation. |
| Will §7 detect that failure? | Yes. A deterministic cross-boundary regression must prove generation reaches `REVIEWABLE` with the exact unsupported candidate and #720 then emits `unsupported_node_type`. |
| Easiest owning boundary to under-test | Production extraction `VALIDATED/REVIEWABLE` transition followed by Candidate Graph Admission qualification. |
| Fact that forces stop/split | Fix requires ontology expansion, model/prompt changes, automatic repair, or redefining #720 admission policy rather than sharing its existing integrity classification. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-campaign-supergraph.md`; `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` |
| Design authority base | `main@55d0fbac467975d1e65ffc895f32619dac00e0a0` |
| Activation gate | none — satisfied |
| Dispatch base rule | fresh current `main` containing this handoff; exact branch base recorded at dispatch/review |
| Predecessor contract | PR #720 Candidate Graph Admission, merge `2e054ce928f4a7de14a4a7b745460c85a90f8ee1` |
| Exact input consumed | Fully assembled `dmb_candidate_graph_preview_v0@0.1` candidate emitted by production graph extraction |
| Named successor | Fresh chronological current-corpus batch admission acceptance through genesis → production generation → candidate admission → governed write |
| What remains false | No current-corpus structural PASS; no semantic benchmark/model winner; no new ontology support; no unattended batch loop |
| Explicit non-goals | candidate repair/sanitization; prompt/model tuning; ontology expansion; identity policy; source admission changes; genesis/write changes; batch runner |
| Branch / isolated checkout | `dogfood-continuity/candidate-generation-integrity-alignment-v1` after steward landing |
| Parallel lanes / collision hotspots | No open PRs at design re-anchor. Central candidate preview/integrity code is the only expected shared seam. |
| Runtime/state ownership | Not applicable; deterministic tests only, no live model or PostgreSQL acceptance run required |
| State-authority sync set after merge | Completion is recorded by the next steward/successor handoff; this implementation PR does not pre-mark itself complete. |

Authority order for this slice:

1. merged #720 behavior on current `main`;
2. `src/graph_memory/candidate_graph_preview.py` typed preview validation;
3. production extraction controller behavior;
4. durable #715-derived regression witnesses on `main` only as historical failure signatures.

PR #715 itself is closed/unmerged historical evidence and must not be imported, rebased, cherry-picked, or repaired.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Fully coherent supported candidate | Production extraction reaches `REVIEWABLE` | Same candidate reaches `REVIEWABLE` unchanged | Yes | production extraction controller |
| Coherent unsupported node kind (`sublocation`) | Typed validation currently makes extraction fail before admission | Extraction reaches `REVIEWABLE` unchanged; admission later emits explicit eligibility disposition | Yes | extraction → admission seam |
| Conflicting duplicate node/edge/beat/write ID | Typed validation fails | Still fails as candidate-document integrity; never becomes reviewable | Yes | shared integrity classifier + extraction |
| Missing edge endpoint / beat node / write target | Typed validation fails | Still fails as candidate-document integrity | Yes | shared integrity classifier + extraction |
| Malformed candidate parse | Fails typed parse | Still fails closed before review/admission | Yes | shared integrity classifier + extraction |
| Unsupported candidate plus independent integrity failure | Currently all errors collapse into validation failure | Integrity failure wins; candidate is not reviewable and is not sanitized to expose only eligibility | Yes | shared integrity classifier |
| Reviewable unsupported candidate enters #720 | Not reachable through current production runner | Exact candidate/digest remains intact and #720 owns `unsupported_node_type`, dependency dispositions, and confirmability | Yes | Candidate Graph Admission |
| #720 candidate drift / stale binding | Already blocked | Unchanged | Yes | Candidate Graph Admission confirmation |
| Profile-owned post-extraction validator failure | Fails production extraction | Unchanged; this slice does not weaken profile-specific validation | Yes | production extraction controller |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| unique `sublocation` → production typed validation → admission | `REVIEWABLE` exact candidate → explicit `unsupported_node_type`; no rewrite | W2/W3 |
| duplicate ID + unsupported kind → generation | integrity failure; no first-wins/delete path and no reviewable candidate | W1/W2 |
| supported valid candidate → integrity classification | exact candidate semantics unchanged | W4 |
| shared-classifier refactor → direct #720 duplicate witness | existing #720 behavior unchanged | W5 |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/candidate_document_integrity.py` | Own one pure shared classification of typed candidate issues into document integrity versus admission eligibility. |
| Modify | `src/graph_memory/extraction/graph_preview_runner.py` | Use shared classification so only integrity failures block `VALIDATED/REVIEWABLE`; preserve candidate bytes/semantics and profile validation. |
| Modify | `apps/live_control_server/services/candidate_graph_admission.py` | Consume the same shared integrity classifier while preserving #720 public behavior and existing wrapper/API surface. |
| Modify | `tests/test_graph_preview_runner.py` | Prove producer-side integrity/eligibility behavior and exact-candidate preservation. |
| Modify | `tests/test_candidate_graph_admission_contract.py` | Prove #720 admission behavior does not drift under classifier sharing. |

**Bounded discovery exception:** Not applicable. A required production or test path outside this lease is a stop report.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Candidate assembly/prompt/reconciliation policy is not being changed. |
| `src/graph_memory/extraction/category_candidate_graph_schema.py` | No model-output schema or node-kind expansion. |
| `src/graph_memory/identity_resolution.py` | Identity merge/reconciliation is a separate contract. |
| `src/graph_memory/extraction/recap_extraction_profile.py` | No profile/prompt/pass changes. |
| `MODEL_POLICY.json` | No model selection or tuning. |
| `corpus/**` | Read-only design evidence; no source repair. |
| `apps/live_control_server/services/recap_world_genesis.py` | Merged genesis is successor input, not this slice. |
| DungeonMind/provider/governed-write paths | Existing #720/genesis authority; production semantic changes here require a new slice. |
| `evals/**` / batch acceptance runner | Named successor only. |
| PR #715 branch/output | Historical evidence only; never active authority. |

## §6 Implementation contract

```text
Input:
  fully assembled CandidateGraphPreview-shaped mapping

Shared classification output:
  parsed typed preview
  + document-integrity issues
  + admission-eligibility issues

Invariant:
  candidate semantics are immutable;
  integrity failure blocks review/admission;
  eligibility issues do not block review and are not resolved by generation.

Failure behavior:
  typed parse failure → integrity failure
  duplicate/missing-reference/committed-state/evidence integrity error → integrity failure
  coherent unsupported node_type → eligibility issue, not generation failure
  profile post-extraction validation failure → unchanged generation failure

Replay / idempotency:
  same in-memory candidate → same issue classification
  changed candidate → classification is recomputed from changed exact input
  retry after integrity failure → new caller invocation only; no hidden repair/regeneration in this slice

Trust boundary:
  Verifies: typed candidate document coherence under the existing #720 integrity definition
  Records/trusts without proving: semantic truth, model quality, whether an unsupported concept should become supported
```

### Integrity versus eligibility matrix

| Condition | Generation result | Admission ownership | Candidate mutation permitted? |
|---|---|---|---:|
| Supported coherent candidate | `REVIEWABLE` | ordinary qualification | No |
| Unsupported but coherent node kind | `REVIEWABLE` | explicit eligibility disposition | No |
| Unmapped predicate that is otherwise coherent | preserve current generation behavior | explicit admission disposition | No |
| Duplicate candidate ID | FAILED integrity | must not reach ordinary admission | No |
| Missing edge/beat/write dependency | FAILED integrity | must not reach ordinary admission | No |
| Malformed typed parse | FAILED integrity | must not reach ordinary admission | No |
| Profile-specific validation failure | FAILED validation | not admission-owned | No |

### Compatibility rule

`apps.live_control_server.services.candidate_graph_admission.validate_candidate_document_integrity(...)` is existing consumed behavior. Preserve its callable behavior for current callers/tests; it may delegate to the new shared pure classifier rather than duplicate classification logic.

Do not introduce a second candidate schema, status, digest, disposition format, or operator workflow.

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Historical duplicate-ID class remains integrity failure | shared classifier + production runner | adversarial regression | deterministic duplicate node/edge fixture; durable #715 witness signatures remain read-only | extraction FAILED/non-reviewable; no sanitation | duplicate becomes reviewable or is silently deleted/merged solely to pass |
| Unsupported coherent kind survives generation | production runner | contract regression | fixture candidate with one unique `sublocation` and valid evidence/references | run reaches `REVIEWABLE`; exact unsupported node remains present | generation fails or rewrites/drops node |
| #720 owns unsupported disposition | extraction → admission seam | cross-boundary regression | feed exact reviewable unsupported candidate into admission prepare | explicit `unsupported_node_type`; exact candidate digest/binding retained | producer emits disposition or admission sees changed candidate |
| Integrity outranks eligibility when both exist | shared classifier | adversarial regression | duplicate ID plus unsupported node kind | integrity failure; no reviewable sanitized subset | eligibility path masks structural corruption |
| Valid candidates are unchanged | production runner | regression | existing valid deterministic extraction fixture | candidate before/after classification semantically equal | validation mutates candidate |
| #720 existing seal/confirm semantics remain | Candidate Graph Admission | regression | existing admission test cohort | duplicate/drift/nonconfirmable/eligibility tests unchanged | predecessor behavior changes |
| Profile post-validator remains authoritative | production runner | regression | existing profile validation path | still fails when profile validator fails | shared classifier bypasses profile policy |

Exact verification commands:

```bash
uv run pytest \
  tests/test_graph_preview_runner.py \
  tests/test_candidate_graph_admission_contract.py -q

uv run ruff check \
  src/graph_memory/candidate_document_integrity.py \
  src/graph_memory/extraction/graph_preview_runner.py \
  apps/live_control_server/services/candidate_graph_admission.py \
  tests/test_graph_preview_runner.py \
  tests/test_candidate_graph_admission_contract.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal live / dogfood proof

Not applicable. This slice changes deterministic boundary classification only. Do not spend model calls to prove a condition owned by pure candidate validation.

### Evidence provenance

The review handback must distinguish author-local results from independently rerun review evidence. `tests/fixtures/candidate_admission/pr715_failure_witnesses.json` may be read but not rewritten.

## §8 Required review handback

Record:

1. Review Cycle number and exact PR/branch/head SHA;
2. exact implementation branch base;
3. §1 mission/invariant disposition;
4. exact shared classifier API introduced and which existing callers now consume it;
5. W1–W5/§7 required versus produced evidence and provenance;
6. exact valid-candidate semantic equality proof;
7. exact unsupported-kind generation → admission disposition proof;
8. base/head actual changed paths versus §4;
9. any baseline failures/waivers;
10. paths outside §4 (`none` or stop report);
11. confirmation that no model/prompt/schema/ontology/identity policy changed;
12. named successor still false.

## §9 Acceptance rubric

- [ ] This steward-owned handoff was on `main` and ACTIVE before implementation dispatch.
- [ ] Production generation and Candidate Graph Admission share one candidate-document integrity classification.
- [ ] Coherent unsupported node kinds are reviewable and remain exact input for admission eligibility decisions.
- [ ] Duplicate/missing-reference/malformed candidates still fail closed before admission.
- [ ] A candidate containing both eligibility and integrity problems cannot be sanitized into success.
- [ ] Successful validation does not mutate candidate semantics.
- [ ] #720 candidate digest, disposition, confirmability, drift, and governed-confirm behavior remain unchanged.
- [ ] Profile-owned post-extraction validation remains enforced.
- [ ] No model, prompt, extraction schema, ontology, identity, source, genesis, or governed-write behavior changed.
- [ ] Actual changed paths remain inside §4.
- [ ] Fresh chronological acceptance remains unimplemented and unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- sharing the classifier requires a candidate schema/version change;
- fixing the mismatch requires adding `sublocation` or another node kind to production ontology;
- implementation needs prompt/model changes or automatic regeneration;
- candidate assembly must delete/merge/rewrite semantic objects to satisfy integrity;
- #720's accepted definition of integrity versus eligibility must change materially;
- a required path lies outside §4;
- a second independently useful operator/product workflow appears;
- deterministic owning-boundary evidence cannot prove exact-candidate preservation.

Report the stop using the standard steward format from `Docs/Process/STEWARD-CYCLE.md`.

## Claims that remain false after this slice

Even after successful merge:

- `STRUCTURAL ACCEPTANCE PASS` remains false.
- `SEMANTIC MODEL SELECTION` remains HOLD.
- No model winner exists.
- The frozen-42 DeepSeek sanitized continuation remains diagnostic only.
- PR #715 remains closed unmerged and non-authoritative.
- No fresh chronological current-corpus run has completed.
- The design-time 44-session census is not itself an acceptance manifest or result.
- `sublocation` and other unsupported concepts are not newly supported.
- No semantic benchmark, recall/precision claim, or semantic-quality improvement is established.
- No automatic sanitizer, first-wins repair, semantic deletion, retry, resume, or unattended batch ingestion loop exists.

## Named successor

After this slice is merged, reviewed, and steward re-anchored, design/dispatch:

**DOGFOOD-CONTINUITY — fresh chronological current-corpus batch admission acceptance**

That successor must independently freeze the then-current canonical recap manifest and exercise:

```text
governed recap World genesis
  → fresh production candidate generation
  → candidate-document integrity
  → Candidate Graph Admission
  → exact prior-head prepare
  → governed confirm/write
  → receipt/head verification
  → next chronological recap
```

It must stop at the first generation, admission, source, parent, or governed-write failure without caller-side candidate repair. Structural completion must not be reinterpreted as semantic model selection.