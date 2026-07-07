import { describe, expect, it } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringLinkExistingProposal,
  buildGraphObjectAuthoringProposal,
  buildGraphObjectAuthoringRelationshipProposal,
  buildManualObjectRef,
  buildObjectRefFromInspectedNode,
  buildObjectRefFromObjectProposal,
  buildProposalAliases,
  canStageRelationshipForm,
  createDefaultGraphObjectAuthoringFormState,
  createDefaultGraphObjectAuthoringLinkExistingFormState,
  createDefaultGraphObjectAuthoringRelationshipFormState,
  dedupeAliasesCaseInsensitive,
  formatAuthoringRelationshipStatement,
  friendlyVisibilityLabel,
  GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS,
  isIdentityLikeRelationshipPredicate,
  areSameObjectRef,
  isValidObjectRef,
  parseAliasesText,
  relationshipPreviewCopy,
} from "./graphObjectAuthoringDraft";

const baseSelection: GraphAuthoringSelection = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  selectionKind: "text_span",
  selectedText: "gang",
  normalizedSelectedText: "gang",
  graphId: "graph-c1s2",
  laneRole: "live",
};

describe("createDefaultGraphObjectAuthoringFormState", () => {
  it("seeds the label from the selection's selected text", () => {
    const formState = createDefaultGraphObjectAuthoringFormState(baseSelection);
    expect(formState.label).toBe("gang");
    expect(formState.visibility).toBe("gm_private");
    expect(formState.kind).toBe("unknown");
  });

  it("defaults to an empty label when no selection is provided", () => {
    const formState = createDefaultGraphObjectAuthoringFormState(null);
    expect(formState.label).toBe("");
  });
});

describe("parseAliasesText", () => {
  it("splits on commas and newlines and trims whitespace", () => {
    expect(parseAliasesText("Alden,  the Warden\nGate Keeper")).toEqual([
      "Alden",
      "the Warden",
      "Gate Keeper",
    ]);
  });

  it("drops empty entries", () => {
    expect(parseAliasesText("Alden,, ,\n")).toEqual(["Alden"]);
  });
});

describe("dedupeAliasesCaseInsensitive", () => {
  it("keeps the first casing and drops case-insensitive duplicates", () => {
    expect(dedupeAliasesCaseInsensitive(["Alden", "alden", "ALDEN", "Grish"])).toEqual([
      "Alden",
      "Grish",
    ]);
  });
});

describe("buildProposalAliases", () => {
  it("includes the selected text as an alias when the label diverges", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringFormState(baseSelection),
      label: "Questionable Company",
      aliasesText: "",
    };
    expect(buildProposalAliases(formState, baseSelection)).toEqual(["gang"]);
  });

  it("does not duplicate the selected text when the label matches it", () => {
    const formState = createDefaultGraphObjectAuthoringFormState(baseSelection);
    expect(buildProposalAliases(formState, baseSelection)).toEqual([]);
  });

  it("does not add a duplicate alias when the selected text is already listed", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringFormState(baseSelection),
      label: "Questionable Company",
      aliasesText: "gang, the crew",
    };
    expect(buildProposalAliases(formState, baseSelection)).toEqual([
      "gang",
      "the crew",
    ]);
  });
});

describe("buildGraphObjectAuthoringProposal", () => {
  it("builds a staged-local proposal carrying the selection and form fields", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringFormState(baseSelection),
      label: "Questionable Company",
      kind: "party",
      aliasesText: "the crew",
      summary: "The party's adventuring name.",
      visibility: "table_known" as const,
    };
    const proposal = buildGraphObjectAuthoringProposal(baseSelection, formState, "local-object-1");

    expect(proposal).toMatchObject({
      localProposalId: "local-object-1",
      proposalKind: "object",
      status: "staged_local",
      objectRef: {
        label: "Questionable Company",
        kind: "party",
        summary: "The party's adventuring name.",
      },
      visibility: {
        visibility: "table_known",
        revealState: "unrevealed",
      },
      provenancePreview: {
        origin: "human_authored",
        authoringSurface: "memory_ingest_graph_authoring",
        sourceGraphId: "graph-c1s2",
      },
    });
    expect(proposal.objectRef.aliases).toEqual(["the crew", "gang"]);
    expect(proposal.selection).toBe(baseSelection);
  });

  it("defaults visibility to GM private and includes the note for character-specific visibility", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringFormState(baseSelection),
      visibility: "character_specific" as const,
    };
    const proposal = buildGraphObjectAuthoringProposal(baseSelection, formState, "local-object-2");
    expect(proposal.visibility.visibilityNote).toMatch(/specific characters/i);
  });

  it("preserves player_visible in the staged object payload", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringFormState(baseSelection),
      visibility: "player_visible" as const,
    };
    const proposal = buildGraphObjectAuthoringProposal(baseSelection, formState, "local-object-player");
    expect(proposal.visibility.visibility).toBe("player_visible");
  });
});

describe("buildObjectRefFromObjectProposal / buildObjectRefFromInspectedNode / buildManualObjectRef", () => {
  const objectProposal = buildGraphObjectAuthoringProposal(
    baseSelection,
    { ...createDefaultGraphObjectAuthoringFormState(baseSelection), label: "Questionable Company", kind: "party" },
    "local-object-3",
  );

  it("builds a local_proposal ref from a staged object proposal", () => {
    expect(buildObjectRefFromObjectProposal(objectProposal)).toEqual({
      refKind: "local_proposal",
      localProposalId: "local-object-3",
      label: "Questionable Company",
      kind: "party",
      role: null,
    });
  });

  it("builds an existing_graph_node ref from an inspected node", () => {
    expect(
      buildObjectRefFromInspectedNode({
        node_id: "alden",
        label: "Alden",
        kind: "npc",
        role: "gate warden",
      }),
    ).toEqual({
      refKind: "existing_graph_node",
      nodeId: "alden",
      label: "Alden",
      kind: "npc",
      role: "gate warden",
      graphScope: null,
      sourceLabel: null,
      sourceGraphId: null,
      sourcePath: null,
      visibility: null,
    });
  });

  it("builds a manual_ref from a typed label", () => {
    expect(buildManualObjectRef("  Bonogo  ")).toEqual({
      refKind: "manual_ref",
      label: "Bonogo",
    });
  });
});

describe("isValidObjectRef", () => {
  it("rejects null and undefined refs", () => {
    expect(isValidObjectRef(null)).toBe(false);
    expect(isValidObjectRef(undefined)).toBe(false);
  });

  it("rejects a manual ref with a blank or whitespace-only label", () => {
    expect(isValidObjectRef(buildManualObjectRef(""))).toBe(false);
    expect(isValidObjectRef(buildManualObjectRef("   "))).toBe(false);
  });

  it("accepts a manual ref with a non-blank label", () => {
    expect(isValidObjectRef(buildManualObjectRef("Questionable Company"))).toBe(true);
  });

  it("accepts refs from staged proposals and inspected nodes", () => {
    expect(
      isValidObjectRef(buildObjectRefFromInspectedNode({ node_id: "alden", label: "Alden" })),
    ).toBe(true);
  });
});

describe("buildGraphObjectAuthoringLinkExistingProposal", () => {
  it("returns null when no existing object ref has been chosen", () => {
    const formState = createDefaultGraphObjectAuthoringLinkExistingFormState();
    expect(buildGraphObjectAuthoringLinkExistingProposal(baseSelection, formState)).toBeNull();
  });

  it("returns null when the chosen ref is a manual entry with a blank label", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringLinkExistingFormState(),
      existingObjectRef: buildManualObjectRef("   "),
    };
    expect(buildGraphObjectAuthoringLinkExistingProposal(baseSelection, formState)).toBeNull();
  });

  it("stages a link-existing proposal referencing the chosen object and selected text", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringLinkExistingFormState(),
      existingObjectRef: buildManualObjectRef("Questionable Company"),
      operation: "alias" as const,
    };
    const proposal = buildGraphObjectAuthoringLinkExistingProposal(baseSelection, formState, "local-link-1");

    expect(proposal).toMatchObject({
      localProposalId: "local-link-1",
      proposalKind: "link_existing",
      status: "staged_local",
      selectedText: "gang",
      operation: "alias",
      existingObjectRef: { refKind: "manual_ref", label: "Questionable Company" },
      visibility: { visibility: "gm_private", revealState: "unrevealed" },
    });
    expect(proposal?.selection).toBe(baseSelection);
  });
});

describe("buildGraphObjectAuthoringRelationshipProposal", () => {
  const sourceRef = buildManualObjectRef("Questionable Company");
  const targetRef = buildObjectRefFromInspectedNode({ node_id: "bonogo", label: "Bonogo", kind: "pc" });

  it("returns null when source or target object refs are missing", () => {
    const formState = createDefaultGraphObjectAuthoringRelationshipFormState();
    expect(buildGraphObjectAuthoringRelationshipProposal(formState)).toBeNull();
  });

  it("returns null when the source or target ref is a manual entry with a blank label", () => {
    const blankSourceFormState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: buildManualObjectRef(""),
      targetObjectRef: targetRef,
      relationshipType: "has_member",
    };
    expect(buildGraphObjectAuthoringRelationshipProposal(blankSourceFormState)).toBeNull();

    const blankTargetFormState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: buildManualObjectRef("   "),
      relationshipType: "has_member",
    };
    expect(buildGraphObjectAuthoringRelationshipProposal(blankTargetFormState)).toBeNull();
  });

  it("stages a relationship proposal between source and target object refs", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: targetRef,
      relationshipType: "has_member",
      direction: "directed" as const,
    };
    const proposal = buildGraphObjectAuthoringRelationshipProposal(formState, null, "local-rel-1");

    expect(proposal).toMatchObject({
      localProposalId: "local-rel-1",
      proposalKind: "relationship",
      status: "staged_local",
      relationshipType: "has_member",
      direction: "directed",
      sourceObjectRef: sourceRef,
      targetObjectRef: targetRef,
    });
  });

  it("returns null when source and target are the exact same object ref", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: sourceRef,
      relationshipType: "has_member",
    };
    expect(buildGraphObjectAuthoringRelationshipProposal(formState)).toBeNull();
  });

  it("carries an optional evidence selection through to provenance", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: targetRef,
      relationshipType: "has_member",
    };
    const proposal = buildGraphObjectAuthoringRelationshipProposal(formState, baseSelection, "local-rel-2");

    expect(proposal?.selection).toBe(baseSelection);
    expect(proposal?.provenancePreview.sourceGraphId).toBe("graph-c1s2");
  });
});

describe("GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS", () => {
  it("includes separate table_known and player_visible entries", () => {
    const values = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.map((option) => option.value);
    expect(values).toContain("table_known");
    expect(values).toContain("player_visible");
  });
});

describe("friendlyVisibilityLabel", () => {
  it("maps raw enum values to friendly labels", () => {
    expect(friendlyVisibilityLabel("player_visible")).toBe("Player visible");
    expect(friendlyVisibilityLabel("table_known")).toBe("Table known");
  });
});

describe("relationship guidance helpers", () => {
  const sourceRef = buildManualObjectRef("the group");
  const targetRef = buildObjectRefFromInspectedNode({ node_id: "north-gate", label: "North Gate" });

  it("formats campaign-language relationship statements", () => {
    expect(
      formatAuthoringRelationshipStatement("the group", "North Gate", "threatens"),
    ).toBe("the group threatens North Gate");
  });

  it("builds preview copy when source, target, and type are present", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: targetRef,
      relationshipType: "threatens",
    };
    expect(relationshipPreviewCopy(formState)).toBe("the group threatens North Gate");
  });

  it("detects identity-like custom predicates", () => {
    expect(isIdentityLikeRelationshipPredicate("same_as")).toBe(true);
    expect(isIdentityLikeRelationshipPredicate("alias_of")).toBe(true);
    expect(isIdentityLikeRelationshipPredicate("threatens")).toBe(false);
  });

  it("treats exact same existing node IDs as the same object ref", () => {
    const ref = buildObjectRefFromInspectedNode({ node_id: "bonogo", label: "Bonogo" });
    expect(areSameObjectRef(ref, ref)).toBe(true);
  });

  it("allows same label on different existing node IDs", () => {
    const left = buildObjectRefFromInspectedNode({ node_id: "glowkindle-char", label: "Glowkindle" });
    const right = buildObjectRefFromInspectedNode({ node_id: "glowkindle-faction", label: "Glowkindle" });
    expect(areSameObjectRef(left, right)).toBe(false);
  });

  it("blocks staging when source and target are the exact same ref", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: sourceRef,
      relationshipType: "threatens",
    };
    expect(canStageRelationshipForm(formState)).toBe(false);
  });

  it("allows staging when source and target differ", () => {
    const formState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: sourceRef,
      targetObjectRef: targetRef,
      relationshipType: "threatens",
    };
    expect(canStageRelationshipForm(formState)).toBe(true);
  });
});
