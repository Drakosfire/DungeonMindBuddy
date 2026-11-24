import type { NativeGraph, NativeGraphDemoApi } from "../nativeGraphDemo/nativeGraphDemoApi";

type Source = { id: string; text: string; evidence_role: "support" | "context" };
type Node = { id: string; label: string; kind: string; name_basis: string; kind_basis: string; name_temporal?: string; kind_temporal?: string; name_citations: string[]; kind_citations: string[] };
type Edge = { id: string; source: string; target: string; label: string; basis: string; temporal: string; citations: string[] };
export type GuestGraphRelease = { release_id: string; manifest: { graph: { nodes: Node[]; edges: Edge[] }; sources: Source[] } };
const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === "string" && value.length > 0;
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(text);
export const guestGraphTerm = (value: string) => value.startsWith("dnd5e · ") && value.length > 8 ? value.slice(8) : value;

/** Fail closed before adapting a public copy to the product graph. */
export function parseGuestGraphRelease(value: unknown): GuestGraphRelease {
  if (!record(value) || !text(value.release_id) || !record(value.manifest) || !record(value.manifest.graph)
    || !Array.isArray(value.manifest.graph.nodes) || !Array.isArray(value.manifest.graph.edges) || !Array.isArray(value.manifest.sources)) throw new Error("Invalid shared graph");
  const { nodes, edges } = value.manifest.graph;
  const { sources } = value.manifest;
  if (nodes.length > 500 || edges.length > 1000 || sources.length > 500) throw new Error("Invalid shared graph");
  if (!sources.every((s) => record(s) && text(s.id) && typeof s.text === "string" && (s.evidence_role === "support" || s.evidence_role === "context"))) throw new Error("Invalid shared sources");
  if (!nodes.every((n) => record(n) && text(n.id) && text(n.label) && text(n.kind) && text(n.name_basis) && text(n.kind_basis) && (n.name_temporal === undefined || text(n.name_temporal)) && (n.kind_temporal === undefined || text(n.kind_temporal)) && strings(n.name_citations) && strings(n.kind_citations))) throw new Error("Invalid shared points");
  if (!edges.every((e) => record(e) && text(e.id) && text(e.source) && text(e.target) && text(e.label) && text(e.basis) && text(e.temporal) && strings(e.citations))) throw new Error("Invalid shared connections");
  const sourceIds = new Set(sources.map((s) => s.id));
  const nodeIds = new Set(nodes.map((n) => n.id));
  const edgeIds = new Set(edges.map((e) => e.id));
  if (sourceIds.size !== sources.length || nodeIds.size !== nodes.length || edgeIds.size !== edges.length
    || nodes.some((n) => [...n.name_citations, ...n.kind_citations].some((id: string) => !sourceIds.has(id)))
    || edges.some((e) => !nodeIds.has(e.source) || !nodeIds.has(e.target) || e.citations.some((id: string) => !sourceIds.has(id)))) throw new Error("Incomplete shared graph");
  return value as unknown as GuestGraphRelease;
}

export async function createGuestGraphApi(publicId: string, copy: GuestGraphRelease): Promise<NativeGraphDemoApi> {
  const bytes = new TextEncoder().encode(JSON.stringify(copy.manifest.graph));
  const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  const graph: NativeGraph = {
    world_id: `guest:${publicId}:${copy.release_id}`, revision_id: copy.release_id, graph_sha256: digest, storage: "memory",
    nodes: copy.manifest.graph.nodes.map((node) => ({ id: node.id, name: node.label, kind: guestGraphTerm(node.kind) })),
    edges: copy.manifest.graph.edges.map((edge) => ({ id: edge.id, source_id: edge.source, target_id: edge.target, predicate: guestGraphTerm(edge.label) })),
    capabilities: { create: false, connect: false, rename: false, delete: false, object_kinds: [] }, limitations: [],
  };
  const unsupported = async (): Promise<never> => { throw new Error("The shared copy is read-only in Graph."); };
  return { readGraph: async (signal) => { if (signal?.aborted) throw new DOMException("Aborted", "AbortError"); return graph; }, prepare: unsupported, confirm: unsupported, readOperation: unsupported };
}
