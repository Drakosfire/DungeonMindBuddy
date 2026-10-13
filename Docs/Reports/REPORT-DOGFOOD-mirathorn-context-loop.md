# Mirathorn context-loop investigation

## Initial baseline — 2026-10-13

Code base: parent #1118 head 500f2714, fetched main ec1da1b7.
Plan: Campaign 2 Session 28 (Mireward siege, unrelated to Mirathorn). Exact runtime locators are kept in the private local evidence pack.

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

## Native execution diagnosis and first repair checkpoint

Read-only inspection of native Hermes SQLite messages (excluding all reasoning fields) confirms the baseline did invoke tools. Each turn nevertheless used a separate one-user profile:
- Overview: neighborhood + source read.
- Operators: one empty search for Rocky Talkie operators.
- Frank: broad Caelynn search and Frank search returned truncated results.
- Sara: neighborhood, six-anchor source read, then truncated search. Session row reports gpt-6-luna, 46,791 input / 1,665 output tokens across four API calls.

Exact session/profile locators remain in the private local evidence pack. This is execution diagnosis, not a graph storage bypass.

A pinned admitted Session 20 source read returned enough, truncated=false, at line 32. It contains the tainted-provision warning, Sara's trust concern, and the Tealeaf handoff. Another successful source read covers line 28 and her Mirathorn operator role. Exact source/anchor identifiers remain private. The Plan-only final answer therefore ignored actual admitted source content. Evidence representation and synthesis remain to be repaired; sparse graph relationships alone are insufficient explanation.

Verified continuity root cause: fresh policy turns perform pointer lookup before durable acceptance, under Plan/client identity, but completion stores under agent_conversation_segment with conversation/provenance-derived work identity. The first repair resolves the active server conversation and its provenance segment before assembly and uses the same server segment for completion writes. If active conversation changes before acceptance, provider dispatch is denied.

Prior tool transcripts must not count as current-turn admission. The new compactor keeps visible questions/answers and revision-qualified node/source handles, drops old tool calls/results, and removes repeated Plan bodies (the current Ask supplies its own exact Plan). Its deterministic decisions and route inventory are available internally; product trace persistence/projection is still pending.

Verification at this checkpoint: continuity/context/turn-service tests 101 passed, one PostgreSQL-owning route test excluded after its disposable server on :54329 refused connection. A broader harness run reached 42 passed then failed mixed_plugin_capability_policy_loads_both_surfaces with hermes_tool_surface_mismatch; the identical isolated test fails on unchanged parent #1118, so this is an inherited environment/tool-surface failure. Ruff and diff checks pass. No successor deployment or new provider acceptance run has occurred.

## Compaction review regressions — 2026-10-13

Independent review found that the first compactor fixture did not match the production message shape: `_plan_message` places the Plan/question JSON after its instructions, then the runtime appends Graph-answer instructions. The prior implementation parsed only the final line, so it retained the full Plan and instructions. `_question` now scans lines for the exact Plan payload and returns only `user_question`; a producer-shaped regression proves both synthetic Plan text and appended instructions are pruned.

The review also found that successful `partial` source reads were omitted from retained routes. The compactor now keeps an exact world/revision/anchor route only when the read has a recognized successful outcome (`enough`, `partial`, or `truncated`) and nonempty content; it still removes passage bodies from the next request. A partial-read regression proves the route survives while the prose does not.

Focused compaction tests: 5 passed. Broader context, continuity and turn-service tests: 103 passed, 1 PostgreSQL-owned test deselected because its disposable service was unavailable, 2 existing Pydantic warnings. Ruff and `git diff --check` passed. These checks do not prove live source rehydration; the four-prompt acceptance and owning PostgreSQL witness remain open.

## Post-repair live failure — 2026-10-13

Predecessor #1119 merged head `b0cd7045` as `a2b8db65`; 14 focused continuity/compaction/entrypoint cases passed on the final head. Independent review also supplied a real disposable PostgreSQL witness. 5202 was restarted from the continuity checkout; its tree matches merged main and UI/API/Graph health endpoints returned 200.

In one fresh conversation, the unchanged Session 28 Plan and exact prompt “Tell me all about Mirathorn.” produced a durable turn. It was submitted once. No answer was returned; no replay occurred. Exact runtime identifiers remain in the private local evidence pack.

Read-only inspection through the authenticated history API and the owning APP-STATE execution row proves: status `running`; three `gpt-6-luna` provider authorizations, each followed by `sdk_entered` and `response_received`; two validated graph expansions with distinct result hashes, both coverage incomplete and truncated; no validated source read; no fourth authorization or completion. The input accounting values 67,797 / 98,873 / 159,181 are conservative upper bounds, not actual model token usage. Current API history exposes only claimability/authorization projections, not the execution event list.

The API returned HTTP 503 and logged `provider_authorization_denied`, last runtime phase `host_result_decode`, `parent_authorized=True`, `turn_exists=True`. The phase is not proof of a decode exception. The later parent denial's exact cause is discarded by the public wrapper and absent from the persisted ledger. The UI shows the user message twice (saved row and local submitted row), leaves the composer locked, and Debug shows only generic uncertainty. This is a delivery/authorization failure after successful graph exploration; source expansion and synthesis are unproved.

Offline code inspection identifies a candidate failure mechanism: provider inclusion validation currently counts every matched tool output as admitted evidence, including parent-generated retrieval-error outputs, although those errors are not in the validated payload maps. A rejected source/tool operation could therefore poison the next model envelope. This is a hypothesis, not a claimed diagnosis of this live request: no retained provider envelope or tool-error observation exists to prove it. The next trace slice must preserve exact observable denials before applying a causal fix. Private diagnostic extracts remain local with mode 0600; neither contains hidden reasoning.
