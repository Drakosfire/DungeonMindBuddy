# ONBOARD: Restore signed-out demo session capacity

Status: ACTIVE under the user's signed-out Sizzek demo, Bugbot, merge and deploy authority. Serial serving slice prepared on App-fence candidate `41bed746618a6d8e5d015d6997762232b0b6491c` while Actions run 45694435005 is in progress; only merge or publish if that exact candidate becomes healthy and live. Write lease: guest session limit, its boundary test, and this brief.

Production returned 429 after reaching 64 active guest sessions; sessions last 30 days, so the prior cap makes the demo unavailable after routine trial use. Raise the active bound to 256 while keeping the 1,024 total-record bound, 30-day lifetime, session isolation, advisory lock and fail-closed behavior. Do not evict or alter anyone else's sessions. At investigation the released document bundle was 92,831 bytes and the host had about 16.9 GB free; guest source documents retain their existing 16 MiB per-World bound. This is a finite capacity increase, not an unlimited scaling guarantee.

Verify admission after 64 sessions and continued origin and capacity rejection at the actual session endpoint, exact-head review, and new signed-out entry after Actions deployment. Preserve other Worlds and production settings.
