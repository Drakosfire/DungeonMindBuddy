---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CON-READY / DOGFOOD-CONTINUITY campaign memory
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → ZERO-COST REVIEW → PAID DOGFOOD → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`
  - Branch: `dogfood-continuity/current-corpus-admission-acceptance-v1`

  ## Verification pointer
  - Predecessor: PR #721 merged as `233c49f4cfe247c962def10446eee336ff9a042b`
  - Design authority base: `main@233c49f4cfe247c962def10446eee336ff9a042b`
  - Production seams are read-only; this PR owns only its acceptance harness, tests, and compact report.

  The checked-in ACTIVE handoff, cumulative diff, exact-head verification, and
  dogfood evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Created:** 2026-09-15  
**Status:** ACTIVE — predecessor #721 merged/accepted; no open implementation PR exists at design re-anchor  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → ZERO-COST REVIEW → PAID DOGFOOD → REVIEW  
**Design authority base:** `main@233c49f4cfe247c962def10446eee336ff9a042b`  
**Activation gate:** `none — #721 merged at the exact approved head; no open PRs at re-anchor`  
**Dispatch base rule:** allocate only from fresh current `main` after this handoff and steward sequencing sync are durably landed  
**Candidate branch:** `dogfood-continuity/current-corpus-admission-acceptance-v1`  
**PR title:** `DOGFOOD-CONTINUITY: prove fresh current-corpus admission continuity`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). Campaign graph architecture: [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md).

---

## §1 Mission and merge-ready invariant

**Mission:** Prove that the current campaign recap corpus can be generated fresh and admitted chronologically through the real production memory seams — governed World genesis → production candidate generation → candidate-document integrity → Candidate Graph Admission → exact-parent governed DungeonMind write — without caller-side semantic repair.

**Merge-ready invariant:**

> From one exact implementation head, the acceptance harness freezes one exact current-corpus manifest, initializes one pristine isolated World from canonical Campaign 1 party-registry authority, then processes every manifested recap exactly once in strict chronological order. For each session, production extraction generates a fresh candidate using the current production model policy; that exact candidate is either failed by its owning production boundary or passed unchanged into Candidate Graph Admission; a confirmable sealed admission is confirmed only against the exact current World head; the returned child revision is verified as the next head before the following session begins. Any source drift, generation failure, candidate-integrity failure, nonconfirmable admission, stale parent, governed-write failure, receipt/head mismatch, interruption, or authority ambiguity stops the run. The runner never repairs, sanitizes, skips, resumes, regenerates selectively, or substitutes candidate semantics in order to manufacture a PASS.

A complete run establishes **structural current-corpus acceptance only**. It does not establish semantic truthfulness, extraction recall/precision, model superiority, or production model selection.

### Locked causal order

```text
exact acceptance implementation head
        ↓
freeze current corpus manifest before model calls
        ↓
validate manifest + source bytes + isolated runtime target
        ↓
pristine acceptance World
        ↓
prepare + confirm canonical C1 recap World genesis
        ↓
D0: canonical six-PC baseline, parent = null
        ↓
for each manifested recap in chronological order:
    verify frozen source bytes still match
        ↓
    production RecapSourceAdapter / production extraction
        ↓
    fresh REVIEWABLE candidate artifact
        ↓
    exact source admission
        ↓
    exact current World mutation context
        ↓
    Candidate Graph Admission prepare
        ↓
    confirmable exact sealed decision
        ↓
    governed existing-World confirm/write
        ↓
    verify receipt child.parent == prior head
    verify current head == receipt child
        ↓
    next recap
        ↓
terminal head + compact structural acceptance report
```

There is no special first-recap path after genesis.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. This slice is one fail-closed chronological acceptance loop over existing production seams. |
| Most likely false success | The runner silently drops/rebuilds a malformed candidate, skips a failing session, resumes after partial state, or accepts against a stale parent and still reports completion. |
| Will §7 detect that? | Yes. Deterministic tests own exact-candidate forwarding, first-failure stop, no resume/skip, immutable manifest/source bytes, parent/head chaining, and explicit eligibility dispositions. |
| Easiest boundary to under-test | The transition from a REVIEWABLE production candidate into exact-parent Candidate Graph Admission and governed confirmation. |
| Fact that forces split | Any required production semantic change in extraction, source authority, identity, ontology, admission, genesis, DungeonMind write, model policy, or corpus contents. |

---

## §2 Context, authority, cohort, and runtime ownership

### Authority hierarchy

1. Current `main` production code after PR #721.
2. PR #720 Candidate Graph Admission contract.
3. Governed recap World genesis service.
4. Current session-recap normalization convention for lineage discovery.
5. Original recap files referenced by `normalized_from` as source/evidentiary authority.
6. Current production model policy as resolved by production extraction with no caller model override.

The binding distinction remains:

```text
candidate-document integrity
≠ admission eligibility
≠ governed write failure
≠ semantic quality
```

### Predecessors now true

```text
PR #720  Candidate Graph Admission          MERGED / ACCEPTED
PR #721  candidate-generation alignment     MERGED / ACCEPTED
#721 reviewed head                           f8028a51dfb7c1fb5e9481559490fa39f6146249
#721 final evidence review                   5216154953
#721 merge                                   233c49f4cfe247c962def10446eee336ff9a042b
PR #715                                      CLOSED UNMERGED / historical only
```

### Current design-time census

At design re-anchor the prepared normalized lineage still represents:

```text
Campaign 1: Sessions 1–17
Campaign 2: Sessions 1–27
Total design-time logical recaps: 44
```

**Do not hard-code `44` as acceptance truth.** The execution harness must independently freeze the then-current exact cohort before any model call and report the resulting count/digest.

### Cohort discovery and source-authority rule

Use `_normalized/` only as the deterministic lineage index that resolves one logical observed recap per `(campaign_id, session)`.

Every discovered normalized document must satisfy:

```text
normalization_schema = dmb_recap_normalized_v1
document_class = play
canon_layer = campaign
source_class = observed_session_recap
temporal_scope = session_specific
campaign_id in {longmont-c1, longmont-c2}
session == origin_session == last_updated_session
normalized_from = one repository-contained original recap path
```

The normalized document itself is **not promoted into source authority for this run**. The runner must dereference `normalized_from`; the referenced original recap bytes are the source passed through production recap normalization/extraction and exact source admission.

Freeze, at minimum, for every logical recap:

```text
campaign_id
session_id
normalized lineage path
normalized lineage SHA-256
original source path
original source SHA-256
source_artifact_id
```

Reject duplicate `(campaign_id, session)`, missing `normalized_from`, path escape, missing original source, metadata disagreement, or a non-contiguous session sequence within either campaign.

Execution order is exactly:

```text
longmont-c1 / session-1 ... max manifested C1 session
then
longmont-c2 / session-1 ... max manifested C2 session
```

No CLI session subset, start-at, skip, or resume option is permitted on the acceptance path.

### Model authority

The acceptance run exercises current production policy, not a benchmark-selected model.

```text
ProductionExtractionRequest.model_id = None
resolve through current production model policy
record resolved model_id and MODEL_POLICY.json digest in evidence
```

At this design base, the production resolver falls through `fast_smart_mini` to `gpt-5.4-mini`. Do not hard-code that value into the runner and do not compare models in this slice.

The runner adds no semantic retry/repair loop. Existing production transport/retry behavior may operate unchanged inside production extraction.

### Runtime isolation

Acceptance runtime is fixed:

```text
World ID:  dogfood-current-corpus-acceptance-v1
Database:  dmb_current_corpus_acceptance_v1
Host:      loopback only
Port:      54329
Output:    out/graph_memory/current_corpus_admission_acceptance_v1/<run-id>/
```

The World ID is a runner constant, not arbitrary operator input.

Before any genesis mutation, prove:

- the DSN is loopback, port `54329`, and exact database name above;
- the target World is pristine/uninitialized;
- the configured authority is DungeonMind;
- the implementation checkout is the exact recorded head and its corpus bytes match the frozen manifest.

If the acceptance database is not pristine, STOP and require an operator to recreate it. The runner must never drop/delete/reset a database.

No live Eldyrwild authority may be used or mutated.

### Genesis semantics

Use the existing recap World genesis service unchanged:

```text
world_id = dogfood-current-corpus-acceptance-v1
campaign_id = longmont-c1
baseline_roster_key = "1"
requested_by = current-corpus-admission-acceptance
confirming_principal = current-corpus-admission-acceptance
```

Require a sealed D0 receipt with parent `null`, current head exactly D0, and the canonical six Campaign 1 PC identity anchors. No recap facts may enter genesis.

---

## §3 Observable paths and adversarial sequences

| Observable path | Required result | Owning boundary |
|---|---|---|
| Duplicate/gapped/invalid normalized lineage | STOP before model calls or graph mutation | acceptance preflight |
| `normalized_from` missing/escaping/mismatched | STOP before model calls or graph mutation | acceptance preflight |
| Frozen original source changes before its turn | STOP before that model call | manifest/source guard |
| Wrong DSN/DB/host/port/world | STOP before genesis | runtime guard |
| Non-pristine acceptance World | STOP before genesis | recap genesis probe |
| Genesis prepare | inert | production genesis |
| Genesis confirm | exact D0, parent null, six PCs, head = D0 | production genesis + authority |
| Production extraction failure | preserve run artifacts; STOP cohort | production extraction |
| Candidate integrity failure | FAILED/non-reviewable; STOP; never admit | #721 shared integrity boundary |
| Coherent eligibility issue | candidate remains exact; admission records explicit disposition | #720 admission |
| Admission confirmable with some rejected eligibility items | allowed; record all dispositions; confirm exact sealed accepted union | #720 admission |
| Admission nonconfirmable | STOP; no governed callback | #720 admission |
| Candidate bytes/digest change after prepare | STOP; no governed callback | #720 confirm seal |
| Parent/head changes between prepare and confirm | STOP as stale; no caller retry against new head | governed write seam |
| Governed write error | prior head remains authoritative; STOP | DungeonMind write |
| Successful child write | receipt child parent == prior head; current head == child | receipt + native read |
| Interrupted process | run is incomplete/invalid; no resume-as-PASS | acceptance harness |
| Operator rerun after STOP | new run ID + newly pristine DB only; never continue old chain | acceptance harness/operator |
| Complete manifested cohort | structural PASS report bound to exact head/manifest/terminal head | acceptance report |

### Required adversarial sequences

1. **Unsupported but coherent candidate** → production marks REVIEWABLE unchanged → admission emits `unsupported_node_type` or other eligibility disposition → run may continue only if the sealed plan remains confirmable.
2. **Duplicate/conflicting candidate plus otherwise admissible content** → generation integrity failure → STOP; no first-wins/delete/sanitized subset.
3. **Candidate prepared at head N, head externally changes to N′ before confirm** → stale-parent failure → STOP; do not re-prepare and silently continue.
4. **Manifest source byte changes after freeze** → STOP before extraction for that session.
5. **Session N fails but Session N+1 exists** → N+1 is never invoked.
6. **Process dies after a successful write** → old run cannot resume and claim a continuous acceptance; a new acceptance requires a new pristine authority.

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/graph_memory_layer/run_current_corpus_admission_acceptance.py` | Operator-run, fail-closed structural acceptance harness over existing production seams. |
| Create | `tests/test_current_corpus_admission_acceptance.py` | Deterministic contract tests for manifest freeze, isolation, stop behavior, exact-candidate forwarding, and revision chaining. |
| Create | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md` | Compact exact-head acceptance result after the paid dogfood run; records PASS or first STOP without semantic overclaim. |

Runtime artifacts under `out/graph_memory/current_corpus_admission_acceptance_v1/**` are generated evidence and are not committed unless a future steward explicitly promotes a bounded artifact.

**Bounded discovery exception:** none. If implementation requires changing any production source, model, schema, corpus, or contract file outside the three paths above, STOP and return to the steward.

---

## §5 Explicitly out of scope / collision boundary

The acceptance PR must not modify:

```text
src/graph_memory/extraction/**
apps/live_control_server/services/candidate_graph_admission.py
apps/live_control_server/services/recap_world_genesis.py
apps/live_control_server/** production write/read adapters
src/graph_memory/identity_resolution.py
src/graph_memory/candidate_document_integrity.py
MODEL_POLICY.json
corpus/**
DungeonMind dependency pin/contracts
prompt/profile/schema/ontology/vocabulary files
Plan / Play / Build / Agent surfaces
```

It also must not:

- resurrect or copy PR #715 candidate output;
- sanitize or repair historical/fresh candidates;
- add support for `sublocation` or any other ontology concept;
- add a production batch-ingestion endpoint, cron, queue, resume mechanism, retry scheduler, or unattended loop;
- choose a model winner;
- score semantic truthfulness;
- mutate live Eldyrwild;
- rewrite corpus sources to make the run pass.

A real failure in any production seam is **evidence**, not permission to absorb the fix. Stop and design a focused repair slice at the owning boundary.

---

## §6 Acceptance harness contract

### Modes

The CLI may expose only two operator modes:

```text
--preflight   zero model calls; zero graph/source mutation
--execute     full fresh acceptance from pristine authority
```

Do not expose model, world, campaign subset, session subset, start-at, skip, repair, sanitize, or resume controls on the acceptance path.

### Manifest contract

Preflight computes a canonical manifest object from the lineage/source rules in §2 and a deterministic manifest SHA-256. Execution recomputes and requires exact equality before genesis and re-verifies each source digest immediately before its extraction turn.

The runtime evidence must retain the exact manifest before model calls.

### Per-session structural ledger

For every attempted recap record at least:

```text
ordinal
campaign_id / session_id
normalized path + SHA
original source path + SHA
source_artifact_id / source_revision token
extraction run_id / status / resolved model_id
candidate artifact locator / candidate digest / candidate counts
candidate integrity outcome
admission confirmable
admission dispositions by reason
accepted proposal count
sealed parent revision
proposal/decision digest(s) already exposed by production
confirm outcome / receipt child revision
verified current head after confirm
model attempts / usage / cost / wall time when production exposes them
```

Do not add a new production receipt/schema merely to make the report prettier.

### Stop result

A stopped acceptance is not a partial PASS.

The report must state:

```text
STRUCTURAL ACCEPTANCE: HOLD
first failing campaign/session
last verified good head
failure boundary
production error/diagnostic
candidate preserved? yes/no/not-produced
model calls already spent
sessions not attempted
```

### Complete result

A PASS requires:

```text
all frozen manifest entries attempted exactly once
all required writes confirmed in strict order
no caller-side candidate/source repair
no skipped/resumed session
terminal current head == final confirmed child
revision chain rooted at the exact genesis D0
report bound to exact git head + manifest digest + model-policy digest + DB/world identity
```

---

## §7 Evidence required to merge

### Zero-cost deterministic evidence

Required commands:

```bash
uv run pytest \
  tests/test_current_corpus_admission_acceptance.py \
  tests/test_recap_world_genesis.py \
  tests/test_graph_preview_runner.py \
  tests/test_candidate_graph_admission_contract.py -q

uv run ruff check \
  evals/graph_memory_layer/run_current_corpus_admission_acceptance.py \
  tests/test_current_corpus_admission_acceptance.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

The new deterministic tests must prove at least:

- canonical manifest sorting and digest stability;
- duplicate/gapped lineage rejection;
- `normalized_from` containment and original-source authority;
- source drift rejection before extraction;
- exact runtime DSN/world refusal on mismatch;
- non-pristine World refusal;
- exact candidate object/digest forwarded from extraction to admission with no mutation;
- eligibility dispositions do not trigger runner repair;
- nonconfirmable admission stops before governed confirm;
- first failed session prevents all later-session calls;
- parent/head chain must match each receipt;
- stale head stops rather than re-preparing;
- interrupted/incomplete run has no resume-as-PASS path.

### Zero-cost operator preflight

Against the exact implementation head:

```bash
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --preflight
```

Record:

- exact git head and clean/expected checkout state;
- frozen manifest count and digest;
- campaign/session ranges actually discovered;
- model-policy digest and resolved production model;
- exact acceptance DB/world target;
- pristine genesis probe;
- model calls = 0;
- durable graph/source writes = 0.

### Paid dogfood proof

Only after deterministic review is clean, execute from a pristine acceptance database:

```bash
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --execute
```

This is intentionally the real test. The command must either:

1. complete the entire frozen manifest and produce a truthful structural PASS report; or
2. stop on the first owning-boundary failure and produce a truthful HOLD report.

Do not fix production behavior and continue inside the same acceptance run.

### Review provenance

The handback must separate:

```text
author-local deterministic tests
reviewer-rerun deterministic tests
preflight observation
paid model/runtime dogfood observation
operator database recreation, if any
```

No CI run is required if the repository has none for this lane, but lack of CI must be stated.

---

## §8 Required review handback

Record:

1. Review Cycle number and exact PR/branch/head SHA;
2. exact implementation branch base;
3. §1 mission/invariant disposition;
4. actual changed paths versus §4;
5. exact manifest count/digest and discovered campaign/session ranges;
6. normalized-lineage → original-source authority proof;
7. production model-policy digest and resolved model ID;
8. preflight result with model calls/writes = 0;
9. dogfood result: PASS or first STOP only;
10. exact D0 genesis receipt/head;
11. per-session ledger location and terminal/last-good head;
12. confirmation that candidates were never rewritten/deleted/sanitized by the runner;
13. confirmation that no production/model/prompt/schema/ontology/identity/corpus path changed;
14. baseline failures/waivers, if any;
15. semantic truthfulness/model-selection claims remain false.

If PASS, the compact report in §4 must contain enough manifest/session/receipt identity to audit the claim from the recorded git head without relying on chat history.

---

## §9 Acceptance rubric and stop conditions

### Merge-ready rubric

- [ ] Handoff was ACTIVE on `main` before branch dispatch.
- [ ] Actual changed paths are exactly inside §4.
- [ ] Cohort is freshly frozen from current normalized lineage and original source bytes.
- [ ] Preflight is zero-model / zero-mutation and passes.
- [ ] Runtime target is isolated and pristine.
- [ ] Genesis produces exact canonical D0 and head verification.
- [ ] Fresh production extraction is used for every attempted recap.
- [ ] Exact candidates pass unchanged into Candidate Graph Admission.
- [ ] Eligibility rejection is explicit; integrity failure is fatal.
- [ ] Every confirmed child is bound to the exact prior head.
- [ ] First failure stops all later sessions.
- [ ] No skip/resume/repair/sanitization path exists.
- [ ] Full manifested cohort completes before structural PASS is claimed.
- [ ] Report is bound to exact implementation head and evidence digests.
- [ ] No semantic quality/model winner claim is made.

### Stop conditions

STOP and return to the steward if any of these appears:

- current corpus cannot be uniquely frozen from normalized lineage;
- original source authority is missing/ambiguous/drifted;
- acceptance requires a production code change outside §4;
- model/prompt/profile/schema/ontology/vocabulary or identity policy must change;
- a candidate must be deleted, merged, rewritten, or regenerated to continue;
- the runner would need a session skip, resume, or targeted retry mechanism;
- source admission or candidate admission needs a new durable contract;
- DungeonMind write semantics or dependency pin must change;
- the isolated World cannot be proven pristine;
- execution would touch live Eldyrwild or an unapproved database;
- deterministic tests cannot prove the fail-closed orchestration before paid execution.

### Claims that remain false after a structural PASS

Even after a complete PASS:

```text
SEMANTIC MODEL SELECTION = HOLD
no model winner exists
no semantic recall/precision/truthfulness score exists
no claim that every accepted assertion is factually correct
no claim that unsupported eligibility items should become supported
no unattended production batch ingestion exists
no resume/retry scheduler exists
no live Eldyrwild rewrite has occurred
```

### Named successor after PASS

**DOGFOOD-CONTINUITY — semantic truthfulness / current-memory evaluation contract.**

That successor may ask whether the structurally accepted World is actually a good representation of the campaign and what evidence is needed for model selection. It must not reinterpret structural completion as semantic quality.

If this slice STOPs, the immediate successor is instead one narrowly scoped repair handoff for the first failing production boundary; do not proceed to semantic evaluation until structural acceptance is rerun fresh from a pristine authority.
