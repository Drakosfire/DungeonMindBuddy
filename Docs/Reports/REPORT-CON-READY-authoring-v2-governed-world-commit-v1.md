# Report — CON-READY: Authoring v2 governed World commit

**Status:** Implementation complete; live Witness A remains an operator dogfood gate before merge.

## Exact implementation identity

- Dispatch base: `main@28b1fdf494ffc6e53b99b311b2f4d5256fd5e8a2`.
- Implementation branch: `con-ready/authoring-v2-governed-world-commit-v1`.
- Implementation commit: `3a254140` — `CON-READY: publish staged recap memory to World`.
- PR topology: serial; one V2-2 implementation PR is authorized.
- PR: authorized title `CON-READY: publish staged recap memory to World`; PR transport is opened after this handback.
- Review cycles: none yet.

## What shipped

The published recap Author Node now keeps staging local until the operator reaches the final review step, then exposes the governed transition:

```text
local draft → Review & publish → inspect prepared World change → Confirm publish → refresh same recap scope
```

The existing exact-run `sourceRunId` path remains compatible. Published recap authoring now carries the selected server-owned `recapArtifactId` through the existing prepare/confirm seam. Successful commits return committed proposal IDs and expose created durable node IDs in the operator-visible write details.

The refresh callback reloads the same campaign/session projection. Refresh failure remains separate from publication success, so a durable write is not reported as failed merely because the read-back refresh needs retrying.

## Source authority

- `sourceRunId XOR recapArtifactId` is enforced for expressible writes.
- `recapArtifactId` resolves the server-owned `RecapArtifactRecord`; browser path/digest fields are not authority inputs.
- Campaign/session equality, safe server-owned path resolution, registered digest equality, deterministic recap SourceArtifact creation, and digest-derived revision binding all fail closed.
- Prepare binds selector, admitted source pair, proposal digest, contribution digest, and expected World parent into the signed confirmation intent.
- Confirm re-resolves/re-proves the same source selector and admitted pair before checking the parent and publishing.

The disposable normalized recap witness proved that the record digest and deterministic recap SourceArtifact digest agree when the source bytes satisfy the current normalization contract. A live production record was not mutated or independently audited during implementation; any real digest mismatch remains a source failure rather than a weakened provenance path.

## Evidence produced

| Boundary | Evidence | Result |
|---|---|---|
| Prepare/commit/routes + recap write witness | `uv run pytest tests/test_graph_object_authoring_prepare.py tests/test_graph_object_authoring_commit.py tests/test_graph_object_authoring_routes.py tests/test_graph_object_authoring_published_recap_write.py -q` | **50 passed**, 11 pre-existing Pydantic warnings |
| Published recap UI and projection refresh | Focused Vitest command from HANDOFF §7 | **79 passed** |
| UI types | `pnpm --dir apps/live-control-ui typecheck` | **passed** |
| Production bundle | `pnpm --dir apps/live-control-ui build` | **passed**; existing chunk-size warning only |
| Python syntax | `uv run python -m compileall -q` on changed Python/test files | **passed** |
| Diff hygiene | `git diff --check` | **passed** |

The disposable end-to-end witness publishes two deliberately same-label objects through a durable revision-backed authority seam, reads both IDs back from the published revision, proves the IDs differ, and passes both bindings to the recap mention linker. The linker returns no arbitrary mention winner and emits `ambiguous_mention_surface`.

The required live Witness A is intentionally pending: it requires the operator to select a genuinely absent campaign fact and confirm a real World write. No production-world object was seeded by the implementation agent.

## Dogfood notes and remaining boundary

- The final Author Node review now says `Local review complete`, then presents `Review & publish` and `Confirm publish` as separate actions.
- The recap record identity is the durable handoff between the recap surface and the server source resolver; no browser-supplied filesystem path is used for authority.
- Same-label Create new remains a distinct identity operation. No merge, delete, reconciliation, or automatic dedupe was added.
- Repository steward preflight still reports stale overlaps from older checked-in handoffs (including the already-merged V2-1 lane) and a missing runtime/state-ownership declaration on this handoff. Those are authority/process cleanup items outside this implementation lease and were not changed here.

V2-3 (derive evaluation gold from committed human adjudication) remains unimplemented.
