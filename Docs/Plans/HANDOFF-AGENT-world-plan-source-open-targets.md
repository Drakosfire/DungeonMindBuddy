# HANDOFF — AGENT: project saved World Plan source-open targets

**Status:** ACTIVE — implementation candidate ready for PRIME's independent review. **Owner:** SERVER. **Authority:** PRIME's 2026-10-12 dispatch and ARCH ruling `/tmp/prime-s26-retained-activation/world-plan-source-open-contract-v1.md` (final SHA-256 `d1502b6cea6172e170a6008000bf0f60f99ce84635c37adc872bcd4a03f0dea4`). **Base:** fetched Buddy GitHub `main@8fce46de7e33bc352300abdf3ece0369a3ac1e68`, which includes accepted evidence binding #1088 and SOURCE reader #1089 (reviewed head `df8b3099f9fb220b18b97f42cfc097ea25a2a35f`). Core #114 merged at `13143455b304d748c249bd7bd628134c421bf6d9`. **Topology:** serial producer PR after both merged predecessors; DEMO may consume the published additive DTO on disjoint UI paths. PRIME owns independent review and merge.

## Primary outcome and contract

A completed World Plan turn exposes versioned `plan_context.source_open_targets` keyed by citation `claim_id`. Fresh delivery and reopened history use the same projector over the stored turn, without provider replay. A genuine `evidence_anchor` target joins a cited evidence ref to the exact same-turn `GraphSourceReadScopeV2.admitted_anchors` tuple under the stored graph authority. An optional producing-attempt validated read ID/outcome is audit metadata, never the opener. An old V1 or metadata-only turn has no target. The existing source-anchor read route re-resolves authority on click; this slice does not change that route.

A distinct `related_recap_context` target may be projected only by a read-only Core metadata join at the same frozen native GM cross-campaign World/revision: citation target/ref → Core `get_evidence()` admitted source anchor (including unreadable) → exact artifact/source revision → complete Core context index descriptor. Require target found, complete/nontruncated anchor coverage and exact snapshot; an incomplete read yields `metadata_unavailable`. A complete read with no descriptor match yields explicit `no_context`; multiple matches yield deterministic choices, never a silent first choice. The target carries Core's context ID and exact descriptor tuple/selector, is labeled “Open related recap context,” and cannot enter claim support or source-opened citation fields. The SOURCE reader owns index/read routes. Old opaque evidence need not appear in the *eligible evidence-read* scope for this separate context join. Never derive a pair from an evidence label, slug, model text, or unbound catalog. The separate Agent Harness `read_related_recap_context` tool and APP context execution receipts are successors, not this slice.

## Exclusive write lease

- `apps/live_control_server/models/agent_turn.py`
- `apps/live_control_server/services/agent_turn_service.py` (`project_plan_turn_context` and local projection helpers only)
- `tests/test_agent_turn_service.py`
- `tests/test_live_control_server.py` for history-route serialization
- this handoff and the completed predecessor handoff above

No APP schema/storage/completion mutation, SOURCE adapter/service/route edit, UI edit, provider call, runtime restart, native Graph/DB/corpus write, or source body duplication. If a new durable receipt or other owner path is needed, stop for ARCH's precise contract. Avoid concurrent edits to `agent_turn_service.py` from other lanes.

## Acceptance witness and stop conditions

- A validated V2 completion with one cited, admitted genuine anchor projects the exact claim/anchor/evidence/artifact/source-revision/native-World/scope/revision tuple. The same stored turn yields the same target in fresh and history serialization; no provider call is made.
- An included producing-attempt source-read receipt may add read ID/outcome audit metadata. A nonproducing, failed, foreign, or mismatched read cannot do so or upgrade claim support.
- V1/no scope, foreign World/scope/revision/evidence/anchor/artifact/source revision, and descriptor digest/selector mismatches fail closed. Legacy opaque anchors remain unavailable as evidence openers without erasing Graph knowledge.
- A `related_recap_context` target appears only for the exact admitted target/ref → artifact/source-revision → authorized descriptor join and remains visibly distinct from evidence support. Explicit statuses distinguish a complete no-match, multiple choices, and unavailable metadata. A missing provenance tuple yields no context target.
- Run focused projector and mounted history-route tests, relevant lint/type gates, and inspect the cumulative base-to-head diff. Record exact implementation head and evidence, push the branch, open the assigned PR, and hand it to PRIME without merging.

## Implementation evidence for PRIME review

Code/test head: `c061f9ffcc06f31fe5dde904bd0c721d14a25c36` against exact merged base `8fce46de7e33bc352300abdf3ece0369a3ac1e68`. The additive DTO was published early on this branch for DEMO; the earlier `b02d45f1` pin is superseded. The final PR head includes this evidence update only after the code/test head.

- Focused exact command: `PYTHONPATH="$PWD/src:$PWD" /tmp/buddy-core113-recap-reader/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_agent_turn_service.py tests/test_agent_turn_route.py -k 'history_projection_keeps_receipt or v2_completion_opens_citation_only_from_producing_source_envelope or history_http_route_serializes_mixed_v1_and_v2_turns or completed_graph_receipt_replays_frozen_snapshot_projection'` — **4 passed, 105 deselected**. The V2 test uses a valid completed opaque-only turn with no eligible evidence anchor, fake Core `get_evidence` metadata, a complete context index, and the mounted history route. It checks fresh/reopen parity, exact frozen cross-campaign GM/revision pin, producing-read audit metadata, deterministic choices, no-match, incomplete evidence/index, wrong source revision, and invalid selector. No provider or native DB call occurs in this test.
- Changed-path Ruff passed; `git diff --check` passed. Two inherited Pydantic field-shadow warnings appeared in the focused route test, with no failures.
- SOURCE #1089 independently proved actual read-only S22/S23 authorized descriptors and digest-verified bounded source passages at the pinned native revision. This producer's Core join is tested synthetically at its boundary; it has **not** been replayed against those private native citations, and no live runtime/user click was performed here.
- Cumulative diff changes only the two handoffs, the Agent response model, the saved-turn projector, and its focused service/history test. APP state, SOURCE routes, UI, corpus, and native Graph are untouched.
