# DOCS: retrieval evidence navigation

Status: MERGED / HISTORICAL. Buddy PR #3980, merge `28a707a44ba66bde753f6a38676fd15d08b0f128`. The lane is closed; this record does not authorize new work.

Base: Buddy main `d2f46d19d01432fe305b2d29ae4f308326a1cff4`, after #3963. Branch: `codex/docs-retrieval-evidence`.

## Outcome and boundary

Make the owner-accepted ingestion working baseline and preserved retrieval history discoverable from the documentation and lab entry points. The linked report owns the decision, qualifications, evidence limitations and historical references. Do not change benchmark claims, run evaluations, publish campaign data, or rewrite historical assets.

Expected write lease: `Docs/README.md`, `evals/README.md`, and this handoff. No shared services, ports, databases or generated outputs are required. Check open PRs for overlaps before review.

## Verification

Check both links and their target in the exact diff; read the linked report to confirm it distinguishes accepted working baseline, known limitations, historical evidence and proposed work. Run `git diff --check`, inspect the cumulative diff, and follow the repository review standard. Report unverified runtime or test evidence truthfully.
