import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringLinkExistingProposal,
  buildGraphObjectAuthoringProposal,
  buildGraphObjectAuthoringRelationshipProposal,
  buildObjectRefFromInspectedNode,
  createDefaultGraphObjectAuthoringFormState,
  createDefaultGraphObjectAuthoringLinkExistingFormState,
  createDefaultGraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import { derivePublishedRecapWorkingProjection } from "./publishedRecapWorkingProjection";

const node = (nodeId: string, label: string, summary = "Useful object prose."): GraphProjectionNodeView => ({
  node_id: nodeId,
  label,
  kind: "location",
  role: "location",
  aliases: [label],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  suggested_expansions: [],
  anchored_to_focus_session: true,
  summary,
});

const selection: GraphAuthoringSelection = {
  campaignId: "longmont-c2",
  sessionId: "session-27",
  selectionKind: "text_span",
  selectedText: "Mirathorn",
  normalizedSelectedText: "Mirathorn",
  paragraphOrdinal: 1,
  surroundingTextBefore: "near",
  surroundingTextAfter: "before dawn",
  graphId: "graph-c2s27",
  laneRole: "live",
};

describe("derivePublishedRecapWorkingProjection", () => {
  it("turns a staged existing-node link into an exact-node pill and reverses it when removed", () => {
    const linkForm = {
      ...createDefaultGraphObjectAuthoringLinkExistingFormState(),
      existingObjectRef: buildObjectRefFromInspectedNode({
        node_id: "loc_mirathorn",
        label: "Mirathorn",
        kind: "location",
      }),
      operation: "reference" as const,
    };
    const proposal = buildGraphObjectAuthoringLinkExistingProposal(selection, linkForm, "link-1");
    expect(proposal).toBeTruthy();

    const input = {
      markdown: "The party reached Mirathorn before dawn.",
      nodeViews: { loc_mirathorn: node("loc_mirathorn", "Mirathorn") },
      sessionId: "session-27",
    };
    const working = derivePublishedRecapWorkingProjection({
      ...input,
      proposals: [proposal!],
    });

    expect(working.markdown).toContain("[Mirathorn](dmb-node:loc_mirathorn)");
    expect(working.nodeDeltaPresentations.loc_mirathorn).toBeUndefined();

    const reverted = derivePublishedRecapWorkingProjection({ ...input, proposals: [] });
    expect(reverted.markdown).toBe(input.markdown);
    expect(reverted.nodeDeltaPresentations).toEqual({});
  });

  it("renders a highlighted new object as a local, explicitly uncommitted reference", () => {
    const form = {
      ...createDefaultGraphObjectAuthoringFormState(selection),
      label: "The Ashen Door",
      kind: "object",
      summary: "A sealed door in the old tower.",
    };
    const proposal = buildGraphObjectAuthoringProposal(selection, form, "object-1");
    const working = derivePublishedRecapWorkingProjection({
      markdown: "The party reached Mirathorn before dawn.",
      nodeViews: {},
      proposals: [proposal],
      sessionId: "session-27",
    });

    expect(working.markdown).toContain("[Mirathorn](dmb-node:local-authoring:object-1)");
    expect(working.nodeViews["local-authoring:object-1"]).toMatchObject({
      label: "The Ashen Door",
      authored: true,
      source: "local_authoring",
      summary: "A sealed door in the old tower.",
    });
    expect(working.nodeDeltaPresentations["local-authoring:object-1"]).toMatchObject({
      label: "Local · uncommitted",
    });
  });

  it("adds a staged relationship to both working objects without changing recap prose", () => {
    const relationshipForm = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: buildObjectRefFromInspectedNode({
        node_id: "pc_caelynn",
        label: "Caelynn",
        kind: "pc",
      }),
      targetObjectRef: buildObjectRefFromInspectedNode({
        node_id: "loc_mirathorn",
        label: "Mirathorn",
        kind: "location",
      }),
      relationshipType: "located_in",
      summary: "Local adjudication for this recap.",
    };
    const proposal = buildGraphObjectAuthoringRelationshipProposal(
      relationshipForm,
      null,
      "relationship-1",
    );
    expect(proposal).toBeTruthy();

    const working = derivePublishedRecapWorkingProjection({
      markdown: "The party reached Mirathorn before dawn.",
      nodeViews: {
        pc_caelynn: node("pc_caelynn", "Caelynn", "A party member."),
        loc_mirathorn: node("loc_mirathorn", "Mirathorn"),
      },
      proposals: [proposal!],
      sessionId: "session-27",
    });

    expect(working.markdown).toBe("The party reached Mirathorn before dawn.");
    expect(working.nodeViews.pc_caelynn.adjacency).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          node_id: "loc_mirathorn",
          predicate: "located_in",
          direction: "outgoing",
          source_domains: ["local_authoring"],
        }),
      ]),
    );
    expect(working.nodeViews.loc_mirathorn.adjacency).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          node_id: "pc_caelynn",
          direction: "incoming",
        }),
      ]),
    );
  });

  it("does not apply an ambiguous source occurrence", () => {
    const form = createDefaultGraphObjectAuthoringFormState(selection);
    const proposal = buildGraphObjectAuthoringProposal(selection, form, "ambiguous-1");
    const working = derivePublishedRecapWorkingProjection({
      markdown: "Mirathorn watched the road while the party returned to Mirathorn.",
      nodeViews: { loc_mirathorn: node("loc_mirathorn", "Mirathorn") },
      proposals: [proposal],
      sessionId: "session-27",
    });

    expect(working.markdown).not.toContain("dmb-node:");
    expect(working.diagnostics[0]).toMatch(/Could not safely replay/);
  });
});
