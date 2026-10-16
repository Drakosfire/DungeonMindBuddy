# Ingest: bind fresh recap sources to their World

Status: ACTIVE — PRIME authorizes DOGFOOD to implement this next Ingest slice under the operator's Ingest assignment. ARCHITECTURE owns independent review; PRIME owns merge.
Base: Buddy origin/main@448e88d9006b19cfb607d4ac5afde14d6d44d856.
Lane: codex/ingest-recap-source-world-binding, /tmp/prime-ingest-recap-source-world-binding. Topology: serial successor to merged #1266/#1276; no unmerged dependency.

## Outcome and evidence

One capability: a fresh ordinary recap Process registers immutable source evidence in the verified native World, persists that binding in APP-STATE, and reopens the exact run's source with current admitted graph links. Process creates candidates, not admitted World knowledge.

DOGFOOD's scratch-only combined witness in /tmp/ingest-main-448e-witness reproduces the gap: candidate/source persistence succeeds, but historical projection returns world_binding_unavailable because source.world_id is null. That witness is NOT checked-in main acceptance evidence. The fixture/non-provider model literal was scratch-only, not a production regression. Preserve these distinctions.

PRIME independently verified runner registration omits World, creator has no World parameter, registry idempotence ignores World, APP source copies the null field, and historical projection requires source.world_id. ARCHITECTURE reviewed this contract: fix entirely in Buddy; no Core changes.

## Contract

- Ordinary Ingest already resolves RecapContextSnapshot from the managed World. Use its verified native_world_id for native source.world_id; retain managed_world_id, native_world_id and binding_version distinctly in each run's frozen context. Never infer World from campaign, title, a current selection, sentinel, or default.
- Introduce an explicit new World-scoped recap source ID builder/namespace. Require native World, campaign, session and full normalized-content digest. Use unambiguous canonical tuple encoding/hash. Do not change/rewrite/enrich old worldless records, add migration/recovery shims, or silently bind the old campaign/session/digest ID.
- Fresh registration requires an explicit World before writing registry content. Same World/campaign/session/content is idempotent; different Worlds produce distinct identities. Each run retains its own verified binding version; source identity does not pretend one immutable artifact contains every later run's context.
- Include world_id in registry immutable matching/idempotent scope. Conflicting same-ID World or content fails closed, never overwrites. Registry-owned content bytes/span hashes stay exact and immutable.
- At run persistence and historical readback, verify artifact/APP source native World agrees with its exact run context. Reject missing, null, foreign or contradictory context before a projection/provider action; no latest/default/current-World fallback. Native query uses the source's verified native World.
- Audit all recap creator callers, including graph_object_authoring_prepare and session28_retained_package_registration. Thread an already verified explicit World or return a clear missing-binding refusal. Do not invent campaign-to-World authority or broaden their publication behavior.

## Exclusive expected write set

- this handoff
- Docs/Plans/HANDOFF-INGEST-graph-first-experience.md (truthful settlement of #1276 only)
- Docs/Plans/HANDOFF-INGEST-graph-candidate-source-status.md (truthful settlement of #1266 only)
- src/graph_memory/evidence/source_artifact.py
- apps/live_control_server/services/source_artifact_registry.py
- apps/live_control_server/services/graph_preview_runner.py
- apps/live_control_server/services/graph_run_registry.py
- apps/live_control_server/services/historical_recap_world_projection.py
- apps/live_control_server/services/graph_object_authoring_prepare.py
- apps/live_control_server/services/session28_retained_package_registration.py
- tests/test_recap_source_world_binding.py (new owning identity/persistence regressions)
- tests/test_live_recap_ingest_graph_preview_api.py (checked-in combined acceptance witness)
- tests/test_historical_recap_world_projection.py
- tests/test_source_artifact.py
- tests/test_graph_preview_runner.py

No UI/shared styles, provider route, lock/schema/migration, retained source/registry/corpus or serving changes. Return to PRIME if another path or ownership contract is necessary. Active Build is on main3b575220; PRIME's Jev consumer edits remain in another checkout. These source paths are disjoint from both.

## Verification and handback

Use synthetic source/candidates, fake extraction, exact configured route model identifier and disposable APP databases only. No paid provider calls or World publication. Existing host Postgres54329 is approved and running; sandbox network refusal is not host unavailability. Run host checks with the required execution permission. Unique dungeonbuddy_app_state_test_* databases must be cleaned up; never use retained54330/54331.

Prove same-World idempotence, two Worlds with identical campaign/session/text getting distinct source identities and correct native queries, old worldless records unchanged, conflicting World refusal, APP/run/source mismatch refusal before projection, exact source bytes/span identity, and fresh APP readback after Process. Commit the combined Process→canonical/normalized/candidate/manifest→exact source→historical node-bearing projection regression (fixture World graph explicitly synthetic). Run focused owning tests and cumulative diff checks; distinguish pre-existing failures.

For rendered acceptance, use isolated NON-SERVING ports and synthetic storage at desktop/narrow widths, with explicit runtime lease/cleanup. Do not change/restart 5202/8000, touch the operator's Build draft, repair old retained data, or claim full real-corpus ingestion acceptance from fixture evidence.

Finish implementation, intended diff review, tests, commit, push and PR; return exact head, evidence, limits and merge order to PRIME. ARCHITECTURE independently reviews; do not self-merge or add an operator permission gate for ordinary authorized work. Keep claims tied to exact checked-in refs.
