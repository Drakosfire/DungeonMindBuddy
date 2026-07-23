# HANDOFF — BLD-05a Workspace document authoring seam

- **Created:** 2026-07-23
- **Status:** ACTIVE / REQUEST_CHANGES (PR #399 round 1) — complete shared lifecycle before merge
- **Suggested branch:** `agent/bld05a-workspace-document-authoring-seam`
- **Supersedes for Build product work:** PR #390 (draft) parallel `buildSurface/**` shell
- **PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/399

## §0 Capability

| Candidate outcome | Independently useful? | Durable/public contract changed? | Decision |
|---|---:|---:|---|
| Registry-authorized `WorkspaceDocumentSnapshot` content read | Yes | Yes | Include |
| Shared local-state v3 with base revision/fingerprint | Yes | Yes | Include |
| Shared authoring state machine (Plan/runbook/Build consumers) | Yes | Yes | Include |
| Nullable `AgentInteractionScope.sessionNumber` | Yes | Yes | Include |
| Thin Build product surface | Yes | Yes | Successor/same branch after seam proofs |

## §1 Mission

Prove one coherent workspace-document revision across registry metadata, committed Markdown, content fingerprint, local-draft base, save CAS, URL state, and agent context—or enter an explicit conflict/error state without mutation.

## §2 Invariant

For one workspace document UUID, the editor, registry metadata, committed Markdown, content fingerprint, local-draft base, save CAS, URL state, and agent context must all describe one coherent document revision—or the surface must enter an explicit conflict/error state without mutation. Surfaces must share one local-state schema and one authoring state machine, with null session scope for worldbuilding (never session `0`) and no implicit document creation on route visit.

## §3 Stop / non-goals

Stop when proofs below hold. Do not expand into extraction, SourceArtifact creation, graph review, publication, PDF, or Plan layout redesign.

## §4 Proof obligations

1. Committed doc reopens with exact content after clearing localStorage.
2. Refresh after save preserves UUID, revision, metadata, and content.
3. Dirty local draft restores only when base revision/fingerprint matches.
4. Server advance while dirty local draft exists → conflict recovery; cannot overwrite unseen content.
5. Missing committed bytes for `content_status=committed` → integrity failure.
6. Visiting `/build` without ID → no durable write until explicit create with explicit metadata.
7. Build publishes `sessionNumber: null`, not `0`.
8. Plan and Build use one local-state schema and one shared authoring state machine.
9. Backend workspace/writer tests, focused UI tests, typecheck pass.

## §5 Files (allowlist summary)

- Backend: `workspace_document_registry.py`, `routes/workspace_documents.py`, tests
- Frontend: `tiptap/state/tiptapLocalState.ts`, `workspaceDocument/**`, agent interaction types/provider
- Build: thin `buildSurface/**` consumer; App route/chrome
- Docs: this handoff, PLAN/ROADMAP/CONTRACT updates
