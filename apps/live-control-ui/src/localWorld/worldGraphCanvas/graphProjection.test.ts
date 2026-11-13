import { describe, expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { LocalWorldRecord, LocalWorldRelationship } from "../localWorldRepository";
import { createGraphFallbackPositions, graphBubbleRadius, indexLocalWorldGraph, projectLocalWorldGraph } from "./graphProjection";

function minimumCenterDistance(points: readonly { x: number; y: number }[]): number {
  let minimumSquared = Infinity;
  for (let a = 0; a < points.length; a += 1) {
    for (let b = a + 1; b < points.length; b += 1) {
      minimumSquared = Math.min(minimumSquared, (points[a].x - points[b].x) ** 2 + (points[a].y - points[b].y) ** 2);
    }
  }
  return Math.sqrt(minimumSquared);
}

function minimumBubbleGap(points: readonly { x: number; y: number; relationshipCount: number }[]): number {
  let minimum = Infinity;
  for (let a = 0; a < points.length; a += 1) {
    for (let b = a + 1; b < points.length; b += 1) {
      minimum = Math.min(minimum, Math.hypot(points[a].x - points[b].x, points[a].y - points[b].y)
        - graphBubbleRadius(points[a].relationshipCount) - graphBubbleRadius(points[b].relationshipCount));
    }
  }
  return minimum;
}

function positionedNodes(index: ReturnType<typeof indexLocalWorldGraph>, positions: ReturnType<typeof createGraphFallbackPositions>) {
  return [...positions].map(([id, point]) => ({ ...point, relationshipCount: index.relationshipCounts.get(id) ?? 0 }));
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
    expect(graph.diagnostics).toHaveLength(12);
    expect(graph.omittedDiagnostics).toBe(988);
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

  it("counts distinct valid incident IDs before filters, including parallel, reverse and self edges", async () => {
    const record = await graphRecord();
    const [a, b, c] = record.snapshot.objects;
    const base = record.snapshot.relationships[0];
    const relationships = [base, base,
      { ...base, id: "parallel" as typeof base.id },
      { ...base, id: "reverse" as typeof base.id, fromObjectId: b.id, toObjectId: a.id },
      { ...base, id: "self" as typeof base.id, toObjectId: a.id },
      { ...base, id: "invalid" as typeof base.id, toObjectId: "missing" as typeof a.id },
    ];
    const snapshot = { ...record.snapshot, relationships };
    const index = indexLocalWorldGraph(snapshot);
    expect(index.relationshipCounts.get(a.id)).toBe(4);
    expect(index.relationshipCounts.get(b.id)).toBe(3);
    expect(index.relationshipCounts.get(c.id)).toBe(0);
    const focused = projectLocalWorldGraph({ ...record, snapshot }, {
      fullCorpus: true, showUnconnected: false, focusObjectId: a.id, maxNodes: 1, maxEdges: 0,
    }, index);
    expect(focused.nodes[0].relationshipCount).toBe(4);
    expect(focused.edges).toEqual([]);
    expect(focused.hiddenUnconnectedNodes).toBe(2);
    expect(focused.omittedNodes).toBe(1);
  });

  it("hides only unconnected objects, keeps all valid edges and separates filtering from budget omissions", async () => {
    const record = await corpusRecord();
    const result = projectLocalWorldGraph(record, { fullCorpus: true, showUnconnected: false, maxNodes: 1, maxEdges: 0 });
    expect(result.nodes).toHaveLength(561);
    expect(result.edges).toHaveLength(559);
    expect(result.hiddenUnconnectedNodes).toBe(843);
    expect(result.omittedNodes).toBe(0);
    expect(result.hiddenRelationships).toBe(0);
    expect(result.nodes.every(node => node.relationshipCount > 0)).toBe(true);
    const bounded = projectLocalWorldGraph(record, { showUnconnected: false, maxNodes: 2 });
    expect(bounded.hiddenUnconnectedNodes).toBe(843);
    expect(bounded.omittedNodes).toBe(559);
    expect(projectLocalWorldGraph(record, { fullCorpus: true }).hiddenUnconnectedNodes).toBe(0);
  });

  it("reveals exact isolated IDs without changing focus budgets or full-snapshot coordinates", async () => {
    const record = await corpusRecord();
    const isolated = record.snapshot.objects[1403];
    const full = projectLocalWorldGraph(record, { fullCorpus: true });
    const shown = projectLocalWorldGraph(record, { fullCorpus: true, showUnconnected: false, revealObjectIds: [isolated.id] });
    expect(shown.nodes).toHaveLength(562);
    expect(shown.hiddenUnconnectedNodes).toBe(842);
    expect(shown.nodes.find(node => node.id === isolated.id)).toEqual(full.nodes.find(node => node.id === isolated.id));
    const focused = projectLocalWorldGraph(record, { fullCorpus: true, showUnconnected: false, focusObjectId: isolated.id });
    expect(focused.nodes.map(node => node.id)).toEqual([isolated.id]);
    expect(focused.nodes[0].relationshipCount).toBe(0);
    const bounded = projectLocalWorldGraph(record, {
      fullCorpus: true, showUnconnected: false, focusObjectId: record.snapshot.objects[0].id,
      revealObjectIds: [isolated.id], maxNodes: 1,
    });
    expect(bounded.nodes.map(node => node.id)).toEqual([record.snapshot.objects[0].id]);
  });

  it("keeps all-isolate snapshots accessible through reveal, focus and the legacy default", async () => {
    const record = await graphRecord();
    const isolated = { ...record, snapshot: { ...record.snapshot, relationships: [] } };
    const hidden = projectLocalWorldGraph(isolated, { fullCorpus: true, showUnconnected: false });
    expect(hidden.nodes).toEqual([]);
    expect(hidden.hiddenUnconnectedNodes).toBe(4);
    expect(hidden.omittedNodes).toBe(0);
    expect(projectLocalWorldGraph(isolated).nodes).toHaveLength(4);
    const revealed = projectLocalWorldGraph(isolated, { fullCorpus: true, showUnconnected: false, revealObjectIds: [record.snapshot.objects[1].id] });
    expect(revealed.nodes.map(node => node.id)).toEqual([record.snapshot.objects[1].id]);
    expect(revealed.hiddenUnconnectedNodes).toBe(3);
  });

  it("packs neighbors tightly around larger real hubs with radius-aware separation", async () => {
    const record = await graphRecord();
    const objects = Array.from({ length: 40 }, (_, i) => ({ ...record.snapshot.objects[0], id: `ring:${i}` as typeof record.snapshot.objects[number]["id"] }));
    const relationships = objects.slice(1).map((object, i) => ({
      ...record.snapshot.relationships[0], id: `ring-edge:${i}` as typeof record.snapshot.relationships[number]["id"],
      fromObjectId: objects[0].id, toObjectId: object.id,
    }));
    const index = indexLocalWorldGraph({ ...record.snapshot, objects, relationships });
    const positions = createGraphFallbackPositions(index);
    const center = positions.get(objects[0].id)!;
    const radii = [...positions.values()].map(point => Math.round(Math.hypot(point.x - center.x, point.y - center.y)));
    expect(new Set(radii).size).toBeGreaterThan(2);
    expect(Math.max(...radii)).toBeLessThan(400);
    expect(graphBubbleRadius(index.relationshipCounts.get(objects[0].id)!)).toBeGreaterThan(graphBubbleRadius(1) * 3);
    expect(minimumBubbleGap(positionedNodes(index, positions))).toBeGreaterThanOrEqual(4 - 1e-6);
  });

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
    expect(minimumBubbleGap(result.nodes)).toBeGreaterThanOrEqual(4 - 1e-6);
    for (const { x, y } of result.nodes) {
      expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
      expect(Math.min(x, y)).toBeGreaterThanOrEqual(0);
      expect(Math.max(x, y)).toBeLessThanOrEqual(6000);
    }
  });

  it("reads only sparse focused edge candidates in snapshot order", async () => {
    const record = await graphRecord();
    const [a, b, c, d] = record.snapshot.objects;
    const base = record.snapshot.relationships[0];
    const edge = (id: string, fromObjectId: typeof a.id, toObjectId: typeof a.id) =>
      ({ ...base, id: id as typeof base.id, fromObjectId, toObjectId });
    const relationships = [
      edge("reverse", b.id, a.id),
      ...Array.from({ length: 10_000 }, (_, i) => edge(`unrelated-${i}`, c.id, c.id)),
      edge("loop", a.id, a.id), edge("parallel-1", a.id, b.id), edge("parallel-2", a.id, b.id),
    ];
    const snapshot = { ...record.snapshot, relationships };
    const index = indexLocalWorldGraph(snapshot);
    let reads = 0;
    const countedIndex = { ...index, validRelationships: new Proxy(index.validRelationships, {
      get(target, key, receiver) {
        if (typeof key === "string" && /^\d+$/.test(key)) reads++;
        return Reflect.get(target, key, receiver);
      },
    }) };
    const focused = projectLocalWorldGraph({ ...record, snapshot }, {
      focusObjectId: a.id, maxNodes: 2, maxEdges: 3,
    }, countedIndex);
    expect(focused.edges.map(({ id }) => id)).toEqual(["reverse", "loop", "parallel-1"]);
    expect(focused.hiddenRelationships).toBe(10_001);
    expect(reads).toBe(4);

    reads = 0;
    const isolated = projectLocalWorldGraph({ ...record, snapshot }, { focusObjectId: d.id }, countedIndex);
    expect(isolated.nodes.map(({ id }) => id)).toEqual([d.id]);
    expect(isolated.edges).toEqual([]);
    expect(reads).toBe(0);
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

  it("keeps connected geometry independent of isolates while saved positions remain authoritative", async () => {
    const record = await corpusRecord();
    const previous = createGraphFallbackPositions(indexLocalWorldGraph(record.snapshot));
    const added = { ...record.snapshot.objects[0], id: "added" as typeof record.snapshot.objects[number]["id"] };
    const next = { ...record, snapshot: { ...record.snapshot, objects: [added, ...record.snapshot.objects] } };
    const retained = createGraphFallbackPositions(indexLocalWorldGraph(next.snapshot), previous);
    const index = indexLocalWorldGraph(record.snapshot);
    for (const [id, position] of previous) {
      if (index.relationshipCounts.get(id)) expect(retained.get(id)).toEqual(position);
    }
    expect(retained.size).toBe(1405);
    expect(new Set([...retained.values()].map(({ x, y }) => `${x}:${y}`)).size).toBe(1405);
    expect(minimumBubbleGap(positionedNodes(indexLocalWorldGraph(next.snapshot), retained))).toBeGreaterThanOrEqual(4 - 1e-6);
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
    expect(minimumBubbleGap(graph.nodes)).toBeGreaterThanOrEqual(4 - 1e-6);
    const xs = graph.nodes.map(node => node.x);
    expect(Math.max(...xs) - Math.min(...xs)).toBeGreaterThan(50);
  });

  it("adapts around a moved hub and unrelated pins without moving any saved positions", async () => {
    const record = await graphRecord();
    const index = indexLocalWorldGraph(record.snapshot);
    const original = createGraphFallbackPositions(index);
    const hub = [...index.relationshipCounts].sort((a, b) => b[1] - a[1])[0][0];
    const other = record.snapshot.objects.find(object => object.id !== hub)!;
    const savedPositions: Record<string, { x: number; y: number }> = { [hub]: { x: 1400, y: 1500 }, [other.id]: { x: 500, y: 550 } };
    const positions = createGraphFallbackPositions(index, { savedPositions });
    for (const [id, pin] of Object.entries(savedPositions)) expect(positions.get(id as typeof hub)).toEqual(pin);
    expect(minimumBubbleGap(positionedNodes(index, positions))).toBeGreaterThanOrEqual(4 - 1e-6);
    expect([...positions].some(([id, point]) => !savedPositions[id] && JSON.stringify(point) !== JSON.stringify(original.get(id)))).toBe(true);
    expect(createGraphFallbackPositions(index, { savedPositions })).toEqual(positions);
    const graph = projectLocalWorldGraph({ ...record, layout: { ...record.layout, positions: savedPositions } }, { fullCorpus: true });
    for (const node of graph.nodes) expect({ x: node.x, y: node.y }).toEqual(positions.get(node.id));
    expect(minimumBubbleGap(graph.nodes)).toBeGreaterThanOrEqual(4 - 1e-6);
    expect(createGraphFallbackPositions(index)).toEqual(original);
  });

  it("recomputes unpinned packing for topology and radius changes, not stale fallback hints", async () => {
    const record = await graphRecord();
    const index = indexLocalWorldGraph(record.snapshot);
    const original = createGraphFallbackPositions(index);
    const [a, b] = record.snapshot.objects;
    const more = Array.from({ length: 40 }, (_, i) => ({ ...record.snapshot.relationships[0],
      id: `new:${i}` as LocalWorldRelationship["id"], fromObjectId: a.id, toObjectId: b.id,
    }));
    const changed = indexLocalWorldGraph({ ...record.snapshot, relationships: [...record.snapshot.relationships, ...more] });
    const adapted = createGraphFallbackPositions(changed);
    expect(adapted).not.toEqual(original);
    expect(minimumBubbleGap(positionedNodes(changed, adapted))).toBeGreaterThanOrEqual(4 - 1e-6);
    expect(graphBubbleRadius(changed.relationshipCounts.get(a.id)!)).toBe(24 * Math.sqrt(40));
  });

  it("keeps overlapping pins fixed and other objects separated from them", async () => {
    const record = await graphRecord();
    const [a, b] = record.snapshot.objects;
    const pins = { [a.id]: { x: 640, y: 640 }, [b.id]: { x: 640, y: 640 } };
    const graph = projectLocalWorldGraph({ ...record, layout: { ...record.layout, positions: pins } }, { fullCorpus: true });
    expect(graph.nodes[0]).toMatchObject(pins[a.id]);
    expect(graph.nodes[1]).toMatchObject(pins[b.id]);
    expect(minimumBubbleGap(graph.nodes.filter(node => node.id !== b.id))).toBeGreaterThanOrEqual(4 - 1e-6);
  });

  it("checks high-degree collisions across the old 200-unit bucket boundary", async () => {
    const record = await graphRecord();
    const [hub, a, b] = record.snapshot.objects;
    const relationships = Array.from({ length: 80 }, (_, i) => ({ ...record.snapshot.relationships[0],
      id: `dense-pin:${i}` as LocalWorldRelationship["id"], fromObjectId: hub.id, toObjectId: i < 40 ? a.id : b.id,
    }));
    // A root at (640,640) would overlap a 152-radius pin at (350,640).
    // The old 200-unit cells differ by two and a fixed +/-1 lookup missed it.
    const pins = { [a.id]: { x: 350, y: 640 }, [b.id]: { x: 350, y: 1000 } };
    const graph = projectLocalWorldGraph({ ...record, snapshot: { ...record.snapshot, objects: [hub, a, b], relationships },
      layout: { ...record.layout, positions: pins },
    }, { fullCorpus: true });
    expect(graph.nodes.find(node => node.id === a.id)).toMatchObject(pins[a.id]);
    expect(graph.nodes.find(node => node.id === b.id)).toMatchObject(pins[b.id]);
    expect(graph.nodes.every(node => graphBubbleRadius(node.relationshipCount) === 24 * Math.sqrt(40))).toBe(true);
    expect(minimumBubbleGap(graph.nodes)).toBeGreaterThanOrEqual(4 - 1e-6);
  });

  it("bounds the shared radius and ignores malformed negative or NaN degrees", () => {
    expect(graphBubbleRadius(0)).toBe(18);
    expect(graphBubbleRadius(-1)).toBe(18);
    expect(graphBubbleRadius(NaN)).toBe(18);
    expect(graphBubbleRadius(40)).toBe(24 * Math.sqrt(40));
    expect(graphBubbleRadius(Infinity)).toBe(24 * Math.sqrt(40));
    expect(graphBubbleRadius(100)).toBe(24 * Math.sqrt(40));
    expect(graphBubbleRadius(1)).toBe(24);
    expect(graphBubbleRadius(31)).toBeCloseTo(133.63, 1);
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

  it("terminates with finite unique coordinates for very large disks and singleton self-components", async () => {
    const record = await graphRecord();
    const objects = Array.from({ length: 20000 }, (_, i) => ({ ...record.snapshot.objects[0], id: `extreme:${i}` as typeof record.snapshot.objects[number]["id"] }));
    const positions = createGraphFallbackPositions(indexLocalWorldGraph({ ...record.snapshot, objects, relationships: [] }));
    expect(positions.size).toBe(objects.length);
    expect(new Set([...positions.values()].map(({ x, y }) => `${x}:${y}`)).size).toBe(objects.length);
    expect([...positions.values()].every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 6000 && y >= 0 && y <= 6000)).toBe(true);
    const self = { ...record.snapshot.relationships[0], fromObjectId: objects[0].id, toObjectId: objects[0].id };
    const singleton = projectLocalWorldGraph({ ...record, snapshot: { ...record.snapshot, objects: [objects[0]], relationships: [self] } }, { fullCorpus: true, showUnconnected: false });
    expect(singleton.nodes).toHaveLength(1);
    expect(singleton.nodes[0]).toMatchObject({ relationshipCount: 1, x: 640, y: 640 });
    expect(singleton.edges).toHaveLength(1);
  });

  it("repairs incomplete or non-finite retained fallback maps without a subset grid", async () => {
    const record = await graphRecord();
    const [a, b, c] = record.snapshot.objects;
    const retained = new Map([[a.id, { x: 101, y: 202 }], [b.id, { x: NaN, y: Infinity }], [c.id, { x: 303, y: 404 }]]);
    const result = projectLocalWorldGraph(record, { fullCorpus: true, fallbackPositions: retained });
    expect(result.nodes[0]).toMatchObject({ x: 101, y: 202 });
    expect(result.nodes[2]).toMatchObject({ x: 303, y: 404 });
    expect(result.nodes.every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 6000 && y >= 0 && y <= 6000)).toBe(true);
    expect(retained.get(b.id)!.x).toBeNaN();
  });

  it("places disconnected individuals after real components without inventing edges", async () => {
    const record = await graphRecord();
    const [a, b] = record.snapshot.objects;
    const snapshot = { ...record.snapshot, relationships: [{ ...record.snapshot.relationships[0], fromObjectId: a.id, toObjectId: b.id }] };
    const result = projectLocalWorldGraph({ ...record, snapshot }, { fullCorpus: true });
    const connected = result.nodes.filter(node => node.id === a.id || node.id === b.id);
    const isolated = result.nodes.filter(node => node.id !== a.id && node.id !== b.id);
    const center = connected[0];
    const radius = (node: { x: number; y: number }) => Math.hypot(node.x - center.x, node.y - center.y);
    expect(Math.max(...connected.map(radius))).toBeLessThanOrEqual(Math.min(...isolated.map(radius)) + 0.000001);
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
