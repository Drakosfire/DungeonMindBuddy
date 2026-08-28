---
pr_body_template: |

  ## Handoff pointer

  * Workstream: CUTOVER / D.2C3 — native genesis read/write continuity
  * Flow: CUTOVER
  * Direction: CODE → REVIEW
  * Existing PR: #651
  * Branch: `cutover/native-genesis-read-write-continuity`
  * Handoff: `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md`
  * Frozen design authority: `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §4

  ## Re-anchor

  * Review state entering this dispatch: Cycle 3 PARK ON PREDECESSOR
  * Cycle 3 reviewed head: `cf453078a5c1950ec5f23a5d5b99001ee9e456db`
  * Parking head: `3a60610dc78b710aa0aea6af817da00b0bfb563e`
  * Predecessor now merged: Buddy #658
  * #658 accepted head: `20499e443d43a5064b6c23b12e9abb331f2f7aa8`
  * #658 merge / dispatch base: `d94822f7681da440fdeea981662383980bfbcaf9`
  * DungeonMind compatibility pin: `5ca5d688612349034f8ca490d465af166d883e6e`
  * Next distinct implementation head submitted for review: Review Cycle 4

  ## Verification pointer

  * Cumulative diff is reviewed against `d94822f7681da440fdeea981662383980bfbcaf9`
  * Required real-PostgreSQL witness: corrected first-world D_0 → admitted native projection/retrieval → WorldGraphAuthority → exactly one D_1 → native read → exact retry
  * Existing-world Buddy-A → D_A remains a mandatory regression
  * Verification: §7

  The checked-in handoff, cumulative diff, nano-commit story, and exact verification
  output are the review contract. The PR description is transport metadata.
---

# HANDOFF — CUTOVER D.2C3 RESUME: native genesis read/write continuity

- **Created:** 2026-08-27
- **Status:** ACTIVE — RESUME #651 after merged provenance predecessor
- **Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md`
- **Repository:** `Drakosfire/DungeonMindBuddy`
- **Flow / owner:** `CUTOVER`
- **Direction:** CODE → REVIEW
- **Existing PR:** #651 — `CUTOVER: native genesis read/write continuity`
- **Branch:** `cutover/native-genesis-read-write-continuity`
- **Exact re-anchor base:** `d94822f7681da440fdeea981662383980bfbcaf9`
- **Named successor:** D.2C4 — manual Graph Review authoring continuity

> This is a resume of the existing D.2C3 capability, not a new capability and not a redesign.
>
> Review Cycles 1–3 remain part of the finding ledger. Cycle 3 parked this PR because native projection of the first-world `D_0` could not truthfully admit its graph facts without rewriting DungeonMind evidence in Buddy. That rewrite was correctly rejected.
>
> The predecessor is now resolved by the merged provenance work: DungeonMind #47 provides the narrow historical compatibility contract, and Buddy #658 corrects the future first-world producer while preserving historical evidence identity.
>
> Do not weaken the original §7/§9 acceptance criteria. The point of this resume is to make the previously failing owning witness pass through the real corrected producer.

## §0 Resume gate and prior finding ledger

Before editing:

1. fetch `origin/main`;
2. confirm `d94822f7681da440fdeea981662383980bfbcaf9` is an ancestor of current `main`;
3. confirm Buddy #658 is merged;
4. confirm the DungeonMind dependency resolves to `5ca5d688612349034f8ca490d465af166d883e6e`;
5. inspect current open PRs for collisions with §4;
6. re-anchor the #651 branch onto the exact current CUTOVER base before making Cycle-4 fixes;
7. preserve the existing nano-commit history rather than rebuilding the capability from scratch.

If current `main` has advanced beyond `d94822f7…`, recheck the intervening commits for §4 collisions. A disjoint main advance is not a redesign trigger; an overlapping semantic change is.

### Finding ledger entering Cycle 4

| Prior finding | Status entering this dispatch | Required Cycle-4 treatment |
| --- | --- | --- |
| Adoption-only binder cannot represent reviewed-init `D_0` | Closed in #651 implementation | Preserve generalized two-genesis binding. |
| First-world binding invented/required a legacy Buddy revision | Closed | `legacy_buddy_revision_id=None` remains mandatory. |
| Provider integrity could be mislabeled unavailable | Closed | Preserve integrity/unavailable distinction. |
| Non-transactional receipt/head observation could report false contradiction | Closed | Preserve bounded reread/stabilization behavior. |
| Buddy rewrote DungeonMind `graph_payload.evidence_refs` before projection | Closed by removal; must stay closed | No read-side normalization or evidence mutation may return. |
| Fresh #645-shaped `D_0` facts were not admitted because producer stored `source_domain="other"` | **Predecessor resolved by #658 + DungeonMind #47** | Re-run through the real corrected first-world producer and prove the facts are now admitted. |
| #651 could not merge while provenance predecessor was unresolved | **Resolved** | Re-anchor and submit one distinct final implementation head as Review Cycle 4. |

Do not reopen closed findings merely to make the branch look newer. Do retest their owning invariants.

## §1 Mission and merge-ready invariant

**Mission:** A world created through reviewed first-world initialization can immediately enter the same DungeonMind-native read, retrieval, mutation-context, publication, and retry lifecycle as an adopted existing world.

**Merge-ready invariant:** **One shared `DirectAuthorityBinding` recognizes exactly the two legal genesis authorities—existing-world adoption and reviewed first-world initialization—and every mounted native read or governed existing-parent write derives revision truth from that binding. A reviewed-init world starts at its real DungeonMind `D_0`, has no fabricated Buddy revision, admits the source-backed facts produced by the corrected first-world path, can publish exactly one legal `D_1`, and can read/recover that child normally; an adopted world preserves its exact Buddy-A → D_A compatibility bridge; contradictory genesis state fails closed; no Buddy graph fallback or read-side evidence rewriting exists.**

### Pre-dispatch critique

| Question | Answer |
| --- | --- |
| Can one invariant govern every observable path? | Yes. Projection, retrieval, authority reads, parent classification, child publication, and retry all depend on the same genesis/revision binding. |
| Most likely adversarial failure now | Rebase resolves the #658 overlap incorrectly: the binder works but the corrected reviewed-init repository is not supplied to native projection, or the old Cycle-3 expectation that D₀ facts are rejected survives in the witness. |
| Will §7 detect it? | Yes. The real-PG witness must create the world through the actual first-world prepare/confirm path, inspect stored provenance, then perform projection, search, exact-object retrieval, authority publication, child read, and retry. |
| Easiest boundary to under-test | Native projection/retrieval. `read_revision()` can see raw graph objects even when admissibility rejects them. The witness must prove admitted projection/search/exact-object behavior, not merely repository presence. |
| Split/stop trigger | Any required new DungeonMind API/schema/UoW; any need to alter #658's producer contract; any Graph Review authoring work; any legacy-engine demolition. |

## §2 Authority and predecessor ledger

### Frozen design authority

`Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §4 remains semantic authority for D.2C3.

Do not redesign its two-genesis model.

### Existing D.2C3 review authority

* PR #651
* Cycle 1: REQUEST-CHANGES-equivalent
* Cycle 2: REQUEST-CHANGES-equivalent
* Cycle 3 reviewed head: `cf453078a5c1950ec5f23a5d5b99001ee9e456db`
* Cycle 3 disposition: PARK ON PREDECESSOR
* parking head: `3a60610dc78b710aa0aea6af817da00b0bfb563e`
* next distinct implementation head submitted for review is Cycle 4

### Resolved predecessor

Buddy #658 — first-world provenance producer correction:

* accepted head: `20499e443d43a5064b6c23b12e9abb331f2f7aa8`
* merge: `d94822f7681da440fdeea981662383980bfbcaf9`
* first-world contribution evidence now takes its domain from the command-owned `WORLDBUILDING` SourceArtifact;
* historical exported evidence identity remains unchanged;
* ambiguous/missing/non-worldbuilding source provenance fails closed;
* no generic admissibility waiver exists.

DungeonMind compatibility predecessor:

* DungeonMind PR #47
* pin: `5ca5d688612349034f8ca490d465af166d883e6e`
* owns the narrow historical reviewed-initialization compatibility family;
* does not authorize generic `OTHER` evidence.

### What remains false

After D.2C3 merges:

* manual Graph Review authoring has **not** moved to governed DungeonMind publication;
* `merge_objects` has **not** been resolved for final authoring;
* legacy graph-engine imports/routes still exist;
* `buddy_files` has not been disabled;
* D.3A has not begun;
* D.3B has not begun;
* CUTOVER is not complete.

Named successor remains **D.2C4 manual Graph Review authoring continuity**.

## §3 Observable paths

| Path | Cycle-3 state | Required Cycle-4 state | Owning boundary |
| --- | --- | --- | --- |
| Fresh reviewed first-world confirm | Produced legal D₀ but historical evidence domain blocked admissibility | Real producer creates legal D₀ with corrected source provenance | initialization + real PG |
| D₀ binding | Worked | Still `genesis="reviewed_world_initialization"` and `legacy_buddy_revision_id=None` | native binder |
| D₀ projection | Snapshot existed but `obj_session22_vial` / `mystery_puddles` were correctly excluded | Both expected facts are admitted through normal projection | native projection |
| D₀ search | Could not truthfully prove expected graph facts | Normal native retrieval finds expected fact(s) | retrieval service |
| D₀ exact-object retrieval | Could not truthfully prove expected graph facts | Exact object retrieval succeeds for expected object ID | retrieval service |
| `current_head(D₀)` | Worked | Exact D₀ | `WorldGraphAuthority` |
| `read_revision(D₀)` | Worked | Exact D₀, no legacy hydration | authority adapter |
| `mutation_context(D₀)` | Worked | Exact D₀/current-head context | authority adapter |
| Publish child from D₀ | Worked | Exactly one legal D₁ whose parent is D₀ | governed publication |
| Native D₁ projection/read | Child existed but inherited inadmissible D₀ facts | Child is readable and corrected inherited facts remain admitted | projection + authority |
| Retry/recover same publication | Worked | Same D₁; no duplicate revision or head | publication/recovery |
| Adopted Buddy-A pin | Worked | Still maps exactly A → D_A | binder/pin algebra |
| Both genesis receipts | Integrity | Integrity | binder |
| Receipt without head | Integrity after stabilization reread | Integrity | binder |
| Head without recognized genesis | Integrity after stabilization reread | Integrity | binder |
| Neither receipt nor head | Ordinary uninitialized/not-adopted failure | Unchanged | binder |

### Required adversarial sequence

```text
real first-world prepare
→ real confirm
→ exactly one reviewed-init receipt
→ zero adoption receipts
→ D_0 head

inspect stored D_0
→ evidence IDs remain stable
→ source provenance is corrected by producer authority
→ no Buddy read-side mutation

construct normal native services
→ reviewed-init binding
→ legacy_buddy_revision_id = None
→ revision pin D_0 passes through exactly

native projection(D_0)
→ obj_session22_vial admitted
→ mystery_puddles admitted

native search
→ expected result is reachable

native exact-object retrieval
→ expected object is reachable

WorldGraphAuthority
→ current_head = D_0
→ read_revision(D_0)
→ mutation_context(D_0)

normal governed existing-parent publication
→ exactly one D_1
→ parent = D_0

native read/projection(D_1)
→ child visible
→ inherited corrected facts remain admitted

retry same operation
→ already_applied / recovered D_1
→ revision count unchanged
→ head remains D_1
```

Then independently prove:

```text
existing Eldyrwild adoption
→ Buddy-A pin still resolves exactly to D_A
→ no regression in adopted-world projection/retrieval
```

## §4 Cumulative write lease

Review the **cumulative PR diff against the Cycle-4 base**, not merely the new commits.

Expected cumulative changed paths for #651 are:

```text
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
Docs/Plans/HANDOFF-CUTOVER-native-genesis-read-write-continuity-code.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
tests/test_cutover_direct_dungeonmind_world_graph_reads.py
tests/test_cutover_native_genesis_continuity.py
```

### Cycle-4 delta should be smaller than the cumulative lease

Expected new work is primarily:

* re-anchor conflict resolution;
* preserving #658's `reviewed_world_initializations` projection dependency while preserving #651's generalized two-genesis binder;
* changing the owning native-genesis witness from the historical rejection expectation to the corrected admitted expectation;
* exercising native search and exact-object retrieval;
* truthful active-state re-anchor.

Do not churn already-correct binder/write code without an observed reason.

### Bounded test-only exception

At most two additional existing CUTOVER tests may be modified if, after re-anchor, an already-existing owning regression must be updated to use the merged #658/#47 contract.

No additional production path is authorized by this exception.

A required production path outside the list above is a STOP.

## §5 Explicit non-goals and collision boundary

Do not modify or claim:

```text
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
pyproject.toml
uv.lock
DungeonMind repository code
apps/live_control_server/routes/graph_authoring.py
graph-authoring services
apps/live-control-ui/**
apps/live_control_server/config.py authority selector
apps/live_control_server/services/world_graph_prewarm.py
apps/live_control_server/routes/world_graph_bootstrap.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
graph_memory/kernel/**
graph_memory/world_supergraph/**
graph_memory/union_supergraph/**
```

Why:

* initialization producer correction is predecessor #658 and should be consumed, not reimplemented;
* DungeonMind #47 dependency pin is predecessor truth and should not move in D.2C3;
* Graph Review authoring is D.2C4;
* selector/import/route retirement is D.3A;
* physical package deletion is D.3B.

No frontend behavior belongs in this slice.

## §6 Implementation contract

### Binding

Exactly two genesis families:

```text
existing_world_adoption
reviewed_world_initialization
```

Adopted world:

```text
legacy_buddy_revision_id = Buddy A
dungeonmind_first_revision_id = D_A
pin A → D_A
real DungeonMind pins → pass through
```

Reviewed-init world:

```text
legacy_buddy_revision_id = None
dungeonmind_first_revision_id = D_0
pin D_0 → D_0
descendant DungeonMind pins → pass through
```

No fake/sentinel Buddy revision is legal.

### Genesis topology

```text
adoption receipt + no reviewed-init receipt + head
→ legal adoption binding

reviewed-init receipt + no adoption receipt + head
→ legal reviewed-init binding

both receipts
→ authority_integrity

one recognized receipt + no head
→ stabilize/reread once
→ if still contradictory: authority_integrity

head + neither receipt
→ stabilize/reread once
→ if still contradictory: authority_integrity

no head + neither receipt
→ ordinary uninitialized/not-adopted fail-closed behavior
```

Provider `PersistenceIntegrityError` remains integrity.

Provider availability failure remains unavailable.

### Provenance trust boundary

The most important Cycle-4 rule:

> **Buddy native reads consume the stored DungeonMind graph payload exactly.**

Forbidden:

```text
projection-time source_domain correction
retrieval-time source_domain correction
wrapper repository rewriting evidence_refs
generic OTHER → WORLDBUILDING normalization
reconstructing evidence from Buddy source files
admissibility override
Buddy-file fallback
```

The corrected first-world producer owns future provenance correctness. DungeonMind owns compatibility/admissibility. D.2C3 only consumes their result.

### Child publication

A real reviewed-init `D_0` is an ordinary DungeonMind existing parent.

The existing governed publication algebra remains unchanged:

```text
D_0 + operation O
→ D_1

retry O against D_0
→ recover D_1
→ no D_2
```

No new publication family or provider transaction is introduced.

## §7 Evidence required to merge

### A. Owning real-PostgreSQL witness — mandatory, zero required skips

The owning test must use the real first-world prepare/confirm path and real PostgreSQL.

At minimum it must prove:

```text
fresh world
→ corrected first-world producer
→ D_0

receipt count = 1 reviewed-init
adoption count = 0
head count = 1
revision count = 1

stored D_0 provenance is the corrected producer result
historical evidence IDs remain stable

native binder:
  genesis = reviewed_world_initialization
  legacy_buddy_revision_id = None
  first revision = D_0
  head = D_0

projection(D_0):
  obj_session22_vial admitted
  mystery_puddles admitted

native search:
  expected graph fact reachable

exact-object retrieval:
  expected object reachable

WorldGraphAuthority:
  current_head = D_0
  read_revision(D_0)
  mutation_context(D_0)

publish:
  one D_1
  D_1.parent = D_0

native D_1 read/projection:
  child visible
  inherited expected D_0 facts admitted

retry/recover:
  same D_1
  exactly 2 revisions total
  exactly 1 head
```

A repository-level assertion that the objects merely exist in raw `graph_payload` is insufficient. Projection/retrieval admissibility is the acceptance boundary.

### B. Historical producer compatibility regression

Run predecessor tests that prove the merged #658/#47 historical family still behaves correctly.

Do not duplicate that compatibility implementation in #651.

### C. Existing-world adoption regression

The Eldyrwild adopted-world cohort must remain green/baseline-equivalent.

Exact Buddy-A → D_A rewrite remains required.

### D. D.2A / D.2B governed-write regression

Threat and worldbuilding authority-port tests must remain green/baseline-equivalent.

### E. Fail-closed binder matrix

Prove:

* both receipts;
* adoption receipt without head;
* reviewed-init receipt without head;
* head without recognized genesis;
* provider integrity;
* provider unavailable;
* D₀ passthrough;
* exact legacy A→D_A rewrite.

### Required commands

Use the repository's configured PostgreSQL test DSN.

```bash
uv run pytest tests/test_cutover_native_genesis_continuity.py -q
```

The D.2C3 owning integration witness must execute and must not skip.

Then:

```bash
uv run pytest \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_dungeonmind_world_graph_authority.py \
  -q
```

Record exact pass/fail/skip counts. Any existing unrelated skips must be identified and compared with the exact base; they do not satisfy the owning D.2C3 witness.

Adoption:

```bash
uv run pytest tests/test_eldyrwild_existing_world_adoption_bundle_v2.py -q
```

Governed-write regressions:

```bash
uv run pytest \
  tests/test_cutover_threat_authority_port_integration.py \
  tests/test_cutover_worldbuilding_authority_port_integration.py \
  -q
```

Static quality:

```bash
uv run ruff check \
  apps/live_control_server/integrations/dungeonmind/world_graph_reads.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_writes.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_native_genesis_continuity.py
```

Patch/lease hygiene:

```bash
git diff --check

git diff --name-only \
  d94822f7681da440fdeea981662383980bfbcaf9...HEAD

git diff --stat \
  d94822f7681da440fdeea981662383980bfbcaf9...HEAD
```

Dependency immutability:

```bash
git diff --exit-code \
  d94822f7681da440fdeea981662383980bfbcaf9...HEAD \
  -- pyproject.toml uv.lock
```

Expected: no D.2C3 change.

Authority mirror proof:

```bash
cmp \
  Docs/Plans/PR-TRACKER-campaign-supergraph.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md

cmp \
  Docs/Roadmaps/ROADMAP-campaign-supergraph.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
```

### Verification provenance

The handback must distinguish:

```text
author-local
independently rerun local
CI
manual/dogfood
```

Do not call author-local commands independently verified.

### Baseline protocol

If a required non-owning regression fails/skips on base:

1. run the identical command on `d94822f7…`;
2. run it on the proposed head;
3. record whether the head adds failure or skip;
4. do not call the gate green;
5. require explicit operator waiver if it remains an acceptance gate.

The **owning D.2C3 PostgreSQL witness has no skip waiver**.

## §8 Nano-commit story

Do not collapse the old #651 history.

Add only the smallest new commits needed to resume the parked PR.

Preferred Cycle-4 story:

```text
1. re-anchor D.2C3 on merged provenance predecessor
   - integrate current main
   - preserve #658 provider/producer contract
   - preserve existing generalized two-genesis binder

2. prove corrected D_0 is natively admissible
   - replace Cycle-3 rejection expectations
   - prove obj_session22_vial + mystery_puddles projection
   - prove native search + exact-object retrieval

3. sync active CUTOVER authority for resumed D.2C3
   - #658 backward-looking DONE / merged facts
   - #651 DOING / Review Cycle 4 candidate
   - D.2C4 and D.3 remain false
```

If conflict resolution and behavior proof can truthfully be one atomic commit, two commits are acceptable. Do not manufacture commit count.

Do not submit a rebase-only head for formal review. Complete the owning witness and handback first; the distinct final implementation head becomes Review Cycle 4.

## §9 Required CODE → REVIEW handback

The handback must contain:

1. **Review Cycle 4** and exact #651 final head SHA.
2. Exact re-anchor base and whether merge/rebase was used.
3. Confirmation that #658 merge `d94822f7…` is incorporated.
4. Confirmation of DungeonMind pin `5ca5d688…`.
5. Prior Cycle-3 finding ledger with each finding marked:

   * preserved closed;
   * predecessor resolved;
   * reverified on this head.
6. Cumulative changed paths against §4.
7. Cycle-4-only commit list and purpose.
8. Exact corrected first-world topology:

   * world ID;
   * D₀;
   * reviewed-init receipt count;
   * adoption count;
   * head/revision counts.
9. Stored provenance result and proof no Buddy read-side rewriting occurred.
10. Binding:

    * genesis;
    * first revision;
    * head;
    * `legacy_buddy_revision_id=None`.
11. Admitted D₀ projection result for:

    * `obj_session22_vial`;
    * `mystery_puddles`.
12. Native search result.
13. Exact-object retrieval result.
14. `WorldGraphAuthority` D₀ current-head/read/mutation-context result.
15. D₁ publication:

    * exact D₁ ID;
    * parent D₀;
    * revision/head counts.
16. D₁ native read/projection.
17. Retry/recover result proving no duplicate.
18. Eldyrwild A→D_A regression result.
19. D.2A / D.2B regression result.
20. Fail-closed genesis topology results.
21. Every §7 command and exact pass/fail/skip count.
22. Provenance of each verification result.
23. `git diff --check` result.
24. dependency-diff result for `pyproject.toml` / `uv.lock`.
25. tracker/roadmap `cmp` results.
26. Baseline failures and comparisons; `none` if none.
27. Explicit operator waivers; `none` if none.
28. Paths outside §4; `none` or STOP.
29. Stop conditions encountered; `none` or exact report.
30. Confirmation that D.2C4/D.3 remain unimplemented.

The PR description is not a substitute for this handback.

## §10 Acceptance rubric

Review Cycle 4 is PASS-equivalent only when every item is true:

* [ ] #651 is reviewed on one exact distinct final head.
* [ ] The cumulative diff is evaluated against the current re-anchor base, not the original 2026-08-26 base.
* [ ] One shared `DirectAuthorityBinding` still supports exactly adoption and reviewed initialization.
* [ ] Reviewed-init binding has `legacy_buddy_revision_id=None`.
* [ ] Existing Buddy-A maps exactly to adopted D_A.
* [ ] Real DungeonMind `D_0` and descendants pass through unchanged.
* [ ] The fresh first-world owning witness uses the real corrected #658 producer.
* [ ] The stored D₀ is not rewritten by Buddy on read.
* [ ] `obj_session22_vial` is admitted by native projection.
* [ ] `mystery_puddles` is admitted by native projection.
* [ ] Native search reaches the corrected D₀ facts.
* [ ] Native exact-object retrieval reaches the corrected D₀ object.
* [ ] `WorldGraphAuthority` operates normally from D₀.
* [ ] D₀ is accepted as the parent of exactly one legal D₁.
* [ ] D₁ is natively readable/projectable.
* [ ] Exact retry/recovery returns the same D₁ without duplicate publication.
* [ ] Both-receipt, receipt-without-head, and head-without-genesis states fail closed as integrity.
* [ ] Provider integrity remains distinct from provider unavailable.
* [ ] Existing adoption behavior is green/baseline-equivalent.
* [ ] D.2A Threat and D.2B worldbuilding publication remain green/baseline-equivalent.
* [ ] No DungeonMind provider/repository contract is added.
* [ ] `pyproject.toml` and `uv.lock` are unchanged relative to the Cycle-4 base.
* [ ] No first-world producer logic is reimplemented in D.2C3.
* [ ] No Buddy-file fallback or read-side provenance normalization exists.
* [ ] No D.2C4 Graph Review authoring behavior is included.
* [ ] No D.3A/D.3B demolition behavior is included.
* [ ] Required PostgreSQL owning witness executes with zero required skips.
* [ ] `git diff --check` passes.
* [ ] Tracker and ACTIVE_AUTHORITY mirror are byte-identical.
* [ ] Roadmap and ACTIVE_AUTHORITY mirror are byte-identical.
* [ ] State docs truthfully say #658 is merged and D.2C3 is active, without pre-marking D.2C3 DONE.
* [ ] D.2C4 remains the named successor and remains false until #651 merges.

## §11 Stop conditions

STOP rather than expanding if:

* the merged #658 producer does not produce admissible first-world evidence through the real initialization path;
* satisfying admissibility requires any Buddy read-side evidence rewrite;
* a new DungeonMind command, schema, repository method, provider transaction, or compatibility waiver is required;
* the branch can only work by fabricating a Buddy revision for D₀;
* adoption semantics must change;
* a third genesis family appears;
* Graph Review authoring must change;
* legacy graph-engine routes/imports must be removed;
* a required production edit falls outside §4;
* `pyproject.toml` or `uv.lock` appears to require another pin movement;
* the owning real-PG witness cannot execute;
* another active PR acquires a conflicting §4 lease.

Report a stop as:

```text
Stop condition:
Invariant clause affected:
Observed evidence:
Why D.2C3 cannot absorb it:
Owning layer:
Required predecessor or split:
State-authority update required:
```

Do not weaken §7 or §10 to make a partial branch mergeable.

## §12 Post-merge transition

Do **not** perform this transition inside the implementation review.

After #651 receives PASS-equivalent and is explicitly merged:

1. record exact accepted head;
2. record exact #651 merge SHA;
3. record total formal review cycles = 4 unless another distinct reviewed head was required;
4. update CUTOVER tracker/roadmap/state authorities in a separate backward-looking sync;
5. mark D.2C3 `DONE`;
6. re-anchor current repo truth;
7. only then decompose and author D.2C4.

Expected sequence after merge:

```text
D.2C3 native genesis continuity   DONE
        ↓
D.2C4 Graph Review authoring      READY / next design+implementation slice
        ↓
D.3A mounted engine excision
        ↓
D.3B physical package deletion
        ↓
CUTOVER complete
```

The key change from the old #651 handoff is that **we no longer design around the provenance failure**. We treat it as a resolved predecessor and make Cycle 4 prove the original invariant without compromise. The most important acceptance assertion changes from:

`obj_session22_vial not in projection`

to:

`obj_session22_vial in admitted native projection`

with search and exact-object retrieval proving that this is actual DungeonMind admissibility rather than raw repository visibility.
