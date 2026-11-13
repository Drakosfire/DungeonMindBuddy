import { authenticatedApiFetch, getNativeGraphCatalog } from "../api/liveApi";
import { isCatalogForWorld, sameInspectionPin, type InspectionPin, type NativeGraphEntity } from "../api/nativeGraphInspection";
import {
  createNativeGraphDemoApi,
  NativeGraphDemoApiError,
  type NativeGraph,
  type NativeGraphDemoApi,
  type NativeGraphDemoTransport,
  type NativePrepareRequest,
} from "./nativeGraphDemoApi";

const BASE = "/api/live/native-graph-explorer";
const GRAPH_PATH = `${BASE}/graph`;
const PREPARE_PATH = `${BASE}/prepare`;
const CONFIRM_PATH = `${BASE}/confirm`;
const OPERATIONS_READ_PATH = `${BASE}/operations/read`;
const INSPECTION_READ_PATH = "/api/live/native-graph-inspection/read";

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

interface ManagedBinding {
  readonly managedWorldId: string;
  readonly nativeWorldId: string;
  readonly bindingVersion: number;
}

interface GraphEnvelope {
  readonly schema: "dmb_native_graph_explorer_v1";
  readonly managed_world_id: string;
  readonly native_world_id: string;
  readonly binding_version: number;
  readonly graph: NativeGraph;
}

export interface ManagedNativeGraphApiClient {
  readonly api: NativeGraphDemoApi;
  /** Invalidates pending replies when this verified World leaves the mounted route. */
  invalidate(): void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function invalidResponse(message = "The managed graph response did not match the selected World."): Response {
  return jsonResponse({ error: message, code: "invalid_managed_world_response" }, 502);
}

function errorFromResponse(response: Response, body: unknown): Response {
  if (isRecord(body) && nonEmptyString(body.error) && nonEmptyString(body.code)) return response;
  const detail = isRecord(body) ? body.detail : null;
  const message = isRecord(detail) && nonEmptyString(detail.message)
    ? detail.message
    : isRecord(detail) && nonEmptyString(detail.error)
      ? detail.error
      : isRecord(body) && nonEmptyString(body.message)
        ? body.message
        : `The managed graph service returned HTTP ${response.status}.`;
  const code = isRecord(detail) && nonEmptyString(detail.code)
    ? detail.code
    : isRecord(body) && nonEmptyString(body.code)
      ? body.code
      : "managed_graph_error";
  return jsonResponse({ error: message, code }, response.status);
}

async function responseBody(response: Response): Promise<unknown> {
  return response.clone().json().catch(() => null);
}

function isInspectionPin(value: unknown): value is InspectionPin {
  return isRecord(value)
    && nonEmptyString(value.managed_world_id)
    && value.scope_mode === "world"
    && value.campaign_id === null
    && nonEmptyString(value.native_world_id)
    && Number.isSafeInteger(value.binding_version)
    && (value.binding_version as number) >= 1
    && nonEmptyString(value.revision_id);
}

function isNativeAssertion(value: unknown): boolean {
  if (!isRecord(value) || !nonEmptyString(value.assertion_id)
    || !nonEmptyString(value.subject_entity_id) || !nonEmptyString(value.predicate)
    || !isRecord(value.value) || !isRecord(value.metadata)) return false;
  const assertionValue = value.value;
  if (assertionValue.kind === "literal") {
    if (!("value" in assertionValue)) return false;
  } else if (assertionValue.kind === "term_ref") {
    if (!nonEmptyString(assertionValue.term)) return false;
  } else if (assertionValue.kind === "entity_ref") {
    if (!nonEmptyString(assertionValue.entity_id)) return false;
  } else return false;
  const metadata = value.metadata;
  return Array.isArray(metadata.scope)
    && metadata.scope.every((item) => isRecord(item) && typeof item.axis === "string" && typeof item.value === "string")
    && typeof metadata.epistemic_basis === "string"
    && typeof metadata.claim_mode === "string"
    && typeof metadata.standing === "string"
    && Array.isArray(metadata.evidence_ref_ids)
    && metadata.evidence_ref_ids.every((id) => typeof id === "string")
    && Array.isArray(metadata.domain_metadata);
}

function isNativeGraphEntityForPin(value: unknown, pin: InspectionPin): value is NativeGraphEntity {
  if (!isRecord(value) || value.schema !== "dmb_native_graph_entity_v1"
    || !isInspectionPin(value.scope) || !sameInspectionPin(value.scope, pin)
    || !isRecord(value.entity) || typeof value.entity.found !== "boolean"
    || !Array.isArray(value.entity.assertions) || !value.entity.assertions.every(isNativeAssertion)
    || !Array.isArray(value.entity.evidence)
    || !value.entity.evidence.every((item) => isRecord(item)
      && nonEmptyString(item.evidence_ref_id) && typeof item.evidence_role === "string")
    || !isRecord(value.entity.completeness)) return false;
  const completeness = value.entity.completeness;
  return (completeness.status === "complete" || completeness.status === "partial")
    && (completeness.reason === null || typeof completeness.reason === "string");
}

function abortError(): DOMException {
  return new DOMException("The inspection request was cancelled.", "AbortError");
}

function isAbortError(error: unknown): boolean {
  return isRecord(error) && error.name === "AbortError";
}

function graphEnvelope(value: unknown, managedWorldId: string): GraphEnvelope | null {
  if (!isRecord(value) || value.schema !== "dmb_native_graph_explorer_v1"
    || value.managed_world_id !== managedWorldId
    || !nonEmptyString(value.native_world_id) || !Number.isSafeInteger(value.binding_version)
    || (value.binding_version as number) < 1
    || !isRecord(value.graph) || value.graph.world_id !== value.native_world_id) return null;
  return value as unknown as GraphEnvelope;
}

function bindingFromEnvelope(envelope: GraphEnvelope): ManagedBinding {
  return {
    managedWorldId: envelope.managed_world_id,
    nativeWorldId: envelope.native_world_id,
    bindingVersion: envelope.binding_version,
  };
}

function sameBinding(left: ManagedBinding, right: ManagedBinding): boolean {
  return left.managedWorldId === right.managedWorldId
    && left.nativeWorldId === right.nativeWorldId
    && left.bindingVersion === right.bindingVersion;
}

function operationIdentityMatches(
  value: Record<string, unknown>,
  managedWorldId: string,
  binding: ManagedBinding | null,
): boolean {
  if (value.schema !== "dmb_native_graph_explorer_v1"
    || !nonEmptyString(value.operation_id)
    || !nonEmptyString(value.managed_world_id) || !nonEmptyString(value.native_world_id)
    || !Number.isSafeInteger(value.binding_version) || (value.binding_version as number) < 1) return false;
  const candidate: ManagedBinding = {
    managedWorldId: value.managed_world_id,
    nativeWorldId: value.native_world_id,
    bindingVersion: value.binding_version as number,
  };
  return candidate.managedWorldId === managedWorldId && binding !== null && sameBinding(candidate, binding);
}

function withGraph(value: Record<string, unknown>, managedWorldId: string, binding: ManagedBinding | null): Record<string, unknown> | null {
  if (!operationIdentityMatches(value, managedWorldId, binding)) return null;
  const envelope = graphEnvelope(value.graph, managedWorldId);
  if (!envelope) return null;
  const receivedBinding = bindingFromEnvelope(envelope);
  if (binding && !sameBinding(receivedBinding, binding)) return null;
  if (!sameBinding(receivedBinding, binding ?? receivedBinding)) return null;
  return { ...value, graph: envelope.graph };
}

function requestRecord(init: RequestInit): Record<string, unknown> | null {
  if (typeof init.body !== "string") return null;
  try {
    const value: unknown = JSON.parse(init.body);
    return isRecord(value) ? value : null;
  } catch {
    return null;
  }
}

function decodeOperationId(path: string): string | null {
  const match = /^\/api\/operations\/([^/]+)$/.exec(path);
  if (!match) return null;
  try {
    const operationId = decodeURIComponent(match[1]);
    return nonEmptyString(operationId) ? operationId : null;
  } catch {
    return null;
  }
}

/**
 * A client is bound to one already-verified selected World. It translates the
 * common graph API into the exact managed explorer routes and never chooses a
 * native World, falls back to a playground, or retries a mutation itself.
 */
export function createManagedNativeGraphApi(
  managedWorldId: string,
  options: { readonly fetcher?: FetchLike } = {},
): ManagedNativeGraphApiClient {
  const fetcher = options.fetcher ?? (async (input, init) => {
    const result = await authenticatedApiFetch(String(input), init);
    return result.response;
  });
  let binding: ManagedBinding | null = null;
  let generation = 0;
  let invalidated = false;
  const activeControllers = new Set<AbortController>();
  const snapshotPins = new WeakMap<NativeGraph, {
    readonly pin: InspectionPin;
    readonly nodeIds: ReadonlySet<string>;
    readonly serializedGraph: string;
  }>();

  function invalidManagedGraph(message: string): NativeGraphDemoApiError {
    return new NativeGraphDemoApiError(message, "invalid_managed_world_response", 502);
  }

  function registerSnapshot(graph: NativeGraph, startedGeneration: number): NativeGraph {
    if (invalidated || startedGeneration !== generation) {
      throw invalidManagedGraph("The selected World changed before this graph snapshot could be used.");
    }
    if (!binding || graph.world_id !== binding.nativeWorldId || !nonEmptyString(graph.revision_id)) {
      throw invalidManagedGraph("The graph snapshot did not match the verified managed World binding.");
    }
    const pin: InspectionPin = Object.freeze({
      managed_world_id: binding.managedWorldId,
      native_world_id: binding.nativeWorldId,
      binding_version: binding.bindingVersion,
      scope_mode: "world",
      campaign_id: null,
      revision_id: graph.revision_id,
    });
    snapshotPins.set(graph, {
      pin,
      nodeIds: new Set(graph.nodes.map((node) => node.id)),
      serializedGraph: JSON.stringify(graph),
    });
    return graph;
  }

  function assertCurrentSnapshot(graph: NativeGraph, nodeId?: string): InspectionPin {
    if (invalidated) throw invalidManagedGraph("The selected World changed before this graph inspection completed.");
    const snapshot = snapshotPins.get(graph);
    if (!snapshot) throw invalidManagedGraph("This graph was not read from the currently selected managed World client.");
    let serializedGraph: string;
    try {
      serializedGraph = JSON.stringify(graph);
    } catch {
      throw invalidManagedGraph("The graph snapshot was modified after it was loaded.");
    }
    if (serializedGraph !== snapshot.serializedGraph) {
      throw invalidManagedGraph("The graph snapshot was modified after it was loaded.");
    }
    if (!binding || !sameInspectionPin(snapshot.pin, {
      managed_world_id: managedWorldId,
      native_world_id: binding.nativeWorldId,
      binding_version: binding.bindingVersion,
      scope_mode: "world",
      campaign_id: null,
      revision_id: graph.revision_id,
    }) || graph.world_id !== snapshot.pin.native_world_id || graph.revision_id !== snapshot.pin.revision_id) {
      throw invalidManagedGraph("The graph snapshot no longer matches its verified managed World pin.");
    }
    if (nodeId !== undefined && (!nonEmptyString(nodeId) || !snapshot.nodeIds.has(nodeId))) {
      throw invalidManagedGraph("The selected object is not part of this exact graph snapshot.");
    }
    return snapshot.pin;
  }

  async function throwInspectionResponseError(response: Response, body: unknown): Promise<never> {
    const normalized = await responseBody(errorFromResponse(response, body));
    const message = isRecord(normalized) && nonEmptyString(normalized.error)
      ? normalized.error
      : `The managed graph service returned HTTP ${response.status}.`;
    const code = isRecord(normalized) && nonEmptyString(normalized.code) ? normalized.code : "managed_graph_error";
    throw new NativeGraphDemoApiError(message, code, response.status);
  }

  async function send(path: string, init: RequestInit, startedGeneration: number): Promise<Response> {
    if (invalidated || startedGeneration !== generation) {
      return invalidResponse("The selected World changed before this managed graph request completed.");
    }
    const controller = new AbortController();
    const externalSignal = init.signal;
    const abortFromCaller = () => controller.abort(externalSignal?.reason);
    if (externalSignal?.aborted) abortFromCaller();
    else externalSignal?.addEventListener("abort", abortFromCaller, { once: true });
    activeControllers.add(controller);
    try {
      const response = await fetcher(path, {
        ...init,
        signal: controller.signal,
        cache: "no-store",
        redirect: "error",
      });
      if (invalidated || startedGeneration !== generation) {
        return invalidResponse("The selected World changed before this managed graph response was applied.");
      }
      return response;
    } finally {
      externalSignal?.removeEventListener("abort", abortFromCaller);
      activeControllers.delete(controller);
    }
  }

  const transport: NativeGraphDemoTransport = async (path, init) => {
    const startedGeneration = generation;
    const method = (init.method ?? "GET").toUpperCase();
    if (path === "/api/graph" && method === "GET") {
      const response = await send(GRAPH_PATH, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ managed_world_id: managedWorldId }),
        signal: init.signal,
      }, startedGeneration);
      const body = await responseBody(response);
      if (!response.ok) return errorFromResponse(response, body);
      const envelope = graphEnvelope(body, managedWorldId);
      if (!envelope) return invalidResponse();
      const receivedBinding = bindingFromEnvelope(envelope);
      if (binding && !sameBinding(binding, receivedBinding)) {
        return invalidResponse("The selected World’s native binding changed. Reload the World selection before continuing.");
      }
      binding = receivedBinding;
      return jsonResponse(envelope.graph, response.status);
    }

    if (path === "/api/prepare" && method === "POST") {
      const body = requestRecord(init);
      if (!body || !binding || body.kind !== "create_object" && body.kind !== "connect"
        || !nonEmptyString(body.operation_id) || !nonEmptyString(body.expected_revision_id)) {
        return invalidResponse("The managed World must be read before a write can be prepared.");
      }
      const input = body as unknown as NativePrepareRequest;
      const response = await send(PREPARE_PATH, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          ...input,
          managed_world_id: managedWorldId,
          native_world_id: binding.nativeWorldId,
          binding_version: binding.bindingVersion,
        }),
        signal: init.signal,
      }, startedGeneration);
      const value = await responseBody(response);
      if (!response.ok) return errorFromResponse(response, value);
      if (!isRecord(value)) return invalidResponse();
      if (value.status === "prepared") {
        if (value.operation_id !== input.operation_id
          || !operationIdentityMatches(value, managedWorldId, binding)) return invalidResponse();
        return jsonResponse(value, response.status);
      }
      if (value.status === "already_exists") {
        const mapped = withGraph(value, managedWorldId, binding);
        return mapped && value.operation_id === input.operation_id ? jsonResponse(mapped, response.status) : invalidResponse();
      }
      if (value.status === "committed") {
        const mapped = withGraph(value, managedWorldId, binding);
        if (!mapped || value.operation_id !== input.operation_id) return invalidResponse();
        return jsonResponse({
          error: "This operation is already committed. Checking the exact operation ID for its saved receipt.",
          code: "operation_already_committed",
        }, 409);
      }
      return invalidResponse("The managed graph service returned an unsupported preparation result.");
    }

    if (path === "/api/confirm" && method === "POST") {
      const body = requestRecord(init);
      const operationId = body?.operation_id;
      if (!body || !binding || !nonEmptyString(operationId)) {
        return invalidResponse("The selected World is not verified for this operation.");
      }
      const response = await send(CONFIRM_PATH, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ managed_world_id: managedWorldId, operation_id: operationId }),
        signal: init.signal,
      }, startedGeneration);
      const value = await responseBody(response);
      if (!response.ok) return errorFromResponse(response, value);
      if (!isRecord(value) || value.operation_id !== operationId
        || !operationIdentityMatches(value, managedWorldId, binding)) return invalidResponse();
      if (value.status === "committed") {
        const mapped = withGraph(value, managedWorldId, binding);
        return mapped ? jsonResponse(mapped, response.status) : invalidResponse();
      }
      if (value.status === "unknown" || value.status === "rejected") {
        return jsonResponse(value, response.status);
      }
      return invalidResponse("The managed graph service returned an unsupported confirmation result.");
    }

    const operationId = decodeOperationId(path);
    if (operationId && method === "GET") {
      if (!binding) return invalidResponse("The selected World is not verified for this operation.");
      const response = await send(OPERATIONS_READ_PATH, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ managed_world_id: managedWorldId, operation_id: operationId }),
        signal: init.signal,
      }, startedGeneration);
      const value = await responseBody(response);
      if (!response.ok) return errorFromResponse(response, value);
      if (!isRecord(value) || value.operation_id !== operationId
        || !operationIdentityMatches(value, managedWorldId, binding)) return invalidResponse();
      if (value.graph !== undefined) {
        const mapped = withGraph(value, managedWorldId, binding);
        return mapped ? jsonResponse(mapped, response.status) : invalidResponse();
      }
      if (["prepared", "committed", "unknown", "rejected", "not_found"].includes(String(value.status))) {
        return jsonResponse(value, response.status);
      }
      return invalidResponse("The managed graph service returned an unsupported operation status.");
    }

    return jsonResponse({ error: "The managed graph request is unsupported.", code: "unsupported_request" }, 400);
  };

  const baseApi = createNativeGraphDemoApi({ transport });
  const api: NativeGraphDemoApi = {
    async readGraph() {
      const startedGeneration = generation;
      return registerSnapshot(await baseApi.readGraph(), startedGeneration);
    },
    async prepare(input) {
      const startedGeneration = generation;
      const result = await baseApi.prepare(input);
      if (result.status === "already_exists") registerSnapshot(result.graph, startedGeneration);
      return result;
    },
    async confirm(operationId) {
      const startedGeneration = generation;
      const result = await baseApi.confirm(operationId);
      if (result.status === "committed") registerSnapshot(result.graph, startedGeneration);
      return result;
    },
    async readOperation(operationId) {
      const startedGeneration = generation;
      const result = await baseApi.readOperation(operationId);
      if (result.status === "committed" && result.graph) registerSnapshot(result.graph, startedGeneration);
      return result;
    },
    async readChronology(graph, signal) {
      const pin = assertCurrentSnapshot(graph);
      const catalogue = await getNativeGraphCatalog({
        managed_world_id: pin.managed_world_id, scope_mode: "world", campaign_id: null,
      }, signal);
      if (signal.aborted) throw abortError();
      assertCurrentSnapshot(graph);
      if (!isCatalogForWorld(catalogue, pin.managed_world_id) || !sameInspectionPin(pin, catalogue.scope)) {
        throw invalidManagedGraph("Chronology does not match the selected graph revision. Refresh the graph and try again.");
      }
      return catalogue;
    },
    async inspectNode(graph, nodeId, signal) {
      const pin = assertCurrentSnapshot(graph, nodeId);
      if (signal?.aborted) throw abortError();
      const startedGeneration = generation;
      let response: Response;
      try {
        response = await send(INSPECTION_READ_PATH, {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({ scope: pin, selection: { kind: "entity", entity_id: nodeId } }),
          signal,
        }, startedGeneration);
      } catch (error) {
        if (invalidated || startedGeneration !== generation) {
          throw invalidManagedGraph("The selected World changed before this graph inspection could be applied.");
        }
        if (isAbortError(error)) throw error;
        if (error instanceof NativeGraphDemoApiError) throw error;
        throw new NativeGraphDemoApiError(
          error instanceof Error ? error.message : "The managed graph inspection could not be reached.",
          "network_error",
          0,
        );
      }
      const body = await responseBody(response);
      if (signal?.aborted) throw abortError();
      if (invalidated || startedGeneration !== generation) {
        throw invalidManagedGraph("The selected World changed before this graph inspection could be applied.");
      }
      if (!response.ok) await throwInspectionResponseError(response, body);
      if (!isNativeGraphEntityForPin(body, pin)) {
        throw invalidManagedGraph("The native inspection response did not match the selected World and exact graph revision.");
      }
      return body;
    },
  };
  return {
    api,
    invalidate() {
      if (invalidated) return;
      invalidated = true;
      generation += 1;
      binding = null;
      for (const controller of activeControllers) controller.abort();
      activeControllers.clear();
    },
  };
}
