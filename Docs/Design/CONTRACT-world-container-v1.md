# CONTRACT — World Container v1

**Status:** durable product contract for CON-READY CR01B  
**Schema tokens:** `dmb_world_container_registry_v1` / `dmb_world_container_record_v1`  
**Owning service:** `apps/live_control_server/services/world_container_registry.py`  
**HTTP surface:** `GET|POST /api/live/world-containers`

## Purpose

A **managed world container** is the minimum durable product identity that says a named world exists and owns a source-root directory. It is not a World Graph, campaign, or published corpus.

## Record shape

```text
dmb_world_container_record_v1
  world_id              # immutable server-owned safe id
  name                  # human display name
  source_root_relpath   # server-derived corpus/<world_id>-markdown/
  created_at            # UTC ISO timestamp
```

Registry document:

```text
dmb_world_container_registry_v1
  records[]
```

Persistence path: `out/registries/world_containers.json`

## Create contract

Client may supply only:

```json
{ "name": "The Glass Orchard" }
```

Clients must not supply `world_id`, filesystem paths, graph roots, campaign IDs, or source document IDs. Extra fields are rejected.

Server behavior:

1. Trim/collapse whitespace for display name; empty/whitespace-only → 422.
2. Normalize name (casefold + collapsed whitespace) for duplicate comparison only.
3. Derive a safe `world_id` matching `^[a-z][a-z0-9_-]{0,62}$`.
4. Derive `source_root_relpath = corpus/<world_id>-markdown/`.
5. Same normalized name → reconcile and return the existing managed world (idempotent).
6. Derived id colliding with a **different** managed name → 409.
7. Unmanaged pre-existing directory at the intended root → 409 (do not adopt/delete).
8. If root `mkdir` fails → no registry record.
9. If registry persist fails after this operation created a new empty root → best-effort remove only that empty root.

## Authority boundaries

| Concern | Authority |
|---|---|
| Managed world existence + display name + source root | world-container registry |
| Build source identity / path | workspace document registry (unchanged) |
| Source bytes / `source_import` | Tiptap/Canvas write + CR01A contract |
| Campaign → graph world mapping | static `WORLD_ID_BY_CAMPAIGN` (unchanged; not this registry) |
| World Graph / extraction / publication | unchanged; not created by world create |

## Build world-level source compatibility

A Build source that belongs directly to a managed world uses:

```text
world_id    = <exact managed world id>
campaign_id = <same exact managed world id>
```

This means **world-scoped Build source**, not “a campaign named after the world.”

## Explicit non-goals

- campaign creation/registry
- graph bootstrap
- rename/delete/archive/merge worlds
- adopting arbitrary existing `corpus/*-markdown` roots by scanning the filesystem
- mutating `WORLD_ID_BY_CAMPAIGN`
