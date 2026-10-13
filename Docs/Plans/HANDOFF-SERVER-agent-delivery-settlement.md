# SERVER — settle non-ok Agent delivery

Status: ACTIVE

## 1. Primary question

Does a failed already-authorized Plan Agent runtime result settle the owned
durable turn as interrupted, retaining the provider uncertainty and preventing
automatic redispatch, instead of leaving the conversation running indefinitely?

## 2. Authority and predecessor

PRIME authorized this one bounded repair on 2026-10-13. Base is Buddy remote main
`c4a81c6661dd292c6adb9d314ce4d154d1e78352`, after reviewed #1120 merged exact
`e8a5751b`. PRIME explicitly assigned authoring/pinning this ACTIVE handoff in the
isolated implementation lane before code changes; this overrides the older
main-first handoff procedure for this incident. No merge/deployment authority.

State-authority sync set: this handoff records the completed #1120 predecessor
only; no unrelated roadmap or architecture claims change.

## 3. Topology and lane

PR topology: serial. One SERVER delivery-settlement PR against main.
Branch: `codex/server-agent-delivery-settlement`.
Isolated checkout: `/tmp/buddy-agent-delivery-settlement`.
Open #1014 is older inactive rollout preparation and does not lease these paths.
Open RULES/DEMO/BACKLOG work is independent. #1120 is merged. The serving Buddy
checkouts and their local UI edits are outside this lane.

## 4. Write lease

| Path | Purpose |
| --- | --- |
| Docs/Plans/HANDOFF-SERVER-agent-delivery-settlement.md | Authority and evidence |
| apps/live_control_server/services/agent_turn_service.py | Settle non-ok runtime result through existing owner fence; safe phase status |
| tests/test_agent_turn_service.py | Fake-runtime failure and normal-completion witnesses |
| tests/application_state/test_agent_conversation_postgres.py | Fresh/stale/duplicate and expired-authorization owner fences |

## 5. Exclusions

| Path | Reason |
| --- | --- |
| apps/live_control_server/services/hermes_graph_agent_host.py | No proven decoder defect; separate lease required |
| out/hermes-agent | No SDK/provider plumbing changes |
| src/application_state | Existing owner contract/fences must suffice |
| apps/live-control-ui | Preserve owner edits; no UI repair lease |
| pyproject.toml / uv.lock | No dependency changes |

No provider calls, replay, invented assistant, new public contract, live database
test, runtime restart/deployment, Graph publication, or direct SQL status write.
The separately released single retained-turn recovery used the accepted owner
expired-authorization path; this source PR does not execute recovery again.

## 6. Stop conditions

Stop if existing owner failure fences cannot preserve the ledger safely, if a
leased file collides with new active work, or if implementation requires a new
APP schema, host/SDK/UI behavior, or public contract. Preserve uncertain outcomes.

## 7. Verification

Use the accepted existing Python 3.13 environment without dependency installs.
Real PostgreSQL is a dedicated disposable tmpfs container/database, never APP.

```bash
PYTHONPATH=src:. "$DMB_REPAIR_PYTHON" -m pytest tests/test_agent_turn_service.py -q
PYTHONPATH=src:. "$DMB_REPAIR_PYTHON" -m pytest tests/application_state/test_agent_conversation_postgres.py -q -k 'delivery_settlement or expired_authorized_execution'
"$DMB_REPAIR_PYTHON" -m ruff check apps/live_control_server/services/agent_turn_service.py tests/test_agent_turn_service.py tests/application_state/test_agent_conversation_postgres.py
git diff --check
```

Required witnesses: three received responses then fourth unknown/non-ok result;
normal completion unchanged; one owning failure invocation, preserved ledger,
no assistant and no redispatch; real-PG fresh/stale/duplicate fences and the
existing expired prior-authorization branch. Diagnose phase status only from an
existing safe host span. Inspect full cumulative base→head diff and path lease.

## 8. Handback

Report exact base/head, tests, cumulative diff, deviations, risks and PR URL to
PRIME for independent review. No source-only runtime adoption is implied.

## 9. Acceptance

- Failed non-ok delivery settles the active owned turn through `fail_turn` with
  `interrupted=True`, preserving every execution event and uncertainty.
- Expired/stale fences fail closed; duplicate owner settlement is idempotent.
- Normal completion and prior provider authorization remain truthful.
- No provider replay, invented answer, live-state test, or unleased change.
- Token proposed only when evidence passes:
  `SERVER_AGENT_DELIVERY_SETTLEMENT_IMPLEMENTED`.

## 10. Implementation evidence

Handoff pin before implementation: `36fd5c9519df5a6439b538e2d25c8305da93fe2f`.
Implementation commit: `d848363f7128d32ce55aa6b771f286d9d769cb2d`.

- Complete `tests/test_agent_turn_service.py`: 109 passed; two existing Pydantic
  field-shadow warnings. This includes normal completion, pre-freeze/no-claim
  no-mutation, four authorized attempts with three received and one unknown,
  stale/expired fake fences, public history uncertainty and privacy diagnostics.
- Focused PostgreSQL command above: 3 passed, 37 deselected. The production
  settlement helper exercises real fresh/expired owner fences; stale rejection,
  duplicate idempotence and prior-authorization nonreclaimability are proven.
  PostgreSQL 16 used a dedicated 512 MiB tmpfs container on an isolated local
  port with `DMB_APPLICATION_STATE_TEST_DATABASE_URL` pointing only to that
  container. Per-test databases and the container were removed after proof.
- Existing private Python 3.13 environment reused; no package installation.
  Changed-file Ruff and `git diff --check` pass. No tracked repository CI workflow
  or additional Python typecheck gate exists in this base.
- Cumulative base→implementation lease comprises this handoff and exactly the
  three leased Python files. No host, SDK, APP contract, UI or dependency changes.

Failed delivery now invokes owner `fail_turn(..., interrupted=True)` exactly once
only after the adapter acquired a claim. It preserves execution events, records
the existing unknown outcome as `provider_outcome_unknown`, and keeps the existing
HTTP error shape. A stale/expired fence remains indeterminate and requires owner
reconciliation; it is never overwritten. Deterministic guard exhaustion retains
its previous failure behavior.

The endpoint exposes interruption through ordinary durable history. DOGFOOD owns
the separately discovered client pending-state reconciliation repair. This PR
does not establish the SDK stream failure subtype or guarantee a final answer.
No provider run, replay, runtime adoption or independent review occurred here.

Implementation token proposed: `SERVER_AGENT_DELIVERY_SETTLEMENT_IMPLEMENTED`.
PRIME owns independent acceptance and any later merge/deployment release.
