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
