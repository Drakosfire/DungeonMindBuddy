# HANDOFF — SOURCE: open authorized recap context in Buddy

**Status:** ACTIVE, 2026-10-12 — Core #114 resolved the ordinary cross-campaign World scope gate. **Owner:** SOURCE (Buddy reader); PRIME coordinates review and merge. **Base:** fetched Buddy `main@ef39f2e5c08bb851c5646c47586506d6e7150dd4`. **Predecessors:** Core #113 merged at `b883034fbb4a8ae2b1da894d7ff7d6ee34dc4491`; Core #114 merged at `13143455b304d748c249bd7bd628134c421bf6d9`, exact reviewed head `9e1f76a5ff270d6050be3463eb0b4902d4d87f4f`. **Topology:** one parallel-independent Buddy PR; no overlap with the separate evidence-ID/edge-ID producer repair in `src/graph_memory/interaction/authority_classifier.py` and `apps/live_control_server/services/agent_turn_service.py`. Core #114 admits pinned GM `WORLD_CROSS_CAMPAIGN` context index/resolve, preserves WORLD and CAMPAIGN semantics, and binds source campaign in the context ID. Its read-only native witness found S22/S23 among 19 descriptors at `rev:62820bcd7eca116af9d889e128fabf4e` with unchanged head. Buddy still must prove its own descriptor-to-local-passage read.

## User outcome and contract

A GM can enumerate Core-authorized recap-context descriptors for an exact native World/Graph revision, choose one, and open a bounded passage in Buddy's ordinary retrieval API. Core `SourceContextIndexRequest`/`list_source_context_index` and `resolve_source_context` authorize the exact source tuple and `recap_section` / `markdown-session-recap-v1` selector. Buddy verifies source URI containment, full local byte SHA-256, exactly one `# Session N Recap` H1 matching Core's session selector, and computes the section after that H1 through the next H1 or EOF. The result records actual URI/digest, heading and line range, section digest, truncation and same-tuple continuation. A context ID is not a source-evidence anchor, claim support, or a source-text quotation license. Old opaque S22/S23 evidence labels remain provenance but are honestly unreadable; existing modern digest-bound recap and worldbuilding evidence reads remain unchanged.

## §4 exact write lease

- `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`
- `apps/live_control_server/services/world_graph_retrieval.py`
- `apps/live_control_server/routes/world_graph_retrieval.py`
- `src/graph_memory/retrieval/models.py`
- `tests/test_recap_source_read_continuity.py`
- `tests/test_world_graph_retrieval_contract.py`
- `pyproject.toml` and `uv.lock` only for the exact merged Core #114 pin
- this handoff

No Graph/corpus/DB/runtime/provider/S28 write, `authority_classifier.py`, or `agent_turn_service.py` is leased. No UI or Agent Harness integration is claimed by this API slice; if the ordinary Agent cannot invoke the new context operation, that is an explicit bounded successor. The historical source-reader handoff and current Roadmap need no backward-looking sync beyond naming Core #113/#114 here; do not pre-mark this slice complete.

## Owning-boundary acceptance

The API must list exact, bounded descriptors and re-resolve the selected opaque ID under the same pinned GM projection before every local content read. Overflow, missing/changed descriptor, wrong World/campaign/revision, changed source tuple, URI escape, missing/modified bytes, invalid UTF-8, zero/multiple/wrong H1, malformed selector, invalid continuation, and oversized requests fail closed without content. Default bounded reads explicitly truncate, and continuation returns only the remaining bytes under the same immutable tuple. Old evidence IDs cannot call context open; context IDs cannot appear in claim-support/citation fields.

The focused contract/continuity suites must prove the new public route and native adapter, existing C2S1 digest-bound and worldbuilding reads, and no whole-document fallback. An actual read-only witness must obtain real S22/S23 descriptors from Core at an admitted revision, then open local sources at `sha256:06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083` and `sha256:77ba5030b5c89e8888e8a3d900fe3fc07b94313af81a7ad5f888eb663d4c7782`. The already verified local files each have one matching H1 at line 12 and section lines 13–38; that byte-only receipt is not a substitute for real Core descriptor authorization. S23 gold `e08ce9…` is distinct and must not be substituted. Publish only IDs/digests/ranges, not private passage bodies.

Stop if the merged Core DTO differs, a live descriptor is absent, an active path lease collides, or implementation needs another public contract/path. Bring the bounded PR to PRIME for independent review. No live runtime swap or provider replay belongs to this slice.

## Resolved activation gate

Buddy maps `scopeMode=world` to Core `ScopeModeV2.WORLD_CROSS_CAMPAIGN`. Core #113 rejected that scope while its `WORLD` branch admitted only world-owned recap artifacts, excluding campaign-owned S22/S23. Core #114 merged the scoped correction at `13143455b304d748c249bd7bd628134c421bf6d9`. Its tests distinguish cross-campaign union, world-owned-only `WORLD`, and exact `CAMPAIGN`; its read-only native witness found both S22/S23 under cross-campaign at the pinned head. This Buddy lane remains responsible for proving the source sections are digest-verified and openable through its own API under ordinary World scope.

## Reader verification at the pinned Core merge

The isolated Buddy lane pinned Core `13143455b304d748c249bd7bd628134c421bf6d9`. Its focused non-integration continuity/contract command passed **38 tests** (one integration test deselected), including a synthetic ordinary World-scope request returning a campaign-owned recap descriptor, fenced fake-heading rejection, and mounted route GM dependency/error-envelope checks. Changed-path Ruff, `git diff --check`, and `uv lock --check --offline` passed. The lockfile diff against Buddy main is limited to the exact Core pin and seven lines of uv-required metadata rather than unrelated package timestamp/wheel churn. A read-only native probe with `default_transaction_read_only=on` used Buddy `scopeMode=world`, `campaignId=""`, GM, and `rev:62820bcd7eca116af9d889e128fabf4e`: Core returned a complete index of **19** descriptors. Buddy opened S22 at digest `06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083` and S23 at `77ba5030b5c89e8888e8a3d900fe3fc07b94313af81a7ad5f888eb663d4c7782`; each was `enough` with heading line 12 and section lines 13–38. The native head was unchanged before/after. This proves the source-read seam, not an Agent chat answer, source claim support, provider dispatch, runtime activation, or S28 publication.
