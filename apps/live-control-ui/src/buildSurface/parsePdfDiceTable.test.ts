import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, it } from "vitest";
import { parsePdfDiceTable, type PdfRegionTextRun } from "./parsePdfDiceTable";

const goldPath = resolve(process.cwd(), "../../evals/document_extraction_gold/adventure_pdf_source_gold_v1.json");
const sourceGold = JSON.parse(readFileSync(goldPath, "utf8")) as {
  cases: Array<{
    case_id: string; physical_page: number; block_title: string; columns: string[];
    rows: Array<{ roll: number; name: string; notes: string }>;
  }>;
};
const tableGold = sourceGold.cases.find(candidate => candidate.case_id === "conks-appendix-c-male-villager-names");
if (!tableGold) throw new Error("The source-pinned Conks table gold is missing.");

function run(text: string, left: number, top: number, right = left + 0.1): PdfRegionTextRun {
  return { text, left, right, top, bottom: top + 0.01 };
}

function maleVillagerTable(): PdfRegionTextRun[] {
  return [
    run("Male Villager NamesMale Villager Names", 0.1, 0.1, 0.45),
    run("1d121d12", 0.1, 0.13, 0.15),
    run("NameName", 0.2, 0.13, 0.3),
    run("NotesNotes", 0.7, 0.13, 0.8),
    ...tableGold.rows.flatMap(({roll, name}) => {
      const index = roll - 1;
      const top = 0.16 + index * 0.02;
      return [run(String(roll), 0.1, top, 0.13), run(name, 0.2, top, 0.38)];
    }),
  ];
}

it("reconstructs the source-gold D12 table from selected PDF.js coordinates", () => {
  expect(tableGold.physical_page).toBe(18);
  const candidate = parsePdfDiceTable(maleVillagerTable());

  expect(candidate).toEqual({
    title: tableGold.block_title,
    columns: tableGold.columns,
    rows: tableGold.rows.map(({roll, name, notes}) => [String(roll), name, notes]),
  });
});

it("assigns populated notes only when the run lies in that source column", () => {
  const items = maleVillagerTable();
  items[4] = run("1", 0.1, 0.16, 0.13);
  items[5] = run("Ryan Burke", 0.2, 0.16, 0.38);
  items.splice(6, 0, run("Warden", 0.7, 0.16, 0.78));

  expect(parsePdfDiceTable(items)?.rows[0]).toEqual(["1", "Ryan Burke", "Warden"]);
});

it.each(["haha", "mama", "abab", "No No"])(
  "preserves legitimate repeated text in body cells: %s",
  name => {
    const items = maleVillagerTable();
    items[5] = run(name, 0.2, 0.16, 0.38);

    expect(parsePdfDiceTable(items)?.rows[0]?.[1]).toBe(name);
  },
);

it("normalizes a duplicated multiword body-cell phrase", () => {
  const items = maleVillagerTable();
  items[5] = run("Ryan BurkeRyan Burke", 0.2, 0.16, 0.38);

  expect(parsePdfDiceTable(items)?.rows[0]?.[1]).toBe("Ryan Burke");
});

it("refuses a flattened row that crosses inferred column boundaries", () => {
  const items = maleVillagerTable().filter(item => item.top <= 0.13);
  items.push(run("1 Ryan Burke", 0.1, 0.16, 0.38));
  items.push(run("2 Adam Campbell", 0.1, 0.18, 0.38));
  items.push(run("3 Logan Hunt", 0.1, 0.2, 0.38));

  expect(parsePdfDiceTable(items)).toBeUndefined();
});

it("does not classify prose as a table", () => {
  expect(parsePdfDiceTable([
    run("The room is quiet", 0.1, 0.1), run("until the pool moves", 0.1, 0.13),
    run("under the benches", 0.1, 0.16),
  ])).toBeUndefined();
});
