import { describe, expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { LocalWorldRecord, LocalWorldRelationship } from "../localWorldRepository";
import { indexLocalWorldGraph, projectLocalWorldGraph } from "./graphProjection";

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
