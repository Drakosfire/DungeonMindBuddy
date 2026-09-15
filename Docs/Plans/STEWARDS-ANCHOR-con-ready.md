# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-15  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main` `3a777c91df9ad690a45fb22603631b55583b3eb9`  
**Last product capability merge:** PR #720, merge `2e054ce928f4a7de14a4a7b745460c85a90f8ee1`  
**Current forcing function:** DESIGN the next bounded campaign-memory acceptance slice; no implementation lane is currently authorized  
**Product roadmap:** [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md)  
**Campaign graph architecture:** [`../Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Consumed admission handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md)  
**Steward process:** [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md)

> This file is the current pickup authority for sequencing. Repository truth supersedes older chat summaries and stale `CURRENT` banners in historical handoffs/roadmaps. The product roadmap remains authoritative for user stories and product intent; use this anchor for present sequencing until the roadmap header is separately synchronized.

---

## 0. Pickup rule

A fresh Designing agent must:

1. fetch current `main` and record the exact SHA;
2. inspect open PRs/branches for write-lease collisions;
3. read this anchor;
4. read the consumed candidate-admission handoff and the campaign-supergraph architecture;
5. inspect the frozen-42 acceptance report only as historical experiment evidence;
6. re-census current canonical campaign sources before using any historical session count;
7. design **one independently useful capability** and land its handoff on `main` before any implementation lane is allocated;
8. do not merge unless explicitly instructed.

At this re-anchor there were **no open PRs** in `Drakosfire/DungeonMindBuddy`.

---

## 1. Current campaign-memory truth

### 1.1 Governed World bootstrap exists

The campaign-memory path no longer starts from an ad hoc or copied graph.

Merged recap World genesis provides:

```text
canonical party registry
  → sealed genesis prepare
  → governed zero-parent DungeonMind write
  → D0 containing canonical PC identity anchors only
  → ordinary existing-World mutation for recap admission
```

Genesis is not permission to smuggle recap facts, party-membership assertions, or session claims into D0.

### 1.2 Candidate → Graph Admission is now a production boundary

PR #720 is merged.

```text
reviewed implementation head:
1d490928b556a8672b56d9f4b6c4fca35e3c4e54

Cycle 4 review:
APPROVE — review 5213358854

merge:
2e054ce928f4a7de14a4a7b745460c85a90f8ee1
```

The durable invariant is:

> The exact candidate is immutable input. Candidate admission may accept, reject, or leave meaning unresolved, but it may not rewrite candidate semantics to make graph publication succeed.

The merged seam now distinguishes:

```text
candidate-document integrity
  malformed/conflicting candidate → fail closed

admission eligibility
  coherent but unsupported/unresolved item → explicit disposition

governed confirmation
  exact sealed candidate/source/parent decision → existing DungeonMind write
```

`confirmable` is derived from the final sealed accepted-assertion union after structural qualification and identity resolution, including multi-contribution standing context.

Source admission remains the existing DungeonMind-backed source-authority path. The graph commit remains the existing governed DungeonMind World write. Do not invent a second persistence path.

### 1.3 PR #715 is retired

PR #715 is now:

```text
CLOSED UNMERGED
head 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
```

The accepted lifecycle decision was:

```text
ARCHIVE_MINIMUM_WITNESS_THEN_CLOSE_UNMERGED
```

Durable replacement authority:

```text
tests/fixtures/candidate_admission/pr715_failure_witnesses.json
tests/test_candidate_graph_admission_contract.py
```

The branch/history may remain as historical evidence. It is not active authority, not an implementation lane, and not a corpus that should be repaired to manufacture a passing experiment.

### 1.4 Frozen-42 experiment remains a HOLD

Do not rewrite experiment history after closing #715.

```text
OpenAI exact-frozen arm: PASS
DeepSeek exact-frozen arm: STOP at C2 S9
DeepSeek sanitized continuation: DIAGNOSTIC ONLY
STRUCTURAL ACCEPTANCE: HOLD
SEMANTIC MODEL SELECTION: HOLD
```

Why DeepSeek stopped matters:

- conflicting duplicate candidate IDs are candidate-document integrity failures;
- `sublocation` demonstrated a separate admission-eligibility question;
- first-wins/deletion sanitization changed candidate semantics and therefore could not count as acceptance evidence.

Those failure classes are now represented by production admission behavior and durable regressions.

---

## 2. What #720 proved — and did not prove

#720 proved the **seam**, not the long-horizon campaign outcome.

We can now say:

```text
exact candidate
  → deterministic integrity decision
  → explicit admission qualification
  → sealed candidate/source/world/parent binding
  → confirm or refuse
  → existing governed World revision
```

We still cannot say:

- a fresh current campaign corpus completes chronologically through this seam;
- a generated candidate corpus is structurally clean enough for long-horizon admission;
- one extraction model is semantically better than another;
- the current canonical corpus has the historical 42-session shape;
- unattended batch ingestion is product-ready;
- unsupported candidate concepts should automatically expand World ontology.

No model winner exists. There is still no pre-existing deterministic semantic benchmark that licenses a model-selection claim.

---

## 3. Current forcing function

The next Designing agent owns **design**, not implementation.

Default successor hypothesis:

> **Fresh chronological batch admission acceptance:** prove that the merged production genesis + candidate-admission + governed-write path can build durable campaign memory across the current canonical recap corpus without caller-side semantic repair.

This is a hypothesis, not an already-authorized PR.

The designer must decide whether that experiment is truly the next single capability or whether **candidate-generation contract hardening** is a prerequisite that deserves its own bounded slice first.

The decision should be evidence-driven:

```text
If current generation can reliably produce coherent candidate documents:
    design fresh chronological admission acceptance.

If current generation still produces candidate-integrity failures frequently enough
that the acceptance experiment would mostly measure malformed candidate output:
    design candidate-generation contract hardening first.
```

Do not combine both into one implementation PR merely to make an experiment pass.

---

## 4. Mandatory design questions for the successor

The fresh designer should answer these before writing an implementation handoff.

### Corpus authority

- What is the **current** canonical recap corpus on `main`?
- Re-census it. The old frozen 42 count is stale because later campaign recaps were promoted after that freeze.
- Which sources are observed recap authority versus prep, worldbuilding, duplicate, or ambiguous material?

### Candidate generation

- Is the experiment consuming newly generated candidates or another already-durable current candidate source?
- If models are called, what exact model/profile is being tested and what claim is the run allowed to make?
- What is the fail-closed behavior when a candidate is document-invalid?
- No sanitizer, first-wins duplicate handling, or semantic deletion is permitted after candidate generation.

### Structural acceptance

- What exact sequence constitutes PASS?
- Every session must start from the prior admitted head.
- Prepare must remain inert.
- Every confirm must bind exact candidate/source/parent authority.
- A stop must preserve failure evidence rather than silently continuing.
- A rerun after a real failure must restart from a pristine authorized point, not continue a repaired chain and call it final.

### Model comparison

- Structural acceptance is not semantic model selection.
- If more than one model is compared, arms must be isolated and comparable.
- Do not invent a semantic benchmark after seeing results.
- If no pre-existing benchmark exists, model-selection verdict remains HOLD even if structural runs complete.

### Evidence durability

- What evidence survives disposable database teardown?
- Exact production SHA, source census/manifest, model/profile where applicable, candidate digests, genesis receipt, per-session receipts, parent chain, terminal head, stop conditions, and zero-repair declaration should be durable outside ephemeral databases.

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

Never collapse those classes merely to keep a batch moving.

### Runner law

A batch/acceptance runner may orchestrate production seams. It must not know how to repair graph semantics.

If a runner needs code like:

```text
if duplicate: keep first
if unsupported type: delete node
if edge no longer works: delete edge
```

STOP. Production or generation contract ownership is wrong.

### Process law

```text
re-anchor
→ decompose candidate capabilities
→ design one slice
→ land steward-owned HANDOFF on main
→ activate only after gates are satisfied
→ allocate isolated implementation lane
→ dispatch
→ exact-head review cycles
→ merge only when instructed
→ steward state-authority sync
→ re-anchor
```

A BLOCKED handoff is durable design authority but does not reserve a lane or authorize code. Only ACTIVE dispatches implementation.

---

## 6. Likely next authorities to read

Required:

```text
AGENTS.md
Docs/Process/STEWARD-CYCLE.md
Docs/Design/ARCHITECTURE-campaign-supergraph.md
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md
```

Historical evidence:

```text
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-v1.md
PR #715 @ 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed — closed/unmerged
```

Product intent/user stories:

```text
Docs/Roadmaps/ROADMAP-con-ready.md
```

Use the roadmap for product goals and acceptance stories. Its older sequencing/status prose may lag this anchor.

---

## 7. Stop conditions for the next Designing agent

Stop and rebrief rather than quietly broadening scope if:

- the next experiment requires changing DungeonMind generic contracts;
- candidate generation and batch acceptance both require material implementation changes;
- the only way to complete a corpus is semantic repair after generation;
- source authority cannot be bound exactly;
- corpus membership is ambiguous and cannot be resolved by existing source rules;
- a semantic model winner is requested without a pre-existing evaluation contract;
- the design would reuse #715 as active production authority;
- the successor needs a second independently useful capability to succeed;
- an apparently simple acceptance runner begins accumulating ontology, identity, or mapping policy.

---

## 8. Current steward disposition

```text
PR #720                      MERGED / ACCEPTED
candidate admission handoff  CONSUMED
PR #715                      CLOSED UNMERGED
frozen-42 structural result  HOLD
semantic model selection     HOLD
open implementation PRs      none at re-anchor
next implementation lane     NONE — design required first
```

The next steward action is to design and land one successor handoff. Do not dispatch code directly from this anchor.
