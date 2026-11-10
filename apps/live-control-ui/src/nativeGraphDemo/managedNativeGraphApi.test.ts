import { describe, expect, it, vi } from "vitest";
import { NativeGraphDemoApiError } from "./nativeGraphDemoApi";
import { createManagedNativeGraphApi } from "./managedNativeGraphApi";

const authHarness = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock("../api/liveApi", () => ({
  authenticatedApiFetch: authHarness.fetch,
}));

const nativeGraph = {
  world_id: "native-world-1",
  revision_id: "revision-1",
  graph_sha256: "sha256:graph-1",
  nodes: [{ id: "entity:lina", name: "Lina", kind: "person" }],
  edges: [],
  storage: "postgres",
  limitations: [],
  capabilities: { create: true, connect: true, rename: false, delete: false, object_kinds: ["person", "location"] },
  completeness: {
    status: "complete",
    listed_entities: 1,
    omitted_entities: 0,
    unexamined_entities: 0,
    listed_assertions: 0,
    omitted_assertions: 0,
    unexamined_assertions: 0,
    reasons: [],
  },
};

function envelope(overrides: Record<string, unknown> = {}) {
  return {
    schema: "dmb_native_graph_explorer_v1",
    managed_world_id: "managed-a",
    native_world_id: "native-world-1",
    binding_version: 1,
    graph: nativeGraph,
    ...overrides,
  };
}

function response(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

function graphEnvelope(revisionId: string) {
  return envelope({ graph: { ...nativeGraph, revision_id: revisionId } });
}

function entityDetail(scope: unknown) {
  return {
    schema: "dmb_native_graph_entity_v1",
    scope,
    entity: {
      found: true,
      assertions: [],
      evidence: [],
      completeness: { status: "complete", reason: null },
    },
  };
}

describe("managed native graph API", () => {
  it("reads and validates a graph against the selected World and exact binding", async () => {
    const fetcher = vi.fn(async () => response(envelope()));
    const client = createManagedNativeGraphApi("managed-a", { fetcher });

    await expect(client.api.readGraph()).resolves.toMatchObject({
      world_id: "native-world-1",
      revision_id: "revision-1",
      completeness: { status: "complete", listed_entities: 1 },
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0]?.[0]).toBe("/api/live/native-graph-explorer/graph");
    expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toEqual({ managed_world_id: "managed-a" });
    expect(fetcher.mock.calls[0]?.[1]?.method).toBe("POST");
  });

  it("inspects the pinned displayed revision even after the current native head advances", async () => {
    let graphReads = 0;
    const fetcher = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      if (String(path).endsWith("/graph")) {
        graphReads += 1;
        return response(graphEnvelope(graphReads === 1 ? "revision-1" : "revision-2"));
      }
      if (String(path).endsWith("/native-graph-inspection/read")) {
        const request = JSON.parse(String(init?.body)) as { scope: Record<string, unknown> };
        return response(entityDetail(request.scope));
      }
      return response({ error: "unexpected route", code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    const displayedGraph = await client.api.readGraph();
    await client.api.readGraph();

    await expect(client.api.inspectNode?.(displayedGraph, "entity:lina")).resolves.toMatchObject({
      schema: "dmb_native_graph_entity_v1",
      scope: {
        managed_world_id: "managed-a",
        native_world_id: "native-world-1",
        binding_version: 1,
        scope_mode: "world",
        campaign_id: null,
        revision_id: "revision-1",
      },
    });
    expect(fetcher.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/live/native-graph-explorer/graph",
      "/api/live/native-graph-explorer/graph",
      "/api/live/native-graph-inspection/read",
    ]);
    expect(JSON.parse(String(fetcher.mock.calls[2]?.[1]?.body))).toEqual({
      scope: {
        managed_world_id: "managed-a",
        native_world_id: "native-world-1",
        binding_version: 1,
        scope_mode: "world",
        campaign_id: null,
        revision_id: "revision-1",
      },
      selection: { kind: "entity", entity_id: "entity:lina" },
    });
  });

  it("accepts an unavailable-at-revision entity only with the exact snapshot pin", async () => {
    const fetcher = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      if (String(path).endsWith("/graph")) return response(graphEnvelope("revision-1"));
      const request = JSON.parse(String(init?.body)) as { scope: Record<string, unknown> };
      return response({ ...entityDetail(request.scope), entity: {
        found: false,
        assertions: [],
        evidence: [],
        completeness: { status: "complete", reason: null },
      } });
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    const graph = await client.api.readGraph();
    await expect(client.api.inspectNode?.(graph, "entity:lina")).resolves.toMatchObject({
      entity: { found: false },
      scope: { revision_id: "revision-1" },
    });
  });

  it("registers exact pins from every graph-producing operation flow", async () => {
    const operationId = "f01d8ed1-9886-4fd5-8b9f-f6c8b788084d";
    const revisions: string[] = [];
    const fetcher = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      const url = String(path);
      if (url.endsWith("/graph")) return response(graphEnvelope("read-graph"));
      if (url.endsWith("/prepare")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "already_exists", operation_id: operationId,
        managed_world_id: "managed-a", native_world_id: "native-world-1", binding_version: 1,
        message: "The connection is already present.", graph: graphEnvelope("prepare-result"),
      });
      if (url.endsWith("/confirm")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "committed", operation_id: operationId,
        managed_world_id: "managed-a", native_world_id: "native-world-1", binding_version: 1,
        graph: graphEnvelope("confirm-result"),
      });
      if (url.endsWith("/operations/read")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "committed", operation_id: operationId,
        managed_world_id: "managed-a", native_world_id: "native-world-1", binding_version: 1,
        graph: graphEnvelope("operation-result"),
      });
      if (url.endsWith("/native-graph-inspection/read")) {
        const request = JSON.parse(String(init?.body)) as { scope: { revision_id: string } };
        revisions.push(request.scope.revision_id);
        return response(entityDetail(request.scope));
      }
      return response({ error: `unexpected route ${url}`, code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    const readGraph = await client.api.readGraph();
    const prepared = await client.api.prepare({
      operation_id: operationId,
      expected_revision_id: "read-graph",
      kind: "connect",
      source_id: "entity:lina",
      target_id: "entity:lina",
      predicate: "allied_with",
    });
    const committed = await client.api.confirm(operationId);
    const recovered = await client.api.readOperation(operationId);

    const producedGraphs = [
      readGraph,
      prepared.status === "already_exists" ? prepared.graph : null,
      committed.status === "committed" ? committed.graph : null,
      recovered.status === "committed" ? recovered.graph ?? null : null,
    ];
    expect(producedGraphs.every(Boolean)).toBe(true);
    for (const graph of producedGraphs) {
      await client.api.inspectNode?.(graph!, "entity:lina");
    }
    expect(revisions).toEqual(["read-graph", "prepare-result", "confirm-result", "operation-result"]);
  });

  it("rejects cloned snapshots, unknown nodes, and response scopes outside the exact pin", async () => {
    const calls: unknown[] = [];
    const fetcher = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      if (String(path).endsWith("/graph")) return response(graphEnvelope("revision-1"));
      if (String(path).endsWith("/native-graph-inspection/read")) {
        const request = JSON.parse(String(init?.body)) as { scope: Record<string, unknown> };
        calls.push(request);
        return response(entityDetail({ ...request.scope, revision_id: "revision-other" }));
      }
      return response({ error: "unexpected route", code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    const graph = await client.api.readGraph();
    await expect(client.api.inspectNode?.({ ...graph }, "entity:lina")).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    await expect(client.api.inspectNode?.(graph, "entity:unknown")).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(fetcher).toHaveBeenCalledTimes(1);
    await expect(client.api.inspectNode?.(graph, "entity:lina")).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(calls).toHaveLength(1);
    (graph.nodes as Array<{ id: string; name: string; kind: string }>).push({ id: "entity:altered", name: "Altered", kind: "person" });
    await expect(client.api.inspectNode?.(graph, "entity:lina")).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(calls).toHaveLength(1);
  });

  it("aborts pending inspection and rejects results from an invalidated client", async () => {
    let graphReads = 0;
    const fetcher = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      if (String(path).endsWith("/graph")) {
        graphReads += 1;
        return response(graphEnvelope(`revision-${graphReads}`));
      }
      if (String(path).endsWith("/native-graph-inspection/read")) {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
        });
      }
      return response({ error: "unexpected route", code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    const graph = await client.api.readGraph();
    const controller = new AbortController();
    const pending = client.api.inspectNode?.(graph, "entity:lina", controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(fetcher.mock.calls[1]?.[1]?.signal?.aborted).toBe(true);

    const nextClient = createManagedNativeGraphApi("managed-a", { fetcher });
    const nextGraph = await nextClient.api.readGraph();
    const invalidatedInspection = nextClient.api.inspectNode?.(nextGraph, "entity:lina");
    nextClient.invalidate();
    await expect(invalidatedInspection).rejects.toMatchObject({ code: "invalid_managed_world_response" });
  });

  it("binds prepare, confirm, and operation reads to the graph’s verified World", async () => {
    const operationId = "f01d8ed1-9886-4fd5-8b9f-f6c8b788084d";
    const fetcher = vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
      const url = String(path);
      if (url.endsWith("/graph")) return response(envelope());
      if (url.endsWith("/prepare")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "prepared", operation_id: operationId, managed_world_id: "managed-a",
        native_world_id: "native-world-1", binding_version: 1,
        parent_revision_id: "revision-1", review: { summary: "Create Mira." },
      });
      if (url.endsWith("/confirm")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "committed", operation_id: operationId, managed_world_id: "managed-a",
        native_world_id: "native-world-1", binding_version: 1, created_node_id: "entity:lina", graph: envelope(),
      });
      if (url.endsWith("/operations/read")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "prepared", operation_id: operationId, managed_world_id: "managed-a",
        native_world_id: "native-world-1", binding_version: 1,
        parent_revision_id: "revision-1", review: { summary: "Create Mira." },
      });
      return response({ error: `unexpected ${url}`, code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    await client.api.readGraph();
    const input = {
      operation_id: operationId,
      expected_revision_id: "revision-1",
      kind: "create_object" as const,
      name: "Mira",
      object_kind: "person" as const,
    };

    await expect(client.api.prepare(input)).resolves.toMatchObject({ status: "prepared", operation_id: operationId });
    await expect(client.api.confirm(operationId)).resolves.toMatchObject({
      status: "committed", graph: { world_id: "native-world-1" }, created_node_id: "entity:lina",
    });
    await expect(client.api.readOperation(operationId)).resolves.toMatchObject({ status: "prepared", operation_id: operationId });

    expect(fetcher.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/live/native-graph-explorer/graph",
      "/api/live/native-graph-explorer/prepare",
      "/api/live/native-graph-explorer/confirm",
      "/api/live/native-graph-explorer/operations/read",
    ]);
    const prepareBody = JSON.parse(String(fetcher.mock.calls[1]?.[1]?.body));
    expect(prepareBody).toEqual({
      ...input,
      managed_world_id: "managed-a",
      native_world_id: "native-world-1",
      binding_version: 1,
    });
    expect(JSON.parse(String(fetcher.mock.calls[2]?.[1]?.body))).toEqual({ managed_world_id: "managed-a", operation_id: operationId });
    expect(JSON.parse(String(fetcher.mock.calls[3]?.[1]?.body))).toEqual({ managed_world_id: "managed-a", operation_id: operationId });
  });

  it("rejects a graph or operation response for another managed or native World", async () => {
    const wrongGraphFetcher = vi.fn(async () => response(envelope({ managed_world_id: "managed-b" })));
    const wrongGraphClient = createManagedNativeGraphApi("managed-a", { fetcher: wrongGraphFetcher });
    await expect(wrongGraphClient.api.readGraph()).rejects.toMatchObject<Partial<NativeGraphDemoApiError>>({
      code: "invalid_managed_world_response",
    });

    let graphReads = 0;
    const wrongOperationFetcher = vi.fn(async (path: RequestInfo | URL) => {
      if (String(path).endsWith("/graph")) {
        graphReads += 1;
        return response(envelope());
      }
      return response({
        schema: "dmb_native_graph_explorer_v1", status: "prepared", operation_id: "op-a", managed_world_id: "managed-a",
        native_world_id: "native-world-other", binding_version: 1,
        parent_revision_id: "revision-1", review: { summary: "Wrong World." },
      });
    });
    const wrongOperationClient = createManagedNativeGraphApi("managed-a", { fetcher: wrongOperationFetcher });
    await wrongOperationClient.api.readGraph();
    await expect(wrongOperationClient.api.readOperation("op-a")).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(graphReads).toBe(1);
  });

  it("refuses a changed native binding instead of silently following it", async () => {
    let readCount = 0;
    const fetcher = vi.fn(async () => {
      readCount += 1;
      return response(readCount === 1 ? envelope() : envelope({ binding_version: 2 }));
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });

    await client.api.readGraph();
    await expect(client.api.readGraph()).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(readCount).toBe(2);
  });

  it("does not prepare without a verified binding and does not infer another World", async () => {
    const fetcher = vi.fn(async () => response(envelope()));
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    await expect(client.api.prepare({
      operation_id: "op-a",
      expected_revision_id: "revision-1",
      kind: "create_object",
      name: "Mira",
      object_kind: "person",
    })).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("validates already-present and missing-operation envelopes without losing World identity", async () => {
    const operationId = "f01d8ed1-9886-4fd5-8b9f-f6c8b788084d";
    const fetcher = vi.fn(async (path: RequestInfo | URL) => {
      const url = String(path);
      if (url.endsWith("/graph")) return response(envelope());
      if (url.endsWith("/prepare")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "already_exists", operation_id: operationId,
        managed_world_id: "managed-a", native_world_id: "native-world-1", binding_version: 1,
        message: "The exact connection is already present.", graph: envelope(),
      });
      if (url.endsWith("/operations/read")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "not_found", operation_id: operationId,
        managed_world_id: "managed-a", native_world_id: "native-world-1", binding_version: 1,
      });
      return response({ error: "unexpected route", code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    await client.api.readGraph();
    await expect(client.api.prepare({
      operation_id: operationId,
      expected_revision_id: "revision-1",
      kind: "connect",
      source_id: "entity:lina",
      target_id: "entity:lina",
      predicate: "allied_with",
    })).resolves.toMatchObject({ status: "already_exists", graph: { world_id: "native-world-1" } });
    await expect(client.api.readOperation(operationId)).resolves.toMatchObject({ status: "not_found", operation_id: operationId });
  });

  it("rejects identity-free operation statuses even when no graph is returned", async () => {
    const fetcher = vi.fn(async (path: RequestInfo | URL) => String(path).endsWith("/graph")
      ? response(envelope())
      : response({ status: "not_found", operation_id: "op-a" }));
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    await client.api.readGraph();
    await expect(client.api.readOperation("op-a")).rejects.toMatchObject({ code: "invalid_managed_world_response" });
  });

  it("preserves backend error details from FastAPI detail envelopes", async () => {
    const fetcher = vi.fn(async () => response({
      detail: { code: "managed_world_unavailable", error: "The selected World has no native binding." },
    }, 409));
    const client = createManagedNativeGraphApi("managed-a", { fetcher });

    await expect(client.api.readGraph()).rejects.toMatchObject({
      code: "managed_world_unavailable",
      message: "The selected World has no native binding.",
      status: 409,
    });
  });

  it("does not turn an already-committed exact prepare retry into a fresh review", async () => {
    const operationId = "f01d8ed1-9886-4fd5-8b9f-f6c8b788084d";
    const committedEnvelope = envelope();
    const fetcher = vi.fn(async (path: RequestInfo | URL) => {
      const url = String(path);
      if (url.endsWith("/graph")) return response(envelope());
      if (url.endsWith("/prepare")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "committed", operation_id: operationId, managed_world_id: "managed-a",
        native_world_id: "native-world-1", binding_version: 1,
        created_node_id: "entity:lina", graph: committedEnvelope,
      });
      if (url.endsWith("/operations/read")) return response({
        schema: "dmb_native_graph_explorer_v1", status: "committed", operation_id: operationId, managed_world_id: "managed-a",
        native_world_id: "native-world-1", binding_version: 1,
        created_node_id: "entity:lina", graph: committedEnvelope,
      });
      return response({ error: "unexpected route", code: "unexpected" }, 404);
    });
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    await client.api.readGraph();
    const input = {
      operation_id: operationId,
      expected_revision_id: "revision-1",
      kind: "create_object" as const,
      name: "Lina",
      object_kind: "person" as const,
    };

    await expect(client.api.prepare(input)).rejects.toMatchObject({ code: "operation_already_committed" });
    await expect(client.api.readOperation(operationId)).resolves.toMatchObject({
      status: "committed", operation_id: operationId, created_node_id: "entity:lina",
      graph: { world_id: "native-world-1" },
    });
    expect(fetcher.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/live/native-graph-explorer/graph",
      "/api/live/native-graph-explorer/prepare",
      "/api/live/native-graph-explorer/operations/read",
    ]);
  });

  it("blocks a stale response after the selected World route is disposed", async () => {
    let resolveFetch!: (value: Response) => void;
    const fetcher = vi.fn(() => new Promise<Response>((resolve) => { resolveFetch = resolve; }));
    const client = createManagedNativeGraphApi("managed-a", { fetcher });
    const pending = client.api.readGraph();
    client.invalidate();
    resolveFetch(response(envelope()));
    await expect(pending).rejects.toMatchObject({ code: "invalid_managed_world_response" });
    expect(fetcher.mock.calls[0]?.[1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it("uses the authenticated API owner for exact managed graph routes", async () => {
    authHarness.fetch.mockImplementation(async (path: string, init: RequestInit) => ({
      response: response(envelope()), csrf: null, requestEpoch: 0,
    }));
    const client = createManagedNativeGraphApi("managed-a");
    await client.api.readGraph();
    expect(authHarness.fetch).toHaveBeenCalledWith("/api/live/native-graph-explorer/graph", expect.objectContaining({ method: "POST" }));
  });
});
