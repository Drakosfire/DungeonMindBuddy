# REFERENCE: native citations on lightweight saved messages

Status: PAUSED_FOR_HOST_METADATA_PRIORITY. PRIME owns design/implementation under the active References goal.
Base origin/main36d482c228e919d0f1d563121412eff085edda82; branch
codex/saved-native-citation-preview, existing buddy-context-loop checkout/dependencies.
Topology: parallel-independent of Retry2188 at a12c225991f5960375f0c5367e823152d5dbe596.
That PR owns retry.py/native ordinary retry fixtures. Its delivery coordinator was
stopped before changing this checkout (exit130 while waiting for CI; resource still
PREPARED_NO_RUNTIME_WRITE_LEASE). GitHub CI continues. Re-anchor its exact reviewed
head and immutable integration before later merge/delivery. No concurrent mutable
checkout consumer, new worktree/environment or runtime/DB/provider/migration lease.
INGEST lanes and held Play2172 remain outside this lease.

## One outcome and critique

Reopening the active conversation shows native citation markers without opening
Sources and actions or loading full receipts/execution. Source bodies still open
through existing exact native read owners. Current light messages omit completion,
so restoring citations currently requires a heavy full-turn read.

Add a distinct citation_preview presentation to the existing bounded active-message
response. Preserve actual segment order/text and complete ordered native citation
arrays/indexes. Omit collaboration/actions, execution/query, provider requests and
grounding status. Select only the actual saved Build source basis when needed;
never reconstruct a receipt or use today's page basis. Require exact body alignment.
Unsupported/malformed/mixed Rules rows keep text and explicit details fallback;
do not infer markers from prose or misclassify unsupported history as citation-free.

Adopt nativeChoices/nativeSavedChoices, SourceCitationEvidence and existing bound
GET/hash/identity checks. Native body/clause/assertion/section families share this
slice where their existing parsers/read owners fit. Older opened Graph and passage
families remain explicit subsequent adoption scope. Mixed Rules preview requires
its proper accepted-binding composition owner and is unavailable in this slice.
This does not complete full References or operator acceptance.

Keep the lightweight API page as its own typed presentation view outside verified
full history. Adapt messagePresentation for metadata comparisons; remove redundant
lightweight metadata/revision state in favor of the actual message page owner.
Never append preview fields to a verified history DTO or fabricate graph_context.
Factor structural citation checks from existing checks, retaining all receipt/query
membership checks in full inspectors. Preview is display metadata, not admission.

## Exclusive expected writes

- This handoff; predecessor design remains private evidence.
- src/application_state/agent_conversation/library.py and dedicated pure
  saved_citation_preview.py if needed.
- apps/live-control-ui/src/api/conversationLibraryApi.ts and a dedicated preview
  protocol/types module; no shared api/types.ts INGEST sections.
- shared/sourcePassageProtocol.ts: adopt the existing source-basis structural check.
- shared/nativeAssertionProtocol.ts and nativeStatementAnswerProtocol.ts:
  structural-check extraction only.
- planSurface/components/sourceCitationReads.ts: narrow required presentation
  inputs while retaining bound source read/hash checks.
- New SavedCitationAnswer component adopting existing answer/citation components.
- WorldPlanAgentConversation.tsx: lightweight read/pagination/display only;
  held Play2172 execution/context regions remain untouched.
- Owning library/API/citation protocol/component/history tests/fixtures, excluding
  Retry2188's test_surface_native_build_ordinary.py. Workflow only if a new owning
  test needs registration, limited to the appropriate existing test list.

## Verification and delivery

Prove repeatable-read pointer/page snapshot, ordered citation indexes, exact text,
actual saved basis, malformed/unsupported/null/failed/action and mixed Rules
true/false/malformed cases. Initial UI loading makes no full-detail reads; a marker
click makes exactly one existing bound GET. Verify hash/owner mismatch, stale and
delayed responses, pagination, pointer changes, draft/reference preservation and
unchanged full-details/action authority. Inspect cumulative diff, independent exact
head Bugbot review, owning checks/CI, commit/push/open PR. Compatible API/UI delivery
needs its own resource lease and ordinary reload/source-opening proof. Preserve all
retained data/failures; no ingestion, manual facts or token/output limit changes.

## Operator priority checkpoint

The operator made auditing/scrubbing all host-side model-prompt metadata the next
highest priority. This citation slice is not delivered or merge-ready. Preserve it
as a draft; resume only after the priority work or explicit resequencing.

Current evidence: TypeScript passes;45 focused UI/protocol cases and12 focused
mounted history cases pass. Full mounted run:598 passed/80 failed (all80 in the
older Plan/Play integration file; cause not yet classified). Server projection
unit cases pass23; library+route run had26 passing and5 failures, two fixed SQL
issues and three GM-authority fixture failures not yet proved inherited. Current
focused server run:37 pass/1 fail/3 excluded. The remaining new positive HTTP/native
fixture proves the SQL Rules-record-presence guard is too broad: its actual
answer_composition_kind is base even though a Rules execution record exists.
Use the existing composition owner before preview suppression; do not weaken it.
No runtime, primary data, provider or publication changes were performed.
