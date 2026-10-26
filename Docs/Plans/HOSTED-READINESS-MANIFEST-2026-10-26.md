# DungeonMindBuddy hosted readiness: provisional source manifest

Snapshot: 2026-10-26 UTC. This records repository source state and the implementation candidate only. It is not a deployment manifest, host inventory, login proof, or readiness claim.

## Current remote source heads

| Repository | Main head at re-anchor | Role / note |
|---|---|---|
| [DungeonMindBuddy](https://github.com/Drakosfire/DungeonMindBuddy) | c5250824f3c3d5b4bb33d1897914158a3ee3d8fa | Current Buddy runtime base for the draft. It advanced through PR #1800 at d288f862 and PR #1801 at this re-anchor. |
| [DungeonMindServer](https://github.com/Drakosfire/DungeonMindServer) | f95e92cb0fb50949260534b12c063ab1811eaf30 | Existing DMS identity and session authority. |
| [DungeonMind](https://github.com/Drakosfire/DungeonMind) | 4ccd39a1e433d81569d86c05273ac33ee8f27ef3 | In-process Core library and separate WorldGraph authority. |
| [LandingPage](https://github.com/Drakosfire/LandingPage) | 9e567007cd37867fffd95db8b229c77f5950616e | Public frontend repository; no edits proposed. |
| [DungeonOverMind](https://github.com/Drakosfire/DungeonOverMind) | cd3dda331fecc30e0fcb89901a83597fc020725f | Cross-repository plan owner. The requested plan was read at PR #58 head 9c8e27a9372f14c48d090b385e93e9c987c22ca6. |

## Related open work preserved

- Buddy [#1512](https://github.com/Drakosfire/DungeonMindBuddy/pull/1512) remains open and owns the route authorization inventory and cookie-Origin handoff documentation.
- Buddy [#1514](https://github.com/Drakosfire/DungeonMindBuddy/pull/1514) remains open and owns the proposed account-level World access policy and its blocked implementation handoff.
- The draft described by this manifest adds neither document again and does not adopt #1514's proposed creator-only rule. The allowed population remains the existing DMS-managed population; no new owner-only population gate or legacy-World ownership claim is added.
- DungeonOverMind #20, #39, and #58 are left unchanged. Their unique documentation remains in those PRs.

## Identity and authorization contract

- Hosted identity is resolved from the DMS dungeonmind_session cookie through GET /api/auth/current-user; Buddy uses the returned stable sub.
- Unsafe HTTP methods require the exact configured Buddy Origin. Logout proxies DMS POST /api/auth/logout with that Origin and the session cookie, and relays DMS Set-Cookie clearing headers.
- The Buddy code does not add a login route or alter DMS login-return behavior. DMS's single configured landing target and its deployed value still need operator verification before login can be called complete.
- The subject-to-World map is a static explicit access input, not an ownership inference. The production app registers zero reviewed World routes, so hosted World/API operations fail closed with 403 until resource-to-World route bindings and the retained-World assignment procedure are reviewed.
- The auth middleware covers HTTP paths under /api, including media paths and HTTP streaming/SSE routes. Current code contains no WebSocket route; the Nginx example does not enable WebSocket upgrade. Any later WebSocket surface needs its own authorization boundary.
- Buddy has no permissive CORS middleware; the package example uses one same-origin proxy. Health endpoints return generic status codes and no configuration values.
- Local run explicitly selects local plus local_operator and loopback. The request boundary rejects Forwarded, X-Forwarded-For, X-Forwarded-Host, X-Forwarded-Proto, and X-Real-IP headers. The example reverse proxy forwards these headers, causing local operator requests through that proxy to be denied.
- The fixture-backed graph gold-review developer router is omitted in production builds because its modules import evaluation campaign fixtures. Local source checkouts keep the router when those sources are available. This package boundary is now explicit and has a focused test, but app-level tests could not import the incomplete local source mirror in the final verification attempt.

## Package candidate

- Dockerfile.production pins Node 22.23.0, Python 3.13, uv 0.13.5 and their image digests; npm uses package-lock.json and Python uses uv.lock. Debian build tools use the dated 20261026 snapshot archive. Advance this snapshot through review to receive later OS security updates.
- The app remains in-process. The API container binds to a host loopback mapping; Nginx disables response buffering and uses a long read timeout for HTTP streaming.
- The package expects distinct Buddy application-state and DungeonMind WorldGraph PostgreSQL coordinates and owners. It requires durable managed-world, artifact, session, and WorldGraph roots outside the replaceable container or checkout. It performs no startup migrations.
- Production readiness validates explicit configuration and runtime preflight. The current empty route-policy set is a blocker, not a usable hosted authorization deployment.
- The production image was not built because the available Docker socket was denied. Repository tests do not establish host capacity, deployed versions, database reachability, durable backup/restore, proxy behavior, or login-cookie delivery.

## Source and test provenance

- The writable task copy initially contained Buddy source at 6e4b1580c6aa46f24aafc01e19880089229d3598. main.py was replaced with the exact current c525 base blob 56b8f742e9f5458cae82b8d7b23267e60392f3d9 before adding this slice.
- Additional test-support sources were restored from Buddy 3ddf743c28f15e52f42f86d6b0b8889fedd4bfed, including the full tracked tests/application_state/conftest.py blob 05e406eb8b70e9bf01b84533b2eac643be6546c1. The test mirror is not the full c525 tree; no claim is made that repository tests ran against the complete current main checkout.
- The exact Core source overlay is 4ccd39a1e433d81569d86c05273ac33ee8f27ef3, including src/dungeonmind and src/dungeonmind_dnd. The GenerationEngine overlay is 3e085168c11bdee0de580b8cfa0f00cee157c157.
- The missing evaluation fixture tree was not restored because it contains campaign/session content. The production package excludes it.

## Verification status

- Ruff 0.15.7 passed on the final changed Python auth, app, and auth-test files; bash -n passed on scripts/host_inventory.sh.
- The final focused pytest attempt used the full conftest and exact Core/GenerationEngine source overlays, but only the cached Python 3.12 environment was available; Buddy requires Python 3.13. Result: 109 passed, 8 failed during imports because the cached environment lacks a compatible psycopg binary/libpq wrapper. The failing tests include app import/readiness/logout and existing graph auth route-model tests; this is not a passing integration suite.
- uv sync --locked --offline could not prepare a complete environment because the task mirror lacks generated out/hermes-agent source and the available global uv cache is read-only. No packages were installed globally.
- npm run build passed on the final files (902 modules transformed); Vite reported a non-fatal existing static/dynamic import warning. The Docker image remains unbuilt.
- No tests used a live database, provider, service, or retained World. No server inventory was run.

## Decisions and operator steps still required

1. Choose the exact Elderwyld World and source to host. The local/source inventory candidates are not verified assignments; no campaign contents were opened or migrated.
2. Approve an explicit policy for new Worlds and a verified procedure for retained World-to-subject assignments. Until then, hosted World routes remain denied.
3. Verify the existing DMS-managed account population gate and the deployed DMS landing target and browser delivery of the DMS cookie to buddy.dungeonmind.net.
4. Run and review the sanitized read-only inventory in RUNBOOK-HOSTED-read-only-host-inventory.md. Output may include host/IP, service/container, image, port, and mount identifiers; redact before sharing.
5. Before any later staging change, identify both logical DB migration heads and owners, external durable roots, tested backups and isolated restore proof, exact image pins, proxy routing, capacity, provider limits, and rollback owner.

No live server was contacted. No secrets or credentials were read. No external configuration, account, network, database, branch data, or service was changed.
