---
pr_body_template: |
  ## Outcome
  The live-control UI can express one surface's interaction contributions through one neutral validated publication contract so later host-lifecycle slices can consume the contract without importing Plan, Build, or Ingest domain modules.

  ## Merge-ready invariant
  For one `SurfaceInteractionPublication`, exact surface identity, Canvas/work-object pointer, Agent-context pointers, Tool launchers, Edit commands, Projection descriptors, and Projection binding identifiers form one deterministic fail-closed contract: contradictory identity, duplicate identifiers, incoherent availability, missing projection targets, or missing bindings invalidate the whole publication without invoking callbacks, mutating provider state, or changing any existing surface behavior.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Exact identity and opaque instance-key semantics | `surfaceInteraction/surfaceIdentity.ts` | Focused identity contract tests, including delimiter and label adversaries | TODO |
  | Whole-publication structural validation fails closed | `surfaceInteraction/publication.ts` | Validation matrix and deterministic issue-code tests | TODO |
  | Tool/Edit/Projection references remain internally coherent | `surfaceInteraction/publication.ts` | Missing target, wrong kind, missing binding, and duplicate-ID tests | TODO |
  | Neutral production boundary imports no surface/domain implementation | `surfaceInteraction/boundaries.test.ts` | Source-boundary test and source guard | TODO |
  | Existing UI behavior is unchanged | Existing Plan/Build/AgentInteraction suites | Focused regression command | TODO |

  ## Scope and explicit deferrals
  Base: `d101341bbffeb07627097de2dbcfe84930e01ce2` (PR #470 merge). Record actual head, changed paths, focused diff stat, paths outside §4, and confirmation that SIH-02 provider/store work remains false.

  ## Evidence produced
  ### Automated
  TODO
  ### Adversarial
  TODO
  ### Regression
  TODO
  ### Manual / dogfood
  Not applicable — this slice creates a runtime contract but does not bind it to a provider or render a new affordance.

  ## Gaps, waivers, and stop conditions
  TODO: none, or exact missing evidence, operator waiver, and stop report.
---

# HANDOFF — SIH-01 neutral Surface Interaction contracts

**Created:** 2026-08-01.  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sih01-neutral-surface-interaction-contracts.md`  
**Required implementation base:** `d101341bbffeb07627097de2dbcfe84930e01ce2` — merge of PR #470.

> **Dispatch gate:** Implement only the neutral runtime contract described here. Do not change provider/store ownership, render hosts, route publications, or current Plan/Build/Ingest behavior.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Surface identity** | Exact runtime identity consisting of a nonblank `surfaceId` and opaque nonblank `instanceKey`. Labels are never identity. |
| **Publication** | One runtime-only declaration of the active Surface's Tool, Edit, Canvas, Agent-context, and Projection contributions. It is not persisted and does not contain a provider lease token. |
| **Contribution** | One neutral descriptor consumed by a later shared host: Tool launcher, Edit command, Canvas pointer, Agent context, Projection descriptor, or Projection binding. |
| **Availability** | Explicit `enabled` or `disabled` state. Disabled contributions require a human-readable reason; enabled contributions may not carry a disabled reason. |
| **Projection descriptor** | An authorized projection ID, kind, preferred size, and required binding identifiers. It is not a renderer registration and grants no write authority. |
| **Projection binding** | A typed runtime value identified by exact binding ID. The neutral validator checks identifier coherence only; owning adapters remain responsible for the value's domain type and authorization. |
| **Fail closed** | Any material contract contradiction returns an invalid result for the whole publication. No partial contribution set is treated as valid. |
| **Compatibility adapter** | A later SIH-02 bridge from current Plan/Build/Ingest shapes into this neutral contract. No compatibility adapter is implemented in SIH-01. |

## §1 Mission and merge-ready invariant

The live-control UI can express one surface's interaction contributions through one neutral validated publication contract so later host-lifecycle slices can consume the contract without importing Plan, Build, or Ingest domain modules.

**Merge-ready invariant:** For one `SurfaceInteractionPublication`, exact surface identity, Canvas/work-object pointer, Agent-context pointers, Tool launchers, Edit commands, Projection descriptors, and Projection binding identifiers form one deterministic fail-closed contract: contradictory identity, duplicate identifiers, incoherent availability, missing projection targets, or missing bindings invalidate the whole publication without invoking callbacks, mutating provider state, or changing any existing surface behavior.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every path is construction, comparison, or validation of one runtime-only publication. No consumer or UI path is changed. |
| What adversarial sequence is most likely to falsify it? | Construct a superficially valid publication with an exact identity mismatch plus a Tool targeting a missing Projection, then observe a validator that returns a partially enabled publication or invokes a callback while validating. |
| Would the proposed §7 evidence detect that failure? | Yes. Whole-publication invalidation, issue-code accumulation, callback non-invocation, and unchanged-input determinism are tested at the validator boundary. |
| Which owning boundary is easiest to under-test? | Cross-reference validation between Tool activation, Projection kind, and Projection binding IDs. The handoff requires direct adversarial rows for each. |
| What fact would force this slice to stop or split? | Any need to change `AgentInteractionProvider`, `AppChrome`, `planSurface/**`, `buildSurface/**`, `ingestSurface/**`, renderer registries, CSS, persistence, or a public API to make the contract useful. Those belong to successors. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` |
| Sequencing authority | `Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md`, SIH-01 |
| Repository rules | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`; current repository review and baseline-failure protocols |
| Base revision | `d101341bbffeb07627097de2dbcfe84930e01ce2` |
| Predecessor contract | Current `ProjectionSurfaceIdentity` / `ProjectionSurfacePublication`; current `SurfaceConfig`; current `AppChromeAction` / `AppChromeTools`; current `AgentInteractionSurfaceContext` |
| Exact input consumed | Type-level and callback-level runtime values supplied by future Surface publishers; no serialized or server payload input |
| Named successor | SIH-02 — one lease-scoped publication store and compatibility publishers |
| What remains false | No active provider stores this publication; no shared host reads it; Plan/Build/Ingest do not publish it; no visible behavior changes |
| Explicit non-goals | Provider lifecycle, lease tokens, React rendering, host DOM, CSS, Plan recomposition, Build affordances, projection renderer catalog, graph writes, persistence, localStorage, runtime migrations |

Read authoritative inputs in order before changing code:

1. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
2. `Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md`
3. `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts`
4. `apps/live-control-ui/src/planSurface/types.ts`
5. `apps/live-control-ui/src/chrome/AppChrome.tsx`
6. `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`
7. `apps/live-control-ui/src/markdownCanvas/markdownCanvasTypes.ts`
8. Existing tests named in §7

If the base moved, the parent authority changed, current predecessor shapes materially differ, or the invariant cannot be preserved inside §4, stop and report the consequence before implementation.

## §3 Observable-path and adversarial-sequence inventory

This slice has no user-facing UI path. Its observable paths are public TypeScript imports and pure runtime validation results.

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---:|---|
| Build exact surface identity | Build-specific helper under `agentInteraction` | Neutral helper can encode exact caller-supplied identity parts without importing Build | Yes | `surfaceIdentity.ts` |
| Plan/Ingest exact surface identity | Domain-specific helpers under `agentInteraction` | Neutral helper supports exact opaque identities while existing helpers remain unchanged | Yes | `surfaceIdentity.ts` |
| Same-identity comparison | Existing projection helper compares `surfaceId` + `instanceKey` | Neutral comparison uses only exact `surfaceId` + `instanceKey`; labels and contribution changes do not affect identity | Yes | `surfaceIdentity.ts` |
| Empty publication | No full neutral publication exists | Valid publication with empty Tool/Edit/Projection collections and nullable Canvas/Agent context | Yes | `publication.ts` |
| Fully coherent publication | No full neutral publication exists | Returns `{ valid: true, publication }` without cloning away callback or binding identity | Yes | `publication.ts` |
| Contradictory surface identity | Projection-only path disables projections | Entire neutral publication is invalid with stable issue code | Yes | `publication.ts` |
| Duplicate contribution IDs | No shared rule | Entire publication invalid; all duplicates reported deterministically | Yes | `publication.ts` |
| Tool targets missing Projection | No shared rule | Entire publication invalid; callback/projection activation is never invoked | Yes | `publication.ts` |
| Tool targets content Projection | No shared rule | Invalid: Tool projection activation may target only Projection kind `tool` | Yes | `publication.ts` |
| Projection requires missing binding | Existing registrations are provider-specific | Entire publication invalid with exact projection and binding IDs in issue detail | Yes | `publication.ts` |
| Disabled contribution without reason | Current `disabled?: boolean` has no reason contract | Invalid with stable availability issue | Yes | `publication.ts` |
| Enabled contribution carrying disabled reason | Current shapes can carry no standardized reason | Invalid with stable availability issue | Yes | `publication.ts` |
| Invalid callback/binding value | Current provider trusts registered callbacks/payloads | Validator does not execute or semantically inspect runtime values; owning adapters remain responsible | Yes | `publication.ts` |
| Existing Plan/Build/Ingest runtime | Current behavior | Byte-for-byte source unchanged outside new package; focused suites remain equivalent | Yes | Regression suites + changed-path proof |

### Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Create identity for `plan` → publish `surfaceId: build` → include otherwise valid contributions → validate | Invalid whole publication with `identity_surface_mismatch`; no contribution returned as enabled and no callback called | V2, V8 |
| Create two Tool launchers with same ID but different activation → validate twice | Both validations return the same ordered duplicate issue; neither activation runs | V3, V8 |
| Tool targets Projection `x` → omit `x` → include command callback with observable spy elsewhere → validate | Invalid `tool_projection_missing`; every callback spy remains untouched | V4, V8 |
| Tool targets Projection `x` → declare `x` as kind `content` → validate | Invalid `tool_projection_kind_mismatch`; no fallback to callback or first projection | V4 |
| Projection `x` requires binding `graph` → omit binding → validate | Invalid `projection_binding_missing`; no partial Projection set is accepted | V5 |
| Disabled Tool/Edit contribution with blank reason → validate | Invalid `disabled_reason_missing` | V6 |
| Enabled Tool/Edit contribution with non-null disabled reason → validate | Invalid `enabled_has_disabled_reason` | V6 |
| Encode parts `["a", "b:c"]` and `["a:b", "c"]` → compare | Distinct instance keys and identities | V1 |
| Re-label a publication without changing identity → compare identities | Same identity; display label remains non-authoritative | V1 |
| Validate the same frozen publication twice | Deeply equivalent validation result and issue order; callback and binding object identities are preserved, not executed | V7, V8 |

## §4 Files in scope (allowlist)

Every implementation path is new. Do not modify predecessor consumers in this slice.

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Create | `apps/live-control-ui/src/surfaceInteraction/types.ts` | Defines the neutral runtime contribution and validation-result contracts. |
| Create | `apps/live-control-ui/src/surfaceInteraction/surfaceIdentity.ts` | Owns opaque tuple encoding and exact identity comparison. |
| Create | `apps/live-control-ui/src/surfaceInteraction/publication.ts` | Performs deterministic whole-publication structural validation. |
| Create | `apps/live-control-ui/src/surfaceInteraction/index.ts` | Exposes the narrow public contract; no domain re-exports. |
| Create | `apps/live-control-ui/src/surfaceInteraction/surfaceIdentity.test.ts` | Proves exact identity and tuple-boundary behavior. |
| Create | `apps/live-control-ui/src/surfaceInteraction/publication.test.ts` | Proves the complete validation and adversarial matrix. |
| Create | `apps/live-control-ui/src/surfaceInteraction/boundaries.test.ts` | Proves the neutral production package imports no surface/domain implementation and contains no JSX/React host code. |

**Bounded discovery exception:** Not applicable. If any additional path is required, stop and report it. Do not modify `tsconfig`, package scripts, predecessor types, or current consumers to make the tests compile.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | SIH-02 owns provider/store binding and lease lifecycle. |
| `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts` | Remains the current projection compatibility contract until SIH-02; SIH-01 does not migrate or re-export it. |
| `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts` | Consumer/provider migration is SIH-02 or later. |
| `apps/live-control-ui/src/chrome/AppChrome.tsx` | Tool/Edit host extraction is SIH-04/SIH-05. |
| `apps/live-control-ui/src/planSurface/**` | Plan native recomposition is deferred; Plan remains behavior-equivalent. |
| `apps/live-control-ui/src/buildSurface/**` | Build native publication begins at BLD-REF-01. |
| `apps/live-control-ui/src/ingestSurface/**` | Ingest compatibility/catalog work is SIH-02/SIH-03b. |
| `apps/live-control-ui/src/markdownCanvas/**` | Canvas authority is already landed and must not move. This slice carries pointers only. |
| `apps/live-control-ui/src/graphReference/**` | Neutral graph-reference capability is a predecessor; Build enablement is later. |
| `apps/live-control-ui/src/planSurface/projection/**` | Projection host move/catalog are SIH-03a/SIH-03b. |
| Any backend/API/schema/store path | Publication is runtime-only and non-durable. |
| CSS and visual layout | No host or user-facing change. |
| Runtime `leaseToken` | Generated and owned by SIH-02 store; never supplied by a Surface publication. |
| Rich React panel/body content | Do not place `ReactNode`, JSX, or renderer functions in the neutral publication. Current rich panels remain on compatibility paths until host slices design registered content. |
| Action toggle state (`pressed`) and fold initial-open state (`defaultOpen`) | Both are live on current Plan chrome (lock action and Edit-fold sections in `PlanSurfaceCanvas.tsx`). The legacy render path owns them until SIH-04/SIH-05 host extraction; those slices add neutral fields with adapter evidence before removing the legacy path. See §D. |
| Persistent serialization or localStorage | Separate public/durable contract and explicit successor. |

## §6 Implementation contract and conditional matrices

### 6.1 Required neutral types

Names may vary only when semantics remain exact and the public export surface stays narrow. Do not introduce a single untyped manifest bag.

```text
SurfaceInteractionIdentity
  surfaceId: nonblank string
  instanceKey: nonblank opaque string

SurfaceInteractionInstancePart
  string | number | boolean | null

SurfaceInteractionAvailability
  { status: "enabled"; disabledReason?: never }
  | { status: "disabled"; disabledReason: nonblank string }

SurfaceInteractionPointer
  kind: nonblank string
  value: nonblank string

SurfaceInteractionWorkObjectIdentity
  kind: nonblank string
  id: nonblank string

SurfaceInteractionCanvasContribution
  canvasId: nonblank string
  workObject: SurfaceInteractionWorkObjectIdentity

SurfaceInteractionAgentContextContribution
  label: nonblank string
  campaignId: string | null
  documentId: string | null
  sessionNumber: number | null
  ambientSummary: string | null
  pointers: readonly SurfaceInteractionPointer[]

SurfaceInteractionPlacement
  groupId: nonblank string | null      # null means pinned/top-level
  groupLabel: nonblank string | null   # null iff groupId is null
  groupOrder: finite integer
  itemOrder: finite integer

SurfaceInteractionToolActivation
  | { kind: "projection"; projectionId: nonblank string }
  | { kind: "command"; invoke: () => void | Promise<void> }

SurfaceInteractionToolContribution
  id, label, optional eyebrow
  placement
  availability
  activation

SurfaceInteractionCommandTarget
  kind: nonblank string
  id: nonblank string

SurfaceInteractionEditCommandContribution
  id, label, optional eyebrow
  placement
  availability
  target
  invoke: () => void | Promise<void>

SurfaceInteractionProjectionKind
  "tool" | "content"

SurfaceInteractionProjectionSize
  "compact" | "wide" | "fullscreen"

SurfaceInteractionProjectionDescriptor
  id: nonblank string
  kind: SurfaceInteractionProjectionKind
  preferredSize: SurfaceInteractionProjectionSize
  bindingIds: readonly nonblank string[]

SurfaceInteractionProjectionBinding<TBinding = unknown>
  id: nonblank string
  value: TBinding

SurfaceInteractionPublication<TBinding = unknown>
  surfaceId: nonblank string
  label: nonblank string
  identity: SurfaceInteractionIdentity
  canvas: SurfaceInteractionCanvasContribution | null
  agentContext: SurfaceInteractionAgentContextContribution | null
  tools: readonly SurfaceInteractionToolContribution[]
  editCommands: readonly SurfaceInteractionEditCommandContribution[]
  projections: readonly SurfaceInteractionProjectionDescriptor[]
  projectionBindings: readonly SurfaceInteractionProjectionBinding<TBinding>[]
```

`unknown` is permitted only as the generic default for a typed binding value. Do not add arbitrary `Record<string, unknown>`, metadata bags, renderer payload bags, or surface-specific context blobs.

Toggle (`pressed`) and fold initial-open (`defaultOpen`) states are deliberately not modeled. Both are live on current Plan chrome and remain owned by the legacy render path until SIH-04/SIH-05 host extraction; those slices extend the neutral contract with adapter evidence before the legacy path is removed. See §D.

### 6.2 Identity helpers

Required behavior:

```text
encodeSurfaceInteractionInstanceKey(parts)
  → JSON tuple encoding or an equivalently injective deterministic encoding
  → preserves type and tuple boundaries
  → never derives identity from display labels
  → no delimiter joining

sameSurfaceInteractionIdentity(left, right)
  → false for null/undefined
  → true only when surfaceId and instanceKey are exact string matches
```

A generic helper may construct an identity from `surfaceId` plus caller-supplied exact parts, but it must not contain Plan-, Build-, Ingest-, campaign-, document-, or session-specific field names. Domain helpers remain outside this package until an authorized compatibility slice.

### 6.3 Validation result

Validation is pure, non-throwing for ordinary invalid publications, deterministic, and does not execute callbacks.

```text
validateSurfaceInteractionPublication(publication)
  → { valid: true; publication }
  | { valid: false; publication; issues: readonly SurfaceInteractionValidationIssue[] }
```

The returned `publication` must retain the caller's callback and binding value identities. Validation may inspect structure and identifiers only. It must not clone through JSON, invoke callbacks, inspect React values, access global state, or load a renderer catalog.

Required stable issue codes:

| Code | Trigger |
|---|---|
| `surface_id_blank` | Publication or identity surface ID is blank |
| `instance_key_blank` | Identity instance key is blank |
| `identity_surface_mismatch` | `publication.surfaceId !== publication.identity.surfaceId` |
| `publication_label_blank` | Publication label is blank |
| `contribution_id_blank` | Tool, Edit, Projection, or binding ID is blank |
| `duplicate_tool_id` | Same Tool ID occurs more than once |
| `duplicate_edit_command_id` | Same Edit command ID occurs more than once |
| `duplicate_projection_id` | Same Projection ID occurs more than once |
| `duplicate_projection_binding_id` | Same binding ID occurs more than once |
| `placement_invalid` | Group ID/label nullability disagrees, label is blank, or order is not a finite integer |
| `disabled_reason_missing` | Disabled Tool/Edit contribution has blank reason |
| `enabled_has_disabled_reason` | Enabled Tool/Edit contribution supplies a disabled reason |
| `tool_projection_missing` | Projection activation targets no declared Projection |
| `tool_projection_kind_mismatch` | Projection activation targets a declared non-`tool` Projection |
| `projection_binding_missing` | Projection names an undeclared binding ID |
| `projection_binding_duplicate_reference` | One Projection repeats the same binding ID |
| `canvas_identity_invalid` | Canvas ID or work-object kind/ID is blank |
| `command_target_invalid` | Edit command target kind/ID is blank |
| `agent_context_invalid` | Agent label or supplied campaign/document/ambient fields violate required string/null shape |
| `agent_pointer_invalid` | Pointer kind/value is blank |

Issue order must be deterministic and documented by tests. Recommended order: publication/identity, Canvas, Agent context, Tool collection order, Edit collection order, Projection collection order, binding collection order, then cross-reference issues. The implementation may use a different order only if it is explicit and fully tested.

Issue details must identify the exact contribution ID and referenced ID where applicable. Do not include callback source text, binding values, document content, or other potentially sensitive bodies.

### 6.4 Whole-publication rule

No validator output may expose a filtered or partially accepted contribution list. `valid: false` means later hosts must treat the publication as unusable. SIH-02 will own the policy for replacing or clearing an active lease after invalid input.

The validator must accumulate independent structural issues in one pass where safe. It must not stop at the first duplicate and hide an identity mismatch, or vice versa.

### 6.5 Activation and callback rule

Tool command activations and Edit command callbacks are opaque runtime capabilities.

The validator verifies only:

- function presence for callback-bearing variants;
- structural activation discriminant;
- exact projection target coherence for projection activations.

The validator never invokes them. Authorization, current-lease revalidation, error capture, async lifecycle, and stale-callback suppression belong to SIH-02/SIH-04/SIH-05.

### 6.6 Projection rule

A Projection descriptor authorizes an ID and declares its kind, preferred size, and required binding identifiers. It does not register a renderer and does not prove the binding value is appropriate for that renderer.

A Tool activation with `kind: projection` must target a declared Projection with kind `tool`. Content Projections are opened through content/reference flows in later slices.

Unknown Projection kinds and sizes should be prevented by TypeScript and rejected at runtime when untyped input reaches validation. Do not silently coerce unknown strings.

### 6.7 Agent-context rule

Agent context remains pointer-only. The contract may carry campaign/document/session identifiers, a bounded ambient summary, and exact pointer pairs. It must not carry corpus bodies, document Markdown, graph node bodies, statblock mechanics, citation excerpts, or a generic source-envelope payload.

No cross-field authority is inferred. A `documentId` does not prove Canvas admission; a campaign ID does not prove graph authorization. Those checks remain with owning adapters and services.

### 6.8 Canvas rule

The Canvas contribution identifies the active Canvas host entry and exact work object. It does not expose editor state, dirty state, revision, digest, local draft, admission, or save callbacks. Those remain owned by `MarkdownCanvasSession` and later Edit-command adapters.

### 6.9 Public export rule

`surfaceInteraction/index.ts` exports only the neutral contract, helpers, validator, issue types, and result types. It must not re-export current Plan, Build, Ingest, AppChrome, AgentInteractionProvider, MarkdownCanvas, graphReference, or projection-registry symbols.

### 6.10 Input/output/failure summary

```text
Input:
  One in-memory SurfaceInteractionPublication<TBinding>.

Output:
  Deterministic valid or invalid result retaining the original publication.

Invariant:
  Same as §1.

Failure behavior:
  Structural contradiction → valid:false + stable issue codes.
  Callback or binding semantic invalidity → not proved here; no invocation or coercion.
  Unexpected programmer exception inside validator → test failure; do not convert arbitrary exceptions into valid output.

Replay / idempotency:
  Same immutable input → equivalent result and issue order.
  Changed input → independently validated; no cached acceptance.
  Retry after invalid input → safe; validator has no side effects.

Trust boundary:
  Verifies: structural identity, exact IDs, uniqueness, availability coherence, target/binding references, primitive shape.
  Records or trusts without proving: callback behavior, binding value semantics, renderer presence, graph authorization, Canvas admission, provider lease.
```

### 6.11 Commit model

Not applicable — this slice performs no durable or provider mutation. The only repository commit is the source-code PR itself.

### A. State and fallback matrix

| Observable path | Loading / initializing | Exact success | Ordinary miss | Dependency unavailable | Integrity / contract failure | Stale / superseded | Retry / replay |
|---|---|---|---|---|---|---|---|
| Identity encode/compare | N/A | Deterministic exact identity | Null/undefined compare returns false | N/A | Blank values remain invalid when publication is validated | No lease exists in this slice | Repeat is deterministic |
| Empty publication validation | N/A | Valid empty contribution sets | N/A | N/A | Invalid primitive shape returns issues | No lease exists | Safe repeat |
| Populated publication validation | N/A | Valid coherent publication | Missing optional Canvas/Agent context allowed | No external dependency consulted | Whole publication invalid, no fallback | No lease exists | Safe repeat |
| Tool projection cross-reference | N/A | Exact declared Tool Projection | Missing target is invalid | No renderer lookup | Wrong kind/duplicate is invalid | No lease exists | Safe repeat |
| Projection binding cross-reference | N/A | Every required ID declared exactly once | Missing binding is invalid | Binding semantics not inspected | Duplicate/missing reference invalid | No lease exists | Safe repeat |

Fallback sources: none. The validator never falls back to labels, first matches, current Plan config, renderer registries, or global provider state.

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Exact `surfaceId` + `instanceKey` | Exact string equality only | No ambiguity state; unequal means different identity | No |
| Display label | Never participates in identity | Label changes do not alter identity | No |
| Tuple parts | Deterministic boundary-preserving encoding | Different typed tuples cannot collapse | No delimiter fallback |
| Alias / normalized key | Prohibited | Not applicable | No |
| Work-object rename | Publisher retains or changes exact work-object ID according to domain authority; label irrelevant | Validator does not infer | No |
| Work-object switch | Publisher must supply a different instance key in a later lifecycle slice | SIH-01 cannot prove publisher behavior | No |

### C. Persistence and replay matrix

Not applicable — the contract is runtime-only and no serialization, localStorage, server store, migration, or durable identifier is added. Adding one is a stop condition and successor proposal.

### D. Predecessor-to-consumer mapping

**Grounding source:** Current TypeScript types at base `d101341b`; this table guides SIH-02 adapters but SIH-01 does not implement them.

| Predecessor field / outcome | Real shape and optionality | Neutral contract destination | Transformation | Proof in SIH-01 |
|---|---|---|---|---|
| `ProjectionSurfaceIdentity.surfaceId` | `string` | `identity.surfaceId` | Exact, no normalization | Identity tests |
| `ProjectionSurfaceIdentity.instanceKey` | opaque JSON tuple string | `identity.instanceKey` | Exact preservation | Identity tests |
| `SurfaceConfig.id` | `SurfaceMode` | `publication.surfaceId` | Exact string; must agree with identity | Mismatch tests |
| `SurfaceConfig.label` | `string` | `publication.label` | Display only | Label/identity test |
| `SurfaceConfig.canvas.documentId` | optional `string | null` | Future `canvas.workObject.id` when exact active Canvas exists | SIH-02 adapter decision; no mapping code now | Documented only |
| `SurfaceConfig.tools[]` | `{id,label,size}` | Tool projection activation + Projection descriptor | SIH-02 compatibility adapter; group/order defaults explicit there | Contract cross-reference tests only |
| `AppChromeAction` | `{id,label,eyebrow?,onClick,disabled?,pressed?}` | Tool command activation or Edit command, based on owning call site | SIH-02/SIH-04/SIH-05 adapter decision; never inferred by neutral package | Callback non-invocation tests |
| `AppChromeToolSection` | `{id,title,actions,defaultOpen?,panel?: ReactNode}` | Group placement for actions; rich panel deliberately not represented | Rich panel remains compatibility-only until host design | Boundary test rejects React/JSX production imports |
| `AppChromeAction.pressed` | optional toggle state; live on the Plan lock action (`PlanSurfaceCanvas.tsx`) | Not represented in SIH-01 | Deliberate deferral: legacy chrome renders toggle state until SIH-04/SIH-05 host extraction, which adds a neutral toggle field with adapter evidence before removing the legacy path | Documented only |
| `AppChromeToolSection.defaultOpen` | optional fold initial-open state; live on Plan Edit-fold sections (`PlanSurfaceCanvas.tsx`) | Not represented in SIH-01 | Deliberate deferral: legacy chrome renders fold state until SIH-04/SIH-05 host extraction, which adds a neutral group field with adapter evidence before removing the legacy path | Documented only |
| `AgentInteractionSurfaceContext` | label, campaign/document/session IDs, ambient summary, source envelope | Agent-context scalar fields + exact pointer pairs only | No body/source-envelope blob copied | Agent context validation tests |
| `ActiveProjection` | kind/key/size/title/glance | Not migrated in SIH-01 | SIH-03a owns active-host state | Explicitly out of scope |

Inventing a compatibility adapter, generic metadata bag, or copied Plan context to make this mapping executable is prohibited in SIH-01.

## §7 Evidence required to merge

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Command or scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|---|
| V1 | Exact identity is boundary-preserving and label-independent | `surfaceIdentity.ts` | Contract/adversarial | `npm test -- --run src/surfaceInteraction/surfaceIdentity.test.ts` | Exact tuple, delimiter, typed-part, null, and label tests pass | Any collision or domain-specific helper needed |
| V2 | Identity/publication contradiction invalidates whole publication | `publication.ts` | Contract/adversarial | Focused publication tests | `identity_surface_mismatch`, `valid:false`, no callback invocation | Partial valid output or projection-only disablement |
| V3 | Duplicate Tool/Edit/Projection/binding IDs are deterministic failures | `publication.ts` | Contract | Focused publication tests | All required duplicate codes and deterministic issue order | First-wins behavior or silent overwrite |
| V4 | Tool projection activation resolves only exact declared Tool Projection | `publication.ts` | Adversarial | Missing target and wrong-kind tests | Stable missing/kind issues; no callback/renderer lookup | Label fallback, first projection, or content target accepted |
| V5 | Projection binding requirements resolve only exact declared IDs | `publication.ts` | Adversarial | Missing/duplicate binding-reference tests | Stable issues and whole-publication invalidation | Binding value inspection or first-wins lookup |
| V6 | Availability and placement states are coherent | `publication.ts` | Contract | Enabled/disabled and group/order matrix | Every invalid combination rejected with stable code | Optional silent disabled reasons or non-finite order accepted |
| V7 | Validation is pure and deterministic | `publication.ts` | Adversarial | Freeze input, validate twice, spy callbacks and preserve binding identity | Equivalent results, no callbacks, same object identities | Mutation, JSON cloning, invocation, global read |
| V8 | Independent issues accumulate without enabling partial state | `publication.ts` | Adversarial | One publication with identity mismatch, duplicate IDs, missing target, and callback spies | All material issues returned in deterministic order; `valid:false`; spies untouched | Validator hides contradictions or filters to valid subset |
| V9 | Neutral production package imports no surface/domain implementation or React host code | `boundaries.test.ts` | Contract/source guard | Focused boundary test + `rg` commands | No prohibited imports, JSX, `ReactNode`, or `.tsx` production files | Any exception required for current consumer shape |
| V10 | Existing Plan/Build/AgentInteraction behavior remains unchanged | Existing suites | Regression | Exact command below | All focused predecessor tests pass on head | Any production path outside §4 required |
| V11 | TypeScript and production build introduce no new diagnostics | UI package | Regression/build | Base/head protocol below | Green, or zero new errors versus base with explicit waiver | New diagnostic in §4 or unreported baseline drift |
| V12 | Diff is exactly the §4 package | Repository | Scope | `git diff` commands | Only seven allowlisted files | Any additional path |

Run and record exact results:

```bash
cd apps/live-control-ui

npm test -- --run \
  src/surfaceInteraction/surfaceIdentity.test.ts \
  src/surfaceInteraction/publication.test.ts \
  src/surfaceInteraction/boundaries.test.ts

npm test -- --run \
  src/agentInteraction/projectionSurfacePublication.test.ts \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx

# Production boundary: tests may inspect predecessor shapes, production may not import them.
! rg -n 'planSurface|buildSurface|ingestSurface|AgentInteractionProvider|AppChrome|markdownCanvas|graphReference' \
  src/surfaceInteraction \
  --glob '!*.test.ts' \
  --glob '!*.test.tsx'

# No React host code in production files: no React imports, no ReactNode, no
# .tsx import specifiers. JSX is detected by file extension below, never by tag
# regex — a pattern like '<[A-Za-z]' also matches mandatory generics such as
# 'Promise<void>' and '<TBinding = unknown>' and would reject conforming code.
! rg -n 'ReactNode|from "react"|from '\''react'\''|\.tsx' \
  src/surfaceInteraction \
  --glob '!*.test.ts' \
  --glob '!*.test.tsx'

# No JSX host files: the package contains no production .tsx files at all.
test -z "$(rg --files src/surfaceInteraction --glob '*.tsx' --glob '!*.test.tsx')"

npm run typecheck
npm run build

git diff --check
git diff --stat d101341bbffeb07627097de2dbcfe84930e01ce2...HEAD -- \
  apps/live-control-ui/src/surfaceInteraction/types.ts \
  apps/live-control-ui/src/surfaceInteraction/surfaceIdentity.ts \
  apps/live-control-ui/src/surfaceInteraction/publication.ts \
  apps/live-control-ui/src/surfaceInteraction/index.ts \
  apps/live-control-ui/src/surfaceInteraction/surfaceIdentity.test.ts \
  apps/live-control-ui/src/surfaceInteraction/publication.test.ts \
  apps/live-control-ui/src/surfaceInteraction/boundaries.test.ts

git diff --name-only d101341bbffeb07627097de2dbcfe84930e01ce2...HEAD
```

### Minimal live / dogfood proof

Not applicable — this slice has no provider binding, route publication, rendered host, persistence, or user-facing behavior. Automated owning-boundary and predecessor regression evidence is the appropriate proof.

### Baseline failure protocol

`npm run typecheck` and `npm run build` have been baseline-red in recent UI work. They remain required evidence.

If either fails on head:

1. check out or use a clean worktree at `d101341bbffeb07627097de2dbcfe84930e01ce2`;
2. run the identical command on base and head;
3. record exact error tuples by file, line, code, and message;
4. prove head introduces zero new errors, especially under `surfaceInteraction/**`;
5. request an explicit operator waiver if the gate remains red;
6. do not call the command passed.

A new error in any §4 file blocks merge and is not waivable as baseline.

## §8 Required PR description and implementation handback

The PR description must remain current and include:

1. §1 Mission copied exactly.
2. §1 merge-ready invariant copied exactly.
3. The complete V1–V12 evidence ledger with required proof, produced result, and provenance.
4. Base SHA `d101341bbffeb07627097de2dbcfe84930e01ce2` and actual head SHA.
5. Actual changed paths and focused diff stat limited to §4.
6. Every §7 command and exact result.
7. Provenance of each result: author-local, independently rerun local, CI, or manual.
8. Base/head typecheck and build comparison when baseline-red.
9. Explicit operator waivers; `none` when none exist.
10. Paths outside §4; `none` or a stop report.
11. Stop conditions encountered and resolution; `none` when none exist.
12. Confirmation that SIH-02, SIH-03a/b, SIH-04, SIH-05, BLD-REF-01/02, and Plan recomposition remain false.
13. Confirmation that no existing production consumer imports `surfaceInteraction` yet.
14. Confirmation that no persistent format, API, provider store, renderer registry, or React host was added.
15. Confirmation that this handoff was implemented without compression or omitted matrices.

A generic “Summary / Test plan” PR body does not satisfy this section.

## §9 Acceptance rubric

- [ ] Exactly one capability was delivered: the neutral validated runtime publication contract — V1–V9.
- [ ] The §1 invariant holds for every §3 path and adversarial sequence — V1–V8.
- [ ] Contradictory identity invalidates the whole publication — V2.
- [ ] Duplicate IDs never become first-wins maps — V3.
- [ ] Tool projection targets and binding requirements resolve only by exact IDs — V4–V5.
- [ ] Availability and placement states are explicit and coherent — V6.
- [ ] Validation is deterministic, pure, and callback-free — V7–V8.
- [ ] Production `surfaceInteraction/**` imports no Plan, Build, Ingest, AppChrome, AgentInteractionProvider, MarkdownCanvas, graphReference, React, or JSX implementation — V9.
- [ ] Existing Plan, Build, and AgentInteraction focused behavior remains unchanged — V10.
- [ ] Typecheck/build evidence is truthful, including baseline comparison and any waiver — V11.
- [ ] Exactly the seven §4 files changed — V12.
- [ ] No durable contract, storage, API, renderer catalog, provider state, or UI host was introduced.
- [ ] SIH-02 remains the named next capability and is unimplemented.

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- current behavior cannot be represented without importing a domain production module into `surfaceInteraction/**`;
- a `ReactNode`, JSX panel, renderer function, or concrete component must enter the neutral publication;
- `AgentInteractionProvider`, `AppChrome`, a Surface route, projection registry, or Canvas code must change;
- a provider lease token must be supplied by a Surface publication;
- a persistent schema, serialization, localStorage record, API payload, or migration becomes necessary;
- callbacks must be invoked to establish validity;
- validation requires graph reads, Canvas admission, renderer lookup, or global provider state;
- whole-publication invalidation cannot preserve an existing required behavior;
- a second independently useful capability appears, such as a compatibility adapter or runtime store;
- any path outside §4 is required;
- focused predecessor suites regress;
- typecheck/build introduces a new error under §4;
- the parent authority or merged predecessor shapes differ materially from this handoff.

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Tracker or authority update needed:
```
