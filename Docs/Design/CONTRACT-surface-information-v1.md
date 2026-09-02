# Surface Information Contract v1

**Status:** ACTIVE
**Slice:** SURFACE-INTEGRATION SI-2
**Companion:** [`ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md)
**Implementation:** `apps/live-control-ui/src/surfaceInformation/`
**Handoff:** [`../Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md)

This document is the durable semantic authority for Surface Information v1. It describes how one authority-owned observation reaches a Surface through a reactive channel. It does **not** define commands, AppChrome publication, product providers, or persistence.

## Two separate concepts

```text
Surface Interaction
  structural capabilities / commands / chrome publication

Surface Information
  changing observations from one authority
```

A Surface Information channel observes **one information projection from one authority**. A Surface that needs DungeonMind + APP-STATE + Combat information composes multiple channels. The channel is never a universal store and never silently owns multiple authorities.

Changing information does **not** require republishing structural AppChrome configuration or a new ReactNode. A connected renderer subscribes to the channel. That is the architectural response to OC-020.

## Authority vocabulary

```text
dungeonmind
buddy_app_state
source_storage
ingest
mechanics
combat
agent
```

The provider is not the authority. Example: `providerId = plan_world_graph_projection`, `authority = dungeonmind`.

Do not add `unknown`, `mixed`, `surface`, `generic`, or `derived` as escape hatches. If information cannot identify one owning authority, split it into multiple channels.

## Descriptor

A channel is created from an immutable descriptor:

```text
channelId          opaque exact identity, not a label
informationKind    the projection being observed
providerId         the Buddy adapter/provider
authority          one v1 authority
subject            primary observed identity (kind + id)
scope              exact surrounding request scope
```

Changing any descriptor identity means a **different channel**. Do not mutate a live descriptor to represent a new world, work, run, or scope.

References (`kind` + `id`) are stable identity pointers, never display labels, and carry no body/content fields.

## Revision vs generation

Authority revision is:

```text
exact value
or
unrevisioned  — this authority/projection has no revision concept usable here
```

`unrevisioned` does **not** mean “revision exists but the provider failed to discover it.”

Observation **generation** is channel-local, monotonically increasing, and is not an authority revision, timestamp, payload hash, or React identity.

Initial snapshot:

```text
generation = 0
state = loading
```

## State vocabulary

| Status | Value | Revision | Reason |
|---|---|---|---|
| `loading` | No | No | Optional diagnostics only |
| `ready` | Current value | Exact or explicit unrevisioned | No |
| `empty` | No | Exact or explicit unrevisioned | No |
| `stale` | Last-known value | Last-known exact/unrevisioned | Required |
| `unavailable` | No | No current observation | Required |
| `integrity_error` | No | No trusted current observation | Required |

`empty` is a successful observation that the requested information is genuinely absent. It is never a synonym for not configured, unavailable, failed parsing, integrity failure, or unknown scope.

`stale` is the only way a previous READY value may remain visible as a claimed information value.

`unavailable` and `integrity_error` never carry `value` and never silently substitute the previous READY value.

## Provenance, inspection, diagnostics

Observed metadata on READY / EMPTY / STALE:

```text
provenance           accepted identity/evidence pointers
inspectionTargets    stable identities the product may navigate/inspect
diagnostics          Surface/operator-safe messages
```

Empty arrays are valid. Diagnostics must not contain credentials, password-bearing DSNs, authorization headers, document bodies, private Agent thread bodies, or large serialized domain payloads. v1 has no `details: unknown` escape hatch.

## Channel behavior

Factory: `createSurfaceInformationChannel(descriptor)`.

| Operation | Rule |
|---|---|
| `getSnapshot()` | Same object between accepted observations; new object after every accepted visible observation |
| `subscribe` | Registers one listener; unsubscribe is idempotent; subscription is not an observation event |
| `beginObservation` | Invalidates any previous ticket; default `publishLoading=true` publishes loading as a new generation; `publishLoading=false` retains the visible snapshot while still superseding the prior ticket |
| `commit` | Current ticket + non-loading state → consume ticket, increment generation, new snapshot, notify once, return true. Stale/foreign/consumed/disposed ticket → no change, no notify, return false |
| Equivalent data | Still a new observation. No deep equality, JSON signature, ReactNode, revision, or value dedupe |
| `dispose` | Invalidates the current ticket, clears listeners, `beginObservation` returns null, `commit` returns false. Repeated dispose is safe |

Tickets are opaque, channel-specific, and cannot be constructed by consumers. `commit` accepts only the exact object returned by `beginObservation`; reconstructed, copied, or field-equivalent tickets are rejected.

The channel verifies descriptor lifetime, ticket ordering, generation ordering, snapshot referential semantics, subscriber notification, and dispose. It does **not** verify domain correctness of generic `T`.

## React relationship

Production `surfaceInformation` code does not import React. A consumer may subscribe with:

```ts
useSyncExternalStore(channel.subscribe, channel.getSnapshot)
```

SI-2 does not ship a product hook or provider.

## Persistence

None. Channels, tickets, snapshots, and subscriptions are runtime-only. Replay a consumed ticket is rejected. After dispose, create a new channel.

## What this contract does not do

- Repair Plan's graph panel (SI-3)
- Adopt the contract in Plan / Build / Play / Ingest / Agent / Combat
- Change `SurfaceInteractionPublication`
- Move World, APP-STATE, Ingest, Source, Mechanics, Combat, or Agent authority
- Introduce a backend API, provider registry, or durable store
