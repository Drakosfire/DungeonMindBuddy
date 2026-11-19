import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeAll, describe, expect, it } from "vitest";

// Keep this registered test path; the historical prototype no longer owns product navigation.

type MirewardPrepNavApi = {
  initNav: (activeId: string) => void;
};

function prepApi(): MirewardPrepNavApi {
  return (window as typeof window & { MirewardPrep: MirewardPrepNavApi }).MirewardPrep;
}

describe("Combat Tracker product nav", () => {
  beforeAll(() => {
    const prepPath = resolve(
      process.cwd(),
      "../../evals/c2_live_prep/mireward-prep/assets/prep.js",
    );
    window.eval(readFileSync(prepPath, "utf8"));
  });

  it("keeps the standalone Combat prototype inside local prep navigation", () => {
    document.body.innerHTML = '<nav id="site-nav" class="site-nav"></nav>';
    prepApi().initNav("combat");

    const host = document.getElementById("site-nav");
    expect(host).toHaveAttribute("aria-label", "Prep navigation");

    const links = Array.from(host?.querySelectorAll("a") ?? []).map((anchor) => ({
      href: anchor.getAttribute("href"),
      label: anchor.textContent,
      active: anchor.classList.contains("active"),
    }));

    const pages = [
      ["index.html", "Index"], ["live-play.html", "Live play"],
      ["retrieval.html", "Retrieval"], ["combat.html", "Combat tracker"],
      ["live-notes.html", "Live notes"], ["timeline.html", "Timeline"],
      ["locations.html", "Locations"], ["npcs.html", "NPCs"],
      ["roll-tables.html", "Roll tables"], ["statblocks.html", "Statblocks"],
      ["markdown-theme-fixtures.html", "Theme fixtures"],
    ];
    expect(links).toEqual(pages.map(([page, label]) => ({
      href: `/${page}`, label, active: page === "combat.html",
    })));
    for (const [page] of pages) {
      expect(existsSync(resolve(process.cwd(), "../../evals/c2_live_prep/mireward-prep", page!))).toBe(true);
    }
    const combatHtml = readFileSync(resolve(process.cwd(), "../../evals/c2_live_prep/mireward-prep/combat.html"), "utf8");
    expect(combatHtml).toContain('MirewardPrep.initNav("combat");');
    expect(combatHtml).not.toContain('initNav("combat", "product")');
    expect(links.some(link => ["/", "/graph", "/plan", "/play", "/combat"].includes(link.href ?? ""))).toBe(false);
  });

  it("keeps legacy prep nav available for non-product pages", () => {
    document.body.innerHTML = '<nav id="site-nav" class="site-nav"></nav>';
    prepApi().initNav("live-play");

    const labels = Array.from(document.querySelectorAll("#site-nav a")).map((a) => a.textContent);
    expect(labels).toContain("Live play");
    expect(labels).toContain("Retrieval");
    expect(labels).not.toContain("Plan");
  });
});
