# PR006A — Graph-Native Contribution Union Spike

## Objective

Prove that two graph-native `GraphContribution` objects independently support
one assertion, publish immutable World Supergraph revisions, and rebuild
equivalently through the public Kernel.

## Observed result

| Field | Value |
|---|---|
| Baseline revision / parent | `rev:5ba64745801339e42ce37d4b0f2d1983` / none |
| Contribution A | `contribution:83d02402fa1d8608` |
| Revision A / parent | `rev:1b204b3b23326c040e373e403dd4c08e` / baseline |
| Contribution B | `contribution:1898db0a4398e473` |
| Final head / parent | `rev:4f6d1cebb838a4bc630e44ba590d2c52` / Revision A |
| Shared assertion | `assertion:ab2c510e858ec0eb` |
| Final graph | 5 nodes, 3 edges |
| World integrity | `load_ok=true`, `validation_ok=true` |
| Rebuild | equivalent to current head |

Revision lineage: baseline → Contribution A → Contribution B. The final head's
parent is Revision A.

Shared Mireward support record:

```text
graph_object_id: location:mireward
active_contribution_ids:
  - contribution:83d02402fa1d8608
  - contribution:1898db0a4398e473
source_artifact_ids:
  - graph-native:pr006a:support-a
  - graph-native:pr006a:support-b
support_state: supported
```

The invalid endpoint contribution
`contribution:4caa5a563666e8f6` was recorded as failed. It published no
revision; the valid final head remained readable and unchanged.

## Graph-layer limitations

This spike begins with graph-native `GraphContribution` objects.

It does not prove document ingestion, extraction, source selection, corpus
coverage, materialization quality, projection usefulness, or runtime surface
migration.
