# PERF: hosted first Jev timing

ACTIVE serial Buddy slice under the operator's hosted Send-to-Jev goal.
Base ca239ca90. The preceding #4140 Graph stage timings are merged and
observed on hosted af014b344. No unmerged dependency. This slice owns only
Build and shared native initial-decision stage timing, trace-relative phase
offsets, native complete-entity read timing, their
existing tests, and this handoff. It does not change queries, cache keys, storage
authority, provider settings, or prompts. It runs locally without providers for
contract verification. Hosted comparisons use authorized ordinary Build turns
and retain only bounded measurements in the release record.

Two retained hosted observations correlated by first transport marker and trace
ID measured 6597.5 and 8308.8 ms after server trace start. The top-level
instrumented sums were 4529 and 5971 ms. The residuals are 2068.5 and 2337.8 ms.
The Build browser-to-server interval is outside those sums. Native match catalog
construction used 1579.8 and 1919.8 ms within the native query span. Durable
accept and claim used a combined 1380 and 1362 ms within runtime admission.
Keep both parent and child spans visible, but subtract nested intervals only
once when accounting for the critical path. Existing cumulative execution
append counters include post-dispatch work and cannot explain the residual.

The first Build decision's stage, authorization and sending acknowledgement
get named observation spans before the existing transport marker. Authorization
includes the durable admission span when it runs there. Complete Core entity
reads get a cumulative timer. The timer may also observe authored/campaign reads
outside catalog assembly, and must be treated accordingly. Verify unchanged
dispatch entry and exact Graph catalog equality with local tests and compare
exclusive timing again in hosted opening and continued turns.

The exact transport marker gates both decision paths. Monotonic phase offsets
support interval-union accounting even where retained UTC seconds coincide.
