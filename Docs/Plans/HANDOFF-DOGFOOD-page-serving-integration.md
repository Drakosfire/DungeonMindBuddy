# DOGFOOD: preserve current serving features in page release

Status ACTIVE under Alan's explicit deployment instruction. The goal remains
incomplete until signed-in Buddy creates and saves a page from just-discussed
context. Merged code and local replay alone do not complete it.

Serial release-integration PR on `codex/dogfood-page-serving-integration`, base
`codex/dogfood-page-serving-base@6fca711009799516bb349260dae6c6d050bef769`.
Merge only into that dedicated release base, never silently into `main` or the
unfinished #3824 integration draft. No unmerged behavioral parent. Current root
checkout owns this adoption, not new workbench design or authoring.

During rehearsal the live release advanced from1b94d749 to06634f1a, then
c560395392fae4b9f2341ad2b6016c37819b4b46. The sealed
preflight refused the changed identity without touching production. Preserve
only the exact already-serving 1b94d749→06634f1a delta: hosted owned-World threat
draft create/read/generate/revise/validate/accept/recovery transport and resource
checks. This is the COMBAT hosted-meatling/workbench contract, not adoption of
the broader unfinished #3824 draft. Also preserve the exact seventeen-file
06634f1a→c560395 attachment-preview delta. COMBAT confirmed that it adds no
production migration or persisted conversation DTO: preview is read-only and
confirmation uses the existing scene-copy format. COMBAT has held further
cutovers for this coordinated window. Its ongoing authoring ownership remains
with COMBAT; this lane changes none of its semantics.

Expected writes: this handoff plus the ten files of that immutable served delta
(its existing COMBAT handoff, three frontend API/workbench files, server route
registration, threat create handler, hosted authorization and resource resolver,
and the two owning authorization test files), plus the seventeen files named by
the exact attachment range: its existing COMBAT handoff, API types/transport and
auth test, Plan encounter component/API/test, Plan page/conversation/evidence
renderers and their tests, server preview registration/handler and the owning
scene-template types/service/PostgreSQL test. Carry the served changes unchanged
where the canonical base agrees; preserve all other canonical fixes and guards.
No dependency, schema, provider/model, source-reuse predicate or prompt changes.
The only context adaptation is retaining canonical lore `open_questions` while
adding the served preview interface/optional projection. All other attachment
hunks apply cleanly. If adoption cannot preserve both contracts, stop rather
than redesign another owner's capability.

This remains one atomic serving-preservation slice: shipping either retained
capability alone would remove the other from the already-updated live app. The
two immutable source ranges provide a review map, not two independently safe
production releases. No new product capability is designed here. Preserve the
unqualified b2076f7 intermediate evidence, including its additional unexplained
full-suite failure; qualify the final materially combined source independently
and never relabel that intermediate failure inherited without proof.

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
