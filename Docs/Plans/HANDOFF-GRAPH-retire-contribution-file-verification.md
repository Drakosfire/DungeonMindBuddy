# GRAPH: retire contribution filesystem re-verification

Status: MERGED_DELIVERED. Owner: PRIME under the operator cleanup/demolition objective.
Base: origin/main@2c8ed54d8a84168ec58ca889df7709a75b5578a0.
Branch: codex/retire-contribution-file-verification; reuse buddy-context-loop.
Topology: parallel-independent of PR2057@505f39a08d5333fb9cd45cfec2af636718298d0e
(identity comparison/test/handoff only). No unmerged dependency. Deliver serially.
ADVERSARY owns Gold and ingestion quality; this changes neither.

## One outcome and owner

Remove the optional filesystem verification mode from sealed contribution
reconstruction. All seven product call sites disable or omit it; only three
test helper calls enable it. DungeonMind publication already re-proves the
admitted source identity/revision receipt. A local file is not that authority.
Remove the mode and its now-unused repo_root/disclose_source_digest arguments,
including the native reconstruction wrapper's unused repo_root parameter.
Preserve proposal sealing/selection, mutation context, all native admission,
source identity/digest/revision rejection and commit/replay behavior.
The other preparation-time source verification in extract_promote_ops remains
outside this slice. Do not remove generic verification helpers still in use.

## Exclusive expected writes

- src/graph_memory/extract_promote_ops.py
- apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
- apps/live_control_server/services/threat_publication_proposals.py
- apps/live_control_server/services/threat_publication_commits.py
- tests/test_cutover_dungeonmind_first_world_initialization.py
- tests/test_cutover_native_genesis_continuity.py
- tests/test_candidate_graph_source_provenance_admission.py
- Docs/Plans/HANDOFF-GRAPH-retire-contribution-file-verification.md

No provider, source, Gold, primary database, schema or review-decision changes.
No competing admission owner or compatibility option. Root-context fallbacks and
receipt projection are separate investigations, not part of this deletion.

## Validation and failure cases

Existing nonintegration source provenance cohort baseline:44 passed,4 integration
cases deselected; inherited Pydantic schema warning. Strengthen the existing
verified-mirror case by removing its local mirror before sealed reconstruction;
prove reconstruction uses the sealed package while source admission stays pinned.
Run this regression red before removing the mode. Retain native publication
missing-source and fingerprint-drift rejection tests unchanged; CI exercises them
against disposable databases. Run source/admission and threatened publication
pure tests, inspect all call sites and cumulative diff, Ruff and compile checks.
Obtain independent Bugbot review and applicable CI before merge; qualify actual
merge and conserve primary state during owned delivery. Unit reconstruction is
not full native publication acceptance.

## Author evidence

The synthetic mirror-removal case failed red at the retired readable-file check
and passes after deleting the mode. Source/admission and affected publication
cohort:104 passed,4 integration deselected,4 route-fixture failures. The same
exact four route failures reproduce with base production implementations restored;
no unrelated fixture rewrite. Direct native confirmation cohort:9 passed,1
integration deselected. Source Ruff and diff checks pass. Original failure and
full outputs remain in private runtime-evidence/contribution-file-verification-*.log.
Native missing-source/fingerprint rejection test bodies remain unchanged; their
DB integration evidence is required from CI, not claimed from these pure tests.
Independent review, CI, merge qualification and delivery remain outstanding.

## Settled predecessor

Merged2058 at945e25c04b18d8343a64bf77982d80eed8a463fb after7successful CI
gates and independent original/projected/actual-merge approvals. Conserved API
delivery verified8964 source blobs, APP53/Core38 tables,9sessionfiles, savedPlan
HTTP and UI unchanged; native catalogue439. No provider/Gold/schema/dependency
changes; native source authority preserved. Private contribution-file-verification-
api-delivery-proof.json retains exact evidence. Runtime lease RELEASED.
