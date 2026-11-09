import type {
  LocalWorldObject,
  LocalWorldRecord,
  LocalWorldRelationship,
} from "../localWorldRepository";

export const DEFAULT_GRAPH_LIMITS = Object.freeze({ nodes: 48, edges: 96 });
const MAX_GRAPH_COORDINATE = 6000;
const MAX_ENDPOINT_DIAGNOSTICS = 12;

export interface ProjectedGraphNode {
  readonly id: LocalWorldObject["id"];
  readonly name: string;
  readonly kind: string;
  readonly x: number;
  readonly y: number;
  readonly object: LocalWorldObject;
}

export interface ProjectedGraphEdge {
  readonly id: LocalWorldRelationship["id"];
  readonly fromObjectId: LocalWorldObject["id"];
  readonly toObjectId: LocalWorldObject["id"];
  readonly kind: string;
  readonly relationship: LocalWorldRelationship;
}

export interface GraphProjection {
  readonly worldId: LocalWorldRecord["snapshot"]["worldId"];
  readonly nodes: readonly ProjectedGraphNode[];
  readonly edges: readonly ProjectedGraphEdge[];
  readonly diagnostics: readonly string[];
  readonly omittedNodes: number;
  readonly omittedEdges: number;
  readonly examinedRelationships: number;
  readonly omittedDiagnostics: number;
  readonly unexaminedRelationships: number;
}

export interface GraphProjectionOptions {
  readonly maxNodes?: number;
  readonly maxEdges?: number;
}

function boundedLimit(value: number | undefined, ceiling: number): number {
  if (value === undefined || !Number.isFinite(value)) return ceiling;
  return Math.max(0, Math.min(ceiling, Math.floor(value)));
}

function initialPosition(index: number): { x: number; y: number } {
  const columns = 4;
  return { x: 96 + (index % columns) * 204, y: 74 + Math.floor(index / columns) * 132 };
}

export function projectLocalWorldGraph(
  record: Pick<LocalWorldRecord, "snapshot" | "layout">,
  options: GraphProjectionOptions = {},
): GraphProjection {
  const maxNodes = boundedLimit(options.maxNodes, DEFAULT_GRAPH_LIMITS.nodes);
  const maxEdges = boundedLimit(options.maxEdges, DEFAULT_GRAPH_LIMITS.edges);
  const objects = record.snapshot.objects;
  const relationships = record.snapshot.relationships;
  const visibleObjects = objects.slice(0, maxNodes);
  const visibleIds = new Set(visibleObjects.map((object) => object.id));
  const diagnostics: string[] = [];
  const nodes = visibleObjects.map((object, index) => {
    const saved = record.layout.positions[object.id];
    const fallback = initialPosition(index);
    const x = saved && Number.isFinite(saved.x) ? Math.max(0, Math.min(MAX_GRAPH_COORDINATE, saved.x)) : fallback.x;
    const y = saved && Number.isFinite(saved.y) ? Math.max(0, Math.min(MAX_GRAPH_COORDINATE, saved.y)) : fallback.y;
    return { id: object.id, name: object.name, kind: object.kind, x, y, object };
  });

  const edges: ProjectedGraphEdge[] = [];
  const relationshipScanLimit = Math.min(relationships.length, maxEdges + MAX_ENDPOINT_DIAGNOSTICS);
  let examinedRelationships = 0;
  let omittedDiagnostics = 0;
  for (const relationship of relationships) {
    if (edges.length >= maxEdges || examinedRelationships >= relationshipScanLimit) break;
    examinedRelationships += 1;
    if (!visibleIds.has(relationship.fromObjectId) || !visibleIds.has(relationship.toObjectId)) {
      if (diagnostics.length < MAX_ENDPOINT_DIAGNOSTICS) {
        diagnostics.push(`Relationship ${relationship.id} refers to a missing or capped node and was not rendered.`);
      } else {
        omittedDiagnostics += 1;
      }
      continue;
    }
    edges.push({
      id: relationship.id,
      fromObjectId: relationship.fromObjectId,
      toObjectId: relationship.toObjectId,
      kind: relationship.kind,
      relationship,
    });
  }

  return {
    worldId: record.snapshot.worldId,
    nodes,
    edges,
    diagnostics,
    omittedNodes: Math.max(0, objects.length - visibleObjects.length),
    omittedEdges: Math.max(0, relationships.length - edges.length),
    examinedRelationships,
    omittedDiagnostics,
    unexaminedRelationships: Math.max(0, relationships.length - examinedRelationships),
  };
}
