import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { expect, it } from "vitest";

import { BuildSourceWorkspace } from "./BuildSourceWorkspace";

function NotesEditor() {
  return <textarea aria-label="Notes" defaultValue="Draft notes" />;
}

function SourcePages() {
  const [page, setPage] = useState(1);
  return <>
    <p>Page {page}</p>
    <button type="button" onClick={() => setPage(2)}>Next page</button>
  </>;
}

it("keeps a notes editor mounted while navigating its source", () => {
  render(<BuildSourceWorkspace source={<SourcePages />}>
    <NotesEditor />
  </BuildSourceWorkspace>);

  const artifact = within(screen.getByRole("region", { name: "Artifact" }));
  const source = within(screen.getByRole("region", { name: "Source document" }));
  const notes = artifact.getByRole<HTMLTextAreaElement>("textbox", { name: "Notes" });
  fireEvent.change(notes, { target: { value: "Unsaved notes" } });
  fireEvent.click(source.getByRole("button", { name: "Next page" }));

  expect(source.getByText("Page 2")).toBeTruthy();
  expect(artifact.getByRole("textbox", { name: "Notes" })).toBe(notes);
  expect(notes.value).toBe("Unsaved notes");
});
