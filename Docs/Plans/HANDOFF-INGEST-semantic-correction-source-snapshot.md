# INGEST: bind semantic correction children to immutable recap sources

Status: **BLOCKED — design only; no implementation lease.**
Current remote main confirmed through GitHub: `cbd3a901c62199c56c66c66e7f1a5a540bdbdfb6`.
The design checkout still descends from `803c1ece8869f9a3253dff0f0c646bbcf645fc75`;
the common `.git` path is read-only, so this audit is re-anchored by remote
evidence but the local branch has not been rebased. Before any PR or activation,
rebase the design commit onto current main while preserving its content.
Parent capability: PR #1399, merged at 803c. This is its serial successor;
there is no unmerged behavioral parent. The current checkout also contains the
settlement-only commit `e01ff297c61cefa197c69cd2cb3c870c2781ba7e`; the settlement
is now recorded on main by `cbd3a901...` and is not a behavioral dependency.
PRIME retains activation and merge authority.

The local `git fetch origin main` could not update shared Git metadata because
the worktree's common `.git` path is read-only. GitHub's current commit listing
confirmed `cbd3a901...`; an open-PR search found no source-snapshot correction
implementation. PR #1235 is held on separate Graph Review UI paths. PRIME also
confirmed ROOT owns an existing-World UI-only publication slice, disjoint from
this server/design work. Do not create another #1399 settlement PR.

## Defect and boundary

PR #1399 preserves frozen World scope in semantic correction children. It does
not resolve the separate production source-component URI failure. A parent may
refer to an immutable source snapshot co-located with its candidate graph. The
semantic correction currently relocates the child candidate under
`derived_candidates/<child-id>/candidate_graph.json` while retaining the
parent's source and span-index component refs. The registry correctly accepts
only a canonical `SourceArtifact` URI or a `source.md` snapshot co-located with
the candidate graph. After candidate relocation, the retained run-local source
URI is neither one. In the current ordering the child candidate file is written,
a DRAFT run row is created, and the transition to REVIEWABLE then reaches the
registry guard and fails. This leaves an unreviewable row and candidate artifact.

The registry guard is enforcing provenance and containment. Do not relax it to
make this child pass. The successor must fully preflight source, span, World,
candidate destination and semantic identity before writing a child file or
APP-STATE row.

## Required invariant

For a correction of a frozen recap parent, mechanically prove that the
registered canonical `SourceArtifact` identity, URI, actual bytes, full content
digest, and native World binding agree with the unchanged parent snapshot.
Validate the run's source domain, campaign, session, frozen World context, and
source-artifact ID against the registered artifact and parent. A current World
selection, campaign name, default, or mutable head is not authority.

The child must remain held and derive only its candidate graph from the exact
parent candidate plus the declared correction manifest. Preserve the parent
`source_artifact_id`, exact source span-index reference and bytes, span-index
binding to the same source ID and digest, parent candidate digest, semantic
basis, and deterministic replay/idempotency rules. The parent, registered
artifact, and span index are immutable throughout.

Before any child file or row write, reject missing or foreign artifacts, source
or parent World disagreement, absent files, changed bytes or digests, invalid
span indexes, symlinked paths, and paths escaping the managed artifact root. A
rejected preflight leaves no child file or child row.

Keep the current operation manifest bytes, schema, canonicalization and replay
unchanged for each accepted semantic-correction request version V1-V10. Before
creating a new source-binding child, derive the legacy child ID with the exact
current operation-version mapping and inspect both its APP-STATE row and
deterministic legacy candidate path. If an exact legacy REVIEWABLE child exists,
validate it through its unchanged legacy basis and replay path and return it.
If the legacy row is DRAFT/incomplete, mismatched, or terminal-but-not-reusable,
or a legacy candidate package exists without an exact row, return a clear
conflict naming that legacy child. Do not mutate it, resume it under new rules,
adopt an orphan, or create a second V11 child for the same historical request.

For a new V11 child, an exact retry may resume a registered partial DRAFT only
after re-running full parent/source/span/World/request preflight and verifying
the complete row identity, operation manifest, V12 basis, and deterministic
child ID. Every present canonical package file must match expected bytes; extra,
foreign, symlinked or mismatched files fail without overwrite or cleanup. A
partial package on any status beyond DRAFT fails clearly. A complete
PREPARED/EXTRACTED/VALIDATED row may continue the existing CAS seal sequence on
an exact retry. A REVIEWABLE child is reusable only after the full package,
basis and replay verify. Never rewrite or delete old rows or artifacts.

## Consumer audit and recommended storage strategy

Audit re-anchored to remote main `cbd3a901...` found a bounded storage option
that preserves the registry's existing source acceptance rule and candidate
ownership boundary. The specific evidence is:

- `source_artifact_registry.load_registered_source_artifact_text`
  (`apps/live_control_server/services/source_artifact_registry.py:700-728`)
  resolves the registered canonical URI, reads its bytes, normalizes them, and
  checks the full SHA-256. Use it as the source of the child-owned copy.
- `graph_run_registry.assert_run_reviewable_evidence`
  (`apps/live_control_server/services/graph_run_registry.py:190-250`) binds run
  domain/campaign/session, source ID and digest, span index, and candidate.
  `_assert_source_component_matches_artifact` (lines 300-338) accepts either the
  canonical artifact URI or `source.md` beside the candidate graph, but the
  co-located form is recognized only when the candidate URI begins with
  `repo://` and the source URI exactly names that sibling. The existing
  `_resolve_repo_contained_uri` rejects traversal and root escapes; it resolves
  paths but does not explicitly reject every in-root symlink component.
- `RecapSemanticBasisV11` is paired with derivation V10 and manifest V10
  (`src/application_state/ingest/service.py:241-249`). Its validator requires
  `child.source.uri == basis.source_uri == parent.source.uri`, equal source
  digests, and exact span URI/digest identity
  (`src/application_state/ingest/service.py:843-860`). `verify_child_replay`
  independently rejects any changed source or span component ref
  (`apps/live_control_server/services/recap_semantic_candidate_correction.py:1126-1154`).
- Version selection is spread across independent consumers, so this is not
  only a child-creation edit. The top-level source-binding derivation V11 must
  support every accepted operation request V1-V10 without changing those
  operation manifests or their replay semantics. The existing semantic
  operation derivations (`operator_recap_semantic_candidate_correction_v1`
  through `_v10`) and their corresponding manifests remain the inner operation
  layer; V11 is a new outer source-binding version. In particular, semantic
  operation request V1 currently uses `RecapSemanticBasisV2` (APP-STATE basis
  V1 is for a different literal-evidence correction).
- Use a typed V12 source-binding envelope containing the selected existing
  operation basis unchanged (`RecapSemanticBasisV2` through `V11`), its
  operation derivation and manifest schema, plus parent source URI, child
  snapshot URI, source-artifact ID/digest, and exact span URI/digest. The nested
  operation basis keeps operation-specific pins such as V9 native World/head
  data and V10 expected parent revision/inherited-PC proof. Validate that inner
  basis against a parent-source view of the child, then independently validate
  the V12 child snapshot binding against the actual child row/files and
  registered canonical bytes. This keeps old operation semantics intact while
  making the changed source URI explicit in a new basis.
- Add V11/V12 dispatch to `is_recap_correction`, `assess_recap_semantics`,
  manifest/version selection and basis emission
  (`apps/live_control_server/services/recap_semantic_disposition.py:68-80,
  150-180`); APP-STATE basis unions and `_assert_recap_semantic_basis`
  (`src/application_state/ingest/service.py:795-870`); disposition recording
  (`apps/live_control_server/services/extract_promote.py:1144-1232`); request
  version to operation-basis mapping and new outer derivation selection in
  `correct_recap_candidate`
  (`apps/live_control_server/services/recap_semantic_candidate_correction.py:1365-1450,
  1580-1605`); child replay; and inherited-PC proof construction/ancestry
  (`src/application_state/ingest/service.py:680-689`,
  `apps/live_control_server/services/recap_semantic_candidate_correction.py:1216-1265`).
  Keep the external disposition effect pinned to the full V12 basis digest, and
  test the V12/V11 envelope with every operation request version.
- Inherited-PC proof has a second source-equality assumption: its ancestry walk
  requires each correction's source and span component refs to equal the parent
  (`apps/live_control_server/services/recap_semantic_candidate_correction.py:1237-1260`)
  and currently recognizes selected derivation versions for proof construction
  (`:1216-1236`). V11 must validate the copied source bytes against its parent
  and registered artifact while keeping the span ref exact; simply adding V11
  to the derivation set would still reject a child with the new source URI. Test
  V11 ancestry both with and without inherited-PC references, across operation
  versions that can introduce or preserve those references.
- The child ID hashes derivation, parent run ID, parent candidate digest and
  correction-manifest digest; the current path is derived from that ID
  (`apps/live_control_server/services/recap_semantic_candidate_correction.py:1550-1559`).
  The semantic manifest is stored in `lineage` and hash-checked on replay, not
  looked up as a separate run manifest file (`:1561-1568`, `:1137-1139`).
- Candidate ownership is an exact APP-STATE lookup by URI and digest across run
  statuses; ambiguity fails. A locator under `derived_candidates` without an
  exact owner also fails
  (`apps/live_control_server/services/extract_promote.py:996-1054`;
  `src/application_state/ingest/repository.py:124-145`). Retaining this subtree
  preserves the existing strong owner check.
- `resolve_promotable_ingest_run` derives `run_dir` from the candidate's parent
  (`apps/live_control_server/services/promotable_ingest_run.py:395-431`). A
  sibling candidate beside a parent run would alias the child's `run_dir`,
  `preview_union_store_path`, and synthetic `manifest_path` to the parent
  directory. The current semantic correction path does not need this alias.
- There is no server cleanup path for `derived_candidates` or canonical ingest
  run directories. The shared `_write_child_candidate` removes its temporary
  file but retains the final artifact
  (`apps/live_control_server/services/exact_run_evidence_correction.py:139-159`).
  Current creation writes the candidate before creating a DRAFT row and only
  checks the source URI when sealing
  (`recap_semantic_candidate_correction.py:1618-1660`), explaining the stranded
  production attempt. The existing test proves a sequential exact retry, not a
  concurrent one
  (`tests/test_recap_semantic_candidate_correction.py:3116-3129`).

**Recommended storage direction:** keep each new child in its own
`out/graph_memory/derived_candidates/<child-id>/` package with
`source.md` and `candidate_graph.json`; encode both component URIs as
`repo://...` so the registry's existing co-location rule applies. Before any
write, load canonical text through the registered SourceArtifact, validate its
ID/domain/campaign/session/World/digest against the frozen parent, and compare
the parent's actual source bytes and exact span index. Copy those verified
canonical bytes into the child package. Keep the same `source_artifact_id`,
World scope, source digest, and exact span-index URI/digest; only the child
source URI changes. Preserve every current operation request/manifest shape
V1-V10 byte-for-byte.

Use outer derivation V11 for the source-binding behavior across all accepted
operation requests V1-V10, with a typed `RecapSemanticBasisV12` envelope. The
envelope records operation derivation and manifest schema, contains the
corresponding existing semantic operation basis unchanged (`RecapSemanticBasisV2`
through `RecapSemanticBasisV11`), and adds parent source URI, child snapshot
URI, shared source-artifact ID/digest, and exact span URI/digest. Validate the
nested operation basis against its existing parent-source contract, then
validate V12 independently against the child snapshot bytes and canonical
SourceArtifact. Keep the correction-operation manifest stored in lineage and
its SHA-256 unchanged. Store the operation derivation separately from the
outer `derivation` so semantic assessment/replay can dispatch the operation
without confusing it with source-binding version. This avoids flattening or
dropping version-specific pins such as PC native-world fields, expected parent
revision, and inherited-PC proof. No DB migration is expected for JSON-only
lineage/basis additions; if implementation finds otherwise, return to PRIME.

The child-owned directory preserves exact APP-STATE candidate ownership, gives
each child a unique `run_dir`, and avoids aliasing the parent's package
directory. A sibling candidate would alias `run_dir`, preview storage and
synthetic manifest lookup to the parent, and weaken the path-based owner check.
No registry rule is relaxed.

## Idempotency, historical rows, and concurrency contract

Before claiming a V11 child, compute the old deterministic child ID using the
unchanged request-version-to-operation-derivation mapping, parent run ID,
parent candidate digest and operation-manifest digest. Inspect that legacy APP-
STATE row and its deterministic candidate path. An exact reusable REVIEWABLE
legacy child is verified by the unchanged legacy basis/replay logic and
returned. A DRAFT/failed/otherwise unreusable row, a mismatched row, or an
unowned legacy candidate path produces a clear conflict with the legacy child
ID; it is never rewritten, resumed under V11 rules, adopted or deleted. No new
V11 child is created for that historical request. This also prevents a new
child from silently duplicating the known stranded V10 attempt.

Only after read-only parent/source/span/World/manifest/path preflight and this
legacy-identity check may the request create its deterministic V11 DRAFT row.
APP-STATE's unique run ID is the idempotency claim and linearization point. If
the insert loses a race, reload the row and proceed only if every V11 identity,
lineage, operation manifest, V12 basis and parent pin is exactly equal. The row
creation and filesystem writes are not a cross-store transaction; interruption
after this claim can leave a registered held DRAFT.

On a deliberate exact retry, a matching V11 DRAFT can resume a partial package:
verify all existing canonical files byte-for-byte, create only missing expected
files, and never overwrite, delete, or adopt a conflicting path. Publish each
final file with atomic create-if-absent semantics, then compare its bytes; the
current `os.replace` helper is not sufficient as-is because a race can replace
an unexpected file. After both files pass registry/replay checks, advance
statuses with expected-revision CAS. A complete PREPARED/EXTRACTED/VALIDATED
row can continue sealing on exact retry. If package files are partial beyond
DRAFT, or the row is terminal/mismatched, fail clearly and leave all evidence
held in place. Expose the child ID and held/incomplete status in the correction
result/error so the operator can understand and retry it; never imply it is
reviewable.

Prove the multi-process behavior with two independent APP-STATE connections and
a barrier-synchronized identical request test. It must demonstrate one unique
row, no duplicate child, no clobber, exact file bytes, and one successful seal
with the competing caller reloading and verifying the same child. If DB
uniqueness plus atomic create-if-absent and status CAS do not prove this, add a
per-child lock only in an explicitly approved path; do not assume atomic writes
alone serialize the overall operation.

The legacy-id guard leaves existing stored rows on their unchanged verifier.
New V11 source-binding behavior is separate from operation versions V1-V10;
these are not alternatives. The entire lane remains design-only until PRIME
and ARCHITECTURE accept the envelope, history guard, and retry contract and pin
the exact ACTIVE write lease.

Any strategy must validate canonical source bytes and all source/span/World
bindings before creating artifacts. It may not weaken identity, World scope,
path containment, or replay checks. If a database migration, registry guard
change, new durable public contract, or additional owning path is required,
return to PRIME before implementation activation.

## Mandatory production-path witness

Implementation acceptance requires a disposable APP-STATE database and an
actual registered parent `ExtractionRun`/`SourceArtifact`, not a mocked
`create_extraction_run` call or helper-only test. Exercise the production
correction path end to end:

1. Load and validate the unchanged parent and canonical source; record parent,
   artifact, and span-index identities, bytes, and digests.
2. Create one semantic correction child, observe it remain held, and run the
   real registry sealing path.
3. Close/reopen through a fresh APP-STATE connection, re-resolve and assess the
   child, and re-prove source, span, World, semantic basis, and candidate replay.
4. Run each accepted operation request version V1-V10 through the new V11/V12
   envelope, proving its operation-manifest bytes/schema and replay semantics
   remain unchanged.
5. Submit the identical request again and prove exact V11 idempotent reuse. Seed
   exact legacy REVIEWABLE, stranded legacy DRAFT, mismatched legacy row, and
   legacy orphan-file cases; prove old valid work is reused and every other
   historical collision fails without creating a second child.
6. Interrupt after the DRAFT claim, after each of the two package files, and at
   each seal transition. Prove exact retries resume only eligible registered
   state and preserve all existing bytes; tampered, extra, symlinked, escaped,
   missing-parent, foreign-World, invalid-span, and changed-source cases fail
   before a new child write.
7. Run two concurrent identical requests through independent APP-STATE
   connections and the real file store. Prove one row and child package, no
   overwrite, and one successfully sealed result reused by the other caller.
8. Confirm the original parent, source artifact, and span index remain byte-for-
   byte unchanged.

Use a disposable database and synthetic or otherwise explicitly authorized
fixture data. Never use retained databases 54330/54331, retained ingestion
artifacts, production correction POSTs, or World publication for this witness.
Preserve the exact production reproduction privately; do not put operator data
or production identifiers in this repository.

## Candidate implementation paths — not a write lease

If the gates resolve without broadening the capability, ROOT may consider this
small candidate path set when activating the serial implementation:

- `apps/live_control_server/services/recap_semantic_candidate_correction.py`
- `apps/live_control_server/services/recap_semantic_disposition.py`
- `apps/live_control_server/services/extract_promote.py` (semantic basis
  dispatch only)
- `src/application_state/ingest/service.py` (only if the chosen versioned basis
  contract requires a validator update)
- `tests/test_recap_semantic_candidate_correction.py`
- `tests/test_recap_semantic_disposition.py`
- `tests/test_extract_promote_managed_world_target.py` (new basis dispatch and
  disposition effect binding)
- `tests/integration/test_recap_evidence_append.py` or a focused sibling test
- `tests/application_state/test_ingest_run_postgres.py`
- an owning `graph_run_registry` boundary test, likely
  `tests/test_graph_run_registry.py`

This list is advisory design material, not an exclusive lease. Do not edit
these paths under this BLOCKED handoff. No schema or migration path is included.
If the invariant cannot be proved at this boundary with that scope, return the
design for a steward decision rather than expanding it.

## Explicit exclusions and activation gates

No source rewrite, backfill, history repair, registry-guard relaxation,
provider call, extraction Process, correction decision, prepare, publication,
serving/API change, or 5202 runtime action. No Edge/Gazetteer experiment is part
of this source-binding capability.

Before activation, PRIME must request an independent ARCHITECTURE critique of
the V12 envelope, V1-V10 operation mapping, legacy-row guard, and row/filesystem
retry protocol. DOGFOOD owns the eventual disposable-DB production-path witness;
PRIME owns fixture lifecycle coordination. Then PRIME must pin an ACTIVE
handoff with exact base, branch, checkout, write allowlist, runtime/DB
ownership, verification commands, PR topology, and explicit implementation
authorization. Until then this successor remains BLOCKED and grants no write
authority.
