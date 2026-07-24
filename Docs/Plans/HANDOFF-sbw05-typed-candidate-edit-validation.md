# HANDOFF — SBW05 Complete-definition candidate editing and preview validation

**Created:** 2026-07-22  
**Updated:** 2026-07-23 — SBW05b `#402` merged; SBW05c host+validate + doc-sync in #404  
**Status:** IN PROGRESS — `SBW05a` MERGED `#398`; `SBW05b` MERGED `#402` (`79e22f68`); **`SBW05c` `#404`** per §13; next `SBW07-contract`.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw05-typed-candidate-edit-validation.md`  
**Workstream:** `SBW05`  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Repository tip (not an SBW claim):** see `main` at PR open (includes unrelated work)  
**Last SBW integration on `main` before #404:** `#402` / `d4587f1f` — SBW05b editor library  
**This PR (`#404`):** SBW05c workbench host + preview validate + doc-sync  
**Verification debt (predecessor):** SBW04 `#397` real-candidate live proof remains unchecked — do not treat as closed by this workstream. **SBW05c §7 manual live workbench walkthrough is verification debt** (not waived by automated tests; automated coverage is necessary but not equivalent evidence).

> Dispatch one capability across three PRs: edit a complete typed candidate working copy and obtain authoritative preview validation. Do not save mechanics, revise with a model, publish graph truth, or add media/combat behavior.

## Bite schedule

| Bite | Status | PR mission | Allowlist focus | Still false |
|---|---|---|---|---|
| `SBW05a` | MERGED `#398` | Validate transport: client method + Buddy route + digest association tests | Backend client/service/route/tests only | Editor UI, workbench, save, revise |
| `SBW05b` | MERGED `#402` | Pure editor library + Output→Input initializer + local fingerprint/state machine + field/control matrix + visible protected preservation fallback + unit tests | `apps/live-control-ui/src/statblocks/editor/**` + unit tests **only** | Backend, `liveApi`, workbench host, save, acceptance, durable editor schema, Server `definition_digest` recreation |
| `SBW05c` | **#404** — see §13 | Host proven editor; call merged SBW05a validate route; reject stale responses; preserve edits on dependency failure; demonstrate edit→validate→edit→stale | Workbench module + `liveApi` wiring + preview issue partition | Accept/save path, revise, graph |

Each bite uses this handoff’s §6 contract as amended by §12/§13; do not expand that bite’s allowlist mid-review.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Edit a complete `StatblockDefinitionV1_Input` working copy | Yes | No if session-only; yes if persisted | Yes | Include |
| Submit preview validation through Buddy backend | No; required gate for meaningful editing | Yes API | Yes | Include under same invariant |
| Persist editor working copy across process restart | Yes | Yes | Potentially | Exclude unless predecessor already provides a suitable draft subrecord; otherwise successor |
| Model-assisted revise/regenerate | Yes | Yes | Yes | Successor `SBW06` |
| Save immutable revision | Yes | Yes | Yes | Successor `SBW07` |
| Compare accepted revisions | Yes | No | Yes | Later successor |

**Selected capability:** the GM can change a complete typed candidate working copy and see authoritative validation issues tied to the submitted definition.

**Why included rows share one invariant:** editing without authoritative validation would create an unsafe local schema fork; validation exists solely to establish whether the exact current working copy is eligible for later acceptance.

## §1 Mission

A GM can edit a complete typed statblock candidate and validate the exact working copy through DungeonMindServer so invalid mechanics are visible and cannot be mistaken for save-ready output.

**Invariant**

```text
The editor always owns one complete contract-typed definition; validation applies to its exact digest, and any subsequent edit invalidates that validation state.
```

**Mission falsification test**

```text
This is not one slice if it must also generate a revised candidate, create/append a statblock revision, update graph bindings, persist document embeds, or mutate combat/media.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §6.3; tracker `SBW05`; DungeonMindServer v1 validation contract |
| Repository rules | `AGENTS.md`; external-agent PR loop rules/template |
| Base revision | Actual merged SHA containing `SBW01–04` + `SBW05a` (last SBW integration `#398` / `58db1fc5`; repository tip may be ahead with unrelated work) |
| Predecessor contract | Shared semantic renderer and exact candidate read payload (`SBW04`); authoritative validate transport (`SBW05a`) |
| Exact input consumed | Complete candidate definition copied into local editor state; exact candidate/draft locators |
| Named successor | `SBW07` immutable mechanics save (before revise), then `SBW06` revise/regenerate |
| What remains false | No accepted mechanics exist; validation is advisory eligibility state only |
| Explicit non-goals | Partial patch API, local validator, model revision, persistence save, graph, embed, combat, media |

Read in order:

1. active integration design and tracker
2. merged `SBW04` renderer/workbench contract
3. current generated `StatblockDefinitionV1_Input`, validation request/response, and issue-path types
4. merged `SBW01` adapter error taxonomy
5. current workbench component tests and candidate fixtures

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Enter edit mode | Read-only candidate | Explicit editable working copy initialized from exact candidate | Yes | workbench/editor |
| Change supported scalar/list field | No typed editor | Update complete working definition; mark dirty/unvalidated | Yes | editor state |
| Change rule element text/fields | No typed editor | Preserve element key/type/order and update complete definition | Yes | editor state |
| Validate | No real preview validation | Buddy backend submits exact definition to Server | Yes | route/service/UI |
| Validation errors | Not actionable | Field/global issues visible; save-ready false | Yes | issue mapper/UI |
| Validation warnings | Potentially conflated | Visible but distinct; eligibility follows Server semantics | Yes | UI |
| Edit after validation | Undefined | Prior receipt becomes stale immediately | Yes | editor state |
| Timeout/unavailable | No real dependency | Working copy retained; typed retry state | Yes | UI/service |
| Candidate reload/navigation | Read-only candidate can reload | Unsaved editor state behavior is explicitly session-only unless persisted by predecessor | Yes | module |
| Unknown future element | Renderer can show unsupported | **Out of SBW05b scope** as future-schema inventiveness; typed-but-unhandled *current* structures must stay in the working copy and appear as a visible read-only/protected block | Yes | visible protected preservation fallback |

## §4 Files in scope — allowlist

Re-anchor exact paths after `SBW04`.

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live-control-ui/src/statblocks/editor/StatblockDefinitionEditor.tsx` | Complete-definition editing surface |
| Create | `apps/live-control-ui/src/statblocks/editor/statblockEditorState.ts` | Dirty/digest/validation state transitions |
| Create | `apps/live-control-ui/src/statblocks/editor/statblockValidationIssues.ts` | Typed field-path/global issue mapping |
| Create | `apps/live-control-ui/src/statblocks/editor/StatblockDefinitionEditor.test.tsx` | Editing and preservation proof |
| Create | `apps/live-control-ui/src/statblocks/editor/statblockEditorState.test.ts` | digest/staleness state proof |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | Review/edit/validate mode integration |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | workflow/error/retry proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | validation route view types if not generated directly |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | validation request function |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | request/error mapping proof |
| Create | `apps/live_control_server/services/statblock_definition_validation.py` | Thin adapter orchestration; no local mechanics validation |
| Create/Modify | `apps/live_control_server/routes/statblock_candidates.py` or narrow validation route | Browser-safe validation endpoint |
| Create | `tests/test_statblock_definition_validation.py` | exact payload/error mapping proof |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package; generated contract package; apps/live-control-ui/src/statblocks/
Maximum additional paths: 4
Allowed path kinds: adapter method extension, generated type import/export, one editor fixture helper, one token/style file
Decision rule: required to preserve the complete generated definition or authoritative validation issue shape
Required report: explain why no handwritten canonical mechanics type was introduced
```

## §5 Explicitly out of scope

| Capability/path | Why excluded |
|---|---|
| Persisting editor working copy as a new durable schema | separate capability unless an existing draft field can hold it without schema expansion |
| model revise/regenerate | `SBW06` |
| create/append statblock resource/revision | `SBW07` |
| accept button that commits mechanics | `SBW07` |
| World Graph files | `SBW08–09` |
| accepted Threat Sheet | `SBW10` |
| Markdown/Tiptap embed | `SBW12` |
| combat/media | later slices |
| local challenge-rating/balance validator | Server owns validation |
| generic JSON Patch endpoint | would create ambiguous partial mechanics semantics |

## §6 Implementation contract

```text
Input:
  exact candidate definition copied to a complete StatblockDefinitionV1_Input working value
  candidate_id, draft_id/version context

Output:
  editable complete definition + local dirty state + authoritative validation receipt
  bound to a deterministic digest of the exact submitted definition

Invariant:
  validation eligibility is bound only after proven association with the current working copy;
  every edit/normalization/undo/redo clears eligibility unless that association still holds
  (SBW05b: local fingerprint/state revision only; SBW05c+: Server receipt digest from SBW05a)
Failure behavior:
  local impossible state/contract mismatch -> fail closed, preserve source candidate
  Server validation errors -> successful validation response with error issues; not a transport failure
  auth/timeout/unavailable/rate limit -> typed failure; retain working copy and prior receipt as stale/not-current
  malformed issue path -> show global issue; do not drop it
  unknown element/control -> preserve through typed structured fallback or read-only protected block; never silently delete

Replay / idempotency:
  same definition digest -> repeated validation may replace receipt with equivalent newer receipt
  changed digest -> prior receipt cannot apply
  retry after timeout -> safe; no persistence side effect
  duplicate validation response -> latest response for same digest may be retained

Trust boundary:
  Verifies: complete generated type, deterministic digest, issue paths, Server receipt association
  Records without proving: balance, prose quality, GM intent
  Rejects: partial patch bags, extra unknown top-level fields, provider HTML, local acceptance without Server receipt
```

### Editor decisions

- The working copy is complete, never a sparse patch.
- Dedicated controls may cover the first-release common fields, but unhandled **current** generated-contract structures must remain in the working copy **and** appear to the GM as at least a **visible structured read-only/protected block** (key/type/order + honest protected disclosure; SBW04 visible-unsupported spirit). Typed-constrained editing of those regions is optional. Structured fallback is **not** silent retention, arbitrary future-schema support, or inventing unknown keys.
- Element identity/order must be preserved. Editing text cannot regenerate keys.
- Numeric controls enforce only contract-level shape/ranges locally; authoritative semantic validation remains Server-owned.
- `rules_text` is edited as text and always clears validation eligibility.
- Edit detection uses a **local working-copy fingerprint / state revision only**. Do **not** recreate or claim equality with the Server canonical `definition_digest`. Server digest association is proven only after a successful SBW05a validate response (SBW05c+) for the exact submitted body.
- Any change, normalization, undo, or redo clears validation eligibility unless exact association with the current working copy has been proven (same local fingerprint/state revision that was validated).
- The UI distinguishes: `clean_unvalidated`, `dirty_unvalidated`, `validating`, `validated` (Server `valid`), `validated_with_warnings` (Server `warnings`), `validated_with_errors` (Server `invalid`), `validation_unavailable`. Receipt-bearing states are only `validated` | `validated_with_warnings` | `validated_with_errors`; pending `validating` and `validation_unavailable` never associate a revision.
- No save/accept eligibility claim exists beyond a derived `validation_has_no_errors` state for the exact currently associated receipt.
- The working copy is **session-only and unsaved**. No `localStorage`, IndexedDB, or durable editor schema in SBW05b/c.
### §6A State and fallback matrix

| Path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Initialize editor | copy exact candidate | complete working definition | candidate missing handled by SBW04 | N/A | fail closed/read-only source | candidate expired after load does not erase working copy | reload source explicitly |
| Edit | N/A | dirty/unvalidated | N/A | N/A | keep typed-but-unhandled current structures in working copy + visible protected block | prior receipt stale | undo may restore local fingerprint; receipt reuse only if exact association is proven |
| Validate | validating state | receipt bound to digest | N/A | retain working copy; unavailable | fail closed/global issue | response for old digest discarded | safe |
| Issue display | N/A | field/global issues | no issues | N/A | malformed path becomes global | stale receipt labeled/not used | revalidate |

No fallback to local validation, previous candidate receipt, Markdown parsing, or another revision.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Candidate | exact candidate ID for source attribution | none | No | editing does not mutate Server candidate |
| Definition | local working-copy fingerprint/state revision for edit detection; Server `definition_digest` only after proven SBW05a association | mismatch means stale | No | do not claim local fingerprint equals Server digest |
| Element | exact contract element key where present | duplicate/missing key handled as validation/global error | No name matching | preserve order/identity |
| Field issue | exact typed path segments | unmappable path → global issue | No silent nearest-field match | issue retained |
| Name | editable display/mechanics field | duplicates irrelevant | No | never identity key |

### §6C Persistence and replay matrix

By default:

```text
Not applicable to new durable editor state — the working copy is session-local and the UI must say unsaved.
```

If the merged predecessor already provides a versioned draft subrecord expressly intended for complete working definitions, the dispatching agent must amend this handoff before implementation with exact save/reload/version semantics. Do not invent that persistence during the PR.

Validation requests are side-effect-free and safely replayable by definition digest.

### §6D Predecessor-to-consumer mapping

**Grounding source:** generated `StatblockDefinitionV1_Input`, Server validation request/response, and `ValidationIssueV1` fixtures.

The implementation PR must complete a real field/control matrix. Required categories:

| Contract area | Editor behavior | Preservation rule | Validation proof |
|---|---|---|---|
| identity/classification | dedicated fields | exact typed values | edit + request fixture |
| AC/HP/speed | dedicated structured controls | formulas/notes retained | field error mapping |
| abilities/saves/skills | tables/rows | unknown proficiency entries retained | round-trip test |
| senses/languages | lists | order/values retained | request snapshot |
| traits/actions/reactions | typed repeated element editor | keys/types/order retained | element-path issue test |
| spellcasting | typed nested editor or visible protected structured fallback | no flattening to prose; must remain visible | spellcaster round-trip + UI disclosure |
| legendary/lair/phases | typed nested editor or visible protected fallback | all limits/keys retained and disclosed | complex fixture + UI disclosure |
| human-adjudicated | editable text/typed metadata with warning | never converted to automation | fixture |
| validation issue path | field/global issue | exact path mapping; malformed retained globally | issue tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Complete definition preserved | editor state/component | fixture edit/serialize tests | untouched complex fields identical |
| Edit invalidates receipt | state machine | focused unit tests | validation status stale/unvalidated |
| Exact request/digest mapping | UI API + backend service | snapshot/route tests | submitted payload digest matches receipt association |
| Error/warning distinction | issue mapper/component | fixtures | correct state and labels |
| Unknown issue/element retained | mapper/editor | malformed/future fixture | visible global/protected representation |
| Downstream failure retains working copy | workbench integration | timeout/auth tests | edits remain |
| No local schema fork | diff/contract test | generated type imports + fingerprint | no duplicate canonical interface |

Required commands:

```bash
uv run pytest tests/test_statblock_definition_validation.py -q
cd apps/live-control-ui && npm test -- --run src/statblocks/editor/StatblockDefinitionEditor.test.tsx src/statblocks/editor/statblockEditorState.test.ts src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Use the existing Plan statblock workbench. Edit one scalar mechanic and one rule element, validate, observe an issue/warning, fix it, validate again, then make another edit and show the receipt becomes stale. Simulate timeout and prove edits remain. Do not add persistence or a new route for proof.

## §8 Required handback

Include field/control coverage matrix, generated type/fixture provenance, base/head, actual paths, test/build results, live proof, unsaved-state disclosure, baseline failures/waivers, and confirmation that save/revise/graph/embed/combat/media remain false.

## §9 Acceptance rubric

- [ ] Editor always holds a complete contract-typed definition.
- [ ] Complex unsupported-by-dedicated-control fields are preserved.
- [ ] Validation request contains the exact current definition.
- [ ] Receipt is bound to a tested digest and invalidated by edits.
- [ ] Errors and warnings remain distinct.
- [ ] Unmappable issues are shown globally, never dropped.
- [ ] Downstream failure retains edits.
- [ ] No partial patch API, local validator, mechanics save, model revision, graph, embed, combat, or media ships.

## §10 Reviewer protocol

Start with round-trip preservation on the most complex fixture. Then audit digest normalization, stale-response races, issue mapping, and generated-type ownership. Search for `Partial<>`, arbitrary record bags, local acceptance flags, and dropped unknown elements.

## §11 Re-review protocol

After each fix, rerun complex round-trip, edit-after-validation, stale-response, malformed-path, and timeout tests. Verify the fix does not introduce durable editor storage or acceptance semantics.

## §12 SBW05b dispatch contract (normative — implementation agent)

`SBW05b` is a **pure editor library + unit tests** bite. Hand this section to the implementation agent as the closed mission.

### Mission

Ship a reusable editor library that initializes a complete editable `StatblockDefinitionV1_Input` from a generated candidate `StatblockDefinitionV1_Output`, tracks local edit eligibility with a working-copy fingerprint/state revision, and keeps every current generated-contract structure that lacks a dedicated control in the working copy with **visible** read-only/protected disclosure.

### Allowlist (deny everything else)

```text
apps/live-control-ui/src/statblocks/editor/**
+ unit tests colocated under that tree (or explicitly named *.test.ts(x) for those modules)
```

**Explicitly out of SBW05b scope (even if listed in the parent §4 allowlist):**

- any backend / `apps/live_control_server/**`
- `apps/live-control-ui/src/api/liveApi.ts` and related API tests
- `StatblockWorkbenchModule.tsx` / workbench host wiring
- save, accept, revise, graph, localStorage, IndexedDB, durable editor schema
- recreating or claiming equality with Server canonical `definition_digest`

### Required initializer

- Provide an **explicit, tested** function mapping generated candidate `StatblockDefinitionV1_Output` → complete `StatblockDefinitionV1_Input` that constructs/validates a complete input without claiming type identity by assertion alone.
- **Forbid** unchecked Output→Input bypass: no `as StatblockDefinitionV1_Input`, no double-assertion through `unknown`/`any`, no sparse patch treated as a complete input.
- **Allow** ordinary TypeScript narrowing and literal helpers elsewhere in the editor library (`as const`, discriminated-union narrowing, exhaustiveness checks). The ban targets the Output→Input boundary, not every assertion in the file.
- Do not invent a second handwritten mechanics schema to satisfy the scoped ban; if a second schema is required, stop (parent stop conditions).
- Source candidate object remains **immutable**; the editor mutates only its working copy.
- Preserve element **keys**, **types**, **ordering**, and every current generated-contract structure that lacks a dedicated control.

### Structured fallback (closed definition)

Structured fallback for typed-but-unhandled structures in the **current** generated OpenAPI contract means:

1. **Must** keep the structure in the complete working copy (no silent drop).
2. **Must** surface it to the GM as at least a **visible structured read-only/protected block** (key/type/order + honest “not editable via dedicated control” / protected disclosure). Follow SBW04’s visible-unsupported pattern in spirit; do not invent a second schema.
3. **May** offer typed-constrained editing of that region; editing is optional for SBW05b merge.

It is **not**:

- silent retention without UI disclosure;
- arbitrary future-schema support;
- a license to invent unknown keys;
- flattening complex regions into prose.

### Local fingerprint vs Server digest

- Use a local working-copy fingerprint / state revision **only** for edit detection and eligibility clearing.
- Do **not** recreate or claim equality with the Server canonical `definition_digest`.
- Any edit, normalization, undo, or redo clears validation eligibility unless exact association with the current working copy has already been proven (SBW05c will prove association via SBW05a responses; SBW05b only needs the clear-on-edit state machine).

### Session-only disclosure

The working copy is **session-only and unsaved**. UI copy and tests must state this. No durable persistence path.

### Merge proof (required tests)

Complex round-trips covering at least:

- spellcasting
- legendary / lair data
- phases
- human-adjudicated mechanics
- nested effects
- **untouched-field equality** after edits elsewhere

Also prove: initializer completeness; source candidate immutability; edit/normalization/undo/redo clears eligibility; session-only (no storage writes).

For at least one complex fixture region that lacks a dedicated control: the structure remains in the working copy **and** a queryable protected/read-only block is present in the rendered editor UI (visible disclosure, not data-only preservation).

### Verification commands (SBW05b only)

```bash
cd apps/live-control-ui && npm test -- --run src/statblocks/editor/
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

Report `git diff --stat` filtered to the editor allowlist only.

## §13 SBW05c host contract (normative — #404)

### Mission

Host the proven SBW05b `StatblockDefinitionEditor` in the Plan workbench; submit the **exact current** `workingCopy` (`StatblockDefinitionV1_Input`) to the merged SBW05a Buddy validate route; associate a receipt only when the response matches the in-flight local `stateRevision`; preserve the working copy on transport/dependency failure; prove **edit → validate → edit → stale**. No accept/save.

### Allowlist

- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/liveApi.test.ts`
- `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx`
- `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx`
- `apps/live-control-ui/src/statblocks/editor/statblockValidationIssues.ts` (+ test)
- Docs: this handoff, PR-TRACKER, ROADMAP (status + this §13)

### UI composition

- Modes: `review` | `edit` (default **`edit`** on successful candidate load).
- Review = immutable `StatblockRenderer` (generation receipt).
- Edit = controlled `StatblockDefinitionEditor` + workbench **Validate working copy** control + preview validation panel.
- Editor state owned by the workbench; recreated via `createEditorStateFromOutput` on each successful load/reload.
- Copy must say preview validation / unsaved — no Accept, Save, or `mechanics_saved`.

### Validate orchestration

```text
onValidate:
  1. capture editorEpoch + beginValidationAttempt(editorState)
  2. capture requestedRevision = editorState.stateRevision
  3. POST validateStatblockDefinition({ definition: editorState.workingCopy })
  4. if requestId/epoch ownership is stale → discard all effects (no receipt, preview, failure, unavailable, or pending mutation owned by the old request)
  5. if ownership holds but stateRevision !== requestedRevision → discard effects; clear pending only
  6. if outcome === failure or throw (and ownership+revision current) → markValidationUnavailable; keep workingCopy
  7. if outcome === success (and ownership+revision current):
       require validation_receipt and matching top-level definition_digest
       map receipt.status:
         valid → validated
         warnings → validated_with_warnings
         invalid → validated_with_errors
       markValidationAssociated(state, mapped)
       store preview receipt + digest for display
```

- Validation ownership is `(requestId, editorEpoch, stateRevision)`. Loading/reloading a candidate immediately bumps `editorEpoch`, orphans the prior request id, and clears pending validation.
- Monotonic validate request id so overlapping validates never apply an older response after a newer one started.
- Never compare local fingerprint to Server `definition_digest` for equality/eligibility.
- Server `invalid` is a success outcome with receipt association — not transport failure.
- Pending `validating` and `validation_unavailable` never associate a revision.
- Issue severities `info` | `warning` | `error` are preserved exactly (info is not rendered as warning).

### Issue mapping

`statblockValidationIssues.ts` partitions issues into field vs global: non-empty `field_path` → field; empty/whitespace → global (never dropped, never nearest-field guess). Errors and warnings remain distinct by severity.

### Still false

Accept/save path, revise (`SBW06`), graph, durable editor storage, backend route changes.

### Merge proof

Workbench tests must prove: host editor; clean `valid` → `validated`; edit→validate→edit→stale; stale race discard; dependency failure retains edits; field+global issue display; no Accept/Save controls.

## §14 After SBW05c — SBW07-contract

After `SBW05c` merges, open `SBW07-contract` as an **approve-or-reject doc-only PR** over the existing frozen table in `HANDOFF-sbw07-persist-accepted-mechanics.md` §12.

Do **not** rewrite that contract unless review rejects a specific closed decision.

## Stop conditions

Stop if:

- the generated input type cannot round-trip the Server definition without loss;
- required editing needs a second handwritten schema;
- issue paths cannot be associated with the submitted definition/digest;
- the UI must silently drop a typed rule element;
- useful editing requires durable working-copy persistence not already designed;
- a save/accept operation is necessary to prove this slice;
- a path outside the allowlist is required.

## Final dispatch check

- [x] Re-anchor after `SBW04` / `#397` and `SBW05a` / `#398`.
- [x] Distinguish repository tip from last SBW integration.
- [x] Record SBW04 real-candidate live-proof verification debt as open.
- [x] Capture current generated validation fixtures (SBW05a).
- [x] State session-only editor persistence honestly (§12).
- [x] Dispatch `SBW05b` against §12 only (`#402`); backend/`liveApi`/workbench/save remained false in that bite.
- [x] After `SBW05b`, dispatch `SBW05c` against §13 (#404).
- [ ] After `SBW05c`, open `SBW07-contract` over frozen HANDOFF-sbw07 §12 without rewrite unless rejected.
- [ ] Confirm `SBW06` and all graph/projection/runtime successors remain false until their ordered bites.
