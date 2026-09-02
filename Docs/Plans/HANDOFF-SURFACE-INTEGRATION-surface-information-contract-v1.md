---
pr_body_template: |

  ## Handoff pointer

  * Conversation/workstream: SURFACE-INTEGRATION / SI-2
  * Flow: SURFACE-INTEGRATION
  * Direction: DESIGN → CODE → REVIEW
  * Handoff: `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md`
  * Branch / PR: `agent/surface-information-contract-v1` / `SURFACE-INTEGRATION: establish surface information contract v1`

  ## Verification pointer

  * Base: `c77260b044873f3ccfb5b77e7fce643539ca9abf`
  * Predecessor: PR #675 merged @ `c77260b044873f3ccfb5b77e7fce643539ca9abf`
  * Changed paths: HANDOFF §4
  * Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Surface Information Contract v1

**Created:** 2026-09-02
**Status:** ACTIVE — SURFACE-INTEGRATION SI-2
**Canonical handoff path:** `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md`
**Conversation/workstream:** `SURFACE-INTEGRATION / SI-2`
**Flow / owner:** `SURFACE-INTEGRATION`
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** `c77260b044873f3ccfb5b77e7fce643539ca9abf`
**Predecessor:** PR #675 / SI-1 merged at `c77260b044873f3ccfb5b77e7fce643539ca9abf`; final implementation head `e71b637a3d09da439d069a7eafeb2f4be8dc31a2`; six formal review cycles
**PR title:** `SURFACE-INTEGRATION: establish surface information contract v1`

> Repository law: [`AGENTS.md`](../../AGENTS.md).
> Parent program: [`ROADMAP-surface-integration.md`](../Roadmaps/ROADMAP-surface-integration.md).
> Semantic authority: [`CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md).
> Existing shared-interaction authority: [`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

---

## §0 Steward design ruling

SI-1 proved which assembled runtime and durable authorities DungeonBuddy is actually connected to.

SI-2 establishes a different boundary:

```text
How does changing information from one known authority
reach a Surface truthfully and reactively?
```

The answer is **not** a universal Surface datastore and **not** a larger `SurfaceInteractionPublication`.

DungeonBuddy has two separate concepts:

```text
Surface Interaction
  structural capabilities / commands / chrome publication

Surface Information
  changing observations
  provider + authority identity
  subject + scope
  authority revision
  loading / ready / empty / stale / unavailable / integrity error
  observation generation
  provenance
  inspection/navigation identity
  diagnostics
  reactive delivery
```

A Surface Information channel observes **one information projection from one authority**.

SI-2 does **not** modify `PlanSurfaceShell` or repair the Plan graph lens. It establishes a primitive under which the future SI-3 panel can remain structurally stable while the information it renders changes reactively. That is the architectural response to OC-020.

### Explicit anti-goals

SI-2 does not create a universal data/provider registry; move any authority; define commands; introduce a backend API; persist Surface Information; add localStorage/sessionStorage; modify AppChrome; repair Plan's graph panel; adopt the contract in product Surfaces; modify PR #674; decide Ingest architecture; or thaw feature work.

SI-3 remains the first real product adoption.

---

# §1 Mission and merge-ready invariant

## Mission

A DungeonBuddy information provider can expose one authority-owned observation through a neutral, reactive channel so a consumer can determine what it is observing, which provider/authority/subject/scope applied, whether the observation is loading/ready/empty/stale/unavailable/integrity-invalid, which authority revision was observed when applicable, which local observation generation is current, what provenance and inspection identities accompany it, and why it cannot currently be trusted — without using AppChrome publication identity as the reactivity mechanism.

## Merge-ready invariant

For one immutable Surface Information channel descriptor:

> **Every accepted observation produces a new monotonically increasing snapshot generation, preserves explicit provider/authority/subject/scope identity, distinguishes all contract states without silent fallback, and notifies subscribers independently of structural Surface Interaction publication; a stale or superseded asynchronous observation can never overwrite a newer accepted observation.**

The channel is runtime-only. It owns no domain data and performs no durable mutation.

---

# §2 Context, authority, and lane

| Field | Required content |
| --- | --- |
| Parent authority | `ROADMAP-surface-integration.md`; `ARCHITECTURE-surface-interaction-layer.md`; Of Conks OC-020 evidence carried by SI-1 |
| Base revision | `c77260b044873f3ccfb5b77e7fce643539ca9abf` |
| Named successor | **SI-3 — Graph lens reference implementation (Plan/Build rich panel)** |
| What remains false | Plan graph rich panel can still exhibit OC-020; no production provider uses Surface Information; Ingest persistence disposition remains unresolved; cross-surface adoption remains false |
| Branch | `agent/surface-information-contract-v1` |
| Parallel lanes | PR #674 remains parked/open; Agent Interaction, Play Ask, shared API, and agent server paths are read-only |
| Runtime/state ownership | Browser-memory-only channel objects; no durable state |
| Backward-looking predecessor sync | Mark SI-1 COMPLETE with #675 merge/final-head/six cycles; mark SI-1 DONE and SI-2 CURRENT in the SURFACE-INTEGRATION roadmap |
| Stable authorities not requiring sync | `ROADMAP-con-ready.md` still truthfully says SURFACE-INTEGRATION blocks feature dispatch through SI-6 |

### Re-anchor facts this slice must preserve

```text
main              c77260b044873f3ccfb5b77e7fce643539ca9abf
SI-1 / PR #675    merged; final implementation head e71b637a…; six review cycles
SI-2              current next slice
#674              open and PARKED
feature freeze    unchanged until SI-6 acceptance
```

---

# §3 Observable paths and adversarial sequences

Covered in [`CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md) and owning-boundary tests.

Required adversarial sequences:

- **A.** begin A → begin B → commit B READY → commit A READY: A returns false; snapshot remains B; no notification.
- **B.** READY X then READY X again: new generation, new snapshot object, subscriber notification. No semantic dedupe.
- **C.** `publishLoading=false`: visible snapshot retained; new ticket still supersedes; successful commit creates next generation.
- **D.** READY then unavailable: UNAVAILABLE, never silent prior READY. STALE is the only explicit retain-previous path.
- **E.** begin A → dispose → commit A: rejected; no generation change; no notification.

---

# §4 Files in scope — write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md` | This implementation/review contract |
| Modify | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-runtime-preflight-v1.md` | Backward-looking SI-1 completion sync |
| Modify | `Docs/Roadmaps/ROADMAP-surface-integration.md` | SI-1 DONE; SI-2 CURRENT; freeze preserved |
| Create | `Docs/Design/CONTRACT-surface-information-v1.md` | Durable semantic authority |
| Modify | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` | Companion-boundary statement |
| Create | `apps/live-control-ui/src/surfaceInformation/types.ts` | Neutral types |
| Create | `apps/live-control-ui/src/surfaceInformation/channel.ts` | Runtime reactive channel |
| Create | `apps/live-control-ui/src/surfaceInformation/index.ts` | Narrow public exports |
| Create | `apps/live-control-ui/src/surfaceInformation/channel.test.tsx` | Owning behavior + React interoperability |
| Create | `apps/live-control-ui/src/surfaceInformation/boundaries.test.ts` | Architecture/import/persistence boundary evidence |

Maximum additional write paths: **0**. No package or lockfile change is expected.

---

# §5 Explicitly out of scope / collision boundary

Do not touch: `PlanSurfaceShell.tsx`, `AppChrome.tsx`, `surfaceInteraction` production contract files, `agentInteraction/**`, `playSurface/**`, `api/**`, `apps/live_control_server/**`, package/lockfiles, `Docs/Sources/design-agent/**`, `ROADMAP-con-ready.md`.

If a product adoption is required to make the primitive work, stop. That is SI-3.

---

# §6 Implementation contract

Normative types and channel API live in [`CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md) and `apps/live-control-ui/src/surfaceInformation/`.

Factory: `createSurfaceInformationChannel<T>(descriptor)`.

Rules that the implementation must satisfy:

- One declared v1 authority per channel; provider ≠ authority.
- Descriptor identity is immutable for channel life; blank required strings are rejected at creation.
- Initial snapshot is generation 0 / loading.
- `getSnapshot()` is referentially stable between accepted observations and a new object after every accepted visible observation.
- `beginObservation` invalidates the previous ticket; default publishes loading; `publishLoading=false` retains the visible snapshot.
- `commit` of the current ticket with a non-loading state increments generation, notifies once, consumes the ticket, returns true.
- Stale/foreign/consumed/disposed tickets return false with no snapshot change and no notification.
- Equivalent semantic states are still two observations.
- `dispose` invalidates the current ticket, clears listeners, and prevents future begin/commit.
- Production `surfaceInformation` code must not import React.
- `useSyncExternalStore(channel.subscribe, channel.getSnapshot)` is proven in tests only.

---

# §7 Evidence required to merge

From `apps/live-control-ui`:

```bash
npm test -- src/surfaceInformation/channel.test.tsx src/surfaceInformation/boundaries.test.ts
npm test -- src/surfaceInteraction/publication.test.ts src/surfaceInteraction/boundaries.test.ts
npm test
npm run typecheck
npm run build
```

From repository root:

```bash
git diff --check
git diff --name-only c77260b044873f3ccfb5b77e7fce643539ca9abf...HEAD
```

Actual changed paths must reconcile exactly with §4.

If the full UI test/typecheck/build floor fails for a reason not introduced by this PR: run the same command on base `c77260b…`, record both results, prove head adds no failure.

No product-adoption dogfood is required. SI-3 is the first assembled product proof.

---

# §8 Required review handback

Record: review cycle + exact head; §1 invariant disposition; SI-1 predecessor sync result; descriptor/state/channel vs §6; generation and ticket semantics; same-semantic-observation witness; A/B/late-A witness; React `useSyncExternalStore` witness; dispose/late-completion witness; state vocabulary evidence; test/typecheck/build commands and results; changed paths vs §4; paths outside §4; #674 collision; `surfaceInteraction` unchanged; no backend/API/persistence/provider registry; SI-3 unimplemented; freeze unchanged; prior finding ledger on re-review.

---

# §9 Acceptance rubric

* [ ] SI-1 is backward-synced as COMPLETE / merged #675 @ `c77260b044873f3ccfb5b77e7fce643539ca9abf`, six review cycles.
* [ ] Roadmap says SI-1 DONE and SI-2 CURRENT without pre-marking SI-2 complete.
* [ ] One Surface Information v1 semantic contract exists.
* [ ] One React-neutral runtime channel primitive implements that contract.
* [ ] Descriptor identity is immutable for channel life.
* [ ] Authority and provider are distinct; one channel names exactly one authority.
* [ ] READY / EMPTY / STALE / UNAVAILABLE / INTEGRITY_ERROR remain distinct.
* [ ] Authority revision and local observation generation are not conflated.
* [ ] Every accepted visible observation receives a strictly newer generation.
* [ ] Equivalent observations are not silently deduped.
* [ ] `getSnapshot()` is referentially stable between changes and different after accepted changes.
* [ ] Superseded async tickets cannot overwrite newer observations; consumed tickets cannot replay; dispose prevents late mutation.
* [ ] React `useSyncExternalStore` can consume the channel directly.
* [ ] No React dependency exists in production `surfaceInformation` code.
* [ ] No backend/API/persistence, no `SurfaceInteractionPublication` production changes, no product provider adoption, no #674-owned path.
* [ ] Actual changed paths remain inside §4.
* [ ] SI-3 remains the named first product adoption. Feature freeze remains unchanged.

---

# Stop conditions

Stop if SI-2 needs `PlanSurfaceShell`/`AppChrome`, a `SurfaceInteractionPublication` public type change, a production React provider/hook, a backend route, durable storage, multi-authority channels, a provider registry, lockfile changes, any #674 path, or another path outside §4.

---

# Dispatch summary

```text
Flow: SURFACE-INTEGRATION
Slice: SI-2 — Surface Information Contract v1
Base: c77260b044873f3ccfb5b77e7fce643539ca9abf
Branch: agent/surface-information-contract-v1
PR: SURFACE-INTEGRATION: establish surface information contract v1
Successor: SI-3 — Graph lens reference implementation
Feature freeze: remains in force through SI-6
```
