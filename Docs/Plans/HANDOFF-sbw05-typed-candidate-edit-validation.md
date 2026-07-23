# HANDOFF — SBW05 Complete-definition candidate editing and preview validation

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW04` merges as bites `SBW05a` → `SBW05b` → `SBW05c` (roadmap §5.1). Re-anchor paths, fixtures, and base SHA.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw05-typed-candidate-edit-validation.md`  
**Workstream:** `SBW05`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability across three PRs: edit a complete typed candidate working copy and obtain authoritative preview validation. Do not save mechanics, revise with a model, publish graph truth, or add media/combat behavior.

## Bite schedule

| Bite | PR mission | Allowlist focus | Still false |
|---|---|---|---|
| `SBW05a` | Validate transport: client method + Buddy route + digest association tests | Backend client/service/route/tests only | Editor UI, workbench, save, revise |
| `SBW05b` | Editor library + state machine + field/control matrix + structured fallback | `apps/live-control-ui/src/statblocks/editor/**` + unit tests | Workbench accept/save, durable editor schema |
| `SBW05c` | Workbench edit/validate host + live proof | Workbench module + liveApi wiring | Revise, accept/save, graph |

Each bite uses this handoff’s §6 contract; do not expand the parent allowlist mid-review.

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
| Base revision | Actual merged SHA containing `SBW01–04` |
| Predecessor contract | Shared semantic renderer and exact candidate read payload |
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
| Unknown future element | Renderer can show unsupported | Editor preserves it even when no dedicated control exists | Yes | typed fallback editor |

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
  validation is valid only for the exact digest submitted; every edit clears eligibility

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
- Dedicated controls may cover the first-release common fields, but unhandled typed structures must remain preserved. A structured fallback editor is allowed only when it remains constrained by generated types and cannot introduce unknown keys.
- Element identity/order must be preserved. Editing text cannot regenerate keys.
- Numeric controls enforce only contract-level shape/ranges locally; authoritative semantic validation remains Server-owned.
- `rules_text` is edited as text and always triggers revalidation.
- Any change, undo/redo result, or programmatic normalization that changes the digest marks validation stale.
- The UI distinguishes: `clean_unvalidated`, `dirty_unvalidated`, `validating`, `validated_with_warnings`, `validated_with_errors`, `validation_unavailable`.
- No save/accept eligibility claim exists beyond a derived `validation_has_no_errors` state for the exact digest.

### §6A State and fallback matrix

| Path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Initialize editor | copy exact candidate | complete working definition | candidate missing handled by SBW04 | N/A | fail closed/read-only source | candidate expired after load does not erase working copy | reload source explicitly |
| Edit | N/A | dirty/unvalidated | N/A | N/A | preserve unknown element/read-only block | prior receipt stale | undo may restore digest; receipt reuse only if exact digest association is proven |
| Validate | validating state | receipt bound to digest | N/A | retain working copy; unavailable | fail closed/global issue | response for old digest discarded | safe |
| Issue display | N/A | field/global issues | no issues | N/A | malformed path becomes global | stale receipt labeled/not used | revalidate |

No fallback to local validation, previous candidate receipt, Markdown parsing, or another revision.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Candidate | exact candidate ID for source attribution | none | No | editing does not mutate Server candidate |
| Definition | deterministic canonical digest over complete typed input using an explicitly tested normalization | mismatch means stale | No | receipt bound to digest |
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
| spellcasting | typed nested editor or preserved structured fallback | no flattening to prose | spellcaster round-trip |
| legendary/lair/phases | typed nested editor or preserved fallback | all limits/keys retained | complex fixture |
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

- [ ] Re-anchor after `SBW04`.
- [ ] Capture current generated validation fixtures.
- [ ] Decide and state session-only editor persistence honestly.
- [ ] Confirm `SBW06–07` and all graph/projection/runtime successors remain false.
