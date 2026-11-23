import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { GuestReleaseSelection } from "./GuestReleaseSelection";

afterEach(() => vi.unstubAllGlobals());

it("requires explicit fields and evidence before staging the exact selection", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const body = String(input).endsWith("/selection-context") ? { graph_revision: "rev", next_offset: null, sources: [
      { option_id: "recap", document_id: "recap-doc", document_title: "Recap", visibility: "internal", revision_n: 1,
        sha256: "c".repeat(64), start: 0, end: 8, excerpt: "outcomes", evidence_id: "recap-evidence", evidence_role: "context" }] }
      : String(input).endsWith("/selection-media/list") ? { assets: [{ id: "image", width: 2, height: 2, created_at: "2026-11-20T00:00:00Z" }], next: null }
      : init?.method === "POST" ? { release_id: "candidate", digest: "digest" } : {
      graph_revision: "rev", context_documents: [{ document_id: "recap-doc", title: "Recap" }], fields: [
        { assertion_id: "name", entity_id: "entity", kind: "name", value: "Sizzek", predicate: "dnd5e:name", target_id: null, temporal: "unknown", basis: "inferred", source_option_ids: ["option"] },
        { assertion_id: "kind", entity_id: "entity", kind: "classification", value: "character", predicate: "dnd5e:classification", target_id: null, temporal: "unknown", basis: "inferred", source_option_ids: ["option2"] },
      ], sources: [{ option_id: "option", document_id: "doc", document_title: "Apprentice", visibility: "internal", revision_n: 1,
        sha256: "a".repeat(64), start: 0, end: 4, excerpt: "clue", evidence_id: "evidence", evidence_role: "context" },
        { option_id: "option2", document_id: "doc2", document_title: "Carnival", visibility: "internal", revision_n: 1,
          sha256: "b".repeat(64), start: 0, end: 5, excerpt: "other", evidence_id: "evidence2", evidence_role: "support" }],
    };
    return new Response(JSON.stringify(body), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
  const prepared = vi.fn();
  const user = userEvent.setup();
  render(<GuestReleaseSelection worldId="world" onPrepared={prepared} />);
  await user.click(screen.getByRole("button", { name: "Load selection options" }));
  const name = await screen.findByRole("checkbox", { name: /name: Sizzek/ });
  const kind = screen.getByRole("checkbox", { name: /classification: character/ });
  const button = screen.getByRole("button", { name: "Prepare copy for review" });
  expect(button).toBeDisabled();
  await user.click(name); await user.click(kind);
  expect(button).toBeDisabled();
  const sourceSelects = screen.getAllByRole("combobox", { name: "Source excerpt" });
  await user.selectOptions(sourceSelects[0], "option"); await user.selectOptions(sourceSelects[1], "option2");
  expect(screen.getAllByText("clue").length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: /context, not direct support/ })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Load World images" }));
  const image = await screen.findByRole("img", { name: "World image 1" });
  const imageChoice = screen.getByRole("checkbox", { name: /Include image 1/ });
  expect(imageChoice).toBeDisabled();
  fireEvent.load(image);
  await user.click(imageChoice);
  await user.click(screen.getByRole("checkbox", { name: "Include an owner-authored saved example" }));
  await user.selectOptions(screen.getByLabelText("Source document"), "recap-doc");
  await user.click(screen.getByRole("button", { name: "Load source excerpts" }));
  expect(await screen.findByText("outcomes")).toBeInTheDocument();
  await user.click(screen.getByRole("checkbox", { name: /Recap · private source · context/ }));
  expect(button).toBeDisabled();
  await user.type(screen.getByLabelText("Example title"), "Saved scene");
  await user.type(screen.getByLabelText("Scene text"), "A scene");
  await user.click(screen.getByRole("checkbox", { name: /Apprentice · context/ }));
  await user.click(screen.getByRole("checkbox", { name: /Carnival · support/ }));
  await user.click(kind);
  expect(button).toBeDisabled();
  expect(screen.getByText(/no longer included; remove this reference/)).toBeInTheDocument();
  expect(screen.getByLabelText("Scene text")).toHaveValue("A scene");
  await user.click(kind);
  await user.selectOptions(screen.getAllByRole("combobox", { name: "Source excerpt" })[1], "option2");
  await user.selectOptions(screen.getByLabelText("Inline image"), "image");
  await user.type(screen.getByLabelText("Describe the image for guests"), "A red tent");
  await user.click(screen.getByRole("checkbox", { name: "Include a prewritten guest choice" }));
  expect(button).toBeDisabled();
  expect(screen.getByText(/Both outcomes will be public/)).toBeInTheDocument();
  await user.type(screen.getByLabelText("Choice prompt"), "What next");
  await user.type(screen.getByLabelText("Option 1 label"), "Enter");
  await user.type(screen.getByLabelText("Option 1 outcome"), "A bell rings");
  await user.type(screen.getByLabelText("Option 2 label"), "Wait");
  await user.type(screen.getByLabelText("Option 2 outcome"), "A lantern flickers");
  await user.click(button);
  expect(await screen.findByRole("status")).toHaveTextContent("Copy prepared");
  expect(prepared).toHaveBeenCalledOnce();
  const posted = fetchMock.mock.calls.find(([input, init]) => init?.method === "POST" && !String(input).endsWith("/selection-media/list") && !String(input).endsWith("/selection-context"));
  expect(JSON.parse(String(posted?.[1]?.body))).toMatchObject({ graph_revision: "rev", nodes: [{ entity_id: "entity",
    name_assertion_id: "name", kind_assertion_id: "kind", name_source_index: 0, kind_source_index: 1 }],
    sources: [{ document_id: "doc", excerpt: "clue", evidence_id: "evidence" }, { document_id: "doc2" },
      { document_id: "recap-doc", excerpt: "outcomes", evidence_id: "recap-evidence" }], relationships: [], asset_ids: ["image"],
    saved_example: { title: "Saved scene", body: "A scene", source_indexes: [0, 1], asset_id: "image", image_description: "A red tent" },
    saved_choice: { prompt: "What next", options: [{ label: "Enter", outcome: "A bell rings" }, { label: "Wait", outcome: "A lantern flickers" }] } });
});
