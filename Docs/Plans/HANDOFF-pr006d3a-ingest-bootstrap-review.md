# HANDOFF — PR006D3A — Bootstrap Activation Review gate on `/ingest`

> Status: READY DESIGN, NOT YET DISPATCHABLE
> Parent tracker slice: `PR006D3 — /ingest review and activation UI`
> Predecessor / design contract anchor: GitHub PR #337, merged as `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9`
> Implementation base: current `origin/main` **after** the tracker correction merges — **not** the D2 merge SHA
> Successor: PR006D3B — explicit prepare/confirm activation interaction
> Dispatch gate: do not dispatch implementation until the tracker on `main` records PR006D2 as `DONE` and PR006D3A as `READY` or `DOING`.

## §0 One-sentence mission

A GM can inspect the certified initial World Supergraph package in a distinct Bootstrap Activation Review gate so that they understand what may be published without entering or duplicating the ongoing recap Graph Review workflow.

## §1 Product boundary

D3A is a **Bootstrap Activation Review gate**. It is not a second Graph Review workbench.

The page must communicate:

> **This is the certified initial world package that may be published.**

It must not imply:

> This is another recap run, another preview-union lane, or another editable graph-review workspace.

The two `/ingest` workflows are neighbors, not modes of one pipeline:

```text
Bootstrap Activation Review
  one certified initial package
  fixed D2 status contract
  read-only lifecycle gate
  no run selection
  no editing
  no publication in D3A

Ongoing recap Graph Review
  session-scoped ingest runs
  preview-union / experimental review pipeline
  existing selectors, lanes, diagnostics, and authoring behavior
  remains mounted and independently usable
```

Do not normalize these workflows into a shared data model. Do not route bootstrap data through the preview pipeline merely because both appear on `/ingest`.

## §2 Re-anchor and lifecycle state

### Verified repository state

```text
PR006D1
  DONE — GitHub #336
  merge: fc6e811dd865559f662bf710566bdb9683acc370

PR006D2
  DONE — GitHub #337
  merge: 815f9d8d0f0582d3b8b7d86038e5d598c0a653b9

PR006D3A
  next implementation capability
  design handoff: this document

PR006D3B
  BLOCKED on accepted and merged D3A implementation
```

### Tracker drift

At the time this handoff was revised, `Docs/Plans/PR-TRACKER-campaign-supergraph.md` on `main` still described PR006D2 as `DOING` and PR006D3 as `BLOCKED`.

That is stale repository authority, not an unresolved technical dependency. It remains pending only because this design re-anchor / tracker correction has not yet merged to `main`. This documentation PR may be marked ready for review; that does **not** mean implementation is dispatchable. **Implementation must not be dispatched while the sole-authority tracker on `main` remains stale.** Before dispatch, the tracker must record at minimum:

```text
PR006D
  DOING — D1 and D2 complete; D3A next; D3B deferred

PR006D2
  DONE — GitHub #337; merge 815f9d8d0f0582d3b8b7d86038e5d598c0a653b9

PR006D3A
  READY or DOING — Bootstrap Activation Review gate

PR006D3B
  BLOCKED on PR006D3A — prepare/confirm publication interaction

PR007
  remains BLOCKED on completion of PR006D3A and PR006D3B
```

If this handoff merges without that tracker correction, stop. Land a narrow tracker correction before implementation dispatch. The handoff does not overrule the tracker.

## §3 Authoritative contract and forbidden inputs

### Sole production input

D3A consumes exactly one bootstrap operation:

```http
GET /api/live/world-graph-bootstrap/status
```

Requirements:

- no query string;
- no request body;
- no campaign, session, run, source, manifest, or store selector;
- no caller-supplied package identity;
- no direct browser read of checked-in contribution-bundle files.

The source of truth for ordinary GET `/status` lifecycle results is the D2 `dmb_world_graph_bootstrap_status_v1` response and its returned `BootstrapReview` (present or absent according to state). That includes expected lifecycle states such as `ready`, `active`, `active_head_advanced`, `invalid_bundle`, `blocked_existing_world`, and `inconsistent_lineage`.

`dmb_world_graph_bootstrap_error_v1` is a stable HTTP/route failure body, not the ordinary representation of those lifecycle states. The committed fixture's `invalidBundle` and `blockedExistingWorld` examples are shaped as direct error responses for prepare/confirm or route-failure paths. Tests must not use prepare/confirm error fixtures as the GET `/status` payload. For GET `/status` lifecycle coverage, use or derive `dmb_world_graph_bootstrap_status_v1` objects. Reserve `dmb_world_graph_bootstrap_error_v1` for true domain/transport failure handling.

Production code must not load, import, fetch, or parse:

```text
graph_data/approved_contribution_bundles/**
tests/fixtures/world_graph_bootstrap/api-contract-v1.json
recap manifests
preview-union stores
gold fixtures
run directories
```

The committed API contract fixture is a **test oracle only**. It must never become a production fallback or client-side package database.

### Explicitly forbidden pipeline reuse

D3A must not:

- reuse preview-run selectors or `getGraphIngestRuns`;
- pass manifest paths, run directories, preview-source IDs, artifact IDs, or preview-union store paths;
- reuse gold/live comparison lanes;
- read or mutate recap Graph Review selection state;
- add a bootstrap mode, flag, or compatibility branch to any existing preview API;
- adapt preview response types into a bootstrap-shaped object;
- import the existing Graph Review workbench into the bootstrap panel;
- make the bootstrap panel depend on Plan context, recap context, selected session, or selected run.

The bootstrap panel receives no graph-run props. It owns its own isolated status request and renders the D2 contract directly.

## §4 Mounting decision and failure isolation

### Placement

Mount `WorldGraphBootstrapReviewPanel` as a separate top-level section in `MemoryIngestPage.tsx`, before the existing `GraphReviewWorkbenchModule`.

Conceptual composition:

```tsx
<main className="ingest-surface-root" aria-label="Memory Ingest">
  <WorldGraphBootstrapReviewPanel />
  <GraphReviewWorkbenchModule context={context} />
</main>
```

This is not a toolbox mode. Do not modify `ingestSurfaceConfig.ts`.

The section needs its own semantic heading, boundary copy, lifecycle badge, and visual container. A GM should be able to distinguish the certified initial-package gate from the recap workbench without reading technical IDs.

Required framing copy or an equivalent faithful formulation:

```text
Bootstrap Activation Review
This is the certified initial world package that may be published.
This review is separate from ongoing recap Graph Review below.
```

### Independent loading

The bootstrap request must be isolated from existing page and workbench loading:

- do not add it to the `getPlanView()` request;
- do not combine bootstrap and plan-view loading with `Promise.all`;
- do not pass bootstrap state through `PlanContextDescriptor`;
- do not block Graph Review rendering on bootstrap success;
- do not let a bootstrap retry reset or replace Graph Review state;
- do not let Graph Review run changes trigger a bootstrap request;
- do not let bootstrap state select or alter a recap run.

`WorldGraphBootstrapReviewPanel` owns its request lifecycle and error boundary. When status fails, the panel renders an honest unavailable/error state while `GraphReviewWorkbenchModule` remains present and usable.

The existing `MemoryIngestPage` may continue to require plan-view context before mounting Graph Review. D3A does not redesign that page-level dependency. Its required isolation is specifically:

```text
bootstrap failure ≠ Graph Review failure
bootstrap loading ≠ Graph Review loading
bootstrap retry ≠ Graph Review reload
```

## §5 UX contract

### Default hierarchy

The top-level panel must answer, in order:

1. **What is this gate?** Certified initial World Supergraph package, not a recap run.
2. **What lifecycle state is it in?** Ready, published, advanced, blocked, invalid, inconsistent, or unavailable.
3. **What package is being described?** World, campaign, focus, bundle/package identity, and certification summary from the response.
4. **What will or did it contain?** Compact inventory summaries with expandable complete detail.
5. **What may be trusted?** Returned trust claims, diagnostics, and receipt/lineage health.
6. **What is technical detail?** IDs, digests, contribution hashes, evidence references, and revision IDs behind deliberate disclosure controls.

### Lifecycle states must be materially distinct

Do not render all non-error states as a generic success card.

| State | Required user meaning |
|---|---|
| `ready` | The package is certified and reviewable but **not published**. D3A offers no publication control. |
| `active` | The certified initialization was published and the active head matches the initialization lineage reported by D2. |
| `active_head_advanced` | The initialization was published, but the current head has advanced beyond the initial revision. The initial package is lineage history, not the current complete world. |
| `blocked_existing_world` | A different existing world prevents safe bootstrap publication. Do not imply retrying will overwrite it. |
| `invalid_bundle` | D2 could not certify the locked package. Do not display stale fixture contents as if review remained valid. |
| `inconsistent_lineage` | Stored world lineage does not truthfully match the approved initialization plan. Present this as an integrity problem, not ordinary advancement. |
| `error` or transport/unparseable failure | Status is unavailable. Show the failure and a status-only retry; keep Graph Review usable. |

The state must be evident from heading, state label, explanatory text, and accessible semantics—not color alone.

### Complete but not a graph browser

The full returned `BootstrapReview` and status trust object must remain reachable. Treat these as independent surfaces:

- nodes;
- relationships;
- attributes;
- contributions;
- sources/source artifacts;
- nested evidence and locator status returned inside review records;
- the top-level `review.evidence` collection;
- classifications;
- status-level `status.trustBoundary.canTrust`;
- status-level `status.trustBoundary.cannotTrust`;
- review-level `review.trustBoundary` non-claims (the review list, distinct from the status trust object);
- diagnostics;
- receipt and lineage/integrity health when present.

Do not treat nested evidence-only coverage as satisfying `review.evidence`. Do not treat status `canTrust` / `cannotTrust` as satisfying `review.trustBoundary`.

Counts and digests are not enough. Conversely, D3A is not an interactive graph explorer.

Approved interaction pattern:

```text
state + package summary
inventory count cards
expandable inventory sections
  nodes
  relationships
  attributes
  contributions
  sources
  nested evidence
  review.evidence
status.trustBoundary.canTrust / cannotTrust
review.trustBoundary
diagnostics
receipt / lineage health
technical identifiers
```

Allowed interactions are disclosure, expand/collapse, and retrying the same status GET. Do not add graph navigation, node selection state, edge hover systems, editing, merge/reconciliation actions, source repair, filtering by recap run, or a canvas.

Resolve relationship endpoint labels from the returned node collection for readability, while preserving raw IDs in detail. Never query another data source to enrich the review.

### Evidence handling

Render locator status exactly as returned.

An `unverified` evidence locator must:

- be visibly labeled unverified;
- remain non-navigable;
- not be described as a verified source link;
- not be resolved against the filesystem or served corpus paths in the browser.

## §6 Reuse strategy

Reuse **lower-level neutral presentation primitives** only when they have no preview-pipeline semantics. Examples may include existing buttons, badges, disclosure elements, typography, generic cards, or layout tokens.

Do not reuse or adapt:

- `GraphReviewWorkbenchModule` internals;
- preview projection containers;
- graph-run hooks;
- gold/live lane components;
- preview object-card state;
- recap evidence comparison models;
- authoring overlays or event logs;
- ingest toolbox configuration.

The bootstrap panel may import an existing generic primitive without modifying it. If a shared primitive must be changed, or if the only available primitive requires preview-run data, stop and report the proposed path rather than widening this PR.

Bootstrap-native view models may perform presentation-only derivation from one `BootstrapReview`, such as endpoint-label lookup or grouped counts. They must not translate through a preview or union-supergraph API type.

## §7 Files in scope

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/api/types.ts` | Add the exact status/error and nested `BootstrapReview` types consumed from D2. Do not add prepare/confirm types. |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | Add one isolated no-query, no-body status GET client and preserve stable D2 domain-error bodies. |
| Modify | `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx` | Mount the distinct top-level Bootstrap Activation Review section alongside—not inside—the existing Graph Review workbench. |
| Create | `apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx` | Prove sibling workflow composition and bootstrap-failure isolation. |
| Create | `apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.tsx` | Own status loading and render the bootstrap-native lifecycle gate and complete review inventory. |
| Create | `apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.test.tsx` | Prove transport, lifecycle, complete inventory, response-driven rendering, and non-navigation requirements. |
| Create | `apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/worldGraphBootstrapReview.css` | Visually distinguish the gate using existing application tokens. |

Every changed runtime path must appear above. If another runtime path is required, stop and report it.

### Explicitly out of scope

```text
src/graph_memory/**
apps/live_control_server/**
graph_data/approved_contribution_bundles/**
tests/fixtures/world_graph_bootstrap/api-contract-v1.json
apps/live-control-ui/src/planSurface/graphReviewWorkbench/**
apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts
apps/live-control-ui/src/planSurface/projection/**
apps/live-control-ui/package.json
lockfiles
```

Also out of scope:

- prepare, confirm, actor entry, acknowledgement, proposal IDs, tokens, and publication;
- arbitrary contribution publishing;
- ongoing recap ingestion into the persistent world head;
- graph correction, identity resolution, source editing, or evidence repair;
- Projection Engine and Plan/Play migration;
- backend/schema/fixture correction;
- general Graph Review redesign.

## §8 Implementation contract

```text
Input:
  GET /api/live/world-graph-bootstrap/status
  no query
  no request body

Success / ordinary lifecycle source of truth:
  dmb_world_graph_bootstrap_status_v1
  BootstrapReview returned by D2 when present
  Includes invalid_bundle, blocked_existing_world, inconsistent_lineage as status shapes

Stable HTTP/route domain error:
  dmb_world_graph_bootstrap_error_v1
  Not a substitute for ordinary GET /status lifecycle payloads

Output:
  A distinct read-only Bootstrap Activation Review gate on /ingest.

Invariant:
  Every package fact, label, count, claim, diagnostic, and health value shown in
  production comes from the currently returned D2 response.

Failure isolation:
  Bootstrap failure degrades only the bootstrap gate. Ongoing Graph Review stays
  mounted and independently usable.

Mutation boundary:
  The implementation cannot prepare, confirm, or publish.
```

The generic API helper currently expects FastAPI `detail` error envelopes. The bootstrap route returns a stable domain error directly. Preserve that body through a narrow status result rather than generalizing the whole API layer.

## §9 Required tests

Tests must read `tests/fixtures/world_graph_bootstrap/api-contract-v1.json` as the D2 contract oracle. They may deep-clone and mutate fixture-derived values to prove response-driven rendering. They must not recreate an equivalent campaign fixture by hand.

### 1. Transport exclusivity

Prove the only bootstrap network operation is:

```text
method: GET
path: /api/live/world-graph-bootstrap/status
query: none
body: none
```

Assert the actual fetch/request invocation. Mount, retry, and state transitions must not call any other bootstrap endpoint.

### 2. Mutation absence

Prove no implementation path contains or calls:

```text
/api/live/world-graph-bootstrap/prepare
/api/live/world-graph-bootstrap/confirm
```

No actor input, acknowledgement control, proposal ID, confirmation token, publish button, or mutation response type may exist.

### 3. Workflow failure isolation

At the `MemoryIngestPage` boundary:

- allow plan-view context to load;
- force bootstrap status to fail;
- assert the Bootstrap Activation Review shows its unavailable state;
- assert the existing `GraphReviewWorkbenchModule` remains mounted and usable;
- assert bootstrap retry does not request plan view again or replace Graph Review.

Do not prove this only by unit-testing the panel in isolation.

### 4. Response-driven rendering

Start from a canonical fixture response, deep-clone it, and replace representative package identity, node labels, relationship labels/text, attributes, source titles, trust claims, diagnostics, and revision IDs with unmistakable test values.

Assert the replacement values render and no production constant supplies the original Eldyrwild/Mirathorn/Tripod text. This proves the UI renders the response rather than fixture constants, contribution files, or campaign-specific hardcoding.

### 5. Lifecycle distinction

Prove distinct visible and accessible meaning for:

- certified-but-unpublished `ready`;
- published `active`;
- published but lineage-advanced `active_head_advanced`;
- `blocked_existing_world`;
- `invalid_bundle`;
- `inconsistent_lineage` when represented by the contract;
- direct D2 `error` and transport/unparseable failure.

In particular, `ready` must not imply publication, and `active_head_advanced` must not imply that the initialization revision is the current complete head.

### 6. Complete inventory without preview reuse

For a fixture-derived status response and its `BootstrapReview`:

- expand each inventory section;
- verify every returned node is reachable;
- verify every returned relationship is reachable;
- verify every returned attribute is reachable;
- verify every returned contribution is reachable;
- verify every returned source and nested evidence item is reachable;
- verify every item in the top-level `review.evidence` collection is reachable independently of nested evidence;
- verify every returned classification is represented;
- verify every item in `status.trustBoundary.canTrust` is reachable;
- verify every item in `status.trustBoundary.cannotTrust` is reachable;
- verify every item in `review.trustBoundary` is reachable as its own collection (do not equate it with the status trust object);
- verify diagnostics and receipt/lineage health are reachable;
- verify unverified locators are labeled and not links.

Prefer assertions driven by iterating the response collections, not a small list of famous campaign entities.

Lifecycle-state tests that exercise `invalid_bundle`, `blocked_existing_world`, or `inconsistent_lineage` must use `dmb_world_graph_bootstrap_status_v1` payloads. Do not feed prepare/confirm `dmb_world_graph_bootstrap_error_v1` fixture examples into the GET `/status` success path.

Also assert the bootstrap implementation imports or calls none of the forbidden preview/run selectors listed in §3.

## §10 Verification commands

Run from the repository root unless noted:

```bash
cd apps/live-control-ui
npm test -- \
  src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.test.tsx \
  src/ingestSurface/MemoryIngestPage.test.tsx
npm run typecheck
npm run build
cd ../..

# Record the actual post-tracker main SHA when creating the implementation branch.
# Do NOT use the D2 merge SHA 815f9d8d… as the implementation base for allowlist checks.
IMPLEMENTATION_BASE="$(git merge-base HEAD origin/main)"
# Prefer the SHA recorded in the PR body at branch creation if it differs from merge-base.
test -n "${IMPLEMENTATION_BASE}"

git diff --check

git diff --name-only "${IMPLEMENTATION_BASE}"...HEAD
```

### Scope allowlist check

```bash
python - <<'PY'
import os
import subprocess

implementation_base = os.environ.get("IMPLEMENTATION_BASE")
if not implementation_base:
    raise SystemExit(
        "IMPLEMENTATION_BASE is required. Record the post-tracker main SHA at branch "
        "creation and use it for every diff/stat/allowlist check. Do not substitute "
        "the D2 design-anchor merge SHA 815f9d8d0f0582d3b8b7d86038e5d598c0a653b9."
    )

allowed = {
    "apps/live-control-ui/src/api/types.ts",
    "apps/live-control-ui/src/api/liveApi.ts",
    "apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx",
    "apps/live-control-ui/src/ingestSurface/MemoryIngestPage.test.tsx",
    "apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.tsx",
    "apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.test.tsx",
    "apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/worldGraphBootstrapReview.css",
}
changed = set(
    subprocess.check_output(
        ["git", "diff", "--name-only", f"{implementation_base}...HEAD"],
        text=True,
    ).splitlines()
)
unexpected = sorted(path for path in changed if path and path not in allowed)
if unexpected:
    raise SystemExit("Unexpected paths:\n" + "\n".join(unexpected))
print(f"Allowlist check passed against IMPLEMENTATION_BASE={implementation_base}")
PY
```

### Forbidden bootstrap operations

```bash
if git grep -nE 'world-graph-bootstrap/(prepare|confirm)' -- \
  apps/live-control-ui/src/api \
  apps/live-control-ui/src/ingestSurface; then
  echo 'D3A introduced a forbidden bootstrap mutation operation' >&2
  exit 1
fi
```

### Forbidden preview-pipeline coupling

Scan **added** diff lines across every allowed production file. Do not whole-file
grep `liveApi.ts` / `types.ts` / `MemoryIngestPage.tsx`, which already contain
legitimate preview-pipeline symbols outside this slice.

```bash
python - <<'PY'
import os
import re
import subprocess

implementation_base = os.environ["IMPLEMENTATION_BASE"]
production_paths = [
    "apps/live-control-ui/src/api/types.ts",
    "apps/live-control-ui/src/api/liveApi.ts",
    "apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx",
    "apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/WorldGraphBootstrapReviewPanel.tsx",
    "apps/live-control-ui/src/ingestSurface/worldGraphBootstrap/worldGraphBootstrapReview.css",
]
pattern = re.compile(
    r"getGraphIngestRuns|previewUnion|preview_union|manifestPath|manifest_path|"
    r"goldReview|gold-review|runDir|run_dir"
)
diff = subprocess.check_output(
    ["git", "diff", "-U0", f"{implementation_base}...HEAD", "--", *production_paths],
    text=True,
)
hits = []
current = None
for line in diff.splitlines():
    if line.startswith("+++ b/"):
        current = line[6:]
        continue
    if current is None or not line.startswith("+") or line.startswith("+++"):
        continue
    if pattern.search(line):
        hits.append(f"{current}: {line[1:].strip()}")
if hits:
    raise SystemExit(
        "D3A coupled bootstrap review to the preview/run pipeline in added lines:\n"
        + "\n".join(hits)
    )
print("Preview-coupling added-line guard passed")
PY
```

Review the final diff and confirm `ingestSurfaceConfig.ts` and `graphReviewWorkbench/**` are unchanged.

## §11 Acceptance rubric

Accept only when every item is true:

- [ ] The section is visibly and semantically a **Bootstrap Activation Review**, not a Graph Review mode or lane.
- [ ] It states that this is the certified initial world package that may be published.
- [ ] Production consumes only no-query, no-body `GET /api/live/world-graph-bootstrap/status`.
- [ ] Production renders the D2 status response and `BootstrapReview` directly; it does not load contribution bundles or fixtures.
- [ ] No preview-run selector, manifest path, preview-union store, gold/live lane, recap Graph Review state, or bootstrap preview mode is introduced.
- [ ] The bootstrap panel is a top-level sibling of the existing Graph Review workbench.
- [ ] Bootstrap transport/contract failure does not prevent Graph Review from loading or remaining usable.
- [ ] Bootstrap loading and retry are isolated from plan-view and graph-run loading.
- [ ] `ready`, `active`, `active_head_advanced`, `blocked_existing_world`, `invalid_bundle`, `inconsistent_lineage`, and unavailable/error states make materially distinct truthful claims.
- [ ] Every returned node, relationship, attribute, contribution, source, nested evidence, top-level `review.evidence`, classification, `status.trustBoundary.canTrust`, `status.trustBoundary.cannotTrust`, `review.trustBoundary`, diagnostic, and receipt/lineage health field remains inspectable.
- [ ] The UI uses compact summaries and expandable detail without introducing graph navigation or a second interactive browser.
- [ ] Unverified evidence locators remain visibly unverified and non-navigable.
- [ ] No prepare, confirm, actor, acknowledgement, proposal, token, or publication behavior exists.
- [ ] Focused tests, typecheck, build, diff check, endpoint guard, and preview-coupling guard pass.
- [ ] No runtime paths outside §7 changed.
- [ ] The tracker on `main` truthfully records D2 completion and D3A readiness before implementation dispatch.

## §12 Retain / rewrite / delete

```text
Retained temporarily:
- Existing recap/run Graph Review workbench and its preview-pipeline selectors.

Reason:
- It remains the independently usable ongoing recap-review workflow until later
  projection and write-path replacement slices own its migration or deletion.

Remaining consumer:
- Ongoing session-scoped recap Graph Review on /ingest.

Rewritten:
- None of the existing Graph Review pipeline.

Deleted in D3A:
- Nothing. D3A adds a separate status-driven gate and does not replace the recap
  workflow.

Required deletion PR:
- PR007 and later migration slices retain their existing demolition ownership.
- D3A must not move preview-pipeline deletion into this read-only gate.
```

## §13 Required implementation PR handback

- Branch from the current `main` only after the tracker correction is merged.
- Record that post-tracker `main` SHA as `IMPLEMENTATION_BASE` in the PR body and use it for every §10 diff, stat, and allowlist check. Do not use the D2 design-anchor merge SHA `815f9d8d0f0582d3b8b7d86038e5d598c0a653b9` as the implementation base.
- Open a draft PR against `main`.

The PR body must include:

1. The one-sentence mission from §0.
2. `IMPLEMENTATION_BASE` SHA (post-tracker main), design-anchor SHA (D2 merge), and head SHA.
3. Diff stat and exact changed paths against `IMPLEMENTATION_BASE`.
4. Every §10 command and result.
5. Bootstrap network operations observed in tests; accepted answer: status GET only.
6. Proof that bootstrap failure leaves Graph Review mounted.
7. Proof that fixture-derived replacement values render.
8. Inventory coverage counts for every returned review collection.
9. Explicit statement that no prepare/confirm, preview selector, bundle read, or campaign hardcoding exists.
10. Deviations and stop conditions: `none`, or an explicit split report.

Do not mark PR006D3 or PR006D complete from the implementation branch. The design/review owner re-anchors after implementation merge before writing PR006D3B.

## Stop conditions

Stop and report rather than broadening D3A if implementation requires:

- modifying D2 backend models, routes, service, or fixture;
- reading contribution-bundle files in the browser;
- introducing prepare/confirm types or calls;
- adding a bootstrap mode to preview APIs;
- importing preview-run state into the bootstrap panel;
- modifying `GraphReviewWorkbenchModule` internals or `ingestSurfaceConfig.ts`;
- sharing a load gate that allows bootstrap failure to suppress Graph Review;
- adding a graph browser, graph navigation, editing, filtering, or authoring;
- changing generic shared primitives to carry preview semantics;
- adding dependencies;
- resolving or trusting evidence locators in the browser;
- beginning Projection Engine, Plan/Play migration, or publication interaction.

Use this stop report:

```text
Stop condition:
Why the D3A mission cannot absorb it:
Affected contract or path:
Smallest successor slice:
Tracker change required:
```

The expected successor remains:

```text
PR006D3B
  A GM can prepare and explicitly confirm the certified bootstrap proposal so
  that the initial World Supergraph is published deliberately.
```
