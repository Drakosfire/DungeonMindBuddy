---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER — v6 governed review publication
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-v6-governed-review-publication.md
  - Implementation repository: Drakosfire/DungeonMind

  ## Predecessor truth
  - DungeonMind PR #36 is the merged exact adopted-membership receipt V3 predecessor (merge `9a19584d31baea77f590d7726e508b144c7dd39d`, 2026-08-18; 3 review cycles).
  - Buddy PR #619 Review Cycle 1 (head `67c28aeeed0699c113f58bcd277c4df4f7ad57e2`, formal judgment recorded as review COMMENT `4962154125`) found the governed-write gap this slice repairs: the live switch attempt proved DungeonMind cannot yet commit a GM-confirmed child revision on a `dm_union_graph_v6` world.

  Add the missing governed write seam for v6 union-graph worlds: a
  `dm_contribution_review_intent_v2` contract family that carries the real
  `dm_graph_contribution_v2` confirmed-contribution shape, and v6-aware
  governed materialization, so the normal review→finalize→publish path can
  commit a child revision D_A→D_B on the adopted Eldyrwild world.
---

# HANDOFF — v6 governed review publication

**Created:** 2026-08-18
**Status:** DONE / HISTORICAL — DungeonMind PR #37 merged `2edc07ff27a21b1c83aed847edf95b77d297910e` (3 review cycles; final PASS review `4963853068`). The v2 finalize + v6 materialization + head CAS publication seam is delivered; this handoff remains as the historical dispatch contract. The active CUTOVER implementation is the Buddy-side authority completion per `HANDOFF-CUTOVER-dungeonmind-authority-completion.md`.
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-v6-governed-review-publication.md`
**Conversation/workstream:** `CUTOVER — whole-world authority transfer`
**Flow / owner:** `CUTOVER`
**Direction:** DESIGN → CODE → REVIEW
**Buddy design base:** `89923f1c` (Buddy `main` at dispatch)
**DungeonMind implementation base:** `9a19584d31baea77f590d7726e508b144c7dd39d` (post-#36 `main`)
**Suggested implementation branch:** `dnd/cutover-v6-governed-review-publication`
**Suggested implementation PR title:** `CUTOVER: v6 governed review publication`

> Repository authority beats this handoff. Re-anchor both repositories before dispatch and replace provisional facts with exact merged truth.
>
> This slice is the bounded DungeonMind repair named by `HANDOFF-CUTOVER-whole-world-authority-transfer.md` §7 (conditional DungeonMind repair rule) and demanded by Buddy PR #619 Review Cycle 1 Finding 1. It is deliberately scoped to the governed write seam only: review intent, materialization, and publication for `dm_union_graph_v6` worlds. It does not move product authority, does not change Buddy, and does not add read-path or catch-up capability.

## §1 Mission and merge-ready invariant

**Mission:** make DungeonMind's governed publication path capable of committing a real, GM-confirmed child revision on a `dm_union_graph_v6` world, carrying the confirmed contribution as a durable `dm_graph_contribution_v2` ledger entry, with the same governance invariants the v3 path already enforces (content-bound intent, explicit verdicts, identity disposition, capability gate, expected-parent CAS, idempotent replay).

**Merge-ready invariant:** against a test-PostgreSQL DungeonMind holding the sealed Eldyrwild adoption (V3 receipt, head D_A), an in-process caller can:

1. finalize a v2 contribution review whose candidate is a `GraphContributionV2` carrying Buddy-shaped kernel assertions (`node`, `edge`, `alias`, `attribute`, `evidence_ref` kinds with evidence provenance);
2. publish it through the existing finalized-review publication boundary;
3. obtain a new head revision D_B whose `parent_revision_id` is exactly D_A, whose `dm_union_graph_v6` payload reparses under the pinned semantic profile and contains the newly accepted objects/relationships with Buddy-convention identities, and whose contribution ledger durably contains the reviewed contribution;
4. replay the exact same submission idempotently (same operation id → same publication receipt, zero new rows);
5. observe a concurrent second review against the same parent lose the CAS exactly once and fail closed.

The v1/v3 path behavior is unchanged: every existing v1 review/materialization/publication test passes unmodified.

## §2 Why this slice exists

Buddy PR #619 (whole-world authority transfer) attempted the live authority switch against test PostgreSQL and proved two concrete DungeonMind gaps, now encoded as typed fail-closed errors in the Buddy adapter (`apps/live_control_server/integrations/dungeonmind_kernel/world_graph_authority.py`, Buddy head `67c28aeeed0699c113f58bcd277c4df4f7ad57e2`):

1. **`governed_write_inexpressible`** — `dm_contribution_review_intent_v1` admits only four assertion kinds (`label`, `alias`, `summary`, `relationship`), forbids `value` on `label`, and requires the candidate to be a `dm_graph_contribution_v1`. Buddy's confirmed contributions are `dm_graph_contribution_v2`-shaped: `node` assertions carrying `value.kind`/`value.aliases`, `edge` assertions carrying `value.edge_id` and endpoint bindings, `attribute` assertions, typed `assertion_corrections`, and per-assertion evidence provenance. A real GM-confirmed Eldyrwild contribution does not fit the v1 envelope.
2. **`governed_write_materialization_unsupported`** — `materialize_finalized_review` is hard-bound to `dm_union_graph_v3` parents (`review_materialization.py` validates `parent.payload.graph_schema == GRAPH_SCHEMA_V3`), and `publish_finalized_review` rejects any materialized `graph_schema != dm_union_graph_v3`. The adopted Eldyrwild world is `dm_union_graph_v6` (ADR-0018 assertion-scoped relationship endpoint aspects). There is no v6 incremental applier at all.

The whole-world handoff's §7 makes this repair the defined next step: the failing proof is the repair requirement. Buddy PR #619 cannot merge until this slice lands and Buddy is repinned to its merge.

## §3 Predecessor and sequencing truth

- DungeonMind PR #36 merged as `9a19584d31baea77f590d7726e508b144c7dd39d` (2026-08-18): exact adopted-membership receipt V3, including the public `existing_world_adoption_membership_sha256` helper and the sealed Eldyrwild fixture at `tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json` (bundle SHA-256 `90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f`, adopted DND revision `rev:34b1f8e2625d5ba693fc726a2a1a4720`).
- Buddy PR #619 is open at head `67c28aeeed0699c113f58bcd277c4df4f7ad57e2`, disposition CHANGES REQUIRED (Review Cycle 1, six findings). Finding 1 is this slice. Findings 2–6 are Buddy-side authority repairs that proceed on the Buddy branch in parallel and do not block this slice.
- The parked pinned-snapshot catch-up handoff remains parked; this slice does not unblock it.

Sequencing after this slice merges: Buddy repins `dungeonmind[postgres]` to the exact merge SHA, replaces the fail-closed write seam with a real `confirm_via_dungeonmind` implementation against the v2/v6 seam, and completes the §10 write evidence before PR #619 Review Cycle 2.

## §4 Contract: `dm_contribution_review_intent_v2` family

Create `src/dungeonmind/contracts/contribution_review_v2.py`. The v2 family mirrors the v1 family's governance shape but carries the durable v2 contribution contract. **No v1 contract is modified.**

New schemas (all strict Pydantic, `schema_version` literal-pinned):

```text
ContributionReviewIntentV2        "dm_contribution_review_intent_v2"
ContributionReviewRecordV2        "dm_contribution_review_record_v2"
ContributionReviewStateV2         "dm_contribution_review_state_v2"
ContributionReviewSubmissionV2    "dm_contribution_review_submission_v2"
CommitConfirmationReceiptV2       "dm_commit_confirmation_receipt_v2"
```

Field shape of `ContributionReviewIntentV2`:

```text
schema_version, operation_id, world_id, campaign_id,
plan_ref: ContributionPlanRef            (reused v1 model, unchanged)
candidate_contribution: GraphContributionV2
identity_proposals: list[ContributionIdentityProposal]   (reused v1 models)
identity_verdicts: list[ContributionIdentityVerdict]
assertion_verdicts: list[ContributionAssertionVerdict]
reviewer_id, reviewed_at, review_intent_sha256
```

Validation rules (v2 deltas from v1; all unmentioned v1 rules carry over verbatim, including operation-id format, digest recomputation binding, verdict/proposal pairing, and coverage exactness):

- `candidate_contribution` is a `GraphContributionV2`; `status` must be `active`; `source_kind` is unconstrained (Buddy's confirmed contributions are `graph_review`-sourced; the v1 `extraction`-only rule is an extraction-pipeline assumption, not a governance invariant).
- `unresolved_mentions` and `diagnostics` pass through candidate → reviewed unchanged. They are durable historical record in the ledger, not governance state. (Buddy's sealed packages may retain resolved-history mentions; the materializer ignores them.)
- Assertion kinds are the Buddy kernel vocabulary plus corrections: `node`, `edge`, `alias`, `attribute`, `evidence_ref`. Any other `assertion_kind` on an **accepted** assertion fails validation. (Rejected/candidate assertions may carry any kind; they are never materialized.)
- Identity proposals/verdicts cover exactly the distinct subject targets of accepted `node` and `alias` assertions, with the v1 consistency rules (verdict matches proposal; `create_new` requires exactly one accepted `node` assertion for the target; `confirm_existing` requires the target id).
- `plan_ref.base_graph_schema` must be `dm_union_graph_v6` for this seam. (A v3 world keeps using the v1 path.)
- `review_intent_sha256` recomputes over the same canonical material as v1 with the v2 schema string as domain separator.

`ContributionReviewStateV2` cross-integrity rules mirror v1: candidate stored `superseded`, reviewed `active`, reviewed `supersedes_contribution_id == candidate.contribution_id`, identical assertion id sequence, acceptance states match verdicts exactly, identity outcomes match verdicts, all other assertion fields byte-identical, reviewed `produced_at == reviewed_at`, reviewed `authored_by == reviewer_id`, reviewed `source_kind == candidate.source_kind`.

`CommitConfirmationReceiptV2` mirrors v1 with `tool_name` literal `dungeonmind.finalize_contribution_review_v2`.

Digest derivations: reuse the v1 `derive_review_id` / `derive_reviewed_contribution_id` / `derive_confirmation_id` helpers (they are schema-agnostic given the intent digest); add `derive_review_intent_sha256_v2` with the v2 domain separator.

## §5 v6 materialization semantics

Create `src/dungeonmind/application/review_materialization_v6.py`: a pure function

```text
materialize_finalized_review_v6(state_v2, *, parent, graph_reader)
    -> FinalizedReviewGraphMaterialization
```

with the same binding preflights as the v3 materializer (parent schema/digest/profile must match `plan_ref`; parent world must match), then applying the reviewed contribution's **accepted** assertions to the parent `UnionGraphV6Payload` in assertion list order, per this mapping (the exact continuation of the Eldyrwild adoption producer's conventions):

| assertion_kind | v6 materialization |
|---|---|
| `node` | `CREATE_NEW`: append `GraphObjectV6Record` — `object_id = subject_object_id`; `kind = value["dm_kind"]` (required, must be profile-qualified; the output reparse under the pinned profile validates it); `label = assertion.label or value["label"] or object_id`; existence `assertion_metadata` built from the assertion; aliases from `value["aliases"] or [label]` as `AliasAssertionV4Record`s with deterministic derived assertion ids; `properties=[]`, `aspects=[]`. `CONFIRM_EXISTING`: merge only — append missing aliases, extend existence evidence refs; never rewrite `kind`/`label`. |
| `edge` | append `GraphRelationshipV6Record` — `relationship_id = value["edge_id"] or f"edge:{subject}:{predicate}:{target}"` (Buddy's derivation, continuing the adopted world's id convention); `predicate = value["dm_predicate"]` (required, profile-qualified); source/target from assertion; both endpoint objects must exist in the resulting payload; `label = assertion.label or value["label"]`; no endpoint aspect ids. Exact duplicate relationship id with identical content → no-op; same id with different content → fail closed. |
| `alias` | append `AliasAssertionV4Record` to the existing target object (object must exist); alias text = `assertion.label or value["alias"]`; casefolded duplicate → no-op; assertion id is the contribution assertion id. |
| `attribute` | evidence-only: no object/relationship/property record. Mirrors Buddy's merge semantics (attribute assertions materialize provenance/support; the projection layer derives attributes) and the adopted v6 convention (`properties=[]` throughout). The assertion's evidence refs still land in the payload evidence ledger. |
| `evidence_ref` | evidence-only, same as `attribute`. |
| anything else | fail closed (`unsupported_assertion_kind`), including statblock/mechanics bindings (`uses_statblock` predicate or binding payloads in `value`) — mechanics authority is separately owned. |

Metadata construction for every created record (`KnowledgeAssertionMetadataV1`):

- `assertion_id` = the contribution assertion id (the reader enforces payload-wide uniqueness; duplicates fail closed);
- `campaign_scope` = assertion `campaign_scope` (nullable);
- `visibility` = assertion `visibility`; `epistemic_kind` = assertion `epistemic_kind`; `canon_state = canonical`;
- `evidence_ref_ids` = the assertion's evidence ref ids (see evidence rules below); never empty;
- `session_refs` = `value["session_ids"]` when present, else `[]`;
- `temporal_scope` = `unknown` when the assertion's `temporal_scope` is null/absent; `world_timeless`/`fictional_time_ref` map only when well-formed; anything else fails closed.

Evidence ledger rules:

- For each accepted assertion, every `evidence_refs` entry (`dm_evidence_ref_v1`) is lifted into a `GraphEvidenceRecordV2` payload record keyed by the same `evidence_ref_id`, with `source_domain_key = source_domain.value`, `session_id = None`, `source_span_ref_id = None`, `source_locator = None`, `line_ref = None`, and the remaining fields carried over. (v1 refs do not carry session/span; fabricating them is forbidden. This is a documented fidelity boundary for post-cutover evidence; the adopted-era records keep their rich v2 shape.)
- Same evidence id with identical content → dedup; same id with different content → fail closed (same rule as the v3 materializer and the adoption producer's identity-closure check).
- An accepted assertion with no `evidence_refs` but with source artifact/revision identity (permitted by the V2 model validator) synthesizes the Buddy fallback evidence id `evidence:{reviewed_contribution_id}:{graph_object_id}` (where `graph_object_id` is the object id for node/alias/attribute assertions and the relationship id for edge assertions) and a corresponding payload evidence record, so `evidence_ref_ids` is never empty and Buddy-side replay derives the identical fallback id.
- Evidence `source_artifact_id`/`source_revision_id` values are recorded as provenance exactly as supplied. Registering new Buddy source artifacts in DungeonMind's source authority is **not** part of this slice (see §8 boundaries).

Corrections (`assertion_corrections` on the reviewed contribution), applied after accepted assertions:

- Resolve `target_assertion_id` against the current payload: object existence/alias/summary/property/aspect records and relationship records carry `assertion_metadata.assertion_id`.
- Both `contradicts` and `contradicts_and_replaces` remove the targeted records; for `contradicts_and_replaces` the replacement is applied as a normal accepted assertion (it must appear in the accepted set).
- No record carrying the target id → fail closed (`correction_target_unresolvable`). Adopted-era records carry `ka:*` synthetic ids, so corrections targeting adopted-era assertions fail closed by construction — a documented boundary; correcting adopted-era knowledge is a future receipt-aware correction slice.
- Corrections targeting an object **existence** record fail closed (`correction_target_existence`): object removal is a retraction workflow, not a correction, and would orphan relationships.

Determinism and verification (same posture as the v3 materializer):

- parent payload order preserved; new objects appended sorted by `object_id`; new relationships sorted by `relationship_id`; new evidence sorted by id;
- output reparsed through `graph_reader` (v6, pinned profile) — this is where profile admissibility of `dm_kind`/`dm_predicate` is enforced;
- post-checks: every expected new object/relationship/evidence record present with expected content; corrected records absent;
- result carries `graph_schema = dm_union_graph_v6`, the canonical payload sha256, and the created id lists.

## §6 Finalize and publication wiring

- Create `src/dungeonmind/application/contribution_review_v2.py`: `finalize_contribution_review_v2(submission_v2, *, capability_policy, world_graph_repository, review_repository)`. Same gates as v1: capability policy (new tool name), head-CAS preflight (`plan_ref.expected_parent_revision_id` must equal current head), parent digest/schema/profile preflight, then build and persist the `ContributionReviewStateV2`.
- `application/review_publication.py`: dispatch materialization on the loaded state's schema — v1 state → existing v3 materializer; v2 state → v6 materializer. Replace the hard `graph_schema != GRAPH_SCHEMA_V3` rejection with `graph_schema != plan_ref.base_graph_schema` (v1 plans pin v3, so v1 behavior is byte-identical). The publication command/receipt contracts already carry `graph_schema` as data; no publication contract change.
- `application/review_materialization.py`: relax the `FinalizedReviewGraphMaterialization` result guard to accept `GRAPH_SCHEMA_V6` (the class is already schema-parameterized).
- `application/repositories.py`: widen `ContributionReviewRepository` to `finalize(state: ContributionReviewState | ContributionReviewStateV2)` and `get_for_review(...) -> ContributionReviewState | ContributionReviewStateV2 | None`.
- `infrastructure/postgres/records.py` + `infrastructure/memory/repositories.py`: reconstruct v1 or v2 state by dispatching on the stored `schema_version`. **No migration**: `contribution_reviews` already stores a versioned JSON payload with a `schema_version` column, and its candidate/reviewed foreign keys reference `graph_contributions`, which already stores `dm_graph_contribution_v2` records. The existing finalize path already appends both contributions to the ledger — that behavior is reused unchanged and is the durability proof for the reviewed contribution.
- Export the new public seam through `contracts/__init__.py` and `application/__init__.py` under established convention.
- ADR-0009's "only `dm_union_graph_v3` is materializable" claim is superseded by this slice: add a new ADR (next number) recording the v2/v6 governed publication decision and its boundaries; do not rewrite ADR-0009's history.

## §7 Verification

DungeonMind conventions: `uv run pytest tests/unit/...`, `uv run pytest tests/conformance/...`, and integration via `DUNGEONMIND_DATABASE_URL` (see `tests/integration/conftest.py`). Required:

1. New unit/conformance suites green: v2 contract validation (digest binding, coverage, identity consistency, lifecycle), v6 materializer per-kind mapping and every fail-closed case in §5, publication dispatch, in-memory full path.
2. New integration suite green against test PostgreSQL (§8 lease names the file): the §1 merge-ready invariant end to end on the sealed Eldyrwild fixture.
3. Full `uv run pytest tests/unit tests/conformance` green; full integration suite green; `ruff check` and `ruff format --check` clean on touched files; any inherited baseline failures reported base-vs-head, never rewritten as green.

## §8 Expected DungeonMind write lease

Finalize against exact post-#36 `main` before dispatch. Expected paths:

| Action | Path | Purpose |
|---|---|---|
| Create | `src/dungeonmind/contracts/contribution_review_v2.py` | v2 review contract family (§4) |
| Create | `src/dungeonmind/application/contribution_review_v2.py` | v2 finalize service (§6) |
| Create | `src/dungeonmind/application/review_materialization_v6.py` | v6 materializer (§5) |
| Modify | `src/dungeonmind/application/review_materialization.py` | Relax result-class schema guard to admit v6 |
| Modify | `src/dungeonmind/application/review_publication.py` | Schema-dispatched materialization; plan-bound schema check |
| Modify | `src/dungeonmind/application/repositories.py` | Widen review repository protocol to v1 \| v2 states |
| Modify | `src/dungeonmind/infrastructure/postgres/records.py` | v2 review-state reconstruction by schema dispatch |
| Modify | `src/dungeonmind/infrastructure/memory/repositories.py` | In-memory parity for v2 states |
| Modify | `src/dungeonmind/contracts/__init__.py`, `src/dungeonmind/application/__init__.py` | Public exports |
| Create | `tests/unit/test_contribution_review_v2.py` | v2 contract/finalize proofs |
| Create | `tests/conformance/test_review_materialization_v6.py` | v6 materializer mapping + fail-closed algebra (in-memory) |
| Create | `tests/integration/test_postgres_review_publication_v6.py` | Owning-boundary Eldyrwild D_A→D_B proof |
| Create | `Docs/Decisions/ADR-0020-v6-governed-review-publication.md` | Supersede ADR-0009's v3-only materialization claim |
| Reuse unchanged | `tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json` | Sealed adoption authority for the integration proof |

### Bounded discovery

- shared test helpers may be extended, not rewritten;
- **no migration is pre-authorized**: the review table's versioned JSON payload carries v2 states. If implementation proves a migration is actually required, STOP and re-brief;
- no HTTP/transport layer changes: Buddy integrates in-process; the service API surface is out of scope;
- no v1 contract file modifications; no adoption/correspondence changes; no catch-up; no read-path or product routing; no Buddy files;
- no source-authority registration writes for new evidence artifacts (recorded provenance only; see §5 evidence rules).

If post-#36 repository shape materially differs, stop and re-brief the exact path lease.

## §9 Adversarial evidence required

The implementation PR must prove all of these at the owning boundary (PostgreSQL integration unless noted):

|| Sequence | Required outcome |
|---|---|
|| adopt sealed Eldyrwild fixture (V3 receipt) → finalize v2 review (new node with `dm_kind`, new edge with `dm_predicate` + explicit `value.edge_id`, alias on adopted object, attribute) → publish | new head D_B; `parent_revision_id == D_A`; payload reparses under the pinned profile; new object/relationship present with Buddy-convention ids; reviewed `GraphContributionV2` durable in the ledger |
|| exact replay of the same submission (same `operation_id`) | same publication receipt; zero new revisions/contributions/reviews |
|| second distinct review against the same parent, raced | exactly one CAS winner; loser fails closed with the existing conflict taxonomy; head unchanged from the winner's D_B |
|| accepted assertion with unqualified/missing `dm_kind` or `dm_predicate` | materialization fails closed; zero mutation |
|| `edge` assertion whose endpoint object does not exist | fails closed; zero mutation |
|| duplicate relationship id with different content | fails closed; zero mutation |
|| correction targeting an adopted-era (`ka:*`) assertion id | fails closed (`correction_target_unresolvable`); zero mutation |
|| correction targeting an object existence record | fails closed (`correction_target_existence`); zero mutation |
|| accepted assertion of kind outside the §5 vocabulary (incl. statblock binding) | fails closed; zero mutation |
|| accepted assertion with source identity but no evidence refs | fallback `evidence:{reviewed}:{graph_object}` id synthesized; metadata evidence non-empty; payload evidence record present |
|| same evidence id with conflicting content across two assertions | fails closed |
|| wrong `expected_parent_revision_id` | preflight conflict; zero mutation |
|| tampered `review_intent_sha256` / verdict coverage gap | contract validation failure |
|| v1/v3 regression | every pre-existing v1 review/materialization/publication test passes unmodified (unit + conformance + integration) |
|| in-memory vs PostgreSQL parity | the same v2 finalize/publish sequence succeeds identically on both adapters |

The integration proof must print before/after head revision ids, parent linkage, ledger counts, and payload digests so the child publication cannot be mistaken for a no-op.

## §10 Error taxonomy

Reuse the existing taxonomy. New stable reasons under existing classes, expected at minimum:

- `unsupported_assertion_kind` (materialization; includes mechanics bindings)
- `correction_target_unresolvable`
- `correction_target_existence`
- `missing_qualified_kind` / `missing_qualified_predicate` (or equivalent narrowly named validation failures)

Do not add a new top-level error class unless implementation proves the existing taxonomy cannot truthfully express the failure and the steward re-briefs it first.

## §11 Authority and backward-looking Buddy sync

This handoff's landing commit on Buddy `main` is the dispatch record. When the DungeonMind repair PR actually merges, the successor Buddy work (PR #619 head advancement) records the exact merge SHA/review truth as its backward-looking predecessor sync and repins `dungeonmind[postgres]` to that merge. No standalone documentation PR.

## §12 Review handback

Return:

1. Review Cycle N and exact DND PR/head/base;
2. the v2 contract family's exact schemas and digest domain separators;
3. the v6 materializer mapping implementation path and its per-kind test vectors;
4. the Eldyrwild D_A→D_B integration proof: exact parent/child revision ids, payload digests, ledger counts, and the reviewed contribution id;
5. replay/idempotency and CAS-loser proofs;
6. every §9 fail-closed row with its test name;
7. full unit/conformance/integration/type/lint evidence with inherited failures compared base-vs-head;
8. actual changed paths versus the finalized §8 lease;
9. confirmation that no v1 contract changed, no migration was added, and the v1/v3 path is byte-identical in behavior;
10. confirmation that product authority remains Buddy / `CUTOVER_NOT_READY`.

## §13 Acceptance rubric

- [ ] `dm_contribution_review_intent_v2` family exists, carries `GraphContributionV2`, and binds all content by digest.
- [ ] v6 materializer applies the §5 mapping exactly and fails closed on every listed case.
- [ ] Publication dispatches v1→v3 and v2→v6 by state schema; v1 behavior unchanged.
- [ ] Reviewed contribution lands durably in the contribution ledger through the existing finalize append.
- [ ] Eldyrwild D_A→D_B proven in test PostgreSQL with parent linkage, digest, replay, and CAS evidence.
- [ ] No migration; no v1 contract mutation; no transport changes; no source-authority writes.
- [ ] ADR records the decision; ADR-0009 history preserved.
- [ ] Buddy remains product authority; disposition remains `CUTOVER_NOT_READY`.

## Stop conditions

Stop and report rather than expanding if:

- the v2 state cannot persist without a PostgreSQL migration despite the versioned JSON payload;
- v6 materialization cannot reproduce Buddy's relationship-id derivation (`value.edge_id` or `edge:{subject}:{predicate}:{target}`) without importing Buddy code;
- profile admissibility of `dm_kind`/`dm_predicate` cannot be enforced by the output reparse and instead requires new vocabulary machinery;
- honest publication requires registering new Buddy source artifacts in DungeonMind's source authority at write time (that would expand the slice; re-brief);
- the publication service's schema dispatch cannot keep v1 behavior byte-identical;
- corrections against adopted-era assertions turn out to be required for the first real mutation (they are explicitly out of scope here);
- any required path falls outside the finalized write lease.

The successor after this slice is the Buddy-side Finding 1 closure on PR #619: repin, real `confirm_via_dungeonmind` implementation, and the §10 write evidence (D_A→D_B, parent, frozen digests, retry, restart) before Review Cycle 2.
