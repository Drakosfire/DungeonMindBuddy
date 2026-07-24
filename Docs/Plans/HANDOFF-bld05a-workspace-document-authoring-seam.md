# HANDOFF — BLD-05a Workspace document authoring seam

- **Created:** 2026-07-23
- **Status:** ACTIVE / REQUEST_CHANGES — harden shared lifecycle before merge
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
| Thin Build product surface | Yes | Yes | Include only as a consumer of the proven seam |

## §1 Mission

Plan, runbook, and Build use one shared workspace-document authoring lifecycle so an operator can create, open, edit, save, recover, and navigate a document without cross-surface identity or revision drift.

## §2 Merge-ready invariant

For one workspace-document UUID, the server snapshot, durable commit receipt, local/editor base, URL selection, surface authority, lifecycle display, and Agent Interaction context identify the same authorized document revision; any mismatch fails safely without unintended mutation and provides an explicit recovery path.

Surfaces share one local-state schema and one authoring lifecycle. Worldbuilding uses null session scope, never session `0`. Route visits never create documents implicitly.

## §3 Stop / non-goals

Stop when the evidence ledger below is complete. Do not expand into extraction, SourceArtifact creation, Graph Review, publication, PDF, broad Build polish, or Plan layout redesign.

## §4 Evidence required to merge

| Guarantee | Owning boundary | Required evidence | Current state / stop condition |
|---|---|---|---|
| Snapshot and commit cannot mix revisions | registry + writer | adversarial concurrent snapshot/commit test | Implemented; independently rerun before merge |
| Commit receipt is authoritative | writer + shared hook | receipt/snapshot contract and commit-success/verification-failure proof | Implemented; verify current head |
| Verification never adopts unseen newer content | shared hook | commit rev N, verification returns N+1, next save remains blocked | Missing — stop |
| First real editor transaction persists exactly | shared editor + hook | one-transaction paste/edit test on Plan, Build, and runbook | Missing — stop |
| Surface authority gates editor, storage, save, and agent context | shared open + surface integration | Build opened with Plan/runbook UUID | Agent-context isolation missing — stop |
| Plan commit handback is one-shot | Plan integration | one commit updates parent once and render stabilizes | Missing — stop |
| Runbook reset restores actual starter content | runbook integration | reset committed runbook, refresh, exact starter restore | Missing — stop |
| Shared consumers remain regression-safe | Plan, Build, runbook | full focused suites, typecheck, production build | Full Plan suite not run — stop |
| Bare `/build` creates nothing and Build session is null | Build integration | explicit create and agent-scope tests | Implemented; rerun on current head |

## §5 Files (allowlist summary)

- Backend: `workspace_document_registry.py`, `tiptap_markdown_write.py`, routes, tests.
- Frontend seam: `tiptap/state/tiptapLocalState.ts`, `workspaceDocument/**`, agent interaction types/provider.
- Consumers: Plan canvas, runbook spike, thin `buildSurface/**`, App route/chrome.
- Process learning: this handoff, Build PLAN/ROADMAP, merge-contract design, PR-loop rule/runbook/template.

## §6 Sequence after this PR

1. Harden this seam until §2 and every §4 row pass; do not add a new capability.
2. Merge, then take one bounded polish/dogfood PR across Plan, Build, and runbook.
3. Before planning or launching extraction controls, critique that PR’s proposed invariant and required evidence against the hardened seam and dogfood findings.
