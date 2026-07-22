import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { StatblockRenderer } from "./StatblockRenderer";

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = resolve(
  here,
  "../../../../../tests/fixtures/statblocks/v1/candidate-response.json",
);
const candidateFixture = JSON.parse(readFileSync(fixturePath, "utf8")) as Record<string, unknown>;

describe("StatblockRenderer", () => {
  it("renders structured identity, defenses, abilities, and rule elements", () => {
    render(<StatblockRenderer candidate={candidateFixture} />);

    expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeInTheDocument();
    expect(screen.getByText(/Large, giant, unaligned/i)).toBeInTheDocument();
    expect(screen.getByText("15 (natural armor)")).toBeInTheDocument();
    expect(screen.getByText(/68 \(8d10 \+ 24\)/)).toBeInTheDocument();
    expect(screen.getByText(/walk 30 feet/i)).toBeInTheDocument();
    expect(screen.getByText("Greatclub")).toBeInTheDocument();
    expect(screen.getByText(/Melee Weapon Attack/i)).toBeInTheDocument();
    expect(screen.getByText("No validation issues.")).toBeInTheDocument();
  });

  it("distinguishes validation errors from warnings and shows human-adjudicated labels", () => {
    const candidate = {
      ...candidateFixture,
      definition: {
        ...(candidateFixture.definition as Record<string, unknown>),
        rule_elements: [
          {
            key: "weird_aura",
            name: "Weird Aura",
            section: "trait",
            rules_text: "Requires table adjudication.",
            automation_support: "human_adjudicated",
          },
        ],
      },
      validation_receipt: {
        issues: [
          {
            code: "BAD_FIELD",
            message: "Broken field",
            severity: "error",
            field_path: "rule_elements[0]",
          },
          {
            code: "SOFT_WARN",
            message: "Review numbers",
            severity: "warning",
            field_path: "challenge.rating",
          },
        ],
      },
    };

    render(<StatblockRenderer candidate={candidate} />);

    expect(screen.getByText("human-adjudicated")).toBeInTheDocument();
    expect(screen.getByLabelText("Validation errors")).toHaveTextContent("BAD_FIELD");
    expect(screen.getByLabelText("Validation warnings")).toHaveTextContent("SOFT_WARN");
  });

  it("fails closed when definition is missing", () => {
    render(<StatblockRenderer candidate={{ candidate_id: "cand_x" }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("missing a structured definition");
  });
});
