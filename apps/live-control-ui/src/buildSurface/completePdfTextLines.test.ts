import { expect, it } from "vitest";
import { completePdfTextLines, hasClippedPdfTextLine, pdfTextBoundsOverlap } from "./completePdfTextLines";

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
  const inside = { text: "Range 3", complete: true, overlaps: true, endOfLine: false };
  const outside = { text: "0 ft.", complete: false, overlaps: false, endOfLine: true };
  expect(hasClippedPdfTextLine([inside, outside])).toBe(true);
  expect(hasClippedPdfTextLine([{ ...inside, endOfLine: true }, outside])).toBe(false);
});

it("detects overlap when a text run midpoint is outside the crop", () => {
  const crop = { left: 0.7, top: 0.2, width: 0.2, height: 0.2 };
  const corners = [[0.1, 0.25], [0.8, 0.25], [0.1, 0.3], [0.8, 0.3]] as const;
  const overlaps = pdfTextBoundsOverlap(corners, crop);
  expect(hasClippedPdfTextLine([{ text: "Range 30 ft.", complete: false, overlaps, endOfLine: true }])).toBe(true);
  expect(pdfTextBoundsOverlap(corners, { ...crop, left: 0.8 })).toBe(false);
});
