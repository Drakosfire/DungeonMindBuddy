import { describe, expect, it } from "vitest";

import {
  requestedCampaignFromLocation,
  requestedDocumentIdFromLocation,
  requestedSessionNumberFromLocation,
} from "./sessionCampaignContext";

describe("sessionCampaignContext", () => {
  it("parses campaign and session query params", () => {
    expect(requestedCampaignFromLocation("?campaign=longmont-c2")).toBe("longmont-c2");
    expect(requestedSessionNumberFromLocation("?session=24")).toBe(24);
    expect(requestedSessionNumberFromLocation("?session=session-24")).toBe(24);
  });

  it("parses opaque documentId query param", () => {
    expect(requestedDocumentIdFromLocation("?documentId=11111111-1111-4111-8111-111111111111"))
      .toBe("11111111-1111-4111-8111-111111111111");
    expect(requestedDocumentIdFromLocation("?session=24")).toBeNull();
  });
});
