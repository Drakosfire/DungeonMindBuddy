import { expect, it } from "vitest";
import { completePdfTextLines, hasClippedPdfTextLine } from "./completePdfTextLines";

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

it("warns about text on a clipped line without counting entirely outside lines", () => {
  const inside = { text: "Range 3", complete: true, included: true, endOfLine: false };
  const outside = { text: "0 ft.", complete: false, included: false, endOfLine: true };
  expect(hasClippedPdfTextLine([inside, outside])).toBe(true);
  expect(hasClippedPdfTextLine([{ ...inside, endOfLine: true }, outside])).toBe(false);
});
