# Conversation library UI pass

Status: ACTIVE — PRIME owns this serial UI-only slice. Base1409297acb31ecfda52c47e8467582feebbe597f; branch codex/conversation-library-ui, existing checkout/dependencies. Operator requested Mobbin-informed usability and delight and chose one focused redesign. Shared ConversationLibrary changes apply to its Build/Plan/Play callers.

Job: find a retained chat, read it and deliberately continue. Preserve World/pointer command authority, uncertain retry identities, original drafts/references, preview/full-detail distinction, pagination, rename CAS, exports and recoverable Trash/Restore. No backend, data, routes, schema, dependency or global-theme changes.

Moves: compact list rows (ChatGPT screen eec67af2-b68a-4c8b-bf66-2f45102a0fa3 and Claude2243670f-921d-46eb-9ce2-eb24199ba09c); persistent reader title/action header with primary Continue (same anchors); move Rename/export/Trash into contextual actions (same anchors, Google Gemini a53ebb7d-9c80-42c8-bf34-2371411844c0 for export). Keep own tokens/gold accent; no reference branding. Reject table-oriented Gumloop direction.

Exclusive write set: this handoff; ConversationLibrary.tsx/.css/.test.tsx; host worldHistory tests only if selectors require adaptation; necessary predecessor handoff settlement. All paths under apps/live-control-ui/src/agentInteraction except explicitly named host test. UI5202 delivery lease only after review/CI and current process/claim re-anchor; API8000, APP/Core and evaluator55447 untouched.

Validation: existing lifecycle/name/export/detail/pagination/scope-race tests; menu keyboard/focus and compact header tests; TypeScript/build; exact cumulative review via independent Bugbot; UI union preserving live ingestion; desktop/narrow ordinary read-only dogfood and before/after captures. UI-only protected delivery after gates, no fresh provider call or data mutation. Broader reference goal remains paused.
