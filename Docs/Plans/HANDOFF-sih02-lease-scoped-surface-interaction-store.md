---
pr_body_template: |
  ## Outcome
  The app-scoped interaction owner can bind, update, invalidate, and clear one neutral Surface Interaction publication under an exact lease so current surfaces cannot leak stale tools, edits, projections, or callbacks across surface changes.

  ## Merge-ready invariant
  At every observable point, exactly one app-scoped lease token governs one canonical neutral publication and all temporary compatibility attachments: same-identity valid updates preserve that token and revalidate current capabilities, null/invalid/different-identity transitions clear prior active state before replacement, and any cleanup, invocation, registration, or provider-owned async completion captured outside the current lease is a permanent no-op.

  ## Evidence required to merge
  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | One exact app-scoped lease owns the neutral publication and current compatibility attachments | AgentInteractionProvider + surfaceInteractionLease.ts | Bind/update/replace/clear state-machine tests | TODO |
  | Same-identity updates preserve the lease while invalid or contradictory updates fail closed | surfaceInteractionLease.ts + provider integration | Adversarial update and recovery tests | TODO |
  | Stale cleanup, callbacks, registrations, and provider-owned async completions cannot act on a newer lease | Provider callback gates and leased callback wrappers | Ordered A→B interleaving tests | TODO |
  | Current projection publications and AppChrome props are mirrored through one compatibility composition without moving host DOM | Compatibility adapter + AppChrome bridge | Mapping tests and component equivalence tests | TODO |
  | Existing Plan, Ingest, Build, graph-reference, and projection behavior remains equivalent | Existing focused suites | Regression command | TODO |
  | The slice adds no persistence, second provider, host extraction, or native Build affordance | Changed-path/source guards + storage test | Static guards and localStorage assertion | TODO |

  ## Scope and explicit deferrals
  Base: 390aa0bce872a74a0ac325a2dd7b9d9dd0025d9b (PR #477 merge). Record actual head, changed paths, focused diff stat, paths outside §4, and confirmation that SIH-03a/b, SIH-04, SIH-05, Build-native publication, and Plan recomposition remain false.

  ## Evidence produced
  ### Automated
  TODO
  ### Adversarial
  TODO
  ### Regression
  TODO
  ### Manual / dogfood
  Not applicable unless implementation changes normal visible behavior; this slice is a lease/store and compatibility-wiring capability, not a new product affordance.

  ## Gaps, waivers, and stop conditions
  TODO: none, or exact missing evidence, operator waiver, and stop report.
---

# HANDOFF — SIH-02 one lease-scoped Surface Interaction publication store

**Created:** 2026-08-01.  
**Status:** ACTIVE — dispatch exactly one implementation capability.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-sih02-lease-scoped-surface-interaction-store.md`  
**Required implementation base:** `390aa0bce872a74a0ac325a2dd7b9d9dd0025d9b` — merge of PR #477.  
**Suggested branch:** `feat/sih02-lease-scoped-surface-interaction-store`

**Amended 2026-08-01 (pre-dispatch critique):** Legacy `publishProjectionSurface` same-identity continuity is an explicit adapter matrix (not an implied reuse of the neutral bind API); the provider keeps exactly one Symbol lease token that replaces the prior projection-surface token rather than living beside it; AppChrome Edit targets without a Canvas work object use the exact SIH-01 blank target `{ kind: "", id: "" }`; registrar and AppChrome publisher callback identities must change when effective authorization toggles under a preserved token; native leases ignore Chrome fragments with focused proof even though this slice has no production native publisher.

> **Dispatch gate:** Implement one app-scoped neutral publication lease and only the temporary adapters required to mirror current projection and AppChrome inputs into that lease. Do not extract Tool/Edit/Projection host DOM, introduce a renderer catalog, make Build a native publisher, or recompose Plan.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Neutral publication** | The SIH-01 `SurfaceInteractionPublication` canonical validated snapshot. It contains no provider lease token and is not persisted. |
| **Lease** | One provider-owned transient registration identified by an opaque internal token. The token is never placed in a publication, URL, storage key, durable format, or Surface-owned type. |
| **Singular lease token** | The one provider-owned `Symbol` that simultaneously identifies the neutral publication lease and every compatibility attachment (legacy projection surface, Chrome fragment, graph-reference binding, diagnostics payload, active projection). The existing projection-surface `Symbol` is **replaced by** this token — it is not retained as a second parallel owner. |
| **Bound identity** | The exact `surfaceId` + `instanceKey` identity established by a valid bind. It survives an invalid same-identity update so a later corrected update can recover under the same lease. |
| **Base publication** | The direct neutral publication, or the neutral publication produced from the current legacy `ProjectionSurfacePublication`, before temporary AppChrome contributions are composed. |
| **Effective publication** | The one validated neutral publication exposed by the provider after composing the base publication with the current lease-bound compatibility fragment and wrapping command callbacks with lease guards. Invalid composition exposes no publication. |
| **Compatibility attachment** | Temporary legacy data associated with the same lease: current `ValidatedProjectionSurface`, graph-reference binding, diagnostics payload, or AppChrome contribution fragment. It is not a second lease or second publication authority. |
| **Chrome compatibility fragment** | A temporary neutral-shaped fragment produced from `AppChrome.pageActions` and `AppChrome.editorTools`. It carries Tool/Edit contributions only and is composed into the current compatibility lease. |
| **Lease-guarded callback** | A wrapper that invokes the original callback only when its lease token is current and the same contribution ID still authorizes the same original callback. A removed or replaced callback under the same identity is stale. |
| **Provider-owned async completion** | An async result whose application mutates provider-owned projection/binding state. It must re-check the current lease before applying. This slice does not cancel arbitrary domain work already started by a callback. |
| **Explicit empty lease** | A current token with no effective publication. It truthfully clears hosts and makes stale closures harmless during loading, null publication, or route transition. |
| **Native publisher** | A future Surface that supplies a complete neutral publication directly. No current Plan, Build, Ingest, or Live Control call site becomes a native publisher in this slice. |

## §1 Mission and merge-ready invariant

The app-scoped interaction owner can bind, update, invalidate, and clear one neutral Surface Interaction publication under an exact lease so current surfaces cannot leak stale tools, edits, projections, or callbacks across surface changes.

**Merge-ready invariant:** At every observable point, exactly one app-scoped lease token governs one canonical neutral publication and all temporary compatibility attachments: same-identity valid updates preserve that token and revalidate current capabilities, null/invalid/different-identity transitions clear prior active state before replacement, and any cleanup, invocation, registration, or provider-owned async completion captured outside the current lease is a permanent no-op.

### Capability decomposition decision

| Candidate outcome | Independently useful? | Public/runtime contract changed? | Visible surface changed? | Independently testable/revertible? | Decision |
|---|---|---|---|---|---|
| One neutral lease-scoped publication state machine in the existing app owner | Yes | Yes | No | Yes | Include |
| Mirror current projection publication into the neutral lease | No — required predecessor bridge | Temporary compatibility API only | No | Tested with the same lease invariant | Include |
| Mirror current AppChrome `pageActions` / `editorTools` into the same lease while preserving current rendering | No — required predecessor bridge | Temporary compatibility API only | Normal behavior unchanged | Tested with the same lease invariant | Include |
| Extract Projection host shell/types | Yes | Yes | Potentially | Yes | SIH-03a successor |
| Add typed Projection catalog | Yes | Yes | Potentially | Yes | SIH-03b successor |
| Extract shared Tool host DOM | Yes | Yes | Yes | Yes | SIH-04 successor |
| Extract shared Edit host DOM | Yes | Yes | Yes | Yes | SIH-05 successor |
| Make Build a native publisher / add Find Existing | Yes | Yes | Yes | Yes | BLD-REF-01 successor |
| Persist lease/open-host state | Yes | Durable | Potentially | Yes | Deferred; reject from this slice |

The compatibility rows are included because they are the only way to prove the lease against real current publishers without moving host ownership or shipping a second user capability. They all establish the same invariant: legacy inputs are subordinate attachments to one neutral app-scoped lease.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Every included path is a bind, update, composition, callback, registration, cleanup, or provider-owned completion governed by one current token. |
| What adversarial sequence is most likely to falsify it? | Plan lease A publishes projection + Edit actions → operator captures an Edit callback and opens a Tool → Build lease B binds → A cleanup, the stale Edit callback, and a late A graph-reference completion all run → any A state or side effect appears under B. |
| Would the proposed §7 evidence detect that failure? | Yes. V2, V4, V5, V6, and V8 require the exact ordered interleaving at the provider/component boundary, including same-identity removal/replacement and late provider-owned completion. |
| Which owning boundary is easiest to under-test? | The boundary between a canonical raw publication and its lease-guarded effective publication, especially stale callbacks after a same-identity contribution replacement; and the legacy `publishProjectionSurface` same-identity adapter that must preserve token continuity for Plan/Build effects. |
| What fact would force this slice to stop or split? | Any need to move host DOM, type renderer bindings, persist lease state, alter Canvas authority, change callback signatures, cancel arbitrary domain operations, or introduce a second provider/partial-publication owner. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` |
| Sequencing authority | `Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md`, SIH-02 |
| Repository rules | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`; `.cursor/skills/external-agent-pr-loop/SKILL.md`; current repository review and baseline-failure rules |
| Base revision | `390aa0bce872a74a0ac325a2dd7b9d9dd0025d9b` |
| Predecessor contract | SIH-01 neutral contract merged in PR #477; current `AgentInteractionProvider` projection lease; current `ProjectionSurfacePublication`; current `AppChromeAction` / `AppChromeTools` |
| Exact input consumed | `SurfaceInteractionPublication \| unknown \| null` for the neutral bind/update boundary; current typed legacy projection publication; current AppChrome action/tool props |
| Named successor | SIH-03a — neutral Projection host shell and types |
| What remains false | No shared Tool/Edit host reads the publication; no renderer catalog; no Build-native Tool/Edit publication; no Plan native recomposition; no persistent lease/open state |
| Explicit non-goals | Host DOM/CSS movement, projection renderer redesign, graph writes, Canvas state ownership, callback cancellation after valid invocation, new error UI, localStorage, URL schema, server API, route redesign, broad renames |

Read authoritative inputs in order before changing code:

1. `Docs/Design/ARCHITECTURE-surface-interaction-layer.md`
2. `Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md`
3. `Docs/Plans/HANDOFF-sih01-neutral-surface-interaction-contracts.md`
4. `apps/live-control-ui/src/surfaceInteraction/types.ts`
5. `apps/live-control-ui/src/surfaceInteraction/publication.ts`
6. `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`
7. `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts`
8. `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts`
9. `apps/live-control-ui/src/chrome/AppChrome.tsx`
10. `apps/live-control-ui/src/App.tsx`
11. `apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx`
12. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx`
13. `apps/live-control-ui/src/buildSurface/BuildSurfacePage.tsx`
14. Existing tests named in §7

**Authority precedence**

1. `ARCHITECTURE-surface-interaction-layer.md`
2. `PLAN-surface-interaction-host-hoist-pr-sequence.md`
3. This checked-in SIH-02 handoff
4. SIH-01 exported contract and validator
5. Current provider/compatibility implementation and owning tests
6. Project Sources and chat summaries

If the base moved, SIH-01 exports changed, the current provider no longer owns the singular projection lease, current AppChrome shapes differ materially, or the invariant cannot be preserved inside §4, stop and report the consequence before implementation.

## §3 Observable-path and adversarial-sequence inventory

| Path | Current behavior | Required behavior | Same invariant as §1? | Owning boundary |
|---|---|---|---|---|
| First valid neutral bind | No provider consumes SIH-01 publication | Validate, create one token, store guarded effective publication | Yes | Lease state machine + provider |
| Explicit null bind | Current projection API can publish null | Create a new explicit empty lease and clear all prior active/attached state | Yes | Provider |
| Invalid initial bind | No neutral store behavior | Create a new invalid/empty lease; expose no publication; never retain prior state | Yes | Lease state machine + provider |
| Valid same-identity update | Current projection config update preserves its legacy token | Preserve exact token, replace/recompose publication, revalidate active capabilities | Yes | Lease state machine + provider |
| Invalid same-identity update | Legacy invalid config disables projection paths | Preserve bound identity/token, expose no publication, clear active state and attachments; corrected same-identity update may recover | Yes | Lease state machine + provider |
| Different-identity update through update API | Current helper simply refuses nonmatching updates | Current-token mismatch fails closed and clears effective state; a real identity switch must use bind | Yes | Lease state machine |
| Different-identity bind | Current projection bind replaces registration | Clear A state/attachments before installing B; A cleanup cannot erase B | Yes | Provider |
| Null after populated | Current projection path clears selected projection | Effective publication, Tool/Edit contributions, active projection, graph binding, diagnostics payload all become unavailable | Yes | Provider |
| Callback captured before any lease | Existing provider action closures are token-aware | Remains a permanent no-op after later binds | Yes | Provider callbacks |
| Tool/Edit callback captured on A, invoked after B | No neutral callback contract exists | Permanent no-op; original callback not invoked | Yes | Leased publication wrapper |
| Callback removed during same-identity update | No neutral callback contract exists | Old wrapper becomes stale even though token is unchanged | Yes | Leased publication wrapper |
| Callback replaced under same ID | No neutral callback contract exists | Old wrapper no-ops; new wrapper invokes only new original callback | Yes | Leased publication wrapper |
| Legacy projection publication | Owns current projection lease directly | Adapts into neutral base, while existing renderer-specific state remains one attachment on the same token | Yes | Compatibility adapter + provider |
| Legacy `publishProjectionSurface` same-identity call | Preserves projection token; returns no-op cleanup | Must map to neutral **update**, preserve the singular lease token, and return no-op cleanup — never allocate a fresh bind token | Yes | Legacy projection adapter |
| Legacy projection with tools but missing context | Current `projectionsEnabled` is false | Neutral mirror remains valid but those tool launchers are disabled with a deterministic reason; current projection host remains disabled | Yes | Compatibility adapter |
| Contradictory legacy identity/config | Current projection validation disables it | Neutral validator rejects effective publication; prior capabilities clear | Yes | Compatibility adapter + SIH-01 validator |
| AppChrome `pageActions` | Rendered directly as Tool drawer buttons | Still render in the same DOM/order; mirrored as lease-bound Tool command contributions and execute through guarded callback | Yes | AppChrome compatibility bridge |
| AppChrome `editorTools` pinned actions | Rendered directly in Edit drawer | Same DOM/order; mirrored as top-level lease-bound Edit commands targeted at current Canvas work object | Yes | AppChrome compatibility bridge |
| AppChrome editor sections | Rendered directly with title/default-open/panel | Actions mirrored with exact group/order; `defaultOpen`, `pressed`, and `panel` remain legacy render-only state | Yes | AppChrome compatibility bridge |
| Chrome fragment mounts before a lease | Current props render independently | Registration attempt is a permanent no-op; publisher callback identity changes on valid lease so the mounted bridge republishes | Yes | Provider + AppChrome effect |
| Chrome fragment changes under same lease | Current props rerender | Replace fragment by registration token; stale fragment cleanup cannot erase newer fragment | Yes | Provider |
| Fragment creates duplicate/contradictory neutral IDs | No shared validation | Effective publication invalid; active state clears; legacy DOM remains present but actions are disabled/no-op rather than bypassing the lease | Yes | Composition + AppChrome bridge |
| Current active Tool on same-identity update | Current provider rebuilds label/size or clears | Revalidate from current authorized contribution/projection; preserve only if still enabled and coherent | Yes | Provider |
| Current graph reference / diagnostics binding | Current token-bound attachments | Remain only while current token and effective publication authorize the legacy path; clear on invalid/identity change | Yes | Provider |
| Late provider-owned async completion from A | Existing graph-reference paths guard some completions | Must re-check A token and never attach result to B | Yes | Provider integration |
| LocalStorage | Projection opens are not persisted | No new key or serialized lease/publication state | Yes | Storage assertion |
| Normal Plan/Ingest/Build/AppChrome behavior | Existing UI and projection host | Equivalent under valid current inputs; no host DOM/CSS movement | Yes | Regression/component suites |

### Ordered adversarial sequences

| Sequence | Required safe outcome | Owning proof |
|---|---|---|
| Bind Plan A → attach editor fragment A → open Tool A → bind Build B → run A cleanup | B remains current; no A Tool/Edit/projection/binding state survives | V2, V4 |
| Bind Plan A → capture Tool command and Edit command → bind Build B → invoke both | Neither original callback runs | V5 |
| Bind Plan A → capture command x → same-identity update removes x → invoke old wrapper | Old wrapper no-ops although lease token is unchanged | V5 |
| Bind Plan A → capture command x using callback 1 → same-identity update keeps x but replaces callback with callback 2 → invoke old then new wrappers | Callback 1 remains untouched; callback 2 runs once through the new wrapper | V5 |
| Bind Plan A → open recap → same-identity valid update changes label/size | Token preserved; active projection rebuilt from current values | V3, V6 |
| Bind Plan A → open Tool + attach graph binding → same-identity invalid update → corrected same-identity valid update | Invalid state exposes nothing and clears attachments; corrected publication recovers under the same lease; binder must re-register because registrar callback identities changed | V3, V6 |
| Bind Plan A → AppChrome fragment F1 → AppChrome fragment F2 → run F1 cleanup | F2 remains composed; current actions still execute | V4 |
| Bind Plan A → AppChrome fragment introduces duplicate Tool ID → invoke legacy button | Effective publication is null; button is disabled/no-op; no raw callback bypass | V4, V5 |
| Capture `publishAppChromeCompat` before any lease → bind Plan → invoke stale publisher | It remains a no-op; mounted current bridge republishes through the new callback identity | V4 |
| Bind Plan A → start deferred graph relationship resolution → bind Build B → resolve A promise | No graph content or projection state attaches to B | V6 |
| Bind Plan A → bind explicit null → invoke A close/open/register/command closures | All are no-ops; explicit empty lease stays empty | V2, V5, V6 |
| Bind contradictory legacy publication after valid Plan | Prior effective publication and active state clear; contradiction cannot retain or partially merge old values | V3 |
| Native-source lease → attempt Chrome fragment register/cleanup | Fragment is ignored; cleanup is a no-op; effective publication unchanged | V1, V4 |
| Legacy `publishProjectionSurface` same-identity after prior bind | Singular token preserved; returned cleanup is a no-op; attachments remain under the same token | V3, V7 |

## §4 Files in scope (allowlist)

| Action | Path | Purpose: how this establishes or proves §1 |
|---|---|---|
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx` | Make the existing provider the singular neutral lease owner; bind all legacy projection/binding state to the same token; expose guarded effective publication |
| Modify | `apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts` | Add the neutral runtime state/actions and mark current projection APIs as compatibility paths without removing them |
| Modify | `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx` | Prove provider-level interleavings, active projection revalidation, binding cleanup, and predecessor behavior |
| Create | `apps/live-control-ui/src/agentInteraction/surfaceInteractionLease.ts` | Isolate pure lease/composition/callback-guard mechanics from React rendering |
| Create | `apps/live-control-ui/src/agentInteraction/surfaceInteractionLease.test.ts` | Exhaustive bind/update/invalidate/callback state-machine proof |
| Create | `apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.ts` | Pure temporary adapters for legacy projection publications, AppChrome fragments, and singleton route compatibility publications |
| Create | `apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.test.ts` | Pin exact predecessor mapping, omissions, ordering, disabled reasons, and validation outcomes |
| Create | `apps/live-control-ui/src/agentInteraction/usePublishSurfaceInteraction.ts` | Provide the token-safe bind-on-identity/update-on-config publisher pattern for complete neutral or route-compat publications |
| Modify | `apps/live-control-ui/src/chrome/AppChrome.tsx` | Mirror current props into the current compatibility lease and execute the same visible actions through lease-guarded contributions while retaining existing DOM |
| Create | `apps/live-control-ui/src/chrome/AppChrome.surfaceInteraction.test.tsx` | Prove DOM/order equivalence, valid click equivalence, stale click suppression, and invalid-composition fail-closed behavior |
| Modify | `apps/live-control-ui/src/App.tsx` | Bind exact empty/base compatibility publications for current AppChrome-only routes that otherwise have no projection publisher (`index`, `surface`, `tiptap-callout-spike`) |
| Create | `apps/live-control-ui/src/App.surfaceInteraction.test.tsx` | Prove AppChrome-only routes acquire an exact lease and page/editor actions do not publish into a missing or previous lease |

**Bounded discovery exception:**

- Directory: `apps/live-control-ui/src`
- Maximum additional paths: 2
- Allowed path kinds: existing focused test files only; no production file
- Decision rule for including one: a current Plan, Build, or Ingest publisher regression cannot be proven through `AgentInteractionProvider` tests and the named existing test is the owning component boundary

If a production path outside the table is required, stop and report it. Do not silently modify Plan, Build, Ingest, Canvas, projection renderer, CSS, or storage production files.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/surfaceInteraction/types.ts` and `publication.ts` | SIH-01 contract is the predecessor authority; amend authority first if it is insufficient |
| `apps/live-control-ui/src/planSurface/projection/AdaptiveProjectionContainer.tsx` and renderer switch files | Projection host ownership/catalog are SIH-03a/b |
| Tool/Edit drawer extraction or CSS movement | Shared host DOM is SIH-04/SIH-05 |
| `PlanSurfaceShell` native publication | Plan remains a legacy compatibility publisher until post-SIH-06 recomposition |
| `BuildSurfacePage` native Tool/Edit publication or Find Existing | BLD-REF-01/02 |
| Graph Reference contract or graph query behavior | Already-owned neutral capability; preserve regression only |
| Canvas session, dirty state, selection, save, admission | Canvas authority is independent and unchanged |
| Graph writes, Graph Review confirmation, identity resolution | Campaign Supergraph/Kernel authority |
| Projection binding value typing or renderer authorization catalog | SIH-03b |
| AppChrome `panel`, `pressed`, `defaultOpen` neutral modeling | Deliberately retained in legacy render path until host extraction proves need |
| Callback error capture, cancellation, retries, loading indicators | Host/runtime successors; SIH-02 only gates invocation and provider-owned completion application |
| Lease/publication persistence, localStorage, URL state | Separate durable/local-state capability; explicitly forbidden here |
| Provider rename or broad `agentInteraction` reorganization | Adds review surface without changing the invariant |
| New diagnostics UI or validation issue panel | New product surface; invalid state is exposed as no effective publication in this slice |

## §6 Implementation contract and conditional matrices

### 6.1 Public provider contract

The existing `AgentInteractionProvider` remains the only app-scoped owner. Add neutral state/actions without removing current projection compatibility actions.

Conceptual public shape:

```text
surfaceInteractionPublication: SurfaceInteractionPublication | null

publishSurfaceInteractionPublication(publication: unknown | null)
  -> cleanup function bound to the created lease token

updateSurfaceInteractionPublication(publication: unknown)
  -> current-token, exact-same-identity update only

publishAppChromeCompatibility(fragment)
  -> cleanup function bound to both current surface token and fragment token
```

Names may vary only if they remain explicit and cannot be confused with a second provider or partial neutral public API. The PR handback must document final names.

Current compatibility actions remain callable:

- `publishProjectionSurface`
- `updateProjectionSurfaceConfig`
- `registerGraphReferenceBinding`
- `registerToolProjectionPayload`
- `openTool`
- `openGraphReference`
- `expandContent`
- `close`

`publishProjectionSurface` / `updateProjectionSurfaceConfig` become adapters into the same neutral lease; they must not retain an independent token or independent current-surface owner.

#### Legacy projection API adapter matrix (mandatory)

Plan/Build/Ingest continue to call the legacy APIs. Those calls must preserve today's token-continuity contract by mapping onto the singular neutral lease as follows — they must **not** blindly forward every non-null publish through the neutral bind API:

| Legacy call | Neutral effect | Token | Returned cleanup |
|---|---|---|---|
| `publishProjectionSurface(null)` | Null bind → explicit empty lease | **New** singular token; prior state cleared first | Bound to the new empty-lease token |
| `publishProjectionSurface(pub)` when no current bound identity, or identity differs | Adapt `pub` → base publication → **bind** | **New** singular token; prior state cleared first | Bound to the new token |
| `publishProjectionSurface(pub)` when exact same identity as current bound identity | Adapt `pub` → **same-identity update** | **Preserve** singular token and bound identity | **No-op** cleanup (`() => undefined`) |
| `updateProjectionSurfaceConfig(pub)` | Same-identity update only (ignore/no-op when identity mismatches or no bound identity) | Preserve when update applies | N/A |

The neutral `publishSurfaceInteractionPublication` API itself always creates a fresh lease even when the supplied valid identity equals the prior identity. Same-identity continuity for Plan/Build effects is owned exclusively by this legacy adapter matrix and by `updateSurfaceInteractionPublication` / `updateProjectionSurfaceConfig`.

`usePublishSurfaceInteraction` is for complete neutral or AppChrome-only route compatibility publications in this slice. Plan, Build, and Ingest production files remain on the legacy projection APIs and are not migrated here.

### 6.2 Internal lease state

The provider/lease helper must retain enough internal state to distinguish:

- lease token
- bound exact identity | null
- lease source: `native` | `legacy_projection` | `legacy_route`
- raw canonical base publication | null
- current Chrome compatibility fragment + fragment token | null
- raw effective canonical publication | null
- lease-guarded effective publication | null
- validation issues/internal invalid reason (not a new public issue vocabulary)
- legacy projection attachment | null
- lease-bound graph-reference / diagnostics attachments
- active projection/content state

Only the lease-guarded effective publication is exposed as the neutral current publication.

**Singular token unification:** The provider replaces the current projection-surface registration `Symbol` with the singular neutral lease token. All compatibility attachments — legacy `ValidatedProjectionSurface`, Chrome fragment, graph-reference binding, diagnostics payload, and active projection — authorize against that same token. Implementing a second parallel token (neutral lease beside a retained projection-surface lease) is a stop condition.

The provider may retain SIH-01 validation issues internally for tests/debugging, but this slice must not invent public validation issue codes or add a user-facing diagnostics surface.

### 6.3 Bind contract

```text
Input:
  unknown neutral publication or null

Valid non-null input:
  validate through SIH-01
  allocate a fresh token
  clear old active projection/content and compatibility attachments before installation
  establish bound identity from canonical validated snapshot
  compose current allowed compatibility fragment (initially none)
  wrap callbacks and expose one effective publication

Invalid non-null input:
  allocate a fresh token
  clear old state before installation
  bound identity is null
  expose no effective publication
  cleanup remains token-safe

Null input:
  allocate a fresh explicit empty lease
  clear old state before installation
  expose no effective publication
```

A bind always creates a new lease, even if the supplied valid identity equals the prior identity. Same-identity continuity belongs to the update API (and to the legacy `publishProjectionSurface` same-identity adapter in §6.1). This prevents an accidental re-bind from inheriting stale attachments.

### 6.4 Update contract

The update callback must capture the lease token at the time the provider exposes it.

```text
Stale captured token:
  permanent no-op

Current token + valid exact same identity:
  preserve token and bound identity
  replace base publication
  recompose and revalidate effective publication
  revalidate active projection and authorized attachments

Current token + invalid publication:
  preserve token and prior bound identity
  expose no effective publication
  clear active projection and lease-bound attachments
  later corrected exact-same-identity update may recover

Current token + valid different identity:
  fail closed under current lease
  expose no effective publication and clear active/attached state
  do not adopt the new identity; caller must bind
```

A current-token different-identity update is a provider contract failure, not an implicit bind and not a reason to retain stale state.

### 6.5 Effective publication composition

For compatibility leases only:

```text
base publication
+ current Chrome compatibility Tool contributions
+ current Chrome compatibility Edit contributions
= candidate effective publication
-> SIH-01 validator
-> callback lease wrapping
-> exposed effective publication
```

Composition order is deterministic:

1. base Tool contributions in predecessor order;
2. AppChrome `pageActions` in prop order;
3. base Edit contributions;
4. AppChrome pinned Edit actions in prop order;
5. AppChrome section actions in section order then action order;
6. base Projections and bindings unchanged.

Do not silently rename or first-win duplicate IDs. Preserve predecessor IDs exactly. A duplicate or group contradiction invalidates the effective publication and clears active state.

A direct native lease must reject/ignore Chrome compatibility fragments. Legacy AppChrome props are not allowed to mutate a future native publication. This slice has no production native publisher; the lease helper must still prove the ignore/no-op path under `leaseSource === "native"`.

### 6.6 Lease-guarded callback contract

For every Tool command activation and Edit command in the exposed effective publication:

```text
wrapper captures:
  lease token
  contribution kind
  exact contribution ID
  original callback identity

on invocation:
  current token must match
  current raw effective publication must still contain the same contribution ID
  contribution kind/activation must still match
  current original callback identity must equal captured original callback
  contribution availability must still be enabled

otherwise:
  return undefined without invoking original callback
```

If authorized, return the original callback's result unchanged. Do not catch, translate, retry, or cancel its errors/promises.

This contract prevents stale invocation. It does not cancel arbitrary domain work after a callback was validly invoked. Any async completion that later mutates provider-owned state must independently re-check the token before applying.

### 6.7 Active projection and attachment revalidation

Any transition that leaves no valid effective publication clears:

- active Tool/content projection;
- active graph reference and projection state;
- graph-reference binding;
- diagnostics payload;
- any current Chrome compatibility contribution execution map.

On a valid same-identity update:

- an active legacy Tool remains only if the current effective publication still contains an enabled Tool contribution authorizing that exact legacy projection ID and the legacy attachment still authorizes it;
- label and preferred size are rebuilt from current values;
- removed, disabled, contradictory, or missing targets clear active state;
- Plan graph content remains only while the effective publication is valid and the existing Plan compatibility attachment still authorizes graph content;
- Graph Reference and diagnostics registrar function identities **must change when authorization changes** — including token-preserving invalid→valid and valid→invalid transitions — so mounted binder effects re-register after recovery. Token equality alone is not sufficient to keep a stale registrar closure live;
- the AppChrome compatibility publisher callback identity must likewise change when a lease becomes available or authorization toggles, so a mounted bridge that no-op'd before a lease can republish;
- cleared attachments do not silently resurrect from retained stale registrations.

### 6.8 Legacy projection publication adapter

Grounding source: `ProjectionSurfacePublication`, `SurfaceConfig`, and current validator behavior.

Required mapping:

| Predecessor field/outcome | Neutral field/behavior | Transformation |
|---|---|---|
| `identity.surfaceId` / `identity.instanceKey` | `identity` | Preserve exact strings; no re-encoding or labels |
| `config.id` | publication `surfaceId` | Preserve `config.id`; disagreement with identity is intentionally rejected by SIH-01 |
| `config.label` | publication `label` | Preserve exact label |
| `config.canvas.documentId` string | `canvas` | `canvasId: "markdown-canvas"`; work object `{ kind: "document", id: documentId }` |
| null/absent document ID | `canvas: null` | No invented work object |
| non-null `config.context` | `agentContext` | label from `headerLabel`; campaign ID exact; document ID from canvas; Plan session uses `liveSession`, Ingest uses `ingestSession`; ambient summary is bounded config label/header text; pointers empty |
| null `config.context` | `agentContext: null` | No fabricated context |
| each `config.tools[i]` | Tool + Projection descriptor | Exact ID/label/order; projection activation targets same ID; descriptor kind `tool`, preferred size exact, empty binding IDs |
| tool with missing legacy context | disabled Tool | Stable reason: `Required legacy projection context is unavailable.` |
| empty tools | empty Tool/Projection arrays | Valid honest empty publication |
| `theme`, `sessionDescriptor` | omitted | Not neutral lease/store state |
| current renderer payload registrations | legacy attachment | Remain token-bound in provider; not copied into opaque neutral bindings before SIH-03b |
| current `projectionsEnabled` | current host authorization attachment | Retained and additionally gated by valid effective neutral publication |

The adapter must be pure and covered by exact mapping tests. It must not import renderer components or inspect binding values.

### 6.9 AppChrome compatibility adapter

Grounding source: current `AppChromeAction`, `AppChromeTools`, and current rendered order.

**Page actions**

Each `pageActions[i]` maps to one Tool command contribution:

- `id`: exact `action.id`
- `label` / `eyebrow`: exact values
- `placement`:
  - `groupId`: `"legacy-page-tools"`
  - `groupLabel`: `"Page tools"`
  - `groupOrder`: `100`
  - `itemOrder`: `i`
- `availability`:
  - `disabled` true → disabled with `"Unavailable in the current legacy AppChrome state."`
  - otherwise enabled
- `activation`:
  - `command` → original `onClick` callback before provider lease wrapping

**Editor pinned actions**

Each pinned action maps to one top-level Edit command:

- placement `groupId`/`groupLabel`: `null`/`null`
- `itemOrder`: input order
- `target`: current base Canvas work object when present
- `invoke`: original `onClick` before lease wrapping

**Editor sections**

Each section action maps to one grouped Edit command:

- `groupId`: exact `section.id`
- `groupLabel`: exact `section.title`
- `groupOrder`: section index
- `itemOrder`: action index
- `target`: current base Canvas work object when present

If editor actions exist and the base publication has no Canvas work object, every mirrored Edit command **must** use the exact SIH-01 blank command target `{ kind: "", id: "" }` so validation emits `command_target_invalid`. Do not fabricate a document identity, do not omit `target`, and do not let raw AppChrome callbacks bypass the invalid effective publication.

`pressed`, `defaultOpen`, and `panel` remain legacy render-only fields. They are not copied into neutral metadata or opaque bindings.

### 6.10 AppChrome execution bridge

`AppChrome` continues to receive and render its current props and retains its current DOM, labels, grouping, open state, panel content, and CSS.

For execution only:

- resolve each visible page action to the matching current lease-guarded Tool command by exact ID;
- resolve each visible editor action to the matching current lease-guarded Edit command by exact ID;
- invoke the guarded callback, never the raw prop callback;
- when no unique current authorized contribution exists, render the existing action but disable it or make it an explicit no-op; do not bypass the store;
- existing explicit `disabled` remains disabled;
- normal valid current inputs must remain behavior-equivalent.

This is temporary compatibility wiring, not Tool/Edit host extraction. `AppChrome` remains the legacy DOM owner until SIH-04/SIH-05.

### 6.11 AppChrome-only route compatibility publications

Current routes that use AppChrome actions/tools but do not publish a legacy projection surface require a complete base lease:

| Route | Exact identity parts | Label | Canvas |
|---|---|---|---|
| `index` | `["index"]` | `Command Board` | `null` |
| `surface` / Live Control | `["surface", "live-control"]` | `Live Control` | `null` |
| `tiptap-callout-spike` | `["tiptap-callout-spike"]` | `Tiptap Callout Spike` | `{ canvasId: "tiptap-callout-spike", workObject: { kind: "spike", id: "tiptap-callout-spike" } }` |

Use SIH-01 identity construction. These are compatibility publishers only. They contribute no native Tool/Edit behavior themselves; AppChrome fragments supply current actions.

Do not add a universal AppChrome auto-bind: a parent-generated route lease must not race with or overwrite Plan, Build, or Ingest's exact legacy publication identity.

### 6.12 Failure, replay, trust, and persistence

```text
Failure behavior:
  invalid bind -> new empty/invalid lease; old state already cleared
  invalid composition -> effective publication null; active/attachments cleared
  stale cleanup/update/fragment publisher -> no-op
  current different-identity update -> current lease invalidated; requires bind
  callback throw/reject after authorized invocation -> propagate unchanged

Replay / idempotency:
  repeated bind -> new token each time; old cleanup stale
  repeated exact same update -> same token; equivalent effective publication
  corrected update after invalid same-identity update -> may recover same token
  repeated fragment publication -> newest fragment token wins

Trust boundary:
  Verifies through SIH-01: neutral structure, identity coherence, IDs, placement,
    availability, callbacks present, projection references, bounds
  Verifies in provider: exact lease token, current contribution/callback identity,
    compatibility attachment authorization
  Trusts without proving: callback domain authorization/side effects, opaque binding
    value semantics, Canvas admission, graph write permission, renderer correctness
```

#### A. State and fallback matrix

| Observable path | Initial / no lease | Exact success | Ordinary empty/miss | Dependency unavailable | Integrity/contract failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Neutral bind | Exposes null | New token + guarded publication | null input creates explicit empty lease | N/A | Invalid lease; prior state cleared | Old cleanup no-op | Rebind creates new token |
| Same-identity update | No-op without current bound identity | Token preserved, publication replaced | Empty collections remain valid | N/A | Effective null; token/identity retained | Stale captured update no-op | Corrected update may recover |
| Different-identity update | N/A | Not permitted | N/A | N/A | Current effective state cleared; caller must bind | Stale token no-op | Bind new identity |
| Chrome fragment | No-op and returns no-op cleanup | Composed into compatibility lease | Empty fragment removes Chrome contributions | Current Canvas missing with edit actions → invalid effective publication | Duplicate/group/target contradiction invalidates effective publication | Old fragment cleanup no-op | New fragment may recover |
| Tool/Edit invocation | No authorized callback | Current exact callback executes | Missing/disabled contribution no-op | N/A | Invalid publication no-op | Old lease or old callback identity no-op | User may invoke current wrapper again |
| Legacy Tool open | No-op | Opens current authorized projection | Missing/disabled tool no-op | Missing legacy context keeps disabled | Invalid effective or legacy attachment clears | Old open callback no-op | Current open may retry |
| Graph/diagnostics registration | No-op | Attaches under exact token and authorization | Missing required capability no-op | Legacy dependency unavailable remains null | Invalid effective clears | Stale registrar/cleanup no-op | Binder re-registers after callback identity changes |
| Provider-owned async completion | No state mutation | Applies under exact token | N/A | Truthful existing error state | N/A | Discard completion | Current operation may retry |

No fallback source is permitted. Invalid or unavailable neutral state never falls back to a previous publication or raw AppChrome callback.

#### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Lease identity | Exact validated `surfaceId` + `instanceKey` | No ambiguity | No |
| Display label change | Does not affect identity | N/A | No |
| Valid same identity | Update under same token | Exact comparison only | No |
| Valid different identity through bind | New token; old state cleared first | N/A | No |
| Valid different identity through update | Contract failure; current effective state clears; identity not adopted | N/A | No implicit bind |
| Invalid same-identity update | Prior bound identity retained internally; no effective publication | N/A | No stale publication |
| Contribution identity | Exact collection kind + exact ID | Duplicate invalidates whole effective publication | No first-win |
| Callback identity | Exact original function reference under exact contribution ID and token | Replaced function makes old wrapper stale | No |
| Cleanup/fragment token | Exact symbol equality | N/A | No wildcard/null token |
| Labels/normalized IDs/aliases | Never identity | Prohibited | No |

#### C. Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay behavior | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| Lease bind/update | None — React/provider memory only | None across reload | Rules above within one mount | Existing legacy APIs retained temporarily | Unmount/cleanup or PR revert |
| Effective publication | None | Rebuilt from current publisher inputs | Same update equivalent; bind creates fresh token | SIH-01 runtime type only | Clear lease |
| Chrome fragment | None | Rebuilt from current props | Newest fragment token wins | Existing props remain current render contract | Cleanup/unmount |
| Active projection/open state | Existing transient behavior only | No new persistence | Current provider semantics retained | No migration | Clear on transition |
| localStorage | No new key/value | Existing Agent thread storage unchanged | N/A | No schema change | N/A |

#### D. Predecessor-to-consumer mapping

Grounding sources:

- `apps/live-control-ui/src/agentInteraction/projectionSurfacePublication.ts`
- `apps/live-control-ui/src/planSurface/types.ts`
- `apps/live-control-ui/src/chrome/AppChrome.tsx`
- `apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx`

| Predecessor field/outcome | Real shape and optionality | Consumer field/behavior | Transformation | Proof |
|---|---|---|---|---|
| `ProjectionSurfacePublication.identity` | required exact strings | neutral identity | exact copy | Compat adapter tests |
| `SurfaceConfig.id` | required `SurfaceMode` | publication `surfaceId` | exact copy; mismatch remains invalid | Contradiction test |
| `SurfaceConfig.context` | `PlanContextDescriptor \| null` | neutral Agent context / tool availability | exact mapping described §6.8 | Mapping tests |
| `SurfaceConfig.tools` | ordered array `{id,label,size}` | neutral Tools + Projections | one-to-one exact order | Mapping tests |
| `SurfaceConfig.canvas.documentId` | optional string/null | neutral Canvas | exact document ID or null | Mapping tests |
| `ValidatedProjectionSurface.projectionsEnabled` | derived bool | legacy renderer attachment authorization | retained under same token; never sole lease authority | Provider tests |
| `AppChromeAction.disabled` | optional boolean, no reason | neutral availability | deterministic compatibility reason | Adapter tests |
| `AppChromeAction.pressed` | optional boolean | legacy render only | omitted from neutral publication | DOM equivalence test |
| `AppChromeAction.onClick` | required callback | neutral command callback | same original reference before lease wrapping | Identity/click tests |
| `AppChromeTools.pinnedActions` | optional array | top-level Edit commands | exact order | Adapter tests |
| `AppChromeTools.sections` | optional array with actions/defaultOpen/panel | grouped Edit commands + legacy render-only fields | exact group/action order; omit panel/defaultOpen | Adapter + DOM tests |
| Existing graph/diagnostics registrations | token-bound provider values | compatibility attachments | retain same value identity; reauthorize against effective publication | Provider tests |
| Existing `openTool` / `openGraphReference` callbacks | token-capturing context actions | same public behavior | use singular neutral token and effective publication gate | Regression/adversarial tests |

## §7 Evidence required to merge

| ID | Guarantee / invariant clause | Owning boundary | Evidence class | Command or scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|---|
| V1 | First bind, null bind, invalid bind, exact cleanup semantics; native lease ignores Chrome fragments | Pure lease helper | Contract | Focused `surfaceInteractionLease.test.ts` | Exact state/token transitions; no throw on unknown input; native-source fragment register/cleanup are no-ops | Any old publication survives bind/null/invalid; native lease accepts Chrome mutation |
| V2 | Different identity clears before replacement and stale cleanup cannot erase new lease | Provider integration | Adversarial | Plan A → Build B → A cleanup | B remains; A state absent | Any A state/cleanup affects B |
| V3 | Same-identity valid update preserves token; invalid update clears; corrected update recovers; legacy same-identity `publishProjectionSurface` preserves token and returns no-op cleanup | Helper + provider | Adversarial | Valid → valid → invalid → valid exact identity; legacy same-identity publish | Same token throughout; exposure/active state matches matrix; legacy publish cleanup is no-op | Token changes, stale publication survives, or recovery impossible |
| V4 | Chrome fragment composition is token-safe and deterministic | Compat helper + AppChrome/provider | Contract/adversarial | F1 → F2 → F1 cleanup; duplicate IDs; missing Canvas target; native ignore | F2 wins; invalid composition exposes null and blocks raw callback; native fragment ignored | Stale fragment clears newer or invalid bypasses store |
| V5 | Pre-lease, old-lease, removed, and replaced callbacks are permanent no-ops | Leased callback wrapper + component bridge | Adversarial | Capture/invoke sequences from §3 | Only current exact original callback runs | Any stale original callback invoked |
| V6 | Existing active projection, graph binding, diagnostics, and deferred provider-owned completion revalidate against one token; registrar identities change on authorization toggle | Provider integration | Adversarial/regression | Open/register/defer on A → update/switch → complete; invalid→valid recovery re-register | No stale attachment/result; current valid paths preserved; binders re-fire after recovery | Any stale result attaches or current path regresses |
| V7 | Legacy projection mapping is exact and no renderer/catalog semantics move early | Compat adapter | Contract | `surfaceInteractionCompat.test.ts` | Exact mapping/omissions/disabled reason; SIH-01 validates expected cases | Invented binding payload/catalog or hidden coercion |
| V8 | AppChrome normal DOM/order/click behavior remains equivalent while execution is lease-guarded | AppChrome component | Component/regression | `AppChrome.surfaceInteraction.test.tsx` | Same labels/groups/panels/open behavior; valid click once; stale click blocked | Normal current behavior changes or raw callback bypass remains |
| V9 | AppChrome-only routes bind exact compatibility leases | App route integration | Integration | `App.surfaceInteraction.test.tsx` | index/surface/spike identities exact; actions attach only to own lease | Parent route lease overwrites Plan/Build/Ingest or actions have no lease |
| V10 | SIH-01 contract remains green | Neutral contract | Regression | `npx vitest run src/surfaceInteraction` | All SIH-01 tests pass | Any contract regression |
| V11 | Current provider/projection/Plan/Build behavior remains equivalent | Existing consumers | Regression | Existing focused predecessor command below | All pass | New failure without explicit accepted baseline comparison |
| V12 | No persistence or second provider/store | Storage/static boundary | Contract/static | localStorage assertion + source guards | No new keys; no React provider/context under `surfaceInteraction`; one app owner | Any persisted lease or second owner |
| V13 | Typecheck/build and changed-path discipline | Repository | Build/static | Commands below | Green or truthful baseline comparison; only §4 paths | Unwaived new error or production path outside allowlist |

Run from `apps/live-control-ui` unless noted:

```bash
npx vitest run \
  src/agentInteraction/surfaceInteractionLease.test.ts \
  src/agentInteraction/surfaceInteractionCompat.test.ts \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/chrome/AppChrome.surfaceInteraction.test.tsx \
  src/App.surfaceInteraction.test.tsx

npx vitest run src/surfaceInteraction

npx vitest run \
  src/agentInteraction/projectionSurfacePublication.test.ts \
  src/agentInteraction/AgentInteractionProvider.test.tsx \
  src/planSurface/PlanSurfaceShell.test.tsx \
  src/buildSurface/BuildSurfacePage.test.tsx

npx vitest run src/graphReference src/agentInteraction

! rg -n 'createContext|function .*Provider|const .*Context' \
  src/surfaceInteraction --glob '!*.test.ts' --glob '!*.test.tsx'

! rg -n 'localStorage|sessionStorage' \
  src/agentInteraction/surfaceInteractionLease.ts \
  src/agentInteraction/surfaceInteractionCompat.ts \
  src/agentInteraction/usePublishSurfaceInteraction.ts

npx tsc -b --force
npm run build
git diff --check

git diff --stat 390aa0bce872a74a0ac325a2dd7b9d9dd0025d9b...HEAD -- \
  apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.tsx \
  apps/live-control-ui/src/agentInteraction/agentInteractionTypes.ts \
  apps/live-control-ui/src/agentInteraction/AgentInteractionProvider.test.tsx \
  apps/live-control-ui/src/agentInteraction/surfaceInteractionLease.ts \
  apps/live-control-ui/src/agentInteraction/surfaceInteractionLease.test.ts \
  apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.ts \
  apps/live-control-ui/src/agentInteraction/surfaceInteractionCompat.test.ts \
  apps/live-control-ui/src/agentInteraction/usePublishSurfaceInteraction.ts \
  apps/live-control-ui/src/chrome/AppChrome.tsx \
  apps/live-control-ui/src/chrome/AppChrome.surfaceInteraction.test.tsx \
  apps/live-control-ui/src/App.tsx \
  apps/live-control-ui/src/App.surfaceInteraction.test.tsx

git diff --name-only 390aa0bce872a74a0ac325a2dd7b9d9dd0025d9b...HEAD
```

### Minimal live / dogfood proof

Not required by default — this slice intentionally adds no new visible affordance and automated component/integration tests own the normal-equivalence and stale-interleaving guarantees.

If the implementation changes any normal visible behavior, the PR must stop and obtain an explicit handoff amendment rather than treating manual observation as permission.

### Baseline failure protocol

For any required command already failing on base:

1. run the exact command on base and head in the same environment;
2. record exact counts and failures;
3. do not call the gate green;
4. prove no new failures or request an explicit operator waiver;
5. distinguish author-local, independently rerun local, CI, and manual results.

## §8 Required PR description and handback

The PR description must remain current and include:

1. §1 Mission copied exactly.
2. §1 merge-ready invariant copied exactly.
3. The V1–V13 evidence ledger with produced result and provenance.
4. Base SHA and head SHA.
5. Actual changed paths and focused diff stat limited to §4.
6. Every §7 command and exact result.
7. Provenance of each result: author-local, independently rerun local, CI, or manual.
8. Baseline failures with base/head comparison.
9. Explicit operator waivers; none when none exist.
10. Paths outside §4; none or a stop report.
11. Stop conditions encountered and resolution; none when none exist.
12. Final public API names for neutral bind/update/current publication and AppChrome compatibility registration.
13. Confirmation that current projection APIs are compatibility attachments to the same token, not a second store.
14. Confirmation that callback wrappers revalidate exact original callback identity after same-identity updates.
15. Confirmation that legacy `publishProjectionSurface` same-identity calls preserve the singular token and return no-op cleanup.
16. Successor capabilities deferred and still false: SIH-03a/b, SIH-04, SIH-05, BLD-REF-01/02, Plan native recomposition, persistence.
17. Confirmation that the authoritative handoff was implemented without compressed or omitted constraints.

A generic Summary/Test Plan body does not satisfy this section.

## §9 Acceptance rubric

The reviewer accepts only when every bullet is true and each behavioral bullet names its §7 proof.

1. Exactly one independently useful capability was delivered: one neutral app-scoped lease/store with required temporary bridges — V1–V9.
2. One internal token owns the effective neutral publication, legacy projection attachment, Chrome fragment, active projection, graph binding, and diagnostics payload — V1, V2, V4, V6.
3. Valid same-identity updates preserve the token and revalidate current state — V3, V6.
4. Null, invalid, and identity-changing transitions never retain prior active capabilities — V1–V3, V6.
5. Stale cleanup, registration, invocation, and provider-owned async completion are no-ops — V2, V4–V6.
6. Removed/replaced callbacks under the same token are stale by original function identity — V5.
7. Current projection publication is adapted into the neutral lease without creating a second owner — V6, V7, diff inspection.
8. Legacy `publishProjectionSurface` same-identity continuity is preserved (token + no-op cleanup) — V3.
9. Current AppChrome props remain the render input but never bypass lease-guarded execution — V4, V5, V8.
10. AppChrome-only routes acquire exact compatibility leases without racing Plan/Build/Ingest publishers — V9.
11. No renderer catalog, host DOM extraction, native Build feature, Canvas authority move, graph write, or persistence entered the PR — V7, V12, V13.
12. SIH-01 and current focused predecessor suites remain green or have an explicit accepted baseline comparison — V10, V11, V13.
13. No production path outside §4 changed — V13.
14. The PR description exposes a complete truthful evidence ledger and exact provenance.
15. SIH-03a remains the next named successor and is not claimed as delivered.

### Stop conditions

Stop and report rather than expanding if implementation discovers:

- the provider cannot remain the singular owner without creating a second Context/provider/store;
- the singular lease token cannot replace the projection-surface token without a parallel second owner;
- legacy `publishProjectionSurface` same-identity continuity cannot be preserved without changing Plan/Build production files;
- current projection state cannot be attached to the neutral token without moving Projection host types or renderer selection;
- current renderer payload dependencies must become typed neutral bindings before SIH-03b;
- AppChrome compatibility requires placing ReactNode, panel, pressed, or defaultOpen into the neutral publication;
- Plan, Build, Ingest, Canvas, projection renderer, CSS, storage, or server production files outside §4 must change;
- callback safety requires changing callback signatures or cancelling arbitrary domain operations after valid invocation;
- a same-identity update cannot distinguish removed/replaced callbacks from current callbacks;
- a route compatibility publisher races with or overwrites a more exact Plan/Build/Ingest lease;
- invalid composition can still execute raw AppChrome callbacks;
- Graph Reference or diagnostics authorization cannot re-register after invalid→valid recovery without a second owner;
- a new localStorage/URL/server schema appears necessary;
- required owning-boundary tests cannot reproduce the A→B stale sequences;
- a required command has an unwaived new failure;
- any production path outside §4 or the test-only bounded exception is needed.

Use this stop report shape:

```text
Stop condition:
Why the current mission cannot absorb it:
Invariant clause affected:
Required evidence now missing:
New public/durable contract discovered:
Affected observable paths or ownership layers:
Proposed successor slice:
Authority/tracker amendment needed:
```
