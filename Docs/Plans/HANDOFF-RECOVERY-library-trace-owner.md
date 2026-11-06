# RECOVERY: bind archived trace inspection to its saved turn

Status: ACTIVE. PRIME owns this confirmed activity/history repair under the current operator goal. Base origin/main a43553bf87fb9856c1bbdf3e8ca77767294109fb. Branch codex/library-trace-turn-owner in the existing buddy-context-loop checkout.

## Topology and boundary

Parallel-independent implementation beside API-only #2161 (reviewed b9350b54c110b53d387e0b25355f35ef2e53e3d4). No unmerged behavioral parent or overlapping product files. Reuse the same checkout serially between already committed/pushed branches; no other worker edits these paths. Runtime delivery is ordered #2161 first, then this UI slice with freshly captured resource pins; no runtime lease is granted by implementation. Preserve #2104's hold and all retained data.

Opening Trace on an archived original meat-monster failure currently throws “Trace inspection requires its turn owner” and crashes the conversation panel. The library's SavedTurnTrace directly mounts BuddyContextTraceLoader, while live and retry readers correctly adopt BuddyTurnInspection. Bind the saved reader to its actual selected World/conversation/turn/lifecycle. Do not use active-conversation identity, suppress the owner guard, synthesize traces, add a cache or replay a provider request. A foreign or late read must remain unusable for another selection.

## Exclusive expected writes

- This handoff.
- apps/live-control-ui/src/agentInteraction/ConversationLibrary.tsx.
- apps/live-control-ui/src/agentInteraction/ConversationLibrary.trace.integration.test.tsx (new real owner/loader integration).

Adopt the existing shared inspection owner and its demand, cancellation, lifecycle, binding validation and refresh behavior. Keep lightweight message preview and diagnostics-on-demand. No API/schema/provider, Run, draft, Graph, source or conversation mutation change. Unknown saved lifecycle values must be reported without inventing an owner state or crashing the surrounding conversation.

## Validation and delivery

Exercise the real library, real trace loader and real inspection provider: no trace read before expansion; failed archived turn loads its own full timeline; errors stay local and retry only the read; changing selection while a read is pending cannot expose the old result; foreign binding remains rejected. Keep existing library/retry/inspection tests and typecheck/build. Inspect cumulative diff, independent Bugbot review and CI, then merge/deliver under standing PRIME authority. Ordinary archived failed-turn inspection after reload must prove no panel crash and preserved failure timeline, without resending it. Operator/full-goal acceptance remains open.
