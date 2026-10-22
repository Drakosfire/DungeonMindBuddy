# STATBLOCK — managed World draft provenance

SOURCE DELIVERED: PR1578 mergedf3a8dac3ca900cb79e9da77989ae33e9fab8858b and runs on matchedAPI8000/UI5202, preserving1487 priorAPP rows/schema0042. Bugbot approved06993785b4b8d064071fdc9ba3e17faac0ef4a23 after resolving configured-root and malformed-envelope findings; independent71backend/159UI/typecheck/diff-check passed. PR1579 delivered the persistent lifecycle root. Actual ordinary World-scoped draft creation and generation now succeed with exact managed/native provenance. Candidate review/revise exposed a separate current canonical-digest mismatch, owned by HANDOFF-STATBLOCK-canonical-digest-parity.md. Mechanics acceptance remains open.

Historical scope: PRIME owns design/implementation/merge and guarded8000/5202 delivery.
Baseaf4298575fe8db2bd564da4fa3929b99d55385e9; existing buddy-context-loop checkout,
branch codex/statblock-managed-provenance. Serial one PR; no competing lease.

The actual ordinary Build Workbench opens under the verified managed World but
Create & generate reads its slug through native projection, failing before draft
creation. Server draft revision admission likewise passes the slug to native
read_revision. Fix both owners of this one provenance contract.

World-scoped workbench creation reads the existing managed projection endpoint,
verifies its owner/native/version/exact-head envelope and uses that revision as
provenance. Native campaign scope retains its owning route. Server World draft
create/update resolves the current managed binding, reads the exact requested
revision under that native World, rejects mismatched revision/World, rechecks the
binding before writing. Explicit freestanding provenance stays null; never
synthesize campaign, use slug as native authority, or hide contradictory scope
with a fallback. No new generation call or paid retry on uncertainty.

Exclusive writes: routes/threat_drafts.py and tests/test_threat_draft_routes.py;
surface/modules/StatblockWorkbenchModule.tsx and its tests; this handoff,
HANDOFF-BUILD-statblock-tool.md and ROADMAP-demo.md settlement. No SQL migration,
mechanics-association API/store, native Graph alteration or provider configuration.
Verify HTTP create/update read exact native identity, wrong/missing/unavailable
pin, binding change and absence no-write; UI managed envelope and scope rejection
and existing generation/recovery cohort. Typecheck/build, Bugbot exact cumulative
review, guarded ownedAPI/UI rollout with protected state. Resume the same authored
synthetic brief through ordinary Build generation/review/accept/reopen, inspect
real DMS exact revision and digest. No claim of C1b or Graph publication.
