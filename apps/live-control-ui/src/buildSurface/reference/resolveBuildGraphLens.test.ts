import { describe, expect, it } from "vitest";

import { resolveBuildGraphLens } from "./resolveBuildGraphLens";

describe("resolveBuildGraphLens", () => {
  describe("revision policy", () => {
    it("defaults to head when revision is absent or blank", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "doc-1",
          documentCampaignId: "longmont-c1",
          requestedCampaignId: null,
          requestedRevisionId: null,
        }).revision,
      ).toEqual({ kind: "head" });

      expect(
        resolveBuildGraphLens({
          documentId: "doc-1",
          documentCampaignId: "longmont-c1",
          requestedCampaignId: null,
          requestedRevisionId: "  ",
        }).revision,
      ).toEqual({ kind: "head" });
    });

    it("pins revision when supplied without parsing labels", () => {
      const resolution = resolveBuildGraphLens({
        documentId: "doc-1",
        documentCampaignId: "longmont-c1",
        requestedCampaignId: null,
        requestedRevisionId: "  rev:abc  ",
      });

      expect(resolution.status).toBe("ready");
      if (resolution.status === "ready") {
        expect(resolution.revision).toEqual({ kind: "pinned", revisionId: "rev:abc" });
      }
    });
  });

  describe("campaign-scoped documents", () => {
    it("resolves ready when no campaign is requested", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "doc-1",
          documentCampaignId: "longmont-c2",
          requestedCampaignId: null,
          requestedRevisionId: null,
        }),
      ).toEqual({
        status: "ready",
        documentId: "doc-1",
        documentCampaignId: "longmont-c2",
        campaignId: "longmont-c2",
        worldId: "eldyrwild",
        availableCampaignIds: ["longmont-c2"],
        revision: { kind: "head" },
      });
    });

    it("resolves ready when an explicit matching campaign is requested", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "doc-1",
          documentCampaignId: "longmont-c1",
          requestedCampaignId: "longmont-c1",
          requestedRevisionId: null,
        }),
      ).toMatchObject({
        status: "ready",
        campaignId: "longmont-c1",
        worldId: "eldyrwild",
        availableCampaignIds: ["longmont-c1"],
      });
    });

    it("rejects contradictory campaign requests without rewriting scope", () => {
      const resolution = resolveBuildGraphLens({
        documentId: "doc-1",
        documentCampaignId: "longmont-c1",
        requestedCampaignId: "longmont-c2",
        requestedRevisionId: null,
      });

      expect(resolution).toEqual({
        status: "invalid",
        reason: "Campaign-scoped document (longmont-c1) does not admit campaign lens longmont-c2.",
      });
    });
  });

  describe("world-scoped documents", () => {
    it("requires explicit campaign selection for eldyrwild without auto-selecting c1 or c2", () => {
      const resolution = resolveBuildGraphLens({
        documentId: "doc-world",
        documentCampaignId: "eldyrwild",
        requestedCampaignId: null,
        requestedRevisionId: null,
      });

      expect(resolution).toEqual({
        status: "selection_required",
        documentId: "doc-world",
        documentCampaignId: "eldyrwild",
        worldId: "eldyrwild",
        availableCampaignIds: ["longmont-c1", "longmont-c2"],
        revision: { kind: "head" },
        reason: "World-scoped document (eldyrwild) requires an explicit campaign selection.",
      });
    });

    it("resolves ready when a mapped campaign is selected", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "doc-world",
          documentCampaignId: "eldyrwild",
          requestedCampaignId: "longmont-c2",
          requestedRevisionId: null,
        }),
      ).toMatchObject({
        status: "ready",
        campaignId: "longmont-c2",
        worldId: "eldyrwild",
        availableCampaignIds: ["longmont-c1", "longmont-c2"],
      });
    });

    it("rejects campaigns belonging to another world", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "doc-world",
          documentCampaignId: "eldyrwild",
          requestedCampaignId: "unknown-campaign",
          requestedRevisionId: null,
        }),
      ).toEqual({
        status: "invalid",
        reason: "Campaign unknown-campaign is not mapped to world eldyrwild.",
      });
    });
  });

  describe("invalid inputs", () => {
    it("rejects blank document id or scope", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "  ",
          documentCampaignId: "longmont-c1",
          requestedCampaignId: null,
          requestedRevisionId: null,
        }),
      ).toEqual({
        status: "invalid",
        reason: "Build graph lens requires a document id and campaign/world scope.",
      });

      expect(
        resolveBuildGraphLens({
          documentId: "doc-1",
          documentCampaignId: "",
          requestedCampaignId: null,
          requestedRevisionId: null,
        }),
      ).toEqual({
        status: "invalid",
        reason: "Build graph lens requires a document id and campaign/world scope.",
      });
    });

    it("rejects unknown document scope", () => {
      expect(
        resolveBuildGraphLens({
          documentId: "doc-1",
          documentCampaignId: "unknown-scope",
          requestedCampaignId: null,
          requestedRevisionId: null,
        }),
      ).toEqual({
        status: "invalid",
        reason: "Unknown Build document scope: unknown-scope.",
      });
    });
  });
});
