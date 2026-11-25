import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { StatblockRenderer } from "./StatblockRenderer";
import type { WwnSheetProjectionInput } from "./WwnSheetProjection";
import alternate from "./wwn-alternate.fixture.json";
import known from "./wwn-known.fixture.json";

afterEach(cleanup);

it.each([
  { fixture: known, name: "Iria Vale", armor: 13, hp: 9, weapon: "Shock 2/AC 13; T", nameField: "Name", initiative: "Unconfirmed template default" },
  { fixture: alternate, name: "Mera Sable", armor: 15, hp: 13, weapon: "2/AC 13", nameField: "Character", initiative: "Unknown" },
])("projects reviewed sheet fields and verified locations for $name", ({ fixture, name, armor, hp, weapon, nameField, initiative }) => {
  const { sheet, config } = fixture as WwnSheetProjectionInput;
  const overrides = { "combat.hp_max": { value: 17, reason: "Campaign adjustment" } };
  const { rerender } = render(<StatblockRenderer sheetProjection={{ sheet, config, overrides }} />);
  const view = within(screen.getByRole("article", { name: `WWN statblock for ${name}` }));
  const armorSource = sheet.fields["combat.ac"];
  const hpSource = sheet.fields["combat.hp_max"];
  if (armorSource?.state !== "confirmed" || hpSource?.state !== "confirmed") {
    throw new Error("The fixture must have reviewed AC and HP values");
  }
  const location = armorSource.evidence.occurrences?.[0] ?? armorSource.evidence;
  expect(view.getByText(String(armor))).toBeTruthy();
  expect(view.getByText("0")).toBeTruthy();
  expect(view.getByText("Blank on sheet")).toBeTruthy();
  expect(view.getByText(initiative)).toBeTruthy();
  expect(view.getByText(weapon)).toBeTruthy();
  expect(view.getByText("17")).toBeTruthy();
  expect(view.getByText("Override: Campaign adjustment")).toBeTruthy();
  expect(view.getByText(nameField)).toBeTruthy();
  expect(view.getAllByText(`PDF page ${location.page}, bounds ${location.bbox_pdf_points?.join(", ")}`).length).toBeGreaterThan(0);

  const corrected = {
    ...sheet,
    source_sha256: "corrected-revision",
    fields: {
      ...sheet.fields,
      "combat.ac": { ...armorSource, value: 16 },
      "combat.hp_max": { ...hpSource, value: hp + 1 },
    },
  };
  rerender(<StatblockRenderer sheetProjection={{ sheet: corrected, config, overrides }} />);
  expect(view.getByText("16")).toBeTruthy();
  expect(view.getByText("17")).toBeTruthy();
  expect(view.getByText(weapon)).toBeTruthy();
  expect(view.getByText("corrected-revision")).toBeTruthy();
});
