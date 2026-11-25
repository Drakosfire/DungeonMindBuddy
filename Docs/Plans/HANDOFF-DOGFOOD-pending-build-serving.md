# DOGFOOD: serve pending Build context reuse

ACTIVE serial release assignment. Alan explicitly authorized deployment, reviewed
merges and production cutover while preserving current production changes. This
slice adopts merged source PR4642 c5001f5caabbd2dfa66d8a991604507d0a69533a,
reviewed implementation head e0bb59a53da9e0a5d09e7af210a1a15bae8809c8, into
observed production source928cfbc75cba30bdee2a4a0666cbcc8151ac0f8c. It grants no
new product/provider/model authority. Current main lacks serving prerequisites;
this release does not retarget or merge into main.

Branch codex/dogfood-pending-serving-928; immutable PR base
codex/dogfood-serving-928-base at928cfbc75cba30bdee2a4a0666cbcc8151ac0f8c.
Checkout /home/drakosfire/Projects/.codex/dogfood-ci-one-app/DungeonMindBuddy,
reused after source merge and closed verification workers. Composition9ac49c664e8db7060172c2807585161e003616e2
merges the two exact predecessors without conflict. Delivery is one serial release
PR; source4642 is merged, not a stacked dependency.

Bounded writes: this brief, truthful predecessor settlement in
HANDOFF-DOGFOOD-source-free-build-routing.md, production/source merge resolutions
if needed (none currently), scripts/prepare_buddy_release_image.sh and its focused
tests/test_guest_release_image_config.py. The helper must preserve existing guest
Plan=1 as well as Graph=1/Build=1; current script omits Plan. Dockerfile and runtime
configuration already support the flag and remain unchanged. No adjacent guest
feature work. Open4693/4696 lease Dockerfile/guest serving features, not these
helper/test symbols; inspected their exact file lists. CLARIFICATION4652 retains
normalize_candidate; Plan4580 retains PlanJevDriver; RETRIEVAL4584 retains evaluators.

Resources: reuse sole owned App benchmark_run_e27fc178267a4d7cbc90bf173dd3ecfe,
OID210452, cluster7711451860937605159, evaluator788881785ebc local32769, now
schema211; shared benchmark_shared_core OID204418 stays read-only. No new clone,
per-case clone, full contents inventory or reset. Tests serial; workers/connections
close before returning. Shared frontend lock /tmp/dungeonmind-frontend-verification-1000.lock.
External evidence/build scratch under verified Projects filesystem
48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. No parallel server/port allocation yet.

Observed production: containerb6ea3e142f3d, image
sha256:5ec48ce1391e6601b10a9e54b51d4786a05fd4b3b50ed31337139b5a293f1b7e,
loopback8080, source928cfbc75cba30bdee2a4a0666cbcc8151ac0f8c, guest label
review=0;page=0;home=;graph=1;build=1;plan=1. Preserve exact live environment,
mounts, ports, network endpoints, logging, restart and security settings. Recheck
source/image/config under deployment lock immediately before cutover; advancing
production is a re-anchor, not permission to overwrite it.

Validation: focused integrated pending SQL/POST/replay/reset controls on owned
App; source identity/native body/Graph citation/prompt-reference cases; affected
frontend reader/dispatcher controls and compile in pinned Node22 image; helper
flag acceptance/refusal. Review exact cumulative base-to-head and image source,
flag labels and installed reader proof. No broad local suites/contracts. Record
missing live semantic/latency and full release evidence honestly.

Recovery: schema211 fences prior210 readers. Do not use image-only rollback to928
following successful DDL. Prepare/review a forward-compatible recovery artifact
that retains211 and all pending readers while disabling only fresh pending
admission (retained pending delivery/read paths preserved); it is a NON-MERGE
operational artifact, not a second product feature PR. Reuse existing reviewed
APP-only Docker transport/drain/backup/forward recovery process, adapt exact
210-to211/source/guest identities, and require same-owned-App rehearsal and
independent evidence review before production DDL. Never restore over production
as an automatic failure response. Preserve the final drained backup and all
existing authority data. Record exact commands/hashes and unresolved gates.

Delivery remains unfinished until deployed signed-in app evidence proves current
context/long-chat reuse, no redundant search, valid citations and page creation,
review/save/reopen, plus clarification flow, semantic relevance/attribution/summary
and latency. Source merge or mocked tests alone are not final acceptance.

## Complete ordinary pending history boundary

Release discovery found freeze_interaction still calls legacy list_build_dialogue
(limit6). Earlier60-pair component tests manually supplied history, so they did
not prove this App-loading boundary. This directly contradicts the existing
long-chat goal; hold deployment and extend this release lease to exact
repository.list_pending_build_dialogue/_cached_build_dialogue_item,
AgentConversationService.list_pending_build_dialogue and BuildJevDriver
freeze_interaction. Preserve legacy six-slot input behavior; pending alone reads
all eligible completed dialogue using existing100-row transfer/reference bounds,
one read-only repeatable snapshot and lossless projection. Extend immutable
presentation caching to the equally pure pending completion codec with the same
full-row/fresh-reference key and bounds; it grants no access/source authority.
Prove ordinary POST with125 actual App chat pairs, oldest context in actual Jev
and writer requests, no Core preparation and created/saved page readback where
the owning action permits it. Preserve failed/unapproved output eligibility;
retained evidence admission remains its separate full-history owner.

The125-pair ordinary POST exposed an additional retained-evidence reader failure:
list_retained_build_turns passed more than100 rows to the guarded reference
reader. Its decoding now uses100-row batches while retaining every row, preserving
the existing reference guard and exact retained owner selection.

Working-tree focused boundary evidence: eight real PostgreSQL storage/POST cases
passed in16.33s on the same exclusively owned App clone;125-pair request included
oldest/newest history in actual mocked Jev/writer transport, no Core preparation,
review/confirm and committed page readback, plus idempotent confirm/delivery replay.
Clarification, Rules/native citations and reset-during-writer refusal passed.
Five existing synthetic Graph-binding serializer warnings remain visible.
Evidence: buddy-check.pending-release.w1eihyha/history-focused-sql.log.
This is not live-provider latency or signed-in deployment acceptance. The797f659
candidate image and ecec587 recovery image predate this fix and require replacement.
