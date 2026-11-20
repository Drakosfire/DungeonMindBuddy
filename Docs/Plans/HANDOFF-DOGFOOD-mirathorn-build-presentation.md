# DOGFOOD: navigable saved Build sources

Status: ACTIVE. PRIME authorized the bounded presentation lease on 2026-10-14.
Topology: serial, one presentation PR; independent ARCHITECTURE review before adoption.
Base: c9f5c21f3b835f35660b85fbd2e9a38312c401d4.
Branch: codex/mirathorn-build-reader.
Checkout: /home/drakosfire/.codex/worktrees/mirathorn-build-reader/DungeonMindBuddy.

## Invariant and scope

A long saved Build source is readable and navigable without changing its Markdown,
source hash, source-line citation coordinates or authority. Reuse the canonical
Markdown parser and heading ID allocator, including duplicate headings, inline
formatting, frontmatter and headings inside containers. Code-block contents must
not become navigation entries. Short sources do not need extra navigation.

Exclusive write lease:
- apps/live-control-ui/src/buildSurface/BuildSourceReader.tsx
- apps/live-control-ui/src/buildSurface/BuildSourceReader.test.tsx
- apps/live-control-ui/src/buildSurface/buildSurface.css
- this handoff

No ingestion, extraction, native Graph publication, corpus rewrites, backend,
shared Markdown renderer/canvas, lockfile or private configuration edits.
Shared renderer changes require a precise scope amendment first.

## Runtime and imported witness

DOGFOOD owns 5202/8000/7860, currently serving d0c2b32e from durable
.local/state/dungeonmindbuddy/rollout-candidates/buddy-diagnostic-d0c2b32/source.
Serving source is read-only. Stable 5876/8001/7861 is independent and untouched.
No presentation adoption or restart until coordinated with PRIME.

Existing conversion: corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/The City of Mirathorn.md.
Ordinary UI import created Build document a5f32e92-80d1-42c8-96bd-4587321f39e7,
revision 2, SHA-256 70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342,
exactly matching the existing 22,272-byte file. No extraction was run.
The source has 45 headings, no Markdown tables, links or images. Those absent
features cannot be declared dogfood-verified from this fixture.

## Findings outside this lease

Build reports the imported source World missing from the managed registry while
chrome reports Graph Ready. Entering Edit without typing marks the document dirty.
Both were reported to PRIME; no TipTap normalization was saved over the source.
The imported saved revision remains the ingestion handoff. These controller/authority
issues do not authorize changes outside the reader lease.

## Verification / completion

Required: owning reader tests, UI TypeScript check, cumulative diff inspection,
rendered long-source check including duplicate heading navigation and narrow width.
Preserve stale/exact citation highlight behavior. Commit/push/open the one PR,
request independent ARCHITECTURE review, and state rendered-test limitations honestly.

## Implementation evidence

The reader outline uses the existing AST and heading allocator, collapses after a
section is chosen, preserves normal anchor navigation, and adds no source writes.
Seven owning reader tests plus fifteen shared Markdown reader regressions pass
(22 total); app TypeScript and full production UI build pass. The existing Vite
large-chunk warning remains. Exact/stale source-line highlight tests still pass.
Cumulative four-path diff checked; no ingestion or shared-renderer edits.

The original live Build render screenshot is `mirathorn-build-before.png` in the
chat visualization directory. Candidate rendered acceptance remains pending
normal app deployment: browser policy rejected a local file preview, and no
protocol bypass or extra server was attempted. No candidate screenshot claim.
The imported fixture has no tables/links/images; those formats are not claimed
operator-verified. The snapshot hash and committed revision remain unchanged.
