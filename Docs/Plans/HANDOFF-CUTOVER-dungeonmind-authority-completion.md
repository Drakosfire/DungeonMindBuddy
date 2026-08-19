---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER — DungeonMind World Graph authority completion
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW → LIVE
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-dungeonmind-authority-completion.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Exact predecessor truth
  - Buddy `main` base: `6c2fe9d37dcecf34e025db8373fce072de30b62e` (merge of Buddy PR #619).
  - Buddy PR #619 merged from head `67c28aeeed0699c113f58bcd277c4df4f7ad57e2` after Review Cycle 1 had recorded `CHANGES REQUIRED` (formal review `4962154125`). Treat the merged adapter as forward-fix state, not as accepted CUTOVER completion.
  - DungeonMind PR #37 merged as `2edc07ff27a21b1c83aed847edf95b77d297910e` after Review Cycle 3 PASS (formal review `4963853068`). It supplies the v2/v6 governed review→publish seam the Buddy adapter was missing.

  Complete the already-merged Buddy authority adapter so `dungeonmind` mode is
  bound to the exact published DungeonMind revision lineage for reads and
  governed writes, exposes DungeonMind revision identity publicly, keeps the
  frozen Buddy store immutable, and is merge-ready for the immediate live
  D_A→D_B cutover attempt required by the parent whole-world handoff.
---

# HANDOFF — DungeonMind World Graph authority completion

**Created:** 2026-08-18  
**Status:** DONE — Buddy PR #620 merged; live cutover executed under the parent handoff  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-dungeonmind-authority-completion.md`  
**Conversation/workstream:** `CUTOVER — whole-world authority transfer`  
**Flow / owner:** `CUTOVER`  
**Direction:** DESIGN → CODE → REVIEW → LIVE  
**Buddy implementation base:** `6c2fe9d37dcecf34e025db8373fce072de30b62e`  
**DungeonMind exact target pin:** `2edc07ff27a21b1c83aed847edf95b77d297910e` (merge of DungeonMind PR #37)  
**Implementation PR:** Buddy #620 — `CUTOVER: complete DungeonMind World Graph authority`  
**Merge:** `18bcb18475ac30679ebec84bec17c4e81390f674`  
**Review cycles:** 4 (final PASS review `4966969478` on head `8b9e5e8a68b8a5b766c7684234807c3df4944141`)  
**Parent authority:** `Docs/Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md`  
**Suggested branch:** `cutover/dungeonmind-world-graph-authority-completion`  
**Suggested PR title:** `CUTOVER: complete DungeonMind World Graph authority`

> **Dispatch ruling:** do not reopen readiness or migration design. Buddy PR #619 already merged the authority adapter, quiescence guard, service routing seam, and test harness. DungeonMind PR #37 now supplies the missing governed v6 writer. This slice is the bounded forward repair that makes the merged adapter satisfy the parent handoff's §10 merge-ready evidence before the steward performs the real live cutover.
>
> The first real live DungeonMind-owned child revision is still a post-merge steward operation under the parent handoff. This PR must prove the exact behavior against test PostgreSQL; it must not invent a fake campaign mutation or pre-mark CUTOVER complete.

---

## §1 Mission and merge-ready invariant

**Mission:** make Buddy's selected `dungeonmind` World Graph authority behave as one exact published DungeonMind revision lineage across active product reads and the normal GM-confirmed publication path, while the Buddy file-backed World Graph remains frozen and non-authoritative.

**Merge-ready invariant:** when `DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`, every active Buddy World Graph read or confirmed publication must be bound to an exact DungeonMind published revision and its ancestry; product-visible revision identity is DungeonMind identity; the exact legacy Buddy A pin resolves only through the adoption receipt to D_A; unpublished/finalized-only ledger rows never enter a served graph; derivative cache state never chooses authority; local Buddy World Graph mutation remains fail-closed; and a normal confirmed Buddy publication can commit exactly one D_A→D_B child in test PostgreSQL, survive cold reload, and replay without a second durable mutation.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Reads, exact pins, cache hydration, and writes all ask the same authority question: which exact published DungeonMind revision is being represented, and can any competing Buddy history advance? |
| Most likely adversarial falsification | Finalize two reviews against D_A → publish one as D_B → leave the loser durable but unpublished → clear derivative cache / restart → issue an unpinned read, a D_B exact-pin read, a legacy A read, and an explicit-root Hermes/Threat read. Any replay of the loser, Buddy revision leakage, cache dependence, or local fallback breaks the invariant. |
| Does §7 detect it? | **Yes.** The evidence ledger requires the real two-review CAS-loser state, published-head-bound cold hydration, public DND revision round-trip, legacy A cold bridge, mounted explicit-root callers, and frozen local digests. |
| Easiest owning boundary to under-test | Product-visible revision normalization after the Buddy kernel reads the derivative cache; helper-level hydration tests can pass while the surface still emits the private cache revision. |
| Fact that forces stop/split | A currently required product behavior depends on semantic World Graph information that is absent from the exact DungeonMind published revision and cannot be recovered through existing public DungeonMind authority without changing the locked authority model. |

---

## §2 Context, authority, and boundaries

### Locked predecessor truth

1. **Buddy PR #619 merged** at `6c2fe9d37dcecf34e025db8373fce072de30b62e` from head `67c28aeeed0699c113f58bcd277c4df4f7ad57e2`. Its Review Cycle 1 formal judgment was `CHANGES REQUIRED`, review `4962154125`. Because it merged anyway, those findings are now forward-fix obligations on `main`; do not revert the adapter as a substitute for finishing it.
2. **DungeonMind PR #37 merged** at `2edc07ff27a21b1c83aed847edf95b77d297910e` after Review Cycle 3 PASS, review `4963853068`. The exact merged seam includes `dm_contribution_review_intent_v2`, `finalize_contribution_review_v2`, v6 materialization, publication dispatch, D_A→D_B PostgreSQL proof, exact replay, and one-winner CAS behavior.
3. Exact adopted Eldyrwild authority remains:

```text
world_id: eldyrwild
legacy Buddy A: rev:0c644e56b45bcaac709012206e3e41c2
DungeonMind D_A: rev:34b1f8e2625d5ba693fc726a2a1a4720
V3 adopted-membership sha256:
  538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890
sealed bundle sha256:
  90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f
```

### Known merged #619 defects this slice owns

The cumulative implementation must close all of these together because each violates the same authority invariant:

1. Buddy still pins DungeonMind #36 instead of merged #37.
2. `route_service_read()` treats every explicit root as an authority bypass; mounted production Hermes/Threat callers pass the configured Buddy root explicitly and can therefore keep reading frozen A after DungeonMind advances.
3. The derivative Buddy hydration revision leaks as public `revision_id` / `head_revision_id`; a caller cannot reliably self-repin to the returned revision. New authoritative revisions must expose DungeonMind identity.
4. The exact legacy A→D_A bridge depends on a retained D_A derivative cache after DungeonMind advances; a cold cache after D_B can lose the historical A reference.
5. Hydration replays all active post-adoption contributions and only subset-checks the v6 snapshot. A finalized-but-unpublished CAS loser can therefore appear in Buddy even though it is not in the DungeonMind head. The same hydration path does not fail closed on exact adopted V3 membership loss/tamper.
6. Registering an overlapping cache root can exempt the old Buddy authority tree from the low mutation guard.
7. `confirm_via_dungeonmind()` is intentionally hard-coded to the pre-#37 v1/v3 failure. It must now translate the normal Buddy confirmation into the merged v2/v6 governed finalize→publish seam.

### Parent / repository authority

Read these before editing, in order:

1. `AGENTS.md`
2. `Docs/Plans/STEWARDS-ANCHOR-cutover.md`
3. `Docs/Plans/HANDOFF-CUTOVER-whole-world-authority-transfer.md`
4. this handoff
5. `Docs/Plans/HANDOFF-CUTOVER-v6-governed-review-publication.md`
6. DungeonMind `Docs/Decisions/ADR-0020-v6-governed-review-publication.md` at `2edc07ff...`
7. current Buddy authority adapter / owning tests

If current `main` differs from the bases above, re-anchor first. Repository truth beats this dispatch.

### Named successor

After this PR is merge-ready and merged, the steward immediately resumes the parent handoff's live checklist: final V3 correspondence, switch active reads, exercise mounted product reads, perform one genuine GM-approved D_A→D_B publication, reload, verify frozen Buddy digests, then declare the point of no return.

### Explicit non-goals

- no synthetic pinned-snapshot catch-up unless the real final correspondence check returns `STALE`;
- no dual-write period;
- no HTTP service around DungeonMind merely for layering;
- no generalized migration/cross-world framework;
- no port of dormant repair/maintenance writers that are not exercised by the normal product path;
- no deletion of frozen Buddy A;
- no UI redesign;
- no DungeonMind schema/contract change unless a **new** concrete public-seam failure is proved despite merged #37;
- no support for arbitrary historical Buddy revisions other than exact adopted A;
- no CUTOVER completion claim before the real live D_B operation.

---

## §3 Observable-path and adversarial-sequence inventory

| Observable path | Current merged behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Unpinned projection/retrieval | Rootless calls hydrate current DND head, but surface cache revision identity | Serve current published DND head; response revision/head ids are DND ids | authority adapter + projection/retrieval service |
| Product call passes configured `world_graph_root()` explicitly | Bypasses authority router and may read Buddy A | Configured production root is **not** an authority override in `dungeonmind` mode; route to DND | shared service router / exact mounted caller |
| Deliberate non-production explicit test/tool root | Bypasses routing | May remain isolated only when it is genuinely a different non-production root; must not make configured production root bypassable | shared service router |
| Incoming exact D_A / D_B pin | Only legacy A map exists; private cache ids are expected | Exact DND revision id loads that exact published revision; returned identity is the same DND revision | authority adapter |
| Incoming exact legacy Buddy A pin | Works only while D_A cache exists | Receipt-bound A→D_A mapping survives cold cache and later DND heads | authority adapter + adoption receipt |
| Unknown legacy Buddy revision | Fails | Continue fail-closed; no latest/shape guessing | authority adapter |
| Hydration after a CAS-losing finalized review exists | Replays all active contributions, including unpublished loser | Build from exact selected published DND revision ancestry only; unpublished reviewed rows excluded | authority adapter + DND public repositories |
| Adopted history tampered/missing | Weak subset snapshot gate may still serve | Exact adopted V3 membership proof fails closed before serving | authority adapter |
| Cache root overlaps local authority storage | Guard exemption can cover authoritative files | Reject unsafe overlap before registration/hydration; no exemption is installed | adapter/config + storage guard |
| Normal Graph Review confirm | Typed pre-#37 failure | Verify sealed Buddy package against exact DND parent, finalize v2 review, publish v6 child, return DND D_B | extract-promote service + authority adapter + DND public seam |
| DND write fails/stale/unavailable | No local fallback today | Remain fail-closed; Buddy local graph never mutates | write router + low mutation guard |
| Exact confirm retry | No successful path | Same logical confirmation returns same durable DND publication/no duplicate | DND review/publication + Buddy mapping |
| Fresh process / cold derivative cache | Existing test retains on-disk cache | Reconstruct selected DND revision from durable authority alone; cache is expendable | authority adapter |

### Required adversarial sequences

| Sequence | Safe outcome | Owning proof |
|---|---|---|
| D_A → finalize R1 and R2 → publish R1=D_B → R2 loses CAS → delete derivative cache → hydrate D_B | Buddy shows only D_B published meaning; R2 contribution does not appear | PostgreSQL integration |
| Unpinned read returns D_B → caller immediately sends `revision_pin=D_B` | Exact same D_B content and public revision id | projection + retrieval integration |
| D_B exists → delete D_A and D_B cache dirs → request legacy A | Exact D_A reconstructed/served through receipt binding; no retained derivative cache required | cold-cache integration |
| `dungeonmind` mode + mounted Hermes/Threat caller passes configured production root | DND authority is still used; no frozen-A read | mounted caller regression |
| configure cache root equal/ancestor/overlap of local World Graph storage → enable DND mode | Typed configuration/integrity failure before cache registration; local mutation remains blocked | guard test |
| DND unavailable after authority selection | Visible authority error; zero current Buddy fallback | service integration |
| Normal confirmed package D_A→D_B → retry same confirm | one child revision/publication only; same committed DND revision returned | PostgreSQL write integration |

---

## §4 Files in scope — write lease

### Core implementation allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `pyproject.toml` | repin exact DungeonMind #37 merge |
| Modify | `uv.lock` | lock exact #37 merge and dependencies |
| Modify | `apps/live_control_server/config.py` | authority/cache configuration validation only if required by the final seam |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py` | published-revision selection, public revision mapping, cold A bridge, V3 integrity, safe cache registration, v2/v6 governed write |
| Modify | `apps/live_control_server/services/world_graph_projection.py` | normalize public DND revision identity and preserve authority routing |
| Modify | `apps/live_control_server/services/world_graph_retrieval.py` | normalize public DND revision identity and preserve authority routing |
| Modify | `apps/live_control_server/services/extract_promote.py` | normal product confirm must return the DND publication result without local fallback |
| Modify | `src/graph_memory/world_supergraph/storage.py` | cache-exemption safety only if the invariant belongs at this owning guard boundary |
| Modify | `tests/test_cutover_dungeonmind_world_graph_authority.py` | owning authority/pin/hydration/quiescence/write proof |
| Modify | `tests/test_live_extract_promote_api.py` | product confirm D_A→D_B/retry/error envelope proof if this remains the owning API test |
| Modify | `tests/test_live_query_hermes_graph.py` | mounted Hermes authority-routing regression if needed |
| Modify | `tests/test_live_control_server.py` | mounted live-agent authority-routing regression if needed |

### Known production caller allowlist

These paths are already proven current explicit-root risks and may be modified **only if the shared router cannot close the bypass without changing their product contract**:

```text
apps/live_control_server/services/live_agent_loop.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/routes/threat_query_hydration.py
apps/live_control_server/routes/threat_publication_identity.py
apps/live_control_server/routes/threat_publication_commits.py
apps/live_control_server/routes/threat_publication_proposals.py
```

Prefer one shared authority fix over six caller rewrites. Listing a path is authorization, not a requirement to churn it.

### Bounded discovery exception

If static call-path inspection finds another **mounted production** caller that passes the configured Buddy World Graph root directly into a read/write seam and therefore still bypasses DungeonMind authority:

```text
Directories:
  apps/live_control_server/services/
  apps/live_control_server/routes/
Maximum additional production paths: 4 total
Allowed path kinds:
  existing Python service/route modules only
Decision rule:
  include only when a mounted route/service call path proves the configured
  production root would bypass the shared DungeonMind authority boundary.
```

Owning tests for those exact added callers may expand under `tests/` by at most 4 additional existing test files. Record every expansion and call-path evidence in the PR handback. No scripts, UI files, or generic refactors are authorized by this exception.

### Atomic predecessor state-authority sync in this implementation PR

These facts are already true at dispatch and travel with the consuming implementation PR:

| Action | Path | Required backward-looking sync |
|---|---|---|
| Modify | `Docs/Plans/STEWARDS-ANCHOR-cutover.md` | DND authority anchor becomes #37 merge; active implementation handoff becomes this handoff; #619 is merged forward-fix predecessor |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | record #619 merged/incomplete predecessor, #37 DONE, authority-completion slice DOING |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` | same current ownership truth; do not claim live cutover complete |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | #37 DONE; this completion repair is current; pinned catch-up remains DEFERRED |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-v6-governed-review-publication.md` | mark DONE/HISTORICAL with exact #37 merge, 3 review cycles, final PASS review `4963853068` |

Do **not** pre-mark this handoff DONE or invent its future PR number/merge SHA/review count.

---

## §5 Files and capabilities explicitly out of scope

| Path/layer/capability | Why |
|---|---|
| DungeonMind repository | #37 is merged and sufficient unless this implementation proves a new concrete public-seam failure |
| `graph_data/**` | frozen A/source truth must not mutate during this repair |
| UI surfaces | authority completion is backend/runtime behavior; no new product surface is required |
| dormant maintenance scripts | parent handoff explicitly permits them to remain fail-closed |
| pinned-snapshot catch-up | activates only on observed `STALE` during the real final correspondence check |
| generalized historical revision bridge | only exact adopted A and DND revision identities are required |
| Buddy→DND dual write | prohibited by parent authority model |
| deletion/demolition of frozen Buddy store | post-live-success cleanup, not this pre-live repair |

---

## §6 Implementation contract and matrices

### A. Exact revision authority contract

```text
Input:
  world_id + optional revision_pin + selected authority mode

DungeonMind mode selection:
  no pin        -> current published DND head
  DND pin       -> that exact published DND revision
  legacy A pin  -> D_A only, proven by adoption receipt/source_provenance
  other Buddy pin -> fail closed revision_not_bridged

Output:
  Buddy product payload shape, but all product-visible revision/head identity
  names the selected/current DungeonMind revision, never the derivative Buddy
  cache revision.

Internal cache:
  may use private Buddy content-addressed revision ids for kernel compatibility;
  those ids are implementation detail and must never become the public authority
  identity or an accepted external revision pin.
```

### B. Published-head-bound hydration contract

Hydration must represent **the exact selected published DungeonMind revision**, not "all currently active durable contributions."

Required behavior:

1. prove the exact adopted A membership represented by receipt V3 is intact using the sealed adoption membership and the merged DungeonMind public membership contract/helper;
2. derive post-adoption material only from the exact selected DungeonMind revision ancestry/publication history;
3. exclude finalized/reviewed contributions that have no publication in that selected ancestry, including a CAS loser;
4. require the selected revision payload/digest/profile to validate under DungeonMind's public snapshot reader;
5. build or reuse a derivative Buddy cache keyed by the selected DND revision;
6. verify the derivative is consistent with that exact published revision strongly enough to catch missing/tampered authority material; a loose "snapshot ids are a subset of a replay of all active ledger rows" is not sufficient.

The implementation may use public revision `operation_ids`, finalized-review/publication repositories, and other merged DungeonMind public contracts to prove ancestry. It must not query DungeonMind tables with Buddy-authored SQL.

### C. Adopted V3 membership integrity matrix

| Condition | Required result |
|---|---|
| exact adopted records/fingerprints intact | serve selected DND revision |
| adopted record missing | fail closed `hydration_integrity` (or narrower typed equivalent) |
| adopted record same id / changed content | fail closed |
| legitimate published post-adoption rows exist | allowed; they are not part of the frozen A membership checksum |
| durable finalized-but-unpublished review exists | allowed in DND history but excluded from selected graph hydration |

### D. Explicit-root routing matrix

| Root passed by caller | `buddy_files` | `quiesced` | `dungeonmind` |
|---|---|---|---|
| no explicit root | local | local read | DND |
| explicit root == configured production `world_graph_root()` | local | local read | **DND; not an override** |
| deliberately different test/tool root | explicit root | explicit root read with local writes still governed by test env | may remain isolated test/tool behavior only if no mounted production path can use it as fallback |

No caller may regain current Buddy A merely by passing the server's configured production root explicitly.

### E. Cache-root safety contract

Before registering a derivative cache exemption, prove the cache root does not collide with the file-backed authoritative World Graph storage tree. Unsafe equality/ancestor/descendant overlap with the target local world storage must fail before registration. The normal sibling layout (`out/cache/...` versus `out/graph_memory/...`) remains valid.

A failed cache configuration must not weaken `assert_local_world_graph_mutation_allowed` for the old authority tree.

### F. Governed write mapping contract

The normal existing Buddy confirmation remains the user/GM action. The adapter translates that already-confirmed sealed package into DungeonMind's merged v2/v6 governed contracts; it does not add a second product confirmation step and does not bypass DungeonMind governance.

Required sequence:

```text
1. resolve selected DND parent revision and exact derivative read context
2. verify the sealed Buddy review package against that exact parent content
3. translate the confirmed contribution into GraphContributionV2 without
   dropping assertion/evidence/campaign/temporal/correction meaning
4. construct ContributionReviewIntentV2 + assertion/identity verdicts +
   CommitConfirmationReceiptV2 under a GM-scoped capability policy pinned to
   the exact DND parent
5. finalize_contribution_review_v2
6. publish_finalized_review
7. return the existing Buddy confirm response shape with:
     parent_revision_id   = DND parent
     committed_revision_id = published DND child
     durable success derived from DungeonMind publication receipt/revision
8. never mutate the Buddy file-backed graph/contribution/identity stores
```

Use the existing Buddy→DungeonMind v2 mapping semantics from the sealed adoption producer as the grounding vocabulary. Do not invent a second incompatible assertion translation.

#### Stable retry identity

The DND review operation/intent/confirmation mapping must be stable for the same sealed Buddy package + selected assertion set. Do not use a new random operation id or a fresh wall-clock timestamp on every retry if that changes the DND review identity.

Prefer already-sealed deterministic package/contribution fields. If the current Buddy package contains no stable fact that can honestly populate the required DungeonMind review timestamp/identity without adding a new durable mapping contract, **stop and report that exact contract gap** rather than smuggling in process-local idempotency.

### G. Write failure / rollback matrix

| Failure point | Required state |
|---|---|
| package verification fails | no DND review/publication; no Buddy mutation |
| DND finalize validation/capability fails | no publication/head advance; no Buddy mutation |
| stale parent / CAS loser | DND head unchanged by loser; reviewed history may remain durable per DND contract; Buddy hydration must still exclude it |
| publish succeeds | DND child is authority; Buddy response names DND child |
| response/audit problem after publish | report truthful published DND revision; do not retry through Buddy local writer |
| exact retry after success | same DND publication/no duplicate |
| DND unavailable | visible failure; no current Buddy fallback |

---

## §7 Evidence required to merge

Every row is merge-blocking unless explicitly marked inherited baseline.

| Guarantee | Owning boundary | Required proof | Expected evidence / stop condition |
|---|---|---|---|
| Exact dependency | packaging | lock inspection/test | exact `2edc07ff27a21b1c83aed847edf95b77d297910e`; any branch/latest/#36 pin blocks merge |
| Exact adopted membership | authority adapter + test PostgreSQL | tamper/delete one adopted member and rerun hydration | intact A serves; tamper/missing fails closed; post-adoption published rows do not falsely invalidate A checksum |
| Published-head-bound hydration | authority adapter + DND PostgreSQL | finalize two reviews, publish one, force the other CAS loser, cold-hydrate winner | loser meaning absent from Buddy projection/retrieval |
| Public DND revision identity | projection + retrieval service | unpinned D_B read followed by exact `revision_pin=D_B` | response `revision_id/head_revision_id` are DND ids; self-pin returns same exact state |
| Legacy A cold bridge | authority adapter | D_B exists; delete derivative cache(s); request legacy A | reconstruct/serve exact D_A through receipt; no retained D_A cache dependency |
| Unknown revision fails closed | service | arbitrary non-adopted Buddy rev | `revision_not_bridged`; no latest fallback |
| Mounted explicit-root callers | shared router + mounted service/route tests | exercise Hermes and at least one Threat path using configured production root in DND mode | DND-backed result; frozen A not selected |
| No silent fallback | service | make DND repository unavailable/integrity-invalid | visible typed failure; no Buddy current-head read |
| Cache-root overlap safety | config/adapter + storage guard | configure cache over local graph tree, then attempt local mutation | unsafe cache rejected before exemption; local mutation still raises quiescence error |
| Governed D_A→D_B write | normal extract-promote confirm + DND PostgreSQL | use real sealed Buddy review-package shape against disposable target | one v6 DND child, exact parent D_A, DND head advanced, Buddy confirm receipt names D_B |
| Buddy local store unchanged | low file stores | digest frozen local head/revisions/contributions/identity before and after DND write | byte/tree digests unchanged |
| Exact retry | product confirm + DND publication repository | repeat exact same confirmation | same D_B / `already_applied`-equivalent truthful result; zero second revision/review/publication mutation beyond DND's exact replay semantics |
| Cold reload | fresh adapter/process boundary | discard in-memory state and derivative cache, re-read D_B | durable DND state reconstructs same product meaning and revision identity |
| V1/v3/DungeonMind consumers unaffected | regression | repository focused suites | no new failures caused by #37 repin or adapter changes |
| Write lease | git diff | `git diff --name-only <base>...HEAD` | only §4 paths / recorded bounded expansions |

### Minimum verification commands

Use repository-native tooling, but the handback must include exact results for at least:

```bash
uv sync
uv run pytest tests/test_cutover_dungeonmind_world_graph_authority.py
uv run pytest tests/test_live_extract_promote_api.py
uv run pytest tests/test_live_query_hermes_graph.py tests/test_live_control_server.py
# plus exact owning tests for any bounded caller expansion
# plus the env-gated PostgreSQL cutover integration cohort proving D_A→D_B,
# CAS loser exclusion, cold cache, retry, and frozen Buddy digests
uv run ruff check <changed Python paths>
uv run ruff format --check <changed Python paths>
git diff --check
git diff --name-only 6c2fe9d37dcecf34e025db8373fce072de30b62e...HEAD
```

If a required command fails on base, follow `AGENTS.md` baseline protocol: compare base/head, record inheritance, and do not call the gate green without the required waiver.

### Minimal live/dogfood proof

**Not part of this PR before merge.** The parent handoff owns the real live cutover immediately after merge. This PR's realistic proof is the exact sealed Buddy review-package path against designated/disposable test PostgreSQL. Do not create fake campaign canon as a pre-merge canary.

---

## §8 Suggested nano-commit story

A useful sequence, if implementation naturally supports it:

1. **Repin + predecessor sync** — exact DungeonMind #37 merge and backward-looking state authority.
2. **Published-revision hydration** — ancestry-bound contribution selection, exact V3 adopted membership, cold historical A bridge, cache safety.
3. **Public revision/routing repair** — DND identity normalization and mounted explicit-root closure.
4. **Governed writer** — Buddy package → DND v2 review/finalize/publish, no local fallback.
5. **Owning proofs** — CAS loser exclusion, D_A→D_B, retry, cold restart, frozen local digests.

Do not force this exact commit count; preserve one discrete fix/proof story per nano commit and avoid unrelated cleanup.

---

## §9 Required review handback

Every formal review cycle must be able to answer, without reconstructing chat history:

```text
PR / branch / exact head SHA:
Buddy base:
DungeonMind exact pin:
review cycle number for this distinct head:

Mission + merge-ready invariant:
actual changed paths vs §4:
bounded expansions + call-path evidence:
nano commits:

#619 predecessor:
  merge 6c2fe9d37dcecf34e025db8373fce072de30b62e
  implementation head 67c28aeeed0699c113f58bcd277c4df4f7ad57e2
  prior formal review 4962154125 / CHANGES REQUIRED

#37 predecessor:
  merge 2edc07ff27a21b1c83aed847edf95b77d297910e
  implementation head 6dab6b3b588201fc77b4f2fa12ed1e3b74615d19
  3 review cycles
  final formal PASS review 4963853068

Target PostgreSQL setup:
A receipt schema / membership sha256:
D_A:
selected test D_B:
parent(D_B):

Published-head-bound CAS-loser proof:
public DND revision self-pin proof:
legacy A cold-cache proof:
mounted explicit-root Hermes/Threat proof:
V3 tamper/missing-member proof:
cache-overlap guard proof:
no-fallback proof:

governed Buddy confirm D_A→D_B proof:
Buddy frozen local digests before/after:
retry/replay proof:
cold process/cache reload proof:

State-authority predecessor sync completed:
baseline failures / waivers:
stop conditions encountered:

Disposition:
  MERGE-READY FOR IMMEDIATE LIVE CUTOVER ATTEMPT
  or
  CHANGES REQUIRED — <exact reproducible invariant failure>
```

Because the PR is authored on the same GitHub account, formal PASS/CHANGES REQUIRED may need to be recorded as review `COMMENT` rather than APPROVE/REQUEST_CHANGES. The exact head SHA and explicit disposition are what count as the review cycle.

---

## §10 Acceptance rubric

The reviewer passes the PR only when all are true:

- [ ] Exact DungeonMind dependency is `2edc07ff27a21b1c83aed847edf95b77d297910e`.
- [ ] Hydration is selected-published-revision-bound; active/finalized-but-unpublished rows cannot appear.
- [ ] Exact adopted V3 membership is verified fail-closed before serving.
- [ ] Product-visible revision ids are DungeonMind ids; private Buddy cache revision ids never escape as authority identity.
- [ ] A returned DND revision can be sent back as an exact revision pin and opens the same state.
- [ ] Legacy Buddy A opens exact D_A after D_B on a cold derivative cache.
- [ ] The configured production `world_graph_root()` cannot bypass DND authority merely because a caller passes it explicitly.
- [ ] Mounted Hermes and Threat graph reads are proved DND-backed in `dungeonmind` mode.
- [ ] Unsafe cache-root overlap cannot weaken the local mutation guard.
- [ ] Normal existing GM-confirmed Graph Review publication commits one DND v6 child revision through #37's governed contracts.
- [ ] The DND write path never mutates Buddy's frozen graph/contribution/identity stores.
- [ ] Exact retry does not duplicate the durable mutation.
- [ ] DND unavailable/integrity failures never silently fall back to current Buddy A.
- [ ] Cold reload reconstructs the DND-selected revision from durable authority, not retained process/cache state.
- [ ] No path outside the §4 lease changed without a recorded bounded expansion.
- [ ] Backward-looking state-authority sync records #619/#37 truth without pre-marking this slice or live CUTOVER complete.

The merge disposition is:

```text
MERGE-READY FOR IMMEDIATE LIVE CUTOVER ATTEMPT
```

not `CUTOVER_COMPLETE`.

---

## §11 Stop conditions

Stop and report rather than expanding if implementation proves any of these:

1. merged DungeonMind #37 still lacks a public contract needed to represent the normal Buddy confirmation without weakening explicit GM approval, expected-parent CAS, durable history, or replay;
2. exact selected-revision hydration cannot exclude unpublished review history using public DungeonMind authority and would require private SQL or a new durable cross-repo index;
3. a required current Buddy product read depends on semantic World Graph material absent from the selected DND revision and cannot be represented as a non-authoritative Buddy-owned source/mechanics concern;
4. stable write replay cannot be derived from the sealed Buddy package without inventing a second durable idempotency contract;
5. fixing a mounted caller requires a new product/transport contract rather than authority routing;
6. a path outside §4/bounded discovery is required;
7. the final pre-switch correspondence run performed **after this PR merges** returns actual `STALE`, `MISMATCH`, integrity failure, or unavailable state — those are parent-handoff runtime dispositions, not reasons to silently widen this code PR.

Report format:

```text
Stop condition:
Exact failing request/test:
Invariant clause affected:
Owning boundary:
Why current §4 cannot absorb it:
New public/durable contract required, if any:
Smallest proposed repair/successor:
Does this change the locked whole-world authority model? yes/no
```

---

## §12 After merge — no new design gate

When this PR merges with `MERGE-READY FOR IMMEDIATE LIVE CUTOVER ATTEMPT`, the steward returns directly to `HANDOFF-CUTOVER-whole-world-authority-transfer.md` §11:

```text
re-anchor Buddy main + exact DND pin
→ verify/adopt/promote target A and V3 membership
→ capture frozen Buddy digests and quiesce local writes
→ require final correspondence(A) == CORRESPONDING
→ enable DungeonMind reads
→ exercise Plan / Build-Recap-Hermes / mounted Play reads
→ verify exact legacy A bridge
→ choose one genuine GM-approved World Graph mutation
→ publish through the normal Buddy confirmation path
→ record live D_B + parent
→ reload server/browser and re-read
→ verify frozen Buddy digests unchanged
→ declare DungeonMind living authority / point of no return
```

If a concrete box fails, use the parent handoff's §7 repair loop. Do not author another generic readiness handoff.
