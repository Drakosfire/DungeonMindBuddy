# HANDOFF — DEMO: authenticate Agent graph turns

**Status:** COMPLETE — PR #835 merged at Buddy main `1ccfe7f2af69684e1d02276f66b875ef336b82a0` from corrected code head `3a1a12b05be8e00581dce45da2b1b5efa53f123a`.

**Steward:** DEMO

**Base:** Buddy `origin/main@5b8686829a8f734d99dca59e4998611aee5df5cb`.

This handoff records the completed local-operator gate only. Its claim remains
limited to the guarded local Graph read responses listed here; it does not
provide named-user identity or implement the Session 29 binding/query. A
follow-up route audit found additional unguarded data responses: Graph Preview
recap projection, existing-object candidates, and latest preview; extract/promote
review-package and prepare; and Threat publication identity-resolution responses.
These return recap/source prose, candidate/source evidence, preview excerpts, or
stored candidate snapshots. They are not all native MIND projections. ThreatDraft
revision checks and other prepare/commit reads also remain outside this gate.
None is asserted secured by #835.

**Branch:** `codex/demo-agent-graph-auth`

**PR title:** `DEMO: authenticate Agent graph turns`

**Topology at activation:** Serial. This was the only open implementation PR in
the authentication slice. Session 29 full-graph querying remained BLOCKED on
binding and graph acceptance gates after this prerequisite merged.

## Capability and trust boundary

Establish one trusted local GM gate for Buddy public live API responses that
return native World Graph read data. The server accepts a high-entropy, out-of-band
local-operator bearer only when all of these are explicitly configured:

- `DMB_AGENT_GRAPH_AUTH_MODE=local_operator`
- `DMB_AGENT_GRAPH_AUTH_ENVIRONMENT=local`, `development`, or `dev`
- `DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN` contains at least 32 non-whitespace
  characters; generate it from a cryptographically secure random source.

There is no production default. Unknown, unset, or production environment
configuration fails closed with 503. The server accepts requests only from an
IP loopback peer; forwarded identity headers are ignored. Do not claim LAN,
remote, multi-user, tenant, or durable user identity support. The capability
authenticates the local operator; native MIND GM admissibility remains a
separate read policy.

Missing or invalid bearer credentials return 401. An authenticated typed
non-GM principal returns 403. An authenticated request from a non-loopback peer
returns 403. Error responses never include the credential. Compare the bearer
using a constant-time comparison.

Guard before runtime initialization, World/work resolution, session or packet
resolution, native reads, and provider dispatch on:

- `POST /api/live/agent/turn` when `graph_request.mode` is not `none`;
- `POST /api/live/query` when `world_graph_context` is present;
- both projection routes: `/api/live/world-graph/projection` and
  `/api/live/world-graph/recap-projection`;
- every retrieval route: `/api/live/world-graph/retrieval/{search,object,complete-object,neighborhood,evidence,source-anchor/read}`;
- `POST /api/live/threats/query-hydration`, which returns graph-derived Threat
  query and projection data;
- `POST /api/live/threat-drafts/{draft_id}/publication-operations/{operation_id}/identity-candidates/prepare`, which returns native Threat object details.

Graphless Agent turns and `/api/live/query` without graph context keep their
existing behavior. The retired `/api/live/world-graph-bootstrap/*` routes
already return 410. `/api/live/citation-source` reads allowlisted repository
files, not native Graph data. Except for the identity-candidates response listed
above, this PR does not gate internal revision/context reads performed by
ThreatDraft validation or Graph Review/Threat publication prepare/commit
workflows. Those remaining operations need a separate workflow access review;
they are not asserted secure by this capability.

The Plan Agent asks for the credential in a password field, keeps it only in
module memory, and clears the input after setting or clearing the value. The
shared API client sends it only as an Authorization bearer on the listed native
Graph read responses and graph-enabled Agent/query calls. Do not put it in
local/session storage, URLs, request bodies, application state persistence,
logs, traces, receipts, or the repository. Same-origin scripts/extensions with page access can use an
in-memory bearer; the supported deployment is a local single-operator session.

This slice does not change existing graph binding, graph query semantics,
citations, the Plan Agent graph:none request, MIND contracts, or the Session 29
acceptance gate.

## Exclusive write lease

Only this serial lane may edit these paths during implementation:

- `apps/live_control_server/services/agent_graph_auth.py` (new)
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/routes/live.py`
- `apps/live_control_server/routes/world_graph_retrieval.py`
- `apps/live_control_server/routes/world_graph_projection.py`
- `apps/live_control_server/routes/threat_query_hydration.py`
- `apps/live_control_server/routes/threat_publication_identity.py`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `tests/test_agent_turn_route.py`
- `tests/test_agent_graph_auth.py` (new)
- `tests/test_threat_query_hydration_api.py`
- `tests/test_threat_publication_identity_routes.py`
- `apps/live-control-ui/src/api/liveApi.test.ts`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-agent-graph-auth.md` (new)
- `Docs/Plans/HANDOFF-DEMO-session29-elderwyld-graph.md`
- `Docs/Roadmaps/ROADMAP-demo.md`

The preserved `codex/agent-world-conversation-backend` checkout is suspended
and recoverable, not an active lease. Leave it untouched. No other active PR
overlaps were present at activation. The exclusive write lease ended when #835
merged. Recheck PRs and leases before any added path or contract is considered.

## Runtime and verification ownership

This implementation uses no provider, database, MIND graph, external service,
or shared runtime. Keep all checks local and deterministic. Prove:

- every listed read-response route uses the shared guard and all request bodies validate;
- missing configuration, absent/invalid bearer, non-GM principal, and
  non-loopback peer fail closed;
- forged body roles or forwarded/authenticated-user headers cannot grant GM;
- denied graph requests invoke zero runtime, model, session-resolution, or
  native Graph functions;
- graphless Plan Agent requests omit Authorization even when a credential is
  held in memory, while graph retrieval/projection/query, Threat
  query-hydration, and identity-candidate calls attach it;
- query-hydration denial invokes no native query helper; an authorized request
  reaches that helper;
- identity-candidate denial invokes no native projection helper; an authorized
  request returns the exact candidate set;
- the UI credential is a password field, clears after use, is not persisted,
  and can be cleared explicitly.

Suggested focused checks:

```bash
uv run pytest tests/test_agent_graph_auth.py tests/test_agent_turn_route.py tests/test_threat_query_hydration_api.py tests/test_threat_publication_identity_routes.py
npm --prefix apps/live-control-ui test -- src/api/liveApi.test.ts src/planSurface/PlanSurfacePage.test.tsx
```

At completion, the corrected code head was reviewed and merged as PR #835 at
`1ccfe7f2af69684e1d02276f66b875ef336b82a0`. Nine focused Python tests and 140
focused UI tests passed; the Node TypeScript project passed. The app TypeScript
check retains the inherited JSX namespace error at
`ThreatPublicationPanel.tsx:553`, and the combined synchronous ASGI/TestClient
run stalled in this environment. These limits do not broaden or weaken the
merged route boundary.

## Backward-looking authority sync

PR #833 is merged and its configured-provider saved-Plan witness passed on
2026-10-01. PR #834 is merged at `5b8686829a8f734d99dca59e4998611aee5df5cb`.
PR #835 is merged at `1ccfe7f2af69684e1d02276f66b875ef336b82a0` from corrected
code head `3a1a12b05be8e00581dce45da2b1b5efa53f123a`. It gates only the named
local-operator Graph read responses in this handoff. ThreatDraft, Graph Review,
and remaining publication-workflow reads still require a separate access audit.
The subsequent route audit found unguarded Graph Preview recap-projection,
existing-object candidates, and latest-preview responses; extract/promote
review-package and prepare responses; and Threat publication identity-resolution
responses. These include source prose, evidence, or stored candidate snapshots.
ThreatDraft and other write-workflow reads also remain outside the gate. The
existing-Graph binding and Plan query remain incomplete; this handoff does not
claim graph queryability or close the full DEMO mission.
