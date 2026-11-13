import { expect, it } from "vitest";
import { focusedGraphLayout } from "./focusedGraphLayout";
it("spreads a 23-bubble focal neighborhood without modifying saved pins", () => {
  const input = new Map(Array.from({ length: 23 }, (_, i) => [String(i), { x: i * 20, y: i * 7, radius: i ? 25 + i * 3 : 180 }]));
  const before = JSON.stringify([...input]);
  const result = focusedGraphLayout(input, "0");
  expect(JSON.stringify([...input])).toBe(before);
  expect(result.size).toBe(23);
  const points = [...result.values()];
  for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length; j++) {
    expect(Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y)).toBeGreaterThan((points[i].radius ?? 56) + (points[j].radius ?? 56) + 30);
  }
  expect(focusedGraphLayout(input, "missing")).toEqual(input);
});
