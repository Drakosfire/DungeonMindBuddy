import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { GuestReleaseSelection } from "./GuestReleaseSelection";

afterEach(() => vi.unstubAllGlobals());

it("requires explicit fields and evidence before staging the exact selection", async () => {
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const body = init?.method === "POST" ? { release_id: "candidate", digest: "digest" } : {
      graph_revision: "rev", fields: [
        { assertion_id: "name", entity_id: "entity", kind: "name", value: "Sizzek", predicate: "dnd5e:name", target_id: null, temporal: "unknown", evidence_ids: ["evidence"] },
        { assertion_id: "kind", entity_id: "entity", kind: "classification", value: "character", predicate: "dnd5e:classification", target_id: null, temporal: "unknown", evidence_ids: ["evidence"] },
      ], sources: [{ document_id: "doc", document_title: "Apprentice", visibility: "internal", revision_n: 1,
        sha256: "a".repeat(64), start: 0, end: 4, excerpt: "clue", evidence_id: "evidence" }],
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
  for (const select of screen.getAllByRole("combobox", { name: "Supporting excerpt" })) await user.selectOptions(select, "evidence");
  expect(screen.getByText("clue")).toBeInTheDocument();
  await user.click(button);
  expect(await screen.findByRole("status")).toHaveTextContent("Copy prepared");
  expect(prepared).toHaveBeenCalledOnce();
  const posted = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(posted?.[1]?.body))).toMatchObject({ graph_revision: "rev", nodes: [{ entity_id: "entity",
    name_assertion_id: "name", kind_assertion_id: "kind", name_source_index: 0, kind_source_index: 0 }],
    sources: [{ document_id: "doc", excerpt: "clue", evidence_id: "evidence" }], relationships: [], asset_ids: [] });
});
