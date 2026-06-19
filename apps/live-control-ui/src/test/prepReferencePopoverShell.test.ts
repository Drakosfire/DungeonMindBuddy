import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

type MirewardPrepPopoverApi = {
  initRunbookReferencePopoverShell: () => void;
  closeRunbookReferencePopover: (options?: { restoreFocus?: boolean }) => void;
  resetRunbookReferenceIndexCache: () => void;
};

type FetchMock = ReturnType<typeof vi.fn>;

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
  prepApi().resetRunbookReferenceIndexCache();
  document.body.innerHTML = '<button type="button" id="outside">Outside</button>';
  (globalThis as typeof globalThis & { fetch: FetchMock }).fetch = vi.fn((url: string) =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(emptyPayloadForUrl(String(url))),
    }),
  ) as FetchMock;
  prepApi().initRunbookReferencePopoverShell();
});

function emptyPayloadForUrl(url: string): unknown {
  if (url.includes("/npcs/")) return { npcs: [] };
  if (url.includes("/locations/")) return { locations: [] };
  if (url.includes("/statblocks/")) return { statblocks: [] };
  if (url.includes("/roll-tables/")) return { roll_tables: [] };
  return {};
}

function mockJsonRoutes(routes: Record<string, unknown>): FetchMock {
  const fetch = vi.fn((url: string) => {
    const path = String(url);
    const payload = routes[path] ?? emptyPayloadForUrl(path);
    return Promise.resolve({ ok: true, json: () => Promise.resolve(payload) });
  }) as FetchMock;
  (globalThis as typeof globalThis & { fetch: FetchMock }).fetch = fetch;
  return fetch;
}

function nextTick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("runbook reference popover shell", () => {
  it("stacks above the Markdown viewer modal for modal preview chips", () => {
    const cssPath = resolve(
      process.cwd(),
      "../../evals/c2_live_prep/mireward-prep/assets/prep.css",
    );
    const css = readFileSync(cssPath, "utf8");

    expect(css).toMatch(/Above \.md-viewer at z-index: 1000/);
    expect(css).toMatch(/\.runbook-ref-popover\s*{[^}]*z-index:\s*1100;/s);
  });

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
      "Loading reference",
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

  it("closes an already-open popover when a malformed chip is clicked", () => {
    const chip = referenceChip();
    chip.click();
    const malformed = document.createElement("button");
    malformed.className = "md-ref-chip";
    document.body.appendChild(malformed);

    malformed.click();

    expect(document.getElementById("runbook-ref-popover")).toHaveAttribute("hidden");
    expect(chip).toHaveAttribute("aria-expanded", "false");
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


describe("runbook reference resolver", () => {
  it("resolves an NPC chip from the live NPC index", async () => {
    mockJsonRoutes({
      "/api/live/npcs/index": {
        npcs: [{
          index_id: "campaign_2-lysandro-ironveil",
          title: "Lysandro Ironveil",
          slug: "lysandro-ironveil",
          section: "campaign_2",
          primary_doc_path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/lysandro-ironveil/character_seed.md",
          table_note: "Human accelerant at the gate.",
          canon_layer: "active",
        }],
      },
    });
    referenceChip().click();
    expect(document.querySelector(".runbook-ref-popover-status")).toHaveTextContent("Loading reference");
    await nextTick();
    expect(document.querySelector(".runbook-ref-resolved-eyebrow")).toHaveTextContent("Resolved NPC");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Lysandro Ironveil");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Human accelerant at the gate.");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("character_seed.md");
    expect(document.querySelector(".runbook-ref-popover-actions")).toHaveTextContent("Pin to session context");
    document.querySelectorAll<HTMLButtonElement>(".runbook-ref-popover-actions button").forEach((button) =>
      expect(button).toBeDisabled(),
    );
  });

  it("matches statblock references against normalized source path stems", async () => {
    mockJsonRoutes({
      "/api/live/statblocks/index": {
        statblocks: [{
          index_id: "c2-sewer-meat-creature-statblock",
          title: "Sewer Meat Creature",
          corpus_display_path: "corpus/bestiary/sewer_meat_creature_statblock_cr3.md",
          challenge_rating: "3",
          creature_type: "aberration",
          role_tag: "Brute",
          info_tag: "Gate hazard",
        }],
      },
    });
    referenceChip({ type: "statblock", id: "sewer-meat-creature", label: "Sewer Meat Creature" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-resolved-eyebrow")).toHaveTextContent("Resolved Statblock");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("CR3");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Brute");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Gate hazard");
  });

  it("resolves roll table chips from table_id", async () => {
    mockJsonRoutes({
      "/api/live/roll-tables/index": {
        roll_tables: [{
          table_id: "gate-dilemma-d12",
          title: "Gate Dilemma d12",
          dice: "1d12",
          table_note: "Pressure at North Reach Gate.",
          corpus_display_path: "corpus/tables/gate_dilemma_d12.md",
        }],
      },
    });
    referenceChip({ type: "roll-table", id: "gate-dilemma-d12", label: "Gate Dilemma d12" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-resolved-eyebrow")).toHaveTextContent("Resolved Roll Table");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("1d12");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Pressure at North Reach Gate.");
  });

  it("resolves location chips from the location index", async () => {
    mockJsonRoutes({
      "/api/live/locations/index": {
        locations: [{
          index_id: "north-reach-gate",
          title: "North Reach Gate",
          table_note: "Crowded checkpoint.",
          corpus_display_path: "corpus/locations/north_reach_gate.md",
        }],
      },
    });
    referenceChip({ type: "location", id: "north-reach-gate", label: "North Reach Gate" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-resolved-eyebrow")).toHaveTextContent("Resolved Location");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Crowded checkpoint.");
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("north_reach_gate.md");
  });

  it("renders citation and combat action placeholders without fetching indexes", async () => {
    const fetch = mockJsonRoutes({});
    referenceChip({ type: "citation", id: "c2s22-ending", label: "Session 22 ending" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-unresolved")).toHaveTextContent("Citation placeholder");
    expect(document.querySelector(".runbook-ref-unresolved")).toHaveTextContent("Citation resolver pending");

    referenceChip({ kind: "action", type: "combat", id: "north-gate-combat", label: "North Gate Combat" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-unresolved")).toHaveTextContent("Combat action placeholder");
    expect(document.querySelector(".runbook-ref-unresolved")).toHaveTextContent("Launch behavior is intentionally disabled");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("renders calm unresolved and error states", async () => {
    mockJsonRoutes({ "/api/live/npcs/index": { npcs: [] } });
    referenceChip({ id: "missing-person", label: "Missing Person" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-unresolved")).toHaveTextContent("Missing reference");
    expect(document.querySelector(".runbook-ref-unresolved")).toHaveTextContent("#dmb-ref:npc:missing-person");

    (globalThis as typeof globalThis & { fetch: FetchMock }).fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({ detail: "Service unavailable" }) }),
    ) as FetchMock;
    referenceChip({ type: "location", id: "north-reach-gate", label: "North Reach Gate" }).click();
    await nextTick();
    expect(document.querySelector(".runbook-ref-resolver-error")).toHaveTextContent("Resolver unavailable");
    expect(document.querySelector(".runbook-ref-popover")?.hasAttribute("hidden")).toBe(false);
  });

  it("uses per-type cache and guards against stale async results", async () => {
    const fetch = mockJsonRoutes({
      "/api/live/npcs/index": { npcs: [{ slug: "lysandro-ironveil", title: "Lysandro Ironveil" }] },
      "/api/live/statblocks/index": { statblocks: [{ title: "Sewer Meat Creature", corpus_display_path: "sewer_meat_creature_statblock_cr3.md" }] },
    });
    referenceChip().click();
    await nextTick();
    referenceChip({ id: "lysandro-ironveil", label: "Lysandro Again" }).click();
    await nextTick();
    expect(fetch.mock.calls.filter(([url]) => String(url) === "/api/live/npcs/index")).toHaveLength(1);

    prepApi().resetRunbookReferenceIndexCache();
    let resolveNpc!: (value: unknown) => void;
    (globalThis as typeof globalThis & { fetch: FetchMock }).fetch = vi.fn((url: string) => {
      if (String(url).includes("npcs")) {
        return new Promise((resolve) => { resolveNpc = resolve; });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ statblocks: [{ title: "Sewer Meat Creature", corpus_display_path: "sewer_meat_creature_statblock_cr3.md" }] }),
      });
    }) as FetchMock;
    referenceChip({ id: "new-npc", label: "New NPC" }).click();
    referenceChip({ type: "statblock", id: "sewer-meat-creature", label: "Sewer Meat Creature" }).click();
    resolveNpc({ ok: true, json: () => Promise.resolve({ npcs: [{ slug: "new-npc", title: "Wrong NPC" }] }) });
    await nextTick();
    await nextTick();
    expect(document.querySelector(".runbook-ref-resolved-card")).toHaveTextContent("Sewer Meat Creature");
    expect(document.querySelector(".runbook-ref-resolved-card")).not.toHaveTextContent("Wrong NPC");
  });
});
