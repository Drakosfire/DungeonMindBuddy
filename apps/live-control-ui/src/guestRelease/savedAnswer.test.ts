import { expect, it } from "vitest";
import { isSavedAnswerText } from "./savedAnswer";
import cases from "./savedAnswerParity.json";

it.each(cases)("matches saved-answer text contract: $name", ({ text, repeat, limit, multiline, valid }) => {
  expect(isSavedAnswerText(text.repeat(repeat ?? 1), limit, multiline)).toBe(valid);
});
