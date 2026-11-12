import { describe, expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { LocalWorldRecord, LocalWorldRelationship } from "../localWorldRepository";
import { createGraphFallbackPositions, indexLocalWorldGraph, projectLocalWorldGraph } from "./graphProjection";

function minimumCenterDistance(points: readonly { x: number; y: number }[]): number {
  let minimumSquared = Infinity;
  for (let a = 0; a < points.length; a += 1) {
    for (let b = a + 1; b < points.length; b += 1) {
      minimumSquared = Math.min(minimumSquared, (points[a].x - points[b].x) ** 2 + (points[a].y - points[b].y) ** 2);
    }
  }
  return Math.sqrt(minimumSquared);
}

async function graphRecord(): Promise<LocalWorldRecord> {
  const repo = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
  const empty = await createTestWorld(repo, "The Ember Coast");
  const worldId = empty.snapshot.worldId;
  const people = ["Mara Venn", "Tomas Reed"].map((name) => ({
    id: repo.allocateObjectId(worldId), name, kind: "person", properties: {},
  }));
  const orchard = { id: repo.allocateObjectId(worldId), name: "The Glass Orchard", kind: "location", properties: {} };
  const accord = { id: repo.allocateObjectId(worldId), name: "The Winter Accord", kind: "event", properties: {} };
  const objects = [...people, orchard, accord];
  const relationships = [
    [people[0].id, people[1].id, "allies"],
    [people[0].id, accord.id, "negotiated"],
    [people[1].id, accord.id, "signed"],
    [orchard.id, accord.id, "hosted"],
  ].map(([fromObjectId, toObjectId, kind]) => ({
    id: repo.allocateRelationshipId(worldId), fromObjectId, toObjectId, kind, properties: {},
  })) as LocalWorldRelationship[];
  const result = await repo.commitSemanticEdit({
    worldId, expectedLocalRevision: 0,
    nextSnapshot: { worldId, title: empty.snapshot.title, objects, relationships },
    edit: { classification: "buddy-local-only", description: "Test fixture graph" },
  });
  if (result.status !== "committed") throw new Error("Unable to seed graph test fixture.");
  return result.record;
}

describe("projectLocalWorldGraph", () => {
  it("projects two People, a Location and an Event with identity-preserving connected assertions and no root node", async () => {
    const record = await graphRecord();
    const graph = projectLocalWorldGraph(record);
    expect(graph.nodes.map((node) => node.id)).toEqual(record.snapshot.objects.map((object) => object.id));
    expect(graph.nodes.map((node) => node.kind)).toEqual(["person", "person", "location", "event"]);
    expect(graph.edges.map((edge) => edge.id)).toEqual(record.snapshot.relationships.map((edge) => edge.id));
    expect(graph.edges).toHaveLength(4);
    expect(graph.edges[0].fromObjectId).toBe(graph.nodes[0].id);
    expect(graph.edges[0].toObjectId).toBe(graph.nodes[1].id);
    expect(graph.nodes.some((node) => node.kind === "world")).toBe(false);
    expect(new Set(graph.nodes.map((node) => node.y)).size).toBe(2);
    expect(graph.nodes[1].x - graph.nodes[0].x).toBeGreaterThan(168 + 200);
    expect(graph.nodes[2].y - graph.nodes[0].y).toBeGreaterThan(76 + 160);
  });

  it("preserves parallel relationship IDs and cycles without tree assumptions", async () => {
    const record = await graphRecord();
    const [first, second] = record.snapshot.objects;
    const parallel: LocalWorldRelationship = {
      id: `${record.snapshot.worldId}:relationship:parallel` as LocalWorldRelationship["id"],
      fromObjectId: first.id, toObjectId: second.id, kind: "allies", properties: {},
    };
    const reverse: LocalWorldRelationship = {
      ...parallel,
      id: `${record.snapshot.worldId}:relationship:reverse` as LocalWorldRelationship["id"],
      fromObjectId: second.id, toObjectId: first.id, kind: "rivals",
    };
    const withCycles = { ...record, snapshot: { ...record.snapshot, relationships: [...record.snapshot.relationships, parallel, reverse] } };
    const graph = projectLocalWorldGraph(withCycles);
    expect(graph.edges.slice(-2).map((edge) => edge.id)).toEqual([parallel.id, reverse.id]);
    expect(graph.edges.filter((edge) => edge.kind === "allies")).toHaveLength(2);
    expect(graph.edges.some((edge) => edge.fromObjectId === second.id && edge.toObjectId === first.id)).toBe(true);
    expect(graph.diagnostics).toEqual([]);
  });

  it("omits invalid references without inventing endpoint nodes", async () => {
    const record = await graphRecord();
    const invalid: LocalWorldRelationship = {
      id: `${record.snapshot.worldId}:relationship:missing` as LocalWorldRelationship["id"],
      fromObjectId: record.snapshot.objects[0].id,
      toObjectId: "missing-object" as LocalWorldRelationship["toObjectId"],
      kind: "mentions", properties: {},
    };
    const graph = projectLocalWorldGraph({ ...record, snapshot: { ...record.snapshot, relationships: [...record.snapshot.relationships, invalid] } });
    expect(graph.nodes).toHaveLength(4);
    expect(graph.edges.some((edge) => edge.id === invalid.id)).toBe(false);
    expect(graph.diagnostics).toEqual([`Relationship ${invalid.id} refers to an object absent from the loaded graph and was not rendered.`]);
    expect(graph.omittedEdges).toBe(1);
  });

  it("checks every relationship while bounding malformed diagnostics", async () => {
    const record = await graphRecord();
    const invalidRecords = Array.from({ length: 1000 }, (_, index) => ({
      id: `${record.snapshot.worldId}:relationship:broken-${index}` as LocalWorldRelationship["id"],
      fromObjectId: record.snapshot.objects[0].id,
      toObjectId: `missing-${index}` as LocalWorldRelationship["toObjectId"],
      kind: "mentions",
      properties: {},
    }));
    const graph = projectLocalWorldGraph({
      ...record,
      snapshot: { ...record.snapshot, relationships: invalidRecords },
    }, { maxEdges: 2 });
    expect(graph.examinedRelationships).toBe(1000);
    expect(graph.diagnostics).toHaveLength(12);
    expect(graph.omittedDiagnostics).toBe(988);
    expect(graph.unexaminedRelationships).toBe(0);
    expect(graph.omittedEdges).toBe(1000);
  });

  it("uses deterministic fixed positions and enforces finite node and edge caps", async () => {
    const record = await graphRecord();
    const first = projectLocalWorldGraph(record, { maxNodes: 3, maxEdges: 10 });
    const repeated = projectLocalWorldGraph(record, { maxNodes: 3, maxEdges: 10 });
    expect(first.nodes.map(({ x, y }) => ({ x, y }))).toEqual(repeated.nodes.map(({ x, y }) => ({ x, y })));
    expect(first.nodes).toHaveLength(3);
    expect(first.edges).toHaveLength(1);
    expect(first.omittedNodes).toBe(1);
    expect(first.omittedEdges).toBe(3);
    expect(first.diagnostics).toHaveLength(0)
    expect(first.hiddenRelationships).toBe(3);
    const edgeCapped = projectLocalWorldGraph(record, { maxNodes: 4, maxEdges: 2 });
    expect(edgeCapped.edges).toHaveLength(2);
    expect(edgeCapped.omittedEdges).toBe(2);
    expect(projectLocalWorldGraph(record, { maxNodes: 0, maxEdges: 0 }).nodes).toEqual([]);
  });

  it("keeps the legacy default and supports the explicit bounded explorer budget", async () => {
    const record = await graphRecord();
    const objects = Array.from({ length: 513 }, (_, index) => ({
      ...record.snapshot.objects[0], id: `${record.snapshot.worldId}:object:explorer-${index}` as typeof record.snapshot.objects[number]["id"],
    }));
    const relationships = Array.from({ length: 1025 }, (_, index) => ({
      ...record.snapshot.relationships[0],
      id: `${record.snapshot.worldId}:relationship:explorer-${index}` as typeof record.snapshot.relationships[number]["id"],
      fromObjectId: objects[0].id,
      toObjectId: objects[1].id,
    }));
    const largeRecord = { ...record, snapshot: { ...record.snapshot, objects, relationships } };

    const legacy = projectLocalWorldGraph(largeRecord);
    expect(legacy.nodes).toHaveLength(48);
    expect(legacy.edges).toHaveLength(96);
    expect(legacy.omittedNodes).toBe(465);
    expect(legacy.omittedEdges).toBe(929);

    const explorer = projectLocalWorldGraph(largeRecord, { maxNodes: 512, maxEdges: 1024 });
    expect(explorer.nodes).toHaveLength(512);
    expect(explorer.edges).toHaveLength(1024);
    expect(explorer.omittedNodes).toBe(1);
    expect(explorer.omittedEdges).toBe(1);
    expect(explorer.unexaminedRelationships).toBe(0);
    const full = projectLocalWorldGraph(largeRecord, { fullCorpus: true });
    expect(full.nodes).toHaveLength(513);
    expect(full.edges).toHaveLength(1025);
  });
});


describe("loaded corpus exploration", () => {
  async function corpusRecord() {
    const record = await graphRecord();
    const objects = Array.from({ length: 1404 }, (_, i) => ({
      ...record.snapshot.objects[0], id: `object:${i}` as typeof record.snapshot.objects[number]["id"], name: `Object ${i}`,
    }));
    // Reproduce the report: 43 visible and 516 valid hidden relationships.
    const relationships = Array.from({ length: 559 }, (_, i) => ({
      ...record.snapshot.relationships[0], id: `edge:${i}` as typeof record.snapshot.relationships[number]["id"],
      fromObjectId: objects[i < 43 ? i : 800 + i - 43].id,
      toObjectId: objects[i < 43 ? i + 1 : 801 + i - 43].id,
    }));
    return { ...record, snapshot: { ...record.snapshot, objects, relationships } };
  }

  it("renders all 1404 loaded objects and 559 real edges despite overview budgets", async () => {
    const record = await corpusRecord();
    const result = projectLocalWorldGraph(record, { fullCorpus: true, maxNodes: 1, maxEdges: 0 });
    expect(result.nodes).toHaveLength(1404);
    expect(result.edges).toHaveLength(559);
    expect(result.nodes.map(node => node.id)).toEqual(record.snapshot.objects.map(object => object.id));
    expect(result.edges.map(edge => edge.id)).toEqual(record.snapshot.relationships.map(edge => edge.id));
    expect(result.omittedNodes).toBe(0);
    expect(result.hiddenRelationships).toBe(0);
    expect(result.invalidRelationships).toBe(0);
    expect(new Set(result.nodes.map(({ x, y }) => `${x}:${y}`)).size).toBe(1404);
    expect(minimumCenterDistance(result.nodes)).toBeGreaterThanOrEqual(128);
    for (const { x, y } of result.nodes) {
      expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
      expect(Math.min(x, y)).toBeGreaterThanOrEqual(0);
      expect(Math.max(x, y)).toBeLessThanOrEqual(6000);
    }
  });

  it("keeps full-corpus geometry stable under reorder and bounded focus", async () => {
    const record = await corpusRecord();
    const full = projectLocalWorldGraph(record, { fullCorpus: true });
    const positions = new Map(full.nodes.map(({ id, x, y }) => [id, { x, y }]));
    const reordered = { ...record, snapshot: { ...record.snapshot,
      objects: [...record.snapshot.objects].reverse(), relationships: [...record.snapshot.relationships].reverse(),
    } };
    const reversed = projectLocalWorldGraph(reordered, { fullCorpus: true });
    for (const { id, x, y } of reversed.nodes) expect({ x, y }).toEqual(positions.get(id));
    const focused = projectLocalWorldGraph(record, { fullCorpus: true, focusObjectId: record.snapshot.objects[1000].id, maxNodes: 3 });
    expect(focused.nodes).toHaveLength(3);
    expect(focused.edges).toHaveLength(2);
    for (const { id, x, y } of focused.nodes) expect({ x, y }).toEqual(positions.get(id));
    const isolated = projectLocalWorldGraph(record, { fullCorpus: true, focusObjectId: record.snapshot.objects[1403].id });
    expect(isolated.nodes).toHaveLength(1);
    expect(isolated.edges).toEqual([]);
    expect({ x: isolated.nodes[0].x, y: isolated.nodes[0].y }).toEqual(positions.get(isolated.nodes[0].id));
  });

  it("preserves edge identities, self-loops and endpoint diagnostics in full mode", async () => {
    const record = await graphRecord();
    const [a, b] = record.snapshot.objects;
    const base = record.snapshot.relationships[0];
    const relationships = [base,
      { ...base, id: "parallel" as typeof base.id },
      { ...base, id: "reverse" as typeof base.id, fromObjectId: b.id, toObjectId: a.id },
      { ...base, id: "self" as typeof base.id, toObjectId: a.id },
      { ...base, id: "invalid" as typeof base.id, toObjectId: "missing" as typeof a.id },
    ];
    const result = projectLocalWorldGraph({ ...record, snapshot: { ...record.snapshot, relationships } }, { fullCorpus: true });
    expect(result.edges.map(edge => edge.id)).toEqual(relationships.slice(0, 4).map(edge => edge.id));
    expect(result.nodes).toHaveLength(4);
    expect(result.invalidRelationships).toBe(1);
    expect(result.omittedEdges).toBe(1);
    expect(result.hiddenRelationships).toBe(0);
    expect(result.diagnostics).toHaveLength(1);
  });

  it("retains World-local fallbacks across additions while saved positions remain authoritative", async () => {
    const record = await corpusRecord();
    const previous = createGraphFallbackPositions(indexLocalWorldGraph(record.snapshot));
    const added = { ...record.snapshot.objects[0], id: "added" as typeof record.snapshot.objects[number]["id"] };
    const next = { ...record, snapshot: { ...record.snapshot, objects: [added, ...record.snapshot.objects] } };
    const retained = createGraphFallbackPositions(indexLocalWorldGraph(next.snapshot), previous);
    for (const [id, position] of previous) expect(retained.get(id)).toEqual(position);
    expect(retained.size).toBe(1405);
    expect(new Set([...retained.values()].map(({ x, y }) => `${x}:${y}`)).size).toBe(1405);
    expect(minimumCenterDistance([...retained.values()])).toBeGreaterThanOrEqual(128);
    const [a, b, c] = record.snapshot.objects;
    const pinned = { ...next, layout: { ...next.layout, positions: {
      [a.id]: { x: 123, y: 456 }, [b.id]: { x: -10, y: 9000 }, [c.id]: { x: NaN, y: 333 },
    } } };
    const graph = projectLocalWorldGraph(pinned, { fullCorpus: true, fallbackPositions: retained });
    const byId = new Map(graph.nodes.map(node => [node.id, node]));
    expect(byId.get(a.id)).toMatchObject({ x: 123, y: 456 });
    expect(byId.get(b.id)).toMatchObject({ x: 0, y: 6000 });
    expect(byId.get(c.id)).toMatchObject({ x: retained.get(c.id)!.x, y: 333 });
    const removed = createGraphFallbackPositions(indexLocalWorldGraph(record.snapshot), retained);
    expect(removed.has(added.id)).toBe(false);
  });

  it("keeps small full-graph layouts compact enough for useful Fit zoom", async () => {
    const record = await graphRecord();
    const graph = projectLocalWorldGraph(record, { fullCorpus: true });
    expect(Math.max(...graph.nodes.map(node => node.x))).toBeLessThanOrEqual(720);
    expect(Math.max(...graph.nodes.map(node => node.y))).toBeLessThanOrEqual(720);
    expect(new Set(graph.nodes.map(({ x, y }) => `${x}:${y}`)).size).toBe(4);
    expect(minimumCenterDistance(graph.nodes)).toBeGreaterThanOrEqual(128);
    const xs = graph.nodes.map(node => node.x);
    expect(Math.max(...xs) - Math.min(...xs)).toBeGreaterThan(112);
  });

  it("keeps small-graph additions away from near collisions with retained positions", async () => {
    const record = await graphRecord();
    const [a] = record.snapshot.objects;
    // This is near a normal slot, but not exactly on it. Exact-coordinate
    // de-duplication alone would still allow overlapping 112px bubbles.
    const previous = new Map([[a.id, { x: 90, y: 90 }]]);
    const positions = createGraphFallbackPositions(indexLocalWorldGraph(record.snapshot), previous);
    expect(positions.get(a.id)).toEqual({ x: 90, y: 90 });
    expect(minimumCenterDistance([...positions.values()])).toBeGreaterThanOrEqual(128);
    const added = { ...a, id: "added-small" as typeof a.id };
    const next = createGraphFallbackPositions(indexLocalWorldGraph({ ...record.snapshot, objects: [added, ...record.snapshot.objects] }), positions);
    for (const [id, point] of positions) expect(next.get(id)).toEqual(point);
    expect(minimumCenterDistance([...next.values()])).toBeGreaterThanOrEqual(128);
  });

  it("retains every object with finite coordinates when the fixed-spacing domain is exhausted", async () => {
    const record = await graphRecord();
    const objects = Array.from({ length: 2500 }, (_, i) => ({ ...record.snapshot.objects[0], id: `large:${i}` as typeof record.snapshot.objects[number]["id"] }));
    const result = projectLocalWorldGraph({ ...record, snapshot: { ...record.snapshot, objects, relationships: [] } }, { fullCorpus: true });
    expect(result.nodes).toHaveLength(2500);
    expect(result.omittedNodes).toBe(0);
    expect(result.edges).toEqual([]);
    expect(new Set(result.nodes.map(({ x, y }) => `${x}:${y}`)).size).toBe(2500);
    expect(result.nodes.every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 6000 && y >= 0 && y <= 6000)).toBe(true);
    // Capacity degrades spatial detail, never object identity or loaded count.
    expect(minimumCenterDistance(result.nodes)).toBeLessThan(144);
  });

  it("repairs incomplete or non-finite retained fallback maps without a subset grid", async () => {
    const record = await graphRecord();
    const [a, b] = record.snapshot.objects;
    const retained = new Map([[a.id, { x: 101, y: 202 }], [b.id, { x: NaN, y: Infinity }]]);
    const result = projectLocalWorldGraph(record, { fullCorpus: true, fallbackPositions: retained });
    expect(result.nodes[0]).toMatchObject({ x: 101, y: 202 });
    expect(result.nodes.every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 6000 && y >= 0 && y <= 6000)).toBe(true);
    expect(retained.get(b.id)!.x).toBeNaN();
  });

  it("keeps disconnected individuals in a separate region without inventing edges", async () => {
    const record = await graphRecord();
    const [a, b] = record.snapshot.objects;
    const snapshot = { ...record.snapshot, relationships: [{ ...record.snapshot.relationships[0], fromObjectId: a.id, toObjectId: b.id }] };
    const result = projectLocalWorldGraph({ ...record, snapshot }, { fullCorpus: true });
    const connected = result.nodes.filter(node => node.id === a.id || node.id === b.id);
    const isolated = result.nodes.filter(node => node.id !== a.id && node.id !== b.id);
    expect(Math.max(...connected.map(node => node.y))).toBeLessThan(Math.min(...isolated.map(node => node.y)));
    expect(result.edges).toHaveLength(1);
    expect(result.nodes).toHaveLength(4);
    const empty = createGraphFallbackPositions(indexLocalWorldGraph({ ...snapshot, objects: [], relationships: [] }));
    expect(empty.size).toBe(0);
  });

  it("reports the 1404/559 corpus as bounded visibility, not 516 integrity failures", async () => {
    const record = await corpusRecord();
    const result = projectLocalWorldGraph(record, { maxNodes: 512, maxEdges: 1024 });
    expect(result.nodes).toHaveLength(512);
    expect(result.edges).toHaveLength(43);
    expect(result.omittedNodes).toBe(892);
    expect(result.hiddenRelationships).toBe(516);
    expect(result.invalidRelationships).toBe(0);
    expect(result.diagnostics).toEqual([]);
    expect(result.examinedRelationships).toBe(559);
  });

  it("focuses a late ID, expands both directions and preserves disconnected objects", async () => {
    const record = await corpusRecord();
    const options = { maxNodes: 512, maxEdges: 1024, focusObjectId: record.snapshot.objects[1000].id };
    const oneStep = projectLocalWorldGraph(record, options);
    expect(oneStep.nodes.map(n => n.id)).toEqual(["object:1000", "object:999", "object:1001"]);
    expect(oneStep.edges).toHaveLength(2);
    const twoSteps = projectLocalWorldGraph(record, { ...options, neighborhoodDepth: 2 });
    expect(twoSteps.nodes).toHaveLength(5);
    expect(twoSteps.edges).toHaveLength(4);
    expect(projectLocalWorldGraph(record, { ...options, focusObjectId: record.snapshot.objects[1403].id }).nodes.map(n => n.id)).toEqual(["object:1403"]);
    expect(record.snapshot.objects).toHaveLength(1404);
  });

  it("separates actual absent endpoints even beyond the render budget", async () => {
    const record = await corpusRecord();
    const bad = { ...record.snapshot.relationships[0], id: "invalid" as LocalWorldRelationship["id"], toObjectId: "absent" as LocalWorldRelationship["toObjectId"] };
    const result = projectLocalWorldGraph({ ...record, snapshot: { ...record.snapshot, relationships: [...record.snapshot.relationships, bad] } }, { maxNodes: 1, maxEdges: 0 });
    expect(result.hiddenRelationships).toBe(559);
    expect(result.invalidRelationships).toBe(1);
    expect(result.diagnostics).toHaveLength(1);
    expect(result.unexaminedRelationships).toBe(0);
  });

  it("does not starve visible relationships behind a long valid hidden prefix", async () => {
    const record = await corpusRecord();
    const hidden = {...record.snapshot.relationships[43], fromObjectId: record.snapshot.objects[1000].id};
    const visible = record.snapshot.relationships[0];
    const result = projectLocalWorldGraph({...record, snapshot: {...record.snapshot,
      relationships: [...Array.from({length: 2000}, (_, i) => ({...hidden, id: `hidden:${i}` as LocalWorldRelationship["id"]})), visible],
    }}, {maxNodes: 2, maxEdges: 1});
    expect(result.edges.map(e => e.id)).toEqual([visible.id]);
    expect(result.hiddenRelationships).toBe(2000);
    expect(result.diagnostics).toEqual([]);
  });

  it("bounds dense traversal and rejects an index from a different snapshot", async () => {
    const record = await corpusRecord();
    const relationships = Array.from({length: 2000}, (_, i) => ({
      ...record.snapshot.relationships[0], id: `dense:${i}` as LocalWorldRelationship["id"],
      fromObjectId: record.snapshot.objects[1403].id, toObjectId: record.snapshot.objects[i % 1404].id,
    }));
    const dense = { ...record, snapshot: { ...record.snapshot, relationships } };
    const index = indexLocalWorldGraph(dense.snapshot);
    const result = projectLocalWorldGraph(dense, {maxNodes: 48, maxEdges: 96, focusObjectId: dense.snapshot.objects[1403].id, neighborhoodDepth: 1404}, index);
    expect(result.nodes).toHaveLength(48);
    expect(result.nodes[0].id).toBe("object:1403");
    expect(result.edges.length).toBeLessThanOrEqual(96);
    const other = { ...record, snapshot: { ...record.snapshot, relationships: [] } };
    expect(projectLocalWorldGraph(other, {}, index).edges).toEqual([]);
  });
});
