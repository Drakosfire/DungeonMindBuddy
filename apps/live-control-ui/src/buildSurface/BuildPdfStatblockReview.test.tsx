import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch, listSavedMechanicsVersions } from "../api/liveApi";
import { baseCandidateDefinition } from "../statblocks/editor/editorFixtures";
import { BuildPdfStatblockReview } from "./BuildPdfStatblockReview";

vi.mock("../api/liveApi", () => ({ authenticatedApiFetch: vi.fn(), listSavedMechanicsVersions: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("reopens a draft and saves edits against the exact retained regions", async () => {
  const definition = baseCandidateDefinition();
  const regions = [{ source_revision_id: "srev:test", content_sha256: "a".repeat(64),
    page: 2, left: 0, top: 0, right: 1, bottom: 1 }];
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockImplementation(async (path, init) => {
    if (path.endsWith("/validate?expected_revision=4")) {
      expect(init).toEqual({ method: "POST" });
      return { response: Response.json({ validation: { outcome: "success", validation_receipt: { status: "warnings", issues: [{ severity: "warning", field_path: "/identity/name", message: "Check the printed name" }] } } }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
    }
    if (init?.method === "PUT") {
      const payload = JSON.parse(String(init.body));
      expect(payload.expected_revision).toBe(4);
      expect(payload.regions).toEqual(regions);
      expect(payload.definition.identity.name).toBe("Revised creature");
      return { response: Response.json({ revision: 5, definition: payload.definition, regions }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
    }
    expect(path).toContain("/elderwyld/build-pdf-sources/statblock-reviews/review");
    return { response: Response.json({ revision: 4, definition, regions }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
  });

  render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
  const name = await screen.findByRole("textbox", { name: "Creature name" });
  fireEvent.click(screen.getByRole("button", { name: "Validate mechanics" }));
  await screen.findByText("Mechanics validated with warnings.");
  expect(screen.getByText(/Check the printed name/)).toBeInTheDocument();
  fireEvent.change(name, { target: { value: "Revised creature" } });
  expect(screen.queryByText("Mechanics validated with warnings.")).toBeNull();
  expect(screen.queryByText(/Check the printed name/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Save review draft" }));
  await waitFor(() => expect(screen.getByText("Draft saved")).toBeInTheDocument());
  expect(screen.getByRole("button", { name: "Open source region 1 · Page 2" })).toBeInTheDocument();
});

it.each([false, true])("recovers an acceptance failure (stale draft: %s)", async stale => {
  localStorage.clear();
  const requests: string[] = [];
  const fetch = vi.mocked(authenticatedApiFetch);
  fetch.mockImplementation(async (path, init) => {
    let data: unknown;
    if (path.startsWith("/api/live/threat-drafts?world_id=elderwyld")) {
      data = { drafts: [{ draft_id: "draft-a", version: stale && requests.length ? 9 : 8, name: "Creature draft A" }] };
    } else if (path.endsWith("/validate?expected_revision=4")) {
      data = { validation: { outcome: "success", definition_digest: "sha256:fixture",
        validation_receipt: { status: "valid" } } };
    } else if (path.endsWith("/accept/draft-a")) {
      requests.push(String(init?.body));
      if (requests.length === 1 && !stale) throw new Error("Response lost");
      if (requests.length === 1) {
        return { response: Response.json({ result_label: "acceptance_blocked",
          message: "expected draft version mismatch" }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
      }
      data = { result_label: "mechanics_saved", locator: { revision_id: "rev_a" } };
    } else {
      data = { revision: 4, definition: baseCandidateDefinition(), regions: [] };
    }
    return { response: Response.json(data) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
  });

  render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
  fireEvent.click(await screen.findByRole("button", { name: "Choose creature draft" }));
  fireEvent.change(await screen.findByRole("combobox", { name: "Creature draft" }), {
    target: { value: "draft-a" },
  });
  const accept = screen.getByRole("button", { name: "Accept mechanics" });
  fireEvent.click(accept);
  await screen.findByRole("alert");
  fireEvent.click(accept);
  expect(await screen.findByRole("link", { name: "Open accepted statblock" })).toHaveAttribute(
    "href", "/statblock?world=elderwyld&draft=draft-a&revision=rev_a",
  );
  expect(requests).toHaveLength(2);
  if (stale) {
    expect(JSON.parse(requests[1])).toMatchObject({ expected_draft_version: 9 });
    expect(JSON.parse(requests[1]).operation_id).not.toBe(JSON.parse(requests[0]).operation_id);
  } else {
    expect(requests[0]).toBe(requests[1]);
  }
  expect(JSON.parse(requests[0])).toMatchObject({ expected_revision: 4, expected_draft_version: 8 });
  localStorage.clear();
});

it("appends to the explicitly selected saved revision and replays its request", async () => {
  localStorage.clear();
  const base = { revision_id: "rev_base", statblock_id: "sb_a" };
  vi.mocked(listSavedMechanicsVersions).mockResolvedValue({
    original: base, operations: [],
  } as Awaited<ReturnType<typeof listSavedMechanicsVersions>>);
  const attempts: string[] = [];
  vi.mocked(authenticatedApiFetch).mockImplementation(async (path, init) => {
    let data: unknown = { revision: 4, definition: baseCandidateDefinition(), regions: [] };
    if (path.includes("/threat-drafts?")) {
      data = { drafts: [{ draft_id: "draft-a", name: "Creature A", workflow_state: "mechanics_saved" }] };
    } else if (path.endsWith("/append/draft-a")) {
      attempts.push(String(init?.body));
      data = attempts.length === 1 ? { state: "outcome_unknown" }
        : { state: "committed", result: { revision_id: "rev_new" } };
    }
    return { response: Response.json(data) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
  });
  render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
  fireEvent.click(await screen.findByRole("button", { name: "Choose creature draft" }));
  fireEvent.change(await screen.findByRole("combobox", { name: "Creature draft" }), { target: { value: "draft-a" } });
  await screen.findByRole("option", { name: /rev_base/ });
  fireEvent.change(screen.getByRole("combobox", { name: "Parent statblock version" }), { target: { value: "rev_base" } });
  const append = screen.getByRole("button", { name: "Append mechanics revision" });
  fireEvent.click(append);
  await screen.findByRole("alert");
  fireEvent.click(append);
  expect(await screen.findByRole("link", { name: "Open accepted statblock" })).toHaveAttribute(
    "href", "/statblock?world=elderwyld&draft=draft-a&revision=rev_new",
  );
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toBe(attempts[1]);
  expect(JSON.parse(attempts[0])).toMatchObject({ expected_revision: 4, base });
  localStorage.clear();
});
