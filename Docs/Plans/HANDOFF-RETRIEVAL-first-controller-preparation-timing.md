# Account for Build first-request preparation before authorization

**ACTIVE.** Serial timing slice for the hosted Send-to-first-Jev goal after
deployed #4205. Base `bb050a24ed98b2f6acbc9253f04ca28784b45f47`, branch
`codex/jev-first-controller-preparation-timing`, existing managed Projects
checkout `jev-build-dialogue-warmup/DungeonMindBuddy`.

Lease: this handoff, the Build Jev harness, and the existing ordinary Build
qualification test. Checked open #4207 and #3824 for these files. #3824
overlaps the streaming route and server middleware, which this slice leaves
untouched.

Measure SDK request construction through entry into the authorization
callback, on the existing first-wire trace. Stop the span before authorization
and durable admission so these timings do not overlap. Close it on exits
that never reach authorization. Keep all authorization, claim, dispatch and
source behavior under the same owners. Verify through the actual ordinary
Build transport fixture and the exact-head local query-and-answer contract;
then independent review. Any new real browser samples require the isolated
benchmark conversation and runtime, never the working conversation.
