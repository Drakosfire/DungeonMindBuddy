# PLAN · Preserve PDF-backed assertion citations

Base: e2e90998d. Implementation lane: codex/plan-pdf-evidence.
Authorization: the Conks-to-Play benchmark requires source-backed saved cards.
The initial verification input is the reviewed Conks Event on activation #3750.
That PR is a qualification dependency. The Plan change owns distinct runtime
paths and must be integrated after the native upload, Event, and activation chain.

## Invariant

A selected assertion with complete verified PDF support is usable in Plan and
its citation reopens the exact region from its saved revision. Keep existing
text receipts readable and keep byte/hash validation for their exact spans.
Never manufacture a UTF-8 span from reviewed assertion prose. A support
reference must resolve in the same authorized World and Graph revision.

## Review map

1. Selected read and execution closure: native_graph_reads and
   native_plan_assertions verify a typed PDF region using the existing native
   opener and retain the identity in the execution receipt.
2. Completion and card reference: use the same verified support identity for
   citation admission and the saved selection. Pass model-visible reviewed
   prose and local aliases only. Preserve the exact reference on reorder.
3. Presentation: reuse native Graph inspection for the selected PDF region.
   A current-node chip remains ordinary navigation. A citation resolves with
   the saved Graph revision.

## Verification

Run the retained text closure controls and the isolated Conks selected-read
witness. Open the PDF from the resulting saved card, advance the Graph head,
reorder the card and reopen. The PDF digest, page, rectangle and rendered
bytes must still match. Unavailable, altered and foreign support must not
be admitted. Keep runtime qualification provider-free until the exact
selection, save and reopen contracts pass. Then qualify one ordinary Plan turn.

The proposal projection belongs to the save invariant above. Include
`application_state.agent_conversation.plan_authoring` in the bounded write set:
derive each internal link from the admitted PDF citation and its original
completion index. Keep historical non-PDF Markdown byte-identical. Verify that
the proposal-supplied link survives save, reorder, and exact reopen.
