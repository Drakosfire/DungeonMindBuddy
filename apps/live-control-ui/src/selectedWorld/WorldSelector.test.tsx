import { render, screen, waitFor } from "@testing-library/react";
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
});
