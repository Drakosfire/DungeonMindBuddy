# DOCS: repository entry navigation

Status: MERGED / HISTORICAL. Buddy PR #3963, merge `d2f46d19d01432fe305b2d29ae4f308326a1cff4`. The lane is closed; this record does not authorize new work.

## Outcome and topology

Serial; base Buddy main `eecaf7991bebd58c6ae625cad194cb962ebfa132`, branch `codex/docs-entry-navigation`. Make the root README and documentation index route a new reader to the correct product, setup, architecture, verification, and historical sources. Clearly separate code merged on main, an initial hosted release, and verified deployed capabilities. Do not assert a feature is deployed merely because its PR merged. This is the first slice of the wider documentation goal; domain reconciliation and automated navigation checks remain successors.

Authority: current `AGENTS.md`, repository content at the base, and the operator's documentation goal. #2406 owns `Docs/Design/INDEX-design-agent-source-set.md` and process sources; #3854 owns backlog and roadmap files. Neither is in this lease. Open PR changed-path checks covered the newest 100 open PRs and #2470/#2406/#3854; no overlap with the two entry points was found. Recheck before merge.

## Failure cases

Do not describe the 2026-09 source-set export as current policy or overwrite its owner. Avoid introducing a replacement source of authority, invented setup or deployed-product claims, moving or deleting historical evidence, or links to unverified paths. Preserve the current quick-start commands and product ownership unless the owning sources prove a correction. Avoid requiring private campaign material to explore the product.

## Expected write set

- `README.md`
- `Docs/README.md`
- `Docs/Plans/HANDOFF-DOCS-entry-navigation.md` (this handoff)

No code, data, deployment, provider, database, port, or runtime changes. An API-created branch is the isolated Git lane; no local checkout, runtime, cache or output lease is required.

## Verification

Inspect the exact base-to-head diff; validate relative file links and applicable anchors against the committed tree; compare key claims against exact main code, current owning docs and PR evidence; conduct fresh-reader lookups for product, setup, code/verification, architecture ownership and historical versus current authority. Report checks and unverified runtime/deployment claims. Obtain independent review and comply with current local-verification policy before merge. No merge authorization follows from this handoff.
