# Reader-fence downgrade diagnostic repair — accepted

COMPLETE bounded PR4157, merged390f8a84d4145e2f30f47866af733edf367572ab from exact
608c743e8f29c2c83c848a6286940eae5f0f1da3, independent acceptance review5984416897
and classification44628066098 green. Lease released. Protected4154 work was not
absorbed; accepted repair later entered4154 through normal main merge.

Only the existing downgrade RuntimeError regex accepts both recovery forward and
forward recovery. Actual downgrade, reader/writer fences, retained rows and all
other assertions unchanged; no migration/runtime/dependency/selection change.
Target1PASS/full source-admission46PASS on Core99/WKef9, Ruff0/diffPASS. Prior red
base/candidate logs remain retained, not erased or retrospectively green.

MIND retains scratch/v9-buddy/v10-reader-fence-diagnostic-test-repair for active
fullgoal, no environment/mirror allocated or resources deleted by that slice.
Cleanup follow-up requires approved scope and process/mount/dirty/unique-data
checks. Transition/manual APIs/deployment/V11 remained separate work.
