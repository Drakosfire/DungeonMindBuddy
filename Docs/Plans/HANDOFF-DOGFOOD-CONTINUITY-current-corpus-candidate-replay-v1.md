# HANDOFF — DOGFOOD-CONTINUITY: current-corpus candidate replay v1

**Created:** 2026-09-16
**Activated:** 2026-09-16
**Status:** DONE — MERGED as PR #730 @ `ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d`; reviewed head `634f8d4b0807058a8309d5b19978855b9c7d4cc5`; Review Cycle 1 APPROVE (GitHub COMMENT fallback, self-review); replay PASS; product loadability NOT_READY at recap source-read; lease released
**Canonical path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md`
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`
**Flow / owner:** `DOGFOOD-CONTINUITY / product loadability / provenance-correct replay`
**Direction:** DESIGN → EVALUATE → REVIEW → TARGETED PRODUCT DOGFOOD
**Design authority base:** `main@074d4f66f94d4b391a7aaf485b69030a20d576e4` — PR #729 merged
**Predecessor:** `HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md` — merged as PR #729
**Predecessor merge:** `074d4f66f94d4b391a7aaf485b69030a20d576e4`
**Reviewed predecessor head:** `5cc8a89ce67d2cc9abefe66c7f343f6dd3cb01c3`
**Predecessor review:** Cycle 4 APPROVE, review `5230245572`
**PR topology:** `serial`
**Authorized branch:** `dogfood-continuity/current-corpus-candidate-replay-v1`
**Authorized PR title:** `DOGFOOD-CONTINUITY: replay accepted candidates into a pristine World`
**PR authorization:** open exactly one evaluation PR for this handoff. No repair, model-rerun, backfill, UI, Hermes, or successor PR from this worker.
**Dispatch rule:** branch from current `origin/main` after this handoff is present; never branch from a pre-#729 base.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Sequencing authority: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Readiness doctrine: [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md).

---

## §0 Why this slice exists

The historical 44-session acceptance World proved chronological governed-write continuity, then failed product dogfood because ordinary DungeonMind reads could not admit recap-backed objects whose source provenance had not been durably admitted.

PR #729 repaired the **fresh write contract**. It did not mutate the historical accepted World.

The next question is deliberately narrower than a new extraction/model evaluation:

> **If we replay the exact candidate semantics that already passed structural acceptance, through the repaired production source-admission and governed-write path, do we get a pristine World that normal DungeonBuddy product reads can actually open and traverse?**

This slice isolates the provenance/write repair from model variance.

---

## §1 Merge-ready invariant

> **The exact frozen 44-session candidate cohort from the accepted structural run, with no model regeneration and no semantic rewriting, can be replayed chronologically into one pristine provenance-correct World; the resulting published identities then round-trip through ordinary Buddy/DungeonMind product reads, including the known Mireward witness and source/evidence navigation, while the historical accepted World remains untouched.**

The proof chain is:

```text
accepted structural run artifacts
  exact manifest + exact session ledger + exact 44 candidate JSON documents
        ↓ verify bytes/digests/order/source identity
current canonical recap source bytes
        ↓ exact sha256 + canonical source artifact registration
current production Candidate Graph Admission
        ↓ #729 source prove/admit + sealed source identity
current production governed confirm
        ↓ immutable child + exact-head advancement
new pristine replay World
        ↓ normal Buddy projection/search/object/complete/neighborhood/evidence/source-read
product-loadability verdict
```

A replay PASS does not establish semantic correctness, Agent usefulness, or model selection.

---

## §2 Frozen predecessor evidence

The replay source authority is the already-accepted run:

```text
historical structural report:
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md

accepted run:
execute-2026-09-16T020204Z-6e3b812a

accepted run git head:
26e40f1eb108544516160a97acc6627fac3fe39d

artifact root:
out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-16T020204Z-6e3b812a/

manifest count:
44

manifest digest:
d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c

originating extraction model:
gpt-5.4-mini

originating model-policy digest:
477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212

historical World:
dogfood-current-corpus-acceptance-v1

historical database:
dmb_current_corpus_acceptance_v1

historical terminal head:
rev:cce8d24621d65a018d3e2922552f56f2
```

The old acceptance harness wrote the candidate documents before admission and wrote a session ledger binding each candidate locator and canonical candidate digest to its frozen source/session identity.

Those retained artifacts are **replay inputs**, not graph truth. The original recap bytes remain source evidence authority.

### Artifact availability is fail-closed

Before any graph mutation, the runner must prove all of the following:

```text
artifact root exists
manifest.json exists and digest/count match the accepted report
session_ledger.json exists and contains exactly 44 unique chronological rows
all 44 candidate locators resolve inside the accepted artifact root/repository
all 44 candidate files exist
canonical_candidate_digest(candidate) equals the sealed ledger digest
ledger campaign/session/source fields agree with the frozen manifest
current original recap bytes still equal each frozen original_sha256
current normalized lineage bytes still equal each frozen normalized_sha256
```

If any item is unavailable, ambiguous, outside the allowed root, duplicated, missing, or drifted:

```text
STOP = replay_artifact_unavailable | replay_artifact_drift
model_calls = 0
new World graph writes = 0
```

Do **not** fall back to extraction. Do **not** regenerate one missing candidate. Do **not** substitute a newer candidate.

---

## §3 Runtime isolation

Use a new authority, never the historical accepted database.

```text
World:    dogfood-current-corpus-replay-v1
Database: dmb_current_corpus_replay_v1
Host:     127.0.0.1
Port:     54330
Output:   out/graph_memory/current_corpus_candidate_replay_v1/<run-id>/
Operator: current-corpus-candidate-replay-v1
```

The runner must refuse:

- the historical database name `dmb_current_corpus_acceptance_v1`;
- the historical World id `dogfood-current-corpus-acceptance-v1`;
- non-loopback authority DSNs;
- a replay World that is not pristine before genesis.

No reset/drop/delete behavior belongs in the runner. If the database/World is not pristine, STOP and require the operator to provide a fresh migrated database.

Buddy APP-STATE, if needed for HTTP/product-read smoke, must use a different database from the World authority database.

---

## §4 Replay contract

### 4.1 Zero model calls

This lane must not call `run_production_extraction`, an LLM provider, or model policy resolution as part of replay execution.

Record the predecessor's model/model-policy values only as provenance metadata for the frozen candidate cohort.

Required execution claim:

```text
model_calls = 0
candidate_regenerations = 0
candidate_rewrites = 0
```

### 4.2 Genesis

Initialize the new World through the existing production recap-world genesis path using the canonical C1 party registry, producing one real D0 with null parent.

Do not copy D0 from the historical database.

If genesis itself produces provenance-invalid product objects, preserve that as the earliest replay/product-loadability STOP. Do not repair genesis in this PR.

### 4.3 Per-session replay

For each of the exact 44 manifest rows, strict chronological order C1 then C2:

1. verify frozen original + normalized source bytes;
2. load the exact retained candidate JSON;
3. recompute and compare its canonical candidate digest;
4. reconstruct/load the canonical current `GraphMemorySourceArtifact` from the exact frozen source bytes and require its artifact id to equal the manifest/ledger authority;
5. load mutation context at the exact current replay head;
6. call **current production** `prepare_candidate_graph_admission()` with the canonical source artifact + mounted source-admission authority;
7. require confirmable admission or STOP at that exact session;
8. prove the exact candidate object is unchanged by admission;
9. call current production `confirm_candidate_graph_admission()` / governed confirm seam;
10. require receipt parent = prior head, current head = receipt child, and immutable child parent = prior head;
11. append a replay ledger row binding predecessor candidate digest → new proposal/child/source proof.

No sanitize/repair/skip/resume/selective substitution.

A STOP leaves all earlier replay revisions as diagnostic evidence but does not become PASS and may not resume from the partial World.

### 4.4 Source-provenance proof

For every confirmable replay row, capture enough sealed evidence to establish:

```text
source_artifact_id
Buddy source revision token
DungeonMind admitted source_revision_id
content_sha256
source domain/key
campaign/session scope
snapshot proof at prepare
snapshot re-proof at confirm
```

A source identity conflict, missing canonical source, fingerprint drift, foreign scope, or confirmation-time proof failure is an immediate STOP at the owning session.

---

## §5 Product-loadability acceptance

A complete 44-session replay is **necessary but not sufficient**.

After the terminal replay head exists, exercise the normal Buddy DungeonMind read adapter. No direct SQL/raw-payload fallback may satisfy this section.

### 5.1 Campaign projections

At the exact replay terminal head, run ordinary GM campaign-scope projections for both:

```text
longmont-c1
longmont-c2
```

Record returned object/relationship counts, exclusions, provenance diagnostics, and exact revision identity.

Any `stored_provenance_invalid`, missing-source, scope-unknown-for-in-scope-recap, or equivalent rejection of a replayed recap-backed object keeps:

```text
PRODUCT LOADABILITY = NOT_READY
```

### 5.2 Emitted-ID round trip

For every node identity emitted by the campaign projections (or every node if the API already returns the bounded full set), prove through ordinary Buddy reads at the same World/campaign/revision:

```text
projection emits X
→ exact-object(X) resolves X
→ complete-object(X) resolves X
→ neighborhood(X) treats X as present
→ evidence(X) does not treat X as missing
```

True objects with no evidence may truthfully return an empty evidence set; they may not fail as nonexistent solely because of identity/provenance loss.

Do not invent aliases or translate IDs in the evaluator.

### 5.3 Mireward must clear the historical defect

Recover the replay child revision for C2S22 from the **new replay ledger**.

At that exact immutable revision, with campaign `longmont-c2`, require:

```text
node:location:mireward appears in native/Buddy scoped product reads
exact-object(node:location:mireward) resolves
complete-object resolves
neighborhood treats it as present
evidence resolves one or more provenance-valid recap anchors
at least one source anchor can be read through the normal source-read contract
returned source bytes/anchor remain bound to the same World/campaign/revision
```

If the exact durable ID differs because the unchanged candidate/admission contract legitimately resolves identity differently, record the sealed identity decision and use the **product-emitted durable ID**. No caller-side prefix guessing is allowed.

### 5.4 Historical C1S10 benchmark revision

Recover the new replay child revision for `longmont-c1 / session-10` and record it as the successor benchmark pin candidate.

Do **not** run or score the 16-question gauntlet in this PR.

Run only a read smoke at that historical replay revision sufficient to prove the pin exists, is an ancestor of terminal head, and ordinary product reads can resolve at least one known object (for example Torbin) without falling forward to terminal head.

### 5.5 Source read is part of loadability

At least one recap-backed source anchor from each campaign must successfully traverse the ordinary source/evidence read contract with digest verification.

A graph object that opens but whose admitted source navigation dead-ends does not clear Gate B for this slice.

---

## §6 Operator dogfood witness

This PR does not modify UI or mounting behavior. After Gate B automation is green, perform a small read-only ordinary-product witness using the normal local stack documented in `Docs/Runbooks/RUNBOOK-local-play-dogfood.md`:

```text
mount/select the replay World through the ordinary supported product context
open/search Mireward
open its details
follow an evidence/source path
verify the authority/revision shown is the replay World, not historical Eldyrwild/default state
```

If the product cannot select/mount this World without ad-hoc internal request crafting, record:

```text
PRODUCT LOADABILITY = PASS (only if §5 passed)
OPERATOR DOGFOOD = NOT_READY
first owning boundary = mounting/context surface
```

and STOP the operator claim. Do not modify UI in this PR.

If §5 itself fails, do not use UI behavior to reinterpret the failure.

---

## §7 Write lease

This is an evaluation/acceptance lane. Production graph semantics are read-only.

### Authorized implementation paths

| Action | Path | Purpose |
|---|---|---|
| CREATE | `evals/graph_memory_layer/run_current_corpus_candidate_replay_acceptance.py` | fail-closed zero-model replay + product-loadability runner |
| CREATE | `tests/test_current_corpus_candidate_replay_acceptance.py` | deterministic replay/artifact/runtime/loadability contract tests |
| CREATE | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md` | exact run provenance, STOP/PASS boundary, loadability and dogfood evidence |

### Backward-looking predecessor sync authorized in this PR

These edits record facts already true before this lane began:

| Action | Path | Required truth |
|---|---|---|
| MODIFY | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md` | mark merged/complete; PR #729, merge `074d4f66…`, 4 review cycles, fresh governed recap provenance contract PASS |
| MODIFY | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md` | replace stale awaiting-review header with final reviewed/merged status; preserve historical accepted World NOT_READY |

Do not pre-mark this replay slice complete in those files.

### Read-only production seams

```text
apps/live_control_server/services/candidate_graph_admission.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
apps/live_control_server/services/source_artifact_registry.py
apps/live_control_server/services/recap_world_genesis.py
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
corpus/**
benchmark gold
DungeonMind dependency/pin
apps/live-control-ui/**
Hermes / Agent code
```

If completing the replay requires a production change, STOP and hand back the first owning boundary. Do not repair production inside this evaluation PR.

One bounded evaluator-only helper file under `evals/graph_memory_layer/` may be added **only** if static serialization/schema code cannot reasonably live in the runner. It may not contain copied candidate semantics, rewritten corpus data, or a compatibility shim.

---

## §8 Deterministic regressions

At minimum prove:

1. accepted artifact root missing → STOP before genesis, zero model calls/writes;
2. manifest count/digest mismatch → STOP;
3. duplicate/missing/out-of-order ledger row → STOP;
4. candidate file path escape → STOP;
5. candidate missing → STOP;
6. candidate canonical digest mismatch → STOP;
7. original or normalized source byte drift → STOP;
8. replay never calls extraction/model seam;
9. non-pristine replay World → STOP; no reset behavior;
10. historical World/database identifiers are rejected;
11. one replay row forwards the exact candidate unchanged to admission;
12. nonconfirmable current admission → STOP at that row; no later session processed;
13. stale parent/receipt/head mismatch → STOP;
14. successful row records sealed source admission + exact child continuity;
15. product read round-trip rejects an emitted ID that exact-object cannot reopen;
16. Mireward acceptance fails if evidence/source read is unresolved;
17. historical revision pin smoke rejects terminal-head leakage;
18. a partial STOP cannot be resumed as PASS.

Use injected seams for deterministic unit coverage, but the final real replay must exercise current production admission/write/read boundaries.

---

## §9 Real execution and report

CLI should remain intentionally small:

```text
--preflight <accepted-run-artifact-root>
--execute <accepted-run-artifact-root>
--product-smoke <completed-replay-run-root>
```

Equivalent explicit names are acceptable; do not add repair/regenerate/resume switches.

The durable report must include:

```text
exact git head
predecessor #729 merge SHA
accepted source run id/path
accepted manifest digest + count
candidate cohort verification result
model calls = 0
new World/database/runtime isolation
new D0
44-row replay ledger summary
terminal head or first STOP
source artifact/revision counts/proof summary
C1 + C2 projection results
emitted-ID round-trip totals
Mireward C2S22 revision + read/source results
new C1S10 benchmark-pin revision + ancestor/read-smoke result
historical accepted World head unchanged / not targeted
product loadability verdict
operator dogfood verdict
next owning boundary if NOT_READY
```

Do not report the predecessor's historical `4/16` oracle diagnostic as a replay semantic score.

---

## §10 PASS / STOP semantics

### Full replay + product read PASS

Only if all 44 candidates replay and §5 clears:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS (historical result retained)
FRESH GOVERNED RECAP SOURCE PROVENANCE CONTRACT = PASS (#729)
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
PRODUCT LOADABILITY = PASS for the replay World
```

`OPERATOR DOGFOOD` is separately PASS/NOT_READY from §6.

Still false/not established:

```text
semantic truthfulness / recall / precision
Agent usefulness
semantic model selection
historical accepted World repaired
historical backfill safety
```

### Replay STOP before terminal head

```text
PRISTINE ACCEPTED-CANDIDATE REPLAY = HOLD
PRODUCT LOADABILITY = NOT_MEASURED
OPERATOR DOGFOOD = NOT_MEASURED
```

Report the first exact session/boundary and preserve candidate/source evidence. No repair in this PR.

### Replay completes but product reads fail

```text
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
PRODUCT LOADABILITY = NOT_READY
OPERATOR DOGFOOD = NOT_MEASURED
```

The report must distinguish write success from read failure and localize the first normal-product boundary.

### Product reads pass but ordinary mounting fails

```text
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
PRODUCT LOADABILITY = PASS
OPERATOR DOGFOOD = NOT_READY
```

That handback becomes the next steward slice. Do not solve it here.

---

## §11 Stop / split conditions

STOP and return to the steward if any of these becomes necessary:

- any model/extraction call;
- semantic candidate repair or regeneration;
- mutation/backfill of `dmb_current_corpus_acceptance_v1`;
- production code change;
- DungeonMind dependency/pin or provenance-rule change;
- direct SQL as replay/write/read authority;
- alias/prefix heuristics in evaluator or Buddy reads;
- corpus source edits;
- UI/mounting implementation;
- Agent/Hermes/benchmark scoring;
- resuming a partial replay World;
- a second PR.

A STOP is useful evidence when it names the first owning boundary. Do not broaden the lease to turn a STOP into green.

---

## §12 Review decision signal

Formal review must answer, in order:

1. Are the replay inputs exactly the accepted 44-candidate cohort, with manifest/ledger/candidate/source digests re-proven?
2. Were there **zero** model calls and zero candidate semantic rewrites?
3. Was a genuinely pristine, isolated World used, with the historical accepted World untouched?
4. Did every replay row use current production source admission, candidate admission, governed confirm, and exact-head continuity?
5. If all 44 completed, do ordinary Buddy reads—not raw payload/SQL—round-trip emitted product IDs?
6. Does Mireward specifically clear the historical provenance/read defect at the new C2S22 revision, including evidence/source navigation?
7. Does the new C1S10 revision support an exact historical pin without terminal-head leakage?
8. Are PASS/NOT_READY claims scoped to the gates actually measured?
9. Did the PR stay inside the evaluation + predecessor-sync lease and avoid production repair?

A complete green review authorizes merge of the acceptance capability/report. It does not authorize the subsequent semantic gauntlet PR.

---

## §13 Worker pickup

Read, in order:

1. this handoff;
2. `Docs/Design/ACCEPTANCE-dogfood-readiness.md`;
3. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md`;
4. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`;
5. `evals/graph_memory_layer/run_current_corpus_admission_acceptance.py`;
6. current production candidate admission / governed writes / source-admission adapter / direct read adapter.

First action is replay-artifact preflight. Do not write a harness that silently manufactures replacement inputs.

Open the one authorized PR without asking again once the branch is based on current `origin/main` containing this handoff.
