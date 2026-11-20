import {
  cloneLocalWorldValue,
  type CommitSemanticResult,
  type LocalObjectId,
  type LocalWorldRecord,
  type LocalWorldRepository,
  type LocalWorldRelationship,
  type WriteLayoutResult,
} from "../localWorldRepository";

export interface NewLocalGraphObject {
  readonly name: string;
  readonly kind: string;
}

export interface NewLocalGraphRelationship {
  readonly fromObjectId: LocalObjectId;
  readonly toObjectId: LocalObjectId;
  readonly kind: string;
}

function nonEmpty(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
}

export function createLocalWorldGraphAdapter(repository: LocalWorldRepository) {
  return {
    renameObject(record: LocalWorldRecord, objectId: LocalObjectId, proposedName: string): Promise<CommitSemanticResult> {
      const name = nonEmpty(proposedName);
      if (!name) return Promise.resolve({ status: "error", message: "Enter a name before saving." });
      const snapshot = cloneLocalWorldValue(record.snapshot);
      const object = snapshot.objects.find((candidate) => candidate.id === objectId);
      if (!object) return Promise.resolve({ status: "error", message: "That object is no longer in this World." });
      const previousName = object.name;
      const nextSnapshot = {
        ...snapshot,
        objects: snapshot.objects.map((candidate) => candidate.id === objectId ? { ...candidate, name } : candidate),
      };
      return repository.commitSemanticEdit({
        worldId: snapshot.worldId,
        expectedLocalRevision: record.localRevision,
        nextSnapshot,
        edit: { classification: "buddy-local-only", description: `Renamed ${previousName}` },
      });
    },

    createObject(record: LocalWorldRecord, input: NewLocalGraphObject): Promise<CommitSemanticResult> {
      const name = nonEmpty(input.name);
      const kind = nonEmpty(input.kind);
      if (!name || !kind) return Promise.resolve({ status: "error", message: "Enter both a name and a type." });
      const snapshot = cloneLocalWorldValue(record.snapshot);
      const object = {
        id: repository.allocateObjectId(snapshot.worldId),
        name,
        kind,
        properties: {},
      };
      return repository.commitSemanticEdit({
        worldId: snapshot.worldId,
        expectedLocalRevision: record.localRevision,
        nextSnapshot: { ...snapshot, objects: [...snapshot.objects, object] },
        edit: { classification: "buddy-local-only", description: `Added ${name}` },
      });
    },

    createRelationship(record: LocalWorldRecord, input: NewLocalGraphRelationship): Promise<CommitSemanticResult> {
      const kind = nonEmpty(input.kind);
      if (!kind) return Promise.resolve({ status: "error", message: "Enter a relationship label." });
      const snapshot = cloneLocalWorldValue(record.snapshot);
      if (!snapshot.objects.some((object) => object.id === input.fromObjectId) ||
          !snapshot.objects.some((object) => object.id === input.toObjectId)) {
        return Promise.resolve({ status: "error", message: "Choose two objects that are still in this World." });
      }
      const relationship: LocalWorldRelationship = {
        id: repository.allocateRelationshipId(snapshot.worldId),
        fromObjectId: input.fromObjectId,
        toObjectId: input.toObjectId,
        kind,
        properties: {},
      };
      return repository.commitSemanticEdit({
        worldId: snapshot.worldId,
        expectedLocalRevision: record.localRevision,
        nextSnapshot: { ...snapshot, relationships: [...snapshot.relationships, relationship] },
        edit: { classification: "buddy-local-only", description: `Added relationship: ${kind}` },
      });
    },

    moveObjects(record: LocalWorldRecord, positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>): Promise<WriteLayoutResult> {
      const capturedPositions = cloneLocalWorldValue(positions);
      const nextLayout = {
        positions: { ...cloneLocalWorldValue(record.layout.positions), ...capturedPositions },
        viewport: cloneLocalWorldValue(record.layout.viewport),
        layoutVersion: record.layout.layoutVersion + 1,
      };
      return repository.writeLayout({
        worldId: record.snapshot.worldId,
        expectedLayoutRevision: record.layoutRevision,
        nextLayout,
      });
    },
  };
}
