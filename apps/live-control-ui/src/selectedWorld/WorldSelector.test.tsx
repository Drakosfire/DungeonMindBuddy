import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createWorldContainer, listWorldContainers } from "../api/liveApi";
import { SelectedWorldProvider } from "./SelectedWorldContext";
import { WorldSelector } from "./WorldSelector";

vi.mock("../api/liveApi", () => ({
  listWorldContainers: vi.fn(),
  createWorldContainer: vi.fn(),
  getWorkspaceDocument: vi.fn(),
}));

describe("World selector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/plan?documentId=old-plan");
  });

  it("lists named server Worlds on demand and clears stale route identity", async () => {
    vi.mocked(listWorldContainers).mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1",
        world_id: "world-b",
        name: "World B",
        source_root_relpath: "corpus/world-b-markdown",
        created_at: "2026-01-01T00:00:00Z",
      }],
    });
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/plan"><WorldSelector /></SelectedWorldProvider>);
    expect(listWorldContainers).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "World: Choose" }));
    await user.click(await screen.findByRole("button", { name: "World B" }));
    expect(window.location.pathname).toBe("/plan");
    expect(window.location.search).toBe("?world=world-b");
  });

  it("keeps compact World selection on demand with an explicit switch label", async () => {
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [] });
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/plan"><WorldSelector compact /></SelectedWorldProvider>);
    const trigger = screen.getByRole("button", { name: "Switch World: Choose" });
    expect(trigger).toHaveTextContent("Choose");
    expect(listWorldContainers).not.toHaveBeenCalled();
    await user.click(trigger);
    expect(await screen.findByText("No managed Worlds yet.")).toBeInTheDocument();
    expect(listWorldContainers).toHaveBeenCalledTimes(1);
  });

  it("explains that a new World reserves identity without promising native graph setup", async () => {
    vi.mocked(listWorldContainers).mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1",
        world_id: "world-b",
        name: "World B",
        source_root_relpath: "corpus/world-b-markdown",
        created_at: "2026-01-01T00:00:00Z",
      }],
    });
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/plan?world=world-b"><WorldSelector compact /></SelectedWorldProvider>);

    await user.click(await screen.findByRole("button", { name: "Switch World: World B" }));
    expect(screen.getByRole("link", { name: "Open this World in Build" })).toHaveAttribute("href", "/build?world=world-b");
    expect(screen.getByText(/creating a World reserves its identity/i)).toBeInTheDocument();
    expect(screen.getByText(/native graph initialization is not available in this explorer yet/i)).toBeInTheDocument();
    expect(screen.getByText(/compatible existing Worlds can be explored here/i)).toBeInTheDocument();
    expect(screen.queryByText(/initialize its first native graph through the reviewed Build workflow/i)).not.toBeInTheDocument();
  });

  it("keeps the error visible and permits a fresh registry request", async () => {
    vi.mocked(listWorldContainers)
      .mockRejectedValueOnce(new Error("registry unavailable"))
      .mockResolvedValueOnce({ schema_version: "dmb_world_container_registry_v1", records: [] });
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/plan"><WorldSelector /></SelectedWorldProvider>);
    await user.click(screen.getByRole("button", { name: "World: Choose" }));
    expect(await screen.findByText("registry unavailable")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry World list" }));
    await waitFor(() => expect(listWorldContainers).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("No managed Worlds yet.")).toBeInTheDocument();
  });

  it("creates a named World and opens its blank Plan directly", async () => {
    vi.mocked(listWorldContainers).mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [],
    });
    vi.mocked(createWorldContainer).mockResolvedValue({
      schema_version: "dmb_world_container_record_v1",
      world_id: "glass-orchard",
      name: "The Glass Orchard",
      source_root_relpath: "corpus/glass-orchard-markdown",
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/plan"><WorldSelector /></SelectedWorldProvider>);
    await user.click(screen.getByRole("button", { name: "World: Choose" }));
    await user.type(screen.getByLabelText("New World name"), "The Glass Orchard");
    await user.click(screen.getByRole("button", { name: "Create World and Plan" }));
    await waitFor(() => expect(window.location.search).toBe("?world=glass-orchard"));
    expect(window.location.pathname).toBe("/plan");
    expect(createWorldContainer).toHaveBeenCalledWith({ name: "The Glass Orchard" });
  });

  it("creates a named World from the index and returns to the graph instead of Plan", async () => {
    window.history.replaceState({}, "", "/");
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [] });
    vi.mocked(createWorldContainer).mockResolvedValue({
      schema_version: "dmb_world_container_record_v1",
      world_id: "graph-orchard",
      name: "Graph Orchard",
      source_root_relpath: "corpus/graph-orchard-markdown",
      created_at: "2026-01-01T00:00:00Z",
    });
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/"><WorldSelector compact creationPath="/" /></SelectedWorldProvider>);
    await user.click(screen.getByRole("button", { name: "Switch World: Choose" }));
    await user.type(screen.getByLabelText("New World name"), "Graph Orchard");
    await user.click(screen.getByRole("button", { name: "Create World and open graph" }));

    await waitFor(() => expect(window.location.pathname + window.location.search).toBe("/?world=graph-orchard"));
    expect(window.location.pathname).not.toBe("/plan");
  });

  it("does not redirect back to the starting index after a World switch while creation is pending", async () => {
    window.history.replaceState({}, "", "/");
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [] });
    let resolveCreate!: (value: Awaited<ReturnType<typeof createWorldContainer>>) => void;
    vi.mocked(createWorldContainer).mockImplementation(() => new Promise((resolve) => { resolveCreate = resolve; }));
    const user = userEvent.setup();
    render(<SelectedWorldProvider locationSnapshot="/"><WorldSelector compact creationPath="/" /></SelectedWorldProvider>);
    await user.click(screen.getByRole("button", { name: "Switch World: Choose" }));
    await user.type(screen.getByLabelText("New World name"), "New World");
    await user.click(screen.getByRole("button", { name: "Create World and open graph" }));

    window.history.pushState({}, "", "/?world=another-world");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await act(async () => resolveCreate({
      schema_version: "dmb_world_container_record_v1",
      world_id: "newly-created",
      name: "New World",
      source_root_relpath: "corpus/newly-created-markdown",
      created_at: "2026-01-01T00:00:00Z",
    }));

    expect(window.location.pathname + window.location.search).toBe("/?world=another-world");
  });

  it("does not navigate after the selector unmounts while preserving the created World", async () => {
    window.history.replaceState({}, "", "/");
    let created = false;
    const world = {
      schema_version: "dmb_world_container_record_v1" as const,
      world_id: "saved-after-unmount",
      name: "Saved After Unmount",
      source_root_relpath: "corpus/saved-after-unmount-markdown",
      created_at: "2026-01-01T00:00:00Z",
    };
    vi.mocked(listWorldContainers).mockImplementation(async () => ({
      schema_version: "dmb_world_container_registry_v1",
      records: created ? [world] : [],
    }));
    let resolveCreate!: (value: Awaited<ReturnType<typeof createWorldContainer>>) => void;
    vi.mocked(createWorldContainer).mockImplementation(() => new Promise((resolve) => { resolveCreate = resolve; }));
    const user = userEvent.setup();
    const view = render(<SelectedWorldProvider locationSnapshot="/"><WorldSelector compact creationPath="/" /></SelectedWorldProvider>);
    await user.click(screen.getByRole("button", { name: "Switch World: Choose" }));
    await user.type(screen.getByLabelText("New World name"), world.name);
    await user.click(screen.getByRole("button", { name: "Create World and open graph" }));
    view.unmount();

    created = true;
    await act(async () => resolveCreate(world));
    expect(window.location.pathname + window.location.search).toBe("/");

    render(<SelectedWorldProvider locationSnapshot="/"><WorldSelector compact creationPath="/" /></SelectedWorldProvider>);
    await user.click(screen.getByRole("button", { name: "Switch World: Choose" }));
    expect(await screen.findByRole("button", { name: world.name })).toBeInTheDocument();
    expect(window.location.pathname + window.location.search).toBe("/");
  });
});
