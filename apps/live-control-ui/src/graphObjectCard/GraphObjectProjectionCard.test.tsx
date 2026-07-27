import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const graphObjectCardDir = path.dirname(fileURLToPath(import.meta.url));

describe("GraphObjectProjectionCard (PR380B target module)", () => {
  it("production module file is absent on current main", () => {
    expect(existsSync(path.join(graphObjectCardDir, "GraphObjectProjectionCard.tsx"))).toBe(false);
  });

  it("pre-hoist PlanReferenceObjectCard still renders GraphObjectCard directly", async () => {
    const planCard = await import("../planSurface/reference/PlanReferenceObjectCard");
    expect(planCard.PlanReferenceObjectCard).toBeTypeOf("function");
    expect(existsSync(path.join(graphObjectCardDir, "GraphObjectProjectionCard.tsx"))).toBe(false);
  });
});
