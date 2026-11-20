# Grounding identifier instructions

Status: COMPLETED / BOUNDED LIVE ACCEPTANCE, 2026-10-19. Implementation write lease released; no successor or further provider replay authorized here. The final question completed with two recovered tool-refusal events, not a zero-error trace. This is one successful acceptance witness, not a guarantee of future model compliance. Base853cbceddbeff8fd6c5f4c957a1be1f525ecad67; branchcodex/plan-grounding-id-instructions; samecheckout; one serialPR, exactheadArchitecture review and PRIMEmerge/delivery.

Invariant: existing accepted Plan target-only response shape and exact-ID validator remain unchanged. Clarify which complete input field supplies canonical target IDs and distinguish answer-local claimlabels. No aliases/newselectioncontract/fuzzyrepair/parser/schema change. Automaticapprovalreview blocked a proposed broader target-ref contract before execution; this alternative only clarifies existinginstructions.

Historical implementation write lease (released): apps/live_control_server/services/agent_turn_service.py (newPlanpromptonly); tests/test_agent_turn_service.py (instructionassertionsonly); thishandoff and HANDOFF-PLAN-target-citation-binding.md acceptance-history sync.

Operator2026-10-19 explicitly approved this and other requested externalstorymaterialsharing. Live turn2d3f70f3-13e2-4996-a1e2-6592d93b4626 remainsfailed: correctcomplete record assertion:a9688d6c6ff9c2d4 waspresent, modeltarget assertion:a9683b58c67c8735 wasnot. No providerreplay ordocumentwrite. Protected12payloads unchanged. Existing5owning/8PG/Build36gates andstrictbadtargetnegatives remain. Newactualfreshquestionwitness afterindependentreview/mergedelivery authorized; exactoldturn neverreposted. ReuseAPIcandidate/runtime/correctCWD+UI5202, keep12payloads/UIindex.

## Completion evidence and limits

- PR #1469 merged at `7a96a2fde47c91672cd09f794c8a205b5e9e8146`;
  accepted implementation head `fb419e0c8132cd3cb62cefeb83f88a8b0fa9aeaf`.
  One formal Architecture review cycle: source APPROVE. Architecture independently
  passed six focused owning/instruction/legacy cases; Bugbot found no blockers.
  The accepted change modifies prompt guidance, not the wire or strict validators.
- PRIME's saved receipt records HTTP 200 after 67.33 seconds for client turn
  `6217b2ea-260a-4e19-9836-8e89bfbccfd4`; the distinct durable turn is
  `c3a8239e-415b-4097-a741-f7cb048e4c83`.
  Architecture independently inspected saved JSON offline: durable status is
  completed with no terminal failure code; the 2,896-byte assistant text matches
  the HTTP response and saved history, and their projected completion equals the
  durable completion. Both citation entries have opened-source read IDs.
- All six saved provider envelopes match their trace SHA-256 and byte counts,
  request `max_output_tokens=8192`, and contain no observations operation or
  observationIds selector. Trace capture and terminal status are complete/completed.
  This witness contains zero contentRef occurrences: it does not independently
  establish live deduplication, whose source-boundary tests remain separate.
- The trace retains exactly two `graph_retrieval / ambiguous_target` failures at
  14,059.11ms and 14,071.06ms. They are recoverable tool feedback preceding the
  successful completion, not hidden or deleted failures. The unchanged verifier's
  strict zero-trace-failures assertion therefore **did not pass**. Architecture
  accepts the final durable grounding witness with these explicit exceptions;
  neither the verifier nor its success criterion was changed or rerun here.
- Saved delivery and live receipts report all 12 protected payloads unchanged.
  Delivery records the accepted source head and unchanged UI index
  `b1586c0c597f8e2036f786697b80ad19ff8cb924ce7533c08445ce1ec0bff638`.
  API8000/UI5202 adoption is PRIME's evidence, not a reviewer runtime operation.
- PRIME additionally reported browser acceptance on 5202 Plan Cards: the saved
  answer loaded; Evidence Trail showed two claims, three Graph references,
  three source passages and one related recap; Open evidence opened a pinned
  passage, and notes/reflections links displayed pinned review 54. No draft or
  content input was touched. Screenshot capture failed twice, so this is an
  attributed DOM interaction report, not screenshot evidence. PRIME owns closing
  its temporary QA tab.
- Private evidence owner: PRIME. Saved artifacts remain under
  `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016/`
  with prefix `swamp-grounding-id-guidance-live`, plus
  `grounding-id-guidance-delivery.json`. Preserve the raw trace and historical
  failed turns; no additional provider call or artifact cleanup was performed.
  Any later cleanup or broader reliability work requires its own bounded decision.
