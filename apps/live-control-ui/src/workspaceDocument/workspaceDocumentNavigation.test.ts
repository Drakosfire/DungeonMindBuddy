import { describe, expect, it } from "vitest";

import { workspaceDocumentSelectionSearch } from "./workspaceDocumentNavigation";

describe("workspaceDocumentSelectionSearch", () => {
  const DOC_A = "11111111-1111-4111-8111-111111111111";
  const DOC_B = "22222222-2222-4222-8222-222222222222";

  it("sets the exact documentId and preserves session + campaigns lens params", () => {
    const next = workspaceDocumentSelectionSearch(
      "?session=longmont-c2:25&campaigns=longmont-c1,longmont-c2&documentId=" + DOC_A,
      DOC_B,
    );
    const params = new URLSearchParams(next);
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("session")).toBe("longmont-c2:25");
    expect(params.get("campaigns")).toBe("longmont-c1,longmont-c2");
  });

  it("preserves unrelated tool/dogfood state across selection", () => {
    const next = workspaceDocumentSelectionSearch("?dogfood=1&tool=recap&documentId=" + DOC_A, DOC_B);
    const params = new URLSearchParams(next);
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("dogfood")).toBe("1");
    expect(params.get("tool")).toBe("recap");
  });

  it("adds documentId to a param-less search without inventing other params", () => {
    const next = workspaceDocumentSelectionSearch("", DOC_B);
    expect(next).toBe(`?documentId=${DOC_B}`);
  });

  it("never writes the document title or target session into the search", () => {
    const next = workspaceDocumentSelectionSearch("?documentId=" + DOC_A, DOC_B);
    expect(next).not.toContain("Prep");
    expect(next).not.toContain("session");
  });
});
