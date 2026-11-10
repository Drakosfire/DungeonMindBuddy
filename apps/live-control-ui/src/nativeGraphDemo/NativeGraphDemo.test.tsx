import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NativeGraphDemo } from "./NativeGraphDemo";
import type { NativeGraph, NativeGraphDemoApi } from "./nativeGraphDemoApi";

const graph: NativeGraph = {
  world_id: "space:native-demo",
  revision_id: "revision-001",
  graph_sha256: "sha256:graph-001",
  nodes: [
    { id: "entity:mara", name: "Mara", kind: "npc" },
    { id: "entity:tomas", name: "Tomas", kind: "npc" },
    { id: "entity:inn", name: "Lantern Inn", kind: "location" },
  ],
  edges: [{ id: "assertion:stays", source_id: "entity:mara", target_id: "entity:inn", predicate: "stays_at" }],
  storage: "postgres",
  limitations: ["Event typing is not available in this native profile."],
  capabilities: { create: true, connect: true, rename: false, delete: false, object_kinds: ["person", "location"] },
};

const createdGraph: NativeGraph = {
  ...graph,
  revision_id: "revision-002",
  graph_sha256: "sha256:graph-002",
  nodes: [...graph.nodes, { id: "entity:mira", name: "Mira", kind: "person" }],
};

function makeApi(overrides: Partial<NativeGraphDemoApi> = {}): NativeGraphDemoApi {
  return {
    readGraph: vi.fn().mockResolvedValue(graph),
    prepare: vi.fn().mockResolvedValue({
      status: "prepared",
      operation_id: "bb9c10ac-c94a-4693-b7bc-4d001c398770",
      parent_revision_id: graph.revision_id,
      review: { summary: "Create Mira as a native person in the current World." },
    }),
    confirm: vi.fn().mockResolvedValue({ status: "committed", graph: createdGraph }),
    readOperation: vi.fn().mockResolvedValue({ status: "unknown", operation_id: "bb9c10ac-c94a-4693-b7bc-4d001c398770" }),
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
}

describe("NativeGraphDemo", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    document.head.innerHTML = '<meta name="native-demo-capability" content="demo-test">';
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("uses the server graph and makes create a prepare-review-confirm sequence", async () => {
    const user = userEvent.setup();
    const api = makeApi();
    const uuid = vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    render(<NativeGraphDemo api={api} />);

    expect(await screen.findByRole("heading", { name: "The living graph" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "DungeonMind native graph" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Mara, npc/i })).toHaveAttribute("data-node-id", "entity:mara");
    expect(screen.getByText(/Event typing is not supported by this DungeonMind profile yet/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Event · unavailable/ })).toBeDisabled();
    expect(screen.getByText(/Rename is unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/Delete is unavailable/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));

    await screen.findByText("Create Mira as a native person in the current World.");
    expect(api.prepare).toHaveBeenCalledWith({
      operation_id: "bb9c10ac-c94a-4693-b7bc-4d001c398770",
      expected_revision_id: "revision-001",
      kind: "create_object",
      name: "Mira",
      object_kind: "person",
    });
    expect(api.confirm).not.toHaveBeenCalled();
    expect(screen.getByDisplayValue("Mira")).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));

    expect(await screen.findByText(/is committed\. The graph below is the server readback/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Mira, person/i })).toHaveAttribute("data-node-id", "entity:mira");
    expect(api.confirm).toHaveBeenCalledWith("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    expect(uuid).toHaveBeenCalledOnce();
  });

  it("keeps the exact operation ID and form draft after an uncertain prepare response", async () => {
    const user = userEvent.setup();
    const uncertain = Object.assign(new Error("connection dropped"), { code: "network_error", status: 0 });
    const api = makeApi({
      prepare: vi.fn()
        .mockRejectedValueOnce(uncertain)
        .mockResolvedValueOnce({
          status: "prepared",
          operation_id: "4a4a77ef-4182-4050-86cf-e9c7e06935f8",
          parent_revision_id: graph.revision_id,
          review: { summary: "Create Mira as a native person in the current World." },
        }),
      readOperation: vi.fn().mockResolvedValue({ status: "not_found", operation_id: "4a4a77ef-4182-4050-86cf-e9c7e06935f8" }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("4a4a77ef-4182-4050-86cf-e9c7e06935f8");
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));

    expect(await screen.findByText(/operation ID are preserved/)).toBeInTheDocument();
    expect(api.readOperation).toHaveBeenCalledWith("4a4a77ef-4182-4050-86cf-e9c7e06935f8");
    expect(screen.getByDisplayValue("Mira")).toBeDisabled();
    const stored = JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null");
    expect(stored.pending.operation_id).toBe("4a4a77ef-4182-4050-86cf-e9c7e06935f8");

    await user.click(screen.getByRole("button", { name: "Retry same operation ID" }));

    await screen.findByText("Create Mira as a native person in the current World.");
    expect(api.prepare).toHaveBeenCalledTimes(2);
    expect(api.prepare.mock.calls[0]?.[0]).toEqual(api.prepare.mock.calls[1]?.[0]);
  });

  it("preserves a form draft across navigation and constrains directed relationship predicates", async () => {
    const user = userEvent.setup();
    const api = makeApi();
    const view = render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Aster");
    view.unmount();
    render(<NativeGraphDemo api={api} />);
    expect(await screen.findByDisplayValue("Aster")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("From"), "entity:mara");
    await user.selectOptions(screen.getByLabelText("To"), "entity:tomas");
    const predicate = screen.getByLabelText("Relationship");
    await user.type(predicate, "Knows people");
    expect(predicate).toHaveAttribute("pattern", "[a-z0-9][a-z0-9._-]*");
    expect(screen.getByText(/lowercase letters, numbers, dots, underscores, and hyphens only/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Prepare connection" }));
    expect(api.prepare).not.toHaveBeenCalled();

    fireEvent.change(predicate, { target: { value: "knows_people" } });
    await user.click(screen.getByRole("button", { name: "Prepare connection" }));
    await waitFor(() => expect(api.prepare).toHaveBeenCalledWith(expect.objectContaining({
      kind: "connect",
      expected_revision_id: "revision-001",
      source_id: "entity:mara",
      target_id: "entity:tomas",
      predicate: "knows_people",
    })));
  });

  it("recovers a prepared operation by its saved ID without preparing or confirming automatically", async () => {
    sessionStorage.setItem("dungeonmind-native-demo:draft:space%3Anative-demo", JSON.stringify({
      version: 1,
      world_id: graph.world_id,
      draft: { objectName: "Recovered", objectKind: "person", sourceId: "", targetId: "", predicate: "" },
      pending: {
        operation_id: "c965d040-2d72-49eb-b417-31ccba7c7510",
        expected_revision_id: graph.revision_id,
        kind: "create_object",
        name: "Recovered",
        object_kind: "person",
      },
    }));
    const api = makeApi({
      readOperation: vi.fn().mockResolvedValue({
        status: "prepared",
        operation_id: "c965d040-2d72-49eb-b417-31ccba7c7510",
        parent_revision_id: graph.revision_id,
        review: { summary: "Recovered prepared change." },
      }),
    });
    render(<NativeGraphDemo api={api} />);

    expect(await screen.findByText("Recovered prepared change.")).toBeInTheDocument();
    expect(api.readOperation).toHaveBeenCalledWith("c965d040-2d72-49eb-b417-31ccba7c7510");
    expect(api.prepare).not.toHaveBeenCalled();
    expect(api.confirm).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Confirm in DungeonMind" })).toBeInTheDocument();
  });

  it("refreshes before editing a prepared draft and creates a new review without publishing the old one", async () => {
    const user = userEvent.setup();
    const latestGraph = { ...graph, revision_id: "revision-source-advanced", graph_sha256: "sha256-source-advanced" };
    const firstId = "4a4a77ef-4182-4050-86cf-e9c7e06935f8";
    const secondId = "b121ad7a-c50a-4a58-9e62-91eea9e3972d";
    const api = makeApi({
      readGraph: vi.fn().mockResolvedValueOnce(graph).mockResolvedValueOnce(latestGraph),
      readOperation: vi.fn().mockImplementation(async (operationId: string) => ({ status: "prepared", operation_id: operationId, review: { summary: "Prepared review remains on the server." } })),
      prepare: vi.fn()
        .mockResolvedValueOnce({ status: "prepared", operation_id: firstId, parent_revision_id: graph.revision_id, review: { summary: "First review." } })
        .mockResolvedValueOnce({ status: "prepared", operation_id: secondId, parent_revision_id: latestGraph.revision_id, review: { summary: "Edited review." } }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValueOnce(firstId).mockReturnValueOnce(secondId);
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText("First review.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit draft (keep review record)" }));

    expect(await screen.findByText(new RegExp(`Retained operation ID: ${firstId}`))).toBeInTheDocument();
    expect(screen.getByDisplayValue("Mira")).toBeEnabled();
    expect(api.confirm).not.toHaveBeenCalled();
    expect(api.readOperation).toHaveBeenCalledTimes(2);
    expect(api.readGraph).toHaveBeenCalledTimes(2);

    await user.type(screen.getByLabelText("Name"), " Gray");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    expect(await screen.findByText("Edited review.")).toBeInTheDocument();
    expect(api.prepare).toHaveBeenNthCalledWith(1, expect.objectContaining({ operation_id: firstId, name: "Mira", expected_revision_id: graph.revision_id }));
    expect(api.prepare).toHaveBeenNthCalledWith(2, expect.objectContaining({ operation_id: secondId, name: "Mira Gray", expected_revision_id: latestGraph.revision_id }));
    expect(api.confirm).not.toHaveBeenCalled();
  });

  it("keeps an HTTP 200 unknown confirm outcome locked to status checks", async () => {
    const user = userEvent.setup();
    const api = makeApi({
      confirm: vi.fn().mockResolvedValue({ status: "unknown", message: "Publication receipt is still being reconciled." }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    await screen.findByText("Create Mira as a native person in the current World.");
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));

    expect(await screen.findByText(/Publication receipt is still being reconciled/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check status" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry same operation ID" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refresh and start a fresh review" })).not.toBeInTheDocument();
    const stored = JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null");
    expect(stored.pending_phase).toBe("confirm");
    expect(stored.pending.operation_id).toBe("bb9c10ac-c94a-4693-b7bc-4d001c398770");
  });

  it("does not let a late confirmation from an unmounted instance overwrite a newer tab draft", async () => {
    const user = userEvent.setup();
    const commit = deferred<Awaited<ReturnType<NativeGraphDemoApi["confirm"]>>>();
    const api = makeApi({ confirm: vi.fn(() => commit.promise) });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    const first = render(<NativeGraphDemo api={api} />);

    await screen.findByRole("heading", { name: "The living graph" });
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    await screen.findByText("Create Mira as a native person in the current World.");
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));
    expect(api.confirm).toHaveBeenCalledOnce();
    first.unmount();

    // Model a newer page state that owns the same tab-scoped storage key.
    sessionStorage.setItem("dungeonmind-native-demo:draft:space%3Anative-demo", JSON.stringify({
      version: 1,
      world_id: graph.world_id,
      draft: { objectName: "Aster", objectKind: "person", sourceId: "", targetId: "", predicate: "" },
      pending: null,
    }));
    render(<NativeGraphDemo api={api} />);
    const nameField = await screen.findByDisplayValue("Aster");
    await user.type(nameField, " Vale");
    expect(JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null").draft.objectName).toBe("Aster Vale");

    commit.resolve({ status: "committed", graph: createdGraph });
    await waitFor(() => expect(JSON.parse(sessionStorage.getItem("dungeonmind-native-demo:draft:space%3Anative-demo") ?? "null").draft.objectName).toBe("Aster Vale"));
    expect(screen.getByDisplayValue("Aster Vale")).toBeInTheDocument();
  });

  it("ignores an older graph GET that returns after a newer confirmed graph readback", async () => {
    const user = userEvent.setup();
    const staleGraphRead = deferred<NativeGraph>();
    let graphReads = 0;
    const api = makeApi({
      readGraph: vi.fn(() => {
        graphReads += 1;
        return graphReads === 1 ? Promise.resolve(graph) : staleGraphRead.promise;
      }),
    });
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("bb9c10ac-c94a-4693-b7bc-4d001c398770");
    render(<NativeGraphDemo api={api} />);
    await screen.findByRole("heading", { name: "The living graph" });

    await user.click(screen.getByRole("button", { name: /Refresh/ }));
    await waitFor(() => expect(api.readGraph).toHaveBeenCalledTimes(2));
    await user.type(screen.getByLabelText("Name"), "Mira");
    await user.click(screen.getByRole("button", { name: "Prepare object" }));
    await screen.findByText("Create Mira as a native person in the current World.");
    await user.click(screen.getByRole("button", { name: "Confirm in DungeonMind" }));

    expect(await screen.findByText("revision-002")).toBeInTheDocument();
    staleGraphRead.resolve(graph);
    await waitFor(() => expect(screen.getByText("revision-002")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Mira, person/i })).toHaveAttribute("data-node-id", "entity:mira");
  });
});
