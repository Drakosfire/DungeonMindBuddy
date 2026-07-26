import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname);

const FORBIDDEN = [
  /from\s+["'][^"']*buildSurface[^"']*["']/,
  /from\s+["'][^"']*ingestSurface[^"']*["']/,
  /\bExtractionRun[A-Za-z]*\b/,
  /\bGraphReviewHandoff[A-Za-z]*\b/,
  /worldbuilding_shepherds_flock/,
  /\buseBuildExtraction\b/,
];

function stripCommentsAndStrings(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/(^|[^:])\/\/.*$/gm, "$1")
    .replace(/(['"`])(?:\\.|(?!\1)[\s\S])*\1/g, "''");
}

function listProductionFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const st = statSync(path);
    if (st.isDirectory()) {
      out.push(...listProductionFiles(path));
      continue;
    }
    if (!/\.(ts|tsx)$/.test(name)) continue;
    if (/\.test\.(ts|tsx)$/.test(name)) continue;
    if (name.endsWith("Boundaries.test.ts")) continue;
    out.push(path);
  }
  return out;
}

describe("markdownCanvas boundaries", () => {
  it("keeps generic canvas modules free of Build/extraction/Graph Review types", () => {
    const files = listProductionFiles(ROOT);
    expect(files.length).toBeGreaterThan(0);
    const violations: string[] = [];
    for (const file of files) {
      const source = stripCommentsAndStrings(readFileSync(file, "utf8"));
      for (const pattern of FORBIDDEN) {
        if (pattern.test(source)) {
          violations.push(`${file} matches ${pattern}`);
        }
      }
    }
    expect(violations).toEqual([]);
  });
});
