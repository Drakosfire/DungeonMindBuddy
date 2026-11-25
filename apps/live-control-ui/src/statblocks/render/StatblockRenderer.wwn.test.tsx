import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { StatblockRenderer } from "./StatblockRenderer";
import type { WwnSheetProjectionInput } from "./WwnSheetProjection";

afterEach(cleanup);

const config = {
  sections: [
    {
      title: "Combat",
      fields: [
        { key: "combat.ac", label: "Armor Class" },
        { key: "combat.hp_max", label: "Maximum HP" },
        { key: "combat.effort_current", label: "Effort" },
        { key: "combat.initiative", label: "Initiative" },
        { key: "attributes.str_mod", label: "Strength modifier" },
      ],
    },
    {
      title: "Weapon",
      fields: [{ key: "weapon.special", label: "Special and Shock" }],
    },
  ],
};

function confirmed(value: string | number, label: string, form: boolean) {
  const location = { page: 1, bbox_pdf_points: [1, 2, 3, 4] };
  const evidence = form
    ? { label, method: "acroform", occurrences: [location] }
    : { label, method: "native_pdf_text", ...location };
  return { state: "confirmed" as const, value, evidence };
}

it.each([
  { form: true, name: "Iria Vale", armor: 13, hp: 9, weapon: "Shock 2/AC 13; T" },
  { form: false, name: "Mera Sable", armor: 15, hp: 13, weapon: "2/AC 13" },
])("projects reviewed sheet fields and verified locations for $name", ({ form, name, armor, hp, weapon }) => {
  const sheet: WwnSheetProjectionInput["sheet"] = {
    ruleset: "wwn",
    source_sha256: "source-revision",
    fields: {
      "identity.name": confirmed(name, form ? "Name" : "Character", form),
      "combat.ac": confirmed(armor, form ? "AC" : "Armor Class", form),
      "combat.hp_max": confirmed(hp, "Maximum HP", form),
      "combat.effort_current": { state: "blank", value: null, evidence: null },
      "attributes.str_mod": confirmed(0, "Strength modifier", form),
      "weapon.special": confirmed(weapon, "Weapon Shock", form),
    },
  };
  const overrides = { "combat.hp_max": { value: 17, reason: "Campaign adjustment" } };
  const { rerender } = render(<StatblockRenderer sheetProjection={{ sheet, config, overrides }} />);
  const card = screen.getByRole("article", { name: `WWN statblock for ${name}` });
  const view = within(card);
  expect(view.getByText(String(armor))).toBeTruthy();
  expect(view.getByText("0")).toBeTruthy();
  expect(view.getByText("Blank on sheet")).toBeTruthy();
  expect(view.getByText("Unknown")).toBeTruthy();
  expect(view.getByText(weapon)).toBeTruthy();
  expect(view.getByText("17")).toBeTruthy();
  expect(view.getByText("Override: Campaign adjustment")).toBeTruthy();
  expect(view.getAllByText("PDF page 1, bounds 1, 2, 3, 4")).toHaveLength(4);

  const corrected = {
    ...sheet,
    source_sha256: "corrected-revision",
    fields: {
      ...sheet.fields,
      "combat.ac": confirmed(16, form ? "AC" : "Armor Class", form),
      "combat.hp_max": confirmed(hp + 1, "Maximum HP", form),
    },
  };
  rerender(<StatblockRenderer sheetProjection={{ sheet: corrected, config, overrides }} />);
  expect(view.getByText("16")).toBeTruthy();
  expect(view.getByText("17")).toBeTruthy();
  expect(view.getByText(weapon)).toBeTruthy();
  expect(view.getByText("corrected-revision")).toBeTruthy();
});
