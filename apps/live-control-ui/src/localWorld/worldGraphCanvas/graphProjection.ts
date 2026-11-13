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
  readonly omittedDiagnostics: number;
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

export function graphBubbleRadius(count: number): number {
  const degree = Number.isFinite(count) ? Math.max(0, count) : count === Infinity ? 40 : 0;
  return degree === 0 ? 18 : 24 * Math.sqrt(Math.min(degree, 40));
}

export interface GraphFallbackOptions {
  readonly savedPositions?: Readonly<Record<string, Readonly<{ x: number; y: number }>>>;
}

/**
 * Deterministic, one-shot packing around real hubs. Pins are fixed obstacles;
 * unpinned objects adapt to topology/radius/pin changes, not previous animation
 * state. The caller caches by those inputs, independently of camera/selection.
 * Candidate work is bounded. At extreme density or conflicting pins, finite
 * coordinates/identity take precedence over an impossible separation guarantee.
 */
export function createGraphFallbackPositions(
  index: LocalWorldGraphIndex,
  _previousPositions?: GraphFallbackPositions,
  options: GraphFallbackOptions = {},
): GraphFallbackPositions {
  type Id = LocalWorldObject["id"];
  type Point = { x: number; y: number };
  type Bubble = Point & { radius: number; id: Id };
  const ids = [...index.objects.keys()].sort();
  const degree = (id: Id) => index.relationshipCounts.get(id) ?? 0;
  const radius = (id: Id) => graphBubbleRadius(degree(id));
  const rank = (a: Id, b: Id) => degree(b) - degree(a) || (a < b ? -1 : a > b ? 1 : 0);
  const adjacency = new Map(ids.map(id => [id, [...new Set(index.neighbors.get(id) ?? [])].filter(other => other !== id).sort(rank)]));
  const visited = new Set<Id>();
  const groups: Id[][] = [];
  const isolated: Id[] = [];
  for (const id of ids) {
    if (visited.has(id)) continue;
    if (!degree(id)) { isolated.push(id); visited.add(id); continue; }
    const component = [id];
    visited.add(id);
    for (let cursor = 0; cursor < component.length; cursor += 1) {
      for (const neighbor of adjacency.get(component[cursor])!) {
        if (!visited.has(neighbor)) { visited.add(neighbor); component.push(neighbor); }
      }
    }
    component.sort(rank);
    const ordered = [component[0]];
    const discovered = new Set(ordered);
    for (let cursor = 0; cursor < ordered.length; cursor += 1) {
      for (const neighbor of adjacency.get(ordered[cursor])!) {
        if (!discovered.has(neighbor)) { discovered.add(neighbor); ordered.push(neighbor); }
      }
    }
    groups.push(ordered);
  }
  groups.sort((a, b) => b.length - a.length || rank(a[0], b[0]));
  const result = new Map<Id, Point>();
  const buckets = new Map<string, Bubble[]>();
  // One neighboring cell covers two maximum radii (~304) plus the 4-unit gap.
  const cell = 320;
  const key = (x: number, y: number) => `${x}:${y}`;
  function occupy(id: Id, point: Point) {
    result.set(id, point);
    const k = key(Math.floor(point.x / cell), Math.floor(point.y / cell));
    const list = buckets.get(k) ?? [];
    list.push({ ...point, radius: radius(id), id });
    buckets.set(k, list);
  }
  function available(point: Point, r: number): boolean {
    if (point.x < 0 || point.y < 0 || point.x > MAX_GRAPH_COORDINATE || point.y > MAX_GRAPH_COORDINATE) return false;
    const bx = Math.floor(point.x / cell), by = Math.floor(point.y / cell);
    for (let x = bx - 1; x <= bx + 1; x += 1) {
      for (let y = by - 1; y <= by + 1; y += 1) {
        for (const other of buckets.get(key(x, y)) ?? []) {
          if ((point.x - other.x) ** 2 + (point.y - other.y) ** 2 < (r + other.radius + 4) ** 2 - 1e-7) return false;
        }
      }
    }
    return true;
  }
  for (const id of ids) {
    const pin = options.savedPositions?.[id];
    if (pin && Number.isFinite(pin.x) && Number.isFinite(pin.y)) occupy(id, { x: coordinate(pin.x), y: coordinate(pin.y) });
  }
  // A separate monotonic emergency grid bounds work even for exhausted domains.
  let emergencyCursor = 0;
  const emergencyColumns = Math.max(2, Math.ceil(Math.sqrt(ids.length)));
  function emergency(): Point {
    const slot = emergencyCursor++;
    return { x: 40 + (slot % emergencyColumns) * 5920 / emergencyColumns,
      y: 40 + Math.floor(slot / emergencyColumns) * 5920 / emergencyColumns };
  }
  let rootCursor = 0;
  const origin = { x: 640, y: 640 };
  function placeRoot(r: number): Point {
    for (let attempt = 0; attempt < 2048; attempt += 1) {
      const slot = rootCursor++;
      const distance = 70 * Math.sqrt(slot);
      const angle = slot * 2.399963229728653;
      const point = { x: origin.x + distance * Math.cos(angle), y: origin.y + distance * Math.sin(angle) };
      if (available(point, r)) return point;
    }
    return emergency();
  }
  for (const group of groups) {
    const rootId = group[0];
    if (!result.has(rootId)) occupy(rootId, placeRoot(radius(rootId)));
    const root = result.get(rootId)!;
    for (const id of group.slice(1)) {
      if (result.has(id)) continue;
      const neighbors = adjacency.get(id)!.filter(other => result.has(other));
      const scoringNeighbors = neighbors.slice(0, 32);
      const anchorId = neighbors[0] ?? rootId;
      const anchor = result.get(anchorId)!;
      const r = radius(id);
      const outward = Math.atan2(anchor.y - root.y, anchor.x - root.x);
      let chosen: Point | undefined;
      for (let shell = 0; shell < 16 && !chosen; shell += 1) {
        const distance = r + radius(anchorId) + 4.1 + shell * 12;
        let best = Infinity;
        for (let step = 0; step < 48; step += 1) {
          const angle = outward + step * 2 * Math.PI / 48;
          const point = { x: anchor.x + distance * Math.cos(angle), y: anchor.y + distance * Math.sin(angle) };
          if (!available(point, r)) continue;
          // All admitted neighbors contribute, with bounded work for dense hubs.
          let score = 0;
          for (const neighbor of scoringNeighbors) {
            const other = result.get(neighbor)!;
            score += (point.x - other.x) ** 2 + (point.y - other.y) ** 2;
          }
          score += 0.02 * ((point.x - root.x) ** 2 + (point.y - root.y) ** 2);
          if (score < best) { best = score; chosen = point; }
        }
      }
      occupy(id, chosen ?? placeRoot(r));
    }
  }
  // Bounded settling pulls each real component inward without moving pins or
  // sacrificing radius separation. Rebuild only affected spatial-hash buckets.
  for (let pass = 0; pass < 24; pass += 1) {
    let moved = false;
    for (const group of groups) {
      const root = result.get(group[0])!;
      for (const id of group.slice(1).reverse()) {
        const pin = options.savedPositions?.[id];
        if (pin && Number.isFinite(pin.x) && Number.isFinite(pin.y)) continue;
        const point = result.get(id)!;
        const distance = Math.hypot(point.x - root.x, point.y - root.y);
        if (distance < 1) continue;
        const oldKey = key(Math.floor(point.x / cell), Math.floor(point.y / cell));
        buckets.set(oldKey, buckets.get(oldKey)!.filter(bubble => bubble.id !== id));
        let settled = point;
        for (const step of [32, 16, 8, 4]) {
          if (step >= distance) continue;
          const candidate = { x: point.x + (root.x - point.x) * step / distance, y: point.y + (root.y - point.y) * step / distance };
          if (available(candidate, radius(id))) { settled = candidate; moved = true; break; }
        }
        occupy(id, settled);
      }
    }
    if (!moved) break;
  }
  // Isolates do not set connected-component spacing or placement. Their own
  // revealable band follows the connected bubbles; extreme counts shrink it.
  let connectedBottom = 0;
  for (const [id, point] of result) {
    if (degree(id) > 0) connectedBottom = Math.max(connectedBottom, point.y + radius(id));
  }
  const top = Math.min(5700, connectedBottom + 100);
  const height = MAX_GRAPH_COORDINATE - top - 40;
  const columns = Math.max(1, Math.ceil(Math.sqrt(isolated.length * 5920 / height)));
  const rows = Math.max(1, Math.ceil(isolated.length / columns));
  const spacing = Math.min(42, 5920 / columns, height / rows);
  let isolateCursor = 0;
  for (const id of isolated) {
    if (result.has(id)) continue;
    let point: Point = emergency();
    for (let attempt = 0; attempt < 64; attempt += 1) {
      const slot = isolateCursor++;
      const candidate = { x: 40 + (slot % columns) * spacing, y: top + Math.floor(slot / columns) * spacing };
      if (candidate.y > MAX_GRAPH_COORDINATE) break;
      point = candidate;
      if (spacing < 40 || available(candidate, radius(id))) break;
    }
    occupy(id, point);
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
  let fallbackPositions = options.fullCorpus ? options.fallbackPositions ?? createGraphFallbackPositions(index, undefined, { savedPositions: record.layout.positions }) : undefined;
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
      fallbackPositions = createGraphFallbackPositions(index, fallbackPositions, { savedPositions: record.layout.positions });
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
    omittedDiagnostics: Math.max(0, index.invalidRelationships - index.diagnostics.length),
  };
}
