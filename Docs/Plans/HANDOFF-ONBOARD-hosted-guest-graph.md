# ONBOARD: hosted Sizzek Graph session

Status: MERGED into main by #4604 at `c10b1fc29e832f77049e342c59a8c6144a70d47f`. This slice connects the existing Graph to a server-owned isolated copy; it does not complete the broader Build, Plan, Play and Buddy objective. The owner authorized signed-out use of the complete Sizzek World, review, merge and deployment.

Topology: DungeonMind PR #299 merged at
`6beb506ea3a03b34e27fb309cccf37393d01318e`; this slice consumes that merged
revision. Buddy base is
`f5538e832756ccb58d2a14b1e96c824682b1da48`, branch
`codex/sizzek-hosted-guest-graph`, checkout this worktree. Open Buddy PRs and
the Core lease were checked; existing Build/Play work is separate. No production
database, service, port, or provider is leased for implementation or tests.

The hosted browser gets an opaque, secure, HTTP-only session credential with
same-origin write protection, bounded resource use and a per-session copy of a
server-selected, pinned Sizzek source revision. Copy inputs must be durable and
stable for retries. Never expose a partial copy; never accept a source or native
space identity from a guest. Reset replaces the guest session copy without
changing the source or other sessions. Use the existing Graph and native edit
operations; preserve the local-only service boundary and authenticated users'
behavior. Full source visibility is explicitly authorized by the owner. The
copy is a snapshot, and changing the private owner World must not silently
change existing guest sessions.

Expected write lease: this handoff; Core dependency pin and lockfile; hosted
guest session and graph API/service, existing index-graph session/store and
native Graph initialization only as needed; app entry, existing Buddy Home's
signed-out Graph link, and Graph adapter; their
focused tests and required CI classification. Any additional shared schema,
production configuration, or cross-surface capability requires re-anchoring
and an explicit lease update before editing. Existing unrelated lanes remain
untouched.

Verify anonymous bootstrap, CSRF and origin rejection, session isolation,
copy retry and failure, actual native graph creation and connection, reset,
source and signed-in non-regression at API and browser boundaries. Run the
required exact-SHA local frontend and affected backend contracts, retain
inherited failures, and obtain independent exact-head Bugbot review. Production
activation must use the current supported deployment path and be verified on
desktop and mobile; no changes to serving or rollback pins are implied here.
