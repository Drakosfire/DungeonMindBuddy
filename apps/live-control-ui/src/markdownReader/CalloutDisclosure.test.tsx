import { fireEvent, render } from "@testing-library/react";
import { expect, it } from "vitest";
import { ReadOnlyBodyContent } from "./ReadOnlyBodyContent";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";

it("folds titled read-only blocks without replacing authored content on a parent rerender", () => {
  const content = markdownToTiptapDoc("> [!READ-ALOUD] North of Mireward Reach\n> The entire passage stays available.\n").doc.content;
  const { container, rerender } = render(<ReadOnlyBodyContent content={content} />);
  const details = container.querySelector("details")!;
  expect(details.querySelector("summary")?.textContent).toBe("Read aloud: North of Mireward Reach");
  fireEvent.click(details.querySelector("summary")!);
  expect(details.open).toBe(false);
  rerender(<ReadOnlyBodyContent content={content} />);
  expect(container.querySelector("details")).toBe(details);
  expect(details.open).toBe(false);
  expect(details.querySelector(".md-callout-body")?.textContent).toBe("The entire passage stays available.");
});
