# HANDOFF — DOGFOOD-CONTINUITY: recap source provenance admission v1

**Created:** 2026-09-16  
**Activated:** 2026-09-16  
**Status:** ACTIVE — governed recap source-provenance admission; Case B predecessor closed; serial implementation PR authorized  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY / product loadability / governed recap provenance`  
**Direction:** DESIGN → CODE → REVIEW → TARGETED NATIVE DOGFOOD  
**Design authority base:** `main@f95de4c26483b5b556a8f3411e389824c837f3a4`  
**Predecessor evidence on main:** accepted Case B report from `1a4588e7a853f811c15b213e4299866e3710281d` at `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md`  
**Activation gate:** satisfied — Case B report durable; predecessor closed STOP / dependency handback; no open implementation PR  
**Dispatch base:** `main@cf43ec97d6648667923c543e609dd4c27a6481fc` — create the implementation branch from current `origin/main` at or after the activation commit  
**PR topology:** `serial`  
**Authorized branch:** `dogfood-continuity/recap-source-provenance-admission-v1`  
**Authorized PR title:** `DOGFOOD-CONTINUITY: make governed recap writes provenance-complete`  
**PR authorization:** open/update exactly one implementation PR for this capability; no accepted-World rebuild, UI, Hermes, coverage, or successor PR from the same worker

**Activation facts:**

```text
predecessor Case B closeout:
3fc400af0b425fb02be1a904d3e541d90ea29362
predecessor pin / current main:
cf43ec97d6648667923c543e609dd4c27a6481fc
canonical Case B report:
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-published-object-addressability-v1.md
accepted evidence head:
1a4588e7a853f811c15b213e4299866e3710281d
classification:
Case B TRUE → STOP
Case A:
FALSE
Case C:
NOT ESTABLISHED / not required to proceed
open implementation PRs at activation:
none
§5 collision:
none — no open PRs; UI/kernel worktrees do not lease candidate_graph_admission.py, world_graph_writes.py, contribution_mapping.py, or extract_promote.py
```

> Repository law: [`AGENTS.md`](../../AGENTS.md). Sequencing authority: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Readiness doctrine: [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md). Source-admission architecture precedent: [`HANDOFF-CUTOVER-buddy-graph-engine-demolition.md`](HANDOFF-CUTOVER-buddy-graph-engine-demolition.md).

---

## §0 Activation gate

Activation is complete. The write lease in §5 is now exclusive for the one authorized PR.

```text
1. satisfied — Case B report durable on main from 1a4588e7a853f811c15b213e4299866e3710281d
2. satisfied — published-object-addressability closed as STOP / dependency handback
3. satisfied — origin/main@cf43ec97d6648667923c543e609dd4c27a6481fc; open implementation PRs: none
4. satisfied — this activation records the dispatch base
```

---

## §1 Mission and merge-ready invariant

### Mission

Identify the exact production seam that allowed structurally accepted recap contributions to publish graph revisions whose evidence was not backed by usable DungeonMind source provenance, then repair that seam without weakening native provenance checks or hiding the failure in Buddy reads.

This is not an ID-alias repair. The accepted-world addressability investigation found a native provenance failure before the Buddy adapter boundary.

### Merge-ready invariant

> **A governed recap candidate may become confirmable and publish only when every accepted assertion's exact source artifact/revision pair is admitted and snapshot-provable in DungeonMind, and the published evidence record is compatible with that admitted source. A newly published recap-backed object must therefore survive native scoped projection and round-trip through native search/exact-object/neighborhood/evidence at the same immutable revision.**

One invariant governs both prevention and proof:

```text
verified recap source bytes
→ exact Buddy source identity
→ exact DungeonMind SourceArtifactV2 + SourceRevision admitted
→ confirmable candidate sealed against that admitted pair
→ confirm re-proves the sealed pair
→ published EvidenceRef uses compatible recap provenance
→ scoped native projection admits the fact
→ native retrieval can open it
```

A graph child existing in `graph_revisions` is not sufficient.

---

## §2 Accepted evidence and current hypothesis

The predecessor Case B investigation observed, at C2S22 `rev:24268294e868b30034e247aa9e23087b`:

```text
published object id:          node:location:mireward
existence assertion subject:  node:location:mireward
native exact object:          found=false / stored_provenance_invalid
native projection objects:    0
payload objects:              924
scope_unknown exclusions:     918
in-scope provenance rejects:  6
source_artifacts in World:    1
evidence_refs in payload:     399
Mireward source artifact:     artifact:recap:longmont-c2:session-21:ad4ecd013dad
Mireward source row:          missing
World head unchanged:         true
```

The amended report correctly leaves identity Case C `NOT ESTABLISHED / not required to proceed`; Case B independently forces STOP.

Repository code exposes a strong but still-to-be-proven production hypothesis:

1. `src/graph_memory/candidate_graph_to_contribution.py` constructs recap assertion source identity and embedded `source_artifacts` metadata, but that metadata is contribution content, not SourceRepository persistence.
2. `apps/live_control_server/services/candidate_graph_admission.py::prepare_candidate_graph_admission()` can return a confirmable governed candidate without calling the mounted DungeonMind source-admission authority.
3. `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py::_build_pair_to_dm()` derives/catalog-resolves DungeonMind source revision IDs but does not `put_artifact` / `put_revision`.
4. `confirm_extract_promote_via_dungeonmind()` finalizes and publishes the review after `_build_pair_to_dm()`; `publish_finalized_review` is graph publication, not source admission.
5. The existing production source-admission adapter already owns the correct SourceRepository behavior: `prove_or_admit()` maps the exact source pair, `put_artifact` + `put_revision` idempotently, and proves the pair via `get_provenance_snapshot()`.
6. Normal `source_extraction` contribution mapping currently builds its v2 candidate with `_EmptyEvidenceView()`. The missing-evidence fallback in `contribution_mapping._map_contribution_evidence_ref()` stamps `SourceDomain.OTHER`, `can_open_source=False`, and no locator. Once missing source rows are repaired, this fallback may become the next provenance mismatch rather than a successful read.

This handoff does **not** declare #6 to be the root cause before the worker proves it against a fresh controlled publication. It does require the worker to test it before claiming the defect fixed.

The existing CUTOVER source-authority contract is controlling precedent:

```text
prove/admit the exact mapped SourceArtifactV2 + SourceRevision
before returning a confirmable prepare;
confirm re-proves the sealed pair;
_build_pair_to_dm is derivation, not admission;
publish_finalized_review is graph publication, not source insertion;
missing/mismatched source identity fails closed.
```

Reuse that authority. Do not invent a second source catalog or direct-SQL source writer.

---

## §3 Root-boundary localization — prove before editing

Before changing production code, reproduce one minimal recap-backed governed write in a fresh scratch World/database or isolated transaction fixture and capture this ledger:

```text
Buddy source_artifact_id
Buddy source_revision token / content sha256
source domain / campaign / session / world / URI
catalog-aware DungeonMind source_revision_id
SourceRepository artifact before prepare
SourceRepository revision before prepare
candidate confirmable?
sealed proposal source fields
SourceRepository artifact after prepare
SourceRepository revision after prepare
v2 EvidenceRef source_artifact_id
v2 EvidenceRef source_revision_id
v2 EvidenceRef source_domain / source_domain_key
v2 EvidenceRef locator / can_open_source
published child revision
native scoped projection result
native exact-object result
native evidence/source result
```

Classify the first owning defect:

### Case P1 — source pair is never admitted

```text
confirmable prepare = yes
SourceRepository pair = absent
publish succeeds
native scope = SCOPE_UNKNOWN / stored_provenance_invalid
```

Repair candidate admission so no confirmable prepare exists before exact source admission + snapshot proof. Confirm must re-prove the sealed pair.

### Case P2 — source pair is admitted, but recap evidence is stamped incompatible provenance

Examples:

```text
artifact domain = SESSION_RECAP
EvidenceRef domain = OTHER
or
revision/locator/openability disagrees with admitted source
```

Repair the smallest recap contribution/evidence mapping seam so source-extraction evidence is derived from the verified/admitted source pair instead of the generic `_EmptyEvidenceView()` fallback. Do not weaken DungeonMind scope validation.

### Case P3 — both P1 and P2 are required

This is allowed inside this slice because they are two broken stages of the same merge-ready invariant: **one governed recap write must be provenance-complete before publication and remain admissible after publication.** The PR must keep the changes connected by one end-to-end regression.

### Case P4 — Buddy supplies a correct admitted pair and compatible evidence, but DungeonMind SourceRepository/projection still rejects it

STOP. Produce a compact DungeonMind dependency handback with exact object/source/revision IDs and native results. Do not change the DungeonMind dependency pin or add a compatibility waiver in this PR.

### Case P5 — only an in-place rewrite/compatibility rule can make the already-published accepted World readable

STOP that historical remediation. Published graph revisions remain immutable. This PR repairs the production write contract and proves it on a fresh controlled publication. Any historical accepted-World rebuild/replay/backfill/compatibility policy is a separate steward decision after merge.

---

## §4 Implementation contract

### 4.1 Prepare-time source authority

For a recap candidate that would otherwise be confirmable:

```text
verified source URI + bytes
verified sha256 token
canonical source_artifact_id
campaign_id
session_id
world_id
source_domain = recap
```

must resolve to one `GraphMemorySourceArtifact` / source identity and pass through the existing mounted `WorldGraphSourceAdmissionAuthority`.

Required behavior:

```text
prepare determines candidate is structurally/semantically confirmable
→ validate source scope
→ prove_or_admit exact source pair
→ require snapshot-provable admitted artifact + revision
→ seal enough admitted identity into the proposal to re-prove at confirm
→ only then return confirmable=True
```

Do not admit a source merely because an entirely nonconfirmable candidate was inspected unless the existing production contract already requires that side effect.

Source identity conflicts, foreign campaign/world scope, missing digest/URI, or snapshot failure must fail closed before a confirmable token/package escapes.

### 4.2 Confirm-time source proof

Confirm must not trust contribution metadata alone.

Before finalizing/publishing the review:

```text
re-prove the sealed source_artifact_id + admitted DungeonMind source_revision_id
re-prove catalog-aware Buddy-token → DungeonMind-revision derivation when applicable
reject drift/missing source identity
perform no first-time source admission except an explicitly proven idempotent lost-response replay of the exact sealed pair
```

A source proof failure must leave graph head unchanged.

### 4.3 Recap evidence provenance

A published recap assertion must not reach DungeonMind with generic fallback provenance that contradicts its admitted artifact.

For the exact accepted source pair, v2 evidence must bind at least:

```text
source_artifact_id = admitted artifact
source_revision_id = admitted DungeonMind revision
source_domain = SESSION_RECAP
source_domain_key = recap / DungeonMind canonical equivalent
locator/URI = admitted source revision locator when available
can_open_source = true when the source contract can actually open it
```

Do not:

- globally change all missing-evidence fallback from OTHER to recap;
- infer recap from string prefixes alone;
- trust unverified client evidence metadata;
- waive `evidence_source_domain_mismatch` or `SCOPE_UNKNOWN` in DungeonMind;
- reconstruct graph truth on read.

The repair must be scoped to source-extraction/recap evidence whose source identity has already been verified and admitted.

### 4.4 Idempotency and collision behavior

Reuse the existing catalog-aware source revision derivation. Required cases:

```text
same artifact + same Buddy token → same admitted DM revision / no-op replay
same token already owned by different artifact → collision-safe DM revision id
same source_artifact_id with different fingerprint → source_identity_conflict
confirm retry after publish → same publication receipt; no duplicate source identity
```

Do not fork `_build_pair_to_dm` collision math.

---

## §5 Files in scope — ACTIVE write lease

This table is the exclusive expected write set for the one authorized PR.

### Production paths

| Action | Path | Purpose |
|---|---|---|
| MODIFY | `apps/live_control_server/services/candidate_graph_admission.py` | make source admission/proof a prerequisite of confirmable recap candidate admission; seal source proof identity |
| MODIFY | `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` | re-prove sealed source identity before confirm/publication; use admitted source identity while building the v2 candidate |
| MODIFY if P2/P3 proven | `apps/live_control_server/integrations/dungeonmind/contribution_mapping.py` | remove the recap-specific dependency on generic OTHER fallback; map verified recap evidence from admitted provenance |
| MODIFY if canonical source resolution must stay at the live run boundary | `apps/live_control_server/services/extract_promote.py` | supply the already-authoritative run/source artifact into candidate admission without client invention |

### Tests / report

| Action | Path | Purpose |
|---|---|---|
| CREATE | `tests/test_candidate_graph_source_provenance_admission.py` | deterministic source admission, confirm proof, idempotency, failure, and provenance mapping regressions |
| CREATE | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-recap-source-provenance-admission-v1.md` | root localization, implemented repair, fresh native witness, and remaining readiness claims |

### Backward-looking predecessor state sync in the implementation PR

The Case B addressability predecessor is already closed on `main`. The repair PR updates only documents that would otherwise still claim this provenance slice is unstarted:

```text
Docs/Plans/STEWARDS-ANCHOR-con-ready.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md
```

Those edits record the already-completed Case B predecessor and that this provenance slice is the active work. They must not pre-mark this provenance repair complete, invent its merge SHA, or reopen the closed addressability handoff.

### Read-only unless a stop condition is hit

```text
apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py
apps/live_control_server/ports/world_graph_source_admission.py
apps/live_control_server/ports/world_graph_source_admission_access.py
src/graph_memory/candidate_graph_to_contribution.py
src/graph_memory/evidence/source_artifact.py
evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
DungeonMind dependency / pin
apps/live-control-ui/**
Hermes / Agent code
benchmark gold
corpus recap bytes
accepted World database contents
```

The source-admission adapter is presumed to already implement the required SourceRepository contract. If the worker proves the adapter itself is defective, stop and return the exact failure before expanding the lease.

---

## §6 Required deterministic regressions

At minimum prove:

1. **No confirmable-without-source:** a recap candidate that would be confirmable cannot return `confirmable=True` while its DungeonMind source artifact/revision is absent.
2. **Prepare admission:** successful prepare leaves the exact artifact + revision snapshot-provable without advancing graph head.
3. **Source scope:** foreign campaign/world source identity fails before admission/publication.
4. **Fingerprint conflict:** same artifact ID with incompatible digest/revision fails closed; no overwrite.
5. **Confirm proof:** deleting/missing/drifting the sealed source pair between prepare and confirm prevents graph publication and leaves head unchanged.
6. **Recap domain:** the v2 published evidence for source extraction is `SESSION_RECAP`, not generic `OTHER`, when P2/P3 is the observed path.
7. **Openability:** locator/openability come from the admitted source contract, not a fabricated evaluator value.
8. **Native round-trip:** a fresh published object survives native scoped projection; native search/exact-object/neighborhood/evidence can resolve the published ID at the child revision.
9. **Exact retry:** retry is idempotent for both source identity and graph publication.
10. **Unknown object/source:** true unknown IDs remain truthful misses; no prefix/source guessing.

Helper-only tests are insufficient for #8. At least one integration test must exercise the real DungeonMind SourceRepository + finalize/publish + native projection/retrieval boundary, using a disposable database/world fixture.

---

## §7 Targeted real witness

Do **not** mutate `dmb_current_corpus_acceptance_v1` as implementation proof.

Use a fresh disposable World/database or isolated real-postgres test fixture and run a minimal recap-backed governed write through the production candidate admission → governed confirm path.

Preferred witness shape:

```text
recap source with real bytes + sha256
campaign/session-scoped SourceArtifact
candidate location or NPC with one evidence-backed existence assertion
prepare
confirm
published child
native projection/search/object/neighborhood/evidence
source provenance snapshot/read
```

Required postconditions:

```text
source artifact exists
source revision exists
source pair snapshot-provable
head advances exactly once on confirm
published object appears in scoped projection
exact published ID opens natively
stored evidence is provenance-valid
source navigation has a resolvable admitted source identity
exact retry does not advance head or duplicate source rows
```

If the prior accepted-run C2S21/C2S22 frozen candidate artifacts are locally available, an additional **read-only-source / fresh-World** replay of those candidates is useful dogfood evidence, but it is not required for deterministic CI and must not depend on untracked `out/` files for correctness.

No model call is required for this PR.

---

## §8 Accepted World and rebuild policy

This PR does not rewrite the historical accepted World and does not claim the old C2S22 revision becomes readable.

The current accepted World remains evidence of the defect:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS (historical structural result)
PRODUCT LOADABILITY = NOT_READY
OPERATOR DOGFOOD = NOT_READY
```

After this repair merges and state authority is synchronized, the steward chooses one separate next action:

```text
A. pristine candidate/source replay into a new acceptance World without model regeneration, if the frozen accepted candidates are sufficient and durable;
or
B. pristine current-corpus acceptance rerun through the corrected production path;
or
C. a separately designed historical provenance compatibility/backfill path, only if preserving the exact old World is a product requirement.
```

Do not choose or implement A/B/C inside this PR.

---

## §9 Stop / split conditions

STOP and hand back if any of the following becomes necessary:

- changing DungeonMind source/projection semantics or dependency pin;
- mutating an immutable accepted graph revision;
- direct SQL insertion as the production source-admission mechanism;
- a generic provenance waiver such as “trust artifact when evidence disagrees”;
- changing extraction prompts/model policy/candidate semantics;
- changing Candidate Graph Admission disposition semantics unrelated to source provenance;
- introducing a second source-artifact registry/catalog;
- accepted-World migration/backfill/rebuild;
- UI, operator mounting, Agent, or benchmark work;
- more than the conditional production paths in §5.

If the correct fix lies outside those boundaries, return the exact first owning seam and evidence. Do not broaden the PR.

---

## §10 Review decision signal

Formal review must answer these questions in order:

1. Was the first missing provenance boundary proven rather than guessed?
2. Can a confirmable recap candidate exist while its DungeonMind source pair is absent? **Required answer after repair: no.**
3. Does confirm re-prove the exact sealed admitted pair before graph publication? **Required: yes.**
4. Does source-extraction evidence use provenance compatible with the admitted recap artifact rather than generic OTHER fallback? **Required: yes for the exercised witness.**
5. Does a fresh real published object survive native scoped projection and exact-object retrieval? **Required: yes.**
6. Are source identity conflict, foreign scope, stale/missing proof, and true unknown object cases still fail-closed? **Required: yes.**
7. Did the PR avoid mutating the historical accepted World or weakening DungeonMind provenance validation? **Required: yes.**
8. Is the source/catalog write idempotent and graph-head-neutral at prepare? **Required: yes.**

A PASS establishes only:

```text
GOVERNED RECAP SOURCE PROVENANCE CONTRACT = PASS for fresh writes
```

It does **not** establish:

```text
historical accepted World repaired
full current-corpus product loadability
operator dogfood readiness
semantic coverage
Agent usefulness
semantic model selection
```

---

## §11 Worker pickup

When ACTIVE, the implementation worker starts from the exact dispatch base recorded by the steward and reads, in order:

1. this handoff;
2. the durable Case B addressability report;
3. `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` source-authority contract;
4. `apps/live_control_server/services/candidate_graph_admission.py`;
5. `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py`;
6. `apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py`;
7. `apps/live_control_server/integrations/dungeonmind/contribution_mapping.py`.

First implementation action is the §3 localization ledger, not an edit.

The worker opens the one authorized PR without asking again once the handoff is ACTIVE.