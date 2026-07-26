import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname);

/** Substrings/identifiers that must not appear in generic canvas production sources. */
const FORBIDDEN_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: "buildSurface import", pattern: /from\s+["'][^"']*buildSurface[^"']*["']/ },
  { name: "ingestSurface import", pattern: /from\s+["'][^"']*ingestSurface[^"']*["']/ },
  { name: "ExtractionRun type", pattern: /\bExtractionRun[A-Za-z]*\b/ },
  { name: "GraphReviewHandoff type", pattern: /\bGraphReviewHandoff[A-Za-z]*\b/ },
  { name: "useBuildExtraction", pattern: /\buseBuildExtraction\b/ },
  { name: "BUILD_EXTRACT_COMMAND_ID", pattern: /\bBUILD_EXTRACT_COMMAND_ID\b/ },
  { name: "BUILD_REFRESH_RUN_COMMAND_ID", pattern: /\bBUILD_REFRESH_RUN_COMMAND_ID\b/ },
  { name: "build.extract command", pattern: /["'`]build\.extract["'`]/ },
  { name: "build.refresh-run command", pattern: /["'`]build\.refresh-run["'`]/ },
  { name: "Build extraction copy", pattern: /before extraction/i },
  { name: "Build source copy", pattern: /Build source/i },
  { name: "worldbuilding profile id", pattern: /worldbuilding_shepherds_flock/ },
];

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
    out.push(path);
  }
  return out;
}

function exportedIdentifierHits(source: string): string[] {
  const hits: string[] = [];
  const exportRe = /export\s+(?:const|function|type|interface|class)\s+([A-Za-z0-9_]+)/g;
  let match: RegExpExecArray | null;
  while ((match = exportRe.exec(source)) !== null) {
    const name = match[1];
    if (/^BUILD_/i.test(name) || /Extract/i.test(name) || /GraphReview/i.test(name)) {
      hits.push(name);
    }
  }
  return hits;
}

describe("markdownCanvas boundaries", () => {
  it("keeps generic canvas modules free of Build extraction identity and copy", () => {
    const files = listProductionFiles(ROOT);
    expect(files.length).toBeGreaterThan(0);
    const violations: string[] = [];
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      for (const { name, pattern } of FORBIDDEN_PATTERNS) {
        if (pattern.test(source)) {
          violations.push(`${file}: ${name}`);
        }
      }
      for (const exported of exportedIdentifierHits(source)) {
        violations.push(`${file}: forbidden export ${exported}`);
      }
    }
    expect(violations).toEqual([]);
  });
});
