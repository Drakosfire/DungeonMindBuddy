---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / frozen full-corpus acceptance and notebook retirement
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW → DOGFOOD
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md`
  - Branch / PR: `dogfood-continuity/frozen-42-session-acceptance-replay-v1` — create only from exact post-genesis `main`; **DO NOT MERGE**

  ## Verification pointer
  - Predecessor: governed recap World genesis PR; currently #718 at `187332e22aa67e7baa0e81ccf49359a49caa0eb3`, not yet merged
  - Frozen notebook: PR #715 at `820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed`
  - Frozen candidates: `d6e2599bbabb9719bc92601f7bc1ad8b69411e98` via #715 `ACCEPTANCE_MANIFEST.json`
  - This PR must not merge, rebase, or cherry-pick #715 into production.

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DOGFOOD-CONTINUITY: frozen 42-session two-arm acceptance replay

**Created:** 2026-09-14
**Status:** BLOCKED — activate only after the governed recap World genesis predecessor receives exact-head APPROVE and merges to `main`.
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md`
**Conversation / workstream:** `DOGFOOD-CONTINUITY / frozen full-corpus acceptance and notebook retirement`
**Flow / owner:** `DOGFOOD-CONTINUITY`
**Direction:** DESIGN → CODE → REVIEW → DOGFOOD
**Authority base:** `BLOCKED — replace with main@<POST_GENESIS_MERGE_SHA> before dispatch`
**Predecessor:** governed recap World genesis PR; currently #718 at `187332e22aa67e7baa0e81ccf49359a49caa0eb3`, not yet merged at handoff creation.
**Frozen notebook authority:** PR #715 at reviewed hardening head `820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed`
**Frozen candidate authority:** candidate bytes frozen from `d6e2599bbabb9719bc92601f7bc1ad8b69411e98` by #715 `ACCEPTANCE_MANIFEST.json`
**Implementation branch after activation:** `dogfood-continuity/frozen-42-session-acceptance-replay-v1`, created from exact post-genesis `main`
**Implementation PR disposition:** **DO NOT MERGE.** This is a reviewable execution/evidence branch. A bounded final report may be promoted separately after acceptance.
**PR title:** `DOGFOOD-CONTINUITY: execute frozen 42-session acceptance replay`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

> This handoff is intentionally blocked. Do not create the implementation branch from pre-genesis `main`.
>
> After the predecessor merges, activation consists only of:
>
> 1. recording the exact reviewed predecessor head and merge SHA;
> 2. recording exact post-merge `main@SHA`;
> 3. changing this handoff from `BLOCKED` to `ACTIVE`;
> 4. branching from that exact `main`.
>
> If activation requires changing the mission, invariant, files, evidence, or execution semantics below, stop for design re-review rather than silently editing this handoff.

**Recorded at handoff creation (2026-09-14), not an activation record:**

```text
origin/main = 3c813c4192db8e72f63c50a0c5e424eddf00d2e9
  (docs: dispatch governed recap World genesis)
#718 = OPEN @ 187332e22aa67e7baa0e81ccf49359a49caa0eb3
  reviewDecision empty; not merged
#715 = OPEN @ 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
  worktree clean
```

---

## §1 Mission and merge-ready invariant

**Mission:** A reviewed operator can replay both frozen 42-session candidate arms through the current production genesis and governed existing-World write path so that we obtain trustworthy, comparable, zero-model evidence about long-horizon World Graph continuity.

**Merge-ready invariant:** From one exact post-genesis production revision, each frozen model arm independently starts from the same canonical Campaign 1 party-registry semantics in its own pristine rehearsal authority, creates its own six-PC zero-parent `D_0`, publishes the exact 42 frozen candidate sessions as one uninterrupted ordinary child-revision chain, preserves exact source provenance and arm isolation, performs zero model calls, and produces evidence bound to the exact production SHA, notebook SHA, frozen manifest, genesis receipts, and terminal heads; any mismatch, partial failure, unexpected head, source drift, or authority ambiguity fails closed without being represented as a successful acceptance run.

### Locked causal order

For each arm:

```text
post-genesis current main
+
canonical current-main C1 party_registry bytes
+
read-only #715 frozen candidate authority
        ↓
pristine arm-specific rehearsal authority
        ↓
prepare recap World genesis
        ↓ inert plan
confirm recap World genesis
        ↓
D_0
  parent = null
  six canonical PC identity anchors only
        ↓
native mutation-context read of exact D_0
        ↓
C1 S1 frozen candidate
  ordinary existing-parent governed write
        ↓
D_1.parent_revision_id == D_0
        ↓
C1 S2 ... C1 S17
        ↓
C2 S1 ... C2 S25
        ↓
D_42
        ↓
terminal native read + bounded comparison evidence
```

There is no special first-recap path.

There is no copied head, revision, identity ledger, source state, or graph body between arms.

### Activation gate

Do not dispatch until all are true:

* predecessor genesis PR has received formal exact-head **APPROVE**;
* that exact reviewed predecessor has merged;
* current `main` contains the predecessor;
* exact post-merge `main@SHA` is recorded in this handoff;
* PR #715 still exists at exact reviewed hardening head `820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed`, or any later notebook head has itself received review establishing unchanged candidate/manifest authority;
* no frozen candidate or `ACCEPTANCE_MANIFEST.json` byte has changed.

### Pre-dispatch critique

| Question                                     | Answer                                                                                                                                                                                                                                                              |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Can one invariant govern every claimed path? | Yes. Every path either proves or protects one independently initialized, frozen-input, chronological governed replay.                                                                                                                                               |
| Most likely adversarial sequence             | Correct frozen candidates → operator swaps arm/database or uses stale/mutated notebook → runner publishes anyway → comparison appears valid while authorities or inputs differ.                                                                                     |
| Does §7 detect it?                           | Yes. Read-only notebook-head/cleanliness checks, manifest/live-byte comparison, exact arm→DB→World binding, pristine-authority proof, and per-revision parent checks all occur before or at their owning boundary.                                                  |
| Easiest boundary to under-test               | The transition from acceptance-local frozen candidate evidence into current production source admission and ordinary governed mutation.                                                                                                                             |
| What forces STOP/split?                      | Re-anchoring requires any production semantic/API change; current canonical source bytes no longer match the frozen source digest; an existing benchmark requires new semantic rules; or final replay needs candidate regeneration/model calls/manual graph repair. |

---

## §2 Context, authority, and boundaries

### Authority hierarchy

1. **Post-genesis `main`** owns all production runtime semantics.
2. **Governed recap World genesis predecessor** owns creation of a truthful `D_0`.
3. **Merged PC identity normalization** owns `pc ≡ player_character` compatibility.
4. **PR #715 at `820fe3aa…`** owns the reviewed notebook acceptance harness and immutable experimental record.
5. **`ACCEPTANCE_MANIFEST.json` inside #715** owns the frozen candidate/source digest set from candidate head `d6e2599…`.
6. The canonical corpus under the post-genesis production checkout remains source authority. Frozen candidates do not replace source authority.

The architectural rule remains:

```text
source artifacts = evidentiary authority
candidate extraction = proposal
governed accepted contribution = durable knowledge
immutable revision + atomic head = published World state
```

### Important distinction: two Git authorities

Use two separate checkouts.

**Production execution checkout**

```text
<acceptance-worktree>/
  HEAD = exact post-genesis main base + acceptance-only runner/tests
```

This checkout owns:

* production imports;
* canonical current corpus source bytes;
* acceptance-local `out/registries`;
* acceptance result artifacts.

No live DungeonBuddy process may point at this worktree.

**Frozen notebook checkout**

```text
<notebook-worktree>/
  HEAD = 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
  working tree = clean
```

This checkout is **read-only**.

It supplies:

* `ACCEPTANCE_MANIFEST.json`;
* frozen OpenAI candidate graphs;
* frozen DeepSeek candidate graphs;
* historical extraction telemetry/evidence needed to interpret them.

Do not merge, rebase, or cherry-pick #715 into the production execution branch.

### Source-byte rule

For every one of the 42 sessions:

```text
manifest source SHA
    ==
frozen-notebook source SHA
    ==
current-main canonical source SHA
```

Candidate bytes come from the read-only notebook checkout.

Source admission uses the canonical source path/bytes from the post-genesis production checkout.

If current `main` has legitimately changed any one of the 42 recap source files since the experiment was frozen, **STOP**. Do not silently admit the old notebook copy as current source authority and do not update the acceptance manifest.

### Frozen experiment scope

Exactly:

```text
Campaign 1: Sessions 1–17
Campaign 2: Sessions 1–25
Total: 42 recaps per arm
```

C2 Sessions 26 and 27 are not part of this experiment.

The experiment's accurate claim remains:

> two autoregressive, chronologically generated candidate arms, followed by zero-model governed replay into independently initialized Worlds.

It is not evidence that Session N candidate extraction consumed only the committed World through N−1.

### Rehearsal runtime ownership

Arm configuration is fixed:

| Arm                   | Database                   | World ID                       |
| --------------------- | -------------------------- | ------------------------------ |
| `openai-gpt-5.4-mini` | `dmb_full_corpus_openai`   | `dogfood-frozen42-openai-v1`   |
| `deepseek-v4.1-flash` | `dmb_full_corpus_deepseek` | `dogfood-frozen42-deepseek-v1` |

Database constraints:

* PostgreSQL only;
* loopback only: `127.0.0.1`, `localhost`, or `::1`;
* exact port `54329`;
* live ports `54330` and `54331` forbidden;
* exact arm-specific database name required.

The new runner should derive the World ID from the arm configuration rather than accepting an arbitrary operator-supplied World ID.

Before execution, prove the existing two rehearsal DBs are still pristine and schema-compatible with post-genesis production. If either fact cannot be proven cheaply and exactly, recreate exactly those two databases from the current isolated schema before genesis.

No runner may automate database deletion.

### Genesis semantics

Both arms use:

```text
campaign_id = longmont-c1
baseline_roster_key = "1"
requested_by = full-corpus-acceptance-genesis
confirming_principal = full-corpus-acceptance-genesis
```

Expected PC identities:

```text
Baergrom
Bonogo
Caelynn
Ephanna
Karsemine
Stafl
```

Semantic equivalence across the two genesis runs means:

* same canonical registry source revision/digest;
* same roster key;
* same six PC identity keys;
* same six deterministic PC object IDs;
* same accepted baseline meaning;
* `parent_revision_id = null` for both `D_0`s.

Do **not** require world-bound identifiers such as plan IDs, initialization IDs, command hashes, or revision IDs to be byte-identical between the two Worlds.

### Named successor

After successful evidence review:

1. promote one bounded acceptance report to `main`;
2. extract at most one independently justified production behavior into a small focused PR if the evidence demands it;
3. close #715 unmerged;
4. separately retire remaining notebook PRs according to their own authority/equivalence checks.

None of those actions belongs in this implementation slice.

### Parallel lanes / collision at handoff creation

| Lane | Head | Write-lease collision with this slice |
| --- | --- | --- |
| #718 genesis | `187332e…` | Predecessor. Must merge before activation. Do not edit its §4 production paths. |
| #715 notebook | `820fe3aa…` | Read-only frozen authority. Do not commit onto it. |
| #713 Stage 4J | `c9d9a64b…` | Independent notebook. Do not write this handoff there. |
| #714 Stage 4L | `a8757189…` | Independent notebook. |

Runtime collision: this slice later owns rehearsal databases `dmb_full_corpus_openai` and `dmb_full_corpus_deepseek` on loopback `54329`. #718 must not use those databases. Live ports `54330`/`54331` remain forbidden.

---

## §3 Observable paths and adversarial sequences

### Observable-path inventory

| Path                                                     | Required behavior                                                                                  | Owning boundary                 |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------- |
| Activation against wrong/pre-merge `main`                | Refuse dispatch                                                                                    | steward / exact SHA             |
| Notebook checkout wrong head                             | Fail before DB access                                                                              | acceptance runner               |
| Notebook checkout dirty                                  | Fail before DB access                                                                              | acceptance runner               |
| Frozen manifest missing or changed                       | Fail before DB access                                                                              | acceptance runner               |
| Candidate hash drift                                     | Fail before DB access                                                                              | acceptance runner               |
| Current canonical source differs from frozen source hash | Fail before DB access                                                                              | acceptance runner               |
| C2 S26/S27 appears in job set                            | Fail contract tests                                                                                | acceptance runner               |
| Wrong host/port/database                                 | Fail before seal or DB mutation                                                                    | acceptance runner               |
| Correct DB but wrong arm                                 | Fail before seal or DB mutation                                                                    | acceptance runner               |
| Correct DB but wrong World ID                            | Not operator-selectable; derive from arm                                                           | acceptance runner               |
| Non-pristine rehearsal authority                         | Fail before genesis                                                                                | preflight                       |
| Genesis prepare                                          | No durable mutation                                                                                | production genesis              |
| Genesis confirm                                          | One atomic `D_0`, six PCs, parent null                                                             | production genesis + PostgreSQL |
| Cross-arm genesis                                        | Independently executed; no copied state                                                            | operator + runner               |
| Native read after genesis                                | Exact head = receipt `D_0`, six PCs visible                                                        | production mutation context     |
| C1 S1                                                    | Ordinary existing-parent publish; `D_1.parent = D_0`                                               | governed write                  |
| Sessions 2–42                                            | Every child parent equals prior receipt child                                                      | runner + provider receipts      |
| Source admission                                         | Exact campaign/session/revision/openable source                                                    | source admission                |
| Interrupted replay                                       | Final run invalid; do not resume and call it acceptance                                            | runner/operator                 |
| Head changes unexpectedly mid-run                        | Fail closed at expected-parent check                                                               | governed write / runner         |
| Model/extraction path requested                          | Fail/STOP; never regenerate                                                                        | runner                          |
| Terminal read                                            | Current head exactly final receipt child                                                           | native read                     |
| Comparison                                               | Compare structural evidence only from two complete clean runs                                      | report                          |
| Semantic benchmark                                       | Use existing repository-owned deterministic benchmark unchanged, or STOP before model-winner claim | bounded discovery / report      |
| Teardown                                                 | Explicit operator action after evidence review                                                     | operator                        |

### Adversarial sequences

| Sequence                                                                   | Safe outcome                                                                                               |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Correct arm → swapped DB                                                   | Reject before `verify_seal()` and before DB access                                                         |
| Correct manifest → candidate edited                                        | Hash mismatch; zero mutation                                                                               |
| Correct candidate → current source edited                                  | Source hash mismatch; zero mutation                                                                        |
| Notebook at `820fe3…` → untracked candidate edit                           | Dirty/hash checks reject                                                                                   |
| OpenAI completes genesis → DeepSeek attempts to consume OpenAI head/ledger | Impossible: separate DB/World; no copy path                                                                |
| `D_0` exists → C1 S1 preparation sees different head                       | Reject chronology                                                                                          |
| Session N commits → Session N+1 receives N−1 parent                        | Reject chronology                                                                                          |
| Session N fails after earlier sessions committed                           | Preserve failure evidence; final arm run is invalid                                                        |
| Partial arm exists → operator retries remaining sessions                   | Not a valid final acceptance run; reset that arm to pristine and restart from genesis                      |
| One arm succeeds → second arm fails                                        | No comparative GO/model-winner claim                                                                       |
| Existing semantic benchmark cannot be identified                           | Structural acceptance may be recorded; model-selection/final GO remains HOLD and requires successor design |

### Final-run restart rule

For acceptance evidence, **partial resume is prohibited**.

A failed arm may retain its failed DB temporarily for diagnosis, but any later attempt intended to count as the final acceptance run must begin again from a pristine arm-specific authority and a newly created governed `D_0`.

This does not change production retry/idempotency semantics. It is an experimental cleanliness rule.

---

## §4 Files in scope — write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md` | Authoritative execution contract |
| Create | `tools/run_frozen_42_session_acceptance.py` | Re-anchored acceptance-only runner consuming current production + read-only notebook |
| Create | `tests/test_frozen_42_session_acceptance.py` | Owning runner/preflight/adversarial tests |
| Create | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-v1.md` | Bounded final human-readable evidence report, created only after execution |
| Create | `out/frozen_42_session_acceptance/ACCEPTANCE_RESULT.json` | Bounded machine-readable experiment evidence; acceptance branch only, force-add if gitignored |

### Activation-only modification

Only the handoff itself may be modified during activation to record:

* exact reviewed genesis predecessor head;
* predecessor merge SHA;
* exact post-merge `main` base SHA;
* `BLOCKED → ACTIVE`.

No semantic edits are authorized by activation.

### Read-only production seams

The implementation may consume but must not modify:

```text
apps/live_control_server/models/recap_world_genesis.py
apps/live_control_server/services/recap_world_genesis.py
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py
apps/live_control_server/integrations/dungeonmind/assertion_qualification.py
apps/live_control_server/models/world_graph_mutation_context.py
apps/live_control_server/services/source_artifact_registry.py
src/graph_memory/extract_promote_ops.py
```

Acceptance-local historical SourceArtifact-ID rebinding may use the existing source-registry seam exactly as the reviewed #715 harness does. If that seam no longer exists or cannot be used without changing production code, **STOP/rebrief**.

### Read-only notebook authority

The entire exact `#715@820fe3aa…` checkout is read-only.

In particular:

```text
out/full_corpus_world_graph_ingestion/ACCEPTANCE_MANIFEST.json
out/full_corpus_world_graph_ingestion/openai-gpt-5.4-mini/**
out/full_corpus_world_graph_ingestion/deepseek-v4.1-flash/**
```

No notebook byte may be rewritten by the new runner.

### Bounded discovery exception — semantic benchmark

```text
Directory: not a write directory
Maximum additional read-only paths: 3
Allowed kinds:
- existing continuity/query benchmark
- existing deterministic evaluation fixture
- existing report describing that benchmark's contract

Decision rule:
Include only a repository-owned benchmark that predates this acceptance execution
and can be applied identically to both terminal Worlds without new model calls
or semantic contract changes.
```

If no such benchmark is found within this bound, stop before claiming a semantic model winner or final model-arm GO.

### Hard write-lease rule

If implementation needs to modify any `apps/**` or `src/**` production path, **STOP**.

That means the predecessor/current production contract is insufficient or the acceptance runner has discovered a real product defect. That is a new slice, not permission to patch production inside the experiment.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
| --- | --- |
| `dogfood-continuity/full-corpus-world-graph-ingestion-v1` / PR #715 | Do not merge, rebase, cherry-pick, or rehabilitate the notebook into production. |
| `out/full_corpus_world_graph_ingestion/ACCEPTANCE_MANIFEST.json` | Immutable frozen digest authority. A changed candidate is a different experiment. |
| `out/full_corpus_world_graph_ingestion/openai-gpt-5.4-mini/**` | Frozen OpenAI candidates; notebook read-only. |
| `out/full_corpus_world_graph_ingestion/deepseek-v4.1-flash/**` | Frozen DeepSeek candidates; read-only notebook. |
| C2 Sessions 26 and 27 extraction | Outside the frozen 42-session corpus. |
| `src/graph_memory/extraction/**` | No candidate regeneration, prompt changes, `extra_known_entities` productization, DeepSeek productization, or `node_pass_workers` productization. |
| `apps/**` production runtime | STOP rather than patch production inside the experiment. |
| `src/**` production runtime | STOP rather than patch production inside the experiment. |
| worldbuilding / prep / secret / rumor ingest | Different source class. |
| UI / Agent / Hermes | Separate product lanes. |
| ontology / identity cleanup / new predicates | Separate product slices. |
| DungeonMind dependency or schema | Separate provider slice. |
| production `create_recap_source_artifact()` identity override | Rejected product contract; historical IDs stay runner-private. |
| SQL-created graph heads / copied `D_0` | Forbidden false genesis. |
| automatic `DROP DATABASE` | Operator-only teardown of the two named rehearsal databases. |
| closing #715 or older notebook PRs | Separate retirement decision after evidence review. |
| promoting the final report to `main` | Named successor, not this slice. |

Also excluded in force:

* regenerating any candidate;
* any OpenAI/OpenRouter/other model call;
* first-recap special behavior;
* copying heads, revisions, or identity state between arms;
* manual candidate repair after seeing failures;
* inventing a semantic benchmark after inspecting terminal results.

---

## §6 Implementation contract

### A. Re-anchor contract

Input:

```text
production_base_sha = exact post-genesis main SHA
notebook_root = separate clean checkout
notebook_head = 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
manifest.reviewed_notebook_head =
  d6e2599bbabb9719bc92601f7bc1ad8b69411e98
```

The new runner must:

1. prove its own production base/head provenance;
2. resolve an explicit `--notebook-root`;
3. prove notebook HEAD;
4. prove notebook working tree clean;
5. load the immutable acceptance manifest;
6. verify 42 candidate rows for each exact arm;
7. hash candidate bytes from the notebook checkout;
8. hash frozen source bytes from the notebook checkout;
9. hash canonical source bytes from the current production checkout;
10. require all manifest/source comparisons to match;
11. perform all of the above before any database mutation.

Do not copy candidate trees into the execution branch.

### B. Zero-model contract

The acceptance runner must not import or construct extraction/model clients.

Missing, malformed, or mismatched candidate material is an error, never a regeneration trigger.

The final execution command must run with known model-provider credentials removed from the process environment where practical:

```text
OPENAI_API_KEY
OPENROUTER_API_KEY
DUNGEONBUDDY_OPENROUTER
```

The final result records:

```text
model_calls = 0
candidate_generation = frozen
candidate_regeneration = false
```

If replay unexpectedly requires a model credential, **STOP**.

### C. Arm authority contract

Runner-owned configuration:

```text
openai-gpt-5.4-mini:
  database = dmb_full_corpus_openai
  world_id = dogfood-frozen42-openai-v1

deepseek-v4.1-flash:
  database = dmb_full_corpus_deepseek
  world_id = dogfood-frozen42-deepseek-v1
```

The operator supplies an arm and DSN.

The runner derives the expected World ID.

The runner verifies host, port, database, and arm binding before seal verification or mutation.

### D. Pristine-authority preflight

Immediately before a final run, capture and assert the relevant durable state is empty.

At minimum prove absence of:

* World head for the configured World ID;
* World revisions for it;
* initialization receipt;
* reviewed graph contributions for it;
* provider-side source artifact/revision state owned by that World initialization.

If the existing rehearsal DB's schema equivalence to current production cannot be established, recreate exactly that rehearsal database before this preflight.

No graph state is copied into either database.

### E. Genesis

For each arm, independently:

```text
prepare_recap_world_genesis(...)
```

Prove prepare is inert.

Then:

```text
confirm_recap_world_genesis(...)
```

Capture the complete genesis receipt.

Require:

```text
source_domain_key == party_registry
parent_revision_id == null
accepted PC set == exact six canonical PCs
native head == published_revision_id
native context contains exact six PCs
```

Compare arm baselines semantically after both genesis operations.

Do not require world-bound hashes/IDs to match.

### F. Frozen replay

Before each session publication:

1. re-hash the exact candidate;
2. re-hash current canonical source;
3. compare both to frozen manifest;
4. load current native mutation context;
5. require exact expected parent;
6. admit/re-prove exact source;
7. prepare through the ordinary governed extract/promote path;
8. bind identity using current production behavior;
9. apply current production assertion qualification;
10. explicitly confirm selectable assertions;
11. capture committed child revision and source/contribution evidence.

Chronology is fixed:

```text
C1 S1 … S17 → C2 S1 … S25
```

After C1 S1:

```text
C1S1.parent_revision_id == D_0
```

For every subsequent session:

```text
child[N].parent_revision_id == child[N-1].revision_id
```

After Session 42:

```text
native head == final receipt child
```

### G. Acceptance-local source identity

The frozen candidate evidence uses historical `full-corpus:...` SourceArtifact IDs.

Production `create_recap_source_artifact()` remains canonical and digest-derived.

The acceptance harness may rebind the verified historical ID only after:

```text
candidate hash == frozen manifest
current source hash == frozen manifest
canonical artifact content hash == frozen manifest
```

This remains notebook/acceptance machinery.

It is not a product contract and must not escape the runner.

### H. Terminal structural comparison

For each complete arm capture at minimum:

* genesis source digest and six baseline PC IDs;
* D0 revision;
* 42 child revisions;
* terminal head;
* total objects;
* object counts by kind;
* accepted assertion/edge counts;
* rejected assertion/edge counts and reasons;
* predicate distribution;
* source artifacts/revisions admitted;
* contribution count;
* unresolved/ambiguous identity outcomes;
* duplicate/collision indicators available from current production receipts;
* evidence/provenance completeness;
* terminal native-read success;
* per-session candidate node/edge counts;
* per-session accepted/rejected counts;
* wall time;
* `model_calls = 0`.

Comparison must distinguish:

```text
candidate-generation differences
vs
governed-publication differences
vs
terminal durable-graph differences
```

Do not treat “more nodes/edges” as synonymous with “better”.

### I. Existing semantic/query benchmark

During Gate A, use bounded discovery to locate any already-owned deterministic continuity/query benchmark applicable to these Worlds.

If found:

* freeze its identity/contract before execution;
* run it identically against both completed arms;
* include exact results and provenance.

If not found:

* do not invent one in this slice;
* report **STRUCTURAL ACCEPTANCE COMPLETE / SEMANTIC MODEL SELECTION HOLD** if all structural criteria pass;
* stop before claiming an arm winner, graph-quality GO, or UI GO;
* request a dedicated evaluation-design successor.

### J. Result artifact

`ACCEPTANCE_RESULT.json` is experiment evidence, not a product schema.

It must bind:

```text
production_base_sha
execution_head_sha
genesis_predecessor_merge_sha
notebook_head_sha
candidate_frozen_head_sha
acceptance_manifest_sha256

per arm:
  arm
  database name (no credentials)
  world_id
  genesis receipt summary
  D0
  exact ordered 42-session chain
  terminal revision
  structural metrics
  benchmark result if one existed
  model_calls

overall:
  structural verdict
  semantic verdict
  stop conditions
  teardown status
```

Never write credentials or complete DSNs into tracked evidence.

---

## §7 Evidence required

### Gate A — code/preflight review, zero mutation

Gate A must complete and receive formal review **before either rehearsal World is initialized**.

Required tests include:

| Guarantee                                                  | Owning proof            |
| ---------------------------------------------------------- | ----------------------- |
| Exact notebook head accepted                               | runner test             |
| Wrong notebook head rejected                               | adversarial runner test |
| Dirty notebook rejected                                    | adversarial runner test |
| Frozen manifest accepted                                   | runner test             |
| Manifest/candidate drift rejected                          | runner test             |
| Frozen source/current-main source mismatch rejected        | runner test             |
| Exactly 42 sessions/arm                                    | contract test           |
| S26/S27 excluded                                           | contract test           |
| Correct arm→DB accepted                                    | runner test             |
| Both swapped arm→DB pairings rejected before DB access     | adversarial test        |
| Wrong host/port/name rejected                              | runner test             |
| World ID derived from arm                                  | contract test           |
| Missing candidate never invokes extraction                 | adversarial test        |
| No extraction/model client owned by runner                 | static/import test      |
| Historical SourceArtifact rebinding remains runner-private | contract test           |
| Production runtime diff is empty                           | changed-path proof      |

Required commands after activation:

```bash
uv run pytest -q \
  tests/test_frozen_42_session_acceptance.py \
  tests/test_recap_world_genesis.py \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_native_genesis_continuity.py \
  tests/test_pc_identity_normalization.py \
  tests/test_cutover_native_governed_write.py \
  tests/test_world_graph_source_admission.py

uv run ruff check \
  tools/run_frozen_42_session_acceptance.py \
  tests/test_frozen_42_session_acceptance.py

git diff --check
git diff --name-only <POST_GENESIS_BASE_SHA>...HEAD
git diff --stat <POST_GENESIS_BASE_SHA>...HEAD
```

Also capture:

```bash
git -C <notebook-root> rev-parse HEAD
git -C <notebook-root> status --porcelain
```

Expected:

```text
HEAD = 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
status = empty
```

**Gate A verdict must be APPROVE before Gate B.**

### Gate B — real isolated PostgreSQL dogfood

Before genesis, independently capture:

```text
OpenAI authority: pristine
DeepSeek authority: pristine
production base SHA: exact
execution head SHA: exact
notebook head: exact
manifest SHA: exact
model credentials removed: yes
```

For each arm capture:

#### Genesis evidence

* prepare produced no durable rows;
* exact canonical registry digest;
* roster key `"1"`;
* six PC identity keys/object IDs;
* `D_0.parent_revision_id = null`;
* complete genesis receipt;
* native mutation-context head exactly `D_0`;
* native context exposes six PCs.

#### C1 S1 witness

* candidate hash;
* source hash;
* source admission;
* governed contribution;
* committed `D_1`;
* `D_1.parent_revision_id == D_0`.

This is the critical proof that #715 no longer depends on a special bootstrap route.

#### Full chronology evidence

For all 42 sessions:

```text
receipt[N].parent == prior committed revision
receipt[N].child exists
provider head after receipt[N] == receipt[N].child
```

No gap, fork, rewind, copied head, or hidden alternate parent.

#### Terminal evidence

* exactly one terminal head for configured World;
* native read returns terminal head;
* structural metrics recorded;
* provenance/evidence health recorded;
* zero model calls;
* optional pre-existing deterministic benchmark run identically against both arms.

### Failure injection / interruption witness

Before the final clean run, the runner tests must demonstrate that:

* wrong parent refuses publication;
* wrong frozen digest refuses publication;
* wrong arm authority refuses publication.

Do not deliberately corrupt the real 42-session final authority merely to prove failure behavior if the production owning tests already prove it.

### Final report

`REPORT-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-v1.md` must distinguish:

1. **pipeline/structural verdict**;
2. **OpenAI terminal result**;
3. **DeepSeek terminal result**;
4. **direct comparison**;
5. **semantic/query benchmark result or explicit absence**;
6. **what this experiment does not prove**;
7. **production behavior worth extracting, if any**;
8. **#715 retirement recommendation**.

No result may be promoted from candidate counts alone.

### Independent evidence review

Before teardown, reviewer must inspect:

* exact execution head;
* exact production base;
* exact notebook/manifest identity;
* both genesis receipts;
* C1 S1 parent witnesses;
* both full chains;
* terminal heads;
* comparison metrics;
* semantic benchmark provenance if present;
* zero-model evidence.

Only after that evidence is accepted should teardown occur.

### Teardown

Explicit operator action only.

Drop exactly:

```text
dmb_full_corpus_openai
dmb_full_corpus_deepseek
```

on the isolated loopback rehearsal server.

Do not drop:

* the PostgreSQL server;
* volumes;
* live World authority;
* APP-STATE authority;
* any other database.

Record teardown in the result/report.

---

## §8 Required handback

Return all of the following.

### Activation provenance

```text
reviewed genesis predecessor head:
genesis predecessor merge SHA:
post-genesis main/base SHA:
execution branch:
execution head:
```

### Frozen input provenance

```text
#715 notebook head:
820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed

manifest candidate head:
d6e2599bbabb9719bc92601f7bc1ad8b69411e98

acceptance manifest SHA256:
notebook clean proof:
42 + 42 candidate verification result:
current-main source verification result:
```

### Changed paths

Exact list and diff stat.

Paths outside §4:

```text
none
```

or STOP report.

### Nano-commit chronology

Each commit must tell one discrete story, for example:

```text
1. re-anchor frozen acceptance runner on post-genesis production
2. prove frozen/input/authority fail-closed guards
3. record real two-arm acceptance evidence
```

Do not bundle production cleanup.

### Per-arm handback

For OpenAI and DeepSeek:

```text
database:
world_id:
genesis source revision:
D0:
six PC IDs:
C1 S1 child:
C1 S1 parent:
42-session receipt count:
terminal revision:
source/provenance totals:
candidate edges:
accepted/published edges:
rejected edges + reasons:
object counts by kind:
identity ambiguity/collision observations:
wall time:
model_calls:
benchmark result:
```

### Cross-arm comparison

State explicitly:

* whether baseline genesis semantics were equivalent;
* whether both chains were complete;
* where identity outcomes diverged;
* where durable object/relationship structure diverged;
* whether one arm exhibited materially worse rejection/collision/provenance behavior;
* whether an existing semantic benchmark supports selecting an arm.

### Verdict vocabulary

Use one of:

```text
STRUCTURAL ACCEPTANCE PASS
STRUCTURAL ACCEPTANCE HOLD
```

and separately:

```text
SEMANTIC MODEL SELECTION GO: <arm>
SEMANTIC MODEL SELECTION HOLD
```

Do not collapse these into one verdict.

### Required declarations

```text
New model calls: 0
Candidate regeneration: none
Frozen manifest modifications: none
Cross-arm state copying: none
Manual graph repairs: none
Production runtime modifications: none
Operator waivers: none | <exact waiver>
Stop conditions: none | <exact stop report>
Rehearsal database teardown: complete | intentionally retained pending review
```

### Retirement recommendation

The handback may recommend closing #715 only when:

* structural acceptance is PASS;
* evidence is preserved outside the rehearsal databases;
* any required semantic-selection successor is clearly named;
* no production-worthy behavior remains trapped only in #715.

It must not close #715 itself.

---

## §9 Acceptance rubric

The execution/evidence slice is accepted only when every applicable item is true.

* [ ] Governed genesis predecessor was exact-head reviewed and merged before activation.
* [ ] Execution base is exact post-genesis `main`.
* [ ] No production `apps/**` or `src/**` path changed.
* [ ] Notebook checkout is exact reviewed head and clean.
* [ ] Frozen manifest was not modified.
* [ ] All 84 candidate graphs match frozen hashes.
* [ ] All 42 canonical source files match frozen source hashes in both arm manifests.
* [ ] C2 S26/S27 remain outside the experiment.
* [ ] Each arm is bound to its exact database and derived World ID.
* [ ] Both real authorities were pristine before genesis.
* [ ] Genesis prepare was inert for each arm.
* [ ] Each `D_0` has parent null and exactly the six canonical PC identities.
* [ ] Baseline genesis semantics are equivalent without copying state.
* [ ] Each C1 S1 is an ordinary child of its own `D_0`.
* [ ] Both arms publish all 42 sessions with uninterrupted parent continuity.
* [ ] Every source is exact, campaign/session-scoped, admitted, and traceable.
* [ ] Terminal native head equals the final receipt child for each arm.
* [ ] No model call or candidate regeneration occurred.
* [ ] Structural comparison evidence is complete.
* [ ] Existing semantic/query benchmark was run unchanged, or semantic model selection remains explicitly HOLD.
* [ ] Final report states what the experiment does and does not prove.
* [ ] Evidence received independent exact-head review.
* [ ] Teardown touched only the two named rehearsal databases.
* [ ] #715 remains unmerged.
* [ ] No successor capability is silently claimed as part of this slice.

## Stop / rollback / rebrief conditions

Stop rather than expand if any of the following occurs:

* predecessor genesis is not merged or its merged shape differs from the reviewed contract;
* current production base changes after Gate A review;
* implementing the runner requires changing production runtime code;
* #715 notebook head differs from the reviewed hardening authority;
* notebook working tree is dirty;
* frozen manifest differs;
* any candidate digest differs;
* current canonical source bytes differ from frozen source authority;
* either rehearsal authority is non-pristine and cannot be safely reset;
* arm/database/World identity cannot be proven exactly;
* the two genesis baselines differ in source digest, roster meaning, or PC identity set;
* C1 S1 cannot publish as an ordinary child of `D_0`;
* any session receives the wrong parent;
* provider head diverges from the recorded child;
* one arm sees state from the other;
* any model/extraction path becomes necessary;
* a candidate needs manual repair;
* source identity can only be preserved by widening the production SourceArtifact contract;
* an existing deterministic semantic benchmark cannot be identified and the operator asks for a model-winner claim anyway;
* final evidence cannot distinguish frozen candidate behavior from governed-publication behavior;
* any required write path falls outside §4.

For a failed real run:

```text
1. Stop immediately.
2. Preserve failure evidence.
3. Do not resume the partial arm and call it final acceptance.
4. Diagnose under this handoff only if no production semantic change is needed.
5. If a reattempt is authorized, return that arm to a pristine authority and restart from genesis.
6. If production changes are needed, write a separate successor handoff.
```

Stop report format:

```text
Stop condition:
Exact production base/head:
Exact notebook head:
Arm/session:
Last valid parent:
Observed failure:
Durable state after failure:
Invariant clause affected:
Required evidence now missing:
Production contract change required:
Proposed successor slice:
Safe state / teardown recommendation:
```

---

# Expected end state

Success does **not** mean PR #715 becomes mergeable.

Success means we can point to a bounded evidence package and say:

```text
On exact production version X,
two independently initialized Worlds began from equivalent canonical PC baselines.

The exact frozen OpenAI and DeepSeek candidate arms were replayed,
without model calls or manual graph repair,
through the ordinary governed World write path.

Each produced an uninterrupted 42-session immutable revision chain
whose first observed recap was an ordinary child of governed D0.

We know exactly how the resulting durable graphs differ,
what those differences do and do not tell us,
and whether an existing predeclared semantic benchmark supports a model choice.
```

At that point #715 has fulfilled its purpose as a lab notebook.

The next steward action is a separate bounded report/retirement decision, not a merge of the notebook.
