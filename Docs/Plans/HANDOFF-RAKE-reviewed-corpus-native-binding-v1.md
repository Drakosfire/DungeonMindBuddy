# Reviewed corpus-to-native binding v1

## Authority and scope

Source/test preparation only, based on Buddy `406cb3e2`. Real identity-decision creation, graph publication, replay continuation, source reclassification and frozen-input changes remain held. The separate Core existence-evidence rebind lane is preserved.

The owning failure is a resolved Library NPC reference whose normalized corpus key does not match its already admitted native object ID. A Library reference does not itself prove a World identity. Labels remain validation terms, never a fallback identity lookup.

## Carrier contract

Use the existing Core `HUMAN_OVERRIDE` record without changing Core models. Its reason must be exactly the prefix `dmb-reviewed-corpus-native-binding-v1:` followed by a strict `ReviewedCorpusNativeBindingV1` JSON payload. The payload binds World, parent revision, campaign, complete canonical candidate digest, candidate node ID, normalized NPC corpus-reference key, target native object ID, target and ordered existence-evidence fingerprints, authoritative source-artifact/revision fingerprints, decision ID and reviewer ID. The carrier's World, actor, subject, target, decision ID and active status must agree. The complete carrier record is sealed in the existing identity-ledger proposal effect and covered by the existing proposal digest. No arbitrary caller mapping becomes durable authority.

Only NPC references can use this version. Binding reasons are excluded from the generic candidate override classifier, including on later heads; only the verified anchor gate can consume them. Legacy decisions and unbound PC/NPC behavior retain their existing paths and bytes. No global registry or new alias is created.

## Prepare and confirm proof

The production context loader verifies the actual carrier against the live Core ledger, target existence/standing/campaign against the pinned graph, the complete ordered existence-evidence closure, and actual source-catalog records. Candidate admission carries the complete pre-qualification canonical digest into the gate. Direct prepare computes that digest only if none was provided.

The anchor gate requires an exact binding basis, checks NPC kind, active canonical identity, no redirect, candidate-label membership and no conflict with exact-ID matches. The ordinary classifier must resolve to the same verified target. It emits source support for the existing object, never a replacement object definition.

Confirm rebuilds from the sealed ledger and immutable parent. Before reconstruction and again immediately before publication it rereads actual decisions and sources, rejecting missing/changed/retracted decisions, target/evidence drift, source fingerprint/domain drift and source-closure mismatch. The sealed candidate-admission digest is required.

## Transaction limitation and ARCH question

The Buddy rechecks are **not transactionally fenced** with Core publication. A mutable decision or source row can change after the final check and before the publication transaction commits. The existing parent CAS fences graph revisions only. This PR must not be represented as a solution to that race or authorization for data execution.

ARCH must identify the precise existing owner-boundary mechanism that can fence the selected carrier and source fingerprints inside the Core publication transaction, or define the smallest explicit contract extension if none exists. Required semantics: exact selected decision/source preimages revalidated under the same transaction as parent CAS and child/receipt publication; drift yields no child or publication receipt; exact receipt retry remains idempotent. No Core change or new storage framework is inferred by this Buddy lease.

## Evidence

Public tests use synthetic actors, sources and decision records. Private offline witness: `/tmp/rake-c2s22-party-anchor-gate/frozen-candidate-offline-witness.json`, generated from the actual frozen candidate and retained exports using a hypothetical in-memory carrier. It proves the previously failing anchor resolves to the existing native NPC with unchanged parent and support-only output. It creates no actual decision, opens no database connection and does not prove full prepare/publication, edge qualification or suffix completion.

No PostgreSQL test fixture is activated by this source lease. Existing integration tests requiring disposable PostgreSQL on port 54329 are excluded from the qualified pure test run; an initial unfiltered run failed fixture setup and is not claimed as passing.

## Ownership release

The six Buddy source paths and two test paths remain exclusively held for this repair until source acceptance and explicit release. In particular, `models/extract_promote.py` and `src/graph_memory/extract_promote_ops.py` are shared with the later batch-correction lane. Do not infer an additional route/service or Core write lease.
