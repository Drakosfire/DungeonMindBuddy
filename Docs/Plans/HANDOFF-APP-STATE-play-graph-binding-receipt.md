# Play Graph binding receipt handoff

APP-STATE exports `PlayGraphBindingReceiptV1`,
`encode_play_graph_binding_reference`, and
`decode_play_graph_binding_references` from
`application_state.agent_conversation.types`.

The receipt has schema `dmb_play_graph_binding_receipt_v1`, the managed World ID,
the native World ID, and a positive managed binding version. Its reserved
`supporting_work` reference kind is `dmb_play_graph_binding_v1`: `object_id`
stores the native World ID and canonical decimal `revision` stores the binding
version. The managed owner remains `TurnProvenance.world_id`. The separate
`world_graph_revision` reference stores the same native World ID and the
immutable Graph revision. Existing conversation persistence stores both as
historical references; no migration is needed.

The binding is valid only on a resolved Play surface with a complete frozen
Play Run/Runbook/Beat/optional Scene receipt, exactly one matching resolved
Graph revision, and no selected Graph node. Duplicate, malformed, or
mismatched binding/Graph references are rejected. Generic historical Graph
references and legacy graphless Play turns remain valid when this reserved
binding is absent. No old turn receives a fabricated receipt.

SERVER must validate the current managed-to-native binding and Graph authority
before constructing new provenance. For a pending retry or history read it
must compare against the stored binding and revision rather than refresh those
pins. This codec only validates and persists structural provenance; it does
not grant current Graph access or select a Graph node.
