# DOGFOOD: preserve current serving workbench in page release

Status ACTIVE under Alan's explicit deployment instruction. The goal remains
incomplete until signed-in Buddy creates and saves a page from just-discussed
context. Merged code and local replay alone do not complete it.

Serial release-integration PR on `codex/dogfood-page-serving-integration`, base
`codex/dogfood-page-serving-base@6fca711009799516bb349260dae6c6d050bef769`.
Merge only into that dedicated release base, never silently into `main` or the
unfinished #3824 integration draft. No unmerged behavioral parent. Current root
checkout owns this adoption, not new workbench design or authoring.

During rehearsal the live release advanced from1b94d749 to06634f1a. The sealed
preflight refused the changed identity without touching production. Preserve
only the exact already-serving 1b94d749→06634f1a delta: hosted owned-World threat
draft create/read/generate/revise/validate/accept/recovery transport and resource
checks. This is the COMBAT hosted-meatling/workbench contract, not adoption of
the broader unfinished #3824 draft. Its ongoing authoring and #4411 ownership
remain with COMBAT; this lane changes none of their semantics.

Expected writes: this handoff plus the ten files of that immutable served delta
(its existing COMBAT handoff, three frontend API/workbench files, server route
registration, threat create handler, hosted authorization and resource resolver,
and the two owning authorization test files). Carry the served bytes unchanged
where the canonical base agrees; preserve all other canonical fixes and guards.
No dependency, schema, provider/model, source-reuse predicate or prompt changes.
If adoption cannot preserve both contracts cleanly, stop and split rather than
redesign another owner's capability. The allowlisted patch applies cleanly.

Validate exact-head hosted authorization and page-reuse regressions, compare
inherited failures against the exact canonical base, inspect the cumulative
diff independently, and open/review the assigned PR. Rebuild the exact normal
candidate and refresh its dedicated reader-compatible fallback before cutover.
The fallback predecessor #4435 is merged into its dedicated base; its source
f5c7a7d8 remains qualified only for its frozen release, not this new combination.

External deployment verification retains canonical migrations, protected
host-local backups and isolated restores, exact image identity, source-data
preservation, current/fallback reader compatibility, graceful draining and
signed-in actual-app acceptance. Private operational evidence stays outside
GitHub. Source-only test data and uniquely owned databases stay isolated. Do not
overwrite a changed serving identity, lose an accepted page, or call health alone
completion. User deployment authority is recorded in the chat; no new permission
gate is inferred for this necessary preservation slice.
