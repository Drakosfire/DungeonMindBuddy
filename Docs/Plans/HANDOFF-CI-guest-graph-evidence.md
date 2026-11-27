# Guest Graph exact evidence transport

ACTIVE: user requested frontend diagnostic repairs and Trace deployment. Serial slice `codex/frontend-guest-graph-evidence`, based on `origin/main` at `a644ad4a959e390fbda77d78efe8fb3762ae1ce0`, follows merged #4787. Write scope: frontend transport, its focused tests and this brief.

The native Graph inspection endpoint is an authenticated read-only POST. Treating it as a write starts read waves that unmount the citation while its exact-source request is running. Preserve existing request admission, access, exact pin and cancellation behavior; do not share or cache transport. Preserve invalidation for actual writes. Verify the existing real guest App flow and focused transport/auth contracts, clean exact-head hosted verification, full discovered comparison and independent review.
