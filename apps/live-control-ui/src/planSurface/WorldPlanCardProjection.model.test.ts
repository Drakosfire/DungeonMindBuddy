import { describe, expect, it } from "vitest";

import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { buildWorldPlanCardProjectionModel } from "./components/WorldPlanCardProjection";

function project(markdown: string) {
  const imported = markdownToTiptapDoc(markdown);
  const warnings = imported.diagnostics
    .filter((diagnostic) => diagnostic.level === "warning")
    .map((diagnostic) => diagnostic.message);
  return buildWorldPlanCardProjectionModel({ document: imported.doc, markdown, sourceWarnings: warnings });
}

describe("buildWorldPlanCardProjectionModel", () => {
  it("projects v1 Scene-first membership and document order without absorbing trailing instructions", () => {
    const model = project([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
      "## Arrival",
      "Scene overview.",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:gate -->",
      "### The gate",
      "Gate body.",
      "### Ordinary H3 note",
      "H3 remains body prose.",
      "#### Ordinary H4 note",
      "H4 remains body prose.",
      "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
      "### Choose a route",
      "Choice prompt.",
      "<!-- dmb-playable-element:v1 kind=option id=option:run -->",
      "#### Run through the gate",
      "Option text.",
      "## GM Instructions",
      "Keep this in the complete Document view.",
    ].join("\n"));

    expect(model.status).toBe("ready");
    if (model.status !== "ready") return;
    expect(model.version).toBe("v1");
    expect(model.roots.map((node) => node.id)).toEqual(["scene:arrival"]);
    const scene = model.roots[0]!;
    expect(scene.children.map((node) => node.id)).toEqual(["beat:gate", "choice:route"]);
    expect(scene.bodyText).toBe("Scene overview.");
    expect(scene.children[0]?.bodyText).toContain("Ordinary H3 note");
    expect(scene.children[0]?.bodyText).toContain("H3 remains body prose.");
    expect(scene.children[0]?.bodyText).toContain("H4 remains body prose.");
    const choice = scene.children[1]!;
    expect(choice.children.map((node) => node.id)).toEqual(["option:run"]);
    expect(choice.children[0]?.bodyText).toBe("Option text.");
    expect(JSON.stringify(model)).not.toContain("Keep this in the complete Document view");
  });

  it("projects v2 Beat-first hierarchy and displays authored edges without interpreting them", () => {
    const model = project([
      "<!-- dmb-playable-element:v2 kind=beat id=beat:arrival beat_kind=spine -->",
      "## Arrival",
      "Beat overview.",
      "<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->",
      "### The gate",
      "Scene body.",
      "<!-- dmb-playable-element:v2 kind=choice id=choice:open scene=scene:gate -->",
      "### What do you do?",
      "Choice body.",
      "<!-- dmb-playable-element:v2 kind=option id=option:open activates=scene:gate suppresses=beat:after -->",
      "- Open it",
      "<!-- dmb-playable-element:v2 kind=beat id=beat:after beat_kind=optional -->",
      "## Aftermath",
      "Aftermath body.",
      "## GM Notes",
      "These instructions stay in Document.",
    ].join("\n"));

    expect(model.status).toBe("ready");
    if (model.status !== "ready") return;
    expect(model.version).toBe("v2");
    expect(model.roots.map((node) => node.id)).toEqual(["beat:arrival", "beat:after"]);
    expect(model.roots[0]?.beatKind).toBe("spine");
    expect(model.roots[0]?.children.map((node) => node.id)).toEqual(["scene:gate", "choice:open"]);
    const choice = model.roots[0]!.children[1]!;
    expect(choice.sceneId).toBe("scene:gate");
    expect(choice.children[0]).toMatchObject({
      id: "option:open",
      activates: ["scene:gate"],
      suppresses: ["beat:after"],
    });
    expect(JSON.stringify(model)).not.toContain("These instructions stay in Document");
  });

  it("retains inline atoms, marks, paragraphs, and nested lists in v1 and v2 card slices", () => {
    const v1 = project([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
      "## Arrival [Gate](dmb-node:node:gate)",
      "First paragraph with **bold** and [Captain](#dmb-ref:npc:captain).",
      "",
      "Second paragraph.",
      "",
      "- First item",
      "  - Nested item",
    ].join("\n"));
    expect(v1.status).toBe("ready");
    if (v1.status !== "ready") return;
    const scene = v1.roots[0]!;
    expect(scene.titleContent).toContainEqual(
      expect.objectContaining({ type: "graphNodeReference", attrs: { nodeId: "node:gate", label: "Gate" } }),
    );
    expect(scene.bodyContent.map((node) => node.type)).toEqual([
      "paragraph",
      "paragraph",
      "bulletList",
    ]);
    expect(scene.bodyContent[0]?.content).toContainEqual(
      expect.objectContaining({ type: "text", text: "bold", marks: [{ type: "bold" }] }),
    );
    expect(scene.bodyContent[0]?.content).toContainEqual(
      expect.objectContaining({ type: "runbookReference", attrs: expect.objectContaining({ refId: "captain", label: "Captain" }) }),
    );
    expect(scene.bodyContent[2]?.content?.[0]?.content?.[1]).toMatchObject({ type: "bulletList" });

    const v2Markdown = [
      "<!-- dmb-playable-element:v2 kind=beat id=beat:arrival beat_kind=spine -->",
      "## Arrival",
      "<!-- dmb-playable-element:v2 kind=choice id=choice:route -->",
      "### Choose a route",
      "The party reaches the gate.",
      "<!-- dmb-playable-element:v2 kind=option id=option:open -->",
      "- [Open the gate](#dmb-ref:citation:gate-key) **now**",
      "",
      "  The group advances.",
      "",
      "  - Keep the lantern raised.",
      "## GM instructions",
      "This remains outside the cards.",
    ].join("\n");
    const importedV2 = markdownToTiptapDoc(v2Markdown);
    expect(importedV2.diagnostics).toEqual([]);
    const v2 = buildWorldPlanCardProjectionModel({ document: importedV2.doc, markdown: v2Markdown, sourceWarnings: [] });
    expect(v2.status).toBe("ready");
    if (v2.status !== "ready") return;
    const option = v2.roots[0]!.children[0]!.children[0]!;
    expect(option.titleContent).toContainEqual(
      expect.objectContaining({ type: "runbookReference", attrs: expect.objectContaining({ refId: "gate-key", label: "Open the gate" }) }),
    );
    expect(option.titleContent).toContainEqual(
      expect.objectContaining({ type: "text", text: "now", marks: [{ type: "bold" }] }),
    );
    expect(option.bodyContent.map((node) => node.type)).toEqual(["paragraph", "bulletList"]);
    expect(option.bodyContent[1]).toMatchObject({ type: "bulletList" });
    expect(JSON.stringify(option.bodyContent[1])).toContain("Keep the lantern raised.");
    expect(JSON.stringify(v2)).not.toContain("This remains outside the cards.");
  });

  it("leaves unmarked Plan prose unclassified and gives an empty projection", () => {
    const model = project("# Prep\n\n## A heading that looks like a scene\n\nNo marker was authored.\n");
    expect(model).toEqual({ status: "empty" });
  });

  it.each([
    ["unknown marker version", "<!-- dmb-playable-element:v3 kind=scene id=scene:a -->\n## A"],
    ["mixed grammar", "<!-- dmb-playable-element:v1 kind=scene id=scene:a -->\n## A\n<!-- dmb-playable-element:v2 kind=beat id=beat:b -->\n## B"],
    ["malformed marker-like text", "<!-- dmb-playable-element:v2 kind=scene id=scene:a extra=yes -->\n## A"],
  ])("fails closed with no cards for %s", (_label, markdown) => {
    const model = project(markdown);
    expect(model.status).toBe("blocked");
    if (model.status === "blocked") expect(model.diagnostics.length).toBeGreaterThan(0);
  });

  it("treats marker-like text inside fenced code as ordinary source text", () => {
    const markdown = "```md\n<!-- dmb-playable-element:v3 kind=scene id=scene:a -->\n```\n";
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics.some((diagnostic) => diagnostic.message.includes("Fenced code blocks"))).toBe(true);
    const model = buildWorldPlanCardProjectionModel({ document: imported.doc, markdown });
    expect(model).toEqual({ status: "empty" });
  });

  it.each([
    ["orphan v1 Choice", "<!-- dmb-playable-element:v1 kind=choice id=choice:a -->\n### A"],
    ["orphan v1 Option", "<!-- dmb-playable-element:v1 kind=option id=option:a -->\n#### A"],
    ["orphan v2 Choice", "<!-- dmb-playable-element:v2 kind=choice id=choice:a -->\n### A"],
    ["orphan v2 Option", "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->\n## A\n<!-- dmb-playable-element:v2 kind=option id=option:a -->\n- A"],
  ])("fails closed for %s", (_label, markdown) => {
    const model = project(markdown);
    expect(model.status).toBe("blocked");
    if (model.status === "blocked") expect(model.diagnostics.length).toBeGreaterThan(0);
  });

  it.each([
    ["invalid v2 Scene association", [
      "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->", "## A",
      "<!-- dmb-playable-element:v2 kind=choice id=choice:a scene=scene:missing -->", "### Choice",
    ].join("\n")],
    ["unresolved authored edge", [
      "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->", "## A",
      "<!-- dmb-playable-element:v2 kind=choice id=choice:a -->", "### Choice",
      "<!-- dmb-playable-element:v2 kind=option id=option:a activates=beat:missing -->", "- Option",
    ].join("\n")],
  ])("fails closed for %s without a partial card tree", (_label, markdown) => {
    const model = project(markdown);
    expect(model.status).toBe("blocked");
    expect(JSON.stringify(model)).not.toContain("\"roots\"");
  });

  it("blocks the whole projection when source diagnostics cannot be preserved", () => {
    const markdown = "<!-- dmb-playable-element:v1 kind=scene id=scene:a -->\n## A";
    const imported = markdownToTiptapDoc(markdown);
    const model = buildWorldPlanCardProjectionModel({
      document: imported.doc,
      markdown,
      sourceWarnings: ["unsupported source structure"],
    });
    expect(model.status).toBe("blocked");
  });
});
