import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeAll, describe, expect, it } from "vitest";

import { APP_NAV_ITEMS } from "../chrome/appChromeConfig";

type MirewardPrepNavApi = {
  initNav: (activeId: string, navMode?: "product" | "prep") => void;
};

function prepApi(): MirewardPrepNavApi {
  return (window as typeof window & { MirewardPrep: MirewardPrepNavApi }).MirewardPrep;
}

describe("Play product nav", () => {
  beforeAll(() => {
    const prepPath = resolve(
      process.cwd(),
      "../../evals/c2_live_prep/mireward-prep/assets/prep.js",
    );
    window.eval(readFileSync(prepPath, "utf8"));
  });

  it("renders Command Board links matching AppChrome with Play", () => {
    document.body.innerHTML = '<nav id="site-nav" class="site-nav"></nav>';
    prepApi().initNav("play", "product");

    const host = document.getElementById("site-nav");
    expect(host).toHaveAttribute("aria-label", "Command board navigation");

    const links = Array.from(host?.querySelectorAll("a") ?? []).map((anchor) => ({
      href: anchor.getAttribute("href"),
      label: anchor.textContent,
      active: anchor.classList.contains("active"),
    }));

    expect(links).toEqual(
      APP_NAV_ITEMS.map((item) => ({
        href: item.href,
        label: item.label,
        active: item.href === "/play",
      })),
    );
    expect(links.some((link) => /combat|statblocks|live play|retrieval/i.test(link.label ?? ""))).toBe(
      false,
    );
  });

  it("marks Play active for legacy combat/roll product page ids", () => {
    document.body.innerHTML = '<nav id="site-nav" class="site-nav"></nav>';
    prepApi().initNav("combat", "product");

    const links = Array.from(document.querySelectorAll("#site-nav a")).map((anchor) => ({
      href: anchor.getAttribute("href"),
      label: anchor.textContent,
      active: anchor.classList.contains("active"),
    }));

    expect(links).toEqual(
      APP_NAV_ITEMS.map((item) => ({
        href: item.href,
        label: item.label,
        active: item.href === "/play",
      })),
    );
  });

  it("keeps legacy prep nav available for non-product pages", () => {
    document.body.innerHTML = '<nav id="site-nav" class="site-nav"></nav>';
    prepApi().initNav("live-play", "prep");

    const labels = Array.from(document.querySelectorAll("#site-nav a")).map((a) => a.textContent);
    expect(labels).toContain("Live play");
    expect(labels).toContain("Retrieval");
    expect(labels).not.toContain("Plan");
  });
});
