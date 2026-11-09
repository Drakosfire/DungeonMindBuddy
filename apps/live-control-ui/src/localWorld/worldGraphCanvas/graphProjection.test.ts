import { describe, expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "../localWorldContractFixtures";
import type { LocalWorldRecord, LocalWorldRelationship } from "../localWorldRepository";
import { projectLocalWorldGraph } from "./graphProjection";

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
    expect(graph.diagnostics).toEqual([`Relationship ${invalid.id} refers to a missing or capped node and was not rendered.`]);
    expect(graph.omittedEdges).toBe(1);
  });

  it("caps malformed relationship inspection and diagnostics", async () => {
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
    expect(graph.examinedRelationships).toBe(14);
    expect(graph.diagnostics).toHaveLength(12);
    expect(graph.omittedDiagnostics).toBe(2);
    expect(graph.unexaminedRelationships).toBe(986);
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
    expect(first.diagnostics).toHaveLength(3);
    const edgeCapped = projectLocalWorldGraph(record, { maxNodes: 4, maxEdges: 2 });
    expect(edgeCapped.edges).toHaveLength(2);
    expect(edgeCapped.omittedEdges).toBe(2);
    expect(projectLocalWorldGraph(record, { maxNodes: 0, maxEdges: 0 }).nodes).toEqual([]);
  });
});
