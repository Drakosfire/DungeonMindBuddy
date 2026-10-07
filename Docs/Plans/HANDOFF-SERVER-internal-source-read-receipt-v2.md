# HANDOFF — SERVER: internal source-read receipt V2

**Status:** ACTIVE under PRIME's bounded prerequisite lease. **Base:** Buddy `main@be48c3c846e2ba8f51330ccc1cf41b38c35f8680` after #1002. **Primary question:** Can the existing admitted-anchor source reader return a versioned internal receipt with the executor's own read ID and the authoritative source revision resolved during the same read, while leaving public retrieval V1 and default raw-tool behavior intact?

## Lease

Write only `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`, `apps/live_control_server/services/world_graph_retrieval.py`, `src/graph_memory/interaction/expansion_executor.py`, `src/graph_memory/interaction/session.py`, `tests/test_world_graph_source_admission.py`, `tests/test_graph_retrieval_interaction.py`, and this handoff. The direct reader owns resolved source revision and digest; the thin wrapper transports that internal value; the executor issues one read ID and uses it in both result and session ledger. Its V2 selector is a trusted caller parameter, never a model argument. V1 public request/result models and HTTP behavior stay unchanged.

An internal successful receipt binds active retrieval session, pinned Graph revision, admitted anchor/evidence reference, source artifact/revision/span, content and immutable revision digests, lines/truncation, outcome, and read ID. No caller-supplied metadata may enter those fields. A missing, stale, or mismatched binding cannot produce a successful receipt. Existing V1 tool result and ledger projection remain compatible by default. This slice does not add APP-STATE types, saved-Plan adapter, ingestion/discovery, dependencies, runtime switch, provider call, or product-state/native write.

## Stop and acceptance

Stop if the current reader cannot expose the authoritative resolved revision/digest from its same resolution/read, if the internal envelope needs a public V1 model change, or if an unleased path is required. Prove default V1 compatibility; same read ID in V2 output and ledger; exact source revision from `resolution.anchor.source_revision_id`; integrity against its immutable digest; fail-closed wrong/missing session, anchor, evidence, span, revision, or forged arguments. Run focused owning tests, relevant lint/type gates, and inspect exact cumulative base→head diff. Commit, push, and open one PR for PRIME independent review. Do not merge or deploy.

**Implementation head/evidence:** pending.
