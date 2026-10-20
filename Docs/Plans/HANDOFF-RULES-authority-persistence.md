# R2A — Rules authority persistence prerequisite

**Status:** ACTIVE. PRIME activates the independently useful ApplicationState foundation under operator goal and closed decision PR1504, independently approved13b2882be7d28f1004ed37fa54725e6b217eddc1/merged6d8d340fc23e2e4b25aea0341b74eb7ae2c42808. No Buddy tool activation or R2B worker dispatch.

## Lane and authority

Serial, one implementation PR. Base6d8d340fc23e2e4b25aea0341b74eb7ae2c42808, branch codex/rules-authority-persistence, existing buddy-context-loop checkout. No new checkout/environment/runtime preview. Closed contract: DECISION-RULES-agent-authority-v1.md. Runtime owner PRIME; current accepted UI5202 index-CLjHpgLN.js/defaultindexSHA70403db8ed3b465add90b130c218c89fae188e424bbe7d60ccec33c029f81865; API8000 service dungeonmindbuddy-dogfood-api-jev-7bc8c515.service, source buddy-main-e778b3f0/source, same established interpreter. R1 accepted user lookup stays available. No active implementation PR collides with ApplicationState lease; older763–765 closed as superseded. Combat1367 is an unactivated adoption contract, not a concurrent Rules writer.

## Exclusive expected write lease

- `src/application_state/agent_conversation/rules_authority*.py` (new strict types, pure validation, SQL store/operations as needed).
- `src/application_state/agent_conversation/types.py`, `service.py`, `repository.py`, `__init__.py` only for explicit mixed read/result/claim/history dispatch and locked validation reuse. Current non-Rules behavior must remain.
- `src/application_state/migrations/versions/20261020_0041_rules_authority.py` (new). Current sole Alembic head20261019_0040; no historical migration edits. New ledger table+turn discriminator per closed decision, RESTRICT deletion/refuse downgrade of retained Rules data.
- `tests/application_state/test_rules_authority*.py`, `tests/test_rules_authority*.py` (new); existing exact affected ApplicationState tests only if current typed contract/SQL observations change legitimately. No compatibility fixtures.
- This handoff plus backward settlement in `Docs/Plans/HANDOFF-RULES-agent-query.md` and `Docs/Plans/DECISION-RULES-agent-authority-v1.md`; no forward completion claims.

No API routes, AgentRuntime/Hermes/plugin/tool whitelist, source corpus, Rule graph, provider, UI or dependency edits. If a required invariant crosses this lease, return a bounded steward decision before writing outside it.

## Implementation boundary

Implement the closed Scope/Support/events/budgets, immutable source identity and actual producing-input joins; rules execution current-claim CAS/idempotence and atomic completion; mandatory persisted answer-composition discriminator; explicit MixedCompletedTurn/base projection before ordinary Turn parsing; ordered codepoint segment map/source mapping and bounded accepted summary/seal; completed replay before running-claim gate; exact cited historical support projection. Existing Graph/Build validators run on exact base subsequence. Unclaimed retains genuine Graph authorization+acknowledged outcome/envelope join, no fake completion/binding/Graph grounding. Missing/corrupt mixed bindings fail integrity rather than falling back.

All get/list/lock/claim-completed/replay/history paths must classify raw row marker first. Ordinary history projects bounded accepted metadata with SQL byte CASE before transfer, not full Rules payload or repeated claim prose. Existing `list_turns` calls `_turn_from_row`→`_turn_references` per row; when adapting that owning read boundary, batch admitted-turn reference metadata where necessary and prove bounded query counts without changing World/conversation/sequence ordering. Exact reads use only admitted row identities; never accept unbounded caller turn lists. No cross-scope settled cache.

## Tests and delivery gates

Use existing `tests/application_state/conftest.py` disposable database fixture and safe-name guards. Its established admin on54329 was read-only-checked reachable PostgreSQL16; no test DB created during design. Tests create only generated dungeonbuddy_app_state_test_* databases, migrate and remove their own database. Never use production World/cutover databases or mutable user state as a fixture.

Pure strict models: unknown fields, Unicode/hash/range/order/delimiter/byte budgets, event sequencing/idempotence, producing request joins and every base disposition. Real PostgreSQL: migration head/empty downgrade, refuse downgrade with any retained Rules row, claim expiry/CAS/attempt/World isolation, full rollback across base+Rules completion, accepted replay/conflict without renewed claim, ordinary baseline unchanged, corruption in marker/binding/state/source digest, all get/list/claim/history paths, bounded summary/one-support SQL reads and batch query counts. Include actual Build mixed full-text/base-subsequence and graph-enabled unclaimed cases; no mocked service-only proof for transactions.

Inspect cumulative diff, meaningful affected suites, independent exact-head review, commit/push/assigned PR and authorized merge. Runtime migration/source adoption only after isolated migration+rollback and recoverable backup/restore witness, current schema/process/claim lease re-anchor, protected17/nonterminal state capture. R2A tool remains disabled and current code has no producer of live Rules rows; downgrade must still refuse nonempty Rules storage. Preserve seven expired nonterminal Agent rows and all user data. No new provider calls during this prerequisite. Verify API/R1 user lookup health and retained state after any authorized restart; do not claim Agent lookup complete. R2B requires a separate ACTIVE handoff after accepted foundation.

## Steward amendment before event implementation

Same-lease closed decision amendment pins derived query_observed.presentation_utf8 with internal exact raw-output SHA/length/closed capsule proof, sum-derived counters,1024byte terminal-diagnostic reserve and explicit support_capsules packet field. Architecture acknowledged this as necessary bounded metadata, not a new capability. No raw quoted packet is added to persisted ledger/history. This amendment is covered by the eventual cumulative source review. Initial pure Scope/Support/composition/map/binding28tests pass; no event/DB/runtime/tool activation is implied by that result.

## Incremental author evidence (not completion)

Initial strict source/composition/binding values28puretests PASS. New0041 migration9real disposable PostgreSQL tests PASS: existing current submitted-intent turn survives empty downgrade/re-upgrade, retained Rules row refuses downgrade, SQL scope/type/event/byte caps and completed-only mixed marker. First fixture omitted the current required submitted intent and correctly failed; fixture now supplies valid current Index intent, no compatibility acceptance added. Fixture-created safe databases were removed by their existing teardown. Live runtime/source/schema unchanged; event proof, mixed transaction/read/replay integration and backup/restore/adoption remain required before review/delivery.
