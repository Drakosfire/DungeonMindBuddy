# AGENT: one source-passage writer with durable attribution

Status: ACTIVE under PRIME's source-faithful Graph collaboration goal. PRIME implements solo; ARCHITECTURE independently reviews the exact implementation head. Base `53c9fd723258a4a528fdfb81ee725497fb7ebbae`; branch `codex/build-source-passage-writer`, existing `buddy-tool-denial-delivery/DungeonMindBuddy` checkout. No new checkout, source copy, environment or /tmp directory. One serial implementation PR; no serving changes or real inference in implementation/review.

## One capability

Parent-verified opened passages → exact one-shot writer envelope → genuine mocked SDK response → durable Build completion V2 → fresh APP reconstruction with producing-envelope source attribution. This is the backend producer required before the ordinary Jev/one-writer route can be adopted. It does not complete ordinary routing, UI adoption or operator acceptance.

The source assessor is not a gate: isolated V2 rejected 12 well-supported Council observations in independent review. Preserve that experimental HOLD. No assessor thresholds, verdicts, hand-selected exclusions or gold-specific requirements enter this writer.

## Authority and representation

1. Freeze passage handles deterministically from selected acquired provenance and complete parent-delivered source reads. Require enough, sufficient, untruncated, exact body/hash/range/source revision and frozen World scope. Deduplicate identical source passages without dropping any receipt mappings. Saved Build sections retain their separate source class and selected-section receipts.
2. Remove observation/assertion prose, initialClaimPacket, discovery excerpts, controller judgments and Graph target IDs from the writer envelope. Retain all original Graph navigation/evidence in host history. Only source-attested headings, exact passages, question and necessary source qualifications are writer input. Reference text is data, never instructions.
3. Model output uses `source_passage_claim` text with frozen short passage handles. It must not emit `graph_claim` or claim Graph truth. Explicit `source_insufficient_evidence` may abstain with connective-only segments and no citations; the producing writer must still include actual completed reads. Host derives source citations from handles; source grounding means attribution, not guaranteed semantic entailment.
4. Reuse `ValidatedSourceReadEventV2` and `ProviderAttemptAuthorizedEventV3.included_source_read_event_ids`; no extra execution event is needed. Build completion V2 citations bind producing writer UUID/envelope hash, validated read event, read ID, exact anchor/evidence/source/revision, excerpt digest/range, segment index and text digest. APP independently validates on complete and fresh reload against the producing writer's included receipts, not any controller/earlier read.
5. Reject invented/swapped/foreign handles, omitted or controller-only reads, stale envelope/body bindings, partial/truncated reads and Graph claims in this explicit mode. Capture raw provider answer before parsing. Preserve existing aggregate bounds and V1 serialized history semantics.
6. Store receipt hashes/ranges rather than copying passage bodies into completion. Prove the immutable historical source authority can reopen and verify the same passage after a later source edit; do not substitute latest source or Graph state. The distinct public source-passage open target and matching UI reader are the immediate consumer slice before ordinary/runtime adoption.

## Exclusive expected writes

- This handoff.
- `apps/live_control_server/services/build_jev_writer.py`: explicit immutable source-only projection/prepared-body validation.
- `apps/live_control_server/services/agent_turn_service.py`: writer staging, authorization, completion, parser and response projection only; the shared exposure helper adds completed parent read-event selection solely to support repeated identical source bodies.
- `src/application_state/agent_conversation/types.py`: closed V2 segments/citations, unions and independent receipt validation.
- `src/application_state/agent_conversation/service.py`: complete/replay validation integration.
- `src/application_state/agent_conversation/repository.py`: typed reconstruction only if current union parsing requires it; existing JSONB storage remains.
- `apps/live_control_server/models/agent_turn.py`: explicit V2 response union.
- `src/application_state/migrations/versions/20261017_0029_build_source_passage_completion.py`: closed SQL V2 completion branch; preserve Plan/V1 rows and reject downgrade with retained V2.
- `tests/test_agent_build_source_passage_writer.py`: actual SDK/parent broker/disposable APP producer and fresh reconstruction proof.
- `tests/application_state/test_build_source_passage_completion.py`: independent typed/SQL/replay receipt fences and historical-source proof.
- Existing owning suites `tests/test_agent_build_jev_single_writer.py`, `tests/test_agent_build_saved_sections.py`, `tests/test_agent_build_section_inclusion.py`: only required regression/adaptation coverage.
- `Docs/Plans/HANDOFF-AGENT-jev-isolated-assessment.md`: factual predecessor settlement and semantic HOLD only.

PRIME explicitly splits its own held MEDIA #1306 lease: this lane owns the named Agent service writer/parser/projection functions; MEDIA's image/authoring helpers and Harness capability installation remain excluded. DOGFOOD's Ingest selector lane is disjoint. No Graph authority, corpus, retained database, runtime, credential, image or authoring-tool changes.

## Migration reservation and adoption order

Main currently ends at APP0027. Held MEDIA #1306 reserves0028 and remains DO NOT MERGE/DEPLOY. This lane reserves distinct0029, based on merged0027; it will be the sole migration head in its own PR. Before any future MEDIA merge, PRIME must rebase its held0028 migration to descend from accepted0029 (or explicitly renumber it) and rerun migration gates. Do not merge competing heads or depend on held MEDIA behavior. Both API consumers must understand V2 before any shared retained APP deployment writes V2. No deployment is authorized by this producer PR.

## Owning proof and next acceptance

Actual mocked SDK → real broker reads → exact source-only writer wire → typed host completion → disposable SQL persistence → new service/repository reconstruction. Cover performed-but-omitted reads, controller-only inclusion, swapped handles, cross-subject provenance, truncated/repeated reads, stale envelopes, source edits and exact idempotent completion. Keep existing Graph/saved-section and authoring behavior passing. Inspect cumulative diff and send one implementation PR promptly for ARCHITECTURE review before PRIME merge.

Merged as157f8d11e39772a7e857bc41e110479daa8d6ef7 after independent ARCHITECTURE review. The active source-passage-reader handoff builds the distinct authenticated reader/UI first; ordinary Jev routing remains a later slice, followed by tests Float Goats, Council and unseen/missing/conflict cases with one Luna writer. Full Mirathorn source→ingest→publish→ordinary answer→restart/historical opening and operator inspection remain the product acceptance test.

## Implementation evidence and limits

118 owning tests pass across the new SDK/APP suites and existing writer/saved-section/inclusion suites. These exercise genuine mocked TypeSafe/OpenAI SDK dispatch gates, real parent broker operations, disposable PostgreSQL migrations, V2 completion, fresh service/repository reconstruction, source+saved-section separation, repeated-body receipt preservation, omitted/controller-only/foreign/stale citations, cross-source mapping failures, partial/truncated/insufficient refusal, exact completion replay and explicit connective-only abstention. Native JSON Schema is sent through the existing guarded GE TextRequest support with zero conformance/transport retries; unvalidated response bytes are captured before host parsing. No real provider calls occurred.

Scoped Ruff and cumulative diff checks pass. Changed writer/model files have no Pyright diagnostics; the larger APP types file has23 inherited errors, reproduced on exact base53c9fd7 with the same runtime/import paths. No new error location was introduced; no clean whole-repository typecheck is claimed.

The source-only producer is not selected by ordinary conversation yet. The later-edit test proves frozen attribution remains unchanged after a working-copy edit; it does not prove a public historical passage-open endpoint. That distinct open target/UI reader and immutable-source reopening after retained edits remain required consuming work before ordinary/runtime adoption. The full Mirathorn lifecycle is incomplete. Held MEDIA1306 and serving5202/5876 remain unchanged.
