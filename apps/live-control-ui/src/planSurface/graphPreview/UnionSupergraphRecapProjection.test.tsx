import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";

describe("UnionSupergraphRecapProjection", () => {
  it("renders global pc_caelynn and session-23 focus metadata", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    expect(screen.getByText("Session focus lens")).toBeInTheDocument();
    expect(screen.getByText("longmont-c2:union-supergraph")).toBeInTheDocument();
    expect(screen.getAllByText("Caelynn").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Projected recap")).toHaveTextContent("Session 23 Sample");
  });

  it("distinguishes current session from prior context evidence", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    expect(screen.getAllByText("current session").length).toBeGreaterThan(0);
    expect(screen.getAllByText("prior context").length).toBeGreaterThan(0);
    expect(screen.getAllByText("recap").length).toBeGreaterThan(0);
    expect(screen.getAllByText("worldbuilding").length).toBeGreaterThan(0);
  });

  it("shows adjacency for the pinned node", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    expect(screen.getByLabelText("Adjacency from Caelynn")).toBeInTheDocument();
    expect(screen.getAllByText("Mireward Gate Incident").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Mirathorn").length).toBeGreaterThan(0);
    expect(screen.getAllByText("participated in Mireward Gate Incident").length).toBeGreaterThan(0);
    expect(screen.getAllByText("connected to Mirathorn").length).toBeGreaterThan(0);
  });

  it("pins adjacent nodes when adjacency buttons are clicked", () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    fireEvent.click(screen.getAllByRole("button", { name: /Mirathorn/i })[0]);
    expect(screen.getByRole("complementary", { name: "Global node detail" })).toHaveTextContent(
      "Mirathorn",
    );
  });

  it("pins recap pills when clicked", async () => {
    render(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const mirathornPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Mirathorn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(mirathornPill);
    expect(screen.getByRole("complementary", { name: "Global node detail" })).toHaveTextContent(
      "loc_mirathorn",
    );
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
    expect(caelynnPill).toHaveClass("session-active");

    const mirathornPill = screen
      .getAllByRole("button", { name: "Mirathorn" })
      .find((button) => button.classList.contains("recap-node-token"));
    expect(mirathornPill).toHaveClass("role-location");
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
    expect(hoverCard).toHaveTextContent("Caelynn");
    expect(hoverCard).toHaveTextContent("Why now");
    expect(hoverCard).toHaveTextContent("Known before");
    expect(hoverCard).toHaveTextContent("Held the Mireward gate during the incident");
    expect(hoverCard).toHaveTextContent("participated in Mireward Gate Incident");
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
