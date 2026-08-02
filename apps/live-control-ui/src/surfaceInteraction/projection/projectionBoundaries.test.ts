import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const PROJECTION_ROOT = __dirname;
const SRC_ROOT = join(PROJECTION_ROOT, "../..");

const FORBIDDEN_PROJECTION_IMPORTS: Array<{ name: string; pattern: RegExp }> = [
  {
    name: "planSurface import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*planSurface/,
  },
  {
    name: "buildSurface import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*buildSurface/,
  },
  {
    name: "ingestSurface import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*ingestSurface/,
  },
  {
    name: "api import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*\/api\//,
  },
  {
    name: "graphReference import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*graphReference/,
  },
  {
    name: "projectionRegistry import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*projectionRegistry/,
  },
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

function listProductionSourcesUnder(relativeDir: string): string[] {
  return listProductionFiles(join(SRC_ROOT, relativeDir));
}

function readRelative(pathFromSrc: string): string {
  return readFileSync(join(SRC_ROOT, pathFromSrc), "utf8");
}

describe("projection host ownership boundaries", () => {
  it("removes AdaptiveProjectionContainer from production sources", () => {
    const hits: string[] = [];
    for (const file of listProductionSourcesUnder("")) {
      const source = readFileSync(file, "utf8");
      if (/\bAdaptiveProjectionContainer\b/.test(source)) {
        hits.push(relative(SRC_ROOT, file));
      }
    }
    expect(hits).toEqual([]);
  });

  it("mounts exactly one LegacyProjectionHostAdapter in App.tsx", () => {
    const appSource = readRelative("App.tsx");
    expect(appSource.match(/<LegacyProjectionHostAdapter\s*\/>/g)).toHaveLength(1);
    expect(appSource.match(/\bimport\s+\{\s*LegacyProjectionHostAdapter\s*\}/g)).toHaveLength(1);
  });

  it("uses ProjectionHost exactly once in production", () => {
    const hits: string[] = [];
    for (const file of listProductionSourcesUnder("")) {
      const source = readFileSync(file, "utf8");
      const matches = source.match(/<ProjectionHost\b/g);
      if (matches?.length) {
        hits.push(`${relative(SRC_ROOT, file)}:${matches.length}`);
      }
    }
    expect(hits).toEqual(["planSurface/projection/LegacyProjectionHostAdapter.tsx:1"]);
  });

  it("keeps neutral projection production sources free of Plan/domain imports", () => {
    const violations: string[] = [];
    for (const file of listProductionFiles(PROJECTION_ROOT)) {
      const source = readFileSync(file, "utf8");
      for (const { name, pattern } of FORBIDDEN_PROJECTION_IMPORTS) {
        if (pattern.test(source)) {
          violations.push(`${relative(PROJECTION_ROOT, file)}: ${name}`);
        }
      }
    }
    expect(violations).toEqual([]);
  });

  it("keeps projectionHost.css free of plan-* selectors", () => {
    const css = readFileSync(join(PROJECTION_ROOT, "projectionHost.css"), "utf8");
    expect(css).not.toMatch(/\.plan-/);
  });

  it("does not use localStorage under surfaceInteraction/projection production sources", () => {
    const violations: string[] = [];
    for (const file of listProductionFiles(PROJECTION_ROOT)) {
      const source = readFileSync(file, "utf8");
      if (/localStorage/.test(source)) {
        violations.push(relative(PROJECTION_ROOT, file));
      }
    }
    expect(violations).toEqual([]);
  });

  it("imports ActiveProjection from surfaceInteraction/projection/types in provider types", () => {
    const providerTypes = readRelative("agentInteraction/agentInteractionTypes.ts");
    expect(providerTypes).toMatch(
      /from\s+["']\.\.\/surfaceInteraction\/projection\/types["']/,
    );
    expect(providerTypes).not.toMatch(/from\s+["'][^"']*planSurface\/types["']/);
  });
});
