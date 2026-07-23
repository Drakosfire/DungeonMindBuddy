# HANDOFF — SBW13 Append immutable revision and compare

**Created:** 2026-07-22  
**Status:** PRE-DESIGNED — dispatch after `SBW06`, `SBW07`, and `SBW10` merge; re-anchor append contract, exact parent semantics, and renderer/editor paths.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw13-append-revision-compare.md`  
**Workstream:** `SBW13`  
**Repository:** `Drakosfire/DungeonMindBuddy`

> Dispatch one capability: fork an exact accepted revision into the existing edit/revise workflow, append one immutable child revision, and compare parent/child. Do not update graph bindings, Plan embeds/placements, active combatants, or preferred revision state.

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Open exact accepted revision as editable candidate/working copy | No; required revision input | Existing candidate contract | Yes | Include |
| Append immutable child revision with exact parent | Yes | Yes | Yes | Include |
| Compare parent and child mechanics | No; required human proof before later upgrade | No | Yes | Include |
| Update bindings/placements/embeds | Yes | Yes | Yes | Successor `SBW14` |
| Upgrade active combatants | Yes | Yes | Yes | Explicitly excluded |
| Merge divergent revision branches | Yes | Yes | Yes | Later design only |

**Selected capability:** the GM can create one immutable child revision from one exact parent and understand the mechanical delta while every existing use remains pinned.

**Why included rows share one invariant:** append without exact-source editing and human comparison would not be safely usable; comparison exists to prove what the new immutable revision contains, not to migrate any consumer.

## §1 Mission

A GM can fork an exact accepted statblock revision, edit/validate or revise it, append one immutable child revision, and compare it with its parent so mechanics evolve without mutating existing uses.

**Invariant**

```text
Appending mechanics always creates a new revision_id with one exact expected parent_revision_id; the parent remains readable, and no binding, embed, placement, or combatant changes in this slice.
```

**Mission falsification test**

```text
This is not one slice if implementation must also choose or update campaign-preferred mechanics, rewrite graph bindings, migrate documents/placements, upgrade combat state, or merge branches.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §11; tracker `SBW13` after decomposition; DungeonMindServer append-revision contract |
| Repository rules | `AGENTS.md`; immutable mechanics ownership; external-agent PR loop |
| Base revision | Actual merged SHA containing `SBW06–07` and `SBW10` |
| Predecessor contract | Exact revision read/Threat Sheet, complete editor/validation, candidate revise lineage, accepted mechanics ref |
| Exact input consumed | Exact statblock ID, expected parent revision ID/digest, validation-clean complete definition or candidate source, idempotency key |
| Named successor | `SBW14` explicit scoped use upgrade |
| What remains false | New revision is not automatically selected anywhere |
| Explicit non-goals | binding/preferred/placement/embed updates, active combat changes, branch merge, media, graph publication redesign |

Read in order:

1. integration design §11
2. tracker `SBW13`
3. current Server append-revision request/response/conflict/idempotency fixtures
4. merged `SBW06` lineage and `SBW05` validation digest contract
5. merged `SBW10` exact revision projection/shared renderer
6. existing bindings/embeds/combat models solely to prove non-mutation

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Start revision from Threat Sheet/exact view | Read-only exact mechanics | Fork complete definition with exact parent locator | Yes | Threat Sheet/workbench |
| Edit/validate/revise | Candidate workflow exists | Reuse it with parent lineage disclosed | Yes | workbench |
| Append | First-save only | Call Server append with exact parent/idempotency | Yes | service/route |
| Stale parent | Undefined product behavior | Conflict; no silent rebase/latest | Yes | service/UI |
| Duplicate submit | Risk duplicate child | Idempotent replay returns same child | Yes | service/store |
| Downstream success/local workflow write failure | Undefined | Child remains valid; exact ref recoverable | Yes | orchestration |
| Reload parent and child | Exact read exists | Both readable with immutable IDs/digests | Yes | exact read |
| Compare | No semantic compare | Structured parent→child delta, including rule elements/human-adjudicated text | Yes | compare view model/UI |
| Existing graph binding | Pinned parent | Remains unchanged | Yes | non-mutation proof |
| Existing Plan embed/placement | Pinned parent | Remains unchanged | Yes | non-mutation proof |
| Existing combatant | Pinned/snapshot | Remains unchanged | Yes | non-mutation proof |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `apps/live_control_server/models/statblock_revision_workflow.py` | strict append/result/partial view models |
| Create | `apps/live_control_server/services/statblock_revision_append.py` | exact-parent validation/idempotent append/reconcile |
| Modify | merged DungeonMind client | typed append-revision operation |
| Modify | candidate/workflow routes or create narrow revision route | fork/append/read response |
| Create | `tests/test_statblock_revision_append.py` | stale/idempotency/partial/exact-read proof |
| Create/Modify | focused route tests | contract proof |
| Create | `apps/live-control-ui/src/statblocks/revisions/statblockRevisionDiff.ts` | pure semantic diff model |
| Create | `apps/live-control-ui/src/statblocks/revisions/StatblockRevisionCompare.tsx` | parent/child comparison view |
| Create | comparison unit/component tests with complex fixtures | delta proof |
| Modify | `ThreatSheet.tsx` and/or workbench | “Edit as new revision,” append confirmation, open compare |
| Modify | focused Threat Sheet/workbench tests | workflow/non-mutation proof |
| Modify | API types/functions/tests | fork/append/read operations |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package; apps/live-control-ui/src/statblocks/; exact candidate/workflow route area
Maximum additional paths: 6
Allowed path kinds: adapter method, captured append fixtures, lineage/ref metadata field, shared renderer element-key helper, focused tests
Decision rule: required to append and compare one exact parent/child pair
Required report: identify any local workflow record added and prove no use-selection state changes
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| update Threat binding/preferred revision | `SBW14` |
| update Plan embed/placement | `SBW14` |
| update active combatant | prohibited; create a new combatant later if desired |
| automatic latest selection | violates invariant |
| branch merge/rebase | separate future mechanics design |
| generic version-control UI | only parent/child compare |
| graph write | no consumer migration here |
| media regeneration | separate media workflow |

## §6 Implementation contract

### Append request

```text
AppendStatblockRevisionRequestV1:
  statblock_id
  expected_parent_revision_id
  expected_parent_definition_digest
  complete validated definition
  validation receipt/digest for exact definition
  source candidate/lineage metadata when present
  stable idempotency key
  change note? bounded
```

### Append result

```text
AppendedRevisionRefV1:
  statblock_id
  parent_revision_id
  revision_id
  definition_digest
  contract/version
  appended_from_candidate_id?
  appended_at
```

### Compare model

The compare is derived, not canonical. It must include:

- identity/classification changes;
- AC/HP/speed and abilities/proficiencies changes;
- added/removed/changed/reordered typed rule elements using stable element keys where available;
- spellcasting/legendary/lair/phase changes;
- `rules_text` and `human_adjudicated` text changes;
- validation/provenance metadata changes only in a secondary section;
- explicit “unchanged” summary counts.

Do not compare rendered HTML/Markdown as the primary diff.

```text
Input:
  exact parent resource + validation-clean complete child definition + idempotency key

Output:
  exact immutable child revision ref and derived parent/child comparison

Invariant:
  new revision with exact parent; all existing uses unchanged

Failure behavior:
  parent missing/digest mismatch -> block
  stale parent/current Server conflict -> typed conflict; no silent rebase
  validation stale/errors -> block before append
  timeout/auth/rate limit -> typed failure; working definition retained
  append success + local result write failure -> child remains valid; reconcile exact result
  exact read mismatch -> integrity failure
  compare cannot align an element -> show remove/add or unmatched, never hide

Replay / idempotency:
  same key + same parent/definition -> same child result
  same key + changed parent/definition -> conflict
  new key against same parent may create another branch only if Server contract allows; UI must disclose branch consequence and default not to encourage it
  duplicate response -> one child ref

Trust boundary:
  Verifies: exact parent IDs/digest, validation receipt, Server response/read, typed compare inputs
  Records without proving: whether change is better or should be adopted
  Rejects: implicit latest, in-place mutation, name/path identity, consumer updates
```

### Commit model

```text
Commit point: Server persists immutable child revision.
Before commit: editable candidate/working definition only.
After commit: parent and child are both durable; existing consumers still reference parent.
Truthful post-commit failure: child revision exists; local workflow/compare reference pending recovery.
Recovery: reconcile idempotency/exact child read, then reopen compare.
```

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Dependency unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Fork parent | exact read | working copy with parent lineage | 404 | unavailable | digest mismatch fails | no latest | retry exact |
| Append | submitting | child ref | N/A | typed failure, work retained | malformed/mismatch fail | parent conflict | idempotent reconcile |
| Read parent/child | exact reads | both resources | 404 integrity issue | compare unavailable but refs retained | digest mismatch fail | immutable | retry |
| Compare | derive typed delta | complete delta | N/A | N/A | unmatched elements shown | parent/child exact | deterministic |
| Consumer state audit | inspect fixtures/stores | unchanged | N/A | N/A | any changed consumer fails PR | N/A | N/A |

No fallback to latest or another parent.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Logical statblock | exact statblock ID | none | No | shared revision lineage |
| Parent | exact revision ID + digest | mismatch/stale conflict | No latest | append authority |
| Child | exact Server revision ID + digest | collision mismatch integrity failure | No | new immutable resource |
| Rule element | stable element key/type | missing/mismatch shown as add/remove/unmatched | No name-only silent alignment | compare only |
| Idempotency | stable operation key | changed payload conflict | No | replay safety |
| Display name | informational | duplicates irrelevant | No | never revision selection |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Reversion |
|---|---|---|---|---|---|
| Append child | Server immutable revision lineage | exact parent/child IDs/digests | idempotent same request | Server contract | cannot mutate/delete as rollback |
| Local append ref/operation | bounded workflow record if required | IDs/idempotency retained | same ref idempotent | schema versioned | recoverable metadata only |
| Compare | derived from exact reads | deterministic for same resources | safe repeat | compare view version local | N/A |
| Existing consumers | unchanged graph/document/combat records | exact previous refs | no operation | existing schemas | N/A |

### §6D Predecessor-to-consumer mapping

**Grounding source:** Server append request/response/error fixtures, exact revision resources, generated rule element types.

| Source | Consumer | Rule | Proof |
|---|---|---|---|
| parent statblock/revision/digest | append request + lineage header | exact copy | request fixture |
| validated child definition/digest | append request | exact complete input | service test |
| child revision response | appended ref | exact copy | fixture/read test |
| stale/conflict envelope | blocked UI state | no rebase | error test |
| parent/child typed definitions | semantic diff | element keys/types preserved | complex fixtures |
| human-adjudicated/rules text | compare text delta | visible | fixture |
| existing binding/embed/combat refs | non-mutation audit | bytes/records unchanged | integration tests |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| Exact parent required/no latest | service | missing/mismatch/stale tests | blocked exact errors |
| Append idempotent | service/Server fake | duplicate/changed key tests | same child/conflict |
| Parent remains readable | exact-read integration | append then read both | distinct IDs/digests |
| Post-commit recovery | service failure injection | local write failure/reconcile | same child recovered |
| Semantic compare complete | diff unit/component | simple/complex fixtures | expected deltas/unmatched visible |
| Existing bindings/embeds/combat unchanged | integration/non-mutation | fixture/store assertions | exact refs unchanged |
| UI makes adoption separate | component | workflow test | compare ends without upgrade action committing |

Required commands:

```bash
uv run pytest tests/test_statblock_revision_append.py <focused route/non-mutation tests> -q
cd apps/live-control-ui && npm test -- --run src/statblocks/revisions/<diff-and-component-tests> <ThreatSheet/workbench tests> src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

Open a published exact revision, fork it, edit and validate one attack, append, compare parent/child, and reopen both exact revisions. Show an existing Plan embed and graph binding still resolve the parent. Simulate stale parent and double-submit.

## §8 Required handback

Include real append/idempotency/error mapping, comparison coverage matrix, base/head, actual paths, commands/results/provenance, live parent/child IDs/digests, stale/replay/non-mutation evidence, baseline failures/waivers, and confirmation that no upgrade ships.

## §9 Acceptance rubric

- [ ] Exact parent revision and digest are required.
- [ ] Append creates one new immutable child; parent remains readable.
- [ ] Stale parent never rebases silently.
- [ ] Replay and post-commit recovery are safe.
- [ ] Comparison is typed/semantic and covers complex rule elements and adjudicated text.
- [ ] Unmatched elements are visible, not dropped.
- [ ] Existing graph bindings, embeds, placements, and combatants remain unchanged.
- [ ] No preferred/latest or upgrade capability ships.

## §10 Reviewer protocol

Start with non-mutation of existing consumers. Audit exact parent/idempotency/partial failure, then compare complex fixtures. Search for graph/document/combat writes, latest selection, in-place save, text-only diff, and silent element matching.

## §11 Re-review protocol

Rerun exact parent, stale, duplicate, post-commit recovery, parent/child reads, all compare fixtures, and consumer non-mutation tests after every fix.

## Stop conditions

Stop if:

- Server append contract lacks exact parent or idempotency semantics;
- exact parent/child cannot both be read after append;
- stable element identity is too weak for a truthful compare and a separate compare contract is needed;
- append necessarily changes a campaign preferred/binding state;
- active combat is rewritten;
- a path outside the bounded allowlist is required.

## Final dispatch check

- [ ] Re-anchor after `SBW06–07`, `SBW10`.
- [ ] Capture real append fixtures.
- [ ] Freeze compare alignment/unmatched policy.
- [ ] Confirm `SBW14` upgrade remains false.
