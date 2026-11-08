# RETRIEVAL: reconstruct native bindings without a JSON round trip

Status: ACTIVE under the user's retrieval backend goal. Root owns implementation;
PRIME owns merge and delivery. Branch `codex/native-binding-reconstruction`, base
`64cb0b5c89f685505c7558207e4943e6cf76cac4`. Topology: serial, one implementation
PR, no unmerged parent. The rejected names experiment is not a dependency.

Outcome and hypothesis: replace only the context JSON serialization/parsing round
trip in `validate_context_binding` with a Python-mode field dump followed by
fresh typed reconstruction. Keep the original execution JSON codec: its strict
Build Capabilities dataclass cannot be reconstructed from a Python-mode dict. Retain every structural, policy, source, selected-read,
request, mutable-component and durable binding check. No model-instance shortcut,
cache, fallback, batching, new representation, schema or model-visible change.

Expected exclusive writes: this handoff;
`src/application_state/agent_conversation/native_execution.py`;
`Docs/Plans/HANDOFF-RETRIEVAL-validated-execution-admission.md` for truthful
predecessor settlement. Root transfers these paths from its parked, unadopted
source-local-modality stack; no worker is active there. PRIME's creature delivery
has no overlapping source lease. Stop/split before expanding this scope.

Evidence: `retrieval-recorded-names-ordinary-v2/native-source-append-profile.txt`
profiles one synthetic source observation in a disposable schema133 evaluator
transaction, with rollback verified: 454ms inclusive, four binding validations
235ms inclusive, database waits72ms. Profiler overhead and nested spans prevent
treating these as exclusive ordinary costs. Atomic observation batching was held
because earlier successful observations must survive later failure/process loss.

The offline `binding-codec-prototype.json` preserves canonical output for eight
actual retained ledgers. Two samples per codec/ledger give median binding time
40.92ms versus34.55ms; this is a local hypothesis, not a whole-cycle speedup.
`codec-design-review.json` independently approves this bounded design. Strict
Python and JSON modes can reject malformed internal values differently; do not
claim identical exception text or rejection phase. JSON-value authority and
fail-closed behavior before persistence must remain intact.

Validation and acceptance: use the existing native execution, durable writer and
direct-source tests (113 predecessor checks), including Build/Plan/Play families,
callback-mutated receipt/execution rejection, stale/replay fences and durable
return reads. Add no correction tests or paid QA for this piping change, per the
user's explicit instruction. Retain the eight canonical comparisons and verify
the exact cumulative diff once with an independent reviewer. Any valid family
failure or acceptance widening rejects this codec; do not add a normalization
fallback. Model context, producer requests, retrieval selection and citations
must remain unchanged. Preserve failed verification and historical evidence.

Resources: fresh disposable test databases on evaluator55447 only. Preserve the
original evaluator, corpus/Graph/Gold and primary/live data. No providers, source
publication, ingestion, correction-child resume or live migration. Preserve the
original full15 baseline: six complete/nine partial. Full QA success and the
four-second retrieval target remain unproven after this slice.

Predecessor #2241 merged at64cb0b5c89f685505c7558207e4943e6cf76cac4 and PRIME
delivered API3a852858510df0a4495ec32dce8ffe27d6c4b813 on schema133. Its runtime
lease is released. This slice does not pre-mark its own implementation complete.

Rejected first variant: changing both codecs failed15 existing Build checks
(98 passed), because Python-mode dump expands its strict Capabilities dataclass.
The failure log and rejected source are retained in
retrieval-native-binding-reconstruction-v1. The context-only refinement adds no
normalization, alternate codec branch or fallback. Requalify its local gain and
all existing owner checks; reject if any valid family or authority check fails.

Current context-only verification:113 existing checks pass with14 inherited
serializer warnings (62.96s), and all eight retained executions remain canonical
equal with a fresh returned execution. Two local samples per ledger give median
binding38.06ms versus37.22ms, approximately0.85ms lower; no material latency or
statistical reliability claim. The original broader timing result does not apply
to this refinement. Deliver only as removal of the context JSON round trip; keep
the full retrieval performance and QA requirements open.
