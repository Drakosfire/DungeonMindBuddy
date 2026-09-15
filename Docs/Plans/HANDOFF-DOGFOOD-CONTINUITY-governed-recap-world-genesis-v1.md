---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / governed full-corpus publication
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-governed-recap-world-genesis-v1.md`
  - Branch: `codex/governed-recap-world-genesis`

  ## Verification pointer
  - Predecessor: PR #716 merged as `d85a3787d05fdb0cbf4292f4f1411833f952166a`
  - Blocked successor: PR #715 full-corpus zero-model publication / notebook retirement
  - This PR must not consume or modify #715 branch artifacts.

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DOGFOOD-CONTINUITY: governed recap World genesis

**Created:** 2026-09-14  
**Re-anchored:** 2026-09-14 after PC identity-equivalence promotion  
**Status:** ACTIVE — ready for implementation dispatch  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-governed-recap-world-genesis-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / full-corpus automated World Graph ingestion`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Authority base:** `main@d85a3787d05fdb0cbf4292f4f1411833f952166a`  
**Implementation branch:** `codex/governed-recap-world-genesis` from current `main` containing this handoff  
**PR title:** `DOGFOOD-CONTINUITY: add governed recap World genesis`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §1 Mission and merge-ready invariant

**Mission:** An explicit operator/service action can initialize recap memory for a pristine DungeonMind World from the campaign's canonical party registry so that the ordinary existing-World publication path has a truthful source-backed parent revision.

**Merge-ready invariant:** For one pristine `(authority instance, world_id)`, confirm of one sealed recap-genesis plan atomically admits the exact canonical `party_registry` bytes and creates exactly one immutable zero-parent revision containing only the selected canonical PC identity anchors; prepare is inert, confirm rematerializes source authority, exact retry/lost-response recovery returns the same durable initialization, and stale/foreign/partial inputs fail closed without a second head, partial source state, worldbuilding provenance, or invented played-session claims.

### Locked causal order

```text
canonical campaign _party_registry.json bytes
  ↓
explicit prepare_recap_world_genesis
  ↓ inert sealed plan
explicit confirm_recap_world_genesis
  ↓ existing DungeonMind reviewed zero-parent transaction
D_0: canonical PC identities only
  ↓ native mutation-context read
ordinary existing-parent governed publication
  ↓
D_1 child of D_0
```

The first observed recap is **not** part of genesis. No special first-recap publication path may be introduced.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every changed path establishes or verifies one explicit pristine-World initialization from one exact registry baseline. |
| Most likely adversarial sequence | Prepare from registry digest A → bytes change to digest B → confirm trusts caller-carried plan A → stale identities/source enter `D_0`. Confirm must rematerialize B and reject before mutation. |
| Will §7 actually detect that failure? | Yes. A stale-source service test plus real-PostgreSQL pre/post state assertions own the failure boundary. |
| Easiest owning boundary to under-test | DungeonMind source/evidence mapping: `party_registry` must survive as source-domain key while the provider coarse enum is `OTHER`, and worldbuilding behavior must remain unchanged. |
| Fact that forces stop/split | The pinned DungeonMind reviewed initializer cannot atomically accept a `party_registry`/`standing_context` command without a provider schema/API change, or an ordinary child publication cannot consume the resulting native `D_0` without changing existing-parent semantics. |

## §2 Context, authority, and lane

| Field | Current authority |
|---|---|
| Parent design | Campaign Supergraph immutable-revision/atomic-head invariants plus the landed CUTOVER reviewed first-world authority. |
| Authority base | `main@d85a3787d05fdb0cbf4292f4f1411833f952166a`. The handoff commit is a descendant; implementation branches from current `main` after this handoff lands. |
| Predecessor contract | PR #716, `DOGFOOD-CONTINUITY: promote PC identity equivalence`, merged as `d85a3787d05fdb0cbf4292f4f1411833f952166a`. Review Cycle 1 = APPROVE (GitHub COMMENT due self-review); independent owning verification = 18 passed. `pc`, `player_character`, and `dnd5e:player_character` now compare compatibly while NPC collisions remain blocked. |
| Existing provider boundary | `WorldGraphInitializationAuthority` → `DungeonMindWorldGraphInitializationAdapter` → DungeonMind `ReviewedWorldInitializationCommandV1` / atomic reviewed initialization. |
| Existing source semantics | Buddy already recognizes `party_registry`; `CAMPAIGN_STABLE_SOURCE_DOMAINS` includes it; standing context already uses `artifact:party-registry:<campaign_id>`, exact `repo://.../_party_registry.json`, `source_kind=standing_context`, `source_domain=party_registry`. |
| Exact product input | `world_id`, `campaign_id`, `baseline_roster_key`, actor/principal; server resolves the canonical registry path and exact bytes. C1 acceptance uses `campaign_id=longmont-c1`, `baseline_roster_key="1"`. |
| Named successor | Post-merge #715 acceptance: independently initialize the two saved model-arm rehearsal authorities, replay sealed C1 S1→C2 S25 with zero model calls, preserve final evidence, extract any last production-worthy behavior into focused PRs, then retire #715 and older notebook PRs. |
| What remains false | Full-corpus publication, model-arm comparison, graph-query benchmark verdict, UI GO/HOLD, Sessions 26/27 corpus promotion, broader identity cleanup, ontology widening, Agent tuning, and notebook retirement. |
| Explicit non-goals | No routes/UI, no automatic world creation side effect, no model call, no recap extraction, no worldbuilding bootstrap, no first-session facts, no `member_of`/party collective, no SQL/manual head, no DungeonMind dependency bump. |
| Branch / isolated checkout | `codex/governed-recap-world-genesis`; isolated checkout from current `main`. Do not base on, merge from, or cherry-pick #715. |
| Parallel lanes / collision hotspots | Open #712/#713/#714/#715 are lab/corpus branches. They are read-only evidence for this slice. If any active lane edits a §4 runtime path, serialize or stop; do not resolve by merge conflict. |
| Runtime/state ownership | Focused tests use the existing isolated PostgreSQL test authority/fixture only. Do **not** use live Eldyrwild or #715's `dmb_full_corpus_openai` / `dmb_full_corpus_deepseek` databases in this implementation PR. |
| Backward-looking state sync | The implementation PR may update `HANDOFF-DOGFOOD-CONTINUITY-pc-identity-equivalence-promotion-v1.md` only to record PR #716 merged, merge SHA `d85a3787…`, Review Cycle 1 APPROVE, and 18-pass verification. No current-genesis completion claim belongs in that sync. |
| State authority after this merge | Completion of this handoff is recorded by the next dependent acceptance/retirement slice, or by a guarded steward sync if no successor PR is required. |

### Canonical baseline authority

For Campaign 1 the only semantic genesis source is:

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json
```

The service resolves it through the existing campaign mapping and registry helpers. The caller never supplies an arbitrary filesystem path.

The selected C1 baseline roster contains exactly:

```text
Baergrom
Bonogo
Caelynn
Ephanna
Karsemine
Stafl
```

Registry membership authorizes durable PC identity availability. It does **not** assert that a PC participated in Session 1, was physically present in a scene, performed an action, remained in the party forever, or supports any recap/worldbuilding fact.

Hub README content may remain existing optional display-name enrichment only. Hub bytes are not an additional genesis source. If stable labels cannot be produced without treating hub prose as authority, use deterministic slug-derived labels rather than admit an undeclared source.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Prepare on pristine World | No recap-genesis action exists. | Resolve canonical registry, exact roster, exact digest and inert sealed plan; no graph/source mutation. | Yes | recap-genesis service |
| Prepare on initialized/unreadable World | Existing generic initializer can probe, but no recap service owns semantics. | Fail closed before plan confirmation; never reinterpret existing state as pristine. | Yes | service + initialization authority |
| Prepare malformed/missing/wrong-campaign registry | No dedicated behavior. | Non-confirmable/error; no durable effect. | Yes | service materializer |
| Confirm exact plan | First-world adapter is worldbuilding-shaped. | Rematerialize registry, verify the sealed semantics, then invoke the existing atomic initializer with `party_registry` + `standing_context`. | Yes | service + DungeonMind adapter |
| Registry changes after prepare | Not governed for recap genesis. | Digest/roster/plan mismatch rejects before provider mutation. | Yes | service confirm |
| Head appears after prepare | No recap-specific path. | Provider pristine check fails closed; no second head. | Yes | DungeonMind transaction |
| Exact confirm retry / lost response | Generic provider has receipt-first idempotency. | Return same `D_0`/receipt; no second revision. | Yes | DungeonMind adapter/provider |
| Different semantic command with same init ID | Existing provider detects command conflict. | Typed idempotency conflict; head unchanged. | Yes | provider boundary |
| Different init ID on initialized World | Existing provider detects non-pristine state. | `already_initialized`; no mutation. | Yes | provider boundary |
| Native read immediately after confirm | Existing worldbuilding genesis is readable; recap genesis does not exist. | Normal native mutation-context read sees exact `D_0`, six PCs, and head == receipt revision. | Yes | native read adapter |
| Ordinary existing-parent child publication | #715 can do this only when a parent exists. | Existing governed write path can publish a minimal test child against exact `D_0`; no special first-recap branch. | Yes | existing-parent write integration |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| prepare A → registry bytes become B → confirm A | Reject before source/revision/head/receipt creation. | stale-source service + PG state proof |
| prepare A → another initializer commits → confirm A | `already_initialized`/non-pristine failure; existing head remains sole head. | real-PG competing-init proof |
| confirm commits → caller loses response → exact retry | Same initialization receipt and `D_0`; revision/head counts unchanged. | real-PG lost-response/retry proof |
| exact init ID → changed semantic plan | Idempotency conflict; no head movement. | real-PG changed-command proof |
| party-registry command → adapter accidentally routes through worldbuilding coercion | Test fails; registry source must remain `source_domain_key=party_registry`, coarse provider domain non-worldbuilding/non-recap. | adapter contract proof |
| `D_0` read → ordinary child write | Child parent equals `D_0`; genesis is not bypassed or mutated. | native continuity proof |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/recap_world_genesis.py` | Storage-neutral prepare request, sealed plan, confirm request/result/receipt models. |
| Create | `apps/live_control_server/services/recap_world_genesis.py` | Explicit prepare/confirm behavior, canonical registry rematerialization, deterministic sealing/idempotency, authority invocation. |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py` | Generalize the existing reviewed zero-parent adapter only enough to admit the approved `party_registry` + `standing_context` profile without weakening the existing worldbuilding path. |
| Create | `tests/test_recap_world_genesis.py` | Deterministic roster, inert prepare, stale-source, plan verification, source semantics, all-or-nothing selection, and no-played-claims tests. |
| Modify | `tests/test_cutover_dungeonmind_first_world_initialization.py` | Real-PostgreSQL party-registry initialization, atomicity, exact retry/lost response, conflicting init, and worldbuilding-regression proof. |
| Modify | `tests/test_cutover_native_genesis_continuity.py` | Native `D_0` read plus ordinary existing-parent child-publication witness. |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-pc-identity-equivalence-promotion-v1.md` | Backward-looking state sync for merged prerequisite #716 only. |

Read-only seams expected to be consumed, not edited:

```text
apps/live_control_server/ports/world_graph_initialization.py
apps/live_control_server/ports/world_graph_initialization_access.py
apps/live_control_server/integrations/dungeonmind/contribution_mapping.py
apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py
apps/live_control_server/models/world_graph_contribution_models.py
apps/live_control_server/models/world_graph_mutation_context.py
src/graph_memory/party_context.py
src/graph_memory/standing_context_partition.py
src/graph_memory/source_artifact_domains.py
src/graph_memory/evidence/source_artifact.py
```

**Bounded discovery exception:**

```text
Directory: tests/
Maximum additional paths: 1
Allowed path kinds: an existing shared PostgreSQL fixture/helper only
Decision rule: only when the existing real-PG fixture cannot expose the same
              atomic initialization boundary to the new test without duplication.
```

No additional runtime path is covered by bounded discovery. A missing runtime helper/API is a stop/re-brief rather than permission to broaden the PR.

## §5 Explicitly out of scope / collision boundary

| Path / capability | Rule |
|---|---|
| `out/full_corpus_world_graph_ingestion/**` | #715 notebook evidence; do not edit, copy, regenerate, or make it a merge dependency. |
| `tools/publish_full_corpus_world_graph.py` and other #715 tooling | Post-merge acceptance lane only. Do not promote tooling incidentally in genesis. |
| `src/graph_memory/extract_promote_ops.py` | Existing-parent extraction/promotion remains unchanged. Genesis is a sibling initialization capability. |
| `src/graph_memory/party_context.py` | Consume canonical roster/identity behavior; do not change roster semantics. |
| `src/graph_memory/standing_context_partition.py` | Consume existing artifact/URI/evidence conventions; do not add party edges or new provenance semantics. |
| `apps/live_control_server/services/source_artifact_registry.py` | Do not pre-persist registry authority outside the reviewed zero-parent transaction. |
| `apps/live_control_server/routes/**`, `apps/live_control_server/main.py`, UI | No new route/surface/operator UI in this slice. Service action is sufficient. |
| `pyproject.toml`, `uv.lock` | No DungeonMind pin/schema/API upgrade. Provider-contract change is a stop condition. |
| C1 S1 or later candidate files | No model generation, candidate rewriting, or first-recap special case. |
| Relationship/identity cleanup | No `member_of`, party collective, Lysandra alias work, fuzzy identity widening, or ontology changes. |
| Live/rehearsal campaign databases | No live Eldyrwild and no #715 model-arm DB mutation in this PR. |

## §6 Implementation contract

### Public product behavior

```text
Input — prepare:
  RecapWorldGenesisPrepareRequest
    world_id
    campaign_id
    baseline_roster_key
    requested_by            # audit only; not semantic identity

Input — confirm:
  sealed RecapWorldGenesisPlan
  confirming_principal

Output — inert prepare:
  RecapWorldGenesisPlan

Output — confirm:
  RecapWorldGenesisReceipt

Invariant:
  exact canonical party-registry authority → one atomic zero-parent identity baseline
```

Prepare must:

1. probe the target World and require pristine/uninitialized state;
2. resolve the canonical campaign registry through existing campaign mapping;
3. read **exact bytes** and compute SHA-256;
4. validate supported registry schema and exact `campaign_id` equality;
5. resolve the requested PC roster **by exact key** — no carry-forward for genesis;
6. reject missing/empty roster, duplicate slugs, companions/non-PC entries, unsupported identity, or ambiguous canonical IDs;
7. materialize exactly the selected PC identity anchors, with no party collective or edges;
8. bind evidence to `artifact:party-registry:<campaign_id>` and exact repo URI using existing standing-context provenance conventions;
9. build one accepted `standing_context` contribution with no unresolved/rejected/candidate claims;
10. seal the semantic plan and return without graph/source mutation.

Recommended sealed semantic fields:

```text
schema = dmb_recap_world_genesis_plan_v1
plan_id
plan_digest
initialization_id
world_id
campaign_id
baseline_roster_key
source_artifact_id
source_revision_id = sha256:<exact registry bytes>
source_uri
contribution_id
contribution_payload_sha256
accepted_assertion_ids
pc_object_ids
pc_identity_keys
confirmable
```

Do not put wall-clock prepare time, model-arm name, database name, browser state, or caller-supplied path into the semantic digest. Audit-only fields must not make an otherwise identical baseline produce a different semantic initialization.

### Deterministic identity and plan rules

```text
source_artifact_id = artifact:party-registry:<campaign_id>
source_domain       = party_registry
source_kind         = standing_context
session scope       = null
campaign scope      = exact campaign_id
PC identity key     = pc::<slug>
PC object id        = existing PartyMember.seed_node() object-id family
```

`initialization_id` must be deterministic over the sealed semantic input. Reuse the existing first-world deterministic-id machinery when the sealed `plan_id` already binds all semantic fields; do not create a random UUID.

Same semantic source/roster/world → same plan semantics and initialization ID.  
Same initialization ID + changed semantic command → idempotency conflict.  
Different initialization ID on initialized World → already initialized.

### Confirm trust boundary

Confirm must treat the caller-carried plan as evidence, not source authority. Before invoking `WorldGraphInitializationAuthority.initialize`, rematerialize from the canonical registry and compare at least:

```text
plan_id / plan_digest
world_id / campaign_id
baseline_roster_key
source_artifact_id / source_revision_id / source_uri
PC identity set / object IDs
contribution_id / contribution digest
accepted assertion IDs
```

Any mismatch fails before the transaction boundary.

The `confirming_principal` is recorded as actor/audit authority; changing actor does not change the semantic registry baseline.

### DungeonMind adapter source profile

The existing worldbuilding source profile remains valid and unchanged.

The only new first-world source profile permitted by this slice is:

```text
Buddy source_domain:              party_registry
DungeonMind source_domain_key:    party_registry
DungeonMind coarse source_domain: OTHER
Buddy source_kind:                standing_context
campaign_id:                      exact campaign_id
session_id:                       null
accepted assertion kinds:         node only
```

unless the already-pinned DungeonMind dependency itself already exposes a first-class party-registry enum. Do not map registry authority to WORLDBUILDING, SESSION_RECAP, PREP, MANUAL, or RULEBOOK merely to satisfy an existing branch.

The adapter must fail closed if a party-registry first-world request carries a non-standing contribution, session scope, non-node accepted assertion, mismatched source pair/campaign, unresolved identity, or evidence naming an artifact outside the command.

### Provider timestamp / exact-retry rule

Party-registry source metadata must not cause an exact retry to rebuild a different command digest. If the Buddy registry artifact has no stable persisted `created_at`, the adapter may derive provider artifact/revision creation time from the reviewed initialization's `requested_initialized_at`; the existing receipt-first retry path must then reuse the stored `initialized_at` so the reconstructed command is byte/semantic equivalent. Do not use fresh wall-clock time on exact retry.

This rule is narrow to missing party-registry audit timestamps and must not change existing worldbuilding timestamp semantics.

### Commit point

```text
Before commit:
  canonical bytes were rematerialized and verified;
  only inert plan / request values exist.

Commit point:
  existing DungeonMind reviewed zero-parent initialization transaction.

Atomic durable effects:
  SourceArtifactV2 + SourceRevision
  reviewed standing-context contribution
  immutable D_0 with parent_revision_id = null
  world head → D_0
  reviewed initialization receipt

After commit:
  native World Graph readers/mutation-context code observes D_0 as an ordinary existing World.

Truth after post-commit response loss:
  publication is already durable; exact retry recovers the same receipt/D_0 and never reconfirms a second genesis.
```

### State / fallback matrix

| Path | Loading/init | Exact success | Ordinary miss | Authority unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Prepare | Probe authority + canonical registry | Inert confirmable plan | Missing roster/registry = fail closed | Typed unavailable; no plan claiming success | Malformed/wrong campaign/non-pristine = fail closed | Registry state is read now | Re-prepare rematerializes current bytes |
| Confirm | Rematerialize canonical registry | One `D_0` + receipt | N/A | No success claim | Plan/source/head mismatch fails closed | Changed bytes invalidate carried plan | Exact committed retry returns same receipt |
| Native read | Open exact current revision | Head/revision = receipt `D_0` | Missing after success = integrity failure | Typed read failure | Receipt/head incoherence = integrity failure | Explicit revision remains immutable | Read retry only; never reinitialize |
| Child write smoke | Use exact `D_0` as parent | One ordinary child revision | N/A | Existing write failure semantics | Parent mismatch fails closed | Stale parent rejected | Existing governed-write semantics only |

### Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback? |
|---|---|---|---|
| Registry roster slug | Exact `pc::<slug>` identity; deterministic object ID | Any duplicate/ambiguous identity makes plan non-confirmable | No fuzzy fallback |
| `pc` / `player_character` / `dnd5e:player_character` | Consume #716 normalization at shared mutation comparator | Must resolve as same compatible kind | No new alias layer |
| Later `character` candidate with resolved `corpus_ref.type=pc` | Normal governed identity path resolves existing baseline PC | Collision remains reviewable/blocked per existing policy | No first-win match |
| Same label with NPC/no PC corpus ref | Genuine cross-kind collision remains blocked | Human review per existing policy | No |
| Rename/delete/rebind | Not owned by genesis | Existing identity decision machinery | No genesis special case |

### Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback |
|---|---|---|---|---|---|
| Prepare | None; caller receives sealed plan | Same semantic input seals same semantic plan | Safe; no graph mutation | New plan schema only at product service boundary | Drop plan |
| Confirm | Existing DungeonMind source + contribution + revision/head + reviewed-init receipt | Native read returns exact committed revision/object identities | Exact replay returns same durable init | No DB migration or dependency bump | Transaction rollback before commit; immutable after commit |
| Native read | Existing projection/mutation-context contracts | `head_revision_id == published_revision_id` | Read-only retry | Existing contracts unchanged | N/A |

### Predecessor → consumer mapping

**Grounding:** merged #716 identity rule, current `GraphMemorySourceArtifact`, current `GraphContribution`, current `WorldGraphInitializationRequest`, current DungeonMind adapter.

| Predecessor field/outcome | Real shape | Genesis consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| Buddy `source_domain="party_registry"` | Known source-domain string | First-world source authority | `_store_artifact_v2` preserves key; coarse enum becomes `OTHER` | adapter contract test |
| Buddy `source_kind="standing_context"` | Existing contribution kind | Reviewed baseline contribution | Existing contribution mapper → DungeonMind STANDING_CONTEXT | PG initialization test |
| Registry revision | `sha256:<64 hex>` | SourceRevision identity/digest | Existing source mapping rules; no synthetic parent | source/PG test |
| PC kind representations | `pc`, `player_character`, `dnd5e:player_character` | Existing baseline identity remains reusable | Landed #716 `_norm_kind` compatibility | `test_pc_identity_normalization.py` + continuity test |
| `WorldGraphInitializationReceipt` | existing provider-neutral receipt | Wrap in recap-genesis receipt with source/plan/PC fields | No new DB receipt format | service/PG test |

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected result | Merge blocker |
|---|---|---|---|---|
| Exact C1 registry produces six-PC baseline only | recap-genesis service | focused contract test using real C1 registry bytes | exactly six canonical PC identities, zero edges/session facts | extra/missing identity or invented claim |
| Prepare is inert | service + authority spy/PG state | pre/post counts/probe | no source/revision/head/receipt mutation | any durable effect |
| Source change after prepare fails before commit | confirm service | mutate copied canonical registry between prepare/confirm | plan verification error; durable state still pristine | mutation or stale confirm succeeds |
| `party_registry` provenance survives provider mapping | DungeonMind adapter | focused adapter + PG source snapshot assertion | key=`party_registry`; coarse domain non-worldbuilding/non-recap; contribution STANDING_CONTEXT | provenance relabeled/flattened |
| Worldbuilding first-world path is unchanged | existing adapter regression | existing first-world tests | prior worldbuilding cases remain green | behavior drift |
| One atomic zero-parent revision | real PostgreSQL boundary | existing PG fixture extended for recap genesis | one source/revision, one contribution, one receipt, one `D_0`, parent null, one head | partial rows or extra revision/head |
| Exact retry/lost response | real PostgreSQL boundary | inject response-loss/retry or existing hook | same receipt/revision; no second revision | different command/second head |
| Competing/different init fails closed | real PostgreSQL boundary | initialize then retry with foreign semantic command/id | typed conflict/already initialized; head unchanged | second genesis/head movement |
| Native readers accept `D_0` | native mutation-context integration | load exact world after confirm | six PC objects; head == receipt revision | read requires special recap mode |
| Ordinary existing-parent writer consumes `D_0` | native continuity integration | publish a minimal deterministic test child through existing write path | child parent exactly `D_0`; genesis unchanged | special first-child code or parent drift |
| #716 remains effective | shared identity boundary | existing normalization test | PC forms compatible; NPC collision blocked | regression |
| Scope/lease remains clean | repo diff | diff commands | only §4 paths (+ allowed one test helper) | notebook/tool/route/corpus/runtime scope creep |

Exact commands:

```bash
uv run pytest -q \
  tests/test_recap_world_genesis.py \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_native_genesis_continuity.py \
  tests/test_pc_identity_normalization.py

uv run pytest -q \
  tests/test_cutover_native_governed_write.py \
  tests/test_world_graph_source_admission.py

uv run ruff check \
  apps/live_control_server/models/recap_world_genesis.py \
  apps/live_control_server/services/recap_world_genesis.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py \
  tests/test_recap_world_genesis.py \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_native_genesis_continuity.py

git diff --check
git diff --name-only <implementation-base>...HEAD
```

If a required focused command already fails on base, run the same command on base and head, record the exact delta, and require an explicit waiver before approval. Do not report a baseline-red gate as green.

### Minimal live / dogfood proof

Not applicable as a UI/manual surface. The owning live boundary for this capability is the real isolated PostgreSQL integration witness above.

**Explicitly not a merge gate for this PR:** using #715's saved OpenAI/DeepSeek candidates or rehearsal databases. That is the named post-merge acceptance/retirement successor. This PR must prove the production capability without depending on an unmergeable notebook branch.

## §8 Required review handback

Record:

1. `Review Cycle <N>`, exact PR URL/branch/head SHA, and implementation base;
2. §1 mission/invariant disposition;
3. actual changed paths against §4 and any bounded test-helper discovery;
4. nano-commit story;
5. exact C1 registry SHA-256 used by tests;
6. sealed plan semantic sample (sanitized) and deterministic ID/digest proof;
7. provider source snapshot proving `source_domain_key=party_registry` and coarse non-worldbuilding domain;
8. real-PG state proof: one source revision, one standing contribution, one `D_0` with parent null, one head, one initialization receipt;
9. exact-retry/lost-response and stale-source/foreign-init results;
10. native mutation-context observation of the six PC object IDs/kinds;
11. ordinary child revision ID and exact `parent_revision_id == D_0` proof;
12. #716 identity regression result and existing worldbuilding first-world regression result;
13. every §7 command with exact result and provenance (author-local / independently rerun / CI);
14. baseline failures and waivers (`none` when none);
15. stop conditions (`none` when none);
16. confirmation that #715/#712/#713/#714 branch artifacts were not consumed or modified.

## §9 Acceptance rubric

- [ ] One independently useful production capability exists: explicit governed recap World genesis.
- [ ] The only semantic genesis source is the exact canonical campaign `party_registry` bytes.
- [ ] C1 roster key `1` materializes exactly the six canonical PC identities and no collective, edges, recap/session facts, or participation claims.
- [ ] Prepare performs zero graph/source mutation.
- [ ] Confirm rematerializes canonical bytes and fails stale/tampered plans before commit.
- [ ] `party_registry` remains the DungeonMind source-domain key and is never relabeled as worldbuilding/recap/prep/manual.
- [ ] Existing worldbuilding reviewed genesis behavior remains unchanged.
- [ ] One existing DungeonMind atomic transaction owns source + contribution + `D_0`/head + initialization receipt.
- [ ] Exact retry/lost-response recovery returns the same `D_0`; changed/foreign initialization fails closed.
- [ ] Native mutation context reads `D_0` without a recap-specific fallback.
- [ ] An ordinary existing-parent governed write creates a child whose parent is exactly `D_0`.
- [ ] The landed #716 PC-kind equivalence is consumed, not reimplemented or widened.
- [ ] No route/UI/model call/SQL/bootstrap/DungeonMind upgrade/ontology cleanup enters the slice.
- [ ] No #715 notebook artifact, model-arm database, generated candidate, or publication tool is required for merge.
- [ ] Actual changed paths remain inside §4 / the one bounded test-helper exception.
- [ ] The named successor—full-corpus two-arm acceptance and notebook retirement—remains unimplemented/unclaimed by this PR.

## Stop conditions

Stop and report instead of expanding if:

- the pinned DungeonMind reviewed initializer itself requires worldbuilding provenance or cannot preserve `source_domain_key=party_registry`;
- provider support requires a DungeonMind schema/API/dependency change;
- source + contribution + `D_0`/head + receipt cannot remain one atomic transaction;
- a fake/sentinel/empty parent appears necessary;
- a second source class, party collective, membership edge, recap assertion, or first-recap special write path appears necessary;
- exact retry cannot reconstruct an equivalent provider command without inventing a new durable timestamp/id contract;
- implementation requires changing `party_context`, `standing_context_partition`, `extract_promote_ops`, routes, or #715 tooling;
- native existing-parent publication cannot consume the resulting `D_0` without changing its semantics;
- any active lane owns a required §4 path or shared test database in a way that cannot be isolated;
- a required owning-boundary test cannot be produced with the existing PostgreSQL fixture/provider pin.

Report:

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
