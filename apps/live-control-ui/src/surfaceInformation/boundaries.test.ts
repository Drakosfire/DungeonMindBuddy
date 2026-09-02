import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = __dirname;

const FORBIDDEN_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  {
    name: "domain module import",
    pattern:
      /\b(from|import)\b\s*\(?\s*['"][^'"]*(planSurface|buildSurface|ingestSurface|playSurface|agentInteraction|chrome|surfaceInteraction|markdownCanvas|graphReference)/,
  },
  { name: "ReactNode", pattern: /\bReactNode\b/ },
  { name: "react import", pattern: /from\s+["']react(\/[^"']*)?["']/ },
  { name: ".tsx import specifier", pattern: /\.tsx["']/ },
  { name: "localStorage", pattern: /\blocalStorage\b/ },
  { name: "sessionStorage", pattern: /\bsessionStorage\b/ },
  { name: "fetch", pattern: /\bfetch\s*\(/ },
  { name: "indexedDB", pattern: /\bindexedDB\b/ },
];

const EXPECTED_PRODUCTION_FILES = ["channel.ts", "index.ts", "types.ts"];

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

describe("surfaceInformation boundaries", () => {
  it("contains exactly the allowlisted production files and no JSX host files", () => {
    const files = listProductionFiles(ROOT).map((path) => relative(ROOT, path));
    expect(files.sort()).toEqual(EXPECTED_PRODUCTION_FILES);
    expect(files.some((file) => file.endsWith(".tsx"))).toBe(false);
  });

  it("keeps production sources React-, chrome-, domain-, and persistence-neutral", () => {
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
