import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PlayMapOverlaySection } from "./PlayMapOverlaySection";
import { mapOverlayForMediaSrc } from "./ofConksMapOverlays";

describe("ofConksMapOverlays", () => {
  it("resolves Hempholm village overlay with five area pins", () => {
    const overlay = mapOverlayForMediaSrc(
      "/corpus/of-conks-cons-markdown/media/map-hempholm.jpg",
    );
    expect(overlay?.pins).toHaveLength(5);
    expect(overlay?.pins.map((p) => p.nodeId)).toContain("location:the-shacks");
    expect(overlay?.pins.map((p) => p.nodeId)).toContain("location:grotesque-tree-site");
  });
});

describe("PlayMapOverlaySection", () => {
  it("renders pins and opens a node on click", async () => {
    const user = userEvent.setup();
    const overlay = mapOverlayForMediaSrc(
      "/corpus/of-conks-cons-markdown/media/map-hempholm.jpg",
    );
    expect(overlay).not.toBeNull();
    const onSelectPin = vi.fn();
    render(
      <PlayMapOverlaySection
        media={{
          src: "/corpus/of-conks-cons-markdown/media/map-hempholm.jpg",
          alt: "Map of Hempholm",
          kind: "map",
        }}
        overlay={overlay!}
        activeNodeId="location:morwins-store"
        onSelectPin={onSelectPin}
      />,
    );

    expect(screen.getByTestId("play-map-overlay")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Map" })).toBeInTheDocument();
    const shacks = screen.getByRole("button", { name: /Open 1\. The Shacks/i });
    await user.click(shacks);
    expect(onSelectPin).toHaveBeenCalledWith(
      expect.objectContaining({ nodeId: "location:the-shacks", areaNumber: 1 }),
    );
  });
});
