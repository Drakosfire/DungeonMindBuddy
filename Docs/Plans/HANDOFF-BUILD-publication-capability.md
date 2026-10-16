# BUILD: Advertise Worldbuilding publication capability

ACTIVE. PRIME solo implementation; ARCHITECTURE independent review.
Base 4ec8dabc969b73302ea9a0321f2971c2a440810f; branch codex/worldbuilding-publication-capability.
Serial backend prerequisite for a separately owned DOGFOOD confirmation consumer.
Concurrent DOGFOOD #1235/#1237 own UI paths; this lease does not edit them.

## Outcome and contract
Authenticated GET /api/live/extract-promote/worldbuilding/capabilities reports
that this server implements confirmation, whether its native authority selection
and database URL are configured, and safe machine-readable configuration reasons.
This is configuration discovery only: it does not establish database reachability,
source/World readiness, plan validity, or permission to publish a particular plan.
Confirm still performs every existing exact-run/source/World/head/identity/signature check.
Leave sealed plan models, serialized bytes, digests, historical inert metadata,
and prepare/confirm behavior unchanged. The descriptor lives outside those plans.
ARCHITECTURE recommended this separation instead of changing sealed plan fields.

## Exclusive write set
- This handoff
- apps/live_control_server/models/extract_promote.py
- apps/live_control_server/routes/extract_promote.py
- tests/test_worldbuilding_publication_capabilities.py

## Verification and limits
Exercise the mounted HTTP route with real local GM authentication, missing/invalid
credentials, configured/missing/retired/invalid authority settings, and rejected query
selectors. Prohibit publication, authority construction, database connections and
provider calls during discovery. Verify secret configuration is never returned.
Run existing publication verification tests to preserve sealed-plan behavior.
Implementation owns no serving ports, databases, corpus, runtime config or provider
calls. Push one reviewable PR; independent exact-head review precedes merge.
The later consumer must explicitly confirm exact reviewed effects, preserve decisions
on refusal, avoid duplicate submissions, and not auto-retry uncertain publication.
