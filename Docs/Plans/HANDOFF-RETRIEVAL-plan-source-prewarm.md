# Prewarm the verified Plan source revision before Send

ACTIVE for isolated experiment design under the Buddy latency objective.
Serial lane `codex/buddy-plan-prewarm`, base `4af4fc0f4`. The event
checkpoint experiment #4337 is closed without adoption. No Core code or
production database changes. Use the existing browser replay and writer sink.

Prior Q01 browser evidence from two warm/cold pairs measured median source
preparation 790 to 76 ms and Send to sink 7.80 to 7.11 s. The probe warmed the
cache explicitly. It did not prove that an ordinary pane event runs soon
enough, reaches the same worker, or survives another revision request.

## First bounded comparison

Run the existing disposable browser workflow with actual cold, settled warm,
and immediate-Send pane conditions. Establish the authenticated pane's
ordinary preparation schedule and how the worker chooses the Graph revision.
Then try one best-effort client trigger tied to the existing saved Plan pane,
keeping it outside Send and never carrying its return value into the Turn
request. Backend preparation must reuse the current managed World principal,
binding, and exact-revision Core cache. It does not read bodies, invoke a
provider, write a Turn, or return Graph material to the client. Ordinary
authorization, binding, and pin verification still run on Send. A different
worker, stale revision, or rejected request is a cold miss.

Scope any implementation to the existing Plan pane preparation and APP
source-cache owners, their tests and this handoff. Abort on a route overlap
or a requirement to change Core cache ownership. Test non-GM refusal,
World/revision turnover, no provider dispatch, no extra Send dependency,
trace equivalence, and cold cache misses. Record readiness time and memory,
including overlapping warm-up and immediate Send.

Use a counterbalanced, provider-free Q01 comparison on identical request,
corpus, and writer bytes. Continue only if the median net Send-to-first-Jev
gain is at least 200 ms for the settled pane, with no comparable regression
on immediate Send. Require unchanged evidence and exact citations. Treat an
older warm-cache sample as feasibility evidence and keep the branch out of
main if the natural trigger cannot deliver that result.
