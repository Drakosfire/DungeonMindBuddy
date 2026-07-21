import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GraphNodeHoverToken } from "./GraphNodeHoverToken";
import type { GraphNodeGlancePresentation } from "./types";

const presentation: GraphNodeGlancePresentation = {
  nodeId: "node:bubbles",
  label: "Bubbles the Float Goat",
  kind: "creature",
  role: "creature",
  summary: "A float goat rescued from the flooded river.",
  whyNow: null,
  knownBefore: "Tied to Mirathorn politics in character notes",
  planningChips: [{ label: "creature", tone: "neutral" }],
  threadHints: [
    {
      nodeId: "node:mireward",
      label: "Mireward Gate Incident",
      edgeLabel: "participated in Mireward Gate Incident",
      anchoredToFocusSession: true,
      rankReason: "current session",
    },
    {
      nodeId: "node:river",
      label: "Flooded River",
      edgeLabel: "rescued from Flooded River",
      anchoredToFocusSession: false,
    },
    {
      nodeId: "node:extra",
      label: "Extra Thread",
      edgeLabel: "should not appear in glance",
      anchoredToFocusSession: false,
    },
  ],
};

describe("GraphNodeHoverToken", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("renders a lean CSS hover glance without duplicated name/type chrome", () => {
    render(
      <GraphNodeHoverToken
        presentation={presentation}
        label={presentation.label}
        pinned={false}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Bubbles the Float Goat/i })).toBeInTheDocument();
    const wrap = document.querySelector(".recap-node-token-wrap.recap-node-glance");
    expect(wrap).toBeInTheDocument();
    const glance = wrap?.querySelector(".recap-node-hover-card");
    expect(glance).toBeInTheDocument();
    expect(glance).toHaveAttribute("role", "tooltip");

    // Summary + single type once; no name header, Known before, or role chip row.
    expect(glance).toHaveTextContent("A float goat rescued from the flooded river.");
    expect(glance?.querySelector(".recap-node-kind")?.textContent).toBe("creature");
    expect(glance?.textContent).not.toMatch(/creature\s*·\s*creature/i);
    expect(glance).not.toHaveTextContent("Known before");
    expect(glance).not.toHaveTextContent("Tied to Mirathorn politics");
    expect(glance?.querySelector(".recap-node-chip-row")).toBeNull();
    expect(glance?.querySelector("strong")).toBeNull();

    // Threads capped at two.
    const threadItems = glance?.querySelectorAll(".recap-planning-thread-list li") ?? [];
    expect(threadItems).toHaveLength(2);
    expect(glance).toHaveTextContent("participated in Mireward Gate Incident");
    expect(glance).not.toHaveTextContent("should not appear in glance");
  });

  it("shows distinct role · kind only when they differ", () => {
    render(
      <GraphNodeHoverToken
        presentation={{
          ...presentation,
          role: "npc",
          kind: "creature",
          knownBefore: null,
          planningChips: [],
          threadHints: [],
        }}
        label={presentation.label}
        pinned={false}
        onSelect={vi.fn()}
      />,
    );

    const kind = document.querySelector(".recap-node-hover-card .recap-node-kind");
    expect(kind?.textContent).toBe("npc · creature");
  });

  it("flips the glance above when Ask DungeonBuddy would cover it", () => {
    const shell = document.createElement("div");
    shell.className = "plan-agent-shell closed";
    document.body.appendChild(shell);
    Object.defineProperty(shell, "getBoundingClientRect", {
      value: () => ({
        top: 620,
        bottom: 800,
        left: 0,
        right: 400,
        width: 400,
        height: 180,
      }),
    });
    Object.defineProperty(window, "innerHeight", { configurable: true, value: 800 });

    render(
      <GraphNodeHoverToken
        presentation={presentation}
        label={presentation.label}
        pinned={false}
        onSelect={vi.fn()}
      />,
    );

    const wrap = document.querySelector(".recap-node-glance");
    const card = wrap?.querySelector(".recap-node-hover-card");
    expect(wrap).toBeTruthy();
    expect(card).toBeTruthy();

    Object.defineProperty(wrap!, "getBoundingClientRect", {
      value: () => ({
        top: 520,
        bottom: 540,
        left: 40,
        right: 180,
        width: 140,
        height: 20,
      }),
    });
    Object.defineProperty(card!, "getBoundingClientRect", {
      value: () => ({
        top: 0,
        bottom: 140,
        left: 0,
        right: 200,
        width: 200,
        height: 140,
      }),
    });

    fireEvent.mouseEnter(wrap!);

    expect(wrap).toHaveAttribute("data-open", "true");
    expect(wrap).toHaveClass("recap-node-glance--above");
    expect(card).toHaveAttribute("data-placement", "above");
  });
});
