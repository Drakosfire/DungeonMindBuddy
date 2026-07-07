import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import {
  buildMergeCandidateFromNodes,
  findProjectionMergeCandidates,
  normalizeMergeLabel,
} from "./graphObjectMergeCandidates";

function node(
  overrides: Partial<GraphProjectionNodeView> & Pick<GraphProjectionNodeView, "node_id" | "label">,
): GraphProjectionNodeView {
  return {
    kind: "entity",
    role: "candidate",
    aliases: [],
    source_domains: ["live_projection"],
    evidence_badges: [],
    adjacency: [],
    ...overrides,
  };
}

describe("normalizeMergeLabel", () => {
  it("normalizes punctuation and case", () => {
    expect(normalizeMergeLabel("North Gate")).toBe("north gate");
    expect(normalizeMergeLabel("  the north gate! ")).toBe("the north gate");
  });
});

describe("buildMergeCandidateFromNodes", () => {
  it("returns high-confidence candidate for exact normalized label match", () => {
    const left = node({ node_id: "gate-a", label: "North Gate" });
    const right = node({ node_id: "gate-b", label: "the north gate" });
    const candidate = buildMergeCandidateFromNodes(left, right);
    expect(candidate).not.toBeNull();
    expect(candidate?.confidence).toBe("high");
    expect(candidate?.matchedFeatures.some((feature) => feature.includes("label"))).toBe(true);
  });

  it("rejects same node id", () => {
    const only = node({ node_id: "same", label: "Bonogo" });
    expect(buildMergeCandidateFromNodes(only, only)).toBeNull();
  });
});

describe("findProjectionMergeCandidates", () => {
  it("finds duplicate pairs in projection node views", () => {
    const candidates = findProjectionMergeCandidates({
      a: node({ node_id: "tripod-a", label: "Tripod Null-Calf", kind: "threat" }),
      b: node({ node_id: "tripod-b", label: "Tripod Null Calf", kind: "threat" }),
      c: node({ node_id: "unrelated", label: "Bonogo", kind: "pc" }),
    });
    expect(candidates).toHaveLength(1);
    expect(candidates[0]?.survivorObjectRef.label).toMatch(/Tripod/i);
  });

  it("does not propose merges for distinct player characters with only shared kind", () => {
    const candidates = findProjectionMergeCandidates({
      alden: node({
        node_id: "alden",
        label: "Alden",
        kind: "pc",
        role: "pc",
        source_domains: ["party_pc"],
      }),
      bera: node({
        node_id: "bera",
        label: "Bera",
        kind: "pc",
        role: "pc",
        source_domains: ["party_pc"],
      }),
    });
    expect(candidates).toHaveLength(0);
  });

  it("does not propose merges from shared adjacency alone", () => {
    const sharedAdjacency = [
      {
        edge_id: "edge-1",
        node_id: "longmont",
        label: "Longmont",
        kind: "location",
        predicate: "related_to",
        direction: "out",
        anchored_to_focus_session: false,
        source_domains: ["recap"],
      },
    ];
    const candidates = findProjectionMergeCandidates({
      a: node({
        node_id: "a",
        label: "North Gate",
        kind: "location",
        adjacency: sharedAdjacency,
      }),
      b: node({
        node_id: "b",
        label: "South Gate",
        kind: "location",
        adjacency: sharedAdjacency,
      }),
    });
    expect(candidates).toHaveLength(0);
  });

  it("still finds alias-backed party duplicates", () => {
    const candidates = findProjectionMergeCandidates({
      a: node({ node_id: "a", label: "Questionable Company", kind: "party" }),
      b: node({
        node_id: "b",
        label: "the group",
        kind: "party",
        aliases: ["Questionable Company"],
      }),
    });
    expect(candidates).toHaveLength(1);
    expect(candidates[0]?.matchedFeatures.some((feature) => feature.includes("alias"))).toBe(
      true,
    );
  });

  it("uses current_recap_projection for recap source domains in object refs", () => {
    const candidate = buildMergeCandidateFromNodes(
      node({ node_id: "edge-a", label: "Edge", source_domains: ["recap"] }),
      node({ node_id: "edge-b", label: "the Edge", source_domains: ["recap"] }),
    );
    expect(candidate?.survivorObjectRef.graphScope).toBe("current_recap_projection");
    expect(candidate?.mergedObjectRef.graphScope).toBe("current_recap_projection");
  });
});
