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
  it("rejects unsupported v1 cards instead of projecting a compatibility hierarchy", () => {
    const model = project("<!-- dmb-playable-element:v1 kind=scene id=scene:old -->\n## Old scene\nRetained source.\n");
    expect(model.status).toBe("blocked");
    if (model.status === "blocked") expect(model.diagnostics.some(entry => entry.code === "unsupported_version")).toBe(true);
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
