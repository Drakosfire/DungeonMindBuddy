// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { clearPendingWorldNotesDraft, setPendingWorldNotesDraft } from "../localWorldDocumentAuthoring";
import { LocalWorldSurface } from "./LocalWorldSurface";

const loads = vi.hoisted(() => ({ graph: 0, notes: 0, failNotes: false }));
vi.mock("../../ui/deferredComponent", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../ui/deferredComponent")>();
  const deferredComponent: typeof actual.deferredComponent = (load, label) =>
    actual.deferredComponent(async () => {
      if (label === "local graph editor" && ++loads.graph === 1) {
        throw new Error("Synthetic Graph load failure");
      }
      if (label === "Markdown editor") {
        loads.notes++;
        if (loads.failNotes) {
          throw new Error("Synthetic notes load failure");
        }
      }
      return load();
    }, label);
  return { deferredComponent };
});

afterEach(() => vi.restoreAllMocks());

it("retries the graph editor while keeping the selected World and title draft", async () => {
  const user = userEvent.setup();
  const repository = new InMemoryLocalWorldRepository();
  vi.spyOn(console, "error").mockImplementation(() => {});
  render(<AgentInteractionProvider><LocalWorldSurface openRepository={async () => ({ status: "opened", repository })} /></AgentInteractionProvider>);

  const retry = await screen.findByRole("button", { name: "Retry local graph editor" });
  expect(screen.getByRole("heading", { name: "My World" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Edit World title" }));
  const title = screen.getByLabelText("World title");
  await user.clear(title);
  await user.type(title, "Unsaved Coast");
  await user.click(retry);

  expect(await screen.findByRole("button", { name: "Mara Venn, person" })).toBeVisible();
  expect(screen.getByLabelText("World title")).toHaveValue("Unsaved Coast");
});

it("recovers the notes editor with the pending draft", async () => {
  loads.notes = 0;
  loads.failNotes = true;
  const user = userEvent.setup();
  const repository = new InMemoryLocalWorldRepository();
  const created = await repository.createWorld({ title: "Notes Retry World" });
  if (created.status !== "created") throw new Error("World fixture was not created");
  const { worldId } = created.record.snapshot;
  await repository.commitWorldNotes({ worldId, expectedLocalRevision: 0, markdown: "Saved notes" });
  setPendingWorldNotesDraft(worldId, "Pending notes survive retry", "Saved notes");
  vi.spyOn(console, "error").mockImplementation(() => {});
  try {
    render(<AgentInteractionProvider><LocalWorldSurface openRepository={async () => ({ status: "opened", repository })} /></AgentInteractionProvider>);
    expect(loads.notes).toBe(0);
    await user.click(await screen.findByRole("button", { name: /Notes Retry World/ }));
    const retry = await screen.findByRole("button", { name: "Retry Markdown editor" });
    loads.failNotes = false;
    await user.click(retry);
    await waitFor(() => expect(screen.getByTestId("local-world-notes-editor")).toHaveTextContent("Pending notes survive retry"));
  } finally {
    clearPendingWorldNotesDraft(worldId);
  }
});
