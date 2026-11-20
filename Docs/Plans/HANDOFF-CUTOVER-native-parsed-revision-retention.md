# Retain two parsed native revisions

Buddy's live neighborhood route rebuilds its parsed revision whenever current
and historical pins alternate. The source-verification pool already retains two
proofs. The isolated Elderwyld diagnostic measured 102–105 ms for returning
to retained parsed revisions, compared with 532–612 ms with one slot.

Keep this serial V11 change in Buddy inspection and its owning tests. Bound the
number of retained parsed revisions to two per process. Core must continue to
verify the requested revision and fresh source authority before use, and retain
its exact envelope/content key within each slot. Verify cold and repeated
reads, newest child publication, historical return, exact cited bytes,
withdrawal, LRU eviction and concurrent slot ownership. Compare retained and
peak RSS before deployment. Retain the existing qualified serving fallback.
