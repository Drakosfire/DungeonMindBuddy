import type { NativeGraphEntity } from "../api/nativeGraphInspection";

export type NativeObjectKind = "person" | "location" | "event";

export interface NativeGraphNode {
  readonly id: string;
  readonly name: string;
  readonly kind: string;
}

export interface NativeGraphEdge {
  readonly id: string;
  readonly source_id: string;
  readonly target_id: string;
  readonly predicate: string;
}

export interface NativeGraphCapabilities {
  readonly create: boolean;
  readonly connect: boolean;
  readonly rename: boolean;
  readonly delete: boolean;
  /** The exact typed object kinds this demo profile currently accepts. */
  readonly object_kinds: readonly NativeObjectKind[];
  /** Descriptor-approved labels usable by the managed connector. Absent in legacy demo APIs. */
  readonly allowed_predicates?: readonly string[];
  /** True only when the active native descriptor accepts custom predicate labels. */
  readonly allows_custom_predicates?: boolean;
}

/** How much of the server-owned native catalogue was examined for this read. */
export interface NativeGraphCompleteness {
  readonly status: "complete" | "partial";
  readonly listed_entities: number;
  readonly omitted_entities: number;
  readonly unexamined_entities: number;
  readonly listed_assertions: number;
  readonly omitted_assertions: number;
  readonly unexamined_assertions: number;
  readonly reasons: readonly string[];
}

export interface NativeGraph {
  readonly world_id: string;
  readonly revision_id: string;
  readonly graph_sha256: string;
  readonly nodes: readonly NativeGraphNode[];
  readonly edges: readonly NativeGraphEdge[];
  readonly storage: "postgres";
  readonly limitations: readonly string[];
  readonly capabilities: NativeGraphCapabilities;
  /** Optional for the original standalone and guest APIs. Managed reads report it. */
  readonly completeness?: NativeGraphCompleteness;
}

export interface CreateObjectRequest {
  readonly operation_id: string;
  readonly expected_revision_id: string;
  readonly kind: "create_object";
  readonly name: string;
  readonly object_kind: NativeObjectKind;
}

export interface ConnectRequest {
  readonly operation_id: string;
  readonly expected_revision_id: string;
  readonly kind: "connect";
  readonly source_id: string;
  readonly target_id: string;
  readonly predicate: string;
}

export type NativePrepareRequest = CreateObjectRequest | ConnectRequest;

export interface PreparedOperation {
  readonly status: "prepared";
  readonly operation_id: string;
  readonly parent_revision_id: string;
  readonly review: { readonly summary: string };
}

export interface AlreadyExistsResult {
  readonly status: "already_exists";
  readonly message: string;
  readonly graph: NativeGraph;
}

export type PrepareResult = PreparedOperation | AlreadyExistsResult;

export interface CommittedResult {
  readonly status: "committed";
  readonly graph: NativeGraph;
  /** Exact durable ID from the verified native receipt, only present for committed creates. */
  readonly created_node_id?: string;
}

export type ConfirmResult = CommittedResult
  | { readonly status: "unknown"; readonly message: string; readonly operation_id?: string }
  | { readonly status: "rejected"; readonly code: string; readonly error: string; readonly operation_id?: string };

export type OperationLookupResult =
  | { readonly status: "prepared"; readonly operation_id: string; readonly parent_revision_id?: string; readonly review?: { readonly summary: string } }
  | { readonly status: "committed"; readonly operation_id: string; readonly graph?: NativeGraph; readonly created_node_id?: string }
  | { readonly status: "not_found"; readonly operation_id: string }
  | { readonly status: "rejected"; readonly operation_id: string; readonly code: string; readonly error: string }
  | { readonly status: "unknown"; readonly operation_id: string; readonly recovery_action?: "retry_prepare" };

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
type CapabilityReader = () => string;
/**
 * Transport injection keeps the native DTO validation shared while allowing
 * Buddy to establish its own browser-scoped session and CSRF header.
 */
export type NativeGraphDemoTransport = (path: string, init: RequestInit) => Promise<Response>;

export interface NativeGraphDemoApi {
  readGraph(): Promise<NativeGraph>;
  /** Read native records from this exact returned graph snapshot, when supported. */
  inspectNode?(graph: NativeGraph, nodeId: string, signal?: AbortSignal): Promise<NativeGraphEntity>;
  prepare(input: NativePrepareRequest): Promise<PrepareResult>;
  confirm(operationId: string): Promise<ConfirmResult>;
  readOperation(operationId: string): Promise<OperationLookupResult>;
}

export class NativeGraphDemoApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "NativeGraphDemoApiError";
    this.code = code;
    this.status = status;
  }
}

const NATIVE_OBJECT_KINDS: readonly NativeObjectKind[] = ["person", "location", "event"];

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNativeGraph(value: unknown): value is NativeGraph {
  if (!record(value) || typeof value.world_id !== "string" || !value.world_id
    || typeof value.revision_id !== "string" || !value.revision_id
    || typeof value.graph_sha256 !== "string" || value.storage !== "postgres"
    || !Array.isArray(value.nodes) || !Array.isArray(value.edges) || !Array.isArray(value.limitations)
    || !value.limitations.every((item) => typeof item === "string") || !record(value.capabilities)) return false;
  if (!value.nodes.every((node) => record(node) && typeof node.id === "string" && Boolean(node.id)
    && typeof node.name === "string" && typeof node.kind === "string")) return false;
  if (!value.edges.every((edge) => record(edge) && typeof edge.id === "string" && Boolean(edge.id)
    && typeof edge.source_id === "string" && typeof edge.target_id === "string" && typeof edge.predicate === "string")) return false;
  const capabilities = value.capabilities;
  if (typeof capabilities.create !== "boolean" || typeof capabilities.connect !== "boolean"
    || typeof capabilities.rename !== "boolean" || typeof capabilities.delete !== "boolean"
    || !Array.isArray(capabilities.object_kinds)
    || !capabilities.object_kinds.every((kind) => NATIVE_OBJECT_KINDS.includes(kind as NativeObjectKind))) return false;
  if ((capabilities.allowed_predicates === undefined) !== (capabilities.allows_custom_predicates === undefined)) return false;
  if (capabilities.allowed_predicates !== undefined && (!Array.isArray(capabilities.allowed_predicates)
    || !capabilities.allowed_predicates.every((predicate) => typeof predicate === "string" && Boolean(predicate.trim()))
    || new Set(capabilities.allowed_predicates).size !== capabilities.allowed_predicates.length
    || typeof capabilities.allows_custom_predicates !== "boolean")) return false;
  if (value.completeness !== undefined) {
    if (!record(value.completeness)) return false;
    const completeness = value.completeness;
    if ((completeness.status !== "complete" && completeness.status !== "partial")
      || !Number.isSafeInteger(completeness.listed_entities) || (completeness.listed_entities as number) < 0
      || !Number.isSafeInteger(completeness.omitted_entities) || (completeness.omitted_entities as number) < 0
      || !Number.isSafeInteger(completeness.unexamined_entities) || (completeness.unexamined_entities as number) < 0
      || !Number.isSafeInteger(completeness.listed_assertions) || (completeness.listed_assertions as number) < 0
      || !Number.isSafeInteger(completeness.omitted_assertions) || (completeness.omitted_assertions as number) < 0
      || !Number.isSafeInteger(completeness.unexamined_assertions) || (completeness.unexamined_assertions as number) < 0
      || !Array.isArray(completeness.reasons) || !completeness.reasons.every((reason) => typeof reason === "string")) return false;
    if (completeness.status === "complete" && (
      completeness.omitted_entities !== 0 || completeness.unexamined_entities !== 0
      || completeness.omitted_assertions !== 0 || completeness.unexamined_assertions !== 0
    )) return false;
  }
  return true;
}

function invalidResponse(): NativeGraphDemoApiError {
  return new NativeGraphDemoApiError("The native graph service returned an incomplete or unsupported response.", "invalid_response", 200);
}

function readCapabilityFromDocument(): string {
  if (typeof document === "undefined") return "";
  return document.querySelector<HTMLMetaElement>('meta[name="native-demo-capability"]')?.content.trim() ?? "";
}

function errorFromBody(body: unknown, status: number): NativeGraphDemoApiError {
  const candidate = body && typeof body === "object" ? body as Record<string, unknown> : {};
  const message = typeof candidate.error === "string" && candidate.error.trim()
    ? candidate.error
    : `The native graph service returned HTTP ${status}.`;
  const code = typeof candidate.code === "string" && candidate.code.trim() ? candidate.code : "http_error";
  return new NativeGraphDemoApiError(message, code, status);
}

export function createNativeGraphDemoApi(options: {
  readonly fetcher?: FetchLike;
  readonly readCapability?: CapabilityReader;
  readonly transport?: NativeGraphDemoTransport;
} = {}): NativeGraphDemoApi {
  const fetcher = options.fetcher ?? ((input, init) => globalThis.fetch(input, init));
  const readCapability = options.readCapability ?? readCapabilityFromDocument;
  const transport = options.transport;

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined) headers.set("Content-Type", "application/json");

    if (!transport) {
      const capability = readCapability();
      if (!capability) {
        throw new NativeGraphDemoApiError(
          "The native demo capability is missing from this page. Open the demo from its local DungeonMind service.",
          "missing_capability",
          0,
        );
      }
      headers.set("X-Demo-Capability", capability);
    }

    let response: Response;
    try {
      const requestInit: RequestInit = {
        ...init,
        headers,
        cache: "no-store",
        credentials: "same-origin",
      };
      response = transport
        ? await transport(path, requestInit)
        : await fetcher(path, requestInit);
    } catch (error) {
      throw new NativeGraphDemoApiError(
        error instanceof Error ? error.message : "The native graph service could not be reached.",
        "network_error",
        0,
      );
    }

    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) throw errorFromBody(body, response.status);
    if (body === null) throw new NativeGraphDemoApiError("The native graph service returned an unreadable response.", "invalid_response", response.status);
    return body as T;
  }

  return {
    async readGraph() {
      const value = await request<unknown>("/api/graph");
      if (!isNativeGraph(value)) throw invalidResponse();
      return value;
    },
    async prepare(input) {
      const value = await request<unknown>("/api/prepare", { method: "POST", body: JSON.stringify(input) });
      if (!record(value)) throw invalidResponse();
      if (value.status === "prepared" && value.operation_id === input.operation_id
        && typeof value.parent_revision_id === "string" && record(value.review) && typeof value.review.summary === "string") {
        return value as unknown as PreparedOperation;
      }
      if (value.status === "already_exists" && typeof value.message === "string" && isNativeGraph(value.graph)) {
        return value as unknown as AlreadyExistsResult;
      }
      throw invalidResponse();
    },
    async confirm(operationId) {
      const value = await request<unknown>("/api/confirm", {
        method: "POST",
        body: JSON.stringify({ operation_id: operationId }),
      });
      if (!record(value)) throw invalidResponse();
      if (value.operation_id !== undefined && value.operation_id !== operationId) throw invalidResponse();
      if (value.status === "committed" && isNativeGraph(value.graph)) {
        if (value.created_node_id !== undefined && (typeof value.created_node_id !== "string" || !value.created_node_id
          || !value.graph.nodes.some((node) => node.id === value.created_node_id))) throw invalidResponse();
        return value as unknown as CommittedResult;
      }
      if (value.status === "unknown" && typeof value.message === "string") return value as unknown as ConfirmResult;
      if (value.status === "rejected" && typeof value.code === "string" && typeof value.error === "string") return value as unknown as ConfirmResult;
      throw invalidResponse();
    },
    async readOperation(operationId) {
      const value = await request<unknown>(`/api/operations/${encodeURIComponent(operationId)}`);
      if (!record(value) || value.operation_id !== operationId) throw invalidResponse();
      if (value.status === "prepared" && (value.review === undefined || record(value.review) && typeof value.review.summary === "string")) {
        return value as unknown as OperationLookupResult;
      }
      if (value.status === "committed" && (value.graph === undefined || isNativeGraph(value.graph))) {
        if (value.created_node_id !== undefined && (typeof value.created_node_id !== "string" || !value.created_node_id
          || value.graph !== undefined && !value.graph.nodes.some((node) => node.id === value.created_node_id))) throw invalidResponse();
        return value as unknown as OperationLookupResult;
      }
      if (value.status === "not_found") return value as unknown as OperationLookupResult;
      if (value.status === "unknown" && (value.recovery_action === undefined || value.recovery_action === "retry_prepare")) {
        return value as unknown as OperationLookupResult;
      }
      if (value.status === "rejected" && typeof value.code === "string" && typeof value.error === "string") return value as unknown as OperationLookupResult;
      throw invalidResponse();
    },
  };
}
