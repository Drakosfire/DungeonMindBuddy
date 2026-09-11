import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const srcRoot = resolve(process.cwd(), "src");

function readCss(relativeFromSrc: string): string {
  return readFileSync(resolve(srcRoot, relativeFromSrc), "utf8");
}

describe("app chrome band", () => {
  it("declares the inset once on :root for composable hosts outside .app-shell", () => {
    const css = readCss("styles.css");
    expect(css).toMatch(/:root\s*\{[^}]*--app-chrome-top:/s);
    expect(css).toMatch(/:root\s*\{[^}]*--app-chrome-bottom:\s*0rem/s);
    expect(css).toMatch(/:root:has\(\.plan-agent-shell\.open\)\s*\{[^}]*--app-chrome-bottom:\s*var\(--app-ask-open-height\)/s);
  });

  it("keeps Tools, Edit, Projection, and Author Node drawers inside the chrome band", () => {
    const styles = readCss("styles.css");
    const projection = readCss("surfaceInteraction/projection/projectionHost.css");
    const plan = readCss("planSurface/planSurface.css");

    expect(styles).toMatch(/\.app-tools-toolbox-drawer\s*\{[^}]*top:\s*var\(--app-chrome-top\)/s);
    expect(styles).toMatch(/\.app-tools-toolbox-drawer\s*\{[^}]*bottom:\s*var\(--app-chrome-bottom\)/s);
    expect(styles).toMatch(/\.app-edit-toolbox-drawer\s*\{[^}]*top:\s*var\(--app-chrome-top\)/s);
    expect(styles).toMatch(/\.app-edit-toolbox-drawer\s*\{[^}]*bottom:\s*var\(--app-chrome-bottom\)/s);

    expect(projection).toMatch(/\.surface-projection-drawer\s*\{[^}]*top:\s*var\(--app-chrome-top\)/s);
    expect(projection).toMatch(/\.surface-projection-drawer\s*\{[^}]*bottom:\s*var\(--app-chrome-bottom\)/s);
    expect(projection).toMatch(/\.surface-projection-drawer--fullscreen\s*\{[^}]*top:\s*var\(--app-chrome-top\)/s);
    expect(projection).toMatch(/\.surface-projection-drawer--fullscreen\s*\{[^}]*bottom:\s*var\(--app-chrome-bottom\)/s);

    expect(plan).toMatch(/\.graph-review-author-node-drawer\s*\{[^}]*top:\s*var\(--app-chrome-top\)/s);
    expect(plan).toMatch(/\.graph-review-author-node-drawer\s*\{[^}]*bottom:\s*var\(--app-chrome-bottom\)/s);
  });

  it("has no unavailable Ask sheet presentation and keeps the registered closed dock compact", () => {
    const css = readCss("planSurface/planSurface.css");
    expect(css).not.toMatch(/\.plan-agent-shell\.open\[data-ask-available="false"\]/);
    expect(css).toMatch(/\.plan-agent-shell\s*\{[^}]*width:\s*max-content;[^}]*max-width:\s*calc\(100vw - 2rem\)/s);
    expect(css).toMatch(/\.plan-agent-bar\s*\{[^}]*width:\s*5rem;[^}]*height:\s*5rem/s);
  });

  it("reserves wrapped navigation but no collapsed Agent band at the narrow breakpoint", () => {
    const css = readCss("styles.css");
    expect(css).toMatch(
      /@media[^{}]*\(max-width:\s*900px\)[\s\S]*?:root\s*\{[^}]*--app-chrome-top:\s*10rem;[^}]*--app-chrome-bottom:\s*0rem;/,
    );
  });
});
