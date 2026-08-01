# HANDOFF — DungeonMindServer generation-validation diagnostics

**Created:** 2026-07-29
**Status:** CONDITIONAL SUCCESSOR — dispatch only if R0-A-class opaque `definition_invalid` regresses. #462/SBW09a merged at `2fa5b790…`; this conditional diagnostics handoff remains outside the current Statblock sequence.
**Implementation repository:** `Drakosfire/DungeonMindServer`
**Implementation base:** `2c7d2566baa744f2b1a4667761775c1dec87a2d4`
**Suggested branch:** `feat/statblocks-v1-generation-validation-diagnostics`
**Parent dogfood evidence:** `Drakosfire/DungeonMindBuddy/Docs/Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`
**Named consumer successor:** DungeonMindBuddy propagation + Workbench rendering of the diagnostic packet.

---

> **Salvage banner (2026-07-31):** Mined from superseded PR #449 head `2369d32b3b574104cc09fc8abb0bddef69031f51`. Technical mission/invariant/allowlist preserved. Do not dispatch while R0-A remains OPERATOR_CONFIRMED_PASS on main unless regression reproduces the opaque failure.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Return safe typed diagnostics for generated definitions rejected before candidate creation | Yes | Yes | API consumer-visible | Yes | Yes | **Include** |
| Persist the diagnostic packet in failed generate/revise operation snapshots so replay is identical | No, required to make the included contract truthful | Yes | No direct UI | Yes | Yes | **Include under the same invariant** |
| Teach DungeonMindBuddy to preserve/render the packet | Yes | Yes, separate repository | Yes | Yes | Yes | **Successor** |
| Automatically ask the provider to repair invalid output | Yes | Yes | Yes | Yes | Yes | **Successor / reject from this slice** |
| Relax `StatblockDefinitionV1` or domain validation | Yes | Yes | Yes | Yes | Yes | **Reject** |
| Tune prompts for Mireward Latchling | Yes | No stable contract | Indirect | Yes | Yes | **Defer until diagnostics identify the failure** |

**Selected capability:** DungeonMindServer emits and durably replays bounded typed diagnostics for `definition_invalid` generation/revision failures.

**Why the included rows share one invariant:** The response is not a truthful request-id contract if the first failure is inspectable but same-key replay loses or changes its diagnostics. Initial response and durable replay are two observable paths of one failure contract.

**Named successors:**

1. DungeonMindBuddy candidate response propagation and Workbench rendering.
2. Bounded automatic repair/retry, only if real diagnostics justify it.
3. Prompt/schema changes for recurring provider failure patterns.

---

## §1 Mission

DungeonBuddy consumers can inspect why a generated definition was rejected so that a real failed candidate request is actionable and reproducible instead of collapsing to `Generated definition failed validation`.

**Invariant**

```text
For one exact failed `(caller_scope, request_id, request_digest)`, the first response and every same-body replay expose the same safe diagnostic phase and issue packet, without storing or returning raw provider output.
```

**Mission falsification test**

```text
This is not one slice if implementation must also regenerate a candidate,
change validation acceptance, or modify DungeonMindBuddy UI behavior.
```

---

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | DungeonMindServer statblocks v1 contract and the real Mireward Latchling R0-A failure recorded in DungeonMindBuddy |
| Base revision | `2c7d2566baa744f2b1a4667761775c1dec87a2d4` |
| Predecessor contract | PR23 durable generate request-id idempotency and PR24 durable revise request-id idempotency |
| Exact input consumed | Provider `outcome.payload`, Pydantic `ValidationError`, and `ValidationReceiptV1` produced in `GenerationServiceV1._run` |
| Named successor | DungeonMindBuddy propagation/rendering |
| What remains false | A GM still cannot see diagnostics in the Workbench until the successor lands; invalid output is not auto-repaired |
| Explicit non-goals | parser relaxation, prompt tuning, automatic second provider call, Buddy code, candidate creation on invalid mechanics, raw payload retention |

Read in order before changing code:

1. `statblocks_v1/application/generation.py`
2. `statblocks_v1/domain/receipts.py`
3. `statblocks_v1/domain/candidate_operations.py`
4. `statblocks_v1/api/http_errors.py`
5. `statblocks_v1/api/router.py`
6. PR23/PR24 request-id replay tests and repositories
7. generated/OpenAPI drift tests

### Authority precedence

```text
1. current DungeonMindServer implementation and statblocks v1 contract
2. PR23/PR24 idempotency invariants
3. this checked-in handoff
4. DungeonMindBuddy dogfood report
5. chat summaries
```

Stop if current `main` moved materially, if another PR changes `GenerationFailureV1` or candidate-operation failure persistence, or if failed replay is no longer authoritative.

---

## §3 Observable-path inventory

| Observable path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Provider payload fails Pydantic model validation | `definition_invalid`; generic public error | `phase=schema_validation`; bounded normalized issues | Yes | generation service + HTTP error contract |
| Parsed definition fails generation-candidate domain validation | `definition_invalid`; generic public error | `phase=domain_validation`; bounded `ValidationIssueV1` packet | Yes | generation service + HTTP error contract |
| First failed generate request | operation stores kind/message only | operation stores safe diagnostics and response emits them | Yes | generate operation repository + route |
| Same-key/same-body generate replay | returns stored generic failure; no provider call | returns identical diagnostics; no provider call | Yes | generate operation repository + service |
| First failed revise request | operation stores kind/message only | same diagnostic contract as generate | Yes | revise operation repository + route |
| Same-key/same-body revise replay | returns stored generic failure | returns identical diagnostics; no provider call | Yes | revise operation repository + service |
| Same key/different digest | 409 | unchanged; no diagnostic rebinding | Yes | idempotency repository/service |
| Unknown generation failure | fail-closed generic 500 | unchanged | Yes | HTTP error mapping |
| Raw provider payload | not returned | remains absent from response, logs, operation records | Yes | all boundaries |
| Old persisted failure record without diagnostics | parses under current model | remains readable; exposes empty/absent packet, not fabricated issues | Yes | persistence compatibility |

Adversarial ordered sequence:

```text
provider returns invalid payload
→ service derives safe diagnostics
→ durable operation records terminal failure
→ HTTP response is lost
→ caller replays same request_id/body
→ repository returns terminal failure
→ replay exposes byte-equivalent semantic diagnostic packet
→ provider call count remains one
```

---

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `statblocks_v1/application/generation.py` | Capture normalized schema/domain diagnostics in `GenerationFailureV1` |
| Modify | `statblocks_v1/domain/candidate_operations.py` | Persist safe optional diagnostics in terminal failure snapshots with backward compatibility |
| Modify | `statblocks_v1/api/http_errors.py` | Emit typed bounded diagnostics for `validation_failed` |
| Modify | `statblocks_v1/api/models.py` | Define transport model(s) for diagnostic packet if needed |
| Modify | `statblocks_v1/api/router.py` | Advertise exact 422 response contract if model changes require it |
| Modify | `statblocks_v1/infrastructure/memory_repositories.py` | Round-trip terminal diagnostics |
| Modify | `statblocks_v1/infrastructure/firestore_repositories.py` | Round-trip terminal diagnostics and legacy records |
| Modify | `tests/statblocks_v1/test_generation_service.py` | Prove schema/domain classification and sanitization |
| Modify | `tests/statblocks_v1/test_memory_repositories.py` | Prove first response/replay equality and old-record compatibility |
| Modify | `tests/statblocks_v1/integration/test_firestore_repositories.py` | Prove durable Firestore replay equality |
| Modify | `tests/statblocks_v1/api/test_candidate_routes.py` | Prove route envelope for generate and revise |
| Modify | `tests/statblocks_v1/test_consumer_contract_artifacts.py` | Prove published contract/fixture drift |
| Modify if generated contract changes | `openapi/dungeonbuddy-statblocks-v1.json` | Publish current contract |
| Modify if generated contract changes | `generated/dungeonbuddy-statblocks-v1/client.ts` | Generated consumer artifact |
| Modify if established fixture pack requires it | `tests/statblocks_v1/test_api_fixtures.py` | Cross-fixture proof |

### Bounded discovery exception

```text
Directory: tests/statblocks_v1/fixtures/
Maximum additional paths: 2
Allowed path kinds: one validation-failure response fixture and its paired request fixture
Decision rule: only when the existing consumer-contract artifact test requires committed route-faithful fixtures
Required report: list exact paths and explain why unit/API assertions were insufficient
```

Any production path outside the allowlist is a stop condition.

---

## §5 Files and capabilities explicitly out of scope

| Path or capability | Why excluded |
|---|---|
| DungeonMindBuddy repository | Separate consumer capability and PR |
| provider prompt builders | Failure pattern is not yet known |
| schema compiler | No evidence that the published schema is the fault |
| `StatblockDefinitionV1` validation rules | The gate must remain strict |
| provider retry policy | Automatic repair/retry is a separate behavioral outcome |
| candidate success models | No candidate exists on this failure path |
| UI wording | Consumer-owned successor |
| logging raw payloads | Privacy/security violation |

---

## §6 Implementation contract

```text
Input:
  provider outcome payload
  requested ruleset
  deterministic generation-candidate validation receipt
  exact durable generate/revise operation identity

Output on definition_invalid:
  HTTP 422 ErrorEnvelopeV1
  error.code = "validation_failed"
  error.message = "Generated definition failed validation"
  error.details contains one bounded diagnostic packet

Diagnostic packet minimum:
  schema/version discriminator
  phase: "schema_validation" | "domain_validation"
  issue_count
  issues[] with bounded stable fields

Domain issue fields:
  code
  severity
  field_path
  message
  suggested_resolution?

Schema issue fields:
  stable normalized code
  severity="error"
  field_path derived from Pydantic loc
  bounded public message
  suggested_resolution? = null

Invariant:
  same exact failed operation returns semantically identical packet on replay

Failure behavior:
  diagnostic normalization failure → retain definition_invalid generic message and fail closed; never include raw payload
  persistence unavailable before terminal write → existing persistence_unavailable semantics
  legacy failure record without packet → generic validation_failed with absent/empty packet

Replay:
  same key + same digest → same packet, zero provider calls
  same key + changed digest → 409 idempotency_conflict
```

### Security and bounds

- Never serialize `ValidationError.input`, raw `outcome.payload`, provider exception objects, prompts, credentials, or response bodies.
- Use a fixed issue limit. Recommended maximum: 32 issues.
- Bound field path, code, message, and suggested-resolution lengths.
- Preserve deterministic ordering.
- Redact or omit unexpected message content rather than reflecting arbitrary provider values.

### Commit point

The terminal generate/revise operation failure record is the commit point for replay authority. The packet returned after that commit must be derived from the persisted snapshot, not a separate transient object.

---

### §6A State and fallback matrix

| Path | Initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Replay |
|---|---|---|---|---|---|---|---|
| Generate invalid schema | provider call | 422 + schema packet | N/A | existing provider failure | fail closed, no raw payload | N/A | exact stored packet |
| Generate invalid domain | validator call | 422 + domain packet | N/A | existing provider failure | fail closed | N/A | exact stored packet |
| Revise invalid schema/domain | same as generate | same contract | source miss remains existing 404/503 | existing behavior | fail closed | exact source rules unchanged | exact stored packet |
| Legacy failed op | load | generic existing failure | N/A | persistence behavior unchanged | corrupt record fails closed | N/A | no fabricated packet |

No fallback to a candidate, prior candidate, latest resource, relaxed parser, or new provider call is permitted.

---

### §6B Identity matrix

| Situation | Matching rule | Ambiguity behavior | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Exact request | `(caller_scope, operation, request_id)` plus exact request digest | conflict on changed digest | No | stored failure remains authoritative |
| Candidate ID | no candidate is created | N/A | No | reserved ID may remain operation-internal; never present as successful candidate |
| Validation issue | ordered packet from exact failed attempt | no merge across attempts | No | packet stored with failure snapshot |
| Legacy record | exact operation identity | absent packet remains absent | No | backward-compatible read |

---

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility | Rollback |
|---|---|---|---|---|---|
| fail generate | `CandidateGenerationFailureSnapshotV1` | phase/issues preserved | same request returns same packet | old records without packet load | code rollback must still read records written by this slice or migration/versioning must be explicit |
| fail revise | same snapshot model | same | same | same | same |
| Firestore serialization | existing operation document | exact bounded JSON packet | no provider call on replay | missing optional field accepted | no destructive migration |

---

### §6D Predecessor-to-consumer mapping

| Predecessor field/outcome | Current shape | New consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| Pydantic `ValidationError` | exception retaining rejected payload | safe schema issue packet | `errors(include_input=False, include_url=False)` or equivalent; normalize/bound | generation-service test |
| `ValidationReceiptV1.issues` | typed deterministic list | domain issue packet | model dump of bounded public fields | generation-service test |
| `GenerationFailureV1` | kind/message | kind/message/optional diagnostic packet | explicit field | service tests |
| `CandidateGenerationFailureSnapshotV1` | kind/message | optional packet persisted | backward-compatible optional field | repository tests |
| HTTP `definition_invalid` | 422 generic envelope | 422 generic message + typed details | `raise_for_generation_failure` | API test |

---

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command | Expected evidence |
|---|---|---|---|
| schema failures expose safe normalized issues | generation service | `uv run pytest tests/statblocks_v1/test_generation_service.py -q` | schema-phase test; no raw input |
| domain failures expose exact validator issues | generation service | same | domain-phase issue equality |
| memory replay returns identical packet and one provider call | memory repository/service | `uv run pytest tests/statblocks_v1/test_memory_repositories.py tests/statblocks_v1/test_generation_service.py -q` | replay equality + call count |
| Firestore replay persists packet | Firestore repository | `uv run pytest tests/statblocks_v1/integration/test_firestore_repositories.py -q` with emulator | round-trip + replay equality |
| generate/revise HTTP 422 contract | route | `uv run pytest tests/statblocks_v1/api/test_candidate_routes.py -q` | exact envelope/details |
| legacy failed records remain readable | repository | focused memory + Firestore tests | missing packet accepted |
| published contract does not drift | contract artifacts | `uv run pytest tests/statblocks_v1/test_consumer_contract_artifacts.py tests/statblocks_v1/test_api_fixtures.py -q` | artifacts/fixtures synchronized |
| focused statblocks v1 regression | subsystem | `./scripts/run_statblocks_v1_tests.sh -q` | no regression |
| diff hygiene | repository | `git diff --check` | clean |

### Minimal live proof

Use the existing internal route with a controlled fake provider or opt-in live provider that returns an invalid definition. Do not require the Mireward operator run inside this Server PR.

Capture:

```text
first POST status/body
same-key replay status/body
provider call count
proof no raw payload appears in either response or operation record
```

The real Mireward Latchling Workbench rerun belongs to the Buddy consumer successor and R0-A closeout.

### Baseline failure protocol

Record base/head for every required command that is already red. Do not call the gate green. Preserve the known unrelated OpenAI-import CI failure only if its identity remains exactly unchanged; otherwise stop.

---

## §8 Required implementation handback

Include:

1. Base and head SHAs.
2. Actual changed paths.
3. Focused diff stat.
4. Every §7 command and exact result.
5. Evidence provenance.
6. First-response/replay packet comparison.
7. Provider call count.
8. Raw-payload non-retention proof.
9. Legacy-record compatibility proof.
10. OpenAPI/generated artifact disposition.
11. Paths outside allowlist or `none`.
12. Baseline failures/waivers.
13. Stop conditions.
14. Confirmation that no repair retry, schema relaxation, prompt tuning, or Buddy code was implemented.

---

## §9 Acceptance rubric

- [ ] One capability delivered: inspectable durable `definition_invalid` diagnostics.
- [ ] Schema and domain failure phases are distinguishable.
- [ ] Issues are bounded, deterministic, typed, and safe.
- [ ] Raw provider payload and exception input are absent from response, logs, and durable operation records.
- [ ] First response and same-key replay expose the same packet.
- [ ] Replay performs no second provider call.
- [ ] Changed-digest replay remains 409.
- [ ] Generate and revise paths follow the same contract.
- [ ] Legacy operation records without diagnostics remain readable.
- [ ] Unknown failures still fail closed.
- [ ] Contract fixtures/OpenAPI/generated artifacts are synchronized where applicable.
- [ ] No successor capability is claimed.

---

## §10 Reviewer protocol

1. Reproduce both schema and domain invalidity.
2. Inspect the persisted operation record, not only the HTTP body.
3. Replay the exact request and compare semantic packet equality.
4. Confirm one provider call.
5. Search response, logs, and durable record for sentinel raw input text.
6. Load a legacy failed operation record without diagnostics.
7. Confirm revise shares the invariant.
8. Reject broad validation changes or automatic repair hidden in the diff.

---

## §11 Re-review protocol

Track every finding against its owning boundary. Re-run the full first-failure → lost-response → replay sequence after each fix; do not verify only the edited serializer or route line.

---

## Stop conditions

Stop and report if:

- safe diagnostics require storing raw provider output;
- durable replay cannot preserve the packet without a migration that breaks old records;
- generate and revise cannot share the same failure snapshot contract;
- another open PR changes candidate-operation persistence or generation error envelopes;
- the implementation requires a second provider call or validation relaxation;
- a required production path falls outside §4;
- the real failure is discovered to be a Buddy request-contract mismatch rather than provider-output validation.

Use the standard stop report with affected paths, public contract, and proposed successor.
