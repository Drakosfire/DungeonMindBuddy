# Recover inline Build proposals

Status: SHIPPED — operator reports missing Insert after refresh. PRIME implements,
ARCHITECTURE reviews. Base afa8ab32, serial successor to merged PR1293, branch
codex/build-proposal-recovery at /tmp/prime-recap-mention-boundaries.

Keep the independent inline proposal preview/actions available after refresh.
For a recovered proposal, explicit Insert at current caret captures a fresh editor
target and requires identical World/document/revision/hash/visibility/draft hash,
active conversation and pointer. Never re-run generation, mutate before approval,
or silently target changed documents. Fence late captures on World changes.
Already inserted receipts stay non-insertable; preserve manual Save and source data.

The page editor does not retain table alignment. Deterministically remove alignment
colons only in parser-proven Markdown table delimiter rows for insertion, disclose
that page alignment uses its default, retain original proposal/prompt bytes. Never
weaken general Markdown admission or transform fenced text/other unsafe content.

Exclusive write paths: this handoff; apps/live-control-ui/src/planSurface/components/
BuildComposeProposal.tsx and .test.tsx; apps/live-control-ui/src/buildSurface/
buildProposalMarkdown.ts (new), buildProposalMarkdown.test.ts (new).
No new media producer or API contract. This preserves the independent inline
content block; future media renderers must use typed artifacts and their own
insertion contracts. Verify recovered/stale/foreign/late/double insertion, aligned
table owning admission, and existing mounted Save/reopen tests. PR, independent
review, merge and matched rollout including predecessor PR1293; no operator edits.

## Settlement
PR1294 merged7147d1e4a6372f556c0c2d65a3121f12030e48e0; ARCHITECTURE PASS21a6bfc9;20 UI/admission/persistence tests, typecheck/build pass.
Matched UI5202 and API8000/8002 now serve immutable7147d1e4;5876 UI unchanged.
No schema migration, provider call or operator document edit. Compiled assets and
authenticated routes verified. Desktop actual d20 column46px, name106px; narrow
viewport has no horizontal conversation overflow. Existing input pretty-printed
without request-byte changes. Existing proposal retains Insert at current caret.
Operator approval/Save still required. Lease closed.
