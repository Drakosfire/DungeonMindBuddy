# Report — CON-READY: Authoring v2 governed World commit

**Status:** HOLD — the World/campaign publication fix is implemented; C1 alias dogfood is blocked by a missing durable World target.

## Exact implementation identity

- Dispatch base: `main@28b1fdf494ffc6e53b99b311b2f4d5256fd5e8a2`.
- Implementation branch: `con-ready/authoring-v2-governed-world-commit-v1`.
- Implementation commits: `3a254140` — `CON-READY: publish staged recap memory to World`; `5f079c4d` — `CON-READY: target governed World for recap writes`.
- PR topology: serial; one V2-2 implementation PR is authorized.
- PR: #742 OPEN — `CON-READY: publish staged recap memory to World`; opened from the implementation handback at `a441dc6d`.
- Review Cycle 1: **HOLD**, review `5267550374`, against head `eb5e3298202999759edb2cf5d5b5fd0c307cd0d1`.
- Current fix head: `5f079c4d`.

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
4. Confirm failed closed with DungeonMind’s `orphan_accepted_assertion`: the selected Ephanna target is visible in the recap/extracted projection but is not present as a durable object in the current governed `eldyrwild` revision. The World head remained unchanged.

This separates two states that the old chrome conflated:

```text
ingestion/read projection ready  = recap and extracted graph are available
publication ready                = the selected target exists in governed World truth
```

No genesis or World creation was run for `longmont-c1`. The current UI explains the actionable condition: create or publish the object into the governed World first, then add the alias. This is the smallest successor/bootstrap decision; it is not a reason to create a campaign-level World.

## Dogfood notes and remaining boundary

- The final Author Node review now says `Local review complete`, then presents `Review & publish` and `Confirm publish` as separate actions.
- The recap record identity is the durable handoff between the recap surface and the server source resolver; no browser-supplied filesystem path is used for authority.
- Same-label Create new remains a distinct identity operation. No merge, delete, reconciliation, or automatic dedupe was added.
- Review Cycle 1’s original blocker was corrected: the authoring surface now preserves setting World identity instead of using `worldId = campaignId`, and the durable witness no longer models the campaign as its World.
- Repository steward preflight still reports stale overlaps from older checked-in handoffs (including the already-merged V2-1 lane) and a missing runtime/state-ownership declaration on this handoff. Those are authority/process cleanup items outside this implementation lease and were not changed here.

V2-3 (derive evaluation gold from committed human adjudication) remains unimplemented.
