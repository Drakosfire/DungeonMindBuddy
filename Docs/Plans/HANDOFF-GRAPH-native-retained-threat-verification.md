# GRAPH: recover native retained Threat verification

Status: MERGED_PENDING_DELIVERY. Owner: PRIME runtime repair/cleanup stewardship.
Base: origin/main@945e25c04b18d8343a64bf77982d80eed8a463fb.
Original reviewed parent: PR2058@0b416b7d64bf86bb5f0b257799795e400092ba8a.
Branch: codex/native-retained-threat-verification, reuse buddy-context-loop.
Topology: parent2058 is merged/delivered at945e25c04b18d8343a64bf77982d80eed8a463fb;
this slice is rebased directly onto that actual main revision. PR2059 remains
parallel-independent (identity gate/test and handoffs); merge2059 before this
slice, then qualify its integration before merging. Start this slice's CI on
current main while2059 completes. The former parent's write lease is released;
PRIME owns this bounded successor path and no other writer is dispatched.
Runtime cutover stays serial and requires ADVERSARY's active lease release.


## One outcome and existing owners

A transient native child-verification failure leaves a known committed revision.
Ordinary confirm retry reconstructs with root/no context, calls the deleted Buddy
filesystem engine and never retries the available native verifier. Captured red
boundary reproduction preserves same child and proves zero additional publish.
Use the existing exact-parent native context adapter for this retained-record
branch. Use _advance_committed_verification(authority=authority) for verification
and persistence, instead of retired _verify_committed and duplicate saving.
No new authority, evidence contract, compatibility adapter or recovery framework.

## Exclusive expected writes

- apps/live_control_server/services/threat_publication_commits.py
- tests/test_cutover_threat_authority_port.py
- Docs/Plans/HANDOFF-GRAPH-native-retained-threat-verification.md

Preserve request/selection/identity/order/corruption guards and known committed
outcomes on dependency gaps. Contradictory native child proof stays unverified.
Retained historical identity checks remain. No zero-match retry overhaul, global
root-context demolition, Gold, source-specific edits, ingestion model changes,
providers, primary data, schema or dependencies in this slice.

## Validation and gates

Promote the existing ordinary lifecycle fixture to cover one transient first
verification failure followed by passed, failed or unavailable native proof.
Assert same committed child, exactly one publish, a second native verification
attempt and truthful verification status. Retain exact-parent unavailable recovery
and existing integrity/terminal replay controls. Capture red before implementation,
run native authority/producer/confirmation cohorts, source Ruff and diff checks.
Review cumulative parent-to-head change independently; after parent merges,
rebase/retarget and qualify actual cumulative main integration, CI and actual
merge. Deliver with primary tables/session state conserved only after runtime
lease release. Synthetic native-port tests do not prove PostgreSQL publication.

## Author evidence

Ordinary lifecycle red:3 failed,2 passed,17 deselected. After owner routing fix,
affected native authority/commit/proposal/scoped-guard/confirmation cohort52passed
with1 integration deselected and inherited schema warning. Same child and single
publish asserted in every recovery case. Positive native proof verifies; failed
proof, unavailable proof and missing parent preserve known unverified receipt.
Only confirm_threat_publication changes among runtime functions/classes; all
other ASTs identical. Source/test Ruff and diff checks pass. Red/green logs and
process-local prior experiment retained in private runtime-evidence. Independent
review and post-parent main integration/CI/merge/delivery remain outstanding.

## Settled implementation predecessor

Merged2060 at851586899f3274db1b68a47914ac021e60438e4c after all7CI and
independent actual-source approval; treea5b9a8e57b4120d2c0ff8d0eac811d2c378588de
matches the184-check integration. Implementation lease closed. Runtime delivery
is staged, not complete:693e/API1922493 remains frozen for ADVERSARY's S7comparison.
Private native-retained-threat-verification-delivery-contract.json is PREPARED,
not an active cutover. No claim this fix is live until conserved delivery proves it.
