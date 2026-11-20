# Suppress repeated Build dialogue warmup during history refresh

**ACTIVE.** The hosted Send latency goal authorizes this serial successor to
deployed #4202. Base `807e1771e8e3addc83ad5df42d4c7f56f1ad603f`, branch
`codex/jev-build-warmup-snapshot`, reusing the completed predecessor checkout
`jev-build-dialogue-warmup/DungeonMindBuddy` on Projects.

Write set is this handoff, `apps/live_control_server/routes/conversation_library.py`
and `tests/test_conversation_library_routes.py`. Treat a successfully warmed
six-slot snapshot as done until bounded worker bookkeeping evicts it. Do not
schedule speculative reads while the newest turn is accepted or running.
Keep the current pointer read, cache ownership and authoritative Send path.
This is load shedding and grants no authorization to use stale data. No new
runtime, schema, port, provider call or primary mutation is required for local
verification. Existing local disposable PostgreSQL fixture remains the owner.

The previous hosted sample reached the transport in 18.12 seconds from ingress.
History and warmup logs show concurrent repeat activity but lack the binding
needed to attribute the whole delay to warmup. Validate repeat history refresh,
active turn suppression and fresh snapshot behavior at the route, then run the
exact-head query-and-answer contract and independent review. Measure warmup
frequency and cold and warm dispatch separately after deployment.
