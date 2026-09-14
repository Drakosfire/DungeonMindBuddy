---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / governed full-corpus publication
  - Flow: DOGFOOD-CONTINUITY / recap World genesis
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-governed-recap-world-genesis-v1.md`
  - Blocked consumer: PR #715 full-corpus publication

  ## Decision
  Implement baseline-only recap genesis. A pristine DungeonMind World is initialized from the exact canonical campaign `_party_registry.json` as `party_registry` standing-context authority. Genesis contains only durable PC identity anchors. The first observed recap is then published through the normal existing-parent recap path.

  ## Locked exclusions
  - no LLM calls or candidate regeneration
  - no worldbuilding-as-recap bootstrap
  - no S1 assertions in genesis
  - no SQL/manual head creation
  - no ontology widening, Agent/UI work, or broad identity cleanup
---

# HANDOFF — DOGFOOD-CONTINUITY: governed recap World genesis

**Created:** 2026-09-14  
**Status:** ACTIVE — one production capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-governed-recap-world-genesis-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / full-corpus automated World Graph ingestion`  
**Flow / owner:** `DOGFOOD-CONTINUITY / recap World genesis`  
**Direction:** DESIGN → CODE → REVIEW  
**Design base:** `45e7244dca7beee7c812f82b4004b557cd4d2c2c`  
**Blocked consumer:** PR #715 / full-corpus zero-model publication  
**Suggested PR title:** `DOGFOOD-CONTINUITY: add governed recap World genesis`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

---

## §1 Mission and merge-ready invariant

**Mission:** An explicit operator action can initialize a pristine DungeonMind World for recap memory from a deterministic campaign party baseline, producing one source-backed immutable zero-parent revision that the ordinary existing-World recap publisher can immediately consume.

**Merge-ready invariant:**

> For one pristine `(authority instance, world_id)`, confirm of one sealed recap-genesis plan atomically admits the exact canonical `party_registry` source and creates exactly one zero-parent DungeonMind revision containing only the campaign's canonical PC identity anchors; it never fabricates played/session participation, never uses worldbuilding authority, and exact retry returns the same durable initialization while any changed, foreign, stale, or partial input fails closed without a second head or partially admitted source state.

### Design decision

**Select Option A — baseline-only genesis.**

```text
canonical party_registry bytes
  ↓
sealed recap-genesis plan
  ↓ explicit confirm
DungeonMind reviewed zero-parent transaction
  ↓
D_0: six stable PC identities only
  ↓
normal existing-World recap publication
  ↓
C1 S1 child revision
```

Do **not** select Option B. Combining baseline + S1 into one genesis revision would make the first observed recap use a unique write path, obscure whether identity authority or played evidence created a fact, and weaken the exact chronological witness #715 is trying to exercise.

Do **not** select Option C. The current Buddy first-world adapter is explicitly worldbuilding-shaped (`_worldbuilding_expressible` plus a hard requirement for DungeonMind `SourceDomain.WORLDBUILDING`). Reusing that semantic fiction for recap bootstrap would flatten source authority even though the underlying DungeonMind zero-parent transaction is reusable.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | Yes. Every path is one explicit pristine-World initialization from one sealed registry baseline into one immutable `D_0`. |
| Most likely adversarial sequence | Prepare from registry digest A → registry bytes change to digest B → confirm trusts browser-carried plan → wrong baseline enters `D_0`. Confirm must rematerialize and reject instead. |
| Will §7 detect that failure? | Yes. Real-PG stale-source and lost-response tests exercise the actual initialization boundary. |
| Easiest owning boundary to under-test | Source/evidence mapping: `party_registry` must remain registry authority in DungeonMind rather than silently becoming worldbuilding or recap. |
| Fact that forces stop/split | DungeonMind's existing reviewed zero-parent command cannot accept a non-worldbuilding `SourceArtifactV2` while preserving source/evidence closure. If provider schema itself is source-domain-specific, stop and design the DungeonMind contract first. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/HANDOFF-CUTOVER-mounted-first-world-authority-migration.md`; current `WorldGraphInitializationAuthority`; current `standing_context` / party-registry promotion semantics. |
| Design base | `main@45e7244dca7beee7c812f82b4004b557cd4d2c2c`. Re-anchor before implementation. |
| Blocked consumer | PR #715 has sealed 42-session OpenAI and DeepSeek candidate arms and an existing-parent zero-model replay path, but fresh rehearsal authorities have no head. |
| Canonical baseline source | Campaign `_party_registry.json`, exact bytes, exact SHA-256, `source_domain=party_registry`. For C1 this is `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_party_registry.json`. |
| Existing source identity | `artifact:party-registry:<campaign_id>` and exact `repo://.../_party_registry.json`, via `resolve_party_registry_uri(...)`. |
| Existing contribution class | `standing_context`; do not add a new contribution source kind for this slice. |
| Existing provider transaction | DungeonMind `ReviewedWorldInitializationCommandV1` / reviewed zero-parent initialization: source + contribution + graph revision/head + initialization receipt atomically. |
| Named consumer after merge | #715 creates two fresh equivalent rehearsal Worlds, then replays C1 S1→C2 S25 against exact committed predecessors with zero model calls. |
| What remains false | Worldbuilding ingestion, broader source taxonomies, automatic campaign creation, Agent tuning, UI, general identity cleanup, and ontology expansion remain unimplemented. |
| Runtime/state ownership | Production capability uses the configured DungeonMind authority. #715 injects two explicit isolated rehearsal DSNs; no live authority mutation. |

### Predecessor dependency: PC kind equivalence

The genesis implementation requires the generic identity invariant `pc ≡ player_character` at the mutation/identity boundary so a later generic `character` candidate carrying resolved `corpus_ref.type=pc` resolves to the baseline PC instead of minting an NPC duplicate.

PR #715 currently carries that generic fix experimentally. **Do not silently duplicate a second version here.** Before implementation, re-anchor:

- if the generic normalization is already on `main`, consume it;
- if not, stop and have the steward land/promote that existing generic fix first or explicitly assign it to this PR before coding.

The recap-genesis PR does not own unrelated identity cleanup such as Lysandra aliases or cross-kind meat-object reconciliation.

---

## §3 Authority model and epistemic meaning

### 3.1 `_party_registry.json` is identity authority, not played-session authority

The repo already defines `party_registry` as a source domain, and party context treats registry membership as durable standing campaign state. `PartyMember.corpus_ref()` uses resolved `(type=pc, ref_id=<slug>)` as the strongest deterministic identity key.

For this capability, the registry authorizes only:

```text
this campaign recognizes canonical PC identity <slug>
this identity's object kind is PC / player_character
this identity may be used as a standing anchor for later recap evidence
```

It does **not** authorize:

```text
PC participated in Session 1
PC was physically present in any scene
PC performed any action
party membership persisted through every later session
any recap fact, plan, secret, rumor, or worldbuilding statement
```

The fact that C1's first roster is stored under `session_pc_rosters["1"]` is a registry organization detail used to choose the initial roster. Genesis must not translate that key into a session participation assertion.

### 3.2 Exact source class in DungeonMind

Map the Buddy artifact as:

```text
source_domain_key = "party_registry"
source_domain     = DungeonMind SourceDomain.OTHER
campaign_id       = exact campaign id
session_id        = null
```

unless the pinned DungeonMind dependency already exposes a first-class PARTY_REGISTRY enum at implementation time. Do not map registry evidence to `WORLDBUILDING`, `SESSION_RECAP`, `PREP`, or `MANUAL` merely to fit an existing branch.

`source_domain_key="party_registry"` carries the exact source class even when the provider's coarse enum is `OTHER`.

### 3.3 Baseline content

`D_0` contains exactly the initial canonical PC identity anchors required by the selected registry roster.

For the #715 C1 witness this is exactly:

```text
Baergrom
Bonogo
Caelynn
Ephanna
Karsemine
Stafl
```

Each accepted node is deterministic standing context:

```text
object_id: existing PartyMember.seed_node() identity (`node:<slug>` family)
object_kind: pc → DungeonMind player_character
corpus identity: pc::<slug>
campaign scope: longmont-c1
evidence: exact party_registry source
```

Do not create a party collective, `member_of` edges, session-presence edges, recap facts, or C1 S1 candidate assertions in genesis. Those are not necessary to unblock the chronological write chain and would enlarge the epistemic claim.

Hub READMEs may be used only for existing deterministic display-name enrichment already performed by `party_context`; they are not additional truth sources for genesis. If implementation cannot derive a stable display label without making hub bytes semantic authority, use deterministic slug display and let later source-backed evidence enrich presentation rather than admitting undeclared source authority.

---

## §4 Explicit user/operator intent

Genesis is **not** an implicit side effect of extraction, source admission, database provisioning, or ordinary recap publication.

Introduce one explicit product/service action, conceptual naming:

```text
prepare_recap_world_genesis(...)
confirm_recap_world_genesis(...)
```

The action means:

> Initialize recap memory for this pristine World from this campaign's canonical party-registry baseline.

The caller must identify at least:

```text
world_id
campaign_id
baseline_roster_key          # "1" for the #715 C1 witness
```

The server resolves the canonical registry path/artifact itself. Do not accept an arbitrary filesystem path as equivalent authority.

For #715, the operator invokes the same action independently against each isolated rehearsal authority. The model arm is runtime/receipt metadata, not graph truth and not part of identity resolution.

---

## §5 Prepare / confirm contract

### 5.1 Prepare request

Preferred storage-neutral product request:

```text
RecapWorldGenesisPrepareRequest
  world_id
  campaign_id
  baseline_roster_key
  requested_by / operator principal (audit only)
```

Prepare performs **zero graph mutation** and must:

1. probe initialization authority and require pristine/uninitialized state;
2. resolve the canonical campaign registry using existing campaign corpus mapping;
3. read exact registry bytes and compute SHA-256;
4. validate registry schema and exact `campaign_id`;
5. resolve exactly the selected PC roster;
6. reject empty roster, duplicate slugs, unsupported member kinds, or ambiguous canonical IDs;
7. materialize the six deterministic standing-context node assertions;
8. stamp evidence to `artifact:party-registry:<campaign_id>` using the existing registry provenance convention;
9. build one accepted `standing_context` GraphContribution;
10. seal the complete plan and return it inertly.

### 5.2 Sealed plan

Preferred plan shape:

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
source_uri = repo://...
contribution_id
contribution_payload_sha256
accepted_assertion_ids
pc_object_ids
pc_identity_keys
confirmable
prepared_by
```

**Selection rule: all-or-nothing.** There is no partial six-PC checkbox set. A canonical baseline with one rejected/ambiguous PC is not confirmable. The operator confirms the sealed baseline as a whole or does not initialize.

### 5.3 Deterministic idempotency

Derive `initialization_id` from semantic sealed input, not a random UUID. Conceptually:

```text
sha256(
  schema_version
  + world_id
  + campaign_id
  + baseline_roster_key
  + source_revision_id
  + sorted(pc identity keys)
)
```

Use that value through the existing `WorldGraphInitializationAuthority` / DungeonMind reviewed-init idempotency contract.

Same semantic plan → same initialization id and command digest.  
Same initialization id + changed semantic command → idempotency conflict.  
Different initialization id on an already initialized world → already-initialized conflict.

### 5.4 Confirm

Confirm receives the sealed plan plus the explicit confirming principal. It must **not trust the browser/caller-carried plan as source authority**.

Before crossing the transaction boundary, confirm rematerializes from canonical registry bytes and verifies:

```text
plan_id
plan_digest
source artifact id
source digest/revision
roster key
PC identity set
contribution id/digest
accepted assertion ids
world/campaign scope
```

Any mismatch fails before mutation.

The provider command uses the existing `WorldGraphInitializationRequest` / `ReviewedWorldInitializationCommandV1` machinery. The existing Buddy adapter must be generalized only enough to permit the approved `party_registry` standing-context contribution without relabeling it as worldbuilding.

### 5.5 Product receipt

Return/capture at least:

```text
schema = dmb_recap_world_genesis_receipt_v1
outcome = initialized | already_initialized
world_id
campaign_id
initialization_id
plan_id
plan_digest
source_artifact_id
source_revision_id
source_domain_key = party_registry
contribution_id
contribution_payload_sha256
accepted_assertion_ids
pc_object_ids
published_revision_id
parent_revision_id = null
command_sha256
confirmed_by
initialized_at
```

The receipt must be sufficient to prove that OpenAI-arm and DeepSeek-arm rehearsal authorities began from semantically equivalent baseline inputs without copying one arm's graph or identity ledger into the other.

---

## §6 Atomicity, recovery, identity, and isolation

### A. Failure / recovery matrix

| Situation | Required behavior |
|---|---|
| Registry missing / malformed / wrong campaign | Prepare fails; no source, revision, head, or receipt. |
| Empty/duplicate/ambiguous roster identity | Prepare is non-confirmable; no mutation. |
| Registry bytes change after prepare | Confirm rematerialization detects digest/plan mismatch; no mutation. |
| Target gains a head after prepare | DungeonMind pristine transaction fails closed; no second head. |
| Source admission/materialization fails inside confirm | Transaction rolls back source + contribution + graph/head + receipt together. |
| Exact confirm retried | Return same durable `D_0` / receipt; no second revision. |
| Confirm commits but response is lost | Retry same sealed plan; provider receipt-first recovery returns same `D_0`. |
| Same init id with changed plan | Idempotency conflict. |
| Different init id on initialized world | Already initialized; no mutation. |
| Receipt exists without coherent head | Integrity failure, not success. |
| Partially initialized DB from external/manual tampering | Fail closed as non-pristine/integrity failure; do not repair silently. |

### B. Identity rules

| Situation | Required rule |
|---|---|
| Roster PC | Durable object uses existing resolved `pc::<slug>` identity and PC/player_character kind. |
| Later candidate says `character` but resolved `corpus_ref.type=pc` matches | Resolve existing baseline PC; never mint an NPC duplicate. |
| Same label but different/no corpus_ref | Normal governed identity policy applies; genesis does not broaden fuzzy merging. |
| Registry carry-forward | Identity availability only; never creates participation/history assertions. |
| Party collective/member_of | Not part of this genesis slice. |

### C. Commit point

```text
Before commit:
  only sealed plan / in-memory command values exist

Commit point:
  DungeonMind reviewed zero-parent initialization transaction

Atomic durable effects:
  SourceArtifactV2 + SourceRevision
  reviewed standing-context contribution
  D_0 with parent_revision_id = null
  world head → D_0
  reviewed initialization receipt

After commit:
  native read/mutation-context paths must observe D_0 exactly as an existing World
```

### D. Rehearsal isolation for #715

Use two independently provisioned authorities:

```text
dmb_full_corpus_openai
dmb_full_corpus_deepseek
```

The experiment may use the same semantic `world_id=eldyrwild` inside each isolated database so the already-sealed candidates remain compatible. Isolation is the authority/database boundary, not a fake change to World identity.

Required guards in the #715 consumer:

- explicit injected database URL;
- refuse live `:54330` / live database identity;
- refuse database names outside the declared rehearsal allowlist/prefix;
- never read the other arm's head, identity ledger, receipt, or source catalog;
- initialize each arm independently from the same canonical registry bytes;
- record database name + genesis receipt in sanitized publication evidence;
- teardown only through the existing deliberate scoped drop procedure after experiment completion;
- never write credentials into tracked artifacts.

Equivalent baseline means same source digest, same PC identity set, same plan semantics, and same contribution payload semantics. It does **not** require copying a revision row or receipt between databases.

---

## §7 Read/write compatibility and evidence required

### 7.1 Native compatibility proof

Immediately after confirm, the normal DungeonMind existing-World read path must succeed:

```text
load_production_mutation_context(world_id, database_url=isolated_dsn)
```

and show:

```text
head_revision_id == genesis receipt published_revision_id
revision_id == same D_0
six PC objects exist
all six have player_character-compatible kind
no recap/session facts were authored by genesis
```

Then the existing #715 replay path must publish the already-sealed C1 S1 candidate with:

```text
expected_parent_revision_id = D_0
model_calls = 0
```

and produce one child whose parent is exactly `D_0`.

No special "first recap" publication branch is allowed after genesis.

### 7.2 Required owning-boundary tests

| Guarantee | Owning boundary | Required evidence |
|---|---|---|
| Registry resolves to deterministic six-PC standing baseline | recap-genesis plan materializer | focused contract test using real C1 registry fixture/bytes |
| Prepare mutates nothing | product service + real repository state | pre/post pristine probe + source/head/revision counts unchanged |
| `party_registry` remains registry authority | DungeonMind initialization adapter | adapter test asserting `source_domain_key=party_registry`, coarse enum non-worldbuilding/non-recap, evidence closure preserved |
| Real zero-parent atomic initialization | DungeonMind-backed adapter + PostgreSQL | integration test on fresh isolated PG: 1 head, 1 D_0, parent null, source + contribution + receipt all present |
| Exact retry/lost response | same real-PG boundary | same revision/receipt, no second revision |
| Changed bytes between prepare/confirm | product confirm | mutate fixture copy after prepare; fail before any durable rows |
| Foreign/different init on initialized World | provider boundary | typed already-initialized/idempotency failure; no head movement |
| PC identity does not become NPC later | mutation/identity boundary | baseline genesis + generic PC-shaped later candidate resolves existing |
| Existing worldbuilding first-world path unchanged | current first-world regression cohort | all existing CUTOVER first-world initialization tests remain green |
| Existing recap publisher consumes D_0 | full integration witness | zero-model C1 S1 publication child with exact parent D_0 |

### 7.3 Real isolated-PG witness required before #715 resumes

Run against **two fresh** isolated PostgreSQL authorities, one per model arm:

```text
prepare identical C1 baseline independently
→ confirm each
→ compare sanitized genesis receipts
→ load native mutation context from each D_0
→ assert six canonical PCs
→ replay that arm's saved C1 S1 candidate with zero model calls
→ assert S1 parent == that arm's D_0
```

Only after both witnesses pass may #715 continue S1→S42 publication.

The witness must exercise the production initialization adapter/service. An in-memory mapper test or direct repository insert is not sufficient.

---

## §8 Files in scope — implementation write lease

Expected paths; re-anchor before coding because #715 and any PC-normalization promotion may move shared seams.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/services/recap_world_genesis.py` | Explicit prepare/confirm product service and sealed plan rematerialization. |
| Create | `apps/live_control_server/models/recap_world_genesis.py` | Storage-neutral prepare/plan/confirm/receipt values. |
| Modify | `apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py` | Generalize first-world source/evidence mapping only enough for approved `party_registry` standing context while preserving worldbuilding behavior. |
| Reuse / minimally modify | `src/graph_memory/standing_context_partition.py` | Canonical registry artifact/URI/evidence helpers; only change if an owning helper required by genesis is missing. |
| Reuse / minimally modify | `src/graph_memory/party_context.py` | Deterministic roster/PC identity materialization; no participation semantics. |
| Create | `tests/test_recap_world_genesis.py` | Prepare/rematerialize/idempotency/stale-source/identity contract tests. |
| Create or extend | `tests/...first_world...postgres...py` | Real isolated-Postgres initialization + retry + C1 S1 existing-parent witness. |

**Bounded discovery exception:**

```text
Directories:
  apps/live_control_server/integrations/dungeonmind/**
  apps/live_control_server/ports/**
  src/graph_memory/**
Maximum additional runtime paths: 3
Allowed path kinds:
  existing owner of reviewed zero-parent command construction;
  existing owner of party-registry SourceArtifact materialization;
  exact existing-parent mutation-context consumer needed for the compatibility witness.
Decision rule:
  only if the path already owns a required §1 invariant clause; record the discovery before editing.
```

Do not add a new DungeonMind database migration or provider command in Buddy unless the §1 stop condition proves the current provider cannot express a source-neutral reviewed initialization.

---

## §9 Explicit non-goals / collision boundary

| Capability/path | Exclusion |
|---|---|
| Full worldbuilding ingestion | Remains separately governed; do not use it to bootstrap recap memory. |
| C1 S1 extraction/model generation | Already sealed in #715; zero new model calls. |
| Atomic baseline + S1 genesis | Rejected by design; S1 must exercise normal existing-parent publication. |
| Relationship ontology widening | Not part of genesis. |
| Identity cleanup beyond roster invariant | No Lysandra/cross-kind/general alias project. |
| Party participation / `member_of` chronology | Baseline identity is not session participation. |
| Agent retrieval/tuning | Separate benchmark/successor. |
| Plan/Play/Ingest UI | No UI required; explicit service/operator action is sufficient. |
| Combat | Unrelated. |
| Direct SQL / copied heads / copied arm graph | Forbidden evidence. |
| Live Eldyrwild mutation for #715 witness | Forbidden. |

---

## §10 Acceptance rubric / handback

Implementation is merge-ready only when all are true:

- [ ] Option A is implemented: baseline-only `D_0`, then ordinary S1 child.
- [ ] Exact `_party_registry.json` bytes are the admitted genesis source.
- [ ] Source remains `party_registry`; no worldbuilding/recap relabeling.
- [ ] Genesis contains exactly the selected canonical PC identity anchors and no played/session claims.
- [ ] All roster PCs materialize as durable PC/player_character identities.
- [ ] Prepare is inert and confirm rematerializes source bytes before mutation.
- [ ] One DungeonMind atomic transaction owns source + contribution + D_0/head + receipt.
- [ ] Exact retry/lost-response returns the same D_0.
- [ ] Changed/foreign/stale/partial inputs fail closed.
- [ ] Native mutation-context read works immediately from D_0.
- [ ] Saved C1 S1 candidate publishes against exact D_0 with zero model calls.
- [ ] Existing worldbuilding first-world tests remain green.
- [ ] Two fresh #715 rehearsal authorities independently produce equivalent baseline semantics without cross-arm reads/copies.
- [ ] No live authority, SQL bootstrap, new model call, ontology widening, UI, Agent, or worldbuilding work entered the slice.

### Required review handback

Record:

1. exact implementation PR/head SHA and base;
2. exact C1 registry SHA used by the witness;
3. genesis plan/receipt schema and sanitized sample;
4. six PC object IDs/kinds observed through native mutation context;
5. Postgres row/state proof: one D_0, parent null, one head, one initialization receipt;
6. exact-retry and stale-source results;
7. existing worldbuilding first-world regression result;
8. C1 S1 zero-model child revision and exact `parent_revision_id=D_0` proof;
9. OpenAI-arm and DeepSeek-arm isolated genesis receipt comparison;
10. any path outside §8 (`none` or stop report).

## Stop conditions

Stop and report instead of widening when:

- pinned DungeonMind reviewed initialization itself requires worldbuilding provenance;
- `party_registry` cannot be represented without a DungeonMind contract/schema change;
- source + contribution + D_0/head + receipt cannot commit atomically;
- a fake/sentinel/empty parent appears necessary;
- a second source class or first-recap special write path becomes necessary;
- implementing genesis requires broad identity or relationship redesign;
- the generic `pc ≡ player_character` predecessor is absent and ownership is unresolved;
- #715's saved C1 S1 candidate cannot consume the resulting native mutation context without changing candidate semantics.

Report using the repository stop format before modifying additional authority boundaries.
