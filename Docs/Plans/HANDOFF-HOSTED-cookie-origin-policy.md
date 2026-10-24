# HANDOFF — HOSTED: cookie-authenticated Origin policy

**Status:** SETTLED — PR #1509 merged on 2026-10-20 at `8bcbe69d1b6d7c70734927a314f4ded05846fb76`, from ARCHITECTURE-approved head `830c7eefed9d6ad48a8f87575be9b25bca5db784` (original base `4ba6de08c33d9f8870d6c2857b585ce72f97d903`). The Origin helper remains unmounted; this handoff grants no route-wiring, live configuration, or deployment authority.

**Steward:** Hosted Buddy v1 implementation task

**Owning flow:** `HOSTED`

**Implementation base:** `origin/main` at `4ba6de08c33d9f8870d6c2857b585ce72f97d903` (merged PR #1508). **Post-merge Buddy main:** `8bcbe69d1b6d7c70734927a314f4ded05846fb76` (merged PR #1509).

**Design authority:** The cookie-auth Origin policy was approved as design text in ARCHITECTURE thread `01a086f2-c457-7b10-b753-df6063cab1ce`, review 2, on 2026-10-20. That approval did not activate implementation. This handoff is the operator-authorized activation proposal; implementation may begin only after ARCHITECTURE approves this pinned handoff revision.

**Original slice authorization:** Alan authorized the bounded offline helper implementation, focused tests, review, and PR publication. That authorization did not include merge, route wiring, live configuration, DMS calls, production writes, or deployment. The later user-selected hostname and managed-population intent are recorded in §2; they do not activate route integration.

**Pinned authority ref:** This file at approved initial commit `7fda8f44e8110d26057a60043c855975ead5b505`; that revision is an ancestor of subsequent implementation commits on this same branch/PR. Subsequent implementation updates must remain within this handoff's exclusive write lease.

**Lane:** `codex/hosted-cookie-origin-csrf-v1` at `/home/drakosfire/Projects/DungeonOverMind/task-workspaces/hosted-origin-csrf-20261020/worktrees/buddy-origin-csrf-v1`.

**Settled topology:** The serial helper PR `HOSTED: add cookie-authenticated Origin policy` is merged. The helper remains unmounted and must not be exposed without a later route-wiring authority and the gates in §7.

## 1. Capability and invariant

Add one pure, injectable policy helper for unsafe requests whose authentication has already been selected as browser-cookie authentication:

> A cookie-authenticated unsafe request proceeds only when it has exactly one syntactically valid, non-opaque `Origin` equal to an exact canonical origin in trusted server configuration. The helper rejects before the route can mutate state.

This is an unmounted primitive. It does not authenticate or resolve identity, set CORS, choose a hostname/audience/origin, inspect forwarded headers, authorize World membership, change cookies, or enable `hosted_owner`.

## 2. Re-anchoring and predecessor settlement

- Current Buddy `origin/main` is `8bcbe69d1b6d7c70734927a314f4ded05846fb76`, the confirmed merge of PR #1509 (reviewed head `830c7eefed9d6ad48a8f87575be9b25bca5db784`) on top of PR #1508 merge `4ba6de08c33d9f8870d6c2857b585ce72f97d903`. The DMS principal adapter and Origin helper remain unmounted; no launch readiness is implied.
- ARCHITECTURE approved this ACTIVE handoff at exact head `7fda8f44e8110d26057a60043c855975ead5b505`, then withdrew its initial main-landing HOLD after reconciling current Buddy policy. It found no specific HOSTED main-only rule.
- ARCHITECTURE approved the final helper head after the IDNA and method-token corrections. PR #1509 was merged through the ordinary guarded workflow; its helper is present in main but remains unmounted. This settled helper handoff does not authorize route integration.
- The prior adapter handoff is included in this lane's write set for truthful settlement to `SETTLED` with that exact merge evidence.
- GitHub's open-PR search at activation found no open `HOSTED` PR. The later route inventory observed open Rules PR #1506 and UI PR #1510; their inspected changed-file lists do not overlap the helper lane. No shared state, port, database, service, provider, or runtime was used here.
- The owner subsequently selected `https://buddy.dungeonmind.net` and the intended population is DungeonMind’s managed DMS-authenticated population. This is an intent decision, not proof of the external OAuth eligibility restriction or actual browser cookie delivery. Per-World ownership/roles remain undecided. Browser cookie-delivery and route-wiring gates remain later work.

## 3. Non-goals and auth-mode boundary

- Do not refactor Buddy's existing local-session loopback + session-bound HMAC-CSRF contract in `agent_graph_local_session.py` or its routes.
- Do not replace DungeonMindServer's separate logout Origin policy.
- Do not add global middleware or call this helper from shared bearer/service authentication. Only a later route owner, after selecting cookie authentication, may opt in. Bearer, service-key, local-operator, and other non-cookie authentication retain their existing rules.
- Do not implement an additional CSRF token format. Any future token contract needs separate design/review.
- This settled helper slice does not authorize mounting the helper, changing auth routes/CORS, using a real cookie, calling DMS, enabling live tools, altering deployment, performing production writes, using a provider, or deploying. The later hostname and population intent are recorded in §2 only.

## 4. Proposed API and exact policy

Create `apps/live_control_server/services/trusted_cookie_origin.py` with a pure helper equivalent to:

```python
require_cookie_write_origin(request: Request, *, trusted_origins: Collection[str]) -> None
```

The implementation may choose private helper names while preserving this boundary and behavior:

1. Exact uppercase `GET`, `HEAD`, and `OPTIONS` return without requiring an Origin. Every other method token, including lowercase spellings, is unsafe.
2. For an unsafe method, inspect every raw `Origin` header value. Require exactly one; do not use a single-value accessor that can hide duplicates.
3. Reject missing, duplicate (including identical duplicates), opaque `null` (case-insensitive), comma-containing, whitespace/control-containing, malformed, or foreign values. Reject userinfo, any path including `/`, query or fragment (including empty delimiter forms), wildcard/suffix patterns, backslash, percent-encoded host data, and trailing-dot hostnames.
4. Canonicalize request and configured values with one parser. Accept only HTTP or HTTPS and exact uppercase safe method tokens as defined above. Normalize scheme and ASCII hostname to lowercase. Require hostname input to be ASCII; for internationalized names require an explicit browser-compatible IDNA A-label (for example `xn--bcher-kva.example`) and reject Unicode U-label input. Validate A-labels with `idna.encode(..., uts46=True, transitional=False, std3_rules=True)` and require canonical output to match the lowercase input. Never transform a Unicode hostname with Python's IDNA-2003 codec, which can alias distinct browser origins. The current locked `idna` 3.11 package is present through the direct HTTPX dependency; this slice does not change dependency manifests. Validate DNS labels (1–63 chars, `[a-z0-9](?:[a-z0-9-]*[a-z0-9])?`) and total host length (<=253). Reject malformed hosts. Parse IPv6 with `ipaddress`, require IPv6, and render compressed lowercase inside brackets; reject zone IDs. When all DNS labels are numeric, require a valid dotted IPv4 address and reject numeric shorthand. Accept only ports 1–65535; omit default 80/443 and render other ports as canonical decimal.
5. Canonicalization makes scheme/host case, IDNA equivalents, default-port spellings, and equivalent IPv6 compression compare equally. It does not trim, infer, or widen trust. No trust may be derived from `Host`, `Forwarded`, `X-Forwarded-Host`, `Referer`, or CORS response headers.
6. `trusted_origins` is trusted server configuration. Canonicalize every entry with the same rules. Empty configuration or any invalid entry fails closed for all unsafe requests; do not retain only valid entries. Canonical duplicates collapse. A rejection returns a stable generic 403 and does not disclose request or configured origins.
7. The helper has no auth-mode autodetection and performs no mutation. Future callers must invoke it only on the already-selected cookie-auth path and before state, provider, or file side effects.

## 5. Offline acceptance and verification

Use synthetic Starlette/ASGI requests and a fake mutation counter. No live server, database, secret, DMS session, browser, or provider is needed.

- Allowed exact canonical origin passes for each unsafe method; the fake mutation happens only after the helper.
- Positive canonical equivalence vectors include `HTTPS://ExAmPlE.com:443` → `https://example.com`, `http://EXAMPLE.com:80` → `http://example.com`, equivalent ASCII A-label input `https://XN--BCHER-KVA.example` → `https://xn--bcher-kva.example`, the valid sharp-s A-label `https://xn--fa-hia.example`, and `https://[2001:0db8::1]:443` → `https://[2001:db8::1]`.
- Rejection vectors include missing/duplicate Origin, `null`, comma, leading/trailing whitespace, control characters, malformed host/port, invalid A-label `xn--a`, port 0 or >65535, trailing dot, numeric shorthand, percent in hostname, Unicode U-labels including `faß.example`, foreign origin, userinfo, path `/`, query, fragment, wildcard/suffix, and backslash. Lowercase `get`, `head`, and `options` are unsafe and reject missing Origin. The mutation counter remains unchanged on every rejection.
- Empty configuration and configuration containing any invalid entry reject all unsafe requests, including otherwise-allowed requests. Invalid entries are not silently discarded.
- Exact uppercase `GET`, `HEAD`, and `OPTIONS` do not require Origin under this helper.
- Static diff/import inspection confirms no route imports or calls the helper and no existing auth route, middleware, local-session, or service-auth module changed. This slice makes no bearer/service runtime test claim; that belongs to a future route-wiring integration.
- Execution on the implementation worktree after all exact-head review corrections: focused offline command `PYTHONDONTWRITEBYTECODE=1 TMPDIR=<task scratch> PYTHONPATH=<existing Buddy .venv site-packages> <Python 3.13.12> -B -m pytest -q -p no:cacheprovider tests/test_trusted_cookie_origin.py` passed **66 tests**; Ruff 0.15.7 on the helper and test passed; `git diff --check` passed. Static `git grep` and recursive source search found no helper reference under `apps/live_control_server`, so it remains unmounted. No live services, database, DMS, browser, or provider calls were made.
- Inspect pytest/Ruff configuration and the pinned Python/test environment before running anything. Run the focused test file, lint touched Python files, and `git diff --check`. All tests remain offline and deterministic; do not run tests that touch PostgreSQL, DMS, a live provider, or production data.

## 6. Exclusive expected write lease

Only these four paths may change in the lane:

- `Docs/Plans/HANDOFF-HOSTED-cookie-origin-policy.md` — this settled authority record and truthful completion evidence for this lane.
- `Docs/Plans/HANDOFF-HOSTED-dms-principal-adapter-v1.md` — settle merged PR #1508 and retain the fact that the adapter remains unmounted.
- `apps/live_control_server/services/trusted_cookie_origin.py` — new isolated helper.
- `tests/test_trusted_cookie_origin.py` — new focused offline tests.

Return to the steward before changing any other path or broadening the invariant. Do not touch `main.py`, existing auth/local-session modules, routes, DMS, UI, CORS, schema, deployment configuration, or `hosted_owner`. No database, provider, service, port, or retained runtime state is used. Task-local Python environment, test cache, and temporary files must stay inside the approved task workspace and be inventoried/cleaned within Alan's authorized cleanup scope.

## 7. Later gates and completion boundary

The owner selected `https://buddy.dungeonmind.net` and intends to use DungeonMind's managed DMS-authenticated population. This helper cannot be mounted until actual browser cookie delivery to that origin is proven, the external population restriction is evidenced, the World ownership/role policy is decided, each route's auth mode and mutation boundary is inventoried, and route integration is separately authorized. Adapter and helper merges do not establish login/authorization readiness. PR #1509 was reviewed and merged; the helper remains dormant. Do not wire routes, enable, configure production, or deploy under this settled handoff.

This lane delivered an offline-tested, reviewed, unmounted Origin-policy helper, merged in PR #1509. It does not establish hosted auth, route-level CSRF coverage, or v1 launch readiness.
