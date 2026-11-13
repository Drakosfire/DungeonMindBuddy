# DungeonMindBuddy — Backlog

This file is the **root dispatch inventory** for independent DungeonMindBuddy work that does not already have a sequencing owner.

Cross-project / AI-tooling items live in `~/.cursor/learnings/Backlog.md` instead. Completed and superseded history remains in Git history and, when intentionally archived as a terminal implementation record, `Backlog-DONE.md`.

## Status contract

| Status | Meaning |
|---|---|
| `READY` | Dependencies are satisfied, one bounded slice is known, and a handoff can be authored/dispatched now. |
| `DOING` | One active branch/PR owns the capability. |
| `BLOCKED` | The bounded capability is understood but a named dependency or acceptance gate is unsatisfied. |
| `DEFERRED` | Intentionally not worth pulling now, or only becomes relevant when a named trigger occurs. |
| `IDEA` | Worth preserving, but not yet bounded enough to dispatch. |

Terminal work leaves this file rather than accumulating under `DONE` / `DROPPED` headings.

## Ownership and promotion rules

1. **One status owner.** If an active roadmap, PR tracker, or implementation plan owns sequencing for a capability, that document owns its status. Root backlog keeps at most a non-status pointer in **Delegated workstreams** below.
2. **READY is an execution state, not a synonym for “good idea.”** Every READY entry must contain `Kind`, `Owner`, `Captured`, `Last verified`, `Depends on`, one bounded `Slice`, and an observable `Exit proof`.
3. **Promotion rewrites the entry.** Moving `IDEA` / `DEFERRED` / `BLOCKED` to `READY` means converting capture prose into the execution shape below, not merely changing the heading label.
4. **Captured is immutable.** Re-scoping does not make an old problem newly discovered. Freshness is recorded only in `Last verified`.
5. **Re-verify before dispatch.** More than 30 days after `Last verified`, READY is stale for dispatch until checked against current `main`. If the owning architecture/workstream changed, rewrite, delegate, or drop it.
6. **One slice, one independently useful capability.** “Design and implement,” immediate UX plus future architecture, or multiple authority boundaries must be split before READY.
7. **No shadow sequencing.** Root backlog never overrides a tracker/roadmap because its note happens to be newer.

**Audit anchor:** remote `main@fcaab28ab1db7ce2c024152d15ca844e4c3bb3ef`, 2026-10-19.
This is a document reconciliation anchor, not fresh acceptance of every retained idea.

### Current sequencing posture

[ROADMAP-demo.md](Docs/Roadmaps/ROADMAP-demo.md) is the sole Buddy product
sequencing owner. It records the delivered local authoring/Play baseline,
remaining acceptance and candidates currently under operator discussion.
The old demo-ready roadmap and 2026-09-08 dispatch snapshot are historical.
Do not infer a current blocker or READY assignment from them.

---

# Independent ideas requiring re-verification

## [IDEA] Demolish obsolete Buddy code and repository clutter — captured 2026-11-12

**Kind:** REPOSITORY HYGIENE / RUNTIME BOUNDARY
**Owner:** Buddy maintainers
**Captured:** 2026-11-12
**Last verified:** 2026-11-12 @ `9af1ab3`

**Shipped and verified**

- [#2514](https://github.com/Drakosfire/DungeonMindBuddy/pull/2514) removed seven orphaned Plan and Graph Review modules. Type-check and affected Plan, Graph Review and World ownership suites passed. The Build→Play failure reproduced on the baseline.
- [#2515](https://github.com/Drakosfire/DungeonMindBuddy/pull/2515) removed 13 retired frontend wrappers. Type-check and World-owned Combat and World ownership suites passed. Six unrelated World Agent failures reproduced on the baseline.
- [#2516](https://github.com/Drakosfire/DungeonMindBuddy/pull/2516) replaced broad production-image copies with explicit inputs. Migrations, health, synthetic auth and a native Postgres Graph read passed. **Deployment owner:** complete real DungeonMind browser sign-in and sign-out during deployment rehearsal.
- [#2519](https://github.com/Drakosfire/DungeonMindBuddy/pull/2519) removed the unused ingest-run lock helper. All 25 focused ingest tests passed.
- [#2520](https://github.com/Drakosfire/DungeonMindBuddy/pull/2520) removed two stale reports and verified the pinned links to the [status report](https://github.com/Drakosfire/DungeonMindBuddy/blob/3fbf800e0f134ba9a1396156c22c18c614c8f72d/report/REPORT-current-status.md) and [Graph benchmark](https://github.com/Drakosfire/DungeonMindBuddy/blob/3fbf800e0f134ba9a1396156c22c18c614c8f72d/report/world_graph_warm_path_benchmark.json).
- [#2523](https://github.com/Drakosfire/DungeonMindBuddy/pull/2523) retired the vendored BMAD workflow and project context. Caller checks covered open PRs and local worktree heads, and all 16 Mirathorn historical fixture tests passed.

**Remaining decisions**

| Scope | Owner | Revisit when |
| --- | --- | --- |
| Cursor workflow guidance and the design-agent export | Buddy documentation and agent workflow maintainers | PR #2406 settles overlapping guidance and operator uses of `review_external_pr.py` and Cursor skills are accounted for. The mirror is the documented pickup path for the user-managed ChatGPT Project Sources upload. Before removing it, generate the upload set from the canonical index, verify its paths and links, and confirm the upload operator can use the generated set. |
| Retired Graph bootstrap and checkout-local Combat HTTP routes and wire types | Buddy Graph and Combat API maintainers | The documented statblock/Combat dogfood workflow replaces or retires `scripts/live_dogfood_check.py --server-url`, whose HTTP probe expects success from the retired `/api/live/combat/current` endpoint. Account for external callers and accept the 410-to-404 change before removal, and the cutover witness, reviewed first-World initialization and World-owned Combat suites can verify the replacement paths. Coordinate other Graph client cleanup with #2405. |
| Static Combat importer and Mireward prep viewer | Buddy Combat and local dogfood maintainers | A verified World-owned import path handles the retained saves or the operator retires them. Workspace seeding and Play and Tiptap fixtures must still resolve their retained inputs before the viewer is removed. |
| Standalone Graph demo | Buddy Graph maintainers | Local `/graph` can reproduce the demo's retained fixtures and operator workflow, or the owner explicitly retires them. Run the dedicated demo and local Graph checks before removal. |
| Extraction lab and generated eval output | Buddy ingestion and evaluation maintainers | Retained experiments and their inputs are inventoried, reproducibility and test classification are verified, and dated session-event output work is coordinated with #2474. Preserve the production recap runner and its owning tests. |
| Corpus, large artifacts and adopted World evidence | Buddy corpus and World recovery maintainers | A specific relocation or deletion has provenance and indexing checks, plus replay or recovery proof. The 5.5 MB approved adoption bundle remains pinned input to the existing-World adoption proof. |
| Legacy import CI and other verification lanes | Buddy CI and deployment maintainers | The affected import or runtime contract has been explicitly retired or a replacement demonstrates equivalent coverage, including idempotence and rollback for legacy Agent import. Recheck test classification after any removals. |

## [IDEA] Follow-up cleanup and optimization sweep

**Last verified:** 2026-11-12 @ `4428b90`

| Candidate | Owner | Evidence and next check |
| --- | --- | --- |
| Retire the original Agent launcher PNG from the active tree | Buddy frontend | `dungeonbuddy-agent.png` occupies 1.44 MB and the launcher now imports the generated WebP. The performance handoff retains the PNG as the regeneration source. Pin the source and verify that the WebP can be regenerated before moving it out of the active tree. |
| Retire checkout-local statblock and Combat dogfood tools | Buddy Combat and local dogfood | The historical runbook still points to `live_dogfood_check.py` and `live_dogfood_reset.py`. The live Play runbook also names the checker and CI classifies both test files. Confirm operator usage and equivalent World-owned smoke coverage, then pin the historical procedure and reconcile the CI inventory before removing tools. |
| Reuse the World catalog between the picker and selected-World provider | Buddy frontend and hosted auth | Both paths call `listWorldContainers`. Measure the picker-to-selection request sequence and consider sharing a result scoped to the signed-in account. Verify refresh after World creation, account switch, sign-out, and stale response handling. |
| Trim repeated local Live Control reads | Buddy local dogfood | `LiveControlApp.refreshAll` reloads surface, events, jobs, and Plan after Chat, layout saves, and accepted commands. Measure the request sequence and prove which projections each operation invalidates before narrowing refreshes. Verify local Chat and command readback. |
| Move the PR43 multimode report out of the active tree | Buddy evaluation maintainers | The 1.28 MB report basename had no tracked text references at this revision. Check directory-glob readers, reproducibility and retention expectations, then pin the report before removal. Keep the C1S13 equivalence report while its deep-dive emitter reads it. |
| Move developer tooling out of the production Python environment | Buddy packaging and CI | The production Dockerfile runs `uv sync --locked --no-dev`, but `pytest`, `pytest-cov`, and `ruff` are declared as runtime dependencies. Trace imports and build tooling, move verified developer-only dependencies to a dev group, then compare the image inventory and verify locked CI, migrations, and hosted smoke. Audit `paramiko` separately for operator and transitive consumers. |
| Avoid rebuilding Graph label and connection lookups on unrelated renders | Buddy Graph UI | `NativeGraphDemo` rebuilds labels for every node and filters edges for the selected node during render. Profile a large World before choosing a memoized lookup or adjacency index. Verify selection history, labels and connections after graph revisions, and use the merged #2518 explorer as the profiling baseline. |
| Keep native Graph demo build output out of Git and the Docker context | Buddy frontend tooling | The dedicated Vite config defaults to `apps/live-control-ui/dist-native-demo`, and `git check-ignore` found no rule for a file under that directory. Check the documented build and server asset lookup before adding narrow ignore rules or moving the default under an ignored output directory. |
| Refresh local UI dependencies when the lockfile changes | Buddy local developer tooling | `./run` gates `npm ci` on whether `node_modules` exists. A checkout can keep old dependencies after a branch or lockfile change. Verify clean, unchanged, and changed-lockfile launches before adopting a lockfile-based freshness check. |
| Isolate legacy Mireward static routes from the default Vite server | Buddy frontend tooling and local dogfood | The always-on plugin handles `/index.html` before the app entry and serves files from repo-level Docs, corpus, evals and scripts prefixes. Inventory the legacy page fetches, then put the plugin behind an explicit development entry or narrow its mount. Verify both normal Buddy entry URLs and the retained prep workflow. |
| Reduce production frontend build inputs | Buddy packaging and frontend | The Docker build copies the complete UI directory, and its source type-check needs a synthetic statblock fixture from the test tree. Trace story and fixture imports and evaluate a production build target with explicit inputs. Compare cold and incremental builds and verify the production bundle, Ladle stories, and CI type coverage. |
| Consolidate Python package imports and copies | Buddy runtime and packaging | The slim image contains an 8 MiB source tree plus installed Buddy packages. Runtime imports use both the `src.` namespace and installed top-level packages. Inventory both import forms and path-relative assets before choosing a canonical layout. Verify migration discovery, module identity, hosted startup, and local tooling before dropping a copy. |
| Separate periodic readiness from full operator preflight | Buddy deployment and runtime | Compose calls `/health/ready` every 60 seconds. Hosted readiness invokes the full preflight, which enumerates World heads and checks campaign, ingest, and source roots in addition to application state. Measure query counts and probe duration on representative data. Preserve outage and schema-drift detection while evaluating a cheaper recurring check and keep detailed diagnostics available to operators. |
| Share the locked Python setup across CI workflows | Buddy CI | Five workflows repeat the pinned uv setup, Hermes patch preparation, and locked sync with caching disabled. Consolidate the common steps while preserving each workflow's checks and pinned toolchain. Measure setup time before considering a cache, and keep the independent cold production build as a release check. |
| Reconcile legacy Agent import CI triggers with what the job verifies | Buddy CI and application state | The workflow runs import tests and the classification inventory, but its pull-request filter omits the inventory and runner inputs, including `ci/test-classification.json` and `scripts/ci_contract.py`. Map the dependencies to the existing contract workflows before broadening triggers or moving the tests. Verify both import regression and inventory-only changes exercise the intended gate. |
| Measure the cost of precompiled Python bytecode in the production image | Buddy packaging and runtime | The slim image has 5,827 compiled Python files totaling 89.1 MB inside the virtual environment, and the Dockerfile enables `UV_COMPILE_BYTECODE=1`. Build matched variants and compare image size, cold startup to readiness, and worker startup. Check dependency-supplied bytecode separately and retain compilation where the measured startup gain warrants the space. |
| Measure a hosted startup path without eager Agent host initialization | Buddy hosted runtime and Agent maintainers | The slim image includes Hermes CLI and plugin packages, and the FastAPI lifespan calls the Hermes host getter at startup. Trace hosted route policy and measure the getter's startup cost before changing initialization. Verify hosted auth and Graph startup, local Agent first use, and shutdown after both used and unused runs. Keep Alembic and DungeonMind's Postgres dependencies in scope for migration verification. |
| Verify hosted asset caching and compression at the edge | Buddy deployment and frontend | Buddy serves built files through FileResponse without explicit cache lifetimes. The checked-in Nginx fragment has no asset-specific caching or compression directives. The retained slim image has 151 JS, CSS, and MJS assets totaling 5.98 MB raw or 1.73 MB when individually gzipped offline. This measures the build inventory, not startup transfers. Inspect inherited edge settings during deployment rehearsal. Measure cold and repeat loads, validate cache behavior for fingerprinted assets and HTML across a rollout, and verify authenticated and streaming routes separately. |
| Consolidate byte-identical statblock OpenAPI snapshots | Buddy statblock integration | The `generated/` and `openapi/` copies of `dungeonbuddy-statblocks-v1.json` share the same 188,474-byte Git blob. Determine which path is required by generation and upstream transcript provenance, then keep one canonical artifact if regeneration and schema/hash checks pass. |
| Resolve duplicate Graph gold fixture paths | Buddy Graph evaluation | Four candidate Graph gold files are byte-identical across the benchmark catalog and example fixture trees. The catalog and legacy evaluation helpers still reference those trees. Trace manifest-relative resolution and keep both contracts until fixture validators, comparison tools and local gold review pass against a shared source. |
| Consolidate identical Play evidence screenshots | Buddy Play verification | Three named witnesses in the decision cockpit recut report resolve to the same 123,598-byte Git blob. Check whether identical output is the intended proof for the unselected, cleared, and reloaded states. If it is, link each witness to one canonical screenshot and preserve the original paths in a pinned snapshot. Otherwise recapture the missing evidence before pruning. |
| Reconcile duplicate Mirathorn experiment outputs | Buddy evaluation maintainers | The experiment-suffixed council room question set and trace match their unsuffixed counterparts byte for byte. The Wave 5 archive cites the suffixed question set. Check replay inputs and path-based readers, pin the cited experiment outputs, and consolidate only after the replay and report links still work. |
| Scope hosted World catalog reads before materializing records | Buddy application state and hosted auth | The hosted World collection loads all managed Worlds, native bindings, and grants through the catalog service before filtering by owner and configured access. Measure rows read and request latency on a representative catalog. Evaluate a scoped query while preserving owner checks, allowlist enforcement, transaction consistency, and fail-closed behavior. |
| Reuse pinned descriptors during Graph explorer reads | Buddy Graph runtime | The catalogue resolves a pinned read context, then the explorer opens another repository and reads the same revision to resolve the semantic profile for rendering. Count repository calls and compare latency for a representative Graph. Pass the immutable profile through the internal read path if it preserves the exact revision and the final access and binding rechecks. |
| Reduce PDF crop preview encoding and memory costs | Buddy Build frontend | BuildPdfPreview synchronously converts the crop canvas to a data URL and also uses the encoded image as the OCR component key. Profile capture time and memory for representative large regions. Evaluate asynchronous blob encoding and an explicit capture identity while preserving OCR reset, cancellation, and preview cleanup on recapture, page change, or unmount. |
| Measure repeated PDF OCR process and page rendering costs | Buddy Build and local OCR | Each OCR crop starts a configured Python subprocess and writes a temporary PNG. The retained-region renderer also starts Poppler to rasterize the page for each crop. Measure repeated crops on one page and separate worker startup, rendering, and inference costs. Evaluate worker reuse or bounded page reuse only if measured costs justify it. Verify source authorization on every request, exact revision and page geometry, timeouts, and cleanup. |
| Reconcile frontend Web Locks test doubles | Buddy frontend verification | The global setup models only the two-argument request signature and retains one promise per name. Production Combat uses the options overload, and Combat suites replace the global double with a specialized implementation. Inventory the semantics exercised by both and consolidate shared behavior where appropriate. Verify contention, ifAvailable, missing Web Locks, and test isolation before switching consumers. |
| Verify removal of the unused GraphExtractionOptions module | Buddy ingestion maintainers | The backend module-name scan across runtime, scripts, evals, tools, and tests found no importer for graph_extraction_options.py. An exact symbol search on main found only the class and its return annotation. The live preview runner uses CategoryGraphExtractionOptions. Check open ingestion branches and dynamic or external imports before removal, then run the preview runner and category extraction contracts. |
| Reduce repeated application-state schema checks and connections | Buddy application state | World catalog reads call assert_at_head before opening a separate unit of work. The schema check opens its own connection, performs up to three SQL reads, and resolves the packaged Alembic head. Measure connections and query counts across representative catalog and workspace operations. Evaluate reusing the operation connection or the immutable packaged head while preserving live schema validation, rollback, and disposable database isolation. |
| Bound saved document list reads for large Worlds | Buddy application state and Plan/Build | The work-object list query sorts every matching row by update time and fetches the entire result. Measure row count, response size, and time to open Plan and Build on a large World. If pagination is warranted, preserve World and campaign scopes, use a stable tie-breaker, and keep exact document selection working across page boundaries. |
| Reduce base64 round trips for original media reads | Buddy media runtime and frontend | The original image endpoint encodes staged bytes into JSON, and useSavedMediaImage decodes the data URL back into a Blob. Measure transfer and peak memory for representative originals. Evaluate an authorized binary response while preserving owner checks, no-store behavior, staged previews, downloads, and object URL cleanup. |
| Pass rendered PDF crops directly to the internal OCR service | Buddy Build and local OCR | Two server-side routes base64-encode a rendered PNG to construct PdfCropRequest, then read_crop decodes it before validating and launching OCR. Share the validated bytes path while retaining base64 parsing at the public request boundary. Verify size and image limits, source authorization, and OCR busy and failure responses. |
| Use explicit local stack startup probes and report partial startup accurately | Buddy local tooling | The launcher polls both API docs pages and suppresses failed probes outside the Graph profile before printing local stack up. Compare the owning liveness endpoints and keep the Graph profile preflight for deeper checks. Verify healthy startup, a failed child process, and reuse of an already running service. |
| Track ownership through local stack shutdown | Buddy local tooling | The launcher records wrapper PIDs for uv and npm, signals those PIDs on shutdown, and removes every PID file in the shared run directory. Exercise interrupt and early child failure with reload enabled and with a reused service. Verify that spawned listeners exit, reused services and their PID files survive, and cleanup runs once. |
| Measure workspace draft snapshot and persistence costs | Buddy workspace authoring | The draft coordinator clones the full editor state with a JSON round trip before queueing it, and recovery storage serializes it again for persistence. Profile large pages during typing and queued writes before sharing serialized snapshots or coalescing work. Verify unmount, concurrent tabs, stale writes, and recovery copy retention. |
| Give retained PDF shortcuts a browser storage lifecycle | Buddy Build frontend | Each distinct capture locator adds a localStorage entry and opening the preview scans all storage keys to rebuild the list. The shortcut list offers reopen but no removal. Measure growth with repeated captures, then evaluate explicit shortcut removal and scoped indexing. Verify existing entries remain readable and removing a shortcut preserves the durable PDF and its evidence. |
| Make the deployment smoke block fail when any required check fails | Buddy deployment | The production runbook runs image ID, port, liveness, and readiness checks as separate commands before its final chained SPA and auth checks. In an ordinary Bash session the block can end successfully despite an earlier failure. Rehearse a scoped fail-fast block with injected failures for each check, and verify the operator can still use the recorded release variables for rollback. |
| Rehearse the production image rollback commands | Buddy deployment | The runbook saves a previous image and Compose override and describes when rollback is safe, but leaves the operator to reconstruct the commands. Add the exact prior-image restore and image-ID verification steps for the saved Compose project. Rehearse with a disposable stack, including an incompatible schema case that stops before changing the serving container. |
| Align browser deployment smoke with the session request | Buddy hosted auth and deployment | The runbook tells the operator to watch current-user in the browser network panel, while HostedAuthGate calls /api/auth/session. Document the actual startup, sign-in, and sign-out requests and keep direct API probes explicit. Verify the sequence using the hosted browser fixture and real deployment rehearsal. |
| Parse Build source Markdown once for outline and reader | Buddy Build and Markdown reader | BuildSourceReader computes headings by parsing the Markdown, then MarkdownDocumentReader parses it independently for rendering. Both memoize within their own component. Measure large source open times before sharing the parsed representation. Verify frontmatter handling, duplicate heading IDs, and source line navigation. The exported MarkdownDocumentOutline component itself appears only in its test, while its heading helper has live callers. Check active branches before removing the component. |
| Reuse a verified PDF source within an active Build preview | Buddy Build frontend and source authority | Retaining another region after admission posts to the reopen endpoint, downloads the whole PDF, and restarts PDF.js through the sourceFile effect. Measure bytes and parse time across repeated captures. Check whether locator validation can stay authoritative while an active preview reuses already verified bytes. Cover permission changes, revision mismatch, and explicit reopen after reload. |
| Measure saved Agent conversation list sorting | Buddy application state and Agent | Conversation and turn reads already cap result counts. The conversation list filters by World and optional status, then sorts by updated_at and conversation_id. The tracked conversation indexes include the one-active-per-World constraint. Check the deployed index inventory and measure plans for large conversation libraries before adding an index. Verify archived and active ordering and the cost of writes. |
| Fingerprint shipped statblock theme assets | Buddy frontend packaging | Four fonts and the parchment image live under public/statblock-theme and CSS references fixed root URLs. Check external URL consumers before moving the assets under Vite-managed imports. Verify base-path behavior, font and parchment rendering in app and Ladle, and caching across builds. The tracked assets are still referenced by the theme CSS. |
| Share concurrent saved-image resolution within the current access generation | Buddy media frontend | Each mounted image occurrence calls useSavedMediaImage independently, fetching metadata with no-store and fetching original bytes for staged assets. Measure duplicate calls when the same image appears across the editor and reader. Evaluate sharing in-flight reads while preserving generation checks, staged-to-ready transitions, cancellation, and Blob URL cleanup. |
| Remove retired merge materialization client wrappers | Buddy Graph Review frontend | Both merge-reconciliation materialization endpoints return 410. On main their two frontend wrappers appear only in the API module and the retired notice component test. Check active Graph Review branches and #2405 for overlap, then remove unused wrappers and type declarations while retaining coverage for the live notice and governed prepare/commit path. |
| Cancel stale Graph Review gold projection requests | Buddy Graph Review frontend | The gold projection effect suppresses state updates on cleanup, while the API wrapper has no abort signal and the request continues after a campaign or session change. Measure requests during rapid lane switches. Consider aborting obsolete reads while preserving explicit reload, error reporting, and the current lane’s result. |
| Avoid rebuilding the corpus inventory for each Live Control source bundle | Buddy local runtime and corpus tooling | The source bundle builder calls build_library on each invocation. The library performs multiple recursive walks, including a corpus-wide Markdown count. Profile bundle requests by scope, then evaluate a narrower inventory or verified reuse. Check file changes, scope filtering, and source locators before changing the read path. |
| Read only the needed Live Control session artifacts | Buddy local runtime | The events, jobs, and surface routes each call load_session, which parses packet, layout, events, and jobs even when the route returns only a subset. Several packet-only routes use the same loader. Count files opened during a Live Control refresh and measure long event logs before adding narrower readers. Preserve missing-file handling, event ordering, unknown cursor behavior, and Chat refresh when narrowing the read path. |

## [IDEA] Resume answer-citation experiments after fundamentals settle — captured 2026-11-10
**Kind:** RESEARCH / RESPONSE ASSESSMENT
**Owner:** Buddy response composition
**Captured:** 2026-11-10
**Last verified:** 2026-11-10
**Context:** The operator selected ingestion delivery reconciliation and completion of older fundamentals, explicitly parking citation work. Voice design is separately deferred to the operator; the tighter prompt is a fixed control.
**Insight:** The citation-first Q15 pilot reached the actual provider wire and all eight response segments used structured citation handles before prose. Selected citations passed review, but coverage fell9/9→8/9 by omitting the approximate Abyssal-like scroll clue. No adoption or retry is justified by that one result.
**Action:** Preserve the failed pilot and baseline. Do not resume answer-citation optimization, schema-order experiments, additional citation judges or prompt layers during fundamentals closeout. Existing source-integrity and citation checks remain in force; this is no waiver of them.
**Surfaces when:** Ingestion delivery, QA fundamentals, bounded worldbuilding and real collaborative follow-through have settled and the operator explicitly selects citation work again. This entry grants no implementation or provider authority.
**Refs:** `Docs/Plans/HANDOFF-COMPOSITION-citation-first-experiment.md`; PR2357; retained `out/response-writing-contract-v1/citation-first-experiment-v1/`.


## [IDEA] High priority — shared grid page constructor
**Priority:** HIGH — explicitly requested by the operator.
**Kind:** DESIGN → bounded implementation slices
**Owner:** Build / shared Surface authoring
**Captured:** 2026-10-24
**Last verified:** 2026-10-24 @ `c74b5082ead867cd28fb302935dc05965dc1f4c0`
**Context:** Edge authoring dogfood: the author wants to move and resize artwork on a snapping grid, then compose images, editable text, tables and callouts intentionally on the page.

**Direction:** Keep Tiptap for writing; define shared row/column layout containers, stable section identities and durable layout representation. Preserve reading order for retrieval, citations and Markdown export. Distinguish this page-layout work from the deferred infinite spatial workspace below.

**First slice to design:** Move and resize one existing image on a visible snapping grid. Decide persistence ownership and representation before implementation; image centering is an immediate separate convenience, not completion of the grid constructor.

**Exit proof:** Ordinary controls place/resize an image; Save, reload and reopen preserve placement, undo/recovery preserve authorship, and narrow screens stack content predictably. Later slices may add adjacent editable text, tables/callouts and agent suggestion placement using stable section identities. Freeform overlap, pan/zoom and connectors require separate selection.

**Surfaces when:** Planning Build authoring, media placement, shared page layout or proposal insertion. Product sequencing remains owned by `Docs/Roadmaps/ROADMAP-demo.md`; high priority does not activate implementation or resume the paused broad goal.

**Refs:** Edge source `bba72416-9dfe-49bb-add0-21a346e9a421`; `apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx`; `apps/live-control-ui/src/tiptap/MarkdownDocumentAdapter.ts`; conversation `01a0ef89-ca57-7b82-9c9c-215b02d0fc3b`.


## [DEFERRED] Define independent source-artifact archive and restore
**Owner:** APP-STATE / source lifecycle
**Captured:** 2026-08-11
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** An operator needs to withdraw or restore an independently admitted source, such as a recap, while preserving exact historical evidence.

**Current boundary:** Workspace Trash handles Build and Plan documents and Play sessions. The source service persists immutable artifact and revision identities and serves their Markdown, metadata and scope. It exposes no independent archive or restore operation.

**Next slice on trigger:** Define what source archive changes for discovery, what historical citations can still open, and what exact identity restore preserves. Then identify the owning mutation before adding any UI.

**Refs:** `src/application_state/source/service.py`; `apps/live_control_server/routes/workspace_lifecycle.py`; #1445–#1447.


---

# Cross-owner questions — not implementation blockers by default

- **Generation liveness:** reproduce any false timeout against the current
  GenerationEngine/SERVER path before assigning an owner or designing heartbeat
  machinery. The old claim that DungeonMind owns provider generation is stale.
  OverMind's open backlog-consolidation proposal (#22) is reference, not activation.
- **Authored lore publication:** current governed ingestion/review/publication
  supersedes the pre-cutover missing-elevation premise. Remaining source fidelity,
  semantic richness and fresh-World acceptance belong to the product roadmap and
  the owning knowledge contracts, not a duplicate root BLOCKED item.

# IDEA

## [DEFERRED] Background suggestions for missing World graph relationships
**Owner:** Buddy suggestions and review
**Captured:** 2026-10-13
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator selects proactive source-backed suggestions as a product capability.

**Current boundary:** Agent-requested saved-source relationship review already exists (#1751, #1753). It validates exact supporting quotes and requires confirmation before publication. No background candidate scheduler or cross-run suppression workflow was found in current callers. The original Sara/Frank example requires fresh verification before it can serve as a defect.

**Next slice on trigger:** Reuse the existing candidate/review/publication owners for one opt-in suggestion flow. Define when a suggestion is useful, how prior review suppresses repeats, and when to ask the author.

**Refs:** `src/application_state/agent_conversation/relationship_review.py`; `tests/application_state/test_relationship_review_postgres.py`; #1751, #1753.

## [DEFERRED] Compare retrieval controllers using existing native actions
**Owner:** Retrieval evaluation
**Captured:** 2026-09-26
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** Independent evaluation identifies controller choice as a measured retrieval bottleneck and the operator selects a comparison.

**Current boundary:** Native retrieval, Jev decision drivers, trace capture and independent benchmark assessment already exist. The old proposal's first step of constructing a new exploration environment must be re-scoped around those owners.

**Next slice on trigger:** Pin one ordinary request and its admitted evidence. Compare controller decisions through the same existing native actions and benchmark assessment. Measure support, coverage, latency and calls. Determine whether successful traces warrant further controller research.

**Refs:** `src/application_state/agent_conversation/native_retrieval.py`; `apps/live_control_server/services/build_jev_driver.py`; `apps/live_control_server/services/plan_jev_driver.py`; `evals/buddy_benchmark/`; [original research capture](Docs/Backlog/BACKLOG-graph-exploration-system-one-controller-lab.md) as historical design input.


---

# DEFERRED

## [DEFERRED] Composable spatial workspace and selectable themes
**Owner:** Buddy presentation
**Captured:** 2026-09-26
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator selects spatial composition or selectable themes for implementation.

**Current boundary:** Shared presentation components and graph canvas exist. Current source has no saved multi-object workspace arrangements or selectable theme-pack contract. The shared grid page constructor above owns the separate request for snapping page content into rows and columns.

**Next slice on trigger:** Select either saved spatial arrangements or selectable themes and bound it independently. For spatial arrangements, investigate existing canvas/projection components and define ownership of positions, sizes and camera state. For themes, investigate existing semantic tokens and define one reversible theme selection. These are separate capabilities.

**Refs:** [presentation substrate plan](Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md); `apps/live-control-ui/src/localWorld/worldGraphCanvas/`; shared grid page constructor entry above.

## [DEFERRED] Create a campaign inside an existing World
**Owner:** Buddy campaign UX + DungeonMind campaign membership
**Captured:** 2026-08-11
**Last verified:** 2026-11-10 @ Buddy `8a9ad7902`, DungeonMind `430c1a6d`
**Trigger:** An operator needs to start a new campaign in an existing World through ordinary controls.

**Current boundary:** DungeonMind's campaign ingest-context route requires an existing campaign membership. Buddy's #1860 restored two retained memberships via an offline repair. Neither provides a user-facing creation operation.

**Next slice on trigger:** Define a DungeonMind-owned membership creation operation and the minimal Buddy flow that uses it. Prove the new campaign can be selected and admit its own sources in the existing World.

**Refs:** [Campaign membership repair](Docs/Plans/HANDOFF-BUILD-elderwyld-campaign-membership.md); `src/dungeonmind/service/api.py` in DungeonMind.


## [DEFERRED] Verbatim source phrase grounding in the frozen TL01 evaluation
**Owner:** Temporal grounding evaluation
**Captured:** 2026-08-01
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** A real product use case selects a temporal capability that consumes this renderer, as required by the TL01 close decision.

**Current boundary:** The original renderer check still fails when its cited snippet lacks the requested verbatim phrase. TL01 evaluation remains frozen. Current recap ingestion and source reads use exact stored spans (#1941, #1965), but those changes do not resolve this separate evaluation defect.

**Next slice on trigger:** Reproduce the retained failure through the selected consumer, then prove a known-good phrase grounds through both relevant lanes before revising cohorts or prompts.

**Refs:** [TL01 close decision](Docs/Design/DECISION-tl01-temporal-prompt-calibration-close.md), section 7; `evals/graph_memory_layer/temporal_shadow_grounding_path.py`; #1941, #1965.


---

# Delegated workstreams — pointers only, no root status

The rows below preserve discoverability for capabilities removed from root without creating a second status owner.

| Capability / residual | Status owner | Root disposition / owner health |
|---|---|---|
| Remaining C1/C2 source coverage and the authoring, preparation and Play journey | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) | The [DEMO steward handoff](Docs/Plans/STEWARDS-HANDOFF-demo.md) describes the mandate. The [old Demo-Ready ladder](Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md) and [CON-READY anchor](Docs/Plans/STEWARDS-ANCHOR-con-ready.md) are historical evidence. |
| Build ready-state Reload / Discard-local actions | Demo-Ready Stage 6 / current Markdown Canvas ownership | Removed from root READY on 2026-09-08. It belongs with the real-material edit/save/reopen dogfood rather than an independent pre-Stage-6 dispatch. |
| Hermes optimistic transcript + multiline composer | Demo-Ready Stage 7 Agent work | Removed from root READY on 2026-09-08. Useful UX remains, but Agent-on-Ingest/context/observability sequencing owns when it should ship. |
| Hermes prompt/configuration quality + revision-aware cross-turn evidence deduplication | Demo-Ready Stage 7 / Agent observability | Removed from root IDEA on 2026-09-08. Reproduce against the assembled cross-surface Agent before creating an independent slice. |
| First-class statblock and roll-table display across surfaces | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and owning Threat/Play contracts | Assess remaining cross-surface behavior there; the Build Workbench launcher is already delivered. |
| Durable Combat board / easy roster loading | CON-READY / Play + Combat authorities | Removed from root IDEA. Combat remains a real product need, but it is later than current Demo-Ready continuity and must be re-anchored when Play/Combat resumes. |
| Native Play board usability / Beat-first current moment | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and owning Play design | Re-anchor with DEMO when Play work resumes. |
| Rich Threat authoring, statblock presentation/media, and related conversation behavior | [Buddy product roadmap](Docs/Roadmaps/ROADMAP-demo.md) and current owning handoffs | The [Threat roadmap](Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md) retains historical design and acceptance wording. |
| Historical Campaign-Supergraph residual labels such as PR380E/PR380F and exact-run review sequencing | current Demo-Ready/CUTOVER-era authorities, not the old tracker by default | Historical design ancestry only. Do not dispatch directly from stale PR380 labels without re-anchoring against the post-cutover DungeonMind boundary. |
| Broad “durable database persistence for GM work across worktrees” umbrella | Stage 2A/2B proof + domain-specific successors | Retired as a root umbrella on 2026-09-08. Durable APP-STATE on `54331` and durable DungeonMind World on `54330` now exist and have recovery proof; remaining Combat/statblock/source-coverage/off-laptop work has narrower owners. History remains in Git. |
| Broad “move durable Buddy runtime state out of checkout-local `out/`” umbrella | Stage 2A/2B + Demo-Ready Stage 2C/8 + domain owners | Retired as a root umbrella on 2026-09-08. Checkout-local `out/` is no longer accepted product authority for the recovered core state; surviving residuals must be named by domain rather than reopening the umbrella. |
| Browser-local statblock draft persistence with untrusted receipt restore | Statblock Workbench / future durable draft owner if dogfood requires it | Retired from root READY on 2026-09-08. Browser-only storage is no longer an acceptable durability target. The safety insight survives: restoring mutable draft bytes must never restore a trusted validation receipt; any successor should use a domain-owned durable authority plus fresh validation. |
| Build/Plan shared Threat projection + campaign-useful glance | merged PR #512 | Implemented; regressions should be filed as current defects rather than reviving the old capability ticket. |
| Abandoned `/surface` / `SurfaceShell` cleanup | current source tree | Removed from active backlog after current-tree search found no owner to dispatch; resurrect only from a concrete current consumer. |

## Retained UI/product design input

The earlier detailed nine-goal inventory is in Git at the audit anchor. Keep the
following pressures without treating them as nine parallel implementation plans:

- GM-oriented navigation and a compact shared shell, preserving context/drafts.
- Playable content and usable World objects before technical/debug metadata.
- Ingest as source-faithful memory review; Build as ordinary authoring.
- Combat and roll tools integrated into the session, with owned runtime state.
- Contextual optional Agent help and low-cost presentation iteration.
- Cards' purpose, capacity, editing, boundaries and linked detail; see the current
  roadmap and OverMind's captured operator design request.

Recent navigation, notes, shared toolbar, recovery, media and session-evidence
work is already recorded in the roadmap. Reproduce a residual before dispatching
an old UI repair. Of Conks and other prototype evidence remain reference material;
a prototype is not a new durable authority.

## Hygiene history

- 2026-11-10: reverified the next four entries. Retained the distinct residuals, removed already-shipped portions, and replaced the proposed controller environment with a comparison through existing native retrieval and evaluation.

- 2026-11-10: audited the four oldest active entries against Buddy main `8a9ad7902` and DungeonMind main `430c1a6d`. Archived the broad ecology-pass proposal, retained the unresolved frozen TL01 defect, and reverified two deferred lifecycle gaps.

- 2026-11-10: checked delivery through Buddy main `b0585f6d9`; archived the Build Statblock Workbench launcher, recorded completed image authoring slices, and corrected superseded roadmap pointers.

- 2026-08-16 pass 1: 74 active headings → 29; see `Docs/Reports/BACKLOG-HYGIENE-2026-08-16.md`.
- 2026-08-16 pass 2: converted root backlog from “worth doing” list to strict dispatch inventory; tracker-owned work delegated without duplicate status and READY reduced to seven bounded slices.
- 2026-09-08 pass 3: re-anchored after PR #694 and the Stage 2A/2B durability work. Status-bearing headings reduced **17 → 7** (`2 READY`, `2 BLOCKED`, `3 DEFERRED`). Demo-Ready/CON-READY/Threat-owned work moved to pointer-only delegation; pre-cutover graph-authority assumptions were corrected; broad durability umbrellas were retired after real APP-STATE/World recovery proof; browser-local statblock persistence was retired as a product durability target.


## [DEFERRED] Propose edits to an existing related page from the current workspace
**Owner:** Build authoring
**Captured:** 2026-10-16
**Last verified:** 2026-11-10 @ `8a9ad7902`
**Trigger:** The operator asks to revise an existing related page while retaining the current workspace.

**Current boundary:** Related saved-page context, connected-page creation and saved-source relationship reviews have shipped. Build text proposals still capture one page as their mutation target. A request for a different page returns a destination mismatch or requires handoff. The broad original ticket's connected-page and relationship portions are already covered.

**Next slice on trigger:** Capture an explicit existing destination document and passage, show an editable proposal through the shared review host, and preserve the originating workspace. After saving, reuse the existing source and reviewed publication flow for any proposed Graph changes.

**Refs:** `apps/live_control_server/services/build_document_proposal.py`; `src/application_state/agent_conversation/collaboration.py`; `src/application_state/agent_conversation/relationship_review.py`; #2127, #2129, #2273.
