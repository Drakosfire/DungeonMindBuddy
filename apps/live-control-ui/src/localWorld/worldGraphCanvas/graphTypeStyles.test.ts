import { describe, expect, it } from "vitest";
import { DEFAULT_GRAPH_TYPE_STYLES, graphTypeColor, type GraphTypeStyleRegistry } from "./graphTypeStyles";

describe("graph type presentation registry", () => {
  it("preserves configured types and aliases without changing recorded labels", () => {
    for (const [kind, style] of Object.entries(DEFAULT_GRAPH_TYPE_STYLES.types)) {
      expect(graphTypeColor(kind)).toBe(style.color);
      expect(graphTypeColor(kind.toUpperCase())).toBe(style.color);
      for (const alias of style.aliases ?? []) expect(graphTypeColor(alias)).toBe(style.color);
    }
  });
  it("uses the neutral fallback for unknown and prototype-like names", () => {
    for (const kind of ["future type", "object (mixed classifications)", "constructor", "__proto__", ""]) {
      expect(graphTypeColor(kind)).toBe(DEFAULT_GRAPH_TYPE_STYLES.fallbackColor);
    }
  });
  it("supports new types, aliases, overrides and fallback without mutating defaults", () => {
    const custom: GraphTypeStyleRegistry = {
      types: { ...DEFAULT_GRAPH_TYPE_STYLES.types, vehicle: { color: "#123456", aliases: ["ship"] }, place: { color: "#654321" } },
      fallbackColor: "#abcdef",
    };
    expect(graphTypeColor("SHIP", custom)).toBe("#123456");
    expect(graphTypeColor("place", custom)).toBe("#654321");
    expect(graphTypeColor("unknown", custom)).toBe("#abcdef");
    expect(graphTypeColor("ship")).toBe(DEFAULT_GRAPH_TYPE_STYLES.fallbackColor);
    expect(graphTypeColor("place")).toBe(graphTypeColor("location"));
  });
});
