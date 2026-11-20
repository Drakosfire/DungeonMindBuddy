# SOURCE — opt-in Buddy recap-context reader V2

Status: ACTIVE under PRIME, 2026-10-12. Replaces the held three-path legacy
reader dispatch. One compatible V2 reader using accepted Core selector metadata.

Core #116 merged at aa344e743c138ca099c023d2c384fee90328d37e;
reviewed head81ad5db0260fb04ab72fa4c03b2bb2c427e64c4f, review6133468715.
Its exact contract is Docs/Contracts/CONTRACT-recap-source-context-v2.md.
Pinned amended design /tmp/recap-selector-v2-contract-decision.json SHA
f2a56ca31252ff9707f8b93c7f8d6a671c29d57954f6bc1e66189cb99eb52504.
Re-fetch Buddy main/open PRs/leases; last main cbbf89e7f5af02e09e0182635737e316e05e89b0.

Exact write set:

- src/graph_memory/retrieval/models.py
- apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
- apps/live_control_server/services/world_graph_retrieval.py
- apps/live_control_server/routes/world_graph_retrieval.py
- tests/test_recap_source_read_continuity.py
- tests/test_world_graph_retrieval_contract.py
- pyproject.toml
- uv.lock
- Docs/Plans/HANDOFF-SOURCE-recap-context-reader-v2.md

Pin exactly accepted Core merge, no dependency/version/lock churn. Add explicit
V2 index/read requests/results/routes; old routes stay V1. New discovery opts
into V2; saved V1 IDs delegate to unchanged V1 decoding/cursor policy. V2 IDs
and cursors cannot cross policies, sources, scopes, revisions or sections.

Canonical V2 body bytes/ranges equal valid V1. Legacy: exact Session H2;
unique standalone Recap marker after it, before next H1/numbered Session H2/EOF;
non-session Major/Next Beats prelude headings do not end marker discovery.
Body starts after marker and ends next H1/H2/EOF. Preserve fenced/quoted fake,
wrong-number, mixed/duplicate marker/heading and invalid-bound exclusions.
Use the contract's synthetic prelude vector and real C1S16 read-only witness.

Reuse GM/source/provenance/standing/hash/containment/UTF8/paging guards. No source
rewrite/relabel/catalog fallback, new reader scheme, graph store or data/schema
mutation. Related context is not claim support or literal quotation evidence.

Focused owning parser/service/ASGI evidence and private read-only clone witness:
canonical unchanged; legacy exact contiguous page reassembly; saved V1 reads
and cursors preserved; ambiguity, forged/stale cursor, bytes/hash/scope/source
drift fail. Private source remains outside Git. No provider/runtime/retained write.

Serial topology Core is accepted -> this Buddy reader -> separate bounded
Agent/APP/UI source-target adoption. Do not claim production story complete or
operator dogfood-ready from a V2 API alone. Those consumers remain on V1 here.
Implement -> focused verify -> cumulative diff -> commit/push/PR for independent
PRIME review. Rebrief an essential extra path or public contract before edits.


## Implementation anchor and limits

- Buddy base: `cbbf89e7f5af02e09e0182635737e316e05e89b0`.
- Core pin: exact accepted merge `aa344e743c138ca099c023d2c384fee90328d37e`.
  `pyproject.toml` and `uv.lock` are exactly the previous Core SHA replaced with
  this SHA; Core package dependency metadata is unchanged across the two commits.
- Branch: `codex/source-recap-context-reader-v2`, isolated checkout
  `/tmp/buddy-rake-evidence-append`. Prior legacy-reader HOLD branch is preserved.
- Serial Core -> this reader -> separately bounded Agent/APP/UI adoption.
  Only this handoff is the mutable authority sync set. Implementation awaits
  independent PRIME review; no merge or runtime adoption is claimed.

The V2 route names are `/recap-context/v2/index` and `/recap-context/v2/read`.
Index explicitly negotiates Core V2. Read dispatches from the known ID version:
V1 IDs delegate to the original reader and return V1 descriptors/cursors/schema;
V2 IDs use the new policy and return V2 only. Existing routes remain V1. The V2
cursor binds the complete validated descriptor, section digest, selected form,
heading/marker/body bounds and character offset. Every page re-resolves authority
and verifies full original bytes before serving an exact UTF-8 text slice.

Marker discovery and body selection have independent boundaries. Non-session
H2 prelude does not stop marker discovery; H1 or numbered Session H2 does. The
body starts after the unique literal marker and stops at H1/H2, retaining H3+
and fenced text as original body bytes. Canonical section boundaries reuse the
unchanged V1 H1 scanner, including its empty canonical slice behavior. Legacy
empty/invalid sections remain unavailable. Unsupported or ambiguous structures
never use a normalized file, adjacent session, whole-file or filename fallback.

## 4. Write lease

| Path |
| --- |
| src/graph_memory/retrieval/models.py |
| apps/live_control_server/integrations/dungeonmind/world_graph_reads.py |
| apps/live_control_server/services/world_graph_retrieval.py |
| apps/live_control_server/routes/world_graph_retrieval.py |
| tests/test_recap_source_read_continuity.py |
| tests/test_world_graph_retrieval_contract.py |
| pyproject.toml |
| uv.lock |
| Docs/Plans/HANDOFF-SOURCE-recap-context-reader-v2.md |

## 5. Excluded paths and actions

| Path |
| --- |
| corpus/** |
| out/** |
| apps/live-control-ui/** |
| src/application_state/** |

No retained, clone, graph or source write, source relabel, schema change, provider
call or runtime action. Existing Agent/APP/UI V1 contracts are unchanged.

## 7. Author owning-boundary evidence

```bash
PYTHONPATH="/tmp/core-recap-context-v2/src:$PWD/src:$PWD" /tmp/buddy-runtime-candidate-core115-20261012/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_recap_source_read_continuity.py tests/test_world_graph_retrieval_contract.py -k recap_context
```

36 tests pass, 26 unrelated tests deselected. They cover V1 canonical bytes,
ranges and cursors through old and V2-capable reads; V2 canonical parity, exact
legacy prelude and contiguous paging; frozen/quoted/indented fake structures,
wrong session, duplicate/mixed forms, missing marker, body boundaries, UTF-8,
source/hash/scope/revision drift and cross-version/tampered cursors. Actual
ASGI routes exercise authorization before service, typed negotiation, service
wiring and fail-closed error responses. The inherited Pydantic schema-shadow
warning remains. Changed Python paths pass Ruff; cumulative diff check passes.

Private, read-only owning-reader witness:
`/tmp/c1-session16-recap-context-v2-reader-witness.json`. Actual Core V2 index and
resolution on the existing C1S16 disposable clone select `legacy_h2`, return lines
19–43, and reassemble six bounded pages exactly. Original source hash, source
pair and clone head remain unchanged. No passage bodies are committed or included
in that metadata report. Tests import the exact Core merge from an isolated source
checkout using existing Python libraries; no runtime environment was replaced.

`uv lock --check` cannot complete in this environment because the pre-existing
local dependency `hermes-agent @ out/hermes-agent` is absent. Baseline lock metadata
fails at the same missing package. The two changed dependency files are verified
as exact Core-SHA substitutions, and Core's `pyproject.toml` dependency metadata is
identical between the old and accepted pins. No incidental lock resolution or
package metadata/version/wheel churn was introduced.

## 9. Review acceptance and remaining hold

- Explicit V2 discovery and ID-version-selected resolution; V1 routes, schemas,
  descriptor/ID meaning and cursors remain intact.
- Exact authorized source bytes selected under canonical or supported legacy
  grammar, with distinct marker-search and returned-body boundaries.
- Existing GM, scope, source-standing, digest, containment, UTF-8, paging and
  continuation guards remain at every read; related context remains separate
  from evidence/claim support.
- Synthetic parser/service/ASGI proof and private actual clone witness pass.
- Agent/APP/UI V2 adoption and the operator journey remain separate and unaccepted.
  This API reader alone is not production-story or semantic acceptance.
