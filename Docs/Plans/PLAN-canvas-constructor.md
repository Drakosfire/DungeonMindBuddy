# PLAN — Canvas Constructor

## Purpose

Canvas Constructor is a separate internal project for standardizing how DungeonBuddy benchmark outputs become Cursor canvas review surfaces.

The goal is to stop writing bespoke canvas emitters for every benchmark.

Canvas Constructor should provide a common contract for:

1. benchmark JSON report ingestion,
2. normalized review payload construction,
3. generated canvas block emission,
4. marker-based patching,
5. reusable layout conventions,
6. testable anti-cheating / anti-drift guardrails.

## Problem

Current benchmark canvases are useful but fragmented. Each emitter decides its own payload shape, marker naming, summary rows, card structure, and update flow.

This makes every new benchmark review surface slower and riskier to build.

## Design principles

- Canonical benchmark state lives in JSON reports.
- Canvas payloads are generated projections.
- Generated regions are never hand-edited.
- Canvas files live in Cursor-managed canvas paths.
- Emitters should support `--check`.
- Emitters should support `--payload-out`.
- Payloads should preserve failure detail, not only aggregate scores.
- Payloads should make missing expected context visible.
- Payloads should separate benchmark computation from presentation.
- No canvas emitter should rerun retrieval unless explicitly requested.

## Target architecture

Benchmark report JSON
→ Canvas Constructor adapter
→ normalized canvas review payload
→ generated TypeScript block
→ Cursor canvas shell

## Standard adapter contract

Each benchmark should provide an adapter that maps benchmark-specific report JSON into:

- `summary`
- `statTiles`
- `modeRows`
- `questionRows` or `scenarioRows`
- `detailCards`
- `guardrailRows`
- `sourcePointers`
- `deltaRows`

## Standard generated block contract

```ts
// BEGIN GENERATED <BENCHMARK_ID>
const <benchmarkPayloadName> = { ... } as const;
// END GENERATED <BENCHMARK_ID>
```

## Project phases

### Phase 0 — Document conventions

Capture existing canvas patterns and define Canvas Constructor contract.

### Phase 1 — C1S4 Step 2D adapter

Build the expected-context canvas projection as first conforming adapter.

### Phase 2 — Shared emitter helpers

Extract common marker replacement, check mode, payload writing, and path resolution into shared utilities.

### Phase 3 — Shared review payload schema

Define a common schema for benchmark review payloads.

### Phase 4 — Shared TSX layout components

Standardize rendering components for stat tiles, mode rows, question cards, retrieved evidence, and failure callouts.

### Phase 5 — Backport older benchmarks

Adapt C1S2/C1S13 breadcrumb canvases to the shared Canvas Constructor contract.

## Non-goals

Canvas Constructor does not compute benchmark metrics.
Canvas Constructor does not tune retrieval.
Canvas Constructor does not own benchmark gold.
Canvas Constructor does not replace canonical JSON reports.
Canvas Constructor does not write oracle data into planner-visible surfaces.

## First consumer

C1S4 Step 2C expected-context benchmark.
