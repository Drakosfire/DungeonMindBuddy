# HANDOFF — SBW12 Revision-pinned Markdown/Tiptap statblock embed

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW10` and `SBW11` merge; re-anchor parser, Tiptap extension, document hydration, and resolver paths.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw12-revision-pinned-markdown-tiptap-embed.md`  
**Workstream:** `SBW12`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: a Plan document can store, reload, render, and preserve an exact revision-pinned statblock locator as a typed Markdown/Tiptap block. Do not add revision creation, automatic upgrade, generic arbitrary embeds, combat, or media selection.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Define canonical statblock Markdown directive | No alone; required persisted representation | Yes | No | Include |
| Parse/serialize typed Tiptap node losslessly | No; required round-trip | Yes | Yes | Include |
| Resolve/render exact revision in Plan canvas | Yes | No | Yes | Include |
| Insert block from Threat Sheet/workbench | No; required usable entry path | No | Yes | Include |
| Hydrate committed Plan content | Yes | Yes | Yes | Predecessor `SBW11` |
| Automatically upgrade to latest | Yes | Yes | Yes | Prohibited; explicit upgrade `SBW14` |
| Generic React/component embed framework | Yes | Yes | Broad | Exclude |

**Selected capability:** a Plan document stores one exact statblock locator and renders it through the shared Threat Sheet/statblock projection across save and fresh reload.

**Why included rows share one invariant:** directive, Tiptap node, resolver, insertion, and round-trip are one durable document block contract; none is independently usable without the others.

## §1 Mission

A GM can insert an exact statblock revision into a Plan document and reopen it later so the document retains a stable locator while the shared renderer resolves the same mechanics.

**Invariant**

```text
The document persists exact provider/statblock/revision/view attributes; serialization and hydration preserve them semantically, and rendering never substitutes latest or copied canonical Markdown.
```

**Mission falsification test**

```text
This is not one slice if implementation must also create a new mechanics revision, update existing embeds automatically, add a generic embed platform, modify graph truth, or mutate combat/media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §10; Plan Surface Toolbox; tracker `SBW12`; Tiptap/Markdown save/hydration contracts |
| Repository rules | `AGENTS.md`; one projection/renderer family; two-phase writer; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW10–11` |
| Predecessor contract | Exact Threat Sheet/revision read projection; committed Plan content read/hydration; Markdown parser/serializer; Tiptap extension patterns |
| Exact input consumed | `provider=dungeonmind`, exact `statblock_id`, exact `revision_id`, `view`, optional exact `threat_id` |
| Named successor | `SBW14` explicit scoped embed upgrade |
| What remains false | Embed cannot create/edit mechanics or follow latest automatically |
| Explicit non-goals | Generic embed registry, revision append, graph update, combat, media selection, portable snapshot export unless trivial and separately reviewed |

Read in order:

1. integration design §10
2. tracker `SBW12`
3. merged `SBW10` exact projection API/component
4. merged `SBW11` committed content hydration and local precedence
5. `CalloutNode`, `RunbookReferenceNode`, Markdown parser/serializer, Plan canvas extension registration
6. two-phase Markdown writer and tests

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Insert from Threat Sheet | No typed embed | Insert node with exact locator/view/threat context | Yes | projection action/Plan editor |
| Insert from mechanics-saved workbench | No typed embed | Insert exact accepted ref when available | Yes | workbench action/Plan editor |
| Render in editor | Unsupported Markdown/paragraph | Node view resolves exact revision through Buddy backend | Yes | Tiptap node/NodeView |
| Save to Markdown | Serializer lacks directive | Emit canonical stable directive | Yes | serializer |
| Fresh reload | Parser treats directive unsupported | Recreate exact node/attrs and render same revision | Yes | parser/hydration |
| Missing exact revision | N/A | Unresolved editable block retaining locator | Yes | node view |
| Server unavailable | N/A | Unavailable state retaining locator; document remains editable | Yes | node view |
| Newer revision exists | N/A | Existing embed unchanged; optional non-destructive notice only | Yes | resolver/UI |
| Change view summary/full | No node | Update only `view` attr; save/reload preserved | Yes | command/node |
| Copy/export Markdown | Unsupported block | Canonical directive copied, not expanded mechanics | Yes | serializer |
| Unknown/invalid directive attrs | Imported as paragraph or unsafe | Diagnostic/unresolved literal; never arbitrary request | Yes | parser/validator |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/tiptap/extensions/StatblockEmbedNode.tsx` | Typed Tiptap block/NodeView/commands |
| Create | `apps/live-control-ui/src/tiptap/extensions/StatblockEmbedNode.test.tsx` | rendering/commands/unresolved proof |
| Create | `apps/live-control-ui/src/tiptap/markdown/statblockEmbedMarkdown.ts` | strict directive attrs/parser/serializer helpers |
| Create | `apps/live-control-ui/src/tiptap/markdown/statblockEmbedMarkdown.test.ts` | exact round-trip/invalid diagnostics |
| Modify | `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts` | Recognize canonical directive block |
| Modify | current semantic Markdown serializer (`calloutMarkdown.ts` or renamed successor) | Serialize statblock node canonically |
| Modify | parser/serializer tests | mixed document round-trip proof |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Register extension and insertion command/panel hook |
| Modify | focused Plan canvas tests | insertion/save/reload behavior |
| Modify | `apps/live-control-ui/src/statblocks/threat/ThreatSheet.tsx` | Insert-in-Plan action through existing context seam |
| Modify | Threat Sheet/workbench tests | exact attrs passed |
| Modify | existing projection/runtime context only if needed to provide active editor insertion callback | no second container/editor store |
| Modify | API types/functions only if the exact Threat Sheet resolver cannot be reused directly | exact read only |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/tiptap/, apps/live-control-ui/src/planSurface/, apps/live-control-ui/src/statblocks/, apps/live-control-ui/src/agentInteraction/
Maximum additional paths: 7
Allowed path kinds: extension registration, editor command bridge, existing projection action context, style/token file, focused tests
Decision rule: include only to insert, serialize, hydrate, resolve, or render the one statblock block through existing Plan/projection systems
Required report: prove no second editor/projection registry or generic embed framework was introduced
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| creating/appending mechanics revision | `SBW13` |
| updating embed to another revision | `SBW14` |
| automatic latest/campaign-preferred resolution | violates pinned invariant |
| graph binding write | `SBW14` or governed graph path |
| combat insertion | `SBW15` |
| image generation/selection | `SBW16–17` |
| generic arbitrary component directives | separate architecture |
| copied full statblock JSON/Markdown in document | forbidden ownership collapse |
| changing document writer safety/confirmation | existing writer authority |

## §6 Implementation contract

### Canonical Markdown

```markdown
:::dmb-statblock{provider="dungeonmind" statblock="sb_abc" revision="rev_def" view="full" threat="threat:example"}
:::
```

Canonicalization decisions:

- Attribute order is fixed: `provider`, `statblock`, `revision`, `view`, optional `threat`.
- `provider` must be `dungeonmind` in v1.
- IDs are bounded and validated against explicit safe locator syntax; they are opaque, not paths or URLs.
- `view` is `summary|full`.
- `threat` is optional exact graph node context; it does not control mechanics identity.
- No body content is permitted in v1. Non-empty body is diagnostic/unsupported, not silently discarded.
- Escaping/quoting rules are deterministic and tested. Reject control characters, newlines, and unknown attrs.

### Tiptap attributes

```text
StatblockEmbedAttrsV1:
  provider
  statblockId
  revisionId
  view
  threatId?
```

### Resolution

- NodeView calls DungeonBuddy exact projection/read boundary, never DungeonMindServer directly.
- With `threatId`, compose through Threat Sheet only when the binding matches the exact statblock/revision or display a context mismatch diagnostic. Mechanics still resolve by exact statblock/revision.
- Without `threatId`, render an accepted mechanics statblock view from exact revision.
- Missing/unavailable state retains attributes and offers retry/remove/change-view actions; no “repair” to latest.

```text
Input:
  exact typed locator attrs in Tiptap JSON or canonical Markdown

Output:
  exact Tiptap node, canonical directive, and shared renderer projection/unresolved state

Invariant:
  exact attrs survive every representation and drive exact read

Failure behavior:
  malformed directive -> import diagnostic and preserved literal/unresolved representation according to parser policy
  unknown provider/view/attr/body -> fail closed, no request
  exact revision missing/unavailable -> unresolved NodeView retaining locator
  threat context mismatch/denied -> mechanics may render only under explicit exact-mechanics mode; threat composition unavailable and diagnostic visible
  writer failure -> existing document content/local dirty state remains

Replay / idempotency:
  Markdown -> Tiptap -> Markdown yields canonical semantically equivalent directive
  Tiptap JSON save/reload preserves attrs exactly
  repeated exact read is safe
  newer revision does not alter output

Trust boundary:
  Verifies: attr syntax/enums, exact IDs, backend response/digest
  Records without proving: creative relevance of embedded statblock to surrounding prose
  Rejects: arbitrary URL/path, copied mechanics payload, provider HTML, latest fallback
```

### §6A State and fallback matrix

| Path | Loading | Success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/newer | Retry |
|---|---|---|---|---|---|---|---|
| Markdown import | parse attrs | typed node | invalid literal/diagnostic | N/A | fail closed | N/A | edit source/node |
| Node render | skeleton with locator | exact shared renderer | 404 unresolved | unavailable unresolved | digest/context mismatch diagnostic | update available does not rebind | safe exact retry |
| Save/export | serialize current attrs | canonical directive | N/A | writer unavailable uses existing error | invalid attrs block safe save or serialize literal per declared policy | unchanged | normal writer retry |
| Fresh reload | hydrate committed Markdown | same exact node/render | unresolved retained | unavailable retained | diagnostic retained | no automatic update | retry read |

No fallback to latest, label/name, corpus path, candidate cache, or copied snapshot.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Persistence consequence |
|---|---|---|---|---|
| Statblock | exact `statblock_id` attr | none | No | stored directive attr |
| Revision | exact `revision_id` attr | none | No latest | stored directive attr |
| Threat context | optional exact graph node ID | mismatch/denied diagnostic | No label lookup | composition only |
| Node | Tiptap document position/node attrs; no independent durable block ID required in v1 unless editor architecture mandates | duplicate embeds allowed | No dedupe | each block pinned independently |
| View | exact enum | invalid rejects | No | stored attr |
| Rename | display names may change | none | No rebind | IDs stable |
| Deletion/missing revision | unresolved/tombstone-like block | none | No | locator retained |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Insert/save | canonical Markdown directive + local Tiptap JSON | exact semantic attrs | duplicate blocks permitted | parser schema/version documented | remove block through editor |
| Fresh load | committed Markdown parsed to node | attrs preserved | deterministic | invalid/unknown diagnostic, source preserved | source unchanged until save |
| Change view | node attr update | summary/full persisted | repeated same value no change | enum strict | toggle back |
| Exact render | derived read | revision/digest same | safe repeat | backend projection versioned | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** `SBW10` exact projection, `SBW11` content hydration, current Tiptap JSON/Markdown conventions.

| Predecessor field | Embed attr/behavior | Transformation | Proof |
|---|---|---|---|
| accepted/threat binding provider | `provider` | exact `dungeonmind` | insert test |
| statblock ID | `statblockId` / `statblock` | exact copy | round-trip |
| revision ID | `revisionId` / `revision` | exact copy | round-trip |
| Threat ID | optional `threatId` / `threat` | exact graph ID | context test |
| view action | `view` | enum | command test |
| Threat Sheet/exact read response | renderer input/state | reuse existing component/API | integration test |
| content-read Markdown | parser input | canonical directive recognized | fresh reload test |
| parser diagnostics | Plan load warnings/unresolved block | retain safe message/line | invalid fixture |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Directive exact round-trip | parser/serializer | focused tests | semantic attrs equal/canonical order |
| Invalid attrs never request backend | parser/NodeView | negative tests with call counter | zero calls |
| Insert uses exact IDs | Threat Sheet/workbench→editor command | integration test | node attrs match source |
| Exact revision render/no latest | NodeView/API fake | component test | exact call; newer fixture ignored |
| Missing/unavailable retains locator | NodeView | tests | attrs/actions visible |
| Save→fresh reload | writer/content hydration/Plan | integration test | same node/revision renders |
| Shared renderer/projection reused | diff/component | test | no duplicate mechanics renderer |
| Mixed document content preserved | parser/serializer | fixture | callouts/references/statblock survive |

Required commands:

```bash
cd apps/live-control-ui && npm test -- --run src/tiptap/markdown/statblockEmbedMarkdown.test.ts src/tiptap/extensions/StatblockEmbedNode.test.tsx <Plan canvas/parser/Threat Sheet tests>
cd apps/live-control-ui && npm run build
uv run pytest <workspace document content/write tests if integration touched> -q
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Insert an exact published Threat/statblock into an existing Plan document, save, clear local state/use a fresh browser, reload, and inspect the same revision. Simulate Server unavailable and a newer revision; prove the locator remains and does not move.

## §8 Required handback

Include canonical directive grammar, parser/serializer fixtures, base/head, actual paths, commands/results/provenance, save→fresh-reload and unavailable/newer evidence, baseline failures/waivers, and confirmation that no append/upgrade/combat/media/generic embed capability ships.

## §9 Acceptance rubric

- [ ] Canonical directive and Tiptap attrs are strict and documented.
- [ ] Markdown↔Tiptap round-trip preserves exact identity semantically.
- [ ] Insert actions pass exact IDs from trusted projections.
- [ ] Node resolves through Buddy backend and shared renderer.
- [ ] Missing/unavailable/newer states retain locator and never rebind.
- [ ] Fresh committed-document reload reproduces the block.
- [ ] Mixed existing Markdown constructs remain intact.
- [ ] No generic embed framework, mechanics revision, graph update, combat, or media workflow ships.

## §10 Reviewer protocol

Review serialized identity before visuals. Fuzz invalid attrs/body/escaping, verify zero backend calls, then test fresh reload and newer revision. Search for latest, URL/path attrs, copied JSON/Markdown mechanics, direct Server call, and duplicate renderer.

## §11 Re-review protocol

Rerun parser canonicalization/fuzz cases, mixed document, insertion, exact render, missing/unavailable, context mismatch, fresh reload, and newer-revision tests after every fix.

## Stop conditions

Stop if:

- current Markdown parser cannot support a deterministic block directive without broad redesign;
- Tiptap schema registration would corrupt existing content;
- committed document hydration is not available/stable;
- exact projection requires direct browser Server access;
- insert action needs a second editor/projection state container;
- portable export or generic embeds become required for usefulness;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW10–11`.
- [ ] Freeze grammar/escaping/invalid policy.
- [ ] Capture mixed-document and fresh-reload fixtures.
- [ ] Confirm `SBW13+` remain false.
