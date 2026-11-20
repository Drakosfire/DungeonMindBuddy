# REFERENCE: retire unused opening helpers

Status: SOURCE SETTLED. PR2310 merged as
062984f32a26ebfeaa1f1b914c32742f71d51570 from reviewed
cd4040b7e33b3a303c5718b61c195b41a3841ed2; source write lease released.
Runtime activation remains held. Historical allocation follows.
Status at allocation: ACTIVE source retirement. PRIME owns this serial slice from remote main
6d960ed05831ef5c4aeeae5500474a0b4d68b0f8, branch
codex/reference-unused-opening-helpers, existing buddy-context-loop checkout.
No unmerged parent. Runtime activation remains held during storage recovery;
ADVERSARY coordination remains off.

## Outcome and caller proof

Remove useOpenGraphReference and glanceOnlyForGraphReference, their barrel
exports and their exclusive tests. Exact symbol/import search finds no consumers
outside those source files, the graphReference barrel and the two test files.
The larger diagnostic/resolver/card closure remains independently gated. This
slice does not remove the shared projection host, object preview, saved-statblock
editor, hover tokens, threat view-model, or their tests.

The wrappers are not substitutes for current reference behavior. Mounted native
selection uses SurfaceGraphReferenceInput; activation uses
NativeGraphObjectPreview and the shared SavedStatblockSession. Keep their owning
coverage and meaningful unknown/stale/foreign-World failures.

## Write lease and topology

Delete only:
- graphReference/useOpenGraphReference.ts and .test.tsx
- graphReference/openGraphReferencePolicy.ts and .test.ts

UI paths are under apps/live-control-ui/src. Edit graphReference/index.ts only
for those exports. Remove exactly those two test paths from
ci/test-classification.json under the partition granted in
HANDOFF-PLAY-shared-native-retrieval.md. CI PR2288 inspected head
657def68f68bfffca839c92549146c8ded1044e0 retains its additive entries and all
other inventory/qualification owners. No new manifest or retirement registry.
This handoff and HANDOFF-REFERENCE-adoption-inventory.md own the caller decision.

Delivery is serial. The next diagnostic-panel slice is not activated here:
ci/contracts.json and tests/fixtures/ci_original_commands.json still name its
subjects, and test_ci_contract.py requires exact historical equality. Resolve
that contract with its owner without modifying the frozen fixture in this slice.
Held server PR2104 stays untouched.

## Verification

Prove remaining source contains no import, export or caller of the removed
symbols; inspect the exact cumulative diff and classification delta. Run the
existing CI inventory/command guards. Run and validate exact-SHA local hosted
frontend/build evidence and the discovered-suite diagnostic at an integrated
checkpoint. Compare the retired cases and retained reference/statblock coverage;
removing an unmounted subject is not permission to delete live failure checks.
Obtain independent exact-head review, push/open the owning PR, then merge under
standing PRIME authority when gates pass. No database, provider, retained browser
storage, service or migration action is necessary for this source retirement.
