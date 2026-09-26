# HANDOFF — SETTLEMENT: retire Campaign Supergraph roadmap authority

**Created:** 2026-09-25
**Status:** BLOCKED — design is complete; do not allocate an implementation lane
**Flow / workstream:** SETTLEMENT
**Handoff direction:** STEWARD → CODE after activation
**Design-time base:** `9473244f57e7845928fc47225fd08863ea85804b`
**PR topology:** serial after the existing UI stack
**Activation gate:** the #755–#761 UI stack is fully merged/closed, this settlement authority is on main, and a fresh re-anchor confirms no open PR or ACTIVE handoff leases `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`.

## §1 Mission and merge-ready invariant

**Mission:** Retire the Campaign Supergraph roadmap's stale claim to current
implementation authority while preserving its migration history.

**Merge-ready invariant:** The canonical roadmap path is either a historical
forwarding record or an explicitly archived program record, no current source
manifest classifies it as dispatch authority, and no active UI/product lane
depends on its pre-retirement contents.

## §2 Context, authority, and boundaries

Read in order:

1. `Docs/Reports/REPORT-repository-settlement-2026-09-25.md`
2. `Docs/Reports/graph-document-audit.md`
3. `Docs/Design/INDEX-design-agent-source-set.md`
4. current `AGENTS.md` + `Docs/Process/STEWARD-CYCLE.md`
5. current open PRs and exact `main`

**Predecessor:** this repository-settlement authority repair.
**Named successor:** none; future work is selected from domain workstreams.
**What remains false until this slice lands:** the roadmap file itself still
self-identifies as canonical.

If the UI stack has not drained, the path is still leased, or a new current
consumer is discovered, remain BLOCKED and report the consequence.

## §3 Observable paths

| Path | Required result |
|---|---|
| Fresh contributor opens old roadmap directly | Sees historical/superseded status before any old sequence |
| Fresh contributor follows README/source manifest | Is routed to current domain authorities, not Campaign sequence |
| Historical link targets roadmap | Still resolves to useful history/pointer |
| Active UI work | No in-flight design is invalidated by premature roadmap rewrite |

## §4 Write lease after activation

- `Docs/Roadmaps/ROADMAP-campaign-supergraph.md`
- `Docs/Roadmaps/archive/2026-09-25/campaign-supergraph/ROADMAP-campaign-supergraph.md` (create if explicit archive body is useful)
- this handoff only for activation metadata if the steward performs the activation sync

No runtime/code/schema/source-mirror paths are leased.

## §5 Explicit non-goals

- no UI implementation;
- no reopening Campaign/CUTOVER slices;
- no changes to CON-READY or Play sequencing;
- no DungeonMind/WorldKeeper contract change;
- no Project Sources UI mutation;
- no branch deletion.

## §6 Implementation contract

Preferred shape:

```text
old canonical roadmap body
  → preserved in archive or Git history

canonical roadmap path
  → SUPERSEDED / HISTORICAL pointer
  → current source manifest
  → settlement report
```

Do not invent a replacement global roadmap. The settlement conclusion is that
sequencing is workstream-specific.

## §7 Evidence required to merge

1. Fresh re-anchor proves #755–#761 are drained and no replacement lease exists.
2. Search proves the canonical roadmap no longer claims current/canonical
   implementation sequence.
3. Source manifest still excludes it from the clean current bundle.
4. Historical content remains accessible.
5. Repository Markdown/link checks pass.
6. `git diff --check` passes.

A new current consumer of the roadmap is a stop condition, not a reason to
silently keep old authority wording.

## §8 Required handback

Record:

- exact base/head;
- open-PR topology at activation;
- disposition of #755–#761;
- exact changed paths;
- verification commands/results;
- whether an explicit archive copy was created;
- confirmation that no new global roadmap was invented.

## §9 Acceptance

Accept only when the old roadmap is unambiguously historical, current
workstreams remain untouched, links remain useful, and no active lane lost an
authority it still depended on.
