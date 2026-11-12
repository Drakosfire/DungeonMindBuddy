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
  readonly relationshipCount: number;
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
  readonly hiddenUnconnectedNodes: number;
  readonly omittedEdges: number;
  readonly hiddenRelationships: number;
  readonly invalidRelationships: number;
  readonly examinedRelationships: number;
  readonly omittedDiagnostics: number;
  readonly unexaminedRelationships: number;
}

export interface GraphProjectionOptions {
  /** Overview ignores budgets; an explicit focus still uses bounded exploration. */
  readonly fullCorpus?: boolean;
  /** Hide zero-degree objects except explicit focus/reveal IDs. */
  readonly showUnconnected?: boolean;
  readonly revealObjectIds?: readonly LocalWorldObject["id"][];
  /** World-local fallbacks; persisted positions always win. */
  readonly fallbackPositions?: GraphFallbackPositions;
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
  readonly relationshipCounts: ReadonlyMap<LocalWorldObject["id"], number>;
  readonly diagnostics: readonly string[];
  readonly invalidRelationships: number;
}

export function indexLocalWorldGraph(snapshot: LocalWorldRecord["snapshot"]): LocalWorldGraphIndex {
  const objects = new Map(snapshot.objects.map((object) => [object.id, object]));
  const neighbors = new Map<LocalWorldObject["id"], LocalWorldObject["id"][]>();
  const validRelationships: LocalWorldRelationship[] = [];
  const incidentIds = new Map([...objects.keys()].map(id => [id, new Set<LocalWorldRelationship["id"]>()]));
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
    incidentIds.get(relationship.fromObjectId)!.add(relationship.id);
    incidentIds.get(relationship.toObjectId)!.add(relationship.id);
    for (const [source, target] of [[relationship.fromObjectId, relationship.toObjectId], [relationship.toObjectId, relationship.fromObjectId]]) {
      const adjacent = neighbors.get(source);
      if (adjacent) adjacent.push(target);
      else neighbors.set(source, [target]);
    }
  }
  const relationshipCounts = new Map([...incidentIds].map(([id, incident]) => [id, incident.size]));
  return { snapshot, objects, neighbors, validRelationships, relationshipCounts, diagnostics, invalidRelationships };
}

export type GraphFallbackPositions = ReadonlyMap<LocalWorldObject["id"], Readonly<{ x: number; y: number }>>;

function coordinate(value: number): number {
  return Math.max(0, Math.min(MAX_GRAPH_COORDINATE, value));
}

/**
 * Real components occupy consecutive radial bands, ordered hub-first by BFS.
 * Concentric rings have 136-unit nominal center separation, enough for the
 * 112-unit maximum bubble diameter. Isolates follow the real components;
 * radial distance is presentation only, never a semantic or inferred edge.
 * Previous World-local positions win. Finite-domain capacity can reduce spacing
 * for huge corpora; arbitrary retained/pinned positions may still overlap.
 */
export function createGraphFallbackPositions(
  index: LocalWorldGraphIndex,
  previousPositions?: GraphFallbackPositions,
): GraphFallbackPositions {
  const ids = [...index.objects.keys()].sort();
  const adjacency = new Map(ids.map(id => [id, [...new Set(index.neighbors.get(id) ?? [])].filter(other => other !== id).sort()]));
  const visited = new Set<LocalWorldObject["id"]>();
  const groups: LocalWorldObject["id"][][] = [];
  const isolated: LocalWorldObject["id"][] = [];
  for (const id of ids) {
    if (visited.has(id)) continue;
    if ((index.relationshipCounts.get(id) ?? 0) === 0) {
      isolated.push(id);
      visited.add(id);
      continue;
    }
    const component = [id];
    visited.add(id);
    for (let cursor = 0; cursor < component.length; cursor += 1) {
      for (const neighbor of adjacency.get(component[cursor])!) {
        if (!visited.has(neighbor)) { visited.add(neighbor); component.push(neighbor); }
      }
    }
    // Hub first, then breadth-first neighbors. Stable ID tie breaks ensure source
    // ordering does not change topology or positions.
    const root = [...component].sort((a, b) => adjacency.get(b)!.length - adjacency.get(a)!.length || (a < b ? -1 : a > b ? 1 : 0))[0];
    const ordered = [root];
    const discovered = new Set([root]);
    for (let cursor = 0; cursor < ordered.length; cursor += 1) {
      for (const neighbor of adjacency.get(ordered[cursor])!) {
        if (!discovered.has(neighbor)) { discovered.add(neighbor); ordered.push(neighbor); }
      }
    }
    groups.push(ordered);
  }
  // This region asserts no relationship between its individual objects.
  if (isolated.length) groups.push(isolated);
  const result = new Map<LocalWorldObject["id"], { x: number; y: number }>();
  if (!ids.length) return result;
  const radiusLimit = (MAX_GRAPH_COORDINATE - 160) / 2;
  // Chord length, not arc length, must accommodate each bubble.
  const ringSize = (ring: number) => ring === 0 ? 1 : Math.floor(Math.PI / Math.asin(1 / (2 * ring)));
  let rings = 0;
  let capacity = 1;
  // O(sqrt(N)), explicitly bounded even for a singleton graph.
  while (capacity < ids.length && rings < ids.length) capacity += ringSize(++rings);
  const spacing = Math.min(136, radiusLimit / Math.max(1, rings));
  const minimumSeparation = Math.min(128, spacing * 128 / 136);
  const minimumSquared = minimumSeparation ** 2;
  type Point = { x: number; y: number };
  const buckets = new Map<string, Point[]>();
  const bucketKey = (x: number, y: number) => `${x}:${y}`;
  function occupy(point: Point) {
    const key = bucketKey(Math.floor(point.x / minimumSeparation), Math.floor(point.y / minimumSeparation));
    const bucket = buckets.get(key);
    if (bucket) bucket.push(point);
    else buckets.set(key, [point]);
  }
  function available(point: Point) {
    const bx = Math.floor(point.x / minimumSeparation);
    const by = Math.floor(point.y / minimumSeparation);
    for (let x = bx - 1; x <= bx + 1; x += 1) {
      for (let y = by - 1; y <= by + 1; y += 1) {
        for (const occupied of buckets.get(bucketKey(x, y)) ?? []) {
          if ((point.x - occupied.x) ** 2 + (point.y - occupied.y) ** 2 < minimumSquared - 0.000001) return false;
        }
      }
    }
    return true;
  }
  for (const id of ids) {
    const previous = previousPositions?.get(id);
    if (previous && Number.isFinite(previous.x) && Number.isFinite(previous.y)) {
      const point = { x: coordinate(previous.x), y: coordinate(previous.y) };
      result.set(id, point);
      occupy(point);
    }
  }
  function ringPoints(ringCount: number, center: number): Point[] {
    const points: Point[] = [];
    for (let ring = 0; ring <= ringCount; ring += 1) {
      const count = ringSize(ring);
      for (let slot = 0; slot < count; slot += 1) {
        const angle = -Math.PI / 2 + 2 * Math.PI * slot / count;
        points.push({ x: center + ring * spacing * Math.cos(angle), y: center + ring * spacing * Math.sin(angle) });
      }
    }
    return points;
  }
  const desiredPoints = ringPoints(rings, 80 + rings * spacing);
  // Scan spare full-domain slots at most once, rather than searching O(N²).
  const candidates = [...desiredPoints, ...ringPoints(Math.floor(radiusLimit / spacing), MAX_GRAPH_COORDINATE / 2)];
  let candidateCursor = 0;
  let slot = 0;
  for (const group of groups) {
    for (const id of group) {
      const desired = desiredPoints[slot++];
      if (result.has(id)) continue;
      let point = desired;
      if (!available(point)) {
        while (candidateCursor < candidates.length && !available(candidates[candidateCursor])) candidateCursor += 1;
        // Retention wins if arbitrary previous positions exhaust capacity.
        point = candidates[candidateCursor++] ?? desired;
      }
      result.set(id, point);
      occupy(point);
    }
  }
  return result;
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
  const focused = Boolean(options.focusObjectId && index.objects.has(options.focusObjectId));
  const fullOverview = options.fullCorpus && !focused;
  let fallbackPositions = options.fullCorpus ? options.fallbackPositions ?? createGraphFallbackPositions(index) : undefined;
  const revealedIds = new Set(options.revealObjectIds ?? []);
  const eligibleObjects = options.showUnconnected === false
    ? objects.filter(object => (index.relationshipCounts.get(object.id) ?? 0) > 0 || revealedIds.has(object.id) || (focused && object.id === options.focusObjectId))
    : objects;
  const hiddenUnconnectedNodes = objects.length - eligibleObjects.length;
  let visibleObjects = fullOverview ? eligibleObjects : eligibleObjects.slice(0, maxNodes);
  if (maxNodes && options.focusObjectId && index.objects.has(options.focusObjectId)) {
    const depthLimit = boundedLimit(options.neighborhoodDepth ?? 1, objects.length);
    const queue = [{ id: options.focusObjectId, depth: 0 }];
    const visited = new Set([options.focusObjectId]);
    for (let cursor = 0; cursor < queue.length && queue.length < maxNodes; cursor += 1) {
      const { id, depth } = queue[cursor];
      if (depth >= depthLimit) continue;
      for (const neighbor of options.fullCorpus ? [...(index.neighbors.get(id) ?? [])].sort() : index.neighbors.get(id) ?? []) {
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
    let fallback = fallbackPositions?.get(object.id);
    if (options.fullCorpus && (!fallback || !Number.isFinite(fallback.x) || !Number.isFinite(fallback.y))) {
      fallbackPositions = createGraphFallbackPositions(index, fallbackPositions);
      fallback = fallbackPositions.get(object.id);
    }
    fallback = fallback ? { x: coordinate(fallback.x), y: coordinate(fallback.y) } : initialPosition(position, visibleObjects.length);
    const x = saved && Number.isFinite(saved.x) ? Math.max(0, Math.min(MAX_GRAPH_COORDINATE, saved.x)) : fallback.x;
    const y = saved && Number.isFinite(saved.y) ? Math.max(0, Math.min(MAX_GRAPH_COORDINATE, saved.y)) : fallback.y;
    return { id: object.id, name: object.name, kind: object.kind, x, y, object, relationshipCount: index.relationshipCounts.get(object.id) ?? 0 };
  });
  const edges: ProjectedGraphEdge[] = [];
  // Scan all valid relationships so an early hidden edge cannot starve later visible edges.
  for (const relationship of index.validRelationships) {
    if (!fullOverview && edges.length >= maxEdges) break;
    if (!visibleIds.has(relationship.fromObjectId) || !visibleIds.has(relationship.toObjectId)) continue;
    edges.push({ id: relationship.id, fromObjectId: relationship.fromObjectId,
      toObjectId: relationship.toObjectId, kind: relationship.kind, relationship });
  }
  return {
    worldId: record.snapshot.worldId, nodes, edges,
    diagnostics: index.diagnostics,
    omittedNodes: Math.max(0, eligibleObjects.length - nodes.length),
    hiddenUnconnectedNodes,
    omittedEdges: record.snapshot.relationships.length - edges.length,
    hiddenRelationships: index.validRelationships.length - edges.length,
    invalidRelationships: index.invalidRelationships,
    examinedRelationships: record.snapshot.relationships.length,
    omittedDiagnostics: Math.max(0, index.invalidRelationships - index.diagnostics.length),
    unexaminedRelationships: 0,
  };
}
