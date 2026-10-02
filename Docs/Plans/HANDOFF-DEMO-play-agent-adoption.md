# HANDOFF — DEMO: Play adoption of the World Agent conversation

**Status:** BLOCKED — APP-STATE storage is complete; AGENT-INTERACTION production runtime adoption remains pending; no DEMO implementation or runtime lease
**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design anchor:** Buddy `main@6a11200c729c1abe6d730f7794d935b966041eda`
**Topology:** serial: APP-STATE conversation storage/domain service (#822/#827 complete) → AGENT-INTERACTION production runtime adoption → DEMO Play surface cutover. #826 remains separately paused for its own v2 redesign and zero-skip evidence; PRIME has ruled it is not a Play predecessor. This is a docs-only refresh; no implementation or runtime lease is active.

## User transition

From a managed World with a selected World-owned Play Run, the operator can ask DungeonBuddy about the current moment of play in the same World-wide Agent conversation used across surfaces. Each turn records its exact Play surface, selected Run identity/revision or snapshot, and pinned Runbook identity/committed revision/hash. A change in the server-resolved Play scope starts a new provider-continuation segment. A late response remains attached to the originating Run's historical turn and never becomes the current answer or context for a newly selected Run.

This is one Buddy product capability: adopt the generic Agent turn contract on Play. It does not add Graph retrieval, citations, mutations, a new Agent framework, or changes to Run ownership.

## Current evidence and gates

Buddy #820 completed the World PlayRun C2 UI migration at
`bfa741261e715eadb48d873f87fccc1764417da8`; its lease ended at merge. The
generic `POST /api/live/agent/turn` request permits Play and Run locators, but
the current work resolver accepts only Plan and returns
`work_kind_unresolved` for a Run. Play has no Ask plugin. Its
PlaySurfacePublisher builds legacy A7 publication context from campaign V1
records only, so that publication is not authority for a World V2 Agent turn.

Current Buddy main is `6a11200c729c1abe6d730f7794d935b966041eda`. PR #836
(`6de8d831ab82308086677fb3038122936ab9a756`) adds the managed-World/native-
Graph binding but not generic Run resolution. PR #839
(`47f9955fd054017a1739dfa8129df65dd61d6bcd`) changes Plan source-bundle
diagnostics only. PR #848 (`be608e77ee86ecc2cd57336e98b289c9901823e7`)
adds allowlisted internal trace phases only; it does not change Run resolution,
provider dispatch, turn results, or concurrency. PR #851 settled the unrelated
Hermes prose-pairs handoff at `4466c77ad9db716aaa266d672e8faa860255f3b0`.
PR #852 merged the DEMO readiness report at current main and records D0 as
incomplete pending a verified current runtime pin. None supplies the shared
World-conversation runtime seam.

Buddy PR #822 merged at `0e49c4d708d3e16c8068384549adb50e863bf64a`,
providing typed PostgreSQL storage/domain service for server-assigned World
conversations, one active conversation per verified World, CAS/idempotent
lifecycle commands, ordered turns, typed provenance, source-bound drafts, and
bounded exact-World legacy import. Its assigned service/PostgreSQL tests passed
14/14. The full `tests/application_state` run had 182 passes and 3 failures;
the exact same stale migration-head assertions reproduce on its clean base, so
they are inherited. PR #827 merged at
`c48abb9fa5857df90af0b086ab78294445fd252a`, adding World-wide semantic
idempotency receipts and the unique fence. Its focused retry/PostgreSQL tests
passed 9/9 and existing conversation service tests passed 10/10. Together,
#822 and #827 complete the APP-STATE storage/domain-service and World-wide turn
receipt gate.

The current-main APP-STATE handoff
`HANDOFF-APP-STATE-world-agent-conversation-v1.md` defines the accepted
contract: one server-generated active conversation per verified World across
surfaces; provider-neutral visible history; exact per-turn surface and
role-labeled primary/supporting work provenance; and fresh context/tool
resolution every turn. The remaining serial blocker is AGENT-INTERACTION's
production runtime adoption. Its A2 adapter boundary is COMPLETE/MERGED; A3 is
a challenger experiment only, not production selection. No current-main or
open-PR evidence proves canonical conversation turns are adopted by the
production Agent path. PRIME's sequence is now APP-STATE (#822/#827 complete)
→ AGENT-INTERACTION runtime adoption → DEMO surface cutover.

The current AgentRuntime boundary handoff A2 is COMPLETE/MERGED, while its A3
PydanticAI experiment is a challenger only and does not select a production
adapter. That is not evidence that canonical APP-STATE conversation turns have
been adopted by the production Agent runtime. PRIME's current sequence remains
APP-STATE storage/domain service → AGENT-INTERACTION runtime adoption → DEMO
surface cutover. The first two gates must complete and be pinned before this
Play slice can activate.

PR #826 remains open/paused and unmergeable at head
`4fa28e586783f0e63edb85fa664afa53521367f6`, based on stale
`5b7e1e4543c94708e11687feb60093d98d6db93f`. Its exact eight changed paths are:
- `apps/live_control_server/integrations/dungeonmind/world_space_provisioning.py`
- `apps/live_control_server/routes/world_containers.py`
- `apps/live_control_server/services/world_container_registry.py`
- `apps/live_control_server/services/world_space_binding.py`
- `pyproject.toml`
- `tests/integration/test_world_space_binding_postgres.py`
- `tests/test_world_space_binding.py`
- `uv.lock`

RAKE DUTY's read-only rework audit against Buddy main
`c3904bc1e08df689b92d5a0b710b546f77af4600` and merged #836 found that #826's
v1 contract cannot be resumed unchanged:
- #826 adds flat `space_*` fields to v1 registry records, while main stores v2
  records with nested `native_graph_binding` and forbids extras. Redesign on v2
  with a distinct typed `knowledge_space_binding`; preserve the existing
  Graph relation, v1 read compatibility, and v2 CAS.
- Its public WorldContainer DTO must expose only redacted status/version, never
  the raw space ID, allocation ID, MIND receipt, database configuration, or
  internal storage record.
- #826 and #836 both change `world_containers.py`; any #826 redesign must
  retain #836's guarded Graph routes and DTO. ARCHITECTURE ruled that current
  provisioning is local-only behind the loopback local-operator bearer guard,
  enforced before repository, registry, database, or MIND side effects. This
  does not authorize remote exposure; remote use needs a separate
  actor-and-exact-World authorization contract.
- Keep DungeonMind pinned to MIND #96 at
  `619329c2c8586572ffd04558a79b3555c2ca3764`. Its allocation receipt does not
  prove Buddy World ownership or user authorization.
- The submitted PostgreSQL integration test was skipped. Before #826 can merge,
  its owner must provide a disposable `DMB_J3_PG_ADMIN_DSN` targeting
  `postgres` or `template1`, exact clean MIND #96 source, and a zero-skip
  owning-service witness that preserves an existing v2 Graph relation. Route
  tests must prove unauthorized requests do no repository/registry/database/
  MIND access. RAKE accessed no database and ran no tests.

PRIME explicitly superseded #842's earlier #826 predecessor condition: #826 is
not a behavioral or file-path predecessor of Play, and its changed paths do not
overlap the proposed Play UI consumer. Preserve #826's separate holds; do not
dispatch, revise, or merge it from this lane. Open #843 and #844 are separate
BLOCKED Build/Ingest handoff documents, not implementation leases and not
shared-conversation runtime evidence.

RAKE DUTY's Play audit remains applicable at the owning boundaries: Play must
resolve a server-verified managed World and exact selected World-owned Run
snapshot before dispatch; a failed pin must make zero provider work; same-turn
dispatch and commit must correlate to the originating turn; and concurrent
calls must serialize or return a typed conflict. This DEMO handoff does not
implement those backend runtime/storage responsibilities. It remains BLOCKED
with no write or runtime lease.

## Request and authority contract

The Play request must identify a selected managed World and exact Run locator
with an expected revision. These are locators only: the server independently
verifies World ownership and resolves the exact Run, pinned Runbook, and
current Play material before any provider work. The client never supplies a
claimed owner, native Graph identity, Runbook content, Beat/Scene prose, or
manifest contents.

Resolve the World-global active conversation through the APP-STATE/Agent
runtime contract. Do not make `client_thread_id`, a browser key, Play surface
ID, Run ID, campaign ID, or provider session ID the conversation identity. If
the existing generic request still carries `client_thread_id`, treat it only
as a client/legacy-import correlation value; it cannot select a different
canonical conversation. Use the upstream durable turn ID/idempotency contract
for retries. This handoff does not freeze a new public request shape: the DEMO
consumer must use the exact landed APP-STATE and AGENT-INTERACTION APIs, and
PRIME must pin any needed request/response changes in the later ACTIVE lease.

Every Play turn requires a server-verified managed World and selected
World-owned Run. If no Run is selected, report that current Run context is
absent and keep Play Ask unavailable until the operator selects or starts one.
A missing/rejected World or missing Run fails before pointer/provider work.
Never convert a failed or stale Run into an absent-work request, fall back to
another World/latest Runbook revision, or invent a Run from a browser pointer or
surface publication.

Before dispatch, the generic Agent resolver must establish one exact snapshot:

1. The managed World is verified server-side and owns the selected World V2 Run.
2. The Run ID exists in that World and its revision equals the requested
   expected revision.
3. The Run's exact pinned Runbook artifact, playable revision, immutable
   WorkRevision ID, and content SHA resolve under that World and match the Run.
4. The sealed World Play Run reference manifest has schema
   `dmb_play_run_reference_manifest_v2` and matches the exact Run/artifact/
   revision/body-hash binding; its structure agrees with the pinned Runbook.
5. The current Beat exists in the sealed manifest and pinned Runbook. A selected
   Scene, when present, exists and belongs to that Beat.

Reuse the strict V2 authority core in
`services/agent_play_surface_context.py`; do not use the A7
`/api/live/query` warning-enrichment wrapper as generic Run authority. Invalid
or stale primary work returns a typed rejected/unavailable result and performs
zero provider calls. Pass only bounded authored current Beat and optional Scene
through the established `AgentSurfaceContext.current_play` seam, preserving
its descriptive-data treatment, clipping, and instruction boundaries. Keep
authority IDs, hashes, manifest internals, provider internals, and full
Runbook text out of model-facing prose. This slice remains graphless: no Graph
intent, citations, or publication.

## Typed response and compatibility

Consume the exact canonical conversation/turn receipts defined by the merged
APP-STATE storage and AGENT-INTERACTION runtime contracts. Do not add fields to
the current `dmb_agent_turn_response_v1` or change Index/Plan compatibility in
this DEMO slice. If Play requires a versioned typed envelope, its fields and
compatibility behavior must be pinned by PRIME after the predecessor APIs land.

The Play result must identify the accepted server turn and the immutable work
basis actually used, so completion can attach to that historical turn even if
the selected Run changes. Preserve a bounded internal Run receipt distinct from
trace telemetry. It should represent:
- verified `world_id`, exact `run_id`, and `run_revision` or snapshot;
- pinned Runbook `artifact_id`, playable/committed revision,
  `work_revision_id`, and `content_sha256`;
- the sealed manifest's existing schema and exact Run/Runbook binding, without
  inventing a manifest revision or digest;
- exact current Beat and optional Scene IDs/titles, when resolved.

PR #848's allowlisted trace phase spans remain additive. Keep the Play work
receipt separate from trace telemetry and omit World/Run identity, source text,
and authored Play prose from timing spans.

## Conversation isolation and stale-response fences

The canonical visible transcript is one server-owned conversation per verified
World across surfaces, with a server-generated opaque `conversation_id`.
Play joins that conversation; it does not create a Play-private transcript or
a surface-specific logical continuity key. World, surface, selected work, and
tools are re-resolved for every turn. Each accepted Play turn retains its exact
surface and primary Run provenance plus supporting Runbook/artifact revision
and digest. Prior provenance explains that historical turn; it is not current
World truth, authorization, or a context snapshot.

Keep provider continuation separate from visible conversation identity. For
Play, a provider segment is scoped to the verified World, the resolved Play
surface/instance, exact Run identity and revision/snapshot, and exact pinned
Runbook identity plus committed revision/hash. A change in any part of that
scope starts a fresh provider segment. Any provider continuation key/token must
bind the full tuple or a server-generated segment ID derived from it; it cannot
be keyed only by World, conversation, surface, or browser state. If the selected
provider adapter has no resumable session today, do not add one solely for this
adoption. Default provider replay for a new segment must not silently carry
old-segment Run turns forward as though they described the new selected work.
The World-global transcript may remain visible across surfaces; the Agent
runtime owns any explicit bounded history policy and must preserve provenance
when resolving a conversational reference.

Every UI submission captures the originating durable turn and resolved Play
basis. Validate completion against that captured turn/segment, never against
whatever happens to be selected when the response returns. A late result from
Run A is persisted/displayed only as A's historical turn with its frozen
provenance; it cannot update Run B's current answer slot, context, tools, or
selected-work state. Do not silently discard or relabel it as B.

The shared AGENT-INTERACTION runtime owns provider dispatch, continuation
segmentation, concurrency, and durable completion correlation. APP-STATE owns
canonical turn persistence/idempotency/CAS. DEMO owns the Play consumer UI and
its stale-selection presentation. Do not add a Play-only pointer store or
process-local lock in the surface layer; upstream owning-boundary evidence must
prove same-scope serialization or a typed conflict.

## Owning-boundary verification

APP-STATE's durable World conversation/domain-service gate is complete at the exact merged heads #822 (`0e49c4d708d3e16c8068384549adb50e863bf64a`) and #827 (`c48abb9fa5857df90af0b086ab78294445fd252a`) with the owner-reported service/PostgreSQL, retry, and conversation-service evidence above. Do not treat the APP-STATE handoff's old ACTIVE header as proof of an unmerged implementation or as a new lease.

Before DEMO cutover, AGENT-INTERACTION must prove that the actual production turn path persists accepted user input before dispatch, resolves fresh World/surface/work/tools every turn, replays only history permitted by the current provider segment, and correlates retries/late completions to their originating durable turn. A2's harness boundary or an A3 challenger experiment alone is not that evidence.

After those predecessors merge and PRIME pins an ACTIVE DEMO lease, mounted
Play UI/API tests should prove:
- Play uses the same server active-World conversation identity/history; no
  Play-private transcript is created. When a companion surface has also cut
  over, verify both surfaces expose the same conversation/history. If no
  companion UI is cut over yet, leave that broader visual witness open rather
  than claiming cross-surface UI acceptance.
- Ask is unavailable without a selected Run; with one, request resolution and
  the returned typed receipt match the exact World/Run/Runbook snapshot.
- A surface/Run/revision/Runbook scope change starts a fresh provider segment
  and does not send prior segment turns as current work context.
- A delayed Run A completion stays on A's historical turn after selection
  changes to Run B and cannot change B's active context/tools/current-answer
  state.
- Current response/history survives the user-visible reload/reopen paths
  exposed by the upstream contract, with an honest unavailable/retry state.

No live provider, application server, product database, Graph service, or corpus
is needed for the bounded UI implementation PR. After merge, DEMO's configured-
provider witness must use the designated demo environment and exact World,
Run/revision, Runbook revision/hash, and record multi-turn World-conversation
continuity and A→B result isolation without changing runtime ownership.

Preserve inherited limitations honestly, including the existing main UI
typecheck failure at `ThreatPublicationPanel.tsx(553,77)`:
`Cannot find namespace 'JSX'`.

## Proposed paths — not an active allowlist

The former mixed Play/runtime path proposal is superseded because storage and
Agent runtime adoption belong to serial predecessor owners. This PR changes only
this DEMO handoff. There is no implementation allowlist and no runtime/database/
provider lease.

After APP-STATE storage and AGENT-INTERACTION runtime adoption merge, PRIME must
pin a separate ACTIVE DEMO cutover handoff against current main. Its write set
may include only the Play surface/API consumers and owning UI tests needed to
consume those landed contracts. Do not modify APP-STATE storage, generic Agent
runtime, provider continuation stores, shared request/response schemas, or
unrelated surfaces without an explicit transferred lease. Return to PRIME if
the exact upstream consumer contract or paths require expanding this slice.

## Activation checklist

Re-anchor remote main, open PRs, and active leases before each activation
decision. At this revision Buddy main is
`6a11200c729c1abe6d730f7794d935b966041eda`; #822 and #827 complete the APP-STATE
storage/turn-receipt step. #836, #839, #848, #851, and #852 are settled. #826
remains paused/unmergeable under its separate v2/auth/zero-skip holds; it is not
a Play predecessor. #843/#844 remain separate BLOCKED design handoffs.

Do not activate Play until AGENT-INTERACTION's production runtime adoption is
merged, verified at its owning boundary, and pinned by PRIME. PRIME then must issue
a distinct ACTIVE DEMO surface-cutover lease naming the exact current base,
consumer write set, verification, and runtime/process boundaries. This handoff
remains BLOCKED and grants no implementation, provider, database, or runtime
authority. Human acceptance of the actual connected Play conversation remains
part of the full DEMO mission.
