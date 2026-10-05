# HANDOFF — APP-STATE: Plan World Graph context receipt v1

**Status:** ACTIVE — direct operator authorization recorded 2026-10-05.
**Design:** [DESIGN-APP-STATE-plan-world-graph-context-receipt-v1.md](DESIGN-APP-STATE-plan-world-graph-context-receipt-v1.md).
**Pinned base:** Buddy `main@6240620423989ce0d132c26861c1e0b09cab3053` (PR #921).
**Schema head:** `20261004_0015`; implementation migration is `20261004_0016` with `down_revision=20261004_0015`.
**Branch/checkout:** `codex/app-state-world-graph-context-receipt` at `/tmp/agent-graph-receipt`.
**Topology:** serial: APP-STATE publication/implementation → SERVER API/admission/binding integration → DEMO consumer.
**PR topology:** one APP-STATE implementation PR containing the published contract and its bounded persistence implementation. Merge remains a separate decision.
**External state:** isolated disposable PostgreSQL fixture only. No operator database, provider, Graph, service, process, or runtime access.

## Mission

Persist one immutable, server-validated Graph context receipt on the canonical World conversation turn for explicit auto_plan_world Plan Ask. Preserve graphless v1 request/fingerprint semantics exactly when that policy is absent. Keep the complete committed Plan basis and optional independent card focus; do not persist dirty draft text or raw Graph/source bodies.

## Active contract

Implement the accepted design in DESIGN-APP-STATE-plan-world-graph-context-receipt-v1.md. Core owner invariants:

1. A distinct strict PlanWorldGraphContextReceiptV1 is a nullable typed field on agent.turn, not an invented interpretation of legacy HistoricalReference rows. Existing graph references continue to denote managed product scope; the new receipt separately records native World ID and binding version.
2. Explicit auto_plan_world requires a new submitted-intent v2 policy representation and prohibits simultaneous v1/v2 representations. Although the current request model types submitted_intent_v1 as optional, ordinary new-turn acceptance rejects missing intent; preserve that service behavior and existing replay/error behavior for older no-intent rows. New accepted turns require exactly one valid intent: v1 without policy, or v2 with explicit auto_plan_world. No-policy requests retain exact existing serialized shapes and fingerprints. Optional card focus is separately typed and bound to the exact committed Plan basis.
3. The immutable pre-dispatch receipt distinguishes the retrieved/admitted candidate packet from what was dispatched. It stores `retrieval_packet_sha256`, candidate assertion/relationship/evidence IDs and retrieval/sufficiency/coverage/truncation statuses; then `packet_disposition` (`included` or `omitted_insufficient`) with reason, `dispatched_packet_sha256` and exact dispatched IDs (null digest/empty IDs when omitted), plus `assembled_input_sha256` for the entire provider envelope. It also stores the exact Plan basis, managed/native binding and Graph pins, model/tokenizer/version/output-reserve accounting, and immutable evidence_mode=metadata_only/source_opened=false. The completion citation map appears later inside the typed completion envelope and may reference only dispatched IDs.
4. The service freezes policy-bearing intent when present and receipt in APP-STATE before provider dispatch, rejects same-key policy/basis/card-focus changes, and completes answer, typed segments, answer basis/status, citation map, and unchanged receipt atomically.
5. Completed replay returns stored answer, receipt, and completion envelope before current Plan, Graph, binding, or provider reads. A response-only delivery_replay boolean does not alter the stored outcome. Pending retry validates the original managed/native/binding tuple and exact revision, reconstructs the packet with the recorded serializer/policy and verifies its digest; it never repins or mutates the receipt.
6. Legacy turns remain unchanged with null new receipt and their original fingerprints. No raw source bodies, Graph prose dumps, prompt payloads, or dirty Plan text are stored.
7. Ask while the editor is dirty uses exact committed Plan content; response and history disclose that unsaved edits were excluded.
8. A managed/native binding, exact-revision, Graph-read/evidence-validation, provider-budget, or receipt-freeze failure returns a typed pre-dispatch failure with no receipt, provider call, or automatic downgrade. After a valid receipt freezes, empty/insufficient evidence sets `packet_disposition=omitted_insufficient`, sends full Plan/history but no Graph claim payload, and may produce `plan_only_insufficient_evidence`. Sufficient available evidence with no Graph-claim answer segments may produce `plan_only_graph_unused`; this means only that the output contains no Graph-attributed claim and does not assert model-internal non-use. Both Plan-only outcomes have null citation maps. Sufficient complete evidence used by one or more mapped Graph claims uses `graph_grounded`; sufficient incomplete/truncated evidence used by mapped Graph claims uses `graph_grounded_partial` with incomplete-coverage disclosure. Both grounded statuses require non-empty validated maps drawn only from dispatched IDs. A separate policy-absent Plan-only Ask requires explicit user action and a new idempotency key.
9. The receipt persists `receipt_serializer_version=canonical-json-utf8-v1` and `context_receipt_sha256`, computed over all typed pre-dispatch receipt fields except that digest itself. The hash covers evidence status, Plan/binding pins, `retrieval_packet_sha256`, exact disposition/reason, `dispatched_packet_sha256`/IDs, retrieval/sufficiency/coverage/truncation statuses, and full provider-envelope accounting plus `assembled_input_sha256`; completion outcome/segments/map and response-only delivery_replay are outside this hash.
10. The nullable versioned completion envelope stores `answer_context_status` (`graph_grounded | graph_grounded_partial | plan_only_insufficient_evidence | plan_only_graph_unused`), `answer_basis`, ordered answer_segments (`graph_claim`, `plan_claim`, `proposal`, `connective`), and the validated citation_map bound to the receipt digest. `graph_claim` segments carry claim ID/text/target/pin/refs; `plan_claim` is attributed to the committed Plan; proposals are labelled as invented ideas; connective segments are nonfactual. SERVER derives answer_basis as `committed_plan` or `committed_plan_plus_world_graph` and validates it and status/map consistency against segments, receipt evidence/coverage, and dispatched IDs. Available-but-unused Graph evidence has `plan_only_graph_unused`, not insufficient status; this is output attribution, not a claim about internal model attention. Delivery replay preserves the stored completion unchanged.

## Active APP-STATE path allowlist

The following paths are the exclusive write lease for this slice:

- `Docs/Plans/DESIGN-APP-STATE-plan-world-graph-context-receipt-v1.md`
- `Docs/Plans/HANDOFF-APP-STATE-plan-world-graph-context-receipt-v1.md`
- `Docs/Plans/HANDOFF-APP-STATE-world-agent-conversation-provenance-v1.md` (settle completed PR #862 lease)
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/agent_conversation/service.py`
- `src/application_state/migrations/versions/20261004_0016_agent_turn_graph_context_receipt.py`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`
- `tests/application_state/test_agent_conversation_provenance_migration.py`
- `tests/application_state/test_plan_action_dialogue_postgres.py` (update the migration-head assertion after activating 0016)

Migration 0016 adds only nullable `graph_context_receipt` JSONB, `completion` JSONB, and `submitted_intent_fingerprint_v2` TEXT with a 64-hex check. No new table is proposed. No other file may change; if implementation needs another path or migration head, stop and return the exact deviation to PRIME before editing. SERVER request models/routes/service/tests and DEMO UI/history/tests remain separately owned.

## Re-anchor and lease settlement

Re-anchored fetched Buddy `origin/main` at `6240620423989ce0d132c26861c1e0b09cab3053` (PR #921); that merge publishes DEMO roadmap/design documentation only. The current open-PR census includes SERVER contract publication PR #922, whose exact changed path is `Docs/Plans/HANDOFF-SERVER-plan-world-graph-context-api-projection-v1.md`; it grants no implementation lease and does not overlap this APP-STATE allowlist. #917 defers production Graph retrieval and receipts; #914 owns Plan card presentation. SERVER owns the serial API/provider successor, while APP-STATE exclusively owns the persisted receipt and completion schema on this handoff's paths.

The stale provenance handoff from PR #862 still said ACTIVE and claimed overlapping types/repository/test paths. PR #862 merged at `cfec63c6df9bd14aa7a1b5963266f926c729f8ab`; the code is already on main. This PR settles that old handoff before touching any overlapping path. AGENT-INTERACTION PR #865 merged at `1c0320d18c53037308cd7412719fb3e2f0610d99` and released its separate test-file lease. The suspended `agent-world-conversation-backend` checkout remains historical and untouched.

## Migration and backward compatibility

No historical migration is edited. The candidate migration is additive from the then-current code head and leaves every old turn's receipt null. It must preserve existing turn IDs, answer text, lifecycle, provenance, request/idempotency hashes, and v1 intent fingerprint bytes. Do not infer native IDs, binding versions, Graph packets, or citations from old rows. Downgrade must not silently discard a non-null receipt; either refuse rollback while receipts exist or require an explicitly accepted data-loss procedure.

No operator database is an implementation fixture. Do not upgrade, back up, restore, restart, or verify the operator database. Migration evidence uses only an isolated disposable database built from a populated 0015 fixture.

## Required APP-STATE verification

- strict typed receipt and intent validation; prove new accepted turns require exactly one valid v1/v2 intent, preserve the missing-intent acceptance error and old no-intent-row replay behavior, and reject contradictory simultaneous representations;
- status-matrix tests distinguish hard pre-dispatch/read/budget/freeze failures (no receipt/provider call/no downgrade), frozen insufficient evidence (plan_only_insufficient_evidence, no dispatched claim payload, labelled Plan-only/null citation map/no Graph claims), sufficient-but-unused evidence (plan_only_graph_unused without claims about model-internal attention), sufficient complete evidence used in Graph claims (graph_grounded), and sufficient truncated evidence used in Graph claims (graph_grounded_partial with bounded mapped claims and incomplete-coverage disclosure); verify retrieved/dispatched packet digests, exact dispatched IDs, whole-receipt hash canonical bytes and field coverage;
- versioned completion-envelope tests validate ordered typed segments, answer_basis derivation, exact status/map constraints against dispatched IDs, exact replay readback, and delivery_replay being response-only;
- pre-change golden vectors proving exact request_fingerprint, idempotency_fingerprint, and submitted_intent_fingerprint_v1 equality for graphless Plan Ask, graphless Plan Ask with typed card focus, and generic Graph modes; explicitly exclude new nullable policy/v2 fields from legacy request_fingerprint input;
- populated 0015 upgrade, null legacy receipt preservation, malformed receipt rejection, fresh-service exact readback/projection;
- receipt freeze before dispatch and atomic answer/completion-envelope/receipt completion;
- same-key changed policy, Plan basis, or card target conflict, including concurrent reservation/acceptance races;
- completed replay returns stored receipt and completion envelope with no context/provider dependencies;
- pending retry verifies original binding/pin/packet digest and fails closed without repin;
- run focused service, PostgreSQL, and migration suites against an isolated fixture; preserve full failure output and report skips/inherited failures.

SERVER must separately prove managed-to-native resolution, binding fence, exact Graph evidence validation and zero-read replay ordering. DEMO must separately prove committed Plan use, card focus retention, truthful disclosure, and history rendering.

SERVER's provider-envelope witness must prove that retrieved candidate identities/digest and dispatched identities/digest are distinct when applicable; `omitted_insufficient` sends no Graph claim payload while retaining full committed Plan/history and the explicit omission/status instruction; the assembled-input digest matches the exact envelope dispatched; and completion citations reference only dispatched IDs.

## APP-STATE verification evidence

- `ruff check` passed for all leased Python source, migration, and test paths.
- Against an isolated tmpfs PostgreSQL container and disposable per-test databases, the focused APP-STATE service, PostgreSQL, provenance migration, and Plan action PostgreSQL suites passed: 52 passed. This includes fresh-service receipt/completion readback, completed receipt replay, malformed receipt rejection, downgrade refusal with a non-null receipt, and legacy null/fingerprint preservation.
- A final focused rerun of the receipt round-trip, graphless request-fingerprint compatibility, and populated legacy migration tests passed: 3 passed.
- No provider, Graph service, operator database, or persistent database volume was used.

## Stop rules

- No operator migration, service restart, live provider/Graph call, source-opening behavior, or merge is authorized. Run PostgreSQL verification only against an isolated disposable fixture populated at code head 0015.
- Stop and report the exact deviation if 0015 is no longer the migration head, if another active lease claims a path, if the storage seam requires a new path/table, or if byte-compatible legacy fingerprinting, immutable receipt persistence, atomic completion, or completed replay without current-state reads cannot be proved.
- SERVER owns policy request admission, Graph resolution/retrieval, receipt construction, provider-envelope hashing/budget, citations and API projection. APP-STATE persists typed payloads and lifecycle; it does not resolve or certify Graph facts. DEMO owns committed-Plan disclosure and presentation.
