---
# Instantiated from the operator-provided HANDOFF.template.md on 2026-08-11.
# Optional transport pointer for a future GitHub PR body.
# The checked-in handoff, cumulative diff, nano commits, review handback, and
# independently rerun verification are authoritative. A narrative PR body is not.
pr_body_template: |
  ## Handoff pointer
  - Conversation: CON-READY
  - Flow / agent: BUILD
  - Direction: DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-CON-READY-build-lossless-markdown-import.md
  - Branch: agent/con-ready-lossless-markdown-import

  ## Verification pointer
  - Base: b466ce8dfebaf88366eee79bad795299103a5b58
  - Verification: see §7 and the latest numbered review handback

  The checked-in handoff, cumulative code diff, nano commits, review handback,
  and independently rerun verification are the review contract. The PR
  description is transport metadata only.
---

# HANDOFF — CON-READY: Lossless Pasted Markdown Ingress for an Existing World

**Created:** 2026-08-11.  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-CON-READY-build-lossless-markdown-import.md` on the implementation branch; merging this handoff to `main` is **not** a dispatch or merge prerequisite.  
**Conversation name:** `CON-READY`  
**Flow / agent:** `BUILD`  
**Handoff direction:** `DESIGN → CODE`  
**Design agent:** CON-READY steward  
**Code agent:** BUILD  
**PR title:** `BUILD: import pasted Markdown as a lossless world source`  
**Implementation branch:** `agent/con-ready-lossless-markdown-import`  
**Base:** `main` at `b466ce8dfebaf88366eee79bad795299103a5b58` — merged CON-READY roadmap + Steward's Anchor  
**Roadmap slice:** `CR01A` — first independently useful slice split from `CR01 — Source Ingress & Reading`  
**Primary user story:** `CR-U1 — Bring external material into DungeonBuddy`  
**Partial prerequisite for:** `CR-U2 — Read the original source as a real document`

> **Dispatch rule:** This handoff is authoritative once checked into the implementation branch. It does not need a separate documentation PR or a merge to `main` before BUILD begins.
>
> **Review rule:** Every formal review increments the review-cycle number exactly once. The first formal review is `Review Cycle 1`; the next is `Review Cycle 2`, regardless of whether the verdict is PASS or CHANGES REQUESTED. Fix commits and discussion replies do not increment the count until another formal review is performed.
>
> **PR-body rule:** The PR description is optional transport metadata. It is never a merge gate and is never accepted as substitute evidence for the handoff, cumulative diff, nano-commit story, review handback, or verification.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Capability** | A coherent behavior or contract that creates one outcome someone can use, depend on, test, or revert. |
| **Independently useful outcome** | An outcome that provides value or establishes a reusable contract even if neighboring work never ships. |
| **Public/durable contract** | A persisted format, identifier, API, event, schema, file representation, caller-facing type, or externally consumed interface that must remain interpretable beyond one call stack. |
| **Observable path** | A user-visible or externally observable route through behavior, including success, error, retry, persistence, and operator paths. |
| **Owning boundary** | The layer where a guarantee becomes true and therefore must be proved. |
| **Invariant** | The single property every changed layer and observable path establishes or proves. |
| **Evidence ledger** | Mapping from each invariant clause to its owning boundary, required proof, produced result, provenance, and merge-blocking stop condition. |
| **Source import** | The one-time operation that initializes an empty `worldbuilding_source` with externally supplied Markdown bytes. It is not ordinary rich-editor authoring and is not graph publication. |
| **World-scoped source** | A workspace source whose durable identity records an exact `world_id` and whose server-derived target lives under that world's existing source hierarchy. |
| **Stop condition** | A discovered fact that invalidates this slice boundary or required proof and must be reported before implementation continues. |

## Agent flow and nano-commit contract

Use flow `BUILD`. The implementation should remain a nano-commit story. A reasonable decomposition is:

1. world-scoped workspace-document identity/storage contract;
2. one-time lossless source-import write contract;
3. Build import interaction + retry/activation behavior;
4. exact persistence/fidelity/adversarial proofs;
5. review-cycle fixes as discrete commits.

This is guidance, not a requirement to manufacture commits when one code change naturally proves one invariant clause. Do not mix extraction, Hermes, statblock, combat, generalized world creation, or visual source-reader work into this branch.

## Review and doc-sync contract

The reviewer identifies the exact branch/PR/head SHA and reviews the cumulative diff plus nano commits against this handoff. Each formal review produces exactly one numbered verdict:

```text
Review Cycle N — PASS
```

or

```text
Review Cycle N — CHANGES REQUESTED
```

### Review-cycle numbering

- First formal review: **Review Cycle 1**.
- Every subsequent formal review increments exactly once: 2, 3, 4, ...
- PASS and CHANGES REQUESTED both count as a review cycle.
- Author fix commits, comment replies, CI reruns, or partial spot-checks do **not** increment the cycle until the reviewer performs another formal review.
- Re-review starts from the prior finding ledger and verifies the cumulative invariant, not only the literal changed lines.

Do not require a polished PR description. Do not require this handoff, tracker status, roadmap status, or checklist synchronization to land on `main` before implementation or merge. A document sync may follow separately. The only documentation change owned by this implementation PR is a contract document that changes because the implementation changes the durable workspace-document contract (§4).

---

# §1 Mission and merge-ready invariant

> **As a GM working in an existing admitted world, I can paste non-empty external Markdown into Build as a new worldbuilding source so that DungeonBuddy stores the exact source durably under that world, opens the exact source I created, and can hard-reopen it without source loss or duplicate identity.**

This is the first concrete implementation of `CR-U1` from `Docs/Roadmaps/ROADMAP-con-ready.md`.

## Merge-ready invariant

> **One pasted-source import produces one stable workspace `documentId` with explicit world tenancy and a server-derived world-scoped target; the initial Markdown is committed byte-for-byte through a one-time CAS-bound `source_import` mode before truthful activation, ordinary authoring semantics remain unchanged, unsupported rich-editor constructs are preserved rather than rewritten, and every failure/retry path either reuses that exact identity or fails closed without overwriting source.**

The invariant deliberately contains several layers because they all establish one user-visible outcome: *the imported source is the exact source I brought in, in the world I chose, and it stays that source.*

## What this slice proves

The normal path is:

```text
Build
  → New / Import source
  → choose one currently admitted campaign scope
  → title
  → paste Markdown
  → server derives world from admitted Build scope on the client
  → create one world-scoped worldbuilding_source
  → one-time lossless source_import commit
  → exact snapshot reload
  → activate exact documentId
  → hard reload
  → same title + same documentId + exact Markdown bytes
```

The pasted Markdown may contain constructs the current TipTap authoring writer cannot round-trip safely, including at least tables, image syntax, thematic/frontmatter separators, and HTML-ish blocks. Initial import must still preserve those bytes. The existing fidelity guard must continue to prevent a later lossy rich-editor Save from overwriting them.

## Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Every path is about creating or initializing one exact world-scoped source without changing its identity or source bytes. |
| What adversarial sequence is most likely to falsify it? | `create record → source_import write succeeds or partially fails → activation/load fails or user retries → second create/write accidentally occurs`, or `import unsafe Markdown → TipTap projection loads → ordinary Save silently rewrites source`. |
| Would §7 evidence detect that failure? | **Yes.** Server tests cover one-time import/CAS/path identity; controller tests inject create/import/load failures; fidelity tests prove imported unsafe Markdown remains authoritative and Save-blocked; manual hard-reopen proves the complete path. |
| Which owning boundary is easiest to under-test? | The boundary between committed raw Markdown and the post-import Canvas session: the UI can look correct while a later Save is lossy. The fidelity regression proof is merge-blocking. |
| What fact would force this slice to stop or split? | If world-scoped source placement under the existing world source hierarchy causes automatic legacy corpus publication/admission, or if lossless initialization cannot reuse the existing workspace/Tiptap write authority without creating a second competing writer. |

---

# §2 Context, authority, and boundaries

## Authority matrix

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` and `Docs/Roadmaps/ROADMAP-con-ready.md` on `main` at `b466ce8d`; specifically CR-U1 and CR01. |
| Template basis | Operator-provided `HANDOFF.template.md`; this file instantiates its mission/invariant/matrix/evidence structure and adds the CON-READY review-cycle rules above. |
| Repository process | `Docs/Plans/JUMPSTART-docs-relevance-first.md` for one-capability dispatch/review; operator overrides in this handoff: handoff-on-main is not a gate, PR description is not a gate, every formal review is numbered. |
| Base revision | `b466ce8dfebaf88366eee79bad795299103a5b58` |
| Predecessor contract | PR #560 (`85a2bbf…`) established intentional Build document identity/selection/rename and Canvas revision authority; PR #561 (`b466ce8d…`) canonized CON-READY. |
| Exact input consumed | User-entered title, one current Build-admitted campaign, and a non-empty Markdown string pasted into Build. |
| Named successor | `CR01B — Rich Source Reader + .md/file/assets ingress`: styled source reading, image asset preservation/rendering, `.md` file upload/bundle import. |
| Additional successor | Generic **new-world bootstrap/placement**: create a new world/source hierarchy and then use the same ingress contract. This PR accepts existing admitted worlds only. |
| What remains false | No new-world creation; no file picker/assets; no guarantee that all imported constructs are beautifully rendered/edited; no extraction; no source navigation from graph nodes; no Hermes source follow-through. |
| Explicit non-goals | PDF extraction/RulesIngestion wiring, graph extraction/promotion, Hermes changes, NPC/Threat/Shop projections, statblock mechanics import, Play/Combat, arbitrary filesystem browsing, corpus indexing changes, archive/delete UX, broad workspace-document migration. |

## Current repository facts that constrain implementation

1. `WorkspaceDocumentRecord` currently has `campaign_id` but no exact `world_id`, and current `worldbuilding_source` targets are `out/workspace/worldbuilding/<documentId>.md`.
2. Build already resolves an admitted campaign to a world through `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts`; `longmont-c1` / `longmont-c2` currently resolve to `eldyrwild`.
3. The existing world source hierarchy is rooted at `corpus/<worldId>-markdown`; current Eldyrwild source lives at `corpus/eldyrwild-markdown`.
4. `tiptap_markdown_write.py` intentionally blocks potentially lossy Markdown in ordinary `worldbuilding_source` authoring. Constructs beginning with `|`, `<`, `![`, and `---` are part of that guard today.
5. `useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx` already proves that unsupported loaded Markdown remains authoritative and ordinary Save is blocked rather than overwriting it.
6. `GraphMemorySourceArtifact` already supports `world_id`, `workspace_document_id`, exact workspace revision, URI, and content digest. `source_artifact_registry.py` currently uses campaign identity where an exact world identity should be used for worldbuilding packaging; new world-scoped records must not perpetuate that mismatch.

## World-scoped source representation frozen for this slice

For **new** worldbuilding sources with explicit `world_id`, the server derives:

```text
corpus/<worldId>-markdown/_dungeonbuddy/sources/<documentId>/source.md
```

Example:

```text
world_id       = eldyrwild
document_id    = 9f6d... (opaque exact identity)
target_relpath = corpus/eldyrwild-markdown/_dungeonbuddy/sources/9f6d.../source.md
```

Rules:

- `worldId` and `documentId` are identity; title is not path identity.
- The client never supplies `target_relpath` for a world-scoped source.
- The server sanitizes/validates `world_id` and derives the path.
- The existing parent root `corpus/<worldId>-markdown` must already exist. The server may create only the managed `_dungeonbuddy/sources/<documentId>/` descendants.
- This PR does **not** create `corpus/<newWorld>-markdown`; missing world root is a truthful failure and the new-world bootstrap successor.
- Rename changes title only and never moves the source directory.
- Existing legacy workspace documents whose `world_id` is absent and target remains `out/workspace/worldbuilding/...` continue to load/save under their existing contract. No migration in this PR.
- Merely existing under the world source hierarchy does **not** mean graph publication, extraction acceptance, or canon promotion.

### Storage stop condition

Before implementation commits to this target, audit whether adding `_dungeonbuddy/sources/.../*.md` under `corpus/<worldId>-markdown` is automatically swept into any legacy manifest/index/publication path in a way that would make an imported **draft source** implicitly canonical or broadly queryable.

Managed `_dungeonbuddy` paths **must** be excluded from legacy whole-tree corpus/index/publication authority: planner manifest/ref index, corpus fingerprint, batch ingest collectors, and Hermes lexical fallback. Residual eval/script walkers outside product authority are acknowledged residual risk for a later sweep — not a merge blocker for CR01A once the product paths in §4 exclude managed storage.

If yes (after §4 exclusions land), **STOP**. Report the exact scanner/index and propose the narrowest world-level managed source root that preserves the user's world hierarchy without changing authority. Do not silently choose another location.

## Authoritative inputs to read before changing code

1. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
2. `Docs/Roadmaps/ROADMAP-con-ready.md`
3. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`
4. `apps/live_control_server/services/workspace_document_registry.py`
5. `apps/live_control_server/services/tiptap_markdown_write.py`
6. `apps/live_control_server/services/source_artifact_registry.py`
7. `apps/live_control_server/routes/workspace_documents.py`
8. `apps/live_control_server/routes/live.py` Tiptap prepare/commit routes
9. `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts`
10. `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts`
11. `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts`
12. `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.tsx`
13. `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts`
14. owning tests named in §4/§7.

If `main` has moved after `b466ce8d`, first reconcile this handoff against the new base. Do not implement from stale field shapes.

---

# §3 Observable-path and adversarial-sequence inventory

## Observable paths

| Path | Current behavior | Required behavior | Same invariant? | Owning boundary |
|---|---|---|---:|---|
| Open Build / inspect source controls | New Source creates a blank campaign-scoped `worldbuilding_source`; no pasted-source ingress. | Existing New Source remains available; import affordance is explicit and does not mutate until submit. | Yes | Build component/controller |
| Create new blank worldbuilding source | New record uses campaign identity and global `out/workspace/worldbuilding/...`. | New Build-created worldbuilding records carry exact derived `world_id` and server-derived world-scoped target. Blank creation still works. | Yes | workspace registry + Build controller |
| Import ordinary Markdown | No one-step source import; normal editor authoring only. | Create/select one empty source, commit exact Markdown once in `source_import` mode, reload exact snapshot, activate exact ID. | Yes | Build controller + write service |
| Import Markdown with table / image syntax / `---` / HTML-ish block | Ordinary TipTap writer reports lossy diagnostics and blocks save. | Initial `source_import` preserves the exact raw Markdown; diagnostics may be returned but do not transform or block initial import. | Yes | write service |
| Later rich-editor Save of unsupported imported source | Fidelity guard blocks unsafe save today. | Remains blocked; imported source bytes stay authoritative. | Yes | workspace authoring fidelity boundary |
| Duplicate submit while create/import pending | Could create duplicate if new orchestration is naive. | At most one create/import lifecycle is in flight; no second document identity. | Yes | Build component/controller |
| Import write fails after record creation | Not currently applicable. | Preserve created exact empty record; preserve pasted draft in current UI; retry imports into the same document, not another POST. | Yes | Build controller |
| Browser reload after failed import | Not currently applicable. | The empty created source remains visible/selectable. User may paste/import into that exact empty source; no hidden orphan cleanup required. | Yes | registry + Build recovery UI |
| Import commit succeeds but snapshot load/activation fails | Current create lifecycle already has retained-created-record semantics for activation failures. | Retry load/activation of the exact committed source; never create or source-import again. | Yes | controller lifecycle |
| Stale expected revision | Normal writer CAS fails closed. | `source_import` also fails closed; no overwrite and no fallback to latest. | Yes | write service |
| Second source-import into a non-empty/ready source | No source-import mode today. | Reject. Source import is initialization, not an alternate editor. | Yes | write service |
| Hard reopen | Existing snapshot reads exact target. | Same exact `documentId`, world, title, target and raw Markdown survive process/browser reload. | Yes | registry/snapshot + Build load |
| Existing legacy worldbuilding document | Global old target contract. | Remains readable/writable without forced migration or fabricated `world_id`. | Yes | registry/write compatibility |
| Package source artifact later | Worldbuilding source artifact currently has incomplete world identity behavior. | New world-scoped source packages exact `world_id`; legacy source remains explicitly compatible without rewriting identity. | Yes | source artifact registry |
| Missing world source root | No world-level source create today. | Reject before target mutation; do not create a new world root. | Yes | registry/storage service |

## Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| double-click Import → overlapping async handlers | exactly one workspace create and one source initialization lifecycle | UI/controller adversarial test |
| create record succeeds → prepare source import returns 500 | created record retained; pasted text retained; retry targets same `documentId`; no duplicate create | controller failure-injection test |
| prepare succeeds → commit network failure / token invalidation | record retained; retry re-prepares against exact current revision; no new source identity | controller + route/service tests |
| source import commit succeeds → snapshot reload fails | durable source remains committed; retry only reloads/activates exact record | controller failure-injection test |
| imported unsafe Markdown → Canvas projects it → user presses Save | Save remains blocked by fidelity guard; disk bytes unchanged | markdown fidelity test + exact file assertion |
| source import request at revision N → metadata rename advances to N+1 before commit | stale import commit rejected; no overwrite; caller must reload/reprepare | CAS service test |
| source import exact body succeeds → caller repeats same import request | second initialization rejected even if body text is identical | service replay test |
| create with `world_id=eldyrwild` plus client-supplied foreign `target_relpath` | reject; client cannot steer storage | registry/route contract test |
| create with unsafe `world_id=../../tmp` | reject before filesystem mutation | registry path-safety test |
| create for absent `corpus/<worldId>-markdown` | truthful failure; no invented world root and no registry record claiming success | registry test |
| reopen legacy `out/workspace/worldbuilding/...` source | legacy record remains usable without migration | registry/write compatibility test |

---

# §4 Files in scope (allowlist)

Every implementation change must be in this table or the bounded test-discovery exception. If another production path is required, stop and report it before changing it.

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/services/workspace_document_registry.py` | Persist optional/exact `world_id` for new worldbuilding sources; derive and validate world-scoped target; preserve legacy records. |
| Modify | `apps/live_control_server/routes/workspace_documents.py` | Thread `world_id` through the existing create contract; preserve server ownership of target path. |
| Modify | `apps/live_control_server/services/tiptap_markdown_write.py` | Add one-time CAS-bound `source_import` mode that preserves exact Markdown while leaving ordinary authoring fidelity policy unchanged. |
| Modify if model threading requires it | `apps/live_control_server/routes/live.py` | Expose the existing Tiptap prepare/commit request models with `write_mode`; no new broad route surface. |
| Modify | `apps/live_control_server/services/source_artifact_registry.py` | Package exact world identity for new world-scoped source records; preserve explicit legacy compatibility. |
| Modify | `apps/live-control-ui/src/api/types.ts` | Add `world_id` to workspace document/create types and `write_mode` to Tiptap write request types. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Carry the exact new request fields through existing APIs only. |
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentCreation.ts` | Carry world identity through existing create lifecycle without weakening duplicate/activation recovery semantics. |
| Modify | `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.ts` | Derive world from admitted Build scope; orchestrate create → source_import → exact reload/activation; expose retry against retained empty source. |
| Modify | `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.tsx` | Add pasted Markdown import affordance while preserving ordinary blank New Source creation. |
| Modify if prop plumbing requires it | `apps/live-control-ui/src/buildSurface/BuildSurfaceContext.tsx` | Wire import/retry interaction into existing DOCUMENT context; do not create duplicate document chrome. |
| Modify if controller plumbing requires it | `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx` | Pass the existing controller/session authority into the import affordance. |
| Modify | `Docs/Design/CONTRACT-workspace-document-identity-v1.md` | Record the new durable `world_id`, world-scoped target representation, legacy compatibility, and rename/path identity rule. This is implementation contract sync, not PR narrative. |
| Modify | `tests/test_workspace_document_registry.py` | World identity/path derivation, safety, missing-root and legacy compatibility proofs. |
| Modify | `tests/test_tiptap_markdown_write.py` | One-time exact source-import, unsafe Markdown acceptance, authoring-policy regression, replay, CAS proofs. |
| Modify | `tests/test_live_tiptap_markdown_write.py` | Route-level prepare/commit mode and failure contract. |
| Modify | `tests/test_source_artifact.py` | Exact world identity packaging for new records + legacy compatibility. |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | Wire-level request/response regression where needed. |
| Modify | `apps/live-control-ui/src/buildSurface/useBuildWorkspaceDocumentController.test.ts` | Full create/import/retry/no-duplicate/load/activation orchestration. |
| Create | `apps/live-control-ui/src/buildSurface/BuildDocumentCreateControl.test.tsx` | User-facing import validation, double-submit, retained pasted draft and retry affordance. |
| Modify | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx` | Prove unsupported imported Markdown remains authoritative and later lossy Save is blocked. |
| Modify | `tools/batch_ingest_corpus.py` | Exclude `_dungeonbuddy` from legacy whole-tree ingest collection. |
| Modify | `tools/corpus_batch.py` | Same exclusion for batch path collection. |
| Modify | `src/agent/planner.py` | Exclude `_dungeonbuddy` from corpus manifest/ref index. |
| Modify | `src/agent/planner_cache.py` | Exclude `_dungeonbuddy` from corpus fingerprint. |
| Modify | `integrations/hermes/plugins/dungeonbuddy/__init__.py` | Ignore `_dungeonbuddy` in lexical markdown enumeration. |
| Create/Modify | `tests/test_batch_ingest_managed_source_exclusion.py` | Ingest exclusion proof. |
| Modify | `tests/test_planner.py` | Manifest/ref/fingerprint exclusion proofs. |
| Modify | `tests/test_hermes_dungeonbuddy_plugin.py` | Lexical ignore proof. |

### Bounded discovery exception — adjacent owning tests only

```text
Directory:
  apps/live-control-ui/src/workspaceDocument/
  apps/live-control-ui/src/buildSurface/
  tests/

Maximum additional changed paths: 3
Allowed path kinds: existing or newly created focused test files only
Decision rule: include only when a production path already named above has an
existing owning test whose actual filename was not captured in this handoff, or
when one focused new test file is necessary to prove a §7 guarantee without
mixing product behavior.
```

No production-code path is allowed under this exception.

---

# §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `Drakosfire/RulesIngestion` | PDF extraction exists upstream; integration is not CON-READY CR01A. Markdown is the boundary. |
| `src/graph_memory/extraction/**` | Extraction is CR02. Source ingress must work without graph extraction. |
| Hermes agent/tool files | Source follow-through is CR03. Do not grant filesystem/Markdown browsing here. |
| Threat/statblock workbench | Mechanics import is CR04. |
| Combat/Play modules | Parallel CR06 dependency, separate invariant. |
| New world initialization / graph bootstrap | Existing-world-only slice. New-world creation is named successor. |
| `.md` file picker / drag-drop | Same eventual normalization boundary but separately useful UI/input adapter; CR01B. |
| Image/asset upload, copy, hashing, bundle manifests | CR01B; Markdown image syntax must be preserved now, asset lifecycle comes later. |
| Full rich source reader / TTRPG styling | CR01B. Existing Canvas may project the source, but beautiful faithful reading is not claimed. |
| Automatic corpus index/manifest update | Presence of source bytes is not graph/corpus publication. Any required automatic publication is a stop condition. |
| Archive/delete/cleanup management | Not necessary to prove safe import. Do not build source management because partial failure can retain an exact empty record and retry. |
| Legacy record migration | Existing `out/workspace/worldbuilding/...` records remain compatible; no bulk move/rewrite. |
| Generic world registry | Do not invent it. This slice uses current admitted Build world mapping and an already-existing world source root. |
| Roadmap/tracker status sync | May happen separately after review/merge; not a code merge gate. |
| Narrative PR-body maintenance | Explicitly not evidence or merge gate. |

---

# §6 Implementation contract and conditional matrices

## Public behavior contract

```text
Input:
  title: non-empty source title
  campaign_id: one currently Build-admitted campaign
  world_id: exact world derived from that admitted campaign by existing Build context
  markdown: non-empty UTF-8 Markdown string

Output:
  one WorkspaceDocumentRecord / snapshot where:
    kind = worldbuilding_source
    document_id = exact opaque stable ID
    world_id = exact admitted world
    campaign_id = selected admitted campaign
    target_relpath = server-derived world source target
    content_status = ready after successful source import
    exported_markdown = exact imported source bytes/text under current snapshot contract

Invariant:
  same as §1.

Failure behavior:
  unknown/unmapped Build scope → block before create
  missing world source root → reject; do not bootstrap a world
  create succeeds / import fails → retain exact empty record; retry same ID
  stale revision → reject; no overwrite
  unsupported rich-editor Markdown → permit initial source import; preserve source;
    later ordinary lossy Save remains blocked
  second source_import after initialization → reject

Replay / idempotency:
  same UI submit while pending → no second create
  retry after pre-commit failure → same documentId, fresh prepare if needed
  retry after commit but activation failure → reload/activate only, no second write
  second source_import on ready document → reject, even if Markdown identical

Trust boundary:
  Verifies:
    safe exact world identifier/path containment
    existing world source root
    exact workspace document identity/kind/status/revision
    source is empty before source_import
    token/request mode and body digest
    exact CAS before commit

  Records/trusts without proving:
    the semantic truth of the imported prose
    whether campaign logically belongs to world beyond current admitted Build mapping
    whether image references have corresponding assets (CR01B)
```

## Chosen write-mode contract

Extend the existing Tiptap Markdown prepare/commit request contract with:

```text
write_mode: "authoring" | "source_import"
```

Compatibility:

```text
absent write_mode == "authoring"
```

The prepare token must bind at minimum:

```text
document_id
expected/current revision
markdown digest / exact prepared body identity
write_mode
resolved target identity
```

`source_import` semantics:

- only `worldbuilding_source`;
- only active, empty/uninitialized source;
- exact target is server-resolved from registry;
- lossy diagnostics may be reported for information but do not block initial raw import;
- commit writes the exact supplied Markdown, not a TipTap-normalized derivative;
- successful commit advances the existing workspace revision/content metadata through the same authority as ordinary authoring;
- after successful import, `source_import` is permanently unavailable for that non-empty source;
- it is **not** a second editing API.

If the existing prepare/commit service cannot safely express this distinction without weakening ordinary authoring, trigger the write-authority stop condition. A dedicated narrow endpoint is not pre-authorized if it becomes a competing writer.

## Commit model

```text
Commit point:
  successful CAS-bound source_import commit that atomically replaces the empty
  target with the exact Markdown and advances workspace document content state/revision.

Before commit:
  created workspace record may exist with content_status=empty; no imported source
  may be claimed as durable.

After commit:
  source bytes and registry snapshot are durable truth. Failure to reload or activate
  is a presentation/navigation failure; retry must not repeat import or create.

Truthful result after post-commit failure:
  "Source imported; could not open it yet" (or equivalent truthful state), retaining
  exact document identity for reload/activation retry.
```

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Build world resolution | derive from admitted campaign | exact `world_id` | unmapped campaign: block | graph projection may be loading: defer create/import | contradictory/invalid scope: block | scope changes before submit: recompute/require current | user may resubmit after valid scope |
| Workspace create | one lifecycle in flight | exact world-scoped empty record | n/a | request failure: no success claim | unsafe world/target/root: reject | n/a | duplicate click coalesced/disabled; retry only if no record returned |
| Source prepare | created empty exact record | token bound to exact mode/body/revision | non-empty source: reject | server unavailable: retain record + draft | kind/target/mode mismatch: fail closed | revision mismatch: fail closed | reprepare same record after reload |
| Source commit | pending token | exact body durable; revision advances | n/a | ambiguous network outcome: reload exact snapshot before deciding next action | token/digest/target mismatch: fail closed | stale revision: fail closed | never blindly recommit after ambiguous success; resolve snapshot first |
| Snapshot reload/activate | after durable commit | exact source active | record missing: error | load failure: truthful retained state | content digest mismatch: block activation as successful import | newer revision: load exact current record, do not overwrite | retry reload/activation only |
| Later authoring | normal Canvas behavior | safe supported edits save normally | n/a | normal authoring error | lossy imported projection: Save blocked | existing CAS semantics | reload/discard per existing Canvas rules |
| Legacy source | existing old representation | unchanged behavior | n/a | existing semantics | existing semantics | existing semantics | existing semantics |

No fallback to guessed `world_id`, guessed target path, display title, latest revision, or second document identity is permitted.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Workspace document exact ID | `documentId` is immutable work-object identity | missing/unknown is an error | No |
| World identity | new Build worldbuilding sources persist exact `world_id` derived from admitted scope | unmapped/unsafe world blocks creation | No guessed world |
| Campaign identity | persists selected current admitted `campaign_id`; campaign is affinity/scope, not world substitute | unknown campaign blocks Build creation | No |
| Target path | server derives from `world_id + documentId`; client cannot choose it | foreign/client path rejected for new world-scoped source | No |
| Title | mutable display label only | duplicate titles allowed if current contract allows; never resolves identity | No identity fallback |
| Rename | same documentId/world/path, title changes only | CAS conflicts use existing rename behavior | No path move |
| Legacy source without world_id | retain exact existing record/target; do not fabricate world in storage migration | legacy state is explicit | Compatibility only, not inference |
| SourceArtifact packaging | new record uses exact record.world_id | legacy record follows explicit compatibility behavior named/tested in code | No campaign-as-world for new records |

### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate / replay behavior | Compatibility / migration | Rollback / reversion |
|---|---|---|---|---|---|
| Create new worldbuilding source | registry record with exact `document_id`, `world_id`, `campaign_id`, server target, revision/status | list/get/snapshot return same exact identity | duplicate pending UI submit does not create second record | legacy records remain valid; no migration | existing discard lifecycle remains out of normal path |
| Initial source import | UTF-8 Markdown at world-scoped `source.md` + advanced registry content revision | snapshot/export returns exact imported Markdown | one-time only; repeat rejected | authoring requests with absent mode remain `authoring` | no automatic rollback after committed source; later editing uses normal authoring |
| Hard reopen | registry + target file | exact title/document/world/target/source reloaded | idempotent read | both new and legacy path shapes load | n/a |
| Rename | metadata revision only | target path/body unchanged | existing metadata CAS | works for new and legacy records | normal subsequent rename |
| Package source artifact | existing SourceArtifact schema | exact workspace id/revision/digest/world for new source | existing artifact identity rules | explicit legacy behavior | immutable artifact contract unchanged |

### D. Predecessor-to-consumer mapping

**Grounding sources:** current Pydantic/TypeScript contracts at base `b466ce8d` plus exact existing Build creation/fidelity tests.

| Predecessor field/outcome | Real current shape | Required consumer behavior | Transformation | Owning proof |
|---|---|---|---|---|
| `WorkspaceDocumentRecord.document_id` | string UUID-shaped opaque ID | stable imported-source identity | unchanged | registry + controller tests |
| `campaign_id` | string, required for current Build worldbuilding source | selected admitted campaign remains recorded | unchanged | create/controller tests |
| `world_id` | absent from WorkspaceDocumentRecord today | new optional persisted field; required by normal new Build worldbuilding creation/import | derive client-side from admitted world/campaign mapping; validate server-side as safe existing world root | registry/controller tests |
| `target_relpath` | current worldbuilding default `out/workspace/worldbuilding/<id>.md` | new world-scoped records use server-derived managed source path | worldId + documentId → fixed path; legacy unchanged | registry tests |
| `content_status` | `empty|ready|missing` under existing registry | source_import allowed only from empty/uninitialized; success becomes ready | existing commit metadata update | write tests |
| Tiptap write request | document ID + Markdown + expected revision/token; no mode | add optional `write_mode`, default authoring | explicit enum; token binds it | service/route/liveApi tests |
| lossy diagnostics | blocking for worldbuilding authoring today | remain blocking for authoring; informational/non-blocking for one-time source_import | policy branch by write mode, no transform | write + fidelity tests |
| Build create lifecycle | create → load/activate with retained-record recovery | import extends lifecycle with create → source_import → reload → activate; failure reuses exact created record | state machine extension, no second registry | controller tests |
| SourceArtifact `world_id` | schema supports world_id; workspace packaging currently does not have exact world field | new source artifact gets record.world_id | explicit new-record mapping; legacy compatibility separately named | source artifact test |

---

# §7 Evidence required to merge

Every guarantee is merge-blocking unless explicitly waived by the operator. The PR description cannot satisfy any evidence row.

## Evidence ledger

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| New source persists exact world identity and safe server-derived path | registry service | contract/adversarial | `uv run pytest tests/test_workspace_document_registry.py` | exact path/world round trip; unsafe world/foreign target/missing root rejected; legacy unchanged | any client-controlled path escape or fabricated world |
| `source_import` preserves exact Markdown that authoring would reject | Tiptap write service | exact round-trip | `uv run pytest tests/test_tiptap_markdown_write.py` | table/image/`---`/HTML-ish sample writes byte-for-byte in import mode; same body blocked in normal authoring when lossy | import normalizes or authoring guard weakens |
| One-time mode is CAS/token bound and not replayable | write service | adversarial | same focused pytest | stale revision/token/mode/body mismatch fails closed; second import rejected | replay can overwrite ready source |
| HTTP contract carries mode without widening arbitrary writes | live route | contract | `uv run pytest tests/test_live_tiptap_markdown_write.py` | prepare/commit exact mode behavior; omitted mode remains authoring | old callers change semantics |
| SourceArtifact preserves exact world for new source | source artifact registry/schema | contract | `uv run pytest tests/test_source_artifact.py` | artifact has new record's world_id + exact workspace revision/digest; legacy compatibility explicit | campaign silently substitutes for world on new source |
| Build import creates once and recovers on partial failures | Build controller | adversarial state-machine | `cd apps/live-control-ui && pnpm exec vitest run src/buildSurface/useBuildWorkspaceDocumentController.test.ts` | one create; pending-lifecycle recovery only (no active-draft reuse); create/prepare/commit/load failure paths retain/reuse exact identity; ambiguous commit requires exact Markdown; pending scope mismatch fails closed | retry creates duplicate, imports into active Canvas draft, or blindly recommits |
| Import UI accepts title/scope/non-empty Markdown and prevents duplicate submit | Build component | component/adversarial | `cd apps/live-control-ui && pnpm exec vitest run src/buildSurface/BuildDocumentCreateControl.test.tsx` | empty validation; double submit blocked; failed import keeps Markdown; retained empty source can be retried | paste lost on ordinary recoverable failure or duplicate create |
| Imported unsupported source cannot be destroyed by later rich-editor Save | Canvas authoring fidelity | regression | `cd apps/live-control-ui && pnpm exec vitest run src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx` | exported Markdown remains authoritative and Save is blocked; disk/snapshot source unchanged | lossy Save is enabled or source bytes change |
| Wire types remain compatible | UI API | regression | `cd apps/live-control-ui && pnpm exec vitest run src/api/liveApi.test.ts` | exact fields sent; omitted write mode retains authoring | unrelated API breakage |
| Managed `_dungeonbuddy` storage is excluded from legacy whole-tree ingest | batch ingest collectors | contract | `uv run pytest tests/test_batch_ingest_managed_source_exclusion.py` | `_dungeonbuddy/sources/.../source.md` absent from collected paths; explicit `--paths-file` managed entries warn and skip | managed draft swept into legacy ingest |
| Managed `_dungeonbuddy` storage is excluded from planner corpus authority | planner manifest/ref index + fingerprint | contract | `uv run pytest tests/test_planner.py -k dungeonbuddy` | managed path absent from `build_corpus_manifest` / `build_corpus_path_ref_index`; `corpus_fingerprint` unchanged when managed Markdown is added/edited and changes when ordinary corpus Markdown changes | draft source becomes planner-queryable or invalidates planner cache |
| Managed `_dungeonbuddy` storage is ignored by Hermes lexical fallback | Hermes plugin | contract | `uv run pytest tests/test_hermes_dungeonbuddy_plugin.py -k dungeonbuddy` | lexical matches exclude managed storage while ordinary corpus notes still match | draft source appears in lexical search |
| Type/build integration | UI package | compile/build | `cd apps/live-control-ui && pnpm exec tsc -b && pnpm build` | success | new type/runtime build failure |
| No hidden path expansion | git diff | scope | `git diff --name-only b466ce8dfebaf88366eee79bad795299103a5b58...HEAD` | only §4 + bounded test exception | production path outside allowlist |
| Diff hygiene | git | hygiene | `git diff --check` | no whitespace errors | failure |

## Required backend focused run

Run as one command after focused iteration:

```bash
uv run pytest \
  tests/test_workspace_document_registry.py \
  tests/test_tiptap_markdown_write.py \
  tests/test_live_tiptap_markdown_write.py \
  tests/test_source_artifact.py \
  tests/test_batch_ingest_managed_source_exclusion.py \
  tests/test_planner.py \
  tests/test_hermes_dungeonbuddy_plugin.py
```

## Required frontend focused run

```bash
cd apps/live-control-ui
pnpm exec vitest run \
  src/buildSurface/useBuildWorkspaceDocumentController.test.ts \
  src/buildSurface/BuildDocumentCreateControl.test.tsx \
  src/workspaceDocument/useWorkspaceDocumentAuthoring.markdownFidelity.test.tsx \
  src/api/liveApi.test.ts
pnpm exec tsc -b
pnpm build
```

If the bounded discovery exception resolves an actual owning test to a different filename, record the exact replacement in the review evidence ledger.

## Minimal live / dogfood proof

**Existing surface used:** Build.

**Smallest realistic scenario:** In an existing Eldyrwild/Longmont Build scope, import this source using the product UI:

```markdown
# Hesta's Apothecary

![Hesta behind the counter](assets/hesta.webp)

Hesta keeps a crowded little apothecary near the fen road.

| Item | Price |
|---|---:|
| Healing draught | 25 gp |
| Fen-sleep brew | 8 gp |

---

> Hesta keeps the stronger stock hidden from casual customers.

<section data-source-note="preserve-me">
This block is intentionally awkward Markdown/HTML source material.
</section>
```

**Expected observation:**

1. one source/document is created;
2. title is `Hesta's Apothecary`;
3. record has exact `world_id=eldyrwild` and selected Longmont campaign;
4. target is under the managed Eldyrwild source folder, keyed by exact document ID;
5. source opens in Build after import;
6. hard browser reload returns the same exact document;
7. raw/source export equals the pasted Markdown exactly;
8. if TipTap cannot round-trip all constructs, the UI truthfully seals ordinary Save instead of overwriting the source;
9. no graph extraction/promotion occurs simply because the file exists.

**Evidence captured:** exact document ID, registry/snapshot fields, target path, source SHA/body equality before and after hard reload, screenshot or concise manual note showing the reopened Build document, and confirmation that no second source was created.

If this proof requires building a new rich source reader, an asset uploader, a corpus browser, archive manager, or extraction UI, **STOP**. Those are successor capabilities.

## Baseline failure protocol

For any required command failing on base:

- run/cite the same command on `b466ce8d` and HEAD;
- state whether HEAD adds, removes, or preserves failures;
- do not call the gate green;
- name any requested operator waiver explicitly.

---

# §8 Required review handback

Every formal review handback begins with exactly one of:

```text
Review Cycle N — PASS
```

or

```text
Review Cycle N — CHANGES REQUESTED
```

where `N` is one greater than the preceding formal review cycle. Do not reset the count after fixes or reviewer changes.

The handback must include:

1. Exact PR URL if one exists, plus branch and head SHA. PR number is optional transport metadata.
2. Base `b466ce8dfebaf88366eee79bad795299103a5b58` or the deliberately reconciled replacement base.
3. §1 Mission and merge-ready invariant copied exactly.
4. Finding ledger from all prior review cycles, with current closure state.
5. §7 evidence ledger: required evidence, produced result, and provenance.
6. Nano-commit list and the discrete fix/proof story for each commit.
7. Actual changed paths and focused diff stat limited to §4/bounded exception.
8. Every required test/build/manual scenario and exact result.
9. Provenance of each result: author-local, independently rerun local, CI, or manual/dogfood.
10. Baseline failures and base/head comparison.
11. Operator waivers; `none` when none exist.
12. Paths outside §4; `none` or stop report.
13. Stop conditions encountered and resolution; `none` when none exist.
14. Successors still false: rich reader/file/assets, new-world bootstrap, CR02 extraction, CR03 Hermes follow-through.
15. Confirmation that ordinary authoring's lossy-write protection was not weakened.
16. Confirmation that source presence did not silently become graph/corpus publication.

A generic PR description is neither required nor sufficient.

---

# §9 Acceptance rubric

The reviewer accepts only when every bullet is true and each behavioral claim names its §7 proof.

- [ ] Exactly one independently useful capability was delivered: lossless pasted Markdown ingress for an existing world.
- [ ] The GM can perform the §7 Build dogfood without CLI or manual filesystem edits.
- [ ] One import creates one exact source identity; retry/failure does not duplicate it.
- [ ] Every newly created Build `worldbuilding_source` used by this flow carries explicit exact world tenancy.
- [ ] The server, not the client, derives the world-scoped target path.
- [ ] Unsafe/path-traversal world IDs and client target overrides fail closed.
- [ ] Existing world root is required; this PR does not create a new world.
- [ ] Initial source import preserves exact Markdown, including constructs ordinary TipTap authoring rejects as lossy.
- [ ] `source_import` is one-time, CAS-bound, token/body/mode-bound, and cannot become an alternate overwrite API.
- [ ] Omitted write mode preserves existing `authoring` behavior for old callers.
- [ ] Later unsafe rich-editor Save remains blocked and cannot destroy imported source bytes.
- [ ] Hard reopen returns the same document identity, world, title, target, and source content.
- [ ] Existing legacy `out/workspace/worldbuilding/...` records remain usable without migration.
- [ ] New Source blank creation still works and now follows the same new-worldbuilding tenancy contract where admitted world identity is available.
- [ ] New Source rename does not move world-scoped target path.
- [ ] SourceArtifact packaging for new records carries exact world identity rather than substituting campaign identity.
- [ ] No graph extraction/promotion occurs as an implicit consequence of import.
- [ ] No production path outside §4 changed (§4 includes managed-storage exclusion paths for planner, ingest, and Hermes lexical fallback).
- [ ] Every formal review is numbered and increments the review-cycle count once.
- [ ] The PR description was not treated as a review or merge gate.
- [ ] The named successors remain unimplemented and unclaimed.

---

# Stop conditions

Stop and report rather than expanding if implementation discovers any of the following.

## Source-storage / authority stops

- Managed Markdown under `corpus/<worldId>-markdown/_dungeonbuddy/sources/` is automatically swept into a legacy manifest/index/publication path that changes authority merely because the file exists.
- Correct world placement requires a new general world registry or new-world bootstrap rather than the existing admitted Build mapping + existing world root.
- The server cannot safely distinguish a new world-scoped record from a legacy global workspace record without migrating legacy state.
- Adding `world_id` forces a broad workspace registry migration or breaks existing Plan/runbook records.

## Write-authority stops

- Existing prepare/commit authority cannot bind `source_import` mode + body + target + revision safely.
- Implementing lossless import requires a second independent filesystem writer that can race or disagree with workspace/Canvas CAS authority.
- The current Canvas cannot load an imported unsafe source while keeping exact exported Markdown authoritative.
- A second source-import can overwrite a ready source under any ordinary retry/replay path.

## Scope stops

- Correctness requires archive/delete management, file upload, asset copying, source-reader UI, extraction, Hermes, statblock, or combat changes.
- A production path outside §4 is necessary and does not clearly implement the same invariant.
- A new independently useful public contract appears that is not necessary to lossless existing-world ingress.

## Evidence stops

- Any invariant clause cannot be tested at its owning boundary.
- The §7 dogfood cannot verify exact source equality after hard reopen.
- Base/head failures require an operator waiver before acceptance.

Use this report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```

---

# Named successors after this PR

Do **not** dispatch these from pre-merge assumptions. Re-anchor after the implementation is reviewed/merged.

1. **CR01B — Rich Source Reader + file/assets ingress**
   - `.md` file loading through the same normalized source-import contract;
   - durable local assets/images;
   - faithful styled Markdown reading optimized for GM use;
   - source remains original artifact, not evidence-debug UI.

2. **CON-READY existing/new world bootstrap slice**
   - create a new world/source hierarchy from product UI;
   - make that world available to the same import flow;
   - no hardcoded Eldyrwild assumptions.

3. **CR02 — Source-Backed World Ingestion**
   - bounded semantic extraction/review/promotion from the durable source.

4. **CR03 — Hermes Source Follow-Through**
   - graph discovery → admitted provenance → bounded source-artifact exploration when graph detail is insufficient.

The next steward must begin from `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`, reconcile current `main`, inspect this PR's actual merged behavior, and only then select the next independently useful slice.
