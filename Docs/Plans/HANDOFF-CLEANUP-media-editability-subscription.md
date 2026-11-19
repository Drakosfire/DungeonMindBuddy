# CLEANUP: synchronize image editability on subscription

Status: ACTIVE under standing cleanup goal implementation/review/merge authority.
Base `ca239ca90e42281f0a85ef10a5c62d0945ffaf92`; branch
`codex/media-editability-subscription`, reused checkout. No runtime resources.

## Scope, topology and invariant

One independently reviewable runtime repair: MediaImageView must reflect the
editor's current editability even if Read/Edit changes between render and effect
subscription. Subscribe then synchronize; preserve no authored update, image
identity/document JSON, Read control refusal and active-resize cancellation.

Writes: this handoff and only
`apps/live-control-ui/src/tiptap/extensions/MediaImageNode.tsx` plus its existing
`MediaImageNode.test.tsx`. Current open PR paths and complete cached #3824 paths
contain no overlap. #4147 owns only App's E7 case and its handoff/predecessor.
Explicit parallel-independent source topology with that held PR: no unmerged
behavioral dependency, disjoint files, no shared runtime; all frontend test runs
remain serialized by the global lock. Merge this repair first, then rebase and
requalify #4147. Do not absorb the runtime repair into E7 or weaken its assertions.

## Evidence and failure cases

Exact #4147 head3821bf0daea74c2b19f4f2f312eac6bbe0e66785 full diagnostic made
E7 pass but newly failed existing production Read→Edit controls case. Preserve
that result; not accepted as inherited. Both Media files match base unchanged.
Disposable controlled witness at
`/home/drakosfire/Projects/.codex/buddy-check.w_s8siy6/receipt.json` changes actual
editor editability immediately before listener registration. Identical witness:
original2FAIL (both directions), subscribe-then-sync2PASS, JSON unchanged/no
authored updates. This is modified-source diagnostic, not qualifying evidence or
proof that every observed occurrence has the same cause. Prior executor failure
and exact test/runtime snapshots retained; dependencies/caches disposed by owner.

## Validation and delivery

Retain existing tests unchanged. Add controlled real-editor Read→Edit and
Edit→Read registration-gap regressions, assert current controls, unchanged JSON,
no update; run full Media module including active-resize cancellation. Isolated
exact-source diagnostics first, then exact-head hosted/build/validator and full
discovered identity/status comparison against current main's retained frontend
baseline (8147pass103fail2pending,8252reported/8250inventory). Any new failure
blocks acceptance. Independent cumulative review required. No providers/auth,
backend, dependency, classification, deadline, workflow or deployment changes.
