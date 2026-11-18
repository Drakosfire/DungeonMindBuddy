# DOCS: clarify historical Hermes reset

Status: ACTIVE for this serial PR; this one-shot assignment ends when its PR
merges and remains a historical record thereafter. Authorized by the documentation
goal and the user request to finish it after #2406.
Base: Buddy main `77152afcf8b1d4458df6d9b498793b8ff632a414`.
Branch: `codex/docs-hermes-history`. Predecessor: merged #2406.

## Outcome and boundary

Correct the Plans index and July reset plan to agree with their superseded
historical index, without rewriting their historical content. Point that index
to current path-dependent runtime selection and settle the merged #2406
handoff. No runtime, process policy, external state or provider changes.

Expected write lease: `Docs/Plans/README.md`,
`Docs/Plans/PLAN-hermes-campaign-authoring-foundation-reset.md`,
`Docs/Design/INDEX-hermes-campaign-authoring-foundation.md`,
`Docs/Plans/HANDOFF-PROCESS-retire-standing-steward-role.md`, and this handoff.
No services, ports, databases or provider calls are needed.

## Verification

Check the historical index, current runtime selector and merge SHA; run the
maintained link checker and scoped checks of the edited documents, inspect the
cumulative diff, and complete exact-head review and local verification.
