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
