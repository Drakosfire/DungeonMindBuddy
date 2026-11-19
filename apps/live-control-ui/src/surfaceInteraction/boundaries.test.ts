import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = __dirname;

/**
 * Import/export specifiers that must never appear in neutral production sources
 * (handoff V9). Tests may inspect predecessor shapes; production code may not
 * import them. Anchored on import/export specifiers only — neutral naming,
 * comments, and doc text are not constrained.
 */
const FORBIDDEN_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  {
    name: "domain module import",
    pattern:
      /\b(from|import)\b\s*\(?\s*['"][^'"]*(planSurface|buildSurface|ingestSurface|agentInteraction|chrome|markdownCanvas|graphReference)/,
  },
  {
    name: "shared host import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*\/(contextHost|peekHost|toolHost|editHost|projection|SurfaceSelectionActions)(?:\/|\.tsx?['"]|['"])/,
  },
  { name: "ReactNode", pattern: /\bReactNode\b/ },
  { name: "react import", pattern: /from\s+["']react(\/[^"']*)?["']/ },
  { name: ".tsx import specifier", pattern: /\.tsx["']/ },
];

/** The exact SIH-01 neutral core. Shared React hosts are separate owners below. */
const EXPECTED_NEUTRAL_FILES = [
  "index.ts",
  "publication.ts",
  "surfaceIdentity.ts",
  "types.ts",
];

/** These package owners already have their own boundary checks. */
const SEPARATELY_CHECKED_HOST_DIRS = ["projection", "toolHost", "editHost"];

/** Later shared presentation files; additions require explicit classification. */
const EXPECTED_SHARED_HOST_FILES = [
  "SurfaceSelectionActions.tsx",
  "contextHost/SurfaceContextHost.tsx",
  "contextHost/SurfaceContextModule.tsx",
  "contextHost/SurfaceContextPrimitives.tsx",
  "contextHost/SurfaceContextProvider.tsx",
  "contextHost/SurfaceNavbarIconButton.tsx",
  "contextHost/index.ts",
  "contextHost/surfaceContextTypes.ts",
  "contextHost/useSurfaceContext.ts",
  "peekHost/PeekRegionProvider.tsx",
  "peekHost/index.ts",
];

function listNeutralFiles(): string[] {
  return listProductionFiles(ROOT, SEPARATELY_CHECKED_HOST_DIRS).filter(
    (file) => !EXPECTED_SHARED_HOST_FILES.includes(relative(ROOT, file)),
  );
}

function listProductionFiles(dir: string, skipSubdirs: readonly string[] = []): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    if (skipSubdirs.includes(name)) continue;
    const path = join(dir, name);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      out.push(...listProductionFiles(path, skipSubdirs));
      continue;
    }
    if (!/\.(ts|tsx)$/.test(name)) continue;
    if (/\.test\.(ts|tsx)$/.test(name)) continue;
    out.push(path);
  }
  return out;
}

describe("surfaceInteraction boundaries", () => {
  it("classifies production files and keeps the neutral core free of JSX hosts", () => {
    const files = listProductionFiles(ROOT, SEPARATELY_CHECKED_HOST_DIRS).map((path) => relative(ROOT, path));
    expect(files.sort()).toEqual([...EXPECTED_NEUTRAL_FILES, ...EXPECTED_SHARED_HOST_FILES].sort());
    const neutralFiles = listNeutralFiles().map((path) => relative(ROOT, path));
    expect(neutralFiles.sort()).toEqual(EXPECTED_NEUTRAL_FILES);
    expect(neutralFiles.some((file) => file.endsWith(".tsx"))).toBe(false);
  });

  it("keeps neutral core sources free of surface, domain, and React host references", () => {
    const violations: string[] = [];
    for (const file of listNeutralFiles()) {
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

const EDIT_HOST_ROOT = join(ROOT, "editHost");

const FORBIDDEN_EDIT_HOST_IMPORTS: Array<{ name: string; pattern: RegExp }> = [
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
    name: "tiptap import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*tiptap/,
  },
  {
    name: "markdownCanvas import",
    pattern: /\b(from|import)\b\s*\(?\s*['"][^'"]*markdownCanvas/,
  },
];

describe("editHost boundaries", () => {
  it("keeps editHost production sources free of domain editor imports", () => {
    const violations: string[] = [];
    for (const file of listProductionFiles(EDIT_HOST_ROOT)) {
      const source = readFileSync(file, "utf8");
      for (const { name, pattern } of FORBIDDEN_EDIT_HOST_IMPORTS) {
        if (pattern.test(source)) {
          violations.push(`${relative(ROOT, file)}: ${name}`);
        }
      }
    }
    expect(violations).toEqual([]);
  });
});
