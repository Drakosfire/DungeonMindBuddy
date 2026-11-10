import { describe, expect, it, vi } from "vitest";
import { createNativeGraphDemoApi, NativeGraphDemoApiError } from "./nativeGraphDemoApi";
import type { NativeGraph } from "./nativeGraphDemoApi";

const graph: NativeGraph = {
  world_id: "space-1",
  revision_id: "revision-1",
  graph_sha256: "hash-1",
  nodes: [],
  edges: [],
  storage: "postgres",
  limitations: ["Event creation is unavailable in this profile."],
  capabilities: { create: true, connect: true, rename: false, delete: false, object_kinds: ["person", "location"] },
};

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

describe("native graph demo API", () => {
  it("reads the serving-time capability meta for each same-origin request", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="first-capability">';
    const fetcher = vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/graph"
      ? jsonResponse(graph)
      : jsonResponse({ status: "not_found", operation_id: "op/one" }));
    const api = createNativeGraphDemoApi({ fetcher });

    await api.readGraph();
    document.querySelector<HTMLMetaElement>('meta[name="native-demo-capability"]')!.content = "rotated-capability";
    await api.readOperation("op/one");

    const [firstUrl, firstInit] = fetcher.mock.calls[0]!;
    const [secondUrl, secondInit] = fetcher.mock.calls[1]!;
    expect(firstUrl).toBe("/api/graph");
    expect(firstInit?.credentials).toBe("same-origin");
    expect(firstInit?.cache).toBe("no-store");
    expect(new Headers(firstInit?.headers).get("X-Demo-Capability")).toBe("first-capability");
    expect(new Headers(firstInit?.headers).get("Accept")).toBe("application/json");
    expect(secondUrl).toBe("/api/operations/op%2Fone");
    expect(new Headers(secondInit?.headers).get("X-Demo-Capability")).toBe("rotated-capability");
    expect(localStorage.length).toBe(0);
  });

  it("sends exact prepare and confirm bodies without putting the capability in a URL", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="secret-demo-capability">';
    const fetcher = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => init?.body === JSON.stringify(input)
      ? jsonResponse({ status: "prepared", operation_id: input.operation_id, parent_revision_id: "revision-8", review: { summary: "Create Mira." } })
      : jsonResponse({ status: "committed", graph }));
    const api = createNativeGraphDemoApi({ fetcher });
    const input = {
      operation_id: "3f5b0d7a-a0d8-4c11-9de2-1ade34d0bbab",
      expected_revision_id: "revision-8",
      kind: "create_object" as const,
      name: "Mira",
      object_kind: "person" as const,
    };

    await api.prepare(input);
    await api.confirm(input.operation_id);

    const [prepareUrl, prepareInit] = fetcher.mock.calls[0]!;
    const [confirmUrl, confirmInit] = fetcher.mock.calls[1]!;
    expect(prepareUrl).toBe("/api/prepare");
    expect(prepareInit?.method).toBe("POST");
    expect(prepareInit?.body).toBe(JSON.stringify(input));
    expect(new Headers(prepareInit?.headers).get("X-Demo-Capability")).toBe("secret-demo-capability");
    expect(new Headers(prepareInit?.headers).get("Content-Type")).toBe("application/json");
    expect(confirmUrl).toBe("/api/confirm");
    expect(confirmInit?.method).toBe("POST");
    expect(confirmInit?.body).toBe(JSON.stringify({ operation_id: input.operation_id }));
    for (const [url] of fetcher.mock.calls) expect(String(url)).not.toContain("secret-demo-capability");
  });

  it("fails closed if the serving-time meta is missing", async () => {
    document.head.innerHTML = "";
    const fetcher = vi.fn();
    const api = createNativeGraphDemoApi({ fetcher });

    await expect(api.readGraph()).rejects.toMatchObject<Partial<NativeGraphDemoApiError>>({ code: "missing_capability" });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("preserves typed server error details for recovery UI", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const fetcher = vi.fn(async () => jsonResponse({ error: "The graph changed.", code: "stale_revision" }, 409));
    const api = createNativeGraphDemoApi({ fetcher });

    await expect(api.readGraph()).rejects.toMatchObject({
      name: "NativeGraphDemoApiError",
      message: "The graph changed.",
      code: "stale_revision",
      status: 409,
    });
  });

  it("keeps a 200 unknown confirm outcome distinct from commit", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const fetcher = vi.fn(async () => jsonResponse({ status: "unknown", operation_id: "op-2", message: "Native publication outcome is uncertain." }));
    const api = createNativeGraphDemoApi({ fetcher });

    await expect(api.confirm("op-2")).resolves.toEqual({
      status: "unknown",
      operation_id: "op-2",
      message: "Native publication outcome is uncertain.",
    });
  });

  it("rejects a graph response that omits its supported native object kinds", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const incomplete = { ...graph, capabilities: undefined };
    const fetcher = vi.fn(async () => jsonResponse(incomplete));
    const api = createNativeGraphDemoApi({ fetcher });

    await expect(api.readGraph()).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("accepts optional complete and partial native catalogue coverage while preserving guest compatibility", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const fetcher = vi.fn(async () => jsonResponse({
      ...graph,
      completeness: {
        status: "partial",
        listed_entities: 10,
        omitted_entities: 1,
        unexamined_entities: 2,
        listed_assertions: 7,
        omitted_assertions: 0,
        unexamined_assertions: 3,
        reasons: ["The native catalogue reached its bounded page limit."],
      },
    }));
    const api = createNativeGraphDemoApi({ fetcher });

    await expect(api.readGraph()).resolves.toMatchObject({
      completeness: { status: "partial", omitted_entities: 1, unexamined_assertions: 3 },
    });
    const guestCompatible = createNativeGraphDemoApi({ fetcher: vi.fn(async () => jsonResponse(graph)) });
    await expect(guestCompatible.readGraph()).resolves.not.toHaveProperty("completeness");
  });

  it("rejects inconsistent completeness counts instead of claiming a full native read", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const fetcher = vi.fn(async () => jsonResponse({
      ...graph,
      completeness: {
        status: "complete",
        listed_entities: 10,
        omitted_entities: 1,
        unexamined_entities: 0,
        listed_assertions: 7,
        omitted_assertions: 0,
        unexamined_assertions: 0,
        reasons: [],
      },
    }));
    const api = createNativeGraphDemoApi({ fetcher });

    await expect(api.readGraph()).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("preserves only server-verified created node IDs present in the committed graph", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const committedGraph = {
      ...graph,
      nodes: [{ id: "entity:mira", name: "Mira", kind: "person" }],
    };
    const api = createNativeGraphDemoApi({ fetcher: vi.fn(async () => jsonResponse({
      status: "committed",
      operation_id: "op-create",
      created_node_id: "entity:mira",
      graph: committedGraph,
    })) });

    await expect(api.confirm("op-create")).resolves.toMatchObject({
      status: "committed",
      created_node_id: "entity:mira",
      graph: { nodes: [{ id: "entity:mira" }] },
    });

    const invalidApi = createNativeGraphDemoApi({ fetcher: vi.fn(async () => jsonResponse({
      status: "committed",
      operation_id: "op-create",
      created_node_id: "entity:not-in-readback",
      graph: committedGraph,
    })) });
    await expect(invalidApi.confirm("op-create")).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("validates a recovered created node ID against an included graph", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const invalidApi = createNativeGraphDemoApi({ fetcher: vi.fn(async () => jsonResponse({
      status: "committed",
      operation_id: "op-recovered",
      created_node_id: "entity:missing",
      graph,
    })) });

    await expect(invalidApi.readOperation("op-recovered")).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("validates and preserves descriptor-approved predicate capabilities", async () => {
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo">';
    const managedGraph = {
      ...graph,
      capabilities: {
        ...graph.capabilities,
        allowed_predicates: ["located_in", "allied_with"],
        allows_custom_predicates: false,
      },
    };
    const api = createNativeGraphDemoApi({ fetcher: vi.fn(async () => jsonResponse(managedGraph)) });
    await expect(api.readGraph()).resolves.toMatchObject({
      capabilities: { allowed_predicates: ["located_in", "allied_with"], allows_custom_predicates: false },
    });

    const invalidApi = createNativeGraphDemoApi({ fetcher: vi.fn(async () => jsonResponse({
      ...managedGraph,
      capabilities: { ...managedGraph.capabilities, allowed_predicates: ["located_in", 7] },
    })) });
    await expect(invalidApi.readGraph()).rejects.toMatchObject({ code: "invalid_response" });
  });
});
