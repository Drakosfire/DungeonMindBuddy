# Report — C2 Session 27 native Play dogfood

**Status:** FINAL — post-session re-anchor record  
**Dogfood:** C2 Session 27 (Mireward climax), run at the real table on 2026-08-19  
**Dispatching handoff:** `Docs/Plans/HANDOFF-PLAY-c2s27-native-dogfood.md` (D3; exists only on the evidence branch, see below)  
**Evidence branch:** PR [#623](https://github.com/Drakosfire/DungeonMindBuddy/pull/623) `agent/play-current-beat-table-stage` @ `aa6d1119343c6ec4a65fcf3792251d62c466861d` — **closed unmerged**; retained remotely for historical recovery  
**Re-anchor authority:** `Docs/Plans/HANDOFF-PLAY-SURFACE-c2s27-reanchor-and-workspace-cleanup.md`

## Result

**BLOCKED / PLAY NOT READY**

Exact Run admission worked end-to-end against the real Session 27 Runbook. The native Play
table experience did not. The GM ran the session from the HTML Combat Tracker and abandoned
native Play almost immediately.

This supersedes the interim branch report, which recorded `NOT RUN` while the session was
still in progress.

## Exact identities

```text
Runbook document ID: 8235ce04-5023-485c-92f0-2d8d81d64f50
Runbook revision:    3
Runbook SHA:         2b7f74177d340031b0148893badd46872f8d41b43499593f068b3a483a85c521
Failed first Run UUID (do not reuse): d71541f1-e1d0-4a1e-8a26-60654ef6dd9b
Replacement Run UUID:                 07225b19-7df3-4335-ae14-22e4b133eac4
exact /play route:   /play?run=07225b19-7df3-4335-ae14-22e4b133eac4
PR #623 head:        aa6d1119343c6ec4a65fcf3792251d62c466861d
```

## What was actually used

- Phase A helper dry-run / `--apply` / second `--apply` no-op (branch tooling).
- Shipped `/play` Start Run for `C2 Session 27 — Mireward Climax` (twice; first Run blocked on
  P1 admission of plain Markdown blockquotes, artifact flattened and recommitted as revision 3).
- Native READY Table deck on Run `07225b19-...` — briefly.
- The HTML Combat Tracker (`evals/c2_live_prep/mireward-prep/combat.html`) as the actual table
  instrument for the session.
- Plan / TipTap prep authoring, whose export then lost work (see below).

## What worked

- Second Start Run allocated Run `07225b19-...`, sealed the manifest, and reached READY against
  revision 3. Exact Run creation/admission is no longer the blocker.
- The HTML Combat Tracker carried the real session: adding the party, named NPCs, and threats
  from a pool, live HP tracking, and export/import of board state.

## Operator observations at the table (final)

1. Leaving Play and returning forced Run selection again.
2. Ordinary re-entry encouraged creation of duplicate Runs.
3. The chooser rapidly accumulated useless duplicate UUIDs.
4. Native Play did not meaningfully reproduce the useful Of Conks / Hempholm prototype
   interaction/design.
5. Decision loading / branch visibility was unclear.
6. Plan ideas did not enter Play with sufficient semantic fidelity (Plan export dropped
   playable blocks and styling).
7. Beat appears to be the larger useful hierarchy over Scenes.
8. Decisions should carry consequences and reshape which Scenes remain possible/relevant.
9. The Combat Tracker was materially more useful than native Play.
10. Combat state must become durable and independent of browser/worktree.
11. Statblock and roll-table opening remain first-class table needs.

## Friction recorded by the branch report (still true)

| Severity | Moment | Cost at table | Candidate owner |
|---|---|---|---|
| High | Native Table deck vs Of Conks / Hempholm prototype | GM cannot use Play as a refined table instrument; attention stays on shared chrome and lists instead of the next few minutes | Play surface projection; the deck is an identity browser, not a current-moment instrument |
| High | READY Table/Runbook + Scene/Beat nav: light text on light button backgrounds | GM cannot read which control is which; Play is unnavigable as a table surface | Shared Surface Interaction / AppChrome plus Play-specific presentation; Play must be legible and prototype-quality within shared AppChrome, not create a second chrome boundary |
| High | First READY blocked: `bound Runbook Markdown failed P1 admission` (plain `>` blockquotes, lines 33/43) | Session cannot start until the artifact is flattened and recommitted | Playable Markdown admission / authoring UX; Play UI collapsed two line-level warnings into one generic READY error |
| Medium | First Run remains bound to the rejected SHA/revision | Reloading `/play?run=d71541f1-...` cannot recover; a replacement Run was required | Runtime/start recovery; Run continuity |

## Decision questions — answered by observed use

1. **P3B / exact graph-reference opening:** deferred. The table surface was abandoned before
   reference opening mattered. P3B remains designed, NON-DISPATCHABLE behind the new sequence.
2. **Plan → Runbook authoring:** confirmed a first-class blocker, and worse than admission
   warnings: the Plan→Playable path lost authored blocks and styling. Plan must author/adopt
   the exact Playable material rather than export a lossy derivative.
3. **Playable authoring controls:** the fixed `Runbook → Scene → Beat` hierarchy is rejected
   by table evidence. Beat is the larger useful hierarchy; Scenes are concrete situations
   inside a Beat; Decisions carry consequences and reshape later Scene/Beat relevance.
   This is not structurally compatible with the shipped P1/P2 wiring: current
   Scene/Beat/Choice containment, P2B1 manifest membership/versioning, P2B2
   current-position semantics, sealed Run/manifests, and P2C migration/rebase
   behavior all require a reviewed redesign before implementation.
4. **Runbook storage policy:** durable mutable state is the rank-1 residual. Workspace drafts
   and registries are checkout-local; jumping worktrees lost authored work.
5. **Combat / P4:** the Combat Tracker proved the interaction; its state must become durable
   and browser/worktree-independent before the P4 Threat→Combat mutation is re-pinned.
6. **Runtime ergonomics:** yes — and worse than the branch report knew. Re-entry forced
   re-selection and duplicate Run creation; active-Run continuity (Resume vs Start New) is a
   precondition for any further Play table work.
7. **No new capability before re-anchor:** correct. The re-anchor selects separate
   domain-first slices: Lane A (active-Run continuity) and Lane B (durable Combat
   state). Lane B must first resolve the retained uncommitted Combat-save worktree.
   A common persistence primitive is extracted only if both slices prove a bounded
   common invariant. Then the Beat/Scene/Decision + Plan→Playable design, including
   the P1/P2 redesign, is reviewed before any native Play table implementation.

## Disposition of PR #623

PR #623 is dogfood/mining evidence, not an implementation candidate.

Kept as evidence (recoverable on the remote branch):

- this dogfood's setup helper, operator runbook, and D3/D4 handoffs;
- `DESIGN-play-native-current-moment-deck.md` (Scene-first; superseded by observation 7 and
  intentionally not promoted to `main`);
- the C2S27 runbook artifact, Session 27 prep prose, and the generated Mireward Latchling
  statblock (campaign content, not authority);
- the Combat Tracker pool/named-people implementation and the D4 table-stage code
  (multi-capability bundle; not merged).

Rejected for merge: the Table implementation, hidden Scenes prose parsing, Combat
localStorage changes, and the bundled multi-capability shape itself.

## Recommendation for the record

Continue Session 27–era play from the HTML Combat Tracker and Plan. Do not restore #578, do
not merge #623, and do not start another native Play table implementation until the
Beat/Scene/Decision + Plan→Playable model has been designed and reviewed.
