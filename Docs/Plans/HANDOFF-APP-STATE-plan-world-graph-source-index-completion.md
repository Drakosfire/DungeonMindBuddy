# HANDOFF — APP-STATE: source-index-backed Graph completion evidence

**Status:** ACTIVE — implementation authorized by PRIME on 2026-10-07.
**Base:** Buddy `main@3d59386fd4868e5b365fd8b6210cfa8ea909e78b` (#1011 merged).
**Predecessors:** APP-STATE Graph execution V2 #1004, SERVER source-read adapter #1008, bounded native source-anchor index SDK seam #1010, SERVER bootstrap aggregate #1012, and accepted design #1011 are merged. Preserve their V1/V2 history and behavior.
**Topology:** serial, one APP-STATE implementation PR after SERVER #1012 and design #1011. Branch `codex/app-state-index-completion` in the isolated `app-state-index-completion` worktree. Do not merge; PRIME requires independent review before merge.
**Write lease:** `src/application_state/agent_conversation/types.py`; `tests/application_state/test_agent_conversation_service.py`; this handoff. `tests/application_state/test_agent_conversation_postgres.py` may be added only if required to prove unchanged JSON persistence. No other paths are authorized.

## Mission

Define the narrow APP-STATE completion rule that lets a claim cite a source discovered through an explicitly selected source-index aggregate, while preserving the frozen initial Graph packet and V2 source-read receipt model. A source-index entry is metadata for selecting an admitted read scope. It is never itself evidence, a claim, an access grant, a Graph operation result, or proof of corpus-wide coverage.

This ACTIVE handoff authorizes only the APP-STATE completion validation branch and its owning service tests within the write lease above. It does not authorize migrations, UI changes, provider calls, production data writes, a new retriever/store, a new source-index/execution schema, or changes to SERVER aggregate construction.

## Accepted contract

Use the existing Graph packet V1 receipt and V2 execution scope to represent the aggregate candidate set. Introduce the exact selection-policy literal already named by the SDK predecessor contract:

```text
parent_initial_retrieval_with_bounded_source_index_v1
```

For this exact `PlanWorldGraphPacketV1.selection_policy_version` only, the packet's `candidate_evidence_ref_ids` is the sorted unique union of the initial packet evidence refs and the complete bounded index evidence refs. The exact initial claim packet remains an input to a new canonical `retrieval_packet_sha256` composite; initial assertion/relationship candidate IDs, sufficiency, coverage, truncation, omission reasons, result limit, and assembled/dispatched IDs retain their initial retrieval meaning. The final aggregate packet's `retrieval_status` may be `complete` when index candidates are present, while `evidence_sufficiency_status` and packet dispatch remain based on the initial retrieval. An aggregate candidate is not permission to dispatch index evidence or admit a Graph target.

Define the composite retrieval digest as SHA-256 over canonical JSON UTF-8 using `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`, and `allow_nan=False`, with this payload:

```json
{
  "schema": "dmb_plan_retrieval_composite_v1",
  "selection_policy_version": "parent_initial_retrieval_with_bounded_source_index_v1",
  "initial_claim_packet": {"...": "the exact initial claim packet before candidate aggregation"},
  "source_index": {
    "schema": "dmb_bounded_source_anchor_index_commitment_v1",
    "world_id": "...",
    "graph_revision": "...",
    "status": "complete",
    "max_entries": 512,
    "eligible_count": 2,
    "source_pins": [
      {"anchor_id": "anchor-initial", "evidence_ref_id": "ev-initial", "source_artifact_id": "artifact-initial", "source_revision_id": "source-revision-initial"},
      {"anchor_id": "anchor-index-9", "evidence_ref_id": "ev-source-9", "source_artifact_id": "artifact-9", "source_revision_id": "src-rev-3"}
    ]
  }
}
```

The exact canonical payload is `{schema: "dmb_plan_retrieval_composite_v1", selection_policy_version: "parent_initial_retrieval_with_bounded_source_index_v1", initial_claim_packet: packet, source_index: commitment}`. The final packet stores that digest in its existing `retrieval_packet_sha256` field. Never include the final aggregate packet or its composite digest as the `initial_claim_packet` input; that would be recursive. The normal V2 `execution_policy_sha256` formula and meaning do not change: it continues to bind the final context receipt digest, source scope, execution policy, and budgets. No extra execution-policy digest field or new source-index schema framework is proposed. All legacy V1/V2 packets keep their old digest inputs and behavior.

SERVER #1012 already owns aggregate selection. It combines the complete index source pins with initial-search pins, verifies initial pins against that index, constructs the aggregate candidate evidence union, and freezes the composite packet digest. APP-STATE consumes that frozen receipt/scope; it does not repeat source-index selection. It requires every V2 scope evidence ref to remain in the aggregate candidate set using the existing subset validator. No APP-STATE rule may treat the candidate union as dispatched evidence. Overflow, stale/mismatched pins, more than 512 scope anchors, or more than the packet's 1024 candidate-ref limit fail closed upstream. This contract does not assert full-corpus coverage.

The selected policy is *parent the initial retrieval packet; use every tuple from the complete bounded index snapshot for that same pinned projection; union candidate evidence refs; retain exact pins in V2 scope; reject bounds instead of truncating*. Core #99 is pinned by Buddy #1010 at `5d4e98963991995bdc280e57df52b8d0fe8de79e`; Buddy #1012 freezes the complete index under `dmb_bounded_source_anchor_index_commitment_v1`. The SDK result remains metadata only: identity/revision tuples, no source body, path, or locator. Do not infer that an index result is relevant or citeable merely because it is present in the scope.

## Completion evidence rule

For this exact policy version only, an otherwise valid Graph claim may use an evidence ref outside the frozen initial packet’s candidate/dispatched evidence sets only when all conditions below hold:

1. The claim is for a Graph target independently admitted into the *producing provider attempt*: its ID is in that attempt’s `included_assertion_ids` or `included_relationship_ids`, and the target itself comes from the initial dispatched Graph packet or an included, validated Graph-operation event. Index metadata cannot introduce target IDs. Candidate-only, scope-only, dispatched-but-not-included, or non-producing-attempt targets do not qualify.
2. The claim’s sorted, unique evidence refs exactly match its citation-map entry as under existing V2 validation.
3. For every evidence ref outside the initial *dispatched* evidence IDs, the ref must be in the aggregate candidate set and frozen V2 source scope, and the citation names a successful source-read receipt ID from a validated source-read event included by the same producing `ProviderAttemptAuthorizedEventV2`. The receipt binds that exact evidence ref, anchor, source artifact/revision, and nonempty returned content SHA-256; its content-bearing outcome is `enough`, `partial`, or `truncated` under existing V2 rules. A read in a prior or non-producing attempt is insufficient.
4. The source read was authorized against the frozen aggregate V2 scope and actually executed through the existing active retrieval session/readable-anchor path. Membership in the aggregate scope or source index alone does not grant read access. SERVER revalidates live World/Graph/source revision and readability at the source reader.
5. APP-STATE derives `source_opened` from those successful receipt links, and derives answer-context status from the cited producing-envelope evidence under existing sufficiency/coverage/truncation rules. Partial or truncated support is not silently upgraded to complete support.

Evidence refs already in the initial dispatched set retain the existing completion path. For each out-of-dispatched evidence ref, require both the successful read proof above and an included validated Graph-operation event in `claim_graph_event_ids[claim_id]` that binds the claim's exact target and that exact evidence ref. That operation event must itself be included in the same producing provider attempt's `included_graph_event_ids`; the target must also be included in that attempt's assertion/relationship IDs. The source read receipt and Graph-operation binding must be in the same producing attempt. A source read by itself never establishes a target/evidence relation. A claim with out-of-dispatched refs cannot have an empty Graph-operation binding list. Citation-map refs continue to equal the complete claim ref list. Aggregate candidate refs may appear in `graph_packet.candidate_evidence_ref_ids`, but must not alter the initial claim packet's assertion/relationship candidates, sufficiency/coverage/truncation, omission reasons, result limit, or assembled/dispatched Graph IDs. The final aggregate packet's `retrieval_status` may reflect the candidate union as described above.

For status derivation, keep the initial packet's frozen coverage/sufficiency semantics. A cited read receipt must itself have sufficient evidence status to ground that support; a `partial` or `truncated` receipt makes the resulting status partial, and a read receipt never upgrades incomplete/truncated initial packet coverage to complete. A full-corpus coverage claim remains invalid.

An indexed anchor that is never read cannot support a claim. A successful read omitted from the producing attempt cannot support a claim. A read in the attempt cannot support a claim if its evidence ref does not match the cited evidence. A valid read cannot rescue a target that was not independently admitted into that attempt.

## Protocol sketch

```text
initial receipt R:
  context_receipt_sha256 = H(R canonical bytes)
  graph_packet.candidate_evidence_ref_ids = ["ev-initial", "ev-source-9"]
  dispatched target IDs = ["assertion-17"]

aggregate source scope S (frozen before provider dispatch):
  graph_packet.selection_policy_version = "parent_initial_retrieval_with_bounded_source_index_v1"
  admitted_anchors = sort_unique([
    {anchor_id:"anchor-initial", evidence_ref_id:"ev-initial", ...},
    {anchor_id:"anchor-index-9", evidence_ref_id:"ev-source-9", ...}
  ])

graph_packet.retrieval_packet_sha256 = H(canonical({
  schema: "dmb_plan_retrieval_composite_v1",
  selection_policy_version: "parent_initial_retrieval_with_bounded_source_index_v1",
  initial_claim_packet: initial_packet_before_aggregate_union,
  source_index: {schema:"dmb_bounded_source_anchor_index_commitment_v1", world_id, graph_revision,
    status:"complete", max_entries:512, eligible_count, source_pins:sorted_exact_pins}
}))

execution_policy_sha256 = existing_v2_policy_digest(
  final_context_receipt_sha256,
  unchanged_v2_execution_policy_and_scope
)

producing attempt A:
  included_assertion_ids contains "assertion-17"
  included_source_read_event_ids contains event E
  E has successful receipt {read_id:"read-9", evidence_ref_id:"ev-source-9",
      anchor_id:"anchor-index-9", source_revision_id:"src-rev-3",
      content_sha256:<sha256>, returned_chars:>0, outcome:"enough"}
  included_graph_event_ids also contains validated event G
  G binds assertion-17 to exact evidence ref ev-source-9

completion claim:
  target = assertion-17
  evidence_ref_ids = ["ev-source-9"]  # aggregate candidate; not initially dispatched
  citation source_read_ids = ["read-9"]
  source_opened = true                 # derived by APP-STATE
  claim_graph_event_ids[claim] = [G]   # event binds target and exact indexed evidence
```

The example is valid only if SERVER resolved and admitted `assertion-17` independently, the session/read path admitted `anchor-index-9`, and all receipt/pin bindings validate. Neither the index row nor the aggregate digest alone proves that content was read or binds the target to it.

## Compatibility and versioning

- Keep V1 serialization, hashes, replay, and completion validation unchanged.
- Keep existing V2 behavior unchanged for every other packet `selection_policy_version`. In particular, the current initial-candidate subset rule remains in force for historical V1/V2 rows and executions.
- Select the alternate completion rule only for the exact new policy literal above. Unknown policy values retain current strict validation; they do not fall through to aggregate behavior.
- Minimal version change proposed: no completion discriminator/schema version change; use the exact new `PlanWorldGraphPacketV1.selection_policy_version` literal to select the aggregate-aware V2 validator branch.
- Proposed storage shape remains the existing V2 policy, source-read events, and V2 completion JSON. No completion schema V3, source-index schema field framework, table, column, or migration is planned.
- No new durable aggregate receipt is needed if the aggregate candidate union and composite retrieval digest are retained in the existing V1 packet fields, while the exact admitted read scope remains in the frozen V2 policy and is covered by `execution_policy_sha256`. If a review or implementation proves the current persisted V2 envelope cannot retain or validate those bindings, stop and return for a design amendment rather than adding an unreviewed schema or migration.
- Historical V2 replays keep their old policy digest and validation path. Never reinterpret their original packet as aggregate-index coverage.

## Fail-closed cases

- Index-only evidence ref with no successful content-bearing read receipt.
- Read receipt not included in the producing provider attempt, read authorization missing, wrong attempt/read ID, or receipt outcome has no valid nonempty content digest.
- Receipt evidence ref, anchor, artifact, source revision, World, campaign, Graph revision, retrieval session, or policy digest differs from the frozen pins.
- Claim target only appears in metadata/scope, or appears only in a non-producing attempt or non-included operation event.
- New out-of-packet evidence is mixed with claim refs that have no successful receipt proof.
- SERVER cannot confirm active-session admission/readability or the exact current source revision at read time.
- Duplicate anchor ID with conflicting pins; malformed, incomplete, ambiguous, stale, or over-limit metadata snapshot; silent truncation; more than 512 scope anchors; per-call/aggregate call, anchor, requested-character, provider-input, output, or context-token limits exceeded.
- Attempt to change the canonical initial claim packet, initial assertion/relationship candidates, sufficiency/coverage, dispatched IDs, or included operation IDs. Only aggregate `candidate_evidence_ref_ids` and the composite `retrieval_packet_sha256` take the explicit aggregate form; final aggregate `retrieval_status` may reflect the union as SERVER #1012 defines.
- Any claim or UX language that treats selected-index scope as full-corpus coverage.

Use existing V2 caps: at most 512 frozen scope tuples; 8 source-read calls; 8 total read anchors; 96,000 requested characters total; 12,000 characters per call; and current provider/context limits. Preserve charging the requested maximum before a read and existing partial/truncated semantics. The 512 tuple cap applies to the selected bounded scope, not to a claim about index completeness.

## Ownership and active write set

### APP-STATE (active implementation lease)

Authorized paths for this implementation:

- `src/application_state/agent_conversation/types.py` — select the new completion branch only under the exact packet selection-policy literal; retain the V2 scope subset validator; validate exact producing-attempt read receipt plus target-binding Graph event for out-of-dispatched evidence; derive status/source-opened from receipts. Do not change aggregate packet construction owned by SERVER #1012.
- `tests/application_state/test_agent_conversation_service.py` — positive and negative completion witnesses and legacy policy compatibility.
- `tests/application_state/test_agent_conversation_postgres.py` — only if fresh-service persistence round-trip coverage is needed to prove the unchanged V2 JSON envelope retains the necessary binding.

No migration is expected. `service.py`, repositories, source providers, Plan Action, SERVER route/service code, UI, and database schema are outside this APP-STATE candidate lease unless review proves a required path; obtain a lease amendment before touching anything else. SERVER aggregate/bootstrap behavior is the merged predecessor #1012. Any defect in its owning paths requires a separate SERVER authorization, not this APP-STATE lease.

## Required implementation witnesses

- Golden V1 bytes/digests and stored V1 replay remain unchanged.
- Old V2 policy receipts/completions round-trip and validate identically; existing policy digest is unchanged.
- New composite retrieval digest changes when the initial claim packet, any persisted source-index commitment field/pin, or exact selection policy changes; normal V2 execution-policy digest still changes with scope/budget/receipt changes.
- Positive claim with an independently admitted producing-attempt target, a successful read included in that same attempt, and an included validated Graph event binding the exact target/ref is accepted; the indexed ref is in aggregate candidates but absent from initial dispatched IDs.
- A prior/non-included read, a receipt without a target/ref-binding Graph event, a wrong-target event, or an event that omits the exact ref is rejected.
- Index-only, failed/empty read, wrong revision/evidence/anchor, missing attempt inclusion, and stale session/readability witnesses are rejected.
- Historical replay never gains aggregate evidence interpretation; unknown policy version fails closed.
- Scope selection at exactly 512 is valid; 513, conflicting duplicate pins, nondeterministic/ambiguous selection, truncation, and each existing read/provider budget overflow fail closed.
- No test claims full-corpus completeness or changes initial packet coverage/sufficiency semantics.

## Activation and handback

PRIME accepted the exact contract and activated this bounded APP-STATE implementation after Buddy #1011 merged at `3d59386fd4868e5b365fd8b6210cfa8ea909e78b`. The implementation must preserve the packet/scope/source-read JSON shape, legacy completion behavior, and the existing V2 policy digest. No migration is expected. The implementation and verification record below is backward-looking and makes no claim of independent review or merge completion.

Implementation handback: the V2 validator now admits out-of-dispatch refs only for the exact source-index policy, with a sufficient producing-attempt read bound to frozen scope pins and an included Graph event binding the same target and ref. Missing/non-producing reads, wrong target/ref/pins, unknown policy, receipt-only V1 claims, and unsupported bindings fail closed. Partial/truncated reads and incomplete initial packet coverage remain partial. No envelope or persistence schema changed.

Verification: the indexed-completion witness plus the adjacent V2 source-read scope and source-opened compatibility tests passed (`3 passed`); Ruff check and Python syntax compilation passed. The root pytest conftest could not provision its disposable PostgreSQL instance on this host, so the APP-STATE PostgreSQL suite was not run. The focused tests were executed without the root PostgreSQL autouse fixture; no persistence change required a PostgreSQL witness for this slice.
