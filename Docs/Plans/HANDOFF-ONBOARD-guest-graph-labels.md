# ONBOARD: readable guest graph terms

Status: ACTIVE. The owner-authorized onboarding goal includes evaluating and
improving the guest graph. This parallel-independent presentation slice starts
at `origin/main@31d4ffa9074a1a1b364e8880126e89ce3faa653a` on branch
`codex/onboard-guest-graph-labels`, in the build-status-baseline checkout.
Checked concurrent serving PRs #4557 and #4564; neither owns this guest page or
its tests. No runtime, database or public snapshot is leased for this work.

Display the existing `dnd5e ·` namespace as the underlying graph term in guest
nodes, their details, connections and temporary-point target choices. Preserve
unrecognized namespaces and visitor-authored text verbatim. Keep source roles,
asserted/inferred and time information, identifiers, graph data, sandbox
isolation, and all navigation intact. Write lease: this handoff,
`GuestReleasePage.tsx`, and its focused test file. No backend, schema, shared
editor or release selection changes. Verify the rendered guest interactions,
unknown namespace and temporary text handling; run required exact-SHA hosted
and discovered frontend verification, review the cumulative diff, and request
Bugbot review. Serving adoption is serial after the active production releases
and must be re-anchored on their actual outcome.
