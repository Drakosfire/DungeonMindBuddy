# BUILD: fresh authoring retry through ordinary controls

ACTIVE · PRIME · serial successor to merged2379/022920058bd51293f1c4879b6dec35b8883a71fd.
The failed native request retains its page and draft, but every Build Retry was
sent to the retained-discussion reader. Preserve that reader's no-write guard.
APP now identifies only its exact authoring-required refusal with a typed409.
The UI responds by using existing normal Build capture/dispatch with a fresh
capability, original question/references and retry_of lineage. Do not infer an
operation from a missing resolution or from a write capability.

Require the original page, same active World/conversation and unchanged read/
placement fences; use current captured page context. Retained discussion retries
continue across pages without current editor capture. Unknown outcomes, existing
results, stale predecessor revision and reused capabilities still fail closed at
existing APP admission. Preserve newer composer text/references and old failures.
No automatic send, Save, generation, publication or navigation.

Branch codex/build-authoring-retry, reused buddy-context-loop. Exact lease:
agent_conversation/retry.py, routes/conversation_library.py, conversationRetryApi.ts
and its test, WorldPlanAgentConversation.tsx, existing planPlay integration tests,
test_conversation_library_routes.py, test_build_turn_retry.py,
test_surface_native_build_ordinary.py (real pre-resolution failed-authoring retry),
this handoff.
No conflicting active PR; no ADVERSARY coordination or schema/dependency change.
Independent review; owning backend/API and real mounted composer regression tests,
exact local hosted/discovered qualification, protected API/UI delivery. Preserve
failed turn1a684bbf-8025-49a0-b866-21ac5daa7fe6 and its diagnostic.
