# ONBOARD: mobile guest graph on the serving lineage

Status: ACTIVE. Carry merged main PR #4574 onto the currently deployed serving
lineage, serially after #4567. Base `c51a1a8a291de97cd3314d02d25fcb3793d25a6d`
has the same product tree as deployed image revision `cc4bf0500de93ebb80ad691c7234de76ed93d27f`
(`sha256:bd17c6d220a7498d7b56abcbffea4422d8295be22e9e5da137f76eb73e4c5282`).
Branch: `codex/onboard-mobile-serving-c51a`. The bounded write set is the
mobile graph source, CSS, focused test and its implementation handoff, plus this
serving handoff. No database, schema, auth, public copy or provider changes.

Verify the cumulative serving diff against the base and the exact head with
the hosted and discovered frontend suites; compare inherited failures against
the retained matching serving baseline. Obtain independent Bugbot review. Before
activation, recheck the actual live image, shared deployment locks and concurrent
runtime work, then build an exact-source image and verify guest flags and the
detached fallback. Do not use the old Compose activation packets. After release,
verify signed-out mobile graph interaction, health and private-World isolation.
