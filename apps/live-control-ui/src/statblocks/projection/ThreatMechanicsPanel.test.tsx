import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { ThreatMechanicsPanel } from "./ThreatMechanicsPanel";
import type { ThreatSheetBindingViewModel } from "./threatSheetViewModel";

const revision = revisionFixture as StatblockRevisionResourceV1;

function availableBinding(
  overrides: Partial<ThreatSheetBindingViewModel> = {},
): ThreatSheetBindingViewModel {
  return {
    relationshipEdgeId: "edge-1",
    bindingId: "bind-1",
    role: "primary",
    phaseKey: null,
    variantLabel: null,
    statblockId: revision.statblock_id,
    revisionId: revision.revision_id,
    definitionDigest: revision.definition_digest,
    hydrationStatus: "available",
    revision,
    message: null,
    ...overrides,
  };
}

describe("ThreatMechanicsPanel", () => {
  it("renders one exact admitted revision", () => {
    render(
      <ThreatMechanicsPanel loadStatus="ready" bindings={[availableBinding()]} />,
    );

    const renderer = document.querySelector("[data-statblock-renderer]");
    expect(renderer).toHaveAttribute("data-chrome", "campaign");
    expect(renderer?.textContent).toMatch(/Ironhide Brute/i);
    expect(screen.queryByTestId("threat-sheet-binding-status")).not.toBeInTheDocument();
  });

  it("shows every multi-binding status and does not hide a second exact revision", () => {
    const secondRevision = { ...revision, statblock_id: "sb_000002" };
    render(
      <ThreatMechanicsPanel
        loadStatus="ready"
        bindings={[
          availableBinding(),
          availableBinding({
            relationshipEdgeId: "edge-2",
            bindingId: "bind-2",
            role: "phase",
            phaseKey: "enraged",
            statblockId: "sb_000002",
            revision: secondRevision,
          }),
        ]}
      />,
    );

    expect(document.querySelectorAll("[data-statblock-renderer]")).toHaveLength(2);
    expect(screen.getByRole("heading", { name: /primary · available/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /phase · enraged · available/i })).toBeInTheDocument();
    expect(screen.queryByText(/add to combat/i)).not.toBeInTheDocument();
  });

  it("keeps an unavailable sibling visible while rendering the available revision", () => {
    render(
      <ThreatMechanicsPanel
        loadStatus="ready"
        bindings={[
          availableBinding(),
          availableBinding({
            relationshipEdgeId: "edge-2",
            bindingId: "bind-2",
            role: "variant",
            hydrationStatus: "unavailable",
            revision: null,
            message: "Exact revision is unavailable.",
          }),
        ]}
      />,
    );

    expect(document.querySelectorAll("[data-statblock-renderer]")).toHaveLength(1);
    expect(screen.getByTestId("threat-sheet-binding-status")).toHaveAttribute(
      "data-hydration-status",
      "unavailable",
    );
    expect(screen.getByText(/exact revision is unavailable/i)).toBeInTheDocument();
  });

  it("withholds StatblockRenderer when a claimed-available binding failed integrity", () => {
    render(
      <ThreatMechanicsPanel
        loadStatus="integrity_failure"
        message="Binding locator does not cohere with returned StatblockRevision identity."
        bindings={[
          availableBinding({
            hydrationStatus: "integrity_failure",
            revision: null,
            message: "Binding locator does not cohere with returned StatblockRevision identity.",
          }),
        ]}
      />,
    );

    expect(document.querySelector("[data-statblock-renderer]")).toBeNull();
    expect(screen.getByTestId("threat-sheet-load-status")).toHaveAttribute(
      "data-load-status",
      "integrity_failure",
    );
  });
});
