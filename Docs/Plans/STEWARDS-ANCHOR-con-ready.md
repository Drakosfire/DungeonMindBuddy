# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-15  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main@6cc58dafd6cd27741c53f5f275de080ff5d3cc6f` — successor handoff landed and predecessor authority consumed  
**Last product capability merge:** PR #721, merge `233c49f4cfe247c962def10446eee336ff9a042b`  
**Current forcing function:** IMPLEMENT + DOGFOOD fresh chronological current-corpus admission acceptance  
**Active implementation authority:** [`HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md)  
**Consumed predecessor:** [`HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md)  
**Consumed admission contract:** [`HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md)  
**Campaign graph architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)

> This is the current sequencing authority. Repository truth supersedes old chat summaries, historical notebook branches, and stale `CURRENT` prose in older roadmaps/handoffs.

---

## 0. Pickup rule

### Coding / implementation agent

Do not reconstruct this slice from chat history or old experiments. Read, in order:

1. [`HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md) — **ACTIVE implementation authority**;
2. [`HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md) — consumed producer-boundary predecessor;
3. [`HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md) — consumed admission semantics;
4. only the production seams that the ACTIVE handoff tells you to call/read and the three §4 write-lease paths.

Candidate implementation branch:

```text
dogfood-continuity/current-corpus-admission-acceptance-v1
```

The implementation worker owns only the three paths in handoff §4. Production extraction, source authority, genesis, admission, identity, ontology, model policy, corpus, and DungeonMind write code are **read-only** in this slice.

If the acceptance run discovers a defect in one of those production seams, STOP and return evidence to the steward. Do not repair production behavior inside the acceptance runner.

### Fresh designing/review agent

Re-anchor exact `main`, open PR state, the ACTIVE handoff, and any implementation PR before judgment. Review exact heads by the handoff invariant. Do not advance to semantic-quality/model-selection work unless structural acceptance completes and the current cycle is merged/synchronized.

At successor design re-anchor there were **no open PRs**.

---

## 1. Current campaign-memory truth

### 1.1 Governed recap World genesis exists

Production already provides:

```text
canonical Campaign 1 party registry
  → inert sealed genesis prepare
  → governed zero-parent DungeonMind confirm
  → D0 containing canonical PC identity anchors only
  → ordinary existing-World mutation thereafter
```

Genesis does not contain recap facts.

### 1.2 Candidate Graph Admission is production authority

PR #720 is merged/accepted.

```text
reviewed head: 1d490928b556a8672b56d9f4b6c4fca35e3c4e54
final review: 5213358854
merge: 2e054ce928f4a7de14a4a7b745460c85a90f8ee1
```

Durable rule:

> The exact candidate is immutable input. Admission can accept, reject, defer, or leave meaning unresolved; it may not rewrite candidate semantics merely to make publication succeed.

### 1.3 Production generation now agrees with admission on integrity versus eligibility

PR #721 is merged/accepted.

```text
reviewed head: f8028a51dfb7c1fb5e9481559490fa39f6146249
formal review cycles: 2
final evidence review: 5216154953
merge: 233c49f4cfe247c962def10446eee336ff9a042b
```

The shared boundary now means:

```text
true candidate-document corruption
  → production FAILED / non-reviewable

coherent unsupported candidate concept
  → production REVIEWABLE unchanged
  → Candidate Graph Admission owns explicit eligibility disposition
```

This removed the final known prerequisite mismatch before a fresh chronological acceptance run.

### 1.4 PR #715 remains retired

```text
PR #715
CLOSED UNMERGED
head 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
```

Use only durable witnesses on `main`. Do not resurrect, sanitize, repair, cherry-pick, or treat #715 candidate output as current authority.

### 1.5 Historical frozen experiment remains historical HOLD evidence

```text
OpenAI exact-frozen replay: PASS
DeepSeek exact-frozen replay: STOP at C2 S9
DeepSeek sanitized continuation: DIAGNOSTIC ONLY
STRUCTURAL CURRENT-CORPUS ACCEPTANCE: HOLD
SEMANTIC MODEL SELECTION: HOLD
```

The current slice does not rerun or repair the frozen experiment. It generates candidates fresh from current production code and current source authority.

---

## 2. Current corpus context

Design-time normalized observed-recap lineage currently covers:

```text
Campaign 1: Sessions 1–17
Campaign 2: Sessions 1–27
Total design-time logical recaps: 44
```

This count is **not** the acceptance manifest and must not be hard-coded.

The ACTIVE harness must freeze the then-current cohort before model calls. `_normalized/` recaps are lineage/index authority only. Each entry must resolve `normalized_from`; the referenced original recap bytes are the source/evidentiary authority actually passed through production extraction and source admission.

Historical duplicate raw choices therefore remain resolved by normalized provenance rather than filename guessing.

---

## 3. Current forcing function

The current capability is:

> **Fresh chronological current-corpus admission acceptance.**

We now test the whole structural memory machine rather than another isolated seam:

```text
fresh current-corpus manifest
  → pristine isolated acceptance World
  → governed C1 genesis D0
  → fresh production extraction per recap
  → candidate-document integrity
  → exact Candidate Graph Admission
  → exact current-parent governed write
  → receipt/head verification
  → next recap
```

The acceptance contract is intentionally fail-closed:

```text
source drift            → STOP
generation failure      → STOP
candidate integrity     → STOP
nonconfirmable admission→ STOP
stale parent            → STOP
governed write failure  → STOP
receipt/head mismatch   → STOP
process interruption    → run invalid / no resume-as-PASS
```

Eligibility dispositions such as unsupported coherent concepts are not automatic failures by themselves. They remain exact candidate input; the run can continue only when Candidate Graph Admission truthfully seals a confirmable accepted union.

The runner is orchestration/evidence code, not graph semantics. If it needs logic such as:

```text
if duplicate: keep first
if unsupported type: delete node
if bad edge: remove it
if session fails: skip and continue
```

STOP.

---

## 4. ACTIVE slice ownership

Canonical handoff:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md
```

Only leased writes:

```text
CREATE evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
CREATE tests/test_current_corpus_admission_acceptance.py
CREATE Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md
```

Generated runtime evidence under:

```text
out/graph_memory/current_corpus_admission_acceptance_v1/**
```

is not committed by default.

Runtime target is fixed and isolated:

```text
World ID: dogfood-current-corpus-acceptance-v1
Database: dmb_current_corpus_acceptance_v1
Host: loopback only
Port: 54329
```

The runner must never reset/drop/delete the database. Non-pristine authority is an operator STOP.

CLI contract:

```text
--preflight   zero model calls / zero durable source or graph mutation
--execute     one full fresh run from a pristine authority
```

No session subsets, start-at, skip, resume, sanitize, repair, arbitrary model, or arbitrary world controls.

Model selection is current production authority:

```text
ProductionExtractionRequest.model_id = None
```

Record the resolved model and model-policy digest; do not hard-code or compare models.

---

## 5. Evidence and review gates

### Deterministic review before paid dogfood

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

Then exact-head operator preflight:

```bash
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --preflight
```

Only after deterministic review is clean should the paid run execute:

```bash
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --execute
```

The paid run has only two truthful outcomes:

```text
complete exact frozen manifest → STRUCTURAL ACCEPTANCE PASS
first owning-boundary failure   → STRUCTURAL ACCEPTANCE HOLD / STOP
```

A STOP is useful evidence and should normally lead to one focused repair handoff at the first failing production boundary.

---

## 6. Binding design laws

```text
source artifact = evidentiary authority
graph = durable materialized knowledge
candidate extraction = proposal, never canon
identity = World-global
published revisions = immutable
head movement = atomic
failed write = prior head remains authoritative
candidate integrity ≠ admission eligibility ≠ write failure
structural acceptance ≠ semantic quality
```

The current acceptance runner may compose existing production capabilities. It must not create a second source system, candidate schema, admission contract, identity policy, ontology, graph writer, model policy, or product batch-ingestion workflow.

---

## 7. Claims that remain false

Before this slice completes:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = HOLD
SEMANTIC MODEL SELECTION = HOLD
```

Even after a structural PASS, all of these remain false:

```text
no model winner exists
no semantic truthfulness/recall/precision score exists
no claim every accepted assertion is factually correct
no broad ontology-support decision exists
no unattended production batch-ingestion loop exists
no resume/retry scheduler exists
no live Eldyrwild rewrite has occurred
```

---

## 8. Current steward disposition

```text
recap World genesis                 MERGED / ACCEPTED
PR #720 Candidate Graph Admission   MERGED / ACCEPTED
PR #721 generation alignment        MERGED / ACCEPTED
PR #715                              CLOSED UNMERGED / historical only
frozen-42 structural result          HOLD / historical diagnostic
semantic model selection             HOLD
current corpus design census         C1 S1–17 + C2 S1–27 = 44 logical recaps
active implementation handoff        current-corpus-admission-acceptance-v1
implementation PR                    none yet at authority sync
named successor after PASS           semantic truthfulness / current-memory evaluation contract
successor after STOP                 one focused repair at first failing production boundary
```

The next implementation agent should execute the ACTIVE handoff exactly. It should not redesign campaign-memory sequencing from scratch.
