import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import * as liveApi from "./api/liveApi";
import { makeCapabilityResponse, makeRollTableArtifact, mockCatalog, mockLayout, mockPlanView, mockState } from "./test/fixtures";

vi.mock("./api/liveApi");

describe("App inspector integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
    vi.mocked(liveApi.getSurface).mockResolvedValue({
      catalog: mockCatalog,
      layout: mockLayout,
      state: mockState,
    });
    vi.mocked(liveApi.getEvents).mockResolvedValue({ events: [] });
    vi.mocked(liveApi.getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(liveApi.getPlanView).mockResolvedValue(mockPlanView);
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    vi.mocked(liveApi.getCapabilities).mockResolvedValue(makeCapabilityResponse());
  });

  it("renders the launcher at the root route", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /mireward local tools/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /plan prep surface/i })).toHaveAttribute("href", "/plan");
    expect(screen.getByRole("link", { name: /live play command board/i })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );
    expect(screen.getByRole("link", { name: /retrieval dogfood surface/i })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/retrieval.html",
    );
    expect(screen.getByRole("link", { name: /live control react surface/i })).toHaveAttribute(
      "href",
      "/surface",
    );
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(liveApi.getSurface).not.toHaveBeenCalled();
  });

  it("opens empty inspector from app chrome control", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/surface");
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /inspector/i }));
    expect(screen.getByText(/Select a timeline ref or record event to inspect/i)).toBeInTheDocument();
  });

  it("renders plan surface from /plan", async () => {
    window.history.pushState({}, "", "/plan");
    render(<App />);

    expect(await screen.findByText(/preparing Session 23 · ingesting Session 21/i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Toolbox tools" })).toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(liveApi.getPlanView).toHaveBeenCalled();
  });

  it("renders the shared editor toolbar collapsed on the Tiptap spike route", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/tiptap-callout-spike");
    render(<App />);

    expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Command board navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live play" })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByRole("button", { name: /Insert Read aloud/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Lock editing/ }));

    expect(screen.getByRole("button", { name: /Unlock editing/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Insert Read aloud/ })).toBeDisabled();
  });

});
