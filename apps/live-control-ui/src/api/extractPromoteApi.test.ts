import { afterEach, describe, expect, it, vi } from "vitest";

import { confirmExtractPromote } from "./extractPromoteApi";

function mockJsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    text: async () => JSON.stringify(payload),
  } as Response;
}

describe("extractPromoteApi confirm", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("confirmExtractPromote posts only schema, reviewPackage, and assertionIds", async () => {
    const reviewPackage = {
      schema: "dmb_extract_promote_proposal_v1",
      proposalId: "prop-1",
    };
    const assertionIds = ["a-hesta", "a-edge"];
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJsonResponse({
        schema: "dmb_extract_promote_confirm_v2",
        outcome: "committed",
        worldId: "eldyrwild",
        proposalId: "prop-1",
        proposalDigest: "digest-a",
        parentRevisionId: "rev:parent",
        committedRevisionId: "rev:committed",
        headAdvanced: true,
        selectedAssertionIds: assertionIds,
        acceptedAssertionIds: assertionIds,
        affectedObjectIds: ["obj-hesta"],
        appliedAssertionCount: 2,
        auditStatus: "ok",
        warnings: [],
      }),
    );

    await confirmExtractPromote({ reviewPackage, assertionIds });

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("/api/live/extract-promote/confirm");
    expect(init?.method).toBe("POST");
    const body = JSON.parse(String(init?.body));
    expect(body).toEqual({
      schema: "dmb_extract_promote_confirm_request_v2",
      reviewPackage,
      assertionIds,
    });
    expect(Object.keys(body)).toEqual(["schema", "reviewPackage", "assertionIds"]);
  });
});
