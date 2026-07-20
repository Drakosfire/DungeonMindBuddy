import { describe, expect, it } from "vitest";

import {
  readBottomObstacleTop,
  resolveGlancePlacement,
} from "./glancePlacement";

describe("resolveGlancePlacement", () => {
  it("keeps the glance below when there is room under the token", () => {
    expect(
      resolveGlancePlacement({
        tokenTop: 100,
        tokenBottom: 120,
        cardHeight: 140,
        viewportHeight: 800,
        obstacleTop: 700,
      }),
    ).toBe("below");
  });

  it("flips above when the Ask DungeonBuddy shell would cover the card", () => {
    expect(
      resolveGlancePlacement({
        tokenTop: 520,
        tokenBottom: 540,
        cardHeight: 140,
        viewportHeight: 800,
        obstacleTop: 620,
      }),
    ).toBe("above");
  });

  it("uses the viewport floor when no obstacle is present", () => {
    expect(
      resolveGlancePlacement({
        tokenTop: 700,
        tokenBottom: 720,
        cardHeight: 140,
        viewportHeight: 800,
        obstacleTop: null,
      }),
    ).toBe("above");
  });

  it("prefers the side with more room when neither side fully fits", () => {
    expect(
      resolveGlancePlacement({
        tokenTop: 40,
        tokenBottom: 60,
        cardHeight: 200,
        viewportHeight: 200,
        obstacleTop: 120,
      }),
    ).toBe("below");
  });
});

describe("readBottomObstacleTop", () => {
  it("reads the closed Ask DungeonBuddy shell top edge", () => {
    const root = document.implementation.createHTMLDocument("test");
    const shell = root.createElement("div");
    shell.className = "plan-agent-shell closed";
    root.body.appendChild(shell);
    Object.defineProperty(shell, "getBoundingClientRect", {
      value: () => ({ top: 640, bottom: 800, left: 0, right: 100, width: 100, height: 160 }),
    });

    expect(readBottomObstacleTop(root)).toBe(640);
  });

  it("ignores the fullscreen-open shell", () => {
    const root = document.implementation.createHTMLDocument("test");
    const shell = root.createElement("div");
    shell.className = "plan-agent-shell open";
    root.body.appendChild(shell);
    Object.defineProperty(shell, "getBoundingClientRect", {
      value: () => ({ top: 0, bottom: 800, left: 0, right: 100, width: 100, height: 800 }),
    });

    expect(readBottomObstacleTop(root)).toBeNull();
  });
});
