# Hermes Campaign Authoring Foundation Reset Archive

**Archived:** 2026-07-15  
**Replacement active set:** [`../../../../Design/INDEX-hermes-campaign-authoring-foundation.md`](../../../../Design/INDEX-hermes-campaign-authoring-foundation.md)  
**Sequencing authority:** [`../../../../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md`](../../../../Plans/PLAN-hermes-campaign-authoring-foundation-reset.md)

This archive preserves the superseded Hermes/world-graph design line while removing
its sequencing authority from the active working surface. Nothing in this archive is
an active implementation instruction unless the Phase 1 re-anchor explicitly
promotes a specific lesson.

## Contents

| Archive path | Classification | Why archived | Active replacement |
|---|---|---|---|
| `design-reset-sandbox/` | Historical evidence and superseded proposal | The 2026-07-14 graph-interaction reset is narrower than the new campaign sensemaking and authoring goal; its useful retrieval contracts are retained as input | Active architecture, stories, and evaluation docs |
| `superseded-anchors/ANCHOR-agent-interaction-hermes.md` | Superseded product anchor | Graph-only lookup, cite-or-abstain, and PR ladder sequencing no longer define the product | Goal anchor plus active architecture |
| `superseded-anchors/UX-STORIES-agent-interaction-hermes.md` | Superseded acceptance catalog | Rung-based read-only stories omit the authoring, draft, and promotion lifecycle | Active user/agent stories |
| `superseded-hermes-ladder/` | Historical implementation handoffs | PR008B/010B/344/351–356 describe completed or superseded ladder slices and are no longer the next sequence | Foundation reset plan |
| `historical-authoring-handoffs/HANDOFF-pr329-agent-tool-authored-prep-contract.md` | Historical design handoff | The PR005B dispatch is an implementation-era artifact; its useful authored-prep contract remains in the active contract document, while its Hermes references now point at compatibility stubs | `Docs/Design/CONTRACT-agent-tool-authored-prep-contributions-v0.md` plus foundation plan |

## Retained lessons

- Revision, campaign scope, admissibility, source integrity, and bounded model-visible
  retrieval remain hard boundaries.
- Graph claims, successful source reads, inferences, gaps, and conflicts need distinct
  authority/support states.
- A shared read-only retrieval session is useful when kept smaller than the product.
- Generated material requires explicit review and promotion; it is not canon by
  default.
- Conversation continuity is not factual memory.
- Empty initial deterministic retrieval must not force an empty user-facing answer when
  admitted recap/source context can support useful investigation.

## Deliberately not decided here

- Which archived retrieval contracts survive unchanged;
- final deletion versus quarantine of legacy code;
- final UI removal list;
- whether a `ChangeSet` becomes a first-class product object;
- the implementation checklist and owners.

Those decisions belong to the explicit Phase 1 re-anchor and the code/UI demolition
map. This archive only establishes the document boundary.

## Reference and code status

The moved documents had no runtime code imports. Historical internal links may still
name their original paths; the active repository links that define current authority
are redirected during Phase 0. The implemented retrieval code remains in place until
the separate code demolition pass has reference-scan evidence and an approved
quarantine/deletion list.
