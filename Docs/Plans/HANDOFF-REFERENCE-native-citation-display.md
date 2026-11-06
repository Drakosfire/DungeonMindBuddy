# REFERENCE: name opened native citations through the existing display owner

Status: MERGED, DELIVERED and ordinary citation opening VERIFIED. PR2170 product
6ca193ac8ac39d75ea5f170f6338065d51ad607d merged7afaab5cb23f605a70d45529dc9143c2b293999d.
Paired runtime5b28ad990b549ea0bd52387907655f5b04cadba1 is healthy on8000/5202.
Retained citation reopening resolved Sessions15–17 with exact citation/content
checks; ordinary UI verified Session15. APP/Core rows and session state stayed
unchanged, with zero provider calls. Private native-citation-display-ordinary.json
retains the proof. The implementation/runtime lease is released. Writer labels,
Play integration and performance/operator acceptance remain open; the consuming
Play slice is HANDOFF-PLAY-shared-native-retrieval.md.

Original base origin/main6f66622cccc9a316713e35b2d0cf3242eff46f66; branch
codex/native-citation-display-labels in the existing buddy-context-loop checkout.

## Outcome and critique

Ordinary turn64ccc839-cea8-4d07-9189-7d3bd39f2520 delivered a cited answer, but recap citations are named Introduction because the immutable evidence projection uses the first section label. Preserve its stored citations, producer hashes, exact original source revision and content. Reuse native_source_display after the existing citation reader refreshes Core access and verifies exact bytes. Resolve only the admitted artifact/revision/body hash from that prepared context; missing display metadata must not make an authorized source unreadable or supply a newer body/name as an exact historical label.

Return the optional resolved label in an ephemeral native-body read response v2. The UI uses a neutral source/extent label before opening and the resolved label after verification. Retire the v1 read DTO/caller rather than carrying an unnecessary fallback. This changes no persisted Turn or writer contract and needs no database migration. An old open client fails closed and must reload; delivery pairs the API and UI. Keep transport binding, World/turn/index/citation equality, exact excerpt hash and stale-read cancellation. Display metadata never grants source access, fact scope or grounding.

Independent design review approved this bounded reader approach. Writer composition and stored citation names remain an explicit successor: they require a captured owner-bound name contract that retained-completion validation can verify. This slice does not solve that gap or Play's older retrieval path and does not establish performance/operator acceptance. Do not add another source registry, provenance store, event family, prompt reconstruction, ingestion, model/budget change or manual Graph edits.

## Topology and exclusive writes

Serial product slice after2168. Existing INGEST PRs remain disjoint. Preserve held2104. Its liveApi.ts work retires the non-World Plan producer; PRIME explicitly splits this file lease so this slice owns only getAgentNativeBodyExcerpt's response type annotation, leaving2104's producer function untouched. No implementation runtime mutation lease; guarded delivery gets fresh pins after review/CI.

- This handoff.
- Docs/Plans/HANDOFF-WRITER-incomplete-debug-output.md: settle2168 merge/delivery and ordinary result.
- apps/live_control_server/services/native_source_display.py.
- apps/live_control_server/services/corpus_source_navigation.py: adopt the shared formatter, remove duplicate method.
- apps/live_control_server/services/agent_native_source_sections.py: native-body opening display only.
- apps/live_control_server/models/agent_turn.py: ephemeral body-read DTO only.
- apps/live-control-ui/src/api/types.ts: body-read response only.
- apps/live-control-ui/src/api/liveApi.ts: getAgentNativeBodyExcerpt annotation only.
- apps/live-control-ui/src/planSurface/components/sourceCitationReads.ts.
- apps/live-control-ui/src/planSurface/components/SourceCitationEvidence.tsx.
- apps/live-control-ui/src/planSurface/components/BuildSavedSectionEvidence.tsx: preserve savedSectionChoices string-only return type; no saved-section behavior change.
- apps/live-control-ui/src/planSurface/components/SourceCitationEvidence.test.tsx.
- apps/live-control-ui/src/shared/nativeSourceCitationProtocol.test.ts.
- apps/live-control-ui/src/planSurface/WorldPlanAgentConversation.worldHistory.test.tsx: existing body-read fixture only.
- tests/test_agent_native_corpus_sources.py.
- tests/test_native_source_display.py.

## Verification and delivery

Exercise the existing native citation owner against disposable APP/Core fixtures: real exact-revision reopening, matching admitted metadata, unavailable metadata, historical/current name qualification, and access denial before display lookup. Preserve existing body/source/hash and scope failures. Prove UI foreign/tampered responses still fail; a late title/content cannot attach to another turn; resolved title changes presentation only and copied content remains exact. Verify formatter parity for existing navigation/activity. Inspect cumulative diff, independent Bugbot review, typecheck/build and CI, then guarded paired UI/API delivery over current retained runtime. Ordinary dogfood reopens the retained successful citation without another provider call, Save or publication. Preserve all sources/drafts/session state.
