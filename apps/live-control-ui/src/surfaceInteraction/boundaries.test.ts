import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = __dirname;

/**
 * Substrings that must never appear in neutral production sources (handoff V9).
 * Tests may inspect predecessor shapes; production code may not import them.
 */
const FORBIDDEN_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: "planSurface reference", pattern: /\bplanSurface\b/ },
  { name: "buildSurface reference", pattern: /\bbuildSurface\b/ },
  { name: "ingestSurface reference", pattern: /\bingestSurface\b/ },
  { name: "AgentInteractionProvider reference", pattern: /\bAgentInteractionProvider\b/ },
  { name: "AppChrome reference", pattern: /\bAppChrome\b/ },
  { name: "markdownCanvas reference", pattern: /\bmarkdownCanvas\b/ },
  { name: "graphReference reference", pattern: /\bgraphReference\b/ },
  { name: "ReactNode", pattern: /\bReactNode\b/ },
  { name: "react import", pattern: /from\s+["']react(\/[^"']*)?["']/ },
  { name: ".tsx import specifier", pattern: /\.tsx["']/ },
];

/** The exact SIH-01 production allowlist (handoff §4). Later slices that add
 * files to this package must update this list deliberately. */
const EXPECTED_PRODUCTION_FILES = [
  "index.ts",
  "publication.ts",
  "surfaceIdentity.ts",
  "types.ts",
];

function listProductionFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      out.push(...listProductionFiles(path));
      continue;
    }
    if (!/\.(ts|tsx)$/.test(name)) continue;
    if (/\.test\.(ts|tsx)$/.test(name)) continue;
    out.push(path);
  }
  return out;
}

describe("surfaceInteraction boundaries", () => {
  it("contains exactly the allowlisted production files and no JSX host files", () => {
    const files = listProductionFiles(ROOT).map((path) => relative(ROOT, path));
    expect(files.sort()).toEqual(EXPECTED_PRODUCTION_FILES);
    expect(files.some((file) => file.endsWith(".tsx"))).toBe(false);
  });

  it("keeps production sources free of surface, domain, and React host references", () => {
    const violations: string[] = [];
    for (const file of listProductionFiles(ROOT)) {
      const source = readFileSync(file, "utf8");
      for (const { name, pattern } of FORBIDDEN_PATTERNS) {
        if (pattern.test(source)) {
          violations.push(`${relative(ROOT, file)}: ${name}`);
        }
      }
    }
    expect(violations).toEqual([]);
  });
});
