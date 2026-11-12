import {cleanup, fireEvent, render, screen} from "@testing-library/react";
import {afterEach, expect, it} from "vitest";
import {PdfStatblockCandidate} from "./PdfStatblockCandidate";

afterEach(cleanup);
const locator = {source_revision_id:"srev:test",content_sha256:"a".repeat(64),page:5,left:0,top:0,right:1,bottom:1};

it("previews labeled fields with the source page", () => {
  render(<PdfStatblockCandidate locator={locator} text={"Bed Dragon Wyrmling\nArmor Class 1 6\nHit Points 75"} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getByText("Page 5 · srev:test")).toBeInTheDocument();
  expect(screen.getByText("16")).toBeInTheDocument();
  expect(screen.getByText("75")).toBeInTheDocument();
});

it("asks for a narrower capture when multiple statblocks are present", () => {
  render(<PdfStatblockCandidate locator={locator} text={"Armor Class 16\nHit Points 75\nArmor Class 12\nHit Points 55"} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getByText(/Select a region with one labeled/)).toBeInTheDocument();
  expect(screen.queryByText("16")).toBeNull();
});

it("reads the six printed scores without treating modifiers as scores", () => {
  const text = "Armor Class 16\nHit Points 75\nSTR DEX CON INT WIS CHA\n19 (+4) 14 (+2) 17 (+3) 8 (-1) 8 (-1) 4 (-3)";
  render(<PdfStatblockCandidate locator={locator} text={text} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getAllByRole("definition").map(item => item.textContent)).toEqual(
    ["16", "75", "19", "14", "17", "8", "8", "4"],
  );
});

it("omits an incomplete ability row", () => {
  const text = "Armor Class 16\nHit Points 75\nSTR DEX CON INT WIS CHA\n19 14 17 8 8";
  render(<PdfStatblockCandidate locator={locator} text={text} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getAllByRole("definition").map(item => item.textContent)).toEqual(["16", "75"]);
});

it("keeps printed rules sections separate without rewriting them", () => {
  const text = [
    "Armor Class 16", "Hit Points 75", "Actions", "Bite. First line.",
    "  Second line.", "Lair Actions", "The floor shifts.", "Lair Actions (Cont.)",
    "The ceiling shifts.", "Regional Effects", "Fog gathers.",
  ].join("\n");
  render(<PdfStatblockCandidate locator={locator} text={text} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getByText("Actions · captured text").nextElementSibling?.textContent).toBe("Bite. First line.\n  Second line.");
  expect(screen.getByText("Lair Actions · captured text").nextElementSibling?.textContent).toBe("The floor shifts.");
  expect(screen.getByText("Lair Actions (Cont.) · captured text").nextElementSibling?.textContent).toBe("The ceiling shifts.");
  expect(screen.getByText("Regional Effects · captured text").nextElementSibling?.textContent).toBe("Fog gathers.");
});

it("keeps PDF.js split digits inside their printed score cells", () => {
  const text = "Armor Class 16\nHit Points 75\nSTR DEX CON INT WIS CHA\n1 9(+4) 1 4(+2) 1 7(+3) 8(-1 ) 8(-1 ) 4(-3)";
  render(<PdfStatblockCandidate locator={locator} text={text} />);
  fireEvent.click(screen.getByRole("button", { name: "Preview statblock fields" }));
  expect(screen.getAllByRole("definition").map(item => item.textContent)).toEqual(
    ["16", "75", "19", "14", "17", "8", "8", "4"],
  );
});

it("shows the printed HP and dice formula together even when they disagree", () => {
  render(<PdfStatblockCandidate locator={locator} text={"Armor Class 11\nHit Points 18 (2d10+6)"} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getByText("18 (2d10+6)")).toBeInTheDocument();
});

it("rejoins split PDF digits within the HP formula", () => {
  render(<PdfStatblockCandidate locator={locator} text={"Armor Class 16\nHit Points 75 (1 0d8 + 30)"} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview statblock fields"}));
  expect(screen.getByText("75 (10d8 + 30)")).toBeInTheDocument();
});

it("does not offer a statblock preview for a captured name table", () => {
  render(<PdfStatblockCandidate locator={locator} text={`Male Villager Names
1d12 Name Notes
1 Ryan Burke
2 Adam Campbell
3 Logan Hunt`} />);
  expect(screen.queryByRole("button", {name:"Preview statblock fields"})).toBeNull();
  expect(screen.queryByRole("region", {name:"Extracted statblock fields"})).toBeNull();
});
