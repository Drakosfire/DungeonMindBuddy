# RETRIEVAL: recover owned clone role profiles

Status: ACTIVE. This serial evaluator slice starts from main
`e9b5ce0cd3701e85259696e13f5b6c8d03e34cab` following #4951. The user
authorized the negative-retrieval goal and one retained disposable App clone.
Current open retrieval and benchmark lanes were checked; none owns this scope.

Provide a restart-safe host-only fixture role profile for the owned App clone.
Before committed changes, durably record the verified clone, profile and both
expected database states. Reconciliation must accept only exactly identified
expected states and otherwise quarantine, including absent or modified policy,
grants, ownership, relation or database identity. Verify workers and sessions
are closed before cleanup. Retain an auditable receipt and keep the clone until
the workstream ends. The implementation must not mutate shared databases,
create cluster roles, derive policy from worker input or expose credentials.

Write set: this brief, evaluator profile/recovery code, focused existing
evaluator tests, and evaluator README. Test setup, interruption windows,
idempotent recovery, drift, identity mismatch and real owned-clone multi-session
behavior. Obtain independent exact-head review. This is not an ordinary-turn
runner, complete acquisition proof, role-escape defense or production parity.
