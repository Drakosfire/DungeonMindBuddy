# DEMO-J3 — managed World to KnowledgeSpace binding

**Status:** BLOCKED — concrete redesign; no implementation or runtime lease  
**Owner:** DEMO steward  
**Re-anchor:** Buddy `main@67b0df1a478f50ff324b919d13f299c276b89198` (PR #878 merge), checked 2026-10-02 through the GitHub repository connector. Shell `git fetch origin main` was unavailable because this environment could not resolve GitHub.  
**MIND contract:** DungeonMind `619329c2c8586572ffd04558a79b3555c2ca3764` (PR #96, current MIND main at re-anchor).  
**Topology after activation:** serial; one implementation PR for this capability. Keep the paused Rules #763 dependency work behind this slice while it owns `pyproject.toml` / `uv.lock`; re-anchor it after the dependency decision lands.  
**Predecessor:** Buddy PR #826 remains paused and is not a merge, cherry-pick, or rebase candidate. It must not be treated as active authority.

## User capability and boundary

Provision one empty MIND VNext KnowledgeSpace for an already verified managed Buddy World. Persist the relationship on that World and expose only its safe operational status. MIND owns minting the Space ID and atomically creating its empty genesis. Buddy owns the managed-World-to-Space relationship.

This slice does not bind or modify an existing native Graph; import or migrate Elderwyld/C1/C2 data; admit source material; add retrieval or citations; or claim J3/full-demo acceptance. A managed `world_id`, native Graph `world_id`, and VNext `space_id` remain distinct identities.

## Why #826 is held

The old #826 implementation was written against a V1-only World record with flat `space_*` fields. Current Buddy main uses strict V2 registry records and already stores a typed `native_graph_binding`; applying the old model to a V2 record can fail validation and lose the independent Graph relationship. Rebuild the implementation on the current V2 record shape.

Buddy main currently pins DungeonMind #85 at `7c69e447f6d4acc963ac09c6fb9cb48cc1c5b9cc`, which does not export MIND #96's `create_empty_space` provisioning API. MIND #96 is the current MIND main and defines the required MIND-minted ID and `KnowledgeSpaceProvisioningReceipt`. The #96 dependency upgrade is intentional. Prove Buddy's existing Graph adapters and binding still work with that pin before accepting it.

## Proposed data and lifecycle

Add a typed, versioned `knowledge_space_binding` sibling to `WorldContainerRecord.native_graph_binding`. Do not overload or replace the Graph field, create a parallel registry, or add flat top-level Space fields.

The private binding must preserve enough immutable intent to recover the exact same MIND operation after a process restart or lost response:

- binding schema/version and its own monotonic `binding_version`;
- status: `pending` or `active` (absence means unbound);
- a server-generated, stable `allocation_id` created before the MIND call;
- the exact domain-contract and semantic-profile inputs, or immutable references plus content digests that resolve to those exact inputs;
- the canonical MIND request digest for those inputs;
- after success, the MIND-minted `space_id` and the exact durable provisioning/publication receipt.

Do not accept a client-provided Space ID, allocation ID, domain/profile choice, or arbitrary receipt. Do not use the managed World ID as MIND's allocation key.

Lifecycle is `unbound → pending → active`. A failed or lost MIND response leaves the same pending allocation recoverable. MIND #96 binds an allocation key to semantic request identity; retrying the same key with changed domain/profile semantics can conflict. Therefore every retry must reuse the persisted immutable request snapshot and verify the returned `request_sha256`, allocation ID, Space ID, and publication receipt against it. A mismatched receipt stays pending and fails closed; never allocate a second Space as a workaround.

There is no local deactivate, transfer, delete, or rebind operation in this slice. MIND has no corresponding Space deletion/transfer contract, so local unbinding could orphan durable authority. Keep an active Space reserved to its original World. Any later lifecycle change needs a separate accepted contract.

## Mutation and race rules

1. Under the existing registry mutation lock, load the current registry, verify the managed World and its source root, and persist a unique pending allocation with the frozen semantic request. Validate a newly constructed full V2 document before saving; do not rely on `model_copy(update=...)` alone to run document validators.
2. Release the Buddy registry lock before any MIND call or database work.
3. Call MIND #96 `create_empty_space` with the exact saved allocation and semantic inputs. MIND's operation owns atomic minting and genesis creation.
4. Reacquire the lock and reload the latest registry. Confirm the same managed World, verified source root, pending allocation, binding version, and request digest. Finalize only the Space field on that latest record, preserving any concurrent `native_graph_binding` and unrelated registry updates.
5. If the pending owner or version changed, do not attach the receipt to a replacement. Leave the durable MIND result recoverable under the original allocation and report a conflict for retry/reconciliation. Same-World concurrent requests with identical intent converge on the same allocation and receipt; different intent conflicts.
6. Enforce uniqueness of active MIND Space IDs and allocation IDs across managed Worlds before every persisted mutation. An allocator collision must not write a registry document that later becomes unreadable.

The public World DTO may expose a separate KnowledgeSpace `status` (`unbound | pending | active`) and `binding_version` only. Keep allocation IDs, Space IDs, semantic descriptors/digests, and receipts private. Reads of legacy V1 registry data remain read-only and must not rewrite it; a V2 mutation must preserve every existing Graph binding.

## API and authorization

Use one empty-body endpoint: `POST /api/live/world-containers/{managed_world_id}/knowledge-space`. The server generates the allocation identity and chooses the pinned domain/profile. Reject unexpected body fields.

Reuse the existing accepted `enforce_native_graph_gm(request)` guard at the route before World lookup, registry/file access, MIND access, or any durable mutation. Do not add an auth framework. A mounted route test must show missing and invalid credentials fail before registry or MIND calls; valid authorization reaches only the provisioning operation. The response uses the public DTO and contains no private Space identity or receipt.

## Proposed implementation write set after activation

This list is a design proposal, not an active lease:

- This handoff.
- `apps/live_control_server/services/world_container_registry.py`
- `apps/live_control_server/services/world_space_binding.py`
- `apps/live_control_server/integrations/dungeonmind/world_space_provisioning.py`
- `apps/live_control_server/routes/world_containers.py`
- `pyproject.toml` and `uv.lock` for the exact MIND #96 pin, after PRIME confirms serial ownership relative to #763.
- `tests/test_world_container_registry.py`, `tests/test_world_space_binding.py`, route tests, and `tests/integration/test_world_space_binding_postgres.py`.

Do not edit `Docs/Roadmaps/ROADMAP-demo.md) in this lease proposal: open PR #869 also touches it. If the roadmap needs a status change before #869 settles, re-anchor and resolve that collision first.

## Required verification after activation

**Unit and route boundary**

- V1 registry reads do not write or normalize the stored file; V2 records without Space binding remain unbound.
- A V2 mutation preserves an existing Graph binding and public responses redact all private Space data.
- Cover unique active Space/allocation constraints, allocator collision, invalid or mismatched receipts, pending failure, same-key/same-intent response-loss replay, same-key/changed-intent conflict, same-World concurrent retries, stale-owner/version fencing, and an unrelated concurrent Graph-binding update.
- Prove registry mutation locks are not held while MIND is called.
- Mount the real route and prove auth rejection precedes file/registry/MIND work; prove the authorized empty-body call provisions only once and returns the redacted DTO.
- Run the existing Buddy MIND Graph adapter and native Graph binding suites under exact MIND pin #96. A dependency pin change that breaks those paths blocks activation/merge pending contract repair.

**No-skip disposable PostgreSQL owner-boundary witness**

Adapt the existing J3 integration fixture; use only a dedicated disposable PostgreSQL admin DSN and a clean DungeonMind checkout pinned to `619329c2c8586572ffd04558a79b3555c2ca3764`. The fixture must reject configured/shared production targets, create a unique disposable database, and drop only that database during cleanup. Require the acceptance command to report **1 passed, 0 skipped**; missing DSN/source inputs are a failure to provide evidence, not a pass.

Exercise Buddy's production provisioning path and verify: exact V2 World→Space binding and MIND receipt; MIND Space ID differs from both managed World and native Graph IDs; empty genesis has no parent; a post-commit lost response followed by same-key retry returns the same receipt and one genesis; a fresh Python process can reopen the registry and read the exact MIND revision; and an independent Graph binding survives Space finalization. Include same-World concurrency and stale-owner/version races without writing any shared or live database.

No providers, model calls, source admission, existing-Graph writes, or persistent Buddy demo runtime are part of this slice.

## Gates before this design may become ACTIVE

- PRIME accepts this redesign and issues one exact implementation handoff with current branch/base, path allowlist, verification commands, and disposable PostgreSQL lease.
- Re-anchor all open PRs and leases immediately before activation. Keep #826 held. Resolve the shared `pyproject.toml`/`uv.lock` order with paused #763; the #96 pin and Graph compatibility tests belong to this single J3 implementation PR.
- Obtain the dedicated disposable DSN and clean MIND #96 source needed for the no-skip test. Do not start a database or service for this design-only phase.
- If any source contract, World record lifecycle, or auth guard differs from the stated current evidence, stop and revise the handoff before code changes.

Until those gates are satisfied, this BLOCKED handoff grants no code-write, runtime, database, provider, or merge authority. The original #826 remains paused. This redesign establishes neither existing-Graph adoption nor connected-session acceptance.
