import { describe, expect, it } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringProposal,
  buildProposalAliases,
  createDefaultGraphObjectAuthoringFormState,
  dedupeAliasesCaseInsensitive,
  parseAliasesText,
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
});
