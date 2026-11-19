# CLEANUP: await actual prompt-body request

Status: ACTIVE. Authorized by the standing cleanup goal; independent review and merge authorized. Serial predecessor to existing #4119, which is HOLD with no active implementation lease until this timing defect is resolved. Branch codex/action-prompt-request-start; base709c622f19e7171195bd907c87fcb09900f7fd60; reuse existing isolated checkout. No runtime ports, services or databases.

Write lease: apps/live-control-ui/src/planSurface/components/ActionPromptInspector.test.tsx plus this temporary brief. All61 current open heads inspected; no target-file overlap. Runtime component and #4119's test file are read-only.

Observed exact parent full diagnostic: owner-change test reads body.mock.calls[0][3] before proving request invocation, failing undefined. Model-call select presence does not establish child effect completion. Correct with an assertion-based wait for exactly one body request before inspecting its AbortSignal; preserve all other assertions and three other case bodies. No sleeps in maintained tests or runtime changes.

Validation: isolated controlled delayed body-effect request makes old test fail/new test wait and pass; disabling abort must still fail. Retain original full failure and prior passing variant; no retry-to-green classification. Standard isolated exact-SHA hosted/build/validator and full-discovery comparison with visible baseline variant; independent exact-head review. No provider/DB/deployment proof. Then merge this predecessor, re-anchor #4119 and requalify its integrated head. Remove temporary brief from final tree, retaining pinned history; settle truthful external ledger/owning issue after merge.
