# GRAPH: readable arrows and temporary focus layout

Status: ACTIVE. Owner: graph presentation workstream. User authorized readable
predicate phrases along arrows, dynamic bubble spacing in Focus, and shipping
the accepted preview. World data and saved overview positions are not changed.

## Scope and authority

Base at activation: `3fbf800e0f134ba9a1396156c22c18c614c8f72d`.
Branch: `codex/graph-edge-phrases-20261112`.
Topology: parallel-independent implementation with explorer-menu PR #2518;
release integration follows that predecessor so the reviewed menu remains intact.
Release re-anchor: `62e6b58c3cf3005ac92dd5bc17ab94865030517d`, including merged header #2518. Header ownership transferred its handoff for truthful backward-looking settlement.
Write lease: this handoff, `HANDOFF-GRAPH-explorer-menu.md` settlement, and
`apps/live-control-ui/src/localWorld/worldGraphCanvas/` files
`WorldGraphCanvas.tsx`, `WorldGraphCanvas.test.tsx`, `worldGraphCanvas.css`,
`edgeCaption.ts`, `edgeCaption.test.ts`, `focusedGraphLayout.ts`, and
`focusedGraphLayout.test.ts`.

## Invariants

- Predicate identifiers, endpoints and arrow direction are unchanged. Only
  display underscores become spaces. Full relationships remain accessible.
- Upright phrases occupy available spans along arrows, not opaque plates.
  Colliding/short phrases can be omitted or abbreviated; hover and keyboard
  focus disclose the full source, predicate and target. Do not claim every
  relationship is labelled simultaneously.
- Nodes and connector ports retain hit priority over crossing edge strokes.
  Dragging an arrow still pans; inspection does not create graph operations.
- Focus uses temporary radius-aware neighborhood positions. Moving within
  Focus changes only that temporary arrangement. Exit restores saved overview
  positions. New revision, focus change, and interrupted gestures cannot leak
  temporary coordinates into saved layout writes.
- Fit accounts for asymmetric neighborhoods and self-loops. User pan/zoom does
  not restart layout simulation. No continuous physics or new dependency.

## Evidence and acceptance

Owning tests cover direction, readable phrasing, Unicode/truncation, loops,
parallel/reciprocal edges, collision alternatives, full disclosure, paint order,
pan, temporary moves, exit restoration and interrupted gestures. Use the
repository exact-source hosted and discovered verifier; broad discovery remains
red unless actually proven otherwise. Independent exact-head review and user
acceptance remain distinct gates.

The retained Elderwyld Stafl diagnostic has 23 displayed objects and 32
relationships. The reviewed temporary focus projection produced 23 captions,
including `owns`, `travels to`, and `participates in`, at fitted zoom and 153%.
This is a DOM diagnostic, not a claim that all 32 edges have labels or that a
live World was read. Source-only replay material stays outside the repository.

Preview uses the established loopback port 5248, read-only retained data, atomic
hashed-asset publication, and separate browser layout storage. Preserve old
assets and storage when updating. Preview process is a transient user service,
not a reboot-persistent deployment. Live runtime changes require owner
coordination after merge; no World mutations are part of this slice.
