import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";

describe("UnionSupergraphRecapProjection", () => {

  it("labels the World Graph projection source", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        projectionSource="world-graph"
      />,
    );

    expect(screen.getByText(/Source: World Graph head/i)).toBeInTheDocument();
    expect(screen.getByText(/World Graph · session focus lens/i)).toBeInTheDocument();
    expect(
      screen.getByText(/prior-session evidence appears when present on those identities/i),
    ).toBeInTheDocument();
  });

  it("renders recap without a default static explorer panel", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    expect(screen.getByText("Session focus lens")).toBeInTheDocument();
    expect(screen.queryByLabelText("Graph object panel")).not.toBeInTheDocument();
    expect(screen.queryByText("Pinned node")).not.toBeInTheDocument();
  });

  it("opens shared GraphObjectCard when a recap chip is clicked", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    expect(screen.getByLabelText("Graph object panel")).toBeInTheDocument();
    expect(screen.getByLabelText("Caelynn game card")).toBeInTheDocument();
    expect(screen.getByLabelText("Connected objects and relationships")).toBeInTheDocument();
  });

  it("crawls graph via relationship rows and supports back/close", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    const panel = screen.getByLabelText("Graph object panel");
    fireEvent.click(within(panel).getByRole("button", { name: /Open related object.*Mirathorn/i }));

    const panelAtMirathorn = screen.getByLabelText("Graph object panel");
    expect(within(panelAtMirathorn).getByLabelText("Object trail")).toHaveTextContent("Caelynn");
    expect(within(panelAtMirathorn).getByLabelText("Mirathorn game card")).toBeInTheDocument();

    fireEvent.click(within(panelAtMirathorn).getByRole("button", { name: "Back" }));
    const panelAtCaelynn = screen.getByLabelText("Graph object panel");
    expect(within(panelAtCaelynn).getByLabelText("Caelynn game card")).toBeInTheDocument();

    fireEvent.click(within(panelAtCaelynn).getByRole("button", { name: "Close" }));
    expect(screen.queryByLabelText("Graph object panel")).not.toBeInTheDocument();
  });

  it("shows GraphObjectCard evidence from the hydrated node view", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    const card = screen.getByLabelText("Caelynn game card");
    const details = within(card).getByText("Details");
    fireEvent.click(details);
    expect(within(card).getByLabelText("Evidence and source")).toBeInTheDocument();
    expect(within(card).getByText(/Held the Mireward gate/i)).toBeInTheDocument();
  });

  it("applies role styling to recap pills", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    expect(caelynnPill).toHaveClass("role-pc");
  });

  it("shows GM planning hover card content on recap pills", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    const hoverCard = caelynnPill.parentElement?.querySelector(".recap-node-hover-card");
    expect(hoverCard).toHaveTextContent("Why now");
    expect(hoverCard).toHaveTextContent("Held the Mireward gate during the incident");
  });

  it("calls legacy opener when provided", () => {
    const onOpenLegacy = vi.fn();
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        onOpenLegacy={onOpenLegacy}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Legacy recap preview" }));
    expect(onOpenLegacy).toHaveBeenCalledOnce();
  });
});
