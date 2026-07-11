# PR006B — Semantic Assertion Identity Repair

## Contract before

The assertion hash included the complete assertion `value`. Heterogeneous
provenance therefore produced split assertion IDs and split support records for
the same pre-resolved semantic fact.

## Contract after

Assertion identity hashes semantic value, not explicit top-level provenance
carriers. Provenance remains on assertions and flows into graph-object
aggregation, source artifacts, evidence records, and durable support.

### Excluded top-level provenance keys

- `source_domain`
- `source_domains`
- `source_artifact_id`
- `source_artifacts`
- `source_revision_id`
- `evidence`
- `evidence_ref_ids`

The exclusion is shallow. Nested keys with the same names remain semantic data.

### Retained identity-bearing fields

- assertion kind, subject node ID, target node ID, predicate, and label
- semantic value fields such as `kind`, `role`, `aliases`, `summary`,
  `canon_state`, `approval_state`, `identity_canon_state`, `session_ids`, and
  `edge_id`
- campaign scope and temporal scope
- epistemic kind and visibility

Dedicated provenance and contribution fields remain outside assertion identity:
`evidence_ref_ids`, `source_artifact_id`, `source_revision_id`,
`contribution_id`, `identity_resolution_outcome`, and `acceptance_state`.

## Graph-native proof

| Field | Result |
|---|---|
| Contribution A ID | `contribution:83d02402fa1d8608` |
| Contribution B ID | `contribution:1898db0a4398e473` |
| Old PR006A assertion IDs | `assertion:ce7fa5127bbc6cdc`, `assertion:b18e96423162fb33` |
| New shared assertion ID | `assertion:4992fdd6e75dfc10` |
| Support-record count | 1 |
| Active contribution IDs | A and B |
| Source artifact IDs | `graph-native:pr006a:support-a`, `graph-native:pr006a:support-b` |
| Evidence ref IDs | `evidence:pr006b:worldbuilding:mireward`, `evidence:pr006b:recap:mireward` |
| Node source domains | `worldbuilding`, `recap` |
| Head revision | `rev:9f4cd87b02b76354ecab3a1a362ce7c2` |
| Parent revision | `rev:a98b1820d56e0c1b2a6c63730abfca59` |
| Rebuild result | Equivalent to current head |
| Failed-write result | Invalid contribution published no revision; valid head remained unchanged |

The lifecycle regression additionally proves that retracting one contributor
leaves the shared assertion supported by the other, and that superseding that
remaining contributor preserves one semantic support record while moving the
old contribution into superseded history.

## Legacy-ledger migration

Historical contribution files are not rewritten. During replay,
`rebuild_from_contributions` canonicalizes assertion IDs in memory and records
machine-readable `assertion_identity_rekeys` entries in the rebuild report.

With `publish=True`, the existing validated immutable-revision path writes the
replacement head. The legacy-ledger regression preserves both original record
bytes, produces one shared support record with both artifacts, evidence refs,
and node domains, then proves a second non-publishing rebuild is equivalent to
the new head.

No production World Supergraph publication existed before this repair. This PR
does not require corpus reprocessing.

## Non-claims

PR006B does not prove:

- source extraction quality
- identity resolution
- initial contribution-bundle completeness
- initial Eldyrwild publication
- projection usefulness
- Plan or Play integration
