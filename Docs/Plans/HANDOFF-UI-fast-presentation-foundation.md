---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI Presentation Substrate Sidequest
  - Flow: UI
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-UI-fast-presentation-foundation.md
  - Branch / PR: one serial implementation PR from activation-time main
  - PR topology: serial

  ## Verification pointer
  - Design authority / head: UI sidequest plan merged by PR #755 at fb7437aa763f32cc98cb26b06911558deb41f761
  - Changed paths: exact §4 allowlist only
  - Verification: npm UI workshop build + focused Vitest + typecheck + production Vite build + diff checks

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — UI fast presentation foundation

**Created:** 2026-09-25
**Status:** ACTIVE — PR #755 and #756 merged; activation gate verified on `main@f430dec3ca81a93f554ff9cd546693a1d1e4dd0b`
**Canonical handoff path:** `Docs/Plans/HANDOFF-UI-fast-presentation-foundation.md`
**Conversation/workstream:** `UI Presentation Substrate Sidequest`
**Flow / owner:** `UI`
**Direction:** DESIGN → CODE → REVIEW
**Design authority base:** `fb7437aa763f32cc98cb26b06911558deb41f761` — PR #755 merge
**Activation gate:** PR #755 merged at `fb7437aa763f32cc98cb26b06911558deb41f761`; fresh-main re-anchor confirms no conflicting frontend-foundation lease and Ladle remains compatible with the existing Vite/React toolchain
**Activation record:** PR #756 merged at `f430dec3ca81a93f554ff9cd546693a1d1e4dd0b`; no open PR claims the frontend package/lockfile; `@ladle/react@5.1.1` requires React ≥18, Vite ^6.0.5, Node ≥20, and the target host has Node 20.20.2 available
**Dispatch base rule:** fresh current `main` containing this checked-in handoff after the activation gate is satisfied; record the exact implementation branch base at dispatch/review rather than trying to self-reference it inside this main commit.
**PR topology:** `serial`
**PR authorization:** once ACTIVE, open/update exactly one implementation PR for this capability without asking; no successor/repair PRs
**PR title:** `UI: add fast presentation workshop`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

> Handoff lifecycle: this file landed on `main` as BLOCKED. The steward has now
> re-anchored and verified the activation gate. Its §4 lease applies to the one
> serial UI-F1 implementation lane from activation-time `main`.

## §1 Mission and merge-ready invariant

**Mission:** A frontend developer can start one backend-free UI workshop and restyle a small set of Buddy presentation primitives through semantic tokens so that visual iteration is immediate on the target laptop.

**Merge-ready invariant:** The workshop, four primitive presentations, and token layer run entirely from static frontend code, add no production authority/state dependency, preserve the existing production build, and expose one semantic styling vocabulary rather than route-specific hardcoded paint.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. Tokens, four primitives, and Ladle are one capability only insofar as they jointly prove the backend-free visual-edit loop; no production consumer migrates in this slice. |
| Most likely adversarial sequence | Add workshop dependency → stories accidentally import production providers/API → workshop now requires live context or network → low-power workflow is lost. |
| Will §7 actually detect that failure? | Yes. Static story imports are source-guarded, workshop is launched with backend services off, and production build/typecheck are rerun. |
| Easiest owning boundary to under-test | The workshop boundary: a story can appear static while importing a provider that performs hidden runtime work. |
| What PR topology is authorized, and why is it safe? | Serial. Package files and the new `src/ui` seam are central enough that parallel foundation PRs would create avoidable lockfile/API churn. |
| Fact that forces stop/split | Ladle requires nontrivial Vite replacement/config surgery, stories need production providers/network state, or the primitive set expands beyond the four named primitives to satisfy the mission. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md`; `Docs/Design/ui-language/DESIGN-interaction-layer-language.md` |
| Design authority base | `fb7437aa763f32cc98cb26b06911558deb41f761` |
| Activation gate | satisfied on `main@f430dec3ca81a93f554ff9cd546693a1d1e4dd0b`; no package/lockfile collision; Ladle 5.1.1 compatible with React 19/Vite 6 under Node 20.20.2 |
| Dispatch base rule | fresh current main containing this handoff after activation; exact branch base recorded at dispatch/review |
| Predecessor contract | Existing React 19 / Vite 6 / Vitest frontend; no existing component workshop |
| Exact input consumed | Static React props only; no server DTO fetch, provider state, database, or environment-specific product state |
| Named successor | UI-F2 — representative World-object showroom using real Buddy view-model fixtures |
| What remains false | No production surface uses the new primitives; no ObjectSheet migration; no Base UI; no visual regression suite |
| Explicit non-goals | Tailwind; CSS-in-JS; Storybook; Base UI dependency; AppChrome redesign; Tool/Edit/Peek migration; production CSS cleanup |
| PR topology | serial |
| Authorized PR action | open/update exactly this assigned PR without asking; no additional PRs |
| Open implementation PRs in workstream at dispatch | none required; steward must re-check |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | one isolated implementation branch/worktree from activated `main` |
| Parallel lanes / collision hotspots | CON-READY PLAY may proceed if disjoint; `apps/live-control-ui/package.json` and lockfile are collision hotspots |
| Runtime/state ownership | frontend-only; no backend/runtime state; workshop port may be chosen freely at local launch |
| State-authority sync set after merge | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` records UI-F0 complete / UI-F1 active predecessor truth only |

Read before implementation:

1. `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md`
2. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`
3. `apps/live-control-ui/package.json`
4. `apps/live-control-ui/package-lock.json`
5. `apps/live-control-ui/src/styles.css`
6. representative current component tests for semantic/accessible button behavior

If the active frontend toolchain or package-manager layout differs materially at dispatch, stop and rebrief.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| UI workshop dev launch | No isolated frontend workshop | One Ladle process serves stories without backend services | Yes | package scripts + Ladle story boundary |
| UI workshop static build | No workshop build | `ladle build` completes from static frontend modules | Yes | Ladle/Vite build |
| Primitive story render | No canonical primitives | Surface/Button/Badge/Stack render from static props and semantic tokens | Yes | `src/ui` |
| Production frontend build | Existing Vite app builds | Still builds without importing workshop-only modules into production entrypoints | Yes | production Vite build |
| Token edit | Hardcoded paint dominates | Editing one semantic token visibly changes stories that consume it | Yes | CSS token layer |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Stop API/DB services → launch workshop → open every F1 story | All F1 stories render; no request/error state appears | manual workshop proof |
| Add/change token → workshop HMR → production build | Story changes immediately; production build still succeeds | manual + build |
| Search story/primitive sources for API/provider imports | None from `api/liveApi`, AgentInteraction, SurfaceInteraction providers, graph/world services | source guard |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/package.json` | Add Ladle dev dependency/scripts only |
| Modify | `apps/live-control-ui/package-lock.json` | Exact npm lock update |
| Create | `apps/live-control-ui/.ladle/components.tsx` | Workshop-only global CSS loading; no product provider |
| Create | `apps/live-control-ui/src/ui/tokens.css` | Small semantic token vocabulary |
| Create | `apps/live-control-ui/src/ui/primitives.tsx` | Exactly Surface, Button, Badge, Stack |
| Create | `apps/live-control-ui/src/ui/primitives.css` | Primitive styling consuming semantic tokens |
| Create | `apps/live-control-ui/src/ui/Foundation.stories.tsx` | Static workshop proof for four primitives and token tones |
| Create | `apps/live-control-ui/src/ui/primitives.test.tsx` | Semantic/accessibility contract proof for primitive props |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Backward-looking sync: UI-F0 completed by merged roadmap authority; UI-F1 current |

**Bounded discovery exception:** Not applicable — if Ladle requires additional production/config paths, stop and report instead of widening the slice.

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `apps/live-control-ui/src/App.tsx` | No production adoption in F1 |
| `apps/live-control-ui/src/styles.css` | Existing global paint remains unchanged; migration is later |
| `apps/live-control-ui/src/chrome/**` | No shell redesign |
| `apps/live-control-ui/src/surfaceInteraction/**` | Mature interaction kernel is preserved |
| `apps/live-control-ui/src/markdownCanvas/**` | Mature document authority is preserved |
| `apps/live-control-ui/src/graphReference/**` | No graph presentation migration |
| `apps/live-control-ui/src/graphObjectCard/**` | UI-F2 owns first representative product presentation |
| Base UI or another headless library | No consumer yet; speculative dependency |
| Playwright | UI-F4 owns screenshot infrastructure |

## §6 Implementation contract

```text
Input:
  static React props in Foundation.stories.tsx

Output:
  backend-free Ladle workshop rendering Surface, Button, Badge, Stack
  through one semantic token layer

Invariant:
  same as §1

Failure behavior:
  missing/invalid visual prop → ordinary React/TypeScript failure; do not add runtime fallback systems
  workshop build failure → merge blocked
  production build regression → merge blocked

Replay / idempotency:
  same source → deterministic static workshop build
  changed token → visual change only; no application-state mutation
  retry after failed build → normal rebuild, no persistent state

Trust boundary:
  Verifies: static module composition, token consumption, primitive semantics
  Records/trusts without proving: final product visual quality, future component API sufficiency
```

### A. State / fallback matrix

Not applicable — F1 introduces no loading state, remote dependency, durable state, or fallback source.

### B. Identity matrix

Not applicable — F1 introduces no product identity or resolution behavior.

### C. Persistence / replay matrix

Not applicable — workshop output is generated build material under ignored `build/`; no application persistence contract is introduced.

### D. Predecessor → consumer mapping

Not applicable — no production consumer migrates in F1.

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Workshop compiles independently | Ladle/Vite | contract | `npm --prefix apps/live-control-ui run ui:build` | exit 0; static build emitted under ignored build output | any build/config error |
| Primitives retain basic semantics | React component | regression | `npm --prefix apps/live-control-ui run test -- src/ui/primitives.test.tsx` | PASS | any owning test failure |
| New code typechecks | TS project | regression | `npm --prefix apps/live-control-ui run typecheck` | PASS or exact inherited base comparison | new error |
| Production app still builds | Vite production app | regression | `npm --prefix apps/live-control-ui run build` | PASS or exact inherited base comparison | new failure |
| Workshop has no product runtime dependency | source boundary | adversarial | static search of `src/ui/**` and `.ladle/components.tsx` | no imports from live API, surface providers, graph/world runtime | any such import |
| Weak-laptop workflow is real | developer workflow | manual | stop backend services; run `npm --prefix apps/live-control-ui run ui`; open all F1 stories; edit one token | stories render; HMR reflects token edit without backend | backend/network requirement or unusably heavy workflow |
| Lease stays exact | Git diff | contract | `git diff --check` + `git diff --name-only <dispatch-base>...HEAD` | only §4 paths | any unexpected path |

For the repository's exact-head review runner, execute the commands above from
the repository root with Node 20 or newer. The typecheck and production build
may fail only at the identical inherited base failure described below; the
reviewer must compare base and head rather than mark those commands green.

```bash
npm --prefix apps/live-control-ui ci --no-audit --no-fund
npm --prefix apps/live-control-ui run ui:build
npm --prefix apps/live-control-ui run test -- src/ui/primitives.test.tsx
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
git diff --check fa01c768...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface: Ladle workshop only
Smallest realistic scenario: backend services stopped; open Foundation stories at desktop and narrow browser widths; edit one semantic token
Expected observation: immediate visual change, no API/database dependency
Evidence captured: reviewer notes exact command, stories opened, and whether HMR remained responsive on target laptop
```

### Baseline failure handling

If typecheck/build/test fails on dispatch base, run the exact same command on base and head and report the comparison. No new frontend failure is acceptable.

## §8 Required review handback

Record:

1. Review Cycle N and exact PR/branch/head SHA;
2. exact implementation branch base;
3. serial topology and open PRs at dispatch;
4. §1 mission/invariant disposition;
5. all §7 results + provenance;
6. nano-commit story;
7. actual changed paths vs §4;
8. package dependency/lockfile delta;
9. manual weak-laptop workshop observation;
10. baseline failures/waivers;
11. paths outside §4;
12. stop conditions;
13. UI-F2 still false;
14. confirmation that no production component imports the new presentation layer yet.

## §9 Acceptance rubric

- [ ] Handoff was ACTIVE before dispatch.
- [ ] Exactly one fast-workshop capability was delivered.
- [ ] Workshop runs with backend services off.
- [ ] Exactly four named primitives exist; no speculative component library grew around them.
- [ ] Semantic tokens are used by the primitive styles.
- [ ] No Base UI/Storybook/Tailwind/CSS-in-JS was introduced.
- [ ] Production typecheck/build remain no worse than exact base.
- [ ] No product runtime/provider import enters F1 workshop/primitives.
- [ ] Actual changed paths stay inside §4.
- [ ] UI-F2 remains unimplemented.

## Stop conditions

Stop and report instead of expanding when:

- PR #755 is not merged at activation;
- Ladle requires invasive production Vite changes;
- the workshop needs product providers/network state;
- more than Surface/Button/Badge/Stack is required to prove the mission;
- a second styling system/token compiler is proposed;
- Base UI or another headless dependency becomes necessary without a concrete primitive consumer;
- any production surface must migrate to make the workshop useful;
- another active lane owns package/lock files.
