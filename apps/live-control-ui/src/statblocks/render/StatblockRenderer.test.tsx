import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { GeneratedStatblockCandidateV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import { StatblockRenderer } from "./StatblockRenderer";
import { abilityModifier, buildStatblockViewModel, formatModifier } from "./statblockViewModel";

const candidate = fixture as GeneratedStatblockCandidateV1;

describe("statblockViewModel", () => {
  it("derives ability modifiers deterministically", () => {
    expect(abilityModifier(18)).toBe(4);
    expect(abilityModifier(8)).toBe(-1);
    expect(formatModifier(4)).toBe("+4");
  });

  it("maps structured definition fields without using Markdown", () => {
    const view = buildStatblockViewModel(candidate);
    expect(view.name).toBe("Ironhide Brute");
    expect(view.candidateId).toBe("cand_fixture1");
    expect(view.armorClassSummary).toContain("15");
    expect(view.hitPointsSummary).toContain("68");
    expect(view.speedSummary).toContain("walk");
    expect(view.ruleElements[0]?.key).toBe("greatclub");
    expect(view.ruleElements[0]?.rulesText).toContain("Melee Weapon Attack");
    expect(view.validation?.digest).toMatch(/^sha256:/);
  });
});

describe("StatblockRenderer", () => {
  it("renders typed candidate mechanics and receipts", () => {
    render(<StatblockRenderer candidate={candidate} />);
    expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    expect(screen.getByText(/Candidate/)).toBeTruthy();
    expect(screen.getByText(/cand_fixture1/)).toBeTruthy();
    expect(screen.getByText("Greatclub")).toBeTruthy();
    expect(screen.getByText(/Melee Weapon Attack/)).toBeTruthy();
    expect(screen.getByText(/Validation/)).toBeTruthy();
  });

  it("labels human-adjudicated elements", () => {
    const humanCandidate: GeneratedStatblockCandidateV1 = {
      ...candidate,
      definition: {
        ...candidate.definition,
        rule_elements: [
          {
            ...candidate.definition.rule_elements[0],
            key: "lair_pressure",
            name: "Lair Pressure",
            section: "trait",
            rules_text: "The GM decides when the pressure escalates.",
            automation_support: "manual",
            mechanic: {
              kind: "human_adjudicated",
              adjudication_tags: ["table_judgment"],
            },
          },
        ],
      },
    };
    render(<StatblockRenderer candidate={humanCandidate} />);
    expect(screen.getByText("Human adjudicated")).toBeTruthy();
  });
});
