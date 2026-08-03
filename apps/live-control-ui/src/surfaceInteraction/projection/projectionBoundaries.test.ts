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

/**
 * Strip // and block comments while preserving string/template literal contents
 * so stale comment mentions do not trip ownership scans, but real imports/JSX do.
 */
function stripCommentsForScan(source: string): string {
  let out = "";
  let i = 0;
  type State = "code" | "squote" | "dquote" | "template" | "line" | "block";
  let state: State = "code";
  while (i < source.length) {
    const ch = source[i]!;
    const next = source[i + 1];
    if (state === "code") {
      if (ch === "/" && next === "/") {
        state = "line";
        i += 2;
        continue;
      }
      if (ch === "/" && next === "*") {
        state = "block";
        i += 2;
        continue;
      }
      if (ch === "'") {
        state = "squote";
        out += ch;
        i += 1;
        continue;
      }
      if (ch === '"') {
        state = "dquote";
        out += ch;
        i += 1;
        continue;
      }
      if (ch === "`") {
        state = "template";
        out += ch;
        i += 1;
        continue;
      }
      out += ch;
      i += 1;
      continue;
    }
    if (state === "line") {
      if (ch === "\n") {
        state = "code";
        out += ch;
      }
      i += 1;
      continue;
    }
    if (state === "block") {
      if (ch === "*" && next === "/") {
        state = "code";
        i += 2;
        continue;
      }
      i += 1;
      continue;
    }
    // string / template states — preserve escapes and content
    out += ch;
    if (ch === "\\" && next !== undefined) {
      out += next;
      i += 2;
      continue;
    }
    if (state === "squote" && ch === "'") state = "code";
    else if (state === "dquote" && ch === '"') state = "code";
    else if (state === "template" && ch === "`") state = "code";
    i += 1;
  }
  return out;
}

function hasAdaptiveProjectionContainerReference(source: string): boolean {
  // After comment stripping, any remaining symbol is an import, mount, or runtime use.
  return /\bAdaptiveProjectionContainer\b/.test(stripCommentsForScan(source));
}

describe("projection host ownership boundaries", () => {
  it("removes AdaptiveProjectionContainer from production sources", () => {
    const hits: string[] = [];
    for (const file of listProductionSourcesUnder("")) {
      const rel = relative(SRC_ROOT, file);
      const source = readFileSync(file, "utf8");
      if (hasAdaptiveProjectionContainerReference(source)) {
        hits.push(rel);
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

  it("keeps neutral projection production sources free of Plan-owned presentation copy", () => {
    const forbidden = ["Plan toolbox", "Close toolbox", "Command Board"];
    const violations: string[] = [];
    for (const file of listProductionFiles(PROJECTION_ROOT)) {
      const source = readFileSync(file, "utf8");
      for (const phrase of forbidden) {
        if (source.includes(phrase)) {
          violations.push(`${relative(PROJECTION_ROOT, file)}: ${phrase}`);
        }
      }
    }
    expect(violations).toEqual([]);
  });

  it("does not interpolate tool keys into CSS class tokens in ProjectionHost", () => {
    const hostSource = readFileSync(join(PROJECTION_ROOT, "ProjectionHost.tsx"), "utf8");
    expect(hostSource).not.toMatch(/surface-projection-host--tool-\$\{/);
    expect(hostSource).toMatch(/data-projection-key=\{active\?\.key\}/);
  });

  it("removes the legacy renderer switch symbols from production sources", () => {
    const forbidden = /\b(renderToolProjection|renderContentProjection|projectionRegistry)\b/;
    const hits: string[] = [];
    for (const file of listProductionSourcesUnder("")) {
      const source = stripCommentsForScan(readFileSync(file, "utf8"));
      if (forbidden.test(source)) {
        hits.push(relative(SRC_ROOT, file));
      }
    }
    expect(hits).toEqual([]);
  });

  it("limits concrete projection renderer imports to explicit registration adapters", () => {
    const allowed = new Set([
      "planSurface/projection/PlanProjectionCatalogRegistration.tsx",
      "planSurface/projection/IngestProjectionCatalogRegistration.tsx",
    ]);
    const rendererImport = /\bfrom\s+["'][^"']*(?:modules\/(?:Ingestion|PartyRegistry)|surface\/modules\/Statblock|graphPreview\/(?:RecapGraph|GraphPreview)|graphGoldReview\/GraphGoldReview|manualReview\/ManualReview|graphReviewWorkbench\/GraphReviewDiagnosticsToolPanel|reference\/PlanReferenceObjectCard)/;
    const hits: string[] = [];
    for (const file of listProductionSourcesUnder("planSurface/projection")) {
      const rel = relative(SRC_ROOT, file);
      if (allowed.has(rel)) continue;
      const source = readFileSync(file, "utf8");
      if (rendererImport.test(source)) {
        hits.push(rel);
      }
    }
    expect(hits).toEqual([]);
  });

  it("keeps the neutral projection catalog free of domain imports", () => {
    const catalogSource = readRelative("surfaceInteraction/projection/projectionCatalog.ts");
    const forbidden = /\b(from|import)\b\s*\(?\s*["'][^"']*(planSurface|ingestSurface|buildSurface|graphReference|\/api\/)/;
    expect(forbidden.test(catalogSource)).toBe(false);
  });

  it("does not use dynamic discovery or persistence in catalog provider paths", () => {
    const forbidden = /import\.meta\.glob|dynamic import|localStorage|sessionStorage|indexedDB/;
    const paths = [
      "surfaceInteraction/projection/projectionCatalog.ts",
      "agentInteraction/AgentInteractionProvider.tsx",
    ];
    const hits = paths.filter((relPath) => forbidden.test(readRelative(relPath)));
    expect(hits).toEqual([]);
  });
});
