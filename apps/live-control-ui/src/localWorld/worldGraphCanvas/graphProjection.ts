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
  /** Overview ignores budgets; an explicit focus still uses bounded exploration. */
  readonly fullCorpus?: boolean;
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

export type GraphFallbackPositions = ReadonlyMap<LocalWorldObject["id"], Readonly<{ x: number; y: number }>>;

function coordinate(value: number): number {
  return Math.max(0, Math.min(MAX_GRAPH_COORDINATE, value));
}

/**
 * Build once per loaded snapshot, never per camera change or focused subset.
 * Components use only real edges. Isolated objects occupy a separate region,
 * remaining individual objects. Prior World-local fallbacks retain existing
 * positions across revisions/additions; removed IDs are discarded. Automatic
 * 144px staggered slots fit up to 1,927 individuals in the finite domain. Larger
 * corpora reduce spacing, and arbitrary crowded retained layouts may overlap;
 * positions are never hidden or silently moved to claim unlimited capacity.
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
    if (!adjacency.get(id)!.length) {
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
  const domain = MAX_GRAPH_COORDINATE - 160;
  const rowRatio = Math.sqrt(3) / 2;
  // 144px centers leave 32px between 112px bubbles. The 128px exclusion
  // distance below also protects additions against arbitrary retained positions.
  let spacing = 144;
  const dimensions = () => ({
    columns: Math.floor((domain - spacing / 2) / spacing) + 1,
    rows: Math.floor(domain / (spacing * rowRatio)) + 1,
  });
  let size = dimensions();
  // No finite domain can promise fixed separation for unlimited nodes. Beyond
  // nominal capacity (1,927), reduce spacing, never omit an individual object.
  for (let attempt = 0; attempt < 8 && size.columns * size.rows < ids.length; attempt += 1) {
    spacing *= Math.sqrt(size.columns * size.rows / ids.length) * 0.99;
    size = dimensions();
  }
  if (size.columns * size.rows < ids.length) {
    spacing = domain / (Math.ceil(Math.sqrt(ids.length)) + 1);
    size = dimensions();
  }
  const minimumSeparation = Math.min(128, spacing * 128 / 144);
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
  const capacity = size.columns * size.rows;
  const gap = ids.length + (groups.length - 1) * 2 <= capacity ? 2 : 0;
  const budget = ids.length + Math.max(0, groups.length - 1) * gap;
  const columns = Math.min(size.columns, Math.max(2, Math.ceil(Math.sqrt(budget * rowRatio)), Math.ceil(budget / size.rows)));
  function slotPoint(slot: number, width: number): Point {
    const row = Math.floor(slot / width);
    const column = row % 2 === 0 ? slot % width : width - 1 - slot % width;
    return { x: 80 + (column + (row % 2) / 2) * spacing, y: 80 + row * spacing * rowRatio };
  }
  const candidates = Array.from({ length: capacity }, (_, slot) => slotPoint(slot, size.columns));
  let slot = 0;
  let remaining = ids.length;
  for (const group of groups) {
    if (group === isolated && slot > 0) {
      // A separate final band makes the absence of connections legible, without
      // inventing an aggregate or a relationship among the isolated individuals.
      const nextBand = (Math.floor(slot / columns) + 2) * columns;
      if (nextBand + remaining <= columns * size.rows) slot = nextBand;
    }
    for (const id of group) {
      const desired = slotPoint(slot, columns);
      if (!result.has(id)) {
        let point = desired;
        if (!available(point)) {
          let nearest: Point | undefined;
          let distance = Infinity;
          for (const candidate of candidates) {
            const squared = (candidate.x - desired.x) ** 2 + (candidate.y - desired.y) ** 2;
            if (squared < distance && available(candidate)) { nearest = candidate; distance = squared; }
          }
          // Arbitrarily crowded retained positions may exhaust the fixed domain.
          // Retention wins: keep all objects visible rather than moving prior
          // positions or claiming unlimited collision-free capacity.
          point = nearest ?? desired;
        }
        result.set(id, point);
        occupy(point);
      }
      slot += 1;
      remaining -= 1;
    }
    slot += gap;
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
  let visibleObjects = fullOverview ? objects : objects.slice(0, maxNodes);
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
    return { id: object.id, name: object.name, kind: object.kind, x, y, object };
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
    omittedNodes: Math.max(0, objects.length - nodes.length),
    omittedEdges: record.snapshot.relationships.length - edges.length,
    hiddenRelationships: index.validRelationships.length - edges.length,
    invalidRelationships: index.invalidRelationships,
    examinedRelationships: record.snapshot.relationships.length,
    omittedDiagnostics: Math.max(0, index.invalidRelationships - index.diagnostics.length),
    unexaminedRelationships: 0,
  };
}
