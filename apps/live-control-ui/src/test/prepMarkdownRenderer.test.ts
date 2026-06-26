import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import vm from "node:vm";

import { describe, expect, it } from "vitest";

function loadRenderer(): (markdown: string) => string {
  const rendererPath = resolve(
    process.cwd(),
    "../../evals/c2_live_prep/mireward-prep/assets/prep-markdown.js",
  );
  const script = readFileSync(rendererPath, "utf8");
  const context: {
    window: {
      MirewardMarkdown?: {
        render: (markdown: string) => string;
      };
    };
  } = { window: {} };

  vm.runInNewContext(script, context);

  const render = context.window.MirewardMarkdown?.render;
  if (!render) {
    throw new Error("MirewardMarkdown.render was not registered");
  }

  return render;
}

function renderHost(markdown: string): HTMLElement {
  const render = loadRenderer();
  const host = document.createElement("div");
  host.innerHTML = render(markdown);
  return host;
}

describe("prep markdown renderer", () => {
  it("strips frontmatter before rendering visible content", () => {
    const host = renderHost("---\ntitle: Test Doc\n---\n\n# Visible Heading");

    expect(host.querySelector("h1")?.textContent).toBe("Visible Heading");
    expect(host.textContent).not.toContain("title: Test Doc");
    expect(host.textContent).not.toContain("---");
  });

  it("renders inline markdown while escaping unsafe HTML", () => {
    const host = renderHost("Paragraph with **bold**, *italic*, `code`, and <script>alert(1)</script>.");

    expect(host.querySelector("strong")?.textContent).toBe("bold");
    expect(host.querySelector("em")?.textContent).toBe("italic");
    expect(host.querySelector("code")?.textContent).toBe("code");
    expect(host.querySelector("script")).toBeNull();
    expect(host.innerHTML).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
  });

  it("retains the markdown preview link contract", () => {
    const host = renderHost("See [Plan](../../Docs/Plans/example.md).");
    const link = host.querySelector("a");

    expect(link).not.toBeNull();
    expect(link?.getAttribute("data-md-link")).toBe("1");
    expect(link?.getAttribute("href")).toBe("../../Docs/Plans/example.md");
    expect(link?.textContent).toBe("Plan");
  });

  it.each([
    ["npc", "lysandro-ironveil", "Lysandro Ironveil"],
    ["location", "north-reach-gate", "North Reach Gate"],
    ["statblock", "sewer-meat-creature", "Sewer Meat Creature"],
    ["roll-table", "gate-dilemma-d12", "Gate Dilemma d12"],
    ["citation", "c2s22-ending", "Session 22 ending"],
  ])("renders a supported %s reference as an inert typed chip", (type, id, label) => {
    const host = renderHost(`[${label}](#dmb-ref:${type}:${id})`);
    const chip = host.querySelector("button.md-ref-chip");

    expect(chip).not.toBeNull();
    expect(chip?.getAttribute("type")).toBe("button");
    expect(chip?.classList.contains(`md-ref-chip-${type}`)).toBe(true);
    expect(chip?.getAttribute("data-md-ref-kind")).toBe("ref");
    expect(chip?.getAttribute("data-md-ref-type")).toBe(type);
    expect(chip?.getAttribute("data-md-ref-id")).toBe(id);
    expect(chip?.textContent).toBe(label);
    expect(chip?.hasAttribute("data-md-link")).toBe(false);
    expect(host.querySelector("a")).toBeNull();
  });

  it("renders combat actions as inert action chips", () => {
    const host = renderHost("[North Gate Combat](#dmb-action:combat:north-gate-combat)");
    const chip = host.querySelector("button.md-ref-chip");

    expect(chip).not.toBeNull();
    expect(chip?.getAttribute("type")).toBe("button");
    expect(chip?.classList.contains("md-ref-chip-action")).toBe(true);
    expect(chip?.classList.contains("md-ref-chip-action-combat")).toBe(true);
    expect(chip?.getAttribute("data-md-ref-kind")).toBe("action");
    expect(chip?.getAttribute("data-md-ref-type")).toBe("combat");
    expect(chip?.getAttribute("data-md-ref-id")).toBe("north-gate-combat");
    expect(chip?.textContent).toBe("North Gate Combat");
    expect(chip?.hasAttribute("data-md-link")).toBe(false);
  });

  it.each([
    "#dmb-ref:monster:bog-thing",
    "#dmb-ref:npc:BadCaps",
    "#dmb-ref:npc:-starts-with-dash",
    "#dmb-action:launch:north-gate-combat",
    "#dmb-ref:npc",
    "#dmb-ref::id",
  ])("falls invalid typed href %s back to an ordinary link", (href) => {
    const host = renderHost(`[Unsupported](${href})`);
    const link = host.querySelector("a[data-md-link='1']");

    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe(href);
    expect(link?.textContent).toBe("Unsupported");
    expect(host.querySelector(".md-ref-chip")).toBeNull();
  });

  it("escapes typed chip labels without creating raw elements or handlers", () => {
    const host = renderHost("[<img src=x onerror=alert(1)>](#dmb-ref:npc:bad-label)");
    const chip = host.querySelector("button.md-ref-chip");

    expect(chip).not.toBeNull();
    expect(chip?.textContent).toContain("img src=x onerror=alert(1)");
    expect(host.querySelector("img")).toBeNull();
    expect(host.querySelector("[onerror]")).toBeNull();
  });

  it("keeps ordinary blockquotes as blockquotes", () => {
    const host = renderHost("> This is a normal blockquote.");

    expect(host.querySelector("blockquote")?.textContent).toContain("This is a normal blockquote.");
    expect(host.querySelector(".md-callout")).toBeNull();
    expect(host.querySelector("[data-md-callout]")).toBeNull();
  });

  it("falls unknown callout markers back to visible blockquotes", () => {
    const host = renderHost("> [!SECRET]\n> This marker is not supported.");

    expect(host.querySelector("blockquote")?.textContent).toContain("[!SECRET]");
    expect(host.querySelector("blockquote")?.textContent).toContain("This marker is not supported.");
    expect(host.querySelector(".md-callout")).toBeNull();
  });

  it.each([
    ["READ-ALOUD", "read-aloud", "Read aloud"],
    ["GM-NOTE", "gm-note", "GM note"],
    ["RULES", "rules", "Rules"],
    ["WARNING", "warning", "Warning"],
  ])("renders canonical %s callouts with the semantic contract", (marker, type, label) => {
    const host = renderHost(`> [!${marker}]\n> Text.`);
    const callout = host.querySelector(".md-callout");

    expect(callout).not.toBeNull();
    expect(callout?.tagName.toLowerCase()).toBe("aside");
    expect(callout?.classList.contains("md-callout")).toBe(true);
    expect(callout?.classList.contains(`md-callout-${type}`)).toBe(true);
    expect(callout?.getAttribute("data-md-callout")).toBe(type);
    expect(callout?.querySelector(".md-callout-label")?.textContent).toBe(label);
    expect(callout?.querySelector(".md-callout-body")?.textContent).toContain("Text.");
  });

  it.each([
    ["readaloud", "read-aloud"],
    ["dm", "gm-note"],
    ["rule", "rules"],
    ["danger", "warning"],
  ])("normalizes the %s callout alias", (marker, type) => {
    const host = renderHost(`> [!${marker}]\n> Text.`);

    expect(host.querySelector(".md-callout")?.getAttribute("data-md-callout")).toBe(type);
  });

  it("supports custom labels", () => {
    const host = renderHost("> [!WARNING] Breach clock\n> The gate fails in 3 rounds.");
    const callout = host.querySelector(".md-callout");

    expect(callout?.getAttribute("data-md-callout")).toBe("warning");
    expect(callout?.querySelector(".md-callout-label")?.textContent).toBe("Breach clock");
    expect(callout?.querySelector(".md-callout-body")?.textContent).toContain("The gate fails in 3 rounds.");
  });

  it("escapes custom callout labels", () => {
    const host = renderHost("> [!WARNING] <img src=x onerror=alert(1)>\n> Body.");

    expect(host.querySelector("img")).toBeNull();
    expect(host.querySelector(".md-callout-label")?.textContent).toBe("<img src=x onerror=alert(1)>");
  });

  it("renders markdown inside callout bodies", () => {
    const host = renderHost(
      "> [!RULES]\n> Treat this as **difficult terrain**.\n> - Fire suppresses regeneration.\n> - Cold slows movement.\n> <script>alert(1)</script>",
    );
    const body = host.querySelector(".md-callout-body");

    expect(body?.querySelector("strong")?.textContent).toBe("difficult terrain");
    expect(body?.querySelectorAll("li")).toHaveLength(2);
    expect(body?.querySelector("script")).toBeNull();
    expect(body?.innerHTML).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
  });

  it("does not parse callout markers inside fenced code", () => {
    const host = renderHost("```md\n> [!WARNING]\n> This is example syntax, not a real callout.\n```");

    expect(host.querySelector("pre code")?.textContent).toContain("> [!WARNING]");
    expect(host.querySelector(".md-callout")).toBeNull();
  });

  it("renders markdown tables", () => {
    const host = renderHost("| Creature | CR |\n|---|---:|\n| Sewer Meat | 3 |");

    expect(host.querySelector("table")).not.toBeNull();
    expect(host.querySelector("thead")?.textContent).toContain("Creature");
    expect(host.querySelector("tbody")?.textContent).toContain("Sewer Meat");
    expect(host.querySelector("tbody")?.textContent).toContain("3");
  });
});
