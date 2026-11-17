# Inline prose targeting without an incidental caret

Status: ACTIVE, baseline-only disjoint sub-slice. Root explicitly assigned design
and implementation on November 17, then authorized this baseline-only split.
Base: eecaf7991bebd58c6ae625cad194cb962ebfa132.
Branch: codex/inline-prose-targeting-20261117.
Checkout: /home/drakosfire/Projects/inline-prose-targeting-20261117.
Topology: serial. No unmerged behavioral dependency. No merge/deploy authority.

## Invariant and critique
Named section plus referenced passage must choose an exact existing prose target
without selection; contextual additions choose a meaningful existing boundary.
An incidental top-of-page caret is not permission to insert there. Genuine
ambiguity clarifies without mutation; unnecessary clarification is a valid miss,
not an unsafe edit. Preserve explicit-selection fallback, citations, facts,
unrelated nodes and playable Plan structure. Retain current reviewed suggestion,
explicit Save and cold-reopen owners. No model offsets or new saving authority.

First measure existing behavior, including already-working Plan heading-boundary
placement. Keep deterministic host tests, routing quality and ordinary provider
results distinct. Synthetic inputs only; no provider call is authorized here.
Dev and held-out cases are separate. Table captions, nested structure, duplicate
passages, stale captures and read-only/discussion are adversarial cases.

## Exclusive expected writes
- This handoff.
- evals/inline_prose_targeting/**: synthetic fixtures, runnable baseline and scoring.
No runtime/controller/bridge/type/policy path is leased yet. After baseline,
a bounded unleased immutable catalog may be adopted explicitly; no implied lease.

## Ownership and external state
Fresh open PR inventory inspected November17. #3824 owns PlanSurfacePage,
WorldPlanAgentConversation and hosted shared owners; #3307 owns Plan driver,
harness and writer; #2401 is a separate proof-only heading probe. The active
image lane owns BuildComposeBridge and BuildComposeProposal, despite its ordinary
routing still being blocked. Do not edit those files or steer that task.
No5202/API8001 or other runtime, real World, database or browser state changes.
Outputs use uniquely owned external Projects storage and global verifier lock.

## Verification and stop
Baseline runs real editor/bridge/catalog APIs, reporting capability misses rather
than deliberately failing tests as product regressions. No baseline test is a
provider or end-to-end Save/reopen claim. Preserve raw output and source pin.
Runtime integration and ordinary synthetic provider exercise remain explicit gates.
Affected checks, exact-source repo verifier and independent review precede any
completion claim; push/draft PR is authorized, not merge/deploy.

## Baseline and bounded catalog adoption
Four real-editor baseline checks pass at179521171: Build lacks named prose offers;
Plan heading boundary+Undo already works; intra-paragraph sentence boundary is not
offered; stale/read-only guards refuse. Ordinary routing and Save remain unscored.
75 open PR file inventories checked: no overlap for this handoff, eval directory or
`apps/live-control-ui/src/documentEditing/proseTargetCatalog.ts`. This one new
runtime helper is now added to the exclusive lease, plus tests in the eval dir.
It offers immutable root prose-paragraph occurrences and adjacent legal root
boundaries with heading context, no incidental caret. It never selects, applies,
saves or routes model output. Replacement of partial sentences remains unsupported.
Resolution requires the exact live editable snapshot/scope and an issued catalog.
No arbitrary returned offsets or first-match substring resolution. Model selection
and integration with reviewed proposals remain blocked on bounded owner splits.

## Prose-only bridge split, November 17
Coordinating root explicitly transferred prose-only additions in
`buildSurface/buildComposeBridge.ts` and `.test.ts`, and
`planSurface/components/BuildComposeProposal.tsx` and `.test.ts`. Image capture,
apply and result portions remain exclusively image-owned; its task is paused and
its heads must remain untouched. No shared controller or other lane is transferred.
Fresh main remains eecaf799. External inventories show no overlap on these four
paths; #3864 owns build_jev_harness.py and #3824 owns the shared proposal-review
backend test. Neither is leased here.

Immediate sub-slice: bridge-issued read-only catalogs and explicit host nomination
provenance, retaining the actual author caret/selection basis unchanged. This does
not alter request/response schemas, durable reservations, review receipts, routing,
application or Save. Nonempty author selection stays with the existing path.
Hook writes are permitted only for this provenance scope; no need to change it
until a safe wire consumer exists. Existing author-selected selection metadata
must never impersonate an agent-nominated passage.

Current server reservation/output/review models are strict closed grammars.
Safe ordinary integration needs an explicitly reviewed additive catalog-target
contract with historical serialization and old-reader behavior, current snapshot
and replay checks, single-paragraph output admission, composer-compatible reviewed
application, and Save/cold-reopen proof. These remain gates, not assumed permissions.
