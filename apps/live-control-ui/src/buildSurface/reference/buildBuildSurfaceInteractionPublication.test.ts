import { describe, expect, it, vi } from "vitest";

import { GRAPH_REFERENCE_RESOLUTION_BINDING_ID } from "../../graphReference/projectionBindings";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { validateSurfaceInteractionPublication } from "../../surfaceInteraction/publication";
import {
  BUILD_FIND_EXISTING_TOOL_ID,
  BUILD_REFERENCE_CONTEXT_BINDING_ID,
  BUILD_REFERENCE_SEARCH_PROJECTION_ID,
} from "./buildReferenceIds";
import {
  buildBuildSurfaceInteractionPublication,
  type BuildReferenceContextBinding,
} from "./buildBuildSurfaceInteractionPublication";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

const sampleContext: BuildReferenceContextBinding = {
  schema: "dmb_build_reference_context_v1",
  documentId: DOC_ID,
  documentCampaignId: "longmont-c1",
  lens: {
    status: "ready",
    documentId: DOC_ID,
    documentCampaignId: "longmont-c1",
    campaignId: "longmont-c1",
    worldId: "eldyrwild",
    availableCampaignIds: ["longmont-c1"],
    revision: { kind: "head" },
  },
  items: [],
  projectionState: "ready",
  projectionError: null,
  requestedRevisionId: null,
  loadedRevisionId: "rev-head",
  loadedIsHead: true,
  selectCampaign: () => undefined,
  viewExact: () => undefined,
};

describe("buildBuildSurfaceInteractionPublication", () => {
  it("returns empty inventory when documentId is null", () => {
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: null,
      acceptedDocument: null,
      referenceContext: null,
    });

    expect(publication.tools).toEqual([]);
    expect(publication.editCommands).toEqual([]);
    expect(publication.projections).toEqual([]);
    expect(publication.projectionBindings).toEqual([]);
    expect(publication.canvas).toBeNull();
    expect(publication.identity.surfaceId).toBe("build");
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("returns empty inventory when accepted document is missing", () => {
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: DOC_ID,
      acceptedDocument: null,
      referenceContext: sampleContext,
    });

    expect(publication.tools).toEqual([]);
    expect(publication.projections).toEqual([]);
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("fails closed when accepted document id mismatches route documentId", () => {
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: DOC_ID,
      acceptedDocument: { documentId: "other-doc", campaignId: "longmont-c1" },
      referenceContext: sampleContext,
    });

    expect(publication.tools).toEqual([]);
    expect(publication.canvas).toBeNull();
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("fails closed when reference context is missing for an accepted document", () => {
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: DOC_ID,
      acceptedDocument: { documentId: DOC_ID, campaignId: "longmont-c1" },
      referenceContext: null,
    });

    expect(publication.tools).toEqual([]);
    expect(publication.projections).toEqual([]);
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("publishes Find existing tool and projections for accepted document", () => {
    const save = vi.fn();
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: DOC_ID,
      acceptedDocument: { documentId: DOC_ID, campaignId: "longmont-c1" },
      referenceContext: sampleContext,
      documentSave: { saveDisabled: false, save },
    });

    expect(publication.editCommands).toHaveLength(1);
    expect(publication.editCommands[0]).toMatchObject({
      id: "document.save",
      label: "Save",
      availability: { status: "enabled" },
      target: { kind: "document", id: DOC_ID },
    });
    expect(typeof publication.editCommands[0]?.invoke).toBe("function");
    publication.editCommands[0]?.invoke();
    expect(save).toHaveBeenCalledTimes(1);
    expect(publication.canvas).toEqual({
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: DOC_ID },
    });
    expect(publication.tools).toHaveLength(1);
    expect(publication.tools[0]).toMatchObject({
      id: BUILD_FIND_EXISTING_TOOL_ID,
      label: "Find existing object",
      eyebrow: "World Graph",
      placement: {
        groupId: "build-world-reference",
        groupLabel: "World references",
        groupOrder: 10,
        itemOrder: 0,
      },
      availability: { status: "enabled" },
      activation: {
        kind: "projection",
        projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
      },
    });
    expect(publication.projections).toEqual([
      {
        id: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
        kind: "tool",
        preferredSize: "wide",
        bindingIds: [BUILD_REFERENCE_CONTEXT_BINDING_ID],
      },
      {
        id: GRAPH_REFERENCE_PROJECTION_ID,
        kind: "content",
        preferredSize: "wide",
        bindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
      },
    ]);
    expect(publication.projectionBindings.map((entry) => entry.id)).toEqual([
      BUILD_REFERENCE_CONTEXT_BINDING_ID,
      GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
    ]);
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("disables Find existing for invalid lenses with the resolver reason", () => {
    const invalidContext: BuildReferenceContextBinding = {
      ...sampleContext,
      lens: {
        status: "invalid",
        reason: "Campaign-scoped document (longmont-c1) does not admit campaign lens longmont-c2.",
      },
      projectionState: "error",
      projectionError:
        "Campaign-scoped document (longmont-c1) does not admit campaign lens longmont-c2.",
      loadedRevisionId: null,
      loadedIsHead: false,
    };
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: DOC_ID,
      acceptedDocument: { documentId: DOC_ID, campaignId: "longmont-c1" },
      referenceContext: invalidContext,
    });

    expect(publication.tools[0]?.availability).toEqual({
      status: "disabled",
      disabledReason:
        "Campaign-scoped document (longmont-c1) does not admit campaign lens longmont-c2.",
    });
    expect(validateSurfaceInteractionPublication(publication).valid).toBe(true);
  });

  it("keeps Find existing enabled for selection_required lenses", () => {
    const selectionContext: BuildReferenceContextBinding = {
      ...sampleContext,
      documentCampaignId: "eldyrwild",
      lens: {
        status: "selection_required",
        documentId: DOC_ID,
        documentCampaignId: "eldyrwild",
        worldId: "eldyrwild",
        availableCampaignIds: ["longmont-c1", "longmont-c2"],
        revision: { kind: "head" },
        reason: "World-scoped document requires an explicit campaign selection.",
      },
      projectionState: "unavailable",
      projectionError: "World-scoped document requires an explicit campaign selection.",
      loadedRevisionId: null,
      loadedIsHead: false,
    };
    const publication = buildBuildSurfaceInteractionPublication({
      documentId: DOC_ID,
      acceptedDocument: { documentId: DOC_ID, campaignId: "eldyrwild" },
      referenceContext: selectionContext,
    });

    expect(publication.tools[0]?.availability).toEqual({ status: "enabled" });
  });
});
