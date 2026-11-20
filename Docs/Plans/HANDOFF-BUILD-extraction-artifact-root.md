# BUILD: launch extraction inside the retained artifact root

Status: DELIVERED — PR #1398 merged as 384d82ab2e915eeb3a0829f193caf7286a8a369b after ARCHITECTURE Cycle1 PASS on 725089d9b405165a0b44ca57460fc12a3ed6fe0e. The implementation lease is closed.
Base: origin/main@0b5b473babe1f512196d009de61830d6aca964c0.
Branch: codex/build-extraction-artifact-root; reuse buddy-context-loop checkout.
Topology: parallel-independent of DOGFOOD semantic World-scope repair (disjoint
route/tests); one PR. No new checkout, dependency environment or preview server.

## Invariant / critique

On5202 the operator's saved Edge Extract request reached the running API and
failed before provider execution: graph_preview.post_extraction_run built an
absolute output path under the code checkout, while the real worldbuilding
runner correctly resolves artifact_data_root and rejects output outside it.
Pass an artifact-relative output path to the runner. Preserve the runner's escape
check and source/revision/digest guards. Existing GenerationEngine profile branch
must remain unchanged. Do not change the configured data root or move artifacts.

## Exclusive write set

- This handoff
- apps/live_control_server/routes/graph_preview.py
- tests/test_graph_preview_routes.py
- Docs/Plans/HANDOFF-BUILD-play-answer-evidence.md (truthful predecessor settlement only)

Prove the actual HTTP launch crosses the real runner with separate code/data
roots, deterministic fixture provider, retained run/component readback under data,
source unchanged and no output under code. Cover unset-root compatibility and
existing runner escape rejection. Preserve real failure outputs. No provider call
or new operator extraction as part of implementation tests; no World publication.
Run owning tests on disposable APP-STATE only, never retained54330/54331. Stop
owned fixture server when consumers finish. Review cumulative diff, commit/push/PR,
ARCHITECTURE review, PRIME merge and same-port API rollout with retained-state
proof. The operator may retry extraction after delivery; do not claim successful
Edge enrichment until actual saved-run review/admission and traversal are proven.

## User-facing acceptance

The saved multimodal Edge page is source authority for extraction: authored text,
accepted generated text/tables, and associated media must retain source provenance
and draft/canon distinctions. This slice repairs only launch. It does not claim
all facts or media are represented in the graph, or authorize fabricated facts
from artwork. Verify the larger ingestion-to-traversal workflow separately.


## Verification

The new real HTTP/runner regression fails on exact base with the original
artifact-root ValueError; restored fix passes. Complete route and artifact-root
suites:41 passed on disposable54329 with10 inherited Pydantic warnings.
No provider calls; fixture client only. Existing compatibility and explicit
out-of-root rejection tests remain passing. Detailed local logs in existing
.pytest_cache/build-root-{before,boundary}.log. At that implementation checkpoint, review, merge and adoption remained open; the delivery record below supersedes it.


## Delivered boundary and remaining acceptance

PRIME adopted only the reviewed route bytes, SHA
c52451bf3c9e60a9ee115601997d69b9d01ab701a0ec3b1043155617cfbb7d46,
into the existing API service (first new PID 481953). Before/after checks proved
saved Edge snapshot, media library, conversation, Plan/Run and prior ingestion
state unchanged. No UI reload or provider call was part of deployment. Private
proof: build-root-rollout.json in the established jev-evidence-loop-20261016 state.

The operator then explicitly approved saved Edge r8 text/tables/media references
to DeepSeek via OpenRouter for one Gazetteer1.10 extraction. The browser produced
reviewable run 7931490b-c2c0-4671-870f-d34e50c92ebf, source SHA
30839d528ac5be3cb49ba654043ac4ac7746a736ae0668410369fc19d21c541f,
candidate SHA 60d067941ecf61befbf0ac896b7f6c2b0426d5b0da350b7dcd56751ceb48e9ab.
51 nodes/30 edges include all 40 table names and seven proposed businesses;
invalid quote count 0. The 20 civilian nodes are isolated, garrison-to-Edge is
deferred, and two source media IDs are absent from the candidate graph. No facts
were published and full enrichment/traversal is not established.

The live Gazetteer uses the separate GE branch; the repaired Focused-lore launch
branch is proven by the real HTTP/runner regression, not by relabeling that
Gazetteer result. No extra focused provider replay was performed.

Subsequent independently reviewed #1399 scope deployment restarted the API as
PID 493137 and again proved retained Edge candidate/ledger/provider attempts and
all earlier state unchanged. This did not remove or alter the #1398 route fix.
