# AGENT: isolate local browser sessions by serving profile

Status: ACTIVE under PRIME's authorized main5876/dogfood5202 coexistence and usable Build/Agent goal.
Base: `c6a560e688460171cd51bcefe1ebf6acd599a5c1`.
Lane: `codex/local-session-profile-isolation`, `/tmp/prime-recap-mention-boundaries`.
Topology: serial, PRIME implementation and ARCHITECTURE independent review.

## Invariant and evidence

Two authorized local serving profiles on the same browser hostname must retain
independent sessions despite cookies being shared across ports. Actual synthetic
HTTP reproduction on this base: bootstrap A5202/8000=200, B5876/8002=200, then A=401;
the cookie jar contains only the shared `dmb_local_graph_session` cookie.
This is distinct from DOGFOOD preview5206's unconfirmed origin mismatch.

Choose a deterministic cookie name from canonical configured UI origin and API
authority including ports, never from client headers. The suffix is public routing
metadata, not authentication. Bootstrap, require and revoke use the same name;
foreign/renamed cookies fail even when profiles share a secret and store: bind
session-store and CSRF HMACs to the canonical profile namespace with structured
encoding and distinct purpose tags (ARCHITECTURE approved). Preserve
exact peer/Host/origin/CSRF, expiry, private store and cookie security attributes.
No old-cookie fallback. Existing sessions re-bootstrap once after rollout through
the existing trusted auth-recovery path; no credential regeneration or broader
origin/host allowlist. Explicit revocation stays explicit.

## Exclusive write set

- This handoff.
- `Docs/Plans/HANDOFF-AGENT-selected-knowledge.md` (settle #1213).
- `apps/live_control_server/services/agent_graph_local_session.py`
- `apps/live_control_server/routes/agent_graph_local_session.py`
- `apps/live_control_server/services/agent_graph_auth.py` (existing cookie-presence guard must use the same derived name; no bearer or authorization-policy change).
- `tests/test_agent_graph_local_session.py`

No UI, provider, schema, serving, credential or retained session-store write lease.
Tests use synthetic secrets and disposable stores. DOGFOOD owns disjoint Build UI.
ARCHITECTURE approved this contract before implementation.

## Verification

Real shared cookie jar: A bootstrap, B bootstrap, both remain valid; revoking either
preserves the other. Wrong origin/Host/peer/CSRF, foreign-renamed, expired and revoked
sessions reject. Issue/revoke touch only the profile cookie; security flags/path
remain unchanged. Canonical config yields stable names; distinct configured
profiles differ; invalid/missing config remains fail closed under existing policy.
Review cumulative base→head; carry to one PR and obtain exact independent review.

Author verification: 21 local-session/auth/launch-profile tests pass, including
real shared-cookie-jar bootstrap/revoke and shared-secret/shared-store renamed
cookie/foreign-CSRF rejection with original-session survival. Ruff and cumulative
diff checks pass. No existing operator session or serving process was changed.
