import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../api/types";
import { paintGraphNodePills } from "./paintGraphNodePills";

const alden: GraphProjectionNodeView = {
  node_id: "alden",
  label: "Alden",
  kind: "npc",
  role: "gate warden",
  summary: "Alden guards the western gate.",
  aliases: [],
  source_domains: [],
  evidence_badges: [],
  adjacency: [],
};

describe("paintGraphNodePills", () => {
  it("applies role, pinned, and delta badge classes without rewriting structure", () => {
    const root = document.createElement("div");
    root.innerHTML = `
      <button type="button" class="graph-node-reference-pill recap-node-token" data-graph-node-id="alden">
        Alden
      </button>
      <button type="button" class="graph-node-reference-pill recap-node-token" data-graph-node-id="other">
        Other
      </button>
    `;

    const painted = paintGraphNodePills(root, {
      nodeViews: { alden },
      activeNodeId: "alden",
      deltaByNodeId: {
        alden: { status: "live_only", label: "live only", summary: "only in live" },
      },
    });

    expect(painted).toBe(2);
    const aldenButton = root.querySelector<HTMLButtonElement>('button[data-graph-node-id="alden"]');
    expect(aldenButton?.classList.contains("pinned")).toBe(true);
    expect(aldenButton?.className).toMatch(/role-gate-warden|role-npc/);
    expect(aldenButton?.dataset.deltaStatus).toBe("live_only");
    expect(aldenButton?.querySelector(".graph-review-pill-delta-badge")?.textContent).toBe(
      "live only",
    );

    const other = root.querySelector<HTMLButtonElement>('button[data-graph-node-id="other"]');
    expect(other?.classList.contains("pinned")).toBe(false);
    expect(other?.querySelector(".graph-review-pill-delta-badge")).toBeNull();
  });
});
