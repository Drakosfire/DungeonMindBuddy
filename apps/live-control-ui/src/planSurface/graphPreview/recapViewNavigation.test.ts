import { describe, expect, it } from "vitest";

import { buildRecapViewHref, normalizeRecapSessionParam } from "./recapViewNavigation";

describe("recapViewNavigation", () => {
  it("normalizes bare session numbers and session- ids", () => {
    expect(normalizeRecapSessionParam("25")).toBe("session-25");
    expect(normalizeRecapSessionParam("session-25")).toBe("session-25");
    expect(normalizeRecapSessionParam("SESSION-25")).toBe("session-25");
  });

  it("builds the Plan Recap View href", () => {
    expect(buildRecapViewHref("longmont-c2", "session-25")).toBe(
      "/plan?tool=recap&campaign=longmont-c2&session=session-25",
    );
    expect(buildRecapViewHref("longmont-c2", "25")).toBe(
      "/plan?tool=recap&campaign=longmont-c2&session=session-25",
    );
  });
});
