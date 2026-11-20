# Keep proposal acknowledgments truthful after review

SETTLED: PR #1697 merged at ada13b16ab0b6c1b8b009df02461b2af380e2028;
reviewed head acd14bd40b3bfcfa5467e1ff4cf88a66e94f0b16. Independent Bugbot
passed the mounted regression and 8 Rules/history checks. UI delivered; owned
rendered history shows neutral acknowledgments/current kept controls, unchanged
page content and no stale generation-time prose. Live full quality remains open.
Successor: HANDOFF-BUILD-draft-correction-priority.md.

Original serial PRIME implementation; branch codex/surface-proposal-acknowledgment,
base 45effa24e02c9a87a642f35e37c589840d88d618; existing buddy-context-loop checkout.
One capability/PR. Open hosted/Combat/Ingest lanes are disjoint. PRIME owns API8000
and UI5202; no live model probes during operator dogfood.

Ordinary rendered rehearsal correctly refuses an older proposal on a changed page,
but kept suggestions still display immutable generation-time prose saying they
await review and nothing was saved. Present a concise, neutral past-tense page
suggestion acknowledgment in the shared conversation renderer. Existing live
proposal controls continue to show current review/kept state. Remove the stale
awaiting-review claim from its source-label tooltip. Do not rewrite stored assistant
text, accepted completion, source authority, historical evidence or Debug prompts.
Do not hide ordinary discussion or source/rules answers.

Exclusive writes: this handoff; HANDOFF-BUILD-complete-followup-history.md and
Docs/Roadmaps/ROADMAP-demo.md for predecessor settlement;
apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx;
apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx.
No API/schema/model/corpus/dependency or retained user-source mutation.

Mounted authoring-history regression must prove concise visible acknowledgment,
neutral tooltip, preserved original immutable input and unchanged non-authoring
answers. Run affected shared conversation checks, typecheck/build, independent
exact cumulative Bugbot review, PRIME merge and guarded UI delivery. Reopen owned
rehearsal history, inspect kept/current controls and save a screenshot; no live
model requests or edits to operator pages. Full authoring/model acceptance remains open.
