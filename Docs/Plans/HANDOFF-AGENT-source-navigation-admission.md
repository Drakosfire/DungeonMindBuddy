# AGENT — durable native source navigation admission

ACTIVE serial PRIME slice; basef2ce54282ea8c1d6aef9c2e3dd59de11d2ce91cf,
branch codex/native-source-navigation-admission, existing buddy-context-loop checkout.
Parent exact-native-source-sections design #1631; prerequisite verifier #1632 merged.
One Bugbot-reviewed implementation PR, PRIME merge. No serving/provider/source-body
IO, retained mutation or route/tool activation in this slice. Census2026-10-22:
no overlapping APP ledger lane. No new table: use existing JSON execution
ledger with distinct policy capability and event discriminant. Owning PostgreSQL
checks require migration0053 to admit only the explicit new capability/event;
historical payloads
retain their exact serialized policies.

Outcome: persist metadata navigation authorization only after APP joins the trusted
producer proof to an earlier actual Graph donor, exact current provider outcome,
frozen receipt/policy, effective pin, World binding and claim fence. This is the
first durable authorization gate, not a successful body/section read or citation.
The native verifier owns Core response truth; APP independently validates stored
membership/ordering/equality. Capability remains inactive in ordinary Plan Jev and
native Play Hermes until body receipts, strict writer/completion, history and UI
citation/opener consumers are paired. No new controller migration or old fallback.

Writes: this handoff; HANDOFF-AGENT-source-origin-verifier.md settlement;
src/application_state/agent_conversation/{types.py,service.py,native_source_navigation.py,plan_jev_decision.py};
tests/application_state/test_native_source_navigation_postgres.py;
src/application_state/migrations/versions/20261022_0053_native_source_navigation.py.
Version explicit Plan Jev/native Play capability subclasses, preserving old policy
serialization. Add one dedicated navigation authorization event with unique ID,
provider/receipt/policy/source binding and full structured origin proof/hash.
Reject missing/foreign/changed/later donor, inactive/unknown metadata, exact revision
or digest mismatch, unacknowledged/unknown provider, acquisition after writer, stale
claim/attempt/revision and event rebinding. APP never accepts it as Graph/source
read evidence, nor loads source bodies. Existing storage/event ceilings apply;
no arbitrary new text/token cap. Prove actual APP append→reload and replay/conflict
for Plan and Play, negative scope/proof/fence cases and unchanged historical paths.
Review exact cumulative diff and run owning APP and producer tests independently.
