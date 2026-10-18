# INGEST: bind semantic correction children to immutable recap sources

Status: **BLOCKED — design only; no implementation lease.**
Base confirmed through GitHub: `origin/main@803c1ece8869f9a3253dff0f0c646bbcf645fc75`.
Parent capability: PR #1399, merged at that base. This is its serial successor;
there is no unmerged behavioral parent. The current checkout also contains the
settlement-only commit `e01ff297c61cefa197c69cd2cb3c870c2781ba7e`; it is not a
behavioral dependency. PRIME retains activation and merge authority.

The local `git fetch origin main` could not update shared Git metadata because
the worktree's common `.git` path is read-only. GitHub's current commit listing
confirmed the base above. An open-PR search found no source-snapshot correction
implementation; PR #1235 is held and its listed Graph Review UI paths do not
overlap the proposed server/App-State paths below.

## Defect and boundary

PR #1399 preserves frozen World scope in semantic correction children. It does
not resolve the separate production source-component URI failure. A parent may
refer to an immutable source snapshot co-located with its candidate graph. The
semantic correction currently relocates the child candidate under
`derived_candidates/<child-id>/candidate_graph.json` while retaining the
parent's source and span-index component refs. The registry correctly accepts
only a canonical `SourceArtifact` URI or a `source.md` snapshot co-located with
the candidate graph. After candidate relocation, the retained run-local source
URI is neither one. The registry rejects the child. Today the child candidate
file is written before the registry rejects its run, which can leave an orphan
file.

The registry guard is enforcing provenance and containment. Do not relax it to
make this child pass. The successor must resolve the incompatibility before any
child file or APP-STATE row is written.

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

Before any file write or registry/App-State call, reject missing or foreign
artifacts, source or parent World disagreement, absent files, changed bytes or
digests, invalid span indexes, symlinked paths, and paths escaping the managed
artifact root. A rejected request must leave no child file and no child row.
An existing child may be reused only when its complete stored identity, source
binding, candidate bytes, basis, seal state, and replay all match. A conflicting
row or orphan file must fail explicitly; do not silently repair, adopt, delete,
or overwrite it.

## Storage and schema decisions that block implementation

No storage strategy is selected yet. Resolve these choices with the owning
registry and APP-STATE contracts before ROOT activates an implementation lane:

1. **Keep the parent source URI unchanged.** The existing semantic-basis check
   and replay verifier require the child source and span component refs to equal
   the parent refs. A candidate placement that keeps the source snapshot
   co-located may preserve that contract, but its path must be audited against
   run-directory ownership, manifest lookup, registry identity, candidate-owner
   resolution, cleanup, and concurrent retries. A sibling path is only a
   hypothesis until those consumers are checked.
2. **Give the child a canonical or child-owned source URI.** This can satisfy
   source/candidate co-location or canonical-artifact rules, but it changes the
   source component URI. Existing `RecapSemanticBasisV11` validation and
   `verify_child_replay` require exact parent/child source refs. This route needs
   an explicit versioned basis/derivation and child-identity/idempotency policy;
   it must keep old stored children verifiable without rewriting them. Do not
   add an unversioned exception or silently alter the existing basis.
3. **Define incomplete-retry behavior.** Prove when a fully identical child can
   be returned, and how a pre-existing candidate file without a row, a draft
   row without a valid candidate, or a mismatched child identity fails closed.
   No cleanup or repair side effect is authorized by this design.

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
4. Submit the identical correction again and prove exact idempotent reuse: same
   child ID and bytes, with no extra file or row.
5. Exercise missing, foreign-World, symlink, escape, and changed-byte failures;
   assert each fails before any child file or row is created.
6. Confirm the original parent, source artifact, and span index remain byte-for-
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
- `src/application_state/ingest/service.py` (only if the chosen versioned basis
  contract requires a validator update)
- `tests/test_recap_semantic_candidate_correction.py`
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

Before activation, ROOT/PRIME must settle the storage strategy, basis and
idempotency versioning, conflict/orphan behavior, the disposable DB witness
owner, and any paths or schema effects discovered by consumer audit. Then pin an
ACTIVE handoff with exact base, branch, checkout, write allowlist, runtime/DB
ownership, verification commands, PR topology, and explicit implementation
authorization. Until then this successor remains BLOCKED and grants no write
authority.
