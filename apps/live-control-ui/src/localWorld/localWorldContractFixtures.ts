import type { LocalWorldId, LocalWorldRepository, LocalWorldSnapshot } from "./localWorldRepository";

/** Deterministic test-only local IDs; never used by the production adapter. */
export function sequenceLocalIds(): () => string {
  let next = 0;
  return () => `fixture-${++next}`;
}

export async function createTestWorld(repo: LocalWorldRepository, title = "Untitled World") {
  const created = await repo.createWorld({ title });
  if (created.status !== "created") throw new Error(created.message);
  return created.record;
}

/** Four-node semantic test fixture only; this is not product/demo World data. */
export function fourNodeWorldFixture(
  repo: Pick<LocalWorldRepository, "allocateObjectId" | "allocateRelationshipId">,
  worldId: LocalWorldId,
): LocalWorldSnapshot {
  const mara = {
    id: repo.allocateObjectId(worldId),
    name: "Mara Venn",
    kind: "person",
    properties: { role: "traveler" },
  };
  const tomas = {
    id: repo.allocateObjectId(worldId),
    name: "Tomas Reed",
    kind: "person",
    properties: { role: "traveler" },
  };
  const orchard = {
    id: repo.allocateObjectId(worldId),
    name: "The Glass Orchard",
    kind: "location",
    properties: { region: "North Reach" },
  };
  const accord = {
    id: repo.allocateObjectId(worldId),
    name: "The Winter Accord",
    kind: "event",
    properties: { year: 412 },
  };
  return {
    worldId,
    title: "The Ember Coast",
    objects: [mara, tomas, orchard, accord],
    relationships: [
      {
        id: repo.allocateRelationshipId(worldId),
        fromObjectId: mara.id,
        toObjectId: accord.id,
        kind: "negotiated",
        properties: { outcome: "signed" },
      },
      {
        id: repo.allocateRelationshipId(worldId),
        fromObjectId: tomas.id,
        toObjectId: orchard.id,
        kind: "protects",
        properties: { since: "winter" },
      },
    ],
  };
}

export function sameNameWorldPeopleFixture(
  repo: Pick<LocalWorldRepository, "allocateObjectId">,
  worldId: LocalWorldId,
) {
  return ["east", "west"].map((home) => ({
    id: repo.allocateObjectId(worldId),
    name: "The Lantern Keeper",
    kind: "person",
    properties: { home },
  }));
}
