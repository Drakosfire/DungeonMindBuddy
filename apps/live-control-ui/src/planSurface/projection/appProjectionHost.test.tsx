import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AdaptiveProjectionContainer } from "./AdaptiveProjectionContainer";
import {
  ProjectionProvider,
  useBindProjectionSurface,
  useProjection,
} from "./projectionContext";
import type { SurfaceConfig } from "../types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";

const planConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Plan",
    ingestSession: 21,
    liveSession: 22,
  },
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: "plan-doc" },
  theme: {},
  sessionDescriptor: fixturePlanSessionDescriptor({ memorySession: 21 }),
};

const ingestConfig: SurfaceConfig = {
  id: "ingest",
  label: "Ingest",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Ingest",
    ingestSession: 23,
    liveSession: 24,
  },
  tools: [{ id: "ingest-recap", label: "Ingest Recap", size: "wide" }],
  canvas: { documentId: null },
  theme: {},
};

function SurfaceBinder({ config }: { config: SurfaceConfig }) {
  useBindProjectionSurface(config);
  return <p data-testid="bound-surface">{config.id}</p>;
}

function ActiveProbe() {
  const { active, surfaceConfig } = useProjection();
  return (
    <>
      <p data-testid="surface-id">{surfaceConfig?.id ?? "none"}</p>
      <p data-testid="active-title">{active?.title ?? "none"}</p>
    </>
  );
}

describe("R10a app-scoped projection host", () => {
  it("keeps one host and clears active projection when surface binding changes", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ProjectionProvider>
        <SurfaceBinder config={planConfig} />
        <ActiveProbe />
        <AdaptiveProjectionContainer />
      </ProjectionProvider>,
    );

    expect(screen.getByTestId("app-projection-host")).toBeInTheDocument();
    expect(screen.getByTestId("surface-id")).toHaveTextContent("plan");

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await waitFor(() => {
      expect(screen.getByTestId("active-title")).toHaveTextContent("Statblock");
    });

    rerender(
      <ProjectionProvider>
        <SurfaceBinder config={ingestConfig} />
        <ActiveProbe />
        <AdaptiveProjectionContainer />
      </ProjectionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("surface-id")).toHaveTextContent("ingest");
    });
    expect(screen.getByTestId("active-title")).toHaveTextContent("none");
    expect(screen.getAllByTestId("app-projection-host")).toHaveLength(1);
  });

  it("hides the host when no surface is bound", () => {
    render(
      <ProjectionProvider>
        <AdaptiveProjectionContainer />
      </ProjectionProvider>,
    );
    expect(screen.queryByTestId("app-projection-host")).not.toBeInTheDocument();
  });
});
