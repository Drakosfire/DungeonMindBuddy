# AGENT: inspect the exact passage behind a source-only answer

ACTIVE under PRIME's authorized Graph collaboration goal. Base157f8d11e39772a7e857bc41e110479daa8d6ef7; branch codex/build-source-passage-reader in the existing buddy-tool-denial-delivery checkout. PRIME implements solo; ARCHITECTURE independently reviews. One serial PR, no new checkout, /tmp directory, environment, retained mutation, provider call or serving change. Predecessor1317 is merged; DOGFOOD1244 and heldMEDIA1306 have disjoint ownership.

## One outcome

A durable Build completionV2 is accepted in conversation history, its source evidence is inspectable through an explicit source-passage target, and an authenticated click reopens exactly the cited historical bytes. This completes the source reader consumer before ordinary Jev routing; it does not activate a new Agent driver or certify Mirathorn lifecycle completion.

The target is a closed world/turn/citation-index descriptor, distinct from Graph claim/evidence-anchor and recap-context targets. The server loads and independently validates the completed turn from APP, obtains the cited receipt from that immutable completion, and asks existing native Graph source authority to resolve/read the frozen Graph revision and source anchor. The response must match source revision, artifact/evidence/anchor, exact excerpt digest, character count, range, sufficient untruncated result and native scope. Current Graph head/source text, caller paths, controller-only receipts and trace snapshots cannot substitute for that authority. Later edits may leave old bytes accessible through immutable source storage; otherwise opening must fail explicitly rather than display replacement bytes.

## Exact expected writes

- This handoff; Docs/Plans/HANDOFF-AGENT-build-source-passage-writer.md factual predecessor settlement.
- src/application_state/agent_conversation/service.py: read-only World/turn inspection getter over existing repository reconstruction.
- apps/live_control_server/models/agent_turn.py: distinct source-passage target/read DTOs.
- apps/live_control_server/services/build_jev_writer.py: distinguish native whole-source contentSha256 metadata from the validated excerpt digest; retain exact raw-body versus receipt hashing. Required by the real immutable-source test, not a new writer capability.
- apps/live_control_server/services/agent_source_passages.py: new receipt-bound historical opener over existing native source read contract.
- apps/live_control_server/routes/agent.py: authenticated GET for a completed turn's indexed source passage only; reject query selectors.
- apps/live-control-ui/src/api/liveApi.evidenceReads.test.ts: source-passage bearer/session/loopback/redirect and exact-route client regressions.
- apps/live-control-ui/src/api/types.ts and src/api/liveApi.ts: completionV2/source-passage DTO and exact GET client.
- apps/live-control-ui/src/planSurface/components/BuildSourcePassageEvidence.tsx and .test.tsx: source-class-aware read UI, explicit opening, stale-response protection, all unique passages reachable.
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx: mounted V2 Build history and exact source passage consumer.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx: strict V2 history/response validation and evidence-tab consumer only; preserve existing Graph, authoring and image capabilities.
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentAnswer.tsx: only the five pre-existing Markdown table narrowing errors that prevent validating the new consumer build; no presentation redesign.
- tests/test_agent_build_source_passage_reader.py: actual mocked producer→APP reload→authenticated open, native adapter seam failures and immutable-source read after edit. Existing tests/test_agent_build_source_passage_writer.py only if fixture sharing requires it.

No APP migration, native Graph implementation/authority, source publication, ordinary Harness routing, runtime or corpus changes are leased. Explicit source/Graph attribution remains distinct. Public DTOs do not elevate passage attribution to semantic entailment or Graph truth.

## Owning verification

Prove authentication and World/turn/index binding; unfinished/other-contract/missing turns; exact native revision/source/byte/range/visibility failures; complete original passage after an edit using immutable source storage; unavailable/corrupted source refusal. UI checks must cover strict V2 validation, explicit read, all unique sources, failed opens, tab preservation, older Graph contracts, and stale responses after target changes. Run the relevant API/APP/UI suites and typecheck/build; preserve inherited failures honestly. No rendered or live-provider acceptance is claimed by unit tests. Preserve exact request/response evidence and beginning/end refs privately. Independent review precedes PRIME merge; both serving API/UI consumers must be matched before later rollout.

## Implementation evidence and limits

The producer → APP reload → authenticated source open tests use mocked SDK transports and native Graph resolution with real disposable PostgreSQL. The lifecycle case additionally uses the real workspace source registry, immutable APP source storage, actual Tiptap Markdown prepare/commit edit, removal of the old span index, and the product Worldbuilding source reader. It proves old bytes after edits at that boundary; native Graph publication and retained Mirathorn operator acceptance remain unproven.

That real-source case exposed a prerequisite correction within this slice: native result contentSha256 is the entire source revision digest, while the ledger receipt content_sha256 is the exact excerpt digest. Writer validation now hashes the exact raw excerpt against its ledger receipt without comparing it to the whole-source metadata. The opener separately verifies native whole-source metadata against the resolved source revision and hashes the returned excerpt against its original receipt. No digest is normalized into a different authority.

UI tests include strict V2 attribution validation, explicit reads, wrong identity/body/citation rejection, all unique passage navigation, Unicode length/hash handling, stale-response disposal, separate Prompt tab, and a mounted ordinary conversation history consumer with its real receipt digest check. TypeScript and the production Vite build pass; Vite retains its existing large-chunk warning. The wider history suite passes204/205 on the initial run; its lone rich-text exact-node assertion fails identically on base157f8d11e (same source and same dependencies). The added mounted source-only test passes separately. No runtime or visual/operator acceptance is claimed.

Independent ARCHITECTURE review of5edaa5d4c found one P2: the new GET was missing from the existing native-authorization client classifier. The correction adopts that existing policy for the exact indexed source-passage route and extends the existing evidence-read tests, covering bearer, cookie bootstrap/recovery, loopback restrictions, redirect refusal and near-miss isolation. No new auth mechanism is introduced.
