# ONBOARD: Open Combat Tracker for signed-out guests

Status: ACTIVE under the user's request to fix signed-out Combat Tracker and previously granted review, merge and deploy authority. Serial serving slice based on live `e97a0905a616dc251575a60a7f828cbdb07ff5b1`; recheck current production before release. Write lease: signed-out route and guest request transport, existing Combat encounter HTTP admission and transaction guard, focused tests, and this brief. Existing combat feature branches #4511, #4441, #4438 and #4411 were checked; this slice does not touch their owned functionality.

Allow the existing Combat Tracker to use the guest's bound Sizzek World and normal basic encounter list/create/save. Bind every request to the guest cookie and exact World, preserve CSRF and cross-World denial, serialize guest encounter writes with reset, and bound retained encounters and request size. More advanced imported mechanics and saved-statblock integrations remain governed by existing permissions; do not grant owner-only APIs to guests.

Verify signed-out route/transport, real-database create/save/reopen, guest isolation, CSRF, stale writes, capacity and reset ordering, plus signed-in controls. Review the cumulative diff, obtain Bugbot, merge, publish and deploy through Actions, then verify signed-out Combat Tracker on the deployed site.

The carried patch is byte-identical to reviewed #4743; the changed serving parent affects only trace UI. Focused guest isolation/reset, signed-in controls and UI checks passed on that identical implementation. Recheck the serving parent before publishing and verify the deployed surface.
