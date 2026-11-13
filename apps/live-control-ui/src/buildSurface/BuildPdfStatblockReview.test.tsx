import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { authenticatedApiFetch, getThreatDraft, listSavedMechanicsVersions } from "../api/liveApi";
import { baseCandidateDefinition } from "../test/statblockEditorFixtures";
import { BuildPdfStatblockReview } from "./BuildPdfStatblockReview";

vi.mock("../api/liveApi", async importOriginal => ({ ...await importOriginal<typeof import("../api/liveApi")>(), getThreatDraft: vi.fn(), authenticatedApiFetch: vi.fn(), listSavedMechanicsVersions: vi.fn() }));
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
  fireEvent.click(await screen.findByRole("button", { name: "Developer tools" }));
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

it("opens the first exact source region automatically", async () => {
  const definition = baseCandidateDefinition();
  const regions = [{ source_revision_id: "srev:test", content_sha256: "a".repeat(64),
    page: 2, left: 0.1, top: 0.2, right: 0.8, bottom: 0.7 }];
  const fetch = vi.mocked(authenticatedApiFetch);
  const originalCreateObjectURL = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
  const originalRevokeObjectURL = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:source-region") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  try {
    fetch.mockImplementation(async (path, init) => {
      if (path.endsWith("/open?render=true")) {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual(regions[0]);
        return { response: new Response(new Blob(["source-image"], { type: "image/png" })) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
      }
      return { response: Response.json({ revision: 4, definition, regions }) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
    });

    render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);

    expect(await screen.findByRole("figure", { name: "Source evidence · Page 2" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Exact PDF region on page 2" })).toHaveAttribute("src", "blob:source-region");
  } finally {
    cleanup();
    if (originalCreateObjectURL) Object.defineProperty(URL, "createObjectURL", originalCreateObjectURL);
    else delete (URL as typeof URL & { createObjectURL?: typeof URL.createObjectURL }).createObjectURL;
    if (originalRevokeObjectURL) Object.defineProperty(URL, "revokeObjectURL", originalRevokeObjectURL);
    else delete (URL as typeof URL & { revokeObjectURL?: typeof URL.revokeObjectURL }).revokeObjectURL;
  }
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
  fireEvent.click(await screen.findByRole("button", { name: "Developer tools" }));
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
  type Versions = Awaited<ReturnType<typeof listSavedMechanicsVersions>>;
  vi.mocked(listSavedMechanicsVersions)
    .mockResolvedValueOnce({ original: { ...base, revision_id: "rev_original" }, operations: [], next_offset: 50 } as Versions)
    .mockResolvedValueOnce({ operations: [{ state: "committed", result: base }], next_offset: null } as Versions);
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
  fireEvent.click(await screen.findByRole("button", { name: "Developer tools" }));
  fireEvent.click(await screen.findByRole("button", { name: "Choose creature draft" }));
  fireEvent.change(await screen.findByRole("combobox", { name: "Creature draft" }), { target: { value: "draft-a" } });
  await screen.findByRole("option", { name: /rev_base/ });
  expect(listSavedMechanicsVersions).toHaveBeenLastCalledWith("draft-a", "elderwyld", 50);
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

it.each([401, 403, 404, 422])("retries creature creation after HTTP %s and selects the draft", async status => {
  localStorage.clear();
  try {
    let attempts = 0;
    vi.mocked(authenticatedApiFetch).mockImplementation(async path => {
      const response = path.endsWith("/creature-draft?expected_revision=4")
        ? ++attempts === 1
          ? Response.json({ detail: "Review data rejected" }, { status })
          : Response.json({ draft_id: "new-creature", version: 1 })
        : Response.json({ revision: 4, definition: baseCandidateDefinition(), regions: [] });
      return { response } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
    });
    vi.mocked(getThreatDraft).mockResolvedValueOnce({
        schema: "dmb_threat_draft_v2", draft_id: "new-creature", world_id: "elderwyld",
        name: "Creature", workflow_state: "drafting",
      } as Awaited<ReturnType<typeof getThreatDraft>>);
    render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
    fireEvent.click(await screen.findByRole("button", { name: "Developer tools" }));
    const create = await screen.findByRole("button", { name: "Create creature draft from review" });
    fireEvent.click(create);
    expect(await screen.findByRole("alert")).toHaveTextContent("Review data rejected");
    fireEvent.click(create);
    expect(await screen.findByRole("combobox", { name: "Creature draft" })).toHaveValue("new-creature");
    expect(screen.getByRole("button", { name: "Accept mechanics" })).toBeEnabled();
    expect(attempts).toBe(2);
    expect(getThreatDraft).toHaveBeenCalledWith("new-creature");
  } finally {
    localStorage.clear();
  }
});

it("saves and reopens edits with movement unspecified", async () => {
  let review = { revision: 4, definition: { ...baseCandidateDefinition(), movement: null }, regions: [] };
  vi.mocked(authenticatedApiFetch).mockImplementation(async (_, init) => {
    if (init?.method === "PUT") {
      const payload = JSON.parse(String(init.body));
      expect(payload.definition.movement).toBeNull();
      review = { ...review, revision: 5, definition: payload.definition };
    }
    return { response: Response.json(review) } as Awaited<ReturnType<typeof authenticatedApiFetch>>;
  });

  const view = render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
  fireEvent.change(await screen.findByRole("textbox", { name: "Creature name" }), {
    target: { value: "Edited tree" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save review draft" }));
  await screen.findByText("Draft saved");
  view.unmount();

  render(<BuildPdfStatblockReview worldId="elderwyld" reviewId="review" />);
  expect(await screen.findByRole("textbox", { name: "Creature name" })).toHaveValue("Edited tree");
  expect(screen.getByText(/Movement is unspecified/)).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Developer tools" }));
  expect(screen.getByRole("button", { name: "Validate mechanics" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Create creature draft from review" })).toBeDisabled();
});
