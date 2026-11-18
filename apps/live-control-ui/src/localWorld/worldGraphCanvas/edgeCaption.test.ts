import { describe, expect, it } from "vitest";
import { edgeCaption, overlaps, predicatePhrase } from "./edgeCaption";

describe("arrow phrases", () => {
  it("formats only underscores without inventing predicate semantics", () => {
    expect(predicatePhrase("travels_to")).toBe("travels to");
    expect(predicatePhrase("custom:knows_about")).toBe("custom:knows about");
    expect(predicatePhrase("not_associated_with")).toBe("not associated with");
  });
  it.each(["M 0 0 Q 200 0 400 0", "M 400 0 Q 200 0 0 0", "M 0 0 Q 0 200 0 400", "M 0 400 Q 0 200 0 0", "M 0 0 C 250 -150 250 150 0 100"])("keeps phrases upright on %s", path => {
    const label = edgeCaption(path, "travels_to")!;
    expect(label.angle).toBeGreaterThanOrEqual(-90);
    expect(label.angle).toBeLessThanOrEqual(90);
    expect(label.text).toBe("travels to");
    expect(Object.values(label.bounds).every(Number.isFinite)).toBe(true);
  });
  it("bounds long phrases, preserves Unicode code points and declines tiny gaps", () => {
    expect(edgeCaption("M 0 0 Q 10 0 20 0", "travels_to")).toBeNull();
    const result = edgeCaption("M 0 0 Q 80 0 160 0", "🌍".repeat(50))!;
    expect(result.text).toMatch(/^🌍+…$/u);
    expect(result.text.length).toBeLessThan(50);
  });
  it("detects overlapping caption rectangles", () => {
    expect(overlaps({ left: 0, top: 0, right: 20, bottom: 20 }, { left: 10, top: 10, right: 30, bottom: 30 })).toBe(true);
    expect(overlaps({ left: 0, top: 0, right: 20, bottom: 20 }, { left: 21, top: 0, right: 30, bottom: 20 })).toBe(false);
  });
});
