# HANDOFF — HOSTED: DMS principal adapter

**Status:** SETTLED — PR #1508 merged at `4ba6de08c33d9f8870d6c2857b585ce72f97d903`.

**Steward:** Hosted Buddy v1 implementation task

**Owning flow:** `HOSTED`

**Original implementation base:** `origin/main` at `04e44374300a985e247941fb03de6bdaa01662b3`.

**Current Buddy main:** `origin/main` at `4ba6de08c33d9f8870d6c2857b585ce72f97d903`, the confirmed merge of PR #1508.

**Design authority:** DungeonOverMind plan `Docs/Plans/PLAN-buddymind-hosted-v1.md`, design commit `98454eb41a096462d0650a15edaa34b3e679b0db`. ARCHITECTURE cleared this exact design in thread `01a086f2-c457-7b10-b753-df6063cab1ce` on 2026-10-20. The disposition is thread-only, not a GitHub review.

**Authorization:** Alan authorized this bounded adapter, offline verification, and publication of its implementation PR after the design clearance. Merge, route enablement, and deployment are separate and are not authorized.

**Lane:** `codex/hosted-v1-dms-principal-adapter-v1-20261020` at `/home/drakosfire/Projects/DungeonOverMind/task-workspaces/hosted-v1-plan-order1-20261020/DungeonMindBuddy-parent/checkout`

**Topology:** Serial within `HOSTED`; one implementation PR, title `HOSTED: add unmounted DMS principal adapter`. No direct push to `main`.

## Capability and invariant

Add a request-scoped, injectable resolver that can turn the existing DMS session cookie into a typed principal through server-to-server introspection. This slice only defines and tests the adapter. It does not install it into an API route or enable `hosted_owner`.

- Read only the `dungeonmind_session` cookie from the synthetic or future request.
- Call only `GET /api/auth/current-user` at a trusted, constructor-supplied fixed HTTPS DMS origin. Reject origin values with userinfo, non-root paths, query, or fragment; request data cannot select the destination.
- Use a five-second overall deadline; make one request only; disable redirects. Timeout, transport error, redirect, non-200 response, malformed body, or missing/empty/non-string top-level `sub` yields no principal.
- A valid response yields only the DMS response's stable Google `sub`. Ignore `X-User-ID` and all other caller identity headers. Their presence alone grants no principal; with a valid DMS cookie they must never override the returned `sub`.
- Do not log or persist the inbound cookie, retain it in adapter state, or send it to any other origin. Do not add an auth cache, session store, token, user database, new secret, configuration switch, or retry.
- Preserve existing `local_operator` and local-session behavior. Do not modify DMS, route registration, `main.py`, auth guards, existing local-session modules, UI, deployment, or production configuration.
- Real hostname/path selection and browser cookie-delivery proof remain a precondition for later route wiring. Audience remains undecided.

## Exclusive write set

- `Docs/Plans/HANDOFF-HOSTED-dms-principal-adapter-v1.md` (this lane authority)
- `apps/live_control_server/services/dms_principal.py` (new)
- `tests/test_dms_principal.py` (new)

Do not edit other files without returning to the steward. In particular, current Buddy main has a separate `ACTIVE` `HANDOFF-AGENT-local-session-profile-isolation` whose write lease includes `apps/live_control_server/services/agent_graph_auth.py`, local-session service/routes, and `tests/test_agent_graph_local_session.py`. This lane creates new files and must not touch that lease. No database, provider, service, port, or retained runtime state is used.

## Verification

Use only an injected HTTPX mock transport and synthetic Starlette requests/cookies. Focused tests must cover:

1. A valid response returns exactly its `sub` and the request is one GET to the fixed DMS endpoint with the named cookie.
2. An `X-User-ID`-only request yields no principal; with a valid DMS cookie, a conflicting `X-User-ID` cannot replace the DMS `sub`.
3. Missing cookie, 401, 5xx, timeout, transport failure, redirect, malformed JSON/object, and missing/empty/non-string `sub` fail closed.
4. Insecure or non-origin URL input fails closed without a transport call; redirect response is not followed; transport is invoked once (no retry).
5. The synthetic cookie is absent from logs and persistent adapter state and is sent only in the request to the fixed DMS origin.

Inspect the project test configuration first. Run the focused test file with the repository's pinned Python/test environment and `git diff --check`. These tests must remain offline and must not use PostgreSQL, real DMS, a live provider, or production data. Record exact command and result in the PR. The code PR requires independent ARCHITECTURE review of its exact final head. Do not merge or deploy.

## Completion boundary

PR #1508 was merged from exact reviewed head `a43004aef8afecf6241c3584c1e4948a80dffc30` on 2026-10-20; GitHub confirms merge commit `4ba6de08c33d9f8870d6c2857b585ce72f97d903`, now the Buddy `origin/main` anchor. The adapter and tests are part of main, but the resolver remains unmounted, `hosted_owner` remains disabled, and no deployment or live configuration change occurred. This handoff is settled as implementation authority. Cookie delivery, route authorization, CSRF, persistence, operator configuration, and launch rehearsal remain later gates.
