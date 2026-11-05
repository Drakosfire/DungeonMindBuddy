# INGEST: deterministic known-character bindings

Status: ACTIVE. User authorized implementation, one isolated Session 30 extraction comparison, and source-grounded Gold development. No publication or primary-data writes.

Topology: serial. Base origin/main b20e0b0d72a756d6315605e1501059317628aa9a; branch codex/ingest-known-character-bindings. Predecessors 2084/2085 merged. Existing 2086 owns native source browsing and Core dependency pin; this slice does not change dependency pins, shared runtime or its paths. 2081/2082 and paused2079 remain separate.

Write lease: this handoff; src/graph_memory/extraction/known_character_bindings.py, category_candidate_graph_extractor.py, graph_preview_runner.py; apps/live_control_server/services/known_character_context.py, graph_preview_runner.py, exact_run_candidate_projection.py; owning tests, including bounded failure fixtures. No corpus-specific prompts, new provider pass, directory/registry authority, identity publication or historical fact copying.

Outcome: admitted campaign character names and aliases from one native revision locate exact source mentions using the existing matcher. Persist the pinned context in the run; make it available to actor extraction, retain name-only missing endpoints, and project all unambiguous source mentions for matched candidate nodes. A mention is recognition, not an action or publication decision. Ambiguous identities/overlapping names remain unlinked. Missing native head yields explicitly empty context; no file fallback. Existing runs remain frozen.

Validation: generic names, multiple occurrences, aliases, conflicting identities, word boundaries, exact offsets, source planning exclusion, no imported history, omitted actors retained as name-only candidates, immutable reader projection. Independent review of cumulative diff before PR. Run actual standard-v2 DeepSeek on exact latest Session30 source in isolated evaluator; retain raw output, telemetry/cost, context and candidates in database. Compare source-matched baseline, audit attribution/quotes and produce source-grounded Gold with unresolved cases explicit. No extraction before local boundary checks pass. No merge authorization inferred from previous PRs.


## User-directed scope revision: pre-model name review

User explicitly added an app review step: generic deterministic typo suggestions against known names, correction/keep decisions before any model call, original and corrected source retained in APP with pinned review decisions. This is one coupled recognition boundary, serial in the same PR. Expected write lease additionally includes src/graph_memory/extraction/name_review.py; apps/live_control_server/services/recap_name_review.py and recap_graph_preview_ingest.py; routes/recap_ingest.py; apps/live-control-ui/src/api/recapIngestApi.ts and types.ts; modules/IngestionModule.tsx and its tests; ingestion/RecapNameReview.tsx and tests; corresponding Python/API tests and world-ownership-core.yml ingestion test selection. hosted-validation.yml remains untouched because2086 leases it; its existing IngestionModule integration test now exercises the review gate. Existing2082 changes the same orchestration module in a separate inactive branch; no concurrent editor is active and its existing activity UI is not absorbed or merged here. Do not change source-browser2086 dependency/workflow leases.

User approved the Session30 Karesmine→Karsemine (two occurrences) and Baergom→Baergrom (one occurrence) corrections. Matching code and prompts contain no corpus-specific spelling map. Compare to latest37910c76 with the identical selected notes; report approved source edits as a comparison confound. Original input remains retained and immutable.

## Qualification before actual comparison

Rebased onto merged2086 main eb2f0afe805f473b22bfb2bccf4709a5ad90e210; isolated test interpreter uses Corec2ea8d0 and GE18ea21. Source-browser runtime delivery remains separately owned; this lane uses /tmp/known-character-venv and evaluator port55447 only. No shared interpreter borrower.

Independent subagent approved the code and source-only Gold (56 byte-pinned witnesses) before provider execution. Initial owning backend set115 passed; final ordinary Process/API/model-default set55 passed; name-only omission through actual production validation1 passed; UI review/orchestration21 passed; TypeScript and production UI build passed. Three unrelated failures were separately reproduced on unchanged b20 main (old fixture ownership/BoundedFixtureClient setup); they were not silently fixed or counted as passes here.

Actual comparison remains to be executed and assessed. Preserve original37910c76, identical notes bundle, original source and three user-approved spelling edits. No Gold passed into extraction. No publication/primary data writes or runtime delivery are authorized by this handoff.

## Provider boundary — blocked before execution

PR2087 is open. Automatic approval review rejected the actual Session30 source+selected-notes transmission to OpenRouter before process creation, stating that recognized trusted authorization covered C1 Sessions1–10 rather than this Session30 payload/destination. Do not retry or bypass without the exact missing authorization. No execution lock, provider process or evaluator ingest.run was created; original37910c76 revision5 was verified unchanged. Source-only Gold and all review/correction artifacts are retained at the durable ingestion-resume/session30-name-review evidence root. The Gold has56 independently verified witnesses; no new extraction or comparison result is claimed. Remaining action: exact Session30+notes→OpenRouter DeepSeek V4.1 Flash1017 approval, then one isolated standard-v2 extraction and independent comparison. All other work remains preserved; primary data and publication unchanged.

Final source-only strengthening excludes unmentioned historical names from actor prompts and candidate identity linking. Exact-name bindings allow character/creature actor classifications without changing their type. Independent subagent approved this final delta; focused19 pure tests passed. No corpus-specific names are embedded in matching logic or prompts.


## Dogfood authentication repair

User-reported403 on the live name check exposed a missing client transport registration. This PR additionally owns the exact recap-name-review path classification and read-only session-renewal entry in apps/live-control-ui/src/api/liveApi.ts, its actual-wrapper transport tests, and hosted-validation.yml selection (prior2086 lease is merged/released). Server auth remains unchanged.25 UI/transport/orchestration tests pass; independent subagent APPROVE_CODE for this repair. Deploy only the corrected UI; no extraction, provider call, dependency sync or API restart is needed. Preserve prior immutable assets so already-open tabs retain lazy chunks.
