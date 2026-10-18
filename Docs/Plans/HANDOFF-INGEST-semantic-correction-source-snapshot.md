# INGEST: bind semantic correction children to immutable recap sources

Status: **ACTIVE — PRIME authorizes DOGFOOD implementation of this bounded capability.**
Base: `origin/main@6743466d5f167f26d49c14d87b6353a35843f39e`.
Branch: `codex/ingest-source-snapshot-binding`.
Checkout: `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` (reuse).
Topology: serial, one implementation PR; no unmerged behavioral parent.
PR #1399 is merged and settled. PR #1400 is independently reviewed, merged,
delivered and settled at this base. No predecessor sync document remains open.
ARCHITECTURE independently accepted design 46f251a76859bd8772fa650f995dbc902b3fec7a
before activation; this commit records its four bounded clarifications.
PRIME owns activation, fixture lifecycle, merge and eventual runtime delivery.
DOGFOOD owns implementation and the actual-production-parent disposable-DB witness.
ARCHITECTURE independently reviews the completed cumulative implementation.

No overlapping implementation lane is active on these paths: ROOT's UI lease
is closed; MIND is read-only. Before any required path expansion, return to PRIME.
No new checkout, environment, source export or task directory under /tmp.
Established shared runtime/dependencies are reused. Only disposable PostgreSQL
127.0.0.1:54329 may be used for tests; retained54330/54331 are forbidden. PRIME
starts/removes the named fixture only after port/process/consumer checks.

Bounded runtime outputs: synthetic fixture artifacts beneath this checkout's
existing .pytest_cache; derived_candidates/.locks and owned same-filesystem
staging beneath each synthetic artifact root. No serving directory, retained
APP-STATE/corpus, production source, World or provider changes are authorized.

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

The source-byte invariant is strict: read the raw canonical artifact bytes and
the raw parent snapshot bytes through safe, root-contained paths and require
byte-for-byte equality, plus equality with the recorded full SHA-256 digests,
before decoding or text normalization. CRLF conversion, trailing-newline drift,
or any other byte change is a conflict even if normalized text would compare
equal. `load_registered_source_artifact_text()` may be used only after this raw
comparison; its normalization cannot establish byte identity.

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

Audit re-anchored to remote main `15aa918eb91071b469ea7f733cce6d2c6a3262e6` found a bounded storage option
that preserves the registry's existing source acceptance rule and candidate
ownership boundary. The specific evidence is:

- `source_artifact_registry.load_registered_source_artifact_text`
  (`apps/live_control_server/services/source_artifact_registry.py:700-728`)
  resolves the registered canonical URI, reads its bytes, normalizes them, and
  checks the full SHA-256. Its returned text is not sufficient for the strict
  raw-byte comparison. Resolve both the registered artifact and parent source
  URIs safely, compare the exact file bytes and their recorded full digests
  first, then use the validated bytes for the child-owned copy.
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
- The V12 envelope must be a closed, strictly discriminated mapping, not an
  arbitrary coercible union. The only valid request/derivation/manifest/basis
  combinations are:

  | Request | Operation derivation | Manifest schema | Inner basis |
  | --- | --- | --- | --- |
  | V1 | `operator_recap_semantic_candidate_correction_v1` | V1 | `RecapSemanticBasisV2` |
  | V2 | `operator_recap_semantic_candidate_correction_v2` | V2 | `RecapSemanticBasisV3` |
  | V3 | `operator_recap_semantic_candidate_correction_v3` | V3 | `RecapSemanticBasisV4` |
  | V4 | `operator_recap_semantic_candidate_correction_v4` | V4 | `RecapSemanticBasisV5` |
  | V5 | `operator_recap_semantic_candidate_correction_v5` | V5 | `RecapSemanticBasisV6` |
  | V6 | `operator_recap_semantic_candidate_correction_v6` | V6 | `RecapSemanticBasisV7` |
  | V7 | `operator_recap_semantic_candidate_correction_v7` | V7 | `RecapSemanticBasisV8` |
  | V8 | `operator_recap_semantic_candidate_correction_v8` | V8 | `RecapSemanticBasisV9` |
  | V9 | `operator_recap_semantic_candidate_correction_v9` | V9 | `RecapSemanticBasisV10` |
  | V10 | `operator_recap_semantic_candidate_correction_v10` | V10 | `RecapSemanticBasisV11` |

  Reject unknown, mismatched, duplicate, or coerced discriminator/schema
  combinations before persistence or replay.
- The nested legacy-basis validator needs a pure in-memory validation view of
  the V11 child. It may project only the legacy operation derivation and the
  parent's source URI for that inner check. Keep the actual new child run ID,
  candidate URI/digest, parent run/candidate pins, World/campaign/session pins,
  and version-specific operation data unchanged. Validate the V12 binding
  against the actual child row/files separately. Never persist or serialize the
  projected derivation/source ref, and never use the projection to prove raw
  source-byte identity.
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
  `apps/live_control_server/services/recap_semantic_candidate_correction.py:1216-1265`),
  and the inherited-PC projection in `apps/live_control_server/services/extract_promote.py`
  (`inherited_pc_references`, currently a v7/v8/v10 allowlist with a flat
  `inherited_pc_proof_sha256` lookup). That consumer must inspect the V12 inner
  operation basis while retaining the outer V11 identity. Keep the external
  disposition effect pinned to the full V12 basis digest, and test the V12/V11
  envelope with every operation request version.
- Inherited-PC proof has a second source-equality assumption: its ancestry walk
  requires each correction's source and span component refs to equal the parent
  (`apps/live_control_server/services/recap_semantic_candidate_correction.py:1237-1260`)
  and currently recognizes selected derivation versions for proof construction
  (`:1216-1236`). V11 must validate the copied source bytes against its parent
  and registered artifact while keeping the span ref exact; simply adding V11
  to the derivation set would still reject a child with the new source URI. Both
  the server proof builder and APP-STATE inherited-PC validator must understand
  mixed legacy/V11 ancestry, including a V11 child of a V11 child. Read the
  proof digest from the matching V12 inner operation basis, not a flattened
  field. Test legacy→V11, V11→V11 and relevant legacy-only chains, with and
  without inherited-PC references, across operation versions that can
  introduce or preserve those references.
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

Serialize each deterministic child ID with a safe per-child process lock, for
example `out/graph_memory/derived_candidates/.locks/<child-id>.lock`, acquired
with `flock(LOCK_EX)` and held from before legacy/current row and path inspection
through child creation, package publication, sealing, final reload and replay
verification. Create/open it with no-follow semantics, verify the lock is a regular non-symlink file and every ancestor is an
actual non-symlink directory contained under the managed root, and reject unsafe roots or path escapes. Never unlink or replace a persistent lock inode during operation, retry or
cleanup; each invocation opens a separate descriptor so process exclusion is
real. Stage on the same backing filesystem as final files. Once the lock is held, repeat
the full read-only parent/source/span/World/manifest/path preflight and
legacy-identity check; no untrusted or stale pre-lock observation may authorize
a write. A concurrent caller waits, then reloads and verifies the completed
child or retries only a matching eligible DRAFT. The unique APP-STATE run ID
remains a second idempotency claim: if insertion still reports a conflict,
reload and continue only if every V11 identity, lineage, operation manifest,
V12 basis and parent pin is exactly equal.

The lock is held across `create_extraction_run`, including its source-authority
persist and unique child-row insert, then all child package writes and expected-
revision CAS transitions. The row and filesystem are not one transaction; a
process interruption can leave an exact source revision and/or a registered
held DRAFT. An OS-released lock lets a later exact retry re-run the full
preflight, reload all authority, and resume only the matching DRAFT state.

On a deliberate exact retry, a matching V11 DRAFT can resume a partial package:
verify all existing canonical files byte-for-byte, create only missing expected
files, and never overwrite, delete, or adopt a conflicting path. Stage each
file under a unique temporary name outside the canonical child package. Publish
with atomic no-replace/create-if-absent semantics, then compare final bytes; the
current `os.replace` helper is not sufficient because it can overwrite an
unexpected file. Only the process holding the lock may clean up its own staged
temporary files after successful publication or normal completion. Never
delete another owner's temp, an orphaned temp from a prior process, or any
canonical evidence. A crash may leave a staged temp; it is not a package file,
is never adopted, and does not block a retry that creates its own staging file.
After both canonical files pass registry/replay checks, advance statuses with
expected-revision CAS. A complete PREPARED/EXTRACTED/VALIDATED row can continue
sealing on exact retry. If package files are partial beyond DRAFT, or the row is
terminal/mismatched, fail clearly and leave all evidence held in place.

Held/incomplete failures must identify the child run ID and its actual held
status using the existing `ExtractPromoteError.response()` fields (`code`,
`message`, `status_code`, `diagnostics`, `failure_result`, `run_status`, and
`inspection_status`). Put the child ID and useful reason in the existing message
or `ExtractPromoteDiagnostic`; do not add a response field, change the public
schema, or describe the child as reviewable before sealing succeeds.

Prove the multi-process behavior with two independent APP-STATE connections and
a barrier-synchronized identical request test. It must demonstrate one unique
row, no duplicate child, no clobber, exact file bytes, and one successful seal
with the waiting caller reloading and verifying the same child. Include a
crashed/abandoned-owner case proving the OS releases the lock and the next exact
retry does not adopt or delete another process's stale staging file.

The legacy-id guard leaves existing stored rows on their unchanged verifier.
New V11 source-binding behavior is separate from operation versions V1-V10;
these are not alternatives. The envelope, history guard and retry contract were independently critiqued
before this ACTIVE lease. The full owning test suite has now passed for the
current implementation head; independent exact-head review is still required
before PRIME merge.

Any strategy must validate canonical source bytes and all source/span/World
bindings before creating artifacts. It may not weaken identity, World scope,
path containment, or replay checks. If a database migration, registry guard
change, new durable public contract, or an additional owning path beyond the
bounded source-binding implementation paths below is required, return to PRIME
before implementation activation. The only newly approved durable version is
the internal V12 basis envelope; no unrelated public API or database schema is
approved.

## Source-authority mutation and crash-ordering contract

`graph_run_registry.create_extraction_run()` calls `_persist_source_authority`
before inserting the unique run row. That source-authority write is an explicit
part of this design, not a forbidden registry call or an atomic transaction.
"Preflight before mutation" means finish all parent, raw source-byte, span,
World, request, manifest, legacy identity, child destination and lock checks
before calling it. The subsequent `persist_source_markdown` call is allowed
because the child needs registered authority before its row can be created.

The source service hashes the exact supplied text and enforces immutable
artifact/digest/revision bytes and scope. Repeating the same artifact, digest,
bytes and scope is idempotent. Different bytes, scope or a conflicting revision
must fail. The only existing monotonic exception is filling a previously null
World binding with the already-validated frozen parent World; do not broaden
that exception. If interruption occurs after source persistence but before the
child row, an exact retry may reuse only that same verified authority. A
conflict or different source revision stops before creating a child row or
package. The disposable-DB witness must prove the exact insert ordering,
idempotency, and conflict behavior; do not bypass or weaken the source registry.

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
   remain unchanged. Assert each closed discriminator pair, reject mismatches
   and unknown/coercible variants, and prove the pure validation projection is
   never persisted. Verify `extract_promote.inherited_pc_references` reads the
   nested proof digest and mixed legacy/V11 ancestry supports a V11 child of a
   V11 child.
5. Submit the identical request again and prove exact V11 idempotent reuse. Seed
   exact legacy REVIEWABLE, stranded legacy DRAFT, mismatched legacy row, and
   legacy orphan-file cases; prove old valid work is reused and every other
   historical collision fails without creating a second child.
6. Interrupt after source-authority persistence, after the DRAFT claim, after
   each package file and at each seal transition. Prove exact retries resume
   only eligible registered state and preserve all existing bytes; different
   source bytes including CRLF/trailing-newline drift, tampered/extra/symlinked/
   escaped paths, missing parent, foreign World, and invalid span fail before a
   new child write. Prove exact source-authority retries are idempotent while
   conflicting bytes/scope/revision fail and only the existing null→World fill
   is accepted.
7. Run two concurrent identical requests through independent APP-STATE
   connections and the real file store. Prove one row and child package, no
   overwrite, and one successfully sealed result reused by the waiting caller.
   Include owner interruption and verify the next exact retry never adopts or
   deletes a prior owner's staging file.
8. Confirm the original parent, source artifact, and span index remain byte-for-
   byte unchanged.

Use a disposable database and synthetic or otherwise explicitly authorized
fixture data. Never use retained databases 54330/54331, retained ingestion
artifacts, production correction POSTs, or World publication for this witness.
Preserve the exact production reproduction privately; do not put operator data
or production identifiers in this repository.

## Exclusive implementation write lease

Only these 13 paths are leased:

- `Docs/Plans/HANDOFF-INGEST-semantic-correction-source-snapshot.md`
- `apps/live_control_server/services/recap_semantic_candidate_correction.py`
- `apps/live_control_server/services/recap_semantic_disposition.py`
- `apps/live_control_server/services/source_artifact_registry.py` (raw-byte helper only, if needed)
- `apps/live_control_server/services/extract_promote.py` (basis dispatch and nested inherited-PC review projection only)
- `src/application_state/ingest/service.py` (V12 types, closed validators and ancestry only)
- `tests/test_recap_semantic_candidate_correction.py`
- `tests/test_recap_semantic_disposition.py`
- `tests/test_extract_promote_managed_world_target.py`
- `tests/test_source_artifact.py`
- `tests/integration/test_recap_evidence_append.py`
- `tests/application_state/test_ingest_run_postgres.py`
- `tests/test_graph_run_registry.py`

No repository, schema, migration, registry-guard, route, UI, dependency or global
source-service behavior changes. If these paths cannot prove the invariant,
return to PRIME before expanding. Use the existing source authority dry_run=True
for read-only preflight conflicts; frozen-byte identity is independently required.
Global source authority may accept a distinct digest-keyed revision; this operation
must reject frozen-source drift rather than changing global admission policy.

## Explicit exclusions and activation gates

No source rewrite, backfill, history repair, registry-guard relaxation,
provider call, extraction Process, correction decision, prepare, publication,
serving/API change, or 5202 runtime action. No Edge/Gazetteer experiment is part
of this source-binding capability.

The design critique is complete; the exact implementation is not yet reviewed.
No retained correction/decision/prepare/publication or provider request is leased.
No production runtime action is authorized by the worker handoff.

## Verification commands and completion

From the owning checkout, use existing shared runtime Python and dependencies:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. TMPDIR="$PWD/.pytest_cache" /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-a044ac4e/runtime/bin/python -m pytest -o addopts='' --basetemp=.pytest_cache/source-binding tests/test_recap_semantic_candidate_correction.py tests/test_recap_semantic_disposition.py tests/test_extract_promote_managed_world_target.py tests/test_source_artifact.py tests/integration/test_recap_evidence_append.py tests/application_state/test_ingest_run_postgres.py tests/test_graph_run_registry.py -q --tb=short
```

## Implementation verification recorded for the current branch head

The scoped command above passed **276 tests** against the disposable PostgreSQL
instance at 127.0.0.1:54329 (10 existing Pydantic `schema`-shadow warnings).
The suite exercises V1–V10 operation mapping under the V11/V12 envelope, mixed
legacy/V11 inherited-PC ancestry, exact retry, legacy-row collisions, raw-byte
and span drift, and source-authority interruption/idempotency/scope conflict.
`test_production_source_snapshot_correction_and_locked_parent_authority` now
creates a synthetic registered recap `SourceArtifact`, runs the actual production
extraction pipeline with a deterministic no-provider fixture, applies a held V8
correction, and proves fresh APP-STATE reopen, replay, semantic assessment, and
exact retry. It verifies the producer-owned run-local `source.md`, parent
candidate, and span bytes remain unchanged. The separate append-path integration
fixture continues to cover the V9→V10 chain, fresh-process reopen,
independent-process concurrency, source-authority interruption/idempotency, and
abrupt lock-owner death after a DRAFT claim.

Review identified source-file and parent-authority races at the file boundary.
The correction now reloads the parent run and resolved/pinned identity under the
per-child lock, requires the same REVIEWABLE revision and immutable lineage,
then repeats the source/span preflight before any child row or package claim.
Disposable-DB coverage rejects a parent made REJECTED or SUPERSEDED while the
correction waits. Both no-follow component readers open final paths in
nonblocking mode before rejecting non-regular files; regressions mutate source
bytes during lock acquisition and verify FIFO paths fail promptly.

`ruff check --select F` passed for all eight modified Python files, Python
compilation and AST parsing passed for those files, and `git diff --check`
passed. These checks establish
the disposable implementation witness only; they do not constitute the required
independent exact-head ARCHITECTURE review, PRIME merge, or runtime adoption.

The mandatory witness above must originate the parent through the actual
production producer/registry path with run-local source.md; manually registering
a canonical-source parent is only a control, never acceptance for this defect.
Include every V1–V10 operation mapping and mixed legacy/new ancestry, actual
seal/reopen/assessment, deterministic replay/retry, interruptions and two-process
concurrency. Assert parent/source/span bytes and rows remain unchanged.
Scoped Ruff, compile and cumulative diff check are also required. Inspect exact
base-to-head changes, commit intended files, push the branch and open one PR.
Send PRIME exact head, commands/results, negative boundary evidence and known
limits. Do not merge or deploy. Independent ARCHITECTURE review precedes PRIME
merge and separately verified runtime adoption. Keep this handoff ACTIVE until
those facts are known; do not pre-mark acceptance or invent review/merge IDs.
