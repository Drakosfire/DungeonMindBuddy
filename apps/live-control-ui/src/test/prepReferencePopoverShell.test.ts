import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeAll, beforeEach, describe, expect, it } from "vitest";

type MirewardPrepPopoverApi = {
  initRunbookReferencePopoverShell: () => void;
  closeRunbookReferencePopover: (options?: { restoreFocus?: boolean }) => void;
};

function prepApi(): MirewardPrepPopoverApi {
  return (window as typeof window & { MirewardPrep: MirewardPrepPopoverApi }).MirewardPrep;
}

function referenceChip({
  kind = "ref",
  type = "npc",
  id = "lysandro-ironveil",
  label = "Lysandro Ironveil",
}: {
  kind?: string;
  type?: string;
  id?: string;
  label?: string;
} = {}): HTMLButtonElement {
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = `md-ref-chip md-ref-chip-${type}`;
  chip.dataset.mdRefKind = kind;
  chip.dataset.mdRefType = type;
  chip.dataset.mdRefId = id;
  chip.textContent = label;
  document.body.appendChild(chip);
  return chip;
}

beforeAll(() => {
  const prepPath = resolve(
    process.cwd(),
    "../../evals/c2_live_prep/mireward-prep/assets/prep.js",
  );
  window.eval(readFileSync(prepPath, "utf8"));
});

beforeEach(() => {
  prepApi().closeRunbookReferencePopover();
  document.body.innerHTML = '<button type="button" id="outside">Outside</button>';
  prepApi().initRunbookReferencePopoverShell();
});

describe("runbook reference popover shell", () => {
  it("opens from a reference chip and shows its shell metadata", () => {
    const chip = referenceChip();

    chip.click();

    const popover = document.getElementById("runbook-ref-popover");
    expect(popover).not.toBeNull();
    expect(popover?.hidden).toBe(false);
    expect(popover?.querySelector("#runbook-ref-popover-title")).toHaveTextContent(
      "Lysandro Ironveil",
    );
    expect(popover?.querySelector(".runbook-ref-popover-meta")).toHaveTextContent("Kindref");
    expect(popover?.querySelector(".runbook-ref-popover-meta")).toHaveTextContent("Typenpc");
    expect(popover?.querySelector(".runbook-ref-popover-meta")).toHaveTextContent(
      "IDlysandro-ironveil",
    );
    expect(popover?.querySelector(".runbook-ref-popover-meta")).toHaveTextContent(
      "Href#dmb-ref:npc:lysandro-ironveil",
    );
    expect(popover?.querySelector(".runbook-ref-popover-status")).toHaveTextContent(
      "Resolver pending",
    );
    expect(chip).toHaveAttribute("aria-haspopup", "dialog");
    expect(chip).toHaveAttribute("aria-controls", "runbook-ref-popover");
    expect(chip).toHaveAttribute("aria-expanded", "true");
  });

  it("builds action hrefs and disabled combat placeholders", () => {
    const chip = referenceChip({
      kind: "action",
      type: "combat",
      id: "north-gate-combat",
      label: "North Gate Combat",
    });

    chip.click();

    const popover = document.getElementById("runbook-ref-popover");
    expect(popover?.querySelector(".runbook-ref-popover-meta")).toHaveTextContent(
      "#dmb-action:combat:north-gate-combat",
    );
    const launch = Array.from(
      popover?.querySelectorAll<HTMLButtonElement>(".runbook-ref-popover-actions button") ?? [],
    ).find((button) => button.textContent === "Launch combat");
    expect(launch).toBeDisabled();
  });

  it("closes on Escape and restores focus to the trigger", () => {
    const chip = referenceChip();
    chip.click();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

    expect(document.getElementById("runbook-ref-popover")).toHaveAttribute("hidden");
    expect(chip).toHaveAttribute("aria-expanded", "false");
    expect(document.activeElement).toBe(chip);
  });

  it("closes on an outside click", () => {
    const chip = referenceChip();
    chip.click();

    document.getElementById("outside")?.click();

    expect(document.getElementById("runbook-ref-popover")).toHaveAttribute("hidden");
    expect(chip).toHaveAttribute("aria-expanded", "false");
  });

  it("closes from its close button and restores focus", () => {
    const chip = referenceChip();
    chip.click();

    document
      .querySelector<HTMLButtonElement>(".runbook-ref-popover-close")
      ?.click();

    expect(document.getElementById("runbook-ref-popover")).toHaveAttribute("hidden");
    expect(chip).toHaveAttribute("aria-expanded", "false");
    expect(document.activeElement).toBe(chip);
  });

  it("ignores normal, invalid, and malformed buttons", () => {
    const invalid = document.createElement("button");
    invalid.className = "md-ref-invalid";
    document.body.appendChild(invalid);
    const malformed = document.createElement("button");
    malformed.className = "md-ref-chip";
    document.body.appendChild(malformed);

    document.getElementById("outside")?.click();
    invalid.click();
    malformed.click();

    expect(document.getElementById("runbook-ref-popover")).toHaveAttribute("hidden");
  });

  it("opens for a chip inserted after initialization", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    host.innerHTML = `
      <button type="button" class="md-ref-chip md-ref-chip-location"
        data-md-ref-kind="ref" data-md-ref-type="location" data-md-ref-id="north-reach-gate">
        North Reach Gate
      </button>
    `;

    host.querySelector<HTMLButtonElement>(".md-ref-chip")?.click();

    expect(document.getElementById("runbook-ref-popover")?.hidden).toBe(false);
    expect(document.getElementById("runbook-ref-popover-title")).toHaveTextContent(
      "North Reach Gate",
    );
  });

  it("opens when a valid chip receives focus", () => {
    const chip = referenceChip();

    chip.focus();

    expect(document.getElementById("runbook-ref-popover")?.hidden).toBe(false);
    expect(chip).toHaveAttribute("aria-expanded", "true");
  });
});
