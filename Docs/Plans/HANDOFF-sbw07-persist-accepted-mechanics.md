# HANDOFF — SBW07 Persist accepted mechanics as an immutable revision

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW05`; `SBW06` is optional for first-save UX. Re-anchor base and Server persistence contract.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw07-persist-accepted-mechanics.md`  
**Workstream:** `SBW07`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: persist validated mechanics as one logical statblock with one exact immutable first revision and record that locator on the ThreatDraft. Do not publish a Threat, update a graph binding, append a later revision, embed Markdown, or add combat/media behavior.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Create logical statblock + immutable first revision | Yes | Yes | Yes | Include |
| Store exact accepted mechanics ref on ThreatDraft | No; required to make the save recoverable | Yes | Yes | Include under same invariant |
| Publish Threat + binding to graph | Yes | Yes | Yes | Successor `SBW09` |
| Append later revision | Yes | Yes | Yes | Successor `SBW13` |
| Compare/upgrade uses | Yes | Yes | Yes | Successor `SBW13–14` |
| Corpus promotion | No longer desired architecture | Yes | Yes | Demolish from normal acceptance path |

**Selected capability:** the GM can turn one validation-eligible complete definition into exact durable mechanics and later reload the same immutable revision.

## §1 Mission

A GM can save one validated complete definition as a DungeonMind statblock and immutable first revision so accepted mechanics survive reload with exact identity and digest before any campaign graph publication.

**Invariant**

```text
“Mechanics saved” always means one exact persisted (statblock_id, revision_id, definition_digest) returned by DungeonMindServer and atomically recorded on the source ThreatDraft; it never implies graph publication.
```

**Mission falsification test**

```text
This is not one slice if implementation must also create/update a Threat node, choose a campaign-preferred revision, append a child revision, embed a document, mutate combat, or bind media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §7.1–7.3; tracker `SBW07`; DungeonMindServer create-statblock persistence/idempotency contract |
| Repository rules | `AGENTS.md`; external-agent PR loop rules/template |
| Base revision | Merged SHA containing `SBW01–05`; include `SBW06` if already merged |
| Predecessor contract | Complete typed working definition + validation receipt bound to exact digest |
| Exact input consumed | Draft/candidate locator, complete definition, current validation receipt/digest, stable idempotency key, acceptance metadata |
| Named successor | `SBW09` governed Threat publication; `SBW13` append child revision |
| What remains false | No World Graph object or binding exists; no “published/canonical threat” claim |
| Explicit non-goals | Graph, append revision, preferred revision, Markdown, combat, image selection, Server schema redesign |

Read in order:

1. integration design §7 and object ownership table
2. tracker `SBW07`
3. merged `SBW05` digest/validation state contract
4. current Server create-statblock route/OpenAPI/client fixtures and idempotency rules
5. merged `SBW02` ThreatDraft atomic update semantics
6. current workbench corpus-promotion path solely for demolition inventory

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Open acceptance confirmation | Corpus promotion/transitional controls | Show exact definition digest, validation state, and “mechanics only” consequence | Yes | workbench UI |
| Save valid definition | No v1 persistence workflow | Call Server create with stable idempotency key | Yes | service/route |
| Validation errors present | No authoritative gate | Block before downstream create | Yes | UI/service |
| Warnings only | Undefined | Permit only when Server validation semantics allow; disclose warnings | Yes | UI/service |
| Duplicate submit | Risk of duplicate resources | Idempotent replay returns same exact resource/revision | Yes | service/Server/store |
| Downstream success + Buddy response loss | Undefined | Recover exact result by idempotency/read; no second resource | Yes | orchestration |
| Downstream success + draft-ref write failure | Undefined | Truthful `mechanics_saved_reference_pending` or equivalent; reconcile and retry | Yes | orchestration/store |
| Reload saved mechanics | Corpus path lookup | Exact revision read and digest proof | Yes | service/route/UI |
| Graph publication absent | Potentially conflated | UI explicitly says saved, not published | Yes | workflow state |
| Corpus promotion acceptance | Active predecessor | Removed from normal acceptance path | Yes | workbench/backend demolition |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/models/statblock_candidate_workflow.py` | `AcceptedMechanicsRefV1`, save request/result, partial state |
| Create | `apps/live_control_server/services/statblock_mechanics_acceptance.py` | Validation gate, idempotent create orchestration, reconciliation |
| Modify | merged `SBW01` DungeonMind client implementation | Add typed create-statblock and exact-read operations |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Atomic accepted-ref/workflow-state write |
| Modify | `apps/live_control_server/routes/statblock_candidates.py` | Accept/save and reconciliation/read endpoints |
| Create | `tests/test_statblock_mechanics_acceptance.py` | gate/idempotency/partial/reload proof |
| Modify | `tests/test_statblock_candidate_routes.py` | route contract proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | acceptance/ref/result types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | accept/read/reconcile calls |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | mapping proof |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | confirmation, state, retry/reload UX |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | user workflow proof |
| Delete/Modify | exact corpus-promotion acceptance UI/backend paths named by inventory | remove replaced normal acceptance path |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package; current statblock corpus-promotion route/service area
Maximum additional paths: 5
Allowed path kinds: client method, real create/read fixtures, direct predecessor route/service/test deletion
Decision rule: required to consume real Server persistence or delete the exact normal acceptance predecessor
Required report: name every retained predecessor consumer and deletion owner
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| World Graph Threat/resource/binding | `SBW08–09` |
| graph preview/confirm UI | `SBW09` |
| append child revision | `SBW13` |
| revision comparison/upgrade | `SBW13–14` |
| Markdown/Tiptap embed | `SBW11–12` after decomposition |
| combat | `SBW15` |
| images/media | `SBW16–17` |
| deleting valid Server revision after graph failure | prohibited; mechanics resource remains valid |
| local persistence of canonical definition | Server owns mechanics authority |

## §6 Implementation contract

```text
Input:
  draft_id + expected draft version/workflow token
  exact candidate/source locator
  complete StatblockDefinitionV1_Input
  current validation receipt bound to exact definition digest
  stable idempotency key persisted before/with attempt
  acceptance metadata safe for Server contract

Output:
  AcceptedMechanicsRefV1:
    provider=dungeonmind
    statblock_id
    revision_id
    contract/version
    definition_digest
    accepted_from_candidate_id?
    accepted_from_draft_version
    accepted_at
  plus workflow state mechanics_saved or truthful partial state

Invariant:
  exact persisted locator/digest is the only success truth; graph publication remains separate

Failure behavior:
  validation errors/stale receipt -> block before downstream
  integration/auth/timeout -> typed failure; no success claim
  Server conflict/idempotency mismatch -> explicit conflict, no alternate create
  malformed create response/exact-read mismatch -> integrity failure, no accepted ref
  downstream success + local ref write failure -> preserve idempotency/result locator and expose recovery; do not delete Server resource
  exact-read unavailable after create -> create result may establish saved state only if contract guarantees exact IDs/digest; mark verification pending honestly

Replay / idempotency:
  same idempotency key + same definition digest/metadata -> same logical resource/revision
  same key + changed definition/metadata -> conflict
  UI double-submit -> one operation
  retry after partial failure -> reconcile by idempotency/exact locator before create

Trust boundary:
  Verifies: validation receipt/digest association, complete definition, Server response, exact IDs/digest, draft version
  Records without proving: campaign-world identity, graph canon, game balance beyond validation
  Rejects: stale validation, name/path identity, corpus write as acceptance, local-generated revision IDs
```

### Commit model

```text
Commit point: DungeonMindServer successfully persists logical statblock and first immutable revision.
Before commit: candidate/working definition may be edited or discarded; no durable mechanics claim.
After commit: valid immutable mechanics exist even if DungeonBuddy cannot update the draft or publish graph truth.
Truthful result after post-commit failure: mechanics persisted; DungeonBuddy reference/publication pending.
Recovery: exact read/idempotency reconciliation, then atomic AcceptedMechanicsRef write.
```

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Downstream unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Acceptance gate | compute current digest/receipt | eligible confirmation | no receipt = blocked | N/A | digest mismatch blocked | stale receipt blocked | revalidate |
| Create | submitting | exact IDs/digest | N/A | typed failure | fail closed | draft/version conflict | idempotent reconcile |
| Draft ref write | current draft load | mechanics_saved | draft missing = partial/error | N/A | fail closed | stale draft = partial/reprepare write | exact ref retry |
| Reload exact revision | read locator | exact digest match | 404 integrity issue | unavailable but locator retained | mismatch fail closed | N/A | retry read |

No fallback to corpus file, display name, latest revision, or a second create.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Idempotency operation | stable persisted key scoped to draft/source/digest | changed payload conflict | No | dedupe across retries |
| Statblock | exact Server `statblock_id` | none | No | logical mechanics identity |
| Revision | exact Server `revision_id` | none | No latest | immutable mechanics identity |
| Definition | exact deterministic digest confirmed by Server | mismatch integrity failure | No | accepted ref |
| Draft | exact `draft_id` + expected version/token | stale conflict/partial state | No name match | atomic ref write |
| Candidate | exact source ID if present | expired still valid as provenance if definition/validation exact | No | provenance only |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Recovery |
|---|---|---|---|---|---|
| Create statblock | Server-owned resource + immutable revision | exact IDs/digest readable | idempotent same request | Server contract authority | exact read/idempotency lookup |
| Store accepted ref | strict `AcceptedMechanicsRefV1` on ThreatDraft | exact locator/digest | same ref idempotent; different ref conflict/explicit replacement not allowed here | schema versioned | retry atomic write |
| Store attempt/recovery | bounded local operation record if required | idempotency/source/result retained | same operation reconciles | separate from mechanics authority | resume after restart |
| Reload | exact Server read | digest equality | safe repeat | no latest migration | unavailable state retains ref |

### §6D Predecessor-to-consumer mapping

**Grounding source:** real Server create-statblock request/response, exact revision read, error/idempotency fixtures.

Required mapping:

| Server field/outcome | Buddy field/behavior | Rule | Proof |
|---|---|---|---|
| idempotency key/header | acceptance operation | persisted before call; never browser secret | replay test |
| logical statblock ID | accepted ref | exact copy | fixture/read test |
| first revision ID | accepted ref | exact copy | fixture/read test |
| definition digest | accepted ref/gate | exact equality | mismatch test |
| created/revision metadata | disclosure/audit | bounded copy | fixture |
| validation/conflict envelope | blocked/failure state | stable category | error tests |
| exact-read response | reload proof | IDs/digest must match | integration test |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Stale/error validation cannot create | acceptance service | focused tests with fake call counter | zero downstream calls |
| Double submit creates once | service + fake Server/idempotency | concurrency/replay tests | one resource/revision |
| Post-commit local failure truthful/recoverable | service/store failure injection | focused test | partial state then same ref saved |
| Exact reload/digest proof | service/route | create + exact read test | IDs/digest equal |
| UI wording/state separation | workbench component | tests | “mechanics saved; not published” |
| Corpus acceptance predecessor removed | diff/tests | search and workflow test | no normal promotion path |
| No graph mutation | service/diff | spies/path inspection | zero graph calls |

Required commands:

```bash
uv run pytest tests/test_statblock_mechanics_acceptance.py tests/test_statblock_candidate_routes.py -q
cd apps/live-control-ui && npm test -- --run src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use the existing workbench with a validation-clean candidate. Confirm save, capture exact IDs/digest, reload exact revision, double-submit safely, then inject a local draft-write failure and show mechanics remain saved with a reconciliation action. Do not publish a graph object.

## §8 Required handback

Include real Server mapping/idempotency semantics, operation/partial-state schema, base/head, paths, tests/results/provenance, live IDs/digest proof, demolition ledger, baseline failures/waivers, and confirmation that graph/latest/embed/combat/media remain false.

## §9 Acceptance rubric

- [ ] Validation-clean exact digest is required.
- [ ] One idempotent operation creates one logical statblock and first immutable revision.
- [ ] Exact IDs/digest are atomically recorded or recoverably pending.
- [ ] Exact reload proves the same revision.
- [ ] UI never labels saved mechanics as a published/canonical Threat.
- [ ] Post-commit failure never deletes or hides valid Server mechanics.
- [ ] Corpus promotion is not the normal acceptance path.
- [ ] No graph, append revision, preferred/latest, embed, combat, or media behavior ships.

## §10 Reviewer protocol

Start at the commit point and failure injection. Audit idempotency persistence, exact digest comparison, stale validation, double-submit races, wording, and demolition. Search for graph writers, corpus writers, `latest`, local revision IDs, and rollback deletion.

## §11 Re-review protocol

Re-run validation gates, replay/concurrency, post-commit failure, reconciliation, exact-read mismatch, and UI state tests after every fix.

## Stop conditions

Stop if:

- Server create semantics do not provide stable idempotency;
- accepted ref cannot be written atomically or recovered after restart;
- exact revision read disagrees with create response;
- validation receipt cannot be tied to the submitted digest;
- removing corpus promotion breaks an unnamed active consumer;
- graph publication is required to call mechanics saved;
- a path outside the allowlist is required.

## Final dispatch check

- [ ] Re-anchor after predecessor merge.
- [ ] Capture real create/read/idempotency fixtures.
- [ ] Name demolition consumers/deletion owner.
- [ ] Confirm all graph/projection/runtime successors remain false.
