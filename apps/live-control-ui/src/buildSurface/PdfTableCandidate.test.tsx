import {cleanup, fireEvent, render, screen, within} from "@testing-library/react";
import {afterEach, expect, it} from "vitest";
import {PdfTableCandidate} from "./PdfTableCandidate";
import type {PdfRegionTextRun} from "./parsePdfDiceTable";

afterEach(cleanup);
const locator = {source_revision_id:"srev:conks-gold",content_sha256:"a".repeat(64),page:18,left:0.1,top:0.1,right:0.8,bottom:0.6};
const items: PdfRegionTextRun[] = [
  {text:"Male Villager NamesMale Villager Names",left:0.1,right:0.45,top:0.1,bottom:0.11},
  {text:"1d121d12",left:0.1,right:0.15,top:0.13,bottom:0.14},
  {text:"NameName",left:0.2,right:0.3,top:0.13,bottom:0.14},
  {text:"NotesNotes",left:0.7,right:0.8,top:0.13,bottom:0.14},
  {text:"1",left:0.1,right:0.13,top:0.16,bottom:0.17},
  {text:"Ryan Burke",left:0.2,right:0.35,top:0.16,bottom:0.17},
  {text:"2",left:0.1,right:0.13,top:0.18,bottom:0.19},
  {text:"Adam Campbell",left:0.2,right:0.38,top:0.18,bottom:0.19},
  {text:"3",left:0.1,right:0.13,top:0.2,bottom:0.21},
  {text:"Logan Hunt",left:0.2,right:0.35,top:0.2,bottom:0.21},
];

it("shows a collapsible table with its exact source page and region", () => {
  render(<PdfTableCandidate items={items} locator={locator} />);
  fireEvent.click(screen.getByRole("button", {name:"Preview table rows"}));
  const table = screen.getByRole("table");
  expect(screen.getByText("Male Villager Names")).toBeInTheDocument();
  expect(screen.getByText(/Page 18 · srev:conks-gold · region/)).toBeInTheDocument();
  expect(within(table).getAllByRole("columnheader").map(header => header.textContent)).toEqual(["1d12", "Name", "Notes"]);
  expect(within(table).getByText("Ryan Burke")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name:"Collapse table preview"}));
  expect(screen.getByRole("button", {name:"Preview table rows"})).toBeInTheDocument();
});

it("does not offer a structured table for clipped selections", () => {
  render(<PdfTableCandidate items={items} locator={locator} clipped />);
  expect(screen.queryByRole("button", {name:"Preview table rows"})).toBeNull();
});
