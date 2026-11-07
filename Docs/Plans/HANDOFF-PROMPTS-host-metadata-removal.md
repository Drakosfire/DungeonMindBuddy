# PROMPTS: semantic model inputs, host-owned control

Status: ACTIVE. Highest operator priority as of2026-11-07. PRIME owns audit,
sequencing and runtime fixes. Preserve the full retrieval/connected-authoring/
References objective; resume that work after this priority, without a new approval.
The operator explicitly requested finding all host metadata sent to models,
scrubbing it from prompts and leaving persistent instructions.

Policy: DungeonOverMind PR105, reviewed head24fed2d0b23e0e557006b3bb3d58fdea4cf0797f,
merged on main under Docs/Guides/GUIDE-model-prompt-context-boundary.md. It governs
product inference, not host debugging records or this non-runtime control plane.
No runtime may import Overmind policy files.

## Current authority and topology

Buddy base origin/main f4464ef720737669e1f4a6f28723046e02dcfb4f; branch
codex/prompt-host-metadata-audit in the existing buddy-context-loop checkout.
This first policy/audit-contract PR is parallel-independent of paused citation
PR2191 at7432e4f5b. That draft is not mergeable or delivered. Its source is preserved;
no citation changes belong to this branch. No new checkout, environment, provider,
DB or runtime write lease. INGEST owns its active extraction/review paths and held
Play2172 stays held. Inspect exact live callers and leases before editing them.

Retry2188 is merged f4464ef720737669e1f4a6f28723046e02dcfb4f and delivered through
independently reviewed integration03374f0108777da79ac1fe7e81f6a7c3016f4064. All7CI
checks passed on a single diagnosed timeout rerun; original cancelled attempt is
retained. API-only restart preserved UI, schema0124, all APP/Core rows and session
files. Runtime lease released. Original-attempt ordinary Retry dogfood remains
open and must not be represented as complete.

## First confirmed leaks and existing owners

| Role | Existing owner | Confirmed prompt issue | Next boundary |
| --- | --- | --- | --- |
| Native Jev navigation | jev_retrieval_contract.prepare_decision; PlanJevDispatch | context_accounting with tokenizer/version/multiplier/reserve/capacity policies and limits is copied into model state; phase also doubles as host accounting control | Separate semantic state from existing frozen accounting/dispatch checks |
| Jev final evidence selection | writer_evidence_selection.selection_state; WriterSelectionDriver | query/catalog/basis digests, source-basis machine identity and historical dispatch bindings enter model state | Keep exact closure and hashes host-side; expose source text/meaningful labels plus local aliases |
| Plan requested-work/placement | plan_authoring.prepare_requested_work_decision | authored_references.model_dump serializes the selected-reference records into semantic state | Audit actual selectors and project human context without weakening destination or captured-target authority |
| Native answer/authoring/image-direction writers | native_writer.model_frame/model_work_frame; PlanJevWriter; build_jev_writer; build_image_writer | Internal record IDs, digest handles, schema/receipt structures are mixed with actual text and necessary evidence qualifications | Preserve semantic qualifications and exact host claim/citation joins through local aliases |

The first navigation wire contained430 bytes of accounting metadata. This is a
confirmed boundary defect, not an explanation of183-second latency by itself.
The acquired-text feedback experiment also passed full read records; it is not a
production fix and must not be copied into a live prompt unchanged.

The table is an initial confirmed inventory, not a claim that all prompts are
clean or all callers are audited. Audit ingestion/extraction, semantic review,
Hermes tool results, Rules, media/image generation, alternate direct SDK calls and
GenerationEngine serialization too. Search results alone do not prove a live path;
trace each exercised caller to final provider bytes, including tools/system/state.
Do not edit INGEST-owned files without an explicit owning handoff/partition.

## Bounded delivery sequence and invariants

1. This independently useful policy/audit contract: Buddy AGENTS.md plus this
   handoff. No runtime behavior change. Check links/cumulative diff and independently
   review before push/PR/merge under satisfied gates.
2. Activate a separate runtime slice for one coherent decision boundary after
   mapping its current producer, actual wire, accounting, stored-proof reader and
   callers. Name exact files and versioning/reader-fence needs before edits. A host
   check currently reading model state must be relocated, never deleted or bypassed.
3. Repeat for the remaining model roles, preserving the full inventory and operator
   objective across slices. Combine only inseparable request/validation changes;
   stop and split new capabilities or owning contracts. Retire superseded current
   emitters; retain exact historical codecs only where retained data actually needs
   them. No compatibility execution fallback, second authority or new ledger.
4. Exercise final serialized packets and ordinary requests. Record completed and
   unresolved roles; do not declare all metadata scrubbed from a single role test.

Keep semantic source labels, chronology/campaign/session, attribution, uncertainty,
conflicts, source text and user scope/length/format constraints. Keep grants,
receipts, identifiers, hashes, accounting, capacity policy and telemetry host-side.
Model selection/citation aliases map through existing admitted records. Never
strip arbitrary user/source text using a regex or blacklist. Do not raise limits.

Each runtime slice needs sentinel tests on final model-visible bytes, preserved
semantic/negative authority tests, original failure retention, independent exact
head review, CI and protected delivery. Historical reads, scope/revision, stale
claims, original output binding, replay and native citation opening remain
fail-closed. No fresh ingestion or manually curated corpus/gold. Green packet tests
do not replace ordinary answer quality or operator acceptance.

## Current exclusive write lease

This policy/audit-contract slice owns AGENTS.md and this handoff only. Subsequent
runtime scope must be explicitly activated by PRIME at the owning boundary before
editing prompt/SDK/authority code. No live code reads this handoff as configuration.
