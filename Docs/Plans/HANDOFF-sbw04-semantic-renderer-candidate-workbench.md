# HANDOFF — SBW04 Shared semantic statblock renderer and read-only candidate workbench

**Created:** 2026-07-22  
**Status:** IMPLEMENTING — `feat/sbw04-semantic-renderer`; base includes Milestone B bite-schedule docs.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw04-semantic-renderer-candidate-workbench.md`  
**Workstream:** `SBW04`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch exactly one user-visible capability: a real typed candidate is reviewable through one reusable semantic renderer. Do not add mechanical editing, validation submission, acceptance, graph publication, Markdown embedding, combat insertion, or image generation.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Render typed statblock definitions semantically | Yes | No | Yes | Include |
| Load a generated candidate into the existing workbench | No; required host proof | No | Yes | Include under same invariant |
| Delete mock/corpus-first normal presentation | No; required replacement demolition | No | Yes | Include |
| Edit candidate mechanics | Yes | Yes | Yes | Successor `SBW05` |
| Open accepted graph-backed Threat Sheet | Yes | No | Yes | Successor `SBW10` |
| Embed in Tiptap/Markdown | Yes | Yes | Yes | Successor `SBW12` |

**Selected capability:** the GM can open and inspect a real `GeneratedStatblockCandidateV1` in the existing Statblock Workbench through a renderer reusable by later surfaces.

**Why included rows share one invariant:** the workbench is the first host proof of the renderer; deleting the mock/corpus-first presentation is required so the normal user path has one truthful source of mechanics.

## §1 Mission

A GM can review a real typed statblock candidate in the Plan statblock workflow so generated mechanics are understandable before any edit or persistence action.

**Invariant**

```text
Every displayed mechanical field is derived from the structured candidate definition and validation/provenance receipts; canonical Markdown and mock output are never mechanics sources.
```

**Mission falsification test**

```text
This is not one slice if it must also submit edited definitions, call preview validation, save mechanics, publish graph truth, embed documents, mutate combat, or generate/select media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §§6.2, 9; tracker `SBW04`; Plan Surface Toolbox one-registry/one-container rule |
| Repository rules | `AGENTS.md`; external-agent handoff/review rules |
| Base revision | Merged SHA containing `SBW01–03` |
| Predecessor contract | ThreatDraft candidate read response using generated statblock v1 types |
| Exact input consumed | Exact candidate ID/ref and typed `GeneratedStatblockCandidateV1` payload |
| Named successor | `SBW05` complete-definition editor and validation |
| What remains false | Candidate cannot be edited, accepted, published, embedded, or added to combat |
| Explicit non-goals | New design system, second renderer, local mechanics schema, Markdown parsing, persistence, graph, combat, images |

Read in order:

1. active integration design and tracker
2. Plan Surface Toolbox and current projection registry/container contracts
3. merged `SBW03` candidate API/types/tests
4. `StatblockWorkbenchModule.tsx` and its tests
5. `StatblockViewModule.tsx` only for predecessor styling/behavior inventory
6. generated DungeonMind v1 candidate/definition types and fixtures

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Same invariant? | Owner |
|---|---|---|---:|---|
| Open workbench with candidate ref | Workbench runs mock command/transitional artifacts | Load exact candidate through Buddy API | Yes | module + API |
| Candidate loading | Mock/local flow | Honest loading state retaining draft/candidate context | Yes | module |
| Exact success | Markdown/transitional presentation | Structured semantic statblock + receipts | Yes | renderer/module |
| Candidate missing | Generic failure | Honest not-found state; no fallback to another candidate | Yes | module |
| Candidate expired | Not modeled visually | Explicit expired state retaining locator and regenerate affordance placeholder only | Yes | module |
| Integration unavailable | Mock may appear usable | Honest unavailable state; no mock fallback | Yes | module |
| Contract/unsupported element | Potentially dropped | Visible unsupported/human-adjudicated representation | Yes | renderer |
| Reload | Transitional state | Same candidate ID renders equivalent semantic content | Yes | API/module |
| Normal mock generate path | Active | Removed/disabled from normal product route | Yes | module/routes as needed |
| Corpus promotion/retrieval controls | Active normal flow | Removed from normal candidate-review UI | Yes | module |

## §4 Files in scope — allowlist

Re-anchor component paths after predecessors merge.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/statblocks/render/StatblockRenderer.tsx` | Shared semantic renderer root |
| Create | `apps/live-control-ui/src/statblocks/render/StatblockRenderer.css` | Token-driven styling only |
| Create | `apps/live-control-ui/src/statblocks/render/statblockViewModel.ts` | Pure derived presentation helpers; no canonical schema |
| Create | `apps/live-control-ui/src/statblocks/render/StatblockRenderer.test.tsx` | Fixture coverage across definition shapes |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | Load/render real candidate and truthful states |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | Workflow/state proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | Candidate read view if predecessor did not already land it |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Candidate read call if needed |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | API proof if touched |
| Modify/Delete | Narrow legacy workbench UI helper files discovered under the same module | Remove mock/corpus-first normal presentation only |

### Bounded discovery exception

```text
Directory: apps/live-control-ui/src/surface/ and apps/live-control-ui/src/statblocks/
Maximum additional paths: 4
Allowed path kinds: projection registry wiring, existing shared tokens, fixture helper, legacy mock-only child component deletion
Decision rule: path is necessary to mount the same workbench projection or delete the directly replaced presentation
Required report: name remaining consumer before retaining any replaced mock/corpus component
```

Backend paths are out of scope unless one narrow read-response defect in `SBW03` prevents the UI from consuming its promised contract. Stop rather than silently widening.

## §5 Explicitly out of scope

| Capability/path | Why excluded |
|---|---|
| Candidate editor/form controls | `SBW05` |
| `statblock-definitions:validate` calls | `SBW05` |
| revise/regenerate | `SBW06` |
| create/append immutable revision | `SBW07` |
| graph authoring or binding | `SBW08–09` |
| accepted Threat Sheet resolver | `SBW10` |
| Tiptap extension/Markdown directive | `SBW12` |
| combat state | `SBW15` |
| image generation/selection | later media slices |
| broad `StatblockViewModule` replacement | only delete an exact predecessor consumer named by this PR |

## §6 Implementation contract

```text
Input:
  GeneratedStatblockCandidateV1 plus optional ThreatDraft summary/context

Output:
  semantic React projection in summary/full review mode with validation,
  provenance, warning, and unsupported-element disclosure

Invariant:
  structured definition and receipts are the only sources of displayed mechanics

Failure behavior:
  missing/expired/unavailable -> stable honest state retaining exact locator
  malformed candidate -> fail closed; do not partially reinterpret arbitrary JSON
  unknown future rule element -> visible unsupported block, not silent omission
  missing optional section -> omit section without inventing content

Replay / idempotency:
  same typed candidate -> semantically equivalent render
  reload -> read exact candidate ID; never choose latest
  changed candidate ID -> explicit new review source

Trust boundary:
  Verifies: generated DTO shape, known enum/element rendering, exact locator
  Records/displays without proving: game balance, provider explanation, prose quality
  Rejects: Markdown as mechanics, HTML from provider, arbitrary rich text execution
```

### Renderer design decisions

- One renderer family supports `review`, later `summary`, `full`, `embed`, and `combat-drilldown` host policies. This PR implements only what candidate review needs but must not hard-code the host into each section.
- Preserve definition order for traits/actions/elements unless the contract specifies a canonical order.
- `rules_text` is displayed as text; do not parse it into executable automation.
- `human_adjudicated` elements receive a visible label and explanatory presentation.
- Validation errors and warnings remain distinct. A warning is not visually reported as an error.
- Provider provenance/receipts live in a secondary disclosure region; mechanics remain primary.
- Styling consumes existing surface tokens. No independent palette or page-specific fixed colors.
- Accessibility: semantic headings, table/list structure where appropriate, keyboard-readable disclosure controls, no information conveyed only by color.

### §6A State and fallback matrix

| Path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Expired | Retry |
|---|---|---|---|---|---|---|---|
| Candidate workbench | skeleton with candidate identity | render exact candidate | not-found state | unavailable state | contract-error state | expired state | explicit retry/read; no mock fallback |
| Renderer section | N/A | render typed section | optional section omitted | N/A | visible unsupported/fail component boundary | N/A | same input stable |
| Receipts | deferred disclosure | exact typed data | optional absent | N/A | safe diagnostic | N/A | stable |

No fallback to sample candidate, legacy draft artifact, corpus path, Markdown, or “latest generated statblock.”

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Candidate | exact candidate ID from draft ref/route | none | No | source badge/diagnostic retains ID |
| Draft | exact draft ID/version for context only | none | No | never mechanics source |
| Statblock name | display field | duplicates allowed | No | never selects data |
| Element key | preserve contract key for anchors/issues where present | duplicate key = contract error or explicit list handling | No | used for validation mapping later |
| Expired candidate | exact ID retained | no rebinding | No | regenerate later creates new candidate |

### §6C Persistence and replay matrix

Not applicable to new durable data — this PR reads the `SBW03` candidate contract and changes presentation only. Existing local projection state may remember the active locator, but it must not persist candidate bodies or create a new canonical cache.

### §6D Predecessor-to-consumer mapping

**Grounding source:** generated `GeneratedStatblockCandidateV1` and fixture set from `SBW03`.

The implementation PR must complete exact field mappings. Required coverage:

| Candidate/definition area | Consumer region | Transformation | Proof fixture |
|---|---|---|---|
| identity/name/type/size/alignment/CR | header/identity | display normalization only | simple fixture |
| AC/HP/speed | defense/vitality/movement | preserve values/formulas | simple fixture |
| ability scores/saves/skills | ability/proficiency tables | derived modifiers only if contract explicitly allows deterministic derivation | simple fixture |
| senses/languages/communication | senses/communication | list formatting | simple fixture |
| traits/actions/reactions | rule element sections | ordered semantic cards | complex fixture |
| spellcasting | typed spellcasting section | no prose-only flattening | spellcaster fixture |
| legendary/lair/mythic/phases | distinct sections | preserve keys/limits | legendary/phased fixture |
| human-adjudicated | visible warning/label | no automation claim | adjudicated fixture |
| validation receipt | issue rail | error/warning distinction | invalid/warning fixture |
| generation receipt/provenance | disclosure | safe bounded fields only | fixture |
| asset brief/assets | placeholder/media disclosure only; do not bind | typed display if already present | asset fixture |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Structured field coverage | renderer component | focused renderer tests | all fixture sections visible |
| Unknown/human-adjudicated not dropped | renderer | fixture tests | visible disclosure |
| Exact candidate load/reload | workbench integration | module tests with API fake | same ID/content |
| Missing/expired/unavailable honesty | module | state tests | no mock/corpus fallback |
| Normal mock/corpus UI removed | module/diff | test + diff/search | predecessor controls absent |
| Shared host-neutral renderer | component API/diff | renderer mounted by workbench without Plan-specific data imports | reusable props |
| Accessibility/build | UI | tests + build | semantic queries pass/build green |

Required commands:

```bash
cd apps/live-control-ui && npm test -- --run src/statblocks/render/StatblockRenderer.test.tsx src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use the existing Plan statblock tool projection. Open a real candidate, inspect simple and complex sections, reload, then simulate Server unavailable/expired candidate. Capture screenshots or a short recording as manual evidence; do not build a new route.

## §8 Required handback

Include base/head, actual paths, fixture matrix, commands/results/provenance, live proof, demolition result, named remaining consumers of any retained legacy file, baseline failures/waivers, and confirmation that no edit/save/graph/combat/media capability shipped.

## §9 Acceptance rubric

- [ ] One reusable semantic renderer powers real candidate review.
- [ ] Every displayed mechanic comes from the structured definition.
- [ ] Fixture coverage includes simple, spellcasting, legendary/lair, phased, and human-adjudicated shapes.
- [ ] Missing/expired/unavailable states retain exact identity and use no mock fallback.
- [ ] Normal mock/corpus-first generation presentation is removed.
- [ ] Corpus promotion/retrieval controls are absent from normal candidate review.
- [ ] No editor, validation submit, acceptance, graph, embed, combat, or media generation ships.
- [ ] Styling follows existing tokens and accessibility requirements.

## §10 Reviewer protocol

Begin by tracing each rendered section back to generated contract fields. Search for Markdown parsers, dangerously-set HTML, duplicate mechanics interfaces, display-name lookup, sample/mock fallback, and Plan-specific coupling inside renderer components.

## §11 Re-review protocol

After fixes, rerun the full fixture matrix and all failure-state tests, not only the corrected component. Recheck demolition and that unknown fields are not silently discarded.

## Stop conditions

Stop if:

- the generated candidate types cannot represent a fixture required by the Server contract;
- one host requires a second renderer architecture;
- displaying mechanics requires parsing canonical Markdown;
- the current candidate read contract does not provide enough typed data for reload;
- deleting the mock path breaks a named active consumer that cannot migrate in this slice;
- a backend or unrelated surface path outside the allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW03`.
- [ ] Capture exact fixture inventory.
- [ ] Name demolition targets and remaining consumers.
- [ ] Confirm `SBW05+` remain false.
