---
pr_body_template: |
  ## Outcome

  Build now renders one shared document-bound Markdown canvas. The Build extraction
  capability consumes the canvas's exact committed-clean document envelope instead
  of independently reloading the workspace snapshot or reading editor local storage.

  ## Merge-ready invariant

  For one selected Build workspace-document UUID, the rendered editor, local draft,
  authoritative snapshot, commit receipt, Agent Interaction context, and every
  document-consuming command identify the same document and revision/digest authority.
  Extraction can launch only from a committed-clean envelope produced by that
  authority; document changes invalidate pending document commands; generic canvas
  modules import no Build, ExtractionRun, or Graph Review types.

  ## Evidence required to merge

  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Build lifecycle remains behavior-identical | Build + canvas | characterization tests before/after migration | {{TODO}} |
  | One authority produces extraction admission | canvas session | dirty/conflict/revision/digest matrix | {{TODO}} |
  | Extraction no longer re-proves readiness | source boundary | import/source guard | {{TODO}} |
  | Document commands invalidate safely | command host | document switch + unmount races | {{TODO}} |
  | Launch/refresh exact-run behavior survives | Build plugin | both start-order race suites | {{TODO}} |
  | Canvas is surface-neutral | module boundary | forbidden-import AST/source tests | {{TODO}} |
  | Plan is unchanged | diff + regression | no Plan production paths; focused Plan suite | {{TODO}} |
  | Backend contracts are unchanged | diff boundary | no backend paths | {{TODO}} |

  ## Scope and explicit deferrals

  {{TODO: base/head, characterization commit, actual paths, paths outside allowlist,
  and successors still false}}

  ## Evidence produced

  ### Automated
  {{TODO}}

  ### Adversarial
  {{TODO}}

  ### Regression
  {{TODO}}

  ### Manual / dogfood
  {{TODO}}

  ## Gaps, waivers, and stop conditions
  {{TODO}}
---

# HANDOFF — Build-first shared Markdown canvas

**Created:** 2026-07-26, America/Denver  
**Status:** PREPARED / DRAFT — dispatch only after the documentation re-anchor PR
merges; re-anchor to that immutable merge SHA before implementation.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-pr425-build-first-markdown-canvas.md`  
**Planned implementation PR:** #425  
**Planning base:** `8a73b10185e0e4b5c84bca92c2b1f3e0deda9432`  
**Implementation base:** merge SHA of the documentation re-anchor PR (#424)  
**Suggested branch:** `agent/pr425-build-first-markdown-canvas`  
**Design authority:**
`Docs/Design/DESIGN-shared-markdown-canvas-surface-composition.md`  
**Sequencing authority:**
`Docs/Plans/PLAN-shared-markdown-canvas-build-first.md`

> This handoff delivers MC-01 only. Do not begin MC-02 capability composition or
> MC-03 node authoring in this PR.

## §0 Capability decomposition

| Candidate outcome | Independently useful? | Public contract changed? | Decision |
|---|---:|---:|---|
| Reusable headless Markdown canvas session over the existing authoring hook | Yes | Additive frontend API | Include |
| Reusable rendered Markdown canvas with generic status/recovery/action slots | Yes, required by same consumer migration | Additive frontend API | Include |
| Document-bound command arbitration and admitted envelopes | Yes, required to remove parallel Build authority | Additive frontend API | Include |
| Migrate Build editor/save/recovery to the canvas | Yes | Existing product behavior preserved | Include |
| Make Build extraction consume `committed_clean` envelope | Yes | Internal tool contract | Include |
| Common Edit/Tools capability catalog | Yes | Broader surface contract | Successor MC-02 |
| Migrate Plan or runbook | Yes | Product behavior | Reject |
| Node authoring | Yes | Graph authoring/write boundary | Reject / MC-03 design gate |
| BLD-10c dispositions UI | Yes | Product workflow | Reject |
| Agent Interaction R10 relocation | Yes | App chrome lifetime | Reject |

## §1 Mission and invariant

### Mission

```text
Promote the already-hardened workspace-document authoring lifecycle into a reusable
Markdown canvas session and view, migrate Build as the first consumer, and bind Build
extraction to one exact canvas-produced committed-clean document envelope without
changing Build behavior.
```

### Merge-ready invariant

```text
For one selected Build workspace-document UUID, the rendered editor, local draft,
authoritative snapshot, commit receipt, Agent Interaction context, and every
document-consuming command identify the same document and revision/digest authority.
Extraction can launch only from a committed-clean envelope produced by that authority;
document changes invalidate pending document commands; generic canvas modules import
no Build, ExtractionRun, or Graph Review types.
```

## §2 Existing authority to preserve

The implementation must reuse, not replace:

- `useWorkspaceDocumentAuthoring`;
- `workspaceDocumentAuthoringMachine`;
- local-state v3 and reconciliation helpers;
- `MarkdownEditorCore`;
- current prepare/commit/verification authority;
- current exact-run and handoff validation in `useBuildExtraction`;
- current Agent Interaction source-envelope publication semantics.

The slice may reorganize those consumers behind a new session/provider. It must not
introduce another document state machine or local-storage schema.

## §3 Required contracts

### `MarkdownCanvasSession`

Expose at least:

- truthful phase/status/error;
- record, snapshot, dirty state, and editor content;
- editor handle/update callbacks;
- save/reload/discard;
- `getAdmittedDocument(policy)`;
- `runDocumentCommand(spec, execute)`;
- active command state.

The exact React shape may be provider + hook or one hook returning context. The public
contract must be tested independently of Build.

### `AdmittedDocumentEnvelope`

For `committed_clean`, include exactly the document authority needed by extraction:

```ts
{
  documentId: string;
  revision: number;
  contentSha256: string;
  contentStatus: "committed";
  documentKind: WorkspaceDocumentLocalKind;
  surfaceId: "build";
}
```

Do not include extraction profile, SourceArtifact, ExtractionRun, or handoff fields.

### Document command host

Must support:

- command ID;
- conflict declaration;
- admission policy;
- synchronous duplicate refusal;
- invalidation on document selection change and unmount;
- stale completion suppression;
- abort signal or equivalent cancellation token;
- plugin-visible pending/error result.

The command host arbitrates document-consuming operations. It does not own run
adoption or URL/local run persistence.

## §4 Files in scope

Default deny outside this allowlist.

### Create

```text
apps/live-control-ui/src/markdownCanvas/MarkdownCanvas.tsx
apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.tsx
apps/live-control-ui/src/markdownCanvas/markdownCanvasTypes.ts
apps/live-control-ui/src/markdownCanvas/useCanvasCommand.ts
apps/live-control-ui/src/markdownCanvas/MarkdownCanvas.test.tsx
apps/live-control-ui/src/markdownCanvas/MarkdownCanvasSession.test.tsx
apps/live-control-ui/src/markdownCanvas/useCanvasCommand.test.tsx
apps/live-control-ui/src/markdownCanvas/markdownCanvasBoundaries.test.ts
apps/live-control-ui/src/buildSurface/buildMarkdownCanvasAdapter.ts
```

The worker may choose equivalent filenames inside
`apps/live-control-ui/src/markdownCanvas/`; report exact substitutions.

### Modify

```text
apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx
apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx
apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx
apps/live-control-ui/src/buildSurface/BuildIngestToolbar.tsx
apps/live-control-ui/src/buildSurface/BuildIngestToolbar.test.tsx
apps/live-control-ui/src/buildSurface/useBuildExtraction.ts
apps/live-control-ui/src/buildSurface/useBuildExtraction.test.ts
apps/live-control-ui/src/buildSurface/buildSurfaceConfig.ts
apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts
apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.test.tsx
```

`useWorkspaceDocumentAuthoring` changes must be additive extraction seams only. A
rewrite of its reducer/lifecycle is a stop condition.

### Bounded discovery

At most two additional frontend test/helper paths are allowed when required for:

- an existing shared test fixture used by Build;
- AppChrome test plumbing needed to prove editor tools remain reachable.

No production path outside `markdownCanvas/**`, `buildSurface/**`, and the additive
workspace-document hook seam is allowed without stopping.

## §5 Explicitly out of scope

```text
apps/live-control-ui/src/planSurface/**
apps/live-control-ui/src/ingestSurface/**
apps/live-control-ui/src/planSurface/projection/**
apps/live-control-ui/src/agentInteraction/**
apps/live-control-ui/src/chrome/**
apps/live_control_server/**
src/graph_memory/**
Docs/Design/**
Docs/Plans/**
```

Also out of scope:

- common capability catalog or `SurfaceConfig` generalization;
- Plan/runbook migration;
- graph node authoring;
- Graph Review dispositions;
- visual redesign;
- extraction profile changes;
- API schema changes.

## §6 Behavior matrix

| Sequence | Required result |
|---|---|
| Open valid Build document | Same content, title, metadata, status, and Agent context as base |
| Edit first transaction | Local draft persists; dirty; extraction envelope absent |
| Save cleanly | Same commit/verification behavior; `committed_clean` envelope appears only after authoritative agreement |
| Dirty document → Extract | No launch API call |
| Draft/uncommitted document → Extract | No launch API call |
| Conflict/rejected/load error → Extract | No launch API call and no stale accepted context |
| Clean committed document → Extract | Request uses envelope revision and digest exactly |
| Save begins while Extract attempted | Declared conflict prevents launch |
| Extract begins while Save attempted | Declared conflict policy is deterministic and tested |
| Refresh then Extract | New exact run remains authoritative; stale refresh cannot overwrite |
| Extract then Refresh | Refresh cannot cancel or clear pending extraction |
| Switch A→B during save/extract/refresh | A completion cannot alter B editor, status, envelope, run, URL, storage, or context |
| Unmount during command | No post-unmount state mutation |
| Existing exact run reload | Current run ID/handoff validation remains unchanged |
| Open Graph Review | Exact handoff href and identities remain unchanged |

## §7 Verification

Run from `apps/live-control-ui` unless noted:

```bash
npm test -- --run src/markdownCanvas
npm test -- --run src/buildSurface
npm test -- --run src/workspaceDocument
npm test -- --run src/planSurface/PlanSurfaceShell.test.tsx
npm run typecheck
npm run build
```

Required source/boundary proofs:

```bash
rg 'getWorkspaceDocumentSnapshot|readWorkspaceDocumentLocalState' \
  src/buildSurface/useBuildExtraction.ts
# expected: no matches

rg 'ExtractionRun|GraphReviewHandoff|buildSurface|worldbuilding' \
  src/markdownCanvas
# expected: no production imports/types; test prose may be excluded explicitly
```

If repo-wide typecheck/build is red on the implementation base, record exact
base/head diagnostics. Do not claim green; no new canvas/Build diagnostic is allowed.

## §8 Adversarial evidence

Tests must use controlled deferred promises/barriers, not timing sleeps, for:

- both launch/refresh start orders;
- save/extract conflicts;
- document change during every command phase;
- command completion after unmount;
- edit during save;
- malformed or mismatched admitted envelope;
- rejected Build authority after a previously valid document.

At least one test must prove the extraction plugin cannot manufacture its own envelope.

## §9 Stop conditions

Stop and report rather than widening the slice if:

- the canvas needs an ExtractionRun or Graph Review type;
- behavior preservation requires changing backend APIs;
- Plan production code must change;
- `useWorkspaceDocumentAuthoring` must be replaced rather than wrapped;
- one command host cannot preserve existing launch/refresh behavior without moving
  run-domain ownership into the canvas;
- AppChrome or Agent Interaction production ownership must move;
- Build needs a generic SurfaceConfig redesign to complete MC-01;
- a second independently useful capability appears.

## §10 Required handback

The PR must state:

1. base, characterization, and head SHAs;
2. exact changed paths and substitutions;
3. final public canvas/session/envelope/command types;
4. which authority moved and which Build state stayed plugin-owned;
5. proof that `useBuildExtraction` no longer reloads/re-proves document readiness;
6. behavior-matrix results;
7. race-test mechanism and both start-order outcomes;
8. Plan regression result;
9. paths outside §4;
10. stop conditions, waivers, and baseline failures;
11. explicit confirmation that MC-02, MC-03, BLD-10c, R10, and Plan migration remain false.
