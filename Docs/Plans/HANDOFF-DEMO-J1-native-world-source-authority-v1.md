---
pr_body_template: |
  ## Handoff pointer
  - Workstream: DEMO / J1 native World source authority
  - ACTIVE handoff: `Docs/Plans/HANDOFF-DEMO-J1-native-world-source-authority-v1.md`
  - Topology: serial; one DEMO implementation PR, no merge until PRIME review
  - PR title: `DEMO: admit imported sources into native World authority`

  ## Review contract
  The existing Build import creates a managed World and commits one exact
  `worldbuilding_source` document. Buddy bootstraps that World’s native
  DungeonMind space, admits the committed workspace-document-registry revision as immutable source
  plus whole-document context evidence, and can read/replay that exact admission
  after repository/process recreation. No extraction, assertions, retrieval,
  Plan changes, or claim that the source is already accepted canon.
---

# HANDOFF — DEMO J1: native World source authority

**Created:** 2026-09-28  
**Status:** ACTIVE — PRIME architecture compatibility PASS; serial implementation authorized  
**Workstream / owner:** LOCAL DEMO ACCEPTED / DEMO J1, Buddy owns product orchestration  
**Direction:** STEWARD → CODE → PRIME  
**Activation base:** Buddy `main@f8b923875f9444a1addfb2472a2b8fab35eceb4c` (merged #785)  
**Activation gate:** satisfied — #785 merged; MIND #83 empty initialization and #85 native text/evidence admission merged; PRIME accepted the bounded Buddy integration, with explicit new-world identity policy `managed_world_id == space_id`. The policy is Buddy-owned; it is not an old World Container guarantee.  
**Dependency lease:** PRIME’s 2026-09-28 settlement in open draft PR #763 pauses that stale Rules candidate and exclusively transfers `pyproject.toml` + `uv.lock` to this serial DEMO slice for adoption of MIND #85. #763’s rules code is preserved and must re-anchor after this dependency settles; do not modify #763.  
**Exact external pins:** DungeonMind #85 merge `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc`; WorldKeeper unchanged.  
**Buddy domain/profile pins:** `dungeonbuddy.world` revision `2`, digest `d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd`; `dungeonbuddy.dnd5e` SemanticProfileDescriptorV2 revision `1`, digest `51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14`. Verify against Buddy’s accepted constructors before use; do not copy guessed JSON.  
**PR topology:** serial within DEMO; one assigned implementation PR only.  
**Implementation lane:** create a clean `codex/demo-j1-native-world-source-authority` branch/worktree from freshly fetched `origin/main` after this handoff commit. Record the exact resulting base before code. Never use the dirty detached checkout.  
**PR authorization:** after landing this ACTIVE handoff, open/update the single assigned PR without another operator prompt. Return exact-head implementation review and evidence to PRIME; do not merge.  
**Shared runtime/state:** PRIME owns existing UI/API/Generation processes and persistent demo DB targets. Do not start a duplicate server set, switch/restart its processes, or write to the persistent rehearsal databases from this implementation lane. Use isolated tests and a disposable Postgres target. Exact-head live product use requires coordination with PRIME’s runtime owner.

## §1 Mission and merge-ready invariant

Use the **existing ordinary Build import** for one managed-World `worldbuilding_source`, then connect its exact committed source revision to the same managed World’s native DungeonMind authority.

**Invariant:** after a successful ordinary import, Buddy can truthfully report whether the exact workspace-document-registry revision has been admitted into the World’s native space; its saved bytes, hash, source classification, visibility, origin link and evidence span are verified by MIND; a retry or fresh-process read returns the same receipt/source/evidence without a duplicate child or head rewind. An interrupted two-step lifecycle remains visible as a saved source with native admission pending—not falsely rolled back or called complete.

This proves source authority and provenance only. A source artifact/evidence span is **not** an extracted entity, accepted fact, relationship, retrieval result, or canon decision.

## §2 Accepted context and product seam

The exact base is after #785. Its terminal generation/recovery repair is merged at `f8b923875f9444a1addfb2472a2b8fab35eceb4c`; exact reviewed head `471a967d11e315b24fd5cfe5541f447753fb81f4`; three distinct review-head cycles / four formal review submissions (the final two submissions assessed the same exact head, the last after live acceptance); PRIME review records `5333492877`, `5333610809`, `5341223774`, and `5341878346`. The bounded #785 witness is not full DEMO/J1–J6 acceptance.

MIND owns the native persistence contract; Buddy composes its accepted primitives:
- `initialize_empty_knowledge_space` creates/replays only the native root.
- `publish_native_text_source_evidence` admits exact UTF-8 source bytes, immutable revision, evidence refs/span proofs and one child; it does not extract assertions.
- `get_head`, `get_revision`, `get_native_source_admission_receipt`, `open_native_text_source_access_context`, and `open_admitted_native_text` provide the bounded read/replay proof.
- Use `DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL` and the existing Postgres authority; never infer vNext state from legacy `world_heads` or route through the classic graph authority adapter.

The user-facing origin is Build’s current managed World → `worldbuilding_source` import/commit path (`BuildSurfacePage`, `useBuildWorkspaceDocumentController`, workspace-document registry/routes). The server must take one coherent `get_workspace_document_snapshot` after commit: record, canonical committed Build Markdown, `loaded_revision`, and matching content digest. For `worldbuilding_source`, this is the existing workspace-document registry/file-backed authority, not APP-STATE Content. Treat the snapshot’s returned Markdown string as the exact product text to encode as UTF-8; its digest is computed over that representation. Do not claim original on-disk newline bytes when the registry has normalized them. Do not use browser-posted Markdown for admission or treat the legacy Buddy SourceArtifact digest as native-body bytes; its registry path normalizes trailing newlines. The workspace snapshot is the source authority.

Buddy makes one explicit new-world policy: server-allocated immutable `world_id` is also vNext `space_id`; no derived or client-supplied space mapping. Use the accepted domain/profile constructors and exact digests above. The existing Build source record may carry a compatibility `campaign_id == world_id`; do not propagate that sentinel as a campaign scope or fabricate a campaign/session in native source metadata.

Source mapping for this bounded importer:
- only a committed, active `worldbuilding_source` with exact managed `world_id` and `source_domain == "worldbuilding"`;
- `source_classification = dungeonbuddy.source:worldbuilding` (already represented in Buddy’s V2 preservation fixture);
- `authority = primary` means the imported GM-provided document is the original source, not that any in-world assertion is accepted;
- GM-private visibility from the accepted `dungeonbuddy.visibility:gm` label; no public visibility;
- origin binds the Buddy workspace-document ID and exact registry revision token (for example, `registry-revision:<loaded_revision>`) in a stable Buddy namespace. The integer loaded revision is an opaque Buddy origin locator, not a native MIND revision; the native immutable source record carries the exact snapshot body/digest;
- no campaign/session domain metadata, since this source is World-global;
- one deterministic whole-body UTF-8 half-open span `[0, byte_length)`, exact slice SHA, role `context`, and stable caller-local span ref. This is intentionally coarse source evidence; it must not be presented as paragraph-level highlighting or fact extraction.

Use stable Buddy-derived initialization/admission identities. Initialization time comes from the immutable managed-World creation record. The source admission identity derives from World + workspace-document ID + `loaded_revision` + canonical snapshot digest. On retry, consult the native admission receipt and verify its origin, source revision/body digest, descriptor refs and exact read-back before returning success. New committed document revisions get new admission identities. MIND’s expected-parent check governs a new append; on stale-parent races, re-read and retry only the exact same snapshot/command when no receipt exists. Conflicting bytes or metadata fail closed.

PR #763 is open but draft/paused by PRIME’s durable body settlement; it no longer owns the two dependency files. Its changed `main.py` path is deliberately avoided by adding the new product endpoint to the already-mounted `workspace_documents` router. No other PR/lease may be assumed clear without a fresh changed-path census.

## §3 User-visible path and failure truth

1. Create a **fresh** managed World through the existing Build control (server allocates ID); no manual IDs or synthetic graph rows.
2. Import the pinned, human-normalized Of Conks Markdown through the ordinary Build source control as a `worldbuilding_source`; commit via the existing workspace-document source commit path.
3. After commit, ordinary Build flow calls Buddy’s native-source status/admit API using document ID and expected revision only. Server resolves the managed World and exact committed snapshot.
4. Show a clear `admitted` result with World identity and a safe source/evidence summary, or `saved; native admission pending` with an exact retry path. Retry must reuse the same document/revision and never create a duplicate source document.
5. Reselect/reload the source after API/repository object recreation; status resolves from MIND receipt/read authority. Open the admitted source and verify exact body/span hashes.

Failure contract:
- If World genesis succeeds but admission fails, retain the empty root and report admission pending; exact retry continues from it.
- If workspace-document source commit succeeds but MIND outcome is uncertain, read the deterministic MIND receipt and verify it; never blindly republish under a new ID.
- If the workspace revision changes between UI selection and server snapshot, require refresh/reselection; never admit stale browser text.
- Unsupported source kind/domain, missing/inactive/foreign World, wrong descriptors, digest/span mismatch, native space conflict or unavailable Postgres fail closed with a typed status and no alternate classic/campaign fallback.
- A changed document revision is a distinct immutable source admission; old native bytes remain. No update/delete/archive lifecycle or freshness claim is added here.

## §4 ACTIVE write lease

Expected implementation files; no code edits before this checked-in ACTIVE handoff:

- `pyproject.toml`, `uv.lock` — adopt exact accepted MIND #85 pin; preserve unrelated pins and resolve reproducibly.
- `apps/live_control_server/integrations/dungeonmind/native_world_source_admission.py` — Buddy adapter/service composition around accepted MIND initialization/admission/read/replay APIs.
- `apps/live_control_server/routes/workspace_documents.py` — add typed GET status / POST retry-or-admit endpoint on the existing router; do not edit `main.py`.
- `apps/live_control_server/services/workspace_document_registry.py` — only if needed to expose the existing coherent snapshot contract without a second read path.
- `apps/live_control_server/config.py` — only if the existing authority URL/repository factory cannot be reused; no new DB URL by default.
- `apps/live-control-ui/src/api/types.ts`, `apps/live-control-ui/src/api/liveApi.ts` — typed request/results; browser sends no body text, space ID, or descriptor authority.
- `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts` and its paired test — wire status, post-commit admission and exact retry; keep the saved document ID on partial failure.
- `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx` and its paired test — make pending/admitted status and retry visible for a selected source after reload.
- `tests/test_demo_j1_native_world_source_admission.py` — focused service/route and failure/replay tests.
- `tests/integration/test_demo_j1_native_world_source_admission_postgres.py` — disposable-Postgres persistent receipt/head/revision/body/span/reopen witness; zero skips for the required invocation.
- `apps/live-control-ui/src/api/liveApi.test.ts`, `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.test.ts`, and `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx` — route serialization and owning UI boundary.
- State-authority predecessor sync, in this same implementation PR: `Docs/Roadmaps/ROADMAP-demo.md`, byte-identical `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md`, `Docs/Plans/HANDOFF-DEMO-world-scoped-statblock-drafts-v1.md` (#785 completed state), and `Docs/Plans/HANDOFF-DEMO-world-owned-blank-plan-v1.md` (remove satisfied #785 blocker only; retain its independent PRIME contract gate and BLOCKED status).
- This handoff may receive activation/evidence pointers only; do not mark this in-flight slice complete or invent its future PR/head/review count.

Bounded discovery: at most three additional existing files under `apps/live_control_server/` and paired focused tests, only when a concrete direct route/service seam requires them. Name the exact paths/reason in handback before expanding. Any need for `main.py`, a new APP-STATE schema/migration, generic source lifecycle, WorldKeeper freshness, another repo, or MIND API changes is a stop-and-return-to-PRIME condition.

## §5 Exclusions and collision boundaries

No model/API generation calls; extraction; entities/assertions/facts/relationships; candidate graph publication; Agent retrieval/citations; Plan creation/editing/projection; world-object lens; classic graph read/write; source update/delete/archive lifecycle; migrations; provider or Generation services; user-created semantic aliases; new DungeonMind/WorldKeeper endpoints; new generic registry; campaign/session invention; or data repair.

Do not modify #763 or any path it still owns beyond PRIME’s explicit `pyproject.toml` / `uv.lock` transfer. Keep its Rules query implementation preserved and paused for post-merge re-anchor. Do not change the existing UI/API/Generation runtime set, the user’s other browser tab, or the persistent rehearsal DBs. A product live witness needs exact target/readiness from PRIME; no fixture rows or manual SQL/console setup.

The prior `HANDOFF-DEMO-world-owned-blank-plan-v1.md` remains a separate BLOCKED capability until PRIME accepts its own contract/lease. This handoff does not silently implement or supersede World-owned Plan persistence. The full LOCAL DEMO remains unaccepted.

## §6 Implementation sequence

1. Re-fetch current `origin/main`; verify this handoff, #785 merge, every open PR changed-path set, #763 settlement, current database dependency pin, and runtime ownership. Create one clean isolated worktree from remote main; record exact base and paths.
2. Implement immutable input mapping and typed native status/admission boundary. Prove no client body/space/profile authority enters the call.
3. Add deterministic idempotency/readback behavior, partial-state/failure tests, and MIND pin/lock update. Reuse accepted APIs only.
4. Integrate the existing Build source-import controller so an ordinary committed source is admitted and its exact pending/admitted state is visible after reselection/reload.
5. Run focused backend/UI cohorts, Ruff, frontend build/typecheck and cumulative diff checks. Run the real PostgreSQL integration against an isolated disposable target with zero skips. Verify from a fresh repository/service connection; do not touch PRIME’s persistent DB/runtime.
6. Freeze an exact head, independently review the cumulative diff and evidence, address findings on the same PR through review cycles. Open exactly one DEMO implementation PR, draft until required evidence is recorded; no merge.
7. Hand exact PR/head, test commands/results, dependency lock result, source pins, runtime/DB non-mutation proof, failures and limitations to PRIME. Do not claim full J1 or LOCAL DEMO acceptance from this source-authority slice.

## §7 Required proof

- API/service tests prove server-derived `world_id == space_id`, exact accepted descriptor hashes, exact committed Build snapshot text/digest, source mapping and whole-body byte span; reject browser body, mismatch, stale revision, unsupported source, foreign World, missing DB and descriptor drift.
- Initialization and native source admission are separate durable writes. Inject failure between them and prove a truthful empty-root/pending result followed by exact recovery.
- Native receipt lookup/replay verifies same source origin and IDs; exact replay creates no extra child/event and never rewinds a later head.
- Persistent Postgres integration: new World + committed source through the owning route/service; exact native head/revision/receipt/read-back; recreate repository/service/connection; retrieve exact source body/span through MIND access APIs; replay; same receipt and no duplicate child. Inspect only public repository/read APIs in production code; no direct SQL repair.
- Mounted Build proof: ordinary create/import/commit → automatic admission → pending recovery path → selected-source status after reload. New World/source IDs come only from normal product controls. Existing C1/C2 and campaign-import semantics remain unchanged.
- Exact browser/PR witness uses the pinned Of Conks Markdown at `/home/drakosfire/Downloads/of-conks-cons-v21-gold/specimens/01-cleaned-single-column.md`, expected UTF-8 byte length 48,778 and SHA-256 `7a379fc9025635b1862b6af7eb5a43dd1ee9387b51cf63ba505491fffe7e68f1`, imported via ordinary Build controls (no direct DB/API call). This is the human-normalized parsed Markdown input; it does not prove production PDF parsing. If the pin differs, stop and re-anchor rather than silently substituting.
- Record exact one-set runtime state and isolated DB identity, with no process/server/DB switch performed by the implementation lane.
- Focused cohorts, Ruff, frontend build/typecheck, `git diff --check`, and changed-path/lease audit must be reported honestly. No model cost is expected or claimed.
