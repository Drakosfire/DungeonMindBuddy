import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../graphLens", () => ({
  useWorldGraphLensProjection: vi.fn(),
}));

vi.mock("../graphReference/ResolvedGraphObjectProjection", () => ({
  ResolvedGraphObjectProjection: ({ resolution }: { resolution: { graphObject: { label: string } } }) => (
    <div data-testid="resolved-graph-projection">{resolution.graphObject.label}</div>
  ),
}));

import { useWorldGraphLensProjection } from "../graphLens";
import { EmbedThreatSheetPage } from "./EmbedThreatSheetPage";

describe("EmbedThreatSheetPage", () => {
  beforeEach(() => {
    vi.mocked(useWorldGraphLensProjection).mockReset();
    window.history.replaceState({}, "", "/embed/threat-sheet");
  });

  it("errors when nodeId is missing", () => {
    vi.mocked(useWorldGraphLensProjection).mockReturnValue({
      request: null,
      requestKey: null,
      projection: null,
      projectionState: "ready",
      projectionError: null,
      nodeCount: 0,
      lastProjectionLoadMs: null,
      lastProjectionLoadOutcome: null,
    });

    render(<EmbedThreatSheetPage />);
    expect(screen.getByRole("alert")).toHaveTextContent(/Missing nodeId/i);
  });

  it("shows loading while projection is loading", () => {
    window.history.replaceState(
      {},
      "",
      "/embed/threat-sheet?nodeId=threat%3Aauthored%3Ad16d43d376833e38caf46dd19b1dd17f&label=Latchling",
    );
    vi.mocked(useWorldGraphLensProjection).mockReturnValue({
      request: null,
      requestKey: null,
      projection: null,
      projectionState: "loading",
      projectionError: null,
      nodeCount: 0,
      lastProjectionLoadMs: null,
      lastProjectionLoadOutcome: null,
    });

    render(<EmbedThreatSheetPage />);
    expect(screen.getByRole("status")).toHaveTextContent(/Loading World Graph projection/i);
  });
});
