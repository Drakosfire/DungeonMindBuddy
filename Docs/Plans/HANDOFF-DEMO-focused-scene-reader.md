---
title: Focused Plan scene reader with truthful Agent target
document_class: implementation_handoff
status: ACTIVE
created_at: "2026-10-06"
workstream: DEMO
pr_topology: serial
implementation_branch: codex/demo-focused-card-reader
base_ref: c714c7c6b5f5504590ae5e000de530c079ea9f17
---

# HANDOFF — focused Plan scene reader

## Authority and current lane

DEMO is the Buddy product owner and implementation steward under
[`STEWARDS-HANDOFF-demo.md`](STEWARDS-HANDOFF-demo.md). PRIME assigned this
bounded reader as the next Plan card adoption slice after Buddy #938 merged at
`b92e950cdbc68b47e202822515b13a4ba4228469`. The lane was re-anchored on
`main@c714c7c6b5f5504590ae5e000de530c079ea9f17` after #940 added the
independent synthetic Graph witness report at `Docs/Reports/`; that one-path
documentation change is outside this lease and does not alter its contract.
PRIME explicitly transferred the
three projection/CSS/integration paths and reader-specific roadmap entry from
the open #914 projection-fidelity lane into this lane. PRIME then confirmed the
conditional `PlanSurfacePage.tsx` callback path is included because source proof
shows it is necessary. The exact seven-path lease is §4.

This is one serial implementation PR, titled `DEMO: focused Plan scene reader`.
The checkout is isolated on `codex/demo-focused-card-reader` from the pinned
base above. PRIME owns independent review and merge coordination. Finish the
authorized implementation through owning-boundary verification, cumulative
diff inspection, commit, push and one PR. Do not merge autonomously.

PR #914 remains open with its prior visual hold/evidence branch preserved; it
does not block this lane and its overlapping paths are transferred here. PR
#927 remains queued design context only. PR #887 is prototype evidence only;
its content is not production authority. No second reader, Play backend,
provider, API, database, schema, runtime, migration, corpus or licensed-content
lease is granted. DOGFOOD visual quality control is required before operator
experience acceptance; it is not a prerequisite to code review or merge.

## 1. User outcome and invariant

From Plan Cards, a GM can open one exact authored Scene as a readable focused
reader, see its associated authored Beat/Choice/Option hierarchy and content,
return to the outline, and move to the previous or next Scene in projection
order. The Document view remains available and unchanged. Navigation follows
the existing validated marker hierarchy/order only; it never infers chronology,
location, or missing cards.

The current focused Scene is also the visible default Agent context target.
When the focused Scene is an exact uniquely selectable card from the verified
saved World Plan, focus publishes that exact Scene target and saved revision /
content SHA through the existing `onSelectTarget` seam. If the focused Scene is
draft-only, unverified, ambiguous, or otherwise not sendable from the committed
basis, focus clears the old Ask target. The UI must never show Scene B while
silently retaining saved target A as the default for a new Ask. Focus itself
never dispatches an Agent request and never opens the Agent drawer.

An already submitted Ask or proposal remains frozen to the target and basis
captured when submitted. Moving focus from A to B does not replay, retarget,
cancel, or misattribute the pending A turn. Existing explicit Edit target,
proposal fencing, Apply guards, Save, and Start Run pins remain independent and
unchanged. Focus is ephemeral and is reset when World, document, or verified
basis identity changes; no navigation action changes Plan Markdown or its
revision.

## 2. Bounded implementation

- Add focused-scene state and scene-only previous/next navigation to the
  existing `WorldPlanCardProjection`. Derive candidate scenes from its already
  validated projection tree. Keep authored hierarchy/order and render only the
  focused Scene plus its existing descendants, with an outline/return control.
- Keep the focused card and its Choice/Option content at a readable central
  width. Preserve current projection safety behavior: malformed markers,
  unsupported versions, mixed grammars, missing bodies and invalid parents fail
  closed without a partial reader. Reuse existing source slices and, only if
  needed for legibility, make a bounded semantic-renderer adaptation within
  this leased projection component. Do not add a parser, change marker/range
  rules, or modify native Runbook behavior.
- Reuse `selectableTargetKeys` as the exact saved/current intersection. Focus
  sets the nullable selection callback to the Scene target only when that key is
  selectable under a verified basis; otherwise it calls the callback with
  `null`, which clears prior Ask context. Manual card Ask selection continues
  to use the same seam.
- In `PlanSurfacePage`, extend only the existing selection callback to accept
  `null` and clear `selectedPlayableTarget`; preserve the validated target,
  World, document, revision and digest binding for non-null selections. Keep
  current request submission behavior: each Ask captures immutable target and
  basis at submit time.
- Preserve visible Plan/Document switching, exact Start Run identity pins,
  authored marker data, existing edit targeting and explicit Save semantics.
  Do not alter graph or Run authority.
- Use synthetic fixtures. A prototype comparison may pin one existing reference
  scene only: `scene:warehouse-tail`, `choice:last-abduction`, and its five
  option IDs (`option:save-sleepers`, `option:kill-carriers`,
  `option:track-carrier`, `option:rally-mireward`,
  `option:last-abduction-other`) at prototype source SHA-256
  `a7674ace660d7d3c4b82847a3486cf15e0df8f4a357333ad3c9185ef8f698dd7`.
  The source itself is not to be copied into Git, tests, logs, screenshots, or
  this handoff. This comparison is not a frozen-gold claim.

## 3. Failure cases that must remain explicit

1. A scene title or body text that happens to mention another scene does not
   create chronology, nesting, or a location relationship.
2. If the selected marker structure is malformed or the Scene is not a unique
   indexed target, no partial hierarchy or inferred target is rendered.
3. If focus B cannot be sent from the verified committed Plan, previous Ask
   target A is cleared before a new Ask can use it; no fallback to A occurs.
4. If Ask A is already pending when focus moves to B, the request envelope,
   eventual transcript/history attribution and any existing edit proposal stay
   bound to A. Focus does not cause another request.
5. Switching World/document/basis cannot preserve an obsolete focus or target.
   A late response remains subject to existing request identity guards.
6. Focus does not mutate the editor, persisted Plan bytes, marker identities,
   selected Edit target, proposal fence, Apply result, Save behavior, or Run pins.

## 4. Exclusive expected write set

- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx`
- `apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.css`
- `apps/live-control-ui/src/planSurface/WorldPlanCardProjection.integration.test.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`
- `apps/live-control-ui/src/planSurface/PlanSurfacePage.test.tsx`
- `Docs/Plans/HANDOFF-DEMO-focused-scene-reader.md` — this contract and truthful
  settlement only
- `Docs/Roadmaps/ROADMAP-demo.md` — reader sequencing and truthful evidence only

This is an exact file allowlist, not a directory lease. No other path, shared
contract, app state, service, port, database, external state, or runtime is
owned. If implementation requires anything beyond the list, stop and request a
scope/ownership decision from PRIME before editing that path.

## 5. Owning-boundary acceptance

1. Projection integration tests show one focused Scene with its exact authored
   descendants, outline return, previous/next by projection order, and no
   chronology inference. Focus changes only view state and the nullable
   selection callback. A malformed/duplicate/missing-parent projection fails
   closed.
2. Mounted `PlanSurfacePage` coverage proves focusing selectable B updates the
   visible unsent Agent context to B with B's exact saved revision/SHA. Focusing
   draft-only or otherwise non-sendable B clears prior saved target A; it must
   not submit a request or expose A as the default context. The Document view
   remains available.
3. Mounted race coverage starts an Ask for A, moves focus to B before the
   response, and proves the submitted request remains pinned to A, the visible
   unsent context follows B, and the late A answer remains attributed to A
   without replay or retargeting.
4. Preserve explicit Edit selection while focus moves; mounted coverage keeps
   the selected Edit target at A while focus moves to B. Keep the existing
   proposal target/Apply guard regressions passing. Preserve Save/reopen source
   bytes, Play/Run start identity pins, World/document isolation and existing
   stale basis rejection. Browsing focus causes no API, Graph, provider, or
   persistence call.
5. Run the exact focused projection integration and mounted Plan page suites,
   relevant typecheck, and `git diff --check`. Use repository RTK for noisy
   test/search/log output when available. Broaden only to resolve a concrete
   failure on this boundary. Review the exact cumulative base-to-head diff and
   prove changed paths remain within §4.
6. Inspect synthetic desktop and narrow layouts for readable focused content,
   controls, choices and authored reference/location labels. DOGFOOD performs
   separate visual quality control before operator experience acceptance.

## 6. Stop conditions and holds

Stop for PRIME if the reader needs a new parser/marker grammar, a separate
source of Agent target truth, new persistence or API authority, a route outside
the allowlist, changes to Plan/Run identity, or a second capability/PR. Keep
unknown location relationships unknown; render only authored content already
available in the projection. Preserve all test, compiler and review failures.

This implementation does not close J1–J6, prove DOGFOOD's private corpus,
certify provider or production runtime behavior, or substitute for operator
acceptance. Send PRIME the PR URL, exact base/head, allowlist, owning-boundary
evidence, independent-review status and all remaining holds. Do not merge.
