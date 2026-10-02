# HANDOFF — DEMO: bind a managed World to an existing native Graph

**Status:** ACTIVE — PRIME accepted the exact 11-path allowlist and serial
topology at design head `80ab7490878b297eba14602130fe867a5d3e47c2`. The registry
lease has transferred from paused PR #826 to this implementation lane.

**Steward:** DEMO

**Design base:** Buddy `origin/main@1ccfe7f2af69684e1d02276f66b875ef336b82a0`.

**Consumed contract:** MIND `origin/main@619329c2c8586572ffd04558a79b3555c2ca3764`.

**Implementation PR title:** `DEMO: bind managed Worlds to existing native Graphs`

## 1. One capability

The local operator can bind an existing Buddy managed World to an existing
DungeonMind V2 Graph and inspect whether that binding is active. The stored
binding is an explicit, versioned Buddy authority relation. The demo mapping is
from a distinct managed World ID to native Graph `world_id=eldyrwild`.

This slice establishes the mapping only. It does not add Graph retrieval to the
Plan Agent, send graph data to a provider, create or provision a KnowledgeSpace,
change native Graph contents, or import a recap. The saved-Plan query remains a
separate blocked successor.

## 2. Identity and ownership

- Buddy `WorldContainerRecord.world_id` is the managed World identity. MIND V2
  Graph `world_id` is a separate native identity. VNext Knowledge `space_id` is
  a third identity. Never derive one from another, a display name, campaign ID,
  or graph contents.
- Buddy owns the managed-World-to-native-Graph relation and its activation,
  deactivation, version, and public status. MIND owns whether a native world,
  recognized genesis receipt, and current head exist.
- Use a distinct `native_graph_binding` value on the managed World record. Do
  not put this relation in `world_space_binding.py`, overload `space_id`, or add
  a second parallel binding registry.
- The binding value is typed and versioned. Its stored form contains:

  ```text
  schema_version = dmb_managed_world_native_graph_binding_v1
  provider = dungeonmind_v2
  native_world_id = opaque MIND identity
  status = active | inactive
  binding_version = positive monotonic integer
  validated_at = UTC timestamp
  validated_head_revision_id = opaque audit observation
  ```

  `validated_head_revision_id` records the head observed when the relation was
  activated; it is not a query pin. Each future Graph turn resolves its own
  current head.
- Legacy registry v1 GET/list is read-only: interpret records as unbound in
  memory and do not rewrite the file as a side effect of reading. Persist the v2
  schema only as part of an authorized, locked compare-and-swap mutation, while
  preserving existing World IDs, names, and source roots.
- Initial activation is persisted only after a read-only MIND identity/head
  validation succeeds. Re-activation validates again. Deactivation is a
  Buddy-local transition that remains available while MIND is down; it keeps
  the native identity and validation observation, changes status to inactive,
  and increments the binding version.
- Rebinding to a different native ID requires an explicit inactive state and
  expected-version compare-and-swap. Check the at-most-one-active-Buddy-World
  claim for a native Graph inside that same mutation lock before persistence,
  until a separately reviewed sharing policy exists.
- Perform MIND validation outside the registry file lock, then reacquire the
  lock and compare the exact registry token and expected binding version before
  writing. A concurrent World/binding change fails with a conflict; it must not
  persist a stale validation as ACTIVE.

## 3. Local operator boundary

Use the merged #835 guard, `enforce_native_graph_gm`, before calling `repo_root`,
reading or mutating the registry, or contacting MIND on the new binding and
deactivation operations. Its supported claim is limited to a configured
local-operator bearer on a loopback request; Buddy grants that local operator a
fixed local GM capability. It does not establish a named user, remote/LAN
access, campaign membership, or tabletop identity. MIND `Admissibility.GM`
remains an independent Graph visibility filter, not an authentication proof.
The existing WorldContainer list/create routes remain on their current auth
boundary and change only to use the redacted response DTO; this slice does not
add a UI-wide auth migration.

Use the existing WorldContainer list GET as the binding inspection surface. Its
per-record DTO reports `native_graph_binding.status` and
`native_graph_binding.binding_version`; an unbound World reports `unbound` and
version `0`. It returns no native ID, validation head, receipt, or DSN. This GET
performs only a read-only registry lookup: it does not call MIND or change
registry bytes/token, including when it reads a legacy v1 registry.

Expose explicit local configuration operations, for example:

- `PUT /api/live/world-containers/{managed_world_id}/native-graph-binding`
  accepts `native_world_id` and the expected binding version. This is the only
  operation in this slice where a local operator may choose the native ID. A
  never-bound record requires expected version `0`; later transitions require
  the exact stored version.
- `POST /api/live/world-containers/{managed_world_id}/native-graph-binding/deactivate`
  accepts the expected binding version and performs no MIND call.

Normal Agent/query request bodies must not choose the native ID, scope, GM role,
or binding version. The later query slice resolves all of those from trusted
Buddy state and the stored binding.

Missing/invalid auth configuration fails closed with 503, missing or invalid
bearer with 401, and non-loopback requests with 403. Denial occurs before any
registry lookup or MIND call on the new bind/deactivate operations. Missing,
unavailable, contradictory, wrong-world, or headless MIND authority never
produces an active binding.

## 4. Public response shape

Do not serialize the storage `WorldContainerRecord` directly as an HTTP
response. List, create, bind, and deactivate operations use a redacted public
DTO. It may report binding `status` and `binding_version`; it must omit
`native_world_id`, `validated_head_revision_id`, MIND receipt details, and
database configuration. Add response tests that assert those values and keys
do not escape. The later #826 KnowledgeSpace status must be composed into this
public DTO without exposing its private identifiers or receipt either.

## 5. Existing MIND read path

Buddy `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`
already exposes `direct_services_from_config(native_world_id)`. Its
`DirectAuthorityBinding` checks recognized adoption/reviewed-initialization
identity and observes the authoritative current head. Use this read-only path to
validate activation and capture the audit head. Require the returned binding's
`world_id` to exactly equal the requested native ID and require a non-empty head.
Then read-only-load that exact head revision through the returned MIND
repository with `services.bundle.world_graph.get_revision(native_world_id,
head_revision_id)` and verify the revision's world ID and revision ID before
persisting ACTIVE. No MIND code or new MIND mapping/API is authorized by this
handoff. If the existing adapter/repository cannot provide that exact revision
read, stop and return the missing contract to PRIME before expanding the lease.

The local registry is `out/registries/world_containers.json`; code tests use a
temporary root and must not touch the configured demo registry. No real
`eldyrwild` binding action is allowed until PRIME confirms the exact target
managed World and runtime owner. This slice has no provider calls, server
starts, shared ports, MIND writes, or real Graph mutation. A live binding action
is a later read-only MIND validation plus a Buddy registry write and must be
coordinated with PRIME and the designated runtime owner.

## 6. Verification and acceptance

At the owning Buddy registry/route boundary, prove:

- v1 list reads load records as unbound without changing registry bytes/token;
  an authorized locked CAS mutation writes v2 while preserving existing World
  IDs, names, and source roots;
- a validated initial bind persists active version 1 and survives reload;
- invalid/missing/unavailable native identity or head never persists active;
- deactivation preserves the relation and works with MIND unavailable;
- reactivation and rebinding require exact expected versions and revalidate;
- concurrent changes fail closed, and duplicate active claims for one native
  Graph are rejected by a uniqueness check inside the locked mutation;
- missing configuration, absent/invalid bearer, and non-loopback bind/deactivate
  requests are rejected before registry or MIND access, with denial tests
  proving neither dependency is called;
- an authorized operation validates the exact native Graph identity and head;
- list GET leaves a legacy v1 registry byte-for-byte unchanged and makes no MIND
  call;
- public list/create/bind/deactivate responses expose the managed World fields
  plus native binding status/version only and never expose native IDs,
  validation head IDs, MIND receipts, or DSNs.

Suggested focused checks:

```bash
uv run pytest tests/test_world_container_registry.py tests/test_world_graph_binding.py tests/test_live_world_containers.py tests/test_demo_world_selection_integration.py
ruff check apps/live_control_server/services/world_container_registry.py apps/live_control_server/services/world_graph_binding.py apps/live_control_server/routes/world_containers.py tests/test_world_container_registry.py tests/test_world_graph_binding.py tests/test_live_world_containers.py tests/test_demo_world_selection_integration.py
git diff --check
```

Use deterministic temporary registries and an injected read-only MIND service
for local route tests. Do not target the configured demo registry or a shared
database. Before any separately authorized live `eldyrwild` bind, record its
exact non-empty current MIND head through the read-only adapter and confirm the
Buddy target World ID; never initialize, write, or advance that Graph.

## 7. Exclusive write lease

PRIME accepted the following exact paths as the exclusive implementation lease
at design head `80ab7490878b297eba14602130fe867a5d3e47c2`:

- `apps/live_control_server/services/world_container_registry.py`
- `apps/live_control_server/services/world_graph_binding.py` (new)
- `apps/live_control_server/routes/world_containers.py`
- `tests/test_world_container_registry.py`
- `tests/test_world_graph_binding.py` (new)
- `tests/test_live_world_containers.py`
- `tests/test_demo_world_selection_integration.py`
- `Docs/Plans/HANDOFF-DEMO-existing-graph-binding.md`
- `Docs/Plans/HANDOFF-DEMO-agent-graph-auth.md`
- `Docs/Plans/HANDOFF-DEMO-session29-elderwyld-graph.md`
- `Docs/Roadmaps/ROADMAP-demo.md`

Do not edit the leased #826 branch or any MIND path. Its PR remains OPEN and
paused at `4fa28e586783f0e63edb85fa664afa53521367f6`; preserve its worktree and
head. PRIME's explicit ownership ruling transferred the shared managed-World
registry path to this successor when it accepted this exact allowlist.

## 8. Topology and successors

**Topology:** serial. PRIME activated this as the sole implementation lane from
Buddy main `1ccfe7f2af69684e1d02276f66b875ef336b82a0`; open its one PR when the
slice is implemented and verified. PR #826 is a preserved paused branch, not a
concurrent writer or merge candidate. The graph-binding PR merges first. Then
rebase or redesign #826 against the new registry contract, preserve its
KnowledgeSpace binding as a distinct value, and return its exact tests and PR
state to PRIME before any further implementation or merge on that branch.

The saved-Plan query remains a separate BLOCKED successor. It needs fresh Buddy
and MIND refs, a completed route/access audit, the read-only populated
`eldyrwild` witness, and its own disposable native fixture for R1-to-R2
concurrent publication and restart re-resolution. Its contract must pin every
search, hop, evidence lookup, and source-anchor read to one resolved head,
preserve MIND citation identities, keep C2 narrative focus separate from native
scope, and disclose the configured provider destination plus exact excerpts
sent. No query/UI/provider payload path is leased here.

## 9. Authority settlement

Buddy #835 merged at `1ccfe7f2af69684e1d02276f66b875ef336b82a0` from corrected
code head `3a1a12b05be8e00581dce45da2b1b5efa53f123a`. Its claim is limited to
the guarded local-operator Graph read responses named in
`HANDOFF-DEMO-agent-graph-auth.md`. ThreatDraft, Graph Review, and remaining
Threat publication internal Graph reads still require a separate route audit;
they are not declared secured by #835. The full saved-Plan graph query, Session
28 recap admission, and J1-J6 acceptance remain incomplete.
