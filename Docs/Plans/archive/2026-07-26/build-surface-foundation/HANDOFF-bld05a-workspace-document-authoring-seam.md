# HANDOFF — BLD-05a Workspace document authoring seam

- **Created:** 2026-07-23
- **Status:** HISTORICAL — merged with incomplete evidence; post-merge hardening is the active gate
- **Suggested branch:** `agent/bld05a-workspace-document-authoring-seam`
- **Supersedes for Build product work:** PR #390 (draft) parallel `buildSurface/**` shell
- **PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/399
- **Merge SHA:** `ea7ad826a2ca4f9d275ce245a3884d4af72278a8`
- **Judgment:** `merged_with_incomplete_evidence` (waiver: none recorded)
- **Active gate:** [`HANDOFF-bld05a-post-merge-authoring-hardening.md`](HANDOFF-bld05a-post-merge-authoring-hardening.md)

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

## §3 Historical merge record (PR #399)

```text
state: merged
merge_sha: ea7ad826a2ca4f9d275ce245a3884d4af72278a8
judgment: merged_with_incomplete_evidence
waiver: none recorded
consequence: post-merge hardening remained the active gate
```

PR #399 landed useful foundations (atomic snapshot lock, authoritative commit receipt, discard clears storage, shared hook consumers, URL popstate, Draft labeling, nullable worldbuilding session, bare `/build` creation form). Five adversarial sequences remained open at merge and are owned by the hardening handoff — do not rewrite this history as complete.

## §4 Evidence ledger at merge (incomplete)

| Guarantee | Owning boundary | Required evidence | State at merge |
|---|---|---|---|
| Snapshot and commit cannot mix revisions | registry + writer | adversarial concurrent snapshot/commit test | Implemented |
| Commit receipt is authoritative | writer + shared hook | receipt/snapshot contract and commit-success/verification-failure proof | Implemented |
| Verification never adopts unseen newer content | shared hook | commit rev N, verification returns N+1, next save remains blocked | Missing at merge |
| First real editor transaction persists exactly | shared editor + hook | one-transaction paste/edit test on Plan, Build, and runbook | Missing at merge |
| Surface authority gates editor, storage, save, and agent context | shared open + surface integration | Build opened with Plan/runbook UUID | Agent-context isolation missing at merge |
| Plan commit handback is one-shot | Plan integration | one commit updates parent once and render stabilizes | Missing at merge |
| Runbook reset restores actual starter content | runbook integration | reset committed runbook, refresh, exact starter restore | Missing at merge |
| Shared consumers remain regression-safe | Plan, Build, runbook | full focused suites, typecheck, production build | Incomplete at merge |
| Bare `/build` creates nothing and Build session is null | Build integration | explicit create and agent-scope tests | Implemented |

## §5 Sequence after PR #399

1. Complete [`HANDOFF-bld05a-post-merge-authoring-hardening.md`](HANDOFF-bld05a-post-merge-authoring-hardening.md) until every incomplete row is proved.
2. Bounded polish/dogfood across Plan, Build, and runbook (Phase 4B) begins only from the hardening merge SHA.
3. Extraction controls remain blocked until polish findings exist and their invariant/evidence ledger are critiqued.
