# ONBOARD — hosted owner-created World

Status: BLOCKED design; no implementation write lease. Goal: Sizzek ingestion
and new-user onboarding. Re-anchor before activation.

## Problem and boundary

An authenticated hosted user can list only existing owned and deployment-admitted
Worlds. The selector intentionally disables creation. Local creation reserves a
managed World and native identity; reviewed source admission and first-graph
publication are separate operations. A newly created hosted World must belong
to the actual authenticated subject and become usable through existing hosted
World authorization, without adopting an existing World or granting access to
another account. Creation does not itself admit source content, fabricate a
Graph head, or authorize public/anonymous access.

## Evidence and unresolved contract

- `WorldSelector` currently offers create only to `local_operator`.
- The local `POST /api/live/world-containers` does not bind the request's hosted
  subject. Do not expose it as-is. Hosted middleware admits the existing exact
  owner-filtered GET collection, not a generic collection mutation.
- The catalog's `create_world(name, owner_subject)` owns creator/name
  reconciliation and native reservation. Verify its actual transactional and
  retry behavior with the current locked database environment.
- Hosted access currently combines authenticated subject, authoritative World
  ownership, and an independently configured deployment allowlist. Decide and
  review how a newly created owned World becomes admitted without letting a
  request manufacture or expand arbitrary access. A successful create followed
  by a permanently inaccessible World is not success. Do not silently waive the
  allowlist or modify environment configuration per request.
- Open draft #3824 touches hosted authorization, routing and their tests. Before
  activation, inspect its current head and active write lease; serialize or use
  an explicitly agreed region split. No dependency on its draft head is implied
  merely by a file overlap.

## Proposed bounded delivery

One implementation PR: authenticated hosted creation and owner-visible recovery
using a code-owned exact create capability, with owner derived only from the
verified principal. Preserve local creation semantics and existing World grants;
use the existing catalog/reservation owner and explicit cookie-origin checks.
Define same-name/retry and ambiguous-failure recovery before implementation.
The public response must not expose native IDs, owner subjects, grants, or
provisioning receipts. The UI must communicate what is and is not ready.

Before activation, pin the approved deployment-admission contract, lane/base,
exclusive paths, any migration or operational dependency, and actual ownership
of the overlapping hosted routes. If the correct admission model requires a new
cross-repository or deployment contract, return that decision to the owning
steward; do not broaden this slice silently.

Verification at the owning boundary: mounted hosted HTTP tests with real
authentication boundary and isolated database for unauthenticated, foreign
origin, missing/invalid identity, same-name distinct owners, retry/concurrency,
failure/recovery and cross-account access; verify no caller-selected owner and
no accidental access to existing Worlds. Exercise the selector and exact
hosted transport in browser tests, including creation, refresh and account
switch. Run the repository's required exact-SHA backend/frontend verification
and independently review the cumulative change. A verified created World is not
evidence of source ingestion or a published native Graph.

## Serial successors

1. Real private Apprentice import and source/Graph review, including faithful
   Word-to-source handling and a repeat-ingestion witness. Assess the existing
   Markdown-only Build import and DOCX converter before deciding a code slice.
2. Immutable player-safe guest release with independent access/security proof.
3. Temporary guest graph editing and guided Build/Play experience; live
   anonymous text and image generation each require separate isolation, cost
   and quality evidence. Account onboarding and measured usability remain part
   of the overall goal.
