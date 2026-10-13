# Mirathorn context-loop investigation

## Initial baseline — 2026-10-13

Code base: parent #1118 head 500f2714, fetched main ec1da1b7.
Plan: Campaign 2 Session 28, document a43bd39d-aeaf-45a8-a81a-06e51c4c1e9f (Mireward siege, unrelated to Mirathorn).

Observed existing Turn 6: question about Mirathorn; lifecycle running; no final Graph-context completion. UI Debug has no actual retrieval/result/context trace. A fresh World conversation was created via the UI and the exact first acceptance prompt, "Tell me all about Mirathorn.", was submitted once. Outcome is pending at this checkpoint; not counted as successful acceptance.

The existing service wraps adapter failures with `plan_context_delivery_failure` and "receipt was frozen". The operational AgentTurnTraceBuilder deliberately excludes prompt, args, result and tool-result content. It cannot alone satisfy the product context-inspection requirement. Hermes invocation accepts conversation history and retrieval-session state; continuity and persisted rehydration require further inspection.

## Coverage observations (not ingestion fixes)

Loaded atlas: 524 subjects, 341 connections, 30 source artifacts. Mirathorn has six direct connections and no summary. Sara has zero connections, two evidence references, one source artifact. Frank has no loaded node-label search match. Gate/Gates are separate nodes. Absence from this label search is not proof of absence from all admitted source evidence.

Local corpus comparison finds Sara and Frank in Sessions 12/18/20/21 and an operator dossier. Those local reads are investigation evidence, not an authorized runtime fallback or proof all these passages are admitted. Agent acceptance must use the actual published graph and source contracts.

## Required evidence ledger

- Initial overview and all three follow-ups: not yet proved.
- Conversation context retention and independent expansion: not yet proved.
- Compaction followed by exact source rehydration: not yet proved.
- Reviewable per-turn context trace and model/token usage: not yet proved.
- Read-only World/Plan invariant and no replay: required throughout.
- Tests, live transcript/trace and implementation PR: pending.

## Fresh four-turn baseline — complete run

All four prompts were submitted once via :5202 in one fresh World conversation, with Elderwyld facts enabled and unchanged saved Session 28 Plan. Each returned a saved answer. Delivery therefore succeeded for this run; the earlier stuck turn is a separate failure case.

1. **Tell me all about Mirathorn.** Answer retrieved C1 Session 6 outskirts/Outtown/festival preparations and gate toll protest, then C1 Session 7 unrest at the gates. It explicitly called this a partial picture rather than comprehensive history/current state. Debug showed completed Turn 1, partial graph grounding, three graph relationship claims with source passages read. Overview remains incomplete; no working-context trace was exposed.
2. **Who are its Rocky Talkie operators?** Exact answer: “The committed Plan does not identify any ‘Rocky Talkie operators,’ so I can’t determine who they are from it.” Debug: completed Turn 2, no sufficient World Graph evidence, saved Plan context only. This is a failed acceptance answer, not proof of absent operators.
3. **What happened the last time Caelynn spoke to Frank?** Exact answer: “The committed Plan is for C2 Session 28, ‘The Meat Mind,’ and does not describe a conversation between Caelynn and Frank, so it doesn’t say what happened the last time they spoke.” Failed acceptance: no rich source-backed Frank context.
4. **What could Sara tell us about the tainted provisions?** Exact answer: “The committed Plan doesn’t establish what Sara knows about the tainted provisions, so it can’t tell us what she could add.” Failed acceptance: no source-backed Sara context.

### Classification and next investigation

- **Delivery:** successful for the fresh baseline; earlier running/no-final-completion case still unresolved.
- **Retrieval / retention / expansion:** first turn retrieves some graph evidence; all three follow-ups fall back to Plan-only answers. Existing UI trace cannot establish whether searches were attempted or why evidence was omitted. Must inspect actual provider requests and broker events before attributing every failure to the model.
- **Source coverage:** sparse graph demonstrated; local corpus is richer, but admission and source-open availability must be checked through legal published reads.
- **Pruning:** no observable retained-context/pruning evidence; not proved.
- **Synthesis:** partial initial overview; subsequent answers do not satisfy the questions.
- **Trace:** operational logs omit content by design, and saved-turn UI only shows grounding/provenance. Product context trace is missing.

Code observations: `agent_turn_service` starts each bootstrap with a retrieval session and freezes an initial packet; receipt `included_history` is currently empty. Hermes restores native conversation history through its structured session pointer, so empty receipt history alone does not prove no history was sent. Current policy budget is four model requests (three tool-capable), eight graph operations. Source-read capability is enabled conditionally on initial bootstrap source anchors. Subsequent source reads validate against frozen admitted anchors. These are concrete seams to inspect for conversation-aware evidence re-admission and observable context management; weakening receipt validation is not an acceptable fix.
