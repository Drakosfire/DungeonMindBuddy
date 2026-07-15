# Tripod Null-Calf dogfood forensic

**Question:** “What do we know about Tripod Null-Calf at the North Gate?”  
**Observed symptom:** panel shows Tripod/North Gate graph context; Hermes returns canned insufficient-evidence abstention.

## Confidence statement

The repository and PR were fully inspected through GitHub. The operator’s browser request, activated `out/` World Graph, model run, and persisted completed turn were not available in this environment. Therefore the exact runtime branch among no-tool, missing-completion, empty-anchor, or malformed-result cannot be conclusively selected.

The report separates confirmed facts from bounded inference.

## Confirmed Tripod graph state

The approved graph-native contribution contains:

- node: `threat:tripod-null-calf`;
- edge: Tripod `appeared_in` the Session 23 Mireward gate battle;
- accepted canonical GM-authored attributes:
  - battlefield role: siege scout and positional controller; pins carts, gates, rope lines, or cure-line access;
  - challenge expectation: serious pressure for six level-5 PCs with NPC allies, not a full boss;
  - first appearance: Mireward north-gate pressure sequence;
- source kind: `graph_review_authored_assertion`;
- source URI: `graph-data://.../006-tripod-null-calf-threat-prep.json`;
- locators: JSON pointers into accepted assertions.

This is not a vague node summary. It is explicit, accepted, canonical, GM-authored graph content.

## Confirmed source-read condition

A graph-data JSON-pointer anchor is readable only when the active revision carries a valid `contribution_source_payload_sha256` for its contribution. The initial Eldyrwild activation PR merged before lifecycle-neutral contribution digest authority. The digest-authority PR states that legacy heads require rebuild migration.

Therefore a graph activated before the digest-authority migration likely returns Tripod anchors as `readable: false` until rebuilt or reinitialized. This remains an inference about the operator’s local `out/` state; the active revision was not available for inspection.

## Why unreadable anchors do not explain the canned abstention

Kernel retrieval still emits unreadable anchors. Their IDs remain present in `sourceAnchors`, and retrieval outcome becomes `partial`.

The product classifier accepts a completion when it has any anchor ID. It does not inspect `readable`, locator kind, or source-read success.

Therefore this sequence:

```text
Tripod search → graph content + unreadable anchor IDs → completion(outcome=partial)
```

would produce a **partial answer**, not `hermes_insufficient_evidence`.

The digest migration is required for honest source verification, but it is not sufficient as the causal explanation for the observed canned abstention.

## Failure-hypothesis matrix

| Hypothesis | Compatible with canned abstention? | Current evidence |
|---|---:|---|
| A. Hermes called no graph tool | Yes | High-probability; no real-agent acceptance proof exists |
| B. Tool started but no completion callback | Yes | Possible; requires captured trace |
| C. Completion failed scope/event parsing | Usually produces contract error, not abstention | Lower probability because collector injects scope |
| D. Retrieval returned graph content but no anchors | Yes | Possible if selected objects lack admitted supports |
| E. Retrieval returned unreadable anchors | No, not by itself | Confirmed classifier still accepts IDs |
| F. Hermes found claims but did not open source | No, not by itself | Classifier does not require source read |
| G. Classifier demanded wrong evidence class | Yes architecturally | Confirmed; accepted graph claims cannot independently ground |
| H. Panel candidate match created misleading success | Yes product-wise | Confirmed |

## First confirmed divergence

```text
Preflight envelope → Hermes turn request
```

At this boundary the product has already resolved Tripod and assembled nodes, edges, and attributes, but the Hermes request discards them and retains only scope/revision. The panel displays one retrieval result while Hermes must independently rediscover another.

This is the first boundary where expected user meaning (“the product found Tripod”) diverges from actual agent state (“Hermes was not given Tripod”).

It is not yet proven to be the immediate runtime cause of the abstention.

## Runtime packet still required from operator environment

Capture one instrumented run with:

```text
1. exact browser request body after serializer
2. resolved preflight envelope
3. rendered panel state
4. HermesGraphAgentTurnRequest
5. model-visible tool definitions
6. tool start callback payloads
7. raw tool completion result strings
8. summarized HermesGraphToolEvents
9. classifier input and branch decision
10. citation projection
11. persisted completed turn
12. active world revision and contribution digest map entry for contribution:022187fdefdf4557
```

Required redactions:

```text
API keys
provider credentials
absolute filesystem paths
unbounded source bodies
raw hidden model reasoning
```

## Instrumentation change required before another dogfood conclusion

Add a non-secret forensic envelope for each Hermes turn:

```json
{
  "retrieval_session_id": "...",
  "preflight_candidate_ids": ["..."],
  "agent_seed_ids": ["..."],
  "tool_events": [
    {
      "call_id": "...",
      "tool": "...",
      "state": "started|completed|failed|blocked",
      "result_schema": "...",
      "outcome": "...",
      "claim_ids": ["..."],
      "anchor_states": [{"anchor_id":"...","readable":false,"opened":false}],
      "diagnostics": ["..."]
    }
  ],
  "acceptance": {
    "state": "...",
    "reason_codes": ["..."],
    "accepted_claim_ids": ["..."],
    "rejected_claim_ids": ["..."]
  }
}
```

## Tripod repair decision

**Data repair required:** yes.

Rebuild or republish the active Eldyrwild head so every active graph-native contribution has revision-bound source-payload digest authority. Verify that Tripod JSON-pointer anchors become readable and source reads return the bounded accepted assertion payload.

**Architectural repair required:** also yes.

Do not treat the data rebuild as resolution of the product failure. The replacement architecture must allow the answer:

```text
Graph-grounded: Tripod is a canonical siege scout and positional controller at the North Gate.
Source verification: unavailable until the graph-native contribution anchor is readable.
```

rather than either pretending the source was verified or withholding known canonical graph facts.

## Exact experiments completed

- fetched current PR356 metadata and actual changed paths;
- compared base/head commit topology;
- inspected PR356 patches and current source files;
- inspected canonical architecture/roadmap/tracker/Hermes story docs;
- traced preflight → Hermes request field mapping;
- traced tool result → event summary → classifier mapping;
- inspected pinned Hermes 0.18.2 raw tool-completion callback;
- traced Tripod contribution → graph-data anchor → digest/readability classifier → source reader;
- inspected current fake-host HTTP/product tests;
- checked GitHub combined status for the PR head: no statuses attached.

## Experiments not completed

- local test execution;
- browser reproduction;
- real model/provider run;
- active `out/` graph inspection;
- source-read execution against the operator’s revision;
- persisted local thread inspection.

## Forensic conclusion

The first confirmed product divergence is the panel-to-Hermes handoff. The first runtime cause of the canned abstention remains unproven. The existing evidence rules eliminate “unreadable Tripod source alone” as a sufficient explanation and narrow the next runtime capture to no-tool/no-completion/no-anchor/result-shape branches.
