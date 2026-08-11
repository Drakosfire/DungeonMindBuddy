import { describe, expect, it } from "vitest";

import { buildDocumentSelectionSearch } from "./buildDocumentNavigation";

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

describe("buildDocumentSelectionSearch", () => {
  it("sets documentId and campaign while preserving unrelated params", () => {
    const next = buildDocumentSelectionSearch(
      "?dogfood=1&tool=recap&campaign=longmont-c1&documentId=" + DOC_A,
      DOC_B,
      "longmont-c2",
    );
    const params = new URLSearchParams(next.slice(1));
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("campaign")).toBe("longmont-c2");
    expect(params.get("dogfood")).toBe("1");
    expect(params.get("tool")).toBe("recap");
  });

  it("preserves World Graph lens params when setting document identity", () => {
    const next = buildDocumentSelectionSearch(
      "?campaigns=longmont-c1,longmont-c2&session=longmont-c2:25&documentId=" + DOC_A,
      DOC_B,
      "longmont-c1",
    );
    const params = new URLSearchParams(next.slice(1));
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("campaign")).toBe("longmont-c1");
    expect(params.get("campaigns")).toBe("longmont-c1,longmont-c2");
    expect(params.get("session")).toBe("longmont-c2:25");
  });
});
