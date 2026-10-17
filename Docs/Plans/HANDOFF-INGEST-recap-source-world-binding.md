# Ingest: bind fresh recap sources to their World

Status: MERGED — PR #1284 merged at `44f3a3e57d162fbcf4c8a1de649a5b5395ed3d93`; this source-binding implementation lease is closed.
Base: Buddy origin/main@18dcb5f7fdedee49a7d785ad765ddc8b9e571322.
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
- apps/live_control_server/services/exact_run_evidence_correction.py (derived recap child must inherit the exact verified parent World context; no new resolution or fallback)
- apps/live_control_server/services/historical_recap_world_projection.py
- apps/live_control_server/services/graph_object_authoring_prepare.py
- apps/live_control_server/services/session28_retained_package_registration.py
- tests/test_recap_source_world_binding.py (new owning identity/persistence regressions)
- tests/test_live_recap_ingest_graph_preview_api.py (checked-in combined acceptance witness)
- tests/test_historical_recap_world_projection.py
- tests/test_source_artifact.py
- tests/test_graph_preview_runner.py

### Direct consumer and fixture adoption amendment

PRIME expands the same capability's expected write set after verifying the direct-caller audit, before implementation. The required World argument is intentional; do not retain a worldless creator fallback just to avoid updating its callers.

- evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
- evals/graph_memory_layer/run_current_corpus_candidate_replay_acceptance.py
- tests/test_artifact_data_root.py
- tests/test_graph_ingest_packaging_live_call_shape.py
- tests/test_graph_memory_category_graph_preview_runner.py
- tests/test_graph_preview_routes.py
- tests/test_graph_run_registry.py
- tests/test_live_source_navigation_api.py
- tests/test_recap_literal_evidence_correction.py
- tests/test_recap_source_content_root.py
- tests/test_recap_source_observation_followup.py
- tests/test_graph_object_authoring_prepare.py
- tests/test_graph_object_authoring_routes.py
- tests/test_graph_object_authoring_published_recap_write.py
- tests/test_session28_retained_package_registration.py
- tests/test_registered_known_entity_context.py
- tests/test_recap_generationengine_default.py
- tests/test_bounded_recap_execution.py

The authoring and retained-package owning tests are explicitly included for the already-leased creator callers. Change campaign-as-World fallback only where needed to enforce this source contract; do not redesign unrelated authoring or Worldbuilding workflows.

Changes in these paths are restricted to adopting the new explicit native-World source contract and necessary identity/lineage fixture assertions. Synthetic tests may name an explicit fixture World; real evaluation entrypoints must use verified existing native-World input or require explicit input and refuse if absent, never derive authority from a campaign/title/default. Do not run private corpus evaluation or publication. Preserve negative tests for missing/foreign World rather than changing them into happy paths. Report inherited failures separately; no unrelated test rewriting.

## Re-anchor and topology settlement — 2026-10-17

GitHub confirms PR #1266 merged at `7cd86c3a3fc875e0994ac53cbe5515bff43b27df` and PR #1276 merged at `448e88d9006b19cfb607d4ac5afde14d6d44d856`. Current `origin/main` is `18dcb5f7fdedee49a7d785ad765ddc8b9e571322` after merged #1283. The intervening main changes touch agent prompt-inspection and conversation-trace files plus Backlog.md; none overlap this lease. This lane was rebased onto that ref.

PR #1244 remains open but its candidate-recovery implementation is held and is not a dependency or stacked parent for this World-binding slice. PRIME explicitly transferred the shared `tests/test_graph_memory_category_graph_preview_runner.py` path from that frozen lane to this lane. This slice may keep the explicit World/v2 identity fixture updates in that file; do not incorporate #1244's legacy repair implementation.

No UI/shared styles, provider route, lock/schema/migration, retained source/registry/corpus or serving changes. Return to PRIME if another path or ownership contract is necessary. Active Build is on main3b575220; PRIME's Jev consumer edits remain in another checkout. These source paths are disjoint from both.

## Verification and handback

Use synthetic source/candidates, fake extraction, exact configured route model identifier and disposable APP databases only. No paid provider calls or World publication. Existing host Postgres54329 is approved and running; sandbox network refusal is not host unavailability. Run host checks with the required execution permission. Unique dungeonbuddy_app_state_test_* databases must be cleaned up; never use retained54330/54331.

Prove same-World idempotence, two Worlds with identical campaign/session/text getting distinct source identities and correct native queries, old worldless records unchanged, conflicting World refusal, APP/run/source mismatch refusal before projection, exact source bytes/span identity, and fresh APP readback after Process. Commit the combined Process→canonical/normalized/candidate/manifest→exact source→historical node-bearing projection regression (fixture World graph explicitly synthetic). Run focused owning tests and cumulative diff checks; distinguish pre-existing failures.

Verification on the rebased implementation: 313 tests passed, 12 skipped, and two known base failures were deselected after reproducing them at pinned base `a9ec` (canonical line-only indexing lacks party evidence; the configured content-root symlink test is rejected by the existing repository-root safety check). `ruff check --extend-ignore F401` passes for the changed Python files; the two ignored F401 diagnostics are unchanged on base. `git diff --check` passes. No provider, private corpus, World publication, live serving runtime, or retained database was used.

For rendered acceptance, use isolated NON-SERVING ports and synthetic storage at desktop/narrow widths, with explicit runtime lease/cleanup. Do not change/restart 5202/8000, touch the operator's Build draft, repair old retained data, or claim full real-corpus ingestion acceptance from fixture evidence.

Finish implementation, intended diff review, tests, commit, push and PR; return exact head, evidence, limits and merge order to PRIME. ARCHITECTURE independently reviews; do not self-merge or add an operator permission gate for ordinary authorized work. Keep claims tied to exact checked-in refs.

## Settlement

GitHub confirms PR #1284 merged at `44f3a3e57d162fbcf4c8a1de649a5b5395ed3d93` from head `26f27a081e5c9c5f5407da5fc61b180c7064561b` (`codex/ingest-recap-source-world-binding`). Its checked-in synthetic Process → exact APP-STATE source → node-bearing historical projection test proves the source and projection retain the verified native World. This settles the source identity and run/source binding capability only; real Session 29 ingestion, graph admission/publication, and rendered 5202 acceptance were not established. The successor managed-run projection handoff owns the remaining selected-managed-World UI/backend binding work.
