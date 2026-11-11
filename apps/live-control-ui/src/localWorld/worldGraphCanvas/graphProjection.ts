import type {
  LocalWorldObject,
  LocalWorldRecord,
  LocalWorldRelationship,
} from "../localWorldRepository";

export const DEFAULT_GRAPH_LIMITS = Object.freeze({ nodes: 48, edges: 96 });
export const MAX_GRAPH_LIMITS = Object.freeze({ nodes: 512, edges: 1024 });
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
  readonly hiddenRelationships: number;
  readonly invalidRelationships: number;
  readonly examinedRelationships: number;
  readonly omittedDiagnostics: number;
  readonly unexaminedRelationships: number;
}

export interface GraphProjectionOptions {
  readonly maxNodes?: number;
  readonly maxEdges?: number;
  readonly focusObjectId?: LocalWorldObject["id"] | null;
  readonly neighborhoodDepth?: number;
}

function boundedLimit(value: number | undefined, ceiling: number): number {
  if (value === undefined || !Number.isFinite(value)) return ceiling;
  return Math.max(0, Math.min(ceiling, Math.floor(value)));
}

function initialPosition(index: number, total: number): { x: number; y: number } {
  const columns = total <= 4 ? 2 : Math.ceil(Math.sqrt(total));
  return { x: 80 + (index % columns) * 520, y: 80 + Math.floor(index / columns) * 300 };
}

/** Full loaded-snapshot index. Visibility is not endpoint integrity. */
export interface LocalWorldGraphIndex {
  readonly snapshot: LocalWorldRecord["snapshot"];
  readonly objects: ReadonlyMap<LocalWorldObject["id"], LocalWorldObject>;
  readonly neighbors: ReadonlyMap<LocalWorldObject["id"], readonly LocalWorldObject["id"][]>;
  readonly validRelationships: readonly LocalWorldRelationship[];
  readonly diagnostics: readonly string[];
  readonly invalidRelationships: number;
}

export function indexLocalWorldGraph(snapshot: LocalWorldRecord["snapshot"]): LocalWorldGraphIndex {
  const objects = new Map(snapshot.objects.map((object) => [object.id, object]));
  const neighbors = new Map<LocalWorldObject["id"], LocalWorldObject["id"][]>();
  const validRelationships: LocalWorldRelationship[] = [];
  const diagnostics: string[] = [];
  let invalidRelationships = 0;
  for (const relationship of snapshot.relationships) {
    if (!objects.has(relationship.fromObjectId) || !objects.has(relationship.toObjectId)) {
      invalidRelationships += 1;
      if (diagnostics.length < MAX_ENDPOINT_DIAGNOSTICS) {
        diagnostics.push(`Relationship ${relationship.id} refers to an object absent from the loaded graph and was not rendered.`);
      }
      continue;
    }
    validRelationships.push(relationship);
    for (const [source, target] of [[relationship.fromObjectId, relationship.toObjectId], [relationship.toObjectId, relationship.fromObjectId]]) {
      const adjacent = neighbors.get(source);
      if (adjacent) adjacent.push(target);
      else neighbors.set(source, [target]);
    }
  }
  return { snapshot, objects, neighbors, validRelationships, diagnostics, invalidRelationships };
}

export function projectLocalWorldGraph(
  record: Pick<LocalWorldRecord, "snapshot" | "layout">,
  options: GraphProjectionOptions = {},
  suppliedIndex?: LocalWorldGraphIndex,
): GraphProjection {
  const maxNodes = options.maxNodes === undefined ? DEFAULT_GRAPH_LIMITS.nodes : boundedLimit(options.maxNodes, MAX_GRAPH_LIMITS.nodes);
  const maxEdges = options.maxEdges === undefined ? DEFAULT_GRAPH_LIMITS.edges : boundedLimit(options.maxEdges, MAX_GRAPH_LIMITS.edges);
  // Reject an accidentally retained index from an older World/revision.
  const index = suppliedIndex?.snapshot === record.snapshot ? suppliedIndex : indexLocalWorldGraph(record.snapshot);
  const objects = record.snapshot.objects;
  let visibleObjects = objects.slice(0, maxNodes);
  if (maxNodes && options.focusObjectId && index.objects.has(options.focusObjectId)) {
    const depthLimit = boundedLimit(options.neighborhoodDepth ?? 1, objects.length);
    const queue = [{ id: options.focusObjectId, depth: 0 }];
    const visited = new Set([options.focusObjectId]);
    for (let cursor = 0; cursor < queue.length && queue.length < maxNodes; cursor += 1) {
      const { id, depth } = queue[cursor];
      if (depth >= depthLimit) continue;
      for (const neighbor of index.neighbors.get(id) ?? []) {
        if (visited.has(neighbor)) continue;
        visited.add(neighbor);
        queue.push({ id: neighbor, depth: depth + 1 });
        if (queue.length >= maxNodes) break;
      }
    }
    visibleObjects = queue.map(({ id }) => index.objects.get(id)!);
  }
  const visibleIds = new Set(visibleObjects.map((object) => object.id));
  const nodes = visibleObjects.map((object, position) => {
    const saved = record.layout.positions[object.id];
    const fallback = initialPosition(position, visibleObjects.length);
    const x = saved && Number.isFinite(saved.x) ? Math.max(0, Math.min(MAX_GRAPH_COORDINATE, saved.x)) : fallback.x;
    const y = saved && Number.isFinite(saved.y) ? Math.max(0, Math.min(MAX_GRAPH_COORDINATE, saved.y)) : fallback.y;
    return { id: object.id, name: object.name, kind: object.kind, x, y, object };
  });
  const edges: ProjectedGraphEdge[] = [];
  // Scan all valid relationships so an early hidden edge cannot starve later visible edges.
  for (const relationship of index.validRelationships) {
    if (edges.length >= maxEdges) break;
    if (!visibleIds.has(relationship.fromObjectId) || !visibleIds.has(relationship.toObjectId)) continue;
    edges.push({ id: relationship.id, fromObjectId: relationship.fromObjectId,
      toObjectId: relationship.toObjectId, kind: relationship.kind, relationship });
  }
  return {
    worldId: record.snapshot.worldId, nodes, edges,
    diagnostics: index.diagnostics,
    omittedNodes: Math.max(0, objects.length - nodes.length),
    omittedEdges: record.snapshot.relationships.length - edges.length,
    hiddenRelationships: index.validRelationships.length - edges.length,
    invalidRelationships: index.invalidRelationships,
    examinedRelationships: record.snapshot.relationships.length,
    omittedDiagnostics: Math.max(0, index.invalidRelationships - index.diagnostics.length),
    unexaminedRelationships: 0,
  };
}
