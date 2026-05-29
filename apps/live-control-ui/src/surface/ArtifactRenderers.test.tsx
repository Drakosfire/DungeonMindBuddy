import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeEventArtifact, makeRollTableArtifact } from "../test/fixtures";
import { EventArtifactRenderer, RollTableArtifactRenderer } from "./ArtifactRenderers";

describe("ArtifactRenderers", () => {
  it("renders event artifact fields read-only", () => {
    const artifact = makeEventArtifact({
      title: "Weather: rolled 16",
    });
    render(<EventArtifactRenderer artifact={artifact as typeof artifact & { artifact_kind: "event" }} />);

    expect(screen.getByText("Weather: rolled 16")).toBeInTheDocument();
    expect(screen.getByText("roll_result")).toBeInTheDocument();
    expect(screen.getByText("fast_live")).toBeInTheDocument();
    expect(screen.getByText("Weather resolved to 16.")).toBeInTheDocument();
    expect(screen.getByText("Weather 16.")).toBeInTheDocument();
    expect(screen.getByText(/"table_id": "T-WX"/)).toBeInTheDocument();
  });

  it("renders roll-table artifact metadata and markdown read-only", () => {
    const artifact = makeRollTableArtifact({
      payload: {
        content_type: "text/markdown",
        data: null,
        text: "## 1-4\nFog",
      },
    });
    render(
      <RollTableArtifactRenderer artifact={artifact as typeof artifact & { artifact_kind: "roll_table" }} />,
    );

    expect(screen.getByText("Storm weather")).toBeInTheDocument();
    expect(screen.getByText("T-WX")).toBeInTheDocument();
    expect(screen.getByText("d20")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("fast_live")).toBeInTheDocument();
    expect(screen.getByText(/## 1-4[\s\S]*Fog/)).toBeInTheDocument();
  });
});
