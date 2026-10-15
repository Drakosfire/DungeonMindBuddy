# INGEST: constrain advisory selection to known proposal IDs

Status ACTIVE after ARCHITECTURE design PASS on c6725b71f0be987f809f9a9b57a057b223c9d61a. PRIME solo implementation; one serial
PR after merged1180/1182, base66b24a54684d56bf04f2b34efd4121cf94a64d9c.
Branch codex/advisory-id-schema; isolated /tmp/buddy-advisory-review-design.

## Capability and evidence

Gazetteer1.5 inherits1.4 and binds the canonical post-role-guard edge-ID catalog
to each reviewer request's JSON schema and explicit input allowlist. Keep1.4
frozen. Known membership is deterministic; source fidelity remains advisory.

Actual1.4 registered run ba550b22-cdae-4d81-8e32-1e510c7e01a4 preserved five
byte-matched historical writer responses plus one completed GE reviewer response.
It correctly failed on an unknown returned ID (e034, removed before review by
role support), with no candidate/native publication. Actual reviewer usage58353
input/101output,4633ms,one provider attempt,no retries,cost unknown. Evidence under
private experiments/mirathorn-gazetteer-20261014/gazetteer14-advisory-registered-run-2.
This is an invalid selection, not semantic success or permission to salvage IDs.

## Request-local contract

The existing bounded client's schema seam derives exclusively from pass_spec;
no narrower per-call schema argument exists. Add a frozen review-only subclass
of ExtractionPassSpec in worldbuilding_edge_review.py with an optional immutable
allowed_edge_ids tuple. The code-owned1.5 profile uses this unbound spec; pipeline
binds it from canonical post-role-guard proposals immediately before review.
Unbound/malformed constraint fails before inference. No field added to the generic
ExtractionProfile or public request. Validate IDs as unique nonblank strings.

For this specialized edge_review spec only, schema items.enum is exactly the bound
IDs and uniqueItems=True. Keep valid empty selection; skip empty proposal sets
without binding/calling a reviewer. Input also names this same exact allowlist and
says missing/gapped IDs are intentional. Do not derive IDs from source text, raw
pre-guard generation, gold, model expectations or prior review output.

Keep independent application subset validation. If provider/GE enforcement fails,
unknown/duplicate/rewritten IDs still fail with all available evidence preserved.
No dropping/replacing/renumbering unknown IDs, rewriting candidate objects,
acceptance promotion, extra call/retry/fallback, GE change or default route change.
Existing GE conformance repair and actual-attempt accounting stay truthful.

Writer prompts/specs/source unchanged. Store the bound output-schema hash in the
existing seam request hash/evidence, explicit allowlist in captured review input,
and preserve canonical post-review envelope/private pre-review lineage. Model
retention/omission is not semantic/native/identity/publication approval.

## Exclusive prospective write set

- this handoff
- src/graph_memory/extraction/worldbuilding_edge_review.py
- src/graph_memory/extraction/category_candidate_graph_schema.py
- src/graph_memory/extraction/category_candidate_graph_extractor.py
- src/graph_memory/extraction/worldbuilding_gazetteer_profile.py
- src/graph_memory/extraction/worldbuilding_profile_catalog.py
- tests/test_worldbuilding_edge_review.py
- tests/test_worldbuilding_gazetteer_profile.py

Prior implementation leases1180/1182 released. SERVER owns matched serving rollout;
DOGFOOD UI work is settled. Historical MIND extractor PRs remain frozen; no active
shared extractor edits. No serving/ports/retained native writes/provider/credentials
lease in implementation. Disposable APP fixtures may exercise registered evidence.

## Owning evidence and handback

Actual pipeline test has role-guard-removed ID absent from exact schema AND prompt
allowlist, retained candidate IDs unchanged, writer requests unchanged,1.4/default
behavior unchanged, empty selection/skip-empty, malformed/unbound catalog pre-call
refusal and malicious/unknown output fail-closed. Exercise actual BoundedRecapPassClient
with a synthetic worker seam to inspect schema and keep usage/attempt accounting;
no live provider. Actual registered failure retains prior outputs/response/hash.
Existing preservation/canonical/source retention gates remain intact.

Complete implementation/tests/diff/commit/push/PR and independent exact-head
review before merge. Only afterward may a separately recorded changed-request
research run use standing ingestion approval. No original failed-turn replay or
retained World publication is authorized here. Full Mirathorn lifecycle incomplete.
