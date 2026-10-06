import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorldPlanAgentAnswer } from "./WorldPlanAgentAnswer";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("WorldPlanAgentAnswer", () => {
  it("renders paragraphs, bold emphasis, lists, and embedded reference labels", () => {
    const answer = [
      "**Saved Plan:** The party reaches the warehouse.",
      "",
      "**Evidence:** Exact support remains visible beside the answer.",
      "",
      "- Lysandra watches the loading bay.",
      "- Check the upper windows.",
      "",
      "The party can ask [Lysandra Ironveil](dmb-node:lysandra-ironveil) for help.",
    ].join("\n");
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);

    expect(container.querySelectorAll(":scope > p")).toHaveLength(3);
    expect(container.querySelectorAll(":scope > ul > li")).toHaveLength(2);
    expect(container.querySelectorAll("strong")).toHaveLength(2);
    const reference = container.querySelector('[data-plan-card-reference="graph"]');
    expect(reference?.textContent).toBe("Lysandra Ironveil");
    expect(container.textContent).toContain("Saved Plan:");
    expect(container.textContent).toContain("Evidence:");
    expect(container.textContent).toContain("Exact support remains visible beside the answer.");
  });

  it("shows unsupported HTML, unsafe links, and media as escaped source without executing or fetching", () => {
    const request = vi.fn();
    vi.stubGlobal("fetch", request);
    const answer = [
      "<script>window.compromised = true</script>",
      "",
      "[Open this](javascript:alert(1))",
      "",
      "![remote portrait](https://media.example.invalid/portrait.png)",
      "",
      "<iframe src=\"https://media.example.invalid/embed\"></iframe>",
    ].join("\n");
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);

    expect(container.textContent).toBe(answer);
    expect(container.querySelector("script, iframe, img, video, audio")).toBeNull();
    expect(container.querySelector("a[href^='javascript:']")).toBeNull();
    expect(request).not.toHaveBeenCalled();
    expect((window as Window & { compromised?: boolean }).compromised).toBeUndefined();
  });

  it("preserves unsupported Markdown as whitespace-preserving readable text", () => {
    const answer = "First paragraph.\n\nSecond paragraph with a hard break\\\nnext line.";
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);

    expect(container.textContent).toBe(answer);
    expect(container.querySelector("br, img, iframe, script")).toBeNull();
    expect(container.querySelector("p")).toHaveStyle({ whiteSpace: "pre-wrap" });
  });

  it("keeps hook order stable as validated segment boundaries appear and cease to match", () => {
    const answer = "**Saved Plan:** First claim.\n**Evidence:** Second claim.";
    const { container, rerender } = render(<WorldPlanAgentAnswer answer={answer} />);

    rerender(<WorldPlanAgentAnswer answer={answer} displaySegments={["**Saved Plan:** First claim.", "**Evidence:** Second claim."]} />);
    expect(container.querySelectorAll(".world-plan-agent-answer > .world-plan-agent-answer")).toHaveLength(2);

    rerender(<WorldPlanAgentAnswer answer={answer} displaySegments={["unmatched segment"]} />);
    expect(container.textContent).toContain("Saved Plan:");
    expect(container.textContent).toContain("Evidence:");
    expect(container.querySelectorAll(".world-plan-agent-answer > .world-plan-agent-answer")).toHaveLength(0);
  });
});
