# HANDOFF — BLD-05a post-merge workspace-document authoring hardening

**Created:** 2026-07-23, America/Denver
**Status:** ACTIVE — dispatch exactly one post-merge hardening capability.
**Canonical handoff path:** `Docs/Plans/HANDOFF-bld05a-post-merge-authoring-hardening.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Implementation base:** `ea7ad826a2ca4f9d275ce245a3884d4af72278a8`
**Suggested branch:** `agent/bld05a-post-merge-authoring-hardening`
**Predecessor:** merged PR #399, `BLD-05a: workspace-document authoring seam + thin Build`
**Named successor:** bounded shared-authoring polish and dogfood across Plan, Build, and runbook
**Operating mode:** fresh-context coding agent with adversarial lifecycle ownership; do not continue from the assumption that merge implies completion.

---

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
|---|---:|---:|---:|---:|---:|---|
| Prevent post-commit verification from adopting unseen remote content | Yes | No — hardens merged contract | Yes | Yes | Yes | Include |
| Preserve edits made while verification is in flight | Yes | No — hardens merged contract | Yes | Yes | Yes | Include |
| Persist the first real editor transaction on all three consumers | Yes | No — hardens merged contract | Yes | Yes | Yes | Include |
| Prevent rejected document authority from reaching Build editor, storage, save, or Agent Interaction | Yes | No — hardens merged contract | Yes | Yes | Yes | Include |
| Make Plan commit handback one-shot | Yes | No — hardens merged contract | Yes | Yes | Yes | Include |
| Make runbook reset a durable local reset rather than a visual claim | Yes | No — hardens merged contract | Yes | Yes | Yes | Include |
| Synchronize the BLD-05a judgment record and active gate after proof | No — process closure for this capability | No | No | No | No | Include as required handback |
| Improve state language, navigation, creation usability, and visual polish | Yes | Potentially | Yes | Maybe | Yes | Successor |
| Add extraction controls, SourceArtifact creation, ExtractionRun launch, or Graph Review handoff | Yes | Yes | Yes | Yes | Yes | Reject from this slice |

**Selected capability:** restore and prove the merged BLD-05a workspace-document lifecycle invariant under the five unresolved adversarial sequences, then synchronize repository authority so the next PR can begin from a truthful immutable base.

**Why included rows share one invariant:** each included behavior determines whether one accepted workspace-document identity and revision remains coherent across receipt, verification, editor/local state, surface authority, parent handback, persistence, and Agent Interaction. None creates a new product capability; all close failure sequences in the already-merged authoring lifecycle.

**Named successor:** bounded authoring polish and dogfood. It may improve language, affordances, navigation, creation/classification usability, Agent Interaction visibility, and visual consistency, but it must not begin until this handoff’s evidence ledger is green or explicitly waived.

---

## §1 Mission

Plan, Build, and runbook preserve one authorized workspace-document identity and revision through commit verification, first-edit persistence, cross-surface rejection, Plan handback, and runbook reset, so the merged BLD-05a seam becomes a truthful base for bounded authoring polish and dogfood.

### Merge-ready invariant

> For one workspace-document UUID, the server snapshot, durable commit receipt, local/editor base, URL selection, surface authority, lifecycle display, and Agent Interaction context identify the same authorized document revision; any mismatch fails safely without unintended mutation and provides an explicit recovery path.

### Mission falsification test

This is not one slice if implementation must also deliver extraction controls, SourceArtifact or ExtractionRun creation, Graph Review handoff, graph publication, document-management UX, broad visual redesign, new Markdown syntax support, or a second authoring state machine.

---

## §2 Context, authority, and boundaries

PR #399 merged at `ea7ad826a2ca4f9d275ce245a3884d4af72278a8` while its own PR description still marked five guarantees as merge blockers and recorded no waiver. No functional code changed after commit `c4da6262c8d8720d669561ef84a0040ff1ec4226`; later commits changed only process and planning documentation.

### Parent authority

1. `Docs/Design/DESIGN-merge-ready-invariant-evidence.md`
2. `Docs/Design/CONTRACT-workspace-document-identity-v1.md`
3. `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md`
4. `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md`
5. `Docs/Plans/HANDOFF-bld05a-workspace-document-authoring-seam.md`
6. `.cursor/rules/external-agent-pr-loop.mdc`
7. `.cursor/skills/external-agent-pr-loop/SKILL.md`
8. `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`

### Authority precedence

```text
1. Adopted repository design and identity contracts
2. Active roadmap and implementation plan
3. This checked-in hardening handoff
4. Merged implementation and owning-boundary tests
5. PR #399 body, review comments, and attached handoff context
6. Chat summaries
```

### Exact predecessor contracts consumed

**WorkspaceDocumentSnapshot:** `record`, `markdown`, `content_sha256`, `file_fingerprint`, `file_exists`, `loaded_revision`

**TiptapMarkdownWriteCommitResponse:** `document_id`, `committed_revision`, `committed_record`, `normalized_content_sha256`, `file_fingerprint`, `target_relpath`, `registry_revision`, `writer_ok`, `writer_phase`, `diagnostics`

**WorkspaceDocumentLocalState v3:** `document_id`, `kind`, `surface`, `base_revision`, `base_content_sha256`, `tiptap_json`, `exported_markdown`, `dirty`, `updated_at`, `last_local_save_at`

---

## §3 Observable-path inventory

See the dispatch message for the full inventory. Every path marked “required behavior” is merge-blocking. Do not replace owning-boundary proof with a helper-only unit test.

---

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-bld05a-post-merge-authoring-hardening.md` | Canonical dispatch authority for this slice |
| Modify | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.ts` | Receipt verification, edit-during-verification preservation, accepted-state exposure, editor update handling |
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentAuthoringMachine.ts` | Represent mismatch/reconciliation and dirty-preserving verification truthfully if the current phases are insufficient |
| Modify | `apps/live-control-ui/src/workspaceDocument/workspaceDocumentAuthoringMachine.test.ts` | Prove lifecycle transitions and labels |
| Create or Modify | `apps/live-control-ui/src/workspaceDocument/useWorkspaceDocumentAuthoring.test.tsx` | Owning-boundary hook tests for N/N+1, edit during verification, first update, rejection, and recovery |
| Modify | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx` | Ensure programmatic hydration and user updates are distinguishable without generic next-update suppression |
| Create or Modify | `apps/live-control-ui/src/tiptap/MarkdownEditorCore.test.tsx` | Prove first real transaction is emitted exactly once |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.tsx` | Publish Agent Interaction only from accepted authoring state and clear stale accepted context on rejection/navigation |
| Modify | `apps/live-control-ui/src/buildSurface/BuildSurfaceShell.test.tsx` | Prove rejected Plan/runbook UUID isolation and stale-context clearing |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Consume each authoritative receipt exactly once |
| Modify | `apps/live-control-ui/src/planSurface/PlanSurfaceShell.test.tsx` | Prove callback count is one and render stabilizes |
| Modify | `apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.tsx` | Implement real reset-to-starter local state and editor replacement |
| Modify | `apps/live-control-ui/src/tiptap/TiptapCalloutBridgeSpike.test.tsx` | Prove reset, dirty semantics, refresh restore, and first transaction |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx` | Only if needed to prove rejected/stale Build context removal through the real provider |
| Modify | `apps/live-control-ui/src/App.test.tsx` | Only if needed to prove route-level Build identity/context behavior |
| Modify | `Docs/Plans/HANDOFF-bld05a-workspace-document-authoring-seam.md` | Record PR #399 as merged with incomplete evidence and point to this active hardening gate |
| Modify | `Docs/Plans/PLAN-build-surface-worldbuilding-ingest-pr-slices.md` | Replace stale `open_under_review` state, record historical merge judgment, add hardening PR judgment/evidence, and identify next gate |
| Modify | `Docs/Plans/ROADMAP-build-surface-worldbuilding-ingest.md` | Record Phase 4A as incomplete until hardening merges, then bridge to Phase 4B |
| Modify | `.cursor/rules/external-agent-pr-loop.mdc` | Only if this work reveals a genuinely new reusable process invariant not already captured; otherwise do not touch |
| Modify | `.cursor/skills/external-agent-pr-loop/SKILL.md` | Same restriction as above; not routine doc-sync |
| Modify | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` | Same restriction as above; not routine doc-sync |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/workspaceDocument/
Maximum additional paths: 2
Allowed path kinds: one pure receipt/snapshot verification helper and its direct test
Decision rule: add only if it makes receipt agreement and mismatch behavior independently testable without duplicating lifecycle state
Required report: name the added path, why existing files could not own the rule cleanly, and confirm no new durable contract was introduced
```

```text
Directory: Docs/Archive/
Maximum additional paths: 2
Allowed path kinds: moves or archived copies of the predecessor and hardening handoffs
Decision rule: use only the repository’s existing handoff archive convention after the hardening PR is accepted
Required report: exact source and archive paths; do not invent a new archive hierarchy
```

If another path is required, stop and report it before implementation.

---

## §5–§11

Full matrices, evidence ledger, acceptance rubric, reviewer protocol, doc-sync, and stop conditions are in the operator dispatch for this slice. Implement every §6 matrix row or raise a stop condition. Do not compress or omit constraints.

### Merge-ready invariant (verbatim for PR body)

For one workspace-document UUID, the server snapshot, durable commit receipt, local/editor base, URL selection, surface authority, lifecycle display, and Agent Interaction context identify the same authorized document revision; any mismatch fails safely without unintended mutation and provides an explicit recovery path.
