/**
 * Diagnostic only: run with a Vitest config whose include selects this file.
 * These are development React/jsdom CPU timings, not browser frame rates or a
 * weak-device result. Fixture topology matches the observed counts, not the World.
 */
import { Profiler, type ProfilerOnRenderCallback } from "react";
import { fireEvent, render, cleanup } from "@testing-library/react";
import { expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { LocalWorldRecord } from "../localWorldRepository";
import { graphBubbleRadius, createGraphFallbackPositions, indexLocalWorldGraph, projectLocalWorldGraph } from "./graphProjection";
import { WorldGraphCanvas } from "./WorldGraphCanvas";

function summary(values: number[]) {
  const sorted = [...values].sort((a, b) => a - b);
  return { samples: sorted.length, median_ms: sorted[Math.floor(sorted.length / 2)], p95_ms: sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * .95))] };
}

it("reports the 1404-object/559-edge full SVG experiment without claiming browser performance", async () => {
  const repository = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
  const empty = await createTestWorld(repository, "Synthetic full graph benchmark");
  const objects = Array.from({ length: 1404 }, (_, i) => ({ id: repository.allocateObjectId(empty.snapshot.worldId), name: `Object ${i}`, kind: ["person", "location", "event", "faction"][i % 4], properties: {} }));
  const relationships = Array.from({ length: 559 }, (_, i) => {
    const source = i < 43 ? i : 800 + i - 43;
    return { id: repository.allocateRelationshipId(empty.snapshot.worldId), fromObjectId: objects[source].id, toObjectId: objects[source + 1].id, kind: "linked_to", properties: {} };
  });
  const record: LocalWorldRecord = { ...empty, snapshot: { ...empty.snapshot, objects, relationships } };
  const geometry = projectLocalWorldGraph(record, { fullCorpus: true });
  const radii = geometry.nodes.map(node => graphBubbleRadius(node.relationshipCount));
  let minimumClearance = Infinity;
  let overlappingPairs = 0;
  for (let i = 0; i < geometry.nodes.length; i += 1) {
    for (let j = i + 1; j < geometry.nodes.length; j += 1) {
      const a = geometry.nodes[i], b = geometry.nodes[j];
      const clearance = Math.hypot(a.x - b.x, a.y - b.y) - radii[i] - radii[j];
      minimumClearance = Math.min(minimumClearance, clearance);
      if (clearance < 0) overlappingPairs += 1;
    }
  }
  expect(overlappingPairs).toBe(0);
  expect(minimumClearance).toBeGreaterThanOrEqual(4 - 1e-7);
  const layoutSamples: number[] = [];
  for (let i = 0; i < 31; i += 1) {
    const started = performance.now();
    const index = indexLocalWorldGraph(record.snapshot);
    const fallbackPositions = createGraphFallbackPositions(index);
    const graph = projectLocalWorldGraph(record, { fullCorpus: true, fallbackPositions }, index);
    if (i) layoutSamples.push(performance.now() - started);
    expect(graph.nodes).toHaveLength(1404);
    expect(graph.edges).toHaveLength(559);
  }
  const runs = [];
  for (const fullCorpus of [false, true]) {
    let phase = "mount";
    const renderSamples: Record<string, number[]> = { mount: [], initial_effects: [], pan: [], zoom: [], select: [] };
    const onRender: ProfilerOnRenderCallback = (_id, renderPhase, duration) => { renderSamples[phase === "mount" && renderPhase !== "mount" ? "initial_effects" : phase].push(duration); };
    const view = render(<Profiler id="graph" onRender={onRender}><WorldGraphCanvas record={record} nodeShape="circle" projectionOptions={{ fullCorpus, maxNodes: 512, maxEdges: 1024 }} /></Profiler>);
    const svg = view.container.querySelector("svg")!;
    phase = "pan";
    for (let i = 0; i < 30; i += 1) fireEvent.keyDown(svg, { key: i % 2 ? "ArrowLeft" : "ArrowRight" });
    phase = "zoom";
    for (let i = 0; i < 30; i += 1) fireEvent.keyDown(svg, { key: i % 2 ? "-" : "+" });
    phase = "select";
    const first = view.container.querySelector("[data-node-id]")!;
    for (let i = 0; i < 6; i += 1) fireEvent.click(first);
    runs.push({ mode: fullCorpus ? "full SVG" : "legacy bounded SVG with camera optimization", nodes: view.container.querySelectorAll("[data-node-id]").length, edges: view.container.querySelectorAll("[data-edge-id]").length, total_svg_elements: svg.querySelectorAll("*").length, react_commit_cpu: Object.fromEntries(Object.entries(renderSamples).map(([key, samples]) => [key, summary(samples)])) });
    cleanup();
  }
  console.info(JSON.stringify({ evidence: "synthetic topology; development React/jsdom CPU only; no browser paint, frame-rate, network or weak-device evidence", geometry: { minimum_clearance: minimumClearance, overlapping_pairs: overlappingPairs }, index_layout_projection: summary(layoutSamples), runs }));
}, 60000);
