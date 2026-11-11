import { expect, it } from "vitest";
import { completePdfTextLines } from "./completePdfTextLines";

it("discards a line when the crop clips the last digit of an AC value", () => {
  const runs = [
    { text: "Armor Class 1", complete: true, endOfLine: false },
    { text: "6", complete: false, endOfLine: true },
    { text: "Hit Points 75", complete: true, endOfLine: true },
  ];
  expect(completePdfTextLines(runs)).toBe("\nHit Points 75");
  expect(completePdfTextLines(runs.map(run => ({ ...run, complete: true }))))
    .toBe("Armor Class 16\nHit Points 75");
});
