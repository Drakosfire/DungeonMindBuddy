# PR006A — Graph-Native Contribution Union Diagnostic

## Objective

Determine whether heterogeneous graph-native provenance can independently
support one durable assertion through the public Kernel.

## Observed result

| Field | Value |
|---|---|
| Baseline revision / parent | `rev:5ba64745801339e42ce37d4b0f2d1983` / none |
| Contribution A | `contribution:83d02402fa1d8608` |
| Revision A / parent | `rev:47193b3c4248301ad8c469319032188a` / baseline |
| Contribution B | `contribution:1898db0a4398e473` |
| Final head / parent | `rev:166bc006142a5af1620622981bf6652c` / Revision A |
| Mireward assertion IDs | `assertion:ce7fa5127bbc6cdc`, `assertion:b18e96423162fb33` |
| Final graph | 5 nodes, 3 edges (baseline: 3 nodes, 2 edges) |
| World integrity | `load_ok=true`, `validation_ok=true` |
| Rebuild | equivalent to current head |

Contribution A declares `source_domains=["worldbuilding"]`; Contribution B
declares `source_domains=["recap"]`. The assertions use the same pre-resolved
node key, `location:mireward`, but **do not share an assertion ID or support
record** because `source_domains` participates in the assertion hash.

Observed support split:

```text
graph_object_id: location:mireward
assertion:ce7fa5127bbc6cdc → contribution:83d02402fa1d8608
assertion:b18e96423162fb33 → contribution:1898db0a4398e473
```

The invalid endpoint contribution
`contribution:4caa5a563666e8f6` was recorded as failed. It published no
revision; the valid final head remained readable and unchanged.

## Graph-layer limitations

The baseline is the existing prepopulated synthetic read-model fixture. Its
three nodes and two edges are not a graph bootstrap or materialization proof.

This spike begins with graph-native `GraphContribution` objects. It proves
same-key node mutation, immutable revisions, failed-write safety, and rebuild
equivalence. It does **not** prove identity resolution: both assertions arrive
with the same pre-resolved node key.

The support split is a graph-layer limitation, not a production fix in PR006A.
This spike does not prove document ingestion, extraction, source selection,
coverage, projection usefulness, or runtime surface migration.
