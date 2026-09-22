# Report — CON-READY: Authoring v2 governed World commit

**Status:** HOLD — the World/campaign publication fix is implemented; the authoring “wow moment” is blocked by missing governed PC identities and a recap-vs-union projection boundary.

## Exact implementation identity

- Dispatch base: `main@28b1fdf494ffc6e53b99b311b2f4d5256fd5e8a2`.
- Implementation branch: `con-ready/authoring-v2-governed-world-commit-v1`.
- Implementation commits: `3a254140` — `CON-READY: publish staged recap memory to World`; `5f079c4d` — `CON-READY: target governed World for recap writes`.
- PR topology: serial; one V2-2 implementation PR is authorized.
- PR: #742 OPEN — `CON-READY: publish staged recap memory to World`; opened from the implementation handback at `a441dc6d`.
- Review Cycle 1: **HOLD**, review `5267550374`, against head `eb5e3298202999759edb2cf5d5b5fd0c307cd0d1`.
- Current fix head: `5f079c4d`.

## Resume re-anchor after PR #744

- Current `main`: `8000fb607f418242e816c08b819d92fa764eac70` (PR #744 merged).
- PR #742 remains open and is rebased onto that exact base.
- The merged #744 contract is preserved: recap/session state and the governed
  World lens are independent; resolver candidates can remain visible without
  being bindable; existing-target eligibility uses the exact governed World
  projection and the canonical target ID.
- The six-PC durable identity reconciliation is still pending in live
  `eldyrwild`, so `pc:ephanna` remains correctly unavailable. No live World
  mutation was performed during this re-anchor.

## What shipped

The published recap Author Node now keeps staging local until the operator reaches the final review step, then exposes the governed transition:

```text
local draft → Review & publish → inspect prepared World change → Confirm publish → refresh same recap scope
```

The existing exact-run `sourceRunId` path remains compatible. Published recap authoring now carries the selected server-owned `recapArtifactId` through the existing prepare/confirm seam. Successful commits return committed proposal IDs and expose created durable node IDs in the operator-visible write details.

The published recap surface now carries `payload.snapshot.worldId` through prepare and confirm. A Longmont C1 write therefore targets `eldyrwild` with `longmont-c1` as campaign scope; it no longer reconstructs a nonexistent World from the campaign ID.

The refresh callback reloads the same campaign/session projection. Refresh failure remains separate from publication success, so a durable write is not reported as failed merely because the read-back refresh needs retrying.

## Source authority

- `sourceRunId XOR recapArtifactId` is enforced for expressible writes.
- `recapArtifactId` resolves the server-owned `RecapArtifactRecord`; browser path/digest fields are not authority inputs.
- Campaign/session equality, safe server-owned path resolution, registered digest equality, deterministic recap SourceArtifact creation, and digest-derived revision binding all fail closed.
- Prepare binds selector, admitted source pair, proposal digest, contribution digest, and expected World parent into the signed confirmation intent.
- Confirm re-resolves/re-proves the same source selector and admitted pair before checking the parent and publishing.
- Legacy recap SourceArtifact records may omit `world_id`; the server-resolved authored World is bound onto the in-memory source identity before DungeonMind admission.

The disposable normalized recap witness proved that the record digest and deterministic recap SourceArtifact digest agree when the source bytes satisfy the current normalization contract. A live production record was not mutated or independently audited during implementation; any real digest mismatch remains a source failure rather than a weakened provenance path.

## Evidence produced

| Boundary | Evidence | Result |
|---|---|---|
| Prepare/commit/routes + recap write witness | `uv run pytest tests/test_graph_object_authoring_prepare.py tests/test_graph_object_authoring_commit.py tests/test_graph_object_authoring_routes.py tests/test_graph_object_authoring_published_recap_write.py -q` | **50 passed, 1 skipped**, 11 pre-existing Pydantic warnings; the skipped test is the opt-in real PostgreSQL witness without `DMB_CUTOVER_TEST_DATABASE_URL` |
| Published recap UI and projection refresh | Focused Vitest command from HANDOFF §7 | **80 passed** |
| UI types | `pnpm --dir apps/live-control-ui typecheck` | **passed** |
| Production bundle | `pnpm --dir apps/live-control-ui build` | **passed**; existing chunk-size warning only |
| Python syntax | `uv run python -m compileall -q` on changed Python/test files | **passed** |
| Diff hygiene | `git diff --check` | **passed** |

The disposable end-to-end witness publishes two deliberately same-label objects through a durable revision-backed authority seam, reads both IDs back from the published revision, proves the IDs differ, and passes both bindings to the recap mention linker. The linker returns no arbitrary mention winner and emits `ambiguous_mention_surface`. The real PostgreSQL witness is now present and explicitly models `World = eldyrwild` with `campaign = longmont-c1`, but is opt-in skipped in this environment.

## Live C1 dogfood result

The local API and UI were restarted from this checkout and the existing staged C1S1 draft was retried through the actual Author Node:

1. The recap projection returned `worldId = eldyrwild`, `campaignId = longmont-c1`, and current head `rev:e570042d33a30d07e053c578dedbc804`.
2. Prepare succeeded against that exact World and showed the same parent in the UI. No World revision advanced during prepare.
3. The unrelated Karsemine and merchant-guards local drafts were removed from the local-only staging list so the selected operation was only `Ephanna the Kenku Warlock → Ephanna (pc)`.
4. Confirm failed closed with DungeonMind’s `orphan_accepted_assertion`: the selected `pc:ephanna` target is visible through the Party / PC resolver but is not present as a durable object in the current governed `eldyrwild` revision. A separate durable `node:ephanna` object exists, and the World head remained unchanged.

## Targeted #742 continuity investigation

The follow-up identity investigation was stopped at the handoff’s Case B gate.
The exact live authority observation was:

```text
world                 = eldyrwild
campaign              = longmont-c1
session               = session-1
head                  = rev:e570042d33a30d07e053c578dedbc804
proposal              = link_existing alias
selected text         = Ephanna the Kenku Warlock
candidate source      = Party / PCs (party_pc)
candidate ID          = pc:ephanna
existingObjectRef     = pc:ephanna / Ephanna
```

The resolver returned one high-confidence Party / PC candidate, `pc:ephanna`.
The exact campaign and world recap projections did not expose a canonical
Ephanna node. A direct read of the immutable head payload did expose
`node:ephanna` (`dnd5e:player_character`, `campaign_scope=longmont-c1`), but
not `pc:ephanna` or `pc_ephanna`.

The ancestry query covered 45 revisions, from head
`rev:e570042d33a30d07e053c578dedbc804` back to root
`rev:e25957737702d7a08809f546ef1d64b6`. Every revision contains
`node:ephanna`; no revision contains `pc:ephanna`. The same identity shape is
systemic for the C1 party roster at both root and head:

```text
node:baergrom  node:bonogo  node:caelynn
node:ephanna   node:karsemine  node:stafl
```

The approved historical adoption bundle still contains accepted C1 assertions
against `pc:ephanna`, including the Party Registry Ephanna attribute and
relationships. That bundle is not the current live revision ancestry, so it is
evidence of lineage/identity drift rather than a safe source for rewriting the
live target.

The failed publication envelope was:

```text
API code  = governed_write_inexpressible
message   = DungeonMind v6 materialization rejected the Threat contribution: orphan_accepted_assertion
DungeonMind materialization reason = orphan_accepted_assertion
```

The live head remained unchanged. Because the proposal uses the intended
canonical `pc:ephanna` while the live lineage lacks that ID, this is the
handoff’s Case B continuity failure. No `pc:ephanna` → `node:ephanna` heuristic
binding, replacement object, World initialization, ingestion replay, or
alias publication was attempted.

The smallest next repair is outside ordinary #742: reconcile the accepted
Ephanna/party identity lineage (and the corresponding projection contract)
against the live `eldyrwild` authority, then re-anchor before reopening the
existing-object witness. The current PR cannot truthfully claim the Ephanna
existing-object witness or merge readiness.

## Designing-agent escalation — live dogfood blocker

The later live read was re-anchored against the current authority rather than the
older `rev:e570042d33a30d07e053c578dedbc804` observation. The current read-only
head is:

```text
World          = eldyrwild
head           = rev:bd1d6a17747566fc8955b3c17f9cf680
scope          = C1+C2 plain union
node_count     = 1041
relationships  = 559
evidence       = 419
truncated      = false
```

The dogfood contradiction is now precise:

```text
Party registries:
  C1/S1   → ephanna → resolved PC hub
  C2/S23  → ephanna → resolved PC hub

Governed World union:
  zero nodes with kind/role pc
  no pc:ephanna

C1/S1 recap projection:
  Ephanna-bearing descriptive objects only
  no canonical Ephanna PC
```

This means “loaded” currently means that the World projection endpoint returned a
complete readable projection. It does not mean that party-registry identities
have been materialized into governed World truth. The six-PC atomic reconciliation
handoff was never applied to this live authority. The recent Create-new attempt
therefore did not produce the missing durable `pc:ephanna` identity on the current
read-back; no further duplicate Ephanna should be created as a workaround.

The same read explains the Questionable Company confusion. The exact durable node
`node_faction_questionable_company` is present in the C1+C2 union with
`campaign_scope=longmont-c2`, but it is absent from the C1/S1 campaign projection.
That is correct for the narrower projection, but it is not currently usable from
the C1/S1 authoring surface even when the application chrome says C1+C2 is ready.

### Historical pre-#744 observations

The following earlier diagnosis is retained as historical evidence only. It is
superseded by merged #744 and must not be used as the current implementation
description:

- Author Node existing-target admission no longer uses recap-local `nodeViews`
  as its governed authority. Current code derives eligibility from the active
  governed World-lens projection and the canonical resolver target ID.
- Ingest recap/session selection is now independent from the World Graph lens.
  A recap session may be loaded while the World lens remains a separate union or
  focused projection.

The remaining C1/C2 behavior must therefore be diagnosed against the active
World lens and its exact projection, not against the retired recap-local or
shared-session explanation. The live identity gap remains independently real:
`pc:ephanna` is absent from governed World truth even though the resolver can
find the Party / PCs candidate.

### Design decision requested

Treat this as a blocker to the first convincing authoring loop, not as a copy or
resolver polish issue. The next design/repair slice should establish all of the
following before #742 can claim the existing-object witness:

- apply and prove the six-PC atomic reconciliation against the current
  `eldyrwild` head, including `node:ephanna → pc:ephanna`;
- distinguish `World projection loaded` from `party identities reconciled` in
  readiness/status copy;
- keep the loaded recap payload and its server-owned `RecapArtifactRecord`
  transactionally paired until a replacement `Load` succeeds;
- prove the intended witness end to end:

```text
C1/S1 highlight “Ephanna”
→ resolver offers canonical pc:ephanna as a governed PC
→ stage alias/reference
→ Review & publish
→ one governed child revision
→ refresh C1/S1
→ authored result is readable through the same pc:ephanna identity
```

Until that witness passes, the product cannot deliver the moment the workflow is
designed to create: the GM highlights a known character, receives a trustworthy
identity suggestion, publishes the relationship, and immediately sees durable
World memory reflect the decision. No genesis, campaign-level World, resolver
shim, raw SQL repair, or additional duplicate object is authorized by this
finding.

This separates two states that the old chrome conflated:

```text
ingestion/read projection ready  = recap and extracted graph are available
publication ready                = the selected target exists in governed World truth
```

No genesis or World creation was run for `longmont-c1`. The current UI explains the actionable condition: create or publish the object into the governed World first, then add the alias. This is the smallest successor/bootstrap decision; it is not a reason to create a campaign-level World.

## Designing-agent escalation — current #742 review and identity-reconciliation blocker

This section records the current implementation review and the handback to the
designing agent. It is not a new formal GitHub review-cycle count.

### Exact review anchor

```text
PR                         = #742
implementation head        = 6272097e08e83f12e549a6588cdee4460e956a45
base                        = main@8000fb607f418242e816c08b819d92fa764eac70
branch                      = con-ready/authoring-v2-governed-world-commit-v1
committed changed paths    = 22
```

The committed #742 surface is re-anchored onto merged #744 behavior. Focused
verification at the current head is green: the six-file UI suite reports **102
passed**, UI typecheck and production build pass, and `git diff --check` passes.
The previously recorded focused backend evidence remains green with the
opt-in real-PostgreSQL authority witness skipped. No live World mutation was
performed by this review.

### Review Cycle 3 finding

Formal Review Cycle 3 was posted as `5273340663` against predecessor head
`863b13f68af08cc35d18f7cd0de675ba243a240c` with a **HOLD** verdict. The #744
rebase, governed-target eligibility, and
relationship-picker canonical-ID seam are sound. The concrete new blocker was
the explicit Load state boundary: changing the draft Campaign refreshed the
artifact catalog while leaving the loaded recap visible, so the old
`selectedRecapRecord` lookup could become `null` before a replacement Load.
That stripped the visible recap of its `recapArtifactId`, source path, digest,
and governed write authority.

The repair keeps payload, loaded scope, and `RecapArtifactRecord` in one loaded
state bundle and replaces that bundle only after a projection Load succeeds.
Failed replacement loads also retain the prior bundle rather than stripping
the visible recap's source authority. A focused regression asserts that
changing the draft Campaign leaves the loaded C2 source path and digest intact.
The repair is committed at `6272097e08e83f12e549a6588cdee4460e956a45`.

### Review disposition

The #742 implementation is structurally ready to continue its governed publish
flow, but it remains **HOLD / not merge-ready** for the live existing-object
witness. The UI is correctly refusing to bind `pc:ephanna` while that durable
ID is absent. The misleading “No confident duplicate was found” copy is a
secondary UX defect: the resolver did find a high-confidence exact `pc:ephanna`
candidate, but the governed-target eligibility gate excludes it until the
current World projection contains that ID.

The primary blocker is therefore the missing six-PC identity reconciliation,
not recap ingestion, the #742 prepare/confirm path, or the matcher itself.

### What is stopping the reconciliation

DungeonMind PR #70 delivered the atomic reconciliation capability, but the
identity-specific recovery operation has not been implemented or dispatched.
The inspected recovery checkout
`/tmp/dungeonmind-pc-identity-reconciliation` is still at `a53ac4c` and contains
no `eldyrwild_pc_identity_reconciliation.py`, operator apply script, or
six-PC reconciliation implementation. Consequently there is no governed
operation available to invoke against live `eldyrwild` yet.

The remaining gates are:

1. **DungeonMind ownership:** the mutation belongs in DungeonMind’s recovery
   lane. Buddy must not translate `pc:*` to `node:*`, create a duplicate PC,
   use raw SQL, or add a resolver exception.
2. **Fresh parent re-anchor:** the identity handoff records
   `rev:e570042d33a30d07e053c578dedbc804`, while the later Buddy report recorded
   `rev:bd1d6a17747566fc8955b3c17f9cf680`. Neither should be used blindly. The
   recovery lane must read the actual current `eldyrwild` head and materialize
   the six mappings against that exact parent.
3. **Atomic operator action:** after preflight, one expected-parent CAS
   operation must reconcile all six PCs or make no World change. It must produce
   six durable reconciliation decisions, a child revision, replay evidence, and
   an exact-retry no-op. No partial six-PC migration is acceptable.
4. **Downstream witness:** only after `pc:ephanna` is current in the governed
   projection can #742 prove `highlight → canonical existing Ephanna → alias /
   reference → prepare → confirm → refresh → durable read-back`.

An earlier operator authorization was given in the conversation, but the live
apply did not occur; the recovery work stopped before mutation and the handoff
still correctly shows the explicit apply gate as pending. This is an unfinished
recovery dispatch, not a DungeonMind rejection of the operation.

### Required handback to the designing agent

The next authorized sequence is:

```text
1. Re-anchor the DungeonMind recovery handoff on current main and current
   Eldyrwild head.
2. Implement/dispatch the bounded exact-six recovery operation using PR #70's
   atomic publisher.
3. Re-run read-only preflight and present the exact parent plus six mappings.
4. At the operator gate, publish one atomic child or no-op.
5. Reload through fresh connections and prove canonical IDs, relationship and
   evidence preservation, persisted decisions, replay equality, and retry
   idempotency.
6. Re-anchor #742 and re-run the Ephanna existing-object witness.
7. Complete the separate Create-new durable-node witness.
```

Until those steps pass, #742 must remain open and no V2-3 work should begin.

## Dogfood notes and remaining boundary

- The final Author Node review now says `Local review complete`, then presents `Review & publish` and `Confirm publish` as separate actions.
- The recap record identity is the durable handoff between the recap surface and the server source resolver; no browser-supplied filesystem path is used for authority.
- Same-label Create new remains a distinct identity operation. No merge, delete, reconciliation, or automatic dedupe was added.
- Review Cycle 1’s original blocker was corrected: the authoring surface now preserves setting World identity instead of using `worldId = campaignId`, and the durable witness no longer models the campaign as its World.
- Repository steward preflight still reports stale overlaps from older checked-in handoffs (including the already-merged V2-1 lane) and a missing runtime/state-ownership declaration on this handoff. Those are authority/process cleanup items outside this implementation lease and were not changed here.

V2-3 (derive evaluation gold from committed human adjudication) remains unimplemented.
