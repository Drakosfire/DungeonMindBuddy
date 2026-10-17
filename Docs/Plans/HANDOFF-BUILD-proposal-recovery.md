# Recover inline Build proposals

Status: ACTIVE — operator reports missing Insert after refresh. PRIME implements,
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
