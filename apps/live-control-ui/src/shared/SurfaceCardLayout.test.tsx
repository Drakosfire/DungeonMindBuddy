import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SceneCard } from "./SceneCard";
import { SurfaceCardLayout } from "./SurfaceCardLayout";
import { ReadOnlyBodyContent } from "../markdownReader/ReadOnlyBodyContent";
import layoutCss from "./surfaceCardLayout.css?raw";

afterEach(cleanup);
it("uncaps scene, beat and decision readers inside shared paper while retaining outside reader and media sizing", () => {
  const scene = { id: "scene:road", title: "Road", bodyText: "Scene prose" };
  render(<>
    <style>{".play-body { max-width: 78ch; }" + layoutCss}</style>
    <p className="play-body" data-testid="outside">Outside rail text</p>
    <SurfaceCardLayout data-testid="paper">
      <ReadOnlyBodyContent fallbackText="Beat prose" className="play-body" />
      <SceneCard identity={{ worldId: "world", documentId: "run", sceneId: scene.id,
        revision: 1, sourceState: "run-pin" }} scene={scene} kicker="" variant="play-current"
        choices={[{ id: "choice:road", title: "Route", bodyText: "Decision framing",
          selectedOptionId: "option:road", options: [{ id: "option:road", title: "Road option", bodyText: "Option consequence" }] }]}
        choiceActions={{}} />
      <img alt="Explicit media width" style={{ width: "55%" }} />
    </SurfaceCardLayout>
  </>);
  const paper = screen.getByTestId("paper");
  const readers = paper.querySelectorAll(".play-body");
  expect(readers.length).toBeGreaterThanOrEqual(4);
  for (const reader of readers) expect(getComputedStyle(reader).maxWidth).toBe("none");
  expect(getComputedStyle(screen.getByTestId("outside")).maxWidth).toBe("78ch");
  expect(screen.getByAltText("Explicit media width")).toHaveStyle({ width: "55%" });
});
