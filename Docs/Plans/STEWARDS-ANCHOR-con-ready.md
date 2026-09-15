# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-15  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main` `3db71402ec7beed1670b6ad837290324a0a79b78` — steward handoff landing  
**Last product capability merge:** PR #720, merge `2e054ce928f4a7de14a4a7b745460c85a90f8ee1`  
**Current forcing function:** IMPLEMENT candidate-generation integrity alignment from the checked-in ACTIVE handoff  
**Active implementation authority:** [`HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md)  
**Consumed admission handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md)  
**Campaign graph architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)

> This file is the current pickup authority for sequencing. Repository truth supersedes older chat summaries and stale `CURRENT` banners in historical handoffs/roadmaps. The product roadmap remains authoritative for user stories and product intent; use this anchor for present sequencing until its older status prose is separately synchronized.

---

## 0. Pickup rule

### Coding / implementation agent

Do not redesign the slice from chat history. Read, in order:

1. [`HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md) — **ACTIVE implementation authority**;
2. [`HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md) — consumed predecessor semantics;
3. only the exact owning code/tests named by handoff §4/§7.

The candidate implementation branch is:

```text
dogfood-continuity/candidate-generation-integrity-alignment-v1
```

The steward allocates that branch only from current `main` after this authority sync. The implementation agent must stay inside the handoff §4 lease and STOP on any required path outside it.

### Fresh designing/review agent

Re-anchor exact `main`, open PR state, the ACTIVE handoff, and the predecessor before making any sequencing claim. Do not dispatch the named successor until this slice is reviewed/merged and repository authority is synchronized again.

At handoff design re-anchor there were **no open PRs**.

---

## 1. Current campaign-memory truth

### 1.1 Governed World bootstrap exists

Merged recap World genesis provides:

```text
canonical party registry
  → sealed genesis prepare
  → governed zero-parent DungeonMind write
  → D0 containing canonical PC identity anchors only
  → ordinary existing-World mutation for recap admission
```

Genesis is not permission to smuggle recap facts, party-membership assertions, or session claims into D0.

### 1.2 Candidate Graph Admission is production authority

PR #720 is merged and accepted.

```text
reviewed implementation head:
1d490928b556a8672b56d9f4b6c4fca35e3c4e54

Cycle 4 review:
APPROVE — review 5213358854

merge:
2e054ce928f4a7de14a4a7b745460c85a90f8ee1
```

Durable invariant:

> The exact candidate is immutable input. Candidate admission may accept, reject, or leave meaning unresolved, but it may not rewrite candidate semantics to make graph publication succeed.

The merged seam distinguishes:

```text
candidate-document integrity
  malformed/conflicting candidate → fail closed

admission eligibility
  coherent but unsupported/unresolved item → explicit disposition

governed confirmation
  exact sealed candidate/source/world/parent decision → existing DungeonMind write
```

Source admission remains the existing DungeonMind-backed source-authority path. The graph commit remains the existing governed DungeonMind World write.

### 1.3 Candidate generation has one prerequisite classification mismatch

Current production extraction already validates the fully assembled typed candidate before making an extraction run reviewable. It therefore already fails true malformed documents such as duplicate IDs or broken references.

However, current production extraction treats **every** typed preview error as generation failure. #720 intentionally treats an otherwise coherent `invalid node_type` such as `sublocation` as **admission eligibility**, preserving the exact candidate for an explicit `unsupported_node_type` disposition.

So today the same conceptual condition can be classified differently at adjacent production boundaries:

```text
production generation:
  invalid node_type → FAILED / not reviewable

Candidate Graph Admission:
  coherent unsupported node_type → candidate preserved
  → explicit unsupported_node_type disposition
```

The ACTIVE handoff owns only this alignment. It does not add a new node type and does not weaken real document-integrity validation.

### 1.4 PR #715 is retired

```text
PR #715
CLOSED UNMERGED
head 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
```

Durable replacement authority:

```text
tests/fixtures/candidate_admission/pr715_failure_witnesses.json
tests/test_candidate_graph_admission_contract.py
```

#715 is historical evidence only. Do not merge, rebase, cherry-pick, rehabilitate, sanitize, or use it as active candidate authority.

### 1.5 Frozen-42 experiment remains a HOLD

```text
OpenAI exact-frozen arm: PASS
DeepSeek exact-frozen arm: STOP at C2 S9
DeepSeek sanitized continuation: DIAGNOSTIC ONLY
STRUCTURAL ACCEPTANCE: HOLD
SEMANTIC MODEL SELECTION: HOLD
```

The sanitized DeepSeek continuation is not acceptance evidence.

---

## 2. Re-census result and successor context

The design steward independently re-censused current `main` before selecting this prerequisite.

Current normalized observed-recap lineage covers:

```text
Campaign 1: Sessions 1–17
Campaign 2: Sessions 1–27
Total logical recap sessions: 44
```

Existing normalized provenance resolves the historical duplicate raw recap choices, including:

```text
C1 S2  → Session 2 - Finishing the Job.md
C2 S23 → Session 23 - Mireward Gate Battle.md
```

C2 S26 and S27 are now present and normalized as observed session recaps.

This is a **design-time census**, not a frozen acceptance manifest and not a structural PASS. The named successor must independently re-freeze the then-current corpus before model calls.

---

## 3. Current forcing function

The design decision is complete:

> **Candidate-generation integrity alignment is the one prerequisite slice before fresh chronological batch admission acceptance.**

Why it is separate:

- candidate generation already has a fail-closed full-document validation boundary;
- the missing capability is not generic validation or candidate repair;
- the specific defect is disagreement over **integrity versus admission eligibility**;
- fresh chronological acceptance must not report an eligibility condition as malformed generation before #720 can own it.

The ACTIVE implementation handoff is:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md
```

Its governing invariant is:

> A production-generated candidate becomes reviewable iff its fully assembled document is coherent under the same candidate-document integrity definition consumed by Candidate Graph Admission; admission-eligibility issues remain exact candidate input for #720 to disposition, while true integrity failures still fail closed before admission.

No broader generation hardening is authorized.

---

## 4. Implementation laws for the ACTIVE slice

The coding agent must preserve all of these:

```text
exact candidate semantics remain immutable
candidate integrity failure ≠ admission eligibility rejection
unsupported coherent concept is not silently made supported
no sanitizer / first-wins / semantic deletion
no model/prompt/schema tuning
no identity-policy changes
no source/genesis/governed-write changes
no batch runner
```

Required cross-boundary proof:

```text
coherent unique sublocation candidate
  → production extraction REVIEWABLE unchanged
  → Candidate Graph Admission
  → explicit unsupported_node_type disposition
```

Required adversarial proof:

```text
duplicate/conflicting candidate ID
  + optional eligibility issue
  → generation integrity failure
  → no reviewable sanitized subset
```

If the implementation requires a path outside handoff §4, STOP and return to the steward.

---

## 5. Design laws that remain binding

### World authority

```text
source artifact = evidentiary authority
graph = durable materialized knowledge
candidate extraction = proposal, never canon
campaign = scope, not copied graph
identity = World-global
published revisions = immutable
head movement = atomic
failed write = prior head remains readable
```

### Admission law

```text
candidate integrity failure
≠
admission eligibility rejection
≠
governed write failure
```

### Runner law for the named successor

The future chronological acceptance runner may orchestrate production seams. It must not know how to repair graph semantics.

If it needs code like:

```text
if duplicate: keep first
if unsupported type: delete node
if edge no longer works: delete edge
```

STOP.

### Process law

```text
ACTIVE handoff on main
→ allocate isolated implementation lane
→ dispatch
→ exact-head review cycles
→ merge only when instructed
→ steward state-authority sync
→ re-anchor
→ only then design/dispatch named successor
```

---

## 6. Authorities to read

### Current implementation

```text
AGENTS.md
Docs/Process/STEWARD-CYCLE.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md
src/graph_memory/candidate_graph_preview.py
src/graph_memory/extraction/graph_preview_runner.py
apps/live_control_server/services/candidate_graph_admission.py
tests/test_graph_preview_runner.py
tests/test_candidate_graph_admission_contract.py
```

### Architecture / product intent

```text
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Roadmaps/ROADMAP-con-ready.md
```

### Historical evidence only

```text
tests/fixtures/candidate_admission/pr715_failure_witnesses.json
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md
PR #715 @ 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed — CLOSED UNMERGED
```

Do not require the coding agent to reconstruct the frozen experiment beyond the durable witness needed by the ACTIVE handoff.

---

## 7. Stop conditions

Stop and rebrief rather than broadening scope if:

- shared classification requires changing the candidate schema/version;
- the fix requires adding `sublocation` or any other ontology concept;
- model prompts, model policy, extraction passes, or retry behavior must change;
- candidate assembly must delete/merge/rewrite semantic objects to satisfy integrity;
- #720's accepted integrity/eligibility semantics must materially change;
- source authority, recap genesis, DungeonMind contracts, or governed writes need modification;
- any required path falls outside the ACTIVE handoff §4 lease;
- another independently useful capability appears.

---

## 8. Current steward disposition

```text
PR #720                         MERGED / ACCEPTED
candidate admission handoff     CONSUMED
PR #715                         CLOSED UNMERGED
frozen-42 structural result     HOLD
semantic model selection        HOLD
current corpus design census    C1 S1–17 + C2 S1–27 = 44 logical recaps
active implementation handoff   candidate-generation-integrity-alignment-v1
implementation PR               none yet
named successor                 fresh chronological current-corpus admission acceptance
```

The next implementation agent should execute the ACTIVE handoff, not redesign campaign-memory sequencing from scratch.