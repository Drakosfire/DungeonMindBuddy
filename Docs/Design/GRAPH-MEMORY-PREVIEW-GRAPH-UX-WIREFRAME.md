# Graph Memory Preview Graph UX Wireframe v0

Text-only wireframes for a future GM-facing preview. No images, screenshots, Figma files, runtime UI, React components, routes, or API endpoints are introduced.

## Preview Summary

```text
┌──────────────────────────────────────────────────────────────┐
│ Session 23 Memory Preview                                    │
│ Status: Safe but incomplete        GM Preview: Not ready      │
│ Safety: Pass  Evidence: Pass  High-Risk Audit: Pass          │
├──────────────────────────────────────────────────────────────┤
│ Coverage                                                     │
│ Nodes: 33/42 good     Edges: 8/23 weak                       │
│ Beats: 6/14 partial   Writes: 6/15 partial                   │
├──────────────────────────────────────────────────────────────┤
│ Proposed writes: 6 pending     Hard failures: 0              │
│ Soft misses: 45              Missing coverage: review needed │
├──────────────────────────────────────────────────────────────┤
│ Recommended action                                           │
│ Safe to inspect. Do not approve in bulk.                     │
└──────────────────────────────────────────────────────────────┘
```

## Candidate Graph Explorer

```text
┌──────────────────────────────────────────────────────────────┐
│ Candidate Graph Explorer                                     │
│ Tabs: Nodes | Edges | Beats | Threads | NPCs | Locations     │
│       Groups | Threats | Ignored | Deferred                  │
├──────────────────────────────────────────────────────────────┤
│ Filter: high-risk only [ ]  unresolved evidence [ ]          │
│ Sort: risk first                                             │
├──────────────────────────────────────────────────────────────┤
│ Candidate                         Evidence   Risk    Review  │
│ Lysandro                          4 refs     high    disabled│
│ Lysandra recognizes Lysandro       3 refs     high    disabled│
│ Remaining horde                    2 refs     warn    defer   │
│ Ignored: unsupported second wave   1 ref      pass    ignored │
└──────────────────────────────────────────────────────────────┘
```

## Candidate Detail with Evidence

```text
┌──────────────────────────────────────────────────────────────┐
│ Candidate Detail: Lysandra recognizes Lysandro               │
│ Type: edge                         Risk: high-risk claim      │
│ Status: proposed preview item      Review: disabled in v0     │
├──────────────────────────────────────────────────────────────┤
│ Why proposed                                                  │
│ Candidate edge links recognition event to Session 23 recap.   │
├──────────────────────────────────────────────────────────────┤
│ Evidence                                                     │
│ [resolved + highlightable] src:S23#p12 lines 4-5  Open | HL  │
│ [resolved + openable]      src:S23#p13 lines 1-2  Open       │
│ [warning]                 heading-only anchor     Open       │
├──────────────────────────────────────────────────────────────┤
│ Related nodes: Lysandra, Lysandro                            │
│ Related beats: cliffhanger recognition                       │
├──────────────────────────────────────────────────────────────┤
│ Future controls                                              │
│ [Approve disabled] [Reject disabled] [Defer disabled]         │
│ Disabled reason: This design PR does not implement approval.  │
└──────────────────────────────────────────────────────────────┘
```

## Proposed Writes Queue

```text
┌──────────────────────────────────────────────────────────────┐
│ Proposed Writes Queue                                        │
│ All write actions are conceptual / disabled in this rung.     │
├──────────────────────────────────────────────────────────────┤
│ Type         Target                         Evidence  Status │
│ create node  Lysandro                       4 refs    pending│
│ create edge  Lysandra -> Lysandro           3 refs    pending│
│ create beat  cliffhanger recognition        2 refs    pending│
│ defer item   uncertain horde count          1 ref     pending│
├──────────────────────────────────────────────────────────────┤
│ Approval eligibility: disabled                               │
│ Reason: not_ready_for_gm_preview; high-risk claims present.  │
└──────────────────────────────────────────────────────────────┘
```

## Missing Coverage Panel

```text
┌──────────────────────────────────────────────────────────────┐
│ Missing Coverage and Soft Misses                             │
│ The candidate is safe to inspect but not good enough for GM   │
│ preview. Edges and beats are weak.                           │
├──────────────────────────────────────────────────────────────┤
│ Critical                                                     │
│ - Missing edge coverage: 8/23 gold                           │
│ - Missing beat coverage: 6/14 gold                           │
├──────────────────────────────────────────────────────────────┤
│ Important                                                    │
│ - Missing proposed writes                                    │
│ - Missing deferred items                                     │
├──────────────────────────────────────────────────────────────┤
│ Nice to have                                                 │
│ - Extra candidate coverage review                            │
└──────────────────────────────────────────────────────────────┘
```

## Hard Failure Panel

```text
┌──────────────────────────────────────────────────────────────┐
│ Hard Failures and Safety Blocks                              │
│ Current sample: none                                         │
├──────────────────────────────────────────────────────────────┤
│ If failures exist                                            │
│ Category: unresolved evidence ref                            │
│ Affected object: candidate edge / proposed write             │
│ Why it blocks trust: source evidence cannot be verified.     │
│ Suggested next action: inspect, reject, or defer.            │
├──────────────────────────────────────────────────────────────┤
│ Blocked actions                                              │
│ [Bulk approve disabled] [Approve disabled]                   │
└──────────────────────────────────────────────────────────────┘
```
